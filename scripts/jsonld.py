"""T10-001: build each page's JSON-LD from its own static HTML (templates in seo-research/task7_structured_data/).

Template mapping (Table 6A action + Table 5 page type):
  index.html            -> 1 homepage     (Organization + WebSite + BreadcrumbList)
  *-menu.html hubs      -> 2 menu hub     (Menu + MenuSection/MenuItem + BreadcrumbList)
  item pages (div.page) -> 4 item page    (Product + Offer [+ nutrition] + BreadcrumbList)
Template 3 (sub-category CollectionPage) and 5 (standalone nutrition page) have no existing page yet.
Template 6 (blog) is hand-written on the blog post itself.
"""
import html
import json
import re

BASE = "https://timhortonsdonuts.com"
TIM = {"@type": "Organization", "name": "Tim Hortons"}


def text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def one(pattern, s, what):
    m = re.findall(pattern, s, re.S)
    if len(m) != 1:
        raise ValueError(f"expected one {what}, found {len(m)}")
    return m[0]


def absolute(href):
    return BASE + href if href.startswith("/") else f"{BASE}/{href}"


def offer(price_html):
    """'$2.09 CAD' -> Offer; 'S $1.59 · M $1.83 ...' -> AggregateOffer (low/high), as in template 3."""
    prices = re.findall(r"\$(\d+\.\d{2})", price_html)
    if not prices:
        raise ValueError(f"no price in {price_html!r}")
    if len(prices) == 1:
        return {"@type": "Offer", "price": prices[0], "priceCurrency": "CAD"}
    nums = sorted(prices, key=float)
    return {"@type": "AggregateOffer", "lowPrice": nums[0], "highPrice": nums[-1], "priceCurrency": "CAD"}


def nutrition(price_html):
    """Only when the page itself shows calories; never inferred (Task 7A P0 / Task 9D NOT AVAILABLE rule)."""
    m = re.search(r'<span class="cal">(\d+) cal</span>', price_html)
    return {"nutrition": {"@type": "NutritionInformation", "calories": f"{m[1]} cal"}} if m else {}


def breadcrumb(url, crumbs):
    return {
        "@type": "BreadcrumbList",
        "@id": f"{url}#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": n, "item": u} for i, (n, u) in enumerate(crumbs, 1)
        ],
    }


def homepage(s):
    # Template 1, minus potentialAction/SearchAction: the site has no ?s= search, so declaring one would be false.
    org = f"{BASE}/#organization"
    return [
        {
            "@type": "Organization",
            "@id": org,
            "name": "TimHortonsDonuts.com",
            "url": f"{BASE}/",
            "logo": {"@type": "ImageObject", "url": f"{BASE}/favicon.svg"},
            "description": "An independent, unofficial fan guide to the Tim Hortons Canada menu. Not affiliated with, "
            "endorsed by, or sponsored by Tim Hortons or Restaurant Brands International.",
        },
        {"@type": "WebSite", "@id": f"{BASE}/#website", "url": f"{BASE}/", "name": "Tim Hortons Donuts", "publisher": {"@id": org}},
        breadcrumb(f"{BASE}/", [("Home", f"{BASE}/")]),
    ]


CARD = re.compile(r'<article class="card">.*?<h3><a href="([^"]+)">(.*?)</a>.*?</h3>\s*<p class="price">(.*?)</p>\s*</article>', re.S)


def menu_hub(s, url):
    name = text(one(r"<h1>(.*?)</h1>", s, "h1"))
    main = one(r"<main>(.*?)</main>", s, "main")
    sections = []
    # Each <h2 class="section-title"> heads the grid that follows it.
    for title, body in re.findall(r'<h2 class="section-title"[^>]*>(.*?)</h2>(.*?)(?=<h2 class="section-title"|$)', main, re.S):
        items = [
            {"@type": "MenuItem", "name": text(n), "url": absolute(h), "offers": offer(p), **nutrition(p)}
            for h, n, p in CARD.findall(body)
        ]
        if items:
            sections.append({"@type": "MenuSection", "name": text(title), "hasMenuItem": items})
    cards = main.count('<p class="price">')
    if sum(len(x["hasMenuItem"]) for x in sections) != cards:
        raise ValueError(f"parsed {sum(len(x['hasMenuItem']) for x in sections)} menu items but page shows {cards} prices")
    return [
        {"@type": "Menu", "@id": f"{url}#menu", "name": name, "url": url, "inLanguage": "en", "hasMenuSection": sections},
        breadcrumb(url, [("Home", f"{BASE}/"), (name, url)]),
    ]


def item_page(s, url):
    name = text(one(r"<h1>(.*?)</h1>", s, "h1"))
    price_html = one(r'<p class="price">(.*?)</p>', s, "price")
    img = one(r'<div class="card-img"><img src="([^"]+)"', s, "card image")
    desc = html.unescape(one(r'<meta name="description" content="([^"]*)">', s, "meta description"))
    # Breadcrumb: <p><a href="/">Full Menu</a> / <a href="HUB">Category</a> / Name</p>
    hub_href, category = one(r'<div class="page">\s*<p><a href="/">[^<]*</a> / <a href="([^"]+)">(.*?)</a> / ', s, "breadcrumb")
    category = text(category)
    product = {
        "@type": "Product",
        "@id": f"{url}#product",
        "name": name,
        "url": url,
        "image": absolute(img),
        "description": desc,
        "category": category,
        "brand": {"@type": "Brand", "name": "Tim Hortons"},
        "offers": {**offer(price_html), "seller": TIM},
        **nutrition(price_html),
    }
    crumbs = [("Home", f"{BASE}/")]
    if not hub_href.startswith("/#"):  # 67 items only link to a homepage anchor; no hub page to point at
        product["isRelatedTo"] = {"@type": "WebPage", "url": absolute(hub_href)}
        crumbs.append((category, absolute(hub_href)))
    crumbs.append((name, url))
    return [product, breadcrumb(url, crumbs)]


def template_for(page, s):
    if page == "index.html":
        return homepage
    if page.endswith("-menu.html") and 'class="hero"' in s:
        return menu_hub
    if '<div class="page">' in s and s.count('<p class="price">') == 1:
        return item_page
    return None


def block(page, s):
    url = one(r'<link rel="canonical" href="([^"]+)">', s, "canonical")
    fn = template_for(page, s)
    graph = fn(s) if fn is homepage else fn(s, url)
    body = json.dumps({"@context": "https://schema.org", "@graph": graph}, indent=2, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{body}\n</script>'
