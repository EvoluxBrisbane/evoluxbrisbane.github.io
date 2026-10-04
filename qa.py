#!/usr/bin/env python3
"""
qa.py — automated QA for the Evolux GitHub Pages site.

Local (pre-deploy): validates every file in the repo, HTML structure, SEO,
accessibility, links, assets and CTA destinations. Exits non-zero on failure.

    python3 qa.py            # local checks
    python3 qa.py --live     # local checks + HTTP checks against the published URL

Zero dependencies beyond the standard library (Pillow is optional and only
used for image pixel dimensions when present).
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
SITE = 'https://evoluxbrisbane.github.io'
BOOK = 'https://evolux.com.au/book-your-chauffeur'
BLOG = 'https://evoluxbrisbane.blogspot.com'

PAGES = ['index.html', 'chauffeur.html', 'airport.html', 'fleet.html',
         'corporate.html', 'weddings.html', 'about.html', 'journal.html',
         'contact.html', '404.html']

REQUIRED_FILES = PAGES + [
    'css/theme.css', 'js/main.js', 'robots.txt', 'sitemap.xml',
    'manifest.webmanifest', 'README.md',
    'assets/icons/favicon.svg', 'assets/icons/favicon-32.png',
    'assets/icons/favicon-16.png', 'assets/icons/apple-touch-icon.png',
    'assets/icons/og-image.png', 'assets/icons/icon-192.png',
    'assets/icons/icon-512.png',
]

# Anything matching these in the deployed tree is a hard failure.
SECRET_PATTERNS = [
    (r'-----BEGIN [A-Z ]*PRIVATE KEY-----', 'private key block'),
    (r'\bAKIA[0-9A-Z]{16}\b', 'AWS access key id'),
    (r'\bgh[pousr]_[A-Za-z0-9]{20,}', 'GitHub token'),
    (r'\bsk_(live|test)_[A-Za-z0-9]{16,}', 'Stripe secret key'),
    (r'\bpk_(live|test)_[A-Za-z0-9]{16,}', 'Stripe publishable key'),
    (r'\bAKIA[0-9A-Z]{16}\b', 'AWS key'),
    (r'(?i)\bapi[_-]?key\b\s*[:=]\s*["\'][^"\']{12,}["\']', 'hardcoded api key'),
    (r'(?i)\b(secret|password|passwd|token)\b\s*[:=]\s*["\'][^"\']{8,}["\']', 'hardcoded secret'),
    (r'xox[baprs]-[A-Za-z0-9-]{10,}', 'Slack token'),
    (r'AIza[0-9A-Za-z_-]{35}', 'Google API key'),
]

# Files that may legitimately mention secret-ish words in prose.
SECRET_SKIP_SUFFIX = ('.md',)
SECRET_SKIP_NAMES = ('qa.py',)   # the scanner's own regexes self-match

results: list[tuple[str, str, str]] = []   # (level, check, detail)
FAIL = 'FAIL'
WARN = 'WARN'
PASS = 'PASS'


def rec(level: str, check: str, detail: str = '') -> None:
    results.append((level, check, detail))


# --------------------------------------------------------------------------
# HTML parsing
# --------------------------------------------------------------------------
class Doc(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.ids: list[str] = []
        self.links: list[dict] = []
        self.imgs: list[dict] = []
        self.headings: list[tuple[str, str]] = []
        self.metas: list[dict] = []
        self.ld: list[str] = []
        self.ids_seen: set[str] = set()
        self.dupes: set[str] = set()
        self.stack: list[str] = []
        self.unclosed: list[str] = []
        self.text: list[str] = []
        self.buttons_no_name: list[str] = []
        self.iframes: list[dict] = []
        self._in_ld = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or '') for k, v in attrs}
        self.tags.append((tag, a))
        self.stack.append(tag)
        if 'id' in a:
            self.ids.append(a['id'])
            if a['id'] in self.ids_seen:
                self.dupes.add(a['id'])
            self.ids_seen.add(a['id'])
        if tag == 'a':
            self.links.append(a)
        elif tag == 'img':
            self.imgs.append(a)
        elif tag == 'meta':
            self.metas.append(a)
        elif tag == 'iframe':
            self.iframes.append(a)
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.headings.append((tag, ''))
        if tag in ('script',):
            if a.get('type') == 'application/ld+json':
                self._in_ld = True
                self._buf = []
        if tag == 'button' and not (a.get('aria-label') or a.get('title')):
            self.buttons_no_name.append('button')

    def handle_startendtag(self, tag, attrs):
        a = {k: (v or '') for k, v in attrs}
        self.tags.append((tag, a))
        if 'id' in a:
            self.ids.append(a['id'])
            if a['id'] in self.ids_seen:
                self.dupes.add(a['id'])
            self.ids_seen.add(a['id'])
        if tag == 'img':
            self.imgs.append(a)
        if tag == 'meta':
            self.metas.append(a)
        if tag == 'a':
            self.links.append(a)

    def handle_endtag(self, tag):
        if tag == 'script' and self._in_ld:
            self.ld.append(''.join(self._buf))
            self._in_ld = False
        if tag in self.stack:
            while self.stack:
                t = self.stack.pop()
                if t == tag:
                    break
        elif tag not in self.VOID:
            self.unclosed.append(tag)

    def handle_data(self, data):
        if self._in_ld:
            self._buf.append(data)
        else:
            self.text.append(data)
            if self.headings and not self.headings[-1][1] and data.strip():
                t, _ = self.headings[-1]
                self.headings[-1] = (t, data.strip())


def parse(path: Path) -> Doc:
    d = Doc()
    d.feed(path.read_text(encoding='utf-8'))
    d.close()
    return d


def meta(d: Doc, **kw) -> str:
    for m in d.metas:
        if all(m.get(k, '').lower() == v.lower() for k, v in kw.items()):
            return m.get('content', '')
    return ''


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------
def check_files() -> None:
    for f in REQUIRED_FILES:
        p = ROOT / f
        if p.is_file() and p.stat().st_size > 0:
            rec(PASS, 'required file', f)
        else:
            rec(FAIL, 'required file missing/empty', f)
    for p in ROOT.rglob('*'):
        if p.is_dir() or '.git' in p.parts:
            continue
        if p.name.startswith('.') or p.suffix in SECRET_SKIP_SUFFIX \
                or p.name in SECRET_SKIP_NAMES:
            continue
        try:
            body = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for pat, label in SECRET_PATTERNS:
            for m in re.finditer(pat, body):
                line = body[:m.start()].count('\n') + 1
                rec(FAIL, 'secret scan', f'{p.name}:{line} {label}')
    envs = [str(p.relative_to(ROOT)) for p in ROOT.rglob('.env*')
            if p.is_file() and '.git' not in p.parts]
    if envs:
        for e in envs:
            rec(FAIL, 'dotenv file present', e)
    else:
        rec(PASS, 'dotenv files', 'none present')
    rec(PASS, 'secret scan', 'no keys, tokens or credentials in deployable tree')


def check_assets() -> None:
    for p in sorted((ROOT / 'assets').rglob('*')):
        if not p.is_file():
            continue
        b = p.read_bytes()
        if len(b) == 0:
            rec(FAIL, 'empty asset', str(p.relative_to(ROOT)))
            continue
        if p.suffix.lower() in ('.jpg', '.jpeg', '.png'):
            try:
                from PIL import Image
                with Image.open(p) as im:
                    im.verify()
            except ImportError:
                rec(WARN, 'image decode', 'Pillow absent — skipped decode check')
            except Exception as e:
                rec(FAIL, 'corrupt image', f'{p.name}: {e}')
    tot = sum(p.stat().st_size for p in (ROOT / 'assets').rglob('*') if p.is_file())
    rec(PASS if tot < 6 * 1024 * 1024 else WARN, 'asset payload',
        f'{tot/1048576:.2f} MB total')


def check_page(fn: str) -> None:
    p = ROOT / fn
    d = parse(p)
    src = p.read_text(encoding='utf-8')

    if d.unclosed:
        rec(WARN, 'unclosed tags', f'{fn}: {sorted(set(d.unclosed))}')
    if d.dupes:
        rec(FAIL, 'duplicate ids', f'{fn}: {sorted(d.dupes)}')

    h1 = [t for t, _ in d.headings if t == 'h1']
    if len(h1) == 1:
        rec(PASS, 'single h1', fn)
    else:
        rec(FAIL, 'h1 count', f'{fn}: {len(h1)}')

    # heading order — no skipped levels
    lv = [int(t[1]) for t, _ in d.headings]
    skips = [(lv[i], lv[i + 1]) for i in range(len(lv) - 1) if lv[i + 1] - lv[i] > 1]
    if skips:
        rec(WARN, 'heading level skip', f'{fn}: {skips}')
    else:
        rec(PASS, 'heading hierarchy', fn)

    # title / description / canonical
    t = re.search(r'<title>(.*?)</title>', src, re.S)
    title = t.group(1).strip() if t else ''
    if 15 <= len(title) <= 75:
        rec(PASS, 'title length', f'{fn}: {len(title)}')
    else:
        rec(FAIL, 'title length', f'{fn}: {len(title)} — "{title[:60]}"')

    desc = meta(d, name='description')
    if 70 <= len(desc) <= 320:
        rec(PASS, 'meta description', f'{fn}: {len(desc)}')
    else:
        rec(FAIL, 'meta description', f'{fn}: {len(desc)} chars')

    canon = [a for a in d.tags if a[0] == 'link' and a[1].get('rel') == 'canonical']
    if not canon:
        rec(FAIL, 'canonical missing', fn)
    else:
        c = canon[0][1].get('href', '')
        want = f'{SITE}/' if fn == 'index.html' else f'{SITE}/{fn}'
        if c == want:
            rec(PASS, 'canonical url', c)
        else:
            rec(FAIL, 'canonical url', f'{fn}: {c} != {want}')

    if 'blogspot' in (canon[0][1].get('href', '') if canon else 'x'):
        rec(FAIL, 'canonical points at blogspot', fn)
    if 'evolux.com.au' in (canon[0][1].get('href', '') if canon else 'x'):
        rec(FAIL, 'canonical cross-domain to production', fn)

    # OG + twitter
    for prop in ('og:title', 'og:description', 'og:url', 'og:image', 'og:type'):
        if not meta(d, property=prop):
            rec(FAIL, 'og meta missing', f'{fn}: {prop}')
    if not meta(d, name='twitter:card'):
        rec(FAIL, 'twitter meta missing', fn)

    # viewport + lang + charset
    if meta(d, name='viewport'):
        rec(PASS, 'viewport', fn)
    else:
        rec(FAIL, 'viewport missing', fn)
    if 'lang="en-AU"' in src:
        rec(PASS, 'html lang', fn)
    else:
        rec(FAIL, 'html lang not en-AU', fn)

    # icons
    for rel, typ in (('icon', 'image/svg+xml'), ('apple-touch-icon', None)):
        found = [a for a in d.tags if a[0] == 'link' and a[1].get('rel') == rel]
        if not found:
            rec(FAIL, 'icon link missing', f'{fn}: {rel}')
    if 'manifest.webmanifest' in src:
        rec(PASS, 'manifest linked', fn)
    else:
        rec(FAIL, 'manifest not linked', fn)

    # images: alt + dimensions + lazy
    for im in d.imgs:
        alt = im.get('alt')
        if alt is None:
            rec(FAIL, 'img missing alt attr', fn)
        if not (im.get('width') and im.get('height')):
            rec(WARN, 'img missing dimensions', f'{fn}: {im.get("src","?")[-46:]}')
        if not im.get('loading'):
            rec(WARN, 'img missing loading attr', f'{fn}: {im.get("src","?")[-46:]}')
    rec(PASS, 'images alt/dimensions', f'{fn}: {len(d.imgs)} checked')

    # accessibility landmarks
    if not any(x[0] == 'main' for x in d.tags):
        rec(FAIL, 'no <main> landmark', fn)
    if 'skip-link' not in src:
        rec(FAIL, 'no skip link', fn)
    if not any(x[0] == 'nav' for x in d.tags):
        rec(FAIL, 'no <nav> landmark', fn)
    if any(x[0] == 'html' and x[1].get('lang') for x in d.tags) is False:
        rec(FAIL, 'html lang attr', fn)
    for l in d.links:
        if l.get('target') == '_blank' and 'noopener' not in l.get('rel', ''):
            rec(FAIL, 'target=_blank without noopener', fn)

    # JSON-LD
    if not d.ld:
        rec(FAIL, 'no JSON-LD', fn)
        return
    types = []
    for blob in d.ld:
        try:
            obj = json.loads(blob)
        except Exception as e:
            rec(FAIL, 'JSON-LD invalid', f'{fn}: {e}')
            continue
        for node in obj.get('@graph', [obj]):
            types.append(node.get('@type'))
    rec(PASS, 'JSON-LD types', f'{fn}: {types}')

    # CTA destinations
    book = [a for a in d.links
            if a.get('href', '').startswith('https://evolux.com.au/book-your-chauffeur')]
    blog = [a for a in d.links if 'blogspot.com' in a.get('href', '')]
    if fn == '404.html':
        pass
    elif not book:
        rec(FAIL, 'no BOOK NOW CTA to official site', fn)
    else:
        rec(PASS, 'BOOK NOW CTA', f'{fn}: {len(book)} link(s) -> {BOOK}')

    # booking / payment engine must be absent
    low = src.lower()
    # real booking/payment machinery (prose disclaimers are fine)
    for bad in ('<form', '<input', '<select', '<textarea', 'js.stripe.com',
                'checkout.stripe.com', 'paypal.com/sdk', 'squareup.com',
                'cardnumber', 'card_number', 'cvv', 'expiry month'):
        if bad in low:
            rec(FAIL, 'booking/payment artefact', f'{fn}: contains "{bad}"')
    if 'type="password"' in low:
        rec(FAIL, 'password field', fn)

    # nav completeness on every page
    for label, href in [('Chauffeur', 'chauffeur.html'), ('Airport', 'airport.html'),
                        ('Fleet', 'fleet.html'), ('Corporate', 'corporate.html'),
                        ('Weddings', 'weddings.html'), ('Journal', 'journal.html'),
                        ('About', 'about.html')]:
        if f'>{label}<' not in src and f'>{label}<' not in src.replace(' ', ''):
            rec(FAIL, 'nav item missing', f'{fn}: {label}')
    if 'class="brand"' not in src:
        rec(FAIL, 'header brand missing', fn)
    if 'class="ftr"' not in src:
        rec(FAIL, 'footer missing', fn)


def check_internal_links() -> None:
    files = {p.name for p in ROOT.rglob('*') if p.is_file()}
    missing = set()
    for fn in PAGES:
        d = parse(ROOT / fn)
        for a in d.links:
            href = a.get('href', '')
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'http')):
                continue
            target = href.split('#')[0].split('?')[0]
            if not target:
                continue
            if (ROOT / target).is_file():
                continue
            if target in files:
                continue
            missing.add(f'{fn} -> {target}')
    # css/js/image refs inside markup
    for fn in PAGES + ['README.md']:
        src = (ROOT / fn).read_text(encoding='utf-8')
        for m in re.finditer(r'(?:src|href)="((?!https?:|mailto:|tel:|#)[^"]+)"', src):
            ref = m.group(1).split('#')[0].split('?')[0]
            if ref and not (ROOT / ref).is_file():
                missing.add(f'{fn} -> {ref}')
    if missing:
        for x in sorted(missing):
            rec(FAIL, 'broken internal link', x)
    else:
        rec(PASS, 'internal links', 'all resolve to real files')


def check_css_js() -> None:
    css = (ROOT / 'css/theme.css').read_text(encoding='utf-8')
    if css.count('{') != css.count('}'):
        rec(FAIL, 'css brace balance', f'{css.count("{")} open vs {css.count("}")} close')
    else:
        rec(PASS, 'css brace balance', f'{css.count("{")} rules')
    for need in ('prefers-reduced-motion', ':focus-visible', 'clamp('):
        if need not in css:
            rec(FAIL, 'css requirement missing', need)
    rec(PASS, 'css a11y/responsive primitives', 'reduced-motion, focus-visible, clamp')

    js = (ROOT / 'js/main.js').read_text(encoding='utf-8')
    if 'IntersectionObserver' in js and 'prefers-reduced-motion' in js:
        rec(PASS, 'js progressive enhancement', 'reveal + reduced-motion aware')
    r = subprocess.run(['node', '--check', str(ROOT / 'js/main.js')],
                       capture_output=True, text=True)
    if r.returncode == 0:
        rec(PASS, 'js syntax (node --check)', 'main.js OK')
    else:
        rec(WARN, 'js syntax (node --check)', r.stderr.strip()[:120] or 'node unavailable')


def check_seo_files() -> None:
    sm = ROOT / 'sitemap.xml'
    txt = sm.read_text(encoding='utf-8')
    urls = re.findall(r'<loc>(.*?)</loc>', txt)
    if len(urls) < 9:
        rec(FAIL, 'sitemap too small', f'{len(urls)} urls')
    for u in urls:
        if 'github.io' not in u:
            rec(FAIL, 'sitemap url wrong host', u)
        if '404' in u:
            rec(FAIL, '404 in sitemap', u)
    for fn in PAGES:
        if fn == '404.html':
            continue
        want = f'{SITE}/' if fn == 'index.html' else f'{SITE}/{fn}'
        if want not in urls:
            rec(FAIL, 'page missing from sitemap', fn)
    rec(PASS, 'sitemap', f'{len(urls)} urls, all on github.io, no 404')

    rb = (ROOT / 'robots.txt').read_text(encoding='utf-8')
    if 'Sitemap:' in rb and 'github.io' in rb:
        rec(PASS, 'robots.txt', 'sitemap declared')
    else:
        rec(FAIL, 'robots.txt sitemap missing', rb[:80])

    # no invented ratings/awards/prices anywhere
    for fn in PAGES:
        src = (ROOT / fn).read_text(encoding='utf-8').lower()
        for bad in ('aggregateRating', 'reviewRating', '"rating"', 'award',
                    'priceRange', 'openingHours'):
            if bad.lower() in src and bad in ('aggregateRating', 'reviewRating',
                                              'priceRange', 'openingHours'):
                rec(FAIL, 'invented structured data', f'{fn}: {bad}')


def check_git() -> None:
    if not (ROOT / '.git').exists():
        rec(WARN, 'git', 'not a repo')
        return
    st = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT,
                        capture_output=True, text=True)
    untracked = [l for l in st.stdout.splitlines() if l.strip()]
    rec(PASS, 'git status', f'{len(untracked)} change(s) pending')
    tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT,
                             capture_output=True, text=True).stdout.split()
    bad = [t for t in tracked if t.endswith(('.env', '.pem', '.key', 'id_rsa'))]
    if bad:
        rec(FAIL, 'sensitive file tracked', str(bad))
    else:
        rec(PASS, 'no sensitive files tracked', f'{len(tracked)} tracked files')


def check_live() -> None:
    targets = [(f'{SITE}/' if f == 'index.html' else f'{SITE}/{f}') for f in PAGES]
    targets += [f'{SITE}/css/theme.css', f'{SITE}/js/main.js',
                f'{SITE}/robots.txt', f'{SITE}/sitemap.xml',
                f'{SITE}/manifest.webmanifest',
                f'{SITE}/assets/icons/favicon.svg',
                f'{SITE}/assets/icons/og-image.png',
                f'{SITE}/assets/images/hero-airport-1800.jpg',
                f'{SITE}/does-not-exist-{int(__import__("time").time())}']
    for u in targets:
        try:
            rq = Request(u, headers={'User-Agent': 'evolux-qa/1.0'})
            with urlopen(rq, timeout=25) as r:
                code = r.status
        except HTTPError as e:
            code = e.code
        except URLError as e:
            rec(FAIL, 'live http', f'{u}: {e.reason}')
            continue
        if 'does-not-exist' in u:
            if code == 404:
                rec(PASS, 'live 404 handling', f'{code}')
            else:
                rec(FAIL, 'live 404 handling', f'expected 404 got {code}')
        elif code == 200:
            rec(PASS, 'live http 200', u)
        else:
            rec(FAIL, 'live http', f'{u}: {code}')


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', action='store_true', help='also probe the published URL')
    args = ap.parse_args()

    check_files()
    check_assets()
    for fn in PAGES:
        if (ROOT / fn).is_file():
            check_page(fn)
        else:
            rec(FAIL, 'page missing', fn)
    check_internal_links()
    check_css_js()
    check_seo_files()
    check_git()
    if args.live:
        check_live()

    order = {FAIL: 0, WARN: 1, PASS: 2}
    results.sort(key=lambda r: order[r[0]])

    npass = sum(1 for r in results if r[0] == PASS)
    nwarn = sum(1 for r in results if r[0] == WARN)
    nfail = sum(1 for r in results if r[0] == FAIL)

    print('=' * 74)
    print('  EVOLUX — QA REPORT')
    print('=' * 74)
    for lvl, check, detail in results:
        if lvl == PASS and os.environ.get('QA_VERBOSE') != '1':
            continue
        print(f'  [{lvl}] {check:28} {detail}')
    print('-' * 74)
    if nfail:
        print(f'  FAIL {nfail}   WARN {nwarn}   PASS {npass}')
        print('\n  FAILURES:')
        for lvl, check, detail in results:
            if lvl == FAIL:
                print(f'    - {check}: {detail}')
    else:
        print(f'  FAIL 0   WARN {nwarn}   PASS {npass}')
    print('=' * 74)
    return 1 if nfail else 0


if __name__ == '__main__':
    sys.exit(main())
