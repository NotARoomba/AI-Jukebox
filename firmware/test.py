#!/usr/bin/env python3
# -*- coding: utf8 -*-

import RPi.GPIO as GPIO
import signal
import time
import sys
import argparse
from mfrc522 import MFRC522

# Constants
DEFAULT_VOLUME = 80

def signal_handler(sig, frame):
    print('\nCleaning up GPIO...')
    GPIO.cleanup()
    print('Done!')
    sys.exit(0)

def write_string_to_card(reader, uid, text):
    """Write a string to the NFC card using NTAG methods"""
    print(f"Writing '{text}' to card...")
    
    try:
        # Check if it's an NTAG card
        print("Checking if card is NTAG...")
        if not reader.IsNTAG():
            print("✗ Card is not an NTAG card")
            # Try to get NTAG version anyway for debugging
            stat, rcv = reader.getNTAGVersion()
            if stat == reader.OK:
                print(f"NTAG version response: {[f'{b:02X}' for b in rcv]}")
            return False
        
        print(f"✓ Detected NTAG{reader.NTAG} card (max pages: {reader.NTAG_MaxPage})")
        
        # Convert text to bytes
        text_bytes = text.encode('utf-8')
        text_length = len(text_bytes)
        
        print(f"Text length: {text_length} bytes")
        
        # Prepare NDEF data
        # Block 4: NDEF TLV structure
        # 03 = NDEF TLV tag
        # Length byte will be calculated
        # D1 = NDEF record header (text record)
        # 01 = NDEF record type
        # 0C = text record type length
        # 02 = text record payload length
        # 65 = 'e' (language code)
        # 6E = 'n' (language code)
        # Then the actual text data
        
        # Calculate total NDEF length
        ndef_length = 1 + 1 + 1 + 1 + 2 + text_length  # D1 + 01 + 0C + 02 + language + text
        
        print(f"NDEF length: {ndef_length}")
        
        # Prepare block 4 data (exactly 16 bytes)
        block4 = [0] * 16  # Initialize with zeros
        block4[0] = 0x03  # NDEF TLV tag
        block4[1] = ndef_length  # NDEF length
        block4[2] = 0xD1  # NDEF record header (text record)
        block4[3] = 0x01  # NDEF record type
        block4[4] = 0x0C  # Text record type length
        block4[5] = 0x02  # Text record payload length
        block4[6] = 0x65  # 'e' (language code)
        block4[7] = 0x6E  # 'n' (language code)
        
        # Copy text data to block 4 (max 8 bytes)
        for i, byte in enumerate(text_bytes[:8]):
            block4[i + 8] = byte
        
        print(f"Block 4 data: {' '.join([f'{b:02X}' for b in block4])}")
        
        # Use NTAG write method for 16-byte blocks
        print("Writing block 4...")
        if reader.writeNTAGBlock(4, block4) == reader.OK:
            print("✓ Successfully wrote block 4")
        else:
            print("✗ Failed to write block 4")
            return False
        
        # If text is longer than 8 bytes, write to block 5
        if text_length > 8:
            block5 = [0] * 16  # Initialize with zeros
            remaining_text = text_bytes[8:]
            for i, byte in enumerate(remaining_text[:16]):  # Limit to 16 bytes
                block5[i] = byte
            
            print(f"Block 5 data: {' '.join([f'{b:02X}' for b in block5])}")
            
            print("Writing block 5...")
            if reader.writeNTAGBlock(5, block5) == reader.OK:
                print("✓ Successfully wrote block 5")
            else:
                print("✗ Failed to write block 5")
                return False
        
        # Write terminator TLV
        block_terminator = [0] * 16  # Initialize with zeros
        block_terminator[0] = 0xFE  # Terminator TLV
        
        # Find the next available block
        next_block = 6 if text_length > 8 else 5
        print(f"Writing terminator to block {next_block}...")
        if reader.writeNTAGBlock(next_block, block_terminator) == reader.OK:
            print("✓ Successfully wrote terminator")
        else:
            print("✗ Failed to write terminator")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error in write_string_to_card: {e}")
        import traceback
        traceback.print_exc()
        return False


def read_string_from_card(reader, uid):
    """Read a string from the NFC card using NTAG methods"""
    print("Reading data from card...")
    
    try:
        # Check if it's an NTAG card
        if not reader.IsNTAG():
            print("✗ Card is not an NTAG card")
            return None
        
        print(f"✓ Detected NTAG{reader.NTAG} card (max pages: {reader.NTAG_MaxPage})")
        
        # Read block 4 (NDEF data) using NTAG read method
        stat, block4 = reader.readNTAGBlock(4)
        if stat != reader.OK or not block4 or len(block4) < 8:
            print("✗ Failed to read block 4 or insufficient data")
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
        
        # Get text length (safely)
        if len(block4) < 6:
            print("✗ Insufficient data in block 4")
            return None
        
        text_length = block4[5]
        print(f"Text length: {text_length}")
        
        # Extract text from block 4 (starting from position 8)
        text_bytes = bytearray()
        for i in range(8, min(8 + text_length, len(block4))):
            if block4[i] != 0:
                text_bytes.append(block4[i])
        
        # If text continues in block 5
        if text_length > 8:
            stat, block5 = reader.readNTAGBlock(5)
            if stat == reader.OK and block5 and len(block5) >= min(text_length - 8, 16):
                print(f"Block 5: {' '.join([f'{b:02X}' for b in block5])}")
                for i in range(min(text_length - 8, len(block5))):
                    if block5[i] != 0:
                        text_bytes.append(block5[i])
        
        if not text_bytes:
            print("✗ No text data found")
            return None
        
        try:
            text = text_bytes.decode('utf-8')
            return text
        except UnicodeDecodeError:
            print("✗ Failed to decode text")
            return None
            
    except Exception as e:
        print(f"Error in read_string_from_card: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description='NFC Card Reader/Writer')
    parser.add_argument('-w', '--write', type=str, help='String to write to the card')
    args = parser.parse_args()

    # Set up signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize MFRC522
    print("Initializing MFRC522...")
    reader = MFRC522(bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=22)
    print("✓ MFRC522 initialized successfully with updated pin configuration")
    print("✓ Hardware reset pin (GPIO 22) configured and tested")

    try:
        print("Place an NFC card on the reader...")
        print("Press Ctrl+C to exit")
        
        while True:
            # Request tag
            (status, TagType) = reader.request(reader.REQIDL)
            
            if status == reader.OK:
                print("✓ Card detected!")
                
                # Get the UID
                (status, uid) = reader.SelectTagSN()
                if status == reader.OK:
                    uid_str = ''.join([f'{b:02X}' for b in uid])
                    print(f"Card UID: {uid_str}")
                    
                    if args.write:
                        # Write mode
                        if write_string_to_card(reader, uid, args.write):
                            print("✓ Successfully wrote string to card")
                        else:
                            print("✗ Failed to write string to card")
                    else:
                        # Read mode
                        text = read_string_from_card(reader, uid)
                        if text:
                            print(f"✓ Read string from card: '{text}'")
                        else:
                            print("✗ No readable string found on card")
                    
                    print("-" * 50)
                    break  # Exit after processing one card
                else:
                    print("✗ Failed to select tag")
            else:
                time.sleep(0.1)  # Small delay before next attempt

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Cleaning up GPIO...")
        GPIO.cleanup()
        print("Done!")

if __name__ == "__main__":
    main()
