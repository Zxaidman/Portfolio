"""
render.py — builds index.html from data/profile.json, data/projects.json and data/site.json.

Design: "Coordination room" (v6.0.0). The page is a BIM coordination control room, the screen
wall a site team watches during a federated model review:

  * The permanent scroll stage opens the page (signature.py), full-bleed.
  * After it, the "room": a Revit-style Project Browser docked on the left (a tree of Views,
    Sheets, Families and Project information that highlights where you are, with a live clock
    and a display switch), and a wall of dockable dashboard panels on a 12-column grid.
  * Panels: a telemetry ticker, a KPI strip counted from the model data, the active view with
    a properties palette, the model browser (every project, a storey gauge, filter and sort),
    a bank of site-camera monitors playing the build-ups, the BBS sheet register, the families
    (the signature skill cards), the team, the event log (revisions) and a request panel.
  * On phones the browser becomes a sticky strip of tabs across the top.

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
RHYTHM = ("The room is rebuilt on a schedule: a whole revamp every Monday, Wednesday and Friday, "
          "a new design system on the other mornings, and the featured project changes twice a day.")

# The Project Browser tree: (group, [(anchor, panel code, label)]).
BROWSER = [
    ("Views (3D)", [("featured", "VW-01", "Active view"), ("projects", "VW-02", "Model browser"),
                    ("buildups", "VW-03", "Site cameras")]),
    ("Sheets", [("rebar", "SH-01", "BBS register")]),
    ("Families", [("skills", "FM-01", "Loaded families")]),
    ("Project information", [("about", "PI-01", "Team"), ("revisions", "PI-02", "Event log"),
                             ("contact", "PI-03", "Requests")]),
]


def e(value) -> str:
    """HTML-escape any value (attribute-safe)."""
    return escape(str(value if value is not None else ""), quote=True)


def fmt_date(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return iso or ""


def code_of(anchor: str) -> str:
    return next(c for _, items in BROWSER for a, c, _ in items if a == anchor)


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


def bar(anchor: str, title_id: str, title: str, tools: str = "") -> str:
    """A panel's title bar: status LED, panel code, title, and a small readout on the right."""
    tools_html = f'<span class="pnl-tools mono">{tools}</span>' if tools else ""
    return (f'<header class="pnl-bar"><span class="pnl-led" aria-hidden="true"></span>'
            f'<span class="pnl-code mono">{e(code_of(anchor))}</span>'
            f'<h2 id="{e(title_id)}" class="pnl-title">{e(title)}</h2>{tools_html}</header>')


def panel(anchor: str, title_id: str, title: str, body: str, cls: str, note: str = "", tools: str = "") -> str:
    note_html = f'<p class="pnl-note">{e(note)}</p>' if note else ""
    return f"""
<section class="pnl {cls}" id="{e(anchor)}" aria-labelledby="{e(title_id)}">
  {bar(anchor, title_id, title, tools)}
  <div class="pnl-body">{note_html}{body}</div>
</section>"""


