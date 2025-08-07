#!/usr/bin/env python

# This code was partially made with the use of Copilot AI, specifically the functionality for playing the AI generated audio with VLC. The code to detect the disks was taken from the original authors' repository.
# Given that most of the non-AI code was cobbled together from posts on Reddit, StackOverflow, and the Raspberry Pi forum, this code is exempted from the GNU GPLv3 that the rest of the repository is under. I take no credit or ownership of its contents, and you are free to do whatever you want with it.

import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import vlc
import time
import requests

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

###############################################

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.cleanup()

    reader = SimpleMFRC522()

    # Minecraft songs will be formated using m_{song_name}
    # e.g. m_minecraft, m_chirp, m_cat, etc.
    # AI generated songs will have a bitmask that indicates the mood, denoted by a_{bitmask}

    last_id = None
    tries = 0

    try:
        while True:
            id, text = reader.read()

            print(f"ID: {id}, Text: {text.strip()}")
            if text.startswith('m_'):
                if last_id == id:
                    # print("Already playing Minecraft song.")
                    tries = 0
                    last_id = id
                    continue
                song_name = text[2:].strip()
                print(f"Playing Minecraft song: {song_name}")
                play_audio_url(f"audio/{song_name}.mp3")
            elif text.startswith('a_'):
                if last_id == id:
                    # print("Already playing AI generated song.")
                    tries = 0
                    last_id = id
                    continue
                try:
                    mask = int(text[2:].strip(), 16)
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
                except ValueError:
                    print("Invalid mood bitmask format.")
            else:
                if last_id is not None and last_id != id:
                    print("Unknown song format or no valid song found.")
                    last_id = id
                    time.sleep(1)
                print("Unknown song format.")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()