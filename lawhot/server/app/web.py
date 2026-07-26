from __future__ import annotations

import html
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .config import PUBLIC_BASE_URL

SHANGHAI = ZoneInfo("Asia/Shanghai")

BRAND = "Legal Bulletins"
BRAND_SUB = "法律 AI 每日读本"
TAGLINE = "法律科技频道：产品、融资与实务优先；监管只留最重要的一条。每日中文最多 10、英文最多 5。"

CAT_LABEL = {
    "regulation": "监管",
    "litigation": "诉讼",
    "legaltech": "法律科技",
    "practice": "实务",
    "insight": "启迪",
    "vendor": "厂商",
}

CAT_BLURB = {
    "regulation": "少而精的规则与立法",
    "litigation": "涉 AI 争议与判例",
    "legaltech": "产品、工具与行业技术",
    "practice": "律所落地与融资动态",
    "insight": "方法与行业思考",
    "vendor": "影响法律业的厂商信号",
}

# 顶栏主分类（与 mockup 一致；其余仍可通过 URL 进入）
NAV_ORDER = ("legaltech", "practice", "litigation", "insight", "vendor", "regulation")


def _esc(s: Any) -> str:
    # 先反转义，避免原文标题出现 Plaintiffs&#39; 这类实体
    raw = html.unescape("" if s is None else str(s))
    return html.escape(raw, quote=True)


def _bj_time(iso: str | None) -> str:
    if not iso:
        return "时间未知"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(SHANGHAI)
        return dt.strftime("%Y年%m月%d日 %H:%M")
    except Exception:
        return iso


def _bj_parts(iso: str | None) -> tuple[str, str, str]:
    if not iso:
        return ("—", "—", "—")
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(SHANGHAI)
        return (dt.strftime("%Y"), dt.strftime("%m"), dt.strftime("%d"))
    except Exception:
        return ("—", "—", "—")


