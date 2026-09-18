# 135er-Grow Central Cloud / Server V6

**Plattformstand:** `alpha-0.7.5` · Master `e339602` · Pi-Testkandidat **Build 118**  
**Kanonische Quelle:** [`../RELEASE_STATE.md`](../RELEASE_STATE.md)

## Rolle

Cloud/Server ist **optional**. Der Raspberry Pi bleibt die lokale Geräteautorität und darf bei Internet- oder Serverausfall seine lokalen Kernfunktionen nicht verlieren.

```text
Mobile / Browser
      |
    HTTPS
      |
Grow Central Server V6
      ^
      | abgesicherter Remote-/Sync-Pfad
      |
135er-Grow Central Local
    Raspberry Pi
      |
FRITZ! / Tapo / C920 / Mars Hydro / Räume
```

## Kanonische Installation

- Server-Installer: `scripts/install-135ercloud-v6.sh`
- APT-Bootstrap: `scripts/setup-135ercloud-apt-repo-v1.sh`
- signiertes Repository: `https://repo.grow-central.de/apt`
- öffentliche Kopien: `https://grow-central.de/135ercloud-server-install.sh` und `https://grow-central.de/setup-135ercloud-apt-repo.sh`

Der grow-central.de-Deploy veröffentlicht zusätzlich `RELEASE_STATE.md`, `release-state.txt` und `SHA256SUMS.txt`, damit Installer und sichtbarer Release-Stand eindeutig zusammengehören.

## APT-Sicherheit

- dedizierter `Signed-By`-Keyring;
- alte Grow-Central-Quellen werden vor der kanonischen Einrichtung bereinigt;
- keine widersprüchlichen Legacy-`Signed-By`-Definitionen;
- Installations-/Updatepfad muss reproduzierbar bleiben.

## Ausfallverhalten

Bei Server-/Internetausfall:

- lokale GUI: verfügbar;
- lokale Gerätepfade: verfügbar;
- lokale Automationen/Zeitpläne: sollen weiterarbeiten;
- Remotezugriff/Cloud-Sync: nicht verfügbar bzw. pausiert;
- der Pi bleibt Master.

## Remote-Sicherheit

- öffentliche Remotezugriffe nur über TLS/HTTPS oder einen anderweitig abgesicherten Transport;
- GUI-Login allein ersetzt keine Transportverschlüsselung;
- Remote Commands bleiben lokal und serverseitig explizit freizugeben;
- Credentials und lokale LAN-Endpunkte gehören nicht auf die öffentliche Website oder in Mobile-Pakete;
- deny-by-default bleibt die Grundlage für Schreiboperationen.

## Release-Abgleich Build 118

Cloud V6 und APT werden zusammen mit der Nexus-Website erneut veröffentlicht, ohne Build 118 künstlich zu Build 119 zu machen: diese Publishing-/Dokumentationsänderungen verändern nicht den vorgesehenen Pi-Laufzeitkandidaten. Ein neuer Pi-Build ist erst bei einem Runtime-Fix erforderlich.

## Validierung

Vor einer Produktionsfreigabe des Serverpfads müssen Installation/Upgrade, TLS, Authentifizierung, Backup/Restore, APT-Upgrade/Rollback und der Remotezugriff auf einer realen Serverinstanz geprüft werden. Das Vorhandensein des Installers allein ist keine Produktionsvalidierung.
