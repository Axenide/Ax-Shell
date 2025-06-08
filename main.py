import os

import gi

gi.require_version("GLib", "2.0")
import setproctitle
from fabric import Application
from fabric.utils import exec_shell_command_async, get_relative_path
from gi.repository import GLib

from config.data import APP_NAME, APP_NAME_CAP, CACHE_DIR, CONFIG_FILE, HOME_DIR
from modules.bar import Bar
from modules.corners import Corners
from modules.dock import Dock
from modules.notch import Notch
from modules.notifications import NotificationPopup
from modules.updater import run_updater

fonts_updated_file = f"{CACHE_DIR}/fonts_updated"

if __name__ == "__main__":
    setproctitle.setproctitle(APP_NAME)

    if not os.path.isfile(CONFIG_FILE):
        config_script_path = get_relative_path("config/config.py")
        exec_shell_command_async(f"python {config_script_path}")

    current_wallpaper = os.path.expanduser("~/.current.wall")
    if not os.path.exists(current_wallpaper):
        example_wallpaper = os.path.expanduser(
            f"~/.config/{APP_NAME_CAP}/assets/wallpapers_example/example-1.jpg"
        )
        os.symlink(example_wallpaper, current_wallpaper)

    # Load configuration
    from config.data import load_config

    config = load_config()

    GLib.idle_add(run_updater)
    # Every hour
    GLib.timeout_add(3600000, run_updater)

    corners = Corners()
    bar = Bar()
    notch = Notch()
    dock = Dock()
    bar.notch = notch
    notch.bar = bar
    notification = NotificationPopup(widgets=notch.dashboard.widgets)

    # Set corners visibility based on config
    corners_visible = config.get("corners_visible", True)
    corners.set_visible(corners_visible)

    app = Application(
        f"{APP_NAME}", bar, notch, dock, notification, corners
    )  # Make sure corners is added to the app

    def set_css():
        app.set_stylesheet_from_file(
            get_relative_path("main.css"),
        )

    app.set_css = set_css

    app.set_css()

    app.run()
