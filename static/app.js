const API = '';
let currentDomain = 'rh';
let currentView = 'dashboard';
let currentDashTab = 'overview';
let domains = {};
let dateStart = '';
let dateEnd = '';
let activePreset = '28d';
let socialPeriod = 'weekly';
let seoPeriod = 'weekly';
let ideaCat = 'all';
let repPeriod = 'weekly';

async function api(path, opts) {
    const resp = await fetch(`${API}${path}`, opts);
    if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`${resp.status}: ${text}`);
    }
    return resp.json();
}

function formatNum(n) {
    if (n === undefined || n === null) return '-';
    if (typeof n === 'number') {
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
        if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
        return n.toLocaleString();
    }
    return n;
}

function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function setDates(preset) {
    const today = new Date();
    const end = new Date(today - 86400000);
    const endStr = end.toISOString().split('T')[0];
    let startDate;
    switch (preset) {
        case '7d': startDate = new Date(end - 7 * 86400000); break;
        case '28d': startDate = new Date(end - 28 * 86400000); break;
        case '3m': startDate = new Date(end - 90 * 86400000); break;
        case '6m': startDate = new Date(end - 180 * 86400000); break;
        default: startDate = new Date(end - 28 * 86400000);
    }
    dateStart = startDate.toISOString().split('T')[0];
    dateEnd = endStr;
    const ds = document.getElementById('date-start'); if (ds) ds.value = dateStart;
    const de = document.getElementById('date-end'); if (de) de.value = dateEnd;
    activePreset = preset;
    document.querySelectorAll('[data-preset]').forEach(b => {
        b.classList.toggle('active', b.dataset.preset === preset);
    });
}

function showLoading(id) {
    const el = document.getElementById(id);
    if (el) { el.className = 'metric-value loading'; el.textContent = ''; }
}

function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<div class="error-msg">${esc(msg)}</div>`;
}

function renderMetric(id, value) {
    const el = document.getElementById(id);
    if (el) { el.className = 'metric-value'; el.textContent = formatNum(value); }
}

function renderTable(id, headers, rows) {
    const el = document.getElementById(id);
    if (!el) return;
    if (!rows || rows.length === 0) {
        el.innerHTML = '<div class="empty-state"><p>No data available</p></div>';
        return;
    }
    let html = '<table><thead><tr>';
    headers.forEach(h => html += `<th>${esc(h.label)}</th>`);
    html += '</tr></thead><tbody>';
    rows.forEach(r => {
        html += '<tr>';
        headers.forEach(h => {
            const val = r[h.key];
            const cls = h.key === 'page' || h.key === 'query' ? ' class="url"' : '';
            html += `<td${cls}>${formatNum(val)}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
}

// ── Charts ──
const charts = {};

function getThemeColors() {
    const s = getComputedStyle(document.documentElement);
    return {
        text: s.getPropertyValue('--text').trim() || '#1a1a2e',
        muted: s.getPropertyValue('--text-muted').trim() || '#666',
        border: s.getPropertyValue('--border').trim() || '#e2e8f0',
        accent: s.getPropertyValue('--accent').trim() || '#7C3AED',
        surface: s.getPropertyValue('--surface').trim() || '#fff',
    };
}

function makeChart(id, config) {
    if (charts[id]) { charts[id].destroy(); }
    const ctx = document.getElementById(id);
    if (!ctx) return null;
    const c = getThemeColors();
    config.options = config.options || {};
    config.options.responsive = true;
    config.options.maintainAspectRatio = false;
    config.options.plugins = config.options.plugins || {};
    config.options.plugins.legend = config.options.plugins.legend || {};
    config.options.plugins.legend.labels = { color: c.text, font: { family: 'Inter' } };
    if (config.options.scales) {
        Object.values(config.options.scales).forEach(s => {
            s.ticks = s.ticks || {};
            s.ticks.color = c.muted;
            s.ticks.font = { family: 'Inter', size: 11 };
            s.grid = s.grid || {};
            s.grid.color = c.border + '40';
        });
    }
    charts[id] = new Chart(ctx, config);
    return charts[id];
}

// ── Theme ──
function initTheme() {
    const saved = localStorage.getItem('rh-theme');
    applyTheme(saved === 'dark' ? 'dark' : 'light');
}
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('rh-theme', theme);
    const sun = document.getElementById('icon-sun');
    const moon = document.getElementById('icon-moon');
    if (sun && moon) {
        sun.style.display = theme === 'dark' ? 'none' : 'block';
        moon.style.display = theme === 'dark' ? 'block' : 'none';
    }
}
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
    Object.keys(charts).forEach(id => { if (charts[id]) charts[id].destroy(); delete charts[id]; });
}

// ── Views ──
function switchView(view) {
    currentView = view;
    ['dashboard', 'calendar', 'ideas', 'validator', 'reports', 'settings'].forEach(v => {
        const el = document.getElementById('view-' + v);
        if (el) el.style.display = v === view ? 'block' : 'none';
    });
    document.querySelectorAll('.sidebar-item').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
    const subtitles = {
        dashboard: 'Dashboard', calendar: 'Content Calendar', ideas: 'Creative Ideas',
        validator: 'Content Validator', reports: 'Reports & Analytics', settings: 'Settings'
    };
    const sub = document.getElementById('topbar-sub');
    if (sub) sub.textContent = subtitles[view] || 'Dashboard';
    if (view === 'ideas') markIdeasSeen();
}

function switchDashTab(tab) {
    currentDashTab = tab;
    document.querySelectorAll('[data-dash]').forEach(b => b.classList.toggle('active', b.dataset.dash === tab));
    document.querySelectorAll('.dash-section').forEach(s => s.style.display = 'none');
    const el = document.getElementById('dash-' + tab);
    if (el) el.style.display = 'block';
    if (tab === 'social') loadSocial();
    if (tab === 'youtube') loadYouTube();
    if (tab === 'seo') loadSEOWeekly();
    if (tab === 'meta') loadMeta();
}

