# ENS160 Air Quality Monitor — MicroPython / Raspberry Pi Pico

Reads the **ScioSense ENS160** multi-gas sensor and optionally an **AHT20/AHT21** temperature and humidity sensor. Results are printed to the serial console and, if an SSD1306 128×32 OLED is connected, also shown on the display.

## What it measures

| Value | Unit | Source |
|-------|------|--------|
| AQI (UBA index 1–5) | — | ENS160 |
| TVOC (total volatile organic compounds) | ppb | ENS160 |
| eCO2 (equivalent CO₂) | ppm | ENS160 |
| Temperature | °C | AHT20/21 (optional) |
| Relative humidity | %RH | AHT20/21 (optional) |

Temperature and humidity are fed back into the ENS160 for on-chip compensation, improving gas measurement accuracy.

## Hardware

### Required

- Raspberry Pi Pico or Pico W
- ENS160 breakout board (ScioSense or compatible)

### Optional but recommended

- AHT20 or AHT21 temperature/humidity sensor (many ENS160 combo boards include one)
- SSD1306 128×32 OLED display (I²C)

## Wiring

### I²C bus 0 — sensors (GP4 / GP5)

| Signal | Pico pin | ENS160 / AHT2x pin |
|--------|----------|--------------------|
| 3.3 V  | Pin 36   | VCC                |
| GND    | Pin 38   | GND                |
| SDA    | GP4 (pin 6) | SDA             |
| SCL    | GP5 (pin 7) | SCL             |
| —      | GND      | ADDR (→ 0x52)      |

### I²C bus 1 — OLED display (GP6 / GP7)

| Signal | Pico pin | OLED pin |
|--------|----------|----------|
| 3.3 V  | Pin 36   | VCC      |
| GND    | Pin 38   | GND      |
| SDA    | GP6 (pin 9) | SDA   |
| SCL    | GP7 (pin 10) | SCL  |

The OLED is detected automatically at address `0x3C` or `0x3D`. If no display is found the code runs normally with serial output only.

## Files

| File | Purpose |
|------|---------|
| `main.py` | Main program — init, compensation loop, serial + OLED output |
| `ens160.py` | ENS160 driver (PART_ID check, operating modes, AQI/TVOC/eCO2 registers) |
| `aht2x.py` | AHT20/AHT21 driver (temperature and humidity) |
| `ssd1306.py` | Minimal SSD1306 I²C OLED driver (128×32 and 128×64) |

## Serial output (example)

```
I2C0 devices found: ['0x38', '0x53']
I2C1 devices found: ['0x3c']
ENS160 ready, validity: Initial start-up
AHT2x ready at 0x38
OLED ready at 0x3c on I2C1
Sensor in initial start-up (~1 h on first power-on) …
T: 26.8 C  |  RH: 30.4 %  |  AQI: 1 (Excellent)  |  TVOC:   32 ppb  |  eCO2:  418 ppm  |  Status: Initial start-up
T: 26.8 C  |  RH: 30.4 %  |  AQI: 1 (Excellent)  |  TVOC:   37 ppb  |  eCO2:  429 ppm  |  Status: Initial start-up
```

## OLED layout (128×32)

```
AQI:1 Initial st
TVOC:32 eC:418
```

Line 1: AQI index and truncated validity status  
Line 2: TVOC in ppb and eCO2 in ppm

## Sensor warm-up

The ENS160 gas algorithm has two warm-up phases:

| Status | Duration | Meaning |
|--------|----------|---------|
| Initial start-up | ~1 hour | First power-on only; algorithm is building a baseline |
| Warm-up | ~3 minutes | After waking from sleep or reset |
| Normal | — | Readings are fully settled and reliable |

Measurements are shown during all phases. The validity status is printed in both the serial output and on the OLED so you can tell at a glance whether the readings are settled.

## Deploying to the Pico

Copy all four `.py` files to the root of the Pico filesystem using Thonny, `mpremote`, or MicroPico (VS Code extension):

```
mpremote cp ens160.py aht2x.py ssd1306.py main.py :
```

`main.py` runs automatically on boot.
