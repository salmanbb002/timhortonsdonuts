"""T10-003: Fruit Quencher page copy, generated from the pages' own price lines (never invented).

Two sync blocks on the 18 flavour x format pages:
  QUENCHER        format/sizes/prices, same-flavour sibling formats (linked, with their live prices), FAQ
  QUENCHER-FACTS  attributed, dated line-level facts from Tim Hortons' June 14, 2021 press release
Sibling prices are read from the sibling pages at sync time, so a price change can't leave them stale.
"""
import html
import re

FLAVOURS = {
    "blackberry-yuzu": "Blackberry Yuzu",
    "orange-tangerine": "Orange Tangerine",
    "peach": "Peach",
    "pineapple-dragon-fruit": "Pineapple Dragon Fruit",
    "strawberry-watermelon": "Strawberry Watermelon",
    "wildberry-hibiscus": "Wildberry Hibiscus",
}
FORMATS = {"lemonade": "Lemonade", "sparkling": "Sparkling", "frozen": "Frozen"}
SIZES = {"S": "Small", "M": "Medium", "L": "Large"}
PAGE = re.compile(rf"^({'|'.join(FLAVOURS)})-({'|'.join(FORMATS)})-quencher\.html$")
RELEASE = (
    "https://www.newswire.ca/news-releases/tim-hortons-launches-new-tims-real-fruit-quenchers-in-strawberry-"
    "watermelon-and-peach-flavours-to-keep-canadians-refreshed-all-summer-long--857404448.html"
)
# The CMO quote is scoped to the two flavours that release launched.
RELEASE_FLAVOURS = {"peach", "strawberry-watermelon"}


def is_quencher(page, s=None):
    return bool(PAGE.match(page))


def prices(flavour, fmt):
    s = open(f"{flavour}-{fmt}-quencher.html").read()
    line = re.search(r'<p class="price">(.*?)</p>', s)[1]
    return {k: v for k, v in re.findall(r"\b([SML]) \$(\d+\.\d\d)", line)}


def fmt_line(p):
    return " · ".join(f"{k} ${v}" for k, v in p.items())


def quencher(page, s):
    flavour, fmt = PAGE.match(page).groups()
    fl, fm = FLAVOURS[flavour], FORMATS[fmt]
    name = f"{fl} {fm} Quencher"
    all_p = {(f, m): prices(f, m) for f in FLAVOURS for m in FORMATS}
    p = all_p[(flavour, fmt)]
    vals = [float(v) for v in p.values()]
    steps = {round(b - a, 2) for a, b in zip(vals, vals[1:])}
    step = f", with each size step adding ${steps.pop():.2f}" if len(steps) == 1 else ""
    sizes = ", ".join(f"{SIZES[k]} ${v}" for k, v in p.items())
    out = [f"<p>{name} is the {fm.lower()} version of {fl} in the Tim Hortons Fruit Quenchers lineup. "
           f"It is listed in {len(p)} size{'s' if len(p) > 1 else ''}: {sizes}{step}.</p>"]

    sibs = [m for m in FORMATS if m != fmt]
    links = " and a ".join(
        f'<a href="/{flavour}-{m}-quencher">{FORMATS[m]} Quencher</a> ({fmt_line(all_p[(flavour, m)])})' for m in sibs
    )
    text = f"<h2>Other ways to order {fl}</h2>\n  <p>{fl} is also listed as a {links}."
    common = [k for k in SIZES if all(k in all_p[(flavour, m)] for m in FORMATS)]
    if common:
        order = sorted(FORMATS, key=lambda m: sum(float(all_p[(flavour, m)][k]) for k in common))
        pos = "lowest-priced" if order[0] == fmt else "highest-priced" if order[-1] == fmt else "mid-priced"
        where = (f"At {SIZES[common[0]]}, the only size all three are listed in" if len(common) == 1
                 else "Across the sizes all three share")
        text += f" {where}, the {fm} version is the {pos} of the three."
    out.append(text + "</p>")

    key = "M" if "M" in p else next(iter(p))
    faq = [f"<h2>Common questions</h2>",
           f"<h3>How much is a {SIZES[key].lower()} {name}?</h3>",
           f"<p>${p[key]} CAD before tax, as last verified. Prices vary by location and province.</p>",
           f"<h3>Is it priced differently from other {fm} Quenchers?</h3>"]
    same = [FLAVOURS[f] for f in FLAVOURS if f != flavour and all_p[(f, fmt)] == p]
    diff = [(FLAVOURS[f], all_p[(f, fmt)]) for f in FLAVOURS if f != flavour and all_p[(f, fmt)] != p]
    if same:
        names = ", ".join(same[:-1]) + (" and " if len(same) > 1 else "") + same[-1]
        tail = "; " + "; ".join(f"{n} is listed at {fmt_line(x)}" for n, x in diff) if diff else ""
        faq.append(f"<p>No. {names} {fm} Quenchers are listed at the same prices{tail}.</p>")
    else:
        others = {fmt_line(x) for _, x in diff}
        faq.append(f"<p>Yes. The other five {fm} Quenchers are listed at {' / '.join(sorted(others))}; "
                   f"{name} is listed at {fmt_line(p)}.</p>")
    faq += [f"<h3>Is the {name} caffeine-free and dairy-free?</h3>",
            "<p>Independent menu guides consistently list Fruit Quenchers as caffeine-free and dairy-free. "
            "If you have an allergy, confirm with Tim Hortons' official allergen information before ordering.</p>"]
    out += faq
    return "\n  " + "\n  ".join(out) + "\n  "


def quencher_facts(page, s):
    flavour = PAGE.match(page)[1]
    body = [
        "<h2>About Fruit Quenchers</h2>",
        f'<p>In a <a href="{RELEASE}" rel="nofollow">June 14, 2021 press release</a>, Tim Hortons said its Real Fruit '
        "Quenchers “are made from real fruit juice from concentrate.”</p>",
    ]
    if flavour in RELEASE_FLAVOURS:
        body.append(
            f"<p>That release launched {html.escape(FLAVOURS[flavour])} alongside "
            f"{'Strawberry Watermelon' if flavour == 'peach' else 'Peach'}. Hope Bagozzi, Tim Hortons’ Chief "
            "Marketing Officer, said the two new flavours are “part of our commitment to providing guests with "
            "menu items that are made without artificial colours or flavours.”</p>"
        )
    return "\n  " + "\n  ".join(body) + "\n  "
