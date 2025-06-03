import calendar
import subprocess
from datetime import datetime, timedelta

import gi
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.label import Label

import modules.icons as icons

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk


class Calendar(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, name="calendar")

        try:
            origin_date = datetime.fromisoformat(subprocess.check_output(["locale", "week-1stday"]).decode("utf-8")[:-1])
            date = origin_date + timedelta(days=int(subprocess.check_output(["locale", "first_weekday"])) - 1)
            self.first_weekday = date.weekday()
        except Exception as e:
            print(f"Error getting locale first weekday: {e}")
            self.first_weekday = 0

        self.set_halign(Gtk.Align.CENTER)
        self.set_hexpand(False)

        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.current_day = datetime.now().day
        self.previous_key = (self.current_year, self.current_month)

        self.cache_threshold = 1

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
            center_children=[self.month_label],
            end_children=[self.next_month_button],
        )

        self.add(self.header)

        self.weekday_row = Gtk.Box(spacing=4, name="weekday-row")
        self.pack_start(self.weekday_row, False, False, 0)

        self.stack = Gtk.Stack(name="calendar-stack")
        self.stack.set_transition_duration(250)
        self.pack_start(self.stack, True, True, 0)

        self.update_header()
        self.update_calendar()
        self.schedule_midnight_update()

    def schedule_midnight_update(self):
        now = datetime.now()

        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        delta = midnight - now
        seconds_until = delta.total_seconds()
        GLib.timeout_add_seconds(int(seconds_until), self.on_midnight)

    def on_midnight(self):
        now = datetime.now()
        self.current_year = now.year
        self.current_month = now.month
        self.current_day = now.day

        key = (self.current_year, self.current_month)
        if key in self.month_views:
            widget = self.month_views.pop(key)
            self.stack.remove(widget)

        self.update_calendar()
        self.schedule_midnight_update()
        return False

    def update_header(self):

        self.month_label.set_text(
            datetime(self.current_year, self.current_month, 1).strftime("%B %Y").capitalize()
        )

        for child in self.weekday_row.get_children():
            self.weekday_row.remove(child)
        days = self.get_weekday_initials()
        for day in days:
            label = Gtk.Label(label=day.upper(), name="weekday-label")
            self.weekday_row.pack_start(label, True, True, 0)
        self.weekday_row.show_all()

    def update_calendar(self):
        new_key = (self.current_year, self.current_month)

        if new_key > self.previous_key:
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        elif new_key < self.previous_key:
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)

        self.previous_key = new_key

        if new_key not in self.month_views:
            month_view = self.create_month_view(self.current_year, self.current_month)
            self.month_views[new_key] = month_view
            self.stack.add_titled(
                month_view,
                f"{self.current_year}_{self.current_month}",
                f"{self.current_year}_{self.current_month}"
            )

        self.stack.set_visible_child_name(f"{self.current_year}_{self.current_month}")
        self.update_header()
        self.stack.show_all()

        self.prune_cache()

    def prune_cache(self):

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
        cal = calendar.Calendar(firstweekday=self.first_weekday)
        month_days = cal.monthdayscalendar(year, month)

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

        return [datetime(2024, 1, i + 1 + self.first_weekday).strftime("%a")[:1] for i in range(7)]

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