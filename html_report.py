"""
Premium HTML marketing report — matches the Excel template exactly:
Sheet 1: Performance Overview (This Week summary + key wins/notes)
Sheet 2: SEO Trend (5-week: Traffic, Engagement, Search Console, Indexing)
Sheet 3: SMM Trend (5-week: Instagram, Facebook, LinkedIn)
Sheet 4: Ads (Platform Performance + Campaign detail by ICP)
Sheet 5: Executive Summary (data-driven)
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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{domain} — Marketing Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>

{_header(domain, start, end)}
{_perf_overview(gsc, ga4, fb, ig, ads)}
{_seo_sheet(seo_trend, gsc, ga4)}
{_smm_sheet(smm_trend)}
{_ads_sheet(ads)}
{_exec_summary(gsc, ga4, fb, ig, ads)}

<footer class="footer">
  <span>Generated {ts}</span>
  <span>Right Horizons — Confidential</span>
</footer>
</body></html>"""


def _header(domain, start, end):
    return f"""
<header class="hdr">
  <div class="hdr-l">
    <div class="hdr-logo">RH</div>
    <div><div class="hdr-t">Marketing Weekly Report — Performance Overview</div>
    <div class="hdr-sub">{domain}</div></div>
  </div>
  <div class="hdr-r">
    <div class="hdr-badge">Reporting Period: {start} to {end}</div>
    <div class="hdr-dept">Department: Marketing</div>
  </div>
</header>"""


def _perf_overview(gsc, ga4, fb, ig, ads):
    ig_r = _g(ig, 'reach', 0) or 0
    fb_r = _g(fb, 'reach', 0) or 0
    ig_e = _g(ig, 'engagements', 0) or 0
    fb_e = _g(fb, 'engagements', 0) or 0
    gsc_i = _g(gsc, 'impressions', 0) or 0
    ig_v = _g(ig, 'views', 0) or 0
    fb_v = _g(fb, 'views', 0) or 0
    org = _g(ga4, 'organic_sessions', 0) or 0
    ai = sum(int(_g(c, 'impressions', 0) or 0) for c in ads)
    ac = sum(int(_g(c, 'clicks', 0) or 0) for c in ads)
    al = sum(int(_g(c, 'leads', 0) or 0) for c in ads)

    total_reach = ig_r + fb_r
    total_imp = gsc_i + ig_v + fb_v
    total_eng = ig_e + fb_e
    eng_rate = (total_eng / total_reach * 100) if total_reach > 0 else 0
    ctr = (ac / ai * 100) if ai > 0 else 0

    rows = [
        ('Total Reach (all platforms)', _f(total_reach or None), '#7C3AED'),
        ('Total Impressions (all platforms)', _f(total_imp or None), '#0EA5E9'),
        ('Total Engagements', _f(total_eng or None), '#10B981'),
        ('Avg. Engagement Rate (%)', _f(eng_rate, pct=True) if eng_rate else '—', '#F59E0B'),
        ('Organic Sessions (SEO)', _f(org or None), '#6366F1'),
        ('Total Ad Impressions', _f(ai or None), '#EF4444'),
        ('Total Ad Clicks', _f(ac or None), '#EC4899'),
        ('Overall Ad CTR (%)', _f(ctr, pct=True) if ctr else '—', '#F97316'),
        ('Total Leads', _f(al or None), '#14B8A6'),
    ]

    cards = ''.join(f"""
    <div class="kpi">
      <div class="kpi-bar" style="background:{c}"></div>
      <div class="kpi-v">{v}</div>
      <div class="kpi-l">{l}</div>
    </div>""" for l, v, c in rows)

    return f"""
<section class="sheet">
  <div class="sh-t"><span class="sh-i">📊</span> Performance Summary — All Channels</div>
  <div class="kpi-grid">{cards}</div>
</section>"""


