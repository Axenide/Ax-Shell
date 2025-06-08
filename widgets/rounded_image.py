import math
import cairo
from typing import cast
from fabric.widgets.image import Image
from gi.repository import Gtk


class CustomImage(Image):
    def do_render_rectangle(
        self, cr: cairo.Context, width: int, height: int, radius: int = 0
    ):
        cr.move_to(radius, 0)
        cr.line_to(width - radius, 0)
        cr.arc(width - radius, radius, radius, -(math.pi / 2), 0)
        cr.line_to(width, height - radius)
        cr.arc(width - radius, height - radius, radius, 0, (math.pi / 2))
        cr.line_to(radius, height)
        cr.arc(radius, height - radius, radius, (math.pi / 2), math.pi)
        cr.line_to(0, radius)
        cr.arc(radius, radius, radius, math.pi, (3 * (math.pi / 2)))
        cr.close_path()

    def do_draw(self, cr: cairo.Context):
        context = self.get_style_context()
        width, height = self.get_allocated_width(), self.get_allocated_height()
        cr.save()

        self.do_render_rectangle(
            cr,
            width,
            height,
            cast(int, context.get_property("border-radius", Gtk.StateFlags.NORMAL)),
        )
        cr.clip()
        Image.do_draw(self, cr)

        cr.restore()
