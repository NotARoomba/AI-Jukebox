#!/usr/bin/env python3
"""
NFC Test Script - NDEF Record Reader/Writer

This script implements a complete NDEF library from scratch and provides
automatic NDEF record reading and writing capabilities.

Usage:
    python test.py           # Read only mode
    python test.py -w        # Read and write mode
    python test.py -w "Hello World"  # Read and write specific string
    python test.py -w "https://example.com" -t url  # Write URL record
"""

import sys
import time
import argparse
import RPi.GPIO as GPIO
from typing import List, Optional, Tuple, Dict, Any

# Import the local mfrc522 module
try:
    from mfrc522 import MFRC522
except ImportError:
    print("Error: Could not import mfrc522 module. Make sure you're running this from the firmware directory.")
    sys.exit(1)

class NDEFRecord:
    """Represents an NDEF record"""
    
    def __init__(self, record_type: str, payload: str, language: str = "en", id: str = ""):
        self.record_type = record_type
        self.payload = payload
        self.language = language
        self.id = id
    
    def __str__(self):
        return f"NDEFRecord(type={self.record_type}, payload='{self.payload}', lang={self.language})"

class NDEFMessage:
    """Represents an NDEF message containing multiple records"""
    
    def __init__(self, records: List[NDEFRecord] = None):
        self.records = records or []
    
    def add_record(self, record: NDEFRecord):
        """Add a record to the message"""
        self.records.append(record)
    
    def to_bytes(self) -> bytes:
        """Convert the NDEF message to bytes"""
        if not self.records:
            return b''
        
        message_bytes = bytearray()
        
        for i, record in enumerate(self.records):
            # NDEF record header
            header = 0x00
            
            # Set flags based on position
            if i == 0:  # First record
                header |= 0x80  # MB (Message Begin)
            if i == len(self.records) - 1:  # Last record
                header |= 0x40  # ME (Message End)
            
            # Set SR (Short Record) if payload is <= 255 bytes
            payload_bytes = record.payload.encode('utf-8')
            if record.record_type == "text":
                # Text records have language code
                lang_bytes = record.language.encode('utf-8')
                payload_bytes = bytes([0x02]) + lang_bytes + payload_bytes  # Status byte + lang + text
            
            if len(payload_bytes) <= 255:
                header |= 0x10  # SR (Short Record)
            
            # Set TNF (Type Name Format) - NFC Forum well-known type
            header |= 0x01  # TNF = 0x01
            
            message_bytes.append(header)
            
            # Type length
            type_bytes = record.record_type.encode('utf-8')
            message_bytes.append(len(type_bytes))
            
            # Payload length (short record)
            if len(payload_bytes) <= 255:
                message_bytes.append(len(payload_bytes))
            else:
                # Long record - 4 bytes for length
                message_bytes.extend(len(payload_bytes).to_bytes(4, 'big'))
            
            # ID length (if any)
            if record.id:
                id_bytes = record.id.encode('utf-8')
                message_bytes.append(len(id_bytes))
            else:
                message_bytes.append(0)
            
            # Type
            message_bytes.extend(type_bytes)
            
            # ID (if any)
            if record.id:
                message_bytes.extend(record.id.encode('utf-8'))
            
            # Payload
            message_bytes.extend(payload_bytes)
        
        return bytes(message_bytes)

