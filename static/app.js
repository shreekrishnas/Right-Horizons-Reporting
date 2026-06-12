/* ── State ── */
let currentDomain = 'rh';
let currentView   = 'dashboard';
let startDate     = '';
let endDate       = '';
let gscChart      = null;
let ga4Chart      = null;
let isConnected   = false;

const DOMAIN_META = {
  rh:  { label: 'Right Horizons',     color: '#7C3AED', url: 'https://www.righthorizons.com' },
  pms: { label: 'Right Horizons PMS', color: '#0EA5E9', url: 'https://righthorizonspms.com' },
  aif: { label: 'Right Horizons AIF', color: '#10B981', url: 'https://aif.righthorizonspms.com' },
};

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', async () => {
  initDates(28);
  await checkAuth();
  if (isConnected) await loadAll();
  hideSplash();
});

function hideSplash() {
  const el = document.getElementById('page-loader');
  el.classList.add('fade');
  setTimeout(() => el.remove(), 400);
}

/* ── Auth ── */
async function checkAuth() {
  try {
    const r = await fetch('/auth/status');
    const d = await r.json();
    isConnected = d.connected;
  } catch { isConnected = false; }
  renderAuthArea();
  document.getElementById('auth-banner').style.display = isConnected ? 'none' : 'block';
}

function renderAuthArea() {
  const el = document.getElementById('auth-area');
  if (isConnected) {
    el.innerHTML = `
      <div class="auth-chip" onclick="disconnect()">
        <span class="dot"></span>
        Google Connected
      </div>`;
  } else {
    el.innerHTML = `
      <a href="/auth/google" class="btn-brand-gradient" style="font-size:0.78rem;padding:0.45rem 1rem">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15.545 6.558a9.42 9.42 0 0 1 .139 1.626c0 2.434-.87 4.492-2.384 5.885h.002C11.978 15.292 10.158 16 8 16A8 8 0 1 1 8 0a7.689 7.689 0 0 1 5.352 2.082l-2.284 2.284A4.347 4.347 0 0 0 8 3.166c-2.087 0-3.86 1.408-4.492 3.304a4.792 4.792 0 0 0 0 3.063h.003c.635 1.893 2.405 3.301 4.492 3.301 1.078 0 2.004-.276 2.722-.764h-.003a3.702 3.702 0 0 0 1.599-2.431H8v-3.08h7.545z"/></svg>
        Connect Google
      </a>`;
  }
}

async function disconnect() {
  await fetch('/auth/disconnect', { method: 'POST' });
  window.location.reload();
}

/* ── Date range ── */
function initDates(days) {
  const today = new Date();
  const from  = new Date(today);
  from.setDate(today.getDate() - (days - 1));
  endDate   = today.toISOString().slice(0, 10);
  startDate = from.toISOString().slice(0, 10);
  document.getElementById('end-date').value   = endDate;
  document.getElementById('start-date').value = startDate;
}

function setDateRange(days) {
  document.querySelectorAll('.dr-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`[data-days="${days}"]`).classList.add('active');
  initDates(days);
  if (isConnected) loadAll();
}

function setCustomRange() {
  document.querySelectorAll('.dr-btn').forEach(b => b.classList.remove('active'));
  startDate = document.getElementById('start-date').value;
  endDate   = document.getElementById('end-date').value;
  if (startDate && endDate && isConnected) loadAll();
}

/* ── Domain switching ── */
function setDomain(key) {
  currentDomain = key;
  document.querySelectorAll('.domain-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.domain === key);
  });
  const meta = DOMAIN_META[key];
  document.getElementById('topbar-sub').textContent = meta.url;
  document.documentElement.style.setProperty('--active-accent', meta.color);
  if (isConnected) loadAll();
}

/* ── View switching ── */
function setView(view) {
  currentView = view;
  document.querySelectorAll('.sidebar-item').forEach(i => {
    i.classList.toggle('active', i.dataset.view === view);
  });
  document.querySelectorAll('.view').forEach(v => {
    v.classList.toggle('active', v.id === `view-${view}`);
  });
  if (isConnected) {
    if (view === 'gsc')    loadGscDeep();
    if (view === 'ga4')    loadGa4Deep();
    if (view === 'social') loadSocial();
  }
}

