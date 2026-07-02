"""
Dashboard-style monthly marketing report — exact replica of RH_Monthly_Marketing_Report_2.html
with sidebar, glass-card UI, Add Month modals, localStorage, dynamicTrendTable, entity pills.
Pre-seeded with API data when available.
"""
import json as _json
from datetime import datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))


def _esc(s):
    if not isinstance(s, str):
        return str(s) if s is not None else ''
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')


def _build_seed_store(all_data: dict, start: str, end: str) -> dict:
    """Convert API data into the reference HTML's STORE format."""
    from datetime import date as _date
    try:
        end_d = _date.fromisoformat(end)
        month_label = end_d.strftime('%b')
    except Exception:
        month_label = 'Current'

    store = {
        'monthOrder': [month_label],
        'ads': {},
        'smm': {},
        'seo': {
            'content': {},
            'sites': {},
        },
    }

    ADS_CHANNELS = ['Google Ads','LinkedIn Ads','Meta (FB + Insta)','SEO / Organic Search',
                    'Content Marketing','Email Marketing','Webinars','Offline Events',
                    'Referrals (Client)','Referrals (Partner/CA)','Social Media (Organic)','PR / Media']

    # Ads from meta_ads API data (aggregate into Meta channel)
    ads_month = {}
    for ch in ADS_CHANNELS:
        ads_month[ch] = {'spend': 0, 'leads': 0, 'notes': ''}

    rh_data = all_data.get('rh', {})
    meta_ads = rh_data.get('meta_ads') or []
    total_spend = sum(float((c.get('spend') or 0)) for c in meta_ads)
    total_leads = sum(int((c.get('leads') or 0)) for c in meta_ads)
    if total_spend or total_leads:
        ads_month['Meta (FB + Insta)'] = {
            'spend': total_spend,
            'leads': total_leads,
            'notes': f'{len(meta_ads)} campaigns from API',
        }
    store['ads'][month_label] = ads_month

    # SMM from social API data
    ENTITY_MAP = {
        'rh': 'Right Horizons',
        'pms': 'Right Horizons PMS',
        'aif': 'Right Horizons AIF',
    }
    SMM_PLATFORMS = ['LinkedIn','YouTube','Instagram','Facebook','Twitter / X']
    blank_platform = {'followers': None, 'newFollowers': None, 'posts': None, 'impressions': None, 'engagementRate': None, 'ctr': None}

    for dom_key, entity_name in ENTITY_MAP.items():
        d = all_data.get(dom_key, {})
        ig = d.get('social_ig') or {}
        fb = d.get('social_fb') or {}
        month_data = {}
        for p in SMM_PLATFORMS:
            month_data[p] = dict(blank_platform)

        if ig:
            month_data['Instagram'] = {
                'followers': ig.get('followers'),
                'newFollowers': ig.get('new_followers'),
                'posts': ig.get('posts_published'),
                'impressions': ig.get('views') or ig.get('impressions'),
                'engagementRate': ig.get('engagement_rate'),
                'ctr': None,
            }
        if fb:
            month_data['Facebook'] = {
                'followers': fb.get('followers') or fb.get('page_likes'),
                'newFollowers': fb.get('new_followers'),
                'posts': fb.get('posts_published'),
                'impressions': fb.get('views') or fb.get('impressions'),
                'engagementRate': fb.get('engagement_rate'),
                'ctr': None,
            }

        store['smm'][entity_name] = {month_label: month_data}

    # SEO / Sites from GSC + GA4 API data
    SITE_METRICS_KEYS = ['sessions','uniqueVisitors','avgSessionDuration','bounceRate','organicTraffic',
                         'organicImpressions','organicCTR','avgKeywordPosition','domainAuthority',
                         'newBacklinks','top10Keywords','mobileTrafficPct','pageLoadSpeed']

    CONTENT_TYPES = ['Blog Posts / Articles','Market Commentary / Insights','Whitepapers / Guides',
                     'Videos (YouTube / Reels)','Infographics','Newsletters','Webinar Recordings',
                     'Case Studies / Testimonials','Social Media Posts']

    content_month = {}
    for ct in CONTENT_TYPES:
        content_month[ct] = 0
    store['seo']['content'][month_label] = content_month

    for dom_key, entity_name in ENTITY_MAP.items():
        d = all_data.get(dom_key, {})
        ga4 = d.get('ga4') or {}
        gsc = d.get('gsc') or {}
        site_data = {k: None for k in SITE_METRICS_KEYS}

        site_data['sessions'] = ga4.get('sessions') or ga4.get('organic_sessions')
        site_data['uniqueVisitors'] = ga4.get('users') or ga4.get('organic_users')
        site_data['avgSessionDuration'] = ga4.get('avg_session_duration')
        br = ga4.get('bounce_rate')
        site_data['bounceRate'] = br
        site_data['organicTraffic'] = ga4.get('organic_sessions') or ga4.get('sessions')
        site_data['organicImpressions'] = gsc.get('impressions')
        ctr = gsc.get('ctr')
        site_data['organicCTR'] = ctr
        site_data['avgKeywordPosition'] = gsc.get('position')

        store['seo']['sites'][entity_name] = {month_label: site_data}

    return store


