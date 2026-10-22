/* ==========================================================================
   Zaid Shaikh portfolio — main.js (v3.0.0 "Storey stack")
   Progressive enhancement only: every opener is a real link to its image or
   video, filters show all floors, and the page reads top to bottom without JS.
   Modules:
     levels   — level rail: active level, readout, lift car (scroll-driven CSS
                does the car where supported; this is the fallback)
     reveal   — adds .is-in to section boxes as they enter (CSS fallback for
                browsers without animation-timeline)
     roof     — autoplay the featured build-up only when cheap and wanted
     floors   — filter chips
     buildups — muted hover preview on pointer devices
     bbs      — show / hide the extra drawings
     viewer   — gallery / video dialog with keyboard navigation
   ========================================================================== */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData = Boolean(navigator.connection && navigator.connection.saveData);
  const canHover = window.matchMedia("(hover: hover)").matches;
  const scrollTimeline = typeof CSS !== "undefined" && CSS.supports && CSS.supports("animation-timeline: scroll()");

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

  /* ---------- Level rail: which storey are we on? ---------- */
  function levels() {
    const links = $$(".rail-levels a[data-level]");
    const readout = $("[data-readout]");
    const car = $(".rail-car");
    if (!links.length) return;
    const byId = new Map(links.map((a) => [a.dataset.level, a]));
    const storeys = links.map((a) => document.getElementById(a.dataset.level)).filter(Boolean);

    function setActive(id) {
      links.forEach((a) => {
        const on = a.dataset.level === id;
        a.classList.toggle("is-here", on);
        if (on) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current");
      });
      const link = byId.get(id);
      if (readout && link) readout.textContent = $(".rl-tag", link).textContent;
    }

    // The storey whose top has most recently passed 40% of the viewport is "here".
    const io = new IntersectionObserver(() => {
      const mark = window.innerHeight * 0.4;
      let current = storeys[0];
      storeys.forEach((s) => { if (s.getBoundingClientRect().top <= mark) current = s; });
      if (current) setActive(current.id);
    }, { rootMargin: "-40% 0px -59% 0px", threshold: 0 });
    storeys.forEach((s) => io.observe(s));
    setActive(storeys[0] && storeys[0].id);

    // Lift car fallback for browsers without scroll-driven animations.
    if (car && !scrollTimeline && !reduceMotion) {
      let ticking = false;
      const move = () => {
        ticking = false;
        const max = document.documentElement.scrollHeight - window.innerHeight;
        car.style.setProperty("--lift", String(max > 0 ? window.scrollY / max : 0));
      };
      window.addEventListener("scroll", () => { if (!ticking) { ticking = true; requestAnimationFrame(move); } }, { passive: true });
      move();
    }
  }

  /* ---------- Section-box reveal fallback ---------- */
  function reveal() {
    const boxes = $$(".sbox");
    if (reduceMotion || scrollTimeline || !("IntersectionObserver" in window)) {
      boxes.forEach((b) => b.classList.add("is-in"));
      return;
    }
    document.documentElement.classList.add("reveal-io");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -10% 0px" });
    boxes.forEach((b) => io.observe(b));
  }

  /* ---------- Roof: autoplay the build-up only when it is cheap and wanted ---------- */
  function roof() {
    const video = $(".roof-video");
    if (!video || video.tagName !== "VIDEO" || reduceMotion || saveData) return; // poster only
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { loadVideo(video); safePlay(video); }
        else if (!video.paused) video.pause();
      });
    }, { threshold: 0.25 });
    io.observe(video);
  }

  /* ---------- Floors: filter chips ---------- */
  function floors() {
    const chips = $$(".chip[data-filter]");
    const rows = $$(".floor");
    chips.forEach((chip) => chip.addEventListener("click", () => {
      const type = chip.dataset.filter;
      chips.forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      rows.forEach((row) => { row.hidden = type !== "all" && row.dataset.type !== type; });
    }));
  }

  /* ---------- Build-ups: muted preview on hover (pointer devices only) ---------- */
  function buildups() {
    if (!canHover || reduceMotion || saveData) return;
    $$(".bu-card").forEach((card) => {
      const video = $("video", card);
      if (!video) return;
      card.addEventListener("mouseenter", () => { loadVideo(video); card.classList.add("is-playing"); safePlay(video); });
      card.addEventListener("mouseleave", () => { card.classList.remove("is-playing"); video.pause(); });
    });
  }

  /* ---------- BBS: show / hide the extra drawings ---------- */
  function bbs() {
    const btn = $("[data-more]");
    const grid = $(".bbs-grid");
    if (!btn || !grid) return;
    const total = $$("li", grid).length;
    btn.addEventListener("click", () => {
      const collapsed = grid.dataset.collapsed === "true";
      grid.dataset.collapsed = String(!collapsed);
      btn.setAttribute("aria-expanded", String(collapsed));
      btn.textContent = collapsed ? "Show fewer drawings" : `Show all ${total} drawings`;
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
    levels();
    reveal();
    roof();
    floors();
    buildups();
    bbs();
    viewer();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
