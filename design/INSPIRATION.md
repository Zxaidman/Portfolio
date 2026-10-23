# Design brief and inspiration pool

Read this before every new design system (minor, every morning) and every revamp (major, Monday, Wednesday and Friday). The goal: each morning a visitor should feel they are on a **new site**, and every revamp should look like a different studio built it.

## The bar

- **Minor (new design system, Tue/Thu/Sat/Sun mornings):** a change someone notices in one second. New palette family (≥ 3 themes), a new type pairing, new spacing and corner language, new button/chip/row treatments, and **one new signature motion**. Same page structure.
- **Major (Mon/Wed/Fri mornings):** a whole revamp. New concept, **new layout archetype**, new navigation pattern, new interactions, new motion system. The page structure in `scripts/render.py` and behaviour in `assets/js/main.js` are rewritten. All content stays: the signature scroll stage and skill cards (restyled, never removed), featured project, all 14 projects, build-up videos, rebar/BBS drawings, about, contact, the version and revision history, the image viewer.
- **Never repeat** a layout archetype, a font pairing, a palette family or a signature motion already listed in `design/HISTORY.md`.
- **Research fresh each run.** Search the web for what's current (Awwwards / CSS Design Awards sites of the day, motion sites, trending portfolio posts on LinkedIn, Instagram, X, Dribbble, Behance). Note one or two concrete inspirations in the HISTORY.md row.
- **Ground it in the subject.** BIM, Revit, structural RCC, rebar, construction sequencing, site drawings. The work is the imagery: Revit renders, build-up videos, BBS drawings.

## The permanent signature (never removed)

Two sections live in their own files and survive every minor and major:

- **Scroll stage** (`scripts/signature.py` `stage_html`, `assets/js/signature.js`, `assets/css/signature.css`): the pinned hero. Scrolling plays the Revit build-up frame by frame (tower background cut out, so it floats on any theme), the name fades out, two glass HUD cards float in beside the tower, a "Built %" meter counts up, the camera pushes in, and a Revit `{3D}` viewport opens and expands into the project showcase. Frames come from `scripts/stage.py` and `data/stage.json`; an optional clip of Zaid can be added as a second segment.
- **Skill cards** (`skills_html`): category chips and a grid of cards with a glyph tile, badge, name, one-line description and a link to evidence on the page; hover lift, category-tinted glow that follows the cursor, staggered entrance. Content: `data/skills.json` (hand-edited only).

Rules for every design:
- `render.py` must call `signature.stage_html(...)` as the first section in `<main>` (full-bleed, outside any max-width wrapper) and `signature.skills_html(...)` once, and load `signature.css` (before `main.css`) and `signature.js`. `validate` enforces this; the deploy fails without it.
- Restyle, don't remove. The signature reads only design tokens, so a new design system restyles it automatically. A design may add overrides in its own `main.css` (radius, glass, typography, HUD position) and set `--sig-safe-bottom` if it has a fixed bottom bar. A major may re-choreograph the stage by editing the timeline constants `T` in `signature.js`, or add new behaviour there, but must keep: frame scrubbing, HUD cards, the meter, the expanding viewport/showcase, reduced-motion and no-JS fallbacks.
- Never edit `data/skills.json`, `data/stage.json` or `media/stage/` in a scheduled run.

## Layout archetypes (majors pick one not yet used)

| Archetype | Idea for this portfolio |
|---|---|
| Drawing sheet *(used 2.0.0)* | Title block, drawing register, viewports |
| Bento grid | Varied-size tiles: hero video tile, stats tiles, project tiles, BBS tile; subgrid alignment |
| Horizontal scroll story | Vertical intro that turns into a sideways run through the projects, like walking past a site hoarding |
| Floor-by-floor stack *(used 3.0.0)* | The page is a building: sections are storeys, scroll climbs from foundation to terrace, a level indicator tracks progress |
| Cinematic full-bleed | Each project a full-screen chapter with its build-up video behind oversized type |
| Index / archive list | Dense text index with hover-revealed renders following the cursor; brutalist grid |
| Exploded axonometric | Projects scattered on a canvas like an exploded model, revealed on hover or click |
| Split-screen | Sticky media on one side, scrolling narrative on the other, swapping as you scroll |
| Timeline / Gantt *(used 5.0.0)* | Projects on a 4D construction schedule bar chart; scrubbing the timeline plays the build-ups |
| Magazine / editorial | Large serif headlines, columns, pull quotes from the work, numbered features |
| Dashboard / control room | Dark UI with live-looking panels: element counts, LOD, BBS tonnage, model viewer |
| Card deck / stories | Swipeable story cards like Instagram stories, one project per card |

