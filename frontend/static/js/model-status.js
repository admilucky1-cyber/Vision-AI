/**
 * Vision AI v8 — live model/provider status (next-level diagnostics)
 */
(function (w, d) {
  function render(data) {
    var host = d.getElementById("vaModelStatus");
    if (!host) return;
    var providers = (data && data.providers) || data || {};
    var rows = [];
    if (Array.isArray(providers)) {
      providers.forEach(function (p) {
        rows.push(p);
      });
    } else if (typeof providers === "object") {
      Object.keys(providers).forEach(function (k) {
        var v = providers[k];
        rows.push({ name: k, configured: !!(v && (v.configured || v.ok || v.available)), detail: v });
      });
    }
    if (!rows.length) {
      host.innerHTML = '<span class="va-text-muted">Status unavailable</span>';
      return;
    }
    host.innerHTML = rows.map(function (r) {
      var ok = r.configured || r.ok || r.available;
      var name = r.name || r.provider || "?";
      return '<span class="va-ms-pill ' + (ok ? "ok" : "bad") + '" title="' + name + '">' +
        (ok ? "●" : "○") + " " + name + "</span>";
    }).join(" ");
  }

  function load() {
    fetch("/api/llm/health", { credentials: "same-origin", cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (j) render(j);
        else return fetch("/health", { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (h) {
          render({ providers: { app: { configured: !!(h && (h.status === "healthy" || h.ok)) } } });
        });
      })
      .catch(function () {
        var host = d.getElementById("vaModelStatus");
        if (host) host.innerHTML = '<span class="va-ms-pill bad">○ offline</span>';
      });
  }

  function injectChrome() {
    if (d.getElementById("vaModelStatus")) return;
    var bar = d.querySelector(".chat-header, .main-header, .header-bar, .page-topbar");
    if (!bar) return;
    var el = d.createElement("div");
    el.id = "vaModelStatus";
    el.className = "va-model-status";
    el.setAttribute("aria-label", "Model provider status");
    bar.appendChild(el);
  }

  function boot() {
    injectChrome();
    load();
    setInterval(load, 60000);
  }
  if (d.readyState === "loading") d.addEventListener("DOMContentLoaded", boot);
  else boot();
  w.VisionModelStatus = { refresh: load };
})(window, document);
