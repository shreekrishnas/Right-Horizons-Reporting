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
:root{--ink:#172033;--muted:#64748b;--soft:#f6f8fb;--line:#e5e7eb;--brand:#165e83;--brand2:#0ea5a4;--warn:#b45309;--danger:#b91c1c;--good:#047857;--card:#ffffff;--lav:#eef2ff}*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#f3f6fb;color:var(--ink);line-height:1.45}.wrap{max-width:1360px;margin:0 auto;padding:28px}.hero{background:linear-gradient(135deg,#0f2b46,#165e83 52%,#0ea5a4);color:#fff;border-radius:24px;padding:28px;box-shadow:0 24px 70px rgba(15,43,70,.25);position:relative;overflow:hidden}.hero:after{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;background:rgba(255,255,255,.12);border-radius:50%}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:800;opacity:.85}.hero h1{font-size:36px;margin:8px 0 8px;line-height:1.08}.hero p{max-width:820px;margin:0;color:rgba(255,255,255,.86);font-size:15px}.hero-grid{display:grid;grid-template-columns:2fr 1fr;gap:18px;align-items:end}.period-card{position:relative;z-index:1;background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.22);border-radius:18px;padding:16px}.period-card b{display:block;font-size:20px}.period-card span{display:block;color:rgba(255,255,255,.75);font-size:12px;margin-top:4px}.nav{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}.nav a{background:#fff;border:1px solid var(--line);border-radius:999px;padding:10px 14px;color:#334155;text-decoration:none;font-weight:800;font-size:13px;box-shadow:0 8px 20px rgba(15,23,42,.05)}.nav a:hover{border-color:#165e83;color:#165e83}.section{margin:20px 0 34px}.section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;margin-bottom:12px}.section h2{font-size:24px;margin:0}.section .sub{color:var(--muted);font-size:13px}.card{background:var(--card);border:1px solid var(--line);border-radius:18px;box-shadow:0 12px 35px rgba(15,23,42,.07);padding:18px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.kpi{background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:0 8px 24px rgba(15,23,42,.05)}.kpi .label{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:900}.kpi .value{font-size:26px;font-weight:900;margin-top:6px}.kpi .meta{font-size:12px;color:var(--muted);margin-top:6px}.pill{display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;font-size:11px;font-weight:900;background:#eef2ff;color:#3730a3}.pill.good{background:#dcfce7;color:#166534}.pill.warn{background:#ffedd5;color:#9a3412}.pill.bad{background:#fee2e2;color:#991b1b}.grade{display:inline-block;width:32px;height:32px;line-height:32px;text-align:center;border-radius:8px;font-weight:900;font-size:16px;background:#eef2ff;color:#3730a3}.grade.A{background:#dcfce7;color:#166534}.grade.B{background:#d1fae5;color:#065f46}.grade.C{background:#ffedd5;color:#9a3412}.grade.D,.grade.F{background:#fee2e2;color:#991b1b}.channel-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:12px}.channel-card{background:#f8fafc;border:1px solid var(--line);border-radius:14px;padding:14px}.channel-card .ch-name{font-size:11px;text-transform:uppercase;letter-spacing:.08em;font-weight:900;color:var(--muted)}.channel-card .ch-grade{font-size:28px;font-weight:900;margin:4px 0}.channel-card .ch-trend{font-size:12px;color:var(--muted)}.channel-card .ch-note{font-size:12px;color:#334155;margin-top:6px;line-height:1.4}.next-steps{list-style:none;padding:0;margin:0}.next-steps li{display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--line)}.next-steps li:last-child{border-bottom:0}.ns-badge{min-width:48px;text-align:center;border-radius:6px;padding:3px 6px;font-size:10px;font-weight:900;text-transform:uppercase}.ns-badge.high{background:#fee2e2;color:#991b1b}.ns-badge.medium{background:#ffedd5;color:#9a3412}.ns-badge.low{background:#dcfce7;color:#166534}.ns-text .ns-title{font-weight:800;font-size:13px}.ns-text .ns-desc{font-size:12px;color:var(--muted);margin-top:2px}.summary-block{white-space:pre-line;background:#fff;border-left:5px solid #0ea5a4;border-radius:14px;border-top:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line);padding:16px;color:#334155}.summary-block ul{margin:6px 0;padding-left:20px}.summary-block li{margin:4px 0}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:16px;background:#fff}.report-table{border-collapse:collapse;width:100%;font-size:12px;min-width:920px}.report-table th,.report-table td{border-bottom:1px solid #eef2f7;border-right:1px solid #eef2f7;padding:8px 10px;vertical-align:top}.report-table th{background:#eff6ff;color:#0f2b46;text-align:left;font-weight:900;white-space:nowrap;position:sticky;top:0;z-index:2}.report-table td:first-child,.report-table th:first-child{position:sticky;left:0;background:#fff;z-index:1;min-width:240px;font-weight:800;color:#1e293b}.report-table th:first-child{background:#eff6ff;z-index:3}.report-table tr.group td{background:#f8fafc!important;color:#165e83;font-weight:900;text-transform:uppercase;letter-spacing:.04em}.report-table td.num{text-align:right;font-variant-numeric:tabular-nums}.report-table td.note{min-width:360px;color:#475569}.metric-index{columns:3;column-gap:28px}.metric-index div{break-inside:avoid;background:#fff;border:1px solid #eef2f7;border-radius:10px;padding:7px 9px;margin:0 0 8px;font-size:12px}.page-break{page-break-before:always}.tiny{font-size:11px;color:var(--muted)}.toolbar{display:flex;gap:10px;align-items:center;justify-content:flex-end;margin:14px 0}.btn{border:0;background:#165e83;color:#fff;border-radius:999px;padding:10px 14px;font-weight:900;cursor:pointer}.btn.secondary{background:#fff;color:#165e83;border:1px solid #bae6fd}.confidence-bar{height:8px;border-radius:999px;background:var(--line);margin-top:6px;overflow:hidden}.confidence-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#165e83,#0ea5a4)}@media(max-width:900px){.hero-grid,.cards,.channel-grid{grid-template-columns:1fr}.metric-index{columns:1}.wrap{padding:16px}.hero h1{font-size:28px}}.rr-footer{margin-top:40px;padding:24px 28px;border-top:2px solid var(--line);text-align:center;color:var(--muted);font-size:12px}.rr-footer p{margin:6px 0}.rr-mode-badge{display:inline-block;background:linear-gradient(135deg,#165e83,#0ea5a4);color:#fff;padding:3px 10px;border-radius:999px;font-weight:700;font-size:11px;letter-spacing:.04em}.rr-disclaimer{font-size:10px;color:#94a3b8;max-width:800px;margin:8px auto 0;line-height:1.5}@media print{body{background:#fff}.wrap{max-width:none;padding:0}.nav,.toolbar{display:none}.card,.kpi,.hero,.channel-card{box-shadow:none}.table-wrap{overflow:visible}.report-table{font-size:9px;min-width:0}.report-table th,.report-table td{padding:5px}.page-break{page-break-before:always}.rr-footer{margin-top:20px}}
"""


def _esc(s):
    """HTML-escape a string."""
    if not isinstance(s, str):
        return str(s) if s is not None else '—'
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')


def generate_html_report(data: dict, start: str, end: str, domain: str, report_mode: str = "client") -> str:
    data = data or {}
    ts = datetime.now(_IST).strftime('%d %b %Y, %I:%M %p IST')

    gsc = data.get('gsc') or {}
    ga4 = data.get('ga4') or {}
    fb = data.get('social_fb') or {}
    ig = data.get('social_ig') or {}
    ads = data.get('meta_ads') or []
    smm_trend = data.get('social_trend') or []
    seo_trend = data.get('seo_trend') or []
    ai_summary = data.get('ai_summary') or data.get('executive_summary') or {}

    mode = report_mode.lower().strip()
    MODE_LABELS = {
        'client': 'Client Report',
        'internal': 'Internal Report',
        'leadership': 'Leadership Summary',
        'raw': 'Raw Data Export',
    }
    mode_label = MODE_LABELS.get(mode, 'Client Report')

    hero = _hero(domain, start, end, mode_label)
    toolbar = _toolbar()

    if mode == 'leadership':
        nav = _nav_leadership()
        exec_summary = _exec_summary_section(ai_summary, gsc, ga4, fb, ig, ads)
        kpi_snapshot = _kpi_snapshot(gsc, ga4, fb, ig, ads, seo_trend, smm_trend)
        body = f"{hero}\n{toolbar}\n{nav}\n{exec_summary}\n{kpi_snapshot}"

    elif mode == 'internal':
        nav = _nav()
        exec_summary = _exec_summary_section(ai_summary, gsc, ga4, fb, ig, ads)
        kpi_snapshot = _kpi_snapshot(gsc, ga4, fb, ig, ads, seo_trend, smm_trend)
        perf_overview = _perf_overview(gsc, ga4, fb, ig, ads)
        seo_section = _seo_trend_section(seo_trend, gsc, ga4)
        top_content = _top_content_section(gsc, ga4)
        smm_section = _smm_trend_section(smm_trend)
        ads_section = _ads_section(ads)
        metrics_index = _metrics_index()
        notes_section = _internal_notes_section()
        raw_dump = _raw_data_section(gsc, ga4, fb, ig, ads)
        body = f"{hero}\n{toolbar}\n{nav}\n{exec_summary}\n{kpi_snapshot}\n{perf_overview}\n{seo_section}\n{top_content}\n{smm_section}\n{ads_section}\n{raw_dump}\n{notes_section}\n{metrics_index}"

    elif mode == 'raw':
        nav = _nav_raw()
        perf_overview = _perf_overview(gsc, ga4, fb, ig, ads)
        seo_section = _seo_trend_section(seo_trend, gsc, ga4)
        top_content = _top_content_section(gsc, ga4)
        smm_section = _smm_trend_section(smm_trend)
        ads_section = _ads_section(ads)
        raw_dump = _raw_data_section(gsc, ga4, fb, ig, ads)
        metrics_index = _metrics_index()
        body = f"{hero}\n{toolbar}\n{nav}\n{perf_overview}\n{seo_section}\n{top_content}\n{smm_section}\n{ads_section}\n{raw_dump}\n{metrics_index}"

    else:
        # client (default)
        nav = _nav()
        exec_summary = _exec_summary_section(ai_summary, gsc, ga4, fb, ig, ads)
        kpi_snapshot = _kpi_snapshot(gsc, ga4, fb, ig, ads, seo_trend, smm_trend)
        perf_overview = _perf_overview(gsc, ga4, fb, ig, ads)
        seo_section = _seo_trend_section(seo_trend, gsc, ga4)
        top_content = _top_content_section(gsc, ga4)
        smm_section = _smm_trend_section(smm_trend)
        ads_section = _ads_section(ads)
        metrics_index = _metrics_index()
        body = f"{hero}\n{toolbar}\n{nav}\n{exec_summary}\n{kpi_snapshot}\n{perf_overview}\n{seo_section}\n{top_content}\n{smm_section}\n{ads_section}\n{metrics_index}"

    footer = (
        '<footer class="rr-footer">'
        f'<p>Generated on {ts} &middot; <span class="rr-mode-badge">{_esc(mode_label)}</span></p>'
        '<p class="rr-disclaimer">This report is auto-generated from live API data. '
        'SEBI Registration: INA000013880 (Investment Adviser), INP000007508 (PMS), IN/AIF2/24-25/1595 (AIF). '
        'Past performance is not indicative of future results.</p>'
        '</footer>'
    )

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{_esc(domain)} — {_esc(mode_label)}</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet"><style>
{CSS}</style></head><body><div class="wrap">
{body}
{footer}
</div></body></html>"""


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------
def _hero(domain, start, end, mode_label='Client Report'):
    MODE_SUBTITLES = {
        'Client Report': 'Clean, presentation-ready report with KPIs, trends, and executive summary.',
        'Internal Report': 'Full diagnostic report with raw data, internal notes, and all metric breakdowns.',
        'Leadership Summary': 'One-page executive summary — wins, concerns, KPIs, and recommended focus areas.',
        'Raw Data Export': 'All available data tables for deeper analysis and custom reporting.',
    }
    subtitle = MODE_SUBTITLES.get(mode_label, MODE_SUBTITLES['Client Report'])
    return f"""<div class="hero"><div class="hero-grid"><div><div class="eyebrow">Reporting Room &middot; {_esc(domain)}</div><h1>{_esc(mode_label)}</h1><p>{subtitle}</p></div><div class="period-card"><span>Reporting period</span><b>{_esc(start)} &ndash; {_esc(end)}</b><span>Generated for {_esc(domain)}</span></div></div></div>"""


# ---------------------------------------------------------------------------
# Toolbar
# ---------------------------------------------------------------------------
def _toolbar():
    return """<div class="toolbar"><button class="btn" onclick="window.print()">Print / Save PDF</button></div>"""


# ---------------------------------------------------------------------------
# Navigation anchors
# ---------------------------------------------------------------------------
def _nav():
    return """<div class="nav"><a href="#summary">Executive Summary</a><a href="#quick-kpis">KPI Snapshot</a><a href="#performance-overview">Performance Overview</a><a href="#seo-trend">SEO Trend</a><a href="#smm-trend">SMM Trend</a><a href="#ads">Ads</a><a href="#top-content">Top Content</a><a href="#metrics-index">All Metrics Index</a></div>"""


# ---------------------------------------------------------------------------
# Executive Summary with pill badges
# ---------------------------------------------------------------------------
def _fmt_val(val):
    if isinstance(val, list):
        return '<ul>' + ''.join(f'<li>{_esc(str(item))}</li>' for item in val) + '</ul>'
    if isinstance(val, dict):
        return '<ul>' + ''.join(f'<li><b>{_esc(str(k))}:</b> {_esc(str(v))}</li>' for k, v in val.items()) + '</ul>'
    return _esc(str(val)) if val and val != '—' else '—'


def _exec_summary_section(ai_summary, gsc, ga4, fb, ig, ads):
    if not ai_summary:
        return f"""<section class="section" id="summary"><div class="section-head"><div><h2>Executive Summary</h2><div class="sub">Generate an AI summary from the Reporting Room to populate this section.</div></div></div>
<div class="card"><p style="color:var(--muted);font-style:italic">No AI summary available. Click "Generate AI Summary" in the Reporting Room before exporting.</p></div></section>"""

    # Core narrative
    exec_s = _g(ai_summary, 'executive_summary') or ''
    headline = _g(ai_summary, 'headline') or _g(ai_summary, 'main_win') or exec_s or '—'
    working = _g(ai_summary, 'what_improved') or _g(ai_summary, 'whats_working') or _g(ai_summary, 'working') or '—'
    stable = _g(ai_summary, 'what_stable') or ''
    dropped = _g(ai_summary, 'what_dropped') or _g(ai_summary, 'needs_attention') or '—'
    concern = _g(ai_summary, 'main_concern') or ''
    opportunity = _g(ai_summary, 'key_opportunity') or ''
    actions = _g(ai_summary, 'next_steps') or _g(ai_summary, 'recommended_actions') or _g(ai_summary, 'actions') or '—'
    focus = _g(ai_summary, 'recommended_focus') or ''
    confidence = _g(ai_summary, 'confidence_score') or 0
    risks = _g(ai_summary, 'risks') or []
    channel_grades = _g(ai_summary, 'channel_grades') or {}

    html = '<section class="section" id="summary"><div class="section-head"><div><h2>Executive Summary</h2><div class="sub">AI-generated analysis for the reporting period.</div></div>'
    if confidence:
        html += f'<div><span class="pill">Health Score: {confidence}/100</span><div class="confidence-bar"><div class="confidence-fill" style="width:{min(int(confidence),100)}%"></div></div></div>'
    html += '</div>'

    # Executive headline
    if exec_s and exec_s != headline:
        html += f'<div class="card" style="margin-bottom:12px"><span class="pill">Boardroom Summary</span><div class="summary-block" style="margin-top:12px">{_esc(str(exec_s))}</div></div>'

    html += f'<div class="card" style="margin-bottom:12px"><span class="pill good">What Improved</span><div class="summary-block" style="margin-top:12px">{_fmt_val(working)}</div></div>'

    if stable:
        html += f'<div class="card" style="margin-bottom:12px"><span class="pill">What\'s Stable</span><div class="summary-block" style="margin-top:12px">{_fmt_val(stable)}</div></div>'

    html += f'<div class="card" style="margin-bottom:12px"><span class="pill warn">What Declined</span><div class="summary-block" style="margin-top:12px">{_fmt_val(dropped)}</div></div>'

    if concern:
        html += f'<div class="card" style="margin-bottom:12px"><span class="pill bad">Main Concern</span><div class="summary-block" style="margin-top:12px">{_esc(str(concern))}</div></div>'

    if opportunity:
        html += f'<div class="card" style="margin-bottom:12px"><span class="pill" style="background:#f0fdf4;color:#166534">Key Opportunity</span><div class="summary-block" style="margin-top:12px">{_esc(str(opportunity))}</div></div>'

    # Channel grades
    if channel_grades and isinstance(channel_grades, dict):
        grade_cards = ''
        grade_order = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'F': 4}
        for ch, info in channel_grades.items():
            if not isinstance(info, dict):
                continue
            g = str(_g(info, 'grade', '—'))
            trend = _g(info, 'trend', '')
            note = _g(info, 'one_liner', '')
            trend_arrow = {'improving': '↑', 'stable': '→', 'declining': '↓'}.get(str(trend).lower(), '')
            grade_cards += f'<div class="channel-card"><div class="ch-name">{_esc(ch.upper())}</div><div class="ch-grade"><span class="grade {g}">{g}</span> <span style="font-size:16px;color:var(--muted)">{trend_arrow} {_esc(str(trend))}</span></div><div class="ch-note">{_esc(str(note))}</div></div>'
        if grade_cards:
            html += f'<div class="card" style="margin-bottom:12px"><span class="pill">Channel Grades</span><div class="channel-grid" style="margin-top:12px">{grade_cards}</div></div>'

    # Next steps
    if actions and actions != '—':
        if isinstance(actions, list):
            items_html = ''
            for step in actions:
                if isinstance(step, dict):
                    title = _esc(str(_g(step, 'title', '')))
                    desc = _esc(str(_g(step, 'description', '') or _g(step, 'expected_impact', '')))
                    priority = str(_g(step, 'priority', 'medium')).lower()
                    channel = _g(step, 'channel', '')
                    ch_badge = f'<span class="pill" style="margin-left:6px;font-size:10px">{_esc(str(channel))}</span>' if channel else ''
                    items_html += f'<li><span class="ns-badge {priority}">{priority}</span><div class="ns-text"><div class="ns-title">{title}{ch_badge}</div><div class="ns-desc">{desc}</div></div></li>'
                else:
                    items_html += f'<li><div class="ns-text"><div class="ns-title">{_esc(str(step))}</div></div></li>'
            html += f'<div class="card" style="margin-bottom:12px"><span class="pill bad">Recommended Next Steps</span><ul class="next-steps" style="margin-top:12px">{items_html}</ul></div>'
        else:
            html += f'<div class="card" style="margin-bottom:12px"><span class="pill bad">Recommended Actions</span><div class="summary-block" style="margin-top:12px">{_fmt_val(actions)}</div></div>'

    if focus:
        html += f'<div class="card" style="margin-bottom:12px"><span class="pill">Recommended Focus Next Period</span><div class="summary-block" style="margin-top:12px">{_esc(str(focus))}</div></div>'

    # Risks
    if risks and isinstance(risks, list):
        risk_rows = ''.join(
            f'<tr><td>{_esc(str(_g(r,"risk","") if isinstance(r,dict) else r))}</td><td class="note">{_esc(str(_g(r,"mitigation","") if isinstance(r,dict) else ""))}</td></tr>'
            for r in risks
        )
        html += f'<div class="card" style="margin-bottom:12px"><span class="pill warn">Risks to Monitor</span><div class="table-wrap" style="margin-top:12px"><table class="report-table"><tr><th>Risk</th><th>Mitigation</th></tr>{risk_rows}</table></div></div>'

    html += '</section>'
    return html


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
    ig_f = _g(ig, 'followers', 0) or 0
    fb_f = _g(fb, 'followers', 0) or _g(fb, 'page_likes', 0) or 0
    ig_nf = _g(ig, 'new_followers', 0) or 0
    fb_nf = _g(fb, 'new_followers', 0) or 0
    ig_vv = _g(ig, 'video_views', 0) or 0
    fb_vv = _g(fb, 'video_views', 0) or 0
    ig_lc = _g(ig, 'link_clicks', 0) or 0
    fb_lc = _g(fb, 'link_clicks', 0) or 0
    ig_ss = _g(ig, 'saves_shares', 0) or 0
    fb_ss = _g(fb, 'saves_shares', 0) or 0
    ig_pp = _g(ig, 'posts_published', 0) or 0
    fb_pp = _g(fb, 'posts_published', 0) or 0
    ig_er = _g(ig, 'engagement_rate', 0) or 0
    fb_er = _g(fb, 'engagement_rate', 0) or 0

    gsc_cl = _g(gsc, 'clicks', 0) or 0
    gsc_im = _g(gsc, 'impressions', 0) or 0
    gsc_ct = _g(gsc, 'ctr', 0) or 0
    gsc_po = _g(gsc, 'position', 0) or 0
    org = _g(ga4, 'organic_sessions', 0) or _g(ga4, 'sessions', 0) or 0
    org_u = _g(ga4, 'organic_users', 0) or _g(ga4, 'users', 0) or 0
    leads = _g(ga4, 'leads', 0) or 0
    bounce = _g(ga4, 'bounce_rate', 0) or 0
    dur = _g(ga4, 'avg_session_duration', 0) or 0

    ai = sum(int(_g(c, 'impressions', 0) or 0) for c in ads)
    ac = sum(int(_g(c, 'clicks', 0) or 0) for c in ads)
    al = sum(int(_g(c, 'leads', 0) or 0) for c in ads)
    asp = sum(float(_g(c, 'spend', 0) or 0) for c in ads)
    ar = sum(int(_g(c, 'reach', 0) or 0) for c in ads)

    total_reach = ig_r + fb_r
    total_eng = ig_e + fb_e
    eng_rate = (total_eng / total_reach * 100) if total_reach > 0 else 0
    ctr = (ac / ai * 100) if ai > 0 else 0
    cpl = (asp / al) if al > 0 else 0

    def _r(label, val, indent=False):
        prefix = '&nbsp;&nbsp;&nbsp;' if indent else ''
        return f'<tr><td>{prefix}{label}</td><td class="num">{val}</td></tr>'

    trs = (
        '<tr class="group"><td colspan="2">SOCIAL MEDIA — COMBINED</td></tr>'
        + _r('Total Reach (IG + FB)', _f(total_reach or None))
        + _r('Total Engagements (IG + FB)', _f(total_eng or None))
        + _r('Avg. Engagement Rate', f"{eng_rate:.2f}%" if eng_rate else '—')
        + _r('Total Video Views', _f((ig_vv + fb_vv) or None))
        + _r('Total New Followers', _f((ig_nf + fb_nf) or None))
        + _r('Total Posts Published', _f((ig_pp + fb_pp) or None))
        + _r('Total Link Clicks', _f((ig_lc + fb_lc) or None))
        + _r('Total Saves / Shares', _f((ig_ss + fb_ss) or None))
    )
    if ig:
        trs += (
            '<tr class="group"><td colspan="2">INSTAGRAM</td></tr>'
            + _r('Followers', _f(ig_f or None))
            + _r('New Followers (net)', _f(ig_nf or None))
            + _r('Reach', _f(ig_r or None))
            + _r('Impressions / Views', _f(ig_v or None))
            + _r('Engagements', _f(ig_e or None))
            + _r('Engagement Rate', f"{ig_er:.2f}%" if ig_er else '—')
            + _r('Video Views', _f(ig_vv or None))
            + _r('Link Clicks', _f(ig_lc or None))
            + _r('Saves / Shares', _f(ig_ss or None))
            + _r('Posts Published', _f(ig_pp or None))
        )
    if fb:
        trs += (
            '<tr class="group"><td colspan="2">FACEBOOK</td></tr>'
            + _r('Page Likes / Followers', _f(fb_f or None))
            + _r('New Followers (net)', _f(fb_nf or None))
            + _r('Reach (Unique Impressions)', _f(fb_r or None))
            + _r('Views (Page Views)', _f(fb_v or None))
            + _r('Engagements', _f(fb_e or None))
            + _r('Engagement Rate', f"{fb_er:.2f}%" if fb_er else '—')
            + _r('Video Views', _f(fb_vv or None))
            + _r('Link Clicks', _f(fb_lc or None))
            + _r('Saves / Shares', _f(fb_ss or None))
            + _r('Posts Published', _f(fb_pp or None))
        )
    if gsc or ga4:
        trs += (
            '<tr class="group"><td colspan="2">SEO / ORGANIC SEARCH</td></tr>'
            + _r('GSC Clicks', _f(gsc_cl or None))
            + _r('GSC Impressions', _f(gsc_im or None))
            + _r('GSC CTR', f"{float(gsc_ct)*100:.2f}%" if gsc_ct else '—')
            + _r('Avg. Position', _f(gsc_po or None))
            + _r('Organic Sessions', _f(org or None))
            + _r('Organic Users', _f(org_u or None))
            + _r('Bounce Rate', f"{float(bounce):.2f}%" if bounce else '—')
            + _r('Avg. Session Duration (sec)', _f(int(dur) if dur else None))
            + _r('Website Leads', _f(leads or None))
        )
    if ads:
        trs += (
            '<tr class="group"><td colspan="2">META ADS</td></tr>'
            + _r('Ad Impressions', _f(ai or None))
            + _r('Ad Clicks', _f(ac or None))
            + _r('Ad Reach', _f(ar or None))
            + _r('CTR', f"{ctr:.2f}%" if ctr else '—')
            + _r('Total Leads', _f(al or None))
            + _r('Total Spend', _f(asp, cur=True) if asp else '—')
            + _r('CPL', _f(cpl, cur=True) if cpl else '—')
        )

    return f"""<section class="section page-break" id="performance-overview"><div class="section-head"><div><h2>Performance Overview — All Channels</h2><div class="sub">Channel-by-channel breakdown for the reporting period.</div></div></div><div class="table-wrap"><table class="report-table"><tr><th>Metric</th><th>This Period</th></tr>{trs}</table></div></section>"""


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
        ('Impressions / Views', 'views'),
        ('Engagements (total)', 'engagements'),
        ('Engagement Rate (%)', 'engagement_rate'),
        ('Posts Published', 'posts'),
        ('Stories / Reels', 'reels_stories'),
        ('Video Views', 'video_views'),
        ('Link Clicks', 'link_clicks'),
        ('Saves / Shares', 'saves_shares'),
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
            is_rate = mkey == 'engagement_rate'
            cells = ''.join(f'<td class="num">{(f"{float(v):.2f}%" if v else "—") if is_rate else _f(v)}</td>' for v in vals)
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

    active_ads = [c for c in ads if int(_g(c, 'impressions', 0) or 0) > 0 or float(_g(c, 'spend', 0) or 0) > 0]

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
    for c in active_ads:
        name = c.get('campaign_name', c.get('name', '—'))
        camp_rows += f"""<tr><td>{_esc(name)}</td><td class="num">{_f(_g(c,'impressions'))}</td><td class="num">{_f(_g(c,'clicks'))}</td><td class="num">{_f(_g(c,'ctr'), pct=True)}</td><td class="num">{_f(_g(c,'reach'))}</td><td class="num">{_f(_g(c,'leads'))}</td><td class="num">{_f(float(_g(c,'spend',0) or 0), cur=True)}</td><td class="num">{_f(float(_g(c,'cpl',0) or 0), cur=True)}</td></tr>"""

    return f"""<section class="section page-break" id="ads"><div class="section-head"><div><h2>Ads — Full Sheet Metrics</h2><div class="sub">Platform performance and campaign detail.</div></div><span class="pill">{len(active_ads)} campaigns</span></div>
<div class="table-wrap"><table class="report-table"><tr class="group"><td colspan="2">PLATFORM PERFORMANCE — ALL ICPs</td></tr><tr><th>Metric</th><th>Value</th></tr>{platform_rows}</table></div>

<div class="table-wrap" style="margin-top:14px"><table class="report-table"><tr class="group"><td colspan="8">CAMPAIGN PERFORMANCE</td></tr><tr><th>Campaign Name</th><th>Impressions</th><th>Clicks</th><th>CTR</th><th>Reach</th><th>Leads</th><th>Spend</th><th>CPL</th></tr>{camp_rows}</table></div></section>"""


