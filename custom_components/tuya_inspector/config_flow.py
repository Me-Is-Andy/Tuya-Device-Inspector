"""Config flow for the Tuya Device Inspector."""
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import TuyaApiError, TuyaInspectorApi
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_DATA_CENTER,
    CONF_DEVICE_ID,
    DATA_CENTERS,
    DEFAULT_DATA_CENTER,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCESS_ID): str,
        vol.Required(CONF_ACCESS_SECRET): str,
        vol.Required(CONF_DATA_CENTER, default=DEFAULT_DATA_CENTER): SelectSelector(
            SelectSelectorConfig(
                options=sorted(DATA_CENTERS),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="data_center",
            )
        ),
    }
)


class TuyaInspectorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Credentials, then pick a device from the cloud project."""

    VERSION = 1

    def __init__(self) -> None:
        self._credentials: dict = {}
        self._devices: list[dict] = []

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            api = TuyaInspectorApi(
                async_get_clientsession(self.hass),
                DATA_CENTERS[user_input[CONF_DATA_CENTER]],
                user_input[CONF_ACCESS_ID].strip(),
                user_input[CONF_ACCESS_SECRET].strip(),
            )

            # Authentication and the device list are checked separately so a
            # failure in the second is not reported as bad credentials.
            try:
                await api.async_fetch_token()
            except TuyaApiError as err:
                _LOGGER.error("Tuya rejected the credentials: %s", err)
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error reaching Tuya")
                errors["base"] = "cannot_connect"
            else:
                try:
                    devices = await api.async_list_devices()
                except TuyaApiError as err:
                    _LOGGER.error("Could not list devices: %s", err)
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error listing devices")
                    errors["base"] = "cannot_connect"
                else:
                    if not devices:
                        errors["base"] = "no_devices"
                    else:
                        self._credentials = {
                            CONF_ACCESS_ID: user_input[CONF_ACCESS_ID].strip(),
                            CONF_ACCESS_SECRET: user_input[CONF_ACCESS_SECRET].strip(),
                            CONF_DATA_CENTER: user_input[CONF_DATA_CENTER],
                        }
                        self._devices = devices
                        return await self.async_step_device()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_device(self, user_input=None):
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]

            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            device = next(
                (d for d in self._devices if d.get("id") == device_id), {}
            )
            title = (
                device.get("customName")
                or device.get("name")
                or device_id
            )
            return self.async_create_entry(
                title=title,
                data={**self._credentials, CONF_DEVICE_ID: device_id},
            )

        options = []
        for device in self._devices:
            # customName is whatever the owner typed in the vendor app and may
            # be blank; name is the manufacturer's label.
            label = device.get("customName") or device.get("name") or device.get("id")
            model = device.get("name") or device.get("productName") or ""
            if model and model != label:
                label = f"{label} ({model})"
            options.append(SelectOptionDict(value=device.get("id", ""), label=label))

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options, mode=SelectSelectorMode.DROPDOWN
                        )
                    )
                }
            ),
        )

    async def async_step_reauth(self, entry_data):
        return await self.async_step_user()
