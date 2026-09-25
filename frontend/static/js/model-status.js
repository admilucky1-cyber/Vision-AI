/**
 * Vision AI v8.1 — compact provider status (configured only)
 */
(function (w, d) {
  var SHORT = {
    gemini: "gem", groq: "groq", deepseek: "ds", openrouter: "or",
    ollama: "oll", lmstudio: "lms", openai_compat: "oa", openai: "oa"
  };

  function render(data) {
    var host = d.getElementById("vaModelStatus");
    if (!host) return;
    var providers = (data && data.providers) || data || {};
    var rows = [];
    if (Array.isArray(providers)) {
      providers.forEach(function (p) { rows.push(p); });
    } else if (typeof providers === "object") {
      Object.keys(providers).forEach(function (k) {
        var v = providers[k] || {};
        var ok = !!(v.configured || v.ok || v.available === true);
        if (!ok) return; // hide empty locals — reduces crowd
        rows.push({ name: k, configured: true });
      });
    }
    if (!rows.length) {
      host.innerHTML = '<span class="va-ms-pill bad" title="No cloud keys detected">○ keys</span>';
      return;
    }
    host.innerHTML = rows.map(function (r) {
      var raw = (r.name || "").toLowerCase();
      var label = SHORT[raw] || (r.name || "?").slice(0, 6);
      return '<span class="va-ms-pill ok" title="' + (r.name || "") + '">● ' + label + "</span>";
    }).join("");
  }

  function load() {
    fetch("/api/llm/health", { credentials: "same-origin", cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (j) return render(j);
        return fetch("/health", { credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function () {
            var host = d.getElementById("vaModelStatus");
            if (host) host.innerHTML = '<span class="va-ms-pill ok">● app</span>';
          });
      })
      .catch(function () {
        var host = d.getElementById("vaModelStatus");
        if (host) host.innerHTML = '<span class="va-ms-pill bad">○ off</span>';
      });
  }

  function injectChrome() {
    if (d.getElementById("vaModelStatus")) return;
    var bar = d.querySelector(".header-right-actions, .topbar-tools, .main-header, .page-topbar");
    if (!bar) return;
    var el = d.createElement("div");
    el.id = "vaModelStatus";
    el.className = "va-model-status";
    el.setAttribute("aria-label", "Configured providers");
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
