
/* Avatar gender preference */
function getUserAvatarGender() {
  try { return localStorage.getItem('vision_avatar_gender') || 'neutral'; } catch (e) { return 'neutral'; }
}
function setUserAvatarGender(g) {
  g = (g === 'male' || g === 'female') ? g : 'neutral';
  try { localStorage.setItem('vision_avatar_gender', g); } catch (e) {}
  document.querySelectorAll('.avatar-gender-bar button').forEach(function(b) {
    b.classList.toggle('active', b.getAttribute('data-gender') === g);
  });
  document.querySelectorAll('.msg-avatar.user, .user-avatar, #profileButton .user-avatar').forEach(function(el) {
    el.classList.remove('male', 'female', 'neutral');
    el.classList.add(g);
    el.setAttribute('data-gender', g);
  });
  if (typeof showToast === 'function') {
    try { showToast('Avatar: ' + g, 'info', 1200); } catch (e) {}
  }
}
function avatarEmoji(role) {
  /* Visuals come from CSS ::after — keep DOM empty for cleaner 3D orb */
  return '';
}
window.getUserAvatarGender = getUserAvatarGender;
window.setUserAvatarGender = setUserAvatarGender;


function visionImageToolbar(img) {
  const src = (img && (img.url || img.image_url || (img.image_data ? ("data:image/png;base64," + img.image_data) : ""))) || "";
  let h = "";
  if (src) {
    h += '<a class="img-act" href="' + src + '" download="vision-image.png" target="_blank" rel="noopener">Download</a>';
    h += '<a class="img-act" href="' + src + '" target="_blank" rel="noopener">Full</a>';
  }
  if (img && img.svg_data) {
    h += '<a class="img-act" href="data:image/svg+xml;base64,' + img.svg_data + '" download="vision-graph.svg">SVG</a>';
  }
  return h ? ('<div class="ai-image-actions">' + h + '</div>') : "";
}


function visionSvgDownloadBtn(img) {
  if (!img || !img.svg_data) return '';
  try {
    const href = 'data:image/svg+xml;base64,' + img.svg_data;
    return '<a class="img-act" href="' + href + '" download="vision-graph.svg" title="Download SVG">📄 SVG</a>';
  } catch (e) { return ''; }
}


/* Sidebar boot: clear stale overlay once. Resize handled ONLY by visionSidebarController. */
(function visionUiBoot(){
  function clearDimOnce() {
    try {
      if (typeof isDrawerViewport === 'function' ? !isDrawerViewport() : window.matchMedia('(min-width: 901px)').matches) {
        var ov = document.getElementById('sidebar-overlay');
        if (ov) { ov.classList.remove('active'); ov.style.display = 'none'; ov.style.pointerEvents = 'none'; }
        document.body.classList.remove('sidebar-open');
        var sb = document.getElementById('sidebar');
        if (sb) sb.classList.remove('open-mobile');
      }
    } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', clearDimOnce);
  else clearDimOnce();
})();


// ============================================================
// VISION AI v4.7.6 - INDEX LOGIC (Production Ready)
// ============================================================

// ============================================================
// 🌙 THEME SYNC
// ============================================================
function applyTheme(theme) {
    const root = document.documentElement;
    let stored = theme || localStorage.getItem('vision_ai_theme') || 'dark';
    let resolved = stored;
    if (resolved === 'system') {
        resolved = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }
    if (resolved !== 'light' && resolved !== 'dark') resolved = 'dark';
    try { localStorage.setItem('vision_ai_theme', stored === 'system' ? 'system' : resolved); } catch (e) {}
    root.setAttribute('data-theme', resolved);
    if (document.body) document.body.setAttribute('data-theme', resolved);
    root.style.colorScheme = resolved === 'light' ? 'light' : 'dark';
    try { localStorage.setItem('vision_ai_theme_resolved', resolved); } catch (e) {}
    // Re-apply preset so --color-accent tracks theme sheets
    try {
      var preset = localStorage.getItem('vision_theme_preset') || root.getAttribute('data-theme-preset') || 'humanly';
      if (typeof applyThemePreset === 'function' && theme !== '__skip_preset__') {
        /* only update mode above; accent from CSS */
        var cs = getComputedStyle(root);
        var acc = cs.getPropertyValue('--accent').trim();
        if (acc) root.style.setProperty('--color-accent', acc);
      }
    } catch (e2) {}
    if (typeof updateThemeIcon === 'function') updateThemeIcon(resolved);
    if (typeof syncThemePickerUI === 'function') {
      try { syncThemePickerUI(); } catch (e3) {}
    }
}

// ============================================================
// AUTHENTICATION & TOKEN MANAGEMENT
// ============================================================

function getClientId() {
    try {
        var id = localStorage.getItem("vision_ai_client_id");
        if (id && id.length >= 8) return id;
        id = (typeof crypto !== "undefined" && crypto.randomUUID)
            ? crypto.randomUUID()
            : ("c" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10));
        localStorage.setItem("vision_ai_client_id", id);
        return id;
    } catch (e) {
        return "anon";
    }
}

function getAccessToken() {
    if (window.VisionAuth && typeof window.VisionAuth.getAccessToken === 'function') {
        return window.VisionAuth.getAccessToken();
    }
    return localStorage.getItem('vision_ai_access_token')
        || localStorage.getItem('vision_ai_token')
        || localStorage.getItem('access_token')
        || '';
}

function getRefreshToken() { 
    return localStorage.getItem('vision_ai_refresh_token'); 
}

function setTokens(access, refresh) {
    localStorage.setItem('vision_ai_access_token', access);
    if (refresh) localStorage.setItem('vision_ai_refresh_token', refresh);
}

function clearTokens() {
    try {
        localStorage.removeItem('vision_ai_access_token');
        localStorage.removeItem('vision_ai_access');
        localStorage.removeItem('vision_ai_refresh_token');
        localStorage.removeItem('vision_ai_refresh');
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('vision_ai_user');
        localStorage.removeItem('vision_ai_plan');
        localStorage.removeItem('vision_ai_is_guest');
        sessionStorage.removeItem('vision_auth_redirecting');
    } catch (e) {}
}

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    try {
        const res = await fetch('/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        if (res.ok) {
            const data = await res.json();
            setTokens(data.access_token, data.refresh_token);
            return true;
        }
    } catch (e) {
        console.error('Token refresh failed:', e);
    }
    return false;
}

function getUserKeyHeaders() {
    try {
        const raw = localStorage.getItem('vision_ai_user_keys');
        if (!raw) return {};
        const k = JSON.parse(raw);
        if (!k || !k.override) return {};
        const h = { 'X-Vision-Key-Override': '1' };
        if (k.GOOGLE_API_KEY) h['X-Vision-Key-Google'] = k.GOOGLE_API_KEY;
        if (k.GROQ_API_KEY) h['X-Vision-Key-Groq'] = k.GROQ_API_KEY;
        if (k.DEEPSEEK_API_KEY) h['X-Vision-Key-Deepseek'] = k.DEEPSEEK_API_KEY;
        if (k.OPENROUTER_API_KEY) h['X-Vision-Key-Openrouter'] = k.OPENROUTER_API_KEY;
        if (k.OPENAI_COMPAT_BASE) h['X-Vision-Key-Compat-Base'] = k.OPENAI_COMPAT_BASE;
        if (k.OPENAI_COMPAT_KEY) h['X-Vision-Key-Compat-Key'] = k.OPENAI_COMPAT_KEY;
        if (k.OPENAI_COMPAT_MODEL) h['X-Vision-Key-Compat-Model'] = k.OPENAI_COMPAT_MODEL;
        return h;
    } catch (e) { return {}; }
}

async function authenticatedFetch(url, options = {}) {
    let token = getAccessToken();
    const headers = { 
        ...options.headers, 
        ...getUserKeyHeaders(),
        'X-Vision-Client-Id': getClientId(),
        'Authorization': `Bearer ${token}` 
    };
    let res = await fetch(url, { ...options, headers });
    
    if (res.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            headers['Authorization'] = `Bearer ${getAccessToken()}`;
            res = await fetch(url, { ...options, headers });
        } else {
            // Prefer silent guest recovery over hard redirect (redirect causes page blink)
            const recovered = await ensureGuestSession();
            if (recovered) {
                headers['Authorization'] = `Bearer ${getAccessToken()}`;
                res = await fetch(url, { ...options, headers });
            } else if (typeof showToast === 'function') {
                showToast('Session expired. Use Login when you want a full account.', 'info', 2500);
            }
        }
    }
    return res;
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info', duration = 3000) {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        container.setAttribute('aria-live', 'polite');
        document.body.appendChild(container);
    }
    // Keep toasts inside viewport (bottom-right), never full-width strip
    container.style.cssText = 'position:fixed;bottom:max(16px,env(safe-area-inset-bottom));right:max(12px,env(safe-area-inset-right));z-index:99999;display:flex;flex-direction:column;gap:8px;max-width:min(360px,calc(100vw - 24px));width:auto;pointer-events:none;';

    const toast = document.createElement('div');
    toast.className = 'toast ' + (type || 'info');
    const icons = { error: '⚠️', success: '✅', info: 'ℹ️' };
    const safe = (typeof escapeHtml === 'function') ? escapeHtml(String(message)) : String(message).replace(/</g,'&lt;');
    toast.innerHTML = '<span aria-hidden="true">' + (icons[type] || 'ℹ️') + '</span><span>' + safe + '</span>';
    toast.style.cssText = 'pointer-events:auto;padding:12px 16px;border-radius:10px;background:var(--bg-secondary,#1a2e2a);border:1px solid var(--border-color,rgba(45,212,191,.25));box-shadow:0 8px 24px rgba(0,0,0,.35);display:flex;align-items:center;gap:10px;font-size:14px;color:var(--text-main,#e8f5f0);';
    if (type === 'error') toast.style.borderLeft = '4px solid #ef4444';
    if (type === 'success') toast.style.borderLeft = '4px solid #22c55e';
    if (type === 'info') toast.style.borderLeft = '4px solid #00C6FF';
    container.appendChild(toast);
    const ms = Math.max(800, Number(duration) || 3000);
    setTimeout(function () {
        try {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity .25s';
            setTimeout(function () { toast.remove(); }, 280);
        } catch (e) {}
    }, ms);
}

// Add toast animations if not already in CSS
if (!document.getElementById('toastStyles')) {
    const style = document.createElement('style');
    style.id = 'toastStyles';
    style.textContent = `
        @keyframes toastIn {
            from { opacity: 0; transform: translateY(20px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes toastOut {
            from { opacity: 1; transform: translateY(0) scale(1); }
            to { opacity: 0; transform: translateY(20px) scale(0.95); }
        }
    `;
    document.head.appendChild(style);
}

// ============================================================
// SIDEBAR LOGIC
// ============================================================

/** Single source of truth: drawer mode ≤900px, desktop layout ≥901px (must match CSS). */
window.VA_SIDEBAR_DRAWER_MQ = '(max-width: 900px)';
window.VA_SIDEBAR_DESKTOP_MQ = '(min-width: 901px)';
function isDrawerViewport() {
    try { return window.matchMedia(window.VA_SIDEBAR_DRAWER_MQ).matches; } catch (e) { return window.innerWidth <= 900; }
}
function isDesktopViewport() {
    try { return window.matchMedia(window.VA_SIDEBAR_DESKTOP_MQ).matches; } catch (e) { return window.innerWidth > 900; }
}
function isMobileViewport() { return isDrawerViewport(); }

/* Sidebar mutations: visionSidebarController only (see end of file). */
window.toggleSidebar = function () {
    if (window.__vaSidebar && window.__vaSidebar.toggle) return window.__vaSidebar.toggle();
    console.warn("[sidebar] controller not ready");
};
window.openSidebar = function () {
    if (window.__vaSidebar && window.__vaSidebar.open) return window.__vaSidebar.open();
};
window.closeSidebar = function () {
    if (window.__vaSidebar && window.__vaSidebar.close) return window.__vaSidebar.close();
};
window.closeMobileSidebar = function () {
    if (window.__vaSidebar && window.__vaSidebar.close) return window.__vaSidebar.close();
}

window.forceOpenSearch = function() {
    const sidebar = document.getElementById('sidebar');
    const searchBar = document.getElementById('search-bar');
    const isMobile = isMobileViewport();

    if (searchBar && !searchBar.classList.contains('hidden')) {
        searchBar.classList.add('hidden');
        return;
    }

    if (isMobile) {
        if (typeof window.openSidebar === 'function') window.openSidebar();
        else if (sidebar && !sidebar.classList.contains('open-mobile')) {
            sidebar.classList.add('open-mobile');
            if (typeof window.reconcileSidebarLayout === 'function') window.reconcileSidebarLayout();
        }
    } else {
        if (sidebar.classList.contains('rail-mode')) {
            sidebar.classList.remove('rail-mode');
            const toolbar = document.getElementById('collapsedToolbar');
            if (toolbar) toolbar.classList.remove('active');
        }
    }
    setTimeout(() => {
        if (searchBar) {
            searchBar.classList.remove('hidden');
            const searchInput = document.getElementById('history-search');
            if (searchInput) searchInput.focus();
        }
    }, 300);
}

// ============================================================
// CHAT HISTORY
// ============================================================
function _historyKey() {
    try {
        const u = JSON.parse(localStorage.getItem('vision_ai_user') || '{}');
        const name = (u && u.username) ? String(u.username) : 'guest';
        return 'vision_ai_history_v2_' + name.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 48);
    } catch (e) {
        return 'vision_ai_history_v2_guest';
    }
}
function _safeLoadHistory() {
    try {
        let raw = localStorage.getItem(_historyKey());
        // migrate legacy shared key once
        if (!raw) {
            const legacy = localStorage.getItem('vision_ai_history_v2');
            if (legacy) {
                raw = legacy;
                try { localStorage.setItem(_historyKey(), legacy); } catch (_) {}
            }
        }
        const data = JSON.parse(raw || '[]');
        return Array.isArray(data) ? data : [];
    } catch (e) {
        console.warn('history parse failed', e);
        return [];
    }
}
function reloadHistoryForUser() {
    chatHistory = _safeLoadHistory();
    if (!chatHistory.length) {
        // keep empty — startNewChat will fill when needed
    }
    try { renderHistory(); } catch (_) {}
}
let chatHistory = _safeLoadHistory();

let currentChatId = null;
let isEditMode = false;

function renderHistory() {
    const list = document.getElementById('historyList');
    if (!list) return;
    list.innerHTML = '';
    
    const groups = {};
    const now = new Date();
    chatHistory.forEach(item => {
        const date = new Date(item.timestamp);
        let key = 'Older';
        if (date.toDateString() === now.toDateString()) key = 'Today';
        else if (date.toDateString() === new Date(now - 86400000).toDateString()) key = 'Yesterday';
        else if (now - date < 604800000) key = '7 Days';
        if (!groups[key]) groups[key] = [];
        groups[key].push(item);
    });

    const order = ['Today', 'Yesterday', '7 Days', 'Older'];
    order.forEach(group => {
        if (!groups[group]) return;
        const section = document.createElement('div');
        section.innerHTML = `<div class="history-section-title">${group}</div>`;
        groups[group].forEach(item => {
            const wrapper = document.createElement('div');
            wrapper.className = `chat-item-wrapper ${item.id === currentChatId ? 'active' : ''}`;
            const titleSpan = document.createElement('span');
            titleSpan.className = 'chat-title';
            titleSpan.textContent = item.title || 'New Chat';
            titleSpan.onclick = () => loadChat(item.id);
            const menuBtn = document.createElement('button');
            menuBtn.className = 'chat-item-options';
            menuBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>';
            menuBtn.onclick = (e) => {
                e.stopPropagation();
                toggleChatMenu(menuBtn);
            };
            const menu = document.createElement('div');
            menu.className = 'chat-action-menu';
            menu.innerHTML = `
                <button onclick="renameChat('${item.id}')">✏️ Rename</button>
                <button onclick="deleteChat('${item.id}')" class="delete-btn">🗑️ Delete</button>
            `;
            wrapper.appendChild(titleSpan);
            wrapper.appendChild(menuBtn);
            wrapper.appendChild(menu);
            section.appendChild(wrapper);
        });
        list.appendChild(section);
    });
}

function toggleChatMenu(btn) {
    const menu = btn.nextElementSibling;
    document.querySelectorAll('.chat-action-menu.show').forEach(el => {
        if (el !== menu) el.classList.remove('show');
    });
    if (menu) menu.classList.toggle('show');
}

function renameChat(id) {
    const chat = chatHistory.find(c => c.id === id);
    if (!chat) return;
    const newName = prompt("Rename chat:", chat.title);
    if (newName && newName.trim()) {
        chat.title = newName.trim();
        saveHistory();
        renderHistory();
        if (id === currentChatId) {
            const titleEl = document.getElementById('chatTitle');
            if (titleEl) titleEl.textContent = chat.title;
        }
    }
}

function deleteChat(id) {
    if (!confirm("Delete this chat?")) return;
    const index = chatHistory.findIndex(c => c.id === id);
    if (index !== -1) {
        chatHistory.splice(index, 1);
        saveHistory();
        if (id === currentChatId) startNewChat();
        else renderHistory();
    }
}

