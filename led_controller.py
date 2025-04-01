#!/usr/bin/env python3
import argparse
import time
import signal
import sys
from pi5neo import Pi5Neo

# LED strip configuration
MAX_LEDS = 10
LED_BRIGHTNESS = 1.0  # Set to 0.0 for darkest and 1.0 for brightest

class LEDController:
    def __init__(self, led_count):
        if led_count > MAX_LEDS:
            raise ValueError(f"Number of LEDs cannot exceed {MAX_LEDS}")
        self.led_count = led_count
        # Initialize Pi5Neo with SPI interface (GPIO 10)
        self.neo = Pi5Neo('/dev/spidev0.0', led_count, 800)  # 800kHz SPI speed
        
    def set_color(self, led_index, r, g, b):
        """Set the color of a specific LED."""
        if 0 <= led_index < self.led_count:
            self.neo.set_led_color(led_index, r, g, b)
            self.neo.update_strip()
    
    def set_all(self, r, g, b):
        """Set all LEDs to the same color."""
        self.neo.fill_strip(r, g, b)
        self.neo.update_strip()
    
    def clear(self):
        """Turn off all LEDs."""
        self.neo.clear_strip()
        self.neo.update_strip()
    
    def cleanup(self):
        """Clean up resources."""
        self.clear()
        # Pi5Neo handles cleanup automatically

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print('Cleaning up...')
    controller.cleanup()
    sys.exit(0)

def main():
    global controller
    parser = argparse.ArgumentParser(description='Control WS2812 LEDs using Pi5Neo')
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