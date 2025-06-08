import subprocess

import gi
from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import Gdk, GLib, Gtk

import config.data as data

gi.require_version('Gtk', '3.0')
import modules.icons as icons
from services.network import NetworkClient


def add_hover_cursor(widget):
    widget.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
    widget.connect("enter-notify-event", lambda w, e: w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer")) if w.get_window() else None)
    widget.connect("leave-notify-event", lambda w, e: w.get_window().set_cursor(None) if w.get_window() else None)

class NetworkButton(Box):
    def __init__(self, **kwargs):
        self.widgets_instance = kwargs.pop("widgets")
        self.network_client = NetworkClient()
        self._animation_timeout_id = None
        self._animation_step = 0
        self._animation_direction = 1

        self.network_icon = Label(
            name="network-icon",
            markup=None,
        )
        self.network_label = Label(
            name="network-label",
            label="Wi-Fi",
            justification="left",
        )
        self.network_label_box = Box(children=[self.network_label, Box(h_expand=True)])
        self.network_ssid = Label(
            name="network-ssid",
            justification="left",
        )
        self.network_ssid_box = Box(children=[self.network_ssid, Box(h_expand=True)])
        self.network_text = Box(
            name="network-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.network_label_box, self.network_ssid_box],
        )
        self.network_status_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,

            children=[self.network_icon, self.network_text],
        )
        self.network_status_button = Button(
            name="network-status-button",
            h_expand=True,
            child=self.network_status_box,
            on_clicked=lambda *_: self.network_client.wifi_device.toggle_wifi() if self.network_client.wifi_device else None,
        )
        add_hover_cursor(self.network_status_button)

        self.network_menu_label = Label(
            name="network-menu-label",
            markup=icons.chevron_right,
        )
        self.network_menu_button = Button(
            name="network-menu-button",
            child=self.network_menu_label,
            on_clicked=lambda *_: self.widgets_instance.show_network_applet(),
        )
        add_hover_cursor(self.network_menu_button)

        super().__init__(
            name="network-button",
            orientation="h",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
            spacing=0,
            children=[self.network_status_button, self.network_menu_button],
        )

        self.widgets_list_internal = [self, self.network_icon, self.network_label,
                       self.network_ssid, self.network_status_button,
                       self.network_menu_button, self.network_menu_label]

        self.network_client.connect('device-ready', self._on_wifi_ready)

        GLib.idle_add(self._initial_update)

    def _initial_update(self):
        self.update_state()
        return False

    def _on_wifi_ready(self, *args):
        if self.network_client.wifi_device:
            self.network_client.wifi_device.connect('notify::enabled', self.update_state)
            self.network_client.wifi_device.connect('notify::ssid', self.update_state)
            self.update_state()

    def _animate_searching(self):
        """Animate wifi icon when searching for networks"""
        wifi_icons = [icons.wifi_0, icons.wifi_1, icons.wifi_2, icons.wifi_3, icons.wifi_2, icons.wifi_1]

        wifi = self.network_client.wifi_device
        if not self.network_icon or not wifi or not wifi.enabled:
            self._stop_animation()
            return False

        if wifi.state == "activated" and wifi.ssid != "Disconnected":
            self._stop_animation()
            return False

        GLib.idle_add(self.network_icon.set_markup, wifi_icons[self._animation_step])

        self._animation_step = (self._animation_step + 1) % len(wifi_icons)

        return True

    def _start_animation(self):
        if self._animation_timeout_id is None:
            self._animation_step = 0
            self._animation_direction = 1

            self._animation_timeout_id = GLib.timeout_add(500, self._animate_searching)

    def _stop_animation(self):
        if self._animation_timeout_id is not None:
            GLib.source_remove(self._animation_timeout_id)
            self._animation_timeout_id = None

    def update_state(self, *args):
        """Update the button state based on network status"""
        wifi = self.network_client.wifi_device
        ethernet = self.network_client.ethernet_device

        if wifi and not wifi.enabled:
            self._stop_animation()
            self.network_icon.set_markup(icons.wifi_off)
            for widget in self.widgets_list_internal:
                widget.add_style_class("disabled")
            self.network_ssid.set_label("Disabled")
            return

        for widget in self.widgets_list_internal:
            widget.remove_style_class("disabled")

        if wifi and wifi.enabled:
            if wifi.state == "activated" and wifi.ssid != "Disconnected":
                self._stop_animation()
                self.network_ssid.set_label(wifi.ssid)

                if wifi.strength > 0:
                    strength = wifi.strength
                    if strength < 25:
                        self.network_icon.set_markup(icons.wifi_0)
                    elif strength < 50:
                        self.network_icon.set_markup(icons.wifi_1)
                    elif strength < 75:
                        self.network_icon.set_markup(icons.wifi_2)
                    else:
                        self.network_icon.set_markup(icons.wifi_3)
            else:
                self.network_ssid.set_label("Enabled")
                self._start_animation()

        try:
            primary_device = self.network_client.primary_device
        except AttributeError:
            primary_device = "wireless"

        if primary_device == "wired":
            self._stop_animation()
            if ethernet and ethernet.internet == "activated":
                self.network_icon.set_markup(icons.world)
            else:
                self.network_icon.set_markup(icons.world_off)
        else:
            if not wifi:
                self._stop_animation()
                self.network_icon.set_markup(icons.wifi_off)
            elif wifi.state == "activated" and wifi.ssid != "Disconnected" and wifi.strength > 0:
                self._stop_animation()
                strength = wifi.strength
                if strength < 25:
                    self.network_icon.set_markup(icons.wifi_0)
                elif strength < 50:
                    self.network_icon.set_markup(icons.wifi_1)
                elif strength < 75:
                    self.network_icon.set_markup(icons.wifi_2)
                else:
                    self.network_icon.set_markup(icons.wifi_3)
            else:
                self._start_animation()

