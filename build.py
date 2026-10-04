#!/usr/bin/env python3
"""Generate the static HTML for the Evolux GitHub Pages site.

Usage
-----
    python3 build.py

Writes the ten HTML pages into the repository root. Image dimensions are
read from ``assets/images/`` so every ``<img>`` carries intrinsic
width/height attributes and causes no layout shift, and ``srcset``
descriptors are emitted from true pixel widths rather than filename
suffixes.

The output is deterministic: running this against an unchanged checkout
reproduces the committed HTML byte for byte.

Requirements
------------
Python 3.9+ and Pillow, used only to read image dimensions:

    python3 -m pip install Pillow

Deployment does not need this script. GitHub Pages publishes the
committed static files as-is (legacy build), so ``build.py`` is a
developer tool for regenerating the pages after editing this source.

Inputs are confined to this repository: ``assets/images/`` for
dimensions and the constants below for content. There are no network
calls, no credentials and no dependency on private data.
"""
import pathlib, json, sys

# Repository root, resolved relative to this file so a fresh clone works
# from any location.
ROOT = pathlib.Path(__file__).resolve().parent
SITE = 'https://evoluxbrisbane.github.io'
BOOK = 'https://evolux.com.au/book-your-chauffeur'
BLOG = 'https://evoluxbrisbane.blogspot.com'
PHONE = '0478 191 042'
PHONE_HREF = '+6178191042'
EMAIL = 'info@evolux.com.au'

# ---------- image dimension map (prevents CLS) ----------
DIMS = {}
_images = list((ROOT / 'assets/images').glob('*.jpg'))
if _images:
    try:
        from PIL import Image
    except ImportError:
        sys.exit('FATAL: Pillow is required to read image dimensions.\n'
                 '       Install it with:  python3 -m pip install Pillow')
    for f in _images:
        with Image.open(f) as im:
            DIMS[f.name] = im.size

def _resolve(name):
    """Snap a requested filename to a real variant of the same base image."""
    if name in DIMS:
        return name
    base, _, ext = name.rpartition('-')
    cands = sorted(int(n.rsplit('-', 1)[1].rsplit('.', 1)[0])
                   for n in DIMS
                   if n.rsplit('-', 1)[0] == base
                   and n.rsplit('-', 1)[1].rsplit('.', 1)[0].isdigit())
    if not cands:
        raise SystemExit(f'FATAL: no image variants for base "{base}"')
    want = int(ext.rsplit('.', 1)[0]) if ext.rsplit('.', 1)[0].isdigit() else cands[-1]
    pick = min(cands, key=lambda c: (abs(c - want), c))
    return f'{base}-{pick}.jpg'


def img(name, alt, sizes='100vw', cls='', eager=False, w=0):
    """Responsive <img> with srcset, intrinsic size, alt, lazy loading."""
    name = _resolve(name)
    base = name.rsplit('-', 1)[0]
    # Sort by REAL pixel width. Filename suffixes are only labels: a variant
    # requested wider than its source was never upscaled, so "-1000" can be
    # a 718px file. Declaring the label as the w-descriptor makes browsers
    # over-select undersized images.
    variants = sorted(((n, DIMS[n][0]) for n in DIMS
                       if n.rsplit('-', 1)[0] == base
                       and n.rsplit('-', 1)[1].rsplit('.', 1)[0].isdigit()),
                      key=lambda t: t[1])
    target = min(w or DIMS[name][0], variants[-1][1])
    picked = [v for v in variants if v[1] <= target]
    nxt = [v for v in variants if v[1] > target]
    if nxt:
        picked.append(nxt[0])
    srcset = ', '.join(f'assets/images/{n} {tw}w' for n, tw in picked)
    iw, ih = DIMS[picked[-1][0]]
    parts = [f'<img src="assets/images/{name}"']
    parts.append(f'srcset="{srcset}"')
    parts.append(f'sizes="{sizes}"')
    parts.append(f'alt="{alt}"')
    parts.append(f'width="{iw}" height="{ih}"')
    parts.append('loading="eager" decoding="async" fetchpriority="high"' if eager
                 else 'loading="lazy" decoding="async"')
    if cls:
        parts.append(f'class="{cls}"')
    return ' '.join(parts) + '>'

ARROW = ('<svg class="arw" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="1.5" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" '
         'stroke-linecap="round" stroke-linejoin="round"/></svg>')

NAV = [('Chauffeur', 'chauffeur.html'), ('Airport', 'airport.html'),
       ('Fleet', 'fleet.html'), ('Corporate', 'corporate.html'),
       ('Weddings', 'weddings.html'), ('Journal', 'journal.html'),
       ('About', 'about.html')]

# ---------- shared chrome ----------
def header():
    items = ''.join(f'<li><a href="{h}">{t}</a></li>' for t, h in NAV)
    mitems = ''.join(
        f'<li><a href="{h}">{t}<span>0{i+1}</span></a></li>' for i, (t, h) in enumerate(NAV))
    return f'''<a class="skip-link" href="#main">Skip to main content</a>
<header class="hdr">
  <div class="wrap hdr__in">
    <a class="brand" href="{SITE}/" aria-label="Evolux — home">
      <span class="brand__mark">EVOLUX</span>
    </a>
    <nav class="nav" aria-label="Primary">
      <ul class="nav__list">{items}</ul>
    </nav>
    <a class="btn btn--solid btn--sm hdr__cta" href="{BOOK}">
      <span>Book Now</span>{ARROW}</a>
    <button class="burger" type="button" aria-expanded="false" aria-controls="mobnav" aria-label="Open menu">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>
<div class="mobnav" id="mobnav">
  <ul class="mobnav__list">{mitems}</ul>
  <div class="mobnav__foot">
    <a class="btn btn--solid" href="{BOOK}"><span>Book Now</span>{ARROW}</a>
    <a class="btn" href="tel:{PHONE_HREF}"><span>{PHONE}</span></a>
  </div>
</div>'''

