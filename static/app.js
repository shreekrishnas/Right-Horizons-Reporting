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
    if (n === undefined || n === null) return '0';
    if (typeof n === 'number') return n.toLocaleString('en-IN');
    return n;
}

function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function shortDate(d) {
    if (!d) return d;
    const s = String(d).replace(/-/g, '');
    if (s.length < 8) return d;
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return months[parseInt(s.slice(4,6))-1] + ' ' + parseInt(s.slice(6,8));
}

const CHART_COLORS = {
    purple: '#7C3AED',
    purpleLight: 'rgba(124, 58, 237, 0.08)',
    blue: '#0EA5E9',
    blueLight: 'rgba(14, 165, 233, 0.08)',
    green: '#10B981',
    greenLight: 'rgba(16, 185, 129, 0.08)',
    red: '#EF4444',
    redLight: 'rgba(239, 68, 68, 0.08)',
    amber: '#F59E0B',
    pink: '#EC4899',
    teal: '#14B8A6',
    palette: ['#7C3AED', '#0EA5E9', '#10B981', '#F59E0B', '#EF4444', '#EC4899', '#8B5CF6', '#06B6D4']
};

// Return today's date string in IST (UTC+5:30)
function todayIST() {
    const now = new Date();
    const ist = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
    return ist.toISOString().split('T')[0];
}
function offsetIST(baseIST, days) {
    const d = new Date(baseIST + 'T00:00:00+05:30');
    d.setDate(d.getDate() + days);
    const ist = new Date(d.getTime() + (5.5 * 60 * 60 * 1000));
    return ist.toISOString().split('T')[0];
}

