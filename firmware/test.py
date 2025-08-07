#!/usr/bin/env python

import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time
import sys
import argparse

def read_ultralight_tag(reader):
    """Read data from an ultralight tag"""
    print("Waiting for ultralight tag to read...")
    
    # Wait for card detection (single attempt)
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
    
    # Read data from ultralight pages (starting from page 4 to avoid reserved pages 0-3)
    data_bytes = []
    buffer_size = 4  # 4 bytes per page for ultralight tags
    
    # Read up to 32 pages (pages 4-35) - user data area
    for page_addr in range(4, 36):  # Start reading from page 4
        # Use the standard read command but handle 4-byte response for ultralight
        recvData = []
        recvData.append(reader.PICC_READ)
        recvData.append(page_addr)
        pOut = reader.CalulateCRC(recvData)
        recvData.append(pOut[0])
        recvData.append(pOut[1])
        (status, backData, backLen) = reader.MFRC522_ToCard(reader.PCD_TRANSCEIVE, recvData)
        
        if status == reader.MI_OK and len(backData) >= buffer_size:
            # For ultralight tags, we get exactly 4 bytes per page
            page_data = backData[:buffer_size]  # Take exactly 4 bytes
            data_bytes.extend(page_data)
        else:
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

def clear_ultralight_tag(reader, start_page=4, end_page=35):
    """Clear all user data pages on an ultralight tag by writing zeros"""
    print("Clearing card data...")
    
    # Clear all user data pages (4-35) with zeros
    pages_cleared = 0
    for page_addr in range(start_page, end_page + 1):
        try:
            # Create a 4-byte zero buffer
            zero_data = [0x00, 0x00, 0x00, 0x00]
            
            # Write zeros to the page
            reader.MFRC522_WriteUltralight(page_addr, zero_data)
            
            # Small delay to ensure write completes
            time.sleep(0.1)
            pages_cleared += 1
            
        except Exception as e:
            print(f"Warning: Failed to clear page {page_addr}: {e}")
            # Continue with next page
    
    print(f"Cleared {pages_cleared} pages ({start_page} to {end_page})")

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
    
    # Clear the card before writing
    clear_ultralight_tag(reader)
    
    # Convert text to bytes and pad to 4-byte chunks
    text_bytes = text.encode('ascii')
    buffer_size = 4  # 4 bytes per page for ultralight tags
    
    # Check if data is too large for ultralight tag (max 36 pages, starting from page 4)
    max_pages = 32  # Pages 4-35 are available for user data
    required_pages = (len(text_bytes) + buffer_size - 1) // buffer_size  # Round up division
    
    if required_pages > max_pages:
        print(f"Data too large! Need {required_pages} pages but only {max_pages} available.")
        print(f"Maximum data size: {max_pages * buffer_size} bytes")
        return False
    
    # Write data to ultralight pages (starting from page 4 to avoid reserved pages 0-3)
    page_addr = 4  # Start writing from page 4
    bytes_written = 0
    pages_written = 0
    
    for i in range(0, len(text_bytes), buffer_size):
        # Get exactly 4 bytes for this page
        page_data = list(text_bytes[i:i+buffer_size])
        
        # Pad with zeros if less than 4 bytes to ensure exact buffer_size
        while len(page_data) < buffer_size:
            page_data.append(0)
        
        # Ensure we only write exactly 4 bytes
        page_data = page_data[:buffer_size]
        
        # Write to ultralight page (starting from page 4)
        reader.MFRC522_WriteUltralight(page_addr, page_data)
        
        # Small delay to ensure write completes
        time.sleep(0.1)
        
        page_addr += 1
        bytes_written += len(page_data)
        pages_written += 1
        
        # Stop if we've written all the data
        if i + buffer_size >= len(text_bytes):
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
            # Write mode - write once
            print(f"Write mode: '{args.write}'")
            success = write_ultralight_tag(reader, args.write)
            if success:
                print("Write operation completed successfully!")
            else:
                print("Write operation failed!")
        else:
            # Read mode - read once
            print("Read mode: Place a tag to read")
            uid, text = read_ultralight_tag(reader)
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
        GPIO.cleanup()

if __name__ == "__main__":
    main()