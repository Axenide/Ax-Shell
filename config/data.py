import json
import os

import gi

gi.require_version("Gtk", "3.0")
from fabric.utils.helpers import get_relative_path
from gi.repository import Gdk, GLib

APP_NAME = "ax-shell"
APP_NAME_CAP = "Ax-Shell"


PANEL_POSITION_KEY = "panel_position"
PANEL_POSITION_DEFAULT = "Center"
NOTIF_POS_KEY = "notif_pos"
NOTIF_POS_DEFAULT = "Top"

# AI API Keys
AI_OPENAI_KEY = "ai_openai_key"
AI_GEMINI_KEY = "ai_gemini_key"
AI_CLAUDE_KEY = "ai_claude_key"
AI_GROK_KEY = "ai_grok_key"
AI_DEEPSEEK_KEY = "ai_deepseek_key"

# AI Model Selections
AI_OPENAI_MODEL = "ai_openai_model"
AI_GEMINI_MODEL = "ai_gemini_model"
AI_CLAUDE_MODEL = "ai_claude_model"
AI_GROK_MODEL = "ai_grok_model"
AI_DEEPSEEK_MODEL = "ai_deepseek_model"

CACHE_DIR = str(GLib.get_user_cache_dir()) + f"/{APP_NAME}"

USERNAME = os.getlogin()
HOSTNAME = os.uname().nodename
HOME_DIR = os.path.expanduser("~")

CONFIG_DIR = os.path.expanduser(f"~/.config/{APP_NAME}")

screen = Gdk.Screen.get_default()
CURRENT_WIDTH = screen.get_width()
CURRENT_HEIGHT = screen.get_height()


WALLPAPERS_DIR_DEFAULT = get_relative_path("../assets/wallpapers_example")
CONFIG_FILE = get_relative_path('../config/config.json')
MATUGEN_STATE_FILE = os.path.join(CONFIG_DIR, "matugen")


BAR_WORKSPACE_USE_CHINESE_NUMERALS = False
BAR_THEME = "Pills"

DOCK_THEME = "Pills"

PANEL_THEME = "Notch"

def load_config():
    """Load the configuration from config.json"""
    config_path = os.path.expanduser(f"~/.config/{APP_NAME_CAP}/config/config.json")
    config = {}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    return config

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    WALLPAPERS_DIR = config.get('wallpapers_dir', WALLPAPERS_DIR_DEFAULT)
    BAR_POSITION = config.get('bar_position', "Top")
    VERTICAL = BAR_POSITION in ["Left", "Right"]
    CENTERED_BAR = config.get('centered_bar', False)
    TERMINAL_COMMAND = config.get('terminal_command', "kitty -e")
    DOCK_ENABLED = config.get('dock_enabled', True)
    DOCK_ALWAYS_OCCLUDED = config.get('dock_always_occluded', False)
    DOCK_ICON_SIZE = config.get('dock_icon_size', 28)
    BAR_WORKSPACE_SHOW_NUMBER = config.get('bar_workspace_show_number', False)
    BAR_WORKSPACE_USE_CHINESE_NUMERALS = config.get('bar_workspace_use_chinese_numerals', False)
    BAR_THEME = config.get('bar_theme', "Pills")
    DOCK_THEME = config.get('dock_theme', "Pills")
    PANEL_THEME = config.get('panel_theme', "Pills")

    PANEL_POSITION = config.get(PANEL_POSITION_KEY, PANEL_POSITION_DEFAULT)
    NOTIF_POS = config.get(NOTIF_POS_KEY, NOTIF_POS_DEFAULT)


    BAR_COMPONENTS_VISIBILITY = {
        'button_apps': config.get('bar_button_apps_visible', True),
        'systray': config.get('bar_systray_visible', True),
        'control': config.get('bar_control_visible', True),
        'network': config.get('bar_network_visible', True),
        'button_tools': config.get('bar_button_tools_visible', True),
        'button_overview': config.get('bar_button_overview_visible', True),
        'ws_container': config.get('bar_ws_container_visible', True),
        'weather': config.get('bar_weather_visible', True),
        'battery': config.get('bar_battery_visible', True),
        'metrics': config.get('bar_metrics_visible', True),
        'language': config.get('bar_language_visible', True),
        'date_time': config.get('bar_date_time_visible', True),
        'button_power': config.get('bar_button_power_visible', True),
    }
    
    BAR_METRICS_DISKS = config.get('bar_metrics_disks', ["/"])
    METRICS_VISIBLE = config.get('metrics_visible', {'cpu': True, 'ram': True, 'disk': True, 'gpu': True})
    METRICS_SMALL_VISIBLE = config.get('metrics_small_visible', {'cpu': True, 'ram': True, 'disk': True, 'gpu': True})
    
    # AI API Keys
    AI_OPENAI_API_KEY = config.get(AI_OPENAI_KEY, "")
    AI_GEMINI_API_KEY = config.get(AI_GEMINI_KEY, "")
    AI_CLAUDE_API_KEY = config.get(AI_CLAUDE_KEY, "")
    AI_GROK_API_KEY = config.get(AI_GROK_KEY, "")
    AI_DEEPSEEK_API_KEY = config.get(AI_DEEPSEEK_KEY, "")
    
    # AI Model Selections (with backward compatibility for old format)
    AI_OPENAI_MODEL = config.get(AI_OPENAI_MODEL, config.get("gpt-3.5-turbo", "gpt-3.5-turbo"))
    AI_GEMINI_MODEL = config.get(AI_GEMINI_MODEL, config.get("gemini-1.5-pro", "gemini-1.5-pro"))
    AI_CLAUDE_MODEL = config.get(AI_CLAUDE_MODEL, config.get("claude-3-sonnet-20240229", "claude-3-sonnet-20240229"))
    AI_GROK_MODEL = config.get(AI_GROK_MODEL, config.get("grok-beta", "grok-beta"))
    AI_DEEPSEEK_MODEL = config.get(AI_DEEPSEEK_MODEL, config.get("deepseek-chat", "deepseek-chat"))
