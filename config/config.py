import os
import shutil
import json
import sys
from pathlib import Path
import subprocess # Add subprocess
import threading # Add threading
import time # Add time for logging

import toml
from PIL import Image
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GLib # Add GLib

# Fabric Imports
from fabric import Application
from fabric.widgets.window import Window
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.image import Image as FabricImage # Alias to avoid clash
from fabric.widgets.stack import Stack
from fabric.widgets.scale import Scale
from fabric.utils.helpers import exec_shell_command, exec_shell_command_async # Ensure async helper is imported

# Assuming data.py exists in the same directory or is accessible via sys.path
# If data.py is in ./config/data.py relative to this script's original location:
try:
    # Adjust path relative to the *original* location if needed
    sys.path.insert(0, str(Path(__file__).resolve().parent / '../config'))
    from data import (
        APP_NAME, APP_NAME_CAP, CONFIG_DIR, HOME_DIR, WALLPAPERS_DIR_DEFAULT
    )
except ImportError as e:
    print(f"Error importing data constants: {e}")
    # Provide fallback defaults if import fails
    APP_NAME = "ax-shell"
    APP_NAME_CAP = "Ax-Shell"
    CONFIG_DIR = "~/.config/Ax-Shell"
    HOME_DIR = "~"
    WALLPAPERS_DIR_DEFAULT = "~/Pictures/Wallpapers"


SOURCE_STRING = f"""
# {APP_NAME_CAP}
source = ~/.config/{APP_NAME_CAP}/config/hypr/{APP_NAME}.conf
"""

DEFAULTS = {
    'prefix_restart': "SUPER ALT",
    'suffix_restart': "B",
    'prefix_axmsg': "SUPER",
    'suffix_axmsg': "A",
    'prefix_dash': "SUPER",
    'suffix_dash': "D",
    'prefix_bluetooth': "SUPER",
    'suffix_bluetooth': "B",
    'prefix_pins': "SUPER",
    'suffix_pins': "Q",
    'prefix_kanban': "SUPER",
    'suffix_kanban': "N",
    'prefix_launcher': "SUPER",
    'suffix_launcher': "R",
    'prefix_tmux': "SUPER",
    'suffix_tmux': "T",
    'prefix_cliphist': "SUPER",
    'suffix_cliphist': "V",
    'prefix_toolbox': "SUPER",
    'suffix_toolbox': "S",
    'prefix_overview': "SUPER",
    'suffix_overview': "TAB",
    'prefix_wallpapers': "SUPER",
    'suffix_wallpapers': "COMMA",
    'prefix_emoji': "SUPER",
    'suffix_emoji': "PERIOD",
    'prefix_power': "SUPER",
    'suffix_power': "ESCAPE",
    'prefix_toggle': "SUPER CTRL",
    'suffix_toggle': "B",
    'prefix_css': "SUPER SHIFT",
    'suffix_css': "B",
    'wallpapers_dir': WALLPAPERS_DIR_DEFAULT,
    'prefix_restart_inspector': "SUPER CTRL ALT",
    'suffix_restart_inspector': "B",
    'vertical': False,
    'centered_bar': False,
    'terminal_command': "kitty -e",
    'dock_enabled': True,
    'dock_icon_size': 28,
    'dock_always_occluded': False, # Added default
    'bar_workspace_show_number': False, # Added default for workspace number visibility
    'bar_workspace_use_chinese_numerals': False, # Added default for Chinese numerals
    # Defaults for bar components (assuming True initially)
    'bar_button_apps_visible': True,
    'bar_systray_visible': True,
    'bar_control_visible': True,
    'bar_network_visible': True,
    'bar_button_tools_visible': True,
    'bar_button_overview_visible': True,
    'bar_ws_container_visible': True,
    'bar_weather_visible': True,
    'bar_battery_visible': True,
    'bar_metrics_visible': True,
    'bar_language_visible': True,
    'bar_date_time_visible': True,
    'bar_button_power_visible': True,
    'corners_visible': True, # Added default for corners visibility
    'bar_metrics_disks': ["/"],
    # Add metric visibility defaults
    'metrics_visible': {
        'cpu': True,
        'ram': True,
        'disk': True,
        'gpu': True,
    },
    'metrics_small_visible': {
        'cpu': True,
        'ram': True,
        'disk': True,
        'gpu': True,
    },
}

bind_vars = DEFAULTS.copy()

def deep_update(target: dict, update: dict) -> dict:
    """
    Recursively update a nested dictionary with values from another dictionary.
    """
    for key, value in update.items():
        if isinstance(value, dict):
            target[key] = deep_update(target.get(key, {}), value)
        else:
            target[key] = value
    return target

def ensure_matugen_config():
    """
    Ensure that the matugen configuration file exists and is updated
    with the expected settings.
    """
    expected_config = {
        'config': {
            'reload_apps': True,
            'wallpaper': {
                'command': 'swww',
                'arguments': [
                    'img', '-t', 'outer',
                    '--transition-duration', '1.5',
                    '--transition-step', '255',
                    '--transition-fps', '60',
                    '-f', 'Nearest'
                ],
                'set': True
            },
            'custom_colors': {
                'red': {
                    'color': "#FF0000",
                    'blend': True
                },
                'green': {
                    'color': "#00FF00",
                    'blend': True
                },
                'yellow': {
                    'color': "#FFFF00",
                    'blend': True
                },
                'blue': {
                    'color': "#0000FF",
                    'blend': True
                },
                'magenta': {
                    'color': "#FF00FF",
                    'blend': True
                },
                'cyan': {
                    'color': "#00FFFF",
                    'blend': True
                },
                'white': {
                    'color': "#FFFFFF",
                    'blend': True
                }
            }
        },
        'templates': {
            'hyprland': {
                'input_path': f'~/.config/{APP_NAME_CAP}/config/matugen/templates/hyprland-colors.conf',
                'output_path': f'~/.config/{APP_NAME_CAP}/config/hypr/colors.conf'
            },
            f'{APP_NAME}': {
                'input_path': f'~/.config/{APP_NAME_CAP}/config/matugen/templates/{APP_NAME}.css',
                'output_path': f'~/.config/{APP_NAME_CAP}/styles/colors.css',
                'post_hook': f"fabric-cli exec {APP_NAME} 'app.set_css()' &"
            }
        }
    }

    config_path = os.path.expanduser('~/.config/matugen/config.toml')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Load any existing configuration
    existing_config = {}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            existing_config = toml.load(f)
        # Backup existing configuration
        shutil.copyfile(config_path, config_path + '.bak')

    # Merge configurations
    merged_config = deep_update(existing_config, expected_config)
    with open(config_path, 'w') as f:
        toml.dump(merged_config, f)

    # Expand paths for checking
    current_wall = os.path.expanduser("~/.current.wall")
    hypr_colors = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/colors.conf")
    css_colors = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/styles/colors.css")
    
    # Check if any of the required files are missing
    if not os.path.exists(current_wall) or not os.path.exists(hypr_colors) or not os.path.exists(css_colors):
        # Ensure the directories exist
        os.makedirs(os.path.dirname(hypr_colors), exist_ok=True)
        os.makedirs(os.path.dirname(css_colors), exist_ok=True)
        
        # Use the example wallpaper if no current wallpaper
        if not os.path.exists(current_wall):
            image_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/assets/wallpapers_example/example-1.jpg")
            # Create symlink to the example wallpaper if it doesn't exist already
            if os.path.exists(image_path) and not os.path.exists(current_wall):
                try:
                    os.symlink(image_path, current_wall)
                except FileExistsError:
                    os.remove(current_wall)
                    os.symlink(image_path, current_wall)
        else:
            # Use the existing wallpaper
            image_path = os.path.realpath(current_wall) if os.path.islink(current_wall) else current_wall
        
        # Run matugen to generate the color files
        # Run matugen asynchronously
        print(f"Generating color theme from wallpaper: {image_path}")
        try:
            # Use exec_shell_command_async instead of subprocess.run
            # Ensure the image path is properly quoted for the shell command
            matugen_cmd = f"matugen image '{image_path}'"
            exec_shell_command_async(matugen_cmd)
            print("Matugen color theme generation initiated.")
            # Note: We can't easily check for success here asynchronously without callbacks.
        except FileNotFoundError:
            print("Error: matugen command not found. Please install matugen.")
        except Exception as e:
            # Catch potential errors during command initiation
            print(f"Error initiating matugen: {e}")