# --------------------------------------------------------------------------- #
# Project Browser (navigation)
# --------------------------------------------------------------------------- #
def browser(profile: dict, site: dict, themes: dict) -> str:
    groups = "".join(
        f'<li class="pb-group"><p class="pb-node mono" aria-hidden="true">{e(g)}</p><ul>'
        + "".join(f'<li><a href="#{e(a)}" data-spy="{e(a)}"><span class="pb-code mono">{e(c)}</span>'
                  f'<span class="pb-label">{e(lbl)}</span></a></li>' for a, c, lbl in items)
        + "</ul></li>"
        for g, items in BROWSER
    )
    current = site.get("theme", next(iter(themes), ""))
    swatches = "".join(
        f'<button type="button" class="pb-theme" data-theme-set="{e(t)}" aria-pressed="{"true" if t == current else "false"}">'
        f'<span class="pb-swatch" aria-hidden="true" style="--sw-p:{e(th["paper"])};--sw-a:{e(th["accent"])}"></span>{e(t)}</button>'
        for t, th in themes.items()
    )
    return f"""<aside class="browser" aria-label="Project browser">
  <div class="pb-head">
    <a class="pb-mark" href="#top" aria-label="{e(profile["name"])}, back to the start"><b>ZS</b><span>Coordination room</span></a>
    <p class="pb-clock mono" aria-hidden="true"><span class="pb-live">Live</span><b data-clock>{e(fmt_date(site.get("date", "")))}</b><span>IST</span></p>
  </div>
  <nav class="pb-nav" aria-label="Sections">
    <p class="pb-root mono" aria-hidden="true">Project Browser</p>
    <ul class="pb-tree">{groups}</ul>
  </nav>
  <div class="pb-display" role="group" aria-label="Display theme" hidden>
    <p class="mono">Display</p>
    <div class="pb-themes">{swatches}</div>
  </div>
  <p class="pb-foot mono">Rev {e(site["version"])} &middot; {e(fmt_date(site.get("date", "")))}</p>
</aside>"""


# --------------------------------------------------------------------------- #
# Panels
# --------------------------------------------------------------------------- #
def ticker(projects: list[dict], bbs: list[dict], site: dict, featured: dict) -> str:
    vids = sum(1 for p in projects if p.get("video"))
    items = [
        f"{len(projects)} models online",
        f"{vids} camera feeds",
        f"{len(bbs)} BBS sheets issued",
        f"Active view {featured['slug'].upper()}: {featured['title']}",
        f"Rev {site['version']}",
        f"Display {site.get('theme', '')}",
        "Clash status: resolved before site",
        "Rebar scheduled straight from the model",
    ]
    row = "".join(f"<li>{e(t)}</li>" for t in items)
    return f"""<div class="ticker" aria-label="Status">
  <p class="ticker-tag mono" aria-hidden="true">Telemetry</p>
  <div class="ticker-win"><ul class="ticker-row">{row}</ul><ul class="ticker-row" aria-hidden="true">{row}</ul></div>
</div>"""


def kpis(projects: list[dict], bbs: list[dict], profile: dict) -> str:
    total_fl = sum(storeys(p["title"]) for p in projects)
    tallest = max(projects, key=lambda p: storeys(p["title"]))
    cities = sorted({p["location"] for p in projects if p.get("location")})
    vids = sum(1 for p in projects if p.get("video"))
    top = max(storeys(p["title"]) for p in projects)
    spark = "".join(f'<i style="--v:{storeys(p["title"]) / top:.3f}"></i>' for p in projects)
    tiles = [
        ("Models", str(len(projects)), "Revit and IFC models on the wall", ""),
        ("Storeys", str(total_fl), "floors modelled, all projects", f'<span class="kpi-spark" aria-hidden="true">{spark}</span>'),
        ("Tallest", f"G+{storeys(tallest['title']) - 1}", tallest["title"].replace(f"G+{storeys(tallest['title']) - 1} ", ""), ""),
        ("Feeds", str(vids), "build-up animations", ""),
        ("Sheets", str(len(bbs)), "rebar and BBS drawings", ""),
        ("Cities", str(len(cities)), ", ".join(cities), ""),
    ]
    tiles += [("Profile", s["value"], s["label"], "") for s in profile["stats"]]
    lis = "".join(
        f'<li class="kpi"><p class="kpi-k mono">{e(k)}</p><b class="kpi-v" data-count>{e(v)}</b>'
        f'<p class="kpi-l">{e(lab)}</p>{extra}</li>'
        for k, v, lab, extra in tiles
    )
    return f"""
<section class="pnl pnl-kpis" aria-labelledby="kpi-title">
  <header class="pnl-bar"><span class="pnl-led" aria-hidden="true"></span><span class="pnl-code mono">KPI</span><h2 id="kpi-title" class="pnl-title">Model telemetry</h2><span class="pnl-tools mono">from the model data</span></header>
  <div class="pnl-body"><ul class="kpi-strip">{lis}</ul></div>
</section>"""


