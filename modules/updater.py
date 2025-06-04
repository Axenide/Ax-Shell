import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import gi

# Insertion for embedded VTE terminal
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Vte", "2.91")
from gi.repository import Gdk, GLib, Gtk, Vte

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fabric.utils.helpers import get_relative_path

import config.data as data

# File locations
VERSION_FILE = get_relative_path("../utils/version.json")
REMOTE_VERSION_FILE = "/tmp/remote_version.json"
REMOTE_URL = "https://raw.githubusercontent.com/Axenide/Ax-Shell/refs/heads/main/utils/version.json"
REPO_DIR = get_relative_path("../")

SNOOZE_FILE_NAME = "updater_snooze.txt"
SNOOZE_DURATION_SECONDS = 8 * 60 * 60  # 8 hours

# --- Global state for standalone execution control ---
_QUIT_GTK_IF_NO_WINDOW_STANDALONE = False

def get_snooze_file_path():
    """
    Returns the path to the 'snooze' file inside ~/.cache/APP_NAME.
    """
    cache_dir_base = data.CACHE_DIR or os.path.expanduser(f"~/.cache/{data.APP_NAME}")
    try:
        os.makedirs(cache_dir_base, exist_ok=True)
    except Exception as e:
        print(f"Error creating cache directory {cache_dir_base}: {e}")
    return os.path.join(cache_dir_base, SNOOZE_FILE_NAME)


def fetch_remote_version():
    """
    Downloads the remote version JSON using curl, with timeout and error handling.
    """
    try:
        subprocess.run(
            ["curl", "-sL", "--connect-timeout", "10", REMOTE_URL, "-o", REMOTE_VERSION_FILE],
            check=False,
            timeout=15
        )
    except subprocess.TimeoutExpired:
        print("Error: curl timed out while fetching the remote version.")
    except FileNotFoundError:
        print("Error: curl not found. Please install curl.")
    except Exception as e:
        print(f"Error fetching remote version: {e}")


def get_local_version():
    """
    Reads the local version file and returns (version, changelog).
    """
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r") as f:
                data_content = json.load(f)
                return data_content.get("version", "0.0.0"), data_content.get("changelog", [])
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in local file: {VERSION_FILE}")
            return "0.0.0", []
        except Exception as e:
            print(f"Error reading local version file {VERSION_FILE}: {e}")
            return "0.0.0", []
    return "0.0.0", []


def get_remote_version():
    """
    Reads the downloaded remote file and returns (version, changelog, download_url).
    """
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            with open(REMOTE_VERSION_FILE, "r") as f:
                data_content = json.load(f)
                return (
                    data_content.get("version", "0.0.0"),
                    data_content.get("changelog", []),
                    data_content.get("download_url", "#"),
                )
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in remote file: {REMOTE_VERSION_FILE}")
            return "0.0.0", [], "#"
        except Exception as e:
            print(f"Error reading remote version file {REMOTE_VERSION_FILE}: {e}")
            return "0.0.0", [], "#"
    return "0.0.0", [], "#"


def update_local_version_file():
    """
    Replaces the local version with the remote one by moving the downloaded JSON to the local version file.
    """
    if os.path.exists(REMOTE_VERSION_FILE):
        try:
            shutil.move(REMOTE_VERSION_FILE, VERSION_FILE)
        except Exception as e:
            print(f"Error updating local version file: {e}")
            raise


def is_connected():
    """
    Checks basic connectivity by attempting to connect to www.google.com:80.
    """
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False