def load_bind_vars():
    """
    Load saved key binding variables from JSON, if available.
    """
    config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
    if os.path.exists(config_json):
        try:
            with open(config_json, 'r') as f:
                saved_vars = json.load(f)
                # Update defaults with saved values, ensuring all keys exist
                for key in DEFAULTS:
                    if key in saved_vars:
                        bind_vars[key] = saved_vars[key]
                    else:
                        bind_vars[key] = DEFAULTS[key]
                # Ensure nested dicts for metric visibility
                for vis_key in ['metrics_visible', 'metrics_small_visible']:
                    if vis_key in DEFAULTS:
                        if vis_key not in bind_vars or not isinstance(bind_vars[vis_key], dict):
                            bind_vars[vis_key] = DEFAULTS[vis_key].copy()
                        else:
                            for m in DEFAULTS[vis_key]:
                                if m not in bind_vars[vis_key]:
                                    bind_vars[vis_key][m] = DEFAULTS[vis_key][m]
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {config_json}. Using defaults.")
            bind_vars.update(DEFAULTS) # Ensure defaults on error
        except Exception as e:
            print(f"Error loading config from {config_json}: {e}. Using defaults.")
            bind_vars.update(DEFAULTS) # Ensure defaults on error
    else:
         # Ensure defaults are set if file doesn't exist
         bind_vars.update(DEFAULTS)


def generate_hyprconf() -> str:
    """
    Generate the Hypr configuration string using the current bind_vars.
    """
    home = os.path.expanduser('~')
    return f"""exec-once = uwsm-app $(/home/mathias/.config/Ax-Shell/.venv/bin/python {home}/.config/{APP_NAME_CAP}/main.py)
exec = pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle
exec = uwsm app -- swww-daemon
exec-once =  wl-paste --type text --watch cliphist store
exec-once =  wl-paste --type image --watch cliphist store

$fabricSend = fabric-cli exec {APP_NAME}
$axMessage = notify-send "Axenide" "What are you doing?" -i "{home}/.config/{APP_NAME_CAP}/assets/ax.png" -a "Source Code" -A "Be patient. 🍙"

bind = {bind_vars['prefix_restart']}, {bind_vars['suffix_restart']}, exec, killall {APP_NAME}; uwsm-app $(/home/mathias/.config/Ax-Shell/.venv/bin/python {home}/.config/{APP_NAME_CAP}/main.py) # Reload {APP_NAME_CAP} | Default: SUPER ALT + B
bind = {bind_vars['prefix_axmsg']}, {bind_vars['suffix_axmsg']}, exec, $axMessage # Message | Default: SUPER + A
bind = {bind_vars['prefix_dash']}, {bind_vars['suffix_dash']}, exec, $fabricSend 'notch.open_notch("dashboard")' # Dashboard | Default: SUPER + D
bind = {bind_vars['prefix_bluetooth']}, {bind_vars['suffix_bluetooth']}, exec, $fabricSend 'notch.open_notch("bluetooth")' # Bluetooth | Default: SUPER + B
bind = {bind_vars['prefix_pins']}, {bind_vars['suffix_pins']}, exec, $fabricSend 'notch.open_notch("pins")' # Pins | Default: SUPER + Q
bind = {bind_vars['prefix_kanban']}, {bind_vars['suffix_kanban']}, exec, $fabricSend 'notch.open_notch("kanban")' # Kanban | Default: SUPER + N
bind = {bind_vars['prefix_launcher']}, {bind_vars['suffix_launcher']}, exec, $fabricSend 'notch.open_notch("launcher")' # App Launcher | Default: SUPER + R
bind = {bind_vars['prefix_tmux']}, {bind_vars['suffix_tmux']}, exec, $fabricSend 'notch.open_notch("tmux")' # App Launcher | Default: SUPER + T
bind = {bind_vars['prefix_cliphist']}, {bind_vars['suffix_cliphist']}, exec, $fabricSend 'notch.open_notch("cliphist")' # App Launcher | Default: SUPER + V
bind = {bind_vars['prefix_toolbox']}, {bind_vars['suffix_toolbox']}, exec, $fabricSend 'notch.open_notch("tools")' # Toolbox | Default: SUPER + S
bind = {bind_vars['prefix_overview']}, {bind_vars['suffix_overview']}, exec, $fabricSend 'notch.open_notch("overview")' # Overview | Default: SUPER + TAB
bind = {bind_vars['prefix_wallpapers']}, {bind_vars['suffix_wallpapers']}, exec, $fabricSend 'notch.open_notch("wallpapers")' # Wallpapers | Default: SUPER + COMMA
bind = {bind_vars['prefix_emoji']}, {bind_vars['suffix_emoji']}, exec, $fabricSend 'notch.open_notch("emoji")' # Emoji | Default: SUPER + PERIOD
bind = {bind_vars['prefix_power']}, {bind_vars['suffix_power']}, exec, $fabricSend 'notch.open_notch("power")' # Power Menu | Default: SUPER + ESCAPE
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'bar.toggle_hidden()' # Toggle Bar | Default: SUPER CTRL + B
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'notch.toggle_hidden()' # Toggle Notch | Default: SUPER CTRL + B
bind = {bind_vars['prefix_css']}, {bind_vars['suffix_css']}, exec, $fabricSend 'app.set_css()' # Reload CSS | Default: SUPER SHIFT + B
bind = {bind_vars['prefix_restart_inspector']}, {bind_vars['suffix_restart_inspector']}, exec, killall {APP_NAME}; uwsm-app $(GTK_DEBUG=interactive /home/mathias/.config/Ax-Shell/.venv/bin/python {home}/.config/{APP_NAME_CAP}/main.py) # Restart with inspector | Default: SUPER CTRL ALT + B

# Wallpapers directory: {bind_vars['wallpapers_dir']}

source = {home}/.config/{APP_NAME_CAP}/config/hypr/colors.conf

layerrule = noanim, fabric

exec = cp $wallpaper ~/.current.wall

general {{
    col.active_border = 0xff$primary
    col.inactive_border = 0xff$surface
    gaps_in = 2
    gaps_out = 4
    border_size = 2
    layout = dwindle
}}

cursor {{
  no_warps=true
}}

decoration {{
    blur {{
        enabled = yes
        size = 5
        passes = 3
        new_optimizations = yes
        contrast = 1
        brightness = 1
    }}
    rounding = 14
    shadow {{
      enabled = true
      range = 10
      render_power = 2
      color = rgba(0, 0, 0, 0.25)
    }}
}}

animations {{
    enabled = yes
    bezier = myBezier, 0.4, 0, 0.2, 1
    animation = windows, 1, 2.5, myBezier, popin 80%
    animation = border, 1, 2.5, myBezier
    animation = fade, 1, 2.5, myBezier
    animation = workspaces, 1, 2.5, myBezier, {'slidefadevert' if bind_vars['vertical'] else 'slidefade'} 20%
}}
"""


