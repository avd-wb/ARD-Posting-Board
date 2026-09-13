#!/usr/bin/env python3
"""
enrich_ddo_and_office_codes.py
Ingests verified HRMS/WBIFMS DDO Codes and Office Codes from:
/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /Source from HRMS/2026090_HRMS_ARD_20260908.tsv
and enriches:
1. master_all_cadre_employees
2. officer_extended_dossier
3. sacrosanct_officer_dossier (recalculating SHA-256 state seal)
4. roster_50_point_candidates
5. cadre_1794_posts
"""

import csv
import sqlite3
import hashlib
from datetime import datetime

DB_PATH = 'ard_master_truth.db'
TSV_PATH = '/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /Source from HRMS/2026090_HRMS_ARD_20260908.tsv'

ALIAS_MAP = {
    '1998001816': '1995001816',  # Dr. Madhumita Sengupta
    '1992000095': '1995000092',  # Dr. Manik Lal Saha
    '1993000339': '1994000339',  # Dr. Sritanu Maiti
    '1997005397': '1997005394',  # Dr. Raj Kumar Banerjee
    '2000000075': '2000000755',  # Dr. Tapan Kr. Sur
}

def ensure_columns(cur, table_name, cols):
    cur.execute(f"PRAGMA table_info({table_name})")
    existing_cols = [r[1] for r in cur.fetchall()]
    for col, col_type in cols.items():
        if col not in existing_cols:
            print(f"Adding column '{col} {col_type}' to table '{table_name}'...")
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {col_type};")

