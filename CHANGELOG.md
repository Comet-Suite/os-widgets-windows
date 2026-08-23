# Changelog

## Unreleased — 1.4 development

- Expanded File Converter support to 77 recognized source extensions and 50 output formats
- Added AVIF, HEIC, JPEG 2000, OpenDocument, EPUB, XML, YAML, TOML, Opus, AIFF, AC-3, MPEG, FLV, OGV, 3GP, and TS support
- Added Fast, Balanced, and High conversion quality presets
- Added optional Authenticode signing and verification for the EXE and installer
- Added an Authenticode and SmartScreen-readiness Diagnostics check
- Reduced background network, battery, clock, and desktop-level maintenance work
- Updated the converter Settings and progress UI

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
