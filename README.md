# Pi LED Controller

A service for controlling WS2812 LEDs on Raspberry Pi models, including Pi 5 and Pi Zero 2.

## Hardware Setup

This controller supports two different hardware setups depending on your Raspberry Pi model:

### For Raspberry Pi 5

Connect the WS2812 LED strip to the Raspberry Pi 5 using the SPI interface:

#### SPI Connection (Raspberry Pi 5)
1. Connect the LED strip's data pin to Physical Pin 19 (GPIO 10, MOSI)
2. Connect VCC to the 5V rail
3. Connect GND to the ground rail
4. Add a 0.1µF (100nF) capacitor between VCC and GND near the first LED

```
LED Strip Connection for Pi 5 (SPI):
   5V Rail ──────┬─────── VCC
                 │
                 │ 0.1µF
                 │
   GND Rail ─────┴─────── GND
                 │
   GPIO 10 ──────┴─────── Data In
```

### For Other Raspberry Pi Models (Pi Zero 2, Pi 3, Pi 4, etc.)

Connect the WS2812 LED strip to the Raspberry Pi using GPIO 18 (PWM0):

#### PWM Connection (Pi Zero 2, Pi 3, Pi 4, etc.)
1. Connect the LED strip's data pin to Physical Pin 12 (GPIO 18, PWM0)
2. Connect VCC to the 5V rail
3. Connect GND to the ground rail
4. Add a 0.1µF (100nF) capacitor between VCC and GND near the first LED

```
LED Strip Connection for Other Pi Models (PWM):
   5V Rail ──────┬─────── VCC
                 │
                 │ 0.1µF
                 │
   GND Rail ─────┴─────── GND
                 │
   GPIO 18 ──────┴─────── Data In
```

### Power Setup (All Models)
1. Create a 5V power rail:
   - Connect Physical Pin 2 or 4 (5V) to a positive rail
   - Connect Physical Pin 6, 9, 14, 20, 25, 30, 34, or 39 (GND) to a negative rail
   - Connect the power supply's 5V to the positive rail
   - Connect the power supply's GND to the negative rail

2. Add power protection:
   - Place a 1000µF capacitor in parallel between the positive and negative rails near where the power supply connects
   - This bulk capacitor helps stabilize the power supply for all LEDs

```
Power Supply Connection:
   5V ──────┬─────── 5V Rail
            │
            │ 1000µF
            │
   GND ─────┴─────── GND Rail
```

### Protection Components (All Models)
For reliable operation of WS2812 LEDs, add the following components:
- A 300-500Ω resistor between the Raspberry Pi's GPIO pin and the LED strip's data input

## Installation

1. Clone the repository:
```bash
cd /home/pi
git clone https://github.com/bestestdev/pi-led-service.git
cd pi-led-service
```

2. Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. For Raspberry Pi 5, enable SPI interface:
```bash
sudo raspi-config
```
Navigate to Interface Options > SPI > Enable

5. Copy the service file to systemd:
```bash
sudo cp pi-led.service /etc/systemd/system/
```

6. Enable and start the service:
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

- LED indices range from 0 to 9
- Color values range from 0 to 255
- The service runs as root to access GPIO/SPI interface
- The service will automatically restart if it crashes
- Make sure to activate the virtual environment (`source venv/bin/activate`) before running any commands
- The controller automatically detects which Raspberry Pi model you're using and uses the appropriate library 