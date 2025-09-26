import configparser
import ctypes
import os
import re
import signal
import struct
import subprocess
from math import pi

from fabric.utils.helpers import get_relative_path
from fabric.widgets.overlay import Overlay
from gi.repository import Gdk, GLib, Gtk
from loguru import logger


def get_bars(file_path):
    config = configparser.ConfigParser()
    config.read(file_path)
    return int(config['general']['bars'])

CAVA_CONFIG = get_relative_path("../config/cavalcade/cava.ini")

bars = get_bars(CAVA_CONFIG)

def set_death_signal():
    """
    Set the death signal of the child process to SIGTERM so that if the parent
    process is killed, the child (cava) is automatically terminated.
    """
    libc = ctypes.CDLL("libc.so.6")
    PR_SET_PDEATHSIG = 1
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM)

class Cava:
    """
    CAVA wrapper.
    Launch cava process with certain settings and read output.
    """
    NONE = 0
    RUNNING = 1
    RESTARTING = 2
    CLOSING = 3

    def data_handler(self, *a, **kw):
        """Call all registered handlers with the provided arguments."""
        for h in self._handlers:
            h(*a, **kw)

    def register_handler(self, handler):
        self._handlers.append(handler)

    def __init__(self):
        self.bars = bars
        self.path = "/tmp/cava.fifo"

        self.cava_config_file = CAVA_CONFIG
        self._handlers = []
        self._started = False
        self.command = ["cava", "-p", self.cava_config_file]
        self.state = self.NONE
        self.process = None

        self.env = dict(os.environ)
        self.env["LC_ALL"] = "en_US.UTF-8"  # not sure if it's necessary

        is_16bit = True
        self.byte_type, self.byte_size, self.byte_norm = ("H", 2, 65535) if is_16bit else ("B", 1, 255)

        if not os.path.exists(self.path):
            os.mkfifo(self.path)

        self.fifo_fd = None
        self.fifo_dummy_fd = None
        self.io_watch_id = None

    def _run_process(self):
        try:
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=self.env,
                preexec_fn=set_death_signal  # Ensure cava gets killed when the parent dies.
            )
            self.state = self.RUNNING
        except Exception:
            logger.exception("Fail to launch cava")

    def _start_io_reader(self):
        # Open FIFO in non-blocking mode for reading
        self.fifo_fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)
        # Open dummy write end to prevent getting an EOF on our FIFO
        self.fifo_dummy_fd = os.open(self.path, os.O_WRONLY | os.O_NONBLOCK)
        self.io_watch_id = GLib.io_add_watch(self.fifo_fd, GLib.IO_IN, self._io_callback)

    def _io_callback(self, source, condition):
        chunk = self.byte_size * self.bars  # number of bytes for given format
        try:
            if self.fifo_fd is None:
                return False
                
            data = os.read(self.fifo_fd, chunk)
        except OSError as e:
            if e.errno == 11:  # EAGAIN - would block, normal for non-blocking
                return True
            elif e.errno == 9:  # EBADF - bad file descriptor
                GLib.idle_add(self.restart)
                return False
            else:
                return False
        except Exception:
            return False

        # When no data is read, do not remove the IO watch immediately.
        if len(data) < chunk:
            if len(data) == 0:
                # No data available, continue watching
                return True
            else:
                return True

        try:
            fmt = self.byte_type * self.bars  # format string for struct.unpack
            sample = [i / self.byte_norm for i in struct.unpack(fmt, data)]
            GLib.idle_add(self.data_handler, sample)
        except (struct.error, Exception):
            return True
            
        return True

    def _on_stop(self):
        if self.state == self.RESTARTING:
            self.start()
        elif self.state == self.RUNNING:
            self.state = self.NONE

    def start(self):
        """Launch cava"""
        if self._started:
            return
        self._start_io_reader()
        self._run_process()
        self._started = True

    def restart(self):
        """Restart cava process"""
        if self.state == self.RUNNING:
            self.state = self.RESTARTING
            if self.process and self.process.poll() is None:
                self.process.kill()
        elif self.state == self.NONE:
            self.start()

    def close(self):
        """Stop cava process"""
        self.state = self.CLOSING
        
        # Stop IO watch first
        if self.io_watch_id:
            GLib.source_remove(self.io_watch_id)
            self.io_watch_id = None
            
        # Close file descriptors safely
        if self.fifo_fd is not None:
            try:
                os.close(self.fifo_fd)
            except OSError:
                pass
            finally:
                self.fifo_fd = None
                
        if self.fifo_dummy_fd is not None:
            try:
                os.close(self.fifo_dummy_fd)
            except OSError:
                pass
            finally:
                self.fifo_dummy_fd = None
        
        # Kill process if still running
        if self.process and self.process.poll() is None:
            try:
                self.process.kill()
                self.process.wait(timeout=2.0)  # Wait up to 2 seconds
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception:
                pass
        
        # Remove FIFO file
        if os.path.exists(self.path):
            try:
                os.remove(self.path)
            except OSError:
                pass

