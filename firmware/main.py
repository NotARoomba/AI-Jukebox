#!/usr/bin/env python

# This code was partially made with the use of Copilot AI, specifically the functionality for playing the AI generated audio with VLC. The code to detect the disks was taken from the original authors' repository.
# Given that most of the non-AI code was cobbled together from posts on Reddit, StackOverflow, and the Raspberry Pi forum, this code is exempted from the GNU GPLv3 that the rest of the repository is under. I take no credit or ownership of its contents, and you are free to do whatever you want with it.

import RPi.GPIO as GPIO
import vlc
import time
import requests

from mfrc522 import MFRC522

BASE_URL = "http://localhost:3000" # Suno API URL

# Volume setting (0-100)
VOLUME = 70  # 70% volume by default

# Minecraft UID to song mapping
# This maps specific NFC tag UIDs to Minecraft music disk files
# The audio files should be placed in the audio/ directory
MINECRAFT_UID_MAP = {
    '8804C33679': 'haggstrom',  # Specific mapping for haggstrom
    # Add more UID mappings here as needed
    # '1234567890': 'minecraft',
    # 'ABCDEF1234': 'chirp',
    # 'FEDCBA0987': 'cat',
}

# Mood Flags and functions
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

# SUNO API Functions
def generate_audio_by_prompt(payload):
    url = f"{BASE_URL}/api/generate"
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
    return response.json()

def get_audio_information(audio_ids):
    url = f"{BASE_URL}/api/get?ids={audio_ids}"
    response = requests.get(url)
    return response.json()

# Volume Control System
# Uses amixer to control system volume
# Supports multiple mixer types: Master, PCM, Speaker, Headphone
# Volume range: 0-100%
# Default volume: 70%

def set_volume(volume_percent):
    """
    Set system volume using amixer
    
    Args:
        volume_percent: Volume level (0-100)
    """
    try:
        import subprocess
        # Clamp volume between 0 and 100
        volume_percent = max(0, min(100, volume_percent))
        
        # Use amixer to set volume (assuming ALSA mixer)
        # Try different mixer names if one doesn't work
        mixer_names = ['Master', 'PCM', 'Speaker', 'Headphone']
        
        for mixer in mixer_names:
            try:
                # Set volume using amixer
                cmd = f"amixer set {mixer} {volume_percent}%"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"Volume set to {volume_percent}% using {mixer} mixer")
                    return True
            except Exception as e:
                print(f"Failed to set volume using {mixer} mixer: {e}")
                continue
        
        print("Failed to set volume with any mixer")
        return False
        
    except Exception as e:
        print(f"Error setting volume: {e}")
        return False

def get_volume():
    """
    Get current system volume using amixer
    
    Returns:
        Current volume percentage (0-100) or None if failed
    """
    try:
        import subprocess
        import re
        
        # Try different mixer names
        mixer_names = ['Master', 'PCM', 'Speaker', 'Headphone']
        
        for mixer in mixer_names:
            try:
                # Get volume using amixer
                cmd = f"amixer get {mixer}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Parse the output to extract volume percentage
                    output = result.stdout
                    # Look for pattern like "[50%]" or "50%"
                    match = re.search(r'\[(\d+)%\]', output)
                    if match:
                        volume = int(match.group(1))
                        print(f"Current volume: {volume}% (using {mixer} mixer)")
                        return volume
            except Exception as e:
                print(f"Failed to get volume using {mixer} mixer: {e}")
                continue
        
        print("Failed to get volume from any mixer")
        return None
        
    except Exception as e:
        print(f"Error getting volume: {e}")
        return None

def play_audio_url(audio_url, volume_percent=None):
    print(f"Playing: {audio_url}")
    
    # Check if it's a local file
    if audio_url.startswith('audio/'):
        import os
        if not os.path.exists(audio_url):
            print(f"Error: Audio file not found: {audio_url}")
            print("Please ensure the audio file exists in the audio/ directory")
            return
    
    # Set volume if specified
    if volume_percent is not None:
        set_volume(volume_percent)
    else:
        set_volume(VOLUME) # Use default volume if not specified
    
    player = vlc.MediaPlayer(audio_url)
    player.play()

    try:
        while True:
            state = player.get_state()
            if state in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
                break
            time.sleep(0.1)
    finally:
        player.stop()
        player.release()

