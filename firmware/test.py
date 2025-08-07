#!/usr/bin/env python3

from time import sleep
import sys
import argparse
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='RFID Tag Reader/Writer')
    parser.add_argument('--write', '-w', type=str, help='Text to write to the tag')
    parser.add_argument('--read-only', '-r', action='store_true', help='Only read tags, do not write')
    
    args = parser.parse_args()
    
    reader = SimpleMFRC522()
    
    try:
        while True:
            print("Hold a tag near the reader")
            id, text = reader.read()
            print(f"ID: {id}")
            print(f"Current Text: {text}")
            
            # If write argument is provided and not in read-only mode, write to tag
            if args.write and not args.read_only:
                print(f"Writing '{args.write}' to tag...")
                reader.write(args.write)
                print("Write successful!")
                # Read again to confirm
                id, new_text = reader.read()
                print(f"Updated Text: {new_text}")
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