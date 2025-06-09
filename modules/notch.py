from fabric.hyprland.widgets import ActiveWindow
from fabric.utils.helpers import FormattedString, get_desktop_applications
from fabric.widgets.box import Box
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.revealer import Revealer
from fabric.widgets.stack import Stack
from gi.repository import Gdk, GLib, Gtk, Pango

import config.data as data
from modules.cliphist import ClipHistory
from modules.corners import MyCorner
from modules.dashboard import Dashboard
from modules.emoji import EmojiPicker
from modules.launcher import AppLauncher
from modules.overview import Overview
from modules.player import PlayerSmall
from modules.power import PowerMenu
from modules.tmux import TmuxManager
from modules.tools import Toolbox
from utils.icon_resolver import IconResolver
from utils.occlusion import check_occlusion
from widgets.wayland import WaylandWindow as Window


class Notch(Window):
    def __init__(self, **kwargs):

        is_panel_vertical = False
        if data.PANEL_THEME == "Panel":
            is_panel_vertical = data.VERTICAL

        anchor_val = "top"
        revealer_transition_type = "slide-down"

        if data.PANEL_THEME == "Notch":

            anchor_val = "top"
            revealer_transition_type = "slide-down"
        elif data.PANEL_THEME == "Panel":
            if is_panel_vertical:

                if data.BAR_POSITION == "Left":
                    match data.PANEL_POSITION:
                        case "Start":
                            anchor_val = "left top"
                            revealer_transition_type = "slide-right"
                        case "Center":
                            anchor_val = "left"
                            revealer_transition_type = "slide-right"
                        case "End":
                            anchor_val = "left bottom"
                            revealer_transition_type = "slide-right"
                        case _:
                            anchor_val = "left"
                            revealer_transition_type = "slide-right"
                elif data.BAR_POSITION == "Right":
                    match data.PANEL_POSITION:
                        case "Start":
                            anchor_val = "right top"
                            revealer_transition_type = "slide-left"
                        case "Center":
                            anchor_val = "right"
                            revealer_transition_type = "slide-left"
                        case "End":
                            anchor_val = "right bottom"
                            revealer_transition_type = "slide-left"
                        case _:
                            anchor_val = "right"
                            revealer_transition_type = "slide-left"
            else:

                if data.BAR_POSITION == "Top":
                    match data.PANEL_POSITION:
                        case "Start":
                            anchor_val = "top left"
                            revealer_transition_type = "slide-down"
                        case "Center":
                            anchor_val = "top"
                            revealer_transition_type = "slide-down"
                        case "End":
                            anchor_val = "top right"
                            revealer_transition_type = "slide-down"
                        case _:
                            anchor_val = "top"
                            revealer_transition_type = "slide-down"
                elif data.BAR_POSITION == "Bottom":
                    match data.PANEL_POSITION:
                        case "Start":
                            anchor_val = "bottom left"
                            revealer_transition_type = "slide-up"
                        case "Center":
                            anchor_val = "bottom"
                            revealer_transition_type = "slide-up"
                        case "End":
                            anchor_val = "bottom right"
                            revealer_transition_type = "slide-up"
                        case _:
                            anchor_val = "bottom"
                            revealer_transition_type = "slide-up"

        default_top_anchor_margin_str = "-40px 8px 8px 8px"
        pills_margin_top_str = "-40px 0px 0px 0px"
        dense_edge_margin_top_str = "-46px 0px 0px 0px"
        current_margin_str = ""

        if data.PANEL_THEME == "Panel":
            current_margin_str = "0px 0px 0px 0px"
        else:
            if data.VERTICAL:
                current_margin_str = "0px 0px 0px 0px"
            else:
                if data.BAR_POSITION == "Bottom":
                    current_margin_str = "0px 0px 0px 0px"
                else:
                    match data.BAR_THEME:
                        case "Pills":
                            current_margin_str = pills_margin_top_str
                        case "Dense" | "Edge":
                            current_margin_str = dense_edge_margin_top_str
                        case _:
                            current_margin_str = default_top_anchor_margin_str
        
        super().__init__(
            name="notch",
            layer="top",
            anchor=anchor_val, 
            margin=current_margin_str, 
            keyboard_mode="none",
            exclusivity="none" if data.PANEL_THEME == "Notch" else "normal",
            visible=True,
            all_visible=True,
        )

        self._typed_chars_buffer = ""
        self._launcher_transitioning = False
        self._launcher_transition_timeout = None

        self.bar = kwargs.get("bar", None)
        self.is_hovered = False
        self._prevent_occlusion = False
        self._occlusion_timer_id = None
        
        self.icon_resolver = IconResolver()
        self._all_apps = get_desktop_applications()
        self.app_identifiers = self._build_app_identifiers_map()

        self.dashboard = Dashboard(notch=self)
        self.nhistory = self.dashboard.widgets.notification_history

        self.applet_stack = self.dashboard.widgets.applet_stack
        self.btdevices = self.dashboard.widgets.bluetooth
        self.nwconnections = self.dashboard.widgets.network_connections

        self.btdevices.set_visible(False)
        self.nwconnections.set_visible(False)

        
        self.launcher = AppLauncher(notch=self)
        self.overview = Overview()
        self.emoji = EmojiPicker(notch=self)
        self.power = PowerMenu(notch=self)
        self.tmux = TmuxManager(notch=self)
        self.cliphist = ClipHistory(notch=self)

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
                f"{{'Desktop' if not win_title or win_title == 'unknown' else win_title}}",
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

        if data.PANEL_THEME == "Notch":
            self.active_window.connect("notify::label", self.on_active_window_changed)

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
        self.compact_stack.set_visible_child(self.active_window_box)

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
            style_classes = ["invert"] if (not data.VERTICAL and data.BAR_THEME in ["Dense", "Edge"]) and data.BAR_POSITION not in ["Bottom"] else [],
            transition_type="crossfade",
            transition_duration=250,
            children=[
                self.compact,
                self.launcher,
                self.dashboard,
                self.overview,
                self.emoji,
                self.power,
                self.tools,
                self.tmux,
                self.cliphist,
            ]
        )

        if data.PANEL_THEME == "Panel":
            self.stack.add_style_class("panel")

            self.stack.add_style_class(data.BAR_POSITION.lower())
            self.stack.add_style_class(data.PANEL_POSITION.lower())

        if is_panel_vertical or (data.PANEL_POSITION in ["Start", "End"] and data.PANEL_THEME == "Panel"):
            self.compact.set_size_request(260, 40)
            self.launcher.set_size_request(320, 635)
            self.tmux.set_size_request(320, 635)
            self.cliphist.set_size_request(320, 635)
            self.dashboard.set_size_request(410, 900)

        else:
            self.compact.set_size_request(260, 40)
            self.launcher.set_size_request(480, 244)
            self.tmux.set_size_request(480, 244)
            self.cliphist.set_size_request(480, 244)
            self.dashboard.set_size_request(1093, 472)

        self.stack.set_interpolate_size(True)
        self.stack.set_homogeneous(False)

        self.corner_left = Box(
            name="notch-corner-left",
            orientation="v",
            h_align="start",
            children=[
                MyCorner("top-right"),
                Box(),
            ]
        )

        self.corner_right = Box(
            name="notch-corner-right",
            orientation="v",
            h_align="end",
            children=[
                MyCorner("top-left"),
                Box(),
            ]
        )

        self.notch_box = CenterBox(
            name="notch-box",
            orientation="h",
            h_align="center",
            v_align="center",
            start_children=self.corner_left,
            center_children=self.stack,
            end_children=self.corner_right,
        )

        self.notch_box.add_style_class(data.PANEL_THEME.lower())
        
        self.notch_revealer = Revealer(
            name="notch-revealer",
            transition_type=revealer_transition_type,
            transition_duration=250,
            child_revealed=True,
            child=self.notch_box,
        )

        self.notch_hover_area_event_box = Gtk.EventBox()
        self.notch_hover_area_event_box.add(self.notch_revealer)
        if data.PANEL_THEME == "Notch":
            self.notch_hover_area_event_box.connect("enter-notify-event", self.on_notch_hover_area_enter)
            self.notch_hover_area_event_box.connect("leave-notify-event", self.on_notch_hover_area_leave)
        self.notch_hover_area_event_box.set_size_request(-1, 1)

        self.notch_complete = Box(
            name="notch-complete",
            orientation="v" if is_panel_vertical else "h",
            children=[
                self.notch_hover_area_event_box,
            ]
        )

        self._is_notch_open = False
        self._scrolling = False

        self.vert_comp_left = Box(name="vert-comp")
        self.vert_comp_right = Box(name="vert-comp")

        self.vert_comp = Box()

        match data.BAR_POSITION:
            case "Left":
                self.vert_comp = self.vert_comp_right
            case "Right":
                self.vert_comp = self.vert_comp_left

        match data.BAR_THEME:
            case "Pills":
                self.vert_comp.set_size_request(38, 0)
            case "Dense":
                self.vert_comp.set_size_request(50, 0)
            case "Edge":
                self.vert_comp.set_size_request(44, 0)
            case _:
                self.vert_comp.set_size_request(38, 0)

        if is_panel_vertical:
            self.vert_comp.set_size_request(1, 1)

        self.vert_comp.set_sensitive(False)

        self.notch_children = []

        if data.VERTICAL:
            self.notch_children = [
                self.vert_comp_left,
                self.notch_complete,
                self.vert_comp_right,
            ]
        else:
            self.notch_children = [
                self.notch_complete,
            ]
        
        self.notch_wrap = Box(
            name="notch-wrap",
            children=self.notch_children,
        )

        self.add(self.notch_wrap)
        self.show_all()

        self.add_keybinding("Escape", lambda *_: self.close_notch())
        self.add_keybinding("Ctrl Tab", lambda *_: self.dashboard.go_to_next_child())
        self.add_keybinding("Ctrl Shift ISO_Left_Tab", lambda *_: self.dashboard.go_to_previous_child())
        
        self.update_window_icon()
        
        self.active_window.connect("button-press-event", lambda widget, event: (self.open_notch("dashboard"), False)[1])

        if data.PANEL_THEME != "Notch":
            for corner in [self.corner_left, self.corner_right]:
                corner.set_visible(False)
        

        self._current_window_class = self._get_current_window_class()
        


        if data.PANEL_THEME == "Notch" and data.BAR_POSITION != "Top":
            GLib.timeout_add(250, self._check_occlusion)
        elif data.PANEL_THEME == "Notch":
            self.notch_revealer.set_reveal_child(True)
        else:
            self.notch_revealer.set_reveal_child(False)
        

        self.connect("key-press-event", self.on_key_press)

    def on_button_enter(self, widget, event):
        self.is_hovered = True
        window = widget.get_window()
        if window:
            window.set_cursor(Gdk.Cursor(Gdk.CursorType.HAND2))
        return True

    def on_button_leave(self, widget, event):

        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
            
        self.is_hovered = False
        window = widget.get_window()
        if window:
            window.set_cursor(None)
        return True

    def on_notch_hover_area_enter(self, widget, event):
        """Handle hover enter for the entire notch area"""
        self.is_hovered = True
        if data.PANEL_THEME == "Notch" and data.BAR_POSITION != "Top":
            self.notch_revealer.set_reveal_child(True)
        return False

    def on_notch_hover_area_leave(self, widget, event):
        """Handle hover leave for the entire notch area"""

        if event.detail == Gdk.NotifyType.INFERIOR:
            return False
            
        self.is_hovered = False

        return False

    def close_notch(self):
        self.set_keyboard_mode("none")
        self.notch_box.remove_style_class("open")
        self.stack.remove_style_class("open")

        self.bar.revealer_right.set_reveal_child(True)
        self.bar.revealer_left.set_reveal_child(True)
        self.applet_stack.set_visible_child(self.nhistory)
        self._is_notch_open = False
        self.stack.set_visible_child(self.compact)
        if data.PANEL_THEME != "Notch":
            self.notch_revealer.set_reveal_child(False)

    def open_notch(self, widget_name: str):
        self.notch_revealer.set_reveal_child(True)
        self.notch_box.add_style_class("open")
        self.stack.add_style_class("open")
        current_stack_child = self.stack.get_visible_child()
        is_dashboard_currently_visible = (current_stack_child == self.dashboard)

        if widget_name == "network_applet":
            if is_dashboard_currently_visible:

                if self.dashboard.stack.get_visible_child() == self.dashboard.widgets and \
                   self.applet_stack.get_visible_child() == self.nwconnections:
                    self.close_notch()
                    return

                self.set_keyboard_mode("exclusive") 
                self.dashboard.go_to_section("widgets")
                self.applet_stack.set_visible_child(self.nwconnections)
                return

        elif widget_name == "bluetooth":
            if is_dashboard_currently_visible:

                if self.dashboard.stack.get_visible_child() == self.dashboard.widgets and \
                   self.applet_stack.get_visible_child() == self.btdevices:
                    self.close_notch()
                    return

                self.set_keyboard_mode("exclusive") 
                self.dashboard.go_to_section("widgets")
                self.applet_stack.set_visible_child(self.btdevices)
                return

        elif widget_name == "dashboard":
            if is_dashboard_currently_visible:

                if self.dashboard.stack.get_visible_child() == self.dashboard.widgets and \
                   self.applet_stack.get_visible_child() == self.nhistory:
                    self.close_notch()
                    return

                self.set_keyboard_mode("exclusive")
                self.dashboard.go_to_section("widgets")
                self.applet_stack.set_visible_child(self.nhistory)
                return

        dashboard_sections_map = {
            "pins": self.dashboard.pins,
            "kanban": self.dashboard.kanban,
            "wallpapers": self.dashboard.wallpapers,
        }
        if widget_name in dashboard_sections_map:
            section_widget_instance = dashboard_sections_map[widget_name]

            if is_dashboard_currently_visible and self.dashboard.stack.get_visible_child() == section_widget_instance:
                self.close_notch()
                return

        target_widget_on_stack = None
        action_on_open = None
        focus_action = None

        hide_bar_revealers = False

        widget_configs = {
            "tmux":       {"instance": self.tmux, "action": self.tmux.open_manager},
            "cliphist":   {"instance": self.cliphist, "action": lambda: GLib.idle_add(self.cliphist.open)},
            "launcher":   {"instance": self.launcher, "action": self.launcher.open_launcher, "focus": lambda: (self.launcher.search_entry.set_text(""), self.launcher.search_entry.grab_focus())},
            "emoji":      {"instance": self.emoji, "action": self.emoji.open_picker, "focus": lambda: (self.emoji.search_entry.set_text(""), self.emoji.search_entry.grab_focus())},
            "overview":   {"instance": self.overview, "hide_revealers": True},
            "power":      {"instance": self.power},
            "tools":      {"instance": self.tools},
        }

        if widget_name in widget_configs:
            config = widget_configs[widget_name]
            target_widget_on_stack = config["instance"]
            action_on_open = config.get("action")
            focus_action = config.get("focus")
            hide_bar_revealers = config.get("hide_revealers", False)

            if current_stack_child == target_widget_on_stack:
                self.close_notch()
                return
        else:

            target_widget_on_stack = self.dashboard
            hide_bar_revealers = True

        self.set_keyboard_mode("exclusive")
        self.stack.set_visible_child(target_widget_on_stack)

        if action_on_open:
            action_on_open()
        if focus_action:
            focus_action()

        if target_widget_on_stack == self.dashboard:
            if widget_name == "bluetooth":
                self.dashboard.go_to_section("widgets")
                self.applet_stack.set_visible_child(self.btdevices)
            elif widget_name == "network_applet":
                self.dashboard.go_to_section("widgets")
                self.applet_stack.set_visible_child(self.nwconnections)
            elif widget_name in dashboard_sections_map:
                self.dashboard.go_to_section(widget_name)
            elif widget_name == "dashboard":
                self.dashboard.go_to_section("widgets")
                self.applet_stack.set_visible_child(self.nhistory)

            
        if data.BAR_POSITION in ["Top", "Bottom"] and data.PANEL_THEME == "Panel" or data.BAR_POSITION in ["Bottom"] and data.PANEL_THEME == "Notch":
            self.bar.revealer_right.set_reveal_child(True)
            self.bar.revealer_left.set_reveal_child(True)
        else:
            self.bar.revealer_right.set_reveal_child(not hide_bar_revealers)
            self.bar.revealer_left.set_reveal_child(not hide_bar_revealers)
        
        self._is_notch_open = True

    def toggle_hidden(self):
        self.hidden = not self.hidden
        self.set_visible(not self.hidden)

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
            self.compact_stack.set_visible_child(self.active_window_box)

    def restore_label_properties(self):
        label = self.active_window.get_children()[0]
        if isinstance(label, Gtk.Label):
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_hexpand(True)
            label.set_halign(Gtk.Align.FILL)
            label.queue_resize()

            self.update_window_icon()

    def _build_app_identifiers_map(self):
        """Build a mapping of app identifiers (class names, executables, names) to DesktopApp objects"""
        identifiers = {}
        for app in self._all_apps:

            if app.name:
                identifiers[app.name.lower()] = app
                

            if app.display_name:
                identifiers[app.display_name.lower()] = app
                

            if app.window_class:
                identifiers[app.window_class.lower()] = app
                

            if app.executable:
                exe_basename = app.executable.split('/')[-1].lower()
                identifiers[exe_basename] = app
                

            if app.command_line:
                cmd_base = app.command_line.split()[0].split('/')[-1].lower()
                identifiers[cmd_base] = app
                
        return identifiers

    def find_app(self, app_id: str):
        """Find a DesktopApp object by various identifiers using the pre-built map."""
        normalized_id = app_id.lower()
        return self.app_identifiers.get(normalized_id)

    def update_window_icon(self, *args):
        """Update the window icon based on the current active window title"""

        label_widget = self.active_window.get_children()[0]
        if not isinstance(label_widget, Gtk.Label):
            return
            

        title = label_widget.get_text()
        if title == 'Desktop' or not title:

            self.window_icon.set_visible(False)
            return
        

        self.window_icon.set_visible(True)
            

        from fabric.hyprland.widgets import get_hyprland_connection
        conn = get_hyprland_connection()
        if conn:
            try:
                import json
                active_window_json = conn.send_command("j/activewindow").reply.decode()
                active_window_data = json.loads(active_window_json)
                app_id = active_window_data.get("initialClass", "") or active_window_data.get("class", "")
                

                icon_size = 20
                desktop_app = self.find_app(app_id)
                

                icon_pixbuf = None
                if desktop_app:
                    icon_pixbuf = desktop_app.get_icon_pixbuf(size=icon_size)
                
                if not icon_pixbuf:

                    icon_pixbuf = self.icon_resolver.get_icon_pixbuf(app_id, icon_size)
                
                if not icon_pixbuf and "-" in app_id:

                    base_app_id = app_id.split("-")[0]
                    icon_pixbuf = self.icon_resolver.get_icon_pixbuf(base_app_id, icon_size)
                    
                if icon_pixbuf:
                    self.window_icon.set_from_pixbuf(icon_pixbuf)
                else:

                    try:
                        self.window_icon.set_from_icon_name("application-x-executable", 20)
                    except:

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
        and update the notch_revealer accordingly.
        """

        

        occlusion_edge = "top"
        occlusion_size = 40

        if not (self.is_hovered or self._is_notch_open or self._prevent_occlusion):
            is_occluded = check_occlusion((occlusion_edge, occlusion_size)) 
            self.notch_revealer.set_reveal_child(not is_occluded)
        
        return True

    def _get_current_window_class(self):
        """Get the class of the currently active window"""
        try:
            from fabric.hyprland.widgets import get_hyprland_connection
            conn = get_hyprland_connection()
            if conn:
                import json
                active_window_json = conn.send_command("j/activewindow").reply.decode()
                active_window_data = json.loads(active_window_json)
                return active_window_data.get("initialClass", "") or active_window_data.get("class", "")
        except Exception as e:
            print(f"Error getting window class: {e}")
        return ""

    def on_active_window_changed(self, *args):
        """
        Temporarily remove the 'occluded' class when active window class changes
        to make the notch visible momentarily.
        """

        if data.PANEL_THEME != "Notch":
            return
            

        new_window_class = self._get_current_window_class()
        

        if new_window_class != self._current_window_class:

            self._current_window_class = new_window_class
            

            if self._occlusion_timer_id is not None:
                GLib.source_remove(self._occlusion_timer_id)
                self._occlusion_timer_id = None
            

            self._prevent_occlusion = True
            self.notch_revealer.set_reveal_child(True)
            

            self._occlusion_timer_id = GLib.timeout_add(500, self._restore_occlusion_check)
        
    def _restore_occlusion_check(self):
        """Re-enable occlusion checking after temporary visibility"""

        self._prevent_occlusion = False
        self._occlusion_timer_id = None
        

        return False

    def open_launcher_with_text(self, initial_text):
        """Open the launcher with initial text in the search field."""

        self._launcher_transitioning = True
        

        if initial_text:
            self._typed_chars_buffer = initial_text
        

        if self.stack.get_visible_child() == self.launcher:

            current_text = self.launcher.search_entry.get_text()
            self.launcher.search_entry.set_text(current_text + initial_text)

            self.launcher.search_entry.set_position(-1)
            self.launcher.search_entry.select_region(-1, -1)
            self.launcher.search_entry.grab_focus()
            return
        

        self.set_keyboard_mode("exclusive")
        

        for style in ["launcher", "dashboard", "notification", "overview", "emoji", "power", "tools", "tmux"]:
            self.stack.remove_style_class(style)
        for w in [self.launcher, self.dashboard, self.overview, self.emoji, self.power, self.tools, self.tmux, self.cliphist]:
            w.remove_style_class("open")
            

        self.stack.add_style_class("launcher")
        self.stack.set_visible_child(self.launcher)
        self.launcher.add_style_class("open")
        

        self.launcher.ensure_initialized()
        

        self.launcher.open_launcher()
        

        if self._launcher_transition_timeout:
            GLib.source_remove(self._launcher_transition_timeout)
            
        self._launcher_transition_timeout = GLib.timeout_add(150, self._finalize_launcher_transition)
        

        self.bar.revealer_right.set_reveal_child(True)
        self.bar.revealer_left.set_reveal_child(True)
        
        self._is_notch_open = True
    
    def _finalize_launcher_transition(self):
        """Apply buffered text and finalize launcher transition"""

        if self._typed_chars_buffer:

            entry = self.launcher.search_entry
            entry.set_text(self._typed_chars_buffer)
            

            entry.grab_focus()
            

            GLib.timeout_add(10, self._ensure_no_text_selection)
            GLib.timeout_add(50, self._ensure_no_text_selection)
            GLib.timeout_add(100, self._ensure_no_text_selection)
            

            print(f"Applied buffered text: '{self._typed_chars_buffer}'")
            

            self._typed_chars_buffer = ""
        

        self._launcher_transitioning = False
        self._launcher_transition_timeout = None
        
        return False
    
    def _ensure_no_text_selection(self):
        """Make absolutely sure no text is selected in the search entry"""
        entry = self.launcher.search_entry
        

        text_len = len(entry.get_text())
        

        entry.set_position(text_len)
        

        entry.select_region(text_len, text_len)
        

        if not entry.has_focus():
            entry.grab_focus()

            GLib.idle_add(lambda: entry.select_region(text_len, text_len))
        
        return False
    

    def on_key_press(self, widget, event):
        """Handle key presses at the notch level"""

        if self._launcher_transitioning:
            keyval = event.keyval
            keychar = chr(keyval) if 32 <= keyval <= 126 else None
            

            is_valid_char = (
                (keyval >= Gdk.KEY_a and keyval <= Gdk.KEY_z) or
                (keyval >= Gdk.KEY_A and keyval <= Gdk.KEY_Z) or
                (keyval >= Gdk.KEY_0 and keyval <= Gdk.KEY_9) or
                keyval in (Gdk.KEY_space, Gdk.KEY_underscore, Gdk.KEY_minus, Gdk.KEY_period)
            )
            
            if is_valid_char and keychar:

                self._typed_chars_buffer += keychar
                print(f"Buffered character: {keychar}, buffer now: '{self._typed_chars_buffer}'")
                return True
        

        if (self.stack.get_visible_child() == self.dashboard and 
            self.dashboard.stack.get_visible_child() == self.dashboard.widgets):
            

            if self.stack.get_visible_child() == self.launcher:
                return False
                

            keyval = event.keyval
            keychar = chr(keyval) if 32 <= keyval <= 126 else None
            

            is_valid_char = (
                (keyval >= Gdk.KEY_a and keyval <= Gdk.KEY_z) or
                (keyval >= Gdk.KEY_A and keyval <= Gdk.KEY_Z) or
                (keyval >= Gdk.KEY_0 and keyval <= Gdk.KEY_9) or
                keyval in (Gdk.KEY_space, Gdk.KEY_underscore, Gdk.KEY_minus, Gdk.KEY_period)
            )
            
            if is_valid_char and keychar:
                print(f"Notch received keypress: {keychar}")

                self.open_launcher_with_text(keychar)
                return True
                
        return False