def active_view(p: dict) -> str:
    imgs = p["images"]
    thumbs = "".join(
        f'<li>{opener(p["slug"], im["src"], img_tag(im, "", use_thumb=True), "av-thumb", index=i, label="Open view %d of %s" % (i + 1, p["title"]))}</li>'
        for i, im in enumerate(imgs[1:7], start=1)
    )
    video_btn = (opener(p["slug"], p["video"]["src"], f'Play the build-up <span class="mono">{e(p["video"]["duration"])}</span>',
                        "btn btn-line", video=True)) if p.get("video") else ""
    main_img = opener(p["slug"], imgs[0]["src"],
                      img_tag(imgs[0], p["title"] + " Revit model", sizes="(min-width: 1100px) 55vw, 100vw")
                      + '<span class="av-reticle" aria-hidden="true"></span>',
                      "av-main", label=f'Open {p["title"]} gallery')
    fl = storeys(p["title"])
    props = [("Element ID", p["slug"].upper()), ("Sheet", p["sheet"]), ("Type", p["kind"]),
             ("Category", p["type"]), ("City", p["location"] or "Not published"), ("Levels", f"{fl} above ground"),
             ("Views", f'{len(imgs)}{" + build-up" if p.get("video") else ""}')]
    rows = "".join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in props)
    body = f"""<div class="av-grid">
    <figure class="av-figure">{main_img}<figcaption class="mono"><span class="av-rec">Active</span>{{3D}} &middot; {e(p["slug"].upper())} &middot; sheet {e(p["sheet"])}</figcaption></figure>
    <div class="av-side">
      <h3 class="av-title">{e(p["title"])}</h3>
      <p class="av-summary">{e(p["summary"])}</p>
      <div class="av-props"><p class="av-props-head mono">Properties</p><dl>{rows}</dl></div>
      <div class="actions">
        {opener(p["slug"], imgs[0]["src"], f"Open all {len(imgs)} views", "btn btn-solid")}
        {video_btn}
      </div>
    </div>
  </div>
  <ul class="av-thumbs">{thumbs}</ul>"""
    return panel("featured", "featured-title", "Active view", body, "pnl-active",
                 note="The model on the main screen. It changes twice a day.", tools="Changes twice a day")


def model_browser(projects: list[dict]) -> str:
    counts: dict[str, int] = {}
    for p in projects:
        counts[p["type"]] = counts.get(p["type"], 0) + 1
    # every type gets a chip: the usual ones first, any new type (e.g. Mixed-use) next, Other last
    known = ["Residential", "Commercial", "Mixed-use"]
    order = ([t for t in known if t in counts] + sorted(t for t in counts if t not in known + ["Other"])
             + (["Other"] if "Other" in counts else []))
    filters = f'<button type="button" class="chip" aria-pressed="true" data-filter="all">All <span>{len(projects)}</span></button>'
    filters += "".join(
        f'<button type="button" class="chip" aria-pressed="false" data-filter="{e(t)}">{e(t)} <span>{counts[t]}</span></button>'
        for t in order
    )
    sorts = ('<div class="mb-sort" role="group" aria-label="Sort models" hidden>'
             '<span class="mono">Sort</span>'
             '<button type="button" class="seg" aria-pressed="true" data-sort="id">ID</button>'
             '<button type="button" class="seg" aria-pressed="false" data-sort="height">Height</button></div>')
    tallest = max(storeys(p["title"]) for p in projects)
    tiles = []
    for i, p in enumerate(projects):
        fl = storeys(p["title"])
        inner = (f'<span class="mb-img">{img_tag(p["images"][0], "", use_thumb=True)}'
                 f'<span class="mb-id mono">{e(p["slug"].upper())}</span>'
                 f'<span class="av-reticle" aria-hidden="true"></span></span>'
                 f'<span class="mb-copy"><b class="mb-title">{e(p["title"])}</b>'
                 f'<span class="mb-meta">{e(p["kind"])}</span>'
                 f'<span class="mb-gauge" aria-hidden="true"><i style="--g:{fl / tallest:.4f}"></i></span>'
                 f'<span class="mb-foot mono"><span>{fl} fl</span><span>{e(p["location"] or "—")}</span>'
                 f'<span>{len(p["images"])} views{" + video" if p.get("video") else ""}</span></span></span>')
        tiles.append(f'<li class="mb-tile" data-type="{e(p["type"])}" data-i="{i}" data-h="{fl}" '
                     f'style="view-transition-name:mb-{e(p["slug"])}">'
                     f'{opener(p["slug"], p["images"][0]["src"], inner, "mb-link", label=f"{p["title"]}: {fl} floors, {len(p["images"])} views")}</li>')
    body = f"""<div class="mb-tools"><div class="filters" role="group" aria-label="Filter projects by type">{filters}</div>{sorts}</div>
  <ol class="mb-grid" aria-live="polite">{"".join(tiles)}</ol>"""
    return panel("projects", "projects-title", f"Model browser: {len(projects)} projects", body, "pnl-models",
                 note="Every project I modelled with the Computer Help BIM team. The gauge is the building's height. Open a model to walk its views.",
                 tools=f"{len(projects)} online")


