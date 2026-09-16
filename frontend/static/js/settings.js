
/* v5.6.2 — server preferences sync */
const PREFS_CACHE_KEY = 'vision_ai_preferences';
const LEGACY_KEY_MAP = {
  vision_ai_theme: ['appearance', 'theme_mode'],
  vision_theme_preset: ['appearance', 'theme_preset'],
  vision_density: ['appearance', 'density'],
  vision_reduced_motion: ['appearance', 'reduced_motion'],
  vision_chat_lang: ['chat', 'chat_language'],
  vision_enter_send: ['chat', 'enter_to_send'],
  vision_stt_lang: ['voice', 'stt_language'],
  vision_tts_lang: ['voice', 'tts_language'],
  vision_auto_speak: ['voice', 'auto_speak'],
};

function migrateLegacyLocalKeys() {
  try {
    const cached = JSON.parse(localStorage.getItem(PREFS_CACHE_KEY) || 'null');
    if (cached && cached.appearance) return cached;
    const migrated = { appearance: {}, chat: {}, voice: {}, notifications: {}, privacy: {} };
    Object.keys(LEGACY_KEY_MAP).forEach(function (k) {
      const v = localStorage.getItem(k);
      if (v === null) return;
      const path = LEGACY_KEY_MAP[k];
      let val = v;
      if (v === '1' || v === '0') val = v === '1';
      migrated[path[0]][path[1]] = val;
    });
    localStorage.setItem(PREFS_CACHE_KEY, JSON.stringify(migrated));
    return migrated;
  } catch (e) { return null; }
}

function cachePrefs(prefs) {
  try { localStorage.setItem(PREFS_CACHE_KEY, JSON.stringify(prefs)); } catch (e) {}
  try {
    if (prefs.appearance) {
      if (prefs.appearance.theme_mode) localStorage.setItem('vision_ai_theme', prefs.appearance.theme_mode);
      if (prefs.appearance.theme_preset) localStorage.setItem('vision_theme_preset', prefs.appearance.theme_preset);
      if (prefs.appearance.density) localStorage.setItem('vision_density', prefs.appearance.density);
      document.documentElement.setAttribute('data-density', prefs.appearance.density || 'comfortable');
      document.documentElement.setAttribute('data-reduced-motion', prefs.appearance.reduced_motion ? '1' : '0');
    }
    if (prefs.chat) {
      if (prefs.chat.chat_language) localStorage.setItem('vision_chat_lang', prefs.chat.chat_language);
      if (typeof prefs.chat.enter_to_send === 'boolean') localStorage.setItem('vision_enter_send', prefs.chat.enter_to_send ? '1' : '0');
    }
    if (prefs.voice) {
      if (prefs.voice.stt_language) localStorage.setItem('vision_stt_lang', prefs.voice.stt_language);
      if (prefs.voice.tts_language) localStorage.setItem('vision_tts_lang', prefs.voice.tts_language);
      if (typeof prefs.voice.auto_speak === 'boolean') localStorage.setItem('vision_auto_speak', prefs.voice.auto_speak ? '1' : '0');
    }
  } catch (e) {}
}

async function fetchServerPrefs() {
  const res = await authedFetch('/api/settings');
  if (!res.ok) throw new Error('settings ' + res.status);
  return res.json();
}

async function patchServerPrefs(section, patch) {
  const body = {};
  body[section] = patch;
  const res = await authedFetch('/api/settings', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err.detail && err.detail.error && err.detail.error.message) || err.detail || 'Save failed');
  }
  const prefs = await res.json();
  cachePrefs(prefs);
  return prefs;
}

// ============================================================
// VISION AI v3.2.0 - SETTINGS LOGIC (Production Ready)
// ============================================================

// ============================================================
// 🛡️ SECURITY & UTILITIES
// ============================================================

// Prevent XSS in all user-generated content
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Validate email format
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Format date safely
function fmtDate(iso) {
    if (!iso) return '—';
    try {
        const date = new Date(iso);
        if (isNaN(date.getTime())) return iso;
        return date.toLocaleDateString(undefined, { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    } catch {
        return iso;
    }
}

// ============================================================
// 🌙 THEME MANAGEMENT
// ============================================================

// Get current theme preference with fallback
function getThemePreference() {
    const stored = localStorage.getItem('vision_ai_theme');
    if (stored) return stored;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

// Apply theme with proper icon update
function applyTheme(theme) {
    const toggleBtn = document.getElementById('themeToggle');
    
    if (theme === 'system') {
        const systemTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', systemTheme);
        localStorage.setItem('vision_ai_theme', 'system');
        if (toggleBtn) toggleBtn.textContent = '💻';
    } else if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('vision_ai_theme', 'light');
        if (toggleBtn) toggleBtn.textContent = '☀️';
    } else {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('vision_ai_theme', 'dark');
        if (toggleBtn) toggleBtn.textContent = '🌙';
    }
}

// Toggle between themes
function toggleTheme() {
    const current = localStorage.getItem('vision_ai_theme') || 'dark';
    if (current === 'dark') applyTheme('light');
    else if (current === 'light') applyTheme('system');
    else applyTheme('dark');
    showToast(`Theme switched to ${current === 'dark' ? 'light' : current === 'light' ? 'system' : 'dark'}`, 'success');
}

// Listen for system theme changes
if (getThemePreference() === 'system') {
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
        applyTheme('system');
    });
}

