"""Config flow: pick council -> search address -> save."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    CONF_ADDRESS,
    CONF_ADDRESS_ID,
    CONF_COUNCIL,
    CONF_QUERY,
    DOMAIN,
)
from .councils import COUNCILS, council_options
from .providers import Address, CannotConnect, NoAddressesFound, get_provider

_LOGGER = logging.getLogger(__name__)


class BinHassConfigFlow(ConfigFlow, domain=DOMAIN):
    """council -> address search -> pick address."""

    VERSION = 2

    def __init__(self) -> None:
        self._council: str = ""
        self._query: str = ""
        self._addresses: list[Address] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._council = user_input[CONF_COUNCIL]
            return await self.async_step_search()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_COUNCIL): vol.In(council_options())}),
        )

    async def async_step_search(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        council = COUNCILS[self._council]
        hint = council.get("search_hint", "postcode")

        if user_input is not None:
            self._query = user_input[CONF_QUERY].strip()
            provider = get_provider(council["provider"])
            session = async_create_clientsession(self.hass)
            try:
                self._addresses = await provider.async_search_addresses(
                    session, council["params"], self._query
                )
            except NoAddressesFound:
                errors["base"] = "no_addresses"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Address search failed")
                errors["base"] = "unknown"
            else:
                return await self.async_step_address()

        prompt = "postcode" if hint == "postcode" else "address"
        return self.async_show_form(
            step_id="search",
            data_schema=vol.Schema({vol.Required(CONF_QUERY): str}),
            description_placeholders={"hint": prompt, "council": council["name"]},
            errors=errors,
        )

    async def async_step_address(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        council = COUNCILS[self._council]

        if user_input is not None:
            address_id = user_input[CONF_ADDRESS_ID]
            display = next(
                (a.display for a in self._addresses if a.id == address_id), address_id
            )
            await self.async_set_unique_id(f"{self._council}:{address_id}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"{council['name']} — {display}",
                data={
                    CONF_COUNCIL: self._council,
                    CONF_ADDRESS_ID: address_id,
                    CONF_ADDRESS: display,
                    CONF_QUERY: self._query,
                },
            )

        options = {a.id: a.display for a in self._addresses}
        return self.async_show_form(
            step_id="address",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS_ID): vol.In(options)}),
        )
