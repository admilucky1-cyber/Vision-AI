# VisionCanvas v6.9.0 — Android + Desktop

## Module
`frontend/static/js/vision-canvas.js` → `window.VisionCanvas`

## Features
| Feature | Behavior |
|---------|----------|
| HiDPI | `devicePixelRatio` up to 3, crisp on phones & retina |
| Resize | `ResizeObserver` + window resize |
| Orientation | Android rotate → redraw |
| visualViewport | Browser chrome / keyboard size changes |
| Coarse pointer | Larger nodes/fonts on touch devices |
| Theme | Graph colors follow light/dark |

## API
```js
VisionCanvas.createSurface(canvas, drawFn, { container, minHeight, height })
VisionCanvas.fit(canvas, cssW, cssH)
VisionCanvas.bindPointers(canvas, { onDown, onMove, onUp })
```

## Wired
Memory Graph (Aether Forge) uses the surface and redraws on resize.