// ============================================================
// 🔐 AUTHENTICATION & TOKEN MANAGEMENT
// ============================================================

function getAccessToken() { 
    return localStorage.getItem('vision_ai_access_token'); 
}

function getRefreshToken() { 
    return localStorage.getItem('vision_ai_refresh_token'); 
}

function clearTokens() {
    localStorage.removeItem('vision_ai_access_token');
    localStorage.removeItem('vision_ai_refresh_token');
    localStorage.removeItem('vision_ai_user');
    localStorage.removeItem('vision_ai_plan');
}

// Authenticated fetch with automatic token refresh
async function authedFetch(url, options = {}) {
    let token = getAccessToken();
    if (!token) {
        window.location.href = '/login.html';
        return;
    }
    
    let headers = { 
        ...options.headers, 
        'Authorization': `Bearer ${token}` 
    };
    
    let res = await fetch(url, { ...options, headers });
    
    if (res.status === 401) {
        const refreshToken = getRefreshToken();
        if (refreshToken) {
            try {
                const r = await fetch('/auth/refresh', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken }),
                });
                if (r.ok) {
                    const data = await r.json();
                    localStorage.setItem('vision_ai_access_token', data.access_token);
                    if (data.refresh_token) {
                        localStorage.setItem('vision_ai_refresh_token', data.refresh_token);
                    }
                    headers['Authorization'] = `Bearer ${data.access_token}`;
                    res = await fetch(url, { ...options, headers });
                    return res;
                }
            } catch (e) {
                console.error('Token refresh failed:', e);
            }
        }
        clearTokens();
        window.location.href = '/login.html';
        return;
    }
    return res;
}

// ============================================================
// 🚀 INITIALIZATION
// ============================================================

let initAttempted = false;

async function init() {
    if (initAttempted) return;
    initAttempted = true;

    const token = getAccessToken();
    if (!token) {
        window.location.href = '/login.html';
        return;
    }
    
    // Apply theme
    const theme = getThemePreference();
    applyTheme(theme);
    
    // Setup theme toggle
    const toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleTheme);
    }

    // Load user data
    try {
        const [meRes, planRes] = await Promise.all([
            authedFetch('/auth/me'),
            authedFetch('/upgrade/me'),
        ]);
        
        if (meRes.status === 401) {
            clearTokens();
            window.location.href = '/login.html';
            return;
        }
        
        if (!meRes.ok) {
            throw new Error('Could not load your profile');
        }
        
        const me = await meRes.json();
        const plan = planRes.ok ? await planRes.json() : null;
        migrateLegacyLocalKeys();
        try {
          const serverPrefs = await fetchServerPrefs();
          cachePrefs(serverPrefs);
          if (serverPrefs.appearance && serverPrefs.appearance.theme_mode) {
            applyTheme(serverPrefs.appearance.theme_mode);
          }
        } catch (e) { console.warn('settings sync', e); }
        renderContent(me, plan);
    } catch (err) {
        console.error('Init error:', err);
        const content = document.getElementById('content');
        if (content) {
            content.innerHTML = `
                <div class="settings-card error-state" role="alert">
                    <strong>Unable to load your settings.</strong>
                    <p>${escapeHtml(err.message || 'Please try again.')}</p>
                    <button onclick="window.location.reload()" class="btn btn-primary">Retry</button>
                </div>`;
        }
    }
}

// ============================================================
// 📋 RENDER CONTENT
// ============================================================

