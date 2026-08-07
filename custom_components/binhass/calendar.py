"""Calendar platform for BinHass: upcoming collections as calendar events.

Gives a month-ahead view in the Home Assistant calendar. Only the next date per
service is authoritative (fetched from the council); later events are projected
from the round frequency and may not reflect bank-holiday shifts.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import BinHassConfigEntry
from .api import project_upcoming
from .const import CONF_ADDRESS, CONF_UPRN, DOMAIN
from .coordinator import BinHassCoordinator

# Upper bound for how far ahead we ever project (safety cap).
_MAX_HORIZON = timedelta(days=365)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BinHassConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a single collections calendar for this address."""
    async_add_entities([BinHassCalendar(entry.runtime_data, entry)])


class BinHassCalendar(CoordinatorEntity[BinHassCoordinator], CalendarEntity):
    """A calendar of upcoming bin collections for one address."""

    _attr_has_entity_name = True
    _attr_name = "Collections"
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self, coordinator: BinHassCoordinator, entry: BinHassConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data[CONF_UPRN]}_calendar"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_UPRN])},
            name=f"Bins — {entry.data.get(CONF_ADDRESS, entry.data[CONF_UPRN])}",
            manufacturer="Waltham Forest",
            model="Bin Collection",
        )

    def _build_events(self, start: date, end: date) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        for collection in self.coordinator.data or []:
            for day in project_upcoming(collection, end):
                if day < start:
                    continue
                events.append(
                    CalendarEvent(
                        summary=collection.name,
                        start=day,
                        end=day + timedelta(days=1),  # all-day, end exclusive
                    )
                )
        events.sort(key=lambda event: (event.start, event.summary))
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming collection event."""
        today = dt_util.now().date()
        events = self._build_events(today, today + _MAX_HORIZON)
        return events[0] if events else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return collection events within the requested window."""
        today = dt_util.now().date()
        end = min(end_date.date(), today + _MAX_HORIZON)
        return self._build_events(start_date.date(), end)
