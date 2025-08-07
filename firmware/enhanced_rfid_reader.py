#!/usr/bin/env python3
"""
Enhanced RFID Reader for NTAG215

This module provides enhanced functionality to read raw data from NTAG215 NFC tags
and decode it according to the NTAG215 specification.
"""

import RPi.GPIO as GPIO
import time
import sys
from typing import Dict, Optional, Tuple, Union

# Import the local mfrc522 library
try:
    from mfrc522.MFRC522 import MFRC522
    MFRC522_AVAILABLE = True
except ImportError:
    # Fallback to global mfrc522 if local not available
    try:
        from mfrc522 import MFRC522
        MFRC522_AVAILABLE = True
    except ImportError:
        MFRC522_AVAILABLE = False

from ntag215_decoder import NTAG215Decoder, decode_ntag215_raw_data

class EnhancedRFIDReader:
    """Enhanced RFID reader with NTAG215 support"""
    
    def __init__(self):
        """Initialize the enhanced RFID reader"""
        if not MFRC522_AVAILABLE:
            raise ImportError("MFRC522 library not available")
        self.reader = MFRC522()
        self.ntag_decoder = None
        
    def read_raw_data(self) -> Optional[bytes]:
        """
        Read raw data from NTAG215 tag
        
        Returns:
            Raw bytes from the tag (144 bytes for NTAG215) or None if failed
        """
        try:
            # Initialize the reader
            self.reader.MFRC522_Init()
            
            # Wait for card
            while True:
                # Scan for cards
                (status, tag_type) = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
                
                if status == self.reader.MI_OK:
                    print("Card detected!")
                    break
                
                time.sleep(0.1)
            
            # Get UID
            (status, uid) = self.reader.MFRC522_Anticoll()
            if status != self.reader.MI_OK:
                print("Failed to get UID")
                return None
            
            print(f"UID: {uid}")
            
            # Read all pages (0-35 for NTAG215)
            raw_data = bytearray()
            
            for page in range(36):  # NTAG215 has 36 pages
                try:
                    # For NTAG215, we need to read 4 bytes per page
                    # MFRC522_Read returns the data directly as a list of bytes
                    data = self.reader.MFRC522_Read(page)
                    
                    if data is not None:
                        # Handle different return types from MFRC522_Read
                        if isinstance(data, (list, tuple)):
                            data_list = list(data)
                        elif isinstance(data, bytes):
                            data_list = list(data)
                        elif isinstance(data, int):
                            data_list = [data]
                        else:
                            # Try to convert to list
                            try:
                                data_list = list(data)
                            except:
                                data_list = [0x00] * 4
                        
                        # NTAG215 has 4 bytes per page, but MFRC522_Read might return 16 bytes
                        # We need to take only the first 4 bytes for NTAG215
                        if len(data_list) >= 4:
                            raw_data.extend(data_list[:4])
                        else:
                            # If we get less than 4 bytes, pad with zeros
                            raw_data.extend(data_list)
                            raw_data.extend([0x00] * (4 - len(data_list)))
                    else:
                        print(f"Failed to read page {page}")
                        # Fill with zeros if read fails
                        raw_data.extend([0x00] * 4)
                        
                except Exception as e:
                    print(f"Error reading page {page}: {e}")
                    raw_data.extend([0x00] * 4)
            
            return bytes(raw_data)
            
        except Exception as e:
            print(f"Error reading raw data: {e}")
            return None
        finally:
            # Stop crypto
            self.reader.MFRC522_StopCrypto1()
    
    def read_and_decode_ntag215(self) -> Optional[Dict]:
        """
        Read and decode NTAG215 tag data
        
        Returns:
            Decoded NTAG215 data dictionary or None if failed
        """
        raw_data = self.read_raw_data()
        if raw_data is None:
            return None
        
        try:
            # Decode the raw data
            decoder = NTAG215Decoder(raw_data)
            return decoder.decoded_data
        except Exception as e:
            print(f"Error decoding NTAG215 data: {e}")
            return None
    
    def read_simple(self) -> Optional[Tuple[int, str]]:
        """
        Simple read method compatible with SimpleMFRC522
        
        Returns:
            Tuple of (id, text) or None if failed
        """
        try:
            # Initialize the reader
            self.reader.MFRC522_Init()
            
            # Wait for card
            while True:
                (status, tag_type) = self.reader.MFRC522_Request(self.reader.PICC_REQIDL)
                if status == self.reader.MI_OK:
                    break
                time.sleep(0.1)
            
            # Get UID
            (status, uid) = self.reader.MFRC522_Anticoll()
            if status != self.reader.MI_OK:
                return None
            
            # Convert UID to integer
            uid_int = int.from_bytes(bytes(uid), byteorder='little')
            
            # Read NDEF data if available
            ndef_text = self._read_ndef_text()
            
            return (uid_int, ndef_text)
            
        except Exception as e:
            print(f"Error in simple read: {e}")
            return None
        finally:
            self.reader.MFRC522_StopCrypto1()
    
    def _read_ndef_text(self) -> str:
        """Read NDEF text from the tag"""
        try:
            # Read user data area (pages 4-129)
            user_data = bytearray()
            
            for page in range(4, 130):  # User data pages
                try:
                    # MFRC522_Read returns just the data, not (status, data)
                    data = self.reader.MFRC522_Read(page)
                    if data is not None:
                        # Handle different return types from MFRC522_Read
                        if isinstance(data, (list, tuple)):
                            data_list = list(data)
                        elif isinstance(data, bytes):
                            data_list = list(data)
                        elif isinstance(data, int):
                            data_list = [data]
                        else:
                            # Try to convert to list
                            try:
                                data_list = list(data)
                            except:
                                data_list = [0x00] * 4
                        
                        if len(data_list) >= 4:
                            user_data.extend(data_list[:4])
                        else:
                            user_data.extend(data_list)
                            user_data.extend([0x00] * (4 - len(data_list)))
                    else:
                        break
                except:
                    break
            
            # Look for NDEF TLV
            user_bytes = bytes(user_data)
            for i in range(len(user_bytes) - 1):
                if user_bytes[i] == 0x03:  # NDEF TLV tag
                    length = user_bytes[i + 1]
                    if i + 2 + length <= len(user_bytes):
                        ndef_data = user_bytes[i + 2:i + 2 + length]
                        # Try to extract text from NDEF
                        return self._extract_text_from_ndef(ndef_data)
            
            return ""
            
        except Exception as e:
            print(f"Error reading NDEF: {e}")
            return ""
    
    def _extract_text_from_ndef(self, ndef_data: bytes) -> str:
        """Extract text from NDEF data"""
        try:
            if len(ndef_data) < 2:
                return ""
            
            # Parse NDEF header
            header = ndef_data[0]
            sr = (header & 0x10) != 0  # Short Record
            
            # Get payload length
            if sr:
                payload_length = ndef_data[1]
                offset = 2
            else:
                payload_length = int.from_bytes(ndef_data[1:4], byteorder='big')
                offset = 4
            
            # Get type length
            type_length = ndef_data[offset]
            offset += 1
            
            # Get ID length if present
            il = (header & 0x08) != 0
            if il:
                id_length = ndef_data[offset]
                offset += 1
            else:
                id_length = 0
            
            # Extract type
            type_data = ndef_data[offset:offset + type_length]
            offset += type_length
            
            # Skip ID if present
            offset += id_length
            
            # Extract payload
            payload = ndef_data[offset:offset + payload_length]
            
            # Try to decode as text
            try:
                return payload.decode('utf-8', errors='ignore')
            except:
                return payload.decode('ascii', errors='ignore')
                
        except Exception as e:
            print(f"Error extracting text from NDEF: {e}")
            return ""

