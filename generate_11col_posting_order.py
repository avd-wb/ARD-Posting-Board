#!/usr/bin/env python3
"""
generate_11col_posting_order.py
Converts the full WB ARD Promotion, Post Abolition Rehabilitation, and Consequential Transfer list
into an authentic Government Excel workbook with the exact 11 requested columns:
1. sl no.
2. sl. no. (of 242 promotees)
3. name
4. present designation
5. Present establishment
6. Present block name (only in case of ABAHC, BAHC, BLDO)
7. Present district
8. Present SU (if any) (format - <Desination>, <establishment>, <district>.
9. Transfer basis : Promotion / Displacement due to postt abolision / displacement due to promotee accomodation.
10. Transferred to Substantive post ( <designation>, <establishment>, <block only for BLDO, ABAHC, BAHC>, <District>)
11. Service utilized at ( <designation>, <establishment>, <block only for BLDO, ABAHC, BAHC>, <District>)

Visual Shading Rule:
- White background (#FFFFFF) for manually confirmed / executive directed postings.
- Very light grey background (#F1F5F9) for algorithmic / system recommended postings.
"""

import sqlite3
import re
import os
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

DB_PATH = "ard_master_truth.db"
MASTER_WORKBOOK = "WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx"

def is_block_post(desig, estab=""):
    txt = f"{desig or ''} {estab or ''}".upper()
    return any(k in txt for k in ["BLDO", "BLOCK LIVESTOCK", "BLOCK LIVE STOCK", "ABAHC", "BAHC"])

def clean_block_name(b, dist=""):
    if not b: return ""
    b_clean = re.sub(r'(?i)\bblock\b', '', str(b)).strip()
    b_clean = re.sub(r'(?i)\bddard&po\b', '', b_clean).strip()
    b_clean = re.sub(r'(?i)\bdistrict hq\b', '', b_clean).strip()
    if dist and b_clean.lower() == dist.lower():
        return ""
    if b_clean.lower() in ["none", "null", "nil", "-", "", "livestock", "west bengal"]:
        return ""
    return b_clean

def format_post_fields(desig, estab, block, district):
    desig = re.sub(r'\s+', ' ', desig or '').strip(" ,-")
    estab = re.sub(r'\s+', ' ', estab or '').strip(" ,-")
    block = clean_block_name(block, district)
    district = re.sub(r'\s+', ' ', district or '').strip(" ,-")

    # Clean up standard abbreviations in estab
    estab = re.sub(r'(?i)DEPUTY DIRECTOR,?\s*ARD\s*&\s*PARISHAD OFFICER,?\s*', 'Office of the Deputy Director, ARD, ', estab)
    estab = re.sub(r'(?i)JOINT DIRECTOR,?\s*ARD,?\s*', 'Office of the Joint Director, ARD, ', estab)
    estab = re.sub(r'(?i)DIRECTORATE OF AR&AH', 'Directorate Headquarter, Kolkata', estab)
    estab = re.sub(r'(?i)INSTITUTE OF ANIMAL HEALTH & VETERINARY BIOLOGICALS & REGIONAL DISEASE DIAGNOSTIC LABORATORY', 'IAH&VB, Belgachia, Kolkata', estab)
    estab = re.sub(r'\s+', ' ', estab).strip(" ,-")

    if is_block_post(desig, estab):
        parts = [desig, estab]
        if block:
            parts.append(block)
        parts.append(district)
    else:
        parts = [desig, estab, district]

    res = []
    for p in parts:
        p_clean = p.strip(" ,.-")
        if p_clean and (not res or p_clean.lower() != res[-1].lower()):
            res.append(p_clean)
    return ', '.join(res)

