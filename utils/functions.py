import datetime
import os
import shutil
import subprocess
from typing import Dict, List, Literal

import gi
import psutil
from fabric.utils import exec_shell_command, exec_shell_command_async, get_relative_path
from gi.repository import Gdk, GLib, Gtk
from loguru import logger

from .colors import Colors
from .icons import distro_text_icons

gi.require_version("Gtk", "3.0")


class ExecutableNotFoundError(ImportError):
    """Raised when an executable is not found."""

    def __init__(self, executable_name: str):
        super().__init__(
            f"{Colors.ERROR}Executable {Colors.UNDERLINE}{executable_name}{Colors.RESET} not found. Please install it using your package manager."  # noqa: E501
        )


# Function to escape the markup
def parse_markup(text):
    return text


# support for multiple monitors
def for_monitors(widget):
    n = Gdk.Display.get_default().get_n_monitors() if Gdk.Display.get_default() else 1
    return [widget(i) for i in range(n)]


# Function to get the system icon theme
def copy_theme(theme: str):
    destination_file = get_relative_path("../styles/theme.scss")
    source_file = get_relative_path(f"../styles/themes/{theme}.scss")

    if not os.path.exists(source_file):
        logger.warning(
            f"{Colors.WARNING}Warning: The theme file '{theme}.scss' was not found. Using default theme."  # noqa: E501
        )
        source_file = get_relative_path("../styles/themes/catpuccin-mocha.scss")

    try:
        with open(source_file, "r") as source_file:
            content = source_file.read()

        # Open the destination file in write mode
        with open(destination_file, "w") as destination_file:
            destination_file.write(content)
            logger.info(f"{Colors.INFO}[THEME] '{theme}' applied successfully.")

    except FileNotFoundError:
        logger.error(
            f"{Colors.ERROR}Error: The theme file '{source_file}' was not found."
        )
        exit(1)


# Merge the parsed data with the default configuration
def merge_defaults(data: dict, defaults: dict):
    return {**defaults, **data}


# Validate the widgets
def validate_widgets(parsed_data, default_config):
    layout = parsed_data["layout"]
    for section in layout:
        for widget in layout[section]:
            if widget not in default_config:
                raise ValueError(
                    f"Invalid widget {widget} found in section {section}. Please check the widget name."  # noqa: E501
                )


# Function to exclude keys from a dictionary        )
def exclude_keys(d: Dict, keys_to_exclude: List[str]) -> Dict:
    return {k: v for k, v in d.items() if k not in keys_to_exclude}


# Function to format time in hours and minutes
def format_time(secs: int):
    mm, _ = divmod(secs, 60)
    hh, mm = divmod(mm, 60)
    return "%d h %02d min" % (hh, mm)


# Function to convert bytes to kilobytes, megabytes, or gigabytes
def convert_bytes(bytes: int, to: Literal["kb", "mb", "gb"], format_spec=".1f"):
    multiplier = 1

    if to == "mb":
        multiplier = 2
    elif to == "gb":
        multiplier = 3

    return f"{format(bytes / (1024**multiplier), format_spec)}{to.upper()}"


# Function to get the system uptime
def uptime():
    boot_time = psutil.boot_time()
    now = datetime.datetime.now()

    diff = now.timestamp() - boot_time

    # Convert the difference in seconds to hours and minutes
    hours, remainder = divmod(diff, 3600)
    minutes, _ = divmod(remainder, 60)

    return f"{int(hours):02}:{int(minutes):02}"


# Function to convert seconds to milliseconds
def convert_seconds_to_milliseconds(seconds: int):
    return seconds * 1000


# Function to check if an icon exists, otherwise use a fallback icon
def check_icon_exists(icon_name: str, fallback_icon: str) -> str:
    if Gtk.IconTheme.get_default().has_icon(icon_name):
        return icon_name
    return fallback_icon


# Function to execute a shell command asynchronously
def play_sound(file: str):
    exec_shell_command_async(f"play {file}", None)


# Function to get the distro icon
def get_distro_icon():
    distro_id = GLib.get_os_info("ID")

    # Search for the icon in the list
    return distro_text_icons.get(distro_id, "")


# Function to check if an executable exists
def executable_exists(executable_name):
    executable_path = shutil.which(executable_name)
    return bool(executable_path)


def send_notification(
    title: str,
    body: str,
    urgency: Literal["low", "normal", "critical"],
    icon=None,
    app_name="Application",
    timeout=None,
):
    """
    Sends a notification using the notify-send command.
    :param title: The title of the notification
    :param body: The message body of the notification
    :param urgency: The urgency of the notification ('low', 'normal', 'critical')
    :param icon: Optional icon for the notification
    :param app_name: The application name that is sending the notification
    :param timeout: Optional timeout in milliseconds (e.g., 5000 for 5 seconds)
    """
    # Base command
    command = [
        "notify-send",
        "--urgency",
        urgency,
        "--app-name",
        app_name,
        title,
        body,
    ]

    # Add icon if provided
    if icon:
        command.extend(["--icon", icon])

    if timeout is not None:
        command.extend(["-t", str(timeout)])

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to send notification: {e}")


# Function to get the relative time
def get_relative_time(mins: int) -> str:
    # Seconds
    if mins == 0:
        return "now"

    # Minutes
    if mins < 60:
        return f"{mins} minute{'s' if mins > 1 else ''} ago"

    # Hours
    if mins < 1440:
        hours = mins // 60
        return f"{hours} hour{'s' if hours > 1 else ''} ago"

    # Days
    days = mins // 1440
    return f"{days} day{'s' if days > 1 else ''} ago"


# Function to get the percentage of a value
def convert_to_percent(
    current: int | float, max: int | float, is_int=True
) -> int | float:
    if is_int:
        return int((current / max) * 100)
    else:
        return (current / max) * 100


# Function to ensure the directory exists
def ensure_dir_exists(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


# Function to unique list
def unique_list(lst) -> List:
    return list(set(lst))


# Function to check if an app is running
def is_app_running(app_name: str) -> bool:
    return len(exec_shell_command(f"pidof {app_name}")) != 0
