"""法律 AI 相关度与精选评分。

设计对齐 AIHOT 的「预筛宽召回 + 高门槛精选」思路，但面向 Legal Bulletins：
- 预筛必须同时看见「AI 信号」与「法律/法律科技信号」（交叉才算相关）
- 精选分数看注意力价值，不把官媒身份或「提到人工智能」自动打高分
- 噪声（算力/世赛/网络安全宣传周/外交部空泛表态/厂商营销）压住
"""

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

# ---------------------------------------------------------------------------
# 信号词典
# ---------------------------------------------------------------------------

AI_SIGNAL = [
    r"\bAI\b|人工智能|生成式|大模型|ChatGPT|Claude|Gemini|GPT-?\d|LLM|"
    r"机器学习|深度学习|智能体|Agent|算法推荐|深度合成|多模态|"
    r"OpenAI|Anthropic|DeepSeek|法律大模型|Legal AI|legal AI",
]

LEGAL_SIGNAL = [
    r"律师|律所|法务|合规|诉讼|审判|检察|法院|司法|判决|起诉|"
    r"著作权|版权|知识产权|合同|立法|监管|条例|办法|罚则|"
    r"law firm|lawyer|counsel|court|lawsuit|copyright|liability|"
    r"malpractice|regulation|compliance|GDPR|FTC|SEC|AI Act|"
    r"法律服务|法律监督|数字检察|智慧法院|司法鉴定|"
    r"个人信息保护|数据出境|深度合成.*规定|生成式人工智能.*办法",
]

LEGALTECH_SIGNAL = [
    r"legaltech|legal tech|lawtech|法律科技|Legal AI|legal AI|法律大模型|"
    r"合同审查|智能起草|eDiscovery|尽调|CoCounsel|Harvey|Legora|Clio|"
    r"Everlaw|Lexis\+?|Westlaw|法律 Agent|律所.*AI|AI.*律所|"
    r"律师.*人工智能|人工智能.*律师|法律 AI|智能合同|辅助办案|"
    r"法律服务.*产品|法律科技.*融资|LegalTech",
]

REGULATION_SIGNAL = [
    r"AI Act|artificial intelligence act|网信办|Federal Register|GDPR|FTC|SEC|"
    r"条例|办法|立法|监管令|个人信息保护法|数据出境|"
    r"深度合成.*规定|人工智能.*办法|NIST|AI Office|Copyright Office|"
    r"AISI|preparedness|GPAI|high-risk|Executive Order.*AI|"
    r"生成式人工智能.*办法|算法推荐.*规定",
]

LITIGATION_SIGNAL = [
    r"诉|lawsuit|诉讼|判决|infringement|起诉|原告|被告|malpractice|"
    r"hallucination.*律师|证据.*AI|AI.*证据|著作权.*AI|AI.*版权",
]

# 明确噪声：即使沾了「智能/AI」也不该进法律 AI 精选
NOISE_PATTERNS = [
    r"招聘|求职|优惠|免费领取|success story|customer story|客户案例|"
    r"hiring|we're hiring|限时|课程报名|扫码报名",
    r"具身智能|人形机器人|端侧具身|自动驾驶出租车|无人机融资|芯片流片|"
    r"算力互济|词元工厂|绿电直连|智能算力规模|5G 工厂|5G工厂",
    r"世界技能大赛|世赛|网络安全宣传周|智能制造为主攻|"
    r"活力中国调研行|东西部算力",
    r"召开|座谈会|调研组|学习贯彻|表彰大会|参观考察|展演活动|"
    r"学术研讨会在.举行|联合声明呼吁",
    # 外交/国际治理空泛表态（无具体规则、执法或产品）
    r"外交部.*人工智能|参与人工智能全球治理.*中国方案|"
    r"秉持建设性负责任态度参与人工智能",
    # 纯安全攻防/蜜罐/越狱，无法律落地
    r"蜜罐框架|躲过越狱|安全众测|DARPA.*智能体项目|"
    r"政府网站也被入侵|智能体失控风波",
]

# 英文法律垂直媒体：允许 specialty_media 宽进
EN_LEGAL_VERTICAL_IDS = {
    "en-artificial-lawyer",
    "en-legal-it-insider",
    "en-lawsites",
    "en-legaltech-hub",
    "en-everlaw-blog",
    "en-clio-blog",
    "en-tr-legal-posts",
    "en-harvey-blog",
    "en-legora-blog",
    "en-lexis-insights",
    "en-above-the-law",
    "en-iapp",
}

# 中文官媒/综合法治媒体：必须强交叉，不能因 specialty 身份豁免
CN_STRICT_IDS = {
    "zh-jcrb",
    "zh-secrss",
    "zh-secrss-yaml",
    "zh-legaldaily",
    "zh-legaldaily-ai",
    "zh-chinacourt",
    "zh-chinacourt-yaml",
    "zh-cac",
    "zh-cac-news",
    "zh-court",
    "zh-court-gov",
    "zh-miit",
    "zh-npc",
    "zh-moj",
    "zh-gov-cn",
    "zh-rmfyb",
    "zh-spp",
    "zh-fayan-bigdata",
    "zh-fayan-bigdata-builtin",
    "zh-36kr-ai",
    "zh-thepaper-tech",
    "zh-jiqizhixin-builtin",
}

