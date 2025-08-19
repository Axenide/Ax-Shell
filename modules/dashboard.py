import random

import gi
from fabric.utils import get_relative_path
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.stack import Stack

import config.data as data

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

import modules.icons as icons
from modules.kanban import Kanban
from modules.mixer import Mixer
from modules.pins import Pins
from modules.wallpapers import WallpaperSelector
from modules.widgets import Widgets


class Dashboard(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="dashboard",
            orientation="v",
            spacing=8,
            h_align="center",
            v_align="center",
            h_expand=True,
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs["notch"]

        self.widgets = Widgets(notch=self.notch)
        self.pins = Pins()
        self.kanban = Kanban()
        self.wallpapers = WallpaperSelector()
        self.mixer = Mixer()

        self.stack = Stack(
            name="stack",
            transition_type="slide-left-right",
            transition_duration=500,
            v_expand=True,
            v_align="fill",
            h_expand=True,
            h_align="fill",
        )

        self.stack.set_homogeneous(False)

        self.switcher = Gtk.StackSwitcher(
            name="switcher",
            spacing=8,
        )

        self.stack.add_titled(self.widgets, "widgets", "Widgets")
        self.stack.add_titled(self.pins, "pins", "Pins")
        self.stack.add_titled(self.kanban, "kanban", "Kanban")
        self.stack.add_titled(self.wallpapers, "wallpapers", "Wallpapers")
        self.stack.add_titled(self.mixer, "mixer", "Mixer")

        self.switcher.set_stack(self.stack)
        self.switcher.set_hexpand(True)
        self.switcher.set_homogeneous(True)
        self.switcher.set_can_focus(True)

        self.stack.connect("notify::visible-child", self.on_visible_child_changed)

        self.add(self.switcher)
        self.add(self.stack)

        if data.PANEL_THEME == "Panel" and (
            data.BAR_POSITION in ["Left", "Right"]
            or data.PANEL_POSITION in ["Start", "End"]
        ):
            GLib.idle_add(self._setup_switcher_icons)

        # Close on right click if the event isn't handled
        self.connect(
            "button-release-event",
            lambda widget, event: (event.button == 3 and self.notch.close_notch()),
        )
        self.show_all()

    def _setup_switcher_icons(self):
        icon_details_map = {
            "Widgets": {"icon": icons.widgets, "name": "widgets"},
            "Pins": {"icon": icons.pins, "name": "pins"},
            "Kanban": {"icon": icons.kanban, "name": "kanban"},
            "Wallpapers": {"icon": icons.wallpapers, "name": "wallpapers"},
            "Mixer": {"icon": icons.speaker, "name": "mixer"},
        }

        buttons = self.switcher.get_children()
        for btn in buttons:
            if isinstance(btn, Gtk.ToggleButton):
                original_gtk_label = None
                for child_widget in btn.get_children():
                    if isinstance(child_widget, Gtk.Label):
                        original_gtk_label = child_widget
                        break

                if original_gtk_label:
                    label_text = original_gtk_label.get_text()
                    if label_text in icon_details_map:
                        details = icon_details_map[label_text]
                        icon_markup = details["icon"]
                        css_name_suffix = details["name"]

                        btn.remove(original_gtk_label)

                        new_icon_label = Label(
                            name=f"switcher-icon-{css_name_suffix}", markup=icon_markup
                        )
                        btn.add(new_icon_label)
                        new_icon_label.show_all()
        return GLib.SOURCE_REMOVE

    def go_to_next_child(self):
        children = self.stack.get_children()
        current_index = self.get_current_index(children)
        next_index = (current_index + 1) % len(children)
        self.stack.set_visible_child(children[next_index])

    def go_to_previous_child(self):
        children = self.stack.get_children()
        current_index = self.get_current_index(children)
        previous_index = (current_index - 1 + len(children)) % len(children)
        self.stack.set_visible_child(children[previous_index])

    def get_current_index(self, children):
        current_child = self.stack.get_visible_child()
        return children.index(current_child) if current_child in children else -1

    def on_visible_child_changed(self, stack, param):
        visible = stack.get_visible_child()
        if visible == self.wallpapers:
            self.wallpapers.search_entry.set_text("")
            self.wallpapers.search_entry.grab_focus()

    def go_to_section(self, section_name):
        """Navigate to a specific section in the dashboard."""
        if section_name == "widgets":
            self.stack.set_visible_child(self.widgets)
        elif section_name == "pins":
            self.stack.set_visible_child(self.pins)
        elif section_name == "kanban":
            self.stack.set_visible_child(self.kanban)
        elif section_name == "wallpapers":
            self.stack.set_visible_child(self.wallpapers)
        elif section_name == "mixer":
            self.stack.set_visible_child(self.mixer)
