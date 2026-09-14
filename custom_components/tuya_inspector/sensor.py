"""A single sensor per inspected device.

Its only job is to give the device somewhere to live in the registry, so the
device page exists and the diagnostics download has a home. The state is the
product id, which is the thing that identifies a model.
"""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    stored = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([TuyaProductSensor(stored)])


class TuyaProductSensor(SensorEntity):
    """Shows the product id, with the rest of the record as attributes."""

    _attr_has_entity_name = True
    _attr_name = "Product ID"
    _attr_icon = "mdi:identifier"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    def __init__(self, stored: dict):
        self._record = stored["record"]
        self._device_id = stored["device_id"]
        self._attr_unique_id = f"{self._device_id}_product_id"

    @property
    def device_info(self):
        record = self._record
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": record.get("custom_name")
            or record.get("name")
            or self._device_id,
            "manufacturer": "Tuya",
            "model": record.get("product_name") or record.get("model") or "Unknown",
        }

    @property
    def native_value(self) -> str | None:
        return self._record.get("product_id")

    @property
    def extra_state_attributes(self) -> dict:
        record = self._record
        return {
            "device_id": self._device_id,
            "category": record.get("category"),
            "product_name": record.get("product_name"),
            "model": record.get("model"),
            "name": record.get("name"),
            "online": record.get("online"),
        }
