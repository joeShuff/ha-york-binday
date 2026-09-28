"""Constants for the City of York Bins integration."""

DOMAIN = "york_bins"
CONF_UPRN = "uprn"
DEFAULT_SCAN_INTERVAL_HOURS = 24

API_ENDPOINT = (
    "https://waste-api.york.gov.uk/api/Collections/GetBinCollectionDataForUprn/{uprn}"
)

CALENDAR_API_ENDPOINT = (
    "https://waste-api.york.gov.uk/api/Collections/GetBinCalendarDataForUprn/{uprn}"
)

# Home Assistant calendar events have no colour field, so each round type gets
# a coloured emoji marker in the event title instead.
ROUND_TYPE_MARKERS: dict[str, str] = {
    "REFUSE": "⚫",
    "RECYCLING": "🔵",
    "GARDEN": "🟢",
}
ROUND_TYPE_NAMES: dict[str, str] = {
    "REFUSE": "Refuse",
    "RECYCLING": "Recycling",
    "GARDEN": "Garden",
}