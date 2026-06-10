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

from .const import API_ENDPOINT, CONF_UPRN, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_UPRN): str,
    }
)


def validate_uprn(uprn: str) -> list[dict]:
    """Validate a UPRN by hitting the York API and return the services list."""
    url = API_ENDPOINT.format(uprn=uprn)
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout as err:
        raise CannotConnect("Timed out contacting the York Bins API") from err
    except requests.exceptions.RequestException as err:
        raise CannotConnect(f"Error contacting York Bins API: {err}") from err

    data = response.json()
    services = data.get("services", [])
    if not services:
        raise InvalidUPRN(f"No bin collections found for UPRN {uprn!r}")
    return services


async def async_validate_input(hass: HomeAssistant, uprn: str) -> dict[str, Any]:
    """Run validation in the executor so we don't block the event loop."""
    services = await hass.async_add_executor_job(validate_uprn, uprn)
    bin_count = len(services)
    return {"title": f"York Bins ({uprn})", "bin_count": bin_count}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for City of York Bins."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            uprn = user_input[CONF_UPRN].strip()

            # Prevent duplicate entries for the same UPRN.
            await self.async_set_unique_id(uprn)
            self._abort_if_unique_id_configured()

            try:
                info = await async_validate_input(self.hass, uprn)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidUPRN:
                errors[CONF_UPRN] = "invalid_uprn"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={CONF_UPRN: uprn},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "uprn_help": (
                    "To find your UPRN: go to the York Council bin collections page "
                    "(https://myaccount.york.gov.uk/bin-collections), open your browser's "
                    "developer tools and go to the Network tab. Search for your address and "
                    "select it from the dropdown — then look for a request to the waste-api "
                    "domain. Your UPRN will be visible in the file/URL column of that request."
                )
            },
        )


class CannotConnect(HomeAssistantError):
    """Error raised when we cannot connect to the API."""


class InvalidUPRN(HomeAssistantError):
    """Error raised when the UPRN returns no data."""