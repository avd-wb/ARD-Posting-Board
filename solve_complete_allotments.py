#!/usr/bin/env python3
import sqlite3
import openpyxl
import os

DB_PATH = 'ard_master_truth.db'
PREF_FILE = '/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /20260906 Posting Preferences.xlsx'

DIVISIONS = {
    'Presidency': ['Kolkata', 'North 24 Parganas', 'South 24 Parganas', 'Nadia', 'Howrah'],
    'Burdwan': ['Purba Bardhaman', 'Paschim Bardhaman', 'Birbhum', 'Hooghly'],
    'Medinipur': ['Paschim Medinipur', 'Purba Medinipur', 'Bankura', 'Jhargram'],
    'Malda': ['Malda', 'Murshidabad', 'Uttar Dinajpur', 'Dakshin Dinajpur'],
    'Jalpaiguri': ['Jalpaiguri', 'Alipurduar', 'Cooch Behar', 'Darjeeling', 'Kalimpong', 'Siliguri']
}

def get_cluster(district):
    if not district:
        return []
    d_clean = district.lower().strip()
    for div, dists in DIVISIONS.items():
        if any(d.lower() in d_clean or d_clean in d.lower() for d in dists):
            return dists
    return []

def load_google_form_preferences():
    prefs = {}
    if not os.path.exists(PREF_FILE):
        print(f'Preferences file not found: {PREF_FILE}')
        return prefs

    wb = openpyxl.load_workbook(PREF_FILE, read_only=True)
    sheet = wb.active
    for row in sheet.iter_rows(min_row=2, values_only=True):
        try:
            raw_hrms = row[10]
            if not raw_hrms:
                continue
            hrms = str(int(float(str(raw_hrms).strip())))
            
            dd_prefs = []
            for col_idx in [44, 45, 46, 47, 48, 49, 50, 51, 57, 58, 59, 60, 61, 62, 63, 64]:
                if col_idx < len(row) and row[col_idx] and str(row[col_idx]).strip():
                    dd_prefs.append(str(row[col_idx]).strip())
            
            gen_prefs = []
            for col_idx in [15, 18, 21, 24, 27, 30, 33, 36]:
                d_val = row[col_idx] if col_idx < len(row) else None
                e_val = row[col_idx+2] if col_idx+2 < len(row) else None
                if d_val or e_val:
                    gen_prefs.append(f"{d_val or ''} {e_val or ''}".strip())
                    
            home_dist = str(row[158]).strip() if len(row) > 158 and row[158] else ''
            
            prefs[hrms] = {
                'name': row[4],
                'dd_prefs': dd_prefs,
                'gen_prefs': gen_prefs,
                'home_dist': home_dist
            }
        except Exception:
            continue
            
    print(f'Loaded preferences for {len(prefs)} officers from Google Form.')
    return prefs

