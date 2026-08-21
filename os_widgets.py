#!/usr/bin/env python3
"""
OS Widgets — Your desktop. Your widgets.

A single-file Windows desktop widget application.

Install:
    py -m pip install PySide6 psutil tzdata qtawesome
Run without a console window:
    pyw os_widgets.py
Optional single-EXE build:
    py -m pip install pyinstaller
    pyinstaller --onefile --windowed --name "OS Widgets" os_widgets.py

PySide6 powers the interface, psutil supplies Wi-Fi/RAM telemetry, tzdata
provides daylight-saving-aware Windows time zones, and qtawesome bundles
Font Awesome icons for fully offline use. Native Windows fallbacks are included.
"""

from __future__ import annotations

import base64
import calendar as pycalendar
import copy
import ctypes
import datetime as dt
import email.utils
import hashlib
import html
import ipaddress
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import weakref
import webbrowser
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None  # type: ignore

try:
    import psutil  # type: ignore
except ImportError:
    psutil = None

try:
    import qtawesome as qta  # type: ignore
except ImportError:
    qta = None

try:
    from PySide6.QtCore import (
        QByteArray,
        QEasingCurve,
        QEvent,
        QDate,
        QDateTime,
        QObject,
        QPoint,
        QPointF,
        QPropertyAnimation,
        QRect,
        QRectF,
        QSize,
        Qt,
        QTimer,
        QUrl,
        Signal,
    )
    from PySide6.QtGui import (
        QAction,
        QColor,
        QCursor,
        QDesktopServices,
        QFont,
        QFontDatabase,
        QIcon,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPalette,
        QPen,
        QPixmap,
    )
    from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDialog,
        QDateEdit,
        QDateTimeEdit,
        QFileDialog,
        QFrame,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QInputDialog,
        QListWidget,
        QListWidgetItem,
        QMenu,
        QMessageBox,
        QProgressBar,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QSpinBox,
        QStackedWidget,
        QStyle,
        QSystemTrayIcon,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    message = (
        "OS Widgets needs PySide6.\n\n"
        "Install the UI libraries with:\n  py -m pip install PySide6 psutil tzdata qtawesome"
    )
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.MessageBoxW(None, message, "OS Widgets", 0x10)
        except Exception:
            pass
    print(message)
    raise SystemExit(1)

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:
    QAudioOutput = None  # type: ignore
    QMediaPlayer = None  # type: ignore


APP_NAME = "OS Widgets"
TAGLINE = "Your desktop. Your widgets."
APP_VERSION = "1.2.0"
SETTINGS_SCHEMA_VERSION = 2
IS_WINDOWS = sys.platform == "win32"


def app_data_dir() -> Path:
    if IS_WINDOWS:
        root = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    path = root / "OS Widgets"
    path.mkdir(parents=True, exist_ok=True)
    return path


SETTINGS_PATH = app_data_dir() / "settings.json"
INSTALL_RESET_MARKER = app_data_dir() / ".reset-on-next-launch"
NEWS_CACHE_PATH = app_data_dir() / "news_cache.json"
NEWS_IMAGE_CACHE_DIR = app_data_dir() / "news_images"
NEWS_IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def prune_news_image_cache(max_files: int = 80, max_bytes: int = 48 * 1024 * 1024) -> None:
    """Bound the thumbnail cache so the background app never grows forever."""
    try:
        files = sorted(
            (path for path in NEWS_IMAGE_CACHE_DIR.iterdir() if path.is_file()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        total = 0
        for index, path in enumerate(files):
            size = path.stat().st_size
            total += size
            if index >= max_files or total > max_bytes:
                path.unlink(missing_ok=True)
    except OSError:
        pass


TIMEZONES = [
    "Local",
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
    "America/Vancouver",
    "America/Mexico_City",
    "America/Sao_Paulo",
    "America/Argentina/Buenos_Aires",
    "Europe/London",
    "Europe/Dublin",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Madrid",
    "Europe/Rome",
    "Europe/Amsterdam",
    "Europe/Brussels",
    "Europe/Zurich",
    "Europe/Vienna",
    "Europe/Stockholm",
    "Europe/Warsaw",
    "Europe/Athens",
    "Europe/Helsinki",
    "Europe/Istanbul",
    "Europe/Moscow",
    "Africa/Cairo",
    "Africa/Johannesburg",
    "Africa/Nairobi",
    "Asia/Dubai",
    "Asia/Kolkata",
    "Asia/Karachi",
    "Asia/Dhaka",
    "Asia/Bangkok",
    "Asia/Singapore",
    "Asia/Hong_Kong",
    "Asia/Shanghai",
    "Asia/Taipei",
    "Asia/Seoul",
    "Asia/Tokyo",
    "Asia/Jakarta",
    "Asia/Manila",
    "Australia/Perth",
    "Australia/Adelaide",
    "Australia/Sydney",
    "Pacific/Auckland",
    "Pacific/Honolulu",
]

# Used only if Windows has neither system time-zone data nor the tzdata package.
# Installing tzdata enables full daylight-saving behavior.
FALLBACK_OFFSETS = {
    "UTC": 0,
    "America/New_York": -5,
    "America/Chicago": -6,
    "America/Denver": -7,
    "America/Los_Angeles": -8,
    "America/Toronto": -5,
    "America/Vancouver": -8,
    "America/Mexico_City": -6,
    "America/Sao_Paulo": -3,
    "America/Argentina/Buenos_Aires": -3,
    "Europe/London": 0,
    "Europe/Dublin": 0,
    "Europe/Paris": 1,
    "Europe/Berlin": 1,
    "Europe/Madrid": 1,
    "Europe/Rome": 1,
    "Europe/Amsterdam": 1,
    "Europe/Brussels": 1,
    "Europe/Zurich": 1,
    "Europe/Vienna": 1,
    "Europe/Stockholm": 1,
    "Europe/Warsaw": 1,
    "Europe/Athens": 2,
    "Europe/Helsinki": 2,
    "Europe/Istanbul": 3,
    "Europe/Moscow": 3,
    "Africa/Cairo": 2,
    "Africa/Johannesburg": 2,
    "Africa/Nairobi": 3,
    "Asia/Dubai": 4,
    "Asia/Kolkata": 5.5,
    "Asia/Karachi": 5,
    "Asia/Dhaka": 6,
    "Asia/Bangkok": 7,
    "Asia/Singapore": 8,
    "Asia/Hong_Kong": 8,
    "Asia/Shanghai": 8,
    "Asia/Taipei": 8,
    "Asia/Seoul": 9,
    "Asia/Tokyo": 9,
    "Asia/Jakarta": 7,
    "Asia/Manila": 8,
    "Australia/Perth": 8,
    "Australia/Adelaide": 9.5,
    "Australia/Sydney": 10,
    "Pacific/Auckland": 12,
    "Pacific/Honolulu": -10,
}


def clock_config(city: str, zone: str, variant: int) -> dict[str, Any]:
    return {
        "enabled": True,
        "city": city,
        "timezone": zone,
        "format_24h": False,
        "display_mode": "digital",
        "show_seconds": True,
        "show_date": True,
        "variant": variant,
        "geometry": None,
        "size_preset": "standard",
        "opacity": 100,
        "always_top": False,
        "locked": False,
    }


def default_settings() -> dict[str, Any]:
    return {
        "version": SETTINGS_SCHEMA_VERSION,
        "appearance": {
            "theme": "system",
            "transparency": True,
            "animations": True,
            "app_accent": "#3178C6",
            "custom_widget_colors": False,
            "widget_accent": "#58A6FF",
            "widget_surface": "#171C26",
            "widget_corners": "rounded",
        },
        "general": {"startup": False, "performance_mode": "balanced"},
        "widgets": {
            "clock1": clock_config("Local Time", "Local", 0),
            "clock2": clock_config("New York", "America/New_York", 1),
            "clock3": clock_config("London", "Europe/London", 2),
            "clock4": clock_config("Tokyo", "Asia/Tokyo", 3),
            "cpu": {
                "enabled": True,
                "geometry": None,
                "size_preset": "standard",
                "opacity": 100,
                "always_top": False,
                "locked": False,
                "show_temperature": True,
                "show_ram": True,
                "interval_ms": 2000,
                "metric_index": 0,
                "alerts_enabled": False,
                "alert_cpu": 90,
                "alert_gpu": 95,
                "alert_ram": 90,
                "alert_temp": 90,
                "alert_cooldown_minutes": 10,
                "alert_sound_enabled": False,
                "alert_sound_path": "",
            },
            "music": {
                "enabled": False,
                "geometry": None,
                "size_preset": "standard",
                "opacity": 100,
                "always_top": False,
                "locked": False,
                "playlist": [],
                "current_index": 0,
                "volume": 70,
                "cover_image": "",
            },
            "goal": {
                "enabled": False,
                "geometry": None,
                "size_preset": "standard",
                "opacity": 100,
                "always_top": False,
                "locked": False,
                "title": "My Goal",
                "target": (dt.datetime.now().astimezone() + dt.timedelta(days=30)).replace(microsecond=0).isoformat(),
                "image_path": "",
                "completed_text": "Goal reached",
                "show_seconds": True,
            },
            "calendar": {
                "enabled": False,
                "geometry": None,
                "size_preset": "standard",
                "opacity": 100,
                "always_top": False,
                "locked": False,
                "todos": [],
                "show_completed": True,
            },
            "quotes": {
                "enabled": False,
                "geometry": None,
                "size_preset": "ultra_mini",
                "opacity": 100,
                "always_top": False,
                "locked": False,
                "interval_minutes": 5,
                "quote_index": 0,
                "custom_quotes": [],
                "use_builtin": True,
            },
            "news": {
                "enabled": True,
                "geometry": None,
                "size_preset": "standard",
                "opacity": 100,
                "always_top": False,
                "locked": False,
                "source": "Google News",
                "category": "Top stories",
                "custom_url": "",
                "refresh_minutes": 15,
                "slide_seconds": 8,
                "fetch_article_images": True,
                "reader_fallback": True,
            }
        },
    }


def deep_merge(default: dict[str, Any], value: Any) -> dict[str, Any]:
    result = copy.deepcopy(default)
    if not isinstance(value, dict):
        return result
    for key, item in value.items():
        if key in result and isinstance(result[key], dict) and isinstance(item, dict):
            result[key] = deep_merge(result[key], item)
        else:
            result[key] = item
    return result


class SettingsStore:
    def __init__(self) -> None:
        self.reset_on_load = False
        self.data = self.load()
        if self.reset_on_load:
            self.save()

    def load(self) -> dict[str, Any]:
        # The installer places this one-shot marker so an installed build never
        # inherits geometry, playlists or preferences from a source checkout.
        if INSTALL_RESET_MARKER.exists():
            self.reset_on_load = True
            try:
                INSTALL_RESET_MARKER.unlink()
            except OSError:
                pass
            return default_settings()
        try:
            raw = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if int(raw.get("version", 0)) < SETTINGS_SCHEMA_VERSION:
                self.reset_on_load = True
                return default_settings()
            return deep_merge(default_settings(), raw)
        except Exception:
            return default_settings()

    def save(self) -> None:
        temp = SETTINGS_PATH.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(temp, SETTINGS_PATH)
        except OSError:
            pass

    def reset(self) -> None:
        self.data = default_settings()
        self.save()


STORE = SettingsStore()


def is_windows_dark() -> bool:
    if not IS_WINDOWS:
        return QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(value) == 0
    except Exception:
        return True


def resolved_dark() -> bool:
    theme = STORE.data["appearance"]["theme"]
    return theme == "dark" or (theme == "system" and is_windows_dark())


def performance_mode() -> str:
    return str(STORE.data.get("general", {}).get("performance_mode", "balanced"))


def palette_colors() -> dict[str, QColor]:
    dark = resolved_dark()
    transparent = STORE.data["appearance"]["transparency"]
    if dark:
        return {
            "surface": QColor(20, 23, 30, 224 if transparent else 255),
            "surface2": QColor(31, 35, 45, 238 if transparent else 255),
            "text": QColor(245, 247, 252),
            "muted": QColor(164, 172, 190),
            "border": QColor(255, 255, 255, 28),
            "control": QColor(255, 255, 255, 18),
            "hover": QColor(255, 255, 255, 31),
        }
    return {
        "surface": QColor(249, 250, 253, 228 if transparent else 255),
        "surface2": QColor(255, 255, 255, 242 if transparent else 255),
        "text": QColor(26, 31, 42),
        "muted": QColor(91, 101, 120),
        "border": QColor(17, 24, 39, 28),
        "control": QColor(20, 30, 50, 12),
        "hover": QColor(20, 30, 50, 24),
    }


def safe_color(value: Any, fallback: str) -> QColor:
    color = QColor(str(value or ""))
    return color if color.isValid() else QColor(fallback)


def app_accent_color() -> QColor:
    return safe_color(STORE.data["appearance"].get("app_accent"), "#3178C6")


def widget_palette_colors() -> dict[str, QColor]:
    if not STORE.data["appearance"].get("custom_widget_colors", False):
        return palette_colors()
    transparent = STORE.data["appearance"].get("transparency", True)
    surface = safe_color(STORE.data["appearance"].get("widget_surface"), "#171C26")
    surface.setAlpha(224 if transparent else 255)
    dark_surface = surface.lightness() < 145
    text = QColor(247, 249, 253) if dark_surface else QColor(24, 30, 42)
    muted = QColor(173, 182, 200) if dark_surface else QColor(82, 94, 115)
    contrast = QColor(255,255,255) if dark_surface else QColor(15,25,40)
    border = QColor(contrast); border.setAlpha(32)
    control = QColor(contrast); control.setAlpha(18)
    hover = QColor(contrast); hover.setAlpha(32)
    surface2 = surface.lighter(112) if dark_surface else surface.darker(103)
    return {"surface":surface,"surface2":surface2,"text":text,"muted":muted,"border":border,"control":control,"hover":hover}


def widget_corner_radius() -> int:
    return {"square": 2, "soft": 8, "rounded": 15}.get(str(STORE.data["appearance"].get("widget_corners", "rounded")), 15)


def accent_for(key: str) -> QColor:
    if STORE.data["appearance"].get("custom_widget_colors", False):
        return safe_color(STORE.data["appearance"].get("widget_accent"), "#58A6FF")
    return {
        "clock1": QColor("#58A6FF"),
        "clock2": QColor("#9B8AFB"),
        "clock3": QColor("#36C6A5"),
        "clock4": QColor("#FF718B"),
        "cpu": QColor("#4BC0FF"),
        "music": QColor("#A889FF"),
        "goal": QColor("#42D3A5"),
        "calendar": QColor("#FFB547"),
        "quotes": QColor("#7BD88F"),
        "news": QColor("#FFB547"),
    }.get(key, QColor("#58A6FF"))


def timezone_now(zone_name: str) -> dt.datetime:
    if zone_name == "Local":
        return dt.datetime.now().astimezone()
    if ZoneInfo is not None:
        try:
            return dt.datetime.now(ZoneInfo(zone_name))
        except Exception:
            pass
    offset = FALLBACK_OFFSETS.get(zone_name, 0)
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=offset)))


_DESKTOP_HOST_CACHE = 0


def windows_desktop_host() -> int:
    """Return the top-level shell window that owns the desktop icons.

    Windows 10/11 may host SHELLDLL_DefView under either Progman or a WorkerW
    window. Locating the actual host lets desktop-level widgets sit immediately
    above the wallpaper/icons layer, instead of HWND_BOTTOM (which can hide a
    window underneath the wallpaper).
    """
    global _DESKTOP_HOST_CACHE
    if not IS_WINDOWS:
        return 0
    try:
        user32 = ctypes.windll.user32
        if _DESKTOP_HOST_CACHE and user32.IsWindow(ctypes.c_void_p(_DESKTOP_HOST_CACHE)):
            return _DESKTOP_HOST_CACHE
        user32.FindWindowW.restype = ctypes.c_void_p
        user32.FindWindowExW.restype = ctypes.c_void_p
        user32.GetWindow.restype = ctypes.c_void_p
        user32.SetWindowPos.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        ]
        user32.SetWindowPos.restype = ctypes.c_bool
        host = ctypes.c_void_p(0)
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @callback_type
        def enum_window(hwnd, _lparam):
            nonlocal host
            if user32.FindWindowExW(hwnd, 0, "SHELLDLL_DefView", None):
                host = ctypes.c_void_p(hwnd)
                return False
            return True

        user32.EnumWindows(enum_window, 0)
        if host.value:
            _DESKTOP_HOST_CACHE = int(host.value)
            return _DESKTOP_HOST_CACHE
        progman = user32.FindWindowW("Progman", None)
        _DESKTOP_HOST_CACHE = int(progman or 0)
        return _DESKTOP_HOST_CACHE
    except Exception:
        return 0


def set_windows_startup(enabled: bool) -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, "Windows startup registration is available on Windows only."
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        )
        if getattr(sys, "frozen", False):
            command = subprocess.list2cmdline([sys.executable, "--startup"])
        else:
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            executable = str(pythonw if pythonw.exists() else Path(sys.executable))
            command = subprocess.list2cmdline([executable, str(Path(__file__).resolve()), "--startup"])
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def app_stylesheet() -> str:
    dark = resolved_dark()
    fg = "#F4F6FB" if dark else "#202532"
    muted = "#A6AEC0" if dark else "#687086"
    panel = "#1A1E27" if dark else "#F7F8FB"
    raised = "#252A36" if dark else "#FFFFFF"
    border = "rgba(255,255,255,0.09)" if dark else "rgba(20,30,50,0.12)"
    hover = "#303747" if dark else "#EDF1F7"
    accent_color = app_accent_color(); accent = accent_color.name(); accent_hover = accent_color.lighter(115).name()
    return f"""
        QWidget {{ color: {fg}; font-family: "Segoe UI Variable", "Segoe UI", sans-serif; font-size: 13px; }}
        QDialog {{ background: {panel}; }}
        QDialog#settingsDialog {{ background: {panel}; }}
        QLabel#muted {{ color: {muted}; }}
        QLabel#pageTitle {{ color: {fg}; font-size: 21px; font-weight: 700; }}
        QLabel#pageDescription {{ color: {muted}; font-size: 12px; }}
        QLabel#versionBadge {{ color: {accent}; background: {'rgba(49,120,198,0.13)' if dark else 'rgba(49,120,198,0.09)'}; border: 1px solid {'rgba(88,166,255,0.28)' if dark else 'rgba(49,120,198,0.20)'}; border-radius: 10px; padding: 5px 10px; font-size: 10px; font-weight: 700; }}
        QFrame#settingsNavPanel {{ background: {'#161A23' if dark else '#F0F3F8'}; border: 1px solid {border}; border-radius: 14px; }}
        QFrame#pageIconTile {{ background: {'rgba(49,120,198,0.17)' if dark else 'rgba(49,120,198,0.10)'}; border: 1px solid {'rgba(88,166,255,0.25)' if dark else 'rgba(49,120,198,0.18)'}; border-radius: 11px; }}
        QLabel#navSection {{ color: {muted}; font-size: 9px; font-weight: 700; letter-spacing: 1px; }}
        QFrame#settingsCard, QGroupBox {{ background: {raised}; border: 1px solid {border}; border-radius: 12px; }}
        QGroupBox {{ margin-top: 14px; padding: 15px 12px 12px 12px; font-weight: 600; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
        QLineEdit, QComboBox, QSpinBox, QDateEdit, QDateTimeEdit, QPlainTextEdit {{ background: {raised}; color:{fg}; border: 1px solid {border}; border-radius: 7px; padding: 7px 9px; min-height: 18px; }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {accent}; }}
        QComboBox::drop-down {{ border: none; width: 24px; }}
        QComboBox QAbstractItemView {{ background: {raised}; color: {fg}; selection-background-color: {accent}; border: 1px solid {border}; outline: none; }}
        QCheckBox {{ spacing: 9px; }}
        QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid {border}; background: {raised}; }}
        QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; image: none; }}
        QPushButton {{ background: {raised}; color: {fg}; border: 1px solid {border}; border-radius: 8px; padding: 8px 14px; }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton#iconButton {{ background: transparent; border: none; border-radius: 7px; padding: 4px; }}
        QPushButton#iconButton:hover {{ background: {hover}; }}
        QPushButton#primary {{ background: {accent}; color: white; border: none; font-weight: 600; }}
        QPushButton#primary:hover {{ background: {accent_hover}; }}
        QListWidget {{ background: transparent; border: none; outline: none; padding: 4px; }}
        QListWidget::item {{ min-height: 24px; padding: 9px 11px; border-radius: 9px; margin: 2px 0; }}
        QListWidget::item:hover {{ background: {hover}; }}
        QListWidget::item:selected {{ background: {accent}; color: white; }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{ width: 12px; background: {'rgba(255,255,255,0.025)' if dark else 'rgba(20,30,50,0.035)'}; border: none; border-radius: 6px; margin: 3px 2px; }}
        QScrollBar::handle:vertical {{ background: {'#535D70' if dark else '#B4BECD'}; border: 2px solid transparent; border-radius: 5px; min-height: 34px; }}
        QScrollBar::handle:vertical:hover {{ background: {accent}; }}
        QScrollBar:horizontal {{ height: 12px; background: {'rgba(255,255,255,0.025)' if dark else 'rgba(20,30,50,0.035)'}; border: none; border-radius: 6px; margin: 2px 3px; }}
        QScrollBar::handle:horizontal {{ background: {'#535D70' if dark else '#B4BECD'}; border: 2px solid transparent; border-radius: 5px; min-width: 34px; }}
        QScrollBar::handle:horizontal:hover {{ background: {accent}; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: transparent; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QMenu {{ background: {raised}; color: {fg}; border: 1px solid {border}; border-radius: 8px; padding: 6px; }}
        QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: 5px; }}
        QMenu::item:selected {{ background: {hover}; }}
        QMenu::separator {{ height: 1px; background: {border}; margin: 5px 8px; }}
    """


def make_app_icon(size: int = 64) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, size, size)
    icon_accent = app_accent_color()
    grad.setColorAt(0, icon_accent.lighter(132))
    grad.setColorAt(1, icon_accent.darker(118))
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(3, 3, size - 6, size - 6, size * .25, size * .25)
    p.setBrush(QColor(255, 255, 255, 242))
    gap, cell = size * .10, size * .25
    start = size * .20
    for row in range(2):
        for col in range(2):
            p.drawRoundedRect(
                int(start + col * (cell + gap)),
                int(start + row * (cell + gap)),
                int(cell), int(cell), int(size * .055), int(size * .055)
            )
    p.end()
    return QIcon(pix)


def fallback_vector_icon(name: str, color: Optional[str] = None) -> QIcon:
    """Draw an embedded vector fallback so icons never depend on a font file."""
    pix = QPixmap(32, 32); pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    ink = QColor(color or palette_colors()["muted"].name())
    pen = QPen(ink, 2.3); pen.setCapStyle(Qt.PenCapStyle.RoundCap); pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
    key = name.split(".")[-1]
    if key in ("chevron-left", "chevron-right"):
        pts = (QPoint(19, 8), QPoint(12, 16), QPoint(19, 24)) if key.endswith("left") else (QPoint(13, 8), QPoint(20, 16), QPoint(13, 24))
        p.drawPolyline(pts)
    elif key in ("xmark", "check"):
        if key == "xmark": p.drawLine(9, 9, 23, 23); p.drawLine(23, 9, 9, 23)
        else: p.drawPolyline((QPoint(7, 17), QPoint(13, 23), QPoint(25, 9)))
    elif key in ("circle-check", "circle-xmark", "circle-info"):
        p.drawEllipse(5, 5, 22, 22)
        if key == "circle-check": p.drawPolyline((QPoint(10, 16), QPoint(14, 20), QPoint(22, 11)))
        elif key == "circle-xmark": p.drawLine(11, 11, 21, 21); p.drawLine(21, 11, 11, 21)
        else: p.drawPoint(16, 11); p.drawLine(16, 15, 16, 22)
    elif key == "triangle-exclamation":
        p.drawPolygon((QPoint(16, 4), QPoint(28, 26), QPoint(4, 26)))
        p.drawLine(16, 11, 16, 19); p.drawPoint(16, 23)
    elif key in ("clock",):
        p.drawEllipse(5, 5, 22, 22); p.drawLine(16, 16, 16, 9); p.drawLine(16, 16, 22, 19)
    elif key in ("calendar-days",):
        p.drawRoundedRect(5,7,22,20,3,3);p.drawLine(5,12,27,12);p.drawLine(11,4,11,9);p.drawLine(21,4,21,9)
        for x in (10,16,22):p.drawPoint(x,17);p.drawPoint(x,22)
    elif key in ("quote-left",):
        p.setBrush(ink);p.drawRoundedRect(6,10,8,9,3,3);p.drawRoundedRect(18,10,8,9,3,3);p.drawLine(10,18,7,25);p.drawLine(22,18,19,25)
    elif key in ("table-cells-large",):
        for x in (6, 17):
            for y in (6, 17): p.drawRoundedRect(x, y, 9, 9, 2, 2)
    elif key in ("newspaper",):
        p.drawRoundedRect(5, 6, 22, 20, 3, 3); p.drawRect(9, 10, 6, 6)
        for y in (11, 15, 20): p.drawLine(18 if y < 18 else 9, y, 24, y)
    elif key in ("gauge-high",):
        p.drawArc(5, 7, 22, 22, 0, 180 * 16); p.drawLine(16, 19, 23, 11); p.drawEllipse(14, 17, 4, 4)
    elif key in ("palette",):
        p.drawEllipse(5, 6, 23, 20)
        for point in ((12, 11), (18, 10), (23, 14)): p.drawEllipse(point[0]-1, point[1]-1, 2, 2)
        p.drawEllipse(10, 18, 5, 4)
    elif key in ("gear",):
        p.drawEllipse(10, 10, 12, 12); p.drawEllipse(14, 14, 4, 4)
        for i in range(8):
            a=math.pi*i/4; p.drawLine(int(16+7*math.cos(a)),int(16+7*math.sin(a)),int(16+12*math.cos(a)),int(16+12*math.sin(a)))
    elif key in ("stethoscope",):
        p.drawArc(7, 5, 13, 18, 180*16, 180*16); p.drawLine(7, 14, 7, 20); p.drawLine(20, 14, 20, 20)
        p.drawLine(13, 23, 13, 25); p.drawLine(13, 25, 22, 25); p.drawEllipse(21, 21, 6, 6)
    elif key in ("bell",):
        path=QPainterPath(); path.moveTo(8,22); path.quadTo(11,19,11,12); path.quadTo(11,6,16,6); path.quadTo(21,6,21,12); path.quadTo(21,19,24,22); path.closeSubpath(); p.drawPath(path); p.drawArc(13,22,6,5,180*16,180*16)
    elif key in ("play",):
        p.setBrush(ink); p.drawPolygon((QPoint(11,7),QPoint(25,16),QPoint(11,25)))
    elif key in ("pause",):
        p.setBrush(ink);p.drawRoundedRect(9,7,5,18,2,2);p.drawRoundedRect(18,7,5,18,2,2)
    elif key in ("plus",):
        p.drawLine(16,7,16,25);p.drawLine(7,16,25,16)
    elif key in ("backward-step","forward-step"):
        backward=key.startswith("backward");p.setBrush(ink)
        if backward:p.drawLine(8,7,8,25);p.drawPolygon((QPoint(23,7),QPoint(10,16),QPoint(23,25)))
        else:p.drawLine(24,7,24,25);p.drawPolygon((QPoint(9,7),QPoint(22,16),QPoint(9,25)))
    elif key in ("music",):
        p.drawLine(13,8,13,22);p.drawLine(13,8,24,6);p.drawLine(24,6,24,19);p.drawEllipse(7,20,7,5);p.drawEllipse(18,17,7,5)
    elif key in ("flag-checkered",):
        p.drawLine(8,5,8,27);p.drawPolygon((QPoint(9,6),QPoint(25,8),QPoint(21,17),QPoint(9,15)))
    elif key in ("copy",):
        p.drawRoundedRect(10, 6, 16, 18, 3, 3); p.drawRoundedRect(6, 10, 16, 17, 3, 3)
    elif key in ("folder-open",):
        path=QPainterPath(); path.moveTo(5,10); path.lineTo(12,10); path.lineTo(15,13); path.lineTo(27,13); path.lineTo(24,25); path.lineTo(6,25); path.closeSubpath(); p.drawPath(path); p.drawLine(6,10,6,23)
    elif key in ("volume-high",):
        p.drawPolygon((QPoint(6,13),QPoint(11,13),QPoint(17,8),QPoint(17,24),QPoint(11,19),QPoint(6,19)))
        p.drawArc(17,10,8,12,-60*16,120*16); p.drawArc(17,6,13,20,-60*16,120*16)
    elif key in ("trash-can",):
        p.drawRoundedRect(9, 10, 14, 17, 2, 2); p.drawLine(7,8,25,8); p.drawLine(13,5,19,5); p.drawLine(14,14,14,23); p.drawLine(18,14,18,23)
    elif key in ("arrows-rotate",):
        p.drawArc(6,6,20,20,35*16,135*16); p.drawPolyline((QPoint(22,5),QPoint(27,7),QPoint(24,12)))
        p.drawArc(6,6,20,20,215*16,135*16); p.drawPolyline((QPoint(10,27),QPoint(5,24),QPoint(8,20)))
    elif key in ("ellipsis",):
        p.setBrush(ink)
        for x in (9,16,23): p.drawEllipse(x-1,15,3,3)
    elif key in ("microchip", "memory"):
        p.drawRoundedRect(8,8,16,16,3,3)
        for v in (11,16,21): p.drawLine(v,5,v,8); p.drawLine(v,24,v,27); p.drawLine(5,v,8,v); p.drawLine(24,v,27,v)
        if key=="microchip": p.drawRect(12,12,8,8)
        else:
            for y in (12,16,20): p.drawLine(11,y,21,y)
    elif key in ("display",):
        p.drawRoundedRect(5,6,22,16,3,3); p.drawLine(16,22,16,26); p.drawLine(11,26,21,26)
    elif key in ("hard-drive",):
        p.drawRoundedRect(5,8,22,17,4,4); p.drawEllipse(20,14,3,3); p.drawEllipse(20,20,2,2); p.drawLine(9,20,16,20)
    elif key in ("battery-half",):
        p.drawRoundedRect(5,9,21,14,3,3); p.drawLine(27,13,27,19); p.setBrush(ink); p.drawRoundedRect(8,12,8,8,2,2)
    elif key in ("wifi",):
        p.drawArc(5,9,22,18,35*16,110*16); p.drawArc(9,13,14,12,35*16,110*16); p.drawEllipse(15,23,2,2)
    elif key in ("image",):
        p.drawRoundedRect(5,6,22,20,4,4); p.drawEllipse(10,10,4,4); p.drawPolyline((QPoint(7,23),QPoint(13,17),QPoint(17,21),QPoint(21,15),QPoint(26,21)))
    elif key in ("thumbtack",):
        p.drawPolygon((QPoint(11,6),QPoint(22,10),QPoint(19,15),QPoint(22,19),QPoint(10,16),QPoint(14,13))); p.drawLine(15,17,12,26)
    elif key in ("layer-group",):
        p.drawPolygon((QPoint(16,5),QPoint(27,11),QPoint(16,17),QPoint(5,11))); p.drawPolyline((QPoint(6,17),QPoint(16,23),QPoint(26,17))); p.drawPolyline((QPoint(6,21),QPoint(16,27),QPoint(26,21)))
    elif key in ("up-right-and-down-left-from-center",):
        p.drawLine(7,13,7,7); p.drawLine(7,7,13,7); p.drawLine(7,7,14,14); p.drawLine(25,19,25,25); p.drawLine(25,25,19,25); p.drawLine(25,25,18,18)
    else:
        p.drawRoundedRect(6,6,20,20,6,6); p.drawEllipse(14,14,4,4)
    p.end(); return QIcon(pix)


