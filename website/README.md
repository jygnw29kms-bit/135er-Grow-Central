# 135er GrowControl public project website

This directory is the **domain-neutral** static project presentation and is already available through the Git repository.

## Repository source

```text
website/index.html
website/styles.css
website/assets/architecture.svg
website/assets/gui-preview-v0.5.webp
```

## Local preview

```bash
cd website
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000`.

## GitHub Pages

A manual deployment workflow exists at `.github/workflows/pages.yml`.

GitHub currently requires the repository owner to enable **Settings → Pages → Source: GitHub Actions** once before the workflow can deploy. The GitHub Actions token cannot perform that first repository-level enablement in this repository (`Resource not accessible by integration`). After Pages has been enabled once, run **Publish project website** from the Actions tab.

The workflow is deliberately manual until this one-time repository setting is enabled so ordinary pushes do not create expected red deployment failures.

No custom domain is configured. The earlier domain-specific Nginx prototype has been removed.

## Security

The public website is static HTML/CSS/SVG/WebP only. It contains:

- no GrowControl API credentials;
- no control endpoints;
- no analytics/tracking;
- no direct connection to the Raspberry Pi.

The public presentation and the local control UI are intentionally separate trust surfaces.
