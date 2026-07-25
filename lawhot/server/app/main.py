from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from . import __version__, db
from .config import FETCH_INTERVAL_SECONDS, LAWHOT_HTTP_PROXY, PUBLIC_BASE_URL
from .ingest import run_ingest_once

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("lawhot")

app = FastAPI(
    title="LawHOT Public API",
    version=__version__,
    description="Legal AI news aggregation — anonymous read-only v1",
)

CATEGORIES = {"regulation", "litigation", "legaltech", "practice", "insight", "vendor"}
_ingest_task: asyncio.Task | None = None


def problem(
    status: int,
    code: str,
    detail: str,
    title: str | None = None,
) -> JSONResponse:
    request_id = "req_" + secrets.token_hex(6)
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"/problems/{code.replace('_', '-')}",
            "title": title or code.replace("_", " ").title(),
            "status": status,
            "detail": detail,
            "code": code,
            "requestId": request_id,
        },
    )


def window_start(window: str) -> datetime:
    now = datetime.now(timezone.utc)
    if window == "24h":
        return now - timedelta(hours=24)
    return now - timedelta(days=7)


def encode_cursor(offset: int) -> str:
    return f"o_{offset}"


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    if not cursor.startswith("o_"):
        raise ValueError("invalid cursor")
    return int(cursor[2:])


def row_to_item(row: Any) -> dict[str, Any]:
    lawhot = f"{PUBLIC_BASE_URL}/items/{row['id']}"
    return {
        "id": row["id"],
        "title": row["title"],
        "originalTitle": row["original_title"],
        "summary": row["summary"],
        "source": {"name": row["source_name"]},
        "links": {
            "lawhot": lawhot,
            "aihot": lawhot,  # compat alias for aihot-shaped prompts
            "original": row["original_url"],
        },
        "publishedAt": row["published_at"],
        "discoveredAt": row["discovered_at"],
        "category": row["category"],
        "score": row["score"],
        "selected": bool(row["selected"]),
        "attribution": {
            "name": "LawHOT",
            "url": PUBLIC_BASE_URL,
        },
    }


@app.on_event("startup")
async def on_startup() -> None:
    db.init_db()
    global _ingest_task
    _ingest_task = asyncio.create_task(_ingest_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if _ingest_task:
        _ingest_task.cancel()


async def _ingest_loop() -> None:
    # first run soon after boot
    await asyncio.sleep(2)
    while True:
        try:
            stats = await run_ingest_once()
            logger.info("ingest done %s", stats)
        except Exception:
            logger.exception("ingest failed")
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "version": __version__,
        "stats": db.stats(),
        "proxy_configured": bool(LAWHOT_HTTP_PROXY),
        "last_ingest_at": db.get_meta("last_ingest_at"),
        "last_ingest_stats": db.get_meta("last_ingest_stats"),
    }


@app.get("/api/v1/items")
async def items(
    request: Request,
    mode: str = Query("selected", pattern="^(selected|all)$"),
    window: str = Query("7d", pattern="^(24h|7d)$"),
    by: str = Query("timeline", pattern="^(timeline|published)$"),
    category: str | None = Query(None),
    q: str | None = Query(None, min_length=2, max_length=200),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None),
):
    if category is not None and category not in CATEGORIES:
        return problem(400, "invalid_request", f"unknown category: {category}")
    try:
        offset = decode_cursor(cursor)
    except Exception:
        return problem(400, "invalid_cursor", "cursor is invalid for this query")

    start = window_start(window).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = db.list_items(
        mode=mode,
        window_start_iso=start,
        by=by,
        category=category,
        q=q,
        limit=limit + 1,
        offset=offset,
    )
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    body = {
        "schemaVersion": 1,
        "query": {
            "mode": mode,
            "category": category,
            "q": q,
            "window": window,
            "by": by,
            "ordering": "timelineDesc" if by == "timeline" else "publishedDesc",
        },
        "items": [row_to_item(r) for r in page_rows],
        "page": {
            "count": len(page_rows),
            "hasMore": has_more,
            "nextCursor": encode_cursor(offset + limit) if has_more else None,
        },
        "attribution": {"name": "LawHOT", "url": PUBLIC_BASE_URL},
    }
    etag = 'W/"items-%s-%s-%s"' % (mode, window, offset + len(page_rows))
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return JSONResponse(content=body, headers={"ETag": etag})


