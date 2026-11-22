#!/usr/bin/env python3
"""Rebuild index.html and archive.html from reports/ai-news-YYYY-MM-DD.html."""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent
REPORTS_DIR = SITE_ROOT / "reports"
INDEX_PATH = SITE_ROOT / "index.html"
ARCHIVE_PATH = SITE_ROOT / "archive.html"

NAME_RE = re.compile(r"^ai-news-(\d{4}-\d{2}-\d{2})\.html$")
JSON_RE = re.compile(
    r'<script type="application/json" id="report-data">(.*?)</script>',
    re.S,
)

MARKER_START = "<!-- site-archive-nav -->"
MARKER_END = "<!-- /site-archive-nav -->"

NAV_SNIPPET = f"""{MARKER_START}
  <style id="site-archive-nav-css">
    .site-archive-nav {{
      max-width: var(--shell, 1440px);
      margin: -1.6rem auto 0;
      padding: 0 max(var(--pad, 1.15rem), env(safe-area-inset-right, 0px), env(safe-area-inset-left, 0px)) 2.75rem;
      text-align: center;
      color: var(--muted, #5a6280);
      font-size: 0.92rem;
    }}
    .site-archive-nav a {{
      color: var(--accent, #2a46d6);
      font-weight: 600;
      text-decoration: none;
      border-bottom: 1px solid color-mix(in srgb, var(--accent, #2a46d6) 40%, transparent);
    }}
    .site-archive-nav a:hover {{
      text-decoration: underline;
      text-underline-offset: 0.16em;
    }}
    @media print {{ .site-archive-nav {{ display: none !important; }} }}
  </style>
  <footer class="site-archive-nav">
    <a href="archive.html">كل التقارير السابقة</a>
  </footer>
{MARKER_END}
"""


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def excerpt(s: str, limit: int = 180) -> str:
    s = strip_tags(s)
    if len(s) <= limit:
        return s
    cut = s[: limit + 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip("،,;:. ") + "…"


def read_meta(path: Path) -> dict:
    m = NAME_RE.match(path.name)
    iso = m.group(1) if m else ""
    meta = {
        "iso": iso,
        "file": path.name,
        "href": f"reports/{path.name}",
        "title": "تقرير أخبار الـAI",
        "date": iso,
        "day": iso[-2:] if iso else "",
        "monthShort": "",
        "intro": "",
    }
    text = path.read_text(encoding="utf-8")
    jm = JSON_RE.search(text)
    if not jm:
        return meta
    try:
        data = json.loads(jm.group(1))
    except json.JSONDecodeError:
        return meta
    meta["title"] = data.get("pageTitle") or data.get("title") or meta["title"]
    meta["date"] = data.get("date") or meta["date"]
    meta["day"] = str(data.get("day") or meta["day"])
    meta["monthShort"] = data.get("monthShort") or meta["monthShort"]
    meta["intro"] = excerpt(data.get("introHtml") or "")
    return meta


def list_reports() -> list[dict]:
    items = []
    for path in REPORTS_DIR.glob("ai-news-20*.html"):
        if NAME_RE.match(path.name):
            items.append(read_meta(path))
    items.sort(key=lambda r: r["iso"], reverse=True)
    return items


def inject_archive_link(page: str) -> str:
    if MARKER_START in page:
        page = re.sub(
            r"\s*" + re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
            "",
            page,
            count=1,
            flags=re.S,
        )
    needle = '<div id="app"></div>'
    if needle not in page:
        print("warning: #app not found; skipping archive link injection", file=sys.stderr)
        return page
    return page.replace(needle, needle + "\n" + NAV_SNIPPET, 1)


def write_index(latest_path: Path) -> None:
    html_text = latest_path.read_text(encoding="utf-8")
    INDEX_PATH.write_text(inject_archive_link(html_text), encoding="utf-8")


def arabic_count_label(count: int) -> str:
    if count == 0:
        return "ما فيش تقارير لسه."
    if count == 1:
        return "تقرير واحد"
    if count == 2:
        return "تقريران"
    if 3 <= count <= 10:
        return f"{count} تقارير"
    return f"{count} تقرير"


def render_archive(reports: list[dict]) -> str:
    latest = reports[0] if reports else None
    stamp_day = latest["day"] if latest else ""
    stamp_mon = latest["monthShort"] if latest else ""
    count_label = arabic_count_label(len(reports))

    cards = []
    for i, r in enumerate(reports):
        badge = '<span class="badge-latest">الأحدث</span>' if i == 0 else ""
        title = html.escape(r["title"])
        date = html.escape(r["date"])
        day = html.escape(r["day"])
        mon = html.escape(r["monthShort"])
        intro = html.escape(r["intro"])
        href = html.escape(r["href"], quote=True)
        intro_html = f'<p class="summary">{intro}</p>' if intro else ""
        cards.append(
            f"""    <a class="card" href="{href}">
      <div class="stamp" aria-hidden="true"><span class="day">{day}</span><span class="mon">{mon}</span></div>
      <div class="card-body">
        {badge}
        <h2>{title}</h2>
        <p class="date">{date}</p>
        {intro_html}
        <span class="open">افتح التقرير</span>
      </div>
    </a>"""
        )

    cards_html = "\n".join(cards) if cards else '    <p class="empty">ما فيش تقارير لسه.</p>'

    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>أرشيف تقارير أخبار الـAI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
:root {{
  --paper: #f1f3f8;
  --surface: #ffffff;
  --ink: #14182a;
  --muted: #5a6280;
  --line: #d5dae8;
  --accent: #2a46d6;
  --accent-soft: #e8ecff;
  --rose: #c43c6a;
  --rose-soft: #fdeef3;
  --shadow: 0 10px 28px rgba(20, 24, 42, 0.07);
  --radius: 18px;
  --focus: 0 0 0 2px var(--paper), 0 0 0 4px var(--accent);
  --font: "IBM Plex Sans Arabic", "Segoe UI", Tahoma, Arial, sans-serif;
  --shell: 1440px;
  --pad: 1.15rem;
}}
html[data-theme="dark"] {{
  color-scheme: dark;
  --paper: #0c1020;
  --surface: #161b2e;
  --ink: #e8ebf6;
  --muted: #9aa3bb;
  --line: #2b3150;
  --accent: #8aa2ff;
  --accent-soft: #1c2450;
  --rose: #f081a3;
  --rose-soft: #3a1b2a;
  --shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
  --focus: 0 0 0 2px var(--paper), 0 0 0 4px var(--accent);
}}
html[data-theme="light"] {{ color-scheme: light; }}
@media (prefers-color-scheme: dark) {{
  html:not([data-theme="light"]) {{
    color-scheme: dark;
    --paper: #0c1020;
    --surface: #161b2e;
    --ink: #e8ebf6;
    --muted: #9aa3bb;
    --line: #2b3150;
    --accent: #8aa2ff;
    --accent-soft: #1c2450;
    --rose: #f081a3;
    --rose-soft: #3a1b2a;
    --shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
    --focus: 0 0 0 2px var(--paper), 0 0 0 4px var(--accent);
  }}
}}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }}
body {{
  margin: 0;
  background:
    radial-gradient(1400px 520px at 100% -12%, rgba(42, 70, 214, 0.10), transparent 58%),
    radial-gradient(900px 380px at 0% 8%, rgba(196, 60, 106, 0.05), transparent 50%),
    var(--paper);
  color: var(--ink);
  font-family: var(--font);
  font-size: 17.5px;
  line-height: 1.85;
  touch-action: manipulation;
}}
.skip {{
  position: absolute;
  right: 1rem;
  top: -3.5rem;
  background: var(--accent);
  color: #fff;
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  z-index: 100;
  text-decoration: none;
}}
.skip:focus {{ top: 0.6rem; }}
.shell {{
  width: 100%;
  max-width: var(--shell);
  margin: 0 auto;
  padding: 1.15rem var(--pad) 4rem;
  padding-inline: max(var(--pad), env(safe-area-inset-right, 0px), env(safe-area-inset-left, 0px));
}}
.hero {{
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  grid-template-areas:
    "stamp copy theme"
    "intro intro intro";
  gap: 0.85rem 1.1rem;
  align-items: start;
  margin-bottom: 1.75rem;
}}
.hero-copy {{ grid-area: copy; min-width: 0; }}
.stamp {{ grid-area: stamp; }}
.icon-btn {{ grid-area: theme; justify-self: end; }}
.intro {{ grid-area: intro; }}
.stamp {{
  background: var(--ink);
  color: var(--paper);
  border-radius: 16px;
  min-width: 4.7rem;
  padding: 0.65rem 0.7rem 0.55rem;
  text-align: center;
  line-height: 1.15;
}}
.stamp .day {{
  font-size: 1.9rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  display: block;
}}
.stamp .mon {{
  font-size: 0.8rem;
  opacity: 0.86;
  display: block;
  margin-top: 0.15rem;
}}
.hero-copy h1 {{
  margin: 0;
  font-size: clamp(1.55rem, 3.2vw, 2.15rem);
  line-height: 1.3;
  font-weight: 700;
  text-wrap: balance;
}}
.hero-copy .date {{
  margin: 0.2rem 0 0;
  color: var(--muted);
  font-size: 0.95rem;
}}
.intro {{
  margin: 0;
  max-width: 46rem;
}}
.intro a {{
  color: var(--accent);
  font-weight: 600;
  text-decoration: none;
  border-bottom: 1px solid color-mix(in srgb, var(--accent) 40%, transparent);
}}
.intro a:hover {{
  text-decoration: underline;
  text-underline-offset: 0.16em;
}}
.icon-btn {{
  appearance: none;
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--ink);
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow);
}}
.icon-btn:hover {{ border-color: var(--accent); }}
.icon-btn:focus-visible,
a:focus-visible {{
  outline: none;
  box-shadow: var(--focus);
}}
.icon-btn svg {{
  width: 1.15rem;
  height: 1.15rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}}
