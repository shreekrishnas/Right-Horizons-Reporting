"""
Generate a premium HTML marketing report matching the Excel template structure:
1. Performance Overview (This Week vs Last Week)
2. SEO Trend (5-week)
3. SMM Trend (5-week: Instagram, Facebook, LinkedIn)
4. Ads (Meta + LinkedIn platform performance, Campaign details by ICP)
5. Webinar performance
6. Executive Summary
"""

from datetime import datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))


def _fmt(val, is_pct=False, is_currency=False):
    if val is None or val == '' or val == '-':
        return '—'
    if isinstance(val, str):
        return val
    if is_pct:
        if isinstance(val, (int, float)) and val > 0:
            if val < 1:
                return f"{val * 100:.2f}%"
            return f"{val:.2f}%"
        return '—'
    if is_currency:
        return f"₹{val:,.2f}" if val else '—'
    if isinstance(val, float):
        if val == int(val):
            return f"{int(val):,}"
        return f"{val:,.2f}"
    if isinstance(val, int):
        return f"{val:,}"
    return str(val)


def _v(data, key, default=None):
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def generate_html_report(data: dict, start: str, end: str, domain: str) -> str:
    if data is None:
        data = {}

    gsc = data.get('gsc') or {}
    ga4 = data.get('ga4') or {}
    social_fb = data.get('social_fb') or {}
    social_ig = data.get('social_ig') or {}
    meta_ads = data.get('meta_ads') or []
    social_trend = data.get('social_trend') or []
    seo_trend = data.get('seo_trend') or []

    generated_at = datetime.now(_IST).strftime('%d %b %Y, %I:%M %p IST')

    # ── Build sections ──────────────────────────────────────────────
    perf_overview = _build_performance_overview(gsc, ga4, social_fb, social_ig, meta_ads)
    seo_section = _build_seo_trend(gsc, ga4, seo_trend)
    smm_section = _build_smm_trend(social_trend)
    ads_section = _build_ads(meta_ads)
    exec_section = _build_executive_summary(gsc, ga4, social_fb, social_ig, meta_ads)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{domain} — Marketing Performance Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
{_css()}
</style>
</head>
<body>

<!-- Header -->
<div class="report-header">
  <div class="header-brand">
    <div class="header-logo">RH</div>
    <div>
      <div class="header-title">Marketing Weekly Report</div>
      <div class="header-subtitle">{domain}</div>
    </div>
  </div>
  <div class="header-meta">
    <div class="header-period">{start} — {end}</div>
    <div class="header-dept">Department: Marketing</div>
  </div>
</div>

<!-- 1. Performance Overview -->
<div class="sheet" id="performance-overview">
  <div class="sheet-title">
    <span class="sheet-icon">📊</span>
    Performance Overview
  </div>
  {perf_overview}
</div>

<!-- 2. SEO Trend -->
<div class="sheet" id="seo-trend">
  <div class="sheet-title">
    <span class="sheet-icon">🔍</span>
    SEO Weekly Performance — Trend
  </div>
  {seo_section}
</div>

<!-- 3. SMM Trend -->
<div class="sheet" id="smm-trend">
  <div class="sheet-title">
    <span class="sheet-icon">📱</span>
    Social Media Marketing — Trend
  </div>
  {smm_section}
</div>

<!-- 4. Ads -->
<div class="sheet" id="ads">
  <div class="sheet-title">
    <span class="sheet-icon">🎯</span>
    Paid Ads — Performance
  </div>
  {ads_section}
</div>

<!-- 5. Executive Summary -->
<div class="sheet" id="executive-summary">
  <div class="sheet-title">
    <span class="sheet-icon">📌</span>
    Executive Summary
  </div>
  {exec_section}
</div>

<!-- Footer -->
<div class="report-footer">
  <div>Generated on {generated_at}</div>
  <div>Right Horizons — Confidential</div>
</div>

