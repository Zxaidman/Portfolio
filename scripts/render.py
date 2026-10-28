"""
render.py — builds index.html from data/profile.json, data/projects.json and data/site.json.

Design: "Monograph" (v7.0.0). The coordination room is torn down and the portfolio is re-set as
a printed monograph — a bound review of built work, typeset like an architectural journal:

  * The permanent scroll stage opens the page (signature.py), full-bleed.
  * After it, "the issue": a slim running-head bar (publication wordmark, the section you are
    reading, folio, paper switch) stuck to the top, then a masthead/cover with the issue line,
    a standfirst, key figures and a Contents index that doubles as the navigation.
  * Body set to an editorial measure: a leader essay opens with a drop cap (the practice and
    experience); Selected Works runs as a lead feature plus numbered feature plates for every
    project (rubric filter chips keep every type reachable); Build-up films are motion plates;
    the reinforcement drawings are a technical appendix; the signature skill cards are the
    Instruments; and a colophon carries the editions (revision history) and correspondence.

Pre-rendering (instead of fetching JSON in the browser) keeps the page fast, readable without
JavaScript and indexable. Every "open" control is a real link to the image or video, so without
JavaScript it still works; assets/js/main.js upgrades it to the viewer, filters and paper switch.

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

# The cadence line must always name the publishing rhythm in full (see the brief).
RHYTHM = ("This monograph is reset on a schedule: a whole revamp — a new layout — every Monday, "
          "Wednesday and Friday, a new design system on the other mornings, and the featured "
          "project changes twice a day.")

# Contents index = the navigation. (anchor, folio numeral, title). Order is reading order.
CONTENTS = [
    ("about", "I", "The practice"),
    ("projects", "II", "Selected works"),
    ("buildups", "III", "Build-up films"),
    ("rebar", "IV", "Reinforcement"),
    ("skills", "V", "Instruments"),
    ("revisions", "VI", "Editions"),
    ("contact", "VII", "Correspondence"),
]
FOLIO = {a: n for a, n, _ in CONTENTS}
TITLE_OF = {a: t for a, _, t in CONTENTS}


def e(value) -> str:
    """HTML-escape any value (attribute-safe)."""
    return escape(str(value if value is not None else ""), quote=True)


def fmt_date(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


def long_date(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d %B %Y")
    except (TypeError, ValueError):
        return iso or ""


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


def plate_num(i: int) -> str:
    """A plate/figure number, e.g. 'Pl. 03'."""
    return f"Pl. {i:02d}"


# --------------------------------------------------------------------------- #
# Running head (sticky) + masthead (cover) — the navigation lives here
# --------------------------------------------------------------------------- #
def running_head(profile: dict, site: dict, system: dict, themes: dict) -> str:
    """A slim bar stuck to the top of the issue: wordmark, the section being read, folio, and a
    paper (theme) switch. Scroll-spy fills [data-runhead]; the switch is revealed by main.js."""
    current = site.get("theme", next(iter(themes), ""))
    swatches = "".join(
        f'<button type="button" class="paper-dot" data-theme-set="{e(t)}" aria-pressed="{"true" if t == current else "false"}" '
        f'title="{e(t)} edition"><span aria-hidden="true" style="--sw-p:{e(th["paper"])};--sw-a:{e(th["accent"])}"></span>'
        f'<span class="sr">{e(t)} edition</span></button>'
        for t, th in themes.items()
    )
    return f"""<nav class="runhead" aria-label="Running head">
  <a class="runhead-mark" href="#top"><b>Monograph</b><span class="runhead-sub mono">Zaid Shaikh · built work</span></a>
  <p class="runhead-now mono" aria-hidden="true"><span data-runhead>Contents</span></p>
  <div class="runhead-right">
    <div class="paper" role="group" aria-label="Paper edition" hidden><span class="mono">Paper</span>{swatches}</div>
    <a class="runhead-contents mono" href="#contents">Contents ↓</a>
  </div>
