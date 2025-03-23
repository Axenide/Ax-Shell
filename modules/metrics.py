import re
import subprocess

import psutil
from gi.repository import GLib

from fabric.core.fabricator import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import exec_shell_command_async, invoke_repeater
from fabric.widgets.scale import Scale

import modules.icons as icons
import config.data as data
from services.network import NetworkClient
import time

class MetricsProvider:
    """
    Class responsible for obtaining centralized CPU, memory, disk usage, and battery metrics.
    It updates periodically so that all widgets querying it display the same values.
    """
    def __init__(self):
        self.cpu = 0.0
        self.mem = 0.0
        self.disk = 0.0

        self.bat_percent = 0.0
        self.bat_charging = None

        # Updates every 1 second
        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        # Get non-blocking usage percentages (interval=0)
        # The first call may return 0, but subsequent calls will provide consistent values.
        self.cpu = psutil.cpu_percent(interval=0)
        self.mem = psutil.virtual_memory().percent
        self.disk = psutil.disk_usage("/").percent

        battery = psutil.sensors_battery()
        if battery is None:
            self.bat_percent = 0.0
            self.bat_charging = None
        else:
            self.bat_percent = battery.percent
            self.bat_charging = battery.power_plugged

        return True

    def get_metrics(self):
        return (self.cpu, self.mem, self.disk)

    def get_battery(self):
        return (self.bat_percent, self.bat_charging)

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

class MetricsSmall(Button):
    def __init__(self, **kwargs):
        super().__init__(name="metrics-small", **kwargs)
        
        # Create the main box for metrics widgets
        main_box = Box(
            name="metrics-small",
            spacing=0,
            orientation="h" if not data.VERTICAL else "v",
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
            child=self.cpu_icon,
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
            children=[self.cpu_circle, self.cpu_revealer],
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
            child=self.ram_icon,
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
            children=[self.ram_circle, self.ram_revealer],
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
            child=self.disk_icon,
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
            children=[self.disk_circle, self.disk_revealer],
        )

        # Agregamos cada widget métrico al contenedor principal
        main_box.add(self.disk_box)
        main_box.add(Box(name="metrics-sep"))
        main_box.add(self.ram_box)
        main_box.add(Box(name="metrics-sep"))
        main_box.add(self.cpu_box)

        # Set the main box as the button's child
        self.add(main_box)
        
        # Connect events directly to the button
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        GLib.timeout_add_seconds(1, self.update_metrics)
        # Actualización de métricas cada segundo

        # Estado inicial de los revealers y variables para la gestión del hover
        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        """Formato natural del porcentaje sin forzar ancho fijo."""
        return f"{value}%"

    def on_mouse_enter(self, widget, event):
        if not data.VERTICAL:
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
        if not data.VERTICAL:
            if self.hover_counter > 0:
                self.hover_counter -= 1
            if self.hover_counter == 0:
                if self.hide_timer is not None:
                    GLib.source_remove(self.hide_timer)
                self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
            return False

    def hide_revealer(self):
        if not data.VERTICAL:
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
        self.set_tooltip_markup(f"{icons.disk} DISK - {icons.memory} RAM - {icons.cpu} CPU" if not data.VERTICAL else f"{icons.disk} DISK: {self.disk_level.get_label()}\n{icons.memory} RAM: {self.ram_level.get_label()}\n{icons.cpu} CPU: {self.cpu_level.get_label()}")
        return True


