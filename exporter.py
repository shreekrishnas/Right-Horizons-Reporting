import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter


PURPLE = "7C3AED"
SKY    = "0EA5E9"
GREEN  = "10B981"
DOMAIN_COLORS = {"rh": PURPLE, "pms": SKY, "aif": GREEN}

HEADER_FILL  = PatternFill("solid", fgColor="1E1B4B")
HEADER_FONT  = Font(color="FFFFFF", bold=True, name="Calibri", size=10)
TITLE_FONT   = Font(bold=True, name="Calibri", size=13, color="1E1B4B")
SUB_FONT     = Font(bold=True, name="Calibri", size=10, color="475569")
VALUE_FONT   = Font(name="Calibri", size=10)
THIN_BORDER  = Border(
    bottom=Side(style="thin", color="E5E7EB"),
)
CENTER       = Alignment(horizontal="center", vertical="center")
LEFT         = Alignment(horizontal="left",   vertical="center")


def _col_widths(ws, col_map: dict):
    for col_letter, width in col_map.items():
        ws.column_dimensions[col_letter].width = width


def _write_table(ws, start_row: int, headers: list, rows: list, accent_color: str) -> int:
    fill = PatternFill("solid", fgColor=accent_color)
    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=ci, value=h)
        cell.font = Font(color="FFFFFF", bold=True, name="Calibri", size=9)
        cell.fill = fill
        cell.alignment = CENTER
    for ri, row in enumerate(rows, start_row + 1):
        bg = PatternFill("solid", fgColor="F8F7FF") if ri % 2 == 0 else PatternFill("solid", fgColor="FFFFFF")
        for ci, val in enumerate(row, 1):
            cell = ws.cell(row=ri, column=ci, value=val)
            cell.font = VALUE_FONT
            cell.fill = bg
            cell.border = THIN_BORDER
            cell.alignment = LEFT if ci == 1 else CENTER
    return start_row + 1 + len(rows)


def build_report(domain_key: str, domain_label: str, start_date: str, end_date: str,
                 gsc_summary: dict, gsc_queries: list, gsc_pages: list,
                 ga4_summary: dict, ga4_pages: list, ga4_sources: list) -> bytes:
    wb = Workbook()
    accent = DOMAIN_COLORS.get(domain_key, PURPLE)

    # ── Sheet 1: Overview ────────────────────────────────────────────────
    ws = wb.active
    ws.title = "Overview"
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:H1")
    ws["A1"] = f"Right Horizons Reports — {domain_label}"
    ws["A1"].font = Font(bold=True, name="Calibri", size=16, color=accent)
    ws["A1"].alignment = LEFT
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Period: {start_date}  →  {end_date}   |   Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}"
    ws["A2"].font = Font(name="Calibri", size=9, color="94A3B8")
    ws.row_dimensions[2].height = 16

    # GSC KPIs
    row = 4
    ws.cell(row=row, column=1, value="Google Search Console").font = Font(bold=True, name="Calibri", size=11, color="1E1B4B")
    row += 1
    kpi_headers = ["Clicks", "Impressions", "CTR (%)", "Avg. Position"]
    kpi_values  = [gsc_summary.get("clicks",0), gsc_summary.get("impressions",0),
                   gsc_summary.get("ctr",0), gsc_summary.get("position",0)]
    for ci, (h, v) in enumerate(zip(kpi_headers, kpi_values), 1):
        ws.cell(row=row, column=ci, value=h).font = SUB_FONT
        ws.cell(row=row+1, column=ci, value=v).font = Font(bold=True, name="Calibri", size=14, color=accent)
    row += 3

    # GA4 KPIs
    ws.cell(row=row, column=1, value="Google Analytics 4").font = Font(bold=True, name="Calibri", size=11, color="1E1B4B")
    row += 1
    ga_headers = ["Sessions", "Users", "New Users", "Bounce Rate (%)", "Pageviews"]
    ga_values  = [ga4_summary.get("sessions",0), ga4_summary.get("users",0),
                  ga4_summary.get("new_users",0), ga4_summary.get("bounce_rate",0),
                  ga4_summary.get("pageviews",0)]
    for ci, (h, v) in enumerate(zip(ga_headers, ga_values), 1):
        ws.cell(row=row, column=ci, value=h).font = SUB_FONT
        ws.cell(row=row+1, column=ci, value=v).font = Font(bold=True, name="Calibri", size=14, color=accent)
    row += 3

    _col_widths(ws, {"A": 28, "B": 16, "C": 16, "D": 16, "E": 18, "F": 14, "G": 14, "H": 14})

    # ── Sheet 2: GSC Queries ─────────────────────────────────────────────
    ws2 = wb.create_sheet("GSC — Top Queries")
    ws2.sheet_view.showGridLines = False
    ws2["A1"] = f"Top Search Queries — {domain_label} — {start_date} to {end_date}"
    ws2["A1"].font = TITLE_FONT
    ws2.row_dimensions[1].height = 22
    _write_table(ws2, 3,
                 ["Query", "Clicks", "Impressions", "CTR (%)", "Avg. Position"],
                 [[q["query"], q["clicks"], q["impressions"], q["ctr"], q["position"]] for q in gsc_queries],
                 accent)
    _col_widths(ws2, {"A": 48, "B": 12, "C": 16, "D": 12, "E": 16})

    # ── Sheet 3: GSC Pages ───────────────────────────────────────────────
    ws3 = wb.create_sheet("GSC — Top Pages")
    ws3.sheet_view.showGridLines = False
    ws3["A1"] = f"Top Pages (GSC) — {domain_label} — {start_date} to {end_date}"
    ws3["A1"].font = TITLE_FONT
    ws3.row_dimensions[1].height = 22
    _write_table(ws3, 3,
                 ["Page URL", "Clicks", "Impressions", "CTR (%)", "Avg. Position"],
                 [[p["page"], p["clicks"], p["impressions"], p["ctr"], p["position"]] for p in gsc_pages],
                 accent)
    _col_widths(ws3, {"A": 55, "B": 12, "C": 16, "D": 12, "E": 16})

    # ── Sheet 4: GA4 Pages ───────────────────────────────────────────────
    ws4 = wb.create_sheet("GA4 — Top Pages")
    ws4.sheet_view.showGridLines = False
    ws4["A1"] = f"Top Pages (GA4) — {domain_label} — {start_date} to {end_date}"
    ws4["A1"].font = TITLE_FONT
    ws4.row_dimensions[1].height = 22
    _write_table(ws4, 3,
                 ["Page Path", "Views", "Sessions", "Avg. Duration (s)"],
                 [[p["page"], p["views"], p["sessions"], p["avg_dur"]] for p in ga4_pages],
                 accent)
    _col_widths(ws4, {"A": 55, "B": 12, "C": 14, "D": 18})

    # ── Sheet 5: GA4 Traffic Sources ─────────────────────────────────────
    ws5 = wb.create_sheet("GA4 — Traffic Sources")
    ws5.sheet_view.showGridLines = False
    ws5["A1"] = f"Traffic Sources — {domain_label} — {start_date} to {end_date}"
    ws5["A1"].font = TITLE_FONT
    ws5.row_dimensions[1].height = 22
    _write_table(ws5, 3,
                 ["Channel", "Sessions", "Users"],
                 [[s["channel"], s["sessions"], s["users"]] for s in ga4_sources],
                 accent)
    _col_widths(ws5, {"A": 32, "B": 14, "C": 14})

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
