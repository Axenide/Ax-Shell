import json
import os

from fabric.hyprland.service import HyprlandEvent
from fabric.hyprland.widgets import (Language, WorkspaceButton, Workspaces,
                                     get_hyprland_connection)
from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.datetime import DateTime
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from gi.repository import Gdk, Gtk

import config.data as data
import modules.icons as icons
from modules.controls import ControlSmall
from modules.dock import Dock
from modules.metrics import Battery, MetricsSmall, NetworkApplet
from modules.systemtray import SystemTray
from modules.weather import Weather
from widgets.wayland import WaylandWindow as Window

CHINESE_NUMERALS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "〇"]

# Tooltips
tooltip_apps = f"""<b><u>Launcher</u></b>
<b>• Apps:</b> Type to search.

<b>• Calculator [Prefix "="]:</b> Solve a math expression.
  e.g. "=2+2"

<b>• Converter [Prefix ";"]:</b> Convert between units.
  e.g. ";100 USD to EUR", ";10 km to miles"

<b>• Special Commands [Prefix ":"]:</b>
  :update - Open {data.APP_NAME_CAP}'s updater.
  :d - Open Dashboard.
  :w - Open Wallpapers."""

tooltip_power = """<b>Power Menu</b>"""
tooltip_tools = """<b>Toolbox</b>"""
tooltip_overview = """<b>Overview</b>"""


