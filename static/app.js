const API = '';
let currentDomain = 'rh';
let currentView = 'overview';
let domains = {};
let dateStart = '';
let dateEnd = '';
let activePreset = '28d';

async function api(path) {
    const resp = await fetch(`${API}${path}`);
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
    document.getElementById('date-start').value = dateStart;
    document.getElementById('date-end').value = dateEnd;
    activePreset = preset;
    document.querySelectorAll('.dr-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.preset === preset);
    });
}

function showLoading(id) {
    const el = document.getElementById(id);
    if (el) { el.className = 'metric-value loading'; el.textContent = ''; }
}

function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<div class="error-msg">${msg}</div>`;
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
    headers.forEach(h => html += `<th>${h.label}</th>`);
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

// ── Theme ──

function initTheme() {
    const saved = localStorage.getItem('rh-theme');
    if (saved === 'dark') applyTheme('dark');
    else applyTheme('light');
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
}

// ── Views ──

function switchView(view) {
    currentView = view;
    ['overview', 'gsc', 'ga4', 'meta'].forEach(v => {
        const el = document.getElementById('view-' + v);
        if (el) el.style.display = v === view ? 'block' : 'none';
    });
    document.querySelectorAll('.sidebar-item').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
    const subtitles = { overview: 'Reporting Dashboard', gsc: 'Search Console', ga4: 'Google Analytics', meta: 'Meta Ads' };
    const sub = document.getElementById('topbar-sub');
    if (sub) sub.textContent = subtitles[view] || 'Dashboard';
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
        showError('gsc-metrics', e.message);
        showError('gsc-metrics-detail', e.message);
    }

    try {
        const queries = await api(`/api/gsc/queries${qs}&limit=15`);
        renderTable('gsc-queries-table', [
            { label: 'Query', key: 'query' },
            { label: 'Clicks', key: 'clicks' },
            { label: 'Impressions', key: 'impressions' },
            { label: 'CTR %', key: 'ctr' },
            { label: 'Position', key: 'position' },
        ], queries);
    } catch (e) {
        showError('gsc-queries-table', e.message);
    }

    try {
        const pages = await api(`/api/gsc/pages${qs}&limit=15`);
        renderTable('gsc-pages-table', [
            { label: 'Page', key: 'page' },
            { label: 'Clicks', key: 'clicks' },
            { label: 'Impressions', key: 'impressions' },
            { label: 'CTR %', key: 'ctr' },
            { label: 'Position', key: 'position' },
        ], pages);
    } catch (e) {
        showError('gsc-pages-table', e.message);
    }
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
        const msg = '<div class="empty-state"><p>GA4 not configured for this domain</p></div>';
        const m1 = document.getElementById('ga4-metrics');
        const m2 = document.getElementById('ga4-metrics-detail');
        if (m1) m1.innerHTML = msg;
        if (m2) m2.innerHTML = msg;
    }

    try {
        const sources = await api(`/api/ga4/sources${qs}`);
        renderTable('ga4-sources-table', [
            { label: 'Channel', key: 'channel' },
            { label: 'Sessions', key: 'sessions' },
            { label: 'Users', key: 'users' },
        ], sources);
    } catch (e) {
        showError('ga4-sources-table', e.message);
    }

    try {
        const pages = await api(`/api/ga4/pages${qs}&limit=15`);
        renderTable('ga4-pages-table', [
            { label: 'Page', key: 'page' },
            { label: 'Views', key: 'views' },
            { label: 'Sessions', key: 'sessions' },
            { label: 'Avg Duration', key: 'avg_dur' },
        ], pages);
    } catch (e) {
        showError('ga4-pages-table', e.message);
    }
}

async function loadMeta() {
    try {
        const status = await api('/api/meta/status');
        if (!status.marketing) {
            const targets = ['meta-overview', 'meta-section'];
            targets.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = '<div class="empty-state"><p>Meta Marketing API not connected</p></div>';
            });
            return;
        }

        const accounts = await api('/api/meta/accounts');
        if (!accounts || accounts.length === 0) {
            const targets = ['meta-overview', 'meta-section'];
            targets.forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerHTML = '<div class="empty-state"><p>No Meta ad accounts found</p></div>';
            });
            return;
        }

        const acctId = accounts[0].id;
        const qs = `?ad_account=${acctId}&start=${dateStart}&end=${dateEnd}`;
        const campaigns = await api(`/api/meta/campaigns${qs}`);

        renderTable('meta-campaigns-table', [
            { label: 'Campaign', key: 'name' },
            { label: 'Status', key: 'status' },
            { label: 'Spend', key: 'spend' },
            { label: 'Impressions', key: 'impressions' },
            { label: 'Reach', key: 'reach' },
            { label: 'Clicks', key: 'clicks' },
            { label: 'CTR %', key: 'ctr' },
        ], campaigns);

        const overview = document.getElementById('meta-overview');
        if (overview && campaigns && campaigns.length > 0) {
            const totalSpend = campaigns.reduce((s, c) => s + (parseFloat(c.spend) || 0), 0);
            const totalClicks = campaigns.reduce((s, c) => s + (parseInt(c.clicks) || 0), 0);
            const totalImpressions = campaigns.reduce((s, c) => s + (parseInt(c.impressions) || 0), 0);
            overview.innerHTML = `
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="accent-strip" style="background:#7C3AED"></div>
                        <div class="metric-label">Total Spend</div>
                        <div class="metric-value">$${totalSpend.toFixed(2)}</div>
                    </div>
                    <div class="metric-card">
                        <div class="accent-strip" style="background:#0EA5E9"></div>
                        <div class="metric-label">Clicks</div>
                        <div class="metric-value">${formatNum(totalClicks)}</div>
                    </div>
                    <div class="metric-card">
                        <div class="accent-strip" style="background:#10B981"></div>
                        <div class="metric-label">Impressions</div>
                        <div class="metric-value">${formatNum(totalImpressions)}</div>
                    </div>
                    <div class="metric-card">
                        <div class="accent-strip" style="background:#F59E0B"></div>
                        <div class="metric-label">Campaigns</div>
                        <div class="metric-value">${campaigns.length}</div>
                    </div>
                </div>`;
        }
    } catch (e) {
        showError('meta-overview', e.message);
        showError('meta-section', e.message);
    }
}

async function loadAll() {
    await Promise.allSettled([loadGSC(), loadGA4(), loadMeta()]);
}

// ── Domain switching ──

function switchDomain(key) {
    currentDomain = key;
    document.querySelectorAll('.domain-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.domain === key);
    });
    const d = domains[key];
    if (d) {
        document.getElementById('topbar-title').textContent = d.label;
    }
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
            bar.innerHTML = `<span class="status-dot green"></span>
                <span class="status-text">Google connected · Meta: ${h.meta_marketing ? 'connected' : 'not configured'}</span>`;
        } else {
            bar.innerHTML = `<span class="status-dot red"></span>
                <span class="status-text">Google auth error: ${h.error || 'unknown'}</span>`;
        }
    } catch (e) {
        document.getElementById('status-bar').innerHTML =
            `<span class="status-dot red"></span><span class="status-text">API unreachable</span>`;
    }
}

// ── Init ──

document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    setDates('28d');

    checkHealth();

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
    } catch (e) {
        console.error('Failed to load domains', e);
    }

    document.querySelectorAll('.dr-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            setDates(btn.dataset.preset);
            loadAll();
        });
    });

    document.getElementById('date-start').addEventListener('change', (e) => {
        dateStart = e.target.value;
        activePreset = '';
        document.querySelectorAll('.dr-btn').forEach(b => b.classList.remove('active'));
        loadAll();
    });

    document.getElementById('date-end').addEventListener('change', (e) => {
        dateEnd = e.target.value;
        activePreset = '';
        document.querySelectorAll('.dr-btn').forEach(b => b.classList.remove('active'));
        loadAll();
    });

    document.getElementById('btn-export').addEventListener('click', exportReport);
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

    await loadAll();

    const loader = document.getElementById('page-loader');
    if (loader) { loader.classList.add('fade'); setTimeout(() => loader.remove(), 400); }
});
