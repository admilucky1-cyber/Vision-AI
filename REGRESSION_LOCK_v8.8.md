# Regression lock — never reintroduce these flaws

| Flaw | Lock |
|------|------|
| Nested `try` without `except` in main.py | Separate try/except only; always py_compile before zip |
| Force login after browser close | clearTokens forceLogin only on logout |
| Dead hamburger / buttons | click-fix.js + pointer-events auto |
| Mobile spread / empty void | mobile-dense.css + page-shell.css |
| Inconsistent theme per page | theme-unify.js + data-page accents |
| Wrong chat delete | data-chat-id on history items |
| Oversized containers | max-width columns, no 100vw children |
| Desktop site forced | User: turn OFF in Chrome; viewport device-width |

## Page checklist (all HTML)
- [ ] column / page-shell CSS
- [ ] theme-unify
- [ ] data-page attribute
- [ ] click-fix on chat (index)
- [ ] forms use .va-column where applicable
