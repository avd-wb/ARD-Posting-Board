#!/usr/bin/env python3
"""
generate_district_hq_tabs.py
Compiles the District HQ Cadre Summary and Officer Roster tabs according to:
- Notification No. 1809-AR&AH dt. 18.06.2025 (Sanctioned Strength)
- Vacancy of DD.xlsx (244 Substantive Vacancies)
- Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx (Official Promotee Names)
- In-Charge Joint Director assignment by senior-most DDARD at each District HQ
- Inviolable manual posting corrections (e.g. Dr. Basudev Sil SU = Nil)
"""

import os
import sys
import sqlite3
import re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

WORKSPACE = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DB_PATH = os.path.join(WORKSPACE, "ard_master_truth.db")

# District HQ ordering as per official administrative grouping
DISTRICT_HQ_CONFIG = [
    {"name": "Alipurduar", "estab": "District Office, Alipurduar", "dd_office": "Alipurduar"},
    {"name": "Bankura", "estab": "District Office, Bankura", "dd_office": "Bankura"},
    {"name": "Birbhum", "estab": "District Office, Birbhum", "dd_office": "Birbhum"},
    {"name": "Coochbehar", "alias": "Cooch Behar", "estab": "District Office, Coochbehar", "dd_office": "Cooch Behar"},
    {"name": "Dakshin Dinajpur", "estab": "District Office, Dakshin Dinajpur", "dd_office": "Dakshin Dinajpur"},
    {"name": "Darjeeling", "estab": "District Office, Darjeeling", "dd_office": "Darjeeling"},
    {"name": "Hooghly", "estab": "District Office, Hooghly", "dd_office": "Hooghly"},
    {"name": "Howrah", "estab": "District Office, Howrah", "dd_office": "Howrah"},
    {"name": "Jalpaiguri", "estab": "District Office, Jalpaiguri", "dd_office": "Jalpaiguri"},
    {"name": "Jhargram", "estab": "District Office, Jhargram", "dd_office": "Jhargram"},
    {"name": "Kalimpong", "estab": "District Office, Kalimpong", "dd_office": "Kalimpong"},
    {"name": "Malda", "estab": "District Office, Malda", "dd_office": "Malda"},
    {"name": "Murshidabad", "estab": "District Office, Murshidabad", "dd_office": "Murshidabad"},
    {"name": "Nadia", "estab": "District Office, Nadia", "dd_office": "Nadia"},
    {"name": "North 24 Parganas", "estab": "District Office, North 24 Parganas", "dd_office": "North 24 Parganas"},
    {"name": "Paschim Bardhaman", "estab": "District Office, Paschim Bardhaman", "dd_office": "Paschim Bardhaman"},
    {"name": "Paschim Medinipur", "estab": "District Office, Paschim Medinipur", "dd_office": "Paschim Medinipur"},
    {"name": "Purba Bardhaman", "estab": "District Office, Purba Bardhaman", "dd_office": "Purba Bardhaman"},
    {"name": "Purba Medinipur", "estab": "District Office, Purba Medinipur", "dd_office": "Purba Medinipur"},
    {"name": "Purulia", "estab": "District Office, Purulia", "dd_office": "Purulia"},
    {"name": "Siliguri", "estab": "Sub-Division Office, Siliguri", "dd_office": "Siliguri"},
    {"name": "South 24 Parganas", "estab": "District Office, South 24 Parganas", "dd_office": "South 24 Parganas"},
    {"name": "Uttar Dinajpur", "estab": "District Office, Uttar Dinajpur", "dd_office": "Uttar Dinajpur"},
    {"name": "Directorate Headquarter, Kolkata", "alias": "Kolkata", "estab": "Directorate Headquarter, Kolkata", "dd_office": "Directorate Headquarters", "is_hq": True}
]

