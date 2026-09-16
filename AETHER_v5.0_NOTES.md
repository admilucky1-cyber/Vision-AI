# Vision AI v5.0 — Aether Workspace UI

**Status:** Production-safe visual upgrade  
**Breaking changes:** None  
**Backend changes:** None  
**JS changes:** None  

## What changed

- New design layer: `frontend/static/css/aether-v50.css`
- Loaded last so it elevates existing UI without breaking it
- Version bumped to **5.0.0**

## Design goals achieved

- Quieter, more premium dark workspace
- Stronger visual hierarchy (composer is the star)
- Soft layered depth instead of flat or heavy glass
- Refined sidebar, header, and message spacing
- Better focus states and micro-interactions
- Full light-theme compatibility retained

## Compatibility guarantee

- All existing class names and IDs preserved
- All JS event handlers and API calls unchanged
- Backend routes and services untouched
- Previous CSS layers still load (Aether only overrides)

## How to verify

1. Open the app → version shows 5.0.0
2. Dark theme: deep charcoal background, soft accent glow on composer focus
3. Send a message → layout and streaming still work exactly as before
4. Toggle light theme → still functional
5. Mobile sidebar + composer still responsive

## Rollback

Remove the single line that loads `aether-v50.css` from `index.html`  
or revert to the previous package.