/* ── Load all dashboard data ── */
async function loadAll() {
  if (!isConnected) return;
  const qs = `?domain=${currentDomain}&start=${startDate}&end=${endDate}`;
  try {
    const [gscSum, ga4Sum, queries, ga4pages, gscDaily, ga4Daily] = await Promise.allSettled([
      api('/api/gsc/summary' + qs),
      api('/api/ga4/summary' + qs),
      api('/api/gsc/queries' + qs + '&limit=8'),
      api('/api/ga4/pages'   + qs + '&limit=8'),
      api('/api/gsc/daily'   + qs),
      api('/api/ga4/daily'   + qs),
    ]);

    if (gscSum.status === 'fulfilled') renderGscKpis(gscSum.value, 'gsc-kpis');
    if (ga4Sum.status === 'fulfilled') renderGa4Kpis(ga4Sum.value, 'ga4-kpis');
    if (queries.status === 'fulfilled') renderQueriesTable(queries.value, 'queries-table-wrap');
    if (ga4pages.status === 'fulfilled') renderGa4PagesTable(ga4pages.value, 'ga4pages-table-wrap');
    if (gscDaily.status === 'fulfilled') renderGscChart(gscDaily.value);
    if (ga4Daily.status === 'fulfilled') renderGa4Chart(ga4Daily.value);

  } catch (e) { console.error('loadAll error', e); }
}

async function loadGscDeep() {
  const qs = `?domain=${currentDomain}&start=${startDate}&end=${endDate}`;
  const [sum, queries, pages] = await Promise.allSettled([
    api('/api/gsc/summary' + qs),
    api('/api/gsc/queries' + qs + '&limit=20'),
    api('/api/gsc/pages'   + qs + '&limit=20'),
  ]);
  if (sum.status === 'fulfilled')     renderGscKpis(sum.value, 'gsc-kpis-2');
  if (queries.status === 'fulfilled') renderQueriesTable(queries.value, 'gsc-queries-full', true);
  if (pages.status === 'fulfilled')   renderGscPagesTable(pages.value, 'gsc-pages-full', true);
}

async function loadGa4Deep() {
  const qs = `?domain=${currentDomain}&start=${startDate}&end=${endDate}`;
  const [sum, pages, sources] = await Promise.allSettled([
    api('/api/ga4/summary' + qs),
    api('/api/ga4/pages'   + qs + '&limit=20'),
    api('/api/ga4/sources' + qs),
  ]);
  if (sum.status === 'fulfilled')     renderGa4Kpis(sum.value, 'ga4-kpis-2');
  if (pages.status === 'fulfilled')   renderGa4PagesTable(pages.value, 'ga4-pages-full', true);
  if (sources.status === 'fulfilled') renderSourcesTable(sources.value, 'ga4-sources-full');
}

/* ── API helper ── */
async function api(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/* ── KPI renderers ── */
function renderGscKpis(d, containerId) {
  const accent = DOMAIN_META[currentDomain].color;
  document.getElementById(containerId).innerHTML = [
    kpiCard('Clicks',        fmt(d.clicks),      'organic search',  accent),
    kpiCard('Impressions',   fmt(d.impressions),  'search results',  accent),
    kpiCard('CTR',           d.ctr + '%',         'click-through rate', accent),
    kpiCard('Avg. Position', d.position,          'average ranking', accent),
  ].join('');
}

function renderGa4Kpis(d, containerId) {
  const accent = DOMAIN_META[currentDomain].color;
  document.getElementById(containerId).innerHTML = [
    kpiCard('Sessions',    fmt(d.sessions),          'website sessions',    accent),
    kpiCard('Users',       fmt(d.users),             'total users',         accent),
    kpiCard('New Users',   fmt(d.new_users),          'first-time visitors', accent),
    kpiCard('Bounce Rate', d.bounce_rate + '%',       'single-page sessions',accent),
    kpiCard('Pageviews',   fmt(d.pageviews),          'total page views',    accent),
  ].join('');
}

function kpiCard(label, value, meta, accent) {
  return `
    <div class="kpi-card">
      <div class="kpi-accent" style="background:${accent}"></div>
      <div class="kpi-label">${label}</div>
      <div class="kpi-value">${value}</div>
      <div class="kpi-meta">${meta}</div>
    </div>`;
}

function fmt(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000)    return (n / 1000).toFixed(1) + 'K';
  return String(n);
}

