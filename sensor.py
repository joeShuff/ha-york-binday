"""Sensor platform for City of York Bins."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_UPRN, DOMAIN
from .coordinator import YorkBinsCoordinator

_LOGGER = logging.getLogger(__name__)

# Map common York waste type slugs to a friendly icon
_ICON_MAP: dict[str, str] = {
    "refuse": "mdi:trash-can",
    "recycling": "mdi:recycle",
    "garden": "mdi:leaf",
}
_DEFAULT_ICON = "mdi:help"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up York Bins sensors from a config entry."""
    coordinator: YorkBinsCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Wait for the first refresh so we know which bins exist
    await coordinator.async_config_entry_first_refresh()

    entities = [
        YorkBinSensor(coordinator, entry, bin_data)
        for bin_data in coordinator.data
    ]
    async_add_entities(entities)


class YorkBinSensor(CoordinatorEntity, SensorEntity):
    """A sensor representing a single bin collection service."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: YorkBinsCoordinator,
        entry: ConfigEntry,
        bin_data: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._slug = bin_data["slug"]
        self._uprn = entry.data[CONF_UPRN]

        # Stable unique ID: domain + uprn + bin slug
        self._attr_unique_id = f"{DOMAIN}_{self._uprn}_{self._slug}"
        self._attr_name = bin_data["waste_type"]
        self._attr_icon = _ICON_MAP.get(self._slug, _DEFAULT_ICON)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP

    # ------------------------------------------------------------------
    # Properties derived from coordinator data
    # ------------------------------------------------------------------

    def _bin(self) -> dict[str, Any] | None:
        """Return this sensor's slice of coordinator data."""
        if not self.coordinator.data:
            return None
        return next(
            (b for b in self.coordinator.data if b["slug"] == self._slug), None
        )

    @property
    def native_value(self) -> datetime | None:
        """The next collection datetime — HA displays this as a relative string."""
        bin_data = self._bin()
        return bin_data["next_collection_dt"] if bin_data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Extra detail exposed in the entity's attributes panel."""
        bin_data = self._bin()
        if not bin_data:
            return {}
        return {
            "next_collection": bin_data["next_collection"],
            "last_collection": bin_data["last_collection"],
            "bin_description": bin_data["bin_description"],
            "frequency": bin_data["frequency"],
            "waste_type": bin_data["waste_type"],
            "slug": bin_data["slug"],
        }

    @property
    def available(self) -> bool:
        """Mark unavailable if the coordinator had an error or bin not found."""
        return self.coordinator.last_update_success and self._bin() is not None