</nav>"""


def masthead(profile: dict, site: dict, system: dict) -> str:
    v = site["version"]
    major, minor, _ = (v.split(".") + ["0", "0"])[:3]
    issue_line = f"Vol. {major} · No. {minor} · {long_date(site.get('date', ''))} · Mumbai edition"
    figures = "".join(
        f'<li><b data-count>{e(s["value"])}</b><span>{e(s["label"])}</span></li>'
        for s in profile["stats"]
    )
    contents = "".join(
        f'<li><a href="#{e(a)}" data-spy="{e(a)}"><span class="toc-no mono">{e(n)}</span>'
        f'<span class="toc-title">{e(t)}</span><span class="toc-leader" aria-hidden="true"></span>'
        f'<span class="toc-fol mono">{e(n)}</span></a></li>'
        for a, n, t in CONTENTS
    )
    status = ('<span class="mh-status mono"><span class="mh-dot" aria-hidden="true"></span>Open to BIM roles</span>'
              if profile.get("available") else "")
    return f"""<header class="masthead" aria-label="Masthead">
  <p class="mh-issue mono">{e(issue_line)}</p>
  <div class="mh-title">
    <h1 class="mh-name">{e(profile["name"])}</h1>
    <p class="mh-role">{e(profile["role"])}</p>
  </div>
  <div class="mh-lede">
    <p class="mh-standfirst">{e(profile["headline"])}</p>
    <p class="mh-intro">{e(profile["intro"])}</p>
    <div class="mh-actions">
      <a class="btn btn-solid" href="#projects">Read the works</a>
      <a class="btn btn-line" href="mailto:{e(profile["email"])}">Commission a model</a>
      {status}
    </div>
  </div>
  <ul class="mh-figures" aria-label="Key figures">{figures}</ul>
  <section class="contents" id="contents" aria-labelledby="contents-title">
    <div class="contents-head">
      <p class="eyebrow mono">In this issue</p>
      <h2 id="contents-title">Contents</h2>
    </div>
    <ol class="toc">{contents}</ol>
    <p class="contents-note">{e(RHYTHM)}</p>
  </section>
</header>"""


# --------------------------------------------------------------------------- #
# Section scaffolding
# --------------------------------------------------------------------------- #
def section_head(anchor: str, title_id: str, kicker: str, title: str, note: str = "") -> str:
    note_html = f'<p class="sec-note">{e(note)}</p>' if note else ""
    return f"""<header class="sec-head">
    <p class="sec-folio mono"><span class="sec-no">{e(FOLIO.get(anchor, ""))}</span>{e(kicker)}</p>
    <h2 id="{e(title_id)}" class="sec-title">{e(title)}</h2>
    {note_html}
  </header>"""


# --------------------------------------------------------------------------- #
# I — The practice (about / experience / skills)
# --------------------------------------------------------------------------- #
def leader(profile: dict) -> str:
    intro = e(profile["intro"])
    drop = intro[:1]
    rest = intro[1:]
    jobs = "".join(
        f"""<article class="cv-job">
      <p class="cv-when mono"><time>{e(j["from"])}</time> – <time>{e(j["to"])}</time></p>
      <h3 class="cv-role">{e(j["role"])}</h3>
      <p class="cv-org">{e(j["org"])}</p>
      <ul class="cv-points">{"".join(f"<li>{e(pt)}</li>" for pt in j["points"])}</ul>
    </article>"""
        for j in profile["experience"]
    )
    skills = "".join(
        f'<div class="disc"><dt class="mono">{e(s["group"])}</dt>'
        f'<dd>{" · ".join(e(x) for x in s["items"])}</dd></div>'
        for s in profile["skills"]
    )
    edu = "".join(f'<p><b>{e(x["title"])}</b><br>{e(x["detail"])}<br><span class="mono">{e(x["years"])}</span></p>'
                  for x in profile["education"])
    return f"""
