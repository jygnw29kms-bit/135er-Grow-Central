@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-qemu-arm64-windows.ps1"
if errorlevel 1 pause
