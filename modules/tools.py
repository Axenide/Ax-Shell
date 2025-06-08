import os
import subprocess
import threading

from fabric.utils.helpers import exec_shell_command_async, get_relative_path
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label
from gi.repository import Gdk, GLib
from loguru import logger

import config.data as data
import modules.icons as icons

SCREENSHOT_SCRIPT = get_relative_path("../scripts/screenshot.sh")
POMODORO_SCRIPT = get_relative_path("../scripts/pomodoro.sh")
OCR_SCRIPT = get_relative_path("../scripts/ocr.sh")
GAMEMODE_SCRIPT = get_relative_path("../scripts/gamemode.sh")
SCREENRECORD_SCRIPT = get_relative_path("../scripts/screenrecord.sh")

# Tooltips
## Screenshot
tooltip_ssregion = """<b><u>Region Screenshot</u></b>
<b>Left Click:</b> Take a screenshot of a selected region.
<b>Right Click:</b> Take a mockup screenshot of a selected region."""

tooltip_ssfull = """<b><u>Screenshot</u></b>
<b>Left Click:</b> Take a fullscreen screenshot.
<b>Right Click:</b> Take a mockup fullscreen screenshot."""

tooltip_sswindow = """<b><u>Window Screenshot</u></b>
<b>Left Click:</b> Take a screenshot of the active window.
<b>Right Click:</b> Take a mockup screenshot of the active window."""

tooltip_screenshots = "<b>Screenshots Directory</b>"

tooltip_screenrecord = "<b>Screen Recorder</b>"
tooltip_recordings = "<b>Recordings Directory</b>"

tooltip_ocr = "<b>OCR</b>"
tooltip_colorpicker = """<b><u>Color Picker</u></b>
<b>Mouse:</b>
Left Click: HEX
Middle Click: HSV
Right Click: RGB

<b>Keyboard:</b>
Enter: HEX
Shift+Enter: RGB
Ctrl+Enter: HSV"""

tooltip_gamemode = "<b>Game Mode</b>"
tooltip_pomodoro = "<b>Pomodoro Timer</b>"
tooltip_emoji = "<b>Emoji Picker</b>"