<section class="sec sec-leader" id="about" aria-labelledby="leader-title">
  {section_head("about", "leader-title", "The practice", "Concrete, modelled to the bar")}
  <div class="leader-grid">
    <div class="leader-body">
      <p class="leader-lede"><span class="dropcap" aria-hidden="true">{drop}</span><span class="sr">{drop}</span>{rest}</p>
      <div class="cv">{jobs}</div>
    </div>
    <aside class="leader-aside">
      <blockquote class="pull"><p>“Rebar modelled precisely enough to schedule straight from the model.”</p></blockquote>
      <dl class="disciplines">{skills}</dl>
      <div class="edu">
        <h3 class="mono">Education</h3>{edu}
        <h3 class="mono">Languages</h3><p>{e(", ".join(profile["languages"]))}</p>
      </div>
    </aside>
  </div>
</section>"""


# --------------------------------------------------------------------------- #
# II — Selected works (lead feature + every project as a plate)
# --------------------------------------------------------------------------- #
def lead_feature(p: dict) -> str:
    imgs = p["images"]
    fl = storeys(p["title"])
    main_img = opener(p["slug"], imgs[0]["src"],
                      img_tag(imgs[0], p["title"] + " Revit model", "lead-img",
                              sizes="(min-width: 1000px) 62vw, 100vw")
                      + '<span class="plate-rule" aria-hidden="true"></span>',
                      "lead-fig", label=f'Open {p["title"]} gallery')
    props = [("Element", p["slug"].upper()), ("Sheet", p["sheet"]), ("Discipline", p["kind"]),
             ("Programme", p["type"]), ("Location", p["location"] or "Not published"),
             ("Levels", f"G+{fl - 1}"), ("Plates", f'{len(imgs)}{" + film" if p.get("video") else ""}')]
    rows = "".join(f"<div><dt>{e(k)}</dt><dd>{e(val)}</dd></div>" for k, val in props)
    play = (opener(p["slug"], p["video"]["src"],
                   f'Play the build-up <span class="mono">{e(p["video"]["duration"])}</span>',
                   "btn btn-line", video=True)) if p.get("video") else ""
    return f"""<article class="lead" aria-label="Cover feature">
    <figure class="lead-plate">{main_img}
      <figcaption class="plate-cap mono"><span class="plate-no">{e(plate_num(1))}</span>{{3D}} · {e(p["slug"].upper())} · sheet {e(p["sheet"])}</figcaption>
    </figure>
    <div class="lead-copy">
      <p class="lead-kicker mono">Cover feature · changes twice a day</p>
      <h3 class="lead-title">{e(p["title"])}</h3>
      <p class="lead-sum">{e(p["summary"])}</p>
      <dl class="lead-props">{rows}</dl>
      <div class="lead-actions">
        {opener(p["slug"], imgs[0]["src"], f"Open all {len(imgs)} plates", "btn btn-solid")}
        {play}
      </div>
    </div>
  </article>"""


def feature_plate(p: dict, i: int) -> str:
    fl = storeys(p["title"])
    im = p["images"][0]
    inner = (f'<span class="feat-img">{img_tag(im, "", use_thumb=True)}'
             f'<span class="plate-rule" aria-hidden="true"></span></span>'
             f'<span class="feat-cap"><span class="feat-no mono">{e(plate_num(i))}</span>'
             f'<b class="feat-title">{e(p["title"])}</b>'
             f'<span class="feat-meta mono">{e(p["kind"])}</span>'
             f'<span class="feat-foot mono"><span>G+{fl - 1}</span><span>{e(p["location"] or "—")}</span>'
             f'<span>{len(p["images"])} plates{" + film" if p.get("video") else ""} ↗</span></span></span>')
    return (f'<li class="feature" data-type="{e(p["type"])}" data-i="{i}">'
            f'{opener(p["slug"], im["src"], inner, "feature-link", label=f"{p["title"]}: G+{fl - 1}, {len(p["images"])} plates")}'
            f'</li>')


def works(projects: list[dict], featured: dict) -> str:
    counts: dict[str, int] = {}
    for p in projects:
        counts[p["type"]] = counts.get(p["type"], 0) + 1
    known = ["Residential", "Commercial", "Mixed-use"]
    order = ([t for t in known if t in counts]
             + sorted(t for t in counts if t not in known + ["Other"])
             + (["Other"] if "Other" in counts else []))
    # A rubric chip per programme type (validate requires every type to be filterable).
    chips = f'<button type="button" class="rubric-chip" aria-pressed="true" data-filter="all">All <span>{len(projects)}</span></button>'
    chips += "".join(
        f'<button type="button" class="rubric-chip" aria-pressed="false" data-filter="{e(t)}">{e(t)} <span>{counts[t]}</span></button>'
        for t in order
    )
    plates = "".join(feature_plate(p, i) for i, p in enumerate(projects, start=1))
    return f"""
