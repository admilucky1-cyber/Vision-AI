/**
 * Vision AI — early theme bootstrap (runs before paint when possible)
 * Ensures data-theme + data-theme-preset are set on every page so
 * CSS variables and page-specific rules activate immediately.
 */
(function () {
  try {
    var root = document.documentElement;
    var theme = localStorage.getItem('vision_ai_theme') || 'dark';
    var preset = localStorage.getItem('vision_theme_preset') || 'humanly';
    if (theme === 'system') {
      theme = (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
    }
    root.setAttribute('data-theme', theme);
    root.setAttribute('data-theme-preset', preset);
    if (document.body) {
      document.body.setAttribute('data-theme', theme);
      document.body.setAttribute('data-theme-preset', preset);
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        if (document.body) {
          document.body.setAttribute('data-theme', theme);
          document.body.setAttribute('data-theme-preset', preset);
        }
      });
    }
    // Sync across tabs / pages
    window.addEventListener('storage', function (e) {
      if (e.key === 'vision_ai_theme' && e.newValue) {
        root.setAttribute('data-theme', e.newValue);
        if (document.body) document.body.setAttribute('data-theme', e.newValue);
      }
      if (e.key === 'vision_theme_preset' && e.newValue) {
        root.setAttribute('data-theme-preset', e.newValue);
        if (document.body) document.body.setAttribute('data-theme-preset', e.newValue);
      }
    });
  } catch (e) { /* ignore */ }
})();
