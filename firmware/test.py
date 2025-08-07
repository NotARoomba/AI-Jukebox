#!/usr/bin/env python

import RPi.GPIO as GPIO
from mfrc522 import MFRC522, NTAGType, NDEFRecord
import time
import sys
import argparse

def read_ntag_tag(reader):
    """Read data from any NTAG tag"""
    print("Waiting for NTAG tag to read...")
    
    # Use the robust detection method
    while True:
        (success, uid, ntag_type) = reader.detect_ntag()
        if success:
            print(f"Card detected! UID: {uid}")
            print(f"NTAG Type: {ntag_type.name}")
            break
        print("Waiting for card...")
        time.sleep(0.1)
    
    # Get NTAG information
    ntag_info = reader.get_ntag_info(ntag_type)
    print(f"NTAG Info: {ntag_info['name']} - {ntag_info['user_bytes']} bytes available")
    
    # Try to read NDEF records first
    ndef_records = reader.read_ndef_records(ntag_type)
    if ndef_records:
        print(f"Found {len(ndef_records)} NDEF record(s):")
        text_data = ""
        for i, record in enumerate(ndef_records):
            print(f"  Record {i+1}: {record.record_type} - {record.payload}")
            if record.record_type == "text":
                text_data += record.payload
            elif record.record_type == "url":
                text_data += record.payload
            else:
                text_data += record.payload
        
        if text_data:
            return uid, text_data, ntag_type
    
    # Fallback to raw data reading
    data_bytes = reader.read_ntag_data(ntag_type)
    
    if data_bytes:
        # Remove trailing zeros
        while data_bytes and data_bytes[-1] == 0:
            data_bytes.pop()
        
        if data_bytes:
            # Convert to text, filtering out non-printable characters
            text = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
            return uid, text, ntag_type
        else:
            return uid, "", ntag_type
    else:
        return uid, "", ntag_type

def clear_ntag_tag(reader, ntag_type):
    """Clear all user data pages on an NTAG tag by writing zeros"""
    print("Clearing card data...")
    
    # Use the new clear method
    success = reader.clear_ntag_data(ntag_type)
    if success:
        ntag_info = reader.get_ntag_info(ntag_type)
        print(f"Cleared {ntag_info['name']} user data pages")
    else:
        print("Warning: Some pages may not have been cleared")
    
    return success

def write_ntag_tag(reader, text, record_type="text"):
    """Write data to any NTAG tag as NDEF record"""
    if not text:
        print("No data provided, exiting...")
        return False
    
    print("Now place your NTAG tag to write")
    
    # Use the robust detection method
    while True:
        (success, uid, ntag_type) = reader.detect_ntag()
        if success:
            print(f"Card detected! UID: {uid}")
            print(f"NTAG Type: {ntag_type.name}")
            break
        print("Waiting for card...")
        time.sleep(0.1)
    
    # Get NTAG information
    ntag_info = reader.get_ntag_info(ntag_type)
    print(f"NTAG Info: {ntag_info['name']} - {ntag_info['user_bytes']} bytes available")
    
    # Clear the card before writing
    clear_ntag_tag(reader, ntag_type)
    
    # Write as NDEF record
    if record_type == "text":
        success = reader.write_ndef_text(text, ntag_type)
    elif record_type == "url":
        success = reader.write_ndef_url(text, ntag_type)
    else:
        # Create custom NDEF record
        record = NDEFRecord(record_type, text)
        record.mb = True
        record.me = True
        success = reader.write_ndef_records([record], ntag_type)
    
    if success:
        print(f"Written {record_type} NDEF record to {ntag_type.name} tag")
        print("NTAG tag write completed!")
        return True
    else:
        print("Failed to write to NTAG tag")
        return False

def main():
    parser = argparse.ArgumentParser(description='NTAG NFC tag reader/writer with NDEF support (supports all NTAG types)')
    parser.add_argument('-w', '--write', type=str, help='Data to write to the tag')
    parser.add_argument('-t', '--type', type=str, default='text', choices=['text', 'url', 'uri'], help='Type of NDEF record to write (default: text)')
    parser.add_argument('-i', '--info', action='store_true', help='Show NTAG type information')
    parser.add_argument('-n', '--ndef', action='store_true', help='Show NDEF record details')
    args = parser.parse_args()
    
    reader = MFRC522()
    
    try:
        if args.write:
            # Write mode - write once
            print(f"Write mode: '{args.write}' as {args.type} NDEF record")
            success = write_ntag_tag(reader, args.write, args.type)
            if success:
                print("Write operation completed successfully!")
            else:
                print("Write operation failed!")
        else:
            # Read mode - read once
            print("Read mode: Place a tag to read")
            uid, text, ntag_type = read_ntag_tag(reader)
            if uid:
                print(f"\nTag UID: {uid}")
                print(f"NTAG Type: {ntag_type.name}")
                
                if args.info:
                    ntag_info = reader.get_ntag_info(ntag_type)
                    print(f"NTAG Information:")
                    print(f"  Name: {ntag_info['name']}")
                    print(f"  Total Pages: {ntag_info['pages']}")
                    print(f"  User Pages: {ntag_info['user_pages'][0]}-{ntag_info['user_pages'][1]}")
                    print(f"  User Bytes: {ntag_info['user_bytes']}")
                    print(f"  UID Length: {ntag_info['uid_length']}")
                
                if args.ndef:
                    # Show NDEF record details
                    ndef_records = reader.read_ndef_records(ntag_type)
                    if ndef_records:
                        print(f"\nNDEF Records ({len(ndef_records)} found):")
                        for i, record in enumerate(ndef_records):
                            print(f"  Record {i+1}:")
                            print(f"    Type: {record.record_type}")
                            print(f"    Payload: {record.payload}")
                            if record.record_type == "text":
                                print(f"    Language: {record.language}")
                            print(f"    Flags: MB={record.mb}, ME={record.me}, SR={record.sr}, CF={record.cf}")
                    else:
                        print("\nNo NDEF records found")
                
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