function renderContent(me, plan) {
    const planName = plan?.plan_details?.name || me.plan || 'Free';
    const content = document.getElementById('content');
    if (!content) return;

    const displayName = me.full_name || me.username || 'User';
    const initials = displayName.split(/\s+/).map(part => part[0]).join('').toUpperCase().slice(0, 2) || 'U';
    const themePreset = localStorage.getItem('vision_theme_preset') || 'default';
    const themeMode = localStorage.getItem('vision_ai_theme') || 'dark';
    const chatLang = localStorage.getItem('vision_chat_lang') || 'auto';
    const sttLang = localStorage.getItem('vision_stt_lang') || 'en-US';
    const ttsLang = localStorage.getItem('vision_tts_lang') || 'en-US';
    const autoSpeak = localStorage.getItem('vision_auto_speak') === '1';
    const enterSend = localStorage.getItem('vision_enter_send') !== '0';
    const reducedMotion = localStorage.getItem('vision_reduced_motion') === '1';
    const density = localStorage.getItem('vision_density') || 'comfortable';
    const memberSince = me.created_at ? String(me.created_at).slice(0, 10) : '—';

    const langOptions = [
      ['auto','Auto'],['en','English'],['ur','Urdu'],['ar','Arabic'],['hi','Hindi'],
      ['zh','Chinese'],['fr','French'],['de','German'],['es','Spanish'],['pt','Portuguese'],
      ['ja','Japanese'],['ko','Korean'],['tr','Turkish'],['id','Indonesian']
    ].map(([v,l]) => `<option value="${v}"${chatLang===v?' selected':''}>${l}</option>`).join('');

    const sttOptions = [
      'en-US','en-GB','ur-PK','ar-SA','hi-IN','bn-BD','zh-CN','fr-FR','de-DE','es-ES',
      'pt-BR','ru-RU','ja-JP','ko-KR','tr-TR','id-ID','ms-MY','fa-IR','it-IT','nl-NL'
    ].map(v => `<option value="${v}"${sttLang===v?' selected':''}>${v}</option>`).join('');

    content.innerHTML = `
      <section class="profile-hero" aria-label="Profile">
        <div class="profile-hero-avatar" aria-hidden="true">${escapeHtml(initials)}</div>
        <div class="profile-hero-copy">
          <div class="profile-hero-name">${escapeHtml(displayName)}</div>
          <div class="profile-hero-meta">${escapeHtml(me.email || 'No email')} · ${escapeHtml(planName)} · since ${escapeHtml(memberSince)}</div>
        </div>
        <div class="profile-hero-actions">
          <button type="button" class="btn btn-outline" onclick="window.location.href='/usage.html'">Usage</button>
          <button type="button" class="btn btn-outline" onclick="window.location.href='/upgrade.html'">Plan</button>
        </div>
      </section>

      <details class="settings-acc" open>
        <summary>Account<span class="acc-desc">Name, email, password</span></summary>
        <div class="acc-body">
          <div class="setting-row" id="nameRow">
            <div class="label-block">
              <label for="nameInput">Display name</label>
              <span class="hint">Shown in chat and profile</span>
            </div>
            <div id="nameDisplay" style="display:flex;gap:8px;align-items:center">
              <span id="nameText">${escapeHtml(displayName)}</span>
              <button type="button" class="btn-outline" onclick="toggleNameEdit()">Edit</button>
            </div>
            <div id="nameEdit" hidden style="display:none;gap:8px;align-items:center">
              <input type="text" id="nameInput" maxlength="100" value="${escapeHtml(displayName)}" autocomplete="name">
              <button type="button" class="btn btn-primary" onclick="saveName()">Save</button>
              <button type="button" class="btn-outline" onclick="toggleNameEdit()">Cancel</button>
            </div>
          </div>
          <div class="setting-row">
            <div class="label-block"><label>Email</label><span class="hint">Sign-in address</span></div>
            <span>${escapeHtml(me.email || '—')}</span>
          </div>
          <div class="setting-row">
            <div class="label-block"><label>Username</label></div>
            <span>${escapeHtml(me.username || '—')}</span>
          </div>
          <form id="pwForm" class="acc-body" style="padding:0;border:0" onsubmit="return false;">
            <div class="setting-row">
              <div class="label-block"><label for="oldPassword">Current password</label></div>
              <div class="password-wrapper">
                <input type="password" id="oldPassword" autocomplete="current-password" minlength="6">
                <button type="button" class="toggle-password" onclick="togglePw('oldPassword', this)" aria-label="Show password">👁</button>
              </div>
            </div>
            <div class="setting-row">
              <div class="label-block"><label for="newPassword">New password</label><span class="hint">At least 6 characters</span></div>
              <div class="password-wrapper">
                <input type="password" id="newPassword" autocomplete="new-password" minlength="6">
                <button type="button" class="toggle-password" onclick="togglePw('newPassword', this)" aria-label="Show password">👁</button>
              </div>
            </div>
            <div class="card-actions">
              <button type="button" class="btn btn-primary" id="pwSubmitBtn" onclick="changePassword()">Update password</button>
            </div>
            <div id="pwMsg" role="status"></div>
          </form>
        </div>
      </details>

      <details class="settings-acc">
        <summary>Appearance<span class="acc-desc">Theme, density, motion</span></summary>
        <div class="acc-body">
          <div class="setting-row">
            <div class="label-block"><label for="themeModeSelect">Color mode</label></div>
            <select id="themeModeSelect" aria-label="Color mode">
              <option value="dark"${themeMode==='dark'?' selected':''}>Dark</option>
              <option value="light"${themeMode==='light'?' selected':''}>Light</option>
              <option value="system"${themeMode==='system'?' selected':''}>System</option>
            </select>
          </div>
          <div class="setting-row">
            <div class="label-block"><label for="themePresetSelect">Accent preset</label><span class="hint">Subtle palette shift</span></div>
            <select id="themePresetSelect" aria-label="Theme preset">
              <option value="default">Default</option>
              <option value="humanly">Humanly</option>
              <option value="nord">Nord</option>
              <option value="ocean">Ocean</option>
              <option value="forest">Forest</option>
              <option value="violet">Violet</option>
              <option value="high-contrast">High contrast</option>
            </select>
          </div>
          <div class="setting-row">
            <div class="label-block"><label for="densitySelect">Density</label></div>
            <select id="densitySelect">
              <option value="comfortable"${density==='comfortable'?' selected':''}>Comfortable</option>
              <option value="compact"${density==='compact'?' selected':''}>Compact</option>
            </select>
          </div>
          <div class="setting-row">
            <div class="label-block"><label for="reducedMotion">Reduced motion</label><span class="hint">Limit animations</span></div>
            <input type="checkbox" id="reducedMotion"${reducedMotion?' checked':''}>
          </div>
        </div>
      </details>

      <details class="settings-acc">
        <summary>Chat<span class="acc-desc">Language and input</span></summary>
        <div class="acc-body">
          <div class="setting-row">
            <div class="label-block"><label for="chatLang">Reply language</label><span class="hint">Preferred language for answers</span></div>
            <select id="chatLang">${langOptions}</select>
          </div>
          <div class="setting-row">
            <div class="label-block"><label for="enterSend">Enter to send</label><span class="hint">Shift+Enter for new line</span></div>
            <input type="checkbox" id="enterSend"${enterSend?' checked':''}>
          </div>
        </div>
      </details>

      <details class="settings-acc">
        <summary>Voice<span class="acc-desc">Speech input and playback</span></summary>
        <div class="acc-body">
          <div class="setting-row">
            <div class="label-block"><label for="sttLang">Speech-to-text</label></div>
            <select id="sttLang">${sttOptions}</select>
          </div>
          <div class="setting-row">
            <div class="label-block"><label for="ttsLang">Text-to-speech</label></div>
            <select id="ttsLang"></select>
          </div>
          <div class="setting-row">
            <div class="label-block"><label for="autoSpeak">Auto-speak replies</label></div>
            <input type="checkbox" id="autoSpeak"${autoSpeak?' checked':''}>
          </div>
        </div>
      </details>

      <details class="settings-acc">
        <summary>Privacy &amp; data<span class="acc-desc">History and session</span></summary>
        <div class="acc-body">
          <div class="setting-row">
            <div class="label-block"><label>Local chat history</label><span class="hint">Stored in this browser only</span></div>
            <button type="button" class="btn-outline" onclick="clearChatStorage()">Clear history</button>
          </div>
          <div class="setting-row">
            <div class="label-block"><label>Preferences</label><span class="hint">Theme and chat options</span></div>
            <button type="button" class="btn-outline" onclick="resetPreferences()">Reset defaults</button>
          </div>
          <div class="setting-row">
            <div class="label-block"><label>Session</label></div>
            <button type="button" class="btn-danger-outline" onclick="handleLogout()">Log out</button>
          </div>
        </div>
      </details>

      <details class="settings-acc">
        <summary>About<span class="acc-desc">Version and health</span></summary>
        <div class="acc-body">
          <div class="setting-row"><div class="label-block"><label>Product</label></div><span>Vision AI</span></div>
          <div class="setting-row"><div class="label-block"><label>Version</label></div><span id="aboutVersion">5.6.1</span></div>
          <div class="setting-row"><div class="label-block"><label>API</label></div><span id="aboutHealth">…</span></div>
        </div>
      </details>
    `;

    const presetSelect = document.getElementById('themePresetSelect');

    if (presetSelect) presetSelect.value = themePreset;

    // Fill TTS options
    const ttsSel = document.getElementById('ttsLang');
    if (ttsSel) {
      ttsSel.innerHTML = [
        'en-US','en-GB','ur-PK','ar-SA','hi-IN','bn-BD','zh-CN','fr-FR','de-DE','es-ES',
        'pt-BR','ru-RU','ja-JP','ko-KR','tr-TR','id-ID','ms-MY','fa-IR','it-IT','nl-NL'
      ].map(v => '<option value="'+v+'"'+(ttsLang===v?' selected':'')+'>'+v+'</option>').join('');
    }

    // Immediate preference bindings
    const themeModeSelect = document.getElementById('themeModeSelect');
    if (themeModeSelect) themeModeSelect.addEventListener('change', function () {
      applyTheme(this.value);
      patchServerPrefs('appearance', { theme_mode: this.value }).catch(function () {});
    });
    if (presetSelect) presetSelect.addEventListener('change', function () {
      try { localStorage.setItem('vision_theme_preset', this.value); } catch (e) {}
      document.documentElement.setAttribute('data-theme-preset', this.value);
      if (window.applyThemePreset) applyThemePreset(this.value);
      patchServerPrefs('appearance', { theme_preset: this.value }).catch(function () {});
    });
    const densitySelect = document.getElementById('densitySelect');
    if (densitySelect) densitySelect.addEventListener('change', function () {
      try { localStorage.setItem('vision_density', this.value); } catch (e) {}
      document.documentElement.setAttribute('data-density', this.value);
      patchServerPrefs('appearance', { density: this.value }).catch(function () {});
    });
    const rm = document.getElementById('reducedMotion');
    if (rm) rm.addEventListener('change', function () {
      try { localStorage.setItem('vision_reduced_motion', this.checked ? '1' : '0'); } catch (e) {}
      document.documentElement.setAttribute('data-reduced-motion', this.checked ? '1' : '0');
      patchServerPrefs('appearance', { reduced_motion: this.checked }).catch(function () {});
    });
    const chatLangEl = document.getElementById('chatLang');
    if (chatLangEl) chatLangEl.addEventListener('change', function () {
      try { localStorage.setItem('vision_chat_lang', this.value); } catch (e) {}
      patchServerPrefs('chat', { chat_language: this.value }).catch(function () {});
    });
    const enterSendEl = document.getElementById('enterSend');
    if (enterSendEl) enterSendEl.addEventListener('change', function () {
      try { localStorage.setItem('vision_enter_send', this.checked ? '1' : '0'); } catch (e) {}
      patchServerPrefs('chat', { enter_to_send: this.checked }).catch(function () {});
    });
    const sttEl = document.getElementById('sttLang');
    if (sttEl) sttEl.addEventListener('change', function () {
      try { localStorage.setItem('vision_stt_lang', this.value); } catch (e) {}
      patchServerPrefs('voice', { stt_language: this.value }).catch(function () {});
    });
    const ttsEl = document.getElementById('ttsLang');
    if (ttsEl) ttsEl.addEventListener('change', function () {
      try { localStorage.setItem('vision_tts_lang', this.value); } catch (e) {}
      patchServerPrefs('voice', { tts_language: this.value }).catch(function () {});
    });
    const autoSpeakEl = document.getElementById('autoSpeak');
    if (autoSpeakEl) autoSpeakEl.addEventListener('change', function () {
      try { localStorage.setItem('vision_auto_speak', this.checked ? '1' : '0'); } catch (e) {}
      patchServerPrefs('voice', { auto_speak: this.checked }).catch(function () {});
    });

    // Health check
    fetch('/health').then(r => r.json()).then(d => {
      const el = document.getElementById('aboutHealth');
      if (el) el.textContent = (d && (d.status || d.version)) ? ('OK · ' + (d.version || d.status)) : 'OK';
      const ver = document.getElementById('aboutVersion');
      if (ver && d && d.version) ver.textContent = d.version;
    }).catch(() => {
      const el = document.getElementById('aboutHealth');
      if (el) el.textContent = 'Unreachable';
    });

// Attach form handler
    const pwForm = document.getElementById('pwForm');
    if (pwForm) {
        pwForm.addEventListener('submit', handleChangePassword);
    }
}

