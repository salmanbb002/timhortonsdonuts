"""Show the next unwritten blog post(s) from the Task 8 content calendar.

A post counts as done once its page exists in the repo (<slug>.html), so there is nothing to tick off by hand.
Usage: python3 scripts/next_post.py        # full brief for the next post + the queue after it
       python3 scripts/next_post.py --all  # every blog row with done/pending status
Reads seo-research/Blog_Keywords_and_Content_Calendar/ (local only, gitignored).
"""
import csv
import os
import sys

CAL = "seo-research/Blog_Keywords_and_Content_Calendar/Task8_26Week_Content_Calendar.csv"
BASE = "https://timhortonsdonuts.com/"

rows = [r for r in csv.DictReader(open(CAL)) if r["Content Type"] == "New blog post"]
for r in rows:
    r["slug"] = r["Target URL"].replace(BASE, "").strip("/")
    r["done"] = os.path.exists(r["slug"] + ".html")
    r["hold"] = "off-cycle" in r["Seasonal Trigger"].lower()

if "--all" in sys.argv:
    for r in rows:
        state = "DONE" if r["done"] else "HOLD - decision needed" if r["hold"] else "pending"
        print(f"wk {r['Week']:>2}  {r['Publish Date']}  {state:22}  /{r['slug']}  ({r['Primary Keyword']}, {r['Volume']}/mo)")
    print(f"\n{sum(r['done'] for r in rows)}/{len(rows)} blog posts published")
    sys.exit()

held = [r for r in rows if not r["done"] and r["hold"]]
queue = [r for r in rows if not r["done"] and not r["hold"]]
for r in held:
    print(f"HOLD wk {r['Week']}: /{r['slug']} - {r['Seasonal Trigger']} (publish as evergreen, skip, or delay?)")
if not queue:
    sys.exit("No unwritten blog posts left in the calendar.")

r = queue[0]
print(f"\nNEXT BLOG POST - week {r['Week']}, planned {r['Publish Date']}")
for key in ("Working Title", "Target URL", "Primary Keyword", "Volume", "KD%", "Search Intent", "Word Count Target",
            "Required Sections (in order)", "Schema Types", "3 Internal Links IN (source page — anchor text)",
            "Pages This Links OUT To", "SERP Feature Targeted", "Seasonal Trigger", "Priority"):
    print(f"  {key}: {r[key]}")
print("\nAfter that:")
for r in queue[1:4]:
    print(f"  wk {r['Week']:>2}  {r['Publish Date']}  /{r['slug']}  ({r['Primary Keyword']}, {r['Volume']}/mo)")
