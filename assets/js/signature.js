/* ==========================================================================
   signature.js — behaviour for the permanent signature sections.
     stage():  pinned scroll stage. One scroll progress p (0 → 1 across the section)
               drives everything: frame sequence on a canvas, hero fade, HUD parallax
               cards, the build meter, the camera push-in and the viewport that expands
               into the showcase. Frames are preloaded progressively (first, last, then
               every other frame, then the rest), so it works before everything loads.
     showcaseTabs(): keyboard-accessible tabs inside the showcase.
     skills(): filter chips + cursor-following glow on the skill cards.
   Motion is opt-in: with prefers-reduced-motion (or no JS) the static layout stays.
   No dependencies.
   ========================================================================== */
(() => {
  "use strict";

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData = Boolean(navigator.connection && navigator.connection.saveData);

  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const seg = (p, a, b) => clamp((p - a) / (b - a));
  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const blur = (px) => (px > 0.2 ? `blur(${px.toFixed(1)}px)` : "none");

  /* ----------------------------------------------------------------------
     Timeline (fractions of the pinned scroll). Tune here.
     ---------------------------------------------------------------------- */
  const T = {
    hero: [0.03, 0.13],          // name + hero copy fade out
    frames: [0.02, 0.60],        // all frame segments play across this range
    hudIn: [0.15, 0.23], hudOut: [0.40, 0.47],                 // desktop: both HUD cards
    mL: { in: [0.15, 0.21], out: [0.29, 0.34] },               // mobile: left card first
    mR: { in: [0.34, 0.40], out: [0.48, 0.53] },               // then right card
    meter: [0.08, 0.14, 0.55, 0.61],
    hint: [0.05, 0.11, 0.48, 0.56],
    push: [0.55, 0.66],          // camera pushes into the model and the model fades away
    screenIn: [0.62, 0.66],      // viewport fades in where the model was
    expand: [0.66, 0.88],        // viewport grows to fill the screen
  };

  function stage() {
    const section = $(".sig-stage");
    const dataEl = $("#sig-stage-data");
    if (!section || !dataEl) return;
    if (reduceMotion) return; // static layout
    let manifest;
    try { manifest = JSON.parse(dataEl.textContent); } catch { return; }
    const segments = manifest.segments || [];
    if (!segments.length) return;

    const canvas = $(".sig-canvas", section);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const hero = $(".sig-hero", section);
    const hudL = $(".sig-hud-l", section);
    const hudR = $(".sig-hud-r", section);
    const meter = $(".sig-meter", section);
    const meterVal = $("[data-sig-meter]", section);
    const meterBar = $("[data-sig-bar]", section);
    const hint = $(".sig-hint", section);
    const screen = $(".sig-screen", section);

    section.classList.add("sig-live", "sig-waiting");

    // Pick the frame set for this screen and build the global frame list.
    const mobileSet = () => window.innerWidth < 860;
    let useMobile = mobileSet();
    const total = segments.reduce((n, s) => n + s.count, 0);
    const frames = [];  // {seg, i, img}
    segments.forEach((s) => { for (let i = 1; i <= s.count; i++) frames.push({ seg: s, i, img: null }); });
    const url = (f) => {
      const set = useMobile ? f.seg.mobile : f.seg.desktop;
      return `${set.dir}/f${String(f.i).padStart(3, "0")}.webp`;
    };

    const st = { p: 0, vw: 0, vh: 0, dpr: 1, drawn: -1, active: true, raf: 0, gen: 0 };

    // ---------------- loading ----------------
    function loadFrame(idx, gen) {
      return new Promise((resolve) => {
        const f = frames[idx];
        if (f.img) return resolve();
        const img = new Image();
        img.decoding = "async";
        img.onload = () => {
          if (gen === st.gen) {
            f.img = img;
            if (idx === wanted()) draw(true);
          }
          resolve();
        };
        img.onerror = () => resolve();
        img.src = url(f);
      });
    }
    async function preload() {
      const gen = ++st.gen;
      frames.forEach((f) => { f.img = null; });
      await Promise.all([loadFrame(0, gen), loadFrame(total - 1, gen)]);
      section.classList.remove("sig-waiting");
      draw(true);
      const step = saveData ? 3 : 1;
      const order = [];
      for (let i = 1; i < total - 1; i += 2 * step) order.push(i);
      if (!saveData) for (let i = 2; i < total - 1; i += 2) order.push(i);
      // Load the frames nearest the current position first.
      const here = wanted();
      order.sort((a, b) => Math.abs(a - here) - Math.abs(b - here));
      for (let k = 0; k < order.length && gen === st.gen; k += 6) {
        await Promise.all(order.slice(k, k + 6).map((i) => loadFrame(i, gen)));
      }
    }

    // ---------------- geometry ----------------
    function wanted() {
      return Math.min(total - 1, Math.round(seg(st.p, T.frames[0], T.frames[1]) * (total - 1)));
    }
    function nearestLoaded(idx) {
      for (let d = 0; d < total; d++) {
        if (frames[idx - d] && frames[idx - d].img) return idx - d;
        if (frames[idx + d] && frames[idx + d].img) return idx + d;
      }
      return -1;
    }

    const pin = $(".sig-pin", section);
    function size() {
      // Measure the pinned box, not the window: designs may put a rail or margins beside it.
      st.vw = pin.clientWidth || window.innerWidth;
      st.vh = pin.clientHeight || window.innerHeight;
      st.dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(st.vw * st.dpr);
      canvas.height = Math.round(st.vh * st.dpr);
      st.drawn = -1;
      const m = mobileSet();
      if (m !== useMobile) { useMobile = m; preload(); }
    }

    function draw(force = false) {
      const idx = nearestLoaded(wanted());
      if (idx < 0) return;
      const push = ease(seg(st.p, T.push[0], T.push[1]));
      const key = `${idx}|${push.toFixed(3)}|${st.vw}x${st.vh}`;
      if (!force && key === st.drawnKey) return;
      st.drawnKey = key;
      const f = frames[idx];
      const img = f.img;
      const { vw, vh, dpr } = st;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, vw, vh);
      let w, h, x, y;
      if (f.seg.fit === "cover") {
        const s = Math.max(vw / img.width, vh / img.height);
        w = img.width * s; h = img.height * s; x = (vw - w) / 2; y = (vh - h) / 2;
      } else {
        const mobile = vw < 860;
        h = vh * (mobile ? 0.6 : 0.82);
        w = img.width * (h / img.height);
        if (w > vw * 0.9) { w = vw * 0.9; h = img.height * (w / img.width); }
        x = (vw - w) / 2;
        y = (mobile ? vh * 0.46 : vh * 0.53) - h / 2;
      }
      // Parallax: the model rises slightly while it builds, then the camera pushes in.
      const lift = seg(st.p, 0, T.frames[1]) * vh * 0.03;
      const k = 1 + push * 0.55;
      const cx = vw / 2, cy = vh * 0.5;
      ctx.globalAlpha = Math.max(0, 1 - push * 1.05);
      ctx.drawImage(img, cx + (x - cx) * k, cy + (y - lift - cy) * k, w * k, h * k);
      ctx.globalAlpha = 1;
    }

    // ---------------- overlays ----------------
    function place() {
      const p = st.p;
      const mobile = st.vw < 860;

      // Hero
      const hp = seg(p, T.hero[0], T.hero[1]);
      hero.style.opacity = String(1 - hp);
      hero.style.transform = `translateY(${-hp * 40}px)`;
      hero.style.filter = blur(hp * 12);
      hero.style.visibility = hp >= 1 ? "hidden" : "visible";

      // HUD cards
      const card = (el, inR, outR, axis, dir) => {
        const a = seg(p, inR[0], inR[1]);
        const b = seg(p, outR[0], outR[1]);
        const op = a * (1 - b);
        el.style.opacity = String(op);
        el.style.filter = blur(Math.max((1 - a) * 14, b * 14));
        el.style.transform = axis === "x"
          ? `translateX(${dir * ((1 - a) * 28 + b * 16)}px) translateY(${-dir * a * 8}px)`
          : `translateY(${(1 - a) * 26 - b * 16}px)`;
        el.style.visibility = op <= 0.01 ? "hidden" : "visible";
      };
      if (mobile) {
        card(hudL, T.mL.in, T.mL.out, "y", 1);
        card(hudR, T.mR.in, T.mR.out, "y", 1);
      } else {
        card(hudL, T.hudIn, T.hudOut, "x", -1);
        card(hudR, T.hudIn, T.hudOut, "x", 1);
      }

      // Build meter (shows the share of the build-up segment that has played)
      const built = seg(p, T.frames[0], T.frames[0] + (T.frames[1] - T.frames[0]) * (segments[0].count / total));
      meter.style.opacity = String(seg(p, T.meter[0], T.meter[1]) * (1 - seg(p, T.meter[2], T.meter[3])));
      meterVal.textContent = `${Math.round(built * 100)}%`;
      meterBar.style.transform = `scaleX(${built})`;
      hint.style.opacity = String(seg(p, T.hint[0], T.hint[1]) * (1 - seg(p, T.hint[2], T.hint[3])));

      // Viewport -> showcase
      const o = seg(p, T.screenIn[0], T.screenIn[1]);
      const ex = ease(seg(p, T.expand[0], T.expand[1]));
      const w0 = mobile ? st.vw * 0.88 : Math.min(st.vw * 0.6, 900);
      const h0 = mobile ? st.vh * 0.5 : Math.min(st.vh * 0.58, w0 * 0.62);
      const insetX = ((st.vw - w0) / 2) * (1 - ex);
      const insetY = ((st.vh - h0) / 2) * (1 - ex);
      screen.style.opacity = String(o);
      screen.style.setProperty("--sig-x", `${insetX.toFixed(1)}px`);
      screen.style.setProperty("--sig-t", `${insetY.toFixed(1)}px`);
      screen.style.setProperty("--sig-b", `${insetY.toFixed(1)}px`);
      screen.style.setProperty("--sig-r", `${(18 * (1 - ex)).toFixed(1)}px`);
      screen.style.setProperty("--sig-k", (0.94 + 0.06 * ex).toFixed(3));
      const usable = ex > 0.95;
      if (usable) screen.removeAttribute("inert"); else screen.setAttribute("inert", "");
      screen.style.visibility = o <= 0.01 ? "hidden" : "visible";
    }

    function progress() {
      const r = section.getBoundingClientRect();
      const run = section.offsetHeight - window.innerHeight;
      return run > 0 ? clamp(-r.top / run) : 0;
    }

    function frame() {
      st.raf = 0;
      st.p = progress();
      place();
      draw();
    }
    const request = () => { if (st.active && !st.raf) st.raf = requestAnimationFrame(frame); };

    // Only work while the stage is near the viewport.
    new IntersectionObserver(([en]) => { st.active = en.isIntersecting; if (st.active) request(); },
      { rootMargin: "50% 0px" }).observe(section);
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", () => { size(); request(); });
    window.addEventListener("orientationchange", () => { size(); request(); });

    // Links into the stage (e.g. "#top") land on the hero; the showcase link lands expanded.
    size();
    frame();
    preload();
  }

  function showcaseTabs() {
    const tabs = $$(".sig-tab");
    if (!tabs.length) return;
    const select = (tab, focus) => {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        const panel = document.getElementById(t.getAttribute("aria-controls"));
        if (panel) panel.hidden = !on;
      });
      if (focus) tab.focus();
    };
    tabs.forEach((t, i) => {
      t.addEventListener("click", () => select(t, false));
      t.addEventListener("keydown", (ev) => {
        const dir = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[ev.key];
        if (dir) { ev.preventDefault(); select(tabs[(i + dir + tabs.length) % tabs.length], true); }
        if (ev.key === "Home") { ev.preventDefault(); select(tabs[0], true); }
        if (ev.key === "End") { ev.preventDefault(); select(tabs[tabs.length - 1], true); }
      });
    });
  }

  function skills() {
    const chips = $$(".sig-chip[data-sig-filter]");
    const cards = $$(".sig-skill");
    chips.forEach((chip) => chip.addEventListener("click", () => {
      const cat = chip.dataset.sigFilter;
      chips.forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      let n = 0;
      cards.forEach((card) => {
        const show = cat === "all" || card.dataset.cat === cat;
        card.hidden = !show;
        card.classList.remove("sig-pop");
        if (show) {
          card.style.setProperty("--n", n++);
          void card.offsetWidth; // restart the entrance animation
          card.classList.add("sig-pop");
        }
      });
    }));
    // Cursor-following glow (pointer devices only).
    if (!window.matchMedia("(hover: hover)").matches) return;
    cards.forEach((card) => {
      let pending = false, ev = null;
      card.addEventListener("pointermove", (e) => {
        ev = e;
        if (pending) return;
        pending = true;
        requestAnimationFrame(() => {
          pending = false;
          const r = card.getBoundingClientRect();
          card.style.setProperty("--mx", `${ev.clientX - r.left}px`);
          card.style.setProperty("--my", `${ev.clientY - r.top}px`);
        });
      });
    });
  }

  function init() { stage(); showcaseTabs(); skills(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