def awesome_icon(name: str, color: Optional[str] = None) -> QIcon:
    """Use Font Awesome when available, with an embedded vector fallback."""
    target_color = color or palette_colors()["muted"].name()
    if qta is not None:
        try:
            icon = qta.icon(name, color=target_color)
            probe = icon.pixmap(20, 20)
            if not probe.isNull():
                image = probe.toImage()
                if any(image.pixelColor(x, y).alpha() > 8 for y in range(image.height()) for x in range(image.width())):
                    return icon
        except Exception:
            pass
    return fallback_vector_icon(name, target_color)


def set_icon_button(button: QPushButton, name: str, fallback: str, size: int = 14) -> None:
    icon = awesome_icon(name)
    button.setObjectName("iconButton")
    button.setIconSize(QSize(size, size))
    if icon.isNull():
        button.setIcon(QIcon())
        button.setText(fallback)
    else:
        button.setText("")
        button.setIcon(icon)


class BaseWidget(QWidget):
    """Frameless desktop-level widget with persistence and shared controls."""

    MIN_SIZE = QSize(230, 125)
    DEFAULT_SIZE = QSize(300, 160)
    supports_refresh = False

    def __init__(self, manager: "WidgetManager", key: str) -> None:
        super().__init__(None)
        self.manager = manager
        self.key = key
        self.config = STORE.data["widgets"][key]
        self.accent = accent_for(key)
        self.last_size_preset = str(self.config.get("size_preset", "standard"))
        self.hovered = False
        self.dragging = False
        self.resizing = False
        self.drag_offset = QPoint()
        self.start_geometry = QRect()
        self.pending_save = QTimer(self)
        self.pending_save.setSingleShot(True)
        self.pending_save.setInterval(350)
        self.pending_save.timeout.connect(self.save_geometry)

        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.config.get("always_top", False):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setMinimumSize(self.MIN_SIZE)
        self.resize(self.DEFAULT_SIZE)

        self.content = QWidget(self)
        self.content.setObjectName("widgetContent")
        self.content.setStyleSheet("background: transparent;")

        self.refresh_button = QPushButton("", self)
        set_icon_button(self.refresh_button, "fa6s.arrows-rotate", "↻")
        self.refresh_button.setToolTip("Refresh")
        self.refresh_button.clicked.connect(lambda: self.refresh())
        self.menu_button = QPushButton("", self)
        set_icon_button(self.menu_button, "fa6s.ellipsis", "•••")
        self.menu_button.setToolTip("Widget menu")
        self.menu_button.clicked.connect(self.show_context_menu)
        for button in (self.refresh_button, self.menu_button):
            button.setFixedSize(28, 25)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.hide()
        if not self.supports_refresh:
            self.refresh_button.hide()

        # Desktop Z-order is maintained by one shared manager timer instead of
        # one timer per widget, keeping idle wake-ups nearly constant as more
        # widgets are enabled.
        self.desktop_timer = None

    def apply_icons(self) -> None:
        set_icon_button(self.refresh_button, "fa6s.arrows-rotate", "↻")
        set_icon_button(self.menu_button, "fa6s.ellipsis", "•••")

    def restore_geometry(self, fallback: QRect) -> None:
        saved = self.config.get("geometry")
        rect = fallback
        if isinstance(saved, list) and len(saved) == 4:
            try:
                rect = QRect(*(int(v) for v in saved))
            except Exception:
                rect = fallback
        rect.setWidth(max(self.minimumWidth(), rect.width()))
        rect.setHeight(max(self.minimumHeight(), rect.height()))
        if not self.manager.rect_visible(rect):
            rect.moveTopLeft(fallback.topLeft())
        self.setGeometry(rect)

    def save_geometry(self) -> None:
        g = self.geometry()
        self.config["geometry"] = [g.x(), g.y(), g.width(), g.height()]
        STORE.save()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        # Qt may deliver a geometry event while the base constructor is still
        # creating child controls, particularly with platform DPI plugins.
        if hasattr(self, "content"):
            # Cards now use the full widget bounds; the old transparent outer
            # gutter existed only to make room for a painted drop shadow.
            self.content.setGeometry(8, 7, self.width() - 16, self.height() - 14)
            right = self.width() - 5
            self.menu_button.move(right - 28, 7)
            self.refresh_button.move(right - 60, 7)
            self.pending_save.start()
        super().resizeEvent(event)

    def moveEvent(self, event) -> None:  # type: ignore[override]
        self.pending_save.start()
        super().moveEvent(event)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if STORE.data["appearance"]["animations"]:
            self.setWindowOpacity(0.0)
            animation = QPropertyAnimation(self, b"windowOpacity", self)
            animation.setDuration(180)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        QTimer.singleShot(120, self.keep_at_desktop_level)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        colors = widget_palette_colors(); widget_dark = colors["surface"].lightness() < 145
        radius = widget_corner_radius()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Flat card edge: no painted drop shadow or background halo.
        card = self.rect().adjusted(2, 2, -2, -2)
        surface_top = QColor(colors["surface"]); surface_bottom = QColor(colors["surface"])
        surface_top = surface_top.lighter(112 if widget_dark else 103)
        surface_bottom = surface_bottom.darker(108 if widget_dark else 102)
        opacity_scale = max(0.35, min(1.0, float(self.config.get("opacity", 100)) / 100.0))
        surface_top.setAlpha(max(28, int(surface_top.alpha() * opacity_scale)))
        surface_bottom.setAlpha(max(28, int(surface_bottom.alpha() * opacity_scale)))
        card_gradient = QLinearGradient(card.left(), card.top(), card.left(), card.bottom())
        card_gradient.setColorAt(0, surface_top); card_gradient.setColorAt(1, surface_bottom)
        border = QColor(self.accent) if self.hovered else QColor(colors["border"])
        border.setAlpha(78 if self.hovered else colors["border"].alpha())
        p.setBrush(card_gradient); p.setPen(QPen(border, 1.0))
        p.drawRoundedRect(card, radius, radius)
        # Fine top-edge highlight gives the cards a machined Windows 11 finish.
        highlight = QLinearGradient(card.left(), card.top(), card.right(), card.top())
        highlight.setColorAt(0, QColor(255, 255, 255, 0))
        highlight.setColorAt(.5, QColor(255, 255, 255, 34 if widget_dark else 95))
        highlight.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(QPen(highlight, .8)); p.drawLine(card.left() + 18, card.top() + 1, card.right() - 18, card.top() + 1)
        self.paint_decor(p, card)
        if self.hovered and not self.config.get("locked", False):
            p.setPen(QPen(QColor(colors["muted"]), 1.4))
            x, y = self.width() - 22, self.height() - 22
            p.drawLine(x - 7, y, x, y - 7)
            p.drawLine(x - 3, y, x, y - 3)
        p.end()

    def paint_decor(self, painter: QPainter, card: QRect) -> None:
        pass

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self.hovered = True
        self.menu_button.show()
        if self.supports_refresh:
            self.refresh_button.show()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.hovered = False
            self.menu_button.hide()
            self.refresh_button.hide()
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            if not self.config.get("locked", False) and pos.x() >= self.width() - 28 and pos.y() >= self.height() - 28:
                self.resizing = True
                self.start_geometry = self.geometry()
                self.drag_offset = event.globalPosition().toPoint()
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                event.accept()
                return
            if not self.config.get("locked", False):
                self.dragging = True
                self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.raise_while_interacting()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        point = event.globalPosition().toPoint()
        if self.resizing:
            delta = point - self.drag_offset
            width = max(self.minimumWidth(), self.start_geometry.width() + delta.x())
            height = max(self.minimumHeight(), self.start_geometry.height() + delta.y())
            self.resize(width, height)
            event.accept()
            return
        if self.dragging:
            self.move(point - self.drag_offset)
            event.accept()
            return
        pos = event.position().toPoint()
        if not self.config.get("locked", False) and pos.x() >= self.width() - 28 and pos.y() >= self.height() - 28:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if self.dragging or self.resizing:
            self.dragging = self.resizing = False
            self.unsetCursor()
            self.save_geometry()
            QTimer.singleShot(450, self.keep_at_desktop_level)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        self.manager.open_settings(self.settings_page())
        event.accept()

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        self.show_context_menu(event.globalPos())

    def settings_page(self) -> str:
        return "Widgets"

    def size_presets(self) -> dict[str, tuple[str, QSize]]:
        if self.key.startswith("clock"):
            return {
                "ultra_mini": ("Ultra mini", QSize(190, 96)),
                "mini": ("Mini", QSize(240, 124)),
                "standard": ("Standard", QSize(300, 158)),
                "large": ("Large", QSize(420, 220)),
            }
        if self.key == "cpu":
            return {
                "ultra_mini": ("Ultra mini", QSize(270, 176)),
                "mini": ("Mini", QSize(320, 205)),
                "standard": ("Standard", QSize(370, 245)),
                "large": ("Large", QSize(520, 330)),
            }
        if self.key == "music":
            return {"ultra_mini":("Ultra mini",QSize(270,140)),"mini":("Mini",QSize(320,170)),"standard":("Standard",QSize(390,205)),"large":("Large",QSize(520,270))}
        if self.key == "goal":
            return {"ultra_mini":("Ultra mini",QSize(280,140)),"mini":("Mini",QSize(340,175)),"standard":("Standard",QSize(420,215)),"large":("Large",QSize(560,290))}
        if self.key == "calendar":
            return {"ultra_mini":("Ultra mini",QSize(280,230)),"mini":("Mini",QSize(320,270)),"standard":("Standard",QSize(380,340)),"large":("Large",QSize(500,440))}
        if self.key == "quotes":
            return {"ultra_mini":("Ultra mini",QSize(230,105)),"mini":("Mini",QSize(280,135)),"standard":("Standard",QSize(340,165)),"large":("Large",QSize(440,210))}
        return {
            "ultra_mini": ("Ultra mini", QSize(300, 305)),
            "mini": ("Mini", QSize(350, 390)),
            "standard": ("Standard", QSize(410, 465)),
            "large": ("Large", QSize(520, 620)),
        }

    def apply_size_preset(self, preset: str, persist: bool = True) -> None:
        presets = self.size_presets()
        if preset not in presets:
            preset = "standard"
        self.config["size_preset"] = preset
        self.last_size_preset = preset
        target = presets[preset][1]
        self.resize(target)
        if persist:
            self.save_geometry(); STORE.save()

    def set_widget_opacity(self, value: int) -> None:
        self.config["opacity"] = max(35, min(100, int(value)))
        STORE.save(); self.update()

    def show_context_menu(self, position: Optional[QPoint] = None) -> None:
        menu = QMenu()
        menu.setStyleSheet(app_stylesheet())
        settings_action = menu.addAction(awesome_icon("fa6s.gear"), "Settings")
        refresh_action = None
        if self.supports_refresh:
            refresh_action = menu.addAction(awesome_icon("fa6s.arrows-rotate"), "Refresh")
        menu.addSeparator()
        resize_action = menu.addAction(awesome_icon("fa6s.up-right-and-down-left-from-center"), "Resize widget")
        resize_action.setEnabled(not self.config.get("locked", False))
        size_menu = menu.addMenu("Size preset")
        size_actions: dict[QAction, str] = {}
        current_size = str(self.config.get("size_preset", "standard"))
        for preset, (label, _size) in self.size_presets().items():
            action = size_menu.addAction(label); action.setCheckable(True); action.setChecked(preset == current_size)
            size_actions[action] = preset
        opacity_menu = menu.addMenu("Transparency")
        opacity_actions: dict[QAction, int] = {}
        current_opacity = int(self.config.get("opacity", 100))
        for label, value in (("Solid", 100), ("Glass", 85), ("Transparent", 70), ("Ultra transparent", 55)):
            action = opacity_menu.addAction(label); action.setCheckable(True); action.setChecked(abs(current_opacity - value) < 4)
            opacity_actions[action] = value
        lock_action = menu.addAction(awesome_icon("fa6s.thumbtack"), "Pin position")
        lock_action.setCheckable(True)
        lock_action.setChecked(self.config.get("locked", False))
        top_action = menu.addAction(awesome_icon("fa6s.layer-group"), "Always on top")
        top_action.setCheckable(True)
        top_action.setChecked(self.config.get("always_top", False))
        menu.addSeparator()
        close_action = menu.addAction(awesome_icon("fa6s.xmark"), "Close widget")
        chosen = menu.exec(position or self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))
        if chosen == settings_action:
            self.manager.open_settings(self.settings_page())
        elif refresh_action is not None and chosen == refresh_action:
            self.refresh()
        elif chosen == resize_action:
            self.hovered = True
            self.update()
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            QTimer.singleShot(1400, self.unsetCursor)
        elif chosen in size_actions:
            self.apply_size_preset(size_actions[chosen])
        elif chosen in opacity_actions:
            self.set_widget_opacity(opacity_actions[chosen])
        elif chosen == lock_action:
            self.config["locked"] = lock_action.isChecked()
            STORE.save()
            self.update()
        elif chosen == top_action:
            self.set_always_top(top_action.isChecked())
        elif chosen == close_action:
            self.manager.set_enabled(self.key, False)

    def set_always_top(self, value: bool) -> None:
        self.config["always_top"] = bool(value)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(value))
        self.show()
        STORE.save()
        if not value:
            QTimer.singleShot(120, self.keep_at_desktop_level)

    def raise_while_interacting(self) -> None:
        self.raise_()

    def keep_at_desktop_level(self) -> None:
        """Keep an unpinned widget below normal app windows but above wallpaper.

        Qt's Tool flag removes taskbar clutter. HWND_BOTTOM gives native Windows
        desktop-gadget behavior: widgets are visible on the desktop and normal
        applications cover them. The user can opt into WindowStaysOnTopHint.
        """
        if self.config.get("always_top", False) or self.dragging or self.resizing:
            return
        if IS_WINDOWS and self.isVisible():
            try:
                user32 = ctypes.windll.user32
                desktop = windows_desktop_host()
                # GW_HWNDPREV is the window immediately above the desktop host.
                # Inserting after it puts this widget above the shell layer but
                # below ordinary application windows.
                GW_HWNDPREV = 3
                insert_after = user32.GetWindow(desktop, GW_HWNDPREV) if desktop else 0
                own_hwnd = int(self.winId())
                if insert_after == own_hwnd:
                    insert_after = user32.GetWindow(own_hwnd, GW_HWNDPREV)
                if not insert_after:
                    insert_after = 1  # HWND_BOTTOM, only as a last-resort fallback
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOACTIVATE = 0x0010
                user32.SetWindowPos(
                    own_hwnd, insert_after, 0, 0, 0, 0,
                    SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE,
                )
            except Exception:
                self.lower()
        elif self.isVisible():
            self.lower()

    def refresh(self) -> None:
        pass


class AnalogClockFace(QWidget):
    def __init__(self, accent: QColor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent = accent; self.current = dt.datetime.now().astimezone(); self.show_seconds = True
        self.setMinimumHeight(72); self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_time(self, value: dt.datetime, show_seconds: bool = True) -> None:
        self.current = value; self.show_seconds = show_seconds; self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = widget_palette_colors(); center = self.rect().center()
        radius = max(18.0, min(self.width(), self.height()) / 2.0 - 4.0)
        p.setPen(QPen(QColor(colors["border"]), 1)); p.setBrush(QColor(colors["control"]))
        p.drawEllipse(QPoint(center), int(radius), int(radius))
        for index in range(60):
            angle = math.radians(index * 6 - 90)
            outer = radius - 3; inner = radius - (9 if index % 5 == 0 else 5)
            alpha = 190 if index % 5 == 0 else 70
            tick = QColor(colors["text"]); tick.setAlpha(alpha)
            p.setPen(QPen(tick, 1.8 if index % 5 == 0 else .8))
            p.drawLine(
                int(center.x() + inner * math.cos(angle)), int(center.y() + inner * math.sin(angle)),
                int(center.x() + outer * math.cos(angle)), int(center.y() + outer * math.sin(angle)),
            )
        hour = (self.current.hour % 12) + self.current.minute / 60.0
        minute = self.current.minute + self.current.second / 60.0
        def hand(angle_value: float, length: float, width: float, color: QColor) -> None:
            angle = math.radians(angle_value - 90)
            p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(center, QPoint(int(center.x() + length * math.cos(angle)), int(center.y() + length * math.sin(angle))))
        hand(hour * 30, radius * .50, 4.2, QColor(colors["text"]))
        hand(minute * 6, radius * .72, 2.8, QColor(colors["text"]))
        if self.show_seconds:
            hand(self.current.second * 6, radius * .78, 1.2, self.accent)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(self.accent); p.drawEllipse(center, 3, 3)
        p.end()


class ClockWidget(BaseWidget):
    MIN_SIZE = QSize(180, 88)
    DEFAULT_SIZE = QSize(300, 158)

    def __init__(self, manager: "WidgetManager", key: str) -> None:
        super().__init__(manager, key)
        self.variant = int(self.config.get("variant", 0))
        self.content.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(16, 13, 16, 12)
        layout.setSpacing(1)
        self.kicker = QLabel()
        self.kicker.setObjectName("clockKicker")
        self.time_label = QLabel()
        self.time_label.setTextFormat(Qt.TextFormat.RichText)
        self.time_label.setObjectName("clockTime")
        self.date_label = QLabel()
        self.date_label.setObjectName("clockDate")
        self.zone_label = QLabel()
        self.zone_label.setObjectName("clockZone")
        self.analog_face = AnalogClockFace(self.accent)

        if self.variant == 0:
            layout.addWidget(self.kicker)
            layout.addStretch(1)
            layout.addWidget(self.time_label)
            layout.addWidget(self.analog_face, 1)
            layout.addWidget(self.date_label)
            self.time_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        elif self.variant == 1:
            layout.addWidget(self.kicker, alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addStretch(1)
            layout.addWidget(self.time_label)
            layout.addWidget(self.analog_face, 1)
            layout.addWidget(self.date_label)
            self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        elif self.variant == 2:
            top = QHBoxLayout()
            top.addWidget(self.kicker)
            top.addStretch()
            top.addWidget(self.zone_label)
            layout.addLayout(top)
            layout.addStretch(1)
            layout.addWidget(self.time_label)
            layout.addWidget(self.analog_face, 1)
            layout.addWidget(self.date_label)
            self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        else:
            top = QHBoxLayout()
            top.addWidget(self.kicker)
            top.addStretch()
            top.addWidget(self.zone_label)
            layout.addLayout(top)
            layout.addStretch(1)
            layout.addWidget(self.time_label)
            layout.addWidget(self.analog_face, 1)
            layout.addWidget(self.date_label)
            self.time_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.apply_clock_style()
        self.update_time()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "date_label"):
            self.date_label.setVisible(bool(self.config.get("show_date", True)) and self.height() >= 112)
            # The UTC offset used to appear as distracting small print in two
            # clock variants. Time-zone selection remains available in Settings,
            # but the desktop clock now keeps that implementation detail hidden.
            self.zone_label.hide()

    def settings_page(self) -> str:
        return "Clocks"

    def apply_clock_style(self) -> None:
        c = widget_palette_colors()
        alignment_extra = "letter-spacing: 1px;" if self.variant == 2 else ""
        self.content.setStyleSheet(f"""
            QLabel {{ background: transparent; color: {c['text'].name()}; }}
            QLabel#clockKicker {{ color: {self.accent.name()}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#clockTime {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 34px; font-weight: {550 if self.variant != 1 else 450}; {alignment_extra} }}
            QLabel#clockDate, QLabel#clockZone {{ color: {c['muted'].name()}; font-size: 11px; }}
        """)

    def paint_decor(self, painter: QPainter, card: QRect) -> None:
        if self.variant == 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.accent)
            painter.drawRoundedRect(card.left(), card.top() + 24, 3, card.height() - 48, 2, 2)
        elif self.variant == 1:
            glow = QColor(self.accent)
            glow.setAlpha(24)
            painter.setPen(QPen(QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 52), 1))
            painter.setBrush(glow)
            painter.drawEllipse(card.center().x() - 47, card.center().y() - 47, 94, 94)
        elif self.variant == 2:
            painter.setPen(QPen(QColor(self.accent.red(), self.accent.green(), self.accent.blue(), 80), 2))
            painter.drawLine(card.left() + 18, card.bottom() - 13, card.right() - 18, card.bottom() - 13)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            wash = QColor(self.accent)
            wash.setAlpha(18)
            painter.setBrush(wash)
            painter.drawEllipse(card.right() - 75, card.top() - 42, 120, 120)
            painter.setBrush(self.accent)
            painter.drawRoundedRect(card.left() + 18, card.top() + 19, 20, 3, 2, 2)

    def update_time(self) -> None:
        current = timezone_now(self.config.get("timezone", "Local"))
        use_24 = bool(self.config.get("format_24h", False))
        show_seconds = bool(self.config.get("show_seconds", True))
        if use_24:
            main = current.strftime("%H:%M")
            suffix = current.strftime(":%S") if show_seconds else ""
        else:
            main = current.strftime("%I:%M").lstrip("0")
            suffix = current.strftime(":%S %p") if show_seconds else current.strftime("%p")
        muted = widget_palette_colors()["muted"].name()
        self.time_label.setText(f"{main}<span style='font-size:13px;color:{muted};font-weight:500'> {suffix}</span>")
        analog = str(self.config.get("display_mode", "digital")) == "analog"
        self.time_label.setVisible(not analog); self.analog_face.setVisible(analog)
        self.analog_face.set_time(current, show_seconds)
        city = str(self.config.get("city", "Clock"))
        if self.variant == 1:
            self.kicker.setText(f"WORLD CLOCK  ·  {city.upper()}")
        else:
            self.kicker.setText(city.upper())
        self.date_label.setText(current.strftime("%A, %d %B %Y"))
        self.date_label.setVisible(bool(self.config.get("show_date", True)) and self.height() >= 112)
        # The configured time zone still drives the clock value; its raw UTC
        # offset is deliberately not printed on the desktop card.
        self.zone_label.clear()
        self.zone_label.hide()


class GPUPerformanceMonitor:
    """Lightweight Windows GPU sampler using the same PDH counters as Task Manager.

    Counters are created lazily when the user first opens the GPU slide. Values
    are grouped by GPU engine type and the busiest engine is reported, matching
    Task Manager's overall GPU percentage much more closely than summing every
    per-process engine counter.
    """

    PDH_FMT_DOUBLE = 0x00000200

    class CounterValue(ctypes.Structure):
        _fields_ = [("status", ctypes.c_ulong), ("value", ctypes.c_double)]

    def __init__(self) -> None:
        self.query = ctypes.c_void_p()
        self.counters: list[tuple[ctypes.c_void_p, str]] = []
        self.initialized = False
        self.available = False
        self.primed = False

    def initialize(self) -> None:
        if self.initialized:
            return
        self.initialized = True
        if not IS_WINDOWS:
            return
        try:
            pdh = ctypes.windll.pdh
            pdh.PdhExpandWildCardPathW.restype = ctypes.c_long
            pdh.PdhOpenQueryW.restype = ctypes.c_long
            pdh.PdhAddEnglishCounterW.restype = ctypes.c_long
            pdh.PdhCollectQueryData.restype = ctypes.c_long
            size = ctypes.c_ulong(0)
            wildcard = r"\GPU Engine(*)\Utilization Percentage"
            pdh.PdhExpandWildCardPathW(None, wildcard, None, ctypes.byref(size), 0)
            if not size.value:
                return
            buffer = ctypes.create_unicode_buffer(size.value)
            if pdh.PdhExpandWildCardPathW(None, wildcard, buffer, ctypes.byref(size), 0) != 0:
                return
            paths = [value for value in buffer[:size.value].split("\0") if value]
            if not paths or pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.query)) != 0:
                return
            for path in paths:
                counter = ctypes.c_void_p()
                if pdh.PdhAddEnglishCounterW(self.query, path, 0, ctypes.byref(counter)) == 0:
                    match = re.search(r"engtype_([^\)]+)", path, re.I)
                    engine = match.group(1).lower() if match else "graphics"
                    adapter_match = re.search(r"(luid_[^_]+_[^_]+_phys_\d+)", path, re.I)
                    adapter = adapter_match.group(1).lower() if adapter_match else "gpu0"
                    self.counters.append((counter, f"{adapter}:{engine}"))
            self.available = bool(self.counters)
            if self.available:
                pdh.PdhCollectQueryData(self.query)
        except Exception:
            self.close()

    def percent(self) -> Optional[float]:
        self.initialize()
        if not self.available or not self.query:
            return None
        try:
            pdh = ctypes.windll.pdh
            if pdh.PdhCollectQueryData(self.query) != 0:
                return None
            totals: dict[str, float] = {}
            for counter, engine in self.counters:
                value = self.CounterValue()
                if pdh.PdhGetFormattedCounterValue(
                    counter, self.PDH_FMT_DOUBLE, None, ctypes.byref(value)
                ) == 0 and value.status in (0, 1) and math.isfinite(value.value):
                    totals[engine] = totals.get(engine, 0.0) + max(0.0, value.value)
            if not totals:
                return None
            return max(0.0, min(100.0, max(totals.values())))
        except Exception:
            return None

    def close(self) -> None:
        if IS_WINDOWS and self.query:
            try:
                ctypes.windll.pdh.PdhCloseQuery(self.query)
            except Exception:
                pass
        self.query = ctypes.c_void_p()
        self.counters.clear()
        self.available = False

    def __del__(self) -> None:
        self.close()


