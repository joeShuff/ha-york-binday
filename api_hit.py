import requests
import json
from datetime import datetime

property_id = "100050589619"

endpoint = "https://doitonline.york.gov.uk/BinsApi/EXOR/getWasteCollectionDatabyUprn?uprn=" + str(property_id)

result = requests.request('GET', endpoint)
json_response = json.loads(result.content)

next_collection_date = None

for collection in json_response:
    if next_collection_date is None:
        next_collection_date = int(collection['NextCollection'][6:-2])
        continue

    this_date = int(collection['NextCollection'][6:-2])

    if this_date < next_collection_date:
        next_collection_date = this_date



for collection in json_response:
    epoch = int(collection['NextCollection'][6:-2]) / 1000
    print(epoch)
    time = datetime.fromtimestamp(epoch)
    print(time.strftime('%d/%m/%Y'))
