import psutil
import subprocess
import re
from gi.repository import GLib
import os

from fabric.widgets.label import Label
from fabric.widgets.box import Box
from fabric.widgets.scale import Scale
from fabric.widgets.eventbox import EventBox
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import exec_shell_command_async, exec_shell_command

import modules.icons as icons

class MetricsProvider:
    """
    Class responsible for obtaining centralized CPU, memory, and disk usage metrics.
    It updates periodically so that all widgets querying it display the same values.
    """
    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.disk = 0.0
        # Updates every 1 second
        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        # Get non-blocking usage percentages (interval=0)
        # The first call may return 0, but subsequent calls will provide consistent values.
        self.cpu = psutil.cpu_percent(interval=0)
        self.mem = psutil.virtual_memory().percent
        self.disk = psutil.disk_usage("/").percent
        return True

    def get_metrics(self):
        return (self.cpu, self.mem, self.disk)

# Global instance to share data between both widgets.
shared_provider = MetricsProvider()

class Metrics(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="metrics",
            spacing=8,
            h_align="center",
            v_align="fill",
            visible=True,
            all_visible=True,
        )

        self.cpu_usage = Scale(
            name="cpu-usage",
            value=0.25,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.cpu_label = Label(
            name="cpu-label",
            markup=icons.cpu,
        )

        self.cpu = Box(
            name="cpu-box",
            orientation='v',
            spacing=8,
            children=[
                self.cpu_usage,
                self.cpu_label,
            ]
        )

        self.ram_usage = Scale(
            name="ram-usage",
            value=0.5,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.ram_label = Label(
            name="ram-label",
            markup=icons.memory,
        )

        self.ram = Box(
            name="ram-box",
            orientation='v',
            spacing=8,
            children=[
                self.ram_usage,
                self.ram_label,
            ]
        )

        self.disk_usage = Scale(
            name="disk-usage",
            value=0.75,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.disk_label = Label(
            name="disk-label",
            markup=icons.disk,
        )

        self.disk = Box(
            name="disk-box",
            orientation='v',
            spacing=8,
            children=[
                self.disk_usage,
                self.disk_label,
            ]
        )

        self.scales = [
            self.disk,
            self.ram,
            self.cpu,
        ]

        self.cpu_usage.set_sensitive(False)
        self.ram_usage.set_sensitive(False)
        self.disk_usage.set_sensitive(False)

        for x in self.scales:
            self.add(x)

        # Update the widget every second
        GLib.timeout_add_seconds(1, self.update_status)

    def update_status(self):
        # Retrieve centralized data
        cpu, mem, disk = shared_provider.get_metrics()

        # Normalize to 0.0 - 1.0
        self.cpu_usage.value = cpu / 100.0
        self.ram_usage.value = mem / 100.0
        self.disk_usage.value = disk / 100.0

        return True  # Continue calling this function.

class MetricsSmall(Overlay):
    def __init__(self, **kwargs):
        # Creamos el contenedor principal para los widgets métricos
        main_box = Box(
            name="metrics-small",
            spacing=0,
            orientation="h",
            visible=True,
            all_visible=True,
        )

        # ------------------ CPU ------------------
        self.cpu_icon = Label(name="metrics-icon", markup=icons.cpu)
        self.cpu_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes="cpu",
        )
        self.cpu_overlay = Overlay(
            name="metrics-cpu-overlay",
            child=self.cpu_circle,
            overlays=[self.cpu_icon],
        )
        self.cpu_level = Label(name="metrics-level", style_classes="cpu", label="0%")
        self.cpu_revealer = Revealer(
            name="metrics-cpu-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.cpu_level,
            child_revealed=False,
        )
        self.cpu_box = Box(
            name="metrics-cpu-box",
            orientation="h",
            spacing=0,
            children=[self.cpu_overlay, self.cpu_revealer],
        )

        # ------------------ RAM ------------------
        self.ram_icon = Label(name="metrics-icon", markup=icons.memory)
        self.ram_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes="ram",
        )
        self.ram_overlay = Overlay(
            name="metrics-ram-overlay",
            child=self.ram_circle,
            overlays=[self.ram_icon],
        )
        self.ram_level = Label(name="metrics-level", style_classes="ram", label="0%")
        self.ram_revealer = Revealer(
            name="metrics-ram-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.ram_level,
            child_revealed=False,
        )
        self.ram_box = Box(
            name="metrics-ram-box",
            orientation="h",
            spacing=0,
            children=[self.ram_overlay, self.ram_revealer],
        )

        # ------------------ Disk ------------------
        self.disk_icon = Label(name="metrics-icon", markup=icons.disk)
        self.disk_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes="disk",
        )
        self.disk_overlay = Overlay(
            name="metrics-disk-overlay",
            child=self.disk_circle,
            overlays=[self.disk_icon],
        )
        self.disk_level = Label(name="metrics-level", style_classes="disk", label="0%")
        self.disk_revealer = Revealer(
            name="metrics-disk-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.disk_level,
            child_revealed=False,
        )
        self.disk_box = Box(
            name="metrics-disk-box",
            orientation="h",
            spacing=0,
            children=[self.disk_overlay, self.disk_revealer],
        )

        # Agregamos cada widget métrico al contenedor principal
        main_box.add(self.disk_box)
        main_box.add(Box(name="metrics-sep"))
        main_box.add(self.ram_box)
        main_box.add(Box(name="metrics-sep"))
        main_box.add(self.cpu_box)

        # Se crea un único EventBox que envuelve todo el contenedor, para que
        # los eventos de hover se capturen de forma central y siempre queden por encima
        # de los widgets internos.
        event_box = EventBox(events=["enter-notify-event", "leave-notify-event"])
        event_box.connect("enter-notify-event", self.on_mouse_enter)
        event_box.connect("leave-notify-event", self.on_mouse_leave)

        # Inicializamos MetricsSmall como un Overlay cuyo "child" es el EventBox
        super().__init__(
            name="metrics-small",
            child=main_box,
            visible=True,
            all_visible=True,
            overlays=[event_box]
        )

        # Actualización de métricas cada segundo
        GLib.timeout_add_seconds(1, self.update_metrics)

        # Estado inicial de los revealers y variables para la gestión del hover
        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        """Formato natural del porcentaje sin forzar ancho fijo."""
        return f"{value}%"

    def on_mouse_enter(self, widget, event):
        self.hover_counter += 1
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        # Revelar niveles en hover para todas las métricas
        self.cpu_revealer.set_reveal_child(True)
        self.ram_revealer.set_reveal_child(True)
        self.disk_revealer.set_reveal_child(True)
        return False

    def on_mouse_leave(self, widget, event):
        if self.hover_counter > 0:
            self.hover_counter -= 1
        if self.hover_counter == 0:
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
            self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
        return False

    def hide_revealer(self):
        self.cpu_revealer.set_reveal_child(False)
        self.ram_revealer.set_reveal_child(False)
        self.disk_revealer.set_reveal_child(False)
        self.hide_timer = None
        return False

    def update_metrics(self):
        # Recuperar datos centralizados
        cpu, mem, disk = shared_provider.get_metrics()
        self.cpu_circle.set_value(cpu / 100.0)
        self.ram_circle.set_value(mem / 100.0)
        self.disk_circle.set_value(disk / 100.0)
        # Actualizar etiquetas con el porcentaje formateado
        self.cpu_level.set_label(self._format_percentage(int(cpu)))
        self.ram_level.set_label(self._format_percentage(int(mem)))
        self.disk_level.set_label(self._format_percentage(int(disk)))
        return True


