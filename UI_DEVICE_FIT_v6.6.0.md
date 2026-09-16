# Vision AI v6.6.0 — All Pages Device Fit & Behaviours

## Scope
- Home (index) + secondary pages: login, settings, studio, data-lab, skills, upgrade, usage, boost, versions
- `device-fit.css` — phone / tablet / desktop / ultrawide
- Safe-area insets (notch / home indicator)
- Touch targets ≥44px under 900px width
- 16px inputs on mobile (no iOS zoom)
- Shared `page-behaviors.js` — theme sync + active nav
- VERSION / meta / CSS cache `v=660`
- `run.py` startup banner with version

## Breakpoints
| Width | Target |
|-------|--------|
| ≤480px | Phone |
| ≤599px | Large phone |
| ≤900px | Tablet / sidebar drawer |
| 901–1199 | Small desktop |
| ≥1200 | Desktop chat column centered |
| ≥1600 | Wide |

## Entry
`python run.py` or `uvicorn main:app`
