/**
 * Vision AI v5.0 — Aether Power Features
 * Non-breaking enhancements:
 *  1. Global Command Palette (Ctrl/Cmd+K)
 *  2. Granular Theme Customizer
 *  3. Context & Token Meter in composer
 *  4. Enhanced Code Actions (copy / export / run sandbox)
 *  5. Expanded keyboard navigation
 *
 * Safe: does not alter existing APIs; degrades gracefully.
 */
(function (window, document) {
  'use strict';

  var STORAGE_THEME = 'vision_aether_theme_custom';
  var STORAGE_SHORTCUTS = 'vision_aether_shortcuts_hint';

  /* ------------------------------------------------------------------ */
  /* 1. COMMAND PALETTE                                                  */
  /* ------------------------------------------------------------------ */
  var paletteOpen = false;
  var paletteEl = null;
  var paletteInput = null;
  var paletteList = null;
  var activeIndex = 0;
  var filteredCommands = [];

  function buildCommands() {
    var cmds = [
      { id: 'new-chat', label: 'New Chat', hint: 'Start a fresh conversation', keys: 'Ctrl+Shift+N', action: function () { if (typeof startNewChat === 'function') startNewChat(); } },
      { id: 'prompt-studio', label: 'Prompt Studio', hint: 'Browse prompt templates', keys: 'Ctrl+Shift+P', action: function () { if (typeof toggleHelpModal === 'function') toggleHelpModal(); } },
      { id: 'theme-custom', label: 'Customize Theme…', hint: 'Colors, radius, glow', keys: 'Ctrl+Shift+T', action: openThemePanel },
      { id: 'settings', label: 'Open Settings', hint: 'Account & preferences', action: function () { window.location.href = '/settings.html'; } },
      { id: 'studio', label: 'Model Studio', hint: 'Image / video / LoRA', action: function () { window.location.href = '/studio.html'; } },
      { id: 'skills', label: 'Skills', hint: 'Workspace skills', action: function () { window.location.href = '/skills.html'; } },
      { id: 'usage', label: 'Usage & Quota', hint: 'Token and plan usage', action: function () { window.location.href = '/usage.html'; } },
      { id: 'upgrade', label: 'Plans & Upgrade', hint: 'View subscription options', action: function () { window.location.href = '/upgrade.html'; } },
      { id: 'clear-cache', label: 'Clear Caches', hint: 'Reset local + server caches', action: function () { if (typeof clearAllCaches === 'function') clearAllCaches(); } },
      { id: 'toggle-sidebar', label: 'Toggle Sidebar', hint: 'Show / hide navigation', keys: 'Ctrl+B', action: function () { if (typeof toggleSidebar === 'function') toggleSidebar(); } },
      { id: 'focus-composer', label: 'Focus Composer', hint: 'Jump to message input', keys: 'Ctrl+/', action: focusComposer },
      { id: 'stop-gen', label: 'Stop Generation', hint: 'Abort current response', keys: 'Esc', action: function () { if (typeof stopGeneration === 'function') stopGeneration(); } },
      { id: 'search-history', label: 'Search Chat History', hint: 'Find past conversations', action: function () { if (typeof forceOpenSearch === 'function') forceOpenSearch(); } },
      { id: 'toggle-theme', label: 'Toggle Light / Dark', hint: 'Switch color scheme', action: toggleLightDark },
      { id: 'copy-last-ai', label: 'Copy Last AI Reply', hint: 'Clipboard last assistant message', action: copyLastAi },
      { id: 'delete-current', label: 'Delete Current Thread', hint: 'Remove this chat from history', action: deleteCurrentThread },
      { id: 'edit-last-user', label: 'Edit Last User Message', hint: 'Re-open last user turn for edit', keys: 'Ctrl+E', action: editLastUser },
      { id: 'export-chat', label: 'Export Chat as Markdown', hint: 'Download current thread', action: exportChatMarkdown }
    ];

    // Dynamic: recent chats
    try {
      if (typeof chatHistory !== 'undefined' && Array.isArray(chatHistory)) {
        chatHistory.slice(0, 8).forEach(function (c, i) {
          var title = (c && c.title) ? String(c.title).slice(0, 48) : ('Chat ' + (i + 1));
          cmds.push({
            id: 'chat-' + (c.id || i),
            label: 'Open: ' + title,
            hint: 'Recent conversation',
            group: 'chats',
            action: function () {
              if (typeof loadChat === 'function') loadChat(c.id);
              else if (typeof switchChat === 'function') switchChat(c.id);
            }
          });
        });
      }
    } catch (e) {}

    return cmds;
  }

  function ensurePaletteDOM() {
    if (paletteEl) return;
    paletteEl = document.createElement('div');
    paletteEl.id = 'aetherCommandPalette';
    paletteEl.className = 'aether-palette';
    paletteEl.setAttribute('role', 'dialog');
    paletteEl.setAttribute('aria-modal', 'true');
    paletteEl.setAttribute('aria-label', 'Command palette');
    paletteEl.hidden = true;
    paletteEl.innerHTML =
      '<div class="aether-palette-backdrop" data-close="1"></div>' +
      '<div class="aether-palette-panel">' +
      '  <div class="aether-palette-search">' +
      '    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>' +
      '    <input type="text" id="aetherPaletteInput" placeholder="Type a command or search…" autocomplete="off" spellcheck="false" aria-label="Command search" />' +
      '    <kbd class="aether-kbd">Esc</kbd>' +
      '  </div>' +
      '  <ul class="aether-palette-list" id="aetherPaletteList" role="listbox"></ul>' +
      '  <div class="aether-palette-footer"><span>↑↓ navigate</span><span>↵ run</span><span>esc close</span></div>' +
      '</div>';
    document.body.appendChild(paletteEl);
    paletteInput = document.getElementById('aetherPaletteInput');
    paletteList = document.getElementById('aetherPaletteList');

    paletteEl.addEventListener('click', function (e) {
      if (e.target && e.target.getAttribute('data-close') === '1') closePalette();
    });
    paletteInput.addEventListener('input', function () {
      renderPaletteList(paletteInput.value);
    });
    paletteInput.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); moveActive(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); moveActive(-1); }
      else if (e.key === 'Enter') { e.preventDefault(); runActive(); }
      else if (e.key === 'Escape') { e.preventDefault(); closePalette(); }
    });
  }

  function renderPaletteList(query) {
    var q = (query || '').trim().toLowerCase();
    var all = buildCommands();
    filteredCommands = !q ? all : all.filter(function (c) {
      return (c.label + ' ' + (c.hint || '') + ' ' + (c.id || '')).toLowerCase().indexOf(q) !== -1;
    });
    activeIndex = 0;
    paletteList.innerHTML = '';
    if (!filteredCommands.length) {
      paletteList.innerHTML = '<li class="aether-palette-empty">No matching commands</li>';
      return;
    }
    filteredCommands.forEach(function (c, i) {
      var li = document.createElement('li');
      li.className = 'aether-palette-item' + (i === 0 ? ' active' : '');
      li.setAttribute('role', 'option');
      li.dataset.index = String(i);
      li.innerHTML =
        '<div class="aether-palette-item-main">' +
        '  <span class="aether-palette-label">' + escapeHtml(c.label) + '</span>' +
        '  <span class="aether-palette-hint">' + escapeHtml(c.hint || '') + '</span>' +
        '</div>' +
        (c.keys ? '<kbd class="aether-kbd">' + escapeHtml(c.keys) + '</kbd>' : '');
      li.addEventListener('click', function () {
        activeIndex = i;
        runActive();
      });
      li.addEventListener('mouseenter', function () {
        activeIndex = i;
        updateActiveClass();
      });
      paletteList.appendChild(li);
    });
  }

  function updateActiveClass() {
    var items = paletteList.querySelectorAll('.aether-palette-item');
    items.forEach(function (el, i) {
      el.classList.toggle('active', i === activeIndex);
    });
    var active = items[activeIndex];
    if (active && active.scrollIntoView) active.scrollIntoView({ block: 'nearest' });
  }

  function moveActive(delta) {
    if (!filteredCommands.length) return;
    activeIndex = (activeIndex + delta + filteredCommands.length) % filteredCommands.length;
    updateActiveClass();
  }

  function runActive() {
    var cmd = filteredCommands[activeIndex];
    closePalette();
    if (cmd && typeof cmd.action === 'function') {
      try { cmd.action(); } catch (err) { console.warn('Command failed', err); }
    }
  }

  function openPalette() {
    ensurePaletteDOM();
    // Close Prompt Studio if open so palette is primary
    try {
      var hm = document.getElementById('helpModal');
      if (hm && hm.style.display === 'flex') hm.style.display = 'none';
    } catch (e) {}
    paletteEl.hidden = false;
    paletteOpen = true;
    paletteInput.value = '';
    renderPaletteList('');
    setTimeout(function () { paletteInput.focus(); }, 10);
  }

  function closePalette() {
    if (!paletteEl) return;
    paletteEl.hidden = true;
    paletteOpen = false;
  }

  function togglePalette() {
    if (paletteOpen) closePalette();
    else openPalette();
  }

  /* ------------------------------------------------------------------ */
  /* 2. THEME CUSTOMIZER                                                 */
  /* ------------------------------------------------------------------ */
  var themePanel = null;

  var THEME_DEFAULTS = {
    accent: '#5b8def',
    bg: '#0c0e12',
    surface: '#161a22',
    radius: 16,
    glow: 0.28,
    borderOpacity: 0.06
  };

  function loadThemeCustom() {
    try {
      var raw = localStorage.getItem(STORAGE_THEME);
      if (!raw) return Object.assign({}, THEME_DEFAULTS);
      return Object.assign({}, THEME_DEFAULTS, JSON.parse(raw));
    } catch (e) {
      return Object.assign({}, THEME_DEFAULTS);
    }
  }

  function saveThemeCustom(cfg) {
    try { localStorage.setItem(STORAGE_THEME, JSON.stringify(cfg)); } catch (e) {}
  }

  function applyThemeCustom(cfg) {
    var root = document.documentElement;
    root.style.setProperty('--aether-accent', cfg.accent);
    root.style.setProperty('--aether-bg', cfg.bg);
    root.style.setProperty('--aether-surface', cfg.surface);
    root.style.setProperty('--aether-radius-xl', cfg.radius + 'px');
    root.style.setProperty('--aether-radius-lg', Math.max(10, cfg.radius - 4) + 'px');
    root.style.setProperty('--aether-radius-md', Math.max(8, cfg.radius - 6) + 'px');
    root.style.setProperty('--aether-accent-glow', hexToRgba(cfg.accent, cfg.glow));
    root.style.setProperty('--aether-accent-soft', hexToRgba(cfg.accent, 0.14));
    root.style.setProperty('--aether-border', 'rgba(255,255,255,' + cfg.borderOpacity + ')');
    // Bridge into legacy tokens
    root.style.setProperty('--color-accent', cfg.accent);
    root.style.setProperty('--color-bg', cfg.bg);
    root.style.setProperty('--color-surface', cfg.surface);
  }

  function hexToRgba(hex, a) {
    hex = String(hex || '').replace('#', '');
    if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
    var n = parseInt(hex, 16);
    if (isNaN(n)) return 'rgba(91,141,239,' + a + ')';
    var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    return 'rgba(' + r + ',' + g + ',' + b + ',' + a + ')';
  }

  function openThemePanel() {
    if (!themePanel) {
      themePanel = document.createElement('div');
      themePanel.id = 'aetherThemePanel';
      themePanel.className = 'aether-theme-panel';
      themePanel.innerHTML =
        '<div class="aether-theme-head">' +
        '  <strong>Aether Theme</strong>' +
        '  <button type="button" class="aether-theme-close" aria-label="Close">×</button>' +
        '</div>' +
        '<div class="aether-theme-body">' +
        '  <label>Accent <input type="color" data-key="accent" /></label>' +
        '  <label>Background <input type="color" data-key="bg" /></label>' +
        '  <label>Surface <input type="color" data-key="surface" /></label>' +
        '  <label>Radius <input type="range" min="8" max="28" data-key="radius" /> <span data-val="radius"></span>px</label>' +
        '  <label>Glow <input type="range" min="0" max="60" data-key="glow" /> <span data-val="glow"></span></label>' +
        '  <label>Border opacity <input type="range" min="2" max="20" data-key="borderOpacity" /> <span data-val="borderOpacity"></span></label>' +
        '</div>' +
        '<div class="aether-theme-foot">' +
        '  <button type="button" data-act="reset">Reset</button>' +
        '  <button type="button" data-act="save" class="primary">Save</button>' +
        '</div>';
      document.body.appendChild(themePanel);

      themePanel.querySelector('.aether-theme-close').addEventListener('click', function () {
        themePanel.hidden = true;
      });
      themePanel.querySelectorAll('input').forEach(function (inp) {
        inp.addEventListener('input', function () {
          var cfg = readThemeForm();
          applyThemeCustom(cfg);
          updateThemeLabels(cfg);
        });
      });
      themePanel.querySelector('[data-act="reset"]').addEventListener('click', function () {
        applyThemeCustom(THEME_DEFAULTS);
        fillThemeForm(THEME_DEFAULTS);
        saveThemeCustom(THEME_DEFAULTS);
      });
      themePanel.querySelector('[data-act="save"]').addEventListener('click', function () {
        var cfg = readThemeForm();
        saveThemeCustom(cfg);
        applyThemeCustom(cfg);
        themePanel.hidden = true;
        if (typeof showToast === 'function') showToast('Theme saved', 'success');
      });
    }
    var cfg = loadThemeCustom();
    fillThemeForm(cfg);
    applyThemeCustom(cfg);
    themePanel.hidden = false;
  }

  function readThemeForm() {
    var panel = themePanel;
    return {
      accent: panel.querySelector('[data-key="accent"]').value,
      bg: panel.querySelector('[data-key="bg"]').value,
      surface: panel.querySelector('[data-key="surface"]').value,
      radius: parseInt(panel.querySelector('[data-key="radius"]').value, 10) || 16,
      glow: (parseInt(panel.querySelector('[data-key="glow"]').value, 10) || 28) / 100,
      borderOpacity: (parseInt(panel.querySelector('[data-key="borderOpacity"]').value, 10) || 6) / 100
    };
  }

  function fillThemeForm(cfg) {
    themePanel.querySelector('[data-key="accent"]').value = cfg.accent;
    themePanel.querySelector('[data-key="bg"]').value = cfg.bg;
    themePanel.querySelector('[data-key="surface"]').value = cfg.surface;
    themePanel.querySelector('[data-key="radius"]').value = cfg.radius;
    themePanel.querySelector('[data-key="glow"]').value = Math.round(cfg.glow * 100);
    themePanel.querySelector('[data-key="borderOpacity"]').value = Math.round(cfg.borderOpacity * 100);
    updateThemeLabels(cfg);
  }

  function updateThemeLabels(cfg) {
    themePanel.querySelector('[data-val="radius"]').textContent = cfg.radius;
    themePanel.querySelector('[data-val="glow"]').textContent = Math.round(cfg.glow * 100) + '%';
    themePanel.querySelector('[data-val="borderOpacity"]').textContent = Math.round(cfg.borderOpacity * 100) + '%';
  }

  /* ------------------------------------------------------------------ */
  /* 3. TOKEN / CONTEXT METER                                            */
  /* ------------------------------------------------------------------ */
  var meterEl = null;
  var CONTEXT_LIMIT = 128000; // soft default; models vary

  function estimateTokens(text) {
    if (!text) return 0;
    // Rough heuristic: ~4 chars per token for English; denser for code
    var chars = String(text).length;
    var codeHeavy = /[{};=<>[\]]/.test(text) ? 1.15 : 1;
    return Math.max(1, Math.round((chars / 4) * codeHeavy));
  }

  function ensureMeter() {
    if (meterEl) return meterEl;
    var shell = document.querySelector('.composer-shell, .input-container, .composer');
    if (!shell) return null;
    meterEl = document.createElement('div');
    meterEl.id = 'aetherTokenMeter';
    meterEl.className = 'aether-token-meter';
    meterEl.innerHTML =
      '<div class="aether-meter-bar"><div class="aether-meter-fill" id="aetherMeterFill"></div></div>' +
      '<span class="aether-meter-text" id="aetherMeterText">0 tokens</span>';
    // Place just above composer actions or at end of shell
    var hints = document.getElementById('composerHints');
    if (hints && hints.parentNode) {
      hints.parentNode.insertBefore(meterEl, hints.nextSibling);
    } else {
      shell.appendChild(meterEl);
    }
    return meterEl;
  }

  function updateTokenMeter() {
    ensureMeter();
    if (!meterEl) return;
    var ta = document.getElementById('message');
    var promptTokens = estimateTokens(ta ? ta.value : '');
    var historyTokens = 0;
    try {
      if (typeof chatHistory !== 'undefined' && Array.isArray(chatHistory)) {
        var current = chatHistory.find(function (c) { return c.id === (window.currentChatId || c.id); }) || chatHistory[0];
        if (current && current.messages) {
          current.messages.slice(-12).forEach(function (m) {
            historyTokens += estimateTokens(m.content || m.text || '');
          });
        }
      }
    } catch (e) {}
    var total = promptTokens + historyTokens;
    var pct = Math.min(100, Math.round((total / CONTEXT_LIMIT) * 100));
    var fill = document.getElementById('aetherMeterFill');
    var text = document.getElementById('aetherMeterText');
    if (fill) {
      fill.style.width = pct + '%';
      fill.classList.toggle('warn', pct > 70);
      fill.classList.toggle('danger', pct > 90);
    }
    if (text) {
      text.textContent = total.toLocaleString() + ' / ~' + (CONTEXT_LIMIT / 1000) + 'k context · prompt ~' + promptTokens;
    }
  }

  /* ------------------------------------------------------------------ */
  /* 4. ENHANCED CODE ACTIONS                                            */
  /* ------------------------------------------------------------------ */
  function enhanceCodeBlocks(root) {
    root = root || document.getElementById('chatOutput') || document;
    var blocks = root.querySelectorAll('pre');
    blocks.forEach(function (pre) {
      if (pre.dataset.aetherEnhanced) return;
      pre.dataset.aetherEnhanced = '1';
      var code = pre.querySelector('code');
      if (!code) return;
      var lang = (code.className || '').replace(/language-/, '').trim() || 'text';
      var toolbar = document.createElement('div');
      toolbar.className = 'aether-code-toolbar';
      toolbar.innerHTML =
        '<span class="aether-code-lang">' + escapeHtml(lang) + '</span>' +
        '<button type="button" data-act="copy" title="Copy code">Copy</button>' +
        '<button type="button" data-act="export" title="Export as file">Export</button>' +
        '<button type="button" data-act="run" title="Run in sandbox (JS only)">Run</button>';
      pre.style.position = 'relative';
      pre.insertBefore(toolbar, pre.firstChild);

      toolbar.addEventListener('click', function (e) {
        var btn = e.target.closest('button');
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();
        var act = btn.getAttribute('data-act');
        var src = code.innerText || code.textContent || '';
        if (act === 'copy') {
          copyText(src).then(function () {
            btn.textContent = 'Copied';
            setTimeout(function () { btn.textContent = 'Copy'; }, 1200);
          });
        } else if (act === 'export') {
          exportCodeFile(src, lang);
        } else if (act === 'run') {
          runSandbox(src, lang, pre);
        }
      });
    });
  }

  function exportCodeFile(src, lang) {
    var extMap = { javascript: 'js', js: 'js', typescript: 'ts', python: 'py', py: 'py', html: 'html', css: 'css', json: 'json', bash: 'sh', shell: 'sh', sql: 'sql', go: 'go', rust: 'rs', java: 'java', c: 'c', cpp: 'cpp', text: 'txt' };
    var ext = extMap[String(lang).toLowerCase()] || 'txt';
    var blob = new Blob([src], { type: 'text/plain;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'vision-code-' + Date.now() + '.' + ext;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function runSandbox(src, lang, pre) {
    var l = String(lang || '').toLowerCase();
    if (l !== 'javascript' && l !== 'js') {
      if (typeof showToast === 'function') showToast('Sandbox supports JavaScript only', 'info');
      return;
    }
    var out = pre.parentNode.querySelector('.aether-sandbox-out');
    if (!out) {
      out = document.createElement('div');
      out.className = 'aether-sandbox-out';
      pre.parentNode.insertBefore(out, pre.nextSibling);
    }
    out.textContent = 'Running…';
    try {
      var logs = [];
      var fakeConsole = {
        log: function () { logs.push(Array.prototype.slice.call(arguments).map(String).join(' ')); },
        error: function () { logs.push('Error: ' + Array.prototype.slice.call(arguments).map(String).join(' ')); },
        warn: function () { logs.push('Warn: ' + Array.prototype.slice.call(arguments).map(String).join(' ')); }
      };
      // Restricted Function — no DOM access
      var fn = new Function('console', '"use strict";\n' + src);
      var result = fn(fakeConsole);
      var text = logs.join('\n');
      if (result !== undefined) text += (text ? '\n' : '') + '→ ' + String(result);
      out.textContent = text || '(no output)';
      out.classList.remove('err');
    } catch (err) {
      out.textContent = String(err && err.message ? err.message : err);
      out.classList.add('err');
    }
  }

  /* ------------------------------------------------------------------ */
  /* 5. KEYBOARD NAVIGATION                                              */
  /* ------------------------------------------------------------------ */
  function focusComposer() {
    var ta = document.getElementById('message');
    if (ta) { ta.focus(); ta.select && ta.setSelectionRange(ta.value.length, ta.value.length); }
  }

  function toggleLightDark() {
    var root = document.documentElement;
    var cur = root.getAttribute('data-theme') || 'dark';
    var next = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    root.style.colorScheme = next;
    try { localStorage.setItem('vision_ai_theme', next); } catch (e) {}
  }

  function copyLastAi() {
    var rows = document.querySelectorAll('.message-row.ai, .message-row.assistant');
    var last = rows[rows.length - 1];
    if (!last) return;
    var bubble = last.querySelector('.message-bubble, .markdown-content');
    var text = bubble ? (bubble.innerText || bubble.textContent) : '';
    copyText(text).then(function () {
      if (typeof showToast === 'function') showToast('Copied last AI reply', 'success');
    });
  }

  function editLastUser() {
    var rows = document.querySelectorAll('.message-row.user');
    var last = rows[rows.length - 1];
    if (!last) return;
    var bubble = last.querySelector('.message-bubble');
    if (bubble && typeof editMessage === 'function') editMessage(bubble);
  }

  function deleteCurrentThread() {
    if (!confirm('Delete current chat thread from local history?')) return;
    try {
      if (typeof chatHistory !== 'undefined' && Array.isArray(chatHistory) && window.currentChatId) {
        var idx = chatHistory.findIndex(function (c) { return c.id === window.currentChatId; });
        if (idx >= 0) {
          chatHistory.splice(idx, 1);
          if (typeof saveHistory === 'function') saveHistory();
          if (typeof startNewChat === 'function') startNewChat();
          if (typeof showToast === 'function') showToast('Thread deleted', 'success');
        }
      }
    } catch (e) {
      console.warn(e);
    }
  }

  function exportChatMarkdown() {
    try {
      var lines = ['# Vision AI Chat Export', '', 'Exported: ' + new Date().toISOString(), ''];
      var current = null;
      if (typeof chatHistory !== 'undefined' && Array.isArray(chatHistory)) {
        current = chatHistory.find(function (c) { return c.id === window.currentChatId; }) || chatHistory[0];
      }
      if (!current || !current.messages) {
        if (typeof showToast === 'function') showToast('No chat to export', 'info');
        return;
      }
      current.messages.forEach(function (m) {
        var role = (m.role || 'user').toUpperCase();
        lines.push('## ' + role);
        lines.push('');
        lines.push(m.content || m.text || '');
        lines.push('');
      });
      var blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'vision-chat-' + (current.id || Date.now()) + '.md';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    } catch (e) {
      console.warn(e);
    }
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve) {
      var ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); } catch (e) {}
      ta.remove();
      resolve();
    });
  }

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* Global key router — does not break existing handlers */
  function onGlobalKey(e) {
    var mod = e.ctrlKey || e.metaKey;
    var key = e.key;

    // Command palette: Ctrl/Cmd+K  (takes priority over Prompt Studio when power is loaded)
    if (mod && !e.shiftKey && (key === 'k' || key === 'K')) {
      e.preventDefault();
      e.stopPropagation();
      togglePalette();
      return;
    }

    if (!mod) return;

    if (e.shiftKey && (key === 'n' || key === 'N')) {
      e.preventDefault();
      if (typeof startNewChat === 'function') startNewChat();
    } else if (e.shiftKey && (key === 't' || key === 'T')) {
      e.preventDefault();
      openThemePanel();
    } else if (e.shiftKey && (key === 'p' || key === 'P')) {
      e.preventDefault();
      if (typeof toggleHelpModal === 'function') toggleHelpModal();
    } else if (key === 'b' || key === 'B') {
      e.preventDefault();
      if (typeof toggleSidebar === 'function') toggleSidebar();
    } else if (key === '/' || key === '.') {
      e.preventDefault();
      focusComposer();
    } else if (key === 'e' || key === 'E') {
      e.preventDefault();
      editLastUser();
    }
  }

  /* Observe new messages for code enhancement */
  function observeChat() {
    var out = document.getElementById('chatOutput');
    if (!out || typeof MutationObserver === 'undefined') return;
    var obs = new MutationObserver(function (mutations) {
      var need = false;
      mutations.forEach(function (m) {
        if (m.addedNodes && m.addedNodes.length) need = true;
      });
      if (need) enhanceCodeBlocks(out);
    });
    obs.observe(out, { childList: true, subtree: true });
  }

  /* Boot */
  function init() {
    // Apply saved theme
    applyThemeCustom(loadThemeCustom());

    // Keyboard
    document.addEventListener('keydown', onGlobalKey, true);

    // Token meter live update
    var ta = document.getElementById('message');
    if (ta) {
      ta.addEventListener('input', function () {
        updateTokenMeter();
      });
      updateTokenMeter();
    }

    // Code blocks
    enhanceCodeBlocks();
    observeChat();

    // Expose for console / other modules
    window.AetherPower = {
      openPalette: openPalette,
      closePalette: closePalette,
      openThemePanel: openThemePanel,
      updateTokenMeter: updateTokenMeter,
      enhanceCodeBlocks: enhanceCodeBlocks
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window, document);
