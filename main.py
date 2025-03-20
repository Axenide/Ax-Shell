import os
import setproctitle

from fabric import Application
from fabric.utils import get_relative_path, exec_shell_command_async

from config.data import APP_NAME, CACHE_DIR, CONFIG_FILE, DOCK_ICON_SIZE
from modules.bar import Bar
from modules.corners import Corners
from modules.dock import Dock
from modules.notch import Notch

fonts_updated_file = f"{CACHE_DIR}/fonts_updated"

if __name__ == "__main__":
    setproctitle.setproctitle(APP_NAME)

    if not os.path.isfile(CONFIG_FILE):
        exec_shell_command_async(f"python {get_relative_path('../config/config.py')}")
    corners = Corners()
    bar = Bar()
    notch = Notch()
    dock = Dock() 
    bar.notch = notch
    notch.bar = bar
    app = Application(f"{APP_NAME}", bar, notch, dock)

    def set_css():
        from config.data import CURRENT_WIDTH, CURRENT_HEIGHT
        app.set_stylesheet_from_file(
            get_relative_path("main.css"),
            exposed_functions={
                "overview_width": lambda: f"min-width: {CURRENT_WIDTH * 0.1 * 5 + 92}px;",
                "overview_height": lambda: f"min-height: {CURRENT_HEIGHT * 0.1 * 2 + 32 + 56}px;",
                "dock_nmargin": lambda: f"margin-bottom: -{28 + DOCK_ICON_SIZE}px;",
            },
        )
    app.set_css = set_css

    app.set_css()

    app.run()
