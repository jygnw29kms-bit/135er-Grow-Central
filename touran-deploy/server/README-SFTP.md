# 135er Touran – SFTP Upload User

Ziel: eigener, stark eingeschraenkter Radio-Account fuer Log-Uploads.

## Sicherheitsmodell
- Benutzer: `touranradio`
- nur SFTP (`internal-sftp`), keine Shell
- SSH-Key only, Passwortlogin aus
- Chroot: `/srv/touranradio`
- Uploadziel aus Sicht des Radios: `/upload/inbox`
- kein Zugriff auf Website, Plesk-Dateien, Datenbanken oder andere Benutzer
- private Auswertung bleibt unter `/var/www/vhosts/dezender.de/private/touran-logs`

## Installation auf dem Server
Als root:

```bash
bash /path/to/setup-touranradio-sftp.sh
```

Danach den PUBLIC KEY des Radios in
`/srv/touranradio/.ssh/authorized_keys`
eintragen.

## Wichtig fuer die App
Keinen privaten SSH-Key ins Git oder fest in die APK einbauen. Die App soll pro Radio lokal ein eigenes Schluesselpaar erzeugen und nur den Public Key exportieren/anzeigen. Der Private Key bleibt im Android Keystore/App-Speicher.

## Empfohlener Dateiaufbau
- `radio_<timestamp>_system.json`
- `adapter_<timestamp>_capability.log`
- `vag_<timestamp>.csv`
- `obd_<timestamp>.csv`

HTTPS-Upload bleibt parallel als Fallback/Metadatenkanal bestehen.
