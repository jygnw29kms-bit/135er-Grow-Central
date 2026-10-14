# Grow Central Test-Pi – Remote-Arbeitsgerät und GitHub Runner

Der Test-Pi `135er-grow-central` ist als dauerhaftes Arbeits- und Testziel eingerichtet.

## Desktop Commander

- Gerät: `135er-grow-central`
- Benutzer: `GrowCentral`
- Node.js: 22.x
- Remote-Agent: `@wonderwhy-er/desktop-commander`
- Benutzer-Service: `desktop-commander-remote.service`
- systemd user lingering ist aktiviert, damit der Dienst ohne aktive SSH-Sitzung nach dem Boot läuft.
- Persistente Installation: `/home/GrowCentral/.local/share/desktop-commander`
- Zugangsdaten liegen ausschließlich lokal unter `/home/GrowCentral/.desktop-commander-device/` und gehören niemals ins Repository.

Der Desktop-Commander-Dienst ist absichtlich gehärtet. Das Home-Verzeichnis ist für seinen Prozess grundsätzlich read-only; Schreibzugriff besteht nur auf die benötigten lokalen Datenpfade.

## GitHub Actions Runner

- Repository: `jygnw29kms-bit/135er-Grow-Central`
- Runner-Name: `135er-grow-central-test-pi`
- Labels: `self-hosted`, `Linux`, `ARM64`, `growcentral`, `test-pi`
- Runner-Verzeichnis: `/home/GrowCentral/.local/share/github-runner-growcentral`
- Benutzer-Service: `github-runner-growcentral.service`
- Work-Verzeichnis: `_work`

Der Runner läuft ohne pauschalen Root-Zugang. Repository-Registrierungstokens sind kurzlebig und dürfen niemals gespeichert oder committed werden.

## Sicherheitsregel

Self-hosted Workflows auf diesem Pi werden nicht automatisch für Pull Requests fremder Herkunft ausgeführt. Test-Pi-Workflows werden gezielt über `workflow_dispatch` gestartet, solange keine zusätzliche Trust-Policy definiert wurde.

## Smoke Test

Workflow: `.github/workflows/test-pi-smoke.yml`

Der Test prüft:

- ARM64/Linux Runner-Erreichbarkeit
- lokalen Grow-Central Health-Endpunkt auf `127.0.0.1:8080/api/health`
- zentrale Final-Master UI Assets
- Schreibbarkeit des isolierten GitHub-Runner-Workspace

Erster erfolgreicher Smoke-Run nach Einrichtung: GitHub Actions Run `38603733185` am 2026-10-14.

## Kontrolle auf dem Pi

```bash
systemctl --user status desktop-commander-remote.service
systemctl --user status github-runner-growcentral.service
loginctl show-user GrowCentral -p Linger
```

Beide Dienste sollen `active (running)` melden und `Linger=yes` soll gesetzt sein.
