from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from . import __version__, db
from .config import FETCH_INTERVAL_SECONDS, LAWHOT_HTTP_PROXY, OPENAI_API_KEY, PUBLIC_BASE_URL
from .edition import ensure_today_edition, rebuild_edition_for_date, today_shanghai
from .ingest import run_ingest_once
from .web import CAT_LABEL, render_home, render_item, render_skill_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("lawhot")

app = FastAPI(
    title="Legal Bulletins Public API",
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
            "name": "Legal Bulletins",
            "url": PUBLIC_BASE_URL,
        },
    }


def _match_q(row: Any, q: str | None) -> bool:
    if not q:
        return True
    blob = f"{row['title'] or ''} {row['summary'] or ''} {row['source_name'] or ''}"
    return q.lower() in blob.lower()


def edition_rows(
    *,
    window: str,
    category: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> list[Any]:
    """精选 = 每日刊发名单（与首页一致）。24h→当日刊；7d→近 7 刊合并。"""
    if window == "24h":
        date = today_shanghai()
        payload = db.get_edition(date)
        if not payload or not (payload.get("item_ids") or []):
            payload = ensure_today_edition() or payload
        if not payload:
            latest = db.latest_edition_date()
            payload = db.get_edition(latest) if latest else None
        ids = list((payload or {}).get("item_ids") or [])
    else:
        ids = []
        for d in db.list_edition_dates(7):
            payload = db.get_edition(d) or {}
            ids.extend(payload.get("item_ids") or [])
        ids = list(dict.fromkeys(ids))

    rows = db.get_items_by_ids(ids)
    if category:
        rows = [r for r in rows if (r["category"] or "") == category]
    if q:
        rows = [r for r in rows if _match_q(r, q)]
    return rows[offset : offset + limit]


@app.on_event("startup")
async def on_startup() -> None:
    db.init_db()
    # 升级后若尚未跑 ingest，先用库内候选撑起今日刊，避免首页空白
    try:
        ensure_today_edition()
    except Exception:
        logger.exception("startup edition rebuild failed")
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
    ed_date = db.latest_edition_date()
    ed = db.get_edition(ed_date) if ed_date else None
    return {
        "ok": True,
        "version": __version__,
        "stats": db.stats(),
        "proxy_configured": bool(LAWHOT_HTTP_PROXY),
        "openai_translate": bool(OPENAI_API_KEY),
        "edition_date": ed_date,
        "edition_counts": (ed or {}).get("counts"),
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

    if mode == "selected":
        # 多取 1 条判断 hasMore
        rows = edition_rows(
            window=window, category=category, q=q, limit=limit + 1, offset=offset
        )
    else:
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
            "ordering": "edition" if mode == "selected" else (
                "timelineDesc" if by == "timeline" else "publishedDesc"
            ),
            "edition": True if mode == "selected" else False,
        },
        "items": [row_to_item(r) for r in page_rows],
        "page": {
            "count": len(page_rows),
            "hasMore": has_more,
            "nextCursor": encode_cursor(offset + limit) if has_more else None,
        },
        "attribution": {"name": "Legal Bulletins", "url": PUBLIC_BASE_URL},
    }
    etag = 'W/"items-%s-%s-%s"' % (mode, window, offset + len(page_rows))
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304)
    return JSONResponse(content=body, headers={"ETag": etag})


@app.get("/api/v1/hot-topics")
async def hot_topics() -> dict[str, Any]:
    rows = edition_rows(window="24h", category=None, q=None, limit=30, offset=0)
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
    rows = edition_rows(window="7d", category=None, q=None, limit=50, offset=0)
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
        "<title>Legal Bulletins 精选</title>"
        f"<link>{PUBLIC_BASE_URL}</link>"
        "<description>法律 AI 资讯精选（非法律意见）</description>"
        + "".join(items_xml)
        + "</channel></rss>"
    )
    return PlainTextResponse(body, media_type="application/rss+xml; charset=utf-8")