def cameras(projects_by_slug: dict, order: list[str]) -> str:
    cams = []
    n = 0
    for slug in order:
        p = projects_by_slug.get(slug)
        if not p or not p.get("video"):
            continue
        n += 1
        v = p["video"]
        poster = v.get("poster") or p["images"][0]["thumb"]
        inner = (f'<span class="cam-screen"><img src="{e(poster)}" alt="" loading="lazy" decoding="async">'
                 f'<video muted loop playsinline preload="none" data-src="{e(v["src"])}" tabindex="-1"></video>'
                 f'<span class="cam-osd mono" aria-hidden="true"><span class="cam-no">CAM {n:02d}</span>'
                 f'<span class="cam-rec">REC</span></span>'
                 f'<span class="cam-tc mono" aria-hidden="true">{e(v["duration"])}</span>'
                 f'<span class="cam-play" aria-hidden="true">&#9654;</span></span>'
                 f'<span class="cam-cap"><b>{e(p["title"])}</b><span class="mono">{e(p["slug"].upper())}</span></span>')
        cams.append(f'<li class="cam">{opener(slug, v["src"], inner, "cam-link", video=True, label="Play the %s build-up" % p["title"])}</li>')
    body = f'<ul class="cam-wall">{"".join(cams)}</ul>'
    return panel("buildups", "cams-title", "Site cameras", body, "pnl-cams",
                 note="Construction-sequence animations rendered from the Revit models. Hover a monitor to preview it muted, open it to watch with sound.",
                 tools=f"{n} feeds")


def sheet_register(bbs: list[dict]) -> str:
    if not bbs:
        return ""
    items = []
    for i, b in enumerate(bbs):
        cap = (f'<span class="sr-cap"><span class="sr-no mono">BBS-{i + 1:03d}</span>'
               f'<span class="sr-name">{e(b["alt"])}</span><span class="sr-rev mono">Rev A</span></span>')
        link = opener("__bbs", b["src"], img_tag(b, b["alt"], use_thumb=True) + cap, "sr-link", index=i,
                      label="Open drawing: " + b["alt"])
        items.append(f'<li{" class=extra" if i >= 8 else ""}>{link}</li>')
    items = "".join(items)
    more = (f'<button type="button" class="btn btn-line sr-more" data-more aria-expanded="false">'
            f'Show all {len(bbs)} sheets</button>') if len(bbs) > 8 else ""
    body = f'<ol class="sr-list" data-collapsed="true">{items}</ol>{more}'
    return panel("rebar", "rebar-title", "BBS sheet register", body, "pnl-sheets",
                 note="Beam, column, footing and slab reinforcement, detailed in Revit and RC-CADS and scheduled straight from the model.",
                 tools=f"{len(bbs)} sheets")


