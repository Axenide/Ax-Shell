import os
import subprocess
import re
import time

from fabric.core.service import Property, Service, Signal
from fabric.utils import exec_shell_command_async, monitor_file
from gi.repository import Gio, GLib
from loguru import logger

import utils.functions as helpers
from utils.colors import Colors


class Brightness(Service):
    """Service for controlling screen brightness using ddcutil or brightnessctl backends.

    The service works with RAW values (0 to max_screen) for both backends:
    - brightnessctl: raw values are device-specific (e.g., 0-96000)
    - ddcutil: raw values are percentages (0-100)

    The 'screen' signal emits percentage values (0-100) for UI display.
    """

    instance = None
    DDCUTIL_PARAMS = "--disable-dynamic-sleep --sleep-multiplier=0.05"
    MIN_CHANGE_THRESHOLD = 2  # Minimum brightness change to apply (percent)
    CACHE_INTERVAL = 3  # Cache duration in seconds
    POLL_INTERVAL = 500  # File polling interval in ms

    @staticmethod
    def get_initial():
        """Singleton to get Brightness service instance."""
        if Brightness.instance is None:
            Brightness.instance = Brightness()
        return Brightness.instance

    @Signal
    def screen(self, value: int) -> None:
        """Signal emitted when screen brightness changes (value: percentage from 0 to 100)."""
        pass

    def __init__(self, backend=None, **kwargs):
        """Initialize service with automatic backend detection."""
        super().__init__(**kwargs)
        self._pending_raw = None
        self._timer_id = None
        self._poll_timer_id = None
        self._file_monitor = None
        self._lock = GLib.Mutex()
        self._last_percent = -1
        self._last_raw = -1
        self._last_update_time = 0
        self._last_file_mtime = 0

        # Detect backend
        self.backend = self._detect_backend(backend)

        self.max_screen = self._read_max_brightness() or 100

        if self.backend:
            if self.backend == "ddcutil":
                # Initialize brightness cache
                GLib.timeout_add(100, lambda: self._update_brightness_cache())
            else:
                # Setup polling for brightness file
                self._setup_polling()

    def _setup_polling(self):
        """Setup file monitoring for brightness changes using inotify."""
        try:
            file_path = f"/sys/class/backlight/{self._get_screen_device()}/brightness"
            if os.path.exists(file_path):
                with open(file_path) as f:
                    self._last_raw = int(f.readline().strip())
                    self._last_percent = (
                        int((self._last_raw / self.max_screen) * 100)
                        if self.max_screen > 0
                        else 0
                    )
                gfile = Gio.File.new_for_path(file_path)
                self._file_monitor = gfile.monitor_file(Gio.FileMonitorFlags.NONE, None)
                self._file_monitor.connect("changed", self._on_brightness_file_changed)
                logger.info(f"Brightness file monitor set up for {file_path}")
        except Exception as e:
            logger.error(f"Error setting up brightness monitoring: {e}")
            # Fall back to polling if inotify fails
            self._last_file_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            self._poll_timer_id = GLib.timeout_add(
                self.POLL_INTERVAL, self._check_brightness_file
            )

    def _on_brightness_file_changed(self, monitor, file, other_file, event_type):
        """Handle brightness file change events from inotify."""
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            try:
                file_path = f"/sys/class/backlight/{self._get_screen_device()}/brightness"
                with open(file_path) as f:
                    raw = int(f.readline().strip())
                if raw != self._last_raw:
                    self._last_raw = raw
                    percent = (
                        int((raw / self.max_screen) * 100)
                        if self.max_screen > 0
                        else 0
                    )
                    if abs(percent - self._last_percent) >= self.MIN_CHANGE_THRESHOLD:
                        self._last_percent = percent
                        self.emit("screen", percent)
            except Exception as e:
                logger.error(f"Error handling brightness file change: {e}")

    def _check_brightness_file(self):
        """Periodically check brightness file for changes."""
        try:
            file_path = f"/sys/class/backlight/{self._get_screen_device()}/brightness"
            if os.path.exists(file_path):
                current_mtime = os.path.getmtime(file_path)
                if current_mtime > self._last_file_mtime:
                    self._last_file_mtime = current_mtime
                    with open(file_path) as f:
                        raw = int(f.readline().strip())

                    if raw != self._last_raw:
                        self._last_raw = raw
                        percent = (
                            int((raw / self.max_screen) * 100)
                            if self.max_screen > 0
                            else 0
                        )
                        if (
                            abs(percent - self._last_percent)
                            >= self.MIN_CHANGE_THRESHOLD
                        ):
                            self._last_percent = percent
                            self.emit("screen", percent)
            return True
        except Exception as e:
            logger.error(f"Error checking brightness file: {e}")
            return True

    def _detect_backend(self, backend):
        """Detect appropriate backend for brightness control."""
        if backend:
            logger.info(f"Using forced backend: {backend}")
            return backend

        # Try brightnessctl first (preferred for laptop internal displays)
        if helpers.executable_exists("brightnessctl"):
            device = self._get_screen_device()
            if device:  # Non-empty string means device found
                logger.info(f"Using brightnessctl backend with device: {device}")
                return "brightnessctl"
            else:
                logger.debug(
                    "brightnessctl is available but no backlight devices found in /sys/class/backlight/"
                )

        # Try ddcutil for external monitors (via DDC/CI protocol)
        if helpers.executable_exists("ddcutil"):
            bus = self._detect_ddcutil_bus()
            if bus != -1:
                self.ddcutil_bus = bus
                logger.info(f"Using ddcutil backend with I2C bus: {bus}")
                return "ddcutil"
            else:
                logger.debug(
                    "ddcutil is available but no DDC/CI capable monitors detected"
                )

        logger.warning(
            "No available backend for brightness control - no backlight devices or DDC/CI monitors found"
        )
        return None

    def _get_screen_device(self):
        """Return first backlight device from sysfs."""
        try:
            return os.listdir("/sys/class/backlight")[0]
        except Exception:
            return ""

    def _detect_ddcutil_bus(self):
        """Detect I2C bus number for ddcutil."""
        try:
            process = subprocess.run(
                ["ddcutil", "detect"], text=True, capture_output=True, timeout=2
            )
            if process.returncode == 0:
                match = re.search(r"I2C bus:\s*/dev/i2c-(\d+)", process.stdout)
                return int(match.group(1)) if match else -1
            return -1
        except Exception:
            return -1

    def _read_max_brightness(self):
        """Read maximum brightness value"""
        if self.backend:
            if self.backend == "ddcutil":
                try:
                    process = subprocess.run(
                        [
                            "ddcutil",
                            "--bus",
                            str(self.ddcutil_bus),
                            *self.DDCUTIL_PARAMS.split(),
                            "getvcp",
                            "10",
                        ],
                        text=True,
                        capture_output=True,
                        timeout=2,
                    )

                    if process.returncode == 0:
                        match = re.search(
                            r"current value\s*=\s*(\d+)\s*,\s*max value\s*=\s*(\d+)",
                            process.stdout,
                        )
                        if match:
                            return int(match.group(2))
                except Exception as e:
                    logger.error(f"Error executing ddcutil: {e}")
            else:
                try:
                    with open(
                        f"/sys/class/backlight/{self._get_screen_device()}/max_brightness"
                    ) as f:
                        return int(f.readline().strip())
                except Exception:
                    return None

    def _update_brightness_cache(self):
        """Update brightness cache with current value."""
        if self.backend == "ddcutil":
            self.screen_brightness  # This will update the cache
        return False

    @Property(int, "read-write")
    def screen_brightness(self):
        """Getter returns current brightness in RAW value (0 to max_screen)."""
        if not self.backend:
            return -1

        if self.backend == "brightnessctl":
            # Return cached raw value if available
            if self._last_raw != -1:
                return self._last_raw

            try:
                with open(
                    f"/sys/class/backlight/{self._get_screen_device()}/brightness"
                ) as f:
                    raw = int(f.readline().strip())
                self._last_raw = raw
                return raw
            except Exception as e:
                logger.error(f"Error reading brightness file: {e}")
                return -1
        elif self.backend == "ddcutil":
            # Use cached value if recent enough
            if (
                time.time() - self._last_update_time < self.CACHE_INTERVAL
                and self._last_raw != -1
            ):
                return self._last_raw

            try:
                process = subprocess.run(
                    [
                        "ddcutil",
                        "--bus",
                        str(self.ddcutil_bus),
                        *self.DDCUTIL_PARAMS.split(),
                        "getvcp",
                        "10",
                    ],
                    text=True,
                    capture_output=True,
                    timeout=2,
                )

                if process.returncode == 0:
                    match = re.search(
                        r"current value\s*=\s*(\d+)\s*,\s*max value\s*=\s*(\d+)",
                        process.stdout,
                    )
                    if match:
                        current = int(match.group(1))
                        # For ddcutil, raw value IS the current value (0-100)
                        self._last_raw = current
                        self._last_update_time = time.time()
                        return current
            except Exception as e:
                logger.error(f"Error executing ddcutil: {e}")

            return self._last_raw if self._last_raw != -1 else -1

    @screen_brightness.setter
    def screen_brightness(self, value: int):
        """Setter accepts brightness value in RAW (0 to max_screen)."""
        self._lock.lock()
        try:
            # Limit value between 0 and max_screen
            value = max(0, min(value, self.max_screen))

            # Check if change is significant enough (in percentage terms)
            current_percent = (
                int((self._last_raw / self.max_screen) * 100)
                if self._last_raw != -1 and self.max_screen > 0
                else -1
            )
            new_percent = (
                int((value / self.max_screen) * 100) if self.max_screen > 0 else 0
            )

            if (
                abs(new_percent - current_percent) < self.MIN_CHANGE_THRESHOLD
                and self._last_raw != -1
            ):
                return

            self._pending_raw = value

            # Use a single timer for applying changes
            if self._timer_id:
                GLib.source_remove(self._timer_id)
            self._timer_id = GLib.timeout_add(50, self._apply_brightness)
        finally:
            self._lock.unlock()

    def _apply_brightness(self):
        """Apply pending brightness change with optimized debouncing."""
        self._lock.lock()
        try:
            if self._pending_raw is None:
                self._timer_id = None
                return False

            raw = self._pending_raw
            self._pending_raw = None
            self._timer_id = None
        finally:
            self._lock.unlock()

        try:
            # Update cache before executing command for faster UI response
            self._last_raw = raw

            # Calculate percentage for signal emission
            percent = int((raw / self.max_screen) * 100) if self.max_screen > 0 else 0

            if self.backend == "brightnessctl":
                self.emit("screen", percent)
                exec_shell_command_async(
                    f"brightnessctl --device '{self._get_screen_device()}' set {raw}"
                )
            elif self.backend == "ddcutil":
                self._last_update_time = time.time()
                self.emit("screen", percent)
                exec_shell_command_async(
                    f"ddcutil --bus {self.ddcutil_bus} {self.DDCUTIL_PARAMS} --terse setvcp 10 {raw}",
                    lambda exit_code, stdout, stderr: logger.error(
                        f"ddcutil error (code {exit_code}): {stderr}"
                    )
                    if exit_code != 0
                    else None,
                )
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
        return False

    def cleanup(self):
        """Clean up resources when service is stopped."""
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

        if self._poll_timer_id:
            GLib.source_remove(self._poll_timer_id)
            self._poll_timer_id = None

        if self._file_monitor:
            self._file_monitor.cancel()
            self._file_monitor = None
