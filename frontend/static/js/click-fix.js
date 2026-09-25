/**
 * Vision AI — click recovery + mobile menu (v8.7.4)
 * Fixes dead hamburger / buttons when overlays or pointer-events break.
 */
(function () {
  function qs(s, r) { return (r || document).querySelector(s); }
  function qsa(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }

  function openSidebar() {
    document.body.classList.add("sidebar-open");
    var sb = qs("#sidebar") || qs(".sidebar");
    if (sb) sb.classList.add("open-mobile");
    var ov = qs("#sidebar-overlay") || qs(".sidebar-overlay");
    if (ov) {
      ov.style.display = "block";
      ov.style.pointerEvents = "auto";
    }
  }
  function closeSidebar() {
    document.body.classList.remove("sidebar-open");
    var sb = qs("#sidebar") || qs(".sidebar");
    if (sb) sb.classList.remove("open-mobile");
    var ov = qs("#sidebar-overlay") || qs(".sidebar-overlay");
    if (ov) ov.style.display = "none";
  }
  function toggleSidebar() {
    if (document.body.classList.contains("sidebar-open")) closeSidebar();
    else openSidebar();
  }

  window.openMobileSidebar = openSidebar;
  window.closeMobileSidebar = closeSidebar;
  window.toggleMobileSidebar = toggleSidebar;
  if (typeof window.toggleSidebar !== "function") window.toggleSidebar = toggleSidebar;

  // Global pointer recovery: no element should eat all clicks forever
  function unblock() {
    try {
      document.documentElement.style.pointerEvents = "auto";
      document.body.style.pointerEvents = "auto";
      qsa(".modal-backdrop, .overlay, #sidebar-overlay").forEach(function (el) {
        if (el && !document.body.classList.contains("sidebar-open")) {
          el.style.pointerEvents = "none";
        }
      });
    } catch (e) {}
  }

  document.addEventListener(
    "click",
    function (ev) {
      var t = ev.target;
      if (!t || !t.closest) return;
      var menuBtn = t.closest(
        '#menuBtn, #sidebarToggle, #hamburger, [data-action="toggle-sidebar"], .menu-btn, button[aria-label*="menu" i], button[aria-label*="sidebar" i]'
      );
      if (menuBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        toggleSidebar();
        return;
      }
      if (t.closest("#sidebar-overlay, .sidebar-overlay")) {
        closeSidebar();
        return;
      }
      // New chat
      var nc = t.closest('#newChatBtn, [data-action="new-chat"], .new-chat-btn');
      if (nc && typeof window.startNewChat === "function") {
        try { window.startNewChat(); } catch (e) {}
      }
    },
    true
  );

  // Touch-friendly: ensure buttons receive clicks
  document.addEventListener("DOMContentLoaded", function () {
    unblock();
    qsa("button, a, [role='button'], .glass-btn").forEach(function (el) {
      el.style.pointerEvents = "auto";
      if (!el.style.touchAction) el.style.touchAction = "manipulation";
    });
    // Wire explicit hamburger if present
    ["menuBtn", "sidebarToggle", "hamburger"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el && !el._vaBound) {
        el._vaBound = true;
        el.addEventListener("click", function (e) {
          e.preventDefault();
          toggleSidebar();
        });
      }
    });
  });

  setInterval(unblock, 8000);
})();
