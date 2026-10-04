# Evolux — GitHub Pages brand site

Luxury private chauffeur and executive transport across Brisbane and South East
Queensland. A free static site with **no runtime dependencies**, published at
**https://evoluxbrisbane.github.io/**

The only build-time dependency is Pillow, used solely to read image dimensions
when regenerating pages (see [Regenerating the pages](#regenerating-the-pages)).

This is a **secondary** Evolux property. It is deliberately separate from:

- https://www.evolux.com.au — official/main site (primary conversion destination)
- https://evoluxbrisbane.blogspot.com — Evolux Journal (Blogger)

Nothing in this repository modifies either of those properties.

## Cost

$0. Static HTML, CSS, vanilla JS, SVG, Google Fonts, GitHub Pages. No domain,
no hosting, no plugins, no paid APIs, no API keys, no booking or payment engine.

## Structure

```
index.html          homepage (12 sections)
chauffeur.html      chauffeur services
airport.html        Brisbane / Gold Coast Airport transfers
fleet.html          confirmed fleet
corporate.html      corporate & executive transport
weddings.html       weddings, events, VIP
about.html          about Evolux
journal.html        editorial index -> Evolux Journal
contact.html        phone / email (no form)
404.html            not found
css/theme.css       design system
js/main.js          progressive enhancement only
assets/images/      optimised responsive photography
assets/icons/       favicon, apple touch icon, OG image, PWA icons
robots.txt  sitemap.xml  manifest.webmanifest
qa.py                    QA harness (local + --live)
build.py                 regenerates the ten HTML pages from source
```

## Regenerating the pages

`build.py` is the source of truth for page content. It writes the ten HTML
files into the repository root.

```bash
python3 -m pip install Pillow   # only dependency, used to read image sizes
python3 build.py                # rewrites the ten .html files
```

Requirements: Python 3.9+ and [Pillow](https://pypi.org/project/Pillow/).
Pillow is used **only** to read pixel dimensions from `assets/images/`, which
gives every `<img>` intrinsic `width`/`height` (no layout shift) and lets
`srcset` descriptors be emitted from true pixel widths rather than filename
suffixes. The script exits with an install hint if Pillow is missing.

The output is deterministic. Running it against an unchanged checkout
reproduces the committed HTML **byte for byte**, from any path:

```bash
git clone https://github.com/EvoluxBrisbane/evoluxbrisbane.github.io.git
cd evoluxbrisbane.github.io && python3 build.py && git diff --exit-code
```

`build.py` reads nothing outside this repository, makes no network calls, and
contains no credentials. It does not depend on the production repository, the
Blogger site, or any private data.

**Editing pages:** change `build.py`, not the generated `.html` files. Re-run
it and commit both together. Hand-edited HTML will be overwritten on the next
run.

**Deployment does not use this script.** GitHub Pages publishes the committed
static files directly (legacy build, no pipeline), so the site deploys whether
or not `build.py` is ever executed. It is a developer convenience.

## Conversion model

`BOOK NOW` on every page links to the official site:
`https://evolux.com.au/book-your-chauffeur`

The Evolux Journal links to `https://evoluxbrisbane.blogspot.com`.

This site contains **no booking form, no payment form, no reservation engine,
no card fields and no third-party tracking.** Bookings complete on the
official Evolux site.

## Accessibility & performance

- Semantic landmarks, skip link, one `h1` per page, logical heading order
- Visible `:focus-visible` rings, ≥44px interactive targets
- `prefers-reduced-motion` fully honoured — the site is static without JS
- Responsive 375 / 390 / 430 / 768 / 1024 / 1280 / 1440
- Lazy-loaded, dimensioned responsive images with `srcset`/`sizes`
- CSS-first motion, no animation libraries

## QA

```bash
python3 qa.py           # local: files, HTML, SEO, a11y, links, secrets, git
python3 qa.py --live    # additionally probes the published URLs
```

Exit code is non-zero on any failure.

## Content integrity

Fleet (BMW i7, Mercedes EQS, Cadillac, Genesis Electrified G80, Mercedes V-Class)
is factual. No vehicle specifications, passenger or luggage capacities, awards,
testimonials, ratings, partnerships, certifications or statistics are claimed —
none are asserted anywhere in this repository.
