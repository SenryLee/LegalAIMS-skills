from __future__ import annotations

import html
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .config import PUBLIC_BASE_URL

SHANGHAI = ZoneInfo("Asia/Shanghai")

CAT_LABEL = {
    "regulation": "监管重点",
    "litigation": "诉讼案例",
    "legaltech": "法律科技",
    "practice": "实务·融资",
    "insight": "行业启迪",
    "vendor": "厂商动态",
}

CAT_BLURB = {
    "regulation": "少而精的规则与立法",
    "litigation": "涉 AI 争议与判例",
    "legaltech": "产品、工具与行业技术",
    "practice": "律所落地与融资动态",
    "insight": "方法与行业思考",
    "vendor": "影响法律业的厂商信号",
}


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _bj_time(iso: str | None) -> str:
    if not iso:
        return "时间未知"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(SHANGHAI)
        return dt.strftime("%Y年%m月%d日 %H:%M")
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
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;0,7..72,700;1,7..72,400&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet" />
  <style>
    :root {{
      --ink: #221c16;
      --ink-soft: #3d342b;
      --muted: #6d6256;
      --paper: #f4efe4;
      --paper-2: #ebe4d4;
      --leaf: #fffaf0;
      --rule: #c9bba5;
      --rule-soft: #ddd2bf;
      --accent: #6b2d2d;
      --accent-2: #245c48;
      --shadow: 0 1px 0 rgba(34,28,22,.04), 0 22px 50px rgba(55,40,20,.08);
      --serif: "Source Serif 4", "Literata", "Songti SC", "Noto Serif SC", "Source Han Serif SC", serif;
      --sans: "Source Han Sans SC", "PingFang SC", "Noto Sans SC", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: var(--serif);
      line-height: 1.8;
      background-color: #cfc3ab;
      background-image:
        radial-gradient(ellipse at 20% 10%, rgba(255,248,230,.55) 0%, transparent 42%),
        radial-gradient(ellipse at 80% 90%, rgba(90,70,40,.08) 0%, transparent 45%),
        url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.07'/%3E%3C/svg%3E"),
        linear-gradient(165deg, #e4d9c4 0%, #d2c4ab 48%, #c7b89d 100%);
    }}
    a {{ color: var(--accent-2); text-decoration-thickness: 1px; text-underline-offset: 3px; }}
    a:hover {{ color: var(--accent); }}
    .stage {{
      width: min(780px, calc(100% - 1.5rem));
      margin: 1.75rem auto 3.5rem;
      background:
        linear-gradient(90deg, rgba(70,50,30,.12) 0, rgba 14px, transparent 36px),
        linear-gradient(90deg, transparent calc(100% - 10px), rgba(70,50,30,.04)),
        linear-gradient(180deg, #fffdf6 0%, var(--leaf) 8%, var(--paper) 55%, var(--paper-2) 100%);
      border: 1px solid #b09e82;
      border-radius: 2px 6px 6px 2px;
      box-shadow:
        -8px 0 0 #a89274,
        -9px 0 0 #8f7a5c,
        var(--shadow),
        inset 0 0 0 1px rgba(255,250,240,.7);
      position: relative;
    }}
    .stage::before {{
      content: "";
      position: absolute; inset: 12px 14px 14px 18px;
      border: 1px solid var(--rule-soft);
      pointer-events: none;
    }}
    .stage::after {{
      content: "";
      position: absolute;
      left: 0; top: 8%; bottom: 8%;
      width: 3px;
      background: linear-gradient(180deg, transparent, rgba(107,45,45,.35), transparent);
      pointer-events: none;
    }}
    .inner {{ position: relative; z-index: 1; padding: clamp(1.55rem, 4.2vw, 2.75rem) clamp(1.4rem, 4vw, 2.5rem); }}
    .brand-row {{
      display: flex; justify-content: space-between; align-items: baseline;
      gap: 1rem; flex-wrap: wrap;
      border-bottom: 2px solid var(--ink);
      padding-bottom: 0.85rem; margin-bottom: 0.85rem;
    }}
    .brand {{
      margin: 0;
      font-size: clamp(2.3rem, 7vw, 3.4rem);
      letter-spacing: 0.04em;
      line-height: 1;
      font-weight: 700;
    }}
    .brand em {{ font-style: normal; color: var(--accent); }}
    .volume {{
      font-family: var(--sans);
      font-size: 0.78rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .tagline {{
      margin: 0 0 1.25rem;
      color: var(--ink-soft);
      font-size: 1.05rem;
      max-width: 34em;
    }}
    .cats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.65rem;
      margin: 0 0 1.6rem;
    }}
    @media (max-width: 720px) {{
      .cats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    .cat {{
      display: block;
      text-decoration: none;
      color: inherit;
      background:
        linear-gradient(180deg, rgba(255,252,245,.95), rgba(244,239,228,.88));
      border: 1px solid var(--rule);
      padding: 0.7rem 0.75rem 0.75rem;
      min-height: 4.6rem;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.55);
      transition: background .18s ease, border-color .18s ease, transform .18s ease, box-shadow .18s ease;
    }}
    .cat:hover {{
      background: #fffef8;
      border-color: var(--accent);
      transform: translateY(-2px);
      box-shadow: 0 6px 14px rgba(55,40,20,.08);
    }}
    .cat.active {{
      background: #fffef8;
      border-color: var(--ink);
      box-shadow: inset 0 -3px 0 var(--accent);
    }}
    @media (prefers-reduced-motion: reduce) {{
      .cat, .cat:hover {{ transition: none; transform: none; }}
    }}
    .cat strong {{
      display: block;
      font-size: 1rem;
      margin-bottom: 0.15rem;
    }}
    .cat span {{
      display: block;
      font-family: var(--sans);
      font-size: 0.78rem;
      color: var(--muted);
      line-height: 1.35;
    }}
    .cat b {{
      font-family: var(--sans);
      font-weight: 600;
      color: var(--accent);
      font-size: 0.78rem;
    }}
    .section-label {{
      font-family: var(--sans);
      font-size: 0.8rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      border-top: 1px solid var(--rule);
      border-bottom: 1px solid var(--rule);
      padding: 0.45rem 0;
      margin: 0 0 1.1rem;
    }}
    .item {{
      padding: 1.15rem 0 1.25rem;
      border-bottom: 1px solid var(--rule-soft);
    }}
    .item:last-child {{ border-bottom: 0; }}
    .item h2 {{
      margin: 0 0 0.45rem;
      font-size: clamp(1.2rem, 3.2vw, 1.45rem);
      line-height: 1.35;
      font-weight: 650;
    }}
    .item h2 a {{ color: inherit; text-decoration: none; }}
    .item h2 a:hover {{ color: var(--accent); }}
    .meta {{
      display: flex; flex-wrap: wrap; gap: 0.35rem 0.85rem;
      font-family: var(--sans);
      font-size: 0.8rem;
      color: var(--muted);
      margin-bottom: 0.5rem;
    }}
    .chip {{
      color: var(--accent);
      border: 1px solid var(--rule);
      padding: 0 0.4rem;
      background: rgba(255,250,240,.9);
    }}
    .summary {{
      margin: 0;
      color: var(--ink-soft);
      font-size: 1.02rem;
    }}
    .orig {{
      margin: 0.35rem 0 0;
      font-family: var(--sans);
      font-size: 0.82rem;
      color: var(--muted);
      font-style: italic;
    }}
    .links {{
      margin-top: 0.7rem;
      font-family: var(--sans);
      font-size: 0.88rem;
      display: flex; gap: 1rem; flex-wrap: wrap;
    }}
    footer.book-foot {{
      margin-top: 2rem;
      padding-top: 0.9rem;
      border-top: 2px solid var(--ink);
      font-family: var(--sans);
      font-size: 0.82rem;
      color: var(--muted);
    }}
    .back {{ font-family: var(--sans); display: inline-block; margin-bottom: 1rem; }}
    .note {{
      font-family: var(--sans);
      font-size: 0.86rem;
      color: var(--muted);
      margin: 0 0 1rem;
    }}
  </style>
</head>
<body>
  <div class="stage"><div class="inner">
    {body}
    <footer class="book-foot">
      <p>LawHOT · 法锤法律 AI 读本。资讯聚合，非法律意见；重要引用请回原文核对。</p>
      <p>
        <a href="{_esc(PUBLIC_BASE_URL)}/feed.xml">RSS</a> ·
        <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md">Agent Skill</a> ·
        <a href="{_esc(PUBLIC_BASE_URL)}/api/v1/items?mode=selected&amp;window=24h&amp;limit=10">JSON API</a>
      </p>
    </footer>
  </div></div>
</body>
</html>"""


def _cat_cards(active: str | None, counts: dict[str, int]) -> str:
    cards = []
    # 全部
    total = sum(counts.values())
    all_active = " active" if not active else ""
    cards.append(
        f'<a class="cat{all_active}" href="{_esc(PUBLIC_BASE_URL)}/">'
        f"<strong>全部精选</strong><span>按阅读优先级编排</span>"
        f"<b>{total} 篇</b></a>"
    )
    # 展示顺序：科技/融资优先，监管靠后
    order = ("legaltech", "practice", "litigation", "insight", "vendor", "regulation")
    for key in order:
        cls = " active" if active == key else ""
        n = counts.get(key, 0)
        cards.append(
            f'<a class="cat{cls}" href="{_esc(PUBLIC_BASE_URL)}/?category={_esc(key)}">'
            f"<strong>{_esc(CAT_LABEL.get(key, key))}</strong>"
            f"<span>{_esc(CAT_BLURB.get(key, ''))}</span>"
            f"<b>{n} 篇</b></a>"
        )
    return f'<div class="cats" aria-label="分类导航">{"".join(cards)}</div>'


def render_home(
    items: list[Any],
    stats: dict[str, Any],
    *,
    category: str | None = None,
    counts: dict[str, int] | None = None,
    edition: dict[str, Any] | None = None,
) -> str:
    counts = counts or {}
    edition = edition or {}
    ed_counts = edition.get("counts") or {}
    cards = []
    for r in items:
        cat = CAT_LABEL.get(r["category"] or "", r["category"] or "未分类")
        lawhot = f"{PUBLIC_BASE_URL}/items/{r['id']}"
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
        cards.append(
            f"""
<article class="item">
  <h2><a href="{_esc(lawhot)}">{_esc(r['title'])}</a></h2>
  <div class="meta">
    <span class="chip">{_esc(cat)}</span>
    <span>{_esc(r['source_name'])}</span>
    <span>{_esc(_bj_time(r['published_at'] or r['discovered_at']))}</span>
  </div>
  <p class="summary">{_esc(r['summary'] or '暂无摘要')}</p>
  {orig_block}
  <div class="links">
    <a href="{_esc(lawhot)}">读本页</a>
    <a href="{_esc(original)}" rel="noopener noreferrer" target="_blank">原文链接</a>
  </div>
</article>"""
        )
    if not cards:
        cards.append('<p class="note">此分类暂无条目。可切换其他分类，或稍后再来。</p>')

    active_label = CAT_LABEL.get(category or "", "今日读本")
    ed_date = edition.get("date") or ""
    zh_n = int(ed_counts.get("zh") or 0)
    en_n = int(ed_counts.get("en") or 0)
    total_n = int(ed_counts.get("total") or len(items))
    lead = edition.get("lead") or (
        "每日固定刊：中文最多 10、英文最多 5；监管至多 1 条。偏重法律科技与实务。"
    )
    body = f"""
<div class="brand-row">
  <h1 class="brand">Law<em>HOT</em></h1>
  <div class="volume">Legal AI Reader · 法锤读本</div>
</div>
<p class="tagline">{_esc(lead)}</p>
{_cat_cards(category, counts)}
<div class="section-label">今日读本 · {_esc(ed_date)} · {_esc(active_label)} · 中文 {zh_n} / 英文 {en_n} · 共 {total_n} 篇</div>
{''.join(cards)}
"""
    return layout("LawHOT · 法律 AI 每日读本", body)


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
<p class="back"><a href="{_esc(PUBLIC_BASE_URL)}/">← 返回读本目录</a></p>
<div class="brand-row">
  <h1 class="brand" style="font-size:clamp(1.5rem,4vw,2.1rem)">{_esc(row['title'])}</h1>
</div>
<div class="meta" style="margin:0.2rem 0 1rem">
  <span class="chip">{_esc(cat)}</span>
  <span>{_esc(row['source_name'])}</span>
  <span>发布 {_esc(_bj_time(row['published_at']))}</span>
  <span>收录 {_esc(_bj_time(row['discovered_at']))}</span>
</div>
<p class="summary">{_esc(row['summary'] or '暂无摘要；请阅读原文。')}</p>
{orig_block}
<div class="links">
  <a href="{_esc(original)}" rel="noopener noreferrer" target="_blank">打开原文</a>
</div>
<p class="note">本页为中文读本摘要，不构成法律意见。条文、判决与监管口径以原文为准。</p>
"""
    return layout(f"{row['title']} · LawHOT", body, description=(row["summary"] or "")[:160])


def render_skill_index() -> str:
    body = f"""
<div class="brand-row">
  <h1 class="brand">Law<em>HOT</em> Skill</h1>
  <div class="volume">For Agents</div>
</div>
<p class="tagline">给 Agent 安装的说明书。人类读者请先回<a href="{_esc(PUBLIC_BASE_URL)}/">读本首页</a>。</p>
<article class="item">
  <p class="summary">把下面的地址发给 Cursor / Claude Code / Codex 等支持 Agent Skills 的工具：</p>
  <p><code>{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md</code></p>
  <div class="links">
    <a href="{_esc(PUBLIC_BASE_URL)}/lawhot-skill/SKILL.md">打开 SKILL.md</a>
    <a href="{_esc(PUBLIC_BASE_URL)}/">返回读本</a>
  </div>
</article>
"""
    return layout("LawHOT Skill", body)
