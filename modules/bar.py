import json
import os

from fabric.hyprland.service import HyprlandEvent
from fabric.hyprland.widgets import (
    Language,
    WorkspaceButton,
    Workspaces,
    get_hyprland_connection,
)
from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.datetime import DateTime
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from gi.repository import Gdk, Gtk, GLib

import config.data as data
import modules.icons as icons
from modules.controls import ControlSmall
from modules.metrics import Battery, MetricsSmall, NetworkApplet
from modules.systemprofiles import Systemprofiles
from modules.systemtray import SystemTray
from modules.weather import Weather
from widgets.wayland import WaylandWindow as Window

import logging


logger = logging.getLogger(__name__)

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


def build_caption(i: int):
    """Build the label for a given workspace number"""
    label = data.BAR_WORKSPACE_ICONS.get(str(i)) or data.BAR_WORKSPACE_ICONS.get(
        "default"
    )
    if label is None:
        return (
            CHINESE_NUMERALS[i - 1]
            if data.BAR_WORKSPACE_USE_CHINESE_NUMERALS
            and 1 <= i <= len(CHINESE_NUMERALS)
            else str(i)
        )
    else:
        return label


class Bar(Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "bar"
        self.layer = "top"
        self.exclusivity = "auto"
        self.visible = True
        self.all_visible = True

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
            buttons_factory=(
                None
                if data.BAR_HIDE_SPECIAL_WORKSPACE
                else Workspaces.default_buttons_factory
            ),
        )

        self.workspaces_num = Workspaces(
            name="workspaces-num",
            invert_scroll=True,
            empty_scroll=True,
            v_align="fill",
            orientation="h" if not data.VERTICAL else "v",
            spacing=(4 if data.BAR_WORKSPACE_USE_CHINESE_NUMERALS else 0),
            buttons=[
                WorkspaceButton(
                    h_expand=False,
                    v_expand=False,
                    h_align="center",
                    v_align="center",
                    id=i,
                    label=build_caption(i),
                )
                for i in range(1, 11)
            ],
            buttons_factory=(
                None
                if data.BAR_HIDE_SPECIAL_WORKSPACE
                else Workspaces.default_buttons_factory
            ),
        )
        self.ws_rail = Box(name="workspace-rail", h_align="start", v_align="center")
        self.current_rail_pos = 0
        self.current_rail_size = 0
        self.is_animating_rail = False
        self.ws_rail_provider = Gtk.CssProvider()
        self.ws_rail.get_style_context().add_provider(
            self.ws_rail_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        # Add initial styling for the rail
        initial_css = """
        #workspace-rail {
            background-color: rgba(255, 0, 0, 0.7);
            border-radius: 999px;
        }
        """
        self.ws_rail_provider.load_from_data(initial_css.encode())
        logger.warning(f"Initialized workspace rail with vertical={data.VERTICAL}")

        workspaces_widget = (
            self.workspaces_num
            if data.BAR_WORKSPACE_SHOW_NUMBER or data.BAR_WORKSPACE_ICONS
            else self.workspaces
        )

        self.ws_container = Gtk.Grid()
        self.ws_container.attach(self.ws_rail, 0, 0, 1, 1)
        self.ws_container.attach(workspaces_widget, 0, 0, 1, 1)
        self.ws_container.set_name("workspaces-container")

        self.button_tools = Button(
            name="button-bar",
            tooltip_markup=tooltip_tools,
            on_clicked=lambda *_: self.tools_menu(),
            child=Label(name="button-bar-label", markup=icons.toolbox),
        )

        self.connection = get_hyprland_connection()
        self.button_tools.connect("enter_notify_event", self.on_button_enter)
        self.button_tools.connect("leave_notify_event", self.on_button_leave)

        self.connection.connect("event::workspace", self._on_workspace_changed)

        self.systray = SystemTray()

        self.weather = Weather()
        self.sysprofiles = Systemprofiles()

        self.network = NetworkApplet()

        self.lang_label = Label(name="lang-label")
        self.language = Button(
            name="language", h_align="center", v_align="center", child=self.lang_label
        )
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
            formatters=(
                [time_format_horizontal]
                if not data.VERTICAL
                else [time_format_vertical]
            ),
            h_align="center" if not data.VERTICAL else "fill",
            v_align="center",
            h_expand=True,
            v_expand=True,
            style_classes=["vertical"] if data.VERTICAL else [],
        )

        self.button_apps = Button(
            name="button-bar",
            tooltip_markup=tooltip_apps,
            on_clicked=lambda *_: self.search_apps(),
            child=Label(name="button-bar-label", markup=icons.apps),
        )
        self.button_apps.connect("enter_notify_event", self.on_button_enter)
        self.button_apps.connect("leave_notify_event", self.on_button_leave)

        self.button_power = Button(
            name="button-bar",
            tooltip_markup=tooltip_power,
            on_clicked=lambda *_: self.power_menu(),
            child=Label(name="button-bar-label", markup=icons.shutdown),
        )
        self.button_power.connect("enter_notify_event", self.on_button_enter)
        self.button_power.connect("leave_notify_event", self.on_button_leave)

        self.button_overview = Button(
            name="button-bar",
            tooltip_markup=tooltip_overview,
            on_clicked=lambda *_: self.overview(),
            child=Label(name="button-bar-label", markup=icons.windows),
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
            self.sysprofiles,
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
            self.sysprofiles,
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

        is_centered_bar = data.VERTICAL and getattr(data, "CENTERED_BAR", False)
        bar_center_actual_children = None
        if self.integrated_dock_widget is not None:
            bar_center_actual_children = self.integrated_dock_widget
        elif data.VERTICAL:
            bar_center_actual_children = Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=4,
                children=(
                    self.v_start_children + self.v_center_children + self.v_end_children
                    if is_centered_bar
                    else self.v_center_children
                ),
            )

        self.bar_inner = CenterBox(
            name="bar-inner",
            orientation=(
                Gtk.Orientation.HORIZONTAL
                if not data.VERTICAL
                else Gtk.Orientation.VERTICAL
            ),
            h_align="fill",
            v_align="fill",
            start_children=(
                None
                if is_centered_bar
                else Box(
                    name="start-container",
                    spacing=4,
                    orientation=(
                        Gtk.Orientation.HORIZONTAL
                        if not data.VERTICAL
                        else Gtk.Orientation.VERTICAL
                    ),
                    children=(
                        self.h_start_children
                        if not data.VERTICAL
                        else (
                            self.v_all_children
                            if is_centered_bar
                            else self.v_start_children
                        )
                    ),
                )
            ),
            center_children=bar_center_actual_children,
            end_children=(
                None
                if is_centered_bar
                else Box(
                    name="end-container",
                    spacing=4,
                    orientation=(
                        Gtk.Orientation.HORIZONTAL
                        if not data.VERTICAL
                        else Gtk.Orientation.VERTICAL
                    ),
                    children=(
                        self.h_end_children
                        if not data.VERTICAL
                        else self.v_end_children
                    ),
                )
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

        if self.integrated_dock_widget and hasattr(
            self.integrated_dock_widget, "add_style_class"
        ):
            for theme_class_to_remove in ["pills", "dense", "edge"]:
                style_context = self.integrated_dock_widget.get_style_context()
                if style_context.has_class(theme_class_to_remove):
                    self.integrated_dock_widget.remove_style_class(
                        theme_class_to_remove
                    )
            self.integrated_dock_widget.add_style_class(self.style)

        if data.BAR_THEME == "Dense" or data.BAR_THEME == "Edge":
            for child in self.themed_children:
                if hasattr(child, "add_style_class"):
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

        self.setup_workspaces()

    def apply_component_props(self):
        components = {
            "button_apps": self.button_apps,
            "systray": self.systray,
            "control": self.control,
            "network": self.network,
            "button_tools": self.button_tools,
            "button_overview": self.button_overview,
            "ws_container": self.ws_container,
            "weather": self.weather,
            "battery": self.battery,
            "metrics": self.metrics,
            "language": self.language,
            "date_time": self.date_time,
            "button_power": self.button_power,
            "sysprofiles": self.sysprofiles,
        }

        for component_name, widget in components.items():
            if component_name in self.component_visibility:
                widget.set_visible(self.component_visibility[component_name])

    def toggle_component_visibility(self, component_name):
        components = {
            "button_apps": self.button_apps,
            "systray": self.systray,
            "control": self.control,
            "network": self.network,
            "button_tools": self.button_tools,
            "button_overview": self.button_overview,
            "ws_container": self.ws_container,
            "weather": self.weather,
            "battery": self.battery,
            "metrics": self.metrics,
            "language": self.language,
            "date_time": self.date_time,
            "button_power": self.button_power,
            "sysprofiles": self.sysprofiles,
        }

        if component_name in components and component_name in self.component_visibility:
            self.component_visibility[component_name] = not self.component_visibility[
                component_name
            ]
            components[component_name].set_visible(
                self.component_visibility[component_name]
            )

            config_file = os.path.expanduser(
                f"~/.config/{data.APP_NAME}/config/config.json"
            )
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        config = json.load(f)

                    config[f"bar_{component_name}_visible"] = self.component_visibility[
                        component_name
                    ]

                    with open(config_file, "w") as f:
                        json.dump(config, f, indent=4)
                except Exception as e:
                    logger.warning(f"Error updating config file: {e}")

            return self.component_visibility[component_name]

        return None

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor.new_from_name(widget.get_display(), "hand2"))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def on_button_clicked(self, *args):
        exec_shell_command_async("notify-send 'Botón presionado' '¡Funciona!'")

    def search_apps(self):
        if self.notch:
            self.notch.open_notch("launcher")

    def overview(self):
        if self.notch:
            self.notch.open_notch("overview")

    def power_menu(self):
        if self.notch:
            self.notch.open_notch("power")

    def tools_menu(self):
        if self.notch:
            self.notch.open_notch("tools")

    def on_language_switch(self, _=None, event: HyprlandEvent = None):
        lang_data = (
            event.data[1]
            if event and event.data and len(event.data) > 1
            else Language().get_label()
        )
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
        if data.BAR_WORKSPACE_USE_CHINESE_NUMERALS or data.BAR_WORKSPACE_ICONS:
            self.workspaces_num.add_style_class("chinese")
        else:
            self.workspaces_num.remove_style_class("chinese")

    def setup_workspaces(self):
        """Set up workspace rail and initialize with current workspace"""
        logger.info("Setting up workspaces")
        try:
            active_workspace = json.loads(
                self.connection.send_command("j/activeworkspace").reply.decode()
            )["id"]
            self.update_rail(active_workspace, initial_setup=True)
        except Exception as e:
            logger.error(f"Error initializing workspace rail: {e}")

    def _on_workspace_changed(self, _, event):
        """Handle workspace change events directly"""
        if event is not None and isinstance(event, HyprlandEvent) and event.data:
            try:
                workspace_id = int(event.data[0])
                logger.info(f"Workspace changed to: {workspace_id}")
                self.update_rail(workspace_id)
            except (ValueError, IndexError) as e:
                logger.error(f"Error processing workspace event: {e}")
        else:
            logger.warning(f"Invalid workspace event received: {event}")

    def update_rail(self, workspace_id, initial_setup=False):
        """Update the workspace rail position based on the workspace button"""
        if self.is_animating_rail and not initial_setup:
            return

        logger.info(f"Updating rail for workspace {workspace_id}")
        workspaces = self.children_workspaces
        active_button = next(
            (
                b
                for b in workspaces
                if isinstance(b, WorkspaceButton) and b.id == workspace_id
            ),
            None,
        )

        if not active_button:
            logger.warning(f"No button found for workspace {workspace_id}")
            return

        if initial_setup:
            GLib.idle_add(self._position_rail_initially, active_button)
        else:
            self.is_animating_rail = True
            GLib.idle_add(self._update_rail_with_animation, active_button)

    def _position_rail_initially(self, active_button):
        allocation = active_button.get_allocation()
        if allocation.width == 0 or allocation.height == 0:
            return True

        diameter = 1
        if data.VERTICAL:
            self.current_rail_pos = (
                allocation.y + (allocation.height / 2) - (diameter / 2)
            )
            self.current_rail_size = diameter
            css = f"""
            #workspace-rail {{
                transition-property: none;
                margin-top: {self.current_rail_pos}px;
                min-height: {self.current_rail_size}px;
                min-width: {self.current_rail_size}px;
            }}
            """
        else:
            self.current_rail_pos = (
                allocation.x + (allocation.width / 2) - (diameter / 2)
            )
            self.current_rail_size = diameter
            css = f"""
            #workspace-rail {{
                transition-property: none;
                margin-left: {self.current_rail_pos}px;
                min-width: {self.current_rail_size}px;
                min-height: {self.current_rail_size}px;
            }}
            """
        self.ws_rail_provider.load_from_data(css.encode())
        logger.info(
            f"Rail initialized at pos={self.current_rail_pos}, size={self.current_rail_size}"
        )
        return False

    def _update_rail_with_animation(self, active_button):
        """Position the rail at the active workspace button with a stretch animation."""
        target_allocation = active_button.get_allocation()

        if target_allocation.width == 0 or target_allocation.height == 0:
            logger.info("Button allocation not ready, retrying...")
            self.is_animating_rail = False
            return True

        diameter = 24
        if data.VERTICAL:
            pos_prop, size_prop = "margin-top", "min-height"
            target_pos = (
                target_allocation.y + (target_allocation.height / 2) - (diameter / 2)
            )
        else:
            pos_prop, size_prop = "margin-left", "min-width"
            target_pos = (
                target_allocation.x + (target_allocation.width / 2) - (diameter / 2)
            )

        if target_pos == self.current_rail_pos:
            self.is_animating_rail = False
            return False

        distance = target_pos - self.current_rail_pos
        stretched_size = self.current_rail_size + abs(distance)
        stretch_pos = target_pos if distance < 0 else self.current_rail_pos

        stretch_duration = 0.1
        shrink_duration = 0.15

        reduced_diameter = max(2, int(diameter - abs(distance / 10.0)))

        if data.VERTICAL:
            other_size_prop, other_size_val = "min-width", reduced_diameter
        else:
            other_size_prop, other_size_val = "min-height", reduced_diameter

        stretch_css = f"""
        #workspace-rail {{
            transition-property: {pos_prop}, {size_prop};
            transition-duration: {stretch_duration}s;
            transition-timing-function: ease-out;
            {pos_prop}: {stretch_pos}px;
            {size_prop}: {stretched_size}px;
            {other_size_prop}: {other_size_val}px;
        }}
        """
        self.ws_rail_provider.load_from_data(stretch_css.encode())

        GLib.timeout_add(
            int(stretch_duration * 1000),
            self._shrink_rail,
            target_pos,
            diameter,
            shrink_duration,
        )
        return False

    def _shrink_rail(self, target_pos, target_size, duration):
        """Shrink the rail to its final size and position."""
        if data.VERTICAL:
            pos_prop = "margin-top"
            size_props = "min-height, min-width"
        else:
            pos_prop = "margin-left"
            size_props = "min-width, min-height"

        shrink_css = f"""
        #workspace-rail {{
            transition-property: {pos_prop}, {size_props};
            transition-duration: {duration}s;
            transition-timing-function: cubic-bezier(0.34, 1.56, 0.64, 1);
            {pos_prop}: {target_pos}px;
            min-width: {target_size}px;
            min-height: {target_size}px;
        }}
        """
        self.ws_rail_provider.load_from_data(shrink_css.encode())

        GLib.timeout_add(
            int(duration * 1000),
            self._finalize_rail_animation,
            target_pos,
            target_size,
        )
        return False

    def _finalize_rail_animation(self, final_pos, final_size):
        """Finalize animation and update state."""
        self.current_rail_pos = final_pos
        self.current_rail_size = final_size
        self.is_animating_rail = False
        logger.info(
            f"Rail animation finished at pos={self.current_rail_pos}, size={self.current_rail_size}"
        )
        return False

    def _update_rail_position(self, active_button):
        """Position the rail at the active workspace button"""
        allocation = active_button.get_allocation()

        # If button isn't properly allocated yet, try again later
        if allocation.width == 0 or allocation.height == 0:
            logger.info("Button allocation not ready, retrying...")
            return True  # Keep retrying

        # Get the current position information to preserve it
        current_css = self.ws_rail.get_style_context().get_property(
            "margin-top" if data.VERTICAL else "margin-left", Gtk.StateFlags.NORMAL
        )

        # A trick to force animation: use a very short transition duration first
        if data.VERTICAL:
            css_preserve = f"""
            #workspace-rail {{
                transition-property: margin-top;
                transition-duration: 0.001s;
                margin-top: {current_css.value}px;
                min-height: {allocation.height}px;
                min-width: {allocation.width}px;
            }}
            """
        else:
            css_preserve = f"""
            #workspace-rail {{
                transition-property: margin-left;
                transition-duration: 0.001s;
                margin-left: {current_css.value}px;
                min-width: {allocation.width}px;
                min-height: {allocation.height}px;
            }}
            """

        # Apply the preservation CSS
        self.ws_rail_provider.load_from_data(css_preserve.encode())

        # Force a redraw and let the short transition complete
        self.ws_rail.queue_draw()

        # Now add a small delay before applying the actual transition and new position
        GLib.timeout_add(10, self._apply_rail_transition, active_button, allocation)

        return False  # Don't call again

    def _apply_rail_transition(self, active_button, allocation):
        """Apply the transition with proper timing"""
        # Set CSS for either vertical or horizontal orientation with transition
        if data.VERTICAL:
            css = f"""
            #workspace-rail {{
                transition-property: margin-top;
                transition-duration: 0.15s;
                transition-timing-function: ease-out;
                margin-top: {allocation.y}px;
                min-height: {allocation.height}px;
                min-width: {allocation.width}px;
            }}
            """
        else:
            css = f"""
            #workspace-rail {{
                transition-property: margin-left;
                transition-duration: 0.15s;
                transition-timing-function: ease-out;
                margin-left: {allocation.x}px;
                min-width: {allocation.width}px;
                min-height: {allocation.height}px;
            }}
            """

        # Apply the CSS with transition
        self.ws_rail_provider.load_from_data(css.encode())
        logger.info(f"Rail animating to x={allocation.x}, y={allocation.y}")

        return False  # Don't call again

    @property
    def children_workspaces(self):
        workspaces_widget = None
        for child in self.ws_container.get_children():
            if isinstance(child, Workspaces):
                workspaces_widget = child
                break

        if workspaces_widget:
            try:
                # The structure is Workspaces -> internal Box -> Buttons
                internal_box = workspaces_widget.get_children()[0]
                return internal_box.get_children()
            except (IndexError, AttributeError):
                logger.error(
                    "Failed to get workspace buttons due to unexpected widget structure."
                )
                return []

        logger.warning("Could not find the Workspaces widget in the container.")
        return []

    def _update_rail_idle(self, workspaces, button_id):
        # Log initial state
        logger.info(f"[Bar] Rail update idle for workspace {button_id}")

        active_button = next(
            (
                b
                for b in workspaces
                if isinstance(b, WorkspaceButton) and b.id == button_id
            ),
            None,
        )

        logger.warning(
            f"Active button {active_button} for workspace {button_id} {workspaces}"
        )

        if not active_button:
            logger.warning(f"[Bar] No active button found for workspace {button_id}")
            return GLib.SOURCE_REMOVE

        allocation = active_button.get_allocation()
        if allocation.width == 0:
            logger.info(
                f"[Bar] Button allocation width is 0 for workspace {button_id}, retrying..."
            )
            return True  # Retry

        # Log allocation values
        logger.info(
            f"[Bar] Button allocation: x={allocation.x}, y={allocation.y}, width={allocation.width}, height={allocation.height}"
        )

        # Handle vertical vs horizontal orientation differently
        if data.VERTICAL:
            logger.info("[Bar] Using vertical CSS positioning")
            css = f"""
            #workspace-rail {{
                transition-duration: 0.15s;
                margin-top: {allocation.y}px;
                min-height: {allocation.height}px;
                min-width: {allocation.width}px;
            }}
            """
        else:
            logger.info("[Bar] Using horizontal CSS positioning")
            css = f"""
            #workspace-rail {{
                transition-duration: 0.15s;
                margin-left: {allocation.x}px;
                min-width: {allocation.width}px;
                min-height: {allocation.height}px;
            }}
            """

        logger.info(f"[Bar] Applying CSS: {css}")
        self.ws_rail_provider.load_from_data(css.encode())

        # Check the style properties after applying
        style_context = self.ws_rail.get_style_context()
        logger.info(f"[Bar] Rail style classes: {list(style_context.list_classes())}")

        return GLib.SOURCE_REMOVE
