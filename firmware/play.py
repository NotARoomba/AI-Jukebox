import vlc
import time
import os
import RPi.GPIO as GPIO

PIN_PLAY_PAUSE = 17
PIN_REWIND = 27
PIN_FORWARD = 22



# Song Playback Function
def play_audio_url(audio_url):
    print(f"Playing: {audio_url}")
    
    # Check if it's a local file
    if audio_url.startswith('audio/'):
        import os
        if not os.path.exists(audio_url):
            print(f"Error: Audio file not found: {audio_url}")
            print("Please ensure the audio file exists in the audio/ directory")
            return
    
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
        player.stop()
        player.release()

play_audio_url(f"audio/haggstrom.mp3")