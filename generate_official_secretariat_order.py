#!/usr/bin/env python3
"""
generate_official_secretariat_order.py
Generates the official Government of West Bengal Secretariat Notification Order
strictly matching the typography, structure, styling, crest, preamble, tables,
signature blocks, and copy-forwarded list of Reference Order 20260211.
"""

import sqlite3
import os
import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DB_PATH = 'ard_master_truth.db'
EMBLEM_PATH = 'wb_state_emblem.png'

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_background(cell, fill_hex):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def format_cell_text(cell, bold_text, normal_text="", text_color=RGBColor(30, 41, 59), font_size=Pt(9.5)):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    
    if bold_text:
        run_b = p.add_run(bold_text)
        run_b.bold = True
        run_b.font.name = "Times New Roman"
        run_b.font.size = font_size
        run_b.font.color.rgb = text_color

    if normal_text:
        if bold_text and not bold_text.endswith("\n") and not normal_text.startswith("\n"):
            p.add_run("\n")
        run_n = p.add_run(normal_text)
        run_n.bold = False
        run_n.font.name = "Times New Roman"
        run_n.font.size = font_size
        run_n.font.color.rgb = text_color

def create_order():
    doc = Document()

    # Set page setup - Standard A4, 0.75 in margins
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # 1. State Emblem
    if os.path.exists(EMBLEM_PATH):
        p_emb = doc.add_paragraph()
        p_emb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_emb.paragraph_format.space_after = Pt(2)
        run_emb = p_emb.add_run()
        run_emb.add_picture(EMBLEM_PATH, width=Inches(0.75))

    # 2. Secretariat Masthead
    p_hdr = doc.add_paragraph()
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_hdr.paragraph_format.space_after = Pt(12)
    p_hdr.paragraph_format.line_spacing = 1.15

    r = p_hdr.add_run("Government of West Bengal\n")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(13)

    r = p_hdr.add_run("Animal Resources Development Department\n")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    r = p_hdr.add_run("AR&AH Branch, Prani Sampad Bhawan, LB-2, Sector-III,\nSalt Lake, Kolkata - 700 106")
    r.bold = False
    r.font.name = "Times New Roman"
    r.font.size = Pt(10.5)

    # 3. Notification Dispatch No. and Date
    p_disp = doc.add_paragraph()
    p_disp.paragraph_format.space_before = Pt(6)
    p_disp.paragraph_format.space_after = Pt(10)
    
    r_no = p_disp.add_run("No. 1890 - AR&AH/AD/O/ 3A- 16/2026")
    r_no.bold = True
    r_no.font.name = "Times New Roman"
    r_no.font.size = Pt(10.5)
    
    # Tab to right for Date
    r_no_tab = p_disp.add_run("\t\t\t\t\t\tDate: 12.09.2026")
    r_no_tab.bold = True
    r_no_tab.font.name = "Times New Roman"
    r_no_tab.font.size = Pt(10.5)

    # 4. Heading: NOTIFICATION
    p_notif = doc.add_paragraph()
    p_notif.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_notif.paragraph_format.space_before = Pt(4)
    p_notif.paragraph_format.space_after = Pt(12)
    r_notif = p_notif.add_run("NOTIFICATION")
    r_notif.bold = True
    r_notif.underline = True
    r_notif.font.name = "Times New Roman"
    r_notif.font.size = Pt(13)

    # 5. Statutory Preamble
    p_pre = doc.add_paragraph()
    p_pre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_pre.paragraph_format.space_after = Pt(12)
    p_pre.paragraph_format.line_spacing = 1.2
    
    preamble_text = (
        "The Governor is pleased to appoint the following 242 (two hundred and forty-two) Assistant Directors / "
        "Veterinary Officers, Animal Resources Development borne under the West Bengal Animal Husbandry & Veterinary Service "
        "on promotion to the post of Deputy Director, Animal Resources Development in the Pay Level 19 (Rs. 95,100 - Rs. 1,48,000/-) "
        "under WBS (ROPA) Rules, 2019 and allowances as admissible from time to time under the said Rules with effect from the date "
        "of their taking over charge of the post of Deputy Director under the Directorate of Animal Resources & Animal Health, "
        "regularize and rehabilitate 84 (eighty-four) serving officers holding posts abolished under Notification No. 1808, "
        "and order consequential lateral transfers and placements of service in public interest. "
        "Their places of posting on promotion, rehabilitation, and transfer are mentioned below:"
    )
    r_pre = p_pre.add_run(preamble_text)
    r_pre.font.name = "Times New Roman"
    r_pre.font.size = Pt(11)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # =========================================================================
    # SCHEDULE I: 242 PROMOTEES TO DEPUTY DIRECTOR (PAY LEVEL 19)
    # =========================================================================
    p_s1 = doc.add_paragraph()
    p_s1.paragraph_format.space_before = Pt(14)
    p_s1.paragraph_format.space_after = Pt(6)
    r_s1 = p_s1.add_run("Schedule I: Promotion to the Post of Deputy Director, ARD (Pay Level 19)")
    r_s1.bold = True
    r_s1.font.name = "Times New Roman"
    r_s1.font.size = Pt(11.5)

    cur.execute("""
        SELECT sl_no, roster_point, point_reserved_for, officer_name, hrms_id, caste,
               present_posting, present_block, present_district, substantive_post_name, su_post_name
        FROM roster_50_point_candidates
        ORDER BY sl_no ASC
    """)
    roster_list = cur.fetchall()

    table1 = doc.add_table(rows=1, cols=3)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    table1.autofit = False

    # Header
    col_widths = [Inches(0.6), Inches(3.1), Inches(3.3)]
    headers = ["Sl. No.", "Name of the Officers with Present posting", "Place of posting on promotion"]
    
    hdr_cells = table1.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].width = col_widths[i]
        set_cell_background(hdr_cells[i], "1E3A8A")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(255, 255, 255)

    for idx, r in enumerate(roster_list):
        row = table1.add_row()
        cells = row.cells
        
        # Col 0: Sl. No.
        cells[0].width = col_widths[0]
        set_cell_margins(cells[0])
        p0 = cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(r["sl_no"]))
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(9.5)
        r0.bold = True

        # Col 1: Officer Name & Present Posting
        cells[1].width = col_widths[1]
        set_cell_margins(cells[1])
        name_line = f"{r['officer_name']}, {r['present_posting'] or 'Assistant Director / VO'}"
        sub_info = f"HRMS: {r['hrms_id']} | District: {r['present_district'] or 'HQ'}"
        format_cell_text(cells[1], name_line, sub_info)

        # Col 2: Place of Posting on Promotion
        cells[2].width = col_widths[2]
        set_cell_margins(cells[2])
        post_line = r["substantive_post_name"] or "Deputy Director, ARD"
        su_info = ""
        if r["su_post_name"]:
            su_info = f"Service Utilized Condition: {r['su_post_name']}. He/She will also act as in situ until further order."
        else:
            su_info = "He/She will act as Deputy Director until further order."
        format_cell_text(cells[2], post_line, su_info)

        # Soft alternating row shading
        if idx % 2 == 1:
            set_cell_background(cells[0], "F8FAFC")
            set_cell_background(cells[1], "F8FAFC")
            set_cell_background(cells[2], "F8FAFC")

    # =========================================================================
    # SCHEDULE II: REHABILITATION OF 84 SERVING OBLITERATED POST OFFICERS
    # =========================================================================
    p_s2 = doc.add_paragraph()
    p_s2.paragraph_format.space_before = Pt(18)
    p_s2.paragraph_format.space_after = Pt(6)
    r_s2 = p_s2.add_run("Schedule II: Rehabilitation and Regularization of Officers Holding Abolished Posts (Notification No. 1808)")
    r_s2.bold = True
    r_s2.font.name = "Times New Roman"
    r_s2.font.size = Pt(11.5)

    cur.execute("""
        SELECT oblit_sl, district, block, establishment, post_name, officer_name, hrms_id, substantive_post_name
        FROM obliterated_posts_1808
        WHERE is_vacant = 'No'
        ORDER BY oblit_sl ASC
    """)
    oblit_list = cur.fetchall()

    table2 = doc.add_table(rows=1, cols=3)
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    table2.autofit = False

    hdr_cells2 = table2.rows[0].cells
    headers2 = ["Sl. No.", "Name of Officer & Abolished Post (Memo 1808)", "Rehabilitated Active Cadre Posting / Assignment"]
    for i, h in enumerate(headers2):
        hdr_cells2[i].width = col_widths[i]
        set_cell_background(hdr_cells2[i], "1E3A8A")
        set_cell_margins(hdr_cells2[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells2[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(255, 255, 255)

    for idx, r in enumerate(oblit_list):
        row = table2.add_row()
        cells = row.cells

        cells[0].width = col_widths[0]
        set_cell_margins(cells[0])
        p0 = cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(r["oblit_sl"]))
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(9.5)
        r0.bold = True

        cells[1].width = col_widths[1]
        set_cell_margins(cells[1])
        name_line = f"{r['officer_name']} (HRMS: {r['hrms_id']})"
        old_post = f"Abolished Post: {r['post_name']}, {r['establishment']}, {r['district']}"
        format_cell_text(cells[1], name_line, old_post)

        cells[2].width = col_widths[2]
        set_cell_margins(cells[2])
        new_post = r["substantive_post_name"] or "Active Sanctioned Cadre Post"
        rehab_note = "Regularized in public interest without break in service."
        format_cell_text(cells[2], new_post, rehab_note)

        if idx % 2 == 1:
            set_cell_background(cells[0], "F8FAFC")
            set_cell_background(cells[1], "F8FAFC")
            set_cell_background(cells[2], "F8FAFC")

    # =========================================================================
    # SCHEDULE III: LATERAL TRANSFERS & CASCADING FIELD BACKFILLS
    # =========================================================================
    p_s3 = doc.add_paragraph()
    p_s3.paragraph_format.space_before = Pt(18)
    p_s3.paragraph_format.space_after = Pt(6)
    r_s3 = p_s3.add_run("Schedule III: Consequential Lateral Transfers, Reciprocal Swaps & Field Deployments")
    r_s3.bold = True
    r_s3.font.name = "Times New Roman"
    r_s3.font.size = Pt(11.5)

    table3 = doc.add_table(rows=1, cols=3)
    table3.alignment = WD_TABLE_ALIGNMENT.CENTER
    table3.autofit = False

    hdr_cells3 = table3.rows[0].cells
    headers3 = ["Sl. No.", "Name of Officer with HRMS & Present Post", "Executive Placement / Urgent Action"]
    for i, h in enumerate(headers3):
        hdr_cells3[i].width = col_widths[i]
        set_cell_background(hdr_cells3[i], "1E3A8A")
        set_cell_margins(hdr_cells3[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells3[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
        run = p.add_run(h)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(255, 255, 255)

    cur.execute("""
        SELECT sl_no, hrms_id, officer_name, present_posting, transferred_post_name, reason_notes
        FROM executive_lateral_transfers
        ORDER BY sl_no ASC
    """)
    lat_rows = cur.fetchall()

    for idx, r in enumerate(lat_rows):
        row = table3.add_row()
        cells = row.cells
        cells[0].width = col_widths[0]
        set_cell_margins(cells[0])
        p0 = cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(str(r["sl_no"]))
        r0.bold = True
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(9.5)

        cells[1].width = col_widths[1]
        set_cell_margins(cells[1])
        off_text = f"{r['officer_name']} ({r['hrms_id']})\n{r['present_posting']}"
        format_cell_text(cells[1], off_text)

        cells[2].width = col_widths[2]
        set_cell_margins(cells[2])
        act_text = f"{r['transferred_post_name']}\n[{r['reason_notes']}]"
        format_cell_text(cells[2], act_text)

        if idx % 2 == 1:
            set_cell_background(cells[0], "F8FAFC")
            set_cell_background(cells[1], "F8FAFC")
            set_cell_background(cells[2], "F8FAFC")

    # Add general holding charge note
    row = table3.add_row()
    cells = row.cells
    cells[0].width = col_widths[0]
    set_cell_margins(cells[0])
    p0 = cells[0].paragraphs[0]
    p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r0 = p0.add_run(str(len(lat_rows) + 1))
    r0.bold = True
    r0.font.name = "Times New Roman"
    r0.font.size = Pt(9.5)

    cells[1].width = col_widths[1]
    set_cell_margins(cells[1])
    format_cell_text(cells[1], "Vacated Field Block & Hospital Units\n(Sub-Divisional, BLDO, BAHC & SAHC Units)")

    cells[2].width = col_widths[2]
    set_cell_margins(cells[2])
    format_cell_text(cells[2], "Controlling Joint Directors to immediately assign local holding charge pending regular backfill postings.")

    if len(lat_rows) % 2 == 1:
        set_cell_background(cells[0], "F8FAFC")
        set_cell_background(cells[1], "F8FAFC")
        set_cell_background(cells[2], "F8FAFC")

    # 6. Concluding Clause
    p_close = doc.add_paragraph()
    p_close.paragraph_format.space_before = Pt(14)
    p_close.paragraph_format.space_after = Pt(14)
    r_close = p_close.add_run("This appointment is made in the interest of public service.")
    r_close.font.name = "Times New Roman"
    r_close.font.size = Pt(11)

    # 7. Signature Block
    p_sig = doc.add_paragraph()
    p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig.paragraph_format.space_after = Pt(16)
    p_sig.paragraph_format.line_spacing = 1.15
    
    r = p_sig.add_run("By the order of the Governor,\n\n\n")
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    
    r = p_sig.add_run("Sd/- B. Sikdar\n")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)

    r = p_sig.add_run("Special Secretary\nto the Government of West Bengal")
    r.font.name = "Times New Roman"
    r.font.size = Pt(10.5)

    # 8. Endorsement Memo
    p_end = doc.add_paragraph()
    p_end.paragraph_format.space_before = Pt(10)
    p_end.paragraph_format.space_after = Pt(8)
    
    r_end_no = p_end.add_run("No. 1890 / 1(15) - AR&AH/AD/O/ 3A- 16/2026")
    r_end_no.bold = True
    r_end_no.font.name = "Times New Roman"
    r_end_no.font.size = Pt(10.5)
    
    r_end_date = p_end.add_run("\t\t\t\t\t\tDate: 12.09.2026")
    r_end_date.bold = True
    r_end_date.font.name = "Times New Roman"
    r_end_date.font.size = Pt(10.5)

    # 9. Copy Forwarded List
    p_cf = doc.add_paragraph()
    p_cf.paragraph_format.space_after = Pt(4)
    r_cf = p_cf.add_run("Copy forwarded for information and necessary action to:")
    r_cf.bold = True
    r_cf.font.name = "Times New Roman"
    r_cf.font.size = Pt(10.5)

    copy_items = [
        "The Principal Accountant General (A&E), West Bengal, Treasury Building, Kolkata - 700001.",
        "The Accountant General (Audit), W.B., Treasury Buildings, Kolkata - 700001.",
        "The Pay & Accounts Officer, Kolkata Pay & Accounts Office - III, Subhanna, Salt Lake - Kolkata - 64.",
        "The Director, AH&VS, West Bengal. He is requested to forward the joining letters of all appointees to this Department.",
        "The PS to the Hon'ble Minister-in-Charge, ARD Department, Government of West Bengal.",
        "The Senior P.S. to the Additional Chief Secretary, ARD Department.",
        "The Additional Director, ARD (All Divisions / Headquarters).",
        "The Joint Director, ARD (All Districts / Zones).",
        "All Officers concerned in Schedule I, Schedule II, and Schedule III. They are directed to join their respective new assignments forthwith.",
        "All Controlling Officers / DDOs with the instruction to release the transferred officers without waiting for a substitute to ensure uninterrupted service delivery.",
        "The Managing Director, West Bengal Livestock Development Corporation Limited (WBLDCL), Salt Lake, Kolkata.",
        "The Chief Executive Officer, Paschim Banga Go-Sampad Bikash Sanstha (PBGSBS), Salt Lake, Kolkata.",
        "The Treasury Officer / Pay & Accounts Officer (All concerned).",
        "The Nodal Officer, Departmental IT Cell, with the direction to upload this Notification on the official website for wide publicity.",
        "Guard File."
    ]

    for idx, item in enumerate(copy_items, 1):
        p_item = doc.add_paragraph()
        p_item.paragraph_format.space_before = Pt(0)
        p_item.paragraph_format.space_after = Pt(2)
        p_item.paragraph_format.left_indent = Inches(0.25)
        r_item = p_item.add_run(f"{idx}. {item}")
        r_item.font.name = "Times New Roman"
        r_item.font.size = Pt(10)

    # 10. Countersignature Block
    p_csig = doc.add_paragraph()
    p_csig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_csig.paragraph_format.space_before = Pt(14)
    p_csig.paragraph_format.space_after = Pt(6)
    p_csig.paragraph_format.line_spacing = 1.15

    r = p_csig.add_run("\n\n(R. Ghosh)\n")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)

    r = p_csig.add_run("Deputy Secretary\nto the Government of West Bengal")
    r.font.name = "Times New Roman"
    r.font.size = Pt(10.5)

    conn.close()

    # Save to temp file first to determine size
    temp_path = "temp_secretariat_order.docx"
    doc.save(temp_path)
    
    file_bytes = os.path.getsize(temp_path)
    size_mb = file_bytes / (1024 * 1024)
    size_mb_str = f"{size_mb:.2f}MB"
    
    now = datetime.datetime.now()
    yyyymmdd = now.strftime("%Y%m%d")
    hhmm = now.strftime("%H%M")
    matter = "Transfer_and_Promotion_Order_242_DD_and_84_Obliterated_Rehabilitation"
    
    # Naming format: <yyyymmdd>_<hhmm>_<matter of the file>_<size in MB>_<mb>.docx
    final_filename = f"{yyyymmdd}_{hhmm}_{matter}_{size_mb_str}_mb.docx"
    os.rename(temp_path, final_filename)
    
    print(f"Generated official order document: {final_filename}")
    print(f"File Size: {file_bytes} bytes ({size_mb_str})")
    return final_filename

if __name__ == '__main__':
    create_order()
