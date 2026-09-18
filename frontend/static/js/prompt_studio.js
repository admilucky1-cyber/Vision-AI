/**
 * Vision AI — Prompt Studio side drawer (optional companion UI)
 * Primary UI is helpModal via toggleHelpModal / closePromptStudio in index.js.
 * This file must NOT overwrite window.closePromptStudio.
 */
(function () {
  "use strict";

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  function ensureDrawer() {
    var d = $("#promptStudioDrawer");
    if (d) return d;
    d = document.createElement("div");
    d.id = "promptStudioDrawer";
    d.className = "ps-drawer";
    d.setAttribute("aria-hidden", "true");
    d.innerHTML =
      '<div class="ps-backdrop" data-ps-close="1"></div>' +
      '<aside class="ps-panel glass-panel" role="dialog" aria-label="Prompt Studio drawer">' +
      '  <header class="ps-header">' +
      '    <div><h2>Prompt Studio</h2><p class="ps-sub">Premium prompts · one tap to chat</p></div>' +
      '    <button type="button" class="ps-close" data-ps-close="1" aria-label="Close">×</button>' +
      "  </header>" +
      '  <div class="ps-search-wrap"><input type="search" id="psSearch" class="ps-search" placeholder="Search prompts…" autocomplete="off" /></div>' +
      '  <div class="ps-chips" id="psChips"></div>' +
      '  <div class="ps-featured" id="psFeatured"></div>' +
      '  <div class="ps-grid" id="psGrid"></div>' +
      "</aside>";
    document.body.appendChild(d);
    d.addEventListener("click", function (e) {
      if (e.target && e.target.getAttribute("data-ps-close")) closeDrawerOnly();
    });
    var search = $("#psSearch", d);
    if (search) search.addEventListener("input", function () { render(search.value || ""); });
    return d;
  }

  function library() {
    return window.PROMPT_LIBRARY || {};
  }

  function closeDrawerOnly() {
    var d = $("#promptStudioDrawer");
    if (!d) return;
    d.classList.remove("open");
    d.setAttribute("aria-hidden", "true");
    document.body.classList.remove("ps-drawer-open");
    document.body.style.overflow = "";
  }

  function openDrawer() {
    // Prefer full modal if available
    if (typeof window.toggleHelpModal === "function" && !document.getElementById("helpModal")) {
      window.toggleHelpModal();
      return;
    }
    if (typeof window.toggleHelpModal === "function") {
      var hm = document.getElementById("helpModal");
      if (hm && hm.style.display !== "flex") {
        window.toggleHelpModal();
        return;
      }
    }
    var d = ensureDrawer();
    d.classList.add("open");
    d.setAttribute("aria-hidden", "false");
    document.body.classList.add("ps-drawer-open");
    render("");
    setTimeout(function () {
      var s = $("#psSearch", d);
      if (s) s.focus();
    }, 200);
  }

  function usePrompt(text) {
    var ta = document.getElementById("message") || document.getElementById("chatInput");
    if (ta) {
      ta.value = text;
      ta.focus();
      ta.dispatchEvent(new Event("input", { bubbles: true }));
    }
    closeDrawerOnly();
    if (typeof window.closePromptStudio === "function") {
      try { window.closePromptStudio(); } catch (e) {}
    }
    if (typeof showToast === "function") showToast("Prompt loaded — edit then Send", "success", 2200);
  }

  function render(filter) {
    var d = ensureDrawer();
    var chips = $("#psChips", d);
    var featured = $("#psFeatured", d);
    var grid = $("#psGrid", d);
    if (!chips || !featured || !grid) return;
    var lib = library();
    var q = (filter || "").toLowerCase().trim();

    chips.innerHTML = '<button type="button" class="ps-chip active" data-cat="*">All</button>';
    Object.keys(lib).forEach(function (c) {
      if (c === "Featured") return;
      var meta = lib[c] || {};
      chips.innerHTML +=
        '<button type="button" class="ps-chip" data-cat="' +
        c.replace(/"/g, "") +
        '">' +
        (meta.icon || "") +
        " " +
        c +
        "</button>";
    });
    $all(".ps-chip", chips).forEach(function (btn) {
      btn.onclick = function () {
        $all(".ps-chip", chips).forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        renderList(btn.getAttribute("data-cat"), q);
      };
    });

    featured.innerHTML = "";
    var feat = (lib.Featured && lib.Featured.prompts) || [];
    feat.forEach(function (p) {
      var card = document.createElement("button");
      card.type = "button";
      card.className = "ps-card ps-card-featured";
      card.innerHTML =
        '<div class="ps-card-top"><span class="ps-badge">Featured</span><strong>' +
        (p.title || "Prompt") +
        "</strong></div><p>" +
        (p.t || "").slice(0, 140) +
        (p.t && p.t.length > 140 ? "…" : "") +
        "</p>";
      card.onclick = function () { usePrompt(p.t); };
      featured.appendChild(card);
    });

    renderList("*", q);

    function renderList(cat, query) {
      grid.innerHTML = "";
      Object.keys(lib).forEach(function (c) {
        if (c === "Featured") return;
        if (cat && cat !== "*" && c !== cat) return;
        (lib[c].prompts || []).forEach(function (p) {
          var text = typeof p === "string" ? p : (p.t || "");
          var title = typeof p === "string" ? "Prompt" : (p.title || "Prompt");
          var blob = (title + " " + text + " " + c).toLowerCase();
          if (query && blob.indexOf(query) === -1) return;
          var card = document.createElement("button");
          card.type = "button";
          card.className = "ps-card";
          card.innerHTML =
            '<div class="ps-card-top"><span>' +
            (lib[c].icon || "✦") +
            "</span><strong>" +
            title +
            '</strong></div><p class="ps-cat">' +
            c +
            "</p><p>" +
            text.slice(0, 110) +
            (text.length > 110 ? "…" : "") +
            "</p>";
          card.onclick = function () { usePrompt(text); };
          grid.appendChild(card);
        });
      });
      if (!grid.children.length) {
        grid.innerHTML = '<p class="ps-empty">No prompts match. Try another search or open the full Prompt Studio from the top bar.</p>';
      }
    }
  }

  window.openPromptStudioDrawer = openDrawer;
  // Never overwrite index.js closePromptStudio — only enhance it
  var _prevClose = window.closePromptStudio;
  window.closePromptStudio = function () {
    closeDrawerOnly();
    if (typeof _prevClose === "function") {
      try { _prevClose(); } catch (e) {}
    }
  };
})();
