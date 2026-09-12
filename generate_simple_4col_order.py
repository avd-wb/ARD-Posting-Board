#!/usr/bin/env python3
"""
generate_simple_4col_order.py
Generates the official Government of West Bengal Secretariat Notification Order
strictly using the exact 4-column, black-line border table requested by the user:
- Col 1: Sl no.
- Col 2: Name of the Officers with Present posting
- Col 3: Place of posting on promotion / Transfer (Substantive post)
- Col 4: Service Utilized post (if any)

Format: Very simple, to the point, easy to understand, only black line border table,
no extra references, no extra descriptions etc.
"""

import sqlite3
import os
import re
import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DB_PATH = 'ard_master_truth.db'
EMBLEM_PATH = 'wb_state_emblem.png'

def set_table_black_borders(table):
    tblPr = table._tbl.tblPr
    borders_xml = parse_xml(
        r'<w:tblBorders %s>'
        r'  <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        r'  <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        r'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        r'  <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>'
        r'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        r'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        r'</w:tblBorders>' % nsdecls('w')
    )
    tblPr.append(borders_xml)

def set_cell_margins(cell, top=80, bottom=80, left=110, right=110):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def clean_pres(name, pres):
    if not pres: return name
    # Clean up redundant strings and title-case
    pres = re.sub(r'DEPUTY DIRECTOR,?\s*ARD\s*&\s*PARISHAD OFFICER,?\s*', 'District Office, ', pres, flags=re.I)
    pres = re.sub(r'JOINT DIRECTOR,?\s*ARD,?\s*', 'District Office, ', pres, flags=re.I)
    pres = re.sub(r'Block Live Stock Development Officer', 'BLDO', pres, flags=re.I)
    pres = re.sub(r'Block Livestock Development Officer', 'BLDO', pres, flags=re.I)
    pres = re.sub(r'Veterinary Officer', 'VO', pres, flags=re.I)
    pres = re.sub(r'Assistant Director of Animal Resources Development', 'AD, ARD', pres, flags=re.I)
    pres = re.sub(r'Assistant Director,?\s*ARD', 'AD, ARD', pres, flags=re.I)
    pres = re.sub(r'INSTITUTE OF ANIMAL HEALTH & VETERINARY BIOLOGICALS & REGIONAL DISEASE DIAGNOSTIC LABORATORY', 'IAH&VB, Belgachia, Kolkata', pres, flags=re.I)
    pres = re.sub(r'DIRECTORATE OF AR&AH', 'Directorate HQ, Salt Lake, Kolkata', pres, flags=re.I)
    pres = re.sub(r'\s+', ' ', pres).strip()
    return f"{name}, {pres}"

