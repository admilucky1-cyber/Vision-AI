// ============================================================
// VISION AI v3.2.0 - UPGRADE LOGIC (Production Ready)
// ============================================================

const API_BASE = '';

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

// ============================================================
// 🌙 THEME MANAGEMENT
// ============================================================

// Apply saved theme immediately when the page loads
const savedTheme = localStorage.getItem('vision_ai_theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);
try {
  var _preset = localStorage.getItem('vision_theme_preset') || 'humanly';
  if (_preset && _preset !== 'default') document.documentElement.setAttribute('data-theme-preset', _preset);
} catch (e) {}


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
    let nextTheme;
    
    if (current === 'dark') {
        nextTheme = 'light';
    } else if (current === 'light') {
        nextTheme = 'system';
    } else {
        nextTheme = 'dark';
    }
    
    applyTheme(nextTheme);
    showStatus(`Theme switched to ${nextTheme}`, 'success');
}

// Listen for system theme changes
if (savedTheme === 'system') {
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
        // Don't redirect automatically - let the caller handle it
        return null;
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
        // Token refresh failed - clear tokens and redirect to login
        clearTokens();
        window.location.href = '/login.html';
        return;
    }
    return res;
}

// ============================================================
// 📋 STATUS MESSAGES
// ============================================================

function showStatus(message, type = 'info', duration = 4000) {
    const el = document.getElementById('statusMsg');
    if (!el) {
        // Fallback to console if element not found
        console.log(`[${type}] ${message}`);
        return;
    }
    
    el.textContent = message;
    el.className = `status-msg show ${type}`;
    
    // Clear any existing timeout
    if (el._timeout) {
        clearTimeout(el._timeout);
    }
    
    el._timeout = setTimeout(() => {
        el.classList.remove('show');
    }, duration);
}

// ============================================================
// 💰 PRICE FORMATTING
// ============================================================

function formatPrice(plan) {
    if (!plan) return '';
    const amount = Number(plan.price) || 0;
    if (amount === 0) {
        return `<div class="plan-price"><span class="price-main">Free</span></div>`;
    }
    // Vision AI is Pakistan-first: always show Rs unless currency is explicitly foreign
    let cur = String(plan.currency || 'PKR').toUpperCase();
    if (cur === 'USD' || cur === '$') {
        // Migrate legacy USD labels to PKR display (amounts already stored as PKR numbers)
        cur = 'PKR';
    }
    if (cur === 'PKR' || cur === 'RS' || cur === 'PK') {
        const n = Math.round(amount).toLocaleString('en-PK');
        return `<div class="plan-price"><span class="price-currency">Rs</span> <span class="price-main">${n}</span><span class="per">/month</span></div>`;
    }
    return `<div class="plan-price"><span class="price-main">${escapeHtml(cur)} ${amount.toFixed(2)}</span><span class="per">/month</span></div>`;
}


// ============================================================
// 🎯 PLAN MANAGEMENT
// ============================================================

let currentPlanId = 'free';
let isLoadingPlans = false;

// Load plans from server
async function loadPlans() {
    if (isLoadingPlans) return;
    isLoadingPlans = true;
    
    const container = document.getElementById('plansContainer');
    if (!container) return;
    
    // Show loading state
    container.innerHTML = `
        <div class="loading-state" style="text-align:center;padding:40px;color:var(--text-muted);">
            ⏳ Loading plans...
        </div>
    `;
    
    try {
        const token = getAccessToken();
        const [plansRes, meRes] = await Promise.all([
            fetch(`${API_BASE}/upgrade/plans`),
            token ? authedFetch(`${API_BASE}/upgrade/me`) : Promise.resolve(null),
        ]);

        if (!plansRes.ok) {
            throw new Error('Could not load plans');
        }
        
        const plans = await plansRes.json();
        
        // Handle user info if logged in
        if (meRes && meRes.ok) {
            const me = await meRes.json();
            currentPlanId = me.current_plan || 'free';
            
            const banner = document.getElementById('currentPlanBanner');
            if (banner) {
                banner.style.display = 'block';
                banner.innerHTML = `
                    Signed in as <strong>${escapeHtml(me.username)}</strong> — 
                    current plan: <strong>${escapeHtml(me.plan_details?.name || me.current_plan || 'Free')}</strong>
                `;
            }
        }

        renderPlans(plans);
    } catch (err) {
        console.error('Load plans error:', err);
        isLoadingPlans = false;
        if (container) {
            container.innerHTML = `
                <div class="loading-state" style="text-align:center;padding:40px;color:var(--text-muted);">
                    ⚠️ ${escapeHtml(err.message || 'Failed to load plans')}
                    <br><br>
                    <button onclick="loadPlans()" class="btn btn-primary" style="padding:8px 20px;">Retry</button>
                </div>
            `;
        }
    } finally {
        isLoadingPlans = false;
    }
}

