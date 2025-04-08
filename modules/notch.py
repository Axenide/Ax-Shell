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
from modules.emoji import EmojiPicker
from modules.corners import MyCorner
from modules.tmux import TmuxManager  # Import the new TmuxManager
from modules.cliphist import ClipHistory  # Import the ClipHistory module
import config.data as data
from modules.player import PlayerSmall
from modules.tools import Toolbox
from utils.icon_resolver import IconResolver
from fabric.utils.helpers import get_desktop_applications
from fabric.widgets.image import Image
from utils.occlusion import check_occlusion


class Notch(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="notch",
            layer="top",
            anchor="top",
            margin="-40px 0px 0px 0px" if not data.VERTICAL else "0px 0px 0px 0px",
            
            keyboard_mode="none",
            exclusivity="none",
            visible=True,
            all_visible=True,
        )

        # Add character buffer for launcher transition
        self._typed_chars_buffer = ""
        self._launcher_transitioning = False
        self._launcher_transition_timeout = None

        self.bar = kwargs.get("bar", None)
        self.is_hovered = False  # Add hover tracking property
        self._prevent_occlusion = False  # Flag to prevent occlusion temporarily
        self._occlusion_timer_id = None  # Track the timeout ID to cancel it if needed

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
        self.tmux = TmuxManager(notch=self)  # Create TmuxManager instance
        self.cliphist = ClipHistory(notch=self)  # Create ClipHistory instance

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
        self.active_window.connect("notify::label", self.on_active_window_changed)  # Connect to window change event

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

                self.tools,
                self.tmux,  # Add tmux to the stack
                self.cliphist,  # Add cliphist to the stack
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
            ]
        )

        # Add event handling for hover detection to notch_overlay
        self.notch_overlay_eventbox = Gtk.EventBox()
        self.notch_overlay_eventbox.add(self.notch_overlay)
        self.notch_overlay_eventbox.connect("enter-notify-event", self.on_notch_enter)
        self.notch_overlay_eventbox.connect("leave-notify-event", self.on_notch_leave)

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
                self.notch_overlay_eventbox,  # Use the eventbox instead of the direct overlay
                self.boxed_notification_revealer,
            ]
        )

        self.hidden = False
        self._is_notch_open = False
        self._scrolling = False
        
        self.notch_wrap = Box(
            name="notch-wrap",
            children=[
                self.notch_complete,
                Box(name="vert-comp" if data.VERTICAL else None),
            ]
        )

        self.add(self.notch_wrap)
        self.show_all()

        self._show_overview_children(False)

        self.add_keybinding("Escape", lambda *_: self.close_notch())
        self.add_keybinding("Ctrl Tab", lambda *_: self.dashboard.go_to_next_child())
        self.add_keybinding("Ctrl Shift ISO_Left_Tab", lambda *_: self.dashboard.go_to_previous_child())

        self.update_window_icon()
        
        self.active_window.connect("button-press-event", lambda widget, event: (self.open_notch("dashboard"), False)[1])
        
        # Track current window class
        self._current_window_class = self._get_current_window_class()
        
        # Start checking for occlusion every 250ms
        GLib.timeout_add(250, self._check_occlusion)
        
        # Add key press event handling to the entire notch window
        self.connect("key-press-event", self.on_key_press)

    def on_button_enter(self, widget, event):
        self.is_hovered = True  # Set hover state
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        # Remove occluded style class when hovered, but only in vertical mode
        if data.VERTICAL:
            self.notch_wrap.remove_style_class("occluded")
        return True

    def on_button_leave(self, widget, event):
        # Only mark as not hovered if actually leaving to outside
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False  # Ignore child-to-child movements
            
        self.is_hovered = False
        window = widget.get_window()
        if window:
            window.set_cursor(None)
        return True

    # Add new hover event handlers for the entire notch
    def on_notch_enter(self, widget, event):
        """Handle hover enter for the entire notch area"""
        self.is_hovered = True
        # Remove occluded class when hovered, but only in vertical mode
        if data.VERTICAL:
            self.notch_wrap.remove_style_class("occluded")
        return False  # Allow event propagation

    def on_notch_leave(self, widget, event):
        """Handle hover leave for the entire notch area"""
        # Only mark as not hovered if actually leaving to outside
        if event.detail == Gdk.NotifyType.INFERIOR:
            return False  # Ignore child-to-child movements
            
        self.is_hovered = False
        return False  # Allow event propagation

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

        for widget in [self.launcher, self.dashboard, self.notification, self.overview, self.emoji, self.power, self.tools, self.tmux, self.cliphist]:
            widget.remove_style_class("open")
        for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools", "tmux", "cliphist"]:
            self.stack.remove_style_class(style)
        self.stack.set_visible_child(self.compact)

    def open_notch(self, widget):
        self.notch_wrap.remove_style_class("occluded")
        
        # Handle tmux manager
        if widget == "tmux":
            if self.stack.get_visible_child() == self.tmux:
                self.close_notch()
                return
                
            self.set_keyboard_mode("exclusive")

            if self.hidden:
                self.notch_box.remove_style_class("hidden")
                self.notch_box.add_style_class("hideshow")

            for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools", "tmux", "cliphist"]:
                self.stack.remove_style_class(style)
            for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools, self.tmux, self.cliphist]:
                w.remove_style_class("open")

            self.stack.add_style_class("launcher")  # Reuse launcher styling
            self.stack.set_visible_child(self.tmux)
            self.tmux.add_style_class("open")
            self.tmux.open_manager()
            self._is_notch_open = True

            return

        # Handle clipboard history
        if widget == "cliphist":
            if self.stack.get_visible_child() == self.cliphist:
                self.close_notch()
                return
                
            self.set_keyboard_mode("exclusive")

            if self.hidden:
                self.notch_box.remove_style_class("hidden")
                self.notch_box.add_style_class("hideshow")

            for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools", "tmux", "cliphist"]:
                self.stack.remove_style_class(style)
            for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools, self.tmux, self.cliphist]:
                w.remove_style_class("open")

            self.stack.add_style_class("launcher")  # Reuse launcher styling
            self.stack.set_visible_child(self.cliphist)
            self.cliphist.add_style_class("open")
            GLib.idle_add(self.cliphist.open)
            self._is_notch_open = True

            return

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
            "dashboard": self.dashboard,
            "tmux": self.tmux,  # Add tmux to widgets dictionary
            "cliphist": self.cliphist,  # Add cliphist to widgets dictionary
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

    def _check_occlusion(self):
        """
        Check if top 40px of the screen is occluded by any window
        and update the notch_box style accordingly.
        """
        # If notch is open or hovered, remove occluded class and skip further checks
        if self._is_notch_open or self.is_hovered or self._prevent_occlusion:
            if data.VERTICAL:
                self.notch_wrap.remove_style_class("occluded")
            return True
            
        # Only check occlusion if not hovered, not open, and in vertical mode
        if data.VERTICAL:
            is_occluded = check_occlusion(("top", 40))
            
            # Add or remove style class based on occlusion
            if is_occluded:
                self.notch_wrap.add_style_class("occluded")
            else:
                self.notch_wrap.remove_style_class("occluded")
        
        return True  # Return True to keep the timeout active

    def _get_current_window_class(self):
        """Get the class of the currently active window"""
        try:
            from fabric.hyprland.widgets import get_hyprland_connection
            conn = get_hyprland_connection()
            if conn:
                import json
                active_window = json.loads(conn.send_command("j/activewindow").reply.decode())
                return active_window.get("initialClass", "") or active_window.get("class", "")
        except Exception as e:
            print(f"Error getting window class: {e}")
        return ""

    def on_active_window_changed(self, *args):
        """
        Temporarily remove the 'occluded' class when active window class changes
        to make the notch visible momentarily.
        """
        # Skip occlusion handling if not in vertical mode
        if not data.VERTICAL:
            return
            
        # Get the current window class
        new_window_class = self._get_current_window_class()
        
        # Only proceed if the window class has actually changed
        if new_window_class != self._current_window_class:
            # Update the stored window class
            self._current_window_class = new_window_class
            
            # If there's an existing timer, cancel it
            if self._occlusion_timer_id is not None:
                GLib.source_remove(self._occlusion_timer_id)
                self._occlusion_timer_id = None
            
            # Set flag to prevent occlusion
            self._prevent_occlusion = True
            
            # Remove occluded class
            self.notch_wrap.remove_style_class("occluded")
            
            # Set up a new timeout to re-enable occlusion check after 500ms
            self._occlusion_timer_id = GLib.timeout_add(500, self._restore_occlusion_check)
        
    def _restore_occlusion_check(self):
        """Re-enable occlusion checking after temporary visibility"""
        # Reset the prevent flag
        self._prevent_occlusion = False
        self._occlusion_timer_id = None
        
        # Now let the regular check handle it
        return False  # Don't repeat the timeout

    def open_launcher_with_text(self, initial_text):
        """Open the launcher with initial text in the search field."""
        # Set the transition flag to capture subsequent keystrokes
        self._launcher_transitioning = True
        
        # Store the initial character in our buffer
        if initial_text:
            self._typed_chars_buffer = initial_text
        
        # Check if launcher is already open
        if self.stack.get_visible_child() == self.launcher:
            # If already open, just append text to existing search
            current_text = self.launcher.search_entry.get_text()
            self.launcher.search_entry.set_text(current_text + initial_text)
            # Ensure cursor is at the end of text without selection
            self.launcher.search_entry.set_position(-1)
            self.launcher.search_entry.select_region(-1, -1)  # Prevent selection
            self.launcher.search_entry.grab_focus()
            return
        
        # Otherwise similar to standard open_notch("launcher") but with text
        self.set_keyboard_mode("exclusive")
        self.notch_wrap.remove_style_class("occluded")
        
        if self.hidden:
            self.notch_box.remove_style_class("hidden")
            self.notch_box.add_style_class("hideshow")
            
        # Clear previous style classes and states
        for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools", "tmux"]:
            self.stack.remove_style_class(style)
        for w in [self.launcher, self.dashboard, self.notification, self.overview, self.emoji, self.power, self.tools, self.tmux]:
            w.remove_style_class("open")
            
        # Configure for launcher
        self.stack.add_style_class("launcher")
        self.stack.set_visible_child(self.launcher)
        self.launcher.add_style_class("open")
        
        # Force initialization before opening - ensures apps are loaded
        self.launcher.ensure_initialized()
        
        # Now fully initialize the launcher UI
        self.launcher.open_launcher()
        
        # Set a timeout to apply the text after the transition (200ms should be enough)
        if self._launcher_transition_timeout:
            GLib.source_remove(self._launcher_transition_timeout)
            
        self._launcher_transition_timeout = GLib.timeout_add(150, self._finalize_launcher_transition)
        
        # Show the standard bar elements
        self.bar.revealer_right.set_reveal_child(True)
        self.bar.revealer_left.set_reveal_child(True)
        
        self._is_notch_open = True
    
    def _finalize_launcher_transition(self):
        """Apply buffered text and finalize launcher transition"""
        # Apply all buffered characters
        if self._typed_chars_buffer:
            # Set the full text at once
            entry = self.launcher.search_entry
            entry.set_text(self._typed_chars_buffer)
            
            # Place cursor at the end without selecting - with careful focus timing
            entry.grab_focus()
            
            # Use multiple deselection attempts at different time intervals
            # GTK can re-select text during the focus event cycle, so we need several checks
            GLib.timeout_add(10, self._ensure_no_text_selection)
            GLib.timeout_add(50, self._ensure_no_text_selection)
            GLib.timeout_add(100, self._ensure_no_text_selection)
            
            # Debug
            print(f"Applied buffered text: '{self._typed_chars_buffer}'")
            
            # Clear the buffer
            self._typed_chars_buffer = ""
        
        # Mark transition as complete
        self._launcher_transitioning = False
        self._launcher_transition_timeout = None
        
        return False  # Don't repeat
    
    def _ensure_no_text_selection(self):
        """Make absolutely sure no text is selected in the search entry"""
        entry = self.launcher.search_entry
        
        # Get current text length
        text_len = len(entry.get_text())
        
        # Move cursor to end
        entry.set_position(text_len)
        
        # Clear any selection that might have happened
        entry.select_region(text_len, text_len)
        
        # Check if entry has focus, if not give it focus
        if not entry.has_focus():
            entry.grab_focus()
            # When grabbing focus again, immediately clear selection
            GLib.idle_add(lambda: entry.select_region(text_len, text_len))
        
        return False  # Don't repeat
    
    # Add new method for handling key presses at the window level
    def on_key_press(self, widget, event):
        """Handle key presses at the notch level"""
        # Special handling during launcher transition - capture all valid keystrokes
        if self._launcher_transitioning:
            keyval = event.keyval
            keychar = chr(keyval) if 32 <= keyval <= 126 else None
            
            # Only capture valid text characters during transition
            is_valid_char = (
                (keyval >= Gdk.KEY_a and keyval <= Gdk.KEY_z) or
                (keyval >= Gdk.KEY_A and keyval <= Gdk.KEY_Z) or
                (keyval >= Gdk.KEY_0 and keyval <= Gdk.KEY_9) or
                keyval in (Gdk.KEY_space, Gdk.KEY_underscore, Gdk.KEY_minus, Gdk.KEY_period)
            )
            
            if is_valid_char and keychar:
                # Add to our buffer during transition
                self._typed_chars_buffer += keychar
                print(f"Buffered character: {keychar}, buffer now: '{self._typed_chars_buffer}'")
                return True
        
        # Only process when dashboard is visible AND specifically in the widgets section
        if (self.stack.get_visible_child() == self.dashboard and 
            self.dashboard.stack.get_visible_child() == self.dashboard.widgets):
            
            # Don't process if launcher is already open
            if self.stack.get_visible_child() == self.launcher:
                return False
                
            # Get the character from the key press
            keyval = event.keyval
            keychar = chr(keyval) if 32 <= keyval <= 126 else None
            
            # Check if the key is a valid search character (alphanumeric or common search symbols)
            is_valid_char = (
                (keyval >= Gdk.KEY_a and keyval <= Gdk.KEY_z) or
                (keyval >= Gdk.KEY_A and keyval <= Gdk.KEY_Z) or
                (keyval >= Gdk.KEY_0 and keyval <= Gdk.KEY_9) or
                keyval in (Gdk.KEY_space, Gdk.KEY_underscore, Gdk.KEY_minus, Gdk.KEY_period)
            )
            
            if is_valid_char and keychar:
                print(f"Notch received keypress: {keychar}")
                # Directly open launcher with the typed character
                self.open_launcher_with_text(keychar)
                return True
                
        return False
