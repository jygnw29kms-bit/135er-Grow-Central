# Release-Pipeline – 135er-Grow Central

**Stand:** 2026-08-16

## Verbindliche Reihenfolge

1. **Build 71 sichern** – Build 71 darf nicht übersprungen oder durch einen neuen Stand ersetzt werden. Der reproduzierbare Quellstand, die zugehörigen Änderungen und der Teststand werden zuerst gesichert.
2. **Build 72 auf Build 71 aufsetzen** – Build 72 wird ausschließlich aus dem gesicherten Build-71-Stand weiterentwickelt.
3. **Mobile v0.1 testen** – iPhone- und Android-Client bleiben reine WebGUI-Clients. Sie ersetzen den Raspberry Pi nicht. Lokal greifen sie auf die Pi-WebGUI zu; optional kann später die Server-Version für sicheren Remote-Zugriff verwendet werden.
4. **Abschlussprüfung** – Prüfen → Probieren/Testen → Optimieren → Absichern → Abschlussprüfung.
5. **Veröffentlichen** – erst nach erfolgreicher Prüfung werden Build 72 und Mobile v0.1 veröffentlicht.
6. **Installationsseite** – anschließend werden getrennte Installationslinks und QR-Codes für iPhone und Android bereitgestellt.

## Aktueller öffentlicher Stand

- Repository-Version: **alpha-0.7.5**
- Letzter veröffentlichter Raspberry-Pi-Testbuild: **Build 70**
- Build 70 Commit: `ddc59b289b051c29bdc6032a9db7698f7ec93336`
- Build 71: **zu sichern / noch nicht als öffentlicher Release vorhanden**
- Build 72: **wartet auf gesicherten Build 71**
- Mobile v0.1: **wartet auf Build 72 und anschließenden Gerätetest**
- Installationslinks / QR-Code: **erst nach erfolgreicher Mobile-Abschlussprüfung**

## Mobile-Zielbild

Die Mobile-App ist ein Client für die bestehende 135er-Grow-Central-WebGUI. Sie übernimmt keine Raspberry-Pi-Funktionen und führt keine lokale Geräteautomation selbstständig aus.

- **iPhone/iOS:** installierbarer WebGUI-Client / Sideload-Ziel
- **Android:** installierbarer WebGUI-Client
- **Lokal:** Verbindung zum Raspberry Pi im Heimnetz
- **Remote:** optional über die abgesicherte Server-Version
- **Sicherheit:** keine hartcodierten Gerätezugänge oder lokalen Smart-Home-Credentials in der App

## Release-Gate

Ein Build oder Mobile-Paket gilt erst dann als veröffentlicht, wenn der zugehörige Stand reproduzierbar ist, die relevanten Tests abgeschlossen sind und der öffentliche Download tatsächlich bereitsteht. Geplante oder vorbereitete Stände werden auf Website und Dokumentation ausdrücklich als solche gekennzeichnet.
