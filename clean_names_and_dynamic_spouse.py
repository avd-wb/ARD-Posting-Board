#!/usr/bin/env python3
"""
clean_names_and_dynamic_spouse.py
---------------------------------
1. Eliminates duplicate/irregular prefixes across all tables:
   - Removes 'Dr. DR', 'Dr. Smt.', 'Dr. Shri', 'Dr. Sri', 'DR.', etc.
   - Standardizes all officer names to clean 'Dr. [Proper Name]'
   - Preserves suffixes: (SC), (ST), (OBC), (PH), (PWD), (2), (3), (nee Saha), etc.
   - Carefully protects names like Srimanta, Sribas, Srihari, Sritanu, Srishti.
   - Updates:
     * officer_extended_dossier
     * master_all_cadre_employees
     * sacrosanct_officer_dossier (recalculates SHA-256 seal)
     * official_gradation_list
     * roster_50_point_candidates
     * master_final_order_schedule
     * cadre_1794_posts
     * obliterated_posts_1808
     * displaced_officers_pool
     * simulation_assignments

2. Dynamic Spouse Intelligence ("Connect the Dots"):
   - Normalizes recorded spouse names from officer_extended_dossier.
   - Matches spouses against live cadre records (master_all_cadre_employees & cadre_1794_posts).
   - Generates 'spouse_cadre_crosswalk' table with live current designations, postings, districts, and co-location metrics.
   - Enriches officer_extended_dossier with verified 'spouse_is_wbahvs' ('Yes' / 'No') and clean spouse names.
   - Strict privacy preservation: Nirmalya Ranjan Sarkar (2014000243) & Madhurima Sarkar (2014000530) remain strictly redacted.
"""

import sqlite3
import re
import hashlib
from datetime import datetime

DB_PATH = 'ard_master_truth.db'
TARGET_PRIVACY_IDS = {'2014000243', '2014000530'}

def clean_officer_name(raw_name):
    if not raw_name:
        return ''
    s = str(raw_name).strip()
    
    # Extract any deployment annotation e.g. 'DR HALIM SARKAR su as DEO , PBGSBS , Malda'
    su_match = re.search(r'\s+(?:su as|s\.u\.|detailed as)\b.*$', s, re.I)
    if su_match:
        s = s[:su_match.start()].strip()
    
    # Repeatedly strip leading honorifics (must be followed by dot or whitespace, or enclosed in parens)
    # Examples: 'Dr. DR CHANDREYEE SEN' -> 'CHANDREYEE SEN'
    # 'Dr. Smt. Purba Sarkar' -> 'Purba Sarkar'
    # 'DR.ADHIR CHANDRA CHONGDER' -> 'ADHIR CHANDRA CHONGDER'
    # 'Dr. (Smt.) Soma Das' -> 'Soma Das'
    prefix_pat = re.compile(r'^(?:(?:dr|smt|shri|sri|mr|mrs|miss)(?:\.|\s+)|\((?:dr|smt|shri|sri|mr|mrs|miss)\.?\)\s*)+', re.I)
    while True:
        m = prefix_pat.match(s)
        if m:
            s = s[m.end():].strip()
        else:
            break
            
    # Handle 'DR.' without space (e.g. 'DR.ADHIR')
    s = re.sub(r'^(?:dr|smt|shri|sri|mr|mrs|miss)\.', '', s, flags=re.I).strip()
    
    # Title Case conversion preserving acronyms / categories
    words = s.split()
    cleaned_words = []
    for w in words:
        # Parenthesized word
        if w.startswith('(') and w.endswith(')'):
            inner = w[1:-1].strip()
            if inner.upper() in ['SC', 'ST', 'OBC', 'PH', 'PWD', 'GEN', 'A', 'B', 'C', '1', '2', '3', '4', '5']:
                cleaned_words.append(f'({inner.upper()})')
            elif inner.lower().startswith('nee '):
                parts = inner.split()
                cleaned_words.append(f'(nee {" ".join([p.capitalize() for p in parts[1:]])})')
            else:
                cleaned_words.append(f'({inner.title()})')
        elif w.upper() in ['SC', 'ST', 'OBC', 'PH', 'PWD', 'GEN']:
            cleaned_words.append(w.upper())
        elif w.isupper() and len(w) > 1:
            if '.' in w:
                parts = w.split('.')
                cleaned_words.append('.'.join([p.capitalize() for p in parts]))
            else:
                cleaned_words.append(w.capitalize())
        elif '.' in w:
            parts = w.split('.')
            cleaned_words.append('.'.join([p.capitalize() if p.isupper() else p for p in parts]))
        else:
            cleaned_words.append(w)
            
    name_core = ' '.join(cleaned_words).strip()
    name_core = re.sub(r'\s+', ' ', name_core)
    
    return f'Dr. {name_core}' if name_core else ''