def generate_html_report(all_data: dict, start: str, end: str, report_mode: str = "client") -> str:
    ts = datetime.now(_IST).strftime('%d %b %Y, %I:%M %p IST')
    seed = _build_seed_store(all_data, start, end)
    seed_json = _json.dumps(seed, default=str)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Right Horizons — Monthly Marketing Performance Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Fraunces:opsz,wght@9..144,400..700&display=swap" rel="stylesheet">
<style>
{CSS}
</style>
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
        Data is saved in this browser. <a id="resetLink">Reset to API data</a>
      </div>
    </aside>
    <div class="app-content">
      <div class="topbar">
        <div>
          <div class="topbar-title" id="pageTitle">Ads</div>
          <div class="topbar-sub">{_esc(start)} to {_esc(end)} · Prepared by Marketing</div>
        </div>
        <div class="topbar-right">
          <button class="btn btn-secondary" onclick="window.print()" style="gap:0.4rem">
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
/* ============================= STORE ============================= */
const STORAGE_KEY = 'rh_marketing_report_v2';
const API_SEED = {seed_json};
const ADS_CHANNELS = ['Google Ads','LinkedIn Ads','Meta (FB + Insta)','SEO / Organic Search','Content Marketing','Email Marketing','Webinars','Offline Events','Referrals (Client)','Referrals (Partner/CA)','Social Media (Organic)','PR / Media'];
const SMM_PLATFORMS = ['LinkedIn','YouTube','Instagram','Facebook','Twitter / X'];
const SMM_PLATFORM_ICON = {{'LinkedIn':'💼','YouTube':'▶️','Instagram':'📷','Facebook':'👥','Twitter / X':'𝕏'}};
const SMM_ENTITIES = ['Right Horizons','Right Horizons PMS','Right Horizons AIF'];
const ENTITY_COLOR = {{'Right Horizons':'#7C3AED','Right Horizons PMS':'#0EA5E9','Right Horizons AIF':'#10B981'}};
const CONTENT_TYPES = ['Blog Posts / Articles','Market Commentary / Insights','Whitepapers / Guides','Videos (YouTube / Reels)','Infographics','Newsletters','Webinar Recordings','Case Studies / Testimonials','Social Media Posts'];
const SITE_METRICS = [
  {{key:'sessions', label:'Total Website Sessions', unit:'num'}},
  {{key:'uniqueVisitors', label:'Unique Visitors', unit:'num'}},
  {{key:'avgSessionDuration', label:'Avg. Session Duration (sec)', unit:'num'}},
  {{key:'bounceRate', label:'Bounce Rate', unit:'pct'}},
  {{key:'organicTraffic', label:'Organic Traffic', unit:'num'}},
  {{key:'organicImpressions', label:'Organic Search Impressions', unit:'num'}},
  {{key:'organicCTR', label:'Organic CTR', unit:'pct'}},
  {{key:'avgKeywordPosition', label:'Avg. Keyword Position', unit:'num1'}},
  {{key:'domainAuthority', label:'Domain Authority', unit:'num'}},
  {{key:'newBacklinks', label:'New Backlinks', unit:'num'}},
  {{key:'top10Keywords', label:'Top-10 Keywords', unit:'num'}},
  {{key:'mobileTrafficPct', label:'Mobile Traffic %', unit:'pct'}},
  {{key:'pageLoadSpeed', label:'Page Load Speed (sec)', unit:'num1'}},
];
const blankSite = ()=>{{ const o={{}}; SITE_METRICS.forEach(m=>o[m.key]=null); return o; }};
const blankPlatform = ()=>({{followers:null,newFollowers:null,posts:null,impressions:null,engagementRate:null,ctr:null}});

function seedStore(){{
  return JSON.parse(JSON.stringify(API_SEED));
}}
let STORE = loadStore();
function loadStore(){{
  try{{
    const raw = localStorage.getItem(STORAGE_KEY);
    if(raw) return JSON.parse(raw);
  }}catch(e){{}}
  return seedStore();
}}
function saveStore(){{ try{{ localStorage.setItem(STORAGE_KEY, JSON.stringify(STORE)); }}catch(e){{}} }}
function addMonthName(name){{ if(!STORE.monthOrder.includes(name)) STORE.monthOrder.push(name); }}
function monthsWithData(obj){{ return STORE.monthOrder.filter(m=>obj[m]); }}
function prevMonthOf(list, current){{ const i=list.indexOf(current); return i>0?list[i-1]:null; }}

