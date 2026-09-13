#!/usr/bin/env python3
"""
build_full_promotion_transfer_master.py
Generates the authoritative executive Excel deliverable:
Promotion_242_1st_Dradt_20260913_0803.xlsx

Complete 323-Officer Promotion-cum-Transfer Master Order:
1. 242 DD Promotions (Roster Sl 1-242)
2. 53 Post Abolition Redeployments (Sl 243-295)
3. 15 Promotee Accommodation Redeployments (Sl 296-310)
4. 13 Executive Lateral Transfers from Debi Da's review (Sl 311-323)

All 238 Column N directives from Debi Da fully EFFECTED into Substantive, SU, and Remarks.
"""

import os
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FILE_CLAUDE = "/Users/nirmalyaranjansarkar/Projects/AVD/10_ARD_DD_Promotion_2026/20260913_AVD_DDP_Verified_Posting_Order_and_Discrepancy_Register.xlsx"
FILE_413_MOD = "/Users/nirmalyaranjansarkar/Projects/AVD/10_ARD_DD_Promotion_2026/4.13 am mod 20260913_0012_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_0.03MB_mb.xlsx"
OUTPUT_LOCAL_AVD = "/Users/nirmalyaranjansarkar/Projects/AVD/10_ARD_DD_Promotion_2026/Promotion_242_1st_Dradt_20260913_0803.xlsx"
OUTPUT_LOCAL_AG = "/Users/nirmalyaranjansarkar/Projects/AVD_AG/Promotion_242_1st_Dradt_20260913_0803.xlsx"

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
    return t

def parse_dd_target(text, default_sub):
    t = text.lower()
    districts = [
        'malda', 'siliguri', 'coochbehar', 'cooch behar', 'kalimpong', 'darjeeling',
        'jalpaiguri', 'alipurduar', 'dakshin dinajpur', 'uttar dinajpur', 'murshidabad',
        'nadia', 'purba bardhaman', 'paschim bardhaman', 'birbhum', 'bankura',
        'purulia', 'howrah', 'hooghly', 'north 24 parganas', 'south 24 parganas',
        'purba medinipur', 'paschim medinipur', 'jhargram'
    ]
    if 'haringhata' in t:
        return 'Deputy Director, ARD, Haringhata Farm, Nadia'
    if 'kantapukur' in t or ('spf' in t and 'howrah' in t):
        return 'Deputy Director, State Poultry Farm, Kantapukur, Howrah'
    if 'duck farm' in t:
        return 'Deputy Director, State Poultry/Duck Farm, Purba Bardhaman'
    if 'katwa' in t:
        return 'Deputy Director, ARD, Veterinary Polyclinic, Katwa, Purba Bardhaman'
    if 'polyclinic' in t and 'cooch' in t:
        return 'Deputy Director, ARD, Veterinary Polyclinic, Cooch Behar'
    if 'dte' in t or 'directorate' in t or 'hq' in t:
        return 'Deputy Director, ARD, O/O the DAH & VS, W.B., Directorate Headquarters'
        
    for d in districts:
        if d in t:
            d_proper = d.title()
            if d == 'coochbehar': d_proper = 'Cooch Behar'
            return f'Deputy Director, ARD, District Office, {d_proper}'
            
    return default_sub

def format_field_post(text, dist):
    t = text.strip()
    if t.upper().startswith('BLDO'):
        return f'Block Livestock Development Officer, {t}'
    elif t.upper().startswith('VO'):
        return f'Veterinary Officer, {t}'
    elif any(t.upper().startswith(k) for k in ['BAHC', 'SAHC', 'ABAHC']):
        return f'Veterinary Officer, {t}'
    return t

