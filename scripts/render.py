"""
render.py — builds index.html from data/profile.json, data/projects.json and data/site.json.

Design: "Four-D programme" (v5.0.0). The page is a 4D construction programme, read like a
Navisworks TimeLiner or Primavera schedule:

  * A week ruler is fixed across the top and acts as the navigation. Every section is an activity
    bar on it (WBS code + name), and a data-date line slides along the ruler as you scroll
    (assets/js/main.js; hidden without JS).
  * Every section opens on an activity row: WBS code, duration, start and finish dates, and a
    Gantt bar that fills as the section comes into view.
  * The projects are a Gantt chart. Each project is a bar as long as the building is tall
    (G+41 = 42 floors), staggered like a real programme, with a preview that follows the cursor.
  * The build-ups are a sideways look-ahead strip, the BBS drawings are a submittal register,
    the featured project sits on the critical path and contact is the handover key date.

The permanent signature (signature.py) stays: the scroll stage is the first section in <main>
(full-bleed, "Mobilise"), and the skill cards are the "Trades" activity.

Pre-rendering (instead of fetching JSON in the browser) keeps the page fast, readable without
JavaScript and indexable. Every "open" control is a real link to the image or video, so without
JavaScript it still works; assets/js/main.js upgrades it to the viewer.

Data contract (unchanged): data/*.json shapes and build(), which writes index.html and
assets/css/tokens.css. Edit content in data/*.json, then run:  python3 scripts/portfolio.py build
"""
from __future__ import annotations

import datetime as dt
import json
import re
from html import escape
from pathlib import Path

import signature  # permanent signature sections (scroll stage + skill cards); see signature.py

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_URL = "https://zxaidman.github.io/Portfolio/"
CHANGELOG_URL = "https://github.com/Zxaidman/Portfolio/blob/main/CHANGELOG.md"
WEEKS = 24  # length of the programme on the ruler (matches --weeks in design/system.json)

# The programme: (anchor id, WBS code, activity name, start week, duration in weeks).
PHASES = [
    ("roof", "A1000", "Mobilise", 0, 2),
    ("featured", "A1010", "Critical path", 2, 2),
    ("projects", "A1020", "Structure", 4, 6),
    ("buildups", "A1030", "Sequencing", 9, 4),
    ("rebar", "A1040", "Reinforcement", 12, 3),
    ("skills", "A1050", "Trades", 14, 3),
    ("about", "A1060", "Resources", 16, 3),
    ("revisions", "A1070", "Baseline", 19, 3),
    ("contact", "M1080", "Handover", 22, 2),
]


def e(value) -> str:
    """HTML-escape any value (attribute-safe)."""
    return escape(str(value if value is not None else ""), quote=True)


