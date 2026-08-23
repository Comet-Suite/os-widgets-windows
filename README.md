<div align="center">
  <img src="docs/brand/readme-hero.svg" alt="OS Widgets — Your desktop. Your widgets." width="100%">
</div>

<div align="center">

[![Windows build](https://github.com/Comet-Suite/os-widgets-windows/actions/workflows/windows-release.yml/badge.svg)](https://github.com/Comet-Suite/os-widgets-windows/actions/workflows/windows-release.yml)
[![Release](https://img.shields.io/github/v/release/Comet-Suite/os-widgets-windows?label=release&color=2490ee)](https://github.com/Comet-Suite/os-widgets-windows/releases/latest)
[![Windows 10/11](https://img.shields.io/badge/Windows-10%20%7C%2011-2490ee?logo=windows11&logoColor=white)](#requirements)

OS Widgets adds configurable desktop widgets and an optional right-click file converter to Windows.

[Download](https://github.com/Comet-Suite/os-widgets-windows/releases/latest) · [Screenshots](#screenshots) · [Wallpapers](#wallpapers) · [Report a problem](https://github.com/Comet-Suite/os-widgets-windows/issues)

</div>

> **Development status:** `main` contains the unreleased 1.4 development work. The latest public package remains OS Widgets 1.3.0; no new release has been created for these changes.

## Screenshots

<div align="center">
  <img src="docs/screenshots/os-widgets-showcase.gif" alt="OS Widgets screenshot tour" width="100%">
</div>

## Download

The [latest release](https://github.com/Comet-Suite/os-widgets-windows/releases/latest) provides two Windows x64 packages:

- **Setup:** `OS-Widgets-1.3.0-Windows-x64-Setup.exe`
- **Portable:** `OS-Widgets-1.3.0-Windows-x64-Portable.zip`

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
| File Converter | Format-aware Explorer submenu for images, documents, tables, audio, and video |
| Appearance | Light/dark theme, colors, opacity, flat cards, and size presets |

Music, Goal, Calendar, Quotes, and File Converter integration are disabled by default. They do not create widget windows, timers, or Explorer entries until enabled.

## File Converter

Enable **Settings → File Converter → Enable OS Widgets in the Windows file context menu**, then save. Right-click a supported file and open **OS Widgets** to see only the output formats available for that extension. The converted file is written to the same folder; existing files are never overwritten.

<div align="center">
  <img src="docs/screenshots/file-converter-settings.png" alt="File Converter settings" width="62%">
</div>

<div align="center">
  <img src="docs/screenshots/context-menu-preview.png" alt="OS Widgets format-aware context submenu" width="42%">
  <img src="docs/screenshots/conversion-complete.png" alt="Completed file conversion" width="42%">
</div>

The unreleased development build recognizes **77 source extensions** and offers **50 output formats**.

| Source family | Output formats |
|---|---|
| Images | PNG, JPEG, WebP, AVIF, HEIC, JPEG 2000, BMP, TIFF, GIF, ICO, TGA, PCX, PPM, PGM, PBM, DDS, PDF |
| Text and documents | TXT, Markdown, HTML, DOCX, PDF, RTF, ODT, EPUB; text extraction from PDF and PPTX |
| Tables and data | CSV, JSON, XLSX, XML, YAML, TOML, ODS, PDF |
| Audio | MP3, WAV, FLAC, OGG, M4A, Opus, AIFF, AC-3, WMA |
| Video | MP4, MKV, AVI, MOV, WebM, MPEG, FLV, OGV, 3GP, TS, MP3, WAV |

Media conversion uses the packaged FFmpeg engine. Office conversions preserve content but may simplify complex layouts. On Windows 11, extension-based commands may appear under **Show more options**. Three quality modes let users trade conversion speed and hardware use for output quality.

## Requirements

- Windows 10 or Windows 11, 64-bit
- Windows Media Foundation codecs for music playback
- Approximately 500 MB free space for the installed package
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

OS Widgets has no account system, telemetry, or advertising. Calendar, goal, quote, music, and file conversion data stay on the computer. Only the News widget contacts the configured RSS and image sources.

## Hardware use

Converter engines remain unloaded until a conversion starts. The development build also uses adaptive clock timing, a slower desktop-level maintenance interval, ten-second background network sampling, and thirty-second battery sampling. **Fast** conversion quality lowers encoder work for large media files.

## SmartScreen and code signing

The build pipeline now supports Authenticode signing for both the application and installer and verifies signatures before packaging. A trusted certificate is not stored in this repository, so public SmartScreen recognition is not claimed. See [`docs/CODE_SIGNING.md`](docs/CODE_SIGNING.md) for the required GitHub Secrets and signing process.

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
packaging/                 PyInstaller and Inno Setup files
docs/screenshots/          Product screenshots
wallpapers/                Desktop and portrait backgrounds
```

## License

No open-source license has been granted. All rights remain with the repository owner.
