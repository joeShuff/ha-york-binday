"""Calendar platform for City of York Bins."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_UPRN, DOMAIN, ROUND_TYPE_MARKERS, ROUND_TYPE_NAMES
from .coordinator import YorkBinsCalendarCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the York Bins calendar from a config entry."""
    coordinator = YorkBinsCalendarCoordinator(hass, entry.data[CONF_UPRN])
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([YorkBinsCalendar(coordinator, entry)])


def _to_event(collection: dict[str, Any]) -> CalendarEvent:
    """Convert a collection dict into an all-day CalendarEvent."""
    round_type = collection["round_type"]
    name = ROUND_TYPE_NAMES.get(round_type, round_type.title())
    marker = ROUND_TYPE_MARKERS.get(round_type, "🗑️")
    return CalendarEvent(
        start=collection["date"],
        end=collection["date"] + timedelta(days=1),  # all-day: end is exclusive
        summary=f"{marker} {name}",
        description=f"{name} bin collection",
    )


class YorkBinsCalendar(CoordinatorEntity[YorkBinsCalendarCoordinator], CalendarEntity):
    """A single calendar containing every bin collection for the UPRN."""

    _attr_has_entity_name = False
    _attr_icon = "mdi:calendar-month"

    def __init__(self, coordinator: YorkBinsCalendarCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        uprn = entry.data[CONF_UPRN]
        self._attr_name = f"Bins - {entry.title}"
        self._attr_unique_id = f"{DOMAIN}_{uprn}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{uprn}_calendar")},
            name=f"Bin Collections - {entry.title}",
            manufacturer="City of York Council",
            suggested_area="Outside",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming collection."""
        today = dt_util.now().date()
        for collection in self.coordinator.data or []:
            if collection["date"] >= today:
                return _to_event(collection)
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return collections overlapping the requested window."""
        start = dt_util.as_local(start_date).date()
        end = dt_util.as_local(end_date).date()
        return [
            _to_event(c)
            for c in self.coordinator.data or []
            if start <= c["date"] <= end
        ]