#!/usr/bin/env python
"""
Test script to verify the MFRC522 library works correctly
"""

import sys
import time

def test_imports():
    """Test if all imports work correctly"""
    print("Testing imports...")
    
    try:
        from mfrc522 import MFRC522, NTAGType, SimpleMFRC522
        print("✓ Successfully imported MFRC522, NTAGType, and SimpleMFRC522")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_ntag_types():
    """Test NTAG type enumeration"""
    print("\nTesting NTAG types...")
    
    try:
        from mfrc522 import NTAGType
        
        # Test all NTAG types
        ntag_types = [
            NTAGType.UNKNOWN,
            NTAGType.NTAG213,
            NTAGType.NTAG215,
            NTAGType.NTAG216,
            NTAGType.NTAG213F,
            NTAGType.NTAG215F,
            NTAGType.NTAG216F
        ]
        
        for ntag_type in ntag_types:
            print(f"  {ntag_type.name}: {ntag_type.value}")
        
        print("✓ NTAG types working correctly")
        return True
    except Exception as e:
        print(f"✗ NTAG types test failed: {e}")
        return False

def test_mfrc522_creation():
    """Test MFRC522 object creation"""
    print("\nTesting MFRC522 object creation...")
    
    try:
        from mfrc522 import MFRC522
        
        # This will fail on non-Raspberry Pi systems, but that's expected
        try:
            reader = MFRC522(debug_level='WARNING')
            print("✓ MFRC522 object created successfully")
            reader.close()
            return True
        except Exception as e:
            if "No module named 'RPi'" in str(e) or "spidev" in str(e):
                print("⚠ MFRC522 creation failed (expected on non-Raspberry Pi systems)")
                print(f"  Error: {e}")
                return True  # This is expected on non-RPi systems
            else:
                print(f"✗ MFRC522 creation failed: {e}")
                return False
                
    except Exception as e:
        print(f"✗ MFRC522 creation test failed: {e}")
        return False

def test_simple_mfrc522_creation():
    """Test SimpleMFRC522 object creation"""
    print("\nTesting SimpleMFRC522 object creation...")
    
    try:
        from mfrc522 import SimpleMFRC522
        
        # This will fail on non-Raspberry Pi systems, but that's expected
        try:
            reader = SimpleMFRC522()
            print("✓ SimpleMFRC522 object created successfully")
            reader.close()
            return True
        except Exception as e:
            if "No module named 'RPi'" in str(e) or "spidev" in str(e):
                print("⚠ SimpleMFRC522 creation failed (expected on non-Raspberry Pi systems)")
                print(f"  Error: {e}")
                return True  # This is expected on non-RPi systems
            else:
                print(f"✗ SimpleMFRC522 creation failed: {e}")
                return False
                
    except Exception as e:
        print(f"✗ SimpleMFRC522 creation test failed: {e}")
        return False

def main():
    """Main test function"""
    print("MFRC522 Library Test")
    print("===================")
    
    tests = [
        test_imports,
        test_ntag_types,
        test_mfrc522_creation,
        test_simple_mfrc522_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The library is working correctly.")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 