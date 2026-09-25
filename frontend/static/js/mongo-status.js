/**
 * Vision AI — optional MongoDB status badge (JS)
 */
(function (w, d) {
  function paint(st) {
    var el = d.getElementById("vaMongoBadge");
    if (!el) return;
    if (!st || !st.configured) {
      el.textContent = "DB · SQL";
      el.title = "Using SQLite/Postgres (Mongo not configured)";
      el.dataset.state = "sql";
      return;
    }
    if (st.available) {
      el.textContent = "DB · Mongo";
      el.title = "MongoDB connected: " + (st.db || "vision_ai");
      el.dataset.state = "mongo";
    } else {
      el.textContent = "DB · SQL*";
      el.title = "Mongo configured but unavailable: " + (st.error || "error");
      el.dataset.state = "fallback";
    }
  }
  function load() {
    fetch("/api/mongo/status", { credentials: "same-origin", cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(paint)
      .catch(function () { paint(null); });
  }
  function inject() {
    if (d.getElementById("vaMongoBadge")) return;
    var host = d.querySelector(".header-right-actions, .topbar-tools, .page-topbar, .sidebar-footer");
    if (!host) return;
    var el = d.createElement("span");
    el.id = "vaMongoBadge";
    el.className = "va-ms-pill";
    el.style.marginLeft = "6px";
    host.appendChild(el);
  }
  function boot() {
    inject();
    load();
  }
  if (d.readyState === "loading") d.addEventListener("DOMContentLoaded", boot);
  else boot();
  w.VisionMongo = { refresh: load };
})(window, document);
