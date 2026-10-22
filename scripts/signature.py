"""
signature.py — the permanent signature sections of the portfolio.

Two sections stay on the site through every redesign; designs restyle them, never remove them:

  stage_html()   The scroll stage. A pinned hero where scrolling plays the build frame by
                 frame on a canvas: a 3D BIM model rendered from an IFC (elements fly into
                 place storey by storey, exploded view, orbit), tinted to the current theme;
                 or a Revit build-up video; then an optional clip of Zaid. The name fades
                 out, two HUD cards float in either side, a meter shows how much is built and
                 which level is being placed, then the camera pushes in and a Revit-style
                 viewport opens and expands into the project showcase.
  skills_html()  The skill cards: category tabs and a grid of cards with a glyph tile,
                 badge, name, one-line description and a link to evidence on the page.

Behaviour lives in assets/js/signature.js and structure in assets/css/signature.css. Both read
only design tokens (--paper, --ink, --accent, --font, --font-display, ...), so every design
system restyles them automatically; a design may add overrides in its own main.css.

Contract for scripts/render.py (enforced by `portfolio.py validate`):
  * include stage_html(...) once, as the first section inside <main>
  * include skills_html(...) once
  * link assets/css/signature.css and assets/js/signature.js
Content comes from data/skills.json (hand-edited) and data/stage.json (written by stage.py).
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CSS_HREF = "assets/css/signature.css"
JS_SRC = "assets/js/signature.js"


def e(value) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def active_model(stage: dict, site: dict) -> dict | None:
    """The IFC model on show: models rotate, one per design system (data/site.json "stage_model",
    advanced by `portfolio.py refresh` on every minor and major)."""
    models = stage.get("models") or []
    if not models:
        return None
    return models[int(site.get("stage_model", 0)) % len(models)]


def load() -> tuple[dict, dict]:
    """skills.json, and the stage manifest the page plays: the active model (if any) followed by
    any other segments (an optional clip of Zaid). Without models, the stored segments as-is."""
    skills = json.loads((DATA / "skills.json").read_text(encoding="utf-8"))
    raw = json.loads((DATA / "stage.json").read_text(encoding="utf-8"))
    site_path = DATA / "site.json"
    site = json.loads(site_path.read_text(encoding="utf-8")) if site_path.exists() else {}
    model = active_model(raw, site)
    others = [s for s in raw.get("segments", []) if not (model and s["id"] == "buildup")]
    stage = {"segments": ([model] if model else []) + others}
    return skills, stage


# --------------------------------------------------------------------------- #
# Glyphs: simple line icons drawn for this site (no third-party logos).
# 24x24 viewBox, stroked with currentColor.
# --------------------------------------------------------------------------- #
GLYPHS = {
    "frame": '<path d="M5 20V6M19 20V6M3 6h18M3 12h18M5 20h14"/>',
    "rebar": '<path d="M4 7h16M4 12h16M4 17h16"/><circle cx="7" cy="7" r="1.2"/><circle cx="17" cy="12" r="1.2"/><circle cx="10" cy="17" r="1.2"/>',
    "plan": '<path d="M4 4h16v16H4zM4 11h7v9M11 4v4M15 11h5"/>',
    "family": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/>',
    "clash": '<rect x="3" y="5" width="11" height="9"/><rect x="10" y="10" width="11" height="9"/><path d="M10 10h4v4h-4z" fill="currentColor" stroke="none" opacity=".45"/>',
    "pipes": '<path d="M3 8h9a4 4 0 014 4v9M3 14h5a2 2 0 012 2v5"/><path d="M14 3h7"/>',
    "extrude": '<path d="M4 15h9v5H4zM4 15l5-5h9l-5 5M18 10v5l-5 5"/><path d="M4 6h6M4 9h3" opacity=".6"/>',
    "team": '<circle cx="8" cy="8" r="3"/><circle cx="17" cy="9" r="2.4"/><path d="M3 20c0-3 2.5-5 5-5s5 2 5 5M14 20c0-2.4 1.4-4 3-4s3 1.6 3 4"/>',
    "bend": '<path d="M4 18V8a3 3 0 013-3h10a3 3 0 013 3v10"/><path d="M2 18h4M18 18h4"/>',
    "table": '<rect x="3" y="4" width="18" height="16"/><path d="M3 9h18M3 14h18M9 4v16"/>',
    "sheet": '<path d="M5 3h10l4 4v14H5z"/><path d="M15 3v4h4M8 12h8M8 16h5"/>',
    "export": '<path d="M12 3l7 4v6M12 3L5 7v10l7 4 4-2.3"/><path d="M15 17h6M18 14l3 3-3 3"/>',
    "cube": '<path d="M12 2l9 5v10l-9 5-9-5V7z"/><path d="M12 12l9-5M12 12v10M12 12L3 7"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/><path d="M3 17.5l9 5 9-5" opacity=".6"/>',
    "compass": '<path d="M12 3v3M12 6l-6 15M12 6l6 15M8 15h8"/><circle cx="12" cy="6" r="1.4"/>',
    "grid": '<rect x="3" y="3" width="18" height="18"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/>',
}


def glyph(key: str) -> str:
    body = GLYPHS.get(key, GLYPHS["cube"])
    return (f'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')


# --------------------------------------------------------------------------- #
# Scroll stage
# --------------------------------------------------------------------------- #
def _hud(card: dict, cls: str) -> str:
    tags = "".join(f"<li>{e(t)}</li>" for t in card.get("tags", []))
    return f"""<article class="sig-hud {cls}">
      <p class="sig-eyebrow">{e(card["eyebrow"])}</p>
      <h3>{e(card["title"])}</h3>
      <p>{e(card["text"])}</p>
      <ul class="sig-tags" aria-label="Tools">{tags}</ul>
    </article>"""


def _showcase(projects: list[dict], show: dict, profile: dict, opener) -> str:
    groups: dict[str, list[dict]] = {}
    for p in projects:
        groups.setdefault(p["type"], []).append(p)
    order = [t for t in ("Residential", "Commercial", "Other") if t in groups]
    tabs = "".join(
        f'<button type="button" class="sig-tab" role="tab" id="sig-tab-{i}" aria-controls="sig-panel-{i}" '
        f'aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}">'
        f'<span>{e(t)}</span><span class="sig-count">{len(groups[t]):02d}</span></button>'
        for i, t in enumerate(order)
    )
    panels = []
    for i, t in enumerate(order):
        cards = []
        for p in groups[t][:4]:
            im = p["images"][0]
            meta = " · ".join(x for x in (p["kind"], p["location"]) if x)
            media = "build-up" if p.get("video") else "views"
            inner = (f'<span class="sig-proj-img"><img src="{e(im["thumb"])}" alt="" width="{im["w"]}" '
                     f'height="{im["h"]}" loading="lazy" decoding="async"></span>'
                     f'<span class="sig-proj-copy"><span class="sig-eyebrow">{e(p["sheet"])} · {e(meta)}</span>'
                     f'<b>{e(p["title"])}</b><span class="sig-proj-foot">{len(p["images"])} views'
                     f'{" + build-up" if p.get("video") else ""}<span aria-hidden="true">↗</span></span></span>')
            cards.append(opener(p["slug"], im["src"], inner, "sig-proj",
                                label=f'Open {p["title"]}, {len(p["images"])} views'))
        panels.append(f'<div class="sig-panel" role="tabpanel" id="sig-panel-{i}" aria-labelledby="sig-tab-{i}"'
                      f'{"" if i == 0 else " hidden"}><p class="sig-panel-title">{e(t)}.</p>'
                      f'<div class="sig-proj-grid">{"".join(cards)}</div></div>')
    stats = "".join(f'<li><b>{e(s["value"])}</b><span>{e(s["label"])}</span></li>' for s in profile["stats"])
    return f"""<div class="sig-screen" aria-label="Project showcase">
      <div class="sig-chrome">
        <span class="sig-chrome-tab">{{3D}} Showcase</span>
        <span class="sig-chrome-path">{e(show["path"])}</span>
        <span class="sig-status">{e(show["status"])}</span>
      </div>
      <div class="sig-screen-body">
        <aside class="sig-side">
          <p class="sig-eyebrow">Project types</p>
          <div class="sig-tabs" role="tablist" aria-label="Project types">{tabs}</div>
          <ul class="sig-stats">{stats}</ul>
          <div class="sig-side-foot"><b>{e(profile["name"])}</b><span>{e(profile["location"])}</span>
            <a class="sig-btn" href="mailto:{e(profile["email"])}">Email Zaid <span aria-hidden="true">↗</span></a></div>
        </aside>
        <div class="sig-panels">
          <h2 class="sig-screen-title">{e(show["heading"])}</h2>
          {"".join(panels)}
          <a class="sig-next" href="#projects">All {len(projects)} projects <span aria-hidden="true">↓</span></a>
        </div>
      </div>
    </div>"""


POSTER_ALT = {
    "model": "Completed 3D BIM model of a residential building, structure and facade",
    "buildup": "Completed Revit model of a residential tower",
}


def stage_html(profile: dict, projects: list[dict], opener, anchor: str = "top") -> str:
    """The pinned scroll stage. `opener(slug, href, inner, cls, label=...)` is the design's
    viewer-link helper, so showcase cards open the same gallery as the rest of the page."""
    skills, stage = load()
    st = skills["stage"]
    segs = stage["segments"]
    first = segs[0]
    left = next((c for c in st["cards"] if c["side"] == "left"), st["cards"][0])
    right = next((c for c in st["cards"] if c["side"] == "right"), st["cards"][-1])
    # Letters animate in one by one; they are grouped by word so a narrow screen wraps between words.
    words, i = [], 0
    for word in profile["name"].upper().split():
        spans = "".join(f'<span class="sig-l" style="--i:{i + k}">{e(ch)}</span>' for k, ch in enumerate(word))
        words.append(f'<span class="sig-w">{spans}</span>')
        i += len(word) + 1
    letters = '<span class="sig-gap"> </span>'.join(words)
    first_name, _, last_name = profile["name"].partition(" ")
    status = f'<span class="sig-dot">{e(st.get("status", "Open to BIM roles"))}</span>' if profile.get("available") else ""
    manifest = json.dumps(stage, separators=(",", ":"))
    return f"""
