# NDEF Record Support for MFRC522 Library

This document describes the NDEF (NFC Data Exchange Format) record support added to the MFRC522 library.

## Overview

The MFRC522 library now supports reading and writing NDEF records to NTAG tags. NDEF is the standard format for storing data on NFC tags, making them compatible with smartphones and other NFC devices.

## Features

- **NDEF Record Support**: Read and write NDEF records to NTAG tags
- **Multiple Record Types**: Text, URL, and custom record types
- **TLV Structure**: Proper TLV (Type-Length-Value) structure for NDEF data
- **Automatic Detection**: Automatically detects and reads NDEF records
- **Backward Compatibility**: Still supports raw data reading/writing

## NDEF Record Types

### Text Records

Text records store human-readable text with language support.

```python
from mfrc522 import NDEFRecord

# Create a text record
text_record = NDEFRecord("text", "Hello, World!", "en")
text_record.mb = True  # Message Begin
text_record.me = True  # Message End
```

### URL Records

URL records store web addresses with automatic prefix handling.

```python
# Create a URL record
url_record = NDEFRecord("url", "example.com")
url_record.mb = True
url_record.me = True
```

### Custom Records

You can create custom record types for specific applications.

```python
# Create a custom record
custom_record = NDEFRecord("application/custom", "custom data")
custom_record.mb = True
custom_record.me = True
```

## Usage Examples

### Reading NDEF Records

```python
from mfrc522 import MFRC522, NTAGType

reader = MFRC522()

# Detect tag
(success, uid, ntag_type) = reader.detect_ntag()
if success:
    # Read NDEF records
    ndef_records = reader.read_ndef_records(ntag_type)

    for i, record in enumerate(ndef_records):
        print(f"Record {i+1}: {record.record_type} - {record.payload}")
        if record.record_type == "text":
            print(f"  Language: {record.language}")
```

### Writing NDEF Records

#### Writing Text Records

```python
# Write a text NDEF record
success = reader.write_ndef_text("Hello, World!", ntag_type, "en")
if success:
    print("Text record written successfully")
```

#### Writing URL Records

```python
# Write a URL NDEF record
success = reader.write_ndef_url("https://example.com", ntag_type)
if success:
    print("URL record written successfully")
```

#### Writing Multiple Records

```python
from mfrc522 import NDEFRecord

# Create multiple records
records = [
    NDEFRecord("text", "First record", "en"),
    NDEFRecord("url", "example.com"),
    NDEFRecord("text", "Third record", "en")
]

# Set message flags
records[0].mb = True  # Message Begin
records[-1].me = True  # Message End

# Write records
success = reader.write_ndef_records(records, ntag_type)
if success:
    print("Multiple records written successfully")
```

### Using SimpleMFRC522 Interface

The SimpleMFRC522 class provides a simpler interface for NDEF operations:

```python
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

# Read NDEF records
uid, ndef_records = reader.read_ndef_records()
for record in ndef_records:
    print(f"{record.record_type}: {record.payload}")

# Write text record
success = reader.write_ndef_text("Hello, World!")
if success:
    print("Text record written")

# Write URL record
success = reader.write_ndef_url("https://example.com")
if success:
    print("URL record written")
```

## Command Line Usage

### Using test.py

The `test.py` script now supports NDEF operations:

```bash
# Read NDEF records
python3 test.py -n

# Write text NDEF record
python3 test.py -w "Hello, World!" -t text

# Write URL NDEF record
python3 test.py -w "example.com" -t url

# Show detailed information
python3 test.py -i -n
```

### Using test_ndef.py

Test NDEF functionality:

```bash
python3 test_ndef.py
```

## NDEF Record Structure

### Text Record Format

```
Byte 0: Record Header (MB=1, ME=1, SR=1, TNF=1)
Byte 1: Type Length (1)
Byte 2: Payload Length
Byte 3: Type ("T")
Byte 4: Status Byte (UTF-8 + language length)
Byte 5-6: Language Code ("en")
Byte 7+: Text Payload
```

