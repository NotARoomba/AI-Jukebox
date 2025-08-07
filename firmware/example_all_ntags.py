#!/usr/bin/env python
"""
Example script demonstrating reading and writing to all NTAG types
using the new comprehensive MFRC522 library.
"""

import RPi.GPIO as GPIO
from mfrc522 import MFRC522, NTAGType
import time

def main():
    """Main function demonstrating all NTAG operations"""
    
    # Initialize the MFRC522 reader
    reader = MFRC522(debug_level='INFO')
    
    try:
        print("NTAG Reader/Writer Example (All NTAG Types)")
        print("===========================================")
        print("Place any NTAG tag near the reader...")
        
        # Wait for card detection
        while True:
            (success, uid, ntag_type) = reader.detect_ntag()
            if success:
                print(f"✓ {ntag_type.name} detected!")
                print(f"UID: {uid}")
                break
            print("Waiting for card...")
            time.sleep(0.5)
        
        # Get NTAG information
        ntag_info = reader.get_ntag_info(ntag_type)
        print(f"\nNTAG Information:")
        print(f"  Name: {ntag_info['name']}")
        print(f"  Total Pages: {ntag_info['pages']}")
        print(f"  User Pages: {ntag_info['user_pages'][0]}-{ntag_info['user_pages'][1]}")
        print(f"  User Bytes: {ntag_info['user_bytes']}")
        print(f"  UID Length: {ntag_info['uid_length']}")
        
        # Read existing data
        print("\nReading existing data...")
        data_bytes = reader.read_ntag_data(ntag_type)
        
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
        test_data = f"Hello {ntag_type.name}!".encode('ascii')
        test_bytes = list(test_data)
        
        # Check if data fits
        if len(test_bytes) > ntag_info['user_bytes']:
            print(f"Test data too large for {ntag_type.name}")
            return
        
        # Clear the tag first
        print("Clearing tag...")
        if reader.clear_ntag_data(ntag_type):
            print("Tag cleared successfully")
        else:
            print("Warning: Some pages may not have been cleared")
        
        # Write test data
        if reader.write_ntag_data(test_bytes, ntag_type):
            print(f"Test data written successfully: '{test_data.decode('ascii')}'")
        else:
            print("Failed to write test data")
            return
        
        # Read back the data to verify
        print("\nVerifying written data...")
        verify_bytes = reader.read_ntag_data(ntag_type)
        
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
        
        # Demonstrate page-by-page reading
        print(f"\nPage-by-page reading (pages {ntag_info['user_pages'][0]}-{ntag_info['user_pages'][1]}):")
        for page in range(ntag_info['user_pages'][0], min(ntag_info['user_pages'][0] + 5, ntag_info['user_pages'][1] + 1)):
            page_data = reader.read_ntag_page(page)
            if page_data:
                # Convert to hex for display
                hex_data = ' '.join([f'{b:02X}' for b in page_data])
                print(f"  Page {page:3d}: {hex_data}")
            else:
                print(f"  Page {page:3d}: Failed to read")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reader.close()
        print("\nReader closed")

if __name__ == "__main__":
    main() 