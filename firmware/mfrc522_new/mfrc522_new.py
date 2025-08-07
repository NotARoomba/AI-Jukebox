#!/usr/bin/env python3

"""
MFRC522 Python Library for Raspberry Pi
Based on the C++ MFRC522 library by Dr.Leong, Miguel Balboa, Søren Thing Andersen, Tom Clement, and others.

This library provides a Python interface to the MFRC522 RFID/NFC reader module.
"""

import time
import spidev
import RPi.GPIO as GPIO
from enum import IntEnum
from typing import List, Optional, Tuple, Union


class PCD_Register(IntEnum):
    """MFRC522 registers. Described in chapter 9 of the datasheet."""
    # Page 0: Command and status
    CommandReg = 0x01 << 1
    ComIEnReg = 0x02 << 1
    DivIEnReg = 0x03 << 1
    ComIrqReg = 0x04 << 1
    DivIrqReg = 0x05 << 1
    ErrorReg = 0x06 << 1
    Status1Reg = 0x07 << 1
    Status2Reg = 0x08 << 1
    FIFODataReg = 0x09 << 1
    FIFOLevelReg = 0x0A << 1
    WaterLevelReg = 0x0B << 1
    ControlReg = 0x0C << 1
    BitFramingReg = 0x0D << 1
    CollReg = 0x0E << 1
    ModeReg = 0x11 << 1
    TxModeReg = 0x12 << 1
    RxModeReg = 0x13 << 1
    TxControlReg = 0x14 << 1
    TxAutoReg = 0x15 << 1
    TxSelReg = 0x16 << 1
    RxSelReg = 0x17 << 1
    RxThresholdReg = 0x18 << 1
    DemodReg = 0x19 << 1
    MfTxReg = 0x1C << 1
    MfRxReg = 0x1D << 1
    SerialSpeedReg = 0x1F << 1
    CRCResultRegM = 0x21 << 1
    CRCResultRegL = 0x22 << 1
    ModWidthReg = 0x24 << 1
    RFCfgReg = 0x26 << 1
    GsNReg = 0x27 << 1
    CWGsPReg = 0x28 << 1
    ModGsPReg = 0x29 << 1
    TModeReg = 0x2A << 1
    TPrescalerReg = 0x2B << 1
    TReloadRegH = 0x2C << 1
    TReloadRegL = 0x2D << 1
    TCounterValueRegH = 0x2E << 1
    TCounterValueRegL = 0x2F << 1
    TestSel1Reg = 0x31 << 1
    TestSel2Reg = 0x32 << 1
    TestPinEnReg = 0x33 << 1
    TestPinValueReg = 0x34 << 1
    TestBusReg = 0x35 << 1
    AutoTestReg = 0x36 << 1
    VersionReg = 0x37 << 1
    AnalogTestReg = 0x38 << 1
    TestDAC1Reg = 0x39 << 1
    TestDAC2Reg = 0x3A << 1
    TestADCReg = 0x3B << 1


class PCD_Command(IntEnum):
    """PCD commands"""
    PCD_IDLE = 0x00
    PCD_AUTHENT = 0x0E
    PCD_RECEIVE = 0x08
    PCD_TRANSMIT = 0x04
    PCD_TRANSCEIVE = 0x0C
    PCD_RESETPHASE = 0x0F
    PCD_CALCCRC = 0x03


class PICC_Command(IntEnum):
    """PICC commands"""
    PICC_CMD_REQA = 0x26
    PICC_CMD_WUPA = 0x52
    PICC_CMD_CT = 0x88
    PICC_CMD_SEL_CL1 = 0x93
    PICC_CMD_SEL_CL2 = 0x95
    PICC_CMD_SEL_CL3 = 0x97
    PICC_CMD_HLTA = 0x50
    PICC_CMD_MF_AUTH_KEY_A = 0x60
    PICC_CMD_MF_AUTH_KEY_B = 0x61
    PICC_CMD_MF_READ = 0x30
    PICC_CMD_MF_WRITE = 0xA0
    PICC_CMD_MF_DECREMENT = 0xC0
    PICC_CMD_MF_INCREMENT = 0xC1
    PICC_CMD_MF_RESTORE = 0xC2
    PICC_CMD_MF_TRANSFER = 0xB0
    PICC_CMD_UL_WRITE = 0xA2


