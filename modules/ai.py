from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.revealer import Revealer
from fabric.widgets.entry import Entry  
from widgets.wayland import WaylandWindow as Window
import gi
import asyncio

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
from fabric.widgets.stack import Stack

# Import AI services
from .ai_services import ai_manager

class AI(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="ai-window",
            title="AI Panel",
            size=(400, 600),
            layer="top",
            anchor="top left bottom",
            margin="0px 0px 0px 0px",
            keyboard_mode="exclusive",
            exclusivity="normal",
            visible=False,
            all_visible=False,
            **kwargs,
        )
        self.set_size_request(400, 500)
        
        # Create revealer for slide animation (recommended for WaylandWindow)
        self.revealer = Revealer(
            name="ai-revealer",
            transition_type="slide_right",
            transition_duration=250,
        )
        
        # Main container
        self.main_box = Box(
            orientation="v",
            spacing=16,
            style="border: 4px solid #000; border-radius: 16px; margin: 0px 16px 16px 0px; padding: 24px; min-width: 320px; min-height: 480px; background: #000000;",
        )

        # Title label (handwritten style, large)
        self.title_label = Label(
            label="panel",
            h_align="start",
            style="font-family: 'Comic Sans MS', 'Comic Sans', cursive; font-size: 2em; font-weight: bold; margin-bottom: 12px;"
        )
        self.main_box.add(self.title_label)

        # # Divider (horizontal line)
        # self.divider = Box(
        #     style="min-height: 2px; background-color: #fff; margin: 16px 0 24px 0;",
        #     h_expand=True
        # )
        # self.main_box.add(self.divider)

        # Chat area (scrollable)
        self.chat_scroll = ScrolledWindow(
            name="ai-chat-scroll",
            vexpand=True,
            hexpand=True,
            min_content_height=200,
        )
        
        # Chat container for messages
        self.chat_container = Box(
            name="ai-chat-container",
            orientation="v",
            spacing=8,
            margin_start=8,
            margin_end=8,
            margin_top=8,
            margin_bottom=8,
        )
        
        self.chat_scroll.add(self.chat_container)
        self.main_box.add(self.chat_scroll)

        # Spacer to push dropdown to bottom
        self.spacer = Box(v_expand=True)
        self.main_box.add(self.spacer)

        # Text field and gear button container (horizontal)
        self.input_container = Box(
            orientation="h",
            spacing=8,
            h_align="fill",
            h_expand=True,
            v_align="fill",
            style="margin: 8px 0 8px -18px;"  # Reduced left margin from 8px to 4px
        )
        
        # AI Model selection (gear button only) - now to the left of text field
        self.model_button = Button(
            name="ai-model-button",
            child=Label(name="ai-model-icon", markup="⚙"),  # Gear icon
            tooltip_text="AI Model Settings",
            halign="start"
        )
        self.model_button.connect("clicked", self._on_model_button_clicked)
        
        # Create a popover for the model options
        self.model_popover = Gtk.Popover()
        self.model_popover.set_relative_to(self.model_button)
        self.model_popover.set_position(Gtk.PositionType.BOTTOM)
        
        # Create a vertical box for model options
        self.model_options_box = Box(
            orientation="v",
            spacing=4,
            margin_start=8,
            margin_end=8,
            margin_top=8,
            margin_bottom=8,
            name="ai-model-options-box"
        )
        
        # Create buttons for each model
        ai_models = ["Chat GPT", "Gemini", "Claude", "Grok", "Deepseek"]
        self.model_buttons = {}  # Store references to buttons
        
        for model in ai_models:
            # Default styling for unselected models
            model_button = Button(
                label=model,
                halign="fill",
                name="ai-model-option-button"
            )
            model_button.get_style_context().add_class("ai-model-button-unselected")
            model_button.connect("clicked", self._on_model_option_clicked, model)
            self.model_options_box.add(model_button)
            self.model_buttons[model] = model_button
        
        # Set initial selected model styling
        self.selected_model = "Chat GPT"
        self._update_model_button_styles()
        
        self.model_popover.add(self.model_options_box)
        # self.model_button.set_popover(self.model_popover)  # Not available in GTK3
        
        self.input_container.add(self.model_button)
        
        # Text field (input area) - now multi-line with wrapping
        self.text_view = Gtk.TextView()
        self.text_view.set_name("ai-text-view")
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_hexpand(True)
        self.text_view.set_halign(Gtk.Align.FILL)
        self.text_view.set_vexpand(False)
        self.text_view.set_margin_start(8)
        self.text_view.set_margin_end(8)
        self.text_view.set_margin_top(8)
        self.text_view.set_margin_bottom(8)
        
        # Enable text wrapping to go down a line
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        
        # Set GTK properties for proper expansion
        self.text_view.set_hexpand(True)
        self.text_view.set_halign(Gtk.Align.FILL)
        
        # Enable keyboard shortcuts
        self.text_view.set_accepts_tab(False)  # Disable tab to prevent focus issues
        
        # Connect key press event to handle Enter key
        self.text_view.connect("key-press-event", self._on_text_key_press)
        # Also connect to the buffer to catch all text changes
        self.text_view.get_buffer().connect("insert-text", self._on_text_insert)
        
        # Create a scrolled window for the text view with max height
        self.text_scroll = Gtk.ScrolledWindow()
        self.text_scroll.set_name("ai-text-scroll")
        self.text_scroll.set_hexpand(True)
        self.text_scroll.set_halign(Gtk.Align.FILL)
        self.text_scroll.set_vexpand(False)
        self.text_scroll.set_size_request(-1, 120)  # Max height of 120px (about 6-8 lines)
        self.text_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.text_scroll.add(self.text_view)
        
        # Style the text entry container to match app launcher search field
        self.entry_container = Box(
            h_align="fill",
            h_expand=True,
            v_align="fill",
            name="ai-entry-container"
        )
        self.entry_container.add(self.text_scroll)
        self.input_container.add(self.entry_container)
        
        self.main_box.add(self.input_container)

        # Add the main box to the revealer, and revealer to the window
        self.revealer.add(self.main_box)
        self.add(self.revealer)

    def show_at_position(self, x, y):
        self.move(x, y)
        self.set_visible(True)
        self.show_all()
        
        # Reveal the content with smooth slide animation
        self.revealer.set_reveal_child(True)
        self.grab_focus()
        
        # Ensure key events are captured
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)

    def hide_ai_panel(self):
        print("hide_ai_panel() called")
        # Hide the content with smooth slide animation
        self.revealer.set_reveal_child(False)
        
        # Wait for animation to complete before hiding the window
        GLib.timeout_add(250, self._hide_after_animation)  # 250ms to match animation duration
    
    def _hide_after_animation(self):
        """Hide the window after the revealer animation completes"""
        self.set_visible(False)
        self.hide()
        return False



        # Initialize variable to store the text
        self.current_message = ""
        self.selected_model = "Chat GPT"  # Default model

        # Close window on Escape key press
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.connect("key-press-event", self._on_key_press)
        
        # Also connect to the main window for key events
        self.connect("key-press-event", self._on_key_press)

    def _on_model_button_clicked(self, button):
        """Handle gear button click - manually show popover"""
        self.model_popover.show_all()
        self.model_popover.popup()

    def _on_model_option_clicked(self, button, model_name):
        """Handle model selection from popover"""
        self.selected_model = model_name
        print(f"Selected AI model: {model_name}")
        self._update_model_button_styles() # Update button styles after selection
        # Close the popover after selection
        self.model_popover.hide()

    def on_model_changed(self, combo):
        """Handle model selection change"""
        active_iter = combo.get_active_iter()
        if active_iter is not None:
            selected_model = self.model_store.get_value(active_iter, 0)
            self.selected_model = selected_model
            print(f"Selected AI model: {selected_model}")
            # Hide the dropdown after selection
            self.model_dropdown.set_visible(False)

    def show_ai_panel(self):
        """Show the AI panel with revealer animation"""
        self.show_at_position(0, 0)

    def _on_text_key_press(self, widget, event):
        """Handle key press events in the text entry"""
        # Check for Shift+Enter to insert new line
        if event.keyval == Gdk.KEY_Return and event.state & Gdk.ModifierType.SHIFT_MASK:
            # Set flag to allow newline
            self._shift_pressed = True
            # Insert a newline at cursor position
            buffer = self.text_view.get_buffer()
            buffer.insert_at_cursor("\n")
            # Clear the flag after a short delay
            GLib.timeout_add(100, self._clear_shift_flag)
            return True
        
        # Regular Enter to send message
        elif event.keyval == Gdk.KEY_Return:
            # Prevent default behavior and send message
            self._send_current_message()
            return True
            
        # Handle other keyboard shortcuts
        elif event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.keyval == Gdk.KEY_a:  # Ctrl+A - Select All
                self.text_view.emit("select-all")
                return True
            elif event.keyval == Gdk.KEY_c:  # Ctrl+C - Copy
                self.text_view.emit("copy-clipboard")
                return True
            elif event.keyval == Gdk.KEY_v:  # Ctrl+V - Paste
                self.text_view.emit("paste-clipboard")
                return True
            elif event.keyval == Gdk.KEY_x:  # Ctrl+X - Cut
                self.text_view.emit("cut-clipboard")
                return True
            elif event.keyval == Gdk.KEY_z:  # Ctrl+Z - Undo
                self.text_view.emit("undo")
                return True
            elif event.keyval == Gdk.KEY_y:  # Ctrl+Y - Redo
                self.text_view.emit("redo")
                return True
        
        return False
    
    def _clear_shift_flag(self):
        """Clear the shift pressed flag"""
        if hasattr(self, '_shift_pressed'):
            delattr(self, '_shift_pressed')
        return False

    def _on_text_insert(self, buffer, location, text, length):
        """Handle text insertion to prevent unwanted newlines"""
        # If this is a newline and we're not in Shift+Enter mode, prevent it
        if text == '\n' and not hasattr(self, '_shift_pressed'):
            # Remove the newline
            buffer.delete(location, buffer.get_iter_at_offset(location.get_offset() + 1))
            # Trigger message sending
            self._send_current_message()
            return True
        return False

    def _send_current_message(self):
        """Send the current message to the AI"""
        # Prevent multiple sends
        if hasattr(self, '_sending_message') and self._sending_message:
            return
        
        self._sending_message = True
        
        # Save the text to variable
        self.current_message = self.text_view.get_buffer().get_text(
            self.text_view.get_buffer().get_start_iter(),
            self.text_view.get_buffer().get_end_iter(),
            include_hidden_chars=False
        )
        print(f"Message saved: {self.current_message}")
        
        # Add message to chat only if there's content
        if self.current_message.strip():
            self.add_user_message(self.current_message)
            
            # Clear the text field
            self.text_view.get_buffer().set_text("")
            
            # Here you can add logic to send the message to the selected AI model
            print(f"Sending message to {self.selected_model}: {self.current_message}")
        
        # Reset sending flag after a short delay
        GLib.timeout_add(100, self._reset_sending_flag)
    
    def _reset_sending_flag(self):
        """Reset the sending message flag"""
        self._sending_message = False
        return False

    def add_user_message(self, message):
        """Add a user message to the chat area (right side)"""
        # Create message container
        message_container = Gtk.Box()
        message_container.set_orientation(Gtk.Orientation.HORIZONTAL)
        message_container.set_halign(Gtk.Align.END)  # Right align for user messages
        message_container.set_margin_top(4)
        message_container.set_margin_bottom(4)
        
        # Create message bubble
        message_bubble = Gtk.Box()
        message_bubble.set_name("user-message-bubble")
        message_bubble.get_style_context().add_class("user-message-bubble")
        message_bubble.set_size_request(300, -1)  # Max width: 300px, height: expand
        message_bubble.set_vexpand(False)
        message_bubble.set_hexpand(False)
        
        # Create message text view for better text wrapping
        message_text = Gtk.TextView()
        message_text.set_name("user-message-text")
        message_text.get_style_context().add_class("user-message-text")
        message_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        message_text.set_editable(False)
        message_text.set_cursor_visible(False)
        message_text.set_size_request(220, 60)  # Fixed width and height
        message_text.set_hexpand(False)
        message_text.set_halign(Gtk.Align.START)
        message_text.set_vexpand(False)
        message_text.set_margin_start(6)
        message_text.set_margin_end(6)
        message_text.set_margin_top(3)
        message_text.set_margin_bottom(3)
        
        # Set the text content
        text_buffer = message_text.get_buffer()
        text_buffer.set_text(message)
        
        message_bubble.add(message_text)
        message_container.add(message_bubble)
        
        # Add to chat container
        self.chat_container.add(message_container)
        
        # Scroll to bottom
        self.chat_scroll.get_vadjustment().set_value(
            self.chat_scroll.get_vadjustment().get_upper()
        )
        
        # Show the new message
        self.chat_container.show_all()
        
        # Get AI response
        self.get_ai_response(message)
    
    def add_ai_message(self, message):
        """Add an AI message to the chat area (left side)"""
        # Create message container
        message_container = Gtk.Box()
        message_container.set_orientation(Gtk.Orientation.HORIZONTAL)
        message_container.set_halign(Gtk.Align.START)  # Left align for AI messages
        message_container.set_margin_top(4)
        message_container.set_margin_bottom(4)
        
        # Create message bubble
        message_bubble = Gtk.Box()
        message_bubble.set_name("ai-message-bubble")
        message_bubble.get_style_context().add_class("ai-message-bubble")
        message_bubble.set_size_request(300, -1)  # Max width: 300px, height: expand
        message_bubble.set_vexpand(False)
        message_bubble.set_hexpand(False)
        
        # Create message text view for better text wrapping
        message_text = Gtk.TextView()
        message_text.set_name("ai-message-text")
        message_text.get_style_context().add_class("ai-message-text")
        message_text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        message_text.set_editable(False)
        message_text.set_cursor_visible(False)
        message_text.set_size_request(220, 60)  # Fixed width and height
        message_text.set_hexpand(False)
        message_text.set_halign(Gtk.Align.START)
        message_text.set_vexpand(False)
        message_text.set_margin_start(6)
        message_text.set_margin_end(6)
        message_text.set_margin_top(3)
        message_text.set_margin_bottom(3)
        
        # Set the text content
        text_buffer = message_text.get_buffer()
        text_buffer.set_text(message)
        
        message_bubble.add(message_text)
        message_container.add(message_bubble)
        
        # Add to chat container
        self.chat_container.add(message_container)
        
        # Scroll to bottom
        self.chat_scroll.get_vadjustment().set_value(
            self.chat_scroll.get_vadjustment().get_upper()
        )
        
        # Show the new message
        self.chat_container.show_all()
    
    def get_ai_response(self, user_message):
        """Get response from the selected AI model"""
        # Show typing indicator
        self.show_typing_indicator()
        
        def _run_async_response():
            """Run the async response in a new event loop"""
            async def _get_response():
                try:
                    response = await ai_manager.get_response(self.selected_model, user_message)
                    # Hide typing indicator and show response
                    GLib.idle_add(self.hide_typing_indicator)
                    GLib.idle_add(self.add_ai_message, response)
                except Exception as e:
                    error_msg = f"Error getting AI response: {str(e)}"
                    GLib.idle_add(self.hide_typing_indicator)
                    GLib.idle_add(self.add_ai_message, error_msg)
            
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_get_response())
            finally:
                loop.close()
        
        # Run the async function in a new thread
        import threading
        thread = threading.Thread(target=_run_async_response)
        thread.daemon = True
        thread.start()
    
    def show_typing_indicator(self):
        """Show typing indicator with animated dots"""
        print("Showing typing indicator")
        
        # Create typing indicator container
        typing_container = Gtk.Box()
        typing_container.set_orientation(Gtk.Orientation.HORIZONTAL)
        typing_container.set_halign(Gtk.Align.START)  # Left align for AI messages
        typing_container.set_margin_top(4)
        typing_container.set_margin_bottom(4)
        
        # Create typing bubble
        typing_bubble = Gtk.Box()
        typing_bubble.set_name("typing-bubble")
        typing_bubble.get_style_context().add_class("typing-bubble")
        typing_bubble.set_size_request(80, 40)  # Small size for typing indicator
        typing_bubble.set_vexpand(False)
        typing_bubble.set_hexpand(False)
        
        # Create dots container
        dots_container = Gtk.Box()
        dots_container.set_orientation(Gtk.Orientation.HORIZONTAL)
        dots_container.set_spacing(4)
        dots_container.set_margin_start(12)
        dots_container.set_margin_end(12)
        dots_container.set_margin_top(8)
        dots_container.set_margin_bottom(8)
        
        # Create three animated dots
        self.typing_dots = []
        for i in range(3):
            dot = Gtk.Label()
            dot.set_name(f"typing-dot-{i}")
            dot.get_style_context().add_class("typing-dot")
            dot.get_style_context().add_class("typing-dot-inactive")
            dot.set_text("●")
            dots_container.add(dot)
            self.typing_dots.append(dot)
            print(f"Created dot {i}")
        
        typing_bubble.add(dots_container)
        typing_container.add(typing_bubble)
        
        # Add to chat container
        self.chat_container.add(typing_container)
        
        # Scroll to bottom
        self.chat_scroll.get_vadjustment().set_value(
            self.chat_scroll.get_vadjustment().get_upper()
        )
        
        # Show the typing indicator
        self.chat_container.show_all()
        
        # Store reference to typing container for removal
        self.current_typing_container = typing_container
        
        # Initialize animation state
        self._dot_index = 0
        
        print(f"Starting animation with {len(self.typing_dots)} dots")
        # Start animation
        GLib.timeout_add(500, self._animate_typing_dots)
    
    def hide_typing_indicator(self):
        """Hide the typing indicator"""
        if hasattr(self, 'current_typing_container') and self.current_typing_container:
            self.chat_container.remove(self.current_typing_container)
            self.current_typing_container = None
            self.chat_container.show_all()
    
    def _animate_typing_dots(self):
        """Animate the typing dots"""
        if not hasattr(self, 'typing_dots') or not self.typing_dots:
            print("No typing dots found")
            return False
        
        print(f"Animating dots, index: {self._dot_index}")
        
        # Simple animation: cycle through dots
        for i, dot in enumerate(self.typing_dots):
            if i == (self._dot_index % 3):
                dot.get_style_context().add_class("typing-dot-active")
                dot.get_style_context().remove_class("typing-dot-inactive")
                print(f"Dot {i} is now active")
            else:
                dot.get_style_context().add_class("typing-dot-inactive")
                dot.get_style_context().remove_class("typing-dot-active")
        
        # Update dot index
        self._dot_index += 1
        
        # Continue animation if typing indicator is still visible
        if hasattr(self, 'current_typing_container') and self.current_typing_container:
            GLib.timeout_add(500, self._animate_typing_dots)
        
        return False  # Important: return False to stop the timeout

    def _on_key_press(self, widget, event):
        # Close window when Escape key is pressed
        if event.keyval == Gdk.KEY_Escape:
            print("Escape key pressed - closing AI panel")
            self.hide_ai_panel()
            return True
        return False
    
    def do_key_press_event(self, event):
        """Override key press event for the window"""
        if event.keyval == Gdk.KEY_Escape:
            print("Escape key pressed (do_key_press_event) - closing AI panel")
            self.hide_ai_panel()
            return True
        return super().do_key_press_event(event) 

    def _update_model_button_styles(self):
        """Update the styles of all model buttons to reflect the selected model."""
        for model_name, button in self.model_buttons.items():
            if model_name == self.selected_model:
                button.get_style_context().add_class("ai-model-button-selected")
                button.get_style_context().remove_class("ai-model-button-unselected")
            else:
                button.get_style_context().add_class("ai-model-button-unselected")
                button.get_style_context().remove_class("ai-model-button-selected") 