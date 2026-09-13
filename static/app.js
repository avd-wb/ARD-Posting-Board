/**
 * app.js
 * Client-side Controller for WB ARD Department Smart Posting Decision Board.
 * Features:
 * - 1,794 Active Cadre Posts (Notification 1809)
 * - 106 Obliterated Posts (Notification 1808) with 84 Serving Officers
 * - 242 50-Point Roster Candidates & 242 Available Deputy Director Posts
 * - Dual Allotment System: Substantive Post + Optional Service Utilization (SU) Post
 * - Real-Time Dynamic Option Reduction: Chosen posts are automatically blocked from subsequent choices
 * - Collision & Forced Displacement Detection
 * - Automated Backup, Snapshot, and Rollback Manager
 * - Local Network & Online Public Sharing
 */

document.addEventListener('DOMContentLoaded', () => {
    // State management
    const state = {
        currentTab: 'tab-roster',
        overview: {},
        rosterCandidates: [],
        obliteratedOfficers: [],
        cadreData: [],
        cadreTotal: 0,
        cadreLimit: 100,
        cadreOffset: 0,
        orders: [],
        districts: [],
        designations: [],
        activeModalOfficer: null,
        activeModalRole: 'roster',
        substantivePosts: [],
        suPosts: []
    };

    // --- VISITOR & ACCESS INTELLIGENCE TELEMETRY ENGINE ---
    function getOrCreateVisitorSession() {
        let id = localStorage.getItem('ard_visitor_session_id');
        if (!id) {
            id = 'sess_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
            localStorage.setItem('ard_visitor_session_id', id);
        }
        return id;
    }

    const telemetryState = {
        sessionId: getOrCreateVisitorSession(),
        activeSeconds: 0,
        lastReportedSeconds: 0,
        currentPage: '50-Point Roster',
        screenResolution: `${window.screen.width}x${window.screen.height}`,
        clientGeo: null
    };

    function sendTelemetryPing(eventType = 'heartbeat', pageTitle = null) {
        if (pageTitle) telemetryState.currentPage = pageTitle;
        const delta = Math.max(0, telemetryState.activeSeconds - telemetryState.lastReportedSeconds);
        telemetryState.lastReportedSeconds = telemetryState.activeSeconds;

        const payload = {
            session_id: telemetryState.sessionId,
            event_type: eventType,
            page: telemetryState.currentPage,
            time_spent_delta: delta,
            screen_resolution: telemetryState.screenResolution,
            client_geo: telemetryState.clientGeo,
            user_agent: navigator.userAgent
        };

        try {
            if (navigator.sendBeacon && (eventType === 'unload' || eventType === 'hide')) {
                const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
                navigator.sendBeacon('/api/analytics/track', blob);
            } else {
                fetch('/api/analytics/track', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    keepalive: true
                }).catch(() => {});
            }
        } catch (e) {
            // Non-blocking telemetry
        }
    }
    window.sendTelemetryPing = sendTelemetryPing;

    function initVisitorTelemetry() {
        sendTelemetryPing('pageview', '50-Point Roster');

        setInterval(() => {
            if (document.visibilityState === 'visible') {
                telemetryState.activeSeconds++;
            }
        }, 1000);

        setInterval(() => {
            if (telemetryState.activeSeconds > telemetryState.lastReportedSeconds) {
                sendTelemetryPing('heartbeat');
            }
        }, 20000);

        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                sendTelemetryPing('hide');
            }
        });
        window.addEventListener('pagehide', () => sendTelemetryPing('unload'));
        window.addEventListener('beforeunload', () => sendTelemetryPing('unload'));
    }

    // --- INITIALIZATION ---
    initTabs();
    initOverview();
    initFilters();
    loadRoster();
    loadMasterOrders();
    loadObliterated();
    loadCadre();
    loadOrders();
    loadDisplacedPool();
    initSimulationControls();
    initBetaSyncCountdown();
    initKPICardClickHandlers();
    initSpotlightSearch();
    initPolicyGuideModal();
    initLivePolicyEvaluator();
    initVisitorTelemetry();
    initVisitorAnalyticsUI();

    // Debounce helper
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // --- TAB SWITCHING & MOBILE NAVIGATION ---
    function switchTab(targetTab) {
        if (!targetTab) return;
        state.currentTab = targetTab;

        // 1. Desktop Tab Buttons (Executive Slate Pills)
        const tabButtons = document.querySelectorAll('#navTabs .tab-btn');
        tabButtons.forEach(b => {
            if (b.getAttribute('data-tab') === targetTab) {
                b.classList.add('bg-white', 'text-slate-900', 'shadow-xs');
                b.classList.remove('text-slate-300', 'text-neutral-400', 'hover:text-white', 'hover:bg-slate-800/60', 'hover:bg-neutral-800/60');
            } else {
                b.classList.remove('bg-white', 'text-slate-900', 'text-black', 'shadow-xs');
                b.classList.add('text-slate-300', 'hover:text-white', 'hover:bg-slate-800/60');
            }
        });

        // 1b. Central Header Organogram Button (Prominent Center Piece)
        const organogramHeaderBtn = document.getElementById('btnHeaderOrganogram');
        if (organogramHeaderBtn) {
            if (targetTab === 'tab-organogram') {
                organogramHeaderBtn.className = "inline-flex items-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-1.5 rounded-xl bg-amber-400 text-slate-950 font-black text-xs sm:text-sm border border-amber-300 shadow-md transition active:scale-95 group text-center shrink-0";
                const icon = organogramHeaderBtn.querySelector('i');
                if (icon) icon.className = "w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-950 shrink-0";
            } else {
                organogramHeaderBtn.className = "inline-flex items-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-1.5 rounded-xl bg-slate-700/90 hover:bg-slate-650 text-white font-bold text-xs sm:text-sm border border-amber-400/60 hover:border-amber-300 shadow-sm transition active:scale-95 group text-center shrink-0";
                const icon = organogramHeaderBtn.querySelector('i');
                if (icon) icon.className = "w-3.5 h-3.5 sm:w-4 sm:h-4 text-amber-300 group-hover:scale-110 transition shrink-0";
            }
        }

        // 2. Mobile Bottom Bar Buttons
        const mobileTabButtons = document.querySelectorAll('.mobile-tab-btn');
        mobileTabButtons.forEach(btn => {
            const isMatch = btn.getAttribute('data-tab') === targetTab;
            const pill = btn.querySelector('.tab-pill');
            const label = btn.querySelector('span:not(.tab-pill)');
            if (isMatch) {
                btn.classList.add('text-wbblue-800');
                btn.classList.remove('text-slate-500');
                if (pill) {
                    pill.classList.add('bg-wbblue-100', 'text-wbblue-900');
                    pill.classList.remove('text-slate-500');
                }
                if (label) {
                    label.classList.add('font-bold');
                    label.classList.remove('font-medium');
                }
            } else {
                btn.classList.remove('text-wbblue-800');
                btn.classList.add('text-slate-500');
                if (pill) {
                    pill.classList.remove('bg-wbblue-100', 'text-wbblue-900');
                    pill.classList.add('text-slate-500');
                }
                if (label) {
                    label.classList.remove('font-bold');
                    label.classList.add('font-medium');
                }
            }
        });

        // 3. Auto-close mobile drawer if open
        const mobileDrawer = document.getElementById('mobileDrawerModal');
        if (mobileDrawer && !mobileDrawer.classList.contains('hidden')) {
            mobileDrawer.classList.add('hidden');
        }

        // 4. Toggle Content Panes
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.add('hidden'));
        const activeContent = document.getElementById(targetTab);
        if (activeContent) {
            activeContent.classList.remove('hidden');
        }

        // 5. Update KPI card highlights if available
        if (window.setActiveKPICard) {
            if (targetTab === 'tab-roster') window.setActiveKPICard('kpiCardRoster');
            else if (targetTab === 'tab-obliterated') window.setActiveKPICard('kpiCardObliterated');
            else if (targetTab === 'tab-cadre') window.setActiveKPICard('kpiCardTotalPosts');
            else if (targetTab === 'tab-displaced') window.setActiveKPICard('kpiCardCollisions');
        }

        // 6. Trigger specific tab loaders
        if (targetTab === 'tab-roster') {
            loadRoster();
        } else if (targetTab === 'tab-master-orders') {
            loadMasterOrders();
        } else if (targetTab === 'tab-obliterated') {
            loadObliterated();
        } else if (targetTab === 'tab-cadre') {
            loadCadre();
        } else if (targetTab === 'tab-cascade') {
            loadSimulationHistory();
            loadCascadingBackfills();
        } else if (targetTab === 'tab-displaced') {
            loadDisplacedPool();
        } else if (targetTab === 'tab-visual-grid') {
            window.renderVisualGrid('visualGridBody', false, null);
        } else if (targetTab === 'tab-master-directory') {
            loadMasterDirectory();
        } else if (targetTab === 'tab-organogram') {
            if (window.renderOrganogram) window.renderOrganogram();
        }

        // 7. Auto scroll smoothly to content top on mobile
        if (window.innerWidth < 768) {
            const tabsNav = document.getElementById('navTabs') || document.getElementById('mainContentArea');
            if (tabsNav) {
                const rect = tabsNav.getBoundingClientRect();
                if (rect.top < 0) {
                    window.scrollTo({ top: window.scrollY + rect.top - 60, behavior: 'smooth' });
                }
            }
        }

        // 8. Telemetry tracking for tab navigation
        if (window.sendTelemetryPing) {
            const tabNameMap = {
                'tab-roster': '50-Point Roster',
                'tab-master-orders': 'Master Schedule',
                'tab-obliterated': 'Obliterated Posts',
                'tab-cadre': 'Cadre & Vacancies',
                'tab-displaced': 'Displaced Officers',
                'tab-cascade': 'Cascade Simulation',
                'tab-orders': 'Official Orders',
                'tab-visual-grid': 'Visual Cadre Grid',
                'tab-master-directory': 'Master Directory',
                'tab-organogram': 'Department Organogram'
            };
            window.sendTelemetryPing('tab_switch', tabNameMap[targetTab] || targetTab);
        }

        if (window.lucide) window.lucide.createIcons();
    }
    window.switchTab = switchTab;

    function initTabs() {
        // Desktop tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
        });

        // Header Organogram Button
        const btnHeaderOrg = document.getElementById('btnHeaderOrganogram');
        if (btnHeaderOrg) {
            btnHeaderOrg.addEventListener('click', () => switchTab('tab-organogram'));
        }

        // Mobile bottom nav tabs
        document.querySelectorAll('.mobile-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
        });

        // Mobile drawer tabs
        document.querySelectorAll('.mobile-drawer-btn').forEach(btn => {
            btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
        });

        // Mobile Drawer Toggle
        const mobileDrawer = document.getElementById('mobileDrawerModal');
        const btnOpenDrawer = document.getElementById('btnOpenMobileDrawer');
        const btnHeaderMenu = document.getElementById('btnHeaderMobileMenu');
        const btnCloseDrawer = document.getElementById('btnCloseMobileDrawer');
        const drawerHandle = document.getElementById('mobileDrawerHandle');

        const openDrawer = () => {
            if (mobileDrawer) {
                mobileDrawer.classList.remove('hidden');
                if (window.lucide) window.lucide.createIcons();
            }
        };

        const closeDrawer = () => {
            if (mobileDrawer) mobileDrawer.classList.add('hidden');
        };

        if (btnOpenDrawer) btnOpenDrawer.addEventListener('click', openDrawer);
        if (btnHeaderMenu) btnHeaderMenu.addEventListener('click', openDrawer);
        if (btnCloseDrawer) btnCloseDrawer.addEventListener('click', closeDrawer);
        if (drawerHandle) drawerHandle.addEventListener('click', closeDrawer);

        if (mobileDrawer) {
            mobileDrawer.addEventListener('click', (e) => {
                if (e.target === mobileDrawer) closeDrawer();
            });
        }
    }

    // --- LOAD OVERVIEW KPIS ---
    async function initOverview() {
        try {
            const res = await fetch('/api/overview');
            const data = await res.json();
            state.overview = data;

            document.getElementById('kpiTotalPosts').innerText = Number(data.total_posts).toLocaleString();
            if (document.getElementById('badgeCadreTotal')) {
                document.getElementById('badgeCadreTotal').innerText = Number(data.total_posts).toLocaleString();
            }
            document.getElementById('kpiTotalVacancies').innerText = Number(data.total_vacancies).toLocaleString();
            const allottedDD = data.allotted_dd != null ? data.allotted_dd : 242;
            const totalDD = data.total_dd_posts != null ? data.total_dd_posts : 244;
            const vacantDD = data.vacant_dd != null ? data.vacant_dd : 2;
            document.getElementById('kpiVacantDD').innerText = `${allottedDD} / ${totalDD}`;
            const kpiVacantDDSub = document.getElementById('kpiVacantDDSub');
            if (kpiVacantDDSub) {
                kpiVacantDDSub.innerHTML = `<span>Promotions Allotted (${vacantDD} Left)</span><i data-lucide="arrow-right" class="w-2 h-2 opacity-0 group-hover:opacity-100 transition"></i>`;
            }
            document.getElementById('kpiVacantAD').innerText = Number(data.vacant_ad).toLocaleString();
            document.getElementById('kpiRoster').innerText = data.roster_candidates;
            document.getElementById('kpiRosterSub').innerText = `Pending: ${data.roster_candidates - data.roster_allotted}`;
            document.getElementById('kpiObliterated').innerText = data.obliterated_posts;
            document.getElementById('kpiOblitSub').innerText = `${data.obliterated_officers} Serving (${data.obliterated_officers - data.obliterated_rehabilitated} Pending)`;
            document.getElementById('kpiOverTenure').innerText = data.over_tenure_count;

            document.getElementById('badgeRosterCount').innerText = `${data.roster_allotted}/${data.roster_candidates}`;
            document.getElementById('badgeOblitCount').innerText = `${data.obliterated_rehabilitated}/${data.obliterated_officers}`;
        } catch (e) {
            console.error('Error loading overview stats:', e);
        }
    }

    // --- POPULATE FILTER DROPDOWNS ---
    async function initFilters() {
        try {
            const [distRes, desigRes] = await Promise.all([
                fetch('/api/districts'),
                fetch('/api/designations')
            ]);
            state.districts = await distRes.json();
            state.designations = await desigRes.json();

            const distSelect = document.getElementById('cadreDistrictFilter');
            const moDistSelect = document.getElementById('masterOrdersDistrictFilter');
            state.districts.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.innerText = d;
                distSelect.appendChild(opt);

                if (moDistSelect) {
                    const opt2 = document.createElement('option');
                    opt2.value = d;
                    opt2.innerText = d;
                    moDistSelect.appendChild(opt2);
                }
            });

            const desigSelect = document.getElementById('cadreDesigFilter');
            state.designations.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.innerText = d;
                desigSelect.appendChild(opt);
            });
        } catch (e) {
            console.error('Error initializing dropdown filters:', e);
        }
    }

    // --- MONOGRAM AVATAR HELPER ---
    function getMonogram(name) {
        if (!name) return 'WB';
        const clean = name.replace(/^Dr\.\s*/i, '').replace(/\s*\([^)]*\)/g, '').replace(/[^a-zA-Z\s]/g, '').trim();
        const parts = clean.split(/\s+/).filter(Boolean);
        if (parts.length === 0) return 'WB';
        if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    // --- TAB 1: LOAD 50-POINT ROSTER ---
    async function loadRoster() {
        const tbody = document.getElementById('rosterTableBody');
        const cat = document.getElementById('rosterCategoryFilter').value;
        const status = document.getElementById('rosterStatusFilter').value;
        const search = document.getElementById('rosterSearchInput').value;

        let url = `/api/roster?category=${encodeURIComponent(cat)}&allotment_status=${encodeURIComponent(status)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        try {
            const res = await fetch(url);
            const json = await res.json();
            state.rosterCandidates = json.data;

            const cardsEl = document.getElementById('rosterMobileCards');

            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="10" class="py-8 text-center text-slate-400">No candidates match current criteria.</td></tr>`;
                if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-slate-400 text-xs">No candidates match current criteria.</div>`;
                return;
            }

            tbody.innerHTML = json.data.map(c => {
                const isAllotted = c.allotment_status === 'Allotted' || Boolean(c.master_sub);
                const statusBadge = isAllotted
                    ? `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">Allotted</span>`
                    : `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">Pending</span>`;

                const dualBadge = c.is_dual_obliterated === 1
                    ? `<span class="px-1.5 py-0.2 ml-1 text-[9px] font-semibold bg-rose-100 text-rose-700 border border-rose-200 rounded">Memo 1808 Post</span>`
                    : '';

                const prefDisplay = (c.pref_1 && c.pref_1 !== '—')
                    ? `<div class="truncate max-w-xs text-[11px]"><span class="font-semibold text-slate-700">1:</span> ${c.pref_1}</div>`
                    : `<span class="text-slate-400 italic">No preference submitted</span>`;

                const dorBadge = (c.dor && c.dor !== '—')
                    ? `<span class="font-mono text-slate-800 font-bold">${c.dor}</span>`
                    : (c.service_ends ? `<span class="font-mono text-slate-700 font-medium">${c.service_ends}</span>` : `<span class="text-slate-400">-</span>`);

                let allotmentDisplay = `<span class="text-amber-700 font-medium">Pending DD Allotment</span>`;
                if (c.master_sub) {
                    allotmentDisplay = `
                        <div class="space-y-1">
                            <div class="text-slate-900 font-bold text-[11px] leading-tight flex items-start gap-1">
                                <span class="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-900 border border-emerald-300 text-[9px] font-bold uppercase shrink-0 mt-0.5">Substantive</span>
                                <span>${c.master_sub}</span>
                            </div>
                            ${c.master_su && c.master_su !== 'Nil' ? `
                                <div class="text-teal-900 font-semibold text-[10px] leading-tight flex items-start gap-1">
                                    <span class="px-1.5 py-0.2 rounded bg-teal-100 text-teal-900 border border-teal-300 text-[9px] font-bold uppercase shrink-0 mt-0.5">SU</span>
                                    <span>${c.master_su}</span>
                                </div>
                            ` : ''}
                            ${c.master_basis ? `
                                <div class="text-[9px] text-slate-500 font-mono">${c.master_basis}</div>
                            ` : ''}
                        </div>
                    `;
                } else if (isAllotted) {
                    allotmentDisplay = `
                        <div class="space-y-0.5">
                            <div class="text-emerald-800 font-bold text-[11px] flex items-center gap-1">
                                <i data-lucide="check-circle" class="w-3 h-3 text-emerald-600"></i>
                                <span>Main: ${c.substantive_post_name || 'DD Post'}</span>
                            </div>
                            ${c.su_post_name ? `
                                <div class="text-teal-700 font-semibold text-[10px] flex items-center gap-1">
                                    <i data-lucide="arrow-right-circle" class="w-3 h-3 text-teal-600"></i>
                                    <span>SU: ${c.su_post_name}</span>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }

                const contactBar = (c.mobile && c.mobile !== '—') ? `
                    <div class="flex items-center gap-2 mt-1 text-[10px]">
                        <a href="tel:${c.mobile}" class="text-blue-600 hover:text-blue-800 flex items-center gap-0.5 font-mono font-medium" title="Call">
                            <i data-lucide="phone" class="w-2.5 h-2.5"></i> ${c.mobile}
                        </a>
                        <a href="https://wa.me/91${c.mobile}" target="_blank" class="text-emerald-600 hover:text-emerald-800 flex items-center gap-0.5 font-semibold" title="WhatsApp">
                            <i data-lucide="message-circle" class="w-2.5 h-2.5"></i> WA
                        </a>
                    </div>
                ` : '';

                const welfareBadges = [];
                if (c.children_board_exams && c.children_board_exams !== '—') {
                    welfareBadges.push(`<span class="px-1.5 py-0.2 rounded bg-purple-100 text-purple-800 text-[9px] font-bold" title="Children Board Exam ${c.children_board_exams}">Exam: ${c.children_board_exams}</span>`);
                }
                if (c.spouse_is_wbahvs) {
                    welfareBadges.push(`<span class="px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 text-[9px] font-bold" title="Spouse in WBAHVS / Public Service">Spouse WBAHVS</span>`);
                }
                if (c.health_conditions && c.health_conditions !== '—' && !c.health_conditions.includes('Standard')) {
                    welfareBadges.push(`<span class="px-1.5 py-0.2 rounded bg-rose-100 text-rose-800 text-[9px] font-bold" title="Medical Grounds">Medical</span>`);
                }

                return `
                    <tr class="hover:bg-slate-50 transition ${isAllotted ? 'bg-emerald-50/20' : ''}">
                        <td class="py-2.5 px-3 font-semibold text-slate-600">${c.sl_no}</td>
                        <td class="py-2.5 px-2 font-mono font-bold text-wbblue-800">${c.roster_point}</td>
                        <td class="py-2.5 px-2">
                            <span class="px-1.5 py-0.5 text-[10px] font-bold rounded ${c.point_reserved_for === 'SC' ? 'bg-amber-100 text-amber-900 border border-amber-300' : c.point_reserved_for === 'ST' ? 'bg-emerald-100 text-emerald-900 border border-emerald-300' : 'bg-slate-100 text-slate-700'}">
                                ${c.point_reserved_for}
                            </span>
                        </td>
                        <td class="py-2.5 px-4">
                            <div class="font-bold text-wbblue-900 hover:text-wbblue-600 hover:underline cursor-pointer flex items-center gap-1.5" onclick="openOfficerDossier('${c.hrms_id}')" title="Click to view full personnel dossier">
                                <span>${c.officer_name}</span>
                                ${dualBadge}
                            </div>
                            <div class="text-[11px] font-mono text-slate-500">HRMS: ${c.hrms_id || 'N/A'}</div>
                            ${contactBar}
                            ${welfareBadges.length > 0 ? `<div class="flex flex-wrap gap-1 mt-1">${welfareBadges.join('')}</div>` : ''}
                            ${c.attention_flag || c.is_dual_obliterated ? `
                                <div class="mt-1">
                                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300 text-[10px] font-bold animate-pulse">
                                        <i data-lucide="alert-triangle" class="w-3 h-3 text-rose-600"></i>
                                        <span>${c.attention_reason || 'Obliterated Post Incumbent'}</span>
                                    </span>
                                </div>
                            ` : (c.needs_backfill ? `
                                <div class="mt-1">
                                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold">
                                        <i data-lucide="corner-down-right" class="w-3 h-3 text-amber-700"></i>
                                        <span>Needs Field Backfill</span>
                                    </span>
                                </div>
                            ` : '')}
                        </td>
                        <td class="py-2.5 px-2 text-slate-700 font-medium">${c.caste}</td>
                        <td class="py-2.5 px-4">
                            <div class="text-slate-800 font-medium">${c.present_posting || '-'}</div>
                            <div class="text-[11px] text-slate-500 font-medium">
                                ${c.present_block ? `<span class="text-slate-700 font-semibold">${c.present_block} Block</span>, ` : ''}${c.present_district || 'District N/A'}
                            </div>
                        </td>
                        <td class="py-2.5 px-3">${dorBadge}</td>
                        <td class="py-2.5 px-4">${prefDisplay}</td>
                        <td class="py-2.5 px-4">${allotmentDisplay}</td>
                        <td class="py-2.5 px-3 text-right whitespace-nowrap">
                            <div class="flex items-center justify-end gap-1.5">
                                <button onclick="openOfficerDossier('${c.hrms_id}')" class="px-2 py-1 text-xs font-semibold rounded bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 transition" title="View Dossier">
                                    Dossier
                                </button>
                                <button onclick="openDualAllotModal('${c.hrms_id}', 'roster')" class="px-2 py-1 text-xs font-semibold rounded bg-wbblue-50 text-wbblue-700 hover:bg-wbblue-100 border border-wbblue-200 transition" title="Manual Post Allotment">
                                    ${isAllotted ? 'Modify' : 'Allot'}
                                </button>
                                <button onclick="openAIAllotModal('${c.hrms_id}', 'roster')" class="px-2 py-1 text-xs font-bold rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-sm transition flex items-center gap-1" title="Quick Statutory Allotment">
                                    <i data-lucide="zap" class="w-3 h-3"></i>
                                    <span>Quick</span>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');

            // Render Mobile Cards Feed (<md Screens)
            if (cardsEl) {
                cardsEl.innerHTML = json.data.map(c => {
                    const isAllotted = c.allotment_status === 'Allotted' || Boolean(c.master_sub);
                    const statusBadge = isAllotted
                        ? `<span class="px-2.5 py-1 rounded-full bg-emerald-100/90 text-emerald-800 text-[10px] font-bold inline-flex items-center gap-1 border border-emerald-300/60 shadow-2xs"><i data-lucide="check-circle" class="w-3 h-3 text-emerald-600"></i> Allotted</span>`
                        : `<span class="px-2.5 py-1 rounded-full bg-amber-100/90 text-amber-800 text-[10px] font-bold inline-flex items-center gap-1 border border-amber-300/60 shadow-2xs"><i data-lucide="clock" class="w-3 h-3 text-amber-600"></i> Pending</span>`;

                    const dualBadge = c.is_dual_obliterated === 1
                        ? `<span class="px-1.5 py-0.5 ml-1 text-[9px] font-semibold bg-rose-100 text-rose-700 border border-rose-200 rounded-md">Memo 1808</span>`
                        : '';

                    const dorBadge = (c.dor && c.dor !== '—')
                        ? `<span class="font-mono text-slate-800 font-bold">${c.dor}</span>`
                        : (c.service_ends ? `<span class="font-mono text-slate-700 font-medium">${c.service_ends}</span>` : `<span class="text-slate-400">-</span>`);

                    const initials = getMonogram(c.officer_name);

                    const contactBar = (c.mobile && c.mobile !== '—') ? `
                        <div class="grid grid-cols-2 gap-2 pt-1">
                            <a href="tel:${c.mobile}" class="h-10 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-xl text-center text-xs flex items-center justify-center gap-1.5 transition active:scale-95 touch-target btn-touch">
                                <i data-lucide="phone" class="w-3.5 h-3.5 text-blue-600"></i> Call (${c.mobile})
                            </a>
                            <a href="https://wa.me/91${c.mobile}" target="_blank" class="h-10 px-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-center text-xs flex items-center justify-center gap-1.5 shadow-xs shadow-emerald-600/20 transition active:scale-95 touch-target btn-touch">
                                <i data-lucide="message-circle" class="w-3.5 h-3.5"></i> WhatsApp
                            </a>
                        </div>
                    ` : '';

                    const welfareBadges = [];
                    if (c.children_board_exams && c.children_board_exams !== '—') {
                        welfareBadges.push(`<span class="px-2 py-0.5 rounded-lg bg-purple-100 text-purple-800 text-[10px] font-bold border border-purple-200">Exam: ${c.children_board_exams}</span>`);
                    }
                    if (c.spouse_is_wbahvs) {
                        welfareBadges.push(`<span class="px-2 py-0.5 rounded-lg bg-amber-100 text-amber-800 text-[10px] font-bold border border-amber-200">Spouse WBAHVS</span>`);
                    }
                    if (c.health_conditions && c.health_conditions !== '—' && !c.health_conditions.includes('Standard')) {
                        welfareBadges.push(`<span class="px-2 py-0.5 rounded-lg bg-rose-100 text-rose-800 text-[10px] font-bold border border-rose-200">Medical Grounds</span>`);
                    }

                    return `
                        <div class="rounded-2xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.04)] p-4 space-y-3.5 mobile-card-interactive">
                            <!-- Card Header -->
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-center gap-2.5 min-w-0">
                                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-wbblue-700 to-indigo-800 text-white font-bold flex items-center justify-center text-xs shadow-xs shrink-0 tracking-tight">
                                        ${initials}
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex flex-wrap items-center gap-1">
                                            <span class="px-1.5 py-0.5 rounded-md bg-slate-900 text-white font-mono text-[9px] font-bold">Sl ${c.sl_no}</span>
                                            <span class="px-1.5 py-0.5 rounded-md bg-wbblue-100 text-wbblue-900 font-mono text-[9px] font-bold">Pt ${c.roster_point}</span>
                                            <span class="px-1.5 py-0.5 rounded-md ${c.point_reserved_for === 'SC' ? 'bg-amber-100 text-amber-900 border border-amber-300 font-bold' : c.point_reserved_for === 'ST' ? 'bg-emerald-100 text-emerald-900 border border-emerald-300 font-bold' : 'bg-slate-100 text-slate-700 font-bold'} text-[9px]">${c.point_reserved_for} Quota</span>
                                        </div>
                                        <div class="font-extrabold text-sm text-slate-900 truncate cursor-pointer hover:text-wbblue-700 pt-0.5" onclick="openOfficerDossier('${c.hrms_id}')" title="Click to view dossier">
                                            ${c.officer_name} ${dualBadge}
                                        </div>
                                        <div class="text-[11px] font-mono text-slate-500 flex items-center gap-1.5 mt-0.5">
                                            <span>HRMS: <strong>${c.hrms_id || 'N/A'}</strong></span>
                                            <span>•</span>
                                            <span>DOR: ${dorBadge}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="shrink-0">${statusBadge}</div>
                            </div>

                            <!-- Welfare Badges if any -->
                            ${welfareBadges.length > 0 ? `<div class="flex flex-wrap gap-1.5">${welfareBadges.join('')}</div>` : ''}

                            <!-- Timeline Flow: Present Posting -> Allotted Substantive Post -->
                            <div class="space-y-1.5">
                                <!-- Origin -->
                                <div class="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                                        <i data-lucide="map-pin" class="w-3 h-3 text-slate-400"></i>
                                        <span>Present Station</span>
                                    </div>
                                    <div class="font-semibold text-slate-800 leading-snug mt-0.5">${c.present_posting || '-'}</div>
                                    <div class="text-[11px] text-slate-500 font-medium">
                                        ${c.present_block ? `<span class="text-slate-700 font-semibold">${c.present_block} Block</span>, ` : ''}${c.present_district || 'District N/A'}
                                    </div>
                                </div>

                                <!-- Flow indicator -->
                                <div class="flex items-center justify-center -my-0.5 text-slate-300">
                                    <i data-lucide="arrow-down" class="w-3 h-3 text-wbblue-500"></i>
                                </div>

                                <!-- Destination / Allotment Result -->
                                <div class="p-3 rounded-xl bg-gradient-to-r from-blue-50/80 via-indigo-50/40 to-emerald-50/60 border border-blue-200/80 text-xs space-y-1.5">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-wbblue-900 flex items-center gap-1">
                                        <i data-lucide="award" class="w-3 h-3 text-wbblue-600"></i>
                                        <span>Promotion Allotment Status</span>
                                    </div>
                                    ${c.master_sub ? `
                                        <div class="space-y-1">
                                            <div class="text-slate-900 font-bold text-xs leading-snug flex items-start gap-1">
                                                <span class="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-900 border border-emerald-300 text-[9px] font-bold uppercase shrink-0 mt-0.5">Substantive</span>
                                                <span>${c.master_sub}</span>
                                            </div>
                                            ${c.master_su && c.master_su !== 'Nil' ? `
                                                <div class="text-teal-900 font-semibold text-[11px] leading-snug flex items-start gap-1">
                                                    <span class="px-1.5 py-0.2 rounded bg-teal-100 text-teal-900 border border-teal-300 text-[9px] font-bold uppercase shrink-0 mt-0.5">SU</span>
                                                    <span>${c.master_su}</span>
                                                </div>
                                            ` : ''}
                                        </div>
                                    ` : (isAllotted ? `
                                        <div class="text-emerald-800 font-bold text-xs flex items-center gap-1">
                                            <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-600"></i>
                                            <span>${c.substantive_post_name || 'DD Post'}</span>
                                        </div>
                                    ` : `<span class="text-amber-700 font-semibold text-xs">Pending Deputy Director Allotment</span>`)}
                                </div>
                            </div>

                            ${(c.pref_1 && c.pref_1 !== '—') ? `
                                <div class="text-xs text-slate-600 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200/60 truncate">
                                    <strong class="text-slate-700">Pref 1:</strong> ${c.pref_1}
                                </div>
                            ` : ''}

                            <!-- Ergonomic Contact Buttons -->
                            ${contactBar}

                            <!-- 44px Touch Action Buttons -->
                            <div class="grid grid-cols-3 gap-2 pt-0.5">
                                <button onclick="openOfficerDossier('${c.hrms_id}')" class="h-10 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 flex items-center justify-center gap-1 transition active:scale-95 touch-target btn-touch">
                                    <i data-lucide="user" class="w-3.5 h-3.5"></i> Dossier
                                </button>
                                <button onclick="openDualAllotModal('${c.hrms_id}', 'roster')" class="h-10 text-xs font-bold rounded-xl bg-wbblue-50 hover:bg-wbblue-100 text-wbblue-800 border border-wbblue-200 flex items-center justify-center gap-1 transition active:scale-95 touch-target btn-touch">
                                    <i data-lucide="edit-3" class="w-3.5 h-3.5"></i> ${isAllotted ? 'Modify' : 'Allot'}
                                </button>
                                <button onclick="openAIAllotModal('${c.hrms_id}', 'roster')" class="h-10 text-xs font-bold rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 text-white flex items-center justify-center gap-1 shadow-xs transition active:scale-95 touch-target btn-touch" title="Quick Statutory Allotment">
                                    <i data-lucide="zap" class="w-3.5 h-3.5"></i> Quick Allot
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            lucide.createIcons();
        } catch (e) {
            console.error('Error loading roster:', e);
            tbody.innerHTML = `<tr><td colspan="10" class="py-8 text-center text-rose-500">Failed to load roster candidates.</td></tr>`;
        }
    }

    document.getElementById('rosterCategoryFilter').addEventListener('change', loadRoster);
    document.getElementById('rosterStatusFilter').addEventListener('change', loadRoster);
    document.getElementById('rosterSearchInput').addEventListener('input', debounce(loadRoster, 300));

    // --- TAB: LOAD AUTHORITATIVE MASTER PROMOTION & TRANSFER ORDERS (328) ---
    async function loadMasterOrders() {
        const tbody = document.getElementById('masterOrdersTableBody');
        if (!tbody) return;

        const search = document.getElementById('masterOrdersSearchInput')?.value || '';
        const basis = document.getElementById('masterOrdersBasisFilter')?.value || 'ALL';
        const district = document.getElementById('masterOrdersDistrictFilter')?.value || 'ALL';

        let url = `/api/master-orders?`;
        if (search) url += `search=${encodeURIComponent(search)}&`;
        if (basis && basis !== 'ALL') url += `transfer_basis=${encodeURIComponent(basis)}&`;
        if (district && district !== 'ALL') url += `district=${encodeURIComponent(district)}&`;

        try {
            const res = await fetch(url);
            const json = await res.json();
            const countEl = document.getElementById('masterOrdersShowingCount');
            if (countEl) countEl.innerText = `Showing ${json.count} orders`;

            const cardsEl = document.getElementById('masterOrdersMobileCards');
            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="py-12 text-center text-slate-400">No orders match current filter criteria.</td></tr>`;
                if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-slate-400 text-xs">No orders match current filter criteria.</div>`;
                return;
            }

            tbody.innerHTML = json.data.map(o => {
                const isRoster = o.roster_sl && o.roster_sl !== '-';
                const is1112 = o.transfer_basis && o.transfer_basis.includes('1112');
                const isDisplaced = o.transfer_basis && (o.transfer_basis.includes('Displacement') || o.transfer_basis.includes('Chain'));

                let basisBadge = `<span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-800 text-[10px] font-bold">Transfer</span>`;
                if (isRoster) {
                    basisBadge = `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-900 border border-emerald-300 text-[10px] font-bold">Promotion to DD</span>`;
                } else if (is1112) {
                    basisBadge = `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold">1112 TPV Intact</span>`;
                } else if (isDisplaced) {
                    basisBadge = `<span class="px-2 py-0.5 rounded-full bg-purple-100 text-purple-900 border border-purple-300 text-[10px] font-bold">Displacement</span>`;
                }

                const phoneContact = (o.mobile && o.mobile !== '—') ? `
                    <div class="flex items-center gap-1.5 mt-0.5 text-[10px]">
                        <a href="tel:${o.mobile}" class="text-blue-600 hover:text-blue-800 flex items-center gap-0.5 font-mono" title="Call">
                            <i data-lucide="phone" class="w-2.5 h-2.5"></i> ${o.mobile}
                        </a>
                        <a href="https://wa.me/91${o.mobile}" target="_blank" class="text-emerald-600 hover:text-emerald-800 flex items-center gap-0.5 font-semibold" title="WhatsApp">
                            <i data-lucide="message-circle" class="w-2.5 h-2.5"></i> WA
                        </a>
                    </div>
                ` : '';

                return `
                    <tr class="hover:bg-slate-50/80 transition ${is1112 ? 'bg-amber-50/20' : ''}">
                        <td class="py-2.5 px-3 text-center font-semibold text-slate-600">${o.sl_no}</td>
                        <td class="py-2.5 px-2 text-center font-mono font-bold ${isRoster ? 'text-wbblue-800' : 'text-slate-400'}">${o.roster_sl || '-'}</td>
                        <td class="py-2.5 px-4">
                            <div class="font-bold text-wbblue-900 hover:text-wbblue-600 hover:underline cursor-pointer" onclick="${o.hrms_id ? `openOfficerDossier('${o.hrms_id}')` : ''}" title="Click to view officer dossier">
                                ${o.officer_name}
                            </div>
                            <div class="text-[11px] font-mono text-slate-500">HRMS: ${o.hrms_id || 'N/A'}</div>
                            ${phoneContact}
                        </td>
                        <td class="py-2.5 px-5">
                            <div class="text-slate-800 font-medium">${o.present_post_full || o.present_designation || '-'}</div>
                            ${o.present_su && o.present_su !== 'Nil' ? `
                                <div class="text-[10px] text-teal-700 font-medium">Present SU: ${o.present_su}</div>
                            ` : ''}
                        </td>
                        <td class="py-2.5 px-5">
                            <div class="text-slate-900 font-bold text-xs leading-snug">${o.transferred_substantive_post || '-'}</div>
                        </td>
                        <td class="py-2.5 px-4">
                            ${o.service_utilized_at && o.service_utilized_at !== 'Nil' ? `
                                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-teal-50 border border-teal-300 text-teal-900 font-semibold text-[11px]">
                                    <i data-lucide="arrow-right-circle" class="w-3 h-3 text-teal-600 shrink-0"></i>
                                    <span>${o.service_utilized_at}</span>
                                </span>
                            ` : `<span class="text-slate-400 italic">Nil</span>`}
                        </td>
                        <td class="py-2.5 px-3">
                            ${basisBadge}
                        </td>
                        <td class="py-2.5 px-4">
                            <div class="text-slate-700 text-xs">${o.administrative_remarks || '-'}</div>
                            ${o.comments_directive ? `
                                <div class="text-[10px] text-slate-500 font-mono mt-0.5 italic">Directive: ${o.comments_directive}</div>
                            ` : ''}
                        </td>
                        <td class="py-2.5 px-3 text-right whitespace-nowrap">
                            ${o.hrms_id ? `
                                <button onclick="openOfficerDossier('${o.hrms_id}')" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-wbblue-50 text-wbblue-700 hover:bg-wbblue-100 border border-wbblue-200 transition shadow-sm" title="View Full Dossier">
                                    Dossier
                                </button>
                            ` : `<span class="text-slate-400 text-xs">-</span>`}
                        </td>
                    </tr>
                `;
            }).join('');

            // Render Mobile Cards Feed (<md Screens)
            if (cardsEl) {
                cardsEl.innerHTML = json.data.map(o => {
                    const isRoster = o.roster_sl && o.roster_sl !== '-';
                    const is1112 = o.transfer_basis && o.transfer_basis.includes('1112');
                    const isDisplaced = o.transfer_basis && (o.transfer_basis.includes('Displacement') || o.transfer_basis.includes('Chain'));

                    let basisBadge = `<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-800 text-[10px] font-bold">Transfer</span>`;
                    if (isRoster) {
                        basisBadge = `<span class="px-2 py-0.5 rounded-md bg-emerald-100 text-emerald-900 border border-emerald-300 text-[10px] font-bold">Promotion to DD</span>`;
                    } else if (is1112) {
                        basisBadge = `<span class="px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold">1112 TPV Intact</span>`;
                    } else if (isDisplaced) {
                        basisBadge = `<span class="px-2 py-0.5 rounded-md bg-purple-100 text-purple-900 border border-purple-300 text-[10px] font-bold">Displacement</span>`;
                    }

                    const initials = getMonogram(o.officer_name);

                    const phoneContact = (o.mobile && o.mobile !== '—') ? `
                        <div class="grid grid-cols-2 gap-2 pt-1">
                            <a href="tel:${o.mobile}" class="h-10 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold rounded-xl text-center text-xs flex items-center justify-center gap-1.5 transition active:scale-95 touch-target btn-touch">
                                <i data-lucide="phone" class="w-3.5 h-3.5 text-blue-600"></i> Call (${o.mobile})
                            </a>
                            <a href="https://wa.me/91${o.mobile}" target="_blank" class="h-10 px-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-center text-xs flex items-center justify-center gap-1.5 shadow-xs shadow-emerald-600/20 transition active:scale-95 touch-target btn-touch">
                                <i data-lucide="message-circle" class="w-3.5 h-3.5"></i> WhatsApp
                            </a>
                        </div>
                    ` : '';

                    return `
                        <div class="rounded-2xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.04)] p-4 space-y-3.5 mobile-card-interactive ${is1112 ? 'border-l-4 border-amber-400 pl-3.5' : ''}">
                            <!-- Header: Monogram Avatar & Order Metadata -->
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-center gap-2.5 min-w-0">
                                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-wbblue-700 to-indigo-800 text-white font-bold flex items-center justify-center text-xs shadow-xs shrink-0 tracking-tight">
                                        ${initials}
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex flex-wrap items-center gap-1">
                                            <span class="px-1.5 py-0.5 rounded-md bg-emerald-900 text-white font-mono text-[9px] font-bold">Order #${o.sl_no}</span>
                                            ${isRoster ? `<span class="px-1.5 py-0.5 rounded-md bg-wbblue-100 text-wbblue-900 font-mono text-[9px] font-bold">Roster Pt ${o.roster_sl}</span>` : ''}
                                            ${basisBadge}
                                        </div>
                                        <div class="font-extrabold text-sm text-slate-900 truncate cursor-pointer hover:text-wbblue-700 pt-0.5" onclick="${o.hrms_id ? `openOfficerDossier('${o.hrms_id}')` : ''}" title="Click to view dossier">
                                            ${o.officer_name}
                                        </div>
                                        <div class="text-[11px] font-mono text-slate-500 mt-0.5">
                                            HRMS: <strong>${o.hrms_id || 'N/A'}</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Timeline Flow: Pre-transfer Station -> Transferred Post -->
                            <div class="space-y-1.5">
                                <!-- Origin -->
                                <div class="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                                        <i data-lucide="map-pin" class="w-3 h-3 text-slate-400"></i>
                                        <span>Pre-Transfer / Present Post</span>
                                    </div>
                                    <div class="font-semibold text-slate-800 leading-snug mt-0.5">${o.present_post_full || o.present_designation || '-'}</div>
                                    ${o.present_su && o.present_su !== 'Nil' ? `
                                        <div class="text-[11px] text-teal-700 font-medium mt-0.5">Present SU: ${o.present_su}</div>
                                    ` : ''}
                                </div>

                                <!-- Flow indicator -->
                                <div class="flex items-center justify-center -my-0.5 text-slate-300">
                                    <i data-lucide="arrow-down" class="w-3 h-3 text-wbblue-500"></i>
                                </div>

                                <!-- Destination / Authoritative Transferred Post -->
                                <div class="p-3 rounded-xl bg-gradient-to-r from-emerald-50/80 via-teal-50/40 to-blue-50/60 border border-emerald-200/80 text-xs space-y-1.5">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1">
                                        <i data-lucide="check-circle-2" class="w-3 h-3 text-emerald-600"></i>
                                        <span>Transferred Post (Authoritative)</span>
                                    </div>
                                    <div class="text-slate-900 font-bold text-xs leading-snug flex items-start gap-1.5">
                                        <span class="px-1.5 py-0.2 rounded bg-emerald-600 text-white text-[9px] font-bold uppercase shrink-0 mt-0.5">Substantive</span>
                                        <span>${o.transferred_substantive_post || '-'}</span>
                                    </div>
                                    ${o.service_utilized_at && o.service_utilized_at !== 'Nil' ? `
                                        <div class="text-teal-900 font-semibold text-[11px] leading-snug flex items-start gap-1.5">
                                            <span class="px-1.5 py-0.2 rounded bg-teal-600 text-white text-[9px] font-bold uppercase shrink-0 mt-0.5">SU</span>
                                            <span>${o.service_utilized_at}</span>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>

                            ${o.administrative_remarks && o.administrative_remarks !== '-' ? `
                                <div class="p-2.5 rounded-xl bg-amber-50/70 border-l-4 border-amber-500 text-xs text-amber-950 font-medium space-y-0.5">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-amber-800 flex items-center gap-1">
                                        <i data-lucide="shield-check" class="w-3 h-3 text-amber-600"></i>
                                        <span>Administrative Directive</span>
                                    </div>
                                    <div class="text-slate-800">${o.administrative_remarks}</div>
                                </div>
                            ` : ''}

                            <!-- Ergonomic Contact Buttons -->
                            ${phoneContact}

                            <!-- Actions -->
                            <div class="pt-0.5">
                                ${o.hrms_id ? `
                                    <button onclick="openOfficerDossier('${o.hrms_id}')" class="w-full h-10 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 flex items-center justify-center gap-1.5 transition active:scale-95 touch-target btn-touch">
                                        <i data-lucide="user" class="w-4 h-4 text-slate-600"></i>
                                        <span>View Complete Personnel Dossier</span>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }).join('');
            }

            lucide.createIcons();
        } catch (e) {
            console.error('Error loading master orders:', e);
            tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-rose-500">Failed to load master orders: ${e.message}</td></tr>`;
        }
    }

    const moSearch = document.getElementById('masterOrdersSearchInput');
    const moBasis = document.getElementById('masterOrdersBasisFilter');
    const moDist = document.getElementById('masterOrdersDistrictFilter');
    if (moSearch) moSearch.addEventListener('input', debounce(loadMasterOrders, 300));
    if (moBasis) moBasis.addEventListener('change', loadMasterOrders);
    if (moDist) moDist.addEventListener('change', loadMasterOrders);

    // --- TAB 2: LOAD OBLITERATED POSTS ---
    async function loadObliterated() {
        const tbody = document.getElementById('oblitTableBody');
        const status = document.getElementById('oblitStatusFilter').value;
        const search = document.getElementById('oblitSearchInput').value;

        let url = `/api/obliterated?status=${encodeURIComponent(status)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        try {
            const res = await fetch(url);
            const json = await res.json();
            state.obliteratedOfficers = json.data;

            const cardsEl = document.getElementById('oblitMobileCards');
            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-slate-400">No obliterated post records found.</td></tr>`;
                if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-slate-400 text-xs">No obliterated post records found.</div>`;
                return;
            }

            tbody.innerHTML = json.data.map(o => {
                const isRehab = o.rehabilitation_status === 'Rehabilitated';
                const isVacant = o.is_vacant === 'Yes';
                const statusBadge = isVacant
                    ? `<span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-bold">Clear Abolished Vacancy</span>`
                    : isRehab
                    ? `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">Rehabilitated</span>`
                    : `<span class="px-2 py-0.5 rounded-full bg-rose-100 text-rose-800 text-[10px] font-bold">Pending Rehab</span>`;

                const trackDisplay = o.is_on_roster === 1
                    ? `<div class="font-bold text-amber-700 text-[11px] flex items-center gap-1">
                         <i data-lucide="award" class="w-3.5 h-3.5"></i>
                         <span>50-Pt Roster Promotion to DD (Rank ${o.roster_rank})</span>
                       </div>`
                    : isVacant
                    ? `<span class="text-slate-400 italic">No incumbent to rehabilitate</span>`
                    : `<div class="font-semibold text-blue-700 text-[11px]">Lateral Cadre Absorption into Active AD Post</div>`;

                let rehabDisplay = `<span class="text-rose-600 font-medium text-[11px]">Awaiting Active Cadre Post</span>`;
                if (isVacant) {
                    rehabDisplay = `<span class="text-slate-400 text-[11px]">Abolished Post (No Action Needed)</span>`;
                } else if (isRehab) {
                    rehabDisplay = `
                        <div class="space-y-0.5">
                            <div class="text-emerald-800 font-bold text-[11px]">Main: ${o.substantive_post_name || 'Cadre Post'}</div>
                            ${o.su_post_name ? `<div class="text-teal-700 font-semibold text-[10px]">SU: ${o.su_post_name}</div>` : ''}
                        </div>
                    `;
                }

                return `
                    <tr class="hover:bg-slate-50 transition ${isRehab ? 'bg-emerald-50/20' : ''}">
                        <td class="py-2.5 px-3 font-mono font-semibold text-slate-500">${o.oblit_sl}</td>
                        <td class="py-2.5 px-4">
                            <div class="font-bold text-slate-800">${o.post_name}</div>
                            <div class="text-[11px] text-slate-500">${o.establishment}</div>
                        </td>
                        <td class="py-2.5 px-3">
                            <div class="font-medium text-slate-800">${o.district}</div>
                            <div class="text-[11px] text-slate-500">${o.block || 'District HQ'}</div>
                        </td>
                        <td class="py-2.5 px-4 font-bold ${isVacant ? 'text-slate-400 italic' : 'text-slate-900'}">
                            ${isVacant ? o.officer_name : `
                                <span class="text-wbblue-900 hover:text-wbblue-600 hover:underline cursor-pointer" onclick="openOfficerDossier('${o.hrms_id}')" title="Click to view officer personnel dossier">
                                    ${o.officer_name}
                                </span>
                            `}
                        </td>
                        <td class="py-2.5 px-3 font-mono text-slate-600">${o.hrms_id || '-'}</td>
                        <td class="py-2.5 px-3 text-slate-600 text-[11px]">${o.tenure || '-'}</td>
                        <td class="py-2.5 px-4">${trackDisplay}</td>
                        <td class="py-2.5 px-4">${rehabDisplay}</td>
                        <td class="py-2.5 px-3 text-right whitespace-nowrap">
                            ${isVacant ? '-' : `
                                <div class="flex items-center justify-end gap-1.5">
                                    <button onclick="openDualAllotModal('${o.hrms_id}', 'obliterated')" class="px-2 py-1 text-xs font-semibold rounded bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 transition">
                                        ${isRehab ? 'Modify' : 'Rehab'}
                                    </button>
                                    <button onclick="openAIAllotModal('${o.hrms_id}', 'obliterated')" class="px-2 py-1 text-xs font-bold rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-sm transition flex items-center gap-1" title="Quick Statutory Rehabilitation">
                                        <i data-lucide="zap" class="w-3 h-3"></i>
                                        <span>Quick</span>
                                    </button>
                                </div>
                            `}
                        </td>
                    </tr>
                `;
            }).join('');

            // Render Mobile Cards Feed (<md Screens)
            if (cardsEl) {
                cardsEl.innerHTML = json.data.map(o => {
                    const isRehab = o.rehabilitation_status === 'Rehabilitated';
                    const isVacant = o.is_vacant === 'Yes';
                    const statusBadge = isVacant
                        ? `<span class="px-2.5 py-1 rounded-full bg-slate-100 text-slate-600 text-[10px] font-bold border border-slate-200">Abolished Vacancy</span>`
                        : isRehab
                        ? `<span class="px-2.5 py-1 rounded-full bg-emerald-100/90 text-emerald-800 text-[10px] font-bold inline-flex items-center gap-1 border border-emerald-300/60 shadow-2xs"><i data-lucide="check-circle" class="w-3 h-3 text-emerald-600"></i> Rehabilitated</span>`
                        : `<span class="px-2.5 py-1 rounded-full bg-rose-100/90 text-rose-800 text-[10px] font-bold inline-flex items-center gap-1 border border-rose-300/60 shadow-2xs"><i data-lucide="alert-circle" class="w-3 h-3 text-rose-600"></i> Pending Rehab</span>`;

                    const trackDisplay = o.is_on_roster === 1
                        ? `<div class="font-bold text-amber-800 text-xs flex items-center gap-1">
                             <i data-lucide="award" class="w-3.5 h-3.5 text-amber-600"></i>
                             <span>50-Pt Roster Promotion (Rank ${o.roster_rank})</span>
                           </div>`
                        : isVacant
                        ? `<span class="text-slate-400 italic text-xs">No incumbent to rehabilitate</span>`
                        : `<div class="font-semibold text-blue-800 text-xs">Lateral Absorption into Active AD Post</div>`;

                    const initials = getMonogram(o.officer_name);

                    return `
                        <div class="rounded-2xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.04)] p-4 space-y-3.5 mobile-card-interactive">
                            <!-- Header: Post & Abolition Badge -->
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-center gap-2.5 min-w-0">
                                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-rose-700 to-amber-700 text-white font-bold flex items-center justify-center text-xs shadow-xs shrink-0 tracking-tight">
                                        ${initials}
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-1.5">
                                            <span class="px-1.5 py-0.5 rounded-md bg-rose-900 text-white font-mono text-[9px] font-bold">Oblit #${o.oblit_sl}</span>
                                            <span class="text-[11px] font-medium text-slate-500">${o.district} • ${o.block || 'HQ'}</span>
                                        </div>
                                        <div class="font-extrabold text-sm text-slate-900 pt-0.5 leading-snug">
                                            ${o.post_name}
                                        </div>
                                        <div class="text-[11px] text-slate-500">${o.establishment}</div>
                                    </div>
                                </div>
                                <div class="shrink-0">${statusBadge}</div>
                            </div>

                            <!-- Incumbent Details -->
                            <div class="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs space-y-1">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                                    <i data-lucide="user" class="w-3 h-3 text-slate-400"></i>
                                    <span>Serving Incumbent</span>
                                </div>
                                ${isVacant ? `<div class="text-slate-500 italic">Clear Abolished Vacancy (Vacant Post)</div>` : `
                                    <div class="font-bold text-slate-900 text-xs cursor-pointer hover:underline" onclick="openOfficerDossier('${o.hrms_id}')">
                                        ${o.officer_name}
                                    </div>
                                    <div class="text-[11px] font-mono text-slate-500 flex items-center gap-2">
                                        <span>HRMS: <strong>${o.hrms_id || '-'}</strong></span>
                                        <span>•</span>
                                        <span>Tenure: ${o.tenure || '-'}</span>
                                    </div>
                                `}
                            </div>

                            <!-- Rehabilitation Strategy & Allocation -->
                            <div class="p-3 rounded-xl bg-gradient-to-r from-rose-50/60 via-amber-50/40 to-emerald-50/50 border border-rose-200/80 text-xs space-y-1.5">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-rose-900 flex items-center gap-1">
                                    <i data-lucide="shield-alert" class="w-3 h-3 text-rose-600"></i>
                                    <span>Rehabilitation Strategy & Allocation</span>
                                </div>
                                <div class="pt-0.5">${trackDisplay}</div>
                                ${isRehab ? `
                                    <div class="pt-1 text-slate-900 font-bold text-xs leading-snug flex items-start gap-1.5">
                                        <span class="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-900 border border-emerald-300 text-[9px] font-bold uppercase shrink-0 mt-0.5">Substantive</span>
                                        <span>${o.substantive_post_name || 'Cadre Post'}</span>
                                    </div>
                                    ${o.su_post_name ? `
                                        <div class="text-teal-900 font-semibold text-[11px] leading-snug flex items-start gap-1.5">
                                            <span class="px-1.5 py-0.2 rounded bg-teal-100 text-teal-900 border border-teal-300 text-[9px] font-bold uppercase shrink-0 mt-0.5">SU</span>
                                            <span>${o.su_post_name}</span>
                                        </div>
                                    ` : ''}
                                ` : ''}
                            </div>

                            <!-- Actions -->
                            ${!isVacant ? `
                                <div class="grid grid-cols-3 gap-2 pt-0.5">
                                    <button onclick="openOfficerDossier('${o.hrms_id}')" class="h-10 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 flex items-center justify-center gap-1 transition active:scale-95 touch-target btn-touch">
                                        <i data-lucide="user" class="w-3.5 h-3.5"></i> Dossier
                                    </button>
                                    <button onclick="openDualAllotModal('${o.hrms_id}', 'obliterated')" class="h-10 text-xs font-bold rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-200 flex items-center justify-center gap-1 transition active:scale-95 touch-target btn-touch">
                                        <i data-lucide="edit-3" class="w-3.5 h-3.5"></i> ${isRehab ? 'Modify' : 'Rehab'}
                                    </button>
                                    <button onclick="openAIAllotModal('${o.hrms_id}', 'obliterated')" class="h-10 text-xs font-bold rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 text-white flex items-center justify-center gap-1 shadow-xs transition active:scale-95 touch-target btn-touch" title="Quick Statutory Rehabilitation">
                                        <i data-lucide="zap" class="w-3.5 h-3.5"></i> Quick Allot
                                    </button>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }).join('');
            }

            lucide.createIcons();
        } catch (e) {
            console.error('Error loading obliterated officers:', e);
            tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-rose-500">Failed to load obliterated records.</td></tr>`;
        }
    }

    document.getElementById('oblitStatusFilter').addEventListener('change', loadObliterated);
    document.getElementById('oblitSearchInput').addEventListener('input', debounce(loadObliterated, 300));

    // --- TAB 3: LOAD CADRE POSTS (1,794) ---
    async function loadCadre() {
        const tbody = document.getElementById('cadreTableBody');
        const search = document.getElementById('cadreSearchInput').value;
        const district = document.getElementById('cadreDistrictFilter').value;
        const designation = document.getElementById('cadreDesigFilter').value;
        const status = document.getElementById('cadreStatusFilter').value;
        const tenureOver = document.getElementById('cadreTenureFilter').value;
        const avd = document.getElementById('cadreAVDFilter').value;

        let url = `/api/cadre?limit=${state.cadreLimit}&offset=${state.cadreOffset}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (district && district !== 'ALL') url += `&district=${encodeURIComponent(district)}`;
        if (designation && designation !== 'ALL') url += `&designation=${encodeURIComponent(designation)}`;
        if (status && status !== 'ALL') url += `&status=${encodeURIComponent(status)}`;
        if (tenureOver && tenureOver !== 'ALL') url += `&tenure_over=${encodeURIComponent(tenureOver)}`;
        if (avd && avd !== 'ALL') url += `&avd_member=${encodeURIComponent(avd)}`;

        try {
            const res = await fetch(url);
            const json = await res.json();
            state.cadreData = json.data;
            state.cadreTotal = json.total;

            document.getElementById('cadrePaginationInfo').innerText = 
                `Showing ${state.cadreOffset + 1} to ${Math.min(state.cadreOffset + json.data.length, json.total)} of ${json.total} posts`;

            document.getElementById('btnCadrePrev').disabled = state.cadreOffset === 0;
            document.getElementById('btnCadreNext').disabled = state.cadreOffset + state.cadreLimit >= json.total;

            const cardsEl = document.getElementById('cadreMobileCards');
            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-slate-400">No cadre posts found matching filters.</td></tr>`;
                if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-slate-400 text-xs">No cadre posts found matching filters.</div>`;
                return;
            }

            tbody.innerHTML = json.data.map(p => {
                const isVacant = p.occupancy_status === 'Vacant';
                const isTenureOver = p.tenure_over_flag === 'Yes';
                const isAVD = p.avd_member === 'Yes';

                let occBadge = isVacant
                    ? `<span class="badge-vacant px-2 py-0.5 rounded text-[10px] font-bold">Clear Vacancy</span>`
                    : `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">Occupied</span>`;

                let tenureBadge = isTenureOver
                    ? `<span class="badge-tenure-over px-1.5 py-0.5 rounded text-[10px] font-bold ml-1">Over-Tenure</span>`
                    : '';

                let avdBadge = isAVD
                    ? `<span class="badge-avd px-1.5 py-0.5 rounded text-[10px] font-bold ml-1">AVD</span>`
                    : '';

                return `
                    <tr class="hover:bg-slate-50 transition">
                        <td class="py-2.5 px-3 font-mono font-bold text-slate-500">${p.id}</td>
                        <td class="py-2.5 px-4">
                            <div class="font-bold text-slate-900">${p.designation}</div>
                            <div class="text-[11px] text-slate-500">${p.establishment}</div>
                        </td>
                        <td class="py-2.5 px-3 font-medium text-slate-700">${p.block || 'HQ'}</td>
                        <td class="py-2.5 px-3 font-medium text-slate-700">${p.district || '-'}</td>
                        <td class="py-2.5 px-3">${occBadge}</td>
                        <td class="py-2.5 px-4">
                            ${isVacant ? '<span class="text-emerald-700 font-semibold italic text-xs">Clear Vacancy</span>' : `
                                <div class="font-bold text-wbblue-900 hover:text-wbblue-600 hover:underline cursor-pointer" onclick="openOfficerDossier('${p.incumbent_hrms}')" title="Click to view officer personnel dossier">${p.incumbent_name} ${avdBadge}</div>
                                <div class="text-[11px] font-mono text-slate-500">HRMS: ${p.incumbent_hrms || 'N/A'}</div>
                            `}
                        </td>
                        <td class="py-2.5 px-3 text-slate-700">${p.incumbent_tenure || '-'} ${tenureBadge}</td>
                        <td class="py-2.5 px-3 font-mono text-xs text-slate-600">${p.incumbent_dor || '-'}</td>
                        <td class="py-2.5 px-3 text-right whitespace-nowrap">
                            ${!isVacant ? (
                                (p.incumbent_hrms === '1992005664' || p.id === 1 || p.pay_level === 'Level-22' || p.pay_level === 'Level-21' || (p.designation && p.designation.toLowerCase().includes('director of ah'))) ? `
                                    <span class="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold rounded bg-slate-100 text-slate-500 border border-slate-300 shadow-sm" title="Apex Cadre Post: Protected from transfer / displacement">
                                        <i data-lucide="lock" class="w-3 h-3 text-slate-400"></i>
                                        <span>Apex Post</span>
                                    </span>
                                ` : `
                                <div class="flex items-center justify-end gap-1.5">
                                    <button onclick="openDualAllotModal('${p.incumbent_hrms}', 'displaced')" class="px-2 py-1 text-[11px] font-medium rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
                                        Allot
                                    </button>
                                    <button onclick="openAIAllotModal('${p.incumbent_hrms}', 'displaced')" class="px-2 py-1 text-xs font-bold rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-sm transition flex items-center gap-1" title="Quick Placement">
                                        <i data-lucide="zap" class="w-3 h-3"></i>
                                        <span>Quick</span>
                                    </button>
                                </div>
                                `
                            ) : '-'}
                        </td>
                    </tr>
                `;
            }).join('');

            // Render Mobile Cards Feed (<md Screens)
            if (cardsEl) {
                cardsEl.innerHTML = json.data.map(p => {
                    const isVacant = p.occupancy_status === 'Vacant';
                    const isTenureOver = p.tenure_over_flag === 'Yes';
                    const isAVD = p.avd_member === 'Yes';

                    let occBadge = isVacant
                        ? `<span class="badge-vacant px-2.5 py-1 rounded-full text-[10px] font-bold">Clear Vacancy</span>`
                        : `<span class="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700">Occupied</span>`;

                    let tenureBadge = isTenureOver
                        ? `<span class="badge-tenure-over px-1.5 py-0.5 rounded-md text-[10px] font-bold ml-1">Over-Tenure</span>`
                        : '';

                    let avdBadge = isAVD
                        ? `<span class="badge-avd px-1.5 py-0.5 rounded-md text-[10px] font-bold ml-1">AVD</span>`
                        : '';

                    const isApexLocked = !isVacant && (p.incumbent_hrms === '1992005664' || p.id === 1 || p.pay_level === 'Level-22' || p.pay_level === 'Level-21' || (p.designation && p.designation.toLowerCase().includes('director of ah')));
                    const initials = isVacant ? 'VAC' : getMonogram(p.incumbent_name);

                    return `
                        <div class="rounded-2xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.04)] p-4 space-y-3.5 mobile-card-interactive ${isVacant ? 'border-l-4 border-emerald-400 pl-3.5' : ''}">
                            <!-- Header: Designation & Post Info -->
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-center gap-2.5 min-w-0">
                                    <div class="w-10 h-10 rounded-full ${isVacant ? 'bg-emerald-100 text-emerald-800' : 'bg-gradient-to-br from-wbblue-700 to-indigo-800 text-white'} font-bold flex items-center justify-center text-xs shadow-xs shrink-0 tracking-tight">
                                        ${isVacant ? '<i data-lucide="check" class="w-4 h-4"></i>' : initials}
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex items-center gap-1.5">
                                            <span class="px-1.5 py-0.5 rounded-md bg-slate-800 text-white font-mono text-[9px] font-bold">Post #${p.id}</span>
                                            <span class="text-[11px] font-medium text-slate-500">${p.district || '-'} • ${p.block || 'HQ'}</span>
                                        </div>
                                        <div class="font-extrabold text-sm text-slate-900 pt-0.5 leading-snug">
                                            ${p.designation}
                                        </div>
                                        <div class="text-[11px] text-slate-500">${p.establishment}</div>
                                    </div>
                                </div>
                                <div class="shrink-0">${occBadge}</div>
                            </div>

                            <!-- Incumbent or Vacancy Box -->
                            <div class="p-2.5 rounded-xl ${isVacant ? 'bg-emerald-50/80 border border-emerald-200' : 'bg-slate-50/90 border border-slate-200/80'} text-xs space-y-1">
                                <div class="text-[10px] font-bold uppercase tracking-wider ${isVacant ? 'text-emerald-800' : 'text-slate-400'} flex items-center gap-1">
                                    <i data-lucide="${isVacant ? 'check-circle' : 'user'}" class="w-3 h-3 ${isVacant ? 'text-emerald-600' : 'text-slate-400'}"></i>
                                    <span>${isVacant ? 'Vacancy Information' : 'Serving Incumbent'}</span>
                                </div>
                                ${isVacant ? `
                                    <div class="text-emerald-900 font-bold text-xs flex items-center gap-1.5">
                                        <span>Available for Substantive / SU Cadre Absorption</span>
                                    </div>
                                ` : `
                                    <div class="font-bold text-wbblue-900 text-xs cursor-pointer hover:underline" onclick="openOfficerDossier('${p.incumbent_hrms}')">
                                        ${p.incumbent_name} ${avdBadge}
                                    </div>
                                    <div class="text-[11px] font-mono text-slate-500 flex flex-wrap items-center gap-2">
                                        <span>HRMS: <strong>${p.incumbent_hrms || 'N/A'}</strong></span>
                                        <span>•</span>
                                        <span>Tenure: ${p.incumbent_tenure || '-'} ${tenureBadge}</span>
                                        <span>•</span>
                                        <span>DOR: ${p.incumbent_dor || '-'}</span>
                                    </div>
                                `}
                            </div>

                            <!-- Action Buttons -->
                            <div class="pt-0.5">
                                ${isApexLocked ? `
                                    <div class="h-10 px-3 rounded-xl bg-slate-100 text-slate-500 border border-slate-300 font-bold text-xs flex items-center justify-center gap-1.5 shadow-xs">
                                        <i data-lucide="lock" class="w-4 h-4 text-slate-400"></i>
                                        <span>Apex Cadre Post (Statutorily Protected)</span>
                                    </div>
                                ` : (!isVacant ? `
                                    <div class="grid grid-cols-3 gap-2">
                                        <button onclick="openOfficerDossier('${p.incumbent_hrms}')" class="h-10 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 flex items-center justify-center gap-1 transition active:scale-95 touch-target btn-touch">
                                            <i data-lucide="user" class="w-3.5 h-3.5"></i> Dossier
                                        </button>
                                        <button onclick="openDualAllotModal('${p.incumbent_hrms}', 'displaced')" class="h-10 text-xs font-bold rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 flex items-center justify-center gap-1 transition active:scale-95 touch-target btn-touch">
                                            <i data-lucide="edit-3" class="w-3.5 h-3.5"></i> Allot
                                        </button>
                                        <button onclick="openAIAllotModal('${p.incumbent_hrms}', 'displaced')" class="h-10 text-xs font-bold rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 text-white flex items-center justify-center gap-1 shadow-xs transition active:scale-95 touch-target btn-touch" title="Quick Statutory Placement">
                                            <i data-lucide="zap" class="w-3.5 h-3.5"></i> Quick Allot
                                        </button>
                                    </div>
                                ` : `
                                    <div class="text-[11px] text-slate-400 italic text-center py-1">
                                        Clear vacancy selectable in 50-Point Roster and Lateral Absorption tools
                                    </div>
                                `)}
                            </div>
                        </div>
                    `;
                }).join('');
            }

            if (window.lucide) window.lucide.createIcons();
        } catch (e) {
            console.error('Error loading cadre:', e);
            tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-rose-500">Failed to load cadre posts.</td></tr>`;
        }
    }

    document.getElementById('btnCadrePrev').addEventListener('click', () => {
        if (state.cadreOffset > 0) {
            state.cadreOffset = Math.max(0, state.cadreOffset - state.cadreLimit);
            loadCadre();
        }
    });

    document.getElementById('btnCadreNext').addEventListener('click', () => {
        if (state.cadreOffset + state.cadreLimit < state.cadreTotal) {
            state.cadreOffset += state.cadreLimit;
            loadCadre();
        }
    });

    ['cadreDistrictFilter', 'cadreDesigFilter', 'cadreStatusFilter', 'cadreTenureFilter', 'cadreAVDFilter'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
            state.cadreOffset = 0;
            loadCadre();
        });
    });
    document.getElementById('cadreSearchInput').addEventListener('input', debounce(() => {
        state.cadreOffset = 0;
        loadCadre();
    }, 300));

    // --- TAB 5: LOAD OFFICIAL ORDERS ---
    async function loadOrders() {
        const tbody = document.getElementById('ordersTableBody');
        const cardsEl = document.getElementById('ordersMobileCards');
        const cat = document.getElementById('ordersCategoryFilter').value;
        const search = document.getElementById('ordersSearchInput').value;

        let url = `/api/orders?category=${encodeURIComponent(cat)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        try {
            const res = await fetch(url);
            const json = await res.json();
            state.orders = json.data;

            if (json.data.length === 0) {
                if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-400">No official orders found.</td></tr>`;
                if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-slate-400 text-xs">No official orders found.</div>`;
                return;
            }

            if (tbody) {
                tbody.innerHTML = json.data.map(o => {
                    return `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="py-2.5 px-3 font-mono text-xs text-slate-600">${o.order_date || '-'}</td>
                            <td class="py-2.5 px-3 font-mono font-bold text-wbblue-900">${o.order_number || '-'}</td>
                            <td class="py-2.5 px-2">
                                <span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-100 text-slate-800">
                                    ${o.category}
                                </span>
                            </td>
                            <td class="py-2.5 px-5">
                                <div class="font-bold text-slate-800 text-xs">${o.title}</div>
                                <div class="text-[11px] text-slate-500">${o.subdirectory || ''}</div>
                            </td>
                            <td class="py-2.5 px-4 text-xs text-slate-700">${o.key_officers || 'Cadre Wide'}</td>
                            <td class="py-2.5 px-3 text-right">
                                ${o.web_source_portal ? `<a href="${o.web_source_portal}" target="_blank" class="text-xs font-semibold text-wbblue-600 hover:underline">Portal Link</a>` : '-'}
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            if (cardsEl) {
                cardsEl.innerHTML = json.data.map(o => {
                    return `
                        <div class="rounded-2xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.04)] mobile-card-interactive p-4 space-y-3">
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-start gap-3 min-w-0">
                                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-wbblue-700 to-indigo-800 text-white flex items-center justify-center shrink-0 shadow-xs">
                                        <i data-lucide="file-text" class="w-5 h-5"></i>
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex flex-wrap items-center gap-1.5 mb-1">
                                            <span class="px-2 py-0.5 rounded-md bg-slate-900 text-white font-mono text-[9px] font-bold">${o.order_date || 'Date N/A'}</span>
                                            <span class="px-2 py-0.5 text-[9px] font-bold rounded-md bg-wbblue-50 text-wbblue-900 border border-wbblue-200">${o.category}</span>
                                        </div>
                                        <div class="font-extrabold text-sm text-slate-900 leading-snug break-words">${o.title}</div>
                                        <div class="font-mono text-xs text-wbblue-800 font-bold mt-0.5">${o.order_number || '—'}</div>
                                    </div>
                                </div>
                            </div>

                            ${o.subdirectory ? `
                                <div class="text-[11px] text-slate-500 font-medium px-1">
                                    <span class="text-slate-400">Wing / Directorate:</span> ${o.subdirectory}
                                </div>
                            ` : ''}

                            ${o.key_officers ? `
                                <div class="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs space-y-1">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                                        <i data-lucide="users" class="w-3 h-3 text-slate-400"></i>
                                        <span>Key Officers / Beneficiaries</span>
                                    </div>
                                    <div class="text-xs text-slate-700 font-medium leading-relaxed">${o.key_officers}</div>
                                </div>
                            ` : ''}

                            ${o.web_source_portal ? `
                                <div class="pt-1 border-t border-slate-100">
                                    <a href="${o.web_source_portal}" target="_blank" class="w-full py-2.5 px-3 rounded-xl bg-wbblue-50 hover:bg-wbblue-100 text-wbblue-800 border border-wbblue-200 text-xs font-bold flex items-center justify-center gap-1.5 btn-touch touch-target">
                                        <i data-lucide="external-link" class="w-3.5 h-3.5 text-wbblue-600"></i>
                                        <span>View Official Gazette Order</span>
                                    </a>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }).join('');
            }

            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Error loading orders:', e);
            if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-rose-500">Failed to load orders.</td></tr>`;
            if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-rose-500 text-xs">Failed to load orders.</div>`;
        }
    }

    document.getElementById('ordersCategoryFilter').addEventListener('change', loadOrders);
    document.getElementById('ordersSearchInput').addEventListener('input', debounce(loadOrders, 300));

    // --- TAB 4: SIMULATION AUDIT TRAIL ---
    async function loadSimulationHistory() {
        const auditContainer = document.getElementById('simAuditList');
        try {
            const res = await fetch('/api/simulation/history');
            const json = await res.json();
            document.getElementById('simAuditCount').innerText = `${json.count} moves`;
            document.getElementById('badgeSimCount').innerText = json.count;

            if (json.data.length === 0) {
                auditContainer.innerHTML = `
                    <div class="text-center py-12 text-slate-400 text-xs">
                        No assignments executed in this simulation yet. Click "Run AI Auto-Solver" or make manual assignments.
                    </div>
                `;
                return;
            }

            auditContainer.innerHTML = json.data.map((a, i) => {
                const isCollision = a.collision_displaced_officer !== null;
                return `
                    <div class="p-3 rounded-lg border ${isCollision ? 'border-amber-300 bg-amber-50/50' : 'border-slate-200 bg-slate-50'} text-xs space-y-1.5 transition">
                        <div class="flex items-center justify-between">
                            <div class="font-bold text-slate-900 flex items-center gap-1.5">
                                <span class="text-slate-400">#${json.data.length - i}</span>
                                <span>${a.officer_name}</span>
                                <span class="text-[10px] font-mono text-slate-500">(${a.officer_hrms_id})</span>
                            </div>
                            <span class="text-[10px] text-slate-400 font-mono">${a.timestamp ? a.timestamp.split('T')[1].slice(0, 8) : ''}</span>
                        </div>
                        <div class="text-slate-700 leading-relaxed text-[11px]">
                            <div class="text-slate-500">From: <span class="italic">${a.from_post_name || 'Present Station'}</span></div>
                            <div class="font-semibold text-emerald-800">Substantive Main: ${a.substantive_post_name || a.to_post_name}</div>
                            ${a.su_post_name ? `<div class="font-semibold text-teal-700">SU Attached: ${a.su_post_name}</div>` : ''}
                        </div>
                        ${isCollision ? `
                            <div class="p-2 rounded bg-amber-100 text-amber-900 text-[11px] font-medium border border-amber-300">
                                ⚠️ Displaced Incumbent: <strong>${a.collision_displaced_officer}</strong> (${a.collision_displaced_hrms}) awaiting rehabilitation!
                            </div>
                        ` : ''}
                    </div>
                `;
            }).join('');
        } catch (e) {
            console.error('Error loading simulation history:', e);
        }
    }

    // --- GROUP C CASCADING REPLACEMENT WARNINGS ---
    let cascadingBackfillsData = [];
    async function loadCascadingBackfills() {
        const tbody = document.getElementById('cascadingBackfillTableBody');
        const badge = document.getElementById('badgeCascadingCount');
        const searchInput = document.getElementById('cascadingSearchInput');
        if (!tbody) return;

        try {
            const res = await fetch('/api/posts/cascading-backfills');
            cascadingBackfillsData = await res.json();
            if (badge) {
                badge.innerText = `${cascadingBackfillsData.length} Vacated Posts`;
            }

            function renderRows(items) {
                if (!items || items.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="6" class="py-8 text-center text-slate-400 text-xs">
                                No cascading vacancies matching your filter.
                            </td>
                        </tr>
                    `;
                    return;
                }

                tbody.innerHTML = items.map((item, idx) => `
                    <tr class="hover:bg-rose-50/60 transition duration-150 border-b border-rose-100">
                        <td class="py-2.5 px-3 font-mono text-slate-500 font-semibold">${idx + 1}</td>
                        <td class="py-2.5 px-3">
                            <div class="font-bold text-slate-900 flex items-center gap-1.5 cursor-pointer hover:text-wbblue-700" onclick="window.showOfficerProfileModal('${item.hrms_id}')">
                                <span>${item.officer_name}</span>
                                <span class="text-[10px] font-normal text-slate-500 font-mono">(${item.hrms_id})</span>
                            </div>
                            <div class="text-[11px] text-slate-500">Roster Pt: ${item.roster_point || item.sl_no}</div>
                        </td>
                        <td class="py-2.5 px-3">
                            <div class="font-bold text-rose-700 flex items-center gap-1">
                                <span class="w-2 h-2 rounded-full bg-rose-600 animate-pulse"></span>
                                <span>${item.present_posting}</span>
                            </div>
                            <div class="text-[11px] text-rose-600 font-medium">⚠️ Relieved without substitute</div>
                        </td>
                        <td class="py-2.5 px-3">
                            <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                                ${item.present_district || 'District HQ'}
                            </span>
                        </td>
                        <td class="py-2.5 px-3 text-slate-800 text-[11px]">
                            <div class="font-semibold text-emerald-800">${item.substantive_post_name || 'Substantive DD Post'}</div>
                            ${item.su_post_name ? `<div class="text-teal-700 font-medium">SU: ${item.su_post_name}</div>` : ''}
                        </td>
                        <td class="py-2.5 px-3 text-center">
                            <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300 shadow-sm">
                                🚨 IMMEDIATE BACKFILL
                            </span>
                        </td>
                    </tr>
                `).join('');
                if (window.lucide) {
                    lucide.createIcons();
                }
            }

            renderRows(cascadingBackfillsData);

            if (searchInput && !searchInput.dataset.initialized) {
                searchInput.dataset.initialized = 'true';
                searchInput.addEventListener('input', (e) => {
                    const q = e.target.value.toLowerCase().trim();
                    if (!q) {
                        renderRows(cascadingBackfillsData);
                        return;
                    }
                    const filtered = cascadingBackfillsData.filter(item =>
                        (item.officer_name && item.officer_name.toLowerCase().includes(q)) ||
                        (item.hrms_id && item.hrms_id.toLowerCase().includes(q)) ||
                        (item.present_posting && item.present_posting.toLowerCase().includes(q)) ||
                        (item.present_district && item.present_district.toLowerCase().includes(q)) ||
                        (item.substantive_post_name && item.substantive_post_name.toLowerCase().includes(q))
                    );
                    renderRows(filtered);
                });
            }
        } catch (e) {
            console.error('Error loading cascading backfills:', e);
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="py-4 text-center text-rose-600 text-xs">
                        Failed to load cascading backfills: ${e.message}
                    </td>
                </tr>
            `;
        }
    }

    // --- SIMULATION CONTROLS (AUTO-SOLVE & RESET) ---
    function initSimulationControls() {
        const btnAutoSolve = document.getElementById('btnAutoSolve');
        const btnRunSolverCascade = document.getElementById('btnRunSolverCascade');
        const btnResetSim = document.getElementById('btnResetSim');
        const btnResetCascade = document.getElementById('btnResetCascade');

        async function triggerAutoSolve() {
            if (!confirm('Run AI Autonomous Solver?\n\nThis will solve posting for all 242 roster promotees into 242 available DD posts and rehabilitate all 84 displaced serving officers into active cadre posts.')) return;
            try {
                const res = await fetch('/api/simulation/auto-solve', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: 'CURRENT_SESSION' })
                });
                const data = await res.json();
                alert(`AI Auto-Solver Completed!\n\nPromotions: ${data.summary.total_promotions}/242\nObliterated Rehabilitated: ${data.summary.total_obliterated_rehabilitated}\nRemaining DD Vacancies: ${data.summary.remaining_dd_vacancies}`);
                await initOverview();
                await loadRoster();
                await loadObliterated();
                await loadCadre();
                await loadSimulationHistory();
                await loadCascadingBackfills();
            } catch (e) {
                console.error('Auto solve error:', e);
                alert('Auto solver failed: ' + e.message);
            }
        }

        async function triggerReset() {
            if (!confirm('Reset simulation to baseline? This will clear all simulation moves and restore original status.')) return;
            try {
                await fetch('/api/simulation/reset', { method: 'POST' });
                alert('Simulation reset to baseline successfully!');
                await initOverview();
                await loadRoster();
                await loadObliterated();
                await loadCadre();
                await loadSimulationHistory();
                await loadCascadingBackfills();
            } catch (e) {
                console.error('Reset error:', e);
            }
        }

        if (btnAutoSolve) btnAutoSolve.addEventListener('click', triggerAutoSolve);
        if (btnRunSolverCascade) btnRunSolverCascade.addEventListener('click', triggerAutoSolve);
        if (btnResetSim) btnResetSim.addEventListener('click', triggerReset);
        if (btnResetCascade) btnResetCascade.addEventListener('click', triggerReset);
    }

    // --- DUAL ALLOTMENT MODAL LOGIC WITH DYNAMIC OPTION REDUCTION ---
    window.openDualAllotModal = async function(hrmsId, source) {
        if (hrmsId === '1992005664') {
            alert('Administrative Protection: Dr. Nikhil Kumar Shit is the Director of AH&VS (Level-22) and cannot be replaced, displaced, or transferred.');
            return;
        }
        const modal = document.getElementById('allotModal');
        const subSelect = document.getElementById('modalSubstantivePostSelect');
        const suSelect = document.getElementById('modalSUPostSelect');
        const suCheck = document.getElementById('modalEnableSUCheck');
        const suContainer = document.getElementById('modalSUContainer');
        const collisionAlert = document.getElementById('modalCollisionAlert');
        const subtitle = document.getElementById('modalOfficerSubtitle');
        const nameHeader = document.getElementById('modalOfficerNameHeader');
        const currPost = document.getElementById('modalCurrPost');
        const currDist = document.getElementById('modalCurrDist');
        const rosterPt = document.getElementById('modalRosterPt');
        const dorEl = document.getElementById('modalDOR');
        const prefsEl = document.getElementById('modalPrefs');

        subSelect.innerHTML = `<option value="">Loading dynamically reduced available posts...</option>`;
        suSelect.innerHTML = `<option value="">-- Choose Post for Service Utilization --</option>`;
        suCheck.checked = false;
        suContainer.classList.add('hidden');
        collisionAlert.classList.add('hidden');
        modal.classList.remove('hidden');

        state.activeModalRole = source;
        let officer = null;

        if (source === 'roster') {
            officer = state.rosterCandidates.find(c => c.hrms_id === hrmsId);
        } else if (source === 'obliterated') {
            officer = state.obliteratedOfficers.find(o => o.hrms_id === hrmsId);
        } else {
            officer = state.cadreData.find(p => p.incumbent_hrms === hrmsId);
        }

        state.activeModalOfficer = officer;

        if (officer) {
            const offName = officer.officer_name || officer.incumbent_name || 'Officer';
            const hid = officer.hrms_id || officer.incumbent_hrms || 'N/A';
            nameHeader.innerText = `${offName} (HRMS: ${hid})`;
            subtitle.innerText = `${offName} | Category: ${officer.caste || 'Gen'}`;
            currPost.innerText = officer.present_posting || officer.post_name || officer.designation || 'N/A';
            currDist.innerText = `${officer.present_block ? officer.present_block + ' Block, ' : ''}${officer.present_district || officer.district || 'N/A'}`;
            rosterPt.innerText = officer.roster_point ? `Point ${officer.roster_point} (${officer.point_reserved_for || officer.caste})` : `Cadre Post`;
            dorEl.innerText = officer.service_ends || officer.incumbent_dor || 'N/A';
            prefsEl.innerText = officer.all_preferences || officer.pref_1 || 'None listed';
        }

        const policyBox = document.getElementById('modalPolicyEvaluationBox');
        if (policyBox) policyBox.classList.add('hidden');
        state.lastPolicyEvaluation = null;

        // Trigger policy check on substantive post change
        subSelect.onchange = () => {
            if (window.triggerLivePolicyEvaluation) window.triggerLivePolicyEvaluation();
        };

        // Fetch dynamically reduced substantive posts
        try {
            const subRes = await fetch(`/api/available-posts?type=substantive&role=${source}&session_id=CURRENT_SESSION`);
            const subData = await subRes.json();
            state.substantivePosts = subData;

            if (subData.length === 0) {
                subSelect.innerHTML = `<option value="">No available posts remaining (all taken or blocked)</option>`;
            } else {
                subSelect.innerHTML = `<option value="">-- Select Target Substantive Post (${subData.length} available) --</option>` +
                    subData.map(p => `<option value="${p.post_id}">${p.display_label}</option>`).join('');
            }
        } catch (e) {
            console.error('Error fetching substantive posts:', e);
            subSelect.innerHTML = `<option value="">Error loading posts</option>`;
        }
    };

    // Toggle SU Post Selection
    document.getElementById('modalEnableSUCheck').addEventListener('change', async (e) => {
        const suContainer = document.getElementById('modalSUContainer');
        const suSelect = document.getElementById('modalSUPostSelect');
        const collisionAlert = document.getElementById('modalCollisionAlert');

        if (e.target.checked) {
            suContainer.classList.remove('hidden');
            suSelect.innerHTML = `<option value="">Loading available posts for SU...</option>`;
            try {
                const res = await fetch('/api/available-posts?type=su&session_id=CURRENT_SESSION');
                const data = await res.json();
                state.suPosts = data;

                suSelect.innerHTML = `<option value="">-- Choose Cadre Post for SU Attachment (${data.length} available) --</option>` +
                    data.map(p => `<option value="${p.post_id}">${p.display_label}</option>`).join('');
            } catch (err) {
                console.error('Error loading SU posts:', err);
                suSelect.innerHTML = `<option value="">Error loading SU posts</option>`;
            }
        } else {
            suContainer.classList.add('hidden');
            collisionAlert.classList.add('hidden');
            suSelect.value = '';
        }
        if (window.triggerLivePolicyEvaluation) window.triggerLivePolicyEvaluation();
    });

    // Handle SU Post change and trigger collision warning + policy evaluation
    document.getElementById('modalSUPostSelect').addEventListener('change', (e) => {
        const val = parseInt(e.target.value);
        const collisionAlert = document.getElementById('modalCollisionAlert');
        const collisionText = document.getElementById('modalCollisionText');

        if (!val) {
            collisionAlert.classList.add('hidden');
        } else {
            const selectedPost = state.suPosts.find(p => p.post_id === val);
            if (selectedPost && selectedPost.occupancy_status !== 'Vacant' && selectedPost.incumbent_name) {
                collisionAlert.classList.remove('hidden');
                collisionText.innerHTML = `
                    <strong>COLLISION RISK DETECTED:</strong> This post is currently occupied by <strong>${selectedPost.incumbent_name}</strong> (HRMS: ${selectedPost.incumbent_hrms}).
                    Placing this officer on Service Utilization here will trigger a displacement chain requiring rehabilitation of the incumbent!
                `;
                lucide.createIcons();
            } else {
                collisionAlert.classList.add('hidden');
            }
        }
        if (window.triggerLivePolicyEvaluation) window.triggerLivePolicyEvaluation();
    });

    // Modal Close buttons
    document.getElementById('btnCloseModal').addEventListener('click', () => {
        document.getElementById('allotModal').classList.add('hidden');
    });
    document.getElementById('btnCancelModal').addEventListener('click', () => {
        document.getElementById('allotModal').classList.add('hidden');
    });

    // Confirm Allotment submission
    document.getElementById('btnConfirmAllot').addEventListener('click', async () => {
        const subPostId = document.getElementById('modalSubstantivePostSelect').value;
        const isSU = document.getElementById('modalEnableSUCheck').checked;
        const suPostId = isSU ? document.getElementById('modalSUPostSelect').value : null;
        const reason = document.getElementById('modalReasonSelect').value;

        if (!subPostId) {
            alert('Please select a Substantive / Main Post.');
            return;
        }

        // Check if there is an unacknowledged policy violation
        if (state.lastPolicyEvaluation && state.lastPolicyEvaluation.overall_status === 'VIOLATION') {
            const proceed = confirm(
                "⚠️ POLICY VIOLATION WARNING (Transfer Policy 2009 / Memo 291):\n\n" +
                (state.lastPolicyEvaluation.violations || []).join("\n") +
                "\n\nDo you wish to proceed with an Administrative Exemption / Competent Authority Waiver?"
            );
            if (!proceed) return;
        }

        const officer = state.activeModalOfficer;
        if (!officer) return;

        const hrms = officer.hrms_id || officer.incumbent_hrms;
        const offName = officer.officer_name || officer.incumbent_name;

        try {
            const res = await fetch('/api/simulation/allot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: 'CURRENT_SESSION',
                    officer_hrms: hrms,
                    substantive_post_id: parseInt(subPostId),
                    su_post_id: suPostId ? parseInt(suPostId) : null,
                    reason: reason,
                    officer_type: state.activeModalRole
                })
            });
            const data = await res.json();

            if (data.success) {
                let msg = `Allotment Successful!\n\nOfficer: ${offName}\nSubstantive Post: ${data.substantive_post_name}`;
                if (data.su_post_name) {
                    msg += `\nService Utilization Post: ${data.su_post_name}`;
                }
                if (data.collision_detected) {
                    msg += `\n\n⚠️ Displacement Triggered: ${data.displaced_officer} (${data.displaced_hrms}) has been marked as displaced and awaiting placement.`;
                }
                alert(msg);
                document.getElementById('allotModal').classList.add('hidden');
                await initOverview();
                await loadRoster();
                await loadObliterated();
                await loadCadre();
                await loadSimulationHistory();
            } else {
                alert('Allotment error: ' + (data.error || 'Unknown error'));
            }
        } catch (e) {
            console.error('Allotment submission error:', e);
            alert('Error completing allotment: ' + e.message);
        }
    });

    // --- TRANSFER POLICY 2009 (MEMO 291) LIVE COMPLIANCE EVALUATOR ---
    function initLivePolicyEvaluator() {
        window.triggerLivePolicyEvaluation = async function() {
            const policyBox = document.getElementById('modalPolicyEvaluationBox');
            const badgeIcon = document.getElementById('modalPolicyBadgeIcon');
            const titleEl = document.getElementById('modalPolicyTitle');
            const subTitleEl = document.getElementById('modalPolicySubtitle');
            const overallBadge = document.getElementById('modalPolicyOverallBadge');
            const violationsBox = document.getElementById('modalPolicyViolations');
            const checksList = document.getElementById('modalPolicyChecksList');

            if (!policyBox) return;

            const subVal = parseInt(document.getElementById('modalSubstantivePostSelect')?.value);
            const isSU = document.getElementById('modalEnableSUCheck')?.checked;
            const suVal = isSU ? (parseInt(document.getElementById('modalSUPostSelect')?.value) || null) : null;
            const officer = state.activeModalOfficer;

            if (!subVal || !officer) {
                policyBox.classList.add('hidden');
                return;
            }

            const hrmsId = officer.hrms_id || officer.incumbent_hrms;
            if (!hrmsId) return;

            policyBox.classList.remove('hidden');
            policyBox.className = "p-3.5 rounded-xl border border-neutral-200 bg-neutral-50 transition-all duration-200 animate-pulse";
            overallBadge.innerText = "Evaluating Policy...";
            overallBadge.className = "text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider bg-neutral-200 text-neutral-700";

            try {
                const res = await fetch('/api/policy/evaluate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        officer_hrms: hrmsId,
                        substantive_post_id: subVal,
                        su_post_id: suVal,
                        officer_type: state.activeModalRole || 'roster'
                    })
                });
                const data = await res.json();
                policyBox.classList.remove('animate-pulse');

                state.lastPolicyEvaluation = data;

                // Color & Badge configuration based on Universal Color System
                if (data.overall_status === 'COMPLIANT') {
                    policyBox.className = "p-3.5 rounded-xl border border-emerald-400 bg-emerald-50/70 transition-all duration-200";
                    badgeIcon.className = "w-6 h-6 rounded-full flex items-center justify-center font-black text-xs shadow-xs bg-emerald-500 text-white";
                    badgeIcon.innerHTML = "✓";
                    titleEl.className = "text-xs font-bold leading-tight text-emerald-950";
                    titleEl.innerText = "✓ Transfer Policy 2009 Compliant (Memo 291)";
                    subTitleEl.className = "text-[10px] text-emerald-800";
                    subTitleEl.innerText = "All statutory transfer & welfare criteria satisfied. Approved for Government posting order.";
                    overallBadge.className = "text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider bg-emerald-500 text-white shadow-xs";
                    overallBadge.innerText = "✓ COMPLIANT";
                    violationsBox.classList.add('hidden');
                } else if (data.overall_status === 'VIOLATION') {
                    policyBox.className = "p-3.5 rounded-xl border border-rose-400 bg-rose-50/90 transition-all duration-200";
                    badgeIcon.className = "w-6 h-6 rounded-full flex items-center justify-center font-black text-xs shadow-xs bg-rose-500 text-white";
                    badgeIcon.innerHTML = "✗";
                    titleEl.className = "text-xs font-bold leading-tight text-rose-950";
                    titleEl.innerText = `✗ Policy Violation: ${data.summary_label}`;
                    subTitleEl.className = "text-[10px] text-rose-800";
                    subTitleEl.innerText = "Statutory conflict detected under Transfer Policy Memo 291 of 2009. Attention required before issuing order.";
                    overallBadge.className = "text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider bg-rose-600 text-white shadow-xs animate-pulse";
                    overallBadge.innerText = "✗ VIOLATION";

                    violationsBox.classList.remove('hidden');
                    violationsBox.innerHTML = `
                        <div class="font-bold flex items-center gap-1.5 text-rose-900">
                            <i data-lucide="alert-circle" class="w-3.5 h-3.5 text-rose-600"></i>
                            <span>Criteria Violations:</span>
                        </div>
                        <ul class="list-disc pl-4 space-y-0.5 text-[10px] text-rose-800">
                            ${(data.violations || []).map(v => `<li>${v}</li>`).join('')}
                        </ul>
                    `;
                } else {
                    policyBox.className = "p-3.5 rounded-xl border border-amber-400 bg-amber-50/80 transition-all duration-200";
                    badgeIcon.className = "w-6 h-6 rounded-full flex items-center justify-center font-black text-xs shadow-xs bg-amber-500 text-white";
                    badgeIcon.innerHTML = "⚠";
                    titleEl.className = "text-xs font-bold leading-tight text-amber-950";
                    titleEl.innerText = `⚠ Advisory: ${data.summary_label}`;
                    subTitleEl.className = "text-[10px] text-amber-800";
                    subTitleEl.innerText = "Administrative advisory or departmental waiver review recommended.";
                    overallBadge.className = "text-[10px] font-extrabold px-2.5 py-0.5 rounded-full uppercase tracking-wider bg-amber-500 text-white shadow-xs";
                    overallBadge.innerText = "⚠ ADVISORY";

                    if (data.cautions && data.cautions.length > 0) {
                        violationsBox.classList.remove('hidden');
                        violationsBox.innerHTML = `
                            <div class="font-bold flex items-center gap-1.5 text-amber-900">
                                <i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-amber-600"></i>
                                <span>Administrative Advisories:</span>
                            </div>
                            <ul class="list-disc pl-4 space-y-0.5 text-[10px] text-amber-800">
                                ${data.cautions.map(c => `<li>${c}</li>`).join('')}
                            </ul>
                        `;
                    } else {
                        violationsBox.classList.add('hidden');
                    }
                }

                // Render checklist pills
                if (data.checks && data.checks.length > 0) {
                    checksList.innerHTML = data.checks.map(c => {
                        let badgeCls = "bg-neutral-100 text-neutral-700 border-neutral-200";
                        let icon = "•";
                        if (c.badge === 'GREEN') {
                            badgeCls = "bg-emerald-100/90 text-emerald-900 border-emerald-300";
                            icon = "✓";
                        } else if (c.badge === 'RED') {
                            badgeCls = "bg-rose-100/90 text-rose-900 border-rose-300 font-bold";
                            icon = "✗";
                        } else if (c.badge === 'YELLOW') {
                            badgeCls = "bg-amber-100/90 text-amber-900 border-amber-300";
                            icon = "⚠";
                        } else if (c.badge === 'BLUE') {
                            badgeCls = "bg-sky-100/90 text-sky-900 border-sky-300";
                            icon = "ℹ";
                        }
                        return `
                            <div class="p-2 rounded-lg border ${badgeCls} flex items-start gap-1.5 leading-snug">
                                <span class="font-bold shrink-0">${icon}</span>
                                <div>
                                    <div class="font-bold text-[10px]">${c.criterion}</div>
                                    <div class="text-[9px] opacity-90">${c.message}</div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }

                if (window.lucide) lucide.createIcons();
            } catch (err) {
                console.error('Error evaluating policy:', err);
                overallBadge.innerText = "Error";
            }
        };
    }

    // --- UNIVERSAL SPOTLIGHT SEMANTIC SEARCH CONTROLLER ---
    function initSpotlightSearch() {
        const modal = document.getElementById('spotlightModal');
        const input = document.getElementById('spotlightInput');
        const spinner = document.getElementById('spotlightSpinner');
        const resultsContainer = document.getElementById('spotlightResultsContainer');
        const filterBtns = document.querySelectorAll('.spotlight-filter-btn');

        let currentResults = { officers: [], posts: [], orders: [], policy_rules: [] };
        let currentFilter = 'all';

        function openSpotlight() {
            if (!modal) return;
            modal.classList.remove('hidden');
            if (input) {
                input.focus();
                input.select();
            }
            if (window.lucide) lucide.createIcons();
        }

        function closeSpotlight() {
            if (!modal) return;
            modal.classList.add('hidden');
        }

        window.openSpotlightSearch = openSpotlight;
        window.closeSpotlightSearch = closeSpotlight;

        document.getElementById('btnOpenSpotlightHeader')?.addEventListener('click', openSpotlight);
        document.getElementById('btnMobileSearchTrigger')?.addEventListener('click', openSpotlight);
        document.getElementById('btnCloseSpotlightModal')?.addEventListener('click', closeSpotlight);

        modal?.addEventListener('click', (e) => {
            if (e.target === modal) closeSpotlight();
        });

        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                if (modal.classList.contains('hidden')) openSpotlight();
                else closeSpotlight();
            } else if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                e.preventDefault();
                openSpotlight();
            } else if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                closeSpotlight();
            }
        });

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const filter = btn.getAttribute('data-spotlight-filter');
                currentFilter = filter;
                filterBtns.forEach(b => {
                    if (b === btn) {
                        b.classList.add('bg-slate-800', 'text-white');
                        b.classList.remove('text-slate-600', 'text-neutral-600', 'hover:bg-slate-100', 'hover:bg-neutral-100');
                    } else {
                        b.classList.remove('bg-slate-800', 'bg-black', 'text-white');
                        b.classList.add('text-slate-600', 'hover:bg-slate-100');
                    }
                });
                renderResults();
            });
        });

        const doSearch = debounce(async (query) => {
            if (!query || query.trim().length < 1) {
                resultsContainer.innerHTML = `
                    <div class="py-12 text-center text-neutral-400 text-xs">
                        <i data-lucide="sparkles" class="w-8 h-8 text-neutral-300 mx-auto mb-2"></i>
                        <p class="font-semibold text-neutral-600">Universal Semantic Search</p>
                        <p class="text-[11px] text-neutral-400 mt-1 max-w-sm mx-auto">Instant lookup across 1,794 sanctioned posts, 242 roster candidates, 328 master orders, 73 obliterated posts, and transfer policy rules.</p>
                    </div>
                `;
                updateCounts(0, 0, 0, 0);
                if (window.lucide) lucide.createIcons();
                return;
            }

            if (spinner) spinner.classList.remove('hidden');

            try {
                const res = await fetch(`/api/search/omni?q=${encodeURIComponent(query.trim())}&limit=30`);
                const data = await res.json();
                currentResults = data;
                updateCounts(
                    data.officers?.length || 0,
                    data.posts?.length || 0,
                    data.orders?.length || 0,
                    data.policy_rules?.length || 0
                );
                renderResults();
            } catch (err) {
                console.error('Spotlight search error:', err);
                resultsContainer.innerHTML = `<div class="p-6 text-center text-rose-500 text-xs">Search error. Please try again.</div>`;
            } finally {
                if (spinner) spinner.classList.add('hidden');
            }
        }, 200);

        input?.addEventListener('input', (e) => doSearch(e.target.value));

        function updateCounts(off, post, ord, rul) {
            const oEl = document.getElementById('spotlightCountOfficers');
            const pEl = document.getElementById('spotlightCountPosts');
            const ordEl = document.getElementById('spotlightCountOrders');
            const rEl = document.getElementById('spotlightCountRules');
            if (oEl) oEl.innerText = off;
            if (pEl) pEl.innerText = post;
            if (ordEl) ordEl.innerText = ord;
            if (rEl) rEl.innerText = rul;
        }

        function renderResults() {
            const { officers = [], posts = [], orders = [], policy_rules = [] } = currentResults;
            const totalFound = officers.length + posts.length + orders.length + policy_rules.length;

            if (totalFound === 0) {
                resultsContainer.innerHTML = `
                    <div class="py-12 text-center text-neutral-400 text-xs">
                        <i data-lucide="search-x" class="w-8 h-8 text-neutral-300 mx-auto mb-2"></i>
                        <p class="font-semibold text-neutral-700">No results found</p>
                        <p class="text-[11px] text-neutral-400 mt-1">Try searching by district name, officer surname, post designation, or HRMS ID.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
                return;
            }

            let html = '';

            // 1. Officers Section
            if ((currentFilter === 'all' || currentFilter === 'officers') && officers.length > 0) {
                html += `
                    <div class="pt-2 pb-1 text-[11px] font-bold uppercase tracking-wider text-neutral-400 flex items-center justify-between">
                        <span>Officers & Personnel (${officers.length})</span>
                        <span class="text-[10px] text-neutral-400 font-normal">Click to view dossier or allot</span>
                    </div>
                `;
                officers.forEach(o => {
                    const offName = o.officer_name || 'Unnamed Officer';
                    const desig = o.designation || o.post_name || 'Officer';
                    const dist = o.district || o.present_district || 'District N/A';
                    const hid = o.hrms_id || 'N/A';
                    const source = o.source || 'master';
                    let tag = `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-neutral-100 text-neutral-700 border border-neutral-200">${source}</span>`;
                    if (source === 'roster') tag = `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">50-Pt Roster</span>`;
                    else if (source === 'obliterated') tag = `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-100 text-rose-800 border border-rose-200">Obliterated (1808)</span>`;

                    html += `
                        <div class="p-2.5 rounded-xl hover:bg-neutral-50 transition border border-transparent hover:border-neutral-200 flex items-center justify-between gap-3 group cursor-pointer" onclick="window.spotlightJumpOfficer('${hid}', '${source}')">
                            <div class="flex items-center gap-2.5 truncate">
                                <div class="w-8 h-8 rounded-full bg-neutral-100 border border-neutral-200 flex items-center justify-center text-neutral-700 shrink-0 font-bold text-xs">
                                    ${offName.charAt(3) || 'Dr'}
                                </div>
                                <div class="truncate">
                                    <div class="font-bold text-xs text-neutral-900 flex items-center gap-1.5 truncate">
                                        <span>${offName}</span>
                                        ${tag}
                                    </div>
                                    <div class="text-[11px] text-neutral-500 truncate">
                                        ${desig} • ${dist} • <span class="font-mono text-[10px]">HRMS: ${hid}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center gap-1.5 shrink-0 opacity-80 group-hover:opacity-100">
                                <button class="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-800 text-white hover:bg-slate-700 transition shadow-xs" title="Open Allotment Modal">
                                    Allot
                                </button>
                            </div>
                        </div>
                    `;
                });
            }

            // 2. Posts Section
            if ((currentFilter === 'all' || currentFilter === 'posts') && posts.length > 0) {
                html += `
                    <div class="pt-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-neutral-400 flex items-center justify-between">
                        <span>Sanctioned Cadre Posts (${posts.length})</span>
                        <span class="text-[10px] text-neutral-400 font-normal">Click to view in Cadre</span>
                    </div>
                `;
                posts.forEach(p => {
                    const pName = p.post_name || p.designation || 'Sanctioned Post';
                    const office = p.establishment || p.office || 'Office N/A';
                    const dist = p.district || 'District N/A';
                    const isVacant = p.occupancy_status === 'Vacant' || p.occupancy_status === 'Available';
                    const statusBadge = isVacant 
                        ? `<span class="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">🟢 Vacant</span>`
                        : `<span class="px-1.5 py-0.5 rounded-full text-[9px] font-bold bg-neutral-100 text-neutral-700 border border-neutral-300">Occupied: ${p.incumbent_name || 'Serving Officer'}</span>`;

                    html += `
                        <div class="p-2.5 rounded-xl hover:bg-neutral-50 transition border border-transparent hover:border-neutral-200 flex items-center justify-between gap-3 group cursor-pointer" onclick="window.spotlightJumpPost('${p.district || ''}')">
                            <div class="truncate">
                                <div class="font-bold text-xs text-neutral-900 flex items-center gap-1.5 truncate">
                                    <span>${pName}</span>
                                    ${statusBadge}
                                </div>
                                <div class="text-[11px] text-neutral-500 truncate">
                                    ${office} • ${dist} ${p.block ? '• ' + p.block + ' Block' : ''}
                                </div>
                            </div>
                            <div class="shrink-0">
                                <i data-lucide="arrow-up-right" class="w-4 h-4 text-neutral-400 group-hover:text-slate-900 transition"></i>
                            </div>
                        </div>
                    `;
                });
            }

            // 3. Official Orders Section
            if ((currentFilter === 'all' || currentFilter === 'orders') && orders.length > 0) {
                html += `
                    <div class="pt-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-neutral-400 flex items-center justify-between">
                        <span>Official Orders & Schedules (${orders.length})</span>
                    </div>
                `;
                orders.forEach(ord => {
                    const ordNo = ord.order_number || 'Official Order';
                    const date = ord.order_date || '';
                    const subject = ord.subject || ord.final_substantive_post || ord.previous_posting || '';
                    const offName = ord.officer_name ? ` • ${ord.officer_name}` : '';

                    html += `
                        <div class="p-2.5 rounded-xl hover:bg-neutral-50 transition border border-transparent hover:border-neutral-200 flex items-center justify-between gap-3 group cursor-pointer" onclick="window.spotlightJumpOrder()">
                            <div class="truncate">
                                <div class="font-bold text-xs text-neutral-900 flex items-center gap-1.5 truncate">
                                    <i data-lucide="file-text" class="w-3.5 h-3.5 text-sky-600"></i>
                                    <span>${ordNo}</span>
                                    <span class="text-[10px] text-neutral-400">${date}</span>
                                </div>
                                <div class="text-[11px] text-neutral-600 truncate">
                                    ${subject}${offName}
                                </div>
                            </div>
                            <div class="shrink-0">
                                <i data-lucide="arrow-up-right" class="w-4 h-4 text-neutral-400 group-hover:text-slate-900 transition"></i>
                            </div>
                        </div>
                    `;
                });
            }

            // 4. Policy Rules Section
            if ((currentFilter === 'all' || currentFilter === 'rules') && policy_rules.length > 0) {
                html += `
                    <div class="pt-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-neutral-400 flex items-center justify-between">
                        <span>Administrative & Transfer Policy Rules (${policy_rules.length})</span>
                    </div>
                `;
                policy_rules.forEach(rule => {
                    html += `
                        <div class="p-3 rounded-xl bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 transition space-y-1 cursor-pointer" onclick="document.getElementById('policyInfoModal')?.classList.remove('hidden'); document.getElementById('spotlightModal')?.classList.add('hidden');">
                            <div class="flex items-center justify-between">
                                <span class="font-bold text-xs text-neutral-900">${rule.title}</span>
                                <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-neutral-200 text-neutral-800">${rule.clause}</span>
                            </div>
                            <p class="text-[11px] text-neutral-600 leading-relaxed">${rule.description}</p>
                        </div>
                    `;
                });
            }

            resultsContainer.innerHTML = html;
            if (window.lucide) lucide.createIcons();
        }

        // Jump helpers
        window.spotlightJumpOfficer = function(hrmsId, source) {
            closeSpotlight();
            if (source === 'roster') {
                switchTab('tab-roster');
                setTimeout(() => openDualAllotModal(hrmsId, 'roster'), 250);
            } else if (source === 'obliterated') {
                switchTab('tab-obliterated');
                setTimeout(() => openDualAllotModal(hrmsId, 'obliterated'), 250);
            } else {
                openOfficerDossier(hrmsId);
            }
        };

        window.spotlightJumpPost = function(district) {
            closeSpotlight();
            switchTab('tab-cadre');
            const distFilter = document.getElementById('cadreDistrictFilter');
            if (distFilter && district) {
                distFilter.value = district;
                distFilter.dispatchEvent(new Event('change'));
            }
        };

        window.spotlightJumpOrder = function() {
            closeSpotlight();
            switchTab('tab-orders');
        };
    }

    // --- TRANSFER POLICY 2009 NORMS MODAL CONTROLLER ---
    function initPolicyGuideModal() {
        const modal = document.getElementById('policyInfoModal');
        const openBtn = document.getElementById('btnOpenPolicyInfoModal');
        const closeBtn = document.getElementById('btnClosePolicyInfoModal');
        const footerBtn = document.getElementById('btnClosePolicyInfoFooter');

        function openModal() {
            if (modal) modal.classList.remove('hidden');
            if (window.lucide) lucide.createIcons();
        }

        function closeModal() {
            if (modal) modal.classList.add('hidden');
        }

        openBtn?.addEventListener('click', openModal);
        closeBtn?.addEventListener('click', closeModal);
        footerBtn?.addEventListener('click', closeModal);

        modal?.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    // --- EXECUTIVE DATA EXPORTER (REMOVED) ---
    function initDataExporterModal() {
        // Disabled per administrative directive
    }


    // --- 84-HOUR DATA SYNC COUNTDOWN TIMER ---
    function initBetaSyncCountdown() {
        const elH = document.getElementById('countdownHours');
        const elM = document.getElementById('countdownMinutes');
        const elS = document.getElementById('countdownSeconds');

        const elHBanner = document.getElementById('countdownHoursBanner');
        const elMBanner = document.getElementById('countdownMinutesBanner');
        const elSBanner = document.getElementById('countdownSecondsBanner');

        const elHDrawer = document.getElementById('countdownHoursDrawer');
        const elMDrawer = document.getElementById('countdownMinutesDrawer');
        const elSDrawer = document.getElementById('countdownSecondsDrawer');

        const elHMobile = document.getElementById('countdownHoursMobile');
        const elMMobile = document.getElementById('countdownMinutesMobile');
        const elSMobile = document.getElementById('countdownSecondsMobile');

        const elStatus = document.getElementById('countdownBadgeStatus');
        const card = document.getElementById('countdownCard');

        // Baseline official start time: 15:45:00 on 2026-09-13 IST (+05:30)
        let startTime = new Date('2026-09-13T15:45:00+05:30').getTime();
        const TOTAL_DURATION_MS = 84 * 60 * 60 * 1000; // 84 hours

        // Fallback if client device clock is significantly off 2026
        const nowCheck = Date.now();
        if (Math.abs(nowCheck - startTime) > 30 * 24 * 3600 * 1000) {
            const today1545 = new Date();
            today1545.setHours(15, 45, 0, 0);
            startTime = today1545.getTime();
        }

        const targetTime = startTime + TOTAL_DURATION_MS;

        let forceElapsed = false;
        if (card) {
            card.addEventListener('click', () => {
                forceElapsed = !forceElapsed;
                tick();
            });
        }

        function setTimeDisplay(hStr, mStr, sStr) {
            if (elH) elH.textContent = hStr;
            if (elM) elM.textContent = mStr;
            if (elS) elS.textContent = sStr;

            if (elHBanner) elHBanner.textContent = hStr;
            if (elMBanner) elMBanner.textContent = mStr;
            if (elSBanner) elSBanner.textContent = sStr;

            if (elHDrawer) elHDrawer.textContent = hStr;
            if (elMDrawer) elMDrawer.textContent = mStr;
            if (elSDrawer) elSDrawer.textContent = sStr;

            if (elHMobile) elHMobile.textContent = hStr;
            if (elMMobile) elMMobile.textContent = mStr;
            if (elSMobile) elSMobile.textContent = sStr;
        }

        function tick() {
            const now = Date.now();
            let remainingMs = targetTime - now;

            // Before 15:45:
            if (now < startTime && !forceElapsed) {
                const tMinusSec = Math.max(0, Math.ceil((startTime - now) / 1000));
                const tMinusM = Math.floor(tMinusSec / 60);
                const tMinusS = tMinusSec % 60;

                setTimeDisplay('84', '00', '00');

                if (elStatus) {
                    elStatus.innerHTML = `<span class="inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span> Starts 15:45 (T-${String(tMinusM).padStart(2, '0')}:${String(tMinusS).padStart(2, '0')})</span>`;
                    elStatus.className = 'text-[10px] font-bold text-amber-300 px-2 py-0.5 rounded bg-amber-950/80 border border-amber-500/40 inline-flex items-center';
                }
            } else {
                // Active 84-hour countdown (or forced preview on click)
                if (forceElapsed && now < startTime) {
                    const elapsed = Math.floor((now % (3600 * 1000)) / 1000);
                    remainingMs = TOTAL_DURATION_MS - (elapsed * 1000);
                }

                if (remainingMs < 0) remainingMs = 0;

                const totalSec = Math.floor(remainingMs / 1000);
                const hours = Math.floor(totalSec / 3600);
                const minutes = Math.floor((totalSec % 3600) / 60);
                const seconds = totalSec % 60;

                const hStr = String(hours).padStart(2, '0');
                const mStr = String(minutes).padStart(2, '0');
                const sStr = String(seconds).padStart(2, '0');

                setTimeDisplay(hStr, mStr, sStr);

                if (elStatus) {
                    elStatus.innerHTML = `<span class="inline-flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Active 84h Sync Lock</span>`;
                    elStatus.className = 'text-[10px] font-bold text-emerald-300 px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-500/40 inline-flex items-center';
                }
            }
        }

        tick();
        setInterval(tick, 1000);
    }



    // --- TAB 6: LOAD DISPLACED OFFICERS POOL ---
    async function loadDisplacedPool() {
        const tbody = document.getElementById('displacedTableBody');
        const cardsEl = document.getElementById('displacedMobileCards');
        const badge = document.getElementById('displacedPoolStatusBadge');
        const navBadge = document.getElementById('badgeDisplacedCount');

        try {
            const res = await fetch('/api/displaced-pool?session_id=CURRENT_SESSION');
            const json = await res.json();
            const rawPool = json.data || [];
            const pool = rawPool.filter(o => 
                o.officer_hrms !== '1992005664' && 
                !((o.from_post_name || '').toLowerCase().includes('director of ah')) &&
                !((o.officer_name || '').toLowerCase().includes('nikhil kumar shit'))
            );

            if (navBadge) navBadge.innerText = pool.length;
            if (badge) badge.innerText = `${pool.length} Displaced Officers Pending Placement`;

            if (pool.length === 0) {
                if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-slate-400">No officers currently displaced. Displaced officers from Service Utilization allotments will queue here automatically.</td></tr>`;
                if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-slate-400 text-xs">No officers currently displaced. Displaced officers from Service Utilization allotments will queue here automatically.</div>`;
                return;
            }

            if (tbody) {
                tbody.innerHTML = pool.map((o, idx) => {
                    const isReallocated = o.rehabilitation_status === 'Reallocated';
                    return `
                        <tr class="hover:bg-slate-50 transition ${isReallocated ? 'bg-emerald-50/20' : 'bg-purple-50/20'}">
                            <td class="py-2.5 px-3 font-semibold text-slate-600">${idx + 1}</td>
                            <td class="py-2.5 px-4">
                                <div class="font-bold text-wbblue-900 hover:text-wbblue-600 hover:underline cursor-pointer" onclick="openOfficerDossier('${o.officer_hrms}')" title="Click to view officer personnel dossier">${o.officer_name}</div>
                                <div class="text-[11px] font-mono text-slate-500">HRMS: ${o.officer_hrms}</div>
                            </td>
                            <td class="py-2.5 px-4 font-medium text-slate-800">${o.from_post_name || 'Station'}</td>
                            <td class="py-2.5 px-3 text-slate-600">${o.block ? `${o.block}, ` : ''}${o.district}</td>
                            <td class="py-2.5 px-4">
                                <div class="text-xs font-semibold text-purple-900">Displaced by: ${o.displaced_by_name} (${o.displaced_by_hrms})</div>
                                <div class="text-[10px] text-purple-700 italic">${o.displaced_by_reason}</div>
                            </td>
                            <td class="py-2.5 px-2 text-slate-700 text-xs">${o.pay_level || 'Level 16'}</td>
                            <td class="py-2.5 px-2 text-slate-700 text-xs">${o.tenure || '0.0'} yrs</td>
                            <td class="py-2.5 px-3">
                                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${isReallocated ? 'bg-emerald-100 text-emerald-800' : 'bg-purple-100 text-purple-800'}">
                                    ${o.rehabilitation_status}
                                </span>
                            </td>
                            <td class="py-2.5 px-3 text-right whitespace-nowrap">
                                <div class="flex items-center justify-end gap-1.5">
                                    <button onclick="openDualAllotModal('${o.officer_hrms}', 'displaced')" class="px-2 py-1 text-xs font-semibold rounded bg-purple-100 hover:bg-purple-200 text-purple-800 transition">
                                        ${isReallocated ? 'Re-Allot' : 'Allot'}
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            if (cardsEl) {
                cardsEl.innerHTML = pool.map((o, idx) => {
                    const isReallocated = o.rehabilitation_status === 'Reallocated';
                    const initials = getMonogram(o.officer_name);
                    return `
                        <div class="rounded-2xl bg-white border border-purple-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.04)] mobile-card-interactive p-4 space-y-3">
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-start gap-3 min-w-0">
                                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-700 to-indigo-900 text-white font-bold flex items-center justify-center text-xs shadow-xs shrink-0 tracking-tight">
                                        ${initials}
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex flex-wrap items-center gap-1.5 mb-1">
                                            <span class="px-2 py-0.5 rounded-md bg-purple-900 text-white font-mono text-[9px] font-bold">#${idx + 1}</span>
                                            <span class="px-2 py-0.5 rounded-full text-[9px] font-bold ${isReallocated ? 'bg-emerald-100 text-emerald-800' : 'bg-purple-100 text-purple-800'}">${o.rehabilitation_status}</span>
                                            <span class="text-[10px] font-mono text-slate-500 font-bold">${o.pay_level || 'Level 16'}</span>
                                        </div>
                                        <div class="font-extrabold text-sm text-slate-900 truncate cursor-pointer hover:text-purple-700" onclick="openOfficerDossier('${o.officer_hrms}')">
                                            ${o.officer_name}
                                        </div>
                                        <div class="text-[11px] font-mono text-slate-500 flex items-center gap-1.5 mt-0.5">
                                            <span>HRMS: <strong>${o.officer_hrms}</strong></span>
                                            <span>•</span>
                                            <span>Tenure: ${o.tenure || '0.0'} yrs</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="space-y-1.5">
                                <div class="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                                        <i data-lucide="map-pin" class="w-3 h-3 text-slate-400"></i>
                                        <span>Displaced From Post</span>
                                    </div>
                                    <div class="font-semibold text-slate-800 leading-snug mt-0.5">${o.from_post_name || 'Station'}</div>
                                    <div class="text-[11px] text-slate-500 font-medium">
                                        ${o.block ? `<span class="text-slate-700 font-semibold">${o.block} Block</span>, ` : ''}${o.district}
                                    </div>
                                </div>

                                <div class="p-2.5 rounded-xl bg-purple-50/70 border border-purple-200/80 text-xs space-y-1">
                                    <div class="text-[10px] font-bold uppercase tracking-wider text-purple-900 flex items-center gap-1">
                                        <i data-lucide="shuffle" class="w-3 h-3 text-purple-600"></i>
                                        <span>Displaced By</span>
                                    </div>
                                    <div class="font-bold text-purple-950">${o.displaced_by_name} <span class="font-mono text-[11px] font-normal text-purple-700">(${o.displaced_by_hrms})</span></div>
                                    <div class="text-[11px] text-purple-800 italic leading-snug">${o.displaced_by_reason}</div>
                                </div>
                            </div>

                            <div class="flex items-center gap-2 pt-1 border-t border-slate-100">
                                <button onclick="openOfficerDossier('${o.officer_hrms}')" class="flex-1 py-2 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 btn-touch touch-target">
                                    <i data-lucide="user" class="w-3.5 h-3.5"></i>
                                    <span>Dossier</span>
                                </button>
                                <button onclick="openDualAllotModal('${o.officer_hrms}', 'displaced')" class="flex-1 py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs shadow-xs flex items-center justify-center gap-1.5 btn-touch touch-target">
                                    <i data-lucide="shuffle" class="w-3.5 h-3.5"></i>
                                    <span>${isReallocated ? 'Re-Allot' : 'Allot Post'}</span>
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Error loading displaced pool:', e);
            if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-rose-500">Failed to load displaced pool.</td></tr>`;
            if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-rose-500 text-xs">Failed to load displaced pool.</div>`;
        }
    }

    // --- CADRE WATERFALL HIERARCHY MODAL LOGIC ---
    window.openWaterfallModal = async function() {
        const modal = document.getElementById('waterfallModal');
        const tierTbody = document.getElementById('wfTierTableBody');
        const estabTbody = document.getElementById('wfEstabTableBody');

        tierTbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-400">Loading waterfall hierarchy data...</td></tr>`;
        estabTbody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-slate-400">Loading establishments...</td></tr>`;
        modal.classList.remove('hidden');

        try {
            const res = await fetch('/api/cadre/hierarchy');
            const data = await res.json();

            document.getElementById('wfSanctioned').innerText = Number(data.summary.sanctioned_posts).toLocaleString();
            document.getElementById('wfOccupied').innerText = Number(data.summary.occupied_posts).toLocaleString();
            document.getElementById('wfOccupancyRate').innerText = `${data.summary.occupancy_rate_pct}% Occupancy`;
            document.getElementById('wfVacant').innerText = Number(data.summary.vacant_posts).toLocaleString();
            document.getElementById('wfVacancyRate').innerText = `${(100 - data.summary.occupancy_rate_pct).toFixed(1)}% Vacant`;

            tierTbody.innerHTML = data.tiers.map((t, i) => {
                const occPct = t.sanctioned > 0 ? Math.round((t.occupied / t.sanctioned) * 100) : 0;
                return `
                    <tr class="hover:bg-slate-50 transition font-medium">
                        <td class="py-2.5 px-3">
                            <div class="font-bold text-slate-900 flex items-center gap-1.5">
                                <span class="text-slate-400 text-[10px]">#${i+1}</span>
                                <span>${t.tier}</span>
                            </div>
                        </td>
                        <td class="py-2.5 px-3 font-mono font-semibold text-wbblue-800">${t.level}</td>
                        <td class="py-2.5 px-2 text-center font-bold text-slate-800">${t.sanctioned}</td>
                        <td class="py-2.5 px-2 text-center font-semibold text-blue-700">${t.occupied}</td>
                        <td class="py-2.5 px-2 text-center font-semibold text-emerald-700">${t.vacant}</td>
                        <td class="py-2.5 px-3">
                            <div class="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden flex">
                                <div class="bg-wbblue-600 h-2.5" style="width: ${occPct}%" title="${occPct}% Occupied"></div>
                                <div class="bg-emerald-500 h-2.5" style="width: ${100 - occPct}%" title="${100 - occPct}% Vacant"></div>
                            </div>
                            <div class="text-[9px] text-slate-500 text-right mt-0.5">${occPct}% occ</div>
                        </td>
                    </tr>
                `;
            }).join('');

            estabTbody.innerHTML = data.establishment_distribution.map(e => `
                <tr class="hover:bg-slate-50 text-[11px]">
                    <td class="py-1.5 px-3 font-medium text-slate-800">${e.estab_type.replace(/_/g, ' ')}</td>
                    <td class="py-1.5 px-2 text-center font-bold text-slate-700">${e.sanctioned}</td>
                    <td class="py-1.5 px-2 text-center text-blue-700">${e.occupied}</td>
                    <td class="py-1.5 px-2 text-center text-emerald-700 font-semibold">${e.vacant}</td>
                </tr>
            `).join('');
            lucide.createIcons();
        } catch (err) {
            console.error('Failed to load waterfall hierarchy:', err);
            tierTbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-rose-500">Failed to load waterfall data.</td></tr>`;
        }
    };

    document.getElementById('btnCloseWaterfallModal')?.addEventListener('click', () => {
        document.getElementById('waterfallModal').classList.add('hidden');
    });
    document.getElementById('btnCloseWaterfallFooter')?.addEventListener('click', () => {
        document.getElementById('waterfallModal').classList.add('hidden');
    });
    // --- TOP KPI STATUS CARDS INTERACTION ---
    function initKPICardClickHandlers() {
        window.setActiveKPICard = function(cardId) {
            document.querySelectorAll('.kpi-card').forEach(c => {
                c.classList.remove('ring-2', 'ring-offset-2', 'shadow-md', 'scale-[1.02]');
                c.classList.remove('ring-wbblue-600', 'ring-emerald-600', 'ring-blue-600', 'ring-teal-600', 'ring-amber-600', 'ring-rose-600', 'ring-red-600', 'ring-purple-600');
            });
            const card = document.getElementById(cardId);
            if (card) {
                card.classList.add('ring-2', 'ring-offset-2', 'shadow-md', 'scale-[1.02]');
                if (cardId === 'kpiCardTotalPosts') card.classList.add('ring-wbblue-600');
                else if (cardId === 'kpiCardTotalVacancies') card.classList.add('ring-emerald-600');
                else if (cardId === 'kpiCardVacantDD') card.classList.add('ring-blue-600');
                else if (cardId === 'kpiCardVacantAD') card.classList.add('ring-teal-600');
                else if (cardId === 'kpiCardRoster') card.classList.add('ring-amber-600');
                else if (cardId === 'kpiCardObliterated') card.classList.add('ring-rose-600');
                else if (cardId === 'kpiCardOverTenure') card.classList.add('ring-red-600');
                else if (cardId === 'kpiCardCollisions') card.classList.add('ring-purple-600');
            }
        };

        const triggerTab = (tabId) => {
            const btn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
            if (btn) btn.click();
        };

        // 1. Total Posts -> Department Cadre (All 1,794 posts)
        const cardTotal = document.getElementById('kpiCardTotalPosts');
        if (cardTotal) {
            cardTotal.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardTotalPosts');
                triggerTab('tab-cadre');
                const statusF = document.getElementById('cadreStatusFilter');
                const desigF = document.getElementById('cadreDesigFilter');
                const distF = document.getElementById('cadreDistrictFilter');
                const tenureF = document.getElementById('cadreTenureFilter');
                const avdF = document.getElementById('cadreAVDFilter');
                const searchF = document.getElementById('cadreSearchInput');
                if (statusF) statusF.value = 'ALL';
                if (desigF) desigF.value = 'ALL';
                if (distF) distF.value = 'ALL';
                if (tenureF) tenureF.value = 'ALL';
                if (avdF) avdF.value = 'ALL';
                if (searchF) searchF.value = '';
                state.cadreOffset = 0;
                loadCadre();
                document.getElementById('tab-cadre')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // 2. Clear Vacancies -> Department Cadre (Clear Vacancies only: 747)
        const cardVac = document.getElementById('kpiCardTotalVacancies');
        if (cardVac) {
            cardVac.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardTotalVacancies');
                triggerTab('tab-cadre');
                const statusF = document.getElementById('cadreStatusFilter');
                const desigF = document.getElementById('cadreDesigFilter');
                const distF = document.getElementById('cadreDistrictFilter');
                const tenureF = document.getElementById('cadreTenureFilter');
                const avdF = document.getElementById('cadreAVDFilter');
                const searchF = document.getElementById('cadreSearchInput');
                if (statusF) statusF.value = 'vacant';
                if (desigF) desigF.value = 'ALL';
                if (distF) distF.value = 'ALL';
                if (tenureF) tenureF.value = 'ALL';
                if (avdF) avdF.value = 'ALL';
                if (searchF) searchF.value = '';
                state.cadreOffset = 0;
                loadCadre();
                document.getElementById('tab-cadre')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // 3. Available DD Posts -> Department Cadre (Vacant Deputy Director posts)
        const cardDD = document.getElementById('kpiCardVacantDD');
        if (cardDD) {
            cardDD.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardVacantDD');
                triggerTab('tab-cadre');
                const statusF = document.getElementById('cadreStatusFilter');
                const desigF = document.getElementById('cadreDesigFilter');
                const distF = document.getElementById('cadreDistrictFilter');
                const tenureF = document.getElementById('cadreTenureFilter');
                const avdF = document.getElementById('cadreAVDFilter');
                const searchF = document.getElementById('cadreSearchInput');
                if (statusF) statusF.value = 'vacant';
                if (searchF) searchF.value = 'Deputy Director';
                if (desigF) desigF.value = 'ALL';
                if (distF) distF.value = 'ALL';
                if (tenureF) tenureF.value = 'ALL';
                if (avdF) avdF.value = 'ALL';
                state.cadreOffset = 0;
                loadCadre();
                document.getElementById('tab-cadre')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // 4. AD Vacancies -> Department Cadre (Vacant Assistant Director posts)
        const cardAD = document.getElementById('kpiCardVacantAD');
        if (cardAD) {
            cardAD.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardVacantAD');
                triggerTab('tab-cadre');
                const statusF = document.getElementById('cadreStatusFilter');
                const desigF = document.getElementById('cadreDesigFilter');
                const distF = document.getElementById('cadreDistrictFilter');
                const tenureF = document.getElementById('cadreTenureFilter');
                const avdF = document.getElementById('cadreAVDFilter');
                const searchF = document.getElementById('cadreSearchInput');
                if (statusF) statusF.value = 'vacant';
                if (searchF) searchF.value = 'Assistant Director';
                if (desigF) desigF.value = 'ALL';
                if (distF) distF.value = 'ALL';
                if (tenureF) tenureF.value = 'ALL';
                if (avdF) avdF.value = 'ALL';
                state.cadreOffset = 0;
                loadCadre();
                document.getElementById('tab-cadre')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // 5. 50-Point Roster -> 50-Point Roster Panel
        const cardRoster = document.getElementById('kpiCardRoster');
        if (cardRoster) {
            cardRoster.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardRoster');
                triggerTab('tab-roster');
                const catF = document.getElementById('rosterCategoryFilter');
                const statF = document.getElementById('rosterStatusFilter');
                const searchF = document.getElementById('rosterSearchInput');
                if (catF) catF.value = 'ALL';
                if (statF) statF.value = 'ALL';
                if (searchF) searchF.value = '';
                loadRoster();
                document.getElementById('tab-roster')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // 6. Obliterated Posts -> Obliterated Posts Memo 1808
        const cardOblit = document.getElementById('kpiCardObliterated');
        if (cardOblit) {
            cardOblit.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardObliterated');
                triggerTab('tab-obliterated');
                const statF = document.getElementById('oblitStatusFilter');
                const searchF = document.getElementById('oblitSearchInput');
                if (statF) statF.value = 'ALL';
                if (searchF) searchF.value = '';
                loadObliterated();
                document.getElementById('tab-obliterated')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // 7. Tenure Over (>4/5y) -> Department Cadre (Tenure norm exceeded: 321)
        const cardTenure = document.getElementById('kpiCardOverTenure');
        if (cardTenure) {
            cardTenure.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardOverTenure');
                triggerTab('tab-cadre');
                const statusF = document.getElementById('cadreStatusFilter');
                const tenureF = document.getElementById('cadreTenureFilter');
                const desigF = document.getElementById('cadreDesigFilter');
                const distF = document.getElementById('cadreDistrictFilter');
                const avdF = document.getElementById('cadreAVDFilter');
                const searchF = document.getElementById('cadreSearchInput');
                if (statusF) statusF.value = 'occupied';
                if (tenureF) tenureF.value = 'Yes';
                if (desigF) desigF.value = 'ALL';
                if (distF) distF.value = 'ALL';
                if (avdF) avdF.value = 'ALL';
                if (searchF) searchF.value = '';
                state.cadreOffset = 0;
                loadCadre();
                document.getElementById('tab-cadre')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // 8. Collisions / Displaced -> Displaced Queue Pool
        const cardColl = document.getElementById('kpiCardCollisions');
        if (cardColl) {
            cardColl.addEventListener('click', () => {
                window.setActiveKPICard('kpiCardCollisions');
                triggerTab('tab-displaced');
                loadDisplacedPool();
                document.getElementById('tab-displaced')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }

        // Initial default active card matching default tab (tab-roster)
        window.setActiveKPICard('kpiCardRoster');
    }

    // --- OFFICER PERSONNEL DOSSIER MODAL LOGIC ---
    // --- OFFICER PERSONNEL DOSSIER & DISTRICT POST VISUALIZER ---
    window.activeDossierOfficer = null;

    window.switchDossierSubTab = function(tabName) {
        const tabs = ['profile', 'preferences', 'history', 'family', 'competencies', 'responses', 'grid'];
        tabs.forEach(t => {
            const btn = document.getElementById(`dossierSubTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
            const sec = document.getElementById(`dossierSec${t.charAt(0).toUpperCase() + t.slice(1)}`);
            if (btn) {
                if (t === tabName) {
                    btn.className = "dossier-tab-btn px-3 py-2 border-b-2 border-wbblue-700 text-wbblue-800 font-bold flex items-center gap-1.5 shrink-0 transition";
                } else {
                    btn.className = "dossier-tab-btn px-3 py-2 text-slate-500 hover:text-slate-800 flex items-center gap-1.5 shrink-0 transition";
                }
            }
            if (sec) {
                if (t === tabName) {
                    sec.classList.remove('hidden');
                } else {
                    sec.classList.add('hidden');
                }
            }
        });

        if (tabName === 'grid' && window.activeDossierOfficer) {
            window.renderVisualGrid('modalVisualGridContainer', true, window.activeDossierOfficer.hrms_id);
        }
    };

    window.filterSelfReported = function(query) {
        const q = (query || '').toLowerCase().trim();
        const items = document.querySelectorAll('.self-reported-item');
        let visibleCount = 0;
        items.forEach(el => {
            const text = el.textContent.toLowerCase();
            if (!q || text.includes(q)) {
                el.classList.remove('hidden');
                visibleCount++;
            } else {
                el.classList.add('hidden');
            }
        });
        const badge = document.getElementById('selfReportedCountBadge');
        if (badge) badge.innerText = `${visibleCount} of ${items.length} responses`;
    };

    window.openOfficerDossier = async function(hrmsId) {
        const modal = document.getElementById('officerDossierModal');
        const container = document.getElementById('dossierContent');
        const subtitle = document.getElementById('dossierSubtitle');
        const btnAI = document.getElementById('btnDossierAIAllot');

        container.innerHTML = `<div class="py-12 text-center text-slate-400">Loading comprehensive personnel dossier for HRMS ${hrmsId}...</div>`;
        modal.classList.remove('hidden');

        try {
            const res = await fetch(`/api/officer/${encodeURIComponent(hrmsId)}`);
            if (!res.ok) throw new Error('Officer record not found');
            const d = await res.json();
            window.activeDossierOfficer = d;

            if (window.sendTelemetryPing) {
                window.sendTelemetryPing('dossier_view', `Officer Dossier: ${d.officer_name} (${d.hrms_id})`);
            }

            subtitle.innerText = `${d.officer_name} | HRMS: ${d.hrms_id} | ${d.source_category}`;

            btnAI.onclick = () => {
                modal.classList.add('hidden');
                openAIAllotModal(d.hrms_id, 'roster');
            };

            const mo = d.master_final_order;
            const masterOrderHtml = mo ? `
                <div class="p-4 rounded-xl bg-gradient-to-r from-emerald-950 via-teal-950 to-slate-900 text-white shadow-md border border-emerald-500/50 space-y-2.5">
                    <div class="flex items-center justify-between flex-wrap gap-2">
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-0.5 rounded-full bg-emerald-500 text-white font-bold text-[10px] tracking-wider uppercase shadow-sm">Verified Authoritative Proposed Order</span>
                            <span class="text-xs text-emerald-200 font-semibold">Sl #${mo.sl_no} ${mo.roster_sl && mo.roster_sl !== '-' ? `(Roster Pt: ${mo.roster_sl})` : ''}</span>
                        </div>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-200 border border-emerald-400/40">
                            ${mo.transfer_basis || 'Cadre Allotment'}
                        </span>
                    </div>
                    <div class="space-y-1.5 pt-1">
                        <div class="text-xs flex items-start gap-2">
                            <span class="text-amber-300 font-bold shrink-0 text-[11px] uppercase tracking-wide">Transferred Substantive Post:</span>
                            <span class="font-semibold text-white leading-relaxed">${mo.transferred_substantive_post || '-'}</span>
                        </div>
                        ${mo.service_utilized_at && mo.service_utilized_at !== 'Nil' ? `
                            <div class="text-xs flex items-start gap-2">
                                <span class="text-teal-300 font-bold shrink-0 text-[11px] uppercase tracking-wide">Service Utilized At (SU):</span>
                                <span class="font-semibold text-teal-100 leading-relaxed">${mo.service_utilized_at}</span>
                            </div>
                        ` : ''}
                        ${mo.administrative_remarks ? `
                            <div class="text-[11px] text-slate-300 flex items-start gap-2 pt-1 border-t border-white/10">
                                <span class="text-slate-400 font-medium shrink-0">Remarks / Directives:</span>
                                <span>${mo.administrative_remarks} ${mo.comments_directive ? `(${mo.comments_directive})` : ''}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            ` : '';

            // Photo avatar markup
            let photoHtml = '';
            if (d.photo_display_url) {
                photoHtml = `
                    <div class="relative group shrink-0">
                        <img src="${d.photo_display_url}" 
                             onerror="this.onerror=null; this.parentElement.innerHTML='<div class=\\'w-20 h-20 rounded-xl bg-wbblue-100 border-2 border-wbblue-300 text-wbblue-800 font-bold flex items-center justify-center text-xl shadow\\'>${(d.officer_name || 'Dr').replace(/^Dr\\.?\\s*/i, '').split(' ').filter(Boolean).map(n=>n[0]).slice(0,2).join('').toUpperCase()}</div>';" 
                             alt="${d.officer_name}" 
                             class="w-20 h-20 rounded-xl object-cover border-2 border-wbblue-400 shadow-md group-hover:shadow-lg transition">
                        ${d.photo_url ? `
                            <a href="${d.photo_url}" target="_blank" class="absolute inset-0 bg-slate-900/60 text-white rounded-xl opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center text-[10px] font-bold transition gap-0.5">
                                <i data-lucide="external-link" class="w-4 h-4"></i>
                                <span>Full Photo</span>
                            </a>
                        ` : ''}
                    </div>
                `;
            } else {
                photoHtml = `
                    <div class="w-20 h-20 rounded-xl bg-gradient-to-br from-wbblue-700 to-indigo-800 text-white font-bold flex items-center justify-center text-xl shadow-md shrink-0">
                        ${(d.officer_name || 'Dr').replace(/^Dr\\.?\\s*/i, '').split(' ').filter(Boolean).map(n=>n[0]).slice(0,2).join('').toUpperCase() || 'DR'}
                    </div>
                `;
            }

            // Contacts bar
            const mobileHtml = (d.mobile && d.mobile !== '—') ? `
                <div class="flex items-center gap-2 flex-wrap">
                    <strong class="text-slate-600">Mobile:</strong>
                    <span class="font-mono text-slate-900 font-bold">${d.mobile}</span>
                    <a href="tel:${d.mobile}" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-100 text-blue-800 hover:bg-blue-200 text-[10px] font-bold transition shadow-xs">
                        <i data-lucide="phone" class="w-3 h-3"></i> Call
                    </a>
                    <a href="https://wa.me/91${d.mobile}" target="_blank" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 hover:bg-emerald-200 text-[10px] font-bold transition shadow-xs">
                        <i data-lucide="message-circle" class="w-3 h-3"></i> WhatsApp
                    </a>
                </div>
            ` : `<div><strong class="text-slate-600">Mobile:</strong> <span class="text-slate-400 italic">Not recorded</span></div>`;

            const altMobileHtml = (d.alt_mobile && d.alt_mobile !== '—' && d.alt_mobile !== '') ? `
                <div class="flex items-center gap-1.5 text-slate-600">
                    <strong class="text-slate-600">Alt Mobile:</strong>
                    <span class="font-mono text-slate-800 font-semibold">${d.alt_mobile}</span>
                    <a href="tel:${d.alt_mobile}" class="text-[10px] text-blue-700 hover:underline">Call</a>
                </div>
            ` : '';

            const emailHtml = (d.email && d.email !== '—') ? `
                <div class="flex items-center gap-1.5 truncate">
                    <strong class="text-slate-600">Email:</strong>
                    <a href="mailto:${d.email}" class="text-wbblue-700 hover:underline truncate">${d.email}</a>
                </div>
            ` : `<div><strong class="text-slate-600">Email:</strong> <span class="text-slate-400 italic">Not recorded</span></div>`;

            // Welfare banners
            const welfareAlerts = [];
            if (d.children_board_exams && d.children_board_exams !== '—') {
                welfareAlerts.push(`
                    <div class="p-3 rounded-lg bg-purple-50 border border-purple-200 text-purple-900 flex items-start gap-2.5">
                        <i data-lucide="graduation-cap" class="w-4 h-4 text-purple-700 shrink-0 mt-0.5"></i>
                        <div>
                            <span class="font-bold text-purple-950">Children Board Exam Year:</span> ${d.children_board_exams}
                            <div class="text-[10px] text-purple-700 font-medium mt-0.5">Transfer Policy 2009 statutory accommodation priority for board exam candidates.</div>
                        </div>
                    </div>
                `);
            }
            if (d.spouse_service_details && d.spouse_service_details !== '—' && !d.spouse_service_details.includes('Standard') && !d.spouse_service_details.includes('No spouse')) {
                welfareAlerts.push(`
                    <div class="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 flex items-start gap-2.5">
                        <i data-lucide="heart-handshake" class="w-4 h-4 text-amber-700 shrink-0 mt-0.5"></i>
                        <div>
                            <span class="font-bold text-amber-950">Spouse in Public Service:</span> ${d.spouse_service_details}
                            <div class="text-[10px] text-amber-700 font-medium mt-0.5">Memo 291 Clause 7 Co-location safeguard applies for working spouses.</div>
                        </div>
                    </div>
                `);
            }
            if (d.health_conditions && d.health_conditions !== '—' && !d.health_conditions.includes('Standard')) {
                welfareAlerts.push(`
                    <div class="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-2.5">
                        <i data-lucide="activity" class="w-4 h-4 text-rose-700 shrink-0 mt-0.5"></i>
                        <div>
                            <span class="font-bold text-rose-950">Medical / Health Ground:</span> ${d.health_conditions} ${d.health_details ? `(${d.health_details})` : ''}
                        </div>
                    </div>
                `);
            }

            // Stated Field Preferences (1 to 8 + free text)
            const rawPrefs = d.preferences_list && d.preferences_list.length > 0 ? d.preferences_list : Object.entries(d.preferences || {});
            let prefsHtml = '';
            if (rawPrefs.length > 0) {
                prefsHtml = rawPrefs.map(([k, v]) => {
                    const isMatched = mo && (
                        (mo.transferred_substantive_post && mo.transferred_substantive_post.toLowerCase().includes(v.toLowerCase())) ||
                        (mo.service_utilized_at && mo.service_utilized_at.toLowerCase().includes(v.toLowerCase())) ||
                        (v.toLowerCase().includes('kalyani') && (mo.transferred_substantive_post && mo.transferred_substantive_post.toLowerCase().includes('kalyani') || (mo.service_utilized_at && mo.service_utilized_at.toLowerCase().includes('kalyani'))))
                    );
                    return `
                        <div class="p-2.5 rounded-lg border ${isMatched ? 'border-emerald-400 bg-emerald-50/60' : 'border-slate-200 bg-white'} flex items-start justify-between gap-2 shadow-xs">
                            <div class="text-[11px] leading-relaxed">
                                <strong class="text-slate-700 uppercase text-[10px] tracking-wider">${k.replace(/_/g, ' ')}:</strong>
                                <span class="text-slate-900 ml-1 font-medium">${v}</span>
                            </div>
                            ${isMatched ? `
                                <span class="px-2 py-0.5 rounded bg-emerald-600 text-white text-[9px] font-bold shrink-0 uppercase tracking-wider shadow-xs">
                                    Choice Matched
                                </span>
                            ` : ''}
                        </div>
                    `;
                }).join('');
            } else {
                prefsHtml = `<div class="p-3 bg-slate-50 text-slate-400 italic rounded border border-slate-200">No field preferences recorded for this officer.</div>`;
            }

            // DD Promotional Preferences
            const dd = d.dd_preferences || {};
            const ddChoices = dd.preferences || [];
            let ddChoicesHtml = '';
            if (ddChoices.length > 0) {
                ddChoicesHtml = ddChoices.map(c => {
                    const isMatched = mo && (
                        (mo.transferred_substantive_post && mo.transferred_substantive_post.toLowerCase().includes(c.choice.toLowerCase())) ||
                        (c.choice.toLowerCase().includes('kalyani') && mo.transferred_substantive_post && mo.transferred_substantive_post.toLowerCase().includes('kalyani'))
                    );
                    return `
                        <div class="p-2.5 rounded-lg border ${isMatched ? 'border-emerald-400 bg-emerald-50/70 shadow-xs' : 'border-slate-200 bg-white'} flex items-start justify-between gap-2">
                            <div class="text-xs">
                                <span class="font-bold text-wbblue-800 mr-1.5">Choice #${c.rank}:</span>
                                <span class="text-slate-800 font-medium">${c.choice}</span>
                            </div>
                            ${isMatched ? `
                                <span class="px-2 py-0.5 rounded bg-emerald-600 text-white text-[9px] font-bold shrink-0 uppercase tracking-wider shadow-xs">
                                    DD Post Matched
                                </span>
                            ` : ''}
                        </div>
                    `;
                }).join('');
            } else {
                ddChoicesHtml = `<div class="p-2.5 bg-slate-50 text-slate-400 italic rounded text-xs">No DD tier preferences specified.</div>`;
            }

            const ddFreeText = [dd.free_text_1, dd.free_text_2, dd.free_text].filter(Boolean).join('; ');
            const publicVision = d.public_service_statement || dd.public_service_statement || '';
            const relocationWill = d.willing_to_relocate || dd.willing_to_relocate || '';

            // JD Preferences
            const jd = d.jd_preferences || {};
            const jdChoices = jd.preferences || [];
            let jdChoicesHtml = '';
            if (jdChoices.length > 0) {
                jdChoicesHtml = jdChoices.map(c => `
                    <div class="p-2.5 rounded-lg border border-slate-200 bg-white flex items-start gap-2 text-xs">
                        <span class="font-bold text-teal-800 mr-1.5">Choice #${c.rank}:</span>
                        <span class="text-slate-800">${c.choice}</span>
                    </div>
                `).join('');
            }

            // AD Preferences
            const ad = d.ad_preferences || {};
            const adChoices = ad.preferences || [];
            let adChoicesHtml = '';
            if (adChoices.length > 0) {
                adChoicesHtml = adChoices.map(c => `
                    <div class="p-2.5 rounded-lg border border-slate-200 bg-white flex items-start gap-2 text-xs">
                        <span class="font-bold text-indigo-800 mr-1.5">Choice #${c.rank}:</span>
                        <span class="text-slate-800">${c.choice}</span>
                    </div>
                `).join('');
            }

            // Posting history
            const rawHistory = d.posting_history_list && d.posting_history_list.length > 0 ? d.posting_history_list : [];
            let historyTimelineHtml = '';
            if (rawHistory.length > 0) {
                historyTimelineHtml = rawHistory.map((item, idx) => {
                    if (typeof item === 'object' && item !== null) {
                        const sl = item.posting_sl || idx + 1;
                        const post = item.post || item.designation || 'Cadre Post';
                        const est = item.establishment || item.office || '';
                        const div = item.division || item.district || '';
                        const fromDate = item.from || '';
                        const toDate = item.to || '';
                        const charge = item.charge_type || 'Main charge';
                        return `
                            <div class="flex items-start gap-3 p-3 rounded-xl bg-white border border-slate-200 shadow-xs hover:border-wbblue-300 transition">
                                <div class="w-7 h-7 rounded-full bg-wbblue-100 text-wbblue-800 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                                    ${sl}
                                </div>
                                <div class="flex-1 space-y-1">
                                    <div class="flex items-center justify-between flex-wrap gap-1">
                                        <span class="font-bold text-slate-900 text-xs">${post}</span>
                                        ${charge ? `<span class="px-2 py-0.5 rounded text-[10px] font-semibold ${charge.includes('SU') || charge.includes('deputation') ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800'}">${charge}</span>` : ''}
                                    </div>
                                    ${est && est !== post ? `<div class="text-xs text-slate-700"><strong>Station / Office:</strong> ${est}</div>` : ''}
                                    ${div ? `<div class="text-xs text-slate-600"><strong>Division / Zone:</strong> ${div}</div>` : ''}
                                    <div class="text-[11px] text-slate-500 font-mono flex items-center gap-1.5 pt-0.5">
                                        <i data-lucide="calendar" class="w-3 h-3 text-slate-400"></i>
                                        <span>Tenure: <strong class="text-slate-700">${fromDate || 'Entry'}</strong> to <strong class="text-slate-700">${toDate || 'Present'}</strong></span>
                                    </div>
                                </div>
                            </div>
                        `;
                    } else {
                        return `
                            <div class="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200 shadow-xs">
                                <div class="w-6 h-6 rounded-full bg-wbblue-100 text-wbblue-800 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                                    ${idx + 1}
                                </div>
                                <div class="text-xs text-slate-800 font-medium leading-relaxed flex-1">
                                    ${item}
                                </div>
                            </div>
                        `;
                    }
                }).join('');
            } else if (d.posting_history) {
                const textItems = (d.posting_history || '').split(/(?=\d+\))/).map(s => s.trim()).filter(Boolean);
                historyTimelineHtml = textItems.map((item, idx) => `
                    <div class="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200 shadow-xs">
                        <div class="w-6 h-6 rounded-full bg-wbblue-100 text-wbblue-800 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                            ${idx + 1}
                        </div>
                        <div class="text-xs text-slate-800 font-medium leading-relaxed flex-1">
                            ${item}
                        </div>
                    </div>
                `).join('');
            } else {
                historyTimelineHtml = `<div class="p-3 bg-slate-50 rounded border text-slate-600 text-center italic">Standard service tenure across departmental postings.</div>`;
            }

            // 4-Stream Strengths Ranking
            let streamHtml = '';
            if (d.stream_ranking) {
                const parts = d.stream_ranking.split(',').map(s => s.trim()).filter(Boolean);
                streamHtml = parts.map(p => {
                    const [label, rank] = p.split(':').map(s => s.trim());
                    let colorClass = 'bg-slate-100 text-slate-800 border-slate-300';
                    if (rank && rank.includes('1')) colorClass = 'bg-emerald-50 text-emerald-900 border-emerald-300 font-bold';
                    else if (rank && rank.includes('2')) colorClass = 'bg-blue-50 text-blue-900 border-blue-300 font-semibold';
                    else if (rank && rank.includes('3')) colorClass = 'bg-amber-50 text-amber-900 border-amber-300';
                    return `
                        <div class="p-2.5 rounded-lg border ${colorClass} flex items-center justify-between text-xs shadow-xs">
                            <span class="font-medium">${label || p}</span>
                            <span class="px-2 py-0.5 rounded text-[10px] bg-white/80 font-bold border border-current">${rank || ''}</span>
                        </div>
                    `;
                }).join('');
            }

            // Self reported questions (all 114+ fields)
            const selfRepData = d.self_reported_data || {};
            const selfRepEntries = Object.entries(selfRepData);
            let selfRepHtml = '';
            if (selfRepEntries.length > 0) {
                selfRepHtml = `
                    <div class="space-y-3">
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-slate-100 rounded-lg border border-slate-200">
                            <div>
                                <div class="font-bold text-slate-800 text-xs">Self-Reported Survey & Preference Responses</div>
                                <div class="text-[11px] text-slate-500">Verified master response dataset (204-column record for HRMS ${d.hrms_id})</div>
                            </div>
                            <div class="flex items-center gap-2">
                                <span id="selfReportedCountBadge" class="px-2.5 py-1 rounded bg-teal-100 text-teal-800 font-bold text-[11px] border border-teal-300 shrink-0">
                                    ${selfRepEntries.length} responses
                                </span>
                                <input type="text" placeholder="Filter questions..." oninput="window.filterSelfReported(this.value)" class="text-xs px-2.5 py-1 rounded-lg border border-slate-300 bg-white focus:ring-2 focus:ring-teal-600 w-44">
                            </div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-[480px] overflow-y-auto p-1">
                            ${selfRepEntries.map(([question, answer]) => `
                                <div class="self-reported-item p-3 rounded-lg border border-slate-200 bg-white shadow-xs space-y-1 hover:border-teal-400 transition">
                                    <div class="text-[11px] font-semibold text-wbblue-900 leading-snug">${question}</div>
                                    <div class="text-xs text-slate-800 font-medium break-words leading-relaxed">${answer || '<span class="text-slate-400 italic">Nil / Not specified</span>'}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            } else {
                selfRepHtml = `<div class="p-4 text-center text-slate-400 italic bg-slate-50 rounded-lg border border-slate-200">No self-reported questionnaire responses recorded for this officer.</div>`;
            }

            container.innerHTML = `
                <!-- TAB 1: SERVICE & IDENTITY PROFILE -->
                <div id="dossierSecProfile" class="dossier-sec space-y-4">
                    ${masterOrderHtml}

                    ${welfareAlerts.length > 0 ? `<div class="space-y-2">${welfareAlerts.join('')}</div>` : ''}

                    ${d.attention_flag ? `
                        <div class="p-3.5 rounded-lg bg-rose-50 border border-rose-300 text-rose-900 flex items-start gap-3 shadow-sm animate-pulse">
                            <i data-lucide="alert-octagon" class="w-5 h-5 text-rose-600 shrink-0 mt-0.5"></i>
                            <div>
                                <div class="font-bold text-xs uppercase tracking-wider text-rose-700">Administrative Attention Flag</div>
                                <div class="text-xs font-semibold text-rose-900 mt-0.5">${d.attention_reason || 'Incumbent seated on abolished post or cascading field vacancy pending.'}</div>
                                ${d.decision_note ? `<div class="text-[11px] text-rose-800 mt-1 font-mono">Note: ${d.decision_note}</div>` : ''}
                            </div>
                        </div>
                    ` : ''}

                    <!-- Identity & Contacts Grid with Photo -->
                    <div class="flex flex-col sm:flex-row items-start gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
                        ${photoHtml}
                        <div class="flex-1 space-y-2">
                            <div class="flex items-center justify-between flex-wrap gap-2">
                                <div>
                                    <div class="text-base font-bold text-slate-900 flex items-center gap-2">
                                        <span>${d.officer_name}</span>
                                        ${d.caste ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-200 text-slate-800">${d.caste}</span>` : ''}
                                        ${d.gender && d.gender !== '—' ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-blue-100 text-blue-800">${d.gender}</span>` : ''}
                                    </div>
                                    <div class="text-[11px] font-mono text-wbblue-700 font-bold mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                                        <span>HRMS ID: ${d.hrms_id}</span>
                                        ${d.wbvc_reg_no && d.wbvc_reg_no !== '—' ? `<span>WBVC Reg: ${d.wbvc_reg_no}</span>` : ''}
                                        ${d.employee_id && d.employee_id !== '—' ? `<span>Emp ID: ${d.employee_id}</span>` : ''}
                                        ${d.gradation_sl && d.gradation_sl !== '—' ? `<span>Gradation Sl: ${d.gradation_sl}</span>` : ''}
                                        ${d.caste ? `<span class="px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 font-semibold">Category: ${d.caste}</span>` : ''}
                                    </div>
                                </div>
                                <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-wbblue-100 text-wbblue-800 border border-wbblue-200">
                                    ${d.source_category || 'WBAH&VS Cadre'}
                                </span>
                            </div>
                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-slate-200 text-[11px]">
                                ${mobileHtml}
                                ${emailHtml}
                                ${altMobileHtml}
                                ${d.languages ? `<div><strong class="text-slate-600">Languages:</strong> <span class="text-slate-800 font-medium">${d.languages}</span></div>` : ''}
                            </div>
                        </div>
                    </div>

                    <!-- Dates of Service & WBSR Rule 75(a) -->
                    <div class="grid grid-cols-3 gap-2 p-3 rounded-lg bg-blue-50/50 border border-blue-200 text-center">
                        <div>
                            <div class="text-[10px] text-blue-700 font-semibold">Date of Birth (DOB)</div>
                            <div class="text-xs font-bold text-slate-900 font-mono">${d.dob}</div>
                        </div>
                        <div>
                            <div class="text-[10px] text-blue-700 font-semibold">Seniority Entry (DOJ)</div>
                            <div class="text-xs font-bold text-slate-900 font-mono">${d.doj}</div>
                        </div>
                        <div>
                            <div class="text-[10px] text-blue-700 font-semibold">Superannuation (DOR)</div>
                            <div class="text-xs font-bold text-rose-700 font-mono">${d.dor}</div>
                            <div class="text-[9px] text-blue-600 font-medium">Rule 75(a) Compliant</div>
                        </div>
                    </div>

                    <!-- Present Posting & Pay Details -->
                    <div class="p-3.5 rounded-lg border border-slate-200 bg-white space-y-2.5">
                        <div class="font-bold text-slate-800 flex items-center justify-between">
                            <span class="flex items-center gap-1.5">
                                <i data-lucide="building-2" class="w-4 h-4 text-wbblue-700"></i>
                                <span>Present Posting, Charge & Tenure Details</span>
                            </span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.tenure_norm_status === 'Yes' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'}">
                                ${d.tenure_norm_status === 'Yes' ? 'Tenure Over (>4/5y)' : 'Within Tenure Norm'}
                            </span>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                            <div><strong class="text-slate-600">Designation:</strong> <span class="font-semibold text-slate-900">${d.current_designation}</span></div>
                            <div><strong class="text-slate-600">Station/Office:</strong> <span class="text-slate-800">${d.establishment}</span></div>
                            <div><strong class="text-slate-600">Block / District:</strong> <span class="text-slate-800">${d.block ? `${d.block}, ` : ''}${d.district}</span></div>
                            <div><strong class="text-slate-600">Station Tenure:</strong> <span class="font-bold ${d.tenure_norm_status === 'Yes' ? 'text-red-700' : 'text-slate-800'}">${d.tenure_years} yrs</span></div>
                            ${d.present_doj ? `<div><strong class="text-slate-600">Present Post DOJ:</strong> <span class="font-mono text-slate-800 font-semibold">${d.present_doj}</span></div>` : ''}
                            ${d.charge_type ? `<div><strong class="text-slate-600">Charge Type:</strong> <span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 font-medium text-[11px]">${d.charge_type}</span></div>` : ''}
                            ${d.additional_charges ? `<div class="col-span-1 sm:col-span-2"><strong class="text-slate-600">Additional Charges:</strong> <span class="text-slate-800">${d.additional_charges}</span></div>` : ''}
                            ${d.last_order_no ? `<div><strong class="text-slate-600">Last Order No:</strong> <span class="font-mono text-slate-800">${d.last_order_no}</span> ${d.last_order_date ? `dt. ${d.last_order_date}` : ''}</div>` : ''}
                            ${d.continue_in_present_post ? `<div class="col-span-1 sm:col-span-2 p-2 rounded bg-amber-50 border border-amber-200 text-amber-900"><strong class="text-amber-950">Prayer to Continue in Present Post:</strong> ${d.continue_in_present_post}</div>` : ''}
                            <div><strong class="text-slate-600">Office Code:</strong> <span class="font-mono text-slate-700">${d.office_code}</span></div>
                            <div><strong class="text-slate-600">DDO Code:</strong> <span class="font-mono text-slate-700">${d.ddo_code}</span></div>
                            <div class="col-span-1 sm:col-span-2"><strong class="text-slate-600">Present Scale:</strong> ${d.present_pay_level}</div>
                        </div>
                    </div>

                    <!-- Permanent & Current Addresses -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50/50">
                        <div>
                            <div class="font-bold text-slate-700 flex items-center gap-1 mb-1">
                                <i data-lucide="home" class="w-3.5 h-3.5 text-slate-500"></i>
                                <span>Ancestral Permanent Address</span>
                            </div>
                            <div class="text-[11px] text-slate-800 bg-white p-2 rounded border border-slate-200 leading-relaxed">
                                ${d.ancestral_address}
                                ${d.ancestral_district ? `<div class="text-slate-500 font-medium mt-0.5">District: ${d.ancestral_district}</div>` : ''}
                            </div>
                        </div>
                        <div>
                            <div class="font-bold text-slate-700 flex items-center gap-1 mb-1">
                                <i data-lucide="building" class="w-3.5 h-3.5 text-slate-500"></i>
                                <span>Current Residential Address</span>
                            </div>
                            <div class="text-[11px] text-slate-800 bg-white p-2 rounded border border-slate-200 leading-relaxed">
                                ${d.current_address}
                                ${d.current_district ? `<div class="text-slate-500 font-medium mt-0.5">District: ${d.current_district} ${d.current_pin ? `· PIN: ${d.current_pin}` : ''}</div>` : ''}
                            </div>
                        </div>
                        ${d.temp_address ? `
                            <div class="col-span-1 md:col-span-2 text-[11px] text-slate-700 bg-white p-2 rounded border border-slate-200">
                                <strong>Temporary / Rented Residence:</strong> ${d.temp_address}
                            </div>
                        ` : ''}
                        ${d.post_retirement_district ? `
                            <div class="col-span-1 md:col-span-2 text-[11px] text-slate-700 bg-white p-2 rounded border border-slate-200 flex items-center gap-2">
                                <i data-lucide="compass" class="w-3.5 h-3.5 text-wbblue-600 shrink-0"></i>
                                <span><strong>Post-Retirement Intended Settlement District:</strong> ${d.post_retirement_district}</span>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Current Simulated Allotment -->
                    ${d.latest_allotment ? `
                        <div class="p-3 rounded-lg border border-emerald-300 bg-emerald-50 space-y-1">
                            <div class="font-bold text-emerald-900 flex items-center gap-1.5">
                                <i data-lucide="check-circle" class="w-4 h-4 text-emerald-700"></i>
                                <span>Active Board Simulation Allotment</span>
                            </div>
                            <div class="text-xs text-emerald-950">
                                <div><strong>Substantive Main:</strong> ${d.latest_allotment.substantive_post_name}</div>
                                ${d.latest_allotment.su_post_name ? `<div><strong>Service Utilization (SU):</strong> ${d.latest_allotment.su_post_name}</div>` : ''}
                                <div class="text-[10px] text-slate-500 font-mono mt-0.5">Recorded: ${d.latest_allotment.timestamp} | Reason: ${d.latest_allotment.reason}</div>
                            </div>
                        </div>
                    ` : ''}
                </div>

                <!-- TAB 2: PREFERENCES & PUBLIC SERVICE VISION -->
                <div id="dossierSecPreferences" class="dossier-sec hidden space-y-4">
                    <!-- General Field Preferences -->
                    <div class="p-3.5 rounded-xl border border-slate-200 bg-white space-y-2">
                        <div class="font-bold text-slate-900 flex items-center justify-between">
                            <span class="flex items-center gap-1.5">
                                <i data-lucide="compass" class="w-4 h-4 text-wbblue-700"></i>
                                <span>Submitted General Field Preferences (Choices 1 - 8)</span>
                            </span>
                            <span class="text-xs text-slate-500">Matching with Authoritative Master Order</span>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                            ${prefsHtml}
                        </div>
                    </div>

                    <!-- Deputy Director (DD) Promotional Preferences -->
                    <div class="p-3.5 rounded-xl border border-blue-200 bg-blue-50/40 space-y-2.5">
                        <div class="font-bold text-wbblue-900 flex items-center gap-1.5">
                            <i data-lucide="award" class="w-4 h-4 text-wbblue-700"></i>
                            <span>Deputy Director (DD) Promotional Tier Preferences</span>
                        </div>
                        <div class="space-y-1.5">
                            ${ddChoicesHtml}
                        </div>
                        ${ddFreeText ? `
                            <div class="p-2.5 rounded bg-white border border-blue-200 text-xs text-slate-800">
                                <strong class="text-wbblue-900">DD Specific Preference / Free Text:</strong> ${ddFreeText}
                            </div>
                        ` : ''}
                        ${relocationWill ? `
                            <div class="p-2.5 rounded bg-white border border-blue-200 text-xs text-slate-800 flex items-center gap-2">
                                <i data-lucide="map-pin" class="w-3.5 h-3.5 text-wbblue-600 shrink-0"></i>
                                <div><strong class="text-wbblue-900">Willingness to Relocate:</strong> ${relocationWill}</div>
                            </div>
                        ` : ''}
                        ${publicVision ? `
                            <div class="p-3 rounded-lg bg-gradient-to-r from-blue-900 to-indigo-900 text-white space-y-1 shadow-sm">
                                <div class="text-[10px] uppercase font-bold tracking-wider text-blue-200 flex items-center gap-1.5">
                                    <i data-lucide="sparkles" class="w-3.5 h-3.5 text-amber-300"></i>
                                    <span>Officer Public Service Vision & Mission Statement</span>
                                </div>
                                <div class="text-xs font-semibold leading-relaxed text-blue-50">
                                    "${publicVision}"
                                </div>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Joint Director & Additional Director Choices -->
                    ${(jdChoices.length > 0 || adChoices.length > 0) ? `
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                            ${jdChoices.length > 0 ? `
                                <div class="p-3.5 rounded-xl border border-teal-200 bg-teal-50/40 space-y-2">
                                    <div class="font-bold text-teal-900 text-xs flex items-center gap-1.5">
                                        <i data-lucide="layers" class="w-4 h-4 text-teal-700"></i>
                                        <span>Joint Director (JD) Preferences</span>
                                    </div>
                                    <div class="space-y-1.5">${jdChoicesHtml}</div>
                                </div>
                            ` : ''}
                            ${adChoices.length > 0 ? `
                                <div class="p-3.5 rounded-xl border border-indigo-200 bg-indigo-50/40 space-y-2">
                                    <div class="font-bold text-indigo-900 text-xs flex items-center gap-1.5">
                                        <i data-lucide="shield" class="w-4 h-4 text-indigo-700"></i>
                                        <span>Additional Director (AD) Preferences</span>
                                    </div>
                                    <div class="space-y-1.5">${adChoicesHtml}</div>
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>

                <!-- TAB 3: POSTING HISTORY TIMELINE -->
                <div id="dossierSecHistory" class="dossier-sec hidden space-y-3">
                    <div class="p-3 bg-blue-50/60 border border-blue-200 rounded-lg text-xs text-blue-900 flex items-center justify-between">
                        <div>
                            <strong>Complete Career Posting Record:</strong> Chronological record of all 8 postings, transfers, and station tenures from verified departmental files.
                        </div>
                        <span class="px-2 py-0.5 rounded bg-blue-200 text-blue-950 font-bold text-[10px] shrink-0">
                            ${rawHistory.length} Postings Recorded
                        </span>
                    </div>
                    <div class="space-y-2.5 max-h-[500px] overflow-y-auto p-1">
                        ${historyTimelineHtml}
                    </div>
                </div>

                <!-- TAB 4: FAMILY & WELFARE SAFEGUARDS -->
                <div id="dossierSecFamily" class="dossier-sec hidden space-y-4">
                    <!-- Spouse Matter -->
                    <div class="p-3.5 rounded-xl border border-amber-200 bg-amber-50/40 space-y-2.5">
                        <div class="font-bold text-amber-900 flex items-center gap-1.5">
                            <i data-lucide="heart-handshake" class="w-4 h-4 text-amber-700"></i>
                            <span>Spouse Public Service Profile & Co-Location Safeguards (Memo 291)</span>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs bg-white p-3 rounded-lg border border-amber-200">
                            <div><strong class="text-slate-600">Spouse Name:</strong> <span class="text-slate-900 font-semibold">${d.spouse_name || 'Not recorded'}</span></div>
                            <div><strong class="text-slate-600">Department:</strong> <span class="text-slate-800">${d.spouse_dept || '—'}</span></div>
                            <div><strong class="text-slate-600">Designation:</strong> <span class="text-slate-800">${d.spouse_desig || '—'}</span></div>
                            <div><strong class="text-slate-600">Posting Station:</strong> <span class="text-slate-800">${d.spouse_block ? `${d.spouse_block}, ` : ''}${d.spouse_district || '—'}</span></div>
                            <div><strong class="text-slate-600">Is WBAH&VS Member:</strong> <span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.spouse_is_wbahvs === 'Yes' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}">${d.spouse_is_wbahvs || 'No'}</span></div>
                        </div>
                        <div class="text-xs text-amber-950 bg-amber-100/60 p-2.5 rounded border border-amber-300/60 leading-relaxed">
                            <strong>Statutory Safeguard Note:</strong> ${d.spouse_service_details}
                        </div>
                    </div>

                    <!-- Children & Dependants -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div class="p-3.5 rounded-xl border border-purple-200 bg-purple-50/40 space-y-2">
                            <div class="font-bold text-purple-900 flex items-center gap-1.5 text-xs">
                                <i data-lucide="graduation-cap" class="w-4 h-4 text-purple-700"></i>
                                <span>Children & Academic Board Exams</span>
                            </div>
                            <div class="bg-white p-2.5 rounded-lg border border-purple-200 text-xs space-y-1.5">
                                <div><strong class="text-slate-600">Children Count:</strong> <span class="font-bold text-slate-800">${d.children_count || '0'}</span></div>
                                ${d.children_board_exams ? `
                                    <div class="p-2 rounded bg-purple-100 text-purple-950 font-medium">
                                        <strong>Board Exam Year:</strong> ${d.children_board_exams}
                                    </div>
                                ` : '<div class="text-slate-400 italic">No 2026-27 board exams recorded.</div>'}
                            </div>
                        </div>

                        <div class="p-3.5 rounded-xl border border-slate-200 bg-white space-y-2">
                            <div class="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                                <i data-lucide="users" class="w-4 h-4 text-wbblue-700"></i>
                                <span>Family Dependencies & Care</span>
                            </div>
                            <div class="bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-xs text-slate-800 leading-relaxed">
                                ${d.family_dependencies || 'Standard family dependencies.'}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- TAB 5: HEALTH & COMPETENCIES -->
                <div id="dossierSecCompetencies" class="dossier-sec hidden space-y-4">
                    <!-- Medical Grounds -->
                    <div class="p-3.5 rounded-xl border border-rose-200 bg-rose-50/40 space-y-2.5">
                        <div class="font-bold text-rose-900 flex items-center gap-1.5">
                            <i data-lucide="activity" class="w-4 h-4 text-rose-700"></i>
                            <span>Medical Conditions & Special Treatment Requirements</span>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs bg-white p-3 rounded-lg border border-rose-200">
                            <div><strong class="text-slate-600">Officer Condition:</strong> <span class="text-slate-900 font-medium">${d.health_conditions || 'None reported'}</span></div>
                            <div><strong class="text-slate-600">Spouse Condition:</strong> <span class="text-slate-800">${d.spouse_health || 'None reported'}</span></div>
                            <div><strong class="text-slate-600">Care Needed:</strong> <span class="text-slate-800">${d.care_needed || '—'}</span></div>
                            <div><strong class="text-slate-600">Facility Needed:</strong> <span class="text-slate-800">${d.facility_needed || '—'}</span></div>
                            <div class="col-span-1 sm:col-span-2"><strong class="text-slate-600">PwD Status:</strong> <span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.pwd_status && d.pwd_status !== 'Not applicable' ? 'bg-amber-100 text-amber-900' : 'bg-slate-100 text-slate-700'}">${d.pwd_status || 'Not applicable'}</span></div>
                        </div>
                    </div>

                    <!-- Academic & Specializations -->
                    <div class="p-3.5 rounded-xl border border-slate-200 bg-white space-y-2">
                        <div class="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                            <i data-lucide="graduation-cap" class="w-4 h-4 text-indigo-700"></i>
                            <span>Academic Qualifications & Post-Graduate Specializations</span>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
                            <div><strong class="text-slate-600">Degree:</strong> <span class="text-slate-900 font-bold">${d.qualifications || d.academic_details || 'B.V.Sc. & A.H.'}</span></div>
                            <div><strong class="text-slate-600">MVSc / PhD Specialization:</strong> <span class="text-slate-900 font-semibold">${d.mvsc_specialization || '—'}</span></div>
                            ${d.skills_certifications ? `<div class="col-span-1 sm:col-span-2"><strong class="text-slate-600">Skills / Certifications:</strong> <span class="text-slate-800">${d.skills_certifications}</span></div>` : ''}
                        </div>
                    </div>

                    <!-- 4-Stream Strengths Ranking -->
                    ${streamHtml ? `
                        <div class="p-3.5 rounded-xl border border-slate-200 bg-slate-50/60 space-y-2">
                            <div class="font-bold text-slate-800 flex items-center gap-1.5 text-xs">
                                <i data-lucide="bar-chart-2" class="w-4 h-4 text-wbblue-700"></i>
                                <span>Self-Evaluated Core Strengths Ranking (4 Departmental Streams)</span>
                            </div>
                            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                                ${streamHtml}
                            </div>
                        </div>
                    ` : ''}
                </div>

                <!-- TAB 6: SELF-REPORTED FORM RESPONSES (114+ QUESTIONS) -->
                <div id="dossierSecResponses" class="dossier-sec hidden space-y-3">
                    ${selfRepHtml}
                </div>

                <!-- TAB 7: DISTRICT POSTINGS / INTERACTIVE ALLOCATION COCKPIT -->
                <div id="dossierSecGrid" class="dossier-sec hidden space-y-3.5">
                    <!-- Instruction Alert Banner -->
                    <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                        <div class="text-emerald-950">
                            <span class="font-bold flex items-center gap-1.5 text-emerald-900"><i data-lucide="crosshair" class="w-4 h-4 text-emerald-700"></i> Interactive Allocation Cockpit</span>
                            <div class="text-slate-700 mt-0.5">Click any post card below to allot directly to <strong>${d.officer_name}</strong> (HRMS: ${d.hrms_id}) as <em>Substantive Main</em> or <em>Service Utilization (SU)</em>.</div>
                        </div>
                        <div class="shrink-0 flex items-center gap-1.5">
                            <span class="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-semibold border border-emerald-300">Live Allotment Mode</span>
                        </div>
                    </div>

                    <!-- Prominent Colour Code Legend Bar -->
                    <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2 shadow-sm">
                        <div class="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center justify-between">
                            <span class="flex items-center gap-1.5">
                                <i data-lucide="palette" class="w-3.5 h-3.5 text-wbblue-700"></i>
                                <span>Official Post Colour Codes & Status Guide</span>
                            </span>
                            <span class="text-[10px] text-slate-500 font-normal">Click any card to allot; click filter pills below to isolate posts</span>
                        </div>
                        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-xs">
                            <div class="p-2 rounded-lg bg-emerald-50 border border-emerald-200 flex flex-col justify-between cursor-pointer hover:border-emerald-400 hover:shadow transition" onclick="window.setModalCockpitStatusFilter('VACANT_PURE')">
                                <div class="flex items-center gap-1.5 font-bold text-emerald-800 text-[11px]">
                                    <span class="w-2.5 h-2.5 rounded-full bg-emerald-600"></span>
                                    <span>Pure Vacancy</span>
                                </div>
                                <div class="text-[10px] text-emerald-700 mt-1 leading-tight">Clear Sanctioned Cadre Vacancy. Available for immediate allotment.</div>
                            </div>
                            <div class="p-2 rounded-lg bg-purple-50 border border-purple-200 flex flex-col justify-between cursor-pointer hover:border-purple-400 hover:shadow transition" onclick="window.setModalCockpitStatusFilter('DD')">
                                <div class="flex items-center gap-1.5 font-bold text-purple-800 text-[11px]">
                                    <span class="w-2.5 h-2.5 rounded-full bg-purple-600"></span>
                                    <span>DD Promotional Post</span>
                                </div>
                                <div class="text-[10px] text-purple-700 mt-1 leading-tight">Pay Level 19 DD post for 50-Point Roster Candidates.</div>
                            </div>
                            <div class="p-2 rounded-lg bg-amber-50 border border-amber-200 flex flex-col justify-between cursor-pointer hover:border-amber-400 hover:shadow transition" onclick="window.setModalCockpitStatusFilter('VACANT_ON_PAPER')">
                                <div class="flex items-center gap-1.5 font-bold text-amber-800 text-[11px]">
                                    <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                                    <span>Vacant on Paper</span>
                                </div>
                                <div class="text-[10px] text-amber-700 mt-1 leading-tight">Substantively occupied, but incumbent is on SU elsewhere.</div>
                            </div>
                            <div class="p-2 rounded-lg bg-slate-100 border border-slate-200 flex flex-col justify-between cursor-pointer hover:border-slate-400 hover:shadow transition" onclick="window.setModalCockpitStatusFilter('FILLED_NORMAL')">
                                <div class="flex items-center gap-1.5 font-bold text-slate-800 text-[11px]">
                                    <span class="w-2.5 h-2.5 rounded-full bg-slate-600"></span>
                                    <span>Occupied Post</span>
                                </div>
                                <div class="text-[10px] text-slate-600 mt-1 leading-tight">Regular serving cadre officer currently in position.</div>
                            </div>
                            <div class="p-2 rounded-lg bg-rose-50 border border-rose-200 flex flex-col justify-between cursor-pointer hover:border-rose-400 hover:shadow transition" onclick="window.setModalCockpitStatusFilter('ATTENTION_REQUIRED')">
                                <div class="flex items-center gap-1.5 font-bold text-rose-800 text-[11px]">
                                    <span class="w-2.5 h-2.5 rounded-full bg-rose-600"></span>
                                    <span>Action Required</span>
                                </div>
                                <div class="text-[10px] text-rose-700 mt-1 leading-tight">Cascading replacement / conflict / tenure priority post.</div>
                            </div>
                            <div class="p-2 rounded-lg bg-slate-100 border border-slate-300 flex flex-col justify-between opacity-75">
                                <div class="flex items-center gap-1.5 font-bold text-slate-600 text-[11px] line-through">
                                    <span class="w-2.5 h-2.5 rounded-full bg-slate-400"></span>
                                    <span>Obliterated (1808)</span>
                                </div>
                                <div class="text-[10px] text-slate-500 mt-1 leading-tight">Abolished under Notification 1808. Reserved for rehabilitation.</div>
                            </div>
                        </div>
                    </div>

                    <!-- Search & Quick Filters Toolbar -->
                    <div class="p-3 bg-white border border-slate-200 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-2.5 shadow-sm">
                        <div class="flex-1 flex items-center gap-2">
                            <div class="relative flex-1">
                                <i data-lucide="search" class="w-4 h-4 text-slate-400 absolute left-3 top-2.5"></i>
                                <input type="text" id="modalCockpitSearch" oninput="window.filterModalCockpitGrid()" placeholder="Quick search post ID, designation, block, office, or incumbent..." class="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg bg-slate-50/50 focus:bg-white focus:ring-2 focus:ring-emerald-500 focus:outline-none">
                            </div>
                            <select id="modalCockpitDistrictFilter" onchange="window.filterModalCockpitGrid()" class="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:ring-2 focus:ring-emerald-500 font-medium">
                                <option value="ALL">All Districts & Complexes</option>
                            </select>
                        </div>
                        <div class="flex flex-wrap items-center gap-1.5 text-xs">
                            <button onclick="window.setModalCockpitStatusFilter('ALL')" id="modalFilterBtn-ALL" class="modal-cockpit-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 text-white shadow-sm transition">All (<span id="modalCockpitCountAll">0</span>)</button>
                            <button onclick="window.setModalCockpitStatusFilter('VACANT_PURE')" id="modalFilterBtn-VACANT_PURE" class="modal-cockpit-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-100 text-emerald-800 hover:bg-emerald-200 border border-emerald-300 transition">🟢 Vacancies (<span id="modalCockpitCountPure">0</span>)</button>
                            <button onclick="window.setModalCockpitStatusFilter('DD')" id="modalFilterBtn-DD" class="modal-cockpit-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-purple-100 text-purple-800 hover:bg-purple-200 border border-purple-300 transition">🟣 DD Posts (<span id="modalCockpitCountDD">0</span>)</button>
                            <button onclick="window.setModalCockpitStatusFilter('VACANT_ON_PAPER')" id="modalFilterBtn-VACANT_ON_PAPER" class="modal-cockpit-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-100 text-amber-800 hover:bg-amber-200 border border-amber-300 transition">🟡 On Paper (<span id="modalCockpitCountPaper">0</span>)</button>
                            <button onclick="window.setModalCockpitStatusFilter('FILLED_NORMAL')" id="modalFilterBtn-FILLED_NORMAL" class="modal-cockpit-filter-btn px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 transition">🔘 Occupied (<span id="modalCockpitCountOccupied">0</span>)</button>
                        </div>
                    </div>

                    <!-- Post Visualizer Grid Container -->
                    <div id="modalVisualGridContainer" class="space-y-4 max-h-[550px] overflow-y-auto p-1 pr-2">
                        <div class="py-8 text-center text-slate-400">Loading district posts grid...</div>
                    </div>
                </div>
            `;
            lucide.createIcons();
            window.switchDossierSubTab('profile');
        } catch (err) {
            console.error('Failed to load dossier:', err);
            container.innerHTML = `<div class="py-12 text-center text-rose-500 font-medium">Failed to load officer dossier: ${err.message}</div>`;
        }
    };

    // --- SLEEK TOAST NOTIFICATION UTILITY ---
    window.showToast = function(message, type = 'info') {
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'fixed bottom-5 right-5 z-[9999] flex flex-col gap-2 pointer-events-none max-w-sm';
            document.body.appendChild(toastContainer);
        }
        const toast = document.createElement('div');
        toast.className = `p-3.5 rounded-lg shadow-xl text-xs font-semibold text-white pointer-events-auto transition transform duration-300 ease-out flex items-center gap-2.5 translate-y-2 opacity-0 ${
            type === 'success' ? 'bg-emerald-600' :
            type === 'error' ? 'bg-rose-600' :
            type === 'warning' ? 'bg-amber-600' : 'bg-slate-800'
        }`;
        const iconName = type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info';
        toast.innerHTML = `<i data-lucide="${iconName}" class="w-4 h-4 shrink-0"></i><span>${message}</span>`;
        toastContainer.appendChild(toast);
        lucide.createIcons();
        setTimeout(() => {
            toast.classList.remove('translate-y-2', 'opacity-0');
        }, 10);
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 350);
        }, 4000);
    };

    // --- COCKPIT FILTER STATE & CONTROLS ---
    window.currentModalCockpitStatusFilter = 'ALL';

    window.setModalCockpitStatusFilter = function(status) {
        window.currentModalCockpitStatusFilter = status;
        document.querySelectorAll('.modal-cockpit-filter-btn').forEach(btn => {
            btn.classList.remove('ring-2', 'ring-slate-900', 'shadow-md');
        });
        const activeBtn = document.getElementById(`modalFilterBtn-${status}`);
        if (activeBtn) {
            activeBtn.classList.add('ring-2', 'ring-slate-900', 'shadow-md');
        }
        window.filterModalCockpitGrid();
    };

    window.filterModalCockpitGrid = function() {
        const searchVal = (document.getElementById('modalCockpitSearch')?.value || '').toLowerCase().trim();
        const distVal = document.getElementById('modalCockpitDistrictFilter')?.value || 'ALL';
        const statusVal = window.currentModalCockpitStatusFilter || 'ALL';

        const distCards = document.querySelectorAll('#modalVisualGridContainer .district-grid-card');
        let totalVisiblePosts = 0;

        distCards.forEach(distCard => {
            const dName = distCard.getAttribute('data-district');
            const matchesDistrict = (distVal === 'ALL' || distVal === dName);
            
            let visibleInDist = 0;
            const postCards = distCard.querySelectorAll('.post-cockpit-card');
            postCards.forEach(card => {
                const cardStatus = card.getAttribute('data-status-code');
                const cardType = card.getAttribute('data-post-type');
                const searchText = (card.getAttribute('data-search-text') || '').toLowerCase();

                let matchesSearch = !searchVal || searchText.includes(searchVal);
                let matchesStatus = true;
                if (statusVal === 'VACANT_PURE') {
                    matchesStatus = (cardStatus === 'VACANT_PURE');
                } else if (statusVal === 'DD') {
                    matchesStatus = (cardType === 'DD');
                } else if (statusVal === 'VACANT_ON_PAPER') {
                    matchesStatus = (cardStatus === 'VACANT_ON_PAPER');
                } else if (statusVal === 'FILLED_NORMAL') {
                    matchesStatus = (cardStatus === 'FILLED_NORMAL');
                } else if (statusVal === 'ATTENTION_REQUIRED') {
                    matchesStatus = (cardStatus === 'ATTENTION_REQUIRED');
                }

                if (matchesDistrict && matchesSearch && matchesStatus) {
                    card.classList.remove('hidden');
                    visibleInDist++;
                    totalVisiblePosts++;
                } else {
                    card.classList.add('hidden');
                }
            });

            // Hide or show the whole district group if it has matching posts
            if (matchesDistrict && visibleInDist > 0) {
                distCard.classList.remove('hidden');
                const counter = distCard.querySelector('.district-matching-counter');
                if (counter) counter.innerText = `${visibleInDist} visible`;
            } else {
                distCard.classList.add('hidden');
            }
        });

        // Handle empty search results
        let emptyMsg = document.getElementById('modalCockpitEmptyMsg');
        const container = document.getElementById('modalVisualGridContainer');
        if (totalVisiblePosts === 0 && container) {
            if (!emptyMsg) {
                emptyMsg = document.createElement('div');
                emptyMsg.id = 'modalCockpitEmptyMsg';
                emptyMsg.className = 'py-12 text-center text-slate-500 font-medium bg-slate-50 rounded-lg border border-dashed border-slate-300';
                emptyMsg.innerHTML = '<i data-lucide="inbox" class="w-8 h-8 text-slate-400 mx-auto mb-2"></i><div>No matching posts found for the selected filters.</div><div class="text-xs text-slate-400 mt-1">Try clearing your search query or choosing "All".</div>';
                container.appendChild(emptyMsg);
                lucide.createIcons();
            } else {
                emptyMsg.classList.remove('hidden');
            }
        } else if (emptyMsg) {
            emptyMsg.classList.add('hidden');
        }
    };

    // --- DISTRICT POST VISUALIZER GRID COMPONENT ---
    window.renderVisualGrid = async function(containerId, isModal = false, targetHrmsId = null) {
        const container = document.getElementById(containerId);
        if (!container) return;

        try {
            const res = await fetch('/api/posts/visual-grid');
            if (!res.ok) throw new Error('Failed to load visual grid data');
            const data = await res.json();

            // Update main screen legend counts if on main screen
            const elPure = document.getElementById('legendCountPure');
            const elPaper = document.getElementById('legendCountPaper');
            const elAttention = document.getElementById('legendCountAttention');
            const elBoard = document.getElementById('legendCountBoard');
            const elFilled = document.getElementById('legendCountFilled');
            if (elPure && data.summary) {
                elPure.innerText = data.summary.pure_vacant;
                elPaper.innerText = data.summary.vacant_on_paper;
                elAttention.innerText = data.summary.attention_required;
                elBoard.innerText = data.summary.board_selected;
                elFilled.innerText = data.summary.filled;
            }

            // Calculate status totals across entire grid for cockpit filters
            let totalCount = 0, pureCount = 0, ddCount = 0, paperCount = 0, filledCount = 0;
            data.grid.forEach(dg => {
                (dg.dd_posts || []).forEach(p => {
                    totalCount++;
                    ddCount++;
                    if (p.status_code === 'VACANT_PURE') pureCount++;
                });
                (dg.cadre_posts || []).forEach(p => {
                    totalCount++;
                    if (p.status_code === 'VACANT_PURE') pureCount++;
                    else if (p.status_code === 'VACANT_ON_PAPER') paperCount++;
                    else if (p.status_code === 'FILLED_NORMAL') filledCount++;
                });
            });

            // Update modal cockpit filter count badges if in modal
            const mCountAll = document.getElementById('modalCockpitCountAll');
            const mCountPure = document.getElementById('modalCockpitCountPure');
            const mCountDD = document.getElementById('modalCockpitCountDD');
            const mCountPaper = document.getElementById('modalCockpitCountPaper');
            const mCountOccupied = document.getElementById('modalCockpitCountOccupied');
            if (mCountAll) mCountAll.innerText = totalCount;
            if (mCountPure) mCountPure.innerText = pureCount;
            if (mCountDD) mCountDD.innerText = ddCount;
            if (mCountPaper) mCountPaper.innerText = paperCount;
            if (mCountOccupied) mCountOccupied.innerText = filledCount;

            // Populate district filter dropdown
            const distFilter = isModal 
                ? document.getElementById('modalCockpitDistrictFilter') 
                : document.getElementById('visualGridDistrictFilter');
            if (distFilter && distFilter.options.length <= 1) {
                data.districts.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d;
                    opt.textContent = d;
                    distFilter.appendChild(opt);
                });
                if (!isModal) {
                    distFilter.onchange = () => {
                        const selected = distFilter.value;
                        document.querySelectorAll('.district-grid-card').forEach(card => {
                            if (selected === 'ALL' || card.getAttribute('data-district') === selected) {
                                card.classList.remove('hidden');
                            } else {
                                card.classList.add('hidden');
                            }
                        });
                    };
                }
            }

            // Render district sections with responsive user-friendly post cards
            let html = '';
            data.grid.forEach(distGroup => {
                const dName = distGroup.district;
                const ddPosts = distGroup.dd_posts || [];
                const cadrePosts = distGroup.cadre_posts || [];
                const totalInDist = ddPosts.length + cadrePosts.length;

                const renderPostCard = (p) => {
                    let cardBg = "bg-white hover:bg-slate-50";
                    let cardBorder = "border-slate-200 hover:border-slate-400";
                    let idBadgeClass = "bg-slate-700 text-white";
                    let statusBadgeClass = "bg-slate-100 text-slate-700 border border-slate-200";
                    let statusDotClass = "bg-slate-400";
                    let shortStatusText = "Occupied";
                    let borderTopClass = "border-slate-100";
                    let footerTextColor = "text-slate-600";
                    let footerText = `Incumbent: ${p.incumbent_name || 'Serving Officer'}`;
                    let actionTextColor = "text-slate-700";

                    if (p.type === 'DD') {
                        cardBg = "bg-purple-50/60 hover:bg-purple-100/80";
                        cardBorder = "border-purple-300 hover:border-purple-500";
                        idBadgeClass = "bg-purple-700 text-white";
                        statusBadgeClass = "bg-purple-100 text-purple-800 border border-purple-300";
                        statusDotClass = "bg-purple-600";
                        shortStatusText = "DD Level 19 Post";
                        borderTopClass = "border-purple-200/70";
                        footerTextColor = "text-purple-700 font-medium";
                        footerText = "50-Point Roster Promotional Post";
                        actionTextColor = "text-purple-800";
                    }

                    if (p.status_code === 'VACANT_PURE') {
                        cardBg = "bg-emerald-50/70 hover:bg-emerald-100/90";
                        cardBorder = "border-emerald-300 hover:border-emerald-500";
                        idBadgeClass = "bg-emerald-700 text-white";
                        statusBadgeClass = "bg-emerald-100 text-emerald-800 border border-emerald-300";
                        statusDotClass = "bg-emerald-600";
                        shortStatusText = "Pure Vacancy";
                        borderTopClass = "border-emerald-200/80";
                        footerTextColor = "text-emerald-700 font-medium";
                        footerText = "Clear Vacancy • Available Immediately";
                        actionTextColor = "text-emerald-800";
                    } else if (p.status_code === 'VACANT_ON_PAPER') {
                        cardBg = "bg-amber-50/70 hover:bg-amber-100/90";
                        cardBorder = "border-amber-300 hover:border-amber-500";
                        idBadgeClass = "bg-amber-600 text-white";
                        statusBadgeClass = "bg-amber-100 text-amber-800 border border-amber-300";
                        statusDotClass = "bg-amber-500";
                        shortStatusText = "Vacant on Paper";
                        borderTopClass = "border-amber-200/80";
                        footerTextColor = "text-amber-700 font-medium";
                        footerText = `Incumbent ${p.incumbent_name || ''} on SU elsewhere`;
                        actionTextColor = "text-amber-800";
                    } else if (p.status_code === 'ATTENTION_REQUIRED') {
                        cardBg = "bg-rose-50/70 hover:bg-rose-100/90";
                        cardBorder = "border-rose-300 hover:border-rose-500";
                        idBadgeClass = "bg-rose-600 text-white animate-pulse";
                        statusBadgeClass = "bg-rose-100 text-rose-800 border border-rose-300";
                        statusDotClass = "bg-rose-600";
                        shortStatusText = "Action Required";
                        borderTopClass = "border-rose-200/80";
                        footerTextColor = "text-rose-700 font-medium";
                        footerText = "Cascading Replacement Priority";
                        actionTextColor = "text-rose-800";
                    } else if (p.status_code === 'BOARD_SELECTED') {
                        cardBg = "bg-purple-50/70 hover:bg-purple-100/90";
                        cardBorder = "border-purple-300 hover:border-purple-500";
                        idBadgeClass = "bg-purple-600 text-white";
                        statusBadgeClass = "bg-purple-100 text-purple-800 border border-purple-300";
                        statusDotClass = "bg-purple-600";
                        shortStatusText = "Board Selected";
                        borderTopClass = "border-purple-200/80";
                        footerTextColor = "text-purple-700 font-medium";
                        footerText = `Selected: ${p.allotted_to || 'Assigned'}`;
                        actionTextColor = "text-purple-800";
                    } else if (p.status_code === 'OBLITERATED') {
                        cardBg = "bg-slate-100/60 opacity-60";
                        cardBorder = "border-slate-300 line-through";
                        idBadgeClass = "bg-slate-400 text-white";
                        statusBadgeClass = "bg-slate-200 text-slate-600";
                        statusDotClass = "bg-slate-400";
                        shortStatusText = "Obliterated";
                        borderTopClass = "border-slate-200";
                        footerTextColor = "text-slate-500";
                        footerText = "Abolished under Notification 1808";
                        actionTextColor = "text-slate-400";
                    }

                    const clickHandler = isModal && targetHrmsId
                        ? `onclick="window.promptPostAllotment('${p.id}', ${p.raw_id}, '${p.type}', '${p.post_name.replace(/'/g, "\\'")}', '${targetHrmsId}', '${(p.establishment || '').replace(/'/g, "\\'")}', '${(p.district || '').replace(/'/g, "\\'")}', '${shortStatusText}')"`
                        : `onclick="window.showToast('${p.id}: ${p.post_name} — ${p.status_label}', 'info')"`;

                    return `
                        <div ${clickHandler} 
                             class="post-cockpit-card p-3 rounded-lg border text-left cursor-pointer transition shadow-sm hover:shadow-md flex flex-col justify-between gap-2.5 ${cardBg} ${cardBorder}"
                             data-post-id="${p.id}"
                             data-post-type="${p.type}"
                             data-status-code="${p.status_code}"
                             data-district="${dName}"
                             data-search-text="${p.id} ${p.designation} ${p.establishment} ${p.block || ''} ${p.incumbent_name || ''} ${p.status_label}">
                            
                            <div class="flex items-center justify-between gap-1.5">
                                <span class="px-2 py-0.5 rounded font-mono text-[11px] font-bold ${idBadgeClass}">${p.id}</span>
                                <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusBadgeClass} flex items-center gap-1">
                                    <span class="w-1.5 h-1.5 rounded-full ${statusDotClass}"></span>
                                    <span>${shortStatusText}</span>
                                </span>
                            </div>

                            <div class="space-y-1">
                                <div class="font-bold text-slate-900 text-xs leading-snug">${p.designation}</div>
                                <div class="text-[11px] text-slate-600 flex items-center gap-1">
                                    <i data-lucide="building" class="w-3 h-3 text-slate-400 shrink-0"></i>
                                    <span class="truncate" title="${p.establishment}">${p.establishment}</span>
                                </div>
                                ${p.block && p.block !== 'District HQ' ? `
                                    <div class="text-[10px] text-slate-500">
                                        Block: <strong class="text-slate-700">${p.block}</strong>
                                    </div>
                                ` : ''}
                            </div>

                            <div class="pt-2 border-t ${borderTopClass} flex items-center justify-between text-[10px]">
                                <span class="truncate ${footerTextColor}">
                                    ${footerText}
                                </span>
                                <span class="shrink-0 font-bold ${actionTextColor} flex items-center gap-0.5">
                                    <span>Allot</span> &rarr;
                                </span>
                            </div>
                        </div>
                    `;
                };

                html += `
                    <div class="district-grid-card bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3" data-district="${dName}">
                        <div class="flex items-center justify-between border-b border-slate-200 pb-2.5">
                            <div class="font-bold text-slate-800 text-xs flex items-center gap-2">
                                <i data-lucide="map-pin" class="w-4 h-4 text-wbblue-700"></i>
                                <span class="text-sm text-slate-900">${dName}</span>
                                <span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-normal text-[11px]">${totalInDist} posts</span>
                                <span class="district-matching-counter text-[11px] font-semibold text-emerald-700 ml-1"></span>
                            </div>
                            <div class="flex items-center gap-2 text-[11px] text-slate-500 font-mono">
                                <span class="px-1.5 py-0.5 rounded bg-purple-50 text-purple-800 font-semibold border border-purple-200">DD: ${ddPosts.length}</span>
                                <span class="px-1.5 py-0.5 rounded bg-slate-50 text-slate-700 font-semibold border border-slate-200">Cadre: ${cadrePosts.length}</span>
                            </div>
                        </div>

                        ${ddPosts.length > 0 ? `
                            <div class="space-y-1.5">
                                <div class="text-[11px] font-bold text-wbblue-900 uppercase tracking-wider flex items-center gap-1.5">
                                    <i data-lucide="award" class="w-3.5 h-3.5 text-purple-700"></i>
                                    <span>Deputy Director Posts (Pay Level 19)</span>
                                </div>
                                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                                    ${ddPosts.map(renderPostCard).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${cadrePosts.length > 0 ? `
                            <div class="space-y-1.5 ${ddPosts.length > 0 ? 'pt-2 border-t border-slate-100' : ''}">
                                <div class="text-[11px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                                    <i data-lucide="building-2" class="w-3.5 h-3.5 text-slate-500"></i>
                                    <span>Cadre Posts (AD / BLDO / VO)</span>
                                </div>
                                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                                    ${cadrePosts.map(renderPostCard).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;
            });

            container.innerHTML = html;
            lucide.createIcons();

            // Run initial filter state
            if (isModal) {
                window.filterModalCockpitGrid();
            }
        } catch (err) {
            console.error('Failed to render visual grid:', err);
            container.innerHTML = `<div class="py-8 text-center text-rose-500 font-medium">Failed to load posts grid: ${err.message}</div>`;
        }
    };

    // --- SAFE QUICK ALLOTMENT MODAL FROM VISUAL GRID ---
    window.promptPostAllotment = async function(postId, rawId, postType, postName, targetHrmsId, establishment, district, statusLabel) {
        const off = window.activeDossierOfficer;
        if (!off) return;

        const modal = document.getElementById('cockpitAllotModal');
        if (!modal) {
            // Fallback to confirm if modal container not in DOM
            const isSub = confirm(`Allot [${postId}] ${postName} to ${off.officer_name}?\n\nClick OK for SUBSTANTIVE MAIN, or Cancel to abort.`);
            if (!isSub) return;
            return;
        }

        // Populate modal data
        document.getElementById('cockpitOfficerName').innerText = off.officer_name;
        document.getElementById('cockpitOfficerHrms').innerText = targetHrmsId;
        document.getElementById('cockpitTargetPostId').innerText = postId;
        document.getElementById('cockpitTargetPostName').innerText = postName;
        document.getElementById('cockpitTargetLocation').innerText = `${establishment ? establishment + ', ' : ''}${district || ''}`;
        
        const statusBadge = document.getElementById('cockpitTargetStatusBadge');
        if (statusBadge) {
            statusBadge.innerText = statusLabel || 'Cadre Post';
        }

        modal.classList.remove('hidden');

        const executeAllotment = async (isSubstantive) => {
            modal.classList.add('hidden');
            const subId = isSubstantive ? rawId : (off.latest_allotment ? off.latest_allotment.substantive_post_id : 1);
            const suId = !isSubstantive ? rawId : null;

            try {
                const res = await fetch('/api/simulation/allot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: 'CURRENT_SESSION',
                        officer_hrms: targetHrmsId,
                        substantive_post_id: subId,
                        su_post_id: suId,
                        reason: isSubstantive ? "Substantive Main Allotment via Allocation Cockpit" : "Service Utilization Allotment via Allocation Cockpit",
                        officer_type: "roster"
                    })
                });
                const data = await res.json();
                if (data.success) {
                    window.showToast(`Successfully allotted [${postId}] to ${off.officer_name}!`, 'success');
                    window.openOfficerDossier(targetHrmsId);
                    if (typeof loadRoster === 'function') loadRoster();
                    if (typeof loadSimulationHistory === 'function') loadSimulationHistory();
                } else {
                    window.showToast(data.error || 'Allotment failed', 'error');
                }
            } catch (e) {
                console.error(e);
                window.showToast('Network error during allotment', 'error');
            }
        };

        // Bind button actions
        document.getElementById('btnCockpitSubstantive').onclick = () => executeAllotment(true);
        document.getElementById('btnCockpitSU').onclick = () => executeAllotment(false);
        document.getElementById('btnCancelCockpitAllot').onclick = () => modal.classList.add('hidden');
        document.getElementById('btnCloseCockpitAllotModal').onclick = () => modal.classList.add('hidden');
    };

    document.getElementById('btnCloseDossierModal')?.addEventListener('click', () => {
        document.getElementById('officerDossierModal').classList.add('hidden');
    });
    document.getElementById('btnCloseDossierFooter')?.addEventListener('click', () => {
        document.getElementById('officerDossierModal').classList.add('hidden');
    });

    // --- AI ALLOTMENT RECOMMENDATION MODAL LOGIC ---
    let currentAIRecommendation = null;

    window.openAIAllotModal = async function(hrmsId, source = 'roster') {
        if (hrmsId === '1992005664') {
            alert('Administrative Protection: Dr. Nikhil Kumar Shit is the Director of AH&VS (Level-22) and cannot be replaced, displaced, or transferred.');
            return;
        }
        const modal = document.getElementById('aiAllotModal');
        const container = document.getElementById('aiAllotContent');
        const subtitle = document.getElementById('aiAllotSubtitle');

        container.innerHTML = `<div class="py-12 text-center text-slate-400">Analyzing officer profile, stated preferences, area tenure norms and available posts...</div>`;
        modal.classList.remove('hidden');

        try {
            const res = await fetch(`/api/simulation/recommend-allotment?officer_hrms=${encodeURIComponent(hrmsId)}&session_id=CURRENT_SESSION`);
            if (!res.ok) throw new Error('AI recommender failed to evaluate post.');
            const r = await res.json();
            currentAIRecommendation = r;

            subtitle.innerText = `Recommendation for ${r.officer_name} (${r.officer_hrms}) | Score: ${r.score} pts`;

            const reasonsHtml = r.match_reasons && r.match_reasons.length > 0
                ? r.match_reasons.map(m => `<span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold text-[11px]">${m}</span>`).join(' ')
                : `<span class="text-slate-500">Standard optimal cadre vacancy assigned</span>`;

            container.innerHTML = `
                <!-- Officer & Score Header -->
                <div class="p-3.5 rounded-lg bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 flex items-center justify-between">
                    <div>
                        <div class="text-[10px] text-amber-800 uppercase tracking-wider font-semibold">Target Officer</div>
                        <div class="text-sm font-bold text-slate-900">${r.officer_name}</div>
                        <div class="text-[11px] text-slate-600">Present: ${r.present_posting}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-black text-orange-600">${r.score}</div>
                        <div class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">AI Optimization Score</div>
                    </div>
                </div>

                <!-- Recommended Substantive Post -->
                <div class="p-3.5 rounded-lg bg-white border border-slate-300 shadow-sm space-y-1.5">
                    <div class="text-[10px] font-bold text-wbblue-800 uppercase tracking-wider flex items-center gap-1.5">
                        <i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-600"></i>
                        <span>Recommended Substantive Post (Sanctioned Cadre)</span>
                    </div>
                    <div class="text-sm font-bold text-slate-900">${r.substantive_post_name}</div>
                    <div class="text-[11px] text-slate-500">Pay Level: Level 19 (Rs. 95,100 - Rs. 1,48,000) under WBS (ROPA) 2019</div>
                </div>

                <!-- Recommended SU Post (if applicable) -->
                ${r.su_post_name ? `
                    <div class="p-3 rounded-lg bg-teal-50 border border-teal-200 space-y-1">
                        <div class="text-[10px] font-bold text-teal-800 uppercase tracking-wider flex items-center gap-1.5">
                            <i data-lucide="arrow-right-circle" class="w-4 h-4 text-teal-600"></i>
                            <span>Recommended Service Utilization (SU) Post</span>
                        </div>
                        <div class="text-xs font-bold text-teal-950">${r.su_post_name}</div>
                    </div>
                ` : `
                    <div class="p-2.5 rounded bg-slate-50 border border-slate-200 text-slate-600 text-xs flex items-center gap-2">
                        <i data-lucide="info" class="w-3.5 h-3.5 text-slate-400"></i>
                        <span>Direct Substantive Deployment — No Service Utilization (SU) required.</span>
                    </div>
                `}

                <!-- Factors & Merits -->
                <div class="space-y-1.5">
                    <div class="text-[10px] font-bold text-slate-700 uppercase tracking-wider">Optimized Statutory Criteria</div>
                    <div class="flex flex-wrap gap-1.5">
                        ${reasonsHtml}
                    </div>
                </div>

                <!-- Statutory Brief Accordion -->
                <div class="p-3 rounded-lg bg-slate-50 border border-slate-200 text-[11px] text-slate-700 space-y-1">
                    <div class="font-bold text-slate-800">Administrative Statutory Justification:</div>
                    <div class="whitespace-pre-line font-mono text-[10px] bg-white p-2.5 rounded border border-slate-300 max-h-36 overflow-y-auto leading-relaxed">
${r.statutory_justification}
                    </div>
                </div>
            `;
            lucide.createIcons();
        } catch (err) {
            console.error('AI allotment error:', err);
            container.innerHTML = `<div class="py-12 text-center text-rose-500 font-medium">Failed to generate AI recommendation: ${err.message}</div>`;
        }
    };

    document.getElementById('btnCloseAIAllotModal')?.addEventListener('click', () => {
        document.getElementById('aiAllotModal').classList.add('hidden');
    });
    document.getElementById('btnCloseAIAllotFooter')?.addEventListener('click', () => {
        document.getElementById('aiAllotModal').classList.add('hidden');
    });

    document.getElementById('btnConfirmAIAllot')?.addEventListener('click', async () => {
        if (!currentAIRecommendation || !currentAIRecommendation.substantive_post_id) {
            alert('No valid recommendation to execute.');
            return;
        }
        const rec = currentAIRecommendation;
        try {
            const res = await fetch('/api/simulation/allot', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: 'CURRENT_SESSION',
                    officer_hrms: rec.officer_hrms,
                    substantive_post_id: rec.substantive_post_id,
                    su_post_id: rec.su_post_id,
                    reason: `AI Intelligent Allotment (Score: ${rec.score} pts)`,
                    officer_type: rec.candidate_type || 'roster'
                })
            });
            const data = await res.json();
            if (!data.success) throw new Error(data.error || 'Allotment execution failed.');

            document.getElementById('aiAllotModal').classList.add('hidden');
            alert(`✅ AI Allotment Executed Successfully!\n\nOfficer: ${rec.officer_name}\nSubstantive Post: ${rec.substantive_post_name}\n${rec.su_post_name ? 'SU Post: ' + rec.su_post_name : ''}`);

            await initOverview();
            await loadRoster();
            await loadObliterated();
            await loadCadre();
            await loadDisplacedPool();
            await loadSimulationHistory();
        } catch (err) {
            console.error('Execution error:', err);
            alert('Allotment failed: ' + err.message);
        }
    });

    // ==================== TAB 8: MASTER CADRE DIRECTORY ====================
    let masterDirState = {
        query: '',
        district: 'ALL',
        category: 'all',
        page: 1,
        pageSize: 50,
        totalPages: 1
    };

    async function loadMasterDirectory(resetPage = false) {
        if (resetPage) masterDirState.page = 1;
        const tbody = document.getElementById('masterDirectoryTableBody');
        const cardsEl = document.getElementById('masterDirectoryMobileCards');
        if (!tbody && !cardsEl) return;

        if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-slate-400">Loading master directory...</td></tr>';
        if (cardsEl) cardsEl.innerHTML = '<div class="py-8 text-center text-slate-400 text-xs">Loading master directory...</div>';

        try {
            const params = new URLSearchParams({
                query: masterDirState.query,
                district: masterDirState.district,
                category: masterDirState.category,
                page: masterDirState.page,
                page_size: masterDirState.pageSize
            });
            const res = await fetch(`/api/employees/master?${params.toString()}`);
            const data = await res.json();

            masterDirState.totalPages = data.total_pages || 1;

            // Update badge & pagination display
            const badgeCount = document.getElementById('badgeMasterCount');
            if (badgeCount && data.kpis) badgeCount.innerText = data.kpis.total.toLocaleString();

            const badgeActive = document.getElementById('masterActiveCountBadge');
            if (badgeActive && data.kpis) badgeActive.innerText = `${data.kpis.in_service.toLocaleString()} Active In-Service`;

            const infoEl = document.getElementById('employeePaginationInfo');
            if (infoEl) {
                const start = data.total === 0 ? 0 : (masterDirState.page - 1) * masterDirState.pageSize + 1;
                const end = Math.min(masterDirState.page * masterDirState.pageSize, data.total);
                infoEl.innerText = `Showing ${start} to ${end} of ${data.total.toLocaleString()} officers`;
            }

            const pageEl = document.getElementById('employeeCurrentPageDisplay');
            if (pageEl) pageEl.innerText = `Page ${masterDirState.page} of ${masterDirState.totalPages}`;

            const prevBtn = document.getElementById('btnEmployeePrev');
            if (prevBtn) prevBtn.disabled = masterDirState.page <= 1;

            const nextBtn = document.getElementById('btnEmployeeNext');
            if (nextBtn) nextBtn.disabled = masterDirState.page >= masterDirState.totalPages;

            if (!data.employees || data.employees.length === 0) {
                if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-slate-400">No officers found matching search criteria.</td></tr>';
                if (cardsEl) cardsEl.innerHTML = '<div class="py-12 text-center text-slate-400 text-xs">No officers found matching search criteria.</div>';
                return;
            }

            if (tbody) {
                tbody.innerHTML = data.employees.map((emp, idx) => {
                    const globalIdx = (masterDirState.page - 1) * masterDirState.pageSize + idx + 1;
                    let badges = '';
                    if (emp.is_hq_deployed) {
                        badges += `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-300 text-[10px] font-bold">🏛️ HQ Deployed</span> `;
                    }
                    if (emp.is_50pt_candidate) {
                        badges += `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-300 text-[10px] font-bold">🎯 50-Pt Roster</span> `;
                    }
                    if (emp.is_unsanctioned_post) {
                        badges += `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold">⚠️ Excess Post</span> `;
                    }

                    return `
                        <tr class="hover:bg-slate-50 transition border-b border-slate-100">
                            <td class="py-2.5 px-3 text-center text-slate-400 font-mono text-[11px]">${globalIdx}</td>
                            <td class="py-2.5 px-3 font-mono font-bold text-slate-700">${emp.hrms_id || '—'}</td>
                            <td class="py-2.5 px-4">
                                <div class="font-bold text-wbblue-900 hover:text-wbblue-600 hover:underline cursor-pointer flex items-center gap-1.5" onclick="openOfficerDossier('${emp.hrms_id}')" title="Click to view full personnel dossier">
                                    <span>${emp.officer_name}</span>
                                </div>
                                <div class="mt-1 flex flex-wrap gap-1">${badges}</div>
                            </td>
                            <td class="py-2.5 px-4">
                                <div class="font-semibold text-slate-800">${emp.designation || 'Officer'}</div>
                                <div class="text-[11px] text-slate-500">${emp.establishment || emp.present_posting || '—'}</div>
                            </td>
                            <td class="py-2.5 px-3">
                                <span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium text-[11px] border border-slate-200">
                                    ${emp.district || '—'}
                                </span>
                            </td>
                            <td class="py-2.5 px-3 font-mono text-slate-600">${emp.dor || '—'}</td>
                            <td class="py-2.5 px-3 text-right">
                                <button onclick="openOfficerDossier('${emp.hrms_id}')" class="px-2.5 py-1 text-[11px] font-semibold rounded bg-wbblue-50 text-wbblue-700 hover:bg-wbblue-100 border border-wbblue-200 transition">
                                    View Dossier
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            }

            if (cardsEl) {
                cardsEl.innerHTML = data.employees.map((emp, idx) => {
                    const globalIdx = (masterDirState.page - 1) * masterDirState.pageSize + idx + 1;
                    const initials = getMonogram(emp.officer_name);
                    let badges = '';
                    if (emp.is_hq_deployed) {
                        badges += `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-300 text-[10px] font-bold">🏛️ HQ Deployed</span> `;
                    }
                    if (emp.is_50pt_candidate) {
                        badges += `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-300 text-[10px] font-bold">🎯 50-Pt Roster</span> `;
                    }
                    if (emp.is_unsanctioned_post) {
                        badges += `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300 text-[10px] font-bold">⚠️ Excess Post</span> `;
                    }

                    return `
                        <div class="rounded-2xl bg-white border border-slate-200/80 shadow-[0_2px_12px_rgba(15,23,42,0.04)] mobile-card-interactive p-4 space-y-3">
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex items-start gap-3 min-w-0">
                                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-wbblue-700 to-indigo-800 text-white font-bold flex items-center justify-center text-xs shadow-xs shrink-0 tracking-tight">
                                        ${initials}
                                    </div>
                                    <div class="min-w-0">
                                        <div class="flex flex-wrap items-center gap-1.5 mb-1">
                                            <span class="px-2 py-0.5 rounded-md bg-slate-900 text-white font-mono text-[9px] font-bold">#${globalIdx}</span>
                                            <span class="font-mono text-[10px] font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">HRMS: ${emp.hrms_id || '—'}</span>
                                        </div>
                                        <div class="font-extrabold text-sm text-slate-900 truncate cursor-pointer hover:text-wbblue-700" onclick="openOfficerDossier('${emp.hrms_id}')" title="Click to view dossier">
                                            ${emp.officer_name}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            ${badges ? `<div class="flex flex-wrap gap-1">${badges}</div>` : ''}

                            <div class="p-2.5 rounded-xl bg-slate-50/90 border border-slate-200/80 text-xs space-y-1">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                                    <i data-lucide="briefcase" class="w-3 h-3 text-slate-400"></i>
                                    <span>Designation & Posting</span>
                                </div>
                                <div class="font-bold text-slate-900 leading-snug">${emp.designation || 'Officer'}</div>
                                <div class="text-[11px] text-slate-600 font-medium leading-snug">${emp.establishment || emp.present_posting || '—'}</div>
                                <div class="flex items-center justify-between text-[11px] pt-1.5 mt-1 border-t border-slate-200/70">
                                    <span class="px-2 py-0.5 rounded-md bg-slate-200/80 text-slate-700 font-bold text-[10px]">${emp.district || 'District N/A'}</span>
                                    <span class="font-mono text-slate-600 text-[11px]">DOR: <strong>${emp.dor || '—'}</strong></span>
                                </div>
                            </div>

                            <div class="pt-1 border-t border-slate-100">
                                <button onclick="openOfficerDossier('${emp.hrms_id}')" class="w-full py-2 px-3 rounded-xl bg-wbblue-50 hover:bg-wbblue-100 text-wbblue-800 border border-wbblue-200 text-xs font-bold flex items-center justify-center gap-1.5 btn-touch touch-target">
                                    <i data-lucide="user" class="w-3.5 h-3.5 text-wbblue-600"></i>
                                    <span>View Personnel Dossier</span>
                                </button>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            if (window.lucide) lucide.createIcons();

        } catch (err) {
            console.error('Error loading master directory:', err);
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-rose-500 font-semibold">Failed to load master directory: ${err.message}</td></tr>`;
            if (cardsEl) cardsEl.innerHTML = `<div class="py-12 text-center text-rose-500 text-xs">Failed to load master directory: ${err.message}</div>`;
        }
    }

    // Bind Master Directory controls
    const searchInput = document.getElementById('employeeSearchInput');
    let searchDebounce = null;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(() => {
                masterDirState.query = e.target.value;
                loadMasterDirectory(true);
            }, 300);
        });
    }

    const distSelect = document.getElementById('employeeDistrictFilter');
    if (distSelect) {
        distSelect.addEventListener('change', (e) => {
            masterDirState.district = e.target.value;
            loadMasterDirectory(true);
        });
    }

    const catChips = document.querySelectorAll('#employeeCategoryChips .emp-cat-btn');
    catChips.forEach(btn => {
        btn.addEventListener('click', () => {
            catChips.forEach(b => {
                b.classList.remove('bg-wbblue-800', 'text-white', 'shadow-sm');
                b.classList.add('bg-white', 'border', 'border-slate-300', 'text-slate-700');
            });
            btn.classList.add('bg-wbblue-800', 'text-white', 'shadow-sm');
            btn.classList.remove('bg-white', 'border', 'border-slate-300', 'text-slate-700');

            masterDirState.category = btn.getAttribute('data-cat');
            loadMasterDirectory(true);
        });
    });

    const prevBtn = document.getElementById('btnEmployeePrev');
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (masterDirState.page > 1) {
                masterDirState.page--;
                loadMasterDirectory(false);
            }
        });
    }

    const nextBtn = document.getElementById('btnEmployeeNext');
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (masterDirState.page < masterDirState.totalPages) {
                masterDirState.page++;
                loadMasterDirectory(false);
            }
        });
    }

    // Populate employee district dropdown
    async function initEmployeeDistricts() {
        try {
            const res = await fetch('/api/districts');
            const data = await res.json();
            const sel = document.getElementById('employeeDistrictFilter');
            if (sel && data.districts) {
                data.districts.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d;
                    opt.textContent = d;
                    sel.appendChild(opt);
                });
            }
        } catch (e) {
            console.error('Failed to load employee districts', e);
        }
    }
    initEmployeeDistricts();

    window.loadMasterDirectory = loadMasterDirectory;

    // --- ARD DEPARTMENT ORGANOGRAM COMPONENT ---