def clean_sub(s):
    if not s: return 'Deputy Director, ARD'
    s = re.sub(r'^DD Sl \d+:\s*', '', s)
    s = re.sub(r'\(O/O the JD ARD,\s*([^)]+)\)', r'(\1)', s)
    s = re.sub(r'\(O/O the Joint Director, ARD,\s*([^)]+)\)', r'(\1)', s)
    s = re.sub(r'\(I\.A\.H\. & V\.B\., \(R\. & T\.\),\s*[^)]+\)', '(IAH&VB, Belgachia, Kolkata)', s)
    s = re.sub(r'\(I\.A\.H\. & V\.B\.,\s*\(R\. & T\.\)\)', '(IAH&VB, Belgachia, Kolkata)', s)
    s = re.sub(r'Promoted to\s*', '', s)
    s = re.sub(r'Rehabilitated to\s*', '', s)
    s = re.sub(r'\(District Office,\s*([^)]+)\)', r'(\1)', s)
    s = re.sub(r'\(([A-Za-z\s]+),\s*\1\)', r'(\1)', s)
    s = re.sub(r'\(Directorate Headquarters,\s*Directorate Headquarters\)', '(Directorate HQ, Salt Lake, Kolkata)', s)
    s = re.sub(r'\(Directorate Headquarters\)', '(Directorate HQ, Salt Lake, Kolkata)', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def clean_su(s):
    if not s or s.strip().lower() in ['none', 'null', '']: return 'Nil'
    s = re.sub(r'^\[SU\]\s*', '', s)
    s = re.sub(r'\(Post \d+\)', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s if s else 'Nil'

def build_order():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    doc = Document()

    # Standard A4 page layout (8.27 x 11.69 in, 0.6 in margins)
    for s in doc.sections:
        s.page_width = Inches(8.27)
        s.page_height = Inches(11.69)
        s.top_margin = Inches(0.6)
        s.bottom_margin = Inches(0.6)
        s.left_margin = Inches(0.6)
        s.right_margin = Inches(0.6)

    # 1. State Emblem
    if os.path.exists(EMBLEM_PATH):
        p_emb = doc.add_paragraph()
        p_emb.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_emb.paragraph_format.space_after = Pt(2)
        r_emb = p_emb.add_run()
        r_emb.add_picture(EMBLEM_PATH, width=Inches(0.65))

    # 2. Masthead
    p_hdr = doc.add_paragraph()
    p_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_hdr.paragraph_format.space_after = Pt(6)
    p_hdr.paragraph_format.line_spacing = 1.15

    r = p_hdr.add_run("Government of West Bengal\n")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)

    r = p_hdr.add_run("Animal Resources Development Department\n")
    r.bold = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)

    r = p_hdr.add_run("AR&AH Branch, Prani Sampad Bhawan, LB-2, Sector-III, Salt Lake, Kolkata - 700 106")
    r.bold = False
    r.font.name = "Times New Roman"
    r.font.size = Pt(10)

    # 3. Notification Dispatch No. & Date
    p_disp = doc.add_paragraph()
    p_disp.paragraph_format.space_before = Pt(4)
    p_disp.paragraph_format.space_after = Pt(8)
    r1 = p_disp.add_run("No. 1890 - AR&AH/AD/O/ 3A- 16/2026")
    r1.bold = True
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(10)

    r2 = p_disp.add_run("\t\t\t\t\tDate: 12.09.2026")
    r2.bold = True
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(10)

    # 4. Title & Preamble
    p_not = doc.add_paragraph()
    p_not.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_not.paragraph_format.space_after = Pt(6)
    r_not = p_not.add_run("NOTIFICATION")
    r_not.bold = True
    r_not.font.name = "Times New Roman"
    r_not.font.size = Pt(12)

    p_pre = doc.add_paragraph()
    p_pre.paragraph_format.line_spacing = 1.15
    p_pre.paragraph_format.space_after = Pt(10)
    p_pre.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_pre = p_pre.add_run(
        "The Governor is pleased to order the promotion, placement, and transfer of the following officers "
        "of the West Bengal Animal Husbandry & Veterinary Service in the interest of public service, with immediate effect "
        "and until further orders, as detailed below:"
    )
    r_pre.font.name = "Times New Roman"
    r_pre.font.size = Pt(10)

    col_widths = [Inches(0.55), Inches(2.6), Inches(2.2), Inches(1.72)]
    headers = [
        "Sl no.",
        "Name of the Officers with Present posting",
        "Place of posting on promotion / Transfer (Substantive post)",
        "Service Utilized post (if any)"
    ]

    def add_table_header(table):
        hdr_cells = table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].width = col_widths[i]
            set_cell_margins(hdr_cells[i], top=80, bottom=80, left=100, right=100)
            p = hdr_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(h)
            run.bold = True
            run.font.name = "Times New Roman"
            run.font.size = Pt(9.5)

    def add_row(table, sl_str, col2_str, col3_str, col4_str, is_manual=True):
        row = table.add_row()
        cells = row.cells
        
        # Col 1: Sl no.
        cells[0].width = col_widths[0]
        set_cell_margins(cells[0])
        p0 = cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(sl_str)
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(9)
        r0.bold = True

        # Col 2: Name of the Officers with Present posting
        cells[1].width = col_widths[1]
        set_cell_margins(cells[1])
        p1 = cells[1].paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r1 = p1.add_run(col2_str)
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(9)

        # Col 3: Place of posting on promotion / Transfer (Substantive post)
        cells[2].width = col_widths[2]
        set_cell_margins(cells[2])
        p2 = cells[2].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r2 = p2.add_run(col3_str)
        r2.font.name = "Times New Roman"
        r2.font.size = Pt(9)

        # Col 4: Service Utilized post (if any)
        cells[3].width = col_widths[3]
        set_cell_margins(cells[3])
        p3 = cells[3].paragraphs[0]
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER if col4_str == 'Nil' else WD_ALIGN_PARAGRAPH.LEFT
        r3 = p3.add_run(col4_str)
        r3.font.name = "Times New Roman"
        r3.font.size = Pt(9)
        if col4_str != 'Nil':
            r3.bold = True

        # "whatever posts not recommended manually and you have recommended -> just make those with very light grey background colour."
        if not is_manual:
            for c in cells:
                shd = parse_xml(r'<w:shd {} w:fill="F1F5F9"/>'.format(nsdecls('w')))
                c._tc.get_or_add_tcPr().append(shd)

    # =========================================================================
    # PART 1: PROMOTION TO DEPUTY DIRECTOR, ARD (242 Promotees)
    # =========================================================================
    p_t1 = doc.add_paragraph()
    p_t1.paragraph_format.space_before = Pt(8)
    p_t1.paragraph_format.space_after = Pt(4)
    r_t1 = p_t1.add_run("Schedule I: Promotion to the post of Deputy Director, ARD (Pay Level 19)")
    r_t1.bold = True
    r_t1.font.name = "Times New Roman"
    r_t1.font.size = Pt(11)

    table1 = doc.add_table(rows=1, cols=4)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    table1.autofit = False
    set_table_black_borders(table1)
    add_table_header(table1)

    cur.execute("""
        SELECT sl_no, officer_name, present_posting, substantive_post_name, su_post_name, is_manual_recommendation
        FROM roster_50_point_candidates
        ORDER BY sl_no ASC
    """)
    roster_rows = cur.fetchall()
    for r in roster_rows:
        sl_s = str(r['sl_no'])
        c2 = clean_pres(r['officer_name'], r['present_posting'])
        c3 = clean_sub(r['substantive_post_name'])
        c4 = clean_su(r['su_post_name'])
        is_m = bool(r['is_manual_recommendation'])
        add_row(table1, sl_s, c2, c3, c4, is_manual=is_m)

    # =========================================================================
    # PART 2: REHABILITATION OF SERVING OFFICERS FROM ABOLISHED POSTS (61 Officers)
    # =========================================================================
    p_t2 = doc.add_paragraph()
    p_t2.paragraph_format.space_before = Pt(14)
    p_t2.paragraph_format.space_after = Pt(4)
    r_t2 = p_t2.add_run("Schedule II: Rehabilitation and Posting of Serving Officers from Abolished / Restructured Posts")
    r_t2.bold = True
    r_t2.font.name = "Times New Roman"
    r_t2.font.size = Pt(11)

    table2 = doc.add_table(rows=1, cols=4)
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    table2.autofit = False
    set_table_black_borders(table2)
    add_table_header(table2)

    cur.execute("""
        SELECT oblit_sl, officer_name, post_name, district, establishment, substantive_post_name, su_post_name, is_manual_recommendation
        FROM obliterated_posts_1808
        WHERE is_vacant = 'No' AND (is_on_roster = 0 OR is_on_roster IS NULL)
        ORDER BY oblit_sl ASC
    """)
    oblit_rows = cur.fetchall()
    for idx, r in enumerate(oblit_rows, 1):
        sl_s = str(idx)
        pres_str = f"{r['post_name']}, {r['establishment'] or r['district']}"
        c2 = clean_pres(r['officer_name'], pres_str)
        c3 = clean_sub(r['substantive_post_name'])
        c4 = clean_su(r['su_post_name'])
        is_m = bool(r['is_manual_recommendation'])
        add_row(table2, sl_s, c2, c3, c4, is_manual=is_m)

    # =========================================================================
    # PART 3: CONSEQUENTIAL LATERAL & FIELD TRANSFERS
    # =========================================================================
    p_t3 = doc.add_paragraph()
    p_t3.paragraph_format.space_before = Pt(14)
    p_t3.paragraph_format.space_after = Pt(4)
    r_t3 = p_t3.add_run("Schedule III: Consequential Lateral Transfers & Inter-District Field Postings")
    r_t3.bold = True
    r_t3.font.name = "Times New Roman"
    r_t3.font.size = Pt(11)

    table3 = doc.add_table(rows=1, cols=4)
    table3.alignment = WD_TABLE_ALIGNMENT.CENTER
    table3.autofit = False
    set_table_black_borders(table3)
    add_table_header(table3)

    cur.execute("""
        SELECT sl_no, officer_name, present_posting, transferred_post_name, reason_notes, is_manual_recommendation
        FROM executive_lateral_transfers
        ORDER BY sl_no ASC
    """)
    lat_rows = cur.fetchall()
    for r in lat_rows:
        sl_s = str(r['sl_no'])
        c2 = clean_pres(r['officer_name'], r['present_posting'])
        c3 = clean_sub(r['transferred_post_name'])
        c4 = clean_su(r['reason_notes'])
        is_m = bool(r['is_manual_recommendation'])
        add_row(table3, sl_s, c2, c3, c4, is_manual=is_m)

    # 5. Signatures & Distribution
    p_close = doc.add_paragraph()
    p_close.paragraph_format.space_before = Pt(14)
    p_close.paragraph_format.space_after = Pt(20)
    r_cl = p_close.add_run("By order of the Governor,\n\n\nSd/-\nSpecial Secretary to the Government of West Bengal")
    r_cl.font.name = "Times New Roman"
    r_cl.font.size = Pt(10.5)
    r_cl.bold = True
    p_close.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    p_memo = doc.add_paragraph()
    p_memo.paragraph_format.space_before = Pt(8)
    p_memo.paragraph_format.space_after = Pt(4)
    r_m = p_memo.add_run("No. 1890 / 1(15) - AR&AH/AD/O/ 3A- 16/2026\t\t\t\t\tDate: 12.09.2026")
    r_m.font.name = "Times New Roman"
    r_m.font.size = Pt(10)
    r_m.bold = True

    p_cp = doc.add_paragraph()
    p_cp.paragraph_format.space_after = Pt(4)
    r_cp = p_cp.add_run("Copy forwarded for information and necessary action to:")
    r_cp.font.name = "Times New Roman"
    r_cp.font.size = Pt(10)
    r_cp.bold = True

    copy_items = [
        "The Principal Accountant General (A&E), West Bengal, Treasury Buildings, Kolkata - 700 001.",
        "The Director of AH & VS, West Bengal with request to circulate among controlling offices.",
        "The Chief Executive Officer, PBGSBS, LB-2, Sector-III, Salt Lake, Kolkata - 700 106.",
        "The Managing Director, WBLDCL, Salt Lake, Kolkata - 700 106.",
        "All Joint Directors, ARD / Deputy Directors, ARD & PO of all Districts.",
        "The Treasury Officer, concerned Treasuries.",
        "The Pay & Accounts Officer, Kolkata Pay & Accounts Office-I / II / III.",
        "PS to Hon'ble Minister-in-Charge, Animal Resources Development Department.",
        "Sr. PS to Additional Chief Secretary, Animal Resources Development Department.",
        "Officers concerned for immediate compliance.",
        "Guard File / Office Copy."
    ]

    for idx, item in enumerate(copy_items, 1):
        p_it = doc.add_paragraph()
        p_it.paragraph_format.left_indent = Inches(0.25)
        p_it.paragraph_format.space_after = Pt(1)
        p_it.paragraph_format.line_spacing = 1.1
        r_it = p_it.add_run(f"{idx}. {item}")
        r_it.font.name = "Times New Roman"
        r_it.font.size = Pt(9.5)

    p_end = doc.add_paragraph()
    p_end.paragraph_format.space_before = Pt(20)
    p_end.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_end = p_end.add_run("Sd/-\nDeputy Secretary to the Government of West Bengal")
    r_end.font.name = "Times New Roman"
    r_end.font.size = Pt(10.5)
    r_end.bold = True

    now = datetime.datetime.now()
    ts_date = now.strftime('%Y%m%d')
    ts_time = now.strftime('%H%M')
    
    temp_name = f"{ts_date}_{ts_time}_Transfer_and_Promotion_Order_4_Column_Format_temp.docx"
    doc.save(temp_name)
    sz_mb = os.path.getsize(temp_name) / (1024 * 1024)
    final_filename = f"{ts_date}_{ts_time}_Transfer_and_Promotion_Order_4_Column_Format_{sz_mb:.2f}MB_mb.docx"
    os.rename(temp_name, final_filename)

    conn.close()
    print(f"Generated clean 4-column order document: {final_filename}")
    print(f"File Size: {os.path.getsize(final_filename)} bytes ({sz_mb:.2f}MB)")
    return final_filename

if __name__ == '__main__':
    build_order()
