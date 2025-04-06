
from sys import exception
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf, Pango
from fabric.widgets.box import Box 
from fabric.widgets.label import Label 
from fabric.widgets.scrolledwindow import ScrolledWindow

import cairo

import re
import os

from enum import Enum
import subprocess

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import modules.icons as icons

import json


from urllib.parse import urlparse

from loguru import logger

SAVE_FILE = os.path.expanduser("~/.pins.json")

    
class DefaultApps(Enum):
    TERMINAL = "ghostty"
    FILE_BROWSER = "nemo"
    BROWSER = "firefox"
    PDF = "okular"
    IMAGE = "okular"
    TEXT = "nvim"
    OTHER = "xdg-open"

URL_REGEX = re.compile(r"https?://\S+")


def open_file(filepath):
    try:
        subprocess.Popen(["xdg-open", filepath])
    except Exception as e:
        logger.error("Error opening file:", e)

def reveal_file(filepath):
    try:
        subprocess.Popen([DefaultApps.FILE_BROWSER.value, filepath])
    except Exception as e:
        logger.error("Error opening file:", e)
        
def createSurfaceFromWidget(widget: Gtk.Widget) -> cairo.ImageSurface:
    alloc = widget.get_allocation()
    surface = cairo.ImageSurface(cairo.Format.ARGB32, alloc.width, alloc.height)
    cr = cairo.Context(surface)
    cr.set_source_rgba(1, 1, 1, 0)  # transparent background
    cr.rectangle(0, 0, alloc.width, alloc.height)
    cr.fill()
    widget.draw(cr)
    return surface

