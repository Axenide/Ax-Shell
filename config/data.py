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
else:
    WALLPAPERS_DIR = WALLPAPERS_DIR_DEFAULT

FUZZY_THRESHOLD = 65
