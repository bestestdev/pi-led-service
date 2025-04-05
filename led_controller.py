#!/usr/bin/env python3
import argparse
import time
import signal
import sys
import os

MAX_LEDS = 10

def is_raspberry_pi_5():
    try:
        with open('/proc/device-tree/model', 'r') as f:
            return 'Raspberry Pi 5' in f.read()
    except:
        return False

def is_spi_enabled():
    # Check for any SPI devices
    return (os.path.exists('/dev/spidev0.0') or 
            os.path.exists('/dev/spidev1.0') or 
            os.path.exists('/dev/spidev10.0'))

def get_available_spi_bus():
    """Find an available SPI bus, prioritizing alternate SPI buses to avoid NVME/PCIe conflicts"""
    # Check for SPI10 (special case on some Pi configurations)
    if os.path.exists('/dev/spidev10.0'):
        return 10
    # Check for SPI1
    elif os.path.exists('/dev/spidev1.0'):
        return 1
    # Fall back to SPI0 if others not available
    elif os.path.exists('/dev/spidev0.0'):
        return 0
    return None

class LEDController:
    def __init__(self, led_count, spi_bus=None):
        if led_count > MAX_LEDS:
            raise ValueError(f"Number of LEDs cannot exceed {MAX_LEDS}")
        self.led_count = led_count
        self.platform = 'rpi5' if is_raspberry_pi_5() else 'rpi_other'
        print(f"Detected platform: {self.platform}")
        
        # Initialize SPI or PWM controller
        if self.platform == 'rpi5' and is_spi_enabled():
            try:
                # Import SPI libraries inside try block to handle import errors
                from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
                self.color_class = Color
                
                # On RPi5, we need to properly initialize SPI
                import spidev
                
                # Determine which SPI bus to use
                if spi_bus is None:
                    self.spi_bus = get_available_spi_bus()
                    if self.spi_bus is None:
                        raise ValueError("No SPI bus available")
                else:
                    self.spi_bus = spi_bus
                
                print(f"Using SPI bus {self.spi_bus} for LED control")
                
                # Close any existing SPI connections first to prevent resource conflicts
                try:
                    spi = spidev.SpiDev()
                    spi.open(self.spi_bus, 0)
                    spi.close()
                except Exception as e:
                    print(f"Note: Could not pre-close SPI bus {self.spi_bus}: {e}")
                    # If no existing connection, this is fine
                    pass
                
                # Now initialize our LED driver
                self.strip = WS2812SpiDriver(spi_bus=self.spi_bus, spi_device=0, led_count=self.led_count).get_strip()
                self.driver_type = 'rpi5-ws2812'
                self.led_states = [self.color_class(0, 0, 0)] * self.led_count
                print("Using rpi5-ws2812 driver")
            except ImportError:
                print("Error: rpi5-ws2812 library not found. Install with 'pip install rpi5-ws2812'")
                sys.exit(1)
            except Exception as e:
                print(f"Error initializing rpi5-ws2812: {e}")
                sys.exit(1)
        else:
            try:
                from rpi_ws281x import Color, PixelStrip, WS2811_STRIP_GRB
                self.color_class = Color
                LED_PIN = 18
                LED_FREQ_HZ = 800000
                LED_DMA = 10
                LED_BRIGHTNESS = 255
                LED_INVERT = False
                LED_CHANNEL = 0

                self.strip = PixelStrip(self.led_count, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, 
                                        LED_BRIGHTNESS, LED_CHANNEL, WS2811_STRIP_GRB)
                self.strip.begin()
                self.driver_type = 'rpi_ws281x'
                print("Using rpi_ws281x driver")
            except ImportError:
                print("Error: rpi_ws281x library not found. Install with 'pip install rpi_ws281x'")
                sys.exit(1)

    def set_color(self, led_index, r, g, b):
        if 0 <= led_index < self.led_count:
            try:
                if self.driver_type == 'rpi5-ws2812':
                    self.led_states[led_index] = self.color_class(r, g, b)
                    self.strip.set_pixels(self.led_states)
                else:
                    self.strip.setPixelColor(led_index, self.color_class(r, g, b))
                self.strip.show()
            except Exception as e:
                print(f"Error setting LED color: {e}")
                raise

    def set_all(self, r, g, b):
        try:
            if self.driver_type == 'rpi5-ws2812':
                self.led_states = [self.color_class(r, g, b)] * self.led_count
                self.strip.set_all_pixels(self.color_class(r, g, b))
            else:
                for i in range(self.led_count):
                    self.strip.setPixelColor(i, self.color_class(r, g, b))
            self.strip.show()
        except Exception as e:
            print(f"Error setting all LEDs: {e}")
            raise

    def set_pattern(self, rgb_values):
        if len(rgb_values) != self.led_count * 3:
            print(f"Error: Expected {self.led_count * 3} values for {self.led_count} LEDs, got {len(rgb_values)}.")
            sys.exit(1)

        try:
            for i in range(self.led_count):
                r, g, b = rgb_values[i * 3 : i * 3 + 3]
                if self.driver_type == 'rpi5-ws2812':
                    self.led_states[i] = self.color_class(r, g, b)
                else:
                    self.strip.setPixelColor(i, self.color_class(r, g, b))

            if self.driver_type == 'rpi5-ws2812':
                self.strip.set_pixels(self.led_states)
            self.strip.show()
        except Exception as e:
            print(f"Error setting pattern: {e}")
            raise

    def clear(self):
        self.set_all(0, 0, 0)

    def cleanup(self):
        try:
            self.clear()
            
            # Properly close the SPI connection if on RPi5
            if self.platform == 'rpi5' and hasattr(self, 'strip') and hasattr(self.strip, '_spi'):
                try:
                    self.strip._spi.close()
                    print("SPI connection closed")
                except:
                    pass
        except:
            # If cleanup fails, just pass since we're shutting down anyway
            pass

