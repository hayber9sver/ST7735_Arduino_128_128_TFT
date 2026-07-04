#!/usr/bin/env python3
"""ST7735 128x128 SPI TFT demo for Orange Pi Zero 3.

Hardware: /dev/spidev1.1, wPi 3 = RESET, wPi 4 = DC
"""
import argparse
import time

from PIL import Image, ImageDraw, ImageFont

from st7735 import ST7735

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SMALL = ImageFont.truetype(FONT_PATH, 12)
FONT_LARGE = ImageFont.truetype(FONT_PATH, 16)


def demo_colors(lcd, seconds=3):
    named = [
        ("RED", (255, 0, 0)),
        ("GREEN", (0, 255, 0)),
        ("BLUE", (0, 0, 255)),
        ("WHITE", (255, 255, 255)),
        ("BLACK", (0, 0, 0)),
    ]
    for name, color in named:
        print(f">>> now showing: {name}")
        lcd.fill(color)
        time.sleep(seconds)


def demo_text(lcd, seconds=3):
    img = Image.new("RGB", (lcd.width, lcd.height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((4, 4), "Orange Pi", font=FONT_LARGE, fill=(255, 255, 0))
    draw.text((4, 24), "ST7735 TFT", font=FONT_SMALL, fill=(0, 255, 255))
    draw.text((4, 40), "128x128 SPI", font=FONT_SMALL, fill=(255, 255, 255))
    lcd.display(img)
    time.sleep(seconds)


def demo_shapes(lcd, seconds=3):
    img = Image.new("RGB", (lcd.width, lcd.height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((4, 4, 60, 40), outline=(255, 0, 0))
    draw.ellipse((66, 4, 122, 40), outline=(0, 255, 0))
    draw.line((4, 60, 122, 60), fill=(0, 128, 255), width=2)
    draw.polygon([(64, 70), (100, 120), (28, 120)], outline=(255, 0, 255))
    lcd.display(img)
    time.sleep(seconds)


def demo_bounce(lcd, duration=5):
    w, h = lcd.width, lcd.height
    x, y = 10, 10
    dx, dy = 4, 3
    size = 12
    end_time = time.time() + duration
    while time.time() < end_time:
        x += dx
        y += dy
        if x <= 0 or x + size >= w:
            dx = -dx
        if y <= 0 or y + size >= h:
            dy = -dy
        img = Image.new("RGB", (w, h), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((x, y, x + size, y + size), fill=(255, 128, 0))
        lcd.display(img)


def main():
    parser = argparse.ArgumentParser(description="ST7735 SPI TFT demo")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=["all", "colors", "text", "shapes", "bounce"],
        help="which demo to run (default: all)",
    )
    args = parser.parse_args()

    lcd = ST7735()
    try:
        if args.mode in ("all", "colors"):
            demo_colors(lcd)
        if args.mode in ("all", "text"):
            demo_text(lcd)
        if args.mode in ("all", "shapes"):
            demo_shapes(lcd)
        if args.mode in ("all", "bounce"):
            demo_bounce(lcd)
    except KeyboardInterrupt:
        pass
    finally:
        lcd.fill((0, 0, 0))


if __name__ == "__main__":
    main()
