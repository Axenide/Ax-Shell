import json
import logging
import subprocess
import time

import psutil
from fabric.core.fabricator import Fabricator
from fabric.utils.helpers import invoke_repeater
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.eventbox import EventBox
from fabric.widgets.label import Label
from fabric.widgets.overlay import Overlay
from fabric.widgets.revealer import Revealer
from fabric.widgets.scale import Scale
from gi.repository import GLib

import config.data as data
from modules.upower.upower import UPowerManager
import modules.icons as icons
from services.network import NetworkClient

logger = logging.getLogger(__name__)

class MetricsProvider:
    """
    Class responsible for obtaining centralized CPU, memory, disk usage, and battery metrics.
    It updates periodically so that all widgets querying it display the same values.
    """
    def __init__(self):
        self.gpu = []
        self.cpu = 0.0
        self.mem = 0.0
        self.disk = []

        self.upower = UPowerManager()
        self.display_device = self.upower.get_display_device()
        self.bat_percent = 0.0
        self.bat_charging = None
        self.bat_time = 0

        self._gpu_update_running = False

        GLib.timeout_add_seconds(1, self._update)

    def _update(self):
        self.cpu = psutil.cpu_percent(interval=0)
        self.mem = psutil.virtual_memory().percent
        self.disk = [psutil.disk_usage(path).percent for path in data.BAR_METRICS_DISKS]

        if not self._gpu_update_running:
            self._start_gpu_update_async()

        battery = self.upower.get_full_device_information(self.display_device)
        if battery is None:
            self.bat_percent = 0.0
            self.bat_charging = None
            self.bat_time = 0
        else:
            self.bat_percent = battery['Percentage']
            self.bat_charging = battery['State'] == 1
            self.bat_time = battery['TimeToFull'] if self.bat_charging else battery['TimeToEmpty']

        return True

    def _start_gpu_update_async(self):
        """Starts a new GLib thread to run nvtop in the background."""
        self._gpu_update_running = True

        GLib.Thread.new("nvtop-thread", lambda _: self._run_nvtop_in_thread(), None)

    def _run_nvtop_in_thread(self):
        """Runs nvtop via subprocess in a separate GLib thread."""
        output = None
        error_message = None
        try:
            result = subprocess.check_output(["nvtop", "-s"], text=True, timeout=10)
            output = result
        except FileNotFoundError:
            error_message = "nvtop command not found."
            logger.warning(error_message)
        except subprocess.CalledProcessError as e:
            error_message = f"nvtop failed with exit code {e.returncode}: {e.stderr.strip()}"
            logger.error(error_message)
        except subprocess.TimeoutExpired:
            error_message = "nvtop command timed out."
            logger.error(error_message)
        except Exception as e:
            error_message = f"Unexpected error running nvtop: {e}"
            logger.error(error_message)

        GLib.idle_add(self._process_gpu_output, output, error_message)
        self._gpu_update_running = False

    def _process_gpu_output(self, output, error_message):
        """Process nvtop JSON output on the main loop."""
        try:
            if error_message:
                logger.error(f"GPU update failed: {error_message}")
                self.gpu = []
            elif output:
                info = json.loads(output)
                try:
                    self.gpu = [int(v["gpu_util"][:-1]) for v in info]
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Failed parsing nvtop JSON: {e}")
                    self.gpu = []
            else:
                logger.warning("nvtop returned no output.")
                self.gpu = []
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self.gpu = []
        except Exception as e:
            logger.error(f"Error processing nvtop output: {e}")
            self.gpu = []

        return False

    def get_metrics(self):
        return (self.cpu, self.mem, self.disk, self.gpu)

    def get_battery(self):
        return (self.bat_percent, self.bat_charging, self.bat_time)

    def get_gpu_info(self):
        try:
            result = subprocess.check_output(["nvtop", "-s"], text=True, timeout=5)
            return json.loads(result)
        except FileNotFoundError:
            logger.warning("nvtop not found; GPU info unavailable.")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"nvtop init sync failed: {e}")
            return []
        except subprocess.TimeoutExpired:
            logger.error("nvtop init call timed out.")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Init JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during GPU init: {e}")
            return []

shared_provider = MetricsProvider()

