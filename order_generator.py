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

from generate_simple_4col_order import clean_pres, clean_sub, clean_su, build_order

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
        strictly following the 4-column, single black line border table format requested by the user.
        """
        generated_file = build_order()
        if output_path and os.path.abspath(output_path) != os.path.abspath(generated_file):
            import shutil
            shutil.copyfile(generated_file, output_path)
            return output_path
        return generated_file

    # --- 3. PRINTABLE HTML GAZETTE NOTIFICATION VIEW ---

    def generate_html_order(self, session_id: str = "CURRENT_SESSION") -> str:
        """
        Generates an authentic Government of West Bengal printable HTML Gazette Notification
        strictly formatted with the requested 4 columns and black line borders:
        - Sl no.
        - Name of the Officers with Present posting
        - Place of posting on promotion / Transfer (Substantive post)
        - Service Utilized post (if any)
        """
        conn = self.get_connection()
        cur = conn.cursor()

        # Schedule I: 242 Promotees
        cur.execute("""
            SELECT sl_no, officer_name, present_posting, substantive_post_name, su_post_name
            FROM roster_50_point_candidates
            ORDER BY sl_no ASC
        """)
        roster_rows = cur.fetchall()

        # Schedule II: 61 Obliterated Non-Roster Rehabilitations
        cur.execute("""
            SELECT oblit_sl, officer_name, post_name, district, establishment, substantive_post_name, su_post_name
            FROM obliterated_posts_1808
            WHERE is_vacant = 'No' AND (is_on_roster = 0 OR is_on_roster IS NULL)
            ORDER BY oblit_sl ASC
        """)
        oblit_rows = cur.fetchall()

        # Schedule III: 14 Consequential Lateral Transfers
        cur.execute("""
            SELECT sl_no, officer_name, present_posting, transferred_post_name, reason_notes
            FROM executive_lateral_transfers
            ORDER BY sl_no ASC
        """)
        lateral_rows = cur.fetchall()
        conn.close()

        def render_table_rows(rows, row_type):
            out = ""
            for idx, r in enumerate(rows, 1):
                if row_type == "roster":
                    sl = str(r["sl_no"])
                    c2 = clean_pres(r["officer_name"], r["present_posting"])
                    c3 = clean_sub(r["substantive_post_name"])
                    c4 = clean_su(r["su_post_name"])
                elif row_type == "oblit":
                    sl = str(idx)
                    pres = f"{r['post_name']}, {r['establishment'] or r['district']}"
                    c2 = clean_pres(r["officer_name"], pres)
                    c3 = clean_sub(r["substantive_post_name"])
                    c4 = clean_su(r["su_post_name"])
                else: # lateral
                    sl = str(r["sl_no"])
                    c2 = clean_pres(r["officer_name"], r["present_posting"])
                    c3 = clean_sub(r["transferred_post_name"])
                    c4 = clean_su(r["reason_notes"])

                su_style = "text-align: center;" if c4 == "Nil" else "text-align: left; font-weight: bold; color: #047857;"
                out += f"""
                <tr>
                    <td style="border: 1px solid #000; padding: 6px 8px; text-align: center; font-weight: bold;">{sl}</td>
                    <td style="border: 1px solid #000; padding: 6px 8px; text-align: left;">{c2}</td>
                    <td style="border: 1px solid #000; padding: 6px 8px; text-align: left;">{c3}</td>
                    <td style="border: 1px solid #000; padding: 6px 8px; {su_style}">{c4}</td>
                </tr>"""
            return out

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
            font-size: 11pt;
            line-height: 1.35;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .header h2 {{
            margin: 0;
            font-size: 14pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .header h3 {{
            margin: 3px 0;
            font-size: 12pt;
        }}
        .header p {{
            margin: 2px 0;
            font-size: 9.5pt;
        }}
        .memo-bar {{
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            margin-bottom: 15px;
            font-size: 10.5pt;
            font-weight: bold;
        }}
        .title-notification {{
            text-align: center;
            font-size: 13pt;
            font-weight: bold;
            letter-spacing: 1.5px;
            margin-bottom: 14px;
            text-decoration: underline;
        }}
        .preamble {{
            text-align: justify;
            margin-bottom: 18px;
            text-indent: 30px;
            font-size: 10.5pt;
        }}
        .sched-title {{
            font-size: 11pt;
            font-weight: bold;
            margin-top: 24px;
            margin-bottom: 8px;
            color: #000;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 9.5pt;
        }}
        th {{
            background: #f8fafc;
            font-weight: bold;
            padding: 6px 8px;
            border: 1px solid #000;
            text-align: left;
        }}
        th.center {{
            text-align: center;
        }}
        .sign-box {{
            text-align: right;
            margin-top: 25px;
            margin-bottom: 25px;
            font-size: 10.5pt;
        }}
        .copy-block {{
            margin-top: 15px;
            font-size: 9.5pt;
            line-height: 1.4;
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
        <div>No. 1890 - AR&AH/AD/O/ 3A- 16/2026</div>
        <div>Date: 12.09.2026</div>
    </div>

    <div class="title-notification">NOTIFICATION</div>

    <div class="preamble">
        The Governor is pleased to order the promotion, placement, and transfer of the following officers of the West Bengal Animal Husbandry & Veterinary Service in the interest of public service, with immediate effect and until further orders, as detailed below:
    </div>

    <div class="sched-title">Schedule I: Promotion to the post of Deputy Director, ARD (Pay Level 19)</div>
    <table>
        <thead>
            <tr>
                <th class="center" style="width: 6%;">Sl no.</th>
                <th style="width: 38%;">Name of the Officers with Present posting</th>
                <th style="width: 34%;">Place of posting on promotion / Transfer (Substantive post)</th>
                <th style="width: 22%;">Service Utilized post (if any)</th>
            </tr>
        </thead>
        <tbody>
            {render_table_rows(roster_rows, "roster")}
        </tbody>
    </table>

    <div class="sched-title">Schedule II: Rehabilitation and Posting of Serving Officers from Abolished / Restructured Posts</div>
    <table>
        <thead>
            <tr>
                <th class="center" style="width: 6%;">Sl no.</th>
                <th style="width: 38%;">Name of the Officers with Present posting</th>
                <th style="width: 34%;">Place of posting on promotion / Transfer (Substantive post)</th>
                <th style="width: 22%;">Service Utilized post (if any)</th>
            </tr>
        </thead>
        <tbody>
            {render_table_rows(oblit_rows, "oblit")}
        </tbody>
    </table>

    <div class="sched-title">Schedule III: Consequential Lateral Transfers & Inter-District Field Postings</div>
    <table>
        <thead>
            <tr>
                <th class="center" style="width: 6%;">Sl no.</th>
                <th style="width: 38%;">Name of the Officers with Present posting</th>
                <th style="width: 34%;">Place of posting on promotion / Transfer (Substantive post)</th>
                <th style="width: 22%;">Service Utilized post (if any)</th>
            </tr>
        </thead>
        <tbody>
            {render_table_rows(lateral_rows, "lateral")}
        </tbody>
    </table>

    <div style="font-style: italic; margin-bottom: 20px;">
        This appointment / transfer is made in the interest of public service.
    </div>

    <div class="sign-box">
        By the order of the Governor,<br><br><br>
        <strong>Sd/-</strong><br>
        Special Secretary<br>
        to the Government of West Bengal
    </div>

    <div class="memo-bar" style="border-top: 1px solid #000; padding-top: 12px;">
        <div>No. 1890 / 1(15) - AR&AH/AD/O/ 3A- 16/2026</div>
        <div>Date: 12.09.2026</div>
    </div>

    <div class="copy-block">
        <strong>Copy forwarded for information and necessary action to:</strong><br>
        1. The Principal Accountant General (A&E), West Bengal, Treasury Buildings, Kolkata - 700 001.<br>
        2. The Accountant General (Audit), West Bengal, Treasury Buildings, Kolkata - 700 001.<br>
        3. The Pay & Accounts Officer, Kolkata Pay & Accounts Office - III, Subhanna, Salt Lake, Kolkata - 700 064.<br>
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

    <div class="sign-box" style="margin-top: 30px;">
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
