#!/usr/bin/env python3
"""
NFC Test Script - Simple Reader/Writer

This script automatically listens for NFC tags and reads/writes data.
It handles both NTAG and Mifare Classic tags by reading/writing raw data.

Usage:
    python test.py           # Read only mode
    python test.py -w        # Read and write mode
    python test.py -w "Hello World"  # Read and write specific string
"""

import sys
import time
import argparse
import RPi.GPIO as GPIO

# Import the local mfrc522 module
try:
    from mfrc522 import MFRC522
except ImportError:
    print("Error: Could not import mfrc522 module. Make sure you're running this from the firmware directory.")
    sys.exit(1)

class SimpleNFCReader:
    def __init__(self):
        self.reader = MFRC522()
        self.reader.MFRC522_Init()
        
    def detect_tag(self):
        """Detect if a tag is present and return UID"""
        # Request for tag
        (status, TagType) = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
        if status != self.reader.MI_OK:
            return None, None
            
        # Anticollision
        (status, uid) = self.reader.MFRC522_Anticoll()
        if status != self.reader.MI_OK:
            return None, None
            
        return uid, TagType
    
    def read_data(self, uid):
        """Read data from the tag"""
        if not uid:
            return None, "No UID"
            
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            return None, "Failed to select tag"
        
        # Read data from blocks 4-15 (typical data area)
        all_data = []
        
        for block_addr in range(4, 16):
            try:
                block_data = self.reader.MFRC522_Read(block_addr)
                if block_data:
                    all_data.extend(block_data)
                else:
                    break  # Stop if no data returned
            except Exception as e:
                print(f"Error reading block {block_addr}: {e}")
                break
        
        # Convert data to text
        if all_data:
            text_data = self.bytes_to_text(all_data)
            return text_data, None
        else:
            return "", None
    
    def write_data(self, uid, text):
        """Write data to the tag"""
        if not uid:
            return False, "No UID"
        
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            return False, "Failed to select tag"
        
        # Convert text to bytes
        text_bytes = text.encode('utf-8')
        
        # Pad to 16-byte blocks
        data = list(text_bytes)
        while len(data) % 16 != 0:
            data.append(0)
        
        # Write to blocks 4-15
        try:
            block_addr = 4
            for i in range(0, len(data), 16):
                if block_addr >= 16:  # Don't write beyond block 15
                    break
                
                block_data = data[i:i+16]
                if len(block_data) < 16:
                    block_data.extend([0] * (16 - len(block_data)))
                
                # Write the block
                try:
                    self.reader.MFRC522_Write(block_addr, block_data)
                    print(f"Wrote block {block_addr}: {block_data[:8]}...")  # Show first 8 bytes
                except Exception as e:
                    return False, f"Failed to write block {block_addr}: {e}"
                
                block_addr += 1
            
            return True, "Success"
            
        except Exception as e:
            return False, f"Error writing: {e}"
    
    def bytes_to_text(self, data):
        """Convert bytes to text, filtering out non-printable characters"""
        if not data:
            return ""
        
        text = ""
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                text += chr(byte)
            elif byte == 0:  # Null terminator
                break
        
        return text.strip()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Simple NFC Reader/Writer')
    parser.add_argument('-w', '--write', nargs='?', const='Test Data', 
                       help='Write mode. If no string provided, writes "Test Data"')
    args = parser.parse_args()

    # Initialize the NFC reader
    print("Initializing NFC reader...")
    reader = SimpleNFCReader()
    
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
            
            # Detect tag
            uid, tag_type = reader.detect_tag()
            if not uid:
                time.sleep(0.1)
                continue
            
            uid_str = ''.join([f'{b:02X}' for b in uid])
            print(f"✓ Tag detected (UID: {uid_str})")
            
            if args.write:
                # Write mode
                print(f"Writing '{args.write}' to tag...")
                success, message = reader.write_data(uid, args.write)
                if success:
                    print(f"✓ Successfully wrote to tag")
                else:
                    print(f"✗ Failed to write to tag: {message}")
            
            # Read mode
            print("Reading tag data...")
            text_data, error = reader.read_data(uid)
            
            if error:
                print(f"✗ Error reading tag: {error}")
            elif text_data:
                print(f"✓ Tag data: '{text_data}'")
            else:
                print("✓ Tag detected but no readable data found")
            
            print("\n" + "="*50)
            print("Remove tag to continue...")
            
            # Wait for tag to be removed
            while True:
                uid_check, _ = reader.detect_tag()
                if not uid_check:
                    break
                time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
        print("Cleaning up GPIO...")
        GPIO.cleanup()
        print("Done!")

if __name__ == "__main__":
    main()
