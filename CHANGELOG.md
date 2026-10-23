# Changelog

All notable changes. Versions follow SemVer (MAJOR.MINOR.PATCH).

## [5.0.0] - 2026-10-23 (morning)
- Revamp (new layout): Four-D programme design system. Synced new project media. Featured G+20 sea-facing residential tower model, baseline theme, hero model m1.

## [4.2.2] - 2026-10-22 (night)
- Night theme and asset change: Synced new project media. Featured G+10 residential block model, quench theme.

## [4.2.1] - 2026-10-22 (fix)
- Hero models: the ground shadow is now a soft contact shadow that fades with distance from the building; the tall tower's long shadow no longer ends in a hard straight edge.

## [4.2.0] - 2026-10-22 (signature)
- The hero now has a rotation of IFC models and shows one at a time; every new design system (each morning's minor or major) moves to the next model, while patches keep it.
- Added a second model: a G+20 twin-tower residential building with basement, three podium levels and an amenity floor (architecture and structure merged, 7,350 elements). It is on show now; the G+4 building returns with the next design system.
- The meter names each level of the model being built (Basement, Podium 1-3, Amenity, Level 5 ... Level 20, Terrace) using generic labels only.
- The ground shadow now fades out softly at the edges of the frame instead of ending in a hard line.

## [4.1.0] - 2026-10-22 (signature)
- The scroll stage now plays a real 3D BIM model built from an IFC instead of a screen recording: a faint wireframe of the finished building, then columns grow, beams slide in, slabs drop, walls rise and the facade flies in, storey by storey, while the camera orbits. The storeys then separate into an exploded view and close up again before the push-in.
- The model is tinted to each day's theme, keeping its shading, so it changes colour with every design system and patch.
- The build meter now names the level being placed (Foundation, Ground floor, Level 1 ... Terrace, Exploded view) and reaches 100% when the building is fully assembled.
- New offline renderer (tools/ifc-stage) that keeps only geometry from an IFC; no names, properties or addresses are published.

## [4.0.0] - 2026-10-22 (signature)
- Signature scroll stage: the hero is now pinned and scrolling builds a Revit tower floor by floor (144 frames, background cut out so it floats on every theme). The name fades out, HUD cards float in beside the tower, a "Built %" meter counts up, then the camera pushes into a Revit {3D} viewport that expands into the project showcase.
- Signature skill cards: 16 cards in four categories with filter chips, glyph tiles, badges, links to evidence, hover lift and a cursor-following glow.
- Both are permanent: every future design system and revamp restyles them but cannot remove them (enforced by validate and the deploy check). Reduced-motion and no-JavaScript visitors get a static layout.

## [3.1.1] - 2026-10-22 (afternoon)
- Afternoon theme and asset change: Synced new project media. Featured Residential block model, galvanised theme.

## [3.1.0] - 2026-10-22 (morning)
- New design system: Bar bending yard design system. Synced new project media. Featured Commercial tower model, millscale theme.

## [3.0.2] - 2026-10-21 (night)
- Night theme and asset change: Synced new project media. Featured Luxury residential tower model, formwork theme.

## [3.0.1] - 2026-10-21 (afternoon)
- Afternoon theme and asset change: Synced new project media. Featured IT park building model, chalkline theme.

## [3.0.0] - 2026-10-21 (morning)
- Revamp (new layout): Storey stack design system. Synced new project media. Featured Luxury residential tower model, survey theme.

## [2.0.2] - 2026-10-20
- Daily rotation: Synced new project media. Featured Sale and rehab building model, blueprint theme.

## [2.0.1] - 2026-10-19
- Cadence: daily PATCH (theme and asset rotation), weekly MINOR on Mondays (design-system overhaul), monthly MAJOR on the 1st (complete rework).
- Design tokens now live in `design/system.json` (generated into `tokens.css`); every weekly and monthly design is archived in `design/archive/` and logged in `design/HISTORY.md`.
- Added WCAG contrast checks, a no-repeat check against archived designs, and headless browser QA (`scripts/qa.py`).
- Monthly designs are also kept as a Claude Design System; v2.0.0 Drawing Sheet is the first.

## [2.0.0] - 2026-10-19
- Redesign: the site is now a Revit drawing sheet. The hero plays a build-up animation inside a title block whose revision cell shows the live version.
- Added 14 Computer Help team projects with 64 model views, 14 construction build-up videos and 17 rebar/BBS drawings, synced from the BIM-Portfolio repo.
- Confidentiality: projects are shown by type, storeys and city only. Media is stored under neutral ids, video metadata is stripped, burned-in titles are masked, and the daily job refuses to publish if a project name appears anywhere.
- Added a filterable drawing register, a project viewer with keyboard navigation, a build-up reel with hover previews, and four rotating themes (sheet, blueprint, night, concrete).
- Content now lives in `data/*.json`; `scripts/portfolio.py` syncs media, rotates the daily state, bumps the version and renders `index.html`.
- Removed the duplicate Jekyll Pages workflow, which raced the static deploy on every push.
