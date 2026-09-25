/**
 * Vision AI — Shared API Client
 * Ustadam Web + Python skills applied:
 * - Single place for all fetch calls
 * - Consistent error handling
 * - Auth header injection
 * - Loading / error helpers
 */
(function (global) {
  "use strict";

  const DEFAULT_TIMEOUT_MS = 30000;

  function getToken() {
    try {
      return localStorage.getItem("vision_ai_token") ||
             localStorage.getItem("access_token") ||
             sessionStorage.getItem("vision_ai_token") ||
             "";
    } catch {
      return "";
    }
  }

  function buildHeaders(extra) {
    const headers = Object.assign(
      { "Content-Type": "application/json", "Accept": "application/json" },
      extra || {}
    );
    const token = getToken();
    if (token) {
      headers["Authorization"] = "Bearer " + token;
    }
    return headers;
  }

  async function request(method, url, body, options) {
    options = options || {};
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeout || DEFAULT_TIMEOUT_MS);

    const opts = {
      method: method,
      headers: buildHeaders(options.headers),
      signal: controller.signal,
      credentials: options.credentials || "same-origin",
    };

    if (body !== undefined && body !== null && method !== "GET" && method !== "HEAD") {
      opts.body = typeof body === "string" ? body : JSON.stringify(body);
    }

    try {
      const res = await fetch(url, opts);
      clearTimeout(timeout);

      let data = null;
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        try { data = await res.json(); } catch { data = null; }
      } else {
        data = await res.text();
      }

      if (!res.ok) {
        const err = new Error((data && data.detail) || res.statusText || "Request failed");
        err.status = res.status;
        err.data = data;
        throw err;
      }
      return data;
    } catch (e) {
      clearTimeout(timeout);
      if (e.name === "AbortError") {
        const err = new Error("Request timed out");
        err.status = 408;
        throw err;
      }
      throw e;
    }
  }

  const api = {
    get: (url, options) => request("GET", url, null, options),
    post: (url, body, options) => request("POST", url, body, options),
    put: (url, body, options) => request("PUT", url, body, options),
    patch: (url, body, options) => request("PATCH", url, body, options),
    delete: (url, options) => request("DELETE", url, null, options),

    /** Convenience for query-string GET */
    getQuery: function (url, params, options) {
      const q = new URLSearchParams();
      if (params) {
        Object.keys(params).forEach(function (k) {
          if (params[k] !== undefined && params[k] !== null && params[k] !== "") {
            q.set(k, params[k]);
          }
        });
      }
      const full = q.toString() ? url + (url.indexOf("?") >= 0 ? "&" : "?") + q.toString() : url;
      return request("GET", full, null, options);
    },
  };

  global.VisionAPI = api;
})(typeof window !== "undefined" ? window : this);
