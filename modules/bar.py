from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.button import Button
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import Workspaces, WorkspaceButton, Language, get_hyprland_connection
import os
import json
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

CHINESE_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "〇"]

class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar",
            layer="top",
            anchor = (
                "left top right"
                if not data.VERTICAL
                else "left" if data.CENTERED_BAR
                else "top left bottom"
            ),
            margin="-4px -4px -8px -4px" if not data.VERTICAL else "-4px -8px -4px -4px",
            exclusivity="auto",
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs.get("notch", None)
        self.component_visibility = data.BAR_COMPONENTS_VISIBILITY

        self.workspaces = Workspaces(
            name="workspaces",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h" if not data.VERTICAL else "v",
            spacing=8,
            # Use data module to determine the label
            buttons=[
                WorkspaceButton(id=i, label=None)
                for i in range(1, 11)
            ],
        )

        self.workspaces_num = Workspaces(
            name="workspaces-num",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h" if not data.VERTICAL else "v",
            spacing=0 if not data.BAR_WORKSPACE_USE_CHINESE_NUMERALS else 4,
            buttons=[
                WorkspaceButton(
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                    id=i,
                    label= CHINESE_NUMERALS[i-1] if data.BAR_WORKSPACE_USE_CHINESE_NUMERALS and 1 <= i <= len(CHINESE_NUMERALS) else str(i)
                )
                for i in range(1, 11)
            ],
        )

        self.ws_container = Box(
            name="workspaces-container",
            children=self.workspaces if not data.BAR_WORKSPACE_SHOW_NUMBER else self.workspaces_num,
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

        self.lang_label = Label(name="lang-label")
        self.language = Button(name="language", h_align="center", v_align="center", child=self.lang_label)
        self.on_language_switch()
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
        
        # Apply visibility settings to components
        self.apply_component_visibility()
        
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

        # Use centered layout when both vertical and centered_bar are enabled
        is_centered_bar = data.VERTICAL and getattr(data, 'CENTERED_BAR', False)
        
        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation="h" if not data.VERTICAL else "v",
            h_align="fill",
            v_align="fill",
            start_children=None if is_centered_bar else Box(
                name="start-container",
                spacing=4,
                orientation="h" if not data.VERTICAL else "v",
                children=self.h_start_children if not data.VERTICAL else self.v_start_children,
            ),
            center_children=Box(
                orientation="v", 
                spacing=4, 
                children=self.v_all_children if is_centered_bar else self.v_center_children
            ) if data.VERTICAL else None,
            end_children=None if is_centered_bar else Box(
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
        self.chinese_numbers()

    def apply_component_visibility(self):
        """Apply saved visibility settings to all components"""
        components = {
            'button_apps': self.button_apps,
            'systray': self.systray,
            'control': self.control,
            'network': self.network,
            'button_tools': self.button_tools,
            'button_overview': self.button_overview,
            'ws_container': self.ws_container,
            'weather': self.weather,
            'battery': self.battery,
            'metrics': self.metrics,
            'language': self.language,
            'date_time': self.date_time,
            'button_power': self.button_power,
        }
        
        for component_name, widget in components.items():
            if component_name in self.component_visibility:
                widget.set_visible(self.component_visibility[component_name])
    
    def toggle_component_visibility(self, component_name):
        """Toggle visibility for a specific component"""
        components = {
            'button_apps': self.button_apps,
            'systray': self.systray,
            'control': self.control,
            'network': self.network,
            'button_tools': self.button_tools,
            'button_overview': self.button_overview,
            'ws_container': self.ws_container,
            'weather': self.weather,
            'battery': self.battery,
            'metrics': self.metrics,
            'language': self.language,
            'date_time': self.date_time,
            'button_power': self.button_power,
        }
        
        if component_name in components and component_name in self.component_visibility:
            # Toggle the visibility state
            self.component_visibility[component_name] = not self.component_visibility[component_name]
            # Apply the new state
            components[component_name].set_visible(self.component_visibility[component_name])
            
            # Update the configuration
            config_file = os.path.expanduser(f"~/.config/{data.APP_NAME}/config/config.json")
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Update the config with the new visibility state
                config[f'bar_{component_name}_visible'] = self.component_visibility[component_name]
                
                with open(config_file, 'w') as f:
                    json.dump(config, f)
            
            return self.component_visibility[component_name]
        
        return None

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

    def on_language_switch(self, _=None, event: HyprlandEvent=None):
        lang = event.data[1] if event else Language().get_label()
        self.language.set_tooltip_text(lang)
        if not data.VERTICAL:
            self.lang_label.set_label(lang[:3].upper())
        else:
            self.lang_label.add_style_class("icon")
            self.lang_label.set_markup(icons.keyboard)
            
    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.bar_inner.add_style_class("hidden")
        else:
            self.bar_inner.remove_style_class("hidden")

    def chinese_numbers(self):
        if data.BAR_WORKSPACE_USE_CHINESE_NUMERALS:
            self.workspaces_num.add_style_class("chinese")
        else:
            self.workspaces_num.remove_style_class("chinese")
