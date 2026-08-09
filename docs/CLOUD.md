# 135er-Grow Central Cloud

## Rolle

Die Cloud ist **optional**. Der Raspberry Pi bleibt lokale Steuerinstanz.

```text
Internet / Mobilgerät
        |
      HTTPS
        |
     VServer
  Grow Central Cloud
        ^
        |
 ausgehende HTTPS-Verbindung
        |
 Raspberry Pi
 Grow Central Local
        |
       BLE
        |
     DF100M
```

## Ausfallverhalten

Wenn der VServer oder das Internet ausfällt:

- DF100M-Adapter lokal: bleibt verfügbar
- lokale Web-GUI: bleibt verfügbar
- lokale Automationen: sollen weiterlaufen
- Zeitpläne: sollen weiterlaufen
- Cloud-Historie: pausiert
- Remote-Zugriff: nicht verfügbar

## Cloud v0.4 Funktionen

- `/api/health`
- Telemetrie vom Pi empfangen
- letzte Werte je Standort
- einfache Historie über SQLite
- Remote-Dashboard
- Command Queue vorbereitet
- Remote Commands doppelt abgesichert:
  - Server: `CLOUD_ALLOW_COMMANDS`
  - Pi: `GC_REMOTE_COMMANDS`

Standardmäßig sind Remote Commands **aus**.

## VServer Schnellstart mit Docker

```bash
cp cloud/.env.example cloud/.env
nano cloud/.env

docker compose -f docker-compose.cloud.yml up -d --build
```

Danach lokal auf dem VServer:

```bash
curl http://127.0.0.1:8090/api/health
```

## Nginx

Beispiel:

`deploy/nginx/grow-central-cloud.conf.example`

Für produktiven Betrieb HTTPS über Let's Encrypt/Certbot aktivieren.

## Pi Cloud-Link

```bash
cd local/cloud_link
cp .env.example .env
nano .env
```

Minimal:

```text
GC_CLOUD_ENABLED=true
GC_CLOUD_URL=https://grow.example.de
GC_CLOUD_TOKEN=<derselbe Token wie am Server>
GC_SITE_ID=garage
GC_REMOTE_COMMANDS=false
```

## Sicherheit

v0.4 nutzt einen statischen API-Token und ist ein **Alpha-Cloud-Layer**.

Für spätere Releases vorgesehen:

- per-device credentials
- Token Rotation
- Benutzerlogin
- Rollen
- TLS pinning optional
- Audit Log
- rate limiting
- command signatures/nonces
- PostgreSQL
- MQTT over TLS

Die Cloud-Weboberfläche sollte nicht ohne vorgeschaltete Authentifizierung öffentlich betrieben werden.
