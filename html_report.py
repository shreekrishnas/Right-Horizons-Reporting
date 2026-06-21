"""
Premium HTML marketing report — matches the final.html template exactly:
Hero header, nav anchors, Executive Summary with pills,
KPI Snapshot, Performance Overview, SEO Trend, SMM Trend, Ads, Metrics Index.
"""
from datetime import datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))


def _f(val, pct=False, cur=False):
    if val is None or val == '' or val == '-':
        return '—'
    if isinstance(val, str):
        return val
    if pct:
        if isinstance(val, (int, float)):
            v = val * 100 if abs(val) < 1 else val
            return f"{v:.2f}%" if v else '—'
        return '—'
    if cur:
        return f"₹{val:,.2f}" if val else '—'
    if isinstance(val, float):
        return f"{int(val):,}" if val == int(val) else f"{val:,.2f}"
    if isinstance(val, int):
        return f"{val:,}"
    return str(val)


def _g(d, k, default=None):
    if not isinstance(d, dict):
        return default
    return d.get(k, default)


def _delta(curr, prev):
    if not curr or not prev:
        return '—', '—'
    try:
        c, p = float(curr), float(prev)
        d = c - p
        pct = ((c - p) / p * 100) if p != 0 else 0
        sign = '+' if d > 0 else ''
        d_str = f"{sign}{_f(int(d))}" if d == int(d) else f"{sign}{d:.2f}"
        p_str = f"{sign}{pct:.1f}%" if pct else '—'
        return d_str, p_str
    except (ValueError, TypeError):
        return '—', '—'


CSS = """\
:root{--ink:#172033;--muted:#64748b;--soft:#f6f8fb;--line:#e5e7eb;--brand:#165e83;--brand2:#0ea5a4;--warn:#b45309;--danger:#b91c1c;--good:#047857;--card:#ffffff;--lav:#eef2ff}*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#f3f6fb;color:var(--ink);line-height:1.45}.wrap{max-width:1360px;margin:0 auto;padding:28px}.hero{background:linear-gradient(135deg,#0f2b46,#165e83 52%,#0ea5a4);color:#fff;border-radius:24px;padding:28px;box-shadow:0 24px 70px rgba(15,43,70,.25);position:relative;overflow:hidden}.hero:after{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;background:rgba(255,255,255,.12);border-radius:50%}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:800;opacity:.85}.hero h1{font-size:36px;margin:8px 0 8px;line-height:1.08}.hero p{max-width:820px;margin:0;color:rgba(255,255,255,.86);font-size:15px}.hero-grid{display:grid;grid-template-columns:2fr 1fr;gap:18px;align-items:end}.period-card{position:relative;z-index:1;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.22);border-radius:18px;padding:16px}.period-card b{display:block;font-size:20px}.period-card span{display:block;color:rgba(255,255,255,.75);font-size:12px;margin-top:4px}.nav{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.nav a{background:#fff;border:1px solid var(--line);border-radius:999px;padding:10px 14px;color:#334155;text-decoration:none;font-weight:800;font-size:13px;box-shadow:0 8px 20px rgba(15,23,42,.05)}.nav a:hover{border-color:#165e83;color:#165e83}.section{margin:20px 0 34px}.section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;margin-bottom:12px}.section h2{font-size:24px;margin:0}.section .sub{color:var(--muted);font-size:13px}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:0 12px 35px rgba(15,23,42,.07);padding:18px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.kpi{background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:0 8px 24px rgba(15,23,42,.05)}.kpi .label{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:900}.kpi .value{font-size:26px;font-weight:900;margin-top:6px}.kpi .meta{font-size:12px;color:var(--muted);margin-top:6px}.pill{display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;font-size:11px;font-weight:900;background:#eef2ff;color:#3730a3}.pill.good{background:#dcfce7;color:#166534}.pill.warn{background:#ffedd5;color:#9a3412}.pill.bad{background:#fee2e2;color:#991b1b}.summary-block{white-space:pre-line;background:#fff;border-left:5px solid #0ea5a4;border-radius:14px;border-top:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:16px;color:#334155}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:16px;background:#fff}.report-table{border-collapse:collapse;width:100%;font-size:12px;min-width:920px}.report-table th,.report-table td{border-bottom:1px solid #eef2f7;border-right:1px solid #eef2f7;padding:8px 10px;vertical-align:top}.report-table th{background:#eff6ff;color:#0f2b46;text-align:left;font-weight:900;white-space:nowrap;position:sticky;top:0;z-index:2}.report-table td:first-child,.report-table th:first-child{position:sticky;left:0;background:#fff;z-index:1;min-width:240px;font-weight:800;color:#1e293b}.report-table th:first-child{background:#eff6ff;z-index:3}.report-table tr.group td{background:#f8fafc!important;color:#165e83;font-weight:900;text-transform:uppercase;letter-spacing:.04em}.report-table td.num{text-align:right;font-variant-numeric:tabular-nums}.report-table td.note{min-width:360px;color:#475569}.metric-index{columns:3;column-gap:28px}.metric-index div{break-inside:avoid;background:#fff;border:1px solid #eef2f7;border-radius:10px;padding:7px 9px;margin:0 0 8px;font-size:12px}.page-break{page-break-before:always}.tiny{font-size:11px;color:var(--muted)}.toolbar{display:flex;gap:10px;align-items:center;justify-content:flex-end;margin:14px 0}.btn{border:0;background:#165e83;color:#fff;border-radius:999px;padding:10px 14px;font-weight:900;cursor:pointer}.btn.secondary{background:#fff;color:#165e83;border:1px solid #bae6fd}@media(max-width:900px){.hero-grid,.cards{grid-template-columns:1fr}.metric-index{columns:1}.wrap{padding:16px}.hero h1{font-size:28px}}@media print{body{background:#fff}.wrap{max-width:none;padding:0}.nav,.toolbar{display:none}.card,.kpi,.hero{box-shadow:none}.table-wrap{overflow:visible}.report-table{font-size:9px;min-width:0}.report-table th,.report-table td{padding:5px}.page-break{page-break-before:always}}
"""


