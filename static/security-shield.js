/**
 * WB ARD Department - Administrative Data Protection & Security Shield Script
 * 
 * Strict Privacy Protocols:
 * 1. Watermark ONLY includes "CONFIDENTIAL" (no names, no personal information).
 * 2. Universal touch callout & text selection suppression (anti-copy / anti-forwarding).
 * 3. Print & PDF Export Lockdown (anti-print shield + shortcut blocking).
 * 4. App-Switch Privacy Curtain (content blur on multitasking/screen capture).
 */

(function () {
    'use strict';

    // =========================================================================
    // 1. WATERMARK ENGINE (ONLY "CONFIDENTIAL")
    // =========================================================================

    function buildWatermarkSvg() {
        const w = 280;
        const h = 160;
        // The watermark strictly and exclusively contains "CONFIDENTIAL"
        const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
            <g transform="rotate(-26 140 80)">
                <text x="140" y="86" fill="rgba(148, 163, 184, 0.13)" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="900" letter-spacing="4" text-anchor="middle">CONFIDENTIAL</text>
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

        const svgUri = buildWatermarkSvg();
        watermarkEl.style.backgroundImage = `url("${svgUri}")`;
    }

    window.updateSecurityWatermark = applyWatermark;

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
    // 2. SECURITY TOAST NOTIFICATION
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
                <span id="ard-security-toast-text">${message}</span>
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
    // 3. PRINT & PDF EXPORT SHIELD SETUP
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
                All records accessed on this system are governed by official administrative confidentiality regulations. 
                Duplication or unauthorized dissemination is strictly prohibited.
            </div>
            <div class="shield-meta">
                Official Cadre Decision Board • Restricted Administrative System
            </div>
        `;
        document.body.appendChild(shield);
    }

    // =========================================================================
    // 4. PRIVACY CURTAIN SETUP (App Switcher / Inactive Tab Blur)
    // =========================================================================

    function setupPrivacyCurtain() {
        if (document.getElementById('ard-privacy-curtain')) return;

        const curtain = document.createElement('div');
        curtain.id = 'ard-privacy-curtain';
        curtain.innerHTML = `
            <div style="max-width: 320px; padding: 24px; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); text-align: center;">
                <div style="font-size: 28px; margin-bottom: 8px;">🔒</div>
                <div style="font-size: 15px; font-weight: 700; color: #ffffff; margin-bottom: 4px;">Protected Screen</div>
                <div style="font-size: 12px; color: #94a3b8; line-height: 1.5;">ARD confidential records are hidden while switching apps. Tap anywhere to resume.</div>
            </div>
        `;
        document.body.appendChild(curtain);

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                document.documentElement.classList.add('ard-privacy-blur');
            } else {
                document.documentElement.classList.remove('ard-privacy-blur');
            }
        });

        window.addEventListener('blur', () => {
            document.documentElement.classList.add('ard-privacy-blur');
        });
        window.addEventListener('focus', () => {
            document.documentElement.classList.remove('ard-privacy-blur');
        });

        curtain.addEventListener('click', () => {
            document.documentElement.classList.remove('ard-privacy-blur');
        });
    }

    // =========================================================================
    // 5. EVENT INTERCEPTORS (Anti-Copy, Anti-Print, Anti-Context Menu)
    // =========================================================================

    function setupInterceptors() {
        // 1. Prevent Right-Click & Long-Press Context Menu (except input / textarea)
        document.addEventListener('contextmenu', function (e) {
            const tag = e.target.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
                e.preventDefault();
                showSecurityToast('Context options are disabled for confidentiality.');
                return false;
            }
        }, true);

        // 2. Prevent Copy (anti-copying to clipboard / messaging)
        document.addEventListener('copy', function (e) {
            const tag = e.target.tagName;
            if (tag !== 'INPUT' && tag !== 'TEXTAREA') {
                e.preventDefault();
                if (e.clipboardData) {
                    e.clipboardData.setData('text/plain', 'CONFIDENTIAL');
                }
                showSecurityToast('Copying data is prohibited.');
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

        // 4. Prevent Drag & Drop of Images / Tables
        document.addEventListener('dragstart', function (e) {
            const tag = e.target.tagName;
            if (tag === 'IMG' || tag === 'A' || tag === 'TABLE' || tag === 'DIV') {
                e.preventDefault();
                return false;
            }
        }, true);

        // 5. Intercept Print & Save Shortcuts (Ctrl/Cmd + P, Ctrl/Cmd + S)
        window.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'p' || e.key === 'P')) {
                e.preventDefault();
                e.stopPropagation();
                showSecurityToast('Printing and PDF export are disabled.');
                return false;
            }

            if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
                e.preventDefault();
                e.stopPropagation();
                showSecurityToast('Saving offline copy is disabled.');
                return false;
            }

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
    // 6. INITIALIZATION
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