class Battery(Button):
    def __init__(self, **kwargs):
        super().__init__(name="metrics-small", **kwargs)
        
        # Create the main box for metrics widgets
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
            child=self.bat_icon,
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
            children=[self.bat_circle, self.bat_revealer],
        )

        # Add the battery widget to the main container
        main_box.add(self.bat_box)

        # Set the main box as the button's child
        self.add(main_box)
        
        # Connect events directly to the button
        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        # Actualización de la batería cada segundo
        self.batt_fabricator = Fabricator(
            poll_from=lambda v: shared_provider.get_battery(),
            on_changed=lambda f, v: self.update_battery,
            interval=1000,
            stream=False,
            default_value=0
        )
        self.batt_fabricator.changed.connect(self.update_battery)
        GLib.idle_add(self.update_battery, None, shared_provider.get_battery())

        # Estado inicial de los revealers y variables para la gestión del hover
        self.hide_timer = None
        self.hover_counter = 0

    def _format_percentage(self, value: int) -> str:
        """Formato natural del porcentaje sin forzar ancho fijo."""
        return f"{value}%"

    def on_mouse_enter(self, widget, event):
        if not data.VERTICAL:
            self.hover_counter += 1
            if self.hide_timer is not None:
                GLib.source_remove(self.hide_timer)
                self.hide_timer = None
            # Revelar niveles en hover para todas las métricas
            self.bat_revealer.set_reveal_child(True)
            return False

    def on_mouse_leave(self, widget, event):
        if not data.VERTICAL:
            if self.hover_counter > 0:
                self.hover_counter -= 1
            if self.hover_counter == 0:
                if self.hide_timer is not None:
                    GLib.source_remove(self.hide_timer)
                self.hide_timer = GLib.timeout_add(500, self.hide_revealer)
            return False

    def hide_revealer(self):
        if not data.VERTICAL:
            self.bat_revealer.set_reveal_child(False)
            self.hide_timer = None
            return False

    def update_battery(self, sender, battery_data):
        value, charging = battery_data
        if value == 0:
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.bat_circle.set_value(value / 100)
        percentage = int(value)
        self.bat_level.set_label(self._format_percentage(percentage))
        
        # Apply alert styling if battery is low, regardless of charging status
        if percentage <= 15:
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")
        
        # Choose the icon based on charging state first, then battery level
        if percentage == 100:
            self.bat_icon.set_markup(icons.battery)
            charging_status = f"{icons.bat_full} Fully Charged"
        elif charging == True:
            self.bat_icon.set_markup(icons.charging)
            charging_status = f"{icons.bat_charging} Charging"
        elif percentage <= 15 and charging == False:
            self.bat_icon.set_markup(icons.alert)
            charging_status = f"{icons.bat_low} Low Battery"
        elif charging == False:
            self.bat_icon.set_markup(icons.discharging)
            charging_status = f"{icons.bat_discharging} Discharging"
        else:
            self.bat_icon.set_markup(icons.battery)
            charging_status = "Battery"
            
        # Set a descriptive tooltip with battery percentage
        self.set_tooltip_markup(f"{charging_status}" if not data.VERTICAL else f"{charging_status}: {percentage}%")

                
