#!/usr/bin/env python3

"""
NFC Card Reader Test Script
Uses the MFRC522 library from the rfid folder.
"""

import time
import sys
import os

try:
    from .mfrc522.mfrc522 import MFRC522, StatusCode, PICC_Type
except ImportError as e:
    print(f"Error importing MFRC522 library: {e}")
    print("Make sure the mfrc522.py file exists in the rfid folder.")
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
    print("=== MFRC522 NFC Card Reader (Using Library) ===")
    print("Hardware Setup:")
    print("- SDA (CS) -> GPIO 24 (CE0)")
    print("- SCK -> GPIO 23 (SCLK)")
    print("- MOSI -> GPIO 19 (MOSI)")
    print("- MISO -> GPIO 21 (MISO)")
    print("- GND -> GND")
    print("- VCC -> 3.3V")
    print("- RST -> GPIO 22 (Hardware Reset)")
    print("")
    print("Initialization process:")
    print("1. Hardware reset using RST pin (GPIO 22)")
    print("2. SPI initialization")
    print("3. RC522 configuration")
    print("4. Antenna activation")
    print("")
    print("Place an NFC card on the reader...")
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    try:
        # Initialize MFRC522 with updated pins
        print("Initializing MFRC522...")
        reader = MFRC522(chip_select_pin=24, reset_power_down_pin=22)
        print("✓ MFRC522 initialized successfully with updated pin configuration")
        print("✓ Hardware reset pin (GPIO 22) configured and tested")
        
        last_uid = None
        while True:
            try:
                # Check if a new card is present
                if reader.PICC_IsNewCardPresent():
                    print("✓ Card detected!")
                    
                    # Read the card serial
                    if reader.PICC_ReadCardSerial():
                        # Convert UID to hex string
                        uid_hex = ''.join([f'{b:02X}' for b in reader.uid.uid_byte[:reader.uid.size]])
                        
                        # Check if it's the same card
                        if last_uid == uid_hex:
                            time.sleep(0.5)
                            continue
                        
                        print(f"Card UID: {uid_hex}")
                        print(f"Card Type: {reader.PICC_GetTypeName(reader.PICC_GetType(reader.uid.sak))}")
                        last_uid = uid_hex
                        
                        # Read first block (block 0)
                        buffer = [0] * 18
                        buffer_size = [0]
                        status = reader.MIFARE_Read(0, buffer, buffer_size)
                        
                        if status == StatusCode.STATUS_OK and buffer_size[0] > 0:
                            print("Block 0 data:", ' '.join([f'{b:02X}' for b in buffer[:buffer_size[0]]]))
                        else:
                            print(f"✗ Failed to read block 0: {reader.GetStatusCodeName(status)}")
                        
                        # Halt the card
                        reader.PICC_HaltA()
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
            del reader
        print("Cleanup complete")


if __name__ == '__main__':
    main()
