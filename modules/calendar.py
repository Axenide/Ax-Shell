import calendar
from datetime import datetime
import gi
import modules.icons as icons
from fabric.widgets.label import Label
from fabric.widgets.centerbox import CenterBox

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

class Calendar(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, name="calendar")

        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.current_day = datetime.now().day
        # Store previous month/year to determine transition direction.
        self.previous_key = (self.current_year, self.current_month)

        # Cache threshold in number of months away from the current view.
        self.cache_threshold = 1  # Allow current month +/- 1 month

        # Dictionary to store built views for each month.
        self.month_views = {}

        self.prev_month_button = Gtk.Button(
            name="prev-month-button",
            child=Label(name="month-button-label", markup=icons.chevron_left)
        )
        self.prev_month_button.connect("clicked", self.on_prev_month_clicked)

        self.month_label = Gtk.Label(name="month-label")

        self.next_month_button = Gtk.Button(
            name="next-month-button",
            child=Label(name="month-button-label", markup=icons.chevron_right)
        )
        self.next_month_button.connect("clicked", self.on_next_month_clicked)

        self.header = CenterBox(
            spacing=4,
            name="header",
            start_children=[self.prev_month_button],
            center_children=[self.month_label,],
            end_children=[self.next_month_button],
        )

        self.add(self.header)

        self.weekday_row = Gtk.Box(spacing=4, name="weekday-row")
        self.pack_start(self.weekday_row, False, False, 0)

        # Create a stack to hold month days views.
        self.stack = Gtk.Stack(name="calendar-stack")
        self.stack.set_transition_duration(250)
        self.pack_start(self.stack, True, True, 0)

        self.update_header()
        self.update_calendar()
        GLib.timeout_add_seconds(60, self.check_date_change)

    def update_header(self):
        # Update header month label and weekday row.
        self.month_label.set_text(
            datetime(self.current_year, self.current_month, 1).strftime("%B %Y").capitalize()
        )
        # Clear existing children from weekday_row.
        for child in self.weekday_row.get_children():
            self.weekday_row.remove(child)
        days = self.get_weekday_initials()
        for day in days:
            label = Gtk.Label(label=day.upper(), name="weekday-label")
            self.weekday_row.pack_start(label, True, True, 0)
        self.weekday_row.show_all()

    def update_calendar(self):
        new_key = (self.current_year, self.current_month)
        # Set the transition type based on whether we're moving to a later or earlier month.
        if new_key > self.previous_key:
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        elif new_key < self.previous_key:
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
        # Update previous key for next comparison.
        self.previous_key = new_key

        # Create the month view if it doesn't exist.
        if new_key not in self.month_views:
            month_view = self.create_month_view(self.current_year, self.current_month)
            self.month_views[new_key] = month_view
            self.stack.add_titled(
                month_view,
                f"{self.current_year}_{self.current_month}",
                f"{self.current_year}_{self.current_month}"
            )
        # Switch the visible child in the stack.
        self.stack.set_visible_child_name(f"{self.current_year}_{self.current_month}")
        self.update_header()
        self.stack.show_all()

        # Purge any cached month views that are too far away.
        self.prune_cache()

    def prune_cache(self):
        # Compute a numerical value for a (year, month) key.
        def month_index(key):
            year, month = key
            return year * 12 + (month - 1)

        current_index = month_index((self.current_year, self.current_month))
        keys_to_remove = []
        for key in self.month_views:
            if abs(month_index(key) - current_index) > self.cache_threshold:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            widget = self.month_views.pop(key)
            self.stack.remove(widget)

    def create_month_view(self, year, month):
        grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=False, name="calendar-grid")
        cal = calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(year, month)
        # Ensure 6 rows for consistency.
        while len(month_days) < 6:
            month_days.append([0] * 7)

        for row, week in enumerate(month_days):
            for col, day in enumerate(week):
                day_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, name="day-box")
                top_spacer = Gtk.Box(hexpand=True, vexpand=True)
                middle_box = Gtk.Box(hexpand=True, vexpand=True)
                bottom_spacer = Gtk.Box(hexpand=True, vexpand=True)

                if day == 0:
                    label = Label(name="day-empty", markup=icons.dot)
                else:
                    label = Gtk.Label(label=str(day), name="day-label")
                    if (
                        day == self.current_day
                        and month == datetime.now().month
                        and year == datetime.now().year
                    ):
                        label.get_style_context().add_class("current-day")

                # Center the label in the middle_box.
                middle_box.pack_start(Gtk.Box(hexpand=True, vexpand=True), True, True, 0)
                middle_box.pack_start(label, False, False, 0)
                middle_box.pack_start(Gtk.Box(hexpand=True, vexpand=True), True, True, 0)

                day_box.pack_start(top_spacer, True, True, 0)
                day_box.pack_start(middle_box, True, True, 0)
                day_box.pack_start(bottom_spacer, True, True, 0)

                grid.attach(day_box, col, row, 1, 1)
        grid.show_all()
        return grid

    def get_weekday_initials(self):
        # Returns localized weekday initials.
        return [datetime(2025, 1, i + 6).strftime("%a")[:1] for i in range(7)]

    def on_prev_month_clicked(self, widget):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.update_calendar()

    def on_next_month_clicked(self, widget):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.update_calendar()

    def check_date_change(self):
        now = datetime.now()
        if now.day != self.current_day or now.month != self.current_month or now.year != self.current_year:
            self.current_day = now.day
            self.current_month = now.month
            self.current_year = now.year
            self.update_calendar()
        return True
