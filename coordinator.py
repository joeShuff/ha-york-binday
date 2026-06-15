"""DataUpdateCoordinator for City of York Bins."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import API_ENDPOINT, DEFAULT_SCAN_INTERVAL_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _parse_date(value: str) -> datetime | None:
    """Parse an ISO-formatted date string, localised to the HA configured timezone."""
    try:
        dt = datetime.fromisoformat(value)
        # Make timezone-aware using HA's configured timezone
        if dt.tzinfo is None:
            dt = dt_util.as_local(dt)
        return dt
    except (ValueError, TypeError):
        return None


def _format_date(value: str) -> str | None:
    """Return a human-readable date string (DD/MM/YYYY), or None on failure."""
    dt = _parse_date(value)
    return dt.strftime("%d/%m/%Y") if dt else None


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

    now = dt_util.now()
    bins: list[dict[str, Any]] = []
    for raw in services:
        service_name = raw.get("service", "unknown")
        next_dt = _parse_date(raw.get("nextCollection"))
        last_dt = _parse_date(raw.get("lastCollected"))

        # Discard dates already in the past
        if next_dt is not None and next_dt < now:
            next_dt = None

        bins.append(
            {
                "service": service_name,
                "slug": service_name.lower().replace(" ", "_").replace("/", "_"),
                "next_collection_dt": next_dt,
                "next_collection": _format_date(raw.get("nextCollection")),
                "last_collection": _format_date(raw.get("lastCollected")),
                "bin_description": raw.get("binDescription"),
                "frequency": raw.get("frequency"),
                "waste_type": raw.get("wasteType"),
            }
        )

    return bins


class YorkBinsCoordinator(DataUpdateCoordinator):
    """Coordinator that polls the York Bins API to refresh collection dates."""

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