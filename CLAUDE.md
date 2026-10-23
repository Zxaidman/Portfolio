# Maintaining this portfolio

This file is the permanent memory for whoever maintains the site, human or AI. The scheduled job reads it on every run. Keep the README free of code and instructions; everything technical lives here.

## Where the history lives (never delete)

- `CHANGELOG.md`: one entry per version, written automatically by `scripts/portfolio.py refresh`.
- `design/HISTORY.md`: one row per design system (minor) and revamp (major), written by the person or job that ships it. `validate` fails if the current design has no row.
- `design/archive/v<version>-<name>/`: a permanent snapshot of every minor and major design (tokens, CSS, JS, renderer, screenshots). Never edit or delete a snapshot, except the one created in the current run while it is still being fixed.
- Claude Design System artifacts: one per revamp (major), linked from `design/HISTORY.md`.

## The permanent signature (never removed)

Two sections live in their own files and survive every minor and major:

- **Scroll stage** (`scripts/signature.py` `stage_html`, `assets/js/signature.js`, `assets/css/signature.css`): the pinned hero. Scrolling plays a 3D BIM model rendered from an IFC frame by frame: a faint wireframe of the finished building, then elements fly into place storey by storey (columns grow, beams slide in, slabs drop, walls rise, facade flies in), an exploded view while the camera orbits, and the model closing up again. Frames are neutral clay on a transparent background; the canvas tints them to `--sig-model-tint` (default: the theme accent, mix `--sig-model-tint-mix`), so every theme recolours the model. The name fades out, two glass HUD cards float in, a "Built %" meter counts up with the level being placed, the camera pushes in, and a Revit `{3D}` viewport opens and expands into the project showcase. Frames come from `tools/ifc-stage/` + `scripts/stage.py model` and `data/stage.json`. **The hero rotates on every update:** `stage.json` holds IFC models (`models`: `m1`, `m2`, ...; tinted clay, fly-in choreography) and the project build-up videos (`videos`: `s04`, `s12`, ...; background and any on-screen overlays cut out, original colours, the project's public title on the meter). `signature.stage_pool` spreads the models evenly through the videos; the page shows one item (`data/site.json` `stage_pick`) and every refresh (patch, minor and major) moves to the next. A model built from a project's IFC can take that project's video slot (`"replaces": "s12"` on the model), or stay alongside it (`"same_as": "s12"`, as m2 does), in which case the pool places the two as far apart as possible. New IFCs arrive from Zaid and are added by hand, never by a scheduled run; videos are rebuilt by hand with `python3 scripts/stage.py video <id|all>` (overlay boxes are stored per video, e.g. s09's 4D legend and timeline). An optional clip of Zaid can be added as a segment after the model.
- **Skill cards** (`skills_html`): category chips and a grid of cards with a glyph tile, badge, name, one-line description and a link to evidence on the page; hover lift, category-tinted glow that follows the cursor, staggered entrance. Content: `data/skills.json` (hand-edited only).

Rules for every design:
- `render.py` must call `signature.stage_html(...)` as the first section in `<main>` (full-bleed, outside any max-width wrapper) and `signature.skills_html(...)` once, and load `signature.css` (before `main.css`) and `signature.js`. `validate` enforces this; the deploy fails without it.
- Restyle, don't remove. The signature reads only design tokens, so a new design system restyles it automatically. A design may add overrides in its own `main.css` (radius, glass, typography, HUD position) and set `--sig-safe-bottom` if it has a fixed bottom bar. A major may re-choreograph the stage by editing the timeline constants `T` in `signature.js`, or add new behaviour there, but must keep: frame scrubbing, HUD cards, the meter, the expanding viewport/showcase, reduced-motion and no-JS fallbacks.
- Never edit `data/skills.json`, `data/stage.json` or `media/stage/` in a scheduled run.

## How the site works