def fmt_date(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


def programme_start(site: dict) -> dt.date:
    """Week 0 of the programme: the Monday of the week this version shipped."""
    try:
        day = dt.date.fromisoformat(site.get("date", ""))
    except ValueError:
        day = dt.date.today()
    return day - dt.timedelta(days=day.weekday())


def phase(anchor: str) -> tuple[str, str, str, int, int]:
    return next(p for p in PHASES if p[0] == anchor)


def storeys(title: str) -> int:
    """Floors above ground from a public title like 'G+41 luxury residential tower model'."""
    m = re.search(r"G\s*\+\s*(\d+)", title)
    return int(m.group(1)) + 1 if m else 5


def img_tag(im: dict, alt: str, cls: str = "", eager: bool = False, use_thumb: bool = False, sizes: str = "") -> str:
    src = im["thumb"] if use_thumb else im["src"]
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'
    srcset = f' srcset="{e(im["thumb"])} 720w, {e(im["src"])} 1800w" sizes="{e(sizes)}"' if sizes else ""
    cls_attr = f' class="{e(cls)}"' if cls else ""
    return (f'<img{cls_attr} src="{e(src)}"{srcset} alt="{e(alt)}" width="{im["w"]}" '
            f'height="{im["h"]}" decoding="async" {loading}>')


def opener(slug: str, href: str, inner: str, cls: str = "", index: int = 0, video: bool = False,
           label: str = "", extra: str = "") -> str:
    """A link to the media file that main.js upgrades into the viewer (works without JS)."""
    attrs = f' class="{e(cls)}"' if cls else ""
    attrs += f' aria-label="{e(label)}"' if label else ""
    attrs += " data-video" if video else ""
    return (f'<a href="{e(href)}"{attrs} data-open="{e(slug)}" data-index="{index}"{extra}>{inner}</a>')


def activity(anchor: str, title_id: str, title: str, note: str, start: dt.date, cls: str = "") -> str:
    """The activity row that opens each section: WBS cell, Gantt bar on the week grid, title."""
    _, code, name, s, d = phase(anchor)
    begin = start + dt.timedelta(weeks=s)
    finish = begin + dt.timedelta(weeks=d, days=-3)  # Friday of the last week
    keydate = code.startswith("M")
    note_html = f'<p class="act-note">{e(note)}</p>' if note else ""
    span = (f'<span class="act-diamond"></span>' if keydate
            else '<span class="act-bar"><span class="act-fill"></span></span>')
    return f"""<header class="act{(' ' + cls) if cls else ''}" style="--s:{s};--d:{d}">
    <p class="act-wbs mono"><span class="act-code">{e(code)}</span><span class="act-name">{e(name)}</span><span class="act-dur">{d} wk{"s" if d != 1 else ""}</span><span class="act-dates">{begin.strftime("%d %b")} &rarr; {finish.strftime("%d %b")}</span></p>
    <div class="act-chart" aria-hidden="true">{span}</div>
    <h2 id="{e(title_id)}" class="act-title">{e(title)}</h2>
    {note_html}
  </header>"""


# --------------------------------------------------------------------------- #
# Programme bar (navigation)
# --------------------------------------------------------------------------- #
def programme_bar(profile: dict, start: dt.date) -> str:
    items = "".join(
        f'<li style="--s:{s};--d:{d}"><a href="#{e(a)}" data-phase="{e(a)}" data-s="{s}" data-d="{d}">'
        f'<span class="pb-code">{e(code)}</span><span class="pb-name">{e(name)}</span></a></li>'
        for a, code, name, s, d in PHASES
    )
    weeks = "".join(f"<span>{w:02d}</span>" for w in range(1, WEEKS + 1, 2))
    return f"""<header class="prog" data-start="{start.isoformat()}">
  <a class="prog-mark" href="#roof" aria-label="{e(profile["name"])}, back to the start"><b>ZS</b><span>4D</span></a>
  <nav class="prog-nav" aria-label="Programme">
    <p class="prog-weeks mono" aria-hidden="true">{weeks}</p>
    <ol class="prog-track">{items}</ol>
    <span class="prog-dd" aria-hidden="true"></span>
  </nav>
  <p class="prog-readout mono" aria-hidden="true"><span>Data date</span><b data-readout>{start.strftime("%d %b")}</b></p>
</header>"""


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def critical_path(p: dict, start: dt.date) -> str:
    imgs = p["images"]
    thumbs = "".join(
        f'<li>{opener(p["slug"], im["src"], img_tag(im, "", use_thumb=True), "cp-thumb", index=i, label="Open view %d of %s" % (i + 1, p["title"]))}</li>'
        for i, im in enumerate(imgs[1:6], start=1)
    )
    video_btn = (opener(p["slug"], p["video"]["src"], f'Play the build-up <span class="mono">{e(p["video"]["duration"])}</span>',
                        "btn btn-line", video=True)) if p.get("video") else ""
    main_img = opener(p["slug"], imgs[0]["src"],
                      img_tag(imgs[0], p["title"] + " Revit model", sizes="(min-width: 900px) 60vw, 100vw"),
                      "cp-main", label=f'Open {p["title"]} gallery')
    floors = storeys(p["title"])
    return f"""
<section class="phase phase-critical" id="featured" aria-labelledby="featured-title">
  {activity("featured", "featured-title", "On the critical path today", "One project leads the programme. It changes twice a day.", start)}
  <div class="cp-grid">
    <figure class="cp-figure">{main_img}<figcaption class="mono"><span class="cp-flag">Critical</span> Sheet {e(p["sheet"])} &middot; {floors} floors</figcaption></figure>
    <div class="cp-copy">
      <p class="mono kicker">Activity {e(p["slug"].upper())}</p>
      <h3>{e(p["title"])}</h3>
      <dl class="cp-facts">
        <div><dt>Type</dt><dd>{e(p["kind"])}</dd></div>
        <div><dt>City</dt><dd>{e(p["location"] or "Not published")}</dd></div>
        <div><dt>Views</dt><dd>{len(imgs)}{" + build-up" if p.get("video") else ""}</dd></div>
      </dl>
      <p>{e(p["summary"])}</p>
      <div class="actions">
        {opener(p["slug"], imgs[0]["src"], f"Open all {len(imgs)} views", "btn btn-solid")}
        {video_btn}
      </div>
      <ul class="cp-thumbs">{thumbs}</ul>
    </div>
  </div>
</section>"""


def gantt(projects: list[dict], start: dt.date) -> str:
    counts: dict[str, int] = {}
    for p in projects:
        counts[p["type"]] = counts.get(p["type"], 0) + 1
    order = [t for t in ("Residential", "Commercial", "Other") if t in counts]
    filters = f'<button type="button" class="chip" aria-pressed="true" data-filter="all">All <span>{len(projects)}</span></button>'
    filters += "".join(
        f'<button type="button" class="chip" aria-pressed="false" data-filter="{e(t)}">{e(t)} <span>{counts[t]}</span></button>'
        for t in order
    )
    total = len(projects)
    tallest = max(storeys(p["title"]) for p in projects)
    rows = []
    for i, p in enumerate(projects):
        fl = storeys(p["title"])
        w = fl / tallest
        x = (i / max(total - 1, 1)) * (1 - w)  # staggered starts, like a real programme
        inner = (f'<span class="g-id mono">{e(p["slug"].upper())}</span>'
                 f'<span class="g-title">{e(p["title"])}</span>'
                 f'<span class="g-kind">{e(p["kind"])}</span>'
                 f'<span class="g-city mono">{e(p["location"] or "—")}</span>'
                 f'<span class="g-chart" aria-hidden="true"><span class="g-bar" style="--x:{x:.4f};--w:{w:.4f}">'
                 f'<span class="g-label mono">{fl} fl</span></span></span>'
                 f'<span class="g-thumb">{img_tag(p["images"][0], "", use_thumb=True)}</span>'
                 f'<span class="g-media mono">{len(p["images"])} views{" + build-up" if p.get("video") else ""}</span>')
        rows.append(f'<li class="g-row" data-type="{e(p["type"])}" style="view-transition-name:row-{e(p["slug"])}">'
                    f'{opener(p["slug"], p["images"][0]["src"], inner, "g-link", label=f"{p["title"]}: {fl} floors, {len(p["images"])} views", extra=f' data-thumb="{e(p["images"][0]["thumb"])}"')}</li>')
    scale = "".join(f'<span style="--at:{n / tallest:.4f}">{n}</span>' for n in range(0, tallest + 1, 10))
    return f"""
<section class="phase phase-gantt" id="projects" aria-labelledby="gantt-title">
  {activity("projects", "gantt-title", f"{total} projects on one programme", "Every project I modelled with the Computer Help BIM team. Each bar is as long as the building is tall. Open a row to walk its views.", start)}
  <div class="filters" role="group" aria-label="Filter projects by type">{filters}</div>
  <div class="gantt" style="--ten:{10 / tallest:.4f}">
    <p class="g-head mono" aria-hidden="true"><span class="gh-id">ID</span><span class="gh-title">Activity</span><span class="gh-city">City</span><span class="gh-media">Views</span><span class="g-scale">{scale}<span class="g-scale-unit">floors</span></span></p>
    <ol class="g-rows" aria-live="polite">{"".join(rows)}</ol>
  </div>
  <div class="g-preview" aria-hidden="true"></div>
</section>"""


def lookahead(projects_by_slug: dict, order: list[str], start: dt.date) -> str:
    cards = []
    n = 0
    for slug in order:
        p = projects_by_slug.get(slug)
        if not p or not p.get("video"):
            continue
        n += 1
        v = p["video"]
        poster = v.get("poster") or p["images"][0]["thumb"]
        wk = start + dt.timedelta(weeks=9 + (n - 1) % 4)
        inner = (f'<span class="la-media"><img src="{e(poster)}" alt="" loading="lazy" decoding="async">'
                 f'<video muted loop playsinline preload="none" data-src="{e(v["src"])}" tabindex="-1"></video>'
                 f'<span class="la-play" aria-hidden="true">&#9654;</span></span>'
                 f'<span class="la-cap"><span class="mono">Run {n:02d} &middot; w/c {wk.strftime("%d %b")}</span>'
                 f'<b>{e(p["title"])}</b><span class="mono la-dur">{e(v["duration"])}</span></span>')
        cards.append(f'<li class="la-card">{opener(slug, v["src"], inner, "la-link", video=True, label="Play the %s build-up" % p["title"])}</li>')
    return f"""
<section class="phase phase-lookahead" id="buildups" aria-labelledby="la-title">
  {activity("buildups", "la-title", "Four-week look-ahead", "Construction-sequence animations rendered from the Revit models, run by run. Hover to preview, open to watch with sound.", start)}
  <div class="la-controls" hidden>
    <button type="button" class="btn btn-line" data-la="-1" aria-label="Scroll the look-ahead back">&larr; Back</button>
    <button type="button" class="btn btn-line" data-la="1" aria-label="Scroll the look-ahead forward">Forward &rarr;</button>
  </div>
  <ul class="la-track" tabindex="0" aria-label="Build-up animations">{"".join(cards)}</ul>
</section>"""


def submittals(bbs: list[dict], start: dt.date) -> str:
    if not bbs:
        return ""
    items = "".join(
        f'<li{" class=extra" if i >= 6 else ""}>'
        f'{opener("__bbs", b["src"], f"<span class=sub-no>SUB-{i + 1:03d}</span>" + img_tag(b, b["alt"], use_thumb=True) + f"<span class=sub-cap>{e(b['alt'])}</span>", "sub-link", index=i, label="Open drawing: " + b["alt"])}</li>'
        for i, b in enumerate(bbs)
    )
    more = (f'<button type="button" class="btn btn-line" data-more aria-expanded="false">'
            f'Show all {len(bbs)} submittals</button>') if len(bbs) > 6 else ""
    return f"""
<section class="phase phase-rebar" id="rebar" aria-labelledby="rebar-title">
  {activity("rebar", "rebar-title", "Rebar submittals", "Beam, column, footing and slab reinforcement, detailed in Revit and RC-CADS and scheduled straight from the model.", start)}
  <ol class="sub-list" data-collapsed="true">{items}</ol>
  {more}
</section>"""


def trades(start: dt.date) -> str:
    """The signature skill cards, opened by this design's activity row."""
    skills, _ = signature.load()
    sk = skills["skills"]
    head = activity("skills", "sig-skills-title", sk["title"], sk["intro"], start)
    return signature.skills_html(header_html=head, anchor="skills").replace(
        'class="sig-skills"', 'class="phase phase-trades sig-skills"', 1)


def resources(profile: dict, start: dt.date) -> str:
    exp = "".join(
        f"""<article class="res">
      <p class="res-when mono"><time>{e(j["from"])}</time> &rarr; <time>{e(j["to"])}</time></p>
      <h3>{e(j["role"])}</h3>
      <p class="meta">{e(j["org"])}</p>
      <ul>{"".join(f"<li>{e(pt)}</li>" for pt in j["points"])}</ul>
    </article>"""
        for j in profile["experience"]
    )
    skills = "".join(
        f'<div><dt>{e(s["group"])}</dt><dd>{"".join(f"<span>{e(x)}</span>" for x in s["items"])}</dd></div>'
        for s in profile["skills"]
    )
    edu = "".join(f'<p><b>{e(x["title"])}</b>, {e(x["years"])}<br>{e(x["detail"])}</p>' for x in profile["education"])
    stats = "".join(f'<li><b data-count>{e(s["value"])}</b><span>{e(s["label"])}</span></li>' for s in profile["stats"])
    return f"""
<section class="phase phase-resources" id="about" aria-labelledby="about-title">
  {activity("about", "about-title", "Resources", profile["intro"], start)}
  <ul class="res-stats">{stats}</ul>
  <div class="res-grid">
    <div class="res-list">{exp}</div>
    <aside class="res-side">
      <dl class="res-skills">{skills}</dl>
      <div class="res-edu"><h3>Education</h3>{edu}<h3>Languages</h3><p>{e(", ".join(profile["languages"]))}</p></div>
    </aside>
  </div>
</section>"""


def baseline(site: dict, start: dt.date) -> str:
    rows = "".join(
        f'<tr><th scope="row" class="mono">{e(r["rev"])}</th><td class="mono">{e(fmt_date(r["date"]))}</td><td>{e(r["note"])}</td></tr>'
        for r in site.get("revisions", [])[:5]
    )
    return f"""
<section class="phase phase-baseline" id="revisions" aria-labelledby="rev-title">
  {activity("revisions", "rev-title", f"Baseline {site['version']}", "This programme is re-baselined on a schedule: a whole revamp every Monday, Wednesday and Friday, a new design system on the other mornings, and the featured project changes twice a day.", start)}
  <div class="rev-wrap">
    <table class="rev-table">
      <caption class="mono">Latest revisions</caption>
      <thead><tr><th scope="col">Rev</th><th scope="col">Date</th><th scope="col">Description</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <a class="btn btn-line" href="{CHANGELOG_URL}" rel="noopener">Full revision history</a>
  </div>
</section>"""


def handover(profile: dict, start: dt.date) -> str:
    return f"""
<section class="phase phase-handover" id="contact" aria-labelledby="contact-title">
  {activity("contact", "contact-title", "Got a model that needs building?", "", start, cls="act-keydate")}
  <a class="ho-mail" href="mailto:{e(profile["email"])}"><span class="ho-diamond" aria-hidden="true"></span>{e(profile["email"])}</a>
  <p class="ho-links">
    <a class="btn btn-line" href="{e(profile["linkedin"])}" rel="noopener">LinkedIn</a>
    <span class="mono">{e(profile["location"])}</span>
  </p>
</section>"""


# --------------------------------------------------------------------------- #
# Design tokens
# --------------------------------------------------------------------------- #
def write_tokens(system: dict) -> Path:
    """design/system.json -> assets/css/tokens.css (themes, font stacks, scale)."""
    lines = ["/* Generated from design/system.json by scripts/render.py. Do not edit. */",
             f"/* Design system: {system.get('name', '')} (since {system.get('introduced', '')}) */"]
    for i, (name, th) in enumerate(system["themes"].items()):
        sel = f':root,\n[data-theme="{name}"]' if i == 0 else f'[data-theme="{name}"]'
        props = "".join(f"\n  --{k}: {val};" for k, val in th.items() if k != "scheme")
        lines.append(f"{sel} {{{props}\n  color-scheme: {th.get('scheme', 'light')};\n}}")
    fonts = system["fonts"]
    stacks = f"\n  --font: {fonts['body']};"
    stacks += f"\n  --font-display: {fonts.get('display', fonts['body'])};"
    stacks += f"\n  --font-mono: {fonts.get('mono', 'ui-monospace, monospace')};"
    scale = "".join(f"\n  {k}: {val};" for k, val in system.get("scale", {}).items())
    lines.append(f":root {{{stacks}{scale}\n}}")
    out = ROOT / "assets" / "css" / "tokens.css"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def build() -> Path:
    profile = json.loads((DATA / "profile.json").read_text(encoding="utf-8"))
    data = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    system = json.loads((ROOT / "design" / "system.json").read_text(encoding="utf-8"))
    write_tokens(system)
    projects = data["projects"]
    by_slug = {p["slug"]: p for p in projects}
    featured = by_slug.get(site["featured"], projects[0])
    start = programme_start(site)

    # Compact payload for the viewer (dialog) — only what the JS needs.
    viewer = {
        p["slug"]: {
            "title": p["title"], "sheet": p["sheet"],
            "meta": ", ".join(x for x in (p["kind"], p["location"]) if x),
            "summary": p["summary"],
            "images": [{"src": i["src"], "w": i["w"], "h": i["h"]} for i in p["images"]],
            "video": p.get("video"),
        }
        for p in projects
    }
    viewer["__bbs"] = {
        "title": "Rebar and BBS submittals", "sheet": "S-100", "meta": "Reinforcement documentation", "summary": "",
        "images": [{"src": b["src"], "w": b["w"], "h": b["h"], "alt": b["alt"]} for b in data.get("bbs", [])],
        "video": None,
    }
    viewer_json = json.dumps(viewer, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    title = f'{profile["name"]}: {profile["role"]}'
    desc = profile["intro"]
    og = SITE_URL + featured["images"][0]["src"]
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "Person", "name": profile["name"],
        "jobTitle": profile["role"], "email": f'mailto:{profile["email"]}', "url": SITE_URL,
        "sameAs": [profile["linkedin"]],
        "worksFor": {"@type": "Organization", "name": profile["employer"], "url": profile["employerUrl"]},
        "address": {"@type": "PostalAddress", "addressLocality": "Mumbai", "addressCountry": "IN"},
    }, ensure_ascii=False)
    v = e(site["version"])

    html = f"""<!doctype html>
<!-- Generated by scripts/render.py — edit data/*.json, not this file. -->
<html lang="en" data-theme="{e(site["theme"])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="version" content="{v}">
<link rel="canonical" href="{SITE_URL}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{e(og)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{e(system["fonts"]["stylesheet"])}">
<link rel="stylesheet" href="assets/css/tokens.css?v={v}">
<link rel="stylesheet" href="{signature.CSS_HREF}?v={v}">
<link rel="stylesheet" href="assets/css/main.css?v={v}">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{programme_bar(profile, start)}
<main id="main">
{signature.stage_html(profile, projects, opener, anchor="roof")}
<div class="programme">
{critical_path(featured, start)}
{gantt(projects, start)}
{lookahead(by_slug, site.get("reel", list(by_slug)), start)}
{submittals(data.get("bbs", []), start)}
{trades(start)}
{resources(profile, start)}
{baseline(site, start)}
{handover(profile, start)}
</div>
</main>
<footer class="closeout">
  <p class="mono">Programme rev {v} &middot; data date {e(fmt_date(site["date"]))} &middot; {WEEKS} weeks</p>
  <p>Projects modelled at {e(profile["employer"])}. Build-up soundtracks from Mixkit. <a href="{CHANGELOG_URL}" rel="noopener">Revision history</a></p>
</footer>

<dialog class="viewer" id="viewer" aria-labelledby="viewer-title">
  <div class="viewer-head">
    <p class="mono kicker" id="viewer-sheet"></p>
    <h2 id="viewer-title"></h2>
    <p class="meta" id="viewer-meta"></p>
    <button type="button" class="viewer-close" data-close aria-label="Close viewer">Close &times;</button>
  </div>
  <div class="viewer-stage" id="viewer-stage"></div>
  <div class="viewer-foot">
    <button type="button" class="btn btn-line" data-step="-1" aria-label="Previous view">&larr; Previous</button>
    <p id="viewer-count" class="mono" aria-live="polite"></p>
    <button type="button" class="btn btn-line" data-step="1" aria-label="Next view">Next &rarr;</button>
  </div>
</dialog>
<script id="viewer-data" type="application/json">{viewer_json}</script>
<script src="assets/js/main.js?v={v}" defer></script>
<script src="{signature.JS_SRC}?v={v}" defer></script>
</body>
</html>
"""
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
    return out