def build_district_hq_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Pre-fetch promoted candidates
    cur.execute("SELECT * FROM roster_50_point_candidates ORDER BY sl_no")
    roster_list = cur.fetchall()
    roster_by_sl = {r["sl_no"]: dict(r) for r in roster_list}
    roster_by_hrms = {str(r["hrms_id"]).strip(): dict(r) for r in roster_list if r["hrms_id"]}

    # Pre-fetch available DD posts
    cur.execute("SELECT * FROM available_dd_posts ORDER BY dd_sl")
    all_dd_posts = cur.fetchall()
    dd_post_by_sl = {d["dd_sl"]: dict(d) for d in all_dd_posts}

    summary_rows = []
    detailed_roster_rows = []

    global_roster_sl = 1

    for dist_cfg in DISTRICT_HQ_CONFIG:
        dist_name = dist_cfg["name"]
        alias = dist_cfg.get("alias", dist_name)
        estab_name = dist_cfg["estab"]
        dd_office_name = dist_cfg["dd_office"]
        is_hq = dist_cfg.get("is_hq", False)

        # 1. Fetch Cadre 1794 posts for this establishment
        cur.execute("""
            SELECT * FROM cadre_1794_posts
            WHERE establishment = ?
            ORDER BY post_sl
        """, (estab_name,))
        estab_cadre = [dict(r) for r in cur.fetchall()]

        # Split into JD, DD, AD
        jd_cadre = [p for p in estab_cadre if "Joint Director" in p["designation"]]
        dd_cadre = [p for p in estab_cadre if "Deputy Director" in p["designation"]]
        ad_cadre = [p for p in estab_cadre if "Assistant Director" in p["designation"]]

        sanctioned_jd_count = len(jd_cadre)
        sanctioned_dd_count = len(dd_cadre)
        sanctioned_ad_count = len(ad_cadre)
        total_sanctioned = sanctioned_jd_count + sanctioned_dd_count + sanctioned_ad_count

        # 2. Substantive JD check
        substantive_jds = []
        for j in jd_cadre:
            inc_name = (j["incumbent_name"] or "").strip()
            inc_hrms = (j["incumbent_hrms"] or "").strip()
            if inc_name and inc_name.lower() not in ["vacant", "none", "null", ""]:
                substantive_jds.append({"post_sl": j["post_sl"], "name": inc_name, "hrms": inc_hrms, "desig": j["designation"]})

        # 3. Fetch allotted DDs from available_dd_posts
        cur.execute("""
            SELECT d.dd_sl, d.office, d.post_name,
                   r.sl_no, r.officer_name, r.hrms_id, r.substantive_post_name, r.su_post_name, r.is_manual_recommendation
            FROM available_dd_posts d
            LEFT JOIN roster_50_point_candidates r ON d.dd_sl = r.substantive_post_id
            WHERE (d.district LIKE ? OR d.district LIKE ? OR d.establishment LIKE ?)
              AND (d.office LIKE '%JD ARD%' OR d.office LIKE '%O/O the JD%' OR d.office LIKE '%Joint Director%' OR d.office LIKE '%DAH & VS%')
            ORDER BY d.dd_sl
        """, (f"%{dist_name}%", f"%{alias}%", f"%{dd_office_name}%"))
        hq_dd_allots = [dict(r) for r in cur.fetchall()]

        # Find senior-most DDARD among valid roster allotted DDs
        valid_roster_dds = [d for d in hq_dd_allots if d["sl_no"] is not None]
        valid_roster_dds_sorted = sorted(valid_roster_dds, key=lambda x: x["sl_no"])
        senior_dd = valid_roster_dds_sorted[0] if valid_roster_dds_sorted else None

        # Determine JD status string
        if substantive_jds:
            jd_status_str = f"Substantive: {substantive_jds[0]['name']}" + (f" ({substantive_jds[0]['hrms']})" if substantive_jds[0]['hrms'] else "")
            if len(substantive_jds) > 1:
                jd_status_str = f"{len(substantive_jds)} Substantive JDs in position"
        elif senior_dd:
            jd_status_str = f"In-Charge (SU): {senior_dd['officer_name']} [Senior-most DD at Dist HQ, Roster Sl {senior_dd['sl_no']}]"
        else:
            jd_status_str = "Vacant"

        # Count of substantive DDs filled
        dd_filled_count = len(valid_roster_dds)
        dd_summary_str = f"{dd_filled_count}/{sanctioned_dd_count} Filled"

        # Check DD physical / SU deployment
        dds_at_hq_names = []
        dds_su_field_names = []
        for d in valid_roster_dds_sorted:
            d_name = d["officer_name"]
            d_sl = d["sl_no"]
            su_txt = d.get("su_post_name") or ""
            # Exception: Dr. Basudev Sil has SU = Nil
            if "Basudev Sil" in d_name:
                dds_at_hq_names.append(f"{d_name} (Sl {d_sl}) [Substantive at HQ, SU: Nil]")
            elif senior_dd and d["sl_no"] == senior_dd["sl_no"] and not substantive_jds:
                dds_at_hq_names.append(f"{d_name} (Sl {d_sl}) [In-Charge Joint Director]")
            elif su_txt and su_txt.strip().lower() not in ["nil", "none", "null", ""]:
                dds_su_field_names.append(f"{d_name} (Sl {d_sl}) [SU: {su_txt}]")
            else:
                dds_at_hq_names.append(f"{d_name} (Sl {d_sl})")

        # AD Status
        ad_filled_count = 0
        ad_summary_list = []
        for a in ad_cadre:
            inc_name = (a["incumbent_name"] or "").strip()
            inc_hrms = (a["incumbent_hrms"] or "").strip()
            if inc_name and inc_name.lower() not in ["vacant", "none", "null", ""]:
                # Check if promoted
                if inc_hrms in roster_by_hrms:
                    prom_info = roster_by_hrms[inc_hrms]
                    ad_summary_list.append(f"{inc_name} (Promoted to DD Sl {prom_info['sl_no']})")
                else:
                    ad_filled_count += 1
                    ad_summary_list.append(f"{inc_name} (Substantive)")
            else:
                ad_summary_list.append("Vacant")

        ad_status_str = f"{ad_filled_count}/{sanctioned_ad_count} Substantive Incumbents in position"

        # Overview remarks
        if is_hq:
            hq_remarks = "Directorate HQ: 3 Substantive JDs in position; 32 DD posts filled substantively; AD wing functional."
        else:
            if substantive_jds:
                hq_remarks = f"Substantive Joint Director in position ({substantive_jds[0]['name']}); all {sanctioned_dd_count} DD posts substantively filled."
            elif senior_dd:
                hq_remarks = f"In-Charge JD designated by senior-most DDARD ({senior_dd['officer_name']}, Sl {senior_dd['sl_no']}); all {sanctioned_dd_count} DD posts substantively filled."
            else:
                hq_remarks = "Cadre operational."

        summary_rows.append({
            "dist_name": dist_name,
            "sanctioned_jd": sanctioned_jd_count,
            "sanctioned_dd": sanctioned_dd_count,
            "sanctioned_ad": sanctioned_ad_count,
            "total_sanctioned": total_sanctioned,
            "jd_status": jd_status_str,
            "dd_status": dd_summary_str + ": " + ", ".join(dds_at_hq_names[:3]) + (f" + {len(dds_at_hq_names)-3} more" if len(dds_at_hq_names) > 3 else ""),
            "su_deployments": ", ".join(dds_su_field_names) if dds_su_field_names else "Nil (All stationed at HQ / In-Charge JD)",
            "ad_status": ad_status_str,
            "remarks": hq_remarks
        })

        # --- Populate Tab 2 (Detailed Officer Roster) ---
        # 1. JD post(s)
        for idx, j in enumerate(jd_cadre, 1):
            inc_name = (j["incumbent_name"] or "").strip()
            inc_hrms = (j["incumbent_hrms"] or "").strip()
            is_substantive = bool(inc_name and inc_name.lower() not in ["vacant", "none", "null", ""])

            if is_substantive:
                officer_name = inc_name
                hrms_id = inc_hrms
                roster_sl_str = "Incumbent JD"
                deployment_status = "Substantive Joint Director in position"
                post_status = "Filled (Substantive)"
                remarks_str = f"Substantive Cadre Post {j['post_sl']} under Order 1809"
            elif senior_dd and idx == 1:
                officer_name = f"In-Charge: {senior_dd['officer_name']}"
                hrms_id = senior_dd["hrms_id"] or ""
                roster_sl_str = f"Roster Sl {senior_dd['sl_no']}"
                deployment_status = f"Held on Additional Charge / Service Utilized by Senior-most DDARD ({senior_dd['officer_name']})"
                post_status = "Filled (In-Charge SU)"
                remarks_str = f"Charge assigned as per seniority at Dist HQ (Roster Sl {senior_dd['sl_no']})"
            else:
                officer_name = "Vacant"
                hrms_id = "-"
                roster_sl_str = "-"
                deployment_status = "Vacant"
                post_status = "Vacant"
                remarks_str = f"Cadre Post {j['post_sl']} under Order 1809"

            detailed_roster_rows.append({
                "sl": global_roster_sl,
                "dist": dist_name,
                "estab": estab_name,
                "desig": j["designation"],
                "pay_level": j.get("pay_level") or "Level-19",
                "cadre_post_sl": j["post_sl"],
                "dd_sl": "-",
                "officer_name": officer_name,
                "hrms_id": hrms_id,
                "roster_sl": roster_sl_str,
                "deployment": deployment_status,
                "status": post_status,
                "remarks": remarks_str
            })
            global_roster_sl += 1

        # 2. DD posts (pair cadre_1794 dd posts with available_dd_posts and allotments)
        for idx, d_post in enumerate(dd_cadre):
            # Find corresponding allotment in hq_dd_allots
            allot = hq_dd_allots[idx] if idx < len(hq_dd_allots) else None
            if allot:
                dd_sl_num = allot["dd_sl"]
                d_name = allot["officer_name"] or "Unallotted"
                d_hrms = allot["hrms_id"] or "-"
                d_roster_sl = f"Roster Sl {allot['sl_no']}" if allot["sl_no"] else "-"
                
                # Check SU status
                su_txt = allot.get("su_post_name") or ""
                if "Basudev Sil" in d_name:
                    deploy_str = "Substantive at District HQ (SU: Nil)"
                    rem_str = "Promoted to Deputy Director, ARD, North 24 Parganas"
                elif senior_dd and allot["sl_no"] == senior_dd["sl_no"] and not substantive_jds:
                    deploy_str = "Substantive DD at HQ; Designated In-Charge Joint Director, ARD (on SU)"
                    rem_str = "Senior-most DD in District HQ; holds charge of In-Charge Joint Director"
                elif su_txt and su_txt.strip().lower() not in ["nil", "none", "null", ""]:
                    deploy_str = f"SU as: {su_txt}"
                    rem_str = "Service Utilized at designated station"
                else:
                    deploy_str = "Substantive at District HQ"
                    rem_str = "Promoted and posted to District HQ"

                p_status = "Filled (Substantive)" if allot["sl_no"] else "Vacant"
            else:
                dd_sl_num = "-"
                d_name = "Vacant"
                d_hrms = "-"
                d_roster_sl = "-"
                deploy_str = "Vacant"
                p_status = "Vacant"
                rem_str = "Sanctioned post under Order 1809"

            detailed_roster_rows.append({
                "sl": global_roster_sl,
                "dist": dist_name,
                "estab": estab_name,
                "desig": d_post["designation"],
                "pay_level": d_post.get("pay_level") or "Level-17",
                "cadre_post_sl": d_post["post_sl"],
                "dd_sl": dd_sl_num,
                "officer_name": d_name,
                "hrms_id": d_hrms,
                "roster_sl": d_roster_sl,
                "deployment": deploy_str,
                "status": p_status,
                "remarks": rem_str
            })
            global_roster_sl += 1

        # 3. AD posts
        for idx, a_post in enumerate(ad_cadre):
            inc_name = (a_post["incumbent_name"] or "").strip()
            inc_hrms = (a_post["incumbent_hrms"] or "").strip()

            if inc_name and inc_name.lower() not in ["vacant", "none", "null", ""]:
                if inc_hrms in roster_by_hrms:
                    prom_info = roster_by_hrms[inc_hrms]
                    officer_name = inc_name
                    hrms_id = inc_hrms
                    roster_sl_str = f"Roster Sl {prom_info['sl_no']} (Promoted to DD)"
                    deploy_str = f"Incumbent promoted to Deputy Director (Roster Sl {prom_info['sl_no']})"
                    p_status = "Vacant (Promoted)"
                    rem_str = f"Substantive promotion to DD ({prom_info['substantive_post_name']})"
                else:
                    officer_name = inc_name
                    hrms_id = inc_hrms
                    roster_sl_str = "Incumbent AD"
                    deploy_str = "Serving substantively at District HQ"
                    p_status = "Filled (Substantive)"
                    rem_str = "Substantive incumbent in position"
            else:
                officer_name = "Vacant"
                hrms_id = "-"
                roster_sl_str = "-"
                deploy_str = "Vacant"
                p_status = "Vacant"
                rem_str = f"Cadre Post {a_post['post_sl']} under Order 1809"

            detailed_roster_rows.append({
                "sl": global_roster_sl,
                "dist": dist_name,
                "estab": estab_name,
                "desig": a_post["designation"],
                "pay_level": a_post.get("pay_level") or "Level-16",
                "cadre_post_sl": a_post["post_sl"],
                "dd_sl": "-",
                "officer_name": officer_name,
                "hrms_id": hrms_id,
                "roster_sl": roster_sl_str,
                "deployment": deploy_str,
                "status": p_status,
                "remarks": rem_str
            })
            global_roster_sl += 1

    conn.close()
    return summary_rows, detailed_roster_rows

