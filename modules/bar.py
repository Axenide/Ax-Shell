from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import Workspaces, WorkspaceButton
from fabric.utils.helpers import get_relative_path, exec_shell_command_async
from gi.repository import Gdk
from modules.systemtray import SystemTray
import modules.icons as icons
import modules.data as data
<<<<<<< HEAD
import nightscout
=======
from modules.metrics import MetricsSmall
from modules.controls import ControlSmall
>>>>>>> 360cd6ffe982d56c29e2e74aa82646d197c34c92

class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar",
            layer="top",
            anchor="left top right",
            margin="-8px -4px -8px -4px",
            exclusivity="auto",
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs.get("notch", None)

        self.workspaces = Workspaces(
            name="workspaces",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h",
            spacing=10,
            buttons=[WorkspaceButton(id=i, label="") for i in range(1, 11)],
        )

        self.systray = SystemTray()
        # self.systray = SystemTray(name="systray", spacing=8, icon_size=20)

        self.date_time = DateTime(name="date-time", formatters=["%H:%M"], h_align="center", v_align="center")

        self.button_apps = Button(
            name="button-bar",
            on_clicked=lambda *_: self.search_apps(),
            child=Label(
                name="button-bar-label",
                markup=icons.apps
            )
        )
        self.button_apps.connect("enter_notify_event", self.on_button_enter)
        self.button_apps.connect("leave_notify_event", self.on_button_leave)

        self.button_power = Button(
            name="button-bar",
            on_clicked=lambda *_: self.power_menu(),
            child=Label(
                name="button-bar-label",
                markup=icons.shutdown
            )
        )
        self.button_power.connect("enter_notify_event", self.on_button_enter)
        self.button_power.connect("leave_notify_event", self.on_button_leave)

        self.button_overview = Button(
            name="button-bar",
            on_clicked=lambda *_: self.overview(),
            child=Label(
                name="button-bar-label",
                markup=icons.windows
            )
        )
        self.button_overview.connect("enter_notify_event", self.on_button_enter)
        self.button_overview.connect("leave_notify_event", self.on_button_leave)

        self.button_color = Button(
            name="button-bar",
            tooltip_text="Color Picker\nLeft Click: RGB\nMiddle Click: HSV\nRight Click: HEX",
            v_expand=False,
            child=Label(
                name="button-bar-label",
                markup=icons.colorpicker
            )
        )
        self.button_color.connect("enter-notify-event", self.on_button_enter)
        self.button_color.connect("leave-notify-event", self.on_button_leave)
        self.button_color.connect("button-press-event", self.colorpicker)

        self.control = ControlSmall()
        self.metrics = MetricsSmall()
        
        self.revealer = Revealer(
            name="bar-revealer",
            transition_type="slide-left",
            child_revealed=True,
            child=Box(
                name="bar-revealer-box",
                orientation="h",
                spacing=4,
                children=[
                    self.control,
                    self.metrics,
                ],
            ),
        )

        self.boxed_revealer = Box(
            name="boxed-revealer",
            children=[
                self.revealer,
            ],
        )

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation="h",
            h_align="fill",
            v_align="center",
            start_children=Box(
                name="start-container",
                spacing=4,
                orientation="h",
                children=[
                    self.button_apps,
                    Box(name="workspaces-container", children=[self.workspaces]),
                    self.button_overview,
                ]
            ),
            end_children=Box(
                name="end-container",
                spacing=4,
                orientation="h",
                children=[
                    self.boxed_revealer,
                    self.button_color,
                    self.systray,
                    self.button_power,
                    self.date_time,
                ],
            ),
        )

        self.children = self.bar_inner

        self.hidden = False

        self.show_all()
        self.systray._update_visibility()

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def on_button_clicked(self, *args):
        # Ejecuta notify-send cuando se hace clic en el botón
        exec_shell_command_async("notify-send 'Botón presionado' '¡Funciona!'")

    def search_apps(self):
        self.notch.open_notch("launcher")

    def overview(self):
        self.notch.open_notch("overview")

    def power_menu(self):
        self.notch.open_notch("power")

    def colorpicker(self, button, event):
        if event.button == 1:
            exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker-rgb.sh')}")
        elif event.button == 2:
            exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker-hsv.sh')}")
        elif event.button == 3:
            exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker-hex.sh')}")

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.bar_inner.add_style_class("hidden")
        else:
            self.bar_inner.remove_style_class("hidden")
