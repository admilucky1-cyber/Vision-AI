/* Vision AI v6.6 — shared secondary-page behaviours */
(function () {
  try {
    var t = localStorage.getItem("vision_ai_theme") || "dark";
    var p = localStorage.getItem("vision_theme_preset") || "humanly";
    if (t === "system") {
      t = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    document.documentElement.setAttribute("data-theme", t === "light" ? "light" : "dark");
    document.documentElement.setAttribute("data-theme-preset", p);
  } catch (e) {}

  // Ensure viewport meta exists
  if (!document.querySelector('meta[name="viewport"]')) {
    var m = document.createElement("meta");
    m.name = "viewport";
    m.content = "width=device-width, initial-scale=1, viewport-fit=cover";
    document.head.appendChild(m);
  }

  // Soft: mark external nav active
  try {
    var path = (location.pathname || "").replace(/\/$/, "") || "/";
    document.querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (!href || href === "#") return;
      var clean = href.replace(/\/$/, "");
      if (clean === path || (path.endsWith(clean) && clean.length > 1)) {
        a.classList.add("is-active");
        a.setAttribute("aria-current", "page");
      }
    });
  } catch (e) {}
})();
