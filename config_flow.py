"""Config flow for City of York Bins integration."""
from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_UPRN

_LOGGER = logging.getLogger(__name__)

CONF_POSTCODE = "postcode"
CONF_ADDRESS = "address"

POSTCODE_SCHEMA = vol.Schema({
    vol.Required(CONF_POSTCODE): str,
})


def _lookup_postcode(postcode: str) -> list[dict]:
    """Call the York address API and return a list of address dicts."""
    cleaned = postcode.strip().replace(" ", "").lower()
    url = f"https://addresses.york.gov.uk/api/address/lookupbypostcode/{cleaned}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout as err:
        raise CannotConnect("Timed out contacting the York address API") from err
    except requests.exceptions.RequestException as err:
        raise CannotConnect(f"Error contacting York address API: {err}") from err

    results = response.json()
    if not results:
        raise NoAddressesFound(f"No addresses found for postcode {postcode!r}")
    return results


def _validate_uprn(uprn: str) -> int:
    """Hit the bin API to confirm the UPRN has collection data; return bin count."""
    from .coordinator import _fetch_bin_data
    bins = _fetch_bin_data(uprn)
    if not bins:
        raise NoBinsFound(f"No bin collections found for UPRN {uprn!r}")
    return len(bins)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Two-step config flow: postcode → address picker."""

    VERSION = 1

    def __init__(self) -> None:
        self._addresses: list[dict] = []
        self._postcode: str = ""

    # ------------------------------------------------------------------
    # Step 1 — postcode entry
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            postcode = user_input[CONF_POSTCODE].strip()
            try:
                self._addresses = await self.hass.async_add_executor_job(
                    _lookup_postcode, postcode
                )
                self._postcode = postcode
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoAddressesFound:
                errors[CONF_POSTCODE] = "no_addresses"
            except Exception:
                _LOGGER.exception("Unexpected error during postcode lookup")
                errors["base"] = "unknown"
            else:
                return await self.async_step_address()

        return self.async_show_form(
            step_id="user",
            data_schema=POSTCODE_SCHEMA,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Step 2 — address picker
    # ------------------------------------------------------------------

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        # Build {shortAddress: uprn} map for the selector
        address_map: dict[str, str] = {
            a["shortAddress"]: a["uprn"] for a in self._addresses
        }

        if user_input is not None:
            selected_address = user_input[CONF_ADDRESS]
            uprn = address_map[selected_address]

            await self.async_set_unique_id(uprn)
            self._abort_if_unique_id_configured()

            try:
                await self.hass.async_add_executor_job(_validate_uprn, uprn)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except NoBinsFound:
                errors["base"] = "no_bins"
            except Exception:
                _LOGGER.exception("Unexpected error validating UPRN")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=selected_address,
                    data={CONF_UPRN: uprn},
                )

        return self.async_show_form(
            step_id="address",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): vol.In(list(address_map.keys())),
            }),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error raised when we cannot connect to an API."""

class NoAddressesFound(HomeAssistantError):
    """Error raised when the postcode returns no addresses."""

class NoBinsFound(HomeAssistantError):
    """Error raised when the UPRN has no bin collection data."""