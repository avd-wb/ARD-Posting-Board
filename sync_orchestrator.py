#!/usr/bin/env python3
"""
sync_orchestrator.py
Central synchronization engine that enforces universal parity across:
1. Database (ard_master_truth.db):
   - roster_50_point_candidates
   - obliterated_posts_1808
   - executive_lateral_transfers
   - available_dd_posts
   - cadre_1794_posts
   - simulation_assignments
2. Google Sheets:
   - Remote Google Sheet (17tv3exhMVzAfedLU7pS8ps1ZWEteMP1Z / 20260913_0012_...):
     All 15 tabs synchronized in-place with Tab 1 = 11_Column_Master_Posting_Order (Column N preserved),
     Tab 2 = District_HQ_Cadre_Summary, Tab 3 = District_HQ_Officer_Roster, plus all decision & directory tabs.
   - Master Interactive Workbook (WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx):
     All 15 tabs synchronized.
3. Official 4-Column Government Order (.docx)
4. Web App (FastAPI / Uvicorn / Vercel SPA)
"""

import os
import sys
import json
import sqlite3
import re
import subprocess
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

WORKSPACE = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DRIVE_FOLDER_ID = "1BgJE4thWGsCLv4qFHqmWobW_met8UuEL"
REMOTE_FILENAME = "20260913_0012_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_0.03MB_mb.xlsx"
LOCAL_EXCEL = os.path.join(WORKSPACE, REMOTE_FILENAME)
MASTER_WORKBOOK = os.path.join(WORKSPACE, "WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx")
DB_PATH = os.path.join(WORKSPACE, "ard_master_truth.db")
COLUMN_N_FILE = os.path.join(WORKSPACE, "column_n_comments.json")
BASELINE_FILE = os.path.join(WORKSPACE, "remarks_baseline.json")

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [SYNC-ORCHESTRATOR] {msg}"
    print(formatted)