function startNewChat() {
    currentChatId = Date.now().toString();
    chatHistory.unshift({ id: currentChatId, title: 'New Chat', timestamp: Date.now(), messages: [] });
    if (chatHistory.length > 80) chatHistory = chatHistory.slice(0, 80);
    saveHistory();
    renderHistory();
    const output = ensureChatOutput();
    if (output) output.innerHTML = '';
    const titleEl = document.getElementById('chatTitle');
    if (titleEl) titleEl.textContent = 'New Chat';
    const input = document.getElementById('message');
    if (input) { input.value = ''; input.style.height = 'auto'; try { input.focus(); } catch (_) {} }
    if (isMobileViewport() && typeof closeMobileSidebar === 'function') closeMobileSidebar();
}

function _slimMessages(messages) {
    return (messages || []).slice(-40).map(m => {
        const out = {
            role: m.role,
            text: (m.text || '').length > 12000 ? (m.text.slice(0, 12000) + '…') : (m.text || ''),
            modelUsed: m.modelUsed || null,
            filesCount: m.filesCount || 0,
            fileNames: m.fileNames || undefined,
        };
        // Never persist huge base64 images in localStorage (quota ~5MB)
        if (m.images && Array.isArray(m.images) && m.images.length) {
            out.imageCount = m.images.length;
            out.images = m.images.map(img => ({
                provider: img && img.provider,
                diagram_type: img && img.diagram_type,
                omitted: true,
            }));
        }
        return out;
    });
}

function _slimHistory(history) {
    return (history || []).slice(0, 80).map(c => ({
        id: c.id,
        title: (c.title || 'New Chat').slice(0, 80),
        timestamp: c.timestamp || Date.now(),
        messages: _slimMessages(c.messages),
    }));
}

function saveHistory() {
    try {
        const slim = _slimHistory(chatHistory);
        localStorage.setItem(_historyKey(), JSON.stringify(slim));
        // also mirror legacy key for older builds
        try { localStorage.setItem('vision_ai_history_v2', JSON.stringify(slim.slice(0, 20))); } catch (_) {}
    } catch (e) {
        console.warn('saveHistory quota', e);
        try {
            // Aggressive: keep 15 chats, short text — still remember daily chats
            const tiny = (chatHistory || []).slice(0, 15).map(c => ({
                id: c.id,
                title: (c.title || 'Chat').slice(0, 60),
                timestamp: c.timestamp || Date.now(),
                messages: (c.messages || []).slice(-20).map(m => ({
                    role: m.role,
                    text: (m.text || '').slice(0, 4000),
                    modelUsed: m.modelUsed || null,
                })),
            }));
            localStorage.setItem(_historyKey(), JSON.stringify(tiny));
            if (typeof showToast === 'function') {
                showToast('Storage almost full — old images removed from history (chat still works)', 'info', 5000);
            }
        } catch (e2) {
            try { localStorage.removeItem(_historyKey()); localStorage.removeItem('vision_ai_history_v2'); } catch (_) {}
            try { localStorage.removeItem('vision_ai_recent'); } catch (_) {}
            if (typeof showToast === 'function') {
                showToast('Browser storage cleared to recover chat. Continue messaging.', 'info', 6000);
            }
        }
    }
}

function loadChat(id) {
    const chat = chatHistory.find(c => c.id === id);
    if (!chat) return;
    currentChatId = id;
    const output = ensureChatOutput();
    if (!output) return;
    hideWelcomeEmpty();
    output.innerHTML = '';
    const titleEl = document.getElementById('chatTitle');
    if (titleEl) titleEl.textContent = chat.title;
    chat.messages.forEach(msg => {
        addMessage(msg.role, msg.text, msg.images || null, msg.modelUsed || null);
    });
    renderHistory();
    if (isMobileViewport()) closeMobileSidebar();
    output.querySelectorAll('pre code').forEach((block) => {
        if (window.hljs) hljs.highlightElement(block);
    });
}

// ============================================================
// CACHE MANAGEMENT
// ============================================================
async function clearAllCaches() {
    try {
        const res = await authenticatedFetch('/chat/clear-cache', { method: 'POST' });
        if (!res) {
            showToast('Please log in again', 'error');
            return;
        }
        let data = {};
        try { data = await res.json(); } catch (_) {}
        if (res.ok) {
            showToast(data.message || 'Caches cleared', 'success');
        } else {
            const detail = data.detail || data.message || ('HTTP ' + res.status);
            showToast('Failed to clear cache: ' + detail, 'error', 5000);
        }
    } catch (e) {
        showToast('Failed to clear cache: ' + e.message, 'error');
    }
}

// ============================================================
// CHAT FUNCTIONS (✅ UPDATED WITH BADGES)
// ============================================================
function addMessage(role, text, images = null, modelUsed = null, ragCount = 0, searchUsed = false, imageCount = 0, streamId = null) {
    const output = ensureChatOutput();
    if (!output) return;
    hideWelcomeEmpty();
    
    const row = document.createElement('div');
    row.className = `message-row ${role}`;
    const gender = getUserAvatarGender();
    const avClass = (role === 'user')
      ? ('msg-avatar user ' + gender)
      : 'msg-avatar ai';
    const avIcon = avatarEmoji(role);
    
    const streamAttr = streamId ? ` data-stream-id="${streamId}"` : '';
    let html = `<div class="${avClass}" title="${role}">${avIcon}</div><div class="message-bubble"${streamAttr} onclick="${role === 'user' ? 'editMessage(this)' : ''}">`;
    
    // 🟢 NEW: Render Badges for AI messages
    if (role === 'ai') {
        let badges = [];
        if (ragCount > 0) badges.push(`📄 ${ragCount} document${ragCount > 1 ? 's' : ''}`);
        if (searchUsed) badges.push('🌐 Web search');
        if (imageCount > 0) badges.push(`🖼️ ${imageCount} image${imageCount > 1 ? 's' : ''}`);
        if (badges.length > 0) {
            html += `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;">`;
            badges.forEach(b => {
                html += `<span style="background:rgba(0,198,255,0.1);color:#00C6FF;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;">${b}</span>`;
            });
            html += `</div>`;
        }
    }
    
    if (role === 'ai' && modelUsed) {
        const modelClass = 'model-' + String(modelUsed || 'auto').toLowerCase().replace(/[^a-z0-9]+/g, '-');
        html += `<span class="model-used ${modelClass}"><span class="model-dot"></span><span>${escapeHtml(modelUsed)}</span></span>`;
    }
    
    if (role === 'ai' && typeof text === 'string') {
        let cleanHtml;
        // Soft-format + math normalization
        let src = text;
        src = src
            .replace(/```(?:math|latex|tex)\s*([\s\S]*?)```/gi, function (_, body) {
                return '\n$$\n' + String(body).trim() + '\n$$\n';
            })
            .replace(/\\begin\{equation\}([\s\S]*?)\\end\{equation\}/gi, '\n$$\n$1\n$$\n')
            .replace(/\\begin\{align\*?\}([\s\S]*?)\\end\{align\*?\}/gi, '\n$$\n$1\n$$\n');

        // Pre-render $$ and $ math with KaTeX so marked cannot break LaTeX
        const mathHolders = [];
        function stashMath(tex, display) {
            var html = '';
            try {
                if (window.katex && typeof katex.renderToString === 'function') {
                    html = katex.renderToString(tex, { displayMode: !!display, throwOnError: false, strict: 'ignore' });
                } else {
                    html = display
                        ? ('<div class="katex-fallback">$$' + escapeHtml(tex) + '$$</div>')
                        : ('<span class="katex-fallback">$' + escapeHtml(tex) + '$</span>');
                }
            } catch (e) {
                html = '<code>' + escapeHtml(tex) + '</code>';
            }
            var key = 'MATHHOLD' + mathHolders.length + 'X';
            mathHolders.push(html);
            return key;
        }
        src = src.replace(/\$\$([\s\S]+?)\$\$/g, function (_, tex) {
            return '\n\n' + stashMath(String(tex).trim(), true) + '\n\n';
        });
        src = src.replace(/(^|[^$])\$([^\n$]+?)\$(?!\$)/g, function (_, pre, tex) {
            return pre + stashMath(String(tex).trim(), false);
        });

        const looksPlain = !/(^|\n)#{1,3}\s|(^|\n)[-*]\s|(^|\n)\d+\.\s|```|MATHHOLD/.test(src);
        if (looksPlain && src.length > 600) {
            src = src
                .replace(/\[Music\]/gi, '\n\n*[Music]*\n\n')
                .replace(/([.!?])\s+(?=[A-Z])/g, '$1\n\n')
                .replace(/\n{3,}/g, '\n\n');
        }
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            try {
                if (typeof marked.setOptions === 'function') {
                    marked.setOptions({ breaks: true, gfm: true });
                }
                const parsedHtml = marked.parse(src);
                cleanHtml = window.DOMPurify ? DOMPurify.sanitize(parsedHtml) : parsedHtml;
            } catch (e) {
                console.error('Markdown parsing failed:', e);
                cleanHtml = escapeHtml(text).replace(/\n/g, '<br>');
            }
        } else {
            cleanHtml = escapeHtml(text).replace(/\n/g, '<br>');
        }
        // Restore KaTeX HTML after sanitize
        mathHolders.forEach(function (html, i) {
            var key = 'MATHHOLD' + i + 'X';
            cleanHtml = cleanHtml.split(key).join(html);
            cleanHtml = cleanHtml.replace(new RegExp('<p>\\s*' + key + '\\s*<\\/p>', 'g'), html);
        });
        const isLong = text.length > 1800;
        const hasRtl = /[\u0600-\u06FF]/.test(text) && ((text.match(/[\u0600-\u06FF]/g) || []).length > 20);
        const bodyClass = (isLong ? 'markdown-content msg-long-body' : 'markdown-content') + (hasRtl ? ' rtl' : '');
        // Force mobile-friendly download links (?dl=1 + data-force-download)
        cleanHtml = cleanHtml.replace(
            /href="([^"]*\/upload\/downloads\/[^"]+)"/g,
            function (_, href) {
                var h = href;
                if (h.indexOf('dl=') === -1) {
                    h += (h.indexOf('?') >= 0 ? '&' : '?') + 'dl=1';
                }
                return 'href="' + h + '" download target="_blank" rel="noopener" class="dl-file-link" data-force-download="1"';
            }
        );
        html += `<div class="${bodyClass}"${hasRtl ? ' dir="rtl" lang="ur"' : ''}>${cleanHtml}</div>`;
        html += `<div class="msg-actions">
            <button type="button" class="msg-action-btn" onclick="copyMessageText(this)" title="Copy" aria-label="Copy message">Copy</button>
            <button type="button" class="msg-action-btn speak-btn" onclick="event.stopPropagation();speakMessage(this)" title="Read aloud" aria-label="Speak message">Speak</button>
            <button type="button" class="msg-action-btn" onclick="event.stopPropagation();stopSpeaking()" title="Stop voice" aria-label="Stop speaking">Stop</button>
            <button type="button" class="msg-action-btn" onclick="zoomMessage(this, 1.1)" title="Zoom in">🔍+</button>
            <button type="button" class="msg-action-btn" onclick="zoomMessage(this, 0.9)" title="Zoom out">🔍−</button>
            <button type="button" class="msg-action-btn" onclick="focusMessageFullscreen(this)" title="Fullscreen">⛶ Full</button>
        </div>`;
    } else {
        html += `<div style="white-space: pre-wrap;">${escapeHtml(text)}</div>`;
    }
    
    const hasImages = images && Array.isArray(images) && images.length > 0;
    if (hasImages) {
        // Single image → large hero; multi → responsive grid (no more 150px thumbs)
        const cols = images.length === 1
            ? 'minmax(280px, 1fr)'
            : 'repeat(auto-fill, minmax(240px, 1fr))';
        html += `<div class="ai-image-grid" style="display:grid;grid-template-columns:${cols};gap:14px;margin-top:14px;width:100%;"></div>`;
    }
    html += '</div>';
    row.innerHTML = html;
    if (typeof bindDownloadLinks === 'function') {
        bindDownloadLinks(row);
    } else {
        row.querySelectorAll('a[href*="/upload/downloads/"]').forEach(function (a) {
            a.setAttribute('download', '');
            a.classList.add('dl-file-link');
            a.setAttribute('data-force-download', '1');
            a.addEventListener('click', function (ev) {
                const href = a.getAttribute('href');
                if (!href) return;
                ev.preventDefault();
                forceMobileDownload(href, a.getAttribute('download') || '').catch(function () {
                    window.open(href, '_blank');
                });
            });
        });
    }

    if (hasImages) {
        const grid = row.querySelector('.ai-image-grid');
        const single = images.length === 1;
        images.forEach(img => {
            // svg export button available via visionSvgDownloadBtn(img)
            const raw = (img && typeof img.data === 'string') ? img.data : '';
            const isDataUri = /^data:image\/(png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=]+$/.test(raw);
            const isBareBase64 = /^[A-Za-z0-9+/=]+$/.test(raw) && raw.length > 0;
            const src = isDataUri ? raw : (isBareBase64 ? `data:image/png;base64,${raw}` : '');
            if (!src) return;
            const wrap = document.createElement('div');
            wrap.className = 'ai-image-wrap';
            wrap.style.cssText = single ? 'width:100%;max-width:720px;' : 'width:100%;';
            const imgEl = document.createElement('img');
            imgEl.src = src;
            imgEl.alt = (img && img.caption) || 'Generated image';
            imgEl.loading = 'lazy';
            imgEl.style.cssText = single
                ? 'width:100%;max-height:640px;height:auto;object-fit:contain;border-radius:12px;cursor:zoom-in;border:1px solid rgba(255,255,255,0.12);background:rgba(0,0,0,0.25);display:block;'
                : 'width:100%;max-height:420px;height:auto;object-fit:contain;border-radius:10px;cursor:zoom-in;border:1px solid rgba(255,255,255,0.12);background:rgba(0,0,0,0.25);display:block;';
            imgEl.addEventListener('click', () => openImageLightbox(src, imgEl.alt));
            wrap.appendChild(imgEl);
            const bar = document.createElement('div');
            bar.className = 'ai-image-actions';
            bar.innerHTML = `
              <button type="button" class="img-act" data-act="download" title="Download">⬇️ Download</button>
              <button type="button" class="img-act" data-act="open" title="Open full size">⛶ Full</button>
              <button type="button" class="img-act" data-act="zoom" title="Zoom preview">🔍 Zoom</button>
            `;
            bar.querySelector('[data-act="download"]').onclick = () => downloadDataUrl(src, 'vision-ai-image.png');
            bar.querySelector('[data-act="open"]').onclick = () => window.open(src, '_blank');
            bar.querySelector('[data-act="zoom"]').onclick = () => openImageLightbox(src, imgEl.alt);
            wrap.appendChild(bar);
            grid.appendChild(wrap);
        });
    }
    
    output.appendChild(row);
    output.scrollTop = output.scrollHeight;
    
    row.querySelectorAll('pre code').forEach((block) => {
        if (window.hljs) hljs.highlightElement(block);
    });

    // Render LaTeX math / physics formulas (KaTeX)
    if (window.renderMathInElement) {
        try {
            renderMathInElement(row, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                throwOnError: false,
                ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
            });
        } catch (e) {
            console.warn('KaTeX render failed:', e);
        }
    }
}

function editMessage(element) {
    const textDiv = element.querySelector('.markdown-content') || element.querySelector('div[style*="white-space"]');
    const currentText = textDiv ? textDiv.textContent : '';
    const inputField = document.getElementById('message');
    if (!inputField) return;
    
    inputField.value = currentText;
    inputField.focus();
    inputField.setSelectionRange(currentText.length, currentText.length);
    document.querySelectorAll('.message-bubble.editing').forEach(el => el.classList.remove('editing'));
    element.classList.add('editing');
    window.editingElement = element;
    window.editingRow = element.closest('.message-row');
    isEditMode = true;
    const editActions = document.getElementById('editActions');
    if (editActions) editActions.classList.add('active');
}

function cancelEdit() {
    window.editingElement = null;
    window.editingRow = null;
    document.querySelectorAll('.message-bubble.editing').forEach(el => el.classList.remove('editing'));
    const inputField = document.getElementById('message');
    if (inputField) inputField.value = '';
    const editActions = document.getElementById('editActions');
    if (editActions) editActions.classList.remove('active');
    isEditMode = false;
}

function sendEdit() {
    if (!window.editingElement) { 
        cancelEdit(); 
        return; 
    }
    sendMessage();
}

// ============================================================
// DYNAMIC LOADING / TYPING INDICATOR
// ============================================================
const LOADING_STATUSES = [
    { title: 'Receiving your request…', sub: 'Files, links, and text are being prepared' },
    { title: 'Processing documents…', sub: 'PDF / image OCR can take up to 1–2 minutes' },
    { title: 'Fetching media / search…', sub: 'YouTube and web data if needed' },
    { title: 'Running AI model…', sub: 'Generating a detailed answer' },
    { title: 'Finishing response…', sub: 'Formatting and diagrams' },
];

let loadingStatusIndex = 0;
let loadingStatusInterval = null;

function showLoading() {
    const output = ensureChatOutput();
    if (!output) return;
    hideWelcomeEmpty();

    loadingStatusIndex = 0;
    if (loadingStatusInterval) {
        clearInterval(loadingStatusInterval);
        loadingStatusInterval = null;
    }

    removeLoading();

    const row = document.createElement('div');
    row.className = 'message-row ai';
    row.id = 'loadingRow';
    row.innerHTML = `
        <div class="message-bubble loading-bubble">
            <div class="typing-indicator" role="status" aria-live="polite" aria-label="Working">
                <span class="loader-label" id="loadingStatus">Working</span>
                <span class="loader-dots" aria-hidden="true"><span></span><span></span><span></span></span>
            </div>
        </div>
    `;
    output.appendChild(row);
    output.scrollTop = output.scrollHeight;

    /* progress bar removed — sine-dot loader only */
    loadingStatusInterval = null; /* fixed label — dots only animate */
}


