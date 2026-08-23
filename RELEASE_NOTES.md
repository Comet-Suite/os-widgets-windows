# OS Widgets 1.3.0

This release adds an optional Windows Explorer file converter while keeping the desktop widgets and previous 1.2.0 release available.

## Downloads

- `OS-Widgets-1.3.0-Windows-x64-Setup.exe`
- `OS-Widgets-1.3.0-Windows-x64-Portable.zip`
- `SHA256SUMS.txt`

## File Converter

Enable it from **Settings → File Converter**. Supported file extensions receive an **OS Widgets** submenu in Windows Explorer with only the valid output formats for that source type. Converted files are saved in the source folder with collision-safe names.

![File Converter settings](https://raw.githubusercontent.com/Comet-Suite/os-widgets-windows/main/docs/screenshots/file-converter-settings.png)

![Format-aware context submenu](https://raw.githubusercontent.com/Comet-Suite/os-widgets-windows/main/docs/screenshots/context-menu-preview.png)

### Included formats

- Images: PNG, JPEG, WebP, BMP, TIFF, GIF, ICO, PDF
- Documents: TXT, Markdown, HTML, DOCX, PDF, PPTX text extraction
- Tables: CSV, JSON, XLSX, PDF
- Audio: MP3, WAV, FLAC, OGG, M4A
- Video: MP4, MKV, AVI, MOV, WebM, MP3, WAV

Media conversion uses the FFmpeg binary bundled through imageio-ffmpeg. Office conversions preserve document content but may simplify advanced layouts.

## Other changes

- Added File Converter status and dependency checks to Diagnostics
- Added automatic cleanup of Explorer menu entries during uninstall
- Added a dedicated conversion progress window and Open folder action
- Added collision-safe output naming; source files are never overwritten
- Converter libraries load only when a conversion is requested

## Verification

The Windows workflow builds the executable, verifies the clean installer state, performs real packaged image/document/table/audio conversions, registers and removes the Explorer submenu in a self-test, builds the installer and portable archive, and publishes SHA-256 checksums.

The executables are not Authenticode-signed. Windows SmartScreen may display a reputation warning; verify the release checksum before running a download.
