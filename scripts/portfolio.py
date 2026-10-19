#!/usr/bin/env python3
"""
portfolio.py — build tooling for Zaid Shaikh's BIM portfolio (static site).

Subcommands
-----------
  sync      Pull projects, images and build-up videos from the source repo
            (aasif-shaikh7/BIM-Portfolio) into this site's media/ and data/.
  refresh   Rotate the daily state (featured project, hero video, theme),
            bump the semantic version, and append a CHANGELOG entry.
  build     Render index.html from data/*.json (see scripts/render.py).
  validate  Check that every JSON file parses and every referenced asset exists.
  daily     sync -> refresh -> build -> validate -> leak check (what the 5:53 AM job runs).
  archive   Snapshot the active design into design/archive/ (weekly and monthly designs).
  cadence   Print today's update kind: patch (daily), minor (Mondays), major (1st of month).

Design notes
------------
* Content lives in data/*.json; index.html + assets/js/main.js render it.
  A daily update therefore only rewrites small JSON files, so the git history
  stays light even though the media folder is large.
* Media is copied only when its content hash changes (no daily re-commit of
  160 MB of video). Images are re-encoded to web sizes with Pillow.
* Versioning follows SemVer (MAJOR.MINOR.PATCH) on a fixed cadence:
    PATCH  daily: theme and featured-asset rotation, plus any new media from the source
    MINOR  weekly (Mondays): complete design-system overhaul (`daily --minor`)
    MAJOR  monthly (the 1st): complete portfolio rework (`daily --major`)
* The rotation is deterministic for a given date, so re-running the job on the
  same day is idempotent: it produces no diff and no version bump.

Requires Python 3.9+ and Pillow (see requirements.txt).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MEDIA = ROOT / "media"
IST = ZoneInfo("Asia/Kolkata")

IMAGE_FULL_MAX = 1800   # px, long edge for gallery images
IMAGE_THUMB_MAX = 720   # px, long edge for register previews / cards
JPEG_QUALITY = 82

def themes() -> list[str]:
    """Themes of the active design system (design/system.json). Daily rotation only picks
    from this list, so the look changes without leaving the current design system."""
    system = read_json(ROOT / "design" / "system.json", {}) or {}
    return list(system.get("themes", {})) or ["sheet"]

# Project type is not in the source data; classify by its category line.
TYPE_RULES = [
    ("Commercial", re.compile(r"commercial|it/ites|it park|business|office", re.I)),
    ("Residential", re.compile(r"residen|home|rehab|tower|skyscraper", re.I)),
]


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def log(msg: str) -> None:
    print(f"[portfolio] {msg}")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> bool:
    """Write JSON only if content changed. Returns True when the file changed."""
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def classify(category: str) -> str:
    for label, rx in TYPE_RULES:
        if rx.search(category):
            return label
    return "Other"


def split_location(category: str) -> tuple[str, str]:
    """'Luxury Residential · Andheri W, Mumbai' -> ('Luxury Residential', 'Andheri W, Mumbai')."""
    parts = [p.strip() for p in category.split("·")]
    if len(parts) >= 2 and not re.search(r"modelling|model", parts[-1], re.I):
        return parts[0], parts[-1]
    return parts[0], ""


# --------------------------------------------------------------------------- #
# Source parsing (stdlib HTMLParser, no third-party dependency)
# --------------------------------------------------------------------------- #
@dataclass
class SourceProject:
    title: str = ""
    category: str = ""
    description: str = ""
    images: list[str] = field(default_factory=list)


@dataclass
class SourceVideo:
    title: str = ""
    src: str = ""
    poster: str = ""
    caption: str = ""


class SourceParser(HTMLParser):
    """Extracts project articles, build-up videos and BBS slides from the source index.html."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.projects: list[SourceProject] = []
        self.videos: list[SourceVideo] = []
        self.bbs: list[tuple[str, str]] = []  # (file, alt)
        self._proj: SourceProject | None = None
        self._vid: SourceVideo | None = None
        self._capture: str | None = None
        self._buf: list[str] = []
        self._in_bbs = False
        self._depth_article = 0

    # -- tag handling -------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "") or ""
        if tag == "article" and "proj-feature" in cls:
            self._proj = SourceProject()
        elif self._proj is not None:
            if tag == "span" and "proj-cat" in cls:
                self._start("category")
            elif tag == "h3":
                self._start("title")
            elif tag == "p":
                self._start("description")
            elif tag == "button" and a.get("data-images"):
                try:
                    self._proj.images = [i.split("?")[0] for i in json.loads(a["data-images"])]
                except json.JSONDecodeError:
                    pass
        if tag == "div" and "bbs-slides" in cls:
            self._in_bbs = True
        if self._in_bbs and tag == "img" and a.get("src"):
            self.bbs.append((Path(a["src"].split("?")[0]).name, a.get("alt", "")))
        if tag == "figure" and "buildup" in cls:
            self._vid = SourceVideo()
        if self._vid is not None:
            if tag == "video":
                self._vid.poster = Path(a.get("poster", "").split("?")[0]).name
            elif tag == "source" and a.get("src"):
                self._vid.src = Path(a["src"].split("?")[0]).name
            elif tag == "b":
                self._start("vtitle")
            elif tag == "span":
                self._start("vcap")

    def handle_endtag(self, tag):
        if self._capture and tag in ("span", "h3", "p", "b"):
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if self._proj is not None:
                if self._capture == "category":
                    self._proj.category = text
                elif self._capture == "title":
                    self._proj.title = text
                elif self._capture == "description":
                    self._proj.description = text
            if self._vid is not None:
                if self._capture == "vtitle":
                    self._vid.title = text
                elif self._capture == "vcap":
                    self._vid.caption = text
            self._capture = None
        if tag == "article" and self._proj is not None:
            if self._proj.images:
                self.projects.append(self._proj)
            self._proj = None
        if tag == "div" and self._in_bbs:
            self._in_bbs = False
        if tag == "figure" and self._vid is not None:
            if self._vid.src:
                self.videos.append(self._vid)
            self._vid = None

    def handle_data(self, data):
        if self._capture:
            self._buf.append(data)

    def _start(self, what: str) -> None:
        self._capture = what
        self._buf = []


