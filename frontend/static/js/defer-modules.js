/**
 * Vision AI — load non-critical modules after first paint (idle)
 * Keeps HTML simple: one tag instead of many blocking scripts.
 */
(function () {
  var DEFER = [
    "/frontend/static/js/prompt_studio.js?v=860",
    "/frontend/static/js/aether-power.js?v=860",
    "/frontend/static/js/aether-advanced.js?v=860",
    "/frontend/static/js/aether-engine.js?v=860",
    "/frontend/static/js/aether-lab.js?v=860",
    "/frontend/static/js/vision-canvas.js?v=860",
    "/frontend/static/js/aether-forge.js?v=860",
    "/frontend/static/js/nova-shell.js?v=860",
    "/frontend/static/js/model-status.js?v=860",
    "/frontend/static/js/mongo-status.js?v=860",
    "/frontend/static/js/boot-selfcheck.js?v=860",
    "/frontend/static/js/ads-monetize.js?v=860",
    "/frontend/static/js/schema-refresh.js?v=860",
  ];

  function load(src) {
    return new Promise(function (resolve) {
      var s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = s.onerror = function () {
        resolve();
      };
      document.head.appendChild(s);
    });
  }

  function run() {
    var i = 0;
    function next() {
      if (i >= DEFER.length) return;
      load(DEFER[i++]).then(function () {
        if (window.requestIdleCallback) {
          requestIdleCallback(next, { timeout: 1200 });
        } else {
          setTimeout(next, 50);
        }
      });
    }
    next();
  }

  if (document.readyState === "complete") run();
  else window.addEventListener("load", function () {
    if (window.requestIdleCallback) requestIdleCallback(run, { timeout: 2000 });
    else setTimeout(run, 1);
  });
})();