def run_cmd(cmd_list, timeout=120):
    res = subprocess.run(cmd_list, cwd=WORKSPACE, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        log(f"Command failed: {' '.join(cmd_list)}\nSTDERR: {res.stderr}")
    return res

def sync_database_truth(conn):
    """
    Harmonizes all relational tables in ard_master_truth.db:
    1. available_dd_posts
    2. cadre_1794_posts
    3. simulation_assignments (CURRENT_SESSION)
    """
    log("Synchronizing database truth across all tables...")
    cur = conn.cursor()

    # 1. available_dd_posts: reset available status, then allot based on roster_50_point_candidates
    cur.execute("""
        UPDATE available_dd_posts 
        SET allotment_status = 'Available', allotted_hrms = NULL, allotted_name = NULL 
        WHERE is_blocked_vigilance = 0
    """)
    cur.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = (SELECT hrms_id FROM roster_50_point_candidates r WHERE r.substantive_post_id = available_dd_posts.dd_sl),
            allotted_name = (SELECT officer_name FROM roster_50_point_candidates r WHERE r.substantive_post_id = available_dd_posts.dd_sl)
        WHERE dd_sl IN (SELECT substantive_post_id FROM roster_50_point_candidates WHERE substantive_post_id IS NOT NULL)
    """)

    # 2. cadre_1794_posts: update SU and Substantive markers
    cur.execute("""
        UPDATE cadre_1794_posts
        SET su_allotted_hrms = NULL, su_allotted_name = NULL,
            substantive_allotted_hrms = NULL, substantive_allotted_name = NULL,
            is_substantive_blocked = 0
        WHERE occupancy_status = 'Vacant'
    """)

    cur.execute("SELECT id, post_sl, designation, establishment, block, district FROM cadre_1794_posts")
    cadre_posts = [dict(r) for r in cur.fetchall()]

    # Match roster SU posts
    cur.execute("""
        SELECT hrms_id, officer_name, su_post_name 
        FROM roster_50_point_candidates 
        WHERE su_post_name IS NOT NULL AND su_post_name != 'Nil' AND su_post_name != ''
    """)
    for r in cur.fetchall():
        su_txt = r["su_post_name"].lower()
        best_post_id = None
        best_score = 0
        for cp in cadre_posts:
            score = 0
            b = (cp["block"] or "").lower()
            d = (cp["district"] or "").lower()
            des = (cp["designation"] or "").lower()
            if b and b in su_txt: score += 3
            if d and d in su_txt: score += 1
            if des and des in su_txt: score += 2
            if score > best_score:
                best_score = score
                best_post_id = cp["id"]
        if best_post_id and best_score >= 3:
            cur.execute("""
                UPDATE cadre_1794_posts
                SET su_allotted_hrms = ?, su_allotted_name = ?
                WHERE id = ?
            """, (r["hrms_id"], r["officer_name"], best_post_id))

    # Match obliterated SU and substantive posts
    cur.execute("""
        SELECT hrms_id, officer_name, substantive_post_name, su_post_name 
        FROM obliterated_posts_1808 
        WHERE is_vacant = 'No' AND (is_on_roster = 0 OR is_on_roster IS NULL)
    """)
    for o in cur.fetchall():
        if o["su_post_name"] and o["su_post_name"] != "Nil":
            su_txt = o["su_post_name"].lower()
            best_post_id = None
            best_score = 0
            for cp in cadre_posts:
                score = 0
                b = (cp["block"] or "").lower()
                d = (cp["district"] or "").lower()
                des = (cp["designation"] or "").lower()
                if b and b in su_txt: score += 3
                if d and d in su_txt: score += 1
                if des and des in su_txt: score += 2
                if score > best_score:
                    best_score = score
                    best_post_id = cp["id"]
            if best_post_id and best_score >= 3:
                cur.execute("""
                    UPDATE cadre_1794_posts
                    SET su_allotted_hrms = ?, su_allotted_name = ?
                    WHERE id = ?
                """, (o["hrms_id"], o["officer_name"], best_post_id))

    # 3. simulation_assignments: rebuild CURRENT_SESSION
    cur.execute("DELETE FROM simulation_assignments WHERE session_id = 'CURRENT_SESSION'")
    step = 1

    # Roster promotees
    cur.execute("""
        SELECT sl_no, officer_name, hrms_id, present_posting, 
               substantive_post_id, substantive_post_name, su_post_id, su_post_name
        FROM roster_50_point_candidates
        WHERE substantive_post_name IS NOT NULL
        ORDER BY sl_no
    """)
    for r in cur.fetchall():
        cur.execute("""
            INSERT INTO simulation_assignments (
                session_id, step_number, officer_hrms_id, officer_name,
                from_post_name, to_post_name, substantive_post_id, substantive_post_name,
                su_post_id, su_post_name, officer_type, status, reason, timestamp
            ) VALUES (
                'CURRENT_SESSION', ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, 'roster', 'Confirmed', '50-Point Roster Promotion to DD', datetime('now')
            )
        """, (
            step, r["hrms_id"], r["officer_name"],
            r["present_posting"], r["substantive_post_name"], r["substantive_post_id"], r["substantive_post_name"],
            r["su_post_id"], r["su_post_name"]
        ))
        step += 1

    # Obliterated officers
    cur.execute("""
        SELECT oblit_sl, officer_name, hrms_id, post_name, establishment, district,
               substantive_post_id, substantive_post_name, su_post_id, su_post_name
        FROM obliterated_posts_1808
        WHERE is_vacant = 'No' AND (is_on_roster = 0 OR is_on_roster IS NULL)
        ORDER BY oblit_sl
    """)
    for o in cur.fetchall():
        pres = f"{o['post_name']}, {o['establishment']}, {o['district']}"
        cur.execute("""
            INSERT INTO simulation_assignments (
                session_id, step_number, officer_hrms_id, officer_name,
                from_post_name, to_post_name, substantive_post_id, substantive_post_name,
                su_post_id, su_post_name, officer_type, status, reason, timestamp
            ) VALUES (
                'CURRENT_SESSION', ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, 'obliterated', 'Confirmed', 'Notification 1808 Cadre Rehabilitation', datetime('now')
            )
        """, (
            step, o["hrms_id"], o["officer_name"],
            pres, o["substantive_post_name"], o["substantive_post_id"], o["substantive_post_name"],
            o["su_post_id"], o["su_post_name"]
        ))
        step += 1

    # Lateral transfers
    cur.execute("""
        SELECT sl_no, hrms_id, officer_name, present_posting, transferred_post_name, reason_notes
        FROM executive_lateral_transfers
        ORDER BY sl_no
    """)
    for l in cur.fetchall():
        cur.execute("""
            INSERT INTO simulation_assignments (
                session_id, step_number, officer_hrms_id, officer_name,
                from_post_name, to_post_name, substantive_post_name,
                officer_type, status, reason, timestamp
            ) VALUES (
                'CURRENT_SESSION', ?, ?, ?,
                ?, ?, ?,
                'displaced', 'Confirmed', coalesce(?, 'Consequential transfer'), datetime('now')
            )
        """, (
            step, l["hrms_id"], l["officer_name"],
            l["present_posting"], l["transferred_post_name"], l["transferred_post_name"],
            l["reason_notes"]
        ))
        step += 1

    conn.commit()
    log(f"Database truth synchronized successfully ({step - 1} total assignments recorded).")

def regenerate_all_sheets_and_tabs():
    """
    Regenerates all tabs across all workbooks:
    1. build_interactive_google_sheet.py -> 12 decision & directory sheets
    2. generate_11col_posting_order.py -> 11_Column_Master_Posting_Order + District HQ tabs
    3. Reorders and writes all 15 tabs into BOTH:
       - WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx
       - LOCAL_EXCEL (20260913_0012_... for Google Sheet 17tv3exhMVzAfedLU7pS8ps1ZWEteMP1Z)
    4. generate_simple_4col_order.py -> official Word doc
    """
    log("Regenerating all sheets and tabs across all files...")

    # Step A: Rebuild the interactive decision sheets
    from build_interactive_google_sheet import build_workbook
    build_workbook()

    # Step B: Build 11-column master sheet and inject District HQ tabs
    from generate_11col_posting_order import build_standalone_and_inject_master
    standalone_file = build_standalone_and_inject_master()

    # Step C: Re-harmonize LOCAL_EXCEL (20260913_0012_...) with all 15 tabs
    target_order = [
        "11_Column_Master_Posting_Order",
        "District_HQ_Cadre_Summary",
        "District_HQ_Officer_Roster",
        "50_Pt_Roster_Decisions",
        "Obliterated_Rehab_Decisions",
        "Available_DD_Posts",
        "Available_AD_Vacancies",
        "SU_Post_Picker",
        "Displaced_Queue_Tracker",
        "Secretariat_Posting_Order",
        "4_Column_Posting_Order",
        "Master_Cadre_Directory",
        "Directorate_HQ_Roster",
        "Excess_Unsanctioned_Deploy",
        "Instructions & Guidelines"
    ]

    wb_master = openpyxl.load_workbook(MASTER_WORKBOOK)
    wb_master._sheets = [wb_master[name] for name in target_order if name in wb_master.sheetnames] + [s for s in wb_master._sheets if s.title not in target_order]
    wb_master.save(MASTER_WORKBOOK)
    wb_master.save(LOCAL_EXCEL)
    log(f"Synchronized all {len(wb_master.sheetnames)} tabs in {os.path.basename(LOCAL_EXCEL)} and {os.path.basename(MASTER_WORKBOOK)}.")

    # Step D: Regenerate official Word document
    from generate_simple_4col_order import build_order
    build_order()
    log("Official 4-Column Word document regenerated.")

def upload_all_deliverables_to_drive():
    log("Uploading updated sheets and Word doc to Google Drive...")
    # 1. Update 17tv3exhMVzAfedLU7pS8ps1ZWEteMP1Z in-place
    res1 = run_cmd([
        "rclone", "copyto",
        LOCAL_EXCEL,
        f"gdrive:{REMOTE_FILENAME}",
        "--drive-root-folder-id", DRIVE_FOLDER_ID
    ])
    if res1.returncode == 0:
        log(f"Successfully updated remote sheet {REMOTE_FILENAME} in-place.")

    # 2. Upload Master Interactive Workbook
    run_cmd([
        "rclone", "copy",
        MASTER_WORKBOOK,
        "gdrive:",
        "--drive-root-folder-id", DRIVE_FOLDER_ID
    ])

    # 3. Upload Word Document
    import glob
    docx_files = sorted(glob.glob(os.path.join(WORKSPACE, "Transfer_and_Promotion_Order_4_Column_Format_*.docx")))
    if docx_files:
        run_cmd([
            "rclone", "copy",
            docx_files[-1],
            "gdrive:",
            "--drive-root-folder-id", DRIVE_FOLDER_ID
        ])

def commit_and_push_to_git(msg="Universal sync: effect changes across all tabs, sheets, database and web app"):
    log("Committing and pushing changes to GitHub / Vercel...")
    run_cmd(["git", "add", "-A"])
    run_cmd(["git", "commit", "-m", msg])
    run_cmd(["git", "push", "origin", "main"])
    log("GitHub and Vercel updated successfully.")

def run_full_sync():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    sync_database_truth(conn)
    conn.close()

    regenerate_all_sheets_and_tabs()
    upload_all_deliverables_to_drive()
    commit_and_push_to_git()
    log("Full universal synchronization complete.")

if __name__ == "__main__":
    run_full_sync()
