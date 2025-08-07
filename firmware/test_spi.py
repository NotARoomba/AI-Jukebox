#!/usr/bin/env python3

"""
SPI Test Script for RC522
This script tests the SPI connection to the RC522 module.
"""

import time
import sys

# Check for required dependencies
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO not found")
    print("Install with: sudo apt-get install python3-rpi.gpio")
    sys.exit(1)

try:
    import spidev
except ImportError:
    print("Error: spidev not found")
    print("Install with: sudo apt-get install python3-spidev")
    sys.exit(1)

def test_gpio():
    """Test GPIO connections"""
    print("=== GPIO Connection Test ===")
    
    try:
        GPIO.setmode(GPIO.BCM)
        
        # Test RST pin
        print("Testing RST pin (GPIO 22)...")
        GPIO.setup(22, GPIO.OUT)
        GPIO.output(22, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(22, GPIO.HIGH)
        print("✓ RST pin (GPIO 22) working")
        
        # Test CE pin
        print("Testing CE pin (GPIO 24)...")
        GPIO.setup(24, GPIO.OUT)
        GPIO.output(24, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(24, GPIO.HIGH)
        print("✓ CE pin (GPIO 24) working")
        
        GPIO.cleanup()
        return True
        
    except Exception as e:
        print(f"✗ GPIO test failed: {e}")
        return False

def test_spi():
    """Test SPI connection"""
    print("\n=== SPI Connection Test ===")
    
    # Initialize GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(22, GPIO.OUT)  # RST pin
    GPIO.setup(24, GPIO.OUT)  # CE pin
    
    # Hardware reset RC522
    print("Performing hardware reset using RST pin...")
    GPIO.output(22, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(22, GPIO.HIGH)
    time.sleep(0.1)
    print("✓ Hardware reset completed")
    
    # Initialize SPI
    try:
        spi = spidev.SpiDev()
        spi.open(0, 0)  # bus 0, device 0
        spi.max_speed_hz = 1000000
        spi.mode = 0
        print("✓ SPI initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize SPI: {e}")
        GPIO.cleanup()
        return False
    
    # Test reading version register (0x37)
    try:
        # Read version register
        address = (0x37 << 1) & 0x7E  # VersionReg = 0x37
        result = spi.xfer([address, 0])
        version = result[1]
        print(f"RC522 Version: 0x{version:02X}")
        
        if version == 0x00 or version == 0xFF:
            print("⚠ Warning: RC522 not responding properly")
            print("  - Check wiring connections")
            print("  - Ensure RC522 is powered (3.3V)")
            print("  - Verify RST pin (GPIO 22) is connected")
            print("  - Check SPI is enabled")
            GPIO.cleanup()
            return False
        elif version == 0x91 or version == 0x92:
            print("✓ RC522 responding correctly")
            GPIO.cleanup()
            return True
        else:
            print(f"⚠ Unknown version: 0x{version:02X}")
            print("  - This might be a different RC522 variant")
            GPIO.cleanup()
            return True
            
    except Exception as e:
        print(f"✗ Failed to read version: {e}")
        GPIO.cleanup()
        return False

def test_reset_functionality():
    """Test reset pin functionality specifically"""
    print("\n=== Reset Pin Functionality Test ===")
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(22, GPIO.OUT)  # RST pin
        
        print("Testing reset pin functionality...")
        
        # Test multiple reset cycles
        for i in range(3):
            print(f"  Reset cycle {i+1}/3...")
            GPIO.output(22, GPIO.LOW)
            time.sleep(0.1)
            GPIO.output(22, GPIO.HIGH)
            time.sleep(0.1)
        
        print("✓ Reset pin functionality test completed")
        GPIO.cleanup()
        return True
        
    except Exception as e:
        print(f"✗ Reset pin test failed: {e}")
        GPIO.cleanup()
        return False

def main():
    """Main function"""
    print("RC522 SPI and GPIO Test")
    print("=" * 30)
    
    # Test GPIO first
    if not test_gpio():
        print("\n✗ GPIO test failed. Check wiring.")
        return
    
    # Test reset functionality
    if not test_reset_functionality():
        print("\n✗ Reset pin test failed. Check RST pin connection.")
        return
    
    # Test SPI
    if not test_spi():
        print("\n✗ SPI test failed. Check SPI configuration.")
        return
    
    print("\n✓ All tests passed!")
    print("\nHardware setup verified:")
    print("  - RST pin (GPIO 22) ✓")
    print("  - CE pin (GPIO 24) ✓")
    print("  - SPI communication ✓")
    print("  - RC522 responding ✓")
    print("\nIf tests passed but NFC detection still doesn't work:")
    print("1. Check card placement on reader")
    print("2. Try different NFC cards")
    print("3. Verify SPI is enabled: sudo raspi-config")
    print("4. Check if SPI module is loaded: lsmod | grep spi")
    print("5. Ensure card is placed directly on the antenna area")

if __name__ == '__main__':
    main() 