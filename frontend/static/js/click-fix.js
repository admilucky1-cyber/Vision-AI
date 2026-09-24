/**
 * Vision AI v8.4.0 — Click recovery + React-style event wiring
 */
(function () {
  function clearBlockingOverlays() {
    try {
      if (window.VAStore) window.VAStore.setState({ sidebarOpen: false });
      document.body.classList.remove("sidebar-open");
      var ov = document.getElementById("sidebar-overlay");
      if (ov) {
        ov.classList.remove("active", "show", "open");
        ov.style.display = "none";
        ov.style.pointerEvents = "none";
      }
      document.body.style.overflow = "";
    } catch (e) {}
  }

  function bindOnce(el, type, fn) {
    if (!el || el.dataset.vaClickFix) return;
    el.dataset.vaClickFix = "1";
    el.addEventListener(type, fn);
  }

  function doSend(e) {
    if (e) e.preventDefault();
    if (window.VAStore && window.VAStore.getState().sending) return;
    if (window.VAStore) window.VAStore.setState({ sending: true });
    try {
      if (typeof window.sendMessage === "function") {
        var p = window.sendMessage();
        if (p && typeof p.finally === "function") {
          p.finally(function () {
            if (window.VAStore) window.VAStore.setState({ sending: false });
          });
          return;
        }
      }
    } catch (err) {
      console.error(err);
    }
    setTimeout(function () {
      if (window.VAStore) window.VAStore.setState({ sending: false });
    }, 800);
  }

  function wire() {
    clearBlockingOverlays();

    bindOnce(document.getElementById("sendBtn"), "click", doSend);

    var msg = document.getElementById("message");
    bindOnce(msg, "keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) doSend(e);
    });

    document.querySelectorAll(".new-chat-btn, #newChatBtn, [data-action='new-chat']").forEach(function (btn) {
      bindOnce(btn, "click", function (e) {
        e.preventDefault();
        clearBlockingOverlays();
        if (typeof window.startNewChat === "function") window.startNewChat();
      });
    });

    var menuBtn =
      document.getElementById("menuBtn") ||
      document.querySelector("[data-action='toggle-sidebar'], .menu-toggle, .hamburger");
    bindOnce(menuBtn, "click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var open = !(window.VAStore && window.VAStore.getState().sidebarOpen);
      if (window.VAStore) window.VAStore.setState({ sidebarOpen: open });
      else document.body.classList.toggle("sidebar-open", open);
    });

    bindOnce(document.getElementById("sidebar-overlay"), "click", function () {
      clearBlockingOverlays();
      if (typeof window.closeMobileSidebar === "function") window.closeMobileSidebar();
    });

    // Event delegation for sidebar links (component-style)
    var side = document.getElementById("sidebar") || document.querySelector(".sidebar");
    if (side && !side.dataset.vaDelegated) {
      side.dataset.vaDelegated = "1";
      side.addEventListener("click", function (e) {
        var a = e.target.closest("a, button, .sidebar-link");
        if (!a) return;
        // Let navigation happen; close drawer on mobile
        if (window.innerWidth <= 900) {
          setTimeout(clearBlockingOverlays, 50);
        }
      });
    }

    if (typeof sendMessage === "function") window.sendMessage = sendMessage;
  }

  function run() {
    wire();
    setTimeout(wire, 400);
    setTimeout(clearBlockingOverlays, 700);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
  window.addEventListener("pageshow", clearBlockingOverlays);
})();
