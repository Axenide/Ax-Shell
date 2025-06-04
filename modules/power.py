from fabric.utils.helpers import exec_shell_command_async
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.label import Label

import config.data as data
import modules.icons as icons

tooltip_lock = "Lock"
tooltip_suspend = "Suspend"
tooltip_logout = "Logout"
tooltip_reboot = "Reboot"
tooltip_shutdown = "Shutdown"


class PowerMenu(Box):
    def __init__(self, **kwargs):
        orientation = "h"
        if data.PANEL_THEME == "Panel" and (
            data.BAR_POSITION in ["Left", "Right"]
            or data.PANEL_POSITION in ["Start", "End"]
        ):
            orientation = "v"

        super().__init__(
            name="power-menu",
            orientation=orientation,
            spacing=4,
            v_align="center",
            h_align="center",
            visible=True,
            **kwargs,
        )

        self.notch = kwargs["notch"]

        self.btn_lock = Button(
            name="power-menu-button",
            tooltip_markup=tooltip_lock,
            child=Label(name="button-label", markup=icons.lock),
            on_clicked=self.lock,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_suspend = Button(
            name="power-menu-button",
            tooltip_markup=tooltip_suspend,
            child=Label(name="button-label", markup=icons.suspend),
            on_clicked=self.suspend,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_logout = Button(
            name="power-menu-button",
            tooltip_markup=tooltip_logout,
            child=Label(name="button-label", markup=icons.logout),
            on_clicked=self.logout,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_reboot = Button(
            name="power-menu-button",
            tooltip_markup=tooltip_reboot,
            child=Label(name="button-label", markup=icons.reboot),
            on_clicked=self.reboot,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.btn_shutdown = Button(
            name="power-menu-button",
            tooltip_markup=tooltip_shutdown,
            child=Label(name="button-label", markup=icons.shutdown),
            on_clicked=self.poweroff,
            h_expand=False,
            v_expand=False,
            h_align="center",
            v_align="center",
        )

        self.buttons = [
            self.btn_lock,
            self.btn_suspend,
            self.btn_logout,
            self.btn_reboot,
            self.btn_shutdown,
        ]

        for button in self.buttons:
            self.add(button)

        self.show_all()

    def close_menu(self):
        self.notch.close_notch()

    def lock(self, *args):
        print("Locking screen...")
        exec_shell_command_async("loginctl lock-session")
        self.close_menu()

    def suspend(self, *args):
        print("Suspending system...")
        exec_shell_command_async("systemctl suspend")
        self.close_menu()

    def logout(self, *args):
        print("Logging out...")
        exec_shell_command_async("hyprctl dispatch exit")
        self.close_menu()

    def reboot(self, *args):
        print("Rebooting system...")
        exec_shell_command_async("systemctl reboot")
        self.close_menu()

    def poweroff(self, *args):
        print("Powering off...")
        exec_shell_command_async("systemctl poweroff")
        self.close_menu()
