"""Firmstep / AchieveForms ``apibroker`` provider (pure HTTP).

Many UK councils publish bin dates through a Firmstep/AchieveForms form. Instead
of driving the form with a browser, we call the same ``apibroker/runLookup``
endpoints directly. Per-council params:

    host                 e.g. "portal.walthamforest.gov.uk"
    service              service slug used for the session uri
    address_lookup_id    runLookup id: postcode -> address list
    collections_lookup_id runLookup id: UPRN -> collections
    uprn_field           form field the collections lookup binds (e.g. "inputUPRN")
    postcode_field       address-lookup input field (default "postcode_search")
"""

from __future__ import annotations

import json
import time
from datetime import date
from urllib.parse import quote

import aiohttp

from . import (
    Address,
    CannotConnect,
    Collection,
    NoAddressesFound,
    Provider,
    parse_date_loose,
    register,
    slugify,
)

_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Friendly names/icons for common (Whitespace-style) service names.
_SERVICE_MAP = {
    "domestic waste collection service": ("refuse", "Refuse", "mdi:trash-can"),
    "refuse collection service": ("refuse", "Refuse", "mdi:trash-can"),
    "recycling collection service": ("recycling", "Recycling", "mdi:recycle"),
    "food waste collection service": ("food", "Food Waste", "mdi:food-apple"),
    "garden waste collection service": ("garden", "Garden Waste", "mdi:leaf"),
}


def _headers(host: str) -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        ),
        "Referer": f"https://{host}/fillform/?iframe_id=fillform-frame-1&db_id=",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
    }


def _friendly(service_name: str) -> tuple[str, str, str]:
    mapped = _SERVICE_MAP.get(service_name.strip().lower())
    if mapped:
        return mapped
    key = slugify(service_name)
    name = service_name.replace(" Collection Service", "").strip() or service_name
    return key, name, "mdi:trash-can-outline"


class AchieveFormsProvider(Provider):
    supports_address_search = True

    async def _get_sid(self, session, host: str, service: str) -> str:
        uri = quote(f"https://{host}/service/{service}", safe="")
        url = (
            f"https://{host}/authapi/isauthenticated"
            f"?uri={uri}&hostname={host}&withCredentials=true"
        )
        try:
            async with session.get(url, headers=_headers(host), timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = json.loads(await resp.text(), strict=False)
        except (aiohttp.ClientError, json.JSONDecodeError) as err:
            raise CannotConnect(f"session failed: {err}") from err
        sid = data.get("auth-session")
        if not sid:
            raise CannotConnect("no session id returned")
        return sid

    async def _run_lookup(self, session, host, sid, lookup_id, field, value) -> list[dict]:
        ts = int(time.time() * 1000)
        url = (
            f"https://{host}/apibroker/runLookup"
            f"?id={lookup_id}&repeat_against=&noRetry=true&getOnlyTokens=undefined"
            f"&log_id=&app_name=AF-Renderer::Self&_={ts}&sid={sid}"
        )
        body = {"formValues": {"Section 1": {field: {"value": value}}}}
        try:
            async with session.post(
                url, headers=_headers(host), data=json.dumps(body), timeout=_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                payload = json.loads(await resp.text(), strict=False)
        except (aiohttp.ClientError, json.JSONDecodeError) as err:
            raise CannotConnect(f"lookup {lookup_id} failed: {err}") from err
        try:
            rows = payload["integration"]["transformed"]["rows_data"]
        except (KeyError, TypeError) as err:
            raise CannotConnect(f"unexpected lookup {lookup_id} response") from err
        if isinstance(rows, dict):
            return [rows[k] for k in rows]
        return rows if isinstance(rows, list) else []

    async def async_search_addresses(self, session, params, postcode) -> list[Address]:
        host = params["host"]
        sid = await self._get_sid(session, host, params["service"])
        rows = await self._run_lookup(
            session, host, sid, params["address_lookup_id"],
            params.get("postcode_field", "postcode_search"), postcode.strip(),
        )
        out: list[Address] = []
        for row in rows:
            uprn = str(row.get("overview_uprn") or row.get("name") or "").strip()
            disp = str(row.get("display") or "").strip()
            if uprn and disp:
                out.append(Address(id=uprn, display=disp))
        if not out:
            raise NoAddressesFound(f"no addresses for {postcode!r}")
        return out

    async def async_get_collections(self, session, params, config, today: date) -> list[Collection]:
        host = params["host"]
        uprn = str(config.get("address_id") or config.get("uprn"))
        sid = await self._get_sid(session, host, params["service"])
        rows = await self._run_lookup(
            session, host, sid, params["collections_lookup_id"],
            params.get("uprn_field", "inputUPRN"), uprn,
        )
        best: dict[str, Collection] = {}
        date_field = params.get("date_field", "NextCollectionDate")
        name_field = params.get("service_field", "ServiceName")
        round_field = params.get("round_field", "RoundSchedule")
        for row in rows:
            sname = str(row.get(name_field) or "").strip()
            if not sname:
                continue
            d = parse_date_loose(str(row.get(date_field) or ""), today)
            if d is None:
                continue
            key, name, icon = _friendly(sname)
            existing = best.get(key)
            if existing is None or d < existing.collection_date:
                best[key] = Collection(
                    service_name=sname, key=key, name=name, icon=icon,
                    collection_date=d, round_schedule=str(row.get(round_field) or "").strip(),
                )
        return sorted(best.values(), key=lambda c: (c.collection_date, c.name))


register("achieveforms", AchieveFormsProvider())
