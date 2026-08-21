<div align="center">
  <img src="docs/brand/readme-hero.svg" alt="OS Widgets — Your desktop. Your widgets." width="100%">
</div>

<div align="center">

[![Windows build](https://github.com/Comet-Suite/os-widgets-windows/actions/workflows/windows-release.yml/badge.svg)](https://github.com/Comet-Suite/os-widgets-windows/actions/workflows/windows-release.yml)
[![Release](https://img.shields.io/github/v/release/Comet-Suite/os-widgets-windows?label=release&color=2490ee)](https://github.com/Comet-Suite/os-widgets-windows/releases/latest)
[![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-2490ee?logo=windows11&logoColor=white)](#requirements)

OS Widgets puts clocks, system information, news, music controls, goals, a calendar, and short quotes directly on the Windows desktop.

[Download](https://github.com/Comet-Suite/os-widgets-windows/releases/latest) · [Screenshots](#screenshots) · [Wallpapers](#wallpapers) · [Report a problem](https://github.com/Comet-Suite/os-widgets-windows/issues)

</div>

## Screenshots

<div align="center">
  <img src="docs/screenshots/os-widgets-showcase.gif" alt="OS Widgets screenshot tour" width="100%">
</div>

## Download

The [latest release](https://github.com/Comet-Suite/os-widgets-windows/releases/latest) provides two Windows x64 packages:

- **Setup:** `OS-Widgets-1.2.0-Windows-x64-Setup.exe`
- **Portable:** `OS-Widgets-1.2.0-Windows-x64-Portable.zip`

The installer is recommended. It installs for the current user and can add desktop and startup shortcuts. The first installed launch deliberately starts with the default configuration instead of reusing settings from a Python/source run.

Release downloads include `SHA256SUMS.txt`. The executables are not Authenticode-signed, so Windows SmartScreen may show a reputation warning. Verify the checksum before running a download.

## Features

| Area | Included |
|---|---|
| Clocks | Four local/world clocks, analog or digital, time zones, 12/24-hour format |
| System monitor | CPU, GPU, RAM, network, Windows volumes, and battery status |
| News | RSS headlines, article images, categories, caching, and offline state |
| Music | Local playlist, playback, seeking, volume, and cover image |
| Goal | Countdown in days, hours, minutes, and seconds with optional artwork |
| Calendar | Month navigation and dated to-do items with completion state |
| Quotes | Offline built-in and custom quotes in an ultra-mini card |
| Appearance | Light/dark theme, colors, opacity, flat cards, and size presets |

Music, Goal, Calendar, and Quotes are disabled by default. They do not create widget windows or timers until enabled.

## Requirements

- Windows 10 or Windows 11, 64-bit
- Windows Media Foundation codecs for music playback
- Internet access only for News

## Run from source

Python 3.10 or newer is required.

```powershell
git clone https://github.com/Comet-Suite/os-widgets-windows.git
cd os-widgets-windows
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
pyw os_widgets.py
```

Use `py os_widgets.py` instead when console output is useful for troubleshooting.

## Using the app

1. Open **Settings** from the tray icon.
2. Enable the widgets you want.
3. Drag a widget by its header area.
4. Resize from the lower-right corner.
5. Right-click for size, opacity, lock, refresh, and placement controls.

Settings and caches are stored under `%LOCALAPPDATA%\OS Widgets`.

## Image sizes

- Music cover: **600 × 600 px** (1:1)
- Goal image: **1200 × 800 px** (3:2)

PNG and JPG work well for both.

## Wallpapers

Matching dark and light wallpapers are included in [`wallpapers/`](wallpapers/README.md).

| Theme | Desktop 4K | Portrait |
|---|---|---|
| Dark | [3840 × 2160](wallpapers/os-widgets-dark-16x9-4k.jpg) | [2160 × 3840](wallpapers/os-widgets-dark-9x16-portrait.jpg) |
| Light | [3840 × 2160](wallpapers/os-widgets-light-16x9-4k.jpg) | [2160 × 3840](wallpapers/os-widgets-light-9x16-portrait.jpg) |

## Privacy

OS Widgets has no account system, telemetry, or advertising. Calendar, goal, quote, and music data stay on the computer. Only the News widget contacts the configured RSS and image sources.

## Build the Windows packages

The Windows build uses PyInstaller and Inno Setup 6:

```powershell
.\packaging\build-windows.ps1
```

A `v*` tag runs the same build through GitHub Actions and publishes the installer, portable ZIP, and checksum file.

## Project files

```text
os_widgets.py              Application source
motivational-quotes.txt    Built-in quote list in text form
assets/                    Windows icon
packaging/          PyInstaller and Inno Setup files
wallpapers/         Desktop and portrait backgrounds
```

## License

No open-source license has been granted. All rights remain with the repository owner.
