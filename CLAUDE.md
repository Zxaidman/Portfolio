# Maintaining this portfolio

This file is the portfolio-specific operating manual. Every AI agent must also read the root `AGENT.md`, the universal contract for all future agents. The scheduled job reads these instructions on every run. Keep the README free of code and instructions; everything technical lives here.

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
- **The Vercel mirror** (zxaidman-portfolio.vercel.app) builds from this repo without LFS, so
  its copies of media are pointer files. `vercel.json` runs
  `python3 scripts/portfolio.py build` and publishes the repository root; this regenerates
  `index.html` and design tokens from the current `VERSION` and `data/site.json` on every
  deployment. Preserve its `buildCommand` and `outputDirectory`. Generated HTML and viewer code
  point directly to `https://zxaidman.github.io/Portfolio/media/`; do not restore a Vercel
  `/media` redirect. GitHub Pages serves the actual LFS-backed assets and includes
  `Access-Control-Allow-Origin: *`, required by the canvas frame loader. Do not enable Git LFS on
  Vercel: each Vercel build would download all media and use up the free LFS bandwidth within days.
- New or changed media is converted to LFS on commit automatically when git-lfs is installed
  (`git lfs install` once per clone). Never commit media without git-lfs installed.

### Performance: images, video and first load

Keep the current static-site architecture. Optimize the existing pipeline before adding an external media platform.

Performance rollout status (2026-11-08):
- **Completed — initial load:** `scripts/signature.py` emits the stage poster eagerly with intrinsic dimensions. It remains visible while the first requested frame is unavailable.
- **Completed — scroll-stage requests:** `assets/js/signature.js` waits until the visitor has scrolled and the stage is near the viewport, then requests a small window around the current frame. Concurrency is capped at four (one with Save-Data); decoded image references are capped at 14 (six with Save-Data). Preserve this behavior; never restore whole-sequence preloading.
- **Completed — video cards:** film cards contain poster images only. They do not contain hidden video elements and do not download or autoplay video on hover. Opening a film is an explicit activation; the viewer uses `preload="none"`, plays only after activation (unless reduced-motion is requested), and releases the video source when the viewer closes or changes media.
- **Completed — media delivery:** generated media image/link URLs and the stage frame loader resolve directly to the GitHub Pages media base. The Vercel `/media` redirect was removed. The stage loader sets `crossOrigin="anonymous"` before assigning frame URLs; preserve this because frames are drawn to canvas and the GitHub Pages origin supplies `Access-Control-Allow-Origin: *`.
- **Measured — delivery comparison (Mumbai audit sandbox, 2026-11-08):** a 1 MiB HTTP range request for the same MP4 returned from GitHub Pages in 17 ms total (11.5 ms TTFB) versus 55 ms total (49.3 ms TTFB) through the Vercel 307 redirect. The response was a GitHub Pages Mumbai edge cache hit with byte ranges enabled. This is one warm-request sample, not a real-user percentile or a substitute for broader testing.
- **Measured — video inventory:** 14 MP4s are 1920x1080, H.264 High Profile, yuv420p, 24 fps, approximately 3.2–3.5 Mbps, and roughly 12–13 MB for 30-second clips. They have no audio track. Do not blindly re-encode: a sample CRF 26 test increased size; CRF 28 saved only about 9% with SSIM 0.9948. Retain the current masters unless a better codec/bitrate wins a visual review and a meaningful size target.
- **Not measured:** real browser LCP/INP/CLS, full-page transfer bytes and a throttled mobile Network waterfall remain unmeasured. Do not claim the Core Web Vitals targets have passed.

