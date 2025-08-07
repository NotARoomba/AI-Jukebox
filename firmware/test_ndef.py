#!/usr/bin/env python
"""
Test script to demonstrate NDEF record functionality
"""

import sys
import time

def test_ndef_imports():
    """Test if NDEF imports work correctly"""
    print("Testing NDEF imports...")
    
    try:
        from mfrc522 import MFRC522, NTAGType, NDEFRecord
        print("✓ Successfully imported MFRC522, NTAGType, and NDEFRecord")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_ndef_record_creation():
    """Test NDEF record creation"""
    print("\nTesting NDEF record creation...")
    
    try:
        from mfrc522 import NDEFRecord
        
        # Test text record
        text_record = NDEFRecord("text", "Hello, World!", "en")
        text_bytes = text_record.to_bytes()
        print(f"✓ Text record created: {len(text_bytes)} bytes")
        
        # Test URL record
        url_record = NDEFRecord("url", "example.com")
        url_bytes = url_record.to_bytes()
        print(f"✓ URL record created: {len(url_bytes)} bytes")
        
        # Test record parsing
        parsed_record = NDEFRecord.from_bytes(text_bytes)
        if parsed_record and parsed_record.payload == "Hello, World!":
            print("✓ Record parsing works correctly")
        else:
            print("✗ Record parsing failed")
            return False
        
        return True
    except Exception as e:
        print(f"✗ NDEF record creation failed: {e}")
        return False

def test_ndef_message_creation():
    """Test NDEF message creation"""
    print("\nTesting NDEF message creation...")
    
    try:
        from mfrc522 import NDEFRecord, MFRC522
        
        # Create multiple records
        records = [
            NDEFRecord("text", "First record", "en"),
            NDEFRecord("url", "example.com"),
            NDEFRecord("text", "Third record", "en")
        ]
        
        # Set message flags
        records[0].mb = True  # Message Begin
        records[-1].me = True  # Message End
        
        # Create message
        reader = MFRC522(debug_level='WARNING')
        ndef_message = reader._create_ndef_message(records)
        
        if ndef_message:
            print(f"✓ NDEF message created: {len(ndef_message)} bytes")
            
            # Test TLV creation
            tlv_data = reader._create_ndef_tlv(ndef_message)
            if tlv_data:
                print(f"✓ TLV structure created: {len(tlv_data)} bytes")
                return True
            else:
                print("✗ TLV structure creation failed")
                return False
        else:
            print("✗ NDEF message creation failed")
            return False
            
    except Exception as e:
        print(f"✗ NDEF message creation failed: {e}")
        return False

def test_ndef_reading_simulation():
    """Test NDEF reading simulation"""
    print("\nTesting NDEF reading simulation...")
    
    try:
        from mfrc522 import NDEFRecord, MFRC522
        
        # Create test NDEF data
        text_record = NDEFRecord("text", "Test message", "en")
        text_record.mb = True
        text_record.me = True
        
        reader = MFRC522(debug_level='WARNING')
        ndef_message = reader._create_ndef_message([text_record])
        tlv_data = reader._create_ndef_tlv(ndef_message)
        
        # Simulate reading
        extracted_ndef = reader._extract_ndef_tlv(tlv_data)
        if extracted_ndef:
            records = reader._parse_ndef_message(extracted_ndef)
            if records and len(records) == 1:
                record = records[0]
                if record.record_type == "text" and record.payload == "Test message":
                    print("✓ NDEF reading simulation successful")
                    return True
                else:
                    print("✗ NDEF reading simulation failed - wrong record content")
                    return False
            else:
                print("✗ NDEF reading simulation failed - no records parsed")
                return False
        else:
            print("✗ NDEF reading simulation failed - no NDEF data extracted")
            return False
            
    except Exception as e:
        print(f"✗ NDEF reading simulation failed: {e}")
        return False

def main():
    """Main test function"""
    print("NDEF Record Test")
    print("================")
    
    tests = [
        test_ndef_imports,
        test_ndef_record_creation,
        test_ndef_message_creation,
        test_ndef_reading_simulation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All NDEF tests passed! The library is working correctly.")
        return 0
    else:
        print("⚠ Some NDEF tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 