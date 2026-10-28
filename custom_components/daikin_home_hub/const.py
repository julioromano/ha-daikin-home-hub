"""Integration identity and shared configuration defaults."""

from homeassistant.const import Platform

DOMAIN = "daikin_home_hub"
MIN_HA_VERSION = "2026.10.2"
CONF_UNIT_ID = "unit_id"
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
DEFAULT_SCAN_INTERVAL_SECONDS = 5
MIN_SCAN_INTERVAL_SECONDS = 5
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]
