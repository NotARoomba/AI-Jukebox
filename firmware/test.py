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
        # Block 5: NDEF TLV structure
        # 03 = NDEF TLV tag
        # Length byte will be calculated
        # D1 = NDEF record header (text record)
        # 01 = NDEF record type
        # 0C = text record type length
        # 02 = text record payload length
        # 65 = 'e' (language code)
        # 6E = 'n' (language code)
        # Then the actual text data
        
        # Calculate total NDEF length (excluding the TLV tag and length byte)
        ndef_length = 1 + 1 + 1 + 1 + 2 + text_length  # D1 + 01 + 0C + 02 + language + text
        
        print(f"NDEF length: {ndef_length}")
        
        # Prepare block 5 data (exactly 16 bytes)
        block5 = [0] * 16  # Initialize with zeros
        block5[0] = 0x03  # NDEF TLV tag
        block5[1] = ndef_length  # NDEF length
        block5[2] = 0xD1  # NDEF record header (text record)
        block5[3] = 0x01  # NDEF record type
        block5[4] = 0x0C  # Text record type length
        block5[5] = text_length  # Text record payload length
        block5[6] = 0x65  # 'e' (language code)
        block5[7] = 0x6E  # 'n' (language code)
        
        # Copy text data to block 5 (max 8 bytes)
        for i, byte in enumerate(text_bytes[:8]):
            block5[i + 8] = byte
        
        print(f"Block 5 data: {' '.join([f'{b:02X}' for b in block5])}")
        
        # Use standard write method (like MicroPython implementation)
        print("Writing block 5...")
        if reader.write(5, block5) == reader.OK:
            print("✓ Successfully wrote block 5")
        else:
            print("✗ Failed to write block 5")
            return False
        
        # If text is longer than 8 bytes, write to block 6
        if text_length > 8:
            block6 = [0] * 16  # Initialize with zeros
            remaining_text = text_bytes[8:]
            for i, byte in enumerate(remaining_text[:16]):  # Limit to 16 bytes
                block6[i] = byte
            
            print(f"Block 6 data: {' '.join([f'{b:02X}' for b in block6])}")
            
            print("Writing block 6...")
            if reader.write(6, block6) == reader.OK:
                print("✓ Successfully wrote block 6")
            else:
                print("✗ Failed to write block 6")
                return False
        
        # Write terminator TLV
        block_terminator = [0] * 16  # Initialize with zeros
        block_terminator[0] = 0xFE  # Terminator TLV
        
        # Find the next available block
        next_block = 7 if text_length > 8 else 6
        print(f"Writing terminator to block {next_block}...")
        if reader.write(next_block, block_terminator) == reader.OK:
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
            # Try to get NTAG version anyway for debugging
            stat, rcv = reader.getNTAGVersion()
            if stat == reader.OK:
                print(f"NTAG version response: {[f'{b:02X}' for b in rcv]}")
            return None
        
        print(f"✓ Detected NTAG{reader.NTAG} card (max pages: {reader.NTAG_MaxPage})")
        
        # Read block 5 (NDEF data) using standard read method
        stat, block5 = reader.read(5)
        if stat != reader.OK or not block5 or len(block5) < 8:
            print("✗ Failed to read block 5 or insufficient data")
            return None
        
        print(f"Block 5: {' '.join([f'{b:02X}' for b in block5])}")
        
        # Check if it's NDEF data
        if block5[0] != 0x03:
            print("✗ Not NDEF data")
            return None
        
        # Get NDEF length
        ndef_length = block5[1]
        print(f"NDEF length: {ndef_length}")
        
        # Check if NDEF is empty
        if ndef_length == 0:
            print("✗ NDEF is empty")
            return None
        
        # Check if it's a text record
        if block5[2] != 0xD1:
            print("✗ Not a text record")
            return None
        
        # Get text length (safely) - this is the payload length
        if len(block5) < 6:
            print("✗ Insufficient data in block 5")
            return None
        
        text_length = block5[5]
        print(f"Text length: {text_length}")
        
        # Check if text length is valid
        if text_length == 0:
            print("✗ Text length is 0")
            return None
        
        # Extract text from all blocks
        text_bytes = bytearray()
        start_pos = 8  # Start after language code (2 bytes)
        
        # Read from block 5 (only the text part, not the full block)
        bytes_read = 0
        for i in range(start_pos, min(start_pos + text_length, len(block5))):
            if block5[i] != 0 and block5[i] != 0xFE:  # Skip null bytes and terminator
                text_bytes.append(block5[i])
                bytes_read += 1
                if bytes_read >= text_length:
                    break
        
        # Calculate how many more blocks we need to read
        remaining_length = text_length - bytes_read
        current_block = 6
        
        while remaining_length > 0 and current_block <= reader.NTAG_MaxPage:
            stat, block = reader.read(current_block)
            if stat == reader.OK and block and len(block) > 0:
                print(f"Block {current_block}: {' '.join([f'{b:02X}' for b in block])}")
                for i in range(len(block)):
                    if remaining_length <= 0:
                        break
                    if block[i] != 0 and block[i] != 0xFE:  # Skip null bytes and terminator
                        text_bytes.append(block[i])
                        remaining_length -= 1
            else:
                break
            current_block += 1
        
        if not text_bytes:
            print("✗ No text data found")
            return None
        
        try:
            text = text_bytes.decode('utf-8')
            return text
        except UnicodeDecodeError as e:
            print(f"✗ Failed to decode text: {e}")
            print(f"Raw bytes: {[f'{b:02X}' for b in text_bytes]}")
            # Try to decode as much as possible
            try:
                text = text_bytes.decode('utf-8', errors='ignore')
                return text
            except:
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