else:
    WALLPAPERS_DIR = WALLPAPERS_DIR_DEFAULT
    BAR_POSITION = "Top"
    VERTICAL = False
    CENTERED_BAR = False
    DOCK_ENABLED = True
    DOCK_ALWAYS_OCCLUDED = False
    TERMINAL_COMMAND = "kitty -e"
    DOCK_ICON_SIZE = 28
    BAR_WORKSPACE_SHOW_NUMBER = False
    BAR_WORKSPACE_USE_CHINESE_NUMERALS = False
    BAR_THEME = "Pills"
    DOCK_THEME = "Pills"
    PANEL_THEME = "Notch"

    PANEL_POSITION = PANEL_POSITION_DEFAULT
    NOTIF_POS = NOTIF_POS_DEFAULT
    
    # AI API Keys (empty by default)
    AI_OPENAI_API_KEY = ""
    AI_GEMINI_API_KEY = ""
    AI_CLAUDE_API_KEY = ""
    AI_GROK_API_KEY = ""
    AI_DEEPSEEK_API_KEY = ""
    
    # AI Model Selections (default models)
    AI_OPENAI_MODEL = "gpt-3.5-turbo"
    AI_GEMINI_MODEL = "gemini-1.5-pro"
    AI_CLAUDE_MODEL = "claude-3-sonnet-20240229"
    AI_GROK_MODEL = "grok-beta"
    AI_DEEPSEEK_MODEL = "deepseek-chat"


    BAR_COMPONENTS_VISIBILITY = {
        'button_apps': True,
        'systray': True,
        'control': True,
        'network': True,
        'button_tools': True,
        'button_overview': True,
        'ws_container': True,
        'weather': True,
        'battery': True,
        'metrics': True,
        'language': True,
        'date_time': True,
        'button_power': True,
    }
    
    BAR_METRICS_DISKS = ["/"]
    METRICS_VISIBLE = {'cpu': True, 'ram': True, 'disk': True, 'gpu': True}
    METRICS_SMALL_VISIBLE = {'cpu': True, 'ram': True, 'disk': True, 'gpu': True}
