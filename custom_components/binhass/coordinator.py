"""Data update coordinator for BinHass."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import CONF_COUNCIL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .councils import COUNCILS
from .providers import BinHassError, Collection, get_provider


_LOGGER = logging.getLogger(__name__)


class BinHassCoordinator(DataUpdateCoordinator[list[Collection]]):
    """Fetch collections for one configured address via its council's provider."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        council_id = entry.data[CONF_COUNCIL]
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{council_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self._council = COUNCILS[council_id]
        self._provider = get_provider(self._council["provider"])
        self._session = async_create_clientsession(hass)

    async def _async_update_data(self) -> list[Collection]:
        today = dt_util.now().date()
        try:
            return await self._provider.async_get_collections(
                self._session, self._council["params"], dict(self.entry.data), today
            )
        except BinHassError as err:
            raise UpdateFailed(str(err)) from err