class UpdateWindow(Gtk.Window):
    def __init__(self, latest_version, changelog, is_standalone_mode=False):
        super().__init__(name="update-window", title=f"{data.APP_NAME_CAP} Updater")
        self.set_default_size(500, 480)
        self.set_border_width(16)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        self.is_standalone_mode = is_standalone_mode
        self.quit_gtk_main_on_destroy = False

        # Main vertical container
        self.main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(self.main_vbox)

        # Title
        title_label = Gtk.Label(name="update-title")
        title_label.set_markup("<span size='xx-large' weight='bold'>📦 Update Available ✨</span>")
        title_label.get_style_context().add_class("title-1")
        self.main_vbox.pack_start(title_label, False, False, 10)

        # Version info text
        info_label = Gtk.Label(
            label=f"A new version ({latest_version}) of {data.APP_NAME_CAP} is available."
        )
        info_label.set_xalign(0)
        info_label.set_line_wrap(True)
        self.main_vbox.pack_start(info_label, False, False, 0)

        # Changelog header
        changelog_header_label = Gtk.Label()
        changelog_header_label.set_markup("<b>Changelog:</b>")
        changelog_header_label.set_xalign(0)
        self.main_vbox.pack_start(changelog_header_label, False, False, 5)

        # — Scrollable window for the changelog (using Gtk.Label with markup) —
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        if changelog:
            # Each entry may already contain Pango tags (<b>, <i>, etc.)
            joined = "\n".join(f"• {change}" for change in changelog)
        else:
            joined = "No specific changes listed for this version."

        self.changelog_label = Gtk.Label()
        self.changelog_label.set_xalign(0)
        self.changelog_label.set_yalign(0)
        self.changelog_label.set_line_wrap(Gtk.WrapMode.WORD_CHAR) # Gtk.WrapMode instead of just True
        self.changelog_label.set_selectable(False)
        self.changelog_label.set_markup(joined)

        scrolled_window.add(self.changelog_label)
        self.main_vbox.pack_start(scrolled_window, True, True, 0)

        # ProgressBar (will be shown if we need to indicate status, although with VTE it remains unused)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_no_show_all(True)
        self.progress_bar.set_visible(False)
        self.main_vbox.pack_start(self.progress_bar, False, False, 5)

        # Button container
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_box.set_halign(Gtk.Align.END)
        self.main_vbox.pack_start(action_box, False, False, 10)

        # Update button (will now show embedded VTE terminal)
        self.update_button = Gtk.Button(name="update-button", label="Update")
        self.update_button.get_style_context().add_class("suggested-action")
        self.update_button.connect("clicked", self.on_update_clicked)
        action_box.pack_end(self.update_button, False, False, 0)

        # 'Later' button
        self.close_button = Gtk.Button(name="later-button", label="Later")
        self.close_button.connect("clicked", self.on_later_clicked)
        action_box.pack_end(self.close_button, False, False, 0)

        self.connect("destroy", self.on_window_destroyed)

        # Placeholder for embedded terminal
        self.terminal_container = None
        self.vte_terminal = None

    def on_later_clicked(self, _widget):
        """
        When 'Later' is clicked, create/update the snooze file and close the window.
        """
        snooze_file_path = get_snooze_file_path()
        try:
            with open(snooze_file_path, "w") as f:
                f.write(str(time.time()))
            print(f"Update snoozed. Snooze file at: {snooze_file_path}")
        except Exception as e:
            print(f"Error creating snooze file {snooze_file_path}: {e}")
        self.destroy()

    def on_update_clicked(self, _widget):
        """
        When 'Update' is pressed, disable buttons, hide the progress bar,
        and create a VTE terminal to run the curl | bash script.
        """
        # Disable the buttons so they can't be clicked again
        self.update_button.set_sensitive(False)
        self.close_button.set_sensitive(False)

        # Hide the progress bar (we don't need it now)
        self.progress_bar.set_visible(False)

        # If there's no container for the terminal, create it
        if self.terminal_container is None:
            # Scrollable container so the terminal can scroll
            self.terminal_container = Gtk.ScrolledWindow()
            self.terminal_container.set_hexpand(True)
            self.terminal_container.set_vexpand(True)
            self.terminal_container.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

            # Create the VTE terminal
            self.vte_terminal = Vte.Terminal()
            self.vte_terminal.set_size(120, 48)
            # Make update window larger
            self.set_default_size(720, 540)
            self.terminal_container.add(self.vte_terminal)
            # Insert the terminal at the end of main_vbox
            self.main_vbox.pack_start(self.terminal_container, True, True, 0)

        # Show everything
        self.show_all()

        # Command to run in the terminal
        curl_command = "curl -fsSL https://raw.githubusercontent.com/Axenide/Ax-Shell/main/install.sh | bash"

        # Spawn the process asynchronously inside the terminal
        self.vte_terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ.get("HOME", "/"),
            ["/bin/bash", "-lc", curl_command],
            [],
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None,
            None,
            -1,
            None,
            None,
            self.on_curl_script_exit,
            None
        )

    def on_curl_script_exit(self, terminal, exit_status, user_data):
        """
        Callback when the script running in the VTE terminal finishes.
        Depending on exit_status, success or failure is considered.
        """
        # exit_status is encoded: 0 means success
        if exit_status == 0:
            # Call the success routine, which restarts the app
            GLib.idle_add(self.handle_update_success)
        else:
            # If there was an error, read the last part of the buffer to display it
            end_iter = self.vte_terminal.get_end_iter()
            start_iter = self.vte_terminal.get_iter_at_line(max(0, self.vte_terminal.get_line_count() - 5))
            error_excerpt = self.vte_terminal.get_text_range(start_iter, end_iter, False)
            GLib.idle_add(self.handle_update_failure, f"Script exited with status {exit_status}. Last lines:\n{error_excerpt}")

    def handle_update_success(self):
        """
        Shows a success message in the progress bar and restarts the application after 2 seconds.
        """
        # If there was any progress bar timeout, remove it
        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")

        # Replace the terminal (or other widget) with a brief message
        # First remove the terminal to show the progress bar and text
        if self.terminal_container:
            self.main_vbox.remove(self.terminal_container)

        # Prepare the progress bar to indicate success
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Update Complete. Restarting application...")
        self.progress_bar.set_show_text(True)

        # Force it to show
        self.show_all()

        # After 2 seconds, close and restart
        GLib.timeout_add_seconds(2, self.trigger_restart_and_close)

    def trigger_restart_and_close(self):
        """
        Closes the window and relaunches the application.
        """
        self.destroy()
        # Relaunch logic would typically be here if not handled by an external script
        # For now, it just closes. A real restart might involve:
        # os.execv(sys.executable, [sys.executable] + sys.argv)
        return False  # So the timeout runs only once

    def handle_update_failure(self, error_message):
        """
        Shows an error dialog if the script execution fails.
        """
        # If there was any progress bar timeout, remove it
        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")

        # Indicate failure in the progress bar
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Update Failed.")
        self.progress_bar.set_show_text(True)

        # Buttons are re-enabled to retry or close
        self.update_button.set_sensitive(True)
        self.close_button.set_sensitive(True)

        # Error dialog
        error_dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Update Failed",
        )
        error_dialog.format_secondary_text(error_message)
        error_dialog.run()
        error_dialog.destroy()

    def on_window_destroyed(self, _widget):
        """
        If the window is destroyed and we're in standalone mode, quit Gtk.main().
        """
        if hasattr(self, "pulse_timeout_id"):
            GLib.source_remove(self.pulse_timeout_id)
            delattr(self, "pulse_timeout_id")

        if self.quit_gtk_main_on_destroy:
            Gtk.main_quit()


