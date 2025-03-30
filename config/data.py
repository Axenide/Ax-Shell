import os
import json
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib

from fabric.utils.helpers import get_relative_path

APP_NAME = "ax-shell"
APP_NAME_CAP = "Ax-Shell"

CACHE_DIR = str(GLib.get_user_cache_dir()) + f"/{APP_NAME}"

USERNAME = os.getlogin()
HOSTNAME = os.uname().nodename
HOME_DIR = os.path.expanduser("~")

CONFIG_DIR = os.path.expanduser(f"~/.config/{APP_NAME}")

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

# Rename to match what's being imported in config.py
WALLPAPERS_DIR_DEFAULT = get_relative_path("../assets/wallpapers_example")
CONFIG_FILE = get_relative_path('../config/config.json')

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    WALLPAPERS_DIR = config.get('wallpapers_dir', WALLPAPERS_DIR_DEFAULT)
    VERTICAL = config.get('vertical', False)  # Use saved value or False as default
    CENTERED_BAR = config.get('centered_bar', False)  # Load centered bar setting
    TERMINAL_COMMAND = config.get('terminal_command', "kitty -e")  # Load terminal command
    DOCK_ENABLED = config.get('dock_enabled', True)  # Load dock visibility setting
    DOCK_ALWAYS_OCCLUDED = config.get('dock_always_occluded', False)  # Load dock hover-only setting
    DOCK_ICON_SIZE = config.get('dock_icon_size', 28)  # Load dock icon size setting
    
    # Load bar component visibility settings
    BAR_COMPONENTS_VISIBILITY = {
        'button_apps': config.get('bar_button_apps_visible', True),
        'systray': config.get('bar_systray_visible', True),
        'control': config.get('bar_control_visible', True),
        'network': config.get('bar_network_visible', True),
        'button_tools': config.get('bar_button_tools_visible', True),
        'button_overview': config.get('bar_button_overview_visible', True),
        'ws_container': config.get('bar_ws_container_visible', True),
        'weather': config.get('bar_weather_visible', True),
        'battery': config.get('bar_battery_visible', True),
        'metrics': config.get('bar_metrics_visible', True),
        'language': config.get('bar_language_visible', True),
        'date_time': config.get('bar_date_time_visible', True),
        'button_power': config.get('bar_button_power_visible', True),
    }
else:
    WALLPAPERS_DIR = WALLPAPERS_DIR_DEFAULT
    VERTICAL = False  # Default value when no config exists
    CENTERED_BAR = False  # Default value for centered bar
    DOCK_ENABLED = True  # Default value for dock visibility
    DOCK_ALWAYS_OCCLUDED = False  # Default value for dock hover-only mode
    TERMINAL_COMMAND = "kitty -e"  # Default terminal command when no config
    DOCK_ICON_SIZE = 28  # Default dock icon size when no config
    
    # Default values for component visibility (all visible)
    BAR_COMPONENTS_VISIBILITY = {
        'button_apps': True,
        'systray': True,
        'control': True,
        'network': True,
        'button_tools': True,
        'button_overview': True,
        'ws_container': True,
        'weather': True,
        'battery': True,
        'metrics': True,
        'language': True,
        'date_time': True,
        'button_power': True,
    }
