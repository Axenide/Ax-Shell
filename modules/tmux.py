import os
import subprocess

from fabric.utils import exec_shell_command_async, idle_add, remove_handler
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.entry import Entry
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from gi.repository import Gdk, GLib, Gtk

import config.data as data
import modules.icons as icons


class TmuxManager(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="tmux-manager",
            visible=False,
            all_visible=False,
            **kwargs,
        )

        self.notch = kwargs["notch"]
        self.selected_index = -1  # Track the selected item index

        self._arranger_handler: int = 0

        self.viewport = Box(name="viewport", spacing=4, orientation="v")
        self.session_name_entry = Entry(
            name="session-name-entry",
            placeholder="Create Tmux Session...",
            h_expand=True,
            h_align="fill",
            on_activate=lambda entry, *_: self.create_session(entry.get_text()),
            on_key_press_event=self.on_entry_key_press,
        )
        self.session_name_entry.props.xalign = 0.5
        self.scrolled_window = ScrolledWindow(
            name="scrolled-window",
            spacing=10,
            h_expand=True,
            v_expand=True,
            h_align="fill",
            v_align="fill",
            child=self.viewport,
            propagate_width=False,
            propagate_height=False,
        )

        self.header_box = Box(
            name="header_box",
            spacing=10,
            orientation="h",
            children=[
                Button(
                    name="new-session-button",
                    child=Label(name="new-session-label", markup=icons.add),
                    tooltip_text="Create New Session",
                    on_clicked=lambda *_: self.create_session(self.session_name_entry.get_text()),
                ),
                self.session_name_entry,
                Button(
                    name="close-button",
                    child=Label(name="close-label", markup=icons.cancel),
                    tooltip_text="Exit",
                    on_clicked=lambda *_: self.close_manager()
                ),
            ],
        )

        self.tmux_box = Box(
            name="tmux-box",
            spacing=10,
            h_expand=True,
            orientation="v",
            children=[
                self.header_box,
                self.scrolled_window,
            ],
        )

        self.add(self.tmux_box)
        self.show_all()

    def close_manager(self):
        """Close the tmux manager"""
        self.viewport.children = []
        self.selected_index = -1  # Reset selection
        self.notch.close_notch()

    def open_manager(self):
        """Open the tmux manager and refresh sessions"""
        self.refresh_sessions()
        self.session_name_entry.set_text("")
        self.session_name_entry.grab_focus()

    def refresh_sessions(self):
        """Get tmux sessions and populate the viewport"""
        remove_handler(self._arranger_handler) if self._arranger_handler else None
        self.viewport.children = []
        self.selected_index = -1  # Clear selection when viewport changes

        # Get tmux sessions
        sessions = self.get_tmux_sessions()
        if not sessions:
            # Create a container box to better center the message
            container = Box(
                name="no-tmux-container",
                orientation="v",
                h_align="center",
                v_align="center",
                h_expand=True,
                v_expand=True
            )
            
            # Show a message if no sessions
            label = Label(
                name="no-tmux",
                markup=icons.terminal,
                h_align="center",
                v_align="center",
            )
            
            container.add(label)
            
            self.viewport.add(container)
            return

        # Add session slots to viewport
        for session in sessions:
            self.viewport.add(self.create_session_slot(session))

    def get_tmux_sessions(self):
        """Get list of tmux sessions"""
        try:
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
            return []
        except Exception as e:
            print(f"Error getting tmux sessions: {e}")
            return []

    def create_session_slot(self, session_name):
        """Create a button for a tmux session"""
        # Create an entry for inline editing (initially hidden)
        name_entry = Entry(
            name="session-name-entry",
            text=session_name,
            visible=False,
            on_activate=lambda entry, *_: self.finish_rename(button, session_name, entry),
            on_key_press_event=self.on_rename_key_press,
        )
        
        # Create the label showing the session name
        name_label = Label(
            name="app-label",
            label=session_name,
            ellipsization="end",
            v_align="center",
            h_align="center",
        )
        
        # Session slot content box
        slot_box = Box(
            name="slot-box",
            orientation="h",
            spacing=10,
            children=[
                Label(
                    name="tmux-icon",
                    markup=icons.terminal,  # Use existing terminal icon
                ),
                name_label,
                name_entry,
            ],
        )
        
        button = Button(
            name="slot-button",  # reuse existing CSS styling
            child=slot_box,
            tooltip_text=f"Attach to session: {session_name}",
            on_clicked=lambda *_: self.attach_to_session(session_name),
            can_focus=True,  # Ensure the button can receive focus
        )
        
        # Add double-click handler to start renaming
        button.connect("button-press-event", self.on_session_click, session_name, name_label, name_entry)
        
        # Add key press handler for 'r' to rename
        button.connect("key-press-event", self.on_slot_key_press, session_name, name_label, name_entry)
        
        # Store reference to entry and label in button for later access
        button.name_entry = name_entry
        button.name_label = name_label
        button.session_name = session_name
        
        return button

    def on_session_click(self, button, event, session_name, label, entry):
        """Handle clicks on session buttons"""
        # Handle double-click to rename
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and event.button == 1:
            self.start_rename(button, session_name, label, entry)
            return True
        # Handle right click for context menu
        elif event.button == 3:
            menu = Gtk.Menu()
            
            # Rename option
            rename_item = Gtk.MenuItem(label="Rename")
            rename_item.connect("activate", lambda _: self.start_rename(button, session_name, label, entry))
            menu.append(rename_item)
            
            # Kill option
            kill_item = Gtk.MenuItem(label="Kill Session")
            kill_item.connect("activate", lambda _: self.kill_session(session_name))
            menu.append(kill_item)
            
            menu.show_all()
            menu.popup_at_pointer(event)
            return True
        
        return False
    
    def start_rename(self, button, session_name, label, entry):
        """Start inline renaming of a session"""
        # Hide label, show entry
        label.set_visible(False)
        entry.set_visible(True)
        
        # Focus entry and select all text
        entry.grab_focus()
        entry.select_region(0, -1)
        
        # Mark button as being edited
        button.get_style_context().add_class("editing")

    def finish_rename(self, button, old_name, entry):
        """Finish renaming a session"""
        new_name = entry.get_text().strip()
        
        # Only rename if the name changed and isn't empty
        if new_name and new_name != old_name:
            self.rename_session(old_name, new_name)
        
        # Reset UI state
        self.cancel_rename(button)
    
    def cancel_rename(self, button):
        """Cancel renaming operation"""
        # Restore original view
        button.name_entry.set_visible(False)
        button.name_label.set_visible(True)
        
        # Remove editing style
        button.get_style_context().remove_class("editing")
        
        # Return focus to session name entry
        self.session_name_entry.grab_focus()
    
    def on_rename_key_press(self, entry, event):
        """Handle key presses in the rename entry"""
        if event.keyval == Gdk.KEY_Escape:
            # Find the parent button
            parent = entry.get_parent()
            while parent and not isinstance(parent, Button):
                parent = parent.get_parent()
            
            if parent:
                self.cancel_rename(parent)
            return True
        
        return False

    def on_session_right_click(self, button, event, session_name):
        """Handle right-click on a session button to show context menu"""
        if event.button == 3:  # Right click
            menu = Gtk.Menu()
            
            # Rename option
            rename_item = Gtk.MenuItem(label="Rename")
            rename_item.connect("activate", lambda _: self.start_rename(
                button, 
                session_name, 
                button.name_label, 
                button.name_entry
            ))
            menu.append(rename_item)
            
            # Kill option
            kill_item = Gtk.MenuItem(label="Kill Session")
            kill_item.connect("activate", lambda _: self.kill_session(session_name))
            menu.append(kill_item)
            
            menu.show_all()
            menu.popup_at_pointer(event)
            return True
        
        return False

    def on_entry_key_press(self, widget, event):
        """Handle key press events in the entry"""
        if event.keyval == Gdk.KEY_Escape:
            self.close_manager()
            return True
        
        # Custom navigation with UP/DOWN keys removed
        return False

    def scroll_to_selected(self, button):
        """Scroll to ensure the selected button is visible"""
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
            # No action if already fully visible
            return False
        GLib.idle_add(scroll)

    def create_session(self, session_name):
        """Create a new tmux session"""
        if not session_name:
            # Get existing session names
            existing_sessions = self.get_tmux_sessions()
            
            # Find the next available number
            counter = 0
            while str(counter) in existing_sessions:
                counter += 1
                
            session_name = str(counter)
            
        try:
            # Clean the session name (replace spaces with underscores)
            clean_name = session_name.strip().replace(" ", "_")
            
            # Create session
            subprocess.run(
                ["tmux", "new-session", "-d", "-s", clean_name],
                check=True
            )
            
            # Refresh the session list
            self.refresh_sessions()
            
            # Clear entry
            self.session_name_entry.set_text("")
            
            # Launch a terminal and attach to this session
            terminal_cmd = self.get_terminal_command(f"tmux attach-session -t {clean_name}")
            exec_shell_command_async(terminal_cmd)
            
            # Close manager
            self.close_manager()
            
        except Exception as e:
            print(f"Error creating tmux session: {e}")

    def attach_to_session(self, session_name):
        """Attach to an existing tmux session"""
        try:
            # Launch a terminal and attach to this session
            terminal_cmd = self.get_terminal_command(f"tmux attach-session -t {session_name}")
            exec_shell_command_async(terminal_cmd)
            self.close_manager()
        except Exception as e:
            print(f"Error attaching to tmux session: {e}")

    def get_terminal_command(self, cmd):
        """Get terminal command based on configured terminal or available terminals"""
        # First try to use the configured terminal command
        if hasattr(data, 'TERMINAL_COMMAND') and data.TERMINAL_COMMAND:
            parts = data.TERMINAL_COMMAND.split()
            terminal = parts[0]
            
            try:
                # Check if the configured terminal is available
                subprocess.run(["which", terminal], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return f"{data.TERMINAL_COMMAND} {cmd}"
            except subprocess.CalledProcessError:
                # If configured terminal is not available, fall back to defaults
                pass
                
        # Fallback to checking available terminals
        terminals = [
            ("kitty", f"kitty -e {cmd}"),
            ("alacritty", f"alacritty -e {cmd}"),
            ("foot", f"foot {cmd}"),
            ("gnome-terminal", f"gnome-terminal -- {cmd}"),
            ("konsole", f"konsole -e {cmd}"),
            ("xfce4-terminal", f"xfce4-terminal -e '{cmd}'"),
        ]
        
        for term, term_cmd in terminals:
            try:
                # Check if terminal is available
                subprocess.run(["which", term], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return term_cmd
            except subprocess.CalledProcessError:
                continue
                
        # Default fallback
        return f"kitty -e {cmd}"

    def rename_session_dialog(self, old_name):
        """Show dialog to rename a session"""
        dialog = Gtk.Dialog(
            title="Rename Session",
            transient_for=None,
            flags=0
        )
        
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK
        )
        
        content_area = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_text(old_name)
        entry.set_activates_default(True)
        content_area.add(entry)
        
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_name = entry.get_text()
            if new_name and new_name != old_name:
                self.rename_session(old_name, new_name)
                
        dialog.destroy()

    def rename_session(self, old_name, new_name):
        """Rename a tmux session"""
        try:
            # Clean the session name (replace spaces with underscores)
            clean_name = new_name.strip().replace(" ", "_")
            
            # Rename session
            subprocess.run(
                ["tmux", "rename-session", "-t", old_name, clean_name],
                check=True
            )
            
            # Refresh the session list
            self.refresh_sessions()
            
        except Exception as e:
            print(f"Error renaming tmux session: {e}")

    def kill_session(self, session_name):
        """Kill a tmux session"""
        try:
            # Kill session
            subprocess.run(
                ["tmux", "kill-session", "-t", session_name],
                check=True
            )
            
            # Refresh the session list
            self.refresh_sessions()
            
            # Close the notch after killing session
            self.close_manager()
            
        except Exception as e:
            print(f"Error killing tmux session: {e}")

    # Add new method to handle key presses on session slots
    def on_slot_key_press(self, button, event, session_name, label, entry):
        """Handle key presses on session buttons"""
        # Print debugging info
        print(f"Key pressed: {event.keyval}, State: {event.state}")
        
        # Check if 'r' key was pressed for renaming
        if event.keyval == Gdk.KEY_r:
            self.start_rename(button, session_name, label, entry)
            return True
        # Check for 'K' (capital K) which indicates Shift is pressed
        elif event.keyval == Gdk.KEY_K:
            print("Shift+K detected - killing session without confirmation")
            self.kill_session(session_name)
            return True
        # Check for lowercase 'k'
        elif event.keyval == Gdk.KEY_k:
            print("Regular k detected - showing confirmation")
            self.show_kill_confirmation_menu(button, session_name)
            return True
        # Check if Delete key was pressed for killing session
        elif event.keyval == Gdk.KEY_Delete:
            self.show_kill_confirmation_menu(button, session_name)
            return True
        return False
    
    def show_kill_confirmation_menu(self, button, session_name):
        """Show a confirmation menu for killing a session"""
        menu = Gtk.Menu()
        
        # Confirmation message as a disabled menu item
        msg_item = Gtk.MenuItem(label=f"Kill session '{session_name}'?")
        msg_item.set_sensitive(False)
        menu.append(msg_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # Confirm option
        confirm_item = Gtk.MenuItem(label="Confirm")
        confirm_item.connect("activate", lambda _: self.kill_session(session_name))
        menu.append(confirm_item)
        
        # Cancel option
        cancel_item = Gtk.MenuItem(label="Cancel")
        # Close notch on cancel
        cancel_item.connect("activate", lambda _: self.close_manager())
        menu.append(cancel_item)
        
        menu.show_all()
        
        # Show the menu positioned at the button
        menu.popup_at_widget(
            button,
            Gdk.Gravity.SOUTH_WEST,
            Gdk.Gravity.NORTH_WEST,
            None
        )
