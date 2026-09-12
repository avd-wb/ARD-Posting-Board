#!/usr/bin/env python3
"""
sync_cadre_with_hrms_tsv.py
Synchronizes all database tables with the genuine, authoritative HRMS TSV export:
'/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /Source from HRMS/2026090_HRMS_ARD_20260908.tsv'
"""

import csv
import sqlite3
import os

DB_PATH = 'ard_master_truth.db'
TSV_PATH = '/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /Source from HRMS/2026090_HRMS_ARD_20260908.tsv'

def sync_hrms():
    print(f"Loading genuine HRMS source: {TSV_PATH}...")
    hrms_data = {}
    all_tsv_records = {}
    with open(TSV_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            hid = str(r['hrms']).strip()
            all_tsv_records[hid] = r
            if r.get('status', '').strip().lower() == 'in service':
                hrms_data[hid] = r

    print(f"Loaded {len(hrms_data)} active in-service officers (out of {len(all_tsv_records)} total) from HRMS TSV.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # =========================================================================
    # 1. Update master_all_cadre_employees table
    # =========================================================================
    print("\n1. Synchronizing master_all_cadre_employees...")
    # First update existing records matching HRMS
    cur.execute("SELECT hrms_id FROM master_all_cadre_employees")
    existing_hrms = set(str(r[0]).strip() for r in cur.fetchall())

    for hid, t in hrms_data.items():
        raw_name = t['name']
        display_name = f"Dr. {raw_name.title().replace('Dr.', '').replace('Dr', '').strip()}"
        clean_name = raw_name.title().replace('Dr.', '').replace('Dr', '').strip()
        desig = t['designation'] or t['post'] or 'Officer'
        office = t['office_name'] or ''
        estab = t['office_name'] or ''
        dor = t['service_end_date'] or ''
        cadre = t['cadre'] or 'West Bengal Animal Husbandry and veterinary Service'
        
        # Determine district from office_address or office_name
        addr = (t['office_address'] or '').upper()
        off_up = office.upper()
        dist = "Kolkata"
        for d in ["North 24 Parganas", "South 24 Parganas", "Howrah", "Hooghly", "Nadia", "Purba Bardhaman", 
                  "Paschim Bardhaman", "Birbhum", "Bankura", "Purulia", "Paschim Medinipur", "Purba Medinipur", 
                  "Jhargram", "Malda", "Murshidabad", "Uttar Dinajpur", "Dakshin Dinajpur", "Jalpaiguri", 
                  "Alipurduar", "Cooch Behar", "Darjeeling", "Kalimpong"]:
            if d.upper() in addr or d.upper() in off_up:
                dist = d
                break

        is_hq = 1 if any(k in off_up for k in ["DIRECTORATE", "PRANI SAMPAD", "SALT LAKE"]) or t.get('ddo') == 'CAFAHV002' else 0
        present_posting = f"{desig}, {office}"

        if hid in existing_hrms:
            cur.execute("""
                UPDATE master_all_cadre_employees
                SET officer_name = ?,
                    clean_name = ?,
                    designation = ?,
                    present_posting = ?,
                    establishment = ?,
                    district = ?,
                    cadre = ?,
                    service_status = 'In Service',
                    dor = ?,
                    is_hq_deployed = ?
                WHERE hrms_id = ?
            """, (display_name, clean_name, desig, present_posting, estab, dist, cadre, dor, is_hq, hid))
        else:
            cur.execute("""
                INSERT INTO master_all_cadre_employees (
                    hrms_id, officer_name, clean_name, designation, present_posting, establishment,
                    district, cadre, service_status, dor, avd_member_flag,
                    is_50pt_candidate, is_hq_deployed, is_unsanctioned_post
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, 'In Service', ?, 1,
                    0, ?, 0
                )
            """, (hid, display_name, clean_name, desig, present_posting, estab, dist, cadre, dor, is_hq))

    # Mark non-in-service officers
    non_active_updated = 0
    for hid, t in all_tsv_records.items():
        st = t.get('status', '').strip()
        if st.lower() != 'in service' and hid in existing_hrms:
            cur.execute("UPDATE master_all_cadre_employees SET service_status = ? WHERE hrms_id = ?", (st, hid))
            non_active_updated += 1

    print(f"Updated master_all_cadre_employees for all {len(hrms_data)} in-service officers, and updated {non_active_updated} retired/deceased statuses.")

    # =========================================================================
    # 2. Update Directorate Headquarters Sanctioned Posts (53 to 73)
    # =========================================================================
    print("\n2. Updating Directorate Headquarters Posts 53-73 in cadre_1794_posts...")
    hq_officers_mapping = [
        (53, "2011000492", "Dr. Nilratan Mandal", "Assistant Director, ARD (Veterinary)"),
        (54, "2005000244", "Dr. Sumit Chowdhury", "Assistant Director, ARD (Veterinary)"),
        (55, "2019014318", "Dr. Prabir Roy", "Assistant Director, ARD (Veterinary)"),
        (56, "1995000104", "Dr. Chayan Bhattacharya", "Assistant Director, ARD (Veterinary)"),
        (57, "2001003414", "Dr. Atanu Saha", "Assistant Director, ARD (Veterinary)"),
        (58, "2020000305", "Dr. Ayan Mukherjee", "Assistant Director, ARD (Veterinary)"),
        (59, "2000000065", "Dr. Paresh Chandra Ghorui", "Assistant Director, ARD (Veterinary)"),
        (60, "1995002497", "Dr. Somen Chatterjee", "Assistant Director, ARD (Veterinary)"),
        (61, "1995000270", "Dr. Tapan Kumar Dey", "Assistant Director, ARD (Veterinary)"),
        (62, "1994005234", "Dr. Rupak Misra", "Assistant Director, ARD (Veterinary)"),
        (63, "1997000050", "Dr. Sumit Kumar Jana", "Assistant Director, ARD (Veterinary)"),
        (64, "1997005394", "Dr. Raj Kumar Banerjee", "Assistant Director, ARD (Veterinary)"),
        (65, "1998005218", "Dr. Priyabrata Chakravarty", "Assistant Director, ARD (Veterinary)"),
        (66, "1998007065", "Dr. Satyajit Roy", "Assistant Director, ARD (Veterinary)"),
        (67, "2005000086", "Dr. Arnab Das", "Assistant Director, ARD (Veterinary)"),
        (68, "2002000037", "Dr. Avijit Dutta", "Assistant Director, ARD (VR&I)"),
        (69, "2001000629", "Dr. Atanu Bose", "Assistant Director, ARD (VR&I)"),
        (70, "1992000077", "Dr. Sovanananda Mahanty", "Assistant Director, ARD (VR&I)"),
        (71, "1989007311", "Dr. Debasis Mukherjee", "Assistant Director, ARD (HQ)"),
        (72, "1987002148", "Dr. Rajat Kumar Roy", "Assistant Director, ARD (HQ)"),
        (73, "2001000715", "Dr. Subrata Sanki", "Veterinary Officer")
    ]

    for p_sl, hid, off_name, desig_title in hq_officers_mapping:
        t_row = hrms_data.get(hid, {})
        dor = t_row.get('service_end_date', '')
        cur.execute("""
            UPDATE cadre_1794_posts
            SET incumbent_name = ?,
                incumbent_hrms = ?,
                occupancy_status = 'Occupied',
                establishment = 'Directorate Headquarter, Kolkata',
                district = 'Kolkata',
                designation = ?,
                incumbent_dor = ?,
                detailed_presentation = ?
            WHERE post_sl = ?
        """, (off_name, hid, desig_title, dor, f"{off_name} ({hid}) — {desig_title}, Directorate Headquarter, Kolkata", p_sl))
        print(f"  Post {p_sl}: {off_name} ({hid}) -> {desig_title}, Directorate Headquarter, Kolkata")

    # Also ensure Dr. Nirmalya Ranjan Sarkar is in Post 1108 (AD Hooghly) with SU at HQ
    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Nirmalya Ranjan Sarkar',
            incumbent_hrms = '2014000243',
            occupancy_status = 'Occupied',
            service_utilized_flag = 'Service Utilized',
            detailed_presentation = 'Dr. Nirmalya Ranjan Sarkar (2014000243) — AD, ARD, Hooghly [SU as AD, ARD (Vety.), HQ, Kolkata]'
        WHERE post_sl = 1108
    """)
    print("  Post 1108: Dr. Nirmalya Ranjan Sarkar (2014000243) -> AD Hooghly [SU at AD Vety HQ]")

    # Clear retired/deceased officers from cadre_1794_posts so they become Clear Vacancies
    dead_retired_posts = [151, 478, 927, 1510]
    for p in dead_retired_posts:
        cur.execute("""
            UPDATE cadre_1794_posts
            SET incumbent_name = '',
                incumbent_hrms = '',
                occupancy_status = 'Vacant',
                detailed_presentation = 'Vacant'
            WHERE post_sl = ?
        """, (p,))
    print(f"  Cleared {len(dead_retired_posts)} deceased/retired incumbents to 'Vacant' in cadre_1794_posts.")

    # Also update all other posts in cadre_1794_posts where incumbent_hrms exists in TSV
    cur.execute("SELECT id, post_sl, incumbent_hrms, incumbent_name FROM cadre_1794_posts WHERE incumbent_hrms IS NOT NULL AND incumbent_hrms != ''")
    cadre_rows = cur.fetchall()
    updated_cadre = 0
    for row in cadre_rows:
        hid = str(row['incumbent_hrms']).strip()
        if hid in hrms_data:
            t = hrms_data[hid]
            name_tsv = t['name']
            dor_tsv = t['service_end_date'] or ''
            clean_name = f"Dr. {name_tsv.title().replace('Dr.', '').replace('Dr', '').strip()}"
            cur.execute("""
                UPDATE cadre_1794_posts
                SET incumbent_name = ?,
                    incumbent_dor = ?
                WHERE id = ?
            """, (clean_name, dor_tsv, row['id']))
            updated_cadre += 1

    print(f"Synchronized {updated_cadre} cadre posts with genuine HRMS titles and superannuation dates.")

    # =========================================================================
    # 3. Synchronize roster_50_point_candidates with genuine HRMS postings
    # =========================================================================
    print("\n3. Synchronizing roster_50_point_candidates with genuine HRMS records...")
    cur.execute("SELECT sl_no, hrms_id, officer_name FROM roster_50_point_candidates")
    roster_rows = cur.fetchall()
    
    updated_roster = 0
    for r in roster_rows:
        hid = str(r['hrms_id']).strip()
        if hid in hrms_data:
            t = hrms_data[hid]
            desig = t['designation'] or t['post'] or ''
            office = t['office_name'] or ''
            dor = t['service_end_date'] or ''
            
            # Format clean present posting string
            clean_posting = f"{desig}, {office}"
            
            cur.execute("""
                UPDATE roster_50_point_candidates
                SET present_posting = ?,
                    service_ends = ?
                WHERE hrms_id = ?
            """, (clean_posting, dor, hid))
            updated_roster += 1

    print(f"Updated present posting for all {updated_roster} of 242 roster candidates.")

    conn.commit()
    conn.close()
    print("\nHRMS synchronization successfully completed!")

if __name__ == '__main__':
    sync_hrms()
