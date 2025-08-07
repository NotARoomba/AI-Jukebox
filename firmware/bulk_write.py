#!/usr/bin/env python3

import os
import sys
import time
import argparse
import RPi.GPIO as GPIO
from mfrc522 import MFRC522


def build_text_ndef_payload(text: str) -> bytes:
    # Build NDEF Text record (short record) wrapped in TLV 0x03 ... 0xFE
    lang = 'en'
    lang_bytes = lang.encode('ascii')
    text_bytes = text.encode('utf-8')
    status = len(lang_bytes) & 0x3F  # UTF-8
    payload_len = 1 + len(lang_bytes) + len(text_bytes)
    ndef = bytearray([0xD1, 0x01, payload_len, 0x54, status])
    ndef += lang_bytes
    ndef += text_bytes
    tlv = bytearray([0x03, len(ndef)])
    tlv += ndef
    tlv += b"\xFE"
    # pad to 4-byte boundary
    while len(tlv) % 4 != 0:
        tlv += b"\x00"
    return bytes(tlv)


def write_ndef_text(reader: MFRC522, text: str) -> bool:
    if not reader.IsNTAG():
        return False
    data = build_text_ndef_payload(text)
    page = 4
    idx = 0
    while idx < len(data) and page <= reader.NTAG_MaxPage:
        chunk = list(data[idx:idx+4])
        if len(chunk) < 4:
            chunk += [0] * (4 - len(chunk))
        if reader.writeNTAGPage(page, chunk) != reader.OK:
            return False
        idx += 4
        page += 1
        time.sleep(0.006)  # small settle time
    return True


def derive_tag_string_from_filename(filename: str) -> str:
    name, _ = os.path.splitext(filename)
    # If name starts with 'm_' treat as minecraft literal
    if name.startswith('m_'):
        return name
    # If AI file encodes hex flags after an underscore e.g. song_0F
    if '_' in name:
        maybe_flags = name.rsplit('_', 1)[-1]
        try:
            int(maybe_flags, 16)
            return f"a_{maybe_flags.upper()}"
        except ValueError:
            pass
    # Default to minecraft with the base name
    return f"m_{name}"


def main():
    parser = argparse.ArgumentParser(description='Bulk write NFC tags from audio files in a folder')
    parser.add_argument('-d', '--dir', default='audio', help='Folder containing audio files')
    parser.add_argument('--ext', default='.mp3', help='Audio file extension to scan')
    args = parser.parse_args()

    files = [f for f in sorted(os.listdir(args.dir)) if f.lower().endswith(args.ext.lower())]
    if not files:
        print(f"No {args.ext} files found in {args.dir}")
        return

    print("Initializing MFRC522...")
    reader = MFRC522(bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=22)
    reader.DEBUG = False
    print("Ready. You'll be prompted to present a tag for each file.")

    try:
        for filename in files:
            tag_string = derive_tag_string_from_filename(filename)
            print("----------------------------------------")
            print(f"File: {filename}")
            print(f"Tag text to write: '{tag_string}'")
            input("Press Enter, then present tag to the reader...")

            # Wait for card
            while True:
                status, _ = reader.request(reader.REQIDL)
                if status == reader.OK:
                    status, uid = reader.SelectTagSN()
                    if status == reader.OK:
                        break
                time.sleep(0.05)

            if write_ndef_text(reader, tag_string):
                print("✓ Wrote tag successfully")
            else:
                print("✗ Failed to write tag")
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()


if __name__ == '__main__':
    main()


