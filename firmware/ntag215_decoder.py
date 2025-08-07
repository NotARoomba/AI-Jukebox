#!/usr/bin/env python3
"""
NTAG215 NFC Tag Decoder

This module provides functionality to decode raw data from NTAG215 NFC tags
according to the NTAG215 specification.

NTAG215 Memory Layout:
- 144 bytes total memory
- 36 pages (4 bytes per page)
- Pages 0-3: Reserved (UID, internal bytes)
- Pages 4-129: User data area
- Pages 130-131: Lock bytes
- Pages 132-135: Capability container
- Pages 136-143: Reserved

Reference: NTAG215 datasheet
"""

import struct
import binascii
from typing import Dict, List, Optional, Tuple, Union

class NTAG215Decoder:
    """NTAG215 NFC tag decoder class"""
    
    # NTAG215 constants
    TOTAL_PAGES = 36
    BYTES_PER_PAGE = 4
    TOTAL_BYTES = TOTAL_PAGES * BYTES_PER_PAGE  # 144 bytes
    
    # Memory layout
    RESERVED_PAGES = 4  # Pages 0-3
    USER_DATA_START = 4  # Page 4
    USER_DATA_END = 129  # Page 129
    LOCK_BYTES_START = 130  # Page 130
    LOCK_BYTES_END = 131  # Page 131
    CAPABILITY_CONTAINER_START = 132  # Page 132
    CAPABILITY_CONTAINER_END = 135  # Page 135
    RESERVED_END = 143  # Page 143
    
    def __init__(self, raw_data: Optional[bytes] = None):
        """
        Initialize NTAG215 decoder
        
        Args:
            raw_data: Raw bytes from NTAG215 tag (144 bytes)
        """
        self.raw_data = raw_data or bytes()
        self.decoded_data = {}
        
        if raw_data:
            self.decode()
    
    def decode(self, raw_data: Optional[bytes] = None) -> Dict:
        """
        Decode raw NTAG215 data
        
        Args:
            raw_data: Raw bytes from NTAG215 tag (144 bytes)
            
        Returns:
            Dictionary containing decoded information
        """
        if raw_data:
            self.raw_data = raw_data
        
        if not self.raw_data:
            raise ValueError("No raw data provided")
        
        if len(self.raw_data) != self.TOTAL_BYTES:
            raise ValueError(f"Expected {self.TOTAL_BYTES} bytes, got {len(self.raw_data)}")
        
        self.decoded_data = {
            'uid': self._decode_uid(),
            'internal_bytes': self._decode_internal_bytes(),
            'user_data': self._decode_user_data(),
            'lock_bytes': self._decode_lock_bytes(),
            'capability_container': self._decode_capability_container(),
            'ndef_data': self._decode_ndef_data(),
            'raw_hex': self.raw_data.hex().upper(),
            'page_dump': self._dump_pages()
        }
        
        return self.decoded_data
    
    def _decode_uid(self) -> Dict:
        """Decode UID from pages 0-2"""
        uid_bytes = self.raw_data[0:7]  # 7 bytes for UID
        return {
            'bytes': uid_bytes,
            'hex': uid_bytes.hex().upper(),
            'decimal': int.from_bytes(uid_bytes, byteorder='little'),
            'reversed_hex': uid_bytes[::-1].hex().upper()
        }
    
    def _decode_internal_bytes(self) -> Dict:
        """Decode internal bytes from page 3"""
        internal_bytes = self.raw_data[12:16]  # Page 3
        return {
            'bytes': internal_bytes,
            'hex': internal_bytes.hex().upper(),
            'bcc0': internal_bytes[0] if len(internal_bytes) > 0 else None,
            'bcc1': internal_bytes[1] if len(internal_bytes) > 1 else None,
            'internal': internal_bytes[2:4] if len(internal_bytes) > 2 else None
        }
    
    def _decode_user_data(self) -> Dict:
        """Decode user data area (pages 4-129)"""
        user_data_start = self.USER_DATA_START * self.BYTES_PER_PAGE
        user_data_end = (self.USER_DATA_END + 1) * self.BYTES_PER_PAGE
        user_data = self.raw_data[user_data_start:user_data_end]
        
        return {
            'bytes': user_data,
            'hex': user_data.hex().upper(),
            'length': len(user_data),
            'pages': list(range(self.USER_DATA_START, self.USER_DATA_END + 1))
        }
    
    def _decode_lock_bytes(self) -> Dict:
        """Decode lock bytes (pages 130-131)"""
        lock_start = self.LOCK_BYTES_START * self.BYTES_PER_PAGE
        lock_end = (self.LOCK_BYTES_END + 1) * self.BYTES_PER_PAGE
        lock_bytes = self.raw_data[lock_start:lock_end]
        
        return {
            'bytes': lock_bytes,
            'hex': lock_bytes.hex().upper(),
            'lock0': lock_bytes[0] if len(lock_bytes) > 0 else None,
            'lock1': lock_bytes[1] if len(lock_bytes) > 1 else None,
            'otp0': lock_bytes[2] if len(lock_bytes) > 2 else None,
            'otp1': lock_bytes[3] if len(lock_bytes) > 3 else None
        }
    
    def _decode_capability_container(self) -> Dict:
        """Decode capability container (pages 132-135)"""
        cc_start = self.CAPABILITY_CONTAINER_START * self.BYTES_PER_PAGE
        cc_end = (self.CAPABILITY_CONTAINER_END + 1) * self.BYTES_PER_PAGE
        cc_data = self.raw_data[cc_start:cc_end]
        
        return {
            'bytes': cc_data,
            'hex': cc_data.hex().upper(),
            'magic_number': cc_data[0:2] if len(cc_data) > 1 else None,
            'version': cc_data[2] if len(cc_data) > 2 else None,
            'access_byte': cc_data[3] if len(cc_data) > 3 else None
        }
    
    def _decode_ndef_data(self) -> Dict:
        """Decode NDEF data from user data area"""
        user_data = self.decoded_data.get('user_data', {}).get('bytes', b'')
        if not user_data:
            return {'error': 'No user data available'}
        
        try:
            # Look for NDEF TLV structure
            ndef_data = self._extract_ndef_tlv(user_data)
            if ndef_data:
                return self._parse_ndef_message(ndef_data)
            else:
                return {'error': 'No NDEF data found'}
        except Exception as e:
            return {'error': f'Failed to parse NDEF: {str(e)}'}
    
    def _extract_ndef_tlv(self, user_data: bytes) -> Optional[bytes]:
        """Extract NDEF TLV from user data"""
        if len(user_data) < 2:
            return None
        
        # Look for NDEF TLV (0x03)
        for i in range(len(user_data) - 1):
            if user_data[i] == 0x03:  # NDEF TLV tag
                length = user_data[i + 1]
                if i + 2 + length <= len(user_data):
                    return user_data[i + 2:i + 2 + length]
        
        return None
    
    def _parse_ndef_message(self, ndef_data: bytes) -> Dict:
        """Parse NDEF message"""
        if len(ndef_data) < 2:
            return {'error': 'Invalid NDEF data'}
        
        # Parse NDEF header
        header = ndef_data[0]
        mb = (header & 0x80) != 0  # Message Begin
        me = (header & 0x40) != 0  # Message End
        cf = (header & 0x20) != 0  # Chunk Flag
        sr = (header & 0x10) != 0  # Short Record
        il = (header & 0x08) != 0  # ID Length present
        tnf = header & 0x07  # Type Name Format
        
        # Get payload length
        if sr:
            payload_length = ndef_data[1]
            offset = 2
        else:
            payload_length = struct.unpack('>I', b'\x00' + ndef_data[1:4])[0]
            offset = 4
        
        # Get type length
        type_length = ndef_data[offset]
        offset += 1
        
        # Get ID length if present
        id_length = 0
        if il:
            id_length = ndef_data[offset]
            offset += 1
        
        # Extract type
        type_data = ndef_data[offset:offset + type_length]
        offset += type_length
        
        # Skip ID if present
        offset += id_length
        
        # Extract payload
        payload = ndef_data[offset:offset + payload_length]
        
        return {
            'header': {
                'mb': mb,
                'me': me,
                'cf': cf,
                'sr': sr,
                'il': il,
                'tnf': tnf
            },
            'type_length': type_length,
            'id_length': id_length,
            'payload_length': payload_length,
            'type': type_data.decode('ascii', errors='ignore'),
            'payload': payload,
            'payload_hex': payload.hex().upper(),
            'payload_text': payload.decode('utf-8', errors='ignore')
        }
    
    def _dump_pages(self) -> List[Dict]:
        """Dump all pages with their content"""
        pages = []
        for page_num in range(self.TOTAL_PAGES):
            start = page_num * self.BYTES_PER_PAGE
            end = start + self.BYTES_PER_PAGE
            page_data = self.raw_data[start:end]
            
            page_info = {
                'page': page_num,
                'bytes': page_data,
                'hex': page_data.hex().upper(),
                'ascii': ''.join([chr(b) if 32 <= b <= 126 else '.' for b in page_data])
            }
            
            # Add page type information
            if page_num < self.RESERVED_PAGES:
                page_info['type'] = 'reserved'
            elif self.USER_DATA_START <= page_num <= self.USER_DATA_END:
                page_info['type'] = 'user_data'
            elif self.LOCK_BYTES_START <= page_num <= self.LOCK_BYTES_END:
                page_info['type'] = 'lock_bytes'
            elif self.CAPABILITY_CONTAINER_START <= page_num <= self.CAPABILITY_CONTAINER_END:
                page_info['type'] = 'capability_container'
            else:
                page_info['type'] = 'reserved'
            
            pages.append(page_info)
        
        return pages
    
    def get_summary(self) -> Dict:
        """Get a summary of the decoded data"""
        return {
            'uid': self.decoded_data.get('uid', {}).get('hex', 'Unknown'),
            'user_data_length': len(self.decoded_data.get('user_data', {}).get('bytes', b'')),
            'has_ndef': 'ndef_data' in self.decoded_data and 'error' not in self.decoded_data['ndef_data'],
            'ndef_type': self.decoded_data.get('ndef_data', {}).get('type', 'None'),
            'total_pages': self.TOTAL_PAGES,
            'total_bytes': self.TOTAL_BYTES
        }
    
    def print_summary(self):
        """Print a human-readable summary of the decoded data"""
        print("=== NTAG215 Decoded Data ===")
        print(f"UID: {self.decoded_data.get('uid', {}).get('hex', 'Unknown')}")
        print(f"Total Pages: {self.TOTAL_PAGES}")
        print(f"Total Bytes: {self.TOTAL_BYTES}")
        
        user_data = self.decoded_data.get('user_data', {})
        print(f"User Data Length: {len(user_data.get('bytes', b''))} bytes")
        
        ndef_data = self.decoded_data.get('ndef_data', {})
        if 'error' not in ndef_data:
            print(f"NDEF Type: {ndef_data.get('type', 'Unknown')}")
            print(f"NDEF Payload: {ndef_data.get('payload_text', '')}")
        else:
            print(f"NDEF: {ndef_data.get('error', 'Unknown error')}")
        
        print("-" * 30)

def decode_ntag215_raw_data(raw_data: bytes) -> Dict:
    """
    Convenience function to decode NTAG215 raw data
    
    Args:
        raw_data: Raw bytes from NTAG215 tag (144 bytes)
        
    Returns:
        Dictionary containing decoded information
    """
    decoder = NTAG215Decoder(raw_data)
    return decoder.decoded_data

def decode_ntag215_hex_string(hex_string: str) -> Dict:
    """
    Decode NTAG215 data from hex string
    
    Args:
        hex_string: Hex string representation of raw data
        
    Returns:
        Dictionary containing decoded information
    """
    # Remove spaces and convert to bytes
    hex_string = hex_string.replace(' ', '').replace('\n', '').replace('\t', '')
    raw_data = bytes.fromhex(hex_string)
    return decode_ntag215_raw_data(raw_data) 