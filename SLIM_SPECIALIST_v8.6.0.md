# Specialist slim pass v8.6.0

## Mental model
1. **Critical path** (must work first paint): auth, store, chat index, click-fix, layout CSS
2. **Enhancement path** (idle load): Aether suite, canvas, ads, schema, status badges
3. **Never delete** backend routes for features still linked in UI — only defer load

## What was frozen / heavy
- 7+ Aether modules (~100KB JS) on every page load → now **idle deferred**
- 31 script tags → critical few + one `defer-modules.js` loader
- Features still available after load; first interaction is faster

## HTML simplicity
- Same structure (sidebar, chat, composer) — no layout rewrite
- Noise comments trimmed
- One loader instead of many body scripts

## Specialist rule
Space is costly on mobile networks. Ship **core chat** fast; optional studio/power after idle.
