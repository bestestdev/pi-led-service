#!/usr/bin/env python3
"""Controls the LEDs via Wyoming events, supporting both ReSpeaker HAT and RPI5 SPI."""
import argparse
import asyncio
import logging
import signal
import sys
import time
import os
from functools import partial
from typing import Tuple, List, Optional

try:
    import gpiozero
except ImportError:
    gpiozero = None

from wyoming.asr import Transcript
from wyoming.event import Event
from wyoming.satellite import (
    RunSatellite,
    SatelliteConnected,
    SatelliteDisconnected,
    StreamingStarted,
    StreamingStopped,
)
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.vad import VoiceStarted
from wyoming.wake import Detection

_LOGGER = logging.getLogger()

# Default settings
MAX_LEDS = 10
DEFAULT_LEDS = 3

# Colors
_BLACK = (0, 0, 0)
_WHITE = (255, 255, 255)
_RED = (255, 0, 0)
_YELLOW = (255, 255, 0)
_BLUE = (0, 0, 255)
_GREEN = (0, 255, 0)

def is_raspberry_pi_5():
    """Check if we're running on a Raspberry Pi 5."""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            return 'Raspberry Pi 5' in f.read()
    except:
        return False

def is_spi_enabled():
    """Check if SPI is enabled."""
    return os.path.exists('/dev/spidev0.0')

class LEDController:
    """Base class for LED controllers."""
    
    def __init__(self, num_leds: int):
        self.num_leds = num_leds
        
    def set_color(self, led_index: int, r: int, g: int, b: int):
        """Set a specific LED to a color."""
        raise NotImplementedError()
        
    def set_all(self, r: int, g: int, b: int):
        """Set all LEDs to the same color."""
        for i in range(self.num_leds):
            self.set_color(i, r, g, b)
            
    def clear(self):
        """Turn off all LEDs."""
        self.set_all(0, 0, 0)
        
    def cleanup(self):
        """Clean up resources."""
        self.clear()

class RPI5LEDController(LEDController):
    """LED Controller for Raspberry Pi 5 using SPI."""
    
    def __init__(self, num_leds: int):
        super().__init__(num_leds)
        try:
            from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
            self.color_class = Color
            self.strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=num_leds).get_strip()
            self.led_states = [self.color_class(0, 0, 0)] * self.num_leds
            _LOGGER.info("Using RPI5-WS2812 driver")
        except ImportError:
            _LOGGER.error("rpi5-ws2812 library not found. Install with 'pip install rpi5-ws2812'")
            sys.exit(1)
            
    def set_color(self, led_index: int, r: int, g: int, b: int):
        if 0 <= led_index < self.num_leds:
            self.led_states[led_index] = self.color_class(r, g, b)
            self.strip.set_pixels(self.led_states)
            self.strip.show()
            
    def set_all(self, r: int, g: int, b: int):
        self.led_states = [self.color_class(r, g, b)] * self.num_leds
        self.strip.set_all_pixels(self.color_class(r, g, b))
        self.strip.show()

class RPI281xLEDController(LEDController):
    """LED Controller for other Raspberry Pi models using the rpi_ws281x library."""
    
    def __init__(self, num_leds: int, led_pin: int = 18):
        super().__init__(num_leds)
        try:
            from rpi_ws281x import Color, PixelStrip, WS2811_STRIP_GRB
            self.color_class = Color
            LED_PIN = led_pin
            LED_FREQ_HZ = 800000
            LED_DMA = 10
            LED_BRIGHTNESS = 255
            LED_INVERT = False
            LED_CHANNEL = 0

            self.strip = PixelStrip(num_leds, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, 
                                  LED_BRIGHTNESS, LED_CHANNEL, WS2811_STRIP_GRB)
            self.strip.begin()
            _LOGGER.info("Using RPI_WS281x driver")
        except ImportError:
            _LOGGER.error("rpi_ws281x library not found. Install with 'pip install rpi_ws281x'")
            sys.exit(1)
            
    def set_color(self, led_index: int, r: int, g: int, b: int):
        if 0 <= led_index < self.num_leds:
            self.strip.setPixelColor(led_index, self.color_class(r, g, b))
            self.strip.show()

