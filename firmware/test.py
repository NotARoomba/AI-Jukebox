#!/usr/bin/env python3
"""
NTAG215 RFID Tag Reader/Writer
Supports reading and writing to NTAG215 NFC tags using MFRC522 module.
"""

import RPi.GPIO as GPIO
import argparse
import sys
import time
from datetime import datetime
from mfrc522 import MFRC522

class NTAG215Reader:
    def __init__(self):
        self.reader = MFRC522()
        self.ntag215_uid = None
        
    def detect_ntag215(self):
        """Detect and authenticate NTAG215 tag"""
        try:
            # Request card detection
            status, _ = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
            if status != self.reader.MI_OK:
                return False, None
                
            # Anticollision
            status, uid_data = self.reader.MFRC522_Anticoll()
            if status != self.reader.MI_OK:
                return False, None
                
            # Convert UID to hex string
            uid = ':'.join([hex(x)[2:].upper().zfill(2) for x in uid_data])
            
            # NTAG215 typically has 7-byte UID, but we'll be more flexible
            # Check if it's a valid NFC tag (4-7 bytes UID)
            if 4 <= len(uid_data) <= 7:
                self.ntag215_uid = uid
                return True, uid
            else:
                return False, uid
                
        except Exception as e:
            print(f"Error detecting tag: {e}")
            return False, None
    
    def read_ntag215(self):
        """Read data from NTAG215 tag"""
        if not self.ntag215_uid:
            return None
            
        try:
            # NTAG215 has 36 pages (0-35), each page is 4 bytes
            # Pages 0-3 contain manufacturer data and UID
            # Pages 4-35 contain user data (128 bytes total)
            
            data = []
            for page in range(4, 36):  # Read user data pages
                try:
                    result = self.reader.MFRC522_Read(page)
                    # Handle different return formats
                    if isinstance(result, tuple):
                        if len(result) >= 2:
                            status, page_data = result[0], result[1]
                        else:
                            print(f"Unexpected return format from MFRC522_Read: {result}")
                            break
                    else:
                        print(f"Unexpected return type from MFRC522_Read: {type(result)}")
                        break
                        
                    if status == self.reader.MI_OK:
                        data.extend(page_data)
                    else:
                        print(f"Failed to read page {page}")
                        break
                except Exception as e:
                    print(f"Error reading page {page}: {e}")
                    break
            
            # Convert to string, removing null bytes and invalid characters
            text = ''
            for byte in data:
                if byte != 0 and 32 <= byte <= 126:  # Printable ASCII
                    text += chr(byte)
            
            return text.strip()
            
        except Exception as e:
            print(f"Error reading tag: {e}")
            return None
    
    def write_ntag215(self, text):
        """Write data to NTAG215 tag"""
        if not self.ntag215_uid:
            print("No NTAG215 tag detected")
            return False
            
        try:
            # Convert text to bytes
            text_bytes = text.encode('utf-8')
            
            # NTAG215 can store up to 128 bytes of user data
            if len(text_bytes) > 128:
                print(f"Text too long ({len(text_bytes)} bytes). Maximum is 128 bytes.")
                return False
            
            # Pad with null bytes to 128 bytes
            padded_data = text_bytes + b'\x00' * (128 - len(text_bytes))
            
            # Write data to pages 4-35
            page = 4
            for i in range(0, len(padded_data), 4):
                page_data = padded_data[i:i+4]
                # Pad to 4 bytes if needed
                while len(page_data) < 4:
                    page_data += b'\x00'
                
                try:
                    result = self.reader.MFRC522_Write(page, list(page_data))
                    # Handle different return formats
                    if isinstance(result, (int, bool)):
                        status = result
                    elif isinstance(result, tuple) and len(result) > 0:
                        status = result[0]
                    else:
                        print(f"Unexpected return format from MFRC522_Write: {result}")
                        return False
                        
                    if status != self.reader.MI_OK:
                        print(f"Failed to write page {page}")
                        return False
                except Exception as e:
                    print(f"Error writing page {page}: {e}")
                    return False
                page += 1
                
            print(f"Successfully wrote {len(text_bytes)} bytes to tag")
            return True
            
        except Exception as e:
            print(f"Error writing to tag: {e}")
            return False
    
    def cleanup(self):
        """Clean up GPIO"""
        GPIO.cleanup()

def main():
    parser = argparse.ArgumentParser(description='NTAG215 RFID Tag Reader/Writer')
    parser.add_argument('--write', '-w', type=str, help='Text to write to the tag')
    parser.add_argument('--read-only', '-r', action='store_true', help='Only read tags, do not write')
    parser.add_argument('--continuous', '-c', action='store_true', help='Continuous reading mode')
    
    args = parser.parse_args()
    
    reader = NTAG215Reader()
    last_uid = None
    
    try:
        print("NTAG215 RFID Tag Reader/Writer")
        print("=" * 40)
        
        while True:
            print("\nHold an NTAG215 tag near the reader...")
            
            # Detect tag
            detected, uid = reader.detect_ntag215()
            
            if detected:
                if uid != last_uid:  # New tag detected
                    print(f"\nNTAG215 Tag Detected!")
                    print(f"UID: {uid}")
                    print(f"Timestamp: {datetime.now().isoformat()}")
                    
                    # Read current data
                    current_data = reader.read_ntag215()
                    if current_data:
                        print(f"Current Data: {current_data}")
                    else:
                        print("No data found on tag")
                    
                    # Write data if requested
                    if args.write and not args.read_only:
                        print(f"\nWriting '{args.write}' to tag...")
                        if reader.write_ntag215(args.write):
                            print("Write successful!")
                            # Read again to confirm
                            new_data = reader.read_ntag215()
                            if new_data:
                                print(f"Updated Data: {new_data}")
                        else:
                            print("Write failed!")
                    elif args.write and args.read_only:
                        print("Write argument provided but --read-only flag is set. Skipping write operation.")
                    
                    print("-" * 40)
                    last_uid = uid
                    
                    if not args.continuous:
                        break
                else:
                    # Same tag, just wait
                    time.sleep(0.1)
            else:
                # No tag detected
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        reader.cleanup()

if __name__ == "__main__":
    main()