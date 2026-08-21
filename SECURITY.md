# Security Policy

## Supported versions

Security fixes are applied to the latest stable release.

| Version | Supported |
|---|---|
| 1.2.x | Yes |
| Release candidates | No |

## Reporting a vulnerability

Do not post sensitive vulnerability details in a public issue. Contact the repository owner through GitHub with:

- A description of the issue
- Reproduction steps
- Affected Windows and Python versions
- Logs with personal data removed
- Expected impact

Please allow time for investigation before public disclosure.

## Download integrity

Windows releases include `SHA256SUMS.txt`. Download packages only from this repository and verify the relevant checksum before running them.

The current executables are not Authenticode-signed, so Microsoft Defender SmartScreen may show a reputation warning.
