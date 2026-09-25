"""T10-026: apply Table 6D's proposed title / meta description / H1 to existing pages.

Usage: python3 scripts/apply_meta.py [path to Table_6D_Meta_Optimisation.csv]
       (default seo-research/Table_6D_Meta_Optimisation.csv, which is local-only)

Only Table 6D rows are used; no other page's meta is touched. A row is written only if ALL hold:
  - the page exists (NEW/CREATE and template-formula rows are skipped)
  - title <= 60 chars, description 140-155 chars
  - every number in title/description/H1 appears in the page's visible content
  - it doesn't promise calories on a page that shows none
  - the title isn't already used by another page
Rows that fail are NOT written; each is printed and the script exits 1.
Written rows are recorded in data/meta.json, which scripts/check.py enforces from then on.
"""
import csv
import glob
import html
import json
import re
import sys

src = sys.argv[1] if len(sys.argv) > 1 else "seo-research/Table_6D_Meta_Optimisation.csv"
managed = json.load(open("data/meta.json")) if glob.glob("data/meta.json") else {}
titles = {p: html.unescape(re.search(r"<title>(.*?)</title>", open(p).read(), re.S)[1]) for p in glob.glob("*.html")}


def visible(s):
    body = re.sub(r"<script.*?</script>|<!--.*?-->", "", s.split("</head>", 1)[1], flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", body))


failed, written, skipped = [], [], []
for r in csv.DictReader(open(src)):
    slug = r["URL"].strip("/") or "index"
    page = f"{slug}.html"
    if page not in titles:
        skipped.append(r["URL"])
        continue
    t, d, h1 = r["Proposed Title"], r["Proposed Meta Description"], r["Proposed H1"]
    s = open(page).read()
    text = visible(s)
    errs = []
    if len(t) > 60:
        errs.append(f"title {len(t)} chars > 60")
    if not 140 <= len(d) <= 155:
        errs.append(f"description {len(d)} chars, want 140-155")
    for n in set(re.findall(r"\d[\d,.]*", t + " " + d + " " + h1)):
        if n.rstrip(".,") not in text:
            errs.append(f"number {n!r} not shown on page")
    if re.search(r"calorie", t + d + h1, re.I) and 'class="cal"' not in s:
        errs.append("promises calories but page shows none")
    if any(v == t for p, v in titles.items() if p != page):
        errs.append("title already used by another page")
    if errs:
        failed.append(f"{r['URL']}: " + "; ".join(errs))
        continue
    s = re.sub(r"<title>.*?</title>", lambda m: f"<title>{html.escape(t, quote=False)}</title>", s, count=1, flags=re.S)
    s = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{html.escape(d)}">', s, count=1)
    if len(re.findall(r"<h1>.*?</h1>", s, re.S)) != 1:
        failed.append(f"{r['URL']}: expected exactly one <h1>")
        continue
    s = re.sub(r"<h1>.*?</h1>", lambda m: f"<h1>{html.escape(h1, quote=False)}</h1>", s, count=1, flags=re.S)
    open(page, "w").write(s)
    titles[page] = t
    managed[page] = {"title": t, "description": d, "h1": h1}
    written.append(r["URL"])

json.dump(managed, open("data/meta.json", "w"), indent=2, ensure_ascii=False)
print(f"written ({len(written)}): {' '.join(written)}")
print(f"skipped, no such page ({len(skipped)}): {' '.join(skipped)}")
print(f"FAILED, not written ({len(failed)}):")
print("\n".join("  " + f for f in failed))
sys.exit(1 if failed else 0)