def clean_spouse_name(raw_name):
    if not raw_name:
        return ''
    s = str(raw_name).strip()
    # Strip prefixes
    prefix_pat = re.compile(r'^(?:(?:dr|smt|shri|sri|mr|mrs|miss)(?:\.|\s+)|\((?:dr|smt|shri|sri|mr|mrs|miss)\.?\)\s*)+', re.I)
    while True:
        m = prefix_pat.match(s)
        if m:
            s = s[m.end():].strip()
        else:
            break
    s = re.sub(r'^(?:dr|smt|shri|sri|mr|mrs|miss)\.', '', s, flags=re.I).strip()
    
    words = s.split()
    cleaned_words = []
    for w in words:
        if w.startswith('(') and w.endswith(')'):
            inner = w[1:-1].strip()
            cleaned_words.append(f'({inner.title()})')
        elif w.isupper() and len(w) > 1:
            cleaned_words.append(w.capitalize())
        else:
            cleaned_words.append(w)
    res = ' '.join(cleaned_words).strip()
    # If original had Dr or mentions vet/ard, prefix Dr.
    if re.search(r'\bdr\b', raw_name, re.I):
        return f'Dr. {res}'
    return res

def normalize_name_tokens(s):
    if not s:
        return []
    s = re.sub(r'\b(dr|smt|shri|sri|mr|mrs|miss)\b\.?', '', s, flags=re.I)
    s = re.sub(r'\(.*?\)', '', s)
    s = re.sub(r'[^a-zA-Z\s]', ' ', s)
    return [t.lower() for t in s.split() if len(t) > 1]

