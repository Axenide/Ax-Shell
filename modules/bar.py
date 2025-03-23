from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import Workspaces, WorkspaceButton, Language, get_hyprland_connection
from fabric.hyprland.service import HyprlandEvent
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import Gdk
from modules.systemtray import SystemTray
import modules.icons as icons
import config.data as data
from modules.metrics import MetricsSmall, Battery, NetworkApplet
from modules.controls import ControlSmall
from modules.weather import Weather
from modules.cgmsugar import SmallCgm

class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar",
            layer="top",
            anchor="left top right" if not data.VERTICAL else "top left bottom",
            margin="-4px -4px -8px -4px" if not data.VERTICAL else "-4px -8px -4px -4px",
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
            orientation="h" if not data.VERTICAL else "v",
            spacing=8,
            buttons=[WorkspaceButton(id=i, label="") for i in range(1, 11)],
        )
        
        self.ws_container = Box(
            name="workspaces-container",
            children=self.workspaces,
        )

        self.button_tools = Button(
            name="button-bar",
            on_clicked=lambda *_: self.tools_menu(),
            child=Label(
                name="button-bar-label",
                markup=icons.toolbox
            )
        )

        self.connection = get_hyprland_connection()
        self.button_tools.connect("enter_notify_event", self.on_button_enter)
        self.button_tools.connect("leave_notify_event", self.on_button_leave)

        self.systray = SystemTray()
        self.weather = Weather()
        self.smallcgm = SmallCgm()
        self.network = NetworkApplet()
        # self.systray = SystemTray(name="systray", spacing=8, icon_size=20)

        self.lang_label = Label(name="lang-label")
        self.language = Button(name="language", h_align="center", v_align="center", child=self.lang_label)
        self.switch_on_start()
        self.connection.connect("event::activelayout", self.on_language_switch)

        self.date_time = DateTime(name="date-time", formatters=["%H:%M"] if not data.VERTICAL else ["%H\n%M"], h_align="center" if not data.VERTICAL else "fill", v_align="center", h_expand=True, v_expand=True)

        self.button_apps = Button(
            name="button-bar",
            on_clicked=lambda *_: self.search_apps(),
            child=Label(
                name="button-bar-label",
                markup=icons.amongus
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
        
        self.rev_right = [
            self.metrics,
            self.control,
        ]

        self.revealer_right = Revealer(
            name="bar-revealer",
            transition_type="slide-left",
            child_revealed=True,
            child=Box(
                name="bar-revealer-box",
                orientation="h",
                spacing=4,
                children=self.rev_right if not data.VERTICAL else None,
            ),
        )
        
        self.boxed_revealer_right = Box(
            name="boxed-revealer",
            children=[
                self.revealer_right,
            ],
        )
        
        self.rev_left = [
            self.weather,
            self.network,
            self.smallcgm,
        ]

        self.revealer_left = Revealer(
            name="bar-revealer",
            transition_type="slide-right",
            child_revealed=True,
            child=Box(
                name="bar-revealer-box",
                orientation="h",
                spacing=4,
                children=self.rev_left if not data.VERTICAL else None,
            ),
        )

        self.boxed_revealer_left = Box(
            name="boxed-revealer",
            children=[
                self.revealer_left,
            ],
        )
        
        self.h_start_children = [
            self.button_apps,
            self.ws_container,
            self.button_overview,
            self.boxed_revealer_left,
        ]
        
        self.h_end_children = [
            self.boxed_revealer_right,
            self.battery,
            self.systray,
            self.button_tools,
            self.language,
            self.date_time,
            self.button_power,
        ]
        
        self.v_start_children = [
            self.button_apps,
            self.systray,
            self.control,
            self.network,
            self.button_tools,
        ]
        
        self.v_center_children = [
            self.button_overview,
            self.ws_container,
            self.weather,
        ]
        
        self.v_end_children = [
            self.battery,
            self.metrics,
            self.language,
            self.date_time,
            self.button_power,
        ]
        
        self.v_all_children = []
        self.v_all_children.extend(self.v_start_children)
        self.v_all_children.extend(self.v_center_children)
        self.v_all_children.extend(self.v_end_children)

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation="h" if not data.VERTICAL else "v",
            h_align="fill",
            v_align="fill",
            start_children=Box(
                name="start-container",
                spacing=4,
                orientation="h" if not data.VERTICAL else "v",
                children=self.h_start_children if not data.VERTICAL else self.v_start_children,
            ),
            center_children=None if not data.VERTICAL else Box(orientation="v", spacing=4, children=self.v_center_children),
            end_children=Box(
                name="end-container",
                spacing=4,
                orientation="h" if not data.VERTICAL else "v",
                children=self.h_end_children if not data.VERTICAL else self.v_end_children,
            ),
        )

        self.children = self.bar_inner

        self.hidden = False

        # self.show_all()
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

    def on_language_switch(self, _, event: HyprlandEvent):
        self.language.set_tooltip_text(Language().get_label())
        if not data.VERTICAL:
            self.lang_label.set_label(Language().get_label()[0:3].upper())
        else:
            self.lang_label.add_style_class("icon")
            self.lang_label.set_markup(icons.keyboard)

    def switch_on_start(self):
        self.language.set_tooltip_text(Language().get_label())
        if not data.VERTICAL:
            self.lang_label.set_label(Language().get_label()[0:3].upper())
        else:
            self.lang_label.add_style_class("icon")
            self.lang_label.set_markup(icons.keyboard)

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.bar_inner.add_style_class("hidden")
        else:
            self.bar_inner.remove_style_class("hidden")
