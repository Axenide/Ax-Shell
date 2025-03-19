import operator
from collections.abc import Iterator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils import DesktopApp, get_desktop_applications, idle_add, remove_handler, exec_shell_command_async
from fabric.utils.helpers import get_relative_path
from gi.repository import GLib, Gdk
import modules.icons as icons
import config.data as data
import json
import os
import re
import math
import subprocess
from thefuzz import fuzz
from config.data import FUZZY_THRESHOLD
from modules.dock import Dock  # Import the Dock class

class AppLauncher(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="app-launcher",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.notch = kwargs["notch"]
        self.selected_index = -1  # Track the selected item index

        self._arranger_handler: int = 0
        self._all_apps = get_desktop_applications()

        # Calculator history initialization
        self.calc_history_path = f"{data.CACHE_DIR}/calc.json"
        if os.path.exists(self.calc_history_path):
            with open(self.calc_history_path, "r") as f:
                self.calc_history = json.load(f)
        else:
            self.calc_history = []

        self.viewport = Box(name="viewport", spacing=4, orientation="v")
        self.search_entry = Entry(
            name="search-entry",
            placeholder="Search Applications...",
            h_expand=True,
            notify_text=lambda entry, *_: (
                self.update_calculator_viewport() if entry.get_text().startswith("=")
                else self.arrange_viewport(entry.get_text())
            ),
            on_activate=lambda entry, *_: self.on_search_entry_activate(entry.get_text()),
            on_key_press_event=self.on_search_entry_key_press,  # Handle key presses
        )
        self.search_entry.props.xalign = 0.5
        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            min_content_size=(450, 105),
            max_content_size=(450, 105),
            child=self.viewport,
        )

        self.header_box = Box(
            name="header_box",
            spacing=10,
            orientation="h",
            children=[
                Button(
                    name="config-button",
                    child=Label(name="config-label", markup=icons.config),
                    on_clicked=lambda *_: (exec_shell_command_async(f"python {get_relative_path('../config/config.py')}"), self.close_launcher()),
                ),
                self.search_entry,
                Button(
                    name="close-button",
                    child=Label(name="close-label", markup=icons.cancel),
                    tooltip_text="Exit",
                    on_clicked=lambda *_: self.close_launcher()
                ),
            ],
        )

        self.launcher_box = Box(
            name="launcher-box",
            spacing=10,
            h_expand=True,
            orientation="v",
            children=[
                self.header_box,
                self.scrolled_window,
            ],
        )

        self.resize_viewport()

        self.add(self.launcher_box)
        self.show_all()

    def close_launcher(self):
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        self.notch.close_notch()

    def open_launcher(self):
        self._all_apps = get_desktop_applications()
        self.arrange_viewport()

    def arrange_viewport(self, query: str = ""):
        if query.startswith("="):
            # In calculator mode, update history view once (not per keystroke)
            self.update_calculator_viewport()
            return
        remove_handler(self._arranger_handler) if self._arranger_handler else None
        self.viewport.children = []
        self.selected_index = -1  # Clear selection when viewport changes

        filtered_apps_iter = iter(
            sorted(
                [
                    app
                    for app in self._all_apps
                    if fuzz.partial_ratio(
                        query.casefold(),
                        (
                            (app.display_name or "")
                            + (" " + app.name + " ")
                            + (app.generic_name or "")
                        ).casefold(),
                    ) >= FUZZY_THRESHOLD or query == ""
                ],
                key=lambda app: (app.display_name or "").casefold(),
            )
        )
        should_resize = operator.length_hint(filtered_apps_iter) == len(self._all_apps)

        self._arranger_handler = idle_add(
            lambda apps_iter: self.add_next_application(apps_iter) or self.handle_arrange_complete(should_resize, query),
            filtered_apps_iter,
            pin=True,
        )

    def handle_arrange_complete(self, should_resize, query):
        if should_resize:
            self.resize_viewport()
        # Only auto-select first item if query exists
        if query.strip() != "" and self.viewport.get_children():
            self.update_selection(0)
        return False

    def add_next_application(self, apps_iter: Iterator[DesktopApp]):
        if not (app := next(apps_iter, None)):
            return False
        self.viewport.add(self.bake_application_slot(app))
        return True

    def resize_viewport(self):
        self.scrolled_window.set_min_content_width(
            self.viewport.get_allocation().width  # type: ignore
        )
        return False

    def bake_application_slot(self, app: DesktopApp, **kwargs) -> Button:
        button = Button(
            name="app-slot-button",
            child=Box(
                name="app-slot-box",
                orientation="h",
                spacing=10,
                children=[
                    Image(name="app-icon", pixbuf=app.get_icon_pixbuf(size=24), h_align="start"),
                    Label(
                        name="app-label",
                        label=app.display_name or "Unknown",
                        ellipsization="end",
                        v_align="center",
                        h_align="center",
                    ),
                ],
            ),
            tooltip_text=app.description,
            on_clicked=lambda *_: (app.launch(), self.close_launcher()),
            **kwargs,
        )
        return button

    def update_selection(self, new_index: int):
        # Unselect current
        if self.selected_index != -1 and self.selected_index < len(self.viewport.get_children()):
            current_button = self.viewport.get_children()[self.selected_index]
            current_button.get_style_context().remove_class("selected")
        # Select new
        if new_index != -1 and new_index < len(self.viewport.get_children()):
            new_button = self.viewport.get_children()[new_index]
            new_button.get_style_context().add_class("selected")
            self.selected_index = new_index
            self.scroll_to_selected(new_button)
        else:
            self.selected_index = -1

    def scroll_to_selected(self, button):
        def scroll():
            adj = self.scrolled_window.get_vadjustment()
            alloc = button.get_allocation()
            if alloc.height == 0:
                return False  # Retry if allocation isn't ready

            y = alloc.y
            height = alloc.height
            page_size = adj.get_page_size()
            current_value = adj.get_value()

            # Calculate visible boundaries
            visible_top = current_value
            visible_bottom = current_value + page_size

            if y < visible_top:
                # Item above viewport - align to top
                adj.set_value(y)
            elif y + height > visible_bottom:
                # Item below viewport - align to bottom
                new_value = y + height - page_size
                adj.set_value(new_value)
            # No action if already fully visible
            return False
        GLib.idle_add(scroll)

    def on_search_entry_activate(self, text):
        if text.startswith("="):
            # If in calculator mode and no history item is selected, evaluate new expression.
            if self.selected_index == -1:
                self.evaluate_calculator_expression(text)
            return
        match text:
            case ":w":
                self.notch.open_notch("wallpapers")
            case ":d":
                self.notch.open_notch("dashboard")
            case ":p":
                self.notch.open_notch("power")
            case _:
                children = self.viewport.get_children()
                if children:
                    # Only activate if we have selection or non-empty query
                    if text.strip() == "" and self.selected_index == -1:
                        return  # Prevent accidental activation when empty
                    selected_index = self.selected_index if self.selected_index != -1 else 0
                    if 0 <= selected_index < len(children):
                        children[selected_index].clicked()

    def on_search_entry_key_press(self, widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and (event.state & Gdk.ModifierType.SHIFT_MASK):
            self.add_selected_app_to_dock()
            return True
        text = widget.get_text()
        if text.startswith("="):
            if event.keyval == Gdk.KEY_Down:
                self.move_selection(1)
                return True
            elif event.keyval == Gdk.KEY_Up:
                self.move_selection(-1)
                return True
            elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                # In calculator mode, if a history item is highlighted, copy it.
                if self.selected_index != -1:
                    if event.state & Gdk.ModifierType.SHIFT_MASK:
                        self.delete_selected_calc_history()
                    else:
                        selected_text = self.calc_history[self.selected_index]
                        self.copy_text_to_clipboard(selected_text)
                        # Clear selection so new expressions are evaluated on further Return presses.
                        self.selected_index = -1
                else:
                    self.evaluate_calculator_expression(text)
                return True
            elif event.keyval == Gdk.KEY_Escape:
                self.close_launcher()
                return True
            return False
        else:
            # Normal app mode behavior
            if event.keyval == Gdk.KEY_Down:
                self.move_selection(1)
                return True
            elif event.keyval == Gdk.KEY_Up:
                self.move_selection(-1)
                return True
            elif event.keyval == Gdk.KEY_Escape:
                self.close_launcher()
                return True
            return False

    def add_selected_app_to_dock(self):
        """Adds the currently selected application to the dock.json file with comprehensive metadata."""
        children = self.viewport.get_children()
        if not children or self.selected_index == -1 or self.selected_index >= len(children):
            return  # No app selected

        selected_button = children[self.selected_index]
        # Extract the app's display name from the label to find the DesktopApp object
        selected_app = next((app for app in self._all_apps if app.display_name == selected_button.get_child().get_children()[1].props.label), None)
        if not selected_app:
            return

        # Create comprehensive app data dictionary - Include all available properties
        # Filter out None values to keep the JSON clean
        app_data = {k: v for k, v in {
            "name": selected_app.name,
            "display_name": selected_app.display_name,
            "window_class": selected_app.window_class,
            "executable": selected_app.executable,
            "command_line": selected_app.command_line,
            "icon_name": selected_app.icon_name
        }.items() if v is not None}

        config_path = get_relative_path("../config/dock.json")
        try:
            with open(config_path, "r") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"pinned_apps": []}

        # Check if app is already pinned (by name)
        already_pinned = False
        for pinned_app in data.get("pinned_apps", []):
            if isinstance(pinned_app, dict) and pinned_app.get("name") == app_data["name"]:
                already_pinned = True
                # Update existing entry with latest app data
                pinned_app.update(app_data)
                break
            elif isinstance(pinned_app, str) and pinned_app == app_data["name"]:
                already_pinned = True
                # Replace string format with new comprehensive format
                data["pinned_apps"].remove(pinned_app)
                data["pinned_apps"].append(app_data)
                break

        # Add to pinned apps if not already there
        if not already_pinned:
            data.setdefault("pinned_apps", []).append(app_data)
        
        # Write the updated config
        with open(config_path, "w") as file:
            json.dump(data, file, indent=4)
            
        # Notify dock instances of the configuration change immediately
        Dock.notify_config_change()

    def move_selection(self, delta: int):
        children = self.viewport.get_children()
        if not children:
            return
        # Allow starting selection from nothing when empty
        if self.selected_index == -1 and delta == 1:
            new_index = 0
        else:
            new_index = self.selected_index + delta
        new_index = max(0, min(new_index, len(children) - 1))
        self.update_selection(new_index)

    def save_calc_history(self):
        with open(self.calc_history_path, "w") as f:
            json.dump(self.calc_history, f)

    def evaluate_calculator_expression(self, text: str):
        # Remove the '=' prefix and extra spaces
        expr = text.lstrip("=").strip()
        if not expr:
            return
        # Replace operators: '^' -> '**', and '×' -> '*'
        expr = expr.replace("^", "**").replace("×", "*")
        # Replace factorial: e.g. 5! -> math.factorial(5)
        expr = re.sub(r'(\d+)!', r'math.factorial(\1)', expr)
        # Replace brackets: allow [] and {} as ()
        for old, new in [("[", "("), ("]", ")"), ("{", "("), ("}", ")")]:
            expr = expr.replace(old, new)
        try:
            result = eval(expr, {"__builtins__": None, "math": math})
        except Exception as e:
            result = f"Error: {e}"
        # Prepend to history (newest first)
        self.calc_history.insert(0, f"{text} => {result}")
        self.save_calc_history()
        self.update_calculator_viewport()

    def update_calculator_viewport(self):
        self.viewport.children = []
        for item in self.calc_history:
            btn = self.create_calc_history_button(item)
            self.viewport.add(btn)
        # Remove resetting selected_index unconditionally so that a highlighted result isn't lost.
        # Optionally, only reset if the input is not more than "=".
        # if self.search_entry.get_text().strip() != "=":
        #     self.selected_index = -1

    def create_calc_history_button(self, text: str) -> Button:
        btn = Button(
            name="app-slot-button",  # reuse existing CSS styling
            child=Box(
                name="calc-slot-box",
                orientation="h",
                spacing=10,
                children=[
                    Label(
                        name="calc-label",
                        label=text,
                        ellipsization="end",
                        v_align="center",
                        h_align="center",
                    ),
                ],
            ),
            tooltip_text=text,
            on_clicked=lambda *_: self.copy_text_to_clipboard(text),
        )
        return btn

    def copy_text_to_clipboard(self, text: str):
        # Split the text on "=>" and copy only the result part if available
        parts = text.split("=>", 1)
        copy_text = parts[1].strip() if len(parts) > 1 else text
        try:
            subprocess.run(["wl-copy"], input=copy_text.encode(), check=True)
        except subprocess.CalledProcessError as e:
            print(f"Clipboard copy failed: {e}")

    def delete_selected_calc_history(self):
        if self.selected_index != -1 and self.selected_index < len(self.calc_history):
            del self.calc_history[self.selected_index]
            self.save_calc_history()
            self.update_calculator_viewport()
