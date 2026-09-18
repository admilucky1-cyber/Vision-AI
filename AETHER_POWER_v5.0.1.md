# Vision AI v5.0.1 — Aether Power Features

Non-breaking upgrade on top of Aether Workspace UI.

## Features

1. **Command Palette** — `Ctrl+K` / `Cmd+K`
   - Searchable actions: New Chat, Settings, Studio, Skills, Theme, Export, Delete thread, etc.
   - Arrow keys + Enter to run; Esc to close
   - Recent chats listed dynamically

2. **Granular Theme Customizer** — `Ctrl+Shift+T` or palette → Customize Theme
   - Live tweak: accent hex, background, surface, border radius, glow intensity, border opacity
   - Saved to localStorage; Reset available

3. **Context & Token Meter**
   - Subtle bar under the hero composer
   - Estimates prompt + recent history tokens vs ~128k context
   - Warn / danger colors when high

4. **Enhanced Code Actions**
   - Every `pre` code block gets: **Copy · Export · Run**
   - Export downloads a language-correct file
   - Run executes JavaScript in a restricted sandbox (no DOM access)

5. **Keyboard Navigation**
   | Shortcut | Action |
   |----------|--------|
   | Ctrl/Cmd+K | Command palette |
   | Ctrl/Cmd+Shift+N | New chat |
   | Ctrl/Cmd+Shift+T | Theme customizer |
   | Ctrl/Cmd+Shift+P | Prompt Studio |
   | Ctrl/Cmd+B | Toggle sidebar |
   | Ctrl/Cmd+/ | Focus composer |
   | Ctrl/Cmd+E | Edit last user message |
   | Esc | Close overlays / stop generation (existing) |

## Compatibility

- Backend: unchanged
- Existing JS handlers: preserved (palette uses capture phase for Ctrl+K)
- CSS: additive only
- Works offline after first load (localStorage + static assets)

## Files added/updated

- `frontend/static/js/aether-power.js` (new)
- `frontend/static/css/aether-v50.css` (extended)
- `frontend/index.html` (script link)
- `VERSION` → 5.0.1
