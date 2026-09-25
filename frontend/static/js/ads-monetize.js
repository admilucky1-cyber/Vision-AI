/**
 * Vision AI — ads & monetization (respects free vs paid)
 * Configure: ADSENSE_CLIENT_ID + ADS_ENABLED=1 on server
 */
(function (w, d) {
  var cfg = null;

  function isPaidUser() {
    try {
      var u = w.__vaUser || JSON.parse(localStorage.getItem("vision_user") || "null");
      if (!u) return false;
      var plan = (u.plan || u.tier || "free").toLowerCase();
      return plan !== "free" && plan !== "guest";
    } catch (e) {
      return false;
    }
  }

  function mountSlot(id, slotId) {
    if (!slotId || !cfg || !cfg.client_id) return;
    var host = d.getElementById(id);
    if (!host) {
      host = d.createElement("div");
      host.id = id;
      host.className = "va-ad-slot";
      var foot = d.querySelector(".sidebar-footer") || d.querySelector(".composer") || d.body;
      foot && foot.parentNode && foot.parentNode.insertBefore(host, foot);
    }
    host.innerHTML =
      '<ins class="adsbygoogle" style="display:block" data-ad-client="' +
      cfg.client_id +
      '" data-ad-slot="' +
      slotId +
      '" data-ad-format="auto" data-full-width-responsive="true"></ins>';
    try {
      (w.adsbygoogle = w.adsbygoogle || []).push({});
    } catch (e) {}
  }

  function showUpgradeNudge() {
    if (d.getElementById("vaAdUpgrade")) return;
    var el = d.createElement("div");
    el.id = "vaAdUpgrade";
    el.className = "va-ad-upgrade";
    el.innerHTML =
      '<a href="' +
      (cfg.plans_url || "/frontend/plans.html") +
      '">' +
      (cfg.upgrade_cta || "Go Pro — remove ads") +
      "</a>";
    var side = d.querySelector(".sidebar-footer, #sidebarFooter");
    if (side) side.appendChild(el);
  }

  function loadAdsense() {
    if (d.getElementById("vaAdsenseScript")) return;
    var s = d.createElement("script");
    s.id = "vaAdsenseScript";
    s.async = true;
    s.src = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=" + encodeURIComponent(cfg.client_id);
    s.crossOrigin = "anonymous";
    d.head.appendChild(s);
  }

  function applySponsor() {
    if (!cfg.sponsor_html) return;
    var host = d.getElementById("vaSponsor");
    if (!host) {
      host = d.createElement("div");
      host.id = "vaSponsor";
      host.className = "va-sponsor";
      var side = d.querySelector(".sidebar-body, .sidebar");
      if (side) side.appendChild(host);
    }
    host.innerHTML = cfg.sponsor_html;
  }

  function boot(c) {
    cfg = c || {};
    if (!cfg.enabled) return;
    if (cfg.show_for_free_only && isPaidUser()) return;
    if (cfg.client_id) {
      loadAdsense();
      setTimeout(function () {
        mountSlot("vaAdSidebar", cfg.slots && cfg.slots.sidebar);
        mountSlot("vaAdFooter", cfg.slots && cfg.slots.footer);
      }, 1200);
    }
    applySponsor();
    showUpgradeNudge();
  }

  fetch("/api/ads/config", { credentials: "same-origin", cache: "default" })
    .then(function (r) {
      return r.ok ? r.json() : null;
    })
    .then(boot)
    .catch(function () {});
})(window, document);
