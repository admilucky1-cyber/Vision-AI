/* Vision AI v8.0 — shell cache */
const CACHE = "va-shell-v8";
const SHELL = ["/", "/frontend/static/css/vision-system.css?v=800", "/frontend/static/js/vision-system.js?v=800"];
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {})).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/chat") || url.pathname === "/health") return;
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
      const copy = res.clone();
      if (res.ok && (url.pathname.includes("/static/") || url.pathname.endsWith(".css") || url.pathname.endsWith(".js"))) {
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
      }
      return res;
    }).catch(() => caches.match("/") || Response.error()))
  );
});
