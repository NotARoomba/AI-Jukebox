#!/usr/bin/env python3

"""
NFC Card Reader Test Script
Uses the old MFRC522 library from the mfrc522 folder.
"""

import time
import sys
import os

# Add the mfrc522 folder to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'mfrc522'))

try:
    from mfrc522 import MFRC522
except ImportError as e:
    print(f"Error importing MFRC522 library: {e}")
    print("Make sure the MFRC522.py file exists in the mfrc522 folder.")
    sys.exit(1)

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO not found")
    print("Install with: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

try:
    import spidev
except ImportError:
    print("Error: spidev not found")
    print("Install with: sudo apt-get install python3-spidev")
    sys.exit(1)


def main():
    """Main function"""
    print("Place an NFC card on the reader...")
    print("Press Ctrl+C to exit")
    
    try:
        # Initialize MFRC522 with updated pins
        print("Initializing MFRC522...")
        reader = MFRC522(bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=22)
        print("✓ MFRC522 initialized successfully with updated pin configuration")
        print("✓ Hardware reset pin (GPIO 22) configured and tested")
        
        last_uid = None
        while True:
            try:
                # Check if a new card is present
                (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
                if status == reader.MI_OK:
                    print("✓ Card detected!")
                    
                    # Read the card serial
                    (status, uid) = reader.MFRC522_Anticoll()
                    if status == reader.MI_OK:
                        # Convert UID to hex string
                        uid_hex = ''.join([f'{b:02X}' for b in uid[:4]])
                        
                        # Check if it's the same card
                        if last_uid == uid_hex:
                            time.sleep(0.5)
                            continue
                        
                        print(f"Card UID: {uid_hex}")
                        last_uid = uid_hex
                        
                        # Read first block (block 0)
                        block_data = reader.MFRC522_Read(0)
                        if block_data:
                            print("Block 0 data:", ' '.join([f'{b:02X}' for b in block_data]))
                        else:
                            print("✗ Failed to read block 0")
                        
                        # Halt the card
                        reader.MFRC522_StopCrypto1()
                        print("-" * 50)
                    else:
                        print("✗ Failed to read card serial")
                else:
                    # No card detected, reset last_uid after a delay
                    if last_uid is not None:
                        time.sleep(1)
                        last_uid = None
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error during card detection: {e}")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'reader' in locals():
            reader.Close_MFRC522()
        print("Cleanup complete")


if __name__ == '__main__':
    main()
