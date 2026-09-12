#!/usr/bin/env python3
"""
order_generator.py
Generates Official Government Orders & Notifications in:
1. Formatted Excel (.xlsx) with columns specified by Government of West Bengal:
   - Sl No
   - Name of the Officers with present place of posting
   - Present pay level
   - Transfer by
   - Place of posting on promotion / transfer/utilization of service
   - Pay level upon transfer
2. Official Word Document (.docx) following WB ARD Secretariat Notification standard (Memo 391-AR&AH)
3. Printable HTML Gazette Notification view
"""

import os
import sqlite3
import datetime
from typing import Dict, List, Optional, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
DEFAULT_DB_PATH = "/tmp/ard_master_truth.db" if is_vercel else os.path.join(BASE_DIR, "ard_master_truth.db")
DEFAULT_OUT_DIR = "/tmp" if is_vercel else BASE_DIR

class OrderGenerator:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- 1. EXCEL ORDER GENERATOR ---

    def generate_excel_order(self, session_id: str = "CURRENT_SESSION", output_path: Optional[str] = None) -> str:
        """
        Generates Government Excel export with exact requested columns:
        - Sl No
        - Name of the Officers with present place of posting
        - Present pay level
        - Transfer by
        - Place of posting on promotion / transfer/utilization of service
        - Pay level upon transfer
        """
        if not output_path:
            output_path = os.path.join(DEFAULT_OUT_DIR, f"Draft_Government_Posting_Order_{session_id}.xlsx")

        conn = self.get_connection()
        cur = conn.cursor()

        # 1. Fetch simulation assignments
        cur.execute("""
        SELECT 
            id,
            officer_hrms_id,
            officer_name,
            from_post_name,
            to_post_name,
            substantive_post_name,
            su_post_name,
            officer_type,
            reason,
            collision_displaced_officer,
            collision_displaced_hrms,
            timestamp
        FROM simulation_assignments
        WHERE session_id = ?
        ORDER BY id ASC
        """, (session_id,))
        assignments = [dict(r) for r in cur.fetchall()]

        # 2. Fetch Roster status
        cur.execute("""
        SELECT sl_no, roster_point, point_reserved_for, officer_name, hrms_id, caste,
               detailed_presentation, service_ends, substantive_post_name, su_post_name, allotment_status
        FROM roster_50_point_candidates
        ORDER BY sl_no
        """)
        roster_rows = [dict(r) for r in cur.fetchall()]

        # 3. Fetch Obliterated status
        cur.execute("""
        SELECT oblit_sl, post_name, establishment, district, officer_name, hrms_id,
               rehabilitation_status, substantive_post_name, su_post_name
        FROM obliterated_posts_1808
        ORDER BY oblit_sl
        """)
        oblit_rows = [dict(r) for r in cur.fetchall()]

        # 4. Fetch Displaced pool
        cur.execute("""
        SELECT * FROM displaced_officers_pool WHERE session_id = ? ORDER BY id
        """, (session_id,))
        displaced_rows = [dict(r) for r in cur.fetchall()]

        conn.close()

        # Build Workbook
        wb = openpyxl.Workbook()
        ws_order = wb.active
        ws_order.title = "Draft_Posting_Order"

        # Government Title Block in Excel
        ws_order.merge_cells("A1:F1")
        title_cell = ws_order["A1"]
        title_cell.value = "GOVERNMENT OF WEST BENGAL — ANIMAL RESOURCES DEVELOPMENT DEPARTMENT"
        title_cell.font = Font(name="Arial", size=13, bold=True, color="FFFFFF")
        title_cell.fill = PatternFill(start_color="0A2540", end_color="0A2540", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_order.row_dimensions[1].height = 32

        ws_order.merge_cells("A2:F2")
        sub_cell = ws_order["A2"]
        sub_cell.value = f"Draft Government Notification Schedule — Administrative Posting & Promotion Order (Session: {session_id} | Date: {datetime.date.today().strftime('%d.%m.%Y')})"
        sub_cell.font = Font(name="Arial", size=10, italic=True, color="1E3A8A")
        sub_cell.fill = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
        sub_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws_order.row_dimensions[2].height = 22

        # Columns explicitly requested by User
        columns = [
            "Sl No",
            "Name of the Officers with present place of posting",
            "Present pay level",
            "Transfer by",
            "Place of posting on promotion / transfer/utilization of service",
            "Pay level upon transfer"
        ]

        ws_order.append([]) # Row 3 blank
        ws_order.append(columns) # Row 4 Header
        header_row = 4
        ws_order.row_dimensions[header_row].height = 28

        header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        border_all = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        for col_idx in range(1, len(columns) + 1):
            c = ws_order.cell(row=header_row, column=col_idx)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = border_all

        # Populate rows
        for idx, a in enumerate(assignments, start=1):
            off_name = a["officer_name"]
            hrms = a["officer_hrms_id"]
            from_p = a["from_post_name"] or "Departmental Post"
            officer_str = f"{off_name} (HRMS: {hrms}), {from_p}"

            # Present pay level determination
            present_pay = "Level 16 (Rs. 56,100 - Rs. 1,44,300)"
            target_pay = "Level 19 (Rs. 95,100 - Rs. 1,48,000)"
            transfer_type = a.get("reason") or "Promotion"

            if a.get("officer_type") == "roster":
                present_pay = "Level 16 (Rs. 56,100 - Rs. 1,44,300)"
                target_pay = "Level 19 (Rs. 95,100 - Rs. 1,48,000)"
                transfer_type = "Promotion (50-Point Roster)"
            elif a.get("officer_type") == "obliterated":
                present_pay = "Level 16 (Rs. 56,100 - Rs. 1,44,300)"
                target_pay = "Level 16 / Level 17 (Lateral Cadre)"
                transfer_type = "Rehabilitation (Notification 1808)"
            elif a.get("officer_type") == "displaced":
                present_pay = "Level 16 (Rs. 56,100 - Rs. 1,44,300)"
                target_pay = "Level 16 (Cadre Transfer)"
                transfer_type = "Transfer due to Displacement"

            # Target posting formulation
            sub_target = a.get("substantive_post_name") or a.get("to_post_name") or "Cadre Post"
            su_target = a.get("su_post_name")
            target_str = sub_target
            if su_target:
                target_str += f"\n[Service Utilization at: {su_target}]"
                transfer_type += " / Service Utilization"

            row_vals = [
                idx,
                officer_str,
                present_pay,
                transfer_type,
                target_str,
                target_pay
            ]

            ws_order.append(row_vals)
            curr_row = ws_order.max_row
            ws_order.row_dimensions[curr_row].height = 36

            bg_color = "F8FAFC" if idx % 2 == 0 else "FFFFFF"
            row_fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type="solid")

            for c_idx in range(1, len(row_vals) + 1):
                cell = ws_order.cell(row=curr_row, column=c_idx)
                cell.fill = row_fill
                cell.border = border_all
                cell.font = Font(name="Arial", size=9.5)
                if c_idx in [1, 3, 4, 6]:
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # Set Column Widths
        col_widths = {1: 8, 2: 45, 3: 25, 4: 25, 5: 45, 6: 25}
        for c_idx, w in col_widths.items():
            col_letter = openpyxl.utils.get_column_letter(c_idx)
            ws_order.column_dimensions[col_letter].width = w

        # --- Sheet 2: 50-Point Roster Panel ---
        ws_roster = wb.create_sheet(title="50_Point_Roster_Status")
        r_headers = ["Sl No", "Roster Pt", "Quota", "Officer Name", "HRMS ID", "Caste", "Detailed Present Posting", "Superannuation", "Substantive DD Post", "SU Attached Post", "Status"]
        ws_roster.append(r_headers)
        for r in roster_rows:
            ws_roster.append([
                r["sl_no"], r["roster_point"], r["point_reserved_for"], r["officer_name"],
                r["hrms_id"], r["caste"], r["detailed_presentation"], r["service_ends"],
                r["substantive_post_name"] or "Pending", r["su_post_name"] or "-", r["allotment_status"]
            ])

        # --- Sheet 3: Obliterated Posts Schedule ---
        ws_oblit = wb.create_sheet(title="Obliterated_Posts_Schedule")
        o_headers = ["Oblit Sl", "Abolished Post", "Establishment", "District", "Incumbent Officer", "HRMS ID", "Status", "Substantive Post", "SU Attached Post"]
        ws_oblit.append(o_headers)
        for o in oblit_rows:
            ws_oblit.append([
                o["oblit_sl"], o["post_name"], o["establishment"], o["district"],
                o["officer_name"], o["hrms_id"], o["rehabilitation_status"],
                o["substantive_post_name"] or "Pending", o["su_post_name"] or "-"
            ])

        # --- Sheet 4: Displaced Queue Pool ---
        ws_disp = wb.create_sheet(title="Displaced_Queue_Pool")
        d_headers = ["ID", "Displaced Officer Name", "HRMS ID", "Original Post", "District", "Displaced By (Promotee)", "Status", "Re-allotted Post"]
        ws_disp.append(d_headers)
        for d in displaced_rows:
            ws_disp.append([
                d["id"], d["officer_name"], d["officer_hrms"], d["from_post_name"],
                d["district"], f"{d['displaced_by_name']} ({d['displaced_by_hrms']})",
                d["rehabilitation_status"], d["reallocated_post_name"] or "Pending"
            ])

        wb.save(output_path)
        return output_path

    # --- 2. OFFICIAL DOCX GOVERNMENT NOTIFICATION GENERATOR ---

    def generate_docx_order(self, session_id: str = "CURRENT_SESSION", output_path: Optional[str] = None) -> str:
        """
        Generates official West Bengal Secretariat Notification in Microsoft Word (.docx) format
        strictly following the format of Memo No. 391-AR&AH/AD/0/3A-16/2025.
        """
        if not output_path:
            output_path = os.path.join(DEFAULT_OUT_DIR, f"Official_Notification_Order_{session_id}.docx")

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
        SELECT 
            id, officer_hrms_id, officer_name, from_post_name, substantive_post_name,
            su_post_name, officer_type, reason
        FROM simulation_assignments
        WHERE session_id = ?
        ORDER BY id ASC
        """, (session_id,))
        assignments = [dict(r) for r in cur.fetchall()]
        conn.close()

        doc = Document()

        # Set page margins to standard 1 inch
        for section in doc.sections:
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.0)
            section.right_margin = Inches(1.0)

        # Header: Government of West Bengal
        p_head = doc.add_paragraph()
        p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_head.paragraph_format.space_after = Pt(2)
        r1 = p_head.add_run("Government of West Bengal\n")
        r1.bold = True
        r1.font.size = Pt(13)
        r1.font.name = "Arial"

        r2 = p_head.add_run("Animal Resources Development Department\n")
        r2.bold = True
        r2.font.size = Pt(12)
        r2.font.name = "Arial"

        r3 = p_head.add_run("AR & AH Branch, Prani Sampad Bhawan, LB - 2, Sector - III, Salt Lake, Kolkata - 700 106")
        r3.font.size = Pt(10)
        r3.font.name = "Arial"

        # Memo Number & Date Line
        doc.add_paragraph()
        p_memo = doc.add_paragraph()
        p_memo.paragraph_format.space_after = Pt(14)
        run_memo = p_memo.add_run(f"No. 1890-AR&AH/3A-16/2026")
        run_memo.bold = True
        run_memo.font.size = Pt(10.5)
        run_memo.font.name = "Arial"

        p_memo.add_run("\t\t\t\t\t\tDate: " + datetime.date.today().strftime("%d.%m.%Y"))

        # NOTIFICATION Title
        p_notif = doc.add_paragraph()
        p_notif.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_notif.paragraph_format.space_after = Pt(12)
        r_notif = p_notif.add_run("NOTIFICATION")
        r_notif.bold = True
        r_notif.font.size = Pt(12)
        r_notif.font.underline = True
        r_notif.font.name = "Arial"

        # Formal Preamble
        p_preamble = doc.add_paragraph()
        p_preamble.paragraph_format.line_spacing = 1.15
        p_preamble.paragraph_format.space_after = Pt(12)
        num_officers = len(assignments) or "the"
        preamble_text = (
            f"The Governor is pleased to appoint / promote / transfer the following {num_officers} officers borne under "
            f"the West Bengal Animal Husbandry & Veterinary Service to the posts mentioned against their names on "
            f"promotion / transfer / placement of service in the Pay Level indicated under WBS (ROPA) Rules, 2019 "
            f"and allowances as admissible from time to time under the said Rules with effect from the date of taking over "
            f"charge of their respective posts under the Directorate of Animal Resources & Animal Health, West Bengal. "
            f"Their places of posting upon promotion / transfer / service utilization are mentioned below:"
        )
        r_pre = p_preamble.add_run(preamble_text)
        r_pre.font.size = Pt(10.5)
        r_pre.font.name = "Arial"

        # Tabular Schedule
        table = doc.add_table(rows=1, cols=3)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        # Set widths: Sl(0.6 in), Officer(3.2 in), Target(3.2 in)
        widths = [Inches(0.6), Inches(3.2), Inches(3.2)]

        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Sl. No."
        hdr_cells[1].text = "Name of the Officers with Present Posting"
        hdr_cells[2].text = "Place of Posting on Promotion / Transfer / Utilization of Service"

        for i, cell in enumerate(hdr_cells):
            cell.width = widths[i]
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.size = Pt(10)
            cell.paragraphs[0].runs[0].font.name = "Arial"
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            shading_elm = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls('w')))
            cell._tc.get_or_add_tcPr().append(shading_elm)

        # Add Data Rows
        for idx, a in enumerate(assignments, start=1):
            row_cells = table.add_row().cells
            row_cells[0].width = widths[0]
            row_cells[1].width = widths[1]
            row_cells[2].width = widths[2]

            row_cells[0].text = str(idx)
            row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

            # Officer Info
            p_off = row_cells[1].paragraphs[0]
            r_o_name = p_off.add_run(f"{a['officer_name']}\n")
            r_o_name.bold = True
            r_o_post = p_off.add_run(f"{a['from_post_name'] or 'Departmental Station'}\n(HRMS: {a['officer_hrms_id']})")
            r_o_post.font.size = Pt(9.5)

            # Target Posting Info
            p_tgt = row_cells[2].paragraphs[0]
            sub_post = a.get("substantive_post_name") or a.get("to_post_name") or "Cadre Station"
            r_tgt_main = p_tgt.add_run(f"{sub_post}\n")
            r_tgt_main.bold = True

            if a.get("su_post_name"):
                r_su = p_tgt.add_run(f"He/She will also act on Service Utilization at: {a['su_post_name']} until further order.\n")
                r_su.font.size = Pt(9.5)
                r_su.font.color.rgb = RGBColor(15, 118, 110)

            # Style text
            for c in row_cells:
                for p in c.paragraphs:
                    for r in p.runs:
                        r.font.name = "Arial"
                        if not r.font.size:
                            r.font.size = Pt(9.5)

        # Public interest clause
        doc.add_paragraph()
        p_pi = doc.add_paragraph()
        p_pi.paragraph_format.space_before = Pt(12)
        r_pi = p_pi.add_run("This appointment / transfer is made in the interest of public service.")
        r_pi.font.size = Pt(10.5)
        r_pi.font.italic = True
        r_pi.font.name = "Arial"

        # Signatory block
        doc.add_paragraph()
        p_sig = doc.add_paragraph()
        p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r_sig1 = p_sig.add_run("By the order of the Governor,\n\n\nSd/-\nSpecial Secretary\nto the Government of West Bengal")
        r_sig1.font.size = Pt(10)
        r_sig1.font.name = "Arial"

        # Copy forwarded section
        p_copy_head = doc.add_paragraph()
        p_copy_head.paragraph_format.space_before = Pt(14)
        r_cp_head = p_copy_head.add_run(f"No. 1890 / 1(15) - AR&AH/3A-16/2026\t\t\tDate: {datetime.date.today().strftime('%d.%m.%Y')}")
        r_cp_head.bold = True
        r_cp_head.font.size = Pt(10)
        r_cp_head.font.name = "Arial"

        p_forward = doc.add_paragraph()
        r_fwd = p_forward.add_run("Copy forwarded for information and necessary action to:\n")
        r_fwd.font.size = Pt(10)
        r_fwd.bold = True
        r_fwd.font.name = "Arial"

        standard_copies = [
            "The Principal Accountant General (A&E), West Bengal, Treasury Buildings, Kolkata - 700 001.",
            "The Accountant General (Audit), West Bengal, Treasury Buildings, Kolkata - 700 001.",
            "The Pay & Accounts Officer, Kolkata Pay & Accounts Office - III, Subhanna, Salt Lake, Kolkata - 700 064.",
            "The Director of AH&VS, West Bengal. He is requested to forward the joining reports of the officers to this Department.",
            "The Managing Director, West Bengal Livestock Development Corporation Ltd. (WBLDCL).",
            "The Chief Executive Officer, Paschim Banga Go Sampad Bikash Sanstha (PBGSBS).",
            "The Director, Institute of Animal Health & Veterinary Biologicals (IAH&VB), Belgachia, Kolkata.",
            "The Joint Director, ARD (All Zones / Divisions).",
            "The Deputy Director, ARD & PO (All Districts).",
            "The Treasury Officer (All concerned Treasuries).",
            "The P.S. to the Hon’ble Minister-in-Charge, Animal Resources Development Department.",
            "The Sr. P.S. to the Additional Chief Secretary, Animal Resources Development Department.",
            "Dr. ...................................................................................., for immediate compliance.",
            "The Nodal Officer, IT & Website, with the request to upload this Notification on the Departmental Website.",
            "Guard File."
        ]

        for i, cp in enumerate(standard_copies, start=1):
            p_c = doc.add_paragraph()
            p_c.paragraph_format.space_after = Pt(2)
            p_c.paragraph_format.left_indent = Inches(0.25)
            r_c = p_c.add_run(f"{i}. {cp}")
            r_c.font.size = Pt(9.5)
            r_c.font.name = "Arial"

        # Final Deputy Secretary sign
        p_end = doc.add_paragraph()
        p_end.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_end.paragraph_format.space_before = Pt(20)
        r_end = p_end.add_run("Deputy Secretary\nto the Government of West Bengal")
        r_end.font.size = Pt(10)
        r_end.font.name = "Arial"

        doc.save(output_path)
        return output_path

    # --- 3. PRINTABLE HTML GAZETTE NOTIFICATION VIEW ---

    def generate_html_order(self, session_id: str = "CURRENT_SESSION") -> str:
        """
        Generates an authentic Government of West Bengal printable HTML Notification.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
        SELECT 
            id, officer_hrms_id, officer_name, from_post_name, substantive_post_name,
            su_post_name, officer_type, reason
        FROM simulation_assignments
        WHERE session_id = ?
        ORDER BY id ASC
        """, (session_id,))
        assignments = [dict(r) for r in cur.fetchall()]
        conn.close()

        rows_html = ""
        for idx, a in enumerate(assignments, start=1):
            sub_post = a.get("substantive_post_name") or a.get("to_post_name") or "Cadre Station"
            su_post = a.get("su_post_name")
            su_text = f"<div style='color: #0f766e; font-size: 11px; margin-top: 4px;'><strong>Service Utilization:</strong> {su_post} (until further order)</div>" if su_post else ""

            rows_html += f"""
            <tr>
                <td style="padding: 10px; text-align: center; font-weight: bold; border: 1px solid #cbd5e1; vertical-align: top;">{idx}</td>
                <td style="padding: 10px; border: 1px solid #cbd5e1; vertical-align: top;">
                    <div style="font-weight: bold; color: #0f172a;">{a['officer_name']}</div>
                    <div style="font-size: 11px; color: #475569;">{a['from_post_name'] or 'Present Station'}</div>
                    <div style="font-family: monospace; font-size: 10px; color: #64748b;">HRMS: {a['officer_hrms_id']}</div>
                </td>
                <td style="padding: 10px; border: 1px solid #cbd5e1; vertical-align: top;">
                    <div style="font-weight: bold; color: #1e3a8a;">{sub_post}</div>
                    {su_text}
                </td>
            </tr>
            """

        if not rows_html:
            rows_html = """
            <tr>
                <td colspan="3" style="padding: 24px; text-align: center; color: #94a3b8; font-style: italic;">
                    No simulated assignments found in active session. Allot officers or execute Auto-Solver to populate draft notification schedule.
                </td>
            </tr>
            """

        today_str = datetime.date.today().strftime("%d.%m.%Y")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Government Notification — ARD Department</title>
    <style>
        body {{
            font-family: 'Times New Roman', Times, serif;
            color: #000;
            background: #fff;
            margin: 0;
            padding: 40px;
            font-size: 12pt;
            line-height: 1.4;
        }}
        .header {{
            text-align: center;
            margin-bottom: 25px;
        }}
        .header h2 {{
            margin: 0;
            font-size: 15pt;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .header h3 {{
            margin: 3px 0;
            font-size: 13pt;
        }}
        .header p {{
            margin: 2px 0;
            font-size: 10pt;
        }}
        .memo-bar {{
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
            margin-bottom: 20px;
            font-size: 11pt;
            font-weight: bold;
        }}
        .title-notification {{
            text-align: center;
            font-size: 14pt;
            font-weight: bold;
            text-decoration: underline;
            letter-spacing: 2px;
            margin-bottom: 18px;
        }}
        .preamble {{
            text-align: justify;
            margin-bottom: 20px;
            text-indent: 40px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
        }}
        th {{
            background: #f1f5f9;
            font-weight: bold;
            padding: 8px;
            border: 1px solid #cbd5e1;
            font-size: 11pt;
        }}
        .sign-box {{
            text-align: right;
            margin-top: 30px;
            margin-bottom: 30px;
        }}
        .copy-block {{
            margin-top: 20px;
            font-size: 10pt;
            line-height: 1.45;
        }}
        .no-print {{
            position: fixed;
            top: 15px;
            right: 20px;
            display: flex;
            gap: 10px;
            z-index: 9999;
        }}
        .btn {{
            background: #0284c7;
            color: #fff;
            padding: 8px 16px;
            border-radius: 6px;
            text-decoration: none;
            font-family: sans-serif;
            font-size: 12px;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            cursor: pointer;
            border: none;
        }}
        .btn-doc {{
            background: #1e3a8a;
        }}
        @media print {{
            .no-print {{ display: none; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>
    <div class="no-print">
        <a href="/api/simulation/export-docx" class="btn btn-doc">Download Word Doc (.docx)</a>
        <button onclick="window.print()" class="btn">Print / Save as PDF</button>
    </div>

    <div class="header">
        <h2>Government of West Bengal</h2>
        <h3>Animal Resources Development Department</h3>
        <p>AR & AH Branch, Prani Sampad Bhawan, LB - 2, Sector - III, Salt Lake, Kolkata - 700 106</p>
    </div>

    <div class="memo-bar">
        <div>No. 1890-AR&AH/3A-16/2026</div>
        <div>Date: {today_str}</div>
    </div>

    <div class="title-notification">NOTIFICATION</div>

    <div class="preamble">
        The Governor is pleased to appoint / promote / transfer the following officers borne under the West Bengal Animal Husbandry & Veterinary Service to the posts mentioned against their names on promotion / transfer / placement of service in the Pay Level indicated under WBS (ROPA) Rules, 2019 and allowances as admissible from time to time under the said Rules with effect from the date of taking over charge of their respective posts under the Directorate of Animal Resources & Animal Health, West Bengal. Their places of posting upon promotion / transfer / service utilization are mentioned below:
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 8%;">Sl. No.</th>
                <th style="width: 46%;">Name of the Officers with Present Posting</th>
                <th style="width: 46%;">Place of Posting on Promotion / Transfer / Utilization of Service</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <div style="font-style: italic; margin-bottom: 25px;">
        This appointment / transfer is made in the interest of public service.
    </div>

    <div class="sign-box">
        By the order of the Governor,<br><br><br>
        <strong>Sd/-</strong><br>
        Special Secretary<br>
        to the Government of West Bengal
    </div>

    <div class="memo-bar" style="border-top: 1px solid #cbd5e1; padding-top: 15px;">
        <div>No. 1890 / 1(15) - AR&AH/3A-16/2026</div>
        <div>Date: {today_str}</div>
    </div>

    <div class="copy-block">
        <strong>Copy forwarded for information and necessary action to:</strong><br>
        1. The Principal Accountant General (A&E), West Bengal, Treasury Buildings, Kolkata - 700 001.<br>
        2. The Accountant General (Audit), West Bengal, Treasury Buildings, Kolkata - 700 001.<br>
        3. The Pay & Accounts Officer, Kolkata Pay & Accounts Office - III, Salt Lake, Kolkata - 700 064.<br>
        4. The Director of AH&VS, West Bengal. He is requested to forward the joining reports to this Department.<br>
        5. The Managing Director, West Bengal Livestock Development Corporation Ltd. (WBLDCL).<br>
        6. The Chief Executive Officer, Paschim Banga Go Sampad Bikash Sanstha (PBGSBS).<br>
        7. The Director, Institute of Animal Health & Veterinary Biologicals (IAH&VB), Belgachia, Kolkata.<br>
        8. The Joint Director, ARD (All Zones / Divisions).<br>
        9. The Deputy Director, ARD & PO (All Districts).<br>
        10. The Treasury Officer (All concerned Treasuries).<br>
        11. The P.S. to the Hon’ble Minister-in-Charge, Animal Resources Development Department.<br>
        12. The Sr. P.S. to the Additional Chief Secretary, Animal Resources Development Department.<br>
        13. Dr. ...................................................................................., for immediate compliance.<br>
        14. The Nodal Officer, IT & Website, with the request to upload this Notification on the Departmental Website.<br>
        15. Guard File.<br>
    </div>

    <div class="sign-box" style="margin-top: 35px;">
        <strong>Deputy Secretary</strong><br>
        to the Government of West Bengal
    </div>
</body>
</html>"""
        return html

_default_generator = OrderGenerator()

def generate_excel_order(session_id: str = "CURRENT_SESSION", output_path: Optional[str] = None) -> str:
    return _default_generator.generate_excel_order(session_id, output_path)

def generate_docx_order(session_id: str = "CURRENT_SESSION", output_path: Optional[str] = None) -> str:
    return _default_generator.generate_docx_order(session_id, output_path)

def generate_html_order(session_id: str = "CURRENT_SESSION") -> str:
    return _default_generator.generate_html_order(session_id)

if __name__ == "__main__":
    gen = OrderGenerator()
    print("Testing OrderGenerator...")
    xlsx_path = gen.generate_excel_order("TEST_RUN")
    print("Generated Excel:", xlsx_path)
    docx_path = gen.generate_docx_order("TEST_RUN")
    print("Generated Word Docx:", docx_path)
