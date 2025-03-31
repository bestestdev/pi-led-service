# Pi LED Controller

A service for controlling WS2812 LEDs on a Raspberry Pi over GPIO

## Installation

1. Install the required dependencies:
```bash
sudo apt-get update
sudo apt-get install python3-pip
pip3 install -r requirements.txt
```

2. Copy the service files to the appropriate locations:
```bash
sudo mkdir -p /opt/pi_led_service
sudo cp led_controller.py /opt/pi_led_service/
sudo cp pi-led.service /etc/systemd/system/
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pi-led
sudo systemctl start pi-led
```

## Usage

The LED controller provides the following commands:

1. Set a specific LED color:
```bash
sudo python3 led_controller.py set <led_index> <r> <g> <b>
```
Example: `sudo python3 led_controller.py set 0 255 0 0` (sets first LED to red)

2. Set all LEDs to the same color:
```bash
sudo python3 led_controller.py all <r> <g> <b>
```
Example: `sudo python3 led_controller.py all 0 255 0` (sets all LEDs to green)

3. Turn off all LEDs:
```bash
sudo python3 led_controller.py clear
```

## Notes

- LED indices range from 0 to 7
- Color values range from 0 to 255
- The service runs as root to access GPIO pins
- The service will automatically restart if it crashes 