class Toolbox(Box):
    def __init__(self, **kwargs):
        orientation = "h"
        if data.PANEL_THEME == "Panel" and (data.BAR_POSITION in ["Left", "Right"] or data.PANEL_POSITION in ["Start", "End"]):
            orientation = "v"

        super().__init__(
            name="toolbox",
            orientation=orientation,
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        self.notch = kwargs["notch"]

        self.btn_ssregion = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_ssregion,
            child=Label(name="button-label", markup=icons.ssregion),
            on_clicked=self.ssregion,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        self.btn_ssregion.set_can_focus(True)
        self.btn_ssregion.connect("button-press-event", self.on_ssregion_click)
        self.btn_ssregion.connect("key-press-event", self.on_ssregion_key)

        self.btn_ssfull = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_ssfull,
            child=Label(name="button-label", markup=icons.ssfull),
            on_clicked=self.ssfull,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_ssfull.set_can_focus(True) 
        self.btn_ssfull.connect("button-press-event", self.on_ssfull_click)
        self.btn_ssfull.connect("key-press-event", self.on_ssfull_key)

        self.btn_sswindow = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_sswindow,
            child=Label(name="button-label", markup=icons.sswindow),
            on_clicked=self.sswindow,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_sswindow.set_can_focus(True)
        self.btn_sswindow.connect("button-press-event", self.on_sswindow_click)
        self.btn_sswindow.connect("key-press-event", self.on_sswindow_key)

        self.btn_screenrecord = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_screenrecord,
            child=Label(name="button-label", markup=icons.screenrecord),
            on_clicked=self.screenrecord,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_ocr = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_ocr,
            child=Label(name="button-label", markup=icons.ocr),
            on_clicked=self.ocr,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_color = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_colorpicker,
            child=Label(
                name="button-bar-label",
                markup=icons.colorpicker
            ),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_gamemode = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_gamemode,
            child=Label(name="button-label", markup=icons.gamemode),
            on_clicked=self.gamemode,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_pomodoro = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_pomodoro,
            child=Label(name="button-label", markup=icons.timer_off),
            on_clicked=self.pomodoro,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_color.set_can_focus(True)

        self.btn_color.connect("button-press-event", self.colorpicker)
        self.btn_color.connect("key_press_event", self.colorpicker_key)

        self.btn_emoji = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_emoji,
            child=Label(name="button-label", markup=icons.emoji),
            on_clicked=self.emoji,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        
        self.btn_screenshots_folder = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_screenshots,
            child=Label(name="button-label", markup=icons.screenshots),
            on_clicked=self.open_screenshots_folder,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )
        
        self.btn_recordings_folder = Button(
            name="toolbox-button",
            tooltip_markup=tooltip_recordings,
            child=Label(name="button-label", markup=icons.recordings),
            on_clicked=self.open_recordings_folder,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.buttons = [
            self.btn_ssregion,
            self.btn_sswindow,
            self.btn_ssfull,
            self.btn_screenshots_folder,
            Box(name="tool-sep", h_expand=False, v_expand=False, h_align="center", v_align="center"),
            self.btn_screenrecord,
            self.btn_recordings_folder,
            Box(name="tool-sep", h_expand=False, v_expand=False, h_align="center", v_align="center"),
            self.btn_ocr,
            self.btn_color,
            Box(name="tool-sep", h_expand=False, v_expand=False, h_align="center", v_align="center"),
            self.btn_gamemode,
            self.btn_pomodoro,
            self.btn_emoji,
        ]

        for button in self.buttons:
            self.add(button)

        self.show_all()

        self.recorder_timer_id = GLib.timeout_add_seconds(1, self.update_screenrecord_state)
        self.gamemode_updater = GLib.timeout_add_seconds(1, self.gamemode_check)
        self.pomodoro_updater = GLib.timeout_add_seconds(1, self.pomodoro_check)

    def close_menu(self):
        self.notch.close_notch()

    def ssfull(self, *args, mockup=False):
        cmd = f"bash {SCREENSHOT_SCRIPT} p"
        if mockup:
            cmd += " mockup"
        exec_shell_command_async(cmd)
        self.close_menu()

    def on_ssfull_click(self, button, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 1:
                self.ssfull()
            elif event.button == 3:
                self.ssfull(mockup=True)
            return True
        return False

    def on_ssfull_key(self, widget, event):
        if event.keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter}:
            modifiers = event.get_state()
            if modifiers & Gdk.ModifierType.SHIFT_MASK:
                self.ssfull(mockup=True)
            else:
                self.ssfull()
            return True
        return False

    def ssregion(self, *args):
        exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} s")
        self.close_menu()

    def on_ssregion_click(self, button, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 1:
                self.ssregion()
            elif event.button == 3:
                exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} s mockup")
                self.close_menu()
            return True
        return False

    def on_ssregion_key(self, widget, event):
        if event.keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter}:
            modifiers = event.get_state()
            if modifiers & Gdk.ModifierType.SHIFT_MASK:
                exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} s mockup")
                self.close_menu()
            else:
                self.ssregion()
            return True
        return False

    def sswindow(self, *args):
        exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} w")
        self.close_menu()

    def on_sswindow_click(self, button, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 1:
                self.sswindow()
            elif event.button == 3:
                exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} w mockup")
                self.close_menu()
            return True
        return False

    def on_sswindow_key(self, widget, event):
        if event.keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter}:
            modifiers = event.get_state()
            if modifiers & Gdk.ModifierType.SHIFT_MASK:
                exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} w mockup")
                self.close_menu()
            else:
                self.sswindow()
            return True
        return False

    def screenrecord(self, *args):

        exec_shell_command_async(f"bash -c 'nohup bash {SCREENRECORD_SCRIPT} > /dev/null 2>&1 & disown'")
        self.close_menu()

    def pomodoro(self, *args):
        exec_shell_command_async(f"bash -c 'nohup bash {POMODORO_SCRIPT} > /dev/null 2>&1 & disown'")
        self.close_menu()

    def pomodoro_check(self):
        def check():
            try:
                result = subprocess.run("pgrep -f pomodoro.sh", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                running = result.returncode == 0
            except Exception:
                running = False

            def update_ui():
                if running:
                    self.btn_pomodoro.get_child().set_markup(icons.timer_on)
                    self.btn_pomodoro.add_style_class("pomodoro")
                else:
                    self.btn_pomodoro.get_child().set_markup(icons.timer_off)
                    self.btn_pomodoro.remove_style_class("pomodoro")
                return False
            GLib.idle_add(update_ui)
            return False
        GLib.idle_add(lambda: threading.Thread(target=check).start())
        return True

    def ocr(self, *args):
        exec_shell_command_async(f"bash {OCR_SCRIPT} s")
        self.close_menu()

    def gamemode(self, *args):
        exec_shell_command_async(f"bash {GAMEMODE_SCRIPT}")
        self.gamemode_check()
        self.close_menu()

    def gamemode_check(self):
        def check():
            try:
                result = subprocess.run(f"bash {GAMEMODE_SCRIPT} check", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                enabled = result.stdout == b't\n'
            except Exception:
                enabled = False

            def update_ui():
                if enabled:
                    self.btn_gamemode.get_child().set_markup(icons.gamemode_off)
                else:
                    self.btn_gamemode.get_child().set_markup(icons.gamemode)
                return False
            GLib.idle_add(update_ui)
            return False
        GLib.idle_add(lambda: threading.Thread(target=check).start())
        return True

    def colorpicker(self, button, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            cmd = {
                1: "-hex",
                2: "-hsv",
                3: "-rgb"
            }.get(event.button)
            
            if cmd:
                exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker.sh')} {cmd}")
                self.close_menu()

    def colorpicker_key(self, widget, event):
        if event.keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter}:
            modifiers = event.get_state()
            cmd = "-hex"
            
            match modifiers & (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK):
                case Gdk.ModifierType.SHIFT_MASK:
                    cmd = "-rgb"
                case Gdk.ModifierType.CONTROL_MASK:
                    cmd = "-hsv"
                
            exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker.sh')} {cmd}")
            self.close_menu()
            return True
        return False

    def update_screenrecord_state(self):
        def check():
            try:
                result = subprocess.run("pgrep -f gpu-screen-recorder", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                running = result.returncode == 0
            except Exception:
                running = False

            def update_ui():
                if running:
                    self.btn_screenrecord.get_child().set_markup(icons.stop)
                    self.btn_screenrecord.add_style_class("recording")
                else:
                    self.btn_screenrecord.get_child().set_markup(icons.screenrecord)
                    self.btn_screenrecord.remove_style_class("recording")
                return False
            GLib.idle_add(update_ui)
            return False
        GLib.idle_add(lambda: threading.Thread(target=check).start())
        return True

    def open_screenshots_folder(self, *args):
        screenshots_dir = os.path.join(os.environ.get('XDG_PICTURES_DIR', 
                                                    os.path.expanduser('~/Pictures')), 
                                     'Screenshots')

        os.makedirs(screenshots_dir, exist_ok=True)
        exec_shell_command_async(f"xdg-open {screenshots_dir}")
        self.close_menu()

    def open_recordings_folder(self, *args):
        recordings_dir = os.path.join(os.environ.get('XDG_VIDEOS_DIR', 
                                                   os.path.expanduser('~/Videos')), 
                                    'Recordings')

        os.makedirs(recordings_dir, exist_ok=True)
        exec_shell_command_async(f"xdg-open {recordings_dir}")
        self.close_menu()

    def emoji(self, *args):
        self.notch.open_notch("emoji")