def add_summary_tab(wb, summary_rows):
    tab_name = "District_HQ_Cadre_Summary"
    if tab_name in wb.sheetnames:
        del wb[tab_name]
    ws = wb.create_sheet(title=tab_name)

    # Styles
    navy_header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    sub_header_fill = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    white_font_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="475569")
    data_font = Font(name="Calibri", size=10)
    data_bold = Font(name="Calibri", size=10, bold=True)
    green_font = Font(name="Calibri", size=10, bold=True, color="166534")
    blue_font = Font(name="Calibri", size=10, bold=True, color="1E40AF")
    amber_font = Font(name="Calibri", size=10, bold=True, color="9A3412")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    # Title Block
    ws.cell(1, 1, "GOVERNMENT OF WEST BENGAL — ANIMAL RESOURCES DEVELOPMENT DEPARTMENT").font = title_font
    ws.cell(2, 1, "DISTRICT HQ CADRE POSTING STATUS & SENIORITY HIERARCHY SUMMARY (ORDER NO. 1809-AR&AH DT. 18.06.2025)").font = data_bold
    ws.cell(3, 1, "In-Charge Joint Director (SU by Senior-Most DDARD), Deputy Director & Assistant Director Deployments across 23 Districts, Siliguri & Directorate HQ").font = subtitle_font

    headers = [
        "Sl No.",
        "District / HQ Set-up",
        "Sanctioned JD (L19)",
        "Sanctioned DD (L17)",
        "Sanctioned AD (L16)",
        "Total Sanctioned at HQ",
        "Joint Director / In-Charge JD Status (SU by Senior-Most DDARD)",
        "Substantive DDs at Dist HQ (Count & Roster Rank)",
        "DDs Serving at Dist HQ vs SU Field Attachments",
        "Assistant Directors at Dist HQ (Count & Incumbents)",
        "HQ Posting Situation & Administrative Remarks"
    ]

    header_row = 5
    ws.row_dimensions[header_row].height = 32
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(header_row, col_idx, h)
        c.fill = navy_header_fill
        c.font = white_font_bold
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = thin_border

    current_row = 6
    for idx, s in enumerate(summary_rows, 1):
        row_fill = alt_fill if idx % 2 == 0 else white_fill
        ws.row_dimensions[current_row].height = 24

        vals = [
            idx,
            s["dist_name"],
            s["sanctioned_jd"],
            s["sanctioned_dd"],
            s["sanctioned_ad"],
            s["total_sanctioned"],
            s["jd_status"],
            s["dd_status"],
            s["su_deployments"],
            s["ad_status"],
            s["remarks"]
        ]

        for col_idx, val in enumerate(vals, 1):
            c = ws.cell(current_row, col_idx, val)
            c.fill = row_fill
            c.border = thin_border

            if col_idx in [1, 3, 4, 5, 6]:
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.font = data_bold if col_idx in [1, 6] else data_font
            elif col_idx == 2:
                c.alignment = Alignment(horizontal="left", vertical="center")
                c.font = data_bold
            elif col_idx == 7:
                c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                c.font = green_font if "Substantive" in str(val) else blue_font
            elif col_idx in [8, 9, 10, 11]:
                c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                c.font = data_font

        current_row += 1

    # Add Totals row
    ws.row_dimensions[current_row].height = 26
    t_label = ws.cell(current_row, 2, "TOTAL STATE HQ CADRE")
    t_label.font = data_bold
    t_label.fill = sub_header_fill
    t_label.alignment = Alignment(horizontal="left", vertical="center")
    t_label.border = thin_border

    tot_jd = sum(s["sanctioned_jd"] for s in summary_rows)
    tot_dd = sum(s["sanctioned_dd"] for s in summary_rows)
    tot_ad = sum(s["sanctioned_ad"] for s in summary_rows)
    tot_all = sum(s["total_sanctioned"] for s in summary_rows)

    for c_idx, tot_val in [(3, tot_jd), (4, tot_dd), (5, tot_ad), (6, tot_all)]:
        tc = ws.cell(current_row, c_idx, tot_val)
        tc.font = white_font_bold
        tc.fill = sub_header_fill
        tc.alignment = Alignment(horizontal="center", vertical="center")
        tc.border = thin_border

    for c_idx in [1, 7, 8, 9, 10, 11]:
        tc = ws.cell(current_row, c_idx, "")
        tc.fill = sub_header_fill
        tc.border = thin_border

    # Freeze panes
    ws.freeze_panes = "C6"

    # Column widths
    col_widths = {
        "A": 8, "B": 24, "C": 18, "D": 18, "E": 18, "F": 18,
        "G": 38, "H": 42, "I": 42, "J": 38, "K": 45
    }
    for col_let, w in col_widths.items():
        ws.column_dimensions[col_let].width = w