// ============================================================
// ✏️ NAME EDITING
// ============================================================

let isEditingName = false;

function toggleNameEdit() {
    const display = document.getElementById('nameDisplay');
    const edit = document.getElementById('nameEdit');
    if (edit && edit.hasAttribute('hidden')) {
      edit.removeAttribute('hidden');
      edit.style.display = 'flex';
      if (display) display.style.display = 'none';
      isEditingName = true;
      return;
    }
    if (edit && !edit.hasAttribute('hidden') && isEditingName) {
      edit.setAttribute('hidden', '');
      edit.style.display = 'none';
      if (display) display.style.display = 'flex';
      isEditingName = false;
      return;
    }
    if (!display || !edit) return;
    
    isEditingName = !isEditingName;
    display.style.display = isEditingName ? 'none' : 'flex';
    edit.style.display = isEditingName ? 'flex' : 'none';
    
    if (isEditingName) {
        const input = document.getElementById('nameInput');
        if (input) {
            input.focus();
            input.select();
        }
    }
}

async function saveName() {
    const input = document.getElementById('nameInput');
    if (!input) return;
    
    const newName = input.value.trim();
    if (!newName) {
        showToast('Name cannot be empty', 'error');
        input.focus();
        return;
    }
    
    const btn = document.querySelector('#nameEdit .btn-primary');
    if (!btn) return;
    
    btn.disabled = true;
    btn.textContent = 'Saving...';
    
    try {
        const res = await authedFetch('/auth/update-profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: newName })
        });
        
        if (res.ok) {
            const nameText = document.getElementById('nameText');
            if (nameText) nameText.textContent = newName;
            toggleNameEdit();
            
            // Update localStorage
            const storedUser = JSON.parse(localStorage.getItem('vision_ai_user') || '{}');
            storedUser.full_name = newName;
            localStorage.setItem('vision_ai_user', JSON.stringify(storedUser));
            
            showToast('Profile updated successfully!', 'success');
        } else {
            const data = await res.json();
            showToast(data.detail || 'Failed to update name', 'error');
        }
    } catch (err) {
        showToast('Connection error: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Save';
    }
}

