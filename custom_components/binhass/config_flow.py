"""Config flow for the Waltham Forest Bin Collection (BinHass) integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import Address, CannotConnect, NoAddressesFound, WalthamForestClient
from .const import CONF_ADDRESS, CONF_POSTCODE, CONF_UPRN, DOMAIN

_LOGGER = logging.getLogger(__name__)

# UK postcode, loose validation (space optional).
_POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE)


class BinHassConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the BinHass config flow: postcode -> address -> UPRN."""

    VERSION = 1

    def __init__(self) -> None:
        self._postcode: str = ""
        self._addresses: list[Address] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step: ask for a postcode and look up its addresses."""
        errors: dict[str, str] = {}

        if user_input is not None:
            postcode = user_input[CONF_POSTCODE].strip().upper()
            if not _POSTCODE_RE.match(postcode):
                errors["base"] = "invalid_postcode"
            else:
                session = async_create_clientsession(self.hass)
                client = WalthamForestClient(session)
                try:
                    self._addresses = await client.async_get_addresses(postcode)
                except NoAddressesFound:
                    errors["base"] = "no_addresses"
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception:  # noqa: BLE001 - surface as generic error
                    _LOGGER.exception("Unexpected error looking up postcode")
                    errors["base"] = "unknown"
                else:
                    self._postcode = postcode
                    return await self.async_step_address()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_POSTCODE): str}),
            errors=errors,
        )

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Second step: pick the address from the list; store its UPRN."""
        if user_input is not None:
            uprn = user_input[CONF_UPRN]
            display = next(
                (a.display for a in self._addresses if a.uprn == uprn), uprn
            )

            await self.async_set_unique_id(uprn)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=display,
                data={
                    CONF_UPRN: uprn,
                    CONF_ADDRESS: display,
                    CONF_POSTCODE: self._postcode,
                },
            )

        options = {a.uprn: a.display for a in self._addresses}
        return self.async_show_form(
            step_id="address",
            data_schema=vol.Schema({vol.Required(CONF_UPRN): vol.In(options)}),
        )
