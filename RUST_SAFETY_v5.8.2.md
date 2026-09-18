# Rust Safety & Speed — Vision AI v5.8.2

## Decision
Full rewrite of Vision AI in Rust is **not** the best option today:
- AI provider SDKs, RAG, and orchestration remain strongest in Python
- FastAPI + existing services are production-proven
- Frontend stays web (HTML/CSS/JS)

Rust is applied **where it clearly wins**: memory safety + speed on a security-critical hot path.

## What was added

### `bin/vision-pii-redactor` (Rust)
- Memory-safe PII / secrets redactor
- Release build with LTO and strip
- No undefined behavior, no GC pauses
- Patterns: API keys, tokens, emails, phones, paths, IPs

### `services/pii_redactor.py`
- Prefers the Rust binary when present
- Falls back to pure Python automatically
- Same public API: `redact(text) -> (clean, count)`

## How to rebuild the Rust binary
```bash
cd native/pii_redactor
cargo build --release
cp target/release/vision-pii-redactor ../../bin/
```

## Verify
```bash
echo 'mail a@b.com api_key=sk-abcdefghijklmnop' | ./bin/vision-pii-redactor
python -c "from services.pii_redactor import redact, backend_info; print(backend_info()); print(redact('a@b.com'))"
```

## Future Rust candidates (optional)
- Rate-limit / token-bucket core
- High-volume log scrubbing pipeline
- Optional edge proxy in front of FastAPI

Product name remains **Vision AI**. Version **v5.8.2**.
