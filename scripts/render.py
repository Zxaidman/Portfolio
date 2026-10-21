"""
render.py — builds index.html from data/profile.json, data/projects.json and data/site.json.

Design: "Storey stack" (v3.0.0). The page is a tower in section, read from the roof
down to the foundation. Every section is a storey that opens on a Revit-style level
datum (level tag + elevation); a fixed level rail on the left (a bottom bar on phones)
is the navigation, and its lift car tracks scroll position.

Pre-rendering (instead of fetching JSON in the browser) keeps the page fast, readable
without JavaScript and indexable. Every "open" control is a real link to the image or
video, so without JavaScript it still works; assets/js/main.js upgrades it to the viewer.

Data contract (unchanged): data/*.json shapes and build(), which writes index.html and
assets/css/tokens.css. Edit content in data/*.json, then run:  python3 scripts/portfolio.py build
"""
from __future__ import annotations

import datetime as dt
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_URL = "https://zxaidman.github.io/Portfolio/"
CHANGELOG_URL = "https://github.com/Zxaidman/Portfolio/blob/main/CHANGELOG.md"
STOREY_HEIGHT = 3.0  # metres between level datums, for the elevation labels

# The tower, top to bottom: (anchor id, level tag, name shown on the datum).
LEVELS = [
    ("roof", "RF", "Roof"),
    ("featured", "L6", "Today's slab"),
    ("projects", "L5", "Floors"),
    ("buildups", "L4", "Build-ups"),
    ("rebar", "L3", "Rebar & BBS"),
    ("about", "L2", "About"),
    ("revisions", "L1", "Revisions"),
    ("contact", "GL", "Ground"),
]


def e(value) -> str:
    """HTML-escape any value (attribute-safe)."""
    return escape(str(value if value is not None else ""), quote=True)