function updateLoadingStatus(msg) {
    /* Label stays "Working"; only three dots animate (sine). */
    const el = document.getElementById('loadingStatus');
    if (el) {
        el.textContent = 'Working';
        if (msg) el.setAttribute('title', String(msg));
    }
    if (loadingStatusInterval) {
        clearInterval(loadingStatusInterval);
        loadingStatusInterval = null;
    }
}

function removeLoading() {
    if (window._progressTimer) { clearInterval(window._progressTimer); window._progressTimer = null; }
    const bar = document.getElementById('loadingProgress');
    if (bar) bar.style.width = '100%';

    const el = document.getElementById('loadingRow') || document.getElementById('loadingMsg');
    if (el) el.remove();
    if (loadingStatusInterval) {
        clearInterval(loadingStatusInterval);
        loadingStatusInterval = null;
    }
}


function stopGeneration() {
    window._userStopped = true;
    try {
        if (window._activeChatAbort) {
            window._activeChatAbort.abort();
            window._activeChatAbort = null;
        }
    } catch (_) {}
    removeLoading();
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) sendBtn.disabled = false;
    const stopBtn = document.getElementById('stopBtn');
    if (stopBtn) stopBtn.hidden = true;
    // Restore last draft so user can edit
    const input = document.getElementById('message');
    if (input && window._lastDraftMessage) {
        input.value = window._lastDraftMessage;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
    }
    showToast('Stopped — edit your message and send again', 'info', 3500);
}
window.stopGeneration = stopGeneration;

async function sendMessage() {
    const msgInput = document.getElementById('message');
    if (!msgInput) return;
    const msg = msgInput.value.trim();
    const fileInput = document.getElementById('fileInput');
    const sendBtn = document.getElementById('sendBtn');
    
    const filesToUpload = Array.from(fileInput ? fileInput.files : []); 

    if (!msg && filesToUpload.length === 0) return;
    window._lastDraftMessage = msg;

    const wasEditing = isEditMode;
    if (wasEditing) cancelEdit();
    if (!currentChatId) startNewChat();
    const chat = chatHistory.find(c => c.id === currentChatId);
    if (!chat) return;

    if (wasEditing && window.editingElement) {
        const rowToRemove = window.editingRow;
        const oldText = window.editingElement.querySelector('.markdown-content')?.textContent || '';
        const msgIndex = chat.messages.findIndex(m => m.role === 'user' && m.text === oldText);
        if (msgIndex !== -1) chat.messages.splice(msgIndex, 1);
        if (rowToRemove) rowToRemove.remove();
        window.editingElement = null;
        window.editingRow = null;
    }

    let userMessage = msg;
    if (filesToUpload.length > 0) {
        const fileList = filesToUpload
            .map(f => `📄 ${escapeHtml(f.name)} (${(f.size/1024).toFixed(1)}KB)`)
            .join('\n');
        userMessage = `Uploading Files:\n${fileList}\n\nMessage: ${msg}`;
    }
    (function(){ var el=document.getElementById('message'); if(el){ el.value=''; el.style.height='auto'; } })();
    addMessage('user', userMessage);
    
    chat.messages.push({ 
        role: 'user', 
        text: userMessage, 
        filesCount: filesToUpload.length, 
        fileNames: filesToUpload.map(f => f.name) 
    });
    
    if (chat.title === 'New Chat') {
        chat.title = msg.substring(0, 40) + (msg.length > 40 ? '...' : '');
    }
    saveHistory();
    renderHistory();
    const titleEl = document.getElementById('chatTitle');
    if (titleEl) titleEl.textContent = chat.title;
    msgInput.value = '';
    if (fileInput) fileInput.value = ''; 
    renderFilePreview(); 
    if (sendBtn) sendBtn.disabled = true;
    const stopBtn = document.getElementById('stopBtn');
    if (stopBtn) { stopBtn.hidden = false; stopBtn.disabled = false; }
    const _msgInput = document.getElementById('message');
    if (_msgInput) { /* already captured text above */ }
    const _sendEarly = document.getElementById('sendBtn');
    if (_sendEarly) _sendEarly.disabled = true;
    showLoading();

    const formData = new FormData();
    formData.append('message', msg);
    // Short context so "what is this chat about" uses this thread
    try {
        const recent = (chat.messages || []).slice(-6).map(m => (m.role + ': ' + (m.text || '').slice(0, 200))).join('\n');
        if (recent) formData.append('history_hint', recent.slice(0, 1500));
    } catch (_) {}
    const modelSelector = document.getElementById('modelSelector');
    const modelVal = modelSelector ? modelSelector.value : (localStorage.getItem('vision_ai_model') || 'auto');
    if (modelSelector) localStorage.setItem('vision_ai_model', modelSelector.value);
    formData.append('model', modelVal === 'default' ? 'auto' : modelVal);
    formData.append('generate_images', 'true');
    const chatLang = localStorage.getItem('vision_ai_chat_lang') || 'auto';
    if (chatLang && chatLang !== 'auto') {
        formData.append('preferred_language', chatLang);
    }
    
    for (const file of filesToUpload) {
        formData.append('files', file); 
    }

    // Exam / document / YouTube / uploads need long client timeout (server budget up to 150s)
    const isHeavy = filesToUpload.length > 0 || /download|transcript|youtube\.com|youtu\.be|mp3|1080p|720p|\bpdf\b|\bsolve\b|question paper|mark scheme|past paper|this paper|this document|answer all|work through|exam\b/i.test(userMessage || '') || /\bpdf\b|\bsolve\b|question paper|mark scheme|past paper|this paper|this document|answer all|work through|exam\b/i.test(msg || '');
    const isImage = /\b(draw|image|picture|photo|generate|create|diagram|logo|illustration|photorealistic|architecture|mosque|masjid|building|graph|plot|chart|flowchart)\b/i.test(userMessage || '');
    try {
        updateLoadingStatus(isImage ? "Generating image (GPU may take 1–2 min)…" : (isHeavy ? "Working on document / long answer (may take 1–3 min)…" : "Contacting AI model..."));
        const controller = new AbortController();
        window._activeChatAbort = controller;
        const timeoutMs = isHeavy ? 300000 : (isImage ? 300000 : 90000);
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        let res;

        // Progressive stream for light text-only chats (faster perceived response)
        const canStream = !isHeavy && !isImage && filesToUpload.length === 0;
        if (canStream) {
            try {
                updateLoadingStatus("Streaming answer…");
                const sRes = await authenticatedFetch('/chat/stream', {
                    method: 'POST',
                    body: formData,
                    signal: controller.signal
                });
                if (sRes.ok && sRes.body) {
                    removeLoading();
                    const streamId = 'stream-' + Date.now();
                    addMessage('ai', '…', null, 'streaming', 0, false, 0, streamId);
                    let bubbleEl = document.querySelector('.message-bubble[data-stream-id="' + streamId + '"]') ||
                        document.querySelector('.message-row.ai:last-child .message-bubble');
                    let bubble = bubbleEl ? (bubbleEl.querySelector('.markdown-content') || bubbleEl) : null;
                    let acc = '';
                    let modelUsed = 'stream';
                    let streamRenderTimer = null;
                    function flushStreamRender() {
                        streamRenderTimer = null;
                        if (!bubble) return;
                        try {
                          var html = (typeof marked !== 'undefined') ? marked.parse(acc) : acc;
                          bubble.innerHTML = window.DOMPurify ? DOMPurify.sanitize(html) : html;
                          if (window.renderMathInElement) {
                            try { renderMathInElement(bubble, { throwOnError: false, delimiters: [{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}]}); } catch(e){}
                          }
                          if (typeof scrollChatToBottom === 'function') scrollChatToBottom(true);
                        } catch(e) {}
                    }

                    const reader = sRes.body.getReader();
                    const decoder = new TextDecoder();
                    let buf = '';
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;
                        buf += decoder.decode(value, { stream: true });
                        const parts = buf.split('\n');
                        buf = parts.pop() || '';
                        for (let i = 0; i < parts.length; i++) {
                            let line = parts[i].trim();
                            if (!line.startsWith('data:')) continue;
                            let payload = line.slice(5).trim();
                            if (payload === '[DONE]') continue;
                            try {
                                const ev = JSON.parse(payload);
                                if (ev.event === 'token' && ev.text) {
                                    acc += ev.text;
                                    if (bubble) bubble.classList.add('streaming-cursor');
                                    if (!streamRenderTimer) streamRenderTimer = setTimeout(flushStreamRender, 50);
                                } else if (ev.event === 'meta' || ev.event === 'done') {
                                    modelUsed = ev.model || ev.provider || modelUsed;
                                } else if (ev.event === 'error') {
                                    throw new Error(ev.message || 'stream error');
                                }
                            } catch (parseErr) {
                                if (parseErr.message && parseErr.message !== 'stream error' && !String(parseErr).includes('JSON')) {
                                    /* skip partial json */
                                } else if (parseErr.message === 'stream error' || (parseErr.message && parseErr.message.indexOf('stream') >= 0)) {
                                    throw parseErr;
                                }
                            }
                        }
                    }
                    clearTimeout(timeoutId);
                    window._activeChatAbort = null;
                    if (sendBtn) sendBtn.disabled = false;
                    if (stopBtn) stopBtn.hidden = true;
                    if (bubble) bubble.classList.remove('streaming-cursor');
                    if (acc) {
                        chat.messages.push({ role: 'ai', text: acc, modelUsed: modelUsed });
                        saveHistory();
                        if (modelUsed) { try { showToast('Model: ' + String(modelUsed).slice(0, 48), 'success', 1800); } catch (e) {} }
                        return;
                    }
                }
            } catch (streamErr) {
                console.warn('stream fallback to /chat/send', streamErr);
                updateLoadingStatus("Contacting AI model...");
            }
        }

        try {
            res = await authenticatedFetch('/chat/send', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            if (res && res.status === 405) {
                res = await authenticatedFetch('/api/chat/send', {
                    method: 'POST',
                    body: formData,
                    signal: controller.signal
                });
            }
        } catch (fetchErr) {
            // One retry on transient network / Railway cold start
            if (fetchErr && fetchErr.name !== 'AbortError') {
                updateLoadingStatus("Reconnecting…");
                await new Promise(r => setTimeout(r, 1000));
                res = await authenticatedFetch('/chat/send', {
                    method: 'POST',
                    body: formData,
                    signal: controller.signal
                });
            } else {
                throw fetchErr;
            }
        } finally {
            clearTimeout(timeoutId);
            window._activeChatAbort = null;
        }
        updateLoadingStatus("Generating response...");
        let data = {};
        try { data = await res.json(); } catch (e) { data = { detail: res.statusText || 'error' }; }
        removeLoading();
        if (res.status === 405) {
            if (typeof addMessage === 'function') addMessage('ai', '❌ Chat endpoint returned 405 Method Not Allowed. Please redeploy Vision AI v3.8.2 (POST /chat/send).');
            if (sendBtn) sendBtn.disabled = false;
            if (stopBtn) stopBtn.hidden = true;
            return;
        }

        if (sendBtn) sendBtn.disabled = false;
        if (stopBtn) stopBtn.hidden = true;
        if (res.ok) {
            // ✅ UPDATED: Pass badge data to addMessage
            addMessage(
                'ai', 
                data.answer, 
                data.images || null, /* images */ 
                data.model_used || null,
                data.rag_files_loaded || 0,
                data.search_performed || false,
                data.images_generated || 0
            );
            maybeHonestNoImage(message, data.images);
            chat.messages.push({ 
                role: 'ai', 
                text: data.answer, 
                images: data.images,
                modelUsed: data.model_used,
                imageCount: (data.images && data.images.length) || 0,
            });
            saveHistory();
            let _toastMsg = `Response from ${data.model_used} in ${data.response_time}s`;
            if ((data.rag_files_loaded || 0) > 0 || (data.context_length || 0) > 8000) {
                _toastMsg += ' · document context used';
            }
            if (data.quota_label) _toastMsg += ' · ' + data.quota_label;
            showToast(_toastMsg, 'success', 3200);
            try {
                var qb = document.getElementById('quotaBadge');
                if (qb && data.quota_label) {
                    qb.textContent = data.quota_label;
                    qb.hidden = false;
                }
            } catch (e) {}
        } else {
            var detail = data.detail || data.error || 'Unknown error';
            var detailMsg = (typeof detail === 'object' && detail)
                ? (detail.message || JSON.stringify(detail))
                : String(detail);
            var upgradeUrl = (typeof detail === 'object' && detail && detail.upgrade_url) || '';
            if (res.status === 401 || (typeof detail === 'object' && detail.code === 'GUEST_LIMIT')) {
                addMessage('ai',
                    '🔐 **Guest limit reached**\n\nYou used your free guest reply. **Sign in** to continue (free accounts get more messages).\n\n[Sign in / Create account](/login.html)'
                );
                showToast('Please sign in to continue', 'info', 5000);
                setTimeout(function () { window.location.href = upgradeUrl || '/login.html'; }, 1800);
            } else if (res.status === 402 || (typeof detail === 'object' && detail.code === 'FREE_LIMIT')) {
                addMessage('ai',
                    '💎 **Free plan limit reached**\n\nYou have used your free messages. Upgrade to **Student** or **Pro** for more capacity and advanced features.\n\n[Open Plans](/upgrade.html)'
                );
                showToast('Upgrade required for more messages', 'info', 5000);
                setTimeout(function () { window.location.href = upgradeUrl || '/upgrade.html'; }, 2200);
            } else {
                addMessage('ai', '❌ Error: ' + detailMsg);
                showToast(detailMsg, 'error');
            }
        }
    } catch (err) {
        removeLoading();
        if (sendBtn) sendBtn.disabled = false;
        const stopBtn2 = document.getElementById('stopBtn');
        if (stopBtn2) stopBtn2.hidden = true;
        if (err.name === 'AbortError') {
            // User stop vs timeout
            if (window._userStopped) {
                window._userStopped = false;
                addMessage('ai', '⏹ Stopped. Edit your message above and press Send to continue.');
                showToast('Generation stopped', 'info');
                return;
            }

            addMessage('ai', '❌ The request timed out. The AI model may be taking too long or the server may be unresponsive.');
            showToast(isImage ? 'Image timed out — wait for Colab warmup (GPU model loaded), keep Boost tab open, retry.' : 'Request timed out. Try again.', 'error', 6000);
        } else {
            const hint = (err.message || '').includes('Failed to fetch')
                ? ' Server may be waking up (Railway) or offline. Wait 10s and retry.'
                : '';
            addMessage('ai', '❌ Connection error: ' + err.message + hint);
            showToast('Connection error — retry in a few seconds.', 'error');
        }
    }
}


// ============================================================
// ProfileController — single authority for profile menu
// ============================================================
(function () {
  function dd() { return document.getElementById("profileDropdown"); }
  function btn() { return document.getElementById("profileButton"); }

  function placeDropdown() {
    var d = dd();
    var b = btn();
    if (!d || !b) return;
    var r = b.getBoundingClientRect();
    d.style.position = "fixed";
    d.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 220)) + "px";
    d.style.bottom = Math.max(8, window.innerHeight - r.top + 6) + "px";
    d.style.top = "auto";
    d.style.zIndex = "10050";
  }

  function open() {
    var d = dd();
    var b = btn();
    if (!d) return;
    placeDropdown();
    d.style.display = "block";
    d.setAttribute("aria-hidden", "false");
    if (b) b.setAttribute("aria-expanded", "true");
  }

  function close() {
    var d = dd();
    var b = btn();
    if (d) {
      d.style.display = "none";
      d.setAttribute("aria-hidden", "true");
    }
    if (b) b.setAttribute("aria-expanded", "false");
  }

  function isOpen() {
    var d = dd();
    return !!(d && d.style.display !== "none" && d.offsetParent !== null);
  }

  function toggle(ev) {
    if (ev) {
      ev.preventDefault();
      ev.stopPropagation();
    }
    if (isOpen()) close();
    else open();
  }

  function onDocClick(ev) {
    var d = dd();
    var b = btn();
    if (!d || !isOpen()) return;
    if (d.contains(ev.target) || (b && b.contains(ev.target))) return;
    close();
  }

  function onKey(ev) {
    if (ev.key === "Escape") close();
    if ((ev.key === "Enter" || ev.key === " ") && ev.target && ev.target.id === "profileButton") {
      ev.preventDefault();
      toggle(ev);
    }
  }

  function onFooterClick(ev) {
    var t = ev.target;
    if (!t) return;
    var action = t.getAttribute && t.getAttribute("data-action");
    if (!action && t.closest) {
      var el = t.closest("[data-action]");
      if (el) action = el.getAttribute("data-action");
    }
    if (action === "logout") {
      ev.preventDefault();
      close();
      if (window.performLogout) window.performLogout();
      return;
    }
    if (t.closest && t.closest("#profileButton")) {
      toggle(ev);
    }
  }

  function bind() {
    var footer = document.getElementById("accountArea");
    if (footer && !footer._profileBound) {
      footer.addEventListener("click", onFooterClick);
      footer._profileBound = true;
    }
    document.addEventListener("click", onDocClick);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", function () {
      if (isOpen()) placeDropdown();
    });
  }

  window.ProfileController = { open: open, close: close, toggle: toggle, isOpen: isOpen, bind: bind };
  window.toggleProfileDropdown = function (ev) { toggle(ev); };
  window.closeProfileDropdown = close;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
})();


