#!/usr/bin/env python3
"""Regenerate the JSON-LD block in index.html and rewrite sitemap.xml.

The site has no build step and deploys fine without ever running this. It
exists because three things must agree and will silently drift apart if they
are edited by hand:

  * the 13 <article class="product"> cards      -> ItemList / Product schema
  * the 7 <details class="faq__item"> entries   -> FAQPage schema
  * every <img> with a real alt                 -> image entries in sitemap.xml

Run it after editing products, FAQ entries or image alt text:

    python3 tools/seo-sync.py

It reads index.html, rewrites the <script type="application/ld+json"> block
in place, and rewrites sitemap.xml. Nothing else in the page is touched.
"""

import datetime
import html
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://mamtasoapworks.com/"
ORG = BASE + "#organization"

CATEGORIES = ["Washing Soap", "Dishwash Gel", "Fabric Cleaner", "Multipurpose Gel"]


def text_of(fragment: str) -> str:
    """Strip tags and entities from an HTML fragment -> normalised plain text."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def url_for(path: str) -> str:
    # image filenames contain literal spaces, so they must be percent-encoded
    return BASE + urllib.parse.quote(path)


def parse_products(src: str):
    products = []
    for cat, body in re.findall(
        r'<article class="product" data-cat="([^"]+)">(.*?)</article>', src, re.S
    ):
        products.append({
            "cat": html.unescape(cat),
            "img": re.search(r'<img src="([^"]+)"', body).group(1),
            "title": text_of(re.search(r'<h3 class="product__title">(.*?)</h3>', body, re.S).group(1)),
            "desc": text_of(re.search(r'<p class="product__desc">(.*?)</p>', body, re.S).group(1)),
            "specs": [text_of(x) for x in re.findall(r'<span class="spec">(.*?)</span>', body, re.S)],
        })
    return products


def parse_faqs(src: str):
    faqs = []
    for block in re.findall(r'<details class="faq__item"[^>]*>(.*?)</details>', src, re.S):
        faqs.append((
            text_of(re.search(r"<summary>(.*?)</summary>", block, re.S).group(1)),
            text_of(re.search(r'<div class="faq__answer">(.*?)</div>', block, re.S).group(1)),
        ))
    return faqs


def build_graph(products, faqs):
    org = {
        "@type": ["Organization", "LocalBusiness"],
        "@id": ORG,
        "name": "Mamta Soap Works",
        "alternateName": ["RK Soap", "RK Sabun", "Mamta Soap Works Ulhasnagar"],
        "description": (
            "Manufacturer of RK washing soap (sabun), concentrated dishwash gel, detergent "
            "powder and liquid fabric cleaner. Making Jain soap from plant-based oils in "
            "Ulhasnagar, Maharashtra since 1978."
        ),
        "slogan": "Stain Never Sustain",
        "foundingDate": "1978",
        "url": BASE,
        "logo": {"@type": "ImageObject", "url": url_for("images/logo-removebg.png")},
        "image": url_for("images/rk_soap.jpeg"),
        "email": "sunilkurseja@gmail.com",
        "telephone": "+91-251-2708650",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "Gajanand Compound, Dhobi Ghat Road, Opp. Sai Baba Mandir",
            "addressLocality": "Ulhasnagar",
            "addressRegion": "Maharashtra",
            "postalCode": "421001",
            "addressCountry": "IN",
        },
        "contactPoint": [{
            "@type": "ContactPoint",
            "contactType": "sales",
            "telephone": "+91-9860234087",
            "email": "sunilkurseja@gmail.com",
            "areaServed": "IN",
            "availableLanguage": ["en", "hi", "mr"],
        }],
        "areaServed": [
            {"@type": "State", "name": "Maharashtra"},
            {"@type": "Country", "name": "India"},
        ],
        "knowsAbout": [
            "washing soap manufacturing", "detergent powder", "dishwash gel",
            "fabric cleaner", "Jain soap", "RK sabun",
        ],
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "RK cleaning product range",
            "itemListElement": [{"@type": "OfferCatalog", "name": c} for c in CATEGORIES],
        },
    }

    website = {
        "@type": "WebSite", "@id": BASE + "#website", "url": BASE,
        "name": "Mamta Soap Works", "inLanguage": "en-IN",
        "publisher": {"@id": ORG},
    }

    webpage = {
        "@type": "WebPage", "@id": BASE + "#webpage", "url": BASE,
        "name": "RK Sabun & Washing Soap Manufacturer, Ulhasnagar | Mamta Soap Works",
        "isPartOf": {"@id": BASE + "#website"},
        "about": {"@id": ORG},
        "inLanguage": "en-IN",
        "primaryImageOfPage": {"@type": "ImageObject", "url": url_for("images/rk_soap.jpeg")},
    }

    itemlist = {
        "@type": "ItemList", "@id": BASE + "#products",
        "name": "RK cleaning products by Mamta Soap Works",
        "numberOfItems": len(products),
        "itemListElement": [{
            "@type": "ListItem",
            "position": i,
            "item": {
                "@type": "Product",
                "name": "%s — %s" % (p["title"], p["specs"][0]),
                "image": url_for(p["img"]),
                "description": p["desc"],
                "category": p["cat"],
                "brand": {"@type": "Brand", "name": "RK"},
                "manufacturer": {"@id": ORG},
                "offers": {
                    "@type": "Offer",
                    "url": BASE + "#products",
                    "availability": "https://schema.org/InStock",
                    "priceCurrency": "INR",
                    "seller": {"@id": ORG},
                },
            },
        } for i, p in enumerate(products, 1)],
    }

    faqpage = {
        "@type": "FAQPage", "@id": BASE + "#faq",
        "mainEntity": [{
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": a},
        } for q, a in faqs],
    }

    return {"@context": "https://schema.org",
            "@graph": [org, website, webpage, itemlist, faqpage]}


def write_sitemap(src: str) -> int:
    try:
        lastmod = subprocess.check_output(
            ["git", "log", "-1", "--format=%cs"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL).strip()
        datetime.date.fromisoformat(lastmod)
    except Exception:
        lastmod = datetime.date.today().isoformat()

    images, seen = [], set()
    for m in re.finditer(r'<img[^>]+src="(images/[^"]+)"[^>]*>', src):
        tag, path = m.group(0), m.group(1)
        if path in seen:
            continue
        seen.add(path)
        alt = re.search(r'alt="([^"]*)"', tag)
        alt = html.unescape(alt.group(1)) if alt else ""
        if alt.strip():
            images.append((path, alt))

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
           '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
           "  <url>", f"    <loc>{BASE}</loc>", f"    <lastmod>{lastmod}</lastmod>",
           "    <changefreq>monthly</changefreq>", "    <priority>1.0</priority>"]
    for path, alt in images:
        out += ["    <image:image>",
                f"      <image:loc>{BASE}{urllib.parse.quote(path)}</image:loc>",
                f"      <image:title>{html.escape(alt, quote=False)}</image:title>",
                "    </image:image>"]
    out += ["  </url>", "</urlset>", ""]
    SITEMAP.write_text("\n".join(out), encoding="utf-8")
    return len(images)


def main() -> int:
    src = PAGE.read_text(encoding="utf-8")

    products = parse_products(src)
    faqs = parse_faqs(src)
    if not products:
        print("error: no product cards found in index.html", file=sys.stderr)
        return 1
    if not faqs:
        print("error: no FAQ entries found in index.html", file=sys.stderr)
        return 1

    blob = json.dumps(build_graph(products, faqs), indent=2, ensure_ascii=False)
    block = ('  <script type="application/ld+json">\n'
             + "\n".join("  " + ln for ln in blob.splitlines())
             + "\n  </script>")

    existing = re.search(r'  <script type="application/ld\+json">.*?</script>', src, re.S)
    if not existing:
        print("error: no JSON-LD block to replace in index.html", file=sys.stderr)
        return 1

    PAGE.write_text(src[:existing.start()] + block + src[existing.end():], encoding="utf-8")
    n_images = write_sitemap(src)

    print(f"index.html  JSON-LD rebuilt: {len(products)} products, {len(faqs)} FAQ entries")
    print(f"sitemap.xml rebuilt: 1 URL, {n_images} images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
