# Contributing to OS Widgets

Thanks for helping make OS Widgets more polished, lightweight, and useful!

## Development setup

```powershell
git clone https://github.com/Comet-Suite/os-widgets-windows.git
cd os-widgets-windows
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
pyw os_widgets.py
```

- Use `py os_widgets.py` for console logs.
- Single-file design: all logic lives in `os_widgets.py`.
- Settings stored in `%LOCALAPPDATA%\OS Widgets\settings.json`.

## Project principles

- **Single file** — keep the app in one Python file for portability.
- **Lazy loading** — converter engines (Pillow, FFmpeg, docx, etc.) must not load at idle.
- **Offline-first** — no telemetry, no ads, no accounts. News/Weather are the only network features.
- **Windows-native** — use Win32 APIs where more accurate (disk, battery, GPU PDH, startup, DPI).
- **Lightweight** — prefer coarse/very-coarse timers, shared timers, capped caches, adaptive history sizes.

## What to work on

- New useful widgets (keep idle cost near zero)
- Converter format coverage and quality presets
- Appearance customization that doesn't bloat
- Performance diagnostics and bug fixes
- Documentation and screenshots

## Code style

- Python 3.10+ compatible, type hints where helpful
- Keep widget classes inheriting `BaseWidget`
- Use `awesome_icon()` with fallback vector icons
- Use `QTimer` with `CoarseTimer` or `VeryCoarseTimer` for background work
- Use `manager.executor` for blocking I/O
- Update `default_settings()` and `deep_merge` handling for new configs
- Bump `SETTINGS_SCHEMA_VERSION` only when breaking old settings

## Testing

```powershell
py -m py_compile os_widgets.py
py os_widgets.py --package-self-test --expect-defaults
py os_widgets.py --converter-package-self-test C:\Temp\converter-test
py os_widgets.py --context-menu-self-test
```

For UI, run with console and check tray → Diagnostics → Run diagnostics.

## Pull requests

1. Fork and create a feature branch.
2. Keep changes focused and documented.
3. Update `CHANGELOG.md` and `README.md` if user-facing.
4. Ensure `os_widgets.py` compiles and self-tests pass.
5. Attach screenshots for UI changes.

## Reporting issues

Use GitHub Issues with:

- Windows version, OS Widgets version, steps to reproduce
- `settings.json` snippet (remove private paths)
- Diagnostics report (Settings → Diagnostics → Copy report)

## Security

See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree your contributions are under the MIT license.
