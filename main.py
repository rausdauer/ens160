"""
ENS160 example for Raspberry Pi Pico / Pico W

Wiring (default pins):
  ENS160 VCC  → 3.3V  (pin 36)
  ENS160 GND  → GND   (pin 38)
  ENS160 SDA  → GP4   (pin 6)
  ENS160 SCL  → GP5   (pin 7)
  ENS160 ADDR → GND   (I2C address 0x52)

Optional OLED on I2C1:
    OLED VCC    → 3.3V
    OLED GND    → GND
    OLED SDA    → GP6
    OLED SCL    → GP7

Many ENS160 combo boards also include an AHT20/AHT21 temperature/humidity
sensor at I2C address 0x38. If present, this example will read it and use
those values for ENS160 compensation automatically.
"""

from machine import I2C, Pin
import time
from ens160 import ENS160, VALIDITY_WARMUP, VALIDITY_STARTUP
from aht2x import AHT2x
from ssd1306 import SSD1306_I2C

# ── I2C setup ───────────────────────────────────────────────────────────────
sensor_i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400_000)
oled_i2c = I2C(1, sda=Pin(6), scl=Pin(7), freq=400_000)

devices = sensor_i2c.scan()
oled_devices = oled_i2c.scan()
print("I2C0 devices found:", [hex(a) for a in devices])
print("I2C1 devices found:", [hex(a) for a in oled_devices])

# ── Sensor init ─────────────────────────────────────────────────────────────
sensor = ENS160(sensor_i2c)
print("ENS160 ready, validity:", sensor.validity_name)

aht = None
if AHT2x.I2C_ADDR in devices:
    try:
        aht = AHT2x(sensor_i2c)
        print("AHT2x ready at 0x38")
    except Exception as exc:
        print("Found device at 0x38, but AHT2x init failed:", exc)

oled = None
for oled_addr in (0x3C, 0x3D):
    if oled_addr in oled_devices:
        try:
            oled = SSD1306_I2C(128, 32, oled_i2c, addr=oled_addr)
            print("OLED ready at {} on I2C1".format(hex(oled_addr)))
            oled.fill(0)
            oled.text("ENS160 monitor", 0, 0)
            oled.text("Starting...", 0, 12)
            oled.show()
            break
        except Exception as exc:
            print("Found OLED at {}, but init failed:".format(hex(oled_addr)), exc)

# Fallback compensation if no live temp/RH sensor is available.
fallback_temp_c = 25.0
fallback_rh_pct = 50.0
sensor.set_compensation(fallback_temp_c, fallback_rh_pct)

last_validity = None


def update_oled(aqi, tvoc, eco2, validity_name, temp_c, rh_pct, aqi_name):
    if oled is None:
        return

    status = validity_name
    if len(status) > 10:
        status = status[:10]

    oled.fill(0)
    oled.text("AQI:{} {}".format(aqi, aqi_name), 0, 0)
    oled.text("CO2:{} T:{:.1f}C".format(eco2, temp_c), 0, 12)
    oled.text("VOC:{} rF:{:.0f}%".format(tvoc, rh_pct), 0, 24)
    oled.show()

# ── Main loop ───────────────────────────────────────────────────────────────
while True:
    temp_c = None
    rh_pct = None

    if aht is not None:
        try:
            temp_c, rh_pct = aht.read()
            sensor.set_compensation(temp_c, rh_pct)
        except Exception as exc:
            print("AHT2x read failed:", exc)

    data = sensor.read(timeout_ms=1500)
    validity = sensor.validity

    if validity != last_validity:
        if validity == VALIDITY_STARTUP:
            print("Sensor in initial start-up (~1 h on first power-on) …")
        elif validity == VALIDITY_WARMUP:
            print("Sensor warming up (~3 min) …")
        else:
            print("Sensor status:", sensor.validity_name)
        last_validity = validity

    if data is not None:
        aqi = data["aqi"]
        tvoc = data["tvoc"]
        eco2 = data["eco2"]
        update_oled(aqi, tvoc, eco2, sensor.validity_name,temp_c, rh_pct, sensor.aqi_name)

        if temp_c is not None and rh_pct is not None:
            print(
                "T: {:.1f} C  |  RH: {:.1f} %  |  AQI: {:d} ({:s})  |  TVOC: {:4d} ppb  |  eCO2: {:4d} ppm  |  Status: {:s}".format(
                    temp_c, rh_pct, aqi, sensor.aqi_name, tvoc, eco2, sensor.validity_name
                )
            )
        else:
            print(
                "AQI: {:d} ({:s})  |  TVOC: {:4d} ppb  |  eCO2: {:4d} ppm  |  Status: {:s}".format(
                    aqi, sensor.aqi_name, tvoc, eco2, sensor.validity_name
                )
            )
    else:
        if oled is not None:
            oled.fill(0)
            oled.text("ENS160 timeout", 0, 0)
            oled.text(sensor.validity_name[:16], 0, 12)
            oled.show()
        print("ENS160 sample timeout; sensor status:", sensor.validity_name)

    time.sleep_ms(250)