TRUST_SCORE = {
    "official": 52,  # 官媒身份不再自动高分
    "specialty_media": 72,
    "vendor_primary": 70,
    "think_tank": 68,
    "academic": 66,
    "general_media": 50,
    "mixed": 48,
}


def _hit(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def _has_ai(text: str) -> bool:
    return _hit(AI_SIGNAL, text)


def _has_legal(text: str) -> bool:
    return _hit(LEGAL_SIGNAL, text) or _hit(LEGALTECH_SIGNAL, text)


def _has_legaltech(text: str) -> bool:
    return _hit(LEGALTECH_SIGNAL, text)


def _is_noise(title: str, summary: str = "") -> bool:
    text = f"{title}\n{summary}"
    if _hit(NOISE_PATTERNS, text):
        # 噪声里若有极强法律科技硬信号，仍可放行（例如律所 AI 产品展演+具体产品）
        if _has_legaltech(text) and re.search(
            r"产品|融资|发布|开源|判决|条例|办法|起诉|System Card", text, re.I
        ):
            return False
        return True
    return False


def intersection_ok(title: str, summary: str = "") -> bool:
    """法律 AI 交叉：必须同时有 AI 与法律/法律科技信号。"""
    text = f"{title}\n{summary}"
    if not text.strip():
        return False
    if _is_noise(title, summary):
        return False
    return _has_ai(text) and _has_legal(text)


def classify_category(title: str, summary: str, source: dict[str, Any]) -> str:
    text = f"{title}\n{summary}"
    tracks = source.get("tracks") or []

    rules: list[tuple[str, str]] = [
        (r"融资|funding|Series [ABC]|seed round|估值|raised \$|venture", "practice"),
        (
            r"legaltech|LegalTech|法律科技|Harvey|Legora|Clio|Everlaw|CoCounsel|"
            r"合同审查|eDiscovery|lawtech|法律大模型|法律 AI|Legal AI|智能起草",
            "legaltech",
        ),
        (r"诉|lawsuit|诉讼|判决|infringement|起诉|原告|被告|malpractice", "litigation"),
        (r"律所|law firm|associate|billing|KM|实务落地|workflow|工作流|法务部", "practice"),
        (
            r"AI Act|网信|FTC|GDPR|Federal Register|监管|立法|条例|办法|合规治理|"
            r"生成式人工智能.*办法|深度合成.*规定",
            "regulation",
        ),
        (r"启示|insight|评论|opinion|如何改变|启迪", "insight"),
    ]
    for pat, cat in rules:
        if re.search(pat, text, re.I):
            return cat

    # 没有硬信号时：不要把「官媒 + 人工智能」默认成 legaltech
    if "vendor_frontier" in tracks or source.get("trust") == "vendor_primary":
        return "vendor"
    if _has_legaltech(text):
        return "legaltech"
    if _hit(REGULATION_SIGNAL, text):
        return "regulation"
    if _hit(LITIGATION_SIGNAL, text):
        return "litigation"
    if "ai_x_law" in tracks and source.get("trust") != "official":
        return "insight"
    if "law_x_ai" in tracks or source.get("trust") == "official":
        return "regulation"
    return "insight"


def relevance_ok(title: str, summary: str, source: dict[str, Any]) -> bool:
    text = f"{title}\n{summary}"
    source_id = source.get("id") or ""
    trust = source.get("trust") or ""
    lang = source.get("lang") or ""

    if _is_noise(title, summary):
        return False

    # 英文法律垂直媒体：标题/摘要沾 AI 或法律科技即可（源本身已是法律向）
    if source_id in EN_LEGAL_VERTICAL_IDS:
        return _has_ai(text) or _has_legaltech(text) or _has_legal(text)

    # 中文严格源 / 官媒：强制交叉
    if source_id in CN_STRICT_IDS or trust == "official":
        return intersection_ok(title, summary)

    # 综合科技站：强制交叉
    if source_id in {"zh-36kr-ai", "zh-thepaper-tech", "en-techcrunch-ai", "en-mit-tr-ai"}:
        return intersection_ok(title, summary)

    # 厂商一手：研究/安全/政策/法律向，拦营销
    if trust == "vendor_primary":
        if re.search(r"customer story|success story|客户案例|we're hiring", text, re.I):
            return False
        return _hit(
            [
                r"legal|law|court|律师|法律|合规|诉讼|版权|copyright|liability|"
                r"safety|alignment|governance|policy|security|contract|eDiscovery|"
                r"system card|model card|preparedness|model spec|economic index|responsible|"
                r"AI Act|监管|版权局",
            ],
            text,
        )

    # 学术/智库
    if trust in {"academic", "think_tank"}:
        return intersection_ok(title, summary) or (
            _has_ai(text) and _hit(REGULATION_SIGNAL, text)
        )

    # 其余 specialty_media：中文仍要交叉；英文可稍宽
    if trust == "specialty_media":
        if lang == "zh" or "cn" in (source.get("region") or []):
            return intersection_ok(title, summary)
        return _has_ai(text) or _has_legaltech(text)

    # Federal Register 等
    if source_id == "en-federal-register-ai":
        return _hit(
            [
                r"artificial intelligence.*(rule|act|governance|safety|executive)",
                r"(rule|act|governance|safety|executive).*artificial intelligence",
            ],
            text,
        )

    if source_id in {"en-whitehouse-news", "en-ftc-press", "en-above-the-law"}:
        return _has_ai(text) and (_has_legal(text) or _hit(REGULATION_SIGNAL, text))

    # 默认：交叉
    return intersection_ok(title, summary)


def score_item(title: str, summary: str, source: dict[str, Any], category: str) -> float:
    """注意力分 0–100。借鉴 AIHOT：实质份量 + 增量 + 证据 + 共振 + 可用性。"""
    text = f"{title}\n{summary}"
    base = float(TRUST_SCORE.get(source.get("trust") or "", 55))
    source_id = source.get("id") or ""

    # ---- 五轴近似（规则版，不用 LLM）----
    sig = 4  # 实质份量
    nov = 4  # 信息增量
    cred = 5  # 证据
    reson = 4  # 对律师/法务共振
    act = 3  # 可行动性

    if _has_legaltech(text):
        sig += 3
        reson += 2
        act += 2
    if _hit(
        [r"融资|funding|Series [ABC]|raised|估值"],
        text,
    ) and _has_legal(text):
        sig += 2
        reson += 2
    if _hit(LITIGATION_SIGNAL, text):
        sig += 2
        reson += 2
        cred += 1
    if _hit(
        [
            r"AI Act|网信办.*办法|生成式人工智能.*办法|深度合成.*规定|"
            r"Executive Order.*AI|Copyright Office|判决|System Card|Model Spec",
        ],
        text,
    ):
        sig += 3
        nov += 2
        cred += 2
    if re.search(r"发布|上线|开源|推出|宣布|正式", title) and _has_legaltech(text):
        nov += 2
        act += 2

    # 噪声/空泛压分
    if _is_noise(title, summary):
        sig = min(sig, 2)
        reson = min(reson, 2)
        act = min(act, 1)
    if re.search(r"展演|研讨会|宣传周|调研行|座谈会", title):
        sig = min(sig, 3)
        act = min(act, 1)
    if source_id in CN_STRICT_IDS and not _has_legaltech(text):
        # 官媒泛 AI：封顶
        sig = min(sig, 4)
        reson = min(reson, 3)

    # 类型权重（对齐 AIHOT industry_event / product 思路）
    weights = {
        "legaltech": (3, 2, 1, 2, 2),
        "practice": (2, 2, 1, 3, 2),
        "litigation": (3, 2, 2, 3, 0),
        "regulation": (3, 1, 3, 2, 1),
        "vendor": (2, 2, 1, 2, 3),
        "insight": (1, 3, 1, 3, 2),
    }
    w = weights.get(category, (2, 2, 2, 2, 2))
    axes = [min(10, max(0, v)) for v in (sig, nov, cred, reson, act)]
    attention = sum(a * wi for a, wi in zip(axes, w))  # 0–100

    # 与信任底分混合：注意力为主，信任为辅
    score = 0.72 * attention + 0.28 * base

    # 英文法律垂直加分；中文严格源无硬法律科技则减分
    if source_id in EN_LEGAL_VERTICAL_IDS:
        score += 6
    if source_id in CN_STRICT_IDS and not _has_legaltech(text):
        score -= 14
    if source.get("trust") == "official" and category == "regulation":
        score -= 6
    if source.get("tier") == "P0" and source_id in EN_LEGAL_VERTICAL_IDS:
        score += 4

    return max(0.0, min(100.0, round(score, 1)))


def should_select(score: float, category: str, source: dict[str, Any]) -> bool:
    """进入候选池门槛（刊发另有每日配额与交叉门）。"""
    source_id = source.get("id") or ""

    if source_id == "en-federal-register-ai":
        return score >= 90
    if source_id in CN_STRICT_IDS:
        # 中文官媒/综合源：更高门槛，宁缺毋滥
        if category == "regulation":
            return score >= 88
        return score >= 82
    if category == "regulation":
        return score >= 84
    if source.get("trust") == "official":
        return score >= 84
    if category == "vendor":
        return score >= 76
    if category in {"legaltech", "practice"}:
        return score >= 70
    if category == "litigation":
        return score >= 74
    if source_id in EN_LEGAL_VERTICAL_IDS and score >= 68:
        return True
    if source.get("tier") == "P0" and score >= 74:
        return True
    return score >= 78
