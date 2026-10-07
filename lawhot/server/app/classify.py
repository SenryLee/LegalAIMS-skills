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
    r"OpenAI|Anthropic|DeepSeek|法律大模型|Legal AI|legal AI|"
    # 法律科技本身就是 AI 应用于法律服务，硬门必须承认它，
    # 否则「法律科技公司完成融资」这类不含「AI」字样的条目会被误挡。
    r"法律科技|legaltech|legal tech|lawtech|LegalTech|法律智能|智能法律|"
    # 通用模型语言：不写具体厂商/版本号时也常只用「模型」「上下文」等词
    r"新模型|模型发布|开源模型|上下文窗口|长上下文|推理模型|多模态模型|"
    r"token|参数|微调|蒸馏|嵌入|检索增强|RAG|提示词|prompt|幻觉|对齐",
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
    r"活力中国调研行|东西部算力|算电协同|智能经济绿色底座|"
    r"研讨会|论坛|峰会|大会|年会|签约仪式|揭牌|"
    r"召开|座谈会|调研组|学习贯彻|表彰大会|参观考察|展演活动|"
    r"学术研讨会在.举行|联合声明呼吁",
    # 外交/国际治理空泛表态（无具体规则、执法或产品）
    r"外交部.*人工智能|参与人工智能全球治理.*中国方案|"
    r"秉持建设性负责任态度参与人工智能|"
    r"共促.{0,8}人工智能.{0,10}(健康有序|有序发展)|"
    r"贡献中国方案|推动算电协同",
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


# 公开别名：供 edition.py 等模块使用，避免跨模块引用私有名。
has_ai_signal = _has_ai
has_legal_signal = _has_legal
has_legaltech_signal = _has_legaltech


def _is_noise(title: str, summary: str = "") -> bool:
    text = f"{title}\n{summary}"
    if _hit(NOISE_PATTERNS, text):
        # 例外放行收紧：必须同时具备法律科技硬信号与可核对的具体动作。
        # 旧规则只要命中「产品/融资/发布/开源/…」任一词就整条放行，导致
        # 「推动算电协同」「共促全球人工智能健康有序发展」这类口号文靠一个词过关。
        has_legaltech = _has_legaltech(text)
        concrete = re.search(
            r"融资(?:轮|额|规模)|收购|并购|IPO|估值|"
            r"开源|发布|上线|判决|起诉|裁定|条例|办法|规定|指引|生效|违规|处罚|"
            r"合同审查|尽调|检索|起草|Agent|智能体|基准|评测",
            text,
            re.I,
        )
        return not (has_legaltech and concrete)
    return False


# 噪声门的公开别名：每日读本（edition）没有客户端评分兜底，必须直接用它挡住
# 算力软文、会议通稿、外交空谈。
is_noise = _is_noise


def intersection_ok(title: str, summary: str = "") -> bool:
    """AI 实质信号为硬门，法律侧降为加权维度。

    定位是科技优先、法律语境优先：通用 AI 新闻（模型发布、Agent 框架开源）
    必须能进入评分器，再由 LLM 评估它对法律工作的传导路径。若在此处要求
    AI×法律硬交叉，通用科技新闻会在评分前被误挡，评分器无从判断 leg 维度。
    """
    text = f"{title}\n{summary}"
    if not text.strip():
        return False
    if _is_noise(title, summary):
        return False
    if not _has_ai(text):
        return False
    # 法律信号不再作硬门：缺失只影响后续 leg 打分，不影响进入候选池。
    # 但完全没有任何法律语境、且属消费/娱乐/图像生成类的通用科技新闻直接挡掉。
    if _has_legal(text) or _has_legaltech(text):
        return True
    return not _is_off_domain_tech(title, summary)


# 与法律服务、法律科技市场、法律监管无传导路径的通用科技方向。
# 这些不属于「科技优先」要覆盖的素材：AI 圈重要，但对法律读者没有可迁移落点。
OFF_DOMAIN_PATTERNS = [
    r"图像生成|绘画|艺术创作|音乐生成|视频生成|自拍|写真|滤镜|"
    r"游戏|Gaming|游戏内|电竞|漫画|动漫|头像",
    r"推荐算法.*广告|广告投放|电商推荐|直播带货|社交裂变|增长黑客",
    r"消费级.{0,4}(应用|功能|助手)|手机厂商.{0,6}(助手|大模型)|"
    r"智能音箱|可穿戴|耳机|手表|扫地机器人",
]


