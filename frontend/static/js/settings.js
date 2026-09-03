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
    const themePreset = localStorage.getItem('vision_theme_preset') || 'humanly';

    content.innerHTML = `
        <section class="settings-card profile-hero full-width" aria-label="Profile summary">
            <div class="profile-hero-avatar" aria-hidden="true">${escapeHtml(initials)}</div>
            <div class="profile-hero-copy">
                <div class="profile-hero-name">${escapeHtml(displayName)}</div>
                <div class="profile-hero-meta">${escapeHtml(me.email || 'No email')} · ${escapeHtml(planName)} plan</div>
            </div>
            <div class="profile-hero-actions">
                <button type="button" class="btn btn-primary" onclick="document.getElementById('nameInput')?.focus(); if(!isEditingName) toggleNameEdit();">Edit profile</button>
                <button type="button" class="btn btn-outline" onclick="window.location.href='/usage.html'">View usage</button>
            </div>
        </section>

        <div class="settings-grid">
        <div class="card" id="account">
            <h2>👤 Profile</h2>
            <div class="profile-row">
                <span class="label">Username</span>
                <span class="value">${escapeHtml(me.username)}</span>
            </div>
            <div class="profile-row" id="nameRow">
                <span class="label">Full name</span>
                <div class="value" id="nameDisplay">
                    <span id="nameText">${escapeHtml(me.full_name || '—')}</span>
                    <button class="edit-icon-btn" onclick="toggleNameEdit()" aria-label="Edit name">✏️</button>
                </div>
                <div class="value" id="nameEdit" style="display:none;">
                    <div class="edit-input-group">
                        <input type="text" id="nameInput" value="${escapeHtml(me.full_name || '')}" placeholder="Enter full name" maxlength="100">
                        <button class="btn btn-primary" onclick="saveName()" style="padding:6px 12px;font-size:12px;">Save</button>
                        <button class="btn btn-outline" onclick="toggleNameEdit()" style="padding:6px 12px;font-size:12px;">Cancel</button>
                    </div>
                </div>
            </div>
            <div class="profile-row">
                <span class="label">Email</span>
                <span class="value">${escapeHtml(me.email || '—')}</span>
            </div>
            <div class="profile-row">
                <span class="label">Member since</span>
                <span class="value">${fmtDate(me.created_at)}</span>
            </div>
            <div class="profile-row">
                <span class="label">Role</span>
                <span class="value">${escapeHtml(me.role || 'user')}</span>
            </div>
        </div>
        
        <div class="card" id="billing">
            <h2>💎 Plan</h2>
            <div class="profile-row">
                <span class="label">Current plan</span>
                <span class="plan-badge">${escapeHtml(planName)}</span>
            </div>
            <div class="card-actions" style="margin-top:16px;">
                <button class="btn btn-primary" onclick="window.location.href='/upgrade.html'">Manage Plan</button>
                <button class="btn btn-outline" onclick="window.location.href='/boost'" style="margin-left:8px;">⚡ GPU Boost</button>
            </div>
        </div>
        
        <div class="card" id="appearance">
            <h2>🎨 Appearance</h2>
            <div class="form-group">
                <label for="themePresetSelect">Theme preset</label>
                <select id="themePresetSelect" aria-label="Theme preset" onchange="if(window.applyThemePreset)applyThemePreset(this.value)">
                    <option value="humanly">Humanly Teal</option>
                    <option value="default">Vision Default</option>
                    <option value="nord">Nord</option>
                    <option value="ocean">Ocean</option>
                    <option value="forest">Forest</option>
                    <option value="violet">Violet</option>
                    <option value="rose">Rose</option>
                    <option value="midnight">Midnight</option>
                    <option value="sunset">Sunset</option>
                    <option value="emerald">Emerald</option>
                    <option value="frost">Frost</option>
                    <option value="ember">Ember</option>
                    <option value="sand">Sand (light)</option>
                    <option value="soft-sepia">Soft Sepia</option>
                    <option value="high-contrast">High Contrast</option>
                </select>
            </div>
            <div class="card-actions">
                <button type="button" class="btn btn-outline" onclick="applyTheme('light')">☀️ Light</button>
                <button type="button" class="btn btn-outline" onclick="applyTheme('dark')">🌙 Dark</button>
                <button type="button" class="btn btn-outline" onclick="applyTheme('system')">💻 System</button>
            </div>
        </div>

        <div class="card" id="security">
            <h2>🔒 Change Password</h2>
            <form id="pwForm" novalidate>
                <div class="form-group">
                    <label for="oldPassword">Current password</label>
                    <div class="password-wrapper">
                        <input type="password" id="oldPassword" required autocomplete="current-password" minlength="6">
                        <button type="button" class="toggle-password" onclick="togglePw('oldPassword', this)" aria-label="Toggle password visibility">👁️</button>
                    </div>
                </div>
                <div class="form-group">
                    <label for="newPassword">New password</label>
                    <div class="password-wrapper">
                        <input type="password" id="newPassword" required minlength="6" autocomplete="new-password">
                        <button type="button" class="toggle-password" onclick="togglePw('newPassword', this)" aria-label="Toggle password visibility">👁️</button>
                    </div>
                    <small style="color:var(--text-muted);font-size:12px;">Minimum 6 characters</small>
                </div>
                <div class="card-actions">
                    <button type="submit" class="btn btn-primary" id="pwSubmitBtn">Update Password</button>
                </div>
                <div class="msg" id="pwMsg" role="alert"></div>
            </form>
        </div>
        
        <div class="card" id="voice">
            <h2>🎤 Voice (mic & speak)</h2>
            <p style="font-size:13px;color:var(--text-muted);margin:0 0 12px;">Mic needs <strong>HTTPS</strong> (your site already has it). Allow microphone in the browser address-bar lock icon if blocked.</p>
            <div class="form-group">
                <label for="sttLang">Speech-to-text language</label>
                <select id="sttLang" style="width:100%;padding:10px;border-radius:10px;border:1px solid var(--border-color);background:var(--input-bg);color:var(--text-main);">

                    <option value="ur-PK">Urdu (Pakistan)</option>
                    <option value="en-US">English (US)</option>
                    <option value="en-GB">English (UK)</option>
                    <option value="ar-SA">Arabic</option>
                    <option value="hi-IN">Hindi</option>
                    <option value="bn-BD">Bengali</option>
                    <option value="zh-CN">Chinese (Simplified)</option>
                    <option value="zh-TW">Chinese (Traditional)</option>
                    <option value="fr-FR">French</option>
                    <option value="de-DE">German</option>
                    <option value="es-ES">Spanish</option>
                    <option value="pt-BR">Portuguese (Brazil)</option>
                    <option value="ru-RU">Russian</option>
                    <option value="ja-JP">Japanese</option>
                    <option value="ko-KR">Korean</option>
                    <option value="tr-TR">Turkish</option>
                    <option value="id-ID">Indonesian</option>
                    <option value="ms-MY">Malay</option>
                    <option value="fa-IR">Persian</option>
                    <option value="pa-IN">Punjabi</option>
                    <option value="ta-IN">Tamil</option>
                    <option value="te-IN">Telugu</option>
                    <option value="it-IT">Italian</option>
                    <option value="nl-NL">Dutch</option>
                    <option value="pl-PL">Polish</option>
                    <option value="uk-UA">Ukrainian</option>
                    <option value="vi-VN">Vietnamese</option>
                    <option value="th-TH">Thai</option>
                </select>
            </div>
            <div class="form-group" style="margin-top:10px;">
                <label for="ttsLang">Text-to-speech language</label>
                <select id="ttsLang" style="width:100%;padding:10px;border-radius:10px;border:1px solid var(--border-color);background:var(--input-bg);color:var(--text-main);">

                    <option value="ur-PK">Urdu (Pakistan)</option>
                    <option value="en-US">English (US)</option>
                    <option value="en-GB">English (UK)</option>
                    <option value="ar-SA">Arabic</option>
                    <option value="hi-IN">Hindi</option>
                    <option value="bn-BD">Bengali</option>
                    <option value="zh-CN">Chinese (Simplified)</option>
                    <option value="zh-TW">Chinese (Traditional)</option>
                    <option value="fr-FR">French</option>
                    <option value="de-DE">German</option>
                    <option value="es-ES">Spanish</option>
                    <option value="pt-BR">Portuguese (Brazil)</option>
                    <option value="ru-RU">Russian</option>
                    <option value="ja-JP">Japanese</option>
                    <option value="ko-KR">Korean</option>
                    <option value="tr-TR">Turkish</option>
                    <option value="id-ID">Indonesian</option>
                    <option value="ms-MY">Malay</option>
                    <option value="fa-IR">Persian</option>
                    <option value="pa-IN">Punjabi</option>
                    <option value="ta-IN">Tamil</option>
                    <option value="te-IN">Telugu</option>
                    <option value="it-IT">Italian</option>
                    <option value="nl-NL">Dutch</option>
                    <option value="pl-PL">Polish</option>
                    <option value="uk-UA">Ukrainian</option>
                    <option value="vi-VN">Vietnamese</option>
                    <option value="th-TH">Thai</option>
                </select>
            </div>
            <div class="form-group" style="margin-top:10px;">
                <label for="chatLang">Chat reply language</label>
                <select id="chatLang" style="width:100%;padding:10px;border-radius:10px;border:1px solid var(--border-color);background:var(--input-bg);color:var(--text-main);">
                    <option value="auto">Auto (match user)</option>

                    <option value="ur-PK">Urdu (Pakistan)</option>
                    <option value="en-US">English (US)</option>
                    <option value="en-GB">English (UK)</option>
                    <option value="ar-SA">Arabic</option>
                    <option value="hi-IN">Hindi</option>
                    <option value="bn-BD">Bengali</option>
                    <option value="zh-CN">Chinese (Simplified)</option>
                    <option value="zh-TW">Chinese (Traditional)</option>
                    <option value="fr-FR">French</option>
                    <option value="de-DE">German</option>
                    <option value="es-ES">Spanish</option>
                    <option value="pt-BR">Portuguese (Brazil)</option>
                    <option value="ru-RU">Russian</option>
                    <option value="ja-JP">Japanese</option>
                    <option value="ko-KR">Korean</option>
                    <option value="tr-TR">Turkish</option>
                    <option value="id-ID">Indonesian</option>
                    <option value="ms-MY">Malay</option>
                    <option value="fa-IR">Persian</option>
                    <option value="pa-IN">Punjabi</option>
                    <option value="ta-IN">Tamil</option>
                    <option value="te-IN">Telugu</option>
                    <option value="it-IT">Italian</option>
                    <option value="nl-NL">Dutch</option>
                    <option value="pl-PL">Polish</option>
                    <option value="uk-UA">Ukrainian</option>
                    <option value="vi-VN">Vietnamese</option>
                    <option value="th-TH">Thai</option>
                </select>
            </div>
            <p style="font-size:12px;color:var(--text-muted);margin-top:8px;">Speak needs a matching voice pack on your device for some languages. Mic: allow in address-bar site settings once.</p>
        </div>
        
        <div class="card full-width" id="session">
            <h2>🚪 Session</h2>
            <p style="font-size:13px;color:var(--text-muted);margin:0 0 10px;">If chat shows storage quota errors, clear local history (images stay generated on server session only).</p>
            <div class="card-actions" style="margin-bottom:0;">
                <button type="button" class="btn btn-outline" onclick="clearChatStorage()">Clear local chat history</button>
                <button class="btn btn-danger-outline" onclick="handleLogout()">Log out</button>
            </div>
        </div>
        </div>
    `;
    
    const presetSelect = document.getElementById('themePresetSelect');
    if (presetSelect) presetSelect.value = themePreset;

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

