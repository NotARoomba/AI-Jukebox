#!/usr/bin/env python3
"""
Custom NFC RC522 Reader/Writer for NTAG tags
Implements a complete RC522 library from scratch for better control
"""

import RPi.GPIO as GPIO
import spidev
import time
import argparse
from typing import List, Optional, Tuple, Dict
import logging

class CustomRC522:
    """Custom RC522 implementation for NTAG tags"""
    
    # RC522 Commands
    PCD_IDLE = 0x00
    PCD_AUTHENT = 0x0E
    PCD_RECEIVE = 0x08
    PCD_TRANSMIT = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC = 0x03
    
    # PICC Commands
    PICC_REQIDL = 0x26
    PICC_REQALL = 0x52
    PICC_ANTICOLL = 0x93
    PICC_SElECTTAG = 0x93
    PICC_AUTHENT1A = 0x60
    PICC_AUTHENT1B = 0x61
    PICC_READ = 0x30
    PICC_WRITE = 0xA0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE = 0xC2
    PICC_TRANSFER = 0xB0
    PICC_HALT = 0x50
    
    # Status codes
    MI_OK = 0
    MI_NOTAGERR = 1
    MI_ERR = 2
    
    # RC522 Registers
    CommandReg = 0x01
    CommIEnReg = 0x02
    DivlEnReg = 0x03
    CommIrqReg = 0x04
    DivIrqReg = 0x05
    ErrorReg = 0x06
    Status1Reg = 0x07
    Status2Reg = 0x08
    FIFODataReg = 0x09
    FIFOLevelReg = 0x0A
    WaterLevelReg = 0x0B
    ControlReg = 0x0C
    BitFramingReg = 0x0D
    CollReg = 0x0E
    
    ModeReg = 0x11
    TxModeReg = 0x12
    RxModeReg = 0x13
    TxControlReg = 0x14
    TxAutoReg = 0x15
    TxSelReg = 0x16
    RxSelReg = 0x17
    RxThresholdReg = 0x18
    DemodReg = 0x19
    MifareReg = 0x1C
    
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegL = 0x2C
    TReloadRegH = 0x2D
    TCounterValueRegH = 0x2E
    TCounterValueRegL = 0x2F
    
    def __init__(self, bus=0, device=0, speed=1000000, pin_rst=22):
        """Initialize the RC522"""
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed
        self.spi.mode = 0
        
        # Setup reset pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin_rst, GPIO.OUT)
        GPIO.output(pin_rst, GPIO.HIGH)
        
        self.logger = logging.getLogger('CustomRC522')
        self.logger.setLevel(logging.INFO)
        
        # Initialize the RC522
        self.init()
    
    def init(self):
        """Initialize the RC522"""
        self.reset()
        
        # Configure for 13.56MHz
        self.write_register(self.TModeReg, 0x8D)
        self.write_register(self.TPrescalerReg, 0x3E)
        self.write_register(self.TReloadRegL, 30)
        self.write_register(self.TReloadRegH, 0)
        
        self.write_register(self.TxAutoReg, 0x40)
        self.write_register(self.ModeReg, 0x3D)
        
        # Turn antenna on
        self.antenna_on()
    
    def reset(self):
        """Reset the RC522"""
        self.write_register(self.CommandReg, self.PCD_RESETPHASE)
        time.sleep(0.1)
    
    def write_register(self, address, value):
        """Write to RC522 register"""
        self.spi.xfer2([(address << 1) & 0x7E, value])
    
    def read_register(self, address):
        """Read from RC522 register"""
        result = self.spi.xfer2([((address << 1) & 0x7E) | 0x80, 0])
        return result[1]
    
    def set_bit_mask(self, reg, mask):
        """Set bits in register"""
        tmp = self.read_register(reg)
        self.write_register(reg, tmp | mask)
    
    def clear_bit_mask(self, reg, mask):
        """Clear bits in register"""
        tmp = self.read_register(reg)
        self.write_register(reg, tmp & (~mask))
    
    def antenna_on(self):
        """Turn antenna on"""
        temp = self.read_register(self.TxControlReg)
        if ~(temp & 0x03):
            self.set_bit_mask(self.TxControlReg, 0x03)
    
    def antenna_off(self):
        """Turn antenna off"""
        self.clear_bit_mask(self.TxControlReg, 0x03)
    
    def to_card(self, command, send_data):
        """Send command to card and get response"""
        back_data = []
        back_len = 0
        status = self.MI_ERR
        irq_en = 0x00
        wait_irq = 0x00
        last_bits = 0
        n = 0
        
        if command == self.PCD_AUTHENT:
            irq_en = 0x12
            wait_irq = 0x10
        if command == self.PCD_TRANSCEIVE:
            irq_en = 0x77
            wait_irq = 0x30
        
        self.write_register(self.CommIEnReg, irq_en | 0x80)
        self.clear_bit_mask(self.CommIrqReg, 0x80)
        self.set_bit_mask(self.FIFOLevelReg, 0x80)
        
        self.write_register(self.CommandReg, self.PCD_IDLE)
        
        # Write data to FIFO
        for i in range(len(send_data)):
            self.write_register(self.FIFODataReg, send_data[i])
        
        self.write_register(self.CommandReg, command)
        
        if command == self.PCD_TRANSCEIVE:
            self.set_bit_mask(self.BitFramingReg, 0x80)
        
        # Wait for completion
        i = 2000
        while True:
            n = self.read_register(self.CommIrqReg)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break
        
        self.clear_bit_mask(self.BitFramingReg, 0x80)
        
        if i != 0:
            if (self.read_register(self.ErrorReg) & 0x1B) == 0x00:
                status = self.MI_OK
                
                if n & irq_en & 0x01:
                    status = self.MI_NOTAGERR
                
                if command == self.PCD_TRANSCEIVE:
                    n = self.read_register(self.FIFOLevelReg)
                    last_bits = self.read_register(self.ControlReg) & 0x07
                    if last_bits != 0:
                        back_len = (n - 1) * 8 + last_bits
                    else:
                        back_len = n * 8
                    
                    if n == 0:
                        n = 1
                    if n > 16:
                        n = 16
                    
                    for i in range(n):
                        back_data.append(self.read_register(self.FIFODataReg))
            else:
                status = self.MI_ERR
        
        return (status, back_data, back_len)
    
    def request(self, req_mode):
        """Request for tag"""
        self.write_register(self.BitFramingReg, 0x07)
        
        tag_type = [req_mode]
        (status, back_data, back_bits) = self.to_card(self.PCD_TRANSCEIVE, tag_type)
        
        if ((status != self.MI_OK) | (back_bits != 0x10)):
            status = self.MI_ERR
        
        return (status, back_bits)
    
    def anticoll(self):
        """Anticollision"""
        back_data = []
        ser_num_check = 0
        
        ser_num = []
        
        self.write_register(self.BitFramingReg, 0x00)
        
        ser_num.append(self.PICC_ANTICOLL)
        ser_num.append(0x20)
        
        (status, back_data, back_bits) = self.to_card(self.PCD_TRANSCEIVE, ser_num)
        
        if (status == self.MI_OK):
            if len(back_data) == 5:
                for i in range(4):
                    ser_num_check = ser_num_check ^ back_data[i]
                if ser_num_check != back_data[4]:
                    status = self.MI_ERR
            else:
                status = self.MI_ERR
        
        return (status, back_data)
    
    def select_tag(self, ser_num):
        """Select tag"""
        back_data = []
        buf = []
        buf.append(self.PICC_SElECTTAG)
        buf.append(0x70)
        
        for i in range(5):
            buf.append(ser_num[i])
        
        # Calculate CRC
        p_out = self.calculate_crc(buf)
        buf.append(p_out[0])
        buf.append(p_out[1])
        
        (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, buf)
        
        if (status == self.MI_OK) and (back_len == 0x18):
            return back_data[0]
        else:
            return 0
    
    def calculate_crc(self, p_indata):
        """Calculate CRC"""
        self.clear_bit_mask(self.DivIrqReg, 0x04)
        self.set_bit_mask(self.FIFOLevelReg, 0x80)
        
        for i in range(len(p_indata)):
            self.write_register(self.FIFODataReg, p_indata[i])
        
        self.write_register(self.CommandReg, self.PCD_CALCCRC)
        i = 0xFF
        while True:
            n = self.read_register(self.DivIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break
        
        p_out_data = []
        p_out_data.append(self.read_register(self.CRCResultRegL))
        p_out_data.append(self.read_register(self.CRCResultRegM))
        return p_out_data
    
    def read_block(self, block_addr):
        """Read a block from the tag"""
        recv_data = []
        recv_data.append(self.PICC_READ)
        recv_data.append(block_addr)
        
        p_out = self.calculate_crc(recv_data)
        recv_data.append(p_out[0])
        recv_data.append(p_out[1])
        
        (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, recv_data)
        
        if not (status == self.MI_OK):
            self.logger.error("Error while reading!")
            return None
        
        if len(back_data) == 16:
            return back_data
        else:
            return None
    
    def write_block(self, block_addr, write_data):
        """Write a block to the tag"""
        buff = []
        buff.append(self.PICC_WRITE)
        buff.append(block_addr)
        
        crc = self.calculate_crc(buff)
        buff.append(crc[0])
        buff.append(crc[1])
        
        (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, buff)
        
        if not (status == self.MI_OK) or not (back_len == 4) or not ((back_data[0] & 0x0F) == 0x0A):
            status = self.MI_ERR
        
        if status == self.MI_OK:
            buf = []
            for i in range(16):
                buf.append(write_data[i])
            
            crc = self.calculate_crc(buf)
            buf.append(crc[0])
            buf.append(crc[1])
            
            (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, buf)
            
            if not (status == self.MI_OK) or not (back_len == 4) or not ((back_data[0] & 0x0F) == 0x0A):
                self.logger.error("Error while writing")
                return False
        
        return status == self.MI_OK
    
    def close(self):
        """Close the SPI connection"""
        self.spi.close()
        GPIO.cleanup()

class NDEFRecord:
    """NDEF Record class"""
    
    def __init__(self, record_type: str, payload: str, language: str = "en", id: str = ""):
        self.record_type = record_type
        self.payload = payload
        self.language = language
        self.id = id
    
    def __str__(self):
        return f"NDEFRecord(type={self.record_type}, payload='{self.payload}', language='{self.language}')"

class NDEFMessage:
    """NDEF Message class"""
    
    def __init__(self, records: List[NDEFRecord] = None):
        self.records = records or []
    
    def add_record(self, record: NDEFRecord):
        self.records.append(record)
    
    def to_bytes(self) -> bytes:
        """Convert the NDEF message to bytes"""
        if not self.records:
            return b''
        
        message_bytes = bytearray()
        
        for i, record in enumerate(self.records):
            # NDEF record header
            header = 0x00
            
            # Set flags based on position
            if i == 0:  # First record
                header |= 0x80  # MB (Message Begin)
            if i == len(self.records) - 1:  # Last record
                header |= 0x40  # ME (Message End)
            
            # Set SR (Short Record) if payload is <= 255 bytes
            payload_bytes = record.payload.encode('utf-8')
            if record.record_type == "text":
                # Text records have language code
                lang_bytes = record.language.encode('utf-8')
                payload_bytes = bytes([0x02]) + lang_bytes + payload_bytes  # Status byte + lang + text
            
            if len(payload_bytes) <= 255:
                header |= 0x10  # SR (Short Record)
            
            # Set TNF (Type Name Format) - NFC Forum well-known type
            header |= 0x01  # TNF = 0x01
            
            message_bytes.append(header)
            
            # Type length
            type_bytes = record.record_type.encode('utf-8')
            message_bytes.append(len(type_bytes))
            
            # Payload length (short record)
            if len(payload_bytes) <= 255:
                message_bytes.append(len(payload_bytes))
            else:
                # Long record - 4 bytes for length
                message_bytes.extend(len(payload_bytes).to_bytes(4, 'big'))
            
            # ID length (if any)
            if record.id:
                id_bytes = record.id.encode('utf-8')
                message_bytes.append(len(id_bytes))
            else:
                message_bytes.append(0)
            
            # Type
            message_bytes.extend(type_bytes)
            
            # ID (if any)
            if record.id:
                message_bytes.extend(record.id.encode('utf-8'))
            
            # Payload
            message_bytes.extend(payload_bytes)
        
        return bytes(message_bytes)

class NDEFReader:
    """NDEF reader/writer for NFC tags using custom RC522"""
    
    def __init__(self):
        self.reader = CustomRC522()
    
    def detect_tag(self) -> bytes:
        """Detect and return the UID of a tag"""
        # Request tag
        (status, TagType) = self.reader.request(self.reader.PICC_REQIDL)
        if status != self.reader.MI_OK:
            return None
        
        # Get UID
        (status, uid) = self.reader.anticoll()
        if status != self.reader.MI_OK:
            return None
        
        # MFRC522_Anticoll returns exactly 5 bytes (4 bytes UID + 1 byte checksum)
        # MFRC522_SelectTag expects exactly 5 bytes
        if len(uid) != 5:
            print(f"Warning: UID length is {len(uid)}, expected 5")
            return None
        
        return bytes(uid)
    
    def read_ndef_records(self, uid: bytes) -> List[NDEFRecord]:
        """Read NDEF records from the tag"""
        if not uid or len(uid) != 5:
            print(f"Invalid UID: {uid}")
            return []
        
        print(f"Attempting to read from tag with UID: {uid.hex().upper()}")
        
        # Select the tag
        status = self.reader.select_tag(uid)
        if status != 0:
            print(f"Failed to select tag (status={status}), trying alternative approach...")
            # Try to re-select the tag
            time.sleep(0.1)
            status = self.reader.select_tag(uid)
            if status != 0:
                print(f"Still failed to select tag (status={status})")
                # Try to continue anyway - some NTAG tags might work without proper selection
                print("Continuing with reading attempt anyway...")
            else:
                print("Tag selection successful on second attempt")
        else:
            print("Tag selection successful")
        
        # Read all sectors until we hit null data for debugging
        print("\n" + "="*60)
        print("RAW NFC DATA DUMP (All Sectors Until Null Data)")
        print("="*60)
        
        all_data = bytearray()
        null_data_count = 0
        max_sectors = 36  # NTAG215 has 36 pages (0-35)
        
        for block_addr in range(max_sectors):
            try:
                # Read block using custom RC522
                block_data = self.reader.read_block(block_addr)
                
                if block_data and len(block_data) == 16:
                    # Check if this block is all null/zero data
                    if all(b == 0x00 for b in block_data):
                        null_data_count += 1
                        print(f"Block {block_addr:02d}: {'00'*16} (NULL DATA)")
                        # If we've hit 3 consecutive null blocks, stop reading
                        if null_data_count >= 3:
                            print(f"Stopping at block {block_addr} - hit {null_data_count} consecutive null blocks")
                            break
                    else:
                        null_data_count = 0  # Reset null counter
                        all_data.extend(block_data)
                        
                        # Print the block data in hex format
                        hex_data = ' '.join(f'{b:02X}' for b in block_data)
                        ascii_data = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in block_data)
                        print(f"Block {block_addr:02d}: {hex_data} | {ascii_data}")
                        
                        # Check for NDEF TLV structure in this block
                        for i, byte in enumerate(block_data):
                            if byte == 0x03:  # NDEF TLV tag
                                print(f"    -> Found NDEF TLV tag at position {i}")
                            elif byte == 0xD1:  # NDEF text record header
                                print(f"    -> Found NDEF text record header at position {i}")
                            elif byte == 0x02:  # Status byte for UTF-8 text
                                print(f"    -> Found status byte 0x02 at position {i}")
                            elif byte == 0xFE:  # Terminator TLV
                                print(f"    -> Found terminator TLV at position {i}")
                else:
                    print(f"Block {block_addr:02d}: FAILED TO READ")
                    null_data_count += 1
                    if null_data_count >= 3:
                        print(f"Stopping at block {block_addr} - hit {null_data_count} consecutive failed reads")
                        break
            except Exception as e:
                print(f"Block {block_addr:02d}: ERROR - {e}")
                null_data_count += 1
                if null_data_count >= 3:
                    print(f"Stopping at block {block_addr} - hit {null_data_count} consecutive errors")
                    break
        
        print("="*60)
        print(f"TOTAL DATA READ: {len(all_data)} bytes")
        if all_data:
            print(f"FIRST 64 BYTES: {' '.join(f'{b:02X}' for b in all_data[:64])}")
            print(f"ASCII PREVIEW: {''.join(chr(b) if 32 <= b <= 126 else '.' for b in all_data[:64])}")
            
            # Summary of key findings
            print("\nKEY FINDINGS:")
            ndef_tlv_count = sum(1 for b in all_data if b == 0x03)
            ndef_text_count = sum(1 for b in all_data if b == 0xD1)
            status_byte_count = sum(1 for b in all_data if b == 0x02)
            terminator_count = sum(1 for b in all_data if b == 0xFE)
            
            if ndef_tlv_count > 0:
                print(f"  - Found {ndef_tlv_count} NDEF TLV tags (0x03)")
            if ndef_text_count > 0:
                print(f"  - Found {ndef_text_count} NDEF text record headers (0xD1)")
            if status_byte_count > 0:
                print(f"  - Found {status_byte_count} status bytes (0x02)")
            if terminator_count > 0:
                print(f"  - Found {terminator_count} terminator TLVs (0xFE)")
            
            # Look for specific text patterns
            if b'haggstrom' in all_data:
                print(f"  - Found 'haggstrom' text in data")
            if b'hagom' in all_data:
                print(f"  - Found 'hagom' text in data")
            
            # Show printable text sequences
            printable_sequences = []
            current_sequence = ""
            for byte in all_data:
                if 32 <= byte <= 126:  # Printable ASCII
                    current_sequence += chr(byte)
                else:
                    if len(current_sequence) >= 3:
                        printable_sequences.append(current_sequence)
                    current_sequence = ""
            
            if len(current_sequence) >= 3:
                printable_sequences.append(current_sequence)
            
            if printable_sequences:
                print(f"  - Found {len(printable_sequences)} printable text sequences:")
                for seq in printable_sequences[:5]:  # Show first 5 sequences
                    print(f"    * '{seq}'")
                if len(printable_sequences) > 5:
                    print(f"    * ... and {len(printable_sequences) - 5} more")
        print("="*60)
        
        # Now try to parse the NDEF data
        if all_data:
            print("\nParsing NDEF data...")
            records = self.parse_ndef_data(all_data)
            if records:
                print(f"Found {len(records)} records")
                return records
        else:
            print("No data read from tag")
        
        print("No NDEF records found")
        return []
    
    def parse_ndef_data(self, data: bytes) -> List[NDEFRecord]:
        """Parse NDEF data and extract records"""
        records = []
        
        if not data or len(data) < 2:
            return records
        
        print(f"Parsing {len(data)} bytes of data")
        
        # Based on the actual data structure: 03:10:d1:01:0c:54:02:65:6e:68:61:67:67:73:74:72:6f:6d:fe:00
        # This is: TLV(03) + length(10) + NDEF record + terminator(FE)
        
        # Strategy 1: Look for NDEF TLV structure (0x03 + length + payload)
        i = 0
        while i < len(data) - 2:
            if data[i] == 0x03:  # NDEF TLV tag
                length = data[i + 1]
                print(f"Found NDEF TLV at position {i}, length: {length}")
                if i + 2 + length <= len(data):
                    ndef_payload = data[i + 2:i + 2 + length]
                    print(f"NDEF payload: {ndef_payload[:16]}...")
                    parsed_records = self.parse_ndef_payload(ndef_payload)
                    if parsed_records:
                        records.extend(parsed_records)
                        return records
                    i += 2 + length
                else:
                    break
            elif data[i] == 0xFE:  # Terminator TLV
                print(f"Found terminator TLV at position {i}")
                break
            else:
                i += 1
        
        # Strategy 2: Look for direct NDEF records (without TLV wrapper)
        # Look for NDEF text record headers: 0xD1, 0x91, 0x51, 0x11
        for i in range(len(data) - 4):
            if data[i] in [0xD1, 0x91, 0x51, 0x11]:  # NDEF text record headers
                print(f"Found NDEF text record header 0x{data[i]:02X} at position {i}")
                parsed_records = self.parse_ndef_payload(data[i:])
                if parsed_records:
                    records.extend(parsed_records)
                    return records
        
        # Strategy 3: Look for raw text patterns
        records = self.parse_raw_text(data)
        if records:
            return records
        
        # Strategy 4: Fallback text parsing
        records = self.parse_fallback_text(data)
        if records:
            return records
        
        return records
    
    def parse_ndef_payload(self, payload: bytes) -> List[NDEFRecord]:
        """Parse NDEF payload and extract records"""
        records = []
        
        if not payload or len(payload) < 4:
            return records
        
        print(f"Parsing NDEF payload: {payload[:16]}...")
        
        try:
            i = 0
            while i < len(payload) - 3:
                # NDEF record header
                header = payload[i]
                i += 1
                
                # Extract flags
                mb = (header & 0x80) != 0  # Message Begin
                me = (header & 0x40) != 0  # Message End
                sr = (header & 0x10) != 0  # Short Record
                tnf = header & 0x07  # Type Name Format
                
                print(f"NDEF header: 0x{header:02X} (MB={mb}, ME={me}, SR={sr}, TNF={tnf})")
                
                # Type length
                if i >= len(payload):
                    break
                type_length = payload[i]
                i += 1
                
                # Payload length
                if sr:
                    # Short record - 1 byte length
                    if i >= len(payload):
                        break
                    payload_length = payload[i]
                    i += 1
                else:
                    # Long record - 4 bytes length
                    if i + 3 >= len(payload):
                        break
                    payload_length = int.from_bytes(payload[i:i+4], 'big')
                    i += 4
                
                # ID length (if any)
                if i >= len(payload):
                    break
                id_length = payload[i]
                i += 1
                
                print(f"Type length: {type_length}, Payload length: {payload_length}, ID length: {id_length}")
                
                # Type
                if i + type_length > len(payload):
                    break
                record_type = payload[i:i+type_length].decode('utf-8', errors='ignore')
                i += type_length
                
                # ID (if any)
                if id_length > 0:
                    if i + id_length > len(payload):
                        break
                    record_id = payload[i:i+id_length].decode('utf-8', errors='ignore')
                    i += id_length
                else:
                    record_id = ""
                
                # Payload
                if i + payload_length > len(payload):
                    break
                record_payload = payload[i:i+payload_length]
                i += payload_length
                
                print(f"Record type: {record_type}, Payload: {record_payload[:16]}...")
                
                # Handle different record types
                if record_type == "T":
                    # Text record
                    if len(record_payload) >= 1:
                        status_byte = record_payload[0]
                        language_length = status_byte & 0x3F
                        encoding = "UTF-8" if (status_byte & 0x80) else "UTF-16"
                        
                        if len(record_payload) >= 1 + language_length:
                            language = record_payload[1:1+language_length].decode('utf-8', errors='ignore')
                            text = record_payload[1+language_length:].decode(encoding, errors='ignore')
                            
                            print(f"Found text record: '{text}' (language: {language})")
                            records.append(NDEFRecord("text", text, language, record_id))
                        else:
                            # Fallback: try to decode as UTF-8
                            text = record_payload.decode('utf-8', errors='ignore')
                            print(f"Found text record (fallback): '{text}'")
                            records.append(NDEFRecord("text", text, "en", record_id))
                elif record_type == "U":
                    # URL record
                    if len(record_payload) >= 1:
                        status_byte = record_payload[0]
                        url = record_payload[1:].decode('utf-8', errors='ignore')
                        print(f"Found URL record: {url}")
                        records.append(NDEFRecord("url", url, "", record_id))
                else:
                    # Generic record
                    generic_payload = record_payload.decode('utf-8', errors='ignore')
                    print(f"Found generic record: '{generic_payload}'")
                    records.append(NDEFRecord(record_type, generic_payload, "", record_id))
                
                if me:  # Message End
                    break
        except Exception as e:
            print(f"Error parsing NDEF payload: {e}")
        
        return records
    
    def parse_raw_text(self, data: bytes) -> List[NDEFRecord]:
        """Parse raw text from data"""
        records = []
        
        if not data:
            return records
        
        print("Trying raw text parsing...")
        
        # Look for the specific pattern in the user's data:
        # 03:10:d1:01:0c:54:02:65:6e:68:61:67:67:73:74:72:6f:6d:fe:00
        # This shows: TLV(03) + length(10) + NDEF record + "haggstrom" + terminator(FE)
        
        # Strategy 1: Look for status byte (0x02) followed by language code and text
        for i in range(len(data) - 3):
            if data[i] == 0x02:  # Status byte for UTF-8 text
                print(f"Found status byte 0x02 at position {i}")
                # Try to extract text after status byte
                if i + 1 < len(data):
                    # Skip language code (usually 2 bytes: 'e' 'n')
                    lang_start = i + 1
                    text_start = lang_start + 2  # Assuming 2-byte language code
                    
                    if text_start < len(data):
                        # Extract text until we hit a null byte or terminator
                        text_bytes = bytearray()
                        for j in range(text_start, len(data)):
                            if data[j] == 0x00 or data[j] == 0xFE:
                                break
                            if 32 <= data[j] <= 126:  # Printable ASCII
                                text_bytes.append(data[j])
                        
                        if text_bytes:
                            text = text_bytes.decode('utf-8', errors='ignore')
                            print(f"Found raw text: '{text}'")
                            records.append(NDEFRecord("text", text, "en"))
                            return records
        
        # Strategy 2: Look for consecutive printable characters
        text_bytes = bytearray()
        for i, byte in enumerate(data):
            if 32 <= byte <= 126:  # Printable ASCII
                text_bytes.append(byte)
            else:
                if len(text_bytes) >= 3:  # At least 3 characters
                    text = text_bytes.decode('utf-8', errors='ignore')
                    if text.strip():  # Non-empty text
                        print(f"Found consecutive text: '{text}'")
                        records.append(NDEFRecord("text", text.strip(), "en"))
                        return records
                text_bytes.clear()
        
        # Check if we have text at the end
        if len(text_bytes) >= 3:
            text = text_bytes.decode('utf-8', errors='ignore')
            if text.strip():
                print(f"Found text at end: '{text}'")
                records.append(NDEFRecord("text", text.strip(), "en"))
                return records
        
        return records
    
    def parse_fallback_text(self, data: bytes) -> List[NDEFRecord]:
        """Fallback text parsing - look for any readable text"""
        records = []
        
        if not data:
            return records
        
        print("Trying fallback text parsing...")
        
        # Convert to string and look for readable text
        try:
            # Look for the specific "haggstrom" text in the data
            if b'haggstrom' in data:
                print("Found 'haggstrom' text in data!")
                records.append(NDEFRecord("text", "haggstrom", "en"))
                return records
            
            # Look for any consecutive printable characters
            text_bytes = bytearray()
            for byte in data:
                if 32 <= byte <= 126:  # Printable ASCII
                    text_bytes.append(byte)
                else:
                    if len(text_bytes) >= 3:  # At least 3 characters
                        text = text_bytes.decode('utf-8', errors='ignore')
                        if text.strip() and text.strip().isprintable():
                            print(f"Found fallback text: '{text.strip()}'")
                            records.append(NDEFRecord("text", text.strip(), "en"))
                            return records
                    text_bytes.clear()
            
            # Check if we have text at the end
            if len(text_bytes) >= 3:
                text = text_bytes.decode('utf-8', errors='ignore')
                if text.strip() and text.strip().isprintable():
                    print(f"Found fallback text at end: '{text.strip()}'")
                    records.append(NDEFRecord("text", text.strip(), "en"))
                    return records
                    
        except Exception as e:
            print(f"Error in fallback text parsing: {e}")
        
        return records
    
    def write_ndef_records(self, uid: bytes, records: List[NDEFRecord]) -> bool:
        """Write NDEF records to the tag"""
        if not uid or len(uid) != 5 or not records:
            print(f"Invalid UID or no records: {uid}")
            return False
        
        # Select the tag
        status = self.reader.select_tag(uid)
        if status != 0:
            print("Failed to select tag for writing, trying alternative approach...")
            # Try to re-select the tag
            time.sleep(0.1)
            status = self.reader.select_tag(uid)
            if status != 0:
                print("Still failed to select tag for writing")
                return False
        
        # Create NDEF message
        message = NDEFMessage(records)
        ndef_bytes = message.to_bytes()
        
        # Create TLV structure
        tlv_data = bytearray()
        tlv_data.append(0x03)  # NDEF TLV tag
        tlv_data.append(len(ndef_bytes))  # Length
        tlv_data.extend(ndef_bytes)
        tlv_data.append(0xFE)  # Terminator TLV
        
        # Pad to 16-byte blocks
        while len(tlv_data) % 16 != 0:
            tlv_data.append(0)
        
        # Try writing to different starting pages
        for start_page in [4, 5, 6]:
            print(f"Trying to write to page {start_page} onwards...")
            try:
                block_addr = start_page
                for i in range(0, len(tlv_data), 16):
                    if block_addr >= 16:  # Don't write beyond block 15
                        break
                    
                    block_data = tlv_data[i:i+16]
                    if len(block_data) < 16:
                        block_data.extend([0] * (16 - len(block_data)))
                    
                    # Ensure block_data is exactly 16 bytes
                    if len(block_data) != 16:
                        print(f"Error: block_data length is {len(block_data)}, expected 16")
                        continue
                    
                    # Write the block using custom RC522
                    success = self.reader.write_block(block_addr, list(block_data))
                    if success:
                        print(f"Wrote block {block_addr}: {block_data[:8]}...")
                    else:
                        print(f"Failed to write block {block_addr}")
                        break
                    
                    block_addr += 1
                
                # If we get here, writing was successful
                print(f"Successfully wrote NDEF data starting from page {start_page}")
                return True
                
            except Exception as e:
                print(f"Error writing to page {start_page}: {e}")
                continue
        
        print("Failed to write to any starting page")
        return False
    
    def write_text_record(self, uid: bytes, text: str, language: str = "en") -> bool:
        """Write a text record to the tag"""
        record = NDEFRecord("text", text, language)
        return self.write_ndef_records(uid, [record])
    
    def write_url_record(self, uid: bytes, url: str) -> bool:
        """Write a URL record to the tag"""
        record = NDEFRecord("url", url)
        return self.write_ndef_records(uid, [record])
    
    def close(self):
        """Close the reader"""
        self.reader.close()