</body>
</html>"""


def _build_performance_overview(gsc, ga4, social_fb, social_ig, meta_ads):
    ig_reach = _v(social_ig, 'reach', 0) or 0
    fb_reach = _v(social_fb, 'reach', 0) or 0
    total_reach = ig_reach + fb_reach

    ig_imp = _v(social_ig, 'views', 0) or 0
    fb_imp = _v(social_fb, 'views', 0) or 0
    gsc_imp = _v(gsc, 'impressions', 0) or 0
    total_impressions = ig_imp + fb_imp + gsc_imp

    ig_eng = _v(social_ig, 'engagements', 0) or 0
    fb_eng = _v(social_fb, 'engagements', 0) or 0
    total_engagements = ig_eng + fb_eng

    organic_sessions = _v(ga4, 'organic_sessions', 0) or 0
    top5_kw = _v(gsc, 'top5_keywords', 0) or 0

    ad_impressions = sum(int(_v(c, 'impressions', 0) or 0) for c in meta_ads)
    ad_clicks = sum(int(_v(c, 'clicks', 0) or 0) for c in meta_ads)
    ad_ctr = (ad_clicks / ad_impressions * 100) if ad_impressions > 0 else 0
    total_leads = sum(int(_v(c, 'leads', 0) or 0) for c in meta_ads)
    total_spend = sum(float(_v(c, 'spend', 0) or 0) for c in meta_ads)

    eng_rate = (total_engagements / total_reach * 100) if total_reach > 0 else 0

    metrics = [
        ('Total Reach (all platforms)', _fmt(total_reach or None)),
        ('Total Impressions (all platforms)', _fmt(total_impressions or None)),
        ('Total Engagements', _fmt(total_engagements or None)),
        ('Avg. Engagement Rate (%)', _fmt(eng_rate, is_pct=True) if eng_rate > 0 else '—'),
        ('Organic Sessions (SEO)', _fmt(organic_sessions or None)),
        ('Top 5 Keywords Ranked', _fmt(top5_kw or None)),
        ('Total Ad Impressions', _fmt(ad_impressions or None)),
        ('Total Ad Clicks', _fmt(ad_clicks or None)),
        ('Overall Ad CTR (%)', _fmt(ad_ctr, is_pct=True) if ad_ctr > 0 else '—'),
        ('Total Leads', _fmt(total_leads or None)),
        ('Total Ad Spend', _fmt(total_spend, is_currency=True) if total_spend > 0 else '—'),
    ]

    rows = ''.join(f'<tr><td class="metric-name">{m[0]}</td><td class="metric-val">{m[1]}</td></tr>' for m in metrics)

    return f"""
    <div class="section-header accent-purple">PERFORMANCE SUMMARY — ALL CHANNELS</div>
    <table class="data-table">
      <thead><tr><th style="text-align:left;">Metric</th><th style="text-align:right;">This Period</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    """


def _build_seo_trend(gsc, ga4, seo_trend):
    sections = []

    # Traffic section
    traffic_metrics = [
        ('Organic Sessions', _v(ga4, 'organic_sessions')),
        ('Organic Users', _v(ga4, 'organic_users')),
        ('Website Leads', _v(ga4, 'leads')),
    ]
    sections.append(_trend_table('TRAFFIC', traffic_metrics))

    # Engagement
    engagement_metrics = [
        ('Avg. Session Duration (sec)', _v(ga4, 'avgSessionDuration')),
        ('Bounce Rate', _v(ga4, 'bounceRate')),
    ]
    sections.append(_trend_table('ENGAGEMENT', engagement_metrics, pct_keys=['Bounce Rate']))

    # Search Console
    gsc_metrics = [
        ('Google Search Console Clicks', _v(gsc, 'clicks')),
        ('Google Search Console Impressions', _v(gsc, 'impressions')),
        ('Avg. Position', _v(gsc, 'position')),
    ]
    sections.append(_trend_table('SEARCH CONSOLE', gsc_metrics))

    # Top Queries
    queries = _v(gsc, 'queries') or []
    if queries:
        q_rows = ''
        for i, q in enumerate(queries[:20], 1):
            q_rows += f"""<tr>
                <td>{i}</td>
                <td style="text-align:left;">{q.get('query', '—')}</td>
                <td class="metric-val">{_fmt(q.get('clicks'))}</td>
                <td class="metric-val">{_fmt(q.get('impressions'))}</td>
                <td class="metric-val">{_fmt(q.get('ctr'), is_pct=True)}</td>
                <td class="metric-val">{_fmt(q.get('position'))}</td>
            </tr>"""
        sections.append(f"""
        <div class="section-header accent-blue">TOP QUERIES</div>
        <table class="data-table">
          <thead><tr><th>#</th><th style="text-align:left;">Query</th><th>Clicks</th><th>Impressions</th><th>CTR</th><th>Avg Position</th></tr></thead>
          <tbody>{q_rows}</tbody>
        </table>""")

    # Top Pages
    pages = _v(gsc, 'pages') or _v(ga4, 'pages') or []
    if pages:
        p_rows = ''
        for i, p in enumerate(pages[:15], 1):
            if isinstance(p, dict):
                page_url = p.get('page', p.get('pagePath', ''))
                if len(page_url) > 60:
                    page_url = page_url[:57] + '...'
                p_rows += f"""<tr>
                    <td>{i}</td>
                    <td style="text-align:left; font-size:0.72rem;">{page_url}</td>
                    <td class="metric-val">{_fmt(p.get('clicks', p.get('sessions')))}</td>
                    <td class="metric-val">{_fmt(p.get('impressions', p.get('users')))}</td>
                </tr>"""
        if p_rows:
            sections.append(f"""
            <div class="section-header accent-blue">TOP PAGES</div>
            <table class="data-table">
              <thead><tr><th>#</th><th style="text-align:left;">Page</th><th>Clicks/Sessions</th><th>Impressions/Users</th></tr></thead>
              <tbody>{p_rows}</tbody>
            </table>""")

    return '\n'.join(sections) if sections else '<p class="empty-note">No SEO data available for this period.</p>'


def _trend_table(header, metrics, pct_keys=None):
    pct_keys = pct_keys or []
    rows = ''
    for label, val in metrics:
        is_pct = label in pct_keys
        rows += f'<tr><td class="metric-name">{label}</td><td class="metric-val">{_fmt(val, is_pct=is_pct)}</td></tr>'
    return f"""
    <div class="section-header accent-blue">{header}</div>
    <table class="data-table">
      <thead><tr><th style="text-align:left;">Metric</th><th style="text-align:right;">Value</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def _build_smm_trend(social_trend):
    if not social_trend:
        return '<p class="empty-note">No social media trend data available.</p>'

    periods = [t.get('period', '') for t in social_trend]
    period_headers = ''.join(f'<th class="period-th">{p}</th>' for p in periods)

    smm_metrics = [
        ('Followers / Page Likes', 'followers'),
        ('New Followers (net)', 'new_followers'),
        ('Reach', 'reach'),
        ('Views', 'views'),
        ('Engagements (total)', 'engagements'),
        ('Engagement Rate (%)', 'engagement_rate'),
        ('Posts Published', 'posts_published'),
        ('Stories / Reels', 'reels_stories'),
        ('Video Views', 'video_views'),
        ('Link Clicks', 'link_clicks'),
        ('Profile Visits / Page Views', 'profile_visits', 'profile_views'),
        ('Saves / Shares', 'saves_shares'),
    ]

    def _platform_rows(platform_key, platform_label, color, icon):
        header = f"""<tr class="platform-header" style="background:{color}10;">
            <td colspan="{len(periods) + 1}" style="font-weight:800; font-size:0.72rem;
            letter-spacing:0.08em; color:{color}; padding:0.6rem 1rem;">
            {icon} {platform_label}</td></tr>"""
        rows = ''
        for item in smm_metrics:
            label = item[0]
            keys = item[1:]
            is_pct = 'rate' in label.lower()
            row = f'<td class="metric-name">{label}</td>'
            for t in social_trend:
                plat = t.get(platform_key) or {}
                val = None
                for k in keys:
                    val = plat.get(k)
                    if val is not None:
                        break
                row += f'<td class="metric-val">{_fmt(val, is_pct=is_pct)}</td>'
            rows += f'<tr>{row}</tr>'
        return header + rows

    ig_rows = _platform_rows('ig', 'INSTAGRAM', '#E4405F', '📷')
    fb_rows = _platform_rows('fb', 'FACEBOOK', '#1877F2', '👥')

    # Check for LinkedIn data in trend
    has_linkedin = any(t.get('li') for t in social_trend)
    li_rows = ''
    if has_linkedin:
        li_rows = _platform_rows('li', 'LINKEDIN', '#0A66C2', '💼')

    return f"""
    <table class="data-table trend-table">
      <thead><tr><th style="text-align:left; width:220px;">Metric</th>{period_headers}</tr></thead>
      <tbody>
        {ig_rows}
        {fb_rows}
        {li_rows}
      </tbody>
    </table>"""