def format_present_su(hrms, desig, estab, dist, raw_txt=""):
    known_su = {
        "2005002146": "Managing Director, Ichamati Milk Union, North 24 Parganas",
        "1995003790": "Assistant Director, ARD (VR&I), State Poultry Farm Gobardanga, North 24 Parganas",
        "2001000187": "Station Director-1, Central Semen Bank PBGSBS, Belgachia, Kolkata",
        "1997000854": "Block Livestock Development Officer, Block Livestock Development Office Bangaon, North 24 Parganas",
        "1995000449": "Station Director-II, PBGSBS HQ, Salt Lake, Kolkata",
        "1998001949": "Assistant Director, ARD (DEO), Office of the Deputy Director, ARD, Paschim Bardhaman",
        "2000007392": "Veterinary Officer, Animal Science Laboratory, Directorate HQ, Kolkata",
        "2001000684": "Veterinary Officer, MDVH Katwa, Purba Bardhaman",
        "1995001801": "Veterinary Officer, Bull Mother Farm, Haringhata, Nadia",
    }
    if hrms in known_su:
        return known_su[hrms]

    if not raw_txt:
        return "Nil"

    m = re.search(r'(?:(?:\bSU\b|S/U)\s*(?:at|as|:)?\s*([^,\n;\)]+)|service\s+utilized\s+(?:at|as)?\s*([^,\n;\)]+))', raw_txt, re.I)
    if m:
        val = (m.group(1) or m.group(2) or "").strip()
        if val and not any(w in val.lower() for w in ['suri', 'suti', 'pursurah', 'surgeon', 'sujapur', 'sub', 'such']):
            return f"{val}, {estab}, {dist}".strip(" ,")
    return "Nil"

def parse_target_post_string(raw_txt, cadre_by_post_sl, dist_fallback=""):
    if not raw_txt or raw_txt.strip().lower() in ["nil", "none", "null", ""]:
        return "Nil"

    raw_sub = raw_txt.split("[SU")[0].strip()
    raw_sub = raw_sub.split("[Additional Charge")[0].strip()

    m_post = re.search(r'Post\s*(\d+)', raw_sub)
    if m_post:
        p_num = int(m_post.group(1))
        p_info = cadre_by_post_sl.get(p_num)
        if p_info:
            raw_upper = raw_sub.upper()
            cadre_upper = p_info["designation"].upper()
            if ("ASSISTANT DIRECTOR" in raw_upper and "ASSISTANT DIRECTOR" in cadre_upper) or \
               ("BLOCK" in raw_upper and "BLOCK" in cadre_upper) or \
               ("VETERINARY OFFICER" in raw_upper and "VETERINARY OFFICER" in cadre_upper) or \
               ("JOINT DIRECTOR" in raw_upper and "JOINT DIRECTOR" in cadre_upper):
                return format_post_fields(p_info["designation"], p_info["establishment"], p_info["block"], p_info["district"])

    clean_sub = re.sub(r'[\(\[]Post\s*\d+[\)\]]', '', raw_sub).strip()
    clean_sub = re.sub(r'\[DD Post\s*\d+\]', '', clean_sub).strip()
    clean_sub = re.sub(r'\s*\([^)]*\)\s*', ' ', clean_sub).strip()
    clean_sub = re.sub(r'\s+', ' ', clean_sub).strip()

    desig_match = re.match(r'^(Joint Director,?\s*ARD(?:\s*\([^\)]+\))?|Deputy Director,?\s*ARD(?:\s*\([^\)]+\))?|Assistant Director,?\s*ARD(?:\s*\([^\)]+\))?|Assistant Director of Animal Resources Development(?:\s*\([^\)]+\))?|Block Livestock Development Officer|Block Live Stock Development Officer|Veterinary Officer,?\s*(?:ABAHC|BAHC|SAHC)?|Veterinary Officer)', clean_sub, re.I)

    if desig_match:
        desig = desig_match.group(1).strip(" ,-")
        rest = clean_sub[len(desig):].strip(" ,-")
        parts = [p.strip() for p in rest.split(",") if p.strip()]
        if len(parts) >= 2:
            estab = parts[0]
            dist = parts[-1]
            block = parts[1] if len(parts) >= 3 else (parts[0] if is_block_post(desig) else "")
        elif len(parts) == 1:
            dist = parts[0]
            estab = f"District Office, {dist}" if "Director" in desig else f"Office of the {desig}, {dist}"
            block = parts[0] if is_block_post(desig) else ""
        else:
            dist = dist_fallback
            estab = f"District Office, {dist}" if "Director" in desig else f"Office of the {desig}, {dist}"
            block = ""
        return format_post_fields(desig, estab, block, dist)

    return clean_sub

