# 135er GrowControl public project website

This directory is the **domain-neutral** static project presentation.

## Local preview

```bash
cd website
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000`.

## GitHub Pages

`.github/workflows/pages.yml` publishes the `website/` directory when website files change on `master` or when the workflow is started manually. The workflow asks `actions/configure-pages` to enable Pages for the repository when possible.

No custom domain is configured. Domain-specific Nginx configuration from the earlier prototype has been removed.

## Security

The public website is static HTML/CSS/SVG/WebP only. It contains:

- no GrowControl API credentials;
- no control endpoints;
- no analytics/tracking;
- no direct connection to the Raspberry Pi.

The public presentation and the local control UI are intentionally separate trust surfaces.
