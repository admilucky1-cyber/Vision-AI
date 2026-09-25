/**
 * Vision AI v8.5 — Ops health pill + empty-state helper (top-seller pattern)
 * Polls /health/ready; does not block UI.
 */
(function () {
  function ensurePill() {
    var el = document.getElementById("chOpsPill");
    if (el) return el;
    el = document.createElement("div");
    el.id = "chOpsPill";
    el.setAttribute("aria-live", "polite");
    el.textContent = "…";
    document.body.appendChild(el);
    return el;
  }

  function setStatus(kind, text) {
    var el = ensurePill();
    el.dataset.status = kind;
    el.textContent = text;
  }

  function deviceHint() {
    fetch("/api/device/profile", { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j || !j.tier) return;
        try { window.__vaDeviceTier = j; } catch (e) {}
        var el = document.getElementById("chOpsPill");
        if (el && j.tier) {
          el.title = "Tier " + j.tier + " · score " + j.score + " · " + (j.recommendation || "");
        }
      })
      .catch(function () {});
  }
  function ping() {
    try { deviceHint(); } catch (e) {}

    var ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    var t = setTimeout(function () {
      try {
        ctrl && ctrl.abort();
      } catch (e) {}
    }, 4000);
    fetch("/health/ready", { signal: ctrl && ctrl.signal, cache: "no-store" })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, j: j };
        });
      })
      .then(function (x) {
        var st = (x.j && x.j.status) || (x.ok ? "ready" : "down");
        var ver = (x.j && x.j.version) || "";
        if (st === "ready") setStatus("ok", "Live · " + ver);
        else if (st === "degraded") setStatus("degraded", "Degraded · " + ver);
        else setStatus("down", "Offline");
        if (window.VAStore) {
          window.VAStore.setState({ online: st === "ready" || st === "degraded", version: ver });
        }
      })
      .catch(function () {
        setStatus("down", "Offline");
        if (window.VAStore) window.VAStore.setState({ online: false });
      })
      .finally(function () {
        clearTimeout(t);
      });
  }

  function boot() {
    ensurePill();
    ping();
    setInterval(ping, 30000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  // Empty chat helper if no messages
  window.chEnsureEmptyState = function () {
    var out = document.getElementById("chatOutput");
    if (!out) return;
    if (out.querySelector(".message-row")) {
      var empty = out.querySelector(".ch-empty");
      if (empty) empty.remove();
      return;
    }
    if (out.querySelector(".ch-empty")) return;
    var d = document.createElement("div");
    d.className = "ch-empty";
    d.innerHTML = "<strong>Start a conversation</strong><span>Ask anything — or drop a file.</span>";
    out.appendChild(d);
  };
  setTimeout(function () {
    try {
      window.chEnsureEmptyState && window.chEnsureEmptyState();
    } catch (e) {}
  }, 600);
})();
