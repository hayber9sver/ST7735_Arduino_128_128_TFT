"""Minimal ST7735 (128x128) SPI TFT driver.

Hardware wiring:
  RESET -> wPi 3   (wiringOP-Python GPIO)
  DC    -> wPi 4   (wiringOP-Python GPIO)
  SPI   -> /dev/spidev1.1 (hardware MOSI/SCLK/CS)

SPI transfers use the `spidev` package rather than wiringOP-Python's
wiringPiSPIDataRW: that call is full-duplex and writes the received MISO
bytes back into the same buffer it was given, which corrupts CPython's
cached single-byte `bytes` objects (e.g. repeated command opcodes like
CASET/RASET/RAMWR) after their first use, and segfaults if given a
bytearray instead (its SWIG typemap only understands `bytes`). spidev's
writebytes() has no such hazard.
"""
import time

import numpy as np
import spidev
import wiringpi

PIN_RESET = 3
PIN_DC = 4

SPI_BUS = 1     # -> /dev/spidev{SPI_BUS}.{SPI_DEVICE}
SPI_DEVICE = 1
SPI_SPEED = 4_000_000
SPI_MODE = 0

WIDTH = 128
HEIGHT = 128
# Common offset for 128x128 ST7735 modules. If the image is shifted or
# clipped on your panel, try COLSTART/ROWSTART = 0, or 2/1, or 0/32.
COLSTART = 2
ROWSTART = 3

_MAX_CHUNK = 4096  # spidev default buffer limit per ioctl transfer

# ST7735 command set
SWRESET = 0x01
SLPOUT = 0x11
INVOFF = 0x20
INVON = 0x21
DISPON = 0x29
CASET = 0x2A
RASET = 0x2B
RAMWR = 0x2C
MADCTL = 0x36
COLMOD = 0x3A
FRMCTR1 = 0xB1
FRMCTR2 = 0xB2
FRMCTR3 = 0xB3
INVCTR = 0xB4
PWCTR1 = 0xC0
PWCTR2 = 0xC1
PWCTR3 = 0xC2
PWCTR4 = 0xC3
PWCTR5 = 0xC4
VMCTR1 = 0xC5
GMCTRP1 = 0xE0
GMCTRN1 = 0xE1

MADCTL_MX = 0x40
MADCTL_MY = 0x80
MADCTL_MV = 0x20
MADCTL_RGB = 0x00
# This panel's color order is BGR, not RGB (confirmed by test_basic.py:
# filling with 0xF800 "red" showed up as blue). Swap via MADCTL bit 3.
MADCTL_BGR = 0x08


class ST7735:
    def __init__(self, width=WIDTH, height=HEIGHT,
                 colstart=COLSTART, rowstart=ROWSTART, rotation=0):
        self.width = width
        self.height = height
        self.colstart = colstart
        self.rowstart = rowstart

        wiringpi.wiringPiSetup()
        wiringpi.pinMode(PIN_RESET, wiringpi.OUTPUT)
        wiringpi.pinMode(PIN_DC, wiringpi.OUTPUT)

        self.spi = spidev.SpiDev()
        self.spi.open(SPI_BUS, SPI_DEVICE)
        self.spi.max_speed_hz = SPI_SPEED
        self.spi.mode = SPI_MODE

        self.reset()
        self._init_panel()
        self.set_rotation(rotation)

    # -- low level -----------------------------------------------------
    def reset(self):
        wiringpi.digitalWrite(PIN_RESET, wiringpi.HIGH)
        time.sleep(0.02)
        wiringpi.digitalWrite(PIN_RESET, wiringpi.LOW)
        time.sleep(0.02)
        wiringpi.digitalWrite(PIN_RESET, wiringpi.HIGH)
        time.sleep(0.15)

    def _spi_write(self, data):
        for i in range(0, len(data), _MAX_CHUNK):
            self.spi.writebytes(list(data[i:i + _MAX_CHUNK]))

    def write_cmd(self, cmd, *args):
        wiringpi.digitalWrite(PIN_DC, wiringpi.LOW)
        self._spi_write([cmd])
        if args:
            self.write_data(bytes(args))

    def write_data(self, data):
        wiringpi.digitalWrite(PIN_DC, wiringpi.HIGH)
        self._spi_write(data)

    # -- init ------------------------------------------------------------
    def _init_panel(self):
        self.write_cmd(SWRESET)
        time.sleep(0.15)
        self.write_cmd(SLPOUT)
        time.sleep(0.5)

        self.write_cmd(FRMCTR1, 0x01, 0x2C, 0x2D)
        self.write_cmd(FRMCTR2, 0x01, 0x2C, 0x2D)
        self.write_cmd(FRMCTR3, 0x01, 0x2C, 0x2D, 0x01, 0x2C, 0x2D)
        self.write_cmd(INVCTR, 0x07)
        self.write_cmd(PWCTR1, 0xA2, 0x02, 0x84)
        self.write_cmd(PWCTR2, 0xC5)
        self.write_cmd(PWCTR3, 0x0A, 0x00)
        self.write_cmd(PWCTR4, 0x8A, 0x2A)
        self.write_cmd(PWCTR5, 0x8A, 0xEE)
        self.write_cmd(VMCTR1, 0x0E)
        self.write_cmd(INVOFF)
        self.write_cmd(MADCTL, MADCTL_MX | MADCTL_MY | MADCTL_BGR)
        self.write_cmd(COLMOD, 0x05)  # 16-bit/pixel RGB565

        self.write_cmd(GMCTRP1, 0x02, 0x1C, 0x07, 0x12, 0x37, 0x32, 0x29, 0x2D,
                       0x29, 0x25, 0x2B, 0x39, 0x00, 0x01, 0x03, 0x10)
        self.write_cmd(GMCTRN1, 0x03, 0x1D, 0x07, 0x06, 0x2E, 0x2C, 0x29, 0x2D,
                       0x2E, 0x2E, 0x37, 0x3F, 0x00, 0x00, 0x02, 0x10)

        self.write_cmd(0x13)  # NORON
        time.sleep(0.01)
        self.write_cmd(DISPON)
        time.sleep(0.1)

    def set_rotation(self, rotation):
        modes = {
            0: MADCTL_MX | MADCTL_MY | MADCTL_BGR,
            90: MADCTL_MY | MADCTL_MV | MADCTL_BGR,
            180: MADCTL_BGR,
            270: MADCTL_MX | MADCTL_MV | MADCTL_BGR,
        }
        self.write_cmd(MADCTL, modes[rotation])

    # -- drawing ---------------------------------------------------------
    def set_window(self, x0, y0, x1, y1):
        self.write_cmd(CASET, 0x00, x0 + self.colstart, 0x00, x1 + self.colstart)
        self.write_cmd(RASET, 0x00, y0 + self.rowstart, 0x00, y1 + self.rowstart)
        self.write_cmd(RAMWR)

    def display(self, image):
        """Push a PIL RGB Image (must match self.width x self.height) to the panel."""
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        arr = np.asarray(image.convert("RGB"), dtype=np.uint16)
        r = (arr[:, :, 0] >> 3) << 11
        g = (arr[:, :, 1] >> 2) << 5
        b = arr[:, :, 2] >> 3
        rgb565 = (r | g | b).astype(">u2")

        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.write_data(rgb565.tobytes())

    def fill(self, color=(0, 0, 0)):
        from PIL import Image
        img = Image.new("RGB", (self.width, self.height), color)
        self.display(img)