Implementation order:
1. **Completed:** eager-load the static stage poster, keep it visible as the initial fallback, and prevent frame requests until the visitor scrolls while the stage is near the viewport. Do not add `fetchpriority="high"` until a measurement confirms which resource is the LCP element.
2. **Completed:** load frames around the active scroll position with bounded concurrency and cache; preserve reverse-scroll, resize, reduced-motion and no-JavaScript behavior.
3. **Completed:** render poster-only film cards and attach/play video only after the user explicitly opens a film. Use `preload="none"`; release the source when the viewer closes or changes media. Do not add hover-triggered previews.
4. **Completed:** point all generated media URLs directly to `MEDIA_BASE` on GitHub Pages. Keep CORS enabled for stage frames drawn to canvas. Do not restore the Vercel `/media` redirect or turn on Vercel Git LFS.
5. **Encoding decision:** current MP4 files are already 1080p H.264 at approximately 3.3 Mbps. Test quality/size before changing; keep source masters and require material size savings plus visual review of fine BIM linework.
6. **Images:** keep project cards on thumbnails and full-size files only inside the gallery. Emit correct `srcset`/`sizes` for real display widths and DPR. Add smaller candidates only where measured; preserve fine BIM linework and text.
7. **Verification:** test video click-to-play, reduced-motion manual playback, source release on close/navigation, byte-range playback, image/frame CORS, keyboard/mobile behavior, stage motion and broken-media handling. Capture a cold mobile/desktop Network waterfall and Core Web Vitals before claiming a performance pass.

### Media platform decision

Do not introduce Cloudinary, Cloudflare Images/Stream, Mux, a JavaScript image framework or a custom media service by default. First right-size files, reduce eager requests and use native browser capabilities. If the measured origin/redirect/cache path remains the bottleneck, evaluate one managed edge-media option with a small proof of concept and compare cost, cache-hit ratio, mobile transfer time and operational complexity. Preserve a simple static site and one source of truth.

### Requirements

- Python 3.9+
- Pillow, for `sync`/`daily` only: `pip install -r requirements.txt`

### Common tasks

```bash
# Every human or AI agent works on main only
git switch main
git pull --ff-only origin main

# Scheduled release: upstream source stays in a separate checkout
git lfs install --skip-smudge     # keep this portfolio LFS assets as pointers
git clone --depth 1 https://github.com/aasif-shaikh7/BIM-Portfolio ../BIM-Portfolio
python3 scripts/portfolio.py cadence --calendar
python3 scripts/portfolio.py daily --source ../BIM-Portfolio

# Validate, inspect the diff, then commit and push directly to main
python3 scripts/portfolio.py build
python3 scripts/portfolio.py validate
python3 scripts/portfolio.py media --qa
python3 scripts/qa.py --out /tmp/qa
git status --short
git diff --check
# Stage only the intended files, then:
git commit -m "vX.Y.0: minor: <design name>"
git push origin main

# Edited data/profile.json? Re-render and check:
python3 scripts/portfolio.py build
python3 scripts/portfolio.py validate

# New hero model from an IFC (never commit the IFC): see tools/ifc-stage/README.md

# Add Zaid clip after the build (8-10 s, steady camera); needs ffmpeg, numpy, scipy:
python3 scripts/stage.py person path/to/zaid.mp4 --frames 120 && python3 scripts/portfolio.py build

# Preview locally
python3 -m http.server 8000      # then open http://localhost:8000

# Check the release kind and upcoming major dates
python3 scripts/portfolio.py cadence --calendar
```
### Update cadence and versions

One scheduled task runs at **5:50 AM IST once per day**. All work is performed directly on `main` and pushed after validation; agents must not create branches or pull requests. The afternoon and night invocations are retired; `cadence` returns `skip` for those slots. `python3 scripts/portfolio.py cadence --calendar` lists the next major days.

| Slot | Kind | Version | What changes |
|---|---|---|---|
| 5:50 AM every day except a major date | MINOR `x.Y.0` | A new design system: palette (≥ 3 themes), type, scale, components and one new signature motion |
| 5:50 AM every third day from 2026-11-10 | MAJOR `X.0.0` | Whole revamp: new layout archetype, concept, interactions and motion; create a new Claude Design System |
| 1:50 PM and 9:50 PM | RETIRED | No patch releases; these slots must not bump a version or rotate the hero |

The first major after v7.1.0 is **Tuesday, November 10, 2026**. Further majors occur every three calendar days (November 13, 16, 19, etc.). On a major date, the major release replaces that day's minor release; do not ship two versions on one date. Every other date ships one minor. A retry on the same date is idempotent.

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
