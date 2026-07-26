"""为刊发候选补摘要：抓正文片段 + DeepSeek 润色/翻译。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    USER_AGENT,
    llm_http_proxy,
)
from .translate import looks_chinese, needs_translation, translate_title_summary

logger = logging.getLogger("lawhot.enrich")

_PLACEHOLDER = re.compile(r"^(来源：|列表页摘录|暂无摘要|详情见原文)", re.I)


def weak_summary(summary: str | None) -> bool:
    s = (summary or "").strip()
    return (not s) or len(s) < 28 or bool(_PLACEHOLDER.search(s))


async def fetch_article_excerpt(client: httpx.AsyncClient, url: str) -> str:
    if not url or not url.startswith("http"):
        return ""
    try:
        resp = await client.get(url, timeout=25.0, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        raw = resp.content
        html = raw.decode(resp.encoding or "utf-8", errors="ignore")
        if not html.strip():
            html = raw.decode("gb18030", errors="ignore")
    except Exception as exc:
        logger.info("excerpt fetch fail %s: %s", url[:80], exc)
        return ""

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    # 常见正文容器
    node = (
        soup.select_one("article")
        or soup.select_one(".article-content")
        or soup.select_one(".content")
        or soup.select_one("#content")
        or soup.select_one(".post-content")
        or soup.body
    )
    if not node:
        return ""
    text = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
    return text[:3500]


async def llm_polish_summary(
    title: str,
    excerpt: str,
    *,
    client: httpx.AsyncClient,
    lang_hint: str = "zh",
) -> str | None:
    if not OPENAI_API_KEY:
        return None
    base = (OPENAI_BASE_URL or "https://api.deepseek.com").rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    url = f"{base}/chat/completions"
    system = (
        "你是法律科技频道编辑。根据标题与原文摘录，写 2～4 句简体中文摘要，"
        "偏重产品、律所/法务落地、融资或诉讼要点；不要空话，不要「本文介绍」。"
        '只输出 JSON：{"summary":"..."}'
    )
    user = f"标题：{title}\n语言提示：{lang_hint}\n摘录：{excerpt[:2800]}"
    payload = {
        "model": OPENAI_MODEL or "deepseek-v4-flash",
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        out = (parsed.get("summary") or "").strip()
        return out or None
    except Exception as exc:
        logger.warning("llm summary failed: %s", exc)
        return None


async def enrich_item(
    item: dict[str, Any],
    *,
    fetch_client: httpx.AsyncClient,
    api_client: httpx.AsyncClient,
) -> dict[str, Any]:
    """补摘要 + 英译中。"""
    title = item.get("title") or ""
    summary = item.get("summary")
    lang = item.get("lang") or ""

    # 先译标题（英文）
    if needs_translation(title, summary, lang):
        if item.get("original_title") in (None, "", title):
            item["original_title"] = title
        zh_title, zh_summary = await translate_title_summary(
            title, summary, client=api_client
        )
        item["title"] = zh_title
        if zh_summary and not weak_summary(zh_summary):
            item["summary"] = zh_summary
        title = item["title"]
        summary = item.get("summary")
        raw = item.get("raw_json") or {}
        if isinstance(raw, dict):
            item["raw_json"] = {**raw, "translated": True}

    if not weak_summary(item.get("summary")):
        return item

    excerpt = await fetch_article_excerpt(fetch_client, item.get("original_url") or "")
    polished = None
    if excerpt:
        polished = await llm_polish_summary(
            title,
            excerpt,
            client=api_client,
            lang_hint="zh" if looks_chinese(title) else "en",
        )
    if polished:
        item["summary"] = polished
    elif excerpt:
        # 无 LLM 时截取可读片段
        item["summary"] = excerpt[:280].rstrip() + ("…" if len(excerpt) > 280 else "")
    return item


def make_api_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=90.0,
        proxy=llm_http_proxy(),
        follow_redirects=True,
    )
