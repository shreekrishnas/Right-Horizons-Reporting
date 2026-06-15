const API = '';
let currentDomain = 'rh';
let currentView = 'overview';
let domains = {};
let dateStart = '';
let dateEnd = '';
let activePreset = '28d';
let socialPeriod = 'weekly';
let seoPeriod = 'weekly';

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
    ['overview', 'gsc', 'ga4', 'meta', 'seo', 'social', 'youtube', 'linkedin'].forEach(v => {
        const el = document.getElementById('view-' + v);
        if (el) el.style.display = v === view ? 'block' : 'none';
    });
    document.querySelectorAll('.sidebar-item').forEach(b => {
        b.classList.toggle('active', b.dataset.view === view);
    });
    const subtitles = {
        overview: 'Reporting Dashboard', gsc: 'Search Console', ga4: 'Google Analytics',
        meta: 'Meta Ads', seo: 'SEO Weekly', social: 'Social Media', youtube: 'YouTube', linkedin: 'LinkedIn',
    };
    const sub = document.getElementById('topbar-sub');
    if (sub) sub.textContent = subtitles[view] || 'Dashboard';

    if (view === 'social') loadSocial();
    if (view === 'youtube') loadYouTube();
    if (view === 'seo') loadSEOWeekly();
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

function switchSocialPeriod(period) {
    socialPeriod = period;
    document.querySelectorAll('[data-social-period]').forEach(b =>
        b.classList.toggle('active', b.dataset.socialPeriod === period));
    loadSocial();
}

function switchSEOPeriod(period) {
    seoPeriod = period;
    document.querySelectorAll('[data-seo-period]').forEach(b =>
        b.classList.toggle('active', b.dataset.seoPeriod === period));
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
    tableEl.innerHTML = '<div class="empty-state"><p>Loading social media data...</p></div>';

    try {
        const data = await api(`/api/social/trend?period=${socialPeriod}&periods=5`);
        if (!data || data.length === 0) {
            tableEl.innerHTML = '<div class="empty-state"><p>No social data available</p></div>';
            return;
        }

        let html = '<table><thead><tr><th style="width:30%">Metric</th>';
        data.forEach(p => html += `<th style="text-align:center; font-size:0.7rem;">${p.period}</th>`);
        html += '</tr></thead><tbody>';

        html += `<tr><td colspan="${data.length + 1}" style="background:rgba(232,64,95,0.08); font-weight:800; font-size:0.7rem; letter-spacing:0.08em; color:#E4405F; padding:0.5rem 1rem;">📷 INSTAGRAM</td></tr>`;
        socialMetricsDef.forEach(m => {
            html += `<tr><td style="font-weight:600;">${m.label}</td>`;
            data.forEach(p => {
                const val = p.ig && p.ig[m.ig] !== undefined ? p.ig[m.ig] : '-';
                html += `<td style="text-align:center;">${formatNum(val)}</td>`;
            });
            html += '</tr>';
        });

        html += `<tr><td colspan="${data.length + 1}" style="background:rgba(24,119,242,0.08); font-weight:800; font-size:0.7rem; letter-spacing:0.08em; color:#1877F2; padding:0.5rem 1rem;">👥 FACEBOOK</td></tr>`;
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
    } catch (e) {
        tableEl.innerHTML = `<div class="error-msg">${e.message}</div>`;
    }

    try {
        const posts = await api(`/api/social/page-posts?start=${dateStart}&end=${dateEnd}`);
        renderTable('fb-posts-table', [
            { label: 'Post', key: 'message' },
            { label: 'Impressions', key: 'post_impressions' },
            { label: 'Engaged', key: 'post_engaged_users' },
            { label: 'Clicks', key: 'post_clicks' },
            { label: 'Shares', key: 'shares' },
        ], posts);
    } catch (e) {
        showError('fb-posts-table', e.message);
    }

    try {
        const igResp = await api('/api/social/ig-account');
        if (igResp.ig_id) {
            const igMedia = await api(`/api/social/ig-media?ig_id=${igResp.ig_id}`);
            renderTable('ig-media-table', [
                { label: 'Caption', key: 'caption' },
                { label: 'Type', key: 'media_type' },
                { label: 'Likes', key: 'like_count' },
                { label: 'Comments', key: 'comments_count' },
            ], (igMedia || []).map(m => ({ ...m, caption: (m.caption || '').slice(0, 80) })));
        }
    } catch (e) {
        showError('ig-media-table', e.message);
    }
}

async function loadSEOWeekly() {
    const tableEl = document.getElementById('seo-weekly-table');
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
        data.forEach(w => html += `<th style="text-align:center; font-size:0.7rem;">${w.period}</th>`);
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
    } catch (e) {
        tableEl.innerHTML = `<div class="error-msg">${e.message}</div>`;
    }
}

