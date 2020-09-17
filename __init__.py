import requests
import json

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

def setup(hass, config):

    def handle_get(call):
        """Handle the service call."""
        property_id = call.data.get(ATTR_ID_NAME, DEFAULT_ID)

        endpoint = "https://doitonline.york.gov.uk/BinsApi/EXOR/getWasteCollectionDatabyUprn?uprn=" + str(property_id)

        result = requests.request('GET', endpoint)
        json_response = json.loads(result.content)

        hass.states.set("york_bins.next_date", )

    hass.services.register(DOMAIN, "get", handle_get)

    # Return boolean to indicate that initialization was successfully.
    return True