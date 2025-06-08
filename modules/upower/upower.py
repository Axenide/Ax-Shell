import dbus

class UPowerManager():

    def __init__(self):
        self.UPOWER_NAME = "org.freedesktop.UPower"
        self.UPOWER_PATH = "/org/freedesktop/UPower"

        self.DBUS_PROPERTIES = "org.freedesktop.DBus.Properties"
        self.bus = dbus.SystemBus()

    def detect_devices(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)

        devices = upower_interface.EnumerateDevices()
        return devices

    def get_display_device(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)

        dispdev = upower_interface.GetDisplayDevice()
        return dispdev

    def get_critical_action(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME)

        critical_action = upower_interface.GetCriticalAction()
        return critical_action

    def get_device_percentage(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        return battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Percentage")

    def get_full_device_information(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        hasHistory = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "HasHistory")
        hasStatistics = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "HasStatistics")
        isPresent = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "IsPresent")
        isRechargable = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "IsRechargeable")
        online = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Online")
        powersupply = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "PowerSupply")
        capacity = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Capacity")
        energy = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Energy")
        energyempty = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyEmpty")
        energyfull = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyFull")
        energyfulldesign = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyFullDesign")
        energyrate = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "EnergyRate")
        luminosity = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Luminosity")
        percentage = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Percentage")
        temperature = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Temperature")
        voltage = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Voltage")
        timetoempty = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "TimeToEmpty")
        timetofull = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "TimeToFull")
        iconname = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "IconName")
        model = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Model")
        nativepath = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "NativePath")
        serial = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Serial")
        vendor = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Vendor")
        state = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "State")
        technology = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Technology")
        battype = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "Type")
        warninglevel = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "WarningLevel")
        updatetime = battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "UpdateTime")


        information_table = {
                'HasHistory': hasHistory,
                'HasStatistics': hasStatistics,
                'IsPresent': isPresent,
                'IsRechargeable': isRechargable,
                'Online': online,
                'PowerSupply': powersupply,
                'Capacity': capacity,
                'Energy': energy,
                'EnergyEmpty': energyempty,
                'EnergyFull': energyfull,
                'EnergyFullDesign': energyfulldesign,
                'EnergyRate': energyrate,
                'Luminosity': luminosity,
                'Percentage': percentage,
                'Temperature': temperature,
                'Voltage': voltage,
                'TimeToEmpty': timetoempty,
                'TimeToFull': timetofull,
                'IconName': iconname,
                'Model': model,
                'NativePath': nativepath,
                'Serial': serial,
                'Vendor': vendor,
                'State': state,
                'Technology': technology,
                'Type': battype,
                'WarningLevel': warninglevel,
                'UpdateTime': updatetime
                }

        return information_table

    def is_lid_present(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        is_lid_present = bool(upower_interface.Get(self.UPOWER_NAME, 'LidIsPresent'))
        return is_lid_present

    def is_lid_closed(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        is_lid_closed = bool(upower_interface.Get(self.UPOWER_NAME, 'LidIsClosed'))
        return is_lid_closed

    def on_battery(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH)
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        on_battery = bool(upower_interface.Get(self.UPOWER_NAME, 'OnBattery'))
        return on_battery

    def has_wakeup_capabilities(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH + "/Wakeups")
        upower_interface = dbus.Interface(upower_proxy, self.DBUS_PROPERTIES)

        has_wakeup_capabilities = bool(upower_interface.Get(self.UPOWER_NAME+ '.Wakeups', 'HasCapability'))
        return has_wakeup_capabilities

    def get_wakeups_data(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH + "/Wakeups")
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME + '.Wakeups')

        data = upower_interface.GetData()
        return data

    def get_wakeups_total(self):
        upower_proxy = self.bus.get_object(self.UPOWER_NAME, self.UPOWER_PATH + "/Wakeups")
        upower_interface = dbus.Interface(upower_proxy, self.UPOWER_NAME + '.Wakeups')

        data = upower_interface.GetTotal()
        return data

    def is_loading(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        state = int(battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "State"))

        if (state == 1):
            return True
        else:
            return False

    def get_state(self, battery):
        battery_proxy = self.bus.get_object(self.UPOWER_NAME, battery)
        battery_proxy_interface = dbus.Interface(battery_proxy, self.DBUS_PROPERTIES)

        state = int(battery_proxy_interface.Get(self.UPOWER_NAME + ".Device", "State"))

        if (state == 0):
            return "Unknown"
        elif (state == 1):
            return "Loading"
        elif (state == 2):
            return "Discharging"
        elif (state == 3):
            return "Empty"
        elif (state == 4):
            return "Fully charged"
        elif (state == 5):
            return "Pending charge"
        elif (state == 6):
            return "Pending discharge"
