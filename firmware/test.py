#!/usr/bin/env python3
"""
NFC Test Script

This script automatically listens for NFC tags and reads the first record.
If the -w flag is provided, it will also write a string to the tag.

Usage:
    python test.py           # Read only mode
    python test.py -w        # Read and write mode
    python test.py -w "Hello World"  # Read and write specific string
"""

import sys
import time
import argparse

# Import the local mfrc522 module
try:
    from mfrc522 import SimpleMFRC522
except ImportError:
    print("Error: Could not import mfrc522 module. Make sure you're running this from the firmware directory.")
    sys.exit(1)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NFC Tag Reader/Writer')
    parser.add_argument('-w', '--write', nargs='?', const='Test Data', 
                       help='Write mode. If no string provided, writes "Test Data"')
    args = parser.parse_args()

    # Initialize the NFC reader
    print("Initializing NFC reader...")
    reader = SimpleMFRC522()
    
    print("NFC Reader initialized successfully!")
    print("Place an NFC tag on the reader...")
    
    if args.write:
        print(f"Write mode enabled. Will write: '{args.write}'")
    else:
        print("Read-only mode enabled.")
    
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    try:
        while True:
            print("\nWaiting for NFC tag...")
            
            if args.write:
                # Write mode - write first, then read
                print(f"Writing '{args.write}' to tag...")
                try:
                    id, text_written = reader.write(args.write)
                    if id:
                        print(f"✓ Successfully wrote to tag (ID: {id})")
                        print(f"  Written text: '{text_written}'")
                    else:
                        print("✗ Failed to write to tag")
                        continue
                except Exception as e:
                    print(f"✗ Error writing to tag: {e}")
                    continue
            
            # Read mode - always read after writing or just read
            print("Reading tag data...")
            try:
                id, text = reader.read()
                if id and text:
                    print(f"✓ Tag detected (ID: {id})")
                    print(f"  First record: '{text.strip()}'")
                elif id:
                    print(f"✓ Tag detected (ID: {id})")
                    print("  No readable data found")
                else:
                    print("✗ Failed to read tag")
                    continue
            except Exception as e:
                print(f"✗ Error reading tag: {e}")
                continue
            
            print("\n" + "="*50)
            print("Remove tag to continue...")
            
            # Wait for tag to be removed before continuing
            while True:
                try:
                    # Try to read without blocking to check if tag is still present
                    id_check, _ = reader.read_no_block()
                    if not id_check:
                        break  # Tag removed
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    raise
                except:
                    break  # Assume tag removed if error occurs
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
        print("Cleaning up GPIO...")
        import RPi.GPIO as GPIO
        GPIO.cleanup()
        print("Done!")

if __name__ == "__main__":
    main()
