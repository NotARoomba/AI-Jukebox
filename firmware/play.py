import vlc
import time
import os
import RPi.GPIO as GPIO

PIN_PLAY_PAUSE = 17
PIN_REWIND     = 27
PIN_FORWARD    = 22
PIN_VOLUME_UP  = 23  # Add volume up button
PIN_VOLUME_DOWN = 24  # Add volume down button

# Default volume setting (0-100)
DEFAULT_VOLUME = 70  # 70% volume by default

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_PLAY_PAUSE, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_REWIND,     GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_FORWARD,    GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_VOLUME_UP,  GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(PIN_VOLUME_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Volume Control System
# Uses amixer to control system volume
# Supports multiple mixer types: Master, PCM, Speaker, Headphone
# Includes mute/unmute functionality
# Volume range: 0-100%
# Default volume: 70%

def mute_audio():
    """
    Mute system audio using amixer
    """
    try:
        import subprocess
        mixer_names = ['Master', 'PCM', 'Speaker', 'Headphone']
        
        for mixer in mixer_names:
            try:
                cmd = f"amixer set {mixer} mute"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"Audio muted using {mixer} mixer")
                    return True
            except Exception as e:
                print(f"Failed to mute using {mixer} mixer: {e}")
                continue
        
        print("Failed to mute audio with any mixer")
        return False
        
    except Exception as e:
        print(f"Error muting audio: {e}")
        return False

def unmute_audio():
    """
    Unmute system audio using amixer
    """
    try:
        import subprocess
        mixer_names = ['Master', 'PCM', 'Speaker', 'Headphone']
        
        for mixer in mixer_names:
            try:
                cmd = f"amixer set {mixer} unmute"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"Audio unmuted using {mixer} mixer")
                    return True
            except Exception as e:
                print(f"Failed to unmute using {mixer} mixer: {e}")
                continue
        
        print("Failed to unmute audio with any mixer")
        return False
        
    except Exception as e:
        print(f"Error unmuting audio: {e}")
        return False

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

def show_volume_info():
    """
    Display current volume information
    """
    current_volume = get_volume()
    if current_volume is not None:
        print(f"Current system volume: {current_volume}%")
    else:
        print("Could not determine current volume")
    print(f"Default playback volume: {DEFAULT_VOLUME}%")

# Song Playback Function
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
        set_volume(DEFAULT_VOLUME) # Use default volume if not specified
    
    player = vlc.MediaPlayer(audio_url)
    player.play()
    is_playing = True
    current_volume = volume_percent if volume_percent is not None else DEFAULT_VOLUME

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

            # Volume control buttons
            if GPIO.input(PIN_VOLUME_UP) == GPIO.HIGH:
                current_volume = min(100, current_volume + 10)
                set_volume(current_volume)
                print(f"Volume increased to {current_volume}%")
                time.sleep(0.3)  # debounce

            if GPIO.input(PIN_VOLUME_DOWN) == GPIO.HIGH:
                current_volume = max(0, current_volume - 10)
                set_volume(current_volume)
                print(f"Volume decreased to {current_volume}%")
                time.sleep(0.3)  # debounce

            time.sleep(0.1)
    finally:
        player.stop()
        player.release()

def main():
    # Show volume information on startup
    print("=== Volume Information ===")
    show_volume_info()
    print("==========================")
    
    try:
        play_audio_url(f"audio/haggstrom.mp3", DEFAULT_VOLUME)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()