# Upgrade from Git v2.7.8 → v2.8.2

Your last pushed tag/commit was **v2.7.8**. This package is the recommended next push.

## What you gain since 2.7.8

| Version | Highlights |
|---------|------------|
| 2.7.9 | Chat text colors (`chat-ui.css`), boost commands |
| 2.8.0 | I–V matplotlib graphs, eye-care theme, Drive docs, longer graph timeouts |
| 2.8.1 | pytest suite, GitHub Actions CI, SVG export, theme presets, SECURITY.md |
| 2.8.2 | SVG toolbar helper, version alignment, upgrade path from 2.7.8 |

## Push to GitHub

```bash
# Extract this zip over your project (keep .env)
git add -A
git status
git commit -m "Vision AI v2.8.2 — graphs, tests, CI, eye-care, themes (from 2.7.8)"
git tag v2.8.2
git push origin main
git push origin v2.8.2
```

## After push

1. Railway auto-redeploy (or Redeploy manually)
2. Hard refresh app (Ctrl+Shift+R)
3. Optional: enable GitHub Actions for CI
4. Colab: pull repo or replace `colab_one_click_boost.py`, restart runtime, run boost

## Smoke test

- Chat: short question
- Image: "create image of a mosque"
- Graph: "create graph between current and voltage" → should return plot image
- Theme: toggle dark/light; optional `applyThemePreset('nord')` in console
