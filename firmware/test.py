#!/usr/bin/env python

import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time
import sys
import argparse

def read_ultralight_tag(reader):
    """Read data from an ultralight tag"""
    print("Waiting for ultralight tag to read...")
    
    # Wait for card detection
    while True:
        (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
        if status == reader.MI_OK:
            print("Card detected!")
            break
        print("Waiting for card...")
        time.sleep(0.1)
    
    # Get UID
    (status, uid) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        print("Failed to get UID")
        return None, None
    
    print(f"UID: {uid}")
    
    # Select the tag
    reader.MFRC522_SelectTag(uid)
    
    # Read data from ultralight pages (starting from page 4)
    data_bytes = []
    
    # Read up to 32 pages (pages 4-35) - user data area
    for page_addr in range(4, 36):
        print(f"Reading page {page_addr}...")
        
        # Use the standard read command but handle 4-byte response for ultralight
        recvData = []
        recvData.append(reader.PICC_READ)
        recvData.append(page_addr)
        pOut = reader.CalulateCRC(recvData)
        recvData.append(pOut[0])
        recvData.append(pOut[1])
        (status, backData, backLen) = reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, recvData)
        
        if status == reader.MI_OK and len(backData) >= 4:
            # For ultralight tags, we get 4 bytes per page
            page_data = backData[:4]  # Take first 4 bytes
            data_bytes.extend(page_data)
            print(f"Page {page_addr}: {page_data}")
        else:
            print(f"Failed to read page {page_addr} or no data")
            # If we can't read a page, assume we've reached the end
            break
    
    # Convert bytes to text
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

def write_ultralight_tag(reader, text):
    """Write data to an ultralight tag"""
    if not text:
        print("No data provided, exiting...")
        return False
    
    print("Now place your ultralight tag to write")
    
    # Wait for card detection
    while True:
        (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
        if status == reader.MI_OK:
            print("Card detected!")
            break
        print("Waiting for card...")
        time.sleep(0.1)
    
    # Get UID
    (status, uid) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        print("Failed to get UID")
        return False
    
    print(f"UID: {uid}")
    
    # Select the tag
    reader.MFRC522_SelectTag(uid)
    
    # Convert text to bytes and pad to 4-byte chunks
    text_bytes = text.encode('ascii')
    
    # Check if data is too large for ultralight tag (max 36 pages, starting from page 4)
    max_pages = 32  # Pages 4-35 are available for user data
    required_pages = (len(text_bytes) + 3) // 4  # Round up division
    
    if required_pages > max_pages:
        print(f"Data too large! Need {required_pages} pages but only {max_pages} available.")
        print(f"Maximum data size: {max_pages * 4} bytes")
        return False
    
    # Write data to ultralight pages (starting from page 4 to avoid reserved pages)
    page_addr = 4
    bytes_written = 0
    pages_written = 0
    
    for i in range(0, len(text_bytes), 4):
        # Get 4 bytes for this page
        page_data = list(text_bytes[i:i+4])
        
        # Pad with zeros if less than 4 bytes
        while len(page_data) < 4:
            page_data.append(0)
        
        print(f"Writing page {page_addr}: {page_data}")
        
        # Write to ultralight page
        reader.MFRC522_WriteUltralight(page_addr, page_data)
        
        # Small delay to ensure write completes
        time.sleep(0.1)
        
        page_addr += 1
        bytes_written += len(page_data)
        pages_written += 1
        
        # Stop if we've written all the data
        if i + 4 >= len(text_bytes):
            break
    
    print(f"Written {bytes_written} bytes to {pages_written} pages on ultralight tag")
    print("Ultralight tag write completed!")
    return True

def main():
    parser = argparse.ArgumentParser(description='Ultralight NFC tag reader/writer')
    parser.add_argument('-w', '--write', type=str, help='Data to write to the tag')
    args = parser.parse_args()
    
    reader = MFRC522()
    
    try:
        if args.write:
            # Write mode
            print(f"Write mode: '{args.write}'")
            success = write_ultralight_tag(reader, args.write)
            if success:
                print("Write operation completed successfully!")
            else:
                print("Write operation failed!")
        else:
            # Read mode (default)
            print("Read mode: Press Ctrl+C to exit")
            while True:
                try:
                    uid, text = read_ultralight_tag(reader)
                    if uid:
                        print(f"\nTag UID: {uid}")
                        if text:
                            print(f"Data: {text}")
                        else:
                            print("No readable data found on tag")
                    else:
                        print("Failed to read tag")
                    
                    print("\n" + "="*50)
                    print("Place another tag to read, or press Ctrl+C to exit")
                    
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    print(f"Error reading tag: {e}")
                    time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()