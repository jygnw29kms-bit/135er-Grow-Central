135er-Grow Central - QEMU ARM64 für Windows
=============================================

Dieses Image ist die virtuelle Testausgabe. Es ersetzt nicht das SD-Karten-Image für einen echten Raspberry Pi.

Start:
1. QEMU für Windows installieren (Standardordner C:\Program Files\qemu).
2. ZIP vollständig in einen beschreibbaren Ordner entpacken.
3. start-qemu-arm64-windows.cmd doppelklicken.
4. Nach dem vollständigen Boot http://localhost:8080 öffnen.

Weboberfläche: http://localhost:8080
SSH: ssh -p 2222 test@localhost
Benutzer: test
Passwort: test
Beenden: Strg+A, danach X

Automatisch geprüft: ARM64-Boot, virtuelle Festplatte, Netzwerk und /api/health.
Nur mit Hardware prüfbar: Bluetooth, GPIO und echte DF100M-Funkkommunikation.
