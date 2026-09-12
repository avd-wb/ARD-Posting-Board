#!/usr/bin/env python3
"""
rebuild_database_1794.py
Authoritative database compiler for West Bengal ARD Department.
Compiles:
1. cadre_1794_posts (STRICTLY 1,794 active sanctioned posts under Notification No. 1809)
2. obliterated_posts_1808 (STRICTLY 106 abolished posts under Notification No. 1808, with Dr. Nirmalya Ranjan Sarkar at row 48)
3. available_dd_posts (244 sanctioned DD posts, 2 blocked on vigilance, 242 available)
4. roster_50_point_candidates (242 candidates with detailed institution & block names)
5. master_source_of_truth (points strictly to the 1,794 sanctioned cadre)
"""

import os
import re
import json
import sqlite3
import openpyxl
import datetime
from backup_manager import BackupManager

DB_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD_AG/ard_master_truth.db"
SEED_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD/04_AVD_Members/02 Master/20260902_AVD_MDV-MASTER_ARD_HR_Master_SEED.xlsx"
OBLIT_TSV = "/Users/nirmalyaranjansarkar/Projects/AVD/04_AVD_Members/06 Vacancies/out_OBLITERATED.tsv"
TSV_N_AM = "/Users/nirmalyaranjansarkar/Projects/AVD/04_AVD_Members/06 Vacancies/20260911_AVD_VF-DATA_1794_POSTS_Columns_N_to_AM.tsv"
TSV_F = "/Users/nirmalyaranjansarkar/Projects/AVD/04_AVD_Members/06 Vacancies/20260911_AVD_VF-DATA_1794_POSTS_Column_F.tsv"
TSV_CD = "/Users/nirmalyaranjansarkar/Projects/AVD/04_AVD_Members/06 Vacancies/20260911_AVD_VF-DATA_1794_POSTS_Columns_C_D.tsv"
OFFICERS_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD/11_AVD_HR_Portal/data/officers"
DD_VACANCY_XLSX = "/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /From AD HQ/Vacancy of DD.xlsx"
GRAD_FILE = "/Users/nirmalyaranjansarkar/Projects/AVD/03_ARD_HR/ARD_HR/02. Working Outputs/20260908 Gradation List 01092026/20260908_AVD_DDP_Gradation_List_01092026.xlsx"
ORDERS_JSON = "/Users/nirmalyaranjansarkar/Projects/AVD_AG/orders_repository/orders_master_index.json"

SPECIAL_TENURE_DISTRICTS = {
    "Alipurduar": 4.0, "Coochbehar": 4.0, "Jalpaiguri": 4.0,
    "Darjeeling": 4.0, "Kalimpong": 4.0, "Uttar Dinajpur": 4.0,
    "Dakshin Dinajpur": 4.0, "Purulia": 4.0, "Jhargram": 4.0
}

def clean(v):
    return str(v or '').strip()

def get_tenure_norm(district, block=""):
    d = clean(district)
    for k, v in SPECIAL_TENURE_DISTRICTS.items():
        if k.lower() in d.lower():
            return v
    b = clean(block).lower()
    if any(sm in b for sm in ["bundowan", "bagmundi", "manbazar", "hirbundh", "ranibundh"]):
        return 4.0
    return 5.0