def _build_ads(meta_ads):
    if not meta_ads:
        return '<p class="empty-note">No ad campaign data available for this period.</p>'

    # Platform summary
    total_imp = sum(int(_v(c, 'impressions', 0) or 0) for c in meta_ads)
    total_clicks = sum(int(_v(c, 'clicks', 0) or 0) for c in meta_ads)
    total_leads = sum(int(_v(c, 'leads', 0) or 0) for c in meta_ads)
    total_spend = sum(float(_v(c, 'spend', 0) or 0) for c in meta_ads)
    total_reach = sum(int(_v(c, 'reach', 0) or 0) for c in meta_ads)
    ctr = (total_clicks / total_imp * 100) if total_imp > 0 else 0
    cpl = (total_spend / total_leads) if total_leads > 0 else 0

    summary = f"""
    <div class="section-header accent-green">PLATFORM PERFORMANCE — SUMMARY</div>
    <table class="data-table">
      <thead><tr><th style="text-align:left;">Metric</th><th>Value</th></tr></thead>
      <tbody>
        <tr><td class="metric-name">Total Impressions</td><td class="metric-val">{_fmt(total_imp)}</td></tr>
        <tr><td class="metric-name">Total Clicks</td><td class="metric-val">{_fmt(total_clicks)}</td></tr>
        <tr><td class="metric-name">Total Leads</td><td class="metric-val">{_fmt(total_leads)}</td></tr>
        <tr><td class="metric-name">CTR</td><td class="metric-val">{_fmt(ctr, is_pct=True)}</td></tr>
        <tr><td class="metric-name">Total Reach</td><td class="metric-val">{_fmt(total_reach)}</td></tr>
        <tr><td class="metric-name">Total Spend</td><td class="metric-val">{_fmt(total_spend, is_currency=True)}</td></tr>
        <tr><td class="metric-name">CPL</td><td class="metric-val">{_fmt(cpl, is_currency=True)}</td></tr>
      </tbody>
    </table>"""

    # Campaign details
    camp_rows = ''
    for c in meta_ads:
        name = c.get('campaign_name', c.get('name', '—'))
        if len(name) > 50:
            name = name[:47] + '...'
        status = c.get('status', '—')
        status_color = '#10B981' if status == 'ACTIVE' else '#9CA3AF'
        camp_rows += f"""<tr>
            <td style="text-align:left; font-size:0.75rem;">{name}</td>
            <td><span style="color:{status_color}; font-weight:600; font-size:0.72rem;">{status}</span></td>
            <td class="metric-val">{_fmt(_v(c, 'impressions'))}</td>
            <td class="metric-val">{_fmt(_v(c, 'clicks'))}</td>
            <td class="metric-val">{_fmt(_v(c, 'ctr'), is_pct=True)}</td>
            <td class="metric-val">{_fmt(_v(c, 'reach'))}</td>
            <td class="metric-val">{_fmt(_v(c, 'leads'))}</td>
            <td class="metric-val">{_fmt(float(_v(c, 'spend', 0) or 0), is_currency=True)}</td>
            <td class="metric-val">{_fmt(float(_v(c, 'cpc', 0) or 0), is_currency=True)}</td>
        </tr>"""

    campaigns = f"""
    <div class="section-header accent-green">CAMPAIGN PERFORMANCE — DETAIL</div>
    <table class="data-table">
      <thead><tr>
        <th style="text-align:left;">Campaign</th><th>Status</th><th>Impressions</th>
        <th>Clicks</th><th>CTR</th><th>Reach</th><th>Leads</th><th>Spend</th><th>CPC</th>
      </tr></thead>
      <tbody>{camp_rows}</tbody>
    </table>"""

    return summary + campaigns


