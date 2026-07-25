from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import httpx
import yaml

from . import db
from .classify import classify_category, relevance_ok, score_item, should_select
from .config import PUBLIC_BASE_URL, SOURCES_YAML, USER_AGENT

logger = logging.getLogger("lawhot.ingest")
SHANGHAI = ZoneInfo("Asia/Shanghai")


def load_sources() -> list[dict[str, Any]]:
    raw = yaml.safe_load(Path(SOURCES_YAML).read_text(encoding="utf-8"))
    sources = raw.get("sources") or []
    out = []
    for s in sources:
        if s.get("tier") not in {"P0", "P1"}:
            continue
        if s.get("channel") != "rss":
            continue
        if not s.get("feed"):
            continue
        # Prefer feeds we already probed as ok_rss; still allow unmarked feeds.
        status = (s.get("status") or {}).get("reachability")
        if status and status not in {"ok_rss"}:
            continue
        out.append(s)
    return out


def _parse_dt(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = parsedate_to_datetime(str(value))
        except Exception:
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except Exception:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _entry_id(source_id: str, link: str, title: str) -> str:
    basis = f"{source_id}|{link}|{title}".encode("utf-8", errors="ignore")
    return "lh_" + hashlib.sha1(basis).hexdigest()[:20]


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def fetch_feed(client: httpx.AsyncClient, source: dict[str, Any]) -> list[dict[str, Any]]:
    feed_url = source["feed"]
    try:
        resp = await client.get(feed_url, timeout=25.0)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        logger.warning("feed failed %s: %s", source.get("id"), exc)
        return []

    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:40]:
        title = _clean_html(getattr(entry, "title", "") or "")
        if not title:
            continue
        link = getattr(entry, "link", None) or ""
        if not link and getattr(entry, "links", None):
            link = entry.links[0].get("href", "")
        summary = _clean_html(
            getattr(entry, "summary", "")
            or getattr(entry, "description", "")
            or ""
        )[:600]
        published = _parse_dt(
            getattr(entry, "published", None) or getattr(entry, "updated", None)
        )
        if not relevance_ok(title, summary, source):
            continue
        category = classify_category(title, summary, source)
        score = score_item(title, summary, source, category)
        selected = should_select(score, category, source)
        discovered = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        item_id = _entry_id(source["id"], link or title, title)
        items.append(
            {
                "id": item_id,
                "title": title,
                "original_title": title,
                "summary": summary or None,
                "source_id": source["id"],
                "source_name": source.get("name") or source["id"],
                "original_url": link or PUBLIC_BASE_URL,
                "published_at": published,
                "discovered_at": discovered,
                "category": category,
                "score": score,
                "selected": selected,
                "track": ",".join(source.get("tracks") or []),
                "lang": source.get("lang") or "en",
                "raw_json": {"feed": feed_url},
            }
        )
    return items


async def run_ingest_once() -> dict[str, int]:
    sources = load_sources()
    fetched = 0
    stored = 0
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for source in sources:
            batch = await fetch_feed(client, source)
            fetched += len(batch)
            for item in batch:
                db.upsert_item(item)
                stored += 1
    db.set_meta("last_ingest_at", datetime.now(timezone.utc).isoformat())
    db.set_meta("last_ingest_stats", f"sources={len(sources)};fetched={fetched};stored={stored}")
    maybe_build_daily()
    return {"sources": len(sources), "fetched": fetched, "stored": stored}


def maybe_build_daily() -> None:
    today = datetime.now(SHANGHAI).date().isoformat()
    if db.get_daily(today):
        return
    start = (
        datetime.now(SHANGHAI).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    )
    start_iso = start.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = db.list_items(
        mode="selected",
        window_start_iso=start_iso,
        by="timeline",
        category=None,
        q=None,
        limit=12,
        offset=0,
    )
    if not rows:
        # fallback: last 24h selected
        start_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).replace(
            microsecond=0
        ).isoformat().replace("+00:00", "Z")
        rows = db.list_items(
            mode="selected",
            window_start_iso=start_iso,
            by="timeline",
            category=None,
            q=None,
            limit=12,
            offset=0,
        )
    if not rows:
        return

    sections: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        cat = r["category"] or "insight"
        sections.setdefault(cat, []).append(
            {
                "title": r["title"],
                "summary": r["summary"],
                "source": {"name": r["source_name"]},
                "links": {
                    "lawhot": f"{PUBLIC_BASE_URL}/items/{r['id']}",
                    "original": r["original_url"],
                },
            }
        )

    payload = {
        "date": today,
        "title": f"LawHOT 日报 {today}",
        "lead": "今日法律 AI 精选（自动生成初稿，非法律意见）。",
        "sections": [
            {"name": name, "items": items} for name, items in sections.items()
        ],
        "flashes": [],
        "links": {"lawhot": f"{PUBLIC_BASE_URL}/daily/{today}"},
    }
    db.save_daily(today, payload)
