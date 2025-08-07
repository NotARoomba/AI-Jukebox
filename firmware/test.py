#!/usr/bin/env python3
"""
NFC Test Script - NDEF Record Reader/Writer

This script automatically listens for NFC tags and reads/writes NDEF records.
It handles both NTAG and Mifare Classic tags properly.

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

class NDEFReader:
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
    
    def read_ndef_records(self, uid):
        """Read NDEF records from the tag"""
        if not uid:
            return None, "No UID"
            
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            return None, "Failed to select tag"
        
        # Try to read NDEF data from different block addresses
        # For NTAG tags, NDEF data typically starts at block 4
        ndef_data = []
        text_data = ""
        
        # Read blocks 4-15 (typical NDEF area for NTAG)
        for block_addr in range(4, 16):
            try:
                # For NTAG tags, we don't need authentication
                block_data = self.reader.MFRC522_Read(block_addr)
                if block_data:
                    ndef_data.extend(block_data)
            except Exception as e:
                print(f"Error reading block {block_addr}: {e}")
                break
        
        # Try to parse NDEF data
        if ndef_data:
            text_data = self.parse_ndef_data(ndef_data)
        
        # If no NDEF data found, try reading as raw text
        if not text_data:
            text_data = self.parse_raw_data(ndef_data)
        
        return text_data, None
    
    def parse_ndef_data(self, data):
        """Parse NDEF data and extract text records"""
        if not data or len(data) < 2:
            return ""
        
        # Look for NDEF TLV structure
        # NDEF TLV starts with 0x03 followed by length
        for i in range(len(data) - 2):
            if data[i] == 0x03:  # NDEF TLV tag
                length = data[i + 1]
                if i + 2 + length <= len(data):
                    ndef_payload = data[i + 2:i + 2 + length]
                    return self.parse_ndef_payload(ndef_payload)
        
        return ""
    
    def parse_ndef_payload(self, payload):
        """Parse NDEF payload and extract text"""
        if not payload or len(payload) < 3:
            return ""
        
        # Check if it's a text record
        if payload[0] & 0x01:  # TNF = 0x01 (NFC Forum well-known type)
            if len(payload) > 3:
                # Skip header bytes and extract text
                text_start = 3
                if text_start < len(payload):
                    # Convert bytes to string, filtering out non-printable characters
                    text = ""
                    for byte in payload[text_start:]:
                        if 32 <= byte <= 126:  # Printable ASCII
                            text += chr(byte)
                        elif byte == 0:  # Null terminator
                            break
                    return text
        
        return ""
    
    def parse_raw_data(self, data):
        """Parse raw data as text"""
        if not data:
            return ""
        
        text = ""
        for byte in data:
            if 32 <= byte <= 126:  # Printable ASCII
                text += chr(byte)
            elif byte == 0:  # Null terminator
                break
        
        return text.strip()
    
    def write_ndef_record(self, uid, text):
        """Write NDEF text record to the tag"""
        if not uid:
            return False, "No UID"
        
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            return False, "Failed to select tag"
        
        # Create NDEF message
        ndef_message = self.create_ndef_message(text)
        
        # Write to blocks 4-15 (typical NDEF area)
        try:
            # Write NDEF TLV
            tlv_data = [0x03, len(ndef_message)] + ndef_message
            
            # Pad to 16-byte blocks
            while len(tlv_data) % 16 != 0:
                tlv_data.append(0)
            
            # Write to blocks
            block_addr = 4
            for i in range(0, len(tlv_data), 16):
                if block_addr >= 16:  # Don't write beyond block 15
                    break
                
                block_data = tlv_data[i:i+16]
                if len(block_data) < 16:
                    block_data.extend([0] * (16 - len(block_data)))
                
                status = self.reader.MFRC522_Write(block_addr, block_data)
                if status != self.reader.MI_OK:
                    return False, f"Failed to write block {block_addr}"
                
                block_addr += 1
            
            return True, "Success"
            
        except Exception as e:
            return False, f"Error writing: {e}"
    
    def create_ndef_message(self, text):
        """Create NDEF message for text record"""
        # NDEF message structure for text record
        text_bytes = text.encode('utf-8')
        
        # NDEF record header
        record_header = [
            0xD1,  # MB=1, ME=1, SR=1, TNF=1 (NFC Forum well-known type)
            0x01,  # Type length
            len(text_bytes) + 3,  # Payload length (text + language code + text)
            0x54,  # Type: 'T' for text
            0x02,  # Status byte (UTF-8, language code length = 2)
            0x65, 0x6E  # Language code: 'en'
        ]
        
        # Combine header and text
        ndef_message = record_header + list(text_bytes)
        
        return ndef_message

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NFC NDEF Record Reader/Writer')
    parser.add_argument('-w', '--write', nargs='?', const='Test Data', 
                       help='Write mode. If no string provided, writes "Test Data"')
    args = parser.parse_args()

    # Initialize the NFC reader
    print("Initializing NFC reader...")
    reader = NDEFReader()
    
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
                success, message = reader.write_ndef_record(uid, args.write)
                if success:
                    print(f"✓ Successfully wrote to tag")
                else:
                    print(f"✗ Failed to write to tag: {message}")
            
            # Read mode
            print("Reading tag data...")
            text_data, error = reader.read_ndef_records(uid)
            
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
