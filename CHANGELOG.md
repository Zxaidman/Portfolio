# Changelog

All notable changes. Versions follow SemVer (MAJOR.MINOR.PATCH).

## [2.0.0] - 2026-10-19
- Redesign: the site is now a Revit drawing sheet. The hero plays a build-up animation inside a title block whose revision cell shows the live version.
- Added 14 Computer Help team projects with 64 model views, 14 construction build-up videos and 17 rebar/BBS drawings, synced from the BIM-Portfolio repo.
- Confidentiality: projects are shown by type, storeys and city only. Media is stored under neutral ids, video metadata is stripped, burned-in titles are masked, and the daily job refuses to publish if a project name appears anywhere.
- Added a filterable drawing register, a project viewer with keyboard navigation, a build-up reel with hover previews, and four rotating themes (sheet, blueprint, night, concrete).
- Content now lives in `data/*.json`; `scripts/portfolio.py` syncs media, rotates the daily state, bumps the version and renders `index.html`.
- Removed the duplicate Jekyll Pages workflow, which raced the static deploy on every push.
