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

- Cloud-Core-Installer: `scripts/install-cloud-core.sh`
- APT-Bootstrap: `scripts/setup-135ercloud-apt-repo-v2.sh`
- signiertes Repository: `https://repo.grow-central.de/apt`
- öffentlicher Cloud-Core-Installer: [`scripts/install-cloud-core.sh`](../scripts/install-cloud-core.sh)
- öffentliche APT-Einrichtung: [`scripts/add-135ercloud-apt-repo.sh`](../scripts/add-135ercloud-apt-repo.sh)

Release- und Buildstände werden im öffentlichen Repository über [`RELEASE_STATE.md`](../RELEASE_STATE.md) und die veröffentlichten Release-Artefakte einschließlich ihrer Prüfsummen dokumentiert.

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

Cloud V7, Cloud Core und das signierte APT-Repository werden gemeinsam gepflegt. Cloud-Releases und Pi-Image-Releases bleiben technisch getrennte Artefakte.

## Validierung

Vor einer Produktionsfreigabe des Serverpfads müssen Installation/Upgrade, TLS, Authentifizierung, Backup/Restore, APT-Upgrade/Rollback und der Remotezugriff auf einer realen Serverinstanz geprüft werden. Das Vorhandensein des Installers allein ist keine Produktionsvalidierung.
