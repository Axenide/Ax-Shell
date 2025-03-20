# Thanks to https://github.com/muhchaudhary for the original code. You are a legend.
import json

import cairo
import gi
from loguru import logger
from fabric.hyprland.service import Hyprland
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
import modules.icons as icons

# WIP icon resolver (app_id to guessing the icon name)
from utils.icon_resolver import IconResolver
from fabric.utils.helpers import get_desktop_applications

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()

icon_resolver = IconResolver()
connection = Hyprland()
SCALE = 0.1

# Credit to Aylur for the drag and drop code
TARGET = [Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.SAME_APP, 0)]

# Credit to Aylur for the createSurfaceFromWidget code
def createSurfaceFromWidget(widget: Gtk.Widget) -> cairo.ImageSurface:
    alloc = widget.get_allocation()
    surface = cairo.ImageSurface(
        cairo.Format.ARGB32,
        alloc.width,
        alloc.height,
    )
    cr = cairo.Context(surface)
    cr.set_source_rgba(255, 255, 255, 0)
    cr.rectangle(0, 0, alloc.width, alloc.height)
    cr.fill()
    widget.draw(cr)
    return surface


class HyprlandWindowButton(Button):
    def __init__(
        self,
        window: Box,
        title: str,
        address: str,
        app_id: str,
        size,
        transform: int = 0,
    ):
        self.transform = transform % 4
        self.size = size if transform in [0, 2] else (size[1], size[0])
        self.address = address
        self.app_id = app_id
        self.title = title
        self.window: Box = window

        # Compute dynamic icon sizes based on the button size.
        # Using the minimum dimension of the button for scaling.
        icon_size_main = int(min(self.size) * 0.5)  # adjust factor as needed

        # Enhanced icon resolution using desktop apps
        desktop_app = window.find_app(app_id)
        
        # Get icon using improved method with fallbacks
        icon_pixbuf = None
        if desktop_app:
            icon_pixbuf = desktop_app.get_icon_pixbuf(size=icon_size_main)
        
        if not icon_pixbuf:
            # Fallback to IconResolver
            icon_pixbuf = icon_resolver.get_icon_pixbuf(app_id, icon_size_main)
        
        if not icon_pixbuf:
            # Additional fallbacks for common apps
            icon_pixbuf = icon_resolver.get_icon_pixbuf("application-x-executable-symbolic", icon_size_main)
            if not icon_pixbuf:
                icon_pixbuf = icon_resolver.get_icon_pixbuf("image-missing", icon_size_main)

        super().__init__(
            name="overview-client-box",
            image=Image(pixbuf=icon_pixbuf),
            tooltip_text=title,
            size=size,
            on_clicked=self.on_button_click,
            on_button_press_event=lambda _, event: connection.send_command(
                f"/dispatch closewindow address:{address}"
            )
            if event.button == 3
            else None,
            on_drag_data_get=lambda _s, _c, data, *_: data.set_text(
                address, len(address)
            ),
            on_drag_begin=lambda _, context: Gtk.drag_set_icon_surface(
                context, createSurfaceFromWidget(self)
            ),
        )

        # Store the desktop_app for later use
        self.desktop_app = desktop_app

        self.drag_source_set(
            start_button_mask=Gdk.ModifierType.BUTTON1_MASK,
            targets=TARGET,
            actions=Gdk.DragAction.COPY,
        )

        self.connect("key_press_event", self.on_key_press_event)

    def on_key_press_event(self, widget, event):
        if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
                connection.send_command(f"/dispatch closewindow address:{self.address}")
                return True
        return False

    def update_image(self, image):
        # Compute overlay icon size dynamically.
        icon_size_overlay = int(min(self.size) * 0.6)  # adjust factor as needed
        
        # Enhanced icon resolution for overlay
        icon_pixbuf = None
        if hasattr(self, 'desktop_app') and self.desktop_app:
            icon_pixbuf = self.desktop_app.get_icon_pixbuf(size=icon_size_overlay)
            
        if not icon_pixbuf:
            icon_pixbuf = icon_resolver.get_icon_pixbuf(self.app_id, icon_size_overlay)
            
        if not icon_pixbuf:
            icon_pixbuf = icon_resolver.get_icon_pixbuf("application-x-executable-symbolic", icon_size_overlay)
            if not icon_pixbuf:
                icon_pixbuf = icon_resolver.get_icon_pixbuf("image-missing", icon_size_overlay)
                
        self.set_image(
            Overlay(
                child=image,
                overlays=Image(
                    name="overview-icon",
                    pixbuf=icon_pixbuf,
                    h_align="center",
                    v_align="end",
                    tooltip_text=self.title,
                ),
            )
        )

    def on_button_click(self, *_):
        connection.send_command(f"/dispatch focuswindow address:{self.address}")


