#!/usr/bin/env python3
"""
build_interactive_google_sheet.py
Creates a production-grade, Google Sheets-ready interactive workbook:
WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx

Sheets Included:
1. Instructions & Guidelines (Color codes, How to use in Google Sheets)
2. 50_Pt_Roster_Decisions (242 Promotees with Dropdowns, SU Toggles, Real-Time Collision Alerts)
3. Obliterated_Rehab_Decisions (106 Obliterated Posts, 84 Active Incumbents with Dropdowns)
4. Available_DD_Posts (242 Unblocked DD Posts with Live Allocation Counter & Status)
5. Available_AD_Vacancies (157 Clear AD Vacancies for Obliterated Rehabilitation)
6. SU_Post_Picker (1,794 Cadre Posts lookup for Service Utilization)
7. Displaced_Queue_Tracker (Tracking officers displaced by SU collisions)
8. Secretariat_Posting_Order (Exact 6-Column Government Order dynamically mirrored from decisions)
"""

import sqlite3
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule

from generate_simple_4col_order import clean_pres, clean_sub, clean_su

DB_PATH = "ard_master_truth.db"
OUTPUT_FILE = "WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx"

def build_workbook():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    navy_header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Deep Navy
    teal_header_fill = PatternFill(start_color="0F766E", end_color="0F766E", fill_type="solid") # Dark Teal
    indigo_header_fill = PatternFill(start_color="3730A3", end_color="3730A3", fill_type="solid") # Indigo
    amber_header_fill = PatternFill(start_color="92400E", end_color="92400E", fill_type="solid") # Amber
    slate_header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid") # Slate

    white_header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=15, bold=True, color="1E3A8A")
    subtitle_font = Font(name="Calibri", size=11, bold=False, color="475569")
    bold_font = Font(name="Calibri", size=10, bold=True)
    normal_font = Font(name="Calibri", size=10)
    italic_font = Font(name="Calibri", size=10, italic=True, color="64748B")

    thin_border_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    plain_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    # =========================================================================
    # SHEET 1: Instructions & Guidelines
    # =========================================================================
    ws_guide = wb.create_sheet(title="Instructions & Guidelines")
    ws_guide.views.sheetView[0].showGridLines = True

    guide_lines = [
        ("GOVERNMENT OF WEST BENGAL", 16, True, "1E3A8A"),
        ("Animal Resources Development Department", 13, True, "0F766E"),
        ("Smart Posting Decision Board & AI Cadre System (Google Sheets Interactive Edition)", 12, False, "334155"),
        ("", 10, False, "000000"),
        ("HOW TO USE THIS SPREADSHEET IN GOOGLE SHEETS / EXCEL:", 12, True, "1E3A8A"),
        ("1. Upload this .xlsx file to Google Drive and open it with Google Sheets.", 10, False, "000000"),
        ("2. Open sheet '50_Pt_Roster_Decisions': Click any cell in Column M (Allotted Substantive Post) to select from the 242 unblocked Deputy Director vacancies via drop-down.", 10, False, "000000"),
        ("3. Service Utilization (SU): If the officer needs to be posted to another location on Service Utilization, select 'YES' in Column N, then choose any station from the drop-down in Column O.", 10, False, "000000"),
        ("4. Real-Time Collision & Displacement Protection: If an SU post is already occupied by a serving officer, Column P will turn RED ('⚠️ SU COLLISION') and Column Q will display the displaced officer's name and HRMS ID.", 10, False, "000000"),
        ("5. Check Post Availability: Open sheet 'Available_DD_Posts' to see live allocation counters. Available posts show GREEN. Blocked/Allotted posts turn GRAY.", 10, False, "000000"),
        ("6. Obliterated Posts Rehabilitation: Open sheet 'Obliterated_Rehab_Decisions' to allot active posts to the 84 serving officers on abolished posts (including Dr. Nirmalya Ranjan Sarkar at Sl. 48).", 10, False, "000000"),
        ("7. Official Secretariat 6-Column Order: Sheet 'Secretariat_Posting_Order' automatically compiles the official notification order with pay levels live as you make decisions!", 10, False, "000000"),
        ("8. Master Cadre Directory: Complete statewide directory of all 1,624 officers with HRMS IDs, designations, contact numbers, and superannuation dates.", 10, False, "000000"),
        ("9. Directorate HQ Deployed Roster: Complete record of all 37 officers physically stationed at Directorate Headquarters & Salt Lake attached units (including Dr. Sumit Chowdhury, Dr. Atanu Saha, Dr. Ayan Mukherjee, etc.) with verified DOJs and career posting timelines.", 10, False, "000000"),
        ("10. Excess & Unsanctioned Deployments: 135 officers deployed in field offices / HQ beyond the Notification 1809 sanctioned post limits.", 10, False, "000000"),
        ("", 10, False, "000000"),
        ("COLOR CODE LEGEND:", 12, True, "1E3A8A"),
        ("🟢 ALLOTTED DIRECT - Officer posted cleanly into clear substantive cadre vacancy (Soft Green).", 10, False, "065F46"),
        ("🔵 ALLOTTED WITH SU - Officer allotted substantive post + Service Utilization to an unblocked station (Soft Blue).", 10, False, "1E40AF"),
        ("🔴 ⚠️ SU COLLISION - The chosen SU post is occupied! Displaced officer automatically flagged for rehabilitation (Soft Rose).", 10, False, "9F1239"),
        ("🟡 PENDING - Awaiting administrative decision (Soft Amber).", 10, False, "92400E"),
        ("⚪ ALLOTTED / BLOCKED - Post has already been taken by an officer in the roster.", 10, False, "475569"),
        ("", 10, False, "000000"),
        ("OPTIONAL: GOOGLE APPS SCRIPT (AI AUTO-ALLOTMENT VIA GOOGLE AI STUDIO):", 12, True, "1E3A8A"),
        ("We provide a companion 'google_apps_script.js' file in your project. In Google Sheets, go to Extensions -> Apps Script, paste the code, and enter your Google AI Studio API key to get 1-click AI allotment recommendations with Gemini 2.0 / Flash right inside Google Sheets!", 10, False, "000000"),
    ]

    for r_idx, (text, sz, is_bold, color_hex) in enumerate(guide_lines, 1):
        cell = ws_guide.cell(row=r_idx, column=2, value=text)
        cell.font = Font(name="Calibri", size=sz, bold=is_bold, color=color_hex)
        if "GOVERNMENT" in text or "Animal Resources" in text:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    ws_guide.column_dimensions["A"].width = 4
    ws_guide.column_dimensions["B"].width = 110

    # =========================================================================
    # SHEET 4: Available_DD_Posts (Create first so formulas can reference it)
    # =========================================================================
    ws_dd = wb.create_sheet(title="Available_DD_Posts")
    ws_dd.views.sheetView[0].showGridLines = True

    dd_headers = [
        "Post ID", "Post Name & Station (Dropdown Identifier)", "Establishment", 
        "District", "Times Selected in Roster", "Availability Status", "Allotted Officer Name"
    ]
    for c_idx, h in enumerate(dd_headers, 1):
        cell = ws_dd.cell(row=1, column=c_idx, value=h)
        cell.fill = navy_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_dd.row_dimensions[1].height = 28

    c.execute("SELECT dd_sl, post_name, establishment, district FROM available_dd_posts WHERE is_blocked_vigilance = 0 ORDER BY dd_sl")
    dd_rows = c.fetchall()
    for idx, r in enumerate(dd_rows, 2):
        post_id = r["dd_sl"]
        dist = r["district"] or "HQ"
        estab = r["establishment"] or ""
        pname = r["post_name"] or "Deputy Director, ARD"
        label = f"[DD-{post_id}] {pname} ({estab}) - {dist}"

        ws_dd.cell(row=idx, column=1, value=post_id).alignment = Alignment(horizontal="center")
        ws_dd.cell(row=idx, column=2, value=label).font = bold_font
        ws_dd.cell(row=idx, column=3, value=estab)
        ws_dd.cell(row=idx, column=4, value=dist).alignment = Alignment(horizontal="center")
        
        # Formula: Count how many times selected in Roster Col M
        cnt_formula = f"=COUNTIF('50_Pt_Roster_Decisions'!$M$2:$M$243, B{idx})"
        ws_dd.cell(row=idx, column=5, value=cnt_formula).alignment = Alignment(horizontal="center")

        # Status Formula
        status_formula = f'=IF(E{idx}=0, "AVAILABLE", IF(E{idx}=1, "ALLOTTED", "⚠️ DUPLICATE ALLOTMENT!"))'
        ws_dd.cell(row=idx, column=6, value=status_formula).alignment = Alignment(horizontal="center")

        # Officer Name formula
        off_formula = f'=IF(E{idx}>0, IFERROR(INDEX(\'50_Pt_Roster_Decisions\'!$E$2:$E$243, MATCH(B{idx}, \'50_Pt_Roster_Decisions\'!$M$2:$M$243, 0)), "-"), "-")'
        ws_dd.cell(row=idx, column=7, value=off_formula)

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 8):
            cell = ws_dd.cell(row=idx, column=c_idx)
            cell.border = cell_border
            if c_idx not in [2, 6]:
                cell.fill = fill_color
            cell.font = normal_font if c_idx != 2 else bold_font
        ws_dd.row_dimensions[idx].height = 20

    # =========================================================================
    # SHEET 5: Available_AD_Vacancies (for Obliterated Posts absorption)
    # =========================================================================
    ws_ad = wb.create_sheet(title="Available_AD_Vacancies")
    ws_ad.views.sheetView[0].showGridLines = True

    ad_headers = [
        "Post ID", "Post Name & Station (Dropdown Identifier)", "Establishment", 
        "District", "Times Selected", "Availability Status", "Allotted Officer Name"
    ]
    for c_idx, h in enumerate(ad_headers, 1):
        cell = ws_ad.cell(row=1, column=c_idx, value=h)
        cell.fill = teal_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_ad.row_dimensions[1].height = 28

    c.execute("""
        SELECT id, post_sl, designation, establishment, district 
        FROM cadre_1794_posts 
        WHERE occupancy_status = 'Clear Vacancy' AND (designation LIKE '%Assistant Director%' OR pay_level = 'Level-16')
        ORDER BY post_sl
    """)
    ad_rows = c.fetchall()
    for idx, r in enumerate(ad_rows, 2):
        pid = r["id"]
        psl = r["post_sl"]
        desig = r["designation"]
        estab = r["establishment"] or ""
        dist = r["district"] or "HQ"
        label = f"[AD-{psl}] {desig} ({estab}) - {dist}"

        ws_ad.cell(row=idx, column=1, value=psl).alignment = Alignment(horizontal="center")
        ws_ad.cell(row=idx, column=2, value=label).font = bold_font
        ws_ad.cell(row=idx, column=3, value=estab)
        ws_ad.cell(row=idx, column=4, value=dist).alignment = Alignment(horizontal="center")

        cnt_formula = f"=COUNTIF('Obliterated_Rehab_Decisions'!$J$2:$J$107, B{idx})"
        ws_ad.cell(row=idx, column=5, value=cnt_formula).alignment = Alignment(horizontal="center")

        status_formula = f'=IF(E{idx}=0, "AVAILABLE", IF(E{idx}=1, "ALLOTTED", "⚠️ DUPLICATE!"))'
        ws_ad.cell(row=idx, column=6, value=status_formula).alignment = Alignment(horizontal="center")

        off_formula = f'=IF(E{idx}>0, IFERROR(INDEX(\'Obliterated_Rehab_Decisions\'!$F$2:$F$107, MATCH(B{idx}, \'Obliterated_Rehab_Decisions\'!$J$2:$J$107, 0)), "-"), "-")'
        ws_ad.cell(row=idx, column=7, value=off_formula)

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 8):
            cell = ws_ad.cell(row=idx, column=c_idx)
            cell.border = cell_border
            if c_idx not in [2, 6]:
                cell.fill = fill_color
            cell.font = normal_font if c_idx != 2 else bold_font
        ws_ad.row_dimensions[idx].height = 20

    # =========================================================================
    # SHEET 6: SU_Post_Picker (All 1,794 Posts for Lookup)
    # =========================================================================
    ws_su = wb.create_sheet(title="SU_Post_Picker")
    ws_su.views.sheetView[0].showGridLines = True

    su_headers = [
        "Post Label (Dropdown Source)", "Designation & Office", "Occupancy Status", 
        "Current Incumbent & HRMS", "District", "Pay Level", "Post ID"
    ]
    for c_idx, h in enumerate(su_headers, 1):
        cell = ws_su.cell(row=1, column=c_idx, value=h)
        cell.fill = slate_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_su.row_dimensions[1].height = 28

    c.execute("""
        SELECT post_sl, designation, establishment, district, occupancy_status, incumbent_name, incumbent_hrms, pay_level 
        FROM cadre_1794_posts 
        ORDER BY post_sl
    """)
    all_cadre = c.fetchall()
    for idx, r in enumerate(all_cadre, 2):
        psl = r["post_sl"]
        desig = r["designation"]
        estab = r["establishment"] or ""
        dist = r["district"] or "HQ"
        occ = r["occupancy_status"] or "Clear Vacancy"
        inc_name = r["incumbent_name"] or "None"
        inc_hrms = r["incumbent_hrms"] or ""
        inc_str = f"{inc_name} ({inc_hrms})" if inc_hrms else ("Vacant" if occ == "Clear Vacancy" else inc_name)
        label = f"[{psl}] {desig}, {estab} ({dist})"

        ws_su.cell(row=idx, column=1, value=label).font = bold_font
        ws_su.cell(row=idx, column=2, value=f"{desig} - {estab}")
        ws_su.cell(row=idx, column=3, value=occ).alignment = Alignment(horizontal="center")
        ws_su.cell(row=idx, column=4, value=inc_str)
        ws_su.cell(row=idx, column=5, value=dist).alignment = Alignment(horizontal="center")
        ws_su.cell(row=idx, column=6, value=r["pay_level"]).alignment = Alignment(horizontal="center")
        ws_su.cell(row=idx, column=7, value=psl).alignment = Alignment(horizontal="center")

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 8):
            cell = ws_su.cell(row=idx, column=c_idx)
            cell.border = cell_border
            if c_idx != 3:
                cell.fill = fill_color
            cell.font = normal_font if c_idx != 1 else bold_font
        ws_su.row_dimensions[idx].height = 19

    # =========================================================================
    # SHEET 2: 50_Pt_Roster_Decisions (Main User Decision Sheet)
    # =========================================================================
    ws_roster = wb.create_sheet(title="50_Pt_Roster_Decisions")
    ws_roster.views.sheetView[0].showGridLines = True

    roster_headers = [
        "Sl", "Pt", "Quota", "HRMS ID", "Officer Name", 
        "Present Designation", "Present Block", "Present District", "DOR (Retirement)",
        "Stated Pref 1", "Stated Pref 2", "Stated Pref 3",
        "Allotted Substantive Post (Choose Dropdown)", 
        "Enable SU? (NO / YES)", 
        "Service Utilization (SU) Post (Choose Dropdown)",
        "Allotment Status", 
        "Collision Alert / Displaced Officer",
        "Statutory Category", 
        "Present Pay Level", 
        "New Pay Level"
    ]
    for c_idx, h in enumerate(roster_headers, 1):
        cell = ws_roster.cell(row=1, column=c_idx, value=h)
        if c_idx in [13, 14, 15]:
            cell.fill = indigo_header_fill # Action columns in Indigo
        elif c_idx in [16, 17]:
            cell.fill = amber_header_fill # Alert columns in Amber
        else:
            cell.fill = navy_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_roster.row_dimensions[1].height = 32

    c.execute("""
        SELECT sl_no, roster_point, point_reserved_for, hrms_id, officer_name, 
               present_posting, present_block, present_district, service_ends, 
               pref_1, pref_2, pref_3,
               substantive_post_name, su_post_name, allotment_status
        FROM roster_50_point_candidates 
        ORDER BY sl_no
    """)
    roster_rows = c.fetchall()

    total_roster = len(roster_rows)
    for idx, r in enumerate(roster_rows, 2):
        ws_roster.cell(row=idx, column=1, value=r["sl_no"]).alignment = Alignment(horizontal="center")
        ws_roster.cell(row=idx, column=2, value=r["roster_point"]).alignment = Alignment(horizontal="center")
        ws_roster.cell(row=idx, column=3, value=r["point_reserved_for"]).alignment = Alignment(horizontal="center")
        ws_roster.cell(row=idx, column=4, value=r["hrms_id"]).alignment = Alignment(horizontal="center")
        
        name_cell = ws_roster.cell(row=idx, column=5, value=r["officer_name"])
        name_cell.font = bold_font
        
        ws_roster.cell(row=idx, column=6, value=r["present_posting"])
        ws_roster.cell(row=idx, column=7, value=r["present_block"] or "-")
        ws_roster.cell(row=idx, column=8, value=r["present_district"] or "-")
        ws_roster.cell(row=idx, column=9, value=r["service_ends"] or "-").alignment = Alignment(horizontal="center")
        
        p1 = r["pref_1"] or ""
        p2 = r["pref_2"] or ""
        p3 = r["pref_3"] or ""
        ws_roster.cell(row=idx, column=10, value=p1).font = italic_font
        ws_roster.cell(row=idx, column=11, value=p2).font = italic_font
        ws_roster.cell(row=idx, column=12, value=p3).font = italic_font

        # Populate confirmed decisions from DB if present
        sub_name = r["substantive_post_name"] or ""
        su_name = r["su_post_name"] or ""
        has_su = "YES" if su_name else "NO"

        ws_roster.cell(row=idx, column=13, value=sub_name).font = bold_font
        ws_roster.cell(row=idx, column=14, value=has_su).alignment = Alignment(horizontal="center", vertical="center")
        ws_roster.cell(row=idx, column=15, value=su_name).font = bold_font

        # Status Formula
        status_formula = (
            f'=IF(ISBLANK(M{idx}), "PENDING", '
            f'IF(N{idx}="YES", '
            f'IF(IFERROR(VLOOKUP(O{idx}, SU_Post_Picker!$A$2:$C$1795, 3, FALSE), "")="Occupied", "⚠️ SU COLLISION", "ALLOTTED WITH SU"), '
            f'"ALLOTTED DIRECT"))'
        )
        ws_roster.cell(row=idx, column=16, value=status_formula).alignment = Alignment(horizontal="center", vertical="center")

        # Collision / Displaced Formula
        collision_formula = (
            f'=IF(AND(N{idx}="YES", NOT(ISBLANK(O{idx}))), '
            f'IF(IFERROR(VLOOKUP(O{idx}, SU_Post_Picker!$A$2:$D$1795, 3, FALSE), "")="Occupied", '
            f'"⚠️ DISPLACES: " & IFERROR(VLOOKUP(O{idx}, SU_Post_Picker!$A$2:$D$1795, 4, FALSE), "Unknown") & " (Move to Displaced Pool)", '
            f'"Clear Vacancy / Clean SU"), '
            f'IF(ISBLANK(M{idx}), "Awaiting Selection", "Direct Cadre Placement"))'
        )
        ws_roster.cell(row=idx, column=17, value=collision_formula)

        ws_roster.cell(row=idx, column=18, value="Promotion under WBS (ROPA) 2019")
        ws_roster.cell(row=idx, column=19, value="Level 16").alignment = Alignment(horizontal="center")
        ws_roster.cell(row=idx, column=20, value="Level 19 (Rs. 95,100 - Rs. 1,48,000)").alignment = Alignment(horizontal="center")

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 21):
            cell = ws_roster.cell(row=idx, column=c_idx)
            cell.border = cell_border
            if c_idx not in [13, 14, 15, 16, 17]:
                cell.fill = fill_color
        ws_roster.row_dimensions[idx].height = 22

    # Data Validations on Roster Sheet
    dv_dd_roster = DataValidation(type="list", formula1="'Available_DD_Posts'!$B$2:$B$243", allow_blank=True)
    ws_roster.add_data_validation(dv_dd_roster)
    dv_dd_roster.add(f"M2:M{total_roster + 1}")

    dv_su_toggle = DataValidation(type="list", formula1='"NO,YES"', allow_blank=True)
    ws_roster.add_data_validation(dv_su_toggle)
    dv_su_toggle.add(f"N2:N{total_roster + 1}")

    dv_su_roster = DataValidation(type="list", formula1="'SU_Post_Picker'!$A$2:$A$1795", allow_blank=True)
    ws_roster.add_data_validation(dv_su_roster)
    dv_su_roster.add(f"O2:O{total_roster + 1}")

    # =========================================================================
    # SHEET 3: Obliterated_Rehab_Decisions (106 Abolished Posts, 84 Serving)
    # =========================================================================
    ws_oblit = wb.create_sheet(title="Obliterated_Rehab_Decisions")
    ws_oblit.views.sheetView[0].showGridLines = True

    oblit_headers = [
        "Sl", "Old Abolished Post (Memo 1808)", "Establishment / Office", "Block", "District",
        "Serving Incumbent Officer", "HRMS ID", "Station Tenure", "Post Status",
        "Allotted Active Substantive Post (Choose Dropdown)",
        "Enable SU? (NO / YES)",
        "Service Utilization (SU) Post (Choose Dropdown)",
        "Rehabilitation Status",
        "Collision Alert / Displaced Officer",
        "Statutory Category",
        "Present Pay Level",
        "New Pay Level"
    ]
    for c_idx, h in enumerate(oblit_headers, 1):
        cell = ws_oblit.cell(row=1, column=c_idx, value=h)
        if c_idx in [10, 11, 12]:
            cell.fill = indigo_header_fill
        elif c_idx in [13, 14]:
            cell.fill = amber_header_fill
        else:
            cell.fill = teal_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_oblit.row_dimensions[1].height = 32

    c.execute("""
        SELECT oblit_sl, post_name, establishment, block, district, 
               officer_name, hrms_id, tenure, is_vacant,
               substantive_post_name, su_post_name, rehabilitation_status
        FROM obliterated_posts_1808 
        ORDER BY oblit_sl
    """)
    oblit_rows = c.fetchall()
    total_oblit = len(oblit_rows)

    for idx, r in enumerate(oblit_rows, 2):
        ws_oblit.cell(row=idx, column=1, value=r["oblit_sl"]).alignment = Alignment(horizontal="center")
        ws_oblit.cell(row=idx, column=2, value=r["post_name"]).font = bold_font
        ws_oblit.cell(row=idx, column=3, value=r["establishment"] or "-")
        ws_oblit.cell(row=idx, column=4, value=r["block"] or "-")
        ws_oblit.cell(row=idx, column=5, value=r["district"] or "-")
        
        inc_name = r["officer_name"] or "None (Vacant Abolished)"
        ws_oblit.cell(row=idx, column=6, value=inc_name).font = bold_font if r["officer_name"] else italic_font
        ws_oblit.cell(row=idx, column=7, value=r["hrms_id"] or "-").alignment = Alignment(horizontal="center")
        ws_oblit.cell(row=idx, column=8, value=r["tenure"] or "-").alignment = Alignment(horizontal="center")
        
        post_stat = "Serving Incumbent" if not r["is_vacant"] else "Vacant Abolished"
        ws_oblit.cell(row=idx, column=9, value=post_stat).alignment = Alignment(horizontal="center")

        # Substantive & SU Selections
        sub_name_ob = r["substantive_post_name"] or ""
        su_name_ob = r["su_post_name"] or ""
        has_su_ob = "YES" if su_name_ob else "NO"

        ws_oblit.cell(row=idx, column=10, value=sub_name_ob).font = bold_font
        ws_oblit.cell(row=idx, column=11, value=has_su_ob).alignment = Alignment(horizontal="center")
        ws_oblit.cell(row=idx, column=12, value=su_name_ob).font = bold_font

        # Status Formula
        status_formula = (
            f'=IF(G{idx}="-", "VACANT POST (NO REHAB REQUIRED)", '
            f'IF(ISBLANK(J{idx}), "PENDING REHABILITATION", '
            f'IF(K{idx}="YES", '
            f'IF(IFERROR(VLOOKUP(L{idx}, SU_Post_Picker!$A$2:$C$1795, 3, FALSE), "")="Occupied", "⚠️ SU COLLISION", "REHABILITATED WITH SU"), '
            f'"REHABILITATED DIRECT")))'
        )
        ws_oblit.cell(row=idx, column=13, value=status_formula).alignment = Alignment(horizontal="center")

        # Collision Formula
        col_formula = (
            f'=IF(AND(K{idx}="YES", NOT(ISBLANK(L{idx}))), '
            f'IF(IFERROR(VLOOKUP(L{idx}, SU_Post_Picker!$A$2:$D$1795, 3, FALSE), "")="Occupied", '
            f'"⚠️ DISPLACES: " & IFERROR(VLOOKUP(L{idx}, SU_Post_Picker!$A$2:$D$1795, 4, FALSE), "Unknown") & " (Move to Displaced Pool)", '
            f'"Clear Vacancy / Clean SU"), '
            f'IF(G{idx}="-", "-", IF(ISBLANK(J{idx}), "Awaiting Active Cadre Post", "Direct Cadre Absorption")))'
        )
        ws_oblit.cell(row=idx, column=14, value=col_formula)

        ws_oblit.cell(row=idx, column=15, value="Cadre Absorption under Restructuring")
        ws_oblit.cell(row=idx, column=16, value="Level 16").alignment = Alignment(horizontal="center")
        ws_oblit.cell(row=idx, column=17, value="Level 16 (Preserved Scale)").alignment = Alignment(horizontal="center")

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 18):
            cell = ws_oblit.cell(row=idx, column=c_idx)
            cell.border = cell_border
            if c_idx not in [10, 11, 12, 13, 14]:
                cell.fill = fill_color
        ws_oblit.row_dimensions[idx].height = 22

    # Data Validations on Obliterated Sheet
    dv_ad_oblit = DataValidation(type="list", formula1="'Available_AD_Vacancies'!$B$2:$B$158", allow_blank=True)
    ws_oblit.add_data_validation(dv_ad_oblit)
    dv_ad_oblit.add(f"J2:J{total_oblit + 1}")

    dv_su_oblit_toggle = DataValidation(type="list", formula1='"NO,YES"', allow_blank=True)
    ws_oblit.add_data_validation(dv_su_oblit_toggle)
    dv_su_oblit_toggle.add(f"K2:K{total_oblit + 1}")

    dv_su_oblit = DataValidation(type="list", formula1="'SU_Post_Picker'!$A$2:$A$1795", allow_blank=True)
    ws_oblit.add_data_validation(dv_su_oblit)
    dv_su_oblit.add(f"L2:L{total_oblit + 1}")

    # =========================================================================
    # SHEET 7: Displaced_Queue_Tracker (Tracking collisions & displaced officers)
    # =========================================================================
    ws_disp = wb.create_sheet(title="Displaced_Queue_Tracker")
    ws_disp.views.sheetView[0].showGridLines = True

    disp_headers = [
        "Sl", "Displaced Officer Name", "HRMS ID", "Original Post Occupied", 
        "Station & District", "Displaced By (Incoming Doctor & Event)", 
        "Pay Level", "Rehabilitation Action / Status"
    ]
    for c_idx, h in enumerate(disp_headers, 1):
        cell = ws_disp.cell(row=1, column=c_idx, value=h)
        cell.fill = amber_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_disp.row_dimensions[1].height = 28

    c.execute("""
        SELECT officer_hrms, officer_name, from_post_name, district, 
               displaced_by_name, displaced_by_hrms, displaced_by_reason, pay_level, rehabilitation_status
        FROM displaced_officers_pool
        ORDER BY id
    """)
    disp_rows = c.fetchall()
    if not disp_rows:
        ws_disp.cell(row=2, column=2, value="No officers currently displaced. Officers displaced by SU collisions will log here automatically.").font = italic_font
    else:
        for idx, r in enumerate(disp_rows, 2):
            ws_disp.cell(row=idx, column=1, value=idx - 1).alignment = Alignment(horizontal="center")
            ws_disp.cell(row=idx, column=2, value=r["officer_name"]).font = bold_font
            ws_disp.cell(row=idx, column=3, value=r["officer_hrms"]).alignment = Alignment(horizontal="center")
            ws_disp.cell(row=idx, column=4, value=r["from_post_name"])
            ws_disp.cell(row=idx, column=5, value=r["district"]).alignment = Alignment(horizontal="center")
            disp_by = f"{r['displaced_by_name']} ({r['displaced_by_hrms']}) — {r['displaced_by_reason']}"
            ws_disp.cell(row=idx, column=6, value=disp_by)
            ws_disp.cell(row=idx, column=7, value=r["pay_level"] or "Level-16 / 19").alignment = Alignment(horizontal="center")
            ws_disp.cell(row=idx, column=8, value=r["rehabilitation_status"]).alignment = Alignment(horizontal="center")

            fill_color = zebra_fill if idx % 2 == 0 else plain_fill
            for c_idx in range(1, 9):
                cell = ws_disp.cell(row=idx, column=c_idx)
                cell.border = cell_border
                cell.fill = fill_color
            ws_disp.row_dimensions[idx].height = 20

    # Section 2: Group C Cascading Replacement Warnings (Field Posts Requiring Urgent Backfill)
    start_c_row = ws_disp.max_row + 3
    ws_disp.cell(row=start_c_row, column=1, value="GROUP C: CASCADING REPLACEMENT WARNINGS (FIELD POSTS REQUIRING IMMEDIATE BACKFILL)").font = Font(name="Calibri", size=12, bold=True, color="991B1B")
    ws_disp.merge_cells(f"A{start_c_row}:H{start_c_row}")
    
    c_header_row = start_c_row + 1
    casc_headers = [
        "Sl", "Transferred Out Officer", "HRMS ID", "Vacated Field Post (Must Backfill)", 
        "District", "New Promotional / Transfer Post", "Pay Level", "Action Required / Warning"
    ]
    red_header_fill = PatternFill(start_color="991B1B", end_color="991B1B", fill_type="solid")
    red_row_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    red_font = Font(name="Calibri", size=10, bold=True, color="991B1B")

    for c_idx, h in enumerate(casc_headers, 1):
        cell = ws_disp.cell(row=c_header_row, column=c_idx, value=h)
        cell.fill = red_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_disp.row_dimensions[c_header_row].height = 28

    c.execute("""
        SELECT r.hrms_id, r.officer_name, r.present_posting, r.present_district,
               r.substantive_post_name, e.attention_reason
        FROM roster_50_point_candidates r
        JOIN officer_extended_dossier e ON r.hrms_id = e.hrms_id
        WHERE e.needs_backfill = 1
        ORDER BY r.present_district, r.officer_name
    """)
    casc_rows = c.fetchall()
    for c_idx, cr in enumerate(casc_rows, 1):
        target_r = c_header_row + c_idx
        ws_disp.cell(row=target_r, column=1, value=c_idx).alignment = Alignment(horizontal="center")
        ws_disp.cell(row=target_r, column=2, value=cr["officer_name"]).font = bold_font
        ws_disp.cell(row=target_r, column=3, value=cr["hrms_id"]).alignment = Alignment(horizontal="center")
        ws_disp.cell(row=target_r, column=4, value=cr["present_posting"]).font = red_font
        ws_disp.cell(row=target_r, column=5, value=cr["present_district"]).alignment = Alignment(horizontal="center")
        ws_disp.cell(row=target_r, column=6, value=cr["substantive_post_name"])
        ws_disp.cell(row=target_r, column=7, value="Level 16 -> 19").alignment = Alignment(horizontal="center")
        ws_disp.cell(row=target_r, column=8, value="⚠️ VACATED FIELD POST - MUST BE BACKFILLED IMMEDIATELY").font = red_font
        
        for col_i in range(1, 9):
            cell = ws_disp.cell(row=target_r, column=col_i)
            cell.border = cell_border
            cell.fill = red_row_fill
        ws_disp.row_dimensions[target_r].height = 22

    # =========================================================================
    # SHEET 8: Secretariat_Posting_Order (Exact 6 Columns Requested by User)
    # =========================================================================
    ws_order = wb.create_sheet(title="Secretariat_Posting_Order")
    ws_order.views.sheetView[0].showGridLines = True

    # Government Title Header
    ws_order.merge_cells("A1:F1")
    ws_order.merge_cells("A2:F2")
    ws_order.merge_cells("A3:F3")
    ws_order.merge_cells("A4:F4")

    ws_order.cell(row=1, column=1, value="GOVERNMENT OF WEST BENGAL").font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    ws_order.cell(row=2, column=1, value="Animal Resources Development Department").font = Font(name="Calibri", size=12, bold=True, color="0F766E")
    ws_order.cell(row=3, column=1, value="AR & AH Branch, Prani Sampad Bhawan, LB - 2, Sector - III, Salt Lake, Kolkata - 700 106").font = Font(name="Calibri", size=10, italic=True)
    ws_order.cell(row=4, column=1, value="NOTIFICATION / POSTING SCHEDULE (WBS ROPA RULES 2019)").font = Font(name="Calibri", size=11, bold=True, color="1E293B")

    for r_idx in range(1, 5):
        ws_order.cell(row=r_idx, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws_order.row_dimensions[r_idx].height = 20

    ws_order.row_dimensions[5].height = 8 # Spacing

    # Exact 6 Columns
    sec_headers = [
        "Sl No",
        "Name of the Officers with present place of posting",
        "Present pay level",
        "Transfer by",
        "Place of posting on promotion / transfer/utilization of service",
        "Pay level upon transfer"
    ]
    for c_idx, h in enumerate(sec_headers, 1):
        cell = ws_order.cell(row=6, column=c_idx, value=h)
        cell.fill = navy_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_order.row_dimensions[6].height = 36

    # Dynamically mirror 242 promotees from 50_Pt_Roster_Decisions
    for idx in range(2, total_roster + 2):
        target_r = idx + 5 # row 7 onwards
        r_sl = idx - 1

        ws_order.cell(row=target_r, column=1, value=r_sl).alignment = Alignment(horizontal="center", vertical="center")
        
        # Officer Name + Present Posting
        name_posting_formula = (
            f'=IF(ISBLANK(\'50_Pt_Roster_Decisions\'!E{idx}), "", '
            f'\'50_Pt_Roster_Decisions\'!E{idx} & " (" & \'50_Pt_Roster_Decisions\'!D{idx} & ") — " & '
            f'\'50_Pt_Roster_Decisions\'!F{idx} & ", " & \'50_Pt_Roster_Decisions\'!G{idx} & ", " & \'50_Pt_Roster_Decisions\'!H{idx})'
        )
        ws_order.cell(row=target_r, column=2, value=name_posting_formula).alignment = Alignment(horizontal="left", vertical="center")

        # Present pay level
        ws_order.cell(row=target_r, column=3, value=f"='50_Pt_Roster_Decisions'!S{idx}").alignment = Alignment(horizontal="center", vertical="center")

        # Transfer by
        ws_order.cell(row=target_r, column=4, value=f"='50_Pt_Roster_Decisions'!R{idx}").alignment = Alignment(horizontal="center", vertical="center")

        # Place of posting on promotion / transfer / utilization of service
        new_posting_formula = (
            f'=IF(ISBLANK(\'50_Pt_Roster_Decisions\'!M{idx}), "PENDING ALLOTMENT", '
            f'IF(\'50_Pt_Roster_Decisions\'!N{idx}="YES", '
            f'\'50_Pt_Roster_Decisions\'!M{idx} & " [Service Utilization: " & \'50_Pt_Roster_Decisions\'!O{idx} & "]", '
            f'\'50_Pt_Roster_Decisions\'!M{idx}))'
        )
        ws_order.cell(row=target_r, column=5, value=new_posting_formula).alignment = Alignment(horizontal="left", vertical="center")

        # Pay level upon transfer
        ws_order.cell(row=target_r, column=6, value=f"='50_Pt_Roster_Decisions'!T{idx}").alignment = Alignment(horizontal="center", vertical="center")

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 7):
            cell = ws_order.cell(row=target_r, column=c_idx)
            cell.border = cell_border
            cell.fill = fill_color
            cell.font = bold_font if c_idx in [1, 2, 5] else normal_font
        ws_order.row_dimensions[target_r].height = 24

    # Part 2: Executive Realignment & Lateral Transfer Schedule (18 Named Cadre Posts)
    start_sec2 = ws_order.max_row + 2
    ws_order.merge_cells(f"A{start_sec2}:F{start_sec2}")
    sec2_title = ws_order.cell(row=start_sec2, column=1, value="SCHEDULE B: LATERAL TRANSFERS, SERVICE UTILIZATION & CADRE REALIGNMENTS")
    sec2_title.font = Font(name="Calibri", size=11, bold=True, color="0F766E")
    sec2_title.alignment = Alignment(horizontal="center", vertical="center")
    ws_order.row_dimensions[start_sec2].height = 24
    
    sec2_hdr_row = start_sec2 + 1
    for c_idx, h in enumerate(sec_headers, 1):
        cell = ws_order.cell(row=sec2_hdr_row, column=c_idx, value=h)
        cell.fill = teal_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_order.row_dimensions[sec2_hdr_row].height = 28

    c.execute("""
        SELECT sl_no, officer_name, hrms_id, present_posting, transferred_post_name, transfer_type, reason_notes
        FROM executive_lateral_transfers
        ORDER BY sl_no ASC
    """)
    exec_transfers_db = c.fetchall()

    for ex_idx, r in enumerate(exec_transfers_db, 1):
        tr = sec2_hdr_row + ex_idx
        ex_name = f"{r['officer_name']} ({r['hrms_id']}) — {r['present_posting']}"
        ex_pl = "Level 16"
        ex_tb = r['transfer_type']
        ex_place = f"{r['transferred_post_name']} [{r['reason_notes']}]"
        ex_npl = "Level 16"

        ws_order.cell(row=tr, column=1, value=ex_idx).alignment = Alignment(horizontal="center", vertical="center")
        ws_order.cell(row=tr, column=2, value=ex_name).alignment = Alignment(horizontal="left", vertical="center")
        ws_order.cell(row=tr, column=3, value=ex_pl).alignment = Alignment(horizontal="center", vertical="center")
        ws_order.cell(row=tr, column=4, value=ex_tb).alignment = Alignment(horizontal="center", vertical="center")
        ws_order.cell(row=tr, column=5, value=ex_place).alignment = Alignment(horizontal="left", vertical="center")
        ws_order.cell(row=tr, column=6, value=ex_npl).alignment = Alignment(horizontal="center", vertical="center")
        
        fill_color = zebra_fill if ex_idx % 2 == 0 else plain_fill
        for col_i in range(1, 7):
            c_cell = ws_order.cell(row=tr, column=col_i)
            c_cell.border = cell_border
            c_cell.fill = fill_color
            c_cell.font = bold_font if col_i in [1, 2, 5] else normal_font
        ws_order.row_dimensions[tr].height = 24

    # =========================================================================
    # SHEET 8B: 4_Column_Posting_Order (Exact 4-Column Official Table Requested by User)
    # Col 1: Sl no.
    # Col 2: Name of the Officers with Present posting
    # Col 3: Place of posting on promotion / Transfer (Substantive post)
    # Col 4: Service Utilized post (if any)
    # Border: Single black line borders only, simple, to the point
    # =========================================================================
    ws_4col = wb.create_sheet(title="4_Column_Posting_Order")
    ws_4col.views.sheetView[0].showGridLines = True

    black_thin = Side(border_style="thin", color="000000")
    black_border = Border(left=black_thin, right=black_thin, top=black_thin, bottom=black_thin)
    black_hdr_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    sec_hdr_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    order_4col_font = Font(name="Times New Roman", size=10, color="000000")
    order_4col_bold = Font(name="Times New Roman", size=10, bold=True, color="000000")
    order_4col_hdr_font = Font(name="Times New Roman", size=10.5, bold=True, color="000000")

    # Title block
    ws_4col.merge_cells("A1:D1")
    ws_4col.merge_cells("A2:D2")
    ws_4col.merge_cells("A3:D3")
    ws_4col.merge_cells("A4:D4")

    ws_4col.cell(row=1, column=1, value="GOVERNMENT OF WEST BENGAL").font = Font(name="Times New Roman", size=13, bold=True, color="000000")
    ws_4col.cell(row=2, column=1, value="Animal Resources Development Department").font = Font(name="Times New Roman", size=11, bold=True, color="000000")
    ws_4col.cell(row=3, column=1, value="AR & AH Branch, Prani Sampad Bhawan, LB-2, Sector-III, Salt Lake, Kolkata - 700 106").font = Font(name="Times New Roman", size=9.5, italic=True, color="000000")
    ws_4col.cell(row=4, column=1, value="NOTIFICATION (MEMO NO. 1890-AR&AH / DATED 12.09.2026)").font = Font(name="Times New Roman", size=10.5, bold=True, color="000000")

    for r_idx in range(1, 5):
        ws_4col.cell(row=r_idx, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws_4col.row_dimensions[r_idx].height = 20

    ws_4col.merge_cells("A5:D5")
    ws_4col.cell(row=5, column=1, value="Note on Postings: Pure White Background = Confirmed Executive Allocation | Very Light Grey Background = AI Cadre System Recommended Posting").font = Font(name="Times New Roman", size=9.5, italic=True, color="475569")
    ws_4col.cell(row=5, column=1).alignment = Alignment(horizontal="center", vertical="center")
    ws_4col.row_dimensions[5].height = 20

    col4_headers = [
        "Sl no.",
        "Name of the Officers with Present posting",
        "Place of posting on promotion / Transfer (Substantive post)",
        "Service Utilized post (if any)"
    ]

    light_grey_row_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    white_row_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    def write_4col_header(ws, row_idx):
        for c_idx, h in enumerate(col4_headers, 1):
            cell = ws.cell(row=row_idx, column=c_idx, value=h)
            cell.fill = black_hdr_fill
            cell.font = order_4col_hdr_font
            cell.alignment = Alignment(horizontal="center" if c_idx == 1 else "left", vertical="center", wrap_text=True)
            cell.border = black_border
        ws.row_dimensions[row_idx].height = 28

    cur_row = 6

    # Schedule I: Promotion to DD (242 Promotees)
    ws_4col.merge_cells(f"A{cur_row}:D{cur_row}")
    s1_title = ws_4col.cell(row=cur_row, column=1, value="Schedule I: Promotion to the post of Deputy Director, ARD (Pay Level 19)")
    s1_title.font = Font(name="Times New Roman", size=11, bold=True, color="000000")
    s1_title.alignment = Alignment(horizontal="center", vertical="center")
    s1_title.fill = sec_hdr_fill
    for ci in range(1, 5):
        ws_4col.cell(row=cur_row, column=ci).border = black_border
    ws_4col.row_dimensions[cur_row].height = 24
    cur_row += 1

    write_4col_header(ws_4col, cur_row)
    cur_row += 1

    c.execute("""
        SELECT sl_no, officer_name, present_posting, substantive_post_name, su_post_name, is_manual_recommendation
        FROM roster_50_point_candidates
        ORDER BY sl_no ASC
    """)
    for r in c.fetchall():
        sl_val = r['sl_no']
        c2_val = clean_pres(r['officer_name'], r['present_posting'])
        c3_val = clean_sub(r['substantive_post_name'])
        c4_val = clean_su(r['su_post_name'])
        is_m = bool(r['is_manual_recommendation'])
        row_fill = white_row_fill if is_m else light_grey_row_fill

        ws_4col.cell(row=cur_row, column=1, value=sl_val).alignment = Alignment(horizontal="center", vertical="center")
        ws_4col.cell(row=cur_row, column=2, value=c2_val).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws_4col.cell(row=cur_row, column=3, value=c3_val).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws_4col.cell(row=cur_row, column=4, value=c4_val).alignment = Alignment(horizontal="center" if c4_val == "Nil" else "left", vertical="center", wrap_text=True)

        for col_i in range(1, 5):
            cell = ws_4col.cell(row=cur_row, column=col_i)
            cell.border = black_border
            cell.fill = row_fill
            cell.font = order_4col_bold if (col_i == 1 or (col_i == 4 and c4_val != "Nil")) else order_4col_font
        ws_4col.row_dimensions[cur_row].height = 22
        cur_row += 1

    # Schedule II: Serving Officers on Abolished Posts (61 Officers)
    cur_row += 1
    ws_4col.merge_cells(f"A{cur_row}:D{cur_row}")
    s2_title = ws_4col.cell(row=cur_row, column=1, value="Schedule II: Rehabilitation and Posting of Serving Officers from Abolished / Restructured Posts")
    s2_title.font = Font(name="Times New Roman", size=11, bold=True, color="000000")
    s2_title.alignment = Alignment(horizontal="center", vertical="center")
    s2_title.fill = sec_hdr_fill
    for ci in range(1, 5):
        ws_4col.cell(row=cur_row, column=ci).border = black_border
    ws_4col.row_dimensions[cur_row].height = 24
    cur_row += 1

    write_4col_header(ws_4col, cur_row)
    cur_row += 1

    c.execute("""
        SELECT oblit_sl, officer_name, post_name, district, establishment, substantive_post_name, su_post_name, is_manual_recommendation
        FROM obliterated_posts_1808
        WHERE is_vacant = 'No' AND (is_on_roster = 0 OR is_on_roster IS NULL)
        ORDER BY oblit_sl ASC
    """)
    for idx, r in enumerate(c.fetchall(), 1):
        sl_val = idx
        pres_str = f"{r['post_name']}, {r['establishment'] or r['district']}"
        c2_val = clean_pres(r['officer_name'], pres_str)
        c3_val = clean_sub(r['substantive_post_name'])
        c4_val = clean_su(r['su_post_name'])
        is_m = bool(r['is_manual_recommendation'])
        row_fill = white_row_fill if is_m else light_grey_row_fill

        ws_4col.cell(row=cur_row, column=1, value=sl_val).alignment = Alignment(horizontal="center", vertical="center")
        ws_4col.cell(row=cur_row, column=2, value=c2_val).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws_4col.cell(row=cur_row, column=3, value=c3_val).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws_4col.cell(row=cur_row, column=4, value=c4_val).alignment = Alignment(horizontal="center" if c4_val == "Nil" else "left", vertical="center", wrap_text=True)

        for col_i in range(1, 5):
            cell = ws_4col.cell(row=cur_row, column=col_i)
            cell.border = black_border
            cell.fill = row_fill
            cell.font = order_4col_bold if (col_i == 1 or (col_i == 4 and c4_val != "Nil")) else order_4col_font
        ws_4col.row_dimensions[cur_row].height = 22
        cur_row += 1

    # Schedule III: Lateral & Field Transfers
    cur_row += 1
    ws_4col.merge_cells(f"A{cur_row}:D{cur_row}")
    s3_title = ws_4col.cell(row=cur_row, column=1, value="Schedule III: Consequential Lateral Transfers & Inter-District Field Postings")
    s3_title.font = Font(name="Times New Roman", size=11, bold=True, color="000000")
    s3_title.alignment = Alignment(horizontal="center", vertical="center")
    s3_title.fill = sec_hdr_fill
    for ci in range(1, 5):
        ws_4col.cell(row=cur_row, column=ci).border = black_border
    ws_4col.row_dimensions[cur_row].height = 24
    cur_row += 1

    write_4col_header(ws_4col, cur_row)
    cur_row += 1

    c.execute("""
        SELECT sl_no, officer_name, present_posting, transferred_post_name, reason_notes, is_manual_recommendation
        FROM executive_lateral_transfers
        ORDER BY sl_no ASC
    """)
    for r in c.fetchall():
        sl_val = r['sl_no']
        c2_val = clean_pres(r['officer_name'], r['present_posting'])
        c3_val = clean_sub(r['transferred_post_name'])
        c4_val = clean_su(r['reason_notes'])
        is_m = bool(r['is_manual_recommendation'])
        row_fill = white_row_fill if is_m else light_grey_row_fill

        ws_4col.cell(row=cur_row, column=1, value=sl_val).alignment = Alignment(horizontal="center", vertical="center")
        ws_4col.cell(row=cur_row, column=2, value=c2_val).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws_4col.cell(row=cur_row, column=3, value=c3_val).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws_4col.cell(row=cur_row, column=4, value=c4_val).alignment = Alignment(horizontal="center" if c4_val == "Nil" else "left", vertical="center", wrap_text=True)

        for col_i in range(1, 5):
            cell = ws_4col.cell(row=cur_row, column=col_i)
            cell.border = black_border
            cell.fill = row_fill
            cell.font = order_4col_bold if (col_i == 1 or (col_i == 4 and c4_val != "Nil")) else order_4col_font
        ws_4col.row_dimensions[cur_row].height = 22
        cur_row += 1

    # =========================================================================
    # SHEET 9: Master_Cadre_Directory (1,624 Statewide Cadre Employees)
    # =========================================================================
    ws_master = wb.create_sheet(title="Master_Cadre_Directory")
    ws_master.views.sheetView[0].showGridLines = True

    master_headers = [
        "Sl No", "HRMS ID", "Officer Name", "Designation", "Present Posting / Office",
        "District", "Service Status", "Date of Retirement", "50-Pt Roster?", 
        "HQ Deployed?", "Excess / Unsanctioned?", "Mobile", "Email", "WBVC Reg No", 
        "Residential Address", "Posting History / Notes"
    ]
    for c_idx, h in enumerate(master_headers, 1):
        cell = ws_master.cell(row=1, column=c_idx, value=h)
        cell.fill = navy_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_master.row_dimensions[1].height = 28

    c.execute("""
        SELECT hrms_id, officer_name, designation, present_posting, district,
               service_status, dor, is_50pt_candidate, is_hq_deployed, is_unsanctioned_post,
               mobile, email, wbvc_reg_no, residential_address,
               COALESCE(NULLIF(hq_posting_history, ''), source_notes) as notes
        FROM master_all_cadre_employees
        ORDER BY 
            is_hq_deployed DESC,
            is_50pt_candidate DESC,
            district ASC,
            officer_name ASC
    """)
    master_rows = c.fetchall()
    for idx, r in enumerate(master_rows, 2):
        row_sl = idx - 1
        ws_master.cell(row=idx, column=1, value=row_sl).alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=2, value=r["hrms_id"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=3, value=r["officer_name"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_master.cell(row=idx, column=4, value=r["designation"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_master.cell(row=idx, column=5, value=r["present_posting"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_master.cell(row=idx, column=6, value=r["district"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=7, value=r["service_status"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=8, value=r["dor"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=9, value="YES" if r["is_50pt_candidate"] else "NO").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=10, value="YES" if r["is_hq_deployed"] else "NO").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=11, value="YES" if r["is_unsanctioned_post"] else "NO").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=12, value=r["mobile"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=13, value=r["email"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_master.cell(row=idx, column=14, value=r["wbvc_reg_no"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_master.cell(row=idx, column=15, value=r["residential_address"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_master.cell(row=idx, column=16, value=r["notes"] or "").alignment = Alignment(horizontal="left", vertical="center")

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 17):
            cell = ws_master.cell(row=idx, column=c_idx)
            cell.border = cell_border
            cell.fill = fill_color
            cell.font = bold_font if c_idx in [1, 2, 3] else normal_font
        ws_master.row_dimensions[idx].height = 22

    # =========================================================================
    # SHEET 10: Directorate_HQ_Roster (37 Verified HQ Deployed Officers)
    # =========================================================================
    ws_hq = wb.create_sheet(title="Directorate_HQ_Roster")
    ws_hq.views.sheetView[0].showGridLines = True

    hq_headers = [
        "Sl No", "HRMS ID", "Officer Name", "HQ Post Designation", "HQ Date of Joining",
        "50-Pt Promotee?", "District", "Service Status", "Date of Retirement", 
        "Mobile", "Email", "Career Posting History / Timeline"
    ]
    for c_idx, h in enumerate(hq_headers, 1):
        cell = ws_hq.cell(row=1, column=c_idx, value=h)
        cell.fill = teal_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_hq.row_dimensions[1].height = 28

    c.execute("""
        SELECT hrms_id, officer_name, 
               COALESCE(NULLIF(hq_post_title, ''), designation) as hq_desig,
               hq_doj, is_50pt_candidate, district, service_status, dor,
               mobile, email, hq_posting_history
        FROM master_all_cadre_employees
        WHERE is_hq_deployed = 1
        ORDER BY hrms_id ASC
    """)
    hq_rows = c.fetchall()
    for idx, r in enumerate(hq_rows, 2):
        row_sl = idx - 1
        ws_hq.cell(row=idx, column=1, value=row_sl).alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=2, value=r["hrms_id"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=3, value=r["officer_name"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_hq.cell(row=idx, column=4, value=r["hq_desig"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_hq.cell(row=idx, column=5, value=r["hq_doj"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=6, value="YES" if r["is_50pt_candidate"] else "NO").alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=7, value=r["district"] or "Kolkata").alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=8, value=r["service_status"] or "In Service").alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=9, value=r["dor"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=10, value=r["mobile"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_hq.cell(row=idx, column=11, value=r["email"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_hq.cell(row=idx, column=12, value=r["hq_posting_history"] or "").alignment = Alignment(horizontal="left", vertical="center")

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 13):
            cell = ws_hq.cell(row=idx, column=c_idx)
            cell.border = cell_border
            cell.fill = fill_color
            cell.font = bold_font if c_idx in [1, 2, 3] else normal_font
        ws_hq.row_dimensions[idx].height = 24

    # =========================================================================
    # SHEET 11: Excess_Unsanctioned_Deploy (135 Officers beyond Notification 1809)
    # =========================================================================
    ws_excess = wb.create_sheet(title="Excess_Unsanctioned_Deploy")
    ws_excess.views.sheetView[0].showGridLines = True

    excess_headers = [
        "Sl No", "HRMS ID", "Officer Name", "Designation", "Establishment",
        "District", "Service Status", "Date of Retirement", "Reason / Classification"
    ]
    for c_idx, h in enumerate(excess_headers, 1):
        cell = ws_excess.cell(row=1, column=c_idx, value=h)
        cell.fill = amber_header_fill
        cell.font = white_header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border
    ws_excess.row_dimensions[1].height = 28

    c.execute("""
        SELECT hrms_id, officer_name, designation, establishment, district,
               service_status, dor, source_notes
        FROM master_all_cadre_employees
        WHERE is_unsanctioned_post = 1
        ORDER BY district ASC, officer_name ASC
    """)
    excess_rows = c.fetchall()
    for idx, r in enumerate(excess_rows, 2):
        row_sl = idx - 1
        ws_excess.cell(row=idx, column=1, value=row_sl).alignment = Alignment(horizontal="center", vertical="center")
        ws_excess.cell(row=idx, column=2, value=r["hrms_id"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_excess.cell(row=idx, column=3, value=r["officer_name"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_excess.cell(row=idx, column=4, value=r["designation"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_excess.cell(row=idx, column=5, value=r["establishment"] or "").alignment = Alignment(horizontal="left", vertical="center")
        ws_excess.cell(row=idx, column=6, value=r["district"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_excess.cell(row=idx, column=7, value=r["service_status"] or "In Service").alignment = Alignment(horizontal="center", vertical="center")
        ws_excess.cell(row=idx, column=8, value=r["dor"] or "").alignment = Alignment(horizontal="center", vertical="center")
        ws_excess.cell(row=idx, column=9, value=r["source_notes"] or "").alignment = Alignment(horizontal="left", vertical="center")

        fill_color = zebra_fill if idx % 2 == 0 else plain_fill
        for c_idx in range(1, 10):
            cell = ws_excess.cell(row=idx, column=c_idx)
            cell.border = cell_border
            cell.fill = fill_color
            cell.font = bold_font if c_idx in [1, 2, 3] else normal_font
        ws_excess.row_dimensions[idx].height = 22

    # Column Widths
    col_widths = {
        "50_Pt_Roster_Decisions": {
            "A": 6, "B": 6, "C": 10, "D": 14, "E": 26, "F": 26, "G": 20, "H": 18, "I": 14,
            "J": 22, "K": 22, "L": 22, "M": 40, "N": 14, "O": 42, "P": 22, "Q": 42, "R": 28, "S": 16, "T": 32
        },
        "Obliterated_Rehab_Decisions": {
            "A": 6, "B": 32, "C": 28, "D": 18, "E": 18, "F": 26, "G": 14, "H": 14, "I": 18,
            "J": 40, "K": 14, "L": 42, "M": 24, "N": 42, "O": 28, "P": 14, "Q": 24
        },
        "Available_DD_Posts": {
            "A": 10, "B": 50, "C": 35, "D": 18, "E": 22, "F": 20, "G": 28
        },
        "Available_AD_Vacancies": {
            "A": 10, "B": 50, "C": 35, "D": 18, "E": 18, "F": 20, "G": 28
        },
        "SU_Post_Picker": {
            "A": 50, "B": 35, "C": 18, "D": 30, "E": 18, "F": 14, "G": 10
        },
        "Displaced_Queue_Tracker": {
            "A": 6, "B": 28, "C": 14, "D": 35, "E": 22, "F": 45, "G": 16, "H": 24
        },
        "Secretariat_Posting_Order": {
            "A": 8, "B": 45, "C": 18, "D": 28, "E": 52, "F": 32
        },
        "4_Column_Posting_Order": {
            "A": 8, "B": 54, "C": 48, "D": 42
        },
        "Master_Cadre_Directory": {
            "A": 8, "B": 14, "C": 28, "D": 32, "E": 45, "F": 18, "G": 16, "H": 16, "I": 16, "J": 16, "K": 22, "L": 16, "M": 26, "N": 16, "O": 35, "P": 50
        },
        "Directorate_HQ_Roster": {
            "A": 8, "B": 14, "C": 28, "D": 35, "E": 18, "F": 16, "G": 16, "H": 16, "I": 16, "J": 16, "K": 26, "L": 60
        },
        "Excess_Unsanctioned_Deploy": {
            "A": 8, "B": 14, "C": 28, "D": 32, "E": 35, "F": 18, "G": 16, "H": 16, "I": 40
        }
    }

    all_sheets = [ws_guide, ws_roster, ws_oblit, ws_dd, ws_ad, ws_su, ws_disp, ws_order, ws_4col, ws_master, ws_hq, ws_excess]
    for ws in all_sheets:
        title = ws.title
        if title in col_widths:
            for col_letter, width in col_widths[title].items():
                ws.column_dimensions[col_letter].width = width

    # Add Conditional Formatting Rules
    fill_allotted_direct = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid") # soft green
    font_allotted_direct = Font(color="065F46", bold=True)
    rule_allotted_direct = CellIsRule(operator="equal", formula=['"ALLOTTED DIRECT"'], fill=fill_allotted_direct, font=font_allotted_direct)

    fill_allotted_su = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid") # soft blue
    font_allotted_su = Font(color="1E40AF", bold=True)
    rule_allotted_su = CellIsRule(operator="equal", formula=['"ALLOTTED WITH SU"'], fill=fill_allotted_su, font=font_allotted_su)

    fill_collision = PatternFill(start_color="FFE4E6", end_color="FFE4E6", fill_type="solid") # soft red
    font_collision = Font(color="9F1239", bold=True)
    rule_collision = CellIsRule(operator="equal", formula=['"⚠️ SU COLLISION"'], fill=fill_collision, font=font_collision)

    fill_pending = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid") # soft amber
    font_pending = Font(color="92400E", italic=True)
    rule_pending = CellIsRule(operator="equal", formula=['"PENDING"'], fill=fill_pending, font=font_pending)

    ws_roster.conditional_formatting.add(f"P2:P{total_roster + 1}", rule_allotted_direct)
    ws_roster.conditional_formatting.add(f"P2:P{total_roster + 1}", rule_allotted_su)
    ws_roster.conditional_formatting.add(f"P2:P{total_roster + 1}", rule_collision)
    ws_roster.conditional_formatting.add(f"P2:P{total_roster + 1}", rule_pending)

    # Obliterated conditional formatting
    ws_oblit.conditional_formatting.add(f"M2:M{total_oblit + 1}", rule_allotted_direct)
    ws_oblit.conditional_formatting.add(f"M2:M{total_oblit + 1}", rule_allotted_su)
    ws_oblit.conditional_formatting.add(f"M2:M{total_oblit + 1}", rule_collision)

    # Available_DD_Posts conditional formatting
    fill_avail = PatternFill(start_color="ECFDF5", end_color="ECFDF5", fill_type="solid")
    font_avail = Font(color="047857", bold=True)
    rule_avail = CellIsRule(operator="equal", formula=['"AVAILABLE"'], fill=fill_avail, font=font_avail)

    fill_allot_post = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    font_allot_post = Font(color="64748B")
    rule_allot_post = CellIsRule(operator="equal", formula=['"ALLOTTED"'], fill=fill_allot_post, font=font_allot_post)

    fill_dup = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    font_dup = Font(color="B91C1C", bold=True)
    rule_dup = CellIsRule(operator="equal", formula=['"⚠️ DUPLICATE ALLOTMENT!"'], fill=fill_dup, font=font_dup)

    ws_dd.conditional_formatting.add(f"F2:F{len(dd_rows) + 1}", rule_avail)
    ws_dd.conditional_formatting.add(f"F2:F{len(dd_rows) + 1}", rule_allot_post)
    ws_dd.conditional_formatting.add(f"F2:F{len(dd_rows) + 1}", rule_dup)

    wb.save(OUTPUT_FILE)
    conn.close()
    print(f"Successfully generated Google Sheets-ready workbook: {OUTPUT_FILE}")

if __name__ == "__main__":
    build_workbook()