// ============================================================
// 🔑 PASSWORD MANAGEMENT
// ============================================================

function togglePw(id, btn) {
    const input = document.getElementById(id);
    if (!input) return;
    
    const isPw = input.type === 'password';
    input.type = isPw ? 'text' : 'password';
    if (btn) btn.textContent = isPw ? '🙈' : '👁️';
}

async function handleChangePassword(event) {
    event.preventDefault();
    
    const oldPassword = document.getElementById('oldPassword');
    const newPassword = document.getElementById('newPassword');
    const msgEl = document.getElementById('pwMsg');
    const btn = document.getElementById('pwSubmitBtn');
    
    if (!oldPassword || !newPassword || !msgEl || !btn) return;
    
    const oldVal = oldPassword.value;
    const newVal = newPassword.value;
    
    // Validation
    if (!oldVal || !newVal) {
        msgEl.textContent = 'Please fill in both password fields.';
        msgEl.className = 'msg show error';
        return;
    }
    
    if (newVal.length < 6) {
        msgEl.textContent = 'New password must be at least 6 characters.';
        msgEl.className = 'msg show error';
        newPassword.focus();
        return;
    }
    
    if (oldVal === newVal) {
        msgEl.textContent = 'New password must be different from current password.';
        msgEl.className = 'msg show error';
        return;
    }
    
    msgEl.className = 'msg';
    btn.disabled = true;
    btn.textContent = 'Updating…';
    
    try {
        const res = await authedFetch('/auth/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                old_password: oldVal, 
                new_password: newVal 
            }),
        });
        
        const data = await res.json();
        
        if (res.ok) {
            msgEl.textContent = '✅ Password updated successfully.';
            msgEl.className = 'msg show success';
            document.getElementById('pwForm').reset();
            showToast('Password updated successfully!', 'success');
        } else {
            msgEl.textContent = data.detail || 'Could not update password.';
            msgEl.className = 'msg show error';
        }
    } catch (err) {
        msgEl.textContent = 'Connection error. Is the server running?';
        msgEl.className = 'msg show error';
        console.error('Password change error:', err);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Update Password';
    }
}

