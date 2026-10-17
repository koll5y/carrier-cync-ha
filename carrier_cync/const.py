"""Constants for Carrier Cync."""

DOMAIN = "carrier_cync"
DEFAULT_NAME = "Carrier Cync"
DEFAULT_MODEL = "SA"
DEFAULT_SCAN_INTERVAL = 20

API_BASE = "https://www.carrieriot.com/api/v1"
API_CONTROL = f"{API_BASE}/control.php"

# dt / control keys (SA 실측)
KEY_POWER = "2A"
KEY_MODE = "2B"
KEY_OPTIONS = "2C"
KEY_SPLASH = "2D"
KEY_SET_TEMP_WRITE = "3A"  # write: °C * 2
KEY_SET_HUMIDITY = "3B"
KEY_FAN = "3C"
KEY_SET_TEMP_STATE = "3D"  # read: °C (also PMV step write)
KEY_ROOM_TEMP = "3E"
KEY_ROOM_HUMIDITY = "3J"
KEY_SET_HUMIDITY_STATE = "3K"
KEY_FAN_STATE = "3S"
KEY_PMV_STATE = "3h"
KEY_OUTDOOR_TEMP = "1L"

# 2B mode values
MODE_COOL = 6
MODE_HEAT = 13
MODE_DRY = 5
MODE_FAN = 10  # 공기청정
MODE_PMV_COOL = 14
MODE_PMV_HEAT = 15

CONF_MEMBER_ID = "member_id"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_MODEL = "device_model"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"