def _is_off_domain_tech(title: str, summary: str = "") -> bool:
    """纯消费/娱乐/图像类通用科技：AI 成立但与法律工作无传导路径。"""
    text = f"{title}\n{summary}"
    return bool(_hit(OFF_DOMAIN_PATTERNS, title)) or bool(
        _hit(OFF_DOMAIN_PATTERNS, summary) and not _has_legal(text)
    )


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
    # 通用科技新闻（AI 成立、法律语境缺失）不再默认落到 regulation。
    # 它进评分器由 LLM 判 leg，此前归 insight，避免官媒身份把通用科技伪装成监管动态。
    if _is_off_domain_tech(title, summary):
        return "insight"
    if "ai_x_law" in tracks and source.get("trust") != "official":
        return "insight"
    if "law_x_ai" in tracks or source.get("trust") == "official":
        return "regulation"
    return "insight"


def relevance_ok(title: str, summary: str, source: dict[str, Any]) -> bool:
    """宽召回预筛：只判断「是否与 AI 有关」，不判断「值不值得看」。

    质量判断已移到客户端（skill 的 selection-score.md），服务端不再替用户
    做筛选决策。因此这里只保留一条硬门——必须含 AI 实质信号；连法律信号都
    不要求，因为通用科技新闻恰恰要靠客户端的 `leg` 轴去判断它对法律工作的
    传导路径，服务端提前挡掉等于替客户端做了决定。

    噪声（算力软文、会议通稿、纯法律动态）在这里**故意不拦**：由客户端评分
    压分。实测收紧版预筛会把 7 天候选压到 3 条，客户端无池可选。
    """
    text = f"{title}\n{summary}"
    if not text.strip():
        return False
    if not _has_ai(text):
        return False
    # 只挡两类「与 AI 毫无关系」的极端情况：厂商营销与招聘
    if re.search(
        r"customer story|success story|客户案例|we'?re hiring|招聘|求职|"
        r"限时|优惠|免费领取|课程报名",
        text,
        re.I,
    ):
        return False
    return True


def is_pure_legal(title: str, summary: str = "") -> bool:
    """无 AI 实质信号：纯法律/司法动态，或只是沾了「AI」字面的其它品类。

    本刊定位是科技优先、法律语境优先，这类素材不在关注范围。用于给评分
    结果兜底封顶，也用于规则版回退路径直接压到低位。

    注意：消费级AI（AI 写真、AI 相机）同样落在这里——它们不是纯法律动态，
    但同样没有法律传导，与纯法律动态做同样的处理。
    """
    text = f"{title}\n{summary}"
    if not _has_ai(text):
        return True
    # AI 信号若只出现在专有名词里（智慧法院、AI 审判等口号式表述），不算实质信号
    substantive = _has_legaltech(text) or _hit(
        [
            r"大模型|LLM|GPT|生成式|智能体|Agent|机器学习|深度学习|算法|"
            r"模型|推理|开源|微调|RAG|提示词|prompt|token|算力|"
            # 「人工智能促进法律监督提质增效」这类：AI 是主语且落在法律业务环节上，
            # 不是背景提及。仅靠「+AI」二字不足以判定为实质，缺了这条会把
            # 检察/法院侧的真实 AI 应用一并误判为纯法律动态。
            r"人工智能.{0,12}(促进|赋能|提升|改进|应用|辅助|驱动|"
            r"审判|裁判|监督|办案|检索|审查|释法)|"
            r"(审判|裁判|监督|办案|检索|审查|释法|仲裁).{0,12}人工智能",
        ],
        text,
    )
    return not substantive


def is_ai_legal_cross(title: str, summary: str = "") -> bool:
    """AI 实质信号 **且** 法律语境成立——真正的交叉素材。

    这类条目不应被「官媒泛AI 封顶」规则压掉：判决、监管规则、法律科技产品
    即使来自官方媒体，也是本刊的核心内容，而不是官媒空谈。
    """
    text = f"{title}\n{summary}"
    if is_pure_legal(title, summary):
        return False
    return _has_legaltech(text) or _hit(LITIGATION_SIGNAL, text)


