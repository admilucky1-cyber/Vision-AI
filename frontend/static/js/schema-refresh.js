/** Refresh JSON-LD graph from /api/schema so APP_BASE_URL is accurate in production */
(function () {
  function apply(graph) {
    if (!graph || !graph["@graph"]) return;
    var el = document.getElementById("va-schema-graph");
    if (!el) {
      el = document.createElement("script");
      el.type = "application/ld+json";
      el.id = "va-schema-graph";
      document.head.appendChild(el);
    }
    el.textContent = JSON.stringify(graph);
  }
  fetch("/api/schema", { credentials: "omit", cache: "default" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(apply)
    .catch(function () {});
})();
