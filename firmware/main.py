#!/usr/bin/env python3

import os
import time
import re
import requests
import vlc
import RPi.GPIO as GPIO
from mfrc522 import MFRC522

BASE_URL = "http://localhost:3000"  # Suno API URL
VOLUME = 70

MOOD_FLAGS = {
    'HAPPY':       0x01,
    'SAD':         0x02,
    'ENERGETIC':   0x04,
    'CHILL':       0x08,
    'ROMANTIC':    0x10,
    'ANGRY':       0x20,
    'MELANCHOLIC': 0x40,
    'MYSTERIOUS':  0x80,
}

def extract_flags(mask: int) -> list:
    return [name for name, value in MOOD_FLAGS.items() if mask & value]

def generate_audio_by_prompt(payload):
    url = f"{BASE_URL}/api/generate"
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
    return response.json()

def get_audio_information(audio_ids):
    url = f"{BASE_URL}/api/get?ids={audio_ids}"
    response = requests.get(url)
    return response.json()

def set_volume(volume_percent):
    try:
        import subprocess
        volume_percent = max(0, min(100, volume_percent))
        for mixer in ['Master', 'PCM', 'Speaker', 'Headphone']:
            try:
                result = subprocess.run(f"amixer set {mixer} {volume_percent}%", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"Volume set to {volume_percent}% using {mixer} mixer")
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

