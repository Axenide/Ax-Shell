from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
import modules.icons as icons


class NetworkButton(Box):
    def __init__(self):
        super().__init__(
            name="network-button",
            orientation="h",
            h_align="fill",
            v_align="center",
            h_expand=True,
            v_expand=True,
        )

        self.network_icon = Label(
            name="network-icon",
            markup=icons.wifi,
        )
        self.network_label = Label(
            name="network-label",
            label="Wi-Fi",
            justification="left",
        )
        self.network_label_box = Box(children=[self.network_label, Box(h_expand=True)])
        self.network_ssid = Label(
            name="network-ssid",
            label="ARGOS_5GHz",
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
        )
        self.network_menu_label = Label(
            name="network-menu-label",
            markup=icons.chevron_right,
        )
        self.network_menu_button = Button(
            name="network-menu-button",
            child=self.network_menu_label,
        )

        self.add(self.network_status_button)
        self.add(self.network_menu_button)


class BluetoothButton(Box):
    def __init__(self, notch):
        super().__init__(
            name="bluetooth-button",
            orientation="h",
            h_align="fill",
            v_align="center",
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
        self.bluetooth_menu_label = Label(
            name="bluetooth-menu-label",
            markup=icons.chevron_right,
        )
        self.bluetooth_menu_button = Button(
            name="bluetooth-menu-button",
            on_clicked=lambda *_: self.notch.open_notch("bluetooth"),
            child=self.bluetooth_menu_label,
        )

        self.add(self.bluetooth_status_button)
        self.add(self.bluetooth_menu_button)


class NightModeButton(Button):
    def __init__(self):
        night_mode_icon = Label(
            name="night-mode-icon",
            markup=icons.night,
        )
        night_mode_label = Label(
            name="night-mode-label",
            label="Night Mode",
            justification="left",
        )
        night_mode_label_box = Box(children=[night_mode_label, Box(h_expand=True)])
        night_mode_status = Label(
            name="night-mode-status",
            label="Enabled",
            justification="left",
        )
        night_mode_status_box = Box(children=[night_mode_status, Box(h_expand=True)])
        night_mode_text = Box(
            name="night-mode-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[night_mode_label_box, night_mode_status_box],
        )
        night_mode_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[night_mode_icon, night_mode_text],
        )
        super().__init__(
            name="night-mode-button",
            child=night_mode_box,
        )


class CaffeineButton(Button):
    def __init__(self):
        caffeine_icon = Label(
            name="caffeine-icon",
            markup=icons.coffee,
        )
        caffeine_label = Label(
            name="caffeine-label",
            label="Caffeine",
            justification="left",
        )
        caffeine_label_box = Box(children=[caffeine_label, Box(h_expand=True)])
        caffeine_status = Label(
            name="caffeine-status",
            label="Enabled",
            justification="left",
        )
        caffeine_status_box = Box(children=[caffeine_status, Box(h_expand=True)])
        caffeine_text = Box(
            name="caffeine-text",
            orientation="v",
            h_align="start",
            v_align="center",
            children=[caffeine_label_box, caffeine_status_box],
        )
        caffeine_box = Box(
            h_align="start",
            v_align="center",
            spacing=10,
            children=[caffeine_icon, caffeine_text],
        )
        super().__init__(
            name="caffeine-button",
            child=caffeine_box,
        )


class Buttons(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="buttons",
            spacing=4,
            h_align="center",
            v_align="start",
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
        )
        self.notch = kwargs["notch"]

        # Instanciar cada botón
        self.network_button = NetworkButton()
        self.bluetooth_button = BluetoothButton(self.notch)
        self.night_mode_button = NightModeButton()
        self.caffeine_button = CaffeineButton()

        # Agregar botones al contenedor
        self.add(self.network_button)
        self.add(self.bluetooth_button)
        self.add(self.night_mode_button)
        self.add(self.caffeine_button)

        self.show_all()
