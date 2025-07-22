# Parameters
font_family: str = "tabler-icons"
font_weight: str = "normal"

span: str = f"<span font-family='{font_family}' font-weight='{font_weight}'>"

# Panels
apps: str = "&#xf1fd;"
dashboard: str = "&#xea87;"
chat: str = "&#xf59f;"
windows: str = "&#xefe6;"

# Bar
colorpicker: str = "&#xebe6;"
media: str = "&#xf00d;"

# Toolbox

toolbox: str = "&#xebca;"
ssfull: str = "&#xec3c;"
ssregion: str = "&#xf201;"
sswindow: str = "&#xeaea;"
screenshots: str = "&#xeb0a;"
screenrecord: str = "&#xed22;"
recordings: str = "&#xeafa;"
ocr: str = "&#xfcc3;"
gamemode: str = "&#xf026;"
gamemode_off: str = "&#xf111;"
close: str = "&#xeb55;"

# Circles
temp: str = "&#xeb38;"
disk: str = "&#xea88;"
battery: str = "&#xea38;"
memory: str = "&#xfa97;"
cpu: str = "&#xef8e;"
gpu: str = "&#xf233;"

# AIchat
reload: str = "&#xf3ae;"
detach: str = "&#xea99;"

# Wallpapers
add: str = "&#xeb0b;"
sort: str = "&#xeb5a;"
circle: str = "&#xf671;"

# Chevrons
chevron_up: str = "&#xea62;"
chevron_down: str = "&#xea5f;"
chevron_left: str = "&#xea60;"
chevron_right: str = "&#xea61;"

# Power
lock: str = "&#xeae2;"
suspend: str = "&#xece7;"
logout: str = "&#xeba8;"
reboot: str = "&#xeb13;"
shutdown: str = "&#xeb0d;"

# Power Manager
power_saving: str = "&#xed4f;"
power_balanced: str = "&#xfa77;"
power_performance: str = "&#xec45;"
charging: str = "&#xefef;"
discharging: str = "&#xefe9;"
alert: str = "&#xea06;"
bat_charging: str = "&#xeeca;"
bat_discharging: str = "&#xf0a1;"
bat_low: str = "&#xff1d;"
bat_full: str = "&#xea38;"


# Applets
wifi_0: str = "&#xeba3;"
wifi_1: str = "&#xeba4;"
wifi_2: str = "&#xeba5;"
wifi_3: str = "&#xeb52;"
world: str = "&#xeb54;"
world_off: str = "&#xf1ca;"
bluetooth: str = "&#xea37;"
night: str = "&#xeaf8;"
coffee: str = "&#xef0e;"
notifications: str = "&#xea35;"

wifi_off: str = "&#xecfa;"
bluetooth_off: str = "&#xeceb;"
night_off: str = "&#xf162;"
notifications_off: str = "&#xece9;"

notifications_clear: str = "&#xf814;"

download: str = "&#xea96;"
upload: str = "&#xeb47;"

# Bluetooth
bluetooth_connected: str = "&#xecea;"
bluetooth_disconnected: str = "&#xf081;"

# Player
pause: str = "&#xf690;"
play: str = "&#xf691;"
stop: str = "&#xf695;"
skip_back: str = "&#xf693;"
skip_forward: str = "&#xf694;"
prev: str = "&#xf697;"
next: str = "&#xf696;"
shuffle: str = "&#xf000;"
repeat: str = "&#xeb72;"
music: str = "&#xeafc;"
rewind_backward_5: str = "&#xfabf;"
rewind_forward_5: str = "&#xfac7;"

# Volume
vol_off: str = "&#xf1c3;"
vol_mute: str = "&#xeb50;"
vol_medium: str = "&#xeb4f;"
vol_high: str = "&#xeb51;"

mic: str = "&#xeaf0;"
mic_mute: str = "&#xed16;"

speaker: str = "&#x10045;"
headphones: str = "&#xfa3c;"
mic_filled: str = "&#xfe0f;"

# Overview
circle_plus: str = "&#xea69;"

# Pins
paperclip: str = "&#xeb02;"

# Clipboard Manager
clipboard: str = "&#xea6f;"
clip_text: str = "&#xf089;"

# Confirm
accept: str = "&#xea5e;"
cancel: str = "&#xeb55;"
trash: str = "&#xeb41;"

# Config
config: str = "&#xeb20;"

# Icons
firefox: str = "&#xecfd;"
chromium: str = "&#xec18;"
spotify: str = "&#xfe86;"
disc: str = "&#x1003e;"
disc_off: str = "&#xf118;"

# Brightness
brightness_low: str = "&#xeb7d;"
brightness_medium: str = "&#xeb7e;"
brightness_high: str = "&#xeb30;"

brightness: str = "&#xee1a;"

# Dashboard
widgets: str = "&#xf02c;"
pins: str = "&#xec9c;"
kanban: str = "&#xec3f;"
wallpapers: str = "&#xeb61;"
sparkles: str = "&#xf6d7;"

# Misc
dot: str = "&#xf698;"
palette: str = "&#xeb01;"
cloud_off: str = "&#xed3e;"
loader: str = "&#xeca3;"
radar: str = "&#xf017;"
emoji: str = "&#xeaf7;"
keyboard: str = "&#xebd6;"
terminal: str = "&#xebef;"
timer_off: str = "&#xf146;"
timer_on: str = "&#xf756;"
spy: str = "&#xf227;"

# Dice
dice_1: str = "&#xf08b;"
dice_2: str = "&#xf08c;"
dice_3: str = "&#xf08d;"
dice_4: str = "&#xf08e;"
dice_5: str = "&#xf08f;"
dice_6: str = "&#xf090;"

exceptions: list[str] = ["font_family", "font_weight", "span"]


def apply_span() -> None:
    global_dict = globals()
    for key in global_dict:
        if key not in exceptions and not key.startswith("__"):
            global_dict[key] = f"{span}{global_dict[key]}</span>"


apply_span()
