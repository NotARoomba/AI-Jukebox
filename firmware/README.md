# NTAG215 NFC Tag Support

This module provides comprehensive functionality to decode raw data from NTAG215 NFC tags according to the NTAG215 specification.

## Overview

NTAG215 is a specific type of NFC tag with the following characteristics:

- **144 bytes total memory**
- **36 pages** (4 bytes per page)
- **ISO14443A compatible**
- **NDEF support**

## Memory Layout

```
Pages 0-3:   Reserved (UID, internal bytes)
Pages 4-129: User data area
Pages 130-131: Lock bytes
Pages 132-135: Capability container
Pages 136-143: Reserved
```

## Files

- `ntag215_decoder.py` - Core NTAG215 decoder implementation
- `enhanced_rfid_reader.py` - Enhanced RFID reader with NTAG215 support
- `test.py` - Unified test script for reading and writing tags
- `main.py` - Updated main application with NTAG215 support

## Quick Start

### Testing Tags

```bash
# Read from a tag
python test.py

# Write text to a tag
python test.py -w "m_minecraft"
python test.py -w "a_0F"
```

### Basic Usage

```python
from ntag215_decoder import NTAG215Decoder, decode_ntag215_raw_data

# Decode raw bytes
raw_data = bytes([...])  # 144 bytes from NTAG215
decoded = decode_ntag215_raw_data(raw_data)

# Or use the class directly
decoder = NTAG215Decoder(raw_data)
decoded_data = decoder.decoded_data
```

### Using the Enhanced RFID Reader

```python
from enhanced_rfid_reader import EnhancedRFIDReader

reader = EnhancedRFIDReader()

# Read and decode NTAG215 data
decoded_data = reader.read_and_decode_ntag215()

if decoded_data:
    uid = decoded_data['uid']['hex']
    user_data = decoded_data['user_data']['bytes']
    ndef_data = decoded_data['ndef_data']
    print(f"UID: {uid}")
    print(f"User Data: {user_data}")
```

## Decoded Data Structure

The decoder returns a dictionary with the following structure:

```python
{
    'uid': {
        'bytes': bytes,           # Raw UID bytes
        'hex': str,              # Hex representation
        'decimal': int,          # Decimal representation
        'reversed_hex': str      # Reversed hex (little-endian)
    },
    'internal_bytes': {
        'bytes': bytes,          # Internal bytes
        'hex': str,             # Hex representation
        'bcc0': int,            # BCC0 value
        'bcc1': int,            # BCC1 value
        'internal': bytes       # Internal data
    },
    'user_data': {
        'bytes': bytes,         # User data area
        'hex': str,            # Hex representation
        'length': int,         # Length in bytes
        'pages': list          # Page numbers
    },
    'lock_bytes': {
        'bytes': bytes,        # Lock bytes
        'hex': str,           # Hex representation
        'lock0': int,         # Lock0 value
        'lock1': int,         # Lock1 value
        'otp0': int,          # OTP0 value
        'otp1': int           # OTP1 value
    },
    'capability_container': {
        'bytes': bytes,       # Capability container
        'hex': str,          # Hex representation
        'magic_number': bytes, # Magic number
        'version': int,       # Version
        'access_byte': int    # Access byte
    },
    'ndef_data': {
        'header': dict,       # NDEF header
        'type': str,          # NDEF type
        'payload': bytes,     # NDEF payload
        'payload_text': str,  # Decoded text
        'payload_hex': str    # Hex representation
    },
    'raw_hex': str,          # Complete raw data as hex
    'page_dump': list        # All pages with details
}
```

## NDEF Data Decoding

The decoder automatically detects and parses NDEF data in the user data area:

```python
# Check for NDEF data
ndef_data = decoded_data['ndef_data']
if 'error' not in ndef_data:
    print(f"NDEF Type: {ndef_data['type']}")
    print(f"NDEF Payload: {ndef_data['payload_text']}")
else:
    print(f"NDEF Error: {ndef_data['error']}")
```

## Page Dump

Get detailed information about all pages:

```python
pages = decoded_data['page_dump']
for page in pages[:10]:  # First 10 pages
    print(f"Page {page['page']:2d}: {page['hex']} | {page['ascii']}")
```

## Integration with Jukebox

The enhanced reader integrates seamlessly with the jukebox application:

```python
# In main.py
if ENHANCED_AVAILABLE:
    reader = EnhancedRFIDReader()
    decoded_data = reader.read_and_decode_ntag215()

    if decoded_data:
        # Process song data
        song_type, song_data = process_ntag215_data(decoded_data)

        if song_type == 'minecraft':
            play_minecraft_song(song_data)
        elif song_type == 'ai':
            play_ai_generated_song(song_data)
```

## Error Handling

The decoder includes comprehensive error handling:

```python
try:
    decoder = NTAG215Decoder(raw_data)
    # Process decoded data
except ValueError as e:
    print(f"Invalid data: {e}")
except Exception as e:
    print(f"Decoding error: {e}")
```

## Common Issues

### AUTH ERROR

If you encounter AUTH ERROR:

1. Check card positioning
2. Verify card compatibility
3. Check wiring connections
4. Ensure stable power supply

### Data Format Issues

- Ensure raw data is exactly 144 bytes
- Check for proper NDEF TLV structure
- Verify UID format

## Examples

### Decode from Hex String

```python
from ntag215_decoder import decode_ntag215_hex_string

hex_data = "048A5C2A1B3F80884000000310D1010C55016E66632E6F7267FE00" + "00" * (144 - 32)
decoded = decode_ntag215_hex_string(hex_data)
```

### Extract Text from User Data

```python
user_data = decoded_data['user_data']['bytes']
try:
    text = user_data.decode('utf-8', errors='ignore').strip('\x00')
    print(f"User Data: {text}")
except:
    print(f"Raw Data: {user_data.hex()}")
```

### Process Song Data

```python
def process_song_data(decoded_data):
    # Check NDEF first
    ndef_data = decoded_data.get('ndef_data', {})
    if 'error' not in ndef_data:
        payload = ndef_data.get('payload_text', '').strip()
        if payload.startswith('m_'):
            return 'minecraft', payload[2:]
        elif payload.startswith('a_'):
            return 'ai', int(payload[2:], 16)

    # Check user data
    user_data = decoded_data.get('user_data', {}).get('bytes', b'')
    if user_data:
        try:
            text = user_data.decode('utf-8', errors='ignore').strip('\x00')
            if text.startswith('m_'):
                return 'minecraft', text[2:]
            elif text.startswith('a_'):
                return 'ai', int(text[2:], 16)
        except:
            pass

    return None, None
```

## Troubleshooting

### Import Errors

If you get import errors:

```bash
pip install mfrc522
```

### GPIO Issues

Ensure GPIO is properly configured:

```python
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
```

### SPI Issues

Check SPI configuration:

```bash
# Enable SPI
sudo raspi-config nonint get_spi

# Check SPI devices
ls /dev/spidev*
```

## License

This code is part of the AI Jukebox project and follows the same licensing terms.