def _build_executive_summary(gsc, ga4, social_fb, social_ig, meta_ads):
    highlights = []

    # Auto-generate highlights from data
    organic = _v(ga4, 'organic_sessions')
    if organic and isinstance(organic, (int, float)) and organic > 0:
        highlights.append(f"Organic sessions reached {_fmt(int(organic))} for the reporting period.")

    gsc_clicks = _v(gsc, 'clicks')
    gsc_imp = _v(gsc, 'impressions')
    if gsc_clicks and gsc_imp:
        highlights.append(f"Search Console recorded {_fmt(int(gsc_clicks))} clicks from {_fmt(int(gsc_imp))} impressions.")

    ig_reach = _v(social_ig, 'reach', 0) or 0
    fb_reach = _v(social_fb, 'reach', 0) or 0
    if ig_reach + fb_reach > 0:
        highlights.append(f"Total social media reach: {_fmt(ig_reach + fb_reach)} (Instagram: {_fmt(ig_reach)}, Facebook: {_fmt(fb_reach)}).")

    ig_eng = _v(social_ig, 'engagements', 0) or 0
    fb_eng = _v(social_fb, 'engagements', 0) or 0
    if ig_eng + fb_eng > 0:
        highlights.append(f"Combined social engagements: {_fmt(ig_eng + fb_eng)}.")

    ig_followers = _v(social_ig, 'followers', 0) or 0
    fb_followers = _v(social_fb, 'followers', 0) or 0
    if ig_followers > 0 or fb_followers > 0:
        highlights.append(f"Current followers — Instagram: {_fmt(ig_followers)}, Facebook: {_fmt(fb_followers)}.")

    total_ad_spend = sum(float(_v(c, 'spend', 0) or 0) for c in meta_ads)
    total_ad_leads = sum(int(_v(c, 'leads', 0) or 0) for c in meta_ads)
    if total_ad_spend > 0:
        cpl = total_ad_spend / total_ad_leads if total_ad_leads > 0 else 0
        highlights.append(f"Ad spend: {_fmt(total_ad_spend, is_currency=True)} generating {_fmt(total_ad_leads)} leads" +
                         (f" at {_fmt(cpl, is_currency=True)} CPL." if cpl > 0 else "."))

    if not highlights:
        return '<p class="empty-note">No data available to generate executive summary.</p>'

    bullets = ''.join(f'<li>{h}</li>' for h in highlights)

    return f"""
    <div class="section-header accent-amber">THE HEADLINE</div>
    <ul class="summary-list">{bullets}</ul>

    <div class="section-header accent-green">KEY HIGHLIGHTS</div>
    <div class="summary-grid">
      <div class="summary-card">
        <div class="summary-card-title">Social Reach</div>
        <div class="summary-card-value">{_fmt((ig_reach + fb_reach) or None)}</div>
      </div>
      <div class="summary-card">
        <div class="summary-card-title">Total Engagements</div>
        <div class="summary-card-value">{_fmt((ig_eng + fb_eng) or None)}</div>
      </div>
      <div class="summary-card">
        <div class="summary-card-title">Organic Sessions</div>
        <div class="summary-card-value">{_fmt(_v(ga4, 'organic_sessions'))}</div>
      </div>
      <div class="summary-card">
        <div class="summary-card-title">Ad Leads</div>
        <div class="summary-card-value">{_fmt(total_ad_leads or None)}</div>
      </div>
      <div class="summary-card">
        <div class="summary-card-title">Ad Spend</div>
        <div class="summary-card-value">{_fmt(total_ad_spend, is_currency=True) if total_ad_spend > 0 else '—'}</div>
      </div>
      <div class="summary-card">
        <div class="summary-card-title">GSC Clicks</div>
        <div class="summary-card-value">{_fmt(_v(gsc, 'clicks'))}</div>
      </div>
    </div>
    """