def parse_target_su_string(raw_su, cadre_by_post_sl, dist_fallback=""):
    if not raw_su or raw_su.strip().lower() in ["nil", "none", "null", ""]:
        return "Nil"

    m_post = re.search(r'Post\s*(\d+)', raw_su)
    if m_post:
        p_num = int(m_post.group(1))
        p_info = cadre_by_post_sl.get(p_num)
        if p_info:
            return format_post_fields(p_info["designation"], p_info["establishment"], p_info["block"], p_info["district"])

    clean_su = re.sub(r'^\[SU\]\s*', '', raw_su).strip()
    clean_su = re.sub(r'^\[Additional Charge\]\s*', '[Additional Charge] ', clean_su).strip()
    clean_su = re.sub(r'[\(\[]Post\s*\d+[\)\]]', '', clean_su).strip()
    clean_su = re.sub(r'\s+', ' ', clean_su).strip()

    if "WBLDCL" in clean_su:
        if "HR" in clean_su or "Manager" in clean_su:
            return "Manager (HR), West Bengal Livestock Development Corporation Ltd. HQ, Salt Lake, Kolkata"
        elif "Marketing" in clean_su:
            return "Marketing In-Charge, West Bengal Livestock Development Corporation Ltd. HQ, Salt Lake, Kolkata"

    return clean_su if clean_su else "Nil"