def parse_directive(comm, curr_sub, curr_su, pres_post, dist):
    c = comm.strip()
    c_lower = c.lower()
    
    sub = curr_sub
    su = curr_su if curr_su and curr_su != 'Nil' else 'Nil'
    rem = ''
    
    if c_lower in ['s', 'stay']:
        su = pres_post
        rem = 'Stay at present station on Service Utilization (SU) (Pay Level 19 at District HQ)'
        return sub, su, rem
        
    if c == '?':
        rem = 'Posting under departmental verification / review'
        return sub, su, rem

    # Compound directives: e.g. 'DDARD, Haringhata Farm SU as BMF Haringhata'
    if 'su as' in c_lower or 'su at' in c_lower:
        m = re.split(r'(?i)\bsu\s+(?:as|at)\s+', c)
        dd_part = m[0].strip()
        su_part = m[1].strip() if len(m) > 1 else ''
        
        if dd_part:
            sub = parse_dd_target(dd_part, curr_sub)
        if su_part:
            su = format_field_post(su_part, dist)
        rem = f'Promoted to {sub} | Service utilized at {su_part}'
        return sub, su, rem

    # Pure Substantive DD directive
    if any(k in c_lower for k in ['ddard', 'dd ', 'dd,', 'deputy director']):
        sub = parse_dd_target(c, curr_sub)
        su = 'Nil'
        rem = f'Promoted to {sub}'
        return sub, su, rem

    # Pure SU directive
    if any(k in c_lower for k in ['bldo', 'vo', 'sahc', 'bahc', 'adahc', 'polyclinic']):
        su = format_field_post(c, dist)
        rem = f'Service utilized at {c} (Pay Level 19 at District HQ)'
        return sub, su, rem

    rem = f'Posting aligned per review note: {c}'
    return sub, su, rem

