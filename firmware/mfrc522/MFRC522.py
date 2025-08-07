#!/usr/bin/env python
# -*- coding: utf8 -*-
#
#    Copyright 2014,2018 Mario Gomez <mario.gomez@teubi.co
#    Updated with NTAG support based on MicroPython implementation
#
#    This file is part of MFRC522-Python
#    MFRC522-Python is a simple Python implementation for
#    the MFRC522 NFC Card Reader for the Raspberry Pi.
#
#    MFRC522-Python is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    MFRC522-Python is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with MFRC522-Python.  If not, see <http://www.gnu.org/licenses/>.
#
import RPi.GPIO as GPIO
import spidev
import signal
import time
import logging

class MFRC522:
    DEBUG = False
    OK = 0
    NOTAGERR = 1
    ERR = 2

    NTAG_213 = 213
    NTAG_215 = 215
    NTAG_216 = 216
    NTAG_NONE = 0

    REQIDL = 0x26
    REQALL = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61
  
    PICC_ANTICOLL1 = 0x93
    PICC_ANTICOLL2 = 0x95
    PICC_ANTICOLL3 = 0x97

    def __init__(self, bus=0, device=0, spd=1000000, pin_mode=10, pin_rst=-1, debugLevel='WARNING'):
        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = spd

        self.logger = logging.getLogger('mfrc522Logger')
        self.logger.addHandler(logging.StreamHandler())
        level = logging.getLevelName(debugLevel)
        self.logger.setLevel(level)

        gpioMode = GPIO.getmode()
        
        if gpioMode is None:
            GPIO.setmode(pin_mode)
        else:
            pin_mode = gpioMode
            
        if pin_rst == -1:
            if pin_mode == 11:
                pin_rst = 15
            else:
                pin_rst = 22
            
        GPIO.setup(pin_rst, GPIO.OUT)
        GPIO.output(pin_rst, 1)
        
        self.NTAG = 0
        self.NTAG_MaxPage = 0
        
        self.init()

    def _wreg(self, reg, val):
        """Write a byte to the specified register"""
        self.spi.xfer2([(reg << 1) & 0x7E, val])

    def _rreg(self, reg):
        """Read a byte from the specified register"""
        val = self.spi.xfer2([((reg << 1) & 0x7E) | 0x80, 0])
        return val[1]

    def _sflags(self, reg, mask):
        """Set the bits given by mask in register reg"""
        self._wreg(reg, self._rreg(reg) | mask)

    def _cflags(self, reg, mask):
        """Clear the bits given by mask in register reg"""
        self._wreg(reg, self._rreg(reg) & (~mask))

    def _tocard(self, cmd, send):
        """Transfers a byte to the MFRC522 and returns the received byte"""
        recv = []
        bits = irq_en = wait_irq = n = 0
        stat = self.ERR

        if cmd == 0x0E:
            irq_en = 0x12
            wait_irq = 0x10
        elif cmd == 0x0C:
            irq_en = 0x77
            wait_irq = 0x30

        self._wreg(0x02, irq_en | 0x80)
        self._cflags(0x04, 0x80)
        self._sflags(0x0A, 0x80)
        self._wreg(0x01, 0x00)

        for c in send:
            self._wreg(0x09, c)
        self._wreg(0x01, cmd)

        if cmd == 0x0C:
            self._sflags(0x0D, 0x80)

        i = 2000
        while True:
            n = self._rreg(0x04)
            i -= 1
            if ~((i != 0) and ~(n & 0x01) and ~(n & wait_irq)):
                break

        self._cflags(0x0D, 0x80)

        if i:
            if (self._rreg(0x06) & 0x1B) == 0x00:
                stat = self.OK

                if n & irq_en & 0x01:
                    stat = self.NOTAGERR
                elif cmd == 0x0C:
                    n = self._rreg(0x0A)
                    lbits = self._rreg(0x0C) & 0x07
                    if lbits != 0:
                        bits = (n - 1) * 8 + lbits
                    else:
                        bits = n * 8

                    if n == 0:
                        n = 1
                    elif n > 16:
                        n = 16

                    for _ in range(n):
                        recv.append(self._rreg(0x09))
            else:
                stat = self.ERR

        return stat, recv, bits

    def _crc(self, data):
        """Calculate CRC"""
        self._cflags(0x05, 0x04)
        self._sflags(0x0A, 0x80)

        for c in data:
            self._wreg(0x09, c)

        self._wreg(0x01, 0x03)

        i = 0xFF
        while True:
            n = self._rreg(0x05)
            i -= 1
            if not ((i != 0) and not (n & 0x04)):
                break

        return [self._rreg(0x22), self._rreg(0x21)]

    def init(self):
        """Initialize the MFRC522"""
        self.reset()
        self._wreg(0x2A, 0x8D)
        self._wreg(0x2B, 0x3E)
        self._wreg(0x2D, 30)
        self._wreg(0x2C, 0)
        self._wreg(0x15, 0x40)
        self._wreg(0x11, 0x3D)
        self.antenna_on()

    def reset(self):
        """Reset the MFRC522"""
        self._wreg(0x01, 0x0F)

    def antenna_on(self, on=True):
        """Turn antenna on or off"""
        if on and ~(self._rreg(0x14) & 0x03):
            self._sflags(0x14, 0x03)
        else:
            self._cflags(0x14, 0x03)

    def request(self, mode):
        """Requests for tag"""
        self._wreg(0x0D, 0x07)
        (stat, recv, bits) = self._tocard(0x0C, [mode])

        if (stat != self.OK) | (bits != 0x10):
            stat = self.ERR

        return stat, bits
  
    def anticoll(self, anticolN):
        """Anticollision"""
        ser_chk = 0
        ser = [anticolN, 0x20]

        self._wreg(0x0D, 0x00)
        (stat, recv, bits) = self._tocard(0x0C, ser)

        if stat == self.OK:
            if len(recv) == 5:
                for i in range(4):
                    ser_chk = ser_chk ^ recv[i]
                if ser_chk != recv[4]:
                    stat = self.ERR
            else:
                stat = self.ERR

        return stat, recv

    def PcdSelect(self, serNum, anticolN):
        """Selects tag by number"""
        backData = []
        buf = []
        buf.append(anticolN)
        buf.append(0x70)
        
        for i in serNum:
            buf.append(i)
        
        pOut = self._crc(buf)
        buf.append(pOut[0])
        buf.append(pOut[1])
        (status, backData, backLen) = self._tocard(0x0C, buf)
        if (status == self.OK) and (backLen == 0x18):
            return 1
        else:
            return 0
    
    def SelectTag(self, uid):
        """Select tag by UID"""
        byte5 = 0
        
        for i in uid:
            byte5 = byte5 ^ i
        puid = uid + [byte5]
        
        if self.PcdSelect(puid, self.PICC_ANTICOLL1) == 0:
            return (self.ERR, [])
        return (self.OK, uid)
        
    def SelectTagSN(self):
        """Select tag by serial number"""
        valid_uid = []
        (status, uid) = self.anticoll(self.PICC_ANTICOLL1)
        if status != self.OK:
            return (self.ERR, [])
        
        if self.DEBUG:
            print("anticol(1) {}".format(uid))
        if self.PcdSelect(uid, self.PICC_ANTICOLL1) == 0:
            return (self.ERR, [])
        if self.DEBUG:
            print("pcdSelect(1) {}".format(uid))
        
        # Check if first byte is 0x88
        if uid[0] == 0x88:
            # OK we have another type of card
            valid_uid.extend(uid[1:4])
            (status, uid) = self.anticoll(self.PICC_ANTICOLL2)
            if status != self.OK:
                return (self.ERR, [])
            if self.DEBUG:
                print("Anticol(2) {}".format(uid))
            rtn = self.PcdSelect(uid, self.PICC_ANTICOLL2)
            if self.DEBUG:
                print("pcdSelect(2) return={} uid={}".format(rtn, uid))
            if rtn == 0:
                return (self.ERR, [])
            if self.DEBUG:
                print("PcdSelect2() {}".format(uid))
            # Now check again if uid[0] is 0x88
            if uid[0] == 0x88:
                valid_uid.extend(uid[1:4])
                (status, uid) = self.anticoll(self.PICC_ANTICOLL3)
                if status != self.OK:
                    return (self.ERR, [])
                if self.DEBUG:
                    print("Anticol(3) {}".format(uid))
                if self.PcdSelect(uid, self.PICC_ANTICOLL3) == 0:
                    return (self.ERR, [])
                if self.DEBUG:
                    print("PcdSelect(3) {}".format(uid))
        valid_uid.extend(uid[0:5])
        # If we are here than the uid is ok
        # Let's remove the last BYTE which is the XOR sum
        
        return (self.OK, valid_uid[:len(valid_uid)-1])

    def auth(self, mode, addr, sect, ser):
        """Authentication"""
        return self._tocard(0x0E, [mode, addr] + sect + ser[:4])[0]
    
    def authKeys(self, uid, addr, keyA=None, keyB=None):
        """Authentication with keys"""
        status = self.ERR
        if keyA is not None:
            status = self.auth(self.AUTHENT1A, addr, keyA, uid)
        elif keyB is not None:
            status = self.auth(self.AUTHENT1B, addr, keyB, uid)
        return status

    def stop_crypto1(self):
        """Stop crypto"""
        self._cflags(0x08, 0x08)

    def read(self, addr):
        """Read a block"""
        data = [0x30, addr]
        data += self._crc(data)
        (stat, recv, _) = self._tocard(0x0C, data)
        return stat, recv

    def readNTAGBlock(self, page):
        """Read a block from NTAG using NTAG-specific command"""
        if page > self.NTAG_MaxPage:
            return self.ERR, None
        if page < 0:
            return self.ERR, None
        
        # NTAG read command: 0x30
        data = [0x30, page]
        data += self._crc(data)
        (stat, recv, _) = self._tocard(0x0C, data)
        
        if stat == self.OK and len(recv) == 16:
            return self.OK, recv
        else:
            return self.ERR, None

    def write(self, addr, data):
        """Write a block"""
        buf = [0xA0, addr]
        buf += self._crc(buf)
        (stat, recv, bits) = self._tocard(0x0C, buf)

        if not (stat == self.OK) or not (bits == 4) or not ((recv[0] & 0x0F) == 0x0A):
            stat = self.ERR
        else:
            buf = []
            for i in range(16):
                buf.append(data[i])
            buf += self._crc(buf)
            (stat, recv, bits) = self._tocard(0x0C, buf)
            if not (stat == self.OK) or not (bits == 4) or not ((recv[0] & 0x0F) == 0x0A):
                stat = self.ERR
        return stat

    def writeNTAGPage(self, page, data):
        """Write a page to NTAG (4 bytes)"""
        if page > self.NTAG_MaxPage:
            return self.ERR
        if page < 4:
            return self.ERR
        if len(data) != 4:
            return self.ERR
        
        return self.write(page, data + [0] * 12)
    
    def writeNTAGBlock(self, page, data):
        """Write a block to NTAG (16 bytes) using NTAG-specific command"""
        if page > self.NTAG_MaxPage:
            return self.ERR
        if page < 4:
            return self.ERR
        if len(data) != 16:
            return self.ERR
        
        # NTAG write command: 0xA2
        buf = [0xA2, page]
        
        # Add the data (16 bytes)
        for i in range(16):
            buf.append(data[i])
        
        # Send the command
        (stat, recv, bits) = self._tocard(0x0C, buf)
        
        if stat == self.OK:
            # NTAG cards typically return 4 bytes with ACK (0x0A) in the first byte
            if len(recv) > 0 and recv[0] == 0x0A:
                return self.OK
            elif len(recv) == 0:
                # Some NTAG cards might not return data but still succeed
                return self.OK
            else:
                return self.ERR
        else:
            return self.ERR
        
    def getNTAGVersion(self):
        """Get NTAG version"""
        buf = [0x60]
        buf += self._crc(buf)
        stat, recv, _ = self._tocard(0x0C, buf)
        return stat, recv
        
    def IsNTAG(self):
        """Check if card is NTAG"""
        self.NTAG = self.NTAG_NONE
        self.NTAG_MaxPage = 0
        (stat, rcv) = self.getNTAGVersion()
        if stat == self.OK:
            if len(rcv) < 8:
                return False  # Do we have at least 8 bytes
            if rcv[0] != 0:
                return False  # Check header
            if rcv[1] != 4:
                return False  # Check Vendor ID
            if rcv[2] != 4:
                return False  # Check product type
            if rcv[3] != 2:
                return False  # Check subtype
            if rcv[7] != 3:
                return False  # Check protocol
            if rcv[6] == 0xf:
                self.NTAG = self.NTAG_213  
                self.NTAG_MaxPage = 44                  
                return True
            if rcv[6] == 0x11:
                self.NTAG = self.NTAG_215
                self.NTAG_MaxPage = 134                  
                return True
            if rcv[6] == 0x13:
                self.NTAG = self.NTAG_216
                self.NTAG_MaxPage = 230                  
                return True
        return False

    # Legacy methods for compatibility
    def MFRC522_Request(self, reqMode):
        return self.request(reqMode)

    def MFRC522_Anticoll(self):
        return self.anticoll(self.PICC_ANTICOLL1)

    def MFRC522_SelectTag(self, serNum):
        return self.SelectTag(serNum)

    def MFRC522_Auth(self, authMode, BlockAddr, Sectorkey, serNum):
        return self.auth(authMode, BlockAddr, Sectorkey, serNum)

    def MFRC522_StopCrypto1(self):
        return self.stop_crypto1()

    def MFRC522_Read(self, blockAddr):
        stat, recv = self.read(blockAddr)
        if stat == self.OK:
            return recv
        else:
            return None

    def MFRC522_Write(self, blockAddr, writeData):
        return self.write(blockAddr, writeData)

    def MFRC522_Init(self):
        return self.init()

    def MFRC522_Reset(self):
        return self.reset()

    def AntennaOn(self):
        return self.antenna_on(True)

    def AntennaOff(self):
        return self.antenna_on(False)

    def Close_MFRC522(self):
        self.spi.close()
        GPIO.cleanup()

    # Constants for compatibility
    MI_OK = OK
    MI_NOTAGERR = NOTAGERR
    MI_ERR = ERR
    PICC_REQIDL = REQIDL
    PICC_REQALL = REQALL
    PICC_ANTICOLL = PICC_ANTICOLL1
    PICC_SElECTTAG = PICC_ANTICOLL1
    PICC_AUTHENT1A = AUTHENT1A
    PICC_AUTHENT1B = AUTHENT1B
    PICC_READ = 0x30
    PICC_WRITE = 0xA0
    PICC_DECREMENT = 0xC0
    PICC_INCREMENT = 0xC1
    PICC_RESTORE = 0xC2
    PICC_TRANSFER = 0xB0
    PICC_HALT = 0x50
