"""Cross-session memory graph — SQLite entity/relationship store."""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

DB = Path(__file__).resolve().parent.parent / "data" / "memory_graph.sqlite"
DB.parent.mkdir(parents=True, exist_ok=True)

_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b")
_STOP = set("the and for are but not you all can had her was one our out has its who how did only she may him your than then them this that with from have were been will what when your".split())


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB))
    c.execute("""CREATE TABLE IF NOT EXISTS entities(
        id INTEGER PRIMARY KEY, name TEXT UNIQUE, count INTEGER DEFAULT 1, last_seen REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS edges(
        a TEXT, b TEXT, weight INTEGER DEFAULT 1, last_seen REAL,
        PRIMARY KEY(a,b))""")
    return c


def ingest_text(text: str, max_terms: int = 40) -> Dict[str, Any]:
    terms = [t.lower() for t in _TOKEN.findall(text or "") if t.lower() not in _STOP]
    # frequency
    freq: Dict[str, int] = {}
    for t in terms:
        freq[t] = freq.get(t, 0) + 1
    top = sorted(freq.items(), key=lambda x: -x[1])[:max_terms]
    names = [t for t, _ in top]
    now = time.time()
    with _conn() as c:
        for n, cnt in top:
            c.execute(
                "INSERT INTO entities(name,count,last_seen) VALUES(?,?,?) "
                "ON CONFLICT(name) DO UPDATE SET count=count+?, last_seen=?",
                (n, cnt, now, cnt, now),
            )
        for i, a in enumerate(names):
            for b in names[i + 1 : i + 4]:
                x, y = (a, b) if a < b else (b, a)
                c.execute(
                    "INSERT INTO edges(a,b,weight,last_seen) VALUES(?,?,1,?) "
                    "ON CONFLICT(a,b) DO UPDATE SET weight=weight+1, last_seen=?",
                    (x, y, now, now),
                )
        c.commit()
    return {"ok": True, "entities": len(names)}


def snapshot(limit: int = 30) -> Dict[str, Any]:
    with _conn() as c:
        ents = c.execute(
            "SELECT name, count FROM entities ORDER BY count DESC LIMIT ?", (limit,)
        ).fetchall()
        edges = c.execute(
            "SELECT a,b,weight FROM edges ORDER BY weight DESC LIMIT ?", (limit * 2,)
        ).fetchall()
    return {
        "ok": True,
        "entities": [{"name": n, "count": cnt} for n, cnt in ents],
        "edges": [{"a": a, "b": b, "weight": w} for a, b, w in edges],
    }
