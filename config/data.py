import json
import os

import gi

gi.require_version("Gtk", "3.0")
from fabric.utils.helpers import get_relative_path
from gi.repository import Gdk, GLib

APP_NAME = "ax-shell"
APP_NAME_CAP = "Ax-Shell"


PANEL_POSITION_KEY = "panel_position"
PANEL_POSITION_DEFAULT = "Center"
NOTIF_POS_KEY = "notif_pos"
NOTIF_POS_DEFAULT = "Top"

CACHE_DIR = str(GLib.get_user_cache_dir()) + f"/{APP_NAME}"

USERNAME = os.getlogin()
HOSTNAME = os.uname().nodename
HOME_DIR = os.path.expanduser("~")

CONFIG_DIR = os.path.expanduser(f"~/.config/{APP_NAME}")

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()


WALLPAPERS_DIR_DEFAULT = get_relative_path("../assets/wallpapers_example")
CONFIG_FILE = get_relative_path("../config/config.json")
MATUGEN_STATE_FILE = os.path.join(CONFIG_DIR, "matugen")


BAR_WORKSPACE_USE_CHINESE_NUMERALS = False
BAR_THEME = "Pills"

DOCK_THEME = "Pills"

PANEL_THEME = "Notch"
DATETIME_12H_FORMAT = False  # Default value if config file doesn't exist


def load_config():
    """Load the configuration from config.json"""
    config_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/config.json")
    config = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")

    return config


# Import defaults from settings_constants to avoid duplication
from .settings_constants import DEFAULTS

# Load configuration once and use throughout the module
config = {}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")

# Set configuration values using defaults from settings_constants
WALLPAPERS_DIR = config.get("wallpapers_dir", DEFAULTS["wallpapers_dir"])
BAR_POSITION = config.get("bar_position", DEFAULTS["bar_position"])
VERTICAL = BAR_POSITION in ["Left", "Right"]
CENTERED_BAR = config.get("centered_bar", DEFAULTS["centered_bar"])
DATETIME_12H_FORMAT = config.get("datetime_12h_format", DEFAULTS["datetime_12h_format"])
TERMINAL_COMMAND = config.get("terminal_command", DEFAULTS["terminal_command"])
DOCK_ENABLED = config.get("dock_enabled", DEFAULTS["dock_enabled"])
DOCK_ALWAYS_SHOW = config.get("dock_always_show", DEFAULTS["dock_always_show"])
DOCK_ICON_SIZE = config.get("dock_icon_size", DEFAULTS["dock_icon_size"])
BAR_WORKSPACE_SHOW_NUMBER = config.get("bar_workspace_show_number", DEFAULTS["bar_workspace_show_number"])
BAR_WORKSPACE_USE_CHINESE_NUMERALS = config.get("bar_workspace_use_chinese_numerals", DEFAULTS["bar_workspace_use_chinese_numerals"])
BAR_HIDE_SPECIAL_WORKSPACE = config.get("bar_hide_special_workspace", DEFAULTS["bar_hide_special_workspace"])
BAR_THEME = config.get("bar_theme", DEFAULTS["bar_theme"])
DOCK_THEME = config.get("dock_theme", DEFAULTS["dock_theme"])
PANEL_THEME = config.get("panel_theme", DEFAULTS["panel_theme"])

PANEL_POSITION = config.get(PANEL_POSITION_KEY, DEFAULTS[PANEL_POSITION_KEY])
NOTIF_POS = config.get(NOTIF_POS_KEY, DEFAULTS[NOTIF_POS_KEY])

BAR_COMPONENTS_VISIBILITY = {
    "button_apps": config.get("bar_button_apps_visible", DEFAULTS["bar_button_apps_visible"]),
    "systray": config.get("bar_systray_visible", DEFAULTS["bar_systray_visible"]),
    "control": config.get("bar_control_visible", DEFAULTS["bar_control_visible"]),
    "network": config.get("bar_network_visible", DEFAULTS["bar_network_visible"]),
    "button_tools": config.get("bar_button_tools_visible", DEFAULTS["bar_button_tools_visible"]),
    "sysprofiles": config.get("bar_sysprofiles_visible", DEFAULTS["bar_sysprofiles_visible"]),
    "button_overview": config.get("bar_button_overview_visible", DEFAULTS["bar_button_overview_visible"]),
    "ws_container": config.get("bar_ws_container_visible", DEFAULTS["bar_ws_container_visible"]),
    "weather": config.get("bar_weather_visible", DEFAULTS["bar_weather_visible"]),
    "battery": config.get("bar_battery_visible", DEFAULTS["bar_battery_visible"]),
    "metrics": config.get("bar_metrics_visible", DEFAULTS["bar_metrics_visible"]),
    "language": config.get("bar_language_visible", DEFAULTS["bar_language_visible"]),
    "date_time": config.get("bar_date_time_visible", DEFAULTS["bar_date_time_visible"]),
    "button_power": config.get("bar_button_power_visible", DEFAULTS["bar_button_power_visible"]),
}

BAR_METRICS_DISKS = config.get("bar_metrics_disks", DEFAULTS["bar_metrics_disks"])
METRICS_VISIBLE = config.get("metrics_visible", DEFAULTS["metrics_visible"])
METRICS_SMALL_VISIBLE = config.get("metrics_small_visible", DEFAULTS["metrics_small_visible"])
TEMPERATURE_POLL_INTERVAL = config.get('temperature_poll_interval', 1)
SELECTED_MONITORS = config.get("selected_monitors", DEFAULTS["selected_monitors"])
