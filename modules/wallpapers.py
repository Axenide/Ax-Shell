import os
import hashlib
import shutil
from gi.repository import GdkPixbuf, Gtk, GLib, Gio, Gdk
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
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
    CACHE_DIR = os.path.expanduser("~/.cache/ax-shell/thumbs")  # Changed from wallpapers to thumbs

    def __init__(self, **kwargs):
        # Delete the old cache directory if it exists
        old_cache_dir = os.path.expanduser("~/.cache/ax-shell/wallpapers")
        if os.path.exists(old_cache_dir):
            shutil.rmtree(old_cache_dir)

        super().__init__(name="wallpapers", spacing=4, orientation="v", h_expand=False, v_expand=False, **kwargs)
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        self.files = sorted([f for f in os.listdir(data.WALLPAPERS_DIR) if self._is_image(f)])
        self.thumbnails = []
        self.thumbnail_queue = []
        self.executor = ThreadPoolExecutor(max_workers=4)  # Shared executor

        # Variable para controlar la selección (similar a AppLauncher)
        self.selected_index = -1

        self.viewport = Gtk.IconView(name="wallpaper-icons")
        self.viewport.set_model(Gtk.ListStore(GdkPixbuf.Pixbuf, str))
        self.viewport.set_pixbuf_column(0)
        # Quitamos la columna de texto para que solo se muestre la imagen
        self.viewport.set_text_column(-1)
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
            name="search-entry-walls",
            placeholder="Search Wallpapers...",
            h_expand=True,
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
            on_key_press_event=self.on_search_entry_key_press,
        )
        self.search_entry.props.xalign = 0.5
        # Instead of always grabbing focus on focus-out, call our handler:
        self.search_entry.connect("focus-out-event", self.on_search_entry_focus_out)

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

        # New: Declare a switcher to enable/disable Matugen (enabled by default)
        self.matugen_switcher = Gtk.Switch(name="matugen-switcher")
        self.matugen_switcher.set_vexpand(False)
        self.matugen_switcher.set_hexpand(False)
        self.matugen_switcher.set_valign(Gtk.Align.CENTER)
        self.matugen_switcher.set_halign(Gtk.Align.CENTER)
        self.matugen_switcher.set_active(True)

        self.mat_icon = Label(name="mat-label", markup=icons.palette)

        # Add the switcher to the header_box's start_children
        self.header_box = CenterBox(
            name="header-box",
            spacing=8,
            orientation="h",
            start_children=[self.matugen_switcher, self.mat_icon],  # <-- added here
            center_children=[self.search_entry],
            end_children=[self.scheme_dropdown],
        )

        self.add(self.header_box)
        self.add(self.scrolled_window)
        self._start_thumbnail_thread()
        self.setup_file_monitor()  # Inicializamos la monitorización de archivos
        self.show_all()
        # Garantizamos que el input tenga foco al iniciar
        self.search_entry.grab_focus()

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

    def arrange_viewport(self, query: str = ""):
        model = self.viewport.get_model()
        model.clear()
        filtered_thumbnails = [
            (thumb, name)
            for thumb, name in self.thumbnails
            if query.casefold() in name.casefold()
        ]
        filtered_thumbnails.sort(key=lambda x: x[1].lower())
        for pixbuf, file_name in filtered_thumbnails:
            model.append([pixbuf, file_name])
        # Si el input está vacío, no se marca ningún ícono;
        # de lo contrario, se marca el primero
        if query.strip() == "":
            self.viewport.unselect_all()
            self.selected_index = -1
        elif len(model) > 0:
            self.update_selection(0)

    def on_wallpaper_selected(self, iconview, path):
        model = iconview.get_model()
        file_name = model[path][1]
        full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
        selected_scheme = self.scheme_dropdown.get_active_id()
        if self.matugen_switcher.get_active():
            # Matugen is enabled: run the normal command.
            exec_shell_command_async(f'matugen image {full_path} -t {selected_scheme}')
        else:
            # Matugen is disabled: run the alternative swww command.
            exec_shell_command_async(
                f'swww img {full_path} -t outer --transition-duration 1.5 --transition-step 255 --transition-fps 60 -f Nearest'
            )

    def on_scheme_changed(self, combo):
        selected_scheme = combo.get_active_id()
        print(f"Color scheme selected: {selected_scheme}")

    def on_search_entry_key_press(self, widget, event):
        if event.state & Gdk.ModifierType.SHIFT_MASK:
            if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
                schemes_list = list(self.schemes.keys())
                current_id = self.scheme_dropdown.get_active_id()
                current_index = schemes_list.index(current_id) if current_id in schemes_list else 0
                if event.keyval == Gdk.KEY_Up:
                    new_index = (current_index - 1) % len(schemes_list)
                else:
                    new_index = (current_index + 1) % len(schemes_list)
                self.scheme_dropdown.set_active(new_index)
                return True
            elif event.keyval == Gdk.KEY_Right:
                self.scheme_dropdown.popup()
                return True

        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down, Gdk.KEY_Left, Gdk.KEY_Right):
            self.move_selection_2d(event.keyval)
            return True
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.selected_index != -1:
                path = Gtk.TreePath.new_from_indices([self.selected_index])
                self.on_wallpaper_selected(self.viewport, path)
            return True
        return False

    def move_selection_2d(self, keyval):
        model = self.viewport.get_model()
        total_items = len(model)
        if total_items == 0:
            return

        if self.selected_index == -1:
            # Si no hay selección previa, iniciamos en 0 o en el último según la flecha
            new_index = 0 if keyval in (Gdk.KEY_Down, Gdk.KEY_Right) else total_items - 1
        else:
            current_index = self.selected_index
            # Se calcula el número de columnas basado en el ancho asignado al IconView y el ancho aproximado de cada ítem.
            allocation = self.viewport.get_allocation()
            item_width = 108  # Valor aproximado (tamaño del thumbnail más márgenes)
            columns = max(1, allocation.width // item_width)
            if keyval == Gdk.KEY_Right:
                new_index = current_index + 1
            elif keyval == Gdk.KEY_Left:
                new_index = current_index - 1
            elif keyval == Gdk.KEY_Down:
                new_index = current_index + columns
            elif keyval == Gdk.KEY_Up:
                new_index = current_index - columns
            # Aseguramos que el índice esté dentro de los límites
            if new_index < 0:
                new_index = 0
            if new_index >= total_items:
                new_index = total_items - 1

        self.update_selection(new_index)

    def update_selection(self, new_index: int):
        self.viewport.unselect_all()
        path = Gtk.TreePath.new_from_indices([new_index])
        self.viewport.select_path(path)
        self.viewport.scroll_to_path(path, False, 0.5, 0.5)  # Asegura que el ícono marcado esté visible
        self.selected_index = new_index

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
                    width, height = img.size
                    side = min(width, height)
                    left = (width - side) // 2
                    top = (height - side) // 2
                    right = left + side
                    bottom = top + side
                    img_cropped = img.crop((left, top, right, bottom))
                    img_cropped.thumbnail((96, 96), Image.Resampling.LANCZOS)
                    img_cropped.save(cache_path, "PNG")
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

    def on_search_entry_focus_out(self, widget, event):
        # Only re-grab focus if the WallpaperSelector widget is mapped (visible)
        if self.get_mapped():
            widget.grab_focus()
        return False
