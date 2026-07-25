from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

from .config import (
    LAWHOT_HTTP_PROXY,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

logger = logging.getLogger("lawhot.translate")

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def looks_chinese(text: str) -> bool:
    if not text:
        return False
    cjk = len(_CJK_RE.findall(text))
    return cjk >= max(4, int(len(text) * 0.2))


def needs_translation(title: str, summary: str | None, lang: str | None) -> bool:
    if lang == "zh":
        return False
    sample = f"{title or ''}\n{summary or ''}"
    if looks_chinese(sample):
        return False
    letters = len(re.findall(r"[A-Za-z]", sample))
    return letters >= 8


def _apply_proxy_env() -> None:
    if not LAWHOT_HTTP_PROXY:
        return
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        os.environ.setdefault(key, LAWHOT_HTTP_PROXY)


async def _translate_openai(
    title: str,
    summary: str | None,
    *,
    client: httpx.AsyncClient,
) -> tuple[str, str | None] | None:
    if not OPENAI_API_KEY:
        return None
    base = (OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    system = (
        "你是法律科技资讯编辑。把英文标题和摘要译成简洁、专业的中文，"
        "保留公司名/产品名/法案名常用译法或原文专名。"
        '只输出 JSON：{"title":"...","summary":"..."}，不要 markdown。'
    )
    user = f"标题：{title}\n摘要：{summary or ''}"
    payload = {
        "model": OPENAI_MODEL or "gpt-4o-mini",
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
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed: dict[str, Any] = json.loads(content)
        new_title = (parsed.get("title") or title).strip()
        new_summary = parsed.get("summary")
        if new_summary is not None:
            new_summary = str(new_summary).strip()
        else:
            new_summary = summary
        if new_title:
            return new_title, new_summary
    except Exception as exc:
        logger.warning("openai translate failed: %s", exc)
    return None


def _translate_google(title: str, summary: str | None) -> tuple[str, str | None] | None:
    """无 API Key 时的回退：经代理调用 Google 翻译。"""
    try:
        from deep_translator import GoogleTranslator

        _apply_proxy_env()
        gt = GoogleTranslator(source="auto", target="zh-CN")
        new_title = (gt.translate(title[:4500]) or "").strip()
        new_summary = summary
        if summary:
            new_summary = (gt.translate(summary[:4500]) or "").strip() or summary
        if new_title:
            return new_title, new_summary
    except Exception as exc:
        logger.warning("google translate failed: %s", exc)
    return None


async def translate_title_summary(
    title: str,
    summary: str | None,
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, str | None]:
    """Return (title_zh, summary_zh). Failure → originals."""
    if not needs_translation(title, summary, None):
        return title, summary

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            timeout=60.0,
            proxy=LAWHOT_HTTP_PROXY or None,
            follow_redirects=True,
        )
    assert client is not None
    try:
        out = await _translate_openai(title, summary, client=client)
        if out:
            return out
    finally:
        if own_client:
            await client.aclose()

    out = _translate_google(title, summary)
    if out:
        return out
    return title, summary
