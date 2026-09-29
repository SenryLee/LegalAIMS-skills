"""每日固定刊：中文最多 8、英文最多 6；监管最多 1（可为 0）；宁缺毋滥。

刊发原则（对齐 AIHOT「高门槛精选」）：
- 必须通过法律×AI 交叉门；官媒泛 AI / 安全攻防噪声不得进刊
- 英文 LegalTech 垂直源优先；中文官媒严格限流
- 单源上限更低，避免正义网/法治日报/安全内参占满
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from . import db
from .classify import intersection_ok
from .config import PUBLIC_BASE_URL
from .translate import looks_chinese

logger = logging.getLogger("lawhot.edition")
SHANGHAI = ZoneInfo("Asia/Shanghai")

CN_QUOTA = 8
EN_QUOTA = 6
REGULATION_MAX = 1
PER_SOURCE_MAX = 2  # 默认单源上限
PER_SOURCE_MAX_VERTICAL = 3  # 法律科技垂直源可多占
STRICT_CN_MAX = 2  # 官媒/综合法治媒体整刊上限

# 政务/官媒/综合法治：可进候选，但刊发分大幅降低且整刊限流
GOV_SOURCE_IDS = {
    "zh-cac",
    "zh-cac-news",
    "zh-court",
    "zh-court-gov",
    "zh-miit",
    "zh-npc",
    "zh-moj",
    "zh-gov-cn",
    "zh-legaldaily",
    "zh-legaldaily-ai",
    "zh-chinacourt",
    "zh-chinacourt-yaml",
    "zh-rmfyb",
    "zh-spp",
    "zh-jcrb",
    "zh-secrss",
    "zh-secrss-yaml",
    "zh-fayan-bigdata",
    "zh-fayan-bigdata-builtin",
}

# 法律科技主源：刊发加分
LEGALTECH_SOURCE_IDS = {
    "en-artificial-lawyer",
    "en-legal-it-insider",
    "en-lawsites",
    "en-everlaw-blog",
    "en-clio-blog",
    "en-tr-legal-posts",
    "en-harvey-blog",
    "en-legora-blog",
    "en-lexis-insights",
    "en-above-the-law",
    "en-legaltech-hub",
    "en-iapp",
    "zh-lawyeah",
    "zh-autopilot-law",
    "zh-legaltech-media",
    "zh-fadada-news",
    "zh-esign-news",
    "zh-ciplawyer-ai",
}

_PLACEHOLDER_SUM = re.compile(
    r"^(来源：|列表页摘录|暂无摘要|详情见原文|摘要生成中)", re.I
)


def today_shanghai() -> str:
    return datetime.now(SHANGHAI).date().isoformat()


def is_zh_item(row: Any) -> bool:
    lang = (row["lang"] if hasattr(row, "keys") else row.get("lang")) or ""
    title = row["title"] if hasattr(row, "keys") else row.get("title") or ""
    if lang == "zh":
        return True
    if lang == "en":
        return False
    return looks_chinese(title or "")


def summary_ok(summary: str | None) -> bool:
    s = (summary or "").strip()
    if len(s) < 28:
        return False
    if _PLACEHOLDER_SUM.search(s):
        return False
    return True


def edition_eligible(row: Any) -> bool:
    """刊发硬门：法律×AI 交叉；摘要占位不挡冷启动，但占位会在 require_summary 时过滤。"""
    title = row["title"] or ""
    summary = row["summary"] or ""
    if not title.strip():
        return False
    sid = row["source_id"] or ""
    # 英文法律垂直源：交叉可稍松（源本身法律向）
    if sid in LEGALTECH_SOURCE_IDS and not is_zh_item(row):
        return True
    if not intersection_ok(title, summary):
        return False
    # 官媒/综合法治：还要硬信号（产品/诉讼/正式规则/法律科技），挡「司法护航产业」空话
    if sid in GOV_SOURCE_IDS:
        text = f"{title}\n{summary}"
        hard = re.search(
            r"法律科技|法律大模型|合同审查|智能起草|eDiscovery|Legal AI|法律 AI|"
            r"律师.*人工智能|人工智能.*律师|法律服务.*产品|生成式人工智能.*(办法|规定)|"
            r"深度合成.*规定|AI Act|起诉|判决|System Card|数字检察.*大模型|"
            r"智能辅助办案|法律监督.*人工智能|人工智能.*法律监督",
            text,
            re.I,
        )
        if not hard:
            return False
        if re.search(r"展演活动|学术研讨会|宣传周|调研行|座谈会|司法护航.*产业|行稳致远", title):
            return False
    return True


def edition_score(row: Any) -> float:
    score = float(row["score"] or 0)
    sid = row["source_id"] or ""
    cat = row["category"] or ""
    title = row["title"] or ""
    summary = row["summary"] or ""
    text = f"{title}\n{summary}"

    if sid in LEGALTECH_SOURCE_IDS:
        score += 14
    if sid in GOV_SOURCE_IDS:
        score -= 28
    if cat in {"legaltech", "practice"}:
        score += 10
    if cat == "litigation":
        score += 8
    if cat == "vendor":
        score += 4
    if cat == "regulation":
        score -= 12
    if summary_ok(summary):
        score += 6
    else:
        score -= 10

    # 法律科技硬信号
    if re.search(
        r"legaltech|法律科技|法律大模型|合同审查|eDiscovery|CoCounsel|Harvey|Legora|"
        r"律所.*AI|AI.*律所|法律 AI|Legal AI|智慧.*律师|智能起草|尽调|"
        r"法律服务.*产品|System Card|Model Spec",
        text,
        re.I,
    ):
        score += 12

    # 纯政务/会议/宣传噪声
    if re.search(
        r"召开|座谈会|调研组|学习贯彻|表彰大会|参观考察|宣传周|调研行|"
        r"展演活动|学术研讨会|世赛|算力|外交部.*人工智能",
        title,
    ):
        score -= 22

    # 英文优先一点，纠偏国内官媒占满
    if not is_zh_item(row) and sid in LEGALTECH_SOURCE_IDS:
        score += 8

    return score


def _norm_title(title: str) -> str:
    t = re.sub(r"\s+", "", title or "")
    return t[:28]


def _source_cap(sid: str) -> int:
    if sid in LEGALTECH_SOURCE_IDS:
        return PER_SOURCE_MAX_VERTICAL
    if sid in GOV_SOURCE_IDS:
        return 1
    return PER_SOURCE_MAX


def pick_edition_rows(
    candidates: list[Any], *, require_summary: bool = True
) -> list[Any]:
    ranked = sorted(candidates, key=edition_score, reverse=True)
    picked: list[Any] = []
    cn_n = en_n = reg_n = strict_cn_n = 0
    per_src: dict[str, int] = {}
    seen_titles: set[str] = set()

    for row in ranked:
        if not edition_eligible(row):
            continue
        if require_summary and not summary_ok(row["summary"]):
            continue
        if not (row["title"] or "").strip():
            continue
        sid = row["source_id"] or ""
        cat = row["category"] or ""
        nt = _norm_title(row["title"] or "")
        if nt and nt in seen_titles:
            continue
        if per_src.get(sid, 0) >= _source_cap(sid):
            continue
        if sid in GOV_SOURCE_IDS and strict_cn_n >= STRICT_CN_MAX:
            continue
        if cat == "regulation":
            if reg_n >= REGULATION_MAX:
                continue

        zh = is_zh_item(row)
        if zh:
            if cn_n >= CN_QUOTA:
                continue
        else:
            if en_n >= EN_QUOTA:
                continue

        picked.append(row)
        per_src[sid] = per_src.get(sid, 0) + 1
        if nt:
            seen_titles.add(nt)
        if cat == "regulation":
            reg_n += 1
        if sid in GOV_SOURCE_IDS:
            strict_cn_n += 1
        if zh:
            cn_n += 1
        else:
            en_n += 1

        if cn_n >= CN_QUOTA and en_n >= EN_QUOTA:
            break

    # 刊内排序：法律科技/实务优先，监管最后
    order = {
        "legaltech": 0,
        "practice": 1,
        "litigation": 2,
        "insight": 3,
        "vendor": 4,
        "regulation": 5,
    }
    picked.sort(key=lambda r: (order.get(r["category"] or "", 9), -edition_score(r)))
    return picked


def build_edition_payload(date: str, rows: list[Any]) -> dict[str, Any]:
    cn = sum(1 for r in rows if is_zh_item(r))
    en = len(rows) - cn
    items = []
    for r in rows:
        items.append(
            {
                "id": r["id"],
                "title": r["title"],
                "summary": r["summary"],
                "category": r["category"],
                "lang": "zh" if is_zh_item(r) else "en",
                "source": {"name": r["source_name"]},
                "links": {
                    "lawhot": f"{PUBLIC_BASE_URL}/items/{r['id']}",
                    "original": r["original_url"],
                },
            }
        )
    return {
        "date": date,
        "title": f"Legal Bulletins 每日读本 {date}",
        "lead": (
            f"本日刊发 {len(rows)} 条（中文 {cn} / 英文 {en}，上限 {CN_QUOTA}+{EN_QUOTA}；"
            "监管最多 1 条，官媒综合源整刊限流）。只收法律×AI 交叉硬信号，偏重 LegalTech、诉讼与实务。"
        ),
        "quota": {"zh": CN_QUOTA, "en": EN_QUOTA, "regulation_max": REGULATION_MAX},
        "counts": {"zh": cn, "en": en, "total": len(rows)},
        "item_ids": [r["id"] for r in rows],
        "items": items,
        "links": {"lawhot": f"{PUBLIC_BASE_URL}/?date={date}"},
    }


def rebuild_edition_for_date(date: str | None = None) -> dict[str, Any]:
    """从近 7 日候选中重编指定自然日（上海）刊发名单。"""
    date = date or today_shanghai()
    start = (datetime.now(timezone.utc) - timedelta(days=7)).replace(microsecond=0)
    start_iso = start.isoformat().replace("+00:00", "Z")

    candidates = db.list_items(
        mode="all",
        window_start_iso=start_iso,
        by="timeline",
        category=None,
        q=None,
        limit=300,
        offset=0,
    )
    pool = [
        r
        for r in candidates
        if (r["selected"] or (r["score"] or 0) >= 70) and edition_eligible(r)
    ]
    if not pool:
        # 冷启动：仍要求交叉门，避免官媒泛 AI 回流
        pool = [r for r in candidates if edition_eligible(r)]

    picked = pick_edition_rows(pool, require_summary=True)
    # 冷启动：摘要尚未润色时，允许无摘要先出刊，避免首页空白
    if not picked:
        picked = pick_edition_rows(pool, require_summary=False)
        logger.warning("edition %s: fallback without summary gate, n=%s", date, len(picked))

    payload = build_edition_payload(date, picked)
    db.save_edition(date, payload)
    db.sync_selected_from_editions(days=7)
    db.save_daily(date, payload)
    logger.info(
        "edition %s: total=%s zh=%s en=%s",
        date,
        payload["counts"]["total"],
        payload["counts"]["zh"],
        payload["counts"]["en"],
    )
    return payload


def ensure_today_edition() -> dict[str, Any] | None:
    """若今日刊不存在或为空，立即从库内重建。"""
    date = today_shanghai()
    payload = db.get_edition(date)
    if payload and (payload.get("item_ids") or payload.get("counts", {}).get("total")):
        return payload
    try:
        return rebuild_edition_for_date(date)
    except Exception:
        logger.exception("ensure_today_edition failed")
        return db.get_edition(date)
