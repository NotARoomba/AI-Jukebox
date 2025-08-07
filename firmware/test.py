#!/usr/bin/env python

import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time
import sys
import argparse

def read_ntag215_tag(reader):
    """Read data from an NTAG215 tag"""
    print("Waiting for NTAG215 tag to read...")
    
    # Use the robust detection method
    while True:
        (success, uid) = reader.detect_ntag215()
        if success:
            print(f"Card detected! UID: {uid}")
            break
        print("Waiting for card...")
        time.sleep(0.1)
    
    # Read data from NTAG215 pages (starting from page 4 to avoid reserved pages 0-3)
    data_bytes = reader.read_ntag215_data(start_page=4, end_page=35)
    
    if data_bytes:
        # Remove trailing zeros
        while data_bytes and data_bytes[-1] == 0:
            data_bytes.pop()
        
        if data_bytes:
            # Convert to text, filtering out non-printable characters
            text = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
            return uid, text
        else:
            return uid, ""
    else:
        return uid, ""

def clear_ntag215_tag(reader, start_page=4, end_page=35):
    """Clear all user data pages on an NTAG215 tag by writing zeros"""
    print("Clearing card data...")
    
    # Use the new clear method
    success = reader.clear_ntag215_data(start_page, end_page)
    if success:
        print(f"Cleared pages {start_page} to {end_page}")
    else:
        print("Warning: Some pages may not have been cleared")
    
    return success

def write_ntag215_tag(reader, text):
    """Write data to an NTAG215 tag"""
    if not text:
        print("No data provided, exiting...")
        return False
    
    print("Now place your NTAG215 tag to write")
    
    # Use the robust detection method
    while True:
        (success, uid) = reader.detect_ntag215()
        if success:
            print(f"Card detected! UID: {uid}")
            break
        print("Waiting for card...")
        time.sleep(0.1)
    
    # Clear the card before writing
    clear_ntag215_tag(reader)
    
    # Convert text to bytes
    text_bytes = list(text.encode('ascii'))
    
    # Check if data is too large for NTAG215 tag (max 32 pages for user data)
    max_bytes = 32 * 4  # 32 pages * 4 bytes per page
    if len(text_bytes) > max_bytes:
        print(f"Data too large! Need {len(text_bytes)} bytes but only {max_bytes} available.")
        return False
    
    # Write data to NTAG215 pages (starting from page 4 to avoid reserved pages 0-3)
    success = reader.write_ntag215_data(text_bytes, start_page=4)
    
    if success:
        print(f"Written {len(text_bytes)} bytes to NTAG215 tag")
        print("NTAG215 tag write completed!")
        return True
    else:
        print("Failed to write to NTAG215 tag")
        return False

def main():
    parser = argparse.ArgumentParser(description='NTAG215 NFC tag reader/writer')
    parser.add_argument('-w', '--write', type=str, help='Data to write to the tag')
    args = parser.parse_args()
    
    reader = MFRC522()
    
    try:
        if args.write:
            # Write mode - write once
            print(f"Write mode: '{args.write}'")
            success = write_ntag215_tag(reader, args.write)
            if success:
                print("Write operation completed successfully!")
            else:
                print("Write operation failed!")
        else:
            # Read mode - read once
            print("Read mode: Place a tag to read")
            uid, text = read_ntag215_tag(reader)
            if uid:
                print(f"\nTag UID: {uid}")
                if text:
                    print(f"Data: {text}")
                else:
                    print("No readable data found on tag")
            else:
                print("Failed to read tag")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        reader.close()

if __name__ == "__main__":
    main()