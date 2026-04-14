"""
ENS160 MicroPython Driver
ScioSense ENS160 digital multi-gas sensor (I2C)
Measures: AQI (1-5), TVOC (ppb), eCO2 (ppm)
"""
import time

# Register map
_REG_PART_ID       = 0x00  # 2 bytes, R   – should read 0x0160
_REG_OPMODE        = 0x10  # 1 byte,  R/W
_REG_CONFIG        = 0x11  # 1 byte,  R/W
_REG_COMMAND       = 0x12  # 1 byte,  R/W
_REG_TEMP_IN       = 0x13  # 2 bytes, R/W – temperature compensation (K * 64)
_REG_RH_IN         = 0x15  # 2 bytes, R/W – humidity compensation (% * 512)
_REG_DEVICE_STATUS = 0x20  # 1 byte,  R
_REG_DATA_AQI      = 0x21  # 1 byte,  R   – AQI-UBA index 1..5
_REG_DATA_TVOC     = 0x22  # 2 bytes, R   – TVOC ppb
_REG_DATA_ECO2     = 0x24  # 2 bytes, R   – eCO2 ppm
_REG_DATA_T        = 0x30  # 2 bytes, R   – temperature used internally (K * 64)
_REG_DATA_RH       = 0x32  # 2 bytes, R   – humidity used internally (% * 512)
_REG_GPR_WRITE     = 0x40  # 8 bytes, R/W
_REG_GPR_READ      = 0x48  # 8 bytes, R

# Operating modes
OPMODE_DEEP_SLEEP = 0x00
OPMODE_IDLE       = 0x01
OPMODE_STANDARD   = 0x02
OPMODE_LP         = 0x03  # Low Power
OPMODE_ULP        = 0x04  # Ultra-Low Power

# DEVICE_STATUS bit masks
_STATUS_NEWDAT   = 0x02   # bit 1 – new measurement data available
_STATUS_NEWGPR   = 0x01   # bit 0 – new GPR data available
_STATUS_VALIDITY = 0x0C   # bits 3:2
_STATUS_OPMODE   = 0x30   # bits 5:4

# Validity codes (STATUS bits 3:2)
VALIDITY_NORMAL  = 0  # normal operation
VALIDITY_WARMUP  = 1  # warming up (~3 min after leaving sleep)
VALIDITY_STARTUP = 2  # initial start-up (~1 h after first power-on)
VALIDITY_INVALID = 3  # invalid output

_VALIDITY_NAMES = {
    VALIDITY_NORMAL:  "Normal",
    VALIDITY_WARMUP:  "Warm-up",
    VALIDITY_STARTUP: "Initial start-up",
    VALIDITY_INVALID: "Invalid",
}

_AQI_NAMES = ["", "Excellent", "Good", "Moderate", "Poor", "Unhealthy"]


class ENS160:
    """Driver for the ENS160 multi-gas sensor over I2C."""

    I2C_ADDR = 0x52   # ADDR pin → GND
    I2C_ADDR_HIGH = 0x53  # ADDR pin → VCC

    def __init__(self, i2c, addr=I2C_ADDR_HIGH):
        self._i2c = i2c
        self._addr = addr

        part_id = self._read_u16(_REG_PART_ID)
        if part_id != 0x0160:
            raise RuntimeError(
                "ENS160 not found (PART_ID=0x{:04X}, expected 0x0160)".format(part_id)
            )

        # Transition to idle first (clears any previous state), then standard mode
        self._write(_REG_OPMODE, OPMODE_IDLE)
        time.sleep_ms(10)
        self._write(_REG_OPMODE, OPMODE_STANDARD)
        time.sleep_ms(20)

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def _write(self, reg, value):
        self._i2c.writeto_mem(self._addr, reg, bytes([value]))

    def _read(self, reg, n=1):
        return self._i2c.readfrom_mem(self._addr, reg, n)

    def _read_u8(self, reg):
        return self._read(reg, 1)[0]

    def _read_u16(self, reg):
        d = self._read(reg, 2)
        return d[0] | (d[1] << 8)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_mode(self, mode):
        """Set the operating mode (use OPMODE_* constants)."""
        self._write(_REG_OPMODE, mode)
        time.sleep_ms(10)

    def set_compensation(self, temp_c, rh_pct):
        """
        Supply ambient temperature and humidity for on-chip compensation.
        Call this before reading measurements for best accuracy.

        :param temp_c: Ambient temperature in °C  (e.g. 25.0)
        :param rh_pct: Relative humidity in %RH   (e.g. 50.0)
        """
        temp_raw = int((temp_c + 273.15) * 64)
        rh_raw   = int(rh_pct * 512)
        self._i2c.writeto_mem(
            self._addr, _REG_TEMP_IN,
            bytes([temp_raw & 0xFF, (temp_raw >> 8) & 0xFF])
        )
        self._i2c.writeto_mem(
            self._addr, _REG_RH_IN,
            bytes([rh_raw & 0xFF, (rh_raw >> 8) & 0xFF])
        )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @property
    def status(self):
        """Raw DEVICE_STATUS byte."""
        return self._read_u8(_REG_DEVICE_STATUS)

    @property
    def new_data(self):
        """True when fresh AQI / TVOC / eCO2 measurements are ready."""
        return bool(self.status & _STATUS_NEWDAT)

    @property
    def validity(self):
        """Returns validity code (0=Normal, 1=Warm-up, 2=Start-up, 3=Invalid)."""
        return (self.status & _STATUS_VALIDITY) >> 2

    @property
    def validity_name(self):
        """Human-readable validity string."""
        return _VALIDITY_NAMES.get(self.validity, "Unknown")

    # ------------------------------------------------------------------
    # Measurement data
    # ------------------------------------------------------------------

    @property
    def aqi(self):
        """UBA Air Quality Index: 1 (Excellent) … 5 (Unhealthy)."""
        return self._read_u8(_REG_DATA_AQI) & 0x07

    @property
    def aqi_name(self):
        """Human-readable AQI label."""
        v = self.aqi
        return _AQI_NAMES[v] if 1 <= v <= 5 else "Unknown"

    @property
    def tvoc(self):
        """Total VOC concentration in ppb."""
        return self._read_u16(_REG_DATA_TVOC)

    @property
    def eco2(self):
        """Equivalent CO2 concentration in ppm."""
        return self._read_u16(_REG_DATA_ECO2)

    @property
    def temperature(self):
        """Temperature (°C) actually used by the sensor for compensation."""
        raw = self._read_u16(_REG_DATA_T)
        return raw / 64.0 - 273.15

    @property
    def humidity(self):
        """Relative humidity (%RH) actually used by the sensor for compensation."""
        raw = self._read_u16(_REG_DATA_RH)
        return raw / 512.0

    def wait_for_data(self, timeout_ms=2000, poll_ms=20):
        """Wait until a fresh measurement is available."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if self.new_data:
                return True
            time.sleep_ms(poll_ms)
        return False

    def read(self, timeout_ms=2000):
        """
        Return a dict with all measurements in a single call.
        Blocks until new data is ready or returns None on timeout.
        """
        if not self.wait_for_data(timeout_ms=timeout_ms):
            return None

        st = self.status
        return {
            "aqi":       self._read_u8(_REG_DATA_AQI) & 0x07,
            "tvoc":      self._read_u16(_REG_DATA_TVOC),
            "eco2":      self._read_u16(_REG_DATA_ECO2),
            "validity":  (st & _STATUS_VALIDITY) >> 2,
        }
