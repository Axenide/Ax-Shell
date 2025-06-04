import gi
from loguru import logger
from collections.abc import Callable
from typing import ParamSpec, Concatenate, Any
from fabric.core.service import Service, Signal, Property
from fabric.utils.helpers import (
    bulk_connect,
    get_enum_member_name,
    snake_case_to_kebab_case,
    bridge_signal,
)

from gi.repository import Gio

try:
    gi.require_version("GnomeBluetooth", "3.0")
    from gi.repository import GnomeBluetooth
except Exception:
    raise ImportError("gnome-bluetooth-3 is not installed, please install it first")


P = ParamSpec("P")


class BluetoothDevice(Service):
    @Signal
    def changed(self) -> None: ...

    @Property(GnomeBluetooth.Device, "readable")
    def device(self) -> GnomeBluetooth.Device:
        return self._device

    @Property(bool, "read-write", "is-connected", default_value=False)
    def connected(self) -> bool:
        return self._device.get_property("connected")  # type: ignore

    @connected.setter
    def connected(self, value: bool):
        self.connecting = value
        return

    @Property(bool, "read-write", "is-connecting", default_value=False)
    def connecting(self) -> bool:
        return self._connecting

    @connecting.setter
    def connecting(self, value: bool):
        self._connecting = True

        def request_callback(succeed: bool):
            self._connecting = False
            self.notifier("connected")
            self.notifier("connecting")
            return

        return self.connect_device(value, request_callback)

    @Property(bool, "readable", "is-closed", default_value=False)
    def closed(self) -> bool:
        return self._closed

    @Property(bool, "read-write", "is-paired", default_value=False)
    def paired(self) -> bool:
        return self._device.get_property("paired")  # type: ignore

    @paired.setter
    def paired(self, value: bool):
        return self._device.set_property("paired", value)  # type: ignore

    @Property(bool, "readable", "is-trusted", default_value=False)
    def trusted(self) -> bool:
        return self._device.get_property("trusted")  # type: ignore

    @Property(str, "readable")
    def address(self) -> str:
        return self._device.get_property("address")  # type: ignore

    @Property(str, "readable")
    def name(self) -> str:
        return self._device.get_property("name")  # type: ignore

    @Property(str, "read-write", "is-alias", default_value=None)
    def alias(self) -> str:
        return self._device.get_property("alias")  # type: ignore

    @alias.setter
    def alias(self, value: str):
        return self._device.set_property("alias", value)  # type: ignore

    @Property(str, "readable")
    def icon_name(self) -> str:
        return self._device.get_property("icon")  # type: ignore

    @Property(str, "readable")
    def type(self) -> str:
        return GnomeBluetooth.type_to_string(self._device.get_property("type"))  # type: ignore

    @Property(int, "readable")
    def battery_level(self) -> int:
        return self._device.get_property("battery-level")  # type: ignore

    @Property(float, "readable")
    def battery_percentage(self) -> float:
        return self._device.get_property("battery-percentage")  # type: ignore

    def __init__(
        self, device: GnomeBluetooth.Device, client: "BluetoothClient", **kwargs
    ):
        super().__init__(**kwargs)
        self._device: GnomeBluetooth.Device = device
        self._client: BluetoothClient = client
        self._signal_connectors: list[int] = []

        for pn in (
            "battery-percentage",
            "battery-level",
            "connected",
            "trusted",
            "address",
            "paired",
            "alias",
            "icon",
            "name",
        ):
            self._device.connect(f"notify::{pn}", lambda *_: self.emit("changed"))
            self._signal_connectors.append(
                bridge_signal(
                    self._device,
                    pn,
                    self,
                    "icon-name" if pn not in ("icon",) else pn,
                    notify=True,
                )
            )

        self._closed = self._connecting = False

    def connect_device(
        self,
        connect: bool = True,
        callback: Callable[Concatenate[bool, P], Any] | None = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        return self._client.connect_device(self, connect, callback, *args, **kwargs)

    def close(self):
        for id in self._signal_connectors:
            try:
                self._device.disconnect_handler(id)  # type: ignore
            except Exception:
                pass
        self._closed = True
        self.notifier("closed")
        return

    def notifier(self, name: str, args=None):
        self.notify(name)
        self.emit("changed")
        return


class BluetoothClient(Service):
    @Signal
    def changed(self) -> None: ...

    @Signal
    def closed(self) -> None: ...

    @Signal
    def device_added(self, address: str) -> None: ...

    @Signal
    def device_removed(self, address: str) -> None: ...

    @Property(list[BluetoothDevice], "readable")
    def devices(self) -> list[BluetoothDevice]:
        return list(self._devices.values())

    @Property(list[BluetoothDevice], "readable")
    def connected_devices(self) -> list[BluetoothDevice]:
        return [dev for dev in self._devices.values() if dev.connected]

    @Property(str, "readable")
    def state(self) -> str:
        return snake_case_to_kebab_case(
            get_enum_member_name(
                self._client.get_property("default-adapter-state"),  # type: ignore
                default="unknown",
            )
        )

    @Property(bool, "read-write", default_value=False)
    def scanning(self) -> bool:
        return self._client.get_property("default-adapter-setup-mode")  # type: ignore

    @scanning.setter
    def scanning(self, value: bool):
        return self._client.set_property("default-adapter-setup-mode", value)  # type: ignore

    @Property(bool, "read-write", default_value=False)
    def enabled(self) -> bool:
        return self.state in ("on", "turning-on")

    @enabled.setter
    def enabled(self, value: bool):
        self.powered = value
        return

    @Property(bool, "read-write", "is-powered", default_value=False)
    def powered(self) -> bool:
        return self._client.get_property("default-adapter-powered")  # type: ignore

    @powered.setter
    def powered(self, value: bool):
        return self._client.set_property("default-adapter-powered", value)  # type: ignore

    @Property(str, "readable")
    def address(self) -> str:
        return self._client.get_property("default-adapter-address")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client: GnomeBluetooth.Client = GnomeBluetooth.Client.new()  # type: ignore
        self._devices: dict[str, BluetoothDevice] = {}

        bulk_connect(
            self._client,
            {
                "device-added": self.on_device_added,
                "device-removed": self.on_device_removed,
                "notify::default-adapter-state": lambda *args: self.notifier("state"),
                "notify::default-adapter-powered": lambda *args: self.notifier(
                    "enabled"
                ),
                "notify::default-adapter-setup-mode": lambda *args: self.notifier(
                    "scanning"
                ),
                "notify::default-adapter-address": lambda *args: self.notifier(
                    "address"
                ),
            },
        )
        for device in self.do_get_raw_devices():
            self.on_device_added(self._client, device)  # type: ignore

    def scan(self):
        self.scanning = True
        return

    def toggle_power(self):
        self.powered = not self.powered
        return

    def toggle_scan(self):
        self.scanning = not self.scanning
        return

    def do_get_raw_devices(self) -> list[GnomeBluetooth.Device]:
        all_devs: list[GnomeBluetooth.Device] = self._client.get_devices()  # type: ignore
        return [
            dev
            for dev in all_devs
            if dev.get_paired() or dev.get_trusted()  # type: ignore
        ]

    def on_device_added(self, _, device: GnomeBluetooth.Device):
        addr: str = device.props.address  # type: ignore
        if self._devices.get(addr, None):
            return

        # this may be a mistake, it fixed an issue with me but might not be the right choice
        # we should probably let the user choose what to do with devices with no name

        # RE: it's a mistake, users are responsible about their devices

        # if device.props.name is None:
        #     return
        logger.info(f"[Bluetooth] Adding device: {addr}")

        bluetooth_device: BluetoothDevice = BluetoothDevice(
            device,
            self,
            notify_connected=lambda *_: self.notifier("connected-devices"),
            on_changed=lambda *_: self.emit("changed"),
        )

        self._devices[addr] = bluetooth_device
        self.emit("device-added", addr)
        self.notifier("devices")

    def on_device_removed(self, _, object_path: str):
        addr = object_path.split("/")[-1][4:].replace("_", ":")
        if not (device := self._devices.pop(addr, None)):
            return logger.warning(
                f"[Bluetooth] tried to remove a unknown device with the address {addr}"
            )

        logger.info(f"[Bluetooth] Removing device: {addr}")

        self.emit("device-removed", addr)
        if device.connected:
            self.notifier("connected-devices")
        self.notifier("devices")
        return device.close()

    def get_device(self, address: str) -> BluetoothDevice | None:
        return self._devices.get(address, None)

    def connect_device(
        self,
        device: BluetoothDevice,
        connect: bool = True,
        callback: Callable[Concatenate[bool, P], Any] | None = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        def inner_callback(client: GnomeBluetooth.Client, res: Gio.AsyncResult):
            if not callback:
                return
            try:
                finish = client.connect_service_finish(res)
                logger.info(f"[Bluetooth] Connected to device {device.address}")
                callback(finish, *args, **kwargs)
            except Exception:
                logger.warning(f"[Bluetooth] Failed to connect device {device.address}")
                callback(False, *args, **kwargs)

        return self._client.connect_service(
            device.device.get_object_path(), connect, None, inner_callback
        )

    def notifier(self, name: str, *args):
        self.notify(name)
        self.emit("changed")
        return
