import setproctitle
import os
from fabric import Application
from fabric.utils import get_relative_path
from modules.bar import Bar
from modules.notch import Notch
from modules.corners import Corners
from config.config import open_config, ensure_fonts
from datetime import datetime

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

config_path = os.path.expanduser("~/.config/Ax-Shell/config/config.json")
fonts_updated_file = os.path.expanduser("~/.cache/ax-shell/fonts_updated")
cache_dir = os.path.expanduser("~/.cache/ax-shell/")

if __name__ == "__main__":
    setproctitle.setproctitle("ax-shell")

    # Check if the current date is after February 25, 2025
    current_date = datetime.now()
    target_date = datetime(2025, 2, 25)

    #Check if fonts_updated file exist, so we dont repeat this part every time.
    if current_date > target_date and not os.path.exists(fonts_updated_file):
        tabler_icons_path = os.path.expanduser("~/.fonts/tabler-icons")
        if os.path.exists(tabler_icons_path):
            import shutil
            try:
                shutil.rmtree(tabler_icons_path)
                print(f"Removed directory: {tabler_icons_path}")
            except Exception as e:
                print(f"Error removing {tabler_icons_path}: {e}")
        ensure_fonts()
        # Create the fonts_updated file to indicate that the process has been done.
        os.makedirs(cache_dir, exist_ok=True)
        with open(fonts_updated_file, "w") as f:
            f.write("Fonts updated after February 25, 2025")

    if not os.path.isfile(config_path):
        open_config()
    corners = Corners()
    bar = Bar()
    notch = Notch()
    bar.notch = notch
    notch.bar = bar
    app = Application("ax-shell", bar, notch)

    def set_css():
        app.set_stylesheet_from_file(
            get_relative_path("main.css"),
            exposed_functions={
                "overview_width": lambda: f"min-width: {CURRENT_WIDTH * 0.1 * 5}px;",
                "overview_height": lambda: f"min-height: {CURRENT_HEIGHT * 0.1 * 2}px;",
            },
        )

    app.set_css = set_css

    app.set_css()

    app.run()
