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
              updated_at TEXT NOT NULL,
              -- 最近一次进入每日读本的日期（YYYY-MM-DD）。历史刊发次数不存
              -- 在这里，而是从 editions 表实时数出，避免累加计数漂移。
              last_edition_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_items_discovered ON items(discovered_at DESC);
            CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at DESC);
            CREATE INDEX IF NOT EXISTS idx_items_selected ON items(selected, discovered_at DESC);
            -- 注意：idx_items_last_edition 依赖 last_edition_at 列，该列在老库上
            -- 不存在，必须等_migrate_items_columns 补列后才能建，不能写在这里。

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

            CREATE TABLE IF NOT EXISTS sources (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              lang TEXT,
              region TEXT,
              tier TEXT NOT NULL,
              channel TEXT NOT NULL,
              homepage TEXT,
              feed TEXT,
              list_url TEXT,
              tracks TEXT,
              trust TEXT,
              egress TEXT,
              enabled INTEGER NOT NULL DEFAULT 1,
              ingestible INTEGER NOT NULL DEFAULT 0,
              status_json TEXT,
              notes TEXT,
              raw_json TEXT,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sources_tier ON sources(tier, enabled);
            CREATE INDEX IF NOT EXISTS idx_sources_channel ON sources(channel, ingestible);
            """
        )
        _migrate_items_columns(conn)


def _migrate_items_columns(conn: sqlite3.Connection) -> None:
    """给既有 items 表补列。

    `CREATE TABLE IF NOT EXISTS` 对已存在的表不会补列，线上库是 v0.4 建的老表，
    缺列会导致后续所有 SELECT * 查询报 no such column。这里做一次幂等迁移。
    """
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(items)")}
    if not existing:
        return
    if "last_edition_at" not in existing:
        conn.execute("ALTER TABLE items ADD COLUMN last_edition_at TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_last_edition ON items(last_edition_at)"
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
              -- discovered_at 刻意不更新：它表示「首次收录时间」，
              -- 是新鲜度衰减的时间基准，不能被重复抓取刷新掉。
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


def mark_edition_published(date: str, ids: list[str]) -> None:
    """记录本期刊发的条目，供新鲜度衰减使用。

    刻意**不做累加计数**。累加有两个坏处：重编同一期会把计数刷高，
    而清零重写又会抹掉该条目在其它期的记录。改为把当前日期写进
    `last_edition_at`，历史次数由 `count_edition_appearances` 从 editions
    表实时数出来——editions 是唯一事实来源，不会漂移。
    """
    if not ids:
        return
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        conn.execute(
            f"UPDATE items SET last_edition_at = ? WHERE id IN ({placeholders})",
            [date, *ids],
        )


def count_edition_appearances(
    item_ids: list[str], *, before: str | None = None
) -> dict[str, int]:
    """统计每个条目在往期每日读本中出现过多少次。

    以 editions 表为唯一事实来源，因此重编历史日期不会污染计数。
    `before` 用于排除指定日期自身（重编当天时本期也算在窗口内）。
    """
    if not item_ids:
        return {}
    out: dict[str, int] = dict.fromkeys(item_ids, 0)
    dates = [d for d in list_edition_dates(limit=30) if not before or d != before]
    if not dates:
        return out
    for d in dates:
        payload = get_edition(d) or {}
        for iid in payload.get("item_ids") or []:
            if iid in out:
                out[iid] += 1
    return out


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


def upsert_source(row: dict[str, Any]) -> None:
    now = _utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO sources (
              id, name, lang, region, tier, channel, homepage, feed, list_url,
              tracks, trust, egress, enabled, ingestible, status_json, notes,
              raw_json, updated_at
            ) VALUES (
              :id, :name, :lang, :region, :tier, :channel, :homepage, :feed, :list_url,
              :tracks, :trust, :egress, :enabled, :ingestible, :status_json, :notes,
              :raw_json, :updated_at
            )
            ON CONFLICT(id) DO UPDATE SET
              name=excluded.name,
              lang=excluded.lang,
              region=excluded.region,
              tier=excluded.tier,
              channel=excluded.channel,
              homepage=excluded.homepage,
              feed=excluded.feed,
              list_url=excluded.list_url,
              tracks=excluded.tracks,
              trust=excluded.trust,
              egress=excluded.egress,
              enabled=excluded.enabled,
              ingestible=excluded.ingestible,
              status_json=excluded.status_json,
              notes=excluded.notes,
              raw_json=excluded.raw_json,
              updated_at=excluded.updated_at
            """,
            {
                "id": row["id"],
                "name": row.get("name") or row["id"],
                "lang": row.get("lang"),
                "region": json.dumps(row.get("region") or [], ensure_ascii=False),
                "tier": row.get("tier") or "P2",
                "channel": row.get("channel") or "web",
                "homepage": row.get("homepage"),
                "feed": row.get("feed"),
                "list_url": row.get("list_url"),
                "tracks": json.dumps(row.get("tracks") or [], ensure_ascii=False),
                "trust": row.get("trust"),
                "egress": row.get("egress"),
                "enabled": 1 if row.get("enabled", True) else 0,
                "ingestible": 1 if row.get("ingestible") else 0,
                "status_json": json.dumps(row.get("status") or {}, ensure_ascii=False),
                "notes": row.get("notes"),
                "raw_json": json.dumps(row.get("raw") or {}, ensure_ascii=False),
                "updated_at": now,
            },
        )


def list_sources(
    *,
    tier: str | None = None,
    channel: str | None = None,
    ingestible_only: bool = False,
) -> list[sqlite3.Row]:
    where: list[str] = ["enabled = 1"]
    params: list[Any] = []
    if tier:
        where.append("tier = ?")
        params.append(tier)
    if channel:
        where.append("channel = ?")
        params.append(channel)
    if ingestible_only:
        where.append("ingestible = 1")
    sql = f"""
      SELECT * FROM sources
      WHERE {' AND '.join(where)}
      ORDER BY
        CASE tier WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 ELSE 2 END,
        channel, id
    """
    with connect() as conn:
        return list(conn.execute(sql, params))


def count_sources() -> dict[str, int]:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM sources").fetchone()["c"]
        enabled = conn.execute(
            "SELECT COUNT(*) AS c FROM sources WHERE enabled=1"
        ).fetchone()["c"]
        ingestible = conn.execute(
            "SELECT COUNT(*) AS c FROM sources WHERE enabled=1 AND ingestible=1"
        ).fetchone()["c"]
        p0 = conn.execute(
            "SELECT COUNT(*) AS c FROM sources WHERE enabled=1 AND tier='P0'"
        ).fetchone()["c"]
        p1 = conn.execute(
            "SELECT COUNT(*) AS c FROM sources WHERE enabled=1 AND tier='P1'"
        ).fetchone()["c"]
    return {
        "total": int(total),
        "enabled": int(enabled),
        "ingestible": int(ingestible),
        "p0": int(p0),
        "p1": int(p1),
    }


def stats() -> dict[str, Any]:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
        selected = conn.execute("SELECT COUNT(*) AS c FROM items WHERE selected=1").fetchone()["c"]
    src = count_sources()
    return {
        "items": total,
        "selected": selected,
        "sources": src.get("enabled", 0),
        "sources_ingestible": src.get("ingestible", 0),
        "db_path": str(DB_PATH),
        "db_exists": Path(DB_PATH).exists(),
    }
