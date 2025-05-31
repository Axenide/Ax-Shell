from quopri import HEX
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.scale import Scale
import threading
from fabric import Fabricator
from python_hue_v2 import Hue
import modules.icons as icons
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import numpy as np
import cairo
import modules.icons as icons


class Light(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="hue",
            spacing=8,
            orientation="h",
            **kwargs,
        )
        self.widgets = kwargs["widgets"]

        self.scale_height = 3.1 #310 pixels

        self.wheel_width = 300
        self.wheel_height = 300

        self.buttons = self.widgets.buttons.light_button
        self.light_status_text = self.buttons.light_status_text
        self.light_status_button = self.buttons.light_status_button
        self.light_icon = self.buttons.light_icon
        self.light_label = self.buttons.light_label
        self.light_menu_button = self.buttons.light_menu_button
        self.light_menu_label = self.buttons.light_menu_label

        self.hue = Hue('192.168.10.71', 'OAVsJnfaX476yAFsBt7ES3voatlCWPay43b3arxK')  # create Hue instance, ip address, key

        self.bulb = self.hue.lights[0]

        self.color_wheel = ColorWheel(self.hue, self.wheel_width, self.wheel_height)

        self.brightness = Scale(
            name="brightness-bar",
            min=0.0,
            orientation='vertical',
            inverted=True,
            markup=icons.bulb
        )
        self.brightness.max_value = 100.0
        
        self.status_light()

        if self.bulb.on:
            self.brightness.value = self.bulb.brightness
        else:
            self.brightness.value = 0

        self.last_update = [self.bulb.on, self.brightness.value]

        GLib.timeout_add_seconds(5, self.fetch_status)

        self.brightness.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_MOTION_MASK| Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.brightness.connect("button-press-event", self.on_click)
        self.brightness.connect("motion-notify-event", self.on_drag)
        self.brightness.connect("button-release-event", self.on_release)

        self.add(self.color_wheel)
        self.add(self.brightness)

    def on_click(self, widget, event):
        if event.button == 1:
            self.brightness.value = 100 - event.y/self.scale_height
            self.last_update[1] = 100 - event.y/self.scale_height

    def on_drag(self, widget, event):
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            self.brightness.value = 100 - event.y/self.scale_height
            self.last_update[1] = 100 - event.y/self.scale_height

    def on_release(self, widget, event):
        if event.button == 1:
            if 5 <= self.brightness.value:
                if not self.bulb.on:
                    self.bulb.on = True
                self.bulb.brightness = self.brightness.value
                self.last_update[1] = self.brightness.value
            else:
                self.bulb.on = False

    def fetch_status(self):
        threading.Thread(target=self._fetch_status_thread, daemon=True).start()
        return True

    def _fetch_status_thread(self):
        if self.bulb.brightness != self.last_update[1]:
            if not Gdk.ModifierType.BUTTON1_MASK:
                self.brightness.value = self.bulb.brightness if 5 <= self.bulb.brightness and self.bulb.on else 0
                self.last_update[1] = self.bulb.brightness
        if self.bulb.on != self.last_update[0]:
            self.last_update[0] = False if self.last_update[0] else True
            GLib.idle_add(self.status_light)

    def switch(self):
        self.bulb.on = False if self.bulb.on else True
        self.status_light()

    def status_light(self):
        if self.bulb.on:
            self.light_status_text.set_label("on")
            for i in [self.light_status_button, self.light_status_text, self.light_icon, self.light_label, self.light_menu_button, self.light_menu_label, self.brightness]:
                i.remove_style_class("disabled")
            self.light_icon.set_markup(icons.bulb)
        else:
            self.light_status_text.set_label("off")
            for i in [self.light_status_button, self.light_status_text, self.light_icon, self.light_label, self.light_menu_button, self.light_menu_label, self.brightness]:
                i.add_style_class("disabled")
            self.light_icon.set_markup(icons.bulb_off)

    def set_brightness(self, range_value, scroll, value : float):
        match scroll:
            case scroll.JUMP:
                if 5 <= value:
                    if not self.bulb.on:
                        self.bulb.on = True
                    self.bulb.brightness = value
                else:
                    self.bulb.on = False