def _seo_sheet(seo_trend, gsc, ga4):
    if not seo_trend and not gsc and not ga4:
        return ''

    periods = [t.get('period', '') for t in seo_trend] if seo_trend else []
    n = len(periods)

    def _trend_section(title, accent, metrics_def):
        if not seo_trend:
            rows = ''.join(f'<tr><td class="mn">{label}</td><td class="mv">{_f(val, pct=is_pct)}</td></tr>'
                          for label, val, is_pct in metrics_def)
            return f"""
            <div class="sec-h {accent}">{title}</div>
            <table class="dt"><thead><tr><th class="tl">Metric</th><th class="tr">Value</th></tr></thead>
            <tbody>{rows}</tbody></table>"""

        ph = ''.join(f'<th class="tc">{p}</th>' for p in periods)
        wow_h = '<th class="tc">WoW Δ</th><th class="tc">WoW %</th>' if n >= 2 else ''
        rows = ''
        for label, key, is_pct in metrics_def:
            vals = [t.get(key, 0) or 0 for t in seo_trend]
            d_str, p_str = _delta(vals[-1] if vals else 0, vals[-2] if len(vals) >= 2 else 0)
            cells = ''.join(f'<td class="mv">{_f(v, pct=is_pct)}</td>' for v in vals)
            wow = ''
            if n >= 2:
                d_cls = 'delta-up' if d_str.startswith('+') else ('delta-down' if d_str.startswith('-') else '')
                wow = f'<td class="mv {d_cls}">{d_str}</td><td class="mv {d_cls}">{p_str}</td>'
            rows += f'<tr><td class="mn">{label}</td>{wow}{cells}</tr>'
        return f"""
        <div class="sec-h {accent}">{title}</div>
        <table class="dt"><thead><tr><th class="tl">Metric</th>{wow_h}{ph}</tr></thead>
        <tbody>{rows}</tbody></table>"""

    traffic = _trend_section('TRAFFIC', 'a-blue', [
        ('Organic Sessions', 'organic_sessions', False),
        ('Organic Users', 'organic_users', False),
        ('Website Leads', 'leads', False),
    ])

    engagement = _trend_section('ENGAGEMENT', 'a-green', [
        ('Avg. Session Duration (sec)', 'avg_session_duration', False),
        ('Bounce Rate', 'bounce_rate', True),
    ])

    search_console = _trend_section('SEARCH CONSOLE', 'a-purple', [
        ('Google Search Console Clicks', 'gsc_clicks', False),
        ('Google Search Console Impressions', 'gsc_impressions', False),
        ('Avg. Position', 'gsc_position', False),
    ])

    # Top Queries table
    queries_html = ''
    queries = _g(gsc, 'queries') or []
    if queries:
        qr = ''.join(f"""<tr><td class="mn" style="font-weight:500">{i}.</td>
            <td class="mn">{q.get('query','—')}</td>
            <td class="mv">{_f(q.get('clicks'))}</td>
            <td class="mv">{_f(q.get('impressions'))}</td>
            <td class="mv">{_f(q.get('ctr'), pct=True)}</td>
            <td class="mv">{_f(q.get('position'))}</td></tr>"""
            for i, q in enumerate(queries[:20], 1))
        queries_html = f"""
        <div class="sec-h a-amber">TOP QUERIES</div>
        <table class="dt"><thead><tr><th class="tl">#</th><th class="tl">Query</th>
        <th class="tr">Clicks</th><th class="tr">Impressions</th><th class="tr">CTR</th><th class="tr">Position</th>
        </tr></thead><tbody>{qr}</tbody></table>"""

    # Top Pages
    pages_html = ''
    pages = _g(gsc, 'pages') or _g(ga4, 'pages') or []
    if pages:
        pr = ''
        for i, p in enumerate(pages[:15], 1):
            if isinstance(p, dict):
                url = p.get('page', p.get('pagePath', ''))
                if len(url) > 55:
                    url = url[:52] + '…'
                pr += f"""<tr><td class="mn">{i}.</td><td class="mn" style="font-size:0.72rem">{url}</td>
                    <td class="mv">{_f(p.get('clicks', p.get('sessions')))}</td>
                    <td class="mv">{_f(p.get('impressions', p.get('users')))}</td></tr>"""
        if pr:
            pages_html = f"""
            <div class="sec-h a-amber">TOP PAGES</div>
            <table class="dt"><thead><tr><th class="tl">#</th><th class="tl">Page</th>
            <th class="tr">Clicks</th><th class="tr">Impressions</th></tr></thead><tbody>{pr}</tbody></table>"""

    return f"""
<section class="sheet">
  <div class="sh-t"><span class="sh-i">🔍</span> SEO Weekly Performance — 5 Week Trend</div>
  {traffic}
  {engagement}
  {search_console}
  {queries_html}
  {pages_html}
</section>"""