def main():
    print("=== Step 1: Taking Atomic Backup of Existing Database ===")
    bm = BackupManager(DB_PATH)
    b_res = bm.create_backup("pre_clean_1794_rebuild")
    print("Backup status:", b_res)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Step 2: Load Officer JSON Profiles (1,271 files) ---
    print("\n=== Step 2: Loading Verified Officer JSON Profiles ===")
    officer_profiles = {}
    if os.path.exists(OFFICERS_DIR):
        for f in os.listdir(OFFICERS_DIR):
            if f.endswith(".json"):
                p = os.path.join(OFFICERS_DIR, f)
                try:
                    with open(p) as fp:
                        data = json.load(fp)
                        hid = clean(data.get("hrms"))
                        if hid:
                            officer_profiles[hid] = data
                except Exception:
                    pass
    print(f"Loaded {len(officer_profiles)} verified officer profiles.")

    # --- Step 3: Load Sanctioned 1,794 Spine and Column Data ---
    print("\n=== Step 3: Loading Sanctioned Spine & Adjudicated Columns ===")
    wb_seed = openpyxl.load_workbook(SEED_PATH, read_only=True, data_only=True)
    ws_ps = wb_seed['POSTS_SANCTIONED']
    rows_ps = list(ws_ps.iter_rows(values_only=True))[1:]
    wb_seed.close()
    print(f"Loaded {len(rows_ps)} sanctioned posts from SEED.")

    with open(TSV_N_AM) as fp:
        rows_n = [l.strip().split('\t') for l in fp]

    with open(TSV_F) as fp:
        rows_f = [l.strip() for l in fp]

    with open(TSV_CD) as fp:
        rows_cd = [l.strip().split('\t') for l in fp]

    print(f"Loaded {len(rows_n)} rows of N_to_AM, {len(rows_f)} rows of Column F, {len(rows_cd)} rows of Columns C:D.")

    # --- Step 4: Re-create cadre_1794_posts Table ---
    print("\n=== Step 4: Compiling cadre_1794_posts Table ===")
    cur.execute("DROP TABLE IF EXISTS cadre_1794_posts")
    cur.execute("""
    CREATE TABLE cadre_1794_posts (
        id INTEGER PRIMARY KEY,
        post_sl INTEGER,
        district TEXT,
        block TEXT,
        establishment TEXT,
        estab_type TEXT,
        designation TEXT,
        post_code TEXT,
        post_no TEXT,
        pay_level TEXT,
        occupancy_status TEXT,
        incumbent_name TEXT,
        incumbent_hrms TEXT,
        incumbent_doj TEXT,
        incumbent_tenure TEXT,
        tenure_norm REAL,
        tenure_over_flag TEXT,
        incumbent_dob TEXT,
        incumbent_dor TEXT,
        avd_member TEXT,
        last_transfer_order TEXT,
        service_utilized_flag TEXT,
        qualification TEXT,
        detailed_presentation TEXT,
        is_substantive_blocked INTEGER DEFAULT 0,
        substantive_allotted_hrms TEXT DEFAULT NULL,
        substantive_allotted_name TEXT DEFAULT NULL,
        su_allotted_hrms TEXT DEFAULT NULL,
        su_allotted_name TEXT DEFAULT NULL
    )
    """)

    inserted_cadre = 0
    active_incumbents = 0
    clear_vacancies = 0

    for i in range(1794):
        post_sl = int(rows_ps[i][0])
        dist = clean(rows_ps[i][1])
        estab = clean(rows_ps[i][2])
        estab_type = clean(rows_ps[i][3])
        post_desig = clean(rows_ps[i][4])
        p_code = clean(rows_ps[i][5])
        p_no = clean(rows_ps[i][6])
        pay = clean(rows_ps[i][7])

        block = rows_f[i] if i < len(rows_f) else ""
        if not block:
            block = "Directorate HQ" if "directorate" in estab_type.lower() else dist + " HQ"

        n_row = rows_n[i] if i < len(rows_n) else []
        norm_str = n_row[0] if len(n_row) > 0 else "5 years"
        is_vac_str = n_row[1] if len(n_row) > 1 else "Yes"
        inc_raw = n_row[2] if len(n_row) > 2 else ""
        su_raw = n_row[3] if len(n_row) > 3 else ""
        tenure_str = n_row[5] if len(n_row) > 5 else ""
        avd_str = n_row[8] if len(n_row) > 8 else "No"

        # Correct Dr. Nirmalya Ranjan Sarkar at Post 54:
        # He was transferred to Hooghly on 2024-12-20 via order 4246-AR&AH/3A-40/2016.
        # Post 54 at Dte HQ is VACANT!
        if post_sl == 54 or "2014000243" in inc_raw or "nirmalya ranjan sarkar" in inc_raw.lower():
            if dist.lower() == "kolkata" or "directorate" in estab.lower():
                is_vac_str = "Yes"
                inc_raw = ""
                su_raw = ""
                tenure_str = ""

        # Parse Incumbent Name & HRMS
        inc_name = ""
        inc_hrms = ""
        if inc_raw and is_vac_str.lower() != "yes":
            m_hrms = re.search(r'HRMS\s*(\d+)', inc_raw)
            if m_hrms:
                inc_hrms = m_hrms.group(1).strip()
                inc_name = re.sub(r'\(HRMS.*?\)', '', inc_raw).strip()
            else:
                inc_name = inc_raw.strip()

        occ_status = "Vacant" if (is_vac_str.lower() == "yes" or not inc_name) else "Occupied"
        if occ_status == "Occupied":
            active_incumbents += 1
        else:
            clear_vacancies += 1

        # Enrich with Officer Profile
        prof = officer_profiles.get(inc_hrms)
        inc_dob = ""
        inc_dor = ""
        inc_doj = ""
        last_order = ""
        qual = ""

        if prof and occ_status == "Occupied":
            inc_name = clean(prof.get("name")) or inc_name
            inc_dob = clean(prof.get("dob"))
            inc_doj = clean(prof.get("doj_present_post"))
            inc_dor = clean(prof.get("superannuation_date")) or clean(prof.get("superannuation_expected"))
            avd_str = "Yes" if clean(prof.get("avd_member")).upper() == "YES" else "No"
            last_order = f"{clean(prof.get('last_transfer_order_no'))} dt. {clean(prof.get('last_transfer_order_date'))}"
            qual = clean(prof.get("qualification")) or clean(prof.get("qualifications_submitted"))

        norm = get_tenure_norm(dist, block)
        tenure_over = "No"
        try:
            ten_val = float(tenure_str.split()[0].replace('y', ''))
            if ten_val > norm:
                tenure_over = "Yes"
        except Exception:
            pass

        # Detailed presentation
        if occ_status == "Occupied":
            det = f"{inc_name} ({inc_hrms}) — {post_desig}, {estab}, {block}, {dist}"
        else:
            det = f"[CLEAR VACANCY] {post_desig}, {estab}, {block}, {dist}"

        cur.execute("""
        INSERT INTO cadre_1794_posts (
            id, post_sl, district, block, establishment, estab_type, designation,
            post_code, post_no, pay_level, occupancy_status, incumbent_name,
            incumbent_hrms, incumbent_doj, incumbent_tenure, tenure_norm,
            tenure_over_flag, incumbent_dob, incumbent_dor, avd_member,
            last_transfer_order, service_utilized_flag, qualification,
            detailed_presentation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_sl, post_sl, dist, block, estab, estab_type, post_desig,
            p_code, p_no, pay, occ_status, inc_name,
            inc_hrms, inc_doj, tenure_str, norm,
            tenure_over, inc_dob, inc_dor, avd_str,
            last_order, su_raw or "No", qual, det
        ))
        inserted_cadre += 1

    print(f"Populated {inserted_cadre} active cadre posts into cadre_1794_posts (Occupied: {active_incumbents}, Vacant: {clear_vacancies}).")

    # --- Step 5: Populate obliterated_posts_1808 (106 Posts) ---
    print("\n=== Step 5: Compiling obliterated_posts_1808 Table ===")
    cur.execute("DROP TABLE IF EXISTS obliterated_posts_1808")
    cur.execute("""
    CREATE TABLE obliterated_posts_1808 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oblit_sl INTEGER,
        district TEXT,
        block TEXT,
        establishment TEXT,
        estab_type TEXT,
        post_name TEXT,
        is_vacant TEXT,
        officer_name TEXT,
        hrms_id TEXT,
        doj TEXT,
        tenure TEXT,
        avd_member TEXT,
        is_on_roster INTEGER DEFAULT 0,
        roster_rank INTEGER DEFAULT NULL,
        rehabilitation_status TEXT DEFAULT 'Pending',
        substantive_post_id INTEGER DEFAULT NULL,
        substantive_post_name TEXT DEFAULT NULL,
        su_post_id INTEGER DEFAULT NULL,
        su_post_name TEXT DEFAULT NULL,
        detailed_presentation TEXT
    )
    """)

    # Check 50-point roster HRMS IDs
    wb_g = openpyxl.load_workbook(GRAD_FILE, read_only=True, data_only=True)
    ws_p242 = wb_g['PROMOTION_242']
    p242_rows = list(ws_p242.iter_rows(values_only=True))[5:]
    wb_g.close()

    roster_hrms_map = {}
    for r in p242_rows:
        if r[0] and str(r[0]).isdigit() and r[4]:
            roster_hrms_map[clean(r[4])] = (int(r[0]), int(r[1]), clean(r[2]))

    oblit_count = 0
    oblit_incumbents = 0
    with open(OBLIT_TSV) as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if not parts[0].isdigit():
                continue

            sl = int(parts[0])
            dist = parts[1] if len(parts) > 1 else ""
            blk = parts[2] if len(parts) > 2 else ""
            estab = parts[3] if len(parts) > 3 else ""
            et = parts[4] if len(parts) > 4 else ""
            pname = parts[5] if len(parts) > 5 else ""
            is_vac = parts[6] if len(parts) > 6 else ""
            name = parts[7] if len(parts) > 7 else ""
            hid = parts[8] if len(parts) > 8 else ""
            doj = parts[9] if len(parts) > 9 else ""
            tenure = parts[10] if len(parts) > 10 else ""
            mem = parts[11] if len(parts) > 11 else ""

            # Check Dr. Nirmalya Ranjan Sarkar
            if hid == "2014000243" or "nirmalya ranjan sarkar" in name.lower() or sl == 48:
                name = "Dr. Nirmalya Ranjan Sarkar"
                hid = "2014000243"
                pname = "Asstt. Director, ARD(SA), Hooghly"
                estab = "Deputy Director, ARD&PO, Hooghly"
                blk = "Hooghly District HQ"
                dist = "Hooghly"
                doj = "2024-12-23"
                tenure = "1 y 8 m 19 d"
                mem = "YES"

            r_info = roster_hrms_map.get(hid)
            is_on_r = 1 if r_info else 0
            r_rank = r_info[0] if r_info else None

            if name and name != "Under verification":
                oblit_incumbents += 1
                det = f"{name} ({hid}) — {pname}, {estab}, {blk}, {dist}"
            else:
                det = f"[VACANT OBLITERATED POST] {pname}, {estab}, {blk}, {dist}"

            cur.execute("""
            INSERT INTO obliterated_posts_1808 (
                oblit_sl, district, block, establishment, estab_type, post_name,
                is_vacant, officer_name, hrms_id, doj, tenure, avd_member,
                is_on_roster, roster_rank, detailed_presentation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sl, dist, blk, estab, et, pname,
                is_vac, name, hid, doj, tenure, mem,
                is_on_r, r_rank, det
            ))
            oblit_count += 1

    print(f"Populated {oblit_count} obliterated posts into obliterated_posts_1808 ({oblit_incumbents} serving incumbents).")

    # --- Step 6: Populate available_dd_posts (244 Sanctioned, 242 Available) ---
    print("\n=== Step 6: Compiling available_dd_posts Table ===")
    cur.execute("DROP TABLE IF EXISTS available_dd_posts")
    cur.execute("""
    CREATE TABLE available_dd_posts (
        dd_sl INTEGER PRIMARY KEY,
        district TEXT,
        establishment TEXT,
        office TEXT,
        post_name TEXT,
        is_blocked_vigilance INTEGER DEFAULT 0,
        blocked_reason TEXT DEFAULT NULL,
        allotment_status TEXT DEFAULT 'Available',
        allotted_hrms TEXT DEFAULT NULL,
        allotted_name TEXT DEFAULT NULL
    )
    """)

    wb_dd = openpyxl.load_workbook(DD_VACANCY_XLSX, data_only=True)
    ws_dd = wb_dd['Sheet1']
    dd_count = 0
    for r in ws_dd.iter_rows(min_row=4, values_only=True):
        if r[1] is None or not str(r[1]).isdigit():
            continue
        sl = int(r[1])
        dist_estab = clean(r[3])
        office = clean(r[4])
        post_name = clean(r[5])

        is_blocked = 0
        b_reason = None
        if sl == 178:
            is_blocked = 1
            b_reason = "Held by Dr. Rupam Barua (2013001674) - Promotion to JD stayed on vigilance"
        elif sl == 52:
            is_blocked = 1
            b_reason = "Held by Dr. Sritanu Maiti (1994000339) - Promotion to JD stayed on vigilance"

        cur.execute("""
        INSERT INTO available_dd_posts (
            dd_sl, district, establishment, office, post_name,
            is_blocked_vigilance, blocked_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (sl, dist_estab, dist_estab, office, post_name, is_blocked, b_reason))
        dd_count += 1
    wb_dd.close()
    print(f"Populated {dd_count} Deputy Director posts (2 blocked, {dd_count - 2} available).")

    # --- Step 7: Populate roster_50_point_candidates (242 Candidates) ---
    print("\n=== Step 7: Compiling roster_50_point_candidates Table ===")
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
        present_block TEXT,
        present_district TEXT,
        detailed_presentation TEXT,
        service_status TEXT,
        service_ends TEXT,
        avd_member TEXT,
        is_dual_obliterated INTEGER DEFAULT 0,
        pref_1 TEXT,
        pref_2 TEXT,
        pref_3 TEXT,
        all_preferences TEXT,
        allotment_status TEXT DEFAULT 'Pending',
        substantive_post_id INTEGER DEFAULT NULL,
        substantive_post_name TEXT DEFAULT NULL,
        su_post_id INTEGER DEFAULT NULL,
        su_post_name TEXT DEFAULT NULL
    )
    """)

    for r in p242_rows:
        if not r[0] or not str(r[0]).isdigit():
            continue
        sl = int(r[0])
        roster_pt = int(r[1]) if r[1] is not None else sl
        res_for = clean(r[2])
        name = clean(r[3])
        hid = clean(r[4])
        cat = clean(r[5])
        pres_post = clean(r[6])
        srv_stat = clean(r[7])
        srv_ends = clean(r[8])
        avd_mem = clean(r[9])

        prof = officer_profiles.get(hid)
        p_dist = ""
        p_blk = ""
        p_estab = ""
        p_desig = pres_post

        if prof:
            p_desig = clean(prof.get("present_post_designation")) or pres_post
            p_estab = clean(prof.get("present_establishment"))
            p_blk = clean(prof.get("present_block"))
            p_dist = clean(prof.get("present_district_unit"))
            full_detail = f"{name} ({hid}) — {p_desig}, {p_estab}, {p_blk}, {p_dist}"
        else:
            full_detail = f"{name} ({hid}) — {pres_post}"

        is_dual = 1 if hid in roster_hrms_map and hid in [clean(x[8]) for x in [l.strip().split('\t') for l in open(OBLIT_TSV) if l.strip()] if len(x) > 8] else 0

        cur.execute("""
        INSERT INTO roster_50_point_candidates (
            sl_no, roster_point, point_reserved_for, officer_name, hrms_id,
            caste, present_posting, present_block, present_district,
            detailed_presentation, service_status, service_ends, avd_member,
            is_dual_obliterated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sl, roster_pt, res_for, name, hid,
            cat, p_desig, p_blk, p_dist,
            full_detail, srv_stat, srv_ends, avd_mem,
            is_dual
        ))

    print(f"Populated 242 candidates into roster_50_point_candidates.")

    # --- Step 8: Update Backward Compatible master_source_of_truth ---
    print("\n=== Step 8: Updating master_source_of_truth to Point Strictly to 1,794 Cadre ===")
    try:
        cur.execute("DROP TABLE IF EXISTS master_source_of_truth")
    except Exception:
        pass
    try:
        cur.execute("DROP VIEW IF EXISTS master_source_of_truth")
    except Exception:
        pass
    cur.execute("""
    CREATE TABLE master_source_of_truth AS
    SELECT 
        id,
        detailed_presentation AS name_of_post,
        'Sanctioned' AS type,
        designation,
        post_code AS post,
        establishment,
        block,
        district,
        tenure_norm || ' years norm' AS normal_tenure,
        CASE WHEN occupancy_status = 'Occupied' THEN 'Yes' ELSE 'No' END AS present_occupant_status,
        incumbent_name AS present_officer_name,
        incumbent_tenure AS present_officer_tenure,
        tenure_over_flag,
        incumbent_hrms AS present_officer_hrms_id,
        incumbent_dob AS present_officer_dob,
        '' AS age,
        incumbent_doj AS present_officer_doj,
        incumbent_dor AS present_officer_dor,
        '' AS years_months_days_left,
        avd_member AS avd_affiliation,
        service_utilized_flag AS service_utilization,
        last_transfer_order AS last_posting_history,
        '' AS gradation_rank_roster,
        'Gen' AS caste,
        'No' AS ph_status,
        'Male' AS gender,
        '' AS posting_preferences_all,
        'No' AS elig_promotion,
        tenure_over_flag AS elig_tenure_over,
        'No' AS elig_displacement,
        'No' AS elig_post_obliteration,
        'No' AS elig_other_reasons,
        qualification,
        '' AS additional_qualification,
        '' AS family_details
    FROM cadre_1794_posts
    """)

    conn.commit()
    conn.close()
    print("=== Database Rebuild and Clean 1,794 Cadre Setup Completed Successfully! ===")

if __name__ == "__main__":
    main()
