import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import gi

gi.require_version('Gtk', '3.0')
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image as FabricImage
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.stack import Stack
from fabric.widgets.window import Window
from gi.repository import GdkPixbuf, GLib, Gtk
from PIL import Image

from .data import (APP_NAME, APP_NAME_CAP, NOTIF_POS_DEFAULT, NOTIF_POS_KEY,
                   PANEL_POSITION_DEFAULT, PANEL_POSITION_KEY)
from .settings_utils import backup_and_replace, bind_vars, start_config


class HyprConfGUI(Window):
    def __init__(self, show_lock_checkbox: bool, show_idle_checkbox: bool, **kwargs):
        super().__init__(
            title="Ax-Shell Settings",
            name="axshell-settings-window",
            size=(640, 640),
            **kwargs,
        )

        self.set_resizable(False)

        self.selected_face_icon = None
        self.show_lock_checkbox = show_lock_checkbox
        self.show_idle_checkbox = show_idle_checkbox

        root_box = Box(orientation="v", spacing=10, style="margin: 10px;")
        self.add(root_box)

        main_content_box = Box(orientation="h", spacing=6, v_expand=True, h_expand=True)
        root_box.add(main_content_box)

        self.tab_stack = Stack(
             transition_type="slide-up-down",
             transition_duration=250,
             v_expand=True, h_expand=True
        )

        self.key_bindings_tab_content = self.create_key_bindings_tab()
        self.appearance_tab_content = self.create_appearance_tab()
        self.system_tab_content = self.create_system_tab()
        self.about_tab_content = self.create_about_tab()

        self.tab_stack.add_titled(self.key_bindings_tab_content, "key_bindings", "Key Bindings")
        self.tab_stack.add_titled(self.appearance_tab_content, "appearance", "Appearance")
        self.tab_stack.add_titled(self.system_tab_content, "system", "System")
        self.tab_stack.add_titled(self.about_tab_content, "about", "About")

        tab_switcher = Gtk.StackSwitcher()
        tab_switcher.set_stack(self.tab_stack)
        tab_switcher.set_orientation(Gtk.Orientation.VERTICAL)
        main_content_box.add(tab_switcher)
        main_content_box.add(self.tab_stack)

        button_box = Box(orientation="h", spacing=10, h_align="end")
        reset_btn = Button(label="Reset to Defaults", on_clicked=self.on_reset)
        button_box.add(reset_btn)
        close_btn = Button(label="Close", on_clicked=self.on_close)
        button_box.add(close_btn)
        accept_btn = Button(label="Apply & Reload", on_clicked=self.on_accept)
        button_box.add(accept_btn)
        root_box.add(button_box)

    def create_key_bindings_tab(self):
        scrolled_window = ScrolledWindow(
            h_scrollbar_policy="never", 
            v_scrollbar_policy="automatic",
            h_expand=True,
            v_expand=True,
            propagate_width=False,
            propagate_height=False
        )

        main_vbox = Box(orientation="v", spacing=10, style="margin: 15px;")
        scrolled_window.add(main_vbox)

        keybind_grid = Gtk.Grid()
        keybind_grid.set_column_spacing(10)
        keybind_grid.set_row_spacing(8)
        keybind_grid.set_margin_start(5)
        keybind_grid.set_margin_end(5)
        keybind_grid.set_margin_top(5)
        keybind_grid.set_margin_bottom(5)
        
        action_label = Label(markup="<b>Action</b>", h_align="start", style="margin-bottom: 5px;")
        modifier_label = Label(markup="<b>Modifier</b>", h_align="start", style="margin-bottom: 5px;")
        separator_label = Label(label="+", h_align="center", style="margin-bottom: 5px;")
        key_label = Label(markup="<b>Key</b>", h_align="start", style="margin-bottom: 5px;")

        keybind_grid.attach(action_label, 0, 0, 1, 1)
        keybind_grid.attach(modifier_label, 1, 0, 1, 1)
        keybind_grid.attach(separator_label, 2, 0, 1, 1)
        keybind_grid.attach(key_label, 3, 0, 1, 1)

        self.entries = []
        bindings = [
            (f"Reload {APP_NAME_CAP}", 'prefix_restart', 'suffix_restart'),
            ("Message", 'prefix_axmsg', 'suffix_axmsg'),
            ("Dashboard", 'prefix_dash', 'suffix_dash'),
            ("Bluetooth", 'prefix_bluetooth', 'suffix_bluetooth'),
            ("Pins", 'prefix_pins', 'suffix_pins'),
            ("Kanban", 'prefix_kanban', 'suffix_kanban'),
            ("App Launcher", 'prefix_launcher', 'suffix_launcher'),
            ("Tmux", 'prefix_tmux', 'suffix_tmux'),
            ("Clipboard History", 'prefix_cliphist', 'suffix_cliphist'),
            ("Toolbox", 'prefix_toolbox', 'suffix_toolbox'),
            ("Overview", 'prefix_overview', 'suffix_overview'),
            ("Wallpapers", 'prefix_wallpapers', 'suffix_wallpapers'),
            ("Random Wallpaper", 'prefix_randwall', 'suffix_randwall'),
            ("Emoji Picker", 'prefix_emoji', 'suffix_emoji'),
            ("Power Menu", 'prefix_power', 'suffix_power'),
            ("Toggle Caffeine", 'prefix_caffeine', 'suffix_caffeine'),
            ("Reload CSS", 'prefix_css', 'suffix_css'),
            ("Restart with inspector", 'prefix_restart_inspector', 'suffix_restart_inspector'),
        ]

        for i, (label_text, prefix_key, suffix_key) in enumerate(bindings):
            row = i + 1
            binding_label = Label(label=label_text, h_align="start")
            keybind_grid.attach(binding_label, 0, row, 1, 1)
            prefix_entry = Entry(text=bind_vars.get(prefix_key, ''))
            keybind_grid.attach(prefix_entry, 1, row, 1, 1)
            plus_label = Label(label="+", h_align="center")
            keybind_grid.attach(plus_label, 2, row, 1, 1)
            suffix_entry = Entry(text=bind_vars.get(suffix_key, ''))
            keybind_grid.attach(suffix_entry, 3, row, 1, 1)
            self.entries.append((prefix_key, suffix_key, prefix_entry, suffix_entry))

        main_vbox.add(keybind_grid)
        return scrolled_window

    def create_appearance_tab(self):
        scrolled_window = ScrolledWindow(
            h_scrollbar_policy="never", 
            v_scrollbar_policy="automatic",
            h_expand=True,
            v_expand=True,
            propagate_width=False,
            propagate_height=False
        )

        vbox = Box(orientation="v", spacing=15, style="margin: 15px;")
        scrolled_window.add(vbox)

        top_grid = Gtk.Grid()
        top_grid.set_column_spacing(20)
        top_grid.set_row_spacing(5)
        top_grid.set_margin_bottom(10)
        vbox.add(top_grid)

        wall_header = Label(markup="<b>Wallpapers</b>", h_align="start")
        top_grid.attach(wall_header, 0, 0, 1, 1)
        wall_label = Label(label="Directory:", h_align="start", v_align="center")
        top_grid.attach(wall_label, 0, 1, 1, 1)
        
        chooser_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        chooser_container.set_halign(Gtk.Align.START)
        chooser_container.set_valign(Gtk.Align.CENTER)
        self.wall_dir_chooser = Gtk.FileChooserButton(
            title="Select a folder", action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.wall_dir_chooser.set_tooltip_text("Select the directory containing your wallpaper images")
        self.wall_dir_chooser.set_filename(bind_vars.get('wallpapers_dir',''))
        self.wall_dir_chooser.set_size_request(180, -1)
        chooser_container.add(self.wall_dir_chooser)
        top_grid.attach(chooser_container, 1, 1, 1, 1)

        face_header = Label(markup="<b>Profile Icon</b>", h_align="start")
        top_grid.attach(face_header, 2, 0, 2, 1)
        current_face = os.path.expanduser("~/.face.icon")
        face_image_container = Box(style_classes=["image-frame"], h_align="center", v_align="center")
        self.face_image = FabricImage(size=64)
        try:
            if os.path.exists(current_face):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(current_face, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
            else:
                 self.face_image.set_from_icon_name("user-info", Gtk.IconSize.DIALOG) 
        except Exception as e:
            print(f"Error loading face icon: {e}")
            self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        face_image_container.add(self.face_image)
        top_grid.attach(face_image_container, 2, 1, 1, 1)
        
        browse_btn_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        browse_btn_container.set_halign(Gtk.Align.START)
        browse_btn_container.set_valign(Gtk.Align.CENTER)
        face_btn = Button(label="Browse...",
                          tooltip_text="Select a square image for your profile icon",
                          on_clicked=self.on_select_face_icon)
        browse_btn_container.add(face_btn)
        top_grid.attach(browse_btn_container, 3, 1, 1, 1)
        self.face_status_label = Label(label="", h_align="start")
        top_grid.attach(self.face_status_label, 2, 2, 2, 1)

        separator1 = Box(style="min-height: 1px; background-color: alpha(@fg_color, 0.2); margin: 5px 0px;", h_expand=True)
        vbox.add(separator1)

        # START NEW SECTION FOR DATETIME FORMAT
        datetime_format_header = Label(markup="<b>Date & Time Format</b>", h_align="start")
        vbox.add(datetime_format_header)

        datetime_grid = Gtk.Grid()
        datetime_grid.set_column_spacing(20)
        datetime_grid.set_row_spacing(10)
        datetime_grid.set_margin_start(10)
        datetime_grid.set_margin_top(5)
        datetime_grid.set_margin_bottom(10) # Adds space before the next section
        vbox.add(datetime_grid)

        datetime_12h_label = Label(label="Use 12-Hour Clock", h_align="start", v_align="center")
        datetime_grid.attach(datetime_12h_label, 0, 0, 1, 1)

        datetime_12h_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.datetime_12h_switch = Gtk.Switch(active=bind_vars.get('datetime_12h_format', False))
        datetime_12h_switch_container.add(self.datetime_12h_switch)
        datetime_grid.attach(datetime_12h_switch_container, 1, 0, 1, 1)
        # END NEW SECTION FOR DATETIME FORMAT

        layout_header = Label(markup="<b>Layout Options</b>", h_align="start")
        vbox.add(layout_header)
        layout_grid = Gtk.Grid()
        layout_grid.set_column_spacing(20)
        layout_grid.set_row_spacing(10)
        layout_grid.set_margin_start(10)
        layout_grid.set_margin_top(5)
        vbox.add(layout_grid)

        position_label = Label(label="Bar Position", h_align="start", v_align="center")
        layout_grid.attach(position_label, 0, 0, 1, 1)
        position_combo_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.position_combo = Gtk.ComboBoxText()
        self.position_combo.set_tooltip_text("Select the position of the bar")
        positions = ["Top", "Bottom", "Left", "Right"]
        for pos in positions: 
            self.position_combo.append_text(pos)
        current_position = bind_vars.get('bar_position', "Top")
        try:
            self.position_combo.set_active(positions.index(current_position))
        except ValueError:
            self.position_combo.set_active(0)
        self.position_combo.connect("changed", self.on_position_changed)
        position_combo_container.add(self.position_combo)
        layout_grid.attach(position_combo_container, 1, 0, 1, 1)

        centered_label = Label(label="Centered Bar (Left/Right Only)", h_align="start", v_align="center")
        layout_grid.attach(centered_label, 2, 0, 1, 1)
        centered_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.centered_switch = Gtk.Switch(active=bind_vars.get('centered_bar', False), 
                                          sensitive=bind_vars.get('bar_position', "Top") in ["Left", "Right"])
        centered_switch_container.add(self.centered_switch)
        layout_grid.attach(centered_switch_container, 3, 0, 1, 1)

        dock_label = Label(label="Show Dock", h_align="start", v_align="center")
        layout_grid.attach(dock_label, 0, 1, 1, 1)
        dock_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.dock_switch = Gtk.Switch(active=bind_vars.get('dock_enabled', True))
        self.dock_switch.connect("notify::active", self.on_dock_enabled_changed)
        dock_switch_container.add(self.dock_switch)
        layout_grid.attach(dock_switch_container, 1, 1, 1, 1)

        dock_hover_label = Label(label="Show Dock Only on Hover", h_align="start", v_align="center")
        layout_grid.attach(dock_hover_label, 2, 1, 1, 1)
        dock_hover_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.dock_hover_switch = Gtk.Switch(active=bind_vars.get('dock_always_occluded', False), sensitive=self.dock_switch.get_active())
        dock_hover_switch_container.add(self.dock_hover_switch)
        layout_grid.attach(dock_hover_switch_container, 3, 1, 1, 1)
        
        dock_size_label = Label(label="Dock Icon Size", h_align="start", v_align="center")
        layout_grid.attach(dock_size_label, 0, 2, 1, 1)
        self.dock_size_scale = Scale(
            min_value=16, max_value=48, value=bind_vars.get('dock_icon_size', 28),
            increments=(2, 4), draw_value=True, value_position="right", digits=0, h_expand=True
        )
        layout_grid.attach(self.dock_size_scale, 1, 2, 3, 1)

        ws_num_label = Label(label="Show Workspace Numbers", h_align="start", v_align="center")
        layout_grid.attach(ws_num_label, 0, 3, 1, 1)
        ws_num_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.ws_num_switch = Gtk.Switch(active=bind_vars.get('bar_workspace_show_number', False))
        self.ws_num_switch.connect("notify::active", self.on_ws_num_changed)
        ws_num_switch_container.add(self.ws_num_switch)
        layout_grid.attach(ws_num_switch_container, 1, 3, 1, 1)

        ws_chinese_label = Label(label="Use Chinese Numerals", h_align="start", v_align="center")
        layout_grid.attach(ws_chinese_label, 2, 3, 1, 1)
        ws_chinese_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.ws_chinese_switch = Gtk.Switch(active=bind_vars.get('bar_workspace_use_chinese_numerals', False), sensitive=self.ws_num_switch.get_active())
        ws_chinese_switch_container.add(self.ws_chinese_switch)
        layout_grid.attach(ws_chinese_switch_container, 3, 3, 1, 1)

        bar_theme_label = Label(label="Bar Theme", h_align="start", v_align="center")
        layout_grid.attach(bar_theme_label, 0, 4, 1, 1)
        bar_theme_combo_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.bar_theme_combo = Gtk.ComboBoxText()
        self.bar_theme_combo.set_tooltip_text("Select the visual theme for the bar")
        themes = ["Pills", "Dense", "Edge"]
        for theme in themes: self.bar_theme_combo.append_text(theme)
        current_theme = bind_vars.get('bar_theme', "Pills")
        try:
            self.bar_theme_combo.set_active(themes.index(current_theme))
        except ValueError:
            self.bar_theme_combo.set_active(0)
        bar_theme_combo_container.add(self.bar_theme_combo)
        layout_grid.attach(bar_theme_combo_container, 1, 4, 3, 1)

        dock_theme_label = Label(label="Dock Theme", h_align="start", v_align="center")
        layout_grid.attach(dock_theme_label, 0, 5, 1, 1) 
        dock_theme_combo_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.dock_theme_combo = Gtk.ComboBoxText() 
        self.dock_theme_combo.set_tooltip_text("Select the visual theme for the dock")
        for theme in themes: self.dock_theme_combo.append_text(theme)
        current_dock_theme = bind_vars.get('dock_theme', "Pills") 
        try:
            self.dock_theme_combo.set_active(themes.index(current_dock_theme))
        except ValueError:
            self.dock_theme_combo.set_active(0) 
        dock_theme_combo_container.add(self.dock_theme_combo)
        layout_grid.attach(dock_theme_combo_container, 1, 5, 3, 1)

        panel_theme_label = Label(label="Panel Theme", h_align="start", v_align="center")
        layout_grid.attach(panel_theme_label, 0, 6, 1, 1)
        panel_theme_combo_container = Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.panel_theme_combo = Gtk.ComboBoxText()
        self.panel_theme_combo.set_tooltip_text("Select the theme/mode for panels like toolbox, clipboard, etc.")
        panel_themes = ["Notch", "Panel"]
        for theme in panel_themes: self.panel_theme_combo.append_text(theme)
        current_panel_theme = bind_vars.get('panel_theme', "Notch") 
        try:
            self.panel_theme_combo.set_active(panel_themes.index(current_panel_theme))
        except ValueError:
            self.panel_theme_combo.set_active(0) 
        panel_theme_combo_container.add(self.panel_theme_combo)
        layout_grid.attach(panel_theme_combo_container, 1, 6, 1, 1)
        self.panel_theme_combo.connect("changed", self._on_panel_theme_changed_for_position_sensitivity)

        self.panel_position_options = [
            "Start", "Center", "End"
        ]

        panel_position_label = Label(label="Panel Position", h_align="start", v_align="center")
        layout_grid.attach(panel_position_label, 2, 6, 1, 1)

        panel_position_combo_container = Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        self.panel_position_combo = Gtk.ComboBoxText()
        self.panel_position_combo.set_tooltip_text("Select the position for the 'Panel' theme panels")
        for option in self.panel_position_options:
            self.panel_position_combo.append_text(option)
        
        current_panel_position = bind_vars.get(PANEL_POSITION_KEY, PANEL_POSITION_DEFAULT)
        try:
            self.panel_position_combo.set_active(self.panel_position_options.index(current_panel_position))
        except ValueError:
            try:
                self.panel_position_combo.set_active(self.panel_position_options.index(PANEL_POSITION_DEFAULT))
            except ValueError:
                self.panel_position_combo.set_active(0) 

        panel_position_combo_container.add(self.panel_position_combo)
        layout_grid.attach(panel_position_combo_container, 3, 6, 1, 1)

        notification_pos_label = Label(label="Notification Position", h_align="start", v_align="center")
        layout_grid.attach(notification_pos_label, 0, 7, 1, 1)

        notification_pos_combo_container = Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        
        self.notification_pos_combo = Gtk.ComboBoxText()
        self.notification_pos_combo.set_tooltip_text("Select where notifications appear on the screen.")
        
        notification_positions_list = ["Top", "Bottom"]
        for pos in notification_positions_list:
            self.notification_pos_combo.append_text(pos)
        
        current_notif_pos = bind_vars.get(NOTIF_POS_KEY, NOTIF_POS_DEFAULT)
        try:
            self.notification_pos_combo.set_active(notification_positions_list.index(current_notif_pos))
        except ValueError:
            self.notification_pos_combo.set_active(0)

        self.notification_pos_combo.connect("changed", self.on_notification_position_changed)
        
        notification_pos_combo_container.add(self.notification_pos_combo)
        layout_grid.attach(notification_pos_combo_container, 1, 7, 3, 1)

        separator2 = Box(style="min-height: 1px; background-color: alpha(@fg_color, 0.2); margin: 5px 0px;", h_expand=True)
        vbox.add(separator2)

        components_header = Label(markup="<b>Modules</b>", h_align="start")
        vbox.add(components_header)
        components_grid = Gtk.Grid()
        components_grid.set_column_spacing(15)
        components_grid.set_row_spacing(8)
        components_grid.set_margin_start(10)
        components_grid.set_margin_top(5)
        vbox.add(components_grid)

        self.component_switches = {}
        component_display_names = {
            'button_apps': "App Launcher Button", 'systray': "System Tray", 'control': "Control Panel",
            'network': "Network Applet", 'button_tools': "Toolbox Button", 'button_overview': "Overview Button",
            'ws_container': "Workspaces", 'weather': "Weather Widget", 'battery': "Battery Indicator",
            'metrics': "System Metrics", 'language': "Language Indicator", 'date_time': "Date & Time",
            'button_power': "Power Button",
        }

        self.corners_switch = Gtk.Switch(active=bind_vars.get('corners_visible', True))
        num_components = len(component_display_names) + 1
        rows_per_column = (num_components + 1) // 2
        
        corners_label = Label(label="Rounded Corners", h_align="start", v_align="center")
        components_grid.attach(corners_label, 0, 0, 1, 1)
        switch_container_corners = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        switch_container_corners.add(self.corners_switch)
        components_grid.attach(switch_container_corners, 1, 0, 1, 1)
        
        current_row = 0
        current_col = 0
        item_idx = 0
        for i, (name, display) in enumerate(component_display_names.items()):
            if item_idx < (rows_per_column -1) : 
                row = item_idx + 1 
                col = 0
            else:
                row = (item_idx - (rows_per_column -1))
                col = 2
            
            component_label = Label(label=display, h_align="start", v_align="center")
            components_grid.attach(component_label, col, row, 1, 1)
            
            switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
            component_switch = Gtk.Switch(active=bind_vars.get(f'bar_{name}_visible', True))
            switch_container.add(component_switch)
            components_grid.attach(switch_container, col + 1, row, 1, 1)
            self.component_switches[name] = component_switch
            item_idx +=1
        
        self._update_panel_position_sensitivity()
        return scrolled_window

    def _on_panel_theme_changed_for_position_sensitivity(self, combo):
        self._update_panel_position_sensitivity()

    def _update_panel_position_sensitivity(self):
        if hasattr(self, 'panel_theme_combo') and hasattr(self, 'panel_position_combo'):
            selected_theme = self.panel_theme_combo.get_active_text()
            is_panel_theme_selected = (selected_theme == "Panel")
            self.panel_position_combo.set_sensitive(is_panel_theme_selected)

    def on_notification_position_changed(self, combo: Gtk.ComboBoxText):
        selected_text = combo.get_active_text()
        if selected_text:
            bind_vars[NOTIF_POS_KEY] = selected_text
            print(f"Notification position updated in bind_vars: {bind_vars[NOTIF_POS_KEY]}")

    def create_system_tab(self):
        scrolled_window = ScrolledWindow(
            h_scrollbar_policy="never", 
            v_scrollbar_policy="automatic",
            h_expand=True,
            v_expand=True,
            propagate_width=False,
            propagate_height=False
        )

        vbox = Box(orientation="v", spacing=15, style="margin: 15px;")
        scrolled_window.add(vbox)

        system_grid = Gtk.Grid()
        system_grid.set_column_spacing(20)
        system_grid.set_row_spacing(10)
        system_grid.set_margin_bottom(15)
        vbox.add(system_grid)

        terminal_header = Label(markup="<b>Terminal Settings</b>", h_align="start")
        system_grid.attach(terminal_header, 0, 0, 2, 1)
        terminal_label = Label(label="Command:", h_align="start", v_align="center")
        system_grid.attach(terminal_label, 0, 1, 1, 1)
        self.terminal_entry = Entry(
            text=bind_vars.get('terminal_command', "kitty -e"),
            tooltip_text="Command used to launch terminal apps (e.g., 'kitty -e')",
            h_expand=True
        )
        system_grid.attach(self.terminal_entry, 1, 1, 1, 1)
        hint_label = Label(markup="<small>Examples: 'kitty -e', 'alacritty -e', 'foot -e'</small>", h_align="start")
        system_grid.attach(hint_label, 0, 2, 2, 1)

        hypr_header = Label(markup="<b>Hyprland Integration</b>", h_align="start")
        system_grid.attach(hypr_header, 2, 0, 2, 1)
        row = 1
        self.lock_switch = None
        if self.show_lock_checkbox:
            lock_label = Label(label="Replace Hyprlock config", h_align="start", v_align="center")
            system_grid.attach(lock_label, 2, row, 1, 1)
            lock_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
            self.lock_switch = Gtk.Switch(tooltip_text="Replace Hyprlock configuration with Ax-Shell's custom config")
            lock_switch_container.add(self.lock_switch)
            system_grid.attach(lock_switch_container, 3, row, 1, 1)
            row += 1
        self.idle_switch = None
        if self.show_idle_checkbox:
            idle_label = Label(label="Replace Hypridle config", h_align="start", v_align="center")
            system_grid.attach(idle_label, 2, row, 1, 1)
            idle_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
            self.idle_switch = Gtk.Switch(tooltip_text="Replace Hypridle configuration with Ax-Shell's custom config")
            idle_switch_container.add(self.idle_switch)
            system_grid.attach(idle_switch_container, 3, row, 1, 1)
            row += 1
        if self.show_lock_checkbox or self.show_idle_checkbox:
            note_label = Label(markup="<small>Existing configs will be backed up</small>", h_align="start")
            system_grid.attach(note_label, 2, row, 2, 1)

        metrics_header = Label(markup="<b>System Metrics Options</b>", h_align="start")
        vbox.add(metrics_header)
        metrics_grid = Gtk.Grid(column_spacing=15, row_spacing=8, margin_start=10, margin_top=5)
        vbox.add(metrics_grid)

        self.metrics_switches = {}
        self.metrics_small_switches = {}
        metric_names = {'cpu': "CPU", 'ram': "RAM", 'disk': "Disk", 'gpu': "GPU"}

        metrics_grid.attach(Label(label="Show in Metrics", h_align="start"), 0, 0, 1, 1)
        for i, (key, label_text) in enumerate(metric_names.items()):
            switch = Gtk.Switch(active=bind_vars.get('metrics_visible', {}).get(key, True))
            self.metrics_switches[key] = switch
            metrics_grid.attach(Label(label=label_text, h_align="start"), 0, i + 1, 1, 1)
            metrics_grid.attach(switch, 1, i + 1, 1, 1)

        metrics_grid.attach(Label(label="Show in Small Metrics", h_align="start"), 2, 0, 1, 1)
        for i, (key, label_text) in enumerate(metric_names.items()):
            switch = Gtk.Switch(active=bind_vars.get('metrics_small_visible', {}).get(key, True))
            self.metrics_small_switches[key] = switch
            metrics_grid.attach(Label(label=label_text, h_align="start"), 2, i + 1, 1, 1)
            metrics_grid.attach(switch, 3, i + 1, 1, 1)

        def enforce_minimum_metrics(switch_dict):
            enabled_switches = [s for s in switch_dict.values() if s.get_active()]
            can_disable = len(enabled_switches) > 3
            for s in switch_dict.values():
                s.set_sensitive(True if can_disable or not s.get_active() else False)

        def on_metric_toggle(switch, gparam, switch_dict): enforce_minimum_metrics(switch_dict)
        for k_s, s_s in self.metrics_switches.items(): s_s.connect("notify::active", on_metric_toggle, self.metrics_switches)
        for k_s, s_s in self.metrics_small_switches.items(): s_s.connect("notify::active", on_metric_toggle, self.metrics_small_switches)
        enforce_minimum_metrics(self.metrics_switches)
        enforce_minimum_metrics(self.metrics_small_switches)
        
        disks_label = Label(label="Disk directories for Metrics", h_align="start", v_align="center")
        vbox.add(disks_label)
        self.disk_entries = Box(orientation="v", spacing=8, h_align="start")
        
        self._create_disk_edit_entry_func = lambda path: self._add_disk_entry_widget(path)

        for p in bind_vars.get('bar_metrics_disks', ["/"]): self._create_disk_edit_entry_func(p)
        vbox.add(self.disk_entries)
        
        add_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        add_btn = Button(label="Add new disk", on_clicked=lambda _: self._create_disk_edit_entry_func("/"))
        add_container.add(add_btn)
        vbox.add(add_container)

        return scrolled_window

    def _add_disk_entry_widget(self, path):
        """Helper para añadir una fila de entrada de disco al Box disk_entries."""
        bar = Box(orientation="h", spacing=10, h_align="start")
        entry = Entry(text=path, h_expand=True)
        bar.add(entry)
        x_btn = Button(label="X")
        x_btn.connect("clicked", lambda _, current_bar_to_remove=bar: self.disk_entries.remove(current_bar_to_remove))
        bar.add(x_btn)
        self.disk_entries.add(bar)
        self.disk_entries.show_all()


    def create_about_tab(self):
        vbox = Box(orientation="v", spacing=18, style="margin: 30px;")
        vbox.add(Label(markup=f"<b>{APP_NAME_CAP}</b>", h_align="start", style="font-size: 1.5em; margin-bottom: 8px;"))
        vbox.add(Label(label="A hackable shell for Hyprland, powered by Fabric.", h_align="start", style="margin-bottom: 12px;"))
        repo_box = Box(orientation="h", spacing=6, h_align="start")
        repo_label = Label(label="GitHub:", h_align="start")
        repo_link = Label(markup='<a href="https://github.com/Axenide/Ax-Shell">https://github.com/Axenide/Ax-Shell</a>')
        repo_box.add(repo_label); repo_box.add(repo_link)
        vbox.add(repo_box)
        def on_kofi_clicked(_): import webbrowser; webbrowser.open("https://ko-fi.com/Axenide")
        kofi_btn = Button(label="Support on Ko-Fi ❤️", on_clicked=on_kofi_clicked, tooltip_text="Support Axenide on Ko-Fi", style="margin-top: 18px; min-width: 160px;")
        vbox.add(kofi_btn)
        vbox.add(Box(v_expand=True))
        return vbox

    def on_ws_num_changed(self, switch, gparam):
        is_active = switch.get_active()
        self.ws_chinese_switch.set_sensitive(is_active)
        if not is_active: self.ws_chinese_switch.set_active(False)

    def on_position_changed(self, combo):
        position = combo.get_active_text()
        is_vertical = position in ["Left", "Right"]
        self.centered_switch.set_sensitive(is_vertical)
        if not is_vertical:
            self.centered_switch.set_active(False)

    def on_dock_enabled_changed(self, switch, gparam):
        is_active = switch.get_active()
        self.dock_hover_switch.set_sensitive(is_active)
        if not is_active: self.dock_hover_switch.set_active(False)

    def on_select_face_icon(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Select Face Icon", transient_for=self.get_toplevel(), action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image files")
        for mime in ["image/png", "image/jpeg"]: image_filter.add_mime_type(mime)
        for pattern in ["*.png", "*.jpg", "*.jpeg"]: image_filter.add_pattern(pattern)
        dialog.add_filter(image_filter)
        if dialog.run() == Gtk.ResponseType.OK:
            self.selected_face_icon = dialog.get_filename()
            self.face_status_label.label = f"Selected: {os.path.basename(self.selected_face_icon)}"
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(self.selected_face_icon, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
            except Exception as e:
                 print(f"Error loading selected face icon preview: {e}")
                 self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        dialog.destroy()

    def on_accept(self, widget):
        
        current_bind_vars_snapshot = {} 
        for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
            current_bind_vars_snapshot[prefix_key] = prefix_entry.get_text()
            current_bind_vars_snapshot[suffix_key] = suffix_entry.get_text()

        current_bind_vars_snapshot['wallpapers_dir'] = self.wall_dir_chooser.get_filename()
        
        current_bind_vars_snapshot['bar_position'] = self.position_combo.get_active_text()
        current_bind_vars_snapshot['vertical'] = current_bind_vars_snapshot['bar_position'] in ["Left", "Right"]
        
        current_bind_vars_snapshot['centered_bar'] = self.centered_switch.get_active()
        current_bind_vars_snapshot['datetime_12h_format'] = self.datetime_12h_switch.get_active()
        current_bind_vars_snapshot['dock_enabled'] = self.dock_switch.get_active()
        current_bind_vars_snapshot['dock_always_occluded'] = self.dock_hover_switch.get_active()
        current_bind_vars_snapshot['dock_icon_size'] = int(self.dock_size_scale.value)
        current_bind_vars_snapshot['terminal_command'] = self.terminal_entry.get_text()
        current_bind_vars_snapshot['corners_visible'] = self.corners_switch.get_active()
        current_bind_vars_snapshot['bar_workspace_show_number'] = self.ws_num_switch.get_active()
        current_bind_vars_snapshot['bar_workspace_use_chinese_numerals'] = self.ws_chinese_switch.get_active()
        current_bind_vars_snapshot['bar_theme'] = self.bar_theme_combo.get_active_text()
        current_bind_vars_snapshot['dock_theme'] = self.dock_theme_combo.get_active_text()
        current_bind_vars_snapshot['panel_theme'] = self.panel_theme_combo.get_active_text()
        current_bind_vars_snapshot[PANEL_POSITION_KEY] = self.panel_position_combo.get_active_text()
        selected_notif_pos_text = self.notification_pos_combo.get_active_text()
        if selected_notif_pos_text:
            current_bind_vars_snapshot[NOTIF_POS_KEY] = selected_notif_pos_text
        else:
            current_bind_vars_snapshot[NOTIF_POS_KEY] = NOTIF_POS_DEFAULT

        for component_name, switch in self.component_switches.items():
            current_bind_vars_snapshot[f'bar_{component_name}_visible'] = switch.get_active()

        current_bind_vars_snapshot['metrics_visible'] = {k: s.get_active() for k, s in self.metrics_switches.items()}
        current_bind_vars_snapshot['metrics_small_visible'] = {k: s.get_active() for k, s in self.metrics_small_switches.items()}
        current_bind_vars_snapshot['bar_metrics_disks'] = [
            child.get_children()[0].get_text() for child in self.disk_entries.get_children() if isinstance(child, Gtk.Box) and child.get_children() and isinstance(child.get_children()[0], Entry)
        ]


        selected_icon_path = self.selected_face_icon
        replace_lock = self.lock_switch and self.lock_switch.get_active()
        replace_idle = self.idle_switch and self.idle_switch.get_active()

        if self.selected_face_icon:
             self.selected_face_icon = None
             self.face_status_label.label = ""

        def _apply_and_reload_task_thread():
            nonlocal current_bind_vars_snapshot 
            
            from . import settings_utils
            settings_utils.bind_vars.clear()
            settings_utils.bind_vars.update(current_bind_vars_snapshot)


            start_time = time.time()
            print(f"{start_time:.4f}: Background task started.")

            config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
            os.makedirs(os.path.dirname(config_json), exist_ok=True)
            try:
                with open(config_json, 'w') as f:
                    json.dump(settings_utils.bind_vars, f, indent=4) 
                print(f"{time.time():.4f}: Saved config.json.")
            except Exception as e: print(f"Error saving config.json: {e}")

            if selected_icon_path:
                print(f"{time.time():.4f}: Processing face icon...")
                try:
                    img = Image.open(selected_icon_path)
                    side = min(img.size); left = (img.width - side)//2; top = (img.height - side)//2
                    cropped_img = img.crop((left, top, left + side, top + side))
                    face_icon_dest = os.path.expanduser("~/.face.icon")
                    cropped_img.save(face_icon_dest, format='PNG')
                    print(f"{time.time():.4f}: Face icon saved to {face_icon_dest}")
                    GLib.idle_add(self._update_face_image_widget, face_icon_dest)
                except Exception as e: print(f"Error processing face icon: {e}")
                print(f"{time.time():.4f}: Finished processing face icon.")

            if replace_lock:
                print(f"{time.time():.4f}: Replacing hyprlock config...")
                src = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
                dest = os.path.expanduser("~/.config/hypr/hyprlock.conf")
                if os.path.exists(src): backup_and_replace(src, dest, "Hyprlock")
                else: print(f"Warning: Source hyprlock config not found at {src}")
                print(f"{time.time():.4f}: Finished replacing hyprlock config.")

            if replace_idle:
                print(f"{time.time():.4f}: Replacing hypridle config...")
                src = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
                dest = os.path.expanduser("~/.config/hypr/hypridle.conf")
                if os.path.exists(src): backup_and_replace(src, dest, "Hypridle")
                else: print(f"Warning: Source hypridle config not found at {src}")
                print(f"{time.time():.4f}: Finished replacing hypridle config.")

            print(f"{time.time():.4f}: Checking/Appending hyprland.conf source string...")
            hypr_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
            try:
                from .settings_constants import SOURCE_STRING
                needs_append = True
                if os.path.exists(hypr_path):
                    with open(hypr_path, "r") as f:
                        if SOURCE_STRING.strip() in f.read(): needs_append = False
                else: os.makedirs(os.path.dirname(hypr_path), exist_ok=True)
                
                if needs_append:
                    with open(hypr_path, "a") as f: f.write("\n" + SOURCE_STRING)
                    print(f"Appended source string to {hypr_path}")
            except Exception as e: print(f"Error updating {hypr_path}: {e}")
            print(f"{time.time():.4f}: Finished checking/appending hyprland.conf source string.")

            print(f"{time.time():.4f}: Running start_config()...")
            start_config() 
            print(f"{time.time():.4f}: Finished start_config().")

            print(f"{time.time():.4f}: Initiating Ax-Shell restart using Popen...")
            main_py = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/main.py")
            kill_cmd = f"killall {APP_NAME}"
            start_cmd = ["uwsm", "app", "--", "python", main_py]
            try:
                kill_proc = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                kill_proc.wait(timeout=2)
                print(f"{time.time():.4f}: killall process finished (o timed out).")
            except subprocess.TimeoutExpired: print("Warning: killall command timed out.")
            except Exception as e: print(f"Error running killall: {e}")
            
            try:
                subprocess.Popen(start_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                print(f"{APP_NAME_CAP} restart initiated via Popen.")
            except FileNotFoundError as e: print(f"Error restarting {APP_NAME_CAP}: Command not found ({e})")
            except Exception as e: print(f"Error restarting {APP_NAME_CAP} via Popen: {e}")
            
            print(f"{time.time():.4f}: Ax-Shell restart commands issued via Popen.")
            end_time = time.time()
            print(f"{end_time:.4f}: Background task finished (Total: {end_time - start_time:.4f}s).")

        thread = threading.Thread(target=_apply_and_reload_task_thread)
        thread.daemon = True
        thread.start()
        print("Configuration apply/reload task started in background.")

    def _update_face_image_widget(self, icon_path):
        try:
            if self.face_image and self.face_image.get_window(): 
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
        except Exception as e:
            print(f"Error reloading face icon preview: {e}")
            if self.face_image and self.face_image.get_window():
                self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)
        return GLib.SOURCE_REMOVE

    def on_reset(self, widget):
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(), flags=0, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text="Reset all settings to defaults?"
        )
        dialog.format_secondary_text("This will reset all keybindings and appearance settings to their default values.")
        if dialog.run() == Gtk.ResponseType.YES:
            from . import settings_utils
            from .settings_constants import DEFAULTS 

            settings_utils.bind_vars.clear()
            settings_utils.bind_vars.update(DEFAULTS.copy())

            for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
                prefix_entry.set_text(settings_utils.bind_vars[prefix_key])
                suffix_entry.set_text(settings_utils.bind_vars[suffix_key])

            self.wall_dir_chooser.set_filename(settings_utils.bind_vars['wallpapers_dir'])
            
            positions = ["Top", "Bottom", "Left", "Right"]
            default_position = DEFAULTS.get('bar_position', "Top")
            try:
                self.position_combo.set_active(positions.index(default_position))
            except ValueError:
                self.position_combo.set_active(0)
                
            self.centered_switch.set_active(settings_utils.bind_vars.get('centered_bar', False))
            self.centered_switch.set_sensitive(default_position in ["Left", "Right"])
            
            self.datetime_12h_switch.set_active(settings_utils.bind_vars.get('datetime_12h_format', False))

            self.dock_switch.set_active(settings_utils.bind_vars.get('dock_enabled', True))
            self.dock_hover_switch.set_active(settings_utils.bind_vars.get('dock_always_occluded', False))
            self.dock_hover_switch.set_sensitive(self.dock_switch.get_active())
            self.dock_size_scale.set_value(settings_utils.bind_vars.get('dock_icon_size', 28))
            self.terminal_entry.set_text(settings_utils.bind_vars['terminal_command'])
            self.ws_num_switch.set_active(settings_utils.bind_vars.get('bar_workspace_show_number', False))
            self.ws_chinese_switch.set_active(settings_utils.bind_vars.get('bar_workspace_use_chinese_numerals', False))
            self.ws_chinese_switch.set_sensitive(self.ws_num_switch.get_active())
            
            default_theme_val = DEFAULTS.get('bar_theme', "Pills") 
            themes = ["Pills", "Dense", "Edge"]
            try:
                self.bar_theme_combo.set_active(themes.index(default_theme_val))
            except ValueError:
                self.bar_theme_combo.set_active(0) 

            default_dock_theme_val = DEFAULTS.get('dock_theme', "Pills")
            try:
                self.dock_theme_combo.set_active(themes.index(default_dock_theme_val))
            except ValueError:
                self.dock_theme_combo.set_active(0)

            default_panel_theme_val = DEFAULTS.get('panel_theme', "Notch")
            panel_themes_options = ["Notch", "Panel"] 
            try:
                self.panel_theme_combo.set_active(panel_themes_options.index(default_panel_theme_val))
            except ValueError:
                self.panel_theme_combo.set_active(0)
            
            default_panel_position_val = DEFAULTS.get(PANEL_POSITION_KEY, PANEL_POSITION_DEFAULT)
            try:
                self.panel_position_combo.set_active(self.panel_position_options.index(default_panel_position_val))
            except ValueError:
                try:
                    self.panel_position_combo.set_active(self.panel_position_options.index(PANEL_POSITION_DEFAULT))
                except ValueError:
                    self.panel_position_combo.set_active(0) 

            default_notif_pos_val = DEFAULTS.get(NOTIF_POS_KEY, NOTIF_POS_DEFAULT)
            notification_positions_list = ["Top", "Bottom"]
            try:
                self.notification_pos_combo.set_active(notification_positions_list.index(default_notif_pos_val))
            except ValueError:
                self.notification_pos_combo.set_active(0)

            for name, switch in self.component_switches.items():
                 switch.set_active(settings_utils.bind_vars.get(f'bar_{name}_visible', True))
            self.corners_switch.set_active(settings_utils.bind_vars.get('corners_visible', True))

            metrics_vis_defaults = DEFAULTS.get('metrics_visible', {})
            for k, s_widget in self.metrics_switches.items(): s_widget.set_active(metrics_vis_defaults.get(k, True))
            
            metrics_small_vis_defaults = DEFAULTS.get('metrics_small_visible', {})
            for k, s_widget in self.metrics_small_switches.items(): s_widget.set_active(metrics_small_vis_defaults.get(k, True))
            
            def enforce_minimum_metrics(switch_dict):
                enabled_switches = [s_widget for s_widget in switch_dict.values() if s_widget.get_active()]
                can_disable = len(enabled_switches) > 3
                for s_widget in switch_dict.values():
                    s_widget.set_sensitive(True if can_disable or not s_widget.get_active() else False)
            enforce_minimum_metrics(self.metrics_switches)
            enforce_minimum_metrics(self.metrics_small_switches)

            for child in list(self.disk_entries.get_children()): self.disk_entries.remove(child)
            
            for p in DEFAULTS.get('bar_metrics_disks', ["/"]):
                self._add_disk_edit_entry_func(p)

            self._update_panel_position_sensitivity()

            self.selected_face_icon = None
            self.face_status_label.label = ""
            current_face = os.path.expanduser("~/.face.icon") 
            try:
                 pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(current_face, 64, 64) if os.path.exists(current_face) else None
                 if pixbuf: self.face_image.set_from_pixbuf(pixbuf)
                 else: self.face_image.set_from_icon_name("user-info", Gtk.IconSize.DIALOG)
            except Exception: self.face_image.set_from_icon_name("image-missing", Gtk.IconSize.DIALOG)

            if self.lock_switch: self.lock_switch.set_active(False)
            if self.idle_switch: self.idle_switch.set_active(False)
            print("Settings reset to defaults.")
        dialog.destroy()

    def on_close(self, widget):
        if self.application: self.application.quit()
        else: self.destroy()