class BluetoothButton(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="bluetooth-button",
            orientation="h",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
        )
        self.widgets = kwargs["widgets"]

        self.bluetooth_icon = Label(
            name="bluetooth-icon",
            markup=icons.bluetooth,
        )
        self.bluetooth_label = Label(
            name="bluetooth-label",
            label="Bluetooth",
            justification="left",
        )
        self.bluetooth_label_box = Box(children=[self.bluetooth_label, Box(h_expand=True)])
        self.bluetooth_status_text = Label(
            name="bluetooth-status",
            label="Disabled",
            justification="left",
        )
        self.bluetooth_status_box = Box(children=[self.bluetooth_status_text, Box(h_expand=True)])
        self.bluetooth_text = Box(
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.bluetooth_label_box, self.bluetooth_status_box],
        )
        self.bluetooth_status_container = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.bluetooth_icon, self.bluetooth_text],
        )
        self.bluetooth_status_button = Button(
            name="bluetooth-status-button",
            h_expand=True,
            child=self.bluetooth_status_container,
            on_clicked=lambda *_: self.widgets.bluetooth.client.toggle_power(),
        )
        add_hover_cursor(self.bluetooth_status_button)
        self.bluetooth_menu_label = Label(
            name="bluetooth-menu-label",
            markup=icons.chevron_right,
        )
        self.bluetooth_menu_button = Button(
            name="bluetooth-menu-button",
            on_clicked=lambda *_: self.widgets.show_bt(),
            child=self.bluetooth_menu_label,
        )
        add_hover_cursor(self.bluetooth_menu_button)

        self.add(self.bluetooth_status_button)
        self.add(self.bluetooth_menu_button)

class NightModeButton(Button):
    def __init__(self):
        self.night_mode_icon = Label(
            name="night-mode-icon",
            markup=icons.night,
        )
        self.night_mode_label = Label(
            name="night-mode-label",
            label="Night Mode",
            justification="left",
        )
        self.night_mode_label_box = Box(children=[self.night_mode_label, Box(h_expand=True)])
        self.night_mode_status = Label(
            name="night-mode-status",
            label="Enabled",
            justification="left",
        )
        self.night_mode_status_box = Box(children=[self.night_mode_status, Box(h_expand=True)])
        self.night_mode_text = Box(
            name="night-mode-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.night_mode_label_box, self.night_mode_status_box],
        )
        self.night_mode_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.night_mode_icon, self.night_mode_text],
        )

        super().__init__(
            name="night-mode-button",
            h_expand=True,
            child=self.night_mode_box,
            on_clicked=self.toggle_hyprsunset,
        )
        add_hover_cursor(self)

        self.widgets = [self, self.night_mode_label, self.night_mode_status, self.night_mode_icon]
        self.check_hyprsunset()

    def toggle_hyprsunset(self, *args):
        """
        Toggle the 'hyprsunset' process:
          - If running, kill it and mark as 'Disabled'.
          - If not running, start it and mark as 'Enabled'.
        """
        try:
            subprocess.check_output(["pgrep", "hyprsunset"])
            exec_shell_command_async("pkill hyprsunset")
            self.night_mode_status.set_label("Disabled")
            for widget in self.widgets:
                widget.add_style_class("disabled")
        except subprocess.CalledProcessError:
            exec_shell_command_async("hyprsunset -t 3500")
            self.night_mode_status.set_label("Enabled")
            for widget in self.widgets:
                widget.remove_style_class("disabled")

    def check_hyprsunset(self, *args):
        """
        Update the button state based on whether hyprsunset is running.
        """
        try:
            subprocess.check_output(["pgrep", "hyprsunset"])
            self.night_mode_status.set_label("Enabled")
            for widget in self.widgets:
                widget.remove_style_class("disabled")
        except subprocess.CalledProcessError:
            self.night_mode_status.set_label("Disabled")
            for widget in self.widgets:
                widget.add_style_class("disabled")