class Cell(Gtk.EventBox):
    def __init__(self, parent_app: Gtk.Widget = None, icon_size: int = 40, **kwargs):
        super().__init__(**kwargs)

        self._icon_size = icon_size 
        
        # serializable params
        self._content = None
        self._content_type = None
        self._alias = None
        
        self._parent_app = parent_app

        # Box to display information about contents
        self.box = Gtk.Box(name="pin-cell-box", orientation=Gtk.Orientation.VERTICAL)
        self.box.set_spacing(2)
        self.add(self.box)

        targets = [
            Gtk.TargetEntry.new("text/uri-list", 0, 0),  # for files/folders
            Gtk.TargetEntry.new(
                "text/plain", 0, 1
            ),  # This should handle URLs or plaintext
        ]

        # handle receiving data
        self.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
        self.connect("drag-data-received", self.on_drag_data_received)
        
        # drag this widget, send data
        self.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets, Gdk.DragAction.COPY)
        self.connect("drag-data-get", self.on_drag_data_get)
        
        self.connect("button-press-event", self.on_button_press)
        self.connect("drag-begin", self.on_drag_begin)
        
        self.debuglabel = Gtk.Label(label="hi")

        self.box.add(self.debuglabel)
        
        self.update_display()

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        if not (self._content is None and data.get_length() >= 0):
            return
        
        uris = data.get_uris()
        text = data.get_text()
        
        if uris:
            uri = uris[0]
            try:
                match URL_REGEX.match(uri) is None:
                    case True: # probably a file
                        filepath, _ = GLib.filename_from_uri(uris[0])
                        self._content = filepath
                        self._content_type = "file"
                        self._alias = os.path.basename(self._content)
                        self.update_display()
                        
                    case False: # or a http uri
                        self._content = uri 
                        self._content_type = "url"
                        self._alias = urlparse(self._content).netloc
                        self.update_display()
            except Exception as e:
                logger.info("Error getting file from uri: {}".format(str(e)))
                
        else:
            if not text:
                return
            if URL_REGEX.match(text):
                self._content = text
                self._content_type = "url"
                self._alias = urlparse(self._content).netloc
                self.update_display()
                
    def update_display(self):
        for child in self.box.get_children():
            self.box.remove(child)
            
        if self._content is None: # Default init
            label = Label(name="pin-add", markup=icons.paperclip)
            self.box.pack_start(label, True, True, 0)
            
        match self._content_type:
            case "file":
                widget = self.get_file_preview(self._content)
                self.box.pack_start(widget, True, True, 0)
                label = Gtk.Label(name="pin-file", label=self._alias)
                label.set_justify(Gtk.Justification.CENTER)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                self.box.pack_start(label, False, False, 0)
            case "url": 
                widget = self.get_url_preview()
                self.box.pack_start(widget, True, True, 0)
                label = Gtk.Label(name="pin-file", label=self._alias)
                label.set_justify(Gtk.Justification.CENTER)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                self.box.pack_start(label, False, False, 0)
                
        self.box.show_all()
        if self._parent_app is not None:
            if not self._parent_app.loading_state:
                self._parent_app.save_state()
            
    def on_button_press(self, widget, event):
        if self._content is None:
            if event.button == 1:
                self.select_file()
            elif event.button == 2:
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                text = clipboard.wait_for_text()
                if text:
                    self._content = text
                    self._content_type = 'text'
                    self.update_display()
        else:
            if self._content_type == 'url' or self._content_type == 'file':
                match event.button:
                    case 1:
                        if event.type == Gdk.EventType._2BUTTON_PRESS:
                            open_file(self._content) # xdg-open also works for urls
                    case 3:
                        self.show_context_menu(event)
            elif self._content_type == 'text':
                match event.button:
                    case 1:
                        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                        clipboard.set_text(self._content, -1)
                    case 3:
                        self.show_context_menu(event)
                    
        return True
        
    def on_drag_begin(self, widget, context):
        surface = createSurfaceFromWidget(self)
        Gtk.drag_set_icon_surface(context, surface)
        
    def on_drag_data_get(self, widget, drag_context, data, info, time):
        if self._content is None:
            return  # nothing to drag
        logger.info(str(info) + " sending")
        
        
        # Handle based on what the destination is asking for (info parameter)
        if info == 0:  # URI list requested
            if self._content_type == "file":
                uri = GLib.filename_to_uri(self._content)
                data.set_uris([uri])
            elif self._content_type == "url":
                # send link as URI, check for 'http' in on_drag_data_rec
                data.set_uris([self._content])
        elif info == 1: 
            # Both files and URLs can be represented as text
            if self._content_type == "file":
                data.set_text(self._content, -1)
            elif self._content_type == "url":
                data.set_text(self._content, -1)

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
                pixbuf = icon_theme.load_icon("folder", self._icon_size, 0)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception as e:
                logger.info("Error loading folder icon " + str(e))
                return Gtk.Image.new_from_icon_name("default-folder", Gtk.IconSize.DIALOG)
        
        if content_type and content_type.startswith("image/"):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    filepath, width=self._icon_size, height=self._icon_size, preserve_aspect_ratio=True)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception as e:
                logger.info("Error loading image preview:", e)
        
        elif content_type and content_type.startswith("video/"):
            try:
                pixbuf = icon_theme.load_icon("video-x-generic", self._icon_size, 0)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                logger.info("Error loading video icon")
                return Gtk.Image.new_from_icon_name("video-x-generic", Gtk.IconSize.MENU)
        else:
            icon_name = "text-x-generic"
            if content_type:
                themed_icon = Gio.content_type_get_icon(content_type)
                if hasattr(themed_icon, 'get_names'):
                    names = themed_icon.get_names()
                    if names:
                        icon_name = names[0]
            try:
                pixbuf = icon_theme.load_icon(icon_name, self._icon_size, 0)
                return Gtk.Image.new_from_pixbuf(pixbuf)
            except Exception:
                logger.info("Error loading icon", icon_name)
                return Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)

    def get_url_preview(self):
        icon_theme = Gtk.IconTheme.get_default()

        try:
            pixbuf = icon_theme.load_icon("internet-web-browser", self._icon_size, 0)
            return Gtk.Image.new_from_pixbuf(pixbuf)
        except Exception as e:
            logger.info("Error loading folder icon " + str(e))
            return Gtk.Image.new_from_icon_name("default-folder", Gtk.IconSize.DIALOG)
    
    def clear_cell(self, button=None):
        self._content = None
        self._content_type = None
        self.update_display()
        
    def rename_cell(self, button=None):
        new_alias, ok_clicked = self.show_rename_prompt()
        if new_alias == "":
            match self._content_type:
                case "url":
                    new_alias = urlparse(self._content).netloc 
                case "file":
                    new_alias = os.path.basename(self._content)
                    
        if ok_clicked:
            self._alias = new_alias
            self.update_display()
        
    def show_rename_prompt(self) -> tuple[str, bool]:
        dialog = Gtk.Dialog(title="rename", parent=self.get_toplevel(), flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        
        content_area = dialog.get_content_area()
        label = Gtk.Label(label="enter new alias:")
        entry = Gtk.Entry()
        
        entry.connect("activate", lambda e: dialog.response(Gtk.ResponseType.OK))
        
        content_area.pack_start(entry, True, True, 0)
        content_area.pack_start(label, True, True, 0)
        
        content_area.show_all()
        
        response = dialog.run()
        text = entry.get_text()
        dialog.destroy()
        
        return (text, response == Gtk.ResponseType.OK)
        
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
            self._content = filepath
            self._content_type = 'file'
            self._alias = os.path.basename(self._content)
            self.update_display()
        dialog.destroy()
        
    def show_context_menu(self, event):
        menu = Gtk.Menu()
        reveal_item = Gtk.MenuItem(label="reveal in filebrowser")
        reveal_item.connect("activate", lambda *_: reveal_file(self._content))

        if self._content_type != "file":
            reveal_item.set_sensitive(False)

        menu.append(reveal_item)

        rename_item = Gtk.MenuItem(label="rename")
        rename_item.connect("activate", self.rename_cell)
        menu.append(rename_item)
        
        delete_item = Gtk.MenuItem(label="delete")
        delete_item.connect("activate", self.clear_cell)
        menu.append(delete_item)
        
        menu.show_all()
        menu.popup_at_pointer(event)


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app

    def on_any_event(self, event):
        if event.is_directory:
            return

        for cell in self.app.cells:
            if cell._content_type == 'file' and cell._content:
                try:
                    cell_real = os.path.realpath(cell._content)
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
                cell._content = event.dest_path
                cell.update_display()
                self.app.save_state()
                self.app.add_monitor_for_path(os.path.dirname(event.dest_path))


class Pins(Gtk.Box):
    def __init__(self, rows: int = 4, columns: int = 5, icon_size: int = 30, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

        self._rows = rows 
        self._columns = columns 
        self._icon_size = icon_size

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
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.get_style_context().add_class("scrollable")
        scrolled_window.add(grid)
        self.pack_start(scrolled_window, True, True, 0)

        # generate grid
        for row in range(self._rows):
            for col in range(self._columns):
                cell = Cell(self, icon_size=self._icon_size, name="pin-cell")
                self.cells.append(cell)
                grid.attach(cell, col, row, 1, 1)

        self.load_state()
        self.loading_state = False
        self.start_file_monitoring()

        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.connect("drag-data-received", self.on_drag_data_received)

    def start_file_monitoring(self):
        for cell in self.cells:
            if cell._content_type == 'file' and cell._content:
                dir_path = os.path.dirname(cell._content)
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
                'content_type': cell._content_type,
                'content': cell._content,
                'alias': cell._alias,
            })
        try:
            with open(SAVE_FILE, 'w+') as f:
                json.dump(state, f)
        except Exception as e:
            logger.info("Error saving state:", e)

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
                    alias = cell_data.get('alias')
                    self.cells[i]._content = content
                    self.cells[i]._content_type = content_type
                    self.cells[i]._alias = alias
                    self.cells[i].update_display()
        except Exception as e:
            logger.info("Error loading state:", e)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        if data.get_length() >= 0:
            uris = data.get_uris()
            for uri in uris:
                try:
                    filepath, _ = GLib.filename_from_uri(uri)
                    for cell in self.cells:
                        if cell._content is None:
                            cell._content = filepath
                            cell._content_type = 'file'
                            cell.update_display()
                            break
                except Exception as e:
                    logger.info("Error getting file from URI:", e)
        drag_context.finish(True, False, time)

    def stop_monitoring(self):
        self.observer.stop()
        self.observer.join()
        
if __name__ == "__main__":
    win = Gtk.Window()
    box = Gtk.Box()
    box.pack_start(Pins(icon_size=80), *([1]*3)) 
    win.add(box)
    win.show_all()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
