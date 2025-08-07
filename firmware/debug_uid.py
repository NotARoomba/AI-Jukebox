#!/usr/bin/env python
"""
Debug script to help identify UID issues with NTAG215 tags
"""

import RPi.GPIO as GPIO
from mfrc522 import MFRC522
import time

def debug_uid():
    """Debug UID detection issues"""
    
    # Initialize the MFRC522 reader with debug logging
    reader = MFRC522(debug_level='DEBUG')
    
    try:
        print("NTAG215 UID Debug")
        print("=================")
        print("Place an NTAG215 tag near the reader...")
        
        # Wait for card detection
        print("\n1. Requesting card detection...")
        while True:
            (status, back_bits) = reader.request(reader.PICC_REQIDL)
            print(f"   Request status: {status}, back_bits: {back_bits}")
            if status == reader.MI_OK:
                print("   ✓ Card detected!")
                break
            print("   Waiting for card...")
            time.sleep(0.5)
        
        # Get UID
        print("\n2. Attempting anticollision...")
        (status, uid) = reader.anticoll()
        print(f"   Anticollision status: {status}")
        print(f"   UID data: {uid}")
        
        if status == reader.MI_OK and uid:
            print(f"   ✓ UID obtained: {uid}")
            
            # Select the tag
            print("\n3. Selecting tag...")
            sak = reader.select_tag(uid)
            print(f"   Select status (SAK): {sak}")
            
            if sak != 0:
                print("   ✓ Tag selected successfully!")
                
                # Try to read a page to verify communication
                print("\n4. Testing page read...")
                page_data = reader.read_ntag215_page(4)
                if page_data:
                    print(f"   ✓ Page 4 data: {page_data}")
                else:
                    print("   ✗ Failed to read page 4")
            else:
                print("   ✗ Failed to select tag")
        else:
            print("   ✗ Failed to get UID")
            
            # Try alternative approach
            print("\n5. Trying alternative anticollision approach...")
            reader.write_register(reader.BitFramingReg, 0x00)
            (status, uid) = reader.anticoll()
            print(f"   Alternative anticollision status: {status}")
            print(f"   Alternative UID data: {uid}")
        
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
    debug_uid() 