def _esc(s):
    """HTML-escape a string."""
    if not isinstance(s, str):
        return str(s) if s is not None else '—'
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')


def generate_html_report(data: dict, start: str, end: str, domain: str) -> str:
    data = data or {}
    ts = datetime.now(_IST).strftime('%d %b %Y, %I:%M %p IST')

    gsc = data.get('gsc') or {}
    ga4 = data.get('ga4') or {}
    fb = data.get('social_fb') or {}
    ig = data.get('social_ig') or {}
    ads = data.get('meta_ads') or []
    smm_trend = data.get('social_trend') or []
    seo_trend = data.get('seo_trend') or []

    # AI summary data (if present)
    ai_summary = data.get('ai_summary') or data.get('executive_summary') or {}

    hero = _hero(domain, start, end)
    toolbar = _toolbar()
    nav = _nav()
    exec_summary = _exec_summary_section(ai_summary, gsc, ga4, fb, ig, ads)
    kpi_snapshot = _kpi_snapshot(gsc, ga4, fb, ig, ads, seo_trend, smm_trend)
    perf_overview = _perf_overview(gsc, ga4, fb, ig, ads)
    seo_section = _seo_trend_section(seo_trend, gsc, ga4)
    smm_section = _smm_trend_section(smm_trend)
    ads_section = _ads_section(ads)
    metrics_index = _metrics_index()

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{_esc(domain)} — Marketing Report</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet"><style>
{CSS}</style></head><body><div class="wrap">
{hero}
{toolbar}
{nav}
{exec_summary}
{kpi_snapshot}
{perf_overview}
{seo_section}
{smm_section}
{ads_section}
{metrics_index}
</div></body></html>"""


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
def _hero(domain, start, end):
    return f"""<div class="hero"><div class="hero-grid"><div><div class="eyebrow">Reporting Room &middot; {_esc(domain)}</div><h1>Weekly / Monthly Full Metrics Report</h1><p>Detailed workbook-style weekly/monthly report covering SEO, Social Media, and Paid Ads performance.</p></div><div class="period-card"><span>Reporting period</span><b>{_esc(start)} &ndash; {_esc(end)}</b><span>Generated for {_esc(domain)}</span></div></div></div>"""


# ---------------------------------------------------------------------------
# Toolbar
# ---------------------------------------------------------------------------
def _toolbar():
    return """<div class="toolbar"><button class="btn" onclick="window.print()">Print / Save PDF</button></div>"""


# ---------------------------------------------------------------------------
# Navigation anchors
# ---------------------------------------------------------------------------
def _nav():
    return """<div class="nav"><a href="#summary">Executive Summary</a><a href="#quick-kpis">KPI Snapshot</a><a href="#performance-overview">Performance Overview</a><a href="#seo-trend">SEO Trend</a><a href="#smm-trend">SMM Trend</a><a href="#ads">Ads</a><a href="#metrics-index">All Metrics Index</a></div>"""


# ---------------------------------------------------------------------------
# Executive Summary with pill badges
# ---------------------------------------------------------------------------
def _exec_summary_section(ai_summary, gsc, ga4, fb, ig, ads):
    headline = _g(ai_summary, 'headline') or _g(ai_summary, 'the_headline') or '—'
    working = _g(ai_summary, 'whats_working') or _g(ai_summary, 'working') or '—'
    attention = _g(ai_summary, 'needs_attention') or _g(ai_summary, 'attention') or '—'
    actions = _g(ai_summary, 'recommended_actions') or _g(ai_summary, 'actions') or '—'

    return f"""<section class="section" id="summary"><div class="section-head"><div><h2>Executive Summary</h2><div class="sub">AI-generated executive summary for the reporting period.</div></div></div>
