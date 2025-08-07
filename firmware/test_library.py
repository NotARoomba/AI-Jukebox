#!/usr/bin/env python

"""
Test script for the MFRC522 library
"""

import sys
import os
import time

# Add the mfrc522_new folder to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'mfrc522_new'))

try:
    from mfrc522_new import MFRC522, StatusCode, PICC_Type
    print("✓ Library imported successfully!")
except ImportError as e:
    print(f"✗ Error importing library: {e}")
    sys.exit(1)

def test_library():
    """Test the MFRC522 library"""
    print("Testing MFRC522 library...")
    
    try:
        # Initialize the reader
        reader = MFRC522(chip_select_pin=24, reset_power_down_pin=22)
        print("✓ MFRC522 initialized successfully!")
        
        # Test card detection
        print("Place an NFC card on the reader...")
        print("Press Ctrl+C to exit")
        
        while True:
            if reader.PICC_IsNewCardPresent():
                print("✓ Card detected!")
                
                if reader.PICC_ReadCardSerial():
                    uid = reader.uid
                    uid_str = ''.join([f'{b:02X}' for b in uid.uid_byte[:uid.size]])
                    print(f"✓ UID: {uid_str}")
                    
                    # Get card type
                    card_type = MFRC522.PICC_GetType(uid.sak)
                    card_type_name = MFRC522.PICC_GetTypeName(card_type)
                    print(f"✓ Card type: {card_type_name}")
                    
                    # Halt the card
                    reader.PICC_HaltA()
                    print("✓ Card halted")
                    break
                else:
                    print("✗ Failed to read card serial")
            else:
                print("Waiting for card...")
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'reader' in locals():
            del reader
        print("✓ Cleanup completed")

if __name__ == "__main__":
    test_library() 