def process_ntag_data(uid, text_data, ntag_type):
    """
    Process NTAG data and extract song information
    
    Args:
        uid: UID of the tag
        text_data: Text data from the tag
        ntag_type: NTAG type
        
    Returns:
        Tuple of (song_type, song_data) or (None, None) if no valid song data
    """
    try:
        # Convert UID to hex string for mapping lookup
        if isinstance(uid, bytes):
            uid_hex = ''.join([f'{b:02X}' for b in uid])
        else:
            uid_hex = uid
        
        # Check for UID-based Minecraft song mapping first
        if uid_hex in MINECRAFT_UID_MAP:
            song_name = MINECRAFT_UID_MAP[uid_hex]
            print(f"Found UID-based Minecraft song mapping: {uid_hex} -> {song_name}")
            return 'minecraft', song_name
        
        # Check for text data
        if text_data and text_data.strip():
            return process_text_payload(text_data.strip())
        
        # If no text data and no UID mapping, could check UID for encoded data
        if uid_hex and len(uid_hex) >= 8:
            # Could encode data in UID (though this is unusual)
            pass
        
        return None, None
        
    except Exception as e:
        print(f"Error processing NTAG data: {e}")
        return None, None

def process_text_payload(text):
    """
    Process text payload and determine song type
    
    Args:
        text: Text payload from NFC tag
        
    Returns:
        Tuple of (song_type, song_data) or (None, None) if no valid song data
    """
    text = text.strip()
    
    if text.startswith('m_'):
        # Minecraft song
        song_name = text[2:].strip()
        return 'minecraft', song_name
    elif text.startswith('a_'):
        # AI generated song with mood bitmask
        try:
            mask = int(text[2:].strip(), 16)
            return 'ai', mask
        except ValueError:
            print("Invalid mood bitmask format.")
            return None, None
    else:
        # Unknown format
        return None, None

def show_volume_info():
    """
    Display current volume information
    """
    current_volume = get_volume()
    if current_volume is not None:
        print(f"Current system volume: {current_volume}%")
    else:
        print("Could not determine current volume")
    print(f"Default playback volume: {VOLUME}%")