/* ============================= FORMATTERS ============================= */
const fmtINR = v => (v===null||v===undefined) ? null : '₹' + Math.round(v).toLocaleString('en-IN');
const fmtNum = (v,d=0) => (v===null||v===undefined) ? null : Number(v).toLocaleString('en-IN',{{minimumFractionDigits:d,maximumFractionDigits:d}});
const fmtPct = (v,d=1) => (v===null||v===undefined) ? null : (v*100).toFixed(d)+'%';
const fmtSigned = (v,d=1) => (v===null||v===undefined) ? null : (v>0?'+':'') + v.toFixed(d);
const fmtByUnit = (v,unit) => {{
  if(v===null||v===undefined) return null;
  if(unit==='inr') return fmtINR(v);
  if(unit==='pct') return fmtPct(v,1);
  if(unit==='num1') return v.toFixed(1);
  return fmtNum(v);
}};
function cell(val, cls){{ if(val===null||val===undefined||val==='') return `<td class="num muted">—</td>`; return `<td class="num${{cls?(' '+cls):''}}">${{val}}</td>`; }}
function nameCell(label){{ return `<td class="name-cell">${{label}}</td>`; }}
function notesCell(t){{ return `<td class="notes-cell">${{t||''}}</td>`; }}
function momChip(delta, pct, direction, deltaFmt){{
  if(delta===null||delta===undefined) return `<span class="chip chip-flat">—</span>`;
  const isZero = Math.abs(delta) < 1e-9;
  const up = delta > 0;
  let cls = 'chip-neutral';
  if(!isZero && direction==='up') cls = up ? 'chip-up-good' : 'chip-down-bad';
  if(!isZero && direction==='down') cls = up ? 'chip-up-bad' : 'chip-down-good';
  if(isZero) cls = 'chip-flat';
  const arrow = isZero ? '→' : (up ? '↑' : '↓');
  const dTxt = deltaFmt!==undefined ? deltaFmt : fmtSigned(delta);
  const pTxt = (pct===null||pct===undefined) ? '' : ` (${{fmtSigned(pct*100,1)}}%)`;
  return `<span class="chip ${{cls}}">${{arrow}} ${{dTxt}}${{pTxt}}</span>`;
}}
function statusBadge(status){{
  if(status==='GREEN') return `<span class="badge badge-green">● GREEN</span>`;
  if(status==='AMBER') return `<span class="badge badge-amber">● AMBER</span>`;
  if(status==='RED') return `<span class="badge badge-red">● RED</span>`;
  return `<span class="badge badge-flat">—</span>`;
}}
function statusForCPL(spend, leads){{
  if(!spend && !leads) return null;
  if(!leads) return null;
  const cpl = spend/leads;
  if(cpl<500) return 'GREEN';
  if(cpl<=1000) return 'AMBER';
  return 'RED';
}}

/* ============================= PILL ROWS ============================= */
function entityPillRow(activeEntity, onSelect){{
  const html = SMM_ENTITIES.map(e=>{{
    const active = e===activeEntity;
    return `<button type="button" class="pill-btn ${{active?'active':''}}" style="color:${{active?ENTITY_COLOR[e]:''}}" data-entity="${{e}}">
      <span class="dot" style="background:${{ENTITY_COLOR[e]}}"></span>${{e}}
    </button>`;
  }}).join('');
  const wrap = document.createElement('div');
  wrap.className = 'pill-row';
  wrap.innerHTML = html;
  wrap.querySelectorAll('.pill-btn').forEach(b=> b.addEventListener('click', ()=> onSelect(b.dataset.entity)));
  return wrap;
}}
function monthPillRow(months, activeMonth, onSelect, onAdd){{
  const wrap = document.createElement('div');
  wrap.className = 'pill-row';
  wrap.innerHTML = months.map(m=>{{
    const active = m===activeMonth;
    return `<button type="button" class="pill-btn ${{active?'active':''}}" style="color:${{active?'#6366F1':''}}" data-month="${{m}}">
      <span class="dot" style="background:#6366F1"></span>${{m}}
    </button>`;
  }}).join('') + `<button type="button" class="pill-add" id="addMonthBtn">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
      Add Month
    </button>`;
  wrap.querySelectorAll('.pill-btn').forEach(b=> b.addEventListener('click', ()=> onSelect(b.dataset.month)));
  wrap.querySelector('#addMonthBtn').addEventListener('click', onAdd);
  return wrap;
}}

/* ============================= MODAL ============================= */
function closeModal(){{ document.getElementById('modalOverlay').classList.remove('open'); }}
function openModal(eyebrow, title, bodyHTML, onSave){{
  const card = document.getElementById('modalCard');
  card.innerHTML = `
    <div class="modal-head">
      <div><div class="modal-eyebrow">${{eyebrow}}</div><div class="modal-title">${{title}}</div></div>
      <button class="modal-close" id="modalCloseBtn">✕</button>
    </div>
    <div id="modalBody">${{bodyHTML}}</div>
    <div class="modal-actions">
      <button class="btn btn-secondary" id="modalCancelBtn">Cancel</button>
      <button class="btn btn-primary" id="modalSaveBtn">Save Month</button>
    </div>`;
  document.getElementById('modalOverlay').classList.add('open');
  document.getElementById('modalCloseBtn').onclick = closeModal;
  document.getElementById('modalCancelBtn').onclick = closeModal;
  document.getElementById('modalSaveBtn').onclick = onSave;
}}
document.getElementById('modalOverlay').addEventListener('click', e=>{{ if(e.target.id==='modalOverlay') closeModal(); }});

function monthNameField(existingMonths){{
  return `<div class="field-group">
    <label class="field-label">Month name</label>
    <input type="text" class="field-input" id="newMonthName" placeholder="e.g. Jun, Jun 2026">
    <div style="font-size:0.68rem;color:var(--text-muted);margin-top:0.3rem;">Already added: ${{existingMonths.join(', ')||'—'}}</div>
  </div>`;
}}

