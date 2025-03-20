import gi
gi.require_version('Gtk', '3.0')
from fabric.widgets.box import Box
from fabric.widgets.stack import Stack
from modules.buttons import Buttons
from modules.calendar import Calendar

#from modules.media import Media
from modules.cgmsugar import MyCgm
from modules.kanban import Kanban

from modules.player import Player
from modules.bluetooth import BluetoothConnections
from modules.hue import Light
from modules.metrics import Metrics
from modules.controls import ControlSliders

class Widgets(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="dash-widgets",
            h_align="fill",
            v_align="fill",
            h_expand=True,
            v_expand=True,
            visible=True,
            all_visible=True,
        )

        self.notch = kwargs["notch"]

        self.buttons = Buttons(widgets=self)
        self.bluetooth = BluetoothConnections(widgets=self)
        self.light = Light(widgets=self)

        self.box_1 = Box(
            name="box-1",
            h_expand=True,
            v_expand=True,
        )

        self.box_2 = Box(
            name="box-2",
            h_expand=True,
            v_expand=True,
        )

        self.box_3 = Box(
            name="box-3",
            v_expand=True,
        )

        self.controls = ControlSliders()

        self.player = Player()

        self.metrics = Metrics()

        self.cgm = MyCgm()

        self.notification_history = self.notch.notification_history

        self.applet_stack = Stack(
            h_expand=True,
            v_expand=True,
            transition_type="slide-left-right",
            children=[
                self.notification_history,
                self.bluetooth,
                self.light,
            ]
        )

        self.applet_stack_box = Box(
            name="applet-stack",
            h_expand=True,
            v_expand=True,
            children=[
                self.applet_stack,
            ]
        )

        self.container_1 = Box(
            name="container-1",
            h_expand=True,
            v_expand=True,
            orientation="h",
            spacing=8,
            children=[
                self.box_2,
                Box(
                    name="container-sub-1",
                    h_expand=True,
                    v_expand=True,
                    spacing=8,
                    children=[
                        self.cgm,
                        self.applet_stack_box,
                    ]
                ),
                self.metrics,
            ]
        )

        self.container_2 = Box(
            name="container-2",
            h_expand=True,
            v_expand=True,
            orientation="v",
            spacing=8,
            children=[
                self.buttons,
                self.controls,
                self.container_1,
            ]
        )

        self.container_3 = Box(
            name="container-3",
            h_expand=True,
            v_expand=True,
            orientation="h",
            spacing=8,
            children=[
                self.player,
                self.container_2,
            ]
        )

        self.add(self.container_3)

    def show_bt(self):
        self.applet_stack.set_visible_child(self.bluetooth)

    def show_notif(self):
        self.applet_stack.set_visible_child(self.notification_history)

    def show_light(self):
        self.applet_stack.set_visible_child(self.light)
