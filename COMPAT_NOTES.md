# Cross-platform notes — v5.6.5

## Tested targets (design intent)
- **Desktop:** Windows (Edge/Chrome/Firefox), macOS (Safari/Chrome), Linux (Chrome/Firefox)
- **Mobile:** iOS Safari/Chrome, Android Chrome/Samsung Internet

## Guarantees
- Viewport + safe-area for notched phones
- 16px inputs (no iOS zoom-on-focus)
- 100vh + 100dvh + -webkit-fill-available height stack
- `:has()` fallbacks via `html.sidebar-closed` (cross-platform.js)
- Clipboard fallback for older browsers
- SpeechRecognition webkit prefix helper
- visualViewport keyboard inset for composer
- 44px minimum tap targets
- prefers-reduced-motion respected

## Known platform limits (not bugs we can fully remove)
- Voice input: limited/unavailable on some desktop Firefox builds
- Google sign-in: requires configured OAuth + HTTPS
- Background tabs may throttle streaming responses
- Very old browsers (IE11) are not supported