/* ============================= ADS TAB ============================= */
function addMonthButton(id, label, onClick){{
  const w = document.createElement('div');
  w.className = 'pill-row';
  w.innerHTML = `<button type="button" class="pill-add" id="${{id}}"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>${{label}}</button>`;
  w.querySelector(`#${{id}}`).addEventListener('click', onClick);
  return w;
}}
function renderAds(){{
  const months = monthsWithData(STORE.ads);

  const spendRows = ADS_CHANNELS.map(c=>({{label:c, unit:'inr', direction:null,
    values: Object.fromEntries(months.map(m=>[m, STORE.ads[m][c] ? STORE.ads[m][c].spend : null]))}}));
  const spendTotal = {{label:'TOTAL SPEND', unit:'inr', direction:null, isTotal:true,
    values: Object.fromEntries(months.map(m=>[m, ADS_CHANNELS.reduce((s,c)=> s+((STORE.ads[m][c]&&STORE.ads[m][c].spend)||0),0)]))}};

  const leadsRows = ADS_CHANNELS.map(c=>({{label:c, unit:'num', direction:'up',
    values: Object.fromEntries(months.map(m=>[m, STORE.ads[m][c] ? STORE.ads[m][c].leads : null]))}}));
  const leadsTotal = {{label:'TOTAL LEADS', unit:'num', direction:'up', isTotal:true,
    values: Object.fromEntries(months.map(m=>[m, ADS_CHANNELS.reduce((s,c)=> s+((STORE.ads[m][c]&&STORE.ads[m][c].leads)||0),0)]))}};

  const cplRows = ADS_CHANNELS.map(c=>({{label:c, unit:'inr', direction:'down',
    values: Object.fromEntries(months.map(m=>{{ const d=STORE.ads[m][c]; const v=(d&&d.leads)?d.spend/d.leads:null; return [m,v]; }}))}}));
  const blendedCPL = {{label:'BLENDED CPL', unit:'inr', direction:'down', isTotal:true,
    values: Object.fromEntries(months.map(m=>{{
      const ts = ADS_CHANNELS.reduce((s,c)=> s+((STORE.ads[m][c]&&STORE.ads[m][c].spend)||0),0);
      const tl = ADS_CHANNELS.reduce((s,c)=> s+((STORE.ads[m][c]&&STORE.ads[m][c].leads)||0),0);
      return [m, tl? ts/tl : null];
    }}))}};

  const el = document.getElementById('ads');
  el.innerHTML = `<div id="adsAddBtn"></div><div id="adsBody"></div>`;
  document.getElementById('adsAddBtn').appendChild(addMonthButton('addAdsMonthBtn','Add Month', openAddAdsMonth));
  document.getElementById('adsBody').innerHTML = `
    <h2 class="section-title"><span class="title-txt">💰 Monthly Spend by Channel (₹)</span></h2>
    ${{dynamicTrendTable([...spendRows, spendTotal], months, 'inr', 'FY Total', 'sum', 'Channel')}}
    <h2 class="section-title"><span class="title-txt">📈 Monthly Leads by Channel</span></h2>
    ${{dynamicTrendTable([...leadsRows, leadsTotal], months, 'num', 'FY Total', 'sum', 'Channel')}}
    <h2 class="section-title"><span class="title-txt">💸 Monthly CPL by Channel (₹) — Lower is better</span></h2>
    ${{dynamicTrendTable([...cplRows, blendedCPL], months, 'inr', 'FY Avg', 'avg', 'Channel')}}
  `;
}}
function openAddAdsMonth(){{
  const months = monthsWithData(STORE.ads);
  const rowsHTML = ADS_CHANNELS.map((c,i)=>`<tr>
    <td class="mt-label">${{c}}</td>
    <td><input type="number" step="0.01" id="ads_spend_${{i}}" placeholder="0"></td>
    <td><input type="number" step="1" id="ads_leads_${{i}}" placeholder="0"></td>
    <td><input type="text" id="ads_notes_${{i}}" placeholder="optional note"></td>
  </tr>`).join('');
  const body = `
    ${{monthNameField(months)}}
    <div class="field-group">
      <label class="field-label">Channel spend &amp; leads</label>
      <table class="mini-table"><thead><tr><th>Channel</th><th>Spend (₹)</th><th>Leads</th><th>Notes</th></tr></thead><tbody>${{rowsHTML}}</tbody></table>
    </div>`;
  openModal('Ads', 'Add a new month', body, ()=>{{
    const name = document.getElementById('newMonthName').value.trim();
    if(!name){{ alert('Please enter a month name.'); return; }}
    const monthData = {{}};
    ADS_CHANNELS.forEach((c,i)=>{{
      const spend = parseFloat(document.getElementById(`ads_spend_${{i}}`).value) || 0;
      const leads = parseInt(document.getElementById(`ads_leads_${{i}}`).value) || 0;
      const notes = document.getElementById(`ads_notes_${{i}}`).value.trim();
      monthData[c] = {{spend, leads, notes}};
    }});
    STORE.ads[name] = monthData;
    addMonthName(name); saveStore();
    closeModal(); renderAds();
  }});
}}