// ============================================================
// 👤 USER PROFILE MANAGEMENT
// ============================================================
function renderUserProfile() {
    const footer = document.getElementById('accountArea');
    if (!footer) return;

    let userData = {};
    try { userData = JSON.parse(localStorage.getItem('vision_ai_user') || '{}'); } catch (e) {}
    const plan = localStorage.getItem('vision_ai_plan') || userData.plan || 'free';
    const hasToken = !!(window.VisionAuth && typeof VisionAuth.getAccessToken === 'function' && VisionAuth.getAccessToken())
        || !!(localStorage.getItem('vision_ai_access_token') || localStorage.getItem('vision_ai_token'));
    const isGuest = !!(userData.is_guest || userData.isGuest
        || localStorage.getItem('vision_ai_is_guest') === '1'
        || !userData.username
        || String(userData.username).toLowerCase() === 'guest');

    // Always rebuild a consistent shell so menu + logout stay present
    const nameToUse = (isGuest || !hasToken)
        ? 'Guest'
        : (userData.full_name || userData.username || 'User');
    const initials = (isGuest || !hasToken)
        ? 'G'
        : (String(nameToUse).split(/\s+/).map(function (n) { return n[0] || ''; }).join('').toUpperCase().slice(0, 2) || 'U');
    const planLabel = (isGuest || !hasToken)
        ? 'Free · sign in'
        : (String(plan).charAt(0).toUpperCase() + String(plan).slice(1));

    footer.innerHTML = `
        <div class="profile-menu-shell">
          <button type="button" class="profile-trigger" id="profileButton" aria-haspopup="true" aria-expanded="false"
              onclick="if(window.toggleProfileDropdown)toggleProfileDropdown(event)" title="Account">
            <span class="profile-avatar" aria-hidden="true">${initials}</span>
            <span class="profile-meta">
              <span class="profile-name">${escapeHtml(nameToUse)}</span>
              <span class="profile-plan">${escapeHtml(planLabel)}</span>
            </span>
            <svg class="profile-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>
          </button>
          <div class="profile-dropdown" id="profileDropdown" role="menu" aria-hidden="true" style="display:none;">
            <div class="profile-dd-head">${escapeHtml(nameToUse)}</div>
            <a role="menuitem" href="/settings.html">Settings</a>
            <a role="menuitem" href="/usage.html">Usage</a>
            <a role="menuitem" href="/upgrade.html">Plans</a>
            <a role="menuitem" href="/versions.html">Versions</a>
            <button type="button" class="dl-item" role="menuitem" onclick="if(window.downloadCurrentChat)downloadCurrentChat()">Download chat</button>
            <hr class="menu-sep">
            ${(isGuest || !hasToken)
              ? '<a role="menuitem" href="/login.html">Sign in</a>'
              : '<button type="button" class="logout-item" data-action="logout" role="menuitem">Log out</button>'}
          </div>
        </div>
    `;
    try { footer._profileBound = false; } catch (e) {}
    if (window.ProfileController && typeof ProfileController.bind === 'function') {
        try { ProfileController.bind(); } catch (e) {}
    }
}

/* Profile menu — single controller (not clipped by sidebar overflow) */
window.closeProfileDropdown = function() {
    var dd = document.getElementById('profileDropdown');
    var btn = document.getElementById('profileButton');
    if (dd) {
        dd.classList.remove('open');
        dd.style.display = 'none';
        dd.setAttribute('aria-hidden', 'true');
    }
    if (btn) btn.setAttribute('aria-expanded', 'false');
};

window.openProfileDropdown = function() {
    var dd = document.getElementById('profileDropdown');
    var btn = document.getElementById('profileButton');
    var footer = document.getElementById('sidebarFooter');
    if (!dd || !btn) return;
    // Fixed positioning escapes sidebar overflow:hidden
    try {
        var r = btn.getBoundingClientRect();
        dd.style.position = 'fixed';
        dd.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 240)) + 'px';
        dd.style.bottom = Math.max(8, window.innerHeight - r.top + 8) + 'px';
        dd.style.top = 'auto';
        dd.style.width = Math.max(200, Math.min(280, r.width + 24)) + 'px';
        dd.style.zIndex = '10050';
    } catch (e) {}
    dd.classList.add('open');
    dd.style.display = 'flex';
    dd.setAttribute('aria-hidden', 'false');
    btn.setAttribute('aria-expanded', 'true');
    try { if (typeof setUserAvatarGender === 'function') setUserAvatarGender(getUserAvatarGender()); } catch (e) {}
};

window.toggleProfileDropdown = function(ev) {
    if (ev) {
        ev.preventDefault();
        ev.stopPropagation();
    }
    var dd = document.getElementById('profileDropdown');
    if (!dd) return;
    var isOpen = dd.classList.contains('open') || dd.style.display === 'flex';
    if (isOpen) window.closeProfileDropdown();
    else window.openProfileDropdown();
};

// Outside click + Escape (one listener each)
if (!window.__vaProfileMenuBound) {
    window.__vaProfileMenuBound = true;
    document.addEventListener('click', function(event) {
        var dd = document.getElementById('profileDropdown');
        var btn = document.getElementById('profileButton');
        if (!dd || !dd.classList.contains('open')) return;
        if (btn && btn.contains(event.target)) return;
        if (dd.contains(event.target)) return;
        window.closeProfileDropdown();
    }, true);
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') window.closeProfileDropdown();
        if ((event.key === 'Enter' || event.key === ' ') && document.activeElement && document.activeElement.id === 'profileButton') {
            event.preventDefault();
            window.toggleProfileDropdown(event);
        }
    });
}

// ============================================================
// AUTHENTICATION
// ============================================================
async function ensureGuestSession() {
    try {
        const res = await fetch('/auth/guest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Vision-Client-Id': getClientId() }
        });
        if (!res.ok) return false;
        const data = await res.json();
        const access = data.access_token || data.token;
        if (!access) return false;
        setTokens(access, data.refresh_token || null);
        const user = data.user || {
            username: data.username || 'guest',
            plan: data.plan || 'free',
            is_guest: true
        };
        localStorage.setItem('vision_ai_user', JSON.stringify(user));
        localStorage.setItem('vision_ai_plan', user.plan || 'free');
        localStorage.setItem('vision_ai_is_guest', '1');
        return true;
    } catch (e) {
        console.warn('guest session failed', e);
        return false;
    }
}

async function checkAuth() {
    // Prevent redirect thrash (blink loop between / and /login.html)
    try {
        if (sessionStorage.getItem('vision_auth_redirecting') === '1') {
            sessionStorage.removeItem('vision_auth_redirecting');
        }
    } catch (e) {}

    const urlParams = new URLSearchParams(window.location.search);
    const urlToken = urlParams.get('token');
    const urlRefresh = urlParams.get('refresh');
    if (urlToken) {
        setTokens(urlToken, urlRefresh);
        window.history.replaceState({}, document.title, "/");
    }

    let token = getAccessToken();

    // No token → silent guest UNLESS user just logged out (must see login page / choose)
    if (!token) {
        try {
            if (sessionStorage.getItem('vision_skip_guest') === '1') {
                // Stay without guest JWT if somehow on chat; prefer login
                if (typeof renderUserProfile === 'function') renderUserProfile();
                return;
            }
        } catch (e) {}
        const ok = await ensureGuestSession();
        if (!ok) {
            // Stay on page offline-friendly; profile shows guest
            localStorage.setItem('vision_ai_user', JSON.stringify({
                username: 'guest', plan: 'free', is_guest: true
            }));
            localStorage.setItem('vision_ai_plan', 'free');
            if (typeof renderUserProfile === 'function') renderUserProfile();
            if (typeof updateStatus === 'function') updateStatus(false);
            return;
        }
        token = getAccessToken();
    }

    try {
        const res = await authenticatedFetch('/auth/me');
        if (!res.ok) {
            // Invalid/expired token → try guest once, never hard-loop to login
            clearTokens();
            const ok = await ensureGuestSession();
            if (ok) {
                try {
                    const res2 = await authenticatedFetch('/auth/me');
                    if (res2.ok) {
                        const data = await res2.json();
                        localStorage.setItem('vision_ai_user', JSON.stringify(data));
                        localStorage.setItem('vision_ai_plan', data.plan || 'free');
                        if (typeof renderUserProfile === 'function') renderUserProfile();
                        if (typeof updateStatus === 'function') updateStatus(true);
                        return;
                    }
                } catch (e2) {}
            }
            localStorage.setItem('vision_ai_user', JSON.stringify({
                username: 'guest', plan: 'free', is_guest: true
            }));
            if (typeof renderUserProfile === 'function') renderUserProfile();
            if (typeof updateStatus === 'function') updateStatus(false);
            return;
        }
        const data = await res.json();
        localStorage.setItem('vision_ai_user', JSON.stringify(data));
        localStorage.setItem('vision_ai_plan', data.plan || 'free');
        if (data.is_guest) localStorage.setItem('vision_ai_is_guest', '1');
        else localStorage.removeItem('vision_ai_is_guest');
        if (typeof renderUserProfile === 'function') renderUserProfile();
        if (typeof updateStatus === 'function') updateStatus(true);
        if (typeof reloadHistoryForUser === 'function') {
            reloadHistoryForUser();
            if (chatHistory.length === 0) startNewChat();
            else loadChat(chatHistory[0].id);
        }
    } catch (err) {
        console.error('Auth check failed:', err);
        // Network error: stay put, do not redirect (stops blink)
        if (typeof updateStatus === 'function') updateStatus(false);
    }
}

window.performLogout = async function() {
    if (window.VisionAuth && typeof window.VisionAuth.logout === 'function') {
        return window.VisionAuth.logout({ confirm: true });
    }
    // fallback if auth.js missing
    if (typeof clearTokens === 'function') clearTokens();
    window.location.replace('/login.html');
};

function updateStatus(online) {
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (dot && text) {
        dot.className = online ? 'status-dot' : 'status-dot offline';
        text.textContent = online ? 'Online' : 'Offline';
        text.style.color = online ? '#00C6FF' : '#ff6b6b';
    }
}

