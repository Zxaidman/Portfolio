/* ==========================================================================
   Zaid Shaikh portfolio — main.js (v7.0.0 "Monograph")
   Progressive enhancement only: every opener is a real link to its image or
   video, every section reads top to bottom, and the page works without JS.
   Modules:
     spy      — Contents / running head: track the section being read
     paper    — switch the paper (theme) edition (this visit only)
     counters — key figures count up once when they enter
     rubric   — filter Selected Works by programme type
     films    — build-up plates preview muted on hover
     appendix — show / hide the extra reinforcement drawings
     reveal   — "ink set" fallback for browsers without CSS view() timelines
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

  /* ---------- Contents / running head: scroll-spy ---------- */
  function spy() {
    const links = $$("[data-spy]");
    const now = $("[data-runhead]");
    const targets = links.map((a) => ({ a, el: document.getElementById(a.dataset.spy) })).filter((t) => t.el);
    if (!targets.length) return;
    let current = null;
    let ticking = false;

    function label(a) {
      const title = a.querySelector(".toc-title");
      return (title ? title.textContent : a.textContent).trim();
    }
    function update() {
      ticking = false;
      const mark = window.innerHeight * 0.32;
      let hit = null;
      targets.forEach((t) => { if (t.el.getBoundingClientRect().top <= mark) hit = t; });
      if (hit === current) return;
      current = hit;
      targets.forEach((t) => {
        const on = t === hit;
        t.a.classList.toggle("is-on", on);
        if (on) t.a.setAttribute("aria-current", "location"); else t.a.removeAttribute("aria-current");
      });
      if (now) now.textContent = hit ? label(hit.a) : "Contents";
    }
    const request = () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } };
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", request);
    update();
  }

  /* ---------- Paper edition switch (in memory, this visit only) ---------- */
  function paper() {
    const box = $(".paper");
    if (!box) return;
    const buttons = $$("[data-theme-set]", box);
    box.hidden = false;
    buttons.forEach((btn) => btn.addEventListener("click", () => {
      document.documentElement.dataset.theme = btn.dataset.themeSet;
      buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    }));
  }

  /* ---------- Key figures: count up once ---------- */
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
        const dur = 1000;
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

  /* ---------- Selected works: rubric filter ---------- */
  function rubric() {
    const list = $(".feature-index");
    if (!list) return;
    const chips = $$(".rubric-chip[data-filter]");
    const items = $$(".feature", list);
    chips.forEach((chip) => chip.addEventListener("click", () => {
      const type = chip.dataset.filter;
      chips.forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      items.forEach((it) => { it.hidden = type !== "all" && it.dataset.type !== type; });
    }));
  }

  /* ---------- Build-up films: muted hover previews ---------- */
  function films() {
    if (!canHover || reduceMotion || saveData) return;
    $$(".film").forEach((film) => {
      const video = $("video", film);
      if (!video) return;
      film.addEventListener("mouseenter", () => { loadVideo(video); film.classList.add("is-playing"); safePlay(video); });
      film.addEventListener("mouseleave", () => { film.classList.remove("is-playing"); video.pause(); });
    });
  }

  /* ---------- Technical appendix: show / hide extra drawings ---------- */
  function appendix() {
    const btn = $("[data-more]");
    const list = $(".app-list");
    if (!btn || !list) return;
    const total = $$("li", list).length;
    btn.addEventListener("click", () => {
      const collapsed = list.dataset.collapsed === "true";
      list.dataset.collapsed = String(!collapsed);
      btn.setAttribute("aria-expanded", String(collapsed));
      btn.textContent = collapsed ? "Show fewer drawings" : `Show all ${total} drawings`;
    });
  }

  /* ---------- "Ink set" reveal: fallback where CSS view() is unsupported ---------- */
  function reveal() {
    const marks = $$("[data-ink]");
    if (reduceMotion || viewTimeline || !("IntersectionObserver" in window)) {
      marks.forEach((m) => m.classList.add("is-in")); // CSS view() handles it, or no motion
      return;
    }
    document.documentElement.classList.add("ink-io");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -12% 0px" });
    marks.forEach((m) => io.observe(m));
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
        plate.textContent = `FILM · ${item.sheet}`;
        wrap.append(v, plate);
        stage.append(wrap);
        if (!reduceMotion) safePlay(v);
        count.textContent = `Film ${item.video.duration || ""}`.trim();
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
      count.textContent = `Plate ${String(index + 1).padStart(2, "0")} / ${String(item.images.length).padStart(2, "0")}`;
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
    paper();
    counters();
    rubric();
    films();
    appendix();
    reveal();
    viewer();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
