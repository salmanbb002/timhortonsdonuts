"""Insert an empty <!-- SHARED:NAME --> marker pair on pages that may carry NAME and don't yet.

Usage: python3 scripts/add_markers.py NAME [LIMIT]
Then run scripts/sync.py to fill the new slots. Prints the pages it touched.
"""
import glob
import re
import sys

import sync

ITEM_CARD = re.compile(r'<div class="card" style="[^"]*">.*?<p class="price">.*?</p>\s*</div>\n', re.S)
OLD_DISCLAIMER = re.compile(r'\n *<p class="disclaimer">.*?</p>\n', re.S)


def empty(name):
    return f"<!-- SHARED:{name}:START --><!-- SHARED:{name}:END -->"


def exactly_one(pattern, s):
    m = list(re.finditer(pattern, s, re.S))
    if len(m) != 1:
        raise ValueError(f"{pattern!r} matched {len(m)} times, expected 1")
    return m[0]


def after(s, m, text):
    return s[: m.end()] + text + s[m.end():]


def place(name, page, s):
    if name == "JSONLD":
        m = exactly_one(r"</head>", s)
        return s[: m.start()] + empty(name) + "\n" + s[m.start():]
    if name == "VERIFIED":
        # Item pages: directly under the price card. Homepage + hubs: after the hero H1/intro, before any grid.
        m = exactly_one(ITEM_CARD.pattern, s) if '<div class="page">' in s else exactly_one(r"<main>\n", s)
        return after(s, m, f"  {empty(name)}\n")
    if name == "DISCLAIMER":
        # Move: drop the old page-bottom paragraph, re-add it as a shared block right after VERIFIED.
        if len(OLD_DISCLAIMER.findall(s)) != 1:
            raise ValueError("expected exactly one existing disclaimer paragraph")
        s = OLD_DISCLAIMER.sub("\n", s)
        return after(s, exactly_one(r"<!-- SHARED:VERIFIED:END -->\n", s), f"  {empty(name)}\n")
    if name in ("HEADER", "FOOTER"):
        tag = name.lower()
        m = exactly_one(rf"<{tag}>.*?</{tag}>", s)
        return s[: m.start()] + f"<!-- SHARED:{name}:START -->" + m[0] + f"<!-- SHARED:{name}:END -->" + s[m.end():]
    raise ValueError(f"no placement rule for {name}")


if __name__ == "__main__":
    name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    allowed = sync.BLOCKS[name][0]
    done = []
    for page in sorted(glob.glob("*.html")):
        s = open(page).read()
        if f"SHARED:{name}:" in s or not allowed(page, s):
            continue
        try:
            open(page, "w").write(place(name, page, s))
        except ValueError as e:
            sys.exit(f"{page}: {e}")
        done.append(page)
        if limit and len(done) == limit:
            break
    print(f"add_markers {name}: {len(done)} pages")
