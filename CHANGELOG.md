# Changelog

All notable changes to OS Widgets are documented here.

## [1.2.0-rc.8] — 2026-08-21

### Added

- Compact calendar widget with month navigation, today highlighting, selected-date state, and task dots
- Persistent dated to-do items with add, complete, reopen, and remove operations
- Calendar task management in Settings
- Ultra-mini motivational-quotes widget with bundled and custom offline quotes
- Configurable very-coarse quote rotation and manual next-quote action
- Music Player cover recommendation: 600 × 600 px, square 1:1
- Goal Countdown artwork recommendation: 1200 × 800 px, landscape 3:2
- Professional Windows installer and portable-package automation

### Performance

- Calendar and Quotes remain disabled by default
- Calendar uses an hourly very-coarse refresh
- Quotes use one configurable very-coarse timer and no network requests

### Validation

- 14/14 RC8 functional checks passed in the Qt offscreen harness
- Native Windows multimedia output and Windows-only API behavior remain release-gating checks

## [1.2.0-rc.7]

### Added

- Local Music Player with playlist, transport, seek, volume, and optional cover art
- Goal Countdown with days, hours, minutes, seconds, custom message, and optional image
- Shared desktop-level maintenance timer and additional performance modes

## [1.1.0-rc.6]

### Added

- Per-partition storage rows with internal scrolling
- Accurate laptop battery state and explicit no-battery desktop state
- Expanded Windows Diagnostics checks
