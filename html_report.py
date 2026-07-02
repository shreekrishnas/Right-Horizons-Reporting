"""
Dashboard-style monthly marketing report — glass-card SPA with sidebar navigation,
multi-entity support, MoM comparison tables, dark/light theme, and data upload modals.
Matches the reference RH_Monthly_Marketing_Report_2.html design language.
"""
import json as _json
from datetime import datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))

ENTITY_COLOR = {
    'Right Horizons': '#7C3AED',
    'Right Horizons PMS': '#0EA5E9',
    'Right Horizons AIF': '#10B981',
}

DOMAIN_TO_ENTITY = {
    'rh': 'Right Horizons',
    'pms': 'Right Horizons PMS',
    'aif': 'Right Horizons AIF',
}


def _esc(s):
    if not isinstance(s, str):
        return str(s) if s is not None else '—'
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')


def generate_html_report(all_data: dict, start: str, end: str, report_mode: str = "client") -> str:
    ts = datetime.now(_IST).strftime('%d %b %Y, %I:%M %p IST')
    data_json = _json.dumps(all_data, default=str)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Right Horizons — Monthly Marketing Performance Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Fraunces:opsz,wght@9..144,400..700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="atmosphere"></div>
<div class="app-outer">
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
        </div>
        <div>
          <div class="brand-name">Right Horizons</div>
          <div class="brand-sub">Marketing Report</div>
        </div>
      </div>
      <div id="navList"></div>
      <div class="sidebar-footnote">
        Generated {_esc(ts)}<br>
        Period: {_esc(start)} to {_esc(end)}<br>
        Mode: {_esc(report_mode.title())}
      </div>
    </aside>
    <div class="app-content">
      <div class="topbar">
        <div>
          <div class="topbar-title" id="pageTitle">Overview</div>
          <div class="topbar-sub">{_esc(start)} to {_esc(end)} · Prepared by Marketing</div>
        </div>
        <div class="topbar-right">
          <button class="btn btn-secondary" onclick="window.print()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
            Print
          </button>
          <div class="theme-toggle" id="themeToggle" title="Toggle dark mode">
            <svg id="themeIcon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
          </div>
        </div>
      </div>
      <main class="app-main" id="appMain"></main>
    </div>
  </div>
</div>
<div class="modal-overlay" id="modalOverlay">
  <div class="modal-card" id="modalCard"></div>