def footer():
    nav = ''.join(f'<li><a href="{h}">{t}</a></li>' for t, h in NAV)
    svc = ''.join(f'<li><a href="{h}">{t}</a></li>' for t, h in [
        ('Airport Transfers', 'airport.html'), ('Corporate Chauffeur', 'corporate.html'),
        ('Weddings & Events', 'weddings.html'), ('Full-Day Chauffeur', 'chauffeur.html'),
        ('VIP & Event Transport', 'chauffeur.html'), ('Hourly Chauffeur', 'chauffeur.html')])
    return f'''<footer class="ftr">
  <div class="wrap">
    <div class="ftr__top">
      <div class="ftr__brand">
        <span class="brand__mark">EVOLUX</span>
        <p class="ftr__blurb">Luxury private chauffeur and executive transport across
          Brisbane and South East Queensland.</p>
        <p class="ftr__blurb" style="margin-top:18px">
          <a class="tlink" href="tel:{PHONE_HREF}" style="min-height:44px"><span>{PHONE}</span></a>
        </p>
      </div>
      <div>
        <h2 class="ftr__h">Explore</h2>
        <ul class="ftr__list">{nav}</ul>
      </div>
      <div>
        <h2 class="ftr__h">Services</h2>
        <ul class="ftr__list">{svc}</ul>
      </div>
      <div>
        <h2 class="ftr__h">Enquiries</h2>
        <ul class="ftr__list">
          <li><a href="tel:{PHONE_HREF}">{PHONE}</a></li>
          <li><a href="mailto:{EMAIL}">{EMAIL}</a></li>
          <li>Brisbane, Queensland</li>
          <li><a href="{BLOG}/">Evolux Journal</a></li>
          <li><a href="{BOOK}">Book your chauffeur</a></li>
        </ul>
      </div>
    </div>
    <div class="ftr__bottom">
      <p class="ftr__fine">&copy; <span data-year>2026</span> Evolux. Luxury private chauffeur
        &amp; executive transport, Brisbane and South East Queensland.</p>
      <div class="ftr__legal">
        <a href="{SITE}/about.html">About</a>
        <a href="{SITE}/contact.html">Contact</a>
        <a href="{BLOG}/">Journal</a>
        <a href="{SITE}/sitemap.xml">Sitemap</a>
      </div>
    </div>
  </div>
</footer>'''

def head(title, desc, path, og='og-image.png', extra_ld=''):
    canon = f'{SITE}/{path}' if path != 'index.html' else f'{SITE}/'
    ld = {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'Organization', '@id': f'{SITE}/#org', 'name': 'Evolux',
             'url': SITE, 'logo': f'{SITE}/assets/icons/icon-512.png',
             'email': EMAIL, 'telephone': PHONE,
             'description': 'Luxury private chauffeur and executive transport across Brisbane and South East Queensland.'},
            {'@type': 'LocalBusiness', '@id': f'{SITE}/#business', 'name': 'Evolux',
             'url': SITE, 'telephone': PHONE, 'email': EMAIL,
             'image': f'{SITE}/assets/icons/og-image.png',
             'logo': f'{SITE}/assets/icons/icon-512.png',
             'parentOrganization': {'@id': f'{SITE}/#org'},
             'address': {'@type': 'PostalAddress', 'addressLocality': 'Brisbane',
                         'addressRegion': 'Queensland', 'addressCountry': 'AU'},
             'areaServed': {'@type': 'State', 'name': 'Queensland'},
             'description': 'Luxury private chauffeur and executive transport across Brisbane and South East Queensland.'},
            {'@type': 'WebSite', '@id': f'{SITE}/#website', 'url': SITE, 'name': 'Evolux',
             'publisher': {'@id': f'{SITE}/#org'}, 'inLanguage': 'en-AU'},
            {'@type': 'WebPage', '@id': canon + '#webpage', 'url': canon, 'name': title,
             'description': desc, 'isPartOf': {'@id': f'{SITE}/#website'},
             'about': {'@id': f'{SITE}/#business'}, 'inLanguage': 'en-AU'},
        ] + ([json.loads(extra_ld)] if extra_ld else []),
    }
    return f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta name="theme-color" content="#0a0b0d">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Evolux">