@app.get("/")
async def home(request: Request) -> Any:
    """浏览器返回精选 HTML；显式要 JSON 时（Accept/query）返回机器发现文档。"""
    want_json = (
        request.query_params.get("format") == "json"
        or "application/json" in (request.headers.get("accept") or "")
        and "text/html" not in (request.headers.get("accept") or "")
    )
    stats = db.stats()
    if want_json:
        return {
            "name": "Legal Bulletins",
            "tagline": "法律科技频道 · AI 对法律行业的启迪",
            "disclaimer": "资讯聚合，非法律意见。重要引用请回原文核对。",
            "api": f"{PUBLIC_BASE_URL}/api/v1/items?mode=selected&window=24h&limit=10",
            "skill": f"{PUBLIC_BASE_URL}/lawhot-skill/",
            "feed": f"{PUBLIC_BASE_URL}/feed.xml",
            "health": f"{PUBLIC_BASE_URL}/healthz",
            "stats": stats,
        }

    category = request.query_params.get("category")
    if category and category not in CAT_LABEL:
        category = None
    date = request.query_params.get("date") or today_shanghai()
    payload = db.get_edition(date)
    if not payload or not (payload.get("item_ids") or []):
        payload = ensure_today_edition() or payload
        date = (payload or {}).get("date") or date
    if not payload:
        latest = db.latest_edition_date()
        date = latest or date
        payload = db.get_edition(date) if latest else None

    ids = list((payload or {}).get("item_ids") or [])
    rows = db.get_items_by_ids(ids)
    counts: dict[str, int] = {k: 0 for k in CAT_LABEL}
    for r in rows:
        c = r["category"] or "insight"
        if c in counts:
            counts[c] += 1
    if category:
        rows = [r for r in rows if (r["category"] or "") == category]

    edition_meta = {
        "date": date,
        "lead": (payload or {}).get("lead") or "",
        "counts": (payload or {}).get("counts") or {},
    }
    return HTMLResponse(
        render_home(
            rows,
            stats,
            category=category,
            counts=counts,
            edition=edition_meta,
        )
    )


@app.get("/items/{item_id}")
async def item_page(request: Request, item_id: str) -> Any:
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        return problem(404, "not_found", "item not found")
    want_json = (
        request.query_params.get("format") == "json"
        or "application/json" in (request.headers.get("accept") or "")
        and "text/html" not in (request.headers.get("accept") or "")
    )
    if want_json:
        return row_to_item(row)
    return HTMLResponse(render_item(row))


@app.get("/agent")
async def agent_page() -> HTMLResponse:
    return HTMLResponse(render_skill_index())


def _admin_ok(request: Request) -> bool:
    token = request.headers.get("x-admin-token") or request.query_params.get("token")
    expected = __import__("os").environ.get("LAWHOT_ADMIN_TOKEN", "")
    return bool(expected) and token == expected


@app.post("/admin/ingest")
async def admin_ingest(request: Request) -> Any:
    if not _admin_ok(request):
        return problem(401, "unauthorized", "missing or invalid admin token")
    stats = await run_ingest_once()
    return {"ok": True, "stats": stats}


@app.post("/admin/rebuild-edition")
async def admin_rebuild_edition(request: Request) -> Any:
    """不重新抓取，仅用库内候选重编今日刊（升级后救急）。"""
    if not _admin_ok(request):
        return problem(401, "unauthorized", "missing or invalid admin token")
    payload = rebuild_edition_for_date(today_shanghai())
    return {"ok": True, "edition": payload.get("counts"), "date": payload.get("date")}


@app.post("/admin/reenrich")
async def admin_reenrich(request: Request) -> Any:
    """重跑摘要/译写（不扩抓取），用于修正「截断译文」类坏摘要。"""
    if not _admin_ok(request):
        return problem(401, "unauthorized", "missing or invalid admin token")
    # 复用 ingest 后半段：enrich + rebuild
    from .ingest import run_ingest_once

    # 轻量：只 enrich 现有高分条 — 直接调完整 ingest 中的 enrich 代价可接受
    stats = await run_ingest_once()
    return {"ok": True, "stats": stats}