<div class="card" style="margin-bottom:12px"><span class="pill">The Headline</span><div class="summary-block" style="margin-top:12px">{headline}</div></div>
<div class="card" style="margin-bottom:12px"><span class="pill good">What&#x27;s Working</span><div class="summary-block" style="margin-top:12px">{working}</div></div>
<div class="card" style="margin-bottom:12px"><span class="pill warn">What Needs Attention</span><div class="summary-block" style="margin-top:12px">{attention}</div></div>
<div class="card" style="margin-bottom:12px"><span class="pill bad">Recommended Actions</span><div class="summary-block" style="margin-top:12px">{actions}</div></div>
</section>"""


# ---------------------------------------------------------------------------
# KPI Snapshot cards (4 columns)
# ---------------------------------------------------------------------------
def _kpi_snapshot(gsc, ga4, fb, ig, ads, seo_trend, smm_trend):
    ig_r = _g(ig, 'reach', 0) or 0
    fb_r = _g(fb, 'reach', 0) or 0
    ig_e = _g(ig, 'engagements', 0) or 0
    fb_e = _g(fb, 'engagements', 0) or 0
    ig_v = _g(ig, 'views', 0) or 0
    fb_v = _g(fb, 'views', 0) or 0
    org = _g(ga4, 'organic_sessions', 0) or _g(ga4, 'sessions', 0) or 0
    ai = sum(int(_g(c, 'impressions', 0) or 0) for c in ads)
    ac = sum(int(_g(c, 'clicks', 0) or 0) for c in ads)
    al = sum(int(_g(c, 'leads', 0) or 0) for c in ads)

    total_reach = ig_r + fb_r
    total_imp = ig_v + fb_v
    total_eng = ig_e + fb_e
    eng_rate = (total_eng / total_reach * 100) if total_reach > 0 else 0
    ctr = (ac / ai * 100) if ai > 0 else 0

    # Try to get previous-period values from trend data
    prev_reach = '—'
    prev_imp = '—'
    prev_eng = '—'
    prev_eng_rate = '—'
    prev_org = '—'
    prev_ai = '—'
    prev_ac = '—'

    if len(seo_trend) >= 2:
        prev_org = _f(_g(seo_trend[-2], 'sessions') or _g(seo_trend[-2], 'organic_sessions'))

    kpis = [
        ('Total Reach (all platforms)', _f(total_reach or None), prev_reach),
        ('Total Impressions (all platforms)', _f(total_imp or None), prev_imp),
        ('Total Engagements', _f(total_eng or None), prev_eng),
        ('Avg. Engagement Rate (%)', f"{eng_rate:.2f}%" if eng_rate else '—', prev_eng_rate),
        ('Organic Sessions (SEO)', _f(org or None), prev_org),
        ('Total Ad Impressions', _f(ai or None), prev_ai),
        ('Total Ad Clicks', _f(ac or None), prev_ac),
        ('Total Leads', _f(al or None), '—'),
    ]

    cards = ''
    for label, value, prev in kpis:
        meta = f'<div class="meta">Last period: {prev}</div>' if prev != '—' else ''
        cards += f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div>{meta}</div>'

    return f"""<section class="section" id="quick-kpis"><div class="section-head"><div><h2>Current Period KPI Snapshot</h2><div class="sub">High-level cards from Performance Overview.</div></div></div><div class="cards">{cards}</div></section>"""


# ---------------------------------------------------------------------------
# Performance Overview table
# ---------------------------------------------------------------------------
def _perf_overview(gsc, ga4, fb, ig, ads):
    ig_r = _g(ig, 'reach', 0) or 0
    fb_r = _g(fb, 'reach', 0) or 0
    ig_e = _g(ig, 'engagements', 0) or 0
    fb_e = _g(fb, 'engagements', 0) or 0
    ig_v = _g(ig, 'views', 0) or 0
    fb_v = _g(fb, 'views', 0) or 0
    org = _g(ga4, 'organic_sessions', 0) or _g(ga4, 'sessions', 0) or 0
    ai = sum(int(_g(c, 'impressions', 0) or 0) for c in ads)
    ac = sum(int(_g(c, 'clicks', 0) or 0) for c in ads)
    al = sum(int(_g(c, 'leads', 0) or 0) for c in ads)
    total_reach = ig_r + fb_r
    total_imp = ig_v + fb_v
    total_eng = ig_e + fb_e
    eng_rate = (total_eng / total_reach * 100) if total_reach > 0 else 0
    ctr = (ac / ai * 100) if ai > 0 else 0

    rows = [
        ('Total Reach (all platforms)', _f(total_reach or None)),
        ('Total Impressions (all platforms)', _f(total_imp or None)),
        ('Total Engagements', _f(total_eng or None)),
        ('Avg. Engagement Rate (%)', f"{eng_rate:.2f}%" if eng_rate else '—'),
        ('Organic Sessions (SEO)', _f(org or None)),
        ('Total Ad Impressions', _f(ai or None)),
        ('Total Ad Clicks', _f(ac or None)),
        ('Overall Ad CTR (%)', f"{ctr:.2f}%" if ctr else '—'),
        ('Total Leads', _f(al or None)),
    ]

    trs = ''
    for label, val in rows:
        trs += f'<tr><td>{label}</td><td class="num">{val}</td></tr>'

    return f"""<section class="section page-break" id="performance-overview"><div class="section-head"><div><h2>Performance Overview — Full Sheet Metrics</h2><div class="sub">All metric names and current period values.</div></div><span class="pill">{len(rows)} rows</span></div><div class="table-wrap"><table class="report-table"><tr class="group"><td colspan="2">PERFORMANCE SUMMARY — ALL CHANNELS</td></tr><tr><th>Metric</th><th>This Period</th></tr>{trs}</table></div></section>"""


# ---------------------------------------------------------------------------
# SEO Trend (5-week with WoW delta)
# ---------------------------------------------------------------------------
def _seo_trend_section(seo_trend, gsc, ga4):
    if not seo_trend and not gsc and not ga4:
        return ''

    if not seo_trend:
        # Fallback: single-column table from GSC/GA4 data
        metrics = [
            ('Organic Sessions', _f(_g(ga4, 'organic_sessions') or _g(ga4, 'sessions'))),
            ('Organic Users', _f(_g(ga4, 'organic_users') or _g(ga4, 'users'))),
            ('Bounce Rate', _f(_g(ga4, 'bounce_rate'), pct=True)),
            ('GSC Clicks', _f(_g(gsc, 'clicks'))),
            ('GSC Impressions', _f(_g(gsc, 'impressions'))),
            ('Avg. Position', _f(_g(gsc, 'position'))),
        ]
        trs = ''.join(f'<tr><td>{l}</td><td class="num">{v}</td></tr>' for l, v in metrics)
        return f"""<section class="section page-break" id="seo-trend"><div class="section-head"><div><h2>SEO Trend</h2><div class="sub">Current period data (no weekly trend available).</div></div></div><div class="table-wrap"><table class="report-table"><tr><th>Metric</th><th>Value</th></tr>{trs}</table></div></section>"""

    # Build period headers from trend data
    periods = []
    for t in seo_trend:
        ps = t.get('period_start', '')
        pe = t.get('period_end', '')
        if ps and pe:
            periods.append(f"{ps} &ndash; {pe}")
        else:
            periods.append(t.get('period', ''))

    n = len(periods)
    ph = ''.join(f'<th>{p}</th>' for p in periods)
    wow_h = '<th>WoW &Delta;</th><th>WoW %</th>' if n >= 2 else ''

    seo_metrics = [
        ('TRAFFIC', None),
        ('Organic Sessions', 'sessions', False),
        ('Organic Users', 'users', False),
        ('Website Leads', 'leads', False),
        ('ENGAGEMENT', None),
        ('Avg. Session Duration (sec)', 'avg_session_duration', False),
        ('Bounce Rate', 'bounce_rate', True),
        ('SEARCH CONSOLE', None),
        ('Google Search Console Clicks', 'clicks', False),
        ('Google Search Console Impressions', 'impressions', False),
        ('Avg. Position', 'position', False),
        ('INDEXING &amp; AUTHORITY', None),
        ('Pages Indexed', 'pages_indexed', False),
        ('Backlinks (total)', 'backlinks', False),
        ('Domain Rating', 'domain_rating', False),
    ]

    trs = ''
    for item in seo_metrics:
        if item[1] is None:
            # Group header row
            trs += f'<tr class="group"><td colspan="{n + 1 + (2 if n >= 2 else 0)}">  {item[0]}</td></tr>'
            continue
        label, key, is_pct = item
        vals = [t.get(key) for t in seo_trend]
        cells = ''.join(f'<td class="num">{_f(v, pct=is_pct)}</td>' for v in vals)
        wow = ''
        if n >= 2:
            d_str, p_str = _delta(vals[-1], vals[-2] if len(vals) >= 2 else None)
            wow = f'<td class="num">{d_str}</td><td class="num">{p_str}</td>'
        trs += f'<tr><td>{label}</td>{wow}{cells}</tr>'

    return f"""<section class="section page-break" id="seo-trend"><div class="section-head"><div><h2>SEO Trend — Full Sheet Metrics</h2><div class="sub">All metric names, period columns, and notes from the workbook are included here.</div></div><span class="pill">{len([m for m in seo_metrics if m[1] is not None])} rows</span></div><div class="table-wrap"><table class="report-table"><tr><td colspan="{n + 1 + (2 if n >= 2 else 0)}">SEO Weekly Performance — {n} Week Trend</td></tr><tr><th>Metric</th>{wow_h}{ph}</tr>{trs}</table></div></section>"""


# ---------------------------------------------------------------------------
# SMM Trend (Instagram, Facebook, LinkedIn with 5-week trend)
# ---------------------------------------------------------------------------
def _smm_trend_section(smm_trend):
    if not smm_trend:
        return f"""<section class="section page-break" id="smm-trend"><div class="section-head"><div><h2>SMM Trend — Full Sheet Metrics</h2><div class="sub">No social media trend data available for this period.</div></div></div></section>"""

    periods = []
    for t in smm_trend:
        ps = t.get('period_start', '')
        pe = t.get('period_end', '')
        if ps and pe:
            periods.append(f"{ps} &ndash; {pe}")
        else:
            periods.append(t.get('period', ''))

    n = len(periods)
    ph = ''.join(f'<th>{p}</th>' for p in periods)
    wow_h = '<th>WoW &Delta;</th><th>WoW %</th>' if n >= 2 else ''
    col_span = n + 1 + (2 if n >= 2 else 0) + 1  # +1 for notes

    smm_metrics = [
        ('Followers / Page Likes', 'followers'),
        ('New Followers (net)', 'new_followers'),
        ('Reach', 'reach'),
        ('Views', 'views'),
        ('Engagements (total)', 'engagements'),
        ('Posts Published', 'posts'),
        ('Link Clicks', 'link_clicks'),
        ('Profile Visits / Page Views', 'profile_visits'),
    ]

    platform_configs = [
        ('ig', 'INSTAGRAM'),
        ('fb', 'FACEBOOK'),
        ('li', 'LINKEDIN'),
    ]

    trs = ''
    for plat_key, plat_label in platform_configs:
        # Check if any data exists for this platform
        has_data = any(t.get(plat_key) for t in smm_trend)
        if not has_data and plat_key == 'li':
            continue  # Skip LinkedIn if no data

        trs += f'<tr class="group"><td colspan="{col_span}">  {plat_label}</td></tr>'

        for mlabel, mkey in smm_metrics:
            vals = []
            for t in smm_trend:
                src = t.get(plat_key) or {}
                vals.append(src.get(mkey))
            cells = ''.join(f'<td class="num">{_f(v)}</td>' for v in vals)
            wow = ''
            if n >= 2:
                d_str, p_str = _delta(vals[-1], vals[-2] if len(vals) >= 2 else None)
                wow = f'<td class="num">{d_str}</td><td class="num">{p_str}</td>'
            trs += f'<tr><td>{plat_label[:2]} {mlabel}</td>{wow}{cells}<td class="note"></td></tr>'

    total_rows = sum(len(smm_metrics) for pk, _ in platform_configs if any(t.get(pk) for t in smm_trend))

    return f"""<section class="section page-break" id="smm-trend"><div class="section-head"><div><h2>SMM Trend — Full Sheet Metrics</h2><div class="sub">All metric names, period columns, and notes from the workbook are included here.</div></div><span class="pill">{total_rows} rows</span></div><div class="table-wrap"><table class="report-table"><tr><td colspan="{col_span}">Social Media Marketing — {n} Week Trend</td></tr><tr><th>Metric</th>{wow_h}{ph}<th>Notes</th></tr>{trs}</table></div></section>"""


# ---------------------------------------------------------------------------
# Ads (Meta + LinkedIn platform performance)
# ---------------------------------------------------------------------------
def _ads_section(ads):
    if not ads:
        return f"""<section class="section page-break" id="ads"><div class="section-head"><div><h2>Ads — Full Sheet Metrics</h2><div class="sub">No ad campaign data available for this period.</div></div></div></section>"""

    # Platform-level aggregation
    ti = sum(int(_g(c, 'impressions', 0) or 0) for c in ads)
    tc = sum(int(_g(c, 'clicks', 0) or 0) for c in ads)
    tl = sum(int(_g(c, 'leads', 0) or 0) for c in ads)
    ts = sum(float(_g(c, 'spend', 0) or 0) for c in ads)
    tr_ = sum(int(_g(c, 'reach', 0) or 0) for c in ads)
    ctr = (tc / ti * 100) if ti > 0 else 0
    cpl = (ts / tl) if tl > 0 else 0

    # Platform performance summary rows
    platform_rows = f"""<tr><td>Total Impressions</td><td class="num">{_f(ti or None)}</td></tr>
