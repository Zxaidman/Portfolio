# Maintaining this portfolio

This file is the permanent memory for whoever maintains the site, human or AI. The scheduled job reads it on every run. Keep the README free of code and instructions; everything technical lives here.

## Where the history lives (never delete)

- `CHANGELOG.md`: one entry per version, written automatically by `scripts/portfolio.py refresh`.
- `design/HISTORY.md`: one row per weekly design system and monthly rework, written by the person or job that ships it. `validate` fails if the current design has no row.
- `design/archive/v<version>-<name>/`: a permanent snapshot of every weekly and monthly design (tokens, CSS, JS, renderer, screenshots). Never edit or delete a snapshot, except the one created in the current run while it is still being fixed.
- Claude Design System artifacts: one per monthly rework, linked from `design/HISTORY.md`.

## How the site works

The page is a static site on GitHub Pages, designed as a Revit drawing sheet. The title block's revision cell shows the current version, and a different project, build-up video and theme lead the page each day.

```
index.html              generated — do not edit by hand
assets/css/main.css     design tokens + four themes (sheet, blueprint, night, concrete)
assets/js/main.js       progressive enhancement: filters, viewer, video previews
data/profile.json       bio, experience, skills, contact      <- edit by hand
data/labels.json        public title / storeys / city per project id  <- edit by hand
data/projects.json      projects, images, videos, BBS sheets  <- written by `sync`
data/site.json          today's featured project, theme, version, revisions
data/media-manifest.json content hashes, so unchanged media is never re-copied
media/                  optimised images (1800px + 720px thumbs), videos, posters
scripts/portfolio.py    CLI: sync, refresh, build, validate, daily
scripts/render.py       renders index.html from data/*.json
design/system.json      active design system: themes, fonts, scale  -> assets/css/tokens.css
design/HISTORY.md       every design shipped (no repeats)
design/archive/         snapshot of every weekly/monthly design, never overwritten
scripts/qa.py           headless browser QA: errors, broken images, overflow, all themes
VERSION, CHANGELOG.md   SemVer on a fixed cadence (below)
```

### Requirements

- Python 3.9+
- Pillow, for `sync`/`daily` only: `pip install -r requirements.txt`

### Common tasks

```bash
# Daily job (what the 6 AM IST scheduled task runs)
git clone --depth 1 https://github.com/aasif-shaikh7/BIM-Portfolio ../BIM-Portfolio
python3 scripts/portfolio.py daily --source ../BIM-Portfolio

# Edited data/profile.json? Re-render and check:
python3 scripts/portfolio.py build

# Preview locally
python3 -m http.server 8000      # then open http://localhost:8000

# What kind of day is it? (patch | minor | major)
python3 scripts/portfolio.py cadence

# Weekly overhaul / monthly rework, after changing the design files:
python3 scripts/portfolio.py daily --source ../BIM-Portfolio --minor   # or --major
python3 scripts/qa.py --out /tmp/qa && python3 scripts/portfolio.py archive --shots /tmp/qa
```

### Update cadence and versions

| When | Version | What changes |
|---|---|---|
| Every day | PATCH `x.y.Z` | Theme and featured-asset rotation within the current design system, plus new media from the source |
| Mondays | MINOR `x.Y.0` | Complete design-system overhaul: new palette themes, type, scale, component styling |
| 1st of the month | MAJOR `X.0.0` | Complete rework: new concept, layout and interactions, plus a Claude Design System artifact |

Every weekly and monthly design is snapshotted in `design/archive/` and logged in `design/HISTORY.md`, so nothing is lost when the next one ships, and `validate` refuses a design that repeats an earlier one (name, font set, or paper+accent palette). Design changes ship only after `validate`, the WCAG contrast check, `qa.py` and the leak check all pass.

### Confidentiality

Client project names never appear on the site. Each project is published under a neutral id (`s09` = source slide 9) with the title, storey count and city from `data/labels.json`. To show "G+20 residential tower model", set `"storeys": 20` for that id. Video metadata is stripped, and `mask` covers any burned-in title in a video.

Every `sync` and `daily` run also performs a **leak check**: it reads the project names from the source repo in memory and fails, so nothing is pushed, if any of them appears in a published path or file.

### Behaviour worth knowing

- **Idempotent:** rerunning `daily` on the same date produces no diff and no version bump.
- **Light history:** daily commits only touch `data/site.json`, `index.html`, `VERSION` and `CHANGELOG.md`. Media is recopied only when the source file's bytes change.
- **Safe deploys:** the Pages workflow runs `validate` first, so a missing asset or a bad JSON file blocks the deploy instead of shipping a broken page.
- **Pruning:** media that the source no longer provides is deleted, so removed projects disappear from the site.
- **Source format:** `sync` parses the BIM-Portfolio `index.html` (project articles, build-up figures, BBS slides). If that page's markup changes a lot, `sync` refuses to write an empty project list and the job fails loudly.

Build-up soundtracks are from Mixkit (free licence, no attribution required). Code is licensed under GPL-3.0 (see `LICENSE`).
