#!/usr/bin/env python3
import argparse
import time
import signal
import sys
from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver

# LED strip configuration
MAX_LEDS = 10

class LEDController:
    def __init__(self, led_count):
        if led_count > MAX_LEDS:
            raise ValueError(f"Number of LEDs cannot exceed {MAX_LEDS}")
        self.led_count = led_count
        # Initialize WS2812SpiDriver with SPI channel 0, CE0
        self.strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=led_count).get_strip()
        
    def set_color(self, led_index, r, g, b):
        """Set the color of a specific LED."""
        if 0 <= led_index < self.led_count:
            # Create a list of colors with the target color at the specified index
            colors = [Color(0, 0, 0)] * self.led_count
            colors[led_index] = Color(r, g, b)
            self.strip.set_pixels(colors)
            self.strip.show()
    
    def set_all(self, r, g, b):
        """Set all LEDs to the same color."""
        self.strip.set_all_pixels(Color(r, g, b))
        self.strip.show()
    
    def clear(self):
        """Turn off all LEDs."""
        self.strip.set_all_pixels(Color(0, 0, 0))
        self.strip.show()
    
    def cleanup(self):
        """Clean up resources."""
        self.clear()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print('Cleaning up...')
    controller.cleanup()
    sys.exit(0)

def main():
    global controller
    parser = argparse.ArgumentParser(description='Control WS2812 LEDs using rpi5-ws2812')
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