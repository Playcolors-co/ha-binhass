"""HTTP client for the Waltham Forest 'Find My Bin Collection Dates' portal.

The council exposes no official API. This talks to the same Firmstep/AchieveForms
``apibroker/runLookup`` endpoints the public form uses. Flow:

1. GET ``authapi/isauthenticated`` -> session id (SID) + cookies.
2. POST ``apibroker/runLookup?id=<lookup>&...&sid=<SID>`` with the form values.

See the ``binhass-lookup-risolto`` project note for the full reverse-engineering.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote

import aiohttp

from .const import (
    BASE_URL,
    BROWSER_HEADERS,
    FIELD_INPUT_UPRN,
    FIELD_POSTCODE_SEARCH,
    LOOKUP_ADDRESS,
    LOOKUP_COLLECTIONS,
    SERVICE_MAP,
    SERVICE_NAME,
)

_LOGGER = logging.getLogger(__name__)

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class WalthamForestError(Exception):
    """Base error for the Waltham Forest client."""


class CannotConnect(WalthamForestError):
    """Raised when the portal cannot be reached or answers unexpectedly."""


class NoAddressesFound(WalthamForestError):
    """Raised when a postcode returns no addresses."""


@dataclass(frozen=True)
class Address:
    """A single selectable address returned for a postcode."""

    uprn: str
    display: str


@dataclass(frozen=True)
class Collection:
    """A single upcoming bin collection."""

    service_name: str  # raw Whitespace ServiceName
    key: str  # stable slug, e.g. "refuse"
    name: str  # friendly name, e.g. "Refuse"
    icon: str
    collection_date: date
    round_schedule: str


def _slugify_service(service_name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "_" for c in service_name)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "service"


def parse_collection_date(raw: str, today: date) -> date | None:
    """Parse a portal date like 'Friday 14 August' into a real date.

    The portal omits the year, so we pick the year that puts the date nearest to
    (but not unreasonably before) today. Returns None for empty / 'NaN' values.
    """
    if not raw:
        return None
    text = raw.strip()
    if not text or text.lower() == "nan":
        return None

    tokens = text.replace(",", " ").split()
    day: int | None = None
    month: int | None = None
    for tok in tokens:
        low = tok.lower()
        if low in _MONTHS:
            month = _MONTHS[low]
        elif tok.isdigit():
            day = int(tok)
    if day is None or month is None:
        _LOGGER.debug("Could not parse collection date from %r", raw)
        return None

    best: date | None = None
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        delta = (candidate - today).days
        # Ignore dates more than ~2 weeks in the past (wrong-year candidates).
        if delta < -14:
            continue
        if best is None or abs(delta) < abs((best - today).days):
            best = candidate
    return best


class WalthamForestClient:
    """Small async client around the Waltham Forest apibroker lookups."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get_sid(self) -> str:
        service_url = f"{BASE_URL}/service/{SERVICE_NAME}"
        uri = quote(service_url, safe="")
        url = (
            f"{BASE_URL}/authapi/isauthenticated"
            f"?uri={uri}&hostname=portal.walthamforest.gov.uk&withCredentials=true"
        )
        try:
            async with self._session.get(
                url, headers=BROWSER_HEADERS, timeout=_REQUEST_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                data = json.loads(await resp.text(), strict=False)
        except (aiohttp.ClientError, json.JSONDecodeError) as err:
            raise CannotConnect(f"Could not obtain session: {err}") from err

        sid = data.get("auth-session")
        if not sid:
            raise CannotConnect("Portal did not return a session id")
        return sid

    async def _run_lookup(self, sid: str, lookup_id: str, field: str, value: str) -> list[dict]:
        ts = int(time.time() * 1000)
        url = (
            f"{BASE_URL}/apibroker/runLookup"
            f"?id={lookup_id}&repeat_against=&noRetry=true&getOnlyTokens=undefined"
            f"&log_id=&app_name=AF-Renderer::Self&_={ts}&sid={sid}"
        )
        body = {"formValues": {"Section 1": {field: {"value": value}}}}
        try:
            async with self._session.post(
                url,
                headers=BROWSER_HEADERS,
                data=json.dumps(body),
                timeout=_REQUEST_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                # The portal streams raw control chars in the JSON -> strict=False.
                payload = json.loads(await resp.text(), strict=False)
        except (aiohttp.ClientError, json.JSONDecodeError) as err:
            raise CannotConnect(f"Lookup {lookup_id} failed: {err}") from err

        try:
            rows = payload["integration"]["transformed"]["rows_data"]
        except (KeyError, TypeError) as err:
            raise CannotConnect(f"Unexpected lookup {lookup_id} response") from err

        if isinstance(rows, dict):
            return [rows[k] for k in rows]
        if isinstance(rows, list):
            return rows
        return []

    async def async_get_addresses(self, postcode: str) -> list[Address]:
        """Return the selectable addresses for a postcode."""
        sid = await self._get_sid()
        rows = await self._run_lookup(
            sid, LOOKUP_ADDRESS, FIELD_POSTCODE_SEARCH, postcode.strip()
        )
        addresses: list[Address] = []
        for row in rows:
            uprn = str(row.get("overview_uprn") or row.get("name") or "").strip()
            display = str(row.get("display") or "").strip()
            if uprn and display:
                addresses.append(Address(uprn=uprn, display=display))
        if not addresses:
            raise NoAddressesFound(f"No addresses for postcode {postcode!r}")
        return addresses

    async def async_get_collections(self, uprn: str, today: date) -> list[Collection]:
        """Return the next collection per service for a UPRN.

        The lookup returns several rows per service (active + historic/blocked).
        We keep the soonest valid future date per service.
        """
        sid = await self._get_sid()
        rows = await self._run_lookup(sid, LOOKUP_COLLECTIONS, FIELD_INPUT_UPRN, str(uprn))

        best: dict[str, Collection] = {}
        for row in rows:
            service_name = str(row.get("ServiceName") or "").strip()
            if not service_name:
                continue
            parsed = parse_collection_date(str(row.get("NextCollectionDate") or ""), today)
            if parsed is None:
                continue
            mapped = SERVICE_MAP.get(service_name)
            if mapped:
                key, name, icon = mapped["key"], mapped["name"], mapped["icon"]
            else:
                key = _slugify_service(service_name)
                name = service_name.replace(" Collection Service", "").strip()
                icon = "mdi:trash-can-outline"
            existing = best.get(key)
            if existing is None or parsed < existing.collection_date:
                best[key] = Collection(
                    service_name=service_name,
                    key=key,
                    name=name,
                    icon=icon,
                    collection_date=parsed,
                    round_schedule=str(row.get("RoundSchedule") or "").strip(),
                )

        return sorted(best.values(), key=lambda c: (c.collection_date, c.name))
