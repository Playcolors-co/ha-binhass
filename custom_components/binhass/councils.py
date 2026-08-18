"""Catalog of supported councils.

Each entry maps a council id to a provider and its per-council parameters. Adding
a council is data, not code. Recipes for the Recollect councils are derived from
the MIT-licensed robbrad/UKBinCollectionData project.

``search_hint`` tells the config flow what to ask for:
  - "postcode"  -> the user types their postcode (AchieveForms address lookup)
  - "address"   -> the user types their street/address (Recollect suggest)
"""

from __future__ import annotations

COUNCILS: dict[str, dict] = {
    "waltham_forest": {
        "name": "Waltham Forest",
        "provider": "achieveforms",
        "search_hint": "postcode",
        "params": {
            "host": "portal.walthamforest.gov.uk",
            "service": "Find_My_Bin_Collection_Dates",
            "address_lookup_id": "5694fd42a5541",
            "collections_lookup_id": "5e208cda0d0a0",
            "uprn_field": "inputUPRN",
        },
    },
    "newcastle_upon_tyne": {
        "name": "Newcastle upon Tyne",
        "provider": "recollect",
        "search_hint": "address",
        "params": {"area": "NewcastleUponTyneUK", "service": "50007"},
    },
    "bassetlaw": {
        "name": "Bassetlaw",
        "provider": "recollect",
        "search_hint": "address",
        "params": {"area": "BassetlawUK", "service": "50015"},
    },
    "caerphilly": {
        "name": "Caerphilly County Borough",
        "provider": "recollect",
        "search_hint": "address",
        "params": {"area": "CaerphillyCountyUK", "service": "50008"},
    },
    "east_ayrshire": {
        "name": "East Ayrshire",
        "provider": "recollect",
        "search_hint": "address",
        "params": {"area": "EastAyrshireUK", "service": "50014"},
    },
}


def council_options() -> dict[str, str]:
    """Return {id: name} sorted by name for the config-flow selector."""
    return {
        cid: c["name"]
        for cid, c in sorted(COUNCILS.items(), key=lambda kv: kv[1]["name"])
    }
