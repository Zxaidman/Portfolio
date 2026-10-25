/* ==========================================================================
   Zaid Shaikh portfolio — main.js (v5.0.0 "Four-D programme")
   Progressive enhancement only: every opener is a real link to its image or
   video, all Gantt rows show, and the page reads top to bottom without JS.
   Modules:
     programme — top week ruler: active activity, data-date line and readout
     fills     — Gantt bars fill as they enter (fallback for browsers without
                 CSS animation-timeline; those do it in CSS)
     counters  — numbers in the resource stats count up once when they enter
     gantt     — filter chips (View Transitions where supported)
     preview   — a render that follows the cursor over the Gantt rows
     lookahead — back / forward buttons and muted hover previews
     submittals— show / hide the extra BBS drawings
     viewer    — gallery / video dialog with keyboard navigation
   ========================================================================== */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData = Boolean(navigator.connection && navigator.connection.saveData);
  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  const viewTimeline = typeof CSS !== "undefined" && CSS.supports && CSS.supports("animation-timeline: view()");
  const DAY = 86400000;

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

  /* ---------- Programme ruler: active activity + data date ---------- */
  function programme() {
    const bar = $(".prog");
    const links = $$(".prog-track a[data-phase]");
    if (!bar || !links.length) return;
    const readout = $("[data-readout]", bar);
    const start = new Date(`${bar.dataset.start}T00:00:00`);
    const fmt = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short" });
    const phases = links
      .map((a) => ({ a, el: document.getElementById(a.dataset.phase), s: Number(a.dataset.s), d: Number(a.dataset.d) }))
      .filter((p) => p.el);
    let current = null;
    let lastDay = -1;

    function update() {
      ticking = false;
      const mark = window.innerHeight * 0.35;
      let idx = 0;
      phases.forEach((p, i) => { if (p.el.getBoundingClientRect().top <= mark) idx = i; });
      const ph = phases[idx];
      // Fraction of this activity scrolled past the mark -> position inside its bar.
      const r = ph.el.getBoundingClientRect();
      const frac = Math.min(1, Math.max(0, (mark - r.top) / Math.max(r.height, 1)));
      const week = ph.s + ph.d * frac;
      bar.style.setProperty("--dd", week.toFixed(3));
      if (current !== ph) {
        current = ph;
        links.forEach((a) => {
          const on = a === ph.a;
          a.classList.toggle("is-on", on);
          if (on) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
        });
      }
      const day = Math.floor(week * 7);
      if (readout && day !== lastDay && !Number.isNaN(start.getTime())) {
        lastDay = day;
        readout.textContent = fmt.format(new Date(start.getTime() + day * DAY));
      }
    }
    let ticking = false;
    const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", request);
    bar.classList.add("is-live");
    update();
  }

  /* ---------- Gantt bar fills: IntersectionObserver fallback ---------- */
  function fills() {
    const targets = $$(".act, .g-row");
    if (reduceMotion || viewTimeline || !("IntersectionObserver" in window)) {
      targets.forEach((t) => t.classList.add("is-in"));
      return;
    }
    document.documentElement.classList.add("fill-io");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -12% 0px" });
    targets.forEach((t) => io.observe(t));
  }

  /* ---------- Counters: the number inside each stat rolls up once ---------- */
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
        const dur = 900;
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

  /* ---------- Gantt: filter chips ---------- */
  function gantt() {
    const chips = $$(".chip[data-filter]");
    const rows = $$(".g-row");
    const apply = (type) => rows.forEach((row) => { row.hidden = type !== "all" && row.dataset.type !== type; });
    chips.forEach((chip) => chip.addEventListener("click", () => {
      const type = chip.dataset.filter;
      chips.forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      if (document.startViewTransition && !reduceMotion) document.startViewTransition(() => apply(type));
      else apply(type);
    }));
  }

  /* ---------- Cursor-following preview over the Gantt ---------- */
  function preview() {
    const box = $(".g-preview");
    const list = $(".g-rows");
    if (!box || !list || !canHover || reduceMotion) return;
    const img = document.createElement("img");
    img.alt = ""; img.decoding = "async";
    let x = 0, y = 0, cx = 0, cy = 0, raf = 0, on = false;
    const loop = () => {
      cx += (x - cx) * 0.2; cy += (y - cy) * 0.2;
      box.style.transform = `translate3d(${cx.toFixed(1)}px, ${cy.toFixed(1)}px, 0)`;
      raf = on || Math.abs(x - cx) + Math.abs(y - cy) > 0.5 ? requestAnimationFrame(loop) : 0;
    };
    document.documentElement.classList.add("has-preview");
    list.addEventListener("pointermove", (ev) => {
      x = ev.clientX + 24; y = ev.clientY - 90;
      if (x + 260 > window.innerWidth) x = ev.clientX - 284;
      if (!raf) raf = requestAnimationFrame(loop);
    });
    list.addEventListener("pointerover", (ev) => {
      const link = ev.target.closest(".g-link");
      if (!link) return;
      if (img.getAttribute("src") !== link.dataset.thumb) img.src = link.dataset.thumb;
      if (!img.isConnected) box.append(img);
      if (!on) { cx = x; cy = y; }
      on = true;
      box.classList.add("is-on");
    });
    list.addEventListener("pointerleave", () => { on = false; box.classList.remove("is-on"); });
  }

  /* ---------- Look-ahead strip ---------- */
  function lookahead() {
    const track = $(".la-track");
    const controls = $(".la-controls");
    if (!track) return;
    if (controls) {
      controls.hidden = false;
      $$("[data-la]", controls).forEach((btn) => btn.addEventListener("click", () => {
        const card = $(".la-card", track);
        const stepPx = card ? card.getBoundingClientRect().width + 16 : track.clientWidth * 0.8;
        track.scrollBy({ left: Number(btn.dataset.la) * stepPx, behavior: reduceMotion ? "auto" : "smooth" });
      }));
    }
    if (!canHover || reduceMotion || saveData) return;
    $$(".la-card", track).forEach((card) => {
      const video = $("video", card);
      if (!video) return;
      card.addEventListener("mouseenter", () => { loadVideo(video); card.classList.add("is-playing"); safePlay(video); });
      card.addEventListener("mouseleave", () => { card.classList.remove("is-playing"); video.pause(); });
    });
  }

  /* ---------- Submittals: show / hide the extra drawings ---------- */
  function submittals() {
    const btn = $("[data-more]");
    const list = $(".sub-list");
    if (!btn || !list) return;
    const total = $$("li", list).length;
    btn.addEventListener("click", () => {
      const collapsed = list.dataset.collapsed === "true";
      list.dataset.collapsed = String(!collapsed);
      btn.setAttribute("aria-expanded", String(collapsed));
      btn.textContent = collapsed ? "Show fewer submittals" : `Show all ${total} submittals`;
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
        stage.append(v);
        if (!reduceMotion) safePlay(v);
        count.textContent = `Build-up ${item.video.duration || ""}`.trim();
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
    programme();
    fills();
    counters();
    gantt();
    preview();
    lookahead();
    submittals();
    viewer();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
