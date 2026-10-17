"""Config flow for Carrier Cync."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CarrierCyncApi
from .const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_MODEL,
    CONF_MEMBER_ID,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    DEFAULT_MODEL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MEMBER_ID): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Optional(CONF_DEVICE_MODEL, default=DEFAULT_MODEL): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=300)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate by calling dt API."""
    session = async_get_clientsession(hass)
    api = CarrierCyncApi(
        session,
        data[CONF_MEMBER_ID],
        data[CONF_DEVICE_ID],
        data.get(CONF_DEVICE_MODEL, DEFAULT_MODEL),
    )
    result = await api.async_test_connection()
    title = data.get(CONF_NAME) or DEFAULT_NAME
    model = result.get("model") or data.get(CONF_DEVICE_MODEL, DEFAULT_MODEL)
    return {"title": f"{title} ({model})", "model": model}


class CarrierCyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Carrier Cync."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID].lower())
            self._abort_if_unique_id_configured()
            try:
                info = await validate_input(self.hass, user_input)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
