"""
Generate a premium, self-contained HTML marketing performance report
for Right Horizons clients.
"""

from datetime import datetime, timezone, timedelta


def _fmt(val, is_pct=False, is_currency=False):
    """Format a value for display in the report."""
    if val is None or val == '' or val == '-':
        return '—'
    if isinstance(val, str):
        return val
    if is_pct:
        return f"{val:.2f}%" if val else '—'
    if is_currency:
        return f"₹{val:,.2f}" if val else '—'
    if isinstance(val, float):
        return f"{val:,.2f}" if val else '—'
    if isinstance(val, int):
        return f"{val:,}" if val else '0'
    return str(val)


def _safe(data, *keys, default=None):
    """Safely traverse nested dicts."""
    obj = data
    for k in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(k, default)
    return obj


def _metric_card(label, value, color="#7C3AED"):
    """Render a single KPI card."""
    return f'''
    <div class="metric-card" style="border-top: 4px solid {color};">
      <div class="metric-value">{value}</div>
      <div class="metric-label">{label}</div>
    </div>'''


def _table(headers, rows, align=None):
    """Render an HTML table. align is a list of 'l' or 'r' per column."""
    if not rows:
        return '<p class="empty">No data available for this section.</p>'
    n = len(headers)
    if align is None:
        align = ['l'] + ['r'] * (n - 1)
    head = ''.join(
        f'<th style="text-align:{"left" if align[i] == "l" else "right"}">{h}</th>'
        for i, h in enumerate(headers)
    )
    body = ''
    for row in rows:
        cells = ''.join(
            f'<td style="text-align:{"left" if align[i] == "l" else "right"}">{row[i]}</td>'
            for i in range(n)
        )
        body += f'<tr>{cells}</tr>\n'
    return f'''
    <table>
      <thead><tr>{head}</tr></thead>
      <tbody>{body}</tbody>
    </table>'''