class NetworkApplet(Button):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar", **kwargs)
        self.download_label = Label(name="download-label", markup="Download: 0 B/s")
        self.network_client = NetworkClient()
        self.upload_label = Label(name="upload-label", markup="Upload: 0 B/s")
        self.wifi_label = Label(name="network-icon-label", markup="WiFi: Unknown")

        self.is_mouse_over = False

        self.download_icon = Label(name="download-icon-label", markup=icons.download)
        self.upload_icon = Label(name="upload-icon-label", markup=icons.upload)

        self.download_box = Box(
            children=[self.download_icon, self.download_label],
        )

        self.upload_box = Box(
            children=[self.upload_label, self.upload_icon],
        )

        self.download_revealer = Revealer(child=self.download_box, transition_type = "slide-right", child_revealed=False)
        self.upload_revealer = Revealer(child=self.upload_box, transition_type="slide-left" ,child_revealed=False)
        

        self.children = Box(
            children=[self.upload_revealer, self.wifi_label, self.download_revealer],
        )
        self.last_counters = psutil.net_io_counters()
        self.last_time = time.time()
        invoke_repeater(1000, self.update_network)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

    def update_network(self):
        current_time = time.time()
        elapsed = current_time - self.last_time
        current_counters = psutil.net_io_counters()
        download_speed = (current_counters.bytes_recv - self.last_counters.bytes_recv) / elapsed
        upload_speed = (current_counters.bytes_sent - self.last_counters.bytes_sent) / elapsed
        download_str = self.format_speed(download_speed)
        upload_str = self.format_speed(upload_speed)
        self.download_label.set_markup(download_str)
        self.upload_label.set_markup(upload_str)

        self.downloading = (download_speed >= 10e6)
        self.uploading = (upload_speed >= 2e6)

        # Apply urgent styles regardless of orientation
        if self.downloading and not self.is_mouse_over:
            self.download_urgent()
        if self.uploading and not self.is_mouse_over:
            self.upload_urgent()
        
        if not self.downloading and not self.uploading:
            self.remove_urgent()

        if not data.VERTICAL:
            # Horizontal mode - original behavior for revealers
            self.download_revealer.set_reveal_child(self.downloading or self.is_mouse_over)
            self.upload_revealer.set_reveal_child(self.uploading or self.is_mouse_over)
        else:
            # Vertical mode - don't use revealers, change icon instead
            self.download_revealer.set_reveal_child(False)
            self.upload_revealer.set_reveal_child(False)
        
        if self.network_client and self.network_client.wifi_device:
            if self.network_client.wifi_device.ssid != "Disconnected":
                strength = self.network_client.wifi_device.strength
                
                if data.VERTICAL:
                    # Change the WiFi icon based on network activity
                    if self.downloading:
                        self.wifi_label.set_markup(icons.download)
                    elif self.uploading:
                        self.wifi_label.set_markup(icons.upload)
                    else:
                        # Normal WiFi icon based on signal strength
                        if strength >= 75:
                            self.wifi_label.set_markup(icons.wifi_3)
                        elif strength >= 50:
                            self.wifi_label.set_markup(icons.wifi_2)
                        elif strength >= 25:
                            self.wifi_label.set_markup(icons.wifi_1)
                        else:
                            self.wifi_label.set_markup(icons.wifi_0)
                    
                    # Vertical mode format for tooltip
                    self.set_tooltip_text(f"SSID: {self.network_client.wifi_device.ssid}\nDownload: {download_str}\nUpload: {upload_str}")
                else:
                    # Original horizontal mode
                    if strength >= 75:
                        self.wifi_label.set_markup(icons.wifi_3)
                    elif strength >= 50:
                        self.wifi_label.set_markup(icons.wifi_2)
                    elif strength >= 25:
                        self.wifi_label.set_markup(icons.wifi_1)
                    else:
                        self.wifi_label.set_markup(icons.wifi_0)

                    self.set_tooltip_text(self.network_client.wifi_device.ssid)
            else:
                self.wifi_label.set_markup(icons.world_off)
                self.set_tooltip_text("Disconnected")
        else:
            self.wifi_label.set_markup(icons.world_off)
            self.set_tooltip_text("Disconnected")

        self.last_counters = current_counters
        self.last_time = current_time
        return True

    def format_speed(self, speed):
        if speed < 1024:
            return f"{speed:.0f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed / 1024:.1f} KB/s"
        else:
            return f"{speed / (1024 * 1024):.1f} MB/s"
        
    def on_mouse_enter(self, *_):
        self.is_mouse_over = True
        if not data.VERTICAL:
            self.remove_urgent()
            self.download_revealer.set_reveal_child(True)
            self.upload_revealer.set_reveal_child(True)
        return
    
    def on_mouse_leave(self, *_):
        self.is_mouse_over = False
        if not data.VERTICAL:
            self.remove_urgent()
            self.download_revealer.set_reveal_child(False)
            self.upload_revealer.set_reveal_child(False)
        return

    def upload_urgent(self):
        self.add_style_class("upload")
        self.wifi_label.add_style_class("urgent")
        self.upload_label.add_style_class("urgent")
        self.upload_icon.add_style_class("urgent")
        self.download_icon.add_style_class("urgent")
        self.upload_revealer.set_reveal_child(True)
        self.download_revealer.set_reveal_child(self.downloading)
        return
    
    def download_urgent(self):
        self.add_style_class("download")
        self.wifi_label.add_style_class("urgent")
        self.download_label.add_style_class("urgent")
        self.download_icon.add_style_class("urgent")
        self.upload_icon.add_style_class("urgent")
        self.download_revealer.set_reveal_child(True)
        self.upload_revealer.set_reveal_child(self.uploading)
        return
    
    def remove_urgent(self):
        self.remove_style_class("download")
        self.remove_style_class("upload")
        self.wifi_label.remove_style_class("urgent")
        self.download_label.remove_style_class("urgent")
        self.upload_label.remove_style_class("urgent")
        self.download_icon.remove_style_class("urgent")
        self.upload_icon.remove_style_class("urgent")
        return
