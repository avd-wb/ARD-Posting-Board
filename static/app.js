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

    // --- INITIALIZATION ---
    initTabs();
    initOverview();
    initFilters();
    loadRoster();
    loadObliterated();
    loadCadre();
    loadOrders();
    loadDisplacedPool();
    initSimulationControls();
    initBackupManager();
    initShareModal();
    initAICopilot();

    // Debounce helper
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // --- TAB SWITCHING ---
    function initTabs() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                state.currentTab = targetTab;

                tabButtons.forEach(b => {
                    b.classList.remove('bg-wbblue-800', 'text-white');
                    b.classList.add('text-blue-200', 'hover:bg-wbblue-800/60');
                });
                btn.classList.add('bg-wbblue-800', 'text-white');
                btn.classList.remove('text-blue-200', 'hover:bg-wbblue-800/60');

                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.add('hidden'));
                const activeContent = document.getElementById(targetTab);
                if (activeContent) {
                    activeContent.classList.remove('hidden');
                }

                if (targetTab === 'tab-cascade') {
                    loadSimulationHistory();
                    loadCascadingBackfills();
                } else if (targetTab === 'tab-displaced') {
                    loadDisplacedPool();
                } else if (targetTab === 'tab-visual-grid') {
                    window.renderVisualGrid('visualGridBody', false, null);
                } else if (targetTab === 'tab-master-directory') {
                    loadMasterDirectory();
                }
            });
        });
    }

    // --- LOAD OVERVIEW KPIS ---
    async function initOverview() {
        try {
            const res = await fetch('/api/overview');
            const data = await res.json();
            state.overview = data;

            document.getElementById('kpiTotalPosts').innerText = Number(data.total_posts).toLocaleString();
            document.getElementById('badgeCadreTotal').innerText = Number(data.total_posts).toLocaleString();
            document.getElementById('kpiTotalVacancies').innerText = Number(data.total_vacancies).toLocaleString();
            document.getElementById('kpiVacantDD').innerText = Number(data.vacant_dd).toLocaleString();
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
            state.districts.forEach(d => {
                const opt = document.createElement('option');
                opt.value = d;
                opt.innerText = d;
                distSelect.appendChild(opt);
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

            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="10" class="py-8 text-center text-slate-400">No candidates match current criteria.</td></tr>`;
                return;
            }

            tbody.innerHTML = json.data.map(c => {
                const isAllotted = c.allotment_status === 'Allotted';
                const statusBadge = isAllotted
                    ? `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">Allotted</span>`
                    : `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">Pending</span>`;

                const dualBadge = c.is_dual_obliterated === 1
                    ? `<span class="px-1.5 py-0.2 ml-1 text-[9px] font-semibold bg-rose-100 text-rose-700 border border-rose-200 rounded">Memo 1808 Post</span>`
                    : '';

                const prefDisplay = (c.pref_1 && c.pref_1 !== '—')
                    ? `<div class="truncate max-w-xs text-[11px]"><span class="font-semibold text-slate-700">1:</span> ${c.pref_1}</div>`
                    : `<span class="text-slate-400 italic">No preference submitted</span>`;

                const dorBadge = c.service_ends
                    ? `<span class="font-mono text-slate-700 font-medium">${c.service_ends}</span>`
                    : `<span class="text-slate-400">-</span>`;

                let allotmentDisplay = `<span class="text-amber-700 font-medium">Pending DD Allotment</span>`;
                if (isAllotted) {
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
                                <button onclick="openDualAllotModal('${c.hrms_id}', 'roster')" class="px-2 py-1 text-xs font-semibold rounded bg-wbblue-50 text-wbblue-700 hover:bg-wbblue-100 border border-wbblue-200 transition" title="Manual Post Allotment">
                                    ${isAllotted ? 'Modify' : 'Allot'}
                                </button>
                                <button onclick="openAIAllotModal('${c.hrms_id}', 'roster')" class="px-2 py-1 text-xs font-bold rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-sm transition flex items-center gap-1" title="Automated AI Statutory Allotment">
                                    <i data-lucide="sparkles" class="w-3 h-3"></i>
                                    <span>AI Allot</span>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
            lucide.createIcons();
        } catch (e) {
            console.error('Error loading roster:', e);
            tbody.innerHTML = `<tr><td colspan="10" class="py-8 text-center text-rose-500">Failed to load roster candidates.</td></tr>`;
        }
    }

    document.getElementById('rosterCategoryFilter').addEventListener('change', loadRoster);
    document.getElementById('rosterStatusFilter').addEventListener('change', loadRoster);
    document.getElementById('rosterSearchInput').addEventListener('input', debounce(loadRoster, 300));

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

            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-slate-400">No obliterated post records found.</td></tr>`;
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
                                    <button onclick="openAIAllotModal('${o.hrms_id}', 'obliterated')" class="px-2 py-1 text-xs font-bold rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-sm transition flex items-center gap-1" title="Automated AI Statutory Rehabilitation">
                                        <i data-lucide="sparkles" class="w-3 h-3"></i>
                                        <span>AI Allot</span>
                                    </button>
                                </div>
                            `}
                        </td>
                    </tr>
                `;
            }).join('');
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

            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-slate-400">No cadre posts found matching filters.</td></tr>`;
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
                            ${!isVacant ? `
                                <div class="flex items-center justify-end gap-1.5">
                                    <button onclick="openDualAllotModal('${p.incumbent_hrms}', 'displaced')" class="px-2 py-1 text-[11px] font-medium rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition">
                                        Allot
                                    </button>
                                    <button onclick="openAIAllotModal('${p.incumbent_hrms}', 'displaced')" class="px-2 py-1 text-xs font-bold rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-sm transition flex items-center gap-1" title="Automated AI Placement">
                                        <i data-lucide="sparkles" class="w-3 h-3"></i>
                                        <span>AI Allot</span>
                                    </button>
                                </div>
                            ` : '-'}
                        </td>
                    </tr>
                `;
            }).join('');
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
        const cat = document.getElementById('ordersCategoryFilter').value;
        const search = document.getElementById('ordersSearchInput').value;

        let url = `/api/orders?category=${encodeURIComponent(cat)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        try {
            const res = await fetch(url);
            const json = await res.json();
            state.orders = json.data;

            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-slate-400">No official orders found.</td></tr>`;
                return;
            }

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
        } catch (e) {
            console.error('Error loading orders:', e);
            tbody.innerHTML = `<tr><td colspan="6" class="py-8 text-center text-rose-500">Failed to load orders.</td></tr>`;
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

        btnAutoSolve.addEventListener('click', triggerAutoSolve);
        btnRunSolverCascade.addEventListener('click', triggerAutoSolve);
        btnResetSim.addEventListener('click', triggerReset);
        btnResetCascade.addEventListener('click', triggerReset);
    }

    // --- DUAL ALLOTMENT MODAL LOGIC WITH DYNAMIC OPTION REDUCTION ---
    window.openDualAllotModal = async function(hrmsId, source) {
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
    });

    // Handle SU Post change and trigger collision warning
    document.getElementById('modalSUPostSelect').addEventListener('change', (e) => {
        const val = parseInt(e.target.value);
        const collisionAlert = document.getElementById('modalCollisionAlert');
        const collisionText = document.getElementById('modalCollisionText');

        if (!val) {
            collisionAlert.classList.add('hidden');
            return;
        }

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

    // --- BACKUP & RESTORE MANAGER LOGIC ---
    function initBackupManager() {
        const modal = document.getElementById('backupModal');
        const btnOpen = document.getElementById('btnOpenBackupModal');
        const btnClose = document.getElementById('btnCloseBackupModal');
        const btnCloseFooter = document.getElementById('btnCloseBackupFooter');
        const btnCreate = document.getElementById('btnCreateBackupNow');
        const inputTag = document.getElementById('inputBackupTag');
        const tbody = document.getElementById('backupTableBody');
        const countEl = document.getElementById('backupListCount');

        btnOpen.addEventListener('click', async () => {
            modal.classList.remove('hidden');
            await loadBackups();
        });

        btnClose.addEventListener('click', () => modal.classList.add('hidden'));
        btnCloseFooter.addEventListener('click', () => modal.classList.add('hidden'));

        async function loadBackups() {
            try {
                const res = await fetch('/api/backup/list');
                const json = await res.json();
                const list = json.backups || [];
                countEl.innerText = `${list.length} snapshots available`;

                if (list.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="4" class="py-6 text-center text-slate-400 text-xs">No backups found.</td></tr>`;
                    return;
                }

                tbody.innerHTML = list.map(b => {
                    const dateStr = b.created_at.split('T')[0] + ' ' + b.created_at.split('T')[1].slice(0, 8);
                    return `
                        <tr class="hover:bg-slate-50 transition">
                            <td class="py-2.5 px-3 font-mono text-[11px] text-slate-700">${dateStr}</td>
                            <td class="py-2.5 px-3 font-mono font-semibold text-slate-800 text-[11px]">${b.filename}</td>
                            <td class="py-2.5 px-2 font-mono text-[11px] text-slate-500">${b.size_mb} MB</td>
                            <td class="py-2.5 px-3 text-right">
                                <button onclick="restoreBackupSnapshot('${b.filename}')" class="px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 font-bold text-[10px] rounded transition">
                                    Restore
                                </button>
                            </td>
                        </tr>
                    `;
                }).join('');
            } catch (e) {
                console.error('Error loading backups:', e);
            }
        }

        btnCreate.addEventListener('click', async () => {
            const tag = inputTag.value.trim() || 'manual';
            try {
                const res = await fetch('/api/backup/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tag: tag })
                });
                const data = await res.json();
                if (data.success) {
                    alert(`Snapshot Created Successfully!\n\nFile: ${data.filename}\nSize: ${data.size_mb} MB`);
                    inputTag.value = '';
                    await loadBackups();
                } else {
                    alert('Backup error: ' + data.error);
                }
            } catch (e) {
                alert('Failed to create backup: ' + e.message);
            }
        });

        window.restoreBackupSnapshot = async function(filename) {
            if (!confirm(`Are you sure you want to rollback to snapshot:\n${filename}?\n\nCurrent state will be automatically backed up before rollback.`)) {
                return;
            }
            try {
                const res = await fetch('/api/backup/restore', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filename: filename })
                });
                const data = await res.json();
                if (data.success) {
                    alert(`Rollback Complete!\n\nDatabase has been restored from ${filename}.\nSafety backup taken before restore: ${data.safety_copy}`);
                    modal.classList.add('hidden');
                    await initOverview();
                    await loadRoster();
                    await loadObliterated();
                    await loadCadre();
                    await loadSimulationHistory();
                } else {
                    alert('Rollback error: ' + data.error);
                }
            } catch (e) {
                alert('Rollback failed: ' + e.message);
            }
        };
    }

    // --- SHARE ONLINE MODAL LOGIC ---
    function initShareModal() {
        const modal = document.getElementById('shareModal');
        const btnOpen = document.getElementById('btnOpenShareModal');
        const btnClose = document.getElementById('btnCloseShareModal');
        const btnCloseFooter = document.getElementById('btnCloseShareFooter');

        btnOpen.addEventListener('click', () => modal.classList.remove('hidden'));
        btnClose.addEventListener('click', () => modal.classList.add('hidden'));
        btnCloseFooter.addEventListener('click', () => modal.classList.add('hidden'));
    }

    // --- AI COPILOT INTERACTION ---
    function initAICopilot() {
        const btnToggle = document.getElementById('btnToggleAIChat');
        const drawer = document.getElementById('aiDrawer');
        const btnClose = document.getElementById('btnCloseAIDrawer');
        const form = document.getElementById('aiChatForm');
        const input = document.getElementById('aiInputText');
        const messages = document.getElementById('aiMessages');

        btnToggle.addEventListener('click', () => {
            drawer.classList.toggle('translate-x-full');
        });
        btnClose.addEventListener('click', () => {
            drawer.classList.add('translate-x-full');
        });

        document.querySelectorAll('.ai-quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                input.value = btn.innerText.trim();
                form.dispatchEvent(new Event('submit'));
            });
        });

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = input.value.trim();
            if (!text) return;

            // Append user message
            messages.innerHTML += `
                <div class="flex justify-end">
                    <div class="bg-indigo-600 text-white rounded-xl rounded-tr-none px-3.5 py-2 max-w-[85%] text-xs shadow-sm">
                        ${text}
                    </div>
                </div>
            `;
            input.value = '';
            messages.scrollTop = messages.scrollHeight;

            // Append typing indicator
            const typingId = 'typing-' + Date.now();
            messages.innerHTML += `
                <div id="${typingId}" class="flex justify-start">
                    <div class="bg-slate-100 text-slate-600 rounded-xl rounded-tl-none px-3 py-2 text-xs flex items-center gap-1.5 border border-slate-200">
                        <span class="animate-bounce">●</span>
                        <span class="animate-bounce [animation-delay:0.2s]">●</span>
                        <span class="animate-bounce [animation-delay:0.4s]">●</span>
                    </div>
                </div>
            `;
            messages.scrollTop = messages.scrollHeight;

            try {
                const res = await fetch('/api/ai/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: text })
                });
                const data = await res.json();
                document.getElementById(typingId)?.remove();

                const formatted = data.response
                    .replace(/### (.*)/g, '<div class="font-bold text-slate-800 text-xs mt-1 mb-0.5">$1</div>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/`([^`]+)`/g, '<code class="bg-indigo-50 text-indigo-700 px-1 py-0.2 rounded font-mono text-[10px]">$1</code>')
                    .replace(/- (.*)/g, '<div class="text-[11px] text-slate-700 my-0.5 leading-tight">• $1</div>')
                    .replace(/\n/g, '<br>');

                messages.innerHTML += `
                    <div class="flex justify-start">
                        <div class="bg-white border border-slate-200 text-slate-800 rounded-xl rounded-tl-none px-3.5 py-2.5 max-w-[90%] text-xs shadow-sm space-y-1">
                            ${formatted}
                        </div>
                    </div>
                `;
                messages.scrollTop = messages.scrollHeight;
                lucide.createIcons();
            } catch (err) {
                document.getElementById(typingId)?.remove();
                messages.innerHTML += `
                    <div class="text-rose-500 text-xs p-2">Failed to get AI response.</div>
                `;
            }
        });
    }

    // --- TAB 6: LOAD DISPLACED OFFICERS POOL ---
    async function loadDisplacedPool() {
        const tbody = document.getElementById('displacedTableBody');
        const badge = document.getElementById('displacedPoolStatusBadge');
        const navBadge = document.getElementById('badgeDisplacedCount');

        try {
            const res = await fetch('/api/displaced-pool?session_id=CURRENT_SESSION');
            const json = await res.json();
            const pool = json.data || [];

            if (navBadge) navBadge.innerText = pool.length;
            if (badge) badge.innerText = `${pool.length} Displaced Officers Pending Placement`;

            if (pool.length === 0) {
                tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-slate-400">No officers currently displaced. Displaced officers from Service Utilization allotments will queue here automatically.</td></tr>`;
                return;
            }

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
                                <button onclick="openAIAllotModal('${o.officer_hrms}', 'displaced')" class="px-2 py-1 text-xs font-bold rounded bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-sm transition flex items-center gap-1">
                                    <i data-lucide="sparkles" class="w-3 h-3"></i>
                                    <span>AI Allot</span>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
            lucide.createIcons();
        } catch (e) {
            console.error('Error loading displaced pool:', e);
            tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-rose-500">Failed to load displaced pool.</td></tr>`;
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
    const kpiTotalCard = document.getElementById('kpiCardTotalPosts');
    if (kpiTotalCard) {
        kpiTotalCard.addEventListener('click', window.openWaterfallModal);
    }

    // --- OFFICER PERSONNEL DOSSIER MODAL LOGIC ---
    // --- OFFICER PERSONNEL DOSSIER & DISTRICT POST VISUALIZER ---
    window.activeDossierOfficer = null;

    window.switchDossierSubTab = function(tabName) {
        const tabs = ['profile', 'history', 'family', 'grid'];
        tabs.forEach(t => {
            const btn = document.getElementById(`dossierSubTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
            const sec = document.getElementById(`dossierSec${t.charAt(0).toUpperCase() + t.slice(1)}`);
            if (btn) {
                if (t === tabName) {
                    btn.className = "dossier-tab-btn px-3 py-2 border-b-2 border-wbblue-700 text-wbblue-800 font-bold flex items-center gap-1.5 transition";
                } else {
                    btn.className = "dossier-tab-btn px-3 py-2 text-slate-500 hover:text-slate-800 flex items-center gap-1.5 transition";
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

            subtitle.innerText = `${d.officer_name} | HRMS: ${d.hrms_id} | ${d.source_category}`;

            btnAI.onclick = () => {
                modal.classList.add('hidden');
                openAIAllotModal(d.hrms_id, 'roster');
            };

            const prefEntries = Object.entries(d.preferences || {});
            const prefsHtml = prefEntries.length > 0 
                ? prefEntries.map(([k, v]) => `<div class="text-[11px]"><strong class="text-slate-700">${k.replace('_', ' ')}:</strong> ${v}</div>`).join('')
                : (d.preferences_summary ? `<div class="text-[11px] text-slate-700">${d.preferences_summary}</div>` : `<span class="italic text-slate-400">No preference recorded</span>`);

            // Parse posting history into timeline items
            const historyRaw = d.posting_history || "Standard service tenure across departmental postings.";
            const historyItems = historyRaw.split(/(?=\d+\))/).map(s => s.trim()).filter(Boolean);
            const historyTimelineHtml = historyItems.length > 0
                ? historyItems.map(item => `
                    <div class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-50 border border-slate-200">
                        <div class="mt-0.5 w-6 h-6 rounded-full bg-wbblue-100 text-wbblue-800 flex items-center justify-center font-bold text-[10px] shrink-0">
                            <i data-lucide="map-pin" class="w-3 h-3 text-wbblue-700"></i>
                        </div>
                        <div class="text-xs text-slate-800 font-medium leading-relaxed">${item}</div>
                    </div>
                `).join('')
                : `<div class="p-3 bg-slate-50 rounded border text-slate-600">${historyRaw}</div>`;

            container.innerHTML = `
                <!-- TAB 1: SERVICE & PERSONAL PROFILE -->
                <div id="dossierSecProfile" class="dossier-sec space-y-4">
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

                    <!-- Identity & Contacts Grid -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 p-3.5 rounded-lg bg-slate-50 border border-slate-200">
                        <div class="md:col-span-2">
                            <div class="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Officer Name & Registration</div>
                            <div class="text-base font-bold text-slate-900 flex items-center gap-2">
                                <span>${d.officer_name}</span>
                                ${d.caste ? `<span class="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-200 text-slate-800">${d.caste}</span>` : ''}
                            </div>
                            <div class="text-[11px] font-mono text-wbblue-700 font-bold mt-0.5">
                                HRMS ID: ${d.hrms_id} ${d.wbvc_reg_no && d.wbvc_reg_no !== '—' ? `| WBVC Reg: ${d.wbvc_reg_no}` : ''}
                            </div>
                        </div>
                        <div class="space-y-0.5 text-[11px] border-t md:border-t-0 md:border-l border-slate-200 md:pl-3">
                            <div><strong class="text-slate-600">Mobile:</strong> <span class="font-mono text-slate-800">${d.mobile}</span></div>
                            <div><strong class="text-slate-600">Email:</strong> <span class="text-slate-800">${d.email}</span></div>
                            <div><strong class="text-slate-600">WhatsApp:</strong> <span class="font-mono text-slate-800">${d.whatsapp}</span></div>
                        </div>
                    </div>

                    <!-- Dates of Service & WBSR Rule 75(a) -->
                    <div class="grid grid-cols-3 gap-2 p-3 rounded-lg bg-blue-50/50 border border-blue-200 text-center">
                        <div>
                            <div class="text-[10px] text-blue-700 font-semibold">Date of Birth (DOB)</div>
                            <div class="text-xs font-bold text-slate-900 font-mono">${d.dob}</div>
                        </div>
                        <div>
                            <div class="text-[10px] text-blue-700 font-semibold">Date of Joining (DOJ)</div>
                            <div class="text-xs font-bold text-slate-900 font-mono">${d.doj}</div>
                        </div>
                        <div>
                            <div class="text-[10px] text-blue-700 font-semibold">Superannuation (DOR)</div>
                            <div class="text-xs font-bold text-rose-700 font-mono">${d.dor}</div>
                            <div class="text-[9px] text-blue-600 font-medium">Rule 75(a) Compliant</div>
                        </div>
                    </div>

                    <!-- Present Posting & Pay Details -->
                    <div class="p-3.5 rounded-lg border border-slate-200 bg-white space-y-2">
                        <div class="font-bold text-slate-800 flex items-center justify-between">
                            <span>Present Posting & Pay Details</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${d.tenure_norm_status === 'Yes' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'}">
                                ${d.tenure_norm_status === 'Yes' ? 'Tenure Over (>4/5y)' : 'Within Tenure Norm'}
                            </span>
                        </div>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <div><strong class="text-slate-600">Designation:</strong> ${d.current_designation}</div>
                            <div><strong class="text-slate-600">Station/Office:</strong> ${d.establishment}</div>
                            <div><strong class="text-slate-600">Block / District:</strong> ${d.block ? `${d.block}, ` : ''}${d.district}</div>
                            <div><strong class="text-slate-600">Station Tenure:</strong> ${d.tenure_years} yrs</div>
                            <div><strong class="text-slate-600">Office Code:</strong> <span class="font-mono">${d.office_code}</span></div>
                            <div><strong class="text-slate-600">DDO Code:</strong> <span class="font-mono">${d.ddo_code}</span></div>
                            <div class="col-span-2"><strong class="text-slate-600">Present Scale:</strong> ${d.present_pay_level}</div>
                            <div class="col-span-2"><strong class="text-slate-600">Cadre:</strong> ${d.cadre}</div>
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
                            </div>
                        </div>
                        <div>
                            <div class="font-bold text-slate-700 flex items-center gap-1 mb-1">
                                <i data-lucide="building" class="w-3.5 h-3.5 text-slate-500"></i>
                                <span>Current Residential Address</span>
                            </div>
                            <div class="text-[11px] text-slate-800 bg-white p-2 rounded border border-slate-200 leading-relaxed">
                                ${d.current_address}
                            </div>
                        </div>
                    </div>

                    <!-- Stated Preferences -->
                    <div class="p-3 rounded-lg border border-slate-200 bg-slate-50 space-y-1.5">
                        <div class="font-bold text-slate-800">Officer Stated Preferences (1 - 10)</div>
                        <div class="grid grid-cols-2 gap-1 bg-white p-2 rounded border border-slate-200 max-h-32 overflow-y-auto">
                            ${prefsHtml}
                        </div>
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
                    ` : `
                        <div class="p-2.5 rounded bg-slate-100 text-slate-600 text-center italic text-xs">
                            No posting decision simulated yet. Officer is awaiting placement.
                        </div>
                    `}
                </div>

                <!-- TAB 2: POSTING HISTORY TIMELINE -->
                <div id="dossierSecHistory" class="dossier-sec hidden space-y-3">
                    <div class="p-3 bg-blue-50/60 border border-blue-200 rounded-lg text-xs text-blue-900">
                        <strong>Complete Career Posting Record:</strong> Historical postings, transfers, and tenures recorded across state establishments.
                    </div>
                    <div class="space-y-2 max-h-[450px] overflow-y-auto p-1">
                        ${historyTimelineHtml}
                    </div>
                </div>

                <!-- TAB 3: SPOUSE & FAMILY MATTER -->
                <div id="dossierSecFamily" class="dossier-sec hidden space-y-4">
                    <div class="p-3.5 rounded-lg border border-amber-200 bg-amber-50/50 space-y-2">
                        <div class="font-bold text-amber-900 flex items-center gap-1.5">
                            <i data-lucide="heart-handshake" class="w-4 h-4 text-amber-700"></i>
                            <span>Spouse Service Matter & Co-location Safeguards (Memo 291)</span>
                        </div>
                        <div class="text-xs text-slate-800 bg-white p-2.5 rounded border border-amber-200">
                            ${d.spouse_service_details}
                        </div>
                    </div>

                    <div class="p-3.5 rounded-lg border border-slate-200 bg-white space-y-2">
                        <div class="font-bold text-slate-800 flex items-center gap-1.5">
                            <i data-lucide="shield" class="w-4 h-4 text-wbblue-700"></i>
                            <span>Family Dependencies & Medical Conditions</span>
                        </div>
                        <div class="text-xs text-slate-800 bg-slate-50 p-2.5 rounded border border-slate-200">
                            ${d.family_dependencies}
                        </div>
                    </div>

                    <div class="p-3.5 rounded-lg border border-slate-200 bg-white space-y-2">
                        <div class="font-bold text-slate-800 flex items-center gap-1.5">
                            <i data-lucide="graduation-cap" class="w-4 h-4 text-purple-700"></i>
                            <span>Academic Qualifications & Specializations</span>
                        </div>
                        <div class="text-xs text-slate-800 bg-slate-50 p-2.5 rounded border border-slate-200">
                            ${d.academic_details}
                        </div>
                    </div>
                </div>

                <!-- TAB 4: DISTRICT POST VISUALIZER & QUICK ALLOTMENT COCKPIT -->
                <div id="dossierSecGrid" class="dossier-sec hidden space-y-3">
                    <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between gap-3 text-xs">
                        <div class="text-emerald-950 font-medium">
                            <strong>Interactive Allocation Cockpit:</strong> Click any post button below to allot directly to <strong>${d.officer_name}</strong> as Substantive Main or Service Utilization (SU).
                        </div>
                    </div>

                    <div id="modalVisualGridContainer" class="space-y-4 max-h-[500px] overflow-y-auto p-1">
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

    // --- DISTRICT POST VISUALIZER GRID COMPONENT ---
    window.renderVisualGrid = async function(containerId, isModal = false, targetHrmsId = null) {
        const container = document.getElementById(containerId);
        if (!container) return;

        try {
            const res = await fetch('/api/posts/visual-grid');
            if (!res.ok) throw new Error('Failed to load visual grid data');
            const data = await res.json();

            // Update main legend counts if available
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

            // Populate district filter options if main filter exists
            const distFilter = document.getElementById('visualGridDistrictFilter');
            if (distFilter && distFilter.options.length <= 1) {
                data.districts.forEach(d => {
                    const opt = document.createElement('option');
                    opt.value = d;
                    opt.textContent = d;
                    distFilter.appendChild(opt);
                });
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

            // Render district sections with post buttons
            let html = '';
            data.grid.forEach(distGroup => {
                const dName = distGroup.district;
                const ddPosts = distGroup.dd_posts || [];
                const cadrePosts = distGroup.cadre_posts || [];
                const totalInDist = ddPosts.length + cadrePosts.length;

                const renderButton = (p) => {
                    let btnColorClass = "bg-slate-500 text-white hover:bg-slate-600";
                    if (p.status_code === 'VACANT_PURE') {
                        btnColorClass = "bg-emerald-500 text-white hover:bg-emerald-600 font-bold";
                    } else if (p.status_code === 'VACANT_ON_PAPER') {
                        btnColorClass = "bg-amber-500 text-white hover:bg-amber-600 font-medium";
                    } else if (p.status_code === 'ATTENTION_REQUIRED') {
                        btnColorClass = "bg-rose-500 text-white hover:bg-rose-600 font-bold animate-pulse";
                    } else if (p.status_code === 'BOARD_SELECTED') {
                        btnColorClass = "bg-purple-600 text-white hover:bg-purple-700 font-medium";
                    } else if (p.status_code === 'OBLITERATED') {
                        btnColorClass = "bg-slate-300 text-slate-700 line-through border border-slate-400 opacity-60";
                    }

                    const clickHandler = isModal && targetHrmsId
                        ? `onclick="window.promptPostAllotment('${p.id}', ${p.raw_id}, '${p.type}', '${p.post_name.replace(/'/g, "\\'")}', '${targetHrmsId}')"`
                        : `onclick="showToast('${p.id}: ${p.post_name} - ${p.status_label}', 'info')"`;

                    return `
                        <button ${clickHandler} 
                                class="px-2 py-1 text-[10px] rounded border border-black/10 shadow-sm transition truncate max-w-[175px] text-left flex items-center justify-between gap-1 ${btnColorClass}"
                                title="${p.id} | ${p.designation} (${p.establishment}${p.block ? `, ${p.block}` : ''}) | ${p.status_label}">
                            <span class="truncate">${p.id}: ${p.designation}</span>
                            <span class="w-1.5 h-1.5 rounded-full bg-white shrink-0"></span>
                        </button>
                    `;
                };

                html += `
                    <div class="district-grid-card bg-white rounded-lg border border-slate-200 p-3.5 shadow-sm space-y-2.5" data-district="${dName}">
                        <div class="flex items-center justify-between border-b border-slate-200 pb-2">
                            <div class="font-bold text-slate-800 text-xs flex items-center gap-2">
                                <i data-lucide="map-pin" class="w-3.5 h-3.5 text-wbblue-700"></i>
                                <span>${dName}</span>
                                <span class="px-2 py-0.2 rounded-full bg-slate-100 text-slate-600 font-normal text-[10px]">${totalInDist} posts</span>
                            </div>
                            <div class="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono">
                                <span>DD: ${ddPosts.length}</span> | <span>Cadre: ${cadrePosts.length}</span>
                            </div>
                        </div>

                        ${ddPosts.length > 0 ? `
                            <div>
                                <div class="text-[10px] font-bold text-wbblue-800 uppercase tracking-wider mb-1 flex items-center gap-1">
                                    <i data-lucide="award" class="w-3 h-3 text-wbblue-700"></i>
                                    <span>Deputy Director Posts (Pay Level 19)</span>
                                </div>
                                <div class="flex flex-wrap gap-1.5">
                                    ${ddPosts.map(renderButton).join('')}
                                </div>
                            </div>
                        ` : ''}

                        ${cadrePosts.length > 0 ? `
                            <div>
                                <div class="text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1 flex items-center gap-1">
                                    <i data-lucide="building-2" class="w-3 h-3 text-slate-500"></i>
                                    <span>Cadre Posts (AD / BLDO / VO)</span>
                                </div>
                                <div class="flex flex-wrap gap-1.5">
                                    ${cadrePosts.map(renderButton).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `;
            });

            container.innerHTML = html;
            lucide.createIcons();
        } catch (err) {
            console.error('Failed to render visual grid:', err);
            container.innerHTML = `<div class="py-8 text-center text-rose-500 font-medium">Failed to load posts grid: ${err.message}</div>`;
        }
    };

    // --- QUICK ALLOTMENT PROMPT FROM VISUAL GRID ---
    window.promptPostAllotment = async function(postId, rawId, postType, postName, targetHrmsId) {
        const off = window.activeDossierOfficer;
        if (!off) return;

        const choice = confirm(
            `ALLOT POST TO: ${off.officer_name} (HRMS: ${targetHrmsId})\n\n` +
            `Target Post: [${postId}] ${postName}\n\n` +
            `Click OK to allot as SUBSTANTIVE MAIN POST (Pay Level 19)\n` +
            `Click CANCEL to allot as SERVICE UTILIZATION (SU) POST`
        );

        const isSubstantive = choice;
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
                    reason: isSubstantive ? "Substantive Main Allotment via District Visual Grid" : "Service Utilization Allotment via District Visual Grid",
                    officer_type: "roster"
                })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Successfully allotted [${postId}] to ${off.officer_name}!`, 'success');
                // Reload dossier and roster table
                window.openOfficerDossier(targetHrmsId);
                loadRoster();
                loadSimulationHistory();
            } else {
                showToast(data.error || 'Allotment failed', 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('Network error during allotment', 'error');
        }
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
        if (!tbody) return;

        tbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-slate-400">Loading master directory...</td></tr>';

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
                tbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-slate-400">No officers found matching search criteria.</td></tr>';
                return;
            }

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

            if (window.lucide) lucide.createIcons();

        } catch (err) {
            console.error('Error loading master directory:', err);
            tbody.innerHTML = `<tr><td colspan="7" class="py-8 text-center text-rose-500 font-semibold">Failed to load master directory: ${err.message}</td></tr>`;
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
});
