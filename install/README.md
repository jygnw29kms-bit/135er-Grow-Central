# Installer

## DE

Der v0.5-Installer führt zunächst reproduzierbar die Debian/Ubuntu-Systembasis aus.

Local:

```bash
sudo ./install/install.sh --mode local
```

Cloud mit Domain/TLS:

```bash
sudo ./install/install.sh \
  --mode cloud \
  --domain grow.example.de \
  --email admin@example.de \
  --enable-firewall
```

Wichtig: Bei aktiviertem Firewall-Setup wird standardmäßig SSH-Port 22 erlaubt. Bei abweichendem SSH-Port:

```bash
sudo SSH_PORT=2222 ./install/install.sh --mode cloud --enable-firewall
```

Der Installer verwendet sichere Defaults und veröffentlicht PostgreSQL nicht.

## EN

The v0.5 installer first builds the reproducible Debian/Ubuntu system baseline.

Local:

```bash
sudo ./install/install.sh --mode local
```

Cloud with domain/TLS:

```bash
sudo ./install/install.sh \
  --mode cloud \
  --domain grow.example.com \
  --email admin@example.com \
  --enable-firewall
```

When the firewall step is enabled, SSH port 22 is allowed by default. For a custom SSH port:

```bash
sudo SSH_PORT=2222 ./install/install.sh --mode cloud --enable-firewall
```

The installer uses safe defaults and does not expose PostgreSQL publicly.
