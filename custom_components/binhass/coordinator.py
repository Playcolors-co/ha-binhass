"""Data update coordinator for BinHass."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Collection, WalthamForestError, WalthamForestClient
from .const import CONF_UPRN, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BinHassCoordinator(DataUpdateCoordinator[list[Collection]]):
    """Fetch bin collection dates for a single UPRN."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_UPRN]}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self._uprn = entry.data[CONF_UPRN]
        self._client = WalthamForestClient(async_create_clientsession(hass))

    async def _async_update_data(self) -> list[Collection]:
        today = dt_util.now().date()
        try:
            return await self._client.async_get_collections(self._uprn, today)
        except WalthamForestError as err:
            raise UpdateFailed(str(err)) from err
