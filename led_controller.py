#!/usr/bin/env python3
import argparse
import time
from rpi_ws281x import PixelStrip, Color
import signal
import sys

# LED strip configuration
MAX_LEDS = 10
# GPIO to Physical Pin mapping:
# GPIO 17 = Pin 11
# GPIO 27 = Pin 13
# GPIO 22 = Pin 15
# GPIO 23 = Pin 16
# GPIO 24 = Pin 18
# GPIO 25 = Pin 22
# GPIO 8  = Pin 24
# GPIO 7  = Pin 26
# GPIO 5  = Pin 29
# GPIO 6  = Pin 31
LED_PINS = [17, 27, 22, 23, 24, 25, 8, 7, 5, 6]  # GPIO pins for each LED (ordered)
LED_FREQ_HZ = 800000  # LED signal frequency in Hz
LED_DMA = 10          # DMA channel to use for generating signal
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal
LED_CHANNEL = 0       # Set to 1 for GPIOs 13, 19, 41, 45 or 53

class LEDController:
    def __init__(self, led_count):
        if led_count > MAX_LEDS:
            raise ValueError(f"Number of LEDs cannot exceed {MAX_LEDS}")
        self.led_count = led_count
        self.strips = []
        for pin in LED_PINS[:led_count]:
            strip = PixelStrip(1, pin, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
            strip.begin()
            self.strips.append(strip)
        
    def set_color(self, led_index, r, g, b):
        """Set the color of a specific LED."""
        if 0 <= led_index < self.led_count:
            color = Color(r, g, b)
            self.strips[led_index].setPixelColor(0, color)
            self.strips[led_index].show()
    
    def set_all(self, r, g, b):
        """Set all LEDs to the same color."""
        color = Color(r, g, b)
        for strip in self.strips:
            strip.setPixelColor(0, color)
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
    parser = argparse.ArgumentParser(description='Control WS2812 LEDs')
    parser.add_argument('--leds', type=int, default=8, help=f'Number of LEDs to control (1-{MAX_LEDS})')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Set single LED color
    set_parser = subparsers.add_parser('set', help='Set color for a specific LED')
    set_parser.add_argument('led', type=int, help=f'LED index (0-{MAX_LEDS-1})')
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
    
    try:
        controller = LEDController(args.leds)
        signal.signal(signal.SIGINT, signal_handler)
        
        if args.command == 'set':
            controller.set_color(args.led, args.r, args.g, args.b)
        elif args.command == 'all':
            controller.set_all(args.r, args.g, args.b)
        elif args.command == 'clear':
            controller.clear()
        else:
            parser.print_help()
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 