class NDEFReader:
    """NDEF reader/writer for NFC tags"""
    
    def __init__(self):
        self.reader = MFRC522()
        self.reader.MFRC522_Init()
    
    def detect_tag(self) -> Tuple[Optional[bytes], Optional[int]]:
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
    
    def read_ndef_records(self, uid: bytes) -> List[NDEFRecord]:
        """Read NDEF records from the tag"""
        if not uid:
            return []
        
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            return []
        
        # Read data from blocks 4-15 (typical NDEF area)
        all_data = bytearray()
        
        for block_addr in range(4, 16):
            try:
                block_data = self.reader.MFRC522_Read(block_addr)
                if block_data:
                    all_data.extend(block_data)
                else:
                    break
            except Exception as e:
                print(f"Error reading block {block_addr}: {e}")
                break
        
        # Parse NDEF data
        return self.parse_ndef_data(all_data)
    
    def parse_ndef_data(self, data: bytes) -> List[NDEFRecord]:
        """Parse NDEF data and extract records"""
        records = []
        
        if not data or len(data) < 2:
            return records
        
        # Look for NDEF TLV structure
        # NDEF TLV starts with 0x03 followed by length
        i = 0
        while i < len(data) - 2:
            if data[i] == 0x03:  # NDEF TLV tag
                length = data[i + 1]
                if i + 2 + length <= len(data):
                    ndef_payload = data[i + 2:i + 2 + length]
                    parsed_records = self.parse_ndef_payload(ndef_payload)
                    records.extend(parsed_records)
                    i += 2 + length
                else:
                    break
            elif data[i] == 0xFE:  # Terminator TLV
                break
            else:
                i += 1
        
        return records
    
    def parse_ndef_payload(self, payload: bytes) -> List[NDEFRecord]:
        """Parse NDEF payload and extract records"""
        records = []
        
        if not payload or len(payload) < 3:
            return records
        
        i = 0
        while i < len(payload):
            if i + 3 > len(payload):
                break
            
            # Parse NDEF record header
            header = payload[i]
            i += 1
            
            # Check if this is the last record
            is_last_record = (header & 0x40) != 0
            is_short_record = (header & 0x10) != 0
            tnf = header & 0x07
            
            # Read type length
            if i >= len(payload):
                break
            type_length = payload[i]
            i += 1
            
            # Read payload length
            if is_short_record:
                if i >= len(payload):
                    break
                payload_length = payload[i]
                i += 1
            else:
                if i + 4 > len(payload):
                    break
                payload_length = int.from_bytes(payload[i:i+4], 'big')
                i += 4
            
            # Read ID length
            if i >= len(payload):
                break
            id_length = payload[i]
            i += 1
            
            # Read type
            if i + type_length > len(payload):
                break
            record_type = payload[i:i+type_length].decode('utf-8', errors='ignore')
            i += type_length
            
            # Read ID
            if id_length > 0:
                if i + id_length > len(payload):
                    break
                record_id = payload[i:i+id_length].decode('utf-8', errors='ignore')
                i += id_length
            else:
                record_id = ""
            
            # Read payload
            if i + payload_length > len(payload):
                break
            record_payload = payload[i:i+payload_length]
            i += payload_length
            
            # Parse payload based on type
            if record_type == "text":
                # Text record has language code
                if len(record_payload) >= 3:
                    status_byte = record_payload[0]
                    lang_length = status_byte & 0x3F
                    if len(record_payload) >= 1 + lang_length:
                        language = record_payload[1:1+lang_length].decode('utf-8', errors='ignore')
                        text_payload = record_payload[1+lang_length:].decode('utf-8', errors='ignore')
                        records.append(NDEFRecord("text", text_payload, language, record_id))
            elif record_type == "url":
                # URL record
                url_payload = record_payload.decode('utf-8', errors='ignore')
                records.append(NDEFRecord("url", url_payload, "", record_id))
            else:
                # Generic record
                generic_payload = record_payload.decode('utf-8', errors='ignore')
                records.append(NDEFRecord(record_type, generic_payload, "", record_id))
            
            if is_last_record:
                break
        
        return records
    
    def write_ndef_records(self, uid: bytes, records: List[NDEFRecord]) -> bool:
        """Write NDEF records to the tag"""
        if not uid or not records:
            return False
        
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            return False
        
        # Create NDEF message
        message = NDEFMessage(records)
        ndef_bytes = message.to_bytes()
        
        # Create TLV structure
        tlv_data = bytearray()
        tlv_data.append(0x03)  # NDEF TLV tag
        tlv_data.append(len(ndef_bytes))  # Length
        tlv_data.extend(ndef_bytes)
        tlv_data.append(0xFE)  # Terminator TLV
        
        # Pad to 16-byte blocks
        while len(tlv_data) % 16 != 0:
            tlv_data.append(0)
        
        # Write to blocks 4-15
        try:
            block_addr = 4
            for i in range(0, len(tlv_data), 16):
                if block_addr >= 16:  # Don't write beyond block 15
                    break
                
                block_data = tlv_data[i:i+16]
                if len(block_data) < 16:
                    block_data.extend([0] * (16 - len(block_data)))
                
                # Write the block
                try:
                    self.reader.MFRC522_Write(block_addr, block_data)
                    print(f"Wrote block {block_addr}: {block_data[:8]}...")
                except Exception as e:
                    print(f"Failed to write block {block_addr}: {e}")
                    return False
                
                block_addr += 1
            
            return True
            
        except Exception as e:
            print(f"Error writing: {e}")
            return False
    
    def write_text_record(self, uid: bytes, text: str, language: str = "en") -> bool:
        """Write a text NDEF record to the tag"""
        record = NDEFRecord("text", text, language)
        return self.write_ndef_records(uid, [record])
    
    def write_url_record(self, uid: bytes, url: str) -> bool:
        """Write a URL NDEF record to the tag"""
        record = NDEFRecord("url", url)
        return self.write_ndef_records(uid, [record])

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NDEF Record Reader/Writer')
    parser.add_argument('-w', '--write', nargs='?', const='Test Data', 
                       help='Write mode. If no string provided, writes "Test Data"')
    parser.add_argument('-t', '--type', choices=['text', 'url'], default='text',
                       help='Type of NDEF record to write (default: text)')
    parser.add_argument('-l', '--language', default='en',
                       help='Language code for text records (default: en)')
    args = parser.parse_args()

    # Initialize the NDEF reader
    print("Initializing NDEF reader...")
    reader = NDEFReader()
    
    print("NDEF Reader initialized successfully!")
    print("Place an NFC tag on the reader...")
    
    if args.write:
        print(f"Write mode enabled. Will write: '{args.write}' (type: {args.type})")
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
                if args.type == 'text':
                    success = reader.write_text_record(uid, args.write, args.language)
                elif args.type == 'url':
                    success = reader.write_url_record(uid, args.write)
                else:
                    success = reader.write_text_record(uid, args.write)
                
                if success:
                    print(f"✓ Successfully wrote {args.type} record to tag")
                else:
                    print(f"✗ Failed to write to tag")
            
            # Read mode
            print("Reading NDEF records...")
            records = reader.read_ndef_records(uid)
            
            if records:
                print(f"✓ Found {len(records)} NDEF record(s):")
                for i, record in enumerate(records, 1):
                    print(f"  Record {i}: {record}")
            else:
                print("✓ Tag detected but no NDEF records found")
            
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