### URL Record Format

```
Byte 0: Record Header (MB=1, ME=1, SR=1, TNF=1)
Byte 1: Type Length (1)
Byte 2: Payload Length
Byte 3: Type ("U")
Byte 4: Status Byte (prefix code)
Byte 5+: URL Payload
```

## TLV Structure

NDEF data is stored in TLV (Type-Length-Value) format:

```
Byte 0: TLV Tag (0x03 for NDEF)
Byte 1: Length (0xFF for extended length)
Byte 2-3: Extended Length (if needed)
Byte 4+: NDEF Message
Byte N: Terminator (0xFE)
```

## Error Handling

The library includes comprehensive error handling:

- **Invalid NDEF Data**: Gracefully handles corrupted or invalid NDEF data
- **Memory Limits**: Checks if NDEF data fits in NTAG memory
- **Record Parsing**: Validates record structure during parsing
- **TLV Extraction**: Handles malformed TLV structures

## Compatibility

### NTAG Types Supported

- NTAG213 (128 bytes user data)
- NTAG215 (504 bytes user data)
- NTAG216 (888 bytes user data)
- NTAG213F, NTAG215F, NTAG216F

### NFC Devices

NDEF records written by this library are compatible with:

- Android smartphones
- iPhone (iOS 11+)
- NFC readers
- Other NFC-enabled devices

## Advanced Usage

### Custom Record Types

```python
# Create a custom MIME type record
mime_record = NDEFRecord("application/json", '{"key": "value"}')
mime_record.mb = True
mime_record.me = True

# Create a custom URI record
uri_record = NDEFRecord("uri", "tel:+1234567890")
uri_record.mb = True
uri_record.me = True
```

### Record Flags

```python
record = NDEFRecord("text", "Hello")
record.mb = True   # Message Begin
record.me = True   # Message End
record.sr = True   # Short Record
record.cf = False  # Chunk Flag
record.tnf = 0x01  # Type Name Format
```

### Language Support

```python
# English text
text_record = NDEFRecord("text", "Hello", "en")

# Spanish text
text_record = NDEFRecord("text", "Hola", "es")

# French text
text_record = NDEFRecord("text", "Bonjour", "fr")
```

## Troubleshooting

### Common Issues

1. **No NDEF Records Found**

   - Check if the tag has NDEF data
   - Verify TLV structure is correct
   - Try reading raw data as fallback

2. **Record Parsing Errors**

   - Check record structure
   - Verify type and payload lengths
   - Ensure proper encoding

3. **Memory Issues**
   - Check NTAG type and available space
   - Reduce record size if needed
   - Use shorter text or URLs

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
reader = MFRC522(debug_level='DEBUG')
```

## Examples

### Complete Example

```python
#!/usr/bin/env python3

from mfrc522 import MFRC522, NTAGType, NDEFRecord

def main():
    reader = MFRC522()

    try:
        # Wait for tag
        print("Place an NTAG tag to read/write...")
        while True:
            (success, uid, ntag_type) = reader.detect_ntag()
            if success:
                break
            time.sleep(0.1)

        print(f"Detected {ntag_type.name} tag")

        # Read existing NDEF records
        ndef_records = reader.read_ndef_records(ntag_type)
        if ndef_records:
            print("Existing NDEF records:")
            for record in ndef_records:
                print(f"  {record.record_type}: {record.payload}")
        else:
            print("No NDEF records found")

        # Write new NDEF records
        records = [
            NDEFRecord("text", "Hello from Python!", "en"),
            NDEFRecord("url", "https://github.com")
        ]
        records[0].mb = True
        records[-1].me = True

        success = reader.write_ndef_records(records, ntag_type)
        if success:
            print("NDEF records written successfully")
        else:
            print("Failed to write NDEF records")

    finally:
        reader.close()

if __name__ == "__main__":
    main()
```

This NDEF support makes the MFRC522 library much more powerful and compatible with standard NFC applications!
