#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# SimpleMFRC522 - Simple interface for MFRC522 RFID reader
#

import RPi.GPIO as GPIO
import time
from typing import Tuple, List, Dict, Any
from .MFRC522 import MFRC522, NTAGType

class SimpleMFRC522:
    """
    Simple interface for MFRC522 RFID reader
    Provides easy-to-use methods for reading and writing NTAG tags
    """
    
    def __init__(self, bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=-1):
        """
        Initialize SimpleMFRC522
        
        Args:
            bus: SPI bus number
            device: SPI device number
            spd: SPI speed in Hz
            pin_mode: GPIO mode (10 for BCM, 11 for BOARD)
            pin_rst: Reset pin number (-1 for auto-detect)
        """
        self.reader = MFRC522(bus, device, spd, pin_mode, pin_rst)
        
    def read(self) -> Tuple[List[int], str]:
        """
        Read data from an NTAG tag
        
        Returns:
            Tuple of (uid, text_data)
        """
        try:
            # Wait for card detection
            while True:
                (success, uid, ntag_type) = self.reader.detect_ntag()
                if success:
                    break
                time.sleep(0.1)
            
            # Read data from NTAG pages
            data_bytes = self.reader.read_ntag_data(ntag_type)
            
            if data_bytes:
                # Remove trailing zeros
                while data_bytes and data_bytes[-1] == 0:
                    data_bytes.pop()
                
                if data_bytes:
                    # Convert to text, filtering out non-printable characters
                    text = ''.join(chr(b) for b in data_bytes if b >= 32 and b <= 126)
                    return uid, text
                else:
                    return uid, ""
            else:
                return uid, ""
                
        except Exception as e:
            print(f"Error reading tag: {e}")
            return [], ""
    
    def read_id(self) -> List[int]:
        """
        Read UID from an NTAG tag
        
        Returns:
            UID as list of integers
        """
        try:
            # Wait for card detection
            while True:
                (success, uid, ntag_type) = self.reader.detect_ntag()
                if success:
                    return uid
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error reading UID: {e}")
            return []
    
    def read_id_no_block(self) -> List[int]:
        """
        Read UID from an NTAG tag without blocking
        
        Returns:
            UID as list of integers, or empty list if no card
        """
        try:
            (success, uid, ntag_type) = self.reader.detect_ntag()
            if success:
                return uid
            else:
                return []
                
        except Exception as e:
            print(f"Error reading UID: {e}")
            return []
    
    def write(self, text: str) -> bool:
        """
        Write text data to an NTAG tag
        
        Args:
            text: Text to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Wait for card detection
            while True:
                (success, uid, ntag_type) = self.reader.detect_ntag()
                if success:
                    break
                time.sleep(0.1)
            
            # Convert text to bytes
            text_bytes = list(text.encode('ascii'))
            
            # Check if data is too large for the NTAG tag
            ntag_info = self.reader.get_ntag_info(ntag_type)
            max_bytes = ntag_info['user_bytes']
            if len(text_bytes) > max_bytes:
                print(f"Data too large! Need {len(text_bytes)} bytes but only {max_bytes} available.")
                return False
            
            # Clear the card before writing
            self.reader.clear_ntag_data(ntag_type)
            
            # Write data to NTAG pages
            success = self.reader.write_ntag_data(text_bytes, ntag_type)
            
            if success:
                print(f"Written {len(text_bytes)} bytes to {ntag_type.name} tag")
                return True
            else:
                print("Failed to write to NTAG tag")
                return False
                
        except Exception as e:
            print(f"Error writing to tag: {e}")
            return False
    
    def read_raw(self) -> Tuple[List[int], List[int]]:
        """
        Read raw data from an NTAG tag
        
        Returns:
            Tuple of (uid, raw_data_bytes)
        """
        try:
            # Wait for card detection
            while True:
                (success, uid, ntag_type) = self.reader.detect_ntag()
                if success:
                    break
                time.sleep(0.1)
            
            # Read data from NTAG pages
            data_bytes = self.reader.read_ntag_data(ntag_type)
            
            if data_bytes:
                return uid, data_bytes
            else:
                return uid, []
                
        except Exception as e:
            print(f"Error reading raw data: {e}")
            return [], []
    
    def write_raw(self, data: List[int]) -> bool:
        """
        Write raw data to an NTAG tag
        
        Args:
            data: Raw data bytes to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Wait for card detection
            while True:
                (success, uid, ntag_type) = self.reader.detect_ntag()
                if success:
                    break
                time.sleep(0.1)
            
            # Check if data is too large for the NTAG tag
            ntag_info = self.reader.get_ntag_info(ntag_type)
            max_bytes = ntag_info['user_bytes']
            if len(data) > max_bytes:
                print(f"Data too large! Need {len(data)} bytes but only {max_bytes} available.")
                return False
            
            # Clear the card before writing
            self.reader.clear_ntag_data(ntag_type)
            
            # Write data to NTAG pages
            success = self.reader.write_ntag_data(data, ntag_type)
            
            if success:
                print(f"Written {len(data)} bytes to {ntag_type.name} tag")
                return True
            else:
                print("Failed to write to NTAG tag")
                return False
                
        except Exception as e:
            print(f"Error writing raw data: {e}")
            return False
    
    def get_ntag_type(self) -> NTAGType:
        """
        Get the NTAG type of the detected tag
        
        Returns:
            NTAGType enumeration
        """
        try:
            # Wait for card detection
            while True:
                (success, uid, ntag_type) = self.reader.detect_ntag()
                if success:
                    return ntag_type
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error getting NTAG type: {e}")
            return NTAGType.UNKNOWN
    
    def get_ntag_info(self) -> Dict[str, Any]:
        """
        Get information about the detected NTAG tag
        
        Returns:
            Dictionary with NTAG information
        """
        try:
            # Wait for card detection
            while True:
                (success, uid, ntag_type) = self.reader.detect_ntag()
                if success:
                    return self.reader.get_ntag_info(ntag_type)
                time.sleep(0.1)
                
        except Exception as e:
            print(f"Error getting NTAG info: {e}")
            return {'name': 'Unknown', 'pages': 0, 'user_bytes': 0}
    
    def close(self):
        """Close the reader and cleanup"""
        self.reader.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
