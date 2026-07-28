"""为刊发候选写真正摘要：抓正文 + DeepSeek 概括（禁止正文截断冒充摘要）。"""

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
from .translate import looks_chinese, needs_translation

logger = logging.getLogger("lawhot.enrich")

_PLACEHOLDER = re.compile(r"^(来源：|列表页摘录|暂无摘要|详情见原文)", re.I)
# 像「开篇翻译/作者栏/半截英文」而非摘要
_BAD_SUMMARY = re.compile(
    r"作者[:：]|阅读时间|分钟\s*\||exclusively\s*$|&#\d+;|"
    r"本文由|点击阅读|扫码|责任编辑|来源：.{0,20}列表",
    re.I,
)


def weak_summary(summary: str | None) -> bool:
    s = (summary or "").strip()
    return (not s) or len(s) < 28 or bool(_PLACEHOLDER.search(s))


def bad_summary(summary: str | None) -> bool:
    """判定现有 summary 是否不合格（截断译文、作者栏等）。"""
    s = (summary or "").strip()
    if weak_summary(s):
        return True
    if _BAD_SUMMARY.search(s):
        return True
    # 半截句：以英文单词残片结尾，或省略号且过短
    if re.search(r"[A-Za-z]{2,}$", s) and looks_chinese(s[:40]):
        return True
    if s.endswith(("…", "...", "……")) and len(s) < 120:
        return True
    # 过长更像摘录而非摘要
    if len(s) > 420:
        return True
    return False


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
    node = (
        soup.select_one("article")
        or soup.select_one(".article-content")
        or soup.select_one(".content")
        or soup.select_one("#content")
        or soup.select_one(".post-content")
        or soup.select_one(".entry-content")
        or soup.body
    )
    if not node:
        return ""
    text = re.sub(r"\s+", " ", node.get_text(" ", strip=True))
    return text[:5000]


def _chat_url() -> str:
    base = (OPENAI_BASE_URL or "https://api.deepseek.com").rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    return f"{base}/chat/completions"


async def llm_write_summary(
    title: str,
    excerpt: str,
    *,
    client: httpx.AsyncClient,
    original_title: str | None = None,
) -> str | None:
    """写抽象摘要：发生了什么 / 对法律科技为何重要。"""
    if not OPENAI_API_KEY:
        return None
    system = (
        "你是「Legal Bulletins」法律科技频道编辑。"
        "根据标题与原文材料，用简体中文写真正的内容摘要（不是翻译开篇、不是作者介绍）。"
        "要求：\n"
        "1) 2～4 句，约 80～180 字；\n"
        "2) 先写清事实（产品/公司/案件/融资/规则），再写对律师、法务或 LegalTech 的要点；\n"
        "3) 禁止输出作者、阅读时间、责任编辑；禁止半截英文；禁止「本文介绍了」套话；\n"
        "4) 若材料不足，只写能确认的信息，不要编造。\n"
        '只输出 JSON：{"summary":"..."}'
    )
    user = (
        f"展示标题：{title}\n"
        f"原文标题：{original_title or title}\n"
        f"原文材料：\n{(excerpt or '')[:4200]}"
    )
    payload = {
        "model": OPENAI_MODEL or "deepseek-v4-flash",
        "temperature": 0.25,
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
        resp = await client.post(_chat_url(), headers=headers, json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        out = (parsed.get("summary") or "").strip()
        if not out or bad_summary(out):
            return None
        return out
    except Exception as exc:
        logger.warning("llm summary failed: %s", exc)
        return None


async def llm_translate_title(
    title: str,
    *,
    client: httpx.AsyncClient,
) -> str | None:
    if not OPENAI_API_KEY or not needs_translation(title, None, None):
        return None
    system = (
        "将法律科技新闻英文标题译为简洁专业的简体中文。"
        "保留公司名/产品名专名。"
        '只输出 JSON：{"title":"..."}'
    )
    payload = {
        "model": OPENAI_MODEL or "deepseek-v4-flash",
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": title[:500]},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = await client.post(_chat_url(), headers=headers, json=payload)
        resp.raise_for_status()
        parsed = json.loads(resp.json()["choices"][0]["message"]["content"])
        out = (parsed.get("title") or "").strip()
        return out or None
    except Exception as exc:
        logger.warning("llm title translate failed: %s", exc)
        return None


async def enrich_item(
    item: dict[str, Any],
    *,
    fetch_client: httpx.AsyncClient,
    api_client: httpx.AsyncClient,
    force: bool = False,
) -> dict[str, Any]:
    """译标题 + 写真正摘要。绝不把正文截断当作摘要。"""
    title = item.get("title") or ""
    lang = item.get("lang") or ""
    raw = item.get("raw_json") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except Exception:
            raw = {}
    if not isinstance(raw, dict):
        raw = {}

    # 1) 英文标题 → 中文展示；原文进 original_title
    if needs_translation(title, None, lang) or (
        lang != "zh" and not looks_chinese(title)
    ):
        if item.get("original_title") in (None, "", title):
            item["original_title"] = title
        zh_title = await llm_translate_title(title, client=api_client)
        if zh_title:
            item["title"] = zh_title
            title = zh_title
            raw["translated"] = True

    # 2) 已有合格摘要且非强制 → 跳过
    if not force and raw.get("summarized") and not bad_summary(item.get("summary")):
        item["raw_json"] = raw
        return item

    # 3) 抓正文，用 LLM 写摘要（中英文源同一流程；禁止正文截断冒充）
    excerpt = await fetch_article_excerpt(fetch_client, item.get("original_url") or "")
    material = excerpt or (item.get("summary") or "")
    if material and OPENAI_API_KEY:
        polished = await llm_write_summary(
            title,
            material,
            client=api_client,
            original_title=item.get("original_title"),
        )
        if polished:
            item["summary"] = polished
            raw["summarized"] = True
            raw["summary_engine"] = "deepseek"
            item["raw_json"] = raw
            return item

    # 4) 无 Key / 失败：绝不截断正文；保留原摘要或短提示
    if bad_summary(item.get("summary")):
        item["summary"] = "摘要生成中，请先阅读原文了解详情。"
    item["raw_json"] = raw
    return item


def make_api_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=90.0,
        proxy=llm_http_proxy(),
        follow_redirects=True,
    )