def test_enhanced_reader():
    """Test function for the enhanced RFID reader"""
    print("=== Enhanced RFID Reader Test ===")
    print("This will read raw NTAG215 data and decode it")
    print("Press Ctrl+C to exit")
    print("-" * 30)
    
    reader = EnhancedRFIDReader()
    
    try:
        while True:
            print(f"\n[{time.strftime('%H:%M:%S')}] Waiting for NTAG215 card...")
            
            try:
                # Read and decode NTAG215 data
                decoded_data = reader.read_and_decode_ntag215()
                
                if decoded_data:
                    print("✓ NTAG215 card detected and decoded!")
                    
                    # Print summary
                    uid = decoded_data.get('uid', {}).get('hex', 'Unknown')
                    print(f"UID: {uid}")
                    
                    user_data = decoded_data.get('user_data', {})
                    print(f"User Data Length: {len(user_data.get('bytes', b''))} bytes")
                    
                    ndef_data = decoded_data.get('ndef_data', {})
                    if 'error' not in ndef_data:
                        print(f"NDEF Type: {ndef_data.get('type', 'Unknown')}")
                        print(f"NDEF Payload: {ndef_data.get('payload_text', '')}")
                    else:
                        print(f"NDEF: {ndef_data.get('error', 'Unknown error')}")
                    
                    # Print first few pages
                    print("\nFirst 10 pages:")
                    pages = decoded_data.get('page_dump', [])
                    for page in pages[:10]:
                        print(f"Page {page['page']:2d}: {page['hex']} | {page['ascii']}")
                    
                    print("-" * 30)
                else:
                    print("⚠ No card detected or failed to decode")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"⚠ Error: {e}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    test_enhanced_reader() 