# ---------------------------------------------------------------------------
# Top Content — GSC queries, top pages, GA4 landing pages
# ---------------------------------------------------------------------------
def _top_content_section(gsc, ga4):
    queries = _g(gsc, 'queries') or []
    pages = _g(gsc, 'pages') or []
    ga4_pages = _g(ga4, 'pages') or []
    sources = _g(ga4, 'sources') or []

    if not any([queries, pages, ga4_pages, sources]):
        return ''

    html = '<section class="section page-break" id="top-content"><div class="section-head"><div><h2>Top Content &amp; Traffic Sources</h2><div class="sub">Best-performing keywords, pages, and traffic sources for the period.</div></div></div>'

    def _ctr(val):
        try:
            return f"{float(val)*100:.2f}%" if val else '—'
        except Exception:
            return '—'

    def _br(val):
        try:
            return f"{float(val)*100:.1f}%" if val else '—'
        except Exception:
            return '—'

    if queries:
        q_rows = ''
        for q in queries[:20]:
            q_rows += (f'<tr><td>{_esc(str(q.get("query","—")))}</td>'
                       f'<td class="num">{_f(q.get("clicks"))}</td>'
                       f'<td class="num">{_f(q.get("impressions"))}</td>'
                       f'<td class="num">{_ctr(q.get("ctr"))}</td>'
                       f'<td class="num">{_f(q.get("position"))}</td></tr>')
        html += f'<div class="table-wrap" style="margin-bottom:14px"><table class="report-table"><tr class="group"><td colspan="5">TOP SEARCH QUERIES (Google Search Console)</td></tr><tr><th>Query</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Avg. Position</th></tr>{q_rows}</table></div>'

    if pages:
        p_rows = ''
        for p in pages[:20]:
            p_rows += (f'<tr><td style="word-break:break-all">{_esc(str(p.get("page","—")))}</td>'
                       f'<td class="num">{_f(p.get("clicks"))}</td>'
                       f'<td class="num">{_f(p.get("impressions"))}</td>'
                       f'<td class="num">{_ctr(p.get("ctr"))}</td>'
                       f'<td class="num">{_f(p.get("position"))}</td></tr>')
        html += f'<div class="table-wrap" style="margin-bottom:14px"><table class="report-table"><tr class="group"><td colspan="5">TOP PAGES (Google Search Console)</td></tr><tr><th>Page URL</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Avg. Position</th></tr>{p_rows}</table></div>'

    if ga4_pages:
        gp_rows = ''
        for p in ga4_pages[:20]:
            gp_rows += (f'<tr><td style="word-break:break-all">{_esc(str(p.get("page","") or p.get("pagePath","—")))}</td>'
                        f'<td class="num">{_f(p.get("sessions") or p.get("screenPageViews"))}</td>'
                        f'<td class="num">{_f(p.get("users"))}</td>'
                        f'<td class="num">{_br(p.get("bounceRate"))}</td></tr>')
        html += f'<div class="table-wrap" style="margin-bottom:14px"><table class="report-table"><tr class="group"><td colspan="4">TOP PAGES (Google Analytics — GA4)</td></tr><tr><th>Page</th><th>Sessions / Views</th><th>Users</th><th>Bounce Rate</th></tr>{gp_rows}</table></div>'

    if sources:
        src_rows = ''
        for s in sources[:15]:
            src_rows += (f'<tr><td>{_esc(str(s.get("source","") or s.get("sessionSource","—")))}</td>'
                         f'<td class="num">{_f(s.get("sessions"))}</td>'
                         f'<td class="num">{_f(s.get("users"))}</td></tr>')
        html += f'<div class="table-wrap" style="margin-bottom:14px"><table class="report-table"><tr class="group"><td colspan="3">TRAFFIC SOURCES (Google Analytics)</td></tr><tr><th>Source / Medium</th><th>Sessions</th><th>Users</th></tr>{src_rows}</table></div>'

    html += '</section>'
    return html


