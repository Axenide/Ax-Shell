import subprocess
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async
import gi
from gi.repository import Gtk, Gdk, GLib  # Added GLib import
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
import modules.icons as icons
from services.network import NetworkClient


def add_hover_cursor(widget):
    # Add enter/leave events to change the cursor
    widget.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
    widget.connect("enter-notify-event", lambda w, e: w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer")) if w.get_window() else None)
    widget.connect("leave-notify-event", lambda w, e: w.get_window().set_cursor(None) if w.get_window() else None)


class NetworkButton(Box):
    def __init__(self):
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
        add_hover_cursor(self.network_status_button)  # <-- Added hover

        self.network_menu_label = Label(
            name="network-menu-label",
            markup=icons.chevron_right,
        )
        self.network_menu_button = Button(
            name="network-menu-button",
            child=self.network_menu_label,
        )
        add_hover_cursor(self.network_menu_button)  # <-- Added hover

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

        self.widgets = [self, self.network_icon, self.network_label,
                       self.network_ssid, self.network_status_button,
                       self.network_menu_button, self.network_menu_label]

        # Connect to wifi device signals when ready
        self.network_client.connect('device-ready', self._on_wifi_ready)

        # Check initial state if wifi device is already available
        if self.network_client.wifi_device:
            self.update_state()

    def _on_wifi_ready(self, *args):
        if self.network_client.wifi_device:
            self.network_client.wifi_device.connect('notify::enabled', self.update_state)
            self.network_client.wifi_device.connect('notify::ssid', self.update_state)
            self.update_state()

    def _animate_searching(self):
        """Animate wifi icon when searching for networks"""
        wifi_icons = [icons.wifi_0, icons.wifi_1, icons.wifi_2, icons.wifi_3, icons.wifi_2, icons.wifi_1]

        # Si el widget no existe o el WiFi está desactivado, detener la animación
        wifi = self.network_client.wifi_device
        if not self.network_icon or not wifi or not wifi.enabled:
            self._stop_animation()
            return False

        # Si estamos conectados, detener la animación
        if wifi.state == "activated" and wifi.ssid != "Disconnected":
            self._stop_animation()
            return False

        GLib.idle_add(self.network_icon.set_markup, wifi_icons[self._animation_step])

        # Reiniciar al principio cuando llegamos al final
        self._animation_step = (self._animation_step + 1) % len(wifi_icons)

        return True  # Mantener la animación activa

    def _start_animation(self):
        if self._animation_timeout_id is None:
            self._animation_step = 0
            self._animation_direction = 1
            # Ejecuta la animación cada 500ms sin usar idle_add
            self._animation_timeout_id = GLib.timeout_add(500, self._animate_searching)


    def _stop_animation(self):
        if self._animation_timeout_id is not None:
            GLib.source_remove(self._animation_timeout_id)
            self._animation_timeout_id = None

    def update_state(self, *args):
        """Update the button state based on network status"""
        wifi = self.network_client.wifi_device
        ethernet = self.network_client.ethernet_device

        # Primero actualizamos el estado enabled/disabled
        if wifi and not wifi.enabled:
            self._stop_animation()
            self.network_icon.set_markup(icons.wifi_off)
            for widget in self.widgets:
                widget.add_style_class("disabled")
            self.network_ssid.set_label("Disabled")
            return

        # Removemos la clase disabled si llegamos aquí
        for widget in self.widgets:
            widget.remove_style_class("disabled")

        # Actualizar el texto y la animación según el estado
        if wifi and wifi.enabled:
            if wifi.state == "activated" and wifi.ssid != "Disconnected":
                self._stop_animation()
                self.network_ssid.set_label(wifi.ssid)
                # Actualizar icono según la intensidad de la señal
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

        # Manejar el caso de conexión por cable
        if self.network_client.primary_device == "wired":
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
    def __init__(self, notch):
        super().__init__(
            name="bluetooth-button",
            orientation="h",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
        )
        self.notch = notch

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
            on_clicked=lambda *_: self.notch.bluetooth.client.toggle_power(),
        )
        add_hover_cursor(self.bluetooth_status_button)  # <-- Added hover
        self.bluetooth_menu_label = Label(
            name="bluetooth-menu-label",
            markup=icons.chevron_right,
        )
        self.bluetooth_menu_button = Button(
            name="bluetooth-menu-button",
            on_clicked=lambda *_: self.notch.open_notch("bluetooth"),
            child=self.bluetooth_menu_label,
        )
        add_hover_cursor(self.bluetooth_menu_button)  # <-- Added hover

        self.add(self.bluetooth_status_button)
        self.add(self.bluetooth_menu_button)