</div>
<script>
const API_DATA = {data_json};
const REPORT_START = "{_esc(start)}";
const REPORT_END = "{_esc(end)}";
const REPORT_MODE = "{_esc(report_mode)}";
{JS}
</script>
</body>
</html>"""


CSS = """\
:root{
  --text-primary:#1E1B4B; --text-secondary:#475569; --text-muted:#9CA3AF; --text-on-accent:#FFFFFF;
  --surface-base:#FFFFFF; --surface-card:rgba(255,255,255,0.85); --surface-card-elevated:rgba(255,255,255,0.95);
  --surface-card-header:rgba(0,0,0,0.02); --surface-input:#FFFFFF; --surface-hover:rgba(0,0,0,0.04);
  --border-subtle:rgba(0,0,0,0.06); --border-default:rgba(0,0,0,0.10); --border-input:#E5E7EB;
  --accent-primary:#7C3AED; --accent-primary-soft:rgba(124,58,237,0.08); --accent-section:#7C3AED;
  --status-success:#10B981; --status-warning:#F59E0B; --status-danger:#DC2626; --status-info:#0EA5E9;
}
[data-theme="dark"]{
  --text-primary:#F1F5F9; --text-secondary:#CBD5E1; --text-muted:#94A3B8; --text-on-accent:#FFFFFF;
  --surface-base:#0F172A; --surface-card:rgba(30,41,59,0.85); --surface-card-elevated:rgba(51,65,85,0.95);
  --surface-card-header:rgba(255,255,255,0.04); --surface-input:rgba(15,23,42,0.6); --surface-hover:rgba(255,255,255,0.06);
  --border-subtle:rgba(255,255,255,0.08); --border-default:rgba(255,255,255,0.14); --border-input:rgba(255,255,255,0.16);
  --accent-primary:#7C3AED; --accent-primary-soft:rgba(165,180,252,0.12); --accent-section:#A5B4FC;
}
*{box-sizing:border-box;}
body{margin:0; font-family:'Inter',system-ui,-apple-system,sans-serif; -webkit-font-smoothing:antialiased; background:var(--surface-base); color:var(--text-primary);}
.atmosphere{position:fixed; inset:0; z-index:-1; filter:blur(80px);
  background:
    radial-gradient(circle at 20% 20%, #e0e7ff 0%, transparent 40%),
    radial-gradient(circle at 80% 10%, #fae8ff 0%, transparent 40%),
    radial-gradient(circle at 50% 50%, #f1f5f9 0%, transparent 100%),
    radial-gradient(circle at 10% 80%, #dcfce7 0%, transparent 40%),
    radial-gradient(circle at 90% 90%, #fef9c3 0%, transparent 40%);
}
[data-theme="dark"] .atmosphere{
  background:
    radial-gradient(circle at 20% 20%, #1e1b4b 0%, transparent 40%),
    radial-gradient(circle at 80% 10%, #3b0764 0%, transparent 40%),
    radial-gradient(circle at 50% 50%, #0f172a 0%, transparent 100%),
    radial-gradient(circle at 10% 80%, #064e3b 0%, transparent 40%),
    radial-gradient(circle at 90% 90%, #1c1917 0%, transparent 40%);
}
.app-outer{min-height:100vh; padding:1rem; display:flex; justify-content:center;}
.app-shell{width:100%; max-width:1500px; min-height:95vh; border-radius:2rem; overflow:hidden;
  background:rgba(255,255,255,0.45); backdrop-filter:blur(40px) saturate(160%); -webkit-backdrop-filter:blur(40px) saturate(160%);
  border:1px solid rgba(255,255,255,0.5); box-shadow:0 25px 50px rgba(0,0,0,0.10), 0 8px 24px rgba(0,0,0,0.06);
  display:flex;}
[data-theme="dark"] .app-shell{background:rgba(10,10,30,0.88); border:1px solid rgba(255,255,255,0.06);}
.sidebar{width:220px; flex-shrink:0; padding:1.5rem 1rem; border-right:1px solid var(--border-subtle); display:flex; flex-direction:column; gap:0.35rem;}
.brand{display:flex; align-items:center; gap:0.65rem; padding:0.5rem 0.6rem 1.25rem;}
.brand-mark{width:40px; height:40px; border-radius:0.875rem; background:linear-gradient(135deg,#6366F1,#7C3AED); display:flex; align-items:center; justify-content:center; flex-shrink:0; box-shadow:0 8px 20px rgba(124,58,237,0.32);}
.brand-name{font-weight:800; font-size:0.95rem; letter-spacing:-0.02em; color:var(--text-primary); line-height:1.15;}
.brand-sub{font-size:0.68rem; color:var(--text-muted); font-weight:600; letter-spacing:0.02em;}
.nav-item{display:flex; align-items:center; gap:0.65rem; padding:0.62rem 0.75rem; border-radius:0.875rem; cursor:pointer; color:var(--text-muted); font-size:0.83rem; font-weight:600; transition:background .15s, color .15s;}
.nav-item svg{flex-shrink:0;}
.nav-item:hover{background:var(--surface-hover); color:var(--text-secondary);}
.nav-item.active{background:#fff; color:#6366F1; box-shadow:0 4px 12px rgba(99,102,241,0.20);}
[data-theme="dark"] .nav-item.active{background:rgba(99,102,241,0.22); color:#A5B4FC; box-shadow:none;}
.sidebar-footnote{margin-top:auto; padding:0.75rem 0.6rem 0.25rem; font-size:0.65rem; color:var(--text-muted); line-height:1.5;}
.app-content{flex:1; min-width:0; display:flex; flex-direction:column;}
.topbar{height:72px; flex-shrink:0; border-bottom:1px solid var(--border-subtle); display:flex; align-items:center; justify-content:space-between; padding:0 2rem;}
.topbar-title{font-weight:800; font-size:1.15rem; letter-spacing:-0.02em; color:var(--text-primary);}
.topbar-sub{font-size:0.75rem; color:var(--text-muted); font-weight:500; margin-top:0.1rem;}
.topbar-right{display:flex; align-items:center; gap:0.75rem;}
.theme-toggle{width:44px; height:44px; border-radius:9999px; background:var(--surface-card); border:1px solid var(--border-subtle); box-shadow:0 6px 18px rgba(15,23,42,0.07); display:flex; align-items:center; justify-content:center; cursor:pointer; color:var(--text-secondary);}
.app-main{flex:1; overflow-y:auto; padding:1.5rem 2rem 3rem;}
.page{display:none; animation:fadeIn .25s ease-out;}
.page.active{display:block;}
@keyframes fadeIn{from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:translateY(0);}}

h2.section-title{font-size:1.05rem; font-weight:800; letter-spacing:-0.01em; color:var(--text-primary); margin:2rem 0 0.9rem; display:flex; align-items:center; gap:0.5rem; justify-content:space-between;}
h2.section-title:first-child{margin-top:0;}
h2.section-title .title-txt{display:flex; align-items:center; gap:0.5rem;}
p.section-desc{font-size:0.82rem; color:var(--text-muted); margin:-0.5rem 0 1rem;}

.glass-card{background:var(--surface-card); border:1px solid var(--border-subtle); border-radius:1.5rem; box-shadow:0 2px 12px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04); padding:1.25rem; margin-bottom:1.5rem;}

.kpi-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1rem; margin-bottom:1.5rem;}
.kpi-card{position:relative; background:var(--surface-card); border:1px solid var(--border-subtle); border-radius:1rem; padding:1rem 1.1rem 0.9rem 1.35rem; box-shadow:0 2px 12px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04); overflow:hidden;}
.kpi-card::before{content:''; position:absolute; left:0; top:0; bottom:0; width:4px; background:var(--accent);}
.kpi-label{font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-muted); margin-bottom:0.45rem;}
.kpi-value{font-family:'Fraunces',ui-serif,Georgia,serif; font-size:1.7rem; font-weight:700; color:var(--text-primary); line-height:1.1;}
.kpi-meta{display:flex; align-items:center; gap:0.4rem; margin-top:0.5rem; flex-wrap:wrap;}
.kpi-note{font-size:0.72rem; color:var(--text-muted); margin-top:0.4rem; line-height:1.35;}

.chip{display:inline-flex; align-items:center; gap:0.2rem; padding:0.16rem 0.5rem; border-radius:9999px; font-size:0.68rem; font-weight:700; white-space:nowrap;}
.chip-up-good{background:rgba(16,185,129,0.12); color:#10B981;}
.chip-up-bad{background:rgba(220,38,38,0.12); color:#DC2626;}
.chip-down-good{background:rgba(16,185,129,0.12); color:#10B981;}
.chip-down-bad{background:rgba(220,38,38,0.12); color:#DC2626;}
.chip-neutral{background:rgba(148,163,184,0.14); color:var(--text-secondary);}
.chip-flat{background:rgba(148,163,184,0.14); color:var(--text-muted);}

.badge{display:inline-flex; align-items:center; gap:0.3rem; padding:0.2rem 0.625rem; border-radius:9999px; font-size:0.7rem; font-weight:700; white-space:nowrap;}
.badge-green{background:#D1FAE5; color:#059669;}
.badge-amber{background:#FEF3C7; color:#B45309;}
.badge-red{background:#FEE2E2; color:#DC2626;}
.badge-flat{background:rgba(148,163,184,0.16); color:var(--text-muted);}
.badge-api{background:rgba(14,165,233,0.12); color:#0EA5E9;}
.badge-calc{background:rgba(124,58,237,0.12); color:#7C3AED;}

.table-wrap{background:var(--surface-card); border:1px solid var(--border-subtle); border-radius:1.5rem; overflow:hidden; overflow-x:auto; box-shadow:0 2px 12px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04); margin-bottom:1.5rem;}
table{border-collapse:collapse; width:100%; min-width:640px; font-size:0.8rem;}
thead th{position:sticky; top:0; background:var(--surface-card-elevated); text-align:left; font-size:0.63rem; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; color:var(--text-muted); padding:0.7rem 0.9rem; border-bottom:1px solid var(--border-subtle); white-space:nowrap;}
tbody td{padding:0.6rem 0.9rem; border-bottom:1px solid rgba(15,23,42,0.04); color:var(--text-secondary); white-space:nowrap;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover td{background:var(--surface-hover);}
tbody tr.total-row td{font-weight:800; color:var(--text-primary); background:var(--surface-card-header);}
td.name-cell, th.name-cell{position:sticky; left:0; background:inherit; font-weight:600; color:var(--text-primary); white-space:nowrap; z-index:1;}
thead th.name-cell{background:var(--surface-card-elevated);}
tbody td.name-cell{background:var(--surface-card);}
tbody tr.total-row td.name-cell{background:var(--surface-card-header);}
td.num{text-align:right; font-variant-numeric:tabular-nums;}
td.muted{color:var(--text-muted);}
td.notes-cell{white-space:normal; min-width:200px; color:var(--text-muted); font-size:0.75rem;}
tr.group-row td{background:var(--accent-primary-soft)!important; font-weight:800; color:var(--accent-section); text-transform:uppercase; letter-spacing:0.04em; font-size:0.7rem;}

.pill-row{display:flex; align-items:center; gap:1.6rem; flex-wrap:wrap; margin-bottom:1.25rem;}
.pill-btn{display:inline-flex; align-items:center; gap:0.45rem; background:none; border:none; cursor:pointer; font-family:inherit; font-size:0.85rem; font-weight:600; color:var(--text-muted); padding:0.15rem 0; transition:color .15s;}
.pill-btn .dot{width:8px; height:8px; border-radius:50%; opacity:0.45; transition:opacity .15s, transform .15s;}
.pill-btn.active{font-weight:700;}
.pill-btn.active .dot{opacity:1; transform:scale(1.15);}
.pill-btn:hover{color:var(--text-secondary);}

.subhead{font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--accent-section); margin:1.5rem 0 0.6rem; display:flex; align-items:center; gap:0.4rem;}

.platform-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; margin-bottom:1.5rem;}
.stat-row{display:flex; justify-content:space-between; align-items:center; gap:0.5rem; padding:0.4rem 0; border-bottom:1px solid var(--border-subtle); font-size:0.78rem;}
.stat-row:last-child{border-bottom:none;}
.stat-row .lbl{color:var(--text-muted); font-weight:500;}
.stat-row .valwrap{display:flex; align-items:center; gap:0.45rem;}
.stat-val{font-weight:700; color:var(--text-primary); font-variant-numeric:tabular-nums;}

.footer-note{font-size:0.72rem; color:var(--text-muted); text-align:center; padding:1.5rem 0 0.5rem; line-height:1.5;}
.summary-block{white-space:pre-line; background:var(--surface-card); border-left:4px solid var(--accent-primary); border-radius:0.75rem; padding:1rem 1.25rem; color:var(--text-secondary); font-size:0.85rem; line-height:1.6; margin-bottom:1rem;}
.summary-block ul{margin:6px 0; padding-left:20px;}
.summary-block li{margin:4px 0;}

.btn{display:inline-flex; align-items:center; gap:0.4rem; padding:0.6rem 1.1rem; border-radius:0.875rem; font-family:inherit; font-size:0.82rem; font-weight:700; cursor:pointer; border:none;}
.btn-primary{background:#6366F1; color:#fff;}
.btn-primary:hover{background:#4F46E5;}
.btn-secondary{background:rgba(255,255,255,0.7); color:#374151; border:1px solid var(--border-subtle);}
[data-theme="dark"] .btn-secondary{background:rgba(255,255,255,0.08); color:var(--text-secondary);}

.confidence-bar{height:8px; border-radius:999px; background:var(--border-default); margin-top:6px; overflow:hidden; max-width:200px;}
.confidence-fill{height:100%; border-radius:999px; background:linear-gradient(90deg,#6366F1,#10B981);}

.channel-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:1rem; margin-top:1rem;}
.channel-card{background:var(--surface-card); border:1px solid var(--border-subtle); border-radius:1rem; padding:1rem;}
.ch-name{font-size:0.68rem; text-transform:uppercase; letter-spacing:0.06em; font-weight:800; color:var(--text-muted);}
.ch-grade{font-size:1.5rem; font-weight:900; margin:0.25rem 0;}
.grade{display:inline-block; width:32px; height:32px; line-height:32px; text-align:center; border-radius:8px; font-weight:900; font-size:16px;}
.grade.A{background:#dcfce7; color:#166534;}
.grade.B{background:#d1fae5; color:#065f46;}
.grade.C{background:#ffedd5; color:#9a3412;}
.grade.D,.grade.F{background:#fee2e2; color:#991b1b;}

::-webkit-scrollbar{width:8px; height:8px;}
::-webkit-scrollbar-thumb{background:var(--border-default); border-radius:9999px;}

@media(max-width:900px){
  .app-shell{flex-direction:column;}
  .sidebar{width:100%; flex-direction:row; overflow-x:auto; border-right:none; border-bottom:1px solid var(--border-subtle); padding:0.75rem;}
  .sidebar .brand{display:none;}
  .sidebar-footnote{display:none;}
  .app-main{padding:1rem;}
  .kpi-grid{grid-template-columns:1fr 1fr;}
}
@media print{
  body{background:#fff!important;}
  .atmosphere,.sidebar,.topbar,.theme-toggle,.btn{display:none!important;}
  .app-shell{border:none; box-shadow:none; background:#fff!important; display:block!important;}
  .app-content{display:block!important;}
  .app-main{padding:0!important; overflow:visible!important;}
  .page{display:block!important; page-break-after:always;}
  .glass-card,.kpi-card,.table-wrap{box-shadow:none; border:1px solid #e5e7eb;}
  table{min-width:0!important; font-size:9px;}
}
"""


JS = r"""
/* ============================= FORMATTERS ============================= */
const fmtINR = v => (v===null||v===undefined) ? null : '₹' + Math.round(v).toLocaleString('en-IN');
const fmtNum = (v,d=0) => (v===null||v===undefined) ? null : Number(v).toLocaleString('en-IN',{minimumFractionDigits:d,maximumFractionDigits:d});
const fmtPct = (v,d=1) => (v===null||v===undefined) ? null : (v<1&&v>-1?(v*100).toFixed(d):Number(v).toFixed(d))+'%';
const fmtSigned = (v,d=1) => (v===null||v===undefined) ? null : (v>0?'+':'') + v.toFixed(d);
function cell(val, cls){ if(val===null||val===undefined||val==='') return `<td class="num muted">—</td>`; return `<td class="num${cls?(' '+cls):''}">${val}</td>`; }
function nameCell(label){ return `<td class="name-cell">${label}</td>`; }
function momChip(delta, pct, direction){
  if(delta===null||delta===undefined) return `<span class="chip chip-flat">—</span>`;
  const isZero = Math.abs(delta) < 1e-9;
  const up = delta > 0;
  let cls = 'chip-neutral';
  if(!isZero && direction==='up') cls = up ? 'chip-up-good' : 'chip-down-bad';
  if(!isZero && direction==='down') cls = up ? 'chip-up-bad' : 'chip-down-good';
  if(isZero) cls = 'chip-flat';
  const arrow = isZero ? '→' : (up ? '↑' : '↓');
  const dTxt = fmtSigned(delta);
  const pTxt = (pct===null||pct===undefined) ? '' : ` (${fmtSigned(pct*100,1)}%)`;
  return `<span class="chip ${cls}">${arrow} ${dTxt}${pTxt}</span>`;
}
function statusBadge(status){
  if(status==='GREEN') return `<span class="badge badge-green">● GREEN</span>`;
  if(status==='AMBER') return `<span class="badge badge-amber">● AMBER</span>`;
  if(status==='RED') return `<span class="badge badge-red">● RED</span>`;
  return `<span class="badge badge-flat">—</span>`;
}
function sourceBadge(src){
  if(src==='api') return `<span class="badge badge-api" style="font-size:0.6rem">API</span>`;
  if(src==='calc') return `<span class="badge badge-calc" style="font-size:0.6rem">Calc</span>`;
  return '';
}

/* ============================= DATA UTILS ============================= */
const ENTITIES = ['rh','pms','aif'];
const ENTITY_LABELS = {rh:'Right Horizons', pms:'Right Horizons PMS', aif:'Right Horizons AIF'};
const ENTITY_COLORS = {rh:'#7C3AED', pms:'#0EA5E9', aif:'#10B981'};
const g = (obj, key, def) => (obj && typeof obj === 'object' && key in obj) ? obj[key] : (def===undefined?null:def);
const safeNum = v => (v===null||v===undefined||v===''||v==='—') ? null : Number(v);

function getEntityData(entity) { return API_DATA[entity] || {}; }

/* ============================= KPI CARD BUILDER ============================= */
function kpiCard(label, value, chipHtml, note, accent){
  const accentStyle = accent ? `--accent:${accent}` : '--accent:#7C3AED';
  return `<div class="kpi-card" style="${accentStyle}">
    <div class="kpi-label">${label}</div>
    <div class="kpi-value">${value || '—'}</div>
    <div class="kpi-meta">${chipHtml || ''}</div>
    ${note ? `<div class="kpi-note">${note}</div>` : ''}
  </div>`;
}

/* ============================= OVERVIEW PAGE ============================= */
function renderOverview(){
  const el = document.getElementById('overview');
  let html = '';

  // AI Summary
  const rhData = getEntityData('rh');
  const aiSum = rhData.ai_summary;
  if(aiSum && typeof aiSum === 'object'){
    const exec = aiSum.executive_summary || '';
    const confidence = safeNum(aiSum.confidence_score) || 0;
    const working = aiSum.what_improved;
    const dropped = aiSum.what_dropped;
    const mainWin = aiSum.main_win || '';
    const mainConcern = aiSum.main_concern || '';
    const opportunity = aiSum.key_opportunity || '';
    const focus = aiSum.recommended_focus || '';

    html += `<h2 class="section-title"><span class="title-txt">Executive Summary</span>`;
    if(confidence) html += `<span class="badge badge-green">Health: ${confidence}/100</span>`;
    html += `</h2>`;

    if(exec) html += `<div class="summary-block">${escHtml(exec)}</div>`;
    if(mainWin) html += `<div class="glass-card"><span class="badge badge-green">Main Win</span><p style="margin:0.5rem 0 0;font-size:0.85rem">${escHtml(mainWin)}</p></div>`;
    if(mainConcern) html += `<div class="glass-card"><span class="badge badge-red">Main Concern</span><p style="margin:0.5rem 0 0;font-size:0.85rem">${escHtml(mainConcern)}</p></div>`;
    if(opportunity) html += `<div class="glass-card"><span class="badge badge-amber">Key Opportunity</span><p style="margin:0.5rem 0 0;font-size:0.85rem">${escHtml(opportunity)}</p></div>`;

    if(working && Array.isArray(working)){
      html += `<div class="glass-card"><span class="badge badge-green">What Improved</span><ul style="margin:0.5rem 0 0;padding-left:1.2rem;font-size:0.82rem;color:var(--text-secondary)">`;
      working.forEach(w => html += `<li>${escHtml(String(w))}</li>`);
      html += `</ul></div>`;
    }
    if(dropped && Array.isArray(dropped)){
      html += `<div class="glass-card"><span class="badge badge-red">What Declined</span><ul style="margin:0.5rem 0 0;padding-left:1.2rem;font-size:0.82rem;color:var(--text-secondary)">`;
      dropped.forEach(w => html += `<li>${escHtml(String(w))}</li>`);
      html += `</ul></div>`;
    }

    // Channel grades
    const grades = aiSum.channel_grades;
    if(grades && typeof grades === 'object'){
      html += `<h2 class="section-title"><span class="title-txt">Channel Grades</span></h2><div class="channel-grid">`;
      Object.entries(grades).forEach(([ch, info]) => {
        if(!info || typeof info !== 'object') return;
        const grade = info.grade || '—';
        const trend = info.trend || '';
        const oneLiner = info.one_liner || '';
        const arrow = {improving:'↑', stable:'→', declining:'↓'}[trend] || '';
        html += `<div class="channel-card"><div class="ch-name">${escHtml(ch.toUpperCase())}</div>
          <div class="ch-grade"><span class="grade ${grade}">${grade}</span> <span style="font-size:0.8rem;color:var(--text-muted)">${arrow} ${escHtml(trend)}</span></div>
          <div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem">${escHtml(oneLiner)}</div></div>`;
      });
      html += `</div>`;
    }

    // Next steps
    const steps = aiSum.next_steps;
    if(steps && Array.isArray(steps)){
      html += `<h2 class="section-title"><span class="title-txt">Recommended Actions</span></h2>`;
      steps.forEach(s => {
        if(typeof s === 'object'){
          const pri = (s.priority||'medium').toLowerCase();
          const badgeCls = pri==='high'?'badge-red':pri==='low'?'badge-green':'badge-amber';
          html += `<div class="glass-card" style="padding:0.9rem 1.1rem"><div style="display:flex;gap:0.6rem;align-items:flex-start">
            <span class="badge ${badgeCls}" style="flex-shrink:0;margin-top:2px">${escHtml(pri)}</span>
            <div><div style="font-weight:700;font-size:0.85rem">${escHtml(s.title||'')}</div>
            <div style="font-size:0.78rem;color:var(--text-muted);margin-top:0.2rem">${escHtml(s.description||s.expected_impact||'')}</div></div></div></div>`;
        } else {
          html += `<div class="glass-card" style="padding:0.9rem 1.1rem;font-size:0.85rem">${escHtml(String(s))}</div>`;
        }
      });
    }

    if(focus) html += `<div class="glass-card"><span class="badge badge-flat">Recommended Focus Next Period</span><p style="margin:0.5rem 0 0;font-size:0.85rem">${escHtml(focus)}</p></div>`;

    if(confidence){
      html += `<div style="margin-top:1rem"><div style="font-size:0.72rem;font-weight:700;color:var(--text-muted);margin-bottom:0.3rem">OVERALL HEALTH SCORE</div>
        <div class="confidence-bar" style="max-width:300px"><div class="confidence-fill" style="width:${Math.min(confidence,100)}%"></div></div>
        <div style="font-size:0.72rem;color:var(--text-muted);margin-top:0.3rem">${confidence}/100</div></div>`;
    }
  } else {
    html += `<div class="glass-card" style="text-align:center;color:var(--text-muted);padding:2rem">
      <p>No AI executive summary available. Generate one from the Reporting Room before exporting.</p></div>`;
  }

  // KPI snapshot across all entities
  html += `<h2 class="section-title" style="margin-top:2rem"><span class="title-txt">KPI Snapshot — All Entities</span></h2>`;
  ENTITIES.forEach(ent => {
    const d = getEntityData(ent);
    const gsc = d.gsc || {};
    const ga4 = d.ga4 || {};
    const fb = d.social_fb || {};
    const ig = d.social_ig || {};
    const ads = d.meta_ads || [];
    const totalReach = (safeNum(ig.reach)||0) + (safeNum(fb.reach)||0);
    const totalEng = (safeNum(ig.engagements)||0) + (safeNum(fb.engagements)||0);
    const orgSessions = safeNum(ga4.organic_sessions) || safeNum(ga4.sessions) || 0;
    const gscClicks = safeNum(gsc.clicks) || 0;
    const adSpend = ads.reduce((s,c) => s + (safeNum(c.spend)||0), 0);
    const adLeads = ads.reduce((s,c) => s + (safeNum(c.leads)||0), 0);

    html += `<div class="subhead"><span class="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${ENTITY_COLORS[ent]}"></span>${ENTITY_LABELS[ent]}</div>`;
    html += `<div class="kpi-grid">`;
    html += kpiCard('Total Reach', fmtNum(totalReach||null), sourceBadge('api'), null, ENTITY_COLORS[ent]);
    html += kpiCard('Total Engagements', fmtNum(totalEng||null), sourceBadge('api'), null, ENTITY_COLORS[ent]);
    html += kpiCard('Organic Sessions', fmtNum(orgSessions||null), sourceBadge('api'), null, ENTITY_COLORS[ent]);
    html += kpiCard('GSC Clicks', fmtNum(gscClicks||null), sourceBadge('api'), null, ENTITY_COLORS[ent]);
    html += kpiCard('Ad Spend', fmtINR(adSpend||null), sourceBadge('api'), null, ENTITY_COLORS[ent]);
    html += kpiCard('Ad Leads', fmtNum(adLeads||null), sourceBadge('api'), null, ENTITY_COLORS[ent]);
    html += `</div>`;
  });

  el.innerHTML = html;
}

/* ============================= ADS PAGE ============================= */
function renderAds(){
  const el = document.getElementById('ads');
  let html = '<h2 class="section-title"><span class="title-txt">Meta Ads Performance</span><span class="badge badge-api">API Data</span></h2>';

  ENTITIES.forEach(ent => {
    const d = getEntityData(ent);
    const ads = d.meta_ads || [];
    if(!ads.length) return;

    const ti = ads.reduce((s,c) => s + (safeNum(c.impressions)||0), 0);
    const tc = ads.reduce((s,c) => s + (safeNum(c.clicks)||0), 0);
    const tl = ads.reduce((s,c) => s + (safeNum(c.leads)||0), 0);
    const ts = ads.reduce((s,c) => s + (safeNum(c.spend)||0), 0);
    const tr = ads.reduce((s,c) => s + (safeNum(c.reach)||0), 0);
    const ctr = ti > 0 ? (tc/ti*100) : 0;
    const cpl = tl > 0 ? (ts/tl) : 0;

    html += `<div class="subhead"><span class="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${ENTITY_COLORS[ent]}"></span>${ENTITY_LABELS[ent]}</div>`;
    html += `<div class="kpi-grid">`;
    html += kpiCard('Impressions', fmtNum(ti||null), null, null, ENTITY_COLORS[ent]);
    html += kpiCard('Clicks', fmtNum(tc||null), null, null, ENTITY_COLORS[ent]);
    html += kpiCard('Leads', fmtNum(tl||null), null, null, ENTITY_COLORS[ent]);
    html += kpiCard('CTR', ctr ? ctr.toFixed(2)+'%' : '—', null, null, ENTITY_COLORS[ent]);
    html += kpiCard('Total Spend', fmtINR(ts||null), null, null, ENTITY_COLORS[ent]);
    html += kpiCard('CPL', cpl ? fmtINR(cpl) : '—', null, null, ENTITY_COLORS[ent]);
    html += `</div>`;

    // Campaign table
    const active = ads.filter(c => (safeNum(c.impressions)||0) > 0 || (safeNum(c.spend)||0) > 0);
    if(active.length){
      html += `<div class="table-wrap"><table><thead><tr>
        <th class="name-cell">Campaign</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th>Reach</th><th>Leads</th><th>Spend</th><th>CPL</th>
      </tr></thead><tbody>`;
      active.forEach(c => {
        const name = c.campaign_name || c.name || '—';
        const ci = safeNum(c.impressions);
        const cc = safeNum(c.clicks);
        const cctr = ci ? (cc/ci*100).toFixed(2)+'%' : '—';
        const cr = safeNum(c.reach);
        const cl = safeNum(c.leads);
        const csp = safeNum(c.spend);
        const ccpl = cl ? fmtINR(csp/cl) : '—';
        html += `<tr>${nameCell(escHtml(name))}${cell(fmtNum(ci))}${cell(fmtNum(cc))}${cell(cctr)}${cell(fmtNum(cr))}${cell(fmtNum(cl))}${cell(fmtINR(csp))}${cell(ccpl)}</tr>`;
      });
      html += `</tbody></table></div>`;
    }
  });

  if(!ENTITIES.some(e => (getEntityData(e).meta_ads||[]).length)){
    html += `<div class="glass-card" style="text-align:center;color:var(--text-muted);padding:2rem">No ad campaign data available for this period.</div>`;
  }

  el.innerHTML = html;
}

/* ============================= SMM PAGE ============================= */
let smmEntity = 'rh';
function renderSMM(){
  const el = document.getElementById('smm');
  let html = `<div id="smmPills"></div>`;

  const d = getEntityData(smmEntity);
  const fb = d.social_fb || {};
  const ig = d.social_ig || {};
  const trend = d.social_trend || [];

  // Platform cards
  html += `<h2 class="section-title"><span class="title-txt">Social Media Overview</span><span class="badge badge-api">API Data</span></h2>`;
  html += `<div class="platform-grid">`;

  if(Object.keys(ig).length){
    html += `<div class="glass-card"><div style="font-weight:800;font-size:0.85rem;margin-bottom:0.7rem">Instagram</div>`;
    [['Followers','followers'],['New Followers','new_followers'],['Reach','reach'],['Impressions','views'],
     ['Engagements','engagements'],['Engagement Rate','engagement_rate'],['Posts Published','posts_published'],
     ['Video Views','video_views'],['Link Clicks','link_clicks'],['Saves/Shares','saves_shares']].forEach(([lbl,key]) => {
      const v = ig[key];
      const disp = key==='engagement_rate' ? (v ? (v<1?(v*100).toFixed(2):Number(v).toFixed(2))+'%' : '—') : (v ? fmtNum(v) : '—');
      html += `<div class="stat-row"><span class="lbl">${lbl}</span><span class="valwrap"><span class="stat-val">${disp}</span></span></div>`;
    });
    html += `</div>`;
  }

  if(Object.keys(fb).length){
    html += `<div class="glass-card"><div style="font-weight:800;font-size:0.85rem;margin-bottom:0.7rem">Facebook</div>`;
    [['Page Likes','followers'],['New Followers','new_followers'],['Reach','reach'],['Views','views'],
     ['Engagements','engagements'],['Engagement Rate','engagement_rate'],['Posts Published','posts_published'],
     ['Video Views','video_views'],['Link Clicks','link_clicks'],['Saves/Shares','saves_shares']].forEach(([lbl,key]) => {
      const v = fb[key] || fb[key==='followers'?'page_likes':key];
      const disp = key==='engagement_rate' ? (v ? (v<1?(v*100).toFixed(2):Number(v).toFixed(2))+'%' : '—') : (v ? fmtNum(v) : '—');
      html += `<div class="stat-row"><span class="lbl">${lbl}</span><span class="valwrap"><span class="stat-val">${disp}</span></span></div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;

  // SMM Trend table
  if(trend.length){
    html += `<h2 class="section-title"><span class="title-txt">Social Media Trend</span></h2>`;
    const metrics = [
      {k:'followers', label:'Followers', platform:'ig'},
      {k:'new_followers', label:'New Followers', platform:'ig'},
      {k:'reach', label:'Reach', platform:'ig'},
      {k:'views', label:'Impressions/Views', platform:'ig'},
      {k:'engagements', label:'Engagements', platform:'ig'},
      {k:'engagement_rate', label:'Engagement Rate', platform:'ig', isPct:true},
    ];

    ['ig','fb','li'].forEach(plat => {
      const platLabel = {ig:'Instagram',fb:'Facebook',li:'LinkedIn'}[plat];
      const hasData = trend.some(t => t[plat]);
      if(!hasData) return;

      html += `<div style="font-weight:700;font-size:0.82rem;color:var(--text-primary);margin:1rem 0 0.5rem">${platLabel}</div>`;
      html += `<div class="table-wrap"><table><thead><tr><th class="name-cell">Metric</th><th>MoM Δ</th>`;
      trend.forEach((t,i) => {
        const ps = t.period_start || '';
        const pe = t.period_end || '';
        html += `<th>${ps && pe ? ps+' – '+pe : (t.period||'W'+(i+1))}</th>`;
      });
      html += `</tr></thead><tbody>`;

      metrics.forEach(m => {
        const vals = trend.map(t => {
          const src = t[plat] || {};
          return safeNum(src[m.k]);
        });
        const last = vals[vals.length-1];
        const prev = vals.length>=2 ? vals[vals.length-2] : null;
        const delta = (last!==null && prev!==null) ? last-prev : null;
        const pct = (delta!==null && prev) ? delta/prev : null;

        html += `<tr>${nameCell(m.label)}<td>${momChip(delta, pct, 'up')}</td>`;
        vals.forEach(v => {
          const disp = m.isPct ? (v!==null ? (v<1?(v*100).toFixed(2):Number(v).toFixed(2))+'%' : null) : fmtNum(v);
          html += cell(disp);
        });
        html += `</tr>`;
      });
      html += `</tbody></table></div>`;
    });
  }

  if(!Object.keys(ig).length && !Object.keys(fb).length && !trend.length){
    html += `<div class="glass-card" style="text-align:center;color:var(--text-muted);padding:2rem">No social media data available for this entity.</div>`;
  }

  el.innerHTML = html;

  // Add entity pills
  const pillDiv = document.getElementById('smmPills');
  if(pillDiv){
    pillDiv.innerHTML = '';
    pillDiv.appendChild(entityPillRow(smmEntity, e => { smmEntity=e; renderSMM(); }));
  }
}

/* ============================= SEO PAGE ============================= */
let seoEntity = 'rh';
function renderSEO(){
  const el = document.getElementById('seo');
  let html = `<div id="seoPills"></div>`;

  const d = getEntityData(seoEntity);
  const gsc = d.gsc || {};
  const ga4 = d.ga4 || {};
  const seoTrend = d.seo_trend || [];

  html += `<h2 class="section-title"><span class="title-txt">Website & SEO Overview</span><span class="badge badge-api">API Data</span></h2>`;
  html += `<div class="kpi-grid">`;
  const orgSess = safeNum(ga4.organic_sessions) || safeNum(ga4.sessions) || 0;
  const orgUsers = safeNum(ga4.organic_users) || safeNum(ga4.users) || 0;
  const gscCl = safeNum(gsc.clicks) || 0;
  const gscIm = safeNum(gsc.impressions) || 0;
  const gscCtr = safeNum(gsc.ctr);
  const gscPos = safeNum(gsc.position);
  const bounce = safeNum(ga4.bounce_rate);
  const dur = safeNum(ga4.avg_session_duration);
  const leads = safeNum(ga4.leads);

  html += kpiCard('Organic Sessions', fmtNum(orgSess||null), null, null, ENTITY_COLORS[seoEntity]);
  html += kpiCard('Organic Users', fmtNum(orgUsers||null), null, null, ENTITY_COLORS[seoEntity]);
  html += kpiCard('GSC Clicks', fmtNum(gscCl||null), null, null, ENTITY_COLORS[seoEntity]);
  html += kpiCard('GSC Impressions', fmtNum(gscIm||null), null, null, ENTITY_COLORS[seoEntity]);
  html += kpiCard('Avg Position', gscPos ? gscPos.toFixed(1) : '—', null, null, ENTITY_COLORS[seoEntity]);
  html += kpiCard('CTR', gscCtr ? (gscCtr<1?(gscCtr*100).toFixed(2):gscCtr.toFixed(2))+'%' : '—', null, null, ENTITY_COLORS[seoEntity]);
  html += kpiCard('Bounce Rate', bounce ? (bounce<1?(bounce*100).toFixed(1):bounce.toFixed(1))+'%' : '—', null, null, ENTITY_COLORS[seoEntity]);
  html += kpiCard('Avg Session Duration', dur ? Math.round(dur)+'s' : '—', null, null, ENTITY_COLORS[seoEntity]);
  html += `</div>`;

  // SEO Trend
  if(seoTrend.length){
    html += `<h2 class="section-title"><span class="title-txt">SEO Trend</span></h2>`;
    const trendMetrics = [
      {k:'sessions', label:'Organic Sessions', g:'TRAFFIC'},
      {k:'users', label:'Organic Users'},
      {k:'leads', label:'Website Leads'},
      {k:'avg_session_duration', label:'Avg Session Duration (sec)', g:'ENGAGEMENT'},
      {k:'bounce_rate', label:'Bounce Rate', isPct:true, dir:'down'},
      {k:'clicks', label:'GSC Clicks', g:'SEARCH CONSOLE'},
      {k:'impressions', label:'GSC Impressions'},
      {k:'position', label:'Avg Position', dir:'down'},
    ];

    html += `<div class="table-wrap"><table><thead><tr><th class="name-cell">Metric</th><th>MoM Δ</th><th>MoM %</th>`;
    seoTrend.forEach((t,i) => {
      const ps = t.period_start || '';
      const pe = t.period_end || '';
      html += `<th>${ps && pe ? ps+' – '+pe : (t.period||'W'+(i+1))}</th>`;
    });
    html += `</tr></thead><tbody>`;

    let lastGroup = '';
    trendMetrics.forEach(m => {
      if(m.g && m.g !== lastGroup){
        lastGroup = m.g;
        html += `<tr class="group-row"><td colspan="${seoTrend.length+3}">${m.g}</td></tr>`;
      }
      const vals = seoTrend.map(t => safeNum(t[m.k]));
      const last = vals[vals.length-1];
      const prev = vals.length>=2 ? vals[vals.length-2] : null;
      const delta = (last!==null && prev!==null) ? last-prev : null;
      const pct = (delta!==null && prev) ? delta/prev : null;
      const dir = m.dir || 'up';

      html += `<tr>${nameCell(m.label)}<td>${momChip(delta, pct, dir)}</td>`;
      html += `<td class="num${pct===null?' muted':''}">${pct===null?'—':fmtSigned(pct*100,1)+'%'}</td>`;
      vals.forEach(v => {
        const disp = m.isPct ? (v!==null ? (v<1?(v*100).toFixed(1):v.toFixed(1))+'%' : null) : fmtNum(v);
        html += cell(disp);
      });
      html += `</tr>`;
    });
    html += `</tbody></table></div>`;
  }

  // Top queries
  const queries = gsc.queries || [];
  if(queries.length){
    html += `<h2 class="section-title"><span class="title-txt">Top Search Queries</span></h2>`;
    html += `<div class="table-wrap"><table><thead><tr><th class="name-cell">Query</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Position</th></tr></thead><tbody>`;
    queries.slice(0,20).forEach(q => {
      const ctr = safeNum(q.ctr);
      const ctrDisp = ctr ? (ctr<1?(ctr*100).toFixed(2):ctr.toFixed(2))+'%' : '—';
      html += `<tr>${nameCell(escHtml(q.query||'—'))}${cell(fmtNum(safeNum(q.clicks)))}${cell(fmtNum(safeNum(q.impressions)))}${cell(ctrDisp)}${cell(safeNum(q.position)?Number(q.position).toFixed(1):null)}</tr>`;
    });
    html += `</tbody></table></div>`;
  }

  // Top pages
  const pages = gsc.pages || [];
  if(pages.length){
    html += `<h2 class="section-title"><span class="title-txt">Top Pages (GSC)</span></h2>`;
    html += `<div class="table-wrap"><table><thead><tr><th class="name-cell">Page</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Position</th></tr></thead><tbody>`;
    pages.slice(0,20).forEach(p => {
      const ctr = safeNum(p.ctr);
      const ctrDisp = ctr ? (ctr<1?(ctr*100).toFixed(2):ctr.toFixed(2))+'%' : '—';
      html += `<tr><td class="name-cell" style="word-break:break-all;white-space:normal;max-width:300px">${escHtml(p.page||'—')}</td>${cell(fmtNum(safeNum(p.clicks)))}${cell(fmtNum(safeNum(p.impressions)))}${cell(ctrDisp)}${cell(safeNum(p.position)?Number(p.position).toFixed(1):null)}</tr>`;
    });
    html += `</tbody></table></div>`;
  }

  // GA4 top pages
  const ga4Pages = ga4.pages || [];
  if(ga4Pages.length){
    html += `<h2 class="section-title"><span class="title-txt">Top Pages (GA4)</span></h2>`;
    html += `<div class="table-wrap"><table><thead><tr><th class="name-cell">Page</th><th>Sessions/Views</th><th>Users</th><th>Bounce Rate</th></tr></thead><tbody>`;
    ga4Pages.slice(0,20).forEach(p => {
      const br = safeNum(p.bounceRate);
      const brDisp = br ? (br<1?(br*100).toFixed(1):br.toFixed(1))+'%' : '—';
      html += `<tr><td class="name-cell" style="word-break:break-all;white-space:normal;max-width:300px">${escHtml(p.page||p.pagePath||'—')}</td>${cell(fmtNum(safeNum(p.sessions)||safeNum(p.screenPageViews)))}${cell(fmtNum(safeNum(p.users)))}${cell(brDisp)}</tr>`;
    });
    html += `</tbody></table></div>`;
  }

  // Traffic sources
  const sources = ga4.sources || [];
  if(sources.length){
    html += `<h2 class="section-title"><span class="title-txt">Traffic Sources</span></h2>`;
    html += `<div class="table-wrap"><table><thead><tr><th class="name-cell">Source</th><th>Sessions</th><th>Users</th></tr></thead><tbody>`;
    sources.slice(0,15).forEach(s => {
      html += `<tr>${nameCell(escHtml(s.source||s.sessionSource||'—'))}${cell(fmtNum(safeNum(s.sessions)))}${cell(fmtNum(safeNum(s.users)))}</tr>`;
    });
    html += `</tbody></table></div>`;
  }

  el.innerHTML = html;
  const pillDiv = document.getElementById('seoPills');
  if(pillDiv){
    pillDiv.innerHTML = '';
    pillDiv.appendChild(entityPillRow(seoEntity, e => { seoEntity=e; renderSEO(); }));
  }
}

/* ============================= PERFORMANCE PAGE ============================= */
function renderPerformance(){
  const el = document.getElementById('performance');
  let html = '<h2 class="section-title"><span class="title-txt">Performance Overview — All Channels</span></h2>';

  ENTITIES.forEach(ent => {
    const d = getEntityData(ent);
    const gsc = d.gsc || {};
    const ga4 = d.ga4 || {};
    const fb = d.social_fb || {};
    const ig = d.social_ig || {};
    const ads = d.meta_ads || [];

    const hasData = Object.keys(gsc).length || Object.keys(ga4).length || Object.keys(fb).length || Object.keys(ig).length || ads.length;
    if(!hasData) return;

    html += `<div class="subhead"><span class="dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${ENTITY_COLORS[ent]}"></span>${ENTITY_LABELS[ent]}</div>`;
    html += `<div class="table-wrap"><table><thead><tr><th class="name-cell">Metric</th><th>Value</th></tr></thead><tbody>`;

    const igR = safeNum(ig.reach)||0, fbR = safeNum(fb.reach)||0;
    const igE = safeNum(ig.engagements)||0, fbE = safeNum(fb.engagements)||0;
    const totalReach = igR+fbR, totalEng = igE+fbE;
    const engRate = totalReach>0 ? (totalEng/totalReach*100) : 0;

    if(Object.keys(ig).length || Object.keys(fb).length){
      html += `<tr class="group-row"><td colspan="2">SOCIAL MEDIA</td></tr>`;
      html += `<tr>${nameCell('Total Reach')}${cell(fmtNum(totalReach||null))}</tr>`;
      html += `<tr>${nameCell('Total Engagements')}${cell(fmtNum(totalEng||null))}</tr>`;
      html += `<tr>${nameCell('Engagement Rate')}${cell(engRate?engRate.toFixed(2)+'%':'—')}</tr>`;
    }
    if(Object.keys(gsc).length || Object.keys(ga4).length){
      html += `<tr class="group-row"><td colspan="2">SEO / ORGANIC</td></tr>`;
      html += `<tr>${nameCell('GSC Clicks')}${cell(fmtNum(safeNum(gsc.clicks)))}</tr>`;
      html += `<tr>${nameCell('GSC Impressions')}${cell(fmtNum(safeNum(gsc.impressions)))}</tr>`;
      const ctr = safeNum(gsc.ctr); html += `<tr>${nameCell('GSC CTR')}${cell(ctr?(ctr<1?(ctr*100).toFixed(2):ctr.toFixed(2))+'%':'—')}</tr>`;
      html += `<tr>${nameCell('Organic Sessions')}${cell(fmtNum(safeNum(ga4.organic_sessions)||safeNum(ga4.sessions)))}</tr>`;
      html += `<tr>${nameCell('Organic Users')}${cell(fmtNum(safeNum(ga4.organic_users)||safeNum(ga4.users)))}</tr>`;
    }
    if(ads.length){
      const ti = ads.reduce((s,c)=>s+(safeNum(c.impressions)||0),0);
      const tc = ads.reduce((s,c)=>s+(safeNum(c.clicks)||0),0);
      const tl = ads.reduce((s,c)=>s+(safeNum(c.leads)||0),0);
      const ts = ads.reduce((s,c)=>s+(safeNum(c.spend)||0),0);
      html += `<tr class="group-row"><td colspan="2">META ADS</td></tr>`;
      html += `<tr>${nameCell('Ad Impressions')}${cell(fmtNum(ti||null))}</tr>`;
      html += `<tr>${nameCell('Ad Clicks')}${cell(fmtNum(tc||null))}</tr>`;
      html += `<tr>${nameCell('Ad Leads')}${cell(fmtNum(tl||null))}</tr>`;
      html += `<tr>${nameCell('Total Spend')}${cell(fmtINR(ts||null))}</tr>`;
      html += `<tr>${nameCell('CPL')}${cell(tl?fmtINR(ts/tl):'—')}</tr>`;
    }
    html += `</tbody></table></div>`;
  });

  el.innerHTML = html;
}

/* ============================= NOTES PAGE ============================= */
function renderNotes(){
  document.getElementById('notes').innerHTML = `
    <h2 class="section-title"><span class="title-txt">Notes & Observations</span></h2>
    <div class="glass-card">
      <p style="color:var(--text-muted);font-size:0.85rem;line-height:1.6">
        This section is available for manual annotations after downloading the report.
        Add team observations, action items, and context notes here.
      </p>
      <div style="border:2px dashed var(--border-default);border-radius:1rem;padding:2rem;margin-top:1rem;text-align:center;color:var(--text-muted);font-size:0.82rem">
        Space for notes and comments
      </div>
    </div>
    <div class="footer-note">
      SEBI Registration: INA000013880 (Investment Adviser), INP000007508 (PMS), IN/AIF2/24-25/1595 (AIF).<br>
      Past performance is not indicative of future results. This report is auto-generated from live API data.
    </div>`;
}

/* ============================= ENTITY PILL ROW ============================= */
function entityPillRow(activeEntity, onSelect){
  const wrap = document.createElement('div');
  wrap.className = 'pill-row';
  wrap.innerHTML = ENTITIES.map(e => {
    const active = e===activeEntity;
    return `<button type="button" class="pill-btn ${active?'active':''}" style="color:${active?ENTITY_COLORS[e]:''}" data-entity="${e}">
      <span class="dot" style="background:${ENTITY_COLORS[e]}"></span>${ENTITY_LABELS[e]}
    </button>`;
  }).join('');
  wrap.querySelectorAll('.pill-btn').forEach(b => b.addEventListener('click', () => onSelect(b.dataset.entity)));
  return wrap;
}

/* ============================= ESCAPE ============================= */
function escHtml(s){
  if(s===null||s===undefined) return '—';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ============================= NAV / SHELL ============================= */
const ICONS = {
  overview:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>',
  ads:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/></svg>',
  smm:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 10.6l6.8-3.2M8.6 13.4l6.8 3.2"/></svg>',
  seo:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
  performance:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
  notes:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M16 13H8M16 17H8M10 9H8"/></svg>',
};
const PAGES = [
  {id:'overview', label:'Overview', icon:ICONS.overview},
  {id:'ads', label:'Ads', icon:ICONS.ads},
  {id:'smm', label:'SMM', icon:ICONS.smm},
  {id:'seo', label:'Websites & SEO', icon:ICONS.seo},
  {id:'performance', label:'Performance', icon:ICONS.performance},
  {id:'notes', label:'Notes', icon:ICONS.notes},
];
function buildNav(){
  const nav = document.getElementById('navList');
  nav.innerHTML = PAGES.map(p=>`<div class="nav-item" data-page="${p.id}">${p.icon}<span>${p.label}</span></div>`).join('');
  nav.querySelectorAll('.nav-item').forEach(el=> el.addEventListener('click', ()=> showPage(el.dataset.page)));
}
function showPage(id){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active', n.dataset.page===id));
  document.getElementById('pageTitle').textContent = PAGES.find(p=>p.id===id).label;
}
function buildPages(){
  document.getElementById('appMain').innerHTML = PAGES.map(p=>`<div class="page" id="${p.id}"></div>`).join('');
}
function renderAll(){ renderOverview(); renderAds(); renderSMM(); renderSEO(); renderPerformance(); renderNotes(); }

document.getElementById('themeToggle').addEventListener('click', ()=>{
  const isDark = document.documentElement.getAttribute('data-theme')==='dark';
  document.documentElement.setAttribute('data-theme', isDark?'light':'dark');
  document.getElementById('themeIcon').innerHTML = isDark
    ? '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'
    : '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
});

buildNav();
buildPages();
renderAll();
showPage('overview');
"""
