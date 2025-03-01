import os
import urllib.parse
import urllib.request
import tempfile
from gi.repository import Gtk, GLib, Gio, Gdk
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.overlay import Overlay
from fabric.widgets.stack import Stack
from fabric.utils.helpers import exec_shell_command_async
from widgets.circle_image import CircleImage
import modules.icons as icons
import modules.data as data
from services.mpris import MprisPlayerManager, MprisPlayer

def get_player_icon_markup_by_name(player_name):
    if player_name:
        pn = player_name.lower()
        if pn == "firefox":
            return icons.firefox
        elif pn == "spotify":
            return icons.spotify
        elif pn in ("chromium", "brave"):
            return icons.chromium
    return icons.disc

def add_hover_cursor(widget):
    widget.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
    widget.connect("enter-notify-event", lambda w, event: w.get_window().set_cursor(
        Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "pointer")))
    widget.connect("leave-notify-event", lambda w, event: w.get_window().set_cursor(None))

class PlayerBox(Box):
    def __init__(self, mpris_player=None):
        super().__init__(orientation="v", h_align="fill", spacing=0, h_expand=False, v_expand=True)
        self.mpris_player = mpris_player

        self.cover = CircleImage(
            name="player-cover",
            image_file=f"{data.HOME_DIR}/.current.wall",
            size=162,
            h_align="center",
            v_align="center",
        )
        self.cover_placerholder = CircleImage(
            name="player-cover",
            size=198,
            h_align="center",
            v_align="center",
        )
        self.title = Label(name="player-title", ellipsization="end")
        self.album = Label(name="player-album", ellipsization="end")
        self.artist = Label(name="player-artist", ellipsization="end")
        self.progressbar = CircularProgressBar(
            name="player-progress",
            size=198,
            h_align="center",
            v_align="center",
            start_angle=180,
            end_angle=360,
        )
        self.time = Label(name="player-time", label="--:-- / --:--")
        self.overlay = Overlay(
            child=self.cover_placerholder,
            overlays=[self.progressbar, self.cover],
        )
        self.overlay_container = CenterBox(name="player-overlay", center_children=[self.overlay])
        self.title.set_label("Nothing Playing")
        self.album.set_label("Enjoy the silence")
        self.artist.set_label("¯\\_(ツ)_/¯")
        self.progressbar.set_value(0.0)
        self.prev = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.prev),
        )
        self.backward = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.skip_back),
        )
        self.play_pause = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.play),
        )
        self.forward = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.skip_forward),
        )
        self.next = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.next),
        )
        # Add hover effect to buttons
        add_hover_cursor(self.prev)
        add_hover_cursor(self.backward)
        add_hover_cursor(self.play_pause)
        add_hover_cursor(self.forward)
        add_hover_cursor(self.next)
        self.btn_box = CenterBox(
            name="player-btn-box",
            orientation="h",
            center_children=[
                Box(
                    orientation="h",
                    spacing=8,
                    h_expand=True,
                    h_align="fill",
                    children=[
                        self.prev,
                        self.backward,
                        self.play_pause,
                        self.forward,
                        self.next,
                    ]
                )
            ]
        )
        self.player_box = Box(
            name="player-box",
            orientation="v",
            spacing=4,
            children=[
                self.overlay_container,
                self.title,
                self.album,
                self.artist,
                self.btn_box,
                self.time,
            ]
        )
        self.add(self.player_box)
        if mpris_player:
            self._apply_mpris_properties()
            self.prev.connect("clicked", self._on_prev_clicked)
            self.play_pause.connect("clicked", self._on_play_pause_clicked)
            self.backward.connect("clicked", self._on_backward_clicked)
            self.forward.connect("clicked", self._on_forward_clicked)
            self.next.connect("clicked", self._on_next_clicked)
            if mpris_player.can_seek:
                GLib.timeout_add(1000, self._update_progress)
            self.mpris_player.connect("changed", self._on_mpris_changed)
        else:
            self.play_pause.get_child().set_markup(icons.stop)

    def _apply_mpris_properties(self):
        mp = self.mpris_player
        self.title.set_visible(bool(mp.title and mp.title.strip()))
        if mp.title and mp.title.strip():
            self.title.set_text(mp.title)
        self.album.set_visible(bool(mp.album and mp.album.strip()))
        if mp.album and mp.album.strip():
            self.album.set_text(mp.album)
        self.artist.set_visible(bool(mp.artist and mp.artist.strip()))
        if mp.artist and mp.artist.strip():
            self.artist.set_text(mp.artist)
        if mp.arturl:
            parsed = urllib.parse.urlparse(mp.arturl)
            if parsed.scheme == "file":
                local_arturl = urllib.parse.unquote(parsed.path)
                self._set_cover_image(local_arturl)
            elif parsed.scheme in ("http", "https"):
                GLib.Thread.new("download-artwork", self._download_and_set_artwork, mp.arturl)
            else:
                self._set_cover_image(mp.arturl)
        else:
            fallback = os.path.expanduser("~/.current.wall")
            self._set_cover_image(fallback)
            file_obj = Gio.File.new_for_path(fallback)
            monitor = file_obj.monitor_file(Gio.FileMonitorFlags.NONE, None)
            monitor.connect("changed", self.on_wallpaper_changed)
            self._wallpaper_monitor = monitor
        self.update_play_pause_icon()
        self.progressbar.set_visible(True)
        self.time.set_visible(True)
        player_name = mp.player_name.lower() if hasattr(mp, "player_name") and mp.player_name else ""
        if player_name == "firefox" or (hasattr(mp, "can_seek") and not mp.can_seek):
            self.progressbar.set_visible(False)
            self.time.set_visible(False)
            self.backward.set_visible(False)
            self.forward.set_visible(False)
        else:
            self.backward.set_visible(True)
            self.forward.set_visible(True)

    def _set_cover_image(self, image_path):
        if image_path and os.path.isfile(image_path):
            self.cover.set_image_from_file(image_path)
        else:
            fallback = os.path.expanduser("~/.current.wall")
            self.cover.set_image_from_file(fallback)
            file_obj = Gio.File.new_for_path(fallback)
            monitor = file_obj.monitor_file(Gio.FileMonitorFlags.NONE, None)
            monitor.connect("changed", self.on_wallpaper_changed)
            self._wallpaper_monitor = monitor

    def _download_and_set_artwork(self, arturl):
        """
        Download the artwork from the given URL asynchronously and update the cover image
        using GLib.idle_add to ensure UI updates occur on the main thread.
        """
        try:
            parsed = urllib.parse.urlparse(arturl)
            suffix = os.path.splitext(parsed.path)[1] or ".png"
            with urllib.request.urlopen(arturl) as response:
                data = response.read()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(data)
            temp_file.close()
            local_arturl = temp_file.name
        except Exception:
            local_arturl = os.path.expanduser("~/.current.wall")
        GLib.idle_add(self._set_cover_image, local_arturl)
        return None

    def update_play_pause_icon(self):
        if self.mpris_player.playback_status == "playing":
            self.play_pause.get_child().set_markup(icons.pause)
        else:
            self.play_pause.get_child().set_markup(icons.play)

    def on_wallpaper_changed(self, monitor, file, other_file, event):
        self.cover.set_image_from_file(os.path.expanduser("~/.current.wall"))

    # --- Control methods, defined only once each ---
    def _on_prev_clicked(self, button):
        if self.mpris_player:
            self.mpris_player.previous()

    def _on_play_pause_clicked(self, button):
        if self.mpris_player:
            self.mpris_player.play_pause()
            self.update_play_pause_icon()

    def _on_backward_clicked(self, button):
        if self.mpris_player and self.mpris_player.can_seek:
            new_pos = max(0, self.mpris_player.position - 5000000)  # 5 seconds backward
            self.mpris_player.position = new_pos

    def _on_forward_clicked(self, button):
        if self.mpris_player and self.mpris_player.can_seek:
            new_pos = self.mpris_player.position + 5000000  # 5 seconds forward
            self.mpris_player.position = new_pos

    def _on_next_clicked(self, button):
        if self.mpris_player:
            self.mpris_player.next()

    def _update_progress(self):
        if not self.mpris_player:
            return False
        try:
            current = self.mpris_player.position
        except Exception:
            current = 0
        try:
            total = int(self.mpris_player.length or 0)
        except Exception:
            total = 0
        progress = (current / total) if total > 0 else 0
        self.progressbar.set_value(progress)
        self.time.set_text(f"{self._format_time(current)} / {self._format_time(total)}")
        return True

    def _format_time(self, us):
        seconds = int(us / 1000000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02}"

    def _update_metadata(self):
        if not self.mpris_player:
            return False
        self._apply_mpris_properties()
        return True

    def _on_mpris_changed(self, *args):
        # Debounce metadata updates to avoid excessive work on the main thread.
        if not hasattr(self, "_update_pending") or not self._update_pending:
            self._update_pending = True
            GLib.timeout_add(100, self._apply_mpris_properties_debounced)

    def _apply_mpris_properties_debounced(self):
        self._apply_mpris_properties()
        self._update_pending = False
        return False

