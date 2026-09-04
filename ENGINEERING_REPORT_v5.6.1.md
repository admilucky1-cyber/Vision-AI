# Vision AI v5.6.1 — Engineering Report

## A. Problems discovered

1. **CSS technical debt** — 20+ stylesheets on disk (polish, glass, aether, refine, tokens, style.css…). Chat already loaded only Nova; secondary pages and settings still mixed inline styles and legacy variables.
2. **Settings overcrowded** — All controls rendered at once in multi-card grid; long voice helper text; emoji section headers; inline styles.
3. **Duplicate theme systems** — `vision_ai_theme`, presets, body/html attributes, and page-local CSS variables (`--bg-deep`, `--text-main`) competed.
4. **Composer meta confusion** — Route + context meter unlabeled for ordinary users (addressed in 5.6.0; retained).
5. **Message action clutter** — Height/Width zoom controls in every AI bubble.
6. **Settings persistence** — Some preferences written but not bound on change (enter-to-send, density, reduced motion).
7. **Legacy CSS files remain on disk** — Not linked from index (safe); kept for optional studio/admin pages that still reference patterns, not deleted to avoid silent breakages of unlinked tools.

## B. Changes made

1. **Settings shell** rewritten: single top bar, `#content` mount, Nova + `settings-ui.css`.
2. **`renderContent` in settings.js** replaced with **accordion sections** (Account, Appearance, Chat, Voice, Privacy & data, About).
3. **Immediate preference bindings** for theme mode, preset, density, reduced motion, languages, enter-to-send, auto-speak.
4. **Canonical semantic tokens** added in `nova-system.css` mapping `--bg-page`, `--text-primary`, `--accent`, etc. to Nova variables.
5. **Density / reduced-motion** data attributes honored in CSS.
6. **Message Height/Width** buttons hidden via CSS to reduce noise (DOM kept).
7. **Version** set to **5.6.1** across settings, VERSION file, index meta.

## C. Settings added (implemented)

| Setting | Storage | Behavior |
|---------|---------|----------|
| Color mode (dark/light/system) | `vision_ai_theme` | Immediate |
| Accent preset | `vision_theme_preset` | Immediate |
| Density | `vision_density` | Immediate + `data-density` |
| Reduced motion | `vision_reduced_motion` | Immediate |
| Reply language | `vision_chat_lang` | Immediate |
| Enter to send | `vision_enter_send` | Immediate |
| STT / TTS language | `vision_stt_lang` / `vision_tts_lang` | Immediate |
| Auto-speak | `vision_auto_speak` | Immediate |
| Clear local history | existing | Confirm + clear |
| Reset preferences | new | Confirm + reload |
| Password change | API | Explicit submit |
| Display name | API | Explicit save |

## D. Settings intentionally NOT added

- Temperature / creativity — no stable user-facing backend contract in current routes.
- Notification permission center — would require push infrastructure.
- Delete account — no confirmed backend endpoint in this tree.
- Logout all sessions — no server session-revocation API found.
- Fake usage meters — avoided; Usage page remains honest.

## E. CSS architecture

**Authoritative load order (chat):**

1. `nova-system.css` — tokens, base, layout, components, chat, responsive  
2. `pages-shell.css` — secondary page chrome  
3. `settings-ui.css` — settings accordion only  
4. hljs + KaTeX (code/math)

**On disk but not linked from index:** style.css, polish-*, glass-ui, aether-v50, tokens.css, themes.css, etc.  
**Policy:** Do not add new polish layers. Prefer Nova tokens. Legacy files retained until each optional page is migrated.

## F. JavaScript architecture

- **settings.js** — `renderContent` is the single settings view builder; progressive disclosure via `<details>`.
- **theme-bootstrap.js** / **applyTheme** — unchanged keys (`vision_ai_theme`, `vision_theme_preset`) for compatibility.
- **index.js / aether-*** — not rewritten; behavior preserved.
- **nova-shell.js** — profile menu + tray aria.

## G. UX improvements

- Settings scannable in seconds (section titles + one-line descriptions).
- Password, danger actions, and plan links clearly separated.
- Chat composer remains primary; secondary zoom controls de-emphasized.
- Secondary pages share the same top bar pattern (← Chat).

## H. Accessibility

- Accordion uses native `<details>`/`<summary>` (keyboard operable).
- Labels associated with controls; `aria-label` on icon buttons.
- Focus styles from Nova (`:focus-visible`).
- Reduced motion preference supported.
- High-contrast remains available as preset.

## I. Performance

- Settings page no longer loads large inline CSS blocks.
- Chat continues to avoid loading 15+ legacy stylesheets.
- No new libraries added.

## J. Security

- Password change still goes through authenticated API; no client-side secret storage added.
- Preferences only in localStorage (non-sensitive).
- No API keys embedded in frontend changes.

## K. Testing

| Check | Result |
|-------|--------|
| `node --check settings.js` | Pass |
| CSS/HTML structure present | Pass (packaged) |
| Full pytest suite | Not executed in this environment (no full install); recommend `pytest tests/` after deploy |
| Manual: extract ZIP + `python run.py` | Required on target machine |

## L. Remaining issues

1. Legacy CSS still in tree (unused by index) — gradual deletion after confirming studio/admin.
2. **Offline** badge can still false-positive when `/health` is slow — needs a softer reconnect probe (not changed this pass).
3. `settings.js` still large; further split into modules optional.
4. Studio page only partially migrated to pages-shell.
5. Full WCAG audit not automated in CI.

## Quality gate (engineering judgment)

| Gate | Status |
|------|--------|
| Starts / chat / auth paths preserved | Yes (no backend route removal) |
| Settings progressive disclosure | Yes |
| Theme keys compatible | Yes |
| No new decorative systems | Yes |
| Complete ZIP | `VISION_AI_v5.6.1_REFINED.zip` |
