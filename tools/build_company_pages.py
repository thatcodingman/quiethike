#!/usr/bin/env python3
"""Regenerates the vendor pages (salesforce.html, figma.html, ...) from
data/log-entries.json + data/vendors.json. Run from the repo root:
    python3 tools/build_company_pages.py
Also refreshes sitemap.xml."""
import json, html, datetime, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
entries = json.load(open(root/'data/log-entries.json', encoding='utf-8'))
vendors = json.load(open(root/'data/vendors.json', encoding='utf-8'))
comparisons = json.load(open(root/'data/comparisons.json', encoding='utf-8')) if (root/'data/comparisons.json').exists() else {}
e = html.escape
def nice(d):
    dt = datetime.date.fromisoformat(d); return dt.strftime('%b %-d, %Y')
GA = '''<script async src="https://www.googletagmanager.com/gtag/js?id=G-3KLNY8ZB2S"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag("js",new Date());gtag("config","G-3KLNY8ZB2S");</script>
<meta name="google-adsense-account" content="ca-pub-8828337552440063">'''
def render_entry(x, v):
    tagcls = 'tag-up' if any(t in x['tags'] for t in ('structural','increase')) else 'tag-down'
    vt = 'tag-partial' if 'disputed' in x['tags'] else 'tag-verified'
    src = ' · '.join(f'<a href="{e(s["url"])}" target="_blank" rel="noopener" style="color: var(--accent);">{e(s["name"])}</a> [{e(s["type"])}]' for s in x['sources'])
    note = f'<p class="log-body"><strong>Disputed figure:</strong> {e(x["disputed_note"])}</p>' if x.get('disputed_note') else ''
    corr = f'<p class="log-body"><strong>Correction:</strong> {e(x["correction_note"])}</p>' if x.get('correction_note') else ''
    takeaway = f'<p class="entry-takeaway"><span class="takeaway-label">What this means:</span> {e(x["takeaway"])}</p>' if x.get('takeaway') else ''
    return f'''      <article class="log-entry" id="{e(x["id"])}">
        <div class="log-meta">
          <span class="log-date">{e(x["date_display"])}</span>
          <span class="log-tag {tagcls}">{e(x["status_label"])}</span>
          <span class="log-tag {vt}">{e(x["verification_label"])}</span>
          <span class="log-verified">Rechecked {nice(v["last_verified"])}</span>
        </div>
        <h3>{e(x["headline"])}</h3>
        <div class="diff-line diff-removed">- {e(x["old_price"])}</div>
        <div class="diff-line diff-added">+ {e(x["new_price"])}</div>
        {takeaway}
        <div class="entry-actions">
          <button type="button" class="action-btn copy-link-btn" data-entry-id="{e(x["id"])}">Copy link</button>
          <a class="action-btn" target="_blank" rel="noopener" href="#" data-share-id="{e(x["id"])}">Share on X</a>
        </div>
        <button type="button" class="evidence-toggle" aria-expanded="false">View evidence →</button>
        <div class="evidence-detail" hidden>
          <p class="log-body">{e(x["body"])}</p>
          {note}{corr}
          <p class="log-source">Sources: {src}</p>
          <p class="log-source"><a href="index.html#{e(x["id"])}" style="color: var(--accent);">See this entry on the main log →</a></p>
        </div>
      </article>'''
def rfc822(d):
    dt = datetime.date.fromisoformat(d)
    return dt.strftime('%a, %d %b %Y 12:00:00 GMT')
def rss_for_vendor(v):
    xs = sorted([x for x in entries if x['company']==v['match']], key=lambda x: x['date_logged'], reverse=True)
    url = f'https://quiethike.com/{v["slug"]}.html'
    feed_url = f'https://quiethike.com/{v["slug"]}-rss.xml'
    build_date = rfc822(max(x['date_logged'] for x in xs)) if xs else rfc822(v['last_verified'])
    def item(x):
        link = f'{url}#{x["id"]}'
        return f'''  <item>
    <title>{e(x["headline"])}</title>
    <link>{link}</link>
    <guid isPermaLink="true">{link}</guid>
    <pubDate>{rfc822(x["date_logged"])}</pubDate>
    <description>{e(x["body"])}</description>
  </item>'''
    items = '\n\n'.join(item(x) for x in xs)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>QuietHike — {e(v["name"])} Price Changes</title>
  <link>{url}</link>
  <description>Every {e(v["name"])} pricing change QuietHike has caught and verified, and nothing else.</description>
  <language>en-us</language>
  <lastBuildDate>{build_date}</lastBuildDate>
  <atom:link href="{feed_url}" rel="self" type="application/rss+xml" />

