/**
 * Minimal syntax highlighter fallback (no CDN).
 * Marks <pre><code> blocks; full language grammar optional.
 */
(function (global) {
  function highlightElement(el) {
    if (!el || el.dataset.hljsDone) return;
    el.dataset.hljsDone = "1";
    el.classList.add("hljs");
    var t = el.textContent || "";
    // Very light keyword tint for common languages
    try {
      var escaped = t
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      escaped = escaped.replace(
        /\b(function|return|const|let|var|if|else|for|while|class|import|from|def|async|await|true|false|null|None|and|or|not)\b/g,
        '<span class="hljs-keyword">$1</span>'
      );
      escaped = escaped.replace(/("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/g, '<span class="hljs-string">$1</span>');
      escaped = escaped.replace(/(\/\/[^\n]*|#(?!!).*)/g, '<span class="hljs-comment">$1</span>');
      el.innerHTML = escaped;
    } catch (e) { /* leave plain text */ }
  }
  function highlightAll() {
    document.querySelectorAll("pre code, code.hljs").forEach(highlightElement);
  }
  global.hljs = {
    highlightElement: highlightElement,
    highlightAll: highlightAll,
    highlightAuto: function (code) { return { value: code }; },
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", highlightAll);
  } else {
    highlightAll();
  }
})(window);
