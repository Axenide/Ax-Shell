import os
import sys
from pathlib import Path


def _configure_sys_path_for_direct_execution():
    """
    Ajusta sys.path si este script se ejecuta directamente,
    para asegurar que las importaciones relativas dentro del paquete 'config' funcionen.
    Esto permite ejecutar `python config/config.py` desde cualquier directorio.
    """
    if __name__ == "__main__":
        current_file_dir = Path(__file__).resolve().parent
        project_root = current_file_dir.parent

        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

_configure_sys_path_for_direct_execution()

import shutil

from fabric import Application

if __name__ == "__main__" and (__package__ is None or __package__ == ''):
    from config.data import APP_NAME, APP_NAME_CAP
    from config.settings_gui import HyprConfGUI
    from config.settings_utils import load_bind_vars
else:
    from .data import APP_NAME, APP_NAME_CAP
    from .settings_gui import HyprConfGUI
    from .settings_utils import load_bind_vars


def open_config():
    """
    Entry point for opening the configuration GUI using Fabric Application.
    """
    load_bind_vars()

    show_lock_checkbox = True
    dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
    src_lock = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
    if not os.path.exists(dest_lock) and os.path.exists(src_lock):
        try:
            os.makedirs(os.path.dirname(dest_lock), exist_ok=True)
            shutil.copy(src_lock, dest_lock)
            show_lock_checkbox = False 
            print(f"Copied default hyprlock config to {dest_lock}")
        except Exception as e:
            print(f"Error copying default hyprlock config: {e}")
            show_lock_checkbox = os.path.exists(src_lock)

    show_idle_checkbox = True
    dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
    src_idle = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
    if not os.path.exists(dest_idle) and os.path.exists(src_idle):
        try:
            os.makedirs(os.path.dirname(dest_idle), exist_ok=True)
            shutil.copy(src_idle, dest_idle)
            show_idle_checkbox = False
            print(f"Copied default hypridle config to {dest_idle}")
        except Exception as e:
            print(f"Error copying default hypridle config: {e}")
            show_idle_checkbox = os.path.exists(src_idle)

    app = Application(f"{APP_NAME}-settings")
    window = HyprConfGUI(
        show_lock_checkbox=show_lock_checkbox,
        show_idle_checkbox=show_idle_checkbox,
        application=app,
        on_destroy=lambda *_: app.quit()
    )
    app.add_window(window)

    window.show_all()
    app.run()


if __name__ == "__main__":
    open_config()
