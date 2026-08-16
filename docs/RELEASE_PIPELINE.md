# Release-Pipeline – 135er-Grow Central

**Stand:** 2026-08-16

## Verbindliche Reihenfolge

1. **Build 71 sichern** – der reproduzierbare Quellstand wird vor Build 72 festgehalten.
2. **Build 72 auf Build 71 aufsetzen** – Build 72 wird ausschließlich aus dem gesicherten Build-71-Stand weiterentwickelt.
3. **Mobile v0.1 bauen und testen** – iPhone- und Android-Client bleiben reine WebGUI-Clients. Sie ersetzen den Raspberry Pi nicht.
4. **Abschlussprüfung** – Prüfen → Probieren/Testen → Optimieren → Absichern → Abschlussprüfung.
5. **Veröffentlichen** – erst nach erfolgreicher Prüfung werden Build 72 und Mobile v0.1 als Release gekennzeichnet.
6. **Installationsseite** – anschließend werden getrennte Installationslinks und QR-Codes für iPhone und Android bereitgestellt.

## Aktueller Stand

- Repository-Version: **alpha-0.7.5**
- Letzter vollständig veröffentlichter Raspberry-Pi-Testbuild: **Build 70**
- Build 70 Commit: `ddc59b289b051c29bdc6032a9db7698f7ec93336`
- Build 71: **Checkpoint angelegt und Pi-Workflow ausgelöst**
- Build-71-Checkpoint: `6547857e9a4f7431218399591a3fef8435115cb6`
- Build 72: **Kandidat auf Basis des Build-71-Checkpoints angelegt und Pi-Workflow ausgelöst**
- Build-72-Trigger: `eb5f8342b10b01f383eb4fd666f8c3e80127bacc`
- Mobile v0.1: **Quellbasis und CI für iOS/Android implementiert; Realgerätetest noch Pflicht**
- Installationslinks / QR-Code: **erst nach erfolgreicher Mobile-Abschlussprüfung**

## Mobile-Zielbild

Die Mobile-App ist ein Client für die bestehende 135er-Grow-Central-WebGUI. Sie übernimmt keine Raspberry-Pi-Funktionen und führt keine lokale Geräteautomation selbstständig aus.

- **Gemeinsame Basis:** Capacitor-WebGUI-Client in `mobile/`
- **iPhone/iOS:** unsigned IPA-Testartefakt über GitHub Actions; für reale Installation passend signieren/sideloaden
- **Android:** Debug-APK-Testartefakt über GitHub Actions
- **Lokal:** `http://135er-Grow-Central.local/` oder beim First Boot `http://10.42.0.1/`
- **Remote:** nur über eine abgesicherte HTTPS-Serveradresse
- **Sicherheit:** keine hartcodierten FRITZ!Box-, Tapo-, Smart-Home- oder Gerätezugänge in der App; Zugangsdaten sind in Ziel-URLs verboten

## Relevante Dateien

- `mobile/package.json`
- `mobile/capacitor.config.json`
- `mobile/www/`
- `mobile/README.md`
- `mobile/INSTALLATION.md`
- `mobile/TEST_PLAN.md`
- `.github/workflows/mobile-build.yml`
- `docs/BUILD_71_CHECKPOINT.md`
- `docs/BUILD_72_MOBILE_V0.1.md`

## Release-Gate

Ein Build oder Mobile-Paket gilt erst dann als veröffentlicht, wenn der zugehörige Stand reproduzierbar ist, die relevanten CI- und Realgerätetests abgeschlossen sind und der öffentliche Download tatsächlich bereitsteht. Geplante, laufende oder vorbereitete Stände werden auf Website und Dokumentation ausdrücklich als solche gekennzeichnet.
