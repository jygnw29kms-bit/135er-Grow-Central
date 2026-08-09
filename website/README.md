# 135erheli.de – Projektwebseite

Statische Projektseite für **135er GrowControl**.

## Inhalt

- `index.html` – Startseite
- `styles.css` – responsive Dark/HUD-Optik
- `nginx/135erheli.de.conf` – Beispielkonfiguration für Nginx

## Deployment auf einen Linux-VServer

Beispiel:

```bash
sudo mkdir -p /var/www/135erheli.de
sudo cp website/index.html website/styles.css /var/www/135erheli.de/
sudo mkdir -p /var/www/135erheli.de/docs/assets/gui
sudo cp docs/assets/gui/gui-preview-v0.5.png /var/www/135erheli.de/docs/assets/gui/

sudo cp website/nginx/135erheli.de.conf /etc/nginx/sites-available/135erheli.de
sudo ln -s /etc/nginx/sites-available/135erheli.de /etc/nginx/sites-enabled/135erheli.de
sudo nginx -t
sudo systemctl reload nginx
```

## HTTPS

Nach korrekter DNS-Zuordnung von `135erheli.de` und `www.135erheli.de` auf den Webserver kann TLS z. B. über Certbot aktiviert werden:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 135erheli.de -d www.135erheli.de
```

## Hinweise

Die Webseite ist bewusst statisch gehalten. Sie hat keine direkte Steuerfunktion für GrowControl und exponiert keine lokale Raspberry-Pi-API. Dies hält die öffentliche Projektseite klar getrennt von der lokalen Steuerplattform.
