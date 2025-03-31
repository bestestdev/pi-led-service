#!/usr/bin/env python3
import argparse
import time
from rpi_ws281x import PixelStrip, Color
import signal
import sys

# LED strip configuration
LED_COUNT = 8
LED_PINS = [17, 27, 22, 23, 24, 25, 8, 7]  # GPIO pins for each LED
LED_FREQ_HZ = 800000  # LED signal frequency in Hz
LED_DMA = 10          # DMA channel to use for generating signal
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal
LED_CHANNEL = 0       # Set to 1 for GPIOs 13, 19, 41, 45 or 53

class LEDController:
    def __init__(self):
        self.strips = []
        for pin in LED_PINS:
            strip = PixelStrip(LED_COUNT, pin, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
            strip.begin()
            self.strips.append(strip)
        
    def set_color(self, led_index, r, g, b):
        """Set the color of a specific LED."""
        if 0 <= led_index < LED_COUNT:
            color = Color(r, g, b)
            for strip in self.strips:
                strip.setPixelColor(led_index, color)
                strip.show()
    
    def set_all(self, r, g, b):
        """Set all LEDs to the same color."""
        color = Color(r, g, b)
        for strip in self.strips:
            for i in range(LED_COUNT):
                strip.setPixelColor(i, color)
            strip.show()
    
    def clear(self):
        """Turn off all LEDs."""
        self.set_all(0, 0, 0)
    
    def cleanup(self):
        """Clean up resources."""
        self.clear()
        for strip in self.strips:
            strip._cleanup()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print('Cleaning up...')
    controller.cleanup()
    sys.exit(0)

def main():
    global controller
    controller = LEDController()
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description='Control WS2812 LEDs')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Set single LED color
    set_parser = subparsers.add_parser('set', help='Set color for a specific LED')
    set_parser.add_argument('led', type=int, help='LED index (0-7)')
    set_parser.add_argument('r', type=int, help='Red value (0-255)')
    set_parser.add_argument('g', type=int, help='Green value (0-255)')
    set_parser.add_argument('b', type=int, help='Blue value (0-255)')
    
    # Set all LEDs
    all_parser = subparsers.add_parser('all', help='Set all LEDs to the same color')
    all_parser.add_argument('r', type=int, help='Red value (0-255)')
    all_parser.add_argument('g', type=int, help='Green value (0-255)')
    all_parser.add_argument('b', type=int, help='Blue value (0-255)')
    
    # Clear all LEDs
    subparsers.add_parser('clear', help='Turn off all LEDs')
    
    args = parser.parse_args()
    
    if args.command == 'set':
        controller.set_color(args.led, args.r, args.g, args.b)
    elif args.command == 'all':
        controller.set_all(args.r, args.g, args.b)
    elif args.command == 'clear':
        controller.clear()
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 