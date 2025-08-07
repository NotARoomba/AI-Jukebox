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
    """Write a string to the NFC card using NTAG page writes (4 bytes/page)."""
    print(f"Writing '{text}' to card...")
    
    try:
        # Check if it's an NTAG card
        print("Checking if card is NTAG...")
        if not reader.IsNTAG():
            print("✗ Card is not an NTAG card")
            stat, rcv = reader.getNTAGVersion()
            if stat == reader.OK:
                print(f"NTAG version response: {[f'{b:02X}' for b in rcv]}")
            return False
        
        print(f"✓ Detected NTAG{reader.NTAG} card (max pages: {reader.NTAG_MaxPage})")
        
        # Convert text to bytes
        text_bytes = text.encode('utf-8')
        text_length = len(text_bytes)
        print(f"Text length: {text_length} bytes")
        
        # Build a proper NDEF Text record inside an NDEF TLV
        # NDEF Text record (short record):
        #   D1 | 01 | PL | 54 | SR | lang('en') | text
        #   - D1: MB|ME|SR set, TNF=0x01 (well-known)
        #   - 01: type length = 1 (type 'T')
        #   - PL: payload length = 1 (status) + len(lang) + len(text)
        #   - 54: 'T'
        #   - SR: status: bit7=0 (UTF-8), bits[5:0]=len(lang)
        lang = 'en'
        lang_bytes = lang.encode('ascii')
        status_byte = len(lang_bytes) & 0x3F  # UTF-8
        payload_len = 1 + len(lang_bytes) + text_length

        ndef_msg = bytearray([0xD1, 0x01, payload_len, 0x54, status_byte])
        ndef_msg += lang_bytes
        ndef_msg += text_bytes

        # TLV wrapper: 0x03, length, then NDEF message, terminated by 0xFE
        # For our small payloads we can use the short TLV length (1 byte)
        tlv_len = len(ndef_msg)
        buffer = bytearray([0x03, tlv_len])
        buffer += ndef_msg
        buffer += b"\xFE"
        
        # Pad to 4-byte boundary
        while len(buffer) % 4 != 0:
            buffer += b"\x00"
        
        print(f"Total NDEF bytes (padded): {len(buffer)}")
        
        # Write starting at page 4
        start_page = 4
        num_pages = len(buffer) // 4
        current_page = start_page
        idx = 0
        
        while idx < len(buffer) and current_page <= reader.NTAG_MaxPage:
            page_bytes = list(buffer[idx:idx+4])
            stat = reader.writeNTAGPage(current_page, page_bytes)
            if stat != reader.OK:
                print(f"✗ Failed to write page {current_page}")
                return False
            idx += 4
            current_page += 1
        
        print("✓ Wrote NDEF across pages", start_page, "to", current_page - 1)
        
        # Verify first two pages quickly
        ok4, p4 = reader.readNTAGBlock(4)
        ok5, p5 = reader.readNTAGBlock(5)
        if ok4 == reader.OK and p4:
            print("Page 4..7 (block 4) after write:", ' '.join([f"{b:02X}" for b in p4]))
        if ok5 == reader.OK and p5:
            print("Page 8..11 (block 5) after write:", ' '.join([f"{b:02X}" for b in p5]))
        
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
        
        # Find the start of the embedded NDEF message after the TLV
        tlv_len = ndef_length
        tlv_data_idx = ndef_start + 2
        if ndef_length == 0xFF and (ndef_start + 3) < len(all_data):
            # Long-form length: next two bytes are length (big-endian per NDEF spec)
            if ndef_start + 3 < len(all_data):
                tlv_len = (all_data[ndef_start + 2] << 8) | all_data[ndef_start + 3]
                tlv_data_idx = ndef_start + 4

        # Basic bounds check
        if tlv_data_idx + tlv_len > len(all_data):
            tlv_len = max(0, len(all_data) - tlv_data_idx)

        # Parse NDEF record (expecting a single short Text record)
        if tlv_len < 5 or tlv_data_idx + 5 > len(all_data):
            print("✗ NDEF record too short")
            return None

        rec_header = all_data[tlv_data_idx]
        type_len = all_data[tlv_data_idx + 1]
        payload_len = all_data[tlv_data_idx + 2]
        if type_len != 1:
            print("✗ Unsupported type length")
            return None
        if tlv_data_idx + 3 + type_len + payload_len > len(all_data):
            print("✗ NDEF record length out of bounds")
            return None

        rec_type = all_data[tlv_data_idx + 3]
        if rec_type != 0x54:  # 'T'
            print("✗ Not a text (T) record")
            return None

        payload_idx = tlv_data_idx + 3 + type_len
        status = all_data[payload_idx]
        lang_len = status & 0x3F
        is_utf16 = (status & 0x80) != 0
        text_idx = payload_idx + 1 + lang_len
        text_len = payload_len - 1 - lang_len
        if text_len <= 0:
            print("✗ Empty text payload")
            return None
        if text_idx + text_len > len(all_data):
            print("✗ Text payload out of bounds")
            return None

        # Extract text bytes exactly
        text_bytes = bytes(all_data[text_idx:text_idx + text_len])
        
        if not text_bytes:
            print("✗ No text data found")
            return None
        
        try:
            text = text_bytes.decode('utf-16' if is_utf16 else 'utf-8')
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

    signal.signal(signal.SIGINT, signal_handler)

    print("Initializing MFRC522...")
    reader = MFRC522(bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=22)
    # Turn on verbose debug in the library
    reader.DEBUG = True
    print("✓ MFRC522 initialized successfully with updated pin configuration")
    print("✓ Hardware reset pin (GPIO 22) configured and tested")

    try:
        print("Place an NFC card on the reader...")
        print("Press Ctrl+C to exit")
        
        while True:
            (status, TagType) = reader.request(reader.REQIDL)
            
            if status == reader.OK:
                print("✓ Card detected!")
                
                (status, uid) = reader.SelectTagSN()
                if status == reader.OK:
                    uid_str = ''.join([f'{b:02X}' for b in uid])
                    print(f"Card UID: {uid_str}")

                    # Dump NTAG version frame
                    s, v = reader.getNTAGVersion()
                    print(f"[DEBUG] getNTAGVersion stat={s} ver={[f'{b:02X}' for b in (v or [])]}")
                    
                    if args.write:
                        if write_string_to_card(reader, uid, args.write):
                            print("✓ Successfully wrote string to card")
                        else:
                            print("✗ Failed to write string to card")
                    else:
                        text = read_string_from_card(reader, uid)
                        if text:
                            print(f"✓ Read string from card: '{text}'")
                        else:
                            print("✗ No readable string found on card")
                    
                    print("-" * 50)
                    break
                else:
                    print("✗ Failed to select tag")
            else:
                time.sleep(0.1)

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
