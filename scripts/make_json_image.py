"""Screenshot-style image of one product's reviews in JSON (docs/img/product-json.png), for the README and Kaggle.

    python scripts/make_json_image.py

Takes docs/example-product.json (written by make_json.py), keeps two of its reviews (a 5-star and a 1-star
one, both quoted in the pros and cons) and their main fields, cuts long texts at ~90 characters and lists
at 3 items, highlights it and screenshots it with Playwright.
Needs pygments and playwright (with Chromium: python -m playwright install chromium); they are not in
requirements.txt because CI does not run this script.
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer

ROOT = Path(__file__).resolve().parents[1]
SHOW = (3139068, 3139074)  # review_id of the reviews shown
KEEP = ("rating", "sentiment", "text", "aspects", "clauses")
CUT = 90


def fmt(o, ind: int = 0) -> str:
    """JSON with small flat objects on one line, like a person would write it."""
    sp = "  " * ind
    if isinstance(o, dict):
        flat = json.dumps(o, ensure_ascii=False)
        if all(not isinstance(v, (dict, list)) for v in o.values()) and len(o) <= 4 and len(flat) <= 115:
            return flat
        return "{\n" + ",\n".join(f'{sp}  "{k}": {fmt(v, ind + 1)}' for k, v in o.items()) + f"\n{sp}}}"
    if isinstance(o, list):
        if all(not isinstance(v, (dict, list)) for v in o) and len(json.dumps(o, ensure_ascii=False)) <= 100:
            return json.dumps(o, ensure_ascii=False)
        return "[\n" + ",\n".join(f"{sp}  {fmt(v, ind + 1)}" for v in o) + f"\n{sp}]"
    return json.dumps(o, ensure_ascii=False)


CSS = """
body { margin: 0; background: #fdfdfc; font-family: Inter, 'DejaVu Sans', sans-serif; }
.win { margin: 28px; border-radius: 12px; overflow: hidden; display: inline-block;
       box-shadow: 0 10px 30px rgba(17,17,17,.12), 0 0 0 1px #d9dde3; background: #ffffff; }
.bar { height: 38px; background: #f3f4f6; border-bottom: 1px solid #e5e7eb; display: flex; align-items: center;
       padding: 0 14px; gap: 8px; }
.dot { width: 12px; height: 12px; border-radius: 50%; }
.title { margin-left: 14px; font: 13px 'DejaVu Sans Mono', monospace; color: #555555; }
.code { padding: 16px 26px 20px 0; display: flex; }
.ln { color: #b8bec7; text-align: right; padding: 0 16px 0 18px; user-select: none; }
pre { margin: 0; font: 14px/1.5 'DejaVu Sans Mono', monospace; }
.highlight { background: transparent; }
.highlight .nt { color: #2a78d6; }               /* keys */
.highlight .s2 { color: #b4531f; }               /* strings */
.highlight .mi, .highlight .mf { color: #12895f; } /* numbers */
.highlight .kc { color: #8250df; font-weight: bold; } /* true false null */
.highlight .p { color: #555555; }
"""


def render(text: str, title: str, out: Path) -> None:
    json.loads(text)  # still valid JSON
    code = highlight(text, JsonLexer(), HtmlFormatter(nowrap=True))
    lines = "\n".join(str(i) for i in range(1, text.count("\n") + 2))
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="win" id="win"><div class="bar"><span class="dot" style="background:#ff5f57"></span>
<span class="dot" style="background:#febc2e"></span><span class="dot" style="background:#28c840"></span>
<span class="title">{title}</span></div>
<div class="code"><pre class="ln">{lines}</pre><pre class="highlight">{code}</pre></div></div></body></html>"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(device_scale_factor=2, viewport={"width": 1100, "height": 800})
        page.set_content(html)
        page.locator("#win").screenshot(path=str(out))
        browser.close()
    print(out)


def cut(v):
    if isinstance(v, str):
        v = " ".join(v.split())
        return v if len(v) <= CUT else v[:CUT].rstrip() + "…"
    if isinstance(v, list):
        return v[:3]
    return v


def main() -> None:
    docs = ROOT / "docs"
    rec = json.loads((docs / "example-product.json").read_text(encoding="utf-8"))
    reviews = []
    for r in (r for r in rec["reviews"] if r["review_id"] in SHOW):
        small = {k: cut(r[k]) for k in KEEP}
        small["aspects"] = dict(list(r["aspects"].items())[:4])
        small["clauses"] = [{"text": c["text"], "count_site": c["count_site"]} for c in small["clauses"]]
        reviews.append(small)
    out = {
        "group": {k: v for k, v in rec["group"].items() if k != "group_id"},
        "reviews": reviews,
        "pros": [{k: p[k] for k in ("clause", "mentions", "count_site")} for p in cut(rec["pros"])],
        "cons": [{k: p[k] for k in ("clause", "mentions", "count_site")} for p in cut(rec["cons"])],
    }
    title = f"docs/example-product.json · 2 of {len(rec['reviews'])} reviews, with pros and cons, trimmed"
    render(fmt(out), title, docs / "img" / "product-json.png")


if __name__ == "__main__":
    main()