def layout(title: str, body: str, *, description: str = "", page: str = "inner") -> str:
    desc = description or "全球法律 AI 资讯 · AI 对法律行业的启迪"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <meta name="description" content="{_esc(desc)}" />
  <link rel="alternate" type="application/rss+xml" title="{_esc(BRAND)} 精选" href="{_esc(PUBLIC_BASE_URL)}/feed.xml" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --ink: #1a1a1a;
      --ink-soft: #3a3834;
      --muted: #7a756c;
      --ivory: #f7f5f0;
      --ivory-2: #f0eee6;
      --surface: #fffcf7;
      --metal-1: #6f6b64;
      --metal-2: #a8a49c;
      --metal-3: #d8d4cc;
      --metal-4: #f5f3ee;
      --metal-5: #ebe7df;
      --rule: rgba(111,107,100,.28);
      --serif-display: "Cormorant Garamond", "Songti SC", "Noto Serif SC", serif;
      --serif: "Newsreader", "Source Han Serif SC", "Songti SC", serif;
      --sans: "DM Sans", "PingFang SC", "Source Han Sans SC", "Noto Sans SC", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: var(--sans);
      line-height: 1.65;
      background-color: var(--ivory);
      background-image:
        radial-gradient(ellipse 55% 40% at 78% 18%, rgba(180,190,170,.18) 0%, transparent 70%),
        radial-gradient(ellipse 50% 35% at 12% 0%, rgba(255,255,255,.7) 0%, transparent 55%),
        linear-gradient(165deg, var(--ivory) 0%, var(--ivory-2) 55%, #e8e4da 100%);
      -webkit-font-smoothing: antialiased;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .035;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
      z-index: 0;
    }}
    a {{ color: var(--ink-soft); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    a:hover {{ color: var(--ink); }}
    .shell {{
      position: relative;
      z-index: 1;
      width: min(920px, calc(100% - 2rem));
      margin: 0 auto;
      padding: 1.25rem 0 4rem;
    }}
    .topnav {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
      padding: 0.35rem 0 1rem;
      border-bottom: 1px solid transparent;
      border-image: linear-gradient(90deg, transparent, var(--metal-2) 12%, var(--metal-4) 48%, #fff 50%, var(--metal-3) 58%, var(--metal-1) 88%, transparent) 1;
      margin-bottom: 2.5rem;
      animation: fade-down .7s ease both;
    }}
    .nav-brand {{
      font-family: var(--serif-display);
      font-size: 1.15rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      text-decoration: none;
      color: #5c5852;
      background: linear-gradient(115deg, #5c5852 0%, #b8b4ac 28%, #f5f3ee 48%, #9e9a92 68%, #6f6b64 100%);
      background-size: 200% 100%;
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: metal-sweep 7s ease-in-out infinite;
    }}
    @supports not ((-webkit-background-clip: text) or (background-clip: text)) {{
      .nav-brand {{ color: #3a3834; -webkit-text-fill-color: #3a3834; }}
    }}
    .nav-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem 1.15rem;
      font-size: 0.86rem;
      font-weight: 500;
      letter-spacing: 0.04em;
    }}
    .nav-links a {{
      color: var(--muted);
      text-decoration: none;
      position: relative;
      padding: 0.2rem 0;
    }}
    .nav-links a:hover {{ color: var(--ink); }}
    .nav-links a.active {{
      color: var(--ink);
    }}
    .nav-links a.active::after {{
      content: "";
      position: absolute;
      left: 0; right: 0; bottom: -0.35rem;
      height: 2px;
      background: linear-gradient(90deg, var(--metal-1), var(--metal-4), #fff, var(--metal-3), var(--metal-1));
      box-shadow: 0 0 6px rgba(255,255,255,.45);
    }}
    .hero {{
      position: relative;
      padding: 1.5rem 0 3.25rem;
      margin-bottom: 0.5rem;
      overflow: hidden;
      animation: fade-up .85s ease .08s both;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      right: -8%;
      top: -10%;
      width: min(420px, 55vw);
      height: min(420px, 55vw);
      background:
        radial-gradient(ellipse at 40% 45%, rgba(90,110,80,.12) 0%, transparent 62%),
        radial-gradient(ellipse at 60% 60%, rgba(40,50,35,.08) 0%, transparent 55%);
      -webkit-mask-image: radial-gradient(ellipse at 50% 50%, #000 20%, transparent 72%);
      mask-image: radial-gradient(ellipse at 50% 50%, #000 20%, transparent 72%);
      pointer-events: none;
      filter: blur(2px);
      opacity: .9;
    }}
    .brand-wrap {{
      display: inline-block;
      margin: 0 0 0.85rem;
      filter: drop-shadow(0 1px 0 rgba(255,255,255,.4)) drop-shadow(0 12px 30px rgba(40,35,25,.1));
    }}
    .brand {{
      margin: 0;
      font-family: var(--serif-display);
      font-size: clamp(3.2rem, 9vw, 5.6rem);
      font-weight: 600;
      line-height: 0.95;
      letter-spacing: -0.02em;
      color: #3a3834; /* fallback if clip unsupported */
      background: linear-gradient(
        110deg,
        #5c5852 0%,
        #9e9a92 14%,
        #e8e4dc 28%,
        #fff 36%,
        #b8b4ac 48%,
        #f0ece4 62%,
        #8a8680 78%,
        #d4d0c8 100%
      );
      background-size: 220% 100%;
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: metal-sweep 8s ease-in-out infinite;
    }}
    @supports not ((-webkit-background-clip: text) or (background-clip: text)) {{
      .brand {{ color: #1a1a1a; -webkit-text-fill-color: #1a1a1a; }}
    }}
    .brand-sub {{
      margin: 0 0 1rem;
      font-family: var(--serif);
      font-size: clamp(1.35rem, 3.2vw, 1.75rem);
      font-weight: 600;
      color: var(--ink);
      letter-spacing: 0.02em;
    }}
    .tagline {{
      margin: 0 0 1.5rem;
      max-width: 34em;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.7;
    }}
    .cta {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.95rem;
      font-weight: 500;
      color: var(--ink);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      border-image: linear-gradient(90deg, var(--metal-1), var(--metal-4), #fff, var(--metal-2)) 1;
      padding-bottom: 0.15rem;
      transition: opacity .2s ease, letter-spacing .25s ease;
    }}
    .cta:hover {{
      opacity: .75;
      letter-spacing: 0.02em;
    }}
    .metal-rule {{
      height: 1px;
      border: 0;
      margin: 0 0 1.75rem;
      background: linear-gradient(
        90deg,
        transparent 0%,
        var(--metal-1) 8%,
        var(--metal-3) 28%,
        #fff 50%,
        var(--metal-3) 72%,
        var(--metal-1) 92%,
        transparent 100%
      );
      box-shadow: 0 0 8px rgba(255,255,255,.35);
      animation: rule-gleam 5.5s ease-in-out infinite;
    }}
    .section-head {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 1rem;
      margin: 0 0 1.25rem;
      animation: fade-up .7s ease .16s both;
    }}
    .section-head h2 {{
      margin: 0;
      font-family: var(--serif);
      font-size: 1.35rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 0.65rem;
    }}
    .section-head h2::before {{
      content: "";
      width: 18px;
      height: 2px;
      background: linear-gradient(90deg, var(--metal-1), var(--metal-4), #fff);
      box-shadow: 0 0 5px rgba(255,255,255,.4);
    }}
    .section-meta {{
      font-size: 0.8rem;
      color: var(--muted);
      letter-spacing: 0.04em;
    }}
    .feed {{ animation: fade-up .75s ease .22s both; }}
    .item {{
      display: grid;
      grid-template-columns: 5.5rem minmax(0, 1fr);
      gap: 1.25rem 1.75rem;
      padding: 1.35rem 0;
      border-bottom: 1px solid transparent;
      border-image: linear-gradient(90deg, transparent, var(--metal-2) 10%, var(--metal-4) 45%, #fff 50%, var(--metal-3) 55%, var(--metal-1) 90%, transparent) 1;
    }}
    .item:last-child {{ border-bottom: 0; border-image: none; }}
    .item-date {{
      font-size: 0.78rem;
      color: var(--muted);
      letter-spacing: 0.06em;
      line-height: 1.45;
      padding-top: 0.2rem;
    }}
    .item-date b {{
      display: block;
      font-weight: 500;
      color: var(--ink-soft);
      font-variant-numeric: tabular-nums;
    }}
    .item-cat {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      margin: 0 0 0.45rem;
      font-size: 0.75rem;
      font-weight: 500;
      letter-spacing: 0.08em;
      color: var(--muted);
      text-transform: none;
    }}
    .item-cat::before {{
      content: "";
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: radial-gradient(circle at 30% 30%, #fff, var(--metal-3) 40%, var(--metal-1));
      box-shadow: 0 0 3px rgba(255,255,255,.5);
    }}
    .item h3 {{
      margin: 0 0 0.4rem;
      font-family: var(--serif);
      font-size: clamp(1.15rem, 2.6vw, 1.4rem);
      font-weight: 600;
      line-height: 1.35;
      letter-spacing: -0.01em;
    }}
    .item h3 a {{
      color: inherit;
      text-decoration: none;
      background-image: linear-gradient(90deg, var(--ink), var(--ink));
      background-size: 0 1px;
      background-position: 0 100%;
      background-repeat: no-repeat;
      transition: background-size .25s ease, color .2s ease;
    }}
    .item h3 a:hover {{
      background-size: 100% 1px;
    }}
    .summary {{
      margin: 0;
      color: var(--muted);
      font-size: 0.95rem;
      line-height: 1.65;
      max-width: 46em;
    }}
    .orig {{
      margin: 0.4rem 0 0;
      font-size: 0.8rem;
      color: var(--muted);
      font-style: italic;
    }}
    .links {{
      margin-top: 0.75rem;
      font-size: 0.86rem;
      display: flex;
      gap: 1.1rem;
      flex-wrap: wrap;
    }}
    .links a {{
      color: var(--ink-soft);
      text-decoration: none;
      border-bottom: 1px solid var(--rule);
    }}
    .links a:hover {{ border-color: var(--ink); }}
    .note {{
      font-size: 0.9rem;
      color: var(--muted);
      margin: 0.5rem 0 1rem;
    }}
    .back {{
      display: inline-block;
      margin-bottom: 1.25rem;
      font-size: 0.9rem;
      color: var(--muted);
      text-decoration: none;
    }}
    .back:hover {{ color: var(--ink); }}
    .detail-title {{
      margin: 0 0 1rem;
      font-family: var(--serif);
      font-size: clamp(1.7rem, 4.5vw, 2.4rem);
      font-weight: 600;
      line-height: 1.25;
      letter-spacing: -0.015em;
    }}
    .detail-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem 1rem;
      font-size: 0.84rem;
      color: var(--muted);
      margin: 0 0 1.25rem;
    }}
    .site-foot {{
      margin-top: 3rem;
      padding-top: 1.25rem;
      border-top: 1px solid transparent;
      border-image: linear-gradient(90deg, transparent, var(--metal-2) 15%, var(--metal-4) 50%, var(--metal-1) 85%, transparent) 1;
      font-size: 0.82rem;
      color: var(--muted);
    }}
    .site-foot p {{ margin: 0.35rem 0; }}
    .site-foot a {{ color: var(--ink-soft); }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.88em;
      background: rgba(255,255,255,.55);
      padding: 0.15rem 0.4rem;
      border: 1px solid var(--rule);
    }}
    @keyframes metal-sweep {{
      0%, 100% {{ background-position: 0% 50%; }}
      50% {{ background-position: 100% 50%; }}
    }}
    @keyframes rule-gleam {{
      0%, 100% {{ opacity: .75; filter: brightness(1); }}
      50% {{ opacity: 1; filter: brightness(1.15); }}
    }}
    @keyframes fade-up {{
      from {{ opacity: 0; transform: translateY(14px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes fade-down {{
      from {{ opacity: 0; transform: translateY(-8px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @media (max-width: 640px) {{
      .shell {{ width: min(100% - 1.5rem, 920px); padding-top: 0.85rem; }}
      .item {{ grid-template-columns: 1fr; gap: 0.35rem; }}
      .item-date {{ display: flex; gap: 0.5rem; align-items: baseline; }}
      .item-date b {{ display: inline; }}
      .hero {{ padding-top: 0.5rem; padding-bottom: 2.25rem; }}
      .topnav {{ margin-bottom: 1.5rem; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      html {{ scroll-behavior: auto; }}
      .brand, .nav-brand, .metal-rule, .topnav, .hero, .section-head, .feed {{
        animation: none !important;
      }}
      .brand, .nav-brand {{ background-position: 40% 50%; }}
    }}
  </style>
</head>
<body data-page="{_esc(page)}">
  <div class="shell">
    {body}
    <footer class="site-foot">
      <p>{_esc(BRAND)} · {_esc(BRAND_SUB)}。资讯聚合，非法律意见；重要引用请回原文核对。</p>
      <p>
        <a href="{_esc(PUBLIC_BASE_URL)}/feed.xml">RSS</a> ·
        <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md">Agent Skill</a> ·
        <a href="{_esc(PUBLIC_BASE_URL)}/api/v1/items?mode=selected&amp;window=24h&amp;limit=10">JSON API</a>
      </p>
    </footer>
  </div>
</body>
</html>"""


def _nav(active: str | None) -> str:
    links = [
        f'<a class="{"active" if not active else ""}" href="{_esc(PUBLIC_BASE_URL)}/">精选</a>'
    ]
    for key in NAV_ORDER:
        cls = "active" if active == key else ""
        links.append(
            f'<a class="{cls}" href="{_esc(PUBLIC_BASE_URL)}/?category={_esc(key)}">'
            f"{_esc(CAT_LABEL.get(key, key))}</a>"
        )
    return f"""
<header class="topnav">
  <a class="nav-brand" href="{_esc(PUBLIC_BASE_URL)}/">{_esc(BRAND)}</a>
  <nav class="nav-links" aria-label="分类导航">{"".join(links)}</nav>
</header>"""


def render_home(
    items: list[Any],
    stats: dict[str, Any],
    *,
    category: str | None = None,
    counts: dict[str, int] | None = None,
    edition: dict[str, Any] | None = None,
) -> str:
    del counts  # 顶栏文本导航，保留参数兼容 main.py
    edition = edition or {}
    ed_counts = edition.get("counts") or {}
    cards = []
    for r in items:
        cat = CAT_LABEL.get(r["category"] or "", r["category"] or "未分类")
        detail = f"{PUBLIC_BASE_URL}/items/{r['id']}"
        original = r["original_url"] or "#"
        orig_title = r["original_title"] or ""
        show_orig = bool(
            orig_title
            and orig_title != r["title"]
            and not _mostly_cjk(orig_title)
        )
        orig_block = (
            f'<p class="orig">原文标题：{_esc(orig_title)}</p>' if show_orig else ""
        )
        y, m, d = _bj_parts(r["published_at"] or r["discovered_at"])
        cards.append(
            f"""
<article class="item">
  <div class="item-date"><b>{_esc(y)} / {_esc(m)} / {_esc(d)}</b></div>
  <div>
    <div class="item-cat">{_esc(cat)}</div>
    <h3><a href="{_esc(detail)}">{_esc(r['title'])}</a></h3>
    <p class="summary">{_esc(r['summary'] or '暂无摘要')}</p>
    {orig_block}
    <div class="links">
      <a href="{_esc(detail)}">读本页</a>
      <a href="{_esc(original)}" rel="noopener noreferrer" target="_blank">原文链接</a>
    </div>
  </div>
</article>"""
        )
    if not cards:
        cards.append('<p class="note">此分类暂无条目。可切换其他分类，或稍后再来。</p>')

    active_label = CAT_LABEL.get(category or "", "精选")
    ed_date = edition.get("date") or ""
    zh_n = int(ed_counts.get("zh") or 0)
    en_n = int(ed_counts.get("en") or 0)
    total_n = int(ed_counts.get("total") or len(items))
    meta = (
        f"{ed_date} · {active_label} · 中文 {zh_n} / 英文 {en_n} · 共 {total_n} 篇"
        if ed_date
        else f"{active_label} · 库内 {int(stats.get('selected') or 0)} 条"
    )
    lead = edition.get("lead") or TAGLINE
    body = f"""
{_nav(category)}
<section class="hero" aria-label="品牌">
  <div class="brand-wrap"><h1 class="brand">{_esc(BRAND)}</h1></div>
  <p class="brand-sub">{_esc(BRAND_SUB)}</p>
  <p class="tagline">{_esc(lead)}</p>
  <a class="cta" href="#feed">开始阅读 →</a>
</section>
<hr class="metal-rule" />
<div class="section-head" id="feed">
  <h2>今日读本</h2>
  <div class="section-meta">{_esc(meta)}</div>
</div>
<div class="feed">
{''.join(cards)}
</div>
"""
    return layout(f"{BRAND} · {BRAND_SUB}", body, page="home")


def _mostly_cjk(text: str) -> bool:
    import re

    if not text:
        return False
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    return cjk >= max(4, int(len(text) * 0.25))


def render_item(row: Any) -> str:
    cat = CAT_LABEL.get(row["category"] or "", row["category"] or "未分类")
    original = row["original_url"] or "#"
    orig_title = row["original_title"] or ""
    show_orig = bool(orig_title and orig_title != row["title"] and not _mostly_cjk(orig_title))
    orig_block = (
        f'<p class="orig">原文标题：{_esc(orig_title)}</p>' if show_orig else ""
    )
    body = f"""
{_nav(row["category"])}
<p class="back"><a href="{_esc(PUBLIC_BASE_URL)}/">← 返回精选</a></p>
<hr class="metal-rule" />
<article>
  <div class="item-cat">{_esc(cat)}</div>
  <h1 class="detail-title">{_esc(row['title'])}</h1>
  <div class="detail-meta">
    <span>{_esc(row['source_name'])}</span>
    <span>发布 {_esc(_bj_time(row['published_at']))}</span>
    <span>收录 {_esc(_bj_time(row['discovered_at']))}</span>
  </div>
  <p class="summary" style="color:var(--ink-soft);font-size:1.05rem">{_esc(row['summary'] or '暂无摘要；请阅读原文。')}</p>
  {orig_block}
  <div class="links">
    <a href="{_esc(original)}" rel="noopener noreferrer" target="_blank">打开原文</a>
  </div>
  <p class="note">本页为中文读本摘要，不构成法律意见。条文、判决与监管口径以原文为准。</p>
</article>
"""
    return layout(
        f"{row['title']} · {BRAND}",
        body,
        description=(row["summary"] or "")[:160],
        page="item",
    )


def render_skill_index() -> str:
    body = f"""
{_nav(None)}
<section class="hero">
  <div class="brand-wrap"><h1 class="brand" style="font-size:clamp(2.4rem,7vw,3.8rem)">{_esc(BRAND)}</h1></div>
  <p class="brand-sub">Agent Skill</p>
  <p class="tagline">给 Agent 安装的说明书。人类读者请先回<a href="{_esc(PUBLIC_BASE_URL)}/">精选首页</a>。</p>
</section>
<hr class="metal-rule" />
<article class="item" style="display:block;border:0">
  <p class="summary" style="color:var(--ink-soft)">把下面的地址发给 Cursor / Claude Code / Codex 等支持 Agent Skills 的工具：</p>
  <p><code>{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md</code></p>
  <div class="links">
    <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md">打开 SKILL.md</a>
    <a href="{_esc(PUBLIC_BASE_URL)}/">返回精选</a>
  </div>
</article>
"""
    return layout(f"{BRAND} Skill", body, page="skill")
