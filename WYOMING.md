# Wyoming LED Service

This service integrates LED control with Wyoming protocol events for voice assistants.

## Features

- Works with various Raspberry Pi models including Pi 5
- Supports regular WS281x LEDs via GPIO (default pin 18)
- Supports Raspberry Pi 5 with direct SPI control
- Supports ReSpeaker 2-mic HAT with APA102 LEDs
- Automatically detects platform and chooses appropriate driver
- Visual feedback for various voice assistant events

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Install the systemd service:
   ```bash
   sudo cp wyoming-led.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable wyoming-led.service
   sudo systemctl start wyoming-led.service
   ```

## Usage

The service will automatically start and listen for Wyoming events on the configured port (default 10800).

### Command Line Options

```
usage: wyoming_led_service.py [-h] --uri URI [--debug] [--led-count LED_COUNT]
                             [--led-brightness {1,2,3,...,31}] [--led-pin LED_PIN]
                             [--respeaker] [--respeaker-pin RESPEAKER_PIN]

Wyoming LED service for Raspberry Pi

options:
  -h, --help            show this help message and exit
  --uri URI             unix:// or tcp://
  --debug               Log DEBUG messages
  --led-count LED_COUNT
                        Number of LEDs to control (1-10)
  --led-brightness {1,2,3,...,31}
                        LED brightness (integer from 1 to 31)
  --led-pin LED_PIN     GPIO pin for LED data (default: 18, for WS281x)
  --respeaker           Use ReSpeaker HAT LED controller
  --respeaker-pin RESPEAKER_PIN
                        GPIO pin for ReSpeaker LED power (default: 12)
```

### Example: Use with ReSpeaker 2-mic HAT

To use with a ReSpeaker 2-mic HAT:

```bash
python3 wyoming_led_service.py --uri tcp://0.0.0.0:10800 --led-count 3 --respeaker
```

### Example: Use with standard WS281x LEDs

To use with standard WS281x LEDs connected to GPIO pin 18:

```bash
python3 wyoming_led_service.py --uri tcp://0.0.0.0:10800 --led-count 8
```

### Example: Use with Raspberry Pi 5 SPI

For Raspberry Pi 5 with SPI enabled, the service will automatically use the more efficient SPI method:

```bash
python3 wyoming_led_service.py --uri tcp://0.0.0.0:10800 --led-count 10
```

## LED Color Indicators

- **Yellow**: Streaming voice data / Listening
- **Blue**: Wake word detected
- **Green**: (1 second) Transcript received / ASR completed
- **Green flash**: (3x) Satellite connected
- **Red**: Satellite disconnected
- **Off**: Idle / Not streaming

## Troubleshooting

- For Raspberry Pi 5 SPI mode, make sure SPI is enabled in `/boot/config.txt`
- For ReSpeaker HAT, ensure the GPIO pin for LED power is correct (default: 12)
- For standard WS281x LEDs, ensure the data pin is correct (default: 18)
- Check logs with `journalctl -u wyoming-led.service` 