def _initiate_update_check_flow(is_standalone_mode, force=False): # Added force argument with default
    """
    Logic that checks connection, snooze, and downloads the remote version.
    If there's a new version or force is True, launches the update window.
    """
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE

    if not is_connected():
        print("No internet connection. Skipping update check.")
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)
        return

    fetch_remote_version()
    latest_version, changelog, _ = get_remote_version()

    if force:
        print(f"Force update mode enabled. Opening updater for version {latest_version}.")
        if latest_version == "0.0.0" and not changelog:
            print(f"Warning: Could not fetch remote version details for {data.APP_NAME_CAP}. Updater will show default/empty info.")
        GLib.idle_add(launch_update_window, latest_version, changelog, is_standalone_mode)
        return # Exit after launching in force mode

    # --- Regular update check flow (if not forced) ---
    snooze_file_path = get_snooze_file_path()
    if os.path.exists(snooze_file_path):
        try:
            with open(snooze_file_path, "r") as f:
                snooze_timestamp_str = f.read().strip()
                snooze_timestamp = float(snooze_timestamp_str)

            current_time = time.time()
            if current_time - snooze_timestamp < SNOOZE_DURATION_SECONDS:
                snooze_until_time = snooze_timestamp + SNOOZE_DURATION_SECONDS
                snooze_until_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(snooze_until_time))
                print(f"Check postponed. It will resume after {snooze_until_time_str}.")
                if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
                    GLib.idle_add(Gtk.main_quit)
                return
            else:
                print("Snooze period expired. Removing file and checking for updates.")
                os.remove(snooze_file_path)
        except ValueError:
            print(f"Error: invalid content in snooze file. Removing: {snooze_file_path}")
            try:
                os.remove(snooze_file_path)
            except OSError as e_remove:
                print(f"Error removing corrupt snooze file: {e_remove}")
        except Exception as e_snooze:
            print(f"Error processing snooze file {snooze_file_path}: {e_snooze}. Proceeding with check.")
            try:
                os.remove(snooze_file_path) # Attempt to remove problematic snooze file
            except OSError as e_remove_generic:
                print(f"Error removing problematic snooze file: {e_remove_generic}")


    current_version, _ = get_local_version()

    # Basic version comparison (not strict semver)
    if latest_version > current_version and latest_version != "0.0.0":
        GLib.idle_add(launch_update_window, latest_version, changelog, is_standalone_mode)
    else:
        print(f"{data.APP_NAME_CAP} is up to date or the remote version is invalid.")
        if is_standalone_mode and _QUIT_GTK_IF_NO_WINDOW_STANDALONE:
            GLib.idle_add(Gtk.main_quit)


def launch_update_window(latest_version, changelog, is_standalone_mode):
    """
    Creates and shows the update window.
    """
    win = UpdateWindow(latest_version, changelog, is_standalone_mode)
    if is_standalone_mode:
        win.quit_gtk_main_on_destroy = True
    win.show_all()


def check_for_updates():
    """
    Public function for module: starts the update check in a background thread.
    This will run with force=False by default.
    """
    # _initiate_update_check_flow's 'force' parameter defaults to False,
    # so passing args=(False,) correctly sets is_standalone_mode=False and force=False.
    thread = threading.Thread(target=_initiate_update_check_flow, args=(False,), daemon=True)
    thread.start()


def run_updater(force=False): # Modified to accept force argument
    """
    Standalone entry point: starts Gtk.main and the update check.
    Args:
        force (bool): If True, opens the updater even if the version isn't outdated or snoozed.
                      Defaults to False.
    """
    global _QUIT_GTK_IF_NO_WINDOW_STANDALONE
    _QUIT_GTK_IF_NO_WINDOW_STANDALONE = True

    # Pass the force argument to the target function
    update_check_thread = threading.Thread(target=_initiate_update_check_flow, args=(True, force), daemon=True)
    update_check_thread.start()

    Gtk.main()


if __name__ == "__main__":
    # Example of how to run with force=True:
    # run_updater(force=True)
    # By default, runs with force=False:
    run_updater()
