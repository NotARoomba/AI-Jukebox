#!/usr/bin/env python
"""
Example script demonstrating NTAG215 tag reading and writing
using the new MFRC522 library with ISO 14443-3A Type A support.
"""

import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time

def main():
    """Main function demonstrating NTAG215 operations"""
    
    # Initialize the MFRC522 reader
    reader = MFRC522(debug_level='INFO')
    
    try:
        print("NTAG215 Reader/Writer Example")
        print("=============================")
        print("Place an NTAG215 tag near the reader...")
        
        # Wait for card detection
        while True:
            (status, back_bits) = reader.request(reader.PICC_REQIDL)
            if status == reader.MI_OK:
                print("Card detected!")
                break
            print("Waiting for card...")
            time.sleep(0.1)
        
        # Get UID
        (status, uid) = reader.anticoll()
        if status != reader.MI_OK:
            print("Failed to get UID")
            return
        
        print(f"Tag UID: {uid}")
        
        # Select the tag
        sak = reader.select_tag(uid)
        if sak == 0:
            print("Failed to select tag")
            return
        
        print(f"Tag selected (SAK: {sak})")
        
        # Read existing data
        print("\nReading existing data...")
        data_bytes = reader.read_ntag215_data(start_page=4, end_page=35)
        
        if data_bytes:
            # Remove trailing zeros
            while data_bytes and data_bytes[-1] == 0:
                data_bytes.pop()
            
            if data_bytes:
                # Convert to text, filtering out non-printable characters
                text = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
                print(f"Existing data: '{text}'")
            else:
                print("No readable data found")
        else:
            print("Failed to read data")
        
        # Example: Write some test data
        print("\nWriting test data...")
        test_data = "Hello NTAG215!".encode('ascii')
        test_bytes = list(test_data)
        
        # Clear the tag first
        print("Clearing tag...")
        if reader.clear_ntag215_data(start_page=4, end_page=35):
            print("Tag cleared successfully")
        else:
            print("Warning: Some pages may not have been cleared")
        
        # Write test data
        if reader.write_ntag215_data(test_bytes, start_page=4):
            print(f"Test data written successfully: '{test_data.decode('ascii')}'")
        else:
            print("Failed to write test data")
        
        # Read back the data to verify
        print("\nVerifying written data...")
        verify_bytes = reader.read_ntag215_data(start_page=4, end_page=35)
        
        if verify_bytes:
            # Remove trailing zeros
            while verify_bytes and verify_bytes[-1] == 0:
                verify_bytes.pop()
            
            if verify_bytes:
                verify_text = ''.join(chr(b) for b in verify_bytes if b >= 32 and b <= 126)
                print(f"Verified data: '{verify_text}'")
                
                if verify_text == test_data.decode('ascii'):
                    print("✓ Data verification successful!")
                else:
                    print("✗ Data verification failed!")
            else:
                print("No data found after writing")
        else:
            print("Failed to read back data")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        reader.close()
        print("\nReader closed")

if __name__ == "__main__":
    main() 