$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Version = "1.2.0"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean packaging/os-widgets.spec

# Verify the packaged executable on the Windows runner. The fake previous
# settings plus installer marker must resolve to a clean default configuration.
$OriginalLocalAppData = $env:LOCALAPPDATA
$SmokeRoot = Join-Path $Root "smoke-data"
$SmokeState = Join-Path $SmokeRoot "OS Widgets"
Remove-Item $SmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item $SmokeState -ItemType Directory -Force | Out-Null
'{"version":2,"appearance":{"theme":"dark"},"widgets":{"music":{"enabled":true,"playlist":["old.mp3"],"geometry":[1,2,3,4]}}}' | Set-Content (Join-Path $SmokeState "settings.json") -Encoding UTF8
Copy-Item "packaging/reset-on-next-launch" (Join-Path $SmokeState ".reset-on-next-launch")
try {
  $env:LOCALAPPDATA = $SmokeRoot
  $Process = Start-Process -FilePath "dist/OS-Widgets.exe" -ArgumentList "--package-self-test","--expect-defaults" -Wait -PassThru
  if ($Process.ExitCode -ne 0) { throw "Packaged self-test failed with exit code $($Process.ExitCode)." }
  if (Test-Path (Join-Path $SmokeState ".reset-on-next-launch")) { throw "Reset marker was not consumed." }
  $Saved = Get-Content (Join-Path $SmokeState "settings.json") -Raw | ConvertFrom-Json
  if ($Saved.widgets.music.enabled -or $Saved.widgets.music.playlist.Count -ne 0) { throw "Installer reset state was not saved." }
} finally {
  $env:LOCALAPPDATA = $OriginalLocalAppData
  Remove-Item $SmokeRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$Release = Join-Path $Root "release"
$Portable = Join-Path $Root "portable"
Remove-Item $Release,$Portable -Recurse -Force -ErrorAction SilentlyContinue
New-Item $Release,$Portable -ItemType Directory -Force | Out-Null
Copy-Item "dist/OS-Widgets.exe" $Portable
Copy-Item "motivational-quotes.txt","README.md" $Portable
@"
OS Widgets $Version — Windows x64 Portable

1. Extract every file from this ZIP.
2. Run OS-Widgets.exe.
3. If Microsoft Defender SmartScreen appears, choose More info > Run anyway only after verifying the SHA-256 checksum from the release page.

The executable is currently unsigned. Windows may display a reputation warning.
"@ | Set-Content (Join-Path $Portable "START-HERE.txt") -Encoding UTF8
Compress-Archive -Path "$Portable/*" -DestinationPath "$Release/OS-Widgets-$Version-Windows-x64-Portable.zip" -CompressionLevel Optimal -Force

$isccCommand = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
$iscc = if ($isccCommand) { $isccCommand.Source } else {
  @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    "C:\ProgramData\chocolatey\bin\ISCC.exe"
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw "Inno Setup 6 compiler (ISCC.exe) was not found." }
Write-Host "Using Inno Setup compiler: $iscc"
& $iscc "packaging/os-widgets.iss"

$Assets = Get-ChildItem $Release -File | Sort-Object Name
$Lines = foreach ($Asset in $Assets) {
  $Hash = (Get-FileHash $Asset.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  "$Hash  $($Asset.Name)"
}
$Lines | Set-Content "$Release/SHA256SUMS.txt" -Encoding ascii
Write-Host "Windows release assets created in $Release"
Get-ChildItem $Release | Format-Table Name,Length
