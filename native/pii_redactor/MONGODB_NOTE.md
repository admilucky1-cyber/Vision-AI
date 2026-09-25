# Rust + MongoDB

This crate stays a **standalone PII redactor** (stdin/stdout).

MongoDB storage is handled in Python (`services/mongo_store.py`) so Railway
can enable it with `MONGODB_URI` without rebuilding the Rust binary.

Future: a `vision-mongo-writer` binary could use the official `mongodb` crate
for high-throughput ingest; not required for v8.2.0.