/* ============================= SMM TAB ============================= */
let smmEntity = 'Right Horizons';
function renderSMM(){{
  const months = monthsWithData(STORE.smm[smmEntity]);
  const metricDefs = [
    {{k:'followers', label:'Followers', unit:'num', dir:'up'}},
    {{k:'newFollowers', label:'New Followers', unit:'num', dir:'up'}},
    {{k:'posts', label:'Posts Published', unit:'num', dir:'up'}},
    {{k:'impressions', label:'Impressions', unit:'num', dir:'up'}},
    {{k:'engagementRate', label:'Engagement Rate', unit:'pct', dir:'up'}},
    {{k:'ctr', label:'Click-Through Rate', unit:'pct', dir:'up'}},
  ];

  let tablesHTML = '';
  SMM_PLATFORMS.forEach(p=>{{
    const rows = metricDefs.map(m=>({{
      label:m.label, unit:m.unit, direction:m.dir,
      values: Object.fromEntries(months.map(mo=>{{
        const d = STORE.smm[smmEntity][mo] ? STORE.smm[smmEntity][mo][p] : null;
        return [mo, d ? d[m.k] : null];
      }})),
    }}));
    tablesHTML += `<div class="platform-tag" style="display:inline-flex;align-items:center;gap:0.4rem;font-size:0.8rem;font-weight:700;color:var(--text-primary);margin:1.1rem 0 0.5rem;">${{SMM_PLATFORM_ICON[p]}} ${{p}}</div>`;
    tablesHTML += dynamicTrendTable(rows, months, 'num', 'FY Avg', 'avg');
  }});

  const el = document.getElementById('smm');
  el.innerHTML = `<div id="smmEntityPills"></div><div id="smmAddBtn"></div><div id="smmBody"></div>`;
  document.getElementById('smmEntityPills').appendChild(entityPillRow(smmEntity, e=>{{ smmEntity=e; renderSMM(); }}));
  document.getElementById('smmAddBtn').appendChild(addMonthButton('addSmmMonthBtn', `Add Month (${{smmEntity}})`, ()=>openAddSMMMonth(smmEntity)));
  document.getElementById('smmBody').innerHTML = tablesHTML;
}}
function openAddSMMMonth(entity){{
  const months = monthsWithData(STORE.smm[entity]);
  const rowsHTML = SMM_PLATFORMS.map((p,i)=>`<tr>
    <td class="mt-label">${{SMM_PLATFORM_ICON[p]}} ${{p}}</td>
    <td><input type="number" step="1" id="smm_foll_${{i}}" placeholder="0"></td>
    <td><input type="number" step="1" id="smm_newfoll_${{i}}" placeholder="0"></td>
    <td><input type="number" step="1" id="smm_posts_${{i}}" placeholder="0"></td>
    <td><input type="number" step="1" id="smm_impr_${{i}}" placeholder="0"></td>
    <td><input type="number" step="0.01" id="smm_eng_${{i}}" placeholder="%"></td>
    <td><input type="number" step="0.01" id="smm_ctr_${{i}}" placeholder="%"></td>
  </tr>`).join('');
  const body = `
    ${{monthNameField(months)}}
    <div class="field-group">
      <label class="field-label">${{entity}} — platform metrics</label>
      <div style="overflow-x:auto;">
      <table class="mini-table"><thead><tr><th>Platform</th><th>Followers</th><th>New Foll.</th><th>Posts</th><th>Impressions</th><th>Eng. Rate %</th><th>CTR %</th></tr></thead><tbody>${{rowsHTML}}</tbody></table>
      </div>
    </div>`;
  openModal('SMM · ' + entity, 'Add a new month', body, ()=>{{
    const name = document.getElementById('newMonthName').value.trim();
    if(!name){{ alert('Please enter a month name.'); return; }}
    const monthData = {{}};
    SMM_PLATFORMS.forEach((p,i)=>{{
      const followers = parseInt(document.getElementById(`smm_foll_${{i}}`).value);
      const newFollowers = parseInt(document.getElementById(`smm_newfoll_${{i}}`).value);
      const posts = parseInt(document.getElementById(`smm_posts_${{i}}`).value);
      const impressions = parseInt(document.getElementById(`smm_impr_${{i}}`).value);
      const engRaw = document.getElementById(`smm_eng_${{i}}`).value;
      const ctrRaw = document.getElementById(`smm_ctr_${{i}}`).value;
      monthData[p] = {{
        followers: isNaN(followers)?null:followers,
        newFollowers: isNaN(newFollowers)?null:newFollowers,
        posts: isNaN(posts)?null:posts,
        impressions: isNaN(impressions)?null:impressions,
        engagementRate: engRaw===''?null:parseFloat(engRaw)/100,
        ctr: ctrRaw===''?null:parseFloat(ctrRaw)/100,
      }};
    }});
    STORE.smm[entity][name] = monthData;
    addMonthName(name); saveStore();
    closeModal(); renderSMM();
  }});
}}