<tr><td>Total Clicks</td><td class="num">{_f(tc or None)}</td></tr>
<tr><td>Total Leads</td><td class="num">{_f(tl or None)}</td></tr>
<tr><td>CTR</td><td class="num">{f'{ctr:.2f}%' if ctr else '—'}</td></tr>
<tr><td>Total Reach</td><td class="num">{_f(tr_ or None)}</td></tr>
<tr><td>CPL</td><td class="num">{_f(cpl, cur=True) if cpl else '—'}</td></tr>
<tr><td>Total Spend</td><td class="num">{_f(ts, cur=True) if ts else '—'}</td></tr>"""

    # Campaign detail rows
    camp_rows = ''
    for c in ads:
        name = c.get('campaign_name', c.get('name', '—'))
        camp_rows += f"""<tr><td>{_esc(name)}</td><td class="num">{_f(_g(c,'impressions'))}</td><td class="num">{_f(_g(c,'clicks'))}</td><td class="num">{_f(_g(c,'ctr'), pct=True)}</td><td class="num">{_f(_g(c,'reach'))}</td><td class="num">{_f(_g(c,'leads'))}</td><td class="num">{_f(float(_g(c,'spend',0) or 0), cur=True)}</td><td class="num">{_f(float(_g(c,'cpl',0) or 0), cur=True)}</td></tr>"""

    return f"""<section class="section page-break" id="ads"><div class="section-head"><div><h2>Ads — Full Sheet Metrics</h2><div class="sub">Platform performance and campaign detail.</div></div><span class="pill">{len(ads)} campaigns</span></div>
