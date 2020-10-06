import requests
import json
from datetime import datetime

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
        epoch = int(resp[6:-2]) / 1000
        time = datetime.fromtimestamp(epoch)
        return time.strftime('%d/%m/%Y')
    except:
        return "ERROR (converting time)"


def days_until_collection(resp):
    try:
        epoch = int(resp[6:-2]) / 1000
        time = datetime.fromtimestamp(epoch)
        now = datetime.now()

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

        endpoint = "https://doitonline.york.gov.uk/BinsApi/EXOR/getWasteCollectionDatabyUprn?uprn=" + str(property_id)

        result = requests.request('GET', endpoint)

        hass.states.set(DOMAIN + ".last_request", str(datetime.now()))

        if result.status_code != 200:
            print("Error making get request")
            hass.states.set(DOMAIN + ".last_result", "Web Error (" + str(result.status_code) + ")")
        else:
            json_response = json.loads(result.content)
            bins = len(json_response)

            if bins > 0:
                hass.states.set(DOMAIN + ".last_result", str(bins) + " bins found.")
                hass.states.set(DOMAIN + ".short_address", json_response[0]['ShortAddress'])
            else:
                hass.states.set(DOMAIN + ".last_result", "No Bins Found")

            for bin in json_response:
                waste_type = str(bin['WasteType'].lower().replace(" ", "_").replace("/", "_"))
                entity_domain = DOMAIN + "." + waste_type

                collection_available = get_from_json(bin, 'CollectionAvailable')

                if collection_available == "Y":
                    collection_available = "available"
                else:
                    collection_available = "not_available"

                hass.states.set(entity_domain, collection_available, {
                    "desc": get_from_json(bin, 'WasteTypeDescription'),
                    "last_collection": timestamp_from_api_response(bin['LastCollection']),
                    "next_collection": timestamp_from_api_response(bin['NextCollection']),
                    "collection_in_days": days_until_collection(bin['NextCollection']),
                    "collection_day": get_from_json(bin, 'CollectionDay'),
                    "collection_day_full": get_from_json(bin, 'CollectionDayFull'),
                    "type": get_from_json(bin, 'BinType'),
                    "type_desc": get_from_json(bin, 'BinTypeDescription'),
                    "materials": get_from_json(bin, 'MaterialsCollected'),
                    "provider": get_from_json(bin, 'Provider'),
                    "image": get_from_json(bin, 'ImageName'),
                    "collection_point": get_from_json(bin, 'CollectionPoint'),
                    "collection_point_desc": get_from_json(bin, 'CollectionPointDescription'),
                    "number_of_bins": get_from_json(bin, 'NumberOfBins')
                })


    hass.services.register(DOMAIN, "get", handle_get)
    # Return boolean to indicate that initialization was successfully.
    return True