def _smm_sheet(smm_trend):
    if not smm_trend:
        return """
<section class="sheet">
  <div class="sh-t"><span class="sh-i">📱</span> Social Media Marketing — 5 Week Trend</div>
  <p class="empty-n">No social media trend data available for this period.</p>
</section>"""

    periods = [t.get('period', '') for t in smm_trend]
    n = len(periods)
    ph = ''.join(f'<th class="tc">{p}</th>' for p in periods)
    wow_h = '<th class="tc">WoW Δ</th><th class="tc">WoW %</th>' if n >= 2 else ''
    col_span = n + 1 + (2 if n >= 2 else 0)

    metrics = [
        ('Followers / Page Likes', ['followers'], False),
        ('New Followers (net)', ['new_followers'], False),
        ('Reach', ['reach'], False),
        ('Views', ['views'], False),
        ('Engagements (total)', ['engagements'], False),
        ('Engagement Rate (%)', ['engagement_rate'], True),
        ('Posts Published', ['posts_published'], False),
        ('Stories / Reels', ['reels_stories'], False),
        ('Video Views', ['video_views'], False),
        ('Link Clicks', ['link_clicks'], False),
        ('Profile Visits / Page Views', ['profile_visits', 'profile_views'], False),
        ('Saves / Shares', ['saves_shares'], False),
    ]

    def _plat_block(key, label, color, icon):
        hdr = f"""<tr><td colspan="{col_span}" class="plat-h" style="background:{color}0D; color:{color}; border-left:4px solid {color}">
            {icon} {label}</td></tr>"""
        rows = ''
        for mlabel, mkeys, is_pct in metrics:
            vals = []
            for t in smm_trend:
                src = t.get(key) or {}
                v = None
                for k in mkeys:
                    v = src.get(k)
                    if v is not None:
                        break
                vals.append(v)
            cells = ''.join(f'<td class="mv">{_f(v, pct=is_pct)}</td>' for v in vals)
            wow = ''
            if n >= 2:
                d_str, p_str = _delta(vals[-1], vals[-2])
                d_cls = 'delta-up' if d_str.startswith('+') else ('delta-down' if d_str.startswith('-') else '')
                wow = f'<td class="mv {d_cls}">{d_str}</td><td class="mv {d_cls}">{p_str}</td>'
            rows += f'<tr><td class="mn">{mlabel}</td>{wow}{cells}</tr>'
        return hdr + rows

    ig_block = _plat_block('ig', 'INSTAGRAM', '#E4405F', '📷')
    fb_block = _plat_block('fb', 'FACEBOOK', '#1877F2', '👥')
    li_block = ''
    if any(t.get('li') for t in smm_trend):
        li_block = _plat_block('li', 'LINKEDIN', '#0A66C2', '💼')

    return f"""
<section class="sheet">
  <div class="sh-t"><span class="sh-i">📱</span> Social Media Marketing — 5 Week Trend</div>
  <div class="table-scroll">
  <table class="dt trend">
    <thead><tr><th class="tl" style="min-width:200px">Metric</th>{wow_h}{ph}</tr></thead>
    <tbody>{ig_block}{fb_block}{li_block}</tbody>
  </table>
  </div>
</section>"""


