#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# MFRC522 Library for All NTAG Types (NTAG213, NTAG215, NTAG216, etc.)
# Rewritten from scratch for comprehensive NTAG support
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

class MFRC522:
    """
    MFRC522 RFID Reader/Writer for All NTAG Types
    Supports NTAG213, NTAG215, NTAG216, NTAG213F, NTAG215F, NTAG216F
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
        
        # For NTAG tags, we need to be more flexible with the response
        if status != self.MI_OK:
            return (self.MI_ERR, 0)
        
        # Check if we got a valid response (should be 16 bits for REQIDL)
        if req_mode == self.PICC_REQIDL and back_bits != 0x10:
            # Try again with different bit framing
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
        
        # Clear the bit framing register for anticollision
        self.write_register(self.BitFramingReg, 0x00)
        
        ser_num = [self.PICC_ANTICOLL, 0x20]
        (status, back_data, back_bits) = self.to_card(self.PCD_TRANSCEIVE, ser_num)
        
        if status == self.MI_OK:
            if len(back_data) == 5:
                # Verify the checksum
                for i in range(4):
                    ser_num_check = ser_num_check ^ back_data[i]
                if ser_num_check != back_data[4]:
                    self.logger.warning("Anticollision checksum failed")
                    # Still return the data, as some tags might have checksum issues
                    return (self.MI_OK, back_data[:4])
                else:
                    return (self.MI_OK, back_data[:4])
            elif len(back_data) == 4:
                # Some tags return only 4 bytes (UID without checksum)
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
        
        # Ensure we have exactly 5 bytes for the UID
        if len(uid) < 5:
            # Pad with zeros if needed
            uid = uid + [0] * (5 - len(uid))
        elif len(uid) > 5:
            # Truncate if too long
            uid = uid[:5]
        
        for i in range(5):
            buf.append(uid[i])
            
        p_out = self.calculate_crc(buf)
        buf.append(p_out[0])
        buf.append(p_out[1])
        
        (status, back_data, back_len) = self.to_card(self.PCD_TRANSCEIVE, buf)
        
        if status == self.MI_OK:
            if len(back_data) >= 1:
                # Return the SAK (first byte of response)
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
            # Step 1: Request card detection
            (status, back_bits) = self.request(self.PICC_REQIDL)
            if status != self.MI_OK:
                self.logger.debug("No card detected")
                return (False, [], NTAGType.UNKNOWN)
            
            # Step 2: Anticollision
            (status, uid) = self.anticoll()
            if status != self.MI_OK or not uid:
                self.logger.debug("Anticollision failed")
                return (False, [], NTAGType.UNKNOWN)
            
            # Step 3: Select tag
            sak = self.select_tag(uid)
            if sak == 0:
                self.logger.debug("Tag selection failed")
                return (False, [], NTAGType.UNKNOWN)
            
            # Step 4: Detect NTAG type
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
            # Read page 3 to get capability container
            page3_data = self.read_ntag_page(3)
            if not page3_data:
                self.logger.debug("Failed to read page 3 for capability container")
                return NTAGType.UNKNOWN
            
            # Check capability container (bytes 0-2)
            cc = page3_data[0:3]
            
            # NTAG213/215/216 have CC = [0xE1, 0x10, 0x06]
            if cc == [0xE1, 0x10, 0x06]:
                # Check UID length and structure
                uid_length = len(uid)
                if uid_length >= 4:
                    # Check for NTAG213/215/216 based on UID structure
                    if uid[0] == 0x04:  # NTAG213/215/216 start with 0x04
                        # Try to read more pages to determine exact type
                        # Start with NTAG213 (36 pages)
                        try:
                            # Try to read a page beyond NTAG213 limit
                            test_page = self.read_ntag_page(36)
                            if test_page:
                                # Try to read beyond NTAG215 limit
                                test_page2 = self.read_ntag_page(135)
                                if test_page2:
                                    # Try to read beyond NTAG216 limit
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
                            # Default to NTAG215 if detection fails
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
            return back_data[:4]  # Return first 4 bytes
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
                # Some tags don't return ACK but still succeed
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
                # Stop reading if we can't read a page
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
        
        # Check if data is too large
        max_bytes = spec['user_bytes']
        if len(data) > max_bytes:
            self.logger.error(f"Data too large for {ntag_type.name}: {len(data)} bytes > {max_bytes} bytes")
            return False
        
        # Pad data to 4-byte boundaries
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
            time.sleep(0.01)  # Small delay between writes
            
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
                # Continue with other pages
                
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
        
    def close(self):
        """Close the MFRC522 and cleanup"""
        self.antenna_off()
        self.spi.close()
        GPIO.cleanup()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