{items}

</channel>
</rss>
'''
def related_vendors_block(v):
    others = [o for o in vendors if o['slug'] != v['slug']]
    if not others:
        return ''
    rows = '\n'.join(f'''          <tr>
            <th scope="row"><a href="{o["slug"]}.html">{e(o["name"])}</a></th>
            <td>{e(o["tracks"])}</td>
            <td class="snap-price">{e(o["current"])}</td>
            <td class="snap-date">{nice(o["last_verified"])}</td>
          </tr>''' for o in others)
    return f'''  <section class="section">
    <div class="wrap">
      <div class="section-head"><h2>Also tracking</h2><p>Other vendors on QuietHike, and their current verified price.</p></div>
      <div class="snap-wrap">
        <table class="snap-table">
          <thead><tr><th scope="col">Vendor</th><th scope="col">Tracking</th><th scope="col">Current price</th><th scope="col">Last rechecked</th></tr></thead>
          <tbody>
{rows}
          </tbody>
        </table>
      </div>
    </div>
  </section>
'''

def render_compare(c):
    cols = c['columns']
    head = ''.join(f'<th scope="col">{e(col)}</th>' for col in cols)
    def rowhtml(r):
        cells = ''.join(f'<td>{e(v)}</td>' for v in r['values'])
        return f'<tr><th scope="row">{e(r["label"])}</th>{cells}</tr>'
    rows = '\n          '.join(rowhtml(r) for r in c['rows'])
    foot = f'<p class="log-source" style="margin-top:14px;">{e(c["footnote"])}</p>' if c.get('footnote') else ''
    return f'''  <section class="section" style="padding-top:0;">
    <div class="wrap">
      <div class="section-head">
        <p class="eyebrow">Compare</p>
        <h2>{e(c["title"])}</h2>
        <p>{e(c["intro"])}</p>
      </div>
      <div class="snap-wrap">
        <table class="snap-table compare-table">
          <thead><tr><th scope="col"></th>{head}</tr></thead>
          <tbody>
          {rows}
          </tbody>
        </table>
      </div>
      {foot}
    </div>
  </section>