The page is a static site on GitHub Pages. Its current design is described in `design/system.json` and the newest row of `design/HISTORY.md`; the page always shows the live version and recent revisions.

```
index.html              generated — do not edit by hand
assets/css/main.css     component styles (uses tokens only)
assets/css/tokens.css   generated from design/system.json — do not edit by hand
assets/js/main.js       progressive enhancement: filters, viewer, video previews
data/profile.json       bio, experience, skills, contact      <- edit by hand
data/labels.json        public title / storeys / city per project id  <- edit by hand
data/projects.json      projects, images, videos, BBS sheets  <- written by `sync`
data/site.json          today's featured project, theme, version, revisions
data/media-manifest.json content hashes, so unchanged media is never re-copied
media/                  optimised images (1800px + 720px thumbs), videos, posters
scripts/portfolio.py    CLI: sync, refresh, build, validate, daily, archive, cadence
scripts/render.py       renders index.html from data/*.json
design/system.json      active design system: themes, fonts, scale  -> assets/css/tokens.css
design/HISTORY.md       every design shipped (no repeats)
design/INSPIRATION.md   design brief: the bar, layout archetypes, motions, trend notes
design/archive/         snapshot of every minor and major design, never overwritten
scripts/qa.py           headless browser QA: errors, broken images, overflow, all themes, live scroll stage
scripts/signature.py    permanent signature sections: scroll stage + skill cards (HTML)
scripts/stage.py        packages the stage frames: IFC model renders, project build-up videos, optional clip of Zaid
tools/ifc-stage/        offline IFC -> transparent frames renderer (three.js, headless Chromium); see its README
assets/css/signature.css, assets/js/signature.js   signature styling and scroll engine
data/skills.json        HUD card and skill card content            <- edit by hand
data/stage.json         hero rotation: IFC models + build-up videos  <- written by stage.py
media/stage/            stage frames (desktop + mobile WebP, transparent)
VERSION, CHANGELOG.md   SemVer on a fixed cadence (below)
```

### Projects added by hand

Projects that are not in the BIM-Portfolio source (e.g. built from an IFC Zaid shares) live in
`data/extra-projects.json` (neutral slugs `x01`, `x02`...; title, type, city, summary) with their
images in `media/extra/<slug>/`. `sync` puts them first in `data/projects.json` and never prunes
them. Gallery stills come from the IFC: `tools/ifc-stage/stills.py GEO OUT` renders seven views
(two corners, side, street, aerial, exploded, structure only) and
`python3 scripts/portfolio.py extra-images <slug> OUT` publishes them. Scheduled runs never edit
these. Every project type must have a filter chip (`validate` checks), so a new type such as
Mixed-use stays reachable in every design.

### Media lives in Git LFS

Everything under `media/` that is an image, video or frame (`*.jpg`, `*.webp`, `*.mp4`; see
`.gitattributes`) is stored in Git LFS. The free plan allows 10 GiB storage and 10 GiB download
a month, and every download counts, so:

- **Clone without media:** `GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 ...` (files are small
  pointers). `sync`, `refresh`, `build`, `validate` and the leak check all work on pointers.
- **Before `qa.py`** (minor and major runs): `python3 scripts/portfolio.py media --qa` pulls only
  what the screenshots look at (project images, BBS sheets, posters, the hero item on show).
  `media` without `--qa` pulls everything (manual work only).
- **Deploys** pull media in GitHub Actions from a cache (`.github/workflows/static.yml`), so only
  changed files are downloaded.
- New or changed media is converted to LFS on commit automatically when git-lfs is installed
  (`git lfs install` once per clone). Never commit media without git-lfs installed.

### Requirements

- Python 3.9+
- Pillow, for `sync`/`daily` only: `pip install -r requirements.txt`

### Common tasks

