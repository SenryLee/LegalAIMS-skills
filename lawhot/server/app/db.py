from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DATA_DIR, DB_PATH

_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS items (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              original_title TEXT,
              summary TEXT,
              source_id TEXT NOT NULL,
              source_name TEXT NOT NULL,
              original_url TEXT NOT NULL,
              published_at TEXT,
              discovered_at TEXT NOT NULL,
              category TEXT,
              score REAL,
              selected INTEGER NOT NULL DEFAULT 0,
              track TEXT,
              lang TEXT,
              raw_json TEXT,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_items_discovered ON items(discovered_at DESC);
            CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at DESC);
            CREATE INDEX IF NOT EXISTS idx_items_selected ON items(selected, discovered_at DESC);

            CREATE TABLE IF NOT EXISTS dailies (
              date TEXT PRIMARY KEY,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS editions (
              date TEXT PRIMARY KEY,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        with _lock:
            yield conn
            conn.commit()
    finally:
        conn.close()


def upsert_item(item: dict[str, Any]) -> None:
    now = _utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO items (
              id, title, original_title, summary, source_id, source_name,
              original_url, published_at, discovered_at, category, score,
              selected, track, lang, raw_json, updated_at
            ) VALUES (
              :id, :title, :original_title, :summary, :source_id, :source_name,
              :original_url, :published_at, :discovered_at, :category, :score,
              :selected, :track, :lang, :raw_json, :updated_at
            )
            ON CONFLICT(id) DO UPDATE SET
              title=excluded.title,
              original_title=excluded.original_title,
              summary=excluded.summary,
              category=excluded.category,
              score=excluded.score,
              selected=excluded.selected,
              track=excluded.track,
              raw_json=excluded.raw_json,
              updated_at=excluded.updated_at
            """,
            {
                **item,
                "raw_json": json.dumps(item.get("raw_json") or {}, ensure_ascii=False),
                "updated_at": now,
                "selected": 1 if item.get("selected") else 0,
            },
        )


def list_items(
    *,
    mode: str,
    window_start_iso: str,
    by: str,
    category: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> list[sqlite3.Row]:
    time_col = "COALESCE(published_at, discovered_at)" if by == "published" else "discovered_at"
    # timeline approximation: use discovered_at for window; published kept for display
    where = [f"{time_col} >= ?"]
    params: list[Any] = [window_start_iso]

    if mode == "selected":
        where.append("selected = 1")
    if category:
        where.append("category = ?")
        params.append(category)
    if q:
        where.append("(title LIKE ? OR IFNULL(summary,'') LIKE ? OR source_name LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    sql = f"""
      SELECT * FROM items
      WHERE {' AND '.join(where)}
      ORDER BY {time_col} DESC
      LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    with connect() as conn:
        return list(conn.execute(sql, params))


def count_items(**kwargs: Any) -> int:
    # reuse list with high limit avoided — simple count query
    mode = kwargs["mode"]
    window_start_iso = kwargs["window_start_iso"]
    by = kwargs["by"]
    category = kwargs.get("category")
    q = kwargs.get("q")
    time_col = "COALESCE(published_at, discovered_at)" if by == "published" else "discovered_at"
    where = [f"{time_col} >= ?"]
    params: list[Any] = [window_start_iso]
    if mode == "selected":
        where.append("selected = 1")
    if category:
        where.append("category = ?")
        params.append(category)
    if q:
        where.append("(title LIKE ? OR IFNULL(summary,'') LIKE ? OR source_name LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    with connect() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS c FROM items WHERE {' AND '.join(where)}", params
        ).fetchone()
        return int(row["c"] if row else 0)


def save_daily(date: str, payload: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO dailies(date, payload_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET payload_json=excluded.payload_json
            """,
            (date, json.dumps(payload, ensure_ascii=False), _utc_now()),
        )


def get_daily(date: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT payload_json FROM dailies WHERE date = ?", (date,)).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])


def list_dailies(limit: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT date, payload_json FROM dailies ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        payload = json.loads(r["payload_json"])
        out.append(
            {
                "date": r["date"],
                "title": payload.get("title") or f"LawHOT 日报 {r['date']}",
                "links": payload.get("links") or {},
            }
        )
    return out


def latest_daily_date() -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT date FROM dailies ORDER BY date DESC LIMIT 1").fetchone()
        return row["date"] if row else None


def save_edition(date: str, payload: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO editions(date, payload_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET payload_json=excluded.payload_json,
              created_at=excluded.created_at
            """,
            (date, json.dumps(payload, ensure_ascii=False), _utc_now()),
        )


def get_edition(date: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT payload_json FROM editions WHERE date = ?", (date,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])


def latest_edition_date() -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT date FROM editions ORDER BY date DESC LIMIT 1").fetchone()
        return row["date"] if row else None


def list_edition_dates(limit: int = 7) -> list[str]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT date FROM editions ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
    return [r["date"] for r in rows]


def get_items_by_ids(ids: list[str]) -> list[sqlite3.Row]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        rows = list(
            conn.execute(f"SELECT * FROM items WHERE id IN ({placeholders})", ids)
        )
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def sync_selected_from_editions(days: int = 7) -> None:
    """精选 = 近 N 日刊发条目，供 API mode=selected 与首页一致。"""
    dates = list_edition_dates(limit=days)
    ids: list[str] = []
    for d in dates:
        payload = get_edition(d) or {}
        ids.extend(payload.get("item_ids") or [])
    uniq = list(dict.fromkeys(ids))
    with connect() as conn:
        conn.execute("UPDATE items SET selected = 0")
        if uniq:
            placeholders = ",".join("?" for _ in uniq)
            conn.execute(
                f"UPDATE items SET selected = 1 WHERE id IN ({placeholders})", uniq
            )


def set_meta(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_meta(key: str) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def stats() -> dict[str, Any]:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
        selected = conn.execute("SELECT COUNT(*) AS c FROM items WHERE selected=1").fetchone()["c"]
    return {
        "items": total,
        "selected": selected,
        "db_path": str(DB_PATH),
        "db_exists": Path(DB_PATH).exists(),
    }