class Battery(Overlay):
    def __init__(self, **kwargs):
        # Creamos el contenedor principal para los widgets métricos
        main_box = Box(
            name="metrics-small",
            spacing=0,
            orientation="h",
            visible=True,
            all_visible=True,
        )

        # ------------------ Battery ------------------
        self.bat_icon = Label(name="metrics-icon", markup=icons.battery)
        self.bat_circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes="bat",
        )
        self.bat_overlay = Overlay(
            name="metrics-bat-overlay",
            child=self.bat_circle,
            overlays=[self.bat_icon],
        )
        self.bat_level = Label(name="metrics-level", style_classes="bat", label="100%")
        self.bat_revealer = Revealer(
            name="metrics-bat-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.bat_level,
            child_revealed=False,
        )
        self.bat_box = Box(
            name="metrics-bat-box",
            orientation="h",
            spacing=0,
            children=[self.bat_overlay, self.bat_revealer],
        )

        # Agregamos cada widget métrico al contenedor principal
        main_box.add(self.bat_box)

        # Se crea un único EventBox que envuelve todo el contenedor, para que
        # los eventos de hover se capturen de forma central y siempre queden por encima
        # de los widgets internos.
        event_box = EventBox(events=["enter-notify-event", "leave-notify-event"])
        event_box.connect("enter-notify-event", self.on_mouse_enter)
        event_box.connect("leave-notify-event", self.on_mouse_leave)

        # Inicializamos MetricsSmall como un Overlay cuyo "child" es el EventBox
        super().__init__(
            name="metrics-small",
            child=main_box,
            visible=True,
            all_visible=True,
            overlays=[event_box]
        )

        # Actualización de la batería cada segundo
        self.batt_fabricator = Fabricator(lambda *args, **kwargs: self.poll_battery(), interval=1000, stream=False, default_value=0)
        self.batt_fabricator.changed.connect(self.update_battery)
        GLib.idle_add(self.update_battery, None, self.poll_battery())

        # Estado inicial de los revealers y variables para la gestión del hover
        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        """Formato natural del porcentaje sin forzar ancho fijo."""
        return f"{value}%"

    def on_mouse_enter(self, widget, event):
        self.hover_counter += 1
        if self.hide_timer is not None:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = None
        # Revelar niveles en hover para todas las métricas
        self.bat_revealer.set_reveal_child(True)
        return False

    def on_mouse_leave(self, widget, event):
        if self.hover_counter > 0:
            self.hover_counter -= 1
        if self.hover_counter == 0:
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
            self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
        return False

    def hide_revealer(self):
        self.bat_revealer.set_reveal_child(False)
        self.hide_timer = None
        return False

    def poll_battery(self):
        try:
            output = subprocess.check_output(["acpi", "-b"]).decode("utf-8").strip()
            if "Battery" not in output:
                return (0, None)
            match_percent = re.search(r'(\d+)%', output)
            match_status = re.search(r'Battery \d+: (\w+)', output)
            if match_percent:
                percent = int(match_percent.group(1))
                status = match_status.group(1) if match_status else None
                
                self._check_battery_notifications(percent, status)
                
                return (percent / 100.0, status)
        except Exception:
            pass
        return (0, None)

    def _check_battery_notifications(self, percentage, status):
        if not hasattr(self, 'notified_low'):
            self.notified_low = set()
            self.notified_high = set()
            self.low_thresholds = [20, 10, 5]
            self.high_thresholds = [80, 100]
            
        if status == "Discharging":
            # Check for low battery with different message severity
            for threshold in self.low_thresholds:
                if percentage <= threshold and threshold not in self.notified_low:
                    if threshold <= 5:
                        title = "Critical Battery Level"
                        message = f"Battery at {percentage}%! Connect charger immediately!"
                    elif threshold <= 10:
                        title = "Very Low Battery"
                        message = f"Battery at {percentage}%. Please connect charger soon."
                    else:  # 20%
                        title = "Low Battery"
                        message = f"Battery at {percentage}%. Consider connecting charger."
                    
                    self._notify(title, message)
                    self.notified_low.add(threshold)
            self.notified_high.clear()  
            
        elif status in ["Charging", "Full"]:
            # Check for high battery
            for threshold in self.high_thresholds:
                if percentage >= threshold and threshold not in self.notified_high:
                    if threshold == 100:
                        title = "Battery Fully Charged"
                        message = "Your battery is now fully charged. You can disconnect the charger."
                    else:  # 80%
                        title = "Battery Charging"
                        message = f"Battery charged to {percentage}%. You may disconnect the charger soon."
                    
                    self._notify(title, message)
                    self.notified_high.add(threshold)
            self.notified_low.clear()

    def _notify(self, summary, body):
        icon_path = os.path.expanduser("~/.config/Ax-Shell/assets/ax.png")
        exec_shell_command_async(f'notify-send -i "{icon_path}" "{summary}" "{body}"')

    def update_battery(self, sender, battery_data):
        value, status = battery_data
        if value == 0:
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.bat_circle.set_value(value)
        percentage = int(value * 100)
        self.bat_level.set_label(self._format_percentage(percentage))
        if percentage <= 15:
            self.bat_icon.set_markup(icons.alert)
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")
            if status == "Discharging":
                self.bat_icon.set_markup(icons.discharging)
            elif percentage == 100:
                self.bat_icon.set_markup(icons.battery)
            elif status == "Charging":
                self.bat_icon.set_markup(icons.charging)
            else:
                self.bat_icon.set_markup(icons.battery)