class SystemMonitor:
    """Accurate, non-blocking CPU, memory and network sampler."""

    def __init__(self) -> None:
        self._last_idle = self._last_kernel = self._last_user = None
        self._last_cpu_wall = time.monotonic()
        self._last_cpu_value = 0.0
        self._last_net_time = time.monotonic()
        self._last_net: dict[str, Any] = {}
        if psutil:
            try:
                self._last_net = psutil.net_io_counters(pernic=True)
            except Exception:
                self._last_net = {}
        # Prime the exact same cumulative Windows kernel times used by Task
        # Manager-style samplers. The first displayed delta then spans one full
        # configured update interval rather than an arbitrary process lifetime.
        if IS_WINDOWS:
            self._windows_cpu_percent()
        elif psutil:
            try:
                psutil.cpu_percent(None)
            except Exception:
                pass

    @staticmethod
    def _filetime_value(value: Any) -> int:
        return (int(value.high) << 32) | int(value.low)

    def _windows_cpu_percent(self) -> Optional[float]:
        if not IS_WINDOWS:
            return None

        class FILETIME(ctypes.Structure):
            _fields_ = [("low", ctypes.c_ulong), ("high", ctypes.c_ulong)]

        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        try:
            if not ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
            ):
                return None
            now = (
                self._filetime_value(idle),
                self._filetime_value(kernel),
                self._filetime_value(user),
            )
            old = (self._last_idle, self._last_kernel, self._last_user)
            wall_now = time.monotonic()
            wall_elapsed = wall_now - self._last_cpu_wall
            self._last_cpu_wall = wall_now
            self._last_idle, self._last_kernel, self._last_user = now
            if old[0] is None:
                return self._last_cpu_value
            # Ignore constructor/UI bursts shorter than a meaningful sampling
            # window; the following regular timer tick supplies the real value.
            if wall_elapsed < 0.20:
                return self._last_cpu_value
            idle_delta = max(0, now[0] - int(old[0]))
            kernel_delta = max(0, now[1] - int(old[1]))
            user_delta = max(0, now[2] - int(old[2]))
            total_delta = kernel_delta + user_delta
            if total_delta <= 0:
                return self._last_cpu_value
            # GetSystemTimes' kernel value includes idle time.
            busy_delta = max(0, total_delta - idle_delta)
            self._last_cpu_value = max(0.0, min(100.0, busy_delta * 100.0 / total_delta))
            return self._last_cpu_value
        except Exception:
            return None

    def cpu_percent(self) -> float:
        # Prefer native Windows cumulative processor times. psutil remains the
        # accurate implementation on other platforms and a Windows fallback.
        native = self._windows_cpu_percent()
        if native is not None:
            return native
        if psutil:
            try:
                return max(0.0, min(100.0, float(psutil.cpu_percent(None))))
            except Exception:
                pass
        return 0.0

    def memory_details(self) -> tuple[float, float, float, float]:
        """Return percent, used GiB, total GiB and available GiB."""
        if psutil:
            try:
                memory = psutil.virtual_memory()
                gb = 1024.0 ** 3
                return (
                    float(memory.percent), float(memory.used) / gb,
                    float(memory.total) / gb, float(memory.available) / gb,
                )
            except Exception:
                pass
        if IS_WINDOWS:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong),
                    ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong),
                    ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong),
                    ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong),
                    ("avail_extended", ctypes.c_ulonglong),
                ]
            state = MEMORYSTATUSEX(); state.length = ctypes.sizeof(state)
            try:
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
                    gb = 1024.0 ** 3
                    total = float(state.total_phys) / gb
                    available = float(state.avail_phys) / gb
                    return float(state.memory_load), total - available, total, available
            except Exception:
                pass
        return 0.0, 0.0, 0.0, 0.0

    def ram_percent(self) -> float:
        return self.memory_details()[0]

    def disk_partitions(self) -> list[dict[str, Any]]:
        """Return mounted storage volumes using Windows' authoritative byte counters.

        Windows is queried first so the occupied percentage matches Explorer's
        ``total - total_free`` calculation.  psutil remains a portable fallback
        for non-Windows hosts and unusual Windows environments.
        """
        output: list[dict[str, Any]] = []

        if IS_WINDOWS:
            try:
                kernel32 = ctypes.windll.kernel32
                # Collect every logical drive exposed by Windows, then supplement
                # it with any mounted-folder paths reported by psutil.
                needed = int(kernel32.GetLogicalDriveStringsW(0, None))
                size = max(needed + 2, 512)
                buffer = ctypes.create_unicode_buffer(size)
                copied = int(kernel32.GetLogicalDriveStringsW(size, buffer))
                candidates: list[tuple[str, str]] = []
                if copied:
                    candidates.extend((path, path) for path in buffer[:copied].split("\x00") if path)
                if psutil:
                    try:
                        for part in psutil.disk_partitions(all=True):
                            mount = str(part.mountpoint or "").strip()
                            if mount:
                                candidates.append((mount, str(part.device or mount)))
                    except Exception:
                        pass

                seen_mounts: set[str] = set()
                seen_volumes: set[str] = set()
                drive_types = {2: "Removable", 3: "Local disk", 4: "Network drive", 6: "RAM disk"}
                system_drive = os.getenv("SystemDrive", "C:").lower().rstrip("\\/")
                for raw_mount, device in candidates:
                    mount = os.path.abspath(raw_mount) if not re.match(r"^[A-Za-z]:[\\/]?$", raw_mount) else raw_mount
                    if re.match(r"^[A-Za-z]:[\\/]?$", mount):
                        mount = mount[0].upper() + ":\\"
                    elif not mount.endswith(("\\", "/")):
                        mount += os.sep
                    mount_key = mount.lower().rstrip("\\/") or mount.lower()
                    if mount_key in seen_mounts:
                        continue
                    seen_mounts.add(mount_key)

                    drive_type = int(kernel32.GetDriveTypeW(ctypes.c_wchar_p(mount)))
                    # Unknown roots, missing media and optical drives are not
                    # occupancy-bearing storage partitions.
                    if drive_type in (0, 1, 5):
                        continue

                    available = ctypes.c_ulonglong()
                    total = ctypes.c_ulonglong()
                    total_free = ctypes.c_ulonglong()
                    if not kernel32.GetDiskFreeSpaceExW(
                        ctypes.c_wchar_p(mount), ctypes.byref(available),
                        ctypes.byref(total), ctypes.byref(total_free),
                    ) or total.value <= 0:
                        continue

                    volume_name = ctypes.create_unicode_buffer(261)
                    volume_id = ""
                    try:
                        if kernel32.GetVolumeNameForVolumeMountPointW(
                            ctypes.c_wchar_p(mount), volume_name, len(volume_name)
                        ):
                            volume_id = volume_name.value.lower()
                    except Exception:
                        volume_id = ""
                    identity = volume_id or mount_key
                    if identity in seen_volumes:
                        continue
                    seen_volumes.add(identity)

                    label_buffer = ctypes.create_unicode_buffer(261)
                    fs_buffer = ctypes.create_unicode_buffer(64)
                    serial = ctypes.c_ulong()
                    max_component = ctypes.c_ulong()
                    flags = ctypes.c_ulong()
                    try:
                        kernel32.GetVolumeInformationW(
                            ctypes.c_wchar_p(mount), label_buffer, len(label_buffer),
                            ctypes.byref(serial), ctypes.byref(max_component), ctypes.byref(flags),
                            fs_buffer, len(fs_buffer),
                        )
                    except Exception:
                        pass

                    total_bytes = int(total.value)
                    free_bytes = min(total_bytes, int(total_free.value))
                    used_bytes = max(0, total_bytes - free_bytes)
                    percent = max(0.0, min(100.0, used_bytes * 100.0 / total_bytes))
                    short_mount = mount.rstrip("\\/") or mount
                    volume_label = label_buffer.value.strip()
                    label = f"{short_mount} · {volume_label}" if volume_label else short_mount
                    output.append({
                        "id": identity,
                        "device": device,
                        "mount": mount,
                        "label": label,
                        "volume_label": volume_label,
                        "fstype": fs_buffer.value.strip() or drive_types.get(drive_type, "Windows volume"),
                        "drive_type": drive_types.get(drive_type, "Storage"),
                        "total": total_bytes,
                        "used": used_bytes,
                        "free": free_bytes,
                        "available": min(total_bytes, int(available.value)),
                        "percent": percent,
                        "source": "Windows volume API",
                        "is_system": mount_key == system_drive,
                    })
            except Exception:
                output = []

        if not output and psutil:
            try:
                seen: set[str] = set()
                for part in psutil.disk_partitions(all=False):
                    mount = str(part.mountpoint)
                    key = mount.lower().rstrip("\\/") or mount
                    if key in seen or "cdrom" in str(part.opts).lower():
                        continue
                    try:
                        usage = psutil.disk_usage(mount)
                    except (PermissionError, OSError):
                        continue
                    if usage.total <= 0:
                        continue
                    seen.add(key)
                    output.append({
                        "id": key,
                        "device": str(part.device), "mount": mount,
                        "label": mount.rstrip("\\/") or mount,
                        "fstype": str(part.fstype or "Storage"),
                        "drive_type": "Mounted volume",
                        "total": int(usage.total), "used": int(usage.used),
                        "free": int(usage.free), "available": int(usage.free),
                        "percent": max(0.0, min(100.0, float(usage.percent))),
                        "source": "psutil",
                        "is_system": mount == os.path.abspath(os.sep),
                    })
            except Exception:
                output = []

        output.sort(key=lambda item: (
            0 if item.get("is_system", False) else 1,
            str(item.get("mount", "")).lower(),
        ))
        return output

    def battery_status(self) -> Optional[dict[str, Any]]:
        """Return the laptop battery level, charging state and remaining time."""
        if psutil:
            try:
                battery = psutil.sensors_battery()
                if battery is not None:
                    seconds = int(battery.secsleft) if isinstance(battery.secsleft, (int,float)) and battery.secsleft >= 0 else -1
                    return {"percent": float(battery.percent), "plugged": bool(battery.power_plugged), "seconds": seconds}
            except Exception:
                pass
        if IS_WINDOWS:
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [("ACLineStatus",ctypes.c_ubyte),("BatteryFlag",ctypes.c_ubyte),("BatteryLifePercent",ctypes.c_ubyte),("SystemStatusFlag",ctypes.c_ubyte),("BatteryLifeTime",ctypes.c_ulong),("BatteryFullLifeTime",ctypes.c_ulong)]
            status = SYSTEM_POWER_STATUS()
            try:
                if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)) and status.BatteryFlag != 128 and status.BatteryLifePercent != 255:
                    seconds = int(status.BatteryLifeTime) if status.BatteryLifeTime != 0xFFFFFFFF else -1
                    return {"percent": float(status.BatteryLifePercent), "plugged": status.ACLineStatus == 1, "seconds": seconds}
            except Exception:
                pass
        return None

    def network_rates(self) -> tuple[float, float, str, bool]:
        """Return download B/s, upload B/s, adapter name and link state."""
        if not psutil:
            return 0.0, 0.0, "Network adapter", False
        try:
            current = psutil.net_io_counters(pernic=True)
            now = time.monotonic()
            elapsed = max(0.05, now - self._last_net_time)
            stats = psutil.net_if_stats()
            preferred: list[tuple[float, float, str, bool]] = []
            fallback: list[tuple[float, float, str, bool]] = []
            for name, value in current.items():
                low = name.lower()
                if "loopback" in low or low in ("lo", "lo0"):
                    continue
                old = self._last_net.get(name)
                down = max(0.0, float(value.bytes_recv - old.bytes_recv) / elapsed) if old else 0.0
                up = max(0.0, float(value.bytes_sent - old.bytes_sent) / elapsed) if old else 0.0
                linked = bool(stats.get(name) and stats[name].isup)
                entry = (down, up, name, linked)
                if any(token in low for token in ("wi-fi", "wifi", "wireless", "wlan")):
                    preferred.append(entry)
                elif linked:
                    fallback.append(entry)
            self._last_net = current
            self._last_net_time = now
            choices = preferred or fallback
            if choices:
                return max(choices, key=lambda item: (item[3], item[0] + item[1]))
        except Exception:
            pass
        return 0.0, 0.0, "Wi-Fi", False

    @staticmethod
    def cpu_name() -> str:
        if IS_WINDOWS:
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                winreg.CloseKey(key)
                return re.sub(r"\s+", " ", str(name)).strip()
            except Exception:
                pass
        return platform.processor() or platform.machine() or "Processor"

    @staticmethod
    def gpu_name() -> str:
        if IS_WINDOWS:
            script = "(Get-CimInstance Win32_VideoController | Where-Object {$_.Name} | Select-Object -First 1 -ExpandProperty Name)"
            try:
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                    capture_output=True, text=True, timeout=5, creationflags=flags,
                )
                name = re.sub(r"\s+", " ", result.stdout).strip()
                if name:
                    return name
            except Exception:
                pass
        return "Graphics processor"

    @staticmethod
    def temperature() -> Optional[float]:
        value, _provider = SystemMonitor.temperature_diagnostic()
        return value

    @staticmethod
    def temperature_diagnostic() -> tuple[Optional[float], str]:
        """Return a temperature and the provider that supplied it."""
        if psutil and not IS_WINDOWS:
            try:
                temps = psutil.sensors_temperatures()
                for group in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
                    values = temps.get(group, [])
                    sensible = [float(item.current) for item in values if 0 < float(item.current) < 120]
                    if sensible:
                        return max(sensible), f"psutil/{group}"
            except Exception:
                pass
            return None, "No supported psutil sensor"
        if not IS_WINDOWS:
            return None, "No supported sensor provider"
        script = r"""
$ErrorActionPreference='SilentlyContinue'
function MaximumTemp($namespace) {
  $v = Get-CimInstance -Namespace $namespace -ClassName Sensor | Where-Object { $_.SensorType -eq 'Temperature' -and ($_.Name -match 'CPU|Core|Package|Tctl|Tdie') } | Select-Object -ExpandProperty Value
  if ($v) { return ($v | Where-Object { $_ -gt 5 -and $_ -lt 120 } | Measure-Object -Maximum | Select-Object -ExpandProperty Maximum) }
}
$v = MaximumTemp 'root/LibreHardwareMonitor'; if ($v) { Write-Output "LibreHardwareMonitor|$v"; exit }
$v = MaximumTemp 'root/OpenHardwareMonitor'; if ($v) { Write-Output "OpenHardwareMonitor|$v"; exit }
$v = Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | ForEach-Object { ($_.CurrentTemperature / 10.0) - 273.15 } | Where-Object { $_ -gt 5 -and $_ -lt 120 } | Measure-Object -Maximum | Select-Object -ExpandProperty Maximum
if ($v) { Write-Output "Windows ACPI thermal zone|$v"; exit }
# Newer Windows 10/11 builds may expose the same sensor through formatted
# performance data even when the legacy root/wmi class is blocked.
$v = Get-CimInstance -Namespace root/cimv2 -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation | ForEach-Object {
  $raw = $_.HighPrecisionTemperature
  if (-not $raw) { $raw = $_.Temperature }
  if ($raw -gt 1000) { ($raw / 10.0) - 273.15 } elseif ($raw -gt 200) { $raw - 273.15 } else { $raw }
} | Where-Object { $_ -gt 5 -and $_ -lt 120 } | Measure-Object -Maximum | Select-Object -ExpandProperty Maximum
if ($v) { Write-Output "Windows thermal performance counter|$v"; exit }
try {
  $v = (Get-Counter '\Thermal Zone Information(*)\Temperature' -SampleInterval 1 -MaxSamples 1).CounterSamples.CookedValue | ForEach-Object { if ($_ -gt 200) { $_ - 273.15 } else { $_ } } | Where-Object { $_ -gt 5 -and $_ -lt 120 } | Measure-Object -Maximum | Select-Object -ExpandProperty Maximum
  if ($v) { Write-Output "Windows thermal zone counter|$v"; exit }
} catch {}
"""
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                capture_output=True, text=True, timeout=6, creationflags=flags,
            )
            text = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
            if "|" in text:
                provider, raw = text.split("|", 1)
                return float(raw.strip().replace(",", ".")), provider.strip()
        except Exception:
            pass
        return None, "LibreHardwareMonitor, OpenHardwareMonitor and ACPI were not available"


class GraphWidget(QWidget):
    def __init__(self, accent: QColor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent = accent
        self.values: deque[float] = deque([0.0] * 60, maxlen=60)
        self.setMinimumHeight(45)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def append(self, value: float) -> None:
        self.values.append(max(0.0, min(100.0, value)))
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 3, -1, -2)
        grid = widget_palette_colors()["border"]
        p.setPen(QPen(grid, 1))
        for factor in (.25, .5, .75):
            y = rect.top() + rect.height() * factor
            p.drawLine(rect.left(), int(y), rect.right(), int(y))
        values = list(self.values)
        if len(values) < 2:
            return
        path = QPainterPath()
        step = rect.width() / max(1, len(values) - 1)
        for i, value in enumerate(values):
            x = rect.left() + i * step
            y = rect.bottom() - (value / 100.0) * rect.height()
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        fill = QPainterPath(path)
        fill.lineTo(rect.right(), rect.bottom())
        fill.lineTo(rect.left(), rect.bottom())
        fill.closeSubpath()
        gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
        top = QColor(self.accent); top.setAlpha(85)
        bottom = QColor(self.accent); bottom.setAlpha(4)
        gradient.setColorAt(0, top); gradient.setColorAt(1, bottom)
        p.fillPath(fill, gradient)
        p.setPen(QPen(self.accent, 2.0))
        p.drawPath(path)
        p.end()


class HardwareBridge(QObject):
    temperature = Signal(object)
    gpu_name = Signal(str)


def format_data_rate(value: float) -> str:
    value = max(0.0, value)
    if value >= 1024 ** 3:
        return f"{value / 1024 ** 3:.1f} GB/s"
    if value >= 1024 ** 2:
        return f"{value / 1024 ** 2:.1f} MB/s"
    return f"{value / 1024:.0f} KB/s"


def format_storage(value: float) -> str:
    if value >= 1024 ** 4:
        return f"{value / 1024 ** 4:.1f} TB"
    if value >= 1024 ** 3:
        return f"{value / 1024 ** 3:.1f} GB"
    return f"{value / 1024 ** 2:.0f} MB"


def format_battery_time(seconds: int) -> str:
    if seconds < 0:
        return "—"
    hours, remainder = divmod(seconds, 3600); minutes = remainder // 60
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


class DiskPartitionRow(QFrame):
    def __init__(self, volume: dict[str, Any], accent: QColor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent); self.volume = volume; self.accent = accent
        self.setObjectName("diskPartitionRow"); self.setFixedHeight(62)
        layout = QVBoxLayout(self); layout.setContentsMargins(10, 6, 10, 6); layout.setSpacing(4)
        top = QHBoxLayout(); top.setSpacing(8)
        self.name_label = QLabel(); self.name_label.setObjectName("diskName")
        self.detail_label = QLabel(); self.detail_label.setObjectName("diskDetail")
        self.percent_label = QLabel(); self.percent_label.setObjectName("diskPercent")
        top.addWidget(self.name_label); top.addWidget(self.detail_label); top.addStretch(); top.addWidget(self.percent_label)
        self.bar = QProgressBar(); self.bar.setRange(0,1000); self.bar.setTextVisible(False); self.bar.setFixedHeight(7)
        layout.addLayout(top); layout.addWidget(self.bar); self.apply_data(volume, accent)

    def apply_data(self, volume: dict[str, Any], accent: QColor) -> None:
        self.volume = volume; self.accent = QColor(accent); colors = widget_palette_colors()
        label = str(volume.get("label") or volume.get("mount") or "Volume")
        fstype = str(volume.get("fstype") or "Storage")
        used = float(volume.get("used",0)); total = float(volume.get("total",0)); percent = float(volume.get("percent",0))
        free = float(volume.get("free",0)); drive_type = str(volume.get("drive_type") or "Storage")
        self.name_label.setText(label); self.detail_label.setText(f"{fstype}  ·  {format_storage(used)} used  ·  {format_storage(free)} free")
        self.percent_label.setText(f"{percent:.1f}%"); self.bar.setValue(int(round(percent * 10.0)))
        source = str(volume.get("source") or "system storage API")
        self.setToolTip(f"{label}\n{drive_type} · {fstype}\n{format_storage(used)} used · {format_storage(free)} free · {format_storage(total)} total\nMeasured with {source}")
        row_radius = max(2, widget_corner_radius() - 5)
        self.setStyleSheet(f"""
            QFrame#diskPartitionRow {{ background: rgba({colors['control'].red()},{colors['control'].green()},{colors['control'].blue()},34); border:1px solid {colors['border'].name(QColor.NameFormat.HexArgb)}; border-radius:{row_radius}px; }}
            QLabel {{ background:transparent; border:none; color:{colors['text'].name()}; }}
            QLabel#diskName, QLabel#diskPercent {{ font-weight:700; font-size:12px; }}
            QLabel#diskDetail {{ color:{colors['muted'].name()}; font-size:10px; }}
            QProgressBar {{ background:{colors['control'].name(QColor.NameFormat.HexArgb)}; border:none; border-radius:3px; }}
            QProgressBar::chunk {{ background:{self.accent.name()}; border-radius:3px; }}
        """)


class CPUWidget(BaseWidget):
    """A four-slide system monitor: CPU, GPU, memory and Wi-Fi."""

    MIN_SIZE = QSize(260, 168)
    DEFAULT_SIZE = QSize(370, 245)
    METRICS = ("CPU", "GPU", "RAM", "WI-FI", "DISKS", "BATTERY")
    METRIC_ICONS = ("fa6s.microchip", "fa6s.display", "fa6s.memory", "fa6s.wifi", "fa6s.hard-drive", "fa6s.battery-half")
    METRIC_COLORS = ("#4BC0FF", "#A889FF", "#42D3A5", "#FFB547", "#FF718B", "#7BD88F")

    def __init__(self, manager: "WidgetManager", key: str) -> None:
        super().__init__(manager, key)
        self.content.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.monitor = SystemMonitor()
        self.cpu_model = self.monitor.cpu_name()
        self.gpu_monitor = GPUPerformanceMonitor()
        self.metric_index = max(0, min(len(self.METRICS) - 1, int(self.config.get("metric_index", 0))))
        self.histories: dict[str, deque[float]] = {
            name: deque([0.0] * 60, maxlen=60) for name in self.METRICS
        }
        self.values = {"CPU": 0.0, "GPU": None, "RAM": 0.0, "DISKS": 0.0, "BATTERY": None}
        self.memory_used = self.memory_total = self.memory_available = 0.0
        self.disk_volumes: list[dict[str, Any]] = []
        self.disk_counter = 10000
        self.disk_rows: list[DiskPartitionRow] = []
        self.battery_info: Optional[dict[str, Any]] = None
        self.battery_probed = False; self.battery_counter = 10000
        self.net_down = self.net_up = 0.0
        self.net_adapter = "Wi-Fi"
        self.net_connected = False
        self.network_peak = 128 * 1024.0
        self.gpu_model = "Detecting graphics processor…"
        self.gpu_name_in_progress = False
        self.temp_in_progress = False
        self.temp_has_probed = False
        self.last_temp: Optional[float] = None
        self.last_temp_provider = "Searching for a compatible sensor…"
        self.gpu_alert_counter = 0
        self.alert_active = {"CPU": False, "GPU": False, "RAM": False, "TEMP": False}
        self.alert_streak = {"CPU": 0, "GPU": 0, "RAM": 0, "TEMP": 0}
        self.alert_last_sent = {"CPU": 0.0, "GPU": 0.0, "RAM": 0.0, "TEMP": 0.0}
        self.hardware_bridge = HardwareBridge(self)
        self.hardware_bridge.temperature.connect(self.temperature_ready)
        self.hardware_bridge.gpu_name.connect(self.gpu_name_ready)

        root = QVBoxLayout(self.content)
        root.setContentsMargins(16, 13, 16, 9)
        root.setSpacing(5)
        header = QHBoxLayout(); header.setSpacing(7)
        self.metric_icon = QLabel()
        self.metric_icon.setFixedSize(15, 15)
        self.metric_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = QLabel("CPU MONITOR")
        self.title_label.setObjectName("cpuTitle")
        self.temp_label = QLabel("TEMP  —")
        self.temp_label.setObjectName("mutedSmall")
        header.addWidget(self.metric_icon)
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.temp_label)
        root.addLayout(header)

        middle = QHBoxLayout()
        self.usage_label = QLabel("0%")
        self.usage_label.setObjectName("cpuUsage")
        self.detail_label = QLabel("CURRENT\nUSAGE")
        self.detail_label.setObjectName("mutedSmall")
        middle.addWidget(self.usage_label)
        middle.addWidget(self.detail_label)
        middle.addStretch()
        self.secondary_label = QLabel("RAM\n—")
        self.secondary_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.secondary_label.setObjectName("ramLabel")
        self.ram_label = self.secondary_label  # Backward-compatible attribute.
        middle.addWidget(self.secondary_label)
        root.addLayout(middle)
        self.graph = GraphWidget(self.metric_color())
        root.addWidget(self.graph, 1)
        self.model_label = QLabel(self.cpu_model)
        self.model_label.setObjectName("model"); self.model_label.setWordWrap(True); self.model_label.setMaximumHeight(30)
        root.addWidget(self.model_label)
        self.page_label = QLabel()
        self.page_label.setTextFormat(Qt.TextFormat.RichText)
        self.page_label.setObjectName("metricPager")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setFixedHeight(20)
        root.addWidget(self.page_label)

        # Direct children remain clickable while the data surface passes drag
        # events through to BaseWidget.
        self.previous_metric_button = QPushButton("", self)
        self.previous_metric_button.setToolTip("Previous system metric")
        self.previous_metric_button.setFixedSize(25, 25)
        self.previous_metric_button.clicked.connect(lambda: self.change_metric(-1))
        self.next_metric_button = QPushButton("", self)
        self.next_metric_button.setToolTip("Next system metric")
        self.next_metric_button.setFixedSize(25, 25)
        self.next_metric_button.clicked.connect(lambda: self.change_metric(1))

        self.disk_scroll = QScrollArea(self); self.disk_scroll.setWidgetResizable(True)
        self.disk_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.disk_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.disk_scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background:transparent; border:none; }")
        self.disk_host = QWidget(); self.disk_host.setStyleSheet("background:transparent;")
        self.disk_layout = QVBoxLayout(self.disk_host); self.disk_layout.setContentsMargins(0,0,4,0); self.disk_layout.setSpacing(5); self.disk_layout.addStretch()
        self.disk_scroll.setWidget(self.disk_host); self.disk_scroll.hide()
        self.disk_header_icon = QLabel(self); self.disk_header_icon.setFixedSize(16,16); self.disk_header_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True); self.disk_header_icon.hide()
        self.disk_header_label = QLabel("DISK PARTITIONS",self); self.disk_header_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True); self.disk_header_label.hide()
        self.disk_pager_label = QLabel(self); self.disk_pager_label.setTextFormat(Qt.TextFormat.RichText); self.disk_pager_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.disk_pager_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True); self.disk_pager_label.hide()

        self.timer = QTimer(self); self.timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.timer.timeout.connect(self.sample)
        self.temp_counter = 0
        self.apply_cpu_style()
        self.apply_icons()
        self.restart_timer()
        self.render_metric()
        self.sample()

    def settings_page(self) -> str:
        return "CPU"

    def apply_icons(self) -> None:
        super().apply_icons()
        if hasattr(self, "previous_metric_button"):
            set_icon_button(self.previous_metric_button, "fa6s.chevron-left", "‹", 11)
            set_icon_button(self.next_metric_button, "fa6s.chevron-right", "›", 11)
            self.update_metric_icon()

    def metric_color(self, index: Optional[int] = None) -> QColor:
        index = self.metric_index if index is None else index
        if STORE.data["appearance"].get("custom_widget_colors", False):
            return QColor(self.accent)
        return QColor(self.METRIC_COLORS[index])

    def update_disk_rows(self) -> None:
        identities = [str(volume.get("id") or volume.get("mount") or volume.get("device")) for volume in self.disk_volumes]
        current = [str(row.volume.get("id") or row.volume.get("mount") or row.volume.get("device")) for row in self.disk_rows]
        if identities == current:
            for row, volume in zip(self.disk_rows, self.disk_volumes):
                row.apply_data(volume, self.metric_color(4))
        else:
            for row in self.disk_rows:
                self.disk_layout.removeWidget(row); row.hide(); row.deleteLater()
            self.disk_rows.clear()
            for volume in self.disk_volumes:
                row = DiskPartitionRow(volume, self.metric_color(4))
                self.disk_layout.insertWidget(self.disk_layout.count()-1, row); self.disk_rows.append(row)
        self.disk_host.setMinimumHeight(max(1, len(self.disk_rows) * 67))

    def update_metric_icon(self) -> None:
        if not hasattr(self, "metric_icon"):
            return
        icon = awesome_icon(self.METRIC_ICONS[self.metric_index], self.metric_color().name())
        self.metric_icon.setPixmap(icon.pixmap(14, 14) if not icon.isNull() else QPixmap())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "previous_metric_button"):
            center = self.width() // 2
            y = self.height() - 49
            self.previous_metric_button.move(center - 102, y)
            self.next_metric_button.move(center + 77, y)
            if hasattr(self, "disk_scroll"):
                self.disk_header_icon.move(31,27); self.disk_header_label.move(52,24); self.disk_header_label.resize(max(120,self.width()-100),22)
                self.disk_scroll.setGeometry(30, 52, max(120, self.width() - 60), max(72, self.height() - 107))
                self.disk_pager_label.setGeometry(center-92,self.height()-49,184,24)
                self.disk_header_icon.raise_(); self.disk_header_label.raise_(); self.disk_scroll.raise_(); self.disk_pager_label.raise_()
            self.previous_metric_button.raise_(); self.next_metric_button.raise_()

    def paint_decor(self, painter: QPainter, card: QRect) -> None:
        color = self.metric_color()
        painter.setPen(Qt.PenStyle.NoPen)
        wash = QColor(color); wash.setAlpha(16)
        painter.setBrush(wash)
        painter.drawEllipse(card.right() - 90, card.top() - 55, 145, 145)

    def apply_cpu_style(self) -> None:
        c = widget_palette_colors()
        accent = self.metric_color().name()
        self.content.setStyleSheet(f"""
            QLabel {{ background: transparent; color: {c['text'].name()}; }}
            QLabel#cpuTitle {{ color: {accent}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#cpuUsage {{ font-family: "Segoe UI Variable Display", "Segoe UI"; font-size: 31px; font-weight: 600; }}
            QLabel#mutedSmall, QLabel#model {{ color: {c['muted'].name()}; font-size: 10px; font-weight: 600; }}
            QLabel#ramLabel {{ color: {c['muted'].name()}; font-size: 11px; }}
            QLabel#metricPager {{ color: {c['muted'].name()}; font-size: 10px; font-weight: 600; }}
        """)
        if hasattr(self,"disk_header_label"):
            self.disk_header_label.setStyleSheet(f"background:transparent;color:{self.metric_color(4).name()};font-size:11px;font-weight:700;letter-spacing:1px;")
            self.disk_pager_label.setStyleSheet(f"background:transparent;color:{c['muted'].name()};font-size:10px;font-weight:600;")
            icon=awesome_icon("fa6s.hard-drive",self.metric_color(4).name());self.disk_header_icon.setPixmap(icon.pixmap(14,14))

    def restart_timer(self) -> None:
        interval = max(500, min(5000, int(self.config.get("interval_ms", 2000))))
        if performance_mode() == "eco": interval = max(3000, interval)
        self.timer.start(interval)

    def change_metric(self, offset: int) -> None:
        self.set_metric((self.metric_index + offset) % len(self.METRICS))

    def set_metric(self, index: int) -> None:
        self.metric_index = max(0, min(len(self.METRICS) - 1, int(index)))
        self.config["metric_index"] = self.metric_index
        STORE.save()
        if self.metric_index == 1:
            self.request_gpu_name()
        elif self.metric_index == 4:
            # Force a fresh Windows volume query when the user opens Disks.
            self.disk_counter = 30000
            QTimer.singleShot(0, self.sample)
        self.apply_cpu_style(); self.apply_icons(); self.render_metric(); self.update()

    def request_gpu_name(self) -> None:
        if self.gpu_name_in_progress or self.gpu_model != "Detecting graphics processor…":
            return
        self.gpu_name_in_progress = True
        future = self.manager.executor.submit(SystemMonitor.gpu_name)
        bridge_ref = weakref.ref(self.hardware_bridge)
        def done(result) -> None:
            bridge = bridge_ref()
            if bridge is not None:
                try:
                    bridge.gpu_name.emit(str(result.result()))
                except Exception:
                    bridge.gpu_name.emit("Graphics processor")
        future.add_done_callback(done)

    def gpu_name_ready(self, value: str) -> None:
        self.gpu_name_in_progress = False
        self.gpu_model = value or "Graphics processor"
        if self.metric_index == 1:
            self.render_metric()

    def sample(self) -> None:
        cpu = self.monitor.cpu_percent()
        ram, used, total, available = self.monitor.memory_details()
        down, up, adapter, connected = self.monitor.network_rates()
        self.values["CPU"] = cpu
        self.values["RAM"] = ram
        self.memory_used, self.memory_total, self.memory_available = used, total, available
        self.net_down, self.net_up = down, up
        self.net_adapter, self.net_connected = adapter, connected
        self.histories["CPU"].append(cpu)
        self.histories["RAM"].append(ram)
        traffic = down + up
        self.network_peak = max(128 * 1024.0, self.network_peak * 0.96, traffic)
        self.histories["WI-FI"].append(min(100.0, traffic * 100.0 / self.network_peak))

        interval = max(500, int(self.config.get("interval_ms", 2000)))
        self.disk_counter += interval
        disk_refresh_ms = 5000 if self.metric_index == 4 else 30000
        if self.disk_counter >= disk_refresh_ms or not self.disk_volumes:
            self.disk_counter = 0
            self.disk_volumes = self.monitor.disk_partitions()
            disk_percent = float(self.disk_volumes[0]["percent"]) if self.disk_volumes else 0.0
            self.values["DISKS"] = disk_percent
            self.histories["DISKS"].append(disk_percent); self.update_disk_rows()
        self.battery_counter += interval
        if self.battery_counter >= 10000 or not self.battery_probed:
            self.battery_counter = 0; self.battery_probed = True; self.battery_info = self.monitor.battery_status()
            battery_percent = float(self.battery_info["percent"]) if self.battery_info else 0.0
            self.values["BATTERY"] = battery_percent if self.battery_info else None
            self.histories["BATTERY"].append(battery_percent)
        alerts_enabled = bool(self.config.get("alerts_enabled", False))
        self.gpu_alert_counter += interval
        # GPU PDH stays lazy. When alerts are enabled it is sampled every five
        # seconds even if another slide is visible.
        sample_gpu = self.metric_index == 1 or (alerts_enabled and self.gpu_alert_counter >= 5000)
        if sample_gpu:
            self.gpu_alert_counter = 0
            gpu = self.gpu_monitor.percent()
            self.values["GPU"] = gpu
            self.histories["GPU"].append(float(gpu or 0.0))
            if self.metric_index == 1:
                self.request_gpu_name()

        self.temp_counter += interval
        show_temp = bool(self.config.get("show_temperature", True))
        need_temperature = show_temp or alerts_enabled
        if need_temperature and (not self.temp_has_probed or self.temp_counter >= 60000) and not self.temp_in_progress:
            self.temp_counter = 0
            self.temp_in_progress = True
            future = self.manager.executor.submit(SystemMonitor.temperature_diagnostic)
            bridge_ref = weakref.ref(self.hardware_bridge)
            def done(result) -> None:
                bridge = bridge_ref()
                if bridge is not None:
                    try:
                        bridge.temperature.emit(result.result())
                    except Exception:
                        bridge.temperature.emit(None)
            future.add_done_callback(done)
        self.check_performance_alerts()
        self.render_metric()

    def check_performance_alerts(self) -> None:
        if not self.config.get("alerts_enabled", False):
            for key in self.alert_active:
                self.alert_active[key] = False; self.alert_streak[key] = 0
            return
        values: dict[str, Optional[float]] = {
            "CPU": float(self.values.get("CPU") or 0.0),
            "GPU": float(self.values["GPU"]) if isinstance(self.values.get("GPU"), (int, float)) else None,
            "RAM": float(self.values.get("RAM") or 0.0),
            "TEMP": self.last_temp,
        }
        thresholds = {
            "CPU": float(self.config.get("alert_cpu", 90)),
            "GPU": float(self.config.get("alert_gpu", 95)),
            "RAM": float(self.config.get("alert_ram", 90)),
            "TEMP": float(self.config.get("alert_temp", 90)),
        }
        labels = {"CPU": "CPU usage", "GPU": "GPU usage", "RAM": "Memory usage", "TEMP": "CPU temperature"}
        now = time.monotonic()
        cooldown = max(60.0, float(self.config.get("alert_cooldown_minutes", 10)) * 60.0)
        for key, value in values.items():
            if value is None:
                continue
            threshold = thresholds[key]
            hysteresis = 3.0 if key == "TEMP" else 5.0
            if value >= threshold:
                self.alert_streak[key] += 1
            else:
                self.alert_streak[key] = 0
            if value < threshold - hysteresis:
                self.alert_active[key] = False
            required_samples = 1 if key == "TEMP" else (2 if key == "GPU" else 3)
            if self.alert_streak[key] >= required_samples and not self.alert_active[key] and (self.alert_last_sent[key] == 0.0 or now - self.alert_last_sent[key] >= cooldown):
                unit = "°C" if key == "TEMP" else "%"
                self.manager.show_performance_alert(
                    f"High {labels[key]}",
                    f"{labels[key]} reached {value:.0f}{unit} (alert threshold {threshold:.0f}{unit}).",
                    key, value, threshold,
                )
                self.alert_active[key] = True
                self.alert_last_sent[key] = now

    def acknowledge_alert(self, metric: str) -> None:
        if metric in self.alert_active:
            self.alert_active[metric] = False
            self.alert_streak[metric] = 0
            self.alert_last_sent[metric] = time.monotonic()

    def render_metric(self) -> None:
        name = self.METRICS[self.metric_index]
        color = self.metric_color(); self.graph.accent = color; self.graph.values = self.histories[name]; self.graph.update()
        title = {"RAM":"MEMORY MONITOR","DISKS":"DISK PARTITIONS","BATTERY":"BATTERY STATUS"}.get(name, f"{name} MONITOR")
        self.title_label.setText(title)
        disk_mode = name == "DISKS"
        self.disk_scroll.setVisible(disk_mode); self.disk_header_icon.setVisible(disk_mode); self.disk_header_label.setVisible(disk_mode); self.disk_pager_label.setVisible(disk_mode)
        self.metric_icon.setVisible(not disk_mode); self.title_label.setVisible(not disk_mode); self.page_label.setVisible(not disk_mode)
        if disk_mode:
            self.disk_header_icon.raise_(); self.disk_header_label.raise_(); self.disk_scroll.raise_(); self.disk_pager_label.raise_(); self.previous_metric_button.raise_(); self.next_metric_button.raise_()
        for control in (self.usage_label, self.detail_label, self.temp_label, self.secondary_label, self.graph, self.model_label):
            control.setVisible(not disk_mode)
        self.secondary_label.show() if not disk_mode else None

        if name == "CPU":
            cpu = float(self.values["CPU"] or 0.0); self.usage_label.setText(f"{cpu:.0f}%"); self.detail_label.setText("CURRENT\nUSAGE")
            self.temp_label.setVisible(bool(self.config.get("show_temperature", True)))
            self.temp_label.setText(f"TEMP  {self.last_temp:.0f}°C" if self.last_temp is not None else "TEMP  —"); self.temp_label.setToolTip(self.last_temp_provider)
            if self.config.get("show_ram", True): self.secondary_label.setText(f"RAM\n{float(self.values['RAM'] or 0):.0f}%")
            else: self.secondary_label.hide()
            self.model_label.setText(self.cpu_model)
        elif name == "GPU":
            gpu = self.values["GPU"]; self.usage_label.setText("N/A" if gpu is None else f"{float(gpu):.0f}%"); self.detail_label.setText("CURRENT\nUSAGE")
            self.temp_label.setText("WINDOWS PDH" if IS_WINDOWS else "SENSOR N/A"); self.secondary_label.setText("ENGINE\nBUSIEST")
            self.model_label.setText(self.gpu_model if gpu is not None else "GPU performance counters unavailable")
        elif name == "RAM":
            ram = float(self.values["RAM"] or 0.0); self.usage_label.setText(f"{ram:.0f}%"); self.detail_label.setText("MEMORY\nIN USE")
            self.temp_label.setText(f"AVAILABLE  {self.memory_available:.1f} GB"); self.secondary_label.setText(f"USED\n{self.memory_used:.1f} GB")
            self.model_label.setText(f"{self.memory_used:.1f} of {self.memory_total:.1f} GB physical memory")
        elif name == "WI-FI":
            self.usage_label.setText(format_data_rate(self.net_down)); self.detail_label.setText("DOWNLOAD\nRATE")
            self.temp_label.setText("NETWORK LIVE" if self.net_connected else "NO LINK"); self.secondary_label.setText(f"UPLOAD\n{format_data_rate(self.net_up)}")
            self.model_label.setText(self.net_adapter if self.net_connected else "Wi-Fi is not connected")
        elif name == "DISKS":
            if not self.disk_rows:
                self.update_disk_rows()
        else:
            if self.battery_info:
                percent = float(self.battery_info["percent"]); plugged = bool(self.battery_info["plugged"]); seconds = int(self.battery_info.get("seconds",-1))
                self.usage_label.setText(f"{percent:.0f}%"); self.detail_label.setText("BATTERY\nLEVEL")
                self.temp_label.setText("PLUGGED IN" if plugged else "ON BATTERY")
                self.secondary_label.setText(f"TIME\n{format_battery_time(seconds)}" if not plugged else "POWER\nCHARGING")
                self.model_label.setText("Laptop battery detected · charging" if plugged else "Laptop battery detected · running on battery")
            else:
                self.usage_label.setText("N/A"); self.detail_label.setText("NO\nBATTERY")
                self.temp_label.setText("DESKTOP SYSTEM"); self.secondary_label.setText("POWER\nAC")
                self.model_label.setText("No battery detected — this appears to be a desktop system")
        dots = ["●" if i == self.metric_index else "○" for i in range(len(self.METRICS))]
        pager_text=f"{'  '.join(dots)}&nbsp;&nbsp; {name}"; self.page_label.setText(pager_text); self.disk_pager_label.setText(pager_text); self.update()

    def temperature_ready(self, value: object) -> None:
        self.temp_in_progress = False
        self.temp_has_probed = True
        if isinstance(value, (tuple, list)) and len(value) >= 2:
            reading, provider = value[0], str(value[1])
            self.last_temp = float(reading) if isinstance(reading, (float, int)) else None
            self.last_temp_provider = provider
        else:
            self.last_temp = float(value) if isinstance(value, (float, int)) else None
            self.last_temp_provider = "No compatible Windows temperature sensor responded"
        self.temp_label.setToolTip(self.last_temp_provider)
        self.check_performance_alerts()
        if self.metric_index == 0:
            self.render_metric()

    def refresh(self) -> None:
        self.sample()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.gpu_monitor.close()
        super().closeEvent(event)