'''
def page(v):
    xs = sorted([x for x in entries if x['company']==v['match']], key=lambda x: (x['date_logged'], ), reverse=True)
    n = len(xs)
    title = f'{v["name"]} Price Changes &amp; History — QuietHike'
    desc = f'{v["name"]} pricing changes, verified against the vendor\'s own pages. {n} logged change{"s" if n!=1 else ""}; current: {v["current"]}. Last rechecked {nice(v["last_verified"])}.'
    url = f'https://quiethike.com/{v["slug"]}.html'
    ld_items = ','.join(json.dumps({"@type":"ListItem","position":i+1,"url":f'{url}#{x["id"]}',"item":{"@type":"Article","headline":x["headline"],"datePublished":x["date_logged"],"dateModified":v["last_verified"],"author":{"@type":"Organization","name":"QuietHike"},"publisher":{"@type":"Organization","name":"QuietHike"}}}, ensure_ascii=False) for i,x in enumerate(xs))
    bc = json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"QuietHike","item":"https://quiethike.com/"},{"@type":"ListItem","position":2,"name":f'{v["name"]} price changes',"item":url}]}, ensure_ascii=False)
    compare_block = render_compare(comparisons[v['slug']]) if v['slug'] in comparisons else ''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:site_name" content="QuietHike">
<meta property="og:image" content="https://quiethike.com/{v["slug"]}-og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(v["name"])} current price — QuietHike">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://quiethike.com/{v["slug"]}-og.png">
<meta name="theme-color" content="#131d1a">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="QuietHike — Price Change Log" href="https://quiethike.com/rss.xml">
<link rel="alternate" type="application/rss+xml" title="QuietHike — {e(v["name"])} Price Changes" href="https://quiethike.com/{v["slug"]}-rss.xml">
{GA}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="quiethike-styles.css">
<script type="application/ld+json">{bc}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"ItemList","name":"{e(v["name"])} price changes","itemListElement":[{ld_items}]}}</script>
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header">
  <div class="wrap">
    <a href="index.html" class="logo"><span class="mark">▲▼</span> QuietHike</a>
    <nav class="main-nav">
      <a href="index.html#log">All changes</a>
      <a href="index.html#snapshot">Prices</a>
      <a href="timeline.html">Timeline</a>
      <a href="index.html#methodology">How we verify</a>
      <a href="index.html#subscribe">Subscribe</a>
    </nav>
  </div>
</header>
<main id="main-content">
  <section class="page-hero">
    <div class="wrap">
      <p class="crumbs"><a href="index.html">QuietHike</a> / {e(v["name"])}</p>
      <h1>{e(v["name"])} price changes</h1>
      <p>{e(v["blurb"])}</p>
      <div class="vendor-now">
        <span class="vendor-now-label">Tracking: {e(v["tracks"])}</span>
        <span class="vendor-now-price">{e(v["current"])}</span>
        <span class="log-verified">Last rechecked {nice(v["last_verified"])}</span>
      </div>
      <p class="log-source" style="margin-top:12px;"><a href="{v["slug"]}-rss.xml" style="color: var(--accent);">Follow only {e(v["name"])} (RSS) →</a></p>
    </div>
  </section>
{compare_block}  <section class="section">
    <div class="wrap">
      <div class="section-head"><h2>History ({n} logged {"changes" if n!=1 else "change"})</h2><p>Newest first. Each entry stays as the historical record; later changes are added as new entries.</p></div>
      <div class="log-list">
{chr(10).join(render_entry(x, v) for x in xs)}
      </div>
      <p class="log-source" style="margin-top:28px;"><a href="index.html" style="color: var(--accent);">← Back to all price changes</a> · <a href="rss.xml" style="color: var(--accent);">RSS</a></p>
    </div>
  </section>
{related_vendors_block(v)}</main>
<footer>
  <div class="wrap foot-grid">
    <p class="foot-disclosure">QuietHike logs publicly verifiable pricing changes. We are not affiliated with, and do not receive payment from, any vendor mentioned. Confirm current pricing directly with each vendor before purchasing.</p>
    <nav class="foot-links">
      <a href="index.html#log">This week</a>
      <a href="timeline.html">Timeline</a>
      <a href="index.html#methodology">Methodology</a>
      <a href="index.html#faq">FAQ</a>
      <a href="corrections.html">Corrections</a>
      <a href="suggest.html">Suggest a vendor</a>
      <a href="terms.html">Terms</a>
      <a href="privacy.html">Privacy</a>
      <a href="rss.xml">RSS</a>
    </nav>
  </div>
</footer>
<script>
document.querySelectorAll('.copy-link-btn').forEach(function (btn) {{
  btn.addEventListener('click', function () {{
    var id = btn.getAttribute('data-entry-id');
    var url = location.origin + location.pathname + '#' + id;
    var reset = function () {{ btn.textContent = 'Copy link'; }};
    var done = function () {{ btn.textContent = 'Copied!'; setTimeout(reset, 1500); }};
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(url).then(done).catch(function () {{ window.prompt('Copy this link:', url); }});
    }} else {{
      window.prompt('Copy this link:', url);
    }}
  }});
}});
document.querySelectorAll('[data-share-id]').forEach(function (a) {{
  var id = a.getAttribute('data-share-id');
  var article = document.getElementById(id);
  var headline = article ? article.querySelector('h3').textContent.trim() : 'A quiet pricing change, caught and verified.';
  var url = location.origin + location.pathname + '#' + id;
  var text = headline + ' — via @QuietHike';
  a.href = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text) + '&url=' + encodeURIComponent(url);
}});
document.querySelectorAll('.evidence-toggle').forEach(function (btn) {{
  btn.addEventListener('click', function () {{
    var d = btn.nextElementSibling, open = btn.getAttribute('aria-expanded') === 'true';
    d.hidden = open; btn.setAttribute('aria-expanded', String(!open));
    btn.textContent = open ? 'View evidence →' : 'Hide evidence ↑';
  }});
}});
if (location.hash) {{ var t = document.querySelector(location.hash); if (t) {{ var b = t.querySelector('.evidence-toggle'); if (b) b.click(); }} }}
</script>
</body>
</html>
'''
def timeline_page():
    slug_by_match = {v['match']: v['slug'] for v in vendors}
    xs = sorted(entries, key=lambda x: x['date_logged'], reverse=True)
    n = len(xs)
    url = 'https://quiethike.com/timeline.html'
    title = 'Full Timeline — QuietHike'
    desc = f'Every quiet pricing change QuietHike has logged and verified, in one chronological timeline. {n} entries across {len(vendors)} vendors.'
    def month_key(x):
        d = datetime.date.fromisoformat(x['date_logged'])
        return (d.year, d.month)
    def month_label(k):
        return datetime.date(k[0], k[1], 1).strftime('%B %Y')
    def item(x):
        tagcls = 'tl-up' if any(t in x['tags'] for t in ('structural','increase')) else 'tl-down'
        slug = slug_by_match.get(x['company'])
        href = f'{slug}.html#{e(x["id"])}' if slug else f'index.html#{e(x["id"])}'
        return f'''      <article class="timeline-item {tagcls}">
        <div class="timeline-head">
          <span class="timeline-vendor">{e(x["company"])}</span>
          <span class="timeline-date">{e(x["date_display"])}</span>
        </div>
        <h3><a href="{href}">{e(x["headline"])}</a></h3>
        <div class="diff-line diff-removed" style="margin-bottom:4px;">- {e(x["old_price"])}</div>
        <div class="diff-line diff-added">+ {e(x["new_price"])}</div>
      </article>'''
    groups = []
    last_key = None
    for x in xs:
        k = month_key(x)
        if k != last_key:
            groups.append(f'      <p class="timeline-month">{month_label(k)}</p>')
            last_key = k
        groups.append(item(x))
    body = '\n'.join(groups)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:site_name" content="QuietHike">
