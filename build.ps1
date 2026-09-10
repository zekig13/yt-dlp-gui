# Build Windows onedir distributable for yt-dlp GUI (double-clickable, no console).
# Requires: Python 3.10+ on PATH, pip packages: pyinstaller, customtkinter
# Usage:  powershell -ExecutionPolicy Bypass -File .\build.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Ensuring build dependencies..."
python -m pip install -q -r requirements.txt pyinstaller

$distName = "yt-dlp-gui"
$outRoot = Join-Path $PSScriptRoot "dist"
$releaseDir = Join-Path $PSScriptRoot "release"
$zipName = "yt-dlp-gui-windows-x64.zip"

Write-Host "==> Cleaning previous build..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist\$distName") { Remove-Item -Recurse -Force "dist\$distName" }
if (Test-Path "$distName.spec") { Remove-Item -Force "$distName.spec" }

Write-Host "==> Running PyInstaller (onedir, windowed, collect customtkinter)..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --windowed `
  --onedir `
  --name $distName `
  --collect-all customtkinter `
  --add-data "app\options_catalog.json;app" `
  --hidden-import app `
  --hidden-import app.ui `
  --hidden-import app.ui.main_window `
  --hidden-import app.ui.option_widgets `
  --hidden-import app.catalog `
  --hidden-import app.command_builder `
  --hidden-import app.deps `
  --hidden-import app.runner `
  --hidden-import app.settings `
  main.py

$exePath = Join-Path $outRoot "$distName\$distName.exe"
if (-not (Test-Path $exePath)) {
  throw "Build failed: missing $exePath"
}

Write-Host "==> Writing RELEASE_README.txt into dist folder..."
$readmeNote = @"
YT-DLP GUI (Windows x64)
========================

Double-click yt-dlp-gui.exe to start. No Python install required.

On first launch the app downloads yt-dlp.exe and ffmpeg into:
  %LOCALAPPDATA%\yt-dlp-gui\bin\

Crash log (if the window fails to open):
  %LOCALAPPDATA%\yt-dlp-gui\crash.log

Source / issues: https://github.com/zekig13/yt-dlp-gui
"@
Set-Content -Path (Join-Path $outRoot "$distName\RELEASE_README.txt") -Value $readmeNote -Encoding utf8

Write-Host "==> Creating release zip..."
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$zipPath = Join-Path $releaseDir $zipName
if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
Compress-Archive -Path (Join-Path $outRoot $distName) -DestinationPath $zipPath -Force

Write-Host ""
Write-Host "OK"
Write-Host "  EXE: $exePath"
Write-Host "  ZIP: $zipPath"
