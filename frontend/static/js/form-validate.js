/** Simple form validation UX (course Week 05 pattern → web) */
(function () {
  function mark(el, ok, msg) {
    if (!el) return;
    var wrap = el.closest(".field") || el.parentElement;
    var err = wrap && wrap.querySelector(".field-error");
    if (!ok) {
      el.setAttribute("aria-invalid", "true");
      if (wrap && !err) {
        err = document.createElement("div");
        err.className = "field-error";
        wrap.appendChild(err);
      }
      if (err) err.textContent = msg || "Invalid";
    } else {
      el.removeAttribute("aria-invalid");
      if (err) err.remove();
    }
  }

  document.addEventListener(
    "blur",
    function (e) {
      var t = e.target;
      if (!t || t.tagName !== "INPUT") return;
      if (t.required && !String(t.value || "").trim()) {
        mark(t, false, "Required");
        return;
      }
      if (t.type === "email" && t.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(t.value)) {
        mark(t, false, "Enter a valid email");
        return;
      }
      if (t.minLength > 0 && t.value.length > 0 && t.value.length < t.minLength) {
        mark(t, false, "Min " + t.minLength + " characters");
        return;
      }
      mark(t, true);
    },
    true
  );
})();
