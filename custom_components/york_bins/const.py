"""Constants for the City of York Bins integration."""

DOMAIN = "york_bins"
CONF_UPRN = "uprn"
DEFAULT_SCAN_INTERVAL_HOURS = 24

API_ENDPOINT = (
    "https://waste-api.york.gov.uk/api/Collections/GetBinCollectionDataForUprn/{uprn}"
)
