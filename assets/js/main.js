/* ==========================================================================
   Zaid Shaikh portfolio — main.js (v6.0.0 "Coordination room")
   Progressive enhancement only: every opener is a real link to its image or
   video, all panels and tiles show, and the page reads top to bottom without JS.
   Modules:
     spy      — Project Browser: highlights the panel you are looking at
     clock    — live IST clock in the browser head
     display  — switch the wall between the design system's themes (this visit only)
     boot     — monitor power-on fallback for browsers without CSS view() timelines
     counters — KPI numbers count up once when they enter
     models   — filter chips + sort switch (View Transitions where supported)
     cameras  — monitors preview their build-up muted on hover
     sheets   — show / hide the extra BBS sheets
     viewer   — gallery / video dialog with keyboard navigation
   ========================================================================== */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData = Boolean(navigator.connection && navigator.connection.saveData);
  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const viewTimeline = typeof CSS !== "undefined" && CSS.supports && CSS.supports("animation-timeline: view()");

  document.documentElement.classList.add("js");

  /** Attach a lazily-declared video source (data-src) once. */
  function loadVideo(video) {
    if (!video || video.src || !video.dataset.src) return;
    video.src = video.dataset.src;
  }

  function safePlay(video) {
    const p = video.play();
    if (p && typeof p.catch === "function") p.catch(() => { /* autoplay blocked: poster stays */ });
  }

  /** Run a DOM change inside a View Transition when the browser has one and motion is allowed. */
  function transition(fn) {
    if (document.startViewTransition && !reduceMotion) document.startViewTransition(fn);
    else fn();
  }

  /* ---------- Project Browser: scroll-spy ---------- */
  function spy() {
    const links = $$(".pb-tree a[data-spy]");
    const targets = links.map((a) => ({ a, el: document.getElementById(a.dataset.spy) })).filter((t) => t.el);
    if (!targets.length) return;
    let current = null;
    let ticking = false;

    function update() {
      ticking = false;
      const mark = window.innerHeight * 0.3;
      let hit = null;
      targets.forEach((t) => { if (t.el.getBoundingClientRect().top <= mark) hit = t; });
      if (hit === current) return;
      current = hit;
      targets.forEach((t) => {
        const on = t === hit;
        t.a.classList.toggle("is-on", on);
        if (on) t.a.setAttribute("aria-current", "location"); else t.a.removeAttribute("aria-current");
      });
      // keep the active tab visible in the phone strip
      if (hit && hit.a.closest(".pb-nav").scrollWidth > hit.a.closest(".pb-nav").clientWidth) {
        const nav = hit.a.closest(".pb-nav");
        nav.scrollTo({ left: hit.a.offsetLeft - 16, behavior: reduceMotion ? "auto" : "smooth" });
      }
    }
    const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", request);
    update();
  }

  /* ---------- Live clock (IST) ---------- */
  function clock() {
    const el = $("[data-clock]");
    if (!el) return;
    let fmt;
    try {
      fmt = new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
    } catch { return; }
    const tick = () => { el.textContent = fmt.format(new Date()); };
    tick();
    window.setInterval(tick, 1000);
  }

  /* ---------- Display switch: the wall's themes (in memory, this visit only) ---------- */
  function display() {
    const box = $(".pb-display");
    if (!box) return;
    const buttons = $$("[data-theme-set]", box);
    box.hidden = false;
    buttons.forEach((btn) => btn.addEventListener("click", () => {
      transition(() => {
        document.documentElement.dataset.theme = btn.dataset.themeSet;
        buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      });
    }));
  }

  /* ---------- Monitor power-on: IntersectionObserver fallback ---------- */
  function boot() {
    const panels = $$(".pnl");
    if (reduceMotion || viewTimeline || !("IntersectionObserver" in window)) return; // CSS handles it, or no motion
    document.documentElement.classList.add("boot-io");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("is-on"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -10% 0px" });
    panels.forEach((p) => io.observe(p));
  }

  /* ---------- Counters: KPI numbers roll up once ---------- */
  function counters() {
    const els = $$("[data-count]");
    if (reduceMotion || !("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        io.unobserve(en.target);
        const el = en.target;
        const text = el.textContent;
        const m = text.match(/\d+/);
        if (!m) return;
        const target = Number(m[0]);
        const t0 = performance.now();
        const dur = 1100;
        const tick = (now) => {
          const k = Math.min(1, (now - t0) / dur);
          const val = Math.round(target * (1 - Math.pow(1 - k, 3)));
          el.textContent = text.replace(m[0], String(val));
          if (k < 1) requestAnimationFrame(tick); else el.textContent = text;
        };
        requestAnimationFrame(tick);
      });
    }, { threshold: 0.6 });
    els.forEach((el) => io.observe(el));
  }

  /* ---------- Model browser: filter + sort ---------- */
  function models() {
    const grid = $(".mb-grid");
    if (!grid) return;
    const chips = $$(".chip[data-filter]");
    const tiles = $$(".mb-tile", grid);
    const sortBox = $(".mb-sort");
    chips.forEach((chip) => chip.addEventListener("click", () => {
      const type = chip.dataset.filter;
      chips.forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      transition(() => tiles.forEach((t) => { t.hidden = type !== "all" && t.dataset.type !== type; }));
    }));
    if (!sortBox) return;
    sortBox.hidden = false;
    const segs = $$("[data-sort]", sortBox);
    segs.forEach((seg) => seg.addEventListener("click", () => {
      const by = seg.dataset.sort;
      segs.forEach((s) => s.setAttribute("aria-pressed", String(s === seg)));
      const sorted = tiles.slice().sort((a, b) => (by === "height"
        ? Number(b.dataset.h) - Number(a.dataset.h) || Number(a.dataset.i) - Number(b.dataset.i)
        : Number(a.dataset.i) - Number(b.dataset.i)));
      transition(() => grid.append(...sorted));
    }));
  }

  /* ---------- Site cameras: muted hover previews ---------- */
  function cameras() {
    if (!canHover || reduceMotion || saveData) return;
    $$(".cam").forEach((cam) => {
      const video = $("video", cam);
      if (!video) return;
      cam.addEventListener("mouseenter", () => { loadVideo(video); cam.classList.add("is-playing"); safePlay(video); });
      cam.addEventListener("mouseleave", () => { cam.classList.remove("is-playing"); video.pause(); });
    });
  }

  /* ---------- Sheet register: show / hide the extra sheets ---------- */
  function sheets() {
    const btn = $("[data-more]");
    const list = $(".sr-list");
    if (!btn || !list) return;
    const total = $$("li", list).length;
    btn.addEventListener("click", () => {
      const collapsed = list.dataset.collapsed === "true";
      list.dataset.collapsed = String(!collapsed);
      btn.setAttribute("aria-expanded", String(collapsed));
      btn.textContent = collapsed ? "Show fewer sheets" : `Show all ${total} sheets`;
    });
  }

  /* ---------- Viewer dialog ---------- */
  function viewer() {
    const dialog = $("#viewer");
    const dataEl = $("#viewer-data");
    if (!dialog || !dataEl || typeof dialog.showModal !== "function") return; // links keep working

    let data;
    try { data = JSON.parse(dataEl.textContent); } catch { return; }

    const stage = $("#viewer-stage");
    const count = $("#viewer-count");
    const prev = $('[data-step="-1"]', dialog);
    const next = $('[data-step="1"]', dialog);
    let current = null; // { item, index, mode: 'image' | 'video' }
    let opener = null;

    function render() {
      const { item, index, mode } = current;
      stage.replaceChildren();
      if (mode === "video" && item.video) {
        const v = document.createElement("video");
        v.controls = true; v.playsInline = true; v.preload = "metadata";
        v.poster = item.video.poster || "";
        v.src = item.video.src;
        v.setAttribute("aria-label", `${item.title} build-up animation`);
        // A plate over the top-left corner, where the source renders carry a burned-in caption.
        const wrap = document.createElement("div");
        wrap.className = "vw-video";
        const plate = document.createElement("span");
        plate.className = "vw-plate";
        plate.setAttribute("aria-hidden", "true");
        plate.textContent = `FEED · ${item.sheet}`;
        wrap.append(v, plate);
        stage.append(wrap);
        if (!reduceMotion) safePlay(v);
        count.textContent = `Feed ${item.video.duration || ""}`.trim();
        prev.disabled = true;
        next.disabled = item.images.length === 0;
        return;
      }
      const im = item.images[index];
      const img = document.createElement("img");
      img.src = im.src; img.width = im.w; img.height = im.h;
      img.alt = im.alt || `${item.title}, view ${index + 1}`;
      img.decoding = "async";
      stage.append(img);
      count.textContent = `View ${String(index + 1).padStart(2, "0")} / ${String(item.images.length).padStart(2, "0")}`;
      prev.disabled = index === 0 && !item.video;
      next.disabled = index === item.images.length - 1;
    }

    function open(slug, index = 0, mode = "image") {
      const item = data[slug];
      if (!item) return false;
      current = { item, index: Math.max(0, Math.min(index, item.images.length - 1)), mode };
      $("#viewer-sheet").textContent = `Sheet ${item.sheet}`;
      $("#viewer-title").textContent = item.title;
      $("#viewer-meta").textContent = item.meta;
      render();
      if (!dialog.open) dialog.showModal();
      return true;
    }

    function step(dir) {
      if (!current) return;
      const { item } = current;
      if (current.mode === "video") {
        if (dir > 0 && item.images.length) { current.mode = "image"; current.index = 0; render(); }
        return;
      }
      const target = current.index + dir;
      if (target < 0) { if (item.video) { current.mode = "video"; render(); } return; }
      if (target >= item.images.length) return;
      current.index = target;
      render();
    }

    document.addEventListener("click", (ev) => {
      const trigger = ev.target.closest("[data-open]");
      if (!trigger || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button > 0) return; // new-tab clicks keep the link
      if (open(trigger.dataset.open, Number(trigger.dataset.index || 0), trigger.hasAttribute("data-video") ? "video" : "image")) {
        ev.preventDefault();
        opener = trigger;
      }
    });
    prev.addEventListener("click", () => step(-1));
    next.addEventListener("click", () => step(1));
    $("[data-close]", dialog).addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (ev) => { if (ev.target === dialog) dialog.close(); }); // backdrop
    dialog.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") { ev.preventDefault(); step(1); }
      if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") { ev.preventDefault(); step(-1); }
    });
    dialog.addEventListener("close", () => {
      stage.replaceChildren(); // stops any playing video
      if (opener && document.contains(opener)) opener.focus();
    });
  }

  function init() {
    spy();
    clock();
    display();
    boot();
    counters();
    models();
    cameras();
    sheets();
    viewer();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
