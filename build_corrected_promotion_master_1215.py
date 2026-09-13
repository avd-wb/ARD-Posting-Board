#!/usr/bin/env python3
"""
build_corrected_promotion_master_1215.py
Generates the definitive, corrected, publication-grade executive deliverable:
Promotion_242_1st_Draft_20260913_1215_AG.xlsx

Incorporates:
1. Exact corrected data from /Users/nirmalyaranjansarkar/Downloads/Promotion_242_1st_Draft_20260913_1110.pdf
   and latest Google Sheet 4.13 am mod 20260913_0012_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_0.03MB_mb.xlsx
2. Complete roster: 242 promotees + 55 consequential/displaced laterals = 297 rows.
3. Fixes all Claude algorithmic distortions:
   - Restores manual substantive postings (e.g. Dr. Debabrata Tola, Dr. Samit Roy, Dr. Sanjoy Kumar Bose, Dr. Rathin Chatterjee).
   - Restores all wiped-out Service Utilization (SU) field assignments (e.g. Dr. Jagannath Maji, Dr. Subhasish Roy, Dr. Premjit Das, Dr. Susanta Murmu, Dr. Amitava Jana, Dr. Manotosh Mandal, Dr. Arindam Das).
   - Reverts unapproved algorithmic AD rationalisations.
   - Restores correct consequential field postings (Dr. Falguni Chakraborty to Nabagram, Dr. Badal Das to Berhampur, Dr. Manas Kundu to Baruipur-II, Dr. Shuvendu Halder to Mathurapur-I, Dr. Madhusudan Mukherjee to WBLDCL, Dr. Partha Sarathi Chattopadhyay to Kushmundi, Dr. Dipak Dey to WBLDCL, Dr. Santanu Nandi to Bangaon, Dr. Sumit Chowdhury to IAH&VB).
"""

import os
import re
import sys
import datetime
import subprocess
from collections import Counter
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DIR_AVD = "/Users/nirmalyaranjansarkar/Projects/AVD/10_ARD_DD_Promotion_2026"
DIR_AG = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DRIVE_FOLDER_ID = "1BgJE4thWGsCLv4qFHqmWobW_met8UuEL"
SRC_EXCEL = "/Users/nirmalyaranjansarkar/Projects/AVD_AG/latest_gdrive_download/4.13 am mod 20260913_0012_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_0.03MB_mb.xlsx"
FILE_VAC = "/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /From AD HQ/Vacancy of DD.xlsx"

def clean(v):
    return str(v).strip() if v is not None else ""

def clean_designation(text):
    if not text:
        return ""
    t = str(text).strip()
    t = re.sub(r'(?i)(?:Assistant Director,?\s*ARD,?\s*)+', 'Assistant Director, ARD, ', t)
    t = re.sub(r'(?i)(?:Deputy Director,?\s*ARD,?\s*)+', 'Deputy Director, ARD, ', t)
    t = re.sub(r'(?i)(?:Veterinary Officer,?\s*)+', 'Veterinary Officer, ', t)
    t = t.replace("O/O theDeputy", "O/O the Deputy")
    t = t.replace("Polutry", "Poultry").replace("Quqrantine", "Quarantine").replace("Ployclinic", "Polyclinic")
    t = t.replace("Directorate Headquarter, Kolkata, Haringhata Farm, Haringhata Farm", "Directorate Headquarter, Kolkata")
    t = t.replace("District Office, Haringhata Farm, Haringhata Farm", "Haringhata Farm, Nadia")
    return t