def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    print("=== 1. CLEANING OFFICER NAMES ACROSS DATABASE ===")

    # Table 1: officer_extended_dossier
    rows = c.execute("SELECT hrms_id, officer_name, spouse_name FROM officer_extended_dossier").fetchall()
    print(f"Cleaning {len(rows)} records in officer_extended_dossier...")
    for r in rows:
        hid = r['hrms_id']
        old_name = r['officer_name']
        new_name = clean_officer_name(old_name)
        new_clean = re.sub(r'^Dr\.\s*', '', new_name, flags=re.I).lower().strip()
        
        # Clean spouse name too if present
        old_sp = r['spouse_name']
        new_sp = clean_spouse_name(old_sp) if old_sp else old_sp
        
        c.execute("""
            UPDATE officer_extended_dossier 
            SET officer_name = ?, clean_name = ?, spouse_name = ?
            WHERE hrms_id = ?
        """, (new_name, new_clean, new_sp, hid))

    # Table 2: master_all_cadre_employees
    rows = c.execute("SELECT hrms_id, officer_name FROM master_all_cadre_employees").fetchall()
    print(f"Cleaning {len(rows)} records in master_all_cadre_employees...")
    for r in rows:
        hid = r['hrms_id']
        old_name = r['officer_name']
        new_name = clean_officer_name(old_name)
        new_clean = re.sub(r'^Dr\.\s*', '', new_name, flags=re.I).strip()
        c.execute("""
            UPDATE master_all_cadre_employees 
            SET officer_name = ?, clean_name = ?
            WHERE hrms_id = ?
        """, (new_name, new_clean, hid))

    # Table 3: official_gradation_list
    rows = c.execute("SELECT id, officer_name FROM official_gradation_list").fetchall()
    print(f"Cleaning {len(rows)} records in official_gradation_list...")
    for r in rows:
        gid = r['id']
        old_name = r['officer_name']
        new_name = clean_officer_name(old_name)
        new_clean = re.sub(r'^Dr\.\s*', '', new_name, flags=re.I).lower().strip()
        c.execute("""
            UPDATE official_gradation_list 
            SET officer_name = ?, clean_name = ?
            WHERE id = ?
        """, (new_name, new_clean, gid))

    # Table 4: roster_50_point_candidates
    rows = c.execute("SELECT sl_no, officer_name FROM roster_50_point_candidates").fetchall()
    print(f"Cleaning {len(rows)} records in roster_50_point_candidates...")
    for r in rows:
        sl = r['sl_no']
        old_name = r['officer_name']
        new_name = clean_officer_name(old_name)
        c.execute("""
            UPDATE roster_50_point_candidates 
            SET officer_name = ?
            WHERE sl_no = ?
        """, (new_name, sl))

    # Table 5: master_final_order_schedule
    rows = c.execute("SELECT sl_no, officer_name FROM master_final_order_schedule").fetchall()
    print(f"Cleaning {len(rows)} records in master_final_order_schedule...")
    for r in rows:
        sl = r['sl_no']
        old_name = r['officer_name']
        new_name = clean_officer_name(old_name)
        new_clean = re.sub(r'^Dr\.\s*', '', new_name, flags=re.I).lower().strip()
        c.execute("""
            UPDATE master_final_order_schedule 
            SET officer_name = ?, clean_name = ?
            WHERE sl_no = ?
        """, (new_name, new_clean, sl))

    # Table 6: cadre_1794_posts
    rows = c.execute("SELECT id, incumbent_name FROM cadre_1794_posts WHERE incumbent_name IS NOT NULL").fetchall()
    print(f"Cleaning {len(rows)} records in cadre_1794_posts...")
    for r in rows:
        pid = r['id']
        old_name = r['incumbent_name']
        new_name = clean_officer_name(old_name)
        c.execute("""
            UPDATE cadre_1794_posts 
            SET incumbent_name = ?
            WHERE id = ?
        """, (new_name, pid))

    # Table 7: obliterated_posts_1808
    try:
        rows = c.execute("SELECT id, incumbent_name FROM obliterated_posts_1808 WHERE incumbent_name IS NOT NULL").fetchall()
        print(f"Cleaning {len(rows)} records in obliterated_posts_1808...")
        for r in rows:
            pid = r['id']
            new_name = clean_officer_name(r['incumbent_name'])
            c.execute("UPDATE obliterated_posts_1808 SET incumbent_name = ? WHERE id = ?", (new_name, pid))
    except Exception as e:
        print(f"Skipping obliterated_posts_1808: {e}")

    # Table 8: displaced_officers_pool
    try:
        rows = c.execute("SELECT id, officer_name FROM displaced_officers_pool WHERE officer_name IS NOT NULL").fetchall()
        print(f"Cleaning {len(rows)} records in displaced_officers_pool...")
        for r in rows:
            pid = r['id']
            new_name = clean_officer_name(r['officer_name'])
            c.execute("UPDATE displaced_officers_pool SET officer_name = ? WHERE id = ?", (new_name, pid))
    except Exception as e:
        print(f"Skipping displaced_officers_pool: {e}")

    # Table 9: simulation_assignments
    try:
        rows = c.execute("SELECT id, officer_name FROM simulation_assignments WHERE officer_name IS NOT NULL").fetchall()
        print(f"Cleaning {len(rows)} records in simulation_assignments...")
        for r in rows:
            pid = r['id']
            new_name = clean_officer_name(r['officer_name'])
            c.execute("UPDATE simulation_assignments SET officer_name = ? WHERE id = ?", (new_name, pid))
    except Exception as e:
        print(f"Skipping simulation_assignments: {e}")

    # Table 10: sacrosanct_officer_dossier (and recalculate SHA-256 seal)
    print("Updating sacrosanct_officer_dossier and recalculating SHA-256 seal...")
    now_str = datetime.now().isoformat()
    rows = c.execute("SELECT * FROM sacrosanct_officer_dossier").fetchall()
    for r in rows:
        hid = r['hrms_id']
        old_name = r['officer_name']
        new_name = clean_officer_name(old_name)
        new_clean = re.sub(r'^Dr\.\s*', '', new_name, flags=re.I).lower().strip()
        gender = r['gender'] or 'Male'
        
        # Compute payload hash
        hash_payload = f"{hid}|{new_name}|{gender}|{r['dob']}|{r['dor']}|{r['doj']}|{r['cadre']}|{r['substantive_post']}|{r['current_posting']}|{r['caste']}"
        rec_sha256 = hashlib.sha256(hash_payload.encode('utf-8')).hexdigest()
        
        c.execute("""
            UPDATE sacrosanct_officer_dossier 
            SET officer_name = ?, clean_name = ?, record_sha256 = ?, last_verified_at = ?
            WHERE hrms_id = ?
        """, (new_name, new_clean, rec_sha256, now_str, hid))

    conn.commit()
    print("All tables successfully updated with clean standard names!")

    print("\n=== 2. DYNAMIC SPOUSE CADRE CROSSWALK & INTELLIGENCE ===")
    
    # Create spouse_cadre_crosswalk table
    c.execute("""
        CREATE TABLE IF NOT EXISTS spouse_cadre_crosswalk (
            officer_hrms TEXT PRIMARY KEY,
            officer_name TEXT,
            officer_district TEXT,
            spouse_name_raw TEXT,
            spouse_hrms TEXT,
            spouse_name TEXT,
            spouse_current_designation TEXT,
            spouse_current_posting TEXT,
            spouse_current_establishment TEXT,
            spouse_current_district TEXT,
            is_same_district INTEGER DEFAULT 0,
            match_confidence TEXT,
            updated_at TEXT
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_spouse_officer_hrms ON spouse_cadre_crosswalk(officer_hrms);")
    c.execute("CREATE INDEX IF NOT EXISTS idx_spouse_spouse_hrms ON spouse_cadre_crosswalk(spouse_hrms);")
    c.execute("DELETE FROM spouse_cadre_crosswalk;")

    # Build active cadre index
    cadre_rows = c.execute("""
        SELECT hrms_id, officer_name, clean_name, designation, present_posting, establishment, district 
        FROM master_all_cadre_employees
    """).fetchall()

    cadre_index = []
    cadre_map_by_hrms = {}
    for row in cadre_rows:
        tokens = normalize_name_tokens(row['officer_name'])
        entry = {
            'hrms_id': row['hrms_id'],
            'name': row['officer_name'],
            'clean_name': row['clean_name'],
            'designation': row['designation'] or 'Cadre Officer',
            'present_posting': row['present_posting'] or '',
            'establishment': row['establishment'] or '',
            'district': row['district'] or '',
            'tokens': tokens,
            'token_set': set(tokens)
        }
        cadre_index.append(entry)
        cadre_map_by_hrms[row['hrms_id']] = entry

    # Also build map from cadre_1794_posts for post details
    post_rows = c.execute("""
        SELECT incumbent_hrms, designation, establishment, district, detailed_presentation 
        FROM cadre_1794_posts 
        WHERE incumbent_hrms IS NOT NULL AND incumbent_hrms != ''
    """).fetchall()
    post_map = {}
    for p in post_rows:
        post_map[p['incumbent_hrms']] = p

    # Query all officers with spouse details from officer_extended_dossier
    ext_rows = c.execute("""
        SELECT hrms_id, officer_name, present_district, spouse_name, spouse_dept, spouse_desig, spouse_district, spouse_is_wbahvs, spouse_service_details
        FROM officer_extended_dossier
        WHERE spouse_name IS NOT NULL AND spouse_name != ''
    """).fetchall()

    matched_count = 0
    now_ts = datetime.now().isoformat()

    for r in ext_rows:
        hid = r['hrms_id']
        
        # STRICT PRIVACY: Redact Nirmalya Ranjan Sarkar and Madhurima Sarkar
        if hid in TARGET_PRIVACY_IDS:
            continue

        off_name = r['officer_name']
        off_dist = (r['present_district'] or '').strip()
        sp_name_raw = r['spouse_name']
        sp_dept = (r['spouse_dept'] or '').strip()
        sp_tokens = normalize_name_tokens(sp_name_raw)

        if not sp_tokens or len(sp_tokens) < 2:
            continue
            
        sp_set = set(sp_tokens)

        # Candidate match in WBAH&VS Cadre
        matched_cadre = None
        for cand in cadre_index:
            if cand['hrms_id'] == hid or cand['hrms_id'] in TARGET_PRIVACY_IDS:
                continue
            
            # Exact token sequence
            if cand['tokens'] == sp_tokens:
                matched_cadre = cand
                break
            
            # First and Last token match
            if len(cand['tokens']) >= 2 and sp_tokens[0] == cand['tokens'][0] and sp_tokens[-1] == cand['tokens'][-1]:
                if sp_set.issubset(cand['token_set']) or cand['token_set'].issubset(sp_set):
                    matched_cadre = cand
                    break

        if matched_cadre:
            matched_count += 1
            sp_hrms = matched_cadre['hrms_id']
            sp_name_clean = matched_cadre['name']
            
            # Live posting from cadre_1794_posts if available, otherwise master_all_cadre_employees
            live_post = post_map.get(sp_hrms)
            if live_post:
                sp_desig = live_post['designation'] or matched_cadre['designation']
                sp_estab = live_post['establishment'] or matched_cadre['establishment']
                sp_dist = live_post['district'] or matched_cadre['district']
                sp_posting = live_post['detailed_presentation'] or matched_cadre['present_posting']
            else:
                sp_desig = matched_cadre['designation']
                sp_estab = matched_cadre['establishment']
                sp_dist = matched_cadre['district']
                sp_posting = matched_cadre['present_posting']

            is_same = 1 if (off_dist and sp_dist and off_dist.lower() == sp_dist.lower()) else 0

            c.execute("""
                INSERT INTO spouse_cadre_crosswalk (
                    officer_hrms, officer_name, officer_district,
                    spouse_name_raw, spouse_hrms, spouse_name,
                    spouse_current_designation, spouse_current_posting,
                    spouse_current_establishment, spouse_current_district,
                    is_same_district, match_confidence, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hid, off_name, off_dist,
                sp_name_raw, sp_hrms, sp_name_clean,
                sp_desig, sp_posting,
                sp_estab, sp_dist,
                is_same, 'Cadre-Verified', now_ts
            ))

            # Update officer_extended_dossier flag to 'Yes' and enrich service details
            co_loc_text = f"Co-located in {off_dist}" if is_same else f"Cross-District: {off_dist} ↔ {sp_dist}"
            dynamic_note = f"Dynamic Match: Spouse is {sp_name_clean} (HRMS: {sp_hrms}), serving as {sp_desig} at {sp_dist} ({co_loc_text}). Memo 291 Clause 7 Co-location safeguard applies."
            
            c.execute("""
                UPDATE officer_extended_dossier
                SET spouse_is_wbahvs = 'Yes',
                    spouse_name = ?,
                    spouse_service_details = ?
                WHERE hrms_id = ?
            """, (sp_name_clean, dynamic_note, hid))

    conn.commit()
    print(f"Successfully cross-linked {matched_count} married officer pairs in WBAH&VS Cadre!")

    # Verify sample crosswalk
    samples = c.execute("""
        SELECT officer_name, officer_district, spouse_name, spouse_current_district, is_same_district 
        FROM spouse_cadre_crosswalk 
        LIMIT 10
    """).fetchall()
    print("\nSample Verified Crosswalk Pairs:")
    for s in samples:
        status = "SAME DISTRICT" if s['is_same_district'] else "CROSS-DISTRICT"
        print(f"  {s['officer_name']} ({s['officer_district']}) <---> {s['spouse_name']} ({s['spouse_current_district']}) -> [{status}]")

    # Re-apply privacy redactions to ensure 100% guarantee
    for pid in TARGET_PRIVACY_IDS:
        c.execute("""
            UPDATE officer_extended_dossier
            SET mobile = NULL, alt_mobile = NULL, whatsapp = NULL, email = NULL,
                ancestral_address = NULL, ancestral_district = NULL,
                current_address = NULL, current_district = NULL, current_pin = NULL,
                temp_address = NULL, post_retirement_district = NULL,
                spouse_name = NULL, spouse_dept = NULL, spouse_desig = NULL,
                spouse_district = NULL, spouse_block = NULL, spouse_is_wbahvs = NULL,
                spouse_service_details = NULL, children_count = NULL, children_board_exams = NULL,
                family_dependencies = NULL, health_conditions = NULL, health_details = NULL,
                care_needed = NULL, facility_needed = NULL, pwd_status = NULL,
                spouse_health = NULL, association_remarks = NULL
            WHERE hrms_id = ?
        """, (pid,))
        c.execute("DELETE FROM spouse_cadre_crosswalk WHERE officer_hrms = ? OR spouse_hrms = ?", (pid, pid))

    conn.commit()
    conn.close()
    print("\n=== CLEANING & SPOUSE INTELLIGENCE COMPLETE ===")

if __name__ == '__main__':
    run()