/* ── Table renderers ── */
function renderQueriesTable(rows, wrapperId, full = false) {
  if (!rows.length) { document.getElementById(wrapperId).innerHTML = '<div class="table-loading">No data</div>'; return; }
  const html = `<table class="rh-table">
    <thead><tr>
      <th>Query</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Position</th>
    </tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td>${escHtml(r.query)}</td>
      <td>${r.clicks}</td><td>${r.impressions}</td>
      <td>${r.ctr}%</td><td>${r.position}</td>
    </tr>`).join('')}</tbody>
  </table>`;
  document.getElementById(wrapperId).innerHTML = html;
}

function renderGscPagesTable(rows, wrapperId) {
  if (!rows.length) { document.getElementById(wrapperId).innerHTML = '<div class="table-loading">No data</div>'; return; }
  document.getElementById(wrapperId).innerHTML = `<table class="rh-table">
    <thead><tr><th>Page</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Position</th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td><span class="url-cell mono" title="${escHtml(r.page)}">${escHtml(r.page)}</span></td>
      <td>${r.clicks}</td><td>${r.impressions}</td><td>${r.ctr}%</td><td>${r.position}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

function renderGa4PagesTable(rows, wrapperId) {
  if (!rows.length) { document.getElementById(wrapperId).innerHTML = '<div class="table-loading">No data</div>'; return; }
  document.getElementById(wrapperId).innerHTML = `<table class="rh-table">
    <thead><tr><th>Page</th><th>Views</th><th>Sessions</th><th>Avg. Duration</th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td><span class="url-cell mono" title="${escHtml(r.page)}">${escHtml(r.page)}</span></td>
      <td>${r.views}</td><td>${r.sessions}</td><td>${fmtDur(r.avg_dur)}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

function renderSourcesTable(rows, wrapperId) {
  if (!rows.length) { document.getElementById(wrapperId).innerHTML = '<div class="table-loading">No data</div>'; return; }
  document.getElementById(wrapperId).innerHTML = `<table class="rh-table">
    <thead><tr><th>Channel</th><th>Sessions</th><th>Users</th></tr></thead>
    <tbody>${rows.map(r => `<tr>
      <td>${escHtml(r.channel)}</td><td>${r.sessions}</td><td>${r.users}</td>
    </tr>`).join('')}</tbody>
  </table>`;
}

function fmtDur(s) {
  const m = Math.floor(s / 60), sec = s % 60;
  return m ? `${m}m ${sec}s` : `${sec}s`;
}

/* ── Charts ── */
function renderGscChart(data) {
  const ctx = document.getElementById('gsc-chart').getContext('2d');
  if (gscChart) gscChart.destroy();
  const accent = DOMAIN_META[currentDomain].color;
  gscChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.date.slice(5)),
      datasets: [
        {
          label: 'Clicks', data: data.map(d => d.clicks),
          borderColor: accent, backgroundColor: hexAlpha(accent, 0.12),
          fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2,
        },
        {
          label: 'Impressions', data: data.map(d => d.impressions),
          borderColor: '#CBD5E1', backgroundColor: 'transparent',
          fill: false, tension: 0.4, pointRadius: 0, borderWidth: 1.5, borderDash: [4,3],
        },
      ],
    },
    options: chartOptions(),
  });
}

function renderGa4Chart(data) {
  const ctx = document.getElementById('ga4-chart').getContext('2d');
  if (ga4Chart) ga4Chart.destroy();
  const accent = DOMAIN_META[currentDomain].color;
  ga4Chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.date.slice(4)),
      datasets: [
        {
          label: 'Sessions', data: data.map(d => d.sessions),
          borderColor: accent, backgroundColor: hexAlpha(accent, 0.12),
          fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2,
        },
        {
          label: 'Users', data: data.map(d => d.users),
          borderColor: '#CBD5E1', backgroundColor: 'transparent',
          fill: false, tension: 0.4, pointRadius: 0, borderWidth: 1.5, borderDash: [4,3],
        },
      ],
    },
    options: chartOptions(),
  });
}

function chartOptions() {
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: true, position: 'top', labels: { boxWidth: 10, font: { size: 11 }, color: '#94A3B8' } }, tooltip: { borderRadius: 10, borderWidth: 1, borderColor: 'rgba(15,23,42,0.08)', titleFont: { size: 12 }, bodyFont: { size: 11 } } },
    scales: {
      x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#94A3B8', maxTicksLimit: 8 } },
      y: { grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { font: { size: 10 }, color: '#94A3B8' } },
    },
  };
}

function hexAlpha(hex, alpha) {
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

/* ── Export ── */
async function exportReport() {
  const btn = document.getElementById('btn-export');
  btn.disabled = true;
  btn.textContent = 'Exporting…';
  try {
    const url = `/api/export?domain=${currentDomain}&start=${startDate}&end=${endDate}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(await r.text());
    const blob = await r.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `RH_Report_${currentDomain.toUpperCase()}_${startDate}_${endDate}.xlsx`;
    a.click();
  } catch (e) { alert('Export failed: ' + e.message); }
  finally {
    btn.disabled = false;
    btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Export`;
  }
}

/* ── Meta / Social ── */
let metaChart = null;

async function loadSocial() {
  const qs = `?start=${startDate}&end=${endDate}`;
  const [campaigns, pages, instagram, daily] = await Promise.allSettled([
    api('/api/meta/campaigns' + qs),
    api('/api/meta/pages' + qs),
    api('/api/meta/instagram' + qs),
    api('/api/meta/daily' + qs),
  ]);

  if (campaigns.status === 'fulfilled') renderMetaAds(campaigns.value);
  if (pages.status === 'fulfilled')     renderFacebookCard(pages.value);
  if (instagram.status === 'fulfilled') renderInstagramCard(instagram.value);
  if (daily.status === 'fulfilled')     renderMetaChart(daily.value);
}

function renderMetaAds(d) {
  document.getElementById('meta-ads-card').innerHTML = `
    <div class="card-header-row">
      <span class="card-title">Meta Ads Performance</span>
      <span class="card-badge" style="background:rgba(24,119,242,0.10);color:#1877F2">Marketing API</span>
    </div>
    <div class="kpi-grid stagger" style="margin-bottom:1rem">
      ${kpiCard('Ad Spend', '₹' + fmt(d.spend), 'total spend', '#1877F2')}
      ${kpiCard('Impressions', fmt(d.impressions), 'ad impressions', '#1877F2')}
      ${kpiCard('Clicks', fmt(d.clicks), 'link clicks', '#1877F2')}
      ${kpiCard('Reach', fmt(d.reach), 'unique reach', '#1877F2')}
      ${kpiCard('CPC', '₹' + d.cpc, 'cost per click', '#1877F2')}
      ${kpiCard('CTR', d.ctr + '%', 'click-through rate', '#1877F2')}
    </div>
    ${d.campaigns && d.campaigns.length ? `
    <div class="table-wrap">
      <table class="rh-table">
        <thead><tr><th>Campaign</th><th>Spend</th><th>Impressions</th><th>Clicks</th><th>Reach</th><th>CPC</th></tr></thead>
        <tbody>${d.campaigns.map(c => `<tr>
          <td>${escHtml(c.name)}</td>
          <td>₹${c.spend}</td><td>${fmt(c.impressions)}</td>
          <td>${fmt(c.clicks)}</td><td>${fmt(c.reach)}</td><td>₹${c.cpc}</td>
        </tr>`).join('')}</tbody>
      </table>
    </div>` : '<div class="table-loading">No campaign data for this period</div>'}`;
}

function renderFacebookCard(d) {
  document.getElementById('facebook-card').innerHTML = `
    <div class="card-header-row">
      <span class="card-title">Facebook Pages</span>
      <span class="card-badge" style="background:rgba(24,119,242,0.10);color:#1877F2">Social API</span>
    </div>
    <div class="kpi-grid stagger" style="margin-bottom:1rem">
      ${kpiCard('Followers', fmt(d.followers), 'total followers', '#1877F2')}
      ${kpiCard('Impressions', fmt(d.impressions), 'page impressions', '#1877F2')}
      ${kpiCard('Reach', fmt(d.reach), 'organic reach', '#1877F2')}
      ${kpiCard('Engagement', fmt(d.engagement), 'engaged users', '#1877F2')}
      ${kpiCard('Posts', d.posts, 'posts published', '#1877F2')}
    </div>
    ${(d.pages || []).map(p => `
    <div style="margin-top:0.75rem">
      <div class="card-header-row"><span class="card-title" style="font-size:0.82rem">${escHtml(p.name)}</span><span style="font-size:0.75rem;color:var(--text-muted)">${fmt(p.followers)} followers · ${p.posts} posts</span></div>
      ${p.top_posts && p.top_posts.length ? `<div class="table-wrap"><table class="rh-table">
        <thead><tr><th>Post</th><th>Likes</th><th>Comments</th><th>Shares</th><th>Date</th></tr></thead>
        <tbody>${p.top_posts.map(post => `<tr>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(post.message || '—')}</td>
          <td>${post.likes}</td><td>${post.comments}</td><td>${post.shares}</td><td>${post.date}</td>
        </tr>`).join('')}</tbody>
      </table></div>` : ''}
    </div>`).join('')}`;
}

function renderInstagramCard(d) {
  document.getElementById('instagram-card').innerHTML = `
    <div class="card-header-row">
      <span class="card-title">Instagram</span>
      <span class="card-badge" style="background:rgba(225,48,108,0.10);color:#E1306C">Social API</span>
    </div>
    <div class="kpi-grid stagger">
      ${kpiCard('Followers', fmt(d.followers), 'total followers', '#E1306C')}
      ${kpiCard('Impressions', fmt(d.impressions), 'post impressions', '#E1306C')}
      ${kpiCard('Reach', fmt(d.reach), 'unique reach', '#E1306C')}
      ${kpiCard('Profile Views', fmt(d.profile_views), 'profile visits', '#E1306C')}
    </div>
    ${(d.accounts || []).map(a => `
    <div style="margin-top:0.75rem;padding:0.75rem 0;border-top:1px solid var(--border-subtle)">
      <span style="font-size:0.85rem;font-weight:700;color:var(--text-primary)">@${escHtml(a.username)}</span>
      <span style="font-size:0.75rem;color:var(--text-muted);margin-left:0.75rem">${fmt(a.followers)} followers · ${a.posts} posts</span>
    </div>`).join('')}
    ${d.error ? `<div class="table-loading" style="color:#E1306C">Note: ${escHtml(d.error)}</div>` : ''}`;
}

function renderMetaChart(data) {
  const canvas = document.getElementById('meta-chart');
  if (!canvas || !data.length) return;
  if (metaChart) metaChart.destroy();
  metaChart = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: data.map(d => d.date.slice(5)),
      datasets: [
        { label: 'Spend (₹)', data: data.map(d => d.spend), borderColor: '#1877F2', backgroundColor: 'rgba(24,119,242,0.10)', fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 },
        { label: 'Clicks', data: data.map(d => d.clicks), borderColor: '#CBD5E1', backgroundColor: 'transparent', fill: false, tension: 0.4, pointRadius: 0, borderWidth: 1.5, borderDash: [4,3] },
      ],
    },
    options: chartOptions(),
  });
}

/* ── Util ── */
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
