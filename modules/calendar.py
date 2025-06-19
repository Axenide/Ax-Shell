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
    def __init__(self, view_mode="month"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8, name="calendar")
        self.view_mode = view_mode

        try:
            origin_date_str = subprocess.check_output(["locale", "week-1stday"], text=True).strip()
            first_weekday_val = int(subprocess.check_output(["locale", "first_weekday"], text=True).strip())
            
            origin_date = datetime.fromisoformat(origin_date_str)
            # Esta lógica calcula el día de la semana (0-6, Lunes=0) que es considerado el primero
            # según la configuración regional combinada de week-1stday y first_weekday.
            date_of_first_day_of_week_config = origin_date + timedelta(days=first_weekday_val - 1)
            self.first_weekday = date_of_first_day_of_week_config.weekday() # Lunes=0, ..., Domingo=6
        except Exception as e:
            print(f"Error getting locale first weekday: {e}")
            self.first_weekday = 0  # Por defecto Lunes

        self.set_halign(Gtk.Align.CENTER)
        self.set_hexpand(False)

        self.current_day_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if self.view_mode == "month":
            self.current_shown_date = self.current_day_date.replace(day=1)
            self.current_year = self.current_shown_date.year
            self.current_month = self.current_shown_date.month
            self.current_day = self.current_day_date.day # Solo para resaltar en create_month_view
            self.previous_key = (self.current_year, self.current_month)
        elif self.view_mode == "week":
            # current_shown_date es el primer día (según locale) de la semana actual
            days_to_subtract = (self.current_day_date.weekday() - self.first_weekday + 7) % 7
            self.current_shown_date = self.current_day_date - timedelta(days=days_to_subtract)
            self.current_year = self.current_shown_date.year # Para el header
            self.current_month = self.current_shown_date.month # Para el header
            iso_year, iso_week, _ = self.current_shown_date.isocalendar()
            self.previous_key = (iso_year, iso_week)
            self.set_halign(Gtk.Align.FILL)
            self.set_hexpand(True)
            self.set_valign(Gtk.Align.CENTER)
            self.set_vexpand(False)
        
        self.cache_threshold = 3 # Umbral para mantener vistas en caché

        self.month_views = {} # Reutilizado para vistas de semana también

        self.prev_button = Gtk.Button( # Nombre genérico del botón
            name="prev-month-button", 
            child=Label(name="month-button-label", markup=icons.chevron_left) # CSS puede ser genérico
        )
        self.prev_button.connect("clicked", self.on_prev_clicked)

        self.month_label = Gtk.Label(name="month-label") # El nombre es histórico, pero muestra mes/año

        self.next_button = Gtk.Button( # Nombre genérico del botón
            name="next-month-button",
            child=Label(name="month-button-label", markup=icons.chevron_right) # CSS puede ser genérico
        )
        self.next_button.connect("clicked", self.on_next_clicked)

        self.header = CenterBox(
            spacing=4,
            name="header",
            start_children=[self.prev_button],
            center_children=[self.month_label],
            end_children=[self.next_button],
        )

        self.add(self.header)

        self.weekday_row = Gtk.Box(spacing=4, name="weekday-row")
        self.pack_start(self.weekday_row, False, False, 0)

        self.stack = Gtk.Stack(name="calendar-stack")
        self.stack.set_transition_duration(250)
        self.pack_start(self.stack, True, True, 0)

        self.update_header() # Llamar antes de update_calendar para que el primer header sea correcto
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
        self.current_day_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

        key_to_remove_for_today_highlight = None
        if self.view_mode == "month":
            # Actualizar la fecha base para la vista de mes si es necesario (aunque usualmente no cambia a medianoche)
            self.current_shown_date = self.current_day_date.replace(day=1)
            self.current_year = self.current_shown_date.year
            self.current_month = self.current_shown_date.month
            self.current_day = self.current_day_date.day # Actualizar el día actual
            key_to_remove_for_today_highlight = (self.current_year, self.current_month)
        elif self.view_mode == "week":
            days_to_subtract = (self.current_day_date.weekday() - self.first_weekday + 7) % 7
            self.current_shown_date = self.current_day_date - timedelta(days=days_to_subtract)
            self.current_year = self.current_shown_date.year # Para el header
            self.current_month = self.current_shown_date.month # Para el header
            iso_year, iso_week, _ = self.current_shown_date.isocalendar()
            key_to_remove_for_today_highlight = (iso_year, iso_week)

        # Eliminar la vista actual de la caché para forzar la regeneración con el nuevo "hoy" resaltado
        if key_to_remove_for_today_highlight and key_to_remove_for_today_highlight in self.month_views:
            widget = self.month_views.pop(key_to_remove_for_today_highlight)
            self.stack.remove(widget)
            # Si la vista eliminada era la actual, previous_key podría quedar desactualizado
            # pero update_calendar lo corregirá al establecer la nueva vista.

        self.update_calendar() # Esto regenerará la vista si fue eliminada y actualizará el resaltado
        self.schedule_midnight_update()
        return False # Importante para que el timeout no se repita automáticamente

    def update_header(self):
        # self.current_shown_date es el primer día del mes (modo mes) o el primer día de la semana (modo semana)
        # El encabezado siempre muestra el mes y año de self.current_shown_date
        self.month_label.set_text(
            self.current_shown_date.strftime("%B %Y").capitalize()
        )

        for child in self.weekday_row.get_children():
            self.weekday_row.remove(child)
        
        day_initials = self.get_weekday_initials()
        for day_initial in day_initials:
            label = Gtk.Label(label=day_initial.upper(), name="weekday-label")
            self.weekday_row.pack_start(label, True, True, 0)
        self.weekday_row.show_all()

    def update_calendar(self):
        new_key = None
        child_name = "" # Renombrado de child_name_prefix
        view_widget = None

        if self.view_mode == "month":
            new_key = (self.current_year, self.current_month)
            child_name = f"{self.current_year}_{self.current_month}"
            if new_key not in self.month_views:
                view_widget = self.create_month_view(self.current_year, self.current_month)
        elif self.view_mode == "week":
            iso_year, iso_week, _ = self.current_shown_date.isocalendar()
            new_key = (iso_year, iso_week)
            child_name = f"{iso_year}_w{iso_week}"
            if new_key not in self.month_views:
                # Pasar self.current_shown_date directamente a create_week_view
                view_widget = self.create_week_view(self.current_shown_date)
        
        if new_key is None: return

        if new_key > self.previous_key:
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
        elif new_key < self.previous_key:
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
        # else: no transition if key is the same (e.g. on_midnight for same month/week)

        self.previous_key = new_key

        if view_widget: # Si se creó una nueva vista
            self.month_views[new_key] = view_widget
            self.stack.add_titled(view_widget, child_name, child_name)
        
        self.stack.set_visible_child_name(child_name)
        # El encabezado se actualiza ANTES de llamar a update_calendar en __init__ y on_clicked,
        # y también en on_midnight si es necesario.
        # Pero si la vista cambia (ej. de Enero a Febrero), el encabezado debe reflejarlo.
        self.update_header() # Asegurar que el header está sincronizado con la vista actual
        self.stack.show_all()

        self.prune_cache()

    def prune_cache(self):
        def get_key_index(key_tuple):
            year, num = key_tuple # num es month o week_number
            if self.view_mode == "month": # Asumiendo que la clave es (año, mes)
                return year * 12 + (num - 1)
            else: # Asumiendo que la clave es (año_iso, semana_iso)
                return year * 53 + num # Usar 53 para cubrir años con 53 semanas ISO

        current_index = get_key_index(self.previous_key) # previous_key es la clave de la vista actual
        keys_to_remove = []
        for key_iter in self.month_views:
            if abs(get_key_index(key_iter) - current_index) > self.cache_threshold:
                keys_to_remove.append(key_iter)
        for key_to_remove in keys_to_remove:
            widget = self.month_views.pop(key_to_remove)
            self.stack.remove(widget)

    def create_month_view(self, year, month):
        grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=False, name="calendar-grid")
        cal = calendar.Calendar(firstweekday=self.first_weekday)
        month_days = cal.monthdayscalendar(year, month)

        while len(month_days) < 6: # Asegurar 6 filas para consistencia visual
            month_days.append([0] * 7) # [0] representa un día vacío

        for row, week in enumerate(month_days):
            for col, day_num in enumerate(week):
                day_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, name="day-box")
                top_spacer = Gtk.Box(hexpand=True, vexpand=True)
                middle_box = Gtk.Box(hexpand=True, vexpand=True)
                bottom_spacer = Gtk.Box(hexpand=True, vexpand=True)

                if day_num == 0:
                    label = Label(name="day-empty", markup=icons.dot)
                else:
                    label = Gtk.Label(label=str(day_num), name="day-label")
                    day_date_obj = datetime(year, month, day_num)
                    if day_date_obj == self.current_day_date:
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

    def create_week_view(self, first_day_of_week_to_display):
        grid = Gtk.Grid(column_homogeneous=True, row_homogeneous=False, name="calendar-grid-week-view") # Podría tener estilo diferente
        
        # El mes de referencia para atenuar es el mes de first_day_of_week_to_display
        # que es self.current_shown_date, y su mes es self.current_month (actualizado en nav)
        reference_month_for_dimming = first_day_of_week_to_display.month

        for col in range(7):
            current_day_in_loop = first_day_of_week_to_display + timedelta(days=col)
            
            day_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, name="day-box") # Reusar estilo de day-box
            top_spacer = Gtk.Box(hexpand=True, vexpand=True)
            middle_box = Gtk.Box(hexpand=True, vexpand=True)
            bottom_spacer = Gtk.Box(hexpand=True, vexpand=True)

            label = Gtk.Label(label=str(current_day_in_loop.day), name="day-label")

            if current_day_in_loop == self.current_day_date:
                label.get_style_context().add_class("current-day")
            
            if current_day_in_loop.month != reference_month_for_dimming:
                 label.get_style_context().add_class("dim-label") # Necesita CSS: .dim-label { opacity: 0.5; } o similar

            middle_box.pack_start(Gtk.Box(hexpand=True, vexpand=True), True, True, 0)
            middle_box.pack_start(label, False, False, 0)
            middle_box.pack_start(Gtk.Box(hexpand=True, vexpand=True), True, True, 0)

            day_box.pack_start(top_spacer, True, True, 0)
            day_box.pack_start(middle_box, True, True, 0)
            day_box.pack_start(bottom_spacer, True, True, 0)
            
            grid.attach(day_box, col, 0, 1, 1) # Todos los días en la fila 0
        
        # Para mantener una altura similar a la vista mensual, se podrían añadir filas vacías.
        # Esto es opcional y depende del diseño deseado.
        # for r_idx in range(1, 6): # Añadir 5 filas vacías
        #     empty_row_placeholder = Gtk.Box(name="day-empty-placeholder", hexpand=True, vexpand=True, height_request=20) # Ajustar altura
        #     grid.attach(empty_row_placeholder, 0, r_idx, 7, 1) # Abarca las 7 columnas

        grid.show_all()
        return grid

    def get_weekday_initials(self):
        # Genera las iniciales de los días de la semana comenzando por self.first_weekday
        # datetime(2024, 1, 1) es Lunes. Su weekday() es 0.
        # Si self.first_weekday es 0 (Lunes), queremos que el primer día sea Lunes.
        #   i=0: datetime(2024, 1, 1 + 0) -> Lunes
        # Si self.first_weekday es 6 (Domingo), queremos que el primer día sea Domingo.
        #   i=0: datetime(2024, 1, 1 + 6) -> Domingo
        # Esta lógica es correcta.
        return [(datetime(2024, 1, 1) + timedelta(days=(self.first_weekday + i) % 7)).strftime("%a")[:1] for i in range(7)]


    def on_prev_clicked(self, widget):
        if self.view_mode == "month":
            current_month_val = self.current_shown_date.month
            current_year_val = self.current_shown_date.year
            if current_month_val == 1:
                self.current_shown_date = self.current_shown_date.replace(year=current_year_val - 1, month=12)
            else:
                self.current_shown_date = self.current_shown_date.replace(month=current_month_val - 1)
            self.current_year = self.current_shown_date.year
            self.current_month = self.current_shown_date.month
        elif self.view_mode == "week":
            self.current_shown_date -= timedelta(days=7)
            self.current_year = self.current_shown_date.year # Actualizar para el header
            self.current_month = self.current_shown_date.month # Actualizar para el header y dimming
        
        # self.update_header() # Se llama dentro de update_calendar
        self.update_calendar()

    def on_next_clicked(self, widget):
        if self.view_mode == "month":
            current_month_val = self.current_shown_date.month
            current_year_val = self.current_shown_date.year
            if current_month_val == 12:
                self.current_shown_date = self.current_shown_date.replace(year=current_year_val + 1, month=1)
            else:
                self.current_shown_date = self.current_shown_date.replace(month=current_month_val + 1)
            self.current_year = self.current_shown_date.year
            self.current_month = self.current_shown_date.month
        elif self.view_mode == "week":
            self.current_shown_date += timedelta(days=7)
            self.current_year = self.current_shown_date.year # Actualizar para el header
            self.current_month = self.current_shown_date.month # Actualizar para el header y dimming

        # self.update_header() # Se llama dentro de update_calendar
        self.update_calendar()
