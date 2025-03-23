import os
import shutil
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import toml
from PIL import Image
import subprocess
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from config.data import (
    APP_NAME, APP_NAME_CAP, CONFIG_DIR, HOME_DIR, WALLPAPERS_DIR_DEFAULT
)
from fabric.utils.helpers import get_relative_path
from gi.repository import GdkPixbuf

SOURCE_STRING = f"""
# {APP_NAME_CAP}
source = ~/.config/{APP_NAME_CAP}/config/hypr/{APP_NAME}.conf
"""

# Initialize bind_vars with default values
DEFAULT_KEYBINDINGS = {
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
    'vertical': False,  # New default for vertical layout
    'terminal_command': "kitty -e",  # Default terminal command for tmux
}

bind_vars = DEFAULT_KEYBINDINGS.copy()


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

    # Trigger image generation if "~/.current.wall" does not exist
    current_wall = os.path.expanduser("~/.current.wall")
    if not os.path.exists(current_wall):
        image_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/assets/wallpapers_example/example-1.jpg")
        # Replace os.system with subprocess.run
        subprocess.run(["matugen", "image", image_path])
        os.symlink(image_path, os.path.expanduser(f"~/.current.wall"))

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


def generate_hyprconf() -> str:
    """
    Generate the Hypr configuration string using the current bind_vars.
    """
    home = os.path.expanduser('~')
    return f"""exec-once = uwsm app -- python {home}/.config/{APP_NAME_CAP}/main.py
exec = pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle
exec = uwsm app -- swww-daemon

$fabricSend = fabric-cli exec {APP_NAME}
$axMessage = notify-send "Axenide" "What are you doing?" -i "{home}/.config/{APP_NAME_CAP}/assets/ax.png" -a "Source Code" -A "Be patient. 🍙"

bind = {bind_vars['prefix_restart']}, {bind_vars['suffix_restart']}, exec, killall {APP_NAME}; uwsm app -- python {home}/.config/{APP_NAME_CAP}/main.py # Reload {APP_NAME_CAP} | Default: SUPER ALT + B
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
bind = {bind_vars['prefix_restart_inspector']}, {bind_vars['suffix_restart_inspector']}, exec, killall {APP_NAME}; GTK_DEBUG=interactive uwsm app -- python {home}/.config/{APP_NAME_CAP}/main.py # Restart with inspector | Default: SUPER CTRL ALT + B

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
        shutil.copy(default_icon_path, face_icon_path)


def backup_and_replace(src: str, dest: str, config_name: str):
    """
    Backup the existing configuration file and replace it with a new one.
    """
    if os.path.exists(dest):
        backup_path = dest + ".bak"
        shutil.copy(dest, backup_path)
        print(f"{config_name} config backed up to {backup_path}")
    shutil.copy(src, dest)
    print(f"{config_name} config replaced from {src}")


class HyprConfGUI(Gtk.Window):
    def __init__(self, show_lock_checkbox: bool, show_idle_checkbox: bool):
        super().__init__(title="Ax-Shell Settings")
        self.set_border_width(10)
        self.set_default_size(500, 550)
        self.set_resizable(False)

        self.selected_face_icon = None
        self.show_lock_checkbox = show_lock_checkbox
        self.show_idle_checkbox = show_idle_checkbox

        # Main vertical box to contain the notebook and buttons
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(main_box)

        # Create notebook for tabs
        notebook = Gtk.Notebook()
        notebook.set_margin_top(5)
        notebook.set_margin_bottom(10)
        main_box.pack_start(notebook, True, True, 0)

        # Create tabs
        key_bindings_tab = self.create_key_bindings_tab()
        notebook.append_page(key_bindings_tab, Gtk.Label(label="Key Bindings"))

        appearance_tab = self.create_appearance_tab()
        notebook.append_page(appearance_tab, Gtk.Label(label="Appearance"))

        system_tab = self.create_system_tab()
        notebook.append_page(system_tab, Gtk.Label(label="System"))

        # Button box for Close and Accept buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)

        reset_btn = Gtk.Button(label="Reset to Defaults")
        reset_btn.connect("clicked", self.on_reset)
        button_box.pack_start(reset_btn, False, False, 0)

        cancel_btn = Gtk.Button(label="Close")
        cancel_btn.connect("clicked", self.on_cancel)
        button_box.pack_start(cancel_btn, False, False, 0)

        accept_btn = Gtk.Button(label="Accept")
        accept_btn.connect("clicked", self.on_accept)
        button_box.pack_start(accept_btn, False, False, 0)

        main_box.pack_start(button_box, False, False, 0)

    def create_key_bindings_tab(self):
        """Create tab for key bindings configuration."""
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_margin_top(15)
        grid.set_margin_bottom(15)
        grid.set_margin_start(15)
        grid.set_margin_end(15)
        scrolled_window.add(grid)

        # Create labels for columns
        action_label = Gtk.Label()
        action_label.set_markup("<b>Action</b>")
        action_label.set_halign(Gtk.Align.START)
        action_label.set_margin_bottom(5)
        action_label.get_style_context().add_class("heading")

        modifier_label = Gtk.Label()
        modifier_label.set_markup("<b>Modifier</b>")
        modifier_label.set_halign(Gtk.Align.START)
        modifier_label.set_margin_bottom(5)
        modifier_label.get_style_context().add_class("heading")

        key_label = Gtk.Label()
        key_label.set_markup("<b>Key</b>")
        key_label.set_halign(Gtk.Align.START)
        key_label.set_margin_bottom(5)
        key_label.get_style_context().add_class("heading")

        grid.attach(action_label, 0, 1, 1, 1)
        grid.attach(modifier_label, 1, 1, 1, 1)
        grid.attach(key_label, 3, 1, 1, 1)

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

        # Populate grid with key binding rows, starting at row 2
        row = 2
        for label_text, prefix_key, suffix_key in bindings:
            # Binding description
            binding_label = Gtk.Label(label=label_text)
            binding_label.set_halign(Gtk.Align.START)
            grid.attach(binding_label, 0, row, 1, 1)

            # Prefix entry
            prefix_entry = Gtk.Entry()
            prefix_entry.set_text(bind_vars[prefix_key])
            grid.attach(prefix_entry, 1, row, 1, 1)

            # Plus label between entries
            plus_label = Gtk.Label(label=" + ")
            grid.attach(plus_label, 2, row, 1, 1)

            # Suffix entry
            suffix_entry = Gtk.Entry()
            suffix_entry.set_text(bind_vars[suffix_key])
            grid.attach(suffix_entry, 3, row, 1, 1)

            self.entries.append((prefix_key, suffix_key, prefix_entry, suffix_entry))
            row += 1

        return scrolled_window

    def create_appearance_tab(self):
        """Create tab for appearance settings."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)

        # Wallpapers section with header
        wall_header = Gtk.Label()
        wall_header.set_markup("<b>Wallpapers</b>")
        wall_header.set_halign(Gtk.Align.START)
        box.pack_start(wall_header, False, False, 0)
        
        wall_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        wall_section.set_margin_start(10)
        wall_section.set_margin_top(5)
        wall_section.set_margin_bottom(15)

        wall_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        wall_label = Gtk.Label(label="Directory:")
        wall_label.set_halign(Gtk.Align.START)
        self.wall_dir_chooser = Gtk.FileChooserButton(
            title="Select a folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.wall_dir_chooser.set_tooltip_text("Select the directory containing your wallpaper images")
        self.wall_dir_chooser.set_filename(bind_vars['wallpapers_dir'])
        wall_hbox.pack_start(wall_label, False, False, 0)
        wall_hbox.pack_start(self.wall_dir_chooser, True, True, 0)
        wall_section.pack_start(wall_hbox, False, False, 0)

        box.pack_start(wall_section, False, False, 0)

        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(separator, False, False, 5)

        # Profile Icon section with header
        face_header = Gtk.Label()
        face_header.set_markup("<b>Profile Icon</b>")
        face_header.set_halign(Gtk.Align.START)
        box.pack_start(face_header, False, False, 10)
        
        face_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        face_section.set_margin_start(10)
        
        # Current icon display
        current_face = os.path.expanduser("~/.face.icon")
        current_icon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        face_image_frame = Gtk.Frame()
        face_image_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        face_image = Gtk.Image()
        try:
            if os.path.exists(current_face):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(current_face)
                pixbuf = pixbuf.scale_simple(96, 96, GdkPixbuf.InterpType.BILINEAR)
            else:
                pixbuf = Gtk.IconTheme.get_default().load_icon("user-info", 96, 0)
            face_image.set_from_pixbuf(pixbuf)
        except Exception:
            face_image.set_from_icon_name("user-info", Gtk.IconSize.DIALOG)
        
        face_image_frame.add(face_image)
        current_icon_box.pack_start(face_image_frame, False, False, 0)
        face_section.pack_start(current_icon_box, False, False, 0)
        
        # Select new icon
        face_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        face_label = Gtk.Label(label="Select New Icon:")
        face_label.set_halign(Gtk.Align.START)
        face_btn = Gtk.Button(label="Browse...")
        face_btn.set_tooltip_text("Select a square image for your profile icon")
        face_btn.connect("clicked", self.on_select_face_icon)
        face_hbox.pack_start(face_label, False, False, 0)
        face_hbox.pack_start(face_btn, False, False, 0)
        face_section.pack_start(face_hbox, False, False, 0)

        self.face_status_label = Gtk.Label(label="")
        self.face_status_label.set_halign(Gtk.Align.START)
        face_section.pack_start(self.face_status_label, False, False, 0)

        box.pack_start(face_section, False, False, 0)

        # New vertical layout switch added to Appearance tab
        vertical_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vertical_label = Gtk.Label(label="Vertical Layout")
        vertical_label.set_halign(Gtk.Align.START)
        self.vertical_switch = Gtk.Switch()
        self.vertical_switch.set_active(bind_vars.get('vertical', False))
        vertical_box.pack_start(vertical_label, True, True, 0)
        vertical_box.pack_end(self.vertical_switch, False, False, 0)
        box.pack_start(vertical_box, False, False, 10)

        return box

    def create_system_tab(self):
        """Create tab for system configurations."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)

        # Terminal Command section
        terminal_header = Gtk.Label()
        terminal_header.set_markup("<b>Terminal Settings</b>")
        terminal_header.set_halign(Gtk.Align.START)
        box.pack_start(terminal_header, False, False, 0)
        
        terminal_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        terminal_section.set_margin_start(10)
        terminal_section.set_margin_top(5)
        terminal_section.set_margin_bottom(15)
        
        terminal_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        terminal_label = Gtk.Label(label="Terminal Command:")
        terminal_label.set_halign(Gtk.Align.START)
        self.terminal_entry = Gtk.Entry()
        self.terminal_entry.set_text(bind_vars['terminal_command'])
        self.terminal_entry.set_tooltip_text("Command used to launch terminal apps (e.g., 'kitty -e', 'alacritty -e')")
        terminal_hbox.pack_start(terminal_label, False, False, 0)
        terminal_hbox.pack_start(self.terminal_entry, True, True, 0)
        terminal_section.pack_start(terminal_hbox, False, False, 0)
        
        # Example hint
        hint_label = Gtk.Label()
        hint_label.set_markup("<small>Examples: 'kitty -e', 'alacritty -e', 'foot -e'</small>")
        hint_label.set_halign(Gtk.Align.START)
        terminal_section.pack_start(hint_label, False, False, 5)
        
        box.pack_start(terminal_section, False, False, 0)

        # Hypr Configuration section
        hypr_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

        # Replacing checkboxes with switches for Hyprlock config
        if self.show_lock_checkbox:
            lock_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            lock_label = Gtk.Label(label="Replace Hyprlock config")
            lock_label.set_halign(Gtk.Align.START)
            self.lock_switch = Gtk.Switch()
            lock_box.pack_start(lock_label, True, True, 0)
            lock_box.pack_end(self.lock_switch, False, False, 0)
            hypr_section.pack_start(lock_box, False, False, 10)
        else:
            self.lock_switch = None

        # Replacing checkboxes with switches for Hypridle config
        if self.show_idle_checkbox:
            idle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            idle_label = Gtk.Label(label="Replace Hypridle config")
            idle_label.set_halign(Gtk.Align.START)
            self.idle_switch = Gtk.Switch()
            idle_box.pack_start(idle_label, True, True, 0)
            idle_box.pack_end(self.idle_switch, False, False, 0)
            hypr_section.pack_start(idle_box, False, False, 10)
        else:
            self.idle_switch = None

        box.pack_start(hypr_section, False, False, 0)

        # Spacer to push everything to the top
        spacer = Gtk.Box()
        box.pack_start(spacer, True, True, 0)

        return box

    def create_display_tab(self):
        """Create tab for display configurations."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(15)
        box.set_margin_end(15)

        return box

    def on_select_face_icon(self, widget):
        """
        Open a file chooser dialog for selecting a new face icon image.
        """
        dialog = Gtk.FileChooserDialog(
            title="Select Face Icon",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )

        # Filter to allow image files only
        image_filter = Gtk.FileFilter()
        image_filter.set_name("Image files")
        image_filter.add_mime_type("image/png")
        image_filter.add_mime_type("image/jpeg")
        image_filter.add_pattern("*.png")
        image_filter.add_pattern("*.jpg")
        image_filter.add_pattern("*.jpeg")
        dialog.add_filter(image_filter)

        if dialog.run() == Gtk.ResponseType.OK:
            self.selected_face_icon = dialog.get_filename()
            self.face_status_label.set_text(f"Selected: {os.path.basename(self.selected_face_icon)}")
        dialog.destroy()

    def on_accept(self, widget):
        """
        Save the configuration and update the necessary files.
        """
        # Update bind_vars from user inputs
        for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
            bind_vars[prefix_key] = prefix_entry.get_text()
            bind_vars[suffix_key] = suffix_entry.get_text()

        # Update wallpaper directory
        bind_vars['wallpapers_dir'] = self.wall_dir_chooser.get_filename()

        # Update vertical setting from the new switch
        bind_vars['vertical'] = self.vertical_switch.get_active()
        
        # Update terminal command
        bind_vars['terminal_command'] = self.terminal_entry.get_text()

        # Save the updated bind_vars to a JSON file
        config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
        os.makedirs(os.path.dirname(config_json), exist_ok=True)
        with open(config_json, 'w') as f:
            json.dump(bind_vars, f)

        # Process face icon if one was selected
        if self.selected_face_icon:
            try:
                img = Image.open(self.selected_face_icon)
                side = min(img.size)
                left = (img.width - side) / 2
                top = (img.height - side) / 2
                cropped_img = img.crop((left, top, left + side, top + side))
                cropped_img.save(os.path.expanduser("~/.face.icon"), format='PNG')
                print("Face icon saved.")
            except Exception as e:
                print("Error processing face icon:", e)

        # Replace hyprlock config if requested using the new switch
        if self.lock_switch and self.lock_switch.get_active():
            src_lock = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
            dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
            backup_and_replace(src_lock, dest_lock, "Hyprlock")

        # Replace hypridle config if requested using the new switch
        if self.idle_switch and self.idle_switch.get_active():
            src_idle = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
            dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
            backup_and_replace(src_idle, dest_idle, "Hypridle")

        # Append the source string to the Hyprland config if not present
        hyprland_config_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
        with open(hyprland_config_path, "r") as f:
            content = f.read()
        if (SOURCE_STRING not in content):
            with open(hyprland_config_path, "a") as f:
                f.write(SOURCE_STRING)

        start_config()
        subprocess.run(["killall", APP_NAME])
        subprocess.Popen(
            ["uwsm", "app", "--", "python", os.path.expanduser(f"~/.config/{APP_NAME_CAP}/main.py")],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # self.destroy()

    def on_reset(self, widget):
        """
        Reset all settings to default values.
        """
        # Ask for confirmation
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset all settings to defaults?"
        )
        dialog.format_secondary_text("This will reset all keybindings and other settings to their default values.")
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Reset bind_vars to default values
            global bind_vars
            bind_vars = DEFAULT_KEYBINDINGS.copy()
            
            # Update UI elements
            # Update key binding entries
            for prefix_key, suffix_key, prefix_entry, suffix_entry in self.entries:
                prefix_entry.set_text(bind_vars[prefix_key])
                suffix_entry.set_text(bind_vars[suffix_key])
            
            # Update wallpaper directory chooser
            self.wall_dir_chooser.set_filename(bind_vars['wallpapers_dir'])
            
            # Update vertical switch
            self.vertical_switch.set_active(bind_vars.get('vertical', False))
            
            # Update terminal command entry
            self.terminal_entry.set_text(bind_vars['terminal_command'])
            
            # Clear face icon selection status
            self.selected_face_icon = None
            self.face_status_label.set_text("")

    def on_cancel(self, widget):
        self.destroy()


def start_config():
    """
    Run final configuration steps: ensure necessary configs, write the hyprconf, and reload.
    """
    ensure_matugen_config()
    ensure_face_icon()

    # Write the generated hypr configuration to file
    hypr_config_dir = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/")
    os.makedirs(hypr_config_dir, exist_ok=True)
    hypr_conf_path = os.path.join(hypr_config_dir, f"{APP_NAME}.conf")
    with open(hypr_conf_path, "w") as f:
        f.write(generate_hyprconf())

    # Reload Hyprland configuration using subprocess.run instead of os.system
    subprocess.run(["hyprctl", "reload"])


def open_config():
    """
    Entry point for opening the configuration GUI.
    """
    load_bind_vars()

    # Check and copy hyprlock config if needed
    dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
    src_lock = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hyprlock.conf")
    os.makedirs(os.path.dirname(dest_lock), exist_ok=True)
    show_lock_checkbox = True
    if not os.path.exists(dest_lock):
        shutil.copy(src_lock, dest_lock)
        show_lock_checkbox = False

    # Check and copy hypridle config if needed
    dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
    src_idle = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/hypridle.conf")
    show_idle_checkbox = True
    if not os.path.exists(dest_idle):
        shutil.copy(src_idle, dest_idle)
        show_idle_checkbox = False

    # Create and run the GUI
    window = HyprConfGUI(show_lock_checkbox, show_idle_checkbox)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == "__main__":
    open_config()
