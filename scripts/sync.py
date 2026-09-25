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

import jsonld

DONUTS = json.load(open("data/donuts.json"))


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


# block name -> (page may carry it?, renderer). Order matters: JSON-LD reads the stamped donut grid.
BLOCKS = {
    "DONUT-GRID": (lambda page, s: page in {"index.html", "donuts-menu.html"}, donut_grid),
    "JSONLD": (lambda page, s: jsonld.template_for(page, s) is not None, jsonld.block),
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
