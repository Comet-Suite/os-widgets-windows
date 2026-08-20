$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$Version = "1.2.0-rc.8"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --clean packaging/os-widgets.spec

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
