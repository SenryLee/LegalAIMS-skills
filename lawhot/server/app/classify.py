from __future__ import annotations

import re
from typing import Any

CATEGORIES = (
    "regulation",
    "litigation",
    "legaltech",
    "practice",
    "insight",
    "vendor",
)

# 法律科技频道：产品、落地、融资、诉讼优先
INCLUDE_PATTERNS = [
    r"legaltech|legal tech|法律科技|智慧.*律师|法律大模型|Legal AI|legal AI|lawtech",
    r"Harvey|Legora|Clio|Everlaw|CoCounsel|Lexis\+?|Westlaw|合同审查|eDiscovery|尽调|legal agent",
    r"律所|law firm|associate|billing|KM|实务|落地|工作流|法务",
    r"融资|funding|Series [ABC]|seed round|估值|raised|venture|投资.*法律|法律.*投资|LegalTech.*融资",
    r"(AI|ChatGPT|Claude|OpenAI|Anthropic).{0,40}(copyright|lawsuit|诉讼|著作权|知识产权|infringement)",
    r"(copyright|lawsuit|诉讼|著作权|知识产权|infringement).{0,40}(AI|ChatGPT|Claude|OpenAI|Anthropic)",
    r"(AI|ChatGPT|Claude).{0,40}(liability|malpractice|hallucination|判决|证据|court|律师)",
    r"生成式人工智能|深度合成|法律 AI|AI 法律|智能起草|智能合同",
    r"system card|model card|preparedness framework|model spec|alignment|economic index",
    r"AI RMF|AI Office|AISI|Copyright Office|AI Safety Institute",
]

REGULATION_PATTERNS = [
    r"AI Act|artificial intelligence act|网信办|Federal Register|GDPR|FTC|SEC|条例|办法|立法|监管令",
    r"个人信息保护法|数据出境|深度合成.*规定|人工智能.*办法",
    r"NIST|AI Office|Copyright Office|AISI|preparedness|GPAI|high-risk",
]

# 综合科技媒体噪声：机器人/具身/芯片融资等
EXCLUDE_PATTERNS = [
    r"招聘|求职|优惠|免费领取|success story|customer story|客户案例|hiring|we're hiring",
    r"具身智能|人形机器人|端侧具身|自动驾驶出租车|无人机融资|芯片流片",
]

TRUST_SCORE = {
    "official": 70,  # 政务降权
    "specialty_media": 84,
    "vendor_primary": 78,
    "think_tank": 74,
    "academic": 73,
    "general_media": 58,
    "mixed": 55,
}


