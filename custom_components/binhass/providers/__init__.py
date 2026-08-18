"""Provider framework for BinHass (UK-wide bin collections).

A *provider* implements one council backend platform (e.g. Firmstep/AchieveForms,
Recollect, Whitespace, Bartec) as clean async HTTP. A *council* in ``councils.py``
maps to a provider plus per-council parameters (endpoints, lookup ids, fields).

Council recipes are informed by the MIT-licensed project
`robbrad/UKBinCollectionData <https://github.com/robbrad/UKBinCollectionData>`_.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

_LOGGER = logging.getLogger(__name__)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


class BinHassError(Exception):
    """Base error for providers."""


class CannotConnect(BinHassError):
    """The council backend could not be reached or answered unexpectedly."""


class NoAddressesFound(BinHassError):
    """A postcode returned no addresses."""


@dataclass(frozen=True)
class Address:
    """A selectable address (its id is whatever the provider needs later)."""

    id: str  # UPRN / place id / whatever the provider keys on
    display: str


@dataclass(frozen=True)
class Collection:
    """A single service with its next collection and (if known) future dates.

    ``future_dates`` holds real upcoming dates when the backend provides a
    calendar (e.g. Recollect). When empty, dates beyond ``collection_date`` are
    estimated from ``round_schedule`` via :func:`upcoming_dates`.
    """

    service_name: str  # raw service name from the backend
    key: str           # stable slug, e.g. "refuse"
    name: str          # friendly name
    icon: str
    collection_date: date
    round_schedule: str = ""
    future_dates: tuple[date, ...] = ()


def slugify(text: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "_" for c in text)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "service"


def parse_date_loose(raw: str, today: date) -> date | None:
    """Parse a human date, with or without a year, into a real date.

    Handles 'Friday 14 August', '14/08/2026', '2026-08-14', '14 Aug 2026'.
    When the year is missing, picks the year that puts the date nearest today
    (ignoring candidates > 2 weeks in the past). Returns None if unparseable.
    """
    if not raw:
        return None
    text = raw.strip()
    if not text or text.lower() in ("nan", "none", "n/a"):
        return None

    # ISO / numeric first
    for sep in ("-", "/"):
        parts = text.split(sep)
        if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
            a, b, c = (int(p) for p in parts)
            try:
                if a > 31:  # YYYY-MM-DD
                    return date(a, b, c)
                return date(c, b, a)  # DD/MM/YYYY
            except ValueError:
                return None

    tokens = text.replace(",", " ").replace(" ", " ").split()
    day = month = year = None
    for tok in tokens:
        low = tok.lower().rstrip("stndrh")  # 14th -> 14
        base = tok.lower()
        if base in _MONTHS:
            month = _MONTHS[base]
        elif low.isdigit():
            v = int(low)
            if v > 31:
                year = v
            elif day is None:
                day = v
    if day is None or month is None:
        _LOGGER.debug("Could not parse date from %r", raw)
        return None
    if year is not None:
        try:
            return date(year, month, day)
        except ValueError:
            return None

    best: date | None = None
    for y in (today.year - 1, today.year, today.year + 1):
        try:
            cand = date(y, month, day)
        except ValueError:
            continue
        if (cand - today).days < -14:
            continue
        if best is None or abs((cand - today).days) < abs((best - today).days):
            best = cand
    return best


def schedule_interval_days(round_schedule: str) -> int:
    """Best-effort cadence in days from a round-schedule string."""
    s = (round_schedule or "").lower()
    if "fort" in s:
        return 14
    if "month" in s:
        return 28
    return 7


def project_upcoming(collection: Collection, until: date, max_count: int = 26) -> list[date]:
    """Estimate dates from the next confirmed one to ``until`` using the cadence."""
    step = timedelta(days=schedule_interval_days(collection.round_schedule))
    out: list[date] = []
    cur = collection.collection_date
    while cur <= until and len(out) < max_count:
        out.append(cur)
        cur = cur + step
    return out


def upcoming_dates(collection: Collection, until: date, max_count: int = 26) -> list[date]:
    """Upcoming dates: real ones if the backend gave a calendar, else estimated.

    Returns the second element of a tuple telling the caller whether the result
    is estimated, so the UI can flag it.
    """
    if collection.future_dates:
        return [d for d in collection.future_dates if d <= until][:max_count]
    return project_upcoming(collection, until, max_count)


def is_estimated(collection: Collection) -> bool:
    """True when dates beyond the next are estimated (no real calendar)."""
    return not collection.future_dates


class Provider:
    """Base class for council backend providers."""

    #: whether this provider offers a postcode -> address picker in the flow
    supports_address_search: bool = True

    async def async_search_addresses(self, session, params: dict, postcode: str) -> list[Address]:
        """Return selectable addresses for a postcode. Override if supported."""
        raise NotImplementedError

    async def async_get_collections(
        self, session, params: dict, config: dict, today: date
    ) -> list[Collection]:
        """Return the next collection per service for the configured address."""
        raise NotImplementedError


# Registry populated by provider modules importing and calling register().
_REGISTRY: dict[str, Provider] = {}


def register(name: str, provider: Provider) -> None:
    _REGISTRY[name] = provider


def get_provider(name: str) -> Provider:
    from . import achieveforms, recollect  # noqa: F401  register providers

    if name not in _REGISTRY:
        raise BinHassError(f"Unknown provider {name!r}")
    return _REGISTRY[name]
