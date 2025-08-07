#!/usr/bin/env python3

"""
Simple NFC Card Reader for RC522
This script reads NFC cards using an RC522 module connected to Raspberry Pi.

Hardware Setup:
- RC522 RFID Module connected to Raspberry Pi
- SDA (CS) -> GPIO 24 (CE0)
- SCK -> GPIO 23 (SCLK)
- MOSI -> GPIO 19 (MOSI)
- MISO -> GPIO 21 (MISO)
- GND -> GND
- VCC -> 3.3V
- RST -> GPIO 22

Dependencies:
    sudo apt-get install python3-spidev
    sudo apt-get install python3-rpi.gpio

Usage:
    python3 test.py
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

# RC522 Pin Configuration - Updated for new wiring
RST_PIN = 22
SDA_PIN = 24  # Updated from GPIO 8 to GPIO 24

# RC522 Commands
PCD_IDLE = 0x00
PCD_AUTHENT = 0x0E
PCD_RECEIVE = 0x08
PCD_TRANSMIT = 0x04
PCD_TRANSCEIVE = 0x0C
PCD_RESETPHASE = 0x0F
PCD_CALCCRC = 0x03

# Mifare_One Commands
PICC_REQIDL = 0x26
PICC_REQALL = 0x52
PICC_ANTICOLL = 0x93
PICC_SElECTTAG = 0x93
PICC_AUTHENT1A = 0x60
PICC_AUTHENT1B = 0x61
PICC_READ = 0x30
PICC_WRITE = 0xA0
PICC_DECREMENT = 0xC0
PICC_INCREMENT = 0xC1
PICC_RESTORE = 0xC2
PICC_TRANSFER = 0xB0
PICC_HALT = 0x50

# RC522 Registers
CommandReg = 0x01
ComIEnReg = 0x02
DivIEnReg = 0x03
ComIrqReg = 0x04
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
MfTxReg = 0x1C
MfRxReg = 0x1D
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

class RC522:
    def __init__(self, bus=0, device=0, speed=1000000, pin_rst=22, pin_ce=24):
        """
        Initialize RC522 with updated pin configuration
        
        Args:
            bus: SPI bus number (default: 0)
            device: SPI device number (default: 0)
            speed: SPI speed in Hz (default: 1000000)
            pin_rst: Reset pin (default: 22)
            pin_ce: Chip select pin (default: 24 - updated)
        """
        self.bus = bus
        self.device = device
        self.speed = speed
        self.pin_rst = pin_rst
        self.pin_ce = pin_ce
        
        # Initialize GPIO first
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin_rst, GPIO.OUT)
        GPIO.setup(pin_ce, GPIO.OUT)
        
        # Hardware reset RC522 using reset pin
        print(f"Performing hardware reset using RST pin (GPIO {pin_rst})...")
        GPIO.output(pin_rst, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(pin_rst, GPIO.HIGH)
        time.sleep(0.1)
        
        # Initialize SPI
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(bus, device)
            self.spi.max_speed_hz = speed
            self.spi.mode = 0
            print("✓ SPI initialized successfully")
        except Exception as e:
            print(f"Failed to initialize SPI: {e}")
            raise
        
        # Initialize RC522
        self.init()
    
    def init(self):
        """Initialize RC522"""
        print("Initializing RC522...")
        
        # Perform hardware reset first
        self.hardware_reset()
        time.sleep(0.1)
        
        # Check if RC522 is responding
        version = self.read_register(VersionReg)
        print(f"RC522 Version: 0x{version:02X}")
        
        if version == 0x00 or version == 0xFF:
            print("Warning: RC522 not responding properly. Check wiring and power.")
            print("  - Verify RST pin (GPIO 22) is connected")
            print("  - Check 3.3V power supply")
            print("  - Ensure all SPI connections are correct")
        
        # Set timer
        self.write_register(TModeReg, 0x8D)
        self.write_register(TPrescalerReg, 0x3E)
        self.write_register(TReloadRegL, 30)
        self.write_register(TReloadRegH, 0)
        self.write_register(TxAutoReg, 0x40)
        self.write_register(ModeReg, 0x3D)
        
        # Turn antenna on
        self.antenna_on()
        print("RC522 initialization complete")
    
    def hardware_reset(self):
        """Perform hardware reset using RST pin"""
        print(f"Hardware reset using RST pin (GPIO {self.pin_rst})...")
        GPIO.output(self.pin_rst, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(self.pin_rst, GPIO.HIGH)
        time.sleep(0.1)
        print("✓ Hardware reset completed")
    
    def reset(self):
        """Reset RC522 using both hardware and software reset"""
        # Hardware reset first
        self.hardware_reset()
        
        # Software reset
        self.write_register(CommandReg, PCD_RESETPHASE)
        time.sleep(0.1)
    
    def write_register(self, address, value):
        """Write to RC522 register"""
        address = ((address << 1) & 0x7E) | 0x80
        self.spi.xfer([address, value])
    
    def read_register(self, address):
        """Read from RC522 register"""
        address = (address << 1) & 0x7E
        result = self.spi.xfer([address, 0])
        return result[1]
    
    def antenna_on(self):
        """Turn antenna on"""
        temp = self.read_register(TxControlReg)
        if ~(temp & 0x03):
            self.write_register(TxControlReg, temp | 0x03)
    
    def antenna_off(self):
        """Turn antenna off"""
        temp = self.read_register(TxControlReg)
        self.write_register(TxControlReg, temp & (~0x03))
    
    def to_card(self, command, send_data):
        """Send command to card"""
        back_data = []
        back_len = 0
        status = 0
        irq_en = 0x00
        wait_irq = 0x00
        last_bits = 0
        n = 0
        i = 0
        
        if command == PCD_AUTHENT:
            irq_en = 0x12
            wait_irq = 0x10
        if command == PCD_TRANSCEIVE:
            irq_en = 0x77
            wait_irq = 0x30
        
        self.write_register(ComIEnReg, irq_en | 0x80)
        self.clear_bit_mask(ComIrqReg, 0x80)
        self.set_bit_mask(FIFOLevelReg, 0x80)
        
        self.write_register(CommandReg, PCD_IDLE)
        
        while i < len(send_data):
            self.write_register(FIFODataReg, send_data[i])
            i += 1
        
        self.write_register(CommandReg, command)
        if command == PCD_TRANSCEIVE:
            self.set_bit_mask(BitFramingReg, 0x80)
        
        i = 2000
        while True:
            n = self.read_register(ComIrqReg)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break
        
        self.clear_bit_mask(BitFramingReg, 0x80)
        
        if i != 0:
            if (self.read_register(ErrorReg) & 0x1B) == 0x00:
                status = 0
                if n & irq_en & 0x01:
                    status = 1
                
                if command == PCD_TRANSCEIVE:
                    n = self.read_register(FIFOLevelReg)
                    last_bits = self.read_register(ControlReg) & 0x07
                    if last_bits != 0:
                        back_len = (n - 1) * 8 + last_bits
                    else:
                        back_len = n * 8
                    
                    if n == 0:
                        n = 1
                    if n > 16:
                        n = 16
                    
                    i = 0
                    while i < n:
                        back_data.append(self.read_register(FIFODataReg))
                        i += 1
            else:
                status = 2
        
        return status, back_data, back_len
    
    def request(self, req_mode):
        """Request card"""
        self.write_register(BitFramingReg, 0x07)
        (status, back_data, back_bits) = self.to_card(PCD_TRANSCEIVE, [req_mode])
        if ((status != 0) or (back_bits != 0x10)):
            status = 2
        return status, back_data
    
    def anticoll(self):
        """Anticollision"""
        back_data = []
        ser_num_check = 0
        
        ser_num = []
        
        self.write_register(BitFramingReg, 0x00)
        
        ser_num.append(PICC_ANTICOLL)
        ser_num.append(0x20)
        
        (status, back_data, back_bits) = self.to_card(PCD_TRANSCEIVE, ser_num)
        
        if status == 0:
            i = 0
            if len(back_data) == 5:
                while i < 4:
                    ser_num_check = ser_num_check ^ back_data[i]
                    i += 1
                if ser_num_check != back_data[i]:
                    status = 2
            else:
                status = 2
        
        return status, back_data
    
    def calculate_crc(self, p_indata):
        """Calculate CRC"""
        self.clear_bit_mask(DivIrqReg, 0x04)
        self.set_bit_mask(FIFOLevelReg, 0x80)
        i = 0
        while i < len(p_indata):
            self.write_register(FIFODataReg, p_indata[i])
            i += 1
        self.write_register(CommandReg, PCD_CALCCRC)
        i = 0xFF
        while True:
            n = self.read_register(DivIrqReg)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break
        p_outdata = []
        p_outdata.append(self.read_register(CRCResultRegL))
        p_outdata.append(self.read_register(CRCResultRegM))
        return p_outdata
    
    def select_tag(self, ser_num):
        """Select tag"""
        back_data = []
        back_data.append(PICC_SElECTTAG)
        back_data.append(0x70)
        i = 0
        while i < 5:
            back_data.append(ser_num[i])
            i += 1
        p_out = self.calculate_crc(back_data)
        back_data.append(p_out[0])
        back_data.append(p_out[1])
        (status, back_data, back_len) = self.to_card(PCD_TRANSCEIVE, back_data)
        if (status == 0) and (back_len == 0x18):
            return 0
        else:
            return 2
    
    def auth(self, auth_mode, block_addr, sectorkey, ser_num):
        """Authentication"""
        buff = []
        buff.append(auth_mode)
        buff.append(block_addr)
        i = 0
        while i < len(sectorkey):
            buff.append(sectorkey[i])
            i += 1
        i = 0
        while i < 4:
            buff.append(ser_num[i])
            i += 1
        (status, back_data, back_len) = self.to_card(PCD_AUTHENT, buff)
        if not (status == 0):
            return 2
        if not (self.read_register(Status2Reg) & 0x08) != 0:
            return 2
        return 0
    
    def read(self, block_addr):
        """Read block"""
        recv_data = []
        recv_data.append(PICC_READ)
        recv_data.append(block_addr)
        p_out = self.calculate_crc(recv_data)
        recv_data.append(p_out[0])
        recv_data.append(p_out[1])
        (status, back_data, back_len) = self.to_card(PCD_TRANSCEIVE, recv_data)
        if not (status == 0):
            return 2
        if len(back_data) == 16:
            return 0, back_data
        return 2, []
    
    def write(self, block_addr, write_data):
        """Write block"""
        buff = []
        buff.append(PICC_WRITE)
        buff.append(block_addr)
        crc = self.calculate_crc(buff)
        buff.append(crc[0])
        buff.append(crc[1])
        (status, back_data, back_len) = self.to_card(PCD_TRANSCEIVE, buff)
        if not (status == 0) or not (back_len == 4) or not ((back_data[0] & 0x0F) == 0x0A):
            return 2
        buff = []
        i = 0
        while i < 16:
            buff.append(write_data[i])
            i += 1
        crc = self.calculate_crc(buff)
        buff.append(crc[0])
        buff.append(crc[1])
        (status, back_data, back_len) = self.to_card(PCD_TRANSCEIVE, buff)
        if not (status == 0) or not (back_len == 4) or not ((back_data[0] & 0x0F) == 0x0A):
            return 2
        return 0
    
    def halt(self):
        """Halt card"""
        buff = []
        buff.append(PICC_HALT)
        buff.append(0)
        crc = self.calculate_crc(buff)
        buff.append(crc[0])
        buff.append(crc[1])
        (status, back_data, back_len) = self.to_card(PCD_TRANSCEIVE, buff)
    
    def set_bit_mask(self, reg, mask):
        """Set bit mask"""
        tmp = self.read_register(reg)
        self.write_register(reg, tmp | mask)
    
    def clear_bit_mask(self, reg, mask):
        """Clear bit mask"""
        tmp = self.read_register(reg)
        self.write_register(reg, tmp & (~mask))
    
    def close(self):
        """Close SPI connection"""
        if hasattr(self, 'spi'):
            self.spi.close()
        GPIO.cleanup()

def main():
    """Main function"""
    print("=== RC522 NFC Card Reader (Updated Pins) ===")
    print("Hardware Setup:")
    print("- SDA (CS) -> GPIO 24 (CE0)")
    print("- SCK -> GPIO 23 (SCLK)")
    print("- MOSI -> GPIO 19 (MOSI)")
    print("- MISO -> GPIO 21 (MISO)")
    print("- GND -> GND")
    print("- VCC -> 3.3V")
    print("- RST -> GPIO 22 (Hardware Reset)")
    print("")
    print("Initialization process:")
    print("1. Hardware reset using RST pin (GPIO 22)")
    print("2. SPI initialization")
    print("3. RC522 configuration")
    print("4. Antenna activation")
    print("")
    print("Place an NFC card on the reader...")
    print("Press Ctrl+C to exit")
    print("-" * 50)
    
    try:
        # Initialize RC522 with updated pins
        print("Initializing RC522...")
        reader = RC522(pin_rst=22, pin_ce=24)
        print("✓ RC522 initialized successfully with updated pin configuration")
        print("✓ Hardware reset pin (GPIO 22) configured and tested")
        
        last_uid = None
        while True:
            try:
                # Request card
                (status, tag_type) = reader.request(PICC_REQIDL)
                if status == 0:
                    print("✓ Card detected!")
                    
                    # Anticollision
                    (status, uid) = reader.anticoll()
                    if status == 0:
                        # Convert UID to hex string
                        uid_hex = ''.join([f'{b:02X}' for b in uid[:4]])
                        
                        # Check if it's the same card
                        if last_uid == uid_hex:
                            time.sleep(0.5)
                            continue
                        
                        print(f"Card UID: {uid_hex}")
                        last_uid = uid_hex
                        
                        # Select card
                        if reader.select_tag(uid) == 0:
                            print("✓ Card selected successfully")
                            
                            # Read first block (block 0)
                            (status, data) = reader.read(0)
                            if status == 0:
                                print("Block 0 data:", ' '.join([f'{b:02X}' for b in data]))
                            else:
                                print("✗ Failed to read block 0")
                        else:
                            print("✗ Failed to select card")
                    
                    # Halt card
                    reader.halt()
                    print("-" * 50)
                else:
                    # No card detected, reset last_uid after a delay
                    if last_uid is not None:
                        time.sleep(1)
                        last_uid = None
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error during card detection: {e}")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'reader' in locals():
            reader.close()
        print("Cleanup complete")

if __name__ == '__main__':
    main()
