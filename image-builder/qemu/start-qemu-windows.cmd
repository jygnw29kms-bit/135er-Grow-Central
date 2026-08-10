@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-qemu-windows.ps1"
if errorlevel 1 pause
