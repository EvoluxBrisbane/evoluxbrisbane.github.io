# Evolux — GitHub Pages brand site

Luxury private chauffeur and executive transport across Brisbane and South East
Queensland. A free, dependency-free static site published at
**https://evoluxbrisbane.github.io/**

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
robots.txt  sitemap.xml  manifest.webmanifest  qa.py
```

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
