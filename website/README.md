# 135er GrowControl public project website

This directory is the static public project presentation. It is intentionally domain-neutral.

## Local preview

```bash
cd website
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000`.

## GitHub Pages

`.github/workflows/pages.yml` publishes the `website/` directory when website files change on `master` or when the workflow is started manually.

GitHub repository settings must have **Pages → Source: GitHub Actions** enabled once. No custom domain is required.

## Security

The public website is static HTML/CSS/SVG only. It contains no GrowControl API credentials, no control endpoints, no analytics and no direct connection to the Raspberry Pi.
