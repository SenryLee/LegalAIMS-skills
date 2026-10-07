"""法律 AI 相关度与精选质量单测（不依赖网络）。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.classify import (  # noqa: E402
    classify_category,
    intersection_ok,
    is_pure_legal,
    relevance_ok,
    score_item,
    should_select,
)
from app.edition import edition_eligible, edition_score, pick_edition_rows  # noqa: E402


def _src(**kw):
    base = {
        "id": "zh-jcrb",
        "name": "正义网",
        "lang": "zh",
        "region": ["cn"],
        "tier": "P2",
        "trust": "official",
        "tracks": ["ai_x_law"],
    }
    base.update(kw)
    return base


class IntersectionTests(unittest.TestCase):
    """v0.5 分层：预筛只管「是否与 AI 有关」，噪声与质量由评分层压分。

    这些用例断言的是**分工**而非单一函数的结论：一条噪声可以放行预筛
    （宽召回，为了给客户端留池子），但必须在is_pure_legal / score_item /
    should_select 这一层被压到入库门槛以下。
    """

    def test_rejects_compute_power_soft_news(self):
        title = "西部的风给东部企业“供智能” 解锁宁夏中卫东西部算力互济新范式丨活力中国调研行"
        self.assertFalse(intersection_ok(title))
        self.assertFalse(relevance_ok(title, "", _src()))

    def test_soft_news_is_blocked_from_pool_despite_wide_prefilter(self):
        """算力软文：无实质 AI 信号，进不了候选池。"""
        title = "西部的风给东部企业“供智能” 解锁宁夏中卫东西部算力互济新范式丨活力中国调研行"
        src = _src()
        cat = classify_category(title, "", src)
        self.assertTrue(is_pure_legal(title))
        self.assertFalse(should_select(score_item(title, "", src, cat), cat, src))

    def test_rejects_world_skills(self):
        title = "本届世赛新增3个人工智能相关赛项 数量创历届之最"
        src = _src()
        # 预筛宽召回会放行（「人工智能」字面存在），但质量层必须压掉
        self.assertTrue(relevance_ok(title, "", src))
        cat = classify_category(title, "", src)
        self.assertTrue(is_pure_legal(title))
        self.assertFalse(should_select(score_item(title, "", src, cat), cat, src))

    def test_rejects_diplomacy_boilerplate(self):
        title = "外交部：中方始终秉持建设性负责任态度参与人工智能全球治理，持续不断贡献中国方案"
        src = _src(id="zh-legaldaily", trust="official")
        self.assertTrue(relevance_ok(title, "", src))
        cat = classify_category(title, "", src)
        self.assertTrue(is_pure_legal(title))
        self.assertFalse(should_select(score_item(title, "", src, cat), cat, src))

    def test_rejects_honeypot_security(self):
        title = "HiveAI：面向大模型API的蜜罐框架"
        src = _src(id="zh-secrss", trust="specialty_media")
        self.assertTrue(relevance_ok(title, "", src))
        cat = classify_category(title, "", src)
        # 有「大模型」所以不算纯法律动态，但噪声门必须把分数压到门槛下
        self.assertLess(score_item(title, "", src, cat), 30)

    def test_accepts_legal_supervision_ai(self):
        title = "人工智能促进法律监督提质增效"
        src = _src(id="zh-legaldaily", trust="official")
        self.assertTrue(intersection_ok(title))
        self.assertTrue(relevance_ok(title, "", src))
        # 真正的 AI×法律交叉：不能被当成纯法律动态挡掉
        self.assertFalse(is_pure_legal(title))

    def test_accepts_english_legaltech(self):
        title = "Harvey raises new funding for legal AI platform"
        src = _src(
            id="en-artificial-lawyer",
            lang="en",
            region=["global"],
            trust="specialty_media",
            tier="P0",
        )
        self.assertTrue(relevance_ok(title, "", src))
        cat = classify_category(title, "", src)
        self.assertEqual(cat, "practice")
        score = score_item(title, "", src, cat)
        # 规则版是客户端评分之外的入库参考路径（服务端粗排）。这里断言的是
        # 「优质条目不被误埋没」：分数必须高于同批官媒噪声，且通过 should_select。
        # 规则分到70 属预期——五轴里 act 需要正文才能判断可行动性，而本例摘要为空；
        # 客户端评分不受此限制。
        self.assertGreater(score, 60)
        self.assertTrue(should_select(score, cat, src))


class ScoringTests(unittest.TestCase):
    def test_gov_generic_ai_scores_lower_than_legaltech(self):
        soft = "工业和信息化部：加快信息通信网络和行业智能化升级"
        hard = "Harvey AI launches new contract review workflow for law firms"
        gov = _src()
        en = _src(
            id="en-artificial-lawyer",
            lang="en",
            trust="specialty_media",
            tier="P0",
            region=["global"],
        )
        # soft may fail relevance; if scored as insight/regulation it must be lower
        soft_cat = classify_category(soft, "", gov)
        hard_cat = classify_category(hard, "", en)
        soft_score = score_item(soft, "", gov, soft_cat)
        hard_score = score_item(hard, "", en, hard_cat)
        self.assertGreater(hard_score, soft_score)
        self.assertFalse(should_select(soft_score, soft_cat, gov))


class EditionTests(unittest.TestCase):
    def test_pick_prefers_legaltech_over_gov_noise(self):
        rows = [
            {
                "id": "1",
                "title": "本届世赛新增3个人工智能相关赛项 数量创历届之最",
                "summary": "世界技能大赛新增 AI 赛项，覆盖深度学习等场景。",
                "source_id": "zh-jcrb",
                "source_name": "正义网",
                "category": "legaltech",
                "score": 96,
                "lang": "zh",
                "original_url": "https://example.com/1",
                "selected": True,
            },
            {
                "id": "2",
                "title": "Harvey launches contract review agent for AmLaw firms",
                "summary": "Harvey 面向大型律所发布合同审查 Agent，支持尽调工作流与审计日志。",
                "source_id": "en-artificial-lawyer",
                "source_name": "Artificial Lawyer",
                "category": "legaltech",
                "score": 78,
                "lang": "en",
                "original_url": "https://example.com/2",
                "selected": True,
            },
            {
                "id": "3",
                "title": "人工智能促进法律监督提质增效",
                "summary": "检察机关用大模型辅助法律监督线索发现与案件研判，试点覆盖若干省市。",
                "source_id": "zh-legaldaily",
                "source_name": "法治日报",
                "category": "practice",
                "score": 80,
                "lang": "zh",
                "original_url": "https://example.com/3",
                "selected": True,
            },
            {
                "id": "4",
                "title": "司法护航人工智能产业行稳致远",
                "summary": "法院表示将为人工智能产业提供司法保障，推动高质量发展。",
                "source_id": "zh-legaldaily",
                "source_name": "法治日报",
                "category": "insight",
                "score": 88,
                "lang": "zh",
                "original_url": "https://example.com/4",
                "selected": True,
            },
        ]
        self.assertFalse(edition_eligible(rows[0]))
        self.assertTrue(edition_eligible(rows[1]))
        self.assertTrue(edition_eligible(rows[2]))
        self.assertFalse(edition_eligible(rows[3]))
        picked = pick_edition_rows(rows, require_summary=True)
        ids = [r["id"] for r in picked]
        self.assertIn("2", ids)
        self.assertIn("3", ids)
        self.assertNotIn("1", ids)
        self.assertNotIn("4", ids)
        # 英文垂直源刊发分应高于官媒
        self.assertGreater(edition_score(rows[1]), edition_score(rows[2]))

    def test_edition_keeps_official_ai_legal_cross(self):
        """官媒来源的 AI×法律硬交叉必须能进每日读本。

        这是 v0.5 修掉的一个真实缺陷：「法院判决 AI 生成内容著作权归属」
        这类条目此前被「官媒泛 AI 封顶」规则压到入库门槛以下，而它恰恰是
        本刊的核心内容。
        """
        rows = [
            {
                "id": "1",
                "title": "法院判决 AI 生成内容著作权归属案",
                "summary": "法院就AI 生成内容著作权归属作出判决，认定生成式人工智能的作者认定标准。",
                "source_id": "zh-court",
                "source_name": "中国法院网",
                "category": "litigation",
                "score": 44,
                "lang": "zh",
                "original_url": "https://example.com/1",
                "selected": True,
            },
        ]
        self.assertTrue(edition_eligible(rows[0]))
        self.assertTrue(pick_edition_rows(rows, require_summary=True))


if __name__ == "__main__":
    unittest.main()
