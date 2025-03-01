from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.stack import Stack
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import GLib, Gtk, Vte, Pango
import modules.icons as icons
from modules.dashboard_modules.buttons import Buttons
from modules.calendar import Calendar
from modules.media import Media
from modules.cgmsugar import MyCgm
from modules.kanban import Kanban

class Widgets(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="dash-widgets",
            h_align="center",
            v_align="start",
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs["notch"]

        self.buttons = Buttons(notch=self.notch)

        self.box_1 = Media()

        self.box_2 = MyCgm()


        self.container_1 = Box(
            name="container-1",
            orientation="h",
            spacing=8,
            children=[
                self.box_2,
            ]
        )

        self.container_2 = Box(
            name="container-2",
            orientation="v",
            spacing=8,
            children=[
                self.buttons,
                self.container_1,
            ]
        )

        self.container_3 = Box(
            name="container-3",
            orientation="h",
            spacing=8,
            children=[
                self.box_1,
                self.container_2,
            ]
        )

        self.add(self.container_3)

        self.show_all()