// ============================================================
// 🌙 FLOATING THEME TOGGLE
// ============================================================
function updateThemeIcon(theme) {
    const icon = theme === 'light'
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
            : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    ['floatingThemeToggle', 'headerThemeBtn', 'themeToggle', 'themePickerBtn'].forEach((id) => {
        const btn = document.getElementById(id);
        if (btn) {
            // MUST use innerHTML — textContent paints raw SVG source (stroke-width="2" leak)
            btn.innerHTML = icon;
            btn.setAttribute('aria-label', theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode');
            btn.title = theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode';
        }
    });
}

function toggleTheme() {
    try {
        const stored = localStorage.getItem('vision_ai_theme') || 'dark';
        const next = (stored === 'light' || document.documentElement.getAttribute('data-theme') === 'light')
            ? 'dark' : 'light';
        localStorage.setItem('vision_ai_theme', next);
        applyTheme(next);
        if (typeof showToast === 'function') showToast(next === 'dark' ? 'Dark mode' : 'Light mode', 'info', 1200);
    } catch (e) {
        console.error(e);
        const cur = document.documentElement.getAttribute('data-theme');
        const next = cur === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('vision_ai_theme', next);
        if (typeof updateThemeIcon === 'function') updateThemeIcon(next);
    }
}

// ============================================================
// PROMPT STUDIO — Modern redesign
// Categories, tags, search, favorites, recent, templates, one-click copy
// ============================================================
let favorites = JSON.parse(localStorage.getItem('vision_ai_favorites') || '[]');
let recent = JSON.parse(localStorage.getItem('vision_ai_recent') || '[]');
let currentCategory = 'All';
let isFavoritesMode = false;
let isRecentMode = false;
let activeTag = null;

const PROMPT_LIBRARY = window.PROMPT_LIBRARY = {
    "Featured": {
        icon: "⭐", color: "#34d399", tags: ["featured"],
        prompts: [
            { title: "Master exam solver", featured: true, t: "You are a Cambridge/FBISE physics examiner. Solve the uploaded paper or pasted questions step by step:\n1) Given data\n2) Formula\n3) Substitution\n4) Final answer with units\n5) One-line check.\nMark uncertain figures clearly. Reply in the same language as the user (English or simple Urdu).", tags: ["physics","exam"] },
            { title: "Explain simply", featured: true, t: "Explain [topic] in simple words a college student can understand. Use short paragraphs, one analogy, and 3 key points. Avoid jargon unless you define it.", tags: ["study"] },
            { title: "PDF / notes to Q&A", featured: true, t: "From the uploaded document only, create clear study Q&A:\n- 10 important questions\n- Detailed answers with examples from the text\nDo not invent chapters that are not in the document.", tags: ["study","exam"] }
        ]
    },
    "Physics / Exam": {
        icon: "⚛️", color: "#2dd4bf", tags: ["physics","exam"],
        prompts: [
            { title: "Step-by-step MCQ pack", t: "For each MCQ: state the concept, eliminate wrong options, give the correct letter, and a 2-sentence reason.\n\nQuestions:\n[paste]", tags: ["exam"] },
            { title: "Derive + numeric", t: "Derive the working formula from first principles, then compute with: [data]. Show units at every step. Use $$ for equations.", tags: ["physics"] },
            { title: "Past paper full solve", t: "Solve this past paper in order. For each question: marks-aware depth, working, final answer box. If a diagram is needed, describe it clearly.\n\n[paste or upload]", tags: ["exam","physics"] },
            { title: "Formula sheet", t: "Make a clean formula sheet for [chapter/topic]: formula, symbols, SI units, and one example each.", tags: ["physics","study"] }
        ]
    },
    "Study": {
        icon: "📚", color: "#38bdf8", tags: ["study"],
        prompts: [
            { title: "Summarize notes", t: "Summarize the following notes into bullet points + a 5-line revision box:\n\n[paste]", tags: ["study"] },
            { title: "Flashcards", t: "Create 15 flashcards (front/back) for:\n[topic or paste notes]", tags: ["study"] },
            { title: "Teach me like I'm new", t: "Teach [topic] from zero. Use everyday examples, then slightly harder ones. End with 3 practice questions.", tags: ["study"] }
        ]
    },
    "Urdu": {
        icon: "🇵🇰", color: "#a78bfa", tags: ["urdu"],
        prompts: [
            { title: "Easy Urdu explanation", t: "اس موضوع کو آسان پاکستانی اردو میں سمجھاؤ۔ مشکل الفاظ سے بچو۔ طریقہ، مثال، اور خلاصہ دو۔ موضوع: [topic]", tags: ["urdu","study"] },
            { title: "Accurate Urdu translation", t: "Translate into clear everyday Pakistani Urdu. Keep technical terms in English in parentheses when needed:\n\n[text]", tags: ["urdu"] },
            { title: "Urdu study notes", t: "اس موضوع پر آسان اردو نوٹس لکھیں: تعریف، فارمولے (انگریزی میں ٹھیک)، اور تین مثالیں۔ موضوع: [topic]", tags: ["urdu"] }
        ]
    },
    "YouTube": {
        icon: "🎥", color: "#f472b6", tags: ["youtube"],
        prompts: [
            { title: "Video summary + timestamps", t: "Summarize this YouTube video with timestamps, key claims, and 5 action items:\n[URL]", tags: ["youtube"] },
            { title: "Quiz from video", t: "From the transcript only, create 10 MCQs with answers and short explanations.\n[URL]", tags: ["youtube","quiz"] },
            { title: "Download helper", t: "I want to download this YouTube video as [mp3/mp4 720p]. Confirm the title and give clear next steps in the app.\n[URL]", tags: ["youtube"] }
        ]
    },
    "Code": {
        icon: "💻", color: "#60a5fa", tags: ["code"],
        prompts: [
            { title: "Debugger", t: "Find the bug, explain root cause, and provide a minimal fixed version.\nLanguage: [lang]\n\n```\n[code]\n```", tags: ["code"] },
            { title: "Explain this code", t: "Explain this code line by line in simple terms, then suggest 2 improvements:\n\n```\n[code]\n```", tags: ["code"] },
            { title: "Write a function", t: "Write a clean, documented [lang] function that does: [task]. Include example usage and edge cases.", tags: ["code"] }
        ]
    },
    "Writing": {
        icon: "✍️", color: "#fbbf24", tags: ["writing"],
        prompts: [
            { title: "Professional email", t: "Draft a clear email about [topic] for [audience]: subject line, body, and CTA. Tone: [formal/friendly].", tags: ["writing"] },
            { title: "Scene polish", t: "Rewrite this scene with stronger sensory detail and tighter dialogue. Keep the original meaning:\n\n[paste]", tags: ["writing"] },
            { title: "LinkedIn / CV bullet", t: "Turn this experience into 3 strong CV bullets with metrics where possible:\n\n[paste]", tags: ["writing"] }
        ]
    },
    "Image": {
        icon: "🖼️", color: "#fb7185", tags: ["image"],
        prompts: [
            { title: "Diagram request", t: "Create a clear labeled diagram for: [physics/biology concept]. Keep labels readable.", tags: ["image","physics"] },
            { title: "Creative image", t: "Generate an image of: [description]. Style: [realistic/illustration].", tags: ["image"] }
        ]
    }
};



function normalizePrompt(p) {
    if (typeof p === 'string') return { t: p, tags: [] };
    return p;
}

function getAllPrompts() {
    const all = [];
    Object.entries(PROMPT_LIBRARY).forEach(([cat, data]) => {
        (data.prompts || []).forEach(p => {
            const n = normalizePrompt(p);
            all.push({ ...n, category: cat, icon: data.icon });
        });
    });
    return all;
}

function getAllTags() {
    const tags = new Set();
    getAllPrompts().forEach(p => (p.tags || []).forEach(t => tags.add(t)));
    return Array.from(tags).sort();
}

function closePromptStudio() {
    const modal = document.getElementById('helpModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('ps-open', 'open', 'ps-drawer-root');
        modal.setAttribute('aria-hidden', 'true');
        // Clear any leftover transform that could hide the panel next open
        const panel = modal.querySelector('.ps-panel');
        if (panel) {
            panel.style.transform = 'none';
            panel.style.opacity = '1';
            panel.style.visibility = 'visible';
        }
    }
    document.body.classList.remove('ps-drawer-open', 'sidebar-open', 'chat-focus-mode');
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
    // Also close alternate drawer from prompt_studio.js
    const drawer = document.getElementById('promptStudioDrawer');
    if (drawer) {
        drawer.classList.remove('open');
        drawer.setAttribute('aria-hidden', 'true');
    }
    // Kill any leftover full-screen dim layers (never leave blurred page)
    document.querySelectorAll('.ps-backdrop, .prompt-studio-overlay, #sidebar-overlay').forEach(function (el) {
        el.classList.remove('active', 'open');
        if (el.id === 'sidebar-overlay') {
            el.style.display = 'none';
            el.style.pointerEvents = 'none';
            el.style.opacity = '0';
        }
    });
}

function toggleHelpModal() {
    const modal = document.getElementById('helpModal');
    const isOpen = modal && (modal.style.display === 'flex' || modal.classList.contains('ps-open'));
    if (isOpen) {
        closePromptStudio();
        return;
    }
    if (!modal) {
        createHelpModal();
    }
    const hm = document.getElementById('helpModal');
    if (!hm) return;
    hm.classList.add('ps-drawer-root', 'ps-open');
    hm.style.display = 'flex';
    hm.style.visibility = 'visible';
    hm.style.opacity = '1';
    hm.style.pointerEvents = 'auto';
    hm.setAttribute('aria-hidden', 'false');
    // Ensure panel is not left off-screen by older drawer CSS
    const panel = hm.querySelector('.ps-panel');
    if (panel) {
        panel.style.transform = 'none';
        panel.style.opacity = '1';
        panel.style.visibility = 'visible';
        panel.style.display = 'flex';
    }
    document.body.classList.add('ps-drawer-open');
    // Do NOT lock body overflow permanently — only while open, restored on close
    document.body.style.overflow = 'hidden';
    try {
        renderCategories();
        renderTagChips();
        renderPrompts();
        updateStats();
    } catch (err) {
        console.warn('Prompt Studio render:', err);
    }
    setTimeout(function () {
        const s = document.getElementById('promptSearch');
        if (s) s.focus();
    }, 50);
}
window.closePromptStudio = closePromptStudio;

function createHelpModal() {
    const modal = document.createElement('div');
    modal.id = 'helpModal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-label', 'Prompt Studio');
    modal.style.cssText = 'display:none; position:fixed; inset:0; z-index:99999; background:rgba(0,0,0,0.72); backdrop-filter:blur(10px); align-items:center; justify-content:center; padding:16px;';
    modal.innerHTML = `
        <div class="ps-panel" style="background:var(--bg-secondary); width:100%; max-width:1080px; max-height:92vh; border-radius:20px; overflow:hidden; display:flex; flex-direction:column; box-shadow:var(--shadow-lg); border:1px solid var(--border-color);">
            <div style="padding:20px 24px 12px; border-bottom:1px solid var(--border-color); flex-shrink:0;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:14px;">
                    <div>
                        <h2 style="font-size:20px; font-weight:800; color:var(--text-main); display:flex; align-items:center; gap:10px; letter-spacing:-0.3px;">
                            <span style="background:linear-gradient(135deg,#00C6FF,#7B68EE); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">Prompt Studio</span>
                        </h2>
                        <p style="color:var(--text-muted); font-size:13px; margin-top:4px;">Click a card to load it into chat • edit placeholders • Send</p>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <span id="promptCount" style="color:var(--text-muted); font-size:12px; background:var(--bg-tertiary); padding:4px 10px; border-radius:20px;">0</span>
                        <button onclick="closePromptStudio()" aria-label="Close" style="background:var(--bg-tertiary); border:1px solid var(--border-color); color:var(--text-muted); width:36px; height:36px; border-radius:10px; cursor:pointer; font-size:18px; line-height:1;">✕</button>
                    </div>
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                    <div style="flex:1; min-width:200px; position:relative;">
                        <input type="text" id="promptSearch" placeholder="Search prompts…" autocomplete="off"
                               style="width:100%; padding:11px 14px 11px 38px; border-radius:12px; border:1px solid var(--border-color); background:var(--input-bg); color:var(--text-main); font-size:14px; outline:none;"
                               oninput="handleSearchInput(this.value)">
                        <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%); opacity:0.5; pointer-events:none;">🔍</span>
                    </div>
                    <button onclick="showRecentPrompts()" id="recentBtn" style="padding:10px 14px; border-radius:10px; border:1px solid var(--border-color); background:var(--bg-tertiary); color:var(--text-main); cursor:pointer; font-size:13px; white-space:nowrap;">🕐 Recent</button>
                    <button onclick="toggleFavorites()" id="favBtn" style="padding:10px 14px; border-radius:10px; border:1px solid var(--border-color); background:var(--bg-tertiary); color:var(--text-main); cursor:pointer; font-size:13px; white-space:nowrap;">⭐ Favorites</button>
                    <button onclick="clearSearch()" style="padding:10px 14px; border-radius:10px; border:1px solid var(--border-color); background:transparent; color:var(--text-muted); cursor:pointer; font-size:13px;">Clear</button>
                </div>
                <div id="tagChips" style="display:flex; gap:6px; flex-wrap:wrap; margin-top:12px;"></div>
            </div>
            <div id="categoryTabs" style="display:flex; gap:6px; flex-wrap:nowrap; overflow-x:auto; padding:12px 24px 0; flex-shrink:0; scrollbar-width:thin;"></div>
            <div id="promptGrid" style="overflow-y:auto; flex:1; padding:14px 24px 20px; display:grid; grid-template-columns:repeat(auto-fill, minmax(280px, 1fr)); gap:12px; min-height:200px;"></div>
            <div style="padding:12px 24px; border-top:1px solid var(--border-color); display:flex; justify-content:space-between; color:var(--text-muted); font-size:12px; flex-wrap:wrap; gap:8px; flex-shrink:0;">
                <span>⭐ <span id="favoriteCount">0</span> favorites · 🕐 <span id="recentCount">0</span> recent</span>
                <span><kbd style="background:var(--bg-tertiary); padding:2px 6px; border-radius:4px; border:1px solid var(--border-color);">Ctrl</kbd>+<kbd style="background:var(--bg-tertiary); padding:2px 6px; border-radius:4px; border:1px solid var(--border-color);">K</kbd> open · <kbd style="background:var(--bg-tertiary); padding:2px 6px; border-radius:4px; border:1px solid var(--border-color);">Esc</kbd> close</span>
            </div>
        </div>
    `;
    modal.addEventListener('click', (e) => { if (e.target === modal) closePromptStudio(); });
    document.addEventListener('keydown', function _psEsc(ev) {
        if (ev.key === 'Escape') { closePromptStudio(); }
    });
    document.body.appendChild(modal);

    // Inject minimal styles once
    if (!document.getElementById('ps-styles')) {
        const style = document.createElement('style');
        style.id = 'ps-styles';
        style.textContent = `
            .category-tab { padding:8px 14px; border-radius:20px; border:1px solid var(--border-color); background:var(--bg-tertiary); color:var(--text-main); cursor:pointer; font-size:13px; white-space:nowrap; transition:all 0.15s ease; font-family:inherit; }
            .category-tab:hover { border-color:var(--primary-cyan); }
            .category-tab.active { background:linear-gradient(135deg,rgba(0,198,255,0.2),rgba(123,104,238,0.2)); border-color:var(--primary-cyan); color:var(--text-main); font-weight:600; }
            .ps-card { padding:14px; background:var(--bg-tertiary); border-radius:14px; border:1px solid var(--border-color); cursor:pointer; transition:all 0.18s ease; display:flex; flex-direction:column; gap:10px; min-height:110px; }
            .ps-card:hover { border-color:var(--primary-cyan); transform:translateY(-2px); box-shadow:var(--shadow-md); }
            .ps-card-text { font-size:13.5px; line-height:1.45; color:var(--text-main); flex:1; }
            .ps-card-meta { display:flex; justify-content:space-between; align-items:center; gap:8px; }
            .ps-tag { font-size:10px; padding:2px 8px; border-radius:10px; background:rgba(0,198,255,0.1); color:var(--primary-cyan); border:1px solid rgba(0,198,255,0.2); }
            .ps-actions button { background:none; border:none; cursor:pointer; font-size:16px; padding:2px 4px; border-radius:6px; line-height:1; }
            .ps-actions button:hover { background:var(--bg-secondary); }
            .ps-tag-chip { padding:4px 10px; border-radius:14px; border:1px solid var(--border-color); background:transparent; color:var(--text-muted); font-size:11px; cursor:pointer; font-family:inherit; }
            .ps-tag-chip.active { background:rgba(123,104,238,0.15); border-color:var(--primary-purple); color:var(--text-main); }
            #promptSearch:focus { border-color:var(--primary-cyan); box-shadow:0 0 0 3px rgba(0,198,255,0.12); }
            @media (max-width:600px) {
                #promptGrid { grid-template-columns:1fr !important; padding:12px !important; }
                .ps-panel { max-height:96vh !important; border-radius:16px !important; }
            }
        `;
        document.head.appendChild(style);
    }
}

function renderCategories() {
    const container = document.getElementById('categoryTabs');
    if (!container) return;
    let html = `<button class="category-tab ${currentCategory === 'All' && !isFavoritesMode && !isRecentMode ? 'active' : ''}" data-category="All" onclick="filterByCategory('All')">📌 All</button>`;
    Object.keys(PROMPT_LIBRARY).forEach(cat => {
        const icon = PROMPT_LIBRARY[cat].icon;
        const active = currentCategory === cat && !isFavoritesMode && !isRecentMode ? 'active' : '';
        html += `<button class="category-tab ${active}" data-category="${cat}" onclick="filterByCategory('${cat}')">${icon} ${cat}</button>`;
    });
    container.innerHTML = html;
}

function renderTagChips() {
    const el = document.getElementById('tagChips');
    if (!el) return;
    const tags = getAllTags().slice(0, 14);
    el.innerHTML = tags.map(t =>
        `<button class="ps-tag-chip ${activeTag === t ? 'active' : ''}" onclick="filterByTag('${t}')">#${t}</button>`
    ).join('');
}

function filterByTag(tag) {
    activeTag = activeTag === tag ? null : tag;
    isFavoritesMode = false;
    isRecentMode = false;
    renderTagChips();
    renderPrompts(currentCategory, document.getElementById('promptSearch')?.value || '');
}

function renderPrompts(category = currentCategory, searchTerm = '') {
    const grid = document.getElementById('promptGrid');
    const count = document.getElementById('promptCount');
    if (!grid) return;

    let prompts = [];
    if (isFavoritesMode) {
        prompts = favorites.map(t => ({ t, tags: [], category: 'Favorite', icon: '⭐' }));
    } else if (isRecentMode) {
        prompts = recent.map(t => ({ t, tags: [], category: 'Recent', icon: '🕐' }));
    } else if (category === 'All') {
        prompts = getAllPrompts();
    } else {
        const data = PROMPT_LIBRARY[category];
        prompts = (data?.prompts || []).map(p => {
            const n = normalizePrompt(p);
            return { ...n, category, icon: data.icon };
        });
    }

    if (searchTerm) {
        const q = searchTerm.toLowerCase();
        prompts = prompts.filter(p =>
            p.t.toLowerCase().includes(q) ||
            (p.tags || []).some(tg => tg.includes(q)) ||
            (p.category || '').toLowerCase().includes(q)
        );
    }
    if (activeTag) {
        prompts = prompts.filter(p => (p.tags || []).includes(activeTag));
    }

    if (prompts.length === 0) {
        grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:48px 20px; color:var(--text-muted);">
            <div style="font-size:32px; margin-bottom:8px;">🔍</div>
            <div>No prompts found. Try another search or category.</div>
        </div>`;
        if (count) count.textContent = '0 prompts';
        return;
    }

    grid.innerHTML = prompts.map(p => {
        const text = p.t;
        const escaped = text.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const isFav = favorites.includes(text);
        const tagsHtml = (p.tags || []).slice(0, 3).map(tg => `<span class="ps-tag">#${tg}</span>`).join('');
        const title = p.title ? `<div class="ps-card-title">${escapeHtml(p.title)}</div>` : '';
        return `
            <div class="ps-card" onclick="usePromptInChat('${escaped}')" title="Click to load into chat">
                ${title}
                <div class="ps-card-text">${escapeHtml((text.length > 140 ? text.slice(0, 140) + "…" : text))}</div>
                <div class="ps-card-meta">
                    <div style="display:flex; gap:4px; flex-wrap:wrap; align-items:center;">
                        <span style="font-size:11px; color:var(--text-muted);">${p.icon || ''} ${escapeHtml(p.category || '')}</span>
                        ${tagsHtml}
                    </div>
                    <div class="ps-actions" onclick="event.stopPropagation()">
                        <button type="button" title="${isFav ? 'Unfavorite' : 'Favorite'}" onclick="toggleFavorite('${escaped}')">${isFav ? '⭐' : '☆'}</button>
                        <button type="button" title="Use in chat" onclick="copyAndChat('${escaped}')">➤</button>
                    </div>
                </div>
            </div>`;
    }).join('');

    if (count) count.textContent = `${prompts.length} prompt${prompts.length === 1 ? '' : 's'}`;
}

function filterByCategory(category) {
    currentCategory = category;
    isFavoritesMode = false;
    isRecentMode = false;
    activeTag = null;
    const favBtn = document.getElementById('favBtn');
    const recentBtn = document.getElementById('recentBtn');
    if (favBtn) favBtn.textContent = '⭐ Favorites';
    if (recentBtn) recentBtn.style.opacity = '1';
    renderCategories();
    renderTagChips();
    renderPrompts(category, document.getElementById('promptSearch')?.value || '');
}

function handleSearchInput(value) {
    isFavoritesMode = false;
    isRecentMode = false;
    renderPrompts(currentCategory, value);
}

function clearSearch() {
    const s = document.getElementById('promptSearch');
    if (s) s.value = '';
    activeTag = null;
    isFavoritesMode = false;
    isRecentMode = false;
    renderTagChips();
    renderPrompts(currentCategory, '');
}

function showRecentPrompts() {
    isRecentMode = true;
    isFavoritesMode = false;
    activeTag = null;
    const favBtn = document.getElementById('favBtn');
    if (favBtn) favBtn.textContent = '⭐ Favorites';
    document.querySelectorAll('.category-tab').forEach(btn => btn.classList.remove('active'));
    renderPrompts();
}

function toggleFavorite(prompt) {
    const index = favorites.indexOf(prompt);
    if (index > -1) favorites.splice(index, 1);
    else favorites.push(prompt);
    localStorage.setItem('vision_ai_favorites', JSON.stringify(favorites));
    renderPrompts(currentCategory, document.getElementById('promptSearch')?.value || '');
    updateStats();
}

function toggleFavorites() {
    isFavoritesMode = !isFavoritesMode;
    isRecentMode = false;
    activeTag = null;
    const favBtn = document.getElementById('favBtn');
    if (favBtn) favBtn.textContent = isFavoritesMode ? '🔙 All' : '⭐ Favorites';
    if (isFavoritesMode) {
        document.querySelectorAll('.category-tab').forEach(btn => btn.classList.remove('active'));
        renderPrompts();
    } else {
        filterByCategory(currentCategory);
    }
}

function copyPrompt(text) {
    const doCopy = () => {
        recent = recent.filter(r => r !== text);
        recent.unshift(text);
        if (recent.length > 15) recent.pop();
        localStorage.setItem('vision_ai_recent', JSON.stringify(recent));
        updateStats();
        showToast('✅ Prompt copied', 'success');
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        (window.vaCopyText ? window.vaCopyText(text) : navigator.clipboard.writeText(text)).then(doCopy).catch(() => {
            // fallback
            const ta = document.createElement('textarea');
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            doCopy();
        });
    } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        doCopy();
    }
}

function copyAndChat(text) {
    usePromptInChat(text);
}