def add_roster_tab(wb, roster_rows):
    tab_name = "District_HQ_Officer_Roster"
    if tab_name in wb.sheetnames:
        del wb[tab_name]
    ws = wb.create_sheet(title=tab_name)

    # Styles
    slate_header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    white_font_bold = Font(name="Calibri", size=10.5, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="475569")
    data_font = Font(name="Calibri", size=9.5)
    data_bold = Font(name="Calibri", size=9.5, bold=True)
    green_bold = Font(name="Calibri", size=9.5, bold=True, color="047857")
    blue_bold = Font(name="Calibri", size=9.5, bold=True, color="1E40AF")
    amber_bold = Font(name="Calibri", size=9.5, bold=True, color="B45309")
    gray_font = Font(name="Calibri", size=9.5, italic=True, color="64748B")

    fill_substantive = PatternFill(start_color="F0FDF4", end_color="F0FDF4", fill_type="solid") # soft green
    fill_incharge = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")   # soft blue
    fill_promoted = PatternFill(start_color="FEFCE8", end_color="FEFCE8", fill_type="solid")   # soft amber
    fill_vacant = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")     # slate 50
    fill_white = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # Title Block
    ws.cell(1, 1, "GOVERNMENT OF WEST BENGAL — ANIMAL RESOURCES DEVELOPMENT DEPARTMENT").font = title_font
    ws.cell(2, 1, "DISTRICT HQ POST-BY-POST CADRE ALLOTMENT & INCUMBENT ROSTER (ORDER NO. 1809-AR&AH)").font = data_bold
    ws.cell(3, 1, "Line-by-Line Status of Sanctioned Joint Directors (L19), Deputy Directors (L17) & Assistant Directors (L16) at all District HQs").font = subtitle_font

    headers = [
        "Sl No.",
        "District / Unit",
        "Establishment / Office",
        "Sanctioned Designation (Order 1809)",
        "Pay Level",
        "Cadre 1794 Post Sl",
        "DD Vacancy Sl (if DD)",
        "Substantive Officer Name",
        "HRMS ID",
        "Roster Sl / Seniority",
        "Physical Deployment / SU Status / Additional Charge",
        "Post Status",
        "Administrative Remarks & Authority"
    ]

    header_row = 5
    ws.row_dimensions[header_row].height = 32
    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(header_row, col_idx, h)
        c.fill = slate_header_fill
        c.font = white_font_bold
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = thin_border

    current_row = 6
    for r in roster_rows:
        ws.row_dimensions[current_row].height = 20

        status_txt = r["status"]
        if "In-Charge" in status_txt:
            row_fill = fill_incharge
            status_font = blue_bold
        elif "Filled (Substantive)" in status_txt:
            row_fill = fill_substantive
            status_font = green_bold
        elif "Promoted" in status_txt:
            row_fill = fill_promoted
            status_font = amber_bold
        else:
            row_fill = fill_vacant
            status_font = gray_font

        vals = [
            r["sl"],
            r["dist"],
            r["estab"],
            r["desig"],
            r["pay_level"],
            r["cadre_post_sl"],
            r["dd_sl"],
            r["officer_name"],
            r["hrms_id"],
            r["roster_sl"],
            r["deployment"],
            r["status"],
            r["remarks"]
        ]

        for col_idx, val in enumerate(vals, 1):
            c = ws.cell(current_row, col_idx, val)
            c.fill = row_fill
            c.border = thin_border

            if col_idx in [1, 5, 6, 7, 9, 10]:
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.font = data_font
            elif col_idx in [2, 3, 4]:
                c.alignment = Alignment(horizontal="left", vertical="center")
                c.font = data_bold if col_idx in [2, 4] else data_font
            elif col_idx == 8:
                c.alignment = Alignment(horizontal="left", vertical="center")
                c.font = data_bold
            elif col_idx == 11:
                c.alignment = Alignment(horizontal="left", vertical="center")
                c.font = data_font
            elif col_idx == 12:
                c.alignment = Alignment(horizontal="center", vertical="center")
                c.font = status_font
            elif col_idx == 13:
                c.alignment = Alignment(horizontal="left", vertical="center")
                c.font = data_font

        current_row += 1

    # Freeze panes
    ws.freeze_panes = "D6"

    # Column widths
    col_widths = {
        "A": 7, "B": 22, "C": 30, "D": 32, "E": 12, "F": 16,
        "G": 18, "H": 28, "I": 14, "J": 22, "K": 45, "L": 22, "M": 45
    }
    for col_let, w in col_widths.items():
        ws.column_dimensions[col_let].width = w