```bash
# A run (what the scheduled task does; slot comes from the current IST time)
git lfs install --skip-smudge     # media stays as LFS pointers (see "Media lives in Git LFS")
git clone --depth 1 https://github.com/aasif-shaikh7/BIM-Portfolio ../BIM-Portfolio
python3 scripts/portfolio.py daily --source ../BIM-Portfolio

# Edited data/profile.json? Re-render and check:
python3 scripts/portfolio.py build

# New hero model from an IFC (never commit the IFC): see tools/ifc-stage/README.md

# Add Zaid's clip after the build (8-10 s, steady camera); needs ffmpeg, numpy, scipy:
python3 scripts/stage.py person path/to/zaid.mp4 --frames 120 && python3 scripts/portfolio.py build

# Preview locally
python3 -m http.server 8000      # then open http://localhost:8000

# What does this run ship? (patch | minor | major)
python3 scripts/portfolio.py cadence --calendar

# New design system (minor) or revamp (major), after changing the design files:
python3 scripts/portfolio.py daily --source ../BIM-Portfolio --minor   # or --major
python3 scripts/portfolio.py media --qa      # pull just the media the screenshots need
python3 scripts/qa.py --out /tmp/qa && python3 scripts/portfolio.py archive --shots /tmp/qa
```

### Update cadence and versions

One scheduled task fires at **5:50 AM, 1:50 PM and 9:50 PM IST** every day (8 hours apart). `python3 scripts/portfolio.py cadence` says what this run ships; `--calendar` lists the next major days.

| Slot | Kind | Version | What changes |
|---|---|---|---|
| 5:50 AM, major day | MAJOR `X.0.0` | Whole revamp: new layout archetype, concept, interactions and motion; a new Claude Design System |
| 5:50 AM, other days | MINOR `x.Y.0` | A new design system: palette (≥ 3 themes), type, scale, components, one new signature motion |
| 1:50 PM and 9:50 PM | PATCH `x.y.Z` | Theme and featured-asset change within the current design, plus new media from the source |

Major days are **Monday, Wednesday and Friday**. Minor runs on the other mornings (Tuesday, Thursday, Saturday, Sunday); patch runs every day, Sunday included. Each slot ships at most once: a retried job does nothing.

Read `design/INSPIRATION.md` before any minor or major. Every minor and major is snapshotted in `design/archive/` and logged in `design/HISTORY.md`. `validate` refuses a design that repeats an earlier one (name, font set or palette) or has no HISTORY row. Design changes ship only after `validate`, the WCAG contrast check, `qa.py` and the leak check all pass.

### Confidentiality

Client project names never appear on the site. Each project is published under a neutral id (`s09` = source slide 9) with the title, storey count and city from `data/labels.json`. To show "G+20 residential tower model", set `"storeys": 20` for that id. Video metadata is stripped, and `mask` covers any burned-in title in a video.

The hero model comes from an IFC that is kept outside the repo; only geometry is extracted (no names, GUIDs, properties or addresses) and only rendered images are published. Never commit an IFC, its file name, or its level/project names.

Every `sync` and `daily` run also performs a **leak check**: it reads the project names from the source repo in memory and fails, so nothing is pushed, if any of them appears in a published path or file.

### Behaviour worth knowing

- **Idempotent:** each slot (date + morning/afternoon/night) ships at most once; rerunning it changes nothing.
- **Light history:** patch commits only touch `data/site.json`, `index.html`, `VERSION` and `CHANGELOG.md`. Media is recopied only when the source file's bytes change.
- **Safe deploys:** the Pages workflow runs `validate` first, so a missing asset or a bad JSON file blocks the deploy instead of shipping a broken page.
- **Pruning:** media that the source no longer provides is deleted, so removed projects disappear from the site.
- **Source format:** `sync` parses the BIM-Portfolio `index.html` (project articles, build-up figures, BBS slides). If that page's markup changes a lot, `sync` refuses to write an empty project list and the job fails loudly.

Build-up soundtracks are from Mixkit (free licence, no attribution required). Code is licensed under GPL-3.0 (see `LICENSE`).