def generate_html_report(data: dict, start: str, end: str, domain: str) -> str:
    """
    Generate a premium, self-contained HTML marketing performance report.

    Args:
        data: dict with optional keys: gsc, ga4, social_fb, social_ig,
              meta_ads, social_trend
        start: report start date string
        end: report end date string
        domain: website domain

    Returns:
        Complete HTML document as a string.
    """
    if data is None:
        data = {}

    gsc = data.get('gsc') or {}
    ga4 = data.get('ga4') or {}
    social_fb = data.get('social_fb') or {}
    social_ig = data.get('social_ig') or {}
    meta_ads = data.get('meta_ads') or []
    social_trend = data.get('social_trend') or []

    _IST = timezone(timedelta(hours=5, minutes=30))
    generated_at = datetime.now(_IST).strftime('%d %b %Y, %I:%M %p IST')

    # ── Performance Summary cards ────────────────────────────────────
    total_reach = 0
    total_impressions = 0
    total_engagements = 0
    organic_sessions = _safe(ga4, 'organic_sessions')
    ad_impressions = 0
    ad_clicks = 0

    for ig_key in ['reach']:
        v = _safe(social_ig, ig_key)
        if isinstance(v, (int, float)):
            total_reach += int(v)
    for fb_key in ['reach']:
        v = _safe(social_fb, fb_key)
        if isinstance(v, (int, float)):
            total_reach += int(v)

    for src in [social_ig, social_fb]:
        v = src.get('engagements')
        if isinstance(v, (int, float)):
            total_engagements += int(v)

    gsc_impressions = _safe(gsc, 'impressions')
    if isinstance(gsc_impressions, (int, float)):
        total_impressions += int(gsc_impressions)
    for src in [social_ig, social_fb]:
        v = src.get('views')
        if isinstance(v, (int, float)):
            total_impressions += int(v)

    for camp in meta_ads:
        v = camp.get('impressions')
        if isinstance(v, (int, float)):
            ad_impressions += int(v)
        v = camp.get('clicks')
        if isinstance(v, (int, float)):
            ad_clicks += int(v)

    cards_html = '<div class="metrics-grid">'
    card_data = [
        ("Total Reach", _fmt(total_reach or None), "#7C3AED"),
        ("Total Impressions", _fmt(total_impressions or None), "#0EA5E9"),
        ("Total Engagements", _fmt(total_engagements or None), "#10B981"),
        ("Organic Sessions", _fmt(organic_sessions), "#F59E0B"),
        ("Ad Impressions", _fmt(ad_impressions or None), "#EF4444"),
        ("Ad Clicks", _fmt(ad_clicks or None), "#7C3AED"),
    ]
    for label, value, color in card_data:
        cards_html += _metric_card(label, value, color)
    cards_html += '</div>'

    # ── SEO Performance ──────────────────────────────────────────────
    seo_traffic_rows = []
    if ga4:
        seo_traffic_rows.append((
            'Organic Sessions', _fmt(_safe(ga4, 'organic_sessions')),
        ))
        seo_traffic_rows.append((
            'Organic Users', _fmt(_safe(ga4, 'organic_users')),
        ))
        seo_traffic_rows.append((
            'Leads', _fmt(_safe(ga4, 'leads')),
        ))
        seo_traffic_rows.append((
            'Bounce Rate', _fmt(_safe(ga4, 'bounceRate'), is_pct=True),
        ))
        seo_traffic_rows.append((
            'Avg Session Duration', _fmt(_safe(ga4, 'avgSessionDuration')),
        ))
    seo_traffic_table = _table(['Metric', 'Value'], seo_traffic_rows, ['l', 'r'])

    gsc_summary_rows = []
    if gsc:
        gsc_summary_rows = [(
            _fmt(_safe(gsc, 'clicks')),
            _fmt(_safe(gsc, 'impressions')),
            _fmt(_safe(gsc, 'ctr'), is_pct=True),
            _fmt(_safe(gsc, 'position')),
        )]
    gsc_summary_table = _table(
        ['Clicks', 'Impressions', 'CTR', 'Avg Position'],
        gsc_summary_rows, ['r', 'r', 'r', 'r']
    )

    # Top queries
    queries = _safe(gsc, 'queries') or []
    query_rows = [
        (q.get('query', ''), _fmt(q.get('clicks')), _fmt(q.get('impressions')),
         _fmt(q.get('ctr'), is_pct=True), _fmt(q.get('position')))
        for q in queries[:20]
    ]
    queries_table = _table(
        ['Query', 'Clicks', 'Impressions', 'CTR', 'Avg Position'],
        query_rows, ['l', 'r', 'r', 'r', 'r']
    )

    # Top pages
    gsc_pages = _safe(gsc, 'pages') or []
    ga4_pages = _safe(ga4, 'pages') or []
    pages_list = gsc_pages or ga4_pages
    page_rows = []
    for p in pages_list[:20]:
        if isinstance(p, dict):
            page_rows.append((
                p.get('page', p.get('pagePath', '')),
                _fmt(p.get('clicks', p.get('sessions', ''))),
                _fmt(p.get('impressions', p.get('users', ''))),
                _fmt(p.get('ctr'), is_pct=True),
                _fmt(p.get('position', '')),
            ))
        elif isinstance(p, str):
            page_rows.append((p, '—', '—', '—', '—'))
    pages_table = _table(
        ['Page', 'Clicks', 'Impressions', 'CTR', 'Avg Position'],
        page_rows, ['l', 'r', 'r', 'r', 'r']
    )

    # ── Social Media tables ──────────────────────────────────────────
    social_metrics = [
        ('Followers', 'followers'),
        ('New Followers', 'new_followers'),
        ('Reach', 'reach'),
        ('Views', 'views'),
        ('Engagements', 'engagements'),
        ('Engagement Rate', 'engagement_rate'),
        ('Posts Published', 'posts_published'),
        ('Stories / Reels', 'reels_stories'),
        ('Video Views', 'video_views'),
        ('Link Clicks', 'link_clicks'),
        ('Profile Visits', 'profile_visits', 'profile_views'),
        ('Saves / Shares', 'saves_shares'),
    ]

    def _social_table(src):
        if not src:
            return '<p class="empty">No data available for this section.</p>'
        rows = []
        for item in social_metrics:
            label = item[0]
            keys = item[1:]
            val = None
            for k in keys:
                val = src.get(k)
                if val is not None:
                    break
            is_pct = 'rate' in label.lower()
            rows.append((label, _fmt(val, is_pct=is_pct)))
        return _table(['Metric', 'Value'], rows, ['l', 'r'])

    ig_name = _safe(social_ig, 'username') or ''
    ig_header = f' — @{ig_name}' if ig_name else ''
    fb_name = _safe(social_fb, 'page_name') or ''
    fb_header = f' — {fb_name}' if fb_name else ''

    ig_table = _social_table(social_ig)
    fb_table = _social_table(social_fb)

    # ── Meta Ads ─────────────────────────────────────────────────────
    ads_rows = []
    for c in meta_ads:
        ads_rows.append((
            c.get('campaign_name', ''),
            c.get('status', ''),
            _fmt(c.get('impressions')),
            _fmt(c.get('clicks')),
            _fmt(c.get('ctr'), is_pct=True),
            _fmt(c.get('spend'), is_currency=True),
            _fmt(c.get('cpc'), is_currency=True),
            _fmt(c.get('reach')),
            _fmt(c.get('leads')),
        ))
    ads_table = _table(
        ['Campaign', 'Status', 'Impressions', 'Clicks', 'CTR',
         'Spend', 'CPC', 'Reach', 'Leads'],
        ads_rows, ['l', 'l', 'r', 'r', 'r', 'r', 'r', 'r', 'r']
    )

    # ── Social Media Trend ───────────────────────────────────────────
    trend_html = ''
    if social_trend:
        trend_metrics = [
            ('Followers', 'followers'), ('New Followers', 'new_followers'),
            ('Reach', 'reach'), ('Views', 'views'),
            ('Engagements', 'engagements'), ('Engagement Rate', 'engagement_rate'),
            ('Posts Published', 'posts_published'), ('Stories / Reels', 'reels_stories'),
            ('Video Views', 'video_views'), ('Link Clicks', 'link_clicks'),
            ('Profile Visits', 'profile_visits', 'profile_views'),
            ('Saves / Shares', 'saves_shares'),
        ]
        periods = [t.get('period', '') for t in social_trend]
        period_headers = ['Metric'] + periods
        align = ['l'] + ['r'] * len(periods)

        for platform, pkey in [('Instagram', 'ig'), ('Facebook', 'fb')]:
            rows = []
            for item in trend_metrics:
                label = item[0]
                keys = item[1:]
                is_pct = 'rate' in label.lower()
                row = [label]
                for t in social_trend:
                    plat_data = t.get(pkey) or {}
                    val = None
                    for k in keys:
                        val = plat_data.get(k)
                        if val is not None:
                            break
                    row.append(_fmt(val, is_pct=is_pct))
                rows.append(tuple(row))
            trend_html += f'''
            <h4 class="trend-platform">{platform}</h4>
            {_table(period_headers, rows, align)}
            '''

    # ── Assemble HTML ────────────────────────────────────────────────
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Right Horizons — Marketing Performance Report</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: #1E293B;
    background: #fff;
    font-size: 14px;
    line-height: 1.6;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 40px 32px; }}

  /* Header */
  .report-header {{
    border-bottom: 3px solid #7C3AED;
    padding-bottom: 24px;
    margin-bottom: 36px;
  }}
  .report-header h1 {{
    font-size: 26px;
    font-weight: 700;
    color: #7C3AED;
    margin-bottom: 6px;
  }}
  .report-header .subtitle {{
    font-size: 15px;
    color: #64748B;
  }}
  .report-header .subtitle strong {{
    color: #334155;
  }}

  /* Section headers */
  .section {{
    margin-bottom: 40px;
  }}
  .section h2 {{
    font-size: 18px;
    font-weight: 700;
    color: #1E293B;
    border-left: 4px solid #7C3AED;
    padding-left: 14px;
    margin-bottom: 20px;
  }}
  .section h3 {{
    font-size: 15px;
    font-weight: 600;
    color: #475569;
    margin: 20px 0 10px 0;
  }}
  .trend-platform {{
    font-size: 14px;
    font-weight: 600;
    color: #7C3AED;
    margin: 18px 0 8px 0;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  /* Metric cards */
  .metrics-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 12px;
  }}
  .metric-card {{
    background: #F8FAFC;
    border-radius: 10px;
    padding: 20px 18px;
    text-align: center;
  }}
  .metric-value {{
    font-size: 24px;
    font-weight: 700;
    color: #1E293B;
    margin-bottom: 4px;
  }}
  .metric-label {{
    font-size: 12px;
    font-weight: 500;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12px;
    font-size: 13px;
  }}
  thead tr {{
    background: #7C3AED;
    color: #fff;
  }}
  th {{
    padding: 10px 14px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    white-space: nowrap;
  }}
  td {{
    padding: 9px 14px;
    border-bottom: 1px solid #E2E8F0;
  }}
  tbody tr:nth-child(even) {{
    background: #F8FAFC;
  }}
  tbody tr:hover {{
    background: #EDE9FE;
  }}

  .empty {{
    color: #94A3B8;
    font-style: italic;
    padding: 12px 0;
  }}

  /* Footer */
  .report-footer {{
    margin-top: 48px;
    padding-top: 20px;
    border-top: 1px solid #E2E8F0;
    text-align: center;
    font-size: 11px;
    color: #94A3B8;
  }}

  /* Print styles */
  @media print {{
    body {{ font-size: 11px; }}
    .container {{ padding: 0; max-width: 100%; }}
    .metric-card {{ break-inside: avoid; }}
    table {{ page-break-inside: auto; }}
    tr {{ page-break-inside: avoid; }}
    thead {{ display: table-header-group; }}
    .section {{ page-break-inside: avoid; }}
    tbody tr:hover {{ background: inherit; }}
  }}