def _ads_sheet(ads):
    if not ads:
        return """
<section class="sheet">
  <div class="sh-t"><span class="sh-i">🎯</span> Paid Ads — Performance</div>
  <p class="empty-n">No ad campaign data available for this period.</p>
</section>"""

    ti = sum(int(_g(c, 'impressions', 0) or 0) for c in ads)
    tc = sum(int(_g(c, 'clicks', 0) or 0) for c in ads)
    tl = sum(int(_g(c, 'leads', 0) or 0) for c in ads)
    ts = sum(float(_g(c, 'spend', 0) or 0) for c in ads)
    tr_ = sum(int(_g(c, 'reach', 0) or 0) for c in ads)
    ctr = (tc / ti * 100) if ti > 0 else 0
    cpl = (ts / tl) if tl > 0 else 0

    summary_items = [
        ('Impressions', _f(ti), '#7C3AED'),
        ('Clicks', _f(tc), '#0EA5E9'),
        ('Leads', _f(tl), '#10B981'),
        ('CTR', _f(ctr, pct=True), '#F59E0B'),
        ('Reach', _f(tr_), '#6366F1'),
        ('Spend', _f(ts, cur=True), '#EF4444'),
        ('CPL', _f(cpl, cur=True), '#EC4899'),
    ]

    cards = ''.join(f"""<div class="kpi">
        <div class="kpi-bar" style="background:{c}"></div>
        <div class="kpi-v">{v}</div><div class="kpi-l">{l}</div></div>"""
        for l, v, c in summary_items)

    camp_rows = ''
    for c in ads:
        name = c.get('campaign_name', c.get('name', '—'))
        status = c.get('status', '—')
        sc = '#10B981' if status == 'ACTIVE' else '#94A3B8'
        camp_rows += f"""<tr>
            <td class="mn" style="font-size:0.73rem; max-width:250px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">{name}</td>
            <td><span class="status-pill" style="background:{sc}15; color:{sc}">{status}</span></td>
            <td class="mv">{_f(_g(c,'impressions'))}</td>
            <td class="mv">{_f(_g(c,'clicks'))}</td>
            <td class="mv">{_f(_g(c,'ctr'), pct=True)}</td>
            <td class="mv">{_f(_g(c,'reach'))}</td>
            <td class="mv">{_f(_g(c,'leads'))}</td>
            <td class="mv">{_f(float(_g(c,'spend',0) or 0), cur=True)}</td>
            <td class="mv">{_f(float(_g(c,'cpc',0) or 0), cur=True)}</td></tr>"""

    return f"""
<section class="sheet">
  <div class="sh-t"><span class="sh-i">🎯</span> Paid Ads — Performance</div>
  <div class="sec-h a-purple">PLATFORM PERFORMANCE — SUMMARY</div>
  <div class="kpi-grid">{cards}</div>

  <div class="sec-h a-green">CAMPAIGN PERFORMANCE — DETAIL</div>
  <div class="table-scroll">
  <table class="dt">
    <thead><tr><th class="tl">Campaign</th><th class="tr">Status</th><th class="tr">Impressions</th>
    <th class="tr">Clicks</th><th class="tr">CTR</th><th class="tr">Reach</th>
    <th class="tr">Leads</th><th class="tr">Spend</th><th class="tr">CPC</th></tr></thead>
    <tbody>{camp_rows}</tbody>
  </table>
  </div>
</section>"""


