# Changelog

## 1.3.0 — 2026-08-23

### Added

- Optional format-aware OS Widgets submenu in Windows Explorer
- Image, document, table, audio, and video conversion
- Same-folder collision-safe output naming
- Conversion progress and completion window
- File Converter Settings and Diagnostics sections
- Packaged converter and context-menu self-tests

### Packaging

- Bundled FFmpeg through imageio-ffmpeg
- Added third-party notices
- Explorer integration is removed during uninstall

## 1.2.0 — 2026-08-21

First stable Windows release.

### Widgets

- Four analog or digital clocks
- System monitor for CPU, GPU, RAM, network, Windows volumes, and battery
- News, Music Player, Goal Countdown, Calendar with to-do items, and Quotes
- Four size presets, opacity controls, themes, and custom colors

### Stable-release fixes

- Removed background shadows from every desktop widget
- Removed UTC offset text from clock cards
- Updated Settings navigation, icons, and scrollbars
- Switched disk occupancy to native Windows volume APIs
- Added one-decimal disk percentages and smoother row updates
- Added a clean installed-first-launch reset

### Distribution

- Windows x64 installer
- Portable Windows x64 package
- Packaged Windows self-test
- SHA-256 checksum manifest
