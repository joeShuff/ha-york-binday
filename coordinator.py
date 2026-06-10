"""DataUpdateCoordinator for City of York Bins."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_ENDPOINT, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _parse_date(value: str) -> datetime | None:
    """Parse an ISO-formatted date string, returning None on failure."""
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _format_date(value: str) -> str | None:
    """Return a human-readable date string (DD/MM/YYYY), or None on failure."""
    dt = _parse_date(value)
    return dt.strftime("%d/%m/%Y") if dt else None


def _days_until(value: str) -> int | None:
    """Return the number of days until a collection date, or None on failure."""
    dt = _parse_date(value)
    if dt is None:
        return None
    diff = dt.date() - datetime.now().date()
    return diff.days


def _fetch_bin_data(uprn: str) -> list[dict[str, Any]]:
    """Blocking HTTP call — run this in the executor."""
    url = API_ENDPOINT.format(uprn=uprn)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout as err:
        raise UpdateFailed("Timed out contacting the York Bins API") from err
    except requests.exceptions.HTTPError as err:
        raise UpdateFailed(f"HTTP error from York Bins API: {err}") from err
    except requests.exceptions.RequestException as err:
        raise UpdateFailed(f"Error contacting York Bins API: {err}") from err

    try:
        services = response.json().get("services", [])
    except ValueError as err:
        raise UpdateFailed(f"Invalid JSON from York Bins API: {err}") from err

    bins: list[dict[str, Any]] = []
    for raw in services:
        service_name = raw.get("service", "unknown")
        next_raw = raw.get("nextCollection")
        last_raw = raw.get("lastCollected")

        days = _days_until(next_raw)
        next_date = _format_date(next_raw)

        # Treat past/invalid dates as unknown
        if days is not None and days < 0:
            days = None
            next_date = None

        bins.append(
            {
                "service": service_name,
                # Slug used as sensor unique_id suffix and entity_id
                "slug": service_name.lower().replace(" ", "_").replace("/", "_"),
                "days_until": days,
                "next_collection": next_date,
                "last_collection": _format_date(last_raw),
                "bin_description": raw.get("binDescription"),
                "frequency": raw.get("frequency"),
                "waste_type": raw.get("wasteType"),
            }
        )

    return bins


class YorkBinsCoordinator(DataUpdateCoordinator):
    """Coordinator that polls the York Bins API once a day."""

    def __init__(self, hass: HomeAssistant, uprn: str) -> None:
        self.uprn = uprn
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS),
        )

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch data from the API (called automatically by the coordinator)."""
        _LOGGER.debug("Fetching bin data for UPRN %s", self.uprn)
        return await self.hass.async_add_executor_job(_fetch_bin_data, self.uprn)
