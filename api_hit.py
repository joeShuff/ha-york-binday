import requests
import json
from datetime import datetime, timezone


def timestamp_from_api_response(resp):
    try:
        time = datetime.fromisoformat(resp)
        return time.strftime('%d/%m/%Y')
    except Exception as e:
        return "ERROR (converting time)"


def days_until_collection(resp):
    try:
        time = datetime.fromisoformat(resp)
        time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        diff = time - now
        return diff.days + 1
    except Exception as e:
        return "ERROR (calc days)"


def get_from_json(obj, key, default="N/F"):
    try:
        return obj[key]
    except:
        return default



property_id = "PROPERTY_ID_HERE"
endpoint = "https://cyc-myaccount-live.azurewebsites.net/api/bins/GetCollectionDetails/" + str(property_id)

print(days_until_collection("2020-12-15T00:00:00+00:00"))

result = requests.request('GET', endpoint)

if result.status_code != 200:
    print("Error making get request" + str(result.status_code))
else:
    json_response = json.loads(result.content)['services']
    bins = len(json_response)

    if bins > 0:
        print(str(bins) + " bins found.")

    for bin in json_response:
        waste_type = str(bin['service'].lower().replace(" ", "_").replace("/", "_"))

        days_until = days_until_collection(bin['nextCollection'])
        print("days is " + str(days_until))

        print("bin is " + str(bin))