.kicker {{
  margin: 0 0 0.85rem;
  font-size: 1.15rem;
  font-weight: 700;
}}
.archive-list {{
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.9rem;
}}
.card {{
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 1rem 1.1rem 0.95rem;
  box-shadow: var(--shadow);
  text-decoration: none;
  color: inherit;
  min-width: 0;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.card::before {{
  content: "";
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  width: 5px;
  background: var(--rose);
}}
.card:hover {{
  transform: translateY(-3px);
  box-shadow: 0 14px 32px rgba(20, 24, 42, 0.10);
}}
.card .stamp {{
  flex: 0 0 auto;
  margin-inline-start: 0.2rem;
}}
.card-body {{ min-width: 0; flex: 1; }}
.card h2 {{
  margin: 0;
  font-size: 1.08rem;
  line-height: 1.5;
  font-weight: 700;
  text-wrap: pretty;
}}
.card .date {{
  margin: 0.15rem 0 0;
  color: var(--muted);
  font-size: 0.92rem;
}}
.card .summary {{
  margin: 0.45rem 0 0;
  color: var(--ink);
}}
.open {{
  display: inline-block;
  margin-top: 0.65rem;
  color: var(--accent);
  font-weight: 600;
  font-size: 0.95rem;
}}
.badge-latest {{
  display: inline-flex;
  align-items: center;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1.45;
  padding: 0.12rem 0.55rem;
  border-radius: 999px;
  background: var(--rose-soft);
  color: var(--rose);
  margin-bottom: 0.4rem;
}}
.empty {{ color: var(--muted); }}
.site-foot {{
  margin-top: 2.5rem;
  color: var(--muted);
  font-size: 0.88rem;
}}
@media (min-width: 768px) {{
  .shell {{ padding-inline: 1.6rem; }}
  .archive-list {{ grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); }}
}}
@media (min-width: 1024px) {{
  .shell {{ padding-inline: 2rem; }}
  .hero {{
    grid-template-columns: minmax(0, 1fr) auto auto;
    grid-template-areas:
      "copy stamp theme"
      "intro intro intro";
  }}
}}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
  .card {{ transition: none; }}
  .card:hover {{ transform: none; }}
}}
  </style>