class LightButton(Box):
    def __init__(self, notch):
        super().__init__(
            name="light-button",
            orientation="h",
            h_align="fill",
            v_align="center",
            h_expand=True,
            v_expand=True,
        )
        self.notch = notch

        self.light_icon = Label(
            name="light-icon",
            markup=icons.bulb,
        )
        self.light_label = Label(
            name="light-label",
            label="Light",
            justification="left",
        )
        self.light_label_box = Box(children=[self.light_label, Box(h_expand=True)])
        self.light_status_text = Label(
            name="light-status",
            label="on",
            justification="left",
        )
        self.light_status_box = Box(children=[self.light_status_text, Box(h_expand=True)])
        self.light_text = Box(
            orientation="v",
            h_align="start",
            v_align="center",
            children=[self.light_label_box, self.light_status_box],
        )
        self.light_status_container = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[self.light_icon, self.light_text],
        )
        self.light_status_button = Button(
            name="light-status-button",
            h_expand=True,
            child=self.light_status_container,
            on_clicked=lambda *_: self.notch.hue.switch(),
        )
        self.light_menu_label = Label(
            name="light-menu-label",
            markup=icons.chevron_right,
        )
        self.light_menu_button = Button(
            name="light-menu-button",
            on_clicked=lambda *_: self.notch.open_notch("hue"),
            child=self.light_menu_label,
        )
        add_hover_cursor(self.light_menu_button)

        self.add(self.light_status_button)
        self.add(self.light_menu_button)


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
            on_clicked=self.toggle_wlinhibit,
        )
        add_hover_cursor(self)  # <-- Added hover

        self.widgets = [self, self.caffeine_label, self.caffeine_status, self.caffeine_icon]
        self.check_wlinhibit()

    def toggle_wlinhibit(self, *args):
        """
        Toggle the 'wlinhibit' process:
          - If running, kill it and mark as 'Disabled' (add 'disabled' class).
          - If not running, start it and mark as 'Enabled' (remove 'disabled' class).
        """
        try:
            subprocess.check_output(["pgrep", "wlinhibit"])
            exec_shell_command_async("pkill wlinhibit")
            self.caffeine_status.set_label("Disabled")
            for i in self.widgets:
                i.add_style_class("disabled")
        except subprocess.CalledProcessError:
            exec_shell_command_async("wlinhibit")
            self.caffeine_status.set_label("Enabled")
            for i in self.widgets:
                i.remove_style_class("disabled")

    def check_wlinhibit(self, *args):
        try:
            subprocess.check_output(["pgrep", "wlinhibit"])
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
        self.set_vexpand(False)  # Prevent vertical expansion

        self.notch = kwargs["notch"]

        # Instantiate each button
        self.network_button = NetworkButton()
        self.bluetooth_button = BluetoothButton(self.notch)
        self.light_button = LightButton(self.notch)
        self.caffeine_button = CaffeineButton()

        # Attach buttons into the grid (one row, four columns)
        self.attach(self.network_button, 0, 0, 1, 1)
        self.attach(self.bluetooth_button, 1, 0, 1, 1)
        self.attach(self.light_button, 2, 0, 1, 1)
        self.attach(self.caffeine_button, 3, 0, 1, 1)

        self.show_all()
