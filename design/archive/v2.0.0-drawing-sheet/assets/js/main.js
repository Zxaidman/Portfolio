/* ==========================================================================
   Zaid Shaikh portfolio — main.js (v2.0.0)
   Progressive enhancement only: the page is fully readable without it.
   Modules: heroVideo, register (filter + preview), reel (hover preview),
            bbs (show more), viewer (gallery / video dialog).
   ========================================================================== */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const saveData = Boolean(navigator.connection && navigator.connection.saveData);
  const canHover = window.matchMedia("(hover: hover)").matches;

  /** Attach a lazily-declared video source (data-src) once. */
  function loadVideo(video) {
    if (!video || video.src || !video.dataset.src) return;
    video.src = video.dataset.src;
  }

  function safePlay(video) {
    const p = video.play();
    if (p && typeof p.catch === "function") p.catch(() => { /* autoplay blocked: poster stays */ });
  }

  /* ---------- Hero: autoplay the build-up only when it is cheap and wanted ---------- */
  function heroVideo() {
    const video = $(".hero-video");
    if (!video || video.tagName !== "VIDEO") return;
    if (reduceMotion || saveData) return; // poster frame only
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { loadVideo(video); safePlay(video); }
        else if (!video.paused) video.pause();
      });
    }, { threshold: 0.25 });
    io.observe(video);
  }

  /* ---------- Register: filter chips + hover/focus preview ---------- */
  function register() {
    const chips = $$(".chip[data-filter]");
    const rows = $$(".reg-row");
    const preview = $(".reg-preview img");

    chips.forEach((chip) => chip.addEventListener("click", () => {
      const type = chip.dataset.filter;
      chips.forEach((c) => c.setAttribute("aria-pressed", String(c === chip)));
      rows.forEach((row) => { row.hidden = type !== "all" && row.dataset.type !== type; });
    }));

    if (!preview) return;
    const show = (btn) => {
      const src = btn.dataset.preview;
      if (!src || preview.getAttribute("src") === src) return;
      preview.style.opacity = "0";
      const img = new Image();
      img.onload = () => { preview.src = src; preview.style.opacity = "1"; };
      img.src = src;
      $$(".reg-row button.is-active").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
    };
    rows.forEach((row) => {
      const btn = $("button", row);
      btn.addEventListener("mouseenter", () => show(btn));
      btn.addEventListener("focus", () => show(btn));
    });
  }

  /* ---------- Reel: muted preview on hover (pointer devices only) ---------- */
  function reel() {
    if (!canHover || reduceMotion || saveData) return;
    $$(".reel-card").forEach((card) => {
      const video = $("video", card);
      card.addEventListener("mouseenter", () => {
        loadVideo(video);
        card.classList.add("is-playing");
        safePlay(video);
      });
      card.addEventListener("mouseleave", () => {
        card.classList.remove("is-playing");
        video.pause();
      });
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
    if (!dialog || !dataEl || typeof dialog.showModal !== "function") return;

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
        count.textContent = `Build-up, ${item.video.duration || ""}`.trim();
        prev.disabled = false; next.disabled = item.images.length === 0;
        prev.textContent = "Previous"; next.textContent = "Views";
        return;
      }
      const im = item.images[index];
      const img = document.createElement("img");
      img.src = im.src; img.width = im.w; img.height = im.h;
      img.alt = im.alt || `${item.title}, view ${index + 1}`;
      img.decoding = "async";
      stage.append(img);
      count.textContent = `View ${index + 1} of ${item.images.length}`;
      prev.textContent = "Previous"; next.textContent = "Next";
      prev.disabled = index === 0 && !item.video;
      next.disabled = index === item.images.length - 1;
    }

    function open(slug, index = 0, mode = "image") {
      const item = data[slug];
      if (!item) return;
      current = { item, index: Math.max(0, Math.min(index, item.images.length - 1)), mode };
      $("#viewer-sheet").textContent = `Sheet ${item.sheet}`;
      $("#viewer-title").textContent = item.title;
      $("#viewer-meta").textContent = item.meta;
      render();
      if (!dialog.open) dialog.showModal();
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
      if (!trigger) return;
      ev.preventDefault();
      opener = trigger;
      open(trigger.dataset.open, Number(trigger.dataset.index || 0),
        trigger.hasAttribute("data-video") ? "video" : "image");
    });
    prev.addEventListener("click", () => step(-1));
    next.addEventListener("click", () => step(1));
    $("[data-close]", dialog).addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (ev) => { if (ev.target === dialog) dialog.close(); }); // backdrop
    dialog.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowRight") { ev.preventDefault(); step(1); }
      if (ev.key === "ArrowLeft") { ev.preventDefault(); step(-1); }
    });
    dialog.addEventListener("close", () => {
      stage.replaceChildren(); // stops any playing video
      if (opener && document.contains(opener)) opener.focus();
    });
  }

  function init() {
    heroVideo();
    register();
    reel();
    bbs();
    viewer();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
