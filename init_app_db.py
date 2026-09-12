#!/usr/bin/env python3
"""
init_app_db.py
Initializes helper tables in ard_master_truth.db:
1. roster_50_point_candidates (242 verified candidates from PROMOTION_242)
2. obliterated_post_officers (73 verified officers from abolished posts)
3. official_orders (indexed from orders_master_index.json)
4. simulation_sessions & simulation_assignments (for reactive posting engine)
"""

import os
import json
import sqlite3
import openpyxl

DB_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD_AG/ard_master_truth.db"
SOURCE_GRAD_FILE = "/Users/nirmalyaranjansarkar/Projects/AVD/03_ARD_HR/ARD_HR/02. Working Outputs/20260908 Gradation List 01092026/20260908_AVD_DDP_Gradation_List_01092026.xlsx"
ORDERS_JSON = "/Users/nirmalyaranjansarkar/Projects/AVD_AG/orders_repository/orders_master_index.json"

def init_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Roster Candidates Table
    cur.execute("DROP TABLE IF EXISTS roster_50_point_candidates")
    cur.execute("""
    CREATE TABLE roster_50_point_candidates (
        sl_no INTEGER PRIMARY KEY,
        roster_point INTEGER,
        point_reserved_for TEXT,
        officer_name TEXT,
        hrms_id TEXT,
        caste TEXT,
        present_posting TEXT,
        service_status TEXT,
        service_ends TEXT,
        avd_member TEXT,
        current_post_id INTEGER,
        current_district TEXT,
        current_designation TEXT,
        tenure_years REAL,
        is_dual_obliterated INTEGER DEFAULT 0,
        pref_1 TEXT,
        pref_2 TEXT,
        pref_3 TEXT,
        all_preferences TEXT,
        allotted_post_id INTEGER DEFAULT NULL,
        allotted_post_name TEXT DEFAULT NULL,
        allotment_status TEXT DEFAULT 'Pending',
        allotment_timestamp TEXT DEFAULT NULL
    )
    """)

    # 2. Obliterated Post Officers Table
    cur.execute("DROP TABLE IF EXISTS obliterated_post_officers")
    cur.execute("""
    CREATE TABLE obliterated_post_officers (
        id INTEGER PRIMARY KEY,
        post_id INTEGER,
        post_name TEXT,
        designation TEXT,
        establishment TEXT,
        district TEXT,
        officer_name TEXT,
        hrms_id TEXT,
        caste TEXT,
        dob TEXT,
        dor TEXT,
        tenure_years REAL,
        is_on_roster INTEGER DEFAULT 0,
        roster_rank INTEGER DEFAULT NULL,
        preferences TEXT,
        status TEXT DEFAULT 'Pending Rehabilitation',
        rehabilitated_post_id INTEGER DEFAULT NULL,
        rehabilitated_post_name TEXT DEFAULT NULL
    )
    """)

    # 3. Official Orders Table
    cur.execute("DROP TABLE IF EXISTS official_orders")
    cur.execute("""
    CREATE TABLE official_orders (
        order_index INTEGER PRIMARY KEY,
        category TEXT,
        order_date TEXT,
        order_number TEXT,
        title TEXT,
        key_officers TEXT,
        subdirectory TEXT,
        web_source_portal TEXT,
        google_drive_archive TEXT,
        referenced_file TEXT
    )
    """)

    # 4. Simulation Sessions & Assignments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS simulation_sessions (
        session_id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'ACTIVE',
        total_allotments INTEGER DEFAULT 0,
        total_collisions INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS simulation_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        step_number INTEGER,
        officer_hrms_id TEXT,
        officer_name TEXT,
        from_post_id INTEGER,
        from_post_name TEXT,
        to_post_id INTEGER,
        to_post_name TEXT,
        reason TEXT,
        collision_displaced_officer TEXT,
        collision_displaced_hrms TEXT,
        rule_tenure_check TEXT,
        rule_spouse_check TEXT,
        rule_exam_check TEXT,
        rule_roster_check TEXT,
        status TEXT,
        timestamp TEXT
    )
    """)

    conn.commit()

    # --- POPULATE ROSTER CANDIDATES ---
    wb = openpyxl.load_workbook(SOURCE_GRAD_FILE, read_only=True, data_only=True)
    ws = wb['PROMOTION_242']
    rows = list(ws.iter_rows(values_only=True))[5:]

    # Pre-fetch master posts for lookup
    cur.execute("""
    SELECT id, name_of_post, designation, district, present_officer_name, 
           present_officer_hrms_id, present_officer_tenure, elig_post_obliteration,
           posting_preferences_all
    FROM master_source_of_truth
    """)
    master_posts = cur.fetchall()
    post_by_hrms = {}
    post_by_name = {}
    for mp in master_posts:
        hid = str(mp[5]).strip() if mp[5] else ''
        pname = str(mp[4]).strip().lower() if mp[4] else ''
        if hid:
            post_by_hrms[hid] = mp
        if pname:
            post_by_name[pname] = mp

    roster_count = 0
    for r in rows:
        sl = r[0]
        if sl is None or not str(sl).strip().isdigit():
            continue
        sl_no = int(sl)
        roster_pt = int(r[1]) if r[1] is not None else sl_no
        res_for = str(r[2] or '').strip()
        off_name = str(r[3] or '').strip()
        hrms_id = str(r[4] or '').strip()
        caste = str(r[5] or '').strip()
        pres_post = str(r[6] or '').strip()
        srv_status = str(r[7] or '').strip()
        srv_ends = str(r[8] or '').strip()
        avd_mem = str(r[9] or '').strip()

        # Cross reference with master posts
        m_post = post_by_hrms.get(hrms_id)
        if not m_post:
            clean_n = off_name.lower().replace('dr.', '').strip()
            for kn, kp in post_by_name.items():
                if clean_n in kn or kn in clean_n:
                    m_post = kp
                    break

        curr_post_id = m_post[0] if m_post else None
        curr_dist = m_post[3] if m_post else 'West Bengal'
        curr_desig = m_post[2] if m_post else pres_post
        tenure_str = m_post[6] if m_post else '0'
        try:
            tenure_val = float(str(tenure_str).split()[0])
        except Exception:
            tenure_val = 0.0

        is_dual = 1 if (m_post and m_post[7] == 'Yes') else 0

        # Parse preferences if available
        pref_text = m_post[8] if m_post else '—'
        pref_1, pref_2, pref_3 = '—', '—', '—'
        if pref_text and pref_text != '—':
            for part in pref_text.split('|'):
                part = part.strip()
                if part.startswith('Pref 1:') or part.startswith('DD Pref 1:'):
                    pref_1 = part.split(':', 1)[1].strip()
                elif part.startswith('Pref 2:') or part.startswith('DD Pref 2:'):
                    pref_2 = part.split(':', 1)[1].strip()
                elif part.startswith('Pref 3:') or part.startswith('DD Pref 3:'):
                    pref_3 = part.split(':', 1)[1].strip()

        cur.execute("""
        INSERT INTO roster_50_point_candidates (
            sl_no, roster_point, point_reserved_for, officer_name, hrms_id, caste,
            present_posting, service_status, service_ends, avd_member, current_post_id,
            current_district, current_designation, tenure_years, is_dual_obliterated,
            pref_1, pref_2, pref_3, all_preferences
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sl_no, roster_pt, res_for, off_name, hrms_id, caste,
            pres_post, srv_status, srv_ends, avd_mem, curr_post_id,
            curr_dist, curr_desig, tenure_val, is_dual,
            pref_1, pref_2, pref_3, pref_text
        ))
        roster_count += 1

    wb.close()
    print(f"Populated {roster_count} 50-point roster candidates.")

    # --- POPULATE OBLITERATED OFFICERS ---
    cur.execute("""
    SELECT id, name_of_post, designation, establishment, district,
           present_officer_name, present_officer_hrms_id, caste,
           present_officer_dob, present_officer_dor, present_officer_tenure,
           gradation_rank_roster, posting_preferences_all
    FROM master_source_of_truth
    WHERE elig_post_obliteration = 'Yes'
    """)
    oblit_posts = cur.fetchall()

    oblit_count = 0
    for op in oblit_posts:
        post_id = op[0]
        post_name = op[1]
        desig = op[2]
        estab = op[3]
        dist = op[4]
        name = op[5]
        hid = op[6]
        caste = op[7]
        dob = op[8]
        dor = op[9]
        tenure_s = op[10]
        try:
            tenure_val = float(str(tenure_s).split()[0])
        except Exception:
            tenure_val = 0.0

        r_rank_str = op[11]
        is_on_r = 0
        r_rank = None
        if r_rank_str and r_rank_str != '—' and r_rank_str.isdigit():
            is_on_r = 1
            r_rank = int(r_rank_str)

        prefs = op[12]

        cur.execute("""
        INSERT INTO obliterated_post_officers (
            post_id, post_name, designation, establishment, district,
            officer_name, hrms_id, caste, dob, dor, tenure_years,
            is_on_roster, roster_rank, preferences
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id, post_name, desig, estab, dist,
            name, hid, caste, dob, dor, tenure_val,
            is_on_r, r_rank, prefs
        ))
        oblit_count += 1

    print(f"Populated {oblit_count} obliterated post officers.")

    # --- POPULATE OFFICIAL ORDERS ---
    if os.path.exists(ORDERS_JSON):
        with open(ORDERS_JSON) as f:
            orders = json.load(f)
        for ord_item in orders:
            cur.execute("""
            INSERT INTO official_orders (
                order_index, category, order_date, order_number, title,
                key_officers, subdirectory, web_source_portal,
                google_drive_archive, referenced_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ord_item.get('Order_Index'),
                ord_item.get('Category'),
                ord_item.get('Order_Date'),
                ord_item.get('Order_Number'),
                ord_item.get('Title'),
                ord_item.get('Key_Beneficiaries_or_Officers'),
                ord_item.get('Subdirectory'),
                ord_item.get('Web_Source_Portal'),
                ord_item.get('Google_Drive_Archive'),
                ord_item.get('Referenced_File')
            ))
        print(f"Populated {len(orders)} official orders into database.")

    conn.commit()
    conn.close()
    print("Database helper tables initialized successfully!")

if __name__ == "__main__":
    init_tables()