class AttributeDict(dict):
    """Dictionary with keys as attributes. Does nothing but easy reading"""
    def __getattr__(self, attr):
        return self.get(attr, 3)

    def __setattr__(self, attr, value):
        self[attr] = value

class Spectrum:
    """Spectrum drawing"""
    def __init__(self):
        self.silence_value = 0
        self.audio_sample = []
        self.color = None
        self._cached_color = None
        self._color_file_mtime = 0

        self.area = Gtk.DrawingArea()
        self.area.connect("draw", self.redraw)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        self.sizes = AttributeDict()
        self.sizes.area = AttributeDict()
        self.sizes.bar = AttributeDict()

        self.silence = 10
        self.max_height = 12

        self.area.connect("configure-event", self.size_update)
        self.color_update()

    def is_silence(self, value):
        """Check if volume level critically low during last iterations"""
        self.silence_value = 0 if value > 0 else self.silence_value + 1
        return self.silence_value > self.silence

    def update(self, data):
        """Audio data processing"""
        self.color_update_cached()
        self.audio_sample = data
        if not self.is_silence(self.audio_sample[0]):
            self.area.queue_draw()
        elif self.silence_value == (self.silence + 1):
            self.audio_sample = [0] * self.sizes.number
            self.area.queue_draw()

    def redraw(self, widget, cr):
        """Draw spectrum graph"""
        cr.set_source_rgba(*self.color)
        dx = 3

        center_y = self.sizes.area.height / 2  # center vertical of the drawing area
        for i, value in enumerate(self.audio_sample):
            width = self.sizes.area.width / self.sizes.number - self.sizes.padding
            radius = width / 2
            height = max(self.sizes.bar.height * min(value, 1), self.sizes.zero) / 2
            if height == self.sizes.zero / 2 + 1:
                height *= 0.5

            height = min(height, self.max_height)

            # Draw rectangle and arcs for rounded ends
            cr.rectangle(dx, center_y - height, width, height * 2)
            cr.arc(dx + radius, center_y - height, radius, 0, 2 * pi)
            cr.arc(dx + radius, center_y + height, radius, 0, 2 * pi)

            cr.close_path()
            dx += width + self.sizes.padding
        cr.fill()

    def size_update(self, *args):
        """Update drawing geometry"""
        self.sizes.number = bars
        self.sizes.padding = 100 / bars
        self.sizes.zero = 0

        self.sizes.area.width = self.area.get_allocated_width()
        self.sizes.area.height = self.area.get_allocated_height() - 2

        tw = self.sizes.area.width - self.sizes.padding * (self.sizes.number - 1)
        self.sizes.bar.width = max(int(tw / self.sizes.number), 1)
        self.sizes.bar.height = self.sizes.area.height

    def color_update_cached(self):
        """Set drawing color with caching to avoid file reads on every frame"""
        color_file = get_relative_path("../styles/colors.css")
        try:
            # Check if file has been modified
            current_mtime = os.path.getmtime(color_file)
            if current_mtime != self._color_file_mtime or self._cached_color is None:
                self._color_file_mtime = current_mtime
                
                color = "#a5c8ff"  # default value
                with open(color_file, "r") as f:
                    content = f.read()
                    m = re.search(r"--primary:\s*(#[0-9a-fA-F]{6})", content)
                    if m:
                        color = m.group(1)
                
                red = int(color[1:3], 16) / 255
                green = int(color[3:5], 16) / 255
                blue = int(color[5:7], 16) / 255
                self._cached_color = Gdk.RGBA(red=red, green=green, blue=blue, alpha=1.0)
                
            self.color = self._cached_color
        except Exception:
            if self._cached_color is None:
                # Fallback to default color
                self._cached_color = Gdk.RGBA(red=0.647, green=0.784, blue=1.0, alpha=1.0)
                self.color = self._cached_color

    def color_update(self):
        """Set drawing color according to current settings by reading primary color from CSS"""
        color = "#a5c8ff"  # default value
        try:
            with open(get_relative_path("../styles/colors.css"), "r") as f:
                content = f.read()
                m = re.search(r"--primary:\s*(#[0-9a-fA-F]{6})", content)
                if m:
                    color = m.group(1)
        except Exception:
            pass
        red = int(color[1:3], 16) / 255
        green = int(color[3:5], 16) / 255
        blue = int(color[5:7], 16) / 255
        self.color = Gdk.RGBA(red=red, green=green, blue=blue, alpha=1.0)


_instances = {}


def getCava() -> Cava:
    if "cava" not in _instances:
        _instances["cava"] = Cava()
    return _instances["cava"]


class SpectrumRender:
    def __init__(self, mode=None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

        self.draw = Spectrum()
        self.cava = getCava()
        self.cava.register_handler(self.draw.update)

        self.cava.start()

    def get_spectrum_box(self):
        # Get the spectrum box
        box = Overlay(name="cavalcade", h_align='center', v_align='center')
        box.set_size_request(180, 40)
        box.add_overlay(self.draw.area)
        return box