## Signature motions (each design adds one not yet used)

- Scroll-driven reveal with CSS `animation-timeline: view()` (wrap in `@supports`, fall back to visible)
- Build-up video scrubbed by scroll position instead of autoplay
- View Transitions API for opening a project (`document.startViewTransition`), with a plain fallback
- Kinetic type: variable-font width or weight animating on scroll or hover *(used 3.1.0)*
- Cursor-following media preview over a text index *(used 5.0.0, over the Gantt rows)*
- Horizontal pinned scroll section
- Section-box clipping reveal (a clip-path box sweeping open, like a Revit section box) *(used 3.0.0)*
- Rebar line-draw: SVG stroke-dashoffset drawing bars as the BBS section enters
- Counter roll-up for stats when they enter the viewport *(used 5.0.0, secondary)*
- Gantt bar fill: activity and project bars grow from start to finish on a CSS view() timeline *(used 5.0.0)*
- Magnetic buttons / subtle tilt on project tiles
- Marquee of skills or software, paused on hover
- Grain / noise texture with a slow gradient drift (static under reduced motion)

## Current trend notes (researched 21 Oct 2026)

- Bento grids, oversized hero typography with variable fonts, scroll-driven and scroll-triggered CSS animation, dark-first palettes, restrained glassmorphism, micro-interactions on every state, mixed scroll directions, cinematic video heroes, grain and chromatic textures, accessible-first colour tokens, lightweight pages. Sources: [Line25: Web Design Trends 2026](https://line25.com/articles/web-design-trends-2026/), [Really Good Designs: Web Design Trends 2026](https://reallygooddesigns.com/web-design-trends-2026/), [Chrome: scroll-triggered animations](https://developer.chrome.com/blog/scroll-triggered-animations).
- Each run appends a dated line here with what it found.
- 2026-10-21 (3.0.0): Awwwards Creative Pass keeps surfacing scroll-driven data storytelling ([Scroll-driven PK modelling](https://www.awwwards.com/inspiration/scroll-driven-pk-modeling-substraterx)) and architecture studios using scroll as spatial movement ([Verticité Architecture](https://www.awwwards.com/inspiration/horizontal-scroll-verticite-architecture)). Native CSS scroll timelines (`animation-timeline: scroll()/view()`) are now enough for progress indicators and reveals without JS libraries. Used: a lift car on a scroll timeline and view-timeline section-box reveals.
- 2026-10-22 (3.1.0): Awwwards Creative Pass variable-font collections ([Safari Riot](https://www.awwwards.com/inspiration/variable-font-animation-safari-riot), [Manrope](https://www.awwwards.com/inspiration/variable-font-animation-manrope-font)) and FontLab's [Variable fonts in motion and UI](https://blog.fontlab.com/2026/03/10/variable-fonts-in-motion-and-ui/) (Mar 2026) show type itself as the motion: width/weight axes driven by scroll instead of moving boxes. Used: headings forged from wdth 50/wght 140 to wdth 118/wght 820 on a CSS view() timeline, plus hover-stretch on project titles.
- 2026-10-23 (5.0.0): Awwwards Creative Pass shows schedule UIs used as navigation and storytelling ([Gantt chart with scroll, Wallnut](https://www.awwwards.com/inspiration/gantt-chart-with-scroll-wallnut), [Scroll blueprint](https://www.awwwards.com/inspiration/scroll-blueprint-1)): bars and a moving "now" line give scroll a sense of time. Native View Transitions now cover same-document state changes (filters) with a plain fallback. Used: a fixed week ruler with a data-date line as the nav, Gantt bars filling on view() timelines, View Transitions on the project filter.

## Non-negotiables

- Confidentiality: projects described only by storeys, type and city. Never a project or client name.
- Accessibility: WCAG AA contrast (enforced), visible focus, keyboard-usable viewer, `prefers-reduced-motion` turns motion off, works at 390px wide.
- Performance: no heavy frameworks; CDN scripts only if pinned to an exact version; videos lazy-load.
- Must pass validate, the leak check and `scripts/qa.py` before it ships.