###############################################

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.cleanup()

    # Show volume information on startup
    print("=== Volume Information ===")
    show_volume_info()
    print("==========================")

    # Initialize reader
    if ENHANCED_AVAILABLE:
        print("✓ Using enhanced RFID reader with NTAG215 support")
        reader = EnhancedRFIDReader()
        use_enhanced = True
    else:
        if MFRC522_AVAILABLE:
            print("✓ Using MFRC522 library with NTAG support")
            reader = MFRC522()
            use_enhanced = False
        else:
            print("✗ No MFRC522 library available")
            return

    # Minecraft songs will be formatted using m_{song_name}
    # e.g. m_minecraft, m_chirp, m_cat, etc.
    # AI generated songs will have a bitmask that indicates the mood, denoted by a_{bitmask}

    last_uid = None
    tries = 0
    print("Starting main loop")
    try:
        while True:
            try:
                if use_enhanced:
                    # Use enhanced reader for NTAG215 decoding
                    decoded_data = reader.read_and_decode_ntag215()
                    
                    if decoded_data:
                        uid_hex = decoded_data.get('uid', {}).get('hex', 'Unknown')
                        print(f"NTAG215 Card detected - UID: {uid_hex}")
                        
                        # Process the decoded data (pass UID as hex string)
                        song_type, song_data = process_ntag_data(uid_hex, decoded_data.get('ndef_data', {}).get('payload_text', ''), NTAGType.NTAG215)
                        
                        if song_type == 'minecraft':
                            if last_uid == uid_hex:
                                tries = 0
                                last_uid = uid_hex
                                continue
                            song_name = song_data
                            print(f"Playing Minecraft song: {song_name}")
                            play_audio_url(f"audio/{song_name}.mp3", VOLUME)
                            
                        elif song_type == 'ai':
                            if last_uid == uid_hex:
                                tries = 0
                                last_uid = uid_hex
                                continue
                            mask = song_data
                            moods = extract_flags(mask)
                            print(f"Playing AI generated song with moods: {', '.join(moods)}")
                            
                            data = generate_audio_by_prompt({
                                "prompt": f"Generate a song with the following moods: {', '.join(moods)}",
                                "make_instrumental": True,
                                "wait_audio": False
                            })

                            ids = f"{data[0]['id']},{data[1]['id']}"
                            print(f"ids: {ids}")

                            for _ in range(60):
                                data = get_audio_information(ids)
                                if data[0]["status"] == 'streaming':
                                    url_1 = data[0]["audio_url"]
                                    url_2 = data[1]["audio_url"]
                                    print(f"{data[0]['id']} ==> {url_1}")
                                    print(f"{data[1]['id']} ==> {url_2}")
                                    
                                    play_audio_url(url_1, VOLUME)
                                    play_audio_url(url_2, VOLUME)
                                    break
                                time.sleep(5)
                        else:
                            print("Unknown song format or no valid song data found.")
                            last_uid = uid_hex
                    else:
                        print("No card detected or failed to decode")
                        
                else:
                    # Use new MFRC522 library with NTAG support
                    (success, uid, ntag_type) = reader.detect_ntag()
                    if success:
                        uid_str = ''.join([f'{b:02X}' for b in uid])
                        print(f"NTAG Card detected - UID: {uid_str}, Type: {ntag_type.name}")
                        
                        if last_uid == uid_str:
                            tries = 0
                            last_uid = uid_str
                            continue
                        
                        # Try to read NDEF records first
                        ndef_records = reader.read_ndef_records(ntag_type)
                        text_data = ""
                        
                        if ndef_records:
                            print(f"Found {len(ndef_records)} NDEF record(s):")
                            for i, record in enumerate(ndef_records):
                                print(f"  Record {i+1}: {record.record_type} - {record.payload}")
                                if record.record_type == "text":
                                    text_data += record.payload
                                elif record.record_type == "url":
                                    text_data += record.payload
                                else:
                                    text_data += record.payload
                        
                        # If no NDEF records, try raw data
                        if not text_data:
                            data_bytes = reader.read_ntag_data(ntag_type)
                            
                            if data_bytes:
                                # Remove trailing zeros
                                while data_bytes and data_bytes[-1] == 0:
                                    data_bytes.pop()
                                
                                if data_bytes:
                                    # Convert to text, filtering out non-printable characters
                                    text_data = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
                                    print(f"Raw tag data: {text_data}")
                        
                        # Process the data (including UID-based mapping)
                        song_type, song_data = process_ntag_data(uid, text_data, ntag_type)
                        
                        if song_type == 'minecraft':
                            song_name = song_data
                            print(f"Playing Minecraft song: {song_name}")
                            play_audio_url(f"audio/{song_name}.mp3", VOLUME)
                            
                        elif song_type == 'ai':
                            mask = song_data
                            moods = extract_flags(mask)
                            print(f"Playing AI generated song with moods: {', '.join(moods)}")
                            data = generate_audio_by_prompt({
                                "prompt": f"Generate a song with the following moods: {', '.join(moods)}",
                                "make_instrumental": True,
                                "wait_audio": False
                            })

                            ids = f"{data[0]['id']},{data[1]['id']}"
                            print(f"ids: {ids}")

                            for _ in range(60):
                                data = get_audio_information(ids)
                                if data[0]["status"] == 'streaming':
                                    url_1 = data[0]["audio_url"]
                                    url_2 = data[1]["audio_url"]
                                    print(f"{data[0]['id']} ==> {url_1}")
                                    print(f"{data[1]['id']} ==> {url_2}")
                                    
                                    play_audio_url(url_1, VOLUME)
                                    play_audio_url(url_2, VOLUME)
                                    break
                                time.sleep(5)
                        else:
                            print("Unknown song format or no valid song data found.")
                        
                        last_uid = uid_str
                    else:
                        print("No card detected")
                        time.sleep(0.1)
                    
            except Exception as e:
                error_msg = str(e)
                if "AUTH ERROR" in error_msg or "status2reg" in error_msg:
                    print(f"AUTH ERROR detected: {error_msg}")
                    print("Troubleshooting: Check card position, try different card, verify wiring")
                    tries += 1
                    if tries > 5:
                        print("Too many AUTH errors, waiting 10 seconds before retrying...")
                        time.sleep(10)
                        tries = 0
                    time.sleep(1)
                else:
                    print(f"RFID reading error: {error_msg}")
                    time.sleep(1)
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()