/**
 * Vision AI v6.7.0 — Touch gestures
 * - Edge swipe right → open sidebar (drawer mode ≤900px)
 * - Swipe left on sidebar/overlay → close
 * - Swipe down on chat top → mild scroll assist (no full page reload)
 * - Does not break desktop mouse use
 */
(function (w, d) {
  "use strict";

  var EDGE_PX = 28;
  var MIN_SWIPE = 56;
  var MAX_VERTICAL = 80;
  var startX = 0;
  var startY = 0;
  var tracking = false;
  var edgeStart = false;

  function isDrawer() {
    if (typeof w.isDrawerViewport === "function") return !!w.isDrawerViewport();
    return w.matchMedia && w.matchMedia("(max-width: 900px)").matches;
  }

  function sidebarOpen() {
    var sb = d.getElementById("sidebar");
    if (!sb) return false;
    return (
      sb.classList.contains("open-mobile") ||
      d.body.classList.contains("sidebar-open") ||
      sb.classList.contains("open")
    );
  }

  function openSidebar() {
    if (typeof w.toggleSidebar === "function") {
      if (!sidebarOpen()) w.toggleSidebar();
      return;
    }
    var sb = d.getElementById("sidebar");
    var ov = d.getElementById("sidebar-overlay");
    if (sb) sb.classList.add("open-mobile");
    d.body.classList.add("sidebar-open");
    if (ov) {
      ov.classList.add("active");
      ov.style.display = "block";
      ov.style.pointerEvents = "auto";
    }
  }

  function closeSidebar() {
    if (typeof w.toggleSidebar === "function") {
      if (sidebarOpen()) w.toggleSidebar();
      return;
    }
    var sb = d.getElementById("sidebar");
    var ov = d.getElementById("sidebar-overlay");
    if (sb) sb.classList.remove("open-mobile", "open");
    d.body.classList.remove("sidebar-open");
    if (ov) {
      ov.classList.remove("active");
      ov.style.display = "none";
      ov.style.pointerEvents = "none";
    }
  }

  function onStart(e) {
    if (!e.touches || e.touches.length !== 1) return;
    // ignore when typing
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
      tracking = false;
      return;
    }
    var touch = e.touches[0];
    startX = touch.clientX;
    startY = touch.clientY;
    tracking = true;
    edgeStart = isDrawer() && startX <= EDGE_PX && !sidebarOpen();
  }

  function onMove(e) {
    // allow vertical scroll; only preventDefault near confirmed horizontal edge swipe
    if (!tracking || !e.touches || e.touches.length !== 1) return;
    var touch = e.touches[0];
    var dx = touch.clientX - startX;
    var dy = touch.clientY - startY;
    if (edgeStart && Math.abs(dx) > 24 && Math.abs(dx) > Math.abs(dy) * 1.2) {
      if (e.cancelable) e.preventDefault();
    }
  }

  function onEnd(e) {
    if (!tracking) return;
    tracking = false;
    var touch = (e.changedTouches && e.changedTouches[0]) || null;
    if (!touch) return;
    var dx = touch.clientX - startX;
    var dy = touch.clientY - startY;
    if (Math.abs(dy) > MAX_VERTICAL && Math.abs(dy) > Math.abs(dx)) {
      edgeStart = false;
      return; // vertical scroll
    }
    if (!isDrawer()) {
      edgeStart = false;
      return;
    }
    // Open: edge swipe right
    if (edgeStart && dx >= MIN_SWIPE) {
      openSidebar();
      edgeStart = false;
      return;
    }
    // Close: swipe left when open
    if (sidebarOpen() && dx <= -MIN_SWIPE) {
      closeSidebar();
    }
    edgeStart = false;
  }

  function onOverlaySwipe(e) {
    // handled in onEnd globally
  }

  function bind() {
    // passive start/end; move non-passive only when needed is complex — use passive move
    d.addEventListener("touchstart", onStart, { passive: true });
    d.addEventListener("touchmove", onMove, { passive: false });
    d.addEventListener("touchend", onEnd, { passive: true });
    d.addEventListener("touchcancel", function () {
      tracking = false;
      edgeStart = false;
    }, { passive: true });

    // Double-tap on brand to scroll chat top
    var brand = d.querySelector(".header-brand, .tray-logo, .sidebar-logo");
    if (brand) {
      var lastTap = 0;
      brand.addEventListener(
        "touchend",
        function (e) {
          var now = Date.now();
          if (now - lastTap < 320) {
            var chat = d.getElementById("chatOutput");
            if (chat) chat.scrollTop = 0;
          }
          lastTap = now;
        },
        { passive: true }
      );
    }

    d.documentElement.classList.add("va-touch-gestures");
  }

  if (d.readyState === "loading") d.addEventListener("DOMContentLoaded", bind);
  else bind();

  // Public API
  w.VisionTouch = {
    openSidebar: openSidebar,
    closeSidebar: closeSidebar,
    version: "6.7.0",
  };
})(window, document);
