from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

from .classify import classify_category, relevance_ok, score_item, should_select

logger = logging.getLogger("lawhot.web_cn")

# 内置中文列表页抓取：偏法律科技 / 司法信息化 / AI×法律；监管专题少而精
BUILTIN_CN_LISTS: list[dict[str, Any]] = [
    {
        "id": "zh-legaldaily-ai",
        "name": "法治网 / 法治日报",
        "list_url": "http://www.legaldaily.com.cn/",
        "link_re": r'href=["\']([^"\']+)["\'][^>]*>([^<]{8,80})<',
        "must_title": r"人工智能|大模型|算法|智能|ChatGPT|生成式|深度合成|法律科技|智慧法院|数字检察|信息化",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "specialty_media",
        "tracks": ["law_x_ai", "ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-chinacourt",
        "name": "中国法院网",
        "list_url": "https://www.chinacourt.org/index.shtml",
        "link_re": r'href=["\'](https?://www\.chinacourt\.org/article/detail/\d+/[^"\']+\.shtml)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"人工智能|智能|算法|信息化|智慧法院|数字|大数据|网络|法律科技",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "official",
        "tracks": ["law_x_ai", "ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-rmfyb",
        "name": "人民法院报",
        "list_url": "http://rmfyb.chinacourt.org/paper/html/node_2.htm",
        "link_re": r'href=["\']([^"\']+\.htm)["\'][^>]*>([^<]{8,90})<',
        "must_title": r"人工智能|智能|算法|智慧法院|信息化|数字|大数据|网络|科技",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "official",
        "tracks": ["ai_x_law", "law_x_ai"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-cac-news",
        "name": "中国网信网",
        "list_url": "https://www.cac.gov.cn/wxzcfg/index.htm",
        "link_re": r'href=["\']([^"\']+\.htm)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"人工智能|生成式|深度合成|算法|大模型|智能",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "official",
        "tracks": ["law_x_ai"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-spp",
        "name": "最高人民检察院网",
        "list_url": "https://www.spp.gov.cn/",
        "link_re": r'href=["\']([^"\']+)["\'][^>]*>([^<]{8,90})<',
        "must_title": r"人工智能|数字检察|大数据|智能|算法|网络犯罪|深度合成|法律科技",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "official",
        "tracks": ["law_x_ai", "ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-jcrb",
        "name": "正义网",
        "list_url": "https://www.jcrb.com/",
        "link_re": r'href=["\'](https?://[^"\']*jcrb\.com[^"\']+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"人工智能|智能|算法|数字检察|大数据|网络|科技|信息化",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "specialty_media",
        "tracks": ["ai_x_law", "law_x_ai"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-secrss",
        "name": "安全内参",
        "list_url": "https://www.secrss.com/",
        "link_re": r'href=["\'](https?://www\.secrss\.com/articles/\d+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"法律|合规|监管|诉讼|司法|律师|数据出境|个人信息|人工智能法|\bAI\b|大模型",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "specialty_media",
        "tracks": ["law_x_ai", "ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-court-gov",
        "name": "最高人民法院网",
        "list_url": "https://www.court.gov.cn/",
        "link_re": r'href=["\']([^"\']+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"人工智能|智慧法院|智能|信息化|数字|大数据|算法|科技法庭|在线诉讼",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P0",
        "trust": "official",
        "tracks": ["ai_x_law", "law_x_ai"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-thepaper-tech",
        "name": "澎湃新闻·科技",
        "list_url": "https://www.thepaper.cn/channel_119918",
        "link_re": r'href=["\'](/newsDetail_forward_\d+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"法律|律师|诉讼|合规|著作权|版权|监管|司法|法院|数据出境|人工智能法|融资",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "general_media",
        "tracks": ["law_x_ai", "ai_x_law"],
        "channel": "web",
        "egress": "domestic",
    },
    {
        "id": "zh-36kr-ai",
        "name": "36氪",
        "list_url": "https://www.36kr.com/information/AI/",
        "link_re": r'href=["\'](/p/\d+)["\'][^>]*>([^<]{8,100})<',
        "must_title": r"法律|律师|律所|合规|诉讼|版权|司法|融资|Legal|法律科技|合同",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P1",
        "trust": "general_media",
        "tracks": ["ai_x_law"],
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
        r"人工智能|大模型|法律科技|智慧法院|智能|算法|生成式|深度合成|"
        r"融资|律所|诉讼|合规|数字检察"
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
                "summary": f"来源：{source.get('name')} 列表页摘录。详情见原文。",
                "source_id": source["id"],
                "source_name": source.get("name") or source["id"],
                "original_url": url,
                "published_at": None,
                "discovered_at": discovered,
                "category": category,
                "score": score,
                "selected": selected,
                "track": ",".join(source.get("tracks") or []),
                "lang": "zh",
                "raw_json": {"list_url": list_url},
            }
        )
        if len(items) >= 30:
            break
    logger.info("cn list %s: %s items", source.get("id"), len(items))
    return items