// ── Data loading ──
async function loadGSC() {
    const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
    const overviewIds = ['gsc-clicks', 'gsc-impressions', 'gsc-ctr', 'gsc-position'];
    const detailIds = ['gsc-clicks-d', 'gsc-impressions-d', 'gsc-ctr-d', 'gsc-position-d'];
    [...overviewIds, ...detailIds].forEach(id => showLoading(id));
    try {
        const summary = await api(`/api/gsc/summary${qs}`);
        const vals = [summary.clicks, summary.impressions, summary.ctr + '%', summary.position];
        overviewIds.forEach((id, i) => renderMetric(id, vals[i]));
        detailIds.forEach((id, i) => renderMetric(id, vals[i]));
    } catch (e) {
        [...overviewIds, ...detailIds].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '—'; });
    }
    try {
        const queries = await api(`/api/gsc/queries${qs}&limit=15`);
        renderTable('gsc-queries-table', [
            { label: 'Query', key: 'query' }, { label: 'Clicks', key: 'clicks' },
            { label: 'Impressions', key: 'impressions' }, { label: 'CTR %', key: 'ctr' },
            { label: 'Position', key: 'position' },
        ], queries);
    } catch (e) { showError('gsc-queries-table', e.message); }
    try {
        const pages = await api(`/api/gsc/pages${qs}&limit=15`);
        renderTable('gsc-pages-table', [
            { label: 'Page', key: 'page' }, { label: 'Clicks', key: 'clicks' },
            { label: 'Impressions', key: 'impressions' }, { label: 'CTR %', key: 'ctr' },
            { label: 'Position', key: 'position' },
        ], pages);
    } catch (e) { showError('gsc-pages-table', e.message); }
    // Daily chart
    try {
        const daily = await api(`/api/gsc/daily${qs}`);
        makeChart('chart-gsc-daily', {
            type: 'line',
            data: {
                labels: daily.map(d => d.date),
                datasets: [
                    { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: '#7C3AED', backgroundColor: '#7C3AED20', fill: true, tension: 0.3, yAxisID: 'y' },
                    { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: '#0EA5E9', backgroundColor: '#0EA5E920', fill: true, tension: 0.3, yAxisID: 'y1' },
                ]
            },
            options: { scales: { y: { position: 'left' }, y1: { position: 'right', grid: { drawOnChartArea: false } } } }
        });
    } catch(e) {}
    // Queries bar chart
    try {
        const queries = await api(`/api/gsc/queries${qs}&limit=10`);
        makeChart('chart-gsc-queries', {
            type: 'bar',
            data: {
                labels: queries.map(q => q.query.length > 30 ? q.query.slice(0,27)+'...' : q.query),
                datasets: [
                    { label: 'Clicks', data: queries.map(q => q.clicks), backgroundColor: '#7C3AED90' },
                    { label: 'Impressions', data: queries.map(q => q.impressions), backgroundColor: '#0EA5E990' },
                ]
            },
            options: { indexAxis: 'y', scales: { x: {}, y: {} } }
        });
    } catch(e) {}
}

async function loadGA4() {
    const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
    const overviewIds = ['ga4-sessions', 'ga4-users', 'ga4-pageviews', 'ga4-bounce'];
    const detailIds = ['ga4-sessions-d', 'ga4-users-d', 'ga4-pageviews-d', 'ga4-bounce-d'];
    [...overviewIds, ...detailIds].forEach(id => showLoading(id));
    try {
        const summary = await api(`/api/ga4/summary${qs}`);
        const vals = [summary.sessions, summary.users, summary.pageviews, summary.bounce_rate + '%'];
        overviewIds.forEach((id, i) => renderMetric(id, vals[i]));
        detailIds.forEach((id, i) => renderMetric(id, vals[i]));
    } catch (e) {
        [...overviewIds, ...detailIds].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '—'; });
    }
    try {
        const sources = await api(`/api/ga4/sources${qs}`);
        renderTable('ga4-sources-table', [
            { label: 'Channel', key: 'channel' }, { label: 'Sessions', key: 'sessions' }, { label: 'Users', key: 'users' },
        ], sources);
    } catch (e) { showError('ga4-sources-table', e.message); }
    try {
        const pages = await api(`/api/ga4/pages${qs}&limit=15`);
        renderTable('ga4-pages-table', [
            { label: 'Page', key: 'page' }, { label: 'Views', key: 'views' },
            { label: 'Sessions', key: 'sessions' }, { label: 'Avg Duration', key: 'avg_dur' },
        ], pages);
    } catch (e) { showError('ga4-pages-table', e.message); }
    // Daily chart
    try {
        const daily = await api(`/api/ga4/daily${qs}`);
        makeChart('chart-ga4-daily', {
            type: 'line',
            data: {
                labels: daily.map(d => d.date),
                datasets: [
                    { label: 'Sessions', data: daily.map(d => d.sessions), borderColor: '#7C3AED', backgroundColor: '#7C3AED20', fill: true, tension: 0.3 },
                    { label: 'Users', data: daily.map(d => d.users), borderColor: '#10B981', backgroundColor: '#10B98120', fill: true, tension: 0.3 },
                ]
            },
            options: { scales: { x: {}, y: {} } }
        });
    } catch(e) {}
    // Sources doughnut
    try {
        const sources = await api(`/api/ga4/sources${qs}`);
        const colors = ['#7C3AED','#0EA5E9','#10B981','#F59E0B','#EF4444','#EC4899','#8B5CF6','#06B6D4','#84CC16','#F97316'];
        makeChart('chart-ga4-sources', {
            type: 'doughnut',
            data: {
                labels: sources.map(s => s.channel),
                datasets: [{ data: sources.map(s => s.sessions), backgroundColor: colors.slice(0, sources.length) }]
            },
            options: { plugins: { legend: { position: 'right' } } }
        });
    } catch(e) {}
}