class PICC_Type(IntEnum):
    """PICC types we can detect"""
    PICC_TYPE_UNKNOWN = 0
    PICC_TYPE_ISO_14443_4 = 1
    PICC_TYPE_ISO_18092 = 2
    PICC_TYPE_MIFARE_MINI = 3
    PICC_TYPE_MIFARE_1K = 4
    PICC_TYPE_MIFARE_4K = 5
    PICC_TYPE_MIFARE_UL = 6
    PICC_TYPE_MIFARE_PLUS = 7
    PICC_TYPE_MIFARE_DESFIRE = 8
    PICC_TYPE_TNP3XXX = 9
    PICC_TYPE_NOT_COMPLETE = 0xff


class StatusCode(IntEnum):
    """Return codes from the functions"""
    STATUS_OK = 0
    STATUS_ERROR = 1
    STATUS_COLLISION = 2
    STATUS_TIMEOUT = 3
    STATUS_NO_ROOM = 4
    STATUS_INTERNAL_ERROR = 5
    STATUS_INVALID = 6
    STATUS_CRC_WRONG = 7
    STATUS_MIFARE_NACK = 0xff


class Uid:
    """A struct used for passing the UID of a PICC"""
    def __init__(self):
        self.size = 0  # Number of bytes in the UID. 4, 7 or 10.
        self.uid_byte = [0] * 10  # UID bytes
        self.sak = 0  # The SAK (Select acknowledge) byte returned from the PICC after successful selection.


class MIFARE_Key:
    """A struct used for passing a MIFARE Crypto1 key"""
    def __init__(self):
        self.key_byte = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]  # Default key


