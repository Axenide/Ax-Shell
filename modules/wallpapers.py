import colorsys
import concurrent.futures
import hashlib
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.entry import Entry
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango
from PIL import Image

import config.config
import config.data as data
import modules.icons as icons


def get_all_monitors():
    """
    Returns a list of connected monitor names using xrandr.
    """
    try:
        output = subprocess.check_output(['xrandr', '--query']).decode()
        return [line.split()[0] for line in output.splitlines() if " connected" in line]
    except Exception as e:
        print(f"Monitor detection failed: {e}")
        return []

def kill_swww_daemon():
    try:
        subprocess.run(
            ["pkill", "-x", "swww"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("Killed swww-daemon if it was running.")
    except Exception as e:
        print(f"Failed to kill swww: {e}")

def kill_mpvpaper():
    try:
        subprocess.run(
            ["pkill", "-x", "mpvpaper"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print("Killed mpvpaper if it was running.")
    except Exception as e:
        print(f"Failed to kill mpvpaper: {e}")


class WallpaperSelector(Box):
    CACHE_DIR = f"{data.CACHE_DIR}/thumbs"

    def __init__(self, **kwargs):
        old_cache_dir = f"{data.CACHE_DIR}/wallpapers"
        if os.path.exists(old_cache_dir):
            shutil.rmtree(old_cache_dir)

        super().__init__(name="wallpapers", spacing=4, orientation="v", h_expand=False, v_expand=False, **kwargs)
        os.makedirs(self.CACHE_DIR, exist_ok=True)

        with os.scandir(data.WALLPAPERS_DIR) as entries:
            for entry in entries:
                if entry.is_file() and self._is_media(entry.name):
                    if entry.name != entry.name.lower() or " " in entry.name:
                        new_name = entry.name.lower().replace(" ", "-")
                        full_path = os.path.join(data.WALLPAPERS_DIR, entry.name)
                        new_full_path = os.path.join(data.WALLPAPERS_DIR, new_name)
                        try:
                            os.rename(full_path, new_full_path)
                            print(f"Renamed old wallpaper '{full_path}' to '{new_full_path}'")
                        except Exception as e:
                            print(f"Error renaming file {full_path}: {e}")

        self.files = sorted([f for f in os.listdir(data.WALLPAPERS_DIR) if self._is_media(f)])
        self.thumbnails = []
        self.thumbnail_queue = []
        self.executor = ThreadPoolExecutor(max_workers=4)

        self.selected_index = -1

        self.viewport = Gtk.IconView(name="wallpaper-icons")
        self.viewport.set_model(Gtk.ListStore(GdkPixbuf.Pixbuf, str))
        self.viewport.set_pixbuf_column(0)
        self.viewport.set_text_column(-1)
        self.viewport.set_item_width(0)
        self.viewport.connect("item-activated", self.on_wallpaper_selected)

        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            child=self.viewport,
            propagate_width=False,
            propagate_height=False,
        )

        self.search_entry = Entry(
            name="search-entry-walls",
            placeholder="Search Wallpapers...",
            h_expand=True,
            h_align="fill",
            notify_text=lambda entry, *_: self.arrange_viewport(entry.get_text()),
            on_key_press_event=self.on_search_entry_key_press,
        )
        self.search_entry.props.xalign = 0.5
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
        self.scheme_dropdown.set_active_id("scheme-tonal-spot")
        self.scheme_dropdown.connect("changed", self.on_scheme_changed)

        self.matugen_enabled = True
        try:
            with open(data.MATUGEN_STATE_FILE, 'r') as f:
                content = f.read().strip().lower()
                if content == "false":
                    self.matugen_enabled = False
                elif content == "true":
                    self.matugen_enabled = True
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error reading matugen state file: {e}")

        self.matugen_switcher = Gtk.Switch(name="matugen-switcher")
        self.matugen_switcher.set_vexpand(False)
        self.matugen_switcher.set_hexpand(False)
        self.matugen_switcher.set_valign(Gtk.Align.CENTER)
        self.matugen_switcher.set_halign(Gtk.Align.CENTER)
        self.matugen_switcher.set_active(self.matugen_enabled)
        self.matugen_switcher.connect("notify::active", self.on_switch_toggled)

        self.mat_icon = Label(name="mat-label", markup=icons.palette)

        self.header_box = Box(
            name="header-box",
            spacing=4,
            orientation="h",
            children=[self.matugen_switcher, self.mat_icon, self.search_entry, self.scheme_dropdown],
        )

        self.add(self.header_box)

        self.hue_slider = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=Gtk.Adjustment(value=0, lower=0, upper=360, step_increment=1, page_increment=10),
            draw_value=False,
            digits=0,
            name="hue-slider",
        )

        self.hue_slider.set_hexpand(True)
        self.hue_slider.set_halign(Gtk.Align.FILL)
        self.hue_slider.set_vexpand(False)
        self.hue_slider.set_valign(Gtk.Align.CENTER)

        self.apply_color_button = Button(name="apply-color-button", child=Label(name="apply-color-label", markup=icons.accept))
        self.apply_color_button.connect("clicked", self.on_apply_color_clicked)
        self.apply_color_button.set_vexpand(False)
        self.apply_color_button.set_valign(Gtk.Align.CENTER)

        self.custom_color_selector_box = Box(
            orientation="h", spacing=5, name="custom-color-selector-box",
            h_align="center"
        )
        self.custom_color_selector_box.add(self.hue_slider)
        self.custom_color_selector_box.add(self.apply_color_button)
        self.custom_color_selector_box.set_halign(Gtk.Align.FILL)

        self.pack_start(self.scrolled_window, True, True, 0)
        self.pack_start(self.custom_color_selector_box, False, False, 0)

        self._start_thumbnail_thread()
        self.connect("map", self.on_map)
        self.setup_file_monitor()
        self.show_all()
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
            if self._is_media(file_name):
                new_name = file_name.lower().replace(" ", "-")
                full_path = os.path.join(data.WALLPAPERS_DIR, file_name)
                new_full_path = os.path.join(data.WALLPAPERS_DIR, new_name)
                if new_name != file_name:
                    try:
                        os.rename(full_path, new_full_path)
                        file_name = new_name
                        print(f"Renamed file '{full_path}' to '{new_full_path}')")
                    except Exception as e:
                        print(f"Error renaming file {full_path}: {e}")
                if file_name not in self.files:
                    self.files.append(file_name)
                    self.files.sort()
                    self.executor.submit(self._process_file, file_name)
        elif event_type == Gio.FileMonitorEvent.CHANGED:
            if self._is_media(file_name) and file_name in self.files:
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
        current_wall = os.path.expanduser("~/.current.wall")

        # Kill both wallpaper daemons before switching
        kill_swww_daemon()
        kill_mpvpaper()

        if self._is_image(file_name):
            # Set symlink for images
            if os.path.islink(current_wall) or os.path.isfile(current_wall):
                os.remove(current_wall)
            os.symlink(full_path, current_wall)
            exec_shell_command_async(
                    f'swww img "{full_path}" -t outer --transition-duration 1.5 --transition-step 255 --transition-fps 60 -f Nearest'
            )
            if self.matugen_switcher.get_active():
                exec_shell_command_async(f'matugen image "{full_path}" -t {selected_scheme}')
        elif self._is_video(file_name):
            monitors = get_all_monitors()
            for monitor in monitors:
                subprocess.Popen(
                    ["mpvpaper", monitor, full_path, "-o", "--loop --no-audio"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            extracted_frame = self._extract_video_frame(full_path, size="1920:-1")
            if extracted_frame:
                # Always update .current.wall to the extracted frame for Hyprlock
                if os.path.islink(current_wall) or os.path.isfile(current_wall):
                    os.remove(current_wall)
                os.symlink(extracted_frame, current_wall)
                if self.matugen_switcher.get_active():
                    exec_shell_command_async(f'matugen image "{extracted_frame}" -t {selected_scheme}')

    def _extract_video_frame(self, video_path, size="1920:-1"):
        frame_name = hashlib.md5(video_path.encode("utf-8")).hexdigest() + f"_frame_{size}.png"
        frame_path = os.path.join(self.CACHE_DIR, frame_name)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss", "0.5",
                    "-i", video_path,
                    "-vframes", "1",
                    "-vf", f"scale={size}",
                    frame_path
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if os.path.exists(frame_path):
                return frame_path
        except Exception as e:
            print(f"Error extracting frame from video {video_path}: {e}")
        return None

    def on_scheme_changed(self, combo):
        selected_scheme = combo.get_active_id()
        print(f"Color scheme selected: {selected_scheme}")

    def on_search_entry_key_press(self, widget, event):
        if event.state & Gdk.ModifierType.SHIFT_MASK:
            if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
                schemes_list = list(self.schemes.keys())
                current_id = self.scheme_dropdown.get_active_id()
                current_index = schemes_list.index(current_id) if current_id in schemes_list else 0
                new_index = (current_index - 1) % len(schemes_list) if event.keyval == Gdk.KEY_Up else (current_index + 1) % len(schemes_list)
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
        columns = self.viewport.get_columns()
        if columns <= 0 and total_items > 0:
            estimated_cols = 0
            try:
                first_item_path = Gtk.TreePath.new_from_indices([0])
                base_row = self.viewport.get_item_row(first_item_path)
                for i in range(1, total_items):
                    path = Gtk.TreePath.new_from_indices([i])
                    row = self.viewport.get_item_row(path)
                    if row > base_row:
                        estimated_cols = i
                        break
                if estimated_cols == 0:
                    estimated_cols = total_items
                columns = max(1, estimated_cols)
            except Exception:
                columns = 1
        elif columns <= 0 and total_items == 0:
            columns = 1
        columns = max(1, columns)

        current_index = self.selected_index
        new_index = current_index

        if current_index == -1:
            if keyval in (Gdk.KEY_Down, Gdk.KEY_Right):
                new_index = 0
            elif keyval in (Gdk.KEY_Up, Gdk.KEY_Left):
                new_index = total_items - 1
            if total_items == 0:
                new_index = -1
        else:
            if keyval == Gdk.KEY_Up:
                potential_new_index = current_index - columns
                if potential_new_index >= 0:
                    new_index = potential_new_index
            elif keyval == Gdk.KEY_Down:
                potential_new_index = current_index + columns
                if potential_new_index < total_items:
                    new_index = potential_new_index
            elif keyval == Gdk.KEY_Left:
                if current_index > 0 and current_index % columns != 0:
                    new_index = current_index - 1
            elif keyval == Gdk.KEY_Right:
                if current_index < total_items - 1 and (current_index + 1) % columns != 0:
                    new_index = current_index + 1

        if new_index != self.selected_index and 0 <= new_index < total_items:
            self.update_selection(new_index)
        elif total_items > 0 and self.selected_index == -1 and 0 <= new_index < total_items:
            self.update_selection(new_index)

    def update_selection(self, new_index: int):
        self.viewport.unselect_all()
        path = Gtk.TreePath.new_from_indices([new_index])
        self.viewport.select_path(path)
        self.viewport.scroll_to_path(path, False, 0.5, 0.5)
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
                if self._is_image(file_name):
                    with Image.open(full_path) as img:
                        width, height = img.size
                        side = min(width, height)
                        left = (img.width - side) // 2
                        top = (height - side) // 2
                        right = left + side
                        bottom = top + side
                        img_cropped = img.crop((left, top, right, bottom))
                        img_cropped.thumbnail((96, 96), Image.Resampling.LANCZOS)
                        img_cropped.save(cache_path, "PNG")
                elif self._is_video(file_name):
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-ss", "0.5",
                            "-i", full_path,
                            "-vframes", "1",
                            "-vf", "scale=96:96:force_original_aspect_ratio=decrease",
                            cache_path
                        ],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
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

    @staticmethod
    def _is_video(file_name: str) -> bool:
        return file_name.lower().endswith('.mp4')

    @classmethod
    def _is_media(cls, file_name: str) -> bool:
        return cls._is_image(file_name) or cls._is_video(file_name)

    def on_search_entry_focus_out(self, widget, event):
        if self.get_mapped():
            widget.grab_focus()
        return False

    def on_map(self, widget):
        self.custom_color_selector_box.set_visible(not self.matugen_enabled)

    def hsl_to_rgb_hex(self, h: float, s: float = 1.0, l: float = 0.5) -> str:
        hue = h / 360.0
        r, g, b = colorsys.hls_to_rgb(hue, l, s)
        r_int, g_int, b_int = int(r * 255), int(g * 255), int(b * 255)
        return f"#{r_int:02X}{g_int:02X}{b_int:02X}"

    def rgba_to_hex(self, rgba: Gdk.RGBA) -> str:
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f"#{r:02X}{g:02X}{b:02X}"

    def on_switch_toggled(self, switch, gparam):
        is_active = switch.get_active()
        self.matugen_enabled = is_active
        self.custom_color_selector_box.set_visible(not is_active)
        try:
            with open(data.MATUGEN_STATE_FILE, 'w') as f:
                f.write(str(is_active))
        except Exception as e:
            print(f"Error writing matugen state file: {e}")

    def on_apply_color_clicked(self, button):
        hue_value = self.hue_slider.get_value()
        hex_color = self.hsl_to_rgb_hex(hue_value)
        print(f"Applying color from slider: H={hue_value}, HEX={hex_color}")
        selected_scheme = self.scheme_dropdown.get_active_id()
        exec_shell_command_async(f'matugen color hex "{hex_color}" -t {selected_scheme}')