def score_item(title: str, summary: str, source: dict[str, Any], category: str) -> float:
    """注意力分 0–100（规则版，仅在 LLM 不可用时回退）。

    LLM 主路径见 score_llm.py 与 prompts/selection-score.md。此处保留
    同构的五轴与类型权重，但基线下调——旧版基线（sig=4/nov=4/cred=5）叠加
    正则加分后会普遍冲到 95+，失去区分度。
    """
    text = f"{title}\n{summary}"
    base = float(TRUST_SCORE.get(source.get("trust") or "", 55))
    source_id = source.get("id") or ""

    # 纯法律动态：直接压到低位，不进入后续加权
    if is_pure_legal(title, summary):
        return round(min(base * 0.3, 20.0), 1)

    # ---- 五轴近似（规则版回退，不用 LLM）----
    # 基线取中等偏上而非旧版的偏高值：旧版（sig=4/nov=4/cred=5/reson=4/act=3）
    # 叠加正则后普遍冲到 95+，同批条目挤成一团，失去区分度。这里下调一档，
    # 让规则分与 should_select 的 68–90 门槛体系仍然相容。
    sig = 4  # 实质份量
    nov = 3  # 信息增量
    cred = 4  # 证据
    leg = 3  # 法律传导
    act = 2  # 可行动性

    # RSS 常无摘要，标题即全部证据。法律科技垂直源的标题通常是
    # 「品牌 + 动作 + 标的」结构（如 Harvey raises new funding for legal AI），
    # 其证据强度不应按缺摘要惩罚，否则优质条目会被系统性低估。
    if not (summary or "").strip() and source_id in EN_LEGAL_VERTICAL_IDS:
        cred += 3
        nov += 2
        sig += 1

    if _has_legaltech(text):
        leg += 4
        sig += 1
    elif source_id in EN_LEGAL_VERTICAL_IDS:
        # 法律科技垂直源本身即是法律传导的强证据。RSS 摘要常为空，
        # 若 leg 只靠正文命中会系统性低估这类优质条目。
        leg += 2
    if _hit(
        [r"融资|funding|Series [ABC]|raised|估值"],
        text,
    ) and _has_legal(text):
        sig += 1
        leg += 1
        # 融资、收购、IPO 是明确的商业动作，读者据此可判断赛道温度与竞争格局，
        # 不因缺摘要而低估可行动性。
        act += 2
    if _hit(LITIGATION_SIGNAL, text):
        sig += 1
        leg += 2
    if _hit(
        [
            r"AI Act|网信办.*办法|生成式人工智能.*办法|深度合成.*规定|"
            r"Executive Order.*AI|Copyright Office|System Card|Model Spec",
        ],
        text,
    ):
        sig += 1
        cred += 2
    if re.search(r"发布|上线|开源|推出", title) and _has_legaltech(text):
        nov += 1
        act += 2
    if _is_off_domain_tech(title, summary):
        leg = min(leg, 1)

    # 噪声/空泛压分
    if _is_noise(title, summary):
        sig = min(sig, 2)
        leg = min(leg, 1)
        act = min(act, 1)
    if re.search(r"展演|研讨会|宣传周|调研行|座谈会", title):
        sig = min(sig, 2)
        act = min(act, 1)
    # 官媒泛 AI：封顶。但真正的 AI×法律交叉（判决、监管规则、法律科技产品）
    # 即使来自官方媒体也要豁免，否则「法院判决 AI 生成内容著作权归属」这类
    # 本刊核心内容会被当成官媒空谈压掉。
    if source_id in CN_STRICT_IDS and not is_ai_legal_cross(title, summary):
        sig = min(sig, 3)
        leg = min(leg, 2)

    # 类型权重（与 prompts/selection-score.md 的 leg 轴对齐）
    weights = {
        "legaltech": (3, 2, 1, 3, 1),
        "practice": (2, 2, 1, 3, 2),
        "litigation": (2, 2, 2, 3, 1),
        "regulation": (3, 2, 3, 1, 1),
        "vendor": (2, 2, 1, 2, 2),
        "insight": (1, 3, 1, 3, 2),
    }
    w = weights.get(category, (2, 2, 2, 2, 2))
    axes = [min(10, max(0, v)) for v in (sig, nov, cred, leg, act)]
    attention = sum(a * wi for a, wi in zip(axes, w))  # 0–100

    # 与信任底分混合：注意力为主，信任为辅
    score = 0.72 * attention + 0.28 * base

    # 英文法律垂直加分；中文严格源无硬法律科技则减分
    if source_id in EN_LEGAL_VERTICAL_IDS:
        score += 4
    if source_id in CN_STRICT_IDS and not is_ai_legal_cross(title, summary):
        score -= 10
    if source.get("trust") == "official" and category == "regulation":
        score -= 6

    return max(0.0, min(100.0, round(score, 1)))


def should_select(score: float, category: str, source: dict[str, Any]) -> bool:
    """候选入库门槛（宽召回）。

    服务端不再做质量判断，因此这里的门槛只用来剔除**明显该丢**的条目，
    真正的高门槛由客户端 skill 的 selection-score.md 负责。
    旧实现在68–90 分档之间卡选，结果是 7 天只剩 3 条候选，客户端无从筛选。

    保留两档：纯法律动态（<=20）直接不进候选池，其余 30 分以上即可入库。
    """
    if score >= 30:
        return True
    # 30 分以下只放行高信任度的法律科技垂直源，避免优质条目因规则分偏低被误丢
    return score >= 25 and (source.get("id") or "") in EN_LEGAL_VERTICAL_IDS