class SingularMetric:
    def __init__(self, id, name, icon):
        self.usage = Scale(
            name=f"{id}-usage",
            value=0.25,
            orientation='v',
            inverted=True,
            v_align='fill',
            v_expand=True,
        )

        self.label = Label(
            name=f"{id}-label",
            markup=icon,
        )

        self.box = Box(
            name=f"{id}-box",
            orientation='v',
            spacing=8,
            children=[
                self.usage,
                self.label,
            ]
        )

        self.box.set_tooltip_markup(f"{icon} {name}")

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

        visible = getattr(data, "METRICS_VISIBLE", {'cpu': True, 'ram': True, 'disk': True, 'gpu': True})
        disks = [SingularMetric("disk", f"DISK ({path})" if len(data.BAR_METRICS_DISKS) != 1 else "DISK", icons.disk)
                 for path in data.BAR_METRICS_DISKS] if visible.get('disk', True) else []

        gpu_info = shared_provider.get_gpu_info()
        gpus = [SingularMetric(f"gpu", f"GPU ({v['device_name']})" if len(gpu_info) != 1 else "GPU", icons.gpu)
                for v in gpu_info] if visible.get('gpu', True) else []

        self.cpu = SingularMetric("cpu", "CPU", icons.cpu) if visible.get('cpu', True) else None
        self.ram = SingularMetric("ram", "RAM", icons.memory) if visible.get('ram', True) else None
        self.disk = disks
        self.gpu = gpus

        self.scales = []
        if self.disk: self.scales.extend([v.box for v in self.disk])
        if self.ram: self.scales.append(self.ram.box)
        if self.cpu: self.scales.append(self.cpu.box)
        if self.gpu: self.scales.extend([v.box for v in self.gpu])

        if self.cpu: self.cpu.usage.set_sensitive(False)
        if self.ram: self.ram.usage.set_sensitive(False)
        for disk in self.disk:
            disk.usage.set_sensitive(False)
        for gpu in self.gpu:
            gpu.usage.set_sensitive(False)

        for x in self.scales:
            self.add(x)

        GLib.timeout_add_seconds(1, self.update_status)

    def update_status(self):
        cpu, mem, disks, gpus = shared_provider.get_metrics()

        if self.cpu:
            self.cpu.usage.value = cpu / 100.0
        if self.ram:
            self.ram.usage.value = mem / 100.0
        for i, disk in enumerate(self.disk):

            if i < len(disks):
                disk.usage.value = disks[i] / 100.0
        for i, gpu in enumerate(self.gpu):

            if i < len(gpus):
                gpu.usage.value = gpus[i] / 100.0
        return True

class SingularMetricSmall:
    def __init__(self, id, name, icon):
        self.name_markup = name
        self.icon_markup = icon

        self.icon = Label(name="metrics-icon", markup=icon)
        self.circle = CircularProgressBar(
            name="metrics-circle",
            value=0,
            size=28,
            line_width=2,
            start_angle=150,
            end_angle=390,
            style_classes=id,
            child=self.icon,
        )

        self.level = Label(name="metrics-level", style_classes=id, label="0%")
        self.revealer = Revealer(
            name=f"metrics-{id}-revealer",
            transition_duration=250,
            transition_type="slide-left",
            child=self.level,
            child_revealed=False,
        )

        self.box = Box(
            name=f"metrics-{id}-box",
            orientation="h",
            spacing=0,
            children=[self.circle, self.revealer],
        )

    def markup(self):
        return f"{self.icon_markup} {self.name_markup}" if not data.VERTICAL else f"{self.icon_markup} {self.name_markup}: {self.level.get_label()}"

