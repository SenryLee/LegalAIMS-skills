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

INCLUDE_PATTERNS = [
    r"AI Act|artificial intelligence act|生成式人工智能|深度合成|深度伪造",
    r"legaltech|legal tech|法律科技|智慧法院|法律大模型|Legal AI|legal AI",
    r"(AI|ChatGPT|Claude|OpenAI|Anthropic).{0,40}(copyright|lawsuit|诉讼|著作权|知识产权|infringement)",
    r"(copyright|lawsuit|诉讼|著作权|知识产权|infringement).{0,40}(AI|ChatGPT|Claude|OpenAI|Anthropic)",
    r"(AI|ChatGPT|Claude).{0,40}(liability|malpractice|hallucination|判决|证据|court)",
    r"privacy|GDPR|个人信息|数据出境|网信办|FTC|SEC",
    r"eDiscovery|contract review|合同审查|尽调|legal agent",
    r"responsible AI|AI governance|AI safety|alignment|AI 监管|人工智能.*监管|监管.*人工智能",
]

EXCLUDE_PATTERNS = [
    r"招聘|求职|优惠|免费领取|success story|customer story|客户案例",
]

TRUST_SCORE = {
    "official": 88,
    "specialty_media": 78,
    "vendor_primary": 74,
    "think_tank": 72,
    "academic": 70,
    "general_media": 58,
    "mixed": 55,
}


def _hit(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def classify_category(title: str, summary: str, source: dict[str, Any]) -> str:
    text = f"{title}\n{summary}"
    tracks = source.get("tracks") or []

    rules: list[tuple[str, str]] = [
        (r"AI Act|网信|FTC|GDPR|Federal Register|监管|立法|条例|办法|合规|privacy", "regulation"),
        (r"诉|lawsuit|诉讼|court|判决|infringement|起诉|原告|被告", "litigation"),
        (r"legaltech|LegalTech|法律科技|Harvey|Legora|Clio|Everlaw|合同审查|eDiscovery", "legaltech"),
        (r"律所|practice|落地|workflow|associate|billing|KM", "practice"),
        (r"启示|insight|评论|opinion|为什么|如何改变", "insight"),
    ]
    for pat, cat in rules:
        if re.search(pat, text, re.I):
            return cat

    if "vendor_frontier" in tracks or (source.get("trust") == "vendor_primary"):
        if _hit([r"safety|alignment|policy|security|governance|安全|对齐|治理|监管"], text):
            return "vendor"
        # vendor product noise still tagged vendor but may be unselected later
        return "vendor"
    if "ai_x_law" in tracks:
        return "legaltech"
    if "law_x_ai" in tracks:
        return "regulation"
    return "insight"


def relevance_ok(title: str, summary: str, source: dict[str, Any]) -> bool:
    """Legal specialty feeds pass; broad official / general media need keyword hits."""
    text = f"{title}\n{summary}"
    if _hit(EXCLUDE_PATTERNS, text):
        return False

    trust = source.get("trust") or ""
    source_id = source.get("id") or ""
    tracks = source.get("tracks") or []

    # Noisy / broad feeds: require clear AI × law topicality.
    if source_id in {"en-whitehouse-news", "en-ftc-press", "en-above-the-law", "en-techcrunch-ai"}:
        return _hit(
            [
                r"artificial intelligence",
                r"\bAI\b",
                r"ChatGPT|Claude|OpenAI|Anthropic|Gemini|machine learning",
                r"生成式人工智能|大模型|智能体",
            ],
            text,
        ) and (
            _hit(INCLUDE_PATTERNS, text)
            or _hit(
                [
                    r"law|legal|court|regul|privacy|copyright|compliance|诉讼|监管|合规|版权|律师|律所",
                    r"FTC|SEC|DOJ|GDPR|AI Act|executive order|governance|safety|policy",
                ],
                text,
            )
        )

    if trust == "specialty_media":
        return True

    if trust == "vendor_primary":
        return _hit(
            [
                r"safety|alignment|policy|security|governance|legal|law|court|regul|"
                r"安全|对齐|治理|监管|法律|合规|版权|copyright|liability"
            ],
            text,
        ) or ("vendor_frontier" in tracks)

    if trust in {"academic", "think_tank"}:
        return _hit(INCLUDE_PATTERNS, text) or _hit(
            [r"\bAI\b|artificial intelligence|法律|监管|治理"], text
        )

    if trust == "official":
        if source_id == "en-federal-register-ai":
            # Feed is keyword-scoped but still noisy; require AI in title/summary strongly.
            return _hit(
                [r"artificial intelligence|\bAI\b|machine learning|generative AI"],
                text,
            )
        return _hit(INCLUDE_PATTERNS, text) or _hit(
            [r"\bAI\b|artificial intelligence"], text
        )

    return _hit(INCLUDE_PATTERNS, text)


def score_item(title: str, summary: str, source: dict[str, Any], category: str) -> float:
    base = float(TRUST_SCORE.get(source.get("trust") or "", 60))
    text = f"{title}\n{summary}"
    if _hit([r"AI Act|网信办|Federal Register|Supreme Court|最高法|lawsuit"], text):
        base += 8
    if category in {"regulation", "litigation"}:
        base += 3
    if source.get("tier") == "P0":
        base += 2
    return max(0.0, min(100.0, base))


def should_select(score: float, category: str, source: dict[str, Any]) -> bool:
    # Vendor frontier: only select policy/safety/governance-ish pieces by default.
    if "vendor_frontier" in (source.get("tracks") or []) and category == "vendor":
        return score >= 80
    if source.get("id") == "en-above-the-law":
        return score >= 82
    if source.get("tier") == "P0" and score >= 68:
        return True
    if category in {"regulation", "litigation"} and score >= 70:
        return True
    return score >= 76
