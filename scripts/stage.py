#!/usr/bin/env python3
"""
stage.py — builds the frame sequences for the scroll stage (the permanent signature hero).

The stage plays its segments in order as the visitor scrolls. Each segment is a folder of
WebP frames plus an entry in data/stage.json:

  buildup  a Revit build-up video with its flat background cut out (transparent WebP), so the
           tower floats on whatever theme the current design system uses   (fit: "contain")
  person   optional: a short clip of Zaid, full-frame                       (fit: "cover")

Usage
-----
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

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
STAGE_JSON = ROOT / "data" / "stage.json"
OUT = ROOT / "media" / "stage"

KEY_TOL = 10        # how far from the border colour still counts as background (0-255)
DESKTOP_H = 900     # frame height for wide screens (px)
MOBILE_H = 560      # frame height for phones (px)
WEBP_Q = 72


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


def save_set(images: list[Image.Image], folder: Path, height: int) -> tuple[int, int, int]:
    """Write f001.webp... at the given height. Returns (width, height, total bytes)."""
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    total = 0
    for i, im in enumerate(images, start=1):
        w = round(im.width * height / im.height)
        fr = im.resize((w, height), Image.LANCZOS)
        p = folder / f"f{i:03d}.webp"
        fr.save(p, "WEBP", quality=WEBP_Q, method=4)
        total += p.stat().st_size
    return w, height, total


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
        # Poster = first frame (desktop size) for an instant first paint.
        shutil.copy2(OUT / name / "f001.webp", OUT / f"{name}-poster.webp")
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
    ap.add_argument("kind", choices=["buildup", "person"])
    ap.add_argument("video", type=Path)
    ap.add_argument("--frames", type=int, default=144)
    ap.add_argument("--until", type=float, help="stop at this many seconds (e.g. when the build completes)")
    args = ap.parse_args()
    if not args.video.exists():
        raise SystemExit(f"video not found: {args.video}")
    seg = build_segment(args.kind, args.video.resolve(), args.frames, args.until)
    data = json.loads(STAGE_JSON.read_text()) if STAGE_JSON.exists() else {"segments": []}
    order = {"buildup": 0, "person": 1}
    data["segments"] = sorted([s for s in data["segments"] if s["id"] != args.kind] + [seg],
                              key=lambda s: order[s["id"]])
    STAGE_JSON.write_text(json.dumps(data, indent=2) + "\n")
    log(f"wrote {STAGE_JSON.relative_to(ROOT)} ({len(data['segments'])} segment(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
