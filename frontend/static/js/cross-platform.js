/**
 * Vision AI cross-platform helpers — iOS/Android/Desktop
 * Load early (after theme-bootstrap, before index.js).
 */
(function (w, d) {
  "use strict";

  // --- Class mirrors for CSS that used :has() ---
  function syncSidebarClasses() {
    var side = d.getElementById("sidebar");
    var tray = d.getElementById("collapsedToolbar");
    var closed =
      (side && (side.classList.contains("rail-mode") || side.classList.contains("collapsed-true"))) ||
      (d.documentElement.getAttribute("data-sidebar") === "closed");
    d.documentElement.classList.toggle("sidebar-closed", !!closed);
    if (tray) {
      d.documentElement.classList.toggle("tray-active", tray.classList.contains("active"));
    }
  }

  // --- visualViewport keyboard inset (iOS/Android) ---
  function bindViewport() {
    var vv = w.visualViewport;
    if (!vv) return;
    var apply = function () {
      var offset = Math.max(0, w.innerHeight - vv.height - vv.offsetTop);
      d.documentElement.style.setProperty("--kb-inset", offset + "px");
      d.documentElement.style.setProperty("--vv-height", vv.height + "px");
    };
    vv.addEventListener("resize", apply);
    vv.addEventListener("scroll", apply);
    apply();
  }

  // --- Clipboard with execCommand fallback ---
  w.vaCopyText = function (text) {
    text = String(text == null ? "" : text);
    if (w.navigator.clipboard && w.navigator.clipboard.writeText) {
      return w.navigator.clipboard.writeText(text).catch(function () {
        return legacyCopy(text);
      });
    }
    return Promise.resolve(legacyCopy(text));
  };
  function legacyCopy(text) {
    try {
      var ta = d.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      d.body.appendChild(ta);
      ta.select();
      var ok = d.execCommand("copy");
      d.body.removeChild(ta);
      return ok;
    } catch (e) {
      return false;
    }
  }

  // --- Speech recognition with webkit prefix ---
  w.vaGetSpeechRecognition = function () {
    return w.SpeechRecognition || w.webkitSpeechRecognition || null;
  };

  // --- Safe matchMedia ---
  w.vaMatch = function (q) {
    try {
      return w.matchMedia(q).matches;
    } catch (e) {
      return false;
    }
  };

  // --- iOS standalone / PWA class ---
  try {
    if (w.navigator.standalone || w.matchMedia("(display-mode: standalone)").matches) {
      d.documentElement.classList.add("va-standalone");
    }
  } catch (e) {}

  // Platform hints (for CSS/debug)
  try {
    var ua = w.navigator.userAgent || "";
    if (/iPhone|iPad|iPod/i.test(ua)) d.documentElement.classList.add("va-ios");
    if (/Android/i.test(ua)) d.documentElement.classList.add("va-android");
    if (/Windows/i.test(ua)) d.documentElement.classList.add("va-win");
    if (/Mac OS X/i.test(ua) && !/iPhone|iPad|iPod/i.test(ua)) d.documentElement.classList.add("va-mac");
    if (/Linux/i.test(ua) && !/Android/i.test(ua)) d.documentElement.classList.add("va-linux");
  } catch (e) {}

  function boot() {
    syncSidebarClasses();
    bindViewport();
    // Observe sidebar class changes
    var side = d.getElementById("sidebar");
    if (side && w.MutationObserver) {
      new MutationObserver(syncSidebarClasses).observe(side, {
        attributes: true,
        attributeFilter: ["class"],
      });
    }
    // data-sidebar on html
    if (w.MutationObserver) {
      new MutationObserver(syncSidebarClasses).observe(d.documentElement, {
        attributes: true,
        attributeFilter: ["data-sidebar", "class"],
      });
    }
  }

  if (d.readyState === "loading") d.addEventListener("DOMContentLoaded", boot);
  else boot();
})(window, document);