class WorkspaceEventBox(EventBox):
    def __init__(self, workspace_id: int, fixed: Gtk.Fixed | None = None):
        self.fixed = fixed
        super().__init__(
            name="overview-workspace-bg",
            h_expand=True,
            v_expand=True,
            size=(int(CURRENT_WIDTH * SCALE), int(CURRENT_HEIGHT * SCALE)),
            child=fixed
            if fixed
            else Label(
                name="overview-add-label",
                h_expand=True,
                v_expand=True,
                markup=icons.circle_plus,
            ),
            on_drag_data_received=lambda _w, _c, _x, _y, data, *_: connection.send_command(
                f"/dispatch movetoworkspacesilent {workspace_id},address:{data.get_data().decode()}"
            ),
        )
        self.drag_dest_set(
            Gtk.DestDefaults.ALL,
            TARGET,
            Gdk.DragAction.COPY,
        )
        if fixed:
            fixed.show_all()



class Overview(Box):
    def __init__(self, **kwargs):
        # Initialize as a Box instead of a PopupWindow.
        super().__init__(name="overview", orientation="v", spacing=8, **kwargs)
        self.workspace_boxes: dict[int, Box] = {}
        self.clients: dict[str, HyprlandWindowButton] = {}
        
        # Initialize app registry for better icon resolution
        self._all_apps = get_desktop_applications()
        self.app_identifiers = self._build_app_identifiers_map()
        
        # Remove the window_class_aliases dictionary completely

        connection.connect("event::openwindow", self.do_update)
        connection.connect("event::closewindow", self.do_update)
        connection.connect("event::movewindow", self.do_update)
        self.update()
        
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
    
    def _classes_match(self, class1, class2):
        """Check if two window class names match with stricter comparison."""
        if not class1 or not class2:
            return False
            
        # Normalize both classes
        norm1 = self._normalize_window_class(class1)
        norm2 = self._normalize_window_class(class2)
        
        # Direct match after normalization
        if norm1 == norm2:
            return True
            
        # Don't do substring matching as it's too error-prone
        # This avoids incorrectly matching flatpak apps and others
        return False
        
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

    def update(self, signal_update=False):
        # Refresh app registry when updating to ensure latest data
        self._all_apps = get_desktop_applications()
        self.app_identifiers = self._build_app_identifiers_map()
        
        # Remove old clients and workspaces.
        for client in self.clients.values():
            client.destroy()
        self.clients.clear()

        for workspace in self.workspace_boxes.values():
            workspace.destroy()
        self.workspace_boxes.clear()

        # Create two rows in this Box.
        self.children = [Box(spacing=8), Box(spacing=8)]

        monitors = {
            monitor["id"]: (monitor["x"], monitor["y"], monitor["transform"])
            for monitor in json.loads(
                connection.send_command("j/monitors").reply.decode()
            )
        }

        for client in json.loads(
            str(connection.send_command("j/clients").reply.decode())
        ):
            # Exclude special workspaces.
            if client["workspace"]["id"] > 0:
                self.clients[client["address"]] = HyprlandWindowButton(
                    window=self,
                    title=client["title"],
                    address=client["address"],
                    app_id=client["initialClass"],
                    size=(client["size"][0] * SCALE, client["size"][1] * SCALE),
                    transform=monitors[client["monitor"]][2],
                )
                if client["workspace"]["id"] not in self.workspace_boxes:
                    self.workspace_boxes[client["workspace"]["id"]] = Gtk.Fixed.new()
                self.workspace_boxes[client["workspace"]["id"]].put(
                    self.clients[client["address"]],
                    abs(client["at"][0] - monitors[client["monitor"]][0]) * SCALE,
                    abs(client["at"][1] - monitors[client["monitor"]][1]) * SCALE,
                )

        # Lay out workspaces into two rows.
        for w_id in range(1, 11):
            if w_id <= 5:
                overview_row = self.children[0]
            else:
                overview_row = self.children[1]
            overview_row.add(
                Box(
                    name="overview-workspace-box",
                    orientation="vertical",
                    children=[
                        Label(name="overview-workspace-label", label=f"Workspace {w_id}"),
                        WorkspaceEventBox(
                            w_id,
                            self.workspace_boxes[w_id]
                            if w_id in self.workspace_boxes
                            else None,
                        ),
                    ],
                )
            )

    def do_update(self, *_):
        logger.info(f"[Overview] Updating for :{_[1].name}")
        self.update(signal_update=True)
