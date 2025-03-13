import setproctitle
import os
from fabric import Application
from fabric.utils import get_relative_path, exec_shell_command_async
from modules.bar import Bar
from modules.notch import Notch
from modules.dock import Dock
from modules.corners import Corners
import config.data as data
import json

fonts_updated_file = f"{data.CACHE_DIR}/fonts_updated"

hyprconf = get_relative_path("config.json")


def load_config():
    with open(hyprconf, "r") as f:
        return json.load(f)


if __name__ == "__main__":
    setproctitle.setproctitle(data.APP_NAME)

    if not os.path.isfile(data.CONFIG_FILE):
        exec_shell_command_async(f"python {get_relative_path('../config/config.py')}")

    config = load_config()

    assets = []
    if config["Basic"]["corners"]:
        from modules.corners import Corners

        corners = Corners()
        assets.append(corners)
    if config["Basic"]["bar"]:
        from modules.bar import Bar

        bar = Bar()
        assets.append(bar)
    if config["Basic"]["notch"]:
        from modules.notch import Notch

        notch = Notch()
        bar.notch = notch
        notch.bar = bar
        assets.append(notch)
    if config["Basic"]["dock"]:
        from modules.dock import Dock

        dock = Dock()
        assets.append(dock)

    app = Application(f"{data.APP_NAME}", *assets)

    def set_css():
        app.set_stylesheet_from_file(
            get_relative_path("main.css"),
            exposed_functions={
                "overview_width": lambda: f"min-width: {data.CURRENT_WIDTH * 0.1 * 5 + 92}px;",
                "overview_height": lambda: f"min-height: {data.CURRENT_HEIGHT * 0.1 * 2 + 32 + 56}px;",
            },
        )

    app.set_css = set_css

    app.set_css()

    app.run()