<section class="sec sec-works" id="projects" aria-labelledby="works-title">
  {section_head("projects", "works-title", f"Selected works · {len(projects)} buildings", "Modelled for Mumbai site teams", note="Every building I modelled with the Computer Help BIM team, under a neutral plate number. Open a plate to walk its views.")}
  {lead_feature(featured)}
  <div class="rubric" role="group" aria-label="Filter works by programme">{chips}</div>
  <ol class="feature-index" aria-live="polite">{plates}</ol>
</section>"""


# --------------------------------------------------------------------------- #
# III — Build-up films
# --------------------------------------------------------------------------- #
def films(by_slug: dict, order: list[str]) -> str:
    cams, n = [], 0
    for slug in order:
        p = by_slug.get(slug)
        if not p or not p.get("video"):
            continue
        n += 1
        vobj = p["video"]
        poster = vobj.get("poster") or p["images"][0]["thumb"]
        inner = (f'<span class="film-screen"><img src="{e(poster)}" alt="" loading="lazy" decoding="async">'
                 f'<video muted loop playsinline preload="none" data-src="{e(vobj["src"])}" tabindex="-1"></video>'
                 f'<span class="film-osd mono" aria-hidden="true"><span>Film {n:02d}</span>'
                 f'<span class="film-rec">▶</span></span>'
                 f'<span class="film-tc mono" aria-hidden="true">{e(vobj["duration"])}</span></span>'
                 f'<span class="film-cap"><span class="feat-no mono">{e(plate_num(n))}</span>'
                 f'<b>{e(p["title"])}</b><span class="mono">{e(p["slug"].upper())}</span></span>')
        cams.append(f'<li class="film">{opener(slug, vobj["src"], inner, "film-link", video=True, label="Play the %s build-up" % p["title"])}</li>')
    body = f'<ol class="film-wall">{"".join(cams)}</ol>'
    return f"""
<section class="sec sec-films" id="buildups" aria-labelledby="films-title">
  {section_head("buildups", "films-title", f"Build-up films · {n}", "Construction sequence, rendered from the model", note="Construction-sequence animations rendered from the Revit models. Hover a frame to preview it muted; open it to watch with sound.")}
  {body}
</section>"""


# --------------------------------------------------------------------------- #
# IV — Reinforcement (BBS technical appendix)
# --------------------------------------------------------------------------- #
def appendix(bbs: list[dict]) -> str:
    if not bbs:
        return ""
    items = []
    for i, b in enumerate(bbs):
        cap = (f'<span class="app-cap"><span class="app-no mono">BBS-{i + 1:03d}</span>'
               f'<span class="app-name">{e(b["alt"])}</span><span class="app-rev mono">Rev A</span></span>')
        link = opener("__bbs", b["src"], img_tag(b, b["alt"], use_thumb=True) + cap, "app-link", index=i,
                      label="Open drawing: " + b["alt"])
        items.append(f'<li{" class=extra" if i >= 8 else ""}>{link}</li>')
    more = (f'<button type="button" class="btn btn-line app-more" data-more aria-expanded="false">'
            f'Show all {len(bbs)} drawings</button>') if len(bbs) > 8 else ""
    return f"""
