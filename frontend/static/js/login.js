/**
 * Vision AI v3.0.1 — Login / Register / Guest
 * Fixes [object Object] by normalizing FastAPI `detail` payloads.
 */
(function () {
  "use strict";

  var API = "";
  var mode = "login"; // login | register

  function $(id) { return document.getElementById(id); }

  function formatApiError(data, fallback) {
    if (!data) return fallback || "Request failed";
    var d = data.detail !== undefined ? data.detail : (data.error || data.message);
    if (d == null || d === "") return fallback || "Request failed";
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d.map(function (item) {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          var loc = Array.isArray(item.loc) ? item.loc.filter(function (x) { return x !== "body"; }).join(".") : "";
          var msg = item.msg || item.message || JSON.stringify(item);
          return loc ? (loc + ": " + msg) : msg;
        }
        return String(item);
      }).join(" · ");
    }
    if (typeof d === "object") {
      return d.msg || d.message || JSON.stringify(d);
    }
    return String(d);
  }

  function showAuthMessage(text, kind) {
    var el = $("authMessage");
    if (!el) return;
    el.className = "auth-msg " + (kind === "ok" ? "ok" : "err");
    el.textContent = text || "";
    // legacy
    var errText = $("errorText");
    var errBox = $("errorMsg");
    if (errText) errText.textContent = text || "";
    if (errBox && kind === "err") errBox.style.display = "flex";
    if (errBox && kind === "ok") errBox.style.display = "none";
  }

  function setLoading(on) {
    var btn = $("submitBtn");
    if (!btn) return;
    btn.disabled = !!on;
    if (on) {
      if (!btn.dataset.originalText) btn.dataset.originalText = btn.textContent;
      btn.textContent = "Please wait…";
    } else if (btn.dataset.originalText) {
      btn.textContent = btn.dataset.originalText;
      delete btn.dataset.originalText;
    }
  }

  function switchMode(next) {
    mode = next === "register" ? "register" : "login";
    document.body.classList.toggle("mode-register", mode === "register");
    document.body.classList.toggle("mode-login", mode === "login");
    var tl = $("tabLogin");
    var tr = $("tabRegister");
    if (tl) {
      tl.classList.toggle("active", mode === "login");
      tl.setAttribute("aria-selected", mode === "login" ? "true" : "false");
    }
    if (tr) {
      tr.classList.toggle("active", mode === "register");
      tr.setAttribute("aria-selected", mode === "register" ? "true" : "false");
    }
    var btn = $("submitBtn");
    if (btn) {
      btn.textContent = mode === "login" ? "Sign In" : "Create account";
      delete btn.dataset.originalText;
    }
    var pw = $("password");
    if (pw) pw.autocomplete = mode === "login" ? "current-password" : "new-password";
    showAuthMessage("", "ok");
  }

  function clearLoginGuards() {
    try {
      sessionStorage.removeItem("vision_skip_guest");
      sessionStorage.removeItem("vision_force_login");
    } catch (e) {}
  }
  function storeSession(data, username, extra) {
    extra = extra || {};
    try {
      if (data.access_token) {
        clearLoginGuards();
      localStorage.setItem("vision_ai_access_token", data.access_token);
        localStorage.setItem("vision_ai_access", data.access_token);
      }
      if (data.refresh_token) {
        localStorage.setItem("vision_ai_refresh_token", data.refresh_token);
        localStorage.setItem("vision_ai_refresh", data.refresh_token);
      }
      var user = {
        token: data.access_token || "",
        username: data.username || username || "user",
        plan: (data.user && data.user.plan) || data.plan || extra.plan || "free",
        isGuest: !!(data.isGuest || data.is_guest || extra.isGuest),
        full_name: (data.user && data.user.full_name) || extra.full_name || "",
        email: (data.user && data.user.email) || extra.email || ""
      };
      localStorage.setItem("vision_ai_user", JSON.stringify(user));
      localStorage.setItem("vision_ai_plan", user.plan);
      if (user.isGuest) localStorage.setItem("vision_ai_is_guest", "1");
      else localStorage.removeItem("vision_ai_is_guest");
    } catch (e) {}
  }

  async function handleLogin() {
    var username = ($("username") && $("username").value || "").trim();
    var password = ($("password") && $("password").value) || "";
    if (!username || !password) {
      showAuthMessage("Please enter username and password.", "err");
      return;
    }
    if (username.length < 3) {
      showAuthMessage("Username must be at least 3 characters.", "err");
      return;
    }
    if (password.length < 6) {
      showAuthMessage("Password must be at least 6 characters.", "err");
      return;
    }
    setLoading(true);
    showAuthMessage("Signing in…", "ok");
    try {
      // Backend expects OAuth2 form fields
      async function tryLogin(url, headers, body) {
        return fetch(url, { method: "POST", headers: headers, credentials: "include", body: body });
      }
      var payloadJson = JSON.stringify({ username: username, password: password });
      var formBody = new URLSearchParams();
      formBody.set("username", username);
      formBody.set("password", password);
      var endpoints = [
        [API + "/auth/token", { "Content-Type": "application/json", "Accept": "application/json" }, payloadJson],
        [API + "/auth/login", { "Content-Type": "application/json", "Accept": "application/json" }, payloadJson],
        [API + "/api/auth/login", { "Content-Type": "application/json", "Accept": "application/json" }, payloadJson],
        [API + "/auth/login", { "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json" }, formBody.toString()],
        [API + "/api/auth/login", { "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json" }, formBody.toString()]
      ];
      var res = null;
      for (var i = 0; i < endpoints.length; i++) {
        try {
          res = await tryLogin(endpoints[i][0], endpoints[i][1], endpoints[i][2]);
          if (res.status !== 404 && res.status !== 405) break;
        } catch (e) { res = null; }
      }
      if (!res) {
        showAuthMessage("Cannot reach login API.", "err");
        setLoading(false);
        return;
      }
      var data = {};
      try { data = await res.json(); } catch (e) {}
      if (!res.ok) {
        var msg = formatApiError(data, "Login failed (" + res.status + ")");
        if (res.status === 405) {
          msg = "Login API not available (405). Redeploy latest backend so POST /auth/login is active.";
        }
        if (res.status === 401) msg = "Incorrect username or password.";
        showAuthMessage(msg, "err");
        setLoading(false);
        return;
      }
      storeSession(data, username, { isGuest: false });
      showAuthMessage(data.message || "Login successful — redirecting…", "ok");
      setTimeout(function () { window.location.href = "/"; }, 450);
    } catch (err) {
      showAuthMessage("Cannot reach server. " + (err && err.message ? err.message : ""), "err");
      setLoading(false);
    }
  }

  async function handleRegister() {
    var username = ($("username") && $("username").value || "").trim();
    var password = ($("password") && $("password").value) || "";
    var email = ($("email") && $("email").value || "").trim();
    var fullName = ($("full_name") && $("full_name").value || "").trim() || username;
    if (!username || !password || !email) {
      showAuthMessage("Username, password, and email are required.", "err");
      return;
    }
    if (username.length < 3) {
      showAuthMessage("Username must be at least 3 characters.", "err");
      return;
    }
    if (password.length < 6) {
      showAuthMessage("Password must be at least 6 characters.", "err");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showAuthMessage("Please enter a valid email address.", "err");
      return;
    }
    setLoading(true);
    showAuthMessage("Creating account…", "ok");
    try {
      var res = await fetch(API + "/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username: username,
          password: password,
          email: email,
          full_name: fullName
        })
      });
      var data = {};
      try { data = await res.json(); } catch (e) {}
      if (!res.ok) {
        showAuthMessage(formatApiError(data, "Registration failed (" + res.status + ")"), "err");
        setLoading(false);
        return;
      }
      // Auto-login with form body
      var loginBody = new URLSearchParams();
      loginBody.set("username", username);
      loginBody.set("password", password);
      var loginRes = await fetch(API + "/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        credentials: "include",
        body: loginBody.toString()
      });
      var loginData = {};
      try { loginData = await loginRes.json(); } catch (e) {}
      if (loginRes.ok && loginData.access_token) {
        storeSession(loginData, username, { email: email, full_name: fullName, isGuest: false });
        showAuthMessage(data.message || "Account created — redirecting…", "ok");
        setTimeout(function () { window.location.href = "/"; }, 450);
      } else {
        showAuthMessage("Account created. Please sign in.", "ok");
        switchMode("login");
        setLoading(false);
      }
    } catch (err) {
      showAuthMessage("Cannot reach server. " + (err && err.message ? err.message : ""), "err");
      setLoading(false);
    }
  }

  async function handleGuest(ev) {
    if (ev) ev.preventDefault();
    clearLoginGuards();
    showAuthMessage("Starting guest session…", "ok");
    try {
      var res = await fetch(API + "/auth/guest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: "{}"
      });
      var data = {};
      try { data = await res.json(); } catch (e) {}
      if (!res.ok) {
        // Fallback: allow local guest if server rejects
        if (res.status === 404 || res.status === 501) {
          var localToken = "guest_local_" + Date.now();
          storeSession({ access_token: localToken, username: "guest", isGuest: true }, "guest", { isGuest: true, plan: "free" });
          window.location.href = "/";
          return;
        }
        showAuthMessage(formatApiError(data, "Guest login failed"), "err");
        return;
      }
      storeSession({
        access_token: data.access_token || data.token,
        refresh_token: data.refresh_token,
        username: data.username || "guest",
        isGuest: true,
        is_guest: true,
        plan: data.plan || "free",
        user: data.user
      }, data.username || "guest", { isGuest: true });
      showAuthMessage(data.message || "Welcome, guest — redirecting…", "ok");
      setTimeout(function () { window.location.href = "/"; }, 350);
    } catch (err) {
      // Offline-friendly guest
      try {
        storeSession({ access_token: "guest_" + Date.now(), username: "guest", isGuest: true }, "guest", { isGuest: true });
        window.location.href = "/";
      } catch (e2) {
        showAuthMessage("Guest mode unavailable.", "err");
      }
    }
  }

  function onSubmit(ev) {
    if (ev) ev.preventDefault();
    if (mode === "register") handleRegister();
    else handleLogin();
  }

  function init() {
    // If user opened /login.html intentionally, show the form (do not auto-bounce guests forever).
    // Only auto-redirect when a real non-guest session exists.
    try {
      var tok = localStorage.getItem("vision_ai_access_token");
      var userRaw = localStorage.getItem("vision_ai_user");
      var user = userRaw ? JSON.parse(userRaw) : null;
      var isGuest = !!(user && (user.is_guest || user.isGuest)) || localStorage.getItem("vision_ai_is_guest") === "1";
      if (tok && user && !isGuest && String(tok).indexOf("guest") !== 0) {
        var banner = document.getElementById("authMessage");
        if (banner) {
          banner.className = "auth-msg ok";
          banner.innerHTML = "You are signed in as <strong>" + (user.username || "user") + "</strong>. <a href=\"/\">Open chat</a> or sign in with another account below.";
        }
      }
    } catch (e) {}
    // Google OAuth error query
    try {
      var p = new URLSearchParams(window.location.search);
      var err = p.get("error");
      if (err) showAuthMessage("Google sign-in: " + decodeURIComponent(err).replace(/_/g, " "), "err");
    } catch (e) {}

    var form = $("authForm");
    if (form) form.addEventListener("submit", onSubmit);
    if ($("tabLogin")) $("tabLogin").onclick = function () { switchMode("login"); };
    if ($("tabRegister")) $("tabRegister").onclick = function () { switchMode("register"); };
    if ($("guestLink")) $("guestLink").onclick = handleGuest;
    if ($("googleBtn")) {
      $("googleBtn").onclick = function () {
        window.location.href = "/auth/google";
      };
    }
    if ($("toggleEye")) {
      $("toggleEye").onclick = function () {
        var input = $("password");
        if (!input) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        $("toggleEye").textContent = show ? "🙈" : "👁️";
      };
    }
    switchMode("login");
  }

  // Public API
  window.handleLogin = function (e) { if (e) e.preventDefault(); return handleLogin(); };
  window.handleRegister = function (e) { if (e) e.preventDefault(); return handleRegister(); };
  window.handleGuest = handleGuest;
  window.showError = function (msg) { showAuthMessage(formatApiError({ detail: msg }, String(msg)), "err"); };
  window.formatApiError = formatApiError;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