function usePromptInChat(text) {
    recent = recent.filter(r => r !== text);
    recent.unshift(text);
    if (recent.length > 15) recent.pop();
    localStorage.setItem('vision_ai_recent', JSON.stringify(recent));
    updateStats();
    const input = document.getElementById('message');
    if (input) {
        input.value = text;
        input.focus();
        input.dispatchEvent(new Event('input', { bubbles: true }));
        // Place cursor at first [placeholder]
        const m = text.match(/\[[^\]]+\]/);
        if (m) {
            const i = text.indexOf(m[0]);
            try { input.setSelectionRange(i, i + m[0].length); } catch (_) {}
        }
    }
    const modal = document.getElementById('helpModal');
    if (modal) modal.style.display = 'none';
    showToast('Prompt loaded in chat — edit placeholders then Send', 'success', 3000);
}
window.usePromptInChat = usePromptInChat;

function updateStats() {
    const fc = document.getElementById('favoriteCount');
    const rc = document.getElementById('recentCount');
    if (fc) fc.textContent = favorites.length;
    if (rc) rc.textContent = recent.length;
}

// ============================================================
// EVENT LISTENERS
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    if (window._visionDOMReady) return;
    window._visionDOMReady = true;
    try {
      document.querySelectorAll('.unique-banner,.welcome-banner,.announcement-banner,#promoBanner').forEach(function(el){ el.remove(); });
    } catch (e) {}

    try { document.body.classList.add('vision-ready'); } catch (e) {}

    // Theme already applied inline in <head> — only sync icons / mismatch
    const savedTheme = localStorage.getItem('vision_ai_theme') || 'dark';
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    let resolved = savedTheme;
    if (resolved === 'system') {
        resolved = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }
    if (resolved !== current) applyTheme(resolved);
    if (typeof updateThemeIcon === 'function') updateThemeIcon(resolved === 'system' ? current : resolved);

    if (savedTheme === 'system') {
        window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
            applyTheme('system');
            updateThemeIcon('system');
        });
    }

    checkAuth();

    try {
        if (chatHistory.length === 0) startNewChat();
        else loadChat(chatHistory[0].id);
    } catch (e) {
        console.error('Failed to load initial chat:', e);
        startNewChat();
    }

    const messageInput = document.getElementById('message');
    if (messageInput) {
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });
    }

    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', renderFilePreview);
    }

    /* resize: visionSidebarController only */

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            toggleHelpModal();
        }
        if (e.key === 'Escape') {
            document.querySelectorAll('.chat-action-menu.show').forEach(el => el.classList.remove('show'));
            const dropdown = document.getElementById('profileDropdown');
            if (dropdown) dropdown.style.display = 'none';
            const modal = document.getElementById('helpModal');
            if (modal && modal.style.display === 'flex') {
                modal.style.display = 'none';
            }
        }
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
            e.preventDefault();
            window.open('/admin/search', '_blank', 'noopener,noreferrer');
        }
    });

    // Admin floating buttons: only show for admin users (role or username)
(async function setupAdminButtons() {
    const adminBtn = document.getElementById('adminBtn');
    const adminPayBtn = document.getElementById('adminPayBtn');
    const token = getAccessToken();
    if (!token) return;
    let isAdmin = false;
    try {
        const user = JSON.parse(localStorage.getItem('vision_ai_user') || '{}');
        // ✅ FIX: Check for 'aftab' as well
        if (user.role === 'admin' || user.username === 'admin' || user.username === 'aftab') isAdmin = true;
    } catch (_) {}
    if (!isAdmin) {
        try {
            const res = await authedFetch('/auth/me');
            if (res && res.ok) {
                const data = await res.json();
                // ✅ FIX: Check for 'aftab' as well
                if (data.role === 'admin' || data.username === 'admin' || data.username === 'aftab') isAdmin = true;
                localStorage.setItem('vision_ai_user', JSON.stringify(data));
            }
        } catch (_) {}
    }
    if (isAdmin) {
        if (adminBtn) /* adminBtn moved to top bar */;
        if (adminPayBtn) adminPayBtn.style.display = 'flex';
        var cacheChip = document.getElementById('adminCacheChip');
        var payChip = document.getElementById('adminPayChip');
        if (cacheChip) { cacheChip.hidden = false; cacheChip.style.display = 'inline-flex'; }
        if (payChip) { payChip.hidden = false; payChip.style.display = 'inline-flex'; }
    }
})();

    console.log('👁️ Vision AI v4.4.0 - Ready');
});

// ============================================================
// FILE PREVIEW
// ============================================================
function renderFilePreview() {
    try {
        const fi = document.getElementById('fileInput');
        if (fi && Array.from(fi.files || []).some(f => (f.type || '').startsWith('image/'))) {
            showToast('Image attached — ask what you see or “solve this diagram”', 'info', 2500);
        }
    } catch (_) {}

    const fileInput = document.getElementById('fileInput');
    const previewArea = document.getElementById('filePreviewArea');
    if (!fileInput || !previewArea) return;

    previewArea.innerHTML = '';
    const files = Array.from(fileInput.files);
    if (files.length === 0) return;

    files.forEach((file, index) => {
        const chip = document.createElement('div');
        chip.className = 'file-chip';
        chip.innerHTML = `
            <span>📄</span>
            <span class="file-chip-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
            <button type="button" class="file-chip-remove" title="Remove file">✕</button>
        `;
        chip.querySelector('.file-chip-remove').addEventListener('click', () => removeSelectedFile(index));
        previewArea.appendChild(chip);
    });
}

function removeSelectedFile(index) {
    const fileInput = document.getElementById('fileInput');
    if (!fileInput) return;
    const dt = new DataTransfer();
    Array.from(fileInput.files).forEach((file, i) => {
        if (i !== index) dt.items.add(file);
    });
    fileInput.files = dt.files;
    renderFilePreview();
}

// ============================================================
// 🟢 ADDITIONAL SAFEGUARDS
// ============================================================
if (window._visionAIInitialized) {
    console.warn('Vision AI already initialized!');
} else {
    window._visionAIInitialized = true;
}

window.onerror = function(msg, url, line, col, error) {
    console.error('Global error:', msg, error);
    showToast('An unexpected error occurred. Please refresh the page.', 'error');
    return true;
};

window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('An unexpected error occurred.', 'error');
});

// Export functions for global access
window.applyTheme = applyTheme;
window.getAccessToken = getAccessToken;
window.getRefreshToken = getRefreshToken;
window.setTokens = setTokens;
window.clearTokens = clearTokens;
window.refreshAccessToken = refreshAccessToken;
window.authenticatedFetch = authenticatedFetch;
window.showToast = showToast;
window.forceOpenSearch = forceOpenSearch;
window.renameChat = renameChat;
window.deleteChat = deleteChat;
window.startNewChat = startNewChat;
window.loadChat = loadChat;
window.clearAllCaches = clearAllCaches;


function copyMessageText(btn) {
    const bubble = btn.closest('.message-bubble');
    if (!bubble) return;
    const body = bubble.querySelector('.markdown-content');
    const text = body ? body.innerText : bubble.innerText;
    const done = () => {
        const prev = btn.textContent;
        btn.textContent = '✅ Copied';
        setTimeout(() => { btn.textContent = prev; }, 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
        (window.vaCopyText ? window.vaCopyText(text) : navigator.clipboard.writeText(text)).then(done).catch(() => {
            const ta = document.createElement('textarea');
            ta.value = text; document.body.appendChild(ta); ta.select();
            document.execCommand('copy'); document.body.removeChild(ta); done();
        });
    }
}

function toggleExpandMessage(btn) {
    const bubble = btn.closest('.message-bubble');
    const body = bubble && bubble.querySelector('.markdown-content');
    if (!body) return;
    bubble.classList.toggle('msg-tall');
    body.classList.toggle('msg-expanded-height');
    btn.classList.toggle('active');
    btn.textContent = body.classList.contains('msg-expanded-height') ? '▴ Collapse' : '↕ Height';
}

function toggleWideMessage(btn) {
    const bubble = btn.closest('.message-bubble');
    if (!bubble) return;
    bubble.classList.toggle('msg-wide');
    bubble.classList.toggle('msg-tall');
    btn.classList.toggle('active');
    btn.textContent = bubble.classList.contains('msg-wide') ? '↔ Narrow' : '↔ Width';
}

function zoomMessage(btn, factor) {
    const bubble = btn.closest('.message-bubble');
    const body = bubble && bubble.querySelector('.markdown-content');
    if (!body) return;
    const cur = parseFloat(body.dataset.zoom || '1');
    const next = Math.min(1.8, Math.max(0.75, +(cur * factor).toFixed(2)));
    body.dataset.zoom = String(next);
    body.style.fontSize = (15 * next) + 'px';
    body.style.lineHeight = String(1.65 + (next - 1) * 0.2);
}

function focusMessageFullscreen(btn) {
    const bubble = btn.closest('.message-bubble');
    if (!bubble) return;
    let overlay = document.getElementById('msgFullscreenOverlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'msgFullscreenOverlay';
        overlay.innerHTML = `
            <div class="msg-fs-panel glass-panel">
                <div class="msg-fs-toolbar">
                    <span>Response view</span>
                    <div style="display:flex;gap:8px;">
                        <button type="button" class="msg-action-btn" id="msgFsCopy">Copy</button>
                        <button type="button" class="msg-action-btn" id="msgFsClose">✕ Close</button>
                    </div>
                </div>
                <div class="msg-fs-body markdown-content" id="msgFsBody"></div>
            </div>`;
        document.body.appendChild(overlay);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) closeMsgFullscreen(); });
        document.getElementById('msgFsClose').onclick = closeMsgFullscreen;
        document.getElementById('msgFsCopy').onclick = () => {
            const t = document.getElementById('msgFsBody').innerText;
            navigator.clipboard.writeText(t).then(() => showToast('Copied', 'success'));
        };
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlay.classList.contains('open')) closeMsgFullscreen();
        });
    }
    const src = bubble.querySelector('.markdown-content');
    document.getElementById('msgFsBody').innerHTML = src ? src.innerHTML : bubble.innerHTML;
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeMsgFullscreen() {
    const overlay = document.getElementById('msgFullscreenOverlay');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
}

function toggleChatFocusMode() {
    document.body.classList.toggle('chat-focus-mode');
    const on = document.body.classList.contains('chat-focus-mode');
    document.documentElement.setAttribute('data-focus', on ? '1' : '0');
    // Browser fullscreen for true focus
    try {
        if (on && !document.fullscreenElement) {
            document.documentElement.requestFullscreen?.();
        } else if (!on && document.fullscreenElement) {
            document.exitFullscreen?.();
        }
    } catch (_) {}
    // Ensure overlays never trap clicks after focus exit
    if (!on) {
        if (typeof closeMobileSidebar === 'function') closeMobileSidebar();
        document.body.style.overflow = '';
        document.body.classList.remove('sidebar-open');
    }
    const btn = document.querySelector('[onclick="toggleChatFocusMode()"]');
    if (btn) btn.classList.toggle('active', on);
    const title = document.getElementById('chatTitle');
    if (title && !title.dataset.orig) title.dataset.orig = title.textContent;
}
// Keep class in sync when user exits fullscreen via Esc
document.addEventListener('fullscreenchange', function () {
    if (!document.fullscreenElement && document.body.classList.contains('chat-focus-mode')) {
        document.body.classList.remove('chat-focus-mode');
        document.documentElement.setAttribute('data-focus', '0');
        document.body.style.overflow = '';
        const btn = document.querySelector('[onclick="toggleChatFocusMode()"]');
        if (btn) btn.classList.remove('active');
    }
});


window.addMessage = addMessage;
window.copyMessageText = copyMessageText;
window.toggleExpandMessage = toggleExpandMessage;
window.toggleChatFocusMode = toggleChatFocusMode;
window.closeMsgFullscreen = closeMsgFullscreen;
window.focusMessageFullscreen = focusMessageFullscreen;
window.zoomMessage = zoomMessage;
window.toggleWideMessage = toggleWideMessage;
window.editMessage = editMessage;
window.cancelEdit = cancelEdit;
window.sendEdit = sendEdit;


// ---- Mobile-friendly forced download (blob) ----
function hideWelcomeEmpty() {
    try {
        var w = document.getElementById('welcomeEmpty');
        if (w) w.style.display = 'none';
    } catch (e) {}
}
function ensureChatOutput() {
    var output = document.getElementById('chatOutput') || document.getElementById('output');
    if (output) return output;
    var main = document.querySelector('.main-content');
    if (!main) return null;
    output = document.createElement('div');
    output.id = 'chatOutput';
    output.className = 'chat-container';
    output.setAttribute('role', 'log');
    var inputArea = document.querySelector('.input-area');
    if (inputArea) main.insertBefore(output, inputArea);
    else main.appendChild(output);
    return output;
}

