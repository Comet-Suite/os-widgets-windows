# Changelog

## 1.4.0 — 2026-09-20 — Final stable

### Added
- **Code Converter** — new family with 35+ programming extensions (Python, JavaScript/TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, CSS/SCSS, SQL, Shell, PowerShell, Jupyter and more)
- Code outputs: TXT, Markdown (fenced), HTML (styled <pre>), PDF, DOCX, RTF, ODT, EPUB, PY, JS, IPYNB, JSON with minify/beautify
- Python ↔ Jupyter notebook conversion (extract cells / create notebook)
- JSON pretty/minify, JS/CSS minify in Fast quality preset
- **Weather widget** — city-based, metric/imperial, condition icons, humidity/wind, wttr.in JSON (no API key), offline "You're not connected" state, 30-min refresh
- **Quick Notes widget** — auto-save 0.8s debounce, title edit, font size, char/word count, 10k limit, local storage
- **Focus Timer widget** — Pomodoro work/break/long-break, cycles, auto-start toggles, progress bar, cycle dots, beep, 1s coarse timer only while running
- Appearance: font scale (90/100/115/130%), compact mode, widget border toggle, reduce-motion-on-battery
- Converter stats now show 100+ extensions and 60+ formats in UI

### Improved
- **Lightweight:** news image cache 80→50 files, 48→32 MB; CPU history 60→40 Eco, 80 Responsive; GraphWidget adaptive; news default 15→30 min; quotes default 5→15 min; clock without seconds 5s Balanced / 10s Eco; desktop maintenance 6s Balanced / 12s Eco
- **Customization:** widget_palette_colors respects border toggle; app_stylesheet respects font_scale; compact mode reduces padding and increases min timer interval
- **Stability:** fallback vector icons for every FA name (no font dependency), native Windows volume APIs with volume GUID dedup, PDH GPU busiest-engine grouping, temperature diagnostics with provider names, DPI awareness per-monitor V2, single shared desktop-level timer
- **UI:** file converter groups now include Code card with `fa6s.code` icon; settings nav adds Weather/Notes/Timer with icons; page shells include new icon map
- **Build:** version bumped to 1.4.0 across spec, ISS, version_info, ps1; converter self-test now requires 100+ extensions and 60+ formats and tests 6 code conversions

### Fixed
- Settings icons not appearing on systems without Font Awesome — now always has embedded fallback
- Disk occupancy now uses `GetDiskFreeSpaceExW` total-free (matches Explorer) with correct one-decimal percent
- CPU uses `GetSystemTimes` deltas with wall-time guard (<0.2s burst ignored) — matches Task Manager
- News offline state shows "You're not connected" consistently
- Reset-on-next-launch marker consumed and default state validated (music/goal/calendar/quotes/weather/notes/timer disabled, no geometries, converter disabled)

### Packaging
- Installer and portable now labeled 1.4.0, SHA256SUMS updated
- No new runtime dependencies for code converter (pure Python)
- Spec still collects heif/avif/qtawesome/ffmpeg/tzdata

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

## 1.2.0 — 2026-08-21 — First stable Windows release

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
