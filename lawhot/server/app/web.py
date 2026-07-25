from __future__ import annotations

import html
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .config import PUBLIC_BASE_URL

SHANGHAI = ZoneInfo("Asia/Shanghai")

CAT_LABEL = {
    "regulation": "监管政策",
    "litigation": "诉讼案例",
    "legaltech": "法律科技",
    "practice": "实务落地",
    "insight": "行业启迪",
    "vendor": "厂商动态",
}


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _bj_time(iso: str | None) -> str:
    if not iso:
        return "时间未知"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(SHANGHAI)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


def layout(title: str, body: str, *, description: str = "") -> str:
    desc = description or "全球法律 AI 资讯 · AI 对法律行业的启迪"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(desc)}" />
  <link rel="alternate" type="application/rss+xml" title="LawHOT 精选" href="{_esc(PUBLIC_BASE_URL)}/feed.xml" />
  <style>
    :root {{
      --ink: #14212b;
      --muted: #5c6b76;
      --paper: #f3f1ea;
      --panel: #fffdf8;
      --line: #d9d2c5;
      --accent: #0f6e56;
      --accent-2: #b45309;
      --shadow: 0 18px 50px rgba(20, 33, 43, 0.08);
      --serif: "Source Han Serif SC", "Noto Serif SC", "Songti SC", "Times New Roman", serif;
      --sans: "IBM Plex Sans", "Source Han Sans SC", "PingFang SC", "Noto Sans SC", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(1200px 500px at 10% -10%, rgba(15,110,86,.12), transparent 60%),
        radial-gradient(900px 400px at 90% 0%, rgba(180,83,9,.10), transparent 55%),
        linear-gradient(180deg, #e8e4d8 0%, var(--paper) 38%, #efece3 100%);
      font-family: var(--sans);
      line-height: 1.65;
      min-height: 100vh;
    }}
    a {{ color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    a:hover {{ color: var(--accent-2); }}
    .wrap {{ width: min(920px, calc(100% - 2rem)); margin: 0 auto; padding: 2.2rem 0 4rem; }}
    header.hero {{
      padding: 1.4rem 0 1.8rem;
      border-bottom: 1px solid var(--line);
      margin-bottom: 1.8rem;
    }}
    .brand {{
      font-family: var(--serif);
      font-size: clamp(2.4rem, 6vw, 3.6rem);
      letter-spacing: 0.02em;
      margin: 0 0 0.35rem;
      line-height: 1.1;
    }}
    .brand span {{ color: var(--accent); }}
    .tagline {{
      margin: 0;
      color: var(--muted);
      font-size: 1.05rem;
      max-width: 36em;
    }}
    .nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.85rem 1.2rem;
      margin-top: 1.1rem;
      font-size: 0.95rem;
    }}
    .nav a {{ color: var(--ink); text-decoration: none; border-bottom: 1px solid transparent; }}
    .nav a:hover {{ border-bottom-color: var(--accent); color: var(--accent); }}
    .note {{
      margin: 0 0 1.4rem;
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .item {{
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 1.15rem 1.25rem 1.2rem;
      margin: 0 0 1rem;
    }}
    .item h2 {{
      font-family: var(--serif);
      font-size: 1.28rem;
      line-height: 1.35;
      margin: 0 0 0.55rem;
      font-weight: 650;
    }}
    .item h2 a {{ color: inherit; text-decoration: none; }}
    .item h2 a:hover {{ color: var(--accent); }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem 0.9rem;
      color: var(--muted);
      font-size: 0.86rem;
      margin-bottom: 0.55rem;
    }}
    .chip {{
      display: inline-block;
      padding: 0.1rem 0.45rem;
      border: 1px solid var(--line);
      background: #f7f3ea;
      color: var(--ink);
    }}
    .summary {{ margin: 0; color: #24333d; }}
    .links {{ margin-top: 0.75rem; font-size: 0.9rem; display: flex; gap: 1rem; flex-wrap: wrap; }}
    footer {{
      margin-top: 2.5rem;
      padding-top: 1rem;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .detail .summary {{ font-size: 1.05rem; }}
    .back {{ display: inline-block; margin-bottom: 1rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    {body}
    <footer>
      <p>LawHOT · 法锤法律 AI 资讯中台。资讯聚合，非法律意见；重要引用请回原文核对。</p>
      <p>机器接口：<a href="{_esc(PUBLIC_BASE_URL)}/api/v1/items?mode=selected&amp;window=24h&amp;limit=10">API</a>
      · <a href="{_esc(PUBLIC_BASE_URL)}/feed.xml">RSS</a>
      · <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md">Skill</a>
      · <a href="{_esc(PUBLIC_BASE_URL)}/healthz">健康检查</a></p>
    </footer>
  </div>
</body>
</html>"""


def render_home(items: list[Any], stats: dict[str, Any]) -> str:
    cards = []
    for r in items:
        cat = CAT_LABEL.get(r["category"] or "", r["category"] or "未分类")
        lawhot = f"{PUBLIC_BASE_URL}/items/{r['id']}"
        original = r["original_url"] or "#"
        cards.append(
            f"""
<article class="item">
  <h2><a href="{_esc(lawhot)}">{_esc(r['title'])}</a></h2>
  <div class="meta">
    <span class="chip">{_esc(cat)}</span>
    <span>{_esc(r['source_name'])}</span>
    <span>{_esc(_bj_time(r['published_at'] or r['discovered_at']))} 北京时间</span>
  </div>
  <p class="summary">{_esc(r['summary'] or '暂无摘要')}</p>
  <div class="links">
    <a href="{_esc(lawhot)}">站内阅读</a>
    <a href="{_esc(original)}" rel="noopener noreferrer" target="_blank">原文</a>
  </div>
</article>"""
        )
    if not cards:
        cards.append('<p class="note">暂无精选条目。请稍后刷新，或检查抓取任务。</p>')

    body = f"""
<header class="hero">
  <h1 class="brand">Law<span>HOT</span></h1>
  <p class="tagline">全球法律 AI 资讯，以及 AI 对法律行业的启迪。给律师、法务与合规同学的每日简报。</p>
  <nav class="nav" aria-label="站点导航">
    <a href="{_esc(PUBLIC_BASE_URL)}/">精选</a>
    <a href="{_esc(PUBLIC_BASE_URL)}/feed.xml">RSS 订阅</a>
    <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/">Agent Skill</a>
    <a href="{_esc(PUBLIC_BASE_URL)}/api/v1/items?mode=selected&amp;window=24h&amp;limit=10">JSON API</a>
  </nav>
</header>
<p class="note">当前库内 {int(stats.get('items') or 0)} 条 · 精选 {int(stats.get('selected') or 0)} 条 · 以下为最近精选</p>
{''.join(cards)}
"""
    return layout("LawHOT · 法律 AI 资讯", body)


def render_item(row: Any) -> str:
    cat = CAT_LABEL.get(row["category"] or "", row["category"] or "未分类")
    original = row["original_url"] or "#"
    body = f"""
<p class="back"><a href="{_esc(PUBLIC_BASE_URL)}/">← 返回精选</a></p>
<article class="item detail">
  <h1 class="brand" style="font-size:clamp(1.6rem,4vw,2.2rem);margin-bottom:0.7rem">{_esc(row['title'])}</h1>
  <div class="meta">
    <span class="chip">{_esc(cat)}</span>
    <span>{_esc(row['source_name'])}</span>
    <span>发布 {_esc(_bj_time(row['published_at']))}</span>
    <span>收录 {_esc(_bj_time(row['discovered_at']))}</span>
  </div>
  <p class="summary">{_esc(row['summary'] or '暂无摘要；请阅读原文。')}</p>
  <div class="links">
    <a href="{_esc(original)}" rel="noopener noreferrer" target="_blank">阅读原文</a>
  </div>
</article>
<p class="note">本页为聚合摘要，不构成法律意见。涉及条文、判决或监管口径，请以原文为准。</p>
"""
    return layout(f"{row['title']} · LawHOT", body, description=(row["summary"] or "")[:160])


def render_skill_index() -> str:
    body = f"""
<header class="hero">
  <h1 class="brand">Law<span>HOT</span> Skill</h1>
  <p class="tagline">给 Agent 用的安装包说明。人类读者可先回<a href="{_esc(PUBLIC_BASE_URL)}/">精选首页</a>浏览资讯。</p>
</header>
<article class="item">
  <p class="summary">把下面的地址发给支持 Agent Skills 的工具（Cursor / Claude Code / Codex 等）：</p>
  <p><code>{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md</code></p>
  <div class="links">
    <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md">打开 SKILL.md</a>
    <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/references/api.md">API 参考</a>
    <a href="{_esc(PUBLIC_BASE_URL)}/">返回资讯首页</a>
  </div>
</article>
"""
    return layout("LawHOT Skill", body)