def _exec_summary(gsc, ga4, fb, ig, ads):
    points = []
    org = _g(ga4, 'organic_sessions')
    if org and isinstance(org, (int, float)) and org > 0:
        points.append(f"Organic sessions reached <strong>{_f(int(org))}</strong> for the reporting period.")
    gc = _g(gsc, 'clicks')
    gi = _g(gsc, 'impressions')
    if gc and gi:
        points.append(f"Search Console: <strong>{_f(int(gc))}</strong> clicks from <strong>{_f(int(gi))}</strong> impressions.")
    ir = _g(ig, 'reach', 0) or 0
    fr = _g(fb, 'reach', 0) or 0
    if ir + fr > 0:
        points.append(f"Total social reach: <strong>{_f(ir + fr)}</strong> (IG: {_f(ir)}, FB: {_f(fr)}).")
    ie = _g(ig, 'engagements', 0) or 0
    fe = _g(fb, 'engagements', 0) or 0
    if ie + fe > 0:
        points.append(f"Combined social engagements: <strong>{_f(ie + fe)}</strong>.")
    ifl = _g(ig, 'followers', 0) or 0
    ffl = _g(fb, 'followers', 0) or 0
    if ifl or ffl:
        points.append(f"Current followers — Instagram: <strong>{_f(ifl)}</strong>, Facebook: <strong>{_f(ffl)}</strong>.")
    spend = sum(float(_g(c, 'spend', 0) or 0) for c in ads)
    leads = sum(int(_g(c, 'leads', 0) or 0) for c in ads)
    if spend > 0:
        cpl = spend / leads if leads > 0 else 0
        txt = f"Ad spend: <strong>{_f(spend, cur=True)}</strong> → <strong>{_f(leads)}</strong> leads"
        if cpl > 0:
            txt += f" at <strong>{_f(cpl, cur=True)}</strong> CPL"
        points.append(txt + ".")

    if not points:
        return ''

    bullets = ''.join(f'<li>{p}</li>' for p in points)

    summary_cards = [
        ('Social Reach', _f((ir + fr) or None), '#7C3AED'),
        ('Engagements', _f((ie + fe) or None), '#0EA5E9'),
        ('Organic Sessions', _f(org), '#10B981'),
        ('Ad Leads', _f(leads or None), '#F59E0B'),
        ('Ad Spend', _f(spend, cur=True) if spend else '—', '#EF4444'),
        ('GSC Clicks', _f(gc), '#6366F1'),
    ]
    sc = ''.join(f"""<div class="kpi">
        <div class="kpi-bar" style="background:{c}"></div>
        <div class="kpi-v">{v}</div><div class="kpi-l">{l}</div></div>"""
        for l, v, c in summary_cards)

    return f"""
<section class="sheet">
  <div class="sh-t"><span class="sh-i">📌</span> Executive Summary</div>
  <div class="sec-h a-amber">THE HEADLINE</div>
  <ul class="exec-list">{bullets}</ul>
  <div class="sec-h a-green">KEY METRICS AT A GLANCE</div>
  <div class="kpi-grid">{sc}</div>
</section>"""


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#F0F2F8;color:#0F172A;font-size:.82rem;line-height:1.55}

