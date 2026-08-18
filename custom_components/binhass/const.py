"""Constants for the Waltham Forest Bin Collection (BinHass) integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "binhass"

# Config entry keys
CONF_UPRN = "uprn"
CONF_POSTCODE = "postcode"
CONF_ADDRESS = "address"

# How often to refresh collection dates. Collections move rarely, a couple of
# times a day is plenty and keeps us gentle on the council portal.
DEFAULT_SCAN_INTERVAL = timedelta(hours=12)

# Waltham Forest AchieveForms / apibroker endpoints (see binhass-lookup memory).
BASE_URL = "https://portal.walthamforest.gov.uk"
SERVICE_NAME = "Find_My_Bin_Collection_Dates"

# apibroker lookup ids (reverse-engineered, verified live 2026-08-07).
LOOKUP_ADDRESS = "5694fd42a5541"  # postcode -> address list (overview_uprn/display)
LOOKUP_COLLECTIONS = "5e208cda0d0a0"  # UPRN -> site collections with NextCollectionDate

# Field name the collections lookup binds its SQL against.
FIELD_INPUT_UPRN = "inputUPRN"
FIELD_POSTCODE_SEARCH = "postcode_search"

# Browser headers required to get past the portal WAF. curl-equivalent is enough,
# no TLS/JA3 fingerprinting in play.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE_URL}/fillform/?iframe_id=fillform-frame-1&db_id=",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json",
}

# Map the raw Whitespace ServiceName to a friendly slug/name/icon for entities.
# Unknown services fall back to a slug derived from the ServiceName.
SERVICE_MAP: dict[str, dict[str, str]] = {
    "Domestic Waste Collection Service": {
        "key": "refuse",
        "name": "Refuse",
        "icon": "mdi:trash-can",
    },
    "Recycling Collection Service": {
        "key": "recycling",
        "name": "Recycling",
        "icon": "mdi:recycle",
    },
    "Food Waste Collection Service": {
        "key": "food",
        "name": "Food Waste",
        "icon": "mdi:food-apple",
    },
    "Garden Waste Collection Service": {
        "key": "garden",
        "name": "Garden Waste",
        "icon": "mdi:leaf",
    },
}
