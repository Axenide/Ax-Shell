from pydoc import text
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
from gi.repository import Gtk, Gdk, GLib, Pango

# Import AI services
from .ai_services import ai_manager
 
# Utility to break long unbreakable words for GTK Label wrapping
import re
def break_long_words(text, n=20):
    return re.sub(r'(\S{' + str(n) + r',})', lambda m: '\u200b'.join([m.group(0)[i:i+n] for i in range(0, len(m.group(0)), n)]), text)

class AI(Window):
    def __init__(self, **kwargs):
        super().__init__(
            name="ai-window",
            title="AI Panel",
            size=(400, 600),
            layer="top",
            anchor="top left bottom",
            keyboard_mode="on-demand",  # Changed from 'none' to 'on-demand'
            exclusivity="none",
            visible=False,
            all_visible=False,
            **kwargs,
        )
        self.set_size_request(400, 500)
        # self.steal_input()  # Removed to allow normal input
        
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
        self.main_box.set_hexpand(True)
        self.main_box.set_halign(Gtk.Align.FILL)

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
            min_content_height=200,
        )
        self.chat_scroll.set_size_request(384, -1)
        
        # Chat container for messages
        self.chat_container = Box(
            name="ai-chat-container",
            orientation="v",
            spacing=8,
            margin_start=0,  # Set to 0 for flush left
            margin_end=8,
            margin_top=8,
            margin_bottom=8,
        )
        self.chat_container.set_hexpand(True)
        self.chat_container.set_halign(Gtk.Align.FILL)
        # Wrap in Gtk.Alignment to constrain width
        self.chat_alignment = Gtk.Alignment.new(0.0, 0, 0, 0)
        self.chat_alignment.set_hexpand(True)
        self.chat_alignment.set_halign(Gtk.Align.START)
        #self.chat_alignment.set_size_request(384, -1)
        self.chat_alignment.add(self.chat_container)
        self.chat_scroll.add(self.chat_alignment)
        self.main_box.add(self.chat_scroll)

        # Spacer to push dropdown to bottom
        self.spacer = Box(v_expand=True)
        self.main_box.add(self.spacer)

        # Text field and gear button container (horizontal)
        self.input_container = Box(
            orientation="h",
            spacing=8,
            h_align="fill",
            v_align="fill",
            hexpand=True,
            style="margin: 8px 0 8px -18px;"  # Reduced left margin from 8px to 4px
        )
        self.input_container.set_hexpand(True)
        self.input_container.set_halign(Gtk.Align.FILL)
        
        # AI Model selection (gear button only) - now to the left of text field
        self.model_button = Button(
            name="ai-model-button",
            child=Label(name="ai-model-icon", markup="⚙"),  # Gear icon
            tooltip_text="AI Model Settings",
            halign=Gtk.Align.START,
            hexpand=False
        )
        self.model_button.set_size_request(-1, 40)
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
        
        # Text field (input area) - multiline, scrollable, wrapped
        self.text_entry = Gtk.TextView()
        self.text_entry.set_name("ai-text-entry")
        self.text_entry.set_hexpand(True)
        self.text_entry.set_halign(Gtk.Align.FILL)
        self.text_entry.set_vexpand(True)
        self.text_entry.set_margin_top(0)
        self.text_entry.set_margin_bottom(0)
        self.text_entry.set_sensitive(True)
        self.text_entry.set_editable(True)
        self.text_entry.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        # Make text entry scrollable
        self.text_scroll = Gtk.ScrolledWindow()
        self.text_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.text_scroll.set_hexpand(True)
        self.text_scroll.set_vexpand(True)
        self.text_scroll.set_min_content_height(40)
        self.text_scroll.set_min_content_width(100)
        self.text_scroll.get_style_context().add_class('ai-text-scroll')
        self.text_scroll.set_vexpand(False)
        self.text_scroll.add(self.text_entry)


        # Add scrolled window to input_container for full width
        self.input_container.add(self.text_scroll)
        # Remove Entry 'activate' signal (not valid for TextView)
        # To send on Enter, handle key-press-event on TextView if needed
        
        self.main_box.add(self.input_container)

        # Add the main box to the revealer, and revealer to the window
        self.revealer.add(self.main_box)
        self.add(self.revealer)

    def show_at_position(self, x, y):
        self.move(x, y)
        self.set_visible(True)
        self.present()  # Bring window to front
        self.grab_focus()  # Grab window focus
        self.show_all()
        
        # Reveal the content with smooth slide animation
        self.revealer.set_reveal_child(True)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        
        # Focus the text entry after window is mapped
        GLib.idle_add(self.text_entry.grab_focus)
        
        # Connect key press and key release events to the text entry
        self.text_entry.connect("key-press-event", self._on_text_entry_key_press)
        self.text_entry.connect("key-release-event", self._on_text_entry_key_release)

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

    def _on_entry_activate(self, entry):
        print("[DEBUG] Entry activate signal fired")
        """Send the current message to the AI when Enter is pressed in Entry"""
        self.current_message = entry.get_text()
        print(f"Message saved: {self.current_message}")
        if self.current_message.strip():
            self.add_user_message(self.current_message)
            entry.set_text("")
            print(f"Sending message to {self.selected_model}: {self.current_message}")

    def _send_current_message(self):
        buffer = self.text_entry.get_buffer()
        start_iter = buffer.get_start_iter()
        end_iter = buffer.get_end_iter()
        message = buffer.get_text(start_iter, end_iter, True).strip()
        if message:
            self.add_user_message(message)
            buffer.set_text("")  # Clear the text field
    
    def _reset_sending_flag(self):
        """Reset the sending message flag"""
        self._sending_message = False
        return False

    def add_user_message(self, message):
        """Add a user message to the chat area (right side)"""
        message = break_long_words(message)
        # Create message container
        message_container = Box(
            orientation="h",
            h_align="end",
            margin_top=8,
            margin_bottom=8,
            margin_start=8,
            margin_end=8,
        )
        message_container.set_hexpand(True)
        message_container.set_halign(Gtk.Align.END)  # <--- THIS IS CRITICAL
        
        # Create message bubble
        message_bubble = Box(
            name="user-message-bubble",
            orientation="h",
            vexpand=False,
            margin_top=2,
            margin_bottom=2,
            margin_start=0,
            margin_end=0
        )
        message_bubble.set_hexpand(True)
        message_bubble.set_halign(Gtk.Align.FILL)
        # Create message label for text
        message_label = Label(
            label=message,
            wrap=True,
            xalign=0.0,
            selectable=True,
            style="color: #fff; font-size: 1em; padding: 2px;"
        )
        message_label.set_xalign(0.0)
        message_label.set_hexpand(True)
        message_label.set_halign(Gtk.Align.END)
        message_label.set_line_wrap(True)
        message_label.set_max_width_chars(40)
        message_label.set_ellipsize(Pango.EllipsizeMode.NONE)
        message_bubble.add(message_label)
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
        message = break_long_words(message)
        # Create message container
        message_container = Box(
            orientation="h",
            h_align="start",
            margin_top=8,
            margin_bottom=8,
            margin_start=8,    # Same margin as user
            margin_end=8,      # Same margin as user
        )
        # Create message bubble
        message_bubble = Box(
            name="ai-message-bubble",
            orientation="h",
            vexpand=False,
            margin_top=2,
            margin_bottom=2,
            margin_start=0,   # No extra margin on bubble
            margin_end=0,
            style="background: #444; border-radius: 16px; padding: 10px;"
        )
        message_bubble.set_hexpand(False)
        message_bubble.set_halign(Gtk.Align.START)
        # Create message label for text
        message_label = Label(
            label=message,
            wrap=True,
            xalign=0.0,
            selectable=True,
            style="color: #fff; font-size: 1em; padding: 2px;"
        )
        message_label.set_hexpand(True)
        message_label.set_halign(Gtk.Align.END)
        message_label.set_line_wrap(True)
        message_label.set_max_width_chars(40)
        message_label.set_ellipsize(Pango.EllipsizeMode.NONE)
        message_bubble.add(message_label)
        message_container.add(message_bubble)
        self.chat_container.add(message_container)
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
        typing_container = Box(
            orientation="h",
            h_align="start",
            margin_top=4,
            margin_bottom=4,
        )
        
        # Create typing bubble
        typing_bubble = Box(
            name="typing-bubble",
            v_expand=False,
            h_expand=False,
        )
        typing_bubble.get_style_context().add_class("typing-bubble")
        typing_bubble.set_size_request(80, 40)  # Small size for typing indicator
        
        # Create dots container
        dots_container = Box(
            orientation="h",
            spacing=4,
            margin_start=12,
            margin_end=12,
            margin_top=8,
            margin_bottom=8,
        )
        
        # Create three animated dots
        self.typing_dots = []
        for i in range(3):
            dot = Label(
                name=f"typing-dot-{i}",
                text="●",
            )
            dot.get_style_context().add_class("typing-dot")
            dot.get_style_context().add_class("typing-dot-inactive")
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
        return Gtk.Window.do_key_press_event(self, event)

    def _on_text_entry_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Return and not (event.state & Gdk.ModifierType.SHIFT_MASK):
            self._send_current_message()
            return True
        return False

    def _on_text_entry_key_release(self, widget, event):
        """Handle key release events on the text entry."""
        print(f"Text entry key release: {Gdk.keyval_name(event.keyval)} ({event.keyval})")
        return False  # Return False to allow other handlers to process the event

    def _update_model_button_styles(self):
        """Update the styles of all model buttons to reflect the selected model."""
        for model_name, button in self.model_buttons.items():
            if model_name == self.selected_model:
                button.get_style_context().add_class("ai-model-button-selected")
                button.get_style_context().remove_class("ai-model-button-unselected")
            else:
                button.get_style_context().add_class("ai-model-button-unselected")
                button.get_style_context().remove_class("ai-model-button-selected") 