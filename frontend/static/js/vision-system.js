/**
 * Vision AI v7.2.0 — SINGLE system boot (JS)
 * Applies behaviors that were previously split across files.
 */
(function (w, d) {
  "use strict";
  var VER = "7.2.0";

  function themeBoot() {
    try {
      var t = localStorage.getItem("vision_ai_theme") || "dark";
      var p = localStorage.getItem("vision_theme_preset") || "humanly";
      if (t === "system") {
        t = w.matchMedia && w.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
      }
      if (t !== "light" && t !== "dark") t = "dark";
      d.documentElement.setAttribute("data-theme", t);
      d.documentElement.setAttribute("data-theme-preset", p);
      d.documentElement.style.colorScheme = t;
      if (d.body) {
        d.body.setAttribute("data-theme", t);
        d.body.setAttribute("data-theme-preset", p);
      }
    } catch (e) {}
  }

  function ensureViewport() {
    if (!d.querySelector('meta[name="viewport"]')) {
      var m = d.createElement("meta");
      m.name = "viewport";
      m.content = "width=device-width, initial-scale=1, viewport-fit=cover";
      d.head.appendChild(m);
    }
  }

  function unblockTheme() {
    ["themePickerBtn", "headerThemeBtn", "floatingThemeToggle", "themeToggle"].forEach(function (id) {
      var el = d.getElementById(id);
      if (!el) return;
      el.style.pointerEvents = "auto";
      el.style.zIndex = "10051";
    });
    var panel = d.getElementById("themePickerPanel");
    if (panel) {
      panel.style.pointerEvents = "auto";
      panel.style.zIndex = "10060";
    }
  }

  function healthPing() {
    if (typeof w.updateStatus !== "function") return;
    function ping() {
      fetch("/health", { credentials: "same-origin", cache: "no-store" })
        .then(function (r) { w.updateStatus(!!r.ok); })
        .catch(function () { w.updateStatus(false); });
    }
    ping();
    setInterval(ping, 30000);
  }

  function markActiveNav() {
    try {
      var path = (location.pathname || "").replace(/\/$/, "") || "/";
      d.querySelectorAll("a[href]").forEach(function (a) {
        var href = (a.getAttribute("href") || "").replace(/\/$/, "");
        if (href && href !== "#" && (href === path || path.endsWith(href))) {
          a.classList.add("is-active");
          a.setAttribute("aria-current", "page");
        }
      });
    } catch (e) {}
  }

  function boot() {
    themeBoot();
    ensureViewport();
    unblockTheme();
    markActiveNav();
    healthPing();
    d.documentElement.classList.add("va-system");
    d.documentElement.setAttribute("data-va-version", VER);
  }

  themeBoot(); // before paint if deferred late, still ok
  if (d.readyState === "loading") d.addEventListener("DOMContentLoaded", boot);
  else boot();

  w.VisionSystem = { version: VER, boot: boot, themeBoot: themeBoot };
})(window, document);

/* v7.3.0 — small UI helpers (no React required) */
(function (w, d) {
  if (!w.VisionSystem) return;
  w.VisionSystem.toast = function (msg, type) {
    if (typeof w.showToast === "function") return w.showToast(msg, type || "info");
    var el = d.createElement("div");
    el.setAttribute("role", "status");
    el.textContent = String(msg || "");
    el.style.cssText = "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99999;padding:10px 16px;border-radius:10px;background:#0f172a;color:#e2e8f0;font:600 13px system-ui;box-shadow:0 8px 24px rgba(0,0,0,.35);";
    d.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 2800);
  };
  w.VisionSystem.qs = function (sel, root) { return (root || d).querySelector(sel); };
  w.VisionSystem.qsa = function (sel, root) { return Array.prototype.slice.call((root || d).querySelectorAll(sel)); };
})(window, document);

(function (w, d) {
  if ("serviceWorker" in navigator) {
    w.addEventListener("load", function () {
      navigator.serviceWorker.register("/frontend/sw.js").catch(function () {});
    });
  }
})(window, document);