// ============================================================
// 🚪 LOGOUT
// ============================================================

async function handleLogout() {
    if (window.VisionAuth && typeof window.VisionAuth.logout === 'function') {
        return window.VisionAuth.logout({ confirm: true });
    }
    console.error('VisionAuth missing — reload page');
    window.location.replace('/login.html');
}


// ============================================================
// 🟢 TOAST NOTIFICATIONS
// ============================================================

function showToast(message, type = 'info', duration = 3000) {
    const msgEl = document.getElementById('pwMsg');
    if (msgEl) {
        msgEl.textContent = message;
        msgEl.className = `msg show ${type}`;
        setTimeout(() => { 
            msgEl.className = 'msg'; 
        }, duration);
        return;
    }
    
    // Fallback to console if msg element not found
    console.log(`${type.toUpperCase()}: ${message}`);
}

// ============================================================
// 🎯 DOM READY
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    // Prevent duplicate execution
    if (window._settingsDOMReady) return;
    window._settingsDOMReady = true;

    // Apply theme immediately
    const theme = getThemePreference();
    applyTheme(theme);
    
    // Initialize
    init();
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (isEditingName) {
                toggleNameEdit();
            }
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            if (isEditingName) {
                saveName();
            }
        }
    });
    
    console.log('👁️ Vision AI Settings v3.2.0 - Ready');
});

// ============================================================
// 🟢 ADDITIONAL SAFEGUARDS
// ============================================================

// Prevent multiple initializations
if (window._visionSettingsInitialized) {
    console.warn('Vision AI Settings already initialized!');
} else {
    window._visionSettingsInitialized = true;
}

// Global error handler
window.onerror = function(msg, url, line, col, error) {
    console.error('Global error:', msg, error);
    showToast('An unexpected error occurred. Please refresh the page.', 'error');
    return true;
};

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('An unexpected error occurred.', 'error');
});

// ============================================================
// 🔄 EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================================

window.applyTheme = applyTheme;
window.toggleTheme = toggleTheme;
window.getThemePreference = getThemePreference;
window.getAccessToken = getAccessToken;
window.clearTokens = clearTokens;
window.authedFetch = authedFetch;
window.toggleNameEdit = toggleNameEdit;
window.saveName = saveName;
window.togglePw = togglePw;
window.handleChangePassword = handleChangePassword;
window.handleLogout = handleLogout;
window.showToast = showToast;
window.escapeHtml = escapeHtml;
window.fmtDate = fmtDate;

// ============================================================
// 🎨 ADD TOAST STYLES (if not already present)
// ============================================================

