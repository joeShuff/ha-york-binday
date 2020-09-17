import requests
import json

property_id = "100050589619"

endpoint = "https://doitonline.york.gov.uk/BinsApi/EXOR/getWasteCollectionDatabyUprn?uprn=" + str(property_id)

result = requests.request('GET', endpoint)
json_response = json.loads(result.content)

print(json_response)
