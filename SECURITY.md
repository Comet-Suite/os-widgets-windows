# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.4.0 | ✅ |
| 1.3.0 | ✅ |
| 1.2.0 | ✅ |
| <1.2.0 | ❌ |

## Reporting a vulnerability

If you find a security issue (e.g., unsafe file handling, registry injection, network request issue):

1. **Do not** open a public issue.
2. Email: **m39776401@gmail.com** (or open a private security advisory on GitHub).
3. Include: OS Widgets version, Windows version, reproduction steps, impact.

We aim to acknowledge within 72 hours and release a fix within 14 days for critical issues.

## Security design

- No elevated privileges — installer uses `PrivilegesRequired=lowest`
- File converter writes only beside source, never overwrites without `-converted` suffix
- Context menu uses `HKEY_CURRENT_USER` (per-user) and `CommandStore` shared commands
- Network: only News RSS/image and Weather wttr.in — both use HTTPS, timeouts, size caps
- Image cache: capped 50 files / 32 MB, LRU pruning, no executable content
- No auto-update, no remote code execution, no telemetry

## SmartScreen & signing

Builds support Authenticode signing via GitHub Secrets. Unsigned builds are expected to trigger SmartScreen until reputation builds. Always verify `SHA256SUMS.txt`.

See [docs/CODE_SIGNING.md](docs/CODE_SIGNING.md).
