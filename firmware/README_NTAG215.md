# MFRC522 NTAG215 Library

A Python library for reading and writing NTAG215 NFC tags using the MFRC522 RFID reader module. This library is specifically designed for ISO 14443-3A Type A support and provides a clean, modern interface for NTAG215 operations.

## Features

- **ISO 14443-3A Type A Support**: Full compliance with the ISO 14443-3A Type A standard
- **NTAG215 Specific**: Optimized for NTAG215 tag operations
- **Clean API**: Modern Python interface with type hints
- **Error Handling**: Comprehensive error handling and logging
- **Memory Management**: Proper resource cleanup and context manager support

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
   - `example_ntag215.py` - Example usage

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
from mfrc522 import MFRC522
import time

# Initialize the reader
reader = MFRC522(debug_level='INFO')

try:
    # Wait for card detection
    print("Place an NTAG215 tag near the reader...")
    while True:
        (status, back_bits) = reader.request(reader.PICC_REQIDL)
        if status == reader.MI_OK:
            print("Card detected!")
            break
        time.sleep(0.1)

    # Get UID
    (status, uid) = reader.anticoll()
    if status == reader.MI_OK:
        print(f"Tag UID: {uid}")

        # Select the tag
        reader.select_tag(uid)

        # Read data
        data_bytes = reader.read_ntag215_data(start_page=4, end_page=35)
        if data_bytes:
            # Remove trailing zeros and convert to text
            while data_bytes and data_bytes[-1] == 0:
                data_bytes.pop()
            text = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
            print(f"Data: {text}")

        # Write data
        test_data = "Hello NTAG215!".encode('ascii')
        if reader.write_ntag215_data(list(test_data), start_page=4):
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

##### NTAG215 Specific Methods

- `read_ntag215_page(page_addr)` - Read a single page (4 bytes)
- `write_ntag215_page(page_addr, write_data)` - Write a single page (4 bytes)
- `read_ntag215_data(start_page=4, end_page=35)` - Read multiple pages
- `write_ntag215_data(data, start_page=4)` - Write data to multiple pages
- `clear_ntag215_data(start_page=4, end_page=35)` - Clear data by writing zeros

##### Utility Methods

- `close()` - Close the reader and cleanup resources
- `__enter__()` / `__exit__()` - Context manager support

## NTAG215 Memory Layout

NTAG215 tags have 36 pages (0-35) with 4 bytes per page:

- **Pages 0-3**: Reserved (UID, internal data)
- **Pages 4-35**: User data (128 bytes total)

### Page Structure

| Page | Content                       | Description                         |
| ---- | ----------------------------- | ----------------------------------- |
| 0    | UID0-UID2, BCC0               | Serial number and check byte        |
| 1    | UID3-UID6                     | Serial number continued             |
| 2    | UID7, BCC1, INT, LOCK0, LOCK1 | Serial number, internal, lock bytes |
| 3    | OTP0-OTP3                     | One-time programmable bytes         |
| 4-35 | User Data                     | Available for user data             |

## Error Handling

The library provides comprehensive error handling:

```python
try:
    # Your NTAG215 operations
    data = reader.read_ntag215_data()
    if data is None:
        print("Failed to read data")
except Exception as e:
    print(f"Error: {e}")
finally:
    reader.close()
```

## Examples

### Reading Data

```python
# Read all user data
data_bytes = reader.read_ntag215_data(start_page=4, end_page=35)
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
if reader.write_ntag215_data(text_bytes, start_page=4):
    print("Data written successfully!")
```

### Clearing Data

```python
# Clear all user data
if reader.clear_ntag215_data(start_page=4, end_page=35):
    print("Data cleared successfully!")
```

## Troubleshooting

### Common Issues

1. **SPI not enabled**: Ensure SPI is enabled in raspi-config
2. **Permission denied**: Run with sudo or add user to spi group
3. **No card detected**: Check wiring and ensure tag is close enough
4. **Write failures**: Some tags may be read-only or locked

### Debug Mode

Enable debug logging for troubleshooting:

```python
reader = MFRC522(debug_level='DEBUG')
```

## License

This library is provided as-is for educational and development purposes.

## Contributing

Feel free to submit issues and enhancement requests!