class ImageTileWidget(QWidget):
    def __init__(self, accent: QColor, icon_name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent, self.icon_name, self.pixmap = accent, icon_name, QPixmap()
        self.setMinimumSize(72, 72)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_image(self, path: str) -> None:
        self.pixmap = QPixmap(path) if path and Path(path).is_file() else QPixmap()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1); radius = max(2, widget_corner_radius() - 3)
        clip = QPainterPath(); clip.addRoundedRect(QRectF(rect), radius, radius); p.setClipPath(clip)
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(rect.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(rect.x() + (rect.width()-scaled.width())//2, rect.y() + (rect.height()-scaled.height())//2, scaled)
        else:
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight()); a = QColor(self.accent); a.setAlpha(185)
            grad.setColorAt(0, a); grad.setColorAt(1, widget_palette_colors()["surface2"]); p.fillRect(rect, grad)
            icon = awesome_icon(self.icon_name, "#FFFFFF").pixmap(36, 36); p.setOpacity(.85); p.drawPixmap(rect.center().x()-18, rect.center().y()-18, icon)
        p.setClipping(False); p.setOpacity(1); p.setPen(QPen(widget_palette_colors()["border"], 1)); p.setBrush(Qt.BrushStyle.NoBrush); p.drawRoundedRect(rect, radius, radius); p.end()


class MusicWidget(BaseWidget):
    MIN_SIZE = QSize(270, 140); DEFAULT_SIZE = QSize(390, 205)

    def __init__(self, manager: "WidgetManager", key: str) -> None:
        super().__init__(manager, key)
        self.content.installEventFilter(self); self.player = None; self.audio_output = None; self.duration = 0
        root = QVBoxLayout(self.content); root.setContentsMargins(14,12,14,10); root.setSpacing(7)
        header = QHBoxLayout(); self.header_icon = QLabel(); self.header_icon.setFixedSize(15,15); self.header_title = QLabel("MUSIC PLAYER"); self.header_title.setObjectName("musicHeader"); self.header_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True); self.header_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
        header.addWidget(self.header_icon); header.addWidget(self.header_title); header.addStretch(); root.addLayout(header)
        body = QHBoxLayout(); body.setSpacing(11); self.cover = ImageTileWidget(self.accent, "fa6s.music"); self.cover.setFixedWidth(92); body.addWidget(self.cover)
        info = QVBoxLayout(); info.setSpacing(5); self.track_label = QLabel("No track selected"); self.track_label.setObjectName("trackTitle"); self.track_label.setWordWrap(True)
        self.track_subtitle = QLabel("Add local audio files to begin"); self.track_subtitle.setObjectName("trackMeta"); info.addWidget(self.track_label); info.addWidget(self.track_subtitle)
        self.progress = QSlider(Qt.Orientation.Horizontal); self.progress.setRange(0,0); self.progress.sliderMoved.connect(self.seek); info.addWidget(self.progress)
        controls = QHBoxLayout(); self.prev_button = QPushButton(""); self.play_button = QPushButton(""); self.next_button = QPushButton(""); self.add_button = QPushButton("")
        for button in (self.prev_button,self.play_button,self.next_button,self.add_button): button.setFixedSize(28,27)
        self.prev_button.clicked.connect(self.previous_track); self.play_button.clicked.connect(self.toggle_playback); self.next_button.clicked.connect(self.next_track); self.add_button.clicked.connect(self.choose_tracks)
        self.time_label = QLabel("0:00 / 0:00"); self.time_label.setObjectName("trackMeta"); self.volume = QSlider(Qt.Orientation.Horizontal); self.volume.setRange(0,100); self.volume.setValue(int(self.config.get("volume",70))); self.volume.setFixedWidth(70); self.volume.valueChanged.connect(self.set_volume)
        controls.addWidget(self.prev_button); controls.addWidget(self.play_button); controls.addWidget(self.next_button); controls.addWidget(self.add_button); controls.addStretch(); controls.addWidget(self.time_label); controls.addWidget(self.volume)
        info.addLayout(controls); body.addLayout(info,1); root.addLayout(body,1)
        self.initialize_player(); self.apply_icons(); self.apply_music_style(); self.reload_config()

    def settings_page(self) -> str: return "Music"

    def initialize_player(self) -> None:
        if QMediaPlayer is None or QAudioOutput is None: return
        try:
            self.audio_output = QAudioOutput(self); self.audio_output.setVolume(float(self.config.get("volume",70))/100.0)
            self.player = QMediaPlayer(self); self.player.setAudioOutput(self.audio_output); self.player.positionChanged.connect(self.position_changed); self.player.durationChanged.connect(self.duration_changed); self.player.playbackStateChanged.connect(self.playback_changed); self.player.mediaStatusChanged.connect(self.media_status_changed)
        except Exception: self.player = None; self.audio_output = None

    def apply_icons(self) -> None:
        super().apply_icons()
        if hasattr(self, "prev_button"):
            set_icon_button(self.prev_button,"fa6s.backward-step","⏮",12); set_icon_button(self.next_button,"fa6s.forward-step","⏭",12); set_icon_button(self.add_button,"fa6s.plus","+",12); self.update_play_icon()
            self.header_icon.setPixmap(awesome_icon("fa6s.music", self.accent.name()).pixmap(14,14))

    def update_play_icon(self) -> None:
        playing = bool(self.player and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        set_icon_button(self.play_button, "fa6s.pause" if playing else "fa6s.play", "Ⅱ" if playing else "▶", 12)

    def apply_music_style(self) -> None:
        c = widget_palette_colors()
        self.content.setStyleSheet(f"QLabel{{background:transparent;color:{c['text'].name()};}} QLabel#musicHeader{{color:{self.accent.name()};font-size:11px;font-weight:700;letter-spacing:1px;}} QLabel#trackTitle{{font-size:13px;font-weight:650;}} QLabel#trackMeta{{color:{c['muted'].name()};font-size:10px;}} QSlider::groove:horizontal{{height:4px;background:{c['control'].name(QColor.NameFormat.HexArgb)};border-radius:2px;}} QSlider::sub-page:horizontal{{background:{self.accent.name()};border-radius:2px;}} QSlider::handle:horizontal{{width:10px;margin:-3px 0;background:{self.accent.name()};border-radius:5px;}}")

    def reload_config(self) -> None:
        self.cover.accent = self.accent; self.cover.set_image(str(self.config.get("cover_image",""))); self.volume.setValue(int(self.config.get("volume",70)))
        playlist = self.config.get("playlist",[]); self.config["playlist"] = [str(x) for x in playlist if isinstance(x,str)]
        self.config["current_index"] = max(0,min(len(self.config["playlist"])-1,int(self.config.get("current_index",0)))) if self.config["playlist"] else 0; self.update_track_text()

    def playlist(self) -> list[str]: return list(self.config.get("playlist",[]))

    def update_track_text(self) -> None:
        tracks = self.playlist(); idx = int(self.config.get("current_index",0))
        if tracks and idx < len(tracks):
            self.track_label.setText(Path(tracks[idx]).stem); self.track_subtitle.setText(f"{idx+1} of {len(tracks)} · {Path(tracks[idx]).suffix.upper().lstrip('.')}")
        else: self.track_label.setText("No track selected"); self.track_subtitle.setText("Add local audio files to begin")

    def choose_tracks(self) -> None:
        files,_ = QFileDialog.getOpenFileNames(self,"Add music",str(Path.home()),"Audio files (*.mp3 *.wav *.m4a *.aac *.ogg *.flac)")
        if files: self.config["playlist"] = files; self.config["current_index"] = 0; STORE.save(); self.set_track(0,False)

    def set_track(self,index:int,autoplay:bool=True) -> None:
        tracks = self.playlist()
        if not tracks: return
        index %= len(tracks); self.config["current_index"] = index; STORE.save(); self.update_track_text()
        if self.player:
            self.player.setSource(QUrl.fromLocalFile(str(Path(tracks[index]).resolve())))
            if autoplay: self.player.play()

    def toggle_playback(self) -> None:
        if not self.playlist(): self.choose_tracks(); return
        if not self.player: QMessageBox.warning(None,APP_NAME,"Music playback needs the PySide6 Qt Multimedia components."); return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState: self.player.pause()
        elif self.player.source().isEmpty(): self.set_track(int(self.config.get("current_index",0)),True)
        else: self.player.play()

    def previous_track(self) -> None: self.set_track(int(self.config.get("current_index",0))-1,True)
    def next_track(self) -> None: self.set_track(int(self.config.get("current_index",0))+1,True)
    def set_volume(self,value:int) -> None:
        self.config["volume"] = int(value)
        if self.audio_output: self.audio_output.setVolume(value/100.0)
    def seek(self,value:int) -> None:
        if self.player: self.player.setPosition(value)
    def duration_changed(self,value:int) -> None: self.duration=max(0,int(value)); self.progress.setRange(0,self.duration); self.position_changed(self.player.position() if self.player else 0)
    def position_changed(self,value:int) -> None:
        if not self.progress.isSliderDown(): self.progress.setValue(int(value))
        fmt=lambda ms:f"{ms//60000}:{(ms//1000)%60:02d}"; self.time_label.setText(f"{fmt(int(value))} / {fmt(self.duration)}")
    def playback_changed(self,_state) -> None: self.update_play_icon()
    def media_status_changed(self,status) -> None:
        if self.player and status == QMediaPlayer.MediaStatus.EndOfMedia: self.next_track()

    def eventFilter(self,obj:QObject,event:QEvent) -> bool:
        if obj is self.content and event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseMove,QEvent.Type.MouseButtonRelease):
            try:
                if event.position().y() <= 40:
                    if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton: self.dragging=not self.config.get("locked",False); self.drag_offset=event.globalPosition().toPoint()-self.frameGeometry().topLeft(); return self.dragging
                    if event.type()==QEvent.Type.MouseMove and self.dragging: self.move(event.globalPosition().toPoint()-self.drag_offset); return True
                    if event.type()==QEvent.Type.MouseButtonRelease and self.dragging: self.dragging=False; self.save_geometry(); return True
            except Exception: pass
        return super().eventFilter(obj,event)

    def closeEvent(self,event) -> None:  # type: ignore[override]
        if self.player: self.player.stop()
        STORE.save(); super().closeEvent(event)


class GoalCountdownWidget(BaseWidget):
    MIN_SIZE = QSize(280,140); DEFAULT_SIZE = QSize(420,215)

    def __init__(self,manager:"WidgetManager",key:str) -> None:
        super().__init__(manager,key); self.content.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
        root=QHBoxLayout(self.content); root.setContentsMargins(14,13,14,11); root.setSpacing(13); self.image=ImageTileWidget(self.accent,"fa6s.flag-checkered"); self.image.setFixedWidth(105); root.addWidget(self.image)
        right=QVBoxLayout(); right.setSpacing(6); self.kicker=QLabel("GOAL COUNTDOWN"); self.kicker.setObjectName("goalKicker"); self.title_label=QLabel(); self.title_label.setObjectName("goalTitle"); self.title_label.setWordWrap(True); self.target_label=QLabel(); self.target_label.setObjectName("goalMeta"); right.addWidget(self.kicker); right.addWidget(self.title_label); right.addWidget(self.target_label)
        units=QHBoxLayout(); self.value_labels=[]; self.unit_labels=[]
        for unit in ("DAYS","HOURS","MIN","SEC"):
            box=QVBoxLayout(); box.setSpacing(0); value=QLabel("00"); value.setObjectName("goalValue"); value.setAlignment(Qt.AlignmentFlag.AlignCenter); label=QLabel(unit); label.setObjectName("goalUnit"); label.setAlignment(Qt.AlignmentFlag.AlignCenter); box.addWidget(value); box.addWidget(label); units.addLayout(box); self.value_labels.append(value); self.unit_labels.append(label)
        right.addLayout(units); right.addStretch(); root.addLayout(right,1); self.timer=QTimer(self); self.timer.setTimerType(Qt.TimerType.CoarseTimer); self.timer.timeout.connect(self.update_countdown); self.apply_goal_style(); self.reload_config()

    def settings_page(self) -> str: return "Goal"
    def apply_goal_style(self) -> None:
        c=widget_palette_colors(); self.content.setStyleSheet(f"QLabel{{background:transparent;color:{c['text'].name()};}} QLabel#goalKicker{{color:{self.accent.name()};font-size:11px;font-weight:700;letter-spacing:1px;}} QLabel#goalTitle{{font-size:14px;font-weight:650;}} QLabel#goalMeta,QLabel#goalUnit{{color:{c['muted'].name()};font-size:9px;}} QLabel#goalValue{{font-family:'Segoe UI Variable Display','Segoe UI';font-size:23px;font-weight:650;}}")
    def reload_config(self) -> None:
        self.image.accent=self.accent; self.image.set_image(str(self.config.get("image_path",""))); self.title_label.setText(str(self.config.get("title","My Goal"))); self.restart_timer(); self.update_countdown()
    def restart_timer(self) -> None: self.timer.start(1000 if self.config.get("show_seconds",True) else 60000)
    def target_datetime(self) -> dt.datetime:
        try:
            target=dt.datetime.fromisoformat(str(self.config.get("target",""))); return target if target.tzinfo else target.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        except Exception: return dt.datetime.now().astimezone()
    def update_countdown(self) -> None:
        target=self.target_datetime(); now=dt.datetime.now().astimezone(); seconds=max(0,int((target.astimezone()-now).total_seconds())); days,rem=divmod(seconds,86400); hours,rem=divmod(rem,3600); minutes,secs=divmod(rem,60)
        for label,value in zip(self.value_labels,(days,hours,minutes,secs)): label.setText(f"{value:02d}")
        show_seconds=bool(self.config.get("show_seconds",True)); self.value_labels[3].setVisible(show_seconds); self.unit_labels[3].setVisible(show_seconds); self.title_label.setText(str(self.config.get("completed_text","Goal reached")) if seconds<=0 else str(self.config.get("title","My Goal"))); self.target_label.setText(target.strftime("%d %b %Y · %I:%M %p"))
    def resizeEvent(self,event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self,"image"): self.image.setVisible(self.width()>=330)


class CalendarGridWidget(QWidget):
    daySelected = Signal(object)

    def __init__(self, accent: QColor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent); self.accent=accent; today=dt.date.today(); self.year=today.year; self.month=today.month; self.selected=today; self.todos=[]; self.cells=[]
        self.setMinimumHeight(145); self.setMouseTracking(True)

    def set_month(self, year:int, month:int) -> None:
        self.year,self.month=year,month; self.update()
    def set_todos(self,todos:list[dict[str,Any]]) -> None: self.todos=todos; self.update()

    def paintEvent(self,event) -> None:  # type: ignore[override]
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);c=widget_palette_colors();w=self.width()/7;header=20;h=(self.height()-header)/6
        p.setFont(QFont("Segoe UI",8,QFont.Weight.DemiBold));p.setPen(c['muted'])
        for col,name in enumerate(('MON','TUE','WED','THU','FRI','SAT','SUN')): p.drawText(QRectF(col*w,0,w,header),Qt.AlignmentFlag.AlignCenter,name)
        weeks=pycalendar.Calendar(firstweekday=0).monthdatescalendar(self.year,self.month)
        while len(weeks)<6: weeks.append([weeks[-1][-1]+dt.timedelta(days=i+1) for i in range(7)])
        self.cells=[];today=dt.date.today();task_dates={str(x.get('date','')) for x in self.todos if not x.get('done',False)}
        for row,week in enumerate(weeks[:6]):
            for col,day in enumerate(week):
                rect=QRectF(col*w,header+row*h,w,h);self.cells.append((rect,day));current=day.month==self.month
                if day==self.selected:
                    fill=QColor(self.accent);fill.setAlpha(65);p.setPen(Qt.PenStyle.NoPen);p.setBrush(fill);p.drawRoundedRect(rect.adjusted(3,2,-3,-2),6,6)
                if day==today:
                    p.setPen(QPen(self.accent,1.4));p.setBrush(Qt.BrushStyle.NoBrush);p.drawEllipse(rect.center(),min(w,h)*.28,min(w,h)*.28)
                p.setPen(c['text'] if current else c['muted']);p.setFont(QFont("Segoe UI",9,QFont.Weight.DemiBold if day==today else QFont.Weight.Normal));p.drawText(rect,Qt.AlignmentFlag.AlignCenter,str(day.day))
                if day.isoformat() in task_dates:
                    p.setPen(Qt.PenStyle.NoPen);p.setBrush(self.accent);p.drawEllipse(QPointF(rect.center().x(),rect.bottom()-4),2,2)
        p.end()

    def mouseReleaseEvent(self,event) -> None:  # type: ignore[override]
        if event.button()==Qt.MouseButton.LeftButton:
            point=event.position()
            for rect,day in self.cells:
                if rect.contains(point): self.selected=day;self.daySelected.emit(day);self.update();event.accept();return
        super().mouseReleaseEvent(event)


class CalendarWidget(BaseWidget):
    MIN_SIZE=QSize(280,230);DEFAULT_SIZE=QSize(380,340)
    def __init__(self,manager:"WidgetManager",key:str) -> None:
        super().__init__(manager,key);self.content.installEventFilter(self);today=dt.date.today();self.view_year=today.year;self.view_month=today.month;self.selected=today
        root=QVBoxLayout(self.content);root.setContentsMargins(13,11,13,10);root.setSpacing(6)
        header=QHBoxLayout();self.prev=QPushButton('');self.next=QPushButton('');self.month_label=QLabel();self.month_label.setObjectName('calendarMonth');self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter);self.add=QPushButton('')
        for b in (self.prev,self.next,self.add):b.setFixedSize(27,25)
        self.prev.clicked.connect(lambda:self.change_month(-1));self.next.clicked.connect(lambda:self.change_month(1));self.add.clicked.connect(self.add_todo)
        header.addWidget(self.prev);header.addWidget(self.month_label,1);header.addWidget(self.add);header.addWidget(self.next);root.addLayout(header)
        self.grid=CalendarGridWidget(self.accent);self.grid.daySelected.connect(self.select_day);root.addWidget(self.grid,1)
        self.todo_label=QLabel();self.todo_label.setObjectName('calendarTodos');self.todo_label.setWordWrap(True);root.addWidget(self.todo_label)
        self.manage=QPushButton('Manage to-do list');self.manage.clicked.connect(lambda:self.manager.open_settings('Calendar'));root.addWidget(self.manage)
        self.hour_timer=QTimer(self);self.hour_timer.setTimerType(Qt.TimerType.VeryCoarseTimer);self.hour_timer.setInterval(3600000);self.hour_timer.timeout.connect(self.refresh_today);self.hour_timer.start()
        self.apply_icons();self.apply_calendar_style();self.reload_config()

    def settings_page(self)->str:return 'Calendar'
    def apply_icons(self)->None:
        super().apply_icons()
        if hasattr(self,'prev'):set_icon_button(self.prev,'fa6s.chevron-left','‹',11);set_icon_button(self.next,'fa6s.chevron-right','›',11);set_icon_button(self.add,'fa6s.plus','+',11)
    def apply_calendar_style(self)->None:
        c=widget_palette_colors();self.content.setStyleSheet(f"QLabel{{background:transparent;color:{c['text'].name()};}} QLabel#calendarMonth{{font-size:14px;font-weight:700;color:{self.accent.name()};}} QLabel#calendarTodos{{color:{c['muted'].name()};font-size:10px;}}")
    def todos(self)->list[dict[str,Any]]:return list(self.config.get('todos',[]))
    def reload_config(self)->None:self.grid.accent=self.accent;self.grid.set_todos(self.todos());self.update_month();self.update_todos()
    def update_month(self)->None:self.month_label.setText(dt.date(self.view_year,self.view_month,1).strftime('%B %Y').upper());self.grid.set_month(self.view_year,self.view_month)
    def change_month(self,delta:int)->None:
        value=self.view_year*12+self.view_month-1+delta;self.view_year,self.view_month=divmod(value,12);self.view_month+=1;self.update_month()
    def select_day(self,day:dt.date)->None:self.selected=day;self.update_todos()
    def update_todos(self)->None:
        tasks=[x for x in self.todos() if str(x.get('date',''))==self.selected.isoformat() and (self.config.get('show_completed',True) or not x.get('done',False))]
        if tasks:self.todo_label.setText(self.selected.strftime('%d %b')+'  ·  '+'   '.join(('✓ ' if x.get('done') else '• ')+str(x.get('text','')) for x in tasks[:3]))
        else:self.todo_label.setText(self.selected.strftime('%d %b')+'  ·  No tasks')
    def add_todo(self)->None:
        text,ok=QInputDialog.getText(self,'Add to-do',f'Task for {self.selected.strftime("%d %b %Y")}:')
        if ok and text.strip():
            items=self.todos();items.append({'id':str(time.time_ns()),'text':text.strip(),'date':self.selected.isoformat(),'done':False});self.config['todos']=items;STORE.save();self.grid.set_todos(items);self.update_todos()
    def refresh_today(self)->None:self.grid.update()
    def eventFilter(self,obj:QObject,event:QEvent)->bool:
        if obj is self.content and event.type() in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseMove,QEvent.Type.MouseButtonRelease):
            try:
                if event.position().y()<=36:
                    if event.type()==QEvent.Type.MouseButtonPress and event.button()==Qt.MouseButton.LeftButton:self.dragging=not self.config.get('locked',False);self.drag_offset=event.globalPosition().toPoint()-self.frameGeometry().topLeft();return self.dragging
                    if event.type()==QEvent.Type.MouseMove and self.dragging:self.move(event.globalPosition().toPoint()-self.drag_offset);return True
                    if event.type()==QEvent.Type.MouseButtonRelease and self.dragging:self.dragging=False;self.save_geometry();return True
            except Exception:pass
        return super().eventFilter(obj,event)


BUILTIN_QUOTES=[
    ('Small steps every day create remarkable results.','Unknown'),('The future depends on what you do today.','Mahatma Gandhi'),('Focus on progress, not perfection.','Unknown'),('You are capable of more than you know.','Unknown'),('Discipline is choosing between what you want now and what you want most.','Abraham Lincoln'),('Start where you are. Use what you have. Do what you can.','Arthur Ashe'),('Success is the sum of small efforts repeated daily.','Robert Collier'),('Believe you can and you are halfway there.','Theodore Roosevelt')]


class QuoteWidget(BaseWidget):
    MIN_SIZE=QSize(220,98);DEFAULT_SIZE=QSize(230,105);supports_refresh=True
    def __init__(self,manager:"WidgetManager",key:str)->None:
        super().__init__(manager,key);self.content.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True);layout=QVBoxLayout(self.content);layout.setContentsMargins(14,11,14,10);layout.setSpacing(4);self.mark=QLabel('“');self.mark.setObjectName('quoteMark');self.quote=QLabel();self.quote.setObjectName('quoteText');self.quote.setWordWrap(True);self.author=QLabel();self.author.setObjectName('quoteAuthor');self.author.setAlignment(Qt.AlignmentFlag.AlignRight);layout.addWidget(self.mark);layout.addWidget(self.quote,1);layout.addWidget(self.author)
        self.timer=QTimer(self);self.timer.setTimerType(Qt.TimerType.VeryCoarseTimer);self.timer.timeout.connect(self.refresh);self.apply_quote_style();self.reload_config()
    def settings_page(self)->str:return 'Quotes'
    def quote_pool(self)->list[tuple[str,str]]:
        pool=list(BUILTIN_QUOTES) if self.config.get('use_builtin',True) else [];pool.extend((str(x),'Custom') for x in self.config.get('custom_quotes',[]) if str(x).strip());return pool or list(BUILTIN_QUOTES)
    def reload_config(self)->None:self.timer.start(max(1,int(self.config.get('interval_minutes',5)))*60000);self.show_quote()
    def show_quote(self)->None:
        pool=self.quote_pool();index=int(self.config.get('quote_index',0))%len(pool);text,author=pool[index];self.quote.setText(text);self.author.setText('— '+author)
    def refresh(self)->None:
        pool=self.quote_pool();self.config['quote_index']=(int(self.config.get('quote_index',0))+1)%len(pool);STORE.save();self.show_quote()
    def apply_quote_style(self)->None:
        c=widget_palette_colors();self.content.setStyleSheet(f"QLabel{{background:transparent;color:{c['text'].name()};}} QLabel#quoteMark{{color:{self.accent.name()};font-size:22px;font-weight:700;}} QLabel#quoteText{{font-size:11px;font-weight:600;}} QLabel#quoteAuthor{{color:{c['muted'].name()};font-size:9px;}}")