class CaffeineButton(Button):
    def __init__(self):
        self.caffeine_icon = Label(
            name="caffeine-icon",
            markup=icons.coffee,
        )
        self.caffeine_label = Label(
            name="caffeine-label",
            label="Caffeine",
            justification="left",
        )
        self.caffeine_label_box = Box(children=[self.caffeine_label, Box(h_expand=True)])
        self.caffeine_status = Label(
            name="caffeine-status",
            label="Enabled",
            justification="left",
        )
        self.caffeine_status_box = Box(children=[self.caffeine_status, Box(h_expand=True)])
        self.caffeine_text = Box(
            name="caffeine-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.caffeine_label_box, self.caffeine_status_box],
        )
        self.caffeine_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.caffeine_icon, self.caffeine_text],
        )
        super().__init__(
            name="caffeine-button",
            h_expand=True,
            child=self.caffeine_box,
            on_clicked=self.toggle_inhibit,
        )
        add_hover_cursor(self)

        self.widgets = [self, self.caffeine_label, self.caffeine_status, self.caffeine_icon]
        self.check_inhibit()

    def toggle_inhibit(self, *args, external=False):
        """
        Toggle the 'ax-inhibit' process:
          - If running, kill it and mark as 'Disabled' (add 'disabled' class).
          - If not running, start it and mark as 'Enabled' (remove 'disabled' class).
        """

        try:
            subprocess.check_output(["pgrep", "ax-inhibit"])
            exec_shell_command_async("pkill ax-inhibit")
            self.caffeine_status.set_label("Disabled")
            for i in self.widgets:
                i.add_style_class("disabled")
        except subprocess.CalledProcessError:
            exec_shell_command_async(f"python {data.HOME_DIR}/.config/{data.APP_NAME_CAP}/scripts/inhibit.py")
            self.caffeine_status.set_label("Enabled")
            for i in self.widgets:
                i.remove_style_class("disabled")

        if external:
            # Different if enabled or disabled
            message = "Disabled 💤" if self.caffeine_status.get_label() == "Disabled" else "Enabled ☀️"
            exec_shell_command_async(f"notify-send '☕ Caffeine' '{message}' -a '{data.APP_NAME_CAP}' -e")

    def check_inhibit(self, *args):
        try:
            subprocess.check_output(["pgrep", "ax-inhibit"])
            self.caffeine_status.set_label("Enabled")
            for i in self.widgets:
                i.remove_style_class("disabled")
        except subprocess.CalledProcessError:
            self.caffeine_status.set_label("Disabled")
            for i in self.widgets:
                i.add_style_class("disabled")

class Buttons(Gtk.Grid):
    def __init__(self, **kwargs):
        super().__init__(name="buttons-grid")
        self.set_row_homogeneous(True)
        self.set_column_homogeneous(True)
        self.set_row_spacing(4)
        self.set_column_spacing(4)
        self.set_vexpand(False)

        self.widgets = kwargs["widgets"]

        self.network_button = NetworkButton(widgets=self.widgets)
        self.bluetooth_button = BluetoothButton(widgets=self.widgets)
        self.night_mode_button = NightModeButton()
        self.caffeine_button = CaffeineButton()

        if data.PANEL_THEME == "Panel" and (data.BAR_POSITION in ["Left", "Right"] or data.PANEL_POSITION in ["Start", "End"]):

            self.attach(self.network_button, 0, 0, 1, 1)
            self.attach(self.bluetooth_button, 1, 0, 1, 1)
            self.attach(self.night_mode_button, 0, 1, 1, 1)
            self.attach(self.caffeine_button, 1, 1, 1, 1)
        else:

            self.attach(self.network_button, 0, 0, 1, 1)
            self.attach(self.bluetooth_button, 1, 0, 1, 1)
            self.attach(self.night_mode_button, 2, 0, 1, 1)
            self.attach(self.caffeine_button, 3, 0, 1, 1)

        self.show_all()