async function loadMeta() {
    try {
        const status = await api('/api/meta/status');
        if (!status.marketing) {
            const el = document.getElementById('meta-overview');
            if (el) el.innerHTML = '<div class="empty-state"><p>Meta Marketing API not connected</p></div>';
            const t = document.getElementById('meta-campaigns-table');
            if (t) t.innerHTML = '<div class="empty-state"><p>Meta Marketing API not connected</p></div>';
            return;
        }
        const accounts = await api('/api/meta/accounts');
        if (!accounts || accounts.length === 0) return;
        const acctId = accounts[0].id;
        const qs = `?ad_account=${acctId}&start=${dateStart}&end=${dateEnd}`;
        const campaigns = await api(`/api/meta/campaigns${qs}`);
        renderTable('meta-campaigns-table', [
            { label: 'Campaign', key: 'name' }, { label: 'Status', key: 'status' },
            { label: 'Spend', key: 'spend' }, { label: 'Impressions', key: 'impressions' },
            { label: 'Reach', key: 'reach' }, { label: 'Clicks', key: 'clicks' }, { label: 'CTR %', key: 'ctr' },
        ], campaigns);
        const overview = document.getElementById('meta-overview');
        if (overview && campaigns && campaigns.length > 0) {
            const totalSpend = campaigns.reduce((s, c) => s + (parseFloat(c.spend) || 0), 0);
            const totalClicks = campaigns.reduce((s, c) => s + (parseInt(c.clicks) || 0), 0);
            const totalImpressions = campaigns.reduce((s, c) => s + (parseInt(c.impressions) || 0), 0);
            overview.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-card"><div class="accent-strip" style="background:#7C3AED"></div><div class="metric-label">Total Spend</div><div class="metric-value">$${totalSpend.toFixed(2)}</div></div>
                    <div class="metric-card"><div class="accent-strip" style="background:#0EA5E9"></div><div class="metric-label">Clicks</div><div class="metric-value">${formatNum(totalClicks)}</div></div>
                    <div class="metric-card"><div class="accent-strip" style="background:#10B981"></div><div class="metric-label">Impressions</div><div class="metric-value">${formatNum(totalImpressions)}</div></div>
                    <div class="metric-card"><div class="accent-strip" style="background:#F59E0B"></div><div class="metric-label">Campaigns</div><div class="metric-value">${campaigns.length}</div></div>
                </div>`;
        }
        // Campaign performance chart
        try {
            if (campaigns && campaigns.length) {
                makeChart('chart-meta-campaigns', {
                    type: 'bar',
                    data: {
                        labels: campaigns.map(c => (c.name||'').slice(0,25)),
                        datasets: [
                            { label: 'Spend', data: campaigns.map(c => parseFloat(c.spend) || 0), backgroundColor: '#7C3AED90' },
                            { label: 'Clicks', data: campaigns.map(c => parseInt(c.clicks) || 0), backgroundColor: '#0EA5E990' },
                        ]
                    },
                    options: { scales: { x: {}, y: {} } }
                });
            }
        } catch(e) {}
    } catch (e) {
        showError('meta-overview', e.message);
    }
}

function switchSocialPeriod(period) {
    socialPeriod = period;
    document.querySelectorAll('[data-social-period]').forEach(b => b.classList.toggle('active', b.dataset.socialPeriod === period));
    loadSocial();
}

function switchSEOPeriod(period) {
    seoPeriod = period;
    document.querySelectorAll('[data-seo-period]').forEach(b => b.classList.toggle('active', b.dataset.seoPeriod === period));
    const title = document.getElementById('seo-title');
    if (title) title.textContent = `SEO ${period === 'weekly' ? 'Weekly' : 'Monthly'} Performance — ${period === 'weekly' ? '5 Week' : '5 Month'} Trend`;
    loadSEOWeekly();
}

const socialMetricsDef = [
    { label: 'Followers / Page Likes', fb: 'followers', ig: 'followers' },
    { label: 'New Followers (net)', fb: 'new_followers', ig: 'new_followers' },
    { label: 'Reach', fb: 'reach', ig: 'reach' },
    { label: 'Views', fb: 'views', ig: 'views' },
    { label: 'Engagements (total)', fb: 'engagements', ig: 'engagements' },
    { label: 'Engagement Rate (%)', fb: 'engagement_rate', ig: 'engagement_rate' },
    { label: 'Posts Published', fb: 'posts_published', ig: 'posts_published' },
    { label: 'Stories / Reels', fb: 'reels_stories', ig: 'reels_stories' },
    { label: 'Video Views', fb: 'video_views', ig: 'video_views' },
    { label: 'Link Clicks', fb: 'link_clicks', ig: 'link_clicks' },
    { label: 'Profile Visits / Page Views', fb: 'profile_visits', ig: 'profile_views' },
    { label: 'Saves / Shares', fb: 'saves_shares', ig: 'saves_shares' },
];

async function loadSocial() {
    const tableEl = document.getElementById('social-metrics-table');
    if (!tableEl) return;
    tableEl.innerHTML = '<div class="empty-state"><p>Loading social media data...</p></div>';
    try {
        const data = await api(`/api/social/trend?period=${socialPeriod}&periods=5`);
        if (!data || data.length === 0) {
            tableEl.innerHTML = '<div class="empty-state"><p>No social data available</p></div>';
            return;
        }
        let html = '<table><thead><tr><th style="width:30%">Metric</th>';
        data.forEach(p => html += `<th style="text-align:center; font-size:0.7rem;">${esc(p.period)}</th>`);
        html += '</tr></thead><tbody>';
        html += `<tr><td colspan="${data.length + 1}" style="background:rgba(232,64,95,0.08); font-weight:800; font-size:0.7rem; letter-spacing:0.08em; color:#E4405F; padding:0.5rem 1rem;">INSTAGRAM</td></tr>`;
        socialMetricsDef.forEach(m => {
            html += `<tr><td style="font-weight:600;">${m.label}</td>`;
            data.forEach(p => {
                const val = p.ig && p.ig[m.ig] !== undefined ? p.ig[m.ig] : '-';
                html += `<td style="text-align:center;">${formatNum(val)}</td>`;
            });
            html += '</tr>';
        });
        html += `<tr><td colspan="${data.length + 1}" style="background:rgba(24,119,242,0.08); font-weight:800; font-size:0.7rem; letter-spacing:0.08em; color:#1877F2; padding:0.5rem 1rem;">FACEBOOK</td></tr>`;
        socialMetricsDef.forEach(m => {
            html += `<tr><td style="font-weight:600;">${m.label}</td>`;
            data.forEach(p => {
                const val = p.fb && p.fb[m.fb] !== undefined ? p.fb[m.fb] : '-';
                html += `<td style="text-align:center;">${formatNum(val)}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        tableEl.innerHTML = html;
        // FB trend chart
        try {
            makeChart('chart-fb-trend', {
                type: 'bar',
                data: {
                    labels: data.map(p => p.period),
                    datasets: [
                        { label: 'Reach', data: data.map(p => (p.fb && p.fb.reach) || 0), backgroundColor: '#1877F290' },
                        { label: 'Engagements', data: data.map(p => (p.fb && p.fb.engagements) || 0), backgroundColor: '#0EA5E990' },
                        { label: 'Views', data: data.map(p => (p.fb && p.fb.views) || 0), backgroundColor: '#10B98190' },
                    ]
                },
                options: { scales: { x: {}, y: {} } }
            });
        } catch(e) {}
        // IG trend chart
        try {
            makeChart('chart-ig-trend', {
                type: 'bar',
                data: {
                    labels: data.map(p => p.period),
                    datasets: [
                        { label: 'Reach', data: data.map(p => (p.ig && p.ig.reach) || 0), backgroundColor: '#E4405F90' },
                        { label: 'Engagements', data: data.map(p => (p.ig && p.ig.engagements) || 0), backgroundColor: '#7C3AED90' },
                        { label: 'Views', data: data.map(p => (p.ig && p.ig.views) || 0), backgroundColor: '#F59E0B90' },
                    ]
                },
                options: { scales: { x: {}, y: {} } }
            });
        } catch(e) {}
    } catch (e) {
        tableEl.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
    }
    try {
        const posts = await api(`/api/social/page-posts?start=${dateStart}&end=${dateEnd}`);
        renderTable('fb-posts-table', [
            { label: 'Post', key: 'message' }, { label: 'Impressions', key: 'post_impressions' },
            { label: 'Engaged', key: 'post_engaged_users' }, { label: 'Clicks', key: 'post_clicks' }, { label: 'Shares', key: 'shares' },
        ], posts);
    } catch (e) { showError('fb-posts-table', e.message); }
    try {
        const igResp = await api('/api/social/ig-account');
        if (igResp.ig_id) {
            const igMedia = await api(`/api/social/ig-media?ig_id=${igResp.ig_id}`);
            renderTable('ig-media-table', [
                { label: 'Caption', key: 'caption' }, { label: 'Type', key: 'media_type' },
                { label: 'Likes', key: 'like_count' }, { label: 'Comments', key: 'comments_count' },
            ], (igMedia || []).map(m => ({ ...m, caption: (m.caption || '').slice(0, 80) })));
        }
    } catch (e) { showError('ig-media-table', e.message); }
}

async function loadSEOWeekly() {
    const tableEl = document.getElementById('seo-weekly-table');
    if (!tableEl) return;
    tableEl.innerHTML = '<div class="empty-state"><p>Loading SEO data...</p></div>';
    try {
        const data = await api(`/api/seo/trend?domain=${currentDomain}&period=${seoPeriod}&periods=5`);
        if (!data || data.length === 0) {
            tableEl.innerHTML = '<div class="empty-state"><p>No SEO data available</p></div>';
            return;
        }
        const sections = [
            { header: 'TRAFFIC', metrics: [
                { label: 'Organic Sessions', key: 'organic_sessions' },
                { label: 'Organic Users', key: 'organic_users' },
                { label: 'Website Leads', key: 'leads' },
            ]},
            { header: 'ENGAGEMENT', metrics: [
                { label: 'Avg. Session Duration (sec)', key: 'avg_session_duration' },
                { label: 'Bounce Rate (%)', key: 'bounce_rate' },
            ]},
            { header: 'SEARCH CONSOLE', metrics: [
                { label: 'GSC Clicks', key: 'gsc_clicks' },
                { label: 'GSC Impressions', key: 'gsc_impressions' },
                { label: 'Avg. Position', key: 'gsc_position' },
            ]},
        ];
        let html = '<table><thead><tr><th style="width:35%">Metric</th>';
        data.forEach(w => html += `<th style="text-align:center; font-size:0.7rem;">${esc(w.period)}</th>`);
        html += '</tr></thead><tbody>';
        sections.forEach(section => {
            html += `<tr><td colspan="${data.length + 1}" style="background:var(--accent-primary-soft); font-weight:800; font-size:0.7rem; letter-spacing:0.08em; color:var(--accent-primary); padding:0.5rem 1rem;">${section.header}</td></tr>`;
            section.metrics.forEach(m => {
                html += `<tr><td style="font-weight:600;">${m.label}</td>`;
                data.forEach(w => {
                    const val = w[m.key];
                    html += `<td style="text-align:center;">${val !== undefined ? formatNum(val) : '-'}</td>`;
                });
                html += '</tr>';
            });
        });
        html += '</tbody></table>';
        tableEl.innerHTML = html;
        // SEO trend chart
        try {
            makeChart('chart-seo-trend', {
                type: 'line',
                data: {
                    labels: data.map(d => d.period),
                    datasets: [
                        { label: 'GSC Clicks', data: data.map(d => d.gsc_clicks || 0), borderColor: '#7C3AED', backgroundColor: '#7C3AED20', fill: true, tension: 0.3 },
                        { label: 'Organic Sessions', data: data.map(d => d.organic_sessions || 0), borderColor: '#10B981', backgroundColor: '#10B98120', fill: true, tension: 0.3 },
                    ]
                },
                options: { scales: { x: {}, y: {} } }
            });
        } catch(e) {}
    } catch (e) {
        tableEl.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
    }
}

async function loadYouTube() {
    try {
        const ch = await api('/api/youtube/channel');
        if (ch.title) {
            renderMetric('yt-subscribers', ch.subscribers);
            renderMetric('yt-views', ch.views);
            renderMetric('yt-videos', ch.videos);
        }
    } catch (e) {
        const el = document.getElementById('yt-metrics');
        if (el) el.innerHTML = `<div class="empty-state"><p>YouTube API error: ${esc(e.message)}</p></div>`;
    }
    try {
        const videos = await api('/api/youtube/videos?limit=10');
        renderTable('yt-videos-table', [
            { label: 'Title', key: 'title' }, { label: 'Published', key: 'published' },
            { label: 'Views', key: 'views' }, { label: 'Likes', key: 'likes' }, { label: 'Comments', key: 'comments' },
        ], videos);
    } catch (e) { showError('yt-videos-table', e.message); }
}

async function generateSEO() {
    const topic = document.getElementById('yt-seo-topic').value.trim();
    if (!topic) return;
    const resultEl = document.getElementById('yt-seo-result');
    resultEl.innerHTML = '<div class="empty-state"><p>Generating...</p></div>';
    try {
        const seo = await api(`/api/youtube/seo?topic=${encodeURIComponent(topic)}`);
        let html = '<div class="glass-card-static" style="padding:1.5rem;">';
        html += '<div class="table-title">Suggested Titles</div><ul style="list-style:none; margin-bottom:1rem;">';
        seo.suggested_titles.forEach(t => html += `<li style="padding:0.3rem 0; font-size:0.85rem;">${esc(t)}</li>`);
        html += '</ul><div class="table-title">Description</div>';
        html += `<pre style="white-space:pre-wrap; font-size:0.8rem; background:var(--surface-input); padding:1rem; border-radius:0.75rem; margin-bottom:1rem; font-family:Inter,sans-serif;">${esc(seo.description)}</pre>`;
        html += '<div class="table-title">Hashtags</div><div style="display:flex; flex-wrap:wrap; gap:0.4rem; margin-bottom:1rem;">';
        seo.hashtags.forEach(h => html += `<span style="background:var(--accent-primary-soft); color:var(--accent-primary); padding:0.25rem 0.6rem; border-radius:9999px; font-size:0.75rem; font-weight:600;">${esc(h)}</span>`);
        html += '</div><div class="table-title">Tags</div><div style="display:flex; flex-wrap:wrap; gap:0.4rem;">';
        seo.tags.forEach(t => html += `<span style="background:var(--surface-hover); padding:0.25rem 0.6rem; border-radius:9999px; font-size:0.75rem;">${esc(t)}</span>`);
        html += '</div></div>';
        resultEl.innerHTML = html;
    } catch (e) { resultEl.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`; }
}

async function uploadLinkedIn() {
    const fileInput = document.getElementById('li-file-input');
    const file = fileInput.files[0];
    if (!file) return;
    const type = document.getElementById('li-upload-type').value;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const resp = await fetch(`/api/linkedin/upload?type=${type}`, { method: 'POST', body: formData });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        const summaryEl = document.getElementById('li-summary');
        const metricsEl = document.getElementById('li-metrics');
        const tableWrap = document.getElementById('li-table-wrap');
        if (data.summary) {
            summaryEl.style.display = 'block';
            let metricsHtml = '';
            const colors = ['#7C3AED', '#0EA5E9', '#10B981', '#F59E0B'];
            let ci = 0;
            for (const [key, val] of Object.entries(data.summary)) {
                if (key === 'total_rows') {
                    metricsHtml += `<div class="metric-card"><div class="accent-strip" style="background:${colors[ci++ % 4]}"></div><div class="metric-label">Total Rows</div><div class="metric-value">${val}</div></div>`;
                } else if (typeof val === 'object' && val.sum !== undefined) {
                    metricsHtml += `<div class="metric-card"><div class="accent-strip" style="background:${colors[ci++ % 4]}"></div><div class="metric-label">${esc(key)}</div><div class="metric-value">${formatNum(val.sum)}</div></div>`;
                }
            }
            metricsEl.innerHTML = metricsHtml;
        }
        if (data.headers && data.rows) {
            tableWrap.style.display = 'block';
            renderTable('li-data-table', data.headers.map(h => ({ label: h, key: h })), data.rows.slice(0, 50));
        }
    } catch (e) {
        document.getElementById('li-table-wrap').style.display = 'block';
        showError('li-data-table', e.message);
    }
}

async function loadAll() {
    await Promise.allSettled([loadGSC(), loadGA4(), loadMeta()]);
    // Overview combined chart
    try {
        const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
        const [gscDaily, ga4Daily] = await Promise.allSettled([
            api(`/api/gsc/daily${qs}`),
            api(`/api/ga4/daily${qs}`)
        ]);
        const gscData = gscDaily.status === 'fulfilled' ? gscDaily.value : [];
        const ga4Data = ga4Daily.status === 'fulfilled' ? ga4Daily.value : [];
        const labels = (gscData.length >= ga4Data.length ? gscData : ga4Data).map(d => d.date);
        makeChart('chart-overview-trend', {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'GSC Clicks', data: gscData.map(d => d.clicks), borderColor: '#7C3AED', backgroundColor: '#7C3AED20', fill: true, tension: 0.3 },
                    { label: 'GA4 Sessions', data: ga4Data.map(d => d.sessions), borderColor: '#10B981', backgroundColor: '#10B98120', fill: true, tension: 0.3 },
                ]
            },
            options: { scales: { x: {}, y: {} } }
        });
    } catch(e) {}
}

function switchDomain(key) {
    currentDomain = key;
    document.querySelectorAll('.domain-tab[data-domain]').forEach(t => t.classList.toggle('active', t.dataset.domain === key));
    const d = domains[key];
    if (d) document.getElementById('topbar-title').textContent = d.label;
    loadAll();
}

function exportReport() {
    window.location.href = `/api/export?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
}

async function checkHealth() {
    try {
        const h = await api('/api/health');
        const bar = document.getElementById('status-bar');
        if (h.status === 'ok') {
            bar.innerHTML = `<span class="status-dot green"></span><span class="status-text">Google connected · Meta: ${h.meta_marketing ? 'connected' : 'not configured'}</span>`;
        } else {
            bar.innerHTML = `<span class="status-dot red"></span><span class="status-text">Google auth error: ${h.error || 'unknown'}</span>`;
        }
    } catch (e) {
        document.getElementById('status-bar').innerHTML = `<span class="status-dot red"></span><span class="status-text">API unreachable</span>`;
    }
}

async function exchangeToken() {
    const input = document.getElementById('token-input');
    const token = input.value.trim();
    if (!token) return alert('Please paste a token first');
    const resultDiv = document.getElementById('token-result');
    const content = document.getElementById('token-result-content');
    content.innerHTML = '<p>Exchanging token...</p>';
    resultDiv.style.display = 'block';
    try {
        const data = await api(`/api/meta/exchange-token?token=${encodeURIComponent(token)}`);
        let html = '';
        if (data.long_lived_token) {
            html += `<p><strong>Long-Lived Token</strong> (expires in ~${data.expires_in_days} days):</p>`;
            html += `<textarea style="width:100%; height:60px; font-size:0.75rem;" readonly onclick="this.select()">${esc(data.long_lived_token)}</textarea>`;
        }
        if (data.page_token) {
            html += `<p><strong>Page Token</strong>:</p><textarea style="width:100%; height:60px; font-size:0.75rem;" readonly onclick="this.select()">${esc(data.page_token)}</textarea>`;
        }
        html += `<p style="color:var(--text-muted);">${esc(data.instructions)}</p>`;
        content.innerHTML = html;
    } catch (e) {
        content.innerHTML = `<p style="color:#ef4444;">Error: ${esc(e.message)}</p>`;
    }
}

// ── Calendar ──
async function generateCalendar() {
    const month = document.getElementById('cal-month').value;
    const context = document.getElementById('cal-context').value;
    if (!month) return alert('Pick a month');
    const tbl = document.getElementById('cal-table');
    tbl.innerHTML = '<div class="empty-state"><p>Generating with AI… this may take 30–60s.</p></div>';
    try {
        const data = await api('/api/calendar/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ domain: currentDomain, month, context }),
        });
        renderCalendarTable(data.items || []);
    } catch (e) {
        tbl.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
    }
}

async function uploadCalendar() {
    const fi = document.getElementById('cal-file');
    const file = fi.files[0];
    if (!file) return;
    const month = document.getElementById('cal-month').value;
    if (!month) return alert('Pick a month first');
    const tbl = document.getElementById('cal-table');
    tbl.innerHTML = '<div class="empty-state"><p>Processing document with AI…</p></div>';
    const fd = new FormData();
    fd.append('file', file);
    try {
        const resp = await fetch(`/api/calendar/upload?domain=${currentDomain}&month=${month}`, { method: 'POST', body: fd });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        renderCalendarTable(data.items || []);
    } catch (e) {
        tbl.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
    }
}

let calendarItems = [];
function renderCalendarTable(items) {
    calendarItems = items;
    const tbl = document.getElementById('cal-table');
    if (!items.length) { tbl.innerHTML = '<div class="empty-state"><p>No items.</p></div>'; return; }
    let html = '<table><thead><tr><th>Date</th><th>Platform</th><th>Type</th><th>Title</th><th>Description</th></tr></thead><tbody>';
    items.forEach((it, i) => {
        html += `<tr data-idx="${i}">
            <td contenteditable="true" data-k="date">${esc(it.date || '')}</td>
            <td contenteditable="true" data-k="platform">${esc(it.platform || '')}</td>
            <td contenteditable="true" data-k="type">${esc(it.type || '')}</td>
            <td contenteditable="true" data-k="title">${esc(it.title || '')}</td>
            <td contenteditable="true" data-k="description">${esc(it.description || '')}</td>
        </tr>`;
    });
    html += '</tbody></table>';
    tbl.innerHTML = html;
    tbl.querySelectorAll('td[contenteditable]').forEach(td => {
        td.addEventListener('blur', () => {
            const tr = td.closest('tr');
            const idx = parseInt(tr.dataset.idx);
            calendarItems[idx][td.dataset.k] = td.textContent.trim();
        });
    });
}

// ── Ideas ──
function setIdeaCat(c) {
    ideaCat = c;
    document.querySelectorAll('[data-ideacat]').forEach(b => b.classList.toggle('active', b.dataset.ideacat === c));
}

async function generateIdeas() {
    const grid = document.getElementById('ideas-grid');
    grid.innerHTML = '<div class="empty-state"><p>Generating ideas…</p></div>';
    try {
        const data = await api(`/api/ideas/generate?domain=${currentDomain}&category=${ideaCat}`);
        const items = data.items || [];
        if (!items.length) { grid.innerHTML = '<div class="empty-state"><p>No ideas.</p></div>'; return; }
        grid.innerHTML = items.map(it => `
            <div class="glass-card-static" style="padding:1.25rem; display:flex; flex-direction:column; gap:0.5rem;">
                <div style="font-size:0.7rem; font-weight:800; color:var(--accent-primary); letter-spacing:0.08em;">${esc((it.type || '').toUpperCase())}</div>
                <div style="font-weight:700; font-size:0.95rem;">${esc(it.title || '')}</div>
                <div style="color:var(--text-muted); font-size:0.8rem; line-height:1.5;">${esc(it.description || '')}</div>
                <div style="display:flex; flex-wrap:wrap; gap:0.3rem; margin-top:0.25rem;">
                    ${(it.hashtags || []).map(h => `<span style="background:var(--accent-primary-soft); color:var(--accent-primary); padding:0.15rem 0.5rem; border-radius:9999px; font-size:0.7rem;">${esc(h)}</span>`).join('')}
                </div>
                <div style="margin-top:0.25rem; font-size:0.75rem; color:var(--text-muted);">Best on: <strong>${esc(it.best_platform || '-')}</strong></div>
            </div>
        `).join('');
        checkIdeasNotifications();
    } catch (e) {
        grid.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
    }
}

async function checkIdeasNotifications() {
    try {
        const d = await api('/api/ideas/notifications');
        const badge = document.getElementById('ideas-badge');
        if (d.new && d.new > 0) {
            badge.style.display = 'inline-block';
            badge.textContent = d.new;
        } else {
            badge.style.display = 'none';
        }
    } catch (e) {}
}

async function markIdeasSeen() {
    try { await fetch('/api/ideas/seen', { method: 'POST' }); } catch (e) {}
    const badge = document.getElementById('ideas-badge');
    if (badge) badge.style.display = 'none';
}

// ── Validator ──
function switchValTab(t) {
    document.querySelectorAll('[data-vtab]').forEach(b => b.classList.toggle('active', b.dataset.vtab === t));
    ['text', 'image', 'video'].forEach(v => {
        const el = document.getElementById('val-' + v);
        if (el) el.style.display = v === t ? 'block' : 'none';
    });
}

function renderValResult(r) {
    const el = document.getElementById('val-result');
    if (!r || typeof r !== 'object') { el.innerHTML = `<div class="error-msg">Invalid response</div>`; return; }
    const score = r.score || 0;
    const color = score >= 80 ? '#10B981' : score >= 60 ? '#F59E0B' : '#ef4444';
    const ready = r.publish_ready;
    let html = `<div class="glass-card-static" style="padding:1.5rem;">
        <div style="display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap;">
            <div style="font-size:3rem; font-weight:800; color:${color};">${score}<span style="font-size:1rem; color:var(--text-muted);">/100</span></div>
            <div>
                <div style="font-weight:700; margin-bottom:0.25rem;">${esc(r.summary || '')}</div>
                <span style="background:${ready ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${ready ? '#10B981' : '#ef4444'}; padding:0.25rem 0.6rem; border-radius:9999px; font-size:0.7rem; font-weight:700;">${ready ? 'PUBLISH READY' : 'NEEDS WORK'}</span>
            </div>
        </div>
    </div>`;
    const sections = [
        { title: 'Strengths', items: r.strengths || [], color: '#10B981' },
        { title: 'Weaknesses', items: r.weaknesses || [], color: '#F59E0B' },
        { title: 'Recommendations', items: r.recommendations || [], color: '#0EA5E9' },
        { title: 'Missing Info', items: r.missing_info || [], color: '#7C3AED' },
    ];
    sections.forEach(s => {
        if (!s.items.length) return;
        html += `<div class="glass-card-static" style="padding:1.25rem; margin-top:1rem; border-left:4px solid ${s.color};">
            <div class="section-label" style="color:${s.color};">${s.title}</div>
            <ul style="margin:0.5rem 0 0 1.25rem; font-size:0.85rem; line-height:1.6;">
                ${s.items.map(x => `<li>${esc(typeof x === 'string' ? x : JSON.stringify(x))}</li>`).join('')}
            </ul>
        </div>`;
    });
    if (r.grammar_issues && r.grammar_issues.length) {
        html += `<div class="glass-card-static" style="padding:1.25rem; margin-top:1rem;">
            <div class="section-label">Grammar Issues</div>
            <ul style="margin:0.5rem 0 0 1.25rem; font-size:0.85rem; line-height:1.6;">
                ${r.grammar_issues.map(g => `<li><strong>${esc(g.issue || '')}</strong> → ${esc(g.suggestion || '')}</li>`).join('')}
            </ul>
        </div>`;
    }
    el.innerHTML = html;
}

async function validateText() {
    const content = document.getElementById('val-content').value.trim();
    if (!content) return;
    const el = document.getElementById('val-result');
    el.innerHTML = '<div class="empty-state"><p>Validating…</p></div>';
    try {
        const r = await api('/api/validator/text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });
        renderValResult(r);
    } catch (e) { el.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`; }
}

async function validateImage() {
    const f = document.getElementById('val-img-file').files[0];
    if (!f) return alert('Choose an image first');
    const el = document.getElementById('val-result');
    el.innerHTML = '<div class="empty-state"><p>Analyzing image…</p></div>';
    const fd = new FormData();
    fd.append('file', f);
    try {
        const resp = await fetch('/api/validator/image', { method: 'POST', body: fd });
        if (!resp.ok) throw new Error(await resp.text());
        renderValResult(await resp.json());
    } catch (e) { el.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`; }
}

async function validateVideo() {
    const f = document.getElementById('val-vid-file').files[0];
    if (!f) return alert('Choose a video first');
    const el = document.getElementById('val-result');
    const fd = new FormData();
    fd.append('file', f);
    try {
        const resp = await fetch('/api/validator/video', { method: 'POST', body: fd });
        const r = await resp.json();
        el.innerHTML = `<div class="glass-card-static" style="padding:1.5rem;">${esc(r.message || '')}</div>`;
    } catch (e) { el.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`; }
}

// ── Reports ──
function setRepPeriod(p) {
    repPeriod = p;
    document.querySelectorAll('[data-rep-period]').forEach(b => b.classList.toggle('active', b.dataset.repPeriod === p));
}

async function generateReport() {
    const start = document.getElementById('rep-start').value;
    const end = document.getElementById('rep-end').value;
    const el = document.getElementById('rep-result');
    el.innerHTML = '<div class="empty-state"><p>Generating…</p></div>';
    try {
        const qs = `?period=${repPeriod}&domain=${currentDomain}&start=${start}&end=${end}`;
        const r = await api(`/api/reports/generate${qs}`);
        let html = `<div class="section-label">${esc(r.label)} — ${esc(r.period)} (${esc(r.start)} to ${esc(r.end)})</div>`;
        const sections = [
            { key: 'gsc', title: 'Search Console', color: '#7C3AED' },
            { key: 'ga4', title: 'Google Analytics', color: '#0EA5E9' },
            { key: 'meta', title: 'Meta Ads', color: '#10B981' },
            { key: 'social_fb', title: 'Facebook', color: '#1877F2' },
            { key: 'social_ig', title: 'Instagram', color: '#E4405F' },
        ];
        sections.forEach(s => {
            const v = r[s.key];
            if (!v || typeof v !== 'object' || v.error) return;
            html += `<div class="section"><div class="section-label" style="color:${s.color};">${s.title}</div><div class="metrics-grid">`;
            Object.entries(v).slice(0, 8).forEach(([k, val]) => {
                if (typeof val === 'object') return;
                html += `<div class="metric-card"><div class="accent-strip" style="background:${s.color}"></div><div class="metric-label">${esc(k)}</div><div class="metric-value">${formatNum(val)}</div></div>`;
            });
            html += '</div></div>';
        });
        el.innerHTML = html;
    } catch (e) {
        el.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
    }
}

function exportReportFmt(fmt) {
    const start = document.getElementById('rep-start').value;
    const end = document.getElementById('rep-end').value;
    window.location.href = `/api/reports/export?period=${repPeriod}&domain=${currentDomain}&start=${start}&end=${end}&format=${fmt}`;
}

// ── Init ──
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    setDates('28d');
    checkHealth();
    checkIdeasNotifications();
    setInterval(checkIdeasNotifications, 60000);

    try {
        domains = await api('/api/domains');
        const tabs = document.getElementById('domain-tabs');
        tabs.innerHTML = '';
        Object.entries(domains).forEach(([key, d]) => {
            const btn = document.createElement('button');
            btn.className = 'domain-tab' + (key === currentDomain ? ' active' : '');
            btn.dataset.domain = key;
            btn.innerHTML = `<span class="domain-dot" style="background:${d.color}"></span> ${d.label}`;
            btn.onclick = () => switchDomain(key);
            tabs.appendChild(btn);
        });
    } catch (e) { console.error('Failed to load domains', e); }

    document.querySelectorAll('#date-range-group .dr-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            setDates(btn.dataset.preset);
            loadAll();
        });
    });
    document.getElementById('date-start').addEventListener('change', (e) => {
        dateStart = e.target.value;
        activePreset = '';
        document.querySelectorAll('#date-range-group .dr-btn').forEach(b => b.classList.remove('active'));
        loadAll();
    });
    document.getElementById('date-end').addEventListener('change', (e) => {
        dateEnd = e.target.value;
        activePreset = '';
        document.querySelectorAll('#date-range-group .dr-btn').forEach(b => b.classList.remove('active'));
        loadAll();
    });

    document.getElementById('btn-export').addEventListener('click', exportReport);
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    const btnSeo = document.getElementById('btn-seo-generate');
    if (btnSeo) btnSeo.addEventListener('click', generateSEO);
    const liInput = document.getElementById('li-file-input');
    if (liInput) liInput.addEventListener('change', uploadLinkedIn);
    const seoTopic = document.getElementById('yt-seo-topic');
    if (seoTopic) seoTopic.addEventListener('keydown', e => { if (e.key === 'Enter') generateSEO(); });

    const calFile = document.getElementById('cal-file');
    if (calFile) calFile.addEventListener('change', uploadCalendar);
    const valImg = document.getElementById('val-img-file');
    if (valImg) valImg.addEventListener('change', () => {
        const el = document.getElementById('val-img-name');
        if (el) el.textContent = valImg.files[0]?.name || '';
    });

    // Default report dates
    const today = new Date();
    const monthAgo = new Date(today - 30 * 86400000);
    document.getElementById('rep-end').value = today.toISOString().split('T')[0];
    document.getElementById('rep-start').value = monthAgo.toISOString().split('T')[0];
    // Default calendar month
    document.getElementById('cal-month').value = today.toISOString().slice(0, 7);

    const loader = document.getElementById('page-loader');
    if (loader) { loader.classList.add('fade'); setTimeout(() => loader.remove(), 400); }

    loadAll();
});
