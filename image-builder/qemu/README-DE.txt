135er-Grow Central - QEMU-Test unter Windows
================================================

1. Installiere QEMU für Windows und 7-Zip. Beide Programme müssen über PATH erreichbar sein.
2. Entpacke dieses QEMU-Kit in einen eigenen Ordner.
3. Lege 135er_Grow_Central_RPi3B_Test.img.xz in denselben Ordner.
4. Starte start-qemu-windows.cmd.
5. Warte auf die Anmeldung. Der erste Start kann mehrere Minuten dauern.

Weboberfläche: http://localhost:8080
SSH: ssh -p 2222 test@localhost
Benutzer: test
Passwort: test

QEMU beenden: Strg+A, danach X

Der QEMU-Test prüft ARM64-Boot, Linux, systemd, Netzwerk, SSH und die Grow-Central-Webanwendung.
Bluetooth, GPIO, Raspberry-Pi-Firmware und die echte DF100M-Funkverbindung benötigen weiterhin Hardware.
