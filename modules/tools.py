from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.utils.helpers import exec_shell_command_async, get_relative_path
import modules.icons as icons
from gi.repository import Gdk, GLib
import config.data as data
import subprocess

SCREENSHOT_SCRIPT = get_relative_path("../scripts/screenshot.sh")
OCR_SCRIPT = get_relative_path("../scripts/ocr.sh")
SCREENRECORD_SCRIPT = get_relative_path("../scripts/screenrecord.sh")

class Toolbox(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="toolbox",
            orientation="h",
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        self.notch = kwargs["notch"]

        self.btn_ssregion = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.ssregion),
            on_clicked=self.ssregion,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_ssfull = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.ssfull),
            on_clicked=self.ssfull,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_screenrecord = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.screenrecord),
            on_clicked=self.screenrecord,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_ocr = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.ocr),
            on_clicked=self.ocr,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_color = Button(
            name="toolbox-button",
            tooltip_text="Color Picker\nLeft Click: HEX\nMiddle Click: HSV\nRight Click: RGB\n\nKeyboard:\nReturn: HEX\nShift+Return: RGB\nCtrl+Return: HSV",
            child=Label(
                name="button-bar-label",
                markup=icons.colorpicker
            ),
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        # Enable keyboard focus for the colorpicker button.
        self.btn_color.set_can_focus(True)
        # Connect both mouse and keyboard events.
        self.btn_color.connect("button-press-event", self.colorpicker)
        self.btn_color.connect("key_press_event", self.colorpicker_key)

        self.btn_emoji = Button(
            name="toolbox-button",
            child=Label(name="button-label", markup=icons.emoji),
            on_clicked=self.emoji,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.buttons = [
            self.btn_ssregion,
            self.btn_ssfull,
            self.btn_screenrecord,
            self.btn_ocr,
            self.btn_color,
            self.btn_emoji,
        ]

        for button in self.buttons:
            self.add(button)

        self.show_all()

        # Start polling for process state every second.
        self.recorder_timer_id = GLib.timeout_add_seconds(1, self.update_screenrecord_state)

    def close_menu(self):
        self.notch.close_notch()

    # Action methods
    def ssfull(self, *args):
        exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} p")
        self.close_menu()

    def screenrecord(self, *args):
        # Launch screenrecord script in detached mode so that it remains running independently of this program.
        exec_shell_command_async(f"bash -c 'nohup bash {SCREENRECORD_SCRIPT} > /dev/null 2>&1 & disown'")
        self.close_menu()

    def ocr(self, *args):
        exec_shell_command_async(f"bash {OCR_SCRIPT} sf")
        self.close_menu()

    def ssregion(self, *args):
        exec_shell_command_async(f"bash {SCREENSHOT_SCRIPT} sf")
        self.close_menu()

    def colorpicker(self, button, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            cmd = {
                1: "-hex",   # Left click
                2: "-hsv",   # Middle click
                3: "-rgb"    # Right click
            }.get(event.button)
            
            if cmd:
                exec_shell_command_async(f"bash {get_relative_path('../scripts/hyprpicker.sh')} {cmd}")
                self.close_menu()

    def colorpicker_key(self, widget, event):
        if event.keyval in {Gdk.KEY_Return, Gdk.KEY_KP_Enter}:
            modifiers = event.get_state()
            cmd = "-hex"  # Default
            
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
        """
        Checks if the 'gpu-screen-recorder' process is running.
        If it is, updates the btn_screenrecord icon to icons.stop and adds the 'recording' style class.
        Otherwise, sets the icon back to icons.screenrecord and removes the 'recording' style class.
        This function is called periodically every second.
        """
        try:
            # Use pgrep with -f to check for the process name anywhere in the command line
            result = subprocess.run("pgrep -f gpu-screen-recorder", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            running = result.returncode == 0
        except Exception:
            running = False

        if running:
            self.btn_screenrecord.get_child().set_markup(icons.stop)
            self.btn_screenrecord.add_style_class("recording")
        else:
            self.btn_screenrecord.get_child().set_markup(icons.screenrecord)
            self.btn_screenrecord.remove_style_class("recording")
        
        # Return True to keep this callback active.
        return True

    def emoji(self, *args):
        self.notch.open_notch("emoji")