/* ============================= WEBSITES & SEO TAB ============================= */
let seoSiteEntity = 'Right Horizons';
function dynamicTrendTable(rows, months, unitDefault, fyLabel, fyType, labelHeader){{
  let head = `<tr><th class="name-cell">${{labelHeader||'Metric'}}</th><th>MoM Δ</th><th>MoM %</th>`;
  months.forEach(m=> head += `<th>${{m}}</th>`);
  head += `<th>${{fyLabel}}</th></tr>`;
  const prev = months.length>1 ? months[months.length-2] : null;
  const last = months[months.length-1];
  let body = rows.map(r=>{{
    const unit = r.unit || unitDefault;
    const lastV = r.values[last];
    const prevV = prev!==null ? r.values[prev] : null;
    const delta = (lastV!==null && lastV!==undefined && prevV!==null && prevV!==undefined) ? lastV-prevV : null;
    const pct = (delta!==null && prevV) ? delta/prevV : null;
    const nums = months.map(m=>r.values[m]).filter(v=>v!==null && v!==undefined);
    let fy = null;
    if(nums.length){{ fy = fyType==='sum' ? nums.reduce((a,b)=>a+b,0) : nums.reduce((a,b)=>a+b,0)/nums.length; }}
    const rowCls = r.isTotal ? ' class="total-row"' : '';
    let tr = `<tr${{rowCls}}>${{nameCell(r.label)}}`;
    tr += `<td>${{momChip(delta, pct, r.direction, delta===null?null:fmtByUnit(Math.abs(delta),unit))}}</td>`;
    tr += `<td class="num${{pct===null?' muted':''}}">${{pct===null?'—':fmtSigned(pct*100,1)+'%'}}</td>`;
    months.forEach(m=>{{ const v=r.values[m]; tr += cell(fmtByUnit(v,unit), v===0?'muted':''); }});
    tr += cell(fmtByUnit(fy,unit));
    tr += `</tr>`;
    return tr;
  }}).join('');
  return `<div class="table-wrap"><table><thead>${{head}}</thead><tbody>${{body}}</tbody></table></div>`;
}}
function renderSEO(){{
  const contentMonths = monthsWithData(STORE.seo.content);
  const contentRows = CONTENT_TYPES.map(t=>({{label:t, unit:'num', direction:'up', values: Object.fromEntries(contentMonths.map(m=>[m, STORE.seo.content[m][t]]))}}));
  const totalRow = {{label:'TOTAL CONTENT PUBLISHED', unit:'num', direction:'up', isTotal:true,
    values: Object.fromEntries(contentMonths.map(m=>[m, CONTENT_TYPES.reduce((s,t)=> s + (STORE.seo.content[m][t]||0), 0)]))}};

  const siteMonths = monthsWithData(STORE.seo.sites[seoSiteEntity]);
  const siteRows = SITE_METRICS.map(m=>({{
    label:m.label, unit:m.unit,
    direction: (m.key==='bounceRate'||m.key==='avgKeywordPosition'||m.key==='pageLoadSpeed') ? 'down' : (m.key==='avgSessionDuration'||m.key==='mobileTrafficPct'||m.key==='domainAuthority' ? null : 'up'),
    values: Object.fromEntries(siteMonths.map(mo=>[mo, STORE.seo.sites[seoSiteEntity][mo][m.key]])),
  }}));

  const el = document.getElementById('seo');
  el.innerHTML = `<div id="seoBody"></div>`;
  document.getElementById('seoBody').innerHTML = `
    <h2 class="section-title"><span class="title-txt">✍️ Content Publishing — # Published per Month</span></h2>
    <div id="contentPills"></div>
    ${{dynamicTrendTable([...contentRows, totalRow], contentMonths, 'num', 'FY Total', 'sum')}}

    <h2 class="section-title" style="margin-top:2.25rem;"><span class="title-txt">🌐 Website &amp; SEO Metrics</span></h2>
    <div id="seoEntityPills"></div>
    <div id="seoSitePills"></div>
    ${{dynamicTrendTable(siteRows, siteMonths, 'num', 'FY Avg', 'avg')}}
  `;
  document.getElementById('contentPills').appendChild(
    (()=>{{ const w=document.createElement('div'); w.className='pill-row'; w.innerHTML = `<button type="button" class="pill-add" id="addContentMonthBtn"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>Add Month (Content)</button>`;
      w.querySelector('#addContentMonthBtn').addEventListener('click', openAddContentMonth); return w; }})()
  );
  document.getElementById('seoEntityPills').appendChild(entityPillRow(seoSiteEntity, e=>{{ seoSiteEntity=e; renderSEO(); }}));
  document.getElementById('seoSitePills').appendChild(
    (()=>{{ const w=document.createElement('div'); w.className='pill-row'; w.innerHTML = `<button type="button" class="pill-add" id="addSiteMonthBtn"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>Add Month (${{seoSiteEntity}})</button>`;
      w.querySelector('#addSiteMonthBtn').addEventListener('click', ()=>openAddSiteMonth(seoSiteEntity)); return w; }})()
  );
}}
function openAddContentMonth(){{
  const months = monthsWithData(STORE.seo.content);
  const rowsHTML = CONTENT_TYPES.map((t,i)=>`<tr><td class="mt-label">${{t}}</td><td><input type="number" step="1" id="content_${{i}}" placeholder="0"></td></tr>`).join('');
  const body = `${{monthNameField(months)}}
    <div class="field-group"><label class="field-label">Items published</label>
    <table class="mini-table"><thead><tr><th>Content Type</th><th># Published</th></tr></thead><tbody>${{rowsHTML}}</tbody></table></div>`;
  openModal('Websites & SEO', 'Add a new month — Content Publishing', body, ()=>{{
    const name = document.getElementById('newMonthName').value.trim();
    if(!name){{ alert('Please enter a month name.'); return; }}
    const monthData = {{}};
    CONTENT_TYPES.forEach((t,i)=>{{ monthData[t] = parseInt(document.getElementById(`content_${{i}}`).value) || 0; }});
    STORE.seo.content[name] = monthData;
    addMonthName(name); saveStore();
    closeModal(); renderSEO();
  }});
}}
function openAddSiteMonth(entity){{
  const months = monthsWithData(STORE.seo.sites[entity]);
  const rowsHTML = SITE_METRICS.map((m,i)=>`<tr><td class="mt-label">${{m.label}}</td><td><input type="number" step="0.01" id="site_${{i}}" placeholder="${{m.unit==='pct'?'%':'0'}}"></td></tr>`).join('');
  const body = `${{monthNameField(months)}}
    <div class="field-group"><label class="field-label">${{entity}} — site metrics</label>
    <table class="mini-table"><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>${{rowsHTML}}</tbody></table></div>`;
  openModal('Websites & SEO · ' + entity, 'Add a new month — Site Metrics', body, ()=>{{
    const name = document.getElementById('newMonthName').value.trim();
    if(!name){{ alert('Please enter a month name.'); return; }}
    const monthData = {{}};
    SITE_METRICS.forEach((m,i)=>{{
      const raw = document.getElementById(`site_${{i}}`).value;
      if(raw===''){{ monthData[m.key]=null; return; }}
      const num = parseFloat(raw);
      monthData[m.key] = m.unit==='pct' ? num/100 : num;
    }});
    STORE.seo.sites[entity][name] = monthData;
    addMonthName(name); saveStore();
    closeModal(); renderSEO();
  }});
}}

