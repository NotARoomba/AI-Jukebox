#!/usr/bin/env python3
"""
NTAG215 Test Script

This script provides a unified interface for testing NTAG215 NFC tags.
It can read from tags and write data to tags.

Usage:
    python test.py          # Read from tag
    python test.py -w "text"  # Write text to tag
"""

import argparse
import sys
import time
import RPi.GPIO as GPIO
from typing import Optional

# Try to import the enhanced reader and decoder
try:
    from enhanced_rfid_reader import EnhancedRFIDReader
    from ntag215_decoder import NTAG215Decoder
    ENHANCED_AVAILABLE = True
except ImportError as e:
    print(f"Enhanced reader not available: {e}")
    ENHANCED_AVAILABLE = False

# Import the local mfrc522 library
try:
    from mfrc522.MFRC522 import MFRC522
    from mfrc522.SimpleMFRC522 import SimpleMFRC522
    MFRC522_AVAILABLE = True
except ImportError as e:
    print(f"Local MFRC522 library not available: {e}")
    MFRC522_AVAILABLE = False

# Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

class NTAG215Tester:
    """NTAG215 test class for reading and writing tags"""
    
    def __init__(self):
        """Initialize the NTAG215 tester"""
        if ENHANCED_AVAILABLE:
            self.reader = EnhancedRFIDReader()
            self.use_enhanced = True
        else:
            if MFRC522_AVAILABLE:
                self.reader = SimpleMFRC522()
                self.use_enhanced = False
            else:
                raise ImportError("No MFRC522 library available")
    
    def read_tag(self) -> Optional[dict]:
        """
        Read data from NTAG215 tag
        
        Returns:
            Decoded tag data or None if failed
        """
        print("=== Reading NTAG215 Tag ===")
        print("Place a tag near the reader...")
        
        try:
            if self.use_enhanced:
                # Use enhanced reader for NTAG215 decoding
                decoded_data = self.reader.read_and_decode_ntag215()
                
                if decoded_data:
                    print("✓ NTAG215 tag detected and decoded!")
                    
                    # Print tag summary
                    uid = decoded_data.get('uid', {}).get('hex', 'Unknown')
                    print(f"UID: {uid}")
                    
                    user_data = decoded_data.get('user_data', {})
                    user_bytes = user_data.get('bytes', b'')
                    print(f"User Data Length: {len(user_bytes)} bytes")
                    
                    # Try to decode user data as text
                    if user_bytes:
                        try:
                            user_text = user_bytes.decode('utf-8', errors='ignore').strip('\x00')
                            if user_text:
                                print(f"User Data Text: {user_text}")
                        except:
                            print(f"User Data Hex: {user_bytes.hex()[:64]}...")
                    
                    # Check for NDEF data
                    ndef_data = decoded_data.get('ndef_data', {})
                    if 'error' not in ndef_data:
                        print(f"NDEF Type: {ndef_data.get('type', 'Unknown')}")
                        print(f"NDEF Payload: {ndef_data.get('payload_text', '')}")
                    else:
                        print(f"NDEF: {ndef_data.get('error', 'No NDEF data')}")
                    
                    # Print first few pages
                    print("\nFirst 5 pages:")
                    pages = decoded_data.get('page_dump', [])
                    for page in pages[:5]:
                        print(f"  Page {page['page']:2d}: {page['hex']} | {page['ascii']}")
                    
                    return decoded_data
                else:
                    print("⚠ No tag detected or failed to decode")
                    return None
            else:
                # Use basic reader
                tag_id, tag_text = self.reader.read()
                print("✓ Tag detected!")
                print(f"ID: {tag_id}")
                print(f"Text: {tag_text.strip()}")
                
                # Create basic decoded data structure
                decoded_data = {
                    'uid': {
                        'hex': f"{tag_id:08X}",
                        'decimal': tag_id
                    },
                    'user_data': {
                        'bytes': tag_text.encode('utf-8'),
                        'text': tag_text.strip()
                    },
                    'ndef_data': {'error': 'Basic reader - no NDEF support'}
                }
                
                return decoded_data
                
        except Exception as e:
            error_msg = str(e)
            if "AUTH ERROR" in error_msg or "status2reg" in error_msg:
                print(f"⚠ AUTH ERROR detected: {error_msg}")
                print("  Troubleshooting:")
                print("  - Move tag closer to reader")
                print("  - Try a different tag")
                print("  - Check wiring connections")
                print("  - Ensure stable power supply")
            else:
                print(f"⚠ Error reading tag: {error_msg}")
            return None
    
    def write_tag(self, text: str) -> bool:
        """
        Write text to NTAG215 tag
        
        Args:
            text: Text to write to the tag
            
        Returns:
            True if successful, False otherwise
        """
        print(f"=== Writing to NTAG215 Tag ===")
        print(f"Text to write: {text}")
        print("Place a tag near the reader...")
        
        try:
            if self.use_enhanced:
                # Use enhanced reader for writing
                return self._write_with_enhanced_reader(text)
            else:
                # Use basic reader for writing
                return self._write_with_basic_reader(text)
                
        except Exception as e:
            error_msg = str(e)
            if "AUTH ERROR" in error_msg or "status2reg" in error_msg:
                print(f"⚠ AUTH ERROR detected: {error_msg}")
                print("  Troubleshooting:")
                print("  - Move tag closer to reader")
                print("  - Try a different tag")
                print("  - Check wiring connections")
                print("  - Ensure stable power supply")
            else:
                print(f"⚠ Error writing to tag: {error_msg}")
            return False
    
    def _write_with_enhanced_reader(self, text: str) -> bool:
        """Write using enhanced reader with MFRC522_WriteUltralight"""
        try:
            # Initialize the reader
            self.reader.reader.MFRC522_Init()
            
            # Wait for tag
            while True:
                (status, tag_type) = self.reader.reader.MFRC522_Request(self.reader.reader.PICC_REQIDL)
                if status == self.reader.reader.MI_OK:
                    print("Tag detected!")
                    break
                time.sleep(0.1)
            
            # Get UID
            (status, uid) = self.reader.reader.MFRC522_Anticoll()
            if status != self.reader.reader.MI_OK:
                print("Failed to get UID")
                return False
            
            print(f"UID: {uid}")
            
            # Convert text to bytes
            text_bytes = text.encode('utf-8')
            print(f"Text bytes: {text_bytes.hex().upper()}")
            
            # Write to user data area (starting from page 4)
            user_data_start_page = 4
            bytes_written = 0
            
            # Calculate how many pages we need
            total_pages_needed = (len(text_bytes) + 3) // 4  # Ceiling division
            print(f"Need to write {total_pages_needed} pages for {len(text_bytes)} bytes")
            
            # Write text bytes to user data area using MFRC522_WriteUltralight
            for i in range(0, len(text_bytes), 4):
                page = user_data_start_page + (i // 4)
                
                # Create a 4-byte page data array
                page_data = [0x00] * 4  # Initialize with zeros
                
                # Fill page with text data - ensure we don't go out of bounds
                for j in range(4):
                    if i + j < len(text_bytes):
                        page_data[j] = text_bytes[i + j]
                    else:
                        page_data[j] = 0x00  # Fill with zeros
                
                print(f"Preparing page {page}: {bytes(page_data).hex().upper()}")
                
                # Write page using MFRC522_WriteUltralight
                try:
                    print(f"Writing page {page} with data: {page_data}")
                    # MFRC522_WriteUltralight handles errors internally and logs them
                    self.reader.reader.MFRC522_WriteUltralight(page, page_data)
                    bytes_written += min(4, len(text_bytes) - i)
                    print(f"✓ Wrote page {page}: {bytes(page_data).hex().upper()}")
                        
                except Exception as e:
                    print(f"✗ Failed to write page {page}: {e}")
                    return False
            
            print(f"✓ Successfully wrote {bytes_written} bytes to tag")
            return True
            
        except Exception as e:
            print(f"Error writing with enhanced reader: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Stop crypto
            self.reader.reader.MFRC522_StopCrypto1()
    
    def _write_with_basic_reader(self, text: str) -> bool:
        """Write using basic reader"""
        try:
            # Use the basic reader's write method
            self.reader.write(text)
            print(f"✓ Successfully wrote text to tag")
            return True
        except Exception as e:
            print(f"Error writing with basic reader: {e}")
            return False
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            GPIO.cleanup()
            print("✓ GPIO cleanup completed")
        except:
            pass

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='NTAG215 Test Script')
    parser.add_argument('-w', '--write', type=str, help='Text to write to the tag')
    args = parser.parse_args()
    
    print("NTAG215 Test Script")
    print("=" * 50)
    
    if ENHANCED_AVAILABLE:
        print("✓ Enhanced RFID reader with NTAG215 support available")
    else:
        print("⚠ Using basic RFID reader (enhanced features not available)")
    
    if MFRC522_AVAILABLE:
        print("✓ Local MFRC522 library available")
    else:
        print("⚠ Local MFRC522 library not available")
    
    tester = NTAG215Tester()
    
    try:
        if args.write:
            # Write mode
            success = tester.write_tag(args.write)
            if success:
                print("\n✓ Write operation completed successfully!")
            else:
                print("\n✗ Write operation failed!")
                sys.exit(1)
        else:
            # Read mode
            decoded_data = tester.read_tag()
            if decoded_data:
                print("\n✓ Read operation completed successfully!")
            else:
                print("\n✗ Read operation failed!")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main() 