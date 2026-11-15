# Grow-Central Beta 1.0: Verschlüsseltes Backup und sicherer Restore-Test

Stand: 15.11.2026. **Beta-Vorbereitung, noch kein freigegebener vollständiger System-Restore.**

## Zweck

Das bisherige Messhistorien-Backup sichert nicht automatisch die vollständige Nutzerumgebung. Der neue, unabhängige Beta-Datenexport in `scripts/beta_data_backup.py` archiviert Räume, Kalibrierungen, Datenbanken, Grow-Fotos, HomeKit-Zustand, sichere Cloud-Geräteidentität, Raumfreigaben, Alarm-/Automationsregeln und optionale Zugangskonfiguration.

Erzeugt wird **nur ein AES-256-GCM-verschlüsseltes Archiv** mit passwortbasierter Scrypt-Schlüsselableitung und SHA-256-Dateimanifest. Alle zurückkopierbaren Dateien werden zuerst im temporären Testverzeichnis verifiziert. Das Werkzeug überschreibt **niemals** eine laufende Installation.

## Bedienung auf dem Pi

Die folgenden Befehle erzeugen beziehungsweise prüfen ein lokal verschlüsseltes Archiv. Die Passphrase wird interaktiv abgefragt und **nicht in der Shell-Historie oder im Git gespeichert**.

```bash
sudo install -d -m 700 /var/backups/grow-central/manual
sudo /opt/135er-grow-central/.venv/bin/python /opt/135er-grow-central/scripts/beta_data_backup.py \
  --create /var/backups/grow-central/manual/gc-beta1-encrypted.gcb \
  --data-root /var/lib/135er-grow-central \
  --config-file /opt/135er-grow-central/.env

sudo /opt/135er-grow-central/.venv/bin/python /opt/135er-grow-central/scripts/beta_data_backup.py \
  --verify /var/backups/grow-central/manual/gc-beta1-encrypted.gcb

sudo /opt/135er-grow-central/.venv/bin/python /opt/135er-grow-central/scripts/beta_data_backup.py \
  --stage-restore /var/backups/grow-central/manual/gc-beta1-encrypted.gcb \
  --staging-dir /var/backups/grow-central/manual/restored-test
```

**Wichtig:** `--staging-dir` muss neu und noch nicht vorhanden sein. Der Datenbestand des aktiven Pi wird dabei nicht verändert. Beim Restore entsteht absichtlich **keine** Anmeldung mit vorhandenen Web-Sitzungscookies: `gui-sessions.json` wird nicht exportiert. Die Cloud-Geräteidentität und lokale API-Schlüssel liegen im verschlüsselten Archiv; ein zurückgespieltes Gerät darf die Originalidentität nicht parallel auf zwei laufenden Pis verwenden.

Eine vollständige Wiederherstellung erfordert den Nachweis, dass die neuen Programmdateien und das Image mit den archivierten Datenformaten kompatibel sind. Das ist für die Beta noch nicht abgenommen und darf nicht durch unkontrolliertes Kopieren nach `/var/lib` ersetzt werden.

## Sicherheits- und Datenregeln

- Mindestens 16 Zeichen Passphrase, besser ein einmalig generierter langer Satz. Verlust bedeutet kein Restore.
- Keine Passphrase an AI, Git, Logs oder Support-Systeme senden.
- Die verschlüsselte Datei muss separat vom Pi gesichert werden, idealerweise auf einem eigenen Datenträger.
- Die optionale App-`.env` wird **nur verschlüsselt** hinzugefügt, weil sonst Authentifizierung und Fernzugang nach Restore unvollständig sein könnten.
- Sogenannte `maintenance`-Altdateien, temporäre Testdateien und abgelaufene Login-Sitzungen werden absichtlich nicht mitgesichert.
- SQLite-Dateien werden über die SQLite-Backup-API konsistent kopiert, nicht roh während Schreibzugriffen.
- Symlinks sowie relative Pfadfluchten sind gesperrt; Dateien werden nach Hash geprüft; Restore-Ziele müssen neu sein.
- Passphrase und abweichende Passwortkonfiguration werden beim Restore nicht automatisch auf ein anderes Gerät übernommen.

## Was bereits nachgewiesen ist

Das Werkzeug ist auf dem Test-Pi installiert; **noch kein echter Export ausgeführt**. Fünf isolierte Tests mit **synthetischen** Daten: Verschlüsselung, falsches Passwort, Manipulation, SQLite-Snapshot, Foto-/Schlüsselrückgabe, Ausschluss bestehender Login-Sitzungen, restriktive Dateirechte und zusätzlicher verschlüsselter Konfigurationsexport. Kein echtes Nutzerdatum wurde in diesen Tests gelesen.

## Offene Abnahme

1. Interaktive Passphrase vom Besitzer festlegen, echten verschlüsselten Export erzeugen.
2. Archiv auf externem Ziel sichern und dort verifizieren.
3. Frisches Pi4-Beta-Image booten, gespeichertes Archiv **nur in eine Staging-Umgebung** zurückspielen.
4. Sichere Migrations-/Rollback-Routine für echten Restore bereitstellen, inklusive Datenbankschema und Identitätswechsel.
5. Pflanzen/Growbuch/Fotos/Kalibrierung/Cloud/HomeKit nach Wiederherstellung gemeinsam prüfen und abnehmen.

Der Release-Gate `install_and_recovery` bleibt bis dahin **gesperrt**.