def _css():
    return """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: #F8F9FC;
      color: #1E293B;
      font-size: 0.82rem;
      line-height: 1.6;
      padding: 0;
    }

    /* Header */
    .report-header {
      background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 50%, #4C1D95 100%);
      color: #fff;
      padding: 2rem 2.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .header-brand { display: flex; align-items: center; gap: 1rem; }
    .header-logo {
      width: 48px; height: 48px; border-radius: 12px;
      background: rgba(255,255,255,0.2); backdrop-filter: blur(10px);
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 1.1rem; letter-spacing: 0.04em;
    }
    .header-title { font-size: 1.3rem; font-weight: 800; letter-spacing: -0.02em; }
    .header-subtitle { font-size: 0.82rem; opacity: 0.8; font-weight: 500; }
    .header-meta { text-align: right; }
    .header-period {
      font-size: 0.9rem; font-weight: 700;
      background: rgba(255,255,255,0.15); padding: 0.35rem 1rem;
      border-radius: 8px; display: inline-block; margin-bottom: 0.25rem;
    }
    .header-dept { font-size: 0.75rem; opacity: 0.7; }

    /* Sheets */
    .sheet {
      background: #fff;
      margin: 1.25rem 2rem;
      border-radius: 12px;
      padding: 1.75rem 2rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
      page-break-inside: avoid;
    }
    .sheet-title {
      font-size: 1.05rem; font-weight: 800; color: #1E293B;
      margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem;
      padding-bottom: 0.75rem; border-bottom: 2px solid #F1F5F9;
    }
    .sheet-icon { font-size: 1.1rem; }

    /* Section headers */
    .section-header {
      font-weight: 800; font-size: 0.7rem; letter-spacing: 0.1em;
      text-transform: uppercase; padding: 0.6rem 1rem;
      border-radius: 6px; margin: 1.25rem 0 0.75rem 0;
    }
    .section-header:first-child { margin-top: 0; }
    .accent-purple { background: #F5F3FF; color: #7C3AED; border-left: 4px solid #7C3AED; }
    .accent-blue { background: #EFF6FF; color: #2563EB; border-left: 4px solid #2563EB; }
    .accent-green { background: #F0FDF4; color: #16A34A; border-left: 4px solid #16A34A; }
    .accent-red { background: #FEF2F2; color: #DC2626; border-left: 4px solid #DC2626; }
    .accent-amber { background: #FFFBEB; color: #D97706; border-left: 4px solid #D97706; }

    /* Tables */
    .data-table {
      width: 100%; border-collapse: collapse; margin-bottom: 0.5rem;
      font-size: 0.78rem;
    }
    .data-table thead th {
      background: #F8FAFC; color: #64748B; font-weight: 700;
      font-size: 0.68rem; letter-spacing: 0.06em; text-transform: uppercase;
      padding: 0.6rem 0.75rem; text-align: right;
      border-bottom: 2px solid #E2E8F0;
    }
    .data-table thead th:first-child { text-align: left; }
    .data-table tbody tr { border-bottom: 1px solid #F1F5F9; }
    .data-table tbody tr:nth-child(even) { background: #FAFBFD; }
    .data-table tbody tr:hover { background: #F1F5F9; }
    .data-table td { padding: 0.55rem 0.75rem; }
    .metric-name { font-weight: 600; color: #334155; }
    .metric-val { text-align: right; font-variant-numeric: tabular-nums; color: #1E293B; font-weight: 500; }

    .trend-table { font-size: 0.74rem; }
    .trend-table .period-th {
      font-size: 0.62rem; text-align: center; white-space: nowrap;
      padding: 0.5rem 0.4rem; min-width: 90px;
    }
    .trend-table .metric-val { text-align: center; font-size: 0.74rem; }
    .platform-header td {
      border-top: 2px solid #E2E8F0 !important;
    }

    /* Summary */
    .summary-list {
      padding: 0.75rem 1.5rem; line-height: 1.9; color: #334155;
    }
    .summary-list li { margin-bottom: 0.25rem; }
    .summary-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem; margin-top: 0.5rem;
    }
    .summary-card {
      background: #F8FAFC; border-radius: 8px; padding: 1rem;
      text-align: center; border: 1px solid #E2E8F0;
    }
    .summary-card-title {
      font-size: 0.68rem; font-weight: 700; color: #64748B;
      text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.35rem;
    }
    .summary-card-value { font-size: 1.25rem; font-weight: 800; color: #7C3AED; }

    .empty-note {
      color: #94A3B8; font-style: italic; padding: 1rem 0; font-size: 0.82rem;
    }

    /* Footer */
    .report-footer {
      display: flex; justify-content: space-between; padding: 1.25rem 2.5rem;
      font-size: 0.7rem; color: #94A3B8; border-top: 1px solid #E2E8F0;
      margin: 0 2rem;
    }

    /* Print */
    @media print {
      body { background: #fff; font-size: 0.75rem; }
      .sheet { box-shadow: none; margin: 0.75rem 0; border: 1px solid #E2E8F0; }
      .report-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .section-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .platform-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .data-table tbody tr:nth-child(even) { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
    """
