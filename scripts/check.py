"""Pre-deploy verification harness. Exits non-zero on any failure.

Run from repo root: python3 scripts/check.py
"""
import glob
import os
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

if not os.path.exists("menu.js") or ".html" in open("menu.js").read():
    fails.append("menu.js: still builds .html links")

print("\n".join(fails[:50]))
print(f"check: {len(pages)} pages, {len(fails)} failures -> {'FAIL' if fails else 'PASS'}")
sys.exit(1 if fails else 0)
