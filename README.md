# mamta-soap-website

Single-page marketing site for **Mamta Soap Works** — manufacturers of fabric washing soap,
dishwash detergent liquid, detergent powder and fabric cleaner in Ulhasnagar since 1978.
Deployed to `mamtasoapworks.com` via GitHub Pages from the `single_page` branch.

## Project structure

- **index.html** — the entire page: navbar, hero, marquee, about, "what sets us apart",
  process, product catalogue, FAQ, contact and footer, plus one inline `<script>` holding
  all behaviour and a JSON-LD structured-data block.
- **css/common.css** — the design system: colour/typography tokens, every component, the
  responsive breakpoints and the animation keyframes.
- **images/** — product photography, logo and favicon.
- **robots.txt** / **sitemap.xml** — served from the domain root by GitHub Pages.
- **tools/seo-sync.py** — optional helper that regenerates the JSON-LD and sitemap from
  the markup (see below).
- **tools/optimise-images.py** — downscales and recompresses the images the page uses.

## Running it locally

No build step and no dependencies to install:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

Use a server rather than opening `index.html` directly — relative asset paths and the CDN
font/icon links behave better over `http://`.

## Editing the product range

All thirteen products are written directly in `index.html` as `<article class="product">`
blocks inside `#productsGrid` — they are real markup so search engines index them without
running JavaScript. Copy an existing block and edit the image, title, description and the
two `<span class="spec">` pills. Copy image paths verbatim; several filenames contain
literal spaces.

Two things to update alongside it:

1. the filter chip count for that category in `#filters`;
2. the generated SEO data — run `python3 tools/seo-sync.py`.

## Keeping SEO data in sync

`tools/seo-sync.py` reads `index.html` and regenerates the JSON-LD block (Organization,
WebSite, WebPage, the 13-item product `ItemList` and the `FAQPage`) plus `sitemap.xml`.
Run it after changing products, FAQ entries or image alt text:

```bash
python3 tools/seo-sync.py
```

It is idempotent and edits nothing else. The site deploys correctly without it — it just
stops the structured data drifting away from the page.

## Adding a new product photo

The source photographs are print resolution; the page displays them a few hundred pixels
wide. After dropping a new image into `images/` and referencing it, run:

```bash
python3 tools/optimise-images.py --dry-run   # see what it would do
python3 tools/optimise-images.py             # apply
```

It downscales to a 1200 px long edge (enough for a retina lightbox), re-encodes, and
updates the `width`/`height` attributes in `index.html`. It never upscales and never
writes a file bigger than the one it started with, so running it twice is harmless.

This already ran once: the referenced images went from 9.6 MB to 1.3 MB with no visible
quality change, and `favicon.ico` from 207 KB to 5 KB.

## Contact form

The callback form posts directly to [formsubmit.co](https://formsubmit.co); there is no
backend. It validates the name, a 10-digit phone number and a non-empty query in the
browser, shows errors inline, and returns the visitor to `/?sent=1` for a success message.

## Notes

- No JavaScript frameworks — plain HTML, CSS and vanilla JS. The only external resources are
  Google Fonts (Fraunces + Plus Jakarta Sans) and the bootstrap-icons font.
- Content stays visible if JavaScript fails: the animated start states are gated behind a
  `.js` class that the script adds on startup.
- Animation is disabled automatically for visitors who set `prefers-reduced-motion`.