def solve_allotments():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    prefs_db = load_google_form_preferences()

    cur.execute("""
        SELECT dd_sl, district, establishment, office, post_name
        FROM available_dd_posts
        WHERE allotment_status = 'Available'
        ORDER BY dd_sl ASC
    """)
    available_dd = [dict(r) for r in cur.fetchall()]
    print(f'Initial available DD posts: {len(available_dd)}')

    cur.execute("""
        SELECT sl_no, roster_point, point_reserved_for, officer_name, hrms_id, caste,
               present_posting, present_block, present_district
        FROM roster_50_point_candidates
        WHERE substantive_post_name IS NULL
        ORDER BY sl_no ASC
    """)
    pending_roster = [dict(r) for r in cur.fetchall()]
    print(f'Pending roster candidates to allot: {len(pending_roster)}')

    allotted_count = 0

    for cand in pending_roster:
        hrms = str(cand['hrms_id']).strip()
        name = cand['officer_name']
        pres_dist = cand['present_district'] or ''
        cand_prefs = prefs_db.get(hrms, {})
        
        chosen_post = None
        match_reason = ''

        dd_prefs = cand_prefs.get('dd_prefs', [])
        for p in dd_prefs:
            p_lower = p.lower()
            for post in available_dd:
                p_dist = post['district'].lower()
                if (p_dist in p_lower or p_lower in p_dist) and any(k in p_lower for k in ['district', 'office', 'hq', 'farm', 'polyclinic', 'flf', 'slf']):
                    chosen_post = post
                    match_reason = f'Matched Stated DD Preference: {p}'
                    break
                elif p_dist in p_lower:
                    chosen_post = post
                    match_reason = f'Matched Stated DD District Preference: {post["district"]}'
                    break
            if chosen_post:
                break

        if not chosen_post:
            gen_prefs = cand_prefs.get('gen_prefs', [])
            for p in gen_prefs:
                p_lower = p.lower()
                for post in available_dd:
                    if post['district'].lower() in p_lower or p_lower in post['district'].lower():
                        chosen_post = post
                        match_reason = f'Matched General District Preference: {post["district"]}'
                        break
                if chosen_post:
                    break

        if not chosen_post and pres_dist:
            pres_dist_clean = pres_dist.lower().replace('district', '').strip()
            for post in available_dd:
                if pres_dist_clean in post['district'].lower() or post['district'].lower() in pres_dist_clean:
                    chosen_post = post
                    match_reason = f'Allocated in Present District: {post["district"]}'
                    break

        if not chosen_post and pres_dist:
            cluster = get_cluster(pres_dist)
            for neighbor in cluster:
                n_clean = neighbor.lower().strip()
                for post in available_dd:
                    if n_clean in post['district'].lower() or post['district'].lower() in n_clean:
                        chosen_post = post
                        match_reason = f'Allocated in Contiguous Division District: {post["district"]} (Home: {pres_dist})'
                        break
                if chosen_post:
                    break

        if not chosen_post and available_dd:
            chosen_post = available_dd[0]
            match_reason = f'Allocated Available Departmental Vacancy: {chosen_post["district"]}'

        if chosen_post:
            available_dd.remove(chosen_post)
            post_label = f"DD Sl {chosen_post['dd_sl']}: {chosen_post['post_name']} ({chosen_post['establishment']}, {chosen_post['district']})"
            
            cur.execute("""
                UPDATE roster_50_point_candidates
                SET substantive_post_id = ?,
                    substantive_post_name = ?,
                    allotment_status = 'ALLOTTED'
                WHERE hrms_id = ?
            """, (f"DD_{chosen_post['dd_sl']}", post_label, hrms))

            cur.execute("""
                UPDATE available_dd_posts
                SET allotment_status = 'Allotted',
                    allotted_hrms = ?,
                    allotted_name = ?
                WHERE dd_sl = ?
            """, (hrms, name, chosen_post['dd_sl']))

            cur.execute("""
                INSERT INTO simulation_assignments (
                    session_id, step_number, officer_hrms_id, officer_name,
                    from_post_id, from_post_name, to_post_id, to_post_name,
                    reason, substantive_post_id, substantive_post_name,
                    status, timestamp, officer_type
                ) VALUES (
                    'CURRENT_SESSION', ?, ?, ?,
                    'PRESENT', ?, ?, ?,
                    ?, ?, ?,
                    'CONFIRMED', datetime('now'), 'roster'
                )
            """, (
                cand['sl_no'], hrms, name,
                cand['present_posting'] or 'Present Post',
                f"DD_{chosen_post['dd_sl']}", post_label,
                match_reason, f"DD_{chosen_post['dd_sl']}", post_label
            ))

            allotted_count += 1

    print(f'Successfully allotted {allotted_count} remaining roster candidates into DD posts!')
    print(f'Remaining available DD posts: {len(available_dd)}')

    cur.execute("""
        SELECT oblit_sl, district, block, establishment, post_name, officer_name, hrms_id, is_on_roster
        FROM obliterated_posts_1808
        WHERE is_vacant = 'No' AND (substantive_post_name IS NULL OR substantive_post_name = '')
    """)
    unrehab_oblit = [dict(r) for r in cur.fetchall()]
    print(f'Serving obliterated officers needing rehabilitation: {len(unrehab_oblit)}')

    rehab_count = 0
    for ob in unrehab_oblit:
        hrms = str(ob['hrms_id']).strip()
        name = ob['officer_name']
        dist = ob['district'] or 'District HQ'
        
        cur.execute("SELECT substantive_post_name FROM roster_50_point_candidates WHERE hrms_id = ?", (hrms,))
        roster_row = cur.fetchone()
        if roster_row and roster_row[0]:
            sub_post = roster_row[0]
            rehab_label = f"Promoted to {sub_post}"
        else:
            rehab_label = f"Rehabilitated to Assistant Director, ARD (Active Cadre), {dist} District Office"

        cur.execute("""
            UPDATE obliterated_posts_1808
            SET substantive_post_name = ?,
                rehabilitation_status = 'REHABILITATED'
            WHERE hrms_id = ?
        """, (rehab_label, hrms))
        rehab_count += 1

    print(f'Successfully rehabilitated {rehab_count} serving obliterated officers!')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    solve_allotments()