<div class="table-wrap"><table class="report-table"><tr class="group"><td colspan="2">PLATFORM PERFORMANCE — ALL ICPs</td></tr><tr><th>Metric</th><th>Value</th></tr>{platform_rows}</table></div>

<div class="table-wrap" style="margin-top:14px"><table class="report-table"><tr class="group"><td colspan="8">CAMPAIGN PERFORMANCE</td></tr><tr><th>Campaign Name</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th>Reach</th><th>Leads</th><th>Spend</th><th>CPL</th></tr>{camp_rows}</table></div></section>"""


# ---------------------------------------------------------------------------
# Metrics Index
# ---------------------------------------------------------------------------
def _metrics_index():
    sections = [
        ('Performance Overview', [
            'Total Reach (all platforms)', 'Total Impressions (all platforms)',
            'Total Engagements', 'Avg. Engagement Rate (%)',
            'Organic Sessions (SEO)', 'Total Ad Impressions',
            'Total Ad Clicks', 'Overall Ad CTR (%)', 'Total Leads',
        ]),
        ('SEO Trend', [
            'Organic Sessions', 'Organic Users', 'Website Leads',
            'Avg. Session Duration (sec)', 'Bounce Rate',
            'Google Search Console Clicks', 'Google Search Console Impressions',
            'Avg. Position', 'Pages Indexed', 'Backlinks (total)', 'Domain Rating',
        ]),
        ('SMM Trend', [
            'Followers / Page Likes', 'New Followers (net)', 'Reach', 'Views',
            'Engagements (total)', 'Posts Published', 'Link Clicks',
            'Profile Visits / Page Views',
        ]),
        ('Ads', [
            'Meta Impressions', 'Meta Clicks', 'Meta Leads', 'Meta CTR',
            'Meta Reach', 'Meta CPL', 'Meta Spend',
            'LinkedIn Sends', 'LinkedIn Opens', 'LinkedIn Leads',
            'LinkedIn Open Rate', 'LinkedIn Clicks', 'LinkedIn CPL', 'LinkedIn Spend',
        ]),
    ]

    cards = ''
    for title, labels in sections:
        items = ''.join(f'<div><b>&middot;</b> {l}</div>' for l in labels)
        cards += f'<div class="card" style="margin-bottom:14px"><h3>{title}</h3><div class="metric-index">{items}</div></div>'

    return f"""<section class="section page-break" id="metrics-index"><div class="section-head"><div><h2>All Metrics Index</h2><div class="sub">Exact metric labels used in this report.</div></div></div>{cards}</section>"""