// Render plans to the DOM
function renderPlans(plans) {
    const container = document.getElementById('plansContainer');
    if (!container) return;
    
    if (!plans || plans.length === 0) {
        container.innerHTML = `
            <div class="loading-state" style="text-align:center;padding:40px;color:var(--text-muted);">
                No plans available at this time.
            </div>
        `;
        return;
    }
    
    const grid = document.createElement('div');
    grid.className = 'plans-grid';

    // Lowest price → highest (Free first, Enterprise last)
    const sorted = [...plans].sort(function(a, b) {
        const pa = Number(a.price) || 0;
        const pb = Number(b.price) || 0;
        if (pa !== pb) return pa - pb;
        const order = { free: 0, student: 1, pro: 2, team: 3, enterprise: 4 };
        return (order[a.id] || 50) - (order[b.id] || 50);
    });

    sorted.forEach(plan => {
        const isCurrent = plan.id === currentPlanId;
        const isPopular = plan.id === 'pro' || plan.id === 'plus';
        
        const card = document.createElement('div');
        card.className = `plan-card${isCurrent ? ' current' : ''}${isPopular ? ' popular' : ''}`;

        const featuresHtml = (plan.features || []).map(f => `<li>${escapeHtml(f)}</li>`).join('');

        let btnHtml;
        if (isCurrent) {
            btnHtml = `<button class="plan-btn current-btn" disabled>✅ Current Plan</button>`;
        } else if (plan.id === 'free') {
            btnHtml = `<button class="plan-btn downgrade" data-plan="${plan.id}" data-action="downgrade">⬇️ Downgrade to Free</button>`;
        } else {
            btnHtml = `<button class="plan-btn upgrade" data-plan="${plan.id}" data-action="upgrade">⬆️ Upgrade to ${escapeHtml(plan.name)}</button>`;
        }

        card.innerHTML = `
            <div class="plan-name">${escapeHtml(plan.name)}</div>
            ${formatPrice(plan)}
            ${isPopular ? '<div class="popular-badge">🔥 Most Popular</div>' : ''}
            <ul class="plan-features">${featuresHtml}</ul>
            ${btnHtml}
        `;
        grid.appendChild(card);
    });

    container.innerHTML = '';
    container.appendChild(grid);

    // Keep payment Plan dropdown in sync with all paid plans from API
    const payPlanSelect = document.getElementById("payPlan");
    if (payPlanSelect && Array.isArray(plans)) {
        const paid = plans.filter(pl => pl.id && pl.id !== "free" && Number(pl.price) > 0)
            .sort((a, b) => (Number(a.price)||0) - (Number(b.price)||0));
        if (paid.length) {
            const prev = payPlanSelect.value;
            payPlanSelect.innerHTML = paid.map(pl => {
                const price = Number(pl.price) || 0;
                const label = price ? `${pl.name} (${price} PKR)` : pl.name;
                return `<option value="${pl.id}">${label}</option>`;
            }).join("");
            if ([...payPlanSelect.options].some(o => o.value === prev)) {
                payPlanSelect.value = prev;
            } else if (paid.some(pl => pl.id === "pro")) {
                payPlanSelect.value = "pro";
            }
            payPlanSelect.dispatchEvent(new Event("change"));
        }
    }

    // Attach event listeners to all plan buttons
    grid.querySelectorAll('button[data-action]').forEach(btn => {
        btn.addEventListener('click', () => handlePlanAction(btn.dataset.action, btn.dataset.plan, btn));
    });
}

