import os
from gi.repository import GdkPixbuf, GLib, Gdk
from loguru import logger
from widgets.rounded_image import CustomImage

from fabric.notifications.service import (
    Notification,
    NotificationAction,
    Notifications,
)
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.image import Image
from fabric.widgets.label import Label
import modules.icons as icons

class ActionButton(Button):
    def __init__(self, action: NotificationAction, index: int, total: int, notification_box):
        super().__init__(
            name="action-button",
            h_expand=True,
            on_clicked=self.on_clicked,
            child=Label(name="button-label", label=action.label),
        )
        self.action = action
        self.notification_box = notification_box
        style_class = (
            "start-action" if index == 0
            else "end-action" if index == total - 1
            else "middle-action"
        )
        self.add_style_class(style_class)
        self.connect("enter-notify-event", lambda *_: notification_box.hover_button(self))
        self.connect("leave-notify-event", lambda *_: notification_box.unhover_button(self))

    def on_clicked(self, *_):
        self.action.invoke()
        self.action.parent.close("dismissed-by-user")


class NotificationBox(Box):
    def __init__(self, notification: Notification, timeout_ms=5000, **kwargs):
        super().__init__(
            name="notification-box",
            # spacing=8,
            orientation="v",
            children=[
                # self.create_header(notification),
                self.create_content(notification),
                self.create_action_buttons(notification),
            ],
        )
        self.notification = notification
        self.timeout_ms = timeout_ms
        self._timeout_id = None
        self.start_timeout()

    def create_header(self, notification):
        app_icon = (
            Image(
                name="notification-icon",
                image_file=notification.app_icon[7:],
                size=24,
            ) if "file://" in notification.app_icon else
            Image(
                name="notification-icon",
                icon_name="dialog-information-symbolic" or notification.app_icon,
                icon_size=24,
            )
        )

        return CenterBox(
            name="notification-title",
            start_children=[
                Box(
                    spacing=4,
                    children=[
                        app_icon,
                        Label(
                            notification.app_name,
                            name="notification-app-name",
                            h_align="start"
                        )
                    ]
                )
            ],
            end_children=[self.create_close_button()]
        )

    def create_content(self, notification):
        return Box(
            name="notification-content",
            spacing=8,
            children=[
                Box(
                    name="notification-image",
                    children=CustomImage(
                        pixbuf=notification.image_pixbuf.scale_simple(
                            48, 48, GdkPixbuf.InterpType.BILINEAR
                        ) if notification.image_pixbuf else self.get_pixbuf(
                            notification.app_icon, 48, 48
                        )
                    ),
                ),
                Box(
                    name="notification-text",
                    orientation="v",
                    v_align="center",
                    children=[
                        Box(
                            name="notification-summary-box",
                            orientation="h",
                            # spacing=4,
                            children=[
                                Label(
                                    name="notification-summary",
                                    markup=notification.summary.replace("\n", " "),
                                    h_align="start",
                                    ellipsization="end",
                                ),
                                Label(
                                    name="notification-app-name",
                                    markup= " | " + notification.app_name,
                                    h_align="start",
                                    ellipsization="end",
                                ),
                            ],
                        ),
                        Label(
                            markup=notification.body.replace("\n", " "),
                            h_align="start",
                            ellipsization="end",
                        ) if notification.body else Box(),
                    ],
                ),
                Box(h_expand=True),
                Box(
                    orientation="v",
                    children=[
                        self.create_close_button(),
                        Box(v_expand=True),
                    ],
                ),
            ],
        )

    def get_pixbuf(self, icon_path, width, height):
        if icon_path.startswith("file://"):
            icon_path = icon_path[7:]

        if not os.path.exists(icon_path):
            logger.warning(f"Icon path does not exist: {icon_path}")
            return None

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(icon_path)
            return pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
        except Exception as e:
            logger.error(f"Failed to load or scale icon: {e}")
            return None

    def create_action_buttons(self, notification):
        return Box(
            name="notification-action-buttons",
            spacing=4,
            h_expand=True,
            children=[
                ActionButton(action, i, len(notification.actions), self)
                for i, action in enumerate(notification.actions)
            ],
        )

    def create_close_button(self):
        close_button = Button(
            name="close-button",
            child=Label(name="close-label", markup=icons.cancel),
            on_clicked=lambda *_: self.notification.close("dismissed-by-user"),
        )
        close_button.connect("enter-notify-event", lambda *_: self.hover_button(close_button))
        close_button.connect("leave-notify-event", lambda *_: self.unhover_button(close_button))
        return close_button

    def start_timeout(self):
        self.stop_timeout()
        self._timeout_id = GLib.timeout_add(self.timeout_ms, self.close_notification)

    def stop_timeout(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None

    def close_notification(self):
        self.notification.close("expired")
        self.stop_timeout()
        return False

    def pause_timeout(self):
        self.stop_timeout()

    def resume_timeout(self):
        self.start_timeout()

    def destroy(self):
        self.stop_timeout()
        super().destroy()

    # @staticmethod
    def set_pointer_cursor(self, widget, cursor_name):
        """Cambia el cursor sobre un widget."""
        window = widget.get_window()
        if window:
            cursor = Gdk.Cursor.new_from_name(widget.get_display(), cursor_name)
            window.set_cursor(cursor)

    def hover_button(self, button):
        self.pause_timeout()
        self.set_pointer_cursor(button, "hand2")

    def unhover_button(self, button):
        self.resume_timeout()
        self.set_pointer_cursor(button, "arrow")

class NotificationContainer(Box):
    def __init__(self, **kwargs):
        super().__init__(name="notification", orientation="v", spacing=4, v_expand=True, h_expand=True)
        self.notch = kwargs["notch"]
        self._server = Notifications()
        self._server.connect("notification-added", self.on_new_notification)

    def set_pointer_cursor(self, widget, cursor_name):
        """Cambia el cursor sobre un widget."""
        window = widget.get_window()
        if window:
            cursor = Gdk.Cursor.new_from_name(widget.get_display(), cursor_name)
            window.set_cursor(cursor)

    def on_new_notification(self, fabric_notif, id):
        for child in self.get_children():
            child.destroy()
        notification = fabric_notif.get_notification_from_id(id)
        new_box = NotificationBox(notification)
        self.add(new_box)
        notification.connect("closed", self.on_notification_closed)
        self.notch.open_notch("notification")

    def on_notification_closed(self, notification, reason):
        self.notch.close_notch()
        # Set cursor to default
        self.set_pointer_cursor(self, "arrow")
        logger.info(f"Notification {notification.id} closed with reason: {reason}")
        for child in self.get_children():
            child.destroy()
