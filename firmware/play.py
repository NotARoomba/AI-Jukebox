import vlc
import time
import os
import RPi.GPIO as GPIO

# Volume setting (0-100)
VOLUME = 80  # 80% volume by default

# Volume Control System
# Uses amixer to control system volume
# Supports multiple mixer types: Master, PCM, Speaker, Headphone
# Volume range: 0-100%
# Default volume: 80%

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
    print(f"Default playback volume: {VOLUME}%")

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

def main():
    # Show volume information on startup
    print("=== Volume Information ===")
    show_volume_info()
    print("==========================")
    
    try:
        play_audio_url(f"audio/cat.mp3", VOLUME)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    main()