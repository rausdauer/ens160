"""
AHT2x MicroPython driver
Supports AHT20 / AHT21 style temperature and humidity sensors over I2C.
"""
import time


class AHT2x:
    """Driver for AHT20/AHT21 compatible I2C temperature/humidity sensors."""

    I2C_ADDR = 0x38

    def __init__(self, i2c, addr=I2C_ADDR):
        self._i2c = i2c
        self._addr = addr

        self.soft_reset()
        time.sleep_ms(20)

        if not self.calibrated:
            self._i2c.writeto(self._addr, b"\xBE\x08\x00")
            time.sleep_ms(10)

    @property
    def status(self):
        return self._i2c.readfrom(self._addr, 1)[0]

    @property
    def busy(self):
        return bool(self.status & 0x80)

    @property
    def calibrated(self):
        return bool(self.status & 0x08)

    def soft_reset(self):
        self._i2c.writeto(self._addr, b"\xBA")

    def read(self):
        self._i2c.writeto(self._addr, b"\xAC\x33\x00")

        for _ in range(20):
            time.sleep_ms(10)
            if not self.busy:
                break
        else:
            raise RuntimeError("AHT2x measurement timeout")

        data = self._i2c.readfrom(self._addr, 6)
        raw_h = ((data[1] << 16) | (data[2] << 8) | data[3]) >> 4
        raw_t = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]

        humidity = raw_h * 100.0 / 1048576.0
        temperature = raw_t * 200.0 / 1048576.0 - 50.0
        return temperature, humidity