async function loadYouTube() {
    try {
        const ch = await api('/api/youtube/channel');
        if (ch.title) {
            renderMetric('yt-subscribers', ch.subscribers);
            renderMetric('yt-views', ch.views);
            renderMetric('yt-videos', ch.videos);
        } else {
            document.getElementById('yt-metrics').innerHTML =
                '<div class="empty-state"><p>No YouTube channel found</p></div>';
        }
    } catch (e) {
        document.getElementById('yt-metrics').innerHTML =
            `<div class="empty-state"><p>YouTube API error: ${e.message}</p></div>`;
    }

    try {
        const videos = await api('/api/youtube/videos?limit=10');
        renderTable('yt-videos-table', [
            { label: 'Title', key: 'title' },
            { label: 'Published', key: 'published' },
            { label: 'Views', key: 'views' },
            { label: 'Likes', key: 'likes' },
            { label: 'Comments', key: 'comments' },
        ], videos);
    } catch (e) {
        showError('yt-videos-table', e.message);
    }
}

async function generateSEO() {
    const topic = document.getElementById('yt-seo-topic').value.trim();
    if (!topic) return;
    const resultEl = document.getElementById('yt-seo-result');
    resultEl.innerHTML = '<div class="empty-state"><p>Generating...</p></div>';
    try {
        const seo = await api(`/api/youtube/seo?topic=${encodeURIComponent(topic)}`);
        let html = '<div class="glass-card-static" style="padding:1.5rem;">';
        html += '<div class="table-title">Suggested Titles</div>';
        html += '<ul style="list-style:none; margin-bottom:1rem;">';
        seo.suggested_titles.forEach(t => html += `<li style="padding:0.3rem 0; font-size:0.85rem; color:var(--text-primary);">${t}</li>`);
        html += '</ul>';
        html += '<div class="table-title">Description</div>';
        html += `<pre style="white-space:pre-wrap; font-size:0.8rem; color:var(--text-secondary); background:var(--surface-input); padding:1rem; border-radius:0.75rem; margin-bottom:1rem; font-family:Inter,sans-serif;">${seo.description}</pre>`;
        html += '<div class="table-title">Hashtags</div>';
        html += '<div style="display:flex; flex-wrap:wrap; gap:0.4rem; margin-bottom:1rem;">';
        seo.hashtags.forEach(h => html += `<span style="background:var(--accent-primary-soft); color:var(--accent-primary); padding:0.25rem 0.6rem; border-radius:9999px; font-size:0.75rem; font-weight:600;">${h}</span>`);
        html += '</div>';
        html += '<div class="table-title">Tags</div>';
        html += '<div style="display:flex; flex-wrap:wrap; gap:0.4rem;">';
        seo.tags.forEach(t => html += `<span style="background:var(--surface-hover); color:var(--text-secondary); padding:0.25rem 0.6rem; border-radius:9999px; font-size:0.75rem;">${t}</span>`);
        html += '</div></div>';
        resultEl.innerHTML = html;
    } catch (e) {
        resultEl.innerHTML = `<div class="error-msg">${e.message}</div>`;
    }
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
                    metricsHtml += `<div class="metric-card"><div class="accent-strip" style="background:${colors[ci++ % 4]}"></div><div class="metric-label">${key}</div><div class="metric-value">${formatNum(val.sum)}</div></div>`;
                }
            }
            metricsEl.innerHTML = metricsHtml;
        }

        if (data.headers && data.rows) {
            tableWrap.style.display = 'block';
            renderTable('li-data-table',
                data.headers.map(h => ({ label: h, key: h })),
                data.rows.slice(0, 50),
            );
        }
    } catch (e) {
        document.getElementById('li-table-wrap').style.display = 'block';
        showError('li-data-table', e.message);
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

// ── Token Exchange ──

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
            html += `<textarea style="width:100%; height:60px; font-size:0.75rem; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:8px; padding:0.5rem; margin-bottom:1rem;" readonly onclick="this.select()">${data.long_lived_token}</textarea>`;
        }
        if (data.page_token) {
            html += `<p><strong>Page Token</strong> (never expires — use this as META_SOCIAL_TOKEN):</p>`;
            html += `<textarea style="width:100%; height:60px; font-size:0.75rem; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:8px; padding:0.5rem; margin-bottom:1rem;" readonly onclick="this.select()">${data.page_token}</textarea>`;
        }
        html += `<p style="color:var(--text-muted);">${data.instructions}</p>`;
        content.innerHTML = html;
    } catch (e) {
        content.innerHTML = `<p style="color:#ef4444;">Error: ${e.message}</p>`;
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
    document.getElementById('btn-seo-generate').addEventListener('click', generateSEO);
    document.getElementById('li-file-input').addEventListener('change', uploadLinkedIn);
    document.getElementById('yt-seo-topic').addEventListener('keydown', (e) => { if (e.key === 'Enter') generateSEO(); });

    const loader = document.getElementById('page-loader');
    if (loader) { loader.classList.add('fade'); setTimeout(() => loader.remove(), 400); }

    loadAll();
});
