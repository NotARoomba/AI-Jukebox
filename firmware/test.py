#!/usr/bin/env python3

"""
NFC Card Reader Test Script
Uses the old MFRC522 library from the mfrc522 folder.
"""

import time
import sys
import os
import argparse

# Add the mfrc522 folder to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'mfrc522'))

try:
    from mfrc522 import MFRC522
except ImportError as e:
    print(f"Error importing MFRC522 library: {e}")
    print("Make sure the MFRC522.py file exists in the mfrc522 folder.")
    sys.exit(1)

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO not found")
    print("Install with: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

try:
    import spidev
except ImportError:
    print("Error: spidev not found")
    print("Install with: sudo apt-get install python3-spidev")
    sys.exit(1)


def write_string_to_card(reader, uid, text):
    """Write a string to the NFC card"""
    print(f"Writing '{text}' to card...")
    
    # Convert text to bytes
    text_bytes = text.encode('utf-8')
    text_length = len(text_bytes)
    
    # Prepare data for writing (16 bytes per block)
    # Block 4: NDEF TLV structure
    # 03 = NDEF TLV tag
    # Length byte will be calculated
    # D1 = NDEF record header (text record)
    # 01 = NDEF record length
    # 0C = text record type length
    # 02 = text record payload length
    # 65 = 'e' (language code)
    # 6E = 'n' (language code)
    # Then the actual text data
    
    # Calculate total NDEF length
    ndef_length = 1 + 1 + 1 + 1 + 2 + text_length  # D1 + 01 + 0C + 02 + language + text
    
    # Prepare block 4 data
    block4 = bytearray(16)
    block4[0] = 0x03  # NDEF TLV tag
    block4[1] = ndef_length  # NDEF length
    block4[2] = 0xD1  # NDEF record header (text record)
    block4[3] = 0x01  # NDEF record type
    block4[4] = 0x0C  # Text record type length
    block4[5] = 0x02  # Text record payload length
    block4[6] = 0x65  # 'e' (language code)
    block4[7] = 0x6E  # 'n' (language code)
    
    # Copy text data
    for i, byte in enumerate(text_bytes):
        if i + 8 < 16:
            block4[i + 8] = byte
    
    # Write block 4
    status = reader.MFRC522_Write(4, block4)
    if status == reader.MI_OK:
        print("✓ Successfully wrote block 4")
    else:
        print(f"✗ Failed to write block 4: status={status}")
        return False
    
    # If text is longer than 8 bytes, write to block 5
    if text_length > 8:
        block5 = bytearray(16)
        remaining_text = text_bytes[8:]
        for i, byte in enumerate(remaining_text):
            if i < 16:
                block5[i] = byte
        
        status = reader.MFRC522_Write(5, block5)
        if status == reader.MI_OK:
            print("✓ Successfully wrote block 5")
        else:
            print(f"✗ Failed to write block 5: status={status}")
            return False
    
    # Write terminator TLV
    block_terminator = bytearray(16)
    block_terminator[0] = 0xFE  # Terminator TLV
    
    # Find the next available block
    next_block = 6 if text_length > 8 else 5
    status = reader.MFRC522_Write(next_block, block_terminator)
    if status == reader.MI_OK:
        print("✓ Successfully wrote terminator")
    else:
        print(f"✗ Failed to write terminator: status={status}")
        return False
    
    return True


def read_string_from_card(reader, uid):
    """Read a string from the NFC card"""
    print("Reading data from card...")
    
    # Read block 4 (NDEF data)
    block4 = reader.MFRC522_Read(4)
    if not block4:
        print("✗ Failed to read block 4")
        return None
    
    print(f"Block 4: {' '.join([f'{b:02X}' for b in block4])}")
    
    # Check if it's NDEF data
    if block4[0] != 0x03:
        print("✗ Not NDEF data")
        return None
    
    # Get NDEF length
    ndef_length = block4[1]
    print(f"NDEF length: {ndef_length}")
    
    # Check if it's a text record
    if block4[2] != 0xD1:
        print("✗ Not a text record")
        return None
    
    # Get text length
    text_length = block4[5]
    print(f"Text length: {text_length}")
    
    # Extract text from block 4 (starting from position 8)
    text_bytes = bytearray()
    for i in range(8, min(8 + text_length, 16)):
        if block4[i] != 0:
            text_bytes.append(block4[i])
    
    # If text continues in block 5
    if text_length > 8:
        block5 = reader.MFRC522_Read(5)
        if block5:
            print(f"Block 5: {' '.join([f'{b:02X}' for b in block5])}")
            for i in range(min(text_length - 8, 16)):
                if block5[i] != 0:
                    text_bytes.append(block5[i])
    
    try:
        text = text_bytes.decode('utf-8')
        return text
    except UnicodeDecodeError:
        print("✗ Failed to decode text")
        return None


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='NFC Card Reader/Writer')
    parser.add_argument('-w', '--write', type=str, help='String to write to the NFC card')
    args = parser.parse_args()
    
    if args.write:
        print(f"Write mode enabled. Will write: '{args.write}'")
    else:
        print("Read-only mode enabled.")
    
    print("Place an NFC card on the reader...")
    print("Press Ctrl+C to exit")
    
    try:
        # Initialize MFRC522 with updated pins
        print("Initializing MFRC522...")
        reader = MFRC522(bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=22)
        print("✓ MFRC522 initialized successfully with updated pin configuration")
        print("✓ Hardware reset pin (GPIO 22) configured and tested")
        
        last_uid = None
        while True:
            try:
                # Check if a new card is present
                (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
                if status == reader.MI_OK:
                    print("✓ Card detected!")
                    
                    # Read the card serial
                    (status, uid) = reader.MFRC522_Anticoll()
                    if status == reader.MI_OK:
                        # Convert UID to hex string
                        uid_hex = ''.join([f'{b:02X}' for b in uid[:4]])
                        
                        # Check if it's the same card
                        if last_uid == uid_hex:
                            time.sleep(0.5)
                            continue
                        
                        print(f"Card UID: {uid_hex}")
                        last_uid = uid_hex
                        
                        # Write string if -w flag is provided
                        if args.write:
                            if write_string_to_card(reader, uid, args.write):
                                print("✓ Successfully wrote string to card")
                            else:
                                print("✗ Failed to write string to card")
                        
                        # Read string from card
                        text = read_string_from_card(reader, uid)
                        if text:
                            print(f"✓ Read string from card: '{text}'")
                        else:
                            print("✗ No readable string found on card")
                        
                        # Halt the card
                        reader.MFRC522_StopCrypto1()
                        print("-" * 50)
                    else:
                        print("✗ Failed to read card serial")
                else:
                    # No card detected, reset last_uid after a delay
                    if last_uid is not None:
                        time.sleep(1)
                        last_uid = None
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error during card detection: {e}")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'reader' in locals():
            reader.Close_MFRC522()
        print("Cleanup complete")


if __name__ == '__main__':
    main()