// --- ORGANOGRAM COMPONENT FOR ARD POSTING BOARD ---

(function() {
    const ARD_ORGANOGRAM_DATA = [
        {
            id: "tier-1",
            tierNumber: "Tier 1",
            tierName: "Departmental Secretariat & Governance",
            levelBadge: "State Apex Policy",
            badgeColor: "bg-amber-500 text-slate-950",
            statutoryRef: "WBSCS Rules • WBSR Part I & II",
            description: "Department of Animal Resources Development, Government of West Bengal. Policy formulation, budget appropriation, legislative governance, and cadre control.",
            postsCount: "State Apex",
            groups: ["secretariat"],
            nodes: [
                {
                    id: "sec-mic",
                    title: "Minister-in-Charge (MIC)",
                    office: "ARD Department, Mantralaya / Nabanna",
                    payLevel: "Cabinet Minister",
                    cadre: "Constitutional Executive",
                    posts: "1",
                    headOfOffice: false,
                    hooNote: "Apex Political Authority",
                    superior: "Hon'ble Chief Minister & Cabinet",
                    subordinates: "Additional Chief Secretary / Principal Secretary, ARD Department",
                    sarReporting: "Cabinet & State Legislature",
                    functions: "Departmental policy approvals, Cabinet memoranda, legislative bills, state livestock policy direction, inter-departmental allocations.",
                    legalBasis: "Rules of Business, Government of West Bengal",
                    tags: ["Secretariat", "Cabinet", "Policy"]
                },
                {
                    id: "sec-acs",
                    title: "Additional Chief Secretary / Principal Secretary",
                    office: "ARD Department, Mantralaya / Nabanna & Prani Sampad Bhawan",
                    payLevel: "Apex Scale (Level 17 / IAS)",
                    cadre: "Indian Administrative Service (IAS)",
                    posts: "1",
                    headOfOffice: true,
                    hooNote: "Chief Executive & Secretary to Govt.",
                    superior: "Minister-in-Charge (MIC) & Chief Secretary, GoWB",
                    subordinates: "Special Secretary, Joint Secretaries, DAH&VS (Level 22), Directorate Heads",
                    sarReporting: "Accepting Authority for Additional Directors & Joint Directors; Reports to Chief Secretary",
                    functions: "Administrative command of ARD Department, sanction of capital projects, financial concurrence, cadre notifications, DPC presiding authority.",
                    legalBasis: "WBSR & West Bengal Secretariat Rules",
                    tags: ["Secretariat", "IAS", "Executive Head"]
                },
                {
                    id: "sec-spec-sec",
                    title: "Special Secretary, ARD Department",
                    office: "Secretariat Wing, Prani Sampad Bhawan",
                    payLevel: "Supertime Scale (IAS / Senior WBCS)",
                    cadre: "IAS / Senior WBCS (Exec)",
                    posts: "1",
                    headOfOffice: false,
                    hooNote: "Secretariat Senior Executive",
                    superior: "Additional Chief Secretary / Principal Secretary",
                    subordinates: "Joint Secretaries, Deputy Secretaries, Assistant Secretaries",
                    sarReporting: "Reviewing Officer for Joint Directors & Addl. Directors; Reports to ACS",
                    functions: "Cadre management, Departmental Promotion Committees (DPC), vigilance and disciplinary proceedings, service rule amendments.",
                    legalBasis: "WBSR & WBAH&VS Reconstitution Rules 2025",
                    tags: ["Secretariat", "Cadre Control", "DPC"]
                },
                {
                    id: "sec-joint-sec",
                    title: "Joint Secretaries / Deputy Secretaries",
                    office: "ARD Secretariat Wings (Administration, Budget, Dairy, Planning)",
                    payLevel: "Level 19 - 21 (WBCS Exec / WBSS)",
                    cadre: "WBCS (Exec) & West Bengal Secretariat Service",
                    posts: "4 Wings",
                    headOfOffice: false,
                    hooNote: "Secretariat Branch Heads",
                    superior: "Special Secretary & ACS",
                    subordinates: "Assistant Secretaries, Section Officers, Registrars",
                    sarReporting: "Reports to Special Secretary; Reviewing for Section Officers",
                    functions: "Administrative sanctions, budget allocations, Plan expenditure monitoring, legislative questions, audit reconciliation.",
                    legalBasis: "West Bengal Secretariat Manual of Office Procedure",
                    tags: ["Secretariat", "Administration", "Budget"]
                }
            ]
        },
        {
            id: "tier-2",
            tierNumber: "Tier 2",
            tierName: "Directorate Apex Command",
            levelBadge: "Pay Level 22 (Apex Cadre)",
            badgeColor: "bg-blue-600 text-white",
            statutoryRef: "Notif. 1808-AR&AH & Notif. 1809-AR&AH dt. 18.06.2025",
            description: "Directorate of Animal Health & Veterinary Services (DAH&VS), Prani Sampad Bhawan, Salt Lake. Technical leadership, statewide veterinary services, and epidemic defense.",
            postsCount: "1 Post",
            groups: ["secretariat"],
            nodes: [
                {
                    id: "dir-dahvs",
                    title: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    office: "Directorate Headquarters, Prani Sampad Bhawan, LB-2, Sector-III, Salt Lake, Kolkata-700106",
                    payLevel: "Level 22 (ROPA 2019)",
                    cadre: "Apex Head of WBAH&VS Cadre",
                    posts: "1 Post (Incumbent: Dr. Nikhil Kumar Shit)",
                    headOfOffice: true,
                    hooNote: "Principal Head of Department / Head of Directorate",
                    superior: "Additional Chief Secretary / Principal Secretary, ARD Department",
                    subordinates: "8+1 Additional Directors, 23 Joint Directors (Districts), IAH&VB, Central Mega-Farms",
                    sarReporting: "Reporting Officer for Addl. Directors & JDs; Accepting Authority for DDs, ADs, BLDOs & VOs",
                    functions: "Overall technical and administrative command of the 1,794 reconstituted cadre posts. Implementation of state disease control, livestock breeding programs, statutory licensing, animal welfare, and cadre discipline.",
                    legalBasis: "Notification No. 1808-AR&AH/3A-08/23 dt. 18.06.2025 & WBAH&VS Reconstitution Rules 2025",
                    tags: ["Apex Command", "Pay Level 22", "Directorate Head", "Protected Post"]
                },
                {
                    id: "dir-hq-cells",
                    title: "Directorate Core Headquarters Staff Cells",
                    office: "Prani Sampad Bhawan, Salt Lake, Kolkata",
                    payLevel: "Pay Level 19 - 21 (DD / JD / AD Rank)",
                    cadre: "WBAH&VS Directorate Officers & Ministerial Staff",
                    posts: "5 Functional Cells",
                    headOfOffice: false,
                    hooNote: "Directorate Headquarters Cells",
                    superior: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    subordinates: "Section Officers, Statistical Officers, Technical Assistants",
                    sarReporting: "Reports to DAH&VS",
                    functions: "1. Law & Disciplinary Proceeding Cell\n2. Budget, Accounts & Audit Cell\n3. Planning, MIS, IT & Statistical Cell\n4. State Disease Surveillance & Rapid Response Cell\n5. Central Stores, Logistics & Medicine Procurement Cell",
                    legalBasis: "Directorate Establishment Manual & WB Financial Rules",
                    tags: ["HQ Cells", "Directorate", "Monitoring"]
                }
            ]
        },
        {
            id: "tier-3",
            tierNumber: "Tier 3",
            tierName: "Functional & Zonal Directorate Wings",
            levelBadge: "Pay Level 21",
            badgeColor: "bg-purple-600 text-white",
            statutoryRef: "Notif. 1809-AR&AH Schedule • Order No. 51-AR&AH dt. 07.01.2026",
            description: "8+1 Sanctioned Additional Director Posts overseeing state technical programs, biological research & vaccine manufacturing, and the 4 administrative zonal divisions.",
            postsCount: "8 + 1 Posts",
            groups: ["zones", "iahvb"],
            nodes: [
                {
                    id: "ad-iahvb",
                    title: "Additional Director, ARD (IAH&VB & RDDL, Belgachia)",
                    office: "Institute of Animal Health & Veterinary Biologicals, 37, Kshudiram Bose Sarani, Belgachia, Kolkata-700037",
                    payLevel: "Level 21 (ROPA 2019)",
                    cadre: "WBAH&VS Senior Directorate Cadre",
                    posts: "1 Post",
                    headOfOffice: true,
                    hooNote: "Declared Head of Office vide Order No. 51-AR&AH dt. 07.01.2026",
                    superior: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    subordinates: "Joint Director (IAH&VB), Joint Director (RDDL), Research Officers, DDs & ADs (Virology, Bacteriology, Parasitology, Pathology)",
                    sarReporting: "Reports to DAH&VS; Reviewing for JDs & DDs of IAH&VB; Accepting for IAH&VB Technical Staff",
                    functions: "Autonomous technical and financial head of state vaccine production (Anthrax, HS, BQ, Rabies, Ranikhet), animal disease diagnosis, epidemiology reference lab, quality testing, and RDDL network supervision.",
                    legalBasis: "Order No. 51-AR&AH dt. 07.01.2026 & Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Order 51", "IAH&VB", "Head of Office", "Vaccine Biologicals"]
                },
                {
                    id: "ad-ah",
                    title: "Additional Director, ARD (Animal Health & Epidemic Control)",
                    office: "Directorate HQ, Prani Sampad Bhawan, Salt Lake",
                    payLevel: "Level 21 (ROPA 2019)",
                    cadre: "WBAH&VS Senior Directorate Cadre",
                    posts: "1 Post",
                    headOfOffice: false,
                    hooNote: "Statewide Technical Wing Head",
                    superior: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    subordinates: "Joint Directors of ARD (District AH wings), State Polyclinic coordinators",
                    sarReporting: "Reports to DAH&VS; Reviewing for technical officers in AH wing",
                    functions: "Statewide disease surveillance, mass immunization campaigns (FMD, PPR, Brucellosis), disaster contingency, veterinary hospital clinical standards, veterinary medicines & equipment procurement.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Animal Health", "Epidemic Control", "Clinical Governance"]
                },
                {
                    id: "ad-ap",
                    title: "Additional Director, ARD (Animal Production & Breeding)",
                    office: "Directorate HQ, Prani Sampad Bhawan, Salt Lake",
                    payLevel: "Level 21 (ROPA 2019)",
                    cadre: "WBAH&VS Senior Directorate Cadre",
                    posts: "1 Post",
                    headOfOffice: false,
                    hooNote: "Statewide Production Wing Head",
                    superior: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    subordinates: "Joint Directors (Mega-Farms), DDs (Cattle Production & AI), Fodder specialists",
                    sarReporting: "Reports to DAH&VS; Reviewing for Farm JDs and Cattle Production DDs",
                    functions: "State breeding policy, Artificial Insemination (AI) coverage expansion, fodder seed production, conservation of indigenous breeds (Bengal Goat, Garole Sheep, Siri Cattle), mega-farm production monitoring.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Animal Production", "Breeding", "Mega-Farms"]
                },
                {
                    id: "ad-nb",
                    title: "Additional Director, ARD (North Bengal Setup, Siliguri)",
                    office: "North Bengal Development Department Complex / Siliguri Directorate Wing",
                    payLevel: "Level 21 (ROPA 2019)",
                    cadre: "WBAH&VS Senior Directorate Cadre",
                    posts: "1 Post",
                    headOfOffice: true,
                    hooNote: "Zonal Head of Office for North Bengal",
                    superior: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    subordinates: "8 District Joint Directors: Darjeeling, Kalimpong, Jalpaiguri, Alipurduar, Cooch Behar, Uttar Dinajpur, Dakshin Dinajpur, Malda",
                    sarReporting: "Reports to DAH&VS; Reviewing Officer for North Bengal Joint Directors",
                    functions: "Regional coordination of animal health, livestock development, hill cattle breeding, disease prevention in tea garden belts and international border zones of North Bengal.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["North Bengal", "Siliguri", "Zonal Head", "8 Districts"]
                },
                {
                    id: "ad-zones",
                    title: "Additional Directors, ARD (Zonal Divisions: Zone I, II, III, IV)",
                    office: "Zonal Offices: Presidency (Kolkata), Burdwan, Medinipur, Malda",
                    payLevel: "Level 21 (ROPA 2019)",
                    cadre: "WBAH&VS Senior Directorate Cadre",
                    posts: "4 Zonal Posts",
                    headOfOffice: true,
                    hooNote: "Divisional Zonal Heads",
                    superior: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    subordinates: "District Joint Directors within respective Administrative Division",
                    sarReporting: "Reports to DAH&VS; Reviewing Officer for respective District Joint Directors",
                    functions: "Divisional supervision of district performance, dispute resolution, inter-district resource balancing, disaster mobilization, and compliance monitoring.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Divisional Zones", "Presidency", "Burdwan", "Medinipur", "Malda"]
                }
            ]
        },
        {
            id: "tier-4",
            tierNumber: "Tier 4",
            tierName: "District Directorate Heads & Central Mega-Farms",
            levelBadge: "Pay Level 20",
            badgeColor: "bg-indigo-600 text-white",
            statutoryRef: "Order No. 575-AR&AH/3A-12/2025 dt. 27.02.2026",
            description: "23 District Joint Directors declared statutory Heads of Office with financial powers, along with Joint Directors heading Central State Mega-Farms & Regional Diagnostic Labs.",
            postsCount: "23 Districts + Farms",
            groups: ["districts", "farms", "iahvb"],
            nodes: [
                {
                    id: "jd-districts",
                    title: "Joint Directors of ARD (District Heads)",
                    office: "Offices of the Joint Director of ARD across 23 Districts of West Bengal",
                    payLevel: "Level 20 (ROPA 2019)",
                    cadre: "WBAH&VS Senior Administrative Cadre",
                    posts: "23 District Posts + Siliguri Sub-Division",
                    headOfOffice: true,
                    hooNote: "Declared Head of Office with DDO & Financial Powers vide Order No. 575-AR&AH dt. 27.02.2026",
                    superior: "Respective Zonal Addl. Director & Director, AH&VS",
                    subordinates: "5 District Deputy Directors, Project Officer, 26 Polyclinic DDs, 344 BLDOs",
                    sarReporting: "Reporting Officer for District DDs & PO; Reviewing Officer for BLDOs; Reports to Zonal Addl. Director",
                    functions: "Statutory Head of Office for all ARD establishments in the district. Approves district expenditure, supervises 344 blocks, chairs District Animal Welfare Committees, liaises with District Magistrate (DM) and Zilla Parishad.",
                    legalBasis: "Order No. 575-AR&AH/3A-12/2025 dt. 27.02.2026 & WB Financial Rules",
                    tags: ["Order 575", "Head of Office", "District Head", "Financial DDO"]
                },
                {
                    id: "jd-hclf",
                    title: "Joint Director, Haringhata Central Livestock Farm (HCLF)",
                    office: "Haringhata Central Livestock Farm Complex, Mohanpur, Nadia-741246",
                    payLevel: "Level 20 (ROPA 2019)",
                    cadre: "WBAH&VS Special Administrative Cadre",
                    posts: "41 Sanctioned Cadre Posts (Farm Setup)",
                    headOfOffice: true,
                    hooNote: "Declared Head of Office for HCLF Estate",
                    superior: "Additional Director (Animal Production) & DAH&VS",
                    subordinates: "Deputy Directors (Farms, Dairy, Feed Mill), Assistant Directors, Veterinary Officers",
                    sarReporting: "Reports to Addl. Director (AP); Reviewing for HCLF Officers",
                    functions: "Executive management of West Bengal's largest livestock breeding estate (2,500+ acres). Operates high-yielding dairy herds, central feed manufacturing mill, elite germplasm bank, and certified fodder seed multiplication plots.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025 & Order No. 575-AR&AH",
                    tags: ["HCLF Haringhata", "Mega-Farm", "41 Cadre Posts", "Germplasm"]
                },
                {
                    id: "jd-other-farms",
                    title: "Joint Directors / In-Charge, State Mega-Farms (Kalyani & Salboni)",
                    office: "State Livestock Farm (SLF) Kalyani & Central Sheep & AH Farm (CSAHF) Salboni",
                    payLevel: "Level 20 / Senior DD (Level 19)",
                    cadre: "WBAH&VS Institutional Cadre",
                    posts: "SLF Kalyani (12 posts) • CSAHF Salboni (14 posts)",
                    headOfOffice: true,
                    hooNote: "Institutional Head of Office",
                    superior: "Additional Director (AP) & DAH&VS",
                    subordinates: "Deputy Directors, Farm Managers, Veterinary Officers",
                    sarReporting: "Reports to Addl. Director (AP); Reviewing for Farm Staff",
                    functions: "SLF Kalyani: Cross-bred cattle elite breeding, fodder seed certification. CSAHF Salboni: Conservation of Garole sheep and Bengal black goat seedstock, pasture management in Jangalmahal.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["SLF Kalyani", "CSAHF Salboni", "Farms", "Conservation"]
                },
                {
                    id: "jd-rddl",
                    title: "Joint Directors / Heads, Regional Disease Diagnostic Labs (RDDLs)",
                    office: "5 RDDLs: Belgachia Central, Jalpaiguri, Bethuadahari, Garbeta, Bardhaman",
                    payLevel: "Level 20 / Senior DD (Level 19)",
                    cadre: "WBAH&VS Specialist Diagnostic Cadre",
                    posts: "5 Regional Diagnostic Hubs",
                    headOfOffice: true,
                    hooNote: "Regional Laboratory Head of Office",
                    superior: "Additional Director (IAH&VB) & DAH&VS",
                    subordinates: "Specialist Pathologists, Virologists, Microbiologists, Lab Technicians",
                    sarReporting: "Reports to Addl. Director (IAH&VB)",
                    functions: "Regional confirmatory testing for Anthrax, Brucella, Avian Influenza, PPR, ASF. Serological surveillance, sample banking, and epidemic outbreak investigations.",
                    legalBasis: "Order No. 51-AR&AH dt. 07.01.2026 & Central DAH&D Guidelines",
                    tags: ["RDDL", "IAH&VB", "Disease Diagnostics", "Biosafety"]
                }
            ]
        },
        {
            id: "tier-5",
            tierNumber: "Tier 5",
            tierName: "Operational Specialists, Polyclinics & Breeding Stations",
            levelBadge: "Pay Level 19",
            badgeColor: "bg-emerald-600 text-white",
            statutoryRef: "Notif. 1808-AR&AH • 50-Point Roster Schedule (242 Posts)",
            description: "242 Sanctioned Deputy Director posts under statutory 50-point roster. 5 district functional wings, 26 State Veterinary Polyclinics (130 specialist posts), 8 poultry breeding stations, and training institutes.",
            postsCount: "242 Sanctioned Posts",
            groups: ["districts", "polyclinics", "farms"],
            nodes: [
                {
                    id: "dd-district-wings",
                    title: "Deputy Directors (5 District Core Wings)",
                    office: "Offices of the JD ARD in 23 Districts",
                    payLevel: "Level 19 (ROPA 2019)",
                    cadre: "WBAH&VS Reconstituted DD Cadre (50-Point Roster)",
                    posts: "115 Posts (5 per District across 23 Districts)",
                    headOfOffice: false,
                    hooNote: "District Functional Wing Directors",
                    superior: "Joint Director of ARD (District Head)",
                    subordinates: "Assistant Directors (VR&I, Fodder), BLDOs, Technical Assistants",
                    sarReporting: "Reporting Officer for BLDOs in their discipline; Reports to District JD",
                    functions: "1. DD (Animal Health): District-wide disease control, hospital monitoring.\n2. DD (Cattle Production & AI): Semen distribution, crossbreeding drives.\n3. DD (Fodder Development): Minikit supply, seed demonstration.\n4. DD (Microbiology & Lab): District laboratory diagnostics.\n5. Project Officer (PO) / DD (Special Projects): RKVY, NRLM, state subsidy schemes.",
                    legalBasis: "Notification No. 1808-AR&AH & Order No. 575-AR&AH",
                    tags: ["5 Core Wings", "Level 19", "District Specialists", "50-Point Roster"]
                },
                {
                    id: "dd-polyclinics",
                    title: "Deputy Directors (In-Charge, 26 State Veterinary Polyclinics)",
                    office: "26 State Veterinary Polyclinics situated across West Bengal",
                    payLevel: "Level 19 (ROPA 2019)",
                    cadre: "WBAH&VS Clinical Specialist Cadre",
                    posts: "26 DD Posts (+ 104 Specialist VOs = 130 Clinical Specialists)",
                    headOfOffice: true,
                    hooNote: "Declared Head of Office for Polyclinic Establishment",
                    superior: "Joint Director of ARD (District) & Additional Director (AH)",
                    subordinates: "4 Specialist Veterinary Officers each: Surgery, Medicine, Gynaecology & Obstetrics, Diagnostics",
                    sarReporting: "Reporting Officer for 4 Specialist VOs; Reports to District JD",
                    functions: "Apex tertiary clinical care for large and small animals. Multi-specialty veterinary surgeries, radiographic & ultrasonographic imaging, advanced obstetrics, inpatient critical care, and emergency trauma referral center.",
                    legalBasis: "Notification No. 1808-AR&AH & Order No. 575-AR&AH",
                    tags: ["Polyclinic", "26 Centers", "130 Specialists", "Tertiary Care"]
                },
                {
                    id: "dd-poultry-stations",
                    title: "Deputy Directors / Managers, 8 State Poultry & Duck Stations",
                    office: "Kakdwip, Nimpith, Gobardanga, Ranaghat, Durgapur, Balurghat, Mohitnagar, Golapbag",
                    payLevel: "Level 19 (ROPA 2019)",
                    cadre: "WBAH&VS Production Cadre",
                    posts: "8 Intensive Stations",
                    headOfOffice: true,
                    hooNote: "Breeding Station Head of Office",
                    superior: "Additional Director (AP) & District Joint Director",
                    subordinates: "Assistant Directors, Hatchery Officers, Farm Supervisors",
                    sarReporting: "Reports to Addl. Director (AP) / District JD",
                    functions: "Hatchery management, production and supply of day-old chicks and ducklings (RIR, Vanaraja, Khaki Campbell) to rural self-help groups (SHGs), biosecurity and genetic improvement of avian germplasm.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Poultry Stations", "Hatcheries", "Avian Breeding", "SHG Supply"]
                },
                {
                    id: "dd-training-institutes",
                    title: "Deputy Directors / Principals, Animal Husbandry Training Institutes",
                    office: "AHTI Medinipur, Salboni, and Regional Training Centres",
                    payLevel: "Level 19 (ROPA 2019)",
                    cadre: "WBAH&VS Training Cadre",
                    posts: "Training Setup",
                    headOfOffice: true,
                    hooNote: "Training Institute Head of Office",
                    superior: "Director of Animal Health & Veterinary Services (DAH&VS)",
                    subordinates: "Assistant Directors (Lecturers), Instructors, Trainee Paravets",
                    sarReporting: "Reports to DAH&VS",
                    functions: "Institutional pre-service and in-service training for Livestock Development Assistants (LDAs), refresher courses on modern artificial insemination, biosecurity protocols, cold chain management, and skill certification.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Training Institute", "AHTI Medinipur", "Capacity Building", "Paravets"]
                }
            ]
        },
        {
            id: "tier-6",
            tierNumber: "Tier 6",
            tierName: "Block Animal Husbandry Tier",
            levelBadge: "Pay Level 16 / 17",
            badgeColor: "bg-amber-600 text-white",
            statutoryRef: "Panchayat Act • WBAH&VS Reconstitution Rules 2025",
            description: "344 Block Livestock Development Offices (BLDOs) driving grassroots livestock administration, artificial insemination, and departmental scheme execution across every block of West Bengal.",
            postsCount: "344 BLDOs",
            groups: ["districts"],
            nodes: [
                {
                    id: "bldo-blocks",
                    title: "Block Livestock Development Officers (BLDOs)",
                    office: "344 Block Livestock Development Offices across all Community Development Blocks",
                    payLevel: "Level 16 / Level 17 (WBAH&VS)",
                    cadre: "WBAH&VS Operational Cadre",
                    posts: "344 Sanctioned Block Posts",
                    headOfOffice: true,
                    hooNote: "Block Head of Office & DDO for Block ARD Setup",
                    superior: "Joint Director of ARD (District) & respective District DDs",
                    subordinates: "Block LDAs, Veterinary Pharmacists, Prani Bandhus, Prani Mitras",
                    sarReporting: "Reporting: Respective DD/PO • Reviewing: Joint Director • Accepting: DAH&VS",
                    functions: "Chief administrative executive of ARD at the Block/Panchayat Samiti level. Executes state livestock incentive schemes, manages disaster relief, supervises doorstep AI services, administers block drug store, coordinates with BDO.",
                    legalBasis: "Order No. 575-AR&AH dt. 27.02.2026 & West Bengal Panchayat Act",
                    tags: ["BLDO", "344 Blocks", "Panchayat Samiti", "Field Executive"]
                },
                {
                    id: "ad-specialist-wings",
                    title: "Assistant Directors (Specialized Wings: VR&I, Fodder, Small Animals)",
                    office: "District Headquarters & Sub-Divisional Offices",
                    payLevel: "Level 16 / 17 (ROPA 2019)",
                    cadre: "WBAH&VS Technical Cadre",
                    posts: "District Sub-Wings",
                    headOfOffice: false,
                    hooNote: "District Specialist Wing Officers",
                    superior: "Respective Deputy Director & Joint Director of ARD",
                    subordinates: "Field Assistants, Inseminators, Demonstration Staff",
                    sarReporting: "Reports to respective DD; Reviewing: Joint Director; Accepting: DAH&VS",
                    functions: "Vaccine Research & Investigation (VR&I), cold chain logistics, fodder demonstration plots, small animal extension (Black Bengal goat, piggery multiplication).",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Assistant Directors", "VR&I", "Fodder", "Small Animals"]
                }
            ]
        },
        {
            id: "tier-7",
            tierNumber: "Tier 7",
            tierName: "Field Primary Veterinary Clinical Infrastructure",
            levelBadge: "Pay Level 16",
            badgeColor: "bg-rose-600 text-white",
            statutoryRef: "Notif. 1809-AR&AH Cadre Schedule (703 Hospitals + 1962 MVUs)",
            description: "Primary animal health backbone: 87 State Animal Health Centres (SAHC), 342 Block Animal Health Centres (BAHC), 274 Additional Block Animal Health Centres (ABAHC), and Mobile Veterinary Units.",
            postsCount: "703 Centres + MVUs",
            groups: ["districts"],
            nodes: [
                {
                    id: "vo-hospitals",
                    title: "Veterinary Officers (SAHC / BAHC / ABAHC)",
                    office: "87 SAHCs, 342 BAHCs, 274 ABAHCs situated throughout rural and urban West Bengal",
                    payLevel: "Level 16 (ROPA 2019)",
                    cadre: "WBAH&VS Entry & Clinical Cadre",
                    posts: "703 Sanctioned Primary Clinical Centres",
                    headOfOffice: false,
                    hooNote: "Clinical Centre In-Charge",
                    superior: "Block Livestock Development Officer (BLDO) & District DD (AH)",
                    subordinates: "Livestock Development Assistants (LDAs), Dressers, Attendants",
                    sarReporting: "Reporting: Respective DD/PO • Reviewing: Joint Director • Accepting: DAH&VS",
                    functions: "Direct frontline veterinary medical care, out-patient consultations, minor and major surgeries, preventive rabies prophylaxis, emergency obstetrical interventions, post-mortem examinations, epidemic outbreak reporting.",
                    legalBasis: "Notification No. 1809-AR&AH dt. 18.06.2025",
                    tags: ["Veterinary Officers", "SAHC", "BAHC", "ABAHC", "Primary Healthcare"]
                },
                {
                    id: "vo-mvu",
                    title: "Veterinary Officers, Mobile Veterinary Units (MVUs)",
                    office: "1962 Mobile Veterinary Units operating in rural and remote gram panchayats",
                    payLevel: "Level 16 (ROPA 2019)",
                    cadre: "WBAH&VS Clinical Cadre",
                    posts: "Doorstep Ambulatory Network",
                    headOfOffice: false,
                    hooNote: "Mobile Unit Clinician",
                    superior: "Block Livestock Development Officer (BLDO) & District DD (AH)",
                    subordinates: "Paravet, Driver-cum-Attendant",
                    sarReporting: "Reports to BLDO & DD (AH)",
                    functions: "Doorstep emergency veterinary healthcare, clinical treatment of animals in remote villages, organized vaccination camps, rapid response during natural disasters (floods, cyclones).",
                    legalBasis: "State MVU Mission & GoI DAHD Scheme",
                    tags: ["MVU", "Doorstep Healthcare", "Ambulatory", "Disaster Response"]
                }
            ]
        }
    ];

    let currentOrganogramFilter = 'all';
    let collapsedTiers = {};

    function getOrganogramNodeById(nodeId) {
        for (const tier of ARD_ORGANOGRAM_DATA) {
            for (const node of tier.nodes) {
                if (node.id === nodeId) return { node, tier };
            }
        }
        return null;
    }

    function renderSARFlowDiagram() {
        return `
        <div class="space-y-6">
            <!-- Banner -->
            <div class="bg-gradient-to-r from-blue-900 to-indigo-900 rounded-xl p-5 text-white shadow-md border border-blue-700">
                <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-400 text-slate-900">Statutory Performance Appraisal</span>
                            <span class="text-xs text-blue-200">Memo No. 926-AR&AH/3A-08/2021 dt. 25.04.2022 & Memo No. 1393 dt. 08.06.2026</span>
                        </div>
                        <h3 class="text-lg font-bold text-white mt-1">West Bengal Animal Health & Veterinary Services (WBAH&VS) SAR / ACR Statutory Channels</h3>
                        <p class="text-xs text-blue-100 mt-1 max-w-3xl">
                            All performance appraisals (Self Appraisal Reports / Annual Confidential Reports) within the 1,794-post cadre flow through strictly designated 3-tier statutory appraisal chains.
                        </p>
                    </div>
                    <div class="text-right text-xs">
                        <div class="font-bold text-amber-300">Timelines</div>
                        <div class="text-blue-200 text-[11px]">Self: By 30 Apr • Reporting: By 31 May<br>Review: By 30 Jun • Accept: By 31 Jul</div>
                    </div>
                </div>
            </div>

            <!-- Flowcards Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Flow 1: Field Officers & BLDOs -->
                <div class="bg-white rounded-xl border-2 border-rose-200 shadow-sm overflow-hidden flex flex-col">
                    <div class="bg-rose-50 border-b border-rose-200 p-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-600 text-white uppercase">Channel 1</span>
                        <h4 class="font-bold text-sm text-slate-900 mt-1">Field Clinical Cadre & BLDOs</h4>
                        <p class="text-[11px] text-slate-500">VOs (SAHC / BAHC / ABAHC / MVU) & BLDOs (Pay Level 16 / 17)</p>
                    </div>
                    <div class="p-4 space-y-4 flex-1">
                        <!-- Step 1 -->
                        <div class="p-3 bg-slate-50 rounded-lg border border-slate-200">
                            <div class="text-[10px] font-bold text-slate-400 uppercase">Step 1: Self Appraisal Submission</div>
                            <div class="font-semibold text-xs text-slate-800 mt-0.5">Veterinary Officer / BLDO</div>
                            <div class="text-[11px] text-slate-500">Submits SAR Form 1 with quantitative targets</div>
                        </div>
                        <div class="flex justify-center text-rose-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 2 -->
                        <div class="p-3 bg-amber-50 rounded-lg border border-amber-200">
                            <div class="text-[10px] font-bold text-amber-700 uppercase">Step 2: Reporting Officer</div>
                            <div class="font-bold text-xs text-amber-950 mt-0.5">Respective Deputy Director / PO</div>
                            <div class="text-[11px] text-amber-800">Assigns numerical score, pen-picture & integrity note</div>
                        </div>
                        <div class="flex justify-center text-rose-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 3 -->
                        <div class="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                            <div class="text-[10px] font-bold text-indigo-700 uppercase">Step 3: Reviewing Officer</div>
                            <div class="font-bold text-xs text-indigo-950 mt-0.5">Joint Director of ARD (District)</div>
                            <div class="text-[11px] text-indigo-800">Reviews grading, records remarks or disagreement</div>
                        </div>
                        <div class="flex justify-center text-rose-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 4 -->
                        <div class="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                            <div class="text-[10px] font-bold text-emerald-700 uppercase">Step 4: Accepting Authority</div>
                            <div class="font-bold text-xs text-emerald-950 mt-0.5">Director of AH&VS (Apex Cadre - Level 22)</div>
                            <div class="text-[11px] text-emerald-800">Final acceptance and custody in dossier register</div>
                        </div>
                    </div>
                </div>

                <!-- Flow 2: Deputy Directors & POs -->
                <div class="bg-white rounded-xl border-2 border-emerald-200 shadow-sm overflow-hidden flex flex-col">
                    <div class="bg-emerald-50 border-b border-emerald-200 p-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-600 text-white uppercase">Channel 2</span>
                        <h4 class="font-bold text-sm text-slate-900 mt-1">Deputy Directors & Project Officers</h4>
                        <p class="text-[11px] text-slate-500">District DDs, Polyclinic DDs, Poultry DDs (Pay Level 19 - 242 Posts)</p>
                    </div>
                    <div class="p-4 space-y-4 flex-1">
                        <!-- Step 1 -->
                        <div class="p-3 bg-slate-50 rounded-lg border border-slate-200">
                            <div class="text-[10px] font-bold text-slate-400 uppercase">Step 1: Self Appraisal Submission</div>
                            <div class="font-semibold text-xs text-slate-800 mt-0.5">Deputy Director / PO</div>
                            <div class="text-[11px] text-slate-500">Submits SAR Form 2 with district milestone achievements</div>
                        </div>
                        <div class="flex justify-center text-emerald-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 2 -->
                        <div class="p-3 bg-amber-50 rounded-lg border border-amber-200">
                            <div class="text-[10px] font-bold text-amber-700 uppercase">Step 2: Reporting Officer</div>
                            <div class="font-bold text-xs text-amber-950 mt-0.5">Joint Director of ARD (District / Mega-Farm)</div>
                            <div class="text-[11px] text-amber-800">Evaluates district wing output, leadership & integrity</div>
                        </div>
                        <div class="flex justify-center text-emerald-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 3 -->
                        <div class="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                            <div class="text-[10px] font-bold text-indigo-700 uppercase">Step 3: Reviewing Officer</div>
                            <div class="font-bold text-xs text-indigo-950 mt-0.5">Additional Director of ARD (Zonal / Functional)</div>
                            <div class="text-[11px] text-indigo-800">Divisional quality audit and appraisal review</div>
                        </div>
                        <div class="flex justify-center text-emerald-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 4 -->
                        <div class="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                            <div class="text-[10px] font-bold text-emerald-700 uppercase">Step 4: Accepting Authority</div>
                            <div class="font-bold text-xs text-emerald-950 mt-0.5">Director of AH&VS (Apex Cadre - Level 22)</div>
                            <div class="text-[11px] text-emerald-800">Final acceptance and DPC benchmark certification</div>
                        </div>
                    </div>
                </div>

                <!-- Flow 3: Joint Directors & Additional Directors -->
                <div class="bg-white rounded-xl border-2 border-purple-200 shadow-sm overflow-hidden flex flex-col">
                    <div class="bg-purple-50 border-b border-purple-200 p-4">
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-600 text-white uppercase">Channel 3</span>
                        <h4 class="font-bold text-sm text-slate-900 mt-1">Joint Directors & Additional Directors</h4>
                        <p class="text-[11px] text-slate-500">District JDs, Farm JDs, RDDL JDs, Addl. Directors (Pay Level 20 & 21)</p>
                    </div>
                    <div class="p-4 space-y-4 flex-1">
                        <!-- Step 1 -->
                        <div class="p-3 bg-slate-50 rounded-lg border border-slate-200">
                            <div class="text-[10px] font-bold text-slate-400 uppercase">Step 1: Self Appraisal Submission</div>
                            <div class="font-semibold text-xs text-slate-800 mt-0.5">Joint Director / Additional Director</div>
                            <div class="text-[11px] text-slate-500">Submits SAR Form 3 with executive leadership achievements</div>
                        </div>
                        <div class="flex justify-center text-purple-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 2 -->
                        <div class="p-3 bg-amber-50 rounded-lg border border-amber-200">
                            <div class="text-[10px] font-bold text-amber-700 uppercase">Step 2: Reporting Officer</div>
                            <div class="font-bold text-xs text-amber-950 mt-0.5">Director of AH&VS (Apex Cadre - Level 22)</div>
                            <div class="text-[11px] text-amber-800">Technical leadership assessment and statewide impact</div>
                        </div>
                        <div class="flex justify-center text-purple-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 3 -->
                        <div class="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                            <div class="text-[10px] font-bold text-indigo-700 uppercase">Step 3: Reviewing Officer</div>
                            <div class="font-bold text-xs text-indigo-950 mt-0.5">Special Secretary, ARD Department</div>
                            <div class="text-[11px] text-indigo-800">Secretariat review of administrative and fiscal performance</div>
                        </div>
                        <div class="flex justify-center text-purple-500">
                            <i data-lucide="arrow-down" class="w-5 h-5"></i>
                        </div>
                        <!-- Step 4 -->
                        <div class="p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                            <div class="text-[10px] font-bold text-emerald-700 uppercase">Step 4: Accepting Authority</div>
                            <div class="font-bold text-xs text-emerald-950 mt-0.5">Additional Chief Secretary / Principal Secretary</div>
                            <div class="text-[11px] text-emerald-800">Final acceptance by Government for Apex Promotion</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    function renderOrganogram() {
        const container = document.getElementById('organogramTreeContainer');
        if (!container) return;

        if (currentOrganogramFilter === 'sar') {
            container.innerHTML = renderSARFlowDiagram();
            if (window.lucide) window.lucide.createIcons();
            return;
        }

        const searchQuery = (document.getElementById('organogramSearch')?.value || '').trim().toLowerCase();

        let visibleTiers = [];

        ARD_ORGANOGRAM_DATA.forEach(tier => {
            // Check if tier matches current filter
            let tierMatchesGroup = (currentOrganogramFilter === 'all') || tier.groups.includes(currentOrganogramFilter);

            // Filter nodes inside tier
            const filteredNodes = tier.nodes.filter(node => {
                let nodeMatchesGroup = (currentOrganogramFilter === 'all') || 
                                       tier.groups.includes(currentOrganogramFilter) ||
                                       (node.tags && node.tags.some(t => t.toLowerCase().includes(currentOrganogramFilter)));

                if (!nodeMatchesGroup) return false;

                if (!searchQuery) return true;

                // Match against search query
                const haystack = [
                    node.title,
                    node.office,
                    node.payLevel,
                    node.cadre,
                    node.functions,
                    node.superior,
                    node.subordinates,
                    node.legalBasis,
                    ...(node.tags || [])
                ].join(' ').toLowerCase();

                return haystack.includes(searchQuery);
            });

            if (filteredNodes.length > 0) {
                visibleTiers.push({
                    tier,
                    nodes: filteredNodes
                });
            }
        });

        if (visibleTiers.length === 0) {
            container.innerHTML = `
                <div class="bg-white rounded-2xl p-12 text-center border border-slate-200 shadow-sm">
                    <div class="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 mb-3">
                        <i data-lucide="filter-x" class="w-8 h-8"></i>
                    </div>
                    <h3 class="text-base font-bold text-slate-800">No Administrative Nodes Match Your Query</h3>
                    <p class="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                        Try searching with different keywords (e.g. "Polyclinic", "HCLF", "IAH&VB", "Joint Director", "Level 20") or reset the filter pills.
                    </p>
                    <button onclick="window.setOrganogramFilter('all'); document.getElementById('organogramSearch').value = ''; window.renderOrganogram();" class="mt-4 px-4 py-2 rounded-lg bg-slate-800 text-white text-xs font-semibold hover:bg-slate-700 transition">
                        Reset All Filters
                    </button>
                </div>
            `;
            if (window.lucide) window.lucide.createIcons();
            return;
        }

        let html = '';

        visibleTiers.forEach(({ tier, nodes }) => {
            const isCollapsed = !!collapsedTiers[tier.id];

            html += `
            <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden transition-all duration-200" id="${tier.id}">
                <!-- Tier Header -->
                <div class="p-4 sm:p-5 bg-gradient-to-r from-slate-900 via-slate-800 to-wbblue-950 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer select-none" onclick="window.toggleOrganogramTier('${tier.id}')">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl ${tier.badgeColor} font-black text-xs flex items-center justify-center shadow shrink-0">
                            ${tier.tierNumber.replace('Tier ', 'T')}
                        </div>
                        <div>
                            <div class="flex flex-wrap items-center gap-2">
                                <span class="text-base sm:text-lg font-black tracking-tight text-white">${tier.tierName}</span>
                                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold ${tier.badgeColor}">
                                    ${tier.levelBadge}
                                </span>
                                <span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-white/10 text-blue-200 border border-white/20">
                                    ${tier.postsCount}
                                </span>
                            </div>
                            <p class="text-xs text-blue-200 mt-1 line-clamp-1 max-w-3xl">${tier.description}</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-3 text-xs text-blue-200 shrink-0 self-end sm:self-center">
                        <span class="text-[11px] text-amber-300 font-mono hidden md:inline-block">${tier.statutoryRef}</span>
                        <div class="p-1 rounded-lg bg-white/10 hover:bg-white/20 transition">
                            <i data-lucide="${isCollapsed ? 'chevron-right' : 'chevron-down'}" class="w-5 h-5 text-white"></i>
                        </div>
                    </div>
                </div>

                <!-- Tier Nodes Content -->
                <div class="${isCollapsed ? 'hidden' : 'p-5'} space-y-4 bg-slate-50/50">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        ${nodes.map(node => `
                            <div class="bg-white rounded-xl border border-slate-200/80 p-4 shadow-sm hover:shadow-md hover:border-wbblue-400 transition-all flex flex-col justify-between group">
                                <div class="space-y-3">
                                    <!-- Card Header -->
                                    <div class="flex items-start justify-between gap-2">
                                        <div class="space-y-1 flex-1">
                                            <div class="flex items-center gap-1.5 flex-wrap">
                                                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-800 border border-slate-200">
                                                    ${node.payLevel}
                                                </span>
                                                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                                                    ${node.posts}
                                                </span>
                                                ${node.headOfOffice ? `
                                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                                                        <i data-lucide="check-circle" class="w-3 h-3"></i> Head of Office
                                                    </span>
                                                ` : ''}
                                            </div>
                                            <h4 class="font-bold text-sm text-slate-900 group-hover:text-wbblue-700 transition leading-snug pt-1">
                                                ${node.title}
                                            </h4>
                                            <div class="text-[11px] text-slate-500 line-clamp-1 flex items-center gap-1">
                                                <i data-lucide="map-pin" class="w-3 h-3 text-slate-400 shrink-0"></i>
                                                <span>${node.office}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Quick Summary Bullets -->
                                    <div class="p-2.5 rounded-lg bg-slate-50 border border-slate-100 space-y-1.5 text-[11px]">
                                        <div class="flex items-start gap-1.5 text-slate-700">
                                            <span class="text-slate-400 shrink-0 font-semibold">Reports to:</span>
                                            <span class="font-medium text-slate-900 line-clamp-1">${node.superior}</span>
                                        </div>
                                        <div class="flex items-start gap-1.5 text-slate-700">
                                            <span class="text-slate-400 shrink-0 font-semibold">Subordinates:</span>
                                            <span class="font-medium text-slate-900 line-clamp-1">${node.subordinates}</span>
                                        </div>
                                        <div class="flex items-start gap-1.5 text-slate-700">
                                            <span class="text-purple-600 shrink-0 font-bold">SAR Channel:</span>
                                            <span class="font-medium text-slate-900 line-clamp-1">${node.sarReporting}</span>
                                        </div>
                                    </div>

                                    <!-- Tags Strip -->
                                    <div class="flex flex-wrap gap-1">
                                        ${(node.tags || []).map(tag => `
                                            <span class="px-2 py-0.5 rounded-full text-[9px] font-medium bg-slate-100 text-slate-600">
                                                ${tag}
                                            </span>
                                        `).join('')}
                                    </div>
                                </div>

                                <!-- Action Button -->
                                <div class="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between">
                                    <span class="text-[10px] text-slate-400 font-mono">${node.cadre.substring(0, 24)}...</span>
                                    <button onclick="window.openOrganogramModal('${node.id}')" class="px-3 py-1 text-xs font-semibold text-wbblue-700 hover:text-white hover:bg-wbblue-800 rounded-lg border border-wbblue-300 hover:border-wbblue-800 transition flex items-center gap-1">
                                        <span>Inspect Node</span>
                                        <i data-lucide="external-link" class="w-3 h-3"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            `;
        });

        container.innerHTML = html;
        if (window.lucide) window.lucide.createIcons();
    }

    function toggleOrganogramTier(tierId) {
        collapsedTiers[tierId] = !collapsedTiers[tierId];
        renderOrganogram();
    }

    function expandAllOrganogram() {
        collapsedTiers = {};
        renderOrganogram();
    }

    function collapseAllOrganogram() {
        ARD_ORGANOGRAM_DATA.forEach(t => {
            collapsedTiers[t.id] = true;
        });
        renderOrganogram();
    }

    function setOrganogramFilter(filterKey) {
        currentOrganogramFilter = filterKey;

        // Update pill styling
        const pills = document.querySelectorAll('.organogram-filter-btn');
        pills.forEach(pill => {
            const f = pill.getAttribute('data-filter');
            if (f === filterKey) {
                pill.className = 'organogram-filter-btn px-3 py-1 rounded-lg font-bold bg-slate-900 text-white shadow-sm transition';
            } else {
                let baseColor = 'bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200';
                if (f === 'secretariat') baseColor = 'bg-amber-50 text-amber-900 border-amber-300 hover:bg-amber-100';
                else if (f === 'zones') baseColor = 'bg-purple-50 text-purple-900 border-purple-300 hover:bg-purple-100';
                else if (f === 'districts') baseColor = 'bg-indigo-50 text-indigo-900 border-indigo-300 hover:bg-indigo-100';
                else if (f === 'polyclinics') baseColor = 'bg-teal-50 text-teal-900 border-teal-300 hover:bg-teal-100';
                else if (f === 'iahvb') baseColor = 'bg-rose-50 text-rose-900 border-rose-300 hover:bg-rose-100';
                else if (f === 'farms') baseColor = 'bg-emerald-50 text-emerald-900 border-emerald-300 hover:bg-emerald-100';
                else if (f === 'sar') baseColor = 'bg-blue-50 text-blue-900 border-blue-300 hover:bg-blue-100';
                pill.className = `organogram-filter-btn px-3 py-1 rounded-lg font-semibold ${baseColor} border transition`;
            }
        });

        renderOrganogram();
    }

    function filterOrganogram() {
        renderOrganogram();
    }

    function openOrganogramModal(nodeId) {
        const item = getOrganogramNodeById(nodeId);
        if (!item) return;
        const { node, tier } = item;

        const modal = document.getElementById('organogramNodeModal');
        if (!modal) return;

        document.getElementById('nodeModalTitle').innerHTML = `
            <i data-lucide="network" class="w-5 h-5 text-amber-300 shrink-0"></i>
            <span>${node.title}</span>
        `;
        document.getElementById('nodeModalSubtitle').innerText = `${tier.tierNumber}: ${tier.tierName} • ${node.office}`;

        const content = document.getElementById('nodeModalContent');
        content.innerHTML = `
            <div class="space-y-4">
                <!-- Badges Header -->
                <div class="flex flex-wrap items-center gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <span class="px-2.5 py-1 rounded-md text-xs font-bold bg-slate-800 text-white">
                        ${node.payLevel}
                    </span>
                    <span class="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-100 text-blue-900 border border-blue-300">
                        Sanctioned Posts: ${node.posts}
                    </span>
                    <span class="px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-100 text-purple-900 border border-purple-300">
                        ${node.cadre}
                    </span>
                    ${node.headOfOffice ? `
                        <span class="px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-600 text-white shadow-sm flex items-center gap-1">
                            <i data-lucide="check-circle-2" class="w-3.5 h-3.5"></i> Declared Head of Office (HOO)
                        </span>
                    ` : ''}
                </div>

                <!-- 2-Column Administrative Grid -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div class="p-3 bg-blue-50/60 rounded-xl border border-blue-200 space-y-1">
                        <div class="text-[10px] font-bold text-blue-800 uppercase tracking-wider">Superior Command (Reports To)</div>
                        <div class="text-xs font-bold text-blue-950">${node.superior}</div>
                        <div class="text-[11px] text-blue-700">Immediate Administrative & Technical Authority</div>
                    </div>
                    <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-200 space-y-1">
                        <div class="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">Direct Subordinate Command</div>
                        <div class="text-xs font-bold text-emerald-950">${node.subordinates}</div>
                        <div class="text-[11px] text-emerald-700">Offices, Specialists & Institutions within Jurisdiction</div>
                    </div>
                </div>

                <!-- Statutory Head of Office Status & Financial Delegation -->
                <div class="p-3.5 bg-amber-50/70 rounded-xl border border-amber-200 space-y-1.5">
                    <div class="flex items-center gap-2">
                        <i data-lucide="award" class="w-4 h-4 text-amber-700 shrink-0"></i>
                        <span class="text-xs font-bold text-amber-950">Statutory Head of Office Status & Delegation</span>
                    </div>
                    <p class="text-xs text-amber-900 leading-relaxed">
                        ${node.hooNote}. Exercises designated Drawing & Disbursing Officer (DDO) and financial sanctioning powers under the West Bengal Financial Rules (WBFR) and delegation orders.
                    </p>
                </div>

                <!-- Statutory SAR / ACR Appraisal Hierarchy -->
                <div class="p-3.5 bg-purple-50/70 rounded-xl border border-purple-200 space-y-2">
                    <div class="flex items-center gap-2">
                        <i data-lucide="shield-check" class="w-4 h-4 text-purple-700 shrink-0"></i>
                        <span class="text-xs font-bold text-purple-950">SAR / ACR Performance Appraisal Reporting Hierarchy</span>
                    </div>
                    <div class="p-2 bg-white rounded-lg border border-purple-200 text-xs font-semibold text-purple-900">
                        ${node.sarReporting}
                    </div>
                    <div class="text-[11px] text-purple-700">
                        Statutory compliance mandated vide ARD Memo No. 926-AR&AH/3A-08/2021 dt. 25.04.2022 & Memo No. 1393 dt. 08.06.2026.
                    </div>
                </div>

                <!-- Core Mandates & Functions -->
                <div class="p-3.5 bg-white rounded-xl border border-slate-200 space-y-2">
                    <div class="flex items-center gap-2">
                        <i data-lucide="list-checks" class="w-4 h-4 text-slate-700 shrink-0"></i>
                        <span class="text-xs font-bold text-slate-900">Core Administrative Responsibilities & Functions</span>
                    </div>
                    <div class="text-xs text-slate-700 whitespace-pre-line leading-relaxed pl-2 border-l-2 border-slate-300">
                        ${node.functions}
                    </div>
                </div>

                <!-- Legal & Administrative Authority -->
                <div class="p-3 bg-slate-100 rounded-xl border border-slate-200 text-[11px] text-slate-600 flex items-center justify-between">
                    <div>
                        <span class="font-bold text-slate-800">Statutory Sanction:</span>
                        <span class="font-mono text-slate-700 ml-1">${node.legalBasis}</span>
                    </div>
                    <div class="font-bold text-slate-700">
                        ${tier.statutoryRef}
                    </div>
                </div>
            </div>
        `;

        modal.classList.remove('hidden');
        if (window.lucide) window.lucide.createIcons();
    }

    function closeOrganogramModal() {
        const modal = document.getElementById('organogramNodeModal');
        if (modal) modal.classList.add('hidden');
    }

    // Bind modal close buttons
    const btnClose = document.getElementById('btnCloseOrganogramNodeModal');
    if (btnClose) btnClose.addEventListener('click', closeOrganogramModal);

    const btnCloseFooter = document.getElementById('btnCloseOrganogramNodeFooter');
    if (btnCloseFooter) btnCloseFooter.addEventListener('click', closeOrganogramModal);

    const modal = document.getElementById('organogramNodeModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeOrganogramModal();
        });
    }

    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeOrganogramModal();
    });

    // Expose functions globally
    window.renderOrganogram = renderOrganogram;
    window.toggleOrganogramTier = toggleOrganogramTier;
    window.expandAllOrganogram = expandAllOrganogram;
    window.collapseAllOrganogram = collapseAllOrganogram;
    window.setOrganogramFilter = setOrganogramFilter;
    window.filterOrganogram = filterOrganogram;
    window.openOrganogramModal = openOrganogramModal;
    window.closeOrganogramModal = closeOrganogramModal;
})();

    // =========================================================================
    // VISITOR & ACCESS INTELLIGENCE MODAL CONTROLLER
    // =========================================================================

    let analyticsRefreshInterval = null;

    function formatDuration(totalSec) {
        if (!totalSec || totalSec <= 0) return '0s';
        if (totalSec < 60) return `${totalSec}s`;
        const mins = Math.floor(totalSec / 60);
        const secs = totalSec % 60;
        if (mins < 60) return `${mins}m ${secs}s`;
        const hrs = Math.floor(mins / 60);
        const remMins = mins % 60;
        return `${hrs}h ${remMins}m`;
    }

    function timeAgo(isoStr) {
        if (!isoStr) return '—';
        const diffMs = Date.now() - new Date(isoStr).getTime();
        const diffSec = Math.floor(diffMs / 1000);
        if (diffSec < 15) return 'Just now';
        if (diffSec < 60) return `${diffSec}s ago`;
        const diffMin = Math.floor(diffSec / 60);
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return `${diffHr}h ago`;
        return `${Math.floor(diffHr / 24)}d ago`;
    }

    async function loadVisitorAnalytics() {
        const totalIPsEl = document.getElementById('analyticsTotalIPs');
        const activeNowEl = document.getElementById('analyticsActiveNow');
        const avgTimeEl = document.getElementById('analyticsAvgTime');
        const totalTimeEl = document.getElementById('analyticsTotalTime');
        const totalIntEl = document.getElementById('analyticsTotalInteractions');
        const citiesList = document.getElementById('analyticsTopCitiesList');
        const devicesList = document.getElementById('analyticsDevicesList');
        const popularList = document.getElementById('analyticsPopularPagesList');
        const tableBody = document.getElementById('analyticsSessionsTableBody');
        const searchInput = document.getElementById('analyticsSearchInput');
        const query = searchInput ? searchInput.value.trim() : '';

        try {
            const [statsRes, sessionsRes] = await Promise.all([
                fetch('/api/analytics/stats'),
                fetch(`/api/analytics/sessions?search=${encodeURIComponent(query)}`)
            ]);

            const stats = await statsRes.json();
            const sessionsData = await sessionsRes.json();

            // 1. Update KPI Cards
            if (totalIPsEl) totalIPsEl.innerText = (stats.total_unique_ips || 0).toLocaleString();
            if (activeNowEl) activeNowEl.innerText = (stats.active_now || 0).toLocaleString();
            if (avgTimeEl) avgTimeEl.innerText = formatDuration(stats.avg_time_seconds);
            if (totalTimeEl) totalTimeEl.innerText = `Total: ${formatDuration(stats.total_time_seconds)} across sessions`;
            if (totalIntEl) totalIntEl.innerText = (stats.total_pageviews || 0).toLocaleString();

            // 2. Render Top Locations
            if (citiesList) {
                const cities = stats.top_cities || [];
                if (cities.length === 0) {
                    citiesList.innerHTML = '<div class="text-slate-400 text-center py-4">No location records yet.</div>';
                } else {
                    const maxCount = Math.max(...cities.map(c => c.count), 1);
                    citiesList.innerHTML = cities.map(c => {
                        const pct = Math.round((c.count / maxCount) * 100);
                        return `
                            <div class="space-y-1">
                                <div class="flex items-center justify-between text-xs">
                                    <span class="font-bold text-slate-800">${c.city || 'Unknown'}${c.region ? `, ${c.region}` : ''}</span>
                                    <span class="font-mono text-slate-500 font-semibold">${c.count} ${c.count === 1 ? 'visit' : 'visits'}</span>
                                </div>
                                <div class="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                    <div class="h-full bg-wbblue-600 rounded-full" style="width: ${pct}%"></div>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }

            // 3. Render Devices & Platforms
            if (devicesList) {
                const devices = stats.devices || {};
                const osBreakdown = stats.os_breakdown || {};
                const browsers = stats.browsers || {};

                const devEntries = Object.entries(devices);
                if (devEntries.length === 0) {
                    devicesList.innerHTML = '<div class="text-slate-400 text-center py-4">No device records yet.</div>';
                } else {
                    devicesList.innerHTML = `
                        <div class="space-y-2">
                            <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Device Type</div>
                            <div class="flex flex-wrap gap-1.5">
                                ${devEntries.map(([k, v]) => `
                                    <span class="px-2.5 py-1 rounded-xl bg-purple-50 text-purple-900 border border-purple-200 text-xs font-bold flex items-center gap-1.5">
                                        <i data-lucide="${k === 'Mobile' ? 'smartphone' : k === 'Tablet' ? 'tablet' : 'laptop'}" class="w-3.5 h-3.5 text-purple-700"></i>
                                        <span>${k}: <strong>${v}</strong></span>
                                    </span>
                                `).join('')}
                            </div>
                            <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pt-2">Operating Systems</div>
                            <div class="flex flex-wrap gap-1.5">
                                ${Object.entries(osBreakdown).map(([k, v]) => `
                                    <span class="px-2 py-0.5 rounded-lg bg-slate-100 text-slate-700 font-mono text-[11px] font-semibold border border-slate-200">
                                        ${k}: ${v}
                                    </span>
                                `).join('')}
                            </div>
                            <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider pt-2">Browsers</div>
                            <div class="flex flex-wrap gap-1.5">
                                ${Object.entries(browsers).map(([k, v]) => `
                                    <span class="px-2 py-0.5 rounded-lg bg-slate-100 text-slate-700 font-mono text-[11px] font-semibold border border-slate-200">
                                        ${k}: ${v}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
            }

            // 4. Render Popular Modules
            if (popularList) {
                const popular = stats.popular_pages || [];
                if (popular.length === 0) {
                    popularList.innerHTML = '<div class="text-slate-400 text-center py-4">No module data yet.</div>';
                } else {
                    popularList.innerHTML = popular.map((p, idx) => `
                        <div class="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-200/70 text-xs">
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="w-5 h-5 rounded-full bg-slate-200 text-slate-700 font-bold flex items-center justify-center text-[10px] shrink-0 font-mono">${idx + 1}</span>
                                <span class="font-bold text-slate-800 truncate">${p.page}</span>
                            </div>
                            <span class="font-mono font-bold text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-md text-[11px] shrink-0">${p.count} views</span>
                        </div>
                    `).join('');
                }
            }

            // 5. Render Sessions Table
            if (tableBody) {
                const sessions = sessionsData.sessions || [];
                if (sessions.length === 0) {
                    tableBody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-slate-400">No matching visitor sessions recorded yet.</td></tr>`;
                } else {
                    tableBody.innerHTML = sessions.map(s => {
                        const statusBadge = s.is_active
                            ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold border border-emerald-300"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span><span>Online</span></span>`
                            : `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-semibold border border-slate-200"><span>Idle</span></span>`;

                        const devIcon = s.device_type === 'Mobile' ? 'smartphone' : (s.device_type === 'Tablet' ? 'tablet' : 'laptop');
                        const pagesVisited = s.pages_visited || [];
                        const pagesHtml = pagesVisited.length > 0
                            ? pagesVisited.slice(-4).map(p => `<span class="inline-block px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200/80 text-[10px] font-medium mr-1 mb-1">${p}</span>`).join('')
                            : `<span class="text-slate-400">—</span>`;

                        return `
                            <tr class="hover:bg-slate-50 transition border-b border-slate-100 ${s.is_active ? 'bg-emerald-50/20' : ''}">
                                <td class="py-2.5 px-3 whitespace-nowrap">${statusBadge}</td>
                                <td class="py-2.5 px-3 font-mono font-bold text-wbblue-900 whitespace-nowrap">${s.ip_address}</td>
                                <td class="py-2.5 px-4">
                                    <div class="font-bold text-slate-900">${s.city}${s.region ? `, ${s.region}` : ''}</div>
                                    <div class="text-[10px] text-slate-500">${s.country}</div>
                                </td>
                                <td class="py-2.5 px-3 whitespace-nowrap">
                                    <div class="flex items-center gap-1.5 font-medium text-slate-800 text-xs">
                                        <i data-lucide="${devIcon}" class="w-3.5 h-3.5 text-slate-500"></i>
                                        <span>${s.device_type}</span>
                                    </div>
                                    <div class="text-[10px] font-mono text-slate-500">${s.os} • ${s.browser}</div>
                                </td>
                                <td class="py-2.5 px-3 font-mono font-bold text-purple-900 whitespace-nowrap">
                                    ${formatDuration(s.total_time_seconds)}
                                </td>
                                <td class="py-2.5 px-4 max-w-xs">
                                    <div class="flex flex-wrap">${pagesHtml}</div>
                                </td>
                                <td class="py-2.5 px-3 text-right font-mono text-[11px] text-slate-500 whitespace-nowrap">
                                    ${timeAgo(s.last_seen)}
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            if (window.lucide) lucide.createIcons();
        } catch (err) {
            console.error('Error loading visitor analytics:', err);
        }
    }

    function openVisitorAnalyticsModal() {
        const modal = document.getElementById('visitorAnalyticsModal');
        if (modal) {
            modal.classList.remove('hidden');
            loadVisitorAnalytics();
            if (analyticsRefreshInterval) clearInterval(analyticsRefreshInterval);
            analyticsRefreshInterval = setInterval(loadVisitorAnalytics, 10000);
            if (window.lucide) lucide.createIcons();
        }
    }

    function closeVisitorAnalyticsModal() {
        const modal = document.getElementById('visitorAnalyticsModal');
        if (modal) {
            modal.classList.add('hidden');
            if (analyticsRefreshInterval) {
                clearInterval(analyticsRefreshInterval);
                analyticsRefreshInterval = null;
            }
        }
    }

    function initVisitorAnalyticsUI() {
        const btnOpenHeader = document.getElementById('btnOpenTrafficAnalytics');
        if (btnOpenHeader) btnOpenHeader.addEventListener('click', openVisitorAnalyticsModal);

        const btnOpenDrawer = document.getElementById('btnDrawerTrafficAnalytics');
        if (btnOpenDrawer) {
            btnOpenDrawer.addEventListener('click', () => {
                const mobileDrawer = document.getElementById('mobileDrawerModal');
                if (mobileDrawer) mobileDrawer.classList.add('hidden');
                openVisitorAnalyticsModal();
            });
        }

        const btnFooterSecret = document.getElementById('btnFooterSecretTraffic');
        if (btnFooterSecret) btnFooterSecret.addEventListener('click', openVisitorAnalyticsModal);

        // Optional discrete admin shortcut: Alt+Shift+T
        window.addEventListener('keydown', (e) => {
            if (e.altKey && e.shiftKey && (e.key === 'T' || e.key === 't')) {
                e.preventDefault();
                openVisitorAnalyticsModal();
            }
        });

        const btnClose = document.getElementById('btnCloseVisitorAnalytics');
        if (btnClose) btnClose.addEventListener('click', closeVisitorAnalyticsModal);

        const btnRefresh = document.getElementById('btnRefreshAnalytics');
        if (btnRefresh) btnRefresh.addEventListener('click', loadVisitorAnalytics);

        const btnClear = document.getElementById('btnClearAnalytics');
        if (btnClear) {
            btnClear.addEventListener('click', async () => {
                if (confirm('Are you sure you want to reset all visitor and access logs?')) {
                    await fetch('/api/analytics/clear', { method: 'POST' });
                    loadVisitorAnalytics();
                }
            });
        }

        const modal = document.getElementById('visitorAnalyticsModal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) closeVisitorAnalyticsModal();
            });
        }

        const searchInput = document.getElementById('analyticsSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', debounce(loadVisitorAnalytics, 300));
        }

        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeVisitorAnalyticsModal();
        });
    }

    window.openVisitorAnalyticsModal = openVisitorAnalyticsModal;
    window.closeVisitorAnalyticsModal = closeVisitorAnalyticsModal;
    window.loadVisitorAnalytics = loadVisitorAnalytics;
});
