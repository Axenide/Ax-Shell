from os import truncate
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.stack import Stack
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import ActiveWindow
from fabric.utils.helpers import FormattedString, truncate
from gi.repository import GLib, Gdk
from modules.launcher import AppLauncher
from modules.dashboard import Dashboard
from modules.wallpapers import WallpaperSelector
from modules.notifications import NotificationContainer
from modules.power import PowerMenu
from modules.overview import Overview
from modules.bluetooth import BluetoothConnections
from modules.hue import Light
from modules.corners import MyCorner
import modules.icons as icons
import modules.data as data

class Notch(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="notch",
            layer="top",
            anchor="top",
            margin="-40px 10px 10px 10px",
            keyboard_mode="none",
            exclusivity="normal",
            visible=True,
            all_visible=True,
        )

        self.dashboard = Dashboard(notch=self)
        self.launcher = AppLauncher(notch=self)
        self.wallpapers = WallpaperSelector(notch=self)
        self.notification = NotificationContainer(notch=self)
        self.overview = Overview()
        self.power = PowerMenu(notch=self)

        self.bluetooth = BluetoothConnections(notch=self)
        self.hue = Light(notch=self)

        self.active_window = ActiveWindow(
            name="hyprland-window",
            h_expand=True,
            formatter=FormattedString(
                f"{{'{data.USERNAME}@{data.HOSTNAME}' if not win_class or win_class == 'unknown' else truncate(win_class, 32)}}",
                truncate=truncate,
            ),
        )

        self.compact = Button(
            name="notch-compact",
            h_expand=True,
            on_clicked=lambda *_: self.open_notch("dashboard"),
            child=self.active_window,
        )

        self.stack = Stack(
            name="notch-content",
            v_expand=True,
            h_expand=True,
            transition_type="crossfade",
            transition_duration=100,
            children=[
                self.compact,
                self.launcher,
                self.dashboard,
                self.wallpapers,
                self.notification,
                self.overview,
                self.power,
                self.bluetooth,
                self.hue,
            ]
        )

        self.corner_left = Box(
            name="notch-corner-left",
            orientation="v",
            children=[
                MyCorner("top-right"),
                Box(),
            ]
        )

        self.corner_right = Box(
            name="notch-corner-right",
            orientation="v",
            children=[
                MyCorner("top-left"),
                Box(),
            ]
        )

        self.notch_box = CenterBox(
            name="notch-box",
            orientation="h",
            h_align="center",
            v_align="center",
            start_children=Box(
                children=[
                    self.corner_left,
                ],
            ),
            center_children=self.stack,
            end_children=Box(
                children=[
                    self.corner_right,
                ]
            )
        )

        self.hidden = False

        self.add(self.notch_box)
        self.show_all()
        self.wallpapers.viewport.hide()

        self.add_keybinding("Escape", lambda *_: self.close_notch())
        self.add_keybinding("Ctrl Tab", lambda *_: self.dashboard.go_to_next_child())
        self.add_keybinding("Ctrl Shift ISO_Left_Tab", lambda *_: self.dashboard.go_to_previous_child())

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def close_notch(self):
        self.set_keyboard_mode("none")

        if self.hidden:
            self.notch_box.remove_style_class("hideshow")
            self.notch_box.add_style_class("hidden")

        for widget in [self.launcher, self.dashboard, self.wallpapers, self.notification, self.overview, self.power, self.bluetooth, self.hue]:
            widget.remove_style_class("open")
            if widget == self.wallpapers:
                self.wallpapers.viewport.hide()
                self.wallpapers.viewport.set_property("name", None)
        for style in ["launcher", "dashboard", "wallpapers", "notification", "overview", "power", "bluetooth", "hue"]:
            self.stack.remove_style_class(style)
        self.stack.set_visible_child(self.compact)

    def open_notch(self, widget):
        self.set_keyboard_mode("exclusive")

        if self.hidden:
            self.notch_box.remove_style_class("hidden")
            self.notch_box.add_style_class("hideshow")

        widgets = {
            "launcher": self.launcher,
            "dashboard": self.dashboard,
            "wallpapers": self.wallpapers,
            "notification": self.notification,
            "overview": self.overview,
            "power": self.power,
            "bluetooth": self.bluetooth,
            "hue": self.hue
        }

        # Limpiar clases y estados previos
        for style in widgets.keys():
            self.stack.remove_style_class(style)
        for w in widgets.values():
            w.remove_style_class("open")

        # Configurar según el widget solicitado
        if widget in widgets:
            self.stack.add_style_class(widget)
            self.stack.set_visible_child(widgets[widget])
            widgets[widget].add_style_class("open")

            # Acciones específicas para el launcher
            if widget == "launcher":
                self.launcher.open_launcher()
                self.launcher.search_entry.set_text("")
                self.launcher.search_entry.grab_focus()

            if widget == "notification":
                self.set_keyboard_mode("none")

            if widget == "wallpapers":
                self.wallpapers.search_entry.set_text("")
                self.wallpapers.search_entry.grab_focus()
                GLib.timeout_add(
                    500,
                    lambda: (
                        self.wallpapers.viewport.show(),
                        self.wallpapers.viewport.set_property("name", "wallpaper-icons")
                    )
                )

            if widget != "wallpapers":
                self.wallpapers.viewport.hide()
                self.wallpapers.viewport.set_property("name", None)

            if widget == "dashboard" and self.dashboard.stack.get_visible_child() != self.dashboard.stack.get_children()[4]:
                self.dashboard.stack.set_visible_child(self.dashboard.stack.get_children()[0])

        else:
            self.stack.set_visible_child(self.dashboard)

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.notch_box.add_style_class("hidden")
        else:
            self.notch_box.remove_style_class("hidden")
