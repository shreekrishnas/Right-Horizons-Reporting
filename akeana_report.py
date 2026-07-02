"""
Akeana-specific GA4 & Search Console report.
Follows the akeana_specific_metrics_report_1.html template exactly.
Sections: KPI Snapshot, Graphs (users trend, source, landing page, city),
Device & Age, Search Console KPIs, Branded/Non-Branded Keywords.
"""
import json as _json
from datetime import datetime, timezone, timedelta

_IST = timezone(timedelta(hours=5, minutes=30))

BRAND_TERMS = [
    "akeana", "akaena", "aekana", "aceana", "akeana inc",
    "akeana risc", "akeana risc-v", "akeana careers", "akeana funding",
    "akeana jobs", "akeana chip", "akeana semiconductor",
]

RELEVANT_TERMS = [
    "risc-v", "riscv", "risc v",
    "semiconductor", "chip", "soc", "asic", "fpga",
    "processor", "cpu", "core", "silicon",
    "ai chip", "ai processor", "ai accelerator", "ai hardware",
    "machine learning chip", "ml chip", "inference chip",
    "custom silicon", "custom chip", "custom processor",
    "embedded processor", "embedded core",
    "arm alternative", "arm competitor",
    "open source processor", "open source hardware",
    "tape out", "tapeout", "tape-out",
    "ip core", "ip licensing",
    "high performance computing", "hpc",
    "edge computing", "edge ai",
    "data center chip", "server chip",
    "automotive chip", "automotive processor",
    "iot chip", "iot processor",
]


def _is_branded(query: str) -> bool:
    q = query.lower().strip()
    return any(term in q for term in BRAND_TERMS)


def _is_relevant_non_branded(query: str) -> bool:
    q = query.lower().strip()
    if _is_branded(q):
        return False
    return any(term in q for term in RELEVANT_TERMS)


def _build_akeana_data(ga4_data: dict, gsc_data: dict, ga4_extra: dict, start: str, end: str) -> dict:
    summary = ga4_data.get("summary") or {}
    gsc_summary = gsc_data.get("summary") or {}
    queries = gsc_data.get("queries") or []

    branded = [q for q in queries if _is_branded(q.get("query", ""))]
    non_branded = [q for q in queries if _is_relevant_non_branded(q.get("query", ""))]

    weekly = ga4_extra.get("weekly_users") or []
    users_trend = []
    for w in weekly:
        wk = w.get("week", "")
        users_trend.append({
            "period": f"Week {wk[-2:]}" if len(wk) >= 2 else wk,
            "totalUsers": w.get("totalUsers"),
            "newUsers": w.get("newUsers"),
        })

    sources = ga4_extra.get("traffic_sources") or []
    traffic_by_source = [{"source": s.get("channel", ""), "sessions": s.get("sessions", 0), "users": s.get("users", 0)} for s in sources]

    landing_pages = ga4_extra.get("landing_pages") or []
    landing_page_traffic = [{"landingPage": p.get("landingPage", p.get("page", "")), "sessions": p.get("sessions", 0)} for p in landing_pages]

    cities = ga4_extra.get("cities") or []
    traffic_by_cities = [{"city": c.get("city", ""), "sessions": c.get("sessions", 0)} for c in cities]

    devices = ga4_extra.get("devices") or []
    device_data = [{"deviceCategory": d.get("deviceCategory", ""), "users": d.get("users", 0)} for d in devices]

    ages = ga4_extra.get("ages") or []
    age_data = [{"ageGroup": a.get("ageGroup", ""), "users": a.get("users", 0)} for a in ages]

    return {
        "clientName": "Akeana",
        "period": f"{start} – {end}",
        "generatedAt": datetime.now(_IST).strftime("%d %b %Y"),
        "ga4": {
            "summary": {
                "totalUsers": summary.get("users"),
                "newUsers": summary.get("new_users"),
                "engagementRate": round(100 - (summary.get("bounce_rate") or 0), 1) if summary.get("bounce_rate") is not None else None,
                "averageSessionDuration": summary.get("avg_session"),
                "sessions": summary.get("sessions"),
                "eventCount": summary.get("pageviews"),
            },
            "usersTrend": users_trend,
            "trafficBySource": traffic_by_source,
            "landingPageTraffic": landing_page_traffic,
            "trafficByCities": traffic_by_cities,
            "device": device_data,
            "age": age_data,
        },
        "gsc": {
            "summary": {
                "clicks": gsc_summary.get("clicks"),
                "impressions": gsc_summary.get("impressions"),
                "ctr": gsc_summary.get("ctr"),
            },
            "brandedKeywords": [
                {"query": q["query"], "clicks": q.get("clicks"), "impressions": q.get("impressions"), "ctr": q.get("ctr")}
                for q in branded
            ],
            "nonBrandedKeywords": [
                {"query": q["query"], "clicks": q.get("clicks"), "impressions": q.get("impressions"), "ctr": q.get("ctr")}
                for q in non_branded
            ],
        },
    }


