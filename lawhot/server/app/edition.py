"""每日固定刊：中文最多 8、英文最多 6；监管最多 1（可为 0）；宁缺毋滥。

刊发原则（科技优先、法律语境优先）：
- 硬门是「AI 实质信号」；法律相关性由客户端评分的 leg 轴决定，不作硬门
- 纯法律/司法动态（与 AI 无关）由 is_pure_legal 封顶，不进刊
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
from .classify import has_ai_signal, is_noise, is_pure_legal
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

# 跨期重复衰减：按出现次数分档，每档一档惩罚。上限 24 分——
# 相当于「一个质量档位」，确保高分老条目仍可留存但不再优先。
REPEAT_PENALTY_TIERS = ((2, 6.0), (3, 12.0), (5, 18.0), (8, 24.0))
REPEAT_PENALTY_MAX = 24.0
# 「昨天/今天刚刊过」的额外一档——用户感知最强的重复形态
REPEAT_RECENT_BONUS = 6.0

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
    """刊发硬门：含 AI 实质信号，且不是无实质 AI 的纯法律动态。

    与候选池预筛（`relevance_ok`）的区别很关键：候选池是宽召回，目的是给
    客户端评分留足素材；**每日读本是服务端直接产出的公开页面，没有客户端
    评分兜底**，所以这里必须自己挡掉纯法律动态与噪声。

    两道门的分工：
    - `relevance_ok`（候选池）：只要求含 AI 信号，故意宽松
    - `edition_eligible`（每日读本）：加挡 `is_pure_legal` 与噪声门，宁缺毋滥
    """
    title = row["title"] or ""
    summary = row["summary"] or ""
    if not title.strip():
        return False
    text = f"{title}\n{summary}"
    if not has_ai_signal(text):
        return False
    # 「人工智能促进法律监督提质增效」这类有实质内容的要留，
    # 「司法护航人工智能产业」这类只沾字面的不留。
    if is_pure_legal(title, summary):
        return False
    # 噪声门在这一层必须保留：候选池里噪声可以靠分数压掉（反正不进简报），
    # 但每日读本是直接对外的页面，不能靠分数让运营人员自己去滤。
    return not is_noise(title, summary)


def _repeat_penalty(appearances: int, last_edition_at: str | None, today: str) -> float:
    """跨期重复的衰减分。

    设计约束：**衰减只影响排序，不决定入选**。真正的高分条目即使连出几期，
    也应该在候选池里被看到，只是不该再排在最前面。所以惩罚有上限（不超过
    REPEAT_PENALTY_MAX），且 `pick_edition_rows` 里对已连续出现的条目仍保留
    兜底位置——池子不足时该重复的还得重复，总比开天窗强。

    惩罚按出现次数**分档**而非线性：2/3/5/8 次各一档，之后封顶。线性递增会
    在3 次就触顶，之后 4 次与 12 次完全没有区分度，衰减就白做了。
    """
    if appearances <= 1:
        return 0.0
    penalty = 0.0
    for threshold, value in REPEAT_PENALTY_TIERS:
        if appearances >= threshold:
            penalty = value
    # 昨天或今天刚刊过：额外一档。「昨天刚出过」是用户感知最强的重复形态
    if last_edition_at and last_edition_at >= _recent_date(today, 1):
        penalty = min(REPEAT_PENALTY_MAX, penalty + REPEAT_RECENT_BONUS)
    return penalty


def _recent_date(today: str, days_back: int) -> str:
    try:
        d = datetime.fromisoformat(today) - timedelta(days=days_back)
        return d.date().isoformat()
    except ValueError:
        return today


def edition_score(row: Any, *, today: str | None = None) -> float:
    """刊发排序分。

    客户端评分（references/selection-score.md）已是主判断，这里**不再对分数
    做正则加减**。旧实现在基础分上叠加 ±28/−22/+14/+12/+10 等十余处规则，
    会把评分的结论重新改写回去——那等于评分白做。

    现在只保留三类不扭曲判断的调整：
    1) 摘要质量：不合格的条目不该靠标题唬人入选（硬性惩罚，非加分）；
    2) 结构性偏好：法律科技垂直源略优先，用于打破同分平局；
    3) 跨期重复衰减：往期已入选过的条目降权，解决同批条目反复刷屏。
       次数由 `_appearances` 注入（从 editions 表实时统计，不存累加值）。
    """
    score = float(row["score"] or 0)
    sid = row["source_id"] or ""
    summary = row["summary"] or ""

    # 摘要不合格是硬缺陷：用惩罚而非加分，避免把同分的合格条目挤下去
    if not summary_ok(summary):
        score -= 12

    # 结构性破平局（幅度控制在一个质量档位内，不参与实质判断）：
    # 法律科技垂直源优先，官媒/综合法治源略降权。旧实现用-28 惩罚官媒，
    # 那是在没有客户端分的年代用规则代替判断；现在只保留同分排序所需的最小差值。
    if sid in LEGALTECH_SOURCE_IDS:
        score += 3
    if sid in GOV_SOURCE_IDS:
        score -= 3

    # 跨期重复衰减：`_appearances` 由 pick_edition_rows 从 editions 表统计后注入，
    # 避免在行对象上存会漂移的累加计数。
    appearances = 0
    if hasattr(row, "keys") and "_appearances" in row.keys():
        appearances = int(row["_appearances"] or 0)
    if appearances:
        last_at = row["last_edition_at"] if "last_edition_at" in row.keys() else None
        score -= _repeat_penalty(appearances, last_at, today or today_shanghai())

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
    candidates: list[Any],
    *,
    require_summary: bool = True,
    today: str | None = None,
    appearances: dict[str, int] | None = None,
) -> list[Any]:
    """选本期读本条目。

    跨期去重**只靠排序衰减，不设硬性席位上限**。早期版本给重复条目留了 2 席
    兜底，实际不生效——衰减后它们排在新鲜内容之后，兜底席永远轮不到；而一旦
    改成硬性保留，又会出现「宁可空刊也塞陈旧内容」的坏结果。

    现在的行为是自然收敛：新内容足够时重复条目被完全挤出，池子不足时它们
    自然补位。既不空刊，也不硬塞。
    """
    today = today or today_shanghai()
    # 往期出现次数从 editions 表统计，不写累加计数到库里，避免重编漂移
    if appearances is None:
        appearances = db.count_edition_appearances(
            [r["id"] for r in candidates], before=today
        )
    # sqlite3.Row 不可写，统一转 dict 后注入 `_appearances`
    rows = [
        {**dict(r), "_appearances": appearances.get(r["id"], 0)} for r in candidates
    ]

    ranked = sorted(
        rows, key=lambda r: edition_score(r, today=today), reverse=True
    )
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
    picked.sort(
        key=lambda r: (
            order.get(r["category"] or "", 9),
            -edition_score(r, today=today),
        )
    )
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
            "监管最多 1 条，官媒综合源整刊限流）。以技术如何改变法律服务为主线，"
            "偏重 LegalTech、诉讼与实务，纯法律动态不进刊。"
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
    # 候选池只要求「已入库且含 AI 信号」，不再用分数卡池：
    # 分数是规则版粗排，客户端会用提示词重新评分，70 分门槛会把大池子砍掉。
    pool = [r for r in candidates if edition_eligible(r)]

    # 跨期去重：按历史刊发次数衰减排序。
    # 历史次数要排除本期自身的 edition（重编同一天时该字段已含本期），
    # 所以这里用 list_items 的原始行——mark_edition_published 在选刊后才写。
    picked = pick_edition_rows(pool, require_summary=True, today=date)
    # 冷启动：摘要尚未润色时，允许无摘要先出刊，避免首页空白
    if not picked:
        picked = pick_edition_rows(pool, require_summary=False, today=date)
        logger.warning("edition %s: fallback without summary gate, n=%s", date, len(picked))

    payload = build_edition_payload(date, picked)
    db.save_edition(date, payload)
    # 记录本期刊发，供下一期的重复衰减使用。放在 save_edition 之后，
    # 这样即使保存失败也不会虚增计数。
    db.mark_edition_published(date, [r["id"] for r in picked])
    db.sync_selected_from_editions(days=7)
    db.save_daily(date, payload)
    logger.info(
        "edition %s: total=%s zh=%s en=%s repeats=%s",
        date,
        payload["counts"]["total"],
        payload["counts"]["zh"],
        payload["counts"]["en"],
        sum(1 for r in picked if int(r["edition_count"] or 0) >= 2),
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
