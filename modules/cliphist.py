from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.image import Image
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.utils import idle_add, remove_handler
from fabric.utils.helpers import get_relative_path
from gi.repository import GLib, Gdk, GdkPixbuf
import subprocess
import os
import re
import sys
import tempfile

import modules.icons as icons

class ClipHistory(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="clip-history",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        # Create a temporary directory for image icons
        self.tmp_dir = tempfile.mkdtemp(prefix="cliphist-")
        self.image_cache = {}  # Cache for image previews
        
        self.notch = kwargs["notch"]
        self.selected_index = -1  # Track the selected item index
        self._arranger_handler = 0
        self.clipboard_items = []
        self._loading = False
        self._pending_updates = False

        self.viewport = Box(name="viewport", spacing=4, orientation="v")
        self.search_entry = Entry(
            name="search-entry",
            placeholder="Search Clipboard History...",
            h_expand=True,
            notify_text=self.filter_items,
            on_activate=lambda entry, *_: self.use_selected_item(),
            on_key_press_event=self.on_search_entry_key_press,
        )
        self.search_entry.props.xalign = 0.5
        
        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            min_content_size=(450, 105),
            max_content_size=(450, 105),
            child=self.viewport,
        )

        self.header_box = Box(
            name="header_box",
            spacing=10,
            orientation="h",
            children=[
                Button(
                    name="clear-button",
                    child=Label(name="clear-label", markup=icons.trash),
                    on_clicked=lambda *_: self.clear_history(),
                ),
                self.search_entry,
                Button(
                    name="close-button",
                    child=Label(name="close-label", markup=icons.cancel),
                    tooltip_text="Exit",
                    on_clicked=lambda *_: self.close()
                ),
            ],
        )

        self.history_box = Box(
            name="launcher-box",
            spacing=10,
            h_expand=True,
            orientation="v",
            children=[
                self.header_box,
                self.scrolled_window,
            ],
        )

        self.add(self.history_box)
        self.show_all()

    def close(self):
        """Close the clipboard history panel"""
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        self.notch.close_notch()

    def open(self):
        """Open the clipboard history panel and load items"""
        if self._loading:
            return
        self._loading = True
        self.search_entry.set_text("")  # Clear search
        self.search_entry.grab_focus()
        # Start loading in background using GLib.idle_add
        GLib.idle_add(self._load_clipboard_items_thread)

    def _load_clipboard_items_thread(self):
        """Worker for loading clipboard items, now runs in main loop via idle_add"""
        try:
            result = subprocess.run(
                ["cliphist", "list"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            lines = result.stdout.strip().split('\n')
            new_items = []
            for line in lines:
                if not line or "<meta http-equiv" in line:
                    continue
                new_items.append(line)
            self._update_items(new_items)
        except subprocess.CalledProcessError as e:
            print(f"Error loading clipboard history: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
        finally:
            self._loading = False
            if self._pending_updates:
                self._pending_updates = False
                GLib.idle_add(self._load_clipboard_items_thread)
        return False  # Ensure idle_add does not repeat

    def _update_items(self, new_items):
        """Update the items list from main thread"""
        self.clipboard_items = new_items
        self.display_clipboard_items()

    def display_clipboard_items(self, filter_text=""):
        """Display clipboard items in the viewport"""
        remove_handler(self._arranger_handler) if self._arranger_handler else None
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        
        # Filter items if search text is provided
        filtered_items = []
        for item in self.clipboard_items:
            # Extract just the content part (after the first tab)
            content = item.split('\t', 1)[1] if '\t' in item else item
            if filter_text.lower() in content.lower():
                filtered_items.append(item)
        
        # Show message if no items are found
        if not filtered_items:
            # Create a container box to better center the message
            container = Box(
                name="no-clip-container",
                orientation="v",
                h_align="center",
                v_align="center",
                h_expand=True,
                v_expand=True
            )
            
            # Show a message if no clipboard items
            label = Label(
                name="no-clip",
                markup=icons.clipboard,
                h_align="center",
                v_align="center",
            )
            
            container.add(label)
            self.viewport.add(container)
            return
            
        # Display items in batches to prevent UI freeze
        self._display_items_batch(filtered_items, 0, 10)

    def _display_items_batch(self, items, start, batch_size):
        """Display items in batches to keep UI responsive"""
        end = min(start + batch_size, len(items))
        
        for i in range(start, end):
            item = items[i]
            self.viewport.add(self.create_clipboard_item(item))
        
        # Schedule next batch if there are more items
        if end < len(items):
            GLib.idle_add(self._display_items_batch, items, end, batch_size)
        else:
            # Auto-select first item if we have filter text
            if self.search_entry.get_text() and self.viewport.get_children():
                self.update_selection(0)

    def create_clipboard_item(self, item):
        """Create a button for a clipboard item"""
        # Extract ID and content
        parts = item.split('\t', 1)
        item_id = parts[0] if len(parts) > 1 else "0"
        content = parts[1] if len(parts) > 1 else item
        
        # Truncate content for display
        display_text = content.strip()
        if len(display_text) > 100:
            display_text = display_text[:97] + "..."
        
        # Check if this is an image by examining the content
        is_image = self.is_image_data(content)
        
        if is_image:
            # For images, create item with image preview
            button = Button(
                name="slot-button",
                child=Box(
                    name="slot-box",
                    orientation="h",
                    spacing=10,
                    children=[
                        Image(name="clip-icon", h_align="start"),  # Placeholder
                        Label(
                            name="clip-label",
                            label="[Image]",
                            ellipsization="end",
                            v_align="center",
                            h_align="start",
                            h_expand=True,
                        ),
                    ],
                ),
                tooltip_text="Image in clipboard",
                on_clicked=lambda *_, id=item_id: self.paste_item(id),
            )
            # Load image preview in background
            self._load_image_preview_async(item_id, button)
        else:
            # For text, create regular item
            button = self.create_text_item_button(item_id, display_text)
        
        # Add key press event handler for Enter key
        button.connect("key-press-event", lambda widget, event, id=item_id: self.on_item_key_press(widget, event, id))
        
        # Make sure button can receive focus and key events
        button.set_can_focus(True)
        button.add_events(Gdk.EventMask.KEY_PRESS_MASK)
            
        return button

    def _load_image_preview_async(self, item_id, button):
        """Load image preview using GLib.idle_add instead of threads"""
        def load_image():
            try:
                if item_id in self.image_cache:
                    pixbuf = self.image_cache[item_id]
                else:
                    result = subprocess.run(
                        ["cliphist", "decode", item_id],
                        capture_output=True,
                        check=True
                    )
                    loader = GdkPixbuf.PixbufLoader()
                    loader.write(result.stdout)
                    loader.close()
                    pixbuf = loader.get_pixbuf()
                    width, height = pixbuf.get_width(), pixbuf.get_height()
                    max_size = 72
                    if width > height:
                        new_width = max_size
                        new_height = int(height * (max_size / width))
                    else:
                        new_height = max_size
                        new_width = int(width * (max_size / height))
                    pixbuf = pixbuf.scale_simple(new_width, new_height, GdkPixbuf.InterpType.BILINEAR)
                    self.image_cache[item_id] = pixbuf
                self._update_image_button(button, pixbuf)
            except Exception as e:
                print(f"Error loading image preview: {e}", file=sys.stderr)
            return False
        GLib.idle_add(load_image)

    def _update_image_button(self, button, pixbuf):
        """Update the button with the loaded image preview"""
        box = button.get_child()
        if box and len(box.get_children()) > 0:
            image_widget = box.get_children()[0]
            if isinstance(image_widget, Image):
                image_widget.set_from_pixbuf(pixbuf)

    def create_text_item_button(self, item_id, display_text):
        """Create a button for a text clipboard item"""
        return Button(
            name="slot-button",
            child=Box(
                name="slot-box",
                orientation="h",
                spacing=10,
                children=[
                    Label(
                        name="clip-icon",
                        markup=icons.clip_text,
                        h_align="start",
                    ),
                    Label(
                        name="clip-label",
                        label=display_text,
                        ellipsization="end",
                        v_align="center",
                        h_align="start",
                        h_expand=True,
                    ),
                ],
            ),
            tooltip_text=display_text,
            on_clicked=lambda *_: self.paste_item(item_id),
        )

    def is_image_data(self, content):
        """Determine if clipboard content is likely an image"""
        # Check for common image data patterns
        return (
            content.startswith("data:image/") or
            content.startswith("\x89PNG") or
            content.startswith("GIF8") or
            content.startswith("\xff\xd8\xff") or  # JPEG
            re.match(r'^\s*<img\s+', content) is not None or  # HTML image tag
            "binary" in content.lower() and any(ext in content.lower() for ext in ["jpg", "jpeg", "png", "bmp", "gif"])
        )

    def paste_item(self, item_id):
        """Copy the selected item to the clipboard and close (GLib.idle_add)"""
        def paste():
            try:
                result = subprocess.run(
                    ["cliphist", "decode", item_id],
                    capture_output=True,
                    check=True
                )
                subprocess.run(
                    ["wl-copy"],
                    input=result.stdout,
                    check=True
                )
                GLib.idle_add(self.close)
            except subprocess.CalledProcessError as e:
                print(f"Error pasting clipboard item: {e}", file=sys.stderr)
            return False
        GLib.idle_add(paste)

    def delete_item(self, item_id):
        """Delete the selected clipboard item (GLib.idle_add)"""
        def delete():
            try:
                subprocess.run(
                    ["cliphist", "delete", item_id],
                    check=True
                )
                self._pending_updates = True
                if not self._loading:
                    GLib.idle_add(self._load_clipboard_items_thread)
            except subprocess.CalledProcessError as e:
                print(f"Error deleting clipboard item: {e}", file=sys.stderr)
            return False
        GLib.idle_add(delete)

    def clear_history(self):
        """Clear all clipboard history (GLib.idle_add)"""
        def clear():
            try:
                subprocess.run(["cliphist", "wipe"], check=True)
                self._pending_updates = True
                if not self._loading:
                    GLib.idle_add(self._load_clipboard_items_thread)
            except subprocess.CalledProcessError as e:
                print(f"Error clearing clipboard history: {e}", file=sys.stderr)
            return False
        GLib.idle_add(clear)

    def filter_items(self, entry, *_):
        """Filter clipboard items based on search text"""
        self.display_clipboard_items(entry.get_text())

    def on_search_entry_key_press(self, widget, event):
        """Handle key presses in the search entry"""
        if event.keyval == Gdk.KEY_Down:
            self.move_selection(1)
            return True
        elif event.keyval == Gdk.KEY_Up:
            self.move_selection(-1)
            return True
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.use_selected_item()
            return True
        elif event.keyval == Gdk.KEY_Delete:
            self.delete_selected_item()
            return True
        elif event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def update_selection(self, new_index):
        """Update the selected item in the viewport"""
        children = self.viewport.get_children()
        
        # Unselect current
        if self.selected_index != -1 and self.selected_index < len(children):
            current_button = children[self.selected_index]
            current_button.get_style_context().remove_class("selected")
            
        # Select new
        if new_index != -1 and new_index < len(children):
            new_button = children[new_index]
            new_button.get_style_context().add_class("selected")
            self.selected_index = new_index
            self.scroll_to_selected(new_button)
        else:
            self.selected_index = -1

    def move_selection(self, delta):
        """Move the selection up or down"""
        children = self.viewport.get_children()
        if not children:
            return
            
        # Allow starting selection from nothing
        if self.selected_index == -1 and delta == 1:
            new_index = 0
        else:
            new_index = self.selected_index + delta
            
        new_index = max(0, min(new_index, len(children) - 1))
        self.update_selection(new_index)

    def scroll_to_selected(self, button):
        """Scroll to ensure the selected item is visible"""
        def scroll():
            adj = self.scrolled_window.get_vadjustment()
            alloc = button.get_allocation()
            if alloc.height == 0:
                return False  # Retry if allocation isn't ready

            y = alloc.y
            height = alloc.height
            page_size = adj.get_page_size()
            current_value = adj.get_value()

            # Calculate visible boundaries
            visible_top = current_value
            visible_bottom = current_value + page_size

            if y < visible_top:
                # Item above viewport - align to top
                adj.set_value(y)
            elif y + height > visible_bottom:
                # Item below viewport - align to bottom
                new_value = y + height - page_size
                adj.set_value(new_value)
            return False
        GLib.idle_add(scroll)

    def use_selected_item(self):
        """Use (paste) the selected clipboard item"""
        children = self.viewport.get_children()
        if not children or self.selected_index == -1 or self.selected_index >= len(self.clipboard_items):
            return
            
        # Get the item ID from the first part before the tab
        item_line = self.clipboard_items[self.selected_index]
        item_id = item_line.split('\t', 1)[0]
        self.paste_item(item_id)

    def delete_selected_item(self):
        """Delete the selected clipboard item"""
        children = self.viewport.get_children()
        if not children or self.selected_index == -1:
            return
            
        # Get the item ID from the first part before the tab
        item_line = self.clipboard_items[self.selected_index]
        item_id = item_line.split('\t', 1)[0]
        self.delete_item(item_id)

    def on_item_key_press(self, widget, event, item_id):
        """Handle key press events on clipboard items"""
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            # Copy item to clipboard and close
            self.paste_item(item_id)
            return True
        return False

    def __del__(self):
        """Clean up temporary files on destruction"""
        try:
            if hasattr(self, 'tmp_dir') and os.path.exists(self.tmp_dir):
                import shutil
                shutil.rmtree(self.tmp_dir)
            self.image_cache.clear()
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}", file=sys.stderr)
