/**
 * Vision AI — canonical auth (single source of truth for tokens + logout).
 * Load before index.js / settings.js.
 *
 * Canonical keys:
 *   vision_ai_access_token
 *   vision_ai_refresh_token
 * Legacy keys are migrated on read, then cleared on write/logout.
 */
(function (global) {
  "use strict";

  var ACCESS = "vision_ai_access_token";
  var REFRESH = "vision_ai_refresh_token";
  var USER = "vision_ai_user";

  var LEGACY_ACCESS = [
    "vision_ai_token",
    "vision_ai_access",
    "access_token",
  ];
  var LEGACY_REFRESH = [
    "vision_ai_refresh",
    "refresh_token",
  ];

  function lsGet(k) {
    try { return localStorage.getItem(k) || ""; } catch (e) { return ""; }
  }
  function lsSet(k, v) {
    try { localStorage.setItem(k, v); } catch (e) {}
  }
  function lsDel(k) {
    try { localStorage.removeItem(k); } catch (e) {}
    try { sessionStorage.removeItem(k); } catch (e) {}
  }

  function migrateTokens() {
    var a = lsGet(ACCESS);
    if (!a) {
      for (var i = 0; i < LEGACY_ACCESS.length; i++) {
        a = lsGet(LEGACY_ACCESS[i]);
        if (a) break;
      }
      if (a) lsSet(ACCESS, a);
    }
    var r = lsGet(REFRESH);
    if (!r) {
      for (var j = 0; j < LEGACY_REFRESH.length; j++) {
        r = lsGet(LEGACY_REFRESH[j]);
        if (r) break;
      }
      if (r) lsSet(REFRESH, r);
    }
    return { access: a || lsGet(ACCESS), refresh: r || lsGet(REFRESH) };
  }

  function getAccessToken() {
    return migrateTokens().access || "";
  }

  function getRefreshToken() {
    return migrateTokens().refresh || "";
  }

  function setTokens(access, refresh) {
    if (access) lsSet(ACCESS, access);
    if (refresh) lsSet(REFRESH, refresh);
    // stop dual-writes to legacy names
    LEGACY_ACCESS.concat(LEGACY_REFRESH).forEach(lsDel);
  }

  function clearTokens() {
    [ACCESS, REFRESH, USER, "vision_ai_is_guest"].forEach(lsDel);
    LEGACY_ACCESS.concat(LEGACY_REFRESH).forEach(lsDel);
    try {
      sessionStorage.setItem("vision_force_login", "1");
      sessionStorage.setItem("vision_skip_guest", "1");
      sessionStorage.removeItem("vision_auth_redirecting");
    } catch (e) {}
  }

  async function logout(opts) {
    opts = opts || {};
    var doConfirm = opts.confirm !== false;
    var redirect = opts.redirect || "/login.html";
    if (global.__vaLoggingOut) return;
    if (doConfirm && typeof global.confirm === "function") {
      if (!global.confirm("Log out?")) return;
    }
    global.__vaLoggingOut = true;
    var btn = document.querySelector(
      ".logout-item, #profileDropdown .logout-item, #logoutBtn, [data-logout], [data-action='logout']"
    );
    if (btn) {
      btn.disabled = true;
      if (btn.textContent) btn.textContent = "Logging out…";
    }
    try {
      var token = getAccessToken();
      if (token) {
        try {
          await Promise.race([
            fetch("/auth/logout", {
              method: "POST",
              headers: {
                Authorization: "Bearer " + token,
                "Content-Type": "application/json",
              },
              credentials: "same-origin",
            }),
            new Promise(function (resolve) { setTimeout(resolve, 4000); }),
          ]);
        } catch (e) {}
      }
    } finally {
      clearTokens();
      global.__vaLoggingOut = false;
      global.location.replace(redirect);
    }
  }

  global.VisionAuth = {
    ACCESS_KEY: ACCESS,
    REFRESH_KEY: REFRESH,
    getAccessToken: getAccessToken,
    getRefreshToken: getRefreshToken,
    setTokens: setTokens,
    clearTokens: clearTokens,
    logout: logout,
    migrateTokens: migrateTokens,
  };
  global.clearTokens = clearTokens;
  global.performLogout = function () { return logout({ confirm: true }); };
  global.handleLogout = function () { return logout({ confirm: true }); };

  // migrate once on load
  migrateTokens();
})(typeof window !== "undefined" ? window : globalThis);