/* ============================= NAV / SHELL ============================= */
const ICONS = {{
  ads:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/></svg>',
  smm:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 10.6l6.8-3.2M8.6 13.4l6.8 3.2"/></svg>',
  seo:'<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>',
}};
const PAGES = [
  {{id:'ads', label:'Ads', icon:ICONS.ads}},
  {{id:'smm', label:'SMM', icon:ICONS.smm}},
  {{id:'seo', label:'Websites & SEO', icon:ICONS.seo}},
];
function buildNav(){{
  const nav = document.getElementById('navList');
  nav.innerHTML = PAGES.map(p=>`<div class="nav-item" data-page="${{p.id}}">${{p.icon}}<span>${{p.label}}</span></div>`).join('');
  nav.querySelectorAll('.nav-item').forEach(el=> el.addEventListener('click', ()=> showPage(el.dataset.page)));
}}
function showPage(id){{
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active', n.dataset.page===id));
  document.getElementById('pageTitle').textContent = PAGES.find(p=>p.id===id).label;
}}
function buildPages(){{
  document.getElementById('appMain').innerHTML = PAGES.map(p=>`<div class="page" id="${{p.id}}"></div>`).join('');
}}
function renderAll(){{ renderAds(); renderSMM(); renderSEO(); }}

document.getElementById('themeToggle').addEventListener('click', ()=>{{
  const isDark = document.documentElement.getAttribute('data-theme')==='dark';
  document.documentElement.setAttribute('data-theme', isDark?'light':'dark');
  document.getElementById('themeIcon').innerHTML = isDark
    ? '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'
    : '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
}});
document.getElementById('resetLink').addEventListener('click', ()=>{{
  if(confirm('Reset all data back to the API data? This clears anything you added.')){{
    STORE = seedStore(); saveStore(); renderAll(); showPage('ads');
  }}
}});