class RespeakerLEDController(LEDController):
    """LED Controller for ReSpeaker 2mic HAT using APA102."""
    
    # RGB mappings
    RGB_MAP = {
        "rgb": [3, 2, 1],
        "rbg": [3, 1, 2],
        "grb": [2, 3, 1],
        "gbr": [2, 1, 3],
        "brg": [1, 3, 2],
        "bgr": [1, 2, 3],
    }
    
    # APA102 constants
    MAX_BRIGHTNESS = 0b11111
    LED_START = 0b11100000
    
    def __init__(self, num_leds: int, gpio_pin: int = 12, brightness: int = 31, 
                 order: str = "rgb", bus: int = 0, device: int = 1, max_speed_hz: int = 8000000):
        super().__init__(num_leds)
        
        # Set up GPIO for LED power
        if gpiozero:
            self.led_power = gpiozero.LED(gpio_pin, active_high=False)
            self.led_power.on()
        else:
            _LOGGER.warning("gpiozero not available, LED power control disabled")
            self.led_power = None
            
        # Set up RGB order
        order = order.lower()
        self.rgb = self.RGB_MAP.get(order, self.RGB_MAP["rgb"])
        
        # Set brightness
        if brightness > self.MAX_BRIGHTNESS:
            self.brightness = self.MAX_BRIGHTNESS
        else:
            self.brightness = brightness
            
        _LOGGER.debug("LED brightness: %d", self.brightness)
        
        # Initialize pixel buffer
        self.leds = [self.LED_START, 0, 0, 0] * self.num_leds
        
        try:
            import spidev
            self.spi = spidev.SpiDev()
            self.spi.open(bus, device)
            if max_speed_hz:
                self.spi.max_speed_hz = max_speed_hz
            _LOGGER.info("Using APA102 driver for ReSpeaker HAT")
        except ImportError:
            _LOGGER.error("spidev library not found. Install with 'pip install spidev'")
            sys.exit(1)
            
    def set_color(self, led_num: int, r: int, g: int, b: int, bright_percent: int = 100):
        """Set a single LED to a specific color."""
        if led_num < 0 or led_num >= self.num_leds:
            return
            
        # Calculate brightness
        brightness = int((bright_percent * self.brightness / 100.0) + 0.5)
        
        # LED startframe is three "1" bits, followed by 5 brightness bits
        ledstart = (brightness & 0b00011111) | self.LED_START
        
        start_index = 4 * led_num
        self.leds[start_index] = ledstart
        self.leds[start_index + self.rgb[0]] = r
        self.leds[start_index + self.rgb[1]] = g
        self.leds[start_index + self.rgb[2]] = b
            
    def show(self):
        """Send the LED data to the strip."""
        self._clock_start_frame()
        data = list(self.leds)
        while data:
            self.spi.xfer2(data[:32])
            data = data[32:]
        self._clock_end_frame()
        
    def _clock_start_frame(self):
        """Send start frame to the LED strip."""
        self.spi.xfer2([0] * 4)
        
    def _clock_end_frame(self):
        """Send end frame to the LED strip."""
        self.spi.xfer2([0xFF] * 4)
        
    def set_all(self, r: int, g: int, b: int):
        """Set all LEDs to the same color."""
        for i in range(self.num_leds):
            self.set_color(i, r, g, b)
        self.show()
        
    def cleanup(self):
        """Clean up resources."""
        self.clear()
        if self.led_power:
            self.led_power.off()
        self.spi.close()

def create_led_controller(num_leds: int, gpio_pin: int = 12, brightness: int = 31,
                         respeaker_mode: bool = False, led_pin: int = 18) -> LEDController:
    """Factory method to create the appropriate LED controller."""
    
    if respeaker_mode:
        _LOGGER.info("Using ReSpeaker HAT LED controller")
        return RespeakerLEDController(num_leds, gpio_pin, brightness)
    
    if is_raspberry_pi_5() and is_spi_enabled():
        _LOGGER.info("Detected Raspberry Pi 5 with SPI enabled")
        return RPI5LEDController(num_leds)
    
    _LOGGER.info("Using standard WS281x LED controller")
    return RPI281xLEDController(num_leds, led_pin)

class LEDEventHandler(AsyncEventHandler):
    """Wyoming event handler for controlling LEDs."""

    def __init__(
        self,
        led_controller: LEDController,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        
        self.client_id = str(time.monotonic_ns())
        self.controller = led_controller
        
        _LOGGER.debug("Client connected: %s", self.client_id)

    async def handle_event(self, event: Event) -> bool:
        _LOGGER.debug(event)

        if StreamingStarted.is_type(event.type):
            self.color(_YELLOW)
        elif Detection.is_type(event.type):
            self.color(_BLUE)
            await asyncio.sleep(1.0)  # show for 1 sec
        elif VoiceStarted.is_type(event.type):
            self.color(_YELLOW)
        elif Transcript.is_type(event.type):
            self.color(_GREEN)
            await asyncio.sleep(1.0)  # show for 1 sec
        elif StreamingStopped.is_type(event.type):
            self.color(_BLACK)
        elif RunSatellite.is_type(event.type):
            self.color(_BLACK)
        elif SatelliteConnected.is_type(event.type):
            # Flash
            for _ in range(3):
                self.color(_GREEN)
                await asyncio.sleep(0.3)
                self.color(_BLACK)
                await asyncio.sleep(0.3)
        elif SatelliteDisconnected.is_type(event.type):
            self.color(_RED)

        return True

    def color(self, rgb: Tuple[int, int, int]) -> None:
        """Set all LEDs to the same color."""
        self.controller.set_all(rgb[0], rgb[1], rgb[2])

async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Wyoming LED service for Raspberry Pi")
    parser.add_argument("--uri", required=True, help="unix:// or tcp://")
    parser.add_argument("--debug", action="store_true", help="Log DEBUG messages")
    parser.add_argument(
        "--led-count",
        type=int,
        default=DEFAULT_LEDS,
        help=f"Number of LEDs to control (1-{MAX_LEDS})",
    )
    parser.add_argument(
        "--led-brightness",
        type=int,
        choices=range(1, 32),
        default=31,
        help="LED brightness (integer from 1 to 31)",
    )
    parser.add_argument(
        "--led-pin",
        type=int,
        default=18,
        help="GPIO pin for LED data (default: 18, for WS281x)",
    )
    parser.add_argument(
        "--respeaker",
        action="store_true",
        help="Use ReSpeaker HAT LED controller",
    )
    parser.add_argument(
        "--respeaker-pin",
        type=int,
        default=12,
        help="GPIO pin for ReSpeaker LED power (default: 12)",
    )
    
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    # Create LED controller
    led_controller = create_led_controller(
        num_leds=args.led_count,
        gpio_pin=args.respeaker_pin,
        brightness=args.led_brightness,
        respeaker_mode=args.respeaker,
        led_pin=args.led_pin
    )
    
    # Signal handler for graceful shutdown
    def signal_handler(sig, frame):
        _LOGGER.info("Shutting down...")
        led_controller.cleanup()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    _LOGGER.info("LED service ready")

    # Start server
    server = AsyncServer.from_uri(args.uri)

    try:
        await server.run(partial(LEDEventHandler, led_controller))
    except KeyboardInterrupt:
        pass
    finally:
        led_controller.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass 