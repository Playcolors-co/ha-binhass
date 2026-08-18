"""Sensor platform: one sensor per bin service."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import BinHassConfigEntry
from .const import CONF_ADDRESS_ID, CONF_COUNCIL, DOMAIN
from .coordinator import BinHassCoordinator
from .providers import Collection, is_estimated, upcoming_dates

UPCOMING_COUNT = 6


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BinHassConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = []
        for collection in coordinator.data or []:
            if collection.key not in known:
                known.add(collection.key)
                new.append(BinCollectionSensor(coordinator, entry, collection))
        if new:
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


def _device_info(entry: BinHassConfigEntry) -> DeviceInfo:
    uid = entry.unique_id or f"{entry.data[CONF_COUNCIL]}:{entry.data[CONF_ADDRESS_ID]}"
    return DeviceInfo(
        identifiers={(DOMAIN, uid)},
        name=entry.title,
        manufacturer="BinHass",
        model="UK Bin Collection",
    )


class BinCollectionSensor(CoordinatorEntity[BinHassCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator, entry: BinHassConfigEntry, collection: Collection) -> None:
        super().__init__(coordinator)
        self._key = collection.key
        self._attr_name = collection.name
        self._attr_icon = collection.icon
        uid = entry.unique_id or f"{entry.data[CONF_COUNCIL]}:{entry.data[CONF_ADDRESS_ID]}"
        self._attr_unique_id = f"{uid}_{collection.key}"
        self._attr_device_info = _device_info(entry)

    @property
    def _collection(self) -> Collection | None:
        for c in self.coordinator.data or []:
            if c.key == self._key:
                return c
        return None

    @property
    def native_value(self) -> date | None:
        c = self._collection
        return c.collection_date if c else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        c = self._collection
        if c is None:
            return {}
        today = dt_util.now().date()
        horizon = today + timedelta(days=90)
        upcoming = upcoming_dates(c, horizon, max_count=UPCOMING_COUNT)
        return {
            "service_name": c.service_name,
            "round_schedule": c.round_schedule,
            "days_until": (c.collection_date - today).days,
            "upcoming": [d.isoformat() for d in upcoming],
            "upcoming_estimated": is_estimated(c),
        }