<section class="sig-stage" id="{e(anchor)}" data-sig="stage" aria-labelledby="sig-name">
  <script type="application/json" id="sig-stage-data">{manifest}</script>
  <div class="sig-pin">
    <img class="sig-poster" src="{e(first.get("poster") or f'{first["desktop"]["dir"]}/f{first["count"]:03d}.webp')}" alt="{e(first.get("alt") or POSTER_ALT.get(first["id"], POSTER_ALT["buildup"]))}" width="{first["desktop"]["w"]}" height="{first["desktop"]["h"]}" loading="lazy">
    <canvas class="sig-canvas" aria-hidden="true"></canvas>
    <div class="sig-hero">
      <div class="sig-hero-top"><span>{e(st["eyebrow"])}</span>{status}</div>
      <h1 id="sig-name" class="sig-name" aria-label="{e(profile["name"])}"><span class="sig-name-row" aria-hidden="true">{letters}</span></h1>
      <div class="sig-hero-foot">
        <p class="sig-lede">{e(profile["headline"])}</p>
        <div class="sig-actions">
          <a class="sig-btn sig-btn-solid" href="#projects">See the projects</a>
          <a class="sig-btn" href="mailto:{e(profile["email"])}">Email {e(first_name)}</a>
        </div>
      </div>
    </div>
    {_hud(left, "sig-hud-l")}
    {_hud(right, "sig-hud-r")}
    <div class="sig-meter" aria-hidden="true"><span>{e(st["meter_label"])}</span><b data-sig-meter>0%</b><i><em data-sig-bar></em></i><small data-sig-phase></small></div>
    <p class="sig-hint" aria-hidden="true"><span class="sig-hint-arrow">↓</span>{e(st["hint"])}</p>
    {_showcase(projects, st["showcase"], profile, opener)}
  </div>
