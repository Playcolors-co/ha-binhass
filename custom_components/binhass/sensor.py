"""Sensor platform for BinHass: one sensor per bin service."""

from __future__ import annotations

from datetime import date, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import BinHassConfigEntry
from .api import Collection, project_upcoming
from .const import CONF_ADDRESS, CONF_UPRN, DOMAIN
from .coordinator import BinHassCoordinator

# How many upcoming (projected) dates to expose as an attribute.
UPCOMING_COUNT = 6


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BinHassConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one sensor per collected service found for this address."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new_services() -> None:
        new_entities: list[BinCollectionSensor] = []
        for collection in coordinator.data or []:
            if collection.key not in known:
                known.add(collection.key)
                new_entities.append(BinCollectionSensor(coordinator, entry, collection))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_services()
    # Catch services that only appear on a later refresh.
    entry.async_on_unload(coordinator.async_add_listener(_add_new_services))


class BinCollectionSensor(CoordinatorEntity[BinHassCoordinator], SensorEntity):
    """Next collection date for a single bin service."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(
        self,
        coordinator: BinHassCoordinator,
        entry: BinHassConfigEntry,
        collection: Collection,
    ) -> None:
        super().__init__(coordinator)
        self._key = collection.key
        self._attr_name = collection.name
        self._attr_icon = collection.icon
        self._attr_unique_id = f"{entry.data[CONF_UPRN]}_{collection.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_UPRN])},
            name=f"Bins — {entry.data.get(CONF_ADDRESS, entry.data[CONF_UPRN])}",
            manufacturer="Waltham Forest",
            model="Bin Collection",
        )

    @property
    def _collection(self) -> Collection | None:
        for collection in self.coordinator.data or []:
            if collection.key == self._key:
                return collection
        return None

    @property
    def native_value(self) -> date | None:
        collection = self._collection
        return collection.collection_date if collection else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        collection = self._collection
        if collection is None:
            return {}
        today = dt_util.now().date()
        days_until = (collection.collection_date - today).days
        # Project a handful of future dates. Only the first is authoritative;
        # the rest are computed from the round frequency (see project_upcoming).
        horizon = today + timedelta(days=90)
        upcoming = project_upcoming(collection, horizon, max_count=UPCOMING_COUNT)
        return {
            "service_name": collection.service_name,
            "round_schedule": collection.round_schedule,
            "days_until": days_until,
            "upcoming": [d.isoformat() for d in upcoming],
            "upcoming_estimated": len(upcoming) > 1,
        }