class NewsImage(QWidget):
    """Rounded, cover-cropped image surface with an offline-safe fallback."""

    def __init__(self, accent: QColor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent = accent
        self.source_pixmap = QPixmap()
        self.source_name = "NEWS"
        self.setMinimumHeight(112)
        self.setMaximumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_source(self, pixmap: Optional[QPixmap], source: str = "NEWS") -> None:
        self.source_pixmap = pixmap or QPixmap()
        self.source_name = (source or "NEWS").upper()
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1); radius = max(2, widget_corner_radius() - 3)
        clip = QPainterPath(); clip.addRoundedRect(QRectF(rect), radius, radius)
        p.setClipPath(clip)
        if not self.source_pixmap.isNull():
            scaled = self.source_pixmap.scaled(
                rect.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = rect.x() + (rect.width() - scaled.width()) // 2
            y = rect.y() + (rect.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            shade = QLinearGradient(0, rect.top(), 0, rect.bottom())
            shade.setColorAt(0, QColor(0, 0, 0, 0)); shade.setColorAt(1, QColor(0, 0, 0, 75))
            p.fillRect(rect, shade)
        else:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            start = QColor(self.accent); start.setAlpha(95)
            end = QColor("#253148" if widget_palette_colors()["surface"].lightness() < 145 else "#DCE9F8")
            gradient.setColorAt(0, start); gradient.setColorAt(1, end)
            p.fillRect(rect, gradient)
            is_offline = self.source_name == "OFFLINE"
            icon = awesome_icon("fa6s.wifi" if is_offline else "fa6s.image", "#FFFFFF")
            if not icon.isNull():
                pix = icon.pixmap(48, 48)
                p.setOpacity(.72); p.drawPixmap(rect.center().x() - 24, rect.center().y() - 29, pix); p.setOpacity(1)
                if is_offline:
                    p.setPen(QPen(QColor(255, 255, 255, 205), 4))
                    p.drawLine(rect.center().x() - 28, rect.center().y() - 31, rect.center().x() + 28, rect.center().y() + 25)
            else:
                p.setPen(QPen(QColor(255, 255, 255, 155), 2))
                p.drawRoundedRect(rect.center().x() - 27, rect.center().y() - 28, 54, 40, 7, 7)
                p.drawEllipse(rect.center().x() - 16, rect.center().y() - 18, 8, 8)
                p.drawLine(rect.center().x() - 22, rect.center().y() + 5, rect.center().x() - 7, rect.center().y() - 7)
                p.drawLine(rect.center().x() - 7, rect.center().y() - 7, rect.center().x() + 20, rect.center().y() + 9)
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, radius, radius)
        p.end()


class NewsSlide(QFrame):
    activated = Signal()
    slideRequested = Signal(int)

    def __init__(self, accent: QColor, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.accent = accent
        self.item: dict[str, str] = {}
        self.setObjectName("newsSlide")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self); layout.setContentsMargins(5, 5, 5, 4); layout.setSpacing(8)
        self.image = NewsImage(accent)
        layout.addWidget(self.image, 1)
        self.title = QLabel("Loading headlines…")
        self.title.setObjectName("slideHeadline"); self.title.setWordWrap(True)
        self.title.setMinimumHeight(36); self.title.setMaximumHeight(70)
        self.meta = QLabel("NEWS")
        self.meta.setObjectName("slideMeta")
        self.hint = QLabel("Open article")
        self.hint.setObjectName("slideHint")
        line = QHBoxLayout(); line.addWidget(self.meta); line.addStretch(); line.addWidget(self.hint)
        layout.addWidget(self.title); layout.addLayout(line)
        for child in (self.image, self.title, self.meta, self.hint):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.apply_style()

    def set_item(self, item: dict[str, str], pixmap: Optional[QPixmap] = None) -> None:
        self.item = item
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title.setText(item.get("title", "Untitled"))
        self.meta.setText(f"{item.get('source', 'News')}  ·  {relative_time(item.get('published', ''))}")
        self.hint.setText("Open article  ↗")
        self.image.set_source(pixmap, item.get("source", "News"))

    def show_offline(self) -> None:
        self.item = {}
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.title.setText("You're not connected")
        self.meta.setText("Connect to the internet, then refresh")
        self.hint.setText("")
        self.image.set_source(None, "OFFLINE")

    def apply_style(self) -> None:
        c = widget_palette_colors(); dark = c["surface"].lightness() < 145
        hover = "rgba(255,255,255,0.055)" if dark else "rgba(20,30,50,0.045)"
        self.setStyleSheet(f"""
            QFrame#newsSlide {{ background: transparent; border-radius: 12px; }}
            QFrame#newsSlide:hover {{ background: {hover}; }}
            QLabel {{ background: transparent; color: {c['text'].name()}; border: none; }}
            QLabel#slideHeadline {{ font-size: 14px; font-weight: 650; }}
            QLabel#slideMeta, QLabel#slideHint {{ color: {c['muted'].name()}; font-size: 10px; }}
        """)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self.item.get("link"):
            self.activated.emit(); event.accept(); return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        delta = -1 if event.angleDelta().y() > 0 else 1
        self.slideRequested.emit(delta)
        event.accept()


def relative_time(value: str) -> str:
    try:
        published = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=dt.timezone.utc)
        seconds = max(0, int((dt.datetime.now(dt.timezone.utc) - published.astimezone(dt.timezone.utc)).total_seconds()))
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        if seconds < 604800:
            return f"{seconds // 86400}d ago"
        return published.strftime("%d %b")
    except Exception:
        return "recently"


NEWS_FEEDS = {
    "Google News": {
        "Top stories": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
        "World": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-IN&gl=IN&ceid=IN:en",
        "Technology": "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-IN&gl=IN&ceid=IN:en",
        "Business": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-IN&gl=IN&ceid=IN:en",
        "Science": "https://news.google.com/rss/headlines/section/topic/SCIENCE?hl=en-IN&gl=IN&ceid=IN:en",
        "Sports": "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-IN&gl=IN&ceid=IN:en",
    },
    "BBC News": {
        "Top stories": "https://feeds.bbci.co.uk/news/rss.xml",
        "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "Science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        "Sports": "https://feeds.bbci.co.uk/sport/rss.xml",
    },
}


def news_feed_url(config: dict[str, Any]) -> str:
    source = config.get("source", "Google News")
    if source == "Custom RSS":
        return str(config.get("custom_url", "")).strip()
    feeds = NEWS_FEEDS.get(source, NEWS_FEEDS["Google News"])
    return feeds.get(config.get("category", "Top stories"), next(iter(feeds.values())))


def node_text(node: ET.Element, names: list[str]) -> str:
    for child in list(node):
        tag = child.tag.split("}")[-1].lower()
        if tag in names and child.text:
            return child.text.strip()
    return ""


def extract_news(xml_data: bytes, default_source: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_data)
    candidates = root.findall(".//item")
    if not candidates:
        candidates = [n for n in root.iter() if n.tag.split("}")[-1].lower() == "entry"]
    items: list[dict[str, str]] = []
    for node in candidates[:50]:
        title = html.unescape(re.sub(r"<[^>]+>", "", node_text(node, ["title"]))).strip()
        link = node_text(node, ["link"])
        if not link:
            for child in list(node):
                if child.tag.split("}")[-1].lower() == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        published_raw = node_text(node, ["pubdate", "published", "updated", "date"])
        published = dt.datetime.now(dt.timezone.utc)
        if published_raw:
            try:
                parsed = email.utils.parsedate_to_datetime(published_raw)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=dt.timezone.utc)
                published = parsed.astimezone(dt.timezone.utc)
            except Exception:
                try:
                    parsed = dt.datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
                    published = parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
                except Exception:
                    pass
        source = node_text(node, ["source", "creator", "author"]) or default_source
        source_url = ""
        for child in list(node):
            if child.tag.split("}")[-1].lower() == "source":
                source_url = child.attrib.get("url", "")
                break
        # Google News often appends " - Source" to the title.
        if default_source == "Google News" and " - " in title:
            possible_title, possible_source = title.rsplit(" - ", 1)
            if possible_source and len(possible_source) < 55:
                title, source = possible_title, possible_source
        thumb = ""
        description = node_text(node, ["description", "summary", "content"])
        for child in node.iter():
            tag = child.tag.split("}")[-1].lower()
            url = child.attrib.get("url", "")
            medium = child.attrib.get("medium", "")
            mime = child.attrib.get("type", "")
            if url and (tag in ("thumbnail", "content", "enclosure") or medium == "image") and ("image" in mime or tag != "enclosure"):
                thumb = url
                break
        if not thumb and description:
            match = re.search(r"<img[^>]+src=[\"']([^\"']+)", description, re.I)
            if match:
                thumb = html.unescape(match.group(1))
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "source": re.sub(r"<[^>]+>", "", source).strip() or default_source,
                "published": published.astimezone(dt.timezone.utc).isoformat(),
                "thumbnail": thumb,
                "source_url": source_url,
            })
    return items[:30]


GOOGLE_NEWS_DECODE_LOCK = threading.Lock()

ARTICLE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