buildNav();
buildPages();
renderAll();
showPage('ads');
</script>
</body>
</html>"""


CSS = """:root{
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
.sidebar-footnote a{color:var(--accent-primary); cursor:pointer; text-decoration:none; font-weight:600;}
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
.glass-card{background:var(--surface-card); border:1px solid var(--border-subtle); border-radius:1.5rem; box-shadow:0 2px 12px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04); padding:1.25rem;}
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
.pill-row{display:flex; align-items:center; gap:1.6rem; flex-wrap:wrap; margin-bottom:1.25rem;}
.pill-btn{display:inline-flex; align-items:center; gap:0.45rem; background:none; border:none; cursor:pointer; font-family:inherit; font-size:0.85rem; font-weight:600; color:var(--text-muted); padding:0.15rem 0; transition:color .15s;}
.pill-btn .dot{width:8px; height:8px; border-radius:50%; opacity:0.45; transition:opacity .15s, transform .15s;}
.pill-btn.active{font-weight:700;}
.pill-btn.active .dot{opacity:1; transform:scale(1.15);}
.pill-btn:hover{color:var(--text-secondary);}
.pill-add{display:inline-flex; align-items:center; gap:0.3rem; font-size:0.78rem; font-weight:700; color:var(--accent-primary); background:var(--accent-primary-soft); border:1px dashed var(--accent-primary); border-radius:9999px; padding:0.3rem 0.75rem 0.3rem 0.55rem; cursor:pointer; font-family:inherit;}
.pill-add:hover{background:rgba(124,58,237,0.16);}
.subhead{font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--accent-section); margin:1.5rem 0 0.6rem; display:flex; align-items:center; gap:0.4rem;}
.subhead:first-child{margin-top:0;}
.platform-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:1rem; margin-bottom:1.5rem;}
.platform-card-head{font-weight:800; font-size:0.85rem; margin-bottom:0.7rem; display:flex; align-items:center; gap:0.45rem; color:var(--text-primary);}
.stat-row{display:flex; justify-content:space-between; align-items:center; gap:0.5rem; padding:0.4rem 0; border-bottom:1px solid var(--border-subtle); font-size:0.78rem;}
.stat-row:last-child{border-bottom:none;}
.stat-row .lbl{color:var(--text-muted); font-weight:500;}
.stat-row .valwrap{display:flex; align-items:center; gap:0.45rem;}
.stat-val{font-weight:700; color:var(--text-primary); font-variant-numeric:tabular-nums;}
.footer-note{font-size:0.72rem; color:var(--text-muted); text-align:center; padding:1.5rem 0 0.5rem; line-height:1.5;}
::-webkit-scrollbar{width:8px; height:8px;}
::-webkit-scrollbar-thumb{background:var(--border-default); border-radius:9999px;}
.modal-overlay{position:fixed; inset:0; background:rgba(15,23,42,0.5); backdrop-filter:blur(4px); display:none; align-items:center; justify-content:center; z-index:100; padding:1.5rem;}
.modal-overlay.open{display:flex;}
.modal-card{width:100%; max-width:640px; max-height:88vh; overflow-y:auto; background:var(--surface-card-elevated); border:1px solid var(--border-subtle); border-radius:2rem; box-shadow:0 32px 80px rgba(0,0,0,0.18); padding:1.6rem 1.75rem;}
[data-theme="dark"] .modal-card{background:#1E293B;}
.modal-head{display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:1.1rem;}
.modal-eyebrow{font-size:0.68rem; font-weight:700; text-transform:uppercase; letter-spacing:0.07em; color:var(--accent-section);}
.modal-title{font-size:1.05rem; font-weight:800; color:var(--text-primary); margin-top:0.2rem;}
.modal-close{width:32px; height:32px; border-radius:50%; border:none; background:var(--surface-hover); color:var(--text-secondary); cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0;}
.field-group{margin-bottom:1rem;}
.field-label{font-size:0.72rem; font-weight:700; color:var(--text-secondary); margin-bottom:0.35rem; display:block;}
.field-input, .field-select{width:100%; padding:0.55rem 0.75rem; border-radius:0.75rem; border:1.5px solid var(--border-input); background:var(--surface-input); color:var(--text-primary); font-family:inherit; font-size:0.85rem;}
.field-input:focus, .field-select:focus{outline:none; border-color:#6366F1; box-shadow:0 0 0 3px rgba(99,102,241,0.15);}
.mini-table{width:100%; border-collapse:collapse; margin-bottom:0.5rem;}
.mini-table th{font-size:0.62rem; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-muted); text-align:left; padding:0.3rem 0.4rem; border-bottom:1px solid var(--border-subtle);}
.mini-table td{padding:0.3rem 0.4rem; border-bottom:1px solid var(--border-subtle);}
.mini-table td.mt-label{font-size:0.78rem; font-weight:600; color:var(--text-primary); white-space:nowrap;}
.mini-table input{width:100%; padding:0.4rem 0.5rem; border-radius:0.5rem; border:1.5px solid var(--border-input); background:var(--surface-input); color:var(--text-primary); font-family:inherit; font-size:0.78rem;}
.mini-table input:focus{outline:none; border-color:#6366F1;}
.modal-actions{display:flex; justify-content:flex-end; gap:0.6rem; margin-top:1.2rem; position:sticky; bottom:0; background:var(--surface-card-elevated); padding-top:0.75rem;}
[data-theme="dark"] .modal-actions{background:#1E293B;}
.btn{display:inline-flex; align-items:center; gap:0.4rem; padding:0.6rem 1.1rem; border-radius:0.875rem; font-family:inherit; font-size:0.82rem; font-weight:700; cursor:pointer; border:none;}
.btn-primary{background:#6366F1; color:#fff;}
.btn-primary:hover{background:#4F46E5;}
.btn-secondary{background:rgba(255,255,255,0.7); color:#374151; border:1px solid var(--border-subtle);}
[data-theme="dark"] .btn-secondary{background:rgba(255,255,255,0.08); color:var(--text-secondary);}
@media(max-width:900px){
  .app-shell{flex-direction:column;}
  .sidebar{width:100%; flex-direction:row; overflow-x:auto; border-right:none; border-bottom:1px solid var(--border-subtle); padding:0.75rem;}
  .sidebar .brand{display:none;}
  .sidebar-footnote{display:none;}
  .app-main{padding:1rem;}
}
@media print{
  body{background:#fff!important;}
  .atmosphere,.sidebar,.topbar,.theme-toggle,.btn,.pill-add{display:none!important;}
  .app-shell{border:none; box-shadow:none; background:#fff!important; display:block!important;}
  .app-content{display:block!important;}
  .app-main{padding:0!important; overflow:visible!important;}
  .page{display:block!important; page-break-after:always;}
  .glass-card,.kpi-card,.table-wrap{box-shadow:none; border:1px solid #e5e7eb;}
  table{min-width:0!important; font-size:9px;}
}"""
