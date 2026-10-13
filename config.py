import json
import logging
import os
import sys

APP_NAME = "TickTray"
APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
LOG_FILE = os.path.join(APP_DIR, "TickTray.log")

DEFAULT_CONFIG = {
    "defaultMinutes": 20,
    "defaultSnoozeMinutes": 5,
    "maximumMinutes": 1440,
    "completionSound": True,
    "startWithWindows": False,
    "lastCustomMinutes": 20,
    "language": None,
}
HARD_MAX_MINUTES = 10080

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def setup_logging():
    os.makedirs(APP_DIR, exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE, level=logging.INFO, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(message)s",
    )


def system_language():
    """Arabic when the Windows UI language is Arabic, English otherwise."""
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        return "ar" if (lang_id & 0x3FF) == 0x01 else "en"
    except Exception:
        return "en"


def _as_int(value, default, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return max(low, min(high, int(value)))


def validate(raw):
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(raw, dict):
        cfg.update({k: v for k, v in raw.items() if k in DEFAULT_CONFIG})
    cfg["maximumMinutes"] = _as_int(cfg["maximumMinutes"], DEFAULT_CONFIG["maximumMinutes"], 1, HARD_MAX_MINUTES)
    top = cfg["maximumMinutes"]
    for key in ("defaultMinutes", "defaultSnoozeMinutes", "lastCustomMinutes"):
        cfg[key] = _as_int(cfg[key], min(DEFAULT_CONFIG[key], top), 1, top)
    if cfg["language"] not in ("ar", "en"):
        cfg["language"] = system_language()
    cfg["completionSound"] = bool(cfg["completionSound"])
    cfg["startWithWindows"] = bool(cfg["startWithWindows"])
    return cfg


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return validate(json.load(f))
    except FileNotFoundError:
        return validate(None)
    except Exception:
        logging.exception("config.json unreadable, using defaults")
        return validate(None)


def save_config(cfg):
    os.makedirs(APP_DIR, exist_ok=True)
    tmp = CONFIG_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(validate(cfg), f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_FILE)


def _autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.abspath(sys.argv[0])
    return f'"{pythonw if os.path.exists(pythonw) else sys.executable}" "{script}"'


def set_autostart(enabled):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _autostart_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass


def get_autostart():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except OSError:
        return False
