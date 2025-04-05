#!/usr/bin/env python3
import argparse
import time
import signal
import sys
import os
import subprocess
import importlib.util

# LED strip configuration
MAX_LEDS = 10

def is_raspberry_pi_5():
    """Check if the current device is a Raspberry Pi 5"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi 5' in model
    except:
        return False

def is_spi_enabled():
    """Check if SPI interface is enabled"""
    return os.path.exists('/dev/spidev0.0')

class LEDController:
    def __init__(self, led_count):
        if led_count > MAX_LEDS:
            raise ValueError(f"Number of LEDs cannot exceed {MAX_LEDS}")
        self.led_count = led_count
        
        # Detect platform and initialize the appropriate library
        self.platform = 'rpi5' if is_raspberry_pi_5() else 'rpi_other'
        print(f"Detected platform: {self.platform}")
        
        if self.platform == 'rpi5' and is_spi_enabled():
            # Use rpi5-ws2812 for Raspberry Pi 5
            try:
                from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
                self.strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=led_count).get_strip()
                self.color_class = Color
                self.driver_type = 'rpi5-ws2812'
                print("Using rpi5-ws2812 driver")
            except ImportError:
                print("Error: rpi5-ws2812 library not found. Please install it with 'pip install rpi5-ws2812'")
                sys.exit(1)
        else:
            # Use rpi_ws281x for other Raspberry Pi models
            try:
                from rpi_ws281x import Color, PixelStrip, WS2811_STRIP_GRB
                # Using GPIO 18 (PWM0) as the default pin for rpi_ws281x
                LED_PIN = 18
                LED_FREQ_HZ = 800000  # LED signal frequency in Hz
                LED_DMA = 10          # DMA channel for generating signal
                LED_BRIGHTNESS = 255  # 0-255
                LED_INVERT = False    # Invert signal if needed
                LED_CHANNEL = 0       # PWM channel
                
                self.strip = PixelStrip(led_count, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, 
                                       LED_BRIGHTNESS, LED_CHANNEL, WS2811_STRIP_GRB)
                self.strip.begin()
                self.color_class = Color
                self.driver_type = 'rpi_ws281x'
                print("Using rpi_ws281x driver")
            except ImportError:
                print("Error: rpi_ws281x library not found. Please install it with 'pip install rpi_ws281x'")
                sys.exit(1)
        
    def set_color(self, led_index, r, g, b):
        """Set the color of a specific LED."""
        if 0 <= led_index < self.led_count:
            if self.driver_type == 'rpi5-ws2812':
                # For rpi5-ws2812
                colors = [self.color_class(0, 0, 0)] * self.led_count
                colors[led_index] = self.color_class(r, g, b)
                self.strip.set_pixels(colors)
                self.strip.show()
            else:
                # For rpi_ws281x
                self.strip.setPixelColor(led_index, self.color_class(r, g, b))
                self.strip.show()
    
    def set_all(self, r, g, b):
        """Set all LEDs to the same color."""
        if self.driver_type == 'rpi5-ws2812':
            # For rpi5-ws2812
            self.strip.set_all_pixels(self.color_class(r, g, b))
            self.strip.show()
        else:
            # For rpi_ws281x
            for i in range(self.led_count):
                self.strip.setPixelColor(i, self.color_class(r, g, b))
            self.strip.show()
    
    def clear(self):
        """Turn off all LEDs."""
        self.set_all(0, 0, 0)
    
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
    parser = argparse.ArgumentParser(description='Control WS2812 LEDs on Raspberry Pi')
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