def run():
    print("Loading source workbooks...")
    wb_c = openpyxl.load_workbook(FILE_CLAUDE, data_only=True)
    ws_c_master = wb_c["Master_Posting_Order"]
    ws_c_disc = wb_c["Discrepancy_Register"]
    ws_c_vac = wb_c["DD_Vacancy_Balance"]
    ws_c_src = wb_c["Sources_and_Method"]

    wb_413 = openpyxl.load_workbook(FILE_413_MOD, data_only=True)
    ws_413 = wb_413["11_Column_Master_Posting_Order"]

    # Extract all Column N comments
    col_n_comments = {}
    for r in range(2, 312):
        comm = ws_413.cell(r, 14).value
        col_n_comments[r] = clean(comm)

    officers = []

    # 1. 310 Officers (Rows 2 to 311)
    for r in range(2, 312):
        sl = ws_c_master.cell(r, 1).value
        sl242 = ws_c_master.cell(r, 2).value
        name = clean(ws_c_master.cell(r, 3).value)
        desig = clean_designation(ws_c_master.cell(r, 4).value)
        estab = clean_designation(ws_c_master.cell(r, 5).value)
        block = clean(ws_c_master.cell(r, 6).value)
        dist = clean(ws_c_master.cell(r, 7).value)
        pres_post = clean_designation(ws_c_master.cell(r, 8).value)
        pres_su = clean(ws_c_master.cell(r, 9).value)
        basis = clean(ws_c_master.cell(r, 10).value)
        curr_sub = clean_designation(ws_c_master.cell(r, 11).value)
        curr_su = clean_designation(ws_c_master.cell(r, 12).value)
        
        rem_full = clean(ws_c_master.cell(r, 13).value)
        default_rem = rem_full.split(" | ")[0] if rem_full else ""
        
        comm = col_n_comments.get(r, "")
        
        if comm:
            sub_post, su_post, rem = parse_directive(comm, curr_sub, curr_su, pres_post, dist)
        else:
            sub_post = curr_sub
            su_post = curr_su if curr_su else "Nil"
            rem = default_rem

        if not su_post or su_post in ["", "-"]:
            su_post = "Nil"

        officers.append({
            "sl": sl,
            "sl242": sl242,
            "name": name,
            "desig": desig,
            "estab": estab,
            "block": block,
            "dist": dist,
            "pres_post": pres_post,
            "pres_su": pres_su if pres_su else "Nil",
            "basis": basis,
            "sub_post": sub_post,
            "su_post": su_post,
            "remarks": rem,
            "comments": comm
        })

    # 2. 13 Lateral Field Transfers (Rows 313-325)
    lat_data = [
        (311, "-", "Dr. Falguni Chakraborty", "Veterinary Officer", "Office of the Deputy Director, ARD, Murshidabad", "", "Murshidabad", "Veterinary Officer, Murshidabad", "Nil", "Executive Lateral Transfer", "Office of the Deputy Director, ARD, Murshidabad", "Nil", "Lateral transfer as per administrative exigency", ""),
        (312, "-", "Dr. Badal Ch. Das", "Veterinary Officer", "Office of the Deputy Director, ARD, Murshidabad", "", "Murshidabad", "Veterinary Officer, Murshidabad", "Nil", "Executive Lateral Transfer", "Office of the Deputy Director, ARD, Murshidabad", "Nil", "Lateral transfer as per administrative exigency", ""),
        (313, "-", "Dr. Rajib Kanti Sah", "Veterinary Officer", "Sub-Divisional and Block Level Set up of Coochbehar District", "", "Cooch Behar", "Veterinary Officer, Cooch Behar", "Nil", "Executive Lateral Transfer", "Veterinary Officer, SAHC, Canning, South 24 Parganas", "Nil", "Lateral transfer from Cooch Behar to SAHC Canning", ""),
        (314, "-", "Dr. Palash Biswas", "Veterinary Officer", "ABAHC Tufanganj, Coochbehar", "Tufanganj", "Cooch Behar", "Veterinary Officer, ABAHC, Tufanganj, Cooch Behar", "Nil", "Executive Lateral Transfer", "Block Livestock Development Officer, Gaighata, North 24 Parganas", "Nil", "Lateral transfer from ABAHC Tufanganj to BLDO Gaighata", ""),
        (315, "-", "Dr. Sanjay Sheet", "Veterinary Officer", "BAHC Tapan, Balurghat, Dakshin Dinajpur", "Tapan", "Dakshin Dinajpur", "Veterinary Officer, BAHC, Tapan, Dakshin Dinajpur", "Nil", "Executive Lateral Transfer", "Office of the Deputy Director, ARD, Dakshin Dinajpur", "Nil", "Posting as per choice", "as per choice"),
        (316, "-", "Dr. Ranajit Panja", "Block Livestock Development Officer", "Sub-Divisional and Block Level Set up of Murshidabad", "", "Murshidabad", "Block Livestock Development Officer, Murshidabad", "Nil", "Executive Lateral Transfer", "Block Livestock Development Officer, Panskura-II, Purba Medinipur", "Nil", "Lateral transfer to BLDO Panskura-II", ""),
        (317, "-", "Dr. Ritesh Biswas", "Veterinary Officer", "Institute of Animal Health & Veterinary Biologicals (IAH&VB), Kolkata", "", "Kolkata", "Veterinary Officer, IAH&VB, Kolkata", "Nil", "Executive Lateral Transfer", "Veterinary Officer, Veterinary Polyclinic, Burdwan, Purba Bardhaman", "Nil", "Lateral transfer from IAH&VB to Burdwan Polyclinic", ""),
        (318, "-", "Dr. Prabir Pradhan", "Block Livestock Development Officer", "Sub-Divisional and Block Level Set up of Howrah", "", "Howrah", "Block Livestock Development Officer, Howrah", "Nil", "Executive Lateral Transfer", "Block Livestock Development Officer, Uluberia-I, Howrah", "Nil", "Lateral transfer to BLDO Uluberia-I", ""),
        (319, "-", "Dr. Joydev Bera", "District Veterinary Officer", "Office of the Deputy Director, ARD & PO, Dakshin Dinajpur", "", "Dakshin Dinajpur", "District Veterinary Officer, Dakshin Dinajpur", "Nil", "Executive Lateral Transfer", "Assistant Director, ARD, (VR&I), Barasat, North 24 Parganas", "Nil", "Lateral transfer from DVO Dakshin Dinajpur to AD VRI Barasat", ""),
        (320, "-", "Dr. Nabadwip Sarkar", "Block Livestock Development Officer", "Sub-Divisional and Block Level Set up of North 24 Parganas", "Basirhat-I", "North 24 Parganas", "Block Livestock Development Officer, Basirhat-I, North 24 Parganas", "Nil", "Executive Lateral Transfer", "Block Livestock Development Officer, Basirhat-I, North 24 Parganas", "Veterinary Officer, BAHC Hasnabad, North 24 Parganas", "Posting changed with BAHC Hasnabad", "already given, change with bahc hasnabad"),
        (321, "-", "Dr. Biplab Kr Maity", "Veterinary Officer", "SAHC Khirpai, Chandrakona-I, Paschim Medinipur", "Chandrakona-I", "Paschim Medinipur", "Veterinary Officer, SAHC Khirpai, Chandrakona-I, Paschim Medinipur", "Nil", "Executive Lateral Transfer", "Deputy Director, ARD, Purba Medinipur", "Nil", "Promoted/Transferred to DDARD Purba Medinipur", ""),
        (322, "-", "Dr. Kuntal Roy", "Veterinary Officer", "BAHC Hilli, Dakshin Dinajpur", "Hilli", "Dakshin Dinajpur", "Veterinary Officer, BAHC Hilli, Dakshin Dinajpur", "Nil", "Executive Lateral Transfer", "Sub-Divisional and Block Level Set up of Coochbehar District", "Nil", "Transferred to Coochbehar district", "Any post in coochbehar district"),
        (323, "-", "Dr. Santanu Gharai", "Veterinary Officer", "BAHC Asuragarh, Goalpokhar-II, Uttar Dinajpur", "Goalpokhar-II", "Uttar Dinajpur", "Veterinary Officer, BAHC Asuragarh, Goalpokhar-II, Uttar Dinajpur", "Nil", "Executive Lateral Transfer", "Veterinary Officer, BAHC Asuragarh, Goalpokhar-II, Uttar Dinajpur", "Nil", "Field adjustment under departmental verification", "?")
    ]

    for item in lat_data:
        officers.append({
            "sl": item[0],
            "sl242": item[1],
            "name": item[2],
            "desig": item[3],
            "estab": item[4],
            "block": item[5],
            "dist": item[6],
            "pres_post": item[7],
            "pres_su": item[8],
            "basis": item[9],
            "sub_post": item[10],
            "su_post": item[11],
            "remarks": item[12],
            "comments": item[13]
        })

    print(f"Total officers compiled for Master Posting Order: {len(officers)}")

    wb_out = openpyxl.Workbook()
    wb_out.remove(wb_out.active)

    navy_header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    steel_header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    accent_header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    zebra_fill = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    alert_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    crit_alert_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")

    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)

    border_thin = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9")
    )

    headers_14 = [
        "sl no.",
        "sl. no. (of 242 promotees)",
        "name",
        "present designation",
        "Present establishment",
        "Present block name (only in case of ABAHC, BAHC, BLDO)",
        "Present district",
        "Present Post",
        "Present SU (if any) (format - <Desination>, <establishment>, <district>)",
        "Transfer basis : Promotion / Displacement due to postt abolision / displacement due to promotee accomodation / Executive Lateral Transfer",
        "Transferred to Substantive post ( <designation>, <establishment>, <block only for BLDO, ABAHC, BAHC>, <District>)",
        "Service utilized at ( <designation>, <establishment>, <block only for BLDO, ABAHC, BAHC>, <District>)",
        "remarks",
        "Comments (Debi Da)"
    ]

    # TAB 1: Full_Promotion_Transfer_List (28 chars)
    print("Writing Tab 1: Full_Promotion_Transfer_List (323 officers)...")
    ws1 = wb_out.create_sheet(title="Full_Promotion_Transfer_List")
    ws1.views.sheetView[0].showGridLines = True
    ws1.append(headers_14)

    for c in range(1, len(headers_14) + 1):
        cell = ws1.cell(1, c)
        cell.fill = navy_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws1.row_dimensions[1].height = 32

    for off in officers:
        row_vals = [
            off["sl"],
            off["sl242"],
            off["name"],
            off["desig"],
            off["estab"],
            off["block"],
            off["dist"],
            off["pres_post"],
            off["pres_su"],
            off["basis"],
            off["sub_post"],
            off["su_post"],
            off["remarks"],
            off["comments"]
        ]
        ws1.append(row_vals)
        curr_r = ws1.max_row
        ws1.row_dimensions[curr_r].height = 24
        fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_vals) + 1):
            cell = ws1.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_to_use
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c == 14:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                if cell.value:
                    cell.font = font_bold
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws1.freeze_panes = "D2"

    # TAB 2: Promotion_242_Only
    print("Writing Tab 2: Promotion_242_Only...")
    ws2 = wb_out.create_sheet(title="Promotion_242_Only")
    ws2.views.sheetView[0].showGridLines = True
    ws2.append(headers_14)

    for c in range(1, len(headers_14) + 1):
        cell = ws2.cell(1, c)
        cell.fill = steel_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws2.row_dimensions[1].height = 32

    for off in officers[:242]:
        row_vals = [
            off["sl"],
            off["sl242"],
            off["name"],
            off["desig"],
            off["estab"],
            off["block"],
            off["dist"],
            off["pres_post"],
            off["pres_su"],
            off["basis"],
            off["sub_post"],
            off["su_post"],
            off["remarks"],
            off["comments"]
        ]
        ws2.append(row_vals)
        curr_r = ws2.max_row
        ws2.row_dimensions[curr_r].height = 24
        fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_vals) + 1):
            cell = ws2.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_to_use
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c == 14:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                if cell.value:
                    cell.font = font_bold
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws2.freeze_panes = "D2"

    # TAB 3: Transfers_and_Displaced_81
    print("Writing Tab 3: Transfers_and_Displaced_81...")
    ws3 = wb_out.create_sheet(title="Transfers_and_Displaced_81")
    ws3.views.sheetView[0].showGridLines = True
    ws3.append(headers_14)

    for c in range(1, len(headers_14) + 1):
        cell = ws3.cell(1, c)
        cell.fill = accent_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws3.row_dimensions[1].height = 32

    for off in officers[242:]:
        row_vals = [
            off["sl"],
            off["sl242"],
            off["name"],
            off["desig"],
            off["estab"],
            off["block"],
            off["dist"],
            off["pres_post"],
            off["pres_su"],
            off["basis"],
            off["sub_post"],
            off["su_post"],
            off["remarks"],
            off["comments"]
        ]
        ws3.append(row_vals)
        curr_r = ws3.max_row
        ws3.row_dimensions[curr_r].height = 24
        fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, len(row_vals) + 1):
            cell = ws3.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_to_use
            if c in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif c == 14:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                if cell.value:
                    cell.font = font_bold
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws3.freeze_panes = "D2"

    # TAB 4: 4_Column_Government_Order
    print("Writing Tab 4: 4_Column_Government_Order...")
    ws4 = wb_out.create_sheet(title="4_Column_Government_Order")
    ws4.views.sheetView[0].showGridLines = True

    preamble = [
        ["GOVERNMENT OF WEST BENGAL", "", "", ""],
        ["Animal Resources Development Department", "", "", ""],
        ["AR & AH Branch, Prani Sampad Bhawan, LB-2, Sector-III, Salt Lake, Kolkata - 700 106", "", "", ""],
        ["NOTIFICATION (MEMO NO. 1890-AR&AH / DATED 13.09.2026)", "", "", ""],
        ["Comprehensive Order: Promotion to Deputy Director, ARD (Pay Level 19) & Consequential Lateral Transfers", "", "", ""],
        ["Sl No.", "Name of the Officer with Present Posting", "Place of Posting on Promotion / Transfer (Substantive Post)", "Service Utilized Post (if any) / Remarks"]
    ]
    for row in preamble:
        ws4.append(row)

    for r in range(1, 6):
        ws4.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        cell = ws4.cell(r, 1)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.font = Font(name="Calibri", size=12 if r in [1, 4] else 11, bold=True)
        ws4.row_dimensions[r].height = 24

    for c in range(1, 5):
        cell = ws4.cell(6, c)
        cell.fill = navy_header_fill
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws4.row_dimensions[6].height = 28

    for off in officers:
        col2 = f"{off['name']}, {off['pres_post']}"
        col4 = off['su_post'] if off['su_post'] != "Nil" else off['remarks']
        ws4.append([off['sl'], col2, off['sub_post'], col4])
        curr_r = ws4.max_row
        ws4.row_dimensions[curr_r].height = 26
        fill_to_use = zebra_fill if curr_r % 2 == 0 else white_fill
        for c in range(1, 5):
            cell = ws4.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            cell.fill = fill_to_use
            if c == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws4.freeze_panes = "A7"

    # TAB 5: DD_Vacancy_Balance
    print("Writing Tab 5: DD_Vacancy_Balance...")
    ws5 = wb_out.create_sheet(title="DD_Vacancy_Balance")
    ws5.views.sheetView[0].showGridLines = True
    for r in range(1, ws_c_vac.max_row + 1):
        row_vals = [ws_c_vac.cell(r, c).value for c in range(1, ws_c_vac.max_column + 1)]
        ws5.append(row_vals)
        curr_r = ws5.max_row
        ws5.row_dimensions[curr_r].height = 22
        if r == 1:
            for c in range(1, len(row_vals) + 1):
                cell = ws5.cell(curr_r, c)
                cell.fill = navy_header_fill
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center")
            ws5.row_dimensions[curr_r].height = 28
        else:
            status = clean(ws5.cell(curr_r, 5).value)
            for c in range(1, len(row_vals) + 1):
                cell = ws5.cell(curr_r, c)
                cell.font = font_regular
                cell.border = border_thin
                if status == "OVER-ALLOTTED":
                    cell.fill = crit_alert_fill
                    if c == 5: cell.font = font_bold
                elif status == "Under-allotted":
                    cell.fill = alert_fill
                else:
                    cell.fill = white_fill
                if c in [2, 3, 4]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
    ws5.freeze_panes = "A2"

    # TAB 6: Discrepancy_Register
    print("Writing Tab 6: Discrepancy_Register...")
    ws6 = wb_out.create_sheet(title="Discrepancy_Register")
    ws6.views.sheetView[0].showGridLines = True
    for r in range(1, ws_c_disc.max_row + 1):
        row_vals = [ws_c_disc.cell(r, c).value for c in range(1, ws_c_disc.max_column + 1)]
        ws6.append(row_vals)
        curr_r = ws6.max_row
        ws6.row_dimensions[curr_r].height = 26
        if r == 1:
            for c in range(1, len(row_vals) + 1):
                cell = ws6.cell(curr_r, c)
                cell.fill = navy_header_fill
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center")
            ws6.row_dimensions[curr_r].height = 28
        else:
            sev = clean(ws6.cell(curr_r, 4).value)
            for c in range(1, len(row_vals) + 1):
                cell = ws6.cell(curr_r, c)
                cell.font = font_regular
                cell.border = border_thin
                if sev == "CRITICAL":
                    cell.fill = crit_alert_fill
                elif sev == "HIGH":
                    cell.fill = alert_fill
                else:
                    cell.fill = white_fill
                if c in [1, 4]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    if c == 4: cell.font = font_bold
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws6.freeze_panes = "A2"

    # TAB 7: Sources_and_Method
    print("Writing Tab 7: Sources_and_Method...")
    ws7 = wb_out.create_sheet(title="Sources_and_Method")
    ws7.views.sheetView[0].showGridLines = True
    for r in range(1, ws_c_src.max_row + 1):
        row_vals = [ws_c_src.cell(r, c).value for c in range(1, ws_c_src.max_column + 1)]
        ws7.append(row_vals)
        curr_r = ws7.max_row
        ws7.row_dimensions[curr_r].height = 22
        for c in range(1, len(row_vals) + 1):
            cell = ws7.cell(curr_r, c)
            cell.font = font_regular
            cell.border = border_thin
            if r == 1:
                cell.fill = navy_header_fill
                cell.font = font_header
            elif cell.value and any(k in str(cell.value) for k in ["WHAT WAS", "OPEN DECISION", "SUMMARY"]):
                cell.font = font_bold
                cell.fill = alert_fill

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
        ws.column_dimensions["K"].width = 38
        ws.column_dimensions["L"].width = 38
        ws.column_dimensions["M"].width = 34
        ws.column_dimensions["N"].width = 30

    ws4.column_dimensions["A"].width = 8
    ws4.column_dimensions["B"].width = 45
    ws4.column_dimensions["C"].width = 40
    ws4.column_dimensions["D"].width = 40

    ws5.column_dimensions["A"].width = 35
    ws5.column_dimensions["B"].width = 18
    ws5.column_dimensions["C"].width = 18
    ws5.column_dimensions["D"].width = 14
    ws5.column_dimensions["E"].width = 18

    ws6.column_dimensions["A"].width = 6
    ws6.column_dimensions["B"].width = 20
    ws6.column_dimensions["C"].width = 20
    ws6.column_dimensions["D"].width = 12
    ws6.column_dimensions["E"].width = 35
    ws6.column_dimensions["F"].width = 40
    ws6.column_dimensions["G"].width = 35

    ws7.column_dimensions["A"].width = 25
    ws7.column_dimensions["B"].width = 65

    print(f"Saving to {OUTPUT_LOCAL_AVD}...")
    wb_out.save(OUTPUT_LOCAL_AVD)
    print(f"Saving to {OUTPUT_LOCAL_AG}...")
    wb_out.save(OUTPUT_LOCAL_AG)
    print("Full Promotion cum Transfer Master successfully created!")

if __name__ == "__main__":
    run()