class Player(Box):
    def __init__(self):
        super().__init__(name="player", orientation="v", h_align="fill", spacing=0, h_expand=False, v_expand=True)
        self.player_stack = Stack(
            name="player-stack",
            transition_type="slide-left-right",
            transition_duration=500,
            v_align="center",
            v_expand=True,
        )
        self.switcher = Gtk.StackSwitcher(
            name="player-switcher",
            spacing=8,
        )
        self.switcher.set_stack(self.player_stack)
        self.switcher.set_halign(Gtk.Align.CENTER)
        self.mpris_manager = MprisPlayerManager()
        players = self.mpris_manager.players
        if players:
            for p in players:
                mp = MprisPlayer(p)
                pb = PlayerBox(mpris_player=mp)
                self.player_stack.add_titled(pb, mp.player_name, mp.player_name)
        else:
            pb = PlayerBox(mpris_player=None)
            self.player_stack.add_titled(pb, "nothing", "Nothing Playing")
        self.mpris_manager.connect("player-appeared", self.on_player_appeared)
        self.mpris_manager.connect("player-vanished", self.on_player_vanished)
        self.switcher.set_visible(True)
        self.add(self.player_stack)
        self.add(self.switcher)
        GLib.idle_add(self._replace_switcher_labels)

    def on_player_appeared(self, manager, player):
        children = self.player_stack.get_children()
        if len(children) == 1 and not getattr(children[0], "mpris_player", None):
            self.player_stack.remove(children[0])
        mp = MprisPlayer(player)
        pb = PlayerBox(mpris_player=mp)
        self.player_stack.add_titled(pb, mp.player_name, mp.player_name)
        GLib.timeout_add(1000, pb._update_progress)
        self.switcher.set_visible(True)
        GLib.idle_add(lambda: self._update_switcher_for_player(mp.player_name))
        GLib.idle_add(self._replace_switcher_labels)

    def on_player_vanished(self, manager, player_name):
        for child in self.player_stack.get_children():
            if hasattr(child, "mpris_player") and child.mpris_player and child.mpris_player.player_name == player_name:
                self.player_stack.remove(child)
                break
        if not any(getattr(child, "mpris_player", None) for child in self.player_stack.get_children()):
            pb = PlayerBox(mpris_player=None)
            self.player_stack.add_titled(pb, "nothing", "Nothing Playing")
        self.switcher.set_visible(True)
        GLib.idle_add(self._replace_switcher_labels)

    def _replace_switcher_labels(self):
        buttons = self.switcher.get_children()
        for btn in buttons:
            if isinstance(btn, Gtk.ToggleButton):
                default_label = None
                for child in btn.get_children():
                    if isinstance(child, Gtk.Label):
                        default_label = child
                        break
                if default_label:
                    label_player_name = getattr(default_label, "player_name", default_label.get_text().lower())
                    icon_markup = get_player_icon_markup_by_name(label_player_name)
                    btn.remove(default_label)
                    new_label = Label(name="player-label", markup=icon_markup)
                    new_label.player_name = label_player_name
                    btn.add(new_label)
                    new_label.show_all()
        return False

    def _update_switcher_for_player(self, player_name):
        for btn in self.switcher.get_children():
            if isinstance(btn, Gtk.ToggleButton):
                default_label = None
                for child in btn.get_children():
                    if isinstance(child, Gtk.Label):
                        default_label = child
                        break
                if default_label:
                    label_player_name = getattr(default_label, "player_name", default_label.get_text().lower())
                    if label_player_name == player_name.lower():
                        icon_markup = get_player_icon_markup_by_name(player_name)
                        btn.remove(default_label)
                        new_label = Label(name="player-label", markup=icon_markup)
                        new_label.player_name = player_name.lower()
                        btn.add(new_label)
                        new_label.show_all()
        return False
    

