#!/usr/bin/env python

# This code was partially made with the use of Copilot AI, specifically the functionality for playing the AI generated audio with VLC. The code to detect the disks was taken from the original authors' repository.
# Given that most of the non-AI code was cobbled together from posts on Reddit, StackOverflow, and the Raspberry Pi forum, this code is exempted from the GNU GPLv3 that the rest of the repository is under. I take no credit or ownership of its contents, and you are free to do whatever you want with it.

import RPi.GPIO as GPIO
import vlc
import time
import requests

# Try to import the local mfrc522 library
try:
    from mfrc522 import MFRC522, NTAGType, NDEFRecord, SimpleMFRC522
    MFRC522_AVAILABLE = True
except ImportError:
    # Fallback to global mfrc522 if local not available
    try:
        from mfrc522 import SimpleMFRC522
        MFRC522_AVAILABLE = True
    except ImportError:
        MFRC522_AVAILABLE = False

# Try to import enhanced reader and decoder
try:
    from enhanced_rfid_reader import EnhancedRFIDReader
    from ntag215_decoder import NTAG215Decoder, decode_ntag215_raw_data
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

BASE_URL = "http://localhost:3000" # Suno API URL

# For playback buttons
PIN_PLAY_PAUSE = 17
PIN_REWIND     = 27
PIN_FORWARD    = 22

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_PLAY_PAUSE, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_REWIND,     GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_FORWARD,    GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

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

# Song Playback Function
def play_audio_url(audio_url):
    print(f"Playing: {audio_url}")
    player = vlc.MediaPlayer(audio_url)
    player.play()
    is_playing = True

    try:
        while True:
            state = player.get_state()
            if state in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):
                break

            # Button checks
            if GPIO.input(PIN_PLAY_PAUSE) == GPIO.HIGH:
                if is_playing:
                    player.pause()
                    print("Paused")
                    is_playing = False
                else:
                    player.play()
                    print("Resumed")
                    is_playing = True
                time.sleep(0.3)  # debounce

            if GPIO.input(PIN_REWIND) == GPIO.HIGH:
                current_time = player.get_time()  # in ms
                player.set_time(max(current_time - 10000, 0))
                print("Rewind 10s")
                time.sleep(0.3)  # debounce

            if GPIO.input(PIN_FORWARD) == GPIO.HIGH:
                current_time = player.get_time()
                length = player.get_length()
                player.set_time(min(current_time + 10000, length))
                print("Forward 10s")
                time.sleep(0.3)  # debounce

            time.sleep(0.1)
    finally:
        GPIO.cleanup()

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
        # Check for text data first
        if text_data and text_data.strip():
            return process_text_payload(text_data.strip())
        
        # If no text data, could check UID for encoded data
        uid_hex = ''.join([f'{b:02X}' for b in uid])
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

###############################################

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.cleanup()

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
                        uid = decoded_data.get('uid', {}).get('hex', 'Unknown')
                        print(f"NTAG215 Card detected - UID: {uid}")
                        
                        # Process the decoded data
                        song_type, song_data = process_ntag_data(uid, decoded_data.get('ndef_data', {}).get('payload_text', ''), NTAGType.NTAG215)
                        
                        if song_type == 'minecraft':
                            if last_uid == uid:
                                tries = 0
                                last_uid = uid
                                continue
                            song_name = song_data
                            print(f"Playing Minecraft song: {song_name}")
                            play_audio_url(f"audio/{song_name}.mp3")
                            
                        elif song_type == 'ai':
                            if last_uid == uid:
                                tries = 0
                                last_uid = uid
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
                                    
                                    play_audio_url(url_1)
                                    play_audio_url(url_2)
                                    break
                                time.sleep(5)
                        else:
                            print("Unknown song format or no valid song data found.")
                            last_uid = uid
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
                        
                        if text_data:
                            # Process the text data
                            song_type, song_data = process_ntag_data(uid, text_data, ntag_type)
                            
                            if song_type == 'minecraft':
                                song_name = song_data
                                print(f"Playing Minecraft song: {song_name}")
                                play_audio_url(f"audio/{song_name}.mp3")
                                
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
                                        
                                        play_audio_url(url_1)
                                        play_audio_url(url_2)
                                        break
                                    time.sleep(5)
                            else:
                                print("Unknown song format or no valid song data found.")
                        else:
                            print("No readable data found on tag")
                        
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