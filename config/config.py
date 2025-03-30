import os
import shutil
import json
import sys
from pathlib import Path
import subprocess

import toml
from PIL import Image
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf # Keep Gtk for Switch, FileChooserButton, Expander, Grid

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
from fabric.utils.helpers import get_relative_path # If needed for assets

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
        print(f"Generating color theme from wallpaper: {image_path}")
        try:
            subprocess.run(["matugen", "image", image_path], check=True)
            print("Color theme generated successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error generating color theme: {e}")
        except FileNotFoundError:
            print("Error: matugen command not found. Please install matugen.")


def load_bind_vars():
    """
    Load saved key binding variables from JSON, if available.
    """
    config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
    try:
        with open(config_json, 'r') as f:
            saved_vars = json.load(f)
            bind_vars.update(saved_vars)
    except FileNotFoundError:
        # Use default values if no saved config exists
        pass


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
                        bind_vars[key] = DEFAULTS[key] # Use default if missing in saved
                # Add any new keys from DEFAULTS not present in saved_vars
                for key in saved_vars:
                    if key not in bind_vars:
                         bind_vars[key] = saved_vars[key] # Keep saved if it's not in new defaults (less likely)
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
    return f"""exec-once = uwsm-app $(python {home}/.config/{APP_NAME_CAP}/main.py)
exec = pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle
exec = uwsm app -- swww-daemon

$fabricSend = fabric-cli exec {APP_NAME}
$axMessage = notify-send "Axenide" "What are you doing?" -i "{home}/.config/{APP_NAME_CAP}/assets/ax.png" -a "Source Code" -A "Be patient. 🍙"

bind = {bind_vars['prefix_restart']}, {bind_vars['suffix_restart']}, exec, killall {APP_NAME}; uwsm-app $(python {home}/.config/{APP_NAME_CAP}/main.py) # Reload {APP_NAME_CAP} | Default: SUPER ALT + B
bind = {bind_vars['prefix_axmsg']}, {bind_vars['suffix_axmsg']}, exec, $axMessage # Message | Default: SUPER + A
bind = {bind_vars['prefix_dash']}, {bind_vars['suffix_dash']}, exec, $fabricSend 'notch.open_notch("dashboard")' # Dashboard | Default: SUPER + D
bind = {bind_vars['prefix_bluetooth']}, {bind_vars['suffix_bluetooth']}, exec, $fabricSend 'notch.open_notch("bluetooth")' # Bluetooth | Default: SUPER + B
bind = {bind_vars['prefix_pins']}, {bind_vars['suffix_pins']}, exec, $fabricSend 'notch.open_notch("pins")' # Pins | Default: SUPER + Q
bind = {bind_vars['prefix_kanban']}, {bind_vars['suffix_kanban']}, exec, $fabricSend 'notch.open_notch("kanban")' # Kanban | Default: SUPER + N
bind = {bind_vars['prefix_launcher']}, {bind_vars['suffix_launcher']}, exec, $fabricSend 'notch.open_notch("launcher")' # App Launcher | Default: SUPER + R
bind = {bind_vars['prefix_tmux']}, {bind_vars['suffix_tmux']}, exec, $fabricSend 'notch.open_notch("tmux")' # App Launcher | Default: SUPER + T
bind = {bind_vars['prefix_toolbox']}, {bind_vars['suffix_toolbox']}, exec, $fabricSend 'notch.open_notch("tools")' # Toolbox | Default: SUPER + S
bind = {bind_vars['prefix_overview']}, {bind_vars['suffix_overview']}, exec, $fabricSend 'notch.open_notch("overview")' # Overview | Default: SUPER + TAB
bind = {bind_vars['prefix_wallpapers']}, {bind_vars['suffix_wallpapers']}, exec, $fabricSend 'notch.open_notch("wallpapers")' # Wallpapers | Default: SUPER + COMMA
bind = {bind_vars['prefix_emoji']}, {bind_vars['suffix_emoji']}, exec, $fabricSend 'notch.open_notch("emoji")' # Emoji | Default: SUPER + PERIOD
bind = {bind_vars['prefix_power']}, {bind_vars['suffix_power']}, exec, $fabricSend 'notch.open_notch("power")' # Power Menu | Default: SUPER + ESCAPE
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'bar.toggle_hidden()' # Toggle Bar | Default: SUPER CTRL + B
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'notch.toggle_hidden()' # Toggle Notch | Default: SUPER CTRL + B
bind = {bind_vars['prefix_css']}, {bind_vars['suffix_css']}, exec, $fabricSend 'app.set_css()' # Reload CSS | Default: SUPER SHIFT + B
bind = {bind_vars['prefix_restart_inspector']}, {bind_vars['suffix_restart_inspector']}, exec, killall {APP_NAME}; uwsm-app $(GTK_DEBUG=interactive python {home}/.config/{APP_NAME_CAP}/main.py) # Restart with inspector | Default: SUPER CTRL ALT + B

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

        self.tab_stack.add_titled(self.key_bindings_tab_content, "key_bindings", "Key Bindings")
        self.tab_stack.add_titled(self.appearance_tab_content, "appearance", "Appearance")
        self.tab_stack.add_titled(self.system_tab_content, "system", "System")

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

        # --- Separator ---
        separator2 = Box(style="min-height: 1px; background-color: alpha(@fg_color, 0.2); margin: 5px 0px;",
                         h_expand=True)
        vbox.add(separator2)

        # --- Bar Components ---
        components_header = Label(markup="<b>Bar Components</b>", h_align="start")
        vbox.add(components_header)

        # Create a grid for bar components
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

        # Calculate number of rows needed (we'll use 2 columns)
        num_components = len(component_display_names)
        rows_per_column = (num_components + 1) // 2  # Ceiling division
        
        # Add components to grid in two columns
        for i, (component_name, display_name) in enumerate(component_display_names.items()):
            # Determine position: first half in column 0, second half in column 2
            col = 0 if i < rows_per_column else 2
            row = i % rows_per_column
            
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

        # === SUPPORT INFO ===
        support_box = Box(orientation="h", spacing=10, style="margin-top: 15px;", h_align="start")
        support_icon = FabricImage(icon_name="help-about-symbolic", icon_size=Gtk.IconSize.MENU)
        support_label = Label(markup="<small>For help or to report issues, visit the <a href='https://github.com/Axenide/Ax-Shell'>GitHub repository</a></small>")
        support_box.add(support_icon)
        support_box.add(support_label)
        vbox.add(support_box)

        return scrolled_window

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
        Save the configuration and update the necessary files without closing the window.
        """
        for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
            bind_vars[prefix_key] = prefix_entry.get_text()
            bind_vars[suffix_key] = suffix_entry.get_text()

        bind_vars['wallpapers_dir'] = self.wall_dir_chooser.get_filename()
        bind_vars['vertical'] = self.vertical_switch.get_active()
        bind_vars['centered_bar'] = self.centered_switch.get_active()
        bind_vars['dock_enabled'] = self.dock_switch.get_active()
        bind_vars['dock_always_occluded'] = self.dock_hover_switch.get_active()
        bind_vars['dock_icon_size'] = int(self.dock_size_scale.value)
        bind_vars['terminal_command'] = self.terminal_entry.get_text()

        for component_name, switch in self.component_switches.items():
            config_key = f'bar_{component_name}_visible'
            bind_vars[config_key] = switch.get_active()

        config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
        os.makedirs(os.path.dirname(config_json), exist_ok=True)
        try:
            with open(config_json, 'w') as f:
                json.dump(bind_vars, f, indent=4)
        except Exception as e:
            print(f"Error saving config.json: {e}")

        if self.selected_face_icon:
            try:
                img = Image.open(self.selected_face_icon)
                side = min(img.size)
                left = (img.width - side) // 2
                top = (img.height - side) // 2
                right = left + side
                bottom = top + side
                cropped_img = img.crop((left, top, right, bottom))
                face_icon_dest = os.path.expanduser("~/.face.icon")
                cropped_img.save(face_icon_dest, format='PNG')
                print(f"Face icon saved to {face_icon_dest}")
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(face_icon_dest, 64, 64)
                self.face_image.set_from_pixbuf(pixbuf)

            except Exception as e:
                print(f"Error processing face icon: {e}")
            finally:
                self.selected_face_icon = None
                self.face_status_label.label = ""

        if self.lock_switch and self.lock_switch.get_active():
            src_lock = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
            dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
            if os.path.exists(src_lock):
                backup_and_replace(src_lock, dest_lock, "Hyprlock")
            else:
                print(f"Warning: Source hyprlock config not found at {src_lock}")

        if self.idle_switch and self.idle_switch.get_active():
            src_idle = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
            dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
            if os.path.exists(src_idle):
                 backup_and_replace(src_idle, dest_idle, "Hypridle")
            else:
                print(f"Warning: Source hypridle config not found at {src_idle}")

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

        start_config()

        main_script_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/main.py")
        restart_script_content = f"""#!/bin/bash
echo "Attempting to restart {APP_NAME}..." > /tmp/ax_shell_restart.log
killall {APP_NAME} &>> /tmp/ax_shell_restart.log
sleep 0.5
echo "Running main script: python {main_script_path}" >> /tmp/ax_shell_restart.log
python_output=$(python {main_script_path} 2>&1)
echo "Python script output:" >> /tmp/ax_shell_restart.log
echo "$python_output" >> /tmp/ax_shell_restart.log
if command -v uwsm-app &> /dev/null; then
    echo "Running uwsm-app..." >> /tmp/ax_shell_restart.log
    uwsm-app "$python_output" &>> /tmp/ax_shell_restart.log &
else
    echo "uwsm-app command not found. Cannot start application with uwsm." >> /tmp/ax_shell_restart.log
fi
echo "Restart script finished." >> /tmp/ax_shell_restart.log
"""
        restart_script_path = "/tmp/ax_shell_restart.sh"
        try:
            with open(restart_script_path, "w") as f:
                f.write(restart_script_content)
            os.chmod(restart_script_path, 0o755)

            subprocess.Popen(["/bin/bash", restart_script_path],
                             start_new_session=True,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            print(f"{APP_NAME_CAP} restart initiated in background. Check /tmp/ax_shell_restart.log for details.")
        except Exception as e:
            print(f"Error creating or running restart script: {e}")

        print("Configuration applied and reload initiated.")

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

            for component_name, switch in self.component_switches.items():
                 config_key = f'bar_{component_name}_visible'
                 switch.set_active(bind_vars.get(config_key, True))

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
    ensure_matugen_config()
    ensure_face_icon()

    hypr_config_dir = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/")
    os.makedirs(hypr_config_dir, exist_ok=True)
    hypr_conf_path = os.path.join(hypr_config_dir, f"{APP_NAME}.conf")
    try:
        with open(hypr_conf_path, "w") as f:
            f.write(generate_hyprconf())
        print(f"Generated Hyprland config at {hypr_conf_path}")
    except Exception as e:
        print(f"Error writing Hyprland config: {e}")

    try:
        subprocess.run(["hyprctl", "reload"], check=True, capture_output=True)
        print("Hyprland configuration reloaded.")
    except subprocess.CalledProcessError as e:
         print(f"Error reloading Hyprland: {e}\nstderr: {e.stderr.decode()}")
    except FileNotFoundError:
         print("Error: hyprctl command not found. Cannot reload Hyprland.")
    except Exception as e:
         print(f"An unexpected error occurred during hyprctl reload: {e}")


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