def fmt_date(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


def elevation(anchor: str) -> str:
    """'+21.000' style elevation for a level, ground level = ±0.000."""
    idx = [a for a, _, _ in LEVELS].index(anchor)
    metres = (len(LEVELS) - 1 - idx) * STOREY_HEIGHT
    return "±0.000" if metres == 0 else f"+{metres:.3f}"


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


def datum(anchor: str, title_id: str, title: str, note: str = "") -> str:
    """The level datum that opens each storey: tag bubble, elevation, name, a drawn line."""
    _, tag, name = next(l for l in LEVELS if l[0] == anchor)
    note_html = f'<p class="storey-note">{e(note)}</p>' if note else ""
    return f"""<header class="datum">
    <p class="datum-line" aria-hidden="true"><span class="datum-tag">{e(tag)}</span><span class="datum-el">{e(elevation(anchor))}</span><span class="datum-name">{e(name)}</span><span class="datum-rule"></span></p>
    <h2 id="{e(title_id)}" class="storey-title">{e(title)}</h2>
    {note_html}
  </header>"""


# --------------------------------------------------------------------------- #
# Storeys
# --------------------------------------------------------------------------- #
def rail(profile: dict) -> str:
    items = "".join(
        f'<li><a href="#{e(a)}" data-level="{e(a)}"><span class="rl-tag">{e(t)}</span>'
        f'<span class="rl-el">{e(elevation(a))}</span><span class="rl-name">{e(n)}</span></a></li>'
        for a, t, n in LEVELS
    )
    return f"""<nav class="rail" aria-label="Levels">
  <a class="rail-mark" href="#roof" aria-label="{e(profile["name"])}, back to the roof">ZS<span>BIM</span></a>
  <ol class="rail-levels">{items}</ol>
  <div class="rail-shaft" aria-hidden="true"><span class="rail-car"></span></div>
  <p class="rail-readout" aria-hidden="true"><span>Level</span><b data-readout>RF</b></p>
</nav>"""


def roof(profile: dict, site: dict, featured: dict) -> str:
    video = featured.get("video") or {}
    stats = "".join(f'<li><b>{e(s["value"])}</b><span>{e(s["label"])}</span></li>' for s in profile["stats"])
    where = ", ".join(x for x in (featured["kind"], featured["location"]) if x)
    if video.get("src"):
        media = (f'<video class="roof-video" muted loop playsinline preload="none" '
                 f'poster="{e(video.get("poster") or featured["images"][0]["src"])}" data-src="{e(video["src"])}" '
                 f'aria-label="Build-up animation of {e(featured["title"])}"></video>')
    else:
        media = img_tag(featured["images"][0], featured["title"], "roof-video", eager=True)
    status = '<p class="roof-status">Open to BIM roles</p>' if profile.get("available") else ""
    open_link = opener(featured["slug"], featured["images"][0]["src"], e(featured["title"]), "roof-link",
                       label=f'Open {featured["title"]} gallery')
    return f"""
<section class="storey storey-roof" id="roof" aria-labelledby="hero-title">
  <header class="datum datum-roof">
    <p class="datum-line" aria-hidden="true"><span class="datum-tag">RF</span><span class="datum-el">{e(elevation("roof"))}</span><span class="datum-name">Roof</span><span class="datum-rule"></span></p>
  </header>
  <div class="roof-grid">
    <div class="roof-copy">
      <p class="roof-role">{e(profile["role"])}</p>
      <h1 id="hero-title" class="roof-name">{"<br>".join(e(w) for w in profile["name"].split(" ", 1))}</h1>
      <p class="roof-lede">{e(profile["headline"])}</p>
      <div class="actions">
        <a class="btn btn-solid" href="#projects">Take the stairs down</a>
        <a class="btn btn-line" href="mailto:{e(profile["email"])}">Email Zaid</a>
      </div>
      {status}
    </div>
    <figure class="roof-media">
      <span class="sbox"><span class="sbox-frame">{media}</span></span>
      <figcaption><span class="mono">Build-up</span>{open_link}<span>{e(where)}</span></figcaption>
    </figure>
  </div>
  <ul class="columns" aria-label="At a glance">{stats}<li><b>Rev {e(site["version"])}</b><span>this tower, {e(fmt_date(site["date"]))}</span></li></ul>
</section>"""


def featured_storey(p: dict) -> str:
    imgs = p["images"]
    thumbs = "".join(
        f'<li>{opener(p["slug"], im["src"], img_tag(im, "", use_thumb=True), "thumb", index=i, label="Open view %d of %s" % (i + 1, p["title"]))}</li>'
        for i, im in enumerate(imgs[1:6], start=1)
    )
    video_btn = (opener(p["slug"], p["video"]["src"], f'Watch the build-up <span class="mono">{e(p["video"]["duration"])}</span>',
                        "btn btn-line", video=True)) if p.get("video") else ""
    main_img = opener(p["slug"], imgs[0]["src"],
                      f'<span class="sbox-frame">{img_tag(imgs[0], p["title"] + " Revit model", sizes="(min-width: 900px) 58vw, 100vw")}</span>',
                      "sbox feat-main", label=f'Open {p["title"]} gallery')
    return f"""
<section class="storey storey-featured" id="featured" aria-labelledby="featured-title">
  {datum("featured", "featured-title", "On the slab today", "A different project is poured on this level every morning.")}
  <div class="feat-grid">
    {main_img}
    <div class="feat-copy">
      <p class="mono tag">Sheet {e(p["sheet"])}</p>
      <h3>{e(p["title"])}</h3>
      <p class="meta">{e(p["kind"])}{(", " + e(p["location"])) if p["location"] else ""}</p>
      <p>{e(p["summary"])}</p>
      <div class="actions">
        {opener(p["slug"], imgs[0]["src"], f"All {len(imgs)} views", "btn btn-solid")}
        {video_btn}
      </div>
      <ul class="thumbs">{thumbs}</ul>
    </div>
  </div>
</section>"""


def floors(projects: list[dict]) -> str:
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
    rows = "".join(
        f"""<li class="floor" data-type="{e(p["type"])}">
      {opener(p["slug"], p["images"][0]["src"], f'''<span class="fl-no mono">FL {total - i:02d}</span>
        <span class="fl-title">{e(p["title"])}</span>
        <span class="fl-kind">{e(p["kind"])}</span>
        <span class="fl-loc mono">{e(p["location"] or "—")}</span>
        <span class="fl-media mono">{len(p["images"])} views{" + build-up" if p.get("video") else ""}</span>
        <span class="fl-thumb">{img_tag(p["images"][0], "", use_thumb=True)}</span>''', "fl-link")}
    </li>"""
        for i, p in enumerate(projects)
    )
    return f"""
<section class="storey storey-floors" id="projects" aria-labelledby="floors-title">
  {datum("projects", "floors-title", f"{total} floors, {total} projects", "Every project I modelled with the Computer Help BIM team, stacked one per floor. Open a floor to walk its views.")}
  <div class="filters" role="group" aria-label="Filter projects by type">{filters}</div>
  <ol class="floor-stack" aria-live="polite">{rows}</ol>
</section>"""


def buildups(projects_by_slug: dict, order: list[str]) -> str:
    cards = []
    for slug in order:
        p = projects_by_slug.get(slug)
        if not p or not p.get("video"):
            continue
        v = p["video"]
        poster = v.get("poster") or p["images"][0]["thumb"]
        inner = (f'<span class="sbox bu-box"><span class="sbox-frame bu-media"><img src="{e(poster)}" alt="" loading="lazy" decoding="async">'
                 f'<video muted loop playsinline preload="none" data-src="{e(v["src"])}" tabindex="-1"></video></span></span>'
                 f'<span class="bu-cap"><b>{e(p["title"])}</b><span class="mono">{e(v["duration"])}</span></span>')
        cards.append(f'<li class="bu-card">{opener(slug, v["src"], inner, "bu-link", video=True, label="Play the %s build-up" % p["title"])}</li>')
    return f"""
<section class="storey storey-buildups" id="buildups" aria-labelledby="bu-title">
  {datum("buildups", "bu-title", "Poured floor by floor", "Construction-sequence animations rendered from the Revit models. Hover to preview, open to watch with sound.")}
  <ul class="bu-grid">{"".join(cards)}</ul>
</section>"""


def rebar(bbs: list[dict]) -> str:
    if not bbs:
        return ""
    items = "".join(
        f'<li{" class=extra" if i >= 6 else ""}>'
        f'{opener("__bbs", b["src"], img_tag(b, b["alt"], use_thumb=True), "bbs-link", index=i, label="Open drawing: " + b["alt"])}</li>'
        for i, b in enumerate(bbs)
    )
    more = (f'<button type="button" class="btn btn-line" data-more aria-expanded="false">'
            f'Show all {len(bbs)} drawings</button>') if len(bbs) > 6 else ""
    return f"""
<section class="storey storey-rebar" id="rebar" aria-labelledby="rebar-title">
  {datum("rebar", "rebar-title", "Rebar and bar bending schedules", "Beam, column, footing and slab reinforcement, detailed in Revit and RC-CADS and scheduled straight from the model.")}
  <svg class="bars" viewBox="0 0 600 40" preserveAspectRatio="none" aria-hidden="true" focusable="false">
    <path d="M0 8 H600 M0 32 H600"/><path class="stirrups" d="M20 4 V36 M70 4 V36 M120 4 V36 M170 4 V36 M220 4 V36 M270 4 V36 M320 4 V36 M370 4 V36 M420 4 V36 M470 4 V36 M520 4 V36 M570 4 V36"/>
  </svg>
  <ul class="bbs-grid" data-collapsed="true">{items}</ul>
  {more}
</section>"""


def about(profile: dict) -> str:
    exp = "".join(
        f"""<article class="job">
      <h3>{e(j["role"])}</h3>
      <p class="meta">{e(j["org"])}, <time>{e(j["from"])}</time> to <time>{e(j["to"])}</time></p>
      <ul>{"".join(f"<li>{e(pt)}</li>" for pt in j["points"])}</ul>
    </article>"""
        for j in profile["experience"]
    )
    skills = "".join(
        f'<div><dt>{e(s["group"])}</dt><dd>{"".join(f"<span>{e(x)}</span>" for x in s["items"])}</dd></div>'
        for s in profile["skills"]
    )
    edu = "".join(f'<p><b>{e(x["title"])}</b>, {e(x["years"])}<br>{e(x["detail"])}</p>' for x in profile["education"])
    return f"""
<section class="storey storey-about" id="about" aria-labelledby="about-title">
  {datum("about", "about-title", "About", profile["intro"])}
  <div class="about-grid">
    <div>{exp}</div>
    <div>
      <dl class="skills">{skills}</dl>
      <div class="edu"><h3>Education</h3>{edu}<h3>Languages</h3><p>{e(", ".join(profile["languages"]))}</p></div>
    </div>
  </div>
</section>"""


def revisions(site: dict) -> str:
    rows = "".join(
        f'<tr><th scope="row" class="mono">{e(r["rev"])}</th><td class="mono">{e(fmt_date(r["date"]))}</td><td>{e(r["note"])}</td></tr>'
        for r in site.get("revisions", [])[:5]
    )
    return f"""
<section class="storey storey-revisions" id="revisions" aria-labelledby="rev-title">
  {datum("revisions", "rev-title", f"Rev {site['version']}", "This tower is rebuilt on a schedule: a new design system every morning, a whole revamp every third day, and a fresh featured project twice a day in between.")}
  <div class="rev-wrap">
    <table class="rev-table">
      <caption class="mono">Latest revisions</caption>
      <thead><tr><th scope="col">Rev</th><th scope="col">Date</th><th scope="col">Description</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <a class="btn btn-line" href="{CHANGELOG_URL}" rel="noopener">Full revision history</a>
  </div>
</section>"""


def contact(profile: dict) -> str:
    return f"""
<section class="storey storey-contact" id="contact" aria-labelledby="contact-title">
  <header class="datum">
    <p class="datum-line" aria-hidden="true"><span class="datum-tag">GL</span><span class="datum-el">{e(elevation("contact"))}</span><span class="datum-name">Ground</span><span class="datum-rule"></span></p>
    <h2 id="contact-title" class="storey-title contact-title">Got a model that needs building?</h2>
  </header>
  <a class="contact-mail" href="mailto:{e(profile["email"])}">{e(profile["email"])}</a>
  <p class="contact-links">
    <a href="{e(profile["linkedin"])}" rel="noopener">LinkedIn</a>
    <span>{e(profile["location"])}</span>
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
        "title": "Rebar and BBS drawings", "sheet": "S-100", "meta": "Reinforcement documentation", "summary": "",
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
<link rel="stylesheet" href="assets/css/main.css?v={v}">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{rail(profile)}
<main id="main" class="tower">
{roof(profile, site, featured)}
{featured_storey(featured)}
{floors(projects)}
{buildups(by_slug, site.get("reel", list(by_slug)))}
{rebar(data.get("bbs", []))}
{about(profile)}
{revisions(site)}
{contact(profile)}
</main>
<footer class="foundation">
  <p class="mono">Foundation &minus;1.500 &middot; Rev {v} &middot; updated {e(fmt_date(site["date"]))}</p>
  <p>Projects modelled at {e(profile["employer"])}. Build-up soundtracks from Mixkit. <a href="{CHANGELOG_URL}" rel="noopener">Revision history</a></p>
</footer>

<dialog class="viewer" id="viewer" aria-labelledby="viewer-title">
  <div class="viewer-head">
    <p class="mono tag" id="viewer-sheet"></p>
    <h2 id="viewer-title"></h2>
    <p class="meta" id="viewer-meta"></p>
    <button type="button" class="viewer-close" data-close aria-label="Close viewer">Close</button>
  </div>
  <div class="viewer-stage" id="viewer-stage"></div>
  <div class="viewer-foot">
    <button type="button" class="btn btn-line" data-step="-1" aria-label="Previous view">Up a view</button>
    <p id="viewer-count" class="mono" aria-live="polite"></p>
    <button type="button" class="btn btn-line" data-step="1" aria-label="Next view">Down a view</button>
  </div>
</dialog>
<script id="viewer-data" type="application/json">{viewer_json}</script>
<script src="assets/js/main.js?v={v}" defer></script>
</body>
</html>
"""
    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
    return out
