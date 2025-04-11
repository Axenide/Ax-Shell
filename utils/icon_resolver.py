import json
import os
import re

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
from loguru import logger

import config.data as data

ICON_CACHE_FILE = data.CACHE_DIR + "/icons.json"
if not os.path.exists(data.CACHE_DIR):
    os.makedirs(data.CACHE_DIR)


class IconResolver:
    def __init__(self, default_applicaiton_icon: str = "application-x-executable-symbolic"):
        if os.path.exists(ICON_CACHE_FILE):
            with open(ICON_CACHE_FILE) as f:
                try:
                    self._icon_dict = json.load(f)
                except json.JSONDecodeError:
                    logger.info("[ICONS] Cache file does not exist or is corrupted")
                    self._icon_dict = {}
        else:
            self._icon_dict = {}

        self.default_applicaiton_icon = default_applicaiton_icon

    def get_icon_name(self, app_id: str):
        if app_id in self._icon_dict:
            return self._icon_dict[app_id]
        new_icon = self._compositor_find_icon(app_id)
        logger.info(
            f"[ICONS] found new icon: '{new_icon}' for app id: '{app_id}', storing..."
        )
        self._store_new_icon(app_id, new_icon)
        return new_icon

    def get_icon_pixbuf(self, app_id: str, size: int = 16):
        icon_theme = Gtk.IconTheme.get_default()
        icon_name = self.get_icon_name(app_id)
        try:
            # Try to load the resolved icon.
            return icon_theme.load_icon(icon_name, size, Gtk.IconLookupFlags.FORCE_SIZE)
        except GLib.Error as primary_error:
            logger.warning(
                f"Warning: Icon '{icon_name}' not found in theme. Error: {primary_error}"
            )
            try:
                # Fallback to the default application icon.
                return icon_theme.load_icon(
                    self.default_applicaiton_icon, size, Gtk.IconLookupFlags.FORCE_SIZE
                )
            except GLib.Error as fallback_error:
                logger.error(
                    f"Error: Fallback icon '{self.default_applicaiton_icon}' also not found. Error: {fallback_error}"
                )
                return None

    def _store_new_icon(self, app_id: str, icon: str):
        self._icon_dict[app_id] = icon
        with open(ICON_CACHE_FILE, "w") as f:
            json.dump(self._icon_dict, f)

    def _get_icon_from_desktop_file(self, desktop_file_path: str):
        # Retrieve the icon specified in the [Desktop Entry] section.
        with open(desktop_file_path) as f:
            for line in f.readlines():
                if "Icon=" in line:
                    return "".join(line[5:].split())
            return self.default_applicaiton_icon

    def _get_desktop_file(self, app_id: str) -> str | None:
        data_dirs = GLib.get_system_data_dirs()
        for data_dir in data_dirs:
            data_dir = os.path.join(data_dir, "applications")
            if os.path.exists(data_dir):
                files = os.listdir(data_dir)
                matching = [s for s in files if "".join(app_id.lower().split()) in s.lower()]
                if matching:
                    return os.path.join(data_dir, matching[0])
                for word in list(filter(None, re.split(r"-|\.|_|\s", app_id))):
                    matching = [s for s in files if word.lower() in s.lower()]
                    if matching:
                        return os.path.join(data_dir, matching[0])
        return None

    def _compositor_find_icon(self, app_id: str):
        icon_theme = Gtk.IconTheme.get_default()
        if icon_theme.has_icon(app_id):
            return app_id
        if icon_theme.has_icon(app_id + "-desktop"):
            return app_id + "-desktop"
        desktop_file = self._get_desktop_file(app_id)
        return (
            self._get_icon_from_desktop_file(desktop_file)
            if desktop_file
            else self.default_applicaiton_icon
        )