// Handle plan upgrade/downgrade
async function handlePlanAction(action, planId, btnEl) {
    const token = getAccessToken();
    if (!token) {
        showStatus('Please sign in to manage your plan', 'error');
        setTimeout(() => {
            window.location.href = '/login.html';
        }, 1500);
        return;
    }

    if (!btnEl) return;

    // Paid plans go through real payment verification (Easypaisa/bank or
    // Stripe checkout), never an instant free grant. Route the click to
    // the payment form instead of calling the upgrade endpoint.
    if (action === 'upgrade' && planId !== 'free') {
        const payPlanSelect = document.getElementById('payPlan');
        const paymentSection = document.getElementById('paymentSection');
        if (payPlanSelect && [...payPlanSelect.options].some(o => o.value === planId)) {
            payPlanSelect.value = planId;
        }
        if (paymentSection) {
            paymentSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        showStatus(`Complete payment below to activate the ${planId} plan.`, 'info');
        return;
    }

    // Confirmation dialog
    const actionText = action === 'upgrade' ? 'upgrade to' : 'downgrade to';
    if (!confirm(`Are you sure you want to ${actionText} ${planId} plan?`)) {
        return;
    }

    btnEl.disabled = true;
    const originalText = btnEl.textContent;
    btnEl.textContent = '⏳ Processing…';

    try {
        const url = action === 'upgrade' 
            ? `${API_BASE}/upgrade/upgrade` 
            : `${API_BASE}/upgrade/downgrade`;
            
        const options = { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' } 
        };
        
        if (action === 'upgrade') {
            options.body = JSON.stringify({ plan: planId });
        }

        const res = await authedFetch(url, options);
        
        if (!res) {
            showStatus('Authentication failed. Please sign in again.', 'error');
            btnEl.disabled = false;
            btnEl.textContent = originalText;
            return;
        }
        
        const data = await res.json();

        if (res.ok) {
            showStatus(data.message || 'Plan updated successfully!', 'success');
            currentPlanId = planId === 'free' || action === 'downgrade' ? 'free' : planId;
            await loadPlans();
        } else {
            const errorMsg = data.detail || data.message || 'Something went wrong';
            showStatus(errorMsg, 'error');
            btnEl.disabled = false;
            btnEl.textContent = originalText;
        }
    } catch (err) {
        console.error('Plan action error:', err);
        showStatus('Connection error. Is the server running?', 'error');
        btnEl.disabled = false;
        btnEl.textContent = originalText;
    }
}

// ============================================================
// 💳 MANUAL PAYMENTS (Easypaisa / Bank — Pakistan)
// ============================================================

async function loadPaymentMethods() {
    const el = document.getElementById('paymentMethods');
    if (!el) return;

    try {
        const res = await fetch(`${API_BASE}/upgrade/payment-info`);
        if (!res.ok) throw new Error('Could not load payment details');
        const info = await res.json();

        if (!info.configured || !info.methods || info.methods.length === 0) {
            el.innerHTML = `<p style="color:var(--text-muted);margin:0;">Manual payments aren't configured yet. Please check back later or contact support.</p>`;
            return;
        }

        const amountInput = document.getElementById('payAmount');
        const planSelect = document.getElementById('payPlan');

        // Pre-fill the expected amount for whichever plan is selected
        const applyExpectedAmount = () => {
            if (!amountInput || !planSelect || !info.prices) return;
            const price = info.prices[planSelect.value];
            if (price && !amountInput.value) {
                amountInput.placeholder = String(price);
            }
        };
        if (planSelect) {
            planSelect.addEventListener('change', applyExpectedAmount);
            applyExpectedAmount();
        }

        const qrUrl = (data) =>
            'https://api.qrserver.com/v1/create-qr-code/?size=160x160&margin=8&data=' + encodeURIComponent(data || '');

        const methodsHtml = info.methods.map(m => {
            if (m.id === 'easypaisa') {
                const payload = m.number || '';
                return `
                    <div class="pay-method-row">
                        <div>
                            <strong>${escapeHtml(m.name)}</strong><br>
                            <span style="font-size:1.1rem;letter-spacing:0.02em;font-weight:600;">${escapeHtml(m.number)}</span>
                            ${m.title ? `<br><span style="color:var(--text-muted);font-size:0.85rem;">Account title: ${escapeHtml(m.title)}</span>` : ''}
                            <br><span style="color:var(--text-muted);font-size:0.8rem;">Scan QR in Easypaisa / send to this number</span>
                        </div>
                        ${payload ? `<img src="${qrUrl(payload)}" alt="Easypaisa QR" width="148" height="148" loading="lazy">` : ''}
                    </div>`;
            }
            const iban = m.iban || '';
            return `
                <div class="pay-method-row">
                    <div>
                        <strong>${escapeHtml(m.name)}</strong><br>
                        IBAN: <span style="word-break:break-all;font-size:0.92rem;">${escapeHtml(iban)}</span>
                        ${m.title ? `<br><span style="color:var(--text-muted);font-size:0.85rem;">Account title: ${escapeHtml(m.title)}</span>` : ''}
                        <br><span style="color:var(--text-muted);font-size:0.8rem;">Scan QR for bank transfer details</span>
                    </div>
                    ${iban ? `<img src="${qrUrl(iban)}" alt="IBAN QR" width="148" height="148" loading="lazy">` : ''}
                </div>`;
        }).join('');

        const priceLine = info.prices
            ? `<p style="color:var(--text-muted);font-size:0.85rem;margin:0 0 10px;">Pro: ${info.prices.pro} ${escapeHtml(info.currency)} · Team: ${info.prices.team} ${escapeHtml(info.currency)}</p>`
            : '';

        el.innerHTML = `
            ${priceLine}
            ${methodsHtml}
            ${info.note ? `<p style="color:var(--text-muted);font-size:0.85rem;margin-top:10px;">${escapeHtml(info.note)}</p>` : ''}
            ${info.whatsapp ? `<p style="font-size:0.85rem;margin-top:6px;">Need help? WhatsApp: ${escapeHtml(info.whatsapp)}</p>` : ''}
        `;
    } catch (err) {
        console.error('Load payment methods error:', err);
        el.innerHTML = `<p style="color:#f87171;margin:0;">⚠️ Could not load payment details. Please refresh the page.</p>`;
    }
}

async function submitPayment(event) {
    // nature theme: show patient confirmation banner on any accepted txn id

    event.preventDefault();

    const token = getAccessToken();
    if (!token) {
        showStatus('Please sign in to submit a payment', 'error');
        setTimeout(() => { window.location.href = '/login.html'; }, 1500);
        return false;
    }

    const planEl = document.getElementById('payPlan');
    const methodEl = document.getElementById('payMethod');
    const txnEl = document.getElementById('payTxn');
    const amountEl = document.getElementById('payAmount');
    const senderEl = document.getElementById('paySender');
    const msgEl = document.getElementById('paymentMsg');
    const submitBtn = event.target.querySelector('button[type="submit"]');

    if (!planEl || !methodEl || !txnEl) return false;

    const transactionId = txnEl.value.trim();
    if (transactionId.length < 4) {
        if (msgEl) {
            msgEl.textContent = '⚠️ Please enter a valid transaction ID (at least 4 characters).';
            msgEl.style.color = '#f87171';
        }
        txnEl.focus();
        return false;
    }

    const body = {
        plan: planEl.value,
        method: methodEl.value,
        transaction_id: transactionId,
    };
    if (amountEl && amountEl.value) body.amount_pkr = Number(amountEl.value);
    if (senderEl && senderEl.value.trim()) body.sender_name = senderEl.value.trim();

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting…';
    }
    if (msgEl) {
        msgEl.textContent = '';
    }

    try {
        const res = await authedFetch(`${API_BASE}/upgrade/payment-request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!res) {
            if (msgEl) {
                msgEl.textContent = '⚠️ Session expired. Please sign in again.';
                msgEl.style.color = '#f87171';
            }
            return false;
        }

        const data = await res.json();

        if (res.ok) {
            const banner = document.getElementById('paySuccessBanner');
            if (banner) {
                banner.classList.add('show');
                banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            if (msgEl) {
                msgEl.style.color = '#81c784';
                msgEl.textContent = '⏳ Payment submitted. Please wait for confirmation — the owner has been notified and will verify your transaction before activating your plan.';
            }
            showStatus('Payment submitted. Waiting for owner confirmation. Access activates after verification.', 'info');
            // Keep plan/method; clear sensitive fields only
            const txn = document.getElementById('payTxn');
            if (txn) txn.value = '';
            const sender = document.getElementById('paySender');
            if (sender) sender.value = '';
        } else {
            const errorMsg = data.detail || data.message || 'Could not submit payment.';
            if (msgEl) {
                msgEl.textContent = `⚠️ ${errorMsg}`;
                msgEl.style.color = '#f87171';
            }
        }
    } catch (err) {
        console.error('Payment submission error:', err);
        if (msgEl) {
            msgEl.textContent = '⚠️ Connection error. Please try again.';
            msgEl.style.color = '#f87171';
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit payment for verification';
        }
    }

    return false;
}

// ============================================================
// 🚀 INITIALIZATION
// ============================================================

// Apply theme on load
applyTheme(savedTheme);

// Add event listener for theme toggle when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Prevent duplicate execution
    if (window._visionUpgradeDOMReady) return;
    window._visionUpgradeDOMReady = true;

    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }
    
    // Load plans
    loadPlans();

    // Load Easypaisa/bank payment details
    loadPaymentMethods();
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const statusMsg = document.getElementById('statusMsg');
            if (statusMsg) {
                statusMsg.classList.remove('show');
            }
        }
    });
    
    console.log('👁️ Vision AI Upgrade v3.2.0 - Ready');
});

// ============================================================
// 🟢 ADDITIONAL SAFEGUARDS
// ============================================================

// Prevent multiple initializations
if (window._visionUpgradeInitialized) {
    console.warn('Vision AI Upgrade already initialized!');
} else {
    window._visionUpgradeInitialized = true;
}

// Global error handler
window.onerror = function(msg, url, line, col, error) {
    console.error('Global error:', msg, error);
    showStatus('An unexpected error occurred. Please refresh the page.', 'error');
    return true;
};

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showStatus('An unexpected error occurred.', 'error');
});

// ============================================================
// 🔄 EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================================

window.applyTheme = applyTheme;
window.toggleTheme = toggleTheme;
window.getAccessToken = getAccessToken;
window.clearTokens = clearTokens;
window.authedFetch = authedFetch;
window.loadPlans = loadPlans;
window.handlePlanAction = handlePlanAction;
window.showStatus = showStatus;
window.escapeHtml = escapeHtml;
window.formatPrice = formatPrice;

// ============================================================
// 🎨 ADD STYLES (if not already present)
// ============================================================

if (!document.getElementById('upgradeStyles')) {
    const style = document.createElement('style');
    style.id = 'upgradeStyles';
    style.textContent = `
        .status-msg {
            margin: 16px auto;
            padding: 12px 16px;
            border-radius: 10px;
            display: none;
            font-size: 14px;
            max-width: 600px;
            text-align: center;
            animation: fadeIn 0.3s ease;
        }
        .status-msg.show {
            display: block;
        }
        .status-msg.success {
            background: rgba(34, 197, 94, 0.1);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.2);
        }
        .status-msg.error {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }
        .status-msg.info {
            background: rgba(0, 198, 255, 0.1);
            color: #00C6FF;
            border: 1px solid rgba(0, 198, 255, 0.2);
        }
        .plans-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            padding: 20px 0;
            max-width: 1100px;
            margin: 0 auto;
        }
        .plan-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
        }
        .plan-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }
        .plan-card.current {
            border-color: #00C6FF;
            box-shadow: 0 0 30px rgba(0, 198, 255, 0.1);
        }
        .plan-card.popular {
            border-color: #7B68EE;
            box-shadow: 0 0 30px rgba(123, 104, 238, 0.1);
        }
        .plan-name {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 8px;
        }
        .plan-price {
            font-size: 32px;
            font-weight: 700;
            color: var(--text-main);
            margin: 12px 0;
        }
        .plan-price sup {
            font-size: 16px;
            font-weight: 600;
        }
        .plan-price .per {
            font-size: 14px;
            font-weight: 400;
            color: var(--text-muted);
        }
        .popular-badge {
            background: linear-gradient(135deg, #7B68EE, #00C6FF);
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 8px;
        }
        .plan-features {
            list-style: none;
            padding: 0;
            margin: 16px 0;
            text-align: left;
        }
        .plan-features li {
            padding: 6px 0;
            color: var(--text-main);
            font-size: 14px;
            border-bottom: 1px solid var(--border-subtle);
        }
        .plan-features li:last-child {
            border-bottom: none;
        }
        .plan-features li::before {
            content: "✓ ";
            color: #22c55e;
            font-weight: 700;
        }
        .plan-btn {
            width: 100%;
            padding: 12px;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .plan-btn.upgrade {
            background: linear-gradient(135deg, #00C6FF, #7B68EE);
            color: white;
        }
        .plan-btn.upgrade:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 20px rgba(0, 198, 255, 0.3);
        }
        .plan-btn.downgrade {
            background: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border-color);
        }
        .plan-btn.downgrade:hover {
            border-color: #ef4444;
            color: #ef4444;
        }
        .plan-btn.current-btn {
            background: rgba(0, 198, 255, 0.1);
            color: #00C6FF;
            border: 1px solid rgba(0, 198, 255, 0.2);
            cursor: default;
        }
        .plan-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        #currentPlanBanner {
            display: none;
            text-align: center;
            padding: 16px 24px;
            background: rgba(0, 198, 255, 0.05);
            border: 1px solid rgba(0, 198, 255, 0.1);
            border-radius: 12px;
            margin: 16px auto 0;
            max-width: 600px;
            color: var(--text-main);
            font-size: 14px;
        }
        #currentPlanBanner strong {
            color: #00C6FF;
        }
    `;
    document.head.appendChild(style);
}

console.log('👁️ Vision AI Upgrade - Ready');