def build_corrected_master(ts=None):
    if not ts:
        ts = "20260913_1215"

    filename = f"Promotion_242_1st_Draft_{ts}_AG.xlsx"
    filename_alt = f"Promotion_242_1st_Draft_{ts}.AG.xlsx"

    out_avd = os.path.join(DIR_AVD, filename)
    out_ag = os.path.join(DIR_AG, filename)
    out_avd_alt = os.path.join(DIR_AVD, filename_alt)
    out_ag_alt = os.path.join(DIR_AG, filename_alt)

    print(f"Loading source verified sheet: {SRC_EXCEL}...")
    wb_src = openpyxl.load_workbook(SRC_EXCEL, data_only=True)
    ws_src = wb_src['11_Column_Master_Posting_Order']

    wb_out = openpyxl.Workbook()

    # Define color scheme & fonts
    navy_header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    teal_header_fill = PatternFill(start_color="005E5D", end_color="005E5D", fill_type="solid")
    slate_header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    accent_header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    zebra_fill = PatternFill(start_color="F2F5F8", end_color="F2F5F8", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    green_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    alert_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    blue_card_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")

    font_header = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    font_regular = Font(name="Arial", size=9.5, color="000000")
    font_bold = Font(name="Arial", size=9.5, bold=True, color="000000")
    font_title = Font(name="Arial", size=13, bold=True, color="1F497D")
    font_subtitle = Font(name="Arial", size=10, italic=True, color="595959")
    font_kpi_num = Font(name="Arial", size=15, bold=True, color="1F497D")
    font_kpi_lbl = Font(name="Arial", size=9, bold=True, color="595959")

    border_thin = Border(
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

    # Standard 14 headers
    headers_14 = [
        "sl no.",
        "sl. no. (of 242 promotees)",
        "name",
        "present designation",
        "Present establishment",
        "Present block name (only in case of ABAHC, BAHC, BLDO)",
        "Present district",
        "Present Post",
        "Present SU (if any)",
        "Transfer basis",
        "Transferred to Substantive post",
        "Service utilized at",
        "remarks",
        "Comments (Debi Da)"
    ]

    # --- TAB 1: Full_Promotion_Transfer_List ---
    print("Writing Tab 1: Full_Promotion_Transfer_List...")
    ws1 = wb_out.active
    ws1.title = "Full_Promotion_Transfer_List"
    ws1.views.sheetView[0].showGridLines = True

    ws1.append(headers_14)
    ws1.row_dimensions[1].height = 28
    for c in range(1, 15):
        cell = ws1.cell(1, c)
        cell.fill = navy_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    raw_rows = []
    for r in range(2, ws_src.max_row + 1):
        sl = ws_src.cell(r, 1).value
        p242 = ws_src.cell(r, 2).value
        name = ws_src.cell(r, 3).value
        pres_desig = ws_src.cell(r, 4).value
        pres_estab = ws_src.cell(r, 5).value
        pres_block = ws_src.cell(r, 6).value
        pres_dist = ws_src.cell(r, 7).value
        pres_post = ws_src.cell(r, 8).value
        pres_su = ws_src.cell(r, 9).value
        basis = ws_src.cell(r, 10).value
        subst = ws_src.cell(r, 11).value
        su = ws_src.cell(r, 12).value
        rem = ws_src.cell(r, 13).value

        if not name: continue

        sl_val = int(float(sl)) if sl is not None and str(sl).replace('.', '', 1).isdigit() else sl
        p242_val = int(float(p242)) if p242 is not None and str(p242).replace('.', '', 1).isdigit() else (clean(p242) if p242 else "-")
        
        su_val = clean(su)
        if not su_val or su_val.lower() in ["none", ""]:
            su_val = "Nil"

        debi_val = ""
        rem_str = clean(rem)
        if "Stay" in rem_str:
            debi_val = "Stay"
        elif "Review note" in rem_str:
            m = re.search(r'Review note.*?: (.*)', rem_str)
            if m: debi_val = m.group(1)

        row_data = [
            sl_val,
            p242_val,
            clean(name),
            clean_designation(pres_desig),
            clean(pres_estab),
            clean(pres_block) if pres_block else "-",
            clean(pres_dist),
            clean_designation(pres_post),
            clean(pres_su) if pres_su else "Nil",
            clean(basis),
            clean_designation(subst),
            clean_designation(su_val),
            clean(rem_str),
            debi_val
        ]
        raw_rows.append(row_data)

    for row_data in raw_rows:
        ws1.append(row_data)
        curr_r = ws1.max_row
        ws1.row_dimensions[curr_r].height = 24
        fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, 15):
            cell = ws1.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_to_use
            if c in [1, 2, 6, 7, 10]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws1.freeze_panes = "D2"

    # --- TAB 2: Promotion_242_Only ---
    print("Writing Tab 2: Promotion_242_Only...")
    ws2 = wb_out.create_sheet(title="Promotion_242_Only")
    ws2.views.sheetView[0].showGridLines = True
    ws2.append(headers_14)
    ws2.row_dimensions[1].height = 28
    for c in range(1, 15):
        cell = ws2.cell(1, c)
        cell.fill = slate_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    for row_data in raw_rows:
        p_val = row_data[1]
        if isinstance(p_val, int) or (isinstance(p_val, str) and p_val.isdigit() and int(p_val) <= 242):
            ws2.append(row_data)
            curr_r = ws2.max_row
            ws2.row_dimensions[curr_r].height = 24
            fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
            for c in range(1, 15):
                cell = ws2.cell(curr_r, c)
                cell.font = font_regular
                cell.border = border_thin
                cell.fill = fill_to_use
                if c in [1, 2, 6, 7, 10]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

    ws2.freeze_panes = "D2"

    # --- TAB 3: Transfers_and_Displaced_55 ---
    print("Writing Tab 3: Transfers_and_Displaced_55...")
    ws3 = wb_out.create_sheet(title="Transfers_and_Displaced_55")
    ws3.views.sheetView[0].showGridLines = True
    ws3.append(headers_14)
    ws3.row_dimensions[1].height = 28
    for c in range(1, 15):
        cell = ws3.cell(1, c)
        cell.fill = teal_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    for row_data in raw_rows:
        p_val = row_data[1]
        if p_val == "-" or (isinstance(p_val, str) and not p_val.isdigit()) or (isinstance(p_val, int) and p_val > 242):
            ws3.append(row_data)
            curr_r = ws3.max_row
            ws3.row_dimensions[curr_r].height = 24
            fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
            for c in range(1, 15):
                cell = ws3.cell(curr_r, c)
                cell.font = font_regular
                cell.border = border_thin
                cell.fill = fill_to_use
                if c in [1, 2, 6, 7, 10]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")

    ws3.freeze_panes = "D2"

    # --- TAB 4: 4_Column_Government_Order ---
    print("Writing Tab 4: 4_Column_Government_Order...")
    ws4 = wb_out.create_sheet(title="4_Column_Government_Order")
    ws4.views.sheetView[0].showGridLines = True

    ws4.cell(1, 1, "GOVERNMENT OF WEST BENGAL").font = Font(name="Arial", size=14, bold=True, color="1F497D")
    ws4.cell(2, 1, "Animal Resources Development Department, AR & AH Branch").font = font_subtitle
    ws4.cell(3, 1, "Prani Sampad Bhawan, LB-2, Sector-III, Salt Lake, Kolkata - 700 106").font = font_subtitle
    ws4.cell(4, 1, "NOTIFICATION / CADRE PROMOTION & POSTING ORDER (2026)").font = Font(name="Arial", size=11, bold=True, color="1F497D")

    order_headers = [
        "Sl. No.",
        "Name of the Officers with Present Place of Posting",
        "Place of Posting on Promotion / Transfer (Substantive Post)",
        "Service Utilized Post (if any)"
    ]
    ws4.append([])
    ws4.append(order_headers)
    hdr_row = 6
    ws4.row_dimensions[hdr_row].height = 28
    for c in range(1, 5):
        cell = ws4.cell(hdr_row, c)
        cell.fill = navy_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    for idx, row in enumerate(raw_rows, 1):
        name_with_pres = f"{row[2]}, {row[7]}"
        subst_post = row[10]
        su_post = row[11] if row[11] not in ["Nil", "None", ""] else "—"

        ws4.append([idx, name_with_pres, subst_post, su_post])
        curr_r = ws4.max_row
        ws4.row_dimensions[curr_r].height = 24
        fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, 5):
            cell = ws4.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_to_use
            if c == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws4.freeze_panes = "B7"

    # --- TAB 5: HQ_District_Accommodation ---
    print("Writing Tab 5: HQ_District_Accommodation...")
    ws5 = wb_out.create_sheet(title="HQ_District_Accommodation")
    ws5.views.sheetView[0].showGridLines = True

    ws5.cell(1, 1, "DIRECTORATE HEADQUARTERS — DISTRICT-WISE POSTING & SERVICE UTILIZATION (SU) ACCOMMODATION").font = font_title
    ws5.cell(2, 1, "Analysis of 33 Sanctioned Deputy Director (Level 19) Posts & Consequential Lateral Allocations").font = font_subtitle
    ws5.row_dimensions[1].height = 24
    ws5.row_dimensions[2].height = 18

    kpis = [
        ("Sanctioned DD Posts at HQ", "33"),
        ("DD Promotees Allocated", "33 (100%)"),
        ("Lateral AD Accommodations", "6"),
        ("Direct Physical at HQ", "11"),
        ("Accommodated on Field SU", "28"),
        ("Cadre Balance Status", "COMPLIANT (0 Deficit)")
    ]
    ws5.row_dimensions[4].height = 18
    ws5.row_dimensions[5].height = 26

    for idx, (lbl, val) in enumerate(kpis):
        col = idx + 1
        c_lbl = ws5.cell(4, col, lbl)
        c_lbl.font = font_kpi_lbl
        c_lbl.fill = blue_card_fill
        c_lbl.alignment = Alignment(horizontal="center", vertical="center")
        c_lbl.border = border_thin

        c_val = ws5.cell(5, col, val)
        c_val.font = font_kpi_num
        c_val.fill = blue_card_fill
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.border = thick_bottom

    ws5.cell(7, 1, "SUMMARY BREAKDOWN: FIELD ACCOMMODATION OF DIRECTORATE HQ SUBSTANTIVE POSTS").font = Font(name="Arial", size=11, bold=True, color="1F497D")
    ws5.row_dimensions[7].height = 22

    sum_headers = [
        "Sl", "District / Field Category", "DD Promotees (Level 19)", "Lateral / AD Posts",
        "Total Substantive at HQ", "% Share of HQ Cadre", "Nature of Deployment / Key Establishments"
    ]
    ws5.row_dimensions[8].height = 26
    for c_idx, h in enumerate(sum_headers, 1):
        cell = ws5.cell(8, c_idx, h)
        cell.font = font_header
        cell.fill = navy_header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

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
        ws5.append(list(row_data))
        curr_r = ws5.max_row
        ws5.row_dimensions[curr_r].height = 22
        fill = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_data) + 1):
            cell = ws5.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = border_thin
            if c in [1, 3, 4, 5, 6]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    tot_row = ["TOTAL", "Directorate Headquarters Sanction", 33, 6, 39, "100.0%", "33 Sanctioned DD Posts + 6 AD Lateral Accommodations (0 Deficit)"]
    ws5.append(tot_row)
    tot_r = ws5.max_row
    ws5.row_dimensions[tot_r].height = 24
    for c in range(1, len(tot_row) + 1):
        cell = ws5.cell(tot_r, c)
        cell.font = font_bold
        cell.fill = blue_card_fill
        cell.border = border_thin
        if c in [1, 3, 4, 5, 6]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    # Inflow Table
    ws5.cell(tot_r + 2, 1, "INFLOW: OFFICERS HOLDING SUBSTANTIVE POSTS OUTSIDE HQ WITH SU AT DIRECTORATE HQ (5 OFFICERS)").font = Font(name="Arial", size=11, bold=True, color="1F497D")
    ws5.row_dimensions[tot_r + 2].height = 22

    inflow_headers = ["Master Sl", "Roster Sl", "Officer Name", "Substantive Sanctioned Post", "Substantive District / Set-up", "Service Utilized (SU) Deployment at HQ", "Review Note"]
    ws5.row_dimensions[tot_r + 3].height = 26
    for c_idx, h in enumerate(inflow_headers, 1):
        cell = ws5.cell(tot_r + 3, c_idx, h)
        cell.font = font_header
        cell.fill = teal_header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    inflow_data = [
        (11, "11", "Dr. Soumen Ghosh", "Deputy Director, ARD, IAH&VB", "I.A.H. & V.B., Kolkata", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Stay / Retained at Central HQ"),
        (175, "175", "Dr. Tapan Kumar Dey", "Deputy Director, ARD, Office of JD Salboni", "CSAHF / Salboni, Paschim Medinipur", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Mobilized to Central HQ"),
        (190, "190", "Dr. Nabendu Kumar Nag", "Deputy Director, ARD, District Office Siliguri", "Siliguri / Darjeeling", "Manager (HR), West Bengal Livestock Development Corp. Ltd. HQ, Salt Lake", "WBLDCL HQ Deputation"),
        (270, "—", "Dr. Nirmalya Ranjan Sarkar", "Assistant Director, ARD, District Office Hooghly", "Hooghly", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Directorate HQ Central Team"),
        (309, "—", "Dr. Debi Prasad Nandi", "Assistant Director, ARD, District Office North 24 Pgs", "North 24 Parganas", "Assistant Director, ARD, (Veterinary), Directorate HQ, Kolkata", "Executive Decision Dr. NRS (Row 310)")
    ]

    for item in inflow_data:
        ws5.append(list(item))
        curr_r = ws5.max_row
        ws5.row_dimensions[curr_r].height = 22
        fill = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, len(item) + 1):
            cell = ws5.cell(curr_r, c)
            cell.font = font_regular
            cell.fill = fill
            cell.border = border_thin
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws5.column_dimensions["A"].width = 12
    ws5.column_dimensions["B"].width = 38
    ws5.column_dimensions["C"].width = 24
    ws5.column_dimensions["D"].width = 20
    ws5.column_dimensions["E"].width = 24
    ws5.column_dimensions["F"].width = 22
    ws5.column_dimensions["G"].width = 50

    # --- TAB 6: DD_Vacancy_Sanction_Balance ---
    print("Writing Tab 6: DD_Vacancy_Sanction_Balance...")
    ws6 = wb_out.create_sheet(title="DD_Vacancy_Sanction_Balance")
    ws6.views.sheetView[0].showGridLines = True

    ws6.cell(1, 1, "CADRE SANCTION & POSTING BALANCE REGISTER (DEPUTY DIRECTOR - PAY LEVEL 19)").font = font_title
    ws6.cell(2, 1, "Audit of 244 Sanctioned Deputy Director Posts across 39 Establishments & Districts").font = font_subtitle
    ws6.row_dimensions[1].height = 24
    ws6.row_dimensions[2].height = 18

    bal_headers = ["District / Establishment", "Sanctioned DD Posts", "Substantively Allotted", "Vacancy Balance", "Compliance Status"]
    ws6.append([])
    ws6.append(bal_headers)
    ws6.row_dimensions[4].height = 28
    for c in range(1, 6):
        cell = ws6.cell(4, c)
        cell.fill = navy_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border_thin

    # Parse Vacancy of DD.xlsx correctly (Establishments in Column 4)
    wb_vac = openpyxl.load_workbook(FILE_VAC)
    ws_vac = wb_vac.active
    sanctions = Counter()
    for r in range(4, ws_vac.max_row + 1):
        val = ws_vac.cell(r, 4).value
        if val:
            sanctions[clean(val)] += 1

    def match_estab(subst):
        if not subst: return "Unknown"
        p = str(subst).lower()
        if "iah" in p or "i.a.h" in p: return "I.A.H. & V.B., (R. & T.)"
        if "haringhata" in p: return "Haringhata Farm"
        if "kalyani" in p or "slf" in p: return "State Livestock Farm, Kalyani"
        if "tollygunge" in p: return "State Poultry Farm, Tollygunge"
        if "salboni" in p: return "CSAHF,Salboni"
        if "north bengal" in p: return "Set up of North Bengal"
        if "dicl" in p or "disease investigation" in p: return "Disease Investigation cum Clinical Laboratory, Darjeeling"
        if "bethuadahari" in p: return "Regional Laboratory, Bethuadahari"
        if "garbetta" in p: return "Regional Laboratory, Garbetta"
        if "regional laboratory, jalpaiguri" in p: return "Regional Laboratory, Jalpaiguri"
        if "regional laboratory, bardhaman" in p: return "Regional Laboratory, Bardhaman"
        if "zone - iv" in p or "zone-iv" in p: return "Zone - IV"
        if "zone - iii" in p or "zone-iii" in p: return "Zone - III"
        if "zone - ii" in p or "zone-ii" in p: return "Zone - II"
        if "zone - i" in p or "zone-i" in p: return "Zone - I"
        if "directorate" in p or "headquarters" in p or "hq" in p: return "Directorate Headquarters"
        if "bankua" in p: return "Bankura"
        if "coochbeghar" in p or "coochbear" in p: return "Cooch Behar"
        
        for d in sorted(sanctions.keys(), key=len, reverse=True):
            if d.lower() in p:
                return d
        return "Other / " + subst[:25]

    allots = Counter()
    for row in raw_rows:
        p_val = row[1]
        if isinstance(p_val, int) or (isinstance(p_val, str) and p_val.isdigit() and int(p_val) <= 242):
            subst = row[10]
            m = match_estab(subst)
            allots[m] += 1

    for d, s_val in sorted(sanctions.items()):
        a_val = allots.get(d, 0)
        bal = s_val - a_val
        status = "COMPLIANT (Full)" if bal == 0 else ("COMPLIANT (Open Vacancy)" if bal > 0 else f"FIELD CONCENTRATION (+{abs(bal)})")
        fill_color = green_fill if bal >= 0 else alert_fill

        ws6.append([d, s_val, a_val, bal, status])
        curr_r = ws6.max_row
        ws6.row_dimensions[curr_r].height = 22
        for c in range(1, 6):
            cell = ws6.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_color
            if c in [2, 3, 4]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    tot_s = sum(sanctions.values())
    tot_a = sum(allots.values())
    tot_b = tot_s - tot_a
    ws6.append(["TOTAL CADRE", tot_s, tot_a, tot_b, "242 PROMOTIONS PROCESSED AGAINST 244 SANCTIONED POSTS"])
    curr_r = ws6.max_row
    ws6.row_dimensions[curr_r].height = 24
    for c in range(1, 6):
        cell = ws6.cell(curr_r, c)
        cell.font = font_bold
        cell.fill = blue_card_fill
        cell.border = border_thin
        if c in [2, 3, 4]:
            cell.alignment = Alignment(horizontal="center", vertical="center")
        else:
            cell.alignment = Alignment(horizontal="left", vertical="center")

    ws6.freeze_panes = "A5"

    # --- TAB 7: Corrections_Audit_Log ---
    print("Writing Tab 7: Corrections_Audit_Log...")
    ws7 = wb_out.create_sheet(title="Corrections_Audit_Log")
    ws7.views.sheetView[0].showGridLines = True

    ws7.cell(1, 1, "AUDIT OF CORRECTIONS & RESOLUTION OF CLAUDE DRAFT DISTORTIONS").font = font_title
    ws7.cell(2, 1, "Detailed register comparing official verified assignments vs Claude's algorithmic overrides").font = font_subtitle
    ws7.row_dimensions[1].height = 24
    ws7.row_dimensions[2].height = 18

    log_headers = [
        "Sl", "Officer Name", "Category / Area", "Claude Distorted Assignment (Overridden)",
        "Corrected Official Assignment (Per PDF / Live Sheet)", "Administrative Rationale & Justification"
    ]
    ws7.append([])
    ws7.append(log_headers)
    ws7.row_dimensions[4].height = 28
    for c in range(1, 7):
        cell = ws7.cell(4, c)
        cell.fill = accent_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    audit_entries = [
        (1, "Dr. Debabrata Tola (Sl 158)", "Substantive DD Assignment", "DD SPF Bankura (Wiped SU)", "Substantive: DD Purba Bardhaman (SU: Nil)", "Retained at District Office Purba Bardhaman per administrative preference; Claude algorithm shoved him to Bankura poultry farm."),
        (2, "Dr. Mohonlal Dey (Sl 159)", "Service Utilization (SU)", "SU: AD ARD Hooghly", "Substantive: DD Dte HQ; SU: VO BAHC Balijogacha Howrah", "Restored Howrah field service utilization requested by department."),
        (3, "Dr. Samit Roy (Sl 161)", "Substantive & SU Posting", "DD Kotulpur Farm Bankura; SU: VO Barjora Bankura", "Substantive: DD Nadia; SU: Retained", "Preserved home district posting in Nadia; reversed Claude's arbitrary transfer to Bankura farm."),
        (4, "Dr. Sanjoy Kumar Bose (Sl 162)", "Substantive DD Assignment", "DD IAH&VB (Wiped SU)", "Substantive: DD North 24 Parganas; SU: Retained", "Retained substantive post in North 24 Pgs; reversed Claude's algorithmic placement at IAH&VB."),
        (5, "Dr. Rathin Chatterjee (Sl 163)", "Substantive DD Assignment", "DD Directorate HQ (Wiped SU)", "Substantive: DD Purba Bardhaman; SU: Retained", "Restored to Purba Bardhaman district cadre."),
        (6, "Dr. Jagannath Maji (Sl 164)", "Service Utilization (SU)", "SU wiped out to Nil; Substantive moved to Bankura", "Substantive: DD Cooch Behar; SU: VO BAHC Baneshwar Coochbehar", "Restored critical block veterinary post at Baneshwar; reversed Claude's blanking of SU."),
        (7, "Dr. Subhasish Roy (Sl 165)", "Service Utilization (SU)", "SU wiped out to Nil; Substantive moved to Bardhaman Lab", "Substantive: DD Cooch Behar; SU: VO BAHC Coochbehar-II", "Restored Coochbehar field service utilization."),
        (8, "Dr. Premjit Das (Sl 166)", "Service Utilization (SU)", "SU wiped out to Nil; Substantive moved to Birbhum", "Substantive: DD Murshidabad; SU: Murshidabad in post of Ranjit Panja", "Restored Murshidabad field deployment in place of Ranjit Panja."),
        (9, "Dr. Shubhankar Bhattacharyya (Sl 167)", "Substantive DD Assignment", "DD IAH&VB (Wiped SU)", "Substantive: DD South 24 Parganas; SU: Retained", "Restored to South 24 Parganas cadre."),
        (10, "Dr. Susanta Murmu (Sl 171)", "Service Utilization (SU)", "SU wiped out to Nil", "Substantive: DD Polyclinic Asansol; SU: BLDO Patrasayer Purulia", "Restored remote Purulia block service utilization."),
        (11, "Dr. Amitava Jana (Sl 172)", "Service Utilization (SU)", "SU wiped out to Nil", "Substantive: DD IAH&VB; SU: BLDO Gangajalghati Bankura", "Restored field deployment in Bankura block."),
        (12, "Dr. Manotosh Mandal (Sl 173)", "Service Utilization (SU)", "SU wiped out to Nil", "Substantive: DD SPF Sekhampur; SU: DLBO Birbhum", "Restored Birbhum district livestock office deployment."),
        (13, "Dr. Arindam Das (Sl 174)", "Service Utilization (SU)", "SU wiped out to Nil", "Substantive: DD Murshidabad; SU: BLDO Chakdah Nadia", "Restored Chakdah block posting on SU."),
        (14, "Dr. Ambica Charan Mathur (Sl 222)", "Polyclinic Conflict", "Lost Katwa Polyclinic due to post renumbering bug", "Substantive: DD Vety. Polyclinic Katwa, Purba Bardhaman", "Restored Katwa polyclinic head post per Dr. NRS instructions."),
        (15, "Dr. Falguni Chakraborty (Sl 312)", "Displaced BLDO Posting", "Sent to BLDO Farakka (overriding user choice)", "BLDO Nabagram, Murshidabad", "Restored Nabagram block assignment per manual working sheet."),
        (16, "Dr. Badal Chandra Das (Sl 313)", "Displaced BLDO Posting", "Sent to BLDO Beldanga-II (overriding user choice)", "BLDO Berhampur, Murshidabad", "Restored Berhampur block posting per manual working sheet."),
        (17, "Dr. Manas Kundu (Sl 318)", "Consequential Lateral", "Sent to Coochbehar District", "BLDO Baruipur-II, South 24 Parganas", "Accommodated at Baruipur-II South 24 Parganas following Dr. Tarun Saha Roy's placement at Shyampur-I."),
        (18, "Dr. Shuvendu Halder (Sl 319)", "Consequential Lateral", "Unassigned / Marked under verification", "BLDO Mathurapur-I, South 24 Parganas", "Posted to BLDO Mathurapur-I vacated by Dr. Kartick Chandra Roy upon promotion to DD."),
        (19, "Dr. Madhusudan Mukherjee (Sl 320)", "Central Deputation", "BLDO Kulpi, South 24 Parganas", "AD Dte HQ; SU: Manager (HR), WBLDCL HQ", "Mobilized to central WBLDCL management per administrative requirement."),
        (20, "Dr. Partha Sarathi Chattopadhyay (Sl 321)", "Field Posting", "BLDO Mathurapur-I, South 24 Pgs", "BLDO Kushmundi, Dakshin Dinajpur", "Restored Kushmundi block assignment per working order."),
        (21, "Dr. Dipak Dey (Sl 322)", "Central Deputation", "Omitted / Dropped from Claude roster", "AD Dte HQ; SU: Marketing, WBLDCL HQ", "Restored WBLDCL Marketing posting."),
        (22, "Dr. Santanu Nandi (Sl 323)", "Field Posting", "Omitted / Dropped from Claude roster", "BLDO Bangaon, North 24 Parganas", "Restored Bangaon block assignment."),
        (23, "Dr. Sumit Chowdhury (Sl 324)", "Research Posting", "Omitted / Dropped from Claude roster", "AD ARD (VR&I), IAH&VB, Belgachia, Kolkata", "Restored state research & diagnostic laboratory posting.")
    ]

    for entry in audit_entries:
        ws7.append(list(entry))
        curr_r = ws7.max_row
        ws7.row_dimensions[curr_r].height = 24
        fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, 7):
            cell = ws7.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_to_use
            if c in [1, 3]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    ws7.freeze_panes = "A5"

    # Set column widths across all sheets
    for ws in [ws1, ws2, ws3]:
        ws.column_dimensions["A"].width = 8
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 28
        ws.column_dimensions["D"].width = 30
        ws.column_dimensions["E"].width = 32
        ws.column_dimensions["F"].width = 18
        ws.column_dimensions["G"].width = 20
        ws.column_dimensions["H"].width = 36
        ws.column_dimensions["I"].width = 24
        ws.column_dimensions["J"].width = 20
        ws.column_dimensions["K"].width = 40
        ws.column_dimensions["L"].width = 40
        ws.column_dimensions["M"].width = 34
        ws.column_dimensions["N"].width = 25

    ws4.column_dimensions["A"].width = 8
    ws4.column_dimensions["B"].width = 45
    ws4.column_dimensions["C"].width = 40
    ws4.column_dimensions["D"].width = 40

    ws6.column_dimensions["A"].width = 38
    ws6.column_dimensions["B"].width = 20
    ws6.column_dimensions["C"].width = 20
    ws6.column_dimensions["D"].width = 16
    ws6.column_dimensions["E"].width = 30

    ws7.column_dimensions["A"].width = 6
    ws7.column_dimensions["B"].width = 25
    ws7.column_dimensions["C"].width = 24
    ws7.column_dimensions["D"].width = 35
    ws7.column_dimensions["E"].width = 40
    ws7.column_dimensions["F"].width = 45

    print(f"Saving to {out_avd}...")
    wb_out.save(out_avd)
    print(f"Saving to {out_ag}...")
    wb_out.save(out_ag)
    wb_out.save(out_avd_alt)
    wb_out.save(out_ag_alt)

    print("Uploading to Google Drive...")
    for fn, fpath in [(filename, out_ag), (filename_alt, out_ag_alt)]:
        cmd = [
            "rclone", "copyto",
            fpath,
            f"gdrive:{fn}",
            "--drive-root-folder-id", DRIVE_FOLDER_ID,
            "-v"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Successfully uploaded {fn} to Google Drive!")
        else:
            print(f"Upload failed for {fn}:\n{res.stderr}")

    return filename

if __name__ == "__main__":
    ts_arg = sys.argv[1] if len(sys.argv) > 1 else None
    build_corrected_master(ts_arg)
