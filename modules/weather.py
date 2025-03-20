import gi
import requests
import threading
import urllib.parse
from gi.repository import Gtk, GLib
from modules.private_data import PrivateData
import requests
from gi.repository import Gtk,GLib

from fabric.widgets.label import Label
from fabric.widgets.box import Box

gi.require_version("Gtk", "3.0")
import modules.icons as icons

class Weather(Box):
    def __init__(self, **kwargs) -> None:
        super().__init__(name="weather", orientation="h", spacing=8, **kwargs)
        self.label = Label(name="weather-label", markup=icons.loader)
        self.cords = PrivateData()
        self.add(self.label)
        self.show_all()
        self.session = requests.Session()  # Reuse HTTP connection
        # Update every 10 minutes
        GLib.timeout_add_seconds(600, self.fetch_weather)
        self.fetch_weather()

    def get_location(self):
        try:
            response = requests.get("https://ipinfo.io/json")
            if response.status_code == 200:
                data = response.json()
                return data.get("city", "")
            else:
                print("Error getting location from ipinfo.")
        except Exception as e:
            print(f"Error getting location: {e}")
        return ""

    def fetch_weather(self):
        GLib.Thread.new("weather-fetch", self._fetch_weather_thread, None)
        return True

<<<<<<< HEAD
    def _fetch_weather_thread(self):
        #location = "Harstad" #self.get_location()
        # if location:
        #     # URL encode the location to make it URL friendly.
        #     encoded_location = urllib.parse.quote(location)
        #     url = f"https://wttr.in/{encoded_location}?format=%c+%t"
        # else:
        #     url = "https://wttr.in/?format=%c+%t"
        url = f'https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={self.cords.location}&altitude=90'
        try:
            response = requests.get(url, headers={'User-Agent': 'weather-app/1.0'})
            if response.status_code == 200:
                weather_data = response.json()["properties"]["timeseries"][0]["data"]["instant"]["details"]["air_temperature"]
                GLib.idle_add(self.label.set_label, str(weather_data)+"°C")
=======
    def _fetch_weather_thread(self, data):
        location = self.get_location()
        if location:
            url = f"https://wttr.in/{urllib.parse.quote(location)}?format=%c+%t"
        else:
            url = "https://wttr.in/?format=%c+%t"
        try:
            response = self.session.get(url, timeout=5)
            if response.ok:
                weather_data = response.text.strip()
                if "Unknown" in weather_data:
                    GLib.idle_add(self.set_visible, False)
                else:
                    GLib.idle_add(self.set_visible, True)
                    GLib.idle_add(self.label.set_label, weather_data.replace(" ", ""))
>>>>>>> 5dd7cc83a8aa349975e713044e5b3411cec2d2c2
            else:
                GLib.idle_add(self.label.set_markup, f"{icons.cloud_off} Unavailable")
                GLib.idle_add(self.set_visible, False)
        except Exception as e:
            print(f"Error fetching weather: {e}")
            GLib.idle_add(self.label.set_markup, f"{icons.cloud_off} Error")
            GLib.idle_add(self.set_visible, False)
