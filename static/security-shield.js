/**
 * WB ARD Department - Administrative Data Protection & Security Shield Script
 * 
 * Features:
 * 1. Dynamic Forensic Watermarking (officer identity, live timestamp, session hash, anti-tamper observer)
 * 2. Mobile Touch Callout & Text Selection Suppression (anti-copy to WhatsApp / social apps)
 * 3. Print & PDF Export Lockdown (anti-print shield + Ctrl/Cmd+P interception)
 * 4. App-Switch Privacy Curtain (blurs content on multitasking/task switcher)
 */

(function () {
    'use strict';

    // =========================================================================
    // 1. STATE & USER RESOLUTION
    // =========================================================================

    function getSessionId() {
        try {
            let id = localStorage.getItem('ard_visitor_session_id');
            if (!id) {
                id = 'sess_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now().toString(36);
                localStorage.setItem('ard_visitor_session_id', id);
            }
            return id;
        } catch (e) {
            return 'sess_wb_ard';
        }
    }

    function getOfficerIdentity() {
        // 1. Check active session storage from index.html auth gate
        const sessName = sessionStorage.getItem('avd_officer_name');
        if (sessName && sessName.trim() && sessName.trim() !== 'Officer') {
            return sessName.trim();
        }

        // 2. Check DOM user badge if already rendered
        const badgeEl = document.getElementById('authHeaderUserName');
        if (badgeEl && badgeEl.textContent && badgeEl.textContent.trim() && badgeEl.textContent.trim() !== 'Officer') {
            return badgeEl.textContent.trim();
        }

        // 3. Check review page input #who
        const whoEl = document.getElementById('who');
        if (whoEl && whoEl.value && whoEl.value.trim()) {
            return whoEl.value.trim();
        }

        // 4. Check localStorage fallback
        const localName = localStorage.getItem('avd_officer_name');
        if (localName && localName.trim()) {
            return localName.trim();
        }

        return 'WB ARD OFFICIAL USER';
    }

    function formatTimestamp() {
        const now = new Date();
        const d = String(now.getDate()).padStart(2, '0');
        const m = now.toLocaleString('en-US', { month: 'short' });
        const y = now.getFullYear();
        const hrs = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        const secs = String(now.getSeconds()).padStart(2, '0');
        return `${d}-${m}-${y} ${hrs}:${mins}:${secs} IST`;
    }

    function escapeXml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&apos;');
    }

    // =========================================================================
    // 2. DYNAMIC FORENSIC WATERMARK ENGINE
    // =========================================================================

    function buildWatermarkSvg(officer, timestamp, session) {
        const w = 420;
        const h = 260;
        const line1 = 'WB ARD GOVT RECORD • CONFIDENTIAL';
        const line2 = `${officer} • [${session.slice(0, 14)}]`;
        const line3 = `${timestamp} • STRICTLY CONFIDENTIAL`;
        const line4 = 'UNAUTHORIZED SCREENSHOT / FORWARDING PROHIBITED';

        // Dual-tone opacity renders clearly on both dark & light backgrounds
        const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
            <g transform="rotate(-24 210 130)">
                <text x="210" y="65" fill="rgba(100, 116, 139, 0.14)" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="1.2" text-anchor="middle">${escapeXml(line1)}</text>
                <text x="210" y="98" fill="rgba(15, 23, 42, 0.19)" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="800" letter-spacing="1.5" text-anchor="middle">${escapeXml(line2)}</text>
                <text x="210" y="130" fill="rgba(2, 132, 199, 0.18)" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="700" letter-spacing="1" text-anchor="middle">${escapeXml(line3)}</text>
                <text x="210" y="160" fill="rgba(220, 38, 38, 0.17)" font-family="system-ui, -apple-system, sans-serif" font-size="10" font-weight="700" letter-spacing="1" text-anchor="middle">${escapeXml(line4)}</text>
            </g>
        </svg>`.trim();

        return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
    }

    let watermarkEl = null;

    function applyWatermark() {
        if (!document.body) return;

        if (!watermarkEl || !document.body.contains(watermarkEl)) {
            let existing = document.getElementById('ard-security-watermark');
            if (existing) {
                watermarkEl = existing;
            } else {
                watermarkEl = document.createElement('div');
                watermarkEl.id = 'ard-security-watermark';
                document.body.appendChild(watermarkEl);
            }
        }

        const officer = getOfficerIdentity();
        const timestamp = formatTimestamp();
        const session = getSessionId();
        const svgUri = buildWatermarkSvg(officer, timestamp, session);

        watermarkEl.style.backgroundImage = `url("${svgUri}")`;

        // Update meta in print shield as well
        const shieldMeta = document.getElementById('ardPrintShieldMeta');
        if (shieldMeta) {
            shieldMeta.textContent = `Access Session: ${session} | Officer: ${officer} | Security Stamp: ${timestamp}`;
        }
    }

    window.updateSecurityWatermark = applyWatermark;

    // Refresh watermark timestamp every 30 seconds
    setInterval(applyWatermark, 30000);

    // Anti-Tamper Observer: prevent removal of watermark
    function setupTamperProtection() {
        if (!document.body) return;
        const observer = new MutationObserver(function (mutations) {
            let needsReattach = false;
            for (let i = 0; i < mutations.length; i++) {
                const mut = mutations[i];
                if (mut.type === 'childList') {
                    for (let j = 0; j < mut.removedNodes.length; j++) {
                        if (mut.removedNodes[j].id === 'ard-security-watermark') {
                            needsReattach = true;
                            break;
                        }
                    }
                }
            }
            if (needsReattach || !document.getElementById('ard-security-watermark')) {
                applyWatermark();
            }
        });

        observer.observe(document.body, { childList: true });
    }

    // =========================================================================
    // 3. SECURITY TOAST NOTIFICATION
    // =========================================================================

    let toastEl = null;
    let toastTimeout = null;

    function showSecurityToast(message) {
        if (!toastEl) {
            toastEl = document.createElement('div');
            toastEl.id = 'ard-security-toast';
            toastEl.innerHTML = `
                <svg class="w-4 h-4 text-rose-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" width="16" height="16">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                <span id="ard-security-toast-text">${escapeXml(message)}</span>
            `;
            document.body.appendChild(toastEl);
        } else {
            const txt = document.getElementById('ard-security-toast-text');
            if (txt) txt.textContent = message;
        }

        toastEl.classList.add('show');
        if (toastTimeout) clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {
            if (toastEl) toastEl.classList.remove('show');
        }, 3200);
    }

    // =========================================================================
    // 4. PRINT & PDF EXPORT SHIELD SETUP
    // =========================================================================

    function setupPrintShield() {
        if (document.getElementById('ard-print-security-shield')) return;

        const shield = document.createElement('div');
        shield.id = 'ard-print-security-shield';
        shield.innerHTML = `
            <img src="/static/wb_state_emblem.png" alt="Government of West Bengal" class="shield-emblem" onerror="this.style.display='none'">
            <div class="shield-badge">Confidential Government Record</div>
            <div class="shield-dept">Animal Resources Development Department • Govt. of West Bengal</div>
            <h1 class="shield-title">PRINTING &amp; PDF EXPORT PROHIBITED</h1>
            <p class="shield-desc">
                Direct printing, digital PDF export, and unauthorized reproduction of ARD Posting Board records 
                are strictly prohibited under state administrative data protection protocols.
            </p>
            <div class="shield-warning">
                All records accessed on this system are tracked under official cyber audit regulations. 
                Duplication or unauthorized dissemination will invite disciplinary action under the West Bengal Services (Classification, Control and Appeal) Rules.
            </div>
            <div class="shield-meta" id="ardPrintShieldMeta">
                Security Stamp: ${formatTimestamp()} | Official Cadre Decision Board
            </div>
        `;
        document.body.appendChild(shield);
    }

    // =========================================================================
    // 5. PRIVACY CURTAIN SETUP (App Switcher / Inactive Tab Blur)
    // =========================================================================

    function setupPrivacyCurtain() {
        if (document.getElementById('ard-privacy-curtain')) return;

        const curtain = document.createElement('div');
        curtain.id = 'ard-privacy-curtain';
        curtain.innerHTML = `
            <div style="max-width: 320px; padding: 24px; background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
                <div style="font-size: 28px; margin-bottom: 8px;">🔒</div>
                <div style="font-size: 15px; font-weight: 700; color: #ffffff; margin-bottom: 4px;">Protected Screen</div>
                <div style="font-size: 12px; color: #94a3b8; line-height: 1.5;">ARD confidential records are hidden while switching apps. Tap anywhere to resume.</div>
            </div>
        `;
        document.body.appendChild(curtain);

        // Visibility change handler
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                document.documentElement.classList.add('ard-privacy-blur');
            } else {
                document.documentElement.classList.remove('ard-privacy-blur');
            }
        });

        // Window blur/focus handler
        window.addEventListener('blur', () => {
            document.documentElement.classList.add('ard-privacy-blur');
        });
        window.addEventListener('focus', () => {
            document.documentElement.classList.remove('ard-privacy-blur');
        });

        // Tap curtain to resume
        curtain.addEventListener('click', () => {
            document.documentElement.classList.remove('ard-privacy-blur');
        });
    }

    // =========================================================================
    // 6. EVENT INTERCEPTORS (Anti-Copy, Anti-Print, Anti-Context Menu)
    // =========================================================================

    function setupInterceptors() {
        // 1. Prevent Right-Click & Long-Press Context Menu (except input / textarea)
        document.addEventListener('contextmenu', function (e) {
            const tag = e.target.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
                e.preventDefault();
                showSecurityToast('Context menu and options are disabled for security.');
                return false;
            }
        }, true);

        // 2. Prevent Copy (anti-copying to WhatsApp / clipboard)
        document.addEventListener('copy', function (e) {
            const tag = e.target.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
                e.preventDefault();
                if (e.clipboardData) {
                    e.clipboardData.setData('text/plain', 'Confidential Government Record — Copying is strictly prohibited.');
                }
                showSecurityToast('Copying data to clipboard is prohibited.');
                return false;
            }
        }, true);

        // 3. Prevent Cut
        document.addEventListener('cut', function (e) {
            const tag = e.target.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
                e.preventDefault();
                return false;
            }
        }, true);

        // 4. Prevent Native Drag & Drop of Images / Tables
        document.addEventListener('dragstart', function (e) {
            const tag = e.target.tagName;
            if (tag === 'IMG' || tag === 'A' || tag === 'TABLE' || tag === 'DIV') {
                e.preventDefault();
                return false;
            }
        }, true);

        // 5. Intercept Print & Save Shortcuts (Ctrl/Cmd + P, Ctrl/Cmd + S)
        window.addEventListener('keydown', function (e) {
            // Print shortcut: Ctrl+P / Cmd+P
            if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P')) {
                e.preventDefault();
                e.stopPropagation();
                showSecurityToast('Direct printing & PDF export are prohibited.');
                return false;
            }

            // Save Page shortcut: Ctrl+S / Cmd+S
            if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
                e.preventDefault();
                e.stopPropagation();
                showSecurityToast('Saving offline copy is prohibited.');
                return false;
            }

            // View Source shortcut: Ctrl+U / Cmd+U
            if ((e.ctrlKey || e.metaKey) && (e.key === 'u' || e.key === 'U')) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        }, true);

        // 6. Before-Print event handler
        window.addEventListener('beforeprint', function () {
            applyWatermark();
        });
    }

    // =========================================================================
    // 7. INITIALIZATION
    // =========================================================================

    function initSecurityShield() {
        setupPrintShield();
        setupPrivacyCurtain();
        applyWatermark();
        setupTamperProtection();
        setupInterceptors();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSecurityShield);
    } else {
        initSecurityShield();
    }

})();
