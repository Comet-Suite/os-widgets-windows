# Security Policy

## Supported versions

OS Widgets is currently a release candidate. Security fixes are applied to the newest RC branch only.

| Version | Supported |
|---|---|
| 1.2.0 RC8 | Yes |
| Earlier release candidates | No |

## Reporting a vulnerability

Please avoid posting sensitive vulnerability details in a public issue. Contact the repository owner through GitHub and provide:

- A clear description of the issue
- Reproduction steps
- Affected Windows and Python versions
- Any proof-of-concept files or logs with personal data removed
- Your assessment of impact

Allow reasonable time for investigation before public disclosure.

## Download integrity

Official Windows release assets include `SHA256SUMS.txt`. Verify the downloaded installer or portable ZIP before running it.

The current RC executables are not Authenticode-signed. Microsoft Defender SmartScreen may therefore show a reputation warning. A warning is not proof of malware, but users should download only from this repository and verify the published SHA-256 checksum.