class ColorWheel(Gtk.DrawingArea):
    def __init__(self, hue, width, height):
        super().__init__()
        self.wheel_width = width
        self.wheel_height = height
        self.set_size_request(self.wheel_width+50, self.wheel_height)
        self.connect("draw", self.on_draw)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_MOTION_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect("button-press-event", self.on_click)
        self.connect("motion-notify-event", self.on_drag)
        self.connect("button-release-event", self.on_release)
        self.surface = None
        self.dot_position = None


        self.hue = hue
        self.bulb = self.hue.lights[0]

        self.set_dot_position(self.wheel_width/2, self.wheel_height/2)
        self.create_surface() # Do it right away because it lagg

    def create_surface(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.wheel_width, self.wheel_height)
        cr = cairo.Context(self.surface)
        self.draw_wheel(cr, self.wheel_width, self.wheel_height)

    def draw_wheel(self, cr, width, height):
        radius = min(width, height) / 2
        cx, cy = width / 2, height / 2

        for y in range(height):
            for x in range(width):
                dx = x - cx
                dy = y - cy
                distance = np.sqrt(dx**2 + dy**2)

                if distance <= radius:
                    angle = np.arctan2(dy, dx) + np.pi
                    hue = angle / (2 * np.pi)
                    whiteness = (radius - distance) / radius  # More white towards center
                    r, g, b = self.hsv_to_rgb(hue, 1, 1)
                    r = r + (1 - r) * whiteness
                    g = g + (1 - g) * whiteness
                    b = b + (1 - b) * whiteness

                    cr.set_source_rgb(r, g, b)
                    cr.rectangle(x, y, 1, 1)
                    cr.fill()

    def on_draw(self, widget, cr):
        if self.surface is None:
            self.create_surface()
        cr.set_source_surface(self.surface, 0, 0)
        cr.paint()

        if self.dot_position:
            cr.set_source_rgb(0, 0, 0)
            cr.arc(self.dot_position[0], self.dot_position[1], 5, 0, 2 * np.pi)
            cr.fill()

    def hsv_to_rgb(self, h, s, v):
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i %= 6
        if i == 0: return v, t, p
        if i == 1: return q, v, p
        if i == 2: return p, v, t
        if i == 3: return p, q, v
        if i == 4: return t, p, v
        if i == 5: return v, p, q

    def get_color_at(self, x, y):
        radius = min(self.wheel_width, self.wheel_height) / 2
        cx, cy = self.wheel_width / 2, self.wheel_height / 2

        dx = self.dot_position[0] - cx
        dy = self.dot_position[1] - cy
        distance = np.sqrt(dx**2 + dy**2)

        if distance <= radius:
            angle = np.arctan2(dy, dx) + np.pi
            hue = angle / (2 * np.pi)
            whiteness = (radius - distance) / radius  # More white towards center
            r, g, b = self.hsv_to_rgb(hue, 1, 1)
            r = r + (1 - r) * whiteness
            g = g + (1 - g) * whiteness
            b = b + (1 - b) * whiteness

            self.set_color([r,g,b])
        return None

    def rgb_to_xy(self, r, g, b):
        r = r / 255.0
        g = g / 255.0
        b = b / 255.0

        X = r * 0.664511 + g * 0.154324 + b * 0.162028
        Y = r * 0.283881 + g * 0.668433 + b * 0.047685
        Z = r * 0.000088 + g * 0.072310 + b * 0.986039

        if (X + Y + Z) == 0:
            return (0, 0)

        return (X / (X + Y + Z), Y / (X + Y + Z))

    def on_click(self, widget, event):
        self.set_dot_position(event.x, event.y)

    def on_drag(self, widget, event):
        self.set_dot_position(event.x, event.y)

    def on_release(self, widget, event):
        color = self.get_color_at(event.x, event.y)
        if color:
            print(f"Selected color: RGB{color}")
        self.queue_draw()

    def set_dot_position(self, x, y):
        radius = min(self.wheel_width, self.wheel_height) / 2
        cx, cy = self.wheel_width / 2, self.wheel_height / 2

        dx = x - cx
        dy = y - cy
        distance = np.sqrt(dx**2 + dy**2)

        if distance <= radius:
            self.dot_position = (x, y)
        else:
            angle = np.arctan2(dy, dx)
            self.dot_position = (cx + radius * np.cos(angle), cy + radius * np.sin(angle))
        self.queue_draw()

    def set_color(self, rgb):
        xy = self.rgb_to_xy(rgb[0], rgb[1], rgb[2])
        xy = {'x':xy[0], 'y':xy[1]}
        self.bulb.color_xy = xy

    def get_color_from_bulb(self, bri=1):
        xy = self.bulb.color_xy
        return self._get_rgb_from_xy(xy['x'], xy['y'], bri=bri)

    def _get_rgb_from_xy(self,x, y, bri):
        r = self.hsv_to_rgb(x, 1, 1)[0] + (1 - self.hsv_to_rgb(x, 1, 1)[0]) * bri
        g = self.hsv_to_rgb(x, 1, 1)[1] + (1 - self.hsv_to_rgb(x, 1, 1)[1]) * bri
        b = self.hsv_to_rgb(x, 1, 1)[2] + (1 - self.hsv_to_rgb(x, 1, 1)[2]) * bri
        return round(r*255), round(g*255), round(b*255)
