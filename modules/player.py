import os
import tempfile
import urllib.parse
import urllib.request

from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.stack import Stack
from gi.repository import Gdk, Gio, GLib, Gtk

import config.data as data
import modules.icons as icons
from modules.cavalcade import SpectrumRender
from services.mpris import MprisPlayer, MprisPlayerManager
from widgets.circle_image import CircleImage

vertical_mode = False
if data.PANEL_THEME == "Panel" and (data.BAR_POSITION in ["Left", "Right"] or data.PANEL_POSITION in ["Start", "End"]):
    vertical_mode = True

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
        super().__init__(orientation="v", h_align="fill", spacing=0, h_expand=False, v_expand=not vertical_mode)
        self.mpris_player = mpris_player
        self._progress_timer_id = None

        self.cover = CircleImage(
            name="player-cover",
            image_file=os.path.expanduser("~/.current.wall"),
            size=162 if not vertical_mode else 96,
            h_align="center",
            v_align="center",
        )
        self.cover_placerholder = CircleImage(
            name="player-cover",
            size=198 if not vertical_mode else 132,
            h_align="center",
            v_align="center",
        )
        self.title = Label(name="player-title", h_expand=True, h_align="fill", ellipsization="end", max_chars_width=1, style_classes=["vertical"] if vertical_mode else [])
        self.album = Label(name="player-album", h_expand=True, h_align="fill", ellipsization="end", max_chars_width=1)
        self.artist = Label(name="player-artist", h_expand=True, h_align="fill", ellipsization="end", max_chars_width=1)
        self.progressbar = CircularProgressBar(
            name="player-progress",
            size=198 if not vertical_mode else 132,
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
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        self.backward = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.skip_back),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        self.play_pause = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.play, style_classes=["play-pause"]),
            style_classes=["play-pause"],
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        self.forward = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.skip_forward),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        self.next = Button(
            name="player-btn",
            child=Label(name="player-btn-label", markup=icons.next),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
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

        self.p_children=[
            self.overlay_container,
            self.title,
            self.album,
            self.artist,
            self.btn_box,
            self.time,
        ] if not vertical_mode else [
            self.overlay_container,
            Box(
                orientation="v",
                spacing=4,
                h_expand=True,
                h_align="fill",
                v_expand=False,
                v_align="center",
                children=[
                    self.title,
                    self.album,
                    self.btn_box,
                    self.artist,
                    self.time,
                ]
            )
        ]

        self.player_box = Box(
            name="player-box",
            orientation="v" if not vertical_mode else "h",
            v_align="center",
            spacing=4,
            children=self.p_children,
        )
        self.add(self.player_box)
        if mpris_player:
            self._apply_mpris_properties()
            self.prev.connect("clicked", self._on_prev_clicked)
            self.play_pause.connect("clicked", self._on_play_pause_clicked)
            self.backward.connect("clicked", self._on_backward_clicked)
            self.forward.connect("clicked", self._on_forward_clicked)
            self.next.connect("clicked", self._on_next_clicked)
            self.mpris_player.connect("changed", self._on_mpris_changed)
        else:
            self.play_pause.get_child().set_markup(icons.stop)
            self.play_pause.add_style_class("stop")

            self.backward.add_style_class("disabled")
            self.forward.add_style_class("disabled")
            self.prev.add_style_class("disabled")
            self.next.add_style_class("disabled")
            self.progressbar.set_value(0.0)
            self.time.set_text("--:-- / --:--")

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
        can_seek = hasattr(mp, "can_seek") and mp.can_seek

        if player_name == "firefox" or not can_seek:

            self.backward.add_style_class("disabled")
            self.forward.add_style_class("disabled")
            self.progressbar.set_value(0.0)
            self.time.set_text("--:-- / --:--")

            if self._progress_timer_id:
                GLib.source_remove(self._progress_timer_id)
                self._progress_timer_id = None
        else:

            self.backward.remove_style_class("disabled")
            self.forward.remove_style_class("disabled")

            if not self._progress_timer_id:
                self._progress_timer_id = GLib.timeout_add(1000, self._update_progress)

            self._update_progress()

        if hasattr(mp, "can_go_previous") and mp.can_go_previous:
             self.prev.remove_style_class("disabled")
        else:
             self.prev.add_style_class("disabled")

        if hasattr(mp, "can_go_next") and mp.can_go_next:
             self.next.remove_style_class("disabled")
        else:
             self.next.add_style_class("disabled")

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
            self.play_pause.add_style_class("playing")
        else:
            self.play_pause.get_child().set_markup(icons.play)
            self.play_pause.remove_style_class("playing")

    def on_wallpaper_changed(self, monitor, file, other_file, event):
        self.cover.set_image_from_file(os.path.expanduser("~/.current.wall"))

    def _on_prev_clicked(self, button):
        if self.mpris_player:
            self.mpris_player.previous()

    def _on_play_pause_clicked(self, button):
        if self.mpris_player:
            self.mpris_player.play_pause()
            self.update_play_pause_icon()

    def _on_backward_clicked(self, button):

        if self.mpris_player and self.mpris_player.can_seek and "disabled" not in self.backward.get_style_context().list_classes():
            new_pos = max(0, self.mpris_player.position - 5000000)
            self.mpris_player.position = new_pos

    def _on_forward_clicked(self, button):

        if self.mpris_player and self.mpris_player.can_seek and "disabled" not in self.forward.get_style_context().list_classes():
            new_pos = self.mpris_player.position + 5000000
            self.mpris_player.position = new_pos

    def _on_next_clicked(self, button):
        if self.mpris_player:
            self.mpris_player.next()

    def _update_progress(self):

        if not self.mpris_player:

            if self._progress_timer_id:
                GLib.source_remove(self._progress_timer_id)
                self._progress_timer_id = None
            return False

        try:
            current = self.mpris_player.position
        except Exception:
            current = 0
        try:
            total = int(self.mpris_player.length or 0)
        except Exception:
            total = 0

        if total <= 0:
            progress = 0.0
            self.time.set_text("--:-- / --:--")

        else:
            progress = (current / total)
            self.time.set_text(f"{self._format_time(current)} / {self._format_time(total)}")

        self.progressbar.set_value(progress)
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

        if not hasattr(self, "_update_pending") or not self._update_pending:
            self._update_pending = True

            GLib.idle_add(self._apply_mpris_properties_debounced)

    def _apply_mpris_properties_debounced(self):

        if self.mpris_player:
            self._apply_mpris_properties()
        else:

            if self._progress_timer_id:
                GLib.source_remove(self._progress_timer_id)
                self._progress_timer_id = None
        self._update_pending = False
        return False

class Player(Box):
    def __init__(self):
        super().__init__(name="player", orientation="v", h_align="fill", spacing=0, h_expand=False, v_expand=not vertical_mode)
        self.player_stack = Stack(
            name="player-stack",
            transition_type="slide-left-right",
            transition_duration=500,
            v_align="center",
            v_expand=not vertical_mode,
        )
        self.switcher = Gtk.StackSwitcher(
            name="player-switcher" if not vertical_mode else "player-switcher-vertical",
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
        super().__init__(name="player-small", orientation="h", h_align="fill", v_align="center")
        self._show_artist = False
        self._display_options = ["cavalcade", "title", "artist"]
        self._display_index = 0
        self._current_display = "cavalcade"

        self.mpris_icon = Button(
            name="compact-mpris-icon",
            h_align="center",
            v_align="center",
            child=Label(name="compact-mpris-icon-label", markup=icons.disc)
        )

        self.mpris_icon.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.mpris_icon.connect("button-press-event", self._on_icon_button_press)

        child = self.mpris_icon.get_child()
        child.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        child.connect("button-press-event", lambda widget, event: True)

        add_hover_cursor(self.mpris_icon)

        self.mpris_label = Label(
            name="compact-mpris-label",
            label="Nothing Playing",
            ellipsization="end",
            max_chars_width=26,
            h_align="center",
        )
        self.mpris_button = Button(
            name="compact-mpris-button",
            h_align="center",
            v_align="center",
            child=Label(name="compact-mpris-button-label", markup=icons.play)
        )
        self.mpris_button.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.mpris_button.connect("button-press-event", self._on_play_pause_button_press)

        add_hover_cursor(self.mpris_button)

        self.cavalcade = SpectrumRender()
        self.cavalcade_box = self.cavalcade.get_spectrum_box()

        self.center_stack = Stack(
            name="compact-mpris",
            transition_type="crossfade",
            transition_duration=100,
            v_align="center",
            v_expand=False,
            children=[
                self.cavalcade_box,
                self.mpris_label,
            ]
        )
        self.center_stack.set_visible_child(self.cavalcade_box)

        self.mpris_small = CenterBox(
            name="compact-mpris",
            orientation="h",
            h_expand=True,
            h_align="fill",
            v_align="center",
            v_expand=False,
            start_children=self.mpris_icon,
            center_children=self.center_stack,
            end_children=self.mpris_button,
        )

        self.add(self.mpris_small)

        self.mpris_manager = MprisPlayerManager()
        self.mpris_player = None

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
            if self._current_display != "cavalcade":
                self.center_stack.set_visible_child(self.mpris_label)
            else:
                self.center_stack.set_visible_child(self.cavalcade_box)
            return

        mp = self.mpris_player

        player_name = mp.player_name.lower() if hasattr(mp, "player_name") and mp.player_name else ""
        icon_markup = get_player_icon_markup_by_name(player_name)
        self.mpris_icon.get_child().set_markup(icon_markup)
        self.update_play_pause_icon()

        if self._current_display == "title":
            text = (mp.title if mp.title and mp.title.strip() else "Nothing Playing")
            self.mpris_label.set_text(text)
            self.center_stack.set_visible_child(self.mpris_label)
        elif self._current_display == "artist":
            text = (mp.artist if mp.artist else "Nothing Playing")
            self.mpris_label.set_text(text)
            self.center_stack.set_visible_child(self.mpris_label)
        else:
            self.center_stack.set_visible_child(self.cavalcade_box)

    def _on_icon_button_press(self, widget, event):
        from gi.repository import Gdk
        if event.type == Gdk.EventType.BUTTON_PRESS:
            players = self.mpris_manager.players
            if not players:
                return True

            if event.button == 2:
                self._display_index = (self._display_index + 1) % len(self._display_options)
                self._current_display = self._display_options[self._display_index]
                self._apply_mpris_properties()
                return True

            if event.button == 1:
                self.current_index = (self.current_index + 1) % len(players)
            elif event.button == 3:
                self.current_index = (self.current_index - 1) % len(players)
                if self.current_index < 0:
                    self.current_index = len(players) - 1

            mp_new = MprisPlayer(players[self.current_index])
            self.mpris_player = mp_new

            self.mpris_player.connect("changed", self._on_mpris_changed)
            self._apply_mpris_properties()
            return True
        return True

    def _on_play_pause_button_press(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 1:
                if self.mpris_player:
                    self.mpris_player.previous()
                    self.mpris_button.get_child().set_markup(icons.prev)
                    GLib.timeout_add(500, self._restore_play_pause_icon)
            elif event.button == 3:
                if self.mpris_player:
                    self.mpris_player.next()
                    self.mpris_button.get_child().set_markup(icons.next)
                    GLib.timeout_add(500, self._restore_play_pause_icon)
            elif event.button == 2:
                if self.mpris_player:
                    self.mpris_player.play_pause()
                    self.update_play_pause_icon()
            return True
        return True

    def _restore_play_pause_icon(self):
        self.update_play_pause_icon()
        return False

    def _on_icon_clicked(self, widget):
        pass

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

        self._apply_mpris_properties()

    def on_player_appeared(self, manager, player):

        if not self.mpris_player:
            mp = MprisPlayer(player)
            self.mpris_player = mp
            self._apply_mpris_properties()
            self.mpris_player.connect("changed", self._on_mpris_changed)

    def on_player_vanished(self, manager, player_name):
        players = self.mpris_manager.players
        if players and self.mpris_player and self.mpris_player.player_name == player_name:
            if players:
                self.current_index = self.current_index % len(players)
                new_player = MprisPlayer(players[self.current_index])
                self.mpris_player = new_player
                self.mpris_player.connect("changed", self._on_mpris_changed)
            else:
                self.mpris_player = None
        elif not players:
            self.mpris_player = None
        self._apply_mpris_properties()
