"""Constants for the UK Bin Collection (BinHass) integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "binhass"

# Config entry keys
CONF_COUNCIL = "council"
CONF_ADDRESS_ID = "address_id"  # UPRN / Recollect place id / provider-specific
CONF_ADDRESS = "address"
CONF_QUERY = "query"  # postcode or address text the user searched with

# Legacy key (v1 entries stored the UPRN under "uprn").
CONF_UPRN = "uprn"

DEFAULT_SCAN_INTERVAL = timedelta(hours=12)
