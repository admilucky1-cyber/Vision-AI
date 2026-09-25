/**
 * Ensure theme buttons fire and colors apply (v8.8.3)
 */
(function () {
  function apply(mode, preset) {
    try {
      var root = document.documentElement;
      if (mode === "system") {
        mode =
          window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
            ? "light"
            : "dark";
      }
      if (mode !== "light" && mode !== "dark") mode = "dark";
      root.setAttribute("data-theme", mode);
      if (document.body) document.body.setAttribute("data-theme", mode);
      root.style.colorScheme = mode;
      localStorage.setItem("vision_ai_theme", mode);
      if (preset) {
        root.setAttribute("data-theme-preset", preset);
        if (document.body) document.body.setAttribute("data-theme-preset", preset);
        localStorage.setItem("vision_theme_preset", preset);
      }
      if (typeof window.applyTheme === "function") {
        try {
          window.applyTheme(mode);
        } catch (e) {}
      }
    } catch (e) {}
  }

  function boot() {
    var stored = localStorage.getItem("vision_ai_theme") || "dark";
    var preset = localStorage.getItem("vision_theme_preset") || "humanly";
    apply(stored === "system" ? "system" : stored, preset);

    document.addEventListener(
      "click",
      function (ev) {
        var t = ev.target;
        if (!t || !t.closest) return;
        var modeBtn = t.closest("[data-mode]");
        if (modeBtn && modeBtn.getAttribute("data-mode")) {
          var m = modeBtn.getAttribute("data-mode");
          if (m === "dark" || m === "light" || m === "system") {
            apply(m);
            return;
          }
        }
        var swatch = t.closest("[data-preset], .theme-swatch");
        if (swatch) {
          var p = swatch.getAttribute("data-preset");
          if (p) apply(localStorage.getItem("vision_ai_theme") || "dark", p);
        }
        var toggle = t.closest(
          "#themePickerBtn, #headerThemeBtn, #themeToggle, #floatingThemeToggle, .theme-picker-btn"
        );
        if (toggle) {
          var panel = document.getElementById("themePickerPanel");
          var pick = document.getElementById("themePicker");
          if (panel) {
            var open = panel.hidden === false || panel.style.display === "block";
            if (panel.hasAttribute("hidden")) {
              panel.removeAttribute("hidden");
            } else if (!open) {
              panel.style.display = "block";
            } else {
              panel.setAttribute("hidden", "");
              panel.style.display = "";
            }
          }
          if (pick) pick.classList.toggle("open");
        }
      },
      true
    );
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
