# MFRC522 All-NTAG Library

A comprehensive Python library for reading and writing all NTAG types using the MFRC522 RFID reader module. This library supports NTAG213, NTAG215, NTAG216, NTAG213F, NTAG215F, NTAG216F, and other NTAG variants.

## Features

- **All NTAG Types Support**: NTAG213, NTAG215, NTAG216, NTAG213F, NTAG215F, NTAG216F
- **Automatic Type Detection**: Automatically detects NTAG type and capabilities
- **ISO 14443-3A Type A Compliance**: Full compliance with the ISO 14443-3A Type A standard
- **Clean API**: Modern Python interface with type hints and enums
- **Error Handling**: Comprehensive error handling and logging
- **Memory Management**: Proper resource cleanup and context manager support
- **Page-by-Page Operations**: Low-level page reading and writing
- **Data Management**: High-level data reading, writing, and clearing

## Supported NTAG Types

| NTAG Type | Pages | User Bytes | User Pages | Description                   |
| --------- | ----- | ---------- | ---------- | ----------------------------- |
| NTAG213   | 36    | 128        | 4-35       | Smallest NTAG variant         |
| NTAG215   | 135   | 504        | 4-134      | Medium NTAG variant           |
| NTAG216   | 231   | 888        | 4-230      | Largest NTAG variant          |
| NTAG213F  | 36    | 128        | 4-35       | NTAG213 with factory settings |
| NTAG215F  | 135   | 504        | 4-134      | NTAG215 with factory settings |
| NTAG216F  | 231   | 888        | 4-230      | NTAG216 with factory settings |

## Installation

1. Ensure you have the required dependencies:

   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip python3-dev
   pip3 install RPi.GPIO spidev
   ```

2. Copy the library files to your project:
   - `mfrc522/MFRC522.py` - Main library
   - `test.py` - Test script for reading/writing
   - `example_all_ntags.py` - Example usage

## Hardware Setup

### MFRC522 Pin Connections

| MFRC522 Pin | Raspberry Pi Pin | Description |
| ----------- | ---------------- | ----------- |
| SDA         | GPIO24 (Pin 18)  | Chip Select |
| SCK         | GPIO23 (Pin 16)  | SPI Clock   |
| MOSI        | GPIO19 (Pin 35)  | SPI MOSI    |
| MISO        | GPIO21 (Pin 40)  | SPI MISO    |
| GND         | GND              | Ground      |
| RST         | GPIO22 (Pin 15)  | Reset       |
| 3.3V        | 3.3V             | Power       |

### Enable SPI

1. Enable SPI in raspi-config:

   ```bash
   sudo raspi-config
   # Navigate to: Interface Options > SPI > Enable
   ```

2. Reboot the Raspberry Pi:
   ```bash
   sudo reboot
   ```

## Usage

### Basic Example

```python
from mfrc522 import MFRC522, NTAGType
import time

# Initialize the reader
reader = MFRC522(debug_level='INFO')

try:
    # Wait for card detection
    print("Place any NTAG tag near the reader...")
    while True:
        (success, uid, ntag_type) = reader.detect_ntag()
        if success:
            print(f"✓ {ntag_type.name} detected!")
            print(f"UID: {uid}")
            break
        time.sleep(0.1)

    # Get NTAG information
    ntag_info = reader.get_ntag_info(ntag_type)
    print(f"NTAG Info: {ntag_info['name']} - {ntag_info['user_bytes']} bytes available")

    # Read data
    data_bytes = reader.read_ntag_data(ntag_type)
    if data_bytes:
        # Remove trailing zeros and convert to text
        while data_bytes and data_bytes[-1] == 0:
            data_bytes.pop()
        text = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
        print(f"Data: {text}")

    # Write data
    test_data = "Hello NTAG!".encode('ascii')
    if reader.write_ntag_data(list(test_data), ntag_type):
        print("Data written successfully!")

finally:
    reader.close()
```

### Using Context Manager

```python
from mfrc522 import MFRC522

with MFRC522() as reader:
    # Your code here
    pass
