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

# 更偏向法律科技 / 融资 / 律所落地 / 诉讼；监管保留但收紧
INCLUDE_PATTERNS = [
    r"legaltech|legal tech|法律科技|智慧法院|法律大模型|Legal AI|legal AI|lawtech",
    r"Harvey|Legora|Clio|Everlaw|CoCounsel|Lexis\+?|Westlaw|合同审查|eDiscovery|尽调|legal agent",
    r"律所|law firm|associate|billing|KM|实务|落地|工作流",
    r"融资|funding|Series [ABC]|seed round|估值|raised|venture|投资.*法律|法律.*投资",
    r"(AI|ChatGPT|Claude|OpenAI|Anthropic).{0,40}(copyright|lawsuit|诉讼|著作权|知识产权|infringement)",
    r"(copyright|lawsuit|诉讼|著作权|知识产权|infringement).{0,40}(AI|ChatGPT|Claude|OpenAI|Anthropic)",
    r"(AI|ChatGPT|Claude).{0,40}(liability|malpractice|hallucination|判决|证据|court|律师)",
    r"生成式人工智能|深度合成|深度伪造|人工智能.*司法|司法.*人工智能",
]

REGULATION_PATTERNS = [
    r"AI Act|artificial intelligence act|网信办|Federal Register|GDPR|FTC|SEC|条例|办法|立法|监管令",
    r"个人信息保护法|数据出境|深度合成.*规定|人工智能.*办法",
]

EXCLUDE_PATTERNS = [
    r"招聘|求职|优惠|免费领取|success story|customer story|客户案例|hiring|we're hiring",
]

TRUST_SCORE = {
    "official": 82,
    "specialty_media": 80,
    "vendor_primary": 72,
    "think_tank": 74,
    "academic": 73,
    "general_media": 60,
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
            r"legaltech|LegalTech|法律科技|Harvey|Legora|Clio|Everlaw|CoCounsel|合同审查|eDiscovery|lawtech|法律大模型|智慧法院",
            "legaltech",
        ),
        (r"诉|lawsuit|诉讼|判决|infringement|起诉|原告|被告|malpractice", "litigation"),
        (r"律所|law firm|associate|billing|KM|实务落地|workflow|工作流", "practice"),
        (r"AI Act|网信|FTC|GDPR|Federal Register|监管|立法|条例|办法|合规治理", "regulation"),
        (r"启示|insight|评论|opinion|如何改变|启迪", "insight"),
    ]
    for pat, cat in rules:
        if re.search(pat, text, re.I):
            return cat

    if "vendor_frontier" in tracks or source.get("trust") == "vendor_primary":
        # 厂商稿：有法律/安全治理才进 vendor，否则多半不该精选
        if _hit(
            [r"legal|law|court|合规|法律|律师|诉讼|版权|copyright|safety|governance|监管"],
            text,
        ):
            return "vendor"
        return "vendor"
    if "ai_x_law" in tracks:
        return "legaltech"
    if "law_x_ai" in tracks:
        return "regulation"
    return "insight"


def relevance_ok(title: str, summary: str, source: dict[str, Any]) -> bool:
    text = f"{title}\n{summary}"
    if _hit(EXCLUDE_PATTERNS, text):
        return False

    trust = source.get("trust") or ""
    source_id = source.get("id") or ""
    tracks = source.get("tracks") or []
    lang = source.get("lang") or ""

    # 中文官方/学术源：只要沾 AI×法律/司法/科技 即可
    if lang == "zh" or "cn" in (source.get("region") or []):
        return _hit(
            [
                r"人工智能|大模型|ChatGPT|智能|算法|法律科技|智慧法院|司法|律师|合规|著作权|生成式|深度合成|融资|法律服务",
            ],
            text,
        ) or trust in {"specialty_media", "academic"}

    if source_id in {"en-whitehouse-news", "en-ftc-press", "en-above-the-law", "en-techcrunch-ai"}:
        return _hit([r"artificial intelligence|\bAI\b|ChatGPT|Claude|OpenAI|Anthropic"], text) and (
            _hit(INCLUDE_PATTERNS, text) or _hit(REGULATION_PATTERNS, text)
        )

    if source_id == "en-federal-register-ai":
        # 监管类大幅收紧：标题需明显是 AI 规则/治理，排除琐碎 notice
        return _hit(
            [
                r"artificial intelligence.*(rule|act|governance|safety|executive)",
                r"(rule|act|governance|safety|executive).*artificial intelligence",
                r"generative AI|AI system|machine learning.*(regulation|compliance)",
            ],
            text,
        )

    if trust == "specialty_media":
        return True

    if trust == "vendor_primary":
        return _hit(
            [
                r"legal|law|court|律师|法律|合规|诉讼|版权|copyright|liability|"
                r"safety|alignment|governance|policy|security"
            ],
            text,
        )

    if trust in {"academic", "think_tank"}:
        return _hit(INCLUDE_PATTERNS, text) or _hit(REGULATION_PATTERNS, text)

    if trust == "official":
        return _hit(INCLUDE_PATTERNS, text) or _hit(REGULATION_PATTERNS, text)

    return _hit(INCLUDE_PATTERNS, text) or _hit(REGULATION_PATTERNS, text)


def score_item(title: str, summary: str, source: dict[str, Any], category: str) -> float:
    base = float(TRUST_SCORE.get(source.get("trust") or "", 60))
    text = f"{title}\n{summary}"

    # 提权：法律科技 / 融资 / 诉讼
    if category in {"legaltech", "practice"}:
        base += 10
    if category == "litigation":
        base += 8
    if category == "insight":
        base += 4
    if category == "regulation":
        base -= 4  # 监管整体降权，靠下面重点再加回
    if category == "vendor":
        base -= 2

    if _hit(
        [r"legaltech|法律科技|Harvey|Legora|Clio|合同审查|eDiscovery|法律大模型|智慧法院"],
        text,
    ):
        base += 8
    if _hit([r"融资|funding|Series [ABC]|raised|估值"], text):
        base += 8
    if _hit([r"lawsuit|诉讼|malpractice|判决|hallucination"], text):
        base += 6

    # 监管只给“重点”加分
    if _hit(
        [r"AI Act|网信办.*办法|生成式人工智能.*办法|深度合成.*规定|Executive Order.*AI"],
        text,
    ):
        base += 10
    elif category == "regulation":
        base -= 6

    if source.get("lang") == "zh":
        base += 3  # 略提中文源曝光
    if source.get("tier") == "P0":
        base += 2
    return max(0.0, min(100.0, base))


def should_select(score: float, category: str, source: dict[str, Any]) -> bool:
    if source.get("id") == "en-federal-register-ai":
        return score >= 88
    if category == "regulation":
        return score >= 84  # 监管少而精
    if category == "vendor":
        return score >= 82
    if category in {"legaltech", "practice"}:
        return score >= 66
    if category == "litigation":
        return score >= 70
    if source.get("tier") == "P0" and score >= 70:
        return True
    return score >= 76
