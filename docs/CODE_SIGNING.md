# Windows code signing and SmartScreen — OS Widgets v1.4.0 FINAL

Contact: m39776401@gmail.com

Windows SmartScreen recognition cannot be declared by an application. It depends on a valid Authenticode signature and reputation managed by Microsoft.

The build workflow supports signing but does not contain a certificate. Unsigned builds continue to work and are clearly reported as unsigned in the build log.

## GitHub configuration

Create these repository secrets:

- `WINDOWS_SIGNING_CERT_BASE64` — Base64-encoded PFX certificate
- `WINDOWS_SIGNING_CERT_PASSWORD` — PFX password

Optional repository variable:

- `WINDOWS_SIGNING_TIMESTAMP_URL` — RFC 3161 timestamp server; defaults to `http://timestamp.digicert.com`

Example conversion of a PFX to Base64 in PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("certificate.pfx")) | Set-Clipboard
```

Never commit a PFX file or its password to the repository.

## Build behavior

When the secrets are available, `packaging/build-windows.ps1`:

1. Decodes the certificate into the temporary runner directory.
2. Signs `OS-Widgets.exe` with SHA-256 and an RFC 3161 timestamp.
3. Verifies the executable with `signtool verify /pa` and `Get-AuthenticodeSignature`.
4. Builds the installer around the signed executable.
5. Signs and verifies the installer.
6. Removes the temporary PFX.

The Diagnostics page checks the installed executable's Authenticode status. It can confirm whether a trusted signature is valid, but it cannot query or force Microsoft's SmartScreen reputation score.

## Certificate choice

An EV code-signing certificate generally receives SmartScreen trust sooner. A standard organization-validated certificate may need to build reputation over time. Self-signed certificates do not provide public SmartScreen recognition.
