from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import Workspaces, WorkspaceButton
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import Gdk
from modules.systemtray import SystemTray
import modules.icons as icons
from modules.metrics import MetricsSmall, Battery
from modules.controls import ControlSmall

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
        self.button_tools = Button(
            name="button-bar",
            on_clicked=lambda *_: self.tools_menu(),
            child=Label(
                name="button-bar-label",
                markup=icons.toolbox
            )
        )
        self.button_tools.connect("enter_notify_event", self.on_button_enter)
        self.button_tools.connect("leave_notify_event", self.on_button_leave)


        self.systray = SystemTray()
        # self.weather = Weather()
        # self.systray = SystemTray(name="systray", spacing=8, icon_size=20)

        self.date_time = DateTime(name="date-time", formatters=["%d-%m-%Y %H:%M"], h_align="center", v_align="center")

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


        self.control = ControlSmall()
        self.metrics = MetricsSmall()
        self.battery = Battery()

        self.revealer_right = Revealer(
            name="bar-revealer",
            transition_type="slide-left",
            child_revealed=True,
            child=Box(
                name="bar-revealer-box",
                orientation="h",
                spacing=4,
                children=[
                    self.metrics,
                    self.control,
                ],
            ),
        )

        self.boxed_revealer_right = Box(
            name="boxed-revealer",
            children=[
                self.revealer_right,
            ],
        )

        # self.revealer_left = Revealer(
        #     name="bar-revealer",
        #     transition_type="slide-right",
        #     child_revealed=True,
        #     child=Box(
        #         name="bar-revealer-box",
        #         orientation="h",
        #         spacing=4,
        #         children=[
        #             self.weather,
        #         ],
        #     ),
        # )

        # self.boxed_revealer_left = Box(
        #     name="boxed-revealer",
        #     children=[
        #         self.revealer_left,
        #     ],
        # )

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
                    # self.boxed_revealer_left,
                ]
            ),
            end_children=Box(
                name="end-container",
                spacing=4,
                orientation="h",
                children=[
                    self.boxed_revealer_right,
                    self.battery,
                    self.systray,
                    self.button_tools,
                    self.date_time,
                    self.button_power,
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
    def tools_menu(self):
        self.notch.open_notch("tools")


    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.bar_inner.add_style_class("hidden")
        else:
            self.bar_inner.remove_style_class("hidden")
