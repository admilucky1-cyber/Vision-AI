/**
 * Vision AI v5.2 — Aether Engine UI
 * - Streaming RAG citation cards
 * - Export template modal (range, style, exclude system)
 * - Multi-model split view (dual profile)
 * - Portable config export/import (localStorage pack)
 * - Context governor client helper
 * - Doc visualizer pane for citation jumps
 */
(function (window, document) {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function toast(m, t) {
    if (typeof showToast === 'function') showToast(m, t || 'info');
  }
  function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  /* ---------- Citations ---------- */
  function renderCitations(citations, anchorEl) {
    if (!citations || !citations.length || !anchorEl) return;
    var box = document.createElement('div');
    box.className = 'aether-citations';
    box.innerHTML = '<div class="aether-citations-title">Sources</div>' +
      citations.map(function (c) {
        return '<button type="button" class="aether-cite-card" data-cid="' + esc(c.id) + '" data-text="' + esc((c.text || c.snippet || '').slice(0, 2000)) + '" data-file="' + esc(c.filename || '') + '">' +
          '<span class="cid">' + esc(c.id) + '</span>' +
          '<span class="fn">' + esc(c.filename || 'doc') + '</span>' +
          '<span class="sn">' + esc((c.snippet || '').slice(0, 140)) + '</span></button>';
      }).join('');
    anchorEl.appendChild(box);
    box.querySelectorAll('.aether-cite-card').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openDocViewer(btn.getAttribute('data-file'), btn.getAttribute('data-text'));
      });
    });
  }

  async function fetchCitations(query) {
    try {
      var headers = { 'Content-Type': 'application/json' };
      if (typeof getAccessToken === 'function' && getAccessToken()) {
        headers['Authorization'] = 'Bearer ' + getAccessToken();
      }
      var r = await fetch('/api/rag/search', {
        method: 'POST', credentials: 'same-origin', headers: headers,
        body: JSON.stringify({ query: query, top_k: 4 })
      });
      if (!r.ok) return [];
      var d = await r.json();
      return d.citations || [];
    } catch (e) { return []; }
  }

  /* ---------- Doc visualizer ---------- */
  function openDocViewer(filename, text) {
    var v = $('aetherDocViewer');
    if (!v) {
      v = document.createElement('div');
      v.id = 'aetherDocViewer';
      v.className = 'aether-doc-viewer';
      v.innerHTML = '<div class="back" data-x="1"></div><div class="panel"><header><strong id="aetherDocTitle">Source</strong><button type="button" data-x="1">×</button></header><pre id="aetherDocBody"></pre></div>';
      document.body.appendChild(v);
      v.addEventListener('click', function (e) {
        if (e.target.getAttribute('data-x')) v.hidden = true;
      });
    }
    $('aetherDocTitle').textContent = filename || 'Source fragment';
    $('aetherDocBody').textContent = text || '';
    v.hidden = false;
  }

  /* ---------- Export modal ---------- */
  function openExportModal() {
    var m = $('aetherExportModal');
    if (!m) {
      m = document.createElement('div');
      m.id = 'aetherExportModal';
      m.className = 'aether-export-modal';
      m.innerHTML =
        '<div class="back" data-x="1"></div>' +
        '<div class="panel">' +
        ' <header><strong>Export session</strong><button type="button" data-x="1">×</button></header>' +
        ' <label>Format <select id="exFmt"><option value="md">Markdown</option><option value="json">JSON</option><option value="csv">CSV</option><option value="pdf">PDF</option></select></label>' +
        ' <label>Range <select id="exRange"><option value="all">All messages</option><option value="last10">Last 10</option><option value="last20">Last 20</option><option value="user_only">User only</option><option value="ai_only">AI only</option></select></label>' +
        ' <label class="chk"><input type="checkbox" id="exSys" checked /> Exclude system / governor notes</label>' +
        ' <label class="chk"><input type="checkbox" id="exCompact" /> Compact styling</label>' +
        ' <button type="button" class="go" id="exGo">Export</button>' +
        '</div>';
      document.body.appendChild(m);
      m.addEventListener('click', function (e) {
        if (e.target.getAttribute('data-x')) m.hidden = true;
      });
      $('exGo').addEventListener('click', function () {
        runExport({
          fmt: $('exFmt').value,
          range: $('exRange').value,
          excludeSystem: $('exSys').checked,
          compact: $('exCompact').checked
        });
        m.hidden = true;
      });
    }
    m.hidden = false;
  }

  function collectMessages(opts) {
    var msgs = [];
    if (window.AetherAdvanced && false) {}
    try {
      if (typeof chatHistory !== 'undefined' && Array.isArray(chatHistory)) {
        var cur = chatHistory.find(function (c) { return c.id === window.currentChatId; }) || chatHistory[0];
        if (cur && cur.messages) msgs = cur.messages.slice();
      }
    } catch (e) {}
    if (!msgs.length) {
      document.querySelectorAll('.message-row').forEach(function (row) {
        var role = row.classList.contains('user') ? 'user' : 'assistant';
        var b = row.querySelector('.message-bubble, .markdown-content');
        msgs.push({ role: role, content: b ? b.innerText : '' });
      });
    }
    if (opts.excludeSystem) {
      msgs = msgs.filter(function (m) {
        var r = (m.role || '').toLowerCase();
        var c = m.content || m.text || '';
        return r !== 'system' && c.indexOf('[Context governor') === -1;
      });
    }
    if (opts.range === 'last10') msgs = msgs.slice(-10);
    if (opts.range === 'last20') msgs = msgs.slice(-20);
    if (opts.range === 'user_only') msgs = msgs.filter(function (m) { return (m.role || '') === 'user'; });
    if (opts.range === 'ai_only') msgs = msgs.filter(function (m) { return (m.role || '') !== 'user'; });
    return msgs;
  }

  function runExport(opts) {
    var msgs = collectMessages(opts);
    if (!msgs.length) return toast('No messages', 'info');
    if (window.AetherAdvanced) {
      if (opts.fmt === 'json') return AetherAdvanced.exportJSON();
      if (opts.fmt === 'csv') return AetherAdvanced.exportCSV();
      if (opts.fmt === 'pdf') return AetherAdvanced.exportPDF();
    }
    var lines = ['# Vision AI Export', '', 'Range: ' + opts.range, ''];
    msgs.forEach(function (m) {
      lines.push('## ' + String(m.role || '').toUpperCase(), '', m.content || m.text || '', '');
    });
    var blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'vision-export-' + Date.now() + '.md';
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    toast('Exported', 'success');
  }

  /* ---------- Split view (dual profile) ---------- */
  var splitOn = false;
  function toggleSplitView() {
    splitOn = !splitOn;
    document.body.classList.toggle('aether-split', splitOn);
    var pane = $('aetherSplitPane');
    if (splitOn && !pane) {
      pane = document.createElement('div');
      pane.id = 'aetherSplitPane';
      pane.className = 'aether-split-pane';
      pane.innerHTML = '<header>Co-Pilot (fast profile)</header><div id="aetherSplitOut" class="aether-split-out"><p class="hint">Send a message — secondary profile runs in parallel when enabled.</p></div>';
      var main = document.querySelector('main') || document.body;
      main.appendChild(pane);
    }
    if (pane) pane.hidden = !splitOn;
    toast(splitOn ? 'Split view on' : 'Split view off', 'info');
  }

  /* ---------- Portable config ---------- */
  function exportConfigPack() {
    var pack = {
      version: 1,
      exported_at: new Date().toISOString(),
      theme: null,
      routing_profile: null,
      aether_theme_custom: null,
      prompt_favorites: null
    };
    try {
      pack.theme = localStorage.getItem('vision_ai_theme');
      pack.routing_profile = localStorage.getItem('vision_routing_profile');
      pack.aether_theme_custom = localStorage.getItem('vision_aether_theme_custom');
    } catch (e) {}
    var blob = new Blob([JSON.stringify(pack, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'vision-aether-config.json';
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    toast('Config pack exported', 'success');
  }

  function importConfigPack(file) {
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var pack = JSON.parse(reader.result);
        if (pack.theme) localStorage.setItem('vision_ai_theme', pack.theme);
        if (pack.routing_profile) localStorage.setItem('vision_routing_profile', pack.routing_profile);
        if (pack.aether_theme_custom) localStorage.setItem('vision_aether_theme_custom', pack.aether_theme_custom);
        toast('Config imported — reload to apply theme', 'success');
      } catch (e) {
        toast('Invalid config file', 'error');
      }
    };
    reader.readAsText(file);
  }

  /* ---------- Hook send for citations ---------- */
  function hookSendCitations() {
    var orig = window.sendMessage;
    if (typeof orig !== 'function' || orig.__aetherCited) return;
    var wrapped = async function () {
      var ta = $('message');
      var q = ta ? ta.value : '';
      var p = orig.apply(this, arguments);
      try {
        if (q && q.length > 8) {
          var cites = await fetchCitations(q.slice(0, 500));
          if (cites.length) {
            setTimeout(function () {
              var rows = document.querySelectorAll('.message-row.ai, .message-row.assistant');
              var last = rows[rows.length - 1];
              if (last) renderCitations(cites, last.querySelector('.message-bubble') || last);
            }, 1200);
          }
        }
      } catch (e) {}
      return p;
    };
    wrapped.__aetherCited = true;
    window.sendMessage = wrapped;
  }

  /* ---------- Boot ---------- */
  function ensureButtons() {
    var host = document.querySelector('.header-actions, .top-bar, .chat-header');
    if (!host) return;
    if (!$('aetherExportModalBtn')) {
      var b1 = document.createElement('button');
      b1.id = 'aetherExportModalBtn'; b1.type = 'button'; b1.className = 'icon-btn header-btn';
      b1.title = 'Export options'; b1.textContent = '⇪';
      b1.addEventListener('click', openExportModal);
      host.appendChild(b1);
    }
    if (!$('aetherSplitBtn')) {
      var b2 = document.createElement('button');
      b2.id = 'aetherSplitBtn'; b2.type = 'button'; b2.className = 'icon-btn header-btn';
      b2.title = 'Split co-pilot view'; b2.textContent = '⧉';
      b2.addEventListener('click', toggleSplitView);
      host.appendChild(b2);
    }
    if (!$('aetherCfgBtn')) {
      var b3 = document.createElement('button');
      b3.id = 'aetherCfgBtn'; b3.type = 'button'; b3.className = 'icon-btn header-btn';
      b3.title = 'Export config pack'; b3.textContent = '⧉︎';
      b3.addEventListener('click', exportConfigPack);
      host.appendChild(b3);
    }
  }

  function init() {
    ensureButtons();
    hookSendCitations();
    document.addEventListener('keydown', function (e) {
      if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return;
      if (e.key.toLowerCase() === 'x') { e.preventDefault(); openExportModal(); }
      if (e.key.toLowerCase() === 's' && e.altKey) { e.preventDefault(); toggleSplitView(); }
    }, true);
    window.AetherEngine = {
      openExportModal: openExportModal,
      toggleSplitView: toggleSplitView,
      exportConfigPack: exportConfigPack,
      importConfigPack: importConfigPack,
      openDocViewer: openDocViewer,
      fetchCitations: fetchCitations
    };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window, document);
