# Build 72 + Mobile v0.1

**Datum:** 2026-08-16

Build 72 wird aus dem gesicherten Build-71-Checkpoint weitergeführt. Mobile v0.1 ist jetzt als gemeinsame Capacitor-WebGUI-Clientbasis für iOS und Android im Repository vorhanden.

## Stand

- Build-71-Checkpoint: `6547857e9a4f7431218399591a3fef8435115cb6`
- Build-72-Trigger: `eb5f8342b10b01f383eb4fd666f8c3e80127bacc`
- Mobile-Version: `0.1.0`
- iOS: unsigned IPA-Testartefakt per GitHub Actions
- Android: Debug-APK-Testartefakt per GitHub Actions
- Pi bleibt Master; Mobile führt keine Geräteautomation eigenständig aus.

## Test-Gates

1. Build-71-Workflow muss erfolgreich sein.
2. Build-72-Workflow muss erfolgreich sein.
3. Android APK auf realem Gerät installieren und Login/Session, Offline/Reconnect, Setup-IP und `.local` prüfen.
4. iOS IPA passend signieren/sideloaden und dieselben Tests durchführen.
5. Remote-Zugriff erst mit abgesicherter HTTPS-Serveradresse prüfen.
6. Erst danach Mobile v0.1 und Build 72 als veröffentlicht kennzeichnen und Downloadlinks/QR-Codes freigeben.
