import os
import hashlib
from gi.repository import GdkPixbuf, Gtk, GLib, Gio  # Added Gio for file monitoring
from fabric.widgets.box import Box
from fabric.widgets.entry import Entry
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.label import Label
from fabric.utils.helpers import exec_shell_command_async
import modules.icons as icons
import modules.data as data
from PIL import Image
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

class WallpaperSelector(Box):
    CACHE_DIR = os.path.expanduser("~/.cache/ax-shell/wallpapers")

    def __init__(self, **kwargs):
        super().__init__(name="wallpapers", spacing=4, orientation="v", **kwargs)
        self.notch = kwargs["notch"]
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self.files = sorted([f for f in os.listdir(data.WALLPAPERS_DIR) if self._is_image(f)])
        self.thumbnails = []
        self.thumbnail_queue = []
        self.executor = ThreadPoolExecutor(max_workers=4)  # Shared executor

        # Initialize UI components
        self.viewport = Gtk.IconView()
        self.viewport.set_model(Gtk.ListStore(GdkPixbuf.Pixbuf, str))
        self.viewport.set_pixbuf_column(0)
        self.viewport.set_text_column(1)
        self.viewport.set_item_width(0)
        self.viewport.connect("item-activated", self.on_wallpaper_selected)

        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            h_expand=True,
            v_expand=True,
            child=self.viewport,
        )

        self.search_entry = Entry(
            name="search-entry",
            placeholder="Search Wallpapers...",
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
        )
        self.search_entry.props.xalign = 0.5

        self.schemes = {
            "scheme-tonal-spot": "Tonal Spot",
            "scheme-content": "Content",
            "scheme-expressive": "Expressive",
            "scheme-fidelity": "Fidelity",
            "scheme-fruit-salad": "Fruit Salad",
            "scheme-monochrome": "Monochrome",
            "scheme-neutral": "Neutral",
            "scheme-rainbow": "Rainbow",
        }

        self.scheme_dropdown = Gtk.ComboBoxText()
        self.scheme_dropdown.set_name("scheme-dropdown")
        self.scheme_dropdown.set_tooltip_text("Select color scheme")
        for key, display_name in self.schemes.items():
            self.scheme_dropdown.append(key, display_name)
        self.scheme_dropdown.set_active_id("scheme-monochrome")
        self.scheme_dropdown.connect("changed", self.on_scheme_changed)

        self.dropdown_box = Box(
            name="dropdown-box",
            spacing=10,
            orientation="h",
            children=[
                self.scheme_dropdown,
                Label(name="dropdown-label", markup=icons.chevron_down),
            ],
        )

        self.header_box = Box(
            name="header-box",
            spacing=10,
            orientation="h",
            children=[
                self.search_entry,
                self.dropdown_box,
                Button(
                    name="close-button",
                    child=Label(name="close-label", markup=icons.cancel),
                    tooltip_text="Close Selector",
                    on_clicked=lambda *_: self.close_selector(),
                ),
            ],
        )

        self.add(self.header_box)
        self.add(self.scrolled_window)
        self._start_thumbnail_thread()
        self.setup_file_monitor()  # Initialize file monitoring
        self.show_all()

    def setup_file_monitor(self):
        gfile = Gio.File.new_for_path(data.WALLPAPERS_DIR)
        self.file_monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
        self.file_monitor.connect("changed", self.on_directory_changed)

    def on_directory_changed(self, monitor, file, other_file, event_type):
        file_name = file.get_basename()
        if event_type == Gio.FileMonitorEvent.DELETED:
            if file_name in self.files:
                self.files.remove(file_name)
                cache_path = self._get_cache_path(file_name)
                if os.path.exists(cache_path):
                    try:
                        os.remove(cache_path)
                    except Exception as e:
                        print(f"Error deleting cache {cache_path}: {e}")
                self.thumbnails = [(p, n) for p, n in self.thumbnails if n != file_name]
                GLib.idle_add(self.arrange_viewport, self.search_entry.get_text())
        elif event_type == Gio.FileMonitorEvent.CREATED:
            if self._is_image(file_name) and file_name not in self.files:
                self.files.append(file_name)
                self.files.sort()
                self.executor.submit(self._process_file, file_name)
        elif event_type == Gio.FileMonitorEvent.CHANGED:
            if self._is_image(file_name) and file_name in self.files:
                cache_path = self._get_cache_path(file_name)
                if os.path.exists(cache_path):
                    try:
                        os.remove(cache_path)
                    except Exception as e:
                        print(f"Error deleting cache for changed file {file_name}: {e}")
                self.executor.submit(self._process_file, file_name)

    def close_selector(self):
        self.notch.close_notch()

    def arrange_viewport(self, query: str = ""):
        self.viewport.get_model().clear()
        filtered_thumbnails = [
            (thumb, name)
            for thumb, name in self.thumbnails
            if query.casefold() in name.casefold()
        ]
        filtered_thumbnails.sort(key=lambda x: x[1].lower())
        for pixbuf, file_name in filtered_thumbnails:
            self.viewport.get_model().append([pixbuf, file_name])

    def on_wallpaper_selected(self, iconview, path):
        model = iconview.get_model()
        file_name = model[path][1]
        full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
        selected_scheme = self.scheme_dropdown.get_active_id()
        exec_shell_command_async(f'matugen image {full_path} -t {selected_scheme}')

    def on_scheme_changed(self, combo):
        selected_scheme = combo.get_active_id()
        print(f"Color scheme selected: {selected_scheme}")

    def _start_thumbnail_thread(self):
        thread = GLib.Thread.new("thumbnail-loader", self._preload_thumbnails, None)

    def _preload_thumbnails(self, _data):
        futures = [self.executor.submit(self._process_file, file_name) for file_name in self.files]
        concurrent.futures.wait(futures)
        GLib.idle_add(self._process_batch)

    def _process_file(self, file_name):
        full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
        cache_path = self._get_cache_path(file_name)
        if not os.path.exists(cache_path):
            try:
                with Image.open(full_path) as img:
                    img.thumbnail((96, 96), Image.Resampling.BILINEAR)
                    img.save(cache_path, "PNG")
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
                return
        self.thumbnail_queue.append((cache_path, file_name))
        GLib.idle_add(self._process_batch)

    def _process_batch(self):
        batch = self.thumbnail_queue[:10]
        del self.thumbnail_queue[:10]
        for cache_path, file_name in batch:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(cache_path)
                self.thumbnails.append((pixbuf, file_name))
                self.viewport.get_model().append([pixbuf, file_name])
            except Exception as e:
                print(f"Error loading thumbnail {cache_path}: {e}")
        if self.thumbnail_queue:
            GLib.idle_add(self._process_batch)
        return False

    def _get_cache_path(self, file_name: str) -> str:
        file_hash = hashlib.md5(file_name.encode("utf-8")).hexdigest()
        return os.path.join(self.CACHE_DIR, f"{file_hash}.png")

    @staticmethod
    def _is_image(file_name: str) -> bool:
        return file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'))
