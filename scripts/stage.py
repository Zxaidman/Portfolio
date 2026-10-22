#!/usr/bin/env python3
"""
stage.py — builds the frame sequences for the scroll stage (the permanent signature hero).

The stage plays its segments in order as the visitor scrolls. Each segment is a folder of
WebP frames plus an entry in data/stage.json:

  model    frames pre-rendered from an IFC by tools/ifc-stage (transparent PNGs: elements fly
           into place storey by storey, exploded view, orbit). The page tints them to the
           current theme. Carries phase labels for the meter.               (fit: "contain")
  buildup  a Revit build-up video with its flat background cut out (transparent WebP), so the
           tower floats on whatever theme the current design system uses   (fit: "contain")
  person   optional: a short clip of Zaid, full-frame                       (fit: "cover")

Only one of model / buildup is used as the hero build (model wins); person plays after it.

Usage
-----
  # IFC choreography (see tools/ifc-stage/README.md for rendering the PNGs):
  python3 scripts/stage.py model /path/to/frames --phases /path/to/phases.json --complete 0.6

  # Revit build-up (background keyed out, cropped to the tower):
  python3 scripts/stage.py buildup media/video/s12.mp4 --frames 144

  # Optional clip of Zaid, played after the build-up (8-10 s, steady camera works best):
  python3 scripts/stage.py person path/to/zaid.mp4 --frames 120

Each run rewrites that segment's frames and its entry in data/stage.json; other segments are
kept. Requires ffmpeg, Pillow, numpy and scipy (only for this script, not for the daily job).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
STAGE_JSON = ROOT / "data" / "stage.json"
OUT = ROOT / "media" / "stage"

KEY_TOL = 10        # how far from the border colour still counts as background (0-255)
DESKTOP_H = 900     # frame height for wide screens (px)
MOBILE_H = 560      # frame height for phones (px)
WEBP_Q = 72
# IFC model renders carry fine edge lines in their alpha channel, which dominates file size:
# a slightly smaller frame and lossy alpha keep the set near the video's budget, with no
# visible difference at the size the stage draws it.
MODEL_DESKTOP_H, MODEL_MOBILE_H, MODEL_Q, MODEL_ALPHA_Q = 780, 520, 66, 50


def log(msg: str) -> None:
    print(f"[stage] {msg}")


def probe_duration(video: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(video)], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def extract(video: Path, n: int, until: float | None, tmp: Path) -> list[Path]:
    """n frames evenly spaced from 0 to `until` seconds (default: the whole clip)."""
    end = until or probe_duration(video)
    fps = n / end
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-t", f"{end:.3f}",
                    "-vf", f"fps={fps:.6f}", "-frames:v", str(n), str(tmp / "r%04d.png")], check=True)
    frames = sorted(tmp.glob("r*.png"))
    if len(frames) < n * 0.9:
        raise SystemExit(f"only {len(frames)} frames extracted, expected {n}")
    return frames


def key_out(img: Image.Image) -> Image.Image:
    """Make the flat render background transparent. Only background-coloured pixels connected
    to the frame edge are removed, so light faces inside the model stay opaque."""
    import numpy as np                     # only needed for video build-ups
    from scipy import ndimage
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, 0)
    near = np.abs(a - bg).max(2) <= KEY_TOL
    lab, _ = ndimage.label(near)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    alpha = np.where(np.isin(lab, edge[edge > 0]), 0, 255).astype(np.uint8)
    out = img.convert("RGBA")
    out.putalpha(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.6)))
    return out


def union_bbox(images: list[Image.Image], margin: int = 24) -> tuple[int, int, int, int]:
    boxes = [im.getchannel("A").getbbox() for im in images]
    boxes = [b for b in boxes if b]
    x0 = min(b[0] for b in boxes) - margin
    y0 = min(b[1] for b in boxes) - margin
    x1 = max(b[2] for b in boxes) + margin
    y1 = max(b[3] for b in boxes) + margin
    w, h = images[0].size
    return max(0, x0), max(0, y0), min(w, x1), min(h, y1)


def save_set(images: list[Image.Image], folder: Path, height: int,
             quality: int = WEBP_Q, alpha_quality: int = 100) -> tuple[int, int, int]:
    """Write f001.webp... at the given height. Returns (width, height, total bytes)."""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    total = 0
    for i, im in enumerate(images, start=1):
        w = round(im.width * height / im.height)
        fr = im.resize((w, height), Image.LANCZOS)
        p = folder / f"f{i:03d}.webp"
        fr.save(p, "WEBP", quality=quality, method=6 if alpha_quality < 100 else 4, alpha_quality=alpha_quality)
        total += p.stat().st_size
    return w, height, total


STOREY_LABELS = ["Foundation", "Ground floor"]


def storey_label(i: int, n: int) -> str:
    """Generic level names only (never the model's own level names)."""
    if i < len(STOREY_LABELS):
        return STOREY_LABELS[i]
    return "Terrace" if i == n - 1 else f"Level {i - 1}"


def model_phases(phases_json: Path, complete: float) -> list[dict]:
    """One label per storey (first time anything of it lands), then the exploded view."""
    raw = json.loads(phases_json.read_text())
    n = max(p["storey"] for p in raw) + 1
    first: dict[int, float] = {}
    for p in raw:
        first[p["storey"]] = min(first.get(p["storey"], 1.0), p["at"])
    out = [{"at": round(at, 4), "label": storey_label(s, n)} for s, at in sorted(first.items(), key=lambda x: x[1])]
    out[0]["at"] = 0.0
    out += [{"at": round(complete + 0.02, 4), "label": "Exploded view"},
            {"at": 0.82, "label": "Reassembling"}, {"at": 0.95, "label": "Model complete"}]
    return out


def build_model(folder: Path, phases: Path | None, complete: float) -> dict:
    files = sorted(folder.glob("*.png"))
    if len(files) < 24:
        raise SystemExit(f"expected rendered PNG frames in {folder}, found {len(files)}")
    imgs = [Image.open(p).convert("RGBA") for p in files]
    box = union_bbox(imgs)
    imgs = [im.crop(box) for im in imgs]
    log(f"model: {len(imgs)} frames, cropped to {box}")
    dw, dh, dbytes = save_set(imgs, OUT / "model", MODEL_DESKTOP_H, MODEL_Q, MODEL_ALPHA_Q)
    mw, mh, mbytes = save_set(imgs, OUT / "model-m", MODEL_MOBILE_H, MODEL_Q, MODEL_ALPHA_Q)
    # Poster = the finished model (static / no-JS fallback).
    shutil.copy2(OUT / "model" / f"f{len(imgs):03d}.webp", OUT / "model-poster.webp")
    log(f"model: desktop {dw}x{dh} {dbytes/1e6:.1f} MB, mobile {mw}x{mh} {mbytes/1e6:.1f} MB")
    seg = {
        "id": "model", "fit": "contain", "tint": True, "count": len(imgs), "complete": complete,
        "desktop": {"dir": "media/stage/model", "w": dw, "h": dh},
        "mobile": {"dir": "media/stage/model-m", "w": mw, "h": mh},
        "poster": "media/stage/model-poster.webp",
    }
    if phases:
        seg["phases"] = model_phases(phases, complete)
    return seg


def build_segment(kind: str, video: Path, n: int, until: float | None) -> dict:
    with tempfile.TemporaryDirectory() as td:
        raw = extract(video, n, until, Path(td))
        log(f"{kind}: extracted {len(raw)} frames from {video.name}")
        imgs = [Image.open(p).convert("RGB") for p in raw]
        if kind == "buildup":
            imgs = [key_out(im) for im in imgs]
            box = union_bbox(imgs)
            imgs = [im.crop(box) for im in imgs]
            log(f"buildup: background removed, cropped to {box}")
        name = kind
        dw, dh, dbytes = save_set(imgs, OUT / name, DESKTOP_H)
        mw, mh, mbytes = save_set(imgs, OUT / f"{name}-m", MOBILE_H)
        # Poster = last frame (the finished build) for the static / no-JS fallback.
        shutil.copy2(OUT / name / f"f{len(imgs):03d}.webp", OUT / f"{name}-poster.webp")
    log(f"{kind}: desktop {dw}x{dh} {dbytes/1e6:.1f} MB, mobile {mw}x{mh} {mbytes/1e6:.1f} MB")
    return {
        "id": kind,
        "fit": "contain" if kind == "buildup" else "cover",
        "count": len(imgs),
        "desktop": {"dir": f"media/stage/{name}", "w": dw, "h": dh},
        "mobile": {"dir": f"media/stage/{name}-m", "w": mw, "h": mh},
        "poster": f"media/stage/{name}-poster.webp",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["model", "buildup", "person"])
    ap.add_argument("video", type=Path, help="video file, or the folder of PNG frames for 'model'")
    ap.add_argument("--phases", type=Path, help="model: phases.json written by the renderer")
    ap.add_argument("--complete", type=float, default=0.6,
                    help="model: share of the frames at which the building is fully assembled")
    ap.add_argument("--frames", type=int, default=144)
    ap.add_argument("--until", type=float, help="stop at this many seconds (e.g. when the build completes)")
    args = ap.parse_args()
    if not args.video.exists():
        raise SystemExit(f"video not found: {args.video}")
    if args.kind == "model":
        seg = build_model(args.video.resolve(), args.phases, args.complete)
    else:
        seg = build_segment(args.kind, args.video.resolve(), args.frames, args.until)
    data = json.loads(STAGE_JSON.read_text()) if STAGE_JSON.exists() else {"segments": []}
    keep = [s for s in data["segments"] if s["id"] != args.kind]
    if args.kind == "model":  # the IFC model replaces the video build-up as the hero build
        for old in [s for s in keep if s["id"] == "buildup"]:
            for d in (old["desktop"]["dir"], old["mobile"]["dir"]):
                shutil.rmtree(ROOT / d, ignore_errors=True)
            (ROOT / old["poster"]).unlink(missing_ok=True)
            log("buildup: retired (replaced by the IFC model)")
        keep = [s for s in keep if s["id"] != "buildup"]
    order = {"model": 0, "buildup": 0, "person": 1}
    data["segments"] = sorted(keep + [seg], key=lambda s: order[s["id"]])
    STAGE_JSON.write_text(json.dumps(data, indent=2) + "\n")
    log(f"wrote {STAGE_JSON.relative_to(ROOT)} ({len(data['segments'])} segment(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
