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
            label="Ethernet",
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

        self.add(self.light_status_button)
        self.add(self.light_menu_button)


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
        self.light_button = LightButton(self.notch)
        self.caffeine_button = CaffeineButton()

        # Agregar botones al contenedor
        self.add(self.network_button)
        self.add(self.bluetooth_button)
        self.add(self.light_button)
        self.add(self.caffeine_button)

        self.show_all()
