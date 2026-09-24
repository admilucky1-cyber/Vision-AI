/**
 * Vision AI — React-inspired core (vanilla)
 * Benefits applied without rewriting to React:
 * 1) Single source of truth (state)
 * 2) Subscribe / notify (like setState + re-render)
 * 3) Declarative patches only when data changes
 * 4) Event bus for components
 */
(function (w) {
  var state = {
    theme: "dark",
    sidebarOpen: false,
    currentChatId: null,
    sending: false,
    online: true,
    version: null,
  };
  var listeners = [];

  function getState() {
    return Object.assign({}, state);
  }

  function setState(partial) {
    var next = Object.assign({}, state, partial || {});
    var changed = false;
    for (var k in next) {
      if (next[k] !== state[k]) {
        changed = true;
        break;
      }
    }
    if (!changed) return state;
    state = next;
    listeners.slice().forEach(function (fn) {
      try {
        fn(getState());
      } catch (e) {
        console.warn("[va-store] listener", e);
      }
    });
    return state;
  }

  function subscribe(fn) {
    if (typeof fn !== "function") return function () {};
    listeners.push(fn);
    return function unsubscribe() {
      listeners = listeners.filter(function (x) {
        return x !== fn;
      });
    };
  }

  // Event bus (component communication)
  var bus = {};
  function on(evt, fn) {
    (bus[evt] = bus[evt] || []).push(fn);
    return function () {
      bus[evt] = (bus[evt] || []).filter(function (x) {
        return x !== fn;
      });
    };
  }
  function emit(evt, payload) {
    (bus[evt] || []).forEach(function (fn) {
      try {
        fn(payload);
      } catch (e) {
        console.warn("[va-store] emit", evt, e);
      }
    });
  }

  w.VAStore = { getState: getState, setState: setState, subscribe: subscribe, on: on, emit: emit };

  // Sync sidebar class from state (declarative)
  subscribe(function (s) {
    try {
      document.body.classList.toggle("sidebar-open", !!s.sidebarOpen);
      var ov = document.getElementById("sidebar-overlay");
      if (ov) {
        if (s.sidebarOpen) {
          ov.classList.add("active");
          ov.style.display = "block";
          ov.style.pointerEvents = "auto";
        } else {
          ov.classList.remove("active", "show", "open");
          ov.style.display = "none";
          ov.style.pointerEvents = "none";
        }
      }
      document.body.style.overflow = s.sidebarOpen ? "hidden" : "";
    } catch (e) {}
  });

  // Sending flag → disable send button consistently
  subscribe(function (s) {
    var btn = document.getElementById("sendBtn");
    if (btn) btn.disabled = !!s.sending;
  });

  // Boot: clear stuck overlay
  function boot() {
    setState({ sidebarOpen: false, sending: false });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})(window);
