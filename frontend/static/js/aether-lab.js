/**
 * Vision AI v5.3 — Lab UI
 * Telemetry overlay, thread branching, vault backup, agentic run panel
 */
(function (window, document) {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function toast(m, t) {
    if (typeof showToast === 'function') showToast(m, t || 'info');
  }
  function authHeaders() {
    var h = { 'Content-Type': 'application/json' };
    try {
      if (typeof getAccessToken === 'function' && getAccessToken())
        h['Authorization'] = 'Bearer ' + getAccessToken();
    } catch (e) {}
    return h;
  }

  /* ---------- Telemetry overlay ---------- */
  var telemTimer = null;
  function ensureTelemetry() {
    if ($('aetherTelemetry')) return;
    var el = document.createElement('div');
    el.id = 'aetherTelemetry';
    el.className = 'aether-telemetry';
    el.hidden = true;
    el.innerHTML =
      '<header><strong>Traceability</strong>' +
      '<button type="button" id="aetherTelemClose">×</button></header>' +
      '<div class="aether-telem-grid">' +
      '  <section><h4>Routing</h4><div id="telemRouting">—</div></section>' +
      '  <section><h4>RAG / Vectors</h4><div id="telemRag">—</div></section>' +
      '  <section><h4>Live</h4><div id="telemLive">Polling…</div></section>' +
      '</div>';
    document.body.appendChild(el);
    $('aetherTelemClose').onclick = function () { el.hidden = true; stopTelem(); };
  }

  async function refreshTelemetry() {
    try {
      var r = await fetch('/api/engine/telemetry', { credentials: 'same-origin', headers: authHeaders() });
      var d = await r.json();
      var routes = (d.routing && d.routing.profiles) || [];
      $('telemRouting').innerHTML = routes.slice(0, 6).map(function (p) {
        return '<div class="row"><span>' + p.profile + '</span><span>' + p.count + '× · ' + p.avg_latency_ms + 'ms</span></div>';
      }).join('') || '<em>No routing data yet</em>';
      var st = (d.rag && d.rag.store) || {};
      var h = (d.rag && d.rag.health) || {};
      $('telemRag').innerHTML =
        '<div class="row"><span>Namespace</span><span>' + (d.rag && d.rag.namespace || '—') + '</span></div>' +
        '<div class="row"><span>Chunks</span><span>' + (st.chunks || 0) + '</span></div>' +
        '<div class="row"><span>Docs</span><span>' + (st.docs || 0) + '</span></div>' +
        '<div class="row"><span>Health</span><span>' + (h.ok ? 'OK' : 'Check') + '</span></div>';
      $('telemLive').textContent = 'Updated ' + new Date().toLocaleTimeString();
    } catch (e) {
      if ($('telemLive')) $('telemLive').textContent = 'Telemetry unavailable';
    }
  }

  function openTelemetry() {
    ensureTelemetry();
    $('aetherTelemetry').hidden = false;
    refreshTelemetry();
    stopTelem();
    telemTimer = setInterval(refreshTelemetry, 4000);
  }
  function stopTelem() {
    if (telemTimer) clearInterval(telemTimer);
    telemTimer = null;
  }

  /* ---------- Branching ---------- */
  async function forkBranch(fromIndex) {
    var msgs = [];
    try {
      if (typeof chatHistory !== 'undefined' && Array.isArray(chatHistory)) {
        var cur = chatHistory.find(function (c) { return c.id === window.currentChatId; }) || chatHistory[0];
        if (cur && cur.messages) msgs = cur.messages;
      }
    } catch (e) {}
    if (!msgs.length) {
      document.querySelectorAll('.message-row').forEach(function (row) {
        var role = row.classList.contains('user') ? 'user' : 'assistant';
        var b = row.querySelector('.message-bubble, .markdown-content');
        msgs.push({ role: role, content: b ? b.innerText : '' });
      });
    }
    if (!msgs.length) return toast('Nothing to fork', 'info');
    var idx = typeof fromIndex === 'number' ? fromIndex : msgs.length - 1;
    var profile = 'auto';
    try { profile = localStorage.getItem('vision_routing_profile') || 'auto'; } catch (e) {}
    var r = await fetch('/api/engine/branches', {
      method: 'POST', credentials: 'same-origin', headers: authHeaders(),
      body: JSON.stringify({
        root_chat_id: window.currentChatId || 'local',
        from_message_index: idx,
        messages: msgs,
        label: 'Fork @ ' + idx,
        routing_profile: profile
      })
    });
    var d = await r.json();
    if (d.ok) {
      toast('Branch created: ' + (d.branch && d.branch.branch_id), 'success');
      showBranches();
    } else toast('Fork failed', 'error');
  }

  async function showBranches() {
    var r = await fetch('/api/engine/branches?root_chat_id=' + encodeURIComponent(window.currentChatId || ''), {
      credentials: 'same-origin', headers: authHeaders()
    });
    var d = await r.json();
    var list = d.branches || [];
    var panel = $('aetherBranchPanel');
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'aetherBranchPanel';
      panel.className = 'aether-branch-panel';
      document.body.appendChild(panel);
    }
    panel.hidden = false;
    panel.innerHTML = '<header><strong>Branches</strong><button type="button" id="brClose">×</button></header>' +
      (list.length ? list.map(function (b) {
        return '<button type="button" class="br-item" data-id="' + b.branch_id + '">' +
          '<span>' + (b.label || b.branch_id) + '</span>' +
          '<span class="meta">' + (b.routing_profile || '') + ' · ' + (b.message_count || 0) + ' msgs</span></button>';
      }).join('') : '<p class="empty">No branches yet — fork from a message</p>');
    $('brClose').onclick = function () { panel.hidden = true; };
  }

  function addForkButtons() {
    document.querySelectorAll('.message-row').forEach(function (row, i) {
      if (row.dataset.forkBound) return;
      row.dataset.forkBound = '1';
      var actions = row.querySelector('.msg-actions');
      if (!actions) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'msg-action-btn';
      btn.title = 'Fork thread here';
      btn.textContent = 'Fork';
      btn.onclick = function (e) {
        e.stopPropagation();
        forkBranch(i);
      };
      actions.appendChild(btn);
    });
  }

  /* ---------- Vault ---------- */
  async function runVaultBackup() {
    var r = await fetch('/api/engine/vault/backup', { method: 'POST', credentials: 'same-origin', headers: authHeaders() });
    var d = await r.json();
    if (d.ok) toast('Vault backup → ' + d.path, 'success');
    else toast('Backup failed', 'error');
  }

  async function openVaultUI() {
    var r = await fetch('/api/engine/vault/config', { credentials: 'same-origin', headers: authHeaders() });
    var d = await r.json();
    var cfg = d.config || {};
    var m = $('aetherVaultModal');
    if (!m) {
      m = document.createElement('div');
      m.id = 'aetherVaultModal';
      m.className = 'aether-vault-modal';
      document.body.appendChild(m);
    }
    m.hidden = false;
    m.innerHTML =
      '<div class="back" data-x="1"></div><div class="panel">' +
      '<header><strong>Local Vault</strong><button type="button" data-x="1">×</button></header>' +
      '<label>Backup directory<br/><input id="vaultDir" type="text" value="' + (cfg.target_dir || '') + '" style="width:100%"/></label>' +
      '<button type="button" id="vaultSaveCfg">Save path</button> ' +
      '<button type="button" id="vaultRun" class="primary">Backup now</button>' +
      '<div class="vault-list" id="vaultList"></div></div>';
    m.onclick = function (e) { if (e.target.getAttribute('data-x')) m.hidden = true; };
    $('vaultSaveCfg').onclick = async function () {
      await fetch('/api/engine/vault/config', {
        method: 'POST', credentials: 'same-origin', headers: authHeaders(),
        body: JSON.stringify({ target_dir: $('vaultDir').value, interval_min: 30 })
      });
      toast('Vault path saved', 'success');
    };
    $('vaultRun').onclick = runVaultBackup;
    var list = $('vaultList');
    list.innerHTML = (d.backups || []).map(function (b) {
      return '<div class="row">' + b.name + '</div>';
    }).join('') || '<em>No backups yet</em>';
  }

  /* ---------- Agentic panel ---------- */
  function openAgentic() {
    var m = $('aetherAgentic');
    if (!m) {
      m = document.createElement('div');
      m.id = 'aetherAgentic';
      m.className = 'aether-agentic';
      m.innerHTML =
        '<div class="back" data-x="1"></div><div class="panel">' +
        '<header><strong>Agentic Run</strong><button type="button" data-x="1">×</button></header>' +
        '<p class="hint">Restricted Python sandbox · iterative self-correction</p>' +
        '<textarea id="agentCode" rows="10" placeholder="print(sum(range(10)))\nresult = 2+2"></textarea>' +
        '<label class="chk"><input type="checkbox" id="agentLLM"/> Use LLM repair (needs API keys)</label>' +
        '<button type="button" class="primary" id="agentRun">Run loop</button>' +
        '<pre id="agentOut"></pre></div>';
      document.body.appendChild(m);
      m.onclick = function (e) { if (e.target.getAttribute('data-x')) m.hidden = true; };
      $('agentRun').onclick = async function () {
        $('agentOut').textContent = 'Running…';
        var r = await fetch('/api/engine/agentic/run', {
          method: 'POST', credentials: 'same-origin', headers: authHeaders(),
          body: JSON.stringify({
            code: $('agentCode').value,
            max_steps: 3,
            use_llm_repair: $('agentLLM').checked
          })
        });
        var d = await r.json();
        var lines = [];
        (d.steps || []).forEach(function (s) {
          lines.push('— Step ' + s.step + (s.ok ? ' OK' : ' FAIL'));
          if (s.error) lines.push('  error: ' + s.error);
          if (s.stdout) lines.push('  stdout: ' + s.stdout);
          if (s.result) lines.push('  result: ' + s.result);
        });
        lines.push(d.ok ? 'SUCCESS' : 'FAILED');
        if (d.corrected) lines.push('(self-corrected)');
        if (d.latency_ms) lines.push('latency: ' + d.latency_ms + 'ms');
        $('agentOut').textContent = lines.join('\n');
      };
    }
    m.hidden = false;
  }

  /* ---------- Boot ---------- */
  function ensureHeaderBtns() {
    var host = document.querySelector('.header-actions, .top-bar, .chat-header');
    if (!host) return;
    function add(id, title, label, fn) {
      if ($(id)) return;
      var b = document.createElement('button');
      b.id = id; b.type = 'button'; b.className = 'icon-btn header-btn';
      b.title = title; b.textContent = label;
      b.onclick = fn;
      host.appendChild(b);
    }
    add('aetherTelemBtn', 'Traceability dashboard', 'Telemetry', openTelemetry);
    add('aetherBranchBtn', 'View branches', 'Branches', showBranches);
    add('aetherVaultBtn', 'Local vault backup', 'Vault', openVaultUI);
    add('aetherAgentBtn', 'Agentic code loop', 'Agent', openAgentic);
  }

  function init() {
    ensureHeaderBtns();
    addForkButtons();
    var out = $('chatOutput');
    if (out && window.MutationObserver) {
      new MutationObserver(function () { addForkButtons(); }).observe(out, { childList: true, subtree: true });
    }
    document.addEventListener('keydown', function (e) {
      if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return;
      var k = e.key.toLowerCase();
      if (k === 'y') { e.preventDefault(); openTelemetry(); }
      if (k === 'b') { e.preventDefault(); showBranches(); }
      if (k === 'v') { e.preventDefault(); openVaultUI(); }
      if (k === 'a') { e.preventDefault(); openAgentic(); }
    }, true);
    window.AetherLab = {
      openTelemetry: openTelemetry,
      forkBranch: forkBranch,
      showBranches: showBranches,
      openVaultUI: openVaultUI,
      openAgentic: openAgentic,
      runVaultBackup: runVaultBackup
    };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window, document);