function forceMobileDownload(url, suggestedName) {
    if (!url) throw new Error('No download URL');
    // Resolve relative paths; force ?dl=1 so server returns octet-stream + attachment
    var absolute = url;
    var name = (suggestedName || '').trim();
    try {
        var u = new URL(url, window.location.origin);
        if (/\/upload\/downloads\//.test(u.pathname)) {
            u.searchParams.set('dl', '1');
        }
        absolute = u.href;
        if (!name || name === 'true' || name === 'download') {
            name = (u.pathname.split('/').pop() || 'download.bin');
        }
    } catch (e) {
        if (!name) name = 'download.bin';
    }

    var isMobile = /Android|iPhone|iPad|iPod|Mobile|webOS|BlackBerry/i.test(navigator.userAgent || '') ||
        (window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
    var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent || '') ||
        (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

    // MOBILE: must stay synchronous with the user tap (no fetch/blob).
    // window.location.assign triggers the browser download manager for attachment responses.
    if (isMobile) {
        if (typeof showToast === 'function') {
            showToast(isIOS
                ? 'Opening file… if it plays, use Share → Save to Files'
                : 'Starting download… check notification bar',
                'info', 4000);
        }
        // Same-tab navigation is the most reliable on mobile Chrome/Safari
        window.location.assign(absolute);
        return Promise.resolve();
    }

    // DESKTOP: try anchor download first, then optional blob for small files
    if (typeof showToast === 'function') showToast('Starting download…', 'info', 2500);
    var a = document.createElement('a');
    a.href = absolute;
    a.download = name;
    a.rel = 'noopener';
    a.style.display = 'none';
    document.body.appendChild(a);
    try { a.click(); } catch (e) { window.open(absolute, '_blank', 'noopener'); }
    setTimeout(function () { try { a.remove(); } catch (e) {} }, 2000);

    // Non-blocking small-file blob assist (desktop only)
    (async function () {
        try {
            var token =
                localStorage.getItem('vision_ai_access_token') ||
                localStorage.getItem('vision_ai_access') ||
                localStorage.getItem('vision_ai_token') ||
                localStorage.getItem('token') || '';
            var headers = { 'Accept': '*/*' };
            if (token) headers['Authorization'] = 'Bearer ' + token;
            var head = await fetch(absolute, { method: 'HEAD', headers: headers, credentials: 'include', cache: 'no-store' });
            var len = parseInt(head.headers.get('Content-Length') || '0', 10);
            if (len > 0 && len < 15 * 1024 * 1024) {
                var res = await fetch(absolute, { method: 'GET', headers: headers, credentials: 'include', cache: 'no-store' });
                if (res.ok) {
                    var blob = new Blob([await res.blob()], { type: 'application/octet-stream' });
                    var obj = URL.createObjectURL(blob);
                    var a2 = document.createElement('a');
                    a2.href = obj;
                    a2.download = name;
                    a2.style.display = 'none';
                    document.body.appendChild(a2);
                    a2.click();
                    setTimeout(function () {
                        try { URL.revokeObjectURL(obj); } catch (e) {}
                        try { a2.remove(); } catch (e) {}
                    }, 4000);
                }
            }
        } catch (e) { /* anchor already used */ }
    })();

    if (typeof showToast === 'function') {
        showToast('Download started — check your Downloads folder', 'success', 3500);
    }
    return Promise.resolve();
}

function bindDownloadLinks(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll(
        'a[href*="/upload/downloads/"], a.dl-file-link, a[data-force-download], button[data-download-url]'
    );
    nodes.forEach(function (el) {
        if (el.dataset.dlBound === '1') return;
        el.dataset.dlBound = '1';
        // Always stamp ?dl=1 on the href so even without JS the server forces attachment
        try {
            var href0 = el.getAttribute('href') || '';
            if (href0 && /\/upload\/downloads\//.test(href0)) {
                var u0 = new URL(href0, window.location.origin);
                u0.searchParams.set('dl', '1');
                el.setAttribute('href', u0.pathname + u0.search);
                el.setAttribute('download', u0.pathname.split('/').pop() || 'download.bin');
            }
        } catch (e) {}
        el.addEventListener('click', function (ev) {
            var href = el.getAttribute('href') || el.getAttribute('data-download-url') || '';
            if (!href || href === '#') return;
            if (!/\/upload\/downloads\//.test(href) && !el.hasAttribute('data-force-download')) return;
            var isMobile = /Android|iPhone|iPad|iPod|Mobile|webOS|BlackBerry/i.test(navigator.userAgent || '') ||
                (window.matchMedia && window.matchMedia('(pointer: coarse)').matches);
            var hrefDl = href;
            try {
                var uu = new URL(href, window.location.origin);
                if (/\/upload\/downloads\//.test(uu.pathname)) {
                    uu.searchParams.set('dl', '1');
                    hrefDl = uu.href;
                }
            } catch (e) {}
            // Mobile: navigate immediately in the same gesture (no async)
            if (isMobile) {
                ev.preventDefault();
                if (typeof showToast === 'function') showToast('Starting download…', 'info', 3000);
                window.location.assign(hrefDl);
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            var suggested = el.getAttribute('download') || el.getAttribute('data-filename') || '';
            forceMobileDownload(hrefDl, suggested).catch(function () {
                window.location.href = hrefDl;
            });
        }, { passive: false });
    });
}

// Re-bind after chat mutations
document.addEventListener('DOMContentLoaded', function () {
    bindDownloadLinks(document);
    try {
        var chat = document.getElementById('chatBox') || document.getElementById('messages');
        if (chat && typeof MutationObserver !== 'undefined') {
            var mo = new MutationObserver(function () { bindDownloadLinks(chat); });
            mo.observe(chat, { childList: true, subtree: true });
        }
    } catch (e) {}
});

// ============================================================
// VOICE INPUT (Web Speech API) + VOICE OUTPUT (speechSynthesis)
// ============================================================
let _recognition = null;
let _listening = false;
let _currentUtterance = null;

function fillPrompt(text) {
    const ta = document.getElementById('message');
    if (!ta) return;
    ta.value = text;
    ta.focus();
    ta.dispatchEvent(new Event('input'));
}

let _micDenied = false;
let _micToastAt = 0;

function _micToast(msg, type, ms) {
    const now = Date.now();
    if (now - _micToastAt < 6000) return;
    _micToastAt = now;
    showToast(msg, type || "error", ms || 9000);
}

function _micSiteHelp() {
    const host = (location && location.hostname) ? location.hostname : 'this site';
    return (
        'Mic blocked for ' + host + '. ' +
        'Click the lock/tune icon LEFT of the address bar → Permissions / Site permissions → Microphone → Allow → Reload. ' +
        '(Edge global Settings → Privacy is NOT enough — it must be allowed for THIS site.)'
    );
}

function _getSpeechRecognition() {
    return (window.vaGetSpeechRecognition ? window.vaGetSpeechRecognition() : null) || window.SpeechRecognition || window.webkitSpeechRecognition || null;
}


function toggleVoiceInput() {
    if (_listening) {
        stopVoiceInput();
        return;
    }
    // Always allow a fresh attempt (user may have just fixed site permission)
    _micDenied = false;
    startVoiceInput();
}

async function startVoiceInput() {
    const ta = document.getElementById('message');
    const status = document.getElementById('voiceStatus');
    const mic = document.getElementById('micBtn');

    // Secure context required (localhost or https)
    if (typeof window.isSecureContext === 'boolean' && !window.isSecureContext) {
        _micToast('Mic only works on HTTPS or localhost.', 'error', 9000);
        return;
    }

    const Rec = _getSpeechRecognition();
    if (!Rec) {
        showToast('Voice input needs Chrome, Edge, or Safari (not Facebook/Telegram in-app browsers).', 'error', 6000);
        return;
    }

    // Do NOT trust Permissions API "denied" alone (Edge often reports denied while site is still promptable).
    // Always call getUserMedia — that is the real site-level permission gate.
    try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            _micToast('This browser cannot access the microphone (mediaDevices missing).', 'error', 8000);
            return;
        }
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
            }
        });
        stream.getTracks().forEach(t => t.stop());
        _micDenied = false;
    } catch (permErr) {
        console.warn('getUserMedia', permErr);
        _micDenied = true;
        const name = (permErr && (permErr.name || permErr.message)) || '';
        if (/NotFound|DevicesNotFound/i.test(name)) {
            _micToast('No microphone found on this device.', 'error', 8000);
        } else if (/NotReadable|TrackStart/i.test(name)) {
            _micToast('Microphone is in use by another app. Close Zoom/Teams and retry.', 'error', 9000);
        } else {
            _micToast(_micSiteHelp(), 'error', 14000);
        }
        return;
    }

    try {
        const rec = new Rec();
        rec.continuous = false;
        rec.interimResults = true;
        rec.maxAlternatives = 1;
        // Prefer user STT lang; en-US is safest default if Urdu pack missing
        let sttLang = localStorage.getItem('vision_ai_stt_lang')
            || localStorage.getItem('vision_ai_voice_lang')
            || 'en-US';
        rec.lang = sttLang;

        let finalText = ta ? ta.value : '';

        rec.onstart = () => {
            _listening = true;
            if (status) { status.hidden = false; status.textContent = 'Listening… tap mic again to stop'; }
            if (mic) mic.classList.add('mic-active');
            showToast('Listening…', 'info', 1500);
        };
        rec.onresult = (event) => {
            let interim = '';
            let piece = finalText;
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const r = event.results[i];
                if (r.isFinal) piece = (piece ? piece + ' ' : '') + r[0].transcript;
                else interim += r[0].transcript;
            }
            finalText = piece;
            if (ta) {
                ta.value = (piece + (interim ? ' ' + interim : '')).trim();
                ta.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };
        rec.onerror = (e) => {
            console.warn('speech error', e);
            if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                _micDenied = true;
                _listening = false;
                _micToast(_micSiteHelp(), 'error', 14000);
                stopVoiceInput();
            } else if (e.error === 'language-not-supported') {
                try {
                    rec.lang = 'en-US';
                    rec.start();
                    showToast('STT language not supported — switched to English', 'info', 3000);
                } catch (_) {
                    showToast('Speech language not supported on this device', 'error');
                    stopVoiceInput();
                }
            } else if (e.error === 'no-speech') {
                showToast('No speech heard — try again closer to the mic', 'info', 2500);
            } else if (e.error !== 'aborted') {
                showToast('Voice error: ' + e.error, 'error');
                stopVoiceInput();
            }
        };
rec.onend = () => {
            // Do not auto-restart if denied or user stopped — prevents toast spam
            if (_micDenied || !_listening) {
                stopVoiceInput();
                return;
            }
            stopVoiceInput();
        };
        _recognition = rec;
        rec.start();
    } catch (err) {
        showToast('Could not start microphone: ' + (err && err.message ? err.message : err), 'error');
        stopVoiceInput();
    }
}


function stopVoiceInput() {
    _listening = false;
    try { if (_recognition) _recognition.stop(); } catch (_) {}
    _recognition = null;
    const status = document.getElementById('voiceStatus');
    const mic = document.getElementById('micBtn');
    if (status) status.hidden = true;
    if (mic) mic.classList.remove('mic-active');
}

function _detectSpeechLang(text) {
    const t = text || '';
    // Prefer user preference when set
    const pref = localStorage.getItem('vision_ai_tts_lang')
        || localStorage.getItem('vision_ai_voice_lang');
    if (pref) return pref;
    // Script detection for common languages
    if (/[؀-ۿ]/.test(t)) return 'ur-PK';          // Arabic script → Urdu default (also works for ar)
    if (/[ऀ-ॿ]/.test(t)) return 'hi-IN';          // Devanagari → Hindi
    if (/[\u0E00-\u0E7F]/.test(t)) return 'th-TH'; // Thai
    if (/[\u0600-\u06FF]/.test(t) && /[\u064B-\u065F]/.test(t)) return 'ar-SA';
    if (/[\u4E00-\u9FFF]/.test(t)) return 'zh-CN'; // Chinese
    if (/[\u3040-\u30FF]/.test(t)) return 'ja-JP'; // Japanese
    if (/[\uAC00-\uD7AF]/.test(t)) return 'ko-KR'; // Korean
    if (/[\u0400-\u04FF]/.test(t)) return 'ru-RU'; // Cyrillic
    if (/[àâçéèêëîïôùûü]/i.test(t) && /\b(le|la|les|des|une|est)\b/i.test(t)) return 'fr-FR';
    if (/[äöüß]/i.test(t)) return 'de-DE';
    if (/[ñáéíóú¿¡]/i.test(t)) return 'es-ES';
    return 'en-US';
}

function speakMessage(btn) {
    if (!window.speechSynthesis) {
        showToast('Speech not supported in this browser. Use Chrome or Edge.', 'error');
        return;
    }
    // Toggle off if already speaking
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        document.querySelectorAll('.speak-btn.speaking').forEach(b => b.classList.remove('speaking'));
        if (btn && btn.classList.contains('speaking')) {
            btn.classList.remove('speaking');
            return;
        }
    }

    // Find message bubble: actual DOM uses .message-bubble
    let bubble = null;
    if (btn) {
        bubble = btn.closest('.message-bubble')
            || btn.closest('.message-row')
            || btn.closest('.message, .ai-msg, .msg-ai, .bubble');
    }
    let text = '';
    if (bubble) {
        // Prefer markdown body only (skip buttons / badges)
        const body = bubble.querySelector('.markdown-content')
            || bubble.querySelector('.msg-fs-body')
            || bubble;
        const clone = body.cloneNode(true);
        clone.querySelectorAll('button, .msg-actions, .msg-action-btn, .speak-btn, .model-used, script, style').forEach(n => n.remove());
        text = (clone.innerText || clone.textContent || '').trim();
        // Strip common UI chrome
        text = text.replace(/^\s*(Copy|Speak|Height|Width|Full|Narrow|Collapse)\s*/gim, '').trim();
    }
    if (!text) {
        // Last resort: any text in the row
        const row = btn && btn.closest('.message-row');
        if (row) text = (row.innerText || '').replace(/Copy|Speak|Height|Width|Full/g, '').trim();
    }
    if (!text) {
        showToast('Nothing to read — no message text found', 'info');
        return;
    }

    // Chrome: voices often empty until loaded
    const voices = window.speechSynthesis.getVoices() || [];
    const lang = _detectSpeechLang(text);
    const u = new SpeechSynthesisUtterance(text.slice(0, 12000));
    u.lang = lang;
    u.rate = 0.95;
    u.pitch = 1;
    const langBase = (lang || 'en').split('-')[0].toLowerCase();
    let match = voices.find(v => (v.lang || '') === lang)
        || voices.find(v => (v.lang || '').toLowerCase().startsWith(langBase + '-'))
        || voices.find(v => (v.lang || '').toLowerCase().startsWith(langBase))
        || voices.find(v => /urdu|pakistan/i.test(v.name || ''))
        || voices.find(v => /arabic/i.test(v.name || '') && langBase === 'ur')
        || voices.find(v => /hindi/i.test(v.name || '') && (langBase === 'ur' || langBase === 'hi'));
    if (!match && voices.length) match = voices[0];
    if (match) {
        u.voice = match;
        if (!u.lang) u.lang = match.lang || lang;
    }
    if (langBase === 'ur') {
        const hasUr = voices.some(v =>
            /^ur/i.test(v.lang || '') || /urdu|pakistan/i.test(v.name || '')
        );
        if (!hasUr) {
            showToast(
                'Urdu system voice not found. Install Urdu language pack in phone/PC settings for better speech.',
                'info',
                7000
            );
        }
        u.rate = 0.9;
    }
    if (!voices.length) {
        window.speechSynthesis.onvoiceschanged = function () {
            window.speechSynthesis.cancel();
            speakMessage(btn);
        };
        window.speechSynthesis.getVoices();
    }

    u.onstart = () => { if (btn) btn.classList.add('speaking'); };
    u.onend = () => { if (btn) btn.classList.remove('speaking'); };
    u.onerror = (e) => {
        console.warn('speak error', e);
        if (btn) btn.classList.remove('speaking');
        showToast('Speak failed: ' + (e.error || 'unknown'), 'error');
    };

    // Cancel any queue then speak (Chrome quirk)
    window.speechSynthesis.cancel();
    setTimeout(() => window.speechSynthesis.speak(u), 50);
}


function stopSpeaking() {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    document.querySelectorAll('.speak-btn.speaking').forEach(b => b.classList.remove('speaking'));
}

window.fillPrompt = fillPrompt;
window.toggleVoiceInput = toggleVoiceInput;
window.startVoiceInput = startVoiceInput;
window.stopVoiceInput = stopVoiceInput;
window.speakMessage = speakMessage;
window.stopSpeaking = stopSpeaking;

window.sendMessage = sendMessage;
window.renderUserProfile = function() {
  renderUserProfile();
  try {
    var f = document.getElementById('accountArea');
    if (f) f._profileBound = false;
    if (window.ProfileController && window.ProfileController.bind) window.ProfileController.bind();
  } catch (e) {}
};
document.addEventListener('DOMContentLoaded', function(){ try { setUserAvatarGender(getUserAvatarGender()); } catch(e){} });
window.checkAuth = checkAuth;
window.performLogout = performLogout;
window.updateStatus = updateStatus;
window.updateThemeIcon = updateThemeIcon;
window.toggleTheme = toggleTheme;
window.renderFilePreview = renderFilePreview;
window.removeSelectedFile = removeSelectedFile;
window.toggleHelpModal = toggleHelpModal;
window.toggleFavorite = toggleFavorite;
window.toggleFavorites = toggleFavorites;
window.copyPrompt = copyPrompt;
window.copyAndChat = copyAndChat;
window.filterByCategory = filterByCategory;
window.handleSearchInput = handleSearchInput;
window.clearSearch = clearSearch;
window.showRecentPrompts = showRecentPrompts;
window.filterByTag = filterByTag;
window.renderTagChips = renderTagChips;

console.log('👁️ Vision AI v4.4.0 - Ready');
// Prefetch voices for Urdu/Arabic TTS
if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = function() { window.speechSynthesis.getVoices(); };
    try { window.speechSynthesis.getVoices(); } catch (_) {}
}

(function preloadSpeechVoices() {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.getVoices();
    window.speechSynthesis.onvoiceschanged = function () {
        window.speechSynthesis.getVoices();
    };
})();


(function restoreModelSelector() {
  function run() {
    const sel = document.getElementById('modelSelector');
    if (!sel) return;
    const saved = localStorage.getItem('vision_ai_model');
    if (saved) {
      const opt = [...sel.options].find(o => o.value === saved);
      if (opt) sel.value = saved;
    }
    sel.addEventListener('change', () => localStorage.setItem('vision_ai_model', sel.value));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
})();


// Reset mic deny flag when user returns (after changing site permissions)
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && typeof _micDenied !== 'undefined') {
    _micDenied = false;
  }
});


function downloadCurrentChat() {
  try {
    const chat = window.currentChat || window.chat || null;
    let text = "";
    if (chat && Array.isArray(chat.messages) && chat.messages.length) {
      text = chat.messages.map(function(m) {
        const role = (m.role || m.sender || "msg").toUpperCase();
        return role + ":\n" + (m.text || m.content || "") + "\n";
      }).join("\n");
    } else {
      const out = document.getElementById("chatOutput") || document.getElementById("output");
      if (out) text = out.innerText || out.textContent || "";
    }
    if (!text || !String(text).trim()) {
      if (typeof showToast === "function") showToast("Nothing to download yet", "info", 2000);
      return;
    }
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "vision-ai-chat.txt";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function() { URL.revokeObjectURL(url); }, 1500);
    if (typeof showToast === "function") showToast("Chat download started", "success", 2000);
  } catch (e) {
    console.error(e);
    if (typeof showToast === "function") showToast("Download failed", "error", 3000);
  }
}

window.downloadCurrentChat = downloadCurrentChat;

function maybeHonestNoImage(userText, images) {
  try {
    const wants = /\b(image|picture|photo|draw|generate|illustration|1080p|logo)\b/i.test(userText || '');
    if (!wants) return;
    if (images && images.length) return;
    const output = ensureChatOutput();
    if (!output) return;
    const tip = document.createElement('div');
    tip.className = 'message-row ai';
    tip.innerHTML = '<div class="message-bubble" style="border:1px solid rgba(248,113,113,0.45)"><strong>No image was generated.</strong> Text-only reply is not a picture. Open <a href="/boost.html">/boost.html</a>, keep Colab GPU online (warmed), ensure HF_TOKEN, then try a shorter prompt.</div>';
    output.appendChild(tip);
  } catch (e) {}
}
window.maybeHonestNoImage = maybeHonestNoImage;


/* Theme presets */
function applyThemePreset(name) {
  const n = (name || 'default').trim();
  const val = (n === 'default') ? '' : n;
  const root = document.documentElement;
  root.setAttribute('data-theme-preset', val || 'default');
  if (document.body) document.body.setAttribute('data-theme-preset', val || 'default');
  try { localStorage.setItem('vision_theme_preset', n || 'default'); } catch (e) {}
  const lightPresets = ['soft-sepia', 'sand'];
  var mode = root.getAttribute('data-theme') || 'dark';
  if (lightPresets.indexOf(n) >= 0) {
    mode = 'light';
  }
  root.setAttribute('data-theme', mode);
  if (document.body) document.body.setAttribute('data-theme', mode);
  root.style.colorScheme = mode === 'light' ? 'light' : 'dark';
  try { localStorage.setItem('vision_ai_theme', mode); } catch (e) {}
  // Force token sync from computed accent after CSS applies
  try {
    requestAnimationFrame(function () {
      var cs = getComputedStyle(root);
      var acc = cs.getPropertyValue('--accent').trim();
      if (acc) {
        root.style.setProperty('--color-accent', acc);
        root.style.setProperty('--primary-cyan', acc);
      }
      root.style.setProperty('--theme-tick', String(Date.now()));
    });
  } catch (e2) {}
  if (typeof updateThemeIcon === 'function') {
    try { updateThemeIcon(mode); } catch (e3) {}
  }
  if (typeof syncThemePickerUI === 'function') {
    try { syncThemePickerUI(); } catch (e4) {}
  }
}
function toggleGlassMode(level) {
  const levels = ['off', 'soft', 'strong'];
  let next = level;
  if (!next) {
    const cur = document.documentElement.getAttribute('data-glass') || 'strong';
    const i = levels.indexOf(cur);
    next = levels[(i + 1) % levels.length];
  }
  document.documentElement.setAttribute('data-glass', next);
  try { localStorage.setItem('vision_glass_mode', next); } catch (e) {}
  if (typeof showToast === 'function') showToast('Glass: ' + next, 'info', 1200);
  return next;
}
window.toggleGlassMode = toggleGlassMode;

