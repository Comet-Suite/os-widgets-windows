# OS Widgets 1.4.0 — Final stable

OS Widgets 1.4.0 is the final polished release — lighter, more customizable, and now with code conversion and 3 new useful widgets.

## Downloads

- `OS-Widgets-1.4.0-Windows-x64-Setup.exe` — per-user installer
- `OS-Widgets-1.4.0-Windows-x64-Portable.zip` — portable
- `SHA256SUMS.txt` — checksums

Verify SHA-256 before running. Unsigned builds may trigger SmartScreen → More info → Run anyway after verification.

## What's new

### Code Converter — 35+ languages
**100+ source extensions, 60+ output formats**

- Python, JavaScript/TypeScript, Java, C/C++, C#, Go, Rust, PHP, Ruby, Swift, CSS/SCSS, SQL, Shell, PowerShell, Jupyter and more
- Convert any code file to TXT, Markdown (fenced), HTML (styled), PDF, DOCX, RTF, ODT, EPUB, PY, JS, IPYNB, JSON
- `notebook.ipynb ↔ script.py` — extract cells / create notebook
- JSON pretty/minify, JS/CSS minify in Fast mode, same-extension formatting
- Example: right-click `app.py` → OS Widgets → Convert to Markdown / HTML / Jupyter notebook

### New widgets

- **Weather** — city search, °C/°F, condition icons (cloud-sun, rain, snow...), humidity/wind, 30-min refresh, offline "You're not connected"
- **Quick Notes** — sticky notes, auto-save 0.8s, title edit, font size, char/word count, 10k limit
- **Focus Timer** — Pomodoro 25/5/15, cycles, auto-start toggles, progress bar, cycle dots, beep on completion

All disabled by default — no cost until enabled.

### Lighter & faster

- News cache 80→50 files, 48→32 MB, refresh 15→30 min
- Quotes 5→15 min, CPU history 60→40 Eco / 80 Responsive
- Clock without seconds: 5s Balanced, 10s Eco
- Desktop maintenance: 6s Balanced, 12s Eco (single shared timer)
- Converter engines lazy-loaded, compact mode, border toggle, font scale 90-130%
- GraphWidget adaptive, QPixmapCache, VeryCoarseTimer where possible

### More customization

- Font scale, compact mode, widget border toggle, reduce-motion-on-battery
- Per-widget accent still via custom widget colors, plus square/soft/rounded corners, 4 size presets, opacity
- Settings nav now 15 pages with Weather/Notes/Timer

### Fixes & polish

- Disk: native `GetDiskFreeSpaceExW` + volume GUID dedup, matches Explorer, one-decimal %
- CPU: `GetSystemTimes` deltas with burst guard, GPU PDH busiest-engine
- Icons: embedded fallback vectors — no Font Awesome font dependency
- Shadows removed, UTC offset hidden, DPI-aware per-monitor V2, clean installer reset validated for new widgets

## File Converter matrix

| Family | Formats |
|---|---|
| Images | PNG, JPEG, WebP, AVIF, HEIC, JPEG 2000, BMP, TIFF, GIF, ICO, TGA, PCX, PPM, PGM, PBM, DDS, PDF |
| Documents | TXT, MD, HTML, DOCX, PDF, RTF, ODT, EPUB, PPTX text extraction |
| Data | CSV, JSON, XLSX, XML, YAML, TOML, ODS, PDF |
| Code | PY, JS, TS, JAVA, C, CPP, CS, GO, RS, PHP, RB, SWIFT, CSS, IPYNB, JSON, SH, PS1, SQL + 30 more → TXT/MD/HTML/PDF/DOCX/JS/PY/IPYNB/JSON |
| Audio | MP3, WAV, FLAC, OGG, M4A, Opus, AIFF, AC-3, WMA |
| Video | MP4, MKV, AVI, MOV, WebM, MPEG, FLV, OGV, 3GP, TS + MP3/WAV |

Quality: Fast (lower CPU, minified), Balanced, High.

## Build & verification

Workflow validates: clean installer state (no inherited geometries, music/goal/calendar/quotes/weather/notes/timer disabled), Windows volume APIs, 100+ extensions registration via shared CommandStore (177 keys), image+code+doc+table+audio+video conversions, context-menu self-test, Authenticode diagnostics.

See `docs/CODE_SIGNING.md` for trusted signing.

## Previous releases

- v1.3.0 — file converter (images/docs/tables/audio/video)
- v1.2.0 — first stable widgets release

---

Full changelog: [CHANGELOG.md](https://github.com/Comet-Suite/os-widgets-windows/blob/main/CHANGELOG.md)