<meta property="og:image" content="https://quiethike.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#131d1a">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="QuietHike — Price Change Log" href="https://quiethike.com/rss.xml">
{GA}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="quiethike-styles.css">
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header">
  <div class="wrap">
    <a href="index.html" class="logo"><span class="mark">▲▼</span> QuietHike</a>
    <nav class="main-nav">
      <a href="index.html#snapshot">Prices</a>
      <a href="index.html#log">This week</a>
      <a href="timeline.html">Timeline</a>
      <a href="index.html#methodology">How we verify</a>
      <a href="index.html#subscribe">Subscribe</a>
    </nav>
  </div>
</header>
<main id="main-content">
  <section class="page-hero">
    <div class="wrap">
      <p class="crumbs"><a href="index.html">QuietHike</a> / Timeline</p>
      <h1>The full timeline</h1>
      <p>Every quiet pricing change we've caught and verified, newest first. {n} entries across {len(vendors)} vendors.</p>
    </div>
  </section>
  <section class="section">
    <div class="wrap">
      <div class="timeline-wrap">
{body}
      </div>
    </div>
  </section>
</main>
<footer>
  <div class="wrap foot-grid">
    <p class="foot-disclosure">QuietHike logs publicly verifiable pricing changes. We are not affiliated with, and do not receive payment from, any vendor mentioned. Confirm current pricing directly with each vendor before purchasing.</p>
    <nav class="foot-links">
      <a href="index.html#log">This week</a>
      <a href="timeline.html">Timeline</a>
      <a href="index.html#methodology">Methodology</a>
      <a href="index.html#faq">FAQ</a>
      <a href="corrections.html">Corrections</a>
      <a href="suggest.html">Suggest a vendor</a>
      <a href="terms.html">Terms</a>
      <a href="privacy.html">Privacy</a>
      <a href="rss.xml">RSS</a>
    </nav>
  </div>
