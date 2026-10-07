"""验证 v0.5 架构：服务端宽召回 + 客户端评分。

三层职责在v0.5 明确分开，本测试逐层断言：
1. 预筛（`relevance_ok`）**只**判断「是否与 AI 有关」，故意不拦噪声与纯法律动态
2. `is_pure_legal` 识别无AI 实质信号的条目，评分时压到低位
3. 规则版 `score_item` 必须有区分度（旧版挤在 96–100，等于没有区分度）

用线上真实条目做回归，不依赖训练记忆或手写假分数。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classify import (  # noqa: E402
    classify_category,
    is_ai_legal_cross,
    is_pure_legal,
    relevance_ok,
    score_item,
    should_select,
)

# 字段含义：
#   prefilter  —— 期望的预筛结论（"in" 放行 / "out" 挡掉）
#   pure       —— 期望的 is_pure_legal 结论（无 AI 实质信号 = True）
#   cross      —— 期望的 AI×法律硬交叉结论
#   rule       —— 期望的规则版分数区间，None 表示只打印不断言
CASES = [
    {
        "id": "trump",
        "title": "特朗普宣布成立“超级智能特别工作组”",
        "summary": "美国总统宣布成立超级智能特别工作组，推动人工智能产业发展与国家安全协同。",
        "source": {"id": "zh-legaldaily", "trust": "official", "lang": "zh"},
        "prefilter": "in", "pure": True, "cross": False, "rule": (0, 25),
    },
    {
        "id": "musk",
        "title": "对话马斯克：中美关系、人工智能和人类未来",
        "summary": "长篇访谈，涉及人工智能发展、中美关系与人类未来。",
        "source": {"id": "zh-fayan-bigdata", "trust": "official", "lang": "zh"},
        "prefilter": "in", "pure": True, "cross": False, "rule": (0, 25),
    },
    {
        "id": "compute",
        "title": "推动算电协同 夯实智能经济绿色底座",
        "summary": "推动算电协同，夯实智能经济绿色底座。人工智能与能源融合。",
        "source": {"id": "zh-legaldaily", "trust": "official", "lang": "zh"},
        # v0.5：预筛故意不拦算力软文，交给客户端评分压分（提示词里≤20 的硬上限）
        "prefilter": "in", "pure": True, "cross": False, "rule": (0, 25),
    },
    {
        "id": "foreign",
        "title": "共促全球人工智能健康有序发展",
        "summary": "中方倡导共促全球人工智能健康有序发展，贡献中国方案。",
        "source": {"id": "zh-legaldaily-ai", "trust": "official", "lang": "zh"},
        "prefilter": "in", "pure": True, "cross": False, "rule": (0, 25),
    },
    {
        "id": "pure_legal",
        "title": "最高人民法院发布知识产权司法保护典型案例",
        "summary": "最高人民法院发布一批知识产权纠纷典型案例，涉及专利与商标侵权。",
        "source": {"id": "zh-court", "trust": "official", "lang": "zh"},
        "prefilter": "out", "pure": True, "cross": False, "rule": None,
    },
    {
        "id": "lawfirm_hire",
        "title": "某律所宣布新任合伙人加盟",
        "summary": "该律所宣布新任合伙人加盟，业务覆盖公司与并购。",
        "source": {"id": "zh-rmfyb", "trust": "official", "lang": "zh"},
        "prefilter": "out", "pure": True, "cross": False, "rule": None,
    },
    {
        "id": "claude_court",
        "title": "法院判决 AI 生成内容著作权归属案",
        "summary": "法院就AI 生成内容著作权归属作出判决，认定生成式人工智能的作者认定标准。",
        "source": {"id": "zh-court", "trust": "official", "lang": "zh"},
        # 官媒来源，但属AI×法律硬交叉，必须豁免「官媒泛 AI 封顶」并进入候选池
        "prefilter": "in", "pure": False, "cross": True, "rule": (30, 100),
    },
    {
        "id": "agent_oss",
        "title": "开源通用智能体运行框架，支持自控上下文与工具审批",
        "summary": "该开源框架让团队自行控制界面、上下文、工具调用与审批流程，可用于法律检索等场景。",
        "source": {"id": "en-techcrunch-ai", "trust": "specialty_media", "lang": "en"},
        "prefilter": "in", "pure": False, "cross": False, "rule": (30, 100),
    },
    {
        "id": "model_release",
        "title": "某公司发布新模型，长上下文能力显著提升",
        "summary": "新模型在长文档处理上显著提升，可用于合同审阅与尽调材料分析。",
        "source": {"id": "en-techcrunch-ai", "trust": "specialty_media", "lang": "en"},
        "prefilter": "in", "pure": False, "cross": True, "rule": (30, 100),
    },
    {
        "id": "consumer",
        "title": "AI 相机应用推出自拍写真功能",
        "summary": "消费级应用新增 AI 写真生成功能，用户可一键生成照片。",
        "source": {"id": "zh-36kr-ai", "trust": "specialty_media", "lang": "zh"},
        "prefilter": "in", "pure": True, "cross": False, "rule": (0, 25),
    },
    {
        "id": "legaltech_funding",
        "title": "法律科技公司完成新一轮融资",
        "summary": "该法律科技公司完成 B 轮融资，资金将用于合同审查产品研发，明确客户数与营收增长。",
        "source": {"id": "en-legaltech-hub", "trust": "specialty_media", "lang": "en"},
        "prefilter": "in", "pure": False, "cross": True, "rule": (50, 100),
    },
    {
        "id": "conference",
        "title": "某地举办法律人工智能研讨会",
        "summary": "研讨会探讨大模型在法律服务中的应用。",
        "source": {"id": "zh-legaldaily", "trust": "official", "lang": "zh"},
        "prefilter": "in", "pure": False, "cross": False, "rule": (0, 30),
    },
    {
        "id": "hiring",
        "title": "某法律科技公司诚招资深算法工程师",
        "summary": "招聘算法工程师，负责大模型在合同审查场景的落地。",
        "source": {"id": "zh-36kr-ai", "trust": "specialty_media", "lang": "zh"},
        # 预筛挡在营销/招聘门。cross仍为 True——这条确实同时含AI 与法律信号，
        # is_ai_legal_cross 只判信号成立与否，编辑价值由预筛和客户端评分负责。
        "prefilter": "out", "pure": False, "cross": True, "rule": None,
    },
]


def main() -> None:
    failures: list[str] = []
    print(
        f"{'条目':<20}{'预筛':<6}{'纯法律':<8}{'交叉':<6}"
        f"{'category':<12}{'规则分':<8}{'入库':<6}预期"
    )
    print("-" * 88)

    for c in CASES:
        src = c["source"]
        title, summary = c["title"], c["summary"]
        ok = relevance_ok(title, summary, src)
        pure = is_pure_legal(title, summary)
        cross = is_ai_legal_cross(title, summary)
        cat = classify_category(title, summary, src)
        sc = score_item(title, summary, src, cat)
        picked = should_select(sc, cat, src)

        def check(label: str, got: object, want: object, cid: str = c["id"]) -> None:
            if got != want:
                failures.append(f"{cid}.{label}: 实际 {got!r}，期望 {want!r}")

        check("prefilter", "in" if ok else "out", c["prefilter"])
        check("pure", pure, c["pure"])
        check("cross", cross, c["cross"])
        if c["rule"] is not None:
            lo, hi = c["rule"]
            if not lo <= sc <= hi:
                failures.append(f"{c['id']}.score: {sc} 不在区间 [{lo}, {hi}]")
        # 纯法律动态绝不能进候选池——这是定位的硬约束
        if pure and picked:
            failures.append(f"{c['id']}: 纯法律动态进了候选池")

        print(
            f"{c['id']:<20}{'✓' if ok else '✗':<6}{str(pure):<8}{str(cross):<6}"
            f"{cat:<12}{sc:<8}{'✓' if picked else '✗':<6}"
            f"预筛{c['prefilter']} / 纯法律{c['pure']} / 交叉{c['cross']}"
        )

    scores = [
        score_item(
            c["title"],
            c["summary"],
            c["source"],
            classify_category(c["title"], c["summary"], c["source"]),
        )
        for c in CASES
    ]
    spread = max(scores) - min(scores)
    print()
    print(f"规则版分数区间：{min(scores)} ~ {max(scores)}（极差 {spread}）")
    if spread < 30:
        failures.append(f"分数极差仅 {spread}，区分度不足")
    over90 = sum(1 for s in scores if s > 90)
    if over90:
        failures.append(f"{over90} 条超过 90 分，存在虚高")
    print(f"虚高检查：>90 分条目数 = {over90}")
    print(f"入库条数：{sum(1 for c in CASES if not c['rule'] or c['rule'][0] > 25)}"
          f" / {len(CASES)}（其余被预筛或压分挡掉）")

    print()
    if failures:
        print(f"✗ {len(failures)} 项断言失败：")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print(f"✓ 全部 {len(CASES)} 条用例通过三层断言")


if __name__ == "__main__":
    main()