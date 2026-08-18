"""Recollect provider (api.eu.recollect.net) — clean JSON API.

Recollect returns a real calendar of events, so we get actual future dates
(no estimation needed). Per-council params:

    area       e.g. "NewcastleUponTyneUK"
    service    e.g. "50007"
"""

from __future__ import annotations

from datetime import date, timedelta

import aiohttp

from . import (
    Address,
    CannotConnect,
    Collection,
    NoAddressesFound,
    Provider,
    register,
    slugify,
)

_TIMEOUT = aiohttp.ClientTimeout(total=30)
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_BASE = "https://api.eu.recollect.net/api"

_ICONS = {
    "refuse": "mdi:trash-can", "rubbish": "mdi:trash-can", "general": "mdi:trash-can",
    "recycl": "mdi:recycle", "garden": "mdi:leaf", "food": "mdi:food-apple",
    "glass": "mdi:glass-fragile", "paper": "mdi:newspaper", "card": "mdi:package-variant",
}


def _icon_for(name: str) -> str:
    low = name.lower()
    for token, icon in _ICONS.items():
        if token in low:
            return icon
    return "mdi:trash-can-outline"


class RecollectProvider(Provider):
    supports_address_search = True

    async def async_search_addresses(self, session, params, postcode) -> list[Address]:
        area, service = params["area"], params["service"]
        url = f"{_BASE}/areas/{area}/services/{service}/address-suggest"
        try:
            async with session.get(
                url, headers=_HEADERS,
                params={"q": postcode.strip(), "locale": "en-GB"}, timeout=_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                results = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise CannotConnect(f"address-suggest failed: {err}") from err

        out: list[Address] = []
        for r in results or []:
            if r.get("type") == "parcel" and r.get("place_id"):
                disp = str(r.get("name") or r.get("label") or r.get("place_id"))
                out.append(Address(id=str(r["place_id"]), display=disp))
        if not out:
            raise NoAddressesFound(f"no addresses for {postcode!r}")
        return out

    async def async_get_collections(self, session, params, config, today: date) -> list[Collection]:
        service = params["service"]
        place_id = str(config.get("address_id") or config.get("uprn"))
        url = f"{_BASE}/places/{place_id}/services/{service}/events"
        query = {
            "nomerge": "1", "hide": "reminder_only",
            "after": today.strftime("%Y-%m-%d"),
            "before": (today + timedelta(days=90)).strftime("%Y-%m-%d"),
            "locale": "en-GB",
        }
        try:
            async with session.get(url, headers=_HEADERS, params=query, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise CannotConnect(f"events failed: {err}") from err

        # Gather all pickup dates per bin type.
        dates_by_key: dict[str, dict] = {}
        for event in data.get("events", []):
            day = event.get("day")
            if not day:
                continue
            try:
                d = date.fromisoformat(day)
            except ValueError:
                continue
            if d < today:
                continue
            for flag in event.get("flags", []):
                if flag.get("event_type") != "pickup":
                    continue
                name = str(flag.get("subject") or flag.get("name") or "Collection").strip()
                key = slugify(name)
                bucket = dates_by_key.setdefault(key, {"name": name, "dates": set()})
                bucket["dates"].add(d)

        out: list[Collection] = []
        for key, info in dates_by_key.items():
            future = sorted(info["dates"])
            if not future:
                continue
            out.append(Collection(
                service_name=info["name"], key=key, name=info["name"],
                icon=_icon_for(info["name"]), collection_date=future[0],
                future_dates=tuple(future),
            ))
        return sorted(out, key=lambda c: (c.collection_date, c.name))


register("recollect", RecollectProvider())
