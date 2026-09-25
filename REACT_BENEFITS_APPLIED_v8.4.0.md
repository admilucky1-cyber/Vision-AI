# React benefits applied (without full React rewrite)

Facebook video URL requires login — content not readable. Applied standard React advantages to Vision AI:

| React idea | Applied as |
|------------|------------|
| Single source of truth | `VAStore` state object |
| setState + re-render | `setState` + subscribers update DOM |
| Components / events | Event bus + delegated sidebar clicks |
| Predictable UI | Sidebar open/closed only via state |
| Controlled inputs UX | `sending` disables Send consistently |

**Not** migrated to React/Next.js in this pass — keeps Railway zip simple and avoids a multi-week rewrite. Patterns are React-compatible for a future migration.

## Bugs fixed here
- Stuck overlay blocking all clicks
- Send button not wired / stuck disabled
- Sidebar open state desynced from CSS
