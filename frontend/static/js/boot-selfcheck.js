/** Vision AI v8.2.3 — non-blocking boot self-check */
(function () {
  function run() {
    var issues = [];
    if (!document.getElementById("message") && !document.querySelector(".composer textarea")) {
      issues.push("composer-missing");
    }
    if (!document.querySelector(".sidebar, #sidebar")) {
      issues.push("sidebar-missing");
    }
    // Force SW update once per session after deploy
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.getRegistrations().then(function (regs) {
        regs.forEach(function (r) { try { r.update(); } catch (e) {} });
      });
    }
    if (issues.length) {
      console.warn("[Vision AI boot]", issues.join(", "));
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
})();
