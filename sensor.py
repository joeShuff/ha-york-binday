"""Sensor platform for City of York Bins."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_UPRN, DOMAIN
from .coordinator import YorkBinsCoordinator

_LOGGER = logging.getLogger(__name__)

_ICON_MAP: dict[str, str] = {
    "refuse": "mdi:trash-can",
    "recycling": "mdi:recycle",
    "garden": "mdi:leaf",
}
_DEFAULT_ICON = "mdi:delete"


def _device_info(uprn: str, bin_data: dict[str, Any]) -> DeviceInfo:
    """Build the DeviceInfo for a bin service."""
    slug = bin_data["slug"]
    service = bin_data["service"]
    collected_by = bin_data.get("collected_by", "City of York Council")
    return DeviceInfo(
        identifiers={(DOMAIN, f"{uprn}_{slug}")},
        name=service.title(),
        manufacturer=collected_by,
        model=bin_data.get("bin_description"),
        suggested_area="Outside",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up York Bins sensors from a config entry."""
    coordinator: YorkBinsCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_config_entry_first_refresh()

    entities: list[SensorEntity] = []
    for bin_data in coordinator.data:
        entities.append(NextCollectionSensor(coordinator, entry, bin_data))
        entities.append(LastCollectionSensor(coordinator, entry, bin_data))
        entities.append(FrequencySensor(coordinator, entry, bin_data))
        entities.append(WasteTypeSensor(coordinator, entry, bin_data))
        entities.append(BinDescriptionSensor(coordinator, entry, bin_data))
        entities.append(CollectedBySensor(coordinator, entry, bin_data))

    async_add_entities(entities)


class YorkBinBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for all York Bin sensors — handles coordinator wiring and device linkage."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YorkBinsCoordinator,
        entry: ConfigEntry,
        bin_data: dict[str, Any],
        sensor_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._slug = bin_data["slug"]
        self._uprn = entry.data[CONF_UPRN]
        self._sensor_key = sensor_key

        self._attr_unique_id = f"{DOMAIN}_{self._uprn}_{self._slug}_{sensor_key}"
        self._attr_device_info = _device_info(self._uprn, bin_data)

    def _bin(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return next(
            (b for b in self.coordinator.data if b["slug"] == self._slug), None
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._bin() is not None


class NextCollectionSensor(YorkBinBaseSensor):
    """Next collection date — shown as a relative timestamp by HA."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "next_collection"

    def __init__(self, coordinator, entry, bin_data):
        super().__init__(coordinator, entry, bin_data, "next_collection")
        self._attr_name = "Next Collection"
        self._attr_icon = _ICON_MAP.get(bin_data["slug"], _DEFAULT_ICON)

    @property
    def native_value(self) -> datetime | None:
        bin_data = self._bin()
        return bin_data["next_collection_dt"] if bin_data else None


class LastCollectionSensor(YorkBinBaseSensor):
    """Last collection date."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_collection"

    def __init__(self, coordinator, entry, bin_data):
        super().__init__(coordinator, entry, bin_data, "last_collection")
        self._attr_name = "Last Collection"
        self._attr_icon = "mdi:history"

    @property
    def native_value(self) -> datetime | None:
        bin_data = self._bin()
        return bin_data["last_collection_dt"] if bin_data else None


class FrequencySensor(YorkBinBaseSensor):
    """Collection frequency as a plain text sensor."""

    def __init__(self, coordinator, entry, bin_data):
        super().__init__(coordinator, entry, bin_data, "frequency")
        self._attr_name = "Frequency"
        self._attr_icon = "mdi:calendar-sync"

    @property
    def native_value(self) -> str | None:
        bin_data = self._bin()
        return bin_data["frequency"] if bin_data else None


class WasteTypeSensor(YorkBinBaseSensor):
    """Waste type accepted by this bin."""

    def __init__(self, coordinator, entry, bin_data):
        super().__init__(coordinator, entry, bin_data, "waste_type")
        self._attr_name = "Waste Type"
        self._attr_icon = "mdi:information-outline"

    @property
    def native_value(self) -> str | None:
        bin_data = self._bin()
        return bin_data["waste_type"] if bin_data else None


class BinDescriptionSensor(YorkBinBaseSensor):
    """Physical bin description (size, colour, quantity)."""

    def __init__(self, coordinator, entry, bin_data):
        super().__init__(coordinator, entry, bin_data, "bin_description")
        self._attr_name = "Bin Description"
        self._attr_icon = "mdi:delete-variant"

    @property
    def native_value(self) -> str | None:
        bin_data = self._bin()
        return bin_data["bin_description"] if bin_data else None


class CollectedBySensor(YorkBinBaseSensor):
    """Who collects this bin."""

    def __init__(self, coordinator, entry, bin_data):
        super().__init__(coordinator, entry, bin_data, "collected_by")
        self._attr_name = "Collected By"
        self._attr_icon = "mdi:truck"

    @property
    def native_value(self) -> str | None:
        bin_data = self._bin()
        return bin_data.get("collected_by") if bin_data else None