/* ─ Header ─ */
.hdr{background:linear-gradient(135deg,#4C1D95 0%,#6D28D9 40%,#7C3AED 100%);color:#fff;padding:2.25rem 2.5rem;display:flex;justify-content:space-between;align-items:center;position:relative;overflow:hidden}
.hdr::after{content:'';position:absolute;top:-60px;right:-60px;width:200px;height:200px;background:rgba(255,255,255,.06);border-radius:50%}
.hdr::before{content:'';position:absolute;bottom:-40px;left:30%;width:160px;height:160px;background:rgba(255,255,255,.04);border-radius:50%}
.hdr-l{display:flex;align-items:center;gap:1.1rem;z-index:1}
.hdr-logo{width:52px;height:52px;border-radius:14px;background:rgba(255,255,255,.15);backdrop-filter:blur(12px);display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1.15rem;letter-spacing:.05em;border:1px solid rgba(255,255,255,.2)}
.hdr-t{font-size:1.25rem;font-weight:800;letter-spacing:-.02em}
.hdr-sub{font-size:.85rem;opacity:.75;font-weight:500;margin-top:2px}
.hdr-r{text-align:right;z-index:1}
.hdr-badge{font-size:.8rem;font-weight:700;background:rgba(255,255,255,.14);padding:.4rem 1.1rem;border-radius:10px;display:inline-block;backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.15);margin-bottom:.3rem}
.hdr-dept{font-size:.72rem;opacity:.6;font-weight:500}

/* ─ Sheets ─ */
.sheet{background:#fff;margin:1.1rem 1.75rem;border-radius:14px;padding:2rem 2.25rem;box-shadow:0 1px 4px rgba(0,0,0,.04),0 4px 16px rgba(0,0,0,.03);page-break-inside:avoid}
.sh-t{font-size:1.1rem;font-weight:800;color:#0F172A;margin-bottom:1.5rem;display:flex;align-items:center;gap:.55rem;padding-bottom:.9rem;border-bottom:2px solid #F1F5F9;letter-spacing:-.01em}
.sh-i{font-size:1.15rem}

/* ─ Section headers ─ */
.sec-h{font-weight:800;font-size:.68rem;letter-spacing:.12em;text-transform:uppercase;padding:.55rem 1rem;border-radius:8px;margin:1.5rem 0 .85rem 0}
.sec-h:first-child,.sec-h:first-of-type{margin-top:0}
.a-purple{background:#F5F3FF;color:#7C3AED;border-left:4px solid #7C3AED}
.a-blue{background:#EFF6FF;color:#2563EB;border-left:4px solid #2563EB}
.a-green{background:#ECFDF5;color:#059669;border-left:4px solid #059669}
.a-amber{background:#FFFBEB;color:#D97706;border-left:4px solid #D97706}
.a-red{background:#FEF2F2;color:#DC2626;border-left:4px solid #DC2626}

/* ─ KPI Cards ─ */
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.75rem;margin-bottom:.5rem}
.kpi{background:#FAFBFE;border:1px solid #E8ECF4;border-radius:10px;padding:1rem .85rem;text-align:center;position:relative;overflow:hidden;transition:transform .12s}
.kpi-bar{position:absolute;top:0;left:0;right:0;height:3.5px;border-radius:10px 10px 0 0}
.kpi-v{font-size:1.35rem;font-weight:800;color:#0F172A;margin-top:.3rem;font-variant-numeric:tabular-nums}
.kpi-l{font-size:.62rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.08em;margin-top:.3rem;line-height:1.3}

/* ─ Tables ─ */
.table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.dt{width:100%;border-collapse:separate;border-spacing:0;margin-bottom:.6rem;font-size:.78rem}
.dt thead th{background:#F8FAFC;color:#475569;font-weight:700;font-size:.65rem;letter-spacing:.07em;text-transform:uppercase;padding:.65rem .7rem;border-bottom:2px solid #E2E8F0;position:sticky;top:0}
.tl{text-align:left}.tr{text-align:right}.tc{text-align:center;white-space:nowrap;min-width:90px;font-size:.6rem!important}
.dt tbody tr{border-bottom:1px solid #F1F5F9;transition:background .1s}
.dt tbody tr:nth-child(even){background:#FAFBFD}
.dt tbody tr:hover{background:#F1F5F9}
.dt td{padding:.5rem .7rem;border-bottom:1px solid #F1F5F9}
.mn{font-weight:600;color:#1E293B;white-space:nowrap}
.mv{text-align:right;font-variant-numeric:tabular-nums;color:#0F172A;font-weight:500}
.trend .mv{text-align:center;font-size:.74rem}
.trend .mn{font-size:.76rem}
.plat-h{font-weight:800!important;font-size:.68rem!important;letter-spacing:.1em;padding:.65rem 1rem!important;border-bottom:none!important}

/* ─ Delta colors ─ */
.delta-up{color:#059669!important;font-weight:700!important}
.delta-down{color:#DC2626!important;font-weight:700!important}

/* ─ Status pill ─ */
.status-pill{font-size:.65rem;font-weight:700;padding:3px 10px;border-radius:20px;letter-spacing:.04em;white-space:nowrap}

/* ─ Executive ─ */
.exec-list{padding:.85rem 1.5rem .85rem 2rem;line-height:2;color:#1E293B;font-size:.84rem}
.exec-list li{margin-bottom:.2rem}
.exec-list strong{color:#7C3AED;font-weight:700}

/* ─ Footer ─ */
.footer{display:flex;justify-content:space-between;padding:1.15rem 2.25rem;font-size:.68rem;color:#94A3B8;margin:0 1.75rem .75rem}
.empty-n{color:#94A3B8;font-style:italic;padding:1.25rem 0;font-size:.84rem}

/* ─ Print ─ */
@media print{
  body{background:#fff;font-size:.72rem}
  .sheet{box-shadow:none;margin:.6rem 0;border:1px solid #E2E8F0;page-break-inside:avoid}
  .hdr,.sec-h,.plat-h,.kpi,.kpi-bar,.dt tbody tr:nth-child(even),.status-pill{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .hdr::after,.hdr::before{display:none}
}
"""