# ---------------------------------------------------------------------------
# Navigation variants
# ---------------------------------------------------------------------------
def _nav_leadership():
    return """<div class="nav"><a href="#summary">Executive Summary</a><a href="#quick-kpis">KPI Snapshot</a></div>"""


def _nav_raw():
    return """<div class="nav"><a href="#performance-overview">Performance Overview</a><a href="#seo-trend">SEO Trend</a><a href="#smm-trend">SMM Trend</a><a href="#ads">Ads</a><a href="#raw-data">Raw Data</a><a href="#metrics-index">Metrics Index</a></div>"""


# ---------------------------------------------------------------------------
# Internal notes section (placeholder for internal mode)
# ---------------------------------------------------------------------------
def _internal_notes_section():
    return """<section class="section page-break" id="internal-notes"><div class="section-head"><div><h2>Internal Notes</h2><div class="sub">Space for team annotations, context, and action items.</div></div></div>
<div class="card"><div class="summary-block" style="min-height:120px;color:var(--muted);font-style:italic">Add internal notes, team comments, and action items here after downloading. This section is not included in client-facing reports.</div></div></section>"""


# ---------------------------------------------------------------------------
# Raw data dump section
# ---------------------------------------------------------------------------
def _raw_data_section(gsc, ga4, fb, ig, ads):
    rows = ''
    for section_name, section_data in [('GSC', gsc), ('GA4', ga4), ('Social — Facebook', fb), ('Social — Instagram', ig)]:
        if not section_data or not isinstance(section_data, dict):
            continue
        rows += f'<tr class="group"><td colspan="2">{section_name}</td></tr>'
        for k, v in section_data.items():
            if isinstance(v, (list, dict)):
                continue
            rows += f'<tr><td>{_esc(str(k))}</td><td class="num">{_f(v)}</td></tr>'

    if not rows:
        return ''

    return f"""<section class="section page-break" id="raw-data"><div class="section-head"><div><h2>Raw Data Dump</h2><div class="sub">All individual metric values from each data source.</div></div></div><div class="table-wrap"><table class="report-table"><tr><th>Metric</th><th>Value</th></tr>{rows}</table></div></section>"""


