import json
import os

# Class to get personal data from a JSON file, like location and nightscoutURL

class PrivateData:
    def __init__(self):
        try:
            if os.path.exists('/home/mathias/.config/Ax-Shell/personal_config.json'):
                with open('/home/mathias/.config/Ax-Shell/personal_config.json', 'r') as f:
                    data = json.load(f)
                    _location = data.get("location", "")
                    _nightscout = data.get("nightscout", "")
                    _nightscout_api = data.get("nightscout_api", "")
            else:
                    print("File not found: personal_config.json")
        except (FileNotFoundError, json.JSONDecodeError):
            _location = "40.7128&lon=74.0060" #new york city
            _nightscout = "https://nightscout.com" #paste your nightscout website here
            _nightscout_api = "" #your nightscout api key
        self._location = _location
        self._nightscout = _nightscout
        self._nightscout_api = _nightscout_api

    def get_location(self) -> str:
        return str(self._location)

    def get_nightscout(self) -> str:
        return str(self._nightscout)

    def get_nightscout_api(self) -> str:
        return str(self._nightscout_api)

    nightscout = property(get_nightscout)
    location = property(get_location)
    nightscout_api = property(get_nightscout_api)
