#!/usr/bin/env python3
"""
qa.py — headless browser check of the built site, run before any push.

Serves the repo on a local port, loads it at desktop (1440px) and mobile (390px)
widths in every theme of the active design system, and fails on:
  * JavaScript errors or console errors
  * failed requests for local assets, or images that do not render
  * horizontal overflow (anything wider than the viewport)
  * the project viewer not opening
Screenshots go to --out so a human or agent can review the design.

Usage:  python3 scripts/qa.py --out /tmp/qa-shots
Requires: pip install playwright  (uses a preinstalled Chromium when one is found)
Exit code 0 = pass, 1 = fail, 2 = could not run (no browser) — treat 2 as a failure for
minor/major design changes.
"""
from __future__ import annotations

import argparse
import functools
import glob
import http.server
import json
import os
import ssl
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def find_chromium() -> str | None:
    for pattern in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                    str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux/chrome")):
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]
    return None  # let Playwright use its own default


def serve() -> tuple[http.server.ThreadingHTTPServer, str]:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # keep QA output readable
            pass
    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"


def font_route(route) -> None:
    """The browser runs without a proxy (so localhost works); fetch web fonts via Python,
    which honours HTTPS_PROXY. If that fails, abort the request and fonts fall back."""
    try:
        cafile = os.environ.get("SSL_CERT_FILE") or ("/root/.ccr/ca-bundle.crt"
                                                     if Path("/root/.ccr/ca-bundle.crt").exists() else None)
        ctx = ssl.create_default_context(cafile=cafile)
        req = urllib.request.Request(route.request.url,
                                     headers={"User-Agent": route.request.headers.get("user-agent", "")})
        with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
            route.fulfill(status=r.status, body=r.read(),
                          headers={"content-type": r.headers.get("content-type", ""),
                                   "access-control-allow-origin": "*"})
    except Exception:
        route.abort()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / ".qa", help="screenshot folder (not committed)")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[qa] could not run: playwright is not installed (pip install playwright)")
        return 2

    themes = list(json.loads((ROOT / "design" / "system.json").read_text())["themes"])
    httpd, url = serve()
    problems: list[str] = []
    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(executable_path=find_chromium())
            except Exception as exc:
                print(f"[qa] could not run: no Chromium available ({exc.__class__.__name__})")
                return 2
            for label, vp in (("desktop", {"width": 1440, "height": 900}),
                              ("mobile", {"width": 390, "height": 844})):
                ctx = browser.new_context(viewport=vp, reduced_motion="reduce")
                page = ctx.new_page()
                page.route("https://fonts.googleapis.com/**", font_route)
                page.route("https://fonts.gstatic.com/**", font_route)
                page.on("pageerror", lambda e, l=label: problems.append(f"{l}: JS error {e}"))
                page.on("console", lambda m, l=label: m.type == "error" and "font" not in m.text.lower()
                        and problems.append(f"{l}: console error {m.text}"))
                page.on("requestfailed", lambda r, l=label: r.url.startswith(url)
                        and problems.append(f"{l}: failed request {r.url}"))
                page.goto(url, wait_until="networkidle")
                # Scroll the whole page so lazy images load.
                height = page.evaluate("document.body.scrollHeight")
                for y in range(0, height, 600):
                    page.evaluate(f"window.scrollTo(0, {y})")
                    page.wait_for_timeout(40)
                page.wait_for_timeout(600)
                broken = page.evaluate(
                    "Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
                problems += [f"{label}: broken image {b}" for b in broken]
                for theme in themes:
                    page.evaluate(f"document.documentElement.dataset.theme = {json.dumps(theme)}; window.scrollTo(0, 0)")
                    page.wait_for_timeout(150)
                    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                    if overflow > 1:
                        problems.append(f"{label}/{theme}: horizontal overflow {overflow}px")
                    page.screenshot(path=str(args.out / f"{label}-{theme}.png"))
                page.screenshot(path=str(args.out / f"{label}-full.png"), full_page=True)
                if label == "desktop":
                    opener = page.query_selector("[data-open]")
                    if opener:
                        opener.click()
                        page.wait_for_timeout(400)
                        if not page.evaluate("!!document.querySelector('dialog[open]')"):
                            problems.append("desktop: project viewer did not open")
                        page.screenshot(path=str(args.out / "desktop-viewer.png"))
                ctx.close()
            # Live-motion pass: the signature scroll stage must pin, draw frames and open the showcase.
            for label, vp in (("desktop", {"width": 1440, "height": 900}), ("mobile", {"width": 390, "height": 844})):
                ctx = browser.new_context(viewport=vp, reduced_motion="no-preference")
                page = ctx.new_page()
                page.route("https://fonts.googleapis.com/**", font_route)
                page.route("https://fonts.gstatic.com/**", font_route)
                page.on("pageerror", lambda e, l=label: problems.append(f"{l}/motion: JS error {e}"))
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(800)
                live = page.evaluate("!!document.querySelector('.sig-stage.sig-live')")
                if not live:
                    problems.append(f"{label}/motion: scroll stage did not start (.sig-live missing)")
                else:
                    run = page.evaluate("(()=>{const s=document.querySelector('.sig-stage');return s.offsetHeight-innerHeight})()")
                    for i, f in enumerate((0.0, 0.3, 0.5, 0.97)):
                        page.evaluate(f"window.scrollTo(0,{int(f * run)})")
                        page.wait_for_timeout(700)
                        page.screenshot(path=str(args.out / f"{label}-stage-{i}.png"))
                        if f == 0.3:
                            drawn = page.evaluate("""(()=>{const c=document.querySelector('.sig-canvas');
                              const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
                              for(let i=3;i<d.length;i+=4*97){if(d[i]>0)return true}return false})()""")
                            if not drawn:
                                problems.append(f"{label}/motion: stage canvas is empty mid-scroll")
                    usable = page.evaluate("!document.querySelector('.sig-screen').hasAttribute('inert')")
                    if not usable:
                        problems.append(f"{label}/motion: showcase did not open at the end of the stage")
                ctx.close()
            browser.close()
    finally:
        httpd.shutdown()

    for p in problems:
        print(f"[qa] FAIL {p}")
    print(f"[qa] {'FAILED' if problems else 'OK'} — {len(themes)} themes x 2 viewports; screenshots in {args.out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