def signal_handler(sig, frame):
    print('Cleaning up...')
    controller.cleanup()
    sys.exit(0)

def main():
    global controller
    parser = argparse.ArgumentParser(description='Control WS2812 LEDs on Raspberry Pi')
    parser.add_argument('--leds', type=int, default=8, help=f'Number of LEDs to control (1-{MAX_LEDS})')
    parser.add_argument('--spi-bus', type=int, choices=[0, 1, 10], help='SPI bus to use (0, 1, or 10, default: auto-detect)')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    set_parser = subparsers.add_parser('set', help='Set color for a specific LED')
    set_parser.add_argument('led', type=int, help=f'LED index (0-{MAX_LEDS-1})')
    set_parser.add_argument('r', type=int, help='Red value (0-255)')
    set_parser.add_argument('g', type=int, help='Green value (0-255)')
    set_parser.add_argument('b', type=int, help='Blue value (0-255)')
    
    all_parser = subparsers.add_parser('all', help='Set all LEDs to the same color')
    all_parser.add_argument('r', type=int, help='Red value (0-255)')
    all_parser.add_argument('g', type=int, help='Green value (0-255)')
    all_parser.add_argument('b', type=int, help='Blue value (0-255)')

    pattern_parser = subparsers.add_parser('pattern', help='Set specific RGB values for each LED')
    pattern_parser.add_argument('values', type=int, nargs='+', help='List of RGB values: R G B R G B ...')

    subparsers.add_parser('clear', help='Turn off all LEDs')
    
    args = parser.parse_args()
    
    # Register signal handler for cleanup
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        controller = LEDController(args.leds, spi_bus=args.spi_bus)

        if args.command == 'set':
            controller.set_color(args.led, args.r, args.g, args.b)
        elif args.command == 'all':
            controller.set_all(args.r, args.g, args.b)
        elif args.command == 'pattern':
            controller.set_pattern(args.values)
        elif args.command == 'clear':
            controller.clear()
        else:
            parser.print_help()
            return
            
        # Add a small delay to ensure the command completes before exiting
        time.sleep(0.1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Make sure to always clean up
        if 'controller' in globals():
            controller.cleanup()

if __name__ == '__main__':
    main()
