import gi

gi.require_version('Gtk', '3.0')
gi.require_version('NM', '1.0')
from fabric.utils import bulk_connect
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import NM, GLib, Gtk

import modules.icons as icons
from services.network import NetworkClient


class WifiAccessPointSlot(CenterBox):
    def __init__(self, ap_data: dict, network_service: NetworkClient, wifi_service, **kwargs):
        super().__init__(name="wifi-ap-slot", **kwargs)
        self.ap_data = ap_data
        self.network_service = network_service
        self.wifi_service = wifi_service

        ssid = ap_data.get("ssid", "Unknown SSID")
        icon_name = ap_data.get("icon-name", "network-wireless-signal-none-symbolic")

        self.is_active = False
        active_ap_details = ap_data.get("active-ap")
        if active_ap_details and hasattr(active_ap_details, 'get_bssid') and active_ap_details.get_bssid() == ap_data.get("bssid"):
            self.is_active = True
        
        self.ap_icon = Image(icon_name=icon_name, size=24)
        self.ap_label = Label(label=ssid, h_expand=True, h_align="start", ellipsization="end")
        
        self.connect_button = Button(
            name="wifi-connect-button",
            label="Connected" if self.is_active else "Connect",
            sensitive=not self.is_active,
            on_clicked=self._on_connect_clicked,
            style_classes=["connected"] if self.is_active else None,
        )

        self.set_start_children([
            Box(spacing=8, h_expand=True, h_align="fill", children=[
                self.ap_icon,
                self.ap_label,
            ])
        ])
        self.set_end_children([self.connect_button])

    def _on_connect_clicked(self, _):
        if not self.is_active and self.ap_data.get("bssid"):
            self.connect_button.set_label("Connecting...")
            self.connect_button.set_sensitive(False)
            self.network_service.connect_wifi_bssid(self.ap_data["bssid"])


class NetworkConnections(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="network-connections",
            orientation="vertical",
            spacing=4,
            **kwargs,
        )
        self.widgets = kwargs.get("widgets")
        self.network_client = NetworkClient()

        self.status_label = Label(label="Initializing Wi-Fi...", h_expand=True, h_align="center")

        self.back_button = Button(
            name="network-back",
            child=Label(name="network-back-label", markup=icons.chevron_left),
            on_clicked=lambda *_: self.widgets.show_notif()
        )
        

        self.wifi_toggle_button_icon = Label(markup=icons.wifi_3)
        self.wifi_toggle_button = Button(
            name="wifi-toggle-button",
            child=self.wifi_toggle_button_icon,
            tooltip_text="Toggle Wi-Fi",
            on_clicked=self._toggle_wifi
        )
        

        self.refresh_button_icon = Label(name="network-refresh-label", markup=icons.reload)
        self.refresh_button = Button(
            name="network-refresh",
            child=self.refresh_button_icon,
            tooltip_text="Scan for Wi-Fi networks",
            on_clicked=self._refresh_access_points
        )

        header_box = CenterBox(
            name="network-header",
            start_children=[self.back_button],
            center_children=[Label(name="network-title", label="Wi-Fi Networks")],
            end_children=[Box(orientation="horizontal", spacing=4, children=[self.refresh_button])]
        )

        self.ap_list_box = Box(orientation="vertical", spacing=4)
        scrolled_window = ScrolledWindow(
            name="network-ap-scrolled-window",
            child=self.ap_list_box,
            h_expand=True,
            v_expand=True,
            propagate_width=False,
            propagate_height=False,
        )

        self.add(header_box)
        self.add(self.status_label)
        self.add(scrolled_window)

        self.network_client.connect("device-ready", self._on_device_ready)
        self.wifi_toggle_button.set_sensitive(False)
        self.refresh_button.set_sensitive(False)

    def _on_device_ready(self, _client):

        if self.network_client.wifi_device:
            self.network_client.wifi_device.connect("changed", self._load_access_points)
            self.network_client.wifi_device.connect("notify::enabled", self._update_wifi_status_ui)
            self._update_wifi_status_ui() 
            if self.network_client.wifi_device.enabled:
                self._load_access_points() 
            else:
                self.status_label.set_label("Wi-Fi disabled.")
                self.status_label.set_visible(True)
        else:
            self.status_label.set_label("Wi-Fi device not available.")
            self.status_label.set_visible(True)
            self.wifi_toggle_button.set_sensitive(False)
            self.refresh_button.set_sensitive(False)

    def _update_wifi_status_ui(self, *args):
        if self.network_client.wifi_device:
            enabled = self.network_client.wifi_device.enabled
            self.wifi_toggle_button.set_sensitive(True)
            self.refresh_button.set_sensitive(enabled)
            
            if enabled:
                self.wifi_toggle_button_icon.set_markup(icons.wifi_3)
            else:
                self.wifi_toggle_button_icon.set_markup(icons.wifi_off)
                self.status_label.set_label("Wi-Fi disabled.")
                self.status_label.set_visible(True)
                self._clear_ap_list()
            
            if enabled and not self.ap_list_box.get_children():
                GLib.idle_add(self._refresh_access_points)
        else:
            self.wifi_toggle_button.set_sensitive(False)
            self.refresh_button.set_sensitive(False)

    def _toggle_wifi(self, _):
        if self.network_client.wifi_device:
            self.network_client.wifi_device.toggle_wifi()

    def _refresh_access_points(self, _=None): 
        if self.network_client.wifi_device and self.network_client.wifi_device.enabled:
            self.status_label.set_label("Scanning for Wi-Fi networks...")
            self.status_label.set_visible(True)
            self._clear_ap_list() 
            self.network_client.wifi_device.scan() 
        return False 

    def _clear_ap_list(self):
        for child in self.ap_list_box.get_children():
            child.destroy()

    def _load_access_points(self, *args):
        if not self.network_client.wifi_device or not self.network_client.wifi_device.enabled:
            self._clear_ap_list()
            self.status_label.set_label("Wi-Fi disabled.")
            self.status_label.set_visible(True)
            return

        self._clear_ap_list()
        
        access_points = self.network_client.wifi_device.access_points
        
        if not access_points:
            self.status_label.set_label("No Wi-Fi networks found.")
            self.status_label.set_visible(True)
        else:
            self.status_label.set_visible(False) 
            sorted_aps = sorted(access_points, key=lambda x: x.get("strength", 0), reverse=True)
            for ap_data in sorted_aps:
                slot = WifiAccessPointSlot(ap_data, self.network_client, self.network_client.wifi_device)
                self.ap_list_box.add(slot)
        self.ap_list_box.show_all()
