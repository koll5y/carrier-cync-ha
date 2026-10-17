"""Constants for Carrier Cync."""

DOMAIN = "carrier_cync"
DEFAULT_NAME = "Carrier Cync"
DEFAULT_MODEL = "SA"
DEFAULT_SCAN_INTERVAL = 20

API_BASE = "https://www.carrieriot.com/api/v1"
API_CONTROL = f"{API_BASE}/control.php"
API_WEATHER = f"{API_BASE}/weather.php"

# dt / control keys (SA 실측)
KEY_POWER = "2A"
KEY_MODE = "2B"
KEY_OPTIONS = "2C"
KEY_SPLASH = "2D"
# 주의: 3A 는 읽기/쓰기 스케일이 다름
#   READ  3A = 실내온도 × 10  (예: 220 → 22.0°C)  ← 앱 실내온도와 일치
#   WRITE 3A = 희망온도 × 2   (예: 25°C → 50)
KEY_ROOM_TEMP_READ = "3A"
KEY_SET_TEMP_WRITE = "3A"
KEY_SET_HUMIDITY = "3B"
KEY_FAN = "3C"
KEY_SET_TEMP_STATE = "3D"  # 희망온도 °C (읽기)
KEY_ROOM_TEMP_ALT = "3E"  # 모드에 따라 희망온도를 따라가기도 함 (비권장)
KEY_ROOM_HUMIDITY = "3J"
KEY_SET_HUMIDITY_STATE = "3K"
KEY_FAN_STATE = "3S"
KEY_PMV_STATE = "3h"
KEY_OUTDOOR_TEMP_UNIT = "1L"
KEY_OUTDOOR_HUMI_UNIT = "1A"

POWER_OFF = 0
POWER_ON = 1
POWER_AUTO_DRY = 2

MODE_COOL = 6
MODE_HEAT = 13
MODE_DRY = 5
MODE_FAN = 10
MODE_PMV_COOL = 14
MODE_PMV_HEAT = 15

CONF_MEMBER_ID = "member_id"
CONF_DEVICE_ID = "device_id"
CONF_DEVICE_MODEL = "device_model"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"
