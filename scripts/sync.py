"""Stamp shared blocks into the static HTML between <!-- SHARED:NAME:START/END --> markers.

Source of truth lives in data/. Idempotent. Run from repo root: python3 scripts/sync.py
Stamps a block wherever its markers are; fails (exit 1) on duplicated markers or markers on a page
that shouldn't carry the block. Which pages MUST carry which block is enforced by scripts/check.py.
"""
import glob
import html
import json
import re
import sys
from datetime import date

import jsonld

DONUTS = json.load(open("data/donuts.json"))
CONFIG = json.load(open("data/site-config.json"))
VERIFIED_DATE = date.fromisoformat(CONFIG["prices_verified_date"])  # the only source for the verified line


def donut_grid(page, s):
    cards = []
    for d in DONUTS:
        name = html.escape(d["name"])
        badge = ' <span class="badge">Limited time</span>' if d["seasonal"] else ""
        cards.append(
            f'    <article class="card"><div class="card-img"><img src="{d["img"]}" alt="{name}" loading="lazy" width="280" height="280"></div>'
            f'<h3><a href="/{d["id"]}">{name}</a>{badge}</h3>'
            f'<p class="price">${d["price"]:.2f} CAD <span class="cal">{d["calories"]} cal</span></p></article>'
        )
    return "\n" + "\n".join(cards) + "\n    "


def verified(page, s):
    d = VERIFIED_DATE
    return f'<p class="verified">Prices last verified: {d:%B} {d.day}, {d.year}</p>'


def disclaimer(page, s):
    # Table 6E-audited wording as the site already had it (homepage/hubs and items that show calories say
    # "Prices and calories", other items "Prices"), plus the homepage's sourcing and image-rights sentences.
    is_item = jsonld.template_for(page, s) is jsonld.item_page
    what = "Prices" if is_item and 'class="cal"' not in s else "Prices and calories"
    return (
        '<p class="disclaimer">\n'
        "    This is an independent, unofficial guide to the Tim Hortons Canada menu. It is not affiliated with, endorsed by,\n"
        f"    or sponsored by Tim Hortons or Restaurant Brands International. {what} are listed reference estimates\n"
        "    in CAD, before tax, and vary by location, province and over time. They are sourced from a public menu reference\n"
        "    and may not reflect current pricing at every location. Product names and images belong to their respective owners.\n"
        '    See <a href="/sources">Sources</a> for details.\n'
        "  </p>"
    )


def partial(name):
    return lambda page, s: open(f"data/partials/{name}.html").read().rstrip("\n")


def price_page(page, s):
    return jsonld.template_for(page, s) is not None


# block name -> (page may carry it?, renderer). Order matters: JSON-LD reads the stamped donut grid.
BLOCKS = {
    "DONUT-GRID": (lambda page, s: page in {"index.html", "donuts-menu.html"}, donut_grid),
    "JSONLD": (price_page, jsonld.block),
    "VERIFIED": (price_page, verified),
    "DISCLAIMER": (price_page, disclaimer),
    "HEADER": (lambda page, s: page != "404.html", partial("header")),
    "FOOTER": (lambda page, s: page != "404.html", partial("footer")),
}


def replace_block(s, name, body):
    pat = re.compile(rf"(<!-- SHARED:{name}:START -->)(.*?)(<!-- SHARED:{name}:END -->)", re.S)
    if len(pat.findall(s)) != 1 or s.count(f"SHARED:{name}:") != 2:
        raise ValueError(f"expected exactly one {name} marker pair")
    return pat.sub(lambda m: m[1] + body + m[3], s)


def render(page, s):
    for name, (allowed, fn) in BLOCKS.items():
        if f"SHARED:{name}:" not in s:
            continue
        if not allowed(page, s):
            raise ValueError(f"has {name} markers but shouldn't carry that block")
        s = replace_block(s, name, fn(page, s))
    return s


if __name__ == "__main__":
    errors, changed = [], 0
    for page in sorted(glob.glob("*.html")):
        s = open(page).read()
        try:
            out = render(page, s)
        except ValueError as e:
            errors.append(f"{page}: {e}")
            continue
        if out != s:
            open(page, "w").write(out)
            changed += 1
    print("\n".join(errors))
    print(f"sync: {changed} files updated, {len(errors)} errors")
    sys.exit(1 if errors else 0)
