#!/usr/bin/env python3
"""Render the stage choreography to transparent PNG frames with headless Chromium.

usage: python3 drive.py GEO_DIR OUT_DIR [--frames 168] [--query "az0=32&azspan=105"]
       GEO_DIR holds geom.json + geom.bin from extract.py.
Writes OUT_DIR/r0001.png ... and OUT_DIR/phases.json (for stage.py --phases).
Needs: playwright (Python) with Chromium, and `npm install` in this folder (three.js).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
PORT = 8765


def chromium() -> str | None:
    """Prefer a preinstalled Chromium if one is configured; else let Playwright pick."""
    exe = os.environ.get("CHROMIUM")
    return exe if exe and Path(exe).exists() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("geo", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--frames", type=int, default=168)
    ap.add_argument("--query", default="", help="renderer options, e.g. 'az0=32&azspan=105&fov=26'")
    args = ap.parse_args()
    if not (HERE / "node_modules" / "three").exists():
        raise SystemExit("run `npm install` in tools/ifc-stage first")
    work = HERE / ".work"
    work.mkdir(exist_ok=True)
    for name in ("geom.json", "geom.bin"):
        shutil.copy2(args.geo / name, work / name)
    args.out.mkdir(parents=True, exist_ok=True)
    us = [i / (args.frames - 1) for i in range(args.frames)]

    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"], cwd=HERE,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chromium(),
                                  args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
            pg = b.new_page()
            pg.on("console", lambda m: print("console:", m.text) if m.type == "error" and "404" not in m.text else None)
            pg.goto(f"http://127.0.0.1:{PORT}/render.html?{args.query}")
            pg.wait_for_function("window.ready === true", timeout=60000)
            info = pg.evaluate("setup()")
            print(f"setup: {info['elements']} elements, {info['storeys']} storeys")
            (args.out / "phases.json").write_text(json.dumps(info["phases"]))
            t0 = time.time()
            for i, u in enumerate(us):
                data = pg.evaluate(f"renderAt({u})")
                (args.out / f"r{i + 1:04d}.png").write_bytes(base64.b64decode(data.split(",", 1)[1]))
                if (i + 1) % 20 == 0 or i + 1 == len(us):
                    print(f"  {i + 1}/{len(us)} frames, {time.time() - t0:.0f}s", flush=True)
            b.close()
    finally:
        srv.terminate()
        shutil.rmtree(work, ignore_errors=True)  # geometry never stays in the repo folder
    return 0


if __name__ == "__main__":
    sys.exit(main())