def get_volume():
    try:
        import subprocess
        for mixer in ['Master', 'PCM', 'Speaker', 'Headphone']:
            try:
                result = subprocess.run(f"amixer get {mixer}", shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    match = re.search(r'\[(\d+)%\]', result.stdout)
                    if match:
                        volume = int(match.group(1))
                        print(f"Current volume: {volume}% (using {mixer} mixer)")
                        return volume
            except Exception:
                continue
        return None
    except Exception:
        return None

def create_player(audio_url):
    print(f"Playing: {audio_url}")
    if audio_url.startswith('audio/') and not os.path.exists(audio_url):
        print(f"Audio file not found: {audio_url}")
        return None
    set_volume(VOLUME)
    player = vlc.MediaPlayer(audio_url)
    player.play()
    try:
        # Give VLC a moment to initialize, then set player volume to 0 for fade-in
        time.sleep(0.05)
        player.audio_set_volume(0)  # Start at 0 for fade-in
    except Exception:
        pass
    return player

def fade_in(player, fade_ms=800, steps=16):
    if player is None:
        return
    try:
        target = 100
        step = max(1, target // steps)
        delay = max(0.0, (fade_ms / 1000.0) / max(1, (target // step)))
        vol = 0
        while vol < target:
            player.audio_set_volume(vol)
            time.sleep(delay)
            vol += step
        player.audio_set_volume(target)
    except Exception:
        pass

def fade_out_and_stop(player, fade_ms=800, steps=16):
    if player is None:
        return
    try:
        current = player.audio_get_volume()
        if current is None or current < 0:
            current = 100
        step = max(1, current // steps)
        delay = max(0.0, (fade_ms / 1000.0) / max(1, (current // step)))
        vol = current
        while vol > 0:
            player.audio_set_volume(vol)
            time.sleep(delay)
            vol -= step
        player.audio_set_volume(0)
    except Exception:
        pass
    try:
        player.stop()
        player.release()
    except Exception:
        pass

def read_text_from_tag(reader):
    # Read NDEF Text record payload using same logic verified in test.py
    if not reader.IsNTAG():
        return None
    # Collect TLV data in 16-byte chunks (4 pages per read)
    data = bytearray()
    expected_total = None
    current_page = 4
    while current_page <= reader.NTAG_MaxPage:
        stat, block = reader.readNTAGBlock(current_page)
        if stat != reader.OK or not block:
            break
        data.extend(block)
        # Find TLV length when possible
        if expected_total is None and len(data) >= 2:
            tlv_idx = next((i for i,b in enumerate(data[:-1]) if b == 0x03), -1)
            if tlv_idx != -1 and len(data) >= tlv_idx + 2:
                tlv_len = data[tlv_idx + 1]
                header_extra = 0
                if tlv_len == 0xFF:
                    if len(data) >= tlv_idx + 4:
                        tlv_len = (data[tlv_idx + 2] << 8) | data[tlv_idx + 3]
                        header_extra = 2
                    else:
                        tlv_len = None
                if tlv_len is not None:
                    expected_total = tlv_idx + 2 + header_extra + tlv_len
        if expected_total is not None and len(data) >= expected_total:
            break
        current_page += 4

    if not data:
        return None

    # Parse TLV
    ndef_start = next((i for i,b in enumerate(data[:-1]) if b == 0x03), -1)
    if ndef_start == -1:
        return None
    ndef_length = data[ndef_start + 1]
    tlv_data_idx = ndef_start + 2
    if ndef_length == 0xFF:
        if len(data) < ndef_start + 4:
            return None
        ndef_length = (data[ndef_start + 2] << 8) | data[ndef_start + 3]
        tlv_data_idx = ndef_start + 4

    if tlv_data_idx + ndef_length > len(data):
        return None

    # Parse NDEF Short Text record: D1 01 <PL> 54 <status> 'en' <text>
    if ndef_length < 5:
        return None
    rec_header = data[tlv_data_idx]
    type_len = data[tlv_data_idx + 1]
    payload_len = data[tlv_data_idx + 2]
    if type_len != 1 or tlv_data_idx + 3 + type_len + payload_len > len(data):
        return None
    rec_type = data[tlv_data_idx + 3]
    if rec_type != 0x54:
        return None
    payload_idx = tlv_data_idx + 3 + type_len
    status = data[payload_idx]
    lang_len = status & 0x3F
    is_utf16 = (status & 0x80) != 0
    text_idx = payload_idx + 1 + lang_len
    text_len = payload_len - 1 - lang_len
    if text_len <= 0 or text_idx + text_len > len(data):
        return None
    try:
        return bytes(data[text_idx:text_idx+text_len]).decode('utf-16' if is_utf16 else 'utf-8')
    except Exception:
        return None

def process_text_payload(text):
    text = text.strip()
    if text.startswith('m_'):
        return 'minecraft', text[2:].strip()
    if text.startswith('a_'):
        try:
            return 'ai', int(text[2:].strip(), 16)
        except ValueError:
            return None, None
    return None, None

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.cleanup()

    print("=== Volume Information ===")
    vol = get_volume()
    print(f"Default playback volume: {VOLUME}%")
    print("==========================")

    print("Initializing MFRC522...")
    reader = MFRC522(bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=22)
    reader.DEBUG = False
    print("✓ MFRC522 ready")

    last_uid = None
    current_uid = None
    player = None
    playlist = []  # pending urls for AI two-part playback
    current_track_url = None
    last_tag_text = None
    presence_miss_count = 0
    try:
        print("Place an NFC card on the reader... Press Ctrl+C to exit")
        while True:
            # Poll for tag presence with debounce
            present_status, _ = reader.request(reader.REQIDL)
            if present_status != reader.OK:
                presence_miss_count += 1
                if current_uid is not None and presence_miss_count >= 5:
                    # Consider tag removed after consecutive misses
                    print("Tag removed. Fading out...")
                    if player is not None:
                        fade_out_and_stop(player)
                        player = None
                    playlist = []
                    current_track_url = None
                    current_uid = None
                    last_tag_text = None
                time.sleep(0.1)
                continue
            else:
                presence_miss_count = 0

            # Tag present, get UID
            status, uid = reader.SelectTagSN()
            if status != reader.OK:
                # Could be transient; do not treat as removal yet
                time.sleep(0.05)
                continue

            uid_str = ''.join([f'{b:02X}' for b in uid])

            # If new tag detected
            if uid_str != current_uid:
                current_uid = uid_str
                last_uid = uid_str
                print(f"Card UID: {uid_str}")

                # Read text FIRST to decide if we need to restart playback
                text = read_text_from_tag(reader)
                if not text:
                    print("No readable NDEF text on tag")
                    continue
                print(f"Tag text: {text}")

                song_type, song_data = process_text_payload(text)
                if song_type == 'minecraft':
                    audio_path = f"audio/{song_data}.mp3"
                    # If already playing this exact track, keep playing
                    if player is not None and current_track_url == audio_path and player.get_state() not in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
                        print("Already playing this track; continuing.")
                        last_tag_text = text
                    else:
                        # Stop existing playback only if changing track
                        if player is not None:
                            fade_out_and_stop(player)
                            player = None
                        playlist = []
                        current_track_url = None

                        print(f"Playing Minecraft: {song_data}")
                        player = create_player(audio_path)
                        current_track_url = audio_path if player else None
                        if player is not None:
                            fade_in(player)
                        last_tag_text = text
                elif song_type == 'ai':
                    mask = song_data
                    moods = extract_flags(mask)
                    # If the same AI spec text is already playing, skip
                    if player is not None and last_tag_text == text and player.get_state() not in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
                        print("Already playing this AI selection; continuing.")
                    else:
                        # Stop existing playback only if changing selection
                        if player is not None:
                            fade_out_and_stop(player)
                            player = None
                        playlist = []
                        current_track_url = None

                        print(f"Generating AI track with moods: {', '.join(moods)}")
                        data = generate_audio_by_prompt({
                            "prompt": f"Generate a song with the following moods: {', '.join(moods)}",
                            "make_instrumental": True,
                            "wait_audio": False
                        })
                        ids = f"{data[0]['id']},{data[1]['id']}"
                        # Wait until streaming, but abort if tag leaves or changes
                        ready_urls = None
                        for _ in range(60):
                            # Abort if tag removed or changed
                            st, _ = reader.request(reader.REQIDL)
                            if st != reader.OK:
                                print("Tag removed during AI generation; aborting.")
                                current_uid = None
                                break
                            s2, uid2 = reader.SelectTagSN()
                            if s2 != reader.OK or ''.join([f'{b:02X}' for b in uid2]) != uid_str:
                                print("Different tag detected during AI generation; aborting.")
                                break
                            info = get_audio_information(ids)
                            if info[0]["status"] == 'streaming':
                                ready_urls = [info[0]["audio_url"], info[1]["audio_url"]]
                                break
                            time.sleep(5)
                        if ready_urls:
                            playlist = ready_urls
                            # Start first
                            player = create_player(playlist[0])
                            current_track_url = playlist[0]
                            if player is not None:
                                fade_in(player)
                            # Keep remaining for later
                            playlist = playlist[1:]
                            last_tag_text = text
                else:
                    print("Unknown tag format. Expected 'm_<name>' or 'a_<hexFlags>'.")

            else:
                # Same tag still present; if track ended, advance playlist
                if player is not None:
                    state = player.get_state()
                    if state in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
                        try:
                            player.stop()
                            player.release()
                        except Exception:
                            pass
                        player = None
                        if playlist:
                            next_url = playlist.pop(0)
                            player = create_player(next_url)
                            current_track_url = next_url
                            if player is not None:
                                fade_in(player)

            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()