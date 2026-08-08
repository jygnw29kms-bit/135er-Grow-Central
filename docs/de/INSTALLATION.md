# Installation

## Raspberry Pi

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv bluetooth bluez

git clone https://github.com/jygnw29kms-bit/135er_GrowControl.git
cd 135er_GrowControl
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Cloud auf Linux-VServer

```bash
cp cloud/.env.example cloud/.env
nano cloud/.env
docker compose -f docker-compose.cloud.yml up -d --build
curl http://127.0.0.1:8090/api/health
```

Vor öffentlichem Zugriff: HTTPS, Reverse Proxy und Benutzer-Authentifizierung ergänzen.
