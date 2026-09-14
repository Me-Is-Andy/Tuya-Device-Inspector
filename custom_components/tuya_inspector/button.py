"""The export button.

Pressing it collects the device's description and writes it somewhere the
user can download it.
"""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .export import async_write_export

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    stored = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([TuyaExportButton(stored, config_entry.title)])


class TuyaExportButton(ButtonEntity):
    """Writes the export file when pressed."""

    _attr_has_entity_name = True
    _attr_name = "Export device details"
    _attr_icon = "mdi:file-download-outline"

    def __init__(self, stored: dict, title: str):
        self._stored = stored
        self._title = title
        self._device_id = stored["device_id"]
        self._attr_unique_id = f"{self._device_id}_export"

    @property
    def device_info(self):
        record = self._stored["record"]
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": record.get("custom_name")
            or record.get("name")
            or self._device_id,
            "manufacturer": "Tuya",
            "model": record.get("product_name") or record.get("model") or "Unknown",
        }

    async def async_press(self) -> None:
        try:
            await async_write_export(
                self.hass, self._stored["api"], self._device_id, self._title
            )
        except Exception as err:  # noqa: BLE001 - surfaced to the user
            _LOGGER.exception("Export failed")
            raise HomeAssistantError(f"Could not write the export: {err}") from err
