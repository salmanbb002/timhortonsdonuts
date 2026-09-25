"""T10-002: rewrite every internal .html URL (canonical, hrefs, og:url, JSON-LD) to the clean URL Vercel serves.

Idempotent. Run from repo root: python3 scripts/clean_urls.py
"""
import glob
import re

# A quoted internal URL: optional domain, a slug, .html, then end of string or #fragment.
URL = re.compile(r'"(https://timhortonsdonuts\.com)?/([a-z0-9-]+)\.html(?=["#])')


def clean(m):
    domain, slug = m.group(1) or "", m.group(2)
    return f'"{domain}/' if slug == "index" else f'"{domain}/{slug}'


changed = 0
for f in sorted(glob.glob("*.html")):
    s = open(f).read()
    out = URL.sub(clean, s)
    if out != s:
        open(f, "w").write(out)
        changed += 1
print(f"rewrote {changed} files")
