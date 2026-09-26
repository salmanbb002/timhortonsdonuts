"""Pre-deploy verification harness. Exits non-zero on any failure.

Run from repo root: python3 scripts/check.py
"""
import collections
import datetime
import glob
import html
import json
import re
import sys

sys.path.insert(0, "scripts")
import jsonld  # noqa: E402
import sync  # noqa: E402

BASE = "https://timhortonsdonuts.com"
# Page-level blocks every price page must carry (the blog post shows illustrative price cards inside an
# article and keeps its own cited disclaimer, so it is not a sync.price_page).
REQUIRED_ON_PRICE_PAGES = ("JSONLD", "VERIFIED", "DISCLAIMER")
DATE_TEXT = re.compile(r"(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2}")
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

    # Required shared blocks on price pages.
    if sync.price_page(p, s):
        for name in REQUIRED_ON_PRICE_PAGES:
            if f"SHARED:{name}:START" not in s:
                fails[f"{name.lower()}-coverage"].append(f"{p}: price page without SHARED:{name}")

    # Header/footer partials on every page but the deliberately minimal 404; one disclaimer per price page.
    if p != "404.html":
        for name in ("HEADER", "FOOTER"):
            if f"SHARED:{name}:START" not in s:
                fails[f"{name.lower()}-coverage"].append(f"{p}: without SHARED:{name}")
    if sync.is_article(p, s) and "SHARED:BYLINE:START" not in s:
        fails["author"].append(f"{p}: Article page without SHARED:BYLINE")
    if p == "about.html" and "SHARED:AUTHOR:START" not in s:
        fails["author"].append(f"{p}: About page without SHARED:AUTHOR bio")
    n = s.count('<p class="disclaimer">')
    if sync.price_page(p, s) and n != 1:
        fails["disclaimer-count"].append(f"{p}: {n} disclaimer paragraphs, want 1")

    # "Last verified" must come only from data/site-config.json via the VERIFIED block: any verified-date
    # text outside that block is a hardcoded date. (Inside it, the sync check above catches a stale/edited date.)
    outside = re.sub(r"<!-- SHARED:VERIFIED:START -->.*?<!-- SHARED:VERIFIED:END -->", "", s, flags=re.S)
    for m in re.finditer(r"verified", outside, re.I):
        near = outside[m.start(): m.start() + 60]
        if DATE_TEXT.search(near):
            fails["verified-hardcoded"].append(f"{p}: hardcoded verified date {' '.join(near.split())!r}")

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
        # Article authors are the named Person from data/site-config.json, never an Organization (T10-005).
        for node in walk(data, "@graph"):
            for n in node:
                if n.get("@type") == "Article":
                    a = n.get("author", {})
                    if not (isinstance(a, dict) and a.get("@type") == "Person" and a.get("name") == sync.AUTHOR["name"]):
                        fails["author"].append(f"{p}: Article author is {a!r}, want Person {sync.AUTHOR['name']!r}")
        if "SHARED:JSONLD" not in s:
            continue  # hand-written blog schema: parse + placeholder checks only
        for key in ("price", "lowPrice", "highPrice"):
            for v in walk(data, key):
                if v not in shown_prices:
                    fails["jsonld-values"].append(f"{p}: {key} {v} not shown on page")
        for v in walk(data, "calories"):
            if v.removesuffix(" cal") not in shown_cals:
                fails["jsonld-values"].append(f"{p}: calories {v} not shown on page")

# T10-037: the Tim Hortons entity (Organization + sameAs). Parsed-JSON comparison: dict equality ignores key
# order, and string arrays (sameAs) are compared sorted, so reordering can't read as drift.
def canon(x):
    if isinstance(x, dict):
        return {k: canon(v) for k, v in x.items()}
    if isinstance(x, list):
        items = [canon(v) for v in x]
        return sorted(items) if all(isinstance(v, str) for v in items) else items
    return x