def ensure_face_icon():
    """
    Ensure the face icon exists. If not, copy the default icon.
    """
    face_icon_path = os.path.expanduser("~/.face.icon")
    default_icon_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/assets/default.png")
    if not os.path.exists(face_icon_path) and os.path.exists(default_icon_path):
        try:
            shutil.copy(default_icon_path, face_icon_path)
        except Exception as e:
            print(f"Error copying default face icon: {e}")

def backup_and_replace(src: str, dest: str, config_name: str):
    """
    Backup the existing configuration file and replace it with a new one.
    """
    try:
        if os.path.exists(dest):
            backup_path = dest + ".bak"
            shutil.copy(dest, backup_path)
            print(f"{config_name} config backed up to {backup_path}")
        shutil.copy(src, dest)
        print(f"{config_name} config replaced from {src}")
    except Exception as e:
        print(f"Error backing up/replacing {config_name} config: {e}")

# --- Fabric GUI Class ---

class HyprConfGUI(Window):
    def __init__(self, show_lock_checkbox: bool, show_idle_checkbox: bool, **kwargs):
        super().__init__(
            title="Ax-Shell Settings",
            name="axshell-settings-window",
            size=(650, 550), # Adjusted size for vertical tabs
            **kwargs,
        )

        self.set_resizable(False)

        self.selected_face_icon = None
        self.show_lock_checkbox = show_lock_checkbox
        self.show_idle_checkbox = show_idle_checkbox

        # Overall vertical box to hold the main content and bottom buttons
        root_box = Box(orientation="v", spacing=10, style="margin: 10px;")
        self.add(root_box)

        # Main horizontal box for switcher and stack
        main_content_box = Box(orientation="h", spacing=6, v_expand=True, h_expand=True)
        root_box.add(main_content_box)

        # --- Tab Control ---
        self.tab_stack = Stack(
             transition_type="slide-up-down", # Change transition for vertical feel
             transition_duration=250,
             v_expand=True, h_expand=True
        )

        # Create tabs and add to stack
        self.key_bindings_tab_content = self.create_key_bindings_tab()
        self.appearance_tab_content = self.create_appearance_tab()
        self.system_tab_content = self.create_system_tab()
        self.about_tab_content = self.create_about_tab()  # Add About tab

        self.tab_stack.add_titled(self.key_bindings_tab_content, "key_bindings", "Key Bindings")
        self.tab_stack.add_titled(self.appearance_tab_content, "appearance", "Appearance")
        self.tab_stack.add_titled(self.system_tab_content, "system", "System")
        self.tab_stack.add_titled(self.about_tab_content, "about", "About")  # Add About tab to stack

        # Use Gtk.StackSwitcher vertically on the left
        tab_switcher = Gtk.StackSwitcher()
        tab_switcher.set_stack(self.tab_stack)
        tab_switcher.set_orientation(Gtk.Orientation.VERTICAL) # Set vertical orientation
        # Optional: Adjust alignment if needed
        # tab_switcher.set_valign(Gtk.Align.START)

        # Add switcher to the left of the main content box
        main_content_box.add(tab_switcher)

        # Add stack to the right of the main content box
        main_content_box.add(self.tab_stack)


        # --- Bottom Buttons ---
        button_box = Box(orientation="h", spacing=10, h_align="end")

        reset_btn = Button(label="Reset to Defaults", on_clicked=self.on_reset)
        button_box.add(reset_btn)

        # Add Close button back
        close_btn = Button(label="Close", on_clicked=self.on_close)
        button_box.add(close_btn)

        accept_btn = Button(label="Apply & Reload", on_clicked=self.on_accept)
        button_box.add(accept_btn)

        # Add button box to the bottom of the root box
        root_box.add(button_box)

    def create_key_bindings_tab(self):
        """Create tab for key bindings configuration using Fabric widgets and Gtk.Grid."""
        scrolled_window = ScrolledWindow(
            h_scrollbar_policy="never", 
            v_scrollbar_policy="automatic",
            h_expand=True,
            v_expand=True
        )
        # Remove fixed height constraints to allow stack to fill space
        scrolled_window.set_min_content_height(300)
        scrolled_window.set_max_content_height(300)

        # Main container with padding
        main_vbox = Box(orientation="v", spacing=10, style="margin: 15px;")
        scrolled_window.add(main_vbox)

        # Create a grid for key bindings
        keybind_grid = Gtk.Grid()
        keybind_grid.set_column_spacing(10)
        keybind_grid.set_row_spacing(8)
        keybind_grid.set_margin_start(5)
        keybind_grid.set_margin_end(5)
        keybind_grid.set_margin_top(5)
        keybind_grid.set_margin_bottom(5)
        
        # Header Row
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
            ("Emoji Picker", 'prefix_emoji', 'suffix_emoji'),
            ("Power Menu", 'prefix_power', 'suffix_power'),
            ("Toggle Bar and Notch", 'prefix_toggle', 'suffix_toggle'),
            ("Reload CSS", 'prefix_css', 'suffix_css'),
            ("Restart with inspector", 'prefix_restart_inspector', 'suffix_restart_inspector'),
        ]

        # Populate the grid with entries
        for i, (label_text, prefix_key, suffix_key) in enumerate(bindings):
            row = i + 1  # Start at row 1 after headers
            
            # Action label
            binding_label = Label(label=label_text, h_align="start")
            keybind_grid.attach(binding_label, 0, row, 1, 1)
            
            # Prefix entry
            prefix_entry = Entry(text=bind_vars[prefix_key])
            keybind_grid.attach(prefix_entry, 1, row, 1, 1)
            
            # Plus separator
            plus_label = Label(label="+", h_align="center")
            keybind_grid.attach(plus_label, 2, row, 1, 1)
            
            # Suffix entry
            suffix_entry = Entry(text=bind_vars[suffix_key])
            keybind_grid.attach(suffix_entry, 3, row, 1, 1)
            
            self.entries.append((prefix_key, suffix_key, prefix_entry, suffix_entry))

        main_vbox.add(keybind_grid)
        return scrolled_window

    def create_appearance_tab(self):
        """Create tab for appearance settings using Fabric widgets and Gtk.Grid."""
        scrolled_window = ScrolledWindow(
            h_scrollbar_policy="never", 
            v_scrollbar_policy="automatic",
            h_expand=True,
            v_expand=True
        )
        # Remove fixed height constraints
        scrolled_window.set_min_content_height(300)
        scrolled_window.set_max_content_height(300)

        # Main container with padding
        vbox = Box(orientation="v", spacing=15, style="margin: 15px;")
        scrolled_window.add(vbox)

        # --- Top Row: Wallpapers & Profile Icon ---
        top_grid = Gtk.Grid()
        top_grid.set_column_spacing(20)
        top_grid.set_row_spacing(5)
        top_grid.set_margin_bottom(10)
        vbox.add(top_grid)

        # === WALLPAPERS SECTION ===
        wall_header = Label(markup="<b>Wallpapers</b>", h_align="start")
        top_grid.attach(wall_header, 0, 0, 1, 1)
        
        wall_label = Label(label="Directory:", h_align="start", v_align="center")
        top_grid.attach(wall_label, 0, 1, 1, 1)
        
        # Create a container for the file chooser to prevent stretching
        chooser_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        chooser_container.set_halign(Gtk.Align.START)
        chooser_container.set_valign(Gtk.Align.CENTER)
        
        self.wall_dir_chooser = Gtk.FileChooserButton(
            title="Select a folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.wall_dir_chooser.set_tooltip_text("Select the directory containing your wallpaper images")
        self.wall_dir_chooser.set_filename(bind_vars['wallpapers_dir'])
        # Set a minimum width for the file chooser to have adequate space
        self.wall_dir_chooser.set_size_request(180, -1)
        
        chooser_container.add(self.wall_dir_chooser)
        top_grid.attach(chooser_container, 1, 1, 1, 1)

        # === PROFILE ICON SECTION ===
        face_header = Label(markup="<b>Profile Icon</b>", h_align="start")
        top_grid.attach(face_header, 2, 0, 2, 1)
        
        # Current icon display
        current_face = os.path.expanduser("~/.face.icon")
        face_image_container = Box(style_classes=["image-frame"], 
                                  h_align="center", v_align="center")
        self.face_image = FabricImage(size=64)
        try:
            if os.path.exists(current_face):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(current_face, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
            else:
                 self.face_image.set_from_icon_name("user-info", 64)
        except Exception as e:
            print(f"Error loading face icon: {e}")
            self.face_image.set_from_icon_name("image-missing", 64)

        face_image_container.add(self.face_image)
        top_grid.attach(face_image_container, 2, 1, 1, 1)
        
        # Container for button to prevent stretching
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

        # --- Separator ---
        separator1 = Box(style="min-height: 1px; background-color: alpha(@fg_color, 0.2); margin: 5px 0px;",
                         h_expand=True)
        vbox.add(separator1)

        # --- Layout Options ---
        layout_header = Label(markup="<b>Layout Options</b>", h_align="start")
        vbox.add(layout_header)

        layout_grid = Gtk.Grid()
        layout_grid.set_column_spacing(20)
        layout_grid.set_row_spacing(10)
        layout_grid.set_margin_start(10)
        layout_grid.set_margin_top(5)
        vbox.add(layout_grid)

        # Vertical Layout
        vertical_label = Label(label="Vertical Layout", h_align="start", v_align="center")
        layout_grid.attach(vertical_label, 0, 0, 1, 1)
        
        # Container for switch to prevent stretching
        vertical_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vertical_switch_container.set_halign(Gtk.Align.START)
        vertical_switch_container.set_valign(Gtk.Align.CENTER)
        
        self.vertical_switch = Gtk.Switch()
        self.vertical_switch.set_active(bind_vars.get('vertical', False))
        self.vertical_switch.connect("notify::active", self.on_vertical_changed)
        vertical_switch_container.add(self.vertical_switch)
        
        layout_grid.attach(vertical_switch_container, 1, 0, 1, 1)

        # Centered Bar
        centered_label = Label(label="Centered Bar (Vertical Only)", h_align="start", v_align="center")
        layout_grid.attach(centered_label, 2, 0, 1, 1)
        
        # Container for switch to prevent stretching
        centered_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        centered_switch_container.set_halign(Gtk.Align.START)
        centered_switch_container.set_valign(Gtk.Align.CENTER)
        
        self.centered_switch = Gtk.Switch()
        self.centered_switch.set_active(bind_vars.get('centered_bar', False))
        self.centered_switch.set_sensitive(self.vertical_switch.get_active())
        centered_switch_container.add(self.centered_switch)
        
        layout_grid.attach(centered_switch_container, 3, 0, 1, 1)

        # Dock Options
        dock_label = Label(label="Show Dock", h_align="start", v_align="center")
        layout_grid.attach(dock_label, 0, 1, 1, 1)
        
        # Container for switch to prevent stretching
        dock_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        dock_switch_container.set_halign(Gtk.Align.START)
        dock_switch_container.set_valign(Gtk.Align.CENTER)
        
        self.dock_switch = Gtk.Switch()
        self.dock_switch.set_active(bind_vars.get('dock_enabled', True))
        self.dock_switch.connect("notify::active", self.on_dock_enabled_changed)
        dock_switch_container.add(self.dock_switch)
        
        layout_grid.attach(dock_switch_container, 1, 1, 1, 1)

        # Dock Hover
        dock_hover_label = Label(label="Show Dock Only on Hover", h_align="start", v_align="center")
        layout_grid.attach(dock_hover_label, 2, 1, 1, 1)
        
        # Container for switch to prevent stretching
        dock_hover_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        dock_hover_switch_container.set_halign(Gtk.Align.START)
        dock_hover_switch_container.set_valign(Gtk.Align.CENTER)
        
        self.dock_hover_switch = Gtk.Switch()
        self.dock_hover_switch.set_active(bind_vars.get('dock_always_occluded', False))
        self.dock_hover_switch.set_sensitive(self.dock_switch.get_active())
        dock_hover_switch_container.add(self.dock_hover_switch)
        
        layout_grid.attach(dock_hover_switch_container, 3, 1, 1, 1)

        # Dock Icon Size
        dock_size_label = Label(label="Dock Icon Size", h_align="start", v_align="center")
        layout_grid.attach(dock_size_label, 0, 2, 1, 1)

        self.dock_size_scale = Scale(
            min_value=16, max_value=48, value=bind_vars.get('dock_icon_size', 28),
            increments=(2, 4), draw_value=True, value_position="right", digits=0,
            h_expand=True
        )
        layout_grid.attach(self.dock_size_scale, 1, 2, 3, 1)

        # Workspace Number (Row 3)
        ws_num_label = Label(label="Show Workspace Numbers", h_align="start", v_align="center")
        layout_grid.attach(ws_num_label, 0, 3, 1, 1) # Attach to row 3, col 0

        # Container for switch to prevent stretching
        ws_num_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ws_num_switch_container.set_halign(Gtk.Align.START)
        ws_num_switch_container.set_valign(Gtk.Align.CENTER)

        self.ws_num_switch = Gtk.Switch()
        self.ws_num_switch.set_active(bind_vars.get('bar_workspace_show_number', False))
        self.ws_num_switch.connect("notify::active", self.on_ws_num_changed) # Connect signal
        ws_num_switch_container.add(self.ws_num_switch)

        layout_grid.attach(ws_num_switch_container, 1, 3, 1, 1) # Attach to row 3, col 1

        # Chinese Numerals (Row 3, Col 2-3) - Change attachment row and columns
        ws_chinese_label = Label(label="Use Chinese Numerals", h_align="start", v_align="center")
        layout_grid.attach(ws_chinese_label, 2, 3, 1, 1) # Attach to Row 3, Col 2

        # Container for switch
        ws_chinese_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        ws_chinese_switch_container.set_halign(Gtk.Align.START)
        ws_chinese_switch_container.set_valign(Gtk.Align.CENTER)

        self.ws_chinese_switch = Gtk.Switch()
        self.ws_chinese_switch.set_active(bind_vars.get('bar_workspace_use_chinese_numerals', False))
        self.ws_chinese_switch.set_sensitive(self.ws_num_switch.get_active()) # Initially sensitive based on number switch
        ws_chinese_switch_container.add(self.ws_chinese_switch)

        layout_grid.attach(ws_chinese_switch_container, 3, 3, 1, 1) # Attach to Row 3, Col 3

        # --- Separator ---
        separator2 = Box(style="min-height: 1px; background-color: alpha(@fg_color, 0.2); margin: 5px 0px;",
                         h_expand=True)
        vbox.add(separator2)

        # --- Modules (renamed from Bar Components) ---
        components_header = Label(markup="<b>Modules</b>", h_align="start")
        vbox.add(components_header)

        # Create a grid for bar components and other modules
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

        # Add corners visibility switch
        self.corners_switch = Gtk.Switch()
        self.corners_switch.set_active(bind_vars.get('corners_visible', True))
        
        # Calculate number of rows needed (we'll use 2 columns)
        num_components = len(component_display_names) + 1  # +1 for corners
        rows_per_column = (num_components + 1) // 2  # Ceiling division
        
        # First add corners to the top of first column
        corners_label = Label(label="Rounded Corners", h_align="start", v_align="center")
        components_grid.attach(corners_label, 0, 0, 1, 1)
        
        switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        switch_container.set_halign(Gtk.Align.START)
        switch_container.set_valign(Gtk.Align.CENTER)
        switch_container.add(self.corners_switch)
        components_grid.attach(switch_container, 1, 0, 1, 1)
        
        # Add components to grid in two columns
        for i, (component_name, display_name) in enumerate(component_display_names.items()):
            # Determine position: first half in column 0, second half in column 2
            # Start at row 1 to account for corners at row 0
            row = (i + 1) % rows_per_column  # +1 to start after corners
            col = 0 if i < (rows_per_column - 1) else 2  # Adjust column calculation
            
            component_label = Label(label=display_name, h_align="start", v_align="center")
            components_grid.attach(component_label, col, row, 1, 1)
            
            # Container for switch to prevent stretching
            switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            switch_container.set_halign(Gtk.Align.START)
            switch_container.set_valign(Gtk.Align.CENTER)
            
            component_switch = Gtk.Switch()
            config_key = f'bar_{component_name}_visible'
            component_switch.set_active(bind_vars.get(config_key, True))
            switch_container.add(component_switch)
            
            components_grid.attach(switch_container, col + 1, row, 1, 1)
            
            self.component_switches[component_name] = component_switch

        return scrolled_window

    def create_system_tab(self):
        """Create tab for system configurations using Fabric widgets and Gtk.Grid."""
        scrolled_window = ScrolledWindow(
            h_scrollbar_policy="never", 
            v_scrollbar_policy="automatic",
            h_expand=True,
            v_expand=True
        )
        # Remove fixed height constraints
        scrolled_window.set_min_content_height(300)
        scrolled_window.set_max_content_height(300)

        # Main container with padding
        vbox = Box(orientation="v", spacing=15, style="margin: 15px;")
        scrolled_window.add(vbox)

        # Create a grid for system settings
        system_grid = Gtk.Grid()
        system_grid.set_column_spacing(20)
        system_grid.set_row_spacing(10)
        system_grid.set_margin_bottom(15)
        vbox.add(system_grid)

        # === TERMINAL SETTINGS ===
        terminal_header = Label(markup="<b>Terminal Settings</b>", h_align="start")
        system_grid.attach(terminal_header, 0, 0, 2, 1)
        
        terminal_label = Label(label="Command:", h_align="start", v_align="center")
        system_grid.attach(terminal_label, 0, 1, 1, 1)
        
        self.terminal_entry = Entry(
            text=bind_vars['terminal_command'],
            tooltip_text="Command used to launch terminal apps (e.g., 'kitty -e')",
            h_expand=True
        )
        system_grid.attach(self.terminal_entry, 1, 1, 1, 1)
        
        hint_label = Label(markup="<small>Examples: 'kitty -e', 'alacritty -e', 'foot -e'</small>",
                           h_align="start")
        system_grid.attach(hint_label, 0, 2, 2, 1)

        # === HYPRLAND INTEGRATION ===
        hypr_header = Label(markup="<b>Hyprland Integration</b>", h_align="start")
        system_grid.attach(hypr_header, 2, 0, 2, 1)

        row = 1
        
        # Hyprland locks and idle settings
        self.lock_switch = None
        if self.show_lock_checkbox:
            lock_label = Label(label="Replace Hyprlock config", h_align="start", v_align="center")
            system_grid.attach(lock_label, 2, row, 1, 1)
            
            # Container for switch to prevent stretching
            lock_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            lock_switch_container.set_halign(Gtk.Align.START)
            lock_switch_container.set_valign(Gtk.Align.CENTER)
            
            self.lock_switch = Gtk.Switch()
            self.lock_switch.set_tooltip_text("Replace Hyprlock configuration with Ax-Shell's custom config")
            lock_switch_container.add(self.lock_switch)
            
            system_grid.attach(lock_switch_container, 3, row, 1, 1)
            row += 1

        self.idle_switch = None
        if self.show_idle_checkbox:
            idle_label = Label(label="Replace Hypridle config", h_align="start", v_align="center")
            system_grid.attach(idle_label, 2, row, 1, 1)
            
            # Container for switch to prevent stretching
            idle_switch_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            idle_switch_container.set_halign(Gtk.Align.START)
            idle_switch_container.set_valign(Gtk.Align.CENTER)
            
            self.idle_switch = Gtk.Switch()
            self.idle_switch.set_tooltip_text("Replace Hypridle configuration with Ax-Shell's custom config")
            idle_switch_container.add(self.idle_switch)
            
            system_grid.attach(idle_switch_container, 3, row, 1, 1)
            row += 1

        if self.show_lock_checkbox or self.show_idle_checkbox:
            note_label = Label(markup="<small>Existing configs will be backed up</small>",
                               h_align="start")
            system_grid.attach(note_label, 2, row, 2, 1)

        # --- System Metrics Options (moved from appearance tab) ---
        metrics_header = Label(markup="<b>System Metrics Options</b>", h_align="start")
        vbox.add(metrics_header)

        # Metrics visibility toggles
        metrics_grid = Gtk.Grid()
        metrics_grid.set_column_spacing(15)
        metrics_grid.set_row_spacing(8)
        metrics_grid.set_margin_start(10)
        metrics_grid.set_margin_top(5)
        vbox.add(metrics_grid)

        self.metrics_switches = {}
        self.metrics_small_switches = {}

        metric_names = {
            'cpu': "CPU",
            'ram': "RAM",
            'disk': "Disk",
            'gpu': "GPU",
        }

        # Normal metrics toggles
        metrics_grid.attach(Label(label="Show in Metrics", h_align="start"), 0, 0, 1, 1)
        for i, (key, label) in enumerate(metric_names.items()):
            switch = Gtk.Switch()
            switch.set_active(bind_vars.get('metrics_visible', {}).get(key, True))
            self.metrics_switches[key] = switch
            metrics_grid.attach(Label(label=label, h_align="start"), 0, i+1, 1, 1)
            metrics_grid.attach(switch, 1, i+1, 1, 1)

        # Small metrics toggles
        metrics_grid.attach(Label(label="Show in Small Metrics", h_align="start"), 2, 0, 1, 1)
        for i, (key, label) in enumerate(metric_names.items()):
            switch = Gtk.Switch()
            switch.set_active(bind_vars.get('metrics_small_visible', {}).get(key, True))
            self.metrics_small_switches[key] = switch
            metrics_grid.attach(Label(label=label, h_align="start"), 2, i+1, 1, 1)
            metrics_grid.attach(switch, 3, i+1, 1, 1)

        # Enforce minimum 3 enabled metrics
        def enforce_minimum_metrics(switch_dict):
            enabled = [k for k, s in switch_dict.items() if s.get_active()]
            for k, s in switch_dict.items():
                if len(enabled) <= 3 and s.get_active():
                    s.set_sensitive(False)
                else:
                    s.set_sensitive(True)

        def on_metric_toggle(switch, gparam, which):
            enforce_minimum_metrics(self.metrics_switches)

        def on_metric_small_toggle(switch, gparam, which):
            enforce_minimum_metrics(self.metrics_small_switches)

        for k, s in self.metrics_switches.items():
            s.connect("notify::active", on_metric_toggle, k)
        for k, s in self.metrics_small_switches.items():
            s.connect("notify::active", on_metric_small_toggle, k)
        enforce_minimum_metrics(self.metrics_switches)
        enforce_minimum_metrics(self.metrics_small_switches)

        # Disk directories
        disks_label = Label(label="Disk directories", h_align="start", v_align="center")
        vbox.add(disks_label)

        self.disk_entries = Box(orientation="v", spacing=8, h_align="start")

        def create_disk_edit(path):
            bar = Box(orientation="h", spacing=10, h_align="start")
            entry = Entry(text=path, h_expand=True)
            bar.add(entry)
            x = Button(label="X", on_clicked=lambda _: self.disk_entries.remove(bar))
            bar.add(x)
            self.disk_entries.add(bar)

        vbox.add(self.disk_entries)
        for path in bind_vars.get('bar_metrics_disks'):
            create_disk_edit(path)
        add_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        add_container.set_halign(Gtk.Align.START)
        add_container.set_valign(Gtk.Align.CENTER)
        add = Button(label="Add new disk", on_clicked=lambda _: create_disk_edit("/"))
        add_container.add(add)
        vbox.add(add_container)

        return scrolled_window

    def create_about_tab(self):
        """Create an About tab with project info, repo link, and Ko-Fi button."""
        vbox = Box(orientation="v", spacing=18, style="margin: 30px;")
        # Project title
        vbox.add(Label(markup=f"<b>{APP_NAME_CAP}</b>", h_align="start", style="font-size: 1.5em; margin-bottom: 8px;"))
        # Description
        vbox.add(Label(label="A hackable shell for Hyprland, powered by Fabric.", h_align="start", style="margin-bottom: 12px;"))
        # Repo link
        repo_box = Box(orientation="h", spacing=6, h_align="start")
        repo_label = Label(label="GitHub:", h_align="start")
        repo_link = Label()
        repo_link.set_markup(f'<a href="https://github.com/Axenide/Ax-Shell">https://github.com/Axenide/Ax-Shell</a>')
        repo_box.add(repo_label)
        repo_box.add(repo_link)
        vbox.add(repo_box)
        # Ko-Fi button
        def on_kofi_clicked(_):
            import webbrowser
            webbrowser.open("https://ko-fi.com/Axenide")
        kofi_btn = Button(label="Support on Ko-Fi ❤️", on_clicked=on_kofi_clicked, tooltip_text="Support Axenide on Ko-Fi")
        kofi_btn.set_style("margin-top: 18px; min-width: 160px;")
        vbox.add(kofi_btn)
        # Spacer
        vbox.add(Box(v_expand=True))
        return vbox

    def on_ws_num_changed(self, switch, gparam):
        """Callback when 'Show Workspace Numbers' switch changes."""
        is_active = switch.get_active()
        self.ws_chinese_switch.set_sensitive(is_active)
        if not is_active:
            self.ws_chinese_switch.set_active(False) # Turn off Chinese if numbers are off

    def on_vertical_changed(self, switch, gparam):
        """Callback for vertical switch."""
        is_active = switch.get_active()
        self.centered_switch.set_sensitive(is_active)
        if not is_active:
            self.centered_switch.set_active(False)

    def on_dock_enabled_changed(self, switch, gparam):
        """Callback for dock enabled switch."""
        is_active = switch.get_active()
        self.dock_hover_switch.set_sensitive(is_active)
        if not is_active:
            self.dock_hover_switch.set_active(False)

    def on_select_face_icon(self, widget):
        """
        Open a file chooser dialog for selecting a new face icon image.
        Uses Gtk.FileChooserDialog as Fabric doesn't provide one.
        """
        dialog = Gtk.FileChooserDialog(
            title="Select Face Icon",
            transient_for=self.get_toplevel(), # Get parent window
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
             Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )

        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image files")
        image_filter.add_mime_type("image/png")
        image_filter.add_mime_type("image/jpeg")
        image_filter.add_pattern("*.png")
        image_filter.add_pattern("*.jpg")
        image_filter.add_pattern("*.jpeg")
        dialog.add_filter(image_filter)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.selected_face_icon = dialog.get_filename()
            self.face_status_label.label = f"Selected: {os.path.basename(self.selected_face_icon)}"
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(self.selected_face_icon, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
            except Exception as e:
                 print(f"Error loading selected face icon preview: {e}")
                 self.face_image.set_from_icon_name("image-missing", 64)

        dialog.destroy()

    def on_accept(self, widget):
        """
        Gather settings and start a background thread to save, configure, and reload.
        """
        # --- Step 1: Gather all settings synchronously ---
        current_bind_vars = {} # Use a temporary dict to store gathered values
        for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
            current_bind_vars[prefix_key] = prefix_entry.get_text()
            current_bind_vars[suffix_key] = suffix_entry.get_text()

        current_bind_vars['wallpapers_dir'] = self.wall_dir_chooser.get_filename()
        current_bind_vars['vertical'] = self.vertical_switch.get_active()
        current_bind_vars['centered_bar'] = self.centered_switch.get_active()
        current_bind_vars['dock_enabled'] = self.dock_switch.get_active()
        current_bind_vars['dock_always_occluded'] = self.dock_hover_switch.get_active()
        current_bind_vars['dock_icon_size'] = int(self.dock_size_scale.value)
        current_bind_vars['terminal_command'] = self.terminal_entry.get_text()
        current_bind_vars['corners_visible'] = self.corners_switch.get_active()
        current_bind_vars['bar_workspace_show_number'] = self.ws_num_switch.get_active()
        current_bind_vars['bar_workspace_use_chinese_numerals'] = self.ws_chinese_switch.get_active()

        for component_name, switch in self.component_switches.items():
            config_key = f'bar_{component_name}_visible'
            current_bind_vars[config_key] = switch.get_active()

        current_bind_vars['metrics_visible'] = {k: s.get_active() for k, s in self.metrics_switches.items()}
        current_bind_vars['metrics_small_visible'] = {k: s.get_active() for k, s in self.metrics_small_switches.items()}

        current_bind_vars['bar_metrics_disks'] = [
            entry.children[0].get_text() for entry in self.disk_entries.children
        ]

        # Store state of lock/idle switches and selected icon path
        selected_icon_path = self.selected_face_icon # Copy path for the thread
        replace_lock = self.lock_switch and self.lock_switch.get_active()
        replace_idle = self.idle_switch and self.idle_switch.get_active()

        # Reset GUI state immediately (safe to do before starting thread)
        if self.selected_face_icon:
             self.selected_face_icon = None # Clear the selection state
             self.face_status_label.label = "" # Clear the status label

        # --- Step 2: Define the background task ---
        def _apply_and_reload_task_thread():
            start_time = time.time()
            print(f"{start_time:.4f}: Background task started.")
            global bind_vars
            # Update global bind_vars (used by generate_hyprconf in start_config)
            # This assumes bind_vars is primarily written here and read elsewhere.
            # If multiple threads modified bind_vars, locking would be needed.
            bind_vars = current_bind_vars

            # Save config.json
            config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
            os.makedirs(os.path.dirname(config_json), exist_ok=True)
            try:
                with open(config_json, 'w') as f:
                    json.dump(bind_vars, f, indent=4)
                print(f"{time.time():.4f}: Saved config.json.")
            except Exception as e:
                print(f"Error saving config.json: {e}")

            # Process face icon if selected
            if selected_icon_path:
                print(f"{time.time():.4f}: Processing face icon...")
                try:
                    img = Image.open(selected_icon_path)
                    side = min(img.size)
                    left = (img.width - side) // 2
                    top = (img.height - side) // 2
                    right = left + side
                    bottom = top + side
                    cropped_img = img.crop((left, top, right, bottom))
                    face_icon_dest = os.path.expanduser("~/.face.icon")
                    cropped_img.save(face_icon_dest, format='PNG')
                    print(f"{time.time():.4f}: Face icon saved to {face_icon_dest}")
                    # Schedule GUI update for the image widget back on the main thread
                    GLib.idle_add(self._update_face_image_widget, face_icon_dest)
                except Exception as e:
                    print(f"Error processing face icon: {e}")
                print(f"{time.time():.4f}: Finished processing face icon.")

            # Replace hyprlock/hypridle configs if requested (sync file I/O)
            if replace_lock:
                print(f"{time.time():.4f}: Replacing hyprlock config...")
                src_lock = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
                dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
                if os.path.exists(src_lock):
                    backup_and_replace(src_lock, dest_lock, "Hyprlock")
                else:
                    print(f"Warning: Source hyprlock config not found at {src_lock}")
                print(f"{time.time():.4f}: Finished replacing hyprlock config.")

            if replace_idle:
                print(f"{time.time():.4f}: Replacing hypridle config...")
                src_idle = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
                dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
                if os.path.exists(src_idle):
                     backup_and_replace(src_idle, dest_idle, "Hypridle")
                else:
                    print(f"Warning: Source hypridle config not found at {src_idle}")
                print(f"{time.time():.4f}: Finished replacing hypridle config.")

            # Append source string to hyprland.conf if needed (sync file I/O)
            print(f"{time.time():.4f}: Checking/Appending hyprland.conf source string...")
            hyprland_config_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
            try:
                needs_append = True
                if os.path.exists(hyprland_config_path):
                    with open(hyprland_config_path, "r") as f:
                        content = f.read()
                        if SOURCE_STRING.strip() in content:
                            needs_append = False
                else:
                     os.makedirs(os.path.dirname(hyprland_config_path), exist_ok=True)

                if needs_append:
                    with open(hyprland_config_path, "a") as f:
                        f.write("\n" + SOURCE_STRING)
                    print(f"Appended source string to {hyprland_config_path}")
            except Exception as e:
                 print(f"Error updating {hyprland_config_path}: {e}")
            print(f"{time.time():.4f}: Finished checking/appending hyprland.conf source string.")

            # Run final config steps (includes async matugen/hyprctl reload)
            print(f"{time.time():.4f}: Running start_config()...")
            start_config()
            print(f"{time.time():.4f}: Finished start_config().")

            # Restart Ax-Shell using subprocess.Popen for better detachment
            print(f"{time.time():.4f}: Initiating Ax-Shell restart using Popen...")
            main_script_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/main.py")
            kill_cmd = f"killall {APP_NAME}"
            # Use shell=True carefully, but it's often needed for commands like killall
            # Redirect output to prevent blocking
            start_cmd_list = ["uwsm", "app", "--", "/home/mathias/.config/Ax-Shell/.venv/bin/python", main_script_path] # Use list form for Popen

            try:
                # Kill existing process (wait briefly for it to finish)
                print(f"{time.time():.4f}: Executing kill: {kill_cmd}")
                kill_proc = subprocess.Popen(kill_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                kill_proc.wait(timeout=2) # Wait max 2 seconds for killall
                print(f"{time.time():.4f}: killall process finished (or timed out).")

                # Start the new process, detached
                print(f"{time.time():.4f}: Executing start: {' '.join(start_cmd_list)}")
                subprocess.Popen(
                    start_cmd_list,
                    stdout=subprocess.DEVNULL, # Redirect stdout
                    stderr=subprocess.DEVNULL, # Redirect stderr
                    start_new_session=True    # Crucial for detaching
                )
                print(f"{APP_NAME_CAP} restart initiated via Popen.")
            except subprocess.TimeoutExpired:
                print(f"Warning: killall command timed out.")
            except FileNotFoundError as e:
                 print(f"Error restarting {APP_NAME_CAP}: Command not found ({e})")
            except Exception as e:
                print(f"Error restarting {APP_NAME_CAP} via Popen: {e}")
            print(f"{time.time():.4f}: Ax-Shell restart commands issued via Popen.")

            end_time = time.time()
            print(f"{end_time:.4f}: Background configuration and reload task finished (Total time: {end_time - start_time:.4f}s).")

        # --- Step 3: Start the thread ---
        thread = threading.Thread(target=_apply_and_reload_task_thread)
        thread.daemon = True # Allow application to exit even if thread is running
        thread.start()

        print("Configuration apply/reload task started in background.")

    # Add helper method to update face image widget from the background thread
    def _update_face_image_widget(self, icon_path):
        """Safely update the face image widget from the main GTK thread."""
        try:
            # Check if the widget still exists before updating
            if self.face_image and self.face_image.get_window():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_path, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)
        except Exception as e:
            print(f"Error reloading face icon preview: {e}")
            if self.face_image and self.face_image.get_window():
                self.face_image.set_from_icon_name("image-missing", 64)
        return False # Return False to ensure GLib.idle_add runs the callback only once

    def on_reset(self, widget):
        """
        Reset all settings to default values. Uses Gtk.MessageDialog.
        """
        dialog = Gtk.MessageDialog(
            transient_for=self.get_toplevel(),
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset all settings to defaults?"
        )
        dialog.format_secondary_text("This will reset all keybindings and appearance settings to their default values.")
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            global bind_vars
            bind_vars = DEFAULTS.copy()

            for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
                prefix_entry.set_text(bind_vars[prefix_key])
                suffix_entry.set_text(bind_vars[suffix_key])

            self.wall_dir_chooser.set_filename(bind_vars['wallpapers_dir'])
            self.vertical_switch.set_active(bind_vars.get('vertical', False))
            self.centered_switch.set_active(bind_vars.get('centered_bar', False))
            self.centered_switch.set_sensitive(self.vertical_switch.get_active())
            self.dock_switch.set_active(bind_vars.get('dock_enabled', True))
            self.dock_hover_switch.set_active(bind_vars.get('dock_always_occluded', False))
            self.dock_hover_switch.set_sensitive(self.dock_switch.get_active())
            self.dock_size_scale.value = bind_vars.get('dock_icon_size', 28)
            self.terminal_entry.set_text(bind_vars['terminal_command'])
            self.ws_num_switch.set_active(bind_vars.get('bar_workspace_show_number', False))
            self.ws_chinese_switch.set_active(bind_vars.get('bar_workspace_use_chinese_numerals', False)) # Reset Chinese switch
            self.ws_chinese_switch.set_sensitive(self.ws_num_switch.get_active()) # Reset sensitivity

            for component_name, switch in self.component_switches.items():
                 config_key = f'bar_{component_name}_visible'
                 switch.set_active(bind_vars.get(config_key, True))

            self.corners_switch.set_active(bind_vars.get('corners_visible', True))

            # Reset metrics visibility
            for k, s in self.metrics_switches.items():
                s.set_active(DEFAULTS['metrics_visible'][k])
            for k, s in self.metrics_small_switches.items():
                s.set_active(DEFAULTS['metrics_small_visible'][k])

            # Reset disk entries
            if True:
                for i in self.disk_entries.children:
                    self.disk_entries.remove(i)
                bar = Box(orientation="h", spacing=10, h_align="start")
                entry = Entry(text="/", h_expand=True)
                bar.add(entry)
                x = Button(label="X", on_clicked=lambda _: self.disk_entries.remove(bar))
                bar.add(x)
                self.disk_entries.add(bar)

            self.selected_face_icon = None
            self.face_status_label.label = ""
            current_face = os.path.expanduser("~/.face.icon")
            try:
                 if os.path.exists(current_face):
                      pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(current_face, 64, 64)
                      self.face_image.set_from_pixbuf(pixbuf)
                 else:
                      self.face_image.set_from_icon_name("user-info", 64)
            except Exception:
                 self.face_image.set_from_icon_name("image-missing", 64)

            if self.lock_switch: self.lock_switch.set_active(False)
            if self.idle_switch: self.idle_switch.set_active(False)

            print("Settings reset to defaults.")

    def on_close(self, widget):
        """Close the settings window."""
        if self.application:
             self.application.quit()
        else:
            self.destroy()

def start_config():
    """
    Run final configuration steps: ensure necessary configs, write the hyprconf, and reload.
    """
    print(f"{time.time():.4f}: start_config: Ensuring matugen config...")
    ensure_matugen_config()
    print(f"{time.time():.4f}: start_config: Ensuring face icon...")
    ensure_face_icon()
    print(f"{time.time():.4f}: start_config: Generating hypr conf...")

    hypr_config_dir = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/")
    os.makedirs(hypr_config_dir, exist_ok=True)
    hypr_conf_path = os.path.join(hypr_config_dir, f"{APP_NAME}.conf")
    try:
        with open(hypr_conf_path, "w") as f:
            f.write(generate_hyprconf())
        print(f"Generated Hyprland config at {hypr_conf_path}")
    except Exception as e:
        print(f"Error writing Hyprland config: {e}")
    print(f"{time.time():.4f}: start_config: Finished generating hypr conf.")

    # Use async reload
    print(f"{time.time():.4f}: start_config: Initiating hyprctl reload...")
    try:
        exec_shell_command_async("hyprctl reload")
        print(f"{time.time():.4f}: start_config: Hyprland configuration reload initiated.")
    except FileNotFoundError:
         print("Error: hyprctl command not found. Cannot reload Hyprland.")
    except Exception as e:
         # Catch potential errors during command initiation
         print(f"An error occurred initiating hyprctl reload: {e}")
    print(f"{time.time():.4f}: start_config: Finished initiating hyprctl reload.")


def open_config():
    """
    Entry point for opening the configuration GUI using Fabric Application.
    """
    load_bind_vars()

    dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
    src_lock = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
    show_lock_checkbox = True
    if not os.path.exists(dest_lock) and os.path.exists(src_lock):
        try:
             os.makedirs(os.path.dirname(dest_lock), exist_ok=True)
             shutil.copy(src_lock, dest_lock)
             show_lock_checkbox = False
             print(f"Copied default hyprlock config to {dest_lock}")
        except Exception as e:
             print(f"Error copying default hyprlock config: {e}")
             show_lock_checkbox = os.path.exists(src_lock)

    dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
    src_idle = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
    show_idle_checkbox = True
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