def fix_dr_basudev_sil_and_names(ws):
    print("Applying exact names and fixing Dr. Basudev Sil in master posting sheet...")
    # Load revised names
    revised_wb = openpyxl.load_workbook("/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /From AD HQ/Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx")
    revised_ws = revised_wb.active
    revised_names = {}
    for r in range(1, revised_ws.max_row + 1):
        c1 = revised_ws.cell(r, 1).value
        c2 = revised_ws.cell(r, 2).value
        if c1 is not None and str(c1).strip().isdigit() and c2:
            revised_names[int(str(c1).strip())] = str(c2).strip()

    for r in range(2, 330):
        sl_242 = ws.cell(r, 2).value
        if sl_242 is not None and str(sl_242).strip().isdigit():
            num_242 = int(str(sl_242).strip())
            if num_242 in revised_names:
                ws.cell(r, 3, revised_names[num_242])

        # Check Dr. Basudev Sil specifically
        name_val = str(ws.cell(r, 3).value or "")
        if "Basudev Sil" in name_val:
            print(f"Fixing Dr. Basudev Sil at row {r}...")
            ws.cell(r, 11, "Deputy Director, ARD, O/O the JD ARD, North 24 Parganas")
            ws.cell(r, 12, "Nil")
            ws.cell(r, 13, "Promoted to Deputy Director, ARD, North 24 Parganas")
            white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            for c in range(1, 14):
                ws.cell(r, c).fill = white_fill

