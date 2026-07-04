#!/usr/bin/env python3
"""Minimal ST7735 bring-up test: reset + bare-minimum init + solid red fill.

Skips power/gamma tuning commands to isolate whether basic SPI comms
and RAM addressing work at all. Run this if the full driver misbehaves.
"""
import sys
import time

import wiringpi

PIN_RESET = 3
PIN_DC = 4
SPI_CHANNEL = 1
SPI_PORT = 1
SPI_SPEED = 1_000_000  # deliberately slow for this test
SPI_MODE = 0

WIDTH = 128
HEIGHT = 128
COLSTART = 2
ROWSTART = 3


def write_cmd(cmd, *args):
    wiringpi.digitalWrite(PIN_DC, wiringpi.LOW)
    ret, _ = wiringpi.wiringPiSPIDataRW(SPI_CHANNEL, bytes([cmd]))
    print(f"  cmd 0x{cmd:02X} -> ret={ret}")
    if ret < 0:
        sys.exit(f"SPI command write failed for 0x{cmd:02X}")
    if args:
        wiringpi.digitalWrite(PIN_DC, wiringpi.HIGH)
        ret, _ = wiringpi.wiringPiSPIDataRW(SPI_CHANNEL, bytes(args))
        print(f"    data {[hex(a) for a in args]} -> ret={ret}")
        if ret < 0:
            sys.exit(f"SPI data write failed for cmd 0x{cmd:02X}")


def write_pixels(data):
    wiringpi.digitalWrite(PIN_DC, wiringpi.HIGH)
    CHUNK = 2048
    for i in range(0, len(data), CHUNK):
        ret, _ = wiringpi.wiringPiSPIDataRW(SPI_CHANNEL, bytes(data[i:i + CHUNK]))
        if ret < 0:
            sys.exit(f"SPI pixel write failed at offset {i} (ret={ret})")


print("1. wiringPiSetup")
wiringpi.wiringPiSetup()
wiringpi.pinMode(PIN_RESET, wiringpi.OUTPUT)
wiringpi.pinMode(PIN_DC, wiringpi.OUTPUT)

print("2. wiringPiSPISetupMode")
fd = wiringpi.wiringPiSPISetupMode(SPI_CHANNEL, SPI_PORT, SPI_SPEED, SPI_MODE)
print(f"   spi fd = {fd}")
if fd < 0:
    sys.exit("Failed to open SPI device")

print("3. hardware reset")
wiringpi.digitalWrite(PIN_RESET, wiringpi.HIGH)
time.sleep(0.05)
wiringpi.digitalWrite(PIN_RESET, wiringpi.LOW)
time.sleep(0.05)
wiringpi.digitalWrite(PIN_RESET, wiringpi.HIGH)
time.sleep(0.2)

print("4. minimal init sequence")
write_cmd(0x01)          # SWRESET
time.sleep(0.15)
write_cmd(0x11)          # SLPOUT
time.sleep(0.5)
write_cmd(0x3A, 0x05)    # COLMOD: 16-bit/pixel
write_cmd(0x36, 0xC0)    # MADCTL: MX|MY, RGB order
write_cmd(0x29)          # DISPON
time.sleep(0.1)

print("5. set full-screen window and fill RED")
x0, y0, x1, y1 = 0, 0, WIDTH - 1, HEIGHT - 1
write_cmd(0x2A, 0x00, x0 + COLSTART, 0x00, x1 + COLSTART)  # CASET
write_cmd(0x2B, 0x00, y0 + ROWSTART, 0x00, y1 + ROWSTART)  # RASET
write_cmd(0x2C)                                            # RAMWR

RED565 = (0xF8, 0x00)  # RGB565 red, big-endian
pixel_data = bytes(RED565) * (WIDTH * HEIGHT)
print(f"   writing {len(pixel_data)} bytes of pixel data...")
write_pixels(pixel_data)

print("Done. Screen should now be solid RED. Ctrl+C to exit (won't clear screen).")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
