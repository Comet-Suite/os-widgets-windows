# OS Widgets 1.2.0

The first stable release of OS Widgets for Windows 10 and Windows 11.

## Downloads

- `OS-Widgets-1.2.0-Windows-x64-Setup.exe` — current-user installer
- `OS-Widgets-1.2.0-Windows-x64-Portable.zip` — portable build
- `SHA256SUMS.txt` — download verification

## Included

- Four configurable analog or digital clocks
- CPU, GPU, RAM, network, disk-volume, and battery monitoring
- News slider with article images and offline handling
- Local Music Player
- Goal Countdown
- Calendar with dated to-do items
- Offline motivational quotes
- Themes, colors, opacity, flat widget cards, and four size presets
- Performance alerts, custom alert sounds, and Windows diagnostics

## Stable-release changes

- Removed the painted background shadow from every widget
- Removed UTC offset small print from clock cards
- Updated Settings navigation, page icons, controls, and scrollbars
- Switched Windows disk occupancy to native Windows volume APIs with one-decimal precision
- Added an installer reset marker so the installed app starts with default settings rather than source-run preferences
- Added a packaged Windows self-test for default-state reset and volume detection

## Verification

The release workflow compiles the source, builds the x64 executable, runs the packaged self-test on Windows, creates both packages, and publishes SHA-256 checksums.

The executables are currently unsigned. Windows SmartScreen may display a reputation warning; verify the checksum before running a download.
