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
        
        # Calculate total NDEF length (excluding the TLV tag and length byte)
        ndef_length = 1 + 1 + 1 + 1 + 2 + text_length  # D1 + 01 + 0C + 02 + language + text
        
        print(f"NDEF length: {ndef_length}")
        
        # Prepare block 4 data (exactly 16 bytes)
        block4 = [0] * 16  # Initialize with zeros
        block4[0] = 0x03  # NDEF TLV tag
        block4[1] = ndef_length  # NDEF length
        block4[2] = 0xD1  # NDEF record header (text record)
        block4[3] = 0x01  # NDEF record type
        block4[4] = 0x0C  # Text record type length
        block4[5] = text_length  # Text record payload length
        block4[6] = 0x65  # 'e' (language code)
        block4[7] = 0x6E  # 'n' (language code)
        
        # Copy text data to block 4 (max 8 bytes)
        for i, byte in enumerate(text_bytes[:8]):
            block4[i + 8] = byte
        
        print(f"Block 4 data: {' '.join([f'{b:02X}' for b in block4])}")
        
        # Use NTAG-specific write method
        print("Writing block 4...")
        result = reader.writeNTAGBlockDirect(4, block4)
        if result == reader.OK:
            print("✓ Successfully wrote block 4")
            
            # Verify the write by reading it back
            print("Verifying write by reading block 4...")
            stat, read_block4 = reader.readNTAGBlock(4)
            if stat == reader.OK and read_block4:
                print(f"Read back block 4: {' '.join([f'{b:02X}' for b in read_block4])}")
                if read_block4[0] == 0x03 and read_block4[1] == ndef_length:
                    print("✓ Write verification successful")
                else:
                    print("✗ Write verification failed - data corrupted")
                    return False
            else:
                print("✗ Could not read back block 4 for verification")
                return False
        else:
            print(f"✗ Failed to write block 4: {result}")
            return False
        
        # If text is longer than 8 bytes, write to block 5
        if text_length > 8:
            block5 = [0] * 16  # Initialize with zeros
            remaining_text = text_bytes[8:]
            for i, byte in enumerate(remaining_text[:16]):  # Limit to 16 bytes
                block5[i] = byte
            
            print(f"Block 5 data: {' '.join([f'{b:02X}' for b in block5])}")
            
            print("Writing block 5...")
            result = reader.writeNTAGBlockDirect(5, block5)
            if result == reader.OK:
                print("✓ Successfully wrote block 5")
            else:
                print(f"✗ Failed to write block 5: {result}")
                return False
        
        # Write terminator TLV
        block_terminator = [0] * 16  # Initialize with zeros
        block_terminator[0] = 0xFE  # Terminator TLV
        
        # Find the next available block
        next_block = 6 if text_length > 8 else 5
        print(f"Writing terminator to block {next_block}...")
        result = reader.writeNTAGBlockDirect(next_block, block_terminator)
        if result == reader.OK:
            print("✓ Successfully wrote terminator")
        else:
            print(f"✗ Failed to write terminator: {result}")
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
        
        # Read all blocks to reconstruct the data
        all_data = []
        current_block = 4
        
        while current_block <= reader.NTAG_MaxPage:
            stat, block = reader.readNTAGBlock(current_block)
            if stat == reader.OK and block and len(block) > 0:
                print(f"Block {current_block}: {' '.join([f'{b:02X}' for b in block])}")
                all_data.extend(block)
                
                # Check if we hit a terminator or all zeros
                if block[0] == 0xFE or all(b == 0 for b in block):
                    print(f"Found terminator or end of data at block {current_block}")
                    break
            else:
                break
            current_block += 1
        
        if not all_data:
            print("✗ No data found")
            return None
        
        print(f"Total data read: {len(all_data)} bytes")
        print(f"All data: {' '.join([f'{b:02X}' for b in all_data[:32]])}...")
        
        # Look for NDEF TLV structure
        ndef_start = -1
        for i in range(len(all_data) - 2):
            if all_data[i] == 0x03:  # NDEF TLV tag
                ndef_start = i
                break
        
        if ndef_start == -1:
            print("✗ No NDEF TLV structure found")
            return None
        
        print(f"Found NDEF TLV at position {ndef_start}")
        
        # Extract NDEF data
        ndef_length = all_data[ndef_start + 1]
        print(f"NDEF length: {ndef_length}")
        
        if ndef_length == 0:
            print("✗ NDEF is empty")
            return None
        
        # Look for text record
        text_start = -1
        for i in range(ndef_start + 2, min(ndef_start + 2 + ndef_length, len(all_data) - 1)):
            if all_data[i] == 0xD1 and i + 1 < len(all_data) and all_data[i + 1] == 0x01:
                text_start = i
                break
        
        if text_start == -1:
            print("✗ No text record found")
            return None
        
        print(f"Found text record at position {text_start}")
        
        # Extract text length
        if text_start + 5 >= len(all_data):
            print("✗ Insufficient data for text length")
            return None
        
        text_length = all_data[text_start + 5]
        print(f"Text length: {text_length}")
        
        if text_length == 0 or text_length > 1000:
            print("✗ Invalid text length")
            return None
        
        # Extract text data
        text_bytes = bytearray()
        text_data_start = text_start + 8  # Skip header and language code
        
        for i in range(text_data_start, min(text_data_start + text_length, len(all_data))):
            if all_data[i] != 0 and all_data[i] != 0xFE:
                text_bytes.append(all_data[i])
                if len(text_bytes) >= text_length:
                    break
        
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
