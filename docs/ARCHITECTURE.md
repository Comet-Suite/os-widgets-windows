# Architecture — OS Widgets 1.4.0 FINAL

Contact: m39776401@gmail.com

OS Widgets is a **single-file** Windows desktop app (`os_widgets.py`, ~369 KB) built with PySide6. Version 1.4.0 FINAL.

## Single-file principles

- No package, no entry points — `pyw os_widgets.py` or `OS-Widgets.exe`
- Lazy imports for heavy deps (Pillow, FFmpeg, docx, etc.) only inside converter functions
- Settings in `%LOCALAPPDATA%\OS Widgets\settings.json` with schema versioning
- One-shot installer marker `.reset-on-next-launch` ensures clean first launch (no inherited geometries)

## Core classes

| Class | Role |
|---|---|
| `BaseWidget` | Frameless Tool window, drag/resize, opacity, size presets, desktop-level Z-order, hover menu |
| `AnalogClockFace` | Custom paint for analog clocks |
| `ClockWidget` | 4 clocks, digital/analog, timezone via `zoneinfo` or fallback offsets |
| `CPUWidget` | 6 slides: CPU (GetSystemTimes), GPU (PDH busiest engine), RAM, Wi-Fi rates, Disks (GetDiskFreeSpaceExW per volume + scrollbar), Battery (psutil + GetSystemPowerStatus) |
| `WeatherWidget` | City + units, wttr.in JSON, offline handling, condition icons, coarse timer 30 min |
| `NotesWidget` | QPlainTextEdit, auto-save 0.8s, title edit, char/word count |
| `TimerWidget` | Pomodoro, work/break/long-break, cycles, progress 0-1000, 1s timer only while running |
| `MusicWidget` | QMediaPlayer + QAudioOutput, playlist, cover 600×600 |
| `GoalCountdownWidget` | Days/hours/min/sec, optional image 1200×800 |
| `CalendarWidget` + `CalendarGridWidget` | Month grid, to-do dots, add/toggle via dialog |
| `QuoteWidget` | Ultra-mini rotation, built-in + custom, VeryCoarseTimer |
| `NewsWidget` + `NewsImage` + `NewsBridge` | RSS, Google News decoding, article image resolver (JSON-LD, srcset, reader fallback), image cache 50/32 MB, slider |
| `WidgetManager` | Creates enabled widgets, tray menu, shared clock timer, desktop-level timer, executor (3 workers), performance alerts |
| `SettingsPanel` | 15 pages, scroll areas, controls dict, save merges via deep_merge |

## Timers & efficiency

- **Clock timer:** shared, 1s when any clock shows seconds, else 5s Balanced / 10s Eco / 2s Responsive
- **Desktop level:** shared VeryCoarseTimer, 6s Balanced, 12s Eco, 3s Responsive — calls `keep_at_desktop_level()` which uses `GetWindow(GW_HWNDPREV)` to insert above wallpaper but below normal windows
- **CPUWidget:** sampling interval from settings (0.5-5s), Eco min 3s; network 10s background, battery 30s, disks 5s on Disks page / 30s elsewhere, GPU PDH 5s when alerts enabled
- **News:** refresh 30 min default, slide 8s, image fetch via QNetworkAccessManager, cache pruning LRU
- **Weather:** 30 min, executor + bridge
- **Quotes:** VeryCoarseTimer 15 min default
- **Notes:** save timer 800ms single-shot
- **Timer:** 1s CoarseTimer only while running

## File converter

- **Extensions:** `IMAGE_EXTENSIONS`, `TEXT_EXTENSIONS`, `DOCUMENT_EXTENSIONS`, `DATA_EXTENSIONS`, `AUDIO_EXTENSIONS`, `VIDEO_EXTENSIONS`, `CODE_EXTENSIONS` → `CONVERTER_SOURCE_EXTENSIONS` sorted (100+ in 1.4.0)
- **Targets:** `converter_targets_for()` returns format-aware list; code files allow same-extension for minify/beautify
- **Functions:** `_convert_image`, `_convert_code`, `_convert_table`, `_convert_text_document`, `_convert_media` (FFmpeg via imageio-ffmpeg)
- **Quality:** `converter_quality_preset()` Fast/Balanced/High affects JPEG quality, WebP method, AVIF speed, x264 preset/crf, JSON indent, JS/CSS minify
- **Output:** `converter_output_path()` collision-safe `-converted` suffix
- **Registry:** `CommandStore` shared commands (`OSWidgets.convert.<fmt>`) + per-extension `SubCommands` filtered list — compact (177 keys for 50 formats)
- **UI:** `FileConversionDialog` with progress, open folder

## Appearance

- `app_stylesheet()` uses `font_scale` (90-130%), accent colors, transparency, compact mode
- `widget_palette_colors()` respects `widget_border` toggle and custom colors
- `widget_corner_radius()` rounded/soft/square
- Icons via `qtawesome` with `fallback_vector_icon()` embedded (no font dependency)

## Diagnostics

`run_windows_diagnostics()` checks platform, signature (Get-AuthenticodeSignature), GPU PDH, disks (Windows volume API), battery, startup (HKCU Run), desktop host (SHELLDLL_DefView), DPI (per-monitor), temperature providers (LibreHardwareMonitor/OpenHardwareMonitor/ACPI), notifications, audio ring, storage, converter menu, dependencies, footprint.

## Build

- `packaging/os-widgets.spec` — PyInstaller one-file, collects qtawesome, ffmpeg, heif, avif, tzdata, hidden imports QtMultimedia
- `packaging/build-windows.ps1` — pip install, pyinstaller, self-tests (package, converter, context-menu, reset marker), optional Authenticode signing, portable ZIP + installer via Inno Setup, SHA256SUMS
- Workflow `.github/workflows/windows-release.yml` — manual dev + tag release, optional signing secrets, artifact upload

## Data flow

```
SettingsStore.load() → default_settings() + deep_merge → STORE.data
WidgetManager.create_enabled_widgets() → ensure_widget() → restore_geometry() → show()
Timers → sample() / tick_clocks() / maintain_desktop_level()
SettingsPanel → draft copy → controls → save_changes() → deep_merge → STORE.save() → manager.apply_settings()
Converter → right-click → --convert-to → FileConversionDialog → convert_file() → output beside source
```

## Why single file?

- Easy to audit, copy, and run
- No install step for source users
- PyInstaller packaging is straightforward
- Keeps import graph explicit and lazy-loading obvious
