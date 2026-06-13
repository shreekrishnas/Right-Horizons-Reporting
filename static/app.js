const API = '';
let currentDomain = 'rh';
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
    const end = today.toISOString().split('T')[0];
    let start;
    switch (preset) {
        case '7d':
            start = new Date(today - 7 * 86400000).toISOString().split('T')[0];
            break;
        case '28d':
            start = new Date(today - 28 * 86400000).toISOString().split('T')[0];
            break;
        case '3m':
            start = new Date(today - 90 * 86400000).toISOString().split('T')[0];
            break;
        case '6m':
            start = new Date(today - 180 * 86400000).toISOString().split('T')[0];
            break;
        default:
            start = new Date(today - 28 * 86400000).toISOString().split('T')[0];
    }
    dateStart = start;
    dateEnd = end;
    document.getElementById('date-start').value = start;
    document.getElementById('date-end').value = end;
    activePreset = preset;
    document.querySelectorAll('.date-preset').forEach(b => {
        b.classList.toggle('active', b.dataset.preset === preset);
    });
}

function showLoading(id) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '<div class="metric-value loading"></div>';
}

function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<div class="error-msg">${msg}</div>`;
}

function renderMetric(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = formatNum(value);
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

async function loadGSC() {
    const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;

    ['gsc-clicks', 'gsc-impressions', 'gsc-ctr', 'gsc-position'].forEach(id => showLoading(id));

    try {
        const summary = await api(`/api/gsc/summary${qs}`);
        renderMetric('gsc-clicks', summary.clicks);
        renderMetric('gsc-impressions', summary.impressions);
        renderMetric('gsc-ctr', summary.ctr + '%');
        renderMetric('gsc-position', summary.position);
    } catch (e) {
        showError('gsc-metrics', e.message);
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

    ['ga4-sessions', 'ga4-users', 'ga4-pageviews', 'ga4-bounce'].forEach(id => showLoading(id));

    try {
        const summary = await api(`/api/ga4/summary${qs}`);
        renderMetric('ga4-sessions', summary.sessions);
        renderMetric('ga4-users', summary.users);
        renderMetric('ga4-pageviews', summary.pageviews);
        renderMetric('ga4-bounce', summary.bounce_rate + '%');
    } catch (e) {
        document.getElementById('ga4-metrics').innerHTML =
            `<div class="empty-state"><p>GA4 not configured for this domain</p></div>`;
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
            document.getElementById('meta-section').innerHTML =
                '<div class="empty-state"><p>Meta Marketing API not connected</p></div>';
            return;
        }

        const accounts = await api('/api/meta/accounts');
        if (!accounts || accounts.length === 0) {
            document.getElementById('meta-section').innerHTML =
                '<div class="empty-state"><p>No Meta ad accounts found</p></div>';
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
    } catch (e) {
        showError('meta-section', e.message);
    }
}

async function loadAll() {
    document.getElementById('loading-overlay').style.display = 'flex';
    await Promise.allSettled([loadGSC(), loadGA4(), loadMeta()]);
    document.getElementById('loading-overlay').style.display = 'none';
}

function switchDomain(key) {
    currentDomain = key;
    document.querySelectorAll('.domain-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.domain === key);
    });
    const d = domains[key];
    if (d) document.getElementById('domain-label').textContent = d.label;
    loadAll();
}

function exportReport() {
    const url = `/api/export?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
    window.location.href = url;
}

async function checkHealth() {
    try {
        const h = await api('/api/health');
        const bar = document.getElementById('status-bar');
        if (h.status === 'ok') {
            bar.innerHTML = `<span class="status-dot green"></span>
                <span class="status-text">Google connected | Meta: ${h.meta_marketing ? 'connected' : 'not configured'}</span>`;
        } else {
            bar.innerHTML = `<span class="status-dot red"></span>
                <span class="status-text">Google auth error: ${h.error || 'unknown'}</span>`;
        }
    } catch (e) {
        document.getElementById('status-bar').innerHTML =
            `<span class="status-dot red"></span><span class="status-text">API unreachable</span>`;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    setDates('28d');
    await checkHealth();

    try {
        domains = await api('/api/domains');
        const tabs = document.getElementById('domain-tabs');
        tabs.innerHTML = '';
        Object.entries(domains).forEach(([key, d]) => {
            const btn = document.createElement('button');
            btn.className = 'domain-tab' + (key === currentDomain ? ' active' : '');
            btn.dataset.domain = key;
            btn.textContent = d.short;
            btn.onclick = () => switchDomain(key);
            tabs.appendChild(btn);
        });
    } catch (e) {
        console.error('Failed to load domains', e);
    }

    document.querySelectorAll('.date-preset').forEach(btn => {
        btn.addEventListener('click', () => {
            setDates(btn.dataset.preset);
            loadAll();
        });
    });

    document.getElementById('date-start').addEventListener('change', (e) => {
        dateStart = e.target.value;
        activePreset = '';
        document.querySelectorAll('.date-preset').forEach(b => b.classList.remove('active'));
        loadAll();
    });

    document.getElementById('date-end').addEventListener('change', (e) => {
        dateEnd = e.target.value;
        activePreset = '';
        document.querySelectorAll('.date-preset').forEach(b => b.classList.remove('active'));
        loadAll();
    });

    document.getElementById('btn-export').addEventListener('click', exportReport);

    loadAll();
});
