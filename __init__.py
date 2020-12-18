import requests
import json
from datetime import datetime, timezone

"""
The "york_bins" custom component.
Configuration:
To use the yorkbins component you will need to add the following to your
configuration.yaml file.
york_bins:
"""

# The domain of your component. Should be equal to the name of your component.
DOMAIN = "york_bins"
ATTR_ID_NAME = "property_id"
DEFAULT_ID = "None"


def timestamp_from_api_response(resp):
    try:
        time = datetime.fromisoformat(resp)
        return time.strftime('%d/%m/%Y')
    except:
        return "ERROR (converting time)"


def days_until_collection(resp):
    try:
        time = datetime.fromisoformat(resp)
        time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        diff = time - now
        return diff.days + 1
    except:
        return "ERROR (calc days)"


def get_from_json(obj, key, default="N/F"):
    try:
        return obj[key]
    except:
        return default


def setup(hass, config):
    def handle_get(call):
        """Handle the service call."""
        property_id = call.data.get(ATTR_ID_NAME, DEFAULT_ID)

        endpoint = "https://cyc-myaccount-live.azurewebsites.net/api/bins/GetCollectionDetails/" + str(property_id)
        ##endpoint = "https://doitonline.york.gov.uk/BinsApi/EXOR/getWasteCollectionDatabyUprn?uprn=" + str(property_id)

        result = requests.request('GET', endpoint)

        hass.states.set(DOMAIN + ".last_request", str(datetime.now()))

        if result.status_code != 200:
            print("Error making get request")
            hass.states.set(DOMAIN + ".last_result", "Web Error (" + str(result.status_code) + ")")
        else:
            json_response = json.loads(result.content)['services']
            bins = len(json_response)

            if bins > 0:
                hass.states.set(DOMAIN + ".last_result", str(bins) + " bins found.")
            else:
                hass.states.set(DOMAIN + ".last_result", "No Bins Found")

            for bin in json_response:
                waste_type = str(bin['service'].lower().replace(" ", "_").replace("/", "_"))
                entity_domain = DOMAIN + "." + waste_type

                days_until = days_until_collection(bin['nextCollection'])

                hass.states.set(entity_domain, str(days_until) + " Day(s)", {
                    "desc": get_from_json(bin, 'binDescription'),
                    "last_collection": timestamp_from_api_response(bin['lastCollected']),
                    "next_collection": timestamp_from_api_response(bin['nextCollection']),
                    "collection_in_days": days_until,
                    "frequency": get_from_json(bin, 'frequency'),
                    "waste_type": get_from_json(bin, 'wasteType')
                })

    hass.services.register(DOMAIN, "get", handle_get)
    # Return boolean to indicate that initialization was successfully.
    return True