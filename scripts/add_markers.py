"""Insert an empty <!-- SHARED:NAME --> marker pair before ANCHOR on pages that may carry NAME and don't yet.

Usage: python3 scripts/add_markers.py NAME ANCHOR [LIMIT]
  e.g. python3 scripts/add_markers.py JSONLD '</head>' 40
Then run scripts/sync.py to fill the new slots. Prints the pages it touched.
"""
import glob
import sys

import sync

name, anchor = sys.argv[1], sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
allowed = sync.BLOCKS[name][0]
done = []
for page in sorted(glob.glob("*.html")):
    s = open(page).read()
    if f"SHARED:{name}:" in s or not allowed(page, s):
        continue
    if s.count(anchor) != 1:
        sys.exit(f"{page}: anchor {anchor!r} found {s.count(anchor)} times, expected 1")
    open(page, "w").write(s.replace(anchor, f"<!-- SHARED:{name}:START --><!-- SHARED:{name}:END -->\n{anchor}"))
    done.append(page)
    if limit and len(done) == limit:
        break
print(f"add_markers {name}: {len(done)} pages")
print(" ".join(done))
