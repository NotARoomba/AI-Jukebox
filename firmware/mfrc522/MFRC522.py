#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# MFRC522 Library for All NTAG Types (NTAG213, NTAG215, NTAG216, etc.)
# Rewritten from scratch for comprehensive NTAG support with NDEF records
#

import RPi.GPIO as GPIO
import spidev
import time
import logging
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum

class NTAGType(Enum):
    """NTAG type enumeration"""
    UNKNOWN = 0
    NTAG213 = 1
    NTAG215 = 2
    NTAG216 = 3
    NTAG213F = 4
    NTAG215F = 5
    NTAG216F = 6

class NDEFRecord:
    """NDEF Record class for handling NFC Data Exchange Format records"""
    
    def __init__(self, record_type: str = "text", payload: str = "", language: str = "en"):
        """
        Initialize NDEF Record
        
        Args:
            record_type: Type of record ("text", "url", "uri", "mime")
            payload: Payload data
            language: Language code for text records (default: "en")
        """
        self.record_type = record_type
        self.payload = payload
        self.language = language
        self.mb = False  # Message Begin
        self.me = False  # Message End
        self.sr = True   # Short Record
        self.cf = False  # Chunk Flag
        self.tnf = 0x01  # Type Name Format (NFC Forum well-known type)
    
    def to_bytes(self) -> List[int]:
        """Convert NDEF record to bytes"""
        if self.record_type == "text":
            return self._create_text_record()
        elif self.record_type in ["url", "uri"]:
            return self._create_url_record()
        else:
            return self._create_generic_record()
    
    def _create_text_record(self) -> List[int]:
        """Create a text NDEF record"""
        # Text record structure:
        # NDEF Record Header (1 byte)
        # Type Length (1 byte)
        # Payload Length (1 byte) - for SR records
        # Type (2 bytes) - "T"
        # Status Byte (1 byte) - language code length + encoding
        # Language Code (2 bytes) - "en"
        # Text Payload (variable)
        
        text_bytes = self.payload.encode('utf-8')
        lang_bytes = self.language.encode('ascii')
        
        # Status byte: bit 7 = UTF-8 (1), bits 6-0 = language code length
        status_byte = 0x80 | len(lang_bytes)  # UTF-8 + language length
        
        # Record header
        header = 0x00
        if self.mb:
            header |= 0x80  # Message Begin
        if self.me:
            header |= 0x40  # Message End
        if self.sr:
            header |= 0x10  # Short Record
        if self.cf:
            header |= 0x20  # Chunk Flag
        header |= self.tnf  # Type Name Format
        
        # Type "T" for text
        type_bytes = [ord('T')]
        
        # Payload: status byte + language + text
        payload_bytes = [status_byte] + list(lang_bytes) + list(text_bytes)
        
        # Build record
        record = [
            header,                    # Record header
            len(type_bytes),           # Type length
            len(payload_bytes)         # Payload length (for SR)
        ] + type_bytes + payload_bytes
        
        return record
    
    def _create_url_record(self) -> List[int]:
        """Create a URL NDEF record"""
        # URL record structure:
        # NDEF Record Header (1 byte)
        # Type Length (1 byte)
        # Payload Length (1 byte) - for SR records
        # Type (1 byte) - "U"
        # Status Byte (1 byte) - prefix code
        # URL Payload (variable)
        
        url_bytes = self.payload.encode('ascii')
        
        # Status byte: prefix code (0x01 = "http://www.")
        status_byte = 0x01
        
        # Record header
        header = 0x00
        if self.mb:
            header |= 0x80  # Message Begin
        if self.me:
            header |= 0x40  # Message End
        if self.sr:
            header |= 0x10  # Short Record
        if self.cf:
            header |= 0x20  # Chunk Flag
        header |= self.tnf  # Type Name Format
        
        # Type "U" for URL
        type_bytes = [ord('U')]
        
        # Payload: status byte + URL
        payload_bytes = [status_byte] + list(url_bytes)
        
        # Build record
        record = [
            header,                    # Record header
            len(type_bytes),           # Type length
            len(payload_bytes)         # Payload length (for SR)
        ] + type_bytes + payload_bytes
        
        return record
    
    def _create_generic_record(self) -> List[int]:
        """Create a generic NDEF record"""
        payload_bytes = self.payload.encode('utf-8')
        
        # Record header
        header = 0x00
        if self.mb:
            header |= 0x80  # Message Begin
        if self.me:
            header |= 0x40  # Message End
        if self.sr:
            header |= 0x10  # Short Record
        if self.cf:
            header |= 0x20  # Chunk Flag
        header |= self.tnf  # Type Name Format
        
        # Type (use record_type as type)
        type_bytes = list(self.record_type.encode('ascii'))
        
        # Build record
        record = [
            header,                    # Record header
            len(type_bytes),           # Type length
            len(payload_bytes)         # Payload length (for SR)
        ] + type_bytes + list(payload_bytes)
        
        return record
    
    @classmethod
    def from_bytes(cls, data: List[int]) -> Optional['NDEFRecord']:
        """Create NDEF record from bytes"""
        if len(data) < 3:
            return None
        
        header = data[0]
        type_length = data[1]
        payload_length = data[2]
        
        if len(data) < 3 + type_length + payload_length:
            return None
        
        # Extract type
        type_start = 3
        type_end = type_start + type_length
        record_type = ''.join(chr(b) for b in data[type_start:type_end])
        
        # Extract payload
        payload_start = type_end
        payload_end = payload_start + payload_length
        payload_data = data[payload_start:payload_end]
        
        # Parse based on type
        if record_type == 'T':
            # Text record
            if len(payload_data) < 1:
                return None
            
            status_byte = payload_data[0]
            lang_length = status_byte & 0x3F
            encoding = "utf-8" if (status_byte & 0x80) else "ascii"
            
            if len(payload_data) < 1 + lang_length:
                return None
            
            language = ''.join(chr(b) for b in payload_data[1:1+lang_length])
            text = ''.join(chr(b) for b in payload_data[1+lang_length:])
            
            record = cls("text", text, language)
        elif record_type == 'U':
            # URL record
            if len(payload_data) < 1:
                return None
            
            prefix_code = payload_data[0]
            url = ''.join(chr(b) for b in payload_data[1:])
            
            # Add prefix based on code
            if prefix_code == 0x01:
                url = "http://www." + url
            elif prefix_code == 0x02:
                url = "https://www." + url
            elif prefix_code == 0x03:
                url = "http://" + url
            elif prefix_code == 0x04:
                url = "https://" + url
            
            record = cls("url", url)
        else:
            # Generic record
            payload = ''.join(chr(b) for b in payload_data)
            record = cls(record_type, payload)
        
        # Set flags
        record.mb = bool(header & 0x80)
        record.me = bool(header & 0x40)
        record.sr = bool(header & 0x10)
        record.cf = bool(header & 0x20)
        record.tnf = header & 0x07
        
        return record

