"""Pre-deploy verification harness. Exits non-zero on any failure.

Run from repo root: python3 scripts/check.py
"""
import collections
import glob
import json
import re
import sys

sys.path.insert(0, "scripts")
import sync  # noqa: E402

BASE = "https://timhortonsdonuts.com"
PLACEHOLDERS = ("NOT AVAILABLE", "YYYY", "{{", "[NOT", "fruit-quenchers-menu", "example.com")
fails = collections.defaultdict(list)
pages = sorted(glob.glob("*.html"))
slugs = {p[:-5] for p in pages}


def walk(node, key):
    """Yield every value stored under `key` anywhere in a JSON tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield v
            yield from walk(v, key)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v, key)


for p in pages:
    s = open(p).read()
    slug = p[:-5]
    want = f"{BASE}/" if slug == "index" else f"{BASE}/{slug}"

    # Canonical: exactly one, clean, self-referencing. 404 has none by design.
    canon = re.findall(r'<link rel="canonical" href="([^"]*)">', s)
    if slug == "404":
        if canon:
            fails["canonical"].append(f"{p}: 404 should have no canonical")
    elif canon != [want]:
        fails["canonical"].append(f"{p}: canonical {canon} != {want}")

    # No internal .html URLs left anywhere in the page.
    for u in re.findall(r'"((?:https://timhortonsdonuts\.com)?/[^"]*\.html[^"]*)"', s):
        fails["links"].append(f"{p}: internal .html URL {u}")

    # Every internal page link resolves to a real file.
    for u in re.findall(r'href="/([a-z0-9-]*)(?:#[^"]*)?"', s):
        if u and u not in slugs:
            fails["links"].append(f"{p}: broken internal link /{u}")

    # Shared blocks are well-formed and match their sources (scripts/sync.py was run).
    try:
        if sync.render(p, s) != s:
            fails["sync"].append(f"{p}: out of date, run scripts/sync.py")
    except ValueError as e:
        fails["sync"].append(f"{p}: {e}")
    if 'id="donut-grid"' in s and "SHARED:DONUT-GRID:START" not in s:
        fails["sync"].append(f"{p}: donut-grid has no SHARED:DONUT-GRID markers")

    # JSON-LD: every block parses; every price page carries one; values trace to the visible page.
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S)
    if 'class="price"' in s and not blocks:
        fails["jsonld-coverage"].append(f"{p}: shows prices but has no JSON-LD")
    body = s.split("</head>", 1)[1]
    shown_prices = set(re.findall(r"\$(\d+\.\d{2})", body))
    shown_cals = set(re.findall(r'<span class="cal">(\d+) cal</span>', body))
    for b in blocks:
        try:
            data = json.loads(b)
        except json.JSONDecodeError as e:
            fails["jsonld-parse"].append(f"{p}: invalid JSON-LD ({e})")
            continue
        for ph in PLACEHOLDERS:
            if ph in b:
                fails["jsonld-values"].append(f"{p}: placeholder/sample value {ph!r}")
        for i in walk(data, "@id"):
            if not (i.startswith(want) or i.startswith(f"{BASE}/#")):
                fails["jsonld-values"].append(f"{p}: foreign @id {i}")
        if "SHARED:JSONLD" not in s:
            continue  # hand-written blog schema: parse + placeholder checks only
        for key in ("price", "lowPrice", "highPrice"):
            for v in walk(data, key):
                if v not in shown_prices:
                    fails["jsonld-values"].append(f"{p}: {key} {v} not shown on page")
        for v in walk(data, "calories"):
            if v.removesuffix(" cal") not in shown_cals:
                fails["jsonld-values"].append(f"{p}: calories {v} not shown on page")

# Sitemap lists only clean URLs, each backed by a real page.
for u in re.findall(r"<loc>([^<]*)</loc>", open("sitemap.xml").read()):
    slug = u.removeprefix(BASE + "/") or "index"
    if u.endswith(".html") or slug not in slugs:
        fails["sitemap"].append(f"sitemap.xml: bad <loc> {u}")

total = sum(map(len, fails.values()))
for cat, msgs in fails.items():
    print(f"[{cat}] {len(msgs)} failures")
    print("\n".join("  " + m for m in msgs[:10]))
print(f"check: {len(pages)} pages, {total} failures -> {'FAIL' if total else 'PASS'}")
sys.exit(1 if total else 0)
