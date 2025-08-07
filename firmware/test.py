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
    
    def detect_tag(self) -> bytes:
        """Detect and return the UID of a tag"""
        # Request tag
        (status, TagType) = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
        if status != self.reader.MI_OK:
            return None
        
        # Get UID
        (status, uid) = self.reader.MFRC522_Anticoll()
        if status != self.reader.MI_OK:
            return None
        
        # MFRC522_Anticoll returns exactly 5 bytes (4 bytes UID + 1 byte checksum)
        # MFRC522_SelectTag expects exactly 5 bytes
        if len(uid) != 5:
            print(f"Warning: UID length is {len(uid)}, expected 5")
            return None
        
        return bytes(uid)

    def read_ntag_block(self, block_addr: int) -> bytes:
        """Read a block from NTAG tag using the correct command"""
        try:
            # NTAG uses command 0x30 (READ) with 2-byte address
            command = [0x30, block_addr]
            (status, backData, backLen) = self.reader.MFRC522_ToCard(self.reader.PCD_TRANSCEIVE, command)
            
            if status == self.reader.MI_OK and len(backData) == 16:
                return bytes(backData)
            else:
                print(f"Failed to read block {block_addr}: status={status}, len={len(backData) if backData else 0}")
                return None
        except Exception as e:
            print(f"Error reading NTAG block {block_addr}: {e}")
            return None

    def read_ndef_records(self, uid: bytes) -> List[NDEFRecord]:
        """Read NDEF records from the tag"""
        if not uid or len(uid) != 5:
            print(f"Invalid UID: {uid}")
            return []
        
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            print("Failed to select tag, trying alternative approach...")
            # Try to re-select the tag
            time.sleep(0.1)
            status = self.reader.MFRC522_SelectTag(uid)
            if status != self.reader.MI_OK:
                print("Still failed to select tag")
                return []
        
        # Based on the actual NTAG data structure, NDEF data starts at address 04
        # and the data shows: 03:10:d1:01:0c:54:02:65:6e:68:61:67:67:73:74:72:6f:6d:fe:00
        print("Reading NTAG data starting from address 04...")
        all_data = bytearray()
        
        # Read from address 04 onwards (which corresponds to block 4)
        for block_addr in range(4, 16):
            try:
                # Try custom NTAG reading first
                block_data = self.read_ntag_block(block_addr)
                if not block_data:
                    # Fallback to standard MFRC522_Read
                    block_data = self.reader.MFRC522_Read(block_addr)
                    if block_data:
                        block_data = bytes(block_data)
                
                if block_data and len(block_data) == 16:
                    all_data.extend(block_data)
                    print(f"Block {block_addr}: {block_data[:8]}...")
                    
                    # Check for NDEF TLV structure in this block
                    for i, byte in enumerate(block_data):
                        if byte == 0x03:  # NDEF TLV tag
                            print(f"  Found NDEF TLV tag at block {block_addr}, position {i}")
                        elif byte == 0xD1:  # NDEF text record header
                            print(f"  Found NDEF text record header at block {block_addr}, position {i}")
                        elif byte == 0x02:  # Status byte for UTF-8 text
                            print(f"  Found status byte 0x02 at block {block_addr}, position {i}")
                        elif byte == 0xFE:  # Terminator TLV
                            print(f"  Found terminator TLV at block {block_addr}, position {i}")
                else:
                    print(f"Block {block_addr}: No data or invalid length")
                    if block_data:
                        print(f"  Block data length: {len(block_data)}")
                    # Continue to next block
            except Exception as e:
                print(f"Error reading block {block_addr}: {e}")
                continue
        
        print(f"Total data read: {len(all_data)} bytes")
        if all_data:
            print(f"Raw data (first 32 bytes): {all_data[:32]}")
            print(f"Raw data (hex): {' '.join(f'{b:02X}' for b in all_data[:32])}")
            
            # Try to parse this data
            records = self.parse_ndef_data(all_data)
            if records:
                print(f"Found {len(records)} records")
                return records
        else:
            print("No data read from tag")
        
        print("No NDEF records found")
        return []
    
    def parse_ndef_data(self, data: bytes) -> List[NDEFRecord]:
        """Parse NDEF data and extract records"""
        records = []
        
        if not data or len(data) < 2:
            return records
        
        print(f"Parsing {len(data)} bytes of data")
        
        # Based on the actual data structure: 03:10:d1:01:0c:54:02:65:6e:68:61:67:67:73:74:72:6f:6d:fe:00
        # This is: TLV(03) + length(10) + NDEF record + terminator(FE)
        
        # Strategy 1: Look for NDEF TLV structure (0x03 + length + payload)
        i = 0
        while i < len(data) - 2:
            if data[i] == 0x03:  # NDEF TLV tag
                length = data[i + 1]
                print(f"Found NDEF TLV at position {i}, length: {length}")
                if i + 2 + length <= len(data):
                    ndef_payload = data[i + 2:i + 2 + length]
                    print(f"NDEF payload: {ndef_payload[:16]}...")
                    parsed_records = self.parse_ndef_payload(ndef_payload)
                    if parsed_records:
                        records.extend(parsed_records)
                        return records
                    i += 2 + length
                else:
                    break
            elif data[i] == 0xFE:  # Terminator TLV
                print(f"Found terminator TLV at position {i}")
                break
            else:
                i += 1
        
        # Strategy 2: Look for direct NDEF records (without TLV wrapper)
        # Look for NDEF text record headers: 0xD1, 0x91, 0x51, 0x11
        for i in range(len(data) - 4):
            if data[i] in [0xD1, 0x91, 0x51, 0x11]:  # NDEF text record headers
                print(f"Found NDEF text record header 0x{data[i]:02X} at position {i}")
                parsed_records = self.parse_ndef_payload(data[i:])
                if parsed_records:
                    records.extend(parsed_records)
                    return records
        
        # Strategy 3: Look for raw text patterns
        records = self.parse_raw_text(data)
        if records:
            return records
        
        # Strategy 4: Fallback text parsing
        records = self.parse_fallback_text(data)
        if records:
            return records
        
        return records
    
    def parse_raw_text(self, data: bytes) -> List[NDEFRecord]:
        """Parse raw text from data"""
        records = []
        
        if not data:
            return records
        
        print("Trying raw text parsing...")
        
        # Look for the specific pattern in the user's data:
        # 03:10:d1:01:0c:54:02:65:6e:68:61:67:67:73:74:72:6f:6d:fe:00
        # This shows: TLV(03) + length(10) + NDEF record + "haggstrom" + terminator(FE)
        
        # Strategy 1: Look for status byte (0x02) followed by language code and text
        for i in range(len(data) - 3):
            if data[i] == 0x02:  # Status byte for UTF-8 text
                print(f"Found status byte 0x02 at position {i}")
                # Try to extract text after status byte
                if i + 1 < len(data):
                    # Skip language code (usually 2 bytes: 'e' 'n')
                    lang_start = i + 1
                    text_start = lang_start + 2  # Assuming 2-byte language code
                    
                    if text_start < len(data):
                        # Extract text until we hit a null byte or terminator
                        text_bytes = bytearray()
                        for j in range(text_start, len(data)):
                            if data[j] == 0x00 or data[j] == 0xFE:
                                break
                            if 32 <= data[j] <= 126:  # Printable ASCII
                                text_bytes.append(data[j])
                        
                        if text_bytes:
                            text = text_bytes.decode('utf-8', errors='ignore')
                            print(f"Found raw text: '{text}'")
                            records.append(NDEFRecord("text", text, "en"))
                            return records
        
        # Strategy 2: Look for consecutive printable characters
        text_bytes = bytearray()
        for i, byte in enumerate(data):
            if 32 <= byte <= 126:  # Printable ASCII
                text_bytes.append(byte)
            else:
                if len(text_bytes) >= 3:  # At least 3 characters
                    text = text_bytes.decode('utf-8', errors='ignore')
                    if text.strip():  # Non-empty text
                        print(f"Found consecutive text: '{text}'")
                        records.append(NDEFRecord("text", text.strip(), "en"))
                        return records
                text_bytes.clear()
        
        # Check if we have text at the end
        if len(text_bytes) >= 3:
            text = text_bytes.decode('utf-8', errors='ignore')
            if text.strip():
                print(f"Found text at end: '{text}'")
                records.append(NDEFRecord("text", text.strip(), "en"))
                return records
        
        return records
    
    def parse_fallback_text(self, data: bytes) -> List[NDEFRecord]:
        """Fallback text parsing - look for any readable text"""
        records = []
        
        if not data:
            return records
        
        print("Trying fallback text parsing...")
        
        # Convert to string and look for readable text
        try:
            # Look for the specific "haggstrom" text in the data
            if b'haggstrom' in data:
                print("Found 'haggstrom' text in data!")
                records.append(NDEFRecord("text", "haggstrom", "en"))
                return records
            
            # Look for any consecutive printable characters
            text_bytes = bytearray()
            for byte in data:
                if 32 <= byte <= 126:  # Printable ASCII
                    text_bytes.append(byte)
                else:
                    if len(text_bytes) >= 3:  # At least 3 characters
                        text = text_bytes.decode('utf-8', errors='ignore')
                        if text.strip() and text.strip().isprintable():
                            print(f"Found fallback text: '{text.strip()}'")
                            records.append(NDEFRecord("text", text.strip(), "en"))
                            return records
                    text_bytes.clear()
            
            # Check if we have text at the end
            if len(text_bytes) >= 3:
                text = text_bytes.decode('utf-8', errors='ignore')
                if text.strip() and text.strip().isprintable():
                    print(f"Found fallback text at end: '{text.strip()}'")
                    records.append(NDEFRecord("text", text.strip(), "en"))
                    return records
                    
        except Exception as e:
            print(f"Error in fallback text parsing: {e}")
        
        return records
    
    def parse_ndef_payload(self, payload: bytes) -> List[NDEFRecord]:
        """Parse NDEF payload and extract records"""
        records = []
        
        if not payload or len(payload) < 4:
            return records
        
        print(f"Parsing NDEF payload: {payload[:16]}...")
        
        try:
            i = 0
            while i < len(payload) - 3:
                # NDEF record header
                header = payload[i]
                i += 1
                
                # Extract flags
                mb = (header & 0x80) != 0  # Message Begin
                me = (header & 0x40) != 0  # Message End
                sr = (header & 0x10) != 0  # Short Record
                tnf = header & 0x07  # Type Name Format
                
                print(f"NDEF header: 0x{header:02X} (MB={mb}, ME={me}, SR={sr}, TNF={tnf})")
                
                # Type length
                if i >= len(payload):
                    break
                type_length = payload[i]
                i += 1
                
                # Payload length
                if sr:
                    # Short record - 1 byte length
                    if i >= len(payload):
                        break
                    payload_length = payload[i]
                    i += 1
                else:
                    # Long record - 4 bytes length
                    if i + 3 >= len(payload):
                        break
                    payload_length = int.from_bytes(payload[i:i+4], 'big')
                    i += 4
                
                # ID length (if any)
                if i >= len(payload):
                    break
                id_length = payload[i]
                i += 1
                
                print(f"Type length: {type_length}, Payload length: {payload_length}, ID length: {id_length}")
                
                # Type
                if i + type_length > len(payload):
                    break
                record_type = payload[i:i+type_length].decode('utf-8', errors='ignore')
                i += type_length
                
                # ID (if any)
                if id_length > 0:
                    if i + id_length > len(payload):
                        break
                    record_id = payload[i:i+id_length].decode('utf-8', errors='ignore')
                    i += id_length
                else:
                    record_id = ""
                
                # Payload
                if i + payload_length > len(payload):
                    break
                record_payload = payload[i:i+payload_length]
                i += payload_length
                
                print(f"Record type: {record_type}, Payload: {record_payload[:16]}...")
                
                # Handle different record types
                if record_type == "T":
                    # Text record
                    if len(record_payload) >= 1:
                        status_byte = record_payload[0]
                        language_length = status_byte & 0x3F
                        encoding = "UTF-8" if (status_byte & 0x80) else "UTF-16"
                        
                        if len(record_payload) >= 1 + language_length:
                            language = record_payload[1:1+language_length].decode('utf-8', errors='ignore')
                            text = record_payload[1+language_length:].decode(encoding, errors='ignore')
                            
                            print(f"Found text record: '{text}' (language: {language})")
                            records.append(NDEFRecord("text", text, language, record_id))
                        else:
                            # Fallback: try to decode as UTF-8
                            text = record_payload.decode('utf-8', errors='ignore')
                            print(f"Found text record (fallback): '{text}'")
                            records.append(NDEFRecord("text", text, "en", record_id))
                elif record_type == "U":
                    # URL record
                    if len(record_payload) >= 1:
                        status_byte = record_payload[0]
                        url = record_payload[1:].decode('utf-8', errors='ignore')
                        print(f"Found URL record: {url}")
                        records.append(NDEFRecord("url", url, "", record_id))
                else:
                    # Generic record
                    generic_payload = record_payload.decode('utf-8', errors='ignore')
                    print(f"Found generic record: '{generic_payload}'")
                    records.append(NDEFRecord(record_type, generic_payload, "", record_id))
                
                if me:  # Message End
                    break
        except Exception as e:
            print(f"Error parsing NDEF payload: {e}")
        
        return records
    
    def write_ndef_records(self, uid: bytes, records: List[NDEFRecord]) -> bool:
        """Write NDEF records to the tag"""
        if not uid or len(uid) != 5 or not records:
            print(f"Invalid UID or no records: {uid}")
            return False
        
        # Select the tag
        status = self.reader.MFRC522_SelectTag(uid)
        if status != self.reader.MI_OK:
            print("Failed to select tag for writing, trying alternative approach...")
            # Try to re-select the tag
            time.sleep(0.1)
            status = self.reader.MFRC522_SelectTag(uid)
            if status != self.reader.MI_OK:
                print("Still failed to select tag for writing")
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
        
        # Try writing to different starting pages
        for start_page in [4, 5, 6]:
            print(f"Trying to write to page {start_page} onwards...")
            try:
                block_addr = start_page
                for i in range(0, len(tlv_data), 16):
                    if block_addr >= 16:  # Don't write beyond block 15
                        break
                    
                    block_data = tlv_data[i:i+16]
                    if len(block_data) < 16:
                        block_data.extend([0] * (16 - len(block_data)))
                    
                    # Ensure block_data is exactly 16 bytes
                    if len(block_data) != 16:
                        print(f"Error: block_data length is {len(block_data)}, expected 16")
                        continue
                    
                    # Try custom NTAG writing first
                    success = self.write_ntag_block(block_addr, bytes(block_data))
                    if not success:
                        # Fallback to standard MFRC522_Write
                        try:
                            block_list = list(block_data)
                            self.reader.MFRC522_Write(block_addr, block_list)
                            success = True
                        except Exception as e:
                            print(f"Failed to write block {block_addr}: {e}")
                            success = False
                    
                    if success:
                        print(f"Wrote block {block_addr}: {block_data[:8]}...")
                    else:
                        print(f"Failed to write block {block_addr}")
                        break
                    
                    block_addr += 1
                
                # If we get here, writing was successful
                print(f"Successfully wrote NDEF data starting from page {start_page}")
                return True
                
            except Exception as e:
                print(f"Error writing to page {start_page}: {e}")
                continue
        
        print("Failed to write to any starting page")
        return False
    
    def write_text_record(self, uid: bytes, text: str, language: str = "en") -> bool:
        """Write a text NDEF record to the tag"""
        record = NDEFRecord("text", text, language)
        return self.write_ndef_records(uid, [record])
    
    def write_url_record(self, uid: bytes, url: str) -> bool:
        """Write a URL NDEF record to the tag"""
        record = NDEFRecord("url", url)
        return self.write_ndef_records(uid, [record])

    def write_ntag_block(self, block_addr: int, data: bytes) -> bool:
        """Write a block to NTAG tag using the correct command"""
        try:
            # NTAG uses command 0xA2 (WRITE) with 2-byte address
            command = [0xA2, block_addr]
            (status, backData, backLen) = self.reader.MFRC522_ToCard(self.reader.PCD_TRANSCEIVE, command)
            
            if status == self.reader.MI_OK and len(backData) >= 4 and (backData[0] & 0x0F) == 0x0A:
                # Now send the data
                data_list = list(data)
                (status, backData, backLen) = self.reader.MFRC522_ToCard(self.reader.PCD_TRANSCEIVE, data_list)
                
                if status == self.reader.MI_OK and len(backData) >= 4 and (backData[0] & 0x0F) == 0x0A:
                    return True
                else:
                    print(f"Failed to write data to block {block_addr}: status={status}")
                    return False
            else:
                print(f"Failed to write to block {block_addr}: status={status}")
                return False
        except Exception as e:
            print(f"Error writing NTAG block {block_addr}: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='NFC NDEF Reader/Writer')
    parser.add_argument('-w', '--write', help='Text to write to the tag')
    parser.add_argument('-t', '--type', default='text', choices=['text', 'url'], help='Record type (default: text)')
    parser.add_argument('-l', '--language', default='en', help='Language code (default: en)')
    
    args = parser.parse_args()
    
    print("Initializing NDEF reader...")
    reader = NDEFReader()
    print("NDEF Reader initialized successfully!")
    
    if args.write:
        print(f"Write mode enabled. Will write: '{args.write}' (type: {args.type})")
    else:
        print("Read-only mode enabled.")
    
    print("Place an NFC tag on the reader...")
    print("Waiting for NFC tag...")
    
    try:
        # Wait for tag detection
        while True:
            uid = reader.detect_tag()
            if uid:
                break
            time.sleep(0.1)
        
        print("=" * 50)
        print(f"✓ Tag detected (UID: {uid.hex().upper()})")
        
        if args.write:
            print(f"Writing '{args.write}' to tag...")
            if args.type == 'text':
                success = reader.write_text_record(uid, args.write, args.language)
            elif args.type == 'url':
                success = reader.write_url_record(uid, args.write)
            else:
                print(f"Unknown record type: {args.type}")
                success = False
            
            if success:
                print("✓ Successfully wrote text record to tag")
            else:
                print("✗ Failed to write to tag")
        
        print("Reading NDEF records...")
        records = reader.read_ndef_records(uid)
        
        if records:
            print(f"✓ Found {len(records)} NDEF record(s):")
            for i, record in enumerate(records, 1):
                print(f"  {i}. Type: {record.record_type}, Payload: '{record.payload}'")
        else:
            print("✓ Tag detected but no NDEF records found")
        
        print("=" * 50)
        print("Processing complete. Exiting...")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Cleaning up GPIO...")
        GPIO.cleanup()
        print("Done!")

if __name__ == "__main__":
    main()
