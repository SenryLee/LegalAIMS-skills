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
from .translate import looks_chinese, needs_translation, translate_title_summary
from .web_cn import BUILTIN_CN_LISTS, fetch_cn_list

logger = logging.getLogger("lawhot.ingest")
SHANGHAI = ZoneInfo("Asia/Shanghai")


def load_sources() -> list[dict[str, Any]]:
    raw = yaml.safe_load(Path(SOURCES_YAML).read_text(encoding="utf-8"))
    sources = raw.get("sources") or []
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    for s in sources:
        if s.get("tier") not in {"P0", "P1"}:
            continue
        sid = s.get("id") or ""
        channel = s.get("channel")
        if channel == "rss":
            if not s.get("feed"):
                continue
            status = (s.get("status") or {}).get("reachability")
            if status and status not in {"ok_rss"}:
                continue
            out.append(s)
            seen.add(sid)
        elif channel == "web" and (s.get("list_url") or s.get("homepage")):
            # yaml 里显式配置的中文网页源
            out.append(s)
            seen.add(sid)

    # 合并内置中文列表源（加强国内覆盖）
    for s in BUILTIN_CN_LISTS:
        if s["id"] not in seen and s.get("tier") in {"P0", "P1"}:
            out.append(s)
            seen.add(s["id"])
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


async def _maybe_translate_item(
    item: dict[str, Any],
    *,
    api_client: httpx.AsyncClient | None,
) -> dict[str, Any]:
    if item.get("lang") == "zh":
        return item
    if not needs_translation(item.get("title") or "", item.get("summary"), item.get("lang")):
        return item
    before_title = item.get("title") or ""
    zh_title, zh_summary = await translate_title_summary(
        before_title,
        item.get("summary"),
        client=api_client,
    )
    # 展示用中文；原文标题保留在 original_title
    if item.get("original_title") in (None, "", before_title):
        item["original_title"] = before_title
    item["title"] = zh_title
    item["summary"] = zh_summary
    if zh_title != before_title or looks_chinese(zh_title):
        raw = item.get("raw_json") or {}
        if isinstance(raw, dict):
            item["raw_json"] = {
                **raw,
                "translated": True,
                "translate_engine": "openai" if OPENAI_API_KEY else "google",
            }
    return item


async def run_ingest_once() -> dict[str, Any]:
    sources = load_sources()
    fetched = 0
    stored = 0
    translated = 0
    overseas = 0
    domestic = 0
    skipped_no_proxy = 0
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/rss+xml,application/xml,text/xml,*/*",
    }

    direct_client = httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0)
    proxy_client: httpx.AsyncClient | None = None
    api_client: httpx.AsyncClient | None = None
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

    # 翻译客户端：有 Key 走兼容 API；无 Key 时仍创建，便于后续扩展；Google 回退用同步库
    api_client = httpx.AsyncClient(
        timeout=60.0,
        proxy=LAWHOT_HTTP_PROXY or None,
        follow_redirects=True,
    )

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
            if channel == "web":
                batch = await fetch_cn_list(client, source, entry_id_fn=_entry_id)
            else:
                batch = await fetch_feed(client, source)

            fetched += len(batch)
            for item in batch:
                item = _preserve_existing_translation(item)
                before = item.get("title")
                already_zh = looks_chinese(before or "")
                if not already_zh:
                    item = await _maybe_translate_item(item, api_client=api_client)
                    if item.get("title") != before:
                        translated += 1
                db.upsert_item(item)
                stored += 1
    finally:
        await direct_client.aclose()
        if proxy_client is not None:
            await proxy_client.aclose()
        await api_client.aclose()

    stats = {
        "sources": len(sources),
        "fetched": fetched,
        "stored": stored,
        "translated": translated,
        "overseas_attempted": overseas,
        "domestic_attempted": domestic,
        "skipped_no_proxy": skipped_no_proxy,
        "proxy_configured": bool(LAWHOT_HTTP_PROXY),
        "translate_configured": True,  # OpenAI Key 或 Google 回退
        "openai_translate": bool(OPENAI_API_KEY),
    }
    db.set_meta("last_ingest_at", datetime.now(timezone.utc).isoformat())
    db.set_meta("last_ingest_stats", str(stats))
    maybe_build_daily()
    return stats


def maybe_build_daily() -> None:
    today = datetime.now(SHANGHAI).date().isoformat()
    if db.get_daily(today):
        return
    start = (
        datetime.now(SHANGHAI)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(timezone.utc)
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

    # 日报也偏向法律科技/实务，监管少取
    prefer = {"legaltech": 0, "practice": 1, "litigation": 2, "insight": 3, "vendor": 4, "regulation": 5}
    rows = sorted(rows, key=lambda r: prefer.get(r["category"] or "", 9))

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
        "lead": "今日法律 AI 精选（自动生成初稿，非法律意见）。偏重法律科技、融资与实务，监管只留重点。",
        "sections": [{"name": name, "items": items} for name, items in sections.items()],
        "flashes": [],
        "links": {"lawhot": f"{PUBLIC_BASE_URL}/daily/{today}"},
    }
    db.save_daily(today, payload)
