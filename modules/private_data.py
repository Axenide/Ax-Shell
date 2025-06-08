import json
import os
from fabric.utils import get_relative_path

# Class to get personal data from a JSON file, like location and nightscoutURL

class PrivateData:
    def __init__(self) -> None:
        try:
            path: str = get_relative_path(path='../personal_config.json')
            if os.path.exists(path):
                with open(file=path, mode='r') as f:
                    data = json.load(fp=f)
                    _location = data.get("location", "")
                    _nightscout = data.get("nightscout", "")
                    _nightscout_api = data.get("nightscout_api", "")
                    _hue_ip = data.get("hue_ip", "")
                    _hue_key = data.get("hue_key", "")
            else:
                    print("File not found: personal_config.json")
        except (FileNotFoundError, json.JSONDecodeError):
            _location = "40.7128&lon=74.0060" #new york city
            _nightscout = "https://nightscout.com" #paste your nightscout website here
            _nightscout_api = "" #your nightscout api key
            _hue_ip = data.get("hue_ip", "192.0.0.1")
            _hue_key = data.get("hue_key", "")
        
        self._location = str(_location)
        self._nightscout = str(_nightscout)
        self._nightscout_api = str(_nightscout_api)
        self._hue_ip = str(_hue_ip)
        self._hue_key = str(_hue_key)

    def get_location(self) -> str:
        return f'{self._location}'

    def get_nightscout(self) -> str:
        return f'{self._nightscout}'

    def get_nightscout_api(self) -> str:
        return f'{self._nightscout_api}'
    
    def get_hue_ip(self) -> str:
        return f'{self._hue_ip}'

    def get_hue_key(self) -> str:
        return f'{self._hue_key}'

    nightscout: property = property(fget=get_nightscout)
    location: property = property(fget=get_location)
    nightscout_api: property = property(fget=get_nightscout_api)
    hue_ip: property = property(fget=get_hue_ip)
    hue_key: property = property(fget=get_hue_key)