want_entity = canon(jsonld.TIM_HORTONS_ENTITY)
ENTITY_PAGES = {"index.html"} | {p for p in pages if p.endswith("-menu.html") and 'class="hero"' in open(p).read()}
entity_carriers = set()
for p in pages:
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', open(p).read(), re.S):
        try:
            data = json.loads(b)
        except json.JSONDecodeError:
            continue  # reported under jsonld-parse
        for about in walk(data, "about"):
            for e in about if isinstance(about, list) else [about]:
                if isinstance(e, dict) and e.get("name") == "Tim Hortons":
                    entity_carriers.add(p)
                    if canon(e) != want_entity:
                        fails["entity"].append(f"{p}: Tim Hortons 'about' differs from jsonld.TIM_HORTONS_ENTITY")
REFERENCE = "are-tim-hortons-donuts-baked-or-fried.html"  # hand-written original the constant was copied from
for p in sorted(ENTITY_PAGES - entity_carriers):
    fails["entity"].append(f"{p}: missing Tim Hortons 'about' entity")
for p in sorted(entity_carriers - ENTITY_PAGES - {REFERENCE}):
    fails["entity"].append(f"{p}: unexpected Tim Hortons 'about' entity")
if REFERENCE not in entity_carriers:
    fails["entity"].append(f"{REFERENCE}: reference Tim Hortons 'about' entity missing")
if len(ENTITY_PAGES) != 13:
    fails["entity"].append(f"expected 13 entity pages (homepage + 12 hubs), found {len(ENTITY_PAGES)}")

# The verified date itself must be a real, non-future date.
if sync.VERIFIED_DATE > datetime.date.today():
    fails["verified-date"].append(f"data/site-config.json: prices_verified_date {sync.VERIFIED_DATE} is in the future")

# Titles unique sitewide; pages whose meta came from Table 6D (data/meta.json) must match it and fit the
# length rules. Other pages keep legacy meta (Table 6D never covered them) and are only counted.
titles, legacy_out = {}, 0
managed = json.load(open("data/meta.json")) if glob.glob("data/meta.json") else {}
for p in pages:
    s = open(p).read()
    t = html.unescape(re.search(r"<title>(.*?)</title>", s, re.S)[1])
    m = re.search(r'<meta name="description" content="([^"]*)">', s)
    d = html.unescape(m[1]) if m else ""
    if t in titles:
        fails["meta"].append(f"{p}: duplicate title (also {titles[t]})")
    titles[t] = p
    if p in managed:
        h1 = html.unescape(re.search(r"<h1>(.*?)</h1>", s, re.S)[1])
        if (t, d, h1) != (managed[p]["title"], managed[p]["description"], managed[p]["h1"]):
            fails["meta"].append(f"{p}: title/description/H1 differ from data/meta.json")
        if len(t) > 60 or not 140 <= len(d) <= 155:
            fails["meta"].append(f"{p}: title {len(t)} / description {len(d)} chars out of spec")
    elif p != "404.html" and (len(t) > 60 or not 140 <= len(d) <= 155):
        legacy_out += 1

# Sitemap lists only clean URLs, each backed by a real page.
for u in re.findall(r"<loc>([^<]*)</loc>", open("sitemap.xml").read()):
    slug = u.removeprefix(BASE + "/") or "index"
    if u.endswith(".html") or slug not in slugs:
        fails["sitemap"].append(f"sitemap.xml: bad <loc> {u}")

print(f"[info] {legacy_out} pages keep legacy meta outside title<=60 / description 140-155 (no Table 6D row)")
total = sum(map(len, fails.values()))
for cat, msgs in fails.items():
    print(f"[{cat}] {len(msgs)} failures")
    print("\n".join("  " + m for m in msgs[:10]))
print(f"check: {len(pages)} pages, {total} failures -> {'FAIL' if total else 'PASS'}")
sys.exit(1 if total else 0)