</head>
<body>
  <a class="skip" href="#list">تخطي إلى القائمة</a>
  <div class="shell">
    <header class="hero">
      <div class="stamp" aria-hidden="true"><span class="day">{html.escape(stamp_day)}</span><span class="mon">{html.escape(stamp_mon)}</span></div>
      <div class="hero-copy">
        <h1>أرشيف تقارير أخبار الـAI</h1>
        <p class="date">{html.escape(count_label)}</p>
      </div>
      <button class="icon-btn" type="button" id="theme-toggle" aria-label="تغيير المظهر"></button>
      <p class="intro">كل التقارير اليومية في مكان واحد. التقرير الأحدث ظاهر كمان على <a href="./">الصفحة الرئيسية</a>، ومن هنا تقدر ترجع لأي يوم سبق.</p>
    </header>
    <h2 class="kicker" id="list">التقارير</h2>
    <div class="archive-list">
{cards_html}
    </div>
    <p class="site-foot">يتحدّث الأرشيف تلقائيًا مع كل تقرير جديد.</p>
  </div>
  <script>
(function () {{
  "use strict";
  var THEME_KEY = "ai-news-theme";
  var THEMES = ["system", "light", "dark"];
  var LABELS = {{ system: "المظهر: تلقائي", light: "المظهر: فاتح", dark: "المظهر: داكن" }};
  function icon(t) {{
    if (t === "dark") return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 14.3A8.5 8.5 0 1 1 9.7 3 7 7 0 0 0 21 14.3z"/></svg>';
    if (t === "light") return '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M5 12H3M21 12h-2M6.2 6.2 7.6 7.6M16.4 16.4l1.4 1.4M17.8 6.2 16.4 7.6M7.6 16.4 6.2 17.8"/></svg>';
    return '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 3v18"/></svg>';
  }}
  function getTheme() {{
    var t = "system";
    try {{ t = localStorage.getItem(THEME_KEY) || "system"; }} catch (e) {{}}
    return THEMES.indexOf(t) >= 0 ? t : "system";
  }}
  function applyTheme(t) {{
    if (t === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", t);
    try {{ localStorage.setItem(THEME_KEY, t); }} catch (e) {{}}
    var btn = document.getElementById("theme-toggle");
    if (btn) {{
      btn.innerHTML = icon(t);
      btn.setAttribute("aria-label", LABELS[t] || "تغيير المظهر");
    }}
  }}
  var btn = document.getElementById("theme-toggle");
  applyTheme(getTheme());
  if (btn) {{
    btn.addEventListener("click", function () {{
      var cur = getTheme();
      applyTheme(THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length]);
    }});
  }}
}})();
  </script>
</body>
</html>
"""


def main() -> int:
    reports = list_reports()
    if not reports:
        print("error: no reports found under reports/", file=sys.stderr)
        return 1
    latest = REPORTS_DIR / reports[0]["file"]
    write_index(latest)
    ARCHIVE_PATH.write_text(render_archive(reports), encoding="utf-8")
    print(f"index.html <- {latest.name}")
    print(f"archive.html <- {len(reports)} report(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