# ---------------------------------------------------------------------------
# Metrics Index
# ---------------------------------------------------------------------------
def _metrics_index():
    sections = [
        ('Performance Overview — Social', [
            'Total Reach (IG + FB)', 'Total Engagements', 'Avg. Engagement Rate',
            'Total Video Views', 'Total New Followers', 'Total Posts Published',
            'Total Link Clicks', 'Total Saves / Shares',
        ]),
        ('Performance Overview — Instagram', [
            'Followers', 'New Followers (net)', 'Reach', 'Impressions / Views',
            'Engagements', 'Engagement Rate', 'Video Views',
            'Link Clicks', 'Saves / Shares', 'Posts Published',
        ]),
        ('Performance Overview — Facebook', [
            'Page Likes / Followers', 'New Followers (net)', 'Reach (Unique Impressions)',
            'Views (Page Views)', 'Engagements', 'Engagement Rate', 'Video Views',
            'Link Clicks', 'Saves / Shares', 'Posts Published',
        ]),
        ('Performance Overview — SEO', [
            'GSC Clicks', 'GSC Impressions', 'GSC CTR', 'Avg. Position',
            'Organic Sessions', 'Organic Users', 'Bounce Rate',
            'Avg. Session Duration (sec)', 'Website Leads',
        ]),
        ('Performance Overview — Ads', [
            'Ad Impressions', 'Ad Clicks', 'Ad Reach', 'CTR',
            'Total Leads', 'Total Spend', 'CPL',
        ]),
        ('SEO Trend (Weekly)', [
            'Organic Sessions', 'Organic Users', 'Website Leads',
            'Avg. Session Duration (sec)', 'Bounce Rate',
            'GSC Clicks', 'GSC Impressions', 'Avg. Position',
        ]),
        ('SMM Trend (Weekly)', [
            'Followers / Page Likes', 'New Followers (net)', 'Reach',
            'Impressions / Views', 'Engagements (total)', 'Engagement Rate (%)',
            'Posts Published', 'Stories / Reels', 'Video Views',
            'Link Clicks', 'Saves / Shares', 'Profile Visits / Page Views',
        ]),
        ('Meta Ads', [
            'Impressions', 'Clicks', 'Leads', 'CTR', 'Reach', 'CPL', 'Spend',
        ]),
        ('Top Content', [
            'Top Search Queries (GSC)', 'Top Pages by Clicks (GSC)',
            'Top Pages by Sessions (GA4)', 'Traffic Sources (GA4)',
        ]),
    ]

    cards = ''
    for title, labels in sections:
        items = ''.join(f'<div><b>&middot;</b> {l}</div>' for l in labels)
        cards += f'<div class="card" style="margin-bottom:14px"><h3>{title}</h3><div class="metric-index">{items}</div></div>'

    return f"""<section class="section page-break" id="metrics-index"><div class="section-head"><div><h2>All Metrics Index</h2><div class="sub">Exact metric labels used in this report.</div></div></div>{cards}</section>"""
