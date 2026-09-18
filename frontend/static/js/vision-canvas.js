/**
 * Vision AI v6.9.0 — Canvas engine for Android + Desktop
 * - devicePixelRatio / HiDPI
 * - ResizeObserver + orientationchange
 * - CSS size vs backing store
 * - Optional pointer (mouse + touch) helpers
 * - rAF redraw scheduling
 */
(function (w) {
  "use strict";

  function dpr() {
    return Math.min(w.devicePixelRatio || 1, 3);
  }

  function isCoarse() {
    try {
      return w.matchMedia && w.matchMedia("(pointer: coarse)").matches;
    } catch (e) {
      return /Android|iPhone|iPad/i.test(navigator.userAgent || "");
    }
  }

  /**
   * Fit canvas to container (or explicit css size).
   * Sets canvas.width/height to CSS pixels * dpr and scales context.
   */
  function fit(canvas, cssW, cssH) {
    if (!canvas) return null;
    var ratio = dpr();
    var wCss = Math.max(1, Math.floor(cssW || canvas.clientWidth || 320));
    var hCss = Math.max(1, Math.floor(cssH || canvas.clientHeight || 240));
    canvas.style.width = wCss + "px";
    canvas.style.height = hCss + "px";
    var bw = Math.floor(wCss * ratio);
    var bh = Math.floor(hCss * ratio);
    if (canvas.width !== bw || canvas.height !== bh) {
      canvas.width = bw;
      canvas.height = bh;
    }
    var ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx: ctx, width: wCss, height: hCss, dpr: ratio, coarse: isCoarse() };
  }

  /**
   * Create a managed surface: auto-resize + redraw.
   * @param {HTMLCanvasElement} canvas
   * @param {function({ctx,width,height,dpr,coarse})} drawFn
   * @param {object} [opts] { container, minHeight }
   */
  function createSurface(canvas, drawFn, opts) {
    opts = opts || {};
    var container = opts.container || canvas.parentElement;
    var minH = opts.minHeight || 220;
    var scheduled = false;
    var last = null;
    var ro = null;

    function measure() {
      var cw = container ? container.clientWidth : canvas.clientWidth;
      var ch = container ? Math.max(minH, container.clientHeight || minH) : minH;
      if (opts.height) ch = opts.height;
      if (opts.width) cw = opts.width;
      // fallback when container is auto-height
      if (!cw || cw < 40) cw = Math.min(w.innerWidth - 32, 720);
      if (!ch || ch < 40) ch = Math.min(Math.floor(cw * 0.62), 420);
      return { cw: cw, ch: ch };
    }

    function redraw() {
      scheduled = false;
      var m = measure();
      last = fit(canvas, m.cw, m.ch);
      if (last && typeof drawFn === "function") {
        try {
          drawFn(last);
        } catch (e) {
          console.warn("[VisionCanvas] draw error", e);
        }
      }
      return last;
    }

    function schedule() {
      if (scheduled) return;
      scheduled = true;
      w.requestAnimationFrame(redraw);
    }

    if (w.ResizeObserver && container) {
      ro = new ResizeObserver(function () {
        schedule();
      });
      ro.observe(container);
    }
    w.addEventListener("resize", schedule, { passive: true });
    w.addEventListener("orientationchange", function () {
      setTimeout(schedule, 120);
    }, { passive: true });
    // visualViewport helps Android keyboard / browser chrome
    if (w.visualViewport) {
      w.visualViewport.addEventListener("resize", schedule, { passive: true });
    }

    // first paint
    schedule();

    return {
      redraw: redraw,
      schedule: schedule,
      destroy: function () {
        if (ro) ro.disconnect();
        w.removeEventListener("resize", schedule);
      },
      get metrics() {
        return last;
      },
    };
  }

  /**
   * Bind pointer handlers with unified coordinates in CSS pixels.
   */
  function bindPointers(canvas, handlers) {
    handlers = handlers || {};
    function pos(ev) {
      var rect = canvas.getBoundingClientRect();
      var src = ev.touches && ev.touches[0] ? ev.touches[0] : ev.changedTouches && ev.changedTouches[0] ? ev.changedTouches[0] : ev;
      return {
        x: ((src.clientX - rect.left) / rect.width) * (canvas.clientWidth || rect.width),
        y: ((src.clientY - rect.top) / rect.height) * (canvas.clientHeight || rect.height),
      };
    }
    function down(e) {
      if (handlers.onDown) handlers.onDown(pos(e), e);
    }
    function move(e) {
      if (handlers.onMove) handlers.onMove(pos(e), e);
    }
    function up(e) {
      if (handlers.onUp) handlers.onUp(pos(e), e);
    }
    canvas.addEventListener("mousedown", down);
    canvas.addEventListener("mousemove", move);
    canvas.addEventListener("mouseup", up);
    canvas.addEventListener("touchstart", down, { passive: true });
    canvas.addEventListener("touchmove", move, { passive: true });
    canvas.addEventListener("touchend", up, { passive: true });
  }

  w.VisionCanvas = {
    version: "6.9.0",
    dpr: dpr,
    isCoarse: isCoarse,
    fit: fit,
    createSurface: createSurface,
    bindPointers: bindPointers,
  };
})(window);