class PlayerSmall(CenterBox):
    def __init__(self):
        super().__init__(orientation="h", h_align="fill", v_align="center")
        self._show_artist = False  # toggle flag

        self.mpris_icon = Button(
            name="compact-mpris-icon",
            child=Label(name="compact-mpris-icon-label", markup=icons.disc)
        )
        # Remove scroll events; instead, add button press events.
        self.mpris_icon.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.mpris_icon.connect("button-press-event", self._on_icon_button_press)
        # Prevent the child from propagating events.
        child = self.mpris_icon.get_child()
        child.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        child.connect("button-press-event", lambda widget, event: True)
        # Add hover effect
        add_hover_cursor(self.mpris_icon)

        self.mpris_label = Label(
            name="compact-mpris-label",
            label="Nothing Playing",
            ellipsization="end"
        )
        self.mpris_button = Button(
            name="compact-mpris-button",
            child=Label(name="compact-mpris-button-label", markup=icons.play)
        )
        self.mpris_button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.mpris_button.connect("button-press-event", self._on_play_pause_button_press)
        # Add hover effect
        add_hover_cursor(self.mpris_button)

        # Create additional compact view.
        self.mpris_small = CenterBox(
            name="compact-mpris",
            orientation="h",
            h_expand=True,
            h_align="fill",
            v_align="center",
            start_children=self.mpris_icon,
            center_children=self.mpris_label,
            end_children=self.mpris_button,
        )
        self.add(self.mpris_small)

        self.mpris_manager = MprisPlayerManager()
        self.mpris_player = None
        # Almacenar el índice del reproductor actual
        self.current_index = 0

        players = self.mpris_manager.players
        if players:
            mp = MprisPlayer(players[self.current_index])
            self.mpris_player = mp
            self._apply_mpris_properties()
            self.mpris_player.connect("changed", self._on_mpris_changed)
        else:
            self._apply_mpris_properties()

        self.mpris_manager.connect("player-appeared", self.on_player_appeared)
        self.mpris_manager.connect("player-vanished", self.on_player_vanished)
        self.mpris_button.connect("clicked", self._on_play_pause_clicked)

    def _apply_mpris_properties(self):
        if not self.mpris_player:
            self.mpris_label.set_text("Nothing Playing")
            self.mpris_button.get_child().set_markup(icons.stop)
            self.mpris_icon.get_child().set_markup(icons.disc)
            return

        mp = self.mpris_player

        # Toggle between title and artist.
        text = (mp.artist if self._show_artist and mp.artist
                else (mp.title if mp.title and mp.title.strip()
                      else "Nothing Playing"))
        self.mpris_label.set_text(text)

        # Choose icon based on player name.
        player_name = mp.player_name.lower() if hasattr(mp, "player_name") and mp.player_name else ""
        icon_markup = get_player_icon_markup_by_name(player_name)
        self.mpris_icon.get_child().set_markup(icon_markup)
        self.update_play_pause_icon()

    def _on_icon_button_press(self, widget, event):
        from gi.repository import Gdk
        if event.type == Gdk.EventType.BUTTON_PRESS:
            players = self.mpris_manager.players
            if not players:
                return True

            # Cambiar de reproductor según el botón presionado.
            if event.button == 1:  # Left-click: reproductor anterior
                self.current_index = (self.current_index - 1) % len(players)
            elif event.button == 3:  # Right-click: reproductor siguiente
                self.current_index = (self.current_index + 1) % len(players)
            elif event.button == 2:  # Middle-click: toggle entre title y artist
                self._on_icon_clicked(widget)
                return True

            mp_new = MprisPlayer(players[self.current_index])
            self.mpris_player = mp_new
            # Conectar el evento "changed" para que se actualice el botón de play/pausa
            self.mpris_player.connect("changed", self._on_mpris_changed)
            # Se remueve el reinicio de self._show_artist para que la selección (artist/title) persista
            self._apply_mpris_properties()
            return True  # Se consume el evento
        return True

    def _on_play_pause_button_press(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 1:  # Click izquierdo -> track anterior
                if self.mpris_player:
                    self.mpris_player.previous()
                    self.mpris_button.get_child().set_markup(icons.prev)
                    GLib.timeout_add(500, self._restore_play_pause_icon)
            elif event.button == 3:  # Click derecho -> siguiente track
                if self.mpris_player:
                    self.mpris_player.next()
                    self.mpris_button.get_child().set_markup(icons.next)
                    GLib.timeout_add(500, self._restore_play_pause_icon)
            elif event.button == 2:  # Click medio -> play/pausa
                if self.mpris_player:
                    self.mpris_player.play_pause()
                    self.update_play_pause_icon()
            return True
        return True

    def _restore_play_pause_icon(self):
        self.update_play_pause_icon()
        return False

    def _on_icon_clicked(self, widget):
        if not self.mpris_player:
            return
        # Toggle between showing title and artist.
        self._show_artist = not self._show_artist
        text = (self.mpris_player.artist if self._show_artist and self.mpris_player.artist
                else (self.mpris_player.title if self.mpris_player.title and self.mpris_player.title.strip()
                      else "Nothing Playing"))
        self.mpris_label.set_text(text)

    def update_play_pause_icon(self):
        if self.mpris_player and self.mpris_player.playback_status == "playing":
            self.mpris_button.get_child().set_markup(icons.pause)
        else:
            self.mpris_button.get_child().set_markup(icons.play)

    def _on_play_pause_clicked(self, button):
        if self.mpris_player:
            self.mpris_player.play_pause()
            self.update_play_pause_icon()

    def _on_mpris_changed(self, *args):
        # Update properties when the player's state changes.
        self._apply_mpris_properties()

    def on_player_appeared(self, manager, player):
        # When a new player appears, use it if no player is active.
        if not self.mpris_player:
            mp = MprisPlayer(player)
            self.mpris_player = mp
            self._apply_mpris_properties()
            self.mpris_player.connect("changed", self._on_mpris_changed)

    def on_player_vanished(self, manager, player_name):
        players = self.mpris_manager.players
        if players and self.mpris_player and self.mpris_player.player_name == player_name:
            self.current_index = self.current_index % len(players)
            new_player = MprisPlayer(players[self.current_index])
            self.mpris_player = new_player
            self.mpris_player.connect("changed", self._on_mpris_changed)
        elif not players:
            self.mpris_player = None
        self._apply_mpris_properties()