<section class="sec sec-appendix" id="rebar" aria-labelledby="rebar-title">
  {section_head("rebar", "rebar-title", f"Technical appendix · {len(bbs)} drawings", "Reinforcement, scheduled off the model", note="Beam, column, footing and slab reinforcement, detailed in Revit and RC-CADS and scheduled straight from the model.")}
  <ol class="app-list" data-collapsed="true">{"".join(items)}</ol>
  {more}
</section>"""


# --------------------------------------------------------------------------- #
# V — Instruments (the permanent signature skill cards)
# --------------------------------------------------------------------------- #
def instruments() -> str:
    """The signature skill cards, framed as the Instruments section of the issue."""
    skills, _ = signature.load()
    sk = skills["skills"]
    head = (f'<header class="sec-head sig-skills-head">'
            f'<p class="sec-folio mono"><span class="sec-no">{e(FOLIO["skills"])}</span>Instruments · {len(sk["cards"])}</p>'
            f'<h2 id="sig-skills-title" class="sec-title">{e(sk["title"])}</h2>'
            f'<p class="sec-note">{e(sk["intro"])}</p></header>')
    return signature.skills_html(header_html=head, anchor="skills").replace(
        'class="sig-skills"', 'class="sec sec-instruments sig-skills"', 1)


# --------------------------------------------------------------------------- #
# VI / VII — Colophon: editions (revisions) + correspondence (contact)
# --------------------------------------------------------------------------- #
def colophon(site: dict, profile: dict) -> str:
    rows = "".join(
        f'<li><time class="mono" datetime="{e(r["date"])}">{e(fmt_date(r["date"]))}</time>'
        f'<b class="mono">v{e(r["rev"])}</b><span>{e(r["note"])}</span></li>'
        for r in site.get("revisions", [])[:5]
    )
    editions = f"""
<section class="sec sec-editions" id="revisions" aria-labelledby="editions-title">
  {section_head("revisions", "editions-title", f"Editions · rev {site['version']}", "How often this monograph is reset")}
  <ol class="edition-list" aria-label="Latest revisions">{rows}</ol>
  <a class="btn btn-line" href="{CHANGELOG_URL}" rel="noopener">Full edition history ↗</a>
</section>"""
    correspondence = f"""
<section class="sec sec-contact" id="contact" aria-labelledby="contact-title">
  {section_head("contact", "contact-title", "Correspondence", "A model to build, a BBS to schedule, clashes to clear")}
  <div class="corr">
    <a class="corr-mail" href="mailto:{e(profile["email"])}"><span class="corr-dot" aria-hidden="true"></span>{e(profile["email"])}</a>
    <p class="corr-links">
      <a class="btn btn-solid" href="mailto:{e(profile["email"])}">Open a request</a>
      <a class="btn btn-line" href="{e(profile["linkedin"])}" rel="noopener">LinkedIn ↗</a>
      <span class="mono">{e(profile["location"])}</span>
    </p>
  </div>
</section>"""
    return editions + correspondence


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
    bbs = data.get("bbs", [])
    by_slug = {p["slug"]: p for p in projects}
    featured = by_slug.get(site["featured"], projects[0])
    themes = system["themes"]

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
        "title": "Rebar and BBS sheets", "sheet": "S-100", "meta": "Reinforcement documentation", "summary": "",
        "images": [{"src": b["src"], "w": b["w"], "h": b["h"], "alt": b["alt"]} for b in bbs],
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
<main id="main">
{signature.stage_html(profile, projects, opener, anchor="top")}
<div class="issue">
{running_head(profile, site, system, themes)}
{masthead(profile, site, system)}
{leader(profile)}
{works(projects, featured)}
{films(by_slug, site.get("reel", list(by_slug)))}
{appendix(bbs)}
{instruments()}
{colophon(site, profile)}
</div>
</main>
<footer class="foot">
  <p class="mono">{e(system.get("name", ""))} · rev {v} · data date {e(fmt_date(site["date"]))}</p>
  <p>Projects modelled at {e(profile["employer"])}. Build-up soundtracks from Mixkit. <a href="{CHANGELOG_URL}" rel="noopener">Edition history</a></p>
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
