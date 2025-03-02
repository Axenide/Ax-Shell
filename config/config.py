import os
import json
import shutil
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from PIL import Image
import toml

# Constants
SOURCE_STRING = """
# Ax-Shell
source = ~/.config/Ax-Shell/config/hypr/ax-shell.conf
"""

CONFIG_DIR = os.path.expanduser("~/.config/Ax-Shell")
WALLPAPERS_DIR_DEFAULT = os.path.expanduser("~/.config/Ax-Shell/assets/wallpapers_example")

# Default key binding values
bind_vars = {
    'prefix_restart': "SUPER ALT",
    'suffix_restart': "B",
    'prefix_axmsg': "SUPER",
    'suffix_axmsg': "A",
    'prefix_dash': "SUPER",
    'suffix_dash': "D",
    'prefix_bluetooth': "SUPER",
    'suffix_bluetooth': "B",
    'prefix_launcher': "SUPER",
    'suffix_launcher': "R",
    'prefix_overview': "SUPER",
    'suffix_overview': "TAB",
    'prefix_power': "SUPER",
    'suffix_power': "ESCAPE",
    'prefix_toggle': "SUPER CTRL",
    'suffix_toggle': "B",
    'prefix_css': "SUPER SHIFT",
    'suffix_css': "B",
    'wallpapers_dir': WALLPAPERS_DIR_DEFAULT,
    'prefix_restart_inspector': "SUPER CTRL ALT",
    'suffix_restart_inspector': "B",
}


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
                'input_path': '~/.config/Ax-Shell/config/matugen/templates/hyprland-colors.conf',
                'output_path': '~/.config/Ax-Shell/config/hypr/colors.conf'
            },
            'ax-shell': {
                'input_path': '~/.config/Ax-Shell/config/matugen/templates/ax-shell.css',
                'output_path': '~/.config/Ax-Shell/styles/colors.css',
                'post_hook': "fabric-cli exec ax-shell 'app.set_css()' &"
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
        image_path = os.path.expanduser("~/.config/Ax-Shell/assets/wallpapers_example/example-1.jpg")
        os.system(f"matugen image {image_path}")


def ensure_fonts():
    """
    Ensure that required fonts are installed.
    """
    fonts_to_copy = [
        ('~/.fonts/zed-sans/', '~/.config/Ax-Shell/assets/fonts/zed-sans/'),
        ('~/.fonts/tabler-icons/', '~/.config/Ax-Shell/assets/fonts/tabler-icons/')
    ]
    for dest_font, src_font in fonts_to_copy:
        dest_path = os.path.expanduser(dest_font)
        if not os.path.exists(dest_path):
            shutil.copytree(os.path.expanduser(src_font), dest_path)


def load_bind_vars():
    """
    Load saved key binding variables from JSON, if available.
    """
    config_json = os.path.expanduser('~/.config/Ax-Shell/config/config.json')
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
    return f"""exec-once = uwsm app -- python {home}/.config/Ax-Shell/main.py
exec = pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle
exec = uwsm app -- swww-daemon

$fabricSend = fabric-cli exec ax-shell
$axMessage = notify-send "Axenide" "What are you doing?" -i "{home}/.config/Ax-Shell/assets/ax.png" -a "Source Code" -A "Be patient. 🍙"

bind = {bind_vars['prefix_restart']}, {bind_vars['suffix_restart']}, exec, killall ax-shell; uwsm app -- python {home}/.config/Ax-Shell/main.py # Reload Ax-Shell | Default: SUPER ALT + B
bind = {bind_vars['prefix_axmsg']}, {bind_vars['suffix_axmsg']}, exec, $axMessage # Message | Default: SUPER + A
bind = {bind_vars['prefix_dash']}, {bind_vars['suffix_dash']}, exec, $fabricSend 'notch.open_notch("dashboard")' # Dashboard | Default: SUPER + D
bind = {bind_vars['prefix_bluetooth']}, {bind_vars['suffix_bluetooth']}, exec, $fabricSend 'notch.open_notch("bluetooth")' # Bluetooth | Default: SUPER + B
bind = {bind_vars['prefix_launcher']}, {bind_vars['suffix_launcher']}, exec, $fabricSend 'notch.open_notch("launcher")' # App Launcher | Default: SUPER + R
bind = {bind_vars['prefix_overview']}, {bind_vars['suffix_overview']}, exec, $fabricSend 'notch.open_notch("overview")' # Overview | Default: SUPER + TAB
bind = {bind_vars['prefix_power']}, {bind_vars['suffix_power']}, exec, $fabricSend 'notch.open_notch("power")' # Power Menu | Default: SUPER + ESCAPE
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'bar.toggle_hidden()' # Toggle Bar | Default: SUPER CTRL + B
bind = {bind_vars['prefix_toggle']}, {bind_vars['suffix_toggle']}, exec, $fabricSend 'notch.toggle_hidden()' # Toggle Notch | Default: SUPER CTRL + B
bind = {bind_vars['prefix_css']}, {bind_vars['suffix_css']}, exec, $fabricSend 'app.set_css()' # Reload CSS | Default: SUPER SHIFT + B
bind = {bind_vars['prefix_restart_inspector']}, {bind_vars['suffix_restart_inspector']}, exec, killall ax-shell; GTK_DEBUG=interactive uwsm app -- python {home}/.config/Ax-Shell/main.py # Restart with inspector | Default: SUPER CTRL ALT + B

# Wallpapers directory: {bind_vars['wallpapers_dir']}

source = {home}/.config/Ax-Shell/config/hypr/colors.conf

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
    bezier = myBezier, .5, .25, 0, 1
    animation = windows, 1, 2.5, myBezier, popin 80%
    animation = border, 1, 2.5, myBezier
    animation = fade, 1, 2.5, myBezier
    animation = workspaces, 1, 2.5, myBezier, slidefade 20%
}}
"""


def ensure_face_icon():
    """
    Ensure the face icon exists. If not, copy the default icon.
    """
    face_icon_path = os.path.expanduser("~/.face.icon")
    default_icon_path = os.path.expanduser("~/.config/Ax-Shell/assets/default.png")
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
        super().__init__(title="Configure Key Binds")
        self.set_border_width(20)
        self.set_default_size(500, 450)
        self.set_resizable(False)

        self.selected_face_icon = None

        # Use a grid for a more homogeneous layout
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        self.add(grid)

        # Header label spanning across columns
        header = Gtk.Label(label="Configure Key Bindings")
        header.set_halign(Gtk.Align.CENTER)
        grid.attach(header, 0, 0, 4, 1)

        self.entries = []
        bindings = [
            ("Reload Ax-Shell", 'prefix_restart', 'suffix_restart'),
            ("Message", 'prefix_axmsg', 'suffix_axmsg'),
            ("Dashboard", 'prefix_dash', 'suffix_dash'),
            ("Bluetooth", 'prefix_bluetooth', 'suffix_bluetooth'),
            ("App Launcher", 'prefix_launcher', 'suffix_launcher'),
            ("Overview", 'prefix_overview', 'suffix_overview'),
            ("Power Menu", 'prefix_power', 'suffix_power'),
            ("Toggle Bar and Notch", 'prefix_toggle', 'suffix_toggle'),
            ("Reload CSS", 'prefix_css', 'suffix_css'),
            ("Restart with inspector", 'prefix_restart_inspector', 'suffix_restart_inspector'),
        ]

        # Populate grid with key binding rows, starting at row 1
        row = 1
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

        # Row for Wallpapers Directory chooser
        wall_label = Gtk.Label(label="Wallpapers Directory")
        wall_label.set_halign(Gtk.Align.START)
        grid.attach(wall_label, 0, row, 1, 1)
        self.wall_dir_chooser = Gtk.FileChooserButton(
            title="Select a folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        self.wall_dir_chooser.set_filename(bind_vars['wallpapers_dir'])
        grid.attach(self.wall_dir_chooser, 1, row, 3, 1)
        row += 1

        # Row for Profile Icon selection
        face_label = Gtk.Label(label="Profile Icon")
        face_label.set_halign(Gtk.Align.START)
        grid.attach(face_label, 0, row, 1, 1)
        face_btn = Gtk.Button(label="Select Image")
        face_btn.connect("clicked", self.on_select_face_icon)
        grid.attach(face_btn, 1, row, 3, 1)
        row += 1

        # Row for optional checkboxes
        if show_lock_checkbox:
            self.lock_checkbox = Gtk.CheckButton(label="Replace Hyprlock config")
            self.lock_checkbox.set_active(False)
            grid.attach(self.lock_checkbox, 0, row, 2, 1)
        if show_idle_checkbox:
            self.idle_checkbox = Gtk.CheckButton(label="Replace Hypridle config")
            self.idle_checkbox.set_active(False)
            grid.attach(self.idle_checkbox, 2, row, 2, 1)
        row += 1

        # Row for Cancel and Accept buttons, aligned to the right
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", self.on_cancel)
        accept_btn = Gtk.Button(label="Accept")
        accept_btn.connect("clicked", self.on_accept)
        grid.attach(cancel_btn, 2, row, 1, 1)
        grid.attach(accept_btn, 3, row, 1, 1)

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
            print(f"Face icon selected: {self.selected_face_icon}")
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

        # Save the updated bind_vars to a JSON file
        config_json = os.path.expanduser('~/.config/Ax-Shell/config/config.json')
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

        # Replace hyprlock config if requested
        if hasattr(self, "lock_checkbox") and self.lock_checkbox.get_active():
            src_lock = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hyprlock.conf")
            dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
            backup_and_replace(src_lock, dest_lock, "Hyprlock")

        # Replace hypridle config if requested
        if hasattr(self, "idle_checkbox") and self.idle_checkbox.get_active():
            src_idle = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hypridle.conf")
            dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
            backup_and_replace(src_idle, dest_idle, "Hypridle")

        # Append the source string to the Hyprland config if not present
        hyprland_config_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
        with open(hyprland_config_path, "r") as f:
            content = f.read()
        if SOURCE_STRING not in content:
            with open(hyprland_config_path, "a") as f:
                f.write(SOURCE_STRING)

        start_config()
        self.destroy()

    def on_cancel(self, widget):
        self.destroy()


def start_config():
    """
    Run final configuration steps: ensure necessary configs, write the hyprconf, and reload.
    """
    ensure_matugen_config()
    ensure_face_icon()

    # Write the generated hypr configuration to file
    hypr_config_dir = os.path.expanduser("~/.config/Ax-Shell/config/hypr/")
    os.makedirs(hypr_config_dir, exist_ok=True)
    hypr_conf_path = os.path.join(hypr_config_dir, "ax-shell.conf")
    with open(hypr_conf_path, "w") as f:
        f.write(generate_hyprconf())

    # Reload Hyprland configuration
    os.system("hyprctl reload")


def open_config():
    """
    Entry point for opening the configuration GUI.
    """
    ensure_fonts()
    load_bind_vars()

    # Check and copy hyprlock config if needed
    dest_lock = os.path.expanduser("~/.config/hypr/hyprlock.conf")
    src_lock = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hyprlock.conf")
    os.makedirs(os.path.dirname(dest_lock), exist_ok=True)
    show_lock_checkbox = True
    if not os.path.exists(dest_lock):
        shutil.copy(src_lock, dest_lock)
        show_lock_checkbox = False

    # Check and copy hypridle config if needed
    dest_idle = os.path.expanduser("~/.config/hypr/hypridle.conf")
    src_idle = os.path.expanduser("~/.config/Ax-Shell/config/hypr/hypridle.conf")
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
