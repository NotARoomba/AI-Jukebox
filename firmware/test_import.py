#!/usr/bin/env python
"""
Test script to verify NTAGType import works correctly
"""

try:
    from mfrc522 import MFRC522, NTAGType
    print("✓ Import successful!")
    print(f"Available NTAG types: {[t.name for t in NTAGType]}")
    print(f"NTAG213 value: {NTAGType.NTAG213}")
    print(f"NTAG215 value: {NTAGType.NTAG215}")
    print(f"NTAG216 value: {NTAGType.NTAG216}")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"✗ Other error: {e}")
    import traceback
    traceback.print_exc() 