class MFRC522:
    """
    MFRC522 RFID Reader/Writer for All NTAG Types
    Supports NTAG213, NTAG215, NTAG216, NTAG213F, NTAG215F, NTAG216F
    with NDEF record support
    """
    
    # MFRC522 Register definitions
    CommandReg = 0x01
    CommIEnReg = 0x02
    DivIEnReg = 0x03
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
    SerialSpeedReg = 0x1F
    
    CRCResultRegM = 0x21
    CRCResultRegL = 0x22
    ModWidthReg = 0x24
    RFCfgReg = 0x26
    GsNReg = 0x27
    CWGsPReg = 0x28
    ModGsPReg = 0x29
    TModeReg = 0x2A
    TPrescalerReg = 0x2B
    TReloadRegH = 0x2C
    TReloadRegL = 0x2D
    TCounterValueRegH = 0x2E
    TCounterValueRegL = 0x2F
    
    TestSel1Reg = 0x31
    TestSel2Reg = 0x32
    TestPinEnReg = 0x33
    TestPinValueReg = 0x34
    TestBusReg = 0x35
    AutoTestReg = 0x36
    VersionReg = 0x37
    AnalogTestReg = 0x38
    TestDAC1Reg = 0x39
    TestDAC2Reg = 0x3A
    TestADCReg = 0x3B
    
    # Command codes
    PCD_IDLE = 0x00
    PCD_AUTHENT = 0x0E
    PCD_RECEIVE = 0x08
    PCD_TRANSMIT = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC = 0x03
    
    # PICC commands for ISO 14443-3A
    PICC_REQIDL = 0x26  # Request for idle
    PICC_REQALL = 0x52  # Request for all
    PICC_ANTICOLL = 0x93  # Anticollision level 1
    PICC_SElECTTAG = 0x93  # Select tag
    PICC_AUTHENT1A = 0x60  # Authentication key A
    PICC_AUTHENT1B = 0x61  # Authentication key B
    PICC_READ = 0x30  # Read block
    PICC_WRITE = 0xA0  # Write block
    PICC_DECREMENT = 0xC0  # Decrement
    PICC_INCREMENT = 0xC1  # Increment
    PICC_RESTORE = 0xC2  # Restore
    PICC_TRANSFER = 0xB0  # Transfer
    PICC_HALT = 0x50  # Halt
    
    # NTAG specific commands
    PICC_UL_WRITE = 0xA2  # Ultralight write
    PICC_UL_READ = 0x30   # Ultralight read (same as PICC_READ)
    
    # Status codes
    MI_OK = 0
    MI_NOTAGERR = 1
    MI_ERR = 2
    
    # NDEF constants
    NDEF_TLV_TAG = 0x03
    NDEF_TLV_TERMINATOR = 0xFE
    
    # NTAG specifications
    NTAG_SPECS = {
        NTAGType.NTAG213: {
            'name': 'NTAG213',
            'pages': 36,
            'user_pages': (4, 35),
            'user_bytes': 128,
            'uid_length': 7
        },
        NTAGType.NTAG215: {
            'name': 'NTAG215', 
            'pages': 135,
            'user_pages': (4, 134),
            'user_bytes': 504,
            'uid_length': 7
        },
        NTAGType.NTAG216: {
            'name': 'NTAG216',
            'pages': 231,
            'user_pages': (4, 230),
            'user_bytes': 888,
            'uid_length': 7
        },
        NTAGType.NTAG213F: {
            'name': 'NTAG213F',
            'pages': 36,
            'user_pages': (4, 35),
            'user_bytes': 128,
            'uid_length': 7
        },
        NTAGType.NTAG215F: {
            'name': 'NTAG215F',
            'pages': 135,
            'user_pages': (4, 134),
            'user_bytes': 504,
            'uid_length': 7
        },
        NTAGType.NTAG216F: {
            'name': 'NTAG216F',
            'pages': 231,
            'user_pages': (4, 230),
            'user_bytes': 888,
            'uid_length': 7
        }
    }
    
    def __init__(self, bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=-1, debug_level='WARNING'):
        """
        Initialize MFRC522
        
        Args:
            bus: SPI bus number
            device: SPI device number
            spd: SPI speed in Hz
            pin_mode: GPIO mode (10 for BCM, 11 for BOARD)
            pin_rst: Reset pin number (-1 for auto-detect)
            debug_level: Logging level
        """
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = spd
        
        # Setup logging
        self.logger = logging.getLogger('MFRC522')
        self.logger.addHandler(logging.StreamHandler())
        level = logging.getLevelName(debug_level)
        self.logger.setLevel(level)
        
        # Setup GPIO
        gpio_mode = GPIO.getmode()
        if gpio_mode is None:
            GPIO.setmode(pin_mode)
        else:
            pin_mode = gpio_mode
            
        if pin_rst == -1:
            if pin_mode == 11:  # BOARD mode
                pin_rst = 15
            else:  # BCM mode
                pin_rst = 22
                
        GPIO.setup(pin_rst, GPIO.OUT)
        GPIO.output(pin_rst, 1)
        self.pin_rst = pin_rst
        
        # Initialize the reader
        self.init()
        
    def init(self):
        """Initialize the MFRC522"""
        self.reset()
        
        # Configure timer
        self.write_register(self.TModeReg, 0x8D)
        self.write_register(self.TPrescalerReg, 0x3E)
        self.write_register(self.TReloadRegL, 30)
        self.write_register(self.TReloadRegH, 0)
        
        # Configure transmitter
        self.write_register(self.TxAutoReg, 0x40)
        self.write_register(self.ModeReg, 0x3D)
        
        # Turn antenna on
        self.antenna_on()
        
        self.logger.info("MFRC522 initialized")
        
    def reset(self):
        """Reset the MFRC522"""
        self.write_register(self.CommandReg, self.PCD_RESETPHASE)
        time.sleep(0.1)
        
    def write_register(self, reg: int, value: int):
        """Write a value to a register"""
        self.spi.xfer2([(reg << 1) & 0x7E, value])
        
    def read_register(self, reg: int) -> int:
        """Read a value from a register"""
        result = self.spi.xfer2([((reg << 1) & 0x7E) | 0x80, 0])
        return result[1]
        
    def set_bit_mask(self, reg: int, mask: int):
        """Set bits in a register"""
        tmp = self.read_register(reg)
        self.write_register(reg, tmp | mask)
        
    def clear_bit_mask(self, reg: int, mask: int):
        """Clear bits in a register"""
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
        
    def to_card(self, command: int, send_data: List[int]) -> Tuple[int, List[int], int]:
        """
        Send data to the card and receive response
        
        Args:
            command: Command to send
            send_data: Data to send
            
        Returns:
            Tuple of (status, response_data, response_length)
        """
        back_data = []
        back_len = 0
        status = self.MI_ERR
        irq_en = 0x00
        wait_irq = 0x00
        last_bits = None
        n = 0
        
        if command == self.PCD_AUTHENT:
            irq_en = 0x12
            wait_irq = 0x10
        elif command == self.PCD_TRANSCEIVE:
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
        
    def request(self, req_mode: int) -> Tuple[int, int]:
        """
        Request for card detection
        
        Args:
            req_mode: Request mode (PICC_REQIDL or PICC_REQALL)
            
        Returns:
            Tuple of (status, back_bits)
        """
        self.write_register(self.BitFramingReg, 0x07)
        
        tag_type = [req_mode]
        (status, back_data, back_bits) = self.to_card(self.PCD_TRANSCEIVE, tag_type)
        
        if status != self.MI_OK:
            return (self.MI_ERR, 0)
        
        if req_mode == self.PICC_REQIDL and back_bits != 0x10:
            self.write_register(self.BitFramingReg, 0x00)
            (status, back_data, back_bits) = self.to_card(self.PCD_TRANSCEIVE, tag_type)
            if status != self.MI_OK:
                return (self.MI_ERR, 0)
        
        return (status, back_bits)
        
    def anticoll(self) -> Tuple[int, List[int]]:
        """
        Anticollision detection
        
        Returns:
            Tuple of (status, uid)
        """
        back_data = []
        ser_num_check = 0
        
        self.write_register(self.BitFramingReg, 0x00)
        
        ser_num = [self.PICC_ANTICOLL, 0x20]
        (status, back_data, back_bits) = self.to_card(self.PCD_TRANSCEIVE, ser_num)
        
        if status == self.MI_OK:
            if len(back_data) == 5:
                for i in range(4):
                    ser_num_check = ser_num_check ^ back_data[i]
                if ser_num_check != back_data[4]:
                    self.logger.warning("Anticollision checksum failed")
                    return (self.MI_OK, back_data[:4])
                else:
                    return (self.MI_OK, back_data[:4])
            elif len(back_data) == 4:
                return (self.MI_OK, back_data)
            else:
                self.logger.error(f"Anticollision failed: unexpected response length {len(back_data)}")
                return (self.MI_ERR, [])
        else:
            self.logger.error(f"Anticollision failed: status {status}")
            return (self.MI_ERR, [])
        
    def select_tag(self, uid: List[int]) -> int:
        """
        Select a tag by UID
        
        Args:
            uid: UID of the tag
            
        Returns:
            SAK (Select Acknowledge) or 0 if failed
        """
        back_data = []
        buf = [self.PICC_SElECTTAG, 0x70]
        
        if len(uid) < 5:
            uid = uid + [0] * (5 - len(uid))
        elif len(uid) > 5:
            uid = uid[:5]
        
        for i in range(5):
            buf.append(uid[i])
            
        p_out = self.calculate_crc(buf)
        buf.append(p_out[0])
        buf.append(p_out[1])
        
        (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, buf)
        
        if status == self.MI_OK:
            if len(back_data) >= 1:
                return back_data[0]
            else:
                self.logger.warning("Select tag: no response data")
                return 0
        else:
            self.logger.error(f"Select tag failed: status {status}")
            return 0
            
    def calculate_crc(self, p_indata: List[int]) -> List[int]:
        """
        Calculate CRC for data
        
        Args:
            p_indata: Input data
            
        Returns:
            CRC bytes [low, high]
        """
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
        
    def detect_ntag(self) -> Tuple[bool, List[int], NTAGType]:
        """
        Detect and get UID of NTAG tag with type detection
        
        Returns:
            Tuple of (success, uid, ntag_type)
        """
        try:
            (status, back_bits) = self.request(self.PICC_REQIDL)
            if status != self.MI_OK:
                self.logger.debug("No card detected")
                return (False, [], NTAGType.UNKNOWN)
            
            (status, uid) = self.anticoll()
            if status != self.MI_OK or not uid:
                self.logger.debug("Anticollision failed")
                return (False, [], NTAGType.UNKNOWN)
            
            sak = self.select_tag(uid)
            if sak == 0:
                self.logger.debug("Tag selection failed")
                return (False, [], NTAGType.UNKNOWN)
            
            ntag_type = self.detect_ntag_type(uid, sak)
            
            self.logger.info(f"{ntag_type.name} detected with UID: {uid}")
            return (True, uid, ntag_type)
            
        except Exception as e:
            self.logger.error(f"Error in detect_ntag: {e}")
            return (False, [], NTAGType.UNKNOWN)
    
    def detect_ntag_type(self, uid: List[int], sak: int) -> NTAGType:
        """
        Detect NTAG type based on UID and SAK
        
        Args:
            uid: UID of the tag
            sak: Select Acknowledge
            
        Returns:
            NTAGType enumeration
        """
        try:
            page3_data = self.read_ntag_page(3)
            if not page3_data:
                self.logger.debug("Failed to read page 3 for capability container")
                return NTAGType.UNKNOWN
            
            cc = page3_data[0:3]
            
            if cc == [0xE1, 0x10, 0x06]:
                uid_length = len(uid)
                if uid_length >= 4:
                    if uid[0] == 0x04:
                        try:
                            test_page = self.read_ntag_page(36)
                            if test_page:
                                test_page2 = self.read_ntag_page(135)
                                if test_page2:
                                    test_page3 = self.read_ntag_page(231)
                                    if test_page3:
                                        return NTAGType.NTAG216
                                    else:
                                        return NTAGType.NTAG215
                                else:
                                    return NTAGType.NTAG215
                            else:
                                return NTAGType.NTAG213
                        except Exception as e:
                            self.logger.debug(f"Error during page testing: {e}")
                            return NTAGType.NTAG215
                    else:
                        self.logger.debug(f"UID doesn't start with 0x04: {uid[0]:02X}")
                        return NTAGType.UNKNOWN
                else:
                    self.logger.debug(f"UID too short: {uid_length}")
                    return NTAGType.UNKNOWN
            else:
                self.logger.debug(f"Invalid capability container: {cc}")
                return NTAGType.UNKNOWN
                
        except Exception as e:
            self.logger.error(f"Error in detect_ntag_type: {e}")
            return NTAGType.UNKNOWN
    
    def read_ntag_page(self, page_addr: int) -> Optional[List[int]]:
        """
        Read a page from NTAG
        
        Args:
            page_addr: Page address
            
        Returns:
            Page data (4 bytes) or None if failed
        """
        recv_data = [self.PICC_UL_READ, page_addr]
        p_out = self.calculate_crc(recv_data)
        recv_data.append(p_out[0])
        recv_data.append(p_out[1])
        
        (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, recv_data)
        
        if status == self.MI_OK and len(back_data) >= 4:
            return back_data[:4]
        else:
            return None
            
    def write_ntag_page(self, page_addr: int, write_data: List[int]) -> bool:
        """
        Write a page to NTAG
        
        Args:
            page_addr: Page address
            write_data: Data to write (4 bytes)
            
        Returns:
            True if successful, False otherwise
        """
        if len(write_data) != 4:
            self.logger.error(f"Write data must be exactly 4 bytes, got {len(write_data)}")
            return False
            
        buf = [self.PICC_UL_WRITE, page_addr]
        buf.extend(write_data)
        crc = self.calculate_crc(buf)
        buf.extend(crc)
        
        (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, buf)
        
        if status == self.MI_OK:
            if len(back_data) >= 1 and back_data[0] == 0x0A:
                self.logger.debug(f"NTAG write successful for page {page_addr}")
                return True
            elif len(back_data) == 0:
                self.logger.debug(f"NTAG write completed for page {page_addr} (no ACK)")
                return True
            else:
                self.logger.error(f"NTAG write failed for page {page_addr}: unexpected response {back_data}")
                return False
        else:
            self.logger.error(f"NTAG write failed for page {page_addr}: status {status}")
            return False
            
    def read_ntag_data(self, ntag_type: NTAGType, start_page: int = None, end_page: int = None) -> Optional[List[int]]:
        """
        Read data from NTAG pages
        
        Args:
            ntag_type: NTAG type
            start_page: Starting page (default: user data start)
            end_page: Ending page (default: user data end)
            
        Returns:
            Data bytes or None if failed
        """
        if ntag_type == NTAGType.UNKNOWN:
            self.logger.error("Unknown NTAG type")
            return None
        
        spec = self.NTAG_SPECS[ntag_type]
        if start_page is None:
            start_page = spec['user_pages'][0]
        if end_page is None:
            end_page = spec['user_pages'][1]
        
        data_bytes = []
        
        for page_addr in range(start_page, end_page + 1):
            page_data = self.read_ntag_page(page_addr)
            if page_data:
                data_bytes.extend(page_data)
            else:
                break
                
        return data_bytes if data_bytes else None
        
    def write_ntag_data(self, data: List[int], ntag_type: NTAGType, start_page: int = None) -> bool:
        """
        Write data to NTAG pages
        
        Args:
            data: Data to write
            ntag_type: NTAG type
            start_page: Starting page (default: user data start)
            
        Returns:
            True if successful, False otherwise
        """
        if ntag_type == NTAGType.UNKNOWN:
            self.logger.error("Unknown NTAG type")
            return False
        
        if not data:
            return True
        
        spec = self.NTAG_SPECS[ntag_type]
        if start_page is None:
            start_page = spec['user_pages'][0]
        
        max_bytes = spec['user_bytes']
        if len(data) > max_bytes:
            self.logger.error(f"Data too large for {ntag_type.name}: {len(data)} bytes > {max_bytes} bytes")
            return False
        
        while len(data) % 4 != 0:
            data.append(0x00)
            
        page_addr = start_page
        for i in range(0, len(data), 4):
            page_data = data[i:i+4]
            if len(page_data) < 4:
                page_data.extend([0x00] * (4 - len(page_data)))
                
            if not self.write_ntag_page(page_addr, page_data):
                self.logger.error(f"Failed to write page {page_addr}")
                return False
                
            page_addr += 1
            time.sleep(0.01)
            
        return True
        
    def clear_ntag_data(self, ntag_type: NTAGType, start_page: int = None, end_page: int = None) -> bool:
        """
        Clear NTAG data by writing zeros
        
        Args:
            ntag_type: NTAG type
            start_page: Starting page (default: user data start)
            end_page: Ending page (default: user data end)
            
        Returns:
            True if successful, False otherwise
        """
        if ntag_type == NTAGType.UNKNOWN:
            self.logger.error("Unknown NTAG type")
            return False
        
        spec = self.NTAG_SPECS[ntag_type]
        if start_page is None:
            start_page = spec['user_pages'][0]
        if end_page is None:
            end_page = spec['user_pages'][1]
        
        zero_data = [0x00, 0x00, 0x00, 0x00]
        
        for page_addr in range(start_page, end_page + 1):
            if not self.write_ntag_page(page_addr, zero_data):
                self.logger.warning(f"Failed to clear page {page_addr}")
                
        return True
    
    def get_ntag_info(self, ntag_type: NTAGType) -> Dict[str, Any]:
        """
        Get information about NTAG type
        
        Args:
            ntag_type: NTAG type
            
        Returns:
            Dictionary with NTAG information
        """
        if ntag_type == NTAGType.UNKNOWN:
            return {'name': 'Unknown', 'pages': 0, 'user_bytes': 0}
        
        return self.NTAG_SPECS[ntag_type].copy()
    
    def read_ndef_records(self, ntag_type: NTAGType) -> List[NDEFRecord]:
        """
        Read NDEF records from NTAG
        
        Args:
            ntag_type: NTAG type
            
        Returns:
            List of NDEFRecord objects
        """
        if ntag_type == NTAGType.UNKNOWN:
            self.logger.error("Unknown NTAG type")
            return []
        
        # Read all user data
        data_bytes = self.read_ntag_data(ntag_type)
        if not data_bytes:
            return []
        
        # Parse TLV structure to find NDEF data
        ndef_data = self._extract_ndef_tlv(data_bytes)
        if not ndef_data:
            return []
        
        # Parse NDEF message
        return self._parse_ndef_message(ndef_data)
    
    def write_ndef_records(self, records: List[NDEFRecord], ntag_type: NTAGType) -> bool:
        """
        Write NDEF records to NTAG
        
        Args:
            records: List of NDEFRecord objects
            ntag_type: NTAG type
            
        Returns:
            True if successful, False otherwise
        """
        if ntag_type == NTAGType.UNKNOWN:
            self.logger.error("Unknown NTAG type")
            return False
        
        if not records:
            self.logger.error("No records to write")
            return False
        
        # Create NDEF message
        ndef_message = self._create_ndef_message(records)
        if not ndef_message:
            self.logger.error("Failed to create NDEF message")
            return False
        
        # Create TLV structure
        tlv_data = self._create_ndef_tlv(ndef_message)
        if not tlv_data:
            self.logger.error("Failed to create TLV structure")
            return False
        
        # Check if data fits in NTAG
        spec = self.NTAG_SPECS[ntag_type]
        max_bytes = spec['user_bytes']
        if len(tlv_data) > max_bytes:
            self.logger.error(f"NDEF data too large for {ntag_type.name}: {len(tlv_data)} bytes > {max_bytes} bytes")
            return False
        
        # Clear the tag first
        self.clear_ntag_data(ntag_type)
        
        # Write TLV data
        success = self.write_ntag_data(tlv_data, ntag_type)
        
        if success:
            self.logger.info(f"Written {len(records)} NDEF records to {ntag_type.name}")
        else:
            self.logger.error("Failed to write NDEF records")
        
        return success
    
    def write_ndef_text(self, text: str, ntag_type: NTAGType, language: str = "en") -> bool:
        """
        Write a text NDEF record to NTAG
        
        Args:
            text: Text to write
            ntag_type: NTAG type
            language: Language code (default: "en")
            
        Returns:
            True if successful, False otherwise
        """
        record = NDEFRecord("text", text, language)
        record.mb = True  # Message Begin
        record.me = True  # Message End
        return self.write_ndef_records([record], ntag_type)
    
    def write_ndef_url(self, url: str, ntag_type: NTAGType) -> bool:
        """
        Write a URL NDEF record to NTAG
        
        Args:
            url: URL to write
            ntag_type: NTAG type
            
        Returns:
            True if successful, False otherwise
        """
        record = NDEFRecord("url", url)
        record.mb = True  # Message Begin
        record.me = True  # Message End
        return self.write_ndef_records([record], ntag_type)
    
    def _extract_ndef_tlv(self, data: List[int]) -> Optional[List[int]]:
        """
        Extract NDEF data from TLV structure
        
        Args:
            data: Raw data bytes
            
        Returns:
            NDEF data bytes or None if not found
        """
        i = 0
        while i < len(data):
            if data[i] == self.NDEF_TLV_TAG:
                # Found NDEF TLV tag
                if i + 1 < len(data):
                    length = data[i + 1]
                    if length == 0xFF:
                        # Extended length (3 bytes)
                        if i + 3 < len(data):
                            length = (data[i + 2] << 8) | data[i + 3]
                            start = i + 4
                        else:
                            return None
                    else:
                        # Short length (1 byte)
                        start = i + 2
                    
                    if start + length <= len(data):
                        return data[start:start + length]
                    else:
                        return None
                else:
                    return None
            elif data[i] == self.NDEF_TLV_TERMINATOR:
                # End of TLV structure
                break
            else:
                # Skip other TLV blocks
                if i + 1 < len(data):
                    length = data[i + 1]
                    if length == 0xFF:
                        # Extended length
                        if i + 3 < len(data):
                            length = (data[i + 2] << 8) | data[i + 3]
                            i += 4 + length
                        else:
                            break
                    else:
                        # Short length
                        i += 2 + length
                else:
                    break
        
        return None
    
    def _create_ndef_tlv(self, ndef_data: List[int]) -> List[int]:
        """
        Create TLV structure for NDEF data
        
        Args:
            ndef_data: NDEF message bytes
            
        Returns:
            TLV structure bytes
        """
        tlv = []
        
        # NDEF TLV tag
        tlv.append(self.NDEF_TLV_TAG)
        
        # Length
        if len(ndef_data) < 0xFF:
            tlv.append(len(ndef_data))
        else:
            tlv.append(0xFF)
            tlv.append((len(ndef_data) >> 8) & 0xFF)
            tlv.append(len(ndef_data) & 0xFF)
        
        # NDEF data
        tlv.extend(ndef_data)
        
        # Terminator
        tlv.append(self.NDEF_TLV_TERMINATOR)
        
        return tlv
    
    def _create_ndef_message(self, records: List[NDEFRecord]) -> Optional[List[int]]:
        """
        Create NDEF message from records
        
        Args:
            records: List of NDEFRecord objects
            
        Returns:
            NDEF message bytes or None if failed
        """
        if not records:
            return None
        
        # Set message flags
        records[0].mb = True  # First record is Message Begin
        records[-1].me = True  # Last record is Message End
        
        # Convert records to bytes
        message = []
        for record in records:
            record_bytes = record.to_bytes()
            message.extend(record_bytes)
        
        return message
    
    def _parse_ndef_message(self, ndef_data: List[int]) -> List[NDEFRecord]:
        """
        Parse NDEF message into records
        
        Args:
            ndef_data: NDEF message bytes
            
        Returns:
            List of NDEFRecord objects
        """
        records = []
        i = 0
        
        while i < len(ndef_data):
            if i + 2 >= len(ndef_data):
                break
            
            # Parse record header
            header = ndef_data[i]
            type_length = ndef_data[i + 1]
            payload_length = ndef_data[i + 2]
            
            # Check if we have enough data
            if i + 3 + type_length + payload_length > len(ndef_data):
                break
            
            # Extract record data
            record_data = ndef_data[i:i + 3 + type_length + payload_length]
            
            # Create record
            record = NDEFRecord.from_bytes(record_data)
            if record:
                records.append(record)
            
            # Move to next record
            i += 3 + type_length + payload_length
            
            # Check if this was the last record
            if header & 0x40:  # Message End flag
                break
        
        return records
        
    def close(self):
        """Close the MFRC522 and cleanup"""
        self.antenna_off()
        self.spi.close()
        GPIO.cleanup()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
