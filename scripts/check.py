"""Pre-deploy verification harness. Exits non-zero on any failure.

Run from repo root: python3 scripts/check.py
"""
import glob
import re
import sys

BASE = "https://timhortonsdonuts.com"
fails = []
pages = sorted(glob.glob("*.html"))
slugs = {p[:-5] for p in pages}

for p in pages:
    s = open(p).read()
    slug = p[:-5]

    # Canonical: exactly one, clean, self-referencing. 404 has none by design.
    canon = re.findall(r'<link rel="canonical" href="([^"]*)">', s)
    want = f"{BASE}/" if slug == "index" else f"{BASE}/{slug}"
    if slug == "404":
        if canon:
            fails.append(f"{p}: 404 should have no canonical")
    elif canon != [want]:
        fails.append(f"{p}: canonical {canon} != {want}")

    # No internal .html URLs left anywhere in the page.
    for u in re.findall(r'"((?:https://timhortonsdonuts\.com)?/[^"]*\.html[^"]*)"', s):
        fails.append(f"{p}: internal .html URL {u}")

    # Every internal page link resolves to a real file.
    for u in re.findall(r'href="/([a-z0-9-]*)(?:#[^"]*)?"', s):
        if u and u not in slugs:
            fails.append(f"{p}: broken internal link /{u}")

# Sitemap lists only clean URLs, each backed by a real page.
for u in re.findall(r"<loc>([^<]*)</loc>", open("sitemap.xml").read()):
    slug = u.removeprefix(BASE + "/") or "index"
    if u.endswith(".html") or slug not in slugs:
        fails.append(f"sitemap.xml: bad <loc> {u}")

# Shared blocks match data/ (i.e. scripts/sync.py was run and markers are well-formed).
sys.path.insert(0, "scripts")
import sync  # noqa: E402

for p in pages:
    s = open(p).read()
    try:
        if sync.render(p, s) != s:
            fails.append(f"{p}: out of date, run scripts/sync.py")
    except ValueError as e:
        fails.append(f"{p}: {e}")
    if 'id="donut-grid"></div>' in s:
        fails.append(f"{p}: empty donut-grid in static HTML")

print("\n".join(fails[:50]))
print(f"check: {len(pages)} pages, {len(fails)} failures -> {'FAIL' if fails else 'PASS'}")
sys.exit(1 if fails else 0)