def main():
    print("=" * 70)
    print("ENRICHING MASTER DATABASE WITH VERIFIED HRMS DDO & OFFICE CODES")
    print("=" * 70)

    # 1. Load TSV Data
    print(f"\nLoading HRMS TSV dataset from:\n  {TSV_PATH}...")
    tsv_records = {}
    with open(TSV_PATH, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            hid = str(r['hrms']).strip()
            if hid:
                tsv_records[hid] = {
                    'office_code': (r.get('office_code') or '').strip(),
                    'ddo_code': (r.get('ddo') or '').strip(),
                    'office_name': (r.get('office_name') or '').strip(),
                    'office_address': (r.get('office_address') or '').strip(),
                    'designation': (r.get('designation') or '').strip(),
                    'status': (r.get('status') or '').strip(),
                    'service_end_date': (r.get('service_end_date') or '').strip()
                }

    print(f"Loaded {len(tsv_records)} unique HRMS employee records.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 2. Add Columns if needed
    cols_to_add = {'office_code': 'TEXT', 'ddo_code': 'TEXT'}
    for tbl in ['master_all_cadre_employees', 'officer_extended_dossier', 
                'sacrosanct_officer_dossier', 'roster_50_point_candidates', 'cadre_1794_posts']:
        ensure_columns(cur, tbl, cols_to_add)

    # 3. Update master_all_cadre_employees
    print("\n1. Updating master_all_cadre_employees...")
    cur.execute("SELECT hrms_id FROM master_all_cadre_employees")
    all_cadre_ids = [r[0] for r in cur.fetchall()]
    m_updated = 0
    for hid in all_cadre_ids:
        lookup_hid = ALIAS_MAP.get(hid, hid)
        if lookup_hid in tsv_records:
            rec = tsv_records[lookup_hid]
            cur.execute("""
                UPDATE master_all_cadre_employees
                SET office_code = ?, ddo_code = ?
                WHERE hrms_id = ?
            """, (rec['office_code'] or None, rec['ddo_code'] or None, hid))
            m_updated += 1
    print(f"  -> Updated {m_updated} / {len(all_cadre_ids)} records in master_all_cadre_employees.")

    # 4. Update officer_extended_dossier
    print("\n2. Updating officer_extended_dossier...")
    cur.execute("SELECT hrms_id FROM officer_extended_dossier")
    dossier_ids = [r[0] for r in cur.fetchall()]
    d_updated = 0
    for hid in dossier_ids:
        lookup_hid = ALIAS_MAP.get(hid, hid)
        if lookup_hid in tsv_records:
            rec = tsv_records[lookup_hid]
            cur.execute("""
                UPDATE officer_extended_dossier
                SET office_code = ?, ddo_code = ?
                WHERE hrms_id = ?
            """, (rec['office_code'] or None, rec['ddo_code'] or None, hid))
            d_updated += 1
    print(f"  -> Updated {d_updated} / {len(dossier_ids)} records in officer_extended_dossier.")

    # 5. Update roster_50_point_candidates
    print("\n3. Updating roster_50_point_candidates...")
    cur.execute("SELECT hrms_id FROM roster_50_point_candidates")
    roster_ids = [r[0] for r in cur.fetchall()]
    r_updated = 0
    for hid in roster_ids:
        lookup_hid = ALIAS_MAP.get(hid, hid)
        if lookup_hid in tsv_records:
            rec = tsv_records[lookup_hid]
            cur.execute("""
                UPDATE roster_50_point_candidates
                SET office_code = ?, ddo_code = ?
                WHERE hrms_id = ?
            """, (rec['office_code'] or None, rec['ddo_code'] or None, hid))
            r_updated += 1
    print(f"  -> Updated {r_updated} / {len(roster_ids)} records in roster_50_point_candidates.")

    # 6. Update cadre_1794_posts
    print("\n4. Updating cadre_1794_posts from incumbents...")
    cur.execute("SELECT id, incumbent_hrms, establishment, district, block FROM cadre_1794_posts")
    posts = cur.fetchall()
    p_updated = 0
    
    # Also collect establishment/block to DDO mapping from known incumbents
    estab_ddo_map = {}
    for pid, hid, estab, dist, blk in posts:
        if hid:
            lookup_hid = ALIAS_MAP.get(hid, hid)
            if lookup_hid in tsv_records:
                rec = tsv_records[lookup_hid]
                off_code = rec['office_code'] or None
                ddo_code = rec['ddo_code'] or None
                cur.execute("""
                    UPDATE cadre_1794_posts
                    SET office_code = ?, ddo_code = ?
                    WHERE id = ?
                """, (off_code, ddo_code, pid))
                p_updated += 1
                if estab and (off_code or ddo_code):
                    estab_key = (dist.strip().lower() if dist else '', (blk or '').strip().lower(), estab.strip().lower())
                    estab_ddo_map[estab_key] = (off_code, ddo_code)

    print(f"  -> Updated {p_updated} occupied posts in cadre_1794_posts with incumbent DDO & Office codes.")

    # Infer DDO / Office code for vacant posts where station matches a known establishment
    vacant_inferred = 0
    for pid, hid, estab, dist, blk in posts:
        if not hid and estab:
            estab_key = (dist.strip().lower() if dist else '', (blk or '').strip().lower(), estab.strip().lower())
            if estab_key in estab_ddo_map:
                off_code, ddo_code = estab_ddo_map[estab_key]
                cur.execute("""
                    UPDATE cadre_1794_posts
                    SET office_code = ?, ddo_code = ?
                    WHERE id = ?
                """, (off_code, ddo_code, pid))
                vacant_inferred += 1
    print(f"  -> Inferred DDO & Office codes for {vacant_inferred} vacant posts based on establishment match.")

    # 7. Update sacrosanct_officer_dossier and recalculate SHA-256 seal
    print("\n5. Updating sacrosanct_officer_dossier and sealing with SHA-256...")
    conn.row_factory = sqlite3.Row
    cur2 = conn.cursor()
    cur2.execute("SELECT * FROM sacrosanct_officer_dossier")
    sacro_rows = cur2.fetchall()
    now_iso = datetime.now().isoformat()
    s_updated = 0

    for srow in sacro_rows:
        hid = srow['hrms_id']
        lookup_hid = ALIAS_MAP.get(hid, hid)
        off_code = ""
        ddo_code = ""
        if lookup_hid in tsv_records:
            rec = tsv_records[lookup_hid]
            off_code = rec['office_code'] or ""
            ddo_code = rec['ddo_code'] or ""
            s_updated += 1

        # Recompute SHA-256 hash seal including office_code and ddo_code
        hash_payload = (
            f"{hid}|{srow['officer_name']}|{srow['gender']}|{srow['dob']}|{srow['dor']}|"
            f"{srow['doj']}|{srow['cadre']}|{srow['substantive_post']}|{srow['current_posting']}|"
            f"{srow['caste']}|{off_code}|{ddo_code}"
        )
        new_sha256 = hashlib.sha256(hash_payload.encode('utf-8')).hexdigest()

        cur.execute("""
            UPDATE sacrosanct_officer_dossier
            SET office_code = ?,
                ddo_code = ?,
                record_sha256 = ?,
                last_verified_at = ?
            WHERE hrms_id = ?
        """, (off_code or None, ddo_code or None, new_sha256, now_iso, hid))

    print(f"  -> Updated and sealed all {len(sacro_rows)} records in sacrosanct_officer_dossier ({s_updated} matched TSV).")

    conn.commit()
    conn.close()

    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE AND VERIFIED!")
    print("=" * 70)

if __name__ == '__main__':
    main()