def match_video(project_slug: str, videos: dict[str, dict]) -> dict | None:
    """Video captions are often shorter than project titles ('ALPHA' vs 'Alpha Heights').
    Prefer an exact slug match, then the longest video slug that prefixes the project slug."""
    if project_slug in videos:
        return videos[project_slug]
    hits = [v for v in videos if project_slug.startswith(v + "-") or v.startswith(project_slug + "-")]
    return videos[max(hits, key=len)] if hits else None


def figure_buildup_fix(html: str) -> str:
    """Older source revisions used <figure> without a class; tag them so the parser sees them."""
    return re.sub(r"<figure(?![^>]*class=)([^>]*)>(\s*<video)", r'<figure class="buildup"\1>\2', html)


# --------------------------------------------------------------------------- #
# Media handling
# --------------------------------------------------------------------------- #
class MediaSync:
    """Copies/re-encodes media only when the source bytes change (tracked in data/media-manifest.json)."""

    def __init__(self) -> None:
        self.manifest_path = DATA / "media-manifest.json"
        self.manifest: dict[str, str] = read_json(self.manifest_path, {}) or {}
        self.changed: list[str] = []
        self.touched: set[Path] = set()  # every file this run produced; anything else is pruned

    def _fresh(self, key: str, src: Path, outputs: list[Path]) -> bool:
        digest = sha256(src)
        if self.manifest.get(key) == digest and all(o.exists() for o in outputs):
            return False
        self.manifest[key] = digest
        self.changed.append(key)
        return True

    def image(self, src: Path, dest_stem: Path) -> dict:
        from PIL import Image, ImageOps  # imported lazily so `validate` works without Pillow

        full = dest_stem.with_suffix(".jpg")
        thumb = dest_stem.parent / (dest_stem.name + "-thumb.jpg")
        key = f"img:{dest_stem.relative_to(MEDIA)}"
        if self._fresh(key, src, [full, thumb]):
            full.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                for out, size in ((full, IMAGE_FULL_MAX), (thumb, IMAGE_THUMB_MAX)):
                    copy = im.copy()
                    copy.thumbnail((size, size), Image.LANCZOS)
                    copy.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        self.touched.update((full, thumb))
        with Image.open(full) as im:
            w, h = im.size
        return {
            "src": str(full.relative_to(ROOT)).replace("\\", "/"),
            "thumb": str(thumb.relative_to(ROOT)).replace("\\", "/"),
            "w": w,
            "h": h,
        }

    def copy(self, src: Path, dest: Path) -> str:
        key = f"file:{dest.relative_to(MEDIA)}"
        if self._fresh(key, src, [dest]):
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        self.touched.add(dest)
        return str(dest.relative_to(ROOT)).replace("\\", "/")

    def video(self, src: Path, dest: Path, mask: list[int] | None = None) -> str:
        """Copy a video with container metadata stripped; optionally cover a region (burned-in text)."""
        key = f"video:{dest.relative_to(MEDIA)}:{mask or ''}"
        if self._fresh(key, src, [dest]):
            dest.parent.mkdir(parents=True, exist_ok=True)
            if shutil.which("ffmpeg"):
                cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map_metadata", "-1"]
                if mask:
                    x, y, w, h = mask
                    cmd += ["-vf", f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0xE1E1E1:t=fill",
                            "-c:v", "libx264", "-crf", "23", "-preset", "slow", "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart", "-c:a", "copy"]
                else:
                    cmd += ["-c", "copy", "-movflags", "+faststart"]
                subprocess.run(cmd + [str(dest)], check=True)
            elif mask:
                raise SystemExit("ffmpeg is required to mask burned-in text in videos")
            else:
                shutil.copy2(src, dest)
        self.touched.add(dest)
        return str(dest.relative_to(ROOT)).replace("\\", "/")

    def poster_from(self, video: Path, dest: Path) -> str:
        """Last-second frame of a (masked) video as its poster."""
        if not dest.exists() or dest.stat().st_mtime < video.stat().st_mtime:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-1", "-i", str(video),
                            "-frames:v", "1", "-q:v", "3", str(dest)], check=True)
            self.changed.append(f"poster:{dest.name}")
        self.touched.add(dest)
        return str(dest.relative_to(ROOT)).replace("\\", "/")

    def prune(self) -> list[str]:
        """Delete media files no longer produced by the source (e.g. a project removed or renamed)."""
        removed = []
        for f in MEDIA.rglob("*"):
            if f.is_file() and f not in self.touched:
                f.unlink()
                removed.append(str(f.relative_to(MEDIA)))
        for d in sorted((d for d in MEDIA.rglob("*") if d.is_dir()), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
        self.manifest = {k: v for k, v in self.manifest.items() if self._output_exists(k)}
        return removed

    @staticmethod
    def _output_exists(key: str) -> bool:
        kind, rel = key.split(":")[:2]
        path = MEDIA / rel
        return (path.with_suffix(".jpg") if kind == "img" else path).exists()

    def save(self) -> None:
        write_json(self.manifest_path, dict(sorted(self.manifest.items())))


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def project_id(first_image: str) -> str:
    """Neutral, stable id from the source slide number ('slide-09-01.jpg' -> 's09').
    Never derived from the project name, so ids and file paths reveal nothing."""
    m = re.match(r"slide-(\d+)-", Path(first_image).name)
    if not m:
        raise SystemExit(f"Cannot derive a neutral id from image name {first_image!r}")
    return f"s{int(m.group(1)):02d}"


def public_title(label: dict) -> str:
    """'G+20 residential tower model' when storeys are known, else 'Residential tower model'."""
    base = label.get("title") or "structural model"
    if label.get("storeys"):
        return f"G+{label['storeys']} {base}"
    return base[:1].upper() + base[1:]


def city_only(location: str) -> str:
    """'Andheri W, Mumbai' -> 'Mumbai'. Neighbourhoods can identify a project."""
    return location.split(",")[-1].strip() if location else ""


def name_tokens(titles: list[str]) -> set[str]:
    """Distinctive words from confidential project names, for the leak check.
    Generic building words are skipped so 'tower' or 'park' in our own copy is fine."""
    generic = {"tower", "towers", "park", "business", "bank", "home", "homes", "the", "and",
               "residency", "heights", "uae", "mumbai", "bhopal"}
    out = set()
    for t in titles:
        for w in re.findall(r"[a-z]+", t.lower()):
            if len(w) >= 3 and w not in generic:
                out.add(w)
    return out


def cmd_sync(source: Path) -> tuple[bool, set[str]]:
    """Sync from the source repo. Returns (content_changed, confidential_name_tokens)."""
    index = source / "index.html"
    assets = source / "assets"
    if not index.exists():
        raise SystemExit(f"Source index.html not found at {index}")

    parser = SourceParser()
    parser.feed(figure_buildup_fix(index.read_text(encoding="utf-8")))
    if not parser.projects:
        raise SystemExit("Parsed 0 projects from the source; refusing to overwrite data/projects.json.")

    labels = read_json(DATA / "labels.json", {}) or {}
    secrets = name_tokens([p.title for p in parser.projects] + [v.title for v in parser.videos])
    media = MediaSync()

    # Map source video slug -> project id, so videos are stored under neutral names.
    slug_to_id = {slugify(p.title): project_id(p.images[0]) for p in parser.projects if p.images}
    videos: dict[str, dict] = {}
    for v in parser.videos:
        vslug = slugify(v.title)
        hit = match_video(vslug, {k: k for k in slug_to_id}) if vslug not in slug_to_id else vslug
        pid = slug_to_id.get(hit) if hit else None
        if not pid:
            log("WARN a build-up video has no matching project; skipped")
            continue
        label = labels.get(pid, {})
        src_path = assets / "videos" / v.src
        if not src_path.exists():
            continue
        entry = {"src": media.video(src_path, MEDIA / "video" / f"{pid}.mp4", label.get("mask"))}
        poster_dest = MEDIA / "video" / f"{pid}-poster.jpg"
        if label.get("mask"):
            # The source poster carries the same burned-in text: cut a fresh one from the masked video.
            entry["poster"] = media.poster_from(MEDIA / "video" / f"{pid}.mp4", poster_dest)
        elif v.poster and (assets / "videos" / v.poster).exists():
            entry["poster"] = media.copy(assets / "videos" / v.poster, poster_dest)
        m = re.search(r"(\d+:\d{2})", v.caption)
        entry["duration"] = m.group(1) if m else ""
        entry["kind"] = "4D simulation" if "4d" in v.caption.lower() else "Build-up"
        videos[pid] = entry

    projects = []
    for i, p in enumerate(parser.projects, start=1):
        if not p.images:
            continue
        pid = project_id(p.images[0])
        label = labels.get(pid, {})
        if label.get("exclude"):
            continue
        kind, location = split_location(p.category)
        images = []
        for img in p.images:
            src = assets / img
            if src.exists():
                images.append(media.image(src, MEDIA / "projects" / pid / Path(img).stem))
            else:
                log(f"WARN missing image for {pid}")
        if not images:
            continue
        if pid not in labels:
            log(f"WARN {pid} has no entry in data/labels.json; using a generic title. Add one.")
        projects.append({
            "slug": pid,
            "sheet": f"A-{i:03d}",
            "title": public_title(label),
            "kind": kind,
            "type": label.get("type") or classify(f"{p.category} {p.description}"),
            "location": label.get("location", city_only(location)),
            "summary": p.description,
            "images": images,
            "video": videos.get(pid),
        })

    bbs_exclude = set(labels.get("_bbs_exclude", []))
    bbs = []
    for name, alt in parser.bbs:
        src = assets / name
        if src.exists() and Path(name).stem not in bbs_exclude:
            item = media.image(src, MEDIA / "bbs" / Path(name).stem)
            item["alt"] = alt
            bbs.append(item)

    changed = write_json(DATA / "projects.json", {"projects": projects, "bbs": bbs})
    removed = media.prune()
    media.save()
    changed = changed or bool(media.changed) or bool(removed)
    log(f"sync: {len(projects)} projects, {len(videos)} videos, {len(bbs)} BBS sheets; "
        f"{len(media.changed)} media files updated, {len(removed)} removed")
    return changed, secrets


def leak_check(secrets: set[str]) -> int:
    """Fail if any confidential project-name word appears in anything that gets published."""
    if not secrets:
        return 0
    rx = re.compile(r"\b(" + "|".join(sorted(map(re.escape, secrets))) + r")\b", re.I)
    hits = []
    for f in ROOT.rglob("*"):
        rel = f.relative_to(ROOT)
        if rel.parts[0] in (".git",) or "__pycache__" in rel.parts:
            continue
        if rx.search(str(rel)):
            hits.append(f"path {rel}")
        if f.is_file() and f.suffix in (".html", ".json", ".md", ".css", ".js", ".txt", ".yml", ".py"):
            m = rx.search(f.read_text(encoding="utf-8", errors="ignore"))
            if m:
                hits.append(f"{rel}: '{m.group(0)}'")
    for h in hits:
        print(f"[leak-check] CONFIDENTIAL NAME FOUND in {h}")
    print(f"[leak-check] {'FAILED' if hits else 'OK'} — {len(secrets)} name words checked")
    return 1 if hits else 0


def bump(version: str, part: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def daily_state(projects: list[dict], day: dt.date) -> dict:
    """Deterministic rotation for a date: same date -> same state."""
    ordinal = day.toordinal()
    with_video = [p for p in projects if p.get("video")] or projects
    featured = with_video[ordinal % len(with_video)]
    names = themes()
    theme = names[ordinal % len(names)]
    # Reel starts at a different project each day so the strip feels new.
    offset = ordinal % max(len(with_video), 1)
    reel = [p["slug"] for p in with_video[offset:] + with_video[:offset]]
    return {"featured": featured["slug"], "theme": theme, "reel": reel}


def cmd_refresh(day: dt.date, content_changed: bool, force_major: bool, force_minor: bool = False) -> bool:
    data = read_json(DATA / "projects.json")
    if not data or not data.get("projects"):
        raise SystemExit("data/projects.json is empty; run `sync` first.")
    site_path = DATA / "site.json"
    site = read_json(site_path, {}) or {}
    version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "2.0.0"

    state = daily_state(data["projects"], day)
    rotated = any(site.get(k) != v for k, v in state.items())
    if not (rotated or content_changed or force_major or force_minor):
        log(f"refresh: nothing changed for {day.isoformat()}; staying on {version}")
        return False

    # Cadence: MAJOR = monthly full rework, MINOR = weekly design-system overhaul,
    # PATCH = daily theme/asset rotation (new media from the source is a daily asset change).
    part = "major" if force_major else ("minor" if force_minor else "patch")
    # The very first run after a manual redesign keeps the hand-set version.
    new_version = version if site.get("version") != version else bump(version, part)

    featured = next(p for p in data["projects"] if p["slug"] == state["featured"])
    site.update(state)
    site.update({"version": new_version, "date": day.isoformat()})
    history = site.get("revisions", [])
    note = f"Featured {featured['title']}, {state['theme']} theme"
    if content_changed:
        note = "Synced new project media. " + note
    system = read_json(ROOT / "design" / "system.json", {}) or {}
    if part in ("major", "minor"):
        note = f"{system.get('name', 'New design')} design system. " + note
    history.insert(0, {"rev": new_version, "date": day.isoformat(), "note": note})
    site["revisions"] = history[:5]  # the title block shows the last five
    write_json(site_path, site)
    (ROOT / "VERSION").write_text(new_version + "\n")

    changelog = ROOT / "CHANGELOG.md"
    head = "# Changelog\n\nAll notable changes. Versions follow SemVer (MAJOR.MINOR.PATCH).\n"
    body = changelog.read_text(encoding="utf-8").replace(head, "") if changelog.exists() else ""
    if f"## [{new_version}]" not in body:
        kind = {"major": "Monthly rework", "minor": "Weekly design-system overhaul",
                "patch": "Daily rotation"}[part]
        entry = f"\n## [{new_version}] - {day.isoformat()}\n- {kind}: {note}.\n"
        changelog.write_text(head + entry + body, encoding="utf-8")
    how = f"{version} -> {new_version} ({part})" if new_version != version else f"first build of {version}"
    log(f"refresh: {how}; {note}")
    return True


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio between two hex colours."""
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (foreground, background, minimum ratio). Text pairs need 4.5:1; the accent is used for
# small text (sheet numbers, revision), so it is held to 4.5:1 too.
CONTRAST_RULES = [("ink", "paper", 7.0), ("ink", "panel", 4.5), ("muted", "paper", 4.5),
                  ("accent", "paper", 4.5), ("on-accent", "accent", 4.5), ("line", "paper", 1.6)]


def check_design(errors: list[str]) -> None:
    system = read_json(ROOT / "design" / "system.json", None)
    if not system:
        errors.append("design/system.json missing or empty")
        return
    for key in ("name", "introduced", "fonts", "themes"):
        if key not in system:
            errors.append(f"design/system.json: missing '{key}'")
    if len(system.get("themes", {})) < 3:
        errors.append("design/system.json: needs at least 3 themes so the daily rotation has variety")
    for name, th in system.get("themes", {}).items():
        for fg, bg, minimum in CONTRAST_RULES:
            if fg not in th or bg not in th:
                errors.append(f"theme '{name}': missing token {fg if fg not in th else bg}")
                continue
            ratio = contrast(th[fg], th[bg])
            if ratio < minimum:
                errors.append(f"theme '{name}': {fg} on {bg} contrast {ratio:.2f} < {minimum}")
    if not (ROOT / "design" / "HISTORY.md").exists():
        errors.append("design/HISTORY.md missing")


# Files that make up a design. Each shipped weekly/monthly design is snapshotted with them.
DESIGN_FILES = ["design/system.json", "assets/css/tokens.css", "assets/css/main.css",
                "assets/js/main.js", "scripts/render.py"]
ARCHIVE = ROOT / "design" / "archive"


def archive_dir_for(version: str) -> Path | None:
    hits = sorted(ARCHIVE.glob(f"v{version}-*")) if ARCHIVE.exists() else []
    return hits[0] if hits else None


def cmd_archive(version: str, shots: Path | None = None) -> Path:
    """Snapshot the active design into design/archive/v<version>-<name>/ (never overwritten)."""
    system = read_json(ROOT / "design" / "system.json", {}) or {}
    existing = archive_dir_for(version)
    dest = existing or ARCHIVE / f"v{version}-{slugify(system.get('name', 'design'))}"
    if existing:
        # A snapshot is never overwritten; only missing screenshots may be added to it.
        log(f"archive: {existing.relative_to(ROOT)} exists; design files left untouched")
    else:
        for rel in DESIGN_FILES:
            src = ROOT / rel
            if src.exists():
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest / rel)
    if shots and shots.exists() and not (dest / "screenshots").exists():
        (dest / "screenshots").mkdir(parents=True, exist_ok=True)
        for name in ("desktop-full.png", "mobile-full.png"):
            if (shots / name).exists():
                # Downscale so the archive stays small.
                from PIL import Image
                with Image.open(shots / name) as im:
                    im.thumbnail((900, 4000))
                    im.convert("RGB").save(dest / "screenshots" / name.replace(".png", ".jpg"), quality=78)
    if existing:
        return dest
    (dest / "README.md").write_text(
        f"# {system.get('name', '')} (v{version})\n\n{system.get('concept', '')}\n\n"
        "Restore by copying these files back to the repo root, then `python3 scripts/portfolio.py build`.\n",
        encoding="utf-8")
    log(f"archive: wrote {dest.relative_to(ROOT)}")
    return dest


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _near(a: str, b: str, limit: float = 28.0) -> bool:
    return sum((x - y) ** 2 for x, y in zip(_rgb(a), _rgb(b))) ** 0.5 < limit


def check_unique(errors: list[str]) -> None:
    """No repeats: the active design must differ from every archived design other than its own
    snapshot — by name, by font set, and by every theme's paper+accent pairing."""
    system = read_json(ROOT / "design" / "system.json", {}) or {}
    version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else ""
    if version and system.get("introduced") == version and not archive_dir_for(version):
        errors.append(f"design introduced in {version} has no archive snapshot (run `archive`)")
    for snap in sorted(ARCHIVE.glob("v*")) if ARCHIVE.exists() else []:
        old = read_json(snap / "design" / "system.json", None)
        if not old or old == system:
            continue  # its own snapshot, or a restored identical design (allowed only for itself)
        tag = snap.name
        if old.get("name", "").strip().lower() == system.get("name", "").strip().lower():
            errors.append(f"design repeats the name of {tag}")
        if old.get("fonts", {}).get("stylesheet") == system.get("fonts", {}).get("stylesheet"):
            errors.append(f"design reuses the font set of {tag}")
        for tname, th in system.get("themes", {}).items():
            for oname, oth in old.get("themes", {}).items():
                if _near(th["paper"], oth["paper"]) and _near(th["accent"], oth["accent"]):
                    errors.append(f"theme '{tname}' is too close to '{oname}' in {tag} (paper+accent)")


def cadence(day: dt.date) -> str:
    """Which kind of update a date gets: 1st of month = major rework, Monday = minor
    design-system overhaul, any other day = patch rotation. Major wins on a Monday the 1st."""
    if day.day == 1:
        return "major"
    if day.weekday() == 0:
        return "minor"
    return "patch"


def cmd_build() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import render  # local module

    out = render.build()
    log(f"build: wrote {out.relative_to(ROOT)}")


def cmd_validate() -> int:
    errors: list[str] = []
    for jf in DATA.glob("*.json"):
        try:
            json.loads(jf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{jf.name}: invalid JSON ({exc})")
    data = read_json(DATA / "projects.json", {}) or {}
    site = read_json(DATA / "site.json", {}) or {}
    profile = read_json(DATA / "profile.json", {}) or {}

    def need(rel: str | None, ctx: str) -> None:
        if rel and not (ROOT / rel).exists():
            errors.append(f"{ctx}: missing file {rel}")

    slugs = set()
    for p in data.get("projects", []):
        slugs.add(p["slug"])
        if not p.get("images"):
            errors.append(f"{p['slug']}: no images")
        for im in p.get("images", []):
            need(im["src"], p["slug"]); need(im["thumb"], p["slug"])
        if p.get("video"):
            need(p["video"].get("src"), p["slug"]); need(p["video"].get("poster"), p["slug"])
    for b in data.get("bbs", []):
        need(b["src"], "bbs")
    if data.get("hero"):
        need(data["hero"]["src"], "hero"); need(data["hero"]["poster"], "hero")
    if site.get("featured") not in slugs:
        errors.append(f"site.json: featured '{site.get('featured')}' is not a project")
    if site.get("theme") not in themes():
        errors.append(f"site.json: unknown theme '{site.get('theme')}'")
    version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        errors.append(f"VERSION '{version}' is not MAJOR.MINOR.PATCH")
    if site.get("version") != version:
        errors.append(f"site.json version {site.get('version')} != VERSION {version}")
    if not profile.get("name"):
        errors.append("profile.json: missing name")
    check_design(errors)
    check_unique(errors)
    for rel in ("index.html", "assets/css/main.css", "assets/css/tokens.css", "assets/js/main.js", ".nojekyll"):
        need(rel, "site")
    html = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").exists() else ""
    for ref in re.findall(r'(?:src|href)="((?:assets|media|data)/[^"?#]+)', html):
        need(ref, "index.html")

    for e in errors:
        print(f"[validate] ERROR {e}")
    print(f"[validate] {'FAILED' if errors else 'OK'} — {len(slugs)} projects, version {version}")
    return 1 if errors else 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("sync", "daily"):
        sp = sub.add_parser(name)
        sp.add_argument("--source", required=True, type=Path, help="path to a BIM-Portfolio checkout")
    for name in ("refresh", "daily"):
        sp = sub.choices[name] if name in sub.choices else sub.add_parser(name)
        sp.add_argument("--date", help="YYYY-MM-DD (default: today in IST)")
        sp.add_argument("--major", action="store_true", help="bump MAJOR (monthly full rework)")
        sp.add_argument("--minor", action="store_true", help="bump MINOR (weekly design-system overhaul)")
    sub.add_parser("validate")
    sub.add_parser("build")
    ap_ = sub.add_parser("archive", help="snapshot the active design into design/archive/")
    ap_.add_argument("--shots", type=Path, help="QA screenshot folder to include")
    cp = sub.add_parser("cadence", help="print patch/minor/major for a date (default: today, IST)")
    cp.add_argument("--date", help="YYYY-MM-DD")
    args = ap.parse_args(argv)

    if args.cmd == "validate":
        return cmd_validate()
    if args.cmd == "build":
        cmd_build()
        return cmd_validate()
    if args.cmd == "archive":
        cmd_archive((ROOT / "VERSION").read_text().strip(), args.shots)
        return cmd_validate()
    if args.cmd == "cadence":
        d = dt.date.fromisoformat(args.date) if args.date else dt.datetime.now(IST).date()
        print(cadence(d))
        return 0
    day = dt.date.fromisoformat(args.date) if getattr(args, "date", None) else dt.datetime.now(IST).date()
    if args.cmd == "sync":
        _, secrets = cmd_sync(args.source.resolve())
        return max(cmd_validate(), leak_check(secrets))
    if args.cmd == "refresh":
        cmd_refresh(day, content_changed=False, force_major=args.major, force_minor=args.minor)
        cmd_build()
        return cmd_validate()
    # daily
    changed, secrets = cmd_sync(args.source.resolve())
    cmd_refresh(day, content_changed=changed, force_major=args.major, force_minor=args.minor)
    cmd_build()
    if args.major or args.minor:
        # Weekly/monthly designs are snapshotted the moment they are built, so they are never lost.
        cmd_archive((ROOT / "VERSION").read_text().strip())
    # Validation and the confidentiality check both gate the push: non-zero exit = do not push.
    return max(cmd_validate(), leak_check(secrets))


if __name__ == "__main__":
    sys.exit(main())