class MetricsSmall(Button):
    def __init__(self, **kwargs):
        super().__init__(name="metrics-small", **kwargs)

        main_box = Box(

            spacing=0,
            orientation="h" if not data.VERTICAL else "v",
            visible=True,
            all_visible=True,
        )

        visible = getattr(data, "METRICS_SMALL_VISIBLE", {'cpu': True, 'ram': True, 'disk': True, 'gpu': True})
        disks = [SingularMetricSmall("disk", f"DISK ({path})" if len(data.BAR_METRICS_DISKS) != 1 else "DISK", icons.disk)
                 for path in data.BAR_METRICS_DISKS] if visible.get('disk', True) else []

        gpu_info = shared_provider.get_gpu_info()
        gpus = [SingularMetricSmall(f"gpu", f"GPU ({v['device_name']})" if len(gpu_info) != 1 else "GPU", icons.gpu)
                for v in gpu_info] if visible.get('gpu', True) else []

        self.cpu = SingularMetricSmall("cpu", "CPU", icons.cpu) if visible.get('cpu', True) else None
        self.ram = SingularMetricSmall("ram", "RAM", icons.memory) if visible.get('ram', True) else None
        self.disk = disks
        self.gpu = gpus

        for disk in self.disk:
            main_box.add(disk.box)
            main_box.add(Box(name="metrics-sep"))
        if self.ram:
            main_box.add(self.ram.box)
            main_box.add(Box(name="metrics-sep"))
        if self.cpu:
            main_box.add(self.cpu.box)
        for gpu in self.gpu:
            main_box.add(Box(name="metrics-sep"))
            main_box.add(gpu.box)

        self.add(main_box)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        GLib.timeout_add_seconds(1, self.update_metrics)

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

            if self.cpu: self.cpu.revealer.set_reveal_child(True)
            if self.ram: self.ram.revealer.set_reveal_child(True)
            for disk in self.disk:
                disk.revealer.set_reveal_child(True)
            for gpu in self.gpu:
                gpu.revealer.set_reveal_child(True)
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
            if self.cpu: self.cpu.revealer.set_reveal_child(False)
            if self.ram: self.ram.revealer.set_reveal_child(False)
            for disk in self.disk:
                disk.revealer.set_reveal_child(False)
            for gpu in self.gpu:
                gpu.revealer.set_reveal_child(False)
            self.hide_timer = None
            return False

    def update_metrics(self):
        cpu, mem, disks, gpus = shared_provider.get_metrics()

        if self.cpu:
            self.cpu.circle.set_value(cpu / 100.0)
            self.cpu.level.set_label(self._format_percentage(int(cpu)))
        if self.ram:
            self.ram.circle.set_value(mem / 100.0)
            self.ram.level.set_label(self._format_percentage(int(mem)))
        for i, disk in enumerate(self.disk):

            if i < len(disks):
                disk.circle.set_value(disks[i] / 100.0)
                disk.level.set_label(self._format_percentage(int(disks[i])))
        for i, gpu in enumerate(self.gpu):

            if i < len(gpus):
                gpu.circle.set_value(gpus[i] / 100.0)
                gpu.level.set_label(self._format_percentage(int(gpus[i])))

        tooltip_metrics = []
        if self.disk: tooltip_metrics.extend(self.disk)
        if self.ram: tooltip_metrics.append(self.ram)
        if self.cpu: tooltip_metrics.append(self.cpu)
        if self.gpu: tooltip_metrics.extend(self.gpu)
        self.set_tooltip_markup((" - " if not data.VERTICAL else "\n").join([v.markup() for v in tooltip_metrics]))

        return True

class Battery(Button):
    def __init__(self, **kwargs):
        super().__init__(name="metrics-small", **kwargs)

        main_box = Box(

            spacing=0,
            orientation="h",
            visible=True,
            all_visible=True,
        )

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

        main_box.add(self.bat_box)

        self.add(main_box)

        self.connect("enter-notify-event", self.on_mouse_enter)
        self.connect("leave-notify-event", self.on_mouse_leave)

        self.batt_fabricator = Fabricator(
            poll_from=lambda v: shared_provider.get_battery(),
            on_changed=lambda f, v: self.update_battery,
            interval=1000,
            stream=False,
            default_value=0
        )
        self.batt_fabricator.changed.connect(self.update_battery)
        GLib.idle_add(self.update_battery, None, shared_provider.get_battery())

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
        value, charging, time = battery_data
        if value == 0:
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.bat_circle.set_value(value / 100)
        percentage = int(value)
        self.bat_level.set_label(self._format_percentage(percentage))

        if percentage <= 15:
            self.bat_icon.add_style_class("alert")
            self.bat_circle.add_style_class("alert")
        else:
            self.bat_icon.remove_style_class("alert")
            self.bat_circle.remove_style_class("alert")

        if time < 60:
            time_status = f"{int(time)}sec"
        elif time < 60 * 60:
            time_status = f"{int(time / 60)}min"
        else:
            time_status = f"{int(time / 60 / 60)}h"

        if percentage == 100 and charging == False:
            self.bat_icon.set_markup(icons.battery)
            charging_status = f"{icons.bat_full} Fully Charged - {time_status} left"
        elif percentage == 100 and charging == True:
            self.bat_icon.set_markup(icons.battery)
            charging_status = f"{icons.bat_full} Fully Charged"
        elif charging == True:
            self.bat_icon.set_markup(icons.charging)
            charging_status = f"{icons.bat_charging} Charging - {time_status} left"
        elif percentage <= 15 and charging == False:
            self.bat_icon.set_markup(icons.alert)
            charging_status = f"{icons.bat_low} Low Battery - {time_status} left"
        elif charging == False:
            self.bat_icon.set_markup(icons.discharging)
            charging_status = f"{icons.bat_discharging} Discharging - {time_status} left"
        else:
            self.bat_icon.set_markup(icons.battery)
            charging_status = "Battery"

        self.set_tooltip_markup(f"{charging_status}" if not data.VERTICAL else f"{charging_status}: {percentage}%")

