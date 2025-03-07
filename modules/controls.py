import subprocess
from gi.repository import GLib, Gdk, Gtk
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
from fabric.audio.service import Audio
from fabric.widgets.button import Button
from fabric.widgets.overlay import Overlay
from fabric.widgets.eventbox import EventBox
from fabric.widgets.circularprogressbar import CircularProgressBar
from services.brightness import Brightness
import modules.icons as icons
import math
from gi.repository import GLib

def supports_backlight():
    try:
        output = subprocess.check_output(["brightnessctl", "-l"]).decode("utf-8").lower()
        return "backlight" in output
    except Exception:
        return False

# Global flag used to determine if brightness controls should be added.
BACKLIGHT_SUPPORTED = supports_backlight()

class VolumeSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = Audio()
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("vol")
        self.on_speaker_changed()

    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def on_value_changed(self, _):
        if self.audio.speaker:
            self.audio.speaker.volume = self.value * 100

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        self.value = self.audio.speaker.volume / 100

class MicSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        self.audio = Audio()
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.connect("value-changed", self.on_value_changed)
        self.add_style_class("mic")
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def on_value_changed(self, _):
        if self.audio.microphone:
            self.audio.microphone.volume = self.value * 100

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return
        self.value = self.audio.microphone.volume / 100


class BrightnessSlider(Scale):
    def __init__(self, **kwargs):
        super().__init__(
            name="control-slider",
            orientation="h",
            h_expand=True,
            has_origin=True,
            increments=(0.01, 0.1),
            **kwargs,
        )
        # If backlight isn't supported, do not proceed.
        if not BACKLIGHT_SUPPORTED:
            return

        self.brightness = Brightness.get_initial()
        self.brightness.connect("screen", self.on_brightness_changed)
        self.connect("value-changed", self.on_value_changed)
        self.on_brightness_changed()
        self.add_style_class("brightness")

        # Variables for debouncing
        self.timeout_id = None
        self.pending_value = None

    def on_value_changed(self, _):
        if self.brightness.max_screen != -1:
            new_brightness = int(self.value * self.brightness.max_screen)

            # Cancel any pending timeout
            try:
                if self.timeout_id:
                    GLib.source_remove(self.timeout_id)
            except Exception as e:
                pass
            # Store the pending value
            self.pending_value = new_brightness

            # Set a timeout to update brightness after 100ms
            self.timeout_id = GLib.timeout_add(100, self._update_brightness)

    def _update_brightness(self):
        # Apply the pending brightness value
        if self.pending_value is not None:
            self.brightness.screen_brightness = self.pending_value
            self.pending_value = None

        # Return False to ensure the timeout doesn't repeat
        self.timeout_id = None
        return False

    def on_brightness_changed(self, *args):
        if self.brightness.max_screen != -1:
            self.value = self.brightness.screen_brightness / self.brightness.max_screen


class VolumeSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-vol",    **kwargs)
        self.audio = Audio()
        self.progress_bar = CircularProgressBar(
            name="button-volume", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.vol_label = Label(name="vol-label", markup=icons.vol_high)
        self.vol_button = Button(
            on_clicked=self.toggle_mute,
            child=self.vol_label
        )
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=Overlay(
                child=self.progress_bar,
                overlays=self.vol_button
            ),
        )
        self.audio.connect("notify::speaker", self.on_new_speaker)
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        self.on_speaker_changed()
        # self.scroll_threshold = -80.0  # Ajusta este valor para modificar la sensibilidad
        self.add_events(
            Gdk.EventMask.SCROLL_MASK |
                Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        # self._scroll_accumulator = 10.0
    def on_new_speaker(self, *args):
        if self.audio.speaker:
            self.audio.speaker.connect("changed", self.on_speaker_changed)
            self.on_speaker_changed()

    def toggle_mute(self, event):
        current_stream = self.audio.speaker
        if current_stream:
            current_stream.muted = not current_stream.muted
            if current_stream.muted:
                self.vol_button.get_child().set_markup(icons.vol_off)
                self.progress_bar.add_style_class("muted")
                self.vol_label.add_style_class("muted")
            else:
                self.on_speaker_changed()
                self.progress_bar.remove_style_class("muted")
                self.vol_label.remove_style_class("muted")


    def on_scroll(self, _, event):
        if not self.audio.speaker:
            return

        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if abs(event.delta_y) > 0:
                self.audio.speaker.volume -= event.delta_y
            if abs(event.delta_x) > 0:
                self.audio.speaker.volume += event.delta_x

        # match event.direction:
        #     case 0:
        #         self.audio.speaker.volume += 1
        #     case 1:
        #         self.audio.speaker.volume -= 1
        # return

    def on_speaker_changed(self, *_):
        if not self.audio.speaker:
            return
        if self.audio.speaker.muted:
            self.vol_button.get_child().set_markup(icons.vol_off)
            self.progress_bar.add_style_class("muted")
            self.vol_label.add_style_class("muted")
            self.set_tooltip_text("0%")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.vol_label.remove_style_class("muted")
        self.set_tooltip_text(f"{round(self.audio.speaker.volume)}%")
        self.progress_bar.value = self.audio.speaker.volume / 100
        if self.audio.speaker.volume > 74:
            self.vol_button.get_child().set_markup(icons.vol_high)
        elif self.audio.speaker.volume > 0:
            self.vol_button.get_child().set_markup(icons.vol_medium)
        else:
            self.vol_button.get_child().set_markup(icons.vol_mute)

class MicSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-mic", **kwargs)

        self.audio = Audio()
        self.progress_bar = CircularProgressBar(
            name="button-mic", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.mic_label = Label(name="mic-label", markup=icons.mic)
        self.mic_button = Button(
            on_clicked=self.toggle_mute,
            child=self.mic_label
        )
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=Overlay(
                child=self.progress_bar,
                overlays=self.mic_button
            ),
        )
        self.audio.connect("notify::microphone", self.on_new_microphone)
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add_events(
            Gdk.EventMask.SCROLL_MASK |
                Gdk.EventMask.SMOOTH_SCROLL_MASK
        )

        self.add(self.event_box)
        self.on_microphone_changed()

    def on_new_microphone(self, *args):
        if self.audio.microphone:
            self.audio.microphone.connect("changed", self.on_microphone_changed)
            self.on_microphone_changed()

    def toggle_mute(self, event):
        current_stream = self.audio.microphone
        if current_stream:
            current_stream.muted = not current_stream.muted
            if current_stream.muted:
                self.mic_button.get_child().set_markup(icons.mic_mute)
                self.progress_bar.add_style_class("muted")
                self.mic_label.add_style_class("muted")
            else:
                self.on_microphone_changed()
                self.progress_bar.remove_style_class("muted")
                self.mic_label.remove_style_class("muted")

    def on_scroll(self, _, event):
        if not self.audio.microphone:
            return

        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if abs(event.delta_y) > 0:
                self.audio.microphone.volume -= event.delta_y
            if abs(event.delta_x) > 0:
                self.audio.microphone.volume += event.delta_x

    def on_microphone_changed(self, *_):
        if not self.audio.microphone:
            return
        if self.audio.microphone.muted:
            self.mic_button.get_child().set_markup(icons.mic_mute)
            self.progress_bar.add_style_class("muted")
            self.mic_label.add_style_class("muted")
            self.set_tooltip_text("0%")
            return
        else:
            self.progress_bar.remove_style_class("muted")
            self.mic_label.remove_style_class("muted")
        self.progress_bar.value = self.audio.microphone.volume / 100
        self.set_tooltip_text(f"{round(self.audio.microphone.volume)}%")

        if self.audio.microphone.volume >= 1:
            self.mic_button.get_child().set_markup(icons.mic)
        else:
            self.mic_button.get_child().set_markup(icons.mic_mute)

class BrightnessSmall(Box):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar-brightness", **kwargs)
        # Do not proceed if backlight is not supported.
        if not BACKLIGHT_SUPPORTED:
            return

        self.brightness = Brightness.get_initial()
        self.progress_bar = CircularProgressBar(
            name="button-brightness", size=28, line_width=2,
            start_angle=150, end_angle=390,
        )
        self.brightness_label = Label(name="brightness-label", markup=icons.brightness_high)
        self.brightness_button = Button(child=self.brightness_label)
        self.event_box = EventBox(
            events=["scroll", "smooth-scroll"],
            child=Overlay(
                child=self.progress_bar,
                overlays=self.brightness_button
            ),
        )
        self.brightness.connect("screen", self.on_brightness_changed)
        self.event_box.connect("scroll-event", self.on_scroll)
        self.add(self.event_box)
        self.on_brightness_changed()
        self.add_events(
            Gdk.EventMask.SCROLL_MASK |
                Gdk.EventMask.SMOOTH_SCROLL_MASK
        )

    def on_scroll(self, _, event):
        if self.brightness.max_screen == -1:
            return
        val_y = event.delta_y
        if val_y > 0:
            self.brightness.screen_brightness -= 1
        else:
            self.brightness.screen_brightness += 1

    def on_brightness_changed(self, *_):
        if self.brightness.max_screen == -1:
            return
        self.progress_bar.value = self.brightness.screen_brightness / self.brightness.max_screen
        brightness_percentage = (self.brightness.screen_brightness / self.brightness.max_screen) * 100
        if brightness_percentage > 74:
            self.brightness_label.set_markup(icons.brightness_high)
        elif brightness_percentage > 24:
            self.brightness_label.set_markup(icons.brightness_medium)
        else:
            self.brightness_label.set_markup(icons.brightness_low)

        self.set_tooltip_text(f"{round(brightness_percentage)}%")
# ControlSliders now only includes the brightness slider if supported.
class ControlSliders(Box):
    def __init__(self, **kwargs):
        children = []
        if BACKLIGHT_SUPPORTED:
            children.append(BrightnessSlider())
        children.extend([
            VolumeSlider(),
            MicSlider(),
        ])
        super().__init__(
            name="control-sliders",
            orientation="h",
            spacing=4,
            children=children,
            **kwargs,
        )
        self.show_all()

# ControlSmall now only includes the brightness small widget if supported.
class ControlSmall(Box):
    def __init__(self, **kwargs):
        children = []
        if BACKLIGHT_SUPPORTED:
            children.append(BrightnessSmall())
        children.extend([
            VolumeSmall(),
            MicSmall(),
        ])
        super().__init__(
            name="control-small",
            orientation="h",
            spacing=4,
            children=children,
            **kwargs,
        )
        self.show_all()


