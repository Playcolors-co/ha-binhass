"""The UK Bin Collection (BinHass) integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ADDRESS_ID,
    CONF_COUNCIL,
    CONF_QUERY,
    CONF_UPRN,
    DOMAIN,
)
from .coordinator import BinHassCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

type BinHassConfigEntry = ConfigEntry[BinHassCoordinator]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate v1 (Waltham-Forest-only) entries to the v2 council model."""
    if entry.version == 1:
        data = dict(entry.data)
        data.setdefault(CONF_COUNCIL, "waltham_forest")
        # v1 stored the UPRN under "uprn"; v2 uses a generic address id.
        if CONF_ADDRESS_ID not in data and CONF_UPRN in data:
            data[CONF_ADDRESS_ID] = data[CONF_UPRN]
        data.setdefault(CONF_QUERY, data.get("postcode", ""))
        new_unique = f"{data[CONF_COUNCIL]}:{data.get(CONF_ADDRESS_ID, '')}"
        hass.config_entries.async_update_entry(
            entry, data=data, unique_id=new_unique, version=2
        )
        _LOGGER.info("Migrated %s to v2 (council=%s)", entry.title, data[CONF_COUNCIL])
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BinHassConfigEntry) -> bool:
    """Set up BinHass from a config entry."""
    coordinator = BinHassCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BinHassConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
