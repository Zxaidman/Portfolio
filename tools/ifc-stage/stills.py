#!/usr/bin/env python3
"""Render gallery stills of an IFC model (several camera angles, assembled / exploded /
structure-only) on a soft studio background, as project images for the site.

usage: python3 stills.py GEO_DIR OUT_DIR [--size 2400x1600]
Writes OUT_DIR/01-*.png ... (full resolution, background composited). Needs the same setup as
drive.py (npm install here, playwright with Chromium; CHROMIUM=/path/to/chrome optional).
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PORT = 8766

# name, options for renderStill (az/el in degrees; hide = element kinds to leave out)
VIEWS = [
    ("corner", {"az": 35, "el": 24}),
    ("opposite-corner", {"az": 215, "el": 22}),
    ("side", {"az": 125, "el": 16}),
    ("street", {"az": 300, "el": 6, "fov": 36, "margin": 1.04}),
    ("aerial", {"az": 50, "el": 58}),
    ("exploded", {"u": 0.78, "az": 55, "el": 16}),
    ("structure", {"az": 35, "el": 26, "hide": ["wall", "opening"]}),
]


def studio(size: tuple[int, int]) -> Image.Image:
    """Soft vertical gradient with a faint floor glow, like a neutral product shot."""
    w, h = size
    top, bottom = (238, 240, 242), (206, 211, 216)
    bg = Image.new("RGB", size)
    d = ImageDraw.Draw(bg)
    for y in range(h):
        t = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    glow = Image.new("L", size, 0)
    ImageDraw.Draw(glow).ellipse([w * 0.12, h * 0.62, w * 0.88, h * 1.05], fill=60)
    bg.paste((246, 247, 248), mask=glow.filter(ImageFilter.GaussianBlur(h * 0.08)))
    return bg


def crop_to_model(frame: Image.Image, shot: Image.Image, pad: float = 0.09, aspect: float = 1.5) -> Image.Image:
    """Crop to the model (opaque pixels, not the faint shadow) plus padding, at a fixed aspect."""
    box = shot.getchannel("A").point(lambda a: 255 if a >= 60 else 0).getbbox()
    if not box:
        return frame
    x0, y0, x1, y1 = box
    cw, ch = (x1 - x0) * (1 + 2 * pad), (y1 - y0) * (1 + 2 * pad)
    cw, ch = max(cw, ch * aspect), max(ch, cw / aspect)
    W, H = frame.size
    cw, ch = min(cw, W), min(ch, H)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + (y1 - y0) * 0.03   # a touch lower: room for the shadow
    left = min(max(0, cx - cw / 2), W - cw)
    top = min(max(0, cy - ch / 2), H - ch)
    return frame.crop((round(left), round(top), round(left + cw), round(top + ch)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("geo", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--size", default="3300x2200", help="render size; each still is then cropped to "
                                                         "the model with padding at 3:2")
    args = ap.parse_args()
    w, h = (int(v) for v in args.size.split("x"))
    work = HERE / ".work"
    work.mkdir(exist_ok=True)
    for name in ("geom.json", "geom.bin"):
        shutil.copy2(args.geo / name, work / name)
    args.out.mkdir(parents=True, exist_ok=True)
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=HERE,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        with sync_playwright() as p:
            exe = os.environ.get("CHROMIUM")
            b = p.chromium.launch(executable_path=exe if exe and Path(exe).exists() else None,
                                  args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{PORT}/render.html?w={w}&h={h}")
            pg.wait_for_function("window.ready === true", timeout=60000)
            pg.evaluate("setup()")
            bg = studio((w, h))
            for k, (name, opts) in enumerate(VIEWS, start=1):
                data = pg.evaluate(f"renderStill({json.dumps(opts)})")
                shot = Image.open(io.BytesIO(base64.b64decode(data.split(",", 1)[1]))).convert("RGBA")
                frame = bg.copy().convert("RGBA")
                frame.alpha_composite(shot)
                frame = crop_to_model(frame, shot)
                path = args.out / f"{k:02d}-{name}.png"
                frame.convert("RGB").save(path)
                print(f"  {path.name}", flush=True)
            b.close()
    finally:
        srv.terminate()
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
