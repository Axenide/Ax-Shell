from fabric.utils import exec_shell_command_async
from fabric.bluetooth.service import BluetoothClient, BluetoothDevice
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.eventbox import EventBox
from fabric.widgets.entry import Entry
from fabric.core.service import Signal
from gi.repository import Gdk, Gtk

import modules.icons as icons

def add_hover_cursor(widget :Gtk.Widget):
    widget.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK) # type: ignore
    widget.connect("enter-notify-event", lambda w, e: w.get_window().set_cursor(Gdk.Cursor.new_from_name(w.get_display(), "pointer")) if w.get_window() else None)
    widget.connect("leave-notify-event", lambda w, e: w.get_window().set_cursor(None) if w.get_window() else None)

class BluetoothDeviceSlot(CenterBox):
    @Signal
    def editing(self, state: bool) -> None: ...

    def __init__(self, device: BluetoothDevice, **kwargs):
        super().__init__(name="bluetooth-device", **kwargs)
        self.device = device
        self.device.connect("changed", self.on_changed)
        self.device.connect(
            "notify::closed", lambda *_: self.device.closed and self.destroy()
        )

        self.connection_label = Label(name="bluetooth-connection", markup=icons.bluetooth_disconnected)
        self.connect_button = Button(
            name="bluetooth-connect",
            label="Connect",
            on_clicked=lambda *_: self.device.set_connecting(not self.device.connected),
            style_classes=["connected"] if self.device.connected else None,
        )
        # Cannot get ellipsized text on entry so I have label aswell
        self.nickname_label = Label(label=device.alias, h_expand=True, h_align="start", ellipsization="end")
        self.nickname_entry = Entry(name="search-entry-walls",text=device.alias, h_align="start", visible=False)

        self.nickname_button = EventBox(events=["button-press-event"], child=Image(icon_name=device.icon_name + "-symbolic", size=16)) # type: ignore
        self.nickname_button.connect("button-press-event", self.nickname_edit)
        add_hover_cursor(self.nickname_button)

        self.nickname_entry.connect("activate", self.exit_edit)

        self.start_children = [
            Box(
                spacing=8,
                h_expand=True,
                h_align="fill",
                children=[
                    self.nickname_button,
                    self.nickname_label,
                    self.nickname_entry,
                    self.connection_label,
                ],
            )
        ]
        self.end_children = self.connect_button

        self.device.emit("changed")

    def on_changed(self, *_):
        self.connection_label.set_markup(
            icons.bluetooth_connected if self.device.connected else icons.bluetooth_disconnected
        )
        if self.device.connecting:
            self.connect_button.set_label(
                "Connecting..." if not self.device.connecting else "..."
            )
        else:
            self.connect_button.set_label(
                "Connect" if not self.device.connected else "Disconnect"
            )
        if self.device.connected:
            self.connect_button.add_style_class("connected")
        else:
            self.connect_button.remove_style_class("connected")
        return

    def nickname_edit(self, widget, event):
        if event.button == 1:
            toggle = False if self.nickname_entry.is_visible() else True
            self.editable(toggle)
            self.emit('editing', toggle)

    def focus_out(self, *args):
        if self.nickname_entry.is_visible():
            self.exit_edit()

    def exit_edit(self, *args):
        self.editable(False)
        self.emit('editing', False)
        if self.nickname_entry.get_text() == "":
            self.nickname_entry.set_text(self.device.name)
        # Get the text value before setting it
        new_alias = self.nickname_entry.get_text()
        cmd = f"bt-device --set {self.device.address} Alias {new_alias}"
        print(f"Running command: {cmd}")
        exec_shell_command_async(cmd)
        # Set the device alias - the implementation in BluetoothDevice will handle the details
        self.nickname_label.set_label(new_alias)
        self.device.emit("changed")

    def editable(self, yes: bool):
        if yes:
            self.nickname_label.hide()
            self.nickname_entry.show()
            self.nickname_entry.grab_focus()
            self.nickname_entry.set_position(-1)
        else:
            self.nickname_label.show()
            self.nickname_entry.hide()

class BluetoothConnections(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="bluetooth",
            spacing=4,
            orientation="vertical",
            **kwargs,
        )

        self.widgets = kwargs["widgets"]

        self.editing = False

        self.buttons = self.widgets.buttons.bluetooth_button
        self.bt_status_text = self.buttons.bluetooth_status_text
        self.bt_status_button = self.buttons.bluetooth_status_button
        self.bt_icon = self.buttons.bluetooth_icon
        self.bt_label = self.buttons.bluetooth_label
        self.bt_menu_button = self.buttons.bluetooth_menu_button
        self.bt_menu_label = self.buttons.bluetooth_menu_label

        self.client = BluetoothClient(on_device_added=self.on_device_added)
        self.scan_label = Label(name="bluetooth-scan-label", markup=icons.radar)
        self.scan_button = Button(
            name="bluetooth-scan",
            child=self.scan_label,
            tooltip_text="Scan for Bluetooth devices",
            on_clicked=lambda *_: self.client.toggle_scan()
        )
        self.back_button = Button(
            name="bluetooth-back",
            child=Label(name="bluetooth-back-label", markup=icons.chevron_left),
            on_clicked=lambda *_: self.widgets.show_notif()
        )

        self.client.connect("notify::enabled", lambda *_: self.status_label())
        self.client.connect(
            "notify::scanning",
            lambda *_: self.update_scan_label()
        )

        self.paired_box = Box(spacing=2, orientation="vertical")
        self.available_box = Box(spacing=2, orientation="vertical")

        content_box = Box(spacing=4, orientation="vertical")
        content_box.add(self.paired_box)
        content_box.add(Label(name="bluetooth-section", label="Available"))
        content_box.add(self.available_box)

        self.children = [
            CenterBox(
                name="bluetooth-header",
                start_children=self.back_button,
                center_children=Label(name="bluetooth-text", label="Bluetooth Devices"),
                end_children=self.scan_button
            ),
            ScrolledWindow(
                name="bluetooth-devices",
                min_content_size=(-1, -1),
                child=content_box,
                v_expand=True,
                propagate_width=False,
                propagate_height=False,
            ),
        ]

        self.client.notify("scanning")
        self.client.notify("enabled")

    def status_label(self):
        print(self.client.enabled)
        if self.client.enabled:
            self.bt_status_text.set_label("Enabled")
            for i in [self.bt_status_button, self.bt_status_text, self.bt_icon, self.bt_label, self.bt_menu_button, self.bt_menu_label]:
                i.remove_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth)
        else:
            self.bt_status_text.set_label("Disabled")
            for i in [self.bt_status_button, self.bt_status_text, self.bt_icon, self.bt_label, self.bt_menu_button, self.bt_menu_label]:
                i.add_style_class("disabled")
            self.bt_icon.set_markup(icons.bluetooth_off)

    def on_device_added(self, client: BluetoothClient, address: str):
        if not (device := client.get_device(address)):
            return
        slot = BluetoothDeviceSlot(device)
        slot.connect('editing', self.on_editing)

        if device.paired:
            return self.paired_box.add(slot)
        return self.available_box.add(slot)

    def update_scan_label(self):
        if self.client.scanning:
            self.scan_label.add_style_class("scanning")
            self.scan_button.add_style_class("scanning")
            self.scan_button.set_tooltip_text("Stop scanning for Bluetooth devices")
        else:
            self.scan_label.remove_style_class("scanning")
            self.scan_button.remove_style_class("scanning")
            self.scan_button.set_tooltip_text("Scan for Bluetooth devices")

    def on_editing(self, widget, state):
        self.editing = state