if (!document.getElementById('settingsStyles')) {
    const style = document.createElement('style');
    style.id = 'settingsStyles';
    style.textContent = `
        .msg {
            margin-top: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            display: none;
            font-size: 14px;
        }
        .msg.show {
            display: block;
            animation: fadeIn 0.3s ease;
        }
        .msg.success {
            background: rgba(34, 197, 94, 0.1);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.2);
        }
        .msg.error {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        .msg.info {
            background: rgba(0, 198, 255, 0.1);
            color: #00C6FF;
            border: 1px solid rgba(0, 198, 255, 0.2);
        }
        .password-wrapper {
            position: relative;
        }
        .password-wrapper .toggle-password {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            cursor: pointer;
            font-size: 18px;
            padding: 4px;
        }
        .edit-input-group {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }
        .edit-input-group input {
            flex: 1;
            min-width: 150px;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .btn-danger-outline {
            color: #ef4444;
            border: 1px solid #ef4444;
            background: transparent;
        }
        .btn-danger-outline:hover {
            background: #ef4444;
            color: white;
        }
        .plan-badge {
            background: rgba(0, 198, 255, 0.1);
            color: #00C6FF;
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            border: 1px solid rgba(0, 198, 255, 0.2);
        }
    `;
    document.head.appendChild(style);
}

