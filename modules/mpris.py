from fabric.utils import bulk_connect
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.overlay import Overlay
from fabric.utils import invoke_repeater

from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from loguru import logger
from gi.repository import GObject
from gi.repository import GLib

import modules.icons as icons
from gi.repository import Gtk, Gdk
from fabric.widgets.box import Box

from modules.cavalcade import Cava, Spectrum
from services.mpris import MprisPlayer, MprisPlayerManager



import subprocess

class Mpris(Box, GObject.GObject):
    """A widget to display the spectrum visualizer."""

    __gsignals__ = {

        'player-found': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'playback-started': (GObject.SIGNAL_RUN_FIRST, None, ())

    }

    def __init__(self, **kwargs):
        super().__init__(name="mpris", **kwargs)
        self.persistent = False

        self.player = None
        self.paused_icon = icons.music

        # Services
        self.spectrum_out = SpectrumRender()
        # self.spectrum_in = SpectrumRender(mode = 'in')
        

        self.mpris_manager = MprisPlayerManager()


        self.playing_box = self.get_spectrum_box()
        self.paused_button = Button(name="button-paused", child=Label(markup=""), on_clicked=lambda *_: self.play_pause())
       
        self.paused_revealer = Revealer()
        self.paused_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.paused_revealer.add(self.paused_button)
        self.paused_revealer.set_reveal_child(False)
        
        self.playing_revealer = Revealer()
        self.playing_revealer.set_transition_type(Gtk.RevealerTransitionType.CROSSFADE)
        self.playing_revealer.add(self.playing_box)
        self.playing_revealer.set_reveal_child(False)

        self.center_box = CenterBox()
        self.center_box.set_center_widget(self.playing_revealer)
        self.center_box.show_all()

        self.pack_start(self.center_box, True, False, 0)
        

        self.show_spectrum()


        # Check for players periodically
        invoke_repeater(5000, self.check_for_players, initial_call=True)



        # Add the drawing area to the Mpris container

    def check_for_players(self):
        for player in self.mpris_manager.players:
            if self.player is None or self.player.get_property('player-name') != player.get_property('player-name'):
                self.player = None
                logger.info(
                    f"[PLAYER MANAGER] player found: {player.get_property('player-name')}",
                )
                
                self.player = MprisPlayer(player)
                self.emit("player-found")
                self.player.connect("notify::playback-status", self.get_playback_status)
            else:
                return True
        return True

    def play_pause(self, *_):
        # Toggle play/pause using playerctl
        if self.player is not None:
            self.player.play_pause()

    def get_playback_status(self, *_):
        # Get the current playback status and change the display accordingly
        status = None
        if self.player is not None:
            status = self.player.playback_status.lower()

        self.playing_revealer.set_reveal_child(False)
        self.paused_revealer.set_reveal_child(False)
        
        self.emit("playback-started")

        if status == "playing":
            # Show the visualizer
            self.show_spectrum()


        elif status == "paused":
            self.paused_icon = icons.music
            if self.player.get_property('player-name') == 'firefox':
                self.paused_icon = icons.firefox
            if self.player.get_property('player-name') == 'spotify':
                self.paused_icon = icons.spotify

            title = self.paused_icon
            
            if self.player.title is not None:
                title = self.paused_icon + ' ' + self.player.title
                if len(self.player.title) > 24:
                    title = self.paused_icon + ' ' + self.player.title[:24] + '...'
                
            self.paused_button.get_child().set_markup(title)
            self.center_box.set_center_widget(self.paused_revealer)
            self.paused_revealer.set_reveal_child(True)
            self.show()
        else:
            self.show_spectrum()

    def get_spectrum_box(self):
        # Get the spectrum box
        box = Overlay(h_align='center', v_align='center')
        button = Button(on_clicked=lambda *_: self.play_pause())
        
        box.set_size_request(150, 40)  # Ajusta el tamaño según tus necesidades
        # box.add_overlay(self.spectrum_in.draw.area)
        box.add_overlay(self.spectrum_out.draw.area)
        box.add_overlay(button)
        return box

    def show_spectrum(self):
        # Show the visualizer
        self.center_box.set_center_widget(self.playing_revealer)
        self.playing_revealer.set_reveal_child(True)
        self.paused_revealer.set_reveal_child(False)
        self.show()

class SpectrumRender():
    def __init__(self, mode = None, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

      
        self.draw = Spectrum()
        self.cava = Cava(self)
        self.cava.start()