</section>"""


# --------------------------------------------------------------------------- #
# Skill cards
# --------------------------------------------------------------------------- #
def skills_html(header_html: str = "", anchor: str = "skills") -> str:
    """Skill cards. `header_html` is the design's own section heading (datum, eyebrow...)."""
    skills, _ = load()
    sk = skills["skills"]
    cats = {c["id"]: c for c in sk["categories"]}
    tabs = '<button type="button" class="sig-chip" aria-pressed="true" data-sig-filter="all">All <span>' \
           f'{len(sk["cards"])}</span></button>'
    tabs += "".join(
        f'<button type="button" class="sig-chip" aria-pressed="false" data-sig-filter="{e(c["id"])}">{e(c["label"])} '
        f'<span>{sum(1 for k in sk["cards"] if k["category"] == c["id"])}</span></button>'
        for c in sk["categories"]
    )
    cards = []
    for i, k in enumerate(sk["cards"]):
        cat = cats[k["category"]]
        cards.append(f"""<li class="sig-skill" data-cat="{e(k["category"])}" style="--hue:{int(cat["hue"])};--i:{i}">
        <span class="sig-skill-glow" aria-hidden="true"></span>
        <div class="sig-skill-top"><span class="sig-glyph">{glyph(k["glyph"])}</span><span class="sig-badge">{e(k["badge"])}</span></div>
        <h3>{e(k["name"])}</h3>
        <p>{e(k["text"])}</p>
        <a class="sig-skill-foot" href="{e(k["link"])}"><span>{e(cat["label"])}</span><span aria-hidden="true">↗</span><span class="sig-sr">: see the work for {e(k["name"])}</span></a>
      </li>""")
    default_header = (f'<header class="sig-skills-head"><p class="sig-eyebrow">Skills and expertise</p>'
                      f'<h2 id="sig-skills-title">{e(sk["title"])}</h2><p>{e(sk["intro"])}</p></header>')
    return f"""
<section class="sig-skills" id="{e(anchor)}" data-sig="skills" aria-labelledby="sig-skills-title">
  {header_html or default_header}
  <div class="sig-chips" role="group" aria-label="Filter skills">{tabs}</div>
  <ul class="sig-skill-grid" aria-live="polite">{"".join(cards)}</ul>
</section>"""
