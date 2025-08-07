#!/usr/bin/env python3

from time import sleep
import sys
import argparse
import RPi.GPIO as GPIO
from mfrc522 import MFRC522
from mfrc522 import SimpleMFRC522
from datetime import datetime

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='RFID Tag Reader/Writer')
    parser.add_argument('--write', '-w', type=str, help='Text to write to the tag')
    parser.add_argument('--read-only', '-r', action='store_true', help='Only read tags, do not write')
    
    args = parser.parse_args()
    
    reader = MFRC522()
    
    try:
        while True:
            print("Hold a tag near the reader")
            
            # Request card detection
            status, _ = reader.MFRC522_Request(reader.PICC_REQIDL)
            if status != reader.MI_OK:
                sleep(0.1)
                continue
            
            # Anticollision
            status, backData = reader.MFRC522_Anticoll()
            if status != reader.MI_OK:
                print("Anticollision failed")
                continue
            
            # Read the card data
            buf = reader.MFRC522_Read(0)
            reader.MFRC522_Request(reader.PICC_HALT)
            
            if buf:
                # Convert buffer to hex string for display
                hex_data = ':'.join([hex(x) for x in buf])
                print(f"Timestamp: {datetime.now().isoformat()}")
                print(f"Card Data: {hex_data}")
                
                # If write argument is provided and not in read-only mode, write to tag
                if args.write and not args.read_only:
                    print(f"Writing '{args.write}' to tag...")
                    try:
                        # Use SimpleMFRC522 for writing as it handles authentication better
                        simple_reader = SimpleMFRC522()
                        simple_reader.write(args.write)
                        print("Write successful!")
                        # Read again to confirm
                        id, new_text = simple_reader.read()
                        print(f"Updated Text: {new_text}")
                    except Exception as write_error:
                        print(f"Write failed: {write_error}")
                elif args.write:
                    print("Write argument provided but --read-only flag is set. Skipping write operation.")
                
                print("-" * 40)
                sleep(2)
            
    except KeyboardInterrupt:
        print("\nExiting...")
        GPIO.cleanup()
    except Exception as e:
        print(f"Error: {e}")
        GPIO.cleanup()
        raise

if __name__ == "__main__":
    main()