def _hit(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def classify_category(title: str, summary: str, source: dict[str, Any]) -> str:
    text = f"{title}\n{summary}"
    tracks = source.get("tracks") or []

    rules: list[tuple[str, str]] = [
        (r"融资|funding|Series [ABC]|seed round|估值|raised \$|venture", "practice"),
        (
            r"legaltech|LegalTech|法律科技|Harvey|Legora|Clio|Everlaw|CoCounsel|合同审查|eDiscovery|lawtech|法律大模型|法律 AI|Legal AI",
            "legaltech",
        ),
        (r"诉|lawsuit|诉讼|判决|infringement|起诉|原告|被告|malpractice", "litigation"),
        (r"律所|law firm|associate|billing|KM|实务落地|workflow|工作流|法务部", "practice"),
        (r"AI Act|网信|FTC|GDPR|Federal Register|监管|立法|条例|办法|合规治理", "regulation"),
        (r"启示|insight|评论|opinion|如何改变|启迪", "insight"),
    ]
    for pat, cat in rules:
        if re.search(pat, text, re.I):
            return cat

    if "vendor_frontier" in tracks or source.get("trust") == "vendor_primary":
        return "vendor"
    if "ai_x_law" in tracks:
        return "legaltech"
    if "law_x_ai" in tracks:
        # 官媒默认不再一律标监管，避免首页政务化
        if source.get("trust") == "official":
            return "regulation"
        return "insight"
    return "insight"


def relevance_ok(title: str, summary: str, source: dict[str, Any]) -> bool:
    text = f"{title}\n{summary}"
    if _hit(EXCLUDE_PATTERNS, text):
        return False

    trust = source.get("trust") or ""
    source_id = source.get("id") or ""
    lang = source.get("lang") or ""

    # 综合科技站：必须同时沾法律
    if source_id in {"zh-36kr-ai", "zh-thepaper-tech", "en-techcrunch-ai"}:
        return _hit(
            [r"法律|律师|律所|法务|合规|诉讼|版权|著作权|Legal|law firm|legaltech|法律科技"],
            text,
        ) and _hit([r"AI|人工智能|大模型|ChatGPT|智能"], text)

    # 中文官方：收紧——必须有 AI/智能 + 法律行业信号，排除纯会议
    if trust == "official" or source_id.startswith("zh-court") or source_id.startswith("zh-cac"):
        if re.search(r"召开|座谈会|调研组|学习贯彻|表彰|参观考察", title):
            return False
        return _hit(
            [r"人工智能|大模型|ChatGPT|算法|法律科技|法律大模型|智能起草|智能合同|生成式"],
            text,
        ) and _hit(
            [r"律师|律所|法务|诉讼|审判|检察|合同|合规|知识产权|著作权|法律服务"],
            text,
        )

    if lang == "zh" or "cn" in (source.get("region") or []):
        # 法律科技垂直源放宽
        if trust == "specialty_media" or "ai_x_law" in (source.get("tracks") or []):
            return _hit(
                [
                    r"人工智能|大模型|ChatGPT|智能|算法|法律科技|法律 AI|Legal|律师|律所|"
                    r"合同|合规|诉讼|融资|法务|Harvey|Legora",
                ],
                text,
            )
        return _hit(INCLUDE_PATTERNS, text)

    if source_id in {"en-whitehouse-news", "en-ftc-press", "en-above-the-law", "en-techcrunch-ai"}:
        return _hit([r"artificial intelligence|\bAI\b|ChatGPT|Claude|OpenAI|Anthropic"], text) and (
            _hit(INCLUDE_PATTERNS, text) or _hit(REGULATION_PATTERNS, text)
        )

    if source_id == "en-federal-register-ai":
        return _hit(
            [
                r"artificial intelligence.*(rule|act|governance|safety|executive)",
                r"(rule|act|governance|safety|executive).*artificial intelligence",
            ],
            text,
        )

    if trust == "specialty_media":
        return True

    if trust == "vendor_primary":
        return _hit(
            [
                r"legal|law|court|律师|法律|合规|诉讼|版权|copyright|liability|"
                r"safety|alignment|governance|policy|security|contract|eDiscovery|"
                r"system card|model card|preparedness|model spec|economic index|responsible"
            ],
            text,
        )

    if trust in {"academic", "think_tank", "official"}:
        return _hit(INCLUDE_PATTERNS, text) or _hit(REGULATION_PATTERNS, text)

    return _hit(INCLUDE_PATTERNS, text)


def score_item(title: str, summary: str, source: dict[str, Any], category: str) -> float:
    base = float(TRUST_SCORE.get(source.get("trust") or "", 60))
    text = f"{title}\n{summary}"

    if category in {"legaltech", "practice"}:
        base += 12
    if category == "litigation":
        base += 8
    if category == "insight":
        base += 3
    if category == "regulation":
        base -= 8
    if category == "vendor":
        base += 2

    if _hit(
        [r"legaltech|法律科技|Harvey|Legora|Clio|合同审查|eDiscovery|法律大模型|法律 AI"],
        text,
    ):
        base += 10
    if _hit([r"融资|funding|Series [ABC]|raised|估值"], text) and _hit(
        [r"法律|Legal|律所|legaltech|法律科技"], text
    ):
        base += 10
    if _hit([r"lawsuit|诉讼|malpractice|判决|hallucination"], text):
        base += 6

    if _hit(
        [r"AI Act|网信办.*办法|生成式人工智能.*办法|深度合成.*规定|Executive Order.*AI"],
        text,
    ):
        base += 8
    elif category == "regulation":
        base -= 8

    if source.get("trust") == "official":
        base -= 6
    if source.get("tier") == "P0" and source.get("trust") == "specialty_media":
        base += 4
    return max(0.0, min(100.0, base))


def should_select(score: float, category: str, source: dict[str, Any]) -> bool:
    """初筛进入候选池（刊发另有每日配额）。"""
    if source.get("id") == "en-federal-register-ai":
        return score >= 90
    if category == "regulation":
        return score >= 86
    if source.get("trust") == "official":
        return score >= 82
    if category == "vendor":
        return score >= 78
    if category in {"legaltech", "practice"}:
        return score >= 68
    if category == "litigation":
        return score >= 72
    if source.get("tier") == "P0" and score >= 74:
        return True
    return score >= 78
