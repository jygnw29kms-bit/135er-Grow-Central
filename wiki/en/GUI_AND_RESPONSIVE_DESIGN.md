# GUI and Responsive Design

![135er GrowControl GUI Preview](../../docs/assets/gui/gui-preview-v0.5.png)

The image is the authoritative visual target for the finished GUI.

## Branding

Raster graphics are embedded as **PNG**. WebP is no longer used because it did not render reliably on the production hosting path. ICO remains allowed for favicons, and SVG remains allowed for technical vector diagrams.

The public website, local GUI and cloud GUI use the 135er GrowControl logo in PNG form.

- >=1400 px: fixed sidebar, 3–4 columns, full diagnostics
- 1024–1399 px: 2–3 columns, compact navigation
- 768–1023 px: touch-first tablet/iPad layout, 2 columns, collapsible navigation
- <768 px: single-column mobile layout, drawer/bottom navigation, prioritized status and quick actions

No hover-only controls. Important touch targets should be about 44×44 CSS px or larger.