# Reader automatically closed
```

## API Reference

### MFRC522 Class

#### Constructor

```python
MFRC522(bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=-1, debug_level='WARNING')
```

**Parameters:**

- `bus`: SPI bus number (default: 0)
- `device`: SPI device number (default: 0)
- `spd`: SPI speed in Hz (default: 1000000)
- `pin_mode`: GPIO mode (10 for BCM, 11 for BOARD)
- `pin_rst`: Reset pin number (-1 for auto-detect)
- `debug_level`: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')

#### Methods

##### Core Methods

- `request(req_mode)` - Request for card detection
- `anticoll()` - Anticollision detection
- `select_tag(uid)` - Select a tag by UID
- `to_card(command, send_data)` - Send data to card and receive response

##### NTAG Detection Methods

- `detect_ntag()` - Detect and get UID of NTAG tag with type detection
- `detect_ntag_type(uid, sak)` - Detect NTAG type based on UID and SAK
- `get_ntag_info(ntag_type)` - Get information about NTAG type

##### NTAG Operations

- `read_ntag_page(page_addr)` - Read a single page (4 bytes)
- `write_ntag_page(page_addr, write_data)` - Write a single page (4 bytes)
- `read_ntag_data(ntag_type, start_page=None, end_page=None)` - Read multiple pages
- `write_ntag_data(data, ntag_type, start_page=None)` - Write data to multiple pages
- `clear_ntag_data(ntag_type, start_page=None, end_page=None)` - Clear data by writing zeros

##### Utility Methods

- `close()` - Close the reader and cleanup resources
- `__enter__()` / `__exit__()` - Context manager support

### NTAGType Enum

```python
from mfrc522 import NTAGType

# Available NTAG types
NTAGType.UNKNOWN   # Unknown or unsupported tag
NTAGType.NTAG213   # NTAG213
NTAGType.NTAG215   # NTAG215
NTAGType.NTAG216   # NTAG216
NTAGType.NTAG213F  # NTAG213F
NTAGType.NTAG215F  # NTAG215F
NTAGType.NTAG216F  # NTAG216F
```

## NTAG Memory Layout

All NTAG types follow a similar memory structure:

- **Pages 0-3**: Reserved (UID, internal data, capability container)
- **Pages 4+**: User data (varies by NTAG type)

### Page Structure

| Page | Content                       | Description                                       |
| ---- | ----------------------------- | ------------------------------------------------- |
| 0    | UID0-UID2, BCC0               | Serial number and check byte                      |
| 1    | UID3-UID6                     | Serial number continued                           |
| 2    | UID7, BCC1, INT, LOCK0, LOCK1 | Serial number, internal, lock bytes               |
| 3    | OTP0-OTP3, CC0-CC3            | One-time programmable bytes, capability container |
| 4+   | User Data                     | Available for user data                           |

## Examples

### Reading Data

```python
# Read all user data
(success, uid, ntag_type) = reader.detect_ntag()
if success:
    data_bytes = reader.read_ntag_data(ntag_type)
    if data_bytes:
        # Convert to text
        text = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
        print(f"Data: {text}")
```

### Writing Data

```python
# Write text data
text = "Hello World!"
text_bytes = list(text.encode('ascii'))
(success, uid, ntag_type) = reader.detect_ntag()
if success:
    if reader.write_ntag_data(text_bytes, ntag_type):
        print("Data written successfully!")
```

### Clearing Data

```python
# Clear all user data
(success, uid, ntag_type) = reader.detect_ntag()
if success:
    if reader.clear_ntag_data(ntag_type):
        print("Data cleared successfully!")
```

### Page-by-Page Operations

```python
# Read specific page
page_data = reader.read_ntag_page(4)
if page_data:
    print(f"Page 4 data: {page_data}")

# Write specific page
page_data = [0x48, 0x65, 0x6C, 0x6C]  # "Hell"
if reader.write_ntag_page(4, page_data):
    print("Page 4 written successfully!")
```

### Getting NTAG Information

```python
(success, uid, ntag_type) = reader.detect_ntag()
if success:
    ntag_info = reader.get_ntag_info(ntag_type)
    print(f"NTAG Type: {ntag_info['name']}")
    print(f"User Bytes: {ntag_info['user_bytes']}")
    print(f"User Pages: {ntag_info['user_pages'][0]}-{ntag_info['user_pages'][1]}")
```

## Error Handling

The library provides comprehensive error handling:

```python
try:
    (success, uid, ntag_type) = reader.detect_ntag()
    if not success:
        print("No NTAG tag detected")
        return

    if ntag_type == NTAGType.UNKNOWN:
        print("Unknown or unsupported tag type")
        return

    # Your NTAG operations
    data = reader.read_ntag_data(ntag_type)
    if data is None:
        print("Failed to read data")

except Exception as e:
    print(f"Error: {e}")
finally:
    reader.close()
```

## Troubleshooting

### Common Issues

1. **SPI not enabled**: Ensure SPI is enabled in raspi-config
2. **Permission denied**: Run with sudo or add user to spi group
3. **No card detected**: Check wiring and ensure tag is close enough
4. **Write failures**: Some tags may be read-only or locked
5. **Unknown tag type**: Tag might not be an NTAG or might be damaged

### Debug Mode

Enable debug logging for troubleshooting:

```python
reader = MFRC522(debug_level='DEBUG')
```

### Testing Different NTAG Types

Use the example script to test all NTAG types:

```bash
python3 example_all_ntags.py
```

## License

This library is provided as-is for educational and development purposes.

## Contributing

Feel free to submit issues and enhancement requests!
