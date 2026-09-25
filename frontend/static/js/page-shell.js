/** Ensure forms use column structure; re-bind menu (anti-regression). */
(function () {
  function enhance() {
    document.querySelectorAll("form:not(.va-column)").forEach(function (f) {
      if (f.id === "authForm" || f.closest(".glass-card") || f.closest(".settings-section")) {
        f.classList.add("va-column", "va-column--stretch");
      }
    });
    // data-page from path if missing
    if (document.body && !document.body.getAttribute("data-page")) {
      var p = (location.pathname || "").toLowerCase();
      var page = "home";
      if (p.indexOf("login") >= 0) page = "login";
      else if (p.indexOf("setting") >= 0) page = "settings";
      else if (p.indexOf("studio") >= 0) page = "studio";
      else if (p.indexOf("upgrade") >= 0) page = "plans";
      else if (p.indexOf("skill") >= 0) page = "skills";
      else if (p.indexOf("data") >= 0) page = "data-lab";
      else if (p.indexOf("boost") >= 0) page = "boost";
      else if (p.indexOf("admin") >= 0) page = "admin";
      document.body.setAttribute("data-page", page);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", enhance);
  else enhance();
})();