class ArticleMetadataParser(HTMLParser):
    """Small dependency-free parser for publisher image metadata."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[int, str]] = []
        self.canonical = ""
        self._json_depth = 0
        self._json_parts: list[str] = []
        self.json_blocks: list[str] = []

    def add_srcset(self, value: str, priority: int) -> None:
        entries = [part.strip().split()[0] for part in value.split(",") if part.strip()]
        # srcset is normally ordered from small to large; prefer the largest.
        for offset, url in enumerate(reversed(entries)):
            self.images.append((priority + offset, url))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        values = {str(key).lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "meta":
            key = (values.get("property") or values.get("name") or values.get("itemprop") or "").lower()
            value = values.get("content", "").strip()
            priorities = {
                "og:image": 0, "og:image:url": 0, "og:image:secure_url": 0,
                "twitter:image": 1, "twitter:image:src": 1,
                "image": 2, "thumbnailurl": 3,
            }
            if value and key in priorities:
                self.images.append((priorities[key], value))
        elif tag == "link":
            rel = values.get("rel", "").lower().split()
            href = values.get("href", "").strip()
            if "canonical" in rel and href:
                self.canonical = href
            if href and ("image_src" in rel or ("preload" in rel and values.get("as", "").lower() == "image")):
                self.images.append((4, href))
        elif tag == "img":
            try:
                width = int(re.sub(r"\D", "", values.get("width", "0")) or 0)
                height = int(re.sub(r"\D", "", values.get("height", "0")) or 0)
            except ValueError:
                width = height = 0
            marker = " ".join((values.get("class", ""), values.get("id", ""), values.get("itemprop", ""), values.get("alt", ""))).lower()
            rejected = any(word in marker for word in ("favicon", "avatar", "author-photo", "site-logo", "brand-logo", "advertisement", "tracking-pixel"))
            if not rejected:
                priority = 8 if any(word in marker for word in ("hero", "lead", "featured", "article-image", "story-image")) else (11 if width >= 500 and height >= 250 else 18)
                for attribute in ("data-original", "data-lazy-src", "data-src", "src"):
                    src = values.get(attribute, "").strip()
                    if src:
                        self.images.append((priority, src))
                for attribute in ("data-srcset", "srcset"):
                    if values.get(attribute):
                        self.add_srcset(values[attribute], priority)
        elif tag == "source":
            for attribute in ("data-srcset", "srcset"):
                if values.get(attribute):
                    self.add_srcset(values[attribute], 15)
        elif tag == "script" and "ld+json" in values.get("type", "").lower():
            self._json_depth += 1
            self._json_parts = []

    def handle_data(self, data: str) -> None:
        if self._json_depth:
            self._json_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._json_depth:
            value = "".join(self._json_parts).strip()
            if value:
                self.json_blocks.append(value)
            self._json_depth = 0
            self._json_parts = []


def _json_image_candidates(value: Any, output: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            low = str(key).lower()
            if low in ("image", "imageurl", "thumbnailurl", "contenturl"):
                if isinstance(item, str):
                    output.append(item)
                elif isinstance(item, dict):
                    for url_key in ("url", "contentUrl", "thumbnailUrl"):
                        if isinstance(item.get(url_key), str):
                            output.append(item[url_key])
                elif isinstance(item, list):
                    for child in item:
                        if isinstance(child, str):
                            output.append(child)
                        else:
                            _json_image_candidates(child, output)
            elif isinstance(item, (dict, list)):
                _json_image_candidates(item, output)
    elif isinstance(value, list):
        for item in value:
            _json_image_candidates(item, output)


def _usable_image_url(value: str, base_url: str) -> str:
    value = html.unescape(value.strip()).replace("\\/", "/")
    if not value or value.startswith(("data:", "blob:")):
        return ""
    url = urllib.parse.urljoin(base_url, value)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return ""
    low_path = parsed.path.lower()
    basename = low_path.rsplit("/", 1)[-1]
    if low_path.endswith((".svg", ".gif")) or any(token in basename for token in ("favicon", "spacer", "pixel", "1x1", "sprite", "site-logo", "brand-logo", "avatar", "addndtv", "advert", "promo", "web.png")):
        return ""
    if basename.startswith("logo") or "-logo." in basename or "_logo." in basename:
        return ""
    if "gstatic.com/gnews/logo" in url.lower() or "google_news_" in url.lower():
        return ""
    size_match = re.search(r"(?:[?&=_-]|\b)w(?:idth)?[=_-]?(\d{1,4})(?:\D|$)", url.lower())
    if size_match and int(size_match.group(1)) < 180:
        return ""
    return url


def extract_article_metadata(page: str, base_url: str) -> dict[str, Any]:
    parser = ArticleMetadataParser()
    try:
        parser.feed(page); parser.close()
    except Exception:
        pass
    candidates = sorted(parser.images, key=lambda item: item[0])
    json_images: list[str] = []
    for block in parser.json_blocks:
        try:
            _json_image_candidates(json.loads(block), json_images)
        except Exception:
            continue
    candidates.extend((6, value) for value in json_images)
    # Last-resort CSS background images are common on modern article pages.
    for match in re.finditer(r"(?:background-image\s*:\s*url|url)\(\s*['\"]?([^'\")]+)", page, re.I):
        candidates.append((24, match.group(1)))
    seen: set[str] = set(); image_urls: list[str] = []
    for _priority, value in sorted(candidates, key=lambda item: item[0]):
        candidate = _usable_image_url(value, base_url)
        if candidate and candidate not in seen:
            seen.add(candidate); image_urls.append(candidate)
            if len(image_urls) >= 12:
                break
    canonical = _usable_image_url(parser.canonical, base_url) if parser.canonical else base_url
    return {
        "article_url": canonical or base_url,
        "image_url": image_urls[0] if image_urls else "",
        "image_urls": image_urls,
    }


def google_news_search_images(title: str) -> list[str]:
    """Find Google's cached story thumbnail when a publisher blocks hotlinking."""
    if not title.strip():
        return []
    try:
        query = urllib.parse.urlencode({"q": title, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"})
        request = urllib.request.Request(
            "https://news.google.com/search?" + query,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
        )
        with urllib.request.urlopen(request, timeout=16) as response:
            page = response.read(3_000_000).decode(response.headers.get_content_charset() or "utf-8", "replace")
        needle = title[:100].lower(); lower = page.lower(); positions: list[int] = []
        start = 0
        while True:
            found = lower.find(needle, start)
            if found < 0:
                break
            positions.append(found); start = found + len(needle)
        output: list[str] = []
        for position in reversed(positions):
            window = page[max(0, position - 1200):position + 5000]
            for path in re.findall(r'["\'](/attachments/[A-Za-z0-9_-]+)', window):
                url = "https://news.google.com" + path
                if url not in output:
                    output.append(url)
        return output[:6]
    except Exception:
        return []


def reader_fallback_images(article_url: str) -> list[str]:
    """Use a text-mode reader only when a publisher blocks direct metadata access."""
    if not _safe_public_http_url(article_url):
        return []
    try:
        target = "https://r.jina.ai/" + article_url
        request = urllib.request.Request(target, headers={"User-Agent": "OS-Widgets/1.2", "Accept": "text/plain"})
        with urllib.request.urlopen(request, timeout=18) as response:
            page = response.read(1_500_000).decode(response.headers.get_content_charset() or "utf-8", "replace")
        values = re.findall(r"!\[[^\]]*\]\((https?://[^\s\)]+)", page, re.I)
        output: list[str] = []
        for value in values:
            candidate = _usable_image_url(value, article_url)
            if candidate and candidate not in output:
                output.append(candidate)
            if len(output) >= 30:
                break
        def resolution_score(url: str) -> int:
            match = re.search(r"(?:width=|downsize=)(\d{2,4})", url, re.I)
            if match:
                return int(match.group(1))
            match = re.search(r"(\d{3,4})x(\d{3,4})", url, re.I)
            return int(match.group(1)) if match else 900
        return sorted(output, key=resolution_score, reverse=True)[:12]
    except Exception:
        return []


def _safe_public_http_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        host = parsed.hostname.lower().strip(".")
        if host in ("localhost", "localhost.localdomain") or host.endswith(".local"):
            return False
        try:
            address = ipaddress.ip_address(host)
            if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def _fetch_web_page(
    url: str, *, data: Optional[bytes] = None,
    content_type: str = "", max_bytes: int = 2_500_000,
) -> tuple[str, str]:
    if not _safe_public_http_url(url):
        raise ValueError("Unsafe or invalid article URL")
    headers = {
        "User-Agent": ARTICLE_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.8",
        "Cache-Control": "no-cache",
    }
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(request, timeout=12) as response:
        final_url = response.geturl()
        mime = response.headers.get_content_type().lower()
        if mime not in ("text/html", "application/xhtml+xml", "application/json", "text/plain"):
            raise ValueError(f"Unsupported article content type: {mime}")
        raw = response.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raw = raw[:max_bytes]
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, "replace"), final_url


def decode_google_news_article_url(source_url: str) -> str:
    """Resolve a Google News RSS wrapper to the publisher's real article URL."""
    parsed = urllib.parse.urlparse(source_url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname != "news.google.com" or len(parts) < 2 or parts[-2] not in ("articles", "read"):
        return source_url
    token = parts[-1]
    # Older Google News IDs contain the URL directly in a protobuf string.
    try:
        raw = base64.urlsafe_b64decode(token + "===")
        offset = 3 if raw.startswith(b"\x08\x13\x22") else 0
        length = 0; shift = 0
        while offset < len(raw):
            byte = raw[offset]; offset += 1
            length |= (byte & 0x7F) << shift
            if byte < 0x80:
                break
            shift += 7
        candidate = raw[offset:offset + length].decode("utf-8", "ignore")
        if candidate.startswith(("http://", "https://")):
            return candidate
    except Exception:
        pass
    # Current IDs require a short signed Google batchexecute request.
    probe_url = "https://news.google.com/articles/" + urllib.parse.quote(token, safe="-_")
    page, _ = _fetch_web_page(probe_url, max_bytes=2_500_000)
    signature = re.search(r'data-n-a-sg=["\']([^"\']+)', page)
    timestamp = re.search(r'data-n-a-ts=["\']([^"\']+)', page)
    if not signature or not timestamp:
        return source_url
    inner = (
        f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
        f'null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{token}",{timestamp.group(1)},"{signature.group(1)}"]'
    )
    payload = json.dumps([[['Fbv4je', inner]]], separators=(",", ":"))
    body = ("f.req=" + urllib.parse.quote(payload, safe="")).encode("utf-8")
    response, _ = _fetch_web_page(
        "https://news.google.com/_/DotsSplashUi/data/batchexecute",
        data=body, content_type="application/x-www-form-urlencoded;charset=UTF-8",
        max_bytes=300_000,
    )
    try:
        packet = json.loads(response.split("\n\n", 1)[1])
        for row in packet:
            if isinstance(row, list) and len(row) > 2 and row[1] == "Fbv4je" and isinstance(row[2], str):
                decoded = json.loads(row[2])
                if len(decoded) > 1 and _safe_public_http_url(decoded[1]):
                    return decoded[1]
    except Exception:
        pass
    return source_url


class ArticleLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_href = ""; self.current_text: list[str] = []; self.current_images: list[str] = []
        self.links: list[tuple[str, str, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "a":
            self.current_href = values.get("href", ""); self.current_text = []; self.current_images = []
        elif tag.lower() == "img" and self.current_href:
            if values.get("alt"):
                self.current_text.append(values["alt"])
            for attribute in ("data-original", "data-lazy-src", "data-src", "src"):
                if values.get(attribute):
                    self.current_images.append(values[attribute])
            srcset = values.get("data-srcset") or values.get("srcset") or ""
            if srcset:
                choices = [part.strip().split()[0] for part in srcset.split(",") if part.strip()]
                if choices:
                    self.current_images.append(choices[-1])

    def handle_data(self, data: str) -> None:
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.current_href:
            text = re.sub(r"\s+", " ", " ".join(self.current_text)).strip()
            if text:
                self.links.append((self.current_href, text, list(self.current_images)))
            self.current_href = ""; self.current_text = []; self.current_images = []


def discover_article_from_source(title: str, source_url: str) -> tuple[str, str]:
    """Match a story and its card image on the publisher homepage."""
    if not _safe_public_http_url(source_url):
        return "", ""
    try:
        page, final_url = _fetch_web_page(source_url, max_bytes=2_500_000)
        parser = ArticleLinkParser(); parser.feed(page); parser.close()
        stop = {"the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "at", "from", "is", "are", "live", "news"}
        wanted = {word for word in re.findall(r"[a-z0-9]+", title.lower()) if len(word) > 2 and word not in stop}
        best_url = ""; best_image = ""; best_score = 0.0
        for href, text, images in parser.links:
            words = {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2 and word not in stop}
            common = len(wanted & words)
            if common < 3:
                continue
            score = common / max(1, min(len(wanted), len(words)))
            candidate = urllib.parse.urljoin(final_url, html.unescape(href))
            if score > best_score and _safe_public_http_url(candidate):
                best_score = score; best_url = candidate; best_image = ""
                for image in reversed(images):
                    usable = _usable_image_url(image, final_url)
                    if usable:
                        best_image = usable; break
        return (best_url, best_image) if best_score >= .42 else ("", "")
    except Exception:
        return "", ""


def resolve_article_metadata(item: dict[str, str]) -> dict[str, Any]:
    """Worker-thread job: resolve publisher URL, then read its real hero image."""
    original = str(item.get("publisher_url") or item.get("link") or "").strip()
    if not _safe_public_http_url(original):
        return {"article_url": original, "image_url": ""}
    google_wrapped = urllib.parse.urlparse(original).hostname == "news.google.com"
    try:
        if google_wrapped:
            with GOOGLE_NEWS_DECODE_LOCK:
                article_url = decode_google_news_article_url(original)
        else:
            article_url = original
    except Exception:
        article_url = original
    if not _safe_public_http_url(article_url):
        article_url = original
    # If Google rate-limits redirect decoding, match the headline on the
    # publisher homepage instead. Never use Google's own logo/interstitial as
    # article imagery.
    fallback_image = ""
    if urllib.parse.urlparse(article_url).hostname == "news.google.com":
        discovered_url, fallback_image = discover_article_from_source(str(item.get("title", "")), str(item.get("source_url", "")))
        if discovered_url:
            article_url = discovered_url
        else:
            images = google_news_search_images(str(item.get("title", ""))) if google_wrapped else []
            return {"article_url": original, "image_url": images[0] if images else "", "image_urls": images}
    try:
        page, final_url = _fetch_web_page(article_url)
        result = extract_article_metadata(page, final_url)
        if not _safe_public_http_url(result.get("article_url", "")):
            result["article_url"] = final_url
        if fallback_image and fallback_image not in result.get("image_urls", []):
            result.setdefault("image_urls", []).append(fallback_image)
            if not result.get("image_url"):
                result["image_url"] = fallback_image
        if not result.get("image_urls") and google_wrapped:
            cached_images = google_news_search_images(str(item.get("title", "")))
            if cached_images:
                result["image_urls"] = cached_images; result["image_url"] = cached_images[0]
        if item.get("allow_reader_fallback", True) and not result.get("image_urls"):
            reader_images = reader_fallback_images(article_url)
            if reader_images:
                result["image_urls"] = reader_images; result["image_url"] = reader_images[0]
        return result
    except Exception:
        images = [fallback_image] if fallback_image else []
        if google_wrapped:
            images.extend(url for url in google_news_search_images(str(item.get("title", ""))) if url not in images)
        if item.get("allow_reader_fallback", True) and not images:
            images.extend(url for url in reader_fallback_images(article_url) if url not in images)
        return {"article_url": article_url, "image_url": images[0] if images else "", "image_urls": images}


class ArticleMetadataBridge(QObject):
    resolved = Signal(int, int, object)


class DiagnosticsBridge(QObject):
    completed = Signal(object)


class DiagnosticRow(QFrame):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("diagnosticRow")
        layout = QHBoxLayout(self); layout.setContentsMargins(12, 9, 12, 9); layout.setSpacing(10)
        self.icon_label = QLabel(); self.icon_label.setFixedSize(22, 22)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QVBoxLayout(); text.setSpacing(1)
        self.title_label = QLabel(title); self.title_label.setStyleSheet("font-weight: 600;")
        self.detail_label = QLabel("Not tested")
        self.detail_label.setObjectName("muted"); self.detail_label.setWordWrap(True)
        text.addWidget(self.title_label); text.addWidget(self.detail_label)
        layout.addWidget(self.icon_label); layout.addLayout(text, 1)
        c = palette_colors(); raised = "#252A36" if resolved_dark() else "#FFFFFF"
        self.setStyleSheet(f"""
            QFrame#diagnosticRow {{ background: {raised}; border: 1px solid {c['border'].name(QColor.NameFormat.HexArgb)}; border-radius: 9px; }}
            QLabel {{ background: transparent; color: {c['text'].name()}; border: none; }}
            QLabel#muted {{ color: {c['muted'].name()}; font-size: 10px; }}
        """)
        self.set_status("pending", "Not tested")

    def set_status(self, status: str, detail: str) -> None:
        styles = {
            "pass": ("fa6s.circle-check", "#42D3A5"),
            "warn": ("fa6s.triangle-exclamation", "#FFB547"),
            "fail": ("fa6s.circle-xmark", "#FF718B"),
            "info": ("fa6s.circle-info", "#58A6FF"),
            "pending": ("fa6s.ellipsis", palette_colors()["muted"].name()),
        }
        icon_name, color = styles.get(status, styles["info"])
        icon = awesome_icon(icon_name, color)
        self.icon_label.setPixmap(icon.pixmap(18, 18) if not icon.isNull() else QPixmap())
        self.detail_label.setText(detail)


def run_windows_diagnostics(
    dpi_info: list[dict[str, Any]], tray_available: bool,
    widget_info: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """Background release-readiness checks; never mutates user configuration."""
    result: dict[str, dict[str, str]] = {}
    if IS_WINDOWS:
        release = platform.release(); version = platform.version()
        result["platform"] = {"status": "pass", "detail": f"Windows {release} · build {version}"}
    else:
        result["platform"] = {"status": "warn", "detail": f"Running on {platform.system()}; final native checks require Windows 10/11."}

    # GPU PDH counter availability and one real formatted sample.
    if IS_WINDOWS:
        gpu = GPUPerformanceMonitor()
        try:
            gpu.initialize(); time.sleep(0.30)
            value = gpu.percent()
            if value is None:
                result["gpu"] = {"status": "warn", "detail": "Windows GPU Engine PDH counters are unavailable on this driver."}
            else:
                result["gpu"] = {"status": "pass", "detail": f"GPU Engine PDH counter returned {value:.1f}%."}
        except Exception as exc:
            result["gpu"] = {"status": "fail", "detail": f"GPU counter test failed: {exc}"}
        finally:
            gpu.close()
    else:
        result["gpu"] = {"status": "info", "detail": "GPU PDH counters are Windows-only."}

    try:
        volumes = SystemMonitor().disk_partitions()
        if volumes:
            detail = " · ".join(f"{item['label']} {float(item['percent']):.1f}% used ({format_storage(float(item['free']))} free)" for item in volumes)
            source = "Windows volume API" if IS_WINDOWS else str(volumes[0].get("source","system storage API"))
            result["disks"] = {"status": "pass", "detail": f"Detected {len(volumes)} readable partition(s) with {source}: {detail}"}
        else:
            result["disks"] = {"status": "warn", "detail": "No readable storage partitions were detected."}
    except Exception as exc:
        result["disks"] = {"status": "fail", "detail": f"Partition scan failed: {exc}"}
    try:
        battery = SystemMonitor().battery_status()
        if battery:
            state = "plugged in" if battery["plugged"] else "running on battery"
            result["battery"] = {"status": "pass", "detail": f"Battery detected: {float(battery['percent']):.0f}% · {state}."}
        else:
            result["battery"] = {"status": "info", "detail": "No battery detected; desktop systems correctly display the no-battery state."}
    except Exception as exc:
        result["battery"] = {"status": "fail", "detail": f"Battery detection failed: {exc}"}

    # Per-user startup registration should match the saved preference.
    if IS_WINDOWS:
        expected = bool(STORE.data["general"].get("startup", False))
        command = ""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
            try:
                command, _ = winreg.QueryValueEx(key, APP_NAME)
            except FileNotFoundError:
                command = ""
            winreg.CloseKey(key)
            if expected and command:
                result["startup"] = {"status": "pass", "detail": f"Startup entry is registered for the current user: {command}"}
            elif expected and not command:
                result["startup"] = {"status": "fail", "detail": "Startup is enabled in Settings but the Windows Run entry is missing."}
            elif not expected and command:
                result["startup"] = {"status": "warn", "detail": "A Windows Run entry exists although startup is disabled in Settings."}
            else:
                result["startup"] = {"status": "pass", "detail": "Startup is disabled and no stale Windows Run entry exists."}
        except Exception as exc:
            result["startup"] = {"status": "fail", "detail": f"Could not inspect HKCU startup registration: {exc}"}
    else:
        result["startup"] = {"status": "info", "detail": "Windows startup registry test skipped on this platform."}

    # Explorer desktop host discovery is required for gadget-like Z ordering.
    if IS_WINDOWS:
        host = windows_desktop_host()
        try:
            user32 = ctypes.windll.user32
            user32.GetWindow.restype = ctypes.c_void_p
            valid = bool(host and user32.IsWindow(ctypes.c_void_p(host)))
            z_order_ok = True; tool_style_ok = True
            checked = 0
            for item in widget_info:
                hwnd = int(item.get("hwnd", 0))
                if not hwnd or not user32.IsWindow(ctypes.c_void_p(hwnd)):
                    continue
                checked += 1
                get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
                get_style.restype = ctypes.c_longlong
                ex_style = int(get_style(ctypes.c_void_p(hwnd), -20))
                tool_style_ok = tool_style_ok and bool(ex_style & 0x00000080)  # WS_EX_TOOLWINDOW
                if not item.get("always_top", False) and valid:
                    cursor = hwnd; found_host = False
                    for _ in range(512):
                        cursor = int(user32.GetWindow(ctypes.c_void_p(cursor), 2) or 0)  # GW_HWNDNEXT: below
                        if not cursor:
                            break
                        if cursor == host:
                            found_host = True; break
                    z_order_ok = z_order_ok and found_host
            passed = valid and tool_style_ok and z_order_ok
            details = f"Explorer host HWND 0x{host:X}; checked {checked} widget windows."
            if not tool_style_ok:
                details += " A widget is missing WS_EX_TOOLWINDOW."
            if not z_order_ok:
                details += " A desktop-level widget is not above the Explorer host."
        except Exception as exc:
            passed = False; details = f"Desktop Z-order inspection failed: {exc}"
        result["desktop"] = {"status": "pass" if passed else "fail", "detail": details}
    else:
        result["desktop"] = {"status": "info", "detail": "Native Explorer Z-order test skipped on this platform."}

    ratios = [float(item.get("ratio", 1.0)) for item in dpi_info] or [1.0]
    monitors = ", ".join(
        f"{item.get('name', 'Display')}: {float(item.get('dpi', 96)):.0f} DPI / {float(item.get('ratio', 1)):.2f}×"
        for item in dpi_info
    ) or "No display information"
    awareness_ok = True
    if IS_WINDOWS:
        try:
            user32 = ctypes.windll.user32
            user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
            user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
            awareness = user32.GetAwarenessFromDpiAwarenessContext(user32.GetThreadDpiAwarenessContext())
            awareness_ok = int(awareness) == 2  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            awareness_ok = False
    result["dpi"] = {
        "status": "pass" if awareness_ok else "warn",
        "detail": ("Per-monitor DPI awareness active. " if awareness_ok else "Per-monitor DPI awareness could not be confirmed. ")
        + monitors + (" · mixed-DPI layout detected" if len({round(v, 2) for v in ratios}) > 1 else ""),
    }

    try:
        temperature, provider = SystemMonitor.temperature_diagnostic()
        if temperature is None:
            result["temperature"] = {"status": "warn", "detail": f"No CPU temperature value was available. {provider}."}
        else:
            result["temperature"] = {"status": "pass", "detail": f"{provider} returned {temperature:.1f}°C."}
    except Exception as exc:
        result["temperature"] = {"status": "fail", "detail": f"Temperature provider test failed: {exc}"}

    result["notifications"] = {
        "status": "pass" if tray_available else "warn",
        "detail": "System-tray notifications are available; high-usage popup windows do not depend on the tray." if tray_available else "System tray is unavailable, but high-usage popup windows will still work.",
    }
    sound_cfg = STORE.data["widgets"]["cpu"]
    sound_path = Path(str(sound_cfg.get("alert_sound_path", ""))).expanduser()
    if not sound_cfg.get("alert_sound_enabled", False):
        result["audio"] = {"status": "info", "detail": "Custom alert ring is disabled."}
    elif not sound_path.is_file():
        result["audio"] = {"status": "fail", "detail": f"Configured alert sound does not exist: {sound_path}"}
    elif QMediaPlayer is not None and QAudioOutput is not None:
        result["audio"] = {"status": "pass", "detail": f"Qt Multimedia is available for {sound_path.suffix.upper()} playback."}
    elif IS_WINDOWS and sound_path.suffix.lower() == ".wav":
        result["audio"] = {"status": "pass", "detail": "Windows WAV fallback is available."}
    else:
        result["audio"] = {"status": "fail", "detail": "No compatible audio backend is available for the selected file."}

    test_file = app_data_dir() / ".diagnostic-write-test"
    try:
        test_file.write_text("ok", encoding="utf-8"); test_file.unlink(missing_ok=True)
        result["storage"] = {"status": "pass", "detail": f"Settings and cache folder is writable: {app_data_dir()}"}
    except OSError as exc:
        result["storage"] = {"status": "fail", "detail": f"Local data folder is not writable: {exc}"}

    pyside_version = "unknown"
    try:
        import PySide6
        pyside_version = getattr(PySide6, "__version__", "unknown")
    except Exception:
        pass
    result["dependencies"] = {
        "status": "pass" if psutil is not None and qta is not None else "warn",
        "detail": f"PySide6 {pyside_version} · psutil {'installed' if psutil else 'missing'} · qtawesome {'installed' if qta else 'missing'}",
    }
    try:
        process=psutil.Process(os.getpid()) if psutil else None; rss=process.memory_info().rss/(1024**2) if process else 0; threads=process.num_threads() if process else 0
        result["footprint"]={"status":"pass" if process else "warn","detail":f"Current process: {rss:.1f} MB resident memory · {threads} threads · {performance_mode()} mode." if process else "Install psutil to measure the app footprint."}
    except Exception as exc: result["footprint"]={"status":"warn","detail":f"Footprint measurement unavailable: {exc}"}
    return result


class NewsWidget(BaseWidget):
    MIN_SIZE = QSize(290, 295)
    DEFAULT_SIZE = QSize(410, 465)
    supports_refresh = True

    def __init__(self, manager: "WidgetManager", key: str) -> None:
        super().__init__(manager, key)
        self.network = QNetworkAccessManager(self)
        prune_news_image_cache()
        self.feed_reply: Optional[QNetworkReply] = None
        self.items: list[dict[str, str]] = []
        self.image_pixmaps: dict[int, QPixmap] = {}
        self.image_requested: set[int] = set()
        self.image_candidate_queues: dict[int, list[str]] = {}
        self.metadata_requested: set[int] = set()
        self.metadata_completed: set[int] = set()
        self.metadata_bridge = ArticleMetadataBridge(self)
        self.metadata_bridge.resolved.connect(self.article_metadata_ready)
        self.current_index = 0
        self.feed_generation = 0
        self.last_loaded = 0.0
        self.offline = False
        self.refresh_was_manual = False
        self.links_before_refresh: set[str] = set()
        self.current_link_before_refresh = ""
        self.content.installEventFilter(self)

        root = QVBoxLayout(self.content)
        root.setContentsMargins(14, 12, 10, 10)
        root.setSpacing(7)
        header = QHBoxLayout()
        titles = QVBoxLayout(); titles.setSpacing(0)
        title = QLabel("THE DAILY BRIEF")
        title.setObjectName("newsTitle")
        self.subtitle = QLabel("Recent headlines")
        self.subtitle.setObjectName("newsSubtitle")
        title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.subtitle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        titles.addWidget(title); titles.addWidget(self.subtitle)
        header.addLayout(titles); header.addStretch()
        root.addLayout(header)

        self.slide = NewsSlide(self.accent)
        self.slide.activated.connect(self.open_current_article)
        self.slide.slideRequested.connect(self.move_slide)
        root.addWidget(self.slide, 1)

        navigation = QHBoxLayout(); navigation.setContentsMargins(4, 0, 4, 0)
        self.previous_button = QPushButton("")
        self.previous_button.setFixedSize(28, 26)
        self.previous_button.setToolTip("Previous headline")
        self.previous_button.clicked.connect(lambda: self.move_slide(-1))
        self.dots_label = QLabel("●")
        self.dots_label.setObjectName("newsDots")
        self.dots_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_label = QLabel("0 / 0")
        self.counter_label.setObjectName("newsCounter")
        self.next_button = QPushButton("")
        self.next_button.setFixedSize(28, 26)
        self.next_button.setToolTip("Next headline")
        self.next_button.clicked.connect(lambda: self.move_slide(1))
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.dots_label, 1)
        navigation.addWidget(self.counter_label)
        navigation.addWidget(self.next_button)
        root.addLayout(navigation)
        self.status = QLabel("Loading headlines…")
        self.status.setObjectName("newsStatus")
        root.addWidget(self.status)

        self.cache_save_timer = QTimer(self)
        self.cache_save_timer.setSingleShot(True)
        self.cache_save_timer.setInterval(800)
        self.cache_save_timer.timeout.connect(lambda: self.save_cache(self.items))
        self.slider_timer = QTimer(self); self.slider_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.slider_timer.timeout.connect(lambda: self.move_slide(1, automatic=True))
        self.refresh_timer = QTimer(self); self.refresh_timer.setTimerType(Qt.TimerType.VeryCoarseTimer)
        self.refresh_timer.timeout.connect(lambda: self.refresh(False))
        self.apply_news_style(); self.apply_icons()
        self.load_cache()
        if not self.items:
            self.slide.image.set_source(None, "NEWS")
        QTimer.singleShot(250, lambda: self.refresh(False))
        self.restart_timer(); self.restart_slider()

    def settings_page(self) -> str:
        return "News"

    def apply_icons(self) -> None:
        super().apply_icons()
        if hasattr(self, "previous_button"):
            set_icon_button(self.previous_button, "fa6s.chevron-left", "‹", 11)
            set_icon_button(self.next_button, "fa6s.chevron-right", "›", 11)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self.slider_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        super().leaveEvent(event)
        self.restart_slider()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # The header remains a drag surface; the feature card and its controls
        # stay clickable and can also be changed with the mouse wheel.
        if obj is self.content and event.type() in (
            QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove, QEvent.Type.MouseButtonRelease
        ):
            try:
                if event.position().y() <= 52:  # type: ignore[attr-defined]
                    if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:  # type: ignore[attr-defined]
                        self.dragging = not self.config.get("locked", False)
                        self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()  # type: ignore[attr-defined]
                        self.raise_while_interacting()
                        return self.dragging
                    if event.type() == QEvent.Type.MouseMove and self.dragging:
                        self.move(event.globalPosition().toPoint() - self.drag_offset)  # type: ignore[attr-defined]
                        return True
                    if event.type() == QEvent.Type.MouseButtonRelease and self.dragging:
                        self.dragging = False; self.save_geometry()
                        QTimer.singleShot(450, self.keep_at_desktop_level)
                        return True
            except Exception:
                pass
        return super().eventFilter(obj, event)

    def paint_decor(self, painter: QPainter, card: QRect) -> None:
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(self.accent)
        painter.drawRoundedRect(card.left() + 17, card.top() + 19, 4, 24, 2, 2)

    def apply_news_style(self) -> None:
        c = widget_palette_colors()
        self.content.setStyleSheet(f"""
            QWidget {{ background: transparent; }}
            QLabel#newsTitle {{ color: {self.accent.name()}; font-size: 11px; font-weight: 700; letter-spacing: 1px; padding-left: 12px; }}
            QLabel#newsSubtitle {{ color: {c['muted'].name()}; font-size: 10px; padding-left: 12px; }}
            QLabel#newsStatus, QLabel#newsCounter {{ color: {c['muted'].name()}; font-size: 10px; padding-left: 5px; }}
            QLabel#newsDots {{ color: {self.accent.name()}; font-size: 11px; letter-spacing: 2px; }}
        """)
        self.slide.apply_style()

    def restart_timer(self) -> None:
        minutes = max(5, min(180, int(self.config.get("refresh_minutes", 15))))
        self.refresh_timer.start(minutes * 60 * 1000)

    def restart_slider(self) -> None:
        seconds = max(0, min(60, int(self.config.get("slide_seconds", 8))))
        if len(self.items) > 1 and seconds > 0 and STORE.data["appearance"].get("animations", True) and not self.underMouse():
            self.slider_timer.start(seconds * 1000)
        else:
            self.slider_timer.stop()

    def load_cache(self) -> None:
        try:
            cache = json.loads(NEWS_CACHE_PATH.read_text(encoding="utf-8"))
            if cache.get("feed") == news_feed_url(self.config) and isinstance(cache.get("items"), list):
                self.set_items(cache["items"])
                self.last_loaded = float(cache.get("saved_at", 0))
                self.status.setText("Saved headlines · checking for updates")
        except Exception:
            pass

    def save_cache(self, items: list[dict[str, str]]) -> None:
        payload = {"feed": news_feed_url(self.config), "saved_at": time.time(), "items": items}
        temp = NEWS_CACHE_PATH.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            os.replace(temp, NEWS_CACHE_PATH)
        except OSError:
            pass

    def refresh(self, force: bool = True) -> None:
        if self.feed_reply is not None and self.feed_reply.isRunning():
            if force:
                self.status.setText("A news refresh is already in progress…")
            return
        url = news_feed_url(self.config)
        parsed = QUrl(url)
        if not parsed.isValid() or parsed.scheme() not in ("http", "https"):
            self.status.setText("Add a valid HTTP(S) RSS URL in Settings")
            return
        self.refresh_was_manual = bool(force)
        self.links_before_refresh = {str(item.get("link", "")) for item in self.items}
        self.current_link_before_refresh = str(self.items[self.current_index].get("link", "")) if self.items else ""
        if force:
            parts = urllib.parse.urlsplit(url)
            query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
            query = [(key, value) for key, value in query if key != "_osw_refresh"]
            query.append(("_osw_refresh", str(int(time.time() * 1000))))
            url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment))
            parsed = QUrl(url)
        request = QNetworkRequest(parsed)
        request.setRawHeader(b"User-Agent", b"OS-Widgets/1.2 (+desktop RSS reader)")
        request.setRawHeader(b"Accept", b"application/rss+xml, application/atom+xml, application/xml, text/xml")
        request.setRawHeader(b"Cache-Control", b"no-cache, no-store, max-age=0")
        request.setRawHeader(b"Pragma", b"no-cache")
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        if hasattr(request, "setTransferTimeout"):
            request.setTransferTimeout(12000)
        self.status.setText("Checking for new headlines…" if force else "Refreshing…")
        self.feed_reply = self.network.get(request)
        self.feed_reply.finished.connect(self.feed_finished)

    def feed_finished(self) -> None:
        reply = self.feed_reply; self.feed_reply = None
        manual = self.refresh_was_manual; self.refresh_was_manual = False
        if reply is None:
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            code = int(reply.error().value)
            connectivity_errors = {1, 2, 3, 4, 7, 8, 99, 101, 102, 103, 104}
            self.offline = code in connectivity_errors
            if self.offline:
                if self.items:
                    self.status.setText("You're not connected · showing saved headlines")
                else:
                    self.status.setText("You're not connected")
                    self.slide.show_offline(); self.update_navigation()
            else:
                self.status.setText("The news source could not be refreshed")
            reply.deleteLater(); return
        data = bytes(reply.readAll()); reply.deleteLater()
        try:
            items = extract_news(data, str(self.config.get("source", "News")))
            if not items:
                raise ValueError("No feed items")
            self.offline = False
            unseen_link = ""
            if manual:
                for item in items:
                    link = str(item.get("link", ""))
                    if link and link not in self.links_before_refresh:
                        unseen_link = link; break
            preferred = unseen_link or self.current_link_before_refresh
            self.set_items(items, preferred_link=preferred, advance_if_same=manual and not unseen_link)
            self.save_cache(self.items)
            self.last_loaded = time.time()
            if manual and unseen_link:
                self.status.setText(f"New stories loaded · {len(self.items)} headlines")
            elif manual:
                self.status.setText(f"No newer stories yet · showing the next of {len(self.items)}")
            else:
                self.status.setText(f"Updated just now · {len(self.items)} headlines")
        except Exception:
            self.status.setText("The news feed returned an unreadable response")

    def set_items(self, items: list[dict[str, str]], preferred_link: str = "", advance_if_same: bool = False) -> None:
        self.feed_generation += 1
        cleaned: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            copy_item = dict(item)
            publisher_host = urllib.parse.urlparse(str(copy_item.get("publisher_url", ""))).hostname
            image_host = urllib.parse.urlparse(str(copy_item.get("thumbnail", ""))).hostname or ""
            if publisher_host == "news.google.com" and ("googleusercontent.com" in image_host or "gstatic.com" in image_host):
                copy_item.pop("publisher_url", None); copy_item.pop("thumbnail", None); copy_item.pop("article_image_resolved", None)
            identity = str(copy_item.get("link") or copy_item.get("title", "")).strip().lower()
            if not identity or identity in seen:
                continue
            seen.add(identity); cleaned.append(copy_item)
            if len(cleaned) >= 30:
                break
        self.items = cleaned
        self.image_pixmaps.clear(); self.image_requested.clear(); self.image_candidate_queues.clear()
        self.metadata_requested.clear(); self.metadata_completed.clear()
        for index, item in enumerate(self.items):
            if isinstance(item.get("image_candidates"), list) and item.get("image_candidates"):
                self.metadata_completed.add(index)
        self.current_index = 0
        if preferred_link and self.items:
            for index, item in enumerate(self.items):
                if str(item.get("link", "")) == preferred_link:
                    self.current_index = (index + (1 if advance_if_same else 0)) % len(self.items)
                    break
        category = self.config.get("category", "Top stories")
        source = self.config.get("source", "News")
        self.subtitle.setText(f"{source} · {category}" if source != "Custom RSS" else "Custom RSS feed")
        self.show_current(); self.restart_slider()

    def move_slide(self, amount: int, automatic: bool = False) -> None:
        if len(self.items) < 2:
            return
        self.current_index = (self.current_index + int(amount)) % len(self.items)
        self.show_current()
        if not automatic:
            self.restart_slider()

    def show_current(self) -> None:
        if not self.items:
            self.slide.show_offline() if self.offline else None
            self.update_navigation(); return
        self.current_index %= len(self.items)
        item = self.items[self.current_index]
        self.slide.set_item(item, self.image_pixmaps.get(self.current_index))
        self.update_navigation(); self.ensure_nearby_images()

    def update_navigation(self) -> None:
        total = len(self.items)
        enabled = total > 1
        self.previous_button.setEnabled(enabled); self.next_button.setEnabled(enabled)
        self.counter_label.setText(f"{self.current_index + 1} / {total}" if total else "0 / 0")
        if not total:
            self.dots_label.setText("●")
            return
        # Keep the pager compact for feeds with many items.
        visible = min(total, 7)
        center = min(self.current_index, visible - 1)
        dots = ["●" if i == center else "•" for i in range(visible)]
        self.dots_label.setText("  ".join(dots))

    def open_current_article(self) -> None:
        if self.items:
            link = self.items[self.current_index].get("publisher_url") or self.items[self.current_index].get("link", "")
            if link:
                QDesktopServices.openUrl(QUrl(link))

    def ensure_nearby_images(self) -> None:
        if not self.items:
            return
        nearby = {self.current_index} if performance_mode() == "eco" else {self.current_index, (self.current_index + 1) % len(self.items)}
        for index in nearby:
            if self.config.get("fetch_article_images", True):
                self.request_article_metadata(index, self.feed_generation)
            candidates = self.items[index].get("image_candidates", [])
            if isinstance(candidates, list) and candidates and index not in self.image_candidate_queues:
                self.queue_image_candidates(index, [str(value) for value in candidates], self.feed_generation)
            if index in self.image_pixmaps or index in self.image_requested:
                continue
            url = str(self.items[index].get("thumbnail", ""))
            if url:
                self.load_thumbnail(index, url, self.feed_generation, from_candidates=False)

    def request_article_metadata(self, index: int, generation: int) -> None:
        if generation != self.feed_generation or index >= len(self.items):
            return
        if index in self.metadata_requested or index in self.metadata_completed:
            return
        self.metadata_requested.add(index)
        item = dict(self.items[index])
        item["allow_reader_fallback"] = bool(self.config.get("reader_fallback", True))
        future = self.manager.executor.submit(resolve_article_metadata, item)
        bridge_ref = weakref.ref(self.metadata_bridge)
        def done(result) -> None:
            bridge = bridge_ref()
            if bridge is not None:
                try:
                    bridge.resolved.emit(index, generation, result.result())
                except Exception:
                    bridge.resolved.emit(index, generation, {})
        future.add_done_callback(done)

    def article_metadata_ready(self, index: int, generation: int, result: object) -> None:
        if generation != self.feed_generation or index >= len(self.items):
            return
        self.metadata_requested.discard(index)
        self.metadata_completed.add(index)
        if not isinstance(result, dict):
            return
        article_url = str(result.get("article_url", ""))
        if _safe_public_http_url(article_url) and urllib.parse.urlparse(article_url).hostname != "news.google.com":
            self.items[index]["publisher_url"] = article_url
        raw_candidates = result.get("image_urls", [])
        if not isinstance(raw_candidates, list):
            raw_candidates = []
        if result.get("image_url"):
            raw_candidates.insert(0, str(result["image_url"]))
        candidates: list[str] = []
        for value in raw_candidates:
            url = str(value)
            host = urllib.parse.urlparse(url).hostname or ""
            if _safe_public_http_url(url) and host != "news.google.com" and url not in candidates:
                candidates.append(url)
        if candidates:
            self.items[index]["image_candidates"] = candidates[:12]
            self.queue_image_candidates(index, candidates[:12], generation)
        self.cache_save_timer.start()

    def queue_image_candidates(self, index: int, candidates: list[str], generation: int) -> None:
        if generation != self.feed_generation or index >= len(self.items):
            return
        cleaned = [url for url in candidates if _safe_public_http_url(url)]
        if not cleaned:
            return
        self.image_candidate_queues[index] = list(dict.fromkeys(cleaned))
        if index not in self.image_requested:
            self.try_next_image(index, generation)

    def try_next_image(self, index: int, generation: int) -> None:
        if generation != self.feed_generation or index >= len(self.items) or index in self.image_requested:
            return
        queue = self.image_candidate_queues.get(index, [])
        if not queue:
            return
        url = queue.pop(0)
        self.load_thumbnail(index, url, generation, from_candidates=True)

    def load_thumbnail(self, index: int, url: str, generation: int, from_candidates: bool = False) -> None:
        qurl = QUrl(url)
        if not qurl.isValid() or qurl.scheme() not in ("http", "https"):
            if from_candidates:
                self.try_next_image(index, generation)
            return
        self.image_requested.add(index)
        cache_key = hashlib.sha256(url.encode("utf-8", "ignore")).hexdigest()[:32]
        cache_path = NEWS_IMAGE_CACHE_DIR / f"{cache_key}.img"
        cached = QPixmap()
        if cache_path.exists() and cached.load(str(cache_path)) and cached.width() >= 180 and cached.height() >= 90:
            self.image_requested.discard(index)
            queue = self.image_candidate_queues.get(index, [])
            small_placeholder = cached.width() * cached.height() < 250_000 and bool(queue)
            if small_placeholder:
                QTimer.singleShot(0, lambda: self.try_next_image(index, generation))
                return
            self.image_pixmaps[index] = cached
            self.items[index]["thumbnail"] = url; self.items[index]["article_image_resolved"] = True
            if from_candidates:
                self.image_candidate_queues.pop(index, None)
            if index == self.current_index:
                self.slide.image.set_source(cached, self.items[index].get("source", "News"))
            return
        if cache_path.exists():
            try:
                cache_path.unlink()
            except OSError:
                pass
        request = QNetworkRequest(qurl)
        request.setRawHeader(b"User-Agent", ARTICLE_USER_AGENT.encode("ascii"))
        request.setRawHeader(b"Accept", b"image/webp,image/png,image/jpeg,image/*;q=0.8,*/*;q=0.5")
        if index < len(self.items):
            referer = str(self.items[index].get("publisher_url") or self.items[index].get("link") or "")
            if _safe_public_http_url(referer):
                request.setRawHeader(b"Referer", referer.encode("utf-8", "ignore"))
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        if hasattr(request, "setTransferTimeout"):
            request.setTransferTimeout(12000)
        reply = self.network.get(request)
        self_ref = weakref.ref(self)
        def complete() -> None:
            target = self_ref(); loaded = False; pixmap = QPixmap()
            if target is not None and generation == target.feed_generation and reply.error() == QNetworkReply.NetworkError.NoError:
                content_type = bytes(reply.rawHeader("Content-Type")).decode("ascii", "ignore")
                data = reply.readAll()
                if len(data) <= 6_000_000 and ("image" in content_type or content_type == ""):
                    if pixmap.loadFromData(data) and pixmap.width() >= 180 and pixmap.height() >= 90:
                        ratio = pixmap.width() / max(1, pixmap.height())
                        loaded = .30 <= ratio <= 5.0
                        queue = target.image_candidate_queues.get(index, [])
                        if loaded and pixmap.width() * pixmap.height() < 250_000 and queue:
                            loaded = False  # Prefer a later full-size article photo over a small logo.
                        if loaded:
                            target.image_pixmaps[index] = pixmap
                            target.items[index]["thumbnail"] = url
                            target.items[index]["article_image_resolved"] = True
                            try:
                                cache_path.write_bytes(bytes(data))
                            except OSError:
                                pass
                            if index == target.current_index:
                                target.slide.image.set_source(pixmap, target.items[index].get("source", "News"))
            reply.deleteLater()
            if target is None or generation != target.feed_generation:
                return
            target.image_requested.discard(index)
            if loaded:
                if from_candidates:
                    target.image_candidate_queues.pop(index, None)
                elif target.image_candidate_queues.get(index):
                    QTimer.singleShot(0, lambda: target.try_next_image(index, generation))
                target.cache_save_timer.start()
            elif target.image_candidate_queues.get(index):
                QTimer.singleShot(0, lambda: target.try_next_image(index, generation))
            elif target.config.get("fetch_article_images", True) and index not in target.metadata_completed:
                target.request_article_metadata(index, generation)
        reply.finished.connect(complete)


class SettingsPanel(QDialog):
    PAGES = ["Widgets", "Clocks", "CPU", "Music", "Goal", "Calendar", "Quotes", "News", "Appearance", "General", "Diagnostics"]

    def __init__(self, manager: "WidgetManager", page: str = "Widgets") -> None:
        super().__init__(None)
        self.manager = manager
        self.draft = copy.deepcopy(STORE.data)
        self.controls: dict[str, Any] = {}
        self.music_files: list[str] = list(self.draft["widgets"].get("music",{}).get("playlist",[]))
        self.calendar_todos: list[dict[str,Any]] = copy.deepcopy(self.draft["widgets"].get("calendar",{}).get("todos",[]))
        self.diagnostic_rows: dict[str, DiagnosticRow] = {}
        self.diagnostic_report: dict[str, dict[str, str]] = {}
        self.diagnostics_bridge = DiagnosticsBridge(self)
        self.diagnostics_bridge.completed.connect(self.diagnostics_finished)
        self.setWindowTitle(f"{APP_NAME} Settings")
        self.setObjectName("settingsDialog")
        self.setWindowIcon(make_app_icon())
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setMinimumSize(860, 640)
        self.resize(1040, 720)
        self.setStyleSheet(app_stylesheet())

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 18)
        outer.setSpacing(17)
        header = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(make_app_icon(42).pixmap(42, 42))
        name_box = QVBoxLayout(); name_box.setSpacing(0)
        name = QLabel(APP_NAME)
        name.setStyleSheet("font-size: 20px; font-weight: 650;")
        tagline = QLabel(TAGLINE)
        tagline.setObjectName("muted")
        name_box.addWidget(name); name_box.addWidget(tagline)
        header.addWidget(mark); header.addLayout(name_box); header.addStretch()
        version = QLabel(f"STABLE  ·  {APP_VERSION}")
        version.setObjectName("versionBadge")
        header.addWidget(version)
        outer.addLayout(header)

        body = QHBoxLayout(); body.setSpacing(20)
        nav_panel = QFrame(); nav_panel.setObjectName("settingsNavPanel"); nav_panel.setFixedWidth(194)
        nav_layout = QVBoxLayout(nav_panel); nav_layout.setContentsMargins(10, 13, 10, 11); nav_layout.setSpacing(6)
        nav_section = QLabel("CONTROL CENTER"); nav_section.setObjectName("navSection"); nav_layout.addWidget(nav_section)
        self.nav = QListWidget(); self.nav.setIconSize(QSize(18,18)); self.nav.setSpacing(1)
        nav_icons = (
            "fa6s.table-cells-large", "fa6s.clock", "fa6s.gauge-high", "fa6s.music",
            "fa6s.flag-checkered", "fa6s.calendar-days", "fa6s.quote-left", "fa6s.newspaper", "fa6s.palette", "fa6s.gear", "fa6s.stethoscope",
        )
        for label, icon_name in zip(self.PAGES, nav_icons):
            item = QListWidgetItem(awesome_icon(icon_name), label); item.setToolTip(f"Open {label} settings"); self.nav.addItem(item)
        nav_layout.addWidget(self.nav,1)
        local_note=QLabel("LOCAL · PRIVATE");local_note.setObjectName("navSection");local_note.setAlignment(Qt.AlignmentFlag.AlignCenter);nav_layout.addWidget(local_note)
        body.addWidget(nav_panel)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        outer.addLayout(body, 1)

        self.stack.addWidget(self.build_widgets_page())
        self.stack.addWidget(self.build_clocks_page())
        self.stack.addWidget(self.build_cpu_page())
        self.stack.addWidget(self.build_music_page())
        self.stack.addWidget(self.build_goal_page())
        self.stack.addWidget(self.build_calendar_page())
        self.stack.addWidget(self.build_quotes_page())
        self.stack.addWidget(self.build_news_page())
        self.stack.addWidget(self.build_appearance_page())
        self.stack.addWidget(self.build_general_page())
        self.stack.addWidget(self.build_diagnostics_page())
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.currentRowChanged.connect(self.page_changed)

        footer = QHBoxLayout(); footer.setSpacing(9)
        footer_icon=QLabel();footer_icon.setPixmap(awesome_icon("fa6s.shield-halved",palette_colors()["muted"].name()).pixmap(13,13));footer_note=QLabel("Settings stay on this device");footer_note.setObjectName("muted");footer.addWidget(footer_icon);footer.addWidget(footer_note);footer.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setIcon(awesome_icon("fa6s.xmark"))
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save changes")
        save.setIcon(awesome_icon("fa6s.check", "#FFFFFF"))
        save.setObjectName("primary")
        save.clicked.connect(self.save_changes)
        footer.addWidget(cancel); footer.addWidget(save)
        outer.addLayout(footer)
        self.open_page(page)

    def open_page(self, page: str) -> None:
        try:
            self.nav.setCurrentRow(self.PAGES.index(page))
        except ValueError:
            self.nav.setCurrentRow(0)

    def page_shell(self, title: str, description: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(2, 0, 10, 0)
        layout.setSpacing(12)
        icon_map = {
            "your widgets":"fa6s.table-cells-large", "clock widgets":"fa6s.clock", "system monitor":"fa6s.gauge-high",
            "music player":"fa6s.music", "goal countdown":"fa6s.flag-checkered", "calendar and to-do":"fa6s.calendar-days",
            "motivational quotes":"fa6s.quote-left", "news":"fa6s.newspaper", "appearance":"fa6s.palette",
            "general":"fa6s.gear", "windows diagnostics":"fa6s.stethoscope",
        }
        header = QHBoxLayout(); header.setSpacing(12)
        tile = QFrame(); tile.setObjectName("pageIconTile"); tile.setFixedSize(44,44)
        tile_layout=QVBoxLayout(tile);tile_layout.setContentsMargins(0,0,0,0)
        icon_label=QLabel();icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter);icon_label.setPixmap(awesome_icon(icon_map.get(title.lower(),"fa6s.sliders"),app_accent_color().name()).pixmap(20,20));tile_layout.addWidget(icon_label)
        title_box=QVBoxLayout();title_box.setSpacing(2)
        heading = QLabel(title); heading.setObjectName("pageTitle")
        sub = QLabel(description); sub.setObjectName("pageDescription"); sub.setWordWrap(True)
        title_box.addWidget(heading);title_box.addWidget(sub)
        header.addWidget(tile);header.addLayout(title_box,1);layout.addLayout(header)
        return page, layout

    def build_widgets_page(self) -> QWidget:
        page, layout = self.page_shell("Your widgets", "Choose which gadgets appear on the desktop. Closing a widget here preserves its settings and layout.")
        card = QFrame(); card.setObjectName("settingsCard")
        grid = QGridLayout(card); grid.setContentsMargins(18, 15, 18, 15); grid.setVerticalSpacing(13)
        descriptions = {
            "clock1": ("Clock 1 · Local Time", "Analog or digital local clock"),
            "clock2": ("Clock 2 · New York", "Analog or digital world clock"),
            "clock3": ("Clock 3 · London", "Analog or digital world clock"),
            "clock4": ("Clock 4 · Tokyo", "Analog or digital world clock"),
            "cpu": ("System Monitor", "CPU, GPU, RAM, Wi-Fi, partitions and battery"),
            "music": ("Music Player", "Local playlist, playback controls and custom cover"),
            "goal": ("Goal Countdown", "Custom image and live days, hours, minutes, seconds"),
            "calendar": ("Calendar + To-do", "Month view with dated tasks and completion status"),
            "quotes": ("Motivational Quotes", "Ultra-mini, offline, low-frequency quote rotation"),
            "news": ("News", "Image headline slider with offline cache"),
        }
        for column, title in ((1, "Size"), (2, "Surface"), (3, "State")):
            header = QLabel(title.upper()); header.setObjectName("muted"); header.setStyleSheet("font-size: 9px; font-weight: 700;")
            grid.addWidget(header, 0, column)
        for row, (key, (title, desc)) in enumerate(descriptions.items(), start=1):
            cfg = self.draft["widgets"][key]
            box = QVBoxLayout(); box.setSpacing(1)
            label = QLabel(title); label.setStyleSheet("font-weight: 600;")
            detail = QLabel(desc); detail.setObjectName("muted")
            box.addWidget(label); box.addWidget(detail)
            size = QComboBox()
            for text, value in (("Ultra mini", "ultra_mini"), ("Mini", "mini"), ("Standard", "standard"), ("Large", "large")):
                size.addItem(text, value)
            size.setCurrentIndex(max(0, size.findData(str(cfg.get("size_preset", "standard")))))
            opacity = QComboBox()
            for text, value in (("Solid", 100), ("Glass", 85), ("Transparent", 70), ("Ultra", 55)):
                opacity.addItem(text, value)
            target_opacity = int(cfg.get("opacity", 100)); closest = min(range(opacity.count()), key=lambda i: abs(int(opacity.itemData(i)) - target_opacity))
            opacity.setCurrentIndex(closest)
            enabled = QCheckBox("Enabled")
            enabled.setChecked(bool(cfg.get("enabled", True)))
            self.controls[f"enabled:{key}"] = enabled
            self.controls[f"size:{key}"] = size; self.controls[f"opacity:{key}"] = opacity
            grid.addLayout(box, row, 0); grid.addWidget(size, row, 1); grid.addWidget(opacity, row, 2); grid.addWidget(enabled, row, 3)
        grid.setColumnStretch(0, 1)
        widgets_scroll=QScrollArea();widgets_scroll.setWidgetResizable(True);widgets_scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background:transparent; border:none; }");widgets_scroll.setWidget(card);layout.addWidget(widgets_scroll,1)
        note = QLabel("Tip: size and transparency can also be changed from each widget's hover menu. Manual resizing remains available from the lower-right corner.")
        note.setObjectName("muted"); note.setWordWrap(True)
        layout.addWidget(note); layout.addStretch()
        return page

    def build_clocks_page(self) -> QWidget:
        page, layout = self.page_shell("Clock widgets", "Choose analog or digital faces, seconds, location, time zone and independent formatting for every clock.")
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        host = QWidget(); host.setStyleSheet("background: transparent;"); host_layout = QVBoxLayout(host); host_layout.setContentsMargins(1, 4, 7, 4); host_layout.setSpacing(10)
        for number in range(1, 5):
            key = f"clock{number}"; cfg = self.draft["widgets"][key]
            group = QGroupBox(f"Clock {number}")
            grid = QGridLayout(group); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(9)
            city = QLineEdit(str(cfg.get("city", "")))
            city.setMaxLength(40)
            zone = QComboBox(); zone.setEditable(True); zone.addItems(TIMEZONES)
            zone.setCurrentText(str(cfg.get("timezone", "Local")))
            fmt = QComboBox(); fmt.addItems(["12-hour", "24-hour"])
            fmt.setCurrentIndex(1 if cfg.get("format_24h", False) else 0)
            display = QComboBox(); display.addItem("Digital", "digital"); display.addItem("Analog", "analog")
            display.setCurrentIndex(1 if cfg.get("display_mode", "digital") == "analog" else 0)
            seconds = QCheckBox("Show seconds hand / seconds value"); seconds.setChecked(bool(cfg.get("show_seconds", True)))
            show_date = QCheckBox("Show current date"); show_date.setChecked(bool(cfg.get("show_date", True)))
            grid.addWidget(QLabel("City / label"), 0, 0); grid.addWidget(city, 0, 1)
            grid.addWidget(QLabel("Time zone"), 1, 0); grid.addWidget(zone, 1, 1)
            grid.addWidget(QLabel("Time format"), 2, 0); grid.addWidget(fmt, 2, 1)
            grid.addWidget(QLabel("Clock face"), 3, 0); grid.addWidget(display, 3, 1)
            grid.addWidget(seconds, 4, 0, 1, 2)
            grid.addWidget(show_date, 5, 0, 1, 2)
            grid.setColumnStretch(1, 1)
            self.controls[f"city:{key}"] = city
            self.controls[f"zone:{key}"] = zone
            self.controls[f"format:{key}"] = fmt
            self.controls[f"display:{key}"] = display
            self.controls[f"seconds:{key}"] = seconds
            self.controls[f"date:{key}"] = show_date
            host_layout.addWidget(group)
        host_layout.addStretch(); scroll.setWidget(host); layout.addWidget(scroll, 1)
        return page

    def build_cpu_page(self) -> QWidget:
        page, layout = self.page_shell("System monitor", "CPU, GPU, RAM, Wi-Fi, scrollable disk partitions and accurate laptop battery status.")
        cfg = self.draft["widgets"]["cpu"]
        card = QFrame(); card.setObjectName("settingsCard")
        form = QGridLayout(card); form.setContentsMargins(18, 16, 18, 16); form.setVerticalSpacing(14)
        temp = QCheckBox("Show CPU temperature when a sensor is available")
        temp.setChecked(bool(cfg.get("show_temperature", True)))
        ram = QCheckBox("Show RAM summary on the CPU slide")
        ram.setChecked(bool(cfg.get("show_ram", True)))
        interval = QComboBox(); interval.addItem("Every 0.5 seconds", 500); interval.addItem("Every 1 second", 1000); interval.addItem("Every 2 seconds", 2000); interval.addItem("Every 5 seconds", 5000)
        target = int(cfg.get("interval_ms", 2000))
        for i in range(interval.count()):
            if interval.itemData(i) == target: interval.setCurrentIndex(i)
        form.addWidget(temp, 0, 0, 1, 2); form.addWidget(ram, 1, 0, 1, 2)
        form.addWidget(QLabel("Sampling rate"), 2, 0); form.addWidget(interval, 2, 1)
        sensor_test = QPushButton("Test temperature providers")
        sensor_test.setIcon(awesome_icon("fa6s.stethoscope")); sensor_test.clicked.connect(lambda: (self.open_page("Diagnostics"), QTimer.singleShot(100, self.run_diagnostics)))
        form.addWidget(sensor_test, 3, 1)
        form.setColumnStretch(1, 1)
        self.controls["cpu:temp"] = temp; self.controls["cpu:ram"] = ram; self.controls["cpu:interval"] = interval
        layout.addWidget(card)

        alerts = QGroupBox("Performance alerts")
        alert_grid = QGridLayout(alerts); alert_grid.setHorizontalSpacing(12); alert_grid.setVerticalSpacing(9)
        alert_enabled = QCheckBox("Show notifications when thresholds are crossed, even if the widget card is hidden")
        alert_enabled.setChecked(bool(cfg.get("alerts_enabled", False)))
        cpu_limit = QSpinBox(); cpu_limit.setRange(50, 100); cpu_limit.setSuffix(" %"); cpu_limit.setValue(int(cfg.get("alert_cpu", 90)))
        gpu_limit = QSpinBox(); gpu_limit.setRange(50, 100); gpu_limit.setSuffix(" %"); gpu_limit.setValue(int(cfg.get("alert_gpu", 95)))
        ram_limit = QSpinBox(); ram_limit.setRange(50, 100); ram_limit.setSuffix(" %"); ram_limit.setValue(int(cfg.get("alert_ram", 90)))
        temp_limit = QSpinBox(); temp_limit.setRange(55, 110); temp_limit.setSuffix(" °C"); temp_limit.setValue(int(cfg.get("alert_temp", 90)))
        cooldown = QSpinBox(); cooldown.setRange(1, 120); cooldown.setSuffix(" min"); cooldown.setValue(int(cfg.get("alert_cooldown_minutes", 10)))
        alert_grid.addWidget(alert_enabled, 0, 0, 1, 4)
        alert_grid.addWidget(QLabel("CPU"), 1, 0); alert_grid.addWidget(cpu_limit, 1, 1)
        alert_grid.addWidget(QLabel("GPU"), 1, 2); alert_grid.addWidget(gpu_limit, 1, 3)
        alert_grid.addWidget(QLabel("RAM"), 2, 0); alert_grid.addWidget(ram_limit, 2, 1)
        alert_grid.addWidget(QLabel("Temperature"), 2, 2); alert_grid.addWidget(temp_limit, 2, 3)
        alert_grid.addWidget(QLabel("Notification cooldown"), 3, 0); alert_grid.addWidget(cooldown, 3, 1)
        test_alert = QPushButton("Send test notification"); test_alert.setIcon(awesome_icon("fa6s.bell"))
        test_alert.clicked.connect(self.manager.send_test_alert)
        alert_grid.addWidget(test_alert, 3, 2, 1, 2)
        sound_enabled = QCheckBox("Play a custom ring on alerts")
        sound_enabled.setChecked(bool(cfg.get("alert_sound_enabled", False)))
        sound_path = QLineEdit(str(cfg.get("alert_sound_path", ""))); sound_path.setPlaceholderText("Choose a WAV, MP3, M4A, AAC, OGG or FLAC file")
        browse_sound = QPushButton("Browse…"); browse_sound.setIcon(awesome_icon("fa6s.folder-open"))
        browse_sound.clicked.connect(lambda: self.choose_alert_sound(sound_path))
        preview_sound = QPushButton("Preview ring"); preview_sound.setIcon(awesome_icon("fa6s.volume-high"))
        preview_sound.clicked.connect(lambda: self.manager.play_alert_sound(sound_path.text(), preview=True))
        alert_grid.addWidget(sound_enabled, 4, 0, 1, 2)
        alert_grid.addWidget(sound_path, 5, 0, 1, 2)
        alert_grid.addWidget(browse_sound, 5, 2); alert_grid.addWidget(preview_sound, 5, 3)
        alert_grid.setColumnStretch(1, 1); alert_grid.setColumnStretch(3, 1)
        def update_alert_controls() -> None:
            enabled = alert_enabled.isChecked()
            for control in (cpu_limit, gpu_limit, ram_limit, temp_limit, cooldown, sound_enabled):
                control.setEnabled(enabled)
            sound_controls = enabled and sound_enabled.isChecked()
            for control in (sound_path, browse_sound, preview_sound):
                control.setEnabled(sound_controls)
        alert_enabled.toggled.connect(update_alert_controls); sound_enabled.toggled.connect(update_alert_controls); update_alert_controls()
        self.controls["cpu:alerts_enabled"] = alert_enabled
        self.controls["cpu:alert_cpu"] = cpu_limit; self.controls["cpu:alert_gpu"] = gpu_limit
        self.controls["cpu:alert_ram"] = ram_limit; self.controls["cpu:alert_temp"] = temp_limit
        self.controls["cpu:alert_cooldown"] = cooldown
        self.controls["cpu:alert_sound_enabled"] = sound_enabled
        self.controls["cpu:alert_sound_path"] = sound_path
        layout.addWidget(alerts)
        note = QLabel("CPU uses native Windows kernel time deltas and GPU uses Windows PDH engine counters. CPU/RAM alerts require three consecutive high samples; hysteresis prevents repeated notifications for one sustained spike.")
        note.setObjectName("muted"); note.setWordWrap(True)
        layout.addWidget(note); layout.addStretch()
        return page

    def choose_alert_sound(self, target: QLineEdit) -> None:
        start = target.text().strip() or str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Choose alert ring", start, "Audio files (*.wav *.mp3 *.m4a *.aac *.ogg *.flac)")
        if path:
            target.setText(path)

    def build_music_page(self) -> QWidget:
        page, layout = self.page_shell("Music player", "Play local audio without opening a full music application. Playback is signal-driven and adds no idle polling timer.")
        cfg = self.draft["widgets"]["music"]
        card = QFrame(); card.setObjectName("settingsCard"); form = QGridLayout(card); form.setContentsMargins(18,16,18,16); form.setVerticalSpacing(12)
        self.music_files_label = QLabel(); self.music_files_label.setObjectName("muted"); self.music_files_label.setWordWrap(True)
        choose = QPushButton("Choose audio files…"); choose.setIcon(awesome_icon("fa6s.music")); choose.clicked.connect(self.choose_music_files)
        clear = QPushButton("Clear playlist"); clear.setIcon(awesome_icon("fa6s.trash-can")); clear.clicked.connect(self.clear_music_files)
        cover = QLineEdit(str(cfg.get("cover_image",""))); cover.setPlaceholderText("Optional JPG, PNG or WebP cover image")
        browse_cover = QPushButton("Browse…"); browse_cover.setIcon(awesome_icon("fa6s.image")); browse_cover.clicked.connect(lambda: self.choose_image_file(cover,"Choose music cover"))
        volume = QSpinBox(); volume.setRange(0,100); volume.setSuffix(" %"); volume.setValue(int(cfg.get("volume",70)))
        form.addWidget(QLabel("Playlist"),0,0); form.addWidget(self.music_files_label,0,1,1,2)
        buttons=QHBoxLayout(); buttons.addWidget(choose); buttons.addWidget(clear); buttons.addStretch(); form.addLayout(buttons,1,1,1,2)
        form.addWidget(QLabel("Custom cover"),2,0); form.addWidget(cover,2,1); form.addWidget(browse_cover,2,2)
        cover_hint=QLabel("Recommended image: 600 × 600 px (square, 1:1)");cover_hint.setObjectName("muted");form.addWidget(cover_hint,3,1,1,2)
        form.addWidget(QLabel("Default volume"),4,0); form.addWidget(volume,4,1); form.setColumnStretch(1,1)
        self.controls["music:cover"] = cover; self.controls["music:volume"] = volume; self.update_music_files_label(); layout.addWidget(card)
        note=QLabel("Supported formats depend on Windows Media Foundation through Qt Multimedia: MP3, WAV, M4A, AAC, OGG and FLAC are requested. Music starts only when you press Play."); note.setObjectName("muted"); note.setWordWrap(True); layout.addWidget(note); layout.addStretch(); return page

    def choose_music_files(self) -> None:
        files,_=QFileDialog.getOpenFileNames(self,"Choose music files",str(Path.home()),"Audio files (*.mp3 *.wav *.m4a *.aac *.ogg *.flac)")
        if files: self.music_files=files; self.update_music_files_label()

    def clear_music_files(self) -> None: self.music_files=[]; self.update_music_files_label()
    def update_music_files_label(self) -> None:
        if hasattr(self,"music_files_label"): self.music_files_label.setText(f"{len(self.music_files)} track(s): " + ", ".join(Path(x).name for x in self.music_files[:4]) + ("…" if len(self.music_files)>4 else "") if self.music_files else "No tracks selected")

    def choose_image_file(self, target: QLineEdit, title: str) -> None:
        path,_=QFileDialog.getOpenFileName(self,title,target.text() or str(Path.home()),"Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path: target.setText(path)

    def build_goal_page(self) -> QWidget:
        page, layout = self.page_shell("Goal countdown", "Count down to a personal goal in days, hours, minutes and seconds, with an optional custom image.")
        cfg=self.draft["widgets"]["goal"]; card=QFrame(); card.setObjectName("settingsCard"); form=QGridLayout(card); form.setContentsMargins(18,16,18,16); form.setVerticalSpacing(12)
        title=QLineEdit(str(cfg.get("title","My Goal"))); title.setMaxLength(80)
        target=QDateTimeEdit(); target.setCalendarPopup(True); target.setDisplayFormat("dd MMM yyyy  hh:mm AP")
        try: py_target=dt.datetime.fromisoformat(str(cfg.get("target",""))); target.setDateTime(QDateTime.fromSecsSinceEpoch(int(py_target.timestamp())))
        except Exception: target.setDateTime(QDateTime.currentDateTime().addDays(30))
        image=QLineEdit(str(cfg.get("image_path",""))); image.setPlaceholderText("Optional JPG, PNG or WebP image")
        browse=QPushButton("Browse…"); browse.setIcon(awesome_icon("fa6s.image")); browse.clicked.connect(lambda: self.choose_image_file(image,"Choose goal image"))
        completed=QLineEdit(str(cfg.get("completed_text","Goal reached"))); completed.setMaxLength(80)
        seconds=QCheckBox("Show seconds"); seconds.setChecked(bool(cfg.get("show_seconds",True)))
        form.addWidget(QLabel("Goal title"),0,0); form.addWidget(title,0,1,1,2)
        form.addWidget(QLabel("Target date and time"),1,0); form.addWidget(target,1,1,1,2)
        form.addWidget(QLabel("Custom image"),2,0); form.addWidget(image,2,1); form.addWidget(browse,2,2)
        image_hint=QLabel("Recommended image: 1200 × 800 px (landscape, 3:2)");image_hint.setObjectName("muted");form.addWidget(image_hint,3,1,1,2)
        form.addWidget(QLabel("Completion message"),4,0); form.addWidget(completed,4,1,1,2); form.addWidget(seconds,5,0,1,3); form.setColumnStretch(1,1)
        self.controls["goal:title"]=title; self.controls["goal:target"]=target; self.controls["goal:image"]=image; self.controls["goal:completed"]=completed; self.controls["goal:seconds"]=seconds
        layout.addWidget(card); note=QLabel("The countdown uses one coarse one-second timer only while this widget is enabled. Disable seconds to reduce updates to once per minute."); note.setObjectName("muted"); note.setWordWrap(True); layout.addWidget(note); layout.addStretch(); return page

    def build_calendar_page(self) -> QWidget:
        page, layout = self.page_shell("Calendar and to-do", "Plan dated tasks in the calendar. Task dots appear on the widget and completed items can be retained or hidden.")
        cfg=self.draft["widgets"]["calendar"];card=QFrame();card.setObjectName("settingsCard");root=QVBoxLayout(card);root.setContentsMargins(18,16,18,16);root.setSpacing(10)
        add_row=QHBoxLayout();date=QDateEdit();date.setCalendarPopup(True);date.setDate(QDate.currentDate());task=QLineEdit();task.setPlaceholderText("New to-do item");add=QPushButton("Add task");add.setIcon(awesome_icon("fa6s.plus"));add.clicked.connect(lambda:self.add_calendar_todo(date,task));add_row.addWidget(date);add_row.addWidget(task,1);add_row.addWidget(add);root.addLayout(add_row)
        self.calendar_list=QListWidget();self.calendar_list.setMinimumHeight(220);root.addWidget(self.calendar_list,1)
        actions=QHBoxLayout();done=QPushButton("Toggle completed");done.setIcon(awesome_icon("fa6s.circle-check"));remove=QPushButton("Remove selected");remove.setIcon(awesome_icon("fa6s.trash-can"));done.clicked.connect(self.toggle_calendar_todo);remove.clicked.connect(self.remove_calendar_todo);show=QCheckBox("Show completed tasks on widget");show.setChecked(bool(cfg.get("show_completed",True)));actions.addWidget(done);actions.addWidget(remove);actions.addStretch();actions.addWidget(show);root.addLayout(actions)
        self.controls["calendar:show_completed"]=show;self.refresh_calendar_list();layout.addWidget(card);layout.addStretch();return page

    def refresh_calendar_list(self) -> None:
        if not hasattr(self,"calendar_list"):return
        self.calendar_list.clear()
        for task in sorted(self.calendar_todos,key=lambda x:(str(x.get('date','')),str(x.get('text','')))):
            prefix='✓' if task.get('done') else '○';item=QListWidgetItem(f"{prefix}  {task.get('date','')}  ·  {task.get('text','')}");item.setData(Qt.ItemDataRole.UserRole,str(task.get('id','')));self.calendar_list.addItem(item)
    def add_calendar_todo(self,date:QDateEdit,text:QLineEdit) -> None:
        value=text.text().strip()
        if value:self.calendar_todos.append({'id':str(time.time_ns()),'text':value,'date':date.date().toString('yyyy-MM-dd'),'done':False});text.clear();self.refresh_calendar_list()
    def selected_calendar_id(self)->str:
        item=self.calendar_list.currentItem() if hasattr(self,"calendar_list") else None;return str(item.data(Qt.ItemDataRole.UserRole)) if item else ''
    def toggle_calendar_todo(self) -> None:
        identity=self.selected_calendar_id()
        for task in self.calendar_todos:
            if str(task.get('id'))==identity:task['done']=not task.get('done',False);break
        self.refresh_calendar_list()
    def remove_calendar_todo(self) -> None:
        identity=self.selected_calendar_id();self.calendar_todos=[x for x in self.calendar_todos if str(x.get('id'))!=identity];self.refresh_calendar_list()

    def build_quotes_page(self) -> QWidget:
        page, layout = self.page_shell("Motivational quotes", "An ultra-mini offline quote card. Built-in and personal quotes rotate using one very-coarse timer.")
        cfg=self.draft["widgets"]["quotes"];card=QFrame();card.setObjectName("settingsCard");form=QGridLayout(card);form.setContentsMargins(18,16,18,16);form.setVerticalSpacing(12)
        interval=QComboBox()
        for minutes in (1,5,15,30,60):interval.addItem(f"Every {minutes} minute{'s' if minutes!=1 else ''}",minutes)
        interval.setCurrentIndex(max(0,interval.findData(int(cfg.get("interval_minutes",5)))));builtin=QCheckBox("Include built-in motivational quotes");builtin.setChecked(bool(cfg.get("use_builtin",True)));custom=QPlainTextEdit();custom.setPlaceholderText("Add one custom quote per line");custom.setPlainText('\n'.join(str(x) for x in cfg.get('custom_quotes',[])));custom.setMinimumHeight(180)
        form.addWidget(QLabel("Rotation interval"),0,0);form.addWidget(interval,0,1);form.addWidget(builtin,1,0,1,2);form.addWidget(QLabel("Custom quotes"),2,0);form.addWidget(custom,2,1);form.setColumnStretch(1,1)
        self.controls["quotes:interval"]=interval;self.controls["quotes:builtin"]=builtin;self.controls["quotes:custom"]=custom;layout.addWidget(card);note=QLabel("Recommended preset: Ultra mini (230 × 105 px). No network connection is used.");note.setObjectName("muted");layout.addWidget(note);layout.addStretch();return page

    def build_news_page(self) -> QWidget:
        page, layout = self.page_shell("News", "Pick an image-rich headline slider. Headlines stay cached locally and remain readable while offline.")
        cfg = self.draft["widgets"]["news"]
        card = QFrame(); card.setObjectName("settingsCard")
        form = QGridLayout(card); form.setContentsMargins(18, 16, 18, 16); form.setVerticalSpacing(12)
        source = QComboBox(); source.addItems(["Google News", "BBC News", "Custom RSS"]); source.setCurrentText(str(cfg.get("source", "Google News")))
        category = QComboBox(); category.addItems(["Top stories", "World", "Technology", "Business", "Science", "Sports"]); category.setCurrentText(str(cfg.get("category", "Top stories")))
        custom = QLineEdit(str(cfg.get("custom_url", ""))); custom.setPlaceholderText("https://example.com/feed.xml")
        refresh = QComboBox()
        for minutes in (5, 15, 30, 60, 120): refresh.addItem(f"Every {minutes} minutes", minutes)
        for i in range(refresh.count()):
            if refresh.itemData(i) == int(cfg.get("refresh_minutes", 15)): refresh.setCurrentIndex(i)
        slide_speed = QComboBox()
        for label, seconds in (("Off", 0), ("Every 5 seconds", 5), ("Every 8 seconds", 8), ("Every 12 seconds", 12), ("Every 20 seconds", 20)):
            slide_speed.addItem(label, seconds)
        for i in range(slide_speed.count()):
            if slide_speed.itemData(i) == int(cfg.get("slide_seconds", 8)): slide_speed.setCurrentIndex(i)
        article_images = QCheckBox("Search publisher articles for the best available image")
        article_images.setChecked(bool(cfg.get("fetch_article_images", True)))
        reader_fallback = QCheckBox("Use a text-reader fallback when a publisher blocks image access")
        reader_fallback.setChecked(bool(cfg.get("reader_fallback", True)))
        form.addWidget(QLabel("Source"), 0, 0); form.addWidget(source, 0, 1)
        form.addWidget(QLabel("Category"), 1, 0); form.addWidget(category, 1, 1)
        form.addWidget(QLabel("Custom RSS URL"), 2, 0); form.addWidget(custom, 2, 1)
        form.addWidget(QLabel("Refresh interval"), 3, 0); form.addWidget(refresh, 3, 1)
        form.addWidget(QLabel("Auto-advance"), 4, 0); form.addWidget(slide_speed, 4, 1)
        form.addWidget(article_images, 5, 0, 1, 2)
        form.addWidget(reader_fallback, 6, 0, 1, 2)
        form.setColumnStretch(1, 1)
        def update_custom() -> None:
            custom.setEnabled(source.currentText() == "Custom RSS")
            category.setEnabled(source.currentText() != "Custom RSS")
        source.currentTextChanged.connect(update_custom); update_custom()
        self.controls["news:source"] = source; self.controls["news:category"] = category
        self.controls["news:custom"] = custom; self.controls["news:refresh"] = refresh
        self.controls["news:slide"] = slide_speed; self.controls["news:article_images"] = article_images
        self.controls["news:reader_fallback"] = reader_fallback
        layout.addWidget(card)
        privacy = QLabel("The slider checks metadata, JSON-LD, lazy-loaded images and srcset, then retries alternatives. If enabled, blocked public article URLs may be sent to the r.jina.ai text-reader service to recover image links. Successful images remain cached offline.")
        privacy.setObjectName("muted"); privacy.setWordWrap(True)
        layout.addWidget(privacy)
        clear_cache = QPushButton("Clear saved news and images")
        clear_cache.setIcon(awesome_icon("fa6s.trash-can"))
        clear_cache.clicked.connect(self.clear_news_cache)
        cache_row = QHBoxLayout(); cache_row.addWidget(clear_cache); cache_row.addStretch()
        layout.addLayout(cache_row); layout.addStretch()
        return page

    def clear_news_cache(self) -> None:
        try:
            NEWS_CACHE_PATH.unlink(missing_ok=True)
            for path in NEWS_IMAGE_CACHE_DIR.iterdir():
                if path.is_file():
                    path.unlink(missing_ok=True)
            QMessageBox.information(self, APP_NAME, "Saved headlines and article images were cleared.")
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, f"The news cache could not be fully cleared.\n\n{exc}")

    def style_color_button(self, button: QPushButton, value: str) -> None:
        color = safe_color(value, "#3178C6")
        text = "#111111" if color.lightness() > 165 else "#FFFFFF"
        button.setStyleSheet(f"QPushButton {{ background:{color.name()}; color:{text}; border:1px solid rgba(128,128,128,.45); border-radius:7px; }}")

    def choose_theme_color(self, target: QLineEdit, button: QPushButton) -> None:
        chosen = QColorDialog.getColor(safe_color(target.text(), "#3178C6"), self, "Choose colour")
        if chosen.isValid():
            target.setText(chosen.name()); self.style_color_button(button, chosen.name())

    def build_appearance_page(self) -> QWidget:
        page, layout = self.page_shell("Appearance", "Choose light/dark mode, your application accent, a custom widget palette and square or rounded cards.")
        cfg = self.draft["appearance"]
        card = QFrame(); card.setObjectName("settingsCard")
        form = QGridLayout(card); form.setContentsMargins(18, 16, 18, 16); form.setVerticalSpacing(14)
        theme = QComboBox(); theme.addItem("Use Windows setting", "system"); theme.addItem("Light", "light"); theme.addItem("Dark", "dark")
        for i in range(theme.count()):
            if theme.itemData(i) == cfg.get("theme", "system"): theme.setCurrentIndex(i)
        transparency = QCheckBox("Enable translucent glass surfaces"); transparency.setChecked(bool(cfg.get("transparency", True)))
        animations = QCheckBox("Enable subtle animations"); animations.setChecked(bool(cfg.get("animations", True)))
        form.addWidget(QLabel("Theme"), 0, 0); form.addWidget(theme, 0, 1)
        form.addWidget(transparency, 1, 0, 1, 2); form.addWidget(animations, 2, 0, 1, 2)
        form.setColumnStretch(1, 1)
        self.controls["appearance:theme"] = theme; self.controls["appearance:transparency"] = transparency; self.controls["appearance:animations"] = animations
        layout.addWidget(card)

        colors_group = QGroupBox("Custom colour theme and widget shape")
        colors_grid = QGridLayout(colors_group); colors_grid.setHorizontalSpacing(10); colors_grid.setVerticalSpacing(8)
        app_color = QLineEdit(str(cfg.get("app_accent", "#3178C6"))); app_color.setMaxLength(9)
        app_pick = QPushButton(""); app_pick.setFixedWidth(42); self.style_color_button(app_pick, app_color.text())
        app_pick.clicked.connect(lambda: self.choose_theme_color(app_color, app_pick))
        custom_widgets = QCheckBox("Use a custom colour theme for all widgets"); custom_widgets.setChecked(bool(cfg.get("custom_widget_colors", False)))
        widget_accent = QLineEdit(str(cfg.get("widget_accent", "#58A6FF"))); widget_accent.setMaxLength(9)
        widget_accent_pick = QPushButton(""); widget_accent_pick.setFixedWidth(42); self.style_color_button(widget_accent_pick, widget_accent.text())
        widget_accent_pick.clicked.connect(lambda: self.choose_theme_color(widget_accent, widget_accent_pick))
        widget_surface = QLineEdit(str(cfg.get("widget_surface", "#171C26"))); widget_surface.setMaxLength(9)
        widget_surface_pick = QPushButton(""); widget_surface_pick.setFixedWidth(42); self.style_color_button(widget_surface_pick, widget_surface.text())
        widget_surface_pick.clicked.connect(lambda: self.choose_theme_color(widget_surface, widget_surface_pick))
        corners = QComboBox(); corners.addItem("Rounded", "rounded"); corners.addItem("Soft square", "soft"); corners.addItem("Square", "square")
        corners.setCurrentIndex(max(0, corners.findData(str(cfg.get("widget_corners", "rounded")))))
        colors_grid.addWidget(QLabel("Application accent"),0,0); colors_grid.addWidget(app_color,0,1); colors_grid.addWidget(app_pick,0,2)
        colors_grid.addWidget(custom_widgets,1,0,1,3)
        colors_grid.addWidget(QLabel("Widget accent"),2,0); colors_grid.addWidget(widget_accent,2,1); colors_grid.addWidget(widget_accent_pick,2,2)
        colors_grid.addWidget(QLabel("Widget surface"),3,0); colors_grid.addWidget(widget_surface,3,1); colors_grid.addWidget(widget_surface_pick,3,2)
        colors_grid.addWidget(QLabel("Widget corners"),4,0); colors_grid.addWidget(corners,4,1,1,2); colors_grid.setColumnStretch(1,1)
        def update_widget_theme_controls() -> None:
            enabled = custom_widgets.isChecked()
            for control in (widget_accent, widget_accent_pick, widget_surface, widget_surface_pick): control.setEnabled(enabled)
        custom_widgets.toggled.connect(update_widget_theme_controls); update_widget_theme_controls()
        self.controls["appearance:app_accent"] = app_color
        self.controls["appearance:custom_widget_colors"] = custom_widgets
        self.controls["appearance:widget_accent"] = widget_accent
        self.controls["appearance:widget_surface"] = widget_surface
        self.controls["appearance:widget_corners"] = corners
        layout.addWidget(colors_group)

        top_group = QGroupBox("Window behavior")
        top_layout = QVBoxLayout(top_group)
        behavior_note = QLabel("Always-on-top is configured independently from each widget’s hover menu. Unpinned widgets stay at desktop level, behind normal application windows.")
        behavior_note.setWordWrap(True); top_layout.addWidget(behavior_note)
        button = QPushButton("Set all widgets always on top"); button.setIcon(awesome_icon("fa6s.layer-group"))
        button.clicked.connect(lambda: self.set_all_top(True))
        normal = QPushButton("Set all widgets to desktop level"); normal.setIcon(awesome_icon("fa6s.display"))
        normal.clicked.connect(lambda: self.set_all_top(False))
        line = QHBoxLayout(); line.addWidget(button); line.addWidget(normal); line.addStretch(); top_layout.addLayout(line)
        layout.addWidget(top_group); layout.addStretch()
        return page

    def set_all_top(self, value: bool) -> None:
        for cfg in self.draft["widgets"].values():
            cfg["always_top"] = value
        QMessageBox.information(self, APP_NAME, "All widgets will be always on top." if value else "All widgets will return to desktop level.")

    def build_general_page(self) -> QWidget:
        page, layout = self.page_shell("General", "Startup, layout recovery and local settings management.")
        cfg = self.draft["general"]
        card = QFrame(); card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(18, 16, 18, 16); card_layout.setSpacing(12)
        startup = QCheckBox("Start OS Widgets automatically with Windows")
        startup.setChecked(bool(cfg.get("startup", False)))
        quiet = QLabel("Starts quietly in the notification area and restores the exact saved widget layout.")
        quiet.setObjectName("muted"); quiet.setWordWrap(True)
        mode_row=QHBoxLayout(); mode_row.addWidget(QLabel("Performance mode")); mode=QComboBox(); mode.addItem("Balanced — recommended","balanced"); mode.addItem("Eco — fewer background updates","eco"); mode.addItem("Responsive — faster monitoring","responsive"); mode.setCurrentIndex(max(0,mode.findData(str(cfg.get("performance_mode","balanced"))))); mode_row.addWidget(mode,1)
        card_layout.addWidget(startup); card_layout.addWidget(quiet); card_layout.addLayout(mode_row)
        self.controls["general:startup"] = startup; self.controls["general:performance"] = mode
        layout.addWidget(card)
        reset_group = QGroupBox("Reset")
        reset_layout = QVBoxLayout(reset_group)
        positions = QPushButton("Reset widget positions and sizes"); positions.setIcon(awesome_icon("fa6s.arrows-rotate"))
        positions.clicked.connect(self.reset_positions)
        everything = QPushButton("Reset all settings"); everything.setIcon(awesome_icon("fa6s.triangle-exclamation","#FF718B"))
        everything.clicked.connect(self.reset_everything)
        row = QHBoxLayout(); row.addWidget(positions); row.addWidget(everything); row.addStretch()
        reset_layout.addLayout(row)
        local = QLabel(f"Settings are stored locally in: {SETTINGS_PATH}")
        local.setObjectName("muted"); local.setWordWrap(True); reset_layout.addWidget(local)
        layout.addWidget(reset_group); layout.addStretch()
        return page

    def build_diagnostics_page(self) -> QWidget:
        page, layout = self.page_shell(
            "Windows diagnostics",
            "Run release-readiness checks for GPU counters, startup, desktop behavior, display scaling, sensors and notifications.",
        )
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }")
        host = QWidget(); host.setStyleSheet("background: transparent;"); host_layout = QVBoxLayout(host)
        host_layout.setContentsMargins(1, 4, 7, 4); host_layout.setSpacing(7)
        checks = (
            ("platform", "Windows version"),
            ("gpu", "GPU PDH counters"),
            ("disks", "Storage partitions and usage"),
            ("battery", "Laptop battery detection"),
            ("startup", "Startup registration"),
            ("desktop", "Desktop Z-order host"),
            ("dpi", "Per-monitor DPI and mixed scaling"),
            ("temperature", "Hardware temperature provider"),
            ("notifications", "Popup and tray notifications"),
            ("audio", "Custom alert ring playback"),
            ("storage", "Settings and cache storage"),
            ("dependencies", "Runtime dependencies"),
            ("footprint", "Current application footprint"),
        )
        for key, title in checks:
            row = DiagnosticRow(title)
            self.diagnostic_rows[key] = row
            host_layout.addWidget(row)
        host_layout.addStretch(); scroll.setWidget(host); layout.addWidget(scroll, 1)
        actions = QHBoxLayout()
        self.run_diagnostics_button = QPushButton("Run diagnostics")
        self.run_diagnostics_button.setIcon(awesome_icon("fa6s.play"))
        self.run_diagnostics_button.clicked.connect(self.run_diagnostics)
        self.copy_diagnostics_button = QPushButton("Copy report")
        self.copy_diagnostics_button.setIcon(awesome_icon("fa6s.copy"))
        self.copy_diagnostics_button.setEnabled(False)
        self.copy_diagnostics_button.clicked.connect(self.copy_diagnostics_report)
        actions.addWidget(self.run_diagnostics_button); actions.addWidget(self.copy_diagnostics_button); actions.addStretch()
        layout.addLayout(actions)
        return page

    def page_changed(self, index: int) -> None:
        if 0 <= index < len(self.PAGES) and self.PAGES[index] == "Diagnostics" and not self.diagnostic_report:
            QTimer.singleShot(120, self.run_diagnostics)

    def run_diagnostics(self) -> None:
        if not hasattr(self, "run_diagnostics_button") or not self.run_diagnostics_button.isEnabled():
            return
        self.run_diagnostics_button.setEnabled(False)
        self.run_diagnostics_button.setText("Running…")
        self.copy_diagnostics_button.setEnabled(False)
        for row in self.diagnostic_rows.values():
            row.set_status("pending", "Checking…")
        displays: list[dict[str, Any]] = []
        for screen in QApplication.screens():
            displays.append({
                "name": screen.name() or "Display",
                "dpi": float(screen.logicalDotsPerInch()),
                "ratio": float(screen.devicePixelRatio()),
            })
        tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        widgets = [
            {"key": key, "hwnd": int(widget.winId()), "always_top": bool(widget.config.get("always_top", False))}
            for key, widget in self.manager.widgets.items() if widget.isVisible()
        ]
        future = self.manager.executor.submit(run_windows_diagnostics, displays, tray_available, widgets)
        bridge_ref = weakref.ref(self.diagnostics_bridge)
        def done(result) -> None:
            bridge = bridge_ref()
            if bridge is not None:
                try:
                    bridge.completed.emit(result.result())
                except Exception as exc:
                    bridge.completed.emit({"platform": {"status": "fail", "detail": f"Diagnostics failed: {exc}"}})
        future.add_done_callback(done)

    def diagnostics_finished(self, report: object) -> None:
        self.run_diagnostics_button.setEnabled(True)
        self.run_diagnostics_button.setText("Run again")
        if not isinstance(report, dict):
            return
        self.diagnostic_report = report
        for key, row in self.diagnostic_rows.items():
            value = report.get(key, {"status": "warn", "detail": "No result was returned."})
            row.set_status(str(value.get("status", "info")), str(value.get("detail", "")))
        self.copy_diagnostics_button.setEnabled(True)

    def copy_diagnostics_report(self) -> None:
        if not self.diagnostic_report:
            return
        lines = [f"{APP_NAME} {APP_VERSION} — Windows diagnostics", dt.datetime.now().astimezone().isoformat(), ""]
        for key, value in self.diagnostic_report.items():
            title = self.diagnostic_rows[key].title_label.text() if key in self.diagnostic_rows else key
            lines.append(f"[{str(value.get('status', 'info')).upper()}] {title}: {value.get('detail', '')}")
        QApplication.clipboard().setText("\n".join(lines))
        self.copy_diagnostics_button.setText("Copied")
        QTimer.singleShot(1400, lambda: self.copy_diagnostics_button.setText("Copy report"))

    def reset_positions(self) -> None:
        if QMessageBox.question(self, APP_NAME, "Reset all widget positions and sizes to their polished default layout?") == QMessageBox.StandardButton.Yes:
            for cfg in self.draft["widgets"].values():
                cfg["geometry"] = None; cfg["size_preset"] = "standard"
            STORE.data = copy.deepcopy(self.draft); STORE.save(); self.manager.apply_settings(reset_layout=True)

    def reset_everything(self) -> None:
        if QMessageBox.warning(self, APP_NAME, "Reset every OS Widgets setting? This cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            old_startup = STORE.data["general"].get("startup", False)
            STORE.reset()
            if old_startup: set_windows_startup(False)
            self.manager.apply_settings(reset_layout=True)
            self.accept()

    def save_changes(self) -> None:
        for key in ("clock1", "clock2", "clock3", "clock4", "cpu", "music", "goal", "calendar", "quotes", "news"):
            self.draft["widgets"][key]["enabled"] = self.controls[f"enabled:{key}"].isChecked()
            self.draft["widgets"][key]["size_preset"] = self.controls[f"size:{key}"].currentData()
            self.draft["widgets"][key]["opacity"] = int(self.controls[f"opacity:{key}"].currentData())
        for number in range(1, 5):
            key = f"clock{number}"
            self.draft["widgets"][key]["city"] = self.controls[f"city:{key}"].text().strip() or f"Clock {number}"
            zone = self.controls[f"zone:{key}"].currentText().strip() or "UTC"
            self.draft["widgets"][key]["timezone"] = zone
            self.draft["widgets"][key]["format_24h"] = self.controls[f"format:{key}"].currentIndex() == 1
            self.draft["widgets"][key]["display_mode"] = self.controls[f"display:{key}"].currentData()
            self.draft["widgets"][key]["show_seconds"] = self.controls[f"seconds:{key}"].isChecked()
            self.draft["widgets"][key]["show_date"] = self.controls[f"date:{key}"].isChecked()
        cpu = self.draft["widgets"]["cpu"]
        cpu["show_temperature"] = self.controls["cpu:temp"].isChecked()
        cpu["show_ram"] = self.controls["cpu:ram"].isChecked()
        cpu["interval_ms"] = int(self.controls["cpu:interval"].currentData())
        cpu["alerts_enabled"] = self.controls["cpu:alerts_enabled"].isChecked()
        cpu["alert_cpu"] = self.controls["cpu:alert_cpu"].value()
        cpu["alert_gpu"] = self.controls["cpu:alert_gpu"].value()
        cpu["alert_ram"] = self.controls["cpu:alert_ram"].value()
        cpu["alert_temp"] = self.controls["cpu:alert_temp"].value()
        cpu["alert_cooldown_minutes"] = self.controls["cpu:alert_cooldown"].value()
        cpu["alert_sound_enabled"] = self.controls["cpu:alert_sound_enabled"].isChecked()
        cpu["alert_sound_path"] = self.controls["cpu:alert_sound_path"].text().strip()
        music=self.draft["widgets"]["music"]; music["playlist"]=list(self.music_files); music["cover_image"]=self.controls["music:cover"].text().strip(); music["volume"]=self.controls["music:volume"].value()
        goal=self.draft["widgets"]["goal"]; goal["title"]=self.controls["goal:title"].text().strip() or "My Goal"; goal["target"]=self.controls["goal:target"].dateTime().toPython().astimezone().replace(microsecond=0).isoformat(); goal["image_path"]=self.controls["goal:image"].text().strip(); goal["completed_text"]=self.controls["goal:completed"].text().strip() or "Goal reached"; goal["show_seconds"]=self.controls["goal:seconds"].isChecked()
        calendar_cfg=self.draft["widgets"]["calendar"];calendar_cfg["todos"]=copy.deepcopy(self.calendar_todos);calendar_cfg["show_completed"]=self.controls["calendar:show_completed"].isChecked()
        quotes=self.draft["widgets"]["quotes"];quotes["interval_minutes"]=int(self.controls["quotes:interval"].currentData());quotes["use_builtin"]=self.controls["quotes:builtin"].isChecked();quotes["custom_quotes"]=[line.strip() for line in self.controls["quotes:custom"].toPlainText().splitlines() if line.strip()]
        news = self.draft["widgets"]["news"]
        news["source"] = self.controls["news:source"].currentText()
        news["category"] = self.controls["news:category"].currentText()
        news["custom_url"] = self.controls["news:custom"].text().strip()
        news["refresh_minutes"] = int(self.controls["news:refresh"].currentData())
        news["slide_seconds"] = int(self.controls["news:slide"].currentData())
        news["fetch_article_images"] = self.controls["news:article_images"].isChecked()
        news["reader_fallback"] = self.controls["news:reader_fallback"].isChecked()
        appearance = self.draft["appearance"]
        appearance["theme"] = self.controls["appearance:theme"].currentData()
        appearance["transparency"] = self.controls["appearance:transparency"].isChecked()
        appearance["animations"] = self.controls["appearance:animations"].isChecked()
        appearance["app_accent"] = safe_color(self.controls["appearance:app_accent"].text(), "#3178C6").name()
        appearance["custom_widget_colors"] = self.controls["appearance:custom_widget_colors"].isChecked()
        appearance["widget_accent"] = safe_color(self.controls["appearance:widget_accent"].text(), "#58A6FF").name()
        appearance["widget_surface"] = safe_color(self.controls["appearance:widget_surface"].text(), "#171C26").name()
        appearance["widget_corners"] = self.controls["appearance:widget_corners"].currentData()
        self.draft["general"]["performance_mode"] = self.controls["general:performance"].currentData()
        new_startup = self.controls["general:startup"].isChecked()
        old_startup = bool(STORE.data["general"].get("startup", False))
        self.draft["general"]["startup"] = new_startup
        if new_startup != old_startup:
            ok, error = set_windows_startup(new_startup)
            if not ok and IS_WINDOWS:
                QMessageBox.warning(self, APP_NAME, f"Windows startup could not be updated.\n\n{error}")
                self.draft["general"]["startup"] = old_startup
        STORE.data = deep_merge(default_settings(), self.draft)
        STORE.save()
        self.manager.apply_settings()
        self.accept()


class PerformanceAlertDialog(QDialog):
    keepMonitoring = Signal(str)
    disableAlerts = Signal()

    def __init__(self, metric: str, title: str, message: str, value: float, threshold: float) -> None:
        super().__init__(None)
        self.metric_key = metric; self.action_taken = False
        self.setWindowTitle(title); self.setWindowIcon(make_app_icon())
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(440, 250); self.resize(460, 270)
        outer = QVBoxLayout(self); outer.setContentsMargins(12, 12, 12, 12)
        card = QFrame(); card.setObjectName("alertPopup")
        colors = palette_colors(); surface = "#171C26" if resolved_dark() else "#FFFFFF"
        card.setStyleSheet(f"""
            QFrame#alertPopup {{ background: {surface}; border: 1px solid rgba(255,113,139,0.42); border-radius: 16px; }}
            QLabel {{ background: transparent; color: {colors['text'].name()}; border: none; }}
            QLabel#alertKicker {{ color: #FF718B; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#alertValue {{ font-size: 31px; font-weight: 700; }}
            QLabel#alertMessage {{ color: {colors['muted'].name()}; font-size: 12px; }}
        """)
        layout = QVBoxLayout(card); layout.setContentsMargins(20, 18, 20, 18); layout.setSpacing(10)
        header = QHBoxLayout(); icon = QLabel(); warning_icon = awesome_icon("fa6s.triangle-exclamation", "#FF718B")
        icon.setPixmap(warning_icon.pixmap(22,22)); kicker = QLabel("OS WIDGETS · PERFORMANCE WARNING"); kicker.setObjectName("alertKicker")
        header.addWidget(icon); header.addWidget(kicker); header.addStretch(); layout.addLayout(header)
        metric_title = QLabel(title); metric_title.setStyleSheet("font-size: 19px; font-weight: 650;")
        layout.addWidget(metric_title)
        unit = "°C" if metric == "TEMP" else "%"
        value_row = QHBoxLayout(); value_label = QLabel(f"{value:.0f}{unit}"); value_label.setObjectName("alertValue")
        threshold_label = QLabel(f"Threshold  {threshold:.0f}{unit}"); threshold_label.setObjectName("alertMessage")
        value_row.addWidget(value_label); value_row.addStretch(); value_row.addWidget(threshold_label); layout.addLayout(value_row)
        detail = QLabel(message + "\nKeep monitoring to be warned again after the cooldown, or accept the risk to disable all performance alerts.")
        detail.setObjectName("alertMessage"); detail.setWordWrap(True); layout.addWidget(detail)
        buttons = QHBoxLayout(); buttons.addStretch()
        disable = QPushButton("I accept the risk · Turn off alerts")
        disable.setStyleSheet("QPushButton { background:#6E2634; color:white; border:1px solid #A74358; } QPushButton:hover { background:#873044; }")
        disable.clicked.connect(self.disable_clicked)
        keep = QPushButton("Keep monitoring"); keep.setObjectName("primary"); keep.clicked.connect(self.keep_clicked)
        buttons.addWidget(disable); buttons.addWidget(keep); layout.addLayout(buttons)
        outer.addWidget(card)
        self.setStyleSheet(app_stylesheet())

    def showEvent(self, event) -> None:  # type: ignore[override]
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry(); self.move(area.right() - self.width() - 28, area.bottom() - self.height() - 28)
        super().showEvent(event); self.raise_(); self.activateWindow()

    def keep_clicked(self) -> None:
        self.action_taken = True; self.keepMonitoring.emit(self.metric_key); self.close()

    def disable_clicked(self) -> None:
        self.action_taken = True; self.disableAlerts.emit(); self.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self.action_taken:
            self.action_taken = True; self.keepMonitoring.emit(self.metric_key)
        super().closeEvent(event)


class WidgetManager(QObject):
    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self.app = app
        self.widgets: dict[str, BaseWidget] = {}
        self.settings_panel: Optional[SettingsPanel] = None
        self.alert_dialog: Optional[PerformanceAlertDialog] = None
        self.alert_queue: deque[tuple[str, str, str, float, float]] = deque()
        self.media_player = None; self.audio_output = None
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="OSWidgets")
        self.clock_timer = QTimer(self); self.clock_timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.clock_timer.setInterval(1000); self.clock_timer.timeout.connect(self.tick_clocks); self.clock_timer.start()
        self.desktop_level_timer = QTimer(self); self.desktop_level_timer.setTimerType(Qt.TimerType.VeryCoarseTimer)
        self.desktop_level_timer.setInterval(3000); self.desktop_level_timer.timeout.connect(self.maintain_desktop_level); self.desktop_level_timer.start()
        self.tray = self.create_tray()
        self.create_enabled_widgets()

    def create_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(make_app_icon(), self)
        tray.setToolTip(f"{APP_NAME} — {TAGLINE}")
        tray.activated.connect(self.tray_activated)
        self.rebuild_tray_menu(tray)
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray.show()
        return tray

    def rebuild_tray_menu(self, tray: Optional[QSystemTrayIcon] = None) -> None:
        tray = tray or self.tray
        menu = QMenu()
        menu.setStyleSheet(app_stylesheet())
        title = menu.addAction(make_app_icon(20), APP_NAME)
        title.setEnabled(False)
        menu.addAction(awesome_icon("fa6s.gear"), "Open settings", lambda: self.open_settings("Widgets"))
        menu.addSeparator()
        for key, label in (("clock1", "Clock 1"), ("clock2", "Clock 2"), ("clock3", "Clock 3"), ("clock4", "Clock 4"), ("cpu", "System Monitor"), ("music", "Music Player"), ("goal", "Goal Countdown"), ("calendar", "Calendar + To-do"), ("quotes", "Motivational Quotes"), ("news", "News")):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(bool(STORE.data["widgets"][key].get("enabled", True)))
            action.toggled.connect(lambda checked, k=key: self.set_enabled(k, checked))
        menu.addSeparator()
        alerts_action = menu.addAction(awesome_icon("fa6s.bell"), "Performance alerts")
        alerts_action.setCheckable(True)
        alerts_action.setChecked(bool(STORE.data["widgets"]["cpu"].get("alerts_enabled", False)))
        alerts_action.toggled.connect(self.set_alerts_enabled)
        menu.addAction(awesome_icon("fa6s.stethoscope"), "Run diagnostics", lambda: self.open_settings("Diagnostics"))
        menu.addSeparator()
        menu.addAction("Show all widgets", self.show_all)
        menu.addAction("Hide all widgets", self.hide_all)
        menu.addSeparator()
        menu.addAction("Exit OS Widgets", self.quit)
        tray.setContextMenu(menu)

    def tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings("Widgets")

    def show_performance_alert(
        self, title: str, message: str, metric: str = "CPU",
        value: float = 0.0, threshold: float = 0.0,
    ) -> None:
        # Avoid stacking the same warning while a popup is already visible.
        if self.alert_dialog is not None and self.alert_dialog.isVisible() and self.alert_dialog.metric_key == metric:
            return
        if any(entry[0] == metric for entry in self.alert_queue):
            return
        self.alert_queue.append((metric, title, message, float(value), float(threshold)))
        self.display_next_alert()

    def display_next_alert(self) -> None:
        if self.alert_dialog is not None and self.alert_dialog.isVisible():
            return
        if not self.alert_queue or not STORE.data["widgets"]["cpu"].get("alerts_enabled", False):
            return
        metric, title, message, value, threshold = self.alert_queue.popleft()
        dialog = PerformanceAlertDialog(metric, title, message, value, threshold)
        self.alert_dialog = dialog
        dialog.keepMonitoring.connect(self.alert_keep_monitoring)
        dialog.disableAlerts.connect(self.alert_disable_all)
        dialog.finished.connect(lambda _result: self.alert_popup_finished(dialog))
        dialog.show(); dialog.raise_(); dialog.activateWindow()
        sound_cfg = STORE.data["widgets"]["cpu"]
        if sound_cfg.get("alert_sound_enabled", False):
            self.play_alert_sound(str(sound_cfg.get("alert_sound_path", "")))

    def alert_keep_monitoring(self, metric: str) -> None:
        widget = self.widgets.get("cpu")
        if isinstance(widget, CPUWidget):
            widget.acknowledge_alert(metric)

    def alert_disable_all(self) -> None:
        self.alert_queue.clear(); self.set_alerts_enabled(False)

    def alert_popup_finished(self, dialog: PerformanceAlertDialog) -> None:
        if self.alert_dialog is dialog:
            self.alert_dialog = None
        dialog.deleteLater(); QTimer.singleShot(200, self.display_next_alert)

    def play_alert_sound(self, path: str = "", preview: bool = False) -> None:
        sound = Path(path).expanduser() if path else None
        supported = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}
        if not sound or not sound.is_file() or sound.suffix.lower() not in supported:
            if preview:
                QMessageBox.warning(self.settings_panel, APP_NAME, "Choose an existing WAV, MP3, M4A, AAC, OGG or FLAC audio file.")
            return
        if QMediaPlayer is not None and QAudioOutput is not None:
            try:
                if self.media_player is None:
                    self.audio_output = QAudioOutput(self)
                    self.audio_output.setVolume(.85)
                    self.media_player = QMediaPlayer(self)
                    self.media_player.setAudioOutput(self.audio_output)
                self.media_player.stop(); self.media_player.setSource(QUrl.fromLocalFile(str(sound.resolve()))); self.media_player.play()
                return
            except Exception:
                pass
        if IS_WINDOWS and sound.suffix.lower() == ".wav":
            try:
                import winsound
                winsound.PlaySound(str(sound), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                return
            except Exception as exc:
                if preview:
                    QMessageBox.warning(self.settings_panel, APP_NAME, f"The sound could not be played.\n\n{exc}")
                return
        if preview:
            QMessageBox.warning(self.settings_panel, APP_NAME, "This audio format is not supported by the installed Windows media components.")

    def send_test_alert(self) -> None:
        was_enabled = bool(STORE.data["widgets"]["cpu"].get("alerts_enabled", False))
        if not was_enabled:
            STORE.data["widgets"]["cpu"]["alerts_enabled"] = True
        self.show_performance_alert(
            "Test performance warning",
            "This is a preview of the new high-usage popup.",
            "TEST", 91.0, 90.0,
        )
        if not was_enabled:
            # Keep it enabled until the popup is created, then restore the setting.
            QTimer.singleShot(50, lambda: STORE.data["widgets"]["cpu"].__setitem__("alerts_enabled", False))

    def set_alerts_enabled(self, enabled: bool) -> None:
        cfg = STORE.data["widgets"]["cpu"]
        cfg["alerts_enabled"] = bool(enabled)
        if self.settings_panel is not None and "cpu:alerts_enabled" in self.settings_panel.controls:
            self.settings_panel.controls["cpu:alerts_enabled"].setChecked(bool(enabled))
        if not enabled:
            self.alert_queue.clear()
            if self.alert_dialog is not None and self.alert_dialog.isVisible():
                self.alert_dialog.action_taken = True; self.alert_dialog.close()
        if enabled and not cfg.get("enabled", True):
            widget = self.ensure_widget("cpu")
            if widget is not None:
                widget.hide()  # Continue lightweight sampling without a desktop card.
        elif not enabled and not cfg.get("enabled", True) and "cpu" in self.widgets:
            widget = self.widgets.pop("cpu")
            widget.hide(); widget.deleteLater()
        STORE.save()
        QTimer.singleShot(0, self.rebuild_tray_menu)

    def available_rect(self) -> QRect:
        screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

    def default_geometries(self) -> dict[str, QRect]:
        area = self.available_rect()
        margin, gap = 24, 12
        clock_w, clock_h = 292, 156
        cpu_w, cpu_h = 370, 245
        news_w, news_h = 410, min(500, max(360, area.height() - 2 * margin))
        x_right = area.right() - margin - clock_w + 1
        x_second = x_right - clock_w - gap
        y = area.top() + margin
        defaults = {
            "clock1": QRect(x_second, y, clock_w, clock_h),
            "clock2": QRect(x_right, y, clock_w, clock_h),
            "clock3": QRect(x_second, y + clock_h + gap, clock_w, clock_h),
            "clock4": QRect(x_right, y + clock_h + gap, clock_w, clock_h),
            "cpu": QRect(x_second, y + 2 * (clock_h + gap), cpu_w, cpu_h),
            "news": QRect(area.left() + margin, area.top() + margin, news_w, news_h),
            "music": QRect(area.left() + margin + news_w + gap, y, 390, 205),
            "goal": QRect(area.left() + margin + news_w + gap, y + 217, 420, 215),
            "calendar": QRect(area.left() + margin + news_w + gap + 432, y, 380, 340),
            "quotes": QRect(area.left() + margin + news_w + gap + 432, y + 352, 230, 105),
        }
        # On smaller displays, use a cascading layout that always remains reachable.
        if area.width() < 1200 or defaults["cpu"].bottom() > area.bottom() - margin:
            for i, key in enumerate(defaults):
                size = defaults[key].size()
                defaults[key] = QRect(area.left() + margin + i * 28, area.top() + margin + i * 30, size.width(), size.height())
        return defaults

    def rect_visible(self, rect: QRect) -> bool:
        for screen in QApplication.screens():
            visible = rect.intersected(screen.availableGeometry())
            if visible.width() >= 80 and visible.height() >= 50:
                return True
        return False

    def create_enabled_widgets(self) -> None:
        for key, cfg in STORE.data["widgets"].items():
            background_cpu = key == "cpu" and cfg.get("alerts_enabled", False)
            if cfg.get("enabled", True) or background_cpu:
                widget = self.ensure_widget(key)
                if widget is not None and not cfg.get("enabled", True):
                    widget.hide()

    def ensure_widget(self, key: str) -> Optional[BaseWidget]:
        if key in self.widgets:
            widget = self.widgets[key]
            widget.show()
            return widget
        if key.startswith("clock"):
            widget: BaseWidget = ClockWidget(self, key)
        elif key == "cpu":
            widget = CPUWidget(self, key)
        elif key == "music":
            widget = MusicWidget(self, key)
        elif key == "goal":
            widget = GoalCountdownWidget(self, key)
        elif key == "calendar":
            widget = CalendarWidget(self, key)
        elif key == "quotes":
            widget = QuoteWidget(self, key)
        elif key == "news":
            widget = NewsWidget(self, key)
        else:
            return None
        self.widgets[key] = widget
        widget.restore_geometry(self.default_geometries()[key])
        widget.show()
        return widget

    def set_enabled(self, key: str, enabled: bool) -> None:
        cfg = STORE.data["widgets"][key]
        cfg["enabled"] = bool(enabled)
        if enabled:
            self.ensure_widget(key)
        elif key == "cpu" and cfg.get("alerts_enabled", False):
            widget = self.ensure_widget(key)
            if widget is not None:
                widget.save_geometry(); widget.hide()
        elif key in self.widgets:
            widget = self.widgets.pop(key)
            widget.save_geometry()
            widget.hide()
            widget.deleteLater()
        STORE.save()
        QTimer.singleShot(0, self.rebuild_tray_menu)

    def show_all(self) -> None:
        for key in STORE.data["widgets"]:
            self.set_enabled(key, True)

    def hide_all(self) -> None:
        for key in list(STORE.data["widgets"]):
            self.set_enabled(key, False)

    def tick_clocks(self) -> None:
        for widget in self.widgets.values():
            if isinstance(widget, ClockWidget) and widget.isVisible():
                widget.update_time()

    def maintain_desktop_level(self) -> None:
        for widget in self.widgets.values():
            if widget.isVisible(): widget.keep_at_desktop_level()

    def open_settings(self, page: str = "Widgets") -> None:
        if self.settings_panel is not None and self.settings_panel.isVisible():
            self.settings_panel.open_page(page)
            self.settings_panel.raise_(); self.settings_panel.activateWindow()
            return
        self.settings_panel = SettingsPanel(self, page)
        self.settings_panel.finished.connect(lambda _: setattr(self, "settings_panel", None))
        self.settings_panel.show(); self.settings_panel.raise_(); self.settings_panel.activateWindow()

    def apply_settings(self, reset_layout: bool = False) -> None:
        self.app.setStyleSheet(app_stylesheet()); self.app.setWindowIcon(make_app_icon()); self.tray.setIcon(make_app_icon())
        self.desktop_level_timer.setInterval(5000 if performance_mode()=="eco" else (2000 if performance_mode()=="responsive" else 3000))
        if reset_layout:
            for widget in list(self.widgets.values()):
                widget.hide(); widget.deleteLater()
            self.widgets.clear()
        for key, cfg in STORE.data["widgets"].items():
            if cfg.get("enabled", True):
                widget = self.ensure_widget(key)
                if widget is None: continue
                widget.config = cfg
                widget.accent = accent_for(key)
                if isinstance(widget, ClockWidget): widget.analog_face.accent = widget.accent
                if isinstance(widget, MusicWidget): widget.cover.accent = widget.accent
                if isinstance(widget, GoalCountdownWidget): widget.image.accent = widget.accent
                if isinstance(widget, CalendarWidget): widget.grid.accent = widget.accent
                if isinstance(widget, NewsWidget): widget.slide.accent = widget.accent; widget.slide.image.accent = widget.accent
                desired_top = bool(cfg.get("always_top", False))
                if bool(widget.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) != desired_top:
                    widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, desired_top); widget.show()
                if reset_layout:
                    widget.restore_geometry(self.default_geometries()[key])
                requested_preset = str(cfg.get("size_preset", "standard"))
                if not reset_layout and widget.last_size_preset != requested_preset:
                    widget.apply_size_preset(requested_preset, persist=False)
                widget.apply_icons()
                if isinstance(widget, ClockWidget):
                    widget.apply_clock_style(); widget.update_time()
                elif isinstance(widget, CPUWidget):
                    widget.restart_timer(); widget.apply_cpu_style(); widget.update_disk_rows(); widget.sample()
                elif isinstance(widget, MusicWidget):
                    widget.apply_music_style(); widget.apply_icons(); widget.reload_config()
                elif isinstance(widget, GoalCountdownWidget):
                    widget.apply_goal_style(); widget.reload_config()
                elif isinstance(widget, CalendarWidget):
                    widget.apply_calendar_style(); widget.apply_icons(); widget.reload_config()
                elif isinstance(widget, QuoteWidget):
                    widget.apply_quote_style(); widget.reload_config()
                elif isinstance(widget, NewsWidget):
                    widget.apply_news_style(); widget.restart_timer(); widget.restart_slider()
                    widget.ensure_nearby_images(); widget.refresh()
                widget.update()
            elif key == "cpu" and cfg.get("alerts_enabled", False):
                widget = self.ensure_widget("cpu")
                if widget is not None:
                    widget.config = cfg; widget.restart_timer(); widget.hide()
            elif key in self.widgets:
                self.set_enabled(key, False)
        self.rebuild_tray_menu()

    def quit(self) -> None:
        for widget in self.widgets.values():
            widget.save_geometry()
        STORE.save()
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.tray.hide()
        self.app.quit()