class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="bar",
            layer="top",
            exclusivity="auto",
            visible=True,
            all_visible=True,
        )

        self.anchor_var = ""
        self.margin_var = ""

        match data.BAR_POSITION:
            case "Top":
                self.anchor_var = "left top right"
            case "Bottom":
                self.anchor_var = "left bottom right"
            case "Left":
                self.anchor_var = "left" if data.CENTERED_BAR else "left top bottom"
            case "Right":
                self.anchor_var = "right" if data.CENTERED_BAR else "top right bottom"
            case _:
                self.anchor_var = "left top right"

        if data.VERTICAL:
            match data.BAR_THEME:
                case "Edge":
                    self.margin_var = "-8px -8px -8px -8px"
                case _:
                    self.margin_var = "-4px -8px -4px -4px"
        else:
            match data.BAR_THEME:
                case "Edge":
                    self.margin_var = "-8px -8px -8px -8px"
                case _:
                    if data.BAR_POSITION == "Bottom":
                        self.margin_var = "-8px -4px -4px -4px"
                    else:

                        self.margin_var = "-4px -4px -8px -4px"

        self.set_anchor(self.anchor_var)
        self.set_margin(self.margin_var)

        self.notch = kwargs.get("notch", None)
        self.component_visibility = data.BAR_COMPONENTS_VISIBILITY

        self.dock_instance = None
        self.integrated_dock_widget = None

        self.workspaces = Workspaces(
            name="workspaces",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h" if not data.VERTICAL else "v",
            spacing=8,
            buttons=[
                WorkspaceButton(
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                    id=i,
                    label=None,
                    style_classes=["vertical"] if data.VERTICAL else None,
                )
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
            tooltip_markup=tooltip_tools,
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
        self.network = NetworkApplet()

        self.lang_label = Label(name="lang-label")
        self.language = Button(name="language", h_align="center", v_align="center", child=self.lang_label)
        self.on_language_switch()
        self.connection.connect("event::activelayout", self.on_language_switch)

        # Determine date-time format based on the new setting
        if data.DATETIME_12H_FORMAT:
            time_format_horizontal = "%I:%M %p"
            time_format_vertical = "%I\n%M\n%p"
        else:
            time_format_horizontal = "%H:%M"
            time_format_vertical = "%H\n%M"

        self.date_time = DateTime(
            name="date-time",
            formatters=[time_format_horizontal] if not data.VERTICAL else [time_format_vertical],
            h_align="center" if not data.VERTICAL else "fill",
            v_align="center",
            h_expand=True,
            v_expand=True,
            style_classes=["vertical"] if data.VERTICAL else [],
        )

        self.button_apps = Button(
            name="button-bar",
            tooltip_markup = tooltip_apps,
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
            tooltip_markup=tooltip_power,
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
            tooltip_markup=tooltip_overview,
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
        
        self.apply_component_props()
        
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

        if data.DOCK_ENABLED and data.BAR_POSITION == "Bottom" or data.PANEL_THEME == "Panel" and data.BAR_POSITION in ["Top", "Bottom"]:
            if not data.VERTICAL: 
                self.dock_instance = Dock(integrated_mode=True)
                self.integrated_dock_widget = self.dock_instance.wrapper

        
        is_centered_bar = data.VERTICAL and getattr(data, 'CENTERED_BAR', False)
        
        bar_center_actual_children = None
        
        if self.integrated_dock_widget is not None:
            bar_center_actual_children = self.integrated_dock_widget
        elif data.VERTICAL:
            bar_center_actual_children = Box(
                orientation=Gtk.Orientation.VERTICAL, 
                spacing=4, 
                children=self.v_all_children if is_centered_bar else self.v_center_children
            )

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation=Gtk.Orientation.HORIZONTAL if not data.VERTICAL else Gtk.Orientation.VERTICAL,
            h_align="fill",
            v_align="fill",
            start_children=None if is_centered_bar else Box(
                name="start-container",
                spacing=4,
                orientation=Gtk.Orientation.HORIZONTAL if not data.VERTICAL else Gtk.Orientation.VERTICAL,
                children=self.h_start_children if not data.VERTICAL else self.v_start_children,
            ),
            center_children=bar_center_actual_children,
            end_children=None if is_centered_bar else Box(
                name="end-container",
                spacing=4,
                orientation=Gtk.Orientation.HORIZONTAL if not data.VERTICAL else Gtk.Orientation.VERTICAL,
                children=self.h_end_children if not data.VERTICAL else self.v_end_children,
            ),
        )

        self.children = self.bar_inner

        self.hidden = False

        self.themed_children = [
            self.button_apps,
            self.button_overview,
            self.button_power,
            self.button_tools,
            self.language,
            self.date_time,
            self.ws_container,
            self.weather,
            self.network,
            self.battery,
            self.metrics,
            self.systray,
            self.control,
        ]
        if self.integrated_dock_widget:
            self.themed_children.append(self.integrated_dock_widget)

        current_theme = data.BAR_THEME
        theme_classes = ["pills", "dense", "edge", "edgecenter"]
        for tc in theme_classes:
            self.bar_inner.remove_style_class(tc)
        
        self.style = None
        match current_theme:
            case "Pills":
                self.style = "pills"
            case "Dense":
                self.style = "dense"
            case "Edge":
                if data.VERTICAL and data.CENTERED_BAR:
                    self.style = "edgecenter"
                else:
                    self.style = "edge"
            case _:
                self.style = "pills"

        self.bar_inner.add_style_class(self.style)
        
        if self.integrated_dock_widget and hasattr(self.integrated_dock_widget, 'add_style_class'):

            for theme_class_to_remove in ["pills", "dense", "edge"]:
                style_context = self.integrated_dock_widget.get_style_context()
                if style_context.has_class(theme_class_to_remove):
                    self.integrated_dock_widget.remove_style_class(theme_class_to_remove)
            self.integrated_dock_widget.add_style_class(self.style)

        if data.BAR_THEME == "Dense" or data.BAR_THEME == "Edge":
            for child in self.themed_children:
                if hasattr(child, 'add_style_class'):
                    child.add_style_class("invert")

        match data.BAR_POSITION:
            case "Top":
                self.bar_inner.add_style_class("top")
            case "Bottom":
                self.bar_inner.add_style_class("bottom")
            case "Left":
                self.bar_inner.add_style_class("left")
            case "Right":
                self.bar_inner.add_style_class("right")
            case _:
                self.bar_inner.add_style_class("top")

        if data.VERTICAL:
            self.bar_inner.add_style_class("vertical")

        self.systray._update_visibility()
        self.chinese_numbers()

    def apply_component_props(self):
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
            self.component_visibility[component_name] = not self.component_visibility[component_name]
            components[component_name].set_visible(self.component_visibility[component_name])
            
            config_file = os.path.expanduser(f"~/.config/{data.APP_NAME}/config/config.json")
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    config[f'bar_{component_name}_visible'] = self.component_visibility[component_name]
                    
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=4)
                except Exception as e:
                    print(f"Error updating config file: {e}")
            
            return self.component_visibility[component_name]
        
        return None

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor.new_from_name(widget.get_display(),"hand2"))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def on_button_clicked(self, *args):
        exec_shell_command_async("notify-send 'Botón presionado' '¡Funciona!'")

    def search_apps(self):
        if self.notch: self.notch.open_notch("launcher")

    def overview(self):
        if self.notch: self.notch.open_notch("overview")

    def power_menu(self):
        if self.notch: self.notch.open_notch("power")

    def tools_menu(self):
        if self.notch: self.notch.open_notch("tools")

    def on_language_switch(self, _=None, event: HyprlandEvent=None):
        lang_data = event.data[1] if event and event.data and len(event.data) > 1 else Language().get_label()
        self.language.set_tooltip_text(lang_data)
        if not data.VERTICAL:
            self.lang_label.set_label(lang_data[:3].upper())
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
