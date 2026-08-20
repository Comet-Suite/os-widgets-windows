# OS Widgets 1.2.0 RC8

A polished release candidate for Windows 10 and Windows 11.

## Release status

| Check | Result |
|---|---|
| Windows x64 build | **✅ Passing** |
| Installer and portable packages | **✅ Published** |
| Published SHA-256 checksums | **✅ Verified** |
| RC8 functional test suite | **✅ 14/14 passed** |

[View the successful Windows build](https://github.com/Comet-Suite/os-widgets-windows/actions/runs/32405047343)

![OS Widgets screenshot showcase](https://raw.githubusercontent.com/Comet-Suite/os-widgets-windows/main/docs/screenshots/os-widgets-showcase.gif)

## New in RC8

- Calendar widget with month navigation, today highlighting, selected-date state, and task indicator dots
- Persistent dated to-do items with add, complete, reopen, and remove controls
- Ultra-mini offline motivational-quotes widget with custom quotes and slow rotation
- Explicit image guidance for Music Player covers and Goal Countdown artwork
- Continued low-resource behavior: Calendar and Quotes remain disabled by default

## Windows downloads

- **Setup:** `OS-Widgets-1.2.0-rc.8-Windows-x64-Setup.exe`
- **Portable:** `OS-Widgets-1.2.0-rc.8-Windows-x64-Portable.zip`
- **Integrity:** verify downloads using `SHA256SUMS.txt`

## Important RC notice

This is a pre-release build. Native Windows multimedia playback and Windows-specific integration should still be validated on representative physical Windows 10/11 hardware before a stable release.

The executable is not code-signed, so Microsoft Defender SmartScreen may display a reputation warning. Verify the SHA-256 checksum before running it.
