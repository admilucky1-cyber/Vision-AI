/**
 * Vision AI v5.1 — Aether Advanced
 * 1) Local RAG status + index helpers
 * 2) Model Routing Profiles UI
 * 3) Expanded Prompt Template Library (DS / debug / curriculum)
 * 4) Session export: Markdown, JSON, CSV, PDF
 * 5) Multi-Modal Asset Inspector
 */
(function (window, document) {
  'use strict';

  var ROUTING_KEY = 'vision_routing_profile';
  var assets = []; // {id, type, name, url, meta, el}

  function $(id) { return document.getElementById(id); }
  function toast(msg, t) {
    if (typeof showToast === 'function') showToast(msg, t || 'info');
    else console.log('[Aether]', msg);
  }
  function escapeHtml(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  /* ================================================================
     1. LOCAL RAG ENGINE (client helpers + status badge)
     ================================================================ */
  async function ragStatus() {
    try {
      var headers = {};
      if (typeof getAccessToken === 'function' && getAccessToken()) {
        headers['Authorization'] = 'Bearer ' + getAccessToken();
      }
      var r = await fetch('/api/rag/status', { credentials: 'same-origin', headers: headers });
      if (!r.ok) return null;
      return await r.json();
    } catch (e) { return null; }
  }

  async function ragIndexText(text, filename) {
    var headers = { 'Content-Type': 'application/json' };
    if (typeof getAccessToken === 'function' && getAccessToken()) {
      headers['Authorization'] = 'Bearer ' + getAccessToken();
    }
    var r = await fetch('/api/rag/index', {
      method: 'POST',
      credentials: 'same-origin',
      headers: headers,
      body: JSON.stringify({ text: text, filename: filename || 'paste.txt' })
    });
    return r.json();
  }

  function ensureRagBadge() {
    var host = document.querySelector('.header-actions, .top-bar, .chat-header') || document.body;
    if ($('aetherRagBadge')) return;
    var el = document.createElement('button');
    el.id = 'aetherRagBadge';
    el.type = 'button';
    el.className = 'aether-rag-badge';
    el.title = 'Local RAG engine status';
    el.innerHTML = '<span class="dot"></span><span class="lbl">RAG</span>';
    el.addEventListener('click', async function () {
      var s = await ragStatus();
      if (!s) { toast('RAG status unavailable', 'info'); return; }
      toast((s.backend || '?') + ' · chunks ' + (s.total_chunks || s.faiss_lite_docs || 0) +
        ' · docs ' + (s.unique_documents || 0), 'success');
    });
    host.appendChild(el);
    ragStatus().then(function (s) {
      if (!s) return;
      el.classList.toggle('on', !!(s.chroma_available || s.faiss_lite_docs));
      el.querySelector('.lbl').textContent = s.backend === 'chroma' ? 'RAG' : 'RAG·lite';
    });
  }

  /* ================================================================
     2. MODEL ROUTING PROFILES
     ================================================================ */
  var profilesCache = null;

  async function loadProfiles() {
    if (profilesCache) return profilesCache;
    try {
      var r = await fetch('/api/routing/profiles', { credentials: 'same-origin' });
      var d = await r.json();
      profilesCache = (d && d.profiles) || [];
    } catch (e) {
      profilesCache = [
        { id: 'auto', label: 'Auto', description: 'Smart routing' },
        { id: 'coding', label: 'Coding', description: 'Code tasks' },
        { id: 'fast', label: 'Fast', description: 'Lightweight' },
        { id: 'rag_docs', label: 'Documents', description: 'RAG / PDFs' },
        { id: 'data_science', label: 'Data science', description: 'Pandas / ML' }
      ];
    }
    return profilesCache;
  }

  function getProfile() {
    try { return localStorage.getItem(ROUTING_KEY) || 'auto'; } catch (e) { return 'auto'; }
  }
  function setProfile(id) {
    try { localStorage.setItem(ROUTING_KEY, id); } catch (e) {}
  }

  function ensureProfileSelect() {
    if ($('aetherProfileSelect')) return;
    var shell = document.querySelector('.composer-shell, .input-container, .composer');
    if (!shell) return;
    var wrap = document.createElement('div');
    wrap.className = 'aether-profile-wrap';
    wrap.innerHTML =
      '<label class="aether-profile-label" for="aetherProfileSelect">Route</label>' +
      '<select id="aetherProfileSelect" class="aether-profile-select" title="Model routing profile"></select>';
    var hints = $('composerHints');
    if (hints && hints.parentNode) hints.parentNode.insertBefore(wrap, hints);
    else shell.insertBefore(wrap, shell.firstChild);

    loadProfiles().then(function (list) {
      var sel = $('aetherProfileSelect');
      var cur = getProfile();
      sel.innerHTML = list.map(function (p) {
        return '<option value="' + escapeHtml(p.id) + '"' + (p.id === cur ? ' selected' : '') + '>' +
          escapeHtml(p.label) + '</option>';
      }).join('');
      sel.addEventListener('change', function () {
        setProfile(sel.value);
        toast('Routing: ' + sel.options[sel.selectedIndex].text, 'success');
      });
    });
  }

  // Patch fetch to attach X-Vision-Routing-Profile on chat calls
  (function patchChatFetch() {
    if (!window.fetch || window.__aetherFetchPatched) return;
    window.__aetherFetchPatched = true;
    var orig = window.fetch.bind(window);
    window.fetch = function (input, init) {
      init = init || {};
      var url = typeof input === 'string' ? input : (input && input.url) || '';
      if (/\/chat\/(send|stream)/.test(url) || /\/api\/chat\/(send|stream)/.test(url)) {
        var headers = new Headers(init.headers || {});
        headers.set('X-Vision-Routing-Profile', getProfile());
        init = Object.assign({}, init, { headers: headers });
      }
      return orig(input, init);
    };
  })();

  /* ================================================================
     3. PROMPT TEMPLATE LIBRARY
     ================================================================ */
  var PROMPT_BLUEPRINTS = [
    { cat: 'data-science', title: 'EDA Starter', body: 'Perform exploratory data analysis on the dataset described below.\n1) Schema & dtypes\n2) Missing values\n3) Summary stats\n4) Suggested plots\n5) Next modeling steps\n\nDataset notes:\n' },
    { cat: 'data-science', title: 'Pandas Pipeline', body: 'Write a clean, documented pandas pipeline that:\n- Loads CSV\n- Cleans nulls & duplicates\n- Engineers 2–3 features\n- Splits train/test\n- Fits a baseline model\nInclude code only, with brief comments.\n' },
    { cat: 'data-science', title: 'Metrics Report', body: 'Given these model results, produce a metrics report with precision/recall/F1 (or RMSE/MAE), confusion insights, and 3 concrete improvement ideas:\n\n' },
    { cat: 'debugging', title: 'Stack Trace Autopsy', body: 'Analyze this stack trace. Identify root cause, minimal fix, and a regression test idea.\n\n```\nPASTE TRACE\n```\n' },
    { cat: 'debugging', title: 'API Failure Debug', body: 'Debug this failing HTTP/API flow. List likely causes ordered by probability, requests to log, and a fix checklist.\n\nEndpoint / error:\n' },
    { cat: 'debugging', title: 'Flaky Test Hunter', body: 'This test is flaky. Propose isolation steps, race conditions to check, and a stabilized version of the test.\n\nTest code:\n' },
    { cat: 'curriculum', title: 'Lesson Plan (60m)', body: 'Design a 60-minute lesson plan for [TOPIC] aimed at [LEVEL]. Include objectives, warm-up, core activity, assessment, and homework.\n' },
    { cat: 'curriculum', title: 'Socratic Worksheet', body: 'Create a Socratic worksheet (8–10 questions) that guides students from intuition to formal understanding of [CONCEPT]. Include answer key notes for the teacher.\n' },
    { cat: 'curriculum', title: 'Misconception Map', body: 'List the top misconceptions for [TOPIC], why students hold them, and a short classroom activity to correct each one.\n' },
    { cat: 'coding', title: 'Refactor Pass', body: 'Refactor the following code for readability, typing, and error handling without changing behavior. Show before/after summary.\n\n```\nPASTE CODE\n```\n' },
    { cat: 'coding', title: 'Unit Tests', body: 'Write thorough unit tests (pytest or jest as appropriate) for:\n\n```\nPASTE CODE\n```\nCover edge cases and failure modes.\n' }
  ];

  // Merge into global library used by Prompt Studio if present
  function mergePromptLibrary() {
    window.PROMPT_LIBRARY = window.PROMPT_LIBRARY || {};
    PROMPT_BLUEPRINTS.forEach(function (p, i) {
      var key = p.cat + '_' + i;
      window.PROMPT_LIBRARY[key] = {
        title: p.title,
        text: p.body,
        category: p.cat,
        tags: [p.cat, 'blueprint']
      };
    });
  }

  function openPromptDrawer(filterCat) {
    mergePromptLibrary();
    if (typeof window.openPromptStudioDrawer === 'function') {
      window.openPromptStudioDrawer();
      return;
    }
    // Lightweight drawer
    var d = $('aetherPromptDrawer');
    if (!d) {
      d = document.createElement('div');
      d.id = 'aetherPromptDrawer';
      d.className = 'aether-drawer';
      d.innerHTML =
        '<div class="aether-drawer-back" data-close="1"></div>' +
        '<aside class="aether-drawer-panel">' +
        '  <header><strong>Prompt Blueprints</strong><button type="button" data-close="1">×</button></header>' +
        '  <input type="search" id="aetherPromptSearch" placeholder="Search templates…" />' +
        '  <div class="aether-drawer-chips" id="aetherPromptChips"></div>' +
        '  <div class="aether-drawer-list" id="aetherPromptList"></div>' +
        '</aside>';
      document.body.appendChild(d);
      d.addEventListener('click', function (e) {
        if (e.target.getAttribute('data-close')) d.hidden = true;
      });
      $('aetherPromptSearch').addEventListener('input', function () {
        renderPromptList(this.value);
      });
    }
    d.hidden = false;
    renderPromptChips(filterCat);
    renderPromptList('', filterCat);
  }

  function renderPromptChips(active) {
    var cats = ['all', 'data-science', 'debugging', 'curriculum', 'coding'];
    var el = $('aetherPromptChips');
    if (!el) return;
    el.innerHTML = cats.map(function (c) {
      return '<button type="button" class="chip' + ((active || 'all') === c ? ' on' : '') + '" data-cat="' + c + '">' + c + '</button>';
    }).join('');
    el.querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () {
        renderPromptChips(b.dataset.cat);
        renderPromptList($('aetherPromptSearch').value, b.dataset.cat);
      });
    });
  }

  function renderPromptList(q, cat) {
    q = (q || '').toLowerCase();
    cat = cat || 'all';
    var list = $('aetherPromptList');
    if (!list) return;
    var items = PROMPT_BLUEPRINTS.filter(function (p) {
      if (cat !== 'all' && p.cat !== cat) return false;
      if (!q) return true;
      return (p.title + ' ' + p.body + ' ' + p.cat).toLowerCase().indexOf(q) !== -1;
    });
    list.innerHTML = items.map(function (p, i) {
      return '<button type="button" class="aether-prompt-item" data-i="' + i + '">' +
        '<span class="t">' + escapeHtml(p.title) + '</span>' +
        '<span class="c">' + escapeHtml(p.cat) + '</span></button>';
    }).join('') || '<p class="empty">No templates</p>';
    // re-filter index mapping
    list.querySelectorAll('.aether-prompt-item').forEach(function (btn, idx) {
      btn.addEventListener('click', function () {
        var p = items[idx];
        var ta = $('message');
        if (ta && p) {
          ta.value = p.body;
          ta.focus();
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          toast('Template loaded', 'success');
        }
        $('aetherPromptDrawer').hidden = true;
      });
    });
  }

  /* ================================================================
     4. SESSION EXPORT — MD / JSON / CSV / PDF
     ================================================================ */
  function currentMessages() {
    try {
      if (typeof chatHistory !== 'undefined' && Array.isArray(chatHistory)) {
        var cur = chatHistory.find(function (c) { return c.id === window.currentChatId; }) || chatHistory[0];
        if (cur && cur.messages) return cur.messages;
      }
    } catch (e) {}
    // DOM fallback
    var rows = document.querySelectorAll('.message-row');
    var out = [];
    rows.forEach(function (row) {
      var role = row.classList.contains('user') ? 'user' : 'assistant';
      var bubble = row.querySelector('.message-bubble, .markdown-content');
      out.push({ role: role, content: bubble ? (bubble.innerText || '') : '' });
    });
    return out;
  }

  function downloadBlob(blob, filename) {
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 600);
  }

  function exportJSON() {
    var msgs = currentMessages();
    if (!msgs.length) return toast('No messages', 'info');
    var payload = {
      app: 'Vision AI',
      version: (document.querySelector('meta[name="app-version"]') || {}).content || '5.1',
      exported_at: new Date().toISOString(),
      chat_id: window.currentChatId || null,
      messages: msgs
    };
    downloadBlob(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }),
      'vision-chat-' + Date.now() + '.json');
    toast('JSON exported', 'success');
  }

  function exportCSV() {
    var msgs = currentMessages();
    if (!msgs.length) return toast('No messages', 'info');
    var lines = ['role,content'];
    msgs.forEach(function (m) {
      var c = String(m.content || m.text || '').replace(/"/g, '""').replace(/\n/g, ' ');
      lines.push('"' + (m.role || '') + '","' + c + '"');
    });
    downloadBlob(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }),
      'vision-chat-' + Date.now() + '.csv');
    toast('CSV exported', 'success');
  }

  function exportPDF() {
    var msgs = currentMessages();
    if (!msgs.length) return toast('No messages', 'info');
    // Print-friendly HTML window (no external lib required)
    var w = window.open('', '_blank', 'noopener,noreferrer,width=800,height=900');
    if (!w) return toast('Popup blocked — allow popups for PDF', 'info');
    var body = msgs.map(function (m) {
      return '<section class="msg"><h3>' + escapeHtml((m.role || '').toUpperCase()) + '</h3>' +
        '<pre>' + escapeHtml(m.content || m.text || '') + '</pre></section>';
    }).join('');
    w.document.write(
      '<!DOCTYPE html><html><head><title>Vision AI Chat</title>' +
      '<style>body{font-family:system-ui,sans-serif;padding:24px;color:#111}' +
      'h1{font-size:18px}h3{font-size:12px;color:#555;margin:16px 0 4px}' +
      'pre{white-space:pre-wrap;font-size:12px;line-height:1.45;background:#f6f7f9;padding:10px;border-radius:8px}' +
      '@media print{button{display:none}}</style></head><body>' +
      '<h1>Vision AI — Session Report</h1>' +
      '<p style="color:#666;font-size:12px">' + new Date().toISOString() + '</p>' +
      body +
      '<p style="margin-top:24px"><button onclick="window.print()">Print / Save PDF</button></p>' +
      '</body></html>'
    );
    w.document.close();
    toast('PDF window opened — use Print → Save as PDF', 'success');
  }

  function openExportMenu() {
    var m = $('aetherExportMenu');
    if (!m) {
      m = document.createElement('div');
      m.id = 'aetherExportMenu';
      m.className = 'aether-export-menu';
      m.innerHTML =
        '<button type="button" data-fmt="md">Markdown</button>' +
        '<button type="button" data-fmt="json">JSON</button>' +
        '<button type="button" data-fmt="csv">CSV</button>' +
        '<button type="button" data-fmt="pdf">PDF report</button>';
      document.body.appendChild(m);
      m.addEventListener('click', function (e) {
        var b = e.target.closest('button');
        if (!b) return;
        var f = b.getAttribute('data-fmt');
        m.hidden = true;
        if (f === 'json') exportJSON();
        else if (f === 'csv') exportCSV();
        else if (f === 'pdf') exportPDF();
        else if (f === 'md' && window.AetherPower && AetherPower.openPalette) {
          // reuse markdown export via palette command simulation
          try {
            var ev = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true });
          } catch (err) {}
          // direct call if exposed later — fallback DOM scrape MD
          exportMarkdown();
        }
      });
      document.addEventListener('click', function (e) {
        if (m && !m.contains(e.target) && e.target.id !== 'aetherExportBtn') m.hidden = true;
      });
    }
    m.hidden = false;
    var btn = $('aetherExportBtn');
    if (btn) {
      var r = btn.getBoundingClientRect();
      m.style.top = (r.bottom + 6) + 'px';
      m.style.right = Math.max(8, window.innerWidth - r.right) + 'px';
    }
  }

  function exportMarkdown() {
    var msgs = currentMessages();
    if (!msgs.length) return toast('No messages', 'info');
    var lines = ['# Vision AI Chat', '', 'Exported: ' + new Date().toISOString(), ''];
    msgs.forEach(function (m) {
      lines.push('## ' + String(m.role || 'user').toUpperCase(), '', m.content || m.text || '', '');
    });
    downloadBlob(new Blob([lines.join('\n')], { type: 'text/markdown' }), 'vision-chat-' + Date.now() + '.md');
    toast('Markdown exported', 'success');
  }

  function ensureExportButton() {
    if ($('aetherExportBtn')) return;
    var host = document.querySelector('.header-actions, .top-bar, .chat-header');
    if (!host) return;
    var btn = document.createElement('button');
    btn.id = 'aetherExportBtn';
    btn.type = 'button';
    btn.className = 'icon-btn header-btn';
    btn.title = 'Export session';
    btn.setAttribute('aria-label', 'Export session');
    btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>';
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      openExportMenu();
    });
    host.appendChild(btn);
  }

  /* ================================================================
     5. MULTI-MODAL ASSET INSPECTOR
     ================================================================ */
  function registerAsset(item) {
    item.id = item.id || ('asset-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7));
    assets.unshift(item);
    if (assets.length > 40) assets.length = 40;
    renderInspectorList();
  }

  function ensureInspector() {
    if ($('aetherInspector')) return;
    var root = document.createElement('div');
    root.id = 'aetherInspector';
    root.className = 'aether-inspector';
    root.hidden = true;
    root.innerHTML =
      '<div class="aether-inspector-back" data-close="1"></div>' +
      '<div class="aether-inspector-panel">' +
      '  <header><strong>Asset Inspector</strong>' +
      '    <button type="button" id="aetherInspectorClose" data-close="1">×</button></header>' +
      '  <div class="aether-inspector-layout">' +
      '    <aside class="aether-inspector-list" id="aetherInspectorList"></aside>' +
      '    <main class="aether-inspector-view" id="aetherInspectorView">' +
      '      <p class="empty">Select an asset</p>' +
      '    </main>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(root);
    root.addEventListener('click', function (e) {
      if (e.target.getAttribute('data-close')) root.hidden = true;
    });
  }

  function openInspector() {
    ensureInspector();
    $('aetherInspector').hidden = false;
    renderInspectorList();
  }

  function renderInspectorList() {
    var list = $('aetherInspectorList');
    if (!list) return;
    if (!assets.length) {
      list.innerHTML = '<p class="empty">No media yet — upload images or generate graphs</p>';
      return;
    }
    list.innerHTML = assets.map(function (a) {
      return '<button type="button" class="asset-row" data-id="' + escapeHtml(a.id) + '">' +
        '<span class="kind">' + escapeHtml(a.type || 'file') + '</span>' +
        '<span class="name">' + escapeHtml(a.name || a.id) + '</span></button>';
    }).join('');
    list.querySelectorAll('.asset-row').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var a = assets.find(function (x) { return x.id === btn.dataset.id; });
        showAsset(a);
      });
    });
  }

  function showAsset(a) {
    var view = $('aetherInspectorView');
    if (!view || !a) return;
    if (a.type === 'image' || /\.(png|jpe?g|gif|webp|bmp)$/i.test(a.name || '')) {
      view.innerHTML =
        '<div class="inspect-toolbar">' +
        '  <button type="button" data-z="in">Zoom +</button>' +
        '  <button type="button" data-z="out">Zoom −</button>' +
        '  <button type="button" data-z="reset">Reset</button>' +
        '</div>' +
        '<div class="inspect-stage"><img id="aetherInspectImg" src="' + escapeHtml(a.url) + '" alt="" /></div>' +
        '<div class="inspect-meta" id="aetherInspectMeta">Loading metadata…</div>';
      var img = $('aetherInspectImg');
      var scale = 1;
      view.querySelector('.inspect-toolbar').addEventListener('click', function (e) {
        var z = e.target.getAttribute('data-z');
        if (!z) return;
        if (z === 'in') scale = Math.min(4, scale + 0.25);
        if (z === 'out') scale = Math.max(0.25, scale - 0.25);
        if (z === 'reset') scale = 1;
        img.style.transform = 'scale(' + scale + ')';
      });
      img.onload = function () {
        $('aetherInspectMeta').innerHTML =
          '<div><b>Name</b> ' + escapeHtml(a.name || '') + '</div>' +
          '<div><b>Size</b> ' + img.naturalWidth + ' × ' + img.naturalHeight + '</div>' +
          '<div><b>Type</b> ' + escapeHtml(a.type || 'image') + '</div>' +
          (a.meta ? '<pre>' + escapeHtml(JSON.stringify(a.meta, null, 2)) + '</pre>' : '');
      };
    } else {
      view.innerHTML =
        '<div class="inspect-meta">' +
        '<div><b>Name</b> ' + escapeHtml(a.name || '') + '</div>' +
        '<div><b>Type</b> ' + escapeHtml(a.type || 'file') + '</div>' +
        (a.url ? '<div><a href="' + escapeHtml(a.url) + '" target="_blank" rel="noopener">Open</a></div>' : '') +
        (a.meta ? '<pre>' + escapeHtml(JSON.stringify(a.meta, null, 2)) + '</pre>' : '') +
        '</div>';
    }
  }

  function scanPageAssets() {
    document.querySelectorAll('#chatOutput img, .message-bubble img, .markdown-content img').forEach(function (img) {
      var src = img.currentSrc || img.src;
      if (!src || src.indexOf('data:image/svg') === 0) return;
      if (assets.some(function (a) { return a.url === src; })) return;
      registerAsset({
        type: 'image',
        name: (img.alt || src.split('/').pop() || 'image').slice(0, 80),
        url: src,
        meta: { width: img.naturalWidth, height: img.naturalHeight }
      });
    });
  }

  function observeAssets() {
    var out = $('chatOutput');
    if (!out || !window.MutationObserver) return;
    var obs = new MutationObserver(function () { scanPageAssets(); });
    obs.observe(out, { childList: true, subtree: true });
  }

  function ensureInspectorButton() {
    if ($('aetherInspectorBtn')) return;
    var host = document.querySelector('.header-actions, .top-bar, .chat-header');
    if (!host) return;
    var btn = document.createElement('button');
    btn.id = 'aetherInspectorBtn';
    btn.type = 'button';
    btn.className = 'icon-btn header-btn';
    btn.title = 'Asset inspector';
    btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>';
    btn.addEventListener('click', function () {
      scanPageAssets();
      openInspector();
    });
    host.appendChild(btn);
  }

  /* ================================================================
     Command palette integration + boot
     ================================================================ */
  function extendPalette() {
    // If AetherPower exists, users can still use Ctrl+K; we add header shortcuts
    var host = document.querySelector('.header-actions, .top-bar, .chat-header');
    if (!host || $('aetherBlueprintsBtn')) return;
    var b = document.createElement('button');
    b.id = 'aetherBlueprintsBtn';
    b.type = 'button';
    b.className = 'icon-btn header-btn';
    b.title = 'Prompt blueprints';
    b.textContent = '⌘';
    b.addEventListener('click', function () { openPromptDrawer('all'); });
    host.appendChild(b);
  }

  function init() {
    mergePromptLibrary();
    ensureRagBadge();
    ensureProfileSelect();
    ensureExportButton();
    ensureInspectorButton();
    extendPalette();
    observeAssets();
    scanPageAssets();

    // Keyboard: Ctrl+Shift+E export menu, Ctrl+Shift+I inspector, Ctrl+Shift+L library
    document.addEventListener('keydown', function (e) {
      if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return;
      var k = e.key.toLowerCase();
      if (k === 'e') { e.preventDefault(); openExportMenu(); }
      if (k === 'i') { e.preventDefault(); scanPageAssets(); openInspector(); }
      if (k === 'l') { e.preventDefault(); openPromptDrawer('all'); }
    }, true);

    window.AetherAdvanced = {
      ragStatus: ragStatus,
      ragIndexText: ragIndexText,
      openPromptDrawer: openPromptDrawer,
      exportJSON: exportJSON,
      exportCSV: exportCSV,
      exportPDF: exportPDF,
      openInspector: openInspector,
      getProfile: getProfile,
      setProfile: setProfile
    };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window, document);