def enable_windows_dpi_awareness() -> None:
    if not IS_WINDOWS:
        return
    try:
        # Per-monitor V2 awareness keeps saved device-independent geometries
        # accurate across mixed-DPI Windows 11 displays.
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass


def package_self_test(expect_defaults: bool = False) -> int:
    """Small, non-interactive check used by the Windows packaging workflow."""
    try:
        if APP_VERSION != "1.2.0" or SETTINGS_SCHEMA_VERSION != 2:
            return 20
        if expect_defaults:
            defaults = default_settings()
            if STORE.data.get("version") != SETTINGS_SCHEMA_VERSION:
                return 21
            for key in ("music", "goal", "calendar", "quotes"):
                if STORE.data["widgets"][key].get("enabled") != defaults["widgets"][key]["enabled"]:
                    return 22
            if any(STORE.data["widgets"][key].get("geometry") is not None for key in STORE.data["widgets"]):
                return 23
        if IS_WINDOWS:
            volumes = SystemMonitor().disk_partitions()
            if not volumes or any(item.get("source") != "Windows volume API" for item in volumes):
                return 24
            if any(not (0.0 <= float(item["percent"]) <= 100.0) for item in volumes):
                return 25
        return 0
    except Exception:
        return 99


def main() -> int:
    enable_windows_dpi_awareness()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("OS Widgets")
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(make_app_icon())
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(app_stylesheet())

    if "--package-self-test" in sys.argv:
        return package_self_test("--expect-defaults" in sys.argv)

    # A native lock file prevents duplicate background instances after login.
    lock_path = str(Path(tempfile.gettempdir()) / "os_widgets_instance.lock")
    try:
        from PySide6.QtCore import QLockFile
        instance_lock = QLockFile(lock_path)
        instance_lock.setStaleLockTime(15000)
        if not instance_lock.tryLock(120):
            if IS_WINDOWS:
                ctypes.windll.user32.MessageBoxW(None, "OS Widgets is already running in the notification area.", APP_NAME, 0x40)
            return 0
        app.instance_lock = instance_lock  # type: ignore[attr-defined]
    except Exception:
        pass

    manager = WidgetManager(app)
    app.manager = manager  # type: ignore[attr-defined]
    if "--settings" in sys.argv:
        QTimer.singleShot(300, manager.open_settings)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