def populate_11_col_sheet(ws, roster_rows, oblit_rows, lateral_rows, cadre_by_hrms, cadre_by_post_sl, dd_by_sl, master_by_hrms):
    # Header styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Deep Navy
    header_font = Font(name="Calibri", size=10.5, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    data_font_bold = Font(name="Calibri", size=10, bold=True)
    su_font = Font(name="Calibri", size=10, color="047857", bold=True)
    nil_font = Font(name="Calibri", size=10, color="64748B", italic=True)

    thin_border_side = Side(border_style="thin", color="CBD5E1")
    cell_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    manual_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid") # White
    ai_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")     # Very Light Grey

    # Load baseline remarks if available
    baseline = {}
    if os.path.exists('remarks_baseline.json'):
        try:
            with open('remarks_baseline.json') as bf:
                baseline = json.load(bf)
        except Exception:
            baseline = {}

    headers = [
        "sl no.",
        "sl. no. (of 242 promotees)",
        "name",
        "present designation",
        "Present establishment",
        "Present block name (only in case of ABAHC, BAHC, BLDO)",
        "Present district",
        "Present Post",
        "Present SU (if any) (format - <Desination>, <establishment>, <district>)",
        "Transfer basis : Promotion / Displacement due to postt abolision / displacement due to promotee accomodation.",
        "Transferred to Substantive post ( <designation>, <establishment>, <block only for BLDO, ABAHC, BAHC>, <District>)",
        "Service utilized at ( <designation>, <establishment>, <block only for BLDO, ABAHC, BAHC>, <District>)",
        "remarks"
    ]

    ws.row_dimensions[1].height = 45
    for col_idx, h_text in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h_text)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = cell_border

    current_row = 2
    global_sl = 1
    seen_hrms = set()

    # -------------------------------------------------------------
    # PART 1: 242 PROMOTEES
    # -------------------------------------------------------------
    for r in roster_rows:
        hrms = str(r["hrms_id"]).strip()
        seen_hrms.add(hrms)
        is_manual = bool(r["is_manual_recommendation"])
        row_fill = manual_fill if is_manual else ai_fill

        name = r["officer_name"].strip()

        # Present Designation, Establishment, Block, District
        c_info = cadre_by_hrms.get(hrms, {})
        m_info = master_by_hrms.get(hrms, {})

        pres_desig = c_info.get("designation") or m_info.get("designation")
        if not pres_desig:
            pp = r["present_posting"] or ""
            parts = [p.strip() for p in pp.split(",")]
            pres_desig = parts[0] if parts else "Veterinary Officer"

        if "BLDO" in pres_desig.upper() or "BLOCK LIVE" in pres_desig.upper():
            pres_desig = "Block Livestock Development Officer"
        elif "ABAHC" in pres_desig.upper():
            pres_desig = "Veterinary Officer, ABAHC"
        elif "BAHC" in pres_desig.upper():
            pres_desig = "Veterinary Officer, BAHC"
        elif "SAHC" in pres_desig.upper():
            pres_desig = "Veterinary Officer, SAHC"

        pres_estab = c_info.get("establishment") or m_info.get("establishment") or r["present_posting"]
        pres_estab = re.sub(r'(?i)DEPUTY DIRECTOR,?\s*ARD\s*&\s*PARISHAD OFFICER,?\s*', 'Office of the Deputy Director, ARD, ', pres_estab)
        pres_estab = re.sub(r'(?i)JOINT DIRECTOR,?\s*ARD,?\s*', 'Office of the Joint Director, ARD, ', pres_estab)
        pres_estab = re.sub(r'(?i)Block Live\s*Stock Development Officer,?\s*', 'Office of the BLDO, ', pres_estab)
        pres_estab = re.sub(r'(?i)Veterinary Officer,?\s*', 'Office of the VO, ', pres_estab)
        pres_estab = re.sub(r'\s+', ' ', pres_estab).strip()

        pres_dist = c_info.get("district") or r["present_district"] or m_info.get("district") or ""

        # Block only in case of ABAHC, BAHC, BLDO
        pres_block = ""
        if is_block_post(pres_desig, pres_estab):
            raw_b = c_info.get("block") or r["present_block"] or ""
            pres_block = clean_block_name(raw_b, pres_dist)

        # Present SU
        raw_pres = f"{r.get('present_posting', '')} {r.get('detailed_presentation', '')} {m_info.get('source_notes', '')}"
        pres_su = format_present_su(hrms, pres_desig, pres_estab, pres_dist, raw_pres)

        # Transfer Basis
        transfer_basis = "Promotion"

        # Target Substantive Post
        sub_raw = r["substantive_post_name"] or ""
        m_dd = re.search(r'DD Sl (\d+)', sub_raw)
        if m_dd:
            dd_info = dd_by_sl.get(int(m_dd.group(1)), {})
            dd_office = dd_info.get("office") or f"District Office, {dd_info.get('district', '')}"
            dd_dist = dd_info.get("district", "")
            target_sub = format_post_fields("Deputy Director, ARD", dd_office, "", dd_dist)
        else:
            target_sub = parse_target_post_string(sub_raw, cadre_by_post_sl, pres_dist)

        # Target SU Post
        su_raw = r["su_post_name"] or ""
        target_su = parse_target_su_string(su_raw, cadre_by_post_sl, pres_dist)

        pres_post = format_post_fields(pres_desig, pres_estab, pres_block, pres_dist)
        baseline_rem = baseline.get(str(global_sl), {}).get("remark", "").strip()
        if "Basudev Sil" in name:
            target_sub = "Deputy Director, ARD, O/O the JD ARD, North 24 Parganas"
            target_su = "Nil"
            remark = "Promoted to Deputy Director, ARD, North 24 Parganas"
            row_fill = manual_fill
        elif "Bhaskar Prasad Maji" in name:
            target_sub = "Deputy Director, ARD, O/O the Additional Director, ARD, I.A.H. & V.B., (R. & T.)"
            target_su = "Nil"
            remark = "Promoted to Deputy Director, ARD, IAH&VB, Kolkata"
            row_fill = manual_fill
        elif baseline_rem:
            remark = baseline_rem
        elif target_su != "Nil":
            remark = "Stay at present station on SU (Pay Level 19 at District HQ)"
        else:
            remark = f"Promoted to Deputy Director, ARD, {pres_dist}"

        row_values = [
            global_sl,
            r["sl_no"],
            name,
            pres_desig,
            pres_estab,
            pres_block,
            pres_dist,
            pres_post,
            pres_su,
            transfer_basis,
            target_sub,
            target_su,
            remark
        ]

        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.fill = row_fill
            cell.border = cell_border
            if col_idx in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = data_font_bold
            elif col_idx in [3, 10]:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font_bold
            elif col_idx in [6, 7]:
                cell.alignment = Alignment(horizontal="center" if col_idx == 6 else "left", vertical="center")
                cell.font = data_font
            elif col_idx in [9, 12]:
                cell.alignment = Alignment(horizontal="center" if val == "Nil" else "left", vertical="center")
                cell.font = nil_font if val == "Nil" else su_font
            elif col_idx == 11:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font_bold
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font

        current_row += 1
        global_sl += 1

    # -------------------------------------------------------------
    # PART 2: OBLITERATED POST REHABILITATIONS (61 NON-ROSTER)
    # -------------------------------------------------------------
    for o in oblit_rows:
        hrms = str(o["hrms_id"]).strip()
        seen_hrms.add(hrms)
        is_manual = bool(o["is_manual_recommendation"])
        row_fill = manual_fill if is_manual else ai_fill

        name = o["officer_name"].strip()
        name = re.sub(r'\[S/U:.*?\]', '', name).strip()
        name = name.rstrip('*').strip()

        pres_desig = o["post_name"].strip()
        pres_estab = o["establishment"] or f"District Office, {o['district']}"
        pres_estab = re.sub(r'(?i)DD ARD & PO\s*', 'Office of the Deputy Director, ARD, ', pres_estab).strip()
        pres_dist = o["district"] or ""

        # Block only in case of ABAHC, BAHC, BLDO
        pres_block = ""
        if is_block_post(pres_desig, pres_estab):
            pres_block = clean_block_name(o.get("block", ""), pres_dist)

        # Present SU
        raw_pres = f"{o.get('officer_name', '')} {o.get('detailed_presentation', '')}"
        pres_su = format_present_su(hrms, pres_desig, pres_estab, pres_dist, raw_pres)

        # Transfer Basis
        transfer_basis = "Displacement due to post abolision"

        # Target Substantive Post
        sub_raw = o["substantive_post_name"] or ""
        m_post = re.search(r'Post\s*(\d+)', sub_raw)
        if m_post:
            p_info = cadre_by_post_sl.get(int(m_post.group(1)), {})
            target_sub = format_post_fields(p_info.get("designation", ""), p_info.get("establishment", ""), p_info.get("block", ""), p_info.get("district", ""))
        elif "Active Cadre" in sub_raw or "Rehabilitated to" in sub_raw:
            target_sub = format_post_fields("Assistant Director, ARD", f"District Office, {pres_dist}", "", pres_dist)
        else:
            target_sub = format_post_fields("Assistant Director, ARD", sub_raw, "", pres_dist)

        # Target SU Post
        su_raw = o["su_post_name"] or ""
        target_su = parse_target_su_string(su_raw, cadre_by_post_sl, pres_dist)

        pres_post = format_post_fields(pres_desig, pres_estab, pres_block, pres_dist)
        baseline_rem = baseline.get(str(global_sl), {}).get("remark", "").strip()
        remark = baseline_rem if baseline_rem else "Rehabilitated to active cadre"

        row_values = [
            global_sl,
            "-",
            name,
            pres_desig,
            pres_estab,
            pres_block,
            pres_dist,
            pres_post,
            pres_su,
            transfer_basis,
            target_sub,
            target_su,
            remark
        ]

        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.fill = row_fill
            cell.border = cell_border
            if col_idx in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = data_font_bold
            elif col_idx in [3, 10]:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font_bold
            elif col_idx in [6, 7]:
                cell.alignment = Alignment(horizontal="center" if col_idx == 6 else "left", vertical="center")
                cell.font = data_font
            elif col_idx in [9, 12]:
                cell.alignment = Alignment(horizontal="center" if val == "Nil" else "left", vertical="center")
                cell.font = nil_font if val == "Nil" else su_font
            elif col_idx == 11:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font_bold
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font

        current_row += 1
        global_sl += 1

    # -------------------------------------------------------------
    # PART 3: CONSEQUENTIAL LATERAL & FIELD TRANSFERS (23 UNIQUE)
    # -------------------------------------------------------------
    # Explicit mapping for lateral personnel
    lateral_custom_info = {
        "1993000628": {
            "desig": "Veterinary Officer",
            "estab": "Sub-Divisional and Block Level Set up of Purba Bardhaman",
            "block": "Kalna-II",
            "dist": "Purba Bardhaman"
        },
        "1994000305": {
            "desig": "Assistant Director, ARD (Veterinary)",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "1995000574": {
            "desig": "Block Livestock Development Officer",
            "estab": "Sub-Divisional and Block Level Set up of Malda District",
            "block": "Ratua-I",
            "dist": "Malda"
        },
        "2000000780": {
            "desig": "Assistant Director, ARD (Veterinary)",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "1997000854": {
            "desig": "Assistant Director, ARD (Veterinary)",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "1996000007": {
            "desig": "Assistant Director, ARD (Veterinary)",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "2008000492": {
            "desig": "Assistant Director, ARD (Veterinary)",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "2009000185": {
            "desig": "Assistant Director, ARD (Management)",
            "estab": "Haringhata Farm",
            "block": "",
            "dist": "Nadia"
        },
        "2000000371": {
            "desig": "Assistant Director, ARD (Admin)",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "1996000030": {
            "desig": "Deputy Director, ARD",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "1996000388": {
            "desig": "Deputy Director, ARD",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "1995000685": {
            "desig": "Deputy Director, ARD",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "2005000244": {
            "desig": "Assistant Director, ARD (Veterinary)",
            "estab": "Directorate Headquarter, Kolkata",
            "block": "",
            "dist": "Kolkata"
        },
        "2001000032": {
            "desig": "Block Livestock Development Officer",
            "estab": "Sub-Divisional and Block Level Set up of Bankura",
            "block": "Hirbandh",
            "dist": "Bankura"
        },
        "2000003056": {
            "desig": "Block Livestock Development Officer",
            "estab": "Sub-Divisional and Block Level Set up of Howrah",
            "block": "Uluberia-II",
            "dist": "Howrah"
        },
        "2001001503": {
            "desig": "Block Livestock Development Officer",
            "estab": "Sub-Divisional and Block Level Set up of Murshidabad",
            "block": "Beldanga-II",
            "dist": "Murshidabad"
        },
        "2005000472": {
            "desig": "Block Livestock Development Officer",
            "estab": "Sub-Divisional and Block Level Set up of North 24 Parganas District",
            "block": "Rajarhat",
            "dist": "North 24 Parganas"
        },
        "2010001372": {
            "desig": "Veterinary Officer, BAHC",
            "estab": "Sub-Divisional and Block Level Set up of Howrah",
            "block": "Udaynarayanpur",
            "dist": "Howrah"
        },
        "2015008435": {
            "desig": "Veterinary Officer, SAHC",
            "estab": "Block Level Set up of Alipurduar District",
            "block": "",
            "dist": "Alipurduar"
        }
    }

    for l in lateral_rows:
        hrms = str(l["hrms_id"]).strip()
        if hrms in seen_hrms:
            continue
        seen_hrms.add(hrms)

        is_manual = bool(l["is_manual_recommendation"])
        row_fill = manual_fill if is_manual else ai_fill

        name = l["officer_name"].strip()

        # Present Designation, Estab, Block, District
        custom = lateral_custom_info.get(hrms)
        if custom:
            pres_desig = custom["desig"]
            pres_estab = custom["estab"]
            pres_block = custom["block"]
            pres_dist = custom["dist"]
        else:
            c_info = cadre_by_hrms.get(hrms, {})
            m_info = master_by_hrms.get(hrms, {})
            pres_desig = c_info.get("designation") or m_info.get("designation") or "Veterinary Officer"
            pres_estab = c_info.get("establishment") or m_info.get("establishment") or l["present_posting"]
            pres_dist = c_info.get("district") or l["district_from"] or m_info.get("district") or ""
            pres_block = clean_block_name(c_info.get("block") or m_info.get("block") or "", pres_dist) if is_block_post(pres_desig, pres_estab) else ""

        pres_su = format_present_su(hrms, pres_desig, pres_estab, pres_dist, l["present_posting"])
        transfer_basis = "Displacement due to promotee accomodation"

        # Target Substantive Post
        trans_raw = l["transferred_post_name"] or ""
        if hrms in ["1996000030", "1996000388", "1995000685"]:
            target_sub = "Deputy Director, ARD, Directorate Headquarter, Kolkata, Kolkata"
        elif hrms in ["1996000007", "2008000492", "2009000185", "1993000628", "1995000574"]:
            target_sub = "Assistant Director, ARD (Veterinary), Directorate Headquarter, Kolkata, Kolkata"
        elif hrms == "2000000371":
            target_sub = "Assistant Director, ARD (Admin), Directorate Headquarter, Kolkata, Kolkata"
        elif hrms == "2005000244":
            target_sub = "Assistant Director, ARD (VR&I), IAH&VB, Belgachia, Kolkata"
        elif hrms == "2011000454":
            target_sub = "Assistant Director, ARD, District Office, Howrah, Howrah"
        elif hrms == "1998005468":
            target_sub = "Assistant Director, ARD (DEO), District Office, Howrah, Howrah"
        elif hrms == "1997000142":
            target_sub = "Assistant Director, ARD (Veterinary), District Office, North 24 Parganas, North 24 Parganas"
        elif hrms == "2000000780":
            target_sub = "Veterinary Officer, Sub-Divisional and Block Level Set up of Purba Bardhaman, Kalna-II, Purba Bardhaman"
        elif hrms == "1994000305":
            target_sub = "Block Livestock Development Officer, Sub-Divisional and Block Level Set up of Malda District, Ratua-I, Malda"
        elif hrms == "1997000854":
            target_sub = "Block Livestock Development Officer, Sub-Divisional and Block Level Set up of North 24 Parganas District, Bangaon, North 24 Parganas"
        elif hrms == "2001000032":
            target_sub = "Veterinary Officer, SAHC, Sub-Divisional and Block Level Set up of Hooghly, Arambagh, Hooghly"
        elif hrms == "2000003056":
            target_sub = "Assistant Director, ARD (Veterinary), Training Institute, Medinipur, Paschim Medinipur"
        elif hrms == "2010001372":
            target_sub = "Block Livestock Development Officer, Sub-Divisional and Block Level Set up of Howrah, Uluberia-II, Howrah"
        elif hrms == "2015008435":
            target_sub = "Block Livestock Development Officer, Sub-Divisional and Block Level Set up of North 24 Parganas District, Basirhat-I, North 24 Parganas"
        elif hrms == "2001001503":
            target_sub = "Block Livestock Development Officer, Sub-Divisional and Block Level Set up of Purba Medinipur, Panskura-I, Purba Medinipur"
        elif hrms == "2005000472":
            target_sub = "Block Livestock Development Officer, Sub-Divisional and Block Level Set up of Hooghly, Tarakeswar, Hooghly"
        else:
            target_sub = parse_target_post_string(trans_raw, cadre_by_post_sl, pres_dist)

        # Target SU Post
        if "[SU" in trans_raw:
            m_su = re.search(r'\[SU\s*([^\]]+)\]', trans_raw)
            if m_su:
                target_su = parse_target_su_string(m_su.group(1).strip(), cadre_by_post_sl, pres_dist)
            else:
                target_su = "Nil"
        else:
            target_su = "Nil"

        pres_post = format_post_fields(pres_desig, pres_estab, pres_block, pres_dist)
        baseline_rem = baseline.get(str(global_sl), {}).get("remark", "").strip()
        remark = baseline_rem if baseline_rem else "Consequential transfer"

        row_values = [
            global_sl,
            "-",
            name,
            pres_desig,
            pres_estab,
            pres_block,
            pres_dist,
            pres_post,
            pres_su,
            transfer_basis,
            target_sub,
            target_su,
            remark
        ]

        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.fill = row_fill
            cell.border = cell_border
            if col_idx in [1, 2]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font = data_font_bold
            elif col_idx in [3, 10]:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font_bold
            elif col_idx in [6, 7]:
                cell.alignment = Alignment(horizontal="center" if col_idx == 6 else "left", vertical="center")
                cell.font = data_font
            elif col_idx in [9, 12]:
                cell.alignment = Alignment(horizontal="center" if val == "Nil" else "left", vertical="center")
                cell.font = nil_font if val == "Nil" else su_font
            elif col_idx == 11:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font_bold
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = data_font

        current_row += 1
        global_sl += 1

    # Freeze header row
    ws.freeze_panes = "A2"

    # Set calculated column widths
    col_widths = {
        "A": 8,   # sl no.
        "B": 14,  # sl. no. (of 242 promotees)
        "C": 28,  # name
        "D": 32,  # present designation
        "E": 36,  # Present establishment
        "F": 22,  # Present block name
        "G": 20,  # Present district
        "H": 42,  # Present Post
        "I": 32,  # Present SU
        "J": 38,  # Transfer basis
        "K": 52,  # Transferred to Substantive post
        "L": 48,  # Service utilized at
        "M": 45   # remarks
    }
    for col_letter, width in col_widths.items():
        ws.column_dimensions[col_letter].width = width

    return current_row - 2

def build_standalone_and_inject_master():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('SELECT incumbent_hrms, designation, establishment, block, district, service_utilized_flag FROM cadre_1794_posts WHERE incumbent_hrms IS NOT NULL AND incumbent_hrms != ""')
    cadre_by_hrms = {r['incumbent_hrms']: {'designation': r['designation'], 'establishment': r['establishment'], 'block': r['block'], 'district': r['district'], 'service_utilized_flag': r['service_utilized_flag']} for r in c.fetchall()}

    c.execute('SELECT post_sl, designation, establishment, block, district FROM cadre_1794_posts')
    cadre_by_post_sl = {r['post_sl']: {'designation': r['designation'], 'establishment': r['establishment'], 'block': r['block'], 'district': r['district']} for r in c.fetchall()}

    c.execute('SELECT dd_sl, district, establishment, office, post_name FROM available_dd_posts')
    dd_by_sl = {r['dd_sl']: {'district': r['district'], 'establishment': r['establishment'], 'office': r['office'], 'post_name': r['post_name']} for r in c.fetchall()}

    c.execute('SELECT hrms_id, officer_name, designation, present_posting, establishment, district, source_notes, hq_posting_history FROM master_all_cadre_employees')
    master_by_hrms = {r['hrms_id']: {'name': r['officer_name'], 'designation': r['designation'], 'present_posting': r['present_posting'], 'establishment': r['establishment'], 'district': r['district'], 'source_notes': r['source_notes'], 'hq_posting_history': r['hq_posting_history']} for r in c.fetchall()}

    c.execute('SELECT sl_no, roster_point, point_reserved_for, officer_name, hrms_id, present_posting, present_block, present_district, detailed_presentation, substantive_post_name, su_post_name, is_manual_recommendation FROM roster_50_point_candidates ORDER BY sl_no ASC')
    roster_rows = [dict(r) for r in c.fetchall()]

    c.execute('SELECT oblit_sl, officer_name, hrms_id, post_name, establishment, block, district, detailed_presentation, substantive_post_name, su_post_name, is_manual_recommendation FROM obliterated_posts_1808 WHERE is_vacant = "No" AND (is_on_roster = 0 OR is_on_roster IS NULL) ORDER BY oblit_sl ASC')
    oblit_rows = [dict(r) for r in c.fetchall()]

    c.execute('SELECT sl_no, hrms_id, officer_name, present_posting, transferred_post_name, district_from, district_to, transfer_type, reason_notes, is_manual_recommendation FROM executive_lateral_transfers ORDER BY sl_no ASC')
    lateral_rows = [dict(r) for r in c.fetchall()]
    conn.close()

    # 1. Build Standalone Workbook
    wb_standalone = openpyxl.Workbook()
    ws_standalone = wb_standalone.active
    ws_standalone.title = "11_Column_Master_Posting_Order"
    total_officers = populate_11_col_sheet(ws_standalone, roster_rows, oblit_rows, lateral_rows, cadre_by_hrms, cadre_by_post_sl, dd_by_sl, master_by_hrms)

    # Inject District HQ Cadre Summary and Officer Roster tabs
    try:
        from generate_district_hq_tabs import build_district_hq_data, add_summary_tab, add_roster_tab
        summary_rows, detailed_roster_rows = build_district_hq_data()
        add_summary_tab(wb_standalone, summary_rows)
        add_roster_tab(wb_standalone, detailed_roster_rows)
    except Exception as e:
        print(f"Warning: Could not inject District HQ tabs into standalone: {e}")

    now = datetime.datetime.now()
    ts_date = now.strftime('%Y%m%d')
    ts_time = now.strftime('%H%M')

    temp_standalone = f"{ts_date}_{ts_time}_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_temp.xlsx"
    wb_standalone.save(temp_standalone)
    sz_mb = os.path.getsize(temp_standalone) / (1024 * 1024)
    final_standalone = f"{ts_date}_{ts_time}_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_{sz_mb:.2f}MB_mb.xlsx"
    os.rename(temp_standalone, final_standalone)
    print(f"Generated standalone 11-column file: {final_standalone} ({os.path.getsize(final_standalone)} bytes, {sz_mb:.2f}MB)")

    # 2. Inject into Master Interactive Workbook (WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx)
    if os.path.exists(MASTER_WORKBOOK):
        wb_master = openpyxl.load_workbook(MASTER_WORKBOOK)
        sheet_name = "11_Column_Master_Posting_Order"
        if sheet_name in wb_master.sheetnames:
            del wb_master[sheet_name]

        # Insert at index 1 (right after Instructions)
        ws_master = wb_master.create_sheet(title=sheet_name, index=1)
        populate_11_col_sheet(ws_master, roster_rows, oblit_rows, lateral_rows, cadre_by_hrms, cadre_by_post_sl, dd_by_sl, master_by_hrms)
        
        try:
            add_summary_tab(wb_master, summary_rows)
            add_roster_tab(wb_master, detailed_roster_rows)
        except Exception as e:
            print(f"Warning: Could not inject District HQ tabs into master: {e}")

        wb_master.save(MASTER_WORKBOOK)
        print(f"Injected '{sheet_name}' and District HQ tabs into {MASTER_WORKBOOK}")

    return final_standalone

if __name__ == "__main__":
    build_standalone_and_inject_master()
