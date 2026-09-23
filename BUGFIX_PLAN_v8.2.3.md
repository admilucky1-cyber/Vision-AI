# Vision AI v8.2.3 — proactive bugfix & perfection pass

Applied without waiting for user reports:

1. **Service worker** — CACHE `va-shell-v823`; network-first HTML; never cache `/api` `/chat` `/auth`
2. **Composer theme colors** — dark/light text + placeholder fixed (Chrome/Edge)
3. **Chat menus** — outside click + Escape closes menus (wrong-chat delete prevention)
4. **LLM cascade errors** — message names which API keys to check
5. **run.py** — default banner version 8.2.3
6. **Boot self-check** — warns if composer/sidebar missing; triggers SW update
7. **Layout CSS** — still last in cascade; mode rail edge padding

Deploy only this zip. Hard refresh after deploy.
