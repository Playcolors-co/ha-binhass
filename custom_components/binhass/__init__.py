"""The Waltham Forest Bin Collection (BinHass) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BinHassCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CALENDAR]

type BinHassConfigEntry = ConfigEntry[BinHassCoordinator]


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