def families() -> str:
    """The signature skill cards, docked as the Families panel."""
    skills, _ = signature.load()
    sk = skills["skills"]
    head = (bar("skills", "sig-skills-title", sk["title"], f'{len(sk["cards"])} loaded')
            + f'<p class="pnl-note fam-note">{e(sk["intro"])}</p>')
    return signature.skills_html(header_html=head, anchor="skills").replace(
        'class="sig-skills"', 'class="pnl pnl-families sig-skills"', 1)


def team(profile: dict) -> str:
    exp = "".join(
        f"""<article class="tm-job">
      <p class="tm-when mono"><time>{e(j["from"])}</time> &rarr; <time>{e(j["to"])}</time></p>
      <h3>{e(j["role"])}</h3>
      <p class="meta">{e(j["org"])}</p>
      <ul>{"".join(f"<li>{e(pt)}</li>" for pt in j["points"])}</ul>
    </article>"""
        for j in profile["experience"]
    )
    skills = "".join(
        f'<div><dt class="mono">{e(s["group"])}</dt><dd>{"".join(f"<span>{e(x)}</span>" for x in s["items"])}</dd></div>'
        for s in profile["skills"]
    )
    edu = "".join(f'<p><b>{e(x["title"])}</b>, {e(x["years"])}<br>{e(x["detail"])}</p>' for x in profile["education"])
    body = f"""<p class="tm-intro">{e(profile["intro"])}</p>
  <div class="tm-grid">
    <div class="tm-jobs">{exp}</div>
    <aside class="tm-side">
      <dl class="tm-skills">{skills}</dl>
      <div class="tm-edu"><h3 class="mono">Education</h3>{edu}<h3 class="mono">Languages</h3><p>{e(", ".join(profile["languages"]))}</p></div>
    </aside>
  </div>"""
    return panel("about", "about-title", f'Team: {profile["name"]}', body, "pnl-team", tools=e(profile["location"]))


def event_log(site: dict) -> str:
    rows = "".join(
        f'<li><time class="mono" datetime="{e(r["date"])}">{e(fmt_date(r["date"]))}</time>'
        f'<b class="mono">v{e(r["rev"])}</b><span>{e(r["note"])}</span></li>'
        for r in site.get("revisions", [])[:5]
    )
    body = f"""<p class="log-rhythm">{e(RHYTHM)}</p>
  <ol class="log-list" aria-label="Latest revisions">{rows}</ol>
  <a class="btn btn-line" href="{CHANGELOG_URL}" rel="noopener">Full revision history</a>"""
    return panel("revisions", "rev-title", f"Event log: rev {site['version']}", body, "pnl-log", tools="Latest 5")


def requests(profile: dict) -> str:
    body = f"""<p class="rq-lede">Got a model that needs building, a BBS that needs scheduling or clashes that need clearing?</p>
  <a class="rq-mail" href="mailto:{e(profile["email"])}"><span class="rq-led" aria-hidden="true"></span>{e(profile["email"])}</a>
  <p class="rq-links">
    <a class="btn btn-solid" href="mailto:{e(profile["email"])}">Open a request</a>
    <a class="btn btn-line" href="{e(profile["linkedin"])}" rel="noopener">LinkedIn</a>
    <span class="mono">{e(profile["location"])}</span>
  </p>"""
    return panel("contact", "contact-title", "Requests", body, "pnl-request", tools="Channel open")


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
<div class="room">
{browser(profile, site, themes)}
<div class="wall">
{ticker(projects, bbs, site, featured)}
{kpis(projects, bbs, profile)}
{active_view(featured)}
{model_browser(projects)}
{cameras(by_slug, site.get("reel", list(by_slug)))}
{sheet_register(bbs)}
{families()}
{team(profile)}
{event_log(site)}
{requests(profile)}
</div>
</div>
</main>
<footer class="foot">
  <p class="mono">Coordination room &middot; rev {v} &middot; data date {e(fmt_date(site["date"]))}</p>
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
