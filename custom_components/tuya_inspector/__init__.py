"""Tuya Device Inspector.

Reads a Tuya device's description from the cloud so it can be attached to a
bug report or a request to support a new model. It never controls anything.
"""
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TuyaApiError, TuyaInspectorApi
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_DATA_CENTER,
    CONF_DEVICE_ID,
    DATA_CENTERS,
    DEFAULT_DATA_CENTER,
    DOMAIN,
    SERVICE_EXPORT,
)
from .export import async_write_export

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BUTTON, Platform.SENSOR]

SERVICE_SCHEMA = vol.Schema({vol.Optional("entry_id"): str})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one device to inspect."""
    device_id = entry.data[CONF_DEVICE_ID]
    base_url = DATA_CENTERS.get(
        entry.data.get(CONF_DATA_CENTER, DEFAULT_DATA_CENTER),
        DATA_CENTERS[DEFAULT_DATA_CENTER],
    )

    api = TuyaInspectorApi(
        async_get_clientsession(hass),
        base_url,
        entry.data[CONF_ACCESS_ID],
        entry.data[CONF_ACCESS_SECRET],
    )

    try:
        record = await api.async_get_device(device_id)
    except TuyaApiError as err:
        if "1010" in str(err) or "1004" in str(err):
            raise ConfigEntryAuthFailed(f"Tuya rejected the credentials: {err}") from err
        raise ConfigEntryNotReady(f"Could not read the device: {err}") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Could not reach Tuya: {err}") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "device_id": device_id,
        "record": record,
        "title": entry.title,
    }

    _async_register_service(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_register_service(hass: HomeAssistant) -> None:
    """Expose the export as an action as well as a button.

    Registered once for the whole integration rather than per entry, so adding
    a second device does not replace the first one's handler.
    """
    if hass.services.has_service(DOMAIN, SERVICE_EXPORT):
        return

    async def _handle_export(call: ServiceCall) -> dict:
        entries = hass.data.get(DOMAIN, {})
        entry_id = call.data.get("entry_id")

        if entry_id:
            targets = {entry_id: entries[entry_id]} if entry_id in entries else {}
            if not targets:
                raise ValueError(f"No inspected device with entry id {entry_id}")
        else:
            targets = dict(entries)

        written = {}
        for target_id, stored in targets.items():
            written[target_id] = await async_write_export(
                hass, stored["api"], stored["device_id"], stored["title"]
            )
        return {"exports": written}

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT,
        _handle_export,
        schema=SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_EXPORT)
    return unload_ok
