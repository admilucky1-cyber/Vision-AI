/**
 * Vision AI — Reusable DataTable component
 * Ustadam Data Science + Web skills applied.
 *
 * Usage:
 *   const table = VisionDataTable.create({
 *     container: "#my-table",
 *     columns: [
 *       { key: "name", label: "Name", sortable: true },
 *       { key: "status", label: "Status" },
 *       { key: "created", label: "Created", sortable: true }
 *     ],
 *     fetchFn: async (params) => VisionAPI.getQuery("/api/some-list", params),
 *     searchFields: ["name", "status"],
 *     pageSize: 20
 *   });
 *   table.reload();
 */
(function (global) {
  "use strict";

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "className") node.className = attrs[k];
        else if (k === "text") node.textContent = attrs[k];
        else if (k === "html") node.innerHTML = attrs[k];
        else if (k.startsWith("on") && typeof attrs[k] === "function") {
          node.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
        } else {
          node.setAttribute(k, attrs[k]);
        }
      });
    }
    (children || []).forEach(function (c) {
      if (c == null) return;
      node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return node;
  }

  function create(options) {
    const container = typeof options.container === "string"
      ? document.querySelector(options.container)
      : options.container;
    if (!container) throw new Error("DataTable: container not found");

    const state = {
      page: 1,
      pageSize: options.pageSize || 25,
      query: "",
      sortBy: options.defaultSort || null,
      descending: !!options.defaultDesc,
      loading: false,
      error: null,
      data: null,
    };

    const columns = options.columns || [];
    const fetchFn = options.fetchFn;
    const searchFields = options.searchFields || [];
    const onRowClick = options.onRowClick || null;

    // Build shell
    container.innerHTML = "";
    container.classList.add("va-datatable");

    const toolbar = el("div", { className: "va-dt-toolbar" });
    const searchInput = el("input", {
      type: "search",
      className: "va-dt-search",
      placeholder: options.searchPlaceholder || "Search…",
    });
    toolbar.appendChild(searchInput);

    const statusEl = el("div", { className: "va-dt-status" });
    toolbar.appendChild(statusEl);

    const tableWrap = el("div", { className: "va-dt-wrap" });
    const table = el("table", { className: "va-dt-table" });
    const thead = el("thead");
    const tbody = el("tbody");
    table.appendChild(thead);
    table.appendChild(tbody);
    tableWrap.appendChild(table);

    const pager = el("div", { className: "va-dt-pager" });

    container.appendChild(toolbar);
    container.appendChild(tableWrap);
    container.appendChild(pager);

    // Header
    const headerRow = el("tr");
    columns.forEach(function (col) {
      const th = el("th", {
        className: col.sortable ? "va-dt-sortable" : "",
        text: col.label || col.key,
      });
      if (col.sortable) {
        th.style.cursor = "pointer";
        th.addEventListener("click", function () {
          if (state.sortBy === col.key) {
            state.descending = !state.descending;
          } else {
            state.sortBy = col.key;
            state.descending = false;
          }
          state.page = 1;
          reload();
        });
      }
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);

    function renderStatus() {
      if (state.loading) {
        statusEl.textContent = "Loading…";
      } else if (state.error) {
        statusEl.textContent = "Error: " + state.error;
      } else if (state.data) {
        statusEl.textContent =
          state.data.total + " item" + (state.data.total === 1 ? "" : "s") +
          " · page " + state.data.page + " / " + state.data.total_pages;
      } else {
        statusEl.textContent = "";
      }
    }

    function renderBody() {
      tbody.innerHTML = "";
      if (!state.data || !state.data.items || state.data.items.length === 0) {
        const tr = el("tr");
        const td = el("td", {
          colSpan: String(columns.length),
          className: "va-dt-empty",
          text: state.loading ? "Loading…" : (options.emptyText || "No data"),
        });
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
      }

      state.data.items.forEach(function (row) {
        const tr = el("tr");
        if (onRowClick) {
          tr.style.cursor = "pointer";
          tr.addEventListener("click", function () { onRowClick(row); });
        }
        columns.forEach(function (col) {
          let val = row[col.key];
          if (col.render && typeof col.render === "function") {
            val = col.render(val, row);
          } else if (val == null) {
            val = "";
          }
          const td = el("td");
          if (typeof val === "string" || typeof val === "number") {
            td.textContent = String(val);
          } else if (val instanceof Node) {
            td.appendChild(val);
          } else {
            td.textContent = String(val);
          }
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    }

    function renderPager() {
      pager.innerHTML = "";
      if (!state.data) return;

      const prev = el("button", {
        type: "button",
        className: "va-dt-btn",
        text: "← Prev",
        disabled: state.data.has_prev ? null : "disabled",
      });
      prev.addEventListener("click", function () {
        if (state.data.has_prev) {
          state.page -= 1;
          reload();
        }
      });

      const next = el("button", {
        type: "button",
        className: "va-dt-btn",
        text: "Next →",
        disabled: state.data.has_next ? null : "disabled",
      });
      next.addEventListener("click", function () {
        if (state.data.has_next) {
          state.page += 1;
          reload();
        }
      });

      pager.appendChild(prev);
      pager.appendChild(next);
    }

    async function reload() {
      if (!fetchFn) return;
      state.loading = true;
      state.error = null;
      renderStatus();
      renderBody();

      try {
        const params = {
          page: state.page,
          page_size: state.pageSize,
          q: state.query,
          sort_by: state.sortBy || "",
          desc: state.descending ? "1" : "0",
        };
        const result = await fetchFn(params);
        // Accept either the full prepare_table payload or a plain array
        if (Array.isArray(result)) {
          state.data = {
            items: result,
            page: 1,
            page_size: result.length,
            total: result.length,
            total_pages: 1,
            has_next: false,
            has_prev: false,
          };
        } else {
          state.data = result;
        }
      } catch (e) {
        state.error = e.message || "Failed to load";
        state.data = null;
      } finally {
        state.loading = false;
        renderStatus();
        renderBody();
        renderPager();
      }
    }

    // Search debounce
    let searchTimer = null;
    searchInput.addEventListener("input", function () {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        state.query = searchInput.value.trim();
        state.page = 1;
        reload();
      }, 280);
    });

    return {
      reload: reload,
      setQuery: function (q) {
        state.query = q || "";
        searchInput.value = state.query;
        state.page = 1;
        reload();
      },
      getState: function () { return Object.assign({}, state); },
    };
  }

  global.VisionDataTable = { create: create };
})(typeof window !== "undefined" ? window : this);
