# Changelog

All notable changes. Versions follow SemVer (MAJOR.MINOR.PATCH).

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
