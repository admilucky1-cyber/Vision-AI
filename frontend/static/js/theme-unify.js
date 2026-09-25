/** Apply one theme system on every HTML page (unique data-page, shared storage) */
(function () {
  try {
    var t = localStorage.getItem("vision_ai_theme") || "dark";
    var p = localStorage.getItem("vision_theme_preset") || "humanly";
    if (t === "system") {
      t =
        window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    }
    if (t !== "light" && t !== "dark") t = "dark";
    document.documentElement.setAttribute("data-theme", t);
    document.documentElement.setAttribute("data-theme-preset", p);
    document.documentElement.style.colorScheme = t === "light" ? "light" : "dark";
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
  // Infer data-page if missing
  try {
    if (!document.body.getAttribute("data-page")) {
      var path = (location.pathname || "").toLowerCase();
      var page = "home";
      if (path.indexOf("login") >= 0) page = "login";
      else if (path.indexOf("setting") >= 0) page = "settings";
      else if (path.indexOf("studio") >= 0) page = "studio";
      else if (path.indexOf("upgrade") >= 0 || path.indexOf("plan") >= 0) page = "plans";
      else if (path.indexOf("skill") >= 0) page = "skills";
      else if (path.indexOf("data") >= 0) page = "data-lab";
      else if (path.indexOf("boost") >= 0) page = "boost";
      else if (path.indexOf("admin") >= 0) page = "admin";
      else if (path.indexOf("usage") >= 0) page = "usage";
      else if (path.indexOf("index") >= 0 || path === "/" || path.endsWith("/frontend/") || path.endsWith("/frontend"))
        page = "home";
      document.body.setAttribute("data-page", page);
      document.documentElement.setAttribute("data-page", page);
    }
  } catch (e2) {}
})();
