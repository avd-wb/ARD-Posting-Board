#!/usr/bin/env python3
"""
generate_hq_accommodation_excel.py
Generates:
1. Standalone Excel deliverable: HQ_Districtwise_Accommodation_20260913_<hhmm>_AG.xlsx
2. Updated Master Workbook: Promotion_242_1st_Draft_20260913_<hhmm>_AG.xlsx
   containing the new tab: HQ_District_Accommodation
"""

import os
import re
import sys
import datetime
import subprocess
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DIR_AVD = "/Users/nirmalyaranjansarkar/Projects/AVD/10_ARD_DD_Promotion_2026"
DIR_AG = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DRIVE_FOLDER_ID = "1BgJE4thWGsCLv4qFHqmWobW_met8UuEL"

def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M")

def create_hq_accommodation_workbooks(ts=None):
    if not ts:
        ts = get_timestamp()

    print(f"Generating HQ Accommodation Excel with timestamp {ts}...")
    
    # Locate latest master file
    master_file = os.path.join(DIR_AG, "Promotion_242_1st_Draft_20260913_0945_AG.xlsx")
    if not os.path.exists(master_file):
        master_file = os.path.join(DIR_AVD, "Promotion_242_1st_Draft_20260913_0945_AG.xlsx")
    
    wb_master = openpyxl.load_workbook(master_file, data_only=True)
    ws_full = wb_master["Full_Promotion_Transfer_List"]

    # Extract all 39 HQ substantive rows and 5 SU at HQ rows
    hq_subst = []
    hq_su = []

    districts = [
        "South 24 Parganas", "Hooghly", "North 24 Parganas", "Paschim Medinipur",
        "Nadia", "Purba Medinipur", "Howrah"
    ]

    for r in range(2, ws_full.max_row + 1):
        sl = ws_full.cell(r, 1).value
        p242 = ws_full.cell(r, 2).value
        name = ws_full.cell(r, 3).value
        pres_desig = ws_full.cell(r, 4).value
        pres_estab = ws_full.cell(r, 5).value
        pres_block = ws_full.cell(r, 6).value
        pres_dist = ws_full.cell(r, 7).value
        pres_post = ws_full.cell(r, 8).value
        pres_su = ws_full.cell(r, 9).value
        basis = ws_full.cell(r, 10).value
        subst = ws_full.cell(r, 11).value
        su = ws_full.cell(r, 12).value
        rem = ws_full.cell(r, 13).value
        comments = ws_full.cell(r, 14).value

        subst_str = str(subst) if subst else ""
        su_str = str(su) if su else ""

        is_hq_subst = any(k in subst_str.lower() for k in ["directorate", "dte hq", "headquarters", "hq"]) and "district office" not in subst_str.lower()
        is_hq_su = any(k in su_str.lower() for k in ["directorate", "dte hq", "headquarters", "hq", "wbldc"]) and "district office" not in su_str.lower()

        if is_hq_subst:
            # find su district
            found_dist = "HQ In-Person (Direct)"
            for d in districts:
                if d.lower() in su_str.lower():
                    found_dist = d
                    break
            
            # rationale description
            if found_dist == "HQ In-Person (Direct)":
                if p242:
                    rationale = "Direct physical posting at Directorate Headquarters against sanctioned DD vacancy (SU: Nil)"
                else:
                    rationale = "Direct physical posting at Directorate HQ (Consequential Lateral / AD accommodation)"
            else:
                rationale = f"{found_dist} district cap exceeded; absorbed against sanctioned DD vacancy at Directorate HQ to enable field Service Utilization (SU) in home district"

            hq_subst.append({
                "sl": sl, "p242": p242 or "-", "name": name, "pres_desig": pres_desig, "pres_block": pres_block or "-",
                "pres_dist": pres_dist, "basis": basis, "subst": subst_str, "su": su_str, "su_dist": found_dist,
                "comments": comments or "-", "rationale": rationale
            })

        if is_hq_su:
            hq_su.append({
                "sl": sl, "p242": p242 or "-", "name": name, "pres_desig": pres_desig, "pres_dist": pres_dist,
                "subst": subst_str, "su": su_str, "comments": comments or "-"
            })

    print(f"Loaded {len(hq_subst)} HQ substantive officers and {len(hq_su)} SU at HQ officers.")

    # District sort order
    dist_order = [
        "HQ In-Person (Direct)", "South 24 Parganas", "Hooghly", "North 24 Parganas",
        "Paschim Medinipur", "Nadia", "Purba Medinipur", "Howrah"
    ]
    hq_subst.sort(key=lambda x: (dist_order.index(x["su_dist"]) if x["su_dist"] in dist_order else 99, 0 if x["p242"] != "-" else 1, int(x["p242"]) if str(x["p242"]).isdigit() else 999))

    # Styling definitions
    navy_dark = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    navy_medium = PatternFill(start_color="2E5B88", end_color="2E5B88", fill_type="solid")
    teal_header = PatternFill(start_color="005E5D", end_color="005E5D", fill_type="solid")
    blue_accent = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
    light_gray = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    kpi_bg = PatternFill(start_color="EBF1F5", end_color="EBF1F5", fill_type="solid")
    green_tag = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")

    font_title = Font(name="Arial", size=14, bold=True, color="1F497D")
    font_subtitle = Font(name="Arial", size=10, italic=True, color="595959")
    font_th = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Arial", size=10, bold=True, color="000000")
    font_regular = Font(name="Arial", size=9.5, color="000000")
    font_kpi_num = Font(name="Arial", size=16, bold=True, color="1F497D")
    font_kpi_lbl = Font(name="Arial", size=9, bold=True, color="595959")

    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )
    thick_bottom = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="medium", color="1F497D")
    )

    # ----------------------------------------------------
    # 1. BUILD STANDALONE EXCEL WORKBOOK
    # ----------------------------------------------------
    wb_standalone = openpyxl.Workbook()
    
    # Sheet 1: Summary & Dashboard
    ws_dash = wb_standalone.active
    ws_dash.title = "Executive_Summary"
    ws_dash.views.sheetView[0].showGridLines = True

    # Sheet Title
    ws_dash.cell(1, 1, "DIRECTORATE OF ANIMAL RESOURCES & ANIMAL HEALTH, WEST BENGAL").font = Font(name="Arial", size=14, bold=True, color="1F497D")
    ws_dash.cell(2, 1, "Cadre Posting Plan 2026: Directorate Headquarters Posts & District-Wise Accommodation Analysis").font = font_subtitle
    ws_dash.row_dimensions[1].height = 24
    ws_dash.row_dimensions[2].height = 18

    # KPI Summary Cards (Row 4 to 5)
    kpis = [
        ("Sanctioned DD Posts at HQ", "33"),
        ("DD Promotees Allocated", "33 (100%)"),
        ("Lateral AD Accommodations", "6"),
        ("Direct Physical at HQ", "11"),
        ("Accommodated on Field SU", "28"),
        ("Cadre Deficit / Excess", "0 (Balanced)")
    ]
    ws_dash.row_dimensions[4].height = 18
    ws_dash.row_dimensions[5].height = 26

    for idx, (lbl, val) in enumerate(kpis):
        col = idx + 1
        c_lbl = ws_dash.cell(4, col, lbl)
        c_lbl.font = font_kpi_lbl
        c_lbl.fill = kpi_bg
        c_lbl.alignment = Alignment(horizontal="center", vertical="center")
        c_lbl.border = thin_border

        c_val = ws_dash.cell(5, col, val)
        c_val.font = font_kpi_num
        c_val.fill = kpi_bg
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.border = thick_bottom

    # Table 1: Field Accommodation Summary
    ws_dash.cell(7, 1, "SUMMARY BREAKDOWN: FIELD ACCOMMODATION OF DIRECTORATE HQ SUBSTANTIVE POSTS").font = Font(name="Arial", size=11, bold=True, color="1F497D")
    ws_dash.row_dimensions[7].height = 22

    sum_headers = [
        "Sl", "District / Field Category", "DD Promotees (Level 19)", "Lateral / AD Posts",
        "Total Substantive at HQ", "% Share of HQ Cadre", "Nature of Deployment / Key Establishments"
    ]
    ws_dash.row_dimensions[8].height = 26
    for c_idx, h in enumerate(sum_headers, 1):
        cell = ws_dash.cell(8, c_idx, h)
        cell.font = font_th
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    summary_rows = [
        ("1", "Directorate HQ (Direct / Physical In-Person)", 6, 5, 11, "28.2%", "Physical posting at Directorate HQ / Salt Lake (SU: Nil)"),
        ("2", "South 24 Parganas", 8, 0, 8, "20.5%", "Mandirbazar, Basanti, Thakurpukur, Baruipur, Bishnupur-II, Magrahat-II, JD Office"),
        ("3", "Hooghly", 5, 0, 5, "12.8%", "Dhaniakhali (2), Haripal, AD ARD (Mgmt), AD ARD (Veterinary)"),
        ("4", "North 24 Parganas", 3, 1, 4, "10.3%", "Sandeshkhali-II, Sandeshkhali-I, Barrackpore-I, District Office"),
        ("5", "Paschim Medinipur", 4, 0, 4, "10.3%", "SAHC Paschim Med, Daspur-II, Sabang, Pingla ABAHC"),
        ("6", "Nadia", 3, 0, 3, "7.7%", "Ranaghat-I, Ranaghat-II, State Poultry Farm Ranaghat"),
        ("7", "Purba Medinipur", 2, 0, 2, "5.1%", "Mahishadal BAHC, Sutahata BLDO"),
        ("8", "Howrah", 2, 0, 2, "5.1%", "Bagnan-II BLDO, Udaynarayanpur BLDO")
    ]

    for row_data in summary_rows:
        ws_dash.append(list(row_data))
        curr_r = ws_dash.max_row
        ws_dash.row_dimensions[curr_r].height = 22
        fill = light_gray if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_data) + 1):
            cell = ws_dash.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = thin_border
            if c in [1, 3, 4, 5, 6]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Total Row
    tot_row = ["TOTAL", "Directorate Headquarters Sanction", 33, 6, 39, "100.0%", "33 Sanctioned DD Posts + 6 AD Lateral Accommodations (0 Deficit)"]
    ws_dash.append(tot_row)
    tot_r = ws_dash.max_row
    ws_dash.row_dimensions[tot_r].height = 24
    for c in range(1, len(tot_row) + 1):
        cell = ws_dash.cell(tot_r, c)
        cell.font = font_bold
        cell.fill = blue_accent
        cell.border = thin_border
        if c in [1, 3, 4, 5, 6]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # Inflow Table on Dashboard
    ws_dash.cell(tot_r + 2, 1, "INFLOW: OFFICERS HOLDING SUBSTANTIVE POSTS OUTSIDE HQ WITH SU AT DIRECTORATE HQ (5 OFFICERS)").font = Font(name="Arial", size=11, bold=True, color="1F497D")
    ws_dash.row_dimensions[tot_r + 2].height = 22

    inflow_headers = ["Master Sl", "Roster Sl", "Officer Name", "Substantive Sanctioned Post", "Substantive District / Set-up", "Service Utilized (SU) Deployment at HQ", "Administrative Review Notes"]
    ws_dash.row_dimensions[tot_r + 3].height = 26
    for c_idx, h in enumerate(inflow_headers, 1):
        cell = ws_dash.cell(tot_r + 3, c_idx, h)
        cell.font = font_th
        cell.fill = teal_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    inflow_data = [
        (11, "11", "Dr. Soumen Ghosh", "Deputy Director, ARD, IAH&VB", "I.A.H. & V.B., Kolkata", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Stay / Retained at Central HQ"),
        (175, "175", "Dr. Tapan Kumar Dey", "Deputy Director, ARD, Office of JD Salboni", "CSAHF / Salboni, Paschim Medinipur", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Mobilized to Central HQ"),
        (190, "190", "Dr. Nabendu Kumar Nag", "Deputy Director, ARD, District Office Siliguri", "Siliguri / Darjeeling", "Manager (HR), West Bengal Livestock Development Corp. Ltd. HQ, Salt Lake", "WBLDCL HQ Deputation"),
        (270, "—", "Dr. Nirmalya Ranjan Sarkar", "Assistant Director, ARD, District Office Hooghly", "Hooghly", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Directorate HQ Central Team"),
        (309, "—", "Dr. Debi Prasad Nandi", "Assistant Director, ARD, District Office North 24 Pgs", "North 24 Parganas", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Executive Decision Dr. NRS (Row 310)")
    ]

    for item in inflow_data:
        ws_dash.append(list(item))
        curr_r = ws_dash.max_row
        ws_dash.row_dimensions[curr_r].height = 22
        fill = light_gray if curr_r % 2 == 0 else white_fill
        for c in range(1, len(item) + 1):
            cell = ws_dash.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = thin_border
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws_dash.column_dimensions["A"].width = 12
    ws_dash.column_dimensions["B"].width = 38
    ws_dash.column_dimensions["C"].width = 24
    ws_dash.column_dimensions["D"].width = 20
    ws_dash.column_dimensions["E"].width = 24
    ws_dash.column_dimensions["F"].width = 22
    ws_dash.column_dimensions["G"].width = 50

    # Sheet 2: All 39 Substantive HQ Posts (Detailed Roster)
    ws_roster = wb_standalone.create_sheet(title="All_39_Substantive_HQ_Posts")
    ws_roster.views.sheetView[0].showGridLines = True

    roster_headers = [
        "Master Sl", "242 Roster Sl", "Officer Name", "Present Designation", "Present District",
        "Transfer Basis", "Substantive Post at Directorate HQ", "Field Accommodation (SU District)",
        "Service Utilized At (Establishment & Block)", "Administrative Directives & Remarks", "Administrative Accommodation Rationale"
    ]
    ws_roster.append(roster_headers)
    ws_roster.row_dimensions[1].height = 28
    for c_idx, h in enumerate(roster_headers, 1):
        cell = ws_roster.cell(1, c_idx, h)
        cell.font = font_th
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    current_dist = None
    for item in hq_subst:
        if item["su_dist"] != current_dist:
            current_dist = item["su_dist"]
            dist_count = sum(1 for x in hq_subst if x["su_dist"] == current_dist)
            ws_roster.append([f"ACCOMMODATION GROUP: {current_dist.upper()} ({dist_count} OFFICERS)"] + [""] * 10)
            hdr_r = ws_roster.max_row
            ws_roster.row_dimensions[hdr_r].height = 22
            ws_roster.merge_cells(start_row=hdr_r, start_column=1, end_row=hdr_r, end_column=11)
            hdr_cell = ws_roster.cell(hdr_r, 1)
            hdr_cell.font = Font(name="Arial", size=10, bold=True, color="1F497D")
            hdr_cell.fill = blue_accent
            hdr_cell.alignment = Alignment(horizontal="left", vertical="center")
            for col_i in range(1, 12):
                ws_roster.cell(hdr_r, col_i).border = thin_border

        row_vals = [
            item["sl"], item["p242"], item["name"], item["pres_desig"], item["pres_dist"],
            item["basis"], item["subst"], item["su_dist"], item["su"], item["comments"], item["rationale"]
        ]
        ws_roster.append(row_vals)
        curr_r = ws_roster.max_row
        ws_roster.row_dimensions[curr_r].height = 24
        fill = light_gray if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_vals) + 1):
            cell = ws_roster.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = thin_border
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c in [5, 6, 8]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws_roster.column_dimensions["A"].width = 10
    ws_roster.column_dimensions["B"].width = 12
    ws_roster.column_dimensions["C"].width = 28
    ws_roster.column_dimensions["D"].width = 30
    ws_roster.column_dimensions["E"].width = 18
    ws_roster.column_dimensions["F"].width = 22
    ws_roster.column_dimensions["G"].width = 38
    ws_roster.column_dimensions["H"].width = 22
    ws_roster.column_dimensions["I"].width = 42
    ws_roster.column_dimensions["J"].width = 25
    ws_roster.column_dimensions["K"].width = 45
    ws_roster.freeze_panes = "C2"

    # Sheet 3: Separate Tab per Key Field District
    ws_field = wb_standalone.create_sheet(title="Field_SU_Groupings")
    ws_field.views.sheetView[0].showGridLines = True

    field_headers = ["Field SU District", "Master Sl", "242 Sl", "Officer Name", "Present Post", "Substantive Post at HQ", "Service Utilized Station", "Remarks"]
    ws_field.append(field_headers)
    ws_field.row_dimensions[1].height = 28
    for c_idx, h in enumerate(field_headers, 1):
        cell = ws_field.cell(1, c_idx, h)
        cell.font = font_th
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    for item in hq_subst:
        if item["su_dist"] != "HQ In-Person (Direct)":
            row_vals = [
                item["su_dist"], item["sl"], item["p242"], item["name"], item["pres_desig"],
                item["subst"], item["su"], item["rationale"]
            ]
            ws_field.append(row_vals)
            curr_r = ws_field.max_row
            ws_field.row_dimensions[curr_r].height = 24
            fill = light_gray if curr_r % 2 == 0 else white_fill
            for c in range(1, len(row_vals) + 1):
                cell = ws_field.cell(curr_r, c)
                cell.font = font_regular
                cell.fill = fill
                cell.border = thin_border
                if c in [2, 3]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

    ws_field.column_dimensions["A"].width = 20
    ws_field.column_dimensions["B"].width = 10
    ws_field.column_dimensions["C"].width = 10
    ws_field.column_dimensions["D"].width = 28
    ws_field.column_dimensions["E"].width = 30
    ws_field.column_dimensions["F"].width = 38
    ws_field.column_dimensions["G"].width = 42
    ws_field.column_dimensions["H"].width = 45
    ws_field.freeze_panes = "D2"

    # Save Standalone Excel
    standalone_filename = f"HQ_Districtwise_Accommodation_{ts}_AG.xlsx"
    standalone_filename_alt = f"HQ_Districtwise_Accommodation_{ts}.AG.xlsx"

    path_standalone_avd = os.path.join(DIR_AVD, standalone_filename)
    path_standalone_ag = os.path.join(DIR_AG, standalone_filename)
    wb_standalone.save(path_standalone_avd)
    wb_standalone.save(path_standalone_ag)

    path_standalone_avd_alt = os.path.join(DIR_AVD, standalone_filename_alt)
    path_standalone_ag_alt = os.path.join(DIR_AG, standalone_filename_alt)
    wb_standalone.save(path_standalone_avd_alt)
    wb_standalone.save(path_standalone_ag_alt)

    print(f"Saved standalone files:\n  {path_standalone_avd}\n  {path_standalone_ag}")

    # ----------------------------------------------------
    # 2. ALSO INSERT INTO MASTER WORKBOOK AS TAB 4
    # ----------------------------------------------------
    if "HQ_District_Accommodation" in wb_master.sheetnames:
        del wb_master["HQ_District_Accommodation"]
    
    ws_m_hq = wb_master.create_sheet(title="HQ_District_Accommodation", index=3)
    ws_m_hq.views.sheetView[0].showGridLines = True

    # Title
    ws_m_hq.cell(1, 1, "DIRECTORATE HEADQUARTERS — DISTRICT-WISE POSTING & SERVICE UTILIZATION (SU) ACCOMMODATION").font = font_title
    ws_m_hq.cell(2, 1, "Analysis of 33 Sanctioned Deputy Director (Level 19) Posts & 6 Lateral Accommodations").font = font_subtitle
    ws_m_hq.row_dimensions[1].height = 24
    ws_m_hq.row_dimensions[2].height = 18

    # KPI Summary Cards
    for idx, (lbl, val) in enumerate(kpis):
        col = idx + 1
        c_lbl = ws_m_hq.cell(4, col, lbl)
        c_lbl.font = font_kpi_lbl
        c_lbl.fill = kpi_bg
        c_lbl.alignment = Alignment(horizontal="center", vertical="center")
        c_lbl.border = thin_border

        c_val = ws_m_hq.cell(5, col, val)
        c_val.font = font_kpi_num
        c_val.fill = kpi_bg
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.border = thick_bottom

    ws_m_hq.cell(7, 1, "SUMMARY BREAKDOWN: FIELD ACCOMMODATION OF DIRECTORATE HQ SUBSTANTIVE POSTS").font = Font(name="Arial", size=11, bold=True, color="1F497D")
    ws_m_hq.row_dimensions[7].height = 22

    for c_idx, h in enumerate(sum_headers, 1):
        cell = ws_m_hq.cell(8, c_idx, h)
        cell.font = font_th
        cell.fill = navy_dark
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    for row_data in summary_rows:
        ws_m_hq.append(list(row_data))
        curr_r = ws_m_hq.max_row
        ws_m_hq.row_dimensions[curr_r].height = 22
        fill = light_gray if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_data) + 1):
            cell = ws_m_hq.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = thin_border
            if c in [1, 3, 4, 5, 6]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws_m_hq.append(tot_row)
    m_tot_r = ws_m_hq.max_row
    ws_m_hq.row_dimensions[m_tot_r].height = 24
    for c in range(1, len(tot_row) + 1):
        cell = ws_m_hq.cell(m_tot_r, c)
        cell.font = font_bold
        cell.fill = blue_accent
        cell.border = thin_border
        if c in [1, 3, 4, 5, 6]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # Detailed Roster
    ws_m_hq.cell(m_tot_r + 2, 1, "PART A: COMPLETE ROSTER OF OFFICERS WITH SUBSTANTIVE POST AT DIRECTORATE HEADQUARTERS (39 OFFICERS)").font = Font(name="Arial", size=11, bold=True, color="1F497D")
    ws_m_hq.row_dimensions[m_tot_r + 2].height = 22

    for c_idx, h in enumerate(roster_headers, 1):
        cell = ws_m_hq.cell(m_tot_r + 3, c_idx, h)
        cell.font = font_th
        cell.fill = navy_medium
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    curr_dist_m = None
    for item in hq_subst:
        if item["su_dist"] != curr_dist_m:
            curr_dist_m = item["su_dist"]
            dist_count = sum(1 for x in hq_subst if x["su_dist"] == curr_dist_m)
            ws_m_hq.append([f"ACCOMMODATION GROUP: {curr_dist_m.upper()} ({dist_count} OFFICERS)"] + [""] * 10)
            hdr_r = ws_m_hq.max_row
            ws_m_hq.row_dimensions[hdr_r].height = 22
            ws_m_hq.merge_cells(start_row=hdr_r, start_column=1, end_row=hdr_r, end_column=11)
            hdr_cell = ws_m_hq.cell(hdr_r, 1)
            hdr_cell.font = Font(name="Arial", size=10, bold=True, color="1F497D")
            hdr_cell.fill = blue_accent
            hdr_cell.alignment = Alignment(horizontal="left", vertical="center")
            for col_i in range(1, 12):
                ws_m_hq.cell(hdr_r, col_i).border = thin_border

        row_vals = [
            item["sl"], item["p242"], item["name"], item["pres_desig"], item["pres_dist"],
            item["basis"], item["subst"], item["su_dist"], item["su"], item["comments"], item["rationale"]
        ]
        ws_m_hq.append(row_vals)
        curr_r = ws_m_hq.max_row
        ws_m_hq.row_dimensions[curr_r].height = 24
        fill = light_gray if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_vals) + 1):
            cell = ws_m_hq.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = thin_border
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c in [5, 6, 8]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Inflow Table
    inflow_start = ws_m_hq.max_row + 2
    ws_m_hq.cell(inflow_start, 1, "PART B: OFFICERS WITH SUBSTANTIVE POSTS OUTSIDE HQ WITH SERVICE UTILIZATION AT DIRECTORATE HQ (5 OFFICERS)").font = Font(name="Arial", size=11, bold=True, color="1F497D")
    ws_m_hq.row_dimensions[inflow_start].height = 22

    for c_idx, h in enumerate(inflow_headers, 1):
        cell = ws_m_hq.cell(inflow_start + 1, c_idx, h)
        cell.font = font_th
        cell.fill = teal_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    for item in inflow_data:
        ws_m_hq.append(list(item))
        curr_r = ws_m_hq.max_row
        ws_m_hq.row_dimensions[curr_r].height = 22
        fill = light_gray if curr_r % 2 == 0 else white_fill
        for c in range(1, len(item) + 1):
            cell = ws_m_hq.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = thin_border
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws_m_hq.column_dimensions["A"].width = 10
    ws_m_hq.column_dimensions["B"].width = 12
    ws_m_hq.column_dimensions["C"].width = 28
    ws_m_hq.column_dimensions["D"].width = 30
    ws_m_hq.column_dimensions["E"].width = 18
    ws_m_hq.column_dimensions["F"].width = 22
    ws_m_hq.column_dimensions["G"].width = 38
    ws_m_hq.column_dimensions["H"].width = 22
    ws_m_hq.column_dimensions["I"].width = 42
    ws_m_hq.column_dimensions["J"].width = 25
    ws_m_hq.column_dimensions["K"].width = 45

    # Save Updated Master Workbook with timestamp
    master_filename = f"Promotion_242_1st_Draft_{ts}_AG.xlsx"
    master_filename_alt = f"Promotion_242_1st_Draft_{ts}.AG.xlsx"

    path_master_avd = os.path.join(DIR_AVD, master_filename)
    path_master_ag = os.path.join(DIR_AG, master_filename)
    wb_master.save(path_master_avd)
    wb_master.save(path_master_ag)

    path_master_avd_alt = os.path.join(DIR_AVD, master_filename_alt)
    path_master_ag_alt = os.path.join(DIR_AG, master_filename_alt)
    wb_master.save(path_master_avd_alt)
    wb_master.save(path_master_ag_alt)

    print(f"Saved master files:\n  {path_master_avd}\n  {path_master_ag}")

    # Upload both standalone and master to Google Drive
    files_to_upload = [
        (standalone_filename, path_standalone_ag),
        (standalone_filename_alt, path_standalone_ag_alt),
        (master_filename, path_master_ag),
        (master_filename_alt, path_master_ag_alt)
    ]

    for fn, fpath in files_to_upload:
        print(f"Uploading {fn} to Google Drive...")
        cmd = [
            "rclone", "copyto",
            fpath,
            f"gdrive:{fn}",
            "--drive-root-folder-id", DRIVE_FOLDER_ID,
            "-v"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Uploaded {fn} successfully!")
        else:
            print(f"Failed to upload {fn}: {res.stderr}")

    return standalone_filename, master_filename

if __name__ == "__main__":
    ts_arg = sys.argv[1] if len(sys.argv) > 1 else None
    create_hq_accommodation_workbooks(ts_arg)
