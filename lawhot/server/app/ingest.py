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
from .config import (
    LAWHOT_HTTP_PROXY,
    OPENAI_API_KEY,
    PUBLIC_BASE_URL,
    SOURCES_YAML,
    USER_AGENT,
    source_needs_proxy,
)
from .edition import rebuild_edition_for_date, today_shanghai
from .enrich import bad_summary, enrich_item, make_api_client
from .translate import looks_chinese, needs_translation
from .web_cn import BUILTIN_CN_LISTS, fetch_cn_list

logger = logging.getLogger("lawhot.ingest")
SHANGHAI = ZoneInfo("Asia/Shanghai")

# RSS status values we will attempt to fetch
_RSS_OK = {"ok_rss", "pending_probe", "ok_web"}
# Hard skip — known-unusable for automated fetch this cycle
_SKIP_CHANNELS = {"wechat", "x", "newsletter", "api"}
_SKIP_REACHABILITY = {"awaiting_owner", "needs_wechat_id", "needs_x_access", "needs_url", "missing"}


def _yaml_sources() -> list[dict[str, Any]]:
    path = Path(SOURCES_YAML)
    if not path.exists():
        logger.error("sources yaml missing: %s", path)
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(raw.get("sources") or [])


def is_ingestible(source: dict[str, Any]) -> bool:
    """Whether this source can be fetched by the current MVP pipeline (RSS/web list)."""
    if source.get("tier") not in {"P0", "P1"}:
        return False
    if source.get("enabled") is False:
        return False
    channel = source.get("channel")
    if channel in _SKIP_CHANNELS:
        return False
    status = (source.get("status") or {}).get("reachability") or ""
    if status in _SKIP_REACHABILITY:
        return False
    if channel == "rss":
        # Require feed URL. Allow ok_rss / pending_probe / empty / needs_recheck.
        if not source.get("feed"):
            return False
        if status and status not in {
            "ok_rss",
            "pending_probe",
            "ok_web",
            "needs_recheck",
            "flaky_ssl",
            "needs_cn_network",
        }:
            return False
        return True
    if channel == "web":
        return bool(source.get("list_url") or source.get("homepage"))
    if channel == "newsletter":
        # treat as web homepage scrape when URL present
        return bool(source.get("homepage") or source.get("list_url"))
    return False


def load_sources(*, ingestible_only: bool = True) -> list[dict[str, Any]]:
    """Load YAML sources for fetch. By default only MVP-ingestible P0/P1 channels."""
    sources = _yaml_sources()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for s in sources:
        sid = s.get("id") or ""
        if not sid:
            continue
        if ingestible_only and not is_ingestible(s):
            continue
        if not ingestible_only and s.get("tier") not in {"P0", "P1", "P2"}:
            continue
        out.append(s)
        seen.add(sid)

    # 合并内置中文列表源（加强国内覆盖；YAML 同 id 优先）
    for s in BUILTIN_CN_LISTS:
        if s["id"] in seen:
            continue
        if ingestible_only and not is_ingestible(s):
            continue
        if s.get("tier") in {"P0", "P1"}:
            out.append(s)
            seen.add(s["id"])
    return out