class NetworkApplet(Button):
    def __init__(self, **kwargs):
        super().__init__(name="button-bar", **kwargs)
        self.download_label = Label(name="download-label", markup="Download: 0 B/s")
        self.network_client = NetworkClient()
        self.upload_label = Label(name="upload-label", markup="Upload: 0 B/s")
        self.wifi_label = Label(name="network-icon-label", markup="WiFi: Unknown")

        self.is_mouse_over = False
        self.downloading = False
        self.uploading = False

        self.download_icon = Label(name="download-icon-label", markup=icons.download, v_align="center", h_align="center", h_expand=True, v_expand=True)
        self.upload_icon = Label(name="upload-icon-label", markup=icons.upload, v_align="center", h_align="center", h_expand=True, v_expand=True)

        self.download_box = Box(
            children=[self.download_icon, self.download_label],
        )

        self.upload_box = Box(
            children=[self.upload_label, self.upload_icon],
        )

        self.download_revealer = Revealer(child=self.download_box, transition_type = "slide-right" if not data.VERTICAL else "slide-down", child_revealed=False)
        self.upload_revealer = Revealer(child=self.upload_box, transition_type="slide-left" if not data.VERTICAL else "slide-up",child_revealed=False)

        self.children = Box(
            orientation="h" if not data.VERTICAL else "v",
            children=[self.upload_revealer, self.wifi_label, self.download_revealer],
        )

        if data.VERTICAL:
            self.download_label.set_visible(False)
            self.upload_label.set_visible(False)
            self.upload_icon.set_margin_top(4)
            self.download_icon.set_margin_bottom(4)

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

        if not self.is_mouse_over:
            if self.downloading:
                self.download_urgent()
            elif self.uploading:
                self.upload_urgent()
            else:
                self.remove_urgent()

        show_download = self.downloading or (self.is_mouse_over and not data.VERTICAL)
        show_upload = self.uploading or (self.is_mouse_over and not data.VERTICAL)
        self.download_revealer.set_reveal_child(show_download)
        self.upload_revealer.set_reveal_child(show_upload)

        primary_device = None
        if self.network_client:
            primary_device = self.network_client.primary_device

        tooltip_base = ""
        tooltip_vertical = ""

        if primary_device == "wired" and self.network_client.ethernet_device:
            ethernet_state = self.network_client.ethernet_device.internet

            if ethernet_state == "activated":
                self.wifi_label.set_markup(icons.world)
            elif ethernet_state == "activating":
                self.wifi_label.set_markup(icons.world)
            else:
                self.wifi_label.set_markup(icons.world_off)

            tooltip_base = "Ethernet Connection"
            tooltip_vertical = f"SSID: Ethernet\nUpload: {upload_str}\nDownload: {download_str}"

        elif self.network_client and self.network_client.wifi_device:
            if self.network_client.wifi_device.ssid != "Disconnected":
                strength = self.network_client.wifi_device.strength

                if strength >= 75:
                    self.wifi_label.set_markup(icons.wifi_3)
                elif strength >= 50:
                    self.wifi_label.set_markup(icons.wifi_2)
                elif strength >= 25:
                    self.wifi_label.set_markup(icons.wifi_1)
                else:
                    self.wifi_label.set_markup(icons.wifi_0)

                tooltip_base = self.network_client.wifi_device.ssid
                tooltip_vertical = f"SSID: {self.network_client.wifi_device.ssid}\nUpload: {upload_str}\nDownload: {download_str}"
            else:
                self.wifi_label.set_markup(icons.world_off)
                tooltip_base = "Disconnected"
                tooltip_vertical = f"SSID: Disconnected\nUpload: {upload_str}\nDownload: {download_str}"
        else:
            self.wifi_label.set_markup(icons.world_off)
            tooltip_base = "Disconnected"
            tooltip_vertical = f"SSID: Disconnected\nUpload: {upload_str}\nDownload: {download_str}"

        if data.VERTICAL:
            self.set_tooltip_text(tooltip_vertical)
        else:
            self.set_tooltip_text(tooltip_base)

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

            self.download_revealer.set_reveal_child(True)
            self.upload_revealer.set_reveal_child(True)
        return

    def on_mouse_leave(self, *_):
        self.is_mouse_over = False
        if not data.VERTICAL:

            self.download_revealer.set_reveal_child(self.downloading)
            self.upload_revealer.set_reveal_child(self.uploading)

            if self.downloading:
                self.download_urgent()
            elif self.uploading:
                self.upload_urgent()
            else:
                self.remove_urgent()
        return

    def upload_urgent(self):
        self.add_style_class("upload")
        self.wifi_label.add_style_class("urgent")
        self.upload_label.add_style_class("urgent")
        self.upload_icon.add_style_class("urgent")
        self.download_icon.add_style_class("urgent")
        self.download_label.add_style_class("urgent")
        self.upload_revealer.set_reveal_child(True)
        self.download_revealer.set_reveal_child(self.downloading)
        return

    def download_urgent(self):
        self.add_style_class("download")
        self.wifi_label.add_style_class("urgent")
        self.download_label.add_style_class("urgent")
        self.download_icon.add_style_class("urgent")
        self.upload_icon.add_style_class("urgent")
        self.upload_label.add_style_class("urgent")
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