@app.get("/api/v1/hot-topics")
async def hot_topics() -> dict[str, Any]:
    start = window_start("24h").replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = db.list_items(
        mode="selected",
        window_start_iso=start,
        by="timeline",
        category=None,
        q=None,
        limit=30,
        offset=0,
    )
    # naive cluster by normalized title prefix
    buckets: dict[str, list[Any]] = {}
    for r in rows:
        key = (r["title"] or "")[:24].lower()
        buckets.setdefault(key, []).append(r)
    ranked = sorted(buckets.values(), key=lambda xs: (-len(xs), -(xs[0]["score"] or 0)))
    items_out = []
    for group in ranked[:8]:
        head = group[0]
        source_names = []
        for g in group:
            name = g["source_name"]
            if name not in source_names:
                source_names.append(name)
        items_out.append(
            {
                "title": head["title"],
                "summary": head["summary"],
                "latestAt": head["discovered_at"],
                "sourceCount": len(source_names),
                "signalCount": len(group),
                "sourceNames": source_names,
                "links": {
                    "lawhot": f"{PUBLIC_BASE_URL}/items/{head['id']}",
                    "original": head["original_url"],
                },
            }
        )
    return {"schemaVersion": 1, "count": len(items_out), "items": items_out}


@app.get("/api/v1/dailies")
async def dailies(limit: int = Query(7, ge=1, le=30)) -> dict[str, Any]:
    items_out = []
    for d in db.list_dailies(limit):
        items_out.append(
            {
                "date": d["date"],
                "title": d["title"],
                "links": {"lawhot": d.get("links", {}).get("lawhot") or f"{PUBLIC_BASE_URL}/daily/{d['date']}"},
            }
        )
    return {"schemaVersion": 1, "count": len(items_out), "items": items_out}


@app.get("/api/v1/dailies/latest")
async def dailies_latest() -> Any:
    date = db.latest_daily_date()
    if not date:
        return problem(404, "not_found", "no daily report available yet")
    return await dailies_by_date(date)


@app.get("/api/v1/dailies/{date}")
async def dailies_by_date(date: str) -> Any:
    if not (len(date) == 10 and date[4] == "-" and date[7] == "-"):
        return problem(400, "invalid_request", "date must be YYYY-MM-DD")
    payload = db.get_daily(date)
    if not payload:
        return problem(404, "not_found", f"no daily for {date}")
    return {"schemaVersion": 1, "report": payload}


@app.get("/feed.xml")
async def feed_xml() -> PlainTextResponse:
    start = window_start("7d").replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows = db.list_items(
        mode="selected",
        window_start_iso=start,
        by="timeline",
        category=None,
        q=None,
        limit=50,
        offset=0,
    )
    items_xml = []
    for r in rows:
        link = f"{PUBLIC_BASE_URL}/items/{r['id']}"
        desc = (r["summary"] or "").replace("&", "&amp;").replace("<", "&lt;")
        title = (r["title"] or "").replace("&", "&amp;").replace("<", "&lt;")
        items_xml.append(
            f"<item><title>{title}</title><link>{link}</link>"
            f"<guid isPermaLink=\"false\">{r['id']}</guid>"
            f"<description>{desc}</description></item>"
        )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0"><channel>'
        "<title>LawHOT 精选</title>"
        f"<link>{PUBLIC_BASE_URL}</link>"
        "<description>法律 AI 资讯精选（非法律意见）</description>"
        + "".join(items_xml)
        + "</channel></rss>"
    )
    return PlainTextResponse(body, media_type="application/rss+xml; charset=utf-8")


@app.get("/")
async def home() -> dict[str, Any]:
    return {
        "name": "LawHOT",
        "tagline": "全球法律 AI 资讯 · AI 对法律行业的启迪",
        "disclaimer": "资讯聚合，非法律意见。重要引用请回原文核对。",
        "api": f"{PUBLIC_BASE_URL}/api/v1/items?mode=selected&window=24h&limit=10",
        "skill": f"{PUBLIC_BASE_URL}/lawhot-skill/",
        "feed": f"{PUBLIC_BASE_URL}/feed.xml",
        "health": f"{PUBLIC_BASE_URL}/healthz",
        "stats": db.stats(),
    }


@app.get("/items/{item_id}")
async def item_page(item_id: str) -> dict[str, Any]:
    # MVP: JSON stub page; nginx can later serve HTML.
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return problem(404, "not_found", "item not found")
    return row_to_item(row)


@app.post("/admin/ingest")
async def admin_ingest(request: Request) -> Any:
    token = request.headers.get("x-admin-token") or request.query_params.get("token")
    expected = __import__("os").environ.get("LAWHOT_ADMIN_TOKEN", "")
    if not expected or token != expected:
        return problem(401, "unauthorized", "missing or invalid admin token")
    stats = await run_ingest_once()
    return {"ok": True, "stats": stats}