def seed_sources_to_db() -> dict[str, int]:
    """Upsert full registry (P0–P2) into SQLite sources table; mark ingestible flags."""
    all_sources = _yaml_sources()
    # include builtins not in yaml
    seen = {s.get("id") for s in all_sources}
    for s in BUILTIN_CN_LISTS:
        if s["id"] not in seen:
            all_sources.append(s)

    seeded = 0
    ingestible_n = 0
    for s in all_sources:
        sid = s.get("id")
        if not sid:
            continue
        flag = is_ingestible(s)
        if flag:
            ingestible_n += 1
        db.upsert_source(
            {
                "id": sid,
                "name": s.get("name") or sid,
                "lang": s.get("lang"),
                "region": s.get("region") or [],
                "tier": s.get("tier") or "P2",
                "channel": s.get("channel") or "web",
                "homepage": s.get("homepage"),
                "feed": s.get("feed"),
                "list_url": s.get("list_url"),
                "tracks": s.get("tracks") or [],
                "trust": s.get("trust"),
                "egress": s.get("egress"),
                "enabled": True,
                "ingestible": flag,
                "status": s.get("status") or {},
                "notes": s.get("notes"),
                "raw": {
                    "must_title": s.get("must_title"),
                    "link_re": s.get("link_re"),
                    "alt_feed": s.get("alt_feed"),
                    "wechat_name": s.get("wechat_name"),
                },
            }
        )
        seeded += 1

    db.set_meta("sources_seeded_at", datetime.now(timezone.utc).isoformat())
    db.set_meta("sources_registry_version", "0.2")
    counts = db.count_sources()
    logger.info(
        "seeded sources: yaml+builtin=%s db=%s ingestible=%s",
        seeded,
        counts.get("enabled"),
        counts.get("ingestible"),
    )
    return {"seeded": seeded, "ingestible": ingestible_n, **counts}


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
        resp = await client.get(feed_url, timeout=30.0)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        via = "proxy" if source_needs_proxy(source) and LAWHOT_HTTP_PROXY else "direct"
        logger.warning("feed failed %s (%s): %s", source.get("id"), via, exc)
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
            getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
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
        items.append(
            {
                "id": _entry_id(source["id"], link or title, title),
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


def _preserve_existing_translation(item: dict[str, Any]) -> dict[str, Any]:
    """避免重复抓取时用英文盖掉已译中文。"""
    import json

    with db.connect() as conn:
        old = conn.execute(
            "SELECT title, summary, original_title, raw_json FROM items WHERE id = ?",
            (item["id"],),
        ).fetchone()
    if not old:
        return item
    try:
        raw = json.loads(old["raw_json"] or "{}")
    except Exception:
        raw = {}
    if raw.get("translated") and looks_chinese(old["title"] or ""):
        item["original_title"] = item.get("original_title") or old["original_title"] or item.get(
            "title"
        )
        item["title"] = old["title"]
        item["summary"] = old["summary"] or item.get("summary")
        item["raw_json"] = {**(item.get("raw_json") or {}), "translated": True}
    return item


async def _enrich_candidates(
    *,
    direct_client: httpx.AsyncClient,
    proxy_client: httpx.AsyncClient | None,
    api_client: httpx.AsyncClient,
) -> dict[str, int]:
    """对高分候选补摘要/翻译，控制 API 用量。"""
    start_iso = (datetime.now(timezone.utc) - timedelta(hours=40)).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    rows = db.list_items(
        mode="all",
        window_start_iso=start_iso,
        by="timeline",
        category=None,
        q=None,
        limit=120,
        offset=0,
    )
    pool = []
    for r in rows:
        if not (r["selected"] or (r["score"] or 0) >= 68):
            continue
        try:
            import json as _json

            raw = _json.loads(r["raw_json"] or "{}") if isinstance(r["raw_json"], str) else (r["raw_json"] or {})
        except Exception:
            raw = {}
        need = (
            bad_summary(r["summary"])
            or not raw.get("summarized")
            or needs_translation(r["title"] or "", None, r["lang"])
        )
        if need:
            pool.append(r)
    pool.sort(key=lambda r: float(r["score"] or 0), reverse=True)
    pool = pool[:40]

    enriched = translated = 0
    for r in pool:
        item = dict(r)
        try:
            raw = item.get("raw_json")
            if isinstance(raw, str):
                import json

                item["raw_json"] = json.loads(raw or "{}")
        except Exception:
            item["raw_json"] = {}

        before_title = item.get("title") or ""
        fetch_client = direct_client
        if (item.get("lang") or "") != "zh" and proxy_client is not None:
            fetch_client = proxy_client

        item = await enrich_item(
            item, fetch_client=fetch_client, api_client=api_client, force=True
        )
        if item.get("title") != before_title and looks_chinese(item.get("title") or ""):
            translated += 1
        if not bad_summary(item.get("summary")):
            enriched += 1
        db.upsert_item(item)
    return {"enriched": enriched, "translated": translated, "enrich_pool": len(pool)}


async def run_ingest_once() -> dict[str, Any]:
    seed_stats = seed_sources_to_db()
    sources = load_sources(ingestible_only=True)
    fetched = 0
    stored = 0
    overseas = 0
    domestic = 0
    skipped_no_proxy = 0
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/rss+xml,application/xml,text/xml,*/*",
    }

    direct_client = httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0)
    proxy_client: httpx.AsyncClient | None = None
    if LAWHOT_HTTP_PROXY:
        proxy_client = httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=45.0,
            proxy=LAWHOT_HTTP_PROXY,
        )
        logger.info("overseas proxy enabled")
    else:
        logger.warning("LAWHOT_HTTP_PROXY unset: overseas RSS will be skipped on mainland hosts")

    api_client = make_api_client()
    enrich_stats: dict[str, int] = {}
    edition: dict[str, Any] = {}

    try:
        for source in sources:
            needs_proxy = source_needs_proxy(source)
            if needs_proxy:
                if proxy_client is None:
                    skipped_no_proxy += 1
                    logger.warning("skip overseas source without proxy: %s", source.get("id"))
                    continue
                client = proxy_client
                overseas += 1
            else:
                client = direct_client
                domestic += 1

            channel = source.get("channel")
            if channel in {"web", "newsletter"}:
                batch = await fetch_cn_list(client, source, entry_id_fn=_entry_id)
            elif channel == "rss" or source.get("feed"):
                batch = await fetch_feed(client, source)
            else:
                batch = []

            fetched += len(batch)
            for item in batch:
                item = _preserve_existing_translation(item)
                db.upsert_item(item)
                stored += 1

        enrich_stats = await _enrich_candidates(
            direct_client=direct_client,
            proxy_client=proxy_client,
            api_client=api_client,
        )
        edition = rebuild_edition_for_date(today_shanghai())
    finally:
        await direct_client.aclose()
        if proxy_client is not None:
            await proxy_client.aclose()
        await api_client.aclose()

    stats = {
        "sources": len(sources),
        "sources_seeded": seed_stats.get("seeded", 0),
        "sources_registry": seed_stats.get("enabled", 0),
        "sources_ingestible": seed_stats.get("ingestible", 0),
        "fetched": fetched,
        "stored": stored,
        "translated": enrich_stats.get("translated", 0),
        "enriched": enrich_stats.get("enriched", 0),
        "enrich_pool": enrich_stats.get("enrich_pool", 0),
        "edition_total": (edition or {}).get("counts", {}).get("total", 0),
        "edition_zh": (edition or {}).get("counts", {}).get("zh", 0),
        "edition_en": (edition or {}).get("counts", {}).get("en", 0),
        "overseas_attempted": overseas,
        "domestic_attempted": domestic,
        "skipped_no_proxy": skipped_no_proxy,
        "proxy_configured": bool(LAWHOT_HTTP_PROXY),
        "openai_translate": bool(OPENAI_API_KEY),
    }
    db.set_meta("last_ingest_at", datetime.now(timezone.utc).isoformat())
    db.set_meta("last_ingest_stats", str(stats))
    return stats