def main():
    print("=== Step 1: Compiling District HQ Data from Order 1809 and Database ===")
    summary_rows, detailed_roster_rows = build_district_hq_data()
    print(f"Compiled {len(summary_rows)} District HQ summary entries.")
    print(f"Compiled {len(detailed_roster_rows)} District HQ detailed roster posts.")

    # Target files to update:
    target_files = [
        os.path.join(WORKSPACE, "current_drive_sheet.xlsx"),
        os.path.join(WORKSPACE, "20260913_0012_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_0.03MB_mb.xlsx"),
        os.path.join(WORKSPACE, "WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx")
    ]

    for fpath in target_files:
        if not os.path.exists(fpath):
            continue
        print(f"\nProcessing {os.path.basename(fpath)}...")
        wb = openpyxl.load_workbook(fpath)

        # Fix names & Dr. Basudev Sil in the first sheet
        ws_master = wb["11_Column_Master_Posting_Order"] if "11_Column_Master_Posting_Order" in wb.sheetnames else wb.worksheets[0]
        fix_dr_basudev_sil_and_names(ws_master)

        # Add Tab 2: District_HQ_Cadre_Summary
        add_summary_tab(wb, summary_rows)

        # Add Tab 3: District_HQ_Officer_Roster
        add_roster_tab(wb, detailed_roster_rows)

        wb.save(fpath)
        print(f"Saved {fpath} with sheets: {wb.sheetnames}")

if __name__ == "__main__":
    main()
