from gi.repository import Gdk, GObject, Gtk
import re
from collections.abc import Iterable
from enum import Enum
from typing import Literal, cast

import cairo
import gi
from fabric.core.service import Property
from fabric.utils.helpers import extract_css_values, get_enum_member
from fabric.widgets.window import Window
from loguru import logger

gi.require_version("Gtk", "3.0")

try:
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
except:
    raise ImportError(
        "looks like we don't have gtk-layer-shell installed, make sure to install it first (as well as using wayland)"
    )


class WaylandWindowExclusivity(Enum):
    NONE = 1
    NORMAL = 2
    AUTO = 3


class Layer(GObject.GEnum):
    BACKGROUND = 0
    BOTTOM = 1
    TOP = 2
    OVERLAY = 3
    ENTRY_NUMBER = 4


class KeyboardMode(GObject.GEnum):
    NONE = 0
    EXCLUSIVE = 1
    ON_DEMAND = 2
    ENTRY_NUMBER = 3


class Edge(GObject.GEnum):
    LEFT = 0
    RIGHT = 1
    TOP = 2
    BOTTOM = 3
    ENTRY_NUMBER = 4


class WaylandWindow(Window):
    @Property(
        Layer,
        flags="read-write",
        default_value=Layer.TOP,
    )
    def layer(self) -> Layer:  # type: ignore
        return self._layer  # type: ignore

    @layer.setter
    def layer(
        self,
        value: Literal["background", "bottom", "top", "overlay"] | Layer,
    ) -> None:
        self._layer = get_enum_member(Layer, value, default=Layer.TOP)
        return GtkLayerShell.set_layer(self, self._layer)

    @Property(int, "read-write")
    def monitor(self) -> int:
        if not (monitor := cast(Gdk.Monitor, GtkLayerShell.get_monitor(self))):
            return -1
        display = monitor.get_display() or Gdk.Display.get_default()
        for i in range(0, display.get_n_monitors()):
            if display.get_monitor(i) is monitor:
                return i
        return -1

    @monitor.setter
    def monitor(self, monitor: int | Gdk.Monitor) -> bool:
        if isinstance(monitor, int):
            display = Gdk.Display().get_default()
            monitor = display.get_monitor(monitor)
        return (
            (GtkLayerShell.set_monitor(self, monitor), True)[1]
            if monitor is not None
            else False
        )

    @Property(WaylandWindowExclusivity, "read-write")
    def exclusivity(self) -> WaylandWindowExclusivity:
        return self._exclusivity

    @exclusivity.setter
    def exclusivity(
        self, value: Literal["none", "normal", "auto"] | WaylandWindowExclusivity
    ) -> None:
        value = get_enum_member(
            WaylandWindowExclusivity, value, default=WaylandWindowExclusivity.NONE
        )
        self._exclusivity = value
        match value:
            case WaylandWindowExclusivity.NORMAL:
                return GtkLayerShell.set_exclusive_zone(self, True)
            case WaylandWindowExclusivity.AUTO:
                return GtkLayerShell.auto_exclusive_zone_enable(self)
            case _:
                return GtkLayerShell.set_exclusive_zone(self, False)

    @Property(bool, "read-write", default_value=False)
    def pass_through(self) -> bool:
        return self._pass_through

    @pass_through.setter
    def pass_through(self, pass_through: bool = False):
        self._pass_through = pass_through
        region = cairo.Region() if pass_through is True else None
        self.input_shape_combine_region(region)
        del region
        return

    @Property(
        KeyboardMode,
        "read-write",
        default_value=KeyboardMode.NONE,
    )
    def keyboard_mode(self) -> KeyboardMode:
        return self._keyboard_mode

    @keyboard_mode.setter
    def keyboard_mode(
        self,
        value: Literal[
            "none",
            "exclusive",
            "on-demand",
            "entry-number",
        ]
        | KeyboardMode,
    ):
        self._keyboard_mode = get_enum_member(
            KeyboardMode, value, default=KeyboardMode.NONE
        )
        return GtkLayerShell.set_keyboard_mode(self, self._keyboard_mode)

    @Property(tuple[Edge, ...], "read-write")
    def anchor(self):
        return tuple(
            x
            for x in [
                Edge.TOP,
                Edge.RIGHT,
                Edge.BOTTOM,
                Edge.LEFT,
            ]
            if GtkLayerShell.get_anchor(self, x)
        )

    @anchor.setter
    def anchor(self, value: str | Iterable[Edge]) -> None:
        self._anchor = value
        if isinstance(value, (list, tuple)) and all(
            isinstance(edge, Edge) for edge in value
        ):
            for edge in [
                Edge.TOP,
                Edge.RIGHT,
                Edge.BOTTOM,
                Edge.LEFT,
            ]:
                if edge not in value:
                    GtkLayerShell.set_anchor(self, edge, False)
                GtkLayerShell.set_anchor(self, edge, True)
            return
        elif isinstance(value, str):
            for edge, anchored in WaylandWindow.extract_edges_from_string(
                value
            ).items():
                GtkLayerShell.set_anchor(self, edge, anchored)

        return

    @Property(tuple[int, ...], flags="read-write")
    def margin(self) -> tuple[int, ...]:
        return tuple(
            GtkLayerShell.get_margin(self, x)
            for x in [
                Edge.TOP,
                Edge.RIGHT,
                Edge.BOTTOM,
                Edge.LEFT,
            ]
        )

    @margin.setter
    def margin(self, value: str | Iterable[int]) -> None:
        for edge, mrgv in WaylandWindow.extract_margin(value).items():
            GtkLayerShell.set_margin(self, edge, mrgv)
        return

    @Property(object, "read-write")
    def keyboard_mode(self):
        kb_mode = GtkLayerShell.get_keyboard_mode(self)
        if GtkLayerShell.get_keyboard_interactivity(self):
            kb_mode = KeyboardMode.EXCLUSIVE
        return kb_mode

    @keyboard_mode.setter
    def keyboard_mode(
        self,
        value: Literal["none", "exclusive", "on-demand"] | KeyboardMode,
    ):
        return GtkLayerShell.set_keyboard_mode(
            self,
            get_enum_member(
                KeyboardMode,
                value,
                default=KeyboardMode.NONE,
            ),
        )

    def __init__(
        self,
        layer: Literal["background", "bottom", "top", "overlay"] | Layer = Layer.TOP,
        anchor: str = "",
        margin: str | Iterable[int] = "0px 0px 0px 0px",
        exclusivity: Literal["auto", "normal", "none"]
        | WaylandWindowExclusivity = WaylandWindowExclusivity.NONE,
        keyboard_mode: Literal["none", "exclusive", "on-demand"]
        | KeyboardMode = KeyboardMode.NONE,
        pass_through: bool = False,
        monitor: int | Gdk.Monitor | None = None,
        title: str = "fabric",
        type: Literal["top-level", "popup"] | Gtk.WindowType = Gtk.WindowType.TOPLEVEL,
        child: Gtk.Widget | None = None,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        v_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        Window.__init__(
            self,
            title=title,
            type=type,
            child=child,
            name=name,
            visible=False,
            all_visible=False,
            style=style,
            style_classes=style_classes,
            tooltip_text=tooltip_text,
            tooltip_markup=tooltip_markup,
            h_align=h_align,
            v_align=v_align,
            h_expand=h_expand,
            v_expand=v_expand,
            size=size,
            **kwargs,
        )
        self._layer = Layer.ENTRY_NUMBER
        self._keyboard_mode = KeyboardMode.NONE
        self._anchor = anchor
        self._exclusivity = WaylandWindowExclusivity.NONE
        self._pass_through = pass_through

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, title)
        self.connect(
            "notify::title",
            lambda *_: GtkLayerShell.set_namespace(self, self.get_title()),
        )
        if monitor is not None:
            self.monitor = monitor
        self.layer = layer
        self.anchor = anchor
        self.margin = margin
        self.keyboard_mode = keyboard_mode
        self.exclusivity = exclusivity
        self.pass_through = pass_through
        self.show_all() if all_visible is True else self.show() if visible is True else None

    def steal_input(self) -> None:
        return GtkLayerShell.set_keyboard_interactivity(self, True)

    def return_input(self) -> None:
        return GtkLayerShell.set_keyboard_interactivity(self, False)

    # custom overrides
    def show(self) -> None:
        super().show()
        return self.do_handle_post_show_request()

    def show_all(self) -> None:
        super().show_all()
        return self.do_handle_post_show_request()

    def do_handle_post_show_request(self) -> None:
        if not self.get_children():
            logger.warning(
                "[WaylandWindow] showing an empty window is not recommended, some compositors might freak out."
            )
        self.pass_through = self._pass_through
        return

    @staticmethod
    def extract_anchor_values(string: str) -> tuple[str, ...]:
        """
        extracts the geometry values from a given geometry string.

        :param string: the string containing the geometry values.
        :type string: str
        :return: a list of unique directions extracted from the geometry string.
        :rtype: list
        """
        direction_map = {"l": "left", "t": "top", "r": "right", "b": "bottom"}
        pattern = re.compile(r"\b(left|right|top|bottom)\b", re.IGNORECASE)
        matches = pattern.findall(string)
        return tuple(set(tuple(direction_map[match.lower()[0]] for match in matches)))

    @staticmethod
    def extract_edges_from_string(string: str) -> dict["Edge", bool]:
        anchor_values = WaylandWindow.extract_anchor_values(string.lower())
        return {
            Edge.TOP: "top" in anchor_values,
            Edge.RIGHT: "right" in anchor_values,
            Edge.BOTTOM: "bottom" in anchor_values,
            Edge.LEFT: "left" in anchor_values,
        }

    @staticmethod
    def extract_margin(input: str | Iterable[int]) -> dict["Edge", int]:
        margins = (
            extract_css_values(input.lower())
            if isinstance(input, str)
            else input
            if isinstance(input, (tuple, list)) and len(input) == 4
            else (0, 0, 0, 0)
        )
        return {
            Edge.TOP: margins[0],
            Edge.RIGHT: margins[1],
            Edge.BOTTOM: margins[2],
            Edge.LEFT: margins[3],
        }
