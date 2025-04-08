import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio
import os
import subprocess
import json
import cairo
import re
import urllib.request
import urllib.parse
import tempfile
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow

import modules.icons as icons

SAVE_FILE = os.path.expanduser("~/.pins.json")

def createSurfaceFromWidget(widget: Gtk.Widget) -> cairo.ImageSurface:
    alloc = widget.get_allocation()
    surface = cairo.ImageSurface(cairo.Format.ARGB32, alloc.width, alloc.height)
    cr = cairo.Context(surface)
    cr.set_source_rgba(1, 1, 1, 0)  # transparent background
    cr.rectangle(0, 0, alloc.width, alloc.height)
    cr.fill()
    widget.draw(cr)
    return surface

def open_file(filepath):
    try:
        subprocess.Popen(["xdg-open", filepath])
    except Exception as e:
        print("Error opening file:", e)

def open_url(url):
    try:
        subprocess.Popen(["xdg-open", url])
    except Exception as e:
        print("Error opening URL:", e)

def is_url(text):
    # Simple URL validation pattern
    url_pattern = re.compile(
        r'^(https?|ftp)://'  # http://, https://, ftp://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(text))

def get_favicon_url(url):
    """Extract the base domain from a URL and construct a favicon URL."""
    parsed_url = urllib.parse.urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    return f"{base_url}/favicon.ico"

def download_favicon(url, callback):
    """Download a favicon asynchronously and call the callback with the result."""
    favicon_url = get_favicon_url(url)
    
    def do_download():
        temp_file = None
        try:
            # Create a temporary file to store the favicon
            temp_fd, temp_path = tempfile.mkstemp(suffix='.ico')
            os.close(temp_fd)
            
            # Download the favicon
            urllib.request.urlretrieve(favicon_url, temp_path)
            
            # If successful, pass the path to the callback
            GLib.idle_add(callback, temp_path)
        except Exception as e:
            print(f"Error downloading favicon: {e}")
            # If there's an error, call the callback with None
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            GLib.idle_add(callback, None)
        return False  # Don't repeat
    
    # Schedule the download operation with GLib instead of threading
    GLib.idle_add(do_download)

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_any_event(self, event):
        if event.is_directory:
            return

        for cell in self.app.cells:
            if cell.content_type == 'file' and cell.content:
                try:
                    cell_real = os.path.realpath(cell.content)
                    src_real = os.path.realpath(event.src_path)
                    dest_real = os.path.realpath(getattr(event, 'dest_path', ''))
                    if cell_real == src_real or (dest_real and cell_real == dest_real):
                        GLib.idle_add(self.handle_file_event, cell, event)
                except Exception:
                    pass

    def handle_file_event(self, cell, event):
        if event.event_type == 'deleted':
            cell.clear_cell()
            self.app.save_state()
        elif event.event_type == 'moved':
            if hasattr(event, 'dest_path') and os.path.exists(event.dest_path):
                cell.content = event.dest_path
                cell.update_display()
                self.app.save_state()
                self.app.add_monitor_for_path(os.path.dirname(event.dest_path))

class Cell(Gtk.EventBox):
    def __init__(self, app, content=None, content_type=None):
        super().__init__(name="pin-cell")
        self.app = app
        self.content = content
        self.content_type = content_type
        self.box = Box(name="pin-cell-box", orientation="v", spacing=4)
        self.add(self.box)
        
        # Store favicon path for cleanup
        self.favicon_temp_path = None

        target_dest = Gtk.TargetEntry.new("text/uri-list", 0, 0)
        self.drag_dest_set(Gtk.DestDefaults.ALL, [target_dest], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self.on_drag_data_received)

        targets = [
            Gtk.TargetEntry.new("text/uri-list", 0, 0),
            Gtk.TargetEntry.new("text/plain", 0, 1)
        ]
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.COPY)
        self.connect("drag-data-get", self.on_drag_data_get)

        self.connect("button-press-event", self.on_button_press)

        self.connect("drag-begin", self.on_drag_begin)

        self.update_display()

    def update_display(self):
        # Clean up any previous favicon temp file
        if self.favicon_temp_path and os.path.exists(self.favicon_temp_path):
            try:
                os.remove(self.favicon_temp_path)
                self.favicon_temp_path = None
            except Exception as e:
                print(f"Error removing temp favicon: {e}")
        
        for child in self.box.get_children():
            self.box.remove(child)
        
        if self.content is None:
            label = Label(name="pin-add", markup=icons.paperclip)
            self.box.pack_start(label, True, True, 0)
        else:
            if self.content_type == 'file':
                widget = self.get_file_preview(self.content)
                self.box.pack_start(widget, True, True, 0)
                label = Label(name="pin-file", label=os.path.basename(self.content), justification="center", ellipsization="middle")
                self.box.pack_start(label, False, False, 0)
            elif self.content_type == 'text':
                if is_url(self.content):
                    # Create container for icon first
                    icon_container = Box(name="pin-icon-container", orientation="v")
                    self.box.pack_start(icon_container, True, True, 0)
                    
                    # Initially use the world icon in the container
                    url_icon = Label(name="pin-url-icon", markup=icons.world)
                    icon_container.pack_start(url_icon, True, True, 0)
                    
                    # Add the domain name label below the icon
                    domain = re.sub(r'^https?://', '', self.content)
                    domain = domain.split('/')[0]
                    label = Label(name="pin-url", label=domain, justification="center", ellipsization="end")
                    self.box.pack_start(label, False, False, 0)
                    
                    # Try to fetch the favicon asynchronously
                    download_favicon(
                        self.content, 
                        lambda path: self.update_favicon(icon_container, url_icon, path)
                    )
                else:
                    # Regular text display
                    label = Label(name="pin-text", label=self.content.split('\n')[0], justification="center", ellipsization="end", line_wrap="word-char")
                    self.box.pack_start(label, True, True, 0)
        self.box.show_all()
        if not self.app.loading_state:
            self.app.save_state()
    
    def update_favicon(self, container, icon_widget, favicon_path):
        """Update the icon with the downloaded favicon or keep the default."""
        if not favicon_path or not os.path.exists(favicon_path):
            # Keep the default icon if favicon couldn't be downloaded
            return
        
        try:
            # Store the path for later cleanup
            self.favicon_temp_path = favicon_path
            
            # Create a pixbuf from the favicon file
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                favicon_path, width=48, height=48, preserve_aspect_ratio=True)
            
            # Remove the old icon widget from the container
            container.remove(icon_widget)
            
            # Create and add a new image widget with the favicon to the container
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            img.set_name("pin-favicon")
            container.pack_start(img, True, True, 0)
            
            # Make sure it's visible
            container.show_all()
        except Exception as e:
            print(f"Error setting favicon: {e}")
            # If anything fails, the original icon_widget is still in place

    def get_file_preview(self, filepath):
        try:
            file = Gio.File.new_for_path(filepath)
            info = file.query_info("standard::content-type", Gio.FileQueryInfoFlags.NONE, None)
            content_type = info.get_content_type()
        except Exception:
            content_type = None

        icon_theme = Gtk.IconTheme.get_default()

        if content_type == "inode/directory":
            try:
                pixbuf = icon_theme.load_icon("default-folder", 80, 0)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                print("Error loading folder icon")
                return Gtk.Image.new_from_icon_name("default-folder", Gtk.IconSize.DIALOG)
        
        if content_type and content_type.startswith("image/"):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filepath, width=80, height=80, preserve_aspect_ratio=True)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception as e:
                print("Error loading image preview:", e)
        
        elif content_type and content_type.startswith("video/"):
            try:
                pixbuf = icon_theme.load_icon("video-x-generic", 80, 0)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                print("Error loading video icon")
                return Gtk.Image.new_from_icon_name("video-x-generic", Gtk.IconSize.DIALOG)
        else:
            icon_name = "text-x-generic"
            if content_type:
                themed_icon = Gio.content_type_get_icon(content_type)
                if hasattr(themed_icon, 'get_names'):
                    names = themed_icon.get_names()
                    if names:
                        icon_name = names[0]
            try:
                pixbuf = icon_theme.load_icon(icon_name, 80, 0)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                print("Error loading icon", icon_name)
                return Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        if self.content is None and data.get_length() >= 0:
            uris = data.get_uris()
            if uris:
                try:
                    filepath, _ = GLib.filename_from_uri(uris[0])
                    self.content = filepath
                    self.content_type = 'file'
                    self.update_display()
                except Exception as e:
                    print("Error getting file from URI:", e)
        drag_context.finish(True, False, time)

    def on_drag_data_get(self, widget, drag_context, data, info, time):
        if self.content is None:
            return
        if info == 0 and self.content_type == 'file':
            uri = GLib.filename_to_uri(self.content)
            data.set_uris([uri])
        elif info == 1 and self.content_type == 'text':
            data.set_text(self.content, -1)

    def on_drag_begin(self, widget, context):
        # Only show a preview when dragging files.
        if self.content_type == 'file':
            surface = createSurfaceFromWidget(self)
            Gtk.drag_set_icon_surface(context, surface)

    def on_button_press(self, widget, event):
        if self.content is None:
            if event.button == 1:
                self.select_file()
            elif event.button == 2:
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                text = clipboard.wait_for_text()
                if text:
                    self.content = text
                    self.content_type = 'text'
                    self.update_display()
        else:
            if self.content_type == 'file':
                if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                    open_file(self.content)
                elif event.button == 3:
                    self.clear_cell()
            elif self.content_type == 'text':
                if event.button == 1:
                    # Add special handling for URLs
                    if is_url(self.content):
                        # Put URL in clipboard
                        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                        clipboard.set_text(self.content, -1)
                        
                        # If CTRL is not pressed, open the URL
                        if not (event.state & Gdk.ModifierType.CONTROL_MASK):
                            open_url(self.content)
                    else:
                        # Regular text behavior - just copy to clipboard
                        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                        clipboard.set_text(self.content, -1)
                elif event.button == 3:
                    self.clear_cell()
        return True

    def select_file(self):
        dialog = Gtk.FileChooserDialog(
            title="Select File",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            self.content = filepath
            self.content_type = 'file'
            self.update_display()
        dialog.destroy()

    def clear_cell(self):
        # Clean up favicon temp file if it exists
        if self.favicon_temp_path and os.path.exists(self.favicon_temp_path):
            try:
                os.remove(self.favicon_temp_path)
                self.favicon_temp_path = None
            except Exception as e:
                print(f"Error removing temp favicon: {e}")
        
        self.content = None
        self.content_type = None
        self.update_display()

class Pins(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.loading_state = True
        self.monitored_paths = set()
        self.observer = Observer()
        self.event_handler = FileChangeHandler(self)

        self.cells = []

        # Create a grid with 5 rows and 5 columns
        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        # Replace this:
        # scrolled_window = Gtk.ScrolledWindow()
        # scrolled_window.set_name("scrolled-window")
        # scrolled_window.add(grid)
        # self.pack_start(scrolled_window, True, True, 0)

        # With the Fabric ScrolledWindow:
        scrolled_window = ScrolledWindow(child=grid, name="scrolled-window")
        self.pack_start(scrolled_window, True, True, 0)

        # Create 30 cells (5x6)
        for row in range(6):
            for col in range(5):
                cell = Cell(self)
                self.cells.append(cell)
                grid.attach(cell, col, row, 1, 1)

        self.load_state()
        self.loading_state = False
        self.start_file_monitoring()

        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self.on_drag_data_received)

    def start_file_monitoring(self):
        for cell in self.cells:
            if cell.content_type == 'file' and cell.content:
                dir_path = os.path.dirname(cell.content)
                if os.path.exists(dir_path) and dir_path not in self.monitored_paths:
                    self.observer.schedule(self.event_handler, dir_path, recursive=False)
                    self.monitored_paths.add(dir_path)
        self.observer.start()

    def add_monitor_for_path(self, path):
        if path not in self.monitored_paths and os.path.exists(path):
            self.observer.schedule(self.event_handler, path, recursive=False)
            self.monitored_paths.add(path)

    def save_state(self):
        state = []
        for cell in self.cells:
            state.append({
                'content_type': cell.content_type,
                'content': cell.content
            })
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print("Error saving state:", e)

    def load_state(self):
        if not os.path.exists(SAVE_FILE):
            return
        try:
            with open(SAVE_FILE, 'r') as f:
                state = json.load(f)
            for i, cell_data in enumerate(state):
                if i < len(self.cells):
                    content = cell_data.get('content')
                    content_type = cell_data.get('content_type')
                    self.cells[i].content = content
                    self.cells[i].content_type = content_type
                    self.cells[i].update_display()
        except Exception as e:
            print("Error loading state:", e)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        if data.get_length() >= 0:
            uris = data.get_uris()
            for uri in uris:
                try:
                    filepath, _ = GLib.filename_from_uri(uri)
                    for cell in self.cells:
                        if cell.content is None:
                            cell.content = filepath
                            cell.content_type = 'file'
                            cell.update_display()
                            break
                except Exception as e:
                    print("Error getting file from URI:", e)
        drag_context.finish(True, False, time)

    def stop_monitoring(self):
        # Clean up any temp favicon files
        for cell in self.cells:
            if hasattr(cell, 'favicon_temp_path') and cell.favicon_temp_path and os.path.exists(cell.favicon_temp_path):
                try:
                    os.remove(cell.favicon_temp_path)
                except Exception:
                    pass
                    
        self.observer.stop()
        self.observer.join()
