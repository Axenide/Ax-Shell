from os import truncate
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.stack import Stack
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.hyprland.widgets import ActiveWindow
from fabric.utils.helpers import FormattedString, truncate
from gi.repository import GLib, Gdk, Gtk, Pango
from modules.launcher import AppLauncher
from modules.dashboard import Dashboard
from modules.notifications import NotificationContainer
from modules.power import PowerMenu
from modules.overview import Overview
from modules.hue import Light
from modules.emoji import EmojiPicker
from modules.corners import MyCorner
import config.data as data
from modules.player import PlayerSmall
from modules.tools import Toolbox
from utils.icon_resolver import IconResolver
from fabric.utils.helpers import get_desktop_applications
from fabric.widgets.image import Image


class Notch(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="notch",
            layer="top",
            anchor="top center",
            margin="-40px 0px 0px 0px",
            keyboard_mode="none",
            exclusivity="normal",
            visible=True,
            all_visible=True,
        )

        self.bar = kwargs.get("bar", None)

        self.notification = NotificationContainer(notch=self)
        self.notification_history = self.notification.history

        self.icon_resolver = IconResolver()
        self._all_apps = get_desktop_applications()
        self.app_identifiers = self._build_app_identifiers_map()

        self.dashboard = Dashboard(notch=self)
        self.launcher = AppLauncher(notch=self)
        self.overview = Overview()
        self.emoji = EmojiPicker(notch=self)
        self.power = PowerMenu(notch=self)

        self.hue = Box()

        self.applet_stack = self.dashboard.widgets.applet_stack
        self.nhistory = self.applet_stack.get_children()[0]
        self.btdevices = self.applet_stack.get_children()[1]

        self.window_label = Label(
            name="notch-window-label",
            h_expand=True,
            h_align="fill",
        )

        self.window_icon = Image(
            name="notch-window-icon",
            icon_name="application-x-executable",
            icon_size=20
        )

        self.active_window = ActiveWindow(
            name="hyprland-window",
            h_expand=True,
            h_align="fill",
            formatter=FormattedString(
                f"{{'Desktop' if not win_title or win_title == 'unknown' else truncate(win_title, 64)}}",
                truncate=truncate,
            ),
        )
        
        self.active_window_box = CenterBox(
            name="active-window-box",
            h_expand=True,
            h_align="fill",
            start_children=self.window_icon,
            center_children=self.active_window,
            end_children=None
        )

        self.active_window_box.connect("button-press-event", lambda widget, event: (self.open_notch("dashboard"), False)[1])

        self.active_window.connect("notify::label", self.update_window_icon)

        self.active_window.get_children()[0].set_hexpand(True)
        self.active_window.get_children()[0].set_halign(Gtk.Align.FILL)
        self.active_window.get_children()[0].set_ellipsize(Pango.EllipsizeMode.END)

        self.active_window.connect("notify::label", lambda *_: self.restore_label_properties())

        self.player_small = PlayerSmall()
        self.user_label = Label(name="compact-user", label=f"{data.USERNAME}@{data.HOSTNAME}")

        self.player_small.mpris_manager.connect("player-appeared", lambda *_: self.compact_stack.set_visible_child(self.player_small))
        self.player_small.mpris_manager.connect("player-vanished", self.on_player_vanished)

        self.compact_stack = Stack(
            name="notch-compact-stack",
            v_expand=True,
            h_expand=True,
            transition_type="slide-up-down",
            transition_duration=100,
            children=[
                self.user_label,
                self.active_window_box,
                self.player_small,
            ]
        )
        self.compact_stack.set_visible_child(self.player_small)

        self.compact = Gtk.EventBox(name="notch-compact")
        self.compact.set_visible(True)
        self.compact.add(self.compact_stack)
        self.compact.add_events(
            Gdk.EventMask.SCROLL_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.compact.connect("scroll-event", self._on_compact_scroll)
        self.compact.connect("button-press-event", lambda widget, event: (self.open_notch("dashboard"), False)[1])
        self.compact.connect("enter-notify-event", self.on_button_enter)
        self.compact.connect("leave-notify-event", self.on_button_leave)

        self.tools = Toolbox(notch=self)
        self.stack = Stack(
            name="notch-content",
            v_expand=True,
            h_expand=True,
            transition_type="crossfade",
            transition_duration=100,
            children=[
                self.compact,
                self.launcher,
                self.dashboard,
                self.overview,
                self.emoji,
                self.power,
                self.hue,

                self.tools,
            ]
        )

        self.corner_left = Box(
            name="notch-corner-left",
            orientation="v",
            h_align="start",
            children=[
                MyCorner("top-right"),
                Box(),
            ]
        )

        self.corner_left.set_margin_start(56)

        self.corner_right = Box(
            name="notch-corner-right",
            orientation="v",
            h_align="end",
            children=[
                MyCorner("top-left"),
                Box(),
            ]
        )

        self.corner_right.set_margin_end(56)

        self.notch_box = CenterBox(
            name="notch-box",
            orientation="h",
            h_align="center",
            v_align="center",
            center_children=self.stack,
        )

        self.notch_overlay = Overlay(
            name="notch-overlay",
            h_expand=True,
            h_align="fill",
            child=self.notch_box,
            overlays=[
                self.corner_left,
                self.corner_right,
            ],
        )

        self.notch_overlay.set_overlay_pass_through(self.corner_left, True)
        self.notch_overlay.set_overlay_pass_through(self.corner_right, True)

        self.notification_revealer = Revealer(
            name="notification-revealer",
            transition_type="slide-down",
            transition_duration=250,
            child_revealed=False,
        )

        self.boxed_notification_revealer = Box(
            name="boxed-notification-revealer",
            orientation="v",
            children=[
                self.notification_revealer,
            ]
        )

        self.notch_complete = Box(
            name="notch-complete",
            orientation="v",
            children=[
                self.notch_overlay,
                self.boxed_notification_revealer,
            ]
        )

        self.hidden = False
        self._is_notch_open = False
        self._scrolling = False

        self.add(self.notch_complete)
        self.show_all()

        self._show_overview_children(False)

        self.add_keybinding("Escape", lambda *_: self.close_notch())
        self.add_keybinding("Ctrl Tab", lambda *_: self.dashboard.go_to_next_child())
        self.add_keybinding("Ctrl Shift ISO_Left_Tab", lambda *_: self.dashboard.go_to_previous_child())
        
        self.update_window_icon()

    def on_button_enter(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))

    def on_button_leave(self, widget, event):
        window = widget.get_window()
        if window:
            window.set_cursor(None)

    def close_notch(self):
        self.set_keyboard_mode("none")

        GLib.idle_add(self._show_overview_children, False)

        self.bar.revealer_right.set_reveal_child(True)
        self.bar.revealer_left.set_reveal_child(True)
        self.applet_stack.set_transition_duration(0)
        self.applet_stack.set_visible_child(self.nhistory)
        self._is_notch_open = False

        if self.hidden:
            self.notch_box.remove_style_class("hideshow")
            self.notch_box.add_style_class("hidden")


        for widget in [self.launcher, self.dashboard, self.notification, self.overview, self.emoji, self.power, self.tools, self.hue]:
            widget.remove_style_class("open")
        for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "hue", "tools"]:
            self.stack.remove_style_class(style)
        self.stack.set_visible_child(self.compact)

    def open_notch(self, widget):
        # Handle special behavior for "bluetooth"
        if widget == "bluetooth":
            # If dashboard is already open
            if self.stack.get_visible_child() == self.dashboard:
                # If we're in the widgets section and btdevices is already visible, close the notch
                if self.dashboard.stack.get_visible_child() == self.dashboard.widgets and self.applet_stack.get_visible_child() == self.btdevices:
                    self.close_notch()
                    return
                # If we're in the widgets section but not on btdevices, switch to btdevices
                elif self.dashboard.stack.get_visible_child() == self.dashboard.widgets:
                    self.applet_stack.set_transition_duration(250)
                    self.applet_stack.set_visible_child(self.btdevices)
                    return
                # If we're in another dashboard section, switch to widgets and btdevices
                else:
                    self.dashboard.go_to_section("widgets")
                    self.applet_stack.set_transition_duration(250)
                    self.applet_stack.set_visible_child(self.btdevices)
                    return
            else:
                # Open dashboard with btdevices visible
                self.set_keyboard_mode("exclusive")

                if self.hidden:
                    self.notch_box.remove_style_class("hidden")
                    self.notch_box.add_style_class("hideshow")

                for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools"]:
                    self.stack.remove_style_class(style)
                for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools]:
                    w.remove_style_class("open")

                self.stack.add_style_class("dashboard")
                self.applet_stack.set_transition_duration(0)
                self.stack.set_transition_duration(0)
                self.stack.set_visible_child(self.dashboard)
                self.dashboard.add_style_class("open")
                self.dashboard.go_to_section("widgets")  # Ensure we're on widgets section
                self.applet_stack.set_visible_child(self.btdevices)
                self._is_notch_open = True
                GLib.timeout_add(10, lambda: [self.stack.set_transition_duration(100), self.applet_stack.set_transition_duration(250)][-1] or False)

                self.bar.revealer_right.set_reveal_child(False)
                self.bar.revealer_left.set_reveal_child(False)
                return

        # Handle the "dashboard" case
        if widget == "dashboard":
            if self.stack.get_visible_child() == self.dashboard:
                # If dashboard is already open and showing widgets, close it
                if self.applet_stack.get_visible_child() == self.nhistory and self.dashboard.stack.get_visible_child() == self.dashboard.widgets:
                    self.close_notch()
                    return
                # Otherwise navigate to widgets and ensure nhistory is visible
                else:
                    self.applet_stack.set_transition_duration(250)
                    self.applet_stack.set_visible_child(self.nhistory)
                    self.dashboard.go_to_section("widgets")
                    return
            else:
                self.set_keyboard_mode("exclusive")

                if self.hidden:
                    self.notch_box.remove_style_class("hidden")
                    self.notch_box.add_style_class("hideshow")

                for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools"]:
                    self.stack.remove_style_class(style)
                for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools]:
                    w.remove_style_class("open")

                self.stack.add_style_class("dashboard")
                self.applet_stack.set_transition_duration(0)
                self.stack.set_transition_duration(0)
                self.stack.set_visible_child(self.dashboard)
                self.dashboard.add_style_class("open")
                self.dashboard.go_to_section("widgets")  # Explicitly go to widgets section
                self.applet_stack.set_visible_child(self.nhistory)
                self._is_notch_open = True
                # Reset the transition duration back to 250 after a short delay.
                GLib.timeout_add(10, lambda: [self.stack.set_transition_duration(100), self.applet_stack.set_transition_duration(250)][-1] or False)

                self.bar.revealer_right.set_reveal_child(False)
                self.bar.revealer_left.set_reveal_child(False)
                return

        # Handle pins section
        if widget == "pins":
            if self.stack.get_visible_child() == self.dashboard and self.dashboard.stack.get_visible_child() == self.dashboard.pins:
                # If dashboard is already open and showing pins, close it
                self.close_notch()
                return
            else:
                # Open dashboard and navigate to pins
                self.set_keyboard_mode("exclusive")

                if self.hidden:
                    self.notch_box.remove_style_class("hidden")
                    self.notch_box.add_style_class("hideshow")

                for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools"]:
                    self.stack.remove_style_class(style)
                for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools]:
                    w.remove_style_class("open")

                self.stack.add_style_class("dashboard")
                self.stack.set_transition_duration(0)
                self.stack.set_visible_child(self.dashboard)
                self.dashboard.add_style_class("open")
                self.dashboard.go_to_section("pins")
                self._is_notch_open = True
                GLib.timeout_add(10, lambda: self.stack.set_transition_duration(100) or False)

                self.bar.revealer_right.set_reveal_child(False)
                self.bar.revealer_left.set_reveal_child(False)
                return
                
        # Handle kanban section
        if widget == "kanban":
            if self.stack.get_visible_child() == self.dashboard and self.dashboard.stack.get_visible_child() == self.dashboard.kanban:
                # If dashboard is already open and showing kanban, close it
                self.close_notch()
                return
            else:
                # Open dashboard and navigate to kanban
                self.set_keyboard_mode("exclusive")

                if self.hidden:
                    self.notch_box.remove_style_class("hidden")
                    self.notch_box.add_style_class("hideshow")

                for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools"]:
                    self.stack.remove_style_class(style)
                for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools]:
                    w.remove_style_class("open")

                self.stack.add_style_class("dashboard")
                self.stack.set_transition_duration(0)
                self.stack.set_visible_child(self.dashboard)
                self.dashboard.add_style_class("open")
                self.dashboard.go_to_section("kanban")
                self._is_notch_open = True
                GLib.timeout_add(10, lambda: self.stack.set_transition_duration(100) or False)

                self.bar.revealer_right.set_reveal_child(False)
                self.bar.revealer_left.set_reveal_child(False)
                return
                
        # Handle wallpapers section
        if widget == "wallpapers":
            if self.stack.get_visible_child() == self.dashboard and self.dashboard.stack.get_visible_child() == self.dashboard.wallpapers:
                # If dashboard is already open and showing wallpapers, close it
                self.close_notch()
                return
            else:
                # Open dashboard and navigate to wallpapers
                self.set_keyboard_mode("exclusive")

                if self.hidden:
                    self.notch_box.remove_style_class("hidden")
                    self.notch_box.add_style_class("hideshow")

                for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools"]:
                    self.stack.remove_style_class(style)
                for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools]:
                    w.remove_style_class("open")

                self.stack.add_style_class("dashboard")
                self.stack.set_transition_duration(0)
                self.stack.set_visible_child(self.dashboard)
                self.dashboard.add_style_class("open")
                self.dashboard.go_to_section("wallpapers")
                self._is_notch_open = True
                GLib.timeout_add(10, lambda: self.stack.set_transition_duration(100) or False)

                self.bar.revealer_right.set_reveal_child(False)
                self.bar.revealer_left.set_reveal_child(False)
                return

        # Handle other widgets (launcher, overview, power, tools)
        widgets = {
            "launcher": self.launcher,
            "overview": self.overview,
            "emoji": self.emoji,
            "power": self.power,
            "tools": self.tools,
            "hue": self.hue,
            "dashboard": self.dashboard, # Add dashboard here to ensure its style class is removed
        }
        target_widget = widgets.get(widget, self.dashboard)
        # If already showing the requested widget, close the notch.
        if self.stack.get_visible_child() == target_widget:
            self.close_notch()
            return

        self.set_keyboard_mode("exclusive")

        if self.hidden:
            self.notch_box.remove_style_class("hidden")
            self.notch_box.add_style_class("hideshow")

        for style in widgets.keys():
            self.stack.remove_style_class(style)
        for w in widgets.values():
            w.remove_style_class("open")

        # Configure according to the requested widget.
        if widget in widgets:
            if widget != "dashboard": # Avoid adding dashboard class again if switching from bluetooth
                self.stack.add_style_class(widget)
            self.stack.set_visible_child(widgets[widget])
            widgets[widget].add_style_class("open")

            if widget == "launcher":
                self.launcher.open_launcher()
                self.launcher.search_entry.set_text("")
                self.launcher.search_entry.grab_focus()

            if widget == "emoji":
                self.emoji.open_picker()
                self.emoji.search_entry.set_text("")
                self.emoji.search_entry.grab_focus()

            if widget == "overview":
                GLib.timeout_add(300, self._show_overview_children, True)
        else:
            self.stack.set_visible_child(self.dashboard)

        if widget == "dashboard" or widget == "overview":
            self.bar.revealer_right.set_reveal_child(False)
            self.bar.revealer_left.set_reveal_child(False)
        else:
            self.bar.revealer_right.set_reveal_child(True)
            self.bar.revealer_left.set_reveal_child(True)
        self._is_notch_open = True # Set notch state to open

    def _show_overview_children(self, show_children):
        for child in self.overview.get_children():
            if show_children:
                child.set_visible(show_children)
                self.overview.add_style_class("show")
            else:
                child.set_visible(show_children)
                self.overview.remove_style_class("show")
        return False  # Esto evita que el timeout se repita

    def toggle_hidden(self):
        self.hidden = not self.hidden
        if self.hidden:
            self.notch_box.add_style_class("hidden")
        else:
            self.notch_box.remove_style_class("hidden")

    def _on_compact_scroll(self, widget, event):
        if self._scrolling:
            return True

        children = self.compact_stack.get_children()
        current = children.index(self.compact_stack.get_visible_child())
        new_index = current

        if event.direction == Gdk.ScrollDirection.SMOOTH:
            if event.delta_y < -0.1:
                new_index = (current - 1) % len(children)
            elif event.delta_y > 0.1:
                new_index = (current + 1) % len(children)
            else:
                return False
        elif event.direction == Gdk.ScrollDirection.UP:
            new_index = (current - 1) % len(children)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            new_index = (current + 1) % len(children)
        else:
            return False

        self.compact_stack.set_visible_child(children[new_index])
        self._scrolling = True
        GLib.timeout_add(250, self._reset_scrolling)
        return True

    def _reset_scrolling(self):
        self._scrolling = False
        return False

    def on_player_vanished(self, *args):
        if self.player_small.mpris_label.get_label() == "Nothing Playing":
            self.compact_stack.set_visible_child(self.active_window_box)  # Use box instead of direct active_window

    def restore_label_properties(self):
        label = self.active_window.get_children()[0]
        if isinstance(label, Gtk.Label):
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_hexpand(True)
            label.set_halign(Gtk.Align.FILL)
            label.queue_resize()
            # Update icon after restoring label properties
            self.update_window_icon()

    def _build_app_identifiers_map(self):
        """Build a mapping of app identifiers (class names, executables, names) to DesktopApp objects"""
        identifiers = {}
        for app in self._all_apps:
            # Map by name (lowercase)
            if app.name:
                identifiers[app.name.lower()] = app
                
            # Map by display name
            if app.display_name:
                identifiers[app.display_name.lower()] = app
                
            # Map by window class if available
            if app.window_class:
                identifiers[app.window_class.lower()] = app
                
            # Map by executable name if available
            if app.executable:
                exe_basename = app.executable.split('/')[-1].lower()
                identifiers[exe_basename] = app
                
            # Map by command line if available (without parameters)
            if app.command_line:
                cmd_base = app.command_line.split()[0].split('/')[-1].lower()
                identifiers[cmd_base] = app
                
        return identifiers

    def _normalize_window_class(self, class_name):
        """Normalize window class by removing common suffixes and lowercase."""
        if not class_name:
            return ""
            
        normalized = class_name.lower()
        
        # Remove common suffixes
        suffixes = [".bin", ".exe", ".so", "-bin", "-gtk"]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                
        return normalized
    
    def find_app(self, app_identifier):
        """Return the DesktopApp object by matching any app identifier."""
        if not app_identifier:
            return None
        
        # Try direct lookup in our identifiers map
        normalized_id = str(app_identifier).lower()
        if normalized_id in self.app_identifiers:
            return self.app_identifiers[normalized_id]
            
        # Try with normalized class name
        norm_id = self._normalize_window_class(normalized_id)
        if norm_id in self.app_identifiers:
            return self.app_identifiers[norm_id]
            
        # More targeted matching with exact names only
        for app in self._all_apps:
            if app.name and app.name.lower() == normalized_id:
                return app
            if app.window_class and app.window_class.lower() == normalized_id:
                return app
            if app.display_name and app.display_name.lower() == normalized_id:
                return app
            # Try with executable basename
            if app.executable:
                exe_base = app.executable.split('/')[-1].lower()
                if exe_base == normalized_id:
                    return app
            # Try with command basename
            if app.command_line:
                cmd_base = app.command_line.split()[0].split('/')[-1].lower()
                if cmd_base == normalized_id:
                    return app
                
        return None

    def update_window_icon(self, *args):
        """Update the window icon based on the current active window title"""
        # Get current window title from the active_window label
        label_widget = self.active_window.get_children()[0]
        if not isinstance(label_widget, Gtk.Label):
            return
            
        # Get window title
        title = label_widget.get_text()
        if title == 'Desktop' or not title:
            # If on desktop, hide icon completely
            self.window_icon.set_visible(False)
            return
        
        # For any active window, ensure icon is visible
        self.window_icon.set_visible(True)
            
        # Try to get window class from Hyprland
        from fabric.hyprland.widgets import get_hyprland_connection
        conn = get_hyprland_connection()
        if conn:
            try:
                import json
                active_window = json.loads(conn.send_command("j/activewindow").reply.decode())
                app_id = active_window.get("initialClass", "") or active_window.get("class", "")
                
                # Find app using icon resolver or desktop apps
                icon_size = 20
                desktop_app = self.find_app(app_id)
                
                # Get icon using improved method with fallbacks
                icon_pixbuf = None
                if desktop_app:
                    icon_pixbuf = desktop_app.get_icon_pixbuf(size=icon_size)
                
                if not icon_pixbuf:
                    # Try non-symbolic icon first (full color)
                    icon_pixbuf = self.icon_resolver.get_icon_pixbuf(app_id, icon_size)
                
                if not icon_pixbuf and "-" in app_id:
                    # Try with base name (no suffix) for flatpak apps
                    base_app_id = app_id.split("-")[0]
                    icon_pixbuf = self.icon_resolver.get_icon_pixbuf(base_app_id, icon_size)
                    
                if icon_pixbuf:
                    self.window_icon.set_from_pixbuf(icon_pixbuf)
                else:
                    # Fallback chain: first try non-symbolic application icon
                    try:
                        self.window_icon.set_from_icon_name("application-x-executable", 20)
                    except:
                        # Last resort: use symbolic icon
                        self.window_icon.set_from_icon_name("application-x-executable-symbolic", 20)
            except Exception as e:
                print(f"Error updating window icon: {e}")
                try:
                    self.window_icon.set_from_icon_name("application-x-executable", 20)
                except:
                    self.window_icon.set_from_icon_name("application-x-executable-symbolic", 20)
        else:
            try:
                self.window_icon.set_from_icon_name("application-x-executable", 20)
            except:
                self.window_icon.set_from_icon_name("application-x-executable-symbolic", 20)