def generate_akeana_report(ga4_data: dict, gsc_data: dict, ga4_extra: dict, start: str, end: str) -> str:
    report_data = _build_akeana_data(ga4_data, gsc_data, ga4_extra, start, end)
    data_json = _json.dumps(report_data, default=str)

    html_part = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Akeana — GA4 & Search Console Report</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root{{
      --ink:#172033;
      --muted:#64748b;
      --soft:#f6f8fb;
      --line:#e5e7eb;
      --brand:#165e83;
      --brand2:#0ea5a4;
      --card:#ffffff;
      --good:#047857;
      --warn:#b45309;
      --bad:#b91c1c;
    }}
    *{{box-sizing:border-box}}
    body{{margin:0;font-family:Inter,Arial,sans-serif;background:#f3f6fb;color:var(--ink);line-height:1.45}}
    .wrap{{max-width:1280px;margin:0 auto;padding:28px}}
    .hero{{background:linear-gradient(135deg,#0f2b46,#165e83 55%,#0ea5a4);color:#fff;border-radius:24px;padding:28px;box-shadow:0 24px 70px rgba(15,43,70,.24);position:relative;overflow:hidden}}
    .hero:after{{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;background:rgba(255,255,255,.12);border-radius:50%}}
    .hero-grid{{display:grid;grid-template-columns:2fr 1fr;gap:18px;align-items:end;position:relative;z-index:1}}
    .eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.12em;font-weight:900;opacity:.86}}
    .hero h1{{font-size:36px;margin:8px 0 8px;line-height:1.08}}
    .hero p{{max-width:820px;margin:0;color:rgba(255,255,255,.86);font-size:15px}}
    .period-card{{background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.22);border-radius:18px;padding:16px}}
    .period-card b{{display:block;font-size:20px}}
    .period-card span{{display:block;color:rgba(255,255,255,.75);font-size:12px;margin-top:4px}}
    .toolbar{{display:flex;gap:10px;align-items:center;justify-content:flex-end;margin:14px 0}}
    .btn{{border:0;background:#165e83;color:#fff;border-radius:999px;padding:10px 14px;font-weight:900;cursor:pointer}}
    .nav{{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0}}
    .nav a{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:10px 14px;color:#334155;text-decoration:none;font-weight:800;font-size:13px;box-shadow:0 8px 20px rgba(15,23,42,.05)}}
    .nav a:hover{{border-color:#165e83;color:#165e83}}
    .section{{margin:22px 0 34px}}
    .section-head{{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;margin-bottom:12px}}
    .section h2{{font-size:24px;margin:0}}
    .sub{{color:var(--muted);font-size:13px}}
    .cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
    .kpi{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:0 8px 24px rgba(15,23,42,.05)}}
    .kpi .label{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:900}}
    .kpi .value{{font-size:28px;font-weight:900;margin-top:6px}}
    .kpi .meta{{font-size:12px;color:var(--muted);margin-top:6px}}
    .grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
    .card{{background:#fff;border:1px solid var(--line);border-radius:18px;box-shadow:0 12px 35px rgba(15,23,42,.07);padding:18px}}
    .pill{{display:inline-flex;align-items:center;border-radius:999px;padding:4px 9px;font-size:11px;font-weight:900;background:#eef2ff;color:#3730a3}}
    .table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:16px;background:#fff}}
    .report-table{{border-collapse:collapse;width:100%;font-size:12px;min-width:760px}}
    .report-table th,.report-table td{{border-bottom:1px solid #eef2f7;border-right:1px solid #eef2f7;padding:9px 10px;vertical-align:top}}
    .report-table th{{background:#eff6ff;color:#0f2b46;text-align:left;font-weight:900;white-space:nowrap}}
    .report-table td.num{{text-align:right;font-variant-numeric:tabular-nums}}
    .report-table td:first-child{{font-weight:800;color:#1e293b}}
    .chart{{display:flex;flex-direction:column;gap:12px;margin-top:12px}}
    .bar-row{{display:grid;grid-template-columns:minmax(140px,240px) 1fr auto;gap:12px;align-items:center;font-size:12px}}
    .bar-label{{font-weight:800;color:#334155;word-break:break-word}}
    .bar-track{{height:12px;background:#eaf0f7;border-radius:999px;overflow:hidden}}
    .bar-fill{{height:100%;border-radius:999px;background:linear-gradient(90deg,#165e83,#0ea5a4);min-width:2px}}
    .bar-value{{font-weight:900;color:#0f2b46;font-variant-numeric:tabular-nums;white-space:nowrap}}
    .legend{{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-top:8px}}
    .legend span{{display:flex;align-items:center;gap:6px}}
    .dot{{width:10px;height:10px;border-radius:50%;background:#165e83;display:inline-block}}
    .dot.alt{{background:#0ea5a4}}
    .empty{{padding:16px;border:1px dashed #cbd5e1;border-radius:12px;background:#f8fafc;color:#64748b;font-size:13px}}
    .rr-footer{{margin-top:40px;padding:24px 28px;border-top:2px solid var(--line);text-align:center;color:var(--muted);font-size:12px}}
    .rr-footer p{{margin:6px 0}}
    @media(max-width:900px){{.wrap{{padding:16px}}.hero-grid,.cards,.grid-2{{grid-template-columns:1fr}}.hero h1{{font-size:28px}}.bar-row{{grid-template-columns:1fr}}.bar-value{{text-align:left}}}}
    @media print{{body{{background:#fff}}.wrap{{max-width:none;padding:0}}.nav,.toolbar{{display:none}}.hero,.card,.kpi{{box-shadow:none}}.table-wrap{{overflow:visible}}.report-table{{font-size:10px;min-width:0}}.section{{page-break-inside:avoid}}}}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">Reporting Room · Akeana</div>
          <h1>GA4 & Search Console Report</h1>
          <p>This report is restricted to website analytics, search performance, keyword split, traffic sources, landing pages, cities, device and age data only.</p>
        </div>
        <div class="period-card">
          <span>Reporting period</span>
          <b id="periodText">—</b>
          <span id="generatedText">Generated for Akeana</span>
        </div>
      </div>
    </header>

    <div class="toolbar"><button class="btn" onclick="window.print()">Print / Save PDF</button></div>

    <nav class="nav">
      <a href="#kpis">KPI Snapshot</a>
      <a href="#graphs">Graphs</a>
      <a href="#audience">Device & Age</a>
      <a href="#search-console">Search Console</a>
      <a href="#keywords">Branded / Non-Branded Keywords</a>
    </nav>

    <section class="section" id="kpis">
      <div class="section-head">
        <div>
          <h2>GA4 KPI Snapshot</h2>
          <div class="sub">Only the required GA4 metrics are shown here.</div>
        </div>
      </div>
      <div class="cards" id="kpiCards"></div>
    </section>

    <section class="section" id="graphs">
      <div class="section-head">
        <div>
          <h2>Graphs</h2>
          <div class="sub">Total users, new users, traffic source, landing page traffic, and city traffic.</div>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <span class="pill">Total Users vs New Users</span>
          <div class="legend"><span><i class="dot"></i>Total users</span><span><i class="dot alt"></i>New users</span></div>
          <div id="usersTrendChart" class="chart"></div>
        </div>
        <div class="card">
          <span class="pill">Traffic by Source</span>
          <div id="sourceChart" class="chart"></div>
        </div>
        <div class="card">
          <span class="pill">Landing Page Traffic</span>
          <div id="landingPageChart" class="chart"></div>
        </div>
        <div class="card">
          <span class="pill">Traffic by Cities</span>
          <div id="cityChart" class="chart"></div>
        </div>
      </div>
    </section>

    <section class="section" id="audience">
      <div class="section-head">
        <div>
          <h2>Device and Age</h2>
          <div class="sub">Audience breakdown from GA4 only.</div>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <span class="pill">Device Category</span>
          <div id="deviceChart" class="chart"></div>
        </div>
        <div class="card">
          <span class="pill">Age Group</span>
          <div id="ageChart" class="chart"></div>
        </div>
      </div>
    </section>

    <section class="section" id="search-console">
      <div class="section-head">
        <div>
          <h2>Search Console</h2>
          <div class="sub">Only Clicks, Impressions, and CTR are included.</div>
        </div>
      </div>
      <div class="cards" id="gscCards"></div>
    </section>

    <section class="section" id="keywords">
      <div class="section-head">
        <div>
          <h2>Branded and Non-Branded Keywords</h2>
          <div class="sub">Keyword split from Google Search Console query data.</div>
        </div>
      </div>
      <div class="grid-2">
        <div class="card">
          <span class="pill">Branded Keywords</span>
          <div class="table-wrap" style="margin-top:12px">
            <table class="report-table">
              <thead><tr><th>Query</th><th>Clicks</th><th>Impressions</th><th>CTR</th></tr></thead>
              <tbody id="brandedKeywordRows"></tbody>
            </table>
          </div>
        </div>
        <div class="card">
          <span class="pill">Non-Branded Keywords</span>
          <div class="table-wrap" style="margin-top:12px">
            <table class="report-table">
              <thead><tr><th>Query</th><th>Clicks</th><th>Impressions</th><th>CTR</th></tr></thead>
              <tbody id="nonBrandedKeywordRows"></tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <footer class="rr-footer">
      <p id="footerText">Generated for Akeana</p>
      <p>This template intentionally excludes social media, ads, executive summary, health score, recommendations, and all unrelated metrics.</p>
    </footer>
  </div>

  <script>
    window.AKEANA_REPORT_DATA = __REPORT_DATA__;
"""

    js_part = r"""
    const reportData = window.AKEANA_REPORT_DATA;

    function isMissing(value){
      return value === null || value === undefined || value === "" || Number.isNaN(value);
    }

    function formatNumber(value){
      if(isMissing(value)) return "—";
      return Number(value).toLocaleString("en-IN");
    }

    function formatPercent(value){
      if(isMissing(value)) return "—";
      return `${Number(value).toFixed(2).replace(/\.00$/, "")}%`;
    }

    function formatDuration(seconds){
      if(isMissing(seconds)) return "—";
      const s = Number(seconds);
      if(s < 60) return `${Math.round(s)} sec`;
      const min = Math.floor(s / 60);
      const sec = Math.round(s % 60);
      return `${min}m ${sec}s`;
    }

    function renderKpiCards(containerId, cards){
      const container = document.getElementById(containerId);
      container.innerHTML = cards.map(card => `
        <div class="kpi">
          <div class="label">${card.label}</div>
          <div class="value">${card.value}</div>
          ${card.meta ? `<div class="meta">${card.meta}</div>` : ""}
        </div>
      `).join("");
    }

    function maxValue(rows, key){
      const values = rows.map(row => Number(row[key]) || 0);
      return Math.max(...values, 0);
    }

    function renderBarChart(containerId, rows, labelKey, valueKey, valueFormatter = formatNumber){
      const container = document.getElementById(containerId);
      if(!rows || rows.length === 0){
        container.innerHTML = `<div class="empty">No data available for this section.</div>`;
        return;
      }
      const max = maxValue(rows, valueKey) || 1;
      container.innerHTML = rows.map(row => {
        const value = Number(row[valueKey]) || 0;
        const width = Math.max((value / max) * 100, value > 0 ? 2 : 0);
        return `
          <div class="bar-row">
            <div class="bar-label">${row[labelKey] || "—"}</div>
            <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
            <div class="bar-value">${valueFormatter(row[valueKey])}</div>
          </div>
        `;
      }).join("");
    }

    function renderUsersTrend(containerId, rows){
      const container = document.getElementById(containerId);
      const hasData = rows && rows.some(row => !isMissing(row.totalUsers) || !isMissing(row.newUsers));
      if(!hasData){
        container.innerHTML = `<div class="empty">No weekly user trend data available for this period.</div>`;
        return;
      }
      const max = Math.max(maxValue(rows, "totalUsers"), maxValue(rows, "newUsers"), 1);
      container.innerHTML = rows.map(row => {
        const totalWidth = Math.max(((Number(row.totalUsers) || 0) / max) * 100, row.totalUsers ? 2 : 0);
        const newWidth = Math.max(((Number(row.newUsers) || 0) / max) * 100, row.newUsers ? 2 : 0);
        return `
          <div>
            <div class="bar-label" style="margin-bottom:6px">${row.period || row.date || "—"}</div>
            <div class="bar-row" style="grid-template-columns:90px 1fr auto"><div class="bar-label">Total</div><div class="bar-track"><div class="bar-fill" style="width:${totalWidth}%"></div></div><div class="bar-value">${formatNumber(row.totalUsers)}</div></div>
            <div class="bar-row" style="grid-template-columns:90px 1fr auto;margin-top:6px"><div class="bar-label">New</div><div class="bar-track"><div class="bar-fill" style="width:${newWidth}%;background:linear-gradient(90deg,#0ea5a4,#2dd4bf)"></div></div><div class="bar-value">${formatNumber(row.newUsers)}</div></div>
          </div>
        `;
      }).join("");
    }

    function renderKeywordRows(containerId, rows){
      const container = document.getElementById(containerId);
      if(!rows || rows.length === 0){
        container.innerHTML = `<tr><td colspan="4">No keyword data available.</td></tr>`;
        return;
      }
      container.innerHTML = rows.map(row => `
        <tr>
          <td>${row.query || "—"}</td>
          <td class="num">${formatNumber(row.clicks)}</td>
          <td class="num">${formatNumber(row.impressions)}</td>
          <td class="num">${formatPercent(row.ctr)}</td>
        </tr>
      `).join("");
    }

    function initReport(){
      document.getElementById("periodText").textContent = reportData.period || "—";
      document.getElementById("generatedText").textContent = `Generated for ${reportData.clientName || "Akeana"}`;
      document.getElementById("footerText").textContent = `Generated for ${reportData.clientName || "Akeana"}${reportData.generatedAt ? " · " + reportData.generatedAt : ""}`;

      const ga4 = reportData.ga4 || {};
      const ga4Summary = ga4.summary || {};
      renderKpiCards("kpiCards", [
        { label:"Total Users", value:formatNumber(ga4Summary.totalUsers) },
        { label:"New Users", value:formatNumber(ga4Summary.newUsers) },
        { label:"Engagement Rate", value:formatPercent(ga4Summary.engagementRate) },
        { label:"Average Session Duration", value:formatDuration(ga4Summary.averageSessionDuration) },
        { label:"Sessions", value:formatNumber(ga4Summary.sessions) },
        { label:"Event Count", value:formatNumber(ga4Summary.eventCount) }
      ]);

      renderUsersTrend("usersTrendChart", ga4.usersTrend || []);
      renderBarChart("sourceChart", ga4.trafficBySource || [], "source", "sessions");
      renderBarChart("landingPageChart", ga4.landingPageTraffic || [], "landingPage", "sessions");
      renderBarChart("cityChart", ga4.trafficByCities || [], "city", "sessions");
      renderBarChart("deviceChart", ga4.device || [], "deviceCategory", "users");
      renderBarChart("ageChart", ga4.age || [], "ageGroup", "users");

      const gsc = reportData.gsc || {};
      const gscSummary = gsc.summary || {};
      renderKpiCards("gscCards", [
        { label:"Clicks", value:formatNumber(gscSummary.clicks) },
        { label:"Impressions", value:formatNumber(gscSummary.impressions) },
        { label:"CTR", value:formatPercent(gscSummary.ctr) }
      ]);

      renderKeywordRows("brandedKeywordRows", gsc.brandedKeywords || []);
      renderKeywordRows("nonBrandedKeywordRows", gsc.nonBrandedKeywords || []);
    }

    initReport();
  </script>
</body>
</html>"""

    return html_part.replace("__REPORT_DATA__", data_json) + js_part