function setDates(preset) {
    const end = offsetIST(todayIST(), -1);
    let startDate;
    switch (preset) {
        case '7d': startDate = offsetIST(end, -7); break;
        case '28d': startDate = offsetIST(end, -28); break;
        case '3m': startDate = offsetIST(end, -90); break;
        case '6m': startDate = offsetIST(end, -180); break;
        default: startDate = offsetIST(end, -28);
    }
    dateStart = startDate;
    dateEnd = end;
    const ds = document.getElementById('date-start');
    const de = document.getElementById('date-end');
    if (ds) { ds.value = dateStart; if (ds._flatpickr) ds._flatpickr.setDate(dateStart, false); }
    if (de) { de.value = dateEnd; if (de._flatpickr) de._flatpickr.setDate(dateEnd, false); }
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

    // Plugin defaults
    config.options.plugins = config.options.plugins || {};
    config.options.plugins.legend = config.options.plugins.legend || {};
    config.options.plugins.legend.labels = { color: c.text, font: { family: 'Inter', size: 11 }, boxWidth: 12, padding: 12 };
    // Auto-hide legend for single dataset (non-doughnut)
    const ds = config.data && config.data.datasets;
    if (ds && ds.length === 1 && config.type !== 'doughnut') {
        config.options.plugins.legend.display = false;
    } else {
        config.options.plugins.legend.position = config.options.plugins.legend.position || 'top';
    }

    // Tooltip formatting
    config.options.plugins.tooltip = config.options.plugins.tooltip || {};
    config.options.plugins.tooltip.callbacks = config.options.plugins.tooltip.callbacks || {};
    if (!config.options.plugins.tooltip.callbacks.label) {
        config.options.plugins.tooltip.callbacks.label = function(ctx) {
            let label = ctx.dataset.label || '';
            if (label) label += ': ';
            const v = ctx.parsed.y !== undefined ? ctx.parsed.y : ctx.parsed;
            return label + formatNum(v);
        };
    }

    // Element defaults for clean lines
    config.options.elements = config.options.elements || {};
    config.options.elements.line = config.options.elements.line || {};
    config.options.elements.line.borderWidth = config.options.elements.line.borderWidth || 2;
    config.options.elements.point = config.options.elements.point || {};
    if (config.options.elements.point.radius === undefined) config.options.elements.point.radius = 0;
    if (config.options.elements.point.hoverRadius === undefined) config.options.elements.point.hoverRadius = 4;

    // Scale defaults
    if (config.options.scales) {
        Object.entries(config.options.scales).forEach(([key, s]) => {
            s.ticks = s.ticks || {};
            s.ticks.color = c.muted;
            s.ticks.font = { family: 'Inter', size: 11 };
            s.grid = s.grid || {};
            if (key.startsWith('x')) {
                s.grid.color = c.border + '15';
                s.ticks.maxTicksLimit = s.ticks.maxTicksLimit || 8;
            } else {
                s.grid.display = s.grid.display !== undefined ? s.grid.display : false;
            }
            s.border = s.border || {};
            s.border.display = false;
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
    // Re-render current tab charts
    loadAll();
}

// ── Views ──
function switchView(view) {
    currentView = view;
    ['dashboard', 'analytics', 'calendar', 'ideas', 'validator', 'reports', 'settings'].forEach(v => {
        const el = document.getElementById('view-' + v);
        if (el) el.style.display = v === view ? 'block' : 'none';
    });
    document.querySelectorAll('.sidebar-item').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
    const subtitles = {
        dashboard: 'Dashboard', analytics: 'Analytics', calendar: 'Content Calendar', ideas: 'Creative Ideas',
        validator: 'Content Validator', reports: 'Reports & Analytics', settings: 'Settings'
    };
    const sub = document.getElementById('topbar-sub');
    if (sub) sub.textContent = subtitles[view] || 'Dashboard';
    if (view === 'ideas') markIdeasSeen();
    if (view === 'analytics') loadAnalytics();
}

// ── Analytics View ──
function shortUrl(url) {
    try {
        const path = new URL(url, 'https://x.com').pathname;
        return path.length > 35 ? '...' + path.slice(-32) : path || '/';
    } catch { return url.slice(0, 35); }
}

function applyGradient(chart, datasetIdx, color) {
    if (!chart) return;
    const ctx = chart.canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, chart.height);
    gradient.addColorStop(0, color + '35');
    gradient.addColorStop(1, color + '03');
    chart.data.datasets[datasetIdx].backgroundColor = gradient;
    chart.update('none');
}

let analyticsLoaded = {};

// ── Data Cache: fetch 6 months once, filter locally ──
const _dataCache = {};

function _cacheKey(domain) { return domain; }

function _sixMonthRange() {
    const end = offsetIST(todayIST(), -1);
    const start = offsetIST(end, -180);
    return { start, end };
}

function _filterDaily(daily, start, end) {
    return daily.filter(d => d.date >= start && d.date <= end);
}

function _gscSummaryFromDaily(daily) {
    if (!daily.length) return { clicks: 0, impressions: 0, ctr: 0, position: 0 };
    const clicks = daily.reduce((s, d) => s + d.clicks, 0);
    const impressions = daily.reduce((s, d) => s + d.impressions, 0);
    const ctr = impressions > 0 ? parseFloat(((clicks / impressions) * 100).toFixed(2)) : 0;
    const posSum = daily.reduce((s, d) => s + (d.position || 0) * (d.impressions || 1), 0);
    const posWeight = daily.reduce((s, d) => s + (d.impressions || 1), 0);
    const position = posWeight > 0 ? parseFloat((posSum / posWeight).toFixed(1)) : 0;
    return { clicks, impressions, ctr, position };
}

function _ga4SummaryFromDaily(daily) {
    if (!daily.length) return { sessions: 0, users: 0, new_users: 0, bounce_rate: 0, pageviews: 0, avg_session: 0 };
    const sessions = daily.reduce((s, d) => s + d.sessions, 0);
    const users = daily.reduce((s, d) => s + d.users, 0);
    const new_users = daily.reduce((s, d) => s + (d.new_users || 0), 0);
    const pageviews = daily.reduce((s, d) => s + (d.pageviews || 0), 0);
    const brSum = daily.reduce((s, d) => s + (d.bounce_rate || 0) * d.sessions, 0);
    const bounce_rate = sessions > 0 ? parseFloat(((brSum / sessions) * 100).toFixed(1)) : 0;
    const durSum = daily.reduce((s, d) => s + (d.avg_session || 0) * d.sessions, 0);
    const avg_session = sessions > 0 ? Math.round(durSum / sessions) : 0;
    return { sessions, users, new_users, bounce_rate, pageviews, avg_session };
}

async function prefetchDomain(domain) {
    const key = _cacheKey(domain);
    if (_dataCache[key] && _dataCache[key].ready) return _dataCache[key];

    const cache = { ready: false, fetching: true };
    _dataCache[key] = cache;

    const range = _sixMonthRange();
    const qs = `?domain=${domain}&start=${range.start}&end=${range.end}`;

    const [gscDaily, ga4Daily, gscQueries, gscPages, ga4Pages, ga4Sources] = await Promise.allSettled([
        api(`/api/gsc/daily${qs}`),
        api(`/api/ga4/daily${qs}`),
        api(`/api/gsc/queries${qs}&limit=15`),
        api(`/api/gsc/pages${qs}&limit=15`),
        api(`/api/ga4/pages${qs}&limit=15`),
        api(`/api/ga4/sources${qs}`),
    ]);

    cache.range = range;
    cache.gscDaily = gscDaily.status === 'fulfilled' ? gscDaily.value : [];
    cache.ga4Daily = ga4Daily.status === 'fulfilled' ? ga4Daily.value : [];
    cache.gscQueries = gscQueries.status === 'fulfilled' ? gscQueries.value : [];
    cache.gscPages = gscPages.status === 'fulfilled' ? gscPages.value : [];
    cache.ga4Pages = ga4Pages.status === 'fulfilled' ? ga4Pages.value : [];
    cache.ga4Sources = ga4Sources.status === 'fulfilled' ? ga4Sources.value : [];
    cache.ready = true;
    cache.fetching = false;

    return cache;
}

function _getCachedOrNull(domain) {
    const key = _cacheKey(domain);
    const c = _dataCache[key];
    if (!c || !c.ready) return null;
    if (dateStart >= c.range.start && dateEnd <= c.range.end) return c;
    return null;
}

async function _ensureCache(domain) {
    let c = _getCachedOrNull(domain);
    if (c) return c;
    const key = _cacheKey(domain);
    const existing = _dataCache[key];
    if (existing && existing.ready && (dateStart < existing.range.start || dateEnd > existing.range.end)) {
        // Date range exceeds cache — refetch with extended range
        const newStart = dateStart < existing.range.start ? dateStart : existing.range.start;
        const newEnd = dateEnd > existing.range.end ? dateEnd : existing.range.end;
        delete _dataCache[key];
        const qs = `?domain=${domain}&start=${newStart}&end=${newEnd}`;
        const cache = { ready: false, fetching: true };
        _dataCache[key] = cache;
        const [gscDaily, ga4Daily, gscQueries, gscPages, ga4Pages, ga4Sources] = await Promise.allSettled([
            api(`/api/gsc/daily${qs}`),
            api(`/api/ga4/daily${qs}`),
            api(`/api/gsc/queries${qs}&limit=15`),
            api(`/api/gsc/pages${qs}&limit=15`),
            api(`/api/ga4/pages${qs}&limit=15`),
            api(`/api/ga4/sources${qs}`),
        ]);
        cache.range = { start: newStart, end: newEnd };
        cache.gscDaily = gscDaily.status === 'fulfilled' ? gscDaily.value : [];
        cache.ga4Daily = ga4Daily.status === 'fulfilled' ? ga4Daily.value : [];
        cache.gscQueries = gscQueries.status === 'fulfilled' ? gscQueries.value : [];
        cache.gscPages = gscPages.status === 'fulfilled' ? gscPages.value : [];
        cache.ga4Pages = ga4Pages.status === 'fulfilled' ? ga4Pages.value : [];
        cache.ga4Sources = ga4Sources.status === 'fulfilled' ? ga4Sources.value : [];
        cache.ready = true;
        cache.fetching = false;
        return cache;
    }
    return await prefetchDomain(domain);
}

let _analyticsGSCDaily = [];
let _analyticsGA4Daily = [];

async function loadAnalytics() {
    const src = document.getElementById('analytics-source').value;
    ['gsc', 'ga4', 'meta', 'social'].forEach(s => {
        const el = document.getElementById('analytics-' + s);
        if (el) el.style.display = s === src ? 'block' : 'none';
    });

    const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;

    if (src === 'gsc') {
        try {
            const [daily, queries, pages] = await Promise.all([
                api(`/api/gsc/daily${qs}`),
                api(`/api/gsc/queries${qs}&limit=15`),
                api(`/api/gsc/pages${qs}&limit=15`),
            ]);
            _analyticsGSCDaily = daily || [];
            const gscSel = document.getElementById('a-gsc-metric-select');
            switchAnalyticsGSCMetric(gscSel ? gscSel.value : 'clicks-impressions');
            const ctrData = _analyticsGSCDaily.map(d => d.ctr || (d.impressions > 0 ? parseFloat(((d.clicks / d.impressions) * 100).toFixed(2)) : 0));
            const avgCtr = ctrData.length ? (ctrData.reduce((a, b) => a + b, 0) / ctrData.length).toFixed(2) : 0;
            makeChart('a-gsc-ctr', {
                type: 'line',
                data: {
                    labels: _analyticsGSCDaily.map(d => shortDate(d.date)),
                    datasets: [{ label: 'CTR %', data: ctrData, borderColor: CHART_COLORS.teal, backgroundColor: 'transparent', fill: false, tension: 0.4, pointRadius: 0, hoverRadius: 5 }]
                },
                options: {
                    scales: { x: {}, y: {} },
                    plugins: {
                        annotation: {
                            annotations: { avgLine: { type: 'line', yMin: avgCtr, yMax: avgCtr, borderColor: CHART_COLORS.teal + '60', borderDash: [6, 3], borderWidth: 1, label: { display: true, content: 'Avg ' + avgCtr + '%', position: 'end', font: { size: 10 } } } }
                        }
                    }
                }
            });
            makeChart('a-gsc-queries', {
                type: 'bar',
                data: {
                    labels: (queries || []).slice(0, 10).map(q => q.query),
                    datasets: [{ label: 'Clicks', data: (queries || []).slice(0, 10).map(q => q.clicks), backgroundColor: CHART_COLORS.purple, borderRadius: 6 }]
                },
                options: { indexAxis: 'y', scales: { x: {}, y: { ticks: { font: { size: 10 } } } } }
            });
            makeChart('a-gsc-pages', {
                type: 'bar',
                data: {
                    labels: (pages || []).slice(0, 10).map(p => shortUrl(p.page)),
                    datasets: [{ label: 'Clicks', data: (pages || []).slice(0, 10).map(p => p.clicks), backgroundColor: CHART_COLORS.blue, borderRadius: 6 }]
                },
                options: { indexAxis: 'y', scales: { x: {}, y: { ticks: { font: { size: 10 } } } } }
            });
        } catch (e) { console.error('Analytics GSC error:', e); }
    }

    if (src === 'ga4') {
        try {
            const [daily, sources, pages] = await Promise.all([
                api(`/api/ga4/daily${qs}`),
                api(`/api/ga4/sources${qs}`),
                api(`/api/ga4/pages${qs}&limit=15`),
            ]);
            _analyticsGA4Daily = daily || [];
            const ga4Sel = document.getElementById('a-ga4-metric-select');
            switchAnalyticsGA4Metric(ga4Sel ? ga4Sel.value : 'sessions-users');
            const summary = _ga4SummaryFromDaily(_analyticsGA4Daily);
            const el = document.getElementById('a-ga4-bounce');
            if (el) el.textContent = summary.bounce_rate + '%';
            if (sources && sources.length) {
                const total = sources.reduce((s, r) => s + (r.sessions || 0), 0);
                makeChart('a-ga4-sources', {
                    type: 'doughnut',
                    data: {
                        labels: sources.map(s => s.channel),
                        datasets: [{ data: sources.map(s => s.sessions), backgroundColor: CHART_COLORS.palette.slice(0, sources.length) }]
                    },
                    options: {
                        cutout: '70%',
                        plugins: {
                            legend: { position: 'right', labels: { font: { size: 10 }, padding: 8, boxWidth: 10 } },
                            tooltip: { callbacks: { label: function(ctx) {
                                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                                return ctx.label + ': ' + formatNum(ctx.parsed) + ' (' + pct + '%)';
                            }}}
                        }
                    }
                });
            }
            makeChart('a-ga4-pages', {
                type: 'bar',
                data: {
                    labels: (pages || []).slice(0, 10).map(p => shortUrl(p.page)),
                    datasets: [{ label: 'Views', data: (pages || []).slice(0, 10).map(p => p.views), backgroundColor: CHART_COLORS.purple, borderRadius: 6 }]
                },
                options: { indexAxis: 'y', scales: { x: {}, y: { ticks: { font: { size: 10 } } } } }
            });
        } catch (e) { console.error('Analytics GA4 error:', e); }
    }

    if (src === 'meta') {
        try {
            const mqs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
            const campaigns = await api(`/api/meta/campaigns${mqs}`);
            if (campaigns && campaigns.length) {
                makeChart('a-meta-spend', {
                    type: 'bar',
                    data: {
                        labels: campaigns.map(c => (c.name || '').slice(0, 20)),
                        datasets: [{ label: 'Spend (₹)', data: campaigns.map(c => parseFloat(c.spend) || 0), backgroundColor: CHART_COLORS.purple, borderRadius: 6 }]
                    },
                    options: { scales: { x: { ticks: { maxTicksLimit: 6 } }, y: {} } }
                });
                makeChart('a-meta-clicks', {
                    type: 'bar',
                    data: {
                        labels: campaigns.map(c => (c.name || '').slice(0, 20)),
                        datasets: [{ label: 'Clicks', data: campaigns.map(c => parseInt(c.clicks) || 0), backgroundColor: CHART_COLORS.blue, borderRadius: 6 }]
                    },
                    options: { scales: { x: { ticks: { maxTicksLimit: 6 } }, y: {} } }
                });
            }
            try {
                const daily = await api(`/api/meta/daily${mqs}`);
                if (daily && daily.length) {
                    const c = makeChart('a-meta-daily', {
                        type: 'line',
                        data: {
                            labels: daily.map(d => shortDate(d.date)),
                            datasets: [{ label: 'Spend (₹)', data: daily.map(d => parseFloat(d.spend) || 0), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, pointRadius: 0, hoverRadius: 5 }]
                        },
                        options: { scales: { x: {}, y: {} } }
                    });
                    applyGradient(c, 0, CHART_COLORS.purple);
                }
            } catch (e) {}
        } catch (e) {}
    }

    if (src === 'social') {
        try {
            const data = await api(`/api/social/trend?period=weekly&periods=5&domain=${currentDomain}`);
            if (data && data.length) {
                const last = data[data.length - 1];
                const fbF = document.getElementById('a-social-fb-followers');
                const igF = document.getElementById('a-social-ig-followers');
                if (fbF) fbF.textContent = formatNum((last.fb && last.fb.followers) || 0);
                if (igF) igF.textContent = formatNum((last.ig && last.ig.followers) || 0);

                const labels = data.map(p => p.period);
                makeChart('a-social-engagement', {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: [
                            { label: 'Facebook', data: data.map(p => (p.fb && p.fb.engagements) || 0), backgroundColor: '#1877F2', borderRadius: 6 },
                            { label: 'Instagram', data: data.map(p => (p.ig && p.ig.engagements) || 0), backgroundColor: '#E4405F', borderRadius: 6 },
                        ]
                    },
                    options: { scales: { x: {}, y: {} } }
                });
                const c3 = makeChart('a-social-reach', {
                    type: 'line',
                    data: {
                        labels,
                        datasets: [
                            { label: 'Facebook', data: data.map(p => (p.fb && p.fb.reach) || 0), borderColor: '#1877F2', backgroundColor: 'rgba(24,119,242,0.08)', fill: true, tension: 0.4, pointRadius: 0, hoverRadius: 5 },
                            { label: 'Instagram', data: data.map(p => (p.ig && p.ig.reach) || 0), borderColor: '#E4405F', backgroundColor: 'rgba(232,64,95,0.08)', fill: true, tension: 0.4, pointRadius: 0, hoverRadius: 5 },
                        ]
                    },
                    options: { scales: { x: {}, y: {} } }
                });
                makeChart('a-social-posts', {
                    type: 'bar',
                    data: {
                        labels,
                        datasets: [
                            { label: 'Facebook', data: data.map(p => (p.fb && p.fb.posts_published) || 0), backgroundColor: '#1877F2', borderRadius: 6 },
                            { label: 'Instagram', data: data.map(p => (p.ig && p.ig.posts_published) || 0), backgroundColor: '#E4405F', borderRadius: 6 },
                        ]
                    },
                    options: { scales: { x: {}, y: {} } }
                });
            }
        } catch (e) {}
    }
}

function switchAnalyticsGSCMetric(value) {
    const daily = _analyticsGSCDaily;
    if (!daily || !daily.length) return;
    const labels = daily.map(d => shortDate(d.date));
    const ctrData = daily.map(d => d.ctr || (d.impressions > 0 ? parseFloat(((d.clicks / d.impressions) * 100).toFixed(2)) : 0));
    const posData = daily.map(d => d.position || 0);
    let datasets = [], scales = { x: {} };
    const chartLabels = { 'clicks-impressions': 'Clicks & Impressions', 'clicks-ctr': 'Clicks & CTR', 'impressions-position': 'Impressions & Position', 'all': 'All Metrics' };
    const labelEl = document.getElementById('a-gsc-chart-label');
    if (labelEl) labelEl.textContent = chartLabels[value] || 'Clicks & Impressions';
    switch (value) {
        case 'clicks-impressions':
            datasets = [
                { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: CHART_COLORS.blue, backgroundColor: CHART_COLORS.blueLight, fill: true, tension: 0.4, yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', grid: { display: false } } };
            break;
        case 'clicks-ctr':
            datasets = [
                { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'CTR %', data: ctrData, borderColor: CHART_COLORS.teal, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', grid: { display: false } } };
            break;
        case 'impressions-position':
            datasets = [
                { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: CHART_COLORS.blue, backgroundColor: CHART_COLORS.blueLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Position', data: posData, borderColor: CHART_COLORS.amber, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', reverse: true, grid: { display: false } } };
            break;
        case 'all':
            datasets = [
                { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: CHART_COLORS.purple, backgroundColor: 'transparent', fill: false, tension: 0.4, yAxisID: 'y' },
                { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: CHART_COLORS.blue, backgroundColor: 'transparent', fill: false, tension: 0.4, yAxisID: 'y1' },
                { label: 'CTR %', data: ctrData, borderColor: CHART_COLORS.teal, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y2' },
                { label: 'Position', data: posData, borderColor: CHART_COLORS.amber, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y3' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { display: false }, y2: { display: false }, y3: { display: false, reverse: true } };
            break;
    }
    makeChart('a-gsc-clicks', { type: 'line', data: { labels, datasets }, options: { scales } });
}

function switchAnalyticsGA4Metric(value) {
    const daily = _analyticsGA4Daily;
    if (!daily || !daily.length) return;
    const labels = daily.map(d => shortDate(d.date));
    const chartLabels = { 'sessions-users': 'Sessions & Users', 'sessions-bounce': 'Sessions & Bounce Rate', 'pageviews': 'Pageviews', 'new-returning': 'New vs Returning Users' };
    const labelEl = document.getElementById('a-ga4-chart-label');
    if (labelEl) labelEl.textContent = chartLabels[value] || 'Sessions & Users';
    let datasets = [], scales = { x: {} };
    switch (value) {
        case 'sessions-users':
            datasets = [
                { label: 'Sessions', data: daily.map(d => d.sessions), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4 },
                { label: 'Users', data: daily.map(d => d.users || 0), borderColor: CHART_COLORS.green, backgroundColor: CHART_COLORS.greenLight, fill: true, tension: 0.4 },
            ];
            scales = { x: {}, y: {} };
            break;
        case 'sessions-bounce':
            datasets = [
                { label: 'Sessions', data: daily.map(d => d.sessions), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Bounce %', data: daily.map(d => parseFloat(((d.bounce_rate || 0) * 100).toFixed(1))), borderColor: CHART_COLORS.red, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', grid: { display: false } } };
            break;
        case 'pageviews':
            datasets = [
                { label: 'Pageviews', data: daily.map(d => d.pageviews || 0), borderColor: CHART_COLORS.blue, backgroundColor: CHART_COLORS.blueLight, fill: true, tension: 0.4 },
            ];
            scales = { x: {}, y: {} };
            break;
        case 'new-returning':
            datasets = [
                { label: 'New Users', data: daily.map(d => d.new_users || 0), borderColor: CHART_COLORS.green, backgroundColor: CHART_COLORS.greenLight, fill: true, tension: 0.4 },
                { label: 'Returning', data: daily.map(d => Math.max(0, (d.users || 0) - (d.new_users || 0))), borderColor: CHART_COLORS.amber, backgroundColor: 'rgba(245,158,11,0.08)', fill: true, tension: 0.4 },
            ];
            scales = { x: {}, y: {} };
            break;
    }
    makeChart('a-ga4-sessions', { type: 'line', data: { labels, datasets }, options: { scales } });
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

// ── Data loading (cache-aware) ──
let _dashGSCDaily = [];
let _dashGA4Daily = [];
let _dashGA4Sources = [];

async function loadGSC() {
    const overviewIds = ['gsc-clicks', 'gsc-impressions', 'gsc-ctr', 'gsc-position'];
    const detailIds = ['gsc-clicks-d', 'gsc-impressions-d', 'gsc-ctr-d', 'gsc-position-d'];
    [...overviewIds, ...detailIds].forEach(id => showLoading(id));
    try {
        const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
        const [daily, queries, pages] = await Promise.all([
            api(`/api/gsc/daily${qs}`),
            api(`/api/gsc/queries${qs}&limit=15`),
            api(`/api/gsc/pages${qs}&limit=15`),
        ]);
        _dashGSCDaily = daily || [];
        const summary = _gscSummaryFromDaily(_dashGSCDaily);
        const vals = [summary.clicks, summary.impressions, summary.ctr + '%', summary.position];
        overviewIds.forEach((id, i) => renderMetric(id, vals[i]));
        detailIds.forEach((id, i) => renderMetric(id, vals[i]));
        renderTable('gsc-queries-table', [
            { label: 'Query', key: 'query' }, { label: 'Clicks', key: 'clicks' },
            { label: 'Impressions', key: 'impressions' }, { label: 'CTR %', key: 'ctr' },
            { label: 'Position', key: 'position' },
        ], queries || []);
        renderTable('gsc-pages-table', [
            { label: 'Page', key: 'page' }, { label: 'Clicks', key: 'clicks' },
            { label: 'Impressions', key: 'impressions' }, { label: 'CTR %', key: 'ctr' },
            { label: 'Position', key: 'position' },
        ], pages || []);
        const gscMetricSel = document.getElementById('gsc-metric-select');
        switchGSCMetric(gscMetricSel ? gscMetricSel.value : 'clicks-impressions');
    } catch (e) {
        console.error('GSC error:', e);
        [...overviewIds, ...detailIds].forEach(id => { const el = document.getElementById(id); if (el) { el.className = 'metric-value'; el.textContent = '-'; } });
    }
}

async function loadGA4() {
    const overviewIds = ['ga4-sessions', 'ga4-users', 'ga4-pageviews', 'ga4-bounce'];
    const detailIds = ['ga4-sessions-d', 'ga4-users-d', 'ga4-pageviews-d', 'ga4-bounce-d'];
    [...overviewIds, ...detailIds].forEach(id => showLoading(id));
    try {
        const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
        const [daily, sources, pages] = await Promise.all([
            api(`/api/ga4/daily${qs}`),
            api(`/api/ga4/sources${qs}`),
            api(`/api/ga4/pages${qs}&limit=15`),
        ]);
        _dashGA4Daily = daily || [];
        _dashGA4Sources = sources || [];
        const summary = _ga4SummaryFromDaily(_dashGA4Daily);
        const vals = [summary.sessions, summary.users, summary.pageviews, summary.bounce_rate + '%'];
        overviewIds.forEach((id, i) => renderMetric(id, vals[i]));
        detailIds.forEach((id, i) => renderMetric(id, vals[i]));
        renderTable('ga4-sources-table', [
            { label: 'Channel', key: 'channel' }, { label: 'Sessions', key: 'sessions' }, { label: 'Users', key: 'users' },
        ], sources || []);
        renderTable('ga4-pages-table', [
            { label: 'Page', key: 'page' }, { label: 'Views', key: 'views' },
            { label: 'Sessions', key: 'sessions' }, { label: 'Avg Duration', key: 'avg_dur' },
        ], pages || []);
        const ga4MetricSel = document.getElementById('ga4-metric-select');
        switchGA4Metric(ga4MetricSel ? ga4MetricSel.value : 'sessions-users');
    } catch (e) {
        console.error('GA4 error:', e);
        [...overviewIds, ...detailIds].forEach(id => { const el = document.getElementById(id); if (el) { el.className = 'metric-value'; el.textContent = '-'; } });
    }
}

function switchGSCMetric(value) {
    const daily = _dashGSCDaily;
    if (!daily || !daily.length) return;
    const labels = daily.map(d => shortDate(d.date));
    const ctrData = daily.map(d => d.ctr || (d.impressions > 0 ? parseFloat(((d.clicks / d.impressions) * 100).toFixed(2)) : 0));
    const posData = daily.map(d => d.position || 0);
    let datasets = [], scales = { x: {} };
    switch (value) {
        case 'clicks-impressions':
            datasets = [
                { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: CHART_COLORS.blue, backgroundColor: CHART_COLORS.blueLight, fill: true, tension: 0.4, yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', grid: { display: false } } };
            break;
        case 'clicks-ctr':
            datasets = [
                { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'CTR %', data: ctrData, borderColor: CHART_COLORS.teal, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', grid: { display: false } } };
            break;
        case 'impressions-position':
            datasets = [
                { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: CHART_COLORS.blue, backgroundColor: CHART_COLORS.blueLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Position', data: posData, borderColor: CHART_COLORS.amber, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', reverse: true, grid: { display: false } } };
            break;
        case 'all':
            datasets = [
                { label: 'Clicks', data: daily.map(d => d.clicks), borderColor: CHART_COLORS.purple, backgroundColor: 'transparent', fill: false, tension: 0.4, yAxisID: 'y' },
                { label: 'Impressions', data: daily.map(d => d.impressions), borderColor: CHART_COLORS.blue, backgroundColor: 'transparent', fill: false, tension: 0.4, yAxisID: 'y1' },
                { label: 'CTR %', data: ctrData, borderColor: CHART_COLORS.teal, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y2' },
                { label: 'Position', data: posData, borderColor: CHART_COLORS.amber, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y3' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { display: false }, y2: { display: false }, y3: { display: false, reverse: true } };
            break;
    }
    makeChart('chart-gsc-perf', { type: 'line', data: { labels, datasets }, options: { scales } });
}

function switchGA4Metric(value) {
    const daily = _dashGA4Daily;
    if (!daily || !daily.length) return;
    const labels = daily.map(d => shortDate(d.date));
    let datasets = [], scales = { x: {} };
    switch (value) {
        case 'sessions-users':
            datasets = [
                { label: 'Sessions', data: daily.map(d => d.sessions), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Users', data: daily.map(d => d.users || 0), borderColor: CHART_COLORS.green, backgroundColor: CHART_COLORS.greenLight, fill: true, tension: 0.4, yAxisID: 'y' },
            ];
            scales = { x: {}, y: {} };
            break;
        case 'sessions-bounce':
            datasets = [
                { label: 'Sessions', data: daily.map(d => d.sessions), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Bounce %', data: daily.map(d => parseFloat(((d.bounce_rate || 0) * 100).toFixed(1))), borderColor: CHART_COLORS.red, backgroundColor: 'transparent', fill: false, tension: 0.4, borderDash: [4, 2], yAxisID: 'y1' },
            ];
            scales = { x: {}, y: { position: 'left' }, y1: { position: 'right', grid: { display: false } } };
            break;
        case 'pageviews':
            datasets = [
                { label: 'Pageviews', data: daily.map(d => d.pageviews || 0), borderColor: CHART_COLORS.blue, backgroundColor: CHART_COLORS.blueLight, fill: true, tension: 0.4 },
            ];
            scales = { x: {}, y: {} };
            break;
        case 'new-returning':
            datasets = [
                { label: 'New Users', data: daily.map(d => d.new_users || 0), borderColor: CHART_COLORS.green, backgroundColor: CHART_COLORS.greenLight, fill: true, tension: 0.4, yAxisID: 'y' },
                { label: 'Returning Users', data: daily.map(d => Math.max(0, (d.users || 0) - (d.new_users || 0))), borderColor: CHART_COLORS.amber, backgroundColor: 'rgba(245,158,11,0.08)', fill: true, tension: 0.4, yAxisID: 'y' },
            ];
            scales = { x: {}, y: {} };
            break;
    }
    makeChart('chart-ga4-quality', { type: 'line', data: { labels, datasets }, options: { scales } });
}

async function loadMeta() {
    try {
        const statusFilterEl = document.getElementById('meta-status-filter');
        const statusVal = statusFilterEl ? statusFilterEl.value : 'active';
        const qs = `?domain=${currentDomain}&start=${dateStart}&end=${dateEnd}`;
        let campaigns;
        try {
            campaigns = await api(`/api/meta/campaigns${qs}&status=${statusVal}`);
        } catch (e) {
            if (e.message && e.message.includes('not configured')) {
                const el = document.getElementById('meta-overview');
                if (el) el.innerHTML = '<div class="empty-state"><p>Meta Ads not configured for this domain</p></div>';
                const t = document.getElementById('meta-campaigns-table');
                if (t) t.innerHTML = '<div class="empty-state"><p>Meta Ads not configured for this domain</p></div>';
                return;
            }
            throw e;
        }
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
                    <div class="metric-card"><div class="accent-strip" style="background:#7C3AED"></div><div class="metric-label">Total Spend</div><div class="metric-value">₹${formatNum(Math.round(totalSpend))}</div></div>
                    <div class="metric-card"><div class="accent-strip" style="background:#0EA5E9"></div><div class="metric-label">Clicks</div><div class="metric-value">${formatNum(totalClicks)}</div></div>
                    <div class="metric-card"><div class="accent-strip" style="background:#10B981"></div><div class="metric-label">Impressions</div><div class="metric-value">${formatNum(totalImpressions)}</div></div>
                    <div class="metric-card"><div class="accent-strip" style="background:#F59E0B"></div><div class="metric-label">Campaigns</div><div class="metric-value">${campaigns.length}</div></div>
                </div>`;
        }
        // Ad Spend vs Results grouped bar
        try {
            if (campaigns && campaigns.length) {
                makeChart('chart-meta-campaigns', {
                    type: 'bar',
                    data: {
                        labels: campaigns.map(c => (c.name||'').slice(0,20)),
                        datasets: [
                            { label: 'Spend (₹)', data: campaigns.map(c => parseFloat(c.spend) || 0), backgroundColor: CHART_COLORS.purple, borderRadius: 4 },
                            { label: 'Clicks', data: campaigns.map(c => parseInt(c.clicks) || 0), backgroundColor: CHART_COLORS.blue, borderRadius: 4 },
                        ]
                    },
                    options: { scales: { x: { ticks: { maxTicksLimit: 6 } }, y: {} } }
                });
            }
        } catch(e) {}
    } catch (e) {
        showError('meta-overview', e.message);
    }
}

let socialView = 'table';
let socialCalYear, socialCalMonth;
let socialCalFbPosts = [], socialCalIgMedia = [];

function switchSocialView(view) {
    socialView = view;
    document.querySelectorAll('[data-social-view]').forEach(b => b.classList.toggle('active', b.dataset.socialView === view));
    document.getElementById('social-table-view').style.display = view === 'table' ? '' : 'none';
    document.getElementById('social-calendar-view').style.display = view === 'calendar' ? '' : 'none';
    document.getElementById('social-period-toggle').style.display = view === 'table' ? '' : 'none';
    if (view === 'calendar') loadSocialCalendar();
}

function switchSocialPeriod(period) {
    socialPeriod = period;
    document.querySelectorAll('[data-social-period]').forEach(b => b.classList.toggle('active', b.dataset.socialPeriod === period));
    loadSocial();
}

async function loadSocialCalendar() {
    // Default to the month of dateStart
    if (!socialCalYear) {
        const ds = dateStart || todayIST();
        socialCalYear = parseInt(ds.slice(0, 4));
        socialCalMonth = parseInt(ds.slice(5, 7)) - 1;
    }
    renderSocialCalendarShell();
    await fetchAndRenderCalendar();
}

async function socialCalNav(dir) {
    socialCalMonth += dir;
    if (socialCalMonth > 11) { socialCalMonth = 0; socialCalYear++; }
    if (socialCalMonth < 0) { socialCalMonth = 11; socialCalYear--; }
    document.getElementById('social-cal-detail').style.display = 'none';
    await fetchAndRenderCalendar();
}

async function fetchAndRenderCalendar() {
    const mm = String(socialCalMonth + 1).padStart(2, '0');
    const mStart = `${socialCalYear}-${mm}-01`;
    const lastDayNum = new Date(socialCalYear, socialCalMonth + 1, 0).getDate();
    const mEnd = `${socialCalYear}-${mm}-${String(lastDayNum).padStart(2, '0')}`;

    const labelDate = new Date(socialCalYear, socialCalMonth, 1);
    document.getElementById('social-cal-month-label').textContent = labelDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    // Fetch FB posts & IG media for this month
    socialCalFbPosts = [];
    socialCalIgMedia = [];
    try {
        const posts = await api(`/api/social/page-posts?start=${mStart}&end=${mEnd}&limit=100&domain=${currentDomain}`);
        socialCalFbPosts = posts || [];
    } catch(e) {}
    try {
        const igResp = await api(`/api/social/ig-account?domain=${currentDomain}`);
        if (igResp && igResp.ig_id) {
            const media = await api(`/api/social/ig-media?ig_id=${igResp.ig_id}&limit=100&domain=${currentDomain}`);
            socialCalIgMedia = (media || []).filter(m => {
                const d = (m.timestamp || '').slice(0, 10);
                return d >= mStart && d <= mEnd;
            });
        }
    } catch(e) {}

    renderCalendarGrid(mStart, mEnd);
    renderCalendarSummary(mStart, mEnd);
}

function renderSocialCalendarShell() {
    // already in HTML
}

function renderCalendarGrid(mStart, mEnd) {
    const grid = document.getElementById('social-cal-grid');
    if (!grid) return;

    const year = socialCalYear, month = socialCalMonth;
    const firstDow = new Date(year, month, 1).getDay(); // 0=Sun
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = todayIST();

    // Map posts by date
    const fbByDate = {};
    socialCalFbPosts.forEach(p => {
        const d = (p.created_time || '').slice(0, 10);
        if (!fbByDate[d]) fbByDate[d] = [];
        fbByDate[d].push(p);
    });
    const igByDate = {};
    socialCalIgMedia.forEach(m => {
        const d = (m.timestamp || '').slice(0, 10);
        if (!igByDate[d]) igByDate[d] = [];
        igByDate[d].push(m);
    });

    let html = '';
    // Empty cells before first day
    for (let i = 0; i < firstDow; i++) {
        html += `<div style="min-height:80px; border-radius:8px; background:var(--glass-bg); opacity:0.3;"></div>`;
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${year}-${String(month + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        const isToday = dateStr === today;
        const fbPosts = fbByDate[dateStr] || [];
        const igPosts = igByDate[dateStr] || [];
        const hasPosts = fbPosts.length > 0 || igPosts.length > 0;

        const todayBorder = isToday ? 'border:2px solid var(--accent);' : 'border:1px solid var(--border-color);';
        const activeBg = hasPosts ? 'background:var(--glass-bg-hover,rgba(124,58,237,0.06));' : 'background:var(--glass-bg);';

        html += `<div onclick="socialCalSelectDay('${dateStr}')"
            style="min-height:80px; border-radius:8px; ${todayBorder} ${activeBg}
            padding:0.45rem; cursor:${hasPosts ? 'pointer' : 'default'};
            transition:all 0.15s; position:relative; overflow:hidden;"
            onmouseenter="if(${hasPosts}) this.style.transform='translateY(-2px)'"
            onmouseleave="this.style.transform=''">
            <div style="font-size:0.75rem; font-weight:${isToday ? '800' : '600'};
                color:${isToday ? 'var(--accent)' : 'var(--text-secondary)'};
                margin-bottom:0.35rem;">${day}</div>`;

        // FB badges
        fbPosts.slice(0, 2).forEach(p => {
            const snippet = (p.message || 'Post').slice(0, 22);
            html += `<div title="${esc(p.message || '')}"
                style="background:#1877F2; color:#fff; border-radius:4px;
                font-size:0.6rem; font-weight:600; padding:2px 5px;
                margin-bottom:2px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
                ${esc(snippet)}</div>`;
        });
        if (fbPosts.length > 2) {
            html += `<div style="font-size:0.6rem; color:#1877F2; font-weight:700; margin-bottom:2px;">+${fbPosts.length - 2} more FB</div>`;
        }

        // IG badges
        igPosts.slice(0, 2).forEach(m => {
            const snippet = (m.caption || m.media_type || 'Post').slice(0, 22);
            html += `<div title="${esc(m.caption || '')}"
                style="background:#E4405F; color:#fff; border-radius:4px;
                font-size:0.6rem; font-weight:600; padding:2px 5px;
                margin-bottom:2px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
                ${esc(snippet)}</div>`;
        });
        if (igPosts.length > 2) {
            html += `<div style="font-size:0.6rem; color:#E4405F; font-weight:700;">+${igPosts.length - 2} more IG</div>`;
        }

        html += `</div>`;
    }
    grid.innerHTML = html;
}

function socialCalSelectDay(dateStr) {
    const panel = document.getElementById('social-cal-detail');
    const dateLabel = document.getElementById('social-cal-detail-date');
    const postsEl = document.getElementById('social-cal-detail-posts');
    if (!panel) return;

    const fbByDate = {};
    socialCalFbPosts.forEach(p => {
        const d = (p.created_time || '').slice(0, 10);
        if (!fbByDate[d]) fbByDate[d] = [];
        fbByDate[d].push(p);
    });
    const igByDate = {};
    socialCalIgMedia.forEach(m => {
        const d = (m.timestamp || '').slice(0, 10);
        if (!igByDate[d]) igByDate[d] = [];
        igByDate[d].push(m);
    });

    const fbPosts = fbByDate[dateStr] || [];
    const igPosts = igByDate[dateStr] || [];
    if (fbPosts.length === 0 && igPosts.length === 0) return;

    const dt = new Date(dateStr + 'T00:00:00');
    dateLabel.textContent = dt.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

    let html = '';
    fbPosts.forEach(p => {
        html += `<div style="border-left:3px solid #1877F2; padding:0.75rem; border-radius:0 8px 8px 0; background:rgba(24,119,242,0.06);">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
                <span style="width:8px;height:8px;border-radius:50%;background:#1877F2;flex-shrink:0;"></span>
                <span style="font-size:0.7rem; font-weight:700; color:#1877F2; letter-spacing:0.04em;">FACEBOOK</span>
                ${p.permalink ? `<a href="${p.permalink}" target="_blank" style="margin-left:auto; font-size:0.68rem; color:var(--text-muted); text-decoration:none;">View →</a>` : ''}
            </div>
            <div style="font-size:0.82rem; color:var(--text-primary); line-height:1.5; margin-bottom:0.5rem;">${esc(p.message || '(no caption)')}</div>
            <div style="display:flex; gap:1rem; flex-wrap:wrap;">
                <span style="font-size:0.7rem; color:var(--text-muted);">👍 ${p.post_engaged_users || 0} engaged</span>
                <span style="font-size:0.7rem; color:var(--text-muted);">🔁 ${p.shares || 0} shares</span>
                <span style="font-size:0.7rem; color:var(--text-muted);">👁 ${p.post_impressions || 0} impressions</span>
            </div>
        </div>`;
    });
    igPosts.forEach(m => {
        html += `<div style="border-left:3px solid #E4405F; padding:0.75rem; border-radius:0 8px 8px 0; background:rgba(228,64,95,0.06);">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
                <span style="width:8px;height:8px;border-radius:50%;background:#E4405F;flex-shrink:0;"></span>
                <span style="font-size:0.7rem; font-weight:700; color:#E4405F; letter-spacing:0.04em;">INSTAGRAM</span>
                <span style="margin-left:auto; font-size:0.68rem; color:var(--text-muted);">${m.media_type || ''}</span>
            </div>
            <div style="font-size:0.82rem; color:var(--text-primary); line-height:1.5; margin-bottom:0.5rem;">${esc((m.caption || '(no caption)').slice(0, 300))}</div>
            <div style="display:flex; gap:1rem; flex-wrap:wrap;">
                <span style="font-size:0.7rem; color:var(--text-muted);">❤️ ${m.like_count || 0} likes</span>
                <span style="font-size:0.7rem; color:var(--text-muted);">💬 ${m.comments_count || 0} comments</span>
            </div>
        </div>`;
    });

    postsEl.innerHTML = html;
    panel.style.display = '';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderCalendarSummary(mStart, mEnd) {
    const el = document.getElementById('social-cal-summary');
    if (!el) return;
    const fbTotal = socialCalFbPosts.length;
    const igTotal = socialCalIgMedia.length;
    const fbEng = socialCalFbPosts.reduce((s, p) => s + (p.post_engaged_users || 0), 0);
    const igLikes = socialCalIgMedia.reduce((s, m) => s + (m.like_count || 0), 0);
    const igComments = socialCalIgMedia.reduce((s, m) => s + (m.comments_count || 0), 0);

    const stat = (label, val, color) => `
        <div class="glass-card-static" style="padding:1rem; text-align:center;">
            <div style="font-size:1.5rem; font-weight:800; color:${color};">${val}</div>
            <div style="font-size:0.7rem; font-weight:600; color:var(--text-muted); margin-top:0.25rem; letter-spacing:0.04em;">${label}</div>
        </div>`;

    el.innerHTML =
        stat('FB Posts', fbTotal, '#1877F2') +
        stat('IG Posts', igTotal, '#E4405F') +
        stat('FB Engagements', fbEng, '#1877F2') +
        stat('IG Likes', igLikes, '#E4405F') +
        stat('IG Comments', igComments, '#E4405F');
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
        const data = await api(`/api/social/trend?period=${socialPeriod}&periods=5&domain=${currentDomain}`);
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

        // Engagement bar chart (combined FB + IG)
        try {
            const labels = data.map(p => p.period);
            makeChart('chart-social-engagement', {
                type: 'bar',
                data: {
                    labels,
                    datasets: [
                        { label: 'Facebook', data: data.map(p => (p.fb && p.fb.engagements) || 0), backgroundColor: '#1877F2', borderRadius: 4 },
                        { label: 'Instagram', data: data.map(p => (p.ig && p.ig.engagements) || 0), backgroundColor: '#E4405F', borderRadius: 4 },
                    ]
                },
                options: { scales: { x: {}, y: {} } }
            });
        } catch(e) {}

        // Reach area chart (combined)
        try {
            const labels = data.map(p => p.period);
            makeChart('chart-social-reach', {
                type: 'line',
                data: {
                    labels,
                    datasets: [
                        { label: 'Facebook', data: data.map(p => (p.fb && p.fb.reach) || 0), borderColor: '#1877F2', backgroundColor: 'rgba(24,119,242,0.08)', fill: true, tension: 0.4 },
                        { label: 'Instagram', data: data.map(p => (p.ig && p.ig.reach) || 0), borderColor: '#E4405F', backgroundColor: 'rgba(232,64,95,0.08)', fill: true, tension: 0.4 },
                    ]
                },
                options: { scales: { x: {}, y: {} } }
            });
        } catch(e) {}
    } catch (e) {
        tableEl.innerHTML = `<div class="error-msg">${esc(e.message)}</div>`;
    }
    try {
        const posts = await api(`/api/social/page-posts?start=${dateStart}&end=${dateEnd}&domain=${currentDomain}`);
        renderTable('fb-posts-table', [
            { label: 'Post', key: 'message' }, { label: 'Impressions', key: 'post_impressions' },
            { label: 'Engaged', key: 'post_engaged_users' }, { label: 'Clicks', key: 'post_clicks' }, { label: 'Shares', key: 'shares' },
        ], posts);
    } catch (e) { showError('fb-posts-table', e.message); }
    try {
        const igResp = await api(`/api/social/ig-account?domain=${currentDomain}`);
        if (igResp.ig_id) {
            const igMedia = await api(`/api/social/ig-media?ig_id=${igResp.ig_id}&domain=${currentDomain}`);
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
        // Organic Growth area chart
        try {
            makeChart('chart-seo-organic', {
                type: 'line',
                data: {
                    labels: data.map(d => d.period),
                    datasets: [
                        { label: 'Organic Sessions', data: data.map(d => d.organic_sessions || 0), borderColor: CHART_COLORS.green, backgroundColor: CHART_COLORS.greenLight, fill: true, tension: 0.4 },
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

function _copyToClipboard(text, btnEl) {
    navigator.clipboard.writeText(text).then(() => {
        const orig = btnEl.textContent;
        btnEl.textContent = 'Copied!';
        btnEl.style.background = '#10B981';
        setTimeout(() => { btnEl.textContent = orig; btnEl.style.background = ''; }, 1500);
    });
}

async function generateSEO() {
    const topic = document.getElementById('yt-seo-topic').value.trim();
    if (!topic) return;
    const speaker = (document.getElementById('yt-seo-speaker')?.value || '').trim();
    const transcript = (document.getElementById('yt-seo-transcript')?.value || '').trim();
    const resultEl = document.getElementById('yt-seo-result');
    resultEl.innerHTML = '<div class="empty-state"><p style="color:var(--accent-primary);">Generating SEO content...</p></div>';
    try {
        let url = `/api/youtube/seo?topic=${encodeURIComponent(topic)}`;
        if (speaker) url += `&speaker=${encodeURIComponent(speaker)}`;
        if (transcript) url += `&transcript=${encodeURIComponent(transcript)}`;
        const seo = await api(url);
        let html = '';

        html += '<div class="glass-card-static" style="padding:1.5rem; margin-bottom:1rem;">';
        html += '<div class="table-title" style="margin-bottom:0.75rem;">Suggested Titles</div>';
        (seo.titles || []).forEach((t, i) => {
            const badge = t.type === 'SEO Optimized'
                ? '<span style="background:#7C3AED20;color:#7C3AED;padding:2px 8px;border-radius:9999px;font-size:0.7rem;font-weight:700;margin-right:0.5rem;">SEO</span>'
                : '<span style="background:#0EA5E920;color:#0EA5E9;padding:2px 8px;border-radius:9999px;font-size:0.7rem;font-weight:700;margin-right:0.5rem;">BRAND</span>';
            html += `<div style="display:flex;align-items:center;justify-content:space-between;padding:0.6rem 0.75rem;background:var(--surface-input);border-radius:0.6rem;margin-bottom:0.5rem;">
                <div style="font-size:0.85rem;font-weight:500;">${badge}${esc(t.title)}</div>
                <button onclick="_copyToClipboard('${esc(t.title).replace(/'/g,"\\'")}', this)" style="background:var(--accent-primary-soft);color:var(--accent-primary);border:none;padding:4px 12px;border-radius:6px;font-size:0.72rem;font-weight:700;cursor:pointer;white-space:nowrap;">Copy</button>
            </div>`;
        });
        html += '</div>';

        html += '<div class="glass-card-static" style="padding:1.5rem; margin-bottom:1rem;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;"><div class="table-title" style="margin:0;">Description</div>';
        html += `<button id="copy-desc-btn" style="background:var(--accent-primary-soft);color:var(--accent-primary);border:none;padding:4px 12px;border-radius:6px;font-size:0.72rem;font-weight:700;cursor:pointer;">Copy</button></div>`;
        html += `<pre id="seo-desc-text" style="white-space:pre-wrap;font-size:0.8rem;background:var(--surface-input);padding:1rem;border-radius:0.75rem;font-family:Inter,sans-serif;line-height:1.6;max-height:300px;overflow-y:auto;">${esc(seo.description)}</pre>`;
        html += '</div>';

        html += '<div class="glass-card-static" style="padding:1.5rem; margin-bottom:1rem;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;"><div class="table-title" style="margin:0;">Hashtags</div>';
        html += `<button id="copy-hash-btn" style="background:var(--accent-primary-soft);color:var(--accent-primary);border:none;padding:4px 12px;border-radius:6px;font-size:0.72rem;font-weight:700;cursor:pointer;">Copy All</button></div>`;
        html += '<div style="display:flex;flex-wrap:wrap;gap:0.4rem;" id="seo-hashtags-wrap">';
        seo.hashtags.forEach(h => html += `<span style="background:var(--accent-primary-soft);color:var(--accent-primary);padding:0.3rem 0.7rem;border-radius:9999px;font-size:0.75rem;font-weight:600;">${esc(h)}</span>`);
        html += '</div></div>';

        html += '<div class="glass-card-static" style="padding:1.5rem;">';
        html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.75rem;"><div class="table-title" style="margin:0;">Tags</div>';
        html += `<button id="copy-tags-btn" style="background:var(--accent-primary-soft);color:var(--accent-primary);border:none;padding:4px 12px;border-radius:6px;font-size:0.72rem;font-weight:700;cursor:pointer;">Copy All</button></div>`;
        html += '<div style="display:flex;flex-wrap:wrap;gap:0.4rem;" id="seo-tags-wrap">';
        seo.tags.forEach(t => html += `<span style="background:var(--surface-hover);padding:0.3rem 0.7rem;border-radius:9999px;font-size:0.75rem;">${esc(t)}</span>`);
        html += '</div></div>';

        resultEl.innerHTML = html;

        document.getElementById('copy-desc-btn').onclick = function() {
            _copyToClipboard(seo.description, this);
        };
        document.getElementById('copy-hash-btn').onclick = function() {
            _copyToClipboard(seo.hashtags.join(' '), this);
        };
        document.getElementById('copy-tags-btn').onclick = function() {
            _copyToClipboard(seo.tags.join(', '), this);
        };
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
    analyticsLoaded = {};
    await Promise.allSettled([loadGSC(), loadGA4(), loadMeta()]);
    try {
        const gscData = _dashGSCDaily || [];
        const ga4Data = _dashGA4Daily || [];
        const labels = (gscData.length >= ga4Data.length ? gscData : ga4Data).map(d => shortDate(d.date));
        makeChart('chart-overview-trend', {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Clicks', data: gscData.map(d => d.clicks), borderColor: CHART_COLORS.purple, backgroundColor: CHART_COLORS.purpleLight, fill: true, tension: 0.4 },
                    { label: 'Sessions', data: ga4Data.map(d => d.sessions), borderColor: CHART_COLORS.green, backgroundColor: CHART_COLORS.greenLight, fill: true, tension: 0.4 },
                ]
            },
            options: { scales: { x: {}, y: {} } }
        });
        const sources = _dashGA4Sources || [];
        if (sources.length) {
            makeChart('chart-overview-sources', {
                type: 'doughnut',
                data: {
                    labels: sources.map(s => s.channel),
                    datasets: [{ data: sources.map(s => s.sessions), backgroundColor: CHART_COLORS.palette.slice(0, sources.length) }]
                },
                options: {
                    plugins: {
                        legend: { position: 'right', labels: { font: { size: 10 }, padding: 8, boxWidth: 10 } },
                        tooltip: { callbacks: { label: function(ctx) {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                            return ctx.label + ': ' + formatNum(ctx.parsed) + ' (' + pct + '%)';
                        }}}
                    }
                }
            });
        }
    } catch(e) {}
}

function reloadActiveDashTab() {
    if (currentDashTab === 'social') loadSocial();
    else if (currentDashTab === 'youtube') loadYouTube();
    else if (currentDashTab === 'seo') loadSEOWeekly();
    else if (currentDashTab === 'meta') loadMeta();
}

function switchDomain(key) {
    currentDomain = key;
    document.querySelectorAll('.domain-tab[data-domain]').forEach(t => t.classList.toggle('active', t.dataset.domain === key));
    const d = domains[key];
    if (d) document.getElementById('topbar-title').textContent = d.label;
    analyticsLoaded = {};
    loadAll();
    reloadActiveDashTab();
    if (currentView === 'analytics') loadAnalytics();
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
    const entity = r.entity_detected || '';
    const entityColors = { RH: '#7C3AED', PMS: '#0EA5E9', AIF: '#10B981' };
    const entityColor = entityColors[entity] || 'var(--text-muted)';
    let html = `<div class="glass-card-static" style="padding:1.5rem;">
        <div style="display:flex; align-items:center; gap:1.5rem; flex-wrap:wrap;">
            <div style="font-size:3rem; font-weight:800; color:${color};">${score}<span style="font-size:1rem; color:var(--text-muted);">/100</span></div>
            <div>
                <div style="font-weight:700; margin-bottom:0.25rem;">${esc(r.summary || '')}</div>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:0.4rem;">
                    <span style="background:${ready ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; color:${ready ? '#10B981' : '#ef4444'}; padding:0.25rem 0.6rem; border-radius:9999px; font-size:0.7rem; font-weight:700;">${ready ? 'PUBLISH READY' : 'NEEDS WORK'}</span>
                    ${entity ? `<span style="background:${entityColor}15; color:${entityColor}; padding:0.25rem 0.6rem; border-radius:9999px; font-size:0.7rem; font-weight:700;">Entity: ${esc(entity)}</span>` : ''}
                </div>
            </div>
        </div>
    </div>`;
    const compIssues = r.compliance_issues || [];
    if (compIssues.length) {
        const sevColors = { critical: '#ef4444', warning: '#F59E0B', info: '#0EA5E9' };
        html += `<div class="glass-card-static" style="padding:1.25rem; margin-top:1rem; border-left:4px solid #ef4444;">
            <div class="section-label" style="color:#ef4444;">Compliance Issues</div>
            <ul style="margin:0.5rem 0 0 1.25rem; font-size:0.85rem; line-height:1.8; list-style:none;">
                ${compIssues.map(c => {
                    const sc = sevColors[c.severity] || '#F59E0B';
                    return `<li style="margin-bottom:0.4rem;">
                        <span style="background:${sc}15; color:${sc}; padding:0.15rem 0.5rem; border-radius:9999px; font-size:0.65rem; font-weight:700; text-transform:uppercase; margin-right:0.5rem;">${esc(c.severity || 'warning')}</span>
                        ${esc(c.issue || '')}
                        ${c.guideline_ref ? `<span style="color:var(--text-muted); font-size:0.75rem;"> — ${esc(c.guideline_ref)}</span>` : ''}
                    </li>`;
                }).join('')}
            </ul>
        </div>`;
    }
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

function setRepRange(preset) {
    document.querySelectorAll('[data-rep-range]').forEach(b => b.classList.toggle('active', b.dataset.repRange === preset));
    const today = todayIST();
    const yesterday = offsetIST(today, -1);
    let s, e;
    switch (preset) {
        case '7d': s = offsetIST(yesterday, -6); e = yesterday; break;
        case '28d': s = offsetIST(yesterday, -27); e = yesterday; break;
        case '3m': s = offsetIST(yesterday, -89); e = yesterday; break;
        case '6m': s = offsetIST(yesterday, -179); e = yesterday; break;
        case 'thismonth': {
            const t = today.split('-');
            s = `${t[0]}-${t[1]}-01`;
            e = yesterday;
            break;
        }
        case 'lastmonth': {
            const d = new Date(today + 'T00:00:00+05:30');
            d.setDate(1); d.setMonth(d.getMonth() - 1);
            s = d.toISOString().split('T')[0];
            const d2 = new Date(today + 'T00:00:00+05:30');
            d2.setDate(0);
            e = d2.toISOString().split('T')[0];
            break;
        }
        default: s = offsetIST(yesterday, -27); e = yesterday;
    }
    document.getElementById('rep-start').value = s;
    document.getElementById('rep-end').value = e;
}

function _repDomain() {
    const sel = document.getElementById('rep-domain');
    return sel ? sel.value : currentDomain;
}

async function generateReport() {
    const start = document.getElementById('rep-start').value;
    const end = document.getElementById('rep-end').value;
    const dom = _repDomain();
    const el = document.getElementById('rep-result');
    el.innerHTML = '<div class="empty-state"><p>Generating report…</p></div>';
    try {
        const qs = `?period=${repPeriod}&domain=${dom}&start=${start}&end=${end}`;
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
    const dom = _repDomain();
    window.location.href = `/api/reports/export?period=${repPeriod}&domain=${dom}&start=${start}&end=${end}&format=${fmt}`;
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
        // Populate report domain dropdown
        const repDom = document.getElementById('rep-domain');
        if (repDom) {
            repDom.innerHTML = '';
            Object.entries(domains).forEach(([key, d]) => {
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = d.label;
                if (key === currentDomain) opt.selected = true;
                repDom.appendChild(opt);
            });
        }
    } catch (e) { console.error('Failed to load domains', e); }

    // Set default report dates
    setRepRange('28d');

    document.querySelectorAll('#date-range-group .dr-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            setDates(btn.dataset.preset);
            loadAll();
            reloadActiveDashTab();
            if (currentView === 'analytics') loadAnalytics();
        });
    });
    function _onDateChange() {
        activePreset = '';
        document.querySelectorAll('#date-range-group .dr-btn').forEach(b => b.classList.remove('active'));
        if (dateStart) { const d = new Date(dateStart); socialCalYear = d.getFullYear(); socialCalMonth = d.getMonth(); }
        loadAll();
        reloadActiveDashTab();
        if (currentView === 'analytics') loadAnalytics();
    }

    if (typeof flatpickr !== 'undefined') {
        const fpOpts = {
            dateFormat: 'Y-m-d',
            disableMobile: true,
            theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light',
        };
        flatpickr('#date-start', { ...fpOpts, defaultDate: dateStart, onChange: (sel, ds) => { dateStart = ds; _onDateChange(); } });
        flatpickr('#date-end', { ...fpOpts, defaultDate: dateEnd, onChange: (sel, ds) => { dateEnd = ds; _onDateChange(); } });
    } else {
        document.getElementById('date-start').addEventListener('change', (e) => { dateStart = e.target.value; _onDateChange(); });
        document.getElementById('date-end').addEventListener('change', (e) => { dateEnd = e.target.value; _onDateChange(); });
    }

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

    // Default calendar month
    document.getElementById('cal-month').value = todayIST().slice(0, 7);

    const loader = document.getElementById('page-loader');
    if (loader) { loader.classList.add('fade'); setTimeout(() => loader.remove(), 400); }

    loadAll();
});