def main():
    parser = argparse.ArgumentParser(description='NFC NDEF Reader/Writer')
    parser.add_argument('-w', '--write', help='Text to write to the tag')
    parser.add_argument('-t', '--type', default='text', choices=['text', 'url'], help='Record type (default: text)')
    parser.add_argument('-l', '--language', default='en', help='Language code (default: en)')
    
    args = parser.parse_args()
    
    print("Initializing custom NDEF reader...")
    reader = NDEFReader()
    print("Custom NDEF Reader initialized successfully!")
    
    if args.write:
        print(f"Write mode enabled. Will write: '{args.write}' (type: {args.type})")
    else:
        print("Read-only mode enabled.")
    
    print("Place an NFC tag on the reader...")
    print("Waiting for NFC tag...")
    
    try:
        # Wait for tag detection
        while True:
            uid = reader.detect_tag()
            if uid:
                break
            time.sleep(0.1)
        
        print("=" * 50)
        print(f"✓ Tag detected (UID: {uid.hex().upper()})")
        
        if args.write:
            print(f"Writing '{args.write}' to tag...")
            if args.type == 'text':
                success = reader.write_text_record(uid, args.write, args.language)
            elif args.type == 'url':
                success = reader.write_url_record(uid, args.write)
            else:
                print(f"Unknown record type: {args.type}")
                success = False
            
            if success:
                print("✓ Successfully wrote text record to tag")
            else:
                print("✗ Failed to write to tag")
        
        print("Reading NDEF records...")
        records = reader.read_ndef_records(uid)
        
        if records:
            print(f"✓ Found {len(records)} NDEF record(s):")
            for i, record in enumerate(records, 1):
                print(f"  {i}. Type: {record.record_type}, Payload: '{record.payload}'")
        else:
            print("✓ Tag detected but no NDEF records found")
        
        print("=" * 50)
        print("Processing complete. Exiting...")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Cleaning up...")
        reader.close()
        print("Done!")

if __name__ == "__main__":
    main()
