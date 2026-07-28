from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

from .classify import classify_category, relevance_ok, score_item, should_select

logger = logging.getLogger("lawhot.web_cn")

# 内置中文列表：法律科技优先；政务源降为 P1 且关键词更严
BUILTIN_CN_LISTS: list[dict[str, Any]] = [
    {
        "id": "zh-lawyeah",
        "name": "律页科技",
        "list_url": "https://www.lawyeah.cn/article",
        "link_re": r'href=["\'](https?://www\.lawyeah\.cn/[^"\']+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"AI|人工智能|法律|律师|律所|大模型|智能|合同|科技",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "specialty_media",
        "tracks": ["ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-autopilot-law",
        "name": "智律云博客",
        "list_url": "https://autopilot.law/blog",
        "link_re": r'href=["\'](https?://autopilot\.law/[^"\']+)["\'][^>]*>([^<]{8,120})<',
        "must_title": r"AI|法律|律师|Harvey|Legora|合同|律所|大模型|智能|Copilot",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "specialty_media",
        "tracks": ["ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-ciplawyer-ai",
        "name": "中国知识产权律师网",
        "list_url": "https://www.ciplawyer.cn/channels/zh/",
        "link_re": r'href=["\'](https?://www\.ciplawyer\.cn/[^"\']+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"人工智能|AI|大模型|算法|生成式|深度合成|训练数据|著作权|版权",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "specialty_media",
        "tracks": ["law_x_ai", "ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-legaldaily-ai",
        "name": "法治网 / 法治日报",
        "list_url": "http://www.legaldaily.com.cn/",
        "link_re": r'href=["\']([^"\']+)["\'][^>]*>([^<]{8,80})<',
        "must_title": r"法律科技|法律大模型|智能合同|合同审查|律师.*AI|AI.*律师|法律 AI|人工智能.*律师",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "official",
        "tracks": ["ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-chinacourt",
        "name": "中国法院网",
        "list_url": "https://www.chinacourt.org/index.shtml",
        "link_re": r'href=["\'](https?://www\.chinacourt\.org/article/detail/\d+/[^"\']+\.shtml)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"法律科技|人工智能.*审判|智能辅助|法律大模型|AI.*法官|生成式",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "official",
        "tracks": ["ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-cac-news",
        "name": "中国网信网",
        "list_url": "https://www.cac.gov.cn/wxzcfg/index.htm",
        "link_re": r'href=["\']([^"\']+\.htm)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"生成式人工智能|深度合成|人工智能.*办法|算法推荐.*规定",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "official",
        "tracks": ["law_x_ai"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-secrss",
        "name": "安全内参",
        "list_url": "https://www.secrss.com/",
        "link_re": r'href=["\'](https?://www\.secrss\.com/articles/\d+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"法律|合规|诉讼|律师|人工智能法|数据出境|个人信息.*AI|大模型.*合规",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "specialty_media",
        "tracks": ["law_x_ai", "ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-36kr-ai",
        "name": "36氪",
        "list_url": "https://www.36kr.com/information/AI/",
        "link_re": r'href=["\'](/p/\d+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"法律|律师|律所|法务|合规|诉讼|版权|LegalTech|法律科技|合同审查",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "general_media",
        "tracks": ["ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-fayan-bigdata-builtin",
        "name": "中国司法大数据服务网",
        "list_url": "https://data.court.gov.cn/",
        "link_re": r'href=["\']([^"\']+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"人工智能|智能|大数据|智慧法院|法研|算法|数字|信息化|法律科技",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "official",
        "tracks": ["ai_x_law", "law_x_ai"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-jiqizhixin-builtin",
        "name": "机器之心",
        "list_url": "https://www.jiqizhixin.com/",
        "link_re": r'href=["\']([^"\']+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"法律|合规|监管|版权|诉讼|司法|律师|安全|治理|开源许可|人工智能法",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "general_media",
        "tracks": ["vendor_frontier", "law_x_ai"],
        "channel": "web",
        "egress": "domestic",
    },
]


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def fetch_cn_list(
    client: httpx.AsyncClient,
    source: dict[str, Any],
    *,
    entry_id_fn,
) -> list[dict[str, Any]]:
    list_url = source.get("list_url") or source.get("homepage")
    if not list_url:
        return []
    link_re = source.get("link_re") or r'href=["\']([^"\']+)["\'][^>]*>([^<]{8,100})<'
    must_title = source.get("must_title") or (
        r"法律科技|法律大模型|法律 AI|LegalTech|合同审查|律师|律所|法务"
    )
    try:
        resp = await client.get(list_url, timeout=25.0)
        resp.raise_for_status()
        html = resp.content.decode(resp.encoding or "utf-8", errors="ignore")
        if not html.strip() or (resp.encoding and "iso-8859" in resp.encoding.lower()):
            html = resp.content.decode("gb18030", errors="ignore")
    except Exception as exc:
        logger.warning("cn list failed %s: %s", source.get("id"), exc)
        return []

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for m in re.finditer(link_re, html, re.I):
        href, title = m.group(1), _clean(m.group(2))
        if not title or not re.search(must_title, title, re.I):
            continue
        url = urljoin(list_url, href)
        if url in seen or url.startswith("javascript:"):
            continue
        seen.add(url)
        if not relevance_ok(title, "", source):
            continue
        category = classify_category(title, "", source)
        score = score_item(title, "", source, category)
        selected = should_select(score, category, source)
        discovered = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        items.append(
            {
                "id": entry_id_fn(source["id"], url, title),
                "title": title,
                "original_title": title,
                "summary": None,  # 由 enrich 补全文摘要
                "source_id": source["id"],
                "source_name": source.get("name") or source["id"],
                "original_url": url,
                "published_at": None,
                "discovered_at": discovered,
                "category": category,
                "score": score,
                "selected": selected,
                "track": ",".join(source.get("tracks") or []),
                "lang": source.get("lang") or "zh",
                "raw_json": {"list_url": list_url},
            }
        )
        if len(items) >= 20:
            break
    logger.info("cn list %s: %s items", source.get("id"), len(items))
    return items
