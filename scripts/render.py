"""
render.py — builds index.html from data/profile.json, data/projects.json and data/site.json.

Pre-rendering (instead of fetching JSON in the browser) keeps the page fast, readable
without JavaScript and indexable by search engines. assets/js/main.js only adds
behaviour: filtering, the project viewer and video previews.

Edit content in data/*.json, then run:  python3 scripts/portfolio.py build
"""
from __future__ import annotations

import datetime as dt
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE_URL = "https://zxaidman.github.io/Portfolio/"


def e(value) -> str:
    """HTML-escape any value (attribute-safe)."""
    return escape(str(value if value is not None else ""), quote=True)


def fmt_date(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


def img_tag(im: dict, alt: str, cls: str = "", eager: bool = False, use_thumb: bool = False, sizes: str = "") -> str:
    src = im["thumb"] if use_thumb else im["src"]
    loading = 'fetchpriority="high"' if eager else 'loading="lazy"'
    srcset = f' srcset="{e(im["thumb"])} 720w, {e(im["src"])} 1800w" sizes="{e(sizes)}"' if sizes else ""
    return (f'<img class="{e(cls)}" src="{e(src)}"{srcset} alt="{e(alt)}" width="{im["w"]}" '
            f'height="{im["h"]}" decoding="async" {loading}>')


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def hero(profile: dict, site: dict, featured: dict) -> str:
    video = featured.get("video") or {}
    revisions = "".join(
        f'<tr><td>{e(r["rev"])}</td><td>{e(fmt_date(r["date"]))}</td><td>{e(r["note"])}</td></tr>'
        for r in site.get("revisions", [])[:3]
    )
    stats = "".join(f'<li><b>{e(s["value"])}</b><span>{e(s["label"])}</span></li>' for s in profile["stats"])
    where = ", ".join(x for x in (featured["kind"], featured["location"]) if x)
    media = (
        f'<video class="hero-video" muted loop playsinline preload="none" poster="{e(video.get("poster") or featured["images"][0]["src"])}" '
        f'data-src="{e(video["src"])}" aria-label="Build-up animation of {e(featured["title"])}"></video>'
        if video.get("src") else img_tag(featured["images"][0], featured["title"], "hero-video", eager=True)
    )
    return f"""
<section class="hero" aria-labelledby="hero-title">
  <div class="hero-copy">
    <p class="hero-role">{e(profile["role"])}</p>
    <h1 id="hero-title" class="hero-name">{e(profile["name"])}</h1>
    <p class="hero-lede">{e(profile["headline"])}</p>
    <div class="hero-actions">
      <a class="btn btn-solid" href="#projects">See the projects</a>
      <a class="btn btn-line" href="mailto:{e(profile["email"])}">Email Zaid</a>
    </div>
    <ul class="hero-stats">{stats}</ul>
  </div>
  <figure class="viewport hero-viewport">
    {media}
    <figcaption>
      <span>Build-up sequence</span>
      <button class="link-btn" type="button" data-open="{e(featured["slug"])}">{e(featured["title"])}</button>
      <span>{e(where)}</span>
    </figcaption>
  </figure>
  <div class="titleblock" role="group" aria-label="Sheet details">
    <dl class="tb-cells">
      <div><dt>Project</dt><dd>Portfolio of {e(profile["name"])}</dd></div>
      <div><dt>Practice</dt><dd><a href="{e(profile["employerUrl"])}" rel="noopener">{e(profile["employer"])}</a></dd></div>
      <div><dt>Location</dt><dd>{e(profile["location"])}</dd></div>
      <div><dt>Sheet</dt><dd>A-000 cover</dd></div>
      <div><dt>Revision</dt><dd>{e(site["version"])}</dd></div>
    </dl>
    <table class="tb-revs">
      <caption>Revisions</caption>
      <thead><tr><th scope="col">Rev</th><th scope="col">Date</th><th scope="col">Description</th></tr></thead>
      <tbody>{revisions}</tbody>
    </table>
  </div>
</section>"""


def featured_section(p: dict) -> str:
    imgs = p["images"]
    thumbs = "".join(
        f'<li><button type="button" class="thumb" data-open="{e(p["slug"])}" data-index="{i}" '
        f'aria-label="Open view {i + 1} of {e(p["title"])}">{img_tag(im, "", use_thumb=True)}</button></li>'
        for i, im in enumerate(imgs[1:6], start=1)
    )
    video_btn = (f'<button class="btn btn-line" type="button" data-open="{e(p["slug"])}" data-video>'
                 f'Watch the build-up ({e(p["video"]["duration"])})</button>') if p.get("video") else ""
    return f"""
<section class="featured" id="featured" aria-labelledby="featured-title">
  <header class="sec-head">
    <h2 id="featured-title">On the board today</h2>
    <p>A different project leads the sheet each morning.</p>
  </header>
  <div class="featured-grid">
    <button type="button" class="viewport featured-main" data-open="{e(p["slug"])}" data-index="0"
      aria-label="Open {e(p["title"])} gallery">
      {img_tag(imgs[0], p["title"] + " Revit model", sizes="(min-width: 900px) 55vw, 100vw")}
    </button>
    <div class="featured-copy">
      <p class="sheet-no">Sheet {e(p["sheet"])}</p>
      <h3>{e(p["title"])}</h3>
      <p class="meta">{e(p["kind"])}{(", " + e(p["location"])) if p["location"] else ""}</p>
      <p>{e(p["summary"])}</p>
      <div class="hero-actions">
        <button class="btn btn-solid" type="button" data-open="{e(p["slug"])}" data-index="0">View all {len(imgs)} views</button>
        {video_btn}
      </div>
      <ul class="thumbs">{thumbs}</ul>
    </div>
  </div>
</section>"""


def register(projects: list[dict]) -> str:
    counts: dict[str, int] = {}
    for p in projects:
        counts[p["type"]] = counts.get(p["type"], 0) + 1
    order = [t for t in ("Residential", "Commercial", "Other") if t in counts]
    filters = f'<button type="button" class="chip" aria-pressed="true" data-filter="all">All <span>{len(projects)}</span></button>'
    filters += "".join(
        f'<button type="button" class="chip" aria-pressed="false" data-filter="{e(t)}">{e(t)} <span>{counts[t]}</span></button>'
        for t in order
    )
    rows = "".join(
        f"""<li class="reg-row" data-type="{e(p["type"])}">
      <button type="button" data-open="{e(p["slug"])}" data-index="0" data-preview="{e(p["images"][0]["thumb"])}">
        <span class="r-no">{e(p["sheet"])}</span>
        <span class="r-title">{e(p["title"])}</span>
        <span class="r-kind">{e(p["kind"])}</span>
        <span class="r-loc">{e(p["location"] or "—")}</span>
        <span class="r-media">{len(p["images"])} views{" + build-up" if p.get("video") else ""}</span>
        {img_tag(p["images"][0], "", "r-thumb", use_thumb=True)}
      </button>
    </li>"""
        for p in projects
    )
    first = projects[0]["images"][0]
    return f"""
<section class="register" id="projects" aria-labelledby="register-title">
  <header class="sec-head">
    <h2 id="register-title">Drawing register</h2>
    <p>{len(projects)} projects I modelled with the Computer Help BIM team. Select a row to open its views.</p>
  </header>
  <div class="filters" role="group" aria-label="Filter projects by type">{filters}</div>
  <div class="reg-wrap">
    <ol class="reg-list" aria-live="polite">{rows}</ol>
    <figure class="viewport reg-preview" aria-hidden="true">
      <img src="{e(first["thumb"])}" alt="" width="{first["w"]}" height="{first["h"]}" loading="lazy">
    </figure>
  </div>
</section>"""


def reel(projects_by_slug: dict, order: list[str]) -> str:
    cards = []
    for slug in order:
        p = projects_by_slug.get(slug)
        if not p or not p.get("video"):
            continue
        v = p["video"]
        poster = v.get("poster") or p["images"][0]["thumb"]
        cards.append(f"""<li class="reel-card">
      <button type="button" data-open="{e(slug)}" data-video aria-label="Play the {e(p["title"])} build-up">
        <span class="viewport reel-media">
          <img src="{e(poster)}" alt="" loading="lazy" decoding="async">
          <video muted loop playsinline preload="none" data-src="{e(v["src"])}" tabindex="-1"></video>
        </span>
        <span class="reel-cap"><b>{e(p["title"])}</b><span>{e(v["duration"])}</span></span>
      </button>
    </li>""")
    return f"""
<section class="reel" id="buildups" aria-labelledby="reel-title">
  <header class="sec-head">
    <h2 id="reel-title">Floor by floor</h2>
    <p>Construction-sequence animations rendered from the Revit models. Hover to preview, select to watch with sound.</p>
  </header>
  <ul class="reel-track" tabindex="0" aria-label="Build-up animations, scroll sideways">{"".join(cards)}</ul>
</section>"""


def rebar(bbs: list[dict]) -> str:
    if not bbs:
        return ""
    items = "".join(
        f'<li{" class=extra" if i >= 8 else ""}><button type="button" class="viewport" data-open="__bbs" data-index="{i}" '
        f'aria-label="Open drawing: {e(b["alt"])}">{img_tag(b, b["alt"], use_thumb=True)}</button></li>'
        for i, b in enumerate(bbs)
    )
    more = (f'<button type="button" class="btn btn-line" data-more aria-expanded="false">'
            f'Show all {len(bbs)} drawings</button>') if len(bbs) > 8 else ""
    return f"""
<section class="rebar" id="rebar" aria-labelledby="rebar-title">
  <header class="sec-head">
    <h2 id="rebar-title">Rebar and bar bending schedules</h2>
    <p>Beam, column, footing and slab reinforcement, detailed in Revit and RC-CADS and scheduled straight from the model.</p>
  </header>
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
        f'<div><dt>{e(s["group"])}</dt><dd>{e(", ".join(s["items"]))}</dd></div>' for s in profile["skills"]
    )
    edu = "".join(f'<p><b>{e(x["title"])}</b>, {e(x["years"])}<br>{e(x["detail"])}</p>' for x in profile["education"])
    return f"""
<section class="about" id="about" aria-labelledby="about-title">
  <header class="sec-head">
    <h2 id="about-title">About</h2>
    <p>{e(profile["intro"])}</p>
  </header>
  <div class="about-grid">
    <div>{exp}</div>
    <div>
      <dl class="skills">{skills}</dl>
      <div class="edu"><h3>Education</h3>{edu}<h3>Languages</h3><p>{e(", ".join(profile["languages"]))}</p></div>
    </div>
  </div>
</section>"""


def contact(profile: dict) -> str:
    return f"""
<section class="contact" id="contact" aria-labelledby="contact-title">
  <h2 id="contact-title">Got a model that needs building?</h2>
  <a class="contact-mail" href="mailto:{e(profile["email"])}">{e(profile["email"])}</a>
  <p class="contact-links">
    <a href="{e(profile["linkedin"])}" rel="noopener">LinkedIn</a>
    <span>{e(profile["location"])}</span>
  </p>
</section>"""


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def build() -> Path:
    profile = json.loads((DATA / "profile.json").read_text(encoding="utf-8"))
    data = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
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
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,300..900&display=swap">
<link rel="stylesheet" href="assets/css/main.css?v={v}">
<script type="application/ld+json">{ld}</script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="sheet-frame" aria-hidden="true"></div>
<header class="topbar">
  <a class="mark" href="#top" aria-label="{e(profile["name"])}, back to top">{e(profile["name"])}</a>
  <nav aria-label="Sections">
    <a href="#projects">Projects</a><a href="#buildups">Build-ups</a><a href="#rebar">Rebar</a><a href="#about">About</a><a href="#contact">Contact</a>
  </nav>
  {'<span class="status">Open to BIM roles</span>' if profile.get("available") else ""}
</header>
<main id="main">
<span id="top"></span>
{hero(profile, site, featured)}
{featured_section(featured)}
{register(projects)}
{reel(by_slug, site.get("reel", list(by_slug)))}
{rebar(data.get("bbs", []))}
{about(profile)}
{contact(profile)}
</main>
<footer class="foot">
  <p>Rev {v}, updated {e(fmt_date(site["date"]))}. Projects modelled at {e(profile["employer"])}. Build-up soundtracks from Mixkit.</p>
  <p><a href="https://github.com/Zxaidman/Portfolio/blob/main/CHANGELOG.md" rel="noopener">Revision history</a></p>
</footer>

<dialog class="viewer" id="viewer" aria-labelledby="viewer-title">
  <div class="viewer-head">
    <p class="sheet-no" id="viewer-sheet"></p>
    <h2 id="viewer-title"></h2>
    <p class="meta" id="viewer-meta"></p>
    <button type="button" class="viewer-close" data-close aria-label="Close viewer">Close</button>
  </div>
  <div class="viewer-stage viewport" id="viewer-stage"></div>
  <div class="viewer-foot">
    <button type="button" class="btn btn-line" data-step="-1" aria-label="Previous view">Previous</button>
    <p id="viewer-count" aria-live="polite"></p>
    <button type="button" class="btn btn-line" data-step="1" aria-label="Next view">Next</button>
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