<meta property="og:locale" content="en_AU">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/assets/icons/{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{SITE}/assets/icons/{og}">
<link rel="icon" href="assets/icons/favicon.svg" type="image/svg+xml">
<link rel="icon" href="assets/icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">
<link rel="manifest" href="manifest.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=Geist:wght@200;300;400;500&family=Instrument+Serif:ital@0;1&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@200;300;400;500&family=Instrument+Serif:ital@0;1&display=swap" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@200;300;400;500&family=Instrument+Serif:ital@0;1&display=swap"></noscript>
<link rel="stylesheet" href="css/theme.css">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'''

def page(path, title, desc, body, og='og-image.png', extra_ld=''):
    return f'''<!DOCTYPE html>
<html lang="en-AU">
<head>
{head(title, desc, path, og, extra_ld)}
</head>
<body>
{header()}
<main id="main">
{body}
</main>
{footer()}
<script src="js/main.js" defer></script>
</body>
</html>
'''

# ---------- reusable blocks ----------
SERVICES = [
    ('Airport Transfers', 'Door-to-door chauffeur transfers to and from Brisbane Airport and Gold Coast Airport, planned around your flight schedule.', 'airport.html'),
    ('Corporate Chauffeur', 'Executive transport for client meetings, site visits and airport runs across Brisbane and South East Queensland.', 'corporate.html'),
    ('Private Point-to-Point', 'A single, direct journey between two addresses — no waiting, no sharing, no unnecessary stops.', 'chauffeur.html'),
    ('Hourly Chauffeur', 'Chauffeur on hand by the hour for meetings, dining, shopping or a day of touring.', 'chauffeur.html'),
    ('Full-Day Chauffeur', 'A full day of availability for weddings, events and multi-stop itineraries.', 'chauffeur.html'),
    ('Wedding Chauffeur', 'Vehicles reserved for wedding parties, with discreet timing and an unhurried presence.', 'weddings.html'),
    ('VIP & Event Transport', 'Considered movement for VIP guests, private events and arrivals that need to be handled quietly.', 'weddings.html'),
]

def services_block(link=True):
    rows = []
    for i, (name, desc, href) in enumerate(SERVICES, 1):
        inner = f'<h3 class="svc__name">{name}</h3>'
        go = (f'<a class="svc__go" href="{href}" aria-label="Evolux {name}">'
              f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
              f'aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" stroke-linecap="round" '
              f'stroke-linejoin="round"/></svg></a>') if link else ''
        tag = 'a' if link else 'div'
        hrefattr = f' href="{href}"' if link else ''
        rows.append(
            f'<{tag} class="svc__row"{hrefattr} data-reveal>'
            f'<span class="svc__num">{i:02d}</span>{inner}'
            f'<p class="svc__desc">{desc}</p>{go}</{tag}>')
    return '<div class="svc">' + ''.join(rows) + '</div>'

VEHICLES = [
    ('BMW i7', 'fleet-business', 'Executive electric luxury',
     'Executive electric luxury for discreet corporate travel, airport transfers and VIP movements.'),
    ('Mercedes EQS', 'fleet-first', 'Electric saloon',
     'A quiet, seamless electric saloon suited to longer distances and executive transfers.'),
    ('Cadillac', 'fleet-business', 'Saloon',
     'A distinctive saloon presence for VIP and event arrivals.'),
    ('Genesis Electrified G80', 'fleet-first', 'Executive electric',
     'Executive electric comfort in a restrained and private form.'),
    ('Mercedes V-Class', 'fleet-van', 'Group travel',
     'Vehicle choice for group movements, family transfers and wedding parties.'),
]

def fleet_block(limit=None, sizes='(max-width:720px) 92vw, (max-width:1180px) 46vw, 31vw'):
    out = []
    for name, base, tag, desc in (VEHICLES[:limit] if limit else VEHICLES):
        out.append(f'''<article class="veh" data-reveal>
  <div class="veh__media">
    <span class="veh__tag">{tag}</span>
    {img(base + '-1000.jpg', f'{name} — Evolux chauffeur vehicle', sizes)}
  </div>
  <div class="veh__body">
    <h3 class="veh__name">{name}</h3>
    <p class="veh__desc">{desc}</p>
    <div class="veh__meta"><span>Brisbane &amp; SEQ</span><span>Chauffeur driven</span></div>
  </div>
</article>''')
    return '<div class="fleet">' + ''.join(out) + '</div>'

JOURNAL = [
    ('There are plenty of ways to travel from Brisbane to the Gold Coast — and only one of them feels like a holiday.',
     f'{BLOG}/2026/08/there-are-plenty-of-ways-to-travel-from.html', 'dest-gold-coast', 'Travel'),
    ('The Ultimate Luxury Visitor Guide to Brisbane',
     f'{BLOG}/2026/08/the-ultimate-luxury-visitor-guide-to.html', 'svc-hotel', 'City guide'),
    ('Experience the BMW i7 luxury chauffeur difference',
     f'{BLOG}/2026/08/experience-bmw-i7-luxury-chauffeur.html', 'fleet-first', 'The fleet'),
]

def journal_block(n=3):
    out = []
    for title, url, base, cat in JOURNAL[:n]:
        out.append(f'''<article class="jcard" data-reveal>
  <div class="jcard__media">{img(base + '-1000.jpg', title[:70], '(max-width:720px) 92vw, 31vw')}</div>
  <div class="jcard__body">
    <p class="jcard__meta">{cat} · Evolux Journal</p>
    <h3>{title}</h3>
    <a class="tlink" href="{url}"><span>Read the article</span>{ARROW}</a>
  </div>
</article>''')
    return '<div class="jour">' + ''.join(out) + '</div>'

def final_cta(title='Private chauffeur. Elevated.',
              sub='Discreet, door-to-door chauffeur service across Brisbane and South East Queensland.'):
    return f'''<section class="final band">
  <div class="final__bg">{img('hero-private-1800.jpg', '', '100vw', eager=True)}</div>
  <div class="final__scrim"></div>
  <div class="wrap final__in" data-reveal>
    <p class="eyebrow" style="justify-content:center">Evolux</p>
    <h2 class="display">{title}</h2>
    <p class="lede mx-auto">{sub}</p>
    <div class="final__cta">
      <a class="btn btn--solid" href="{BOOK}"><span>Book your chauffeur</span>{ARROW}</a>
      <a class="btn" href="tel:{PHONE_HREF}"><span>{PHONE}</span></a>
    </div>
  </div>
</section>'''

def ph(title, sub, image, alt, crumb=None):
    c = (f'<nav class="pagetop" aria-label="Breadcrumb"><ol class="crumbs">'
         f'<li><a href="{SITE}/">Home</a></li><li aria-hidden="true">/</li>'
         f'<li aria-current="page">{crumb or title}</li></ol></nav>') if True else ''
    return f'''<section class="phero">
  <div class="phero__bg">{img(image, alt, '100vw', eager=True)}</div>
  <div class="phero__scrim"></div>
  <div class="wrap">
    {c}
    <h1 class="display phero__title" data-reveal="line">{title}</h1>
    <p class="lede" data-reveal style="--d:120ms">{sub}</p>
    <div data-reveal style="--d:220ms">
      <a class="btn btn--solid" href="{BOOK}"><span>Book your chauffeur</span>{ARROW}</a>
    </div>
  </div>
</section>'''

def why_block():
    items = [
        ('Private by design', 'Your vehicle and chauffeur are set for your journey. One party, one driver, direct from your door to your destination.'),
        ('A considered fleet', 'Electric and premium saloon vehicles selected for quiet, comfortable and discreet travel.'),
        ('Brisbane &amp; SEQ knowledge', 'Local familiarity across Brisbane, the Gold Coast and the Sunshine Coast — and the routes between them.'),
        ('Unobtrusive service', 'Professional chauffeurs who arrive prepared, drive carefully and keep the experience calm.'),
        ('Airport aware', 'Airport transfers are planned around your flight schedule, with the vehicle set for your arrival.'),
        ('One point of contact', 'Enquiries, bookings and changes are handled directly by the Evolux team.'),
    ]
    ic = ('<svg class="why__ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="1.2" aria-hidden="true"><circle cx="12" cy="12" r="9"/>'
          '<path d="M12 7v5l3.5 2"/></svg>')
    cells = ''.join(f'<div class="why__item" data-reveal>{ic}<h3>{t}</h3><p>{d}</p></div>'
                    for t, d in items)
    return f'<div class="why">{cells}</div>'

def coverage_block():
    cells = [
        ('Brisbane', 'Luxury chauffeur service across the city and greater Brisbane.'),
        ('Brisbane CBD', 'Discreet corporate and executive transfers in the central business district.'),
        ('Brisbane Airport', 'Terminal transfers to and from Brisbane Airport.'),
        ('Gold Coast', 'Gold Coast chauffeur service for hotels, events and weekends away.'),
        ('Gold Coast Airport', 'Terminal transfers to and from Gold Coast Airport.'),
        ('Sunshine Coast', 'Sunshine Coast chauffeur transfers between the coast and Brisbane.'),
        ('South East Queensland', 'South East Queensland chauffeur journeys, arranged door to door.'),
    ]
    out = ''.join(f'''<a class="cover__cell" href="{SITE}/contact.html" data-reveal>
  <h3>{t}</h3><p>{d}</p>{ARROW}</a>''' for t, d in cells)
    return f'<div class="cover">{out}</div>'

# ---------- pages ----------
HOME_BODY = f'''<section class="hero">
  <div class="hero__bg">{img('hero-airport-1800.jpg', '', '100vw', eager=True, w=1800)}</div>
  <div class="hero__scrim"></div>
  <div class="hero__grid"></div>
  <div class="wrap hero__in">
    <p class="eyebrow" data-reveal>Brisbane &amp; South East Queensland</p>
    <h1 class="display hero__title" data-reveal="line" style="--d:80ms">
      Private Chauffeur.<br><em>Elevated.</em></h1>
    <p class="hero__sub" data-reveal style="--d:200ms">Discreet, door-to-door chauffeur service
      across Brisbane and South East Queensland.</p>
    <div class="hero__cta" data-reveal style="--d:300ms">
      <a class="btn btn--solid" href="{BOOK}"><span>Book your chauffeur</span>{ARROW}</a>
      <a class="btn" href="{SITE}/fleet.html"><span>Explore the fleet</span></a>
    </div>
  </div>
  <div class="hero__meta" aria-hidden="true">
    <span>Brisbane</span><span>Gold Coast</span><span>Sunshine Coast</span><span>South East Queensland</span>
  </div>
  <div class="scrollcue" aria-hidden="true"><i></i>Scroll</div>
</section>

<section class="band" id="introduction">
  <div class="wrap intro">
    <div class="intro__body">
      <p class="eyebrow" data-reveal>The Evolux approach</p>
      <h2 data-reveal style="--d:60ms">Travel, considered rather than arranged.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Evolux is a private chauffeur and executive transport service operating
          across Brisbane and South East Queensland. We keep the experience simple: a properly
          presented vehicle, a professional chauffeur, and a direct journey from your door to
          where you are going.</p>
        <p class="lede mt-24">Airport runs, corporate travel, weddings, events and everything
          in between are handled with the same restraint — because the point of private
          chauffeur travel is that you notice the comfort, not the logistics.</p>
        <p class="mt-32"><a class="tlink" href="{SITE}/about.html"><span>About Evolux</span>{ARROW}</a></p>
      </div>
    </div>
    <div class="intro__fig" data-reveal="scale" style="--d:120ms">
      {img('svc-private-1280.jpg', 'Evolux private chauffeur on the road in Brisbane', '(max-width:980px) 92vw, 42vw')}
    </div>
  </div>
</section>

<section class="band band--alt" id="services">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Services</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Transport arranged around your day.</h2>
        <p class="lede" data-reveal style="--d:140ms">Every journey is booked directly and driven
          by a professional chauffeur. Choose the service that matches the occasion.</p>
      </div>
    </div>
    {services_block()}
    <p class="mt-40" data-reveal><a class="btn" href="{SITE}/chauffeur.html"><span>All chauffeur services</span>{ARROW}</a></p>
  </div>
</section>

<section class="band" id="fleet">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>The fleet</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">A fleet chosen for quiet comfort.</h2>
        <p class="lede" data-reveal style="--d:140ms">Electric saloons and premium vehicles,
          selected so the cabin is calm, the ride is composed and the arrival is understated.</p>
      </div>
    </div>
    {fleet_block()}
    <p class="mt-40" data-reveal><a class="btn" href="{SITE}/fleet.html"><span>Explore the fleet</span>{ARROW}</a></p>
  </div>
</section>

<section class="band band--alt" id="coverage">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Where we drive</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Brisbane and South East Queensland.</h2>
        <p class="lede" data-reveal style="--d:140ms">From the CBD to the Gold Coast, the
          Sunshine Coast and the wider South East Queensland — door to door, on your schedule.</p>
      </div>
    </div>
    <div class="coverhero" data-reveal="scale">
      {img('dest-gold-coast-1440.jpg', 'Gold Coast, South East Queensland', '(max-width:720px) 92vw, 94vw', w=1440)}
      <div class="coverhero__cap">
        <h3>The Gold Coast and beyond</h3>
        <p>Coastal transfers between Brisbane, the Gold Coast and the Sunshine Coast, arranged
          as a single private journey.</p>
      </div>
    </div>
    <div class="mt-40">{coverage_block()}</div>
  </div>
</section>

<section class="band" id="airport">
  <div class="wrap split">
    <div class="split__media" data-reveal="left">
      {img('svc-airport-1280.jpg', 'Airport transfer with Evolux chauffeur', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Airport transfers</p>
      <h2 data-reveal style="--d:60ms">Brisbane Airport, handled.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Terminal transfers to and from Brisbane Airport, with the vehicle set for
          your arrival and your flight taken into account when the journey is planned.</p>
        <ul class="split__list">
          <li>Meet-and-greet style arrivals arranged around your flight schedule</li>
          <li>Direct transfers between Brisbane Airport and the CBD, Gold Coast or Sunshine Coast</li>
          <li>Executive and VIP movements for guests and clients</li>
          <li>Group and family transfers available</li>
        </ul>
        <a class="btn" href="{SITE}/airport.html"><span>Airport transfers</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>

<section class="band band--alt" id="corporate">
  <div class="wrap split split--flip">
    <div class="split__media" data-reveal="right">
      {img('svc-corporate-1280.jpg', 'Corporate chauffeur transport in Brisbane', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Corporate travel</p>
      <h2 data-reveal style="--d:60ms">Executive transport, kept professional.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Discreet chauffeur transport for client meetings, site visits, board
          movements and airport runs — a calm, punctual presence in a properly presented vehicle.</p>
        <ul class="split__list">
          <li>Point-to-point executive transfers across Brisbane and the CBD</li>
          <li>Recurring bookings and standing arrangements</li>
          <li>Hourly and full-day chauffeur availability</li>
          <li>VIP guest and event movement</li>
        </ul>
        <a class="btn" href="{SITE}/corporate.html"><span>Corporate chauffeur</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>

<section class="band" id="weddings">
  <div class="wrap split">
    <div class="split__media" data-reveal="left">
      {img('svc-weddings-1280.jpg', 'Wedding day chauffeur transport', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Weddings &amp; events</p>
      <h2 data-reveal style="--d:60ms">Days that run to plan.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Wedding and event chauffeur hire across Brisbane and South East
          Queensland, with vehicles reserved for the day and timings planned around the
          schedule that matters.</p>
        <ul class="split__list">
          <li>Vehicles reserved for wedding parties and family groups</li>
          <li>Full-day availability with the same chauffeur throughout</li>
          <li>Hotel, ceremony and reception transfers coordinated in advance</li>
          <li>VIP and event transport available as an addition</li>
        </ul>
        <a class="btn" href="{SITE}/weddings.html"><span>Weddings &amp; events</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>

<section class="band band--alt" id="why">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Why Evolux</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Restrained, reliable, private.</h2>
        <p class="lede" data-reveal style="--d:140ms">The things that matter when the vehicle is
          reserved for you alone.</p>
      </div>
    </div>
    {why_block()}
  </div>
</section>

<section class="band" id="journal">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>The Evolux journal</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Notes on travel and chauffeur service.</h2>
        <p class="lede" data-reveal style="--d:140ms">City guides, fleet notes and practical
          writing from the Evolux journal.</p>
      </div>
    </div>
    {journal_block()}
    <p class="mt-40" data-reveal><a class="btn" href="{BLOG}/" rel="noopener"><span>Read the Evolux journal</span>{ARROW}</a></p>
  </div>
</section>

{final_cta()}'''

CHAUFFEUR_BODY = ph('Chauffeur services.', 'Door-to-door chauffeur travel across Brisbane and South East Queensland — point-to-point, hourly, full-day, corporate, wedding and VIP movement.',
                    'svc-private-1280.jpg', 'Evolux private chauffeur', 'Chauffeur') + f'''
<section class="band">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Services</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Every kind of journey, booked directly.</h2>
        <p class="lede" data-reveal style="--d:140ms">Book by the journey or by the day. All
          services are arranged through Evolux and driven by a professional chauffeur.</p>
      </div>
    </div>
    {services_block()}
  </div>
</section>
<section class="band band--alt">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>How it works</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Three steps, no fuss.</h2>
        <p class="lede" data-reveal style="--d:140ms">Booking runs through the Evolux website.
          There is no booking engine on this site.</p>
      </div>
    </div>
    <div class="why">
      <div class="why__item" data-reveal><h3>01 — Enquire</h3><p>Tell us the date, the pickup
        address, the destination and how many guests are travelling.</p></div>
      <div class="why__item" data-reveal style="--d:100ms"><h3>02 — Confirm</h3><p>We confirm the
        vehicle and the arrangement, including flight details where relevant.</p></div>
      <div class="why__item" data-reveal style="--d:200ms"><h3>03 — Travel</h3><p>Your chauffeur
        arrives ahead of schedule and drives you door to door.</p></div>
    </div>
    <p class="mt-40" data-reveal><a class="btn btn--solid" href="{BOOK}"><span>Book your chauffeur</span>{ARROW}</a></p>
  </div>
</section>
{final_cta('Wherever Brisbane takes you.', 'Point-to-point, hourly or full-day chauffeur travel, arranged door to door.')}'''

AIRPORT_BODY = ph('Brisbane Airport transfers.', 'Private chauffeur transfers to and from Brisbane Airport, planned around your flight and taken door to door.',
                  'svc-airport-1280.jpg', 'Brisbane Airport chauffeur transfer', 'Airport') + f'''
<section class="band">
  <div class="wrap split">
    <div class="split__media" data-reveal="left">
      {img('hero-airport-1280.jpg', 'Airport transfer with Evolux chauffeur', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Brisbane Airport</p>
      <h2 data-reveal style="--d:60ms">Arrivals and departures, handled.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Airport chauffeur transfers are arranged around the flight schedule you
          provide, so the vehicle is waiting when you need it and the return is planned with the
          departure in mind.</p>
        <ul class="split__list">
          <li>Terminal transfers to and from Brisbane Airport (BNE)</li>
          <li>Direct journeys to the Brisbane CBD, Gold Coast and Sunshine Coast</li>
          <li>Executive and VIP movements for arriving clients and guests</li>
          <li>Group and family transfers available on request</li>
        </ul>
        <a class="btn btn--solid" href="{BOOK}"><span>Book an airport transfer</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>
<section class="band band--alt">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Also served</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Gold Coast Airport transfers.</h2>
        <p class="lede" data-reveal style="--d:140ms">Private chauffeur transfers to and from
          Gold Coast Airport, connecting directly to Brisbane, the Gold Coast and the Sunshine
          Coast.</p>
      </div>
    </div>
    <div class="cover">
      <a class="cover__cell" href="{SITE}/contact.html" data-reveal><h3>Brisbane Airport</h3>
        <p>Terminal transfers in both directions, planned around your flight.</p>{ARROW}</a>
      <a class="cover__cell" href="{SITE}/contact.html" data-reveal style="--d:80ms"><h3>Gold Coast Airport</h3>
        <p>Transfers to and from Gold Coast Airport across South East Queensland.</p>{ARROW}</a>
      <a class="cover__cell" href="{SITE}/contact.html" data-reveal style="--d:160ms"><h3>CBD &amp; hotels</h3>
        <p>Direct journeys from the airport to Brisbane CBD, hotels and residences.</p>{ARROW}</a>
      <a class="cover__cell" href="{SITE}/contact.html" data-reveal style="--d:240ms"><h3>Corporate arrivals</h3>
        <p>Standing arrangements for clients and guests arriving into Brisbane.</p>{ARROW}</a>
    </div>
  </div>
</section>
{final_cta('Smooth arrivals, every time.', 'Airport chauffeur transfers across Brisbane, the Gold Coast and the Sunshine Coast.')}'''

FLEET_BODY = ph('The fleet.', 'Electric saloons and premium vehicles for executive, airport, wedding and VIP chauffeur travel in Brisbane.',
                'fleet-first-1000.jpg', 'Evolux chauffeur fleet', 'Fleet') + f'''
<section class="band">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Confirmed fleet</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Vehicles selected for calm, private travel.</h2>
        <p class="lede" data-reveal style="--d:140ms">Every vehicle is chauffeur driven and
          prepared for your journey. Availability is confirmed when you book.</p>
      </div>
    </div>
    {fleet_block(sizes='(max-width:720px) 92vw, (max-width:1180px) 46vw, 31vw')}
  </div>
</section>
<section class="band band--alt">
  <div class="wrap split">
    <div class="split__media" data-reveal="left">
      {img('fleet-business-1000.jpg', 'Evolux executive saloon', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Choosing a vehicle</p>
      <h2 data-reveal style="--d:60ms">Matched to the occasion.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Executive saloons and electric models suit corporate and airport travel.
          Larger vehicles suit groups, families and wedding parties. Tell us the occasion and we
          will confirm the vehicle.</p>
        <ul class="split__list">
          <li>Executive and electric saloons for corporate and airport transfers</li>
          <li>Saloon options for VIP and event arrivals</li>
          <li>Larger vehicles for group and wedding party travel</li>
          <li>Vehicle confirmed at the time of booking</li>
        </ul>
        <a class="btn btn--solid" href="{BOOK}"><span>Book your chauffeur</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>
{final_cta()}'''

CORPORATE_BODY = ph('Corporate chauffeur.', 'Executive chauffeur transport for client meetings, airport runs, VIP movement and recurring bookings across Brisbane and South East Queensland.',
                    'svc-corporate-1280.jpg', 'Corporate chauffeur transport', 'Corporate') + f'''
<section class="band">
  <div class="wrap split">
    <div class="split__media" data-reveal="left">
      {img('svc-corporate-1280.jpg', 'Executive chauffeur in Brisbane', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Corporate travel</p>
      <h2 data-reveal style="--d:60ms">Professional transport for business travel.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Evolux provides chauffeur transport for businesses and individuals who
          need punctual, discreet movement between meetings, airports and venues across Brisbane
          and the wider South East Queensland.</p>
        <ul class="split__list">
          <li>Point-to-point executive transfers across Brisbane and the CBD</li>
          <li>Client, board and site-visit movements</li>
          <li>Recurring and standing chauffeur arrangements</li>
          <li>Airport transfers aligned to flight schedules</li>
          <li>VIP guest movement for events and site visits</li>
        </ul>
        <a class="btn btn--solid" href="{BOOK}"><span>Book corporate transport</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>
<section class="band band--alt">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Suitability</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Where corporate chauffeur travel fits.</h2>
      </div>
    </div>
    <div class="cover">
      <div class="cover__cell" data-reveal><h3>Client meetings</h3><p>Direct transfers between
        offices, venues and hotels with time to spare.</p></div>
      <div class="cover__cell" data-reveal style="--d:80ms"><h3>Airport runs</h3><p>Transfers
        timed against flight schedules, including arrivals and departures.</p></div>
      <div class="cover__cell" data-reveal style="--d:160ms"><h3>Site visits</h3><p>Multi-stop
        itineraries kept on schedule by an hourly or full-day chauffeur.</p></div>
      <div class="cover__cell" data-reveal style="--d:240ms"><h3>Events &amp; VIP guests</h3><p>
        Discreet arrival and departure arrangements for hosted guests and VIPs.</p></div>
    </div>
  </div>
</section>
{final_cta('Executive travel, kept simple.', 'Corporate chauffeur transport across Brisbane and South East Queensland.')}'''

WEDDINGS_BODY = ph('Weddings &amp; events.', 'Wedding day and event chauffeur hire across Brisbane and South East Queensland, with vehicles reserved for the day.',
                   'svc-weddings-1280.jpg', 'Wedding day chauffeur', 'Weddings') + f'''
<section class="band">
  <div class="wrap split">
    <div class="split__media" data-reveal="left">
      {img('svc-weddings-1280.jpg', 'Wedding day chauffeur transport', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Weddings</p>
      <h2 data-reveal style="--d:60ms">Wedding day chauffeur hire.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Vehicles reserved for wedding parties, with the day's timings planned in
          advance so departures, arrivals and transfers run to the schedule you have set.</p>
        <ul class="split__list">
          <li>Vehicles reserved for the wedding party and family groups</li>
          <li>Full-day availability with a consistent chauffeur</li>
          <li>Hotel, ceremony and reception transfers coordinated in advance</li>
          <li>Timings held against your run sheet and adjusted as needed</li>
        </ul>
        <a class="btn btn--solid" href="{BOOK}"><span>Enquire about wedding hire</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>
<section class="band band--alt">
  <div class="wrap split split--flip">
    <div class="split__media" data-reveal="right">
      {img('svc-vip-1280.jpg', 'VIP and event transport', '(max-width:980px) 92vw, 46vw')}
    </div>
    <div class="split__body">
      <p class="eyebrow" data-reveal>Events &amp; VIP</p>
      <h2 data-reveal style="--d:60ms">VIP and event transport.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Considered movement for private events, hosted guests and VIP arrivals —
          chauffeur driven, discreet, and arranged to fit the run of the day rather than
          interrupt it.</p>
        <ul class="split__list">
          <li>VIP and guest arrivals and departures</li>
          <li>Private events and hospitality movements</li>
          <li>Multi-stop itineraries for groups and families</li>
          <li>Hourly and full-day availability</li>
        </ul>
        <a class="btn" href="{BOOK}"><span>Book VIP transport</span>{ARROW}</a>
      </div>
    </div>
  </div>
</section>
{final_cta('Days worth doing properly.', 'Wedding and event chauffeur hire across Brisbane and South East Queensland.')}'''

ABOUT_BODY = ph('About Evolux.', 'Evolux is a private chauffeur and executive transport service operating across Brisbane and South East Queensland.',
                'svc-hotel-1280.jpg', 'Evolux chauffeur service', 'About') + f'''
<section class="band">
  <div class="wrap intro">
    <div class="intro__body">
      <p class="eyebrow" data-reveal>Who we are</p>
      <h2 data-reveal style="--d:60ms">A Brisbane chauffeur service, built around discretion.</h2>
      <div data-reveal style="--d:140ms">
        <p class="lede">Evolux provides private chauffeur and executive transport across Brisbane
          and South East Queensland. The service covers airport transfers, corporate travel,
          point-to-point journeys, hourly and full-day hire, weddings, events and VIP movement.</p>
        <p class="lede mt-24">We keep the operation deliberately simple. Vehicles are prepared,
          chauffeurs are professional, and journeys are planned around your schedule rather than
          a route sheet. Nothing is sold beyond the transport itself.</p>
      </div>
    </div>
    <div class="intro__fig" data-reveal="scale" style="--d:120ms">
      {img('svc-hotel-1280.jpg', 'Evolux chauffeur on the Gold Coast', '(max-width:980px) 92vw, 42vw')}
    </div>
  </div>
</section>
<section class="band band--alt">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>What to expect</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Restrained, reliable, private.</h2>
      </div>
    </div>
    {why_block()}
  </div>
</section>
<section class="band">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Coverage</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Where Evolux operates.</h2>
      </div>
    </div>
    {coverage_block()}
  </div>
</section>
{final_cta()}'''

JOURNAL_BODY = ph('The Evolux journal.', 'Travel writing, city guides and fleet notes from the Evolux journal.',
                  'dest-sunshine-coast-1440.jpg', 'South East Queensland coastline', 'Journal') + f'''
<section class="band">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Journal</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Read the Evolux journal.</h2>
        <p class="lede" data-reveal style="--d:140ms">Guides to Brisbane, the Gold Coast and the
          Sunshine Coast, along with notes on chauffeur travel and the vehicles in the Evolux
          fleet. The journal is published on the Evolux blog.</p>
      </div>
    </div>
    {journal_block()}
  </div>
</section>
<section class="band band--alt">
  <div class="wrap center">
    <div data-reveal>
      <p class="eyebrow" style="justify-content:center">Continue reading</p>
      <h2 style="margin-bottom:22px">The full journal lives on the Evolux blog.</h2>
      <p class="lede mx-auto" style="margin-bottom:36px">Every article is published on the
        Evolux blog, alongside booking and chauffeur enquiry details.</p>
      <a class="btn btn--solid" href="{BLOG}/" rel="noopener"><span>Explore the Evolux journal</span>{ARROW}</a>
    </div>
  </div>
</section>
{final_cta()}'''

CONTACT_BODY = ph('Contact.', 'Speak to Evolux about chauffeur bookings, airport transfers, corporate travel, weddings and events across Brisbane and South East Queensland.',
                  'svc-vip-1280.jpg', 'Evolux chauffeur vehicle', 'Contact') + f'''
<section class="band">
  <div class="wrap">
    <div class="shead">
      <p class="eyebrow" data-reveal>Get in touch</p>
      <div class="shead__row">
        <h2 data-reveal style="--d:60ms">Speak to the Evolux team.</h2>
        <p class="lede" data-reveal style="--d:140ms">Call or email with your date, pickup
          address, destination and group size. Bookings are completed securely on the official
          Evolux website.</p>
      </div>
    </div>
    <div class="contactgrid">
      <div class="cbox" data-reveal>
        <svg class="cbox__ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><path d="M4 5c0 8.3 6.7 15 15 15v-3.2l-4-1.6-2 2a12.6 12.6 0 0 1-6.2-6.2l2-2L7.2 5H4Z"/></svg>
        <h3>Phone</h3>
        <a class="tel" href="tel:{PHONE_HREF}">{PHONE}</a>
        <p>Direct enquiries with the Evolux team.</p>
      </div>
      <div class="cbox" data-reveal style="--d:80ms">
        <svg class="cbox__ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="m3 7 9 6 9-6"/></svg>
        <h3>Email</h3>
        <a class="mailto" href="mailto:{EMAIL}">{EMAIL}</a>
        <p>Send date, pickup, destination and group size.</p>
      </div>
      <div class="cbox" data-reveal style="--d:160ms">
        <svg class="cbox__ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z"/><circle cx="12" cy="10" r="2.6"/></svg>
        <h3>Location</h3>
        <p><strong>Evolux</strong><br>Brisbane, Queensland<br>Australia</p>
        <p>Serving Brisbane and South East Queensland.</p>
      </div>
      <div class="cbox" data-reveal style="--d:240ms">
        <svg class="cbox__ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true"><rect x="4" y="9" width="16" height="11" rx="1.5"/><path d="M8 9V6.5A4 4 0 0 1 16 6.5V9"/></svg>
        <h3>Online booking</h3>
        <p>Chauffeur bookings are completed securely on the official Evolux website.</p>
        <a class="btn btn--sm btn--solid mt-8" href="{BOOK}"><span>Book now</span>{ARROW}</a>
      </div>
    </div>
    <p class="mt-40 small muted" data-reveal>No booking form, payment form or reservation engine
      is hosted on this website. All bookings are completed on {SITE.replace(SITE, 'the official Evolux website')}.</p>
  </div>
</section>
{final_cta()}'''

NOTFOUND_BODY = f'''<section class="hero" style="min-height:78svh">
  <div class="hero__bg">{img('hero-private-1800.jpg', '', '100vw', eager=True)}</div>
  <div class="hero__scrim"></div>
  <div class="wrap hero__in">
    <p class="eyebrow" data-reveal>Error 404</p>
    <h1 class="display hero__title" data-reveal="line" style="--d:80ms">This page has<br><em>moved on.</em></h1>
    <p class="hero__sub" data-reveal style="--d:180ms">The page you are looking for is not here.
      Continue to the homepage, or speak to the Evolux team.</p>
    <div class="hero__cta" data-reveal style="--d:260ms">
      <a class="btn btn--solid" href="{SITE}/"><span>Back to homepage</span>{ARROW}</a>
      <a class="btn" href="tel:{PHONE_HREF}"><span>{PHONE}</span></a>
    </div>
  </div>
</section>
<section class="band band--tight">
  <div class="wrap">
    <div class="shead"><p class="eyebrow">Explore</p>
      <div class="shead__row"><h2>Popular destinations</h2></div></div>
    <div class="cover">
      <a class="cover__cell" href="{SITE}/fleet.html"><h3>Fleet</h3><p>The Evolux chauffeur fleet.</p>{ARROW}</a>
      <a class="cover__cell" href="{SITE}/airport.html"><h3>Airport transfers</h3><p>Brisbane and Gold Coast Airport.</p>{ARROW}</a>
      <a class="cover__cell" href="{SITE}/corporate.html"><h3>Corporate</h3><p>Executive chauffeur transport.</p>{ARROW}</a>
      <a class="cover__cell" href="{SITE}/contact.html"><h3>Contact</h3><p>Speak to the Evolux team.</p>{ARROW}</a>
    </div>
  </div>
</section>'''

PAGES = [
    ('index.html', 'Evolux — Luxury Private Chauffeur & Executive Transport in Brisbane',
     'Evolux provides luxury private chauffeur and executive transport across Brisbane and South East Queensland. Airport transfers, corporate travel, weddings, events and VIP chauffeur service.',
     HOME_BODY),
    ('chauffeur.html', 'Chauffeur Services — Brisbane & South East Queensland | Evolux',
     'Point-to-point, hourly, full-day, airport, corporate, wedding and VIP chauffeur services across Brisbane and South East Queensland. Book directly with Evolux.',
     CHAUFFEUR_BODY),
    ('airport.html', 'Brisbane Airport Chauffeur Transfers | Evolux',
     'Private Brisbane Airport chauffeur transfers to and from Brisbane Airport and Gold Coast Airport, planned around your flight and taken door to door.',
     AIRPORT_BODY),
    ('fleet.html', 'Chauffeur Fleet — BMW i7, Mercedes EQS, Cadillac, Genesis | Evolux',
     'The Evolux chauffeur fleet: BMW i7, Mercedes EQS, Cadillac, Genesis Electrified G80 and Mercedes V-Class, available for executive, airport, wedding and VIP travel in Brisbane.',
     FLEET_BODY),
    ('corporate.html', 'Corporate Chauffeur & Executive Transport in Brisbane | Evolux',
     'Corporate chauffeur and executive transport in Brisbane — client meetings, airport runs, site visits, VIP movement and recurring chauffeur bookings.',
     CORPORATE_BODY),
    ('weddings.html', 'Wedding & Event Chauffeur Hire in Brisbane | Evolux',
     'Wedding day and event chauffeur hire across Brisbane and South East Queensland, plus VIP and event transport for private occasions.',
     WEDDINGS_BODY),
    ('about.html', 'About Evolux — Private Chauffeur in Brisbane',
     'Evolux is a private chauffeur and executive transport service across Brisbane and South East Queensland, covering airport transfers, corporate travel, weddings and VIP movement.',
     ABOUT_BODY),
    ('journal.html', 'The Evolux Journal — Brisbane Travel & Chauffeur Guides',
     'Travel writing, Brisbane and South East Queensland city guides, and notes on chauffeur travel and the Evolux fleet.',
     JOURNAL_BODY),
    ('contact.html', 'Contact Evolux — Brisbane Private Chauffeur',
     f'Contact Evolux about chauffeur bookings across Brisbane and South East Queensland. Phone {PHONE}. Email {EMAIL}. Bookings completed securely on the official Evolux website.',
     CONTACT_BODY),
    ('404.html', 'Page Not Found | Evolux',
     'The page you are looking for is not available. Return to the Evolux homepage or contact the team.',
     NOTFOUND_BODY),
]

for fn, title, desc, body in PAGES:
    ld = ''
    if fn != 'index.html':
        crumb = [x for x in PAGES if x[0] == fn][0][1].split('—')[0].strip().rstrip('.').replace('&amp;', '&')
        ld = json.dumps({
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': crumb,
                 'item': f'{SITE}/{fn}'}]})
    (ROOT / fn).write_text(page(fn, title, desc, body, extra_ld=ld), encoding='utf-8')
    print(f'  wrote {fn:18} {(ROOT/fn).stat().st_size//1024:>4} KB')

print('\ndone.')
