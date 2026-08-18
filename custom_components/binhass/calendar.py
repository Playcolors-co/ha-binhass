"""Calendar platform: upcoming collections as calendar events."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import BinHassConfigEntry
from .const import CONF_ADDRESS_ID, CONF_COUNCIL, DOMAIN
from .coordinator import BinHassCoordinator
from .providers import upcoming_dates

_MAX_HORIZON = timedelta(days=365)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BinHassConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([BinHassCalendar(entry.runtime_data, entry)])


class BinHassCalendar(CoordinatorEntity[BinHassCoordinator], CalendarEntity):
    _attr_has_entity_name = True
    _attr_name = "Collections"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator, entry: BinHassConfigEntry) -> None:
        super().__init__(coordinator)
        uid = entry.unique_id or f"{entry.data[CONF_COUNCIL]}:{entry.data[CONF_ADDRESS_ID]}"
        self._attr_unique_id = f"{uid}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=entry.title,
            manufacturer="BinHass",
            model="UK Bin Collection",
        )

    def _events(self, start: date, end: date) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        for c in self.coordinator.data or []:
            for day in upcoming_dates(c, end):
                if day < start:
                    continue
                events.append(
                    CalendarEvent(summary=c.name, start=day, end=day + timedelta(days=1))
                )
        events.sort(key=lambda e: (e.start, e.summary))
        return events

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        events = self._events(today, today + _MAX_HORIZON)
        return events[0] if events else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        today = dt_util.now().date()
        end = min(end_date.date(), today + _MAX_HORIZON)
        return self._events(start_date.date(), end)
