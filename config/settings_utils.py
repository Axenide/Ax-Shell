import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import gi
import toml

gi.require_version('Gtk', '3.0')
from fabric.utils.helpers import exec_shell_command_async
from gi.repository import GLib

# Importar settings_constants para DEFAULTS
from . import settings_constants
from .data import (  # CONFIG_DIR, HOME_DIR no se usan aquí directamente
    APP_NAME, APP_NAME_CAP)

# Global variable to store binding variables, managed by this module
bind_vars = {} # Se inicializa vacío, load_bind_vars lo poblará

def deep_update(target: dict, update: dict) -> dict:
    """
    Recursively update a nested dictionary with values from another dictionary.
    Modifies target in-place.
    """
    for key, value in update.items():
        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            # Si el valor es un diccionario y la clave ya existe en target como diccionario,
            # entonces actualiza recursivamente.
            deep_update(target[key], value)
        else:
            # De lo contrario, simplemente establece/sobrescribe el valor.
            target[key] = value
    return target # Aunque modifica in-place, devolverlo es una convención común

def ensure_matugen_config():
    """
    Ensure that the matugen configuration file exists and is updated
    with the expected settings.
    """
    expected_config = {
        'config': {
            'reload_apps': True,
            'wallpaper': {
                'set': False 
            },
            'custom_colors': {
                'red': {'color': "#FF0000", 'blend': True},
                'green': {'color': "#00FF00", 'blend': True},
                'yellow': {'color': "#FFFF00", 'blend': True},
                'blue': {'color': "#0000FF", 'blend': True},
                'magenta': {'color': "#FF00FF", 'blend': True},
                'cyan': {'color': "#00FFFF", 'blend': True},
                'white': {'color': "#FFFFFF", 'blend': True}
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

    existing_config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                existing_config = toml.load(f)
            shutil.copyfile(config_path, config_path + '.bak')
        except toml.TomlDecodeError:
            print(f"Warning: Could not decode TOML from {config_path}. A new default config will be created.")
            existing_config = {} # Reset if corrupt
        except Exception as e:
            print(f"Error reading or backing up {config_path}: {e}")
            # existing_config could be partially loaded or empty.
            # Continue to try merging with defaults.

    merged_config = deep_update(existing_config, expected_config) 

    try:
        with open(config_path, 'w') as f:
            toml.dump(merged_config, f)
    except Exception as e:
        print(f"Error writing matugen config to {config_path}: {e}")

    current_wall = os.path.expanduser("~/.current.wall")
    hypr_colors = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/hypr/colors.conf")
    css_colors = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/styles/colors.css")
    
    # Only do the following if any of the files are missing
    if not os.path.exists(current_wall) or not os.path.exists(hypr_colors) or not os.path.exists(css_colors):
        os.makedirs(os.path.dirname(hypr_colors), exist_ok=True)
        os.makedirs(os.path.dirname(css_colors), exist_ok=True)

        image_path = ""
        if not os.path.exists(current_wall):
            example_wallpaper_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/assets/wallpapers_example/example-1.jpg")
            if os.path.exists(example_wallpaper_path):
                try:
                    if os.path.lexists(current_wall):
                        os.remove(current_wall)
                    os.symlink(example_wallpaper_path, current_wall)
                    image_path = example_wallpaper_path
                except Exception as e:
                    print(f"Error creating symlink for wallpaper: {e}")
        else:
            image_path = os.path.realpath(current_wall) if os.path.islink(current_wall) else current_wall

        if image_path and os.path.exists(image_path): 
            print(f"Generating color theme from wallpaper: {image_path}")
            try:
                matugen_cmd = f"matugen image '{image_path}'"
                exec_shell_command_async(matugen_cmd)
                print("Matugen color theme generation initiated.")
            except FileNotFoundError:
                print("Error: matugen command not found. Please install matugen.")
            except Exception as e:
                print(f"Error initiating matugen: {e}")
        elif not image_path:
            print("Warning: No wallpaper path determined to generate matugen theme from.")
        else:
            print(f"Warning: Wallpaper at {image_path} not found. Cannot generate matugen theme.")

def load_bind_vars():
    """
    Load saved key binding variables from JSON, if available.
    Populates the global `bind_vars` in-place.
    """
    global bind_vars # Necesario para modificar el objeto global bind_vars

    # 1. Limpiar el diccionario bind_vars existente.
    bind_vars.clear()
    # 2. Actualizarlo con una copia de DEFAULTS.
    bind_vars.update(settings_constants.DEFAULTS.copy()) # Usar .copy() para no modificar DEFAULTS accidentalmente

    config_json = os.path.expanduser(f'~/.config/{APP_NAME_CAP}/config/config.json')
    if os.path.exists(config_json):
        try:
            with open(config_json, 'r') as f:
                saved_vars = json.load(f)
                # 3. Usar deep_update para fusionar saved_vars en el bind_vars existente.
                deep_update(bind_vars, saved_vars)

                # La lógica para asegurar la estructura de diccionarios anidados
                # como 'metrics_visible' y 'metrics_small_visible'
                # debe operar sobre el 'bind_vars' ya actualizado.
                for vis_key in ['metrics_visible', 'metrics_small_visible']:
                    # Asegurar que la clave exista en DEFAULTS como referencia de estructura
                    if vis_key in settings_constants.DEFAULTS:
                        default_sub_dict = settings_constants.DEFAULTS[vis_key]
                        # Si la clave no está en bind_vars o no es un diccionario después de deep_update,
                        # restaurarla desde una copia de DEFAULTS para esa clave.
                        if not isinstance(bind_vars.get(vis_key), dict):
                            bind_vars[vis_key] = default_sub_dict.copy()
                        else:
                            # Si es un diccionario, asegurar que todas las sub-claves de DEFAULTS estén presentes.
                            current_sub_dict = bind_vars[vis_key]
                            for m_key, m_val in default_sub_dict.items():
                                if m_key not in current_sub_dict:
                                    current_sub_dict[m_key] = m_val
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {config_json}. Using defaults (already initialized).")
            # bind_vars ya está poblado con DEFAULTS, no se necesita acción adicional aquí.
        except Exception as e:
            print(f"Error loading config from {config_json}: {e}. Using defaults (already initialized).")
            # bind_vars ya está poblado con DEFAULTS.
    # else:
        # Si config_json no existe, bind_vars ya está poblado con DEFAULTS.
        # print(f"Config file {config_json} not found. Using defaults (already initialized).")


def generate_hyprconf() -> str:
    """
    Generate the Hypr configuration string using the current bind_vars.
    """
    home = os.path.expanduser('~')
    # Determine animation type based on bar position
    bar_position = bind_vars.get('bar_position', 'Top')
    is_vertical = bar_position in ["Left", "Right"]
    animation_type = "slidefadevert" if is_vertical else "slidefade"
    
    return f"""exec-once = uwsm-app $(python {home}/.config/{APP_NAME_CAP}/main.py)
exec = pgrep -x "hypridle" > /dev/null || uwsm app -- hypridle
exec = uwsm app -- swww-daemon
exec-once =  wl-paste --type text --watch cliphist store
exec-once =  wl-paste --type image --watch cliphist store

$fabricSend = fabric-cli exec {APP_NAME}
$axMessage = notify-send "Axenide" "FIRE IN THE HOLE‼️🗣️🔥🕳️" -i "{home}/.config/{APP_NAME_CAP}/assets/ax.png" -A "🗣️" -A "🔥" -A "🕳️" -a "Source Code"

bind = {bind_vars.get('prefix_restart', 'SUPER ALT')}, {bind_vars.get('suffix_restart', 'B')}, exec, killall {APP_NAME}; uwsm-app $(python {home}/.config/{APP_NAME_CAP}/main.py) # Reload {APP_NAME_CAP}
bind = {bind_vars.get('prefix_axmsg', 'SUPER')}, {bind_vars.get('suffix_axmsg', 'A')}, exec, $axMessage # Message
bind = {bind_vars.get('prefix_dash', 'SUPER')}, {bind_vars.get('suffix_dash', 'D')}, exec, $fabricSend 'notch.open_notch("dashboard")' # Dashboard
bind = {bind_vars.get('prefix_bluetooth', 'SUPER')}, {bind_vars.get('suffix_bluetooth', 'B')}, exec, $fabricSend 'notch.open_notch("bluetooth")' # Bluetooth
bind = {bind_vars.get('prefix_pins', 'SUPER')}, {bind_vars.get('suffix_pins', 'Q')}, exec, $fabricSend 'notch.open_notch("pins")' # Pins
bind = {bind_vars.get('prefix_kanban', 'SUPER')}, {bind_vars.get('suffix_kanban', 'N')}, exec, $fabricSend 'notch.open_notch("kanban")' # Kanban
bind = {bind_vars.get('prefix_launcher', 'SUPER')}, {bind_vars.get('suffix_launcher', 'R')}, exec, $fabricSend 'notch.open_notch("launcher")' # App Launcher
bind = {bind_vars.get('prefix_tmux', 'SUPER')}, {bind_vars.get('suffix_tmux', 'T')}, exec, $fabricSend 'notch.open_notch("tmux")' # Tmux
bind = {bind_vars.get('prefix_cliphist', 'SUPER')}, {bind_vars.get('suffix_cliphist', 'V')}, exec, $fabricSend 'notch.open_notch("cliphist")' # Clipboard History
bind = {bind_vars.get('prefix_toolbox', 'SUPER')}, {bind_vars.get('suffix_toolbox', 'S')}, exec, $fabricSend 'notch.open_notch("tools")' # Toolbox
bind = {bind_vars.get('prefix_overview', 'SUPER')}, {bind_vars.get('suffix_overview', 'TAB')}, exec, $fabricSend 'notch.open_notch("overview")' # Overview
bind = {bind_vars.get('prefix_wallpapers', 'SUPER')}, {bind_vars.get('suffix_wallpapers', 'COMMA')}, exec, $fabricSend 'notch.open_notch("wallpapers")' # Wallpapers
bind = {bind_vars.get('prefix_randwall', 'SUPER')}, {bind_vars.get('suffix_randwall', 'COMMA')}, exec, $fabricSend 'notch.dashboard.wallpapers.set_random_wallpaper(None, external=True)' # Random Wallpaper
bind = {bind_vars.get('prefix_emoji', 'SUPER')}, {bind_vars.get('suffix_emoji', 'PERIOD')}, exec, $fabricSend 'notch.open_notch("emoji")' # Emoji Picker
bind = {bind_vars.get('prefix_power', 'SUPER')}, {bind_vars.get('suffix_power', 'ESCAPE')}, exec, $fabricSend 'notch.open_notch("power")' # Power Menu
bind = {bind_vars.get('prefix_caffeine', 'SUPER SHIFT')}, {bind_vars.get('suffix_caffeine', 'M')}, exec, $fabricSend 'notch.dashboard.widgets.buttons.caffeine_button.toggle_inhibit(external=True)' # Toggle Caffeine
bind = {bind_vars.get('prefix_css', 'SUPER SHIFT')}, {bind_vars.get('suffix_css', 'B')}, exec, $fabricSend 'app.set_css()' # Reload CSS
bind = {bind_vars.get('prefix_restart_inspector', 'SUPER CTRL ALT')}, {bind_vars.get('suffix_restart_inspector', 'B')}, exec, killall {APP_NAME}; uwsm-app $(GTK_DEBUG=interactive python {home}/.config/{APP_NAME_CAP}/main.py) # Restart with inspector

# Wallpapers directory: {bind_vars.get('wallpapers_dir', '~/.config/Ax-Shell/assets/wallpapers_example')}

source = {home}/.config/{APP_NAME_CAP}/config/hypr/colors.conf

layerrule = noanim, fabric

exec = cp $wallpaper ~/.current.wall

general {{
    col.active_border = rgb($primary)
    col.inactive_border = rgb($surface)
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
    bezier = myBezier, 0.4, 0.0, 0.2, 1.0
    animation = windows, 1, 2.5, myBezier, popin 80%
    animation = border, 1, 2.5, myBezier
    animation = fade, 1, 2.5, myBezier
    animation = workspaces, 1, 2.5, myBezier, {animation_type} 20%
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
            # Asegurarse que el directorio de backup existe si es diferente
            # os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy(dest, backup_path)
            print(f"{config_name} config backed up to {backup_path}")
        os.makedirs(os.path.dirname(dest), exist_ok=True) # Ensure dest directory exists
        shutil.copy(src, dest)
        print(f"{config_name} config replaced from {src}")
    except Exception as e:
        print(f"Error backing up/replacing {config_name} config: {e}")


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
    # Usar APP_NAME para el nombre del archivo .conf para que coincida con SOURCE_STRING corregido
    hypr_conf_path = os.path.join(hypr_config_dir, f"{APP_NAME}.conf")
    try:
        with open(hypr_conf_path, "w") as f:
            f.write(generate_hyprconf())
        print(f"Generated Hyprland config at {hypr_conf_path}")
    except Exception as e:
        print(f"Error writing Hyprland config: {e}")
    print(f"{time.time():.4f}: start_config: Finished generating hypr conf.")

    print(f"{time.time():.4f}: start_config: Initiating hyprctl reload...")
    try:
        # subprocess.run(["hyprctl", "reload"], check=True, capture_output=True, text=True)
        exec_shell_command_async("hyprctl reload") # Mantener async para no bloquear
        print(f"{time.time():.4f}: start_config: Hyprland configuration reload initiated.")
    except FileNotFoundError:
         print("Error: hyprctl command not found. Cannot reload Hyprland.")
    except subprocess.CalledProcessError as e: # Si usáramos subprocess.run con check=True
         print(f"Error reloading Hyprland with hyprctl: {e}\nOutput:\n{e.stdout}\n{e.stderr}")
    except Exception as e:
         print(f"An error occurred initiating hyprctl reload: {e}")
    print(f"{time.time():.4f}: start_config: Finished initiating hyprctl reload.")
