# Installation auf Raspberry Pi

## Empfehlung

- Raspberry Pi 4 oder 5
- Raspberry Pi OS 64-bit
- Bluetooth LE
- Python 3.11+
- Ethernet oder WLAN

## Pakete

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv bluetooth bluez
```

## Repository

```bash
git clone <REPOSITORY-URL>
cd 135er-Grow Central
```

## Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## Start

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Browser

```text
http://RASPBERRY-PI-IP:8080
```

## Bluetooth prüfen

```bash
bluetoothctl show
```

## systemd

```bash
sudo mkdir -p /opt/135er-grow-central
sudo cp -r . /opt/135er-grow-central/
sudo cp systemd/135er-grow-central.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now 135er-grow-central
```

## Quellen

Für Mars-Hydro-/BLE-Hintergrund siehe [SOURCES.md](SOURCES.md).
