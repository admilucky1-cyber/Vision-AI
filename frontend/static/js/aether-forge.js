/**
 * Vision AI v5.4 Forge UI
 * Workbench, cost tracker, memory graph canvas, diagnostics, prompt vars, exec history
 */
(function (window, document) {
  'use strict';

  function $(id) { return document.getElementById(id); }
  function toast(m, t) {
    if (typeof showToast === 'function') showToast(m, t || 'info');
  }
  function headers() {
    var h = { 'Content-Type': 'application/json' };
    try {
      if (typeof getAccessToken === 'function' && getAccessToken())
        h.Authorization = 'Bearer ' + getAccessToken();
    } catch (e) {}
    return h;
  }

  /* Prompt variable injection */
  function injectPromptVars(text) {
    var out = text || '';
    var now = new Date();
    out = out.replace(/\{date\}/gi, now.toISOString().slice(0, 10));
    out = out.replace(/\{time\}/gi, now.toLocaleTimeString());
    var code = '';
    var pre = document.querySelector('#chatOutput pre code, .message-row.ai pre code');
    if (pre) code = pre.innerText || '';
    out = out.replace(/\{code\}/gi, code.slice(0, 3000));
    var fileHint = '';
    try {
      var fp = document.getElementById('filePreviewArea');
      if (fp) fileHint = fp.innerText || '';
    } catch (e) {}
    out = out.replace(/\{file\}/gi, fileHint.slice(0, 1500));
    return out;
  }

  // Hook template loads if composer changes from blueprints
  function watchComposerVars() {
    var ta = $('message');
    if (!ta || ta.dataset.varHooked) return;
    ta.dataset.varHooked = '1';
    ta.addEventListener('blur', function () {
      if (/\{(date|time|code|file)\}/i.test(ta.value)) {
        ta.value = injectPromptVars(ta.value);
        ta.dispatchEvent(new Event('input', { bubbles: true }));
      }
    });
  }

  /* Markdown workbench */
  function openWorkbench(seed) {
    var w = $('aetherWorkbench');
    if (!w) {
      w = document.createElement('div');
      w.id = 'aetherWorkbench';
      w.className = 'aether-workbench';
      w.innerHTML =
        '<header><strong>Workbench</strong>' +
        '<span class="actions">' +
        '<button type="button" id="wbSave">Save .md</button>' +
        '<button type="button" id="wbClose">×</button></span></header>' +
        '<textarea id="wbEditor" spellcheck="false"></textarea>';
      document.body.appendChild(w);
      $('wbClose').onclick = function () { w.hidden = true; document.body.classList.remove('workbench-open'); };
      $('wbSave').onclick = function () {
        var blob = new Blob([$('wbEditor').value], { type: 'text/markdown' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'workbench-' + Date.now() + '.md';
        a.click();
      };
    }
    w.hidden = false;
    document.body.classList.add('workbench-open');
    if (seed) $('wbEditor').value = seed;
    else {
      var last = document.querySelector('.message-row.ai .markdown-content, .message-row.ai .message-bubble');
      $('wbEditor').value = last ? (last.innerText || '') : '';
    }
  }

  /* Cost panel */
  async function openCost() {
    var r = await fetch('/api/forge/cost', { credentials: 'same-origin', headers: headers() });
    var d = await r.json();
    var p = $('aetherCostPanel');
    if (!p) {
      p = document.createElement('div');
      p.id = 'aetherCostPanel';
      p.className = 'aether-cost-panel';
      document.body.appendChild(p);
    }
    p.hidden = false;
    var profiles = d.profiles || {};
    p.innerHTML = '<header><strong>Token / Cost</strong><button type="button" id="costX">×</button></header>' +
      '<div class="sum">Total ~' + (d.total_tokens || 0) + ' tok · $' + (d.total_cost_usd || 0) + '</div>' +
      Object.keys(profiles).map(function (k) {
        var x = profiles[k];
        return '<div class="row"><span>' + k + '</span><span>' + x.tokens + ' tok · $' + (x.cost_usd || 0).toFixed(4) + '</span></div>';
      }).join('') +
      '<p class="hint">Estimates only — local simulator</p>';
    $('costX').onclick = function () { p.hidden = true; };
  }

  /* Memory graph canvas */
  async function openGraph() {
    var r = await fetch('/api/forge/graph', { credentials: 'same-origin', headers: headers() });
    var d = await r.json();
    var g = $('aetherGraph');
    if (!g) {
      g = document.createElement('div');
      g.id = 'aetherGraph';
      g.className = 'aether-graph';
      g.innerHTML = '<header><strong>Memory Graph</strong><button type="button" id="graphX">×</button></header><canvas id="graphCanvas" width="640" height="400"></canvas>';
      document.body.appendChild(g);
      $('graphX').onclick = function () { g.hidden = true; };
    }
    g.hidden = false;
    var canvas = $('graphCanvas');
    var ctx = canvas.getContext('2d');
    ctx.fillStyle = '#0c0e12';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    var ents = (d.entities || []).slice(0, 24);
    var edges = d.edges || [];
    var nodes = {};
    var cx = canvas.width / 2, cy = canvas.height / 2, R = 140;
    ents.forEach(function (e, i) {
      var ang = (i / Math.max(ents.length, 1)) * Math.PI * 2;
      nodes[e.name] = { x: cx + Math.cos(ang) * R, y: cy + Math.sin(ang) * R, n: e.name, c: e.count };
    });
    ctx.strokeStyle = 'rgba(91,141,239,0.35)';
    edges.forEach(function (ed) {
      var a = nodes[ed.a], b = nodes[ed.b];
      if (!a || !b) return;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    });
    Object.keys(nodes).forEach(function (k) {
      var n = nodes[k];
      ctx.fillStyle = '#5b8def';
      ctx.beginPath();
      ctx.arc(n.x, n.y, 4 + Math.min(8, (n.c || 1) / 3), 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#c8d0dc';
      ctx.font = '11px sans-serif';
      ctx.fillText(k, n.x + 8, n.y + 4);
    });
    if (!ents.length) {
      ctx.fillStyle = '#a0a8b8';
      ctx.fillText('No entities yet — chat to populate', 20, 30);
    }
  }

  /* Diagnostics */
  async function runDiagnostics() {
    toast('Running diagnostics…', 'info');
    var r = await fetch('/api/forge/diagnostics', { credentials: 'same-origin', headers: headers() });
    var d = await r.json();
    var lines = (d.checks || []).map(function (c) {
      return (c.ok ? '✓' : '✗') + ' ' + c.name + (c.error ? ' — ' + c.error : '');
    });
    alert('Diagnostics ' + d.passed + '/' + d.total + ' in ' + d.latency_ms + 'ms\n\n' + lines.join('\n'));
  }

  /* Math helper on selection */
  async function solveSelection() {
    var sel = (window.getSelection && window.getSelection().toString()) || '';
    if (!sel) {
      var ta = $('message');
      sel = ta ? ta.value : '';
    }
    if (!sel) return toast('Select or type an expression', 'info');
    var r = await fetch('/api/forge/math', {
      method: 'POST', credentials: 'same-origin', headers: headers(),
      body: JSON.stringify({ expression: sel.slice(0, 500) })
    });
    var d = await r.json();
    if (d.ok) toast((d.mode || 'result') + ': ' + (d.result || d.simplified), 'success');
    else toast(d.error || 'Math failed', 'error');
  }

  /* Ingest graph from last AI message periodically */
  async function softGraphIngest() {
    var last = document.querySelector('.message-row.ai .markdown-content, .message-row.ai .message-bubble');
    if (!last) return;
    var text = (last.innerText || '').slice(0, 4000);
    if (text.length < 40) return;
    try {
      await fetch('/api/forge/graph/ingest', {
        method: 'POST', credentials: 'same-origin', headers: headers(),
        body: JSON.stringify({ text: text })
      });
    } catch (e) {}
  }

  /* Cost record helper for sends */
  function hookCost() {
    var orig = window.sendMessage;
    if (typeof orig !== 'function' || orig.__forgeCost) return;
    var wrapped = function () {
      var ta = $('message');
      var prompt = ta ? ta.value : '';
      var profile = 'auto';
      try { profile = localStorage.getItem('vision_routing_profile') || 'auto'; } catch (e) {}
      var p = orig.apply(this, arguments);
      try {
        fetch('/api/forge/cost/record', {
          method: 'POST', credentials: 'same-origin', headers: headers(),
          body: JSON.stringify({
            thread_id: window.currentChatId || 'local',
            profile: profile,
            prompt: prompt,
            completion: '',
            cpu_ms: 0
          })
        }).catch(function () {});
        setTimeout(softGraphIngest, 2500);
      } catch (e) {}
      return p;
    };
    wrapped.__forgeCost = true;
    window.sendMessage = wrapped;
  }

  function ensureBtns() {
    var host = document.querySelector('.header-actions, .top-bar, .chat-header');
    if (!host) return;
    function add(id, title, label, fn) {
      if ($(id)) return;
      var b = document.createElement('button');
      b.id = id; b.type = 'button'; b.className = 'icon-btn header-btn';
      b.title = title; b.textContent = label; b.onclick = fn;
      host.appendChild(b);
    }
    add('forgeWbBtn', 'Markdown workbench', 'WB', function () { openWorkbench(); });
    add('forgeCostBtn', 'Token cost tracker', '$', openCost);
    add('forgeGraphBtn', 'Memory graph', 'Graph', openGraph);
    add('forgeDiagBtn', 'Diagnostics', 'Diag', runDiagnostics);
    add('forgeMathBtn', 'Sympy math solve', '∑', solveSelection);
  }

  function init() {
    ensureBtns();
    watchComposerVars();
    hookCost();
    document.addEventListener('keydown', function (e) {
      if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return;
      var k = e.key.toLowerCase();
      if (k === 'w') { e.preventDefault(); openWorkbench(); }
      if (k === 'g') { e.preventDefault(); openGraph(); }
      if (k === 'm') { e.preventDefault(); solveSelection(); }
    }, true);
    window.AetherForge = {
      openWorkbench: openWorkbench,
      openCost: openCost,
      openGraph: openGraph,
      runDiagnostics: runDiagnostics,
      solveSelection: solveSelection,
      injectPromptVars: injectPromptVars
    };
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window, document);