</style>
</head>
<body>
<div class="container">

  <div class="report-header">
    <h1>Right Horizons — Marketing Performance Report</h1>
    <div class="subtitle">
      <strong>{domain}</strong> &nbsp;|&nbsp; {start} — {end}
    </div>
  </div>

  <!-- Performance Summary -->
  <div class="section">
    <h2>Performance Summary</h2>
    {cards_html}
  </div>

  <!-- SEO Performance -->
  <div class="section">
    <h2>SEO Performance</h2>
    <h3>Website Traffic (GA4)</h3>
    {seo_traffic_table}
    <h3>Search Console Overview</h3>
    {gsc_summary_table}
    <h3>Top Search Queries</h3>
    {queries_table}
    <h3>Top Pages</h3>
    {pages_table}
  </div>

  <!-- Social Media — Instagram -->
  <div class="section">
    <h2>Social Media — Instagram{ig_header}</h2>
    {ig_table}
  </div>

  <!-- Social Media — Facebook -->
  <div class="section">
    <h2>Social Media — Facebook{fb_header}</h2>
    {fb_table}
  </div>

  <!-- Paid Ads — Meta -->
  <div class="section">
    <h2>Paid Ads — Meta</h2>
    {ads_table}
  </div>

  {"" if not social_trend else f"""
  <!-- Social Media Trend -->
  <div class="section">
    <h2>Social Media Trend</h2>
    {trend_html}
  </div>
  """}

  <div class="report-footer">
    Generated on {generated_at} &nbsp;·&nbsp; Right Horizons &nbsp;·&nbsp; Confidential
  </div>

</div>
</body>
</html>'''

    return html
