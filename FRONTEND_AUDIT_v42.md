# Frontend Audit → v4.2

## Before
- 32 CSS files, ~1700+ !important, stacked polish-v* overrides
- Theme partially applied; mixed hardcoded colors
- Patch accumulation (perfect-v351, theme-unified-v380, tokens-v410…)

## After
Active CSS only:
- tokens.css, themes.css, base.css, layout.css, components.css
- chat.css, studio.css, theme-bridge.css
- style.css + pages.css + chat-ui.css (structural legacy, bridged to tokens)
- responsive.css, accessibility.css, hljs

Historical CSS moved to `frontend/static/css/_archive/` (not linked).

## Theme
- data-theme=dark|light on html
- system preference supported via applyTheme('system')
- Anti-FOUC inline script retained on pages

## Sidebar
- Desktop: collapse rail, no overlay
- Mobile: open-mobile + overlay only when open
- Single resize/orientation reconciler clears sticky overlay

## Remaining limitations
- style.css/pages.css still large legacy; bridged via CSS variables not fully rewritten
- Prompt Studio full 3-pane redesign not completed (structure remains)
- Emoji icons not fully replaced with SVG set
- Full breakpoint matrix not automated tested in CI