</footer>
</body>
</html>
'''
def corrections_page():
    corrected = [x for x in entries if x.get('correction_note')]
    corrected.sort(key=lambda x: x['date_logged'], reverse=True)
    n = len(corrected)
    url = 'https://quiethike.com/corrections.html'
    title = 'Corrections — QuietHike'
    desc = f'Every correction QuietHike has made to a published entry, left visible with what changed and why. {n} correction{"s" if n!=1 else ""} on record.'
    def row(x):
        return f'''      <article class="log-entry" id="correction-{e(x["id"])}">
        <div class="log-meta">
          <span class="log-date">{e(x["date_display"])}</span>
          <span class="log-tag tag-partial">Correction</span>
        </div>
        <h3>{e(x["headline"])}</h3>
        <p class="log-body">{e(x["correction_note"])}</p>
        <p class="log-source"><a href="index.html#{e(x["id"])}" style="color: var(--accent);">See the corrected entry →</a></p>
      </article>'''
    if corrected:
        body = f'''      <div class="section-head"><h2>{n} correction{"s" if n!=1 else ""} on record</h2><p>Each one is left attached to the entry it corrects — nothing is quietly edited or removed.</p></div>
      <div class="log-list">
{chr(10).join(row(x) for x in corrected)}
      </div>'''
    else:
        body = '''      <div class="section-head"><h2>No corrections on record</h2><p>When we get something wrong, it will be logged here with what changed and why — nothing gets quietly edited or removed.</p></div>'''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:title" content="{title}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:site_name" content="QuietHike">
<meta property="og:image" content="https://quiethike.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#131d1a">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="QuietHike — Price Change Log" href="https://quiethike.com/rss.xml">
{GA}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<link rel="stylesheet" href="quiethike-styles.css">
</head>
<body>
<a href="#main-content" class="skip-link">Skip to main content</a>
<header class="site-header">
  <div class="wrap">
    <a href="index.html" class="logo"><span class="mark">▲▼</span> QuietHike</a>
    <nav class="main-nav">
      <a href="index.html#snapshot">Prices</a>
      <a href="index.html#log">All changes</a>
      <a href="timeline.html">Timeline</a>
      <a href="index.html#methodology">How we verify</a>
      <a href="index.html#subscribe">Subscribe</a>
    </nav>
  </div>
</header>
<main id="main-content">
  <section class="page-hero">
    <div class="wrap">
      <p class="crumbs"><a href="index.html">QuietHike</a> / Corrections</p>
      <h1>Corrections</h1>
      <p>QuietHike is only useful if it's accurate. When we publish something wrong, we don't quietly fix it and move on — the correction stays attached to the entry, and it's listed here too.</p>
    </div>
  </section>
  <section class="section">
    <div class="wrap">
{body}
    </div>
  </section>
</main>
<footer>
  <div class="wrap foot-grid">
    <p class="foot-disclosure">QuietHike logs publicly verifiable pricing changes. We are not affiliated with, and do not receive payment from, any vendor mentioned. Confirm current pricing directly with each vendor before purchasing.</p>
    <nav class="foot-links">
      <a href="index.html#log">This week</a>
      <a href="timeline.html">Timeline</a>
      <a href="index.html#methodology">Methodology</a>
      <a href="index.html#faq">FAQ</a>
      <a href="corrections.html">Corrections</a>
      <a href="suggest.html">Suggest a vendor</a>
      <a href="terms.html">Terms</a>
      <a href="privacy.html">Privacy</a>
      <a href="rss.xml">RSS</a>
    </nav>
  </div>
</footer>
</body>
</html>
'''

for v in vendors:
    (root/f'{v["slug"]}.html').write_text(page(v), encoding='utf-8')
    (root/f'{v["slug"]}-rss.xml').write_text(rss_for_vendor(v), encoding='utf-8')
(root/'corrections.html').write_text(corrections_page(), encoding='utf-8')
(root/'timeline.html').write_text(timeline_page(), encoding='utf-8')
today = max(v['last_verified'] for v in vendors)
urls = [('https://quiethike.com/', today, 'weekly', '1.0')] + \
       [(f'https://quiethike.com/{v["slug"]}.html', v['last_verified'], 'weekly', '0.8') for v in vendors] + \
       [('https://quiethike.com/timeline.html', today, 'weekly', '0.6')] + \
       [('https://quiethike.com/corrections.html', today, 'weekly', '0.4')] + \
       [('https://quiethike.com/suggest.html', today, 'monthly', '0.3')] + \
       [('https://quiethike.com/terms.html','2026-08-21','yearly','0.3'),('https://quiethike.com/privacy.html','2026-08-21','yearly','0.3')]
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{u}</loc><lastmod>{l}</lastmod><changefreq>{c}</changefreq><priority>{p}</priority></url>\n' for u,l,c,p in urls) + '</urlset>\n'
(root/'sitemap.xml').write_text(sm, encoding='utf-8')
print('built', len(vendors), 'vendor pages + corrections page + timeline page + sitemap')
