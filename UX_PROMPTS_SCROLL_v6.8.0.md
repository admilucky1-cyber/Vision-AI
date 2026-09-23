# Vision AI v6.8.0 — Scroll, size, prompts

## Fixes
1. **Scrolling** forced on secondary pages (settings, plans, studio, data-lab, etc.)
2. **Size fit** — grids max-width, message word-wrap, no dead overflow traps
3. **System prompts** upgraded for simple math, names, honest capabilities
4. **UTF-8** middleware on JSON/text to reduce `Iâm`-style mojibake
5. Cache bust `v=680`

## Chat quality notes
- "what is my name" → correctly says unknown until user tells you
- Simple arithmetic should stay one-line (prompt guidance)
- Provider still decides final text; better keys + prompt reduce bad formatting
