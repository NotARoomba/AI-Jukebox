#!/usr/bin/env python3

"""
Test script to verify the MFRC522 library import works correctly.
"""

import sys
import os

# Add the mfrc522_new folder to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'mfrc522_new'))

try:
    from mfrc522_new import MFRC522, StatusCode, PICC_Type
    print("✓ Successfully imported MFRC522 library!")
    print(f"  - MFRC522 class: {MFRC522}")
    print(f"  - StatusCode enum: {StatusCode}")
    print(f"  - PICC_Type enum: {PICC_Type}")
    print("\nLibrary is ready to use!")
except ImportError as e:
    print(f"✗ Error importing MFRC522 library: {e}")
    print("Make sure the mfrc522_new.py file exists in the mfrc522_new folder.")
    sys.exit(1) 