console.log('👁️ Vision AI Settings - Ready');
// ---- Custom API keys (saved to localStorage; optional server sync for admin) ----
function renderApiKeysCard(container) {
    if (!container || document.getElementById('apiKeysCard')) return;
    const card = document.createElement('div');
    card.className = 'card glass-panel full-width';
    card.id = 'apiKeysCard';
    const saved = JSON.parse(localStorage.getItem('vision_ai_user_keys') || '{}');
    card.innerHTML = `
        <h2>🔑 Custom API Keys</h2>
        <p style="color:var(--text-muted);font-size:13px;margin-bottom:14px;">
            Optional keys for this browser session. Server keys in <code>.env</code> still take priority unless you enable override below.
        </p>
        <div class="field"><label>Google / Gemini</label><input id="key_gemini" type="password" placeholder="AIza..." value="" autocomplete="off"></div>
        <div class="field"><label>Groq</label><input id="key_groq" type="password" placeholder="gsk_..." value="" autocomplete="off"></div>
        <div class="field"><label>DeepSeek</label><input id="key_deepseek" type="password" placeholder="sk-..." value="" autocomplete="off"></div>
        <div class="field"><label>OpenRouter</label><input id="key_openrouter" type="password" placeholder="sk-or-..." value="" autocomplete="off"></div>
        <div class="field"><label>Tavily Search</label><input id="key_tavily" type="password" placeholder="tvly-..." value="" autocomplete="off"></div>
        <hr style="border:none;border-top:1px solid var(--border-color);margin:16px 0;">
        <h3 style="font-size:14px;margin:0 0 8px;">🖥️ Local / OpenAI-compatible LLM</h3>
        <p style="color:var(--text-muted);font-size:12px;margin:0 0 10px;">Ollama, LM Studio, vLLM, text-gen-webui, Together, etc. Select <b>Ollama</b>, <b>LM Studio</b>, or <b>OpenAI-compat</b> in the chat model menu.</p>
        <div class="field"><label>Base URL</label><input id="key_compat_base" type="text" placeholder="http://127.0.0.1:11434 or http://127.0.0.1:1234/v1" value=""></div>
        <div class="field"><label>API key (optional)</label><input id="key_compat_key" type="password" placeholder="ollama / lm-studio / sk-..." value="" autocomplete="off"></div>
        <div class="field"><label>Model id</label><input id="key_compat_model" type="text" placeholder="llama3.2 / local-model / qwen2.5" value=""></div>
        <label style="display:flex;align-items:center;gap:8px;margin:12px 0;font-size:13px;">
            <input type="checkbox" id="key_override"> Prefer these keys over server defaults (sends on every chat request)
        </label>
        <button type="button" class="btn-primary" id="saveKeysBtn" style="margin-top:8px;">Save keys</button>
        <button type="button" class="btn-secondary" id="clearKeysBtn" style="margin-top:8px;margin-left:8px;">Clear</button>
        <p id="keysStatus" style="font-size:12px;color:var(--text-muted);margin-top:10px;"></p>
    `;
    container.appendChild(card);
    // Assign values via DOM properties (safer than interpolating into innerHTML)
    const _set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
    _set('key_gemini', saved.GOOGLE_API_KEY);
    _set('key_groq', saved.GROQ_API_KEY);
    _set('key_deepseek', saved.DEEPSEEK_API_KEY);
    _set('key_openrouter', saved.OPENROUTER_API_KEY);
    _set('key_tavily', saved.TAVILY_API_KEY);
    _set('key_compat_base', saved.OPENAI_COMPAT_BASE);
    _set('key_compat_key', saved.OPENAI_COMPAT_KEY);
    _set('key_compat_model', saved.OPENAI_COMPAT_MODEL);
    const ov = document.getElementById('key_override');
    if (ov) ov.checked = !!saved.override;
    document.getElementById('saveKeysBtn').onclick = () => {
        const data = {
            GOOGLE_API_KEY: document.getElementById('key_gemini').value.trim(),
            GROQ_API_KEY: document.getElementById('key_groq').value.trim(),
            DEEPSEEK_API_KEY: document.getElementById('key_deepseek').value.trim(),
            OPENROUTER_API_KEY: document.getElementById('key_openrouter').value.trim(),
            TAVILY_API_KEY: document.getElementById('key_tavily').value.trim(),
            OPENAI_COMPAT_BASE: (document.getElementById('key_compat_base') || {}).value?.trim() || '',
            OPENAI_COMPAT_KEY: (document.getElementById('key_compat_key') || {}).value?.trim() || '',
            OPENAI_COMPAT_MODEL: (document.getElementById('key_compat_model') || {}).value?.trim() || '',
            override: document.getElementById('key_override').checked,
        };
        localStorage.setItem('vision_ai_user_keys', JSON.stringify(data));
        document.getElementById('keysStatus').textContent = data.override
          ? '✅ Saved. Override ON — these keys are sent with each chat request (never logged server-side).'
          : '✅ Saved in browser. Enable “Prefer these keys…” to use them on chat.';
    };
    document.getElementById('clearKeysBtn').onclick = () => {
        localStorage.removeItem('vision_ai_user_keys');
        ['key_gemini','key_groq','key_deepseek','key_openrouter','key_tavily','key_compat_base','key_compat_key','key_compat_model'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
        document.getElementById('keysStatus').textContent = 'Cleared.';
    };
}

document.addEventListener('DOMContentLoaded', () => {
    const page = document.querySelector('.page') || document.body;
    setTimeout(() => renderApiKeysCard(page), 400);
});

// Voice language preferences
(function initVoiceLangPrefs() {
    const stt = document.getElementById('sttLang');
    const tts = document.getElementById('ttsLang');
    if (stt) {
        stt.value = localStorage.getItem('vision_ai_stt_lang') || 'ur-PK';
        stt.addEventListener('change', () => localStorage.setItem('vision_ai_stt_lang', stt.value));
    }
    if (tts) {
        tts.value = localStorage.getItem('vision_ai_tts_lang') || 'ur-PK';
        tts.addEventListener('change', () => localStorage.setItem('vision_ai_tts_lang', tts.value));
    }
})();


// Chat language preference
(function initChatLang() {
  function bind() {
    const el = document.getElementById('chatLang');
    if (!el) return;
    const saved = localStorage.getItem('vision_ai_chat_lang') || 'auto';
    el.value = saved;
    el.addEventListener('change', () => localStorage.setItem('vision_ai_chat_lang', el.value));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();

function clearChatStorage() {
  try {
    localStorage.removeItem('vision_ai_history_v2');
    localStorage.removeItem('vision_ai_recent');
    alert('Local chat history cleared. Reload the chat page.');
  } catch (e) {
    alert('Could not clear: ' + e);
  }
}
window.clearChatStorage = clearChatStorage;

(function loadAbout(){
  function run(){
    const v = document.getElementById('aboutVersion');
    const tm = document.getElementById('aboutTime');
    const prod = document.getElementById('aboutProduct');
    const build = document.getElementById('aboutBuild');
    const health = document.getElementById('aboutHealth');
    try {
      if (tm) {
        const pkt = new Date().toLocaleString('en-PK', { timeZone: 'Asia/Karachi', weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        tm.textContent = pkt + ' (PKT)';
      }
    } catch (e) {
      if (tm) tm.textContent = new Date().toLocaleString();
    }
    fetch('/api/version').then(r => r.json()).then(d => {
      if (v) v.textContent = d.version || d.current || '3.2.0';
      if (prod) prod.textContent = d.name || d.product || 'Vision AI';
      if (build) build.textContent = [d.channel, d.build, d.git_sha].filter(Boolean).join(' · ') || 'stable / production';
    }).catch(() => { if (v) v.textContent = '3.2.0 (offline meta)'; });
    fetch('/health').then(r => r.json()).then(d => {
      if (health) health.textContent = (d.status || 'ok') + (d.version ? ' · server ' + d.version : '');
    }).catch(() => { if (health) health.textContent = 'unreachable'; });
  }
  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded', run); else run();
})();



function resetPreferences() {
  if (!confirm('Reset appearance and chat preferences to defaults? Chat history is not deleted.')) return;
  authedFetch('/api/settings/reset', { method: 'POST' }).then(function (r) {
    if (r.ok) return r.json();
    throw new Error('reset failed');
  }).then(function (prefs) {
    cachePrefs(prefs);
    window.location.reload();
  }).catch(function () {
    try {
      ['vision_ai_theme','vision_theme_preset','vision_chat_lang','vision_stt_lang','vision_tts_lang',
       'vision_auto_speak','vision_enter_send','vision_reduced_motion','vision_density', PREFS_CACHE_KEY].forEach(function (k) {
        localStorage.removeItem(k);
      });
    } catch (e) {}
    applyTheme('dark');
    window.location.reload();
  });
}
