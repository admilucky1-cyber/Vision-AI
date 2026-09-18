# Vision AI Single System v7.2.0

## One entry point

| Layer | File |
|-------|------|
| CSS | `/frontend/static/css/vision-system.css` |
| JS | `/frontend/static/js/vision-system.js` |

## Bundles (applied)

- device-fit (responsive + safe-area)
- pages-shell (secondary page scroll shell)
- page-layout-system (AppBar, padding, spacer, container)
- theme-controls (composer/buttons/text follow theme)
- theme boot + theme click unblock
- /health online ping
- active nav marking
- viewport meta ensure

## Pages
All `frontend/*.html` load vision-system.css + vision-system.js.

Previous partial sheets may still load; vision-system is the **authority** layer so missing includes no longer leave a page half-fixed.
