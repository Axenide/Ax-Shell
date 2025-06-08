import urllib.parse

import gi
import requests
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import GLib

gi.require_version("Gtk", "3.0")
import config.data as data
import modules.icons as icons


class Weather(Button):
    def __init__(self, **kwargs) -> None:
        super().__init__(name="weather", orientation="h", spacing=8, **kwargs)
        self.label = Label(name="weather-label", markup=icons.loader)
        self.add(self.label)
        self.show_all()
        self.enabled = True
        self.session = requests.Session()
        GLib.timeout_add_seconds(600, self.fetch_weather)
        self.fetch_weather()

    def set_visible(self, visible):
        """Override to track external visibility setting"""
        self.enabled = visible

        if visible and hasattr(self, 'has_weather_data') and self.has_weather_data:
            super().set_visible(True)
        else:
            super().set_visible(visible)

    def fetch_weather(self):
        GLib.Thread.new("weather-fetch", self._fetch_weather_thread, None)
        return True

    def _fetch_weather_thread(self, user_data):

        url = "https://wttr.in/?format=%c+%t" if not data.VERTICAL else "https://wttr.in/?format=%c"

        tooltip_url = "https://wttr.in/?format=%l:+%C,+%t+(%f),+Humidity:+%h,+Wind:+%w"
        
        try:
            response = self.session.get(url, timeout=5)
            if response.ok:
                weather_data = response.text.strip()
                if "Unknown" in weather_data:
                    self.has_weather_data = False
                    GLib.idle_add(super().set_visible, False)
                else:
                    self.has_weather_data = True

                    tooltip_response = self.session.get(tooltip_url, timeout=5)
                    if tooltip_response.ok:
                        tooltip_text = tooltip_response.text.strip()
                        GLib.idle_add(self.set_tooltip_text, tooltip_text)
                    

                    GLib.idle_add(super().set_visible, self.enabled)
                    GLib.idle_add(self.label.set_label, weather_data.replace(" ", ""))
            else:
                self.has_weather_data = False
                GLib.idle_add(self.label.set_markup, f"{icons.cloud_off} Unavailable")
                GLib.idle_add(super().set_visible, False)
        except Exception as e:
            self.has_weather_data = False
            print(f"Error fetching weather: {e}")
            GLib.idle_add(self.label.set_markup, f"{icons.cloud_off} Error")
            GLib.idle_add(super().set_visible, False)
