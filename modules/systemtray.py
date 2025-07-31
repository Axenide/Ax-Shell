import gi

gi.require_version("Gray", "0.1")
from gi.repository import Gray, Gtk, Gdk, GdkPixbuf, GLib

from loguru import logger
import config.data as data


class SystemTray(Gtk.Box):
    def __init__(self, pixel_size: int = 20, **kwargs) -> None:
        orientation = (
            Gtk.Orientation.HORIZONTAL
            if not data.VERTICAL
            else Gtk.Orientation.VERTICAL
        )
        super().__init__(name="systray", orientation=orientation, spacing=8, **kwargs)
        self.set_visible(False)  # Initially hidden when empty.
        self.pixel_size = pixel_size
        self.watcher = Gray.Watcher()
        self.watcher.connect("item-added", self.on_item_added)
        self.set_visible(False)  # Initially hidden when empty.
        self._update_visibility()  # Ensure visibility is updated after initialization.

    def set_visible(self, visible):
        """Override to track external visibility setting"""
        # Only show if enabled AND has children
        if visible and len(self.get_children()) > 0:
            super().set_visible(True)
        else:
            super().set_visible(False)

    def _update_visibility(self):
        self.set_visible(len(self.get_children()) > 0)

    def on_item_added(self, _, identifier: str):
        item = self.watcher.get_item_for_identifier(identifier)
        item_button = self.do_bake_item_button(item)
        item.connect(
            "removed", lambda *args: (item_button.destroy(), self._update_visibility())
        )
        self.add(item_button)
        item_button.show_all()
        self._update_visibility()

    def do_bake_item_button(self, item: Gray.Item) -> Gtk.Button:
        button = Gtk.Button()

        button.connect(
            "button-press-event",
            lambda button, event: self.on_button_click(button, item, event),
        )
        pixmap = Gray.get_pixmap_for_pixmaps(item.get_icon_pixmaps(), self.pixel_size)

        try:
            if pixmap is not None:
                pixbuf = pixmap.as_pixbuf(self.pixel_size, GdkPixbuf.InterpType.HYPER)
            else:
                icon_name = item.get_icon_name()
                icon_theme_path = item.get_icon_theme_path()

                # Use custom theme path if available
                if icon_theme_path:
                    custom_theme = Gtk.IconTheme.new()
                    custom_theme.prepend_search_path(icon_theme_path)
                    try:
                        pixbuf = custom_theme.load_icon(
                            icon_name,
                            self.pixel_size,
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
                    except GLib.Error:
                        # Fallback to default theme if custom path fails
                        pixbuf = Gtk.IconTheme.get_default().load_icon(
                            icon_name,
                            self.pixel_size,
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
                else:
                    try:
                        # Load icon from default theme
                        pixbuf = Gtk.IconTheme.get_default().load_icon(
                            icon_name,
                            self.pixel_size,
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load icon from default theme {e}")
                        pixbuf = Gtk.IconTheme.get_default().load_icon(
                            "image-missing",
                            self.pixel_size,
                            Gtk.IconLookupFlags.FORCE_SIZE,
                        )
        except GLib.Error:
            # Fallback to 'image-missing' icon
            pixbuf = Gtk.IconTheme.get_default().load_icon(
                "image-missing",
                self.pixel_size,
                Gtk.IconLookupFlags.FORCE_SIZE,
            )

        button.set_image(Gtk.Image.new_from_pixbuf(pixbuf))
        return button

    def on_button_click(self, button, item: Gray.Item, event):
        if event.button == Gdk.BUTTON_PRIMARY:  # Left click
            try:
                item.activate(event.x, event.y)
            except Exception as e:
                print(f"Error activating item: {e}")
        elif event.button == Gdk.BUTTON_SECONDARY:  # Right click
            menu = item.get_menu()
            if menu:
                menu.set_name("system-tray-menu")
                menu.popup_at_widget(
                    button,
                    Gdk.Gravity.SOUTH,
                    Gdk.Gravity.NORTH,
                    event,
                )
            else:
                item.context_menu(event.x, event.y)