function initThemePreset() {
  try {
    const n = localStorage.getItem('vision_theme_preset') || 'humanly';
    applyThemePreset(n);
  } catch (e) {}
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initThemePreset);
} else { initThemePreset(); }
window.applyThemePreset = applyThemePreset;


/* Theme picker UI */
function initThemePicker() {
  var root = document.getElementById("themePicker");
  var btn = document.getElementById("themePickerBtn");
  if (!root || !btn) return;
  var panel = root.querySelector(".theme-picker-panel");
  function closePicker() {
    root.classList.remove("open");
    btn.setAttribute("aria-expanded", "false");
  }
  function openPicker() {
    root.classList.add("open");
    btn.setAttribute("aria-expanded", "true");
    // mark selected
    var cur = (localStorage.getItem("vision_theme_preset") || "humanly");
    root.querySelectorAll(".theme-swatch").forEach(function(sw) {
      sw.classList.toggle("is-selected", sw.getAttribute("data-preset") === cur);
    });
    var mode = localStorage.getItem("vision_ai_theme") || "dark";
    root.querySelectorAll(".theme-mode-row button").forEach(function(b) {
      b.classList.toggle("is-active", b.getAttribute("data-mode") === mode);
    });
  }
  btn.addEventListener("click", function(e) {
    e.preventDefault();
    e.stopPropagation();
    if (root.classList.contains("open")) closePicker(); else openPicker();
  });
  if (panel) {
    panel.addEventListener("click", function(e) { e.stopPropagation(); });
  }
  root.querySelectorAll(".theme-mode-row button").forEach(function(b) {
    b.addEventListener("click", function(e) {
      e.stopPropagation();
      var mode = b.getAttribute("data-mode") || "dark";
      try { localStorage.setItem("vision_ai_theme", mode); } catch (err) {}
      if (typeof applyTheme === "function") applyTheme(mode);
      root.querySelectorAll(".theme-mode-row button").forEach(function(x) {
        x.classList.toggle("is-active", x === b);
      });
    });
  });
  root.querySelectorAll(".theme-swatch").forEach(function(sw) {
    sw.addEventListener("click", function(e) {
      e.stopPropagation();
      var preset = sw.getAttribute("data-preset") || "default";
      if (typeof applyThemePreset === "function") applyThemePreset(preset);
      if (preset === "soft-sepia" || preset === "sand") {
        try { localStorage.setItem("vision_ai_theme", "light"); } catch (err) {}
        if (typeof applyTheme === "function") applyTheme("light");
      } else if (["humanly","nord","ocean","forest","violet","rose","midnight","sunset","default","high-contrast","emerald","frost","ember"].indexOf(preset) >= 0) {
        try { localStorage.setItem("vision_ai_theme", "dark"); } catch (err) {}
        if (typeof applyTheme === "function") applyTheme("dark");
      }
      root.querySelectorAll(".theme-swatch").forEach(function(x) {
        x.classList.toggle("is-selected", x === sw);
      });
      closePicker();
      if (typeof showToast === "function") showToast("Theme: " + preset, "info", 1500);
    });
  });
  document.addEventListener("click", function() { closePicker(); });
  document.addEventListener("keydown", function(e) {
    if (e.key === "Escape") closePicker();
  });
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initThemePicker);
} else { initThemePicker(); }

// Default preset: humanly if none saved
(function() {
  try {
    if (!localStorage.getItem("vision_theme_preset")) {
      localStorage.setItem("vision_theme_preset", "humanly");
    }
  } catch (e) {}
})();

(function(){
  function syncSidebarAttr(){
    try {
      var sb = document.getElementById('sidebar');
      var open = (typeof isDesktopViewport === 'function' ? isDesktopViewport() : window.innerWidth > 900) || (sb && sb.classList.contains('open-mobile'));
      document.documentElement.setAttribute('data-sidebar', open ? 'open' : 'closed');
        /* keep search title visible */
    } catch(e){}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', syncSidebarAttr);
  else syncSidebarAttr();
  /* syncSidebarAttr via visionSidebarController */
})();


// Sync browser tab title + meta with live server version
(function syncLiveVersion(){
  function apply(ver) {
    if (!ver) return;
    try {
      document.title = "Vision AI v" + ver + " — Chat";
      var m = document.querySelector('meta[name="app-version"]');
      if (m) m.setAttribute("content", ver);
      window.__VISION_VERSION__ = ver;
    } catch (e) {}
  }
  function run() {
    fetch("/api/version").then(function(r){ return r.json(); }).then(function(d){
      apply(d.version || d.current);
    }).catch(function(){ apply("3.2.0"); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", run);
  else run();
})();


// Escape always dismisses Prompt Studio overlay
document.addEventListener('keydown', function (ev) {
  if (ev.key === 'Escape' && typeof closePromptStudio === 'function') closePromptStudio();
});

// Header ⋮ more menu
(function initHeaderMore() {
  function bind() {
    var btn = document.getElementById('headerMoreBtn');
    var panel = document.getElementById('headerMorePanel');
    if (!btn || !panel || btn.dataset.bound) return;
    btn.dataset.bound = '1';
    function closeMore() {
      panel.setAttribute('hidden', '');
      btn.setAttribute('aria-expanded', 'false');
    }
    function openMore() {
      panel.removeAttribute('hidden');
      btn.setAttribute('aria-expanded', 'true');
      try {
        panel.style.right = '0';
        panel.style.left = 'auto';
        panel.style.top = 'calc(100% + 6px)';
        panel.style.bottom = 'auto';
        var rect = btn.getBoundingClientRect();
        if (rect.bottom + 280 > window.innerHeight) {
          panel.style.top = 'auto';
          panel.style.bottom = 'calc(100% + 6px)';
        }
        if (rect.right - 240 < 8) {
          panel.style.left = '0';
          panel.style.right = 'auto';
        }
      } catch (e) {}
    }
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (panel.hasAttribute('hidden')) openMore(); else closeMore();
    });
    panel.addEventListener('click', function (e) { e.stopPropagation(); });
    document.addEventListener('click', closeMore);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeMore();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();

/* ===== v3.3.0 performance helpers ===== */
(function perfShell() {
  function debounce(fn, ms) {
    var t;
    return function () {
      var ctx = this, args = arguments;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(ctx, args); }, ms);
    };
  }
  // Avoid layout thrash on rotate/resize
  /* sidebar resize: visionSidebarController */

  // Smooth scroll chat to bottom without forced reflow storms
  window.scrollChatToBottom = function (force) {
    var el = document.getElementById('chatOutput');
    if (!el) return;
    requestAnimationFrame(function () {
      try {
        if (force || el.scrollHeight - el.scrollTop - el.clientHeight < 180) {
          el.scrollTop = el.scrollHeight;
        }
      } catch (e) {}
    });
  };

  // Passive touch listeners for chat scroll
  document.addEventListener('DOMContentLoaded', function () {
    var chat = document.getElementById('chatOutput');
    if (chat) {
      chat.addEventListener('scroll', function () {}, { passive: true });
    }
    // Prefetch heavy routes when idle
    if ('requestIdleCallback' in window) {
      requestIdleCallback(function () {
        ['/settings.html', '/upgrade.html', '/boost'].forEach(function (href) {
          try {
            var l = document.createElement('link');
            l.rel = 'prefetch';
            l.href = href;
            document.head.appendChild(l);
          } catch (e) {}
        });
      }, { timeout: 4000 });
    }
  });
})();



/* Single sidebar resize controller — drawer ≤900px / desktop ≥901px */
(function visionSidebarController(){
  var timer = null;
  var lastMode = null;

  function mode() {
    return (typeof isDrawerViewport === 'function' && isDrawerViewport()) ? 'drawer' : 'desktop';
  }

  function setOverlay(active) {
    var ov = document.getElementById('sidebar-overlay');
    if (!ov) return;
    ov.classList.toggle('active', !!active);
    ov.style.display = active ? 'block' : 'none';
    ov.style.pointerEvents = active ? 'auto' : 'none';
  }

  function reconcile() {
    try {
      var m = mode();
      var sb = document.getElementById('sidebar');
      if (!sb) return;
      if (m === 'desktop') {
        sb.classList.remove('open-mobile');
        document.body.classList.remove('sidebar-open');
        setOverlay(false);
        document.documentElement.setAttribute(
          'data-sidebar',
          (sb.classList.contains('rail-mode') || sb.classList.contains('collapsed-true')) ? 'closed' : 'open'
        );
      } else {
        var open = sb.classList.contains('open-mobile');
        document.body.classList.toggle('sidebar-open', open);
        setOverlay(open);
        document.documentElement.setAttribute('data-sidebar', open ? 'open' : 'closed');
      }
      lastMode = m;
    } catch (e) {}
  }

  function openSidebar() {
    var sb = document.getElementById('sidebar');
    if (!sb) return;
    if (mode() === 'drawer') {
      sb.classList.add('open-mobile');
    } else {
      sb.classList.remove('rail-mode');
      sb.classList.remove('collapsed-true');
    }
    reconcile();
  }
  function closeSidebar() {
    var sb = document.getElementById('sidebar');
    if (!sb) return;
    sb.classList.remove('open-mobile');
    document.body.classList.remove('sidebar-open');
    setOverlay(false);
    reconcile();
  }
  function toggleSidebar() {
    var sb = document.getElementById('sidebar');
    if (!sb) return;
    if (mode() === 'drawer') {
      if (sb.classList.contains('open-mobile')) closeSidebar();
      else openSidebar();
    } else {
      // Desktop collapse — never touch overlay / body.sidebar-open
      document.body.classList.remove('sidebar-open');
      setOverlay(false);
      sb.classList.remove('open-mobile');
      var collapsing = !sb.classList.contains('collapsed-true');
      sb.classList.toggle('rail-mode', collapsing);
      sb.classList.toggle('collapsed-true', collapsing);
      var toolbar = document.getElementById('collapsedToolbar');
      if (toolbar) toolbar.classList.toggle('active', collapsing);
      reconcile();
    }
  }
  // Single public API (v4.9: consolidated, proxies defined at file start)
  window.__vaSidebar = {
    open: openSidebar,
    close: closeSidebar,
    toggle: toggleSidebar,
    reconcile: reconcile,
    mode: mode
  };
  // Note: window.openSidebar, window.closeSidebar, window.toggleSidebar
  // are already defined as proxies at lines 295-300 above; no re-export needed
  window.reconcileSidebarLayout = reconcile;
  window.forceDesktopSidebarCleanup = function () {
    if (typeof isDesktopViewport === 'function' && isDesktopViewport()) reconcile();
  };

  window.addEventListener('resize', function () {
    clearTimeout(timer);
    timer = setTimeout(reconcile, 100);
  }, { passive: true });
  window.addEventListener('orientationchange', function () {
    setTimeout(reconcile, 200);
  }, { passive: true });

  function boot() { lastMode = mode(); reconcile(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();



/* v4.4 — Show more for long AI answers (no forced nested scrollbar) */
(function () {
  function enhanceLongMessages(root) {
    try {
      (root || document).querySelectorAll(".msg-long-body:not([data-expand-ready])").forEach(function (el) {
        el.setAttribute("data-expand-ready", "1");
        if (el.classList.contains("msg-expanded-height")) return;
        el.classList.add("msg-collapsed");
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "msg-action-btn msg-show-more";
        btn.textContent = "Show more";
        btn.setAttribute("aria-label", "Expand full response");
        btn.addEventListener("click", function (e) {
          e.stopPropagation();
          var expanded = el.classList.toggle("msg-expanded-height");
          el.classList.toggle("msg-collapsed", !expanded);
          btn.textContent = expanded ? "Show less" : "Show more";
        });
        var tools = el.parentElement && el.parentElement.querySelector(".message-actions, .msg-actions, .ai-actions");
        if (tools) tools.appendChild(btn);
        else el.insertAdjacentElement("afterend", btn);
      });
    } catch (e) {}
  }
  window.enhanceLongMessages = enhanceLongMessages;
  var _mo = new MutationObserver(function () { enhanceLongMessages(document.getElementById("chatOutput")); });
  if (document.getElementById("chatOutput")) {
    _mo.observe(document.getElementById("chatOutput"), { childList: true, subtree: true });
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      var out = document.getElementById("chatOutput");
      if (out) _mo.observe(out, { childList: true, subtree: true });
    });
  }
})();


/* Migrate deprecated model IDs stored in localStorage (once) */
(function () {
  /* Backend /api/models is authoritative; local map is fallback only */
  var fallbackMap = {
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
    "gemma2-9b-it": "openai/gpt-oss-20b",
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro"
  };

  function applyMap(map) {
    if (!map) return;
    try {
      var keys = ["vision_ai_model", "vision_selected_model", "modelSelector"];
      keys.forEach(function (k) {
        var v = localStorage.getItem(k);
        if (v && map[v]) {
          localStorage.setItem(k, map[v]);
          if (!sessionStorage.getItem("va_model_migrated_toast")) {
            sessionStorage.setItem("va_model_migrated_toast", "1");
            setTimeout(function () {
              if (typeof showToast === "function") showToast("Model updated: " + map[v], "info", 3500);
            }, 1200);
          }
        }
      });
      var sel = document.getElementById("modelSelector");
      if (sel && map[sel.value]) sel.value = map[sel.value];
    } catch (e) {}
  }

  applyMap(fallbackMap);

  try {
    var token = (typeof getAccessToken === "function" && getAccessToken()) || localStorage.getItem("vision_ai_token") || "";
    var headers = { Accept: "application/json" };
    if (token) headers["Authorization"] = "Bearer " + token;
    fetch("/api/models", { headers: headers, credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        var map = Object.assign({}, fallbackMap, data.migrations || {});
        window.__VA_MODEL_MIGRATIONS = map;
        window.__VA_MODEL_SHUTDOWN = data.shutdown || [];
        applyMap(map);
      })
      .catch(function () {});
  } catch (e) {}
})();

/* Repair common UTF-8 mojibake in AI text (e.g. â€¢ → •) */
function fixMojibake(s) {
  if (!s || typeof s !== "string") return s;
  try {
    if (/â€|Ã.|Â./.test(s)) {
      return s
        .replace(/â€¢/g, "•")
        .replace(/â€”/g, "—")
        .replace(/â€“/g, "–")
        .replace(/â€™/g, "'")
        .replace(/â€œ/g, '"')
        .replace(/â€/g, '"')
        .replace(/Ã—/g, "×")
        .replace(/Â /g, " ");
    }
  } catch (e) {}
  return s;
}


/* v4.8 empty-state suggestion chips */
(function () {
  function bindSuggestions() {
    var grid = document.getElementById("suggestionGrid");
    if (!grid || grid._bound) return;
    grid._bound = true;
    grid.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t || !t.classList || !t.classList.contains("suggestion-chip")) return;
      var prompt = t.getAttribute("data-prompt") || t.textContent || "";
      var ta = document.getElementById("message");
      if (ta) {
        ta.value = prompt;
        ta.focus();
        try { ta.dispatchEvent(new Event("input", { bubbles: true })); } catch (e) {}
      }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bindSuggestions);
  else bindSuggestions();
})();


function syncThemePickerUI() {
  try {
    var root = document.getElementById("themePicker");
    if (!root) return;
    var cur = localStorage.getItem("vision_theme_preset") || document.documentElement.getAttribute("data-theme-preset") || "humanly";
    var mode = document.documentElement.getAttribute("data-theme") || "dark";
    root.querySelectorAll(".theme-swatch").forEach(function (sw) {
      sw.classList.toggle("is-selected", (sw.getAttribute("data-preset") || "") === cur);
    });
    root.querySelectorAll("[data-mode]").forEach(function (b) {
      b.classList.toggle("is-active", (b.getAttribute("data-mode") || "") === mode);
    });
  } catch (e) {}
}
window.syncThemePickerUI = syncThemePickerUI;


(function composerIdleBoot() {
  function hideStop() {
    var stop = document.getElementById("stopBtn");
    if (stop) {
      stop.hidden = true;
      stop.setAttribute("hidden", "");
      stop.style.display = "none";
    }
    var send = document.getElementById("sendBtn");
    if (send) send.hidden = false;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", hideStop);
  else hideStop();
  window.ensureComposerIdle = hideStop;
})();

(function () {
  if (window.__vaLogoutClickBound) return;
  window.__vaLogoutClickBound = true;
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    if (!t || !t.closest) return;
    var el = t.closest("[data-action='logout'], .logout-item, #profileLogoutBtn");
    if (!el) return;
    ev.preventDefault();
    ev.stopPropagation();
    if (window.closeProfileDropdown) window.closeProfileDropdown();
    if (window.performLogout) window.performLogout();
    else if (window.VisionAuth && VisionAuth.logout) VisionAuth.logout({ confirm: true });
    else { try { localStorage.clear(); } catch (e) {} location.href = '/login.html'; }
  }, true);
})();
