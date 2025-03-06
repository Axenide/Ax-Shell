import gi
from gi.repository.Gio import Icon
import requests
import threading
import urllib.parse
import datetime
from fabric.widgets.label import Label
from fabric.widgets.webview import WebView
from fabric.widgets.eventbox import EventBox
from fabric.widgets.overlay import Overlay
from fabric.widgets.box import Box
from fabric.widgets.revealer import Revealer
from gi.repository import Gtk, GLib
import modules.icons as icons
# from gi.repository import GLib

URL_FILE_PATH = "/home/mathias/.config/nightscoutURL.txt"

def get_url():
    try:
        with open(URL_FILE_PATH, "r") as file:
            url = file.read().strip()
            if url:
                return url
    except Exception as e:
        print(f"Error reading URL file: {e}")
    return None

class MyCgm(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="cgm",
            spacing=4,
            h_align="center",
            v_align="center"
        )

        self.url = get_url()

        self.web = WebView(
            url=self.url,
            size=[450,290]
        )
        self.add(self.web)

class SmallCgm(Overlay):
    def __init__(self, **kwargs):
        main_box = Box(
            name="smallcgm",
            spacing=0,
            orientation="h",
            visible=True,
            all_visible=True,
        )
        self.label = Label(name="smallcgm-label", markup=icons.loader)
        # Update every 30 seconds
        GLib.timeout_add_seconds(30, self.fetch_svg)

        self.dir_label = Label(name="metrics-level", style_classes="ram", label="1")
        self.dir_icon = Label(name="metrics-level", style_classes="ram", markup=icons.arrow_right)
        self.dir_revealer = Revealer(
            name="metrics-ram-revealer",
            transition_duration=250,
            transition_type="slide-right",
            child=Box(children=[self.dir_label, self.dir_icon]),
            child_revealed=False,
        )
        self.fetch_svg()
        main_box.add(self.label)
        main_box.add(self.dir_revealer)

        event_box = EventBox(events=["enter-notify-event", "leave-notify-event"])
        event_box.connect("enter-notify-event", self.on_mouse_enter)
        event_box.connect("leave-notify-event", self.on_mouse_leave)

        # Inicializamos MetricsSmall como un Overlay cuyo "child" es el EventBox
        super().__init__(
            name="metrics-small",
            child=main_box,
            visible=True,
            all_visible=True,
            overlays=[event_box]
        )

        self.hide_timer = None
        self.hover_counter = 0

        self.show_all()

    def fetch_svg(self):
        threading.Thread(target=self._fetch_svg_thread, daemon=True).start()
        return True

    def _fetch_svg_thread(self):
        url = str(get_url())+"api/v1/entries/sgv?count=1&token=pc-c9c1bb7ea942d452"
        response = requests.get(url)
        if response.status_code == 200:
            tabel = response.text.split()
            svg = round(int(tabel[2]) / 18, 1)
            GLib.idle_add(self.label.set_label, icons.graf + str(svg)+"mmol/L")
            # Parse the ISO 8601 format time
            parsed_time = datetime.datetime.strptime(tabel[0].strip('"\''), "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
            if tabel[3].find("Down") != -1:
                trend = icons.trend_down
            elif tabel[3].find("Flat") != -1:
                trend = icons.arrow_right
            elif tabel[3].find("Up") != -1:
                trend = icons.trend_up
            # Get current time
            now = datetime.datetime.now(datetime.timezone.utc)

            # Calculate the time difference in minutes
            minutes_since = str(round((now - parsed_time).total_seconds() / 60))
            GLib.idle_add(self.dir_label.set_label, " +"+minutes_since+"min")
            GLib.idle_add(self.dir_icon.set_markup, trend)

    def on_mouse_enter(self, widget, event):
        self.hover_counter += 1
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        # Revelar niveles en hover para todas las métricas
        self.dir_revealer.set_reveal_child(True)
        return False

    def on_mouse_leave(self, widget, event):
        if self.hover_counter > 0:
            self.hover_counter -= 1
        if self.hover_counter == 0:
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
            self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
        return False

    def hide_revealer(self):
        self.dir_revealer.set_reveal_child(False)
        self.hide_timer = None
        return False