class MFRC522:
    """MFRC522 RFID/NFC reader library for Raspberry Pi"""
    
    # Size of the MFRC522 FIFO
    FIFO_SIZE = 64
    
    def __init__(self, chip_select_pin: int = 24, reset_power_down_pin: int = 22, 
                 bus: int = 0, device: int = 0, speed: int = 4000000):
        """
        Constructor.
        
        Args:
            chip_select_pin: Raspberry Pi pin connected to MFRC522's SPI slave select input
            reset_power_down_pin: Raspberry Pi pin connected to MFRC522's reset and power down input
            bus: SPI bus number
            device: SPI device number
            speed: SPI speed in Hz
        """
        self._chip_select_pin = chip_select_pin
        self._reset_power_down_pin = reset_power_down_pin
        self._bus = bus
        self._device = device
        self._speed = speed
        self._spi = None
        self.uid = Uid()
        
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._chip_select_pin, GPIO.OUT)
        GPIO.setup(self._reset_power_down_pin, GPIO.OUT)
        
        # Initialize SPI
        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = speed
        self._spi.mode = 0
        
        # Initialize the MFRC522
        self.PCD_Init()
    
    def __del__(self):
        """Destructor"""
        if hasattr(self, '_spi') and self._spi:
            self._spi.close()
        GPIO.cleanup()
    
    def PCD_WriteRegister(self, reg: PCD_Register, value: int) -> None:
        """
        Writes a byte to the specified register in the MFRC522 chip.
        
        Args:
            reg: The register to write to
            value: The value to write
        """
        GPIO.output(self._chip_select_pin, GPIO.LOW)
        self._spi.xfer([reg, value])
        GPIO.output(self._chip_select_pin, GPIO.HIGH)
    
    def PCD_ReadRegister(self, reg: PCD_Register) -> int:
        """
        Reads a byte from the specified register in the MFRC522 chip.
        
        Args:
            reg: The register to read from
            
        Returns:
            The value read from the register
        """
        GPIO.output(self._chip_select_pin, GPIO.LOW)
        result = self._spi.xfer([0x80 | reg, 0])
        GPIO.output(self._chip_select_pin, GPIO.HIGH)
        return result[1]
    
    def PCD_SetRegisterBitMask(self, reg: PCD_Register, mask: int) -> None:
        """
        Sets the bits given in mask in register reg.
        
        Args:
            reg: The register to update
            mask: The bits to set
        """
        tmp = self.PCD_ReadRegister(reg)
        self.PCD_WriteRegister(reg, tmp | mask)
    
    def PCD_ClearRegisterBitMask(self, reg: PCD_Register, mask: int) -> None:
        """
        Clears the bits given in mask from register reg.
        
        Args:
            reg: The register to update
            mask: The bits to clear
        """
        tmp = self.PCD_ReadRegister(reg)
        self.PCD_WriteRegister(reg, tmp & (~mask))
    
    def PCD_CalculateCRC(self, data: List[int], length: int) -> Tuple[int, int]:
        """
        Calculates the CRC_A of the first length bytes in data.
        
        Args:
            data: Data to calculate CRC for
            length: Number of bytes to use
            
        Returns:
            Tuple of (CRC high byte, CRC low byte)
        """
        self.PCD_WriteRegister(PCD_Register.CommandReg, PCD_Command.PCD_IDLE)
        self.PCD_WriteRegister(PCD_Register.DivIrqReg, 0x04)
        self.PCD_WriteRegister(PCD_Register.FIFOLevelReg, 0x80)
        
        for i in range(length):
            self.PCD_WriteRegister(PCD_Register.FIFODataReg, data[i])
        
        self.PCD_WriteRegister(PCD_Register.CommandReg, PCD_Command.PCD_CALCCRC)
        
        # Wait for the CRC calculation to complete
        for i in range(0xFF):
            n = self.PCD_ReadRegister(PCD_Register.DivIrqReg)
            if n & 0x04:
                break
        
        crc_low = self.PCD_ReadRegister(PCD_Register.CRCResultRegL)
        crc_high = self.PCD_ReadRegister(PCD_Register.CRCResultRegM)
        
        return crc_high, crc_low
    
    def PCD_Init(self) -> None:
        """Initializes the MFRC522 chip"""
        if self._reset_power_down_pin != 0xFF:
            # Perform a hard reset
            GPIO.output(self._reset_power_down_pin, GPIO.LOW)
            time.sleep(0.1)
            GPIO.output(self._reset_power_down_pin, GPIO.HIGH)
            time.sleep(0.1)
        
        # Reset baud rates
        self.PCD_WriteRegister(PCD_Register.TxModeReg, 0x00)
        self.PCD_WriteRegister(PCD_Register.RxModeReg, 0x00)
        # Reset ModWidthReg
        self.PCD_WriteRegister(PCD_Register.ModWidthReg, 0x26)
        
        # When communicating with a PICC we need a timeout if something goes wrong.
        # f_timer = 13.56 MHz / (2*TPreScaler+1) where TPreScaler = [TPrescaler_Hi:TPrescaler_Lo].
        # TPreScaler of 0xA gives 13.56 MHz / (2*10+1) = 646.36 kHz.
        # TAutomatic of 0x86 gives TAuto=1000 * f_timer / 13.56 MHz = 1000 * 646.36 kHz / 13.56 MHz = 47.66 ms.
        # That means the timer will expire after 47.66 ms.
        self.PCD_WriteRegister(PCD_Register.TModeReg, 0x8D)
        self.PCD_WriteRegister(PCD_Register.TPrescalerReg, 0x3E)
        self.PCD_WriteRegister(PCD_Register.TReloadRegL, 30)
        self.PCD_WriteRegister(PCD_Register.TReloadRegH, 0)
        self.PCD_WriteRegister(PCD_Register.TxAutoReg, 0x40)
        self.PCD_WriteRegister(PCD_Register.ModeReg, 0x3D)
        
        # Turn antenna on
        self.PCD_AntennaOn()
    
    def PCD_Reset(self) -> None:
        """Performs a soft reset on the MFRC522"""
        self.PCD_WriteRegister(PCD_Register.CommandReg, PCD_Command.PCD_RESETPHASE)
    
    def PCD_AntennaOn(self) -> None:
        """Turns the antenna on by enabling pins TX1 and TX2"""
        temp = self.PCD_ReadRegister(PCD_Register.TxControlReg)
        if ~(temp & 0x03):
            self.PCD_WriteRegister(PCD_Register.TxControlReg, temp | 0x03)
    
    def PCD_AntennaOff(self) -> None:
        """Turns the antenna off by disabling pins TX1 and TX2"""
        temp = self.PCD_ReadRegister(PCD_Register.TxControlReg)
        self.PCD_WriteRegister(PCD_Register.TxControlReg, temp & (~0x03))
    
    def PCD_TransceiveData(self, send_data: List[int], send_len: int, 
                          back_data: List[int], back_len: List[int], 
                          valid_bits: Optional[int] = None, 
                          rx_align: int = 0, check_crc: bool = False) -> StatusCode:
        """
        Transfers data to the MFRC522 FIFO, executes a command, waits for completion and transfers data back from the FIFO.
        
        Args:
            send_data: Data to transfer to the FIFO
            send_len: Number of bytes to transfer to the FIFO
            back_data: Data from the FIFO
            back_len: Number of bytes returned from the FIFO (list with one element)
            valid_bits: In: Defines the number of bits of the last byte that are valid in send_data
            rx_align: In: Defines the bit position in back_data[0] for the first bit received
            check_crc: In: True => The last two bytes of the response is assumed to be a CRC_A that must be validated
            
        Returns:
            StatusCode indicating success or failure
        """
        wait_irq = 0x30
        self.PCD_WriteRegister(PCD_Register.ComIrqReg, 0x7F)
        self.PCD_SetRegisterBitMask(PCD_Register.FIFOLevelReg, 0x80)
        
        self.PCD_WriteRegister(PCD_Register.CommandReg, PCD_Command.PCD_IDLE)
        
        # Writing data to the FIFO
        for i in range(send_len):
            self.PCD_WriteRegister(PCD_Register.FIFODataReg, send_data[i])
        
        # Execute the command
        self.PCD_WriteRegister(PCD_Register.CommandReg, PCD_Command.PCD_TRANSCEIVE)
        self.PCD_SetRegisterBitMask(PCD_Register.BitFramingReg, 0x80)
        
        # Wait for the command to complete
        i = 2000
        while True:
            n = self.PCD_ReadRegister(PCD_Register.ComIrqReg)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break
        
        self.PCD_ClearRegisterBitMask(PCD_Register.BitFramingReg, 0x80)
        
        if i != 0:
            if (self.PCD_ReadRegister(PCD_Register.ErrorReg) & 0x1B) == 0x00:
                status = StatusCode.STATUS_OK
                if n & wait_irq & 0x01:
                    status = StatusCode.STATUS_NO_ROOM
                
                if status == StatusCode.STATUS_OK:
                    n = self.PCD_ReadRegister(PCD_Register.FIFOLevelReg)
                    last_bits = self.PCD_ReadRegister(PCD_Register.ControlReg) & 0x07
                    if last_bits != 0:
                        back_len[0] = (n - 1) * 8 + last_bits
                    else:
                        back_len[0] = n * 8
                    
                    if n == 0:
                        n = 1
                    if n > self.FIFO_SIZE:
                        n = self.FIFO_SIZE
                    
                    # Reading the received data from FIFO
                    for i in range(n):
                        back_data[i] = self.PCD_ReadRegister(PCD_Register.FIFODataReg)
            else:
                status = StatusCode.STATUS_ERROR
        else:
            status = StatusCode.STATUS_TIMEOUT
        
        return status
    
    def PICC_RequestA(self, buffer_atqa: List[int], buffer_size: List[int]) -> StatusCode:
        """
        Transmits REQA command.
        
        Args:
            buffer_atqa: The answer to the request, 2 bytes
            buffer_size: Buffer size, at least 2 bytes (list with one element)
            
        Returns:
            StatusCode indicating success or failure
        """
        buffer_size[0] = 2
        status = self.PICC_REQA_or_WUPA(PICC_Command.PICC_CMD_REQA, buffer_atqa, buffer_size)
        return status
    
    def PICC_REQA_or_WUPA(self, command: PICC_Command, buffer_atqa: List[int], 
                         buffer_size: List[int]) -> StatusCode:
        """
        Transmits REQA or WUPA command.
        
        Args:
            command: The command to send - PICC_CMD_REQA or PICC_CMD_WUPA
            buffer_atqa: The answer to the request, 2 bytes
            buffer_size: Buffer size, at least 2 bytes (list with one element)
            
        Returns:
            StatusCode indicating success or failure
        """
        buffer_size[0] = 2
        buffer_atqa[0] = command
        buffer_atqa[1] = 0x00
        
        status = self.PCD_TransceiveData(buffer_atqa, 1, buffer_atqa, buffer_size)
        return status
    
    def PICC_Select(self, uid: Uid, valid_bits: int = 0) -> StatusCode:
        """
        Selects a PICC.
        
        Args:
            uid: UID to select
            valid_bits: The number of known UID bits supplied in *uid
            
        Returns:
            StatusCode indicating success or failure
        """
        # Anti-collision
        select_data = [0x93, 0x70]
        select_data.extend(uid.uid_byte[:5])
        
        # Calculate CRC_A
        crc_high, crc_low = self.PCD_CalculateCRC(select_data, 7)
        select_data.append(crc_low)
        select_data.append(crc_high)
        
        back_data = [0] * 3
        back_len = [0]
        
        status = self.PCD_TransceiveData(select_data, 9, back_data, back_len)
        
        if status == StatusCode.STATUS_OK and back_len[0] == 0x18:
            uid.sak = back_data[0]
            # Copy the UID
            for i in range(4):
                uid.uid_byte[i] = back_data[i + 1]
            uid.size = 4
        else:
            status = StatusCode.STATUS_ERROR
        
        return status
    
    def PICC_HaltA(self) -> StatusCode:
        """
        Instructs a PICC in state ACTIVE(*) to go to state HALT.
        
        Returns:
            StatusCode indicating success or failure
        """
        halt_data = [PICC_Command.PICC_CMD_HLTA, 0]
        crc_high, crc_low = self.PCD_CalculateCRC(halt_data, 2)
        halt_data.append(crc_low)
        halt_data.append(crc_high)
        
        back_data = [0] * 1
        back_len = [0]
        
        status = self.PCD_TransceiveData(halt_data, 4, back_data, back_len)
        return status
    
    def PICC_IsNewCardPresent(self) -> bool:
        """
        Returns true if a PICC responds to PICC_CMD_REQA.
        
        Returns:
            True if a card is detected
        """
        buffer_atqa = [0, 0]
        buffer_size = [2]
        status = self.PICC_RequestA(buffer_atqa, buffer_size)
        return status == StatusCode.STATUS_OK and buffer_size[0] == 2 and buffer_atqa[0] == 0x04
    
    def PICC_ReadCardSerial(self) -> bool:
        """
        Reads the serial number of a PICC.
        
        Returns:
            True if a card was read
        """
        # Reset baud rates
        self.PCD_WriteRegister(PCD_Register.TxModeReg, 0x00)
        self.PCD_WriteRegister(PCD_Register.RxModeReg, 0x00)
        # Reset ModWidthReg
        self.PCD_WriteRegister(PCD_Register.ModWidthReg, 0x26)
        
        # Transmit the buffer and receive the response
        buffer_atqa = [0, 0]
        buffer_size = [2]
        status = self.PICC_RequestA(buffer_atqa, buffer_size)
        
        if status != StatusCode.STATUS_OK:
            return False
        
        # Anti-collision
        buffer_uid = [0] * 10
        buffer_size = [4]
        
        # First anti-collision
        select_data = [0x93, 0x20]
        crc_high, crc_low = self.PCD_CalculateCRC(select_data, 2)
        select_data.append(crc_low)
        select_data.append(crc_high)
        
        back_data = [0] * 5
        back_len = [0]
        
        status = self.PCD_TransceiveData(select_data, 4, back_data, back_len)
        
        if status != StatusCode.STATUS_OK or back_len[0] != 5:
            return False
        
        # Copy the UID
        for i in range(4):
            buffer_uid[i] = back_data[i]
        
        # Second anti-collision
        select_data = [0x93, 0x70]
        select_data.extend(buffer_uid[:4])
        crc_high, crc_low = self.PCD_CalculateCRC(select_data, 6)
        select_data.append(crc_low)
        select_data.append(crc_high)
        
        back_data = [0] * 1
        back_len = [0]
        
        status = self.PCD_TransceiveData(select_data, 8, back_data, back_len)
        
        if status != StatusCode.STATUS_OK or back_len[0] != 1:
            return False
        
        # Copy the UID to the object
        self.uid.size = 4
        for i in range(4):
            self.uid.uid_byte[i] = buffer_uid[i]
        self.uid.sak = back_data[0]
        
        return True
    
    def MIFARE_Read(self, block_addr: int, buffer: List[int], buffer_size: List[int]) -> StatusCode:
        """
        Reads a block from a MIFARE Classic PICC.
        
        Args:
            block_addr: The block (0-0xff) number
            buffer: Buffer to store the data in
            buffer_size: Buffer size, at least 18 bytes (list with one element)
            
        Returns:
            StatusCode indicating success or failure
        """
        buffer_size[0] = 18
        buffer[0] = PICC_Command.PICC_CMD_MF_READ
        buffer[1] = block_addr
        
        # Calculate CRC_A
        crc_high, crc_low = self.PCD_CalculateCRC(buffer, 2)
        buffer[2] = crc_low
        buffer[3] = crc_high
        
        back_data = [0] * 18
        back_len = [0]
        
        status = self.PCD_TransceiveData(buffer, 4, back_data, back_len)
        
        if status == StatusCode.STATUS_OK and back_len[0] == 16:
            for i in range(16):
                buffer[i] = back_data[i]
            buffer_size[0] = 16
        else:
            buffer_size[0] = 0
        
        return status
    
    def MIFARE_Write(self, block_addr: int, buffer: List[int], buffer_size: int) -> StatusCode:
        """
        Writes a block to a MIFARE Classic PICC.
        
        Args:
            block_addr: The block (0-0xff) number
            buffer: Buffer containing the data to write
            buffer_size: Buffer size, must be at least 16 bytes
            
        Returns:
            StatusCode indicating success or failure
        """
        buffer[0] = PICC_Command.PICC_CMD_MF_WRITE
        buffer[1] = block_addr
        
        # Calculate CRC_A
        crc_high, crc_low = self.PCD_CalculateCRC(buffer, 2)
        buffer[2] = crc_low
        buffer[3] = crc_high
        
        back_data = [0] * 1
        back_len = [0]
        
        status = self.PCD_TransceiveData(buffer, 4, back_data, back_len)
        
        if status != StatusCode.STATUS_OK:
            return status
        
        if back_len[0] != 1 or back_data[0] != 0x0A:
            status = StatusCode.STATUS_ERROR
        
        if status == StatusCode.STATUS_OK:
            # Data to write
            data_buffer = buffer[:16]
            crc_high, crc_low = self.PCD_CalculateCRC(data_buffer, 16)
            data_buffer.append(crc_low)
            data_buffer.append(crc_high)
            
            status = self.PCD_TransceiveData(data_buffer, 18, back_data, back_len)
            
            if status != StatusCode.STATUS_OK:
                return status
            
            if back_len[0] != 1 or back_data[0] != 0x0A:
                status = StatusCode.STATUS_ERROR
        
        return status
    
    @staticmethod
    def PICC_GetType(sak: int) -> PICC_Type:
        """
        Translates the SAK (Select Acknowledge) to a PICC type.
        
        Args:
            sak: The SAK byte returned from PICC_Select()
            
        Returns:
            PICC_Type
        """
        if sak & 0x04:
            return PICC_Type.PICC_TYPE_NOT_COMPLETE
        
        switch_code = sak & 0x20
        if switch_code == 0x00:
            return PICC_Type.PICC_TYPE_MIFARE_MINI
        elif switch_code == 0x20:
            return PICC_Type.PICC_TYPE_MIFARE_1K
        elif switch_code == 0x40:
            return PICC_Type.PICC_TYPE_MIFARE_4K
        elif switch_code == 0x60:
            return PICC_Type.PICC_TYPE_MIFARE_PLUS
        elif switch_code == 0x80:
            return PICC_Type.PICC_TYPE_MIFARE_DESFIRE
        elif switch_code == 0x10:
            return PICC_Type.PICC_TYPE_TNP3XXX
        elif switch_code == 0x01:
            return PICC_Type.PICC_TYPE_ISO_14443_4
        elif switch_code == 0x02:
            return PICC_Type.PICC_TYPE_ISO_18092
        elif switch_code == 0x03:
            return PICC_Type.PICC_TYPE_MIFARE_UL
        else:
            return PICC_Type.PICC_TYPE_UNKNOWN
    
    @staticmethod
    def PICC_GetTypeName(picc_type: PICC_Type) -> str:
        """
        Returns a __FlashStringHelper pointer to the PICC type name.
        
        Args:
            picc_type: One of the PICC_Type enums
            
        Returns:
            String representation of the PICC type
        """
        if picc_type == PICC_Type.PICC_TYPE_ISO_14443_4:
            return "PICC compliant with ISO/IEC 14443-4"
        elif picc_type == PICC_Type.PICC_TYPE_ISO_18092:
            return "PICC compliant with ISO/IEC 18092 (NFC)"
        elif picc_type == PICC_Type.PICC_TYPE_MIFARE_MINI:
            return "MIFARE Classic protocol, 320 bytes"
        elif picc_type == PICC_Type.PICC_TYPE_MIFARE_1K:
            return "MIFARE Classic protocol, 1KB"
        elif picc_type == PICC_Type.PICC_TYPE_MIFARE_4K:
            return "MIFARE Classic protocol, 4KB"
        elif picc_type == PICC_Type.PICC_TYPE_MIFARE_UL:
            return "MIFARE Ultralight or Ultralight C"
        elif picc_type == PICC_Type.PICC_TYPE_MIFARE_PLUS:
            return "MIFARE Plus"
        elif picc_type == PICC_Type.PICC_TYPE_MIFARE_DESFIRE:
            return "MIFARE DESFire"
        elif picc_type == PICC_Type.PICC_TYPE_TNP3XXX:
            return "Only mentioned in NXP AN 10833 MIFARE Type Identification Procedure"
        elif picc_type == PICC_Type.PICC_TYPE_NOT_COMPLETE:
            return "SAK indicates UID is not complete"
        else:
            return "Unknown type"
    
    @staticmethod
    def GetStatusCodeName(code: StatusCode) -> str:
        """
        Returns a __FlashStringHelper pointer to a status code name.
        
        Args:
            code: One of the StatusCode enums
            
        Returns:
            String representation of the status code
        """
        if code == StatusCode.STATUS_OK:
            return "Success"
        elif code == StatusCode.STATUS_ERROR:
            return "Error in communication"
        elif code == StatusCode.STATUS_COLLISION:
            return "Collision detected"
        elif code == StatusCode.STATUS_TIMEOUT:
            return "Timeout in communication"
        elif code == StatusCode.STATUS_NO_ROOM:
            return "A buffer is not big enough"
        elif code == StatusCode.STATUS_INTERNAL_ERROR:
            return "Internal error in the code"
        elif code == StatusCode.STATUS_INVALID:
            return "Invalid argument"
        elif code == StatusCode.STATUS_CRC_WRONG:
            return "The CRC_A does not match"
        elif code == StatusCode.STATUS_MIFARE_NACK:
            return "A MIFARE PICC responded with NAK"
        else:
            return "Unknown error" 