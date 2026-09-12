#!/usr/bin/env python3
"""
apply_executive_transfers_and_cascades.py
=========================================
Applies confirmed executive orders, regional assignments, 39 Stay allocations,
shifts from obliterated posts, 3-AD district HQ balancing, and marks Group C
cascading field vacancies in RED for urgent backfill.
"""

import sqlite3
import datetime

DB_PATH = "ard_master_truth.db"

def run_updates():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    timestamp = datetime.datetime.now().isoformat()
    session_id = "CURRENT_SESSION"

    print("--- 1. Applying 18 Specific Named Postings / Transfers ---")

    # 1. Dr. Prasanta Kumar Bera (2001001103): DVO Howrah -> AD, ARD (Vety.), HQ, Kolkata
    c.execute("""
        UPDATE obliterated_post_officers
        SET status = 'Rehabilitated',
            rehabilitated_post_id = 53,
            rehabilitated_post_name = 'Assistant Director, ARD (Veterinary), Directorate Headquarter, Kolkata'
        WHERE hrms_id = '2001001103'
    """)
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (Veterinary)',
            present_posting = 'Assistant Director, ARD (Veterinary), Directorate HQ, Salt Lake, Kolkata',
            district = 'Kolkata',
            is_hq_deployed = 1
        WHERE hrms_id = '2001001103'
    """)

    # 2. Dr. Pradip Pati (2000004209): AD Management Haringhata -> AD, ARD (Vety.), HQ, Kolkata
    c.execute("""
        UPDATE obliterated_post_officers
        SET status = 'Rehabilitated',
            rehabilitated_post_id = 54,
            rehabilitated_post_name = 'Assistant Director, ARD (Veterinary), Directorate Headquarter, Kolkata'
        WHERE hrms_id = '2000004209'
    """)
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (Veterinary)',
            present_posting = 'Assistant Director, ARD (Veterinary), Directorate HQ, Salt Lake, Kolkata',
            district = 'Kolkata',
            is_hq_deployed = 1
        WHERE hrms_id = '2000004209'
    """)

    # 3. Dr. Sukanta Roy (2012002908): AD VR&I N24Pgs -> AD, ARD (Vety.), HQ, Kolkata
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (Veterinary)',
            present_posting = 'Assistant Director, ARD (Veterinary), Directorate HQ, Salt Lake, Kolkata',
            district = 'Kolkata',
            is_hq_deployed = 1
        WHERE hrms_id = '2012002908'
    """)

    # 4. Dr. Debi Prasad Nandi (2000000354): BLDO Swarupnagar -> AD, ARD, North 24 Parganas SU as AD, ARD (Vety.), HQ, Kolkata
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD',
            present_posting = 'AD, ARD, North 24 Parganas [SU as AD, ARD (Vety.), HQ, Kolkata]',
            establishment = 'District Office, North 24 Parganas (SU: Directorate HQ)',
            is_hq_deployed = 1
        WHERE hrms_id = '2000000354'
    """)

    # 5. Dr. Nirmalya Ranjan Sarkar (2014000243): AD SA Hooghly -> AD, ARD, Hooghly SU as AD, ARD (Vety.), HQ, Kolkata
    c.execute("""
        UPDATE obliterated_post_officers
        SET status = 'Rehabilitated',
            rehabilitated_post_id = 1108,
            rehabilitated_post_name = 'Assistant Director, ARD, District Office, Hooghly [SU as AD, ARD (Vety.), HQ, Kolkata]'
        WHERE hrms_id = '2014000243'
    """)
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD',
            present_posting = 'AD, ARD, Hooghly [SU as AD, ARD (Vety.), HQ, Kolkata]',
            establishment = 'District Office, Hooghly (SU: Directorate HQ)',
            is_hq_deployed = 1
        WHERE hrms_id = '2014000243'
    """)

    # 7. Dr. Puspendu Panja (2005000825): AD Management Haringhata -> AD, ARD (Vety.), HQ, Kolkata
    c.execute("""
        UPDATE obliterated_post_officers
        SET status = 'Rehabilitated',
            rehabilitated_post_id = 55,
            rehabilitated_post_name = 'Assistant Director, ARD (Veterinary), Directorate Headquarter, Kolkata'
        WHERE hrms_id = '2005000825'
    """)
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (Veterinary)',
            present_posting = 'Assistant Director, ARD (Veterinary), Directorate HQ, Salt Lake, Kolkata',
            district = 'Kolkata',
            is_hq_deployed = 1
        WHERE hrms_id = '2005000825'
    """)

    # 8. Dr. (Smt.) Soma Das (nee Saha) (1995004945): AD Admin Howrah -> Deputy Director, ARD - Directorate Headquarter, Kolkata
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 1,
            substantive_post_name = 'DD Sl 1: Deputy Director, ARD (O/O the DAH & VS, W.B., Directorate Headquarters)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1995004945'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1995004945',
            allotted_name = 'Dr. (Smt.) Soma Das (nee Saha)'
        WHERE dd_sl = 1
    """)

    # 9. Dr. Kartick Chandra Roy (1997006910): BLDO Mathurapur-I -> Deputy Director, ARD - Directorate Headquarter, Kolkata
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 2,
            substantive_post_name = 'DD Sl 2: Deputy Director, ARD (O/O the DAH & VS, W.B., Directorate Headquarters)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1997006910'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1997006910',
            allotted_name = 'Dr. Kartick Chandra Roy'
        WHERE dd_sl = 2
    """)

    # 10. Dr. Banibrata Nayek (1999000493): BLDO Kulpi -> AD, ARD (Vety.), HQ, Kolkata
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (Veterinary)',
            present_posting = 'Assistant Director, ARD (Veterinary), Directorate HQ, Salt Lake, Kolkata',
            district = 'Kolkata',
            is_hq_deployed = 1
        WHERE hrms_id = '1999000493'
    """)

    # 11. Dr. Samir Patra (1995003969): VO Gocharan -> Deputy Director, ARD - Directorate Headquarter, Kolkata
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 3,
            substantive_post_name = 'DD Sl 3: Deputy Director, ARD (O/O the DAH & VS, W.B., Directorate Headquarters)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1995003969'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1995003969',
            allotted_name = 'Dr. Samir Patra'
        WHERE dd_sl = 3
    """)

    # 12. Dr. Chayan Bhattacharya (1995000104): AD Vety HQ -> Deputy Director, Haringhata Farm, Nadia
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 35,
            substantive_post_name = 'DD Sl 35: Deputy Director, ARD (O/O the Additional Director, ARD, Haringhata Farm)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1995000104'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1995000104',
            allotted_name = 'Dr. Chayan Bhattacharya'
        WHERE dd_sl = 35
    """)

    # 13. Dr. Shuvendu Halder (1998000164): AD Vety HQ -> VO, BAHC, Kalna-II, Purba Bardhaman
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Veterinary Officer, BAHC',
            present_posting = 'Veterinary Officer, BAHC, Kalna-II, Purba Bardhaman',
            district = 'Purba Bardhaman',
            establishment = 'BLDO, Kalna-II, Purba Bardhaman',
            is_hq_deployed = 0
        WHERE hrms_id = '1998000164'
    """)
    c.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Shuvendu Halder',
            incumbent_hrms = '1998000164',
            occupancy_status = 'Occupied'
        WHERE id = 1230
    """)

    # 14. Dr. Madhusudan Mukherjee (2001001523): VO Kalna-II -> AD, ARD (Vety.), HQ, Kolkata SU at WBLDCL, HQ as Manager (HR)
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (Veterinary)',
            present_posting = 'AD, ARD (Vety.), HQ, Kolkata [SU at WBLDCL, HQ as Manager (HR)]',
            establishment = 'Directorate of AR & AH, HQ (SU: WBLDCL HQ)',
            district = 'Kolkata',
            is_hq_deployed = 1
        WHERE hrms_id = '2001001523'
    """)

    # 15. Dr. Partha Sarathi Chattopadhyay (2001000022): SU at WBLDCL withdrawn -> BLDO, Ratua-I, Malda
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Block Livestock Development Officer',
            present_posting = 'Block Livestock Development Officer, Ratua-I, Malda',
            establishment = 'BLDO Office, Ratua-I, Malda',
            district = 'Malda',
            is_hq_deployed = 0
        WHERE hrms_id = '2001000022'
    """)
    c.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Partha Sarathi Chattopadhyay',
            incumbent_hrms = '2001000022',
            occupancy_status = 'Occupied'
        WHERE id = 643
    """)

    # 16. Dr. Dipak Dey (2019018249): BLDO Ratua-I -> AD, ARD (Vety.), Dte. HQ SU at WBLDCL, HQ (Marketing)
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (Veterinary)',
            present_posting = 'AD, ARD (Vety.), Dte. HQ [SU at WBLDCL, HQ (Marketing)]',
            establishment = 'Directorate of AR & AH, HQ (SU: WBLDCL HQ)',
            district = 'Kolkata',
            is_hq_deployed = 1
        WHERE hrms_id = '2019018249'
    """)

    # 17. Dr. Santanu Nandi (2011000171): SU at WBLDCL withdrawn -> BLDO, Bangaon, North 24 Parganas
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Block Livestock Development Officer',
            present_posting = 'Block Livestock Development Officer, Bangaon, North 24 Parganas',
            establishment = 'BLDO Office, Bangaon, North 24 Parganas',
            district = 'North 24 Parganas',
            is_hq_deployed = 0
        WHERE hrms_id = '2011000171'
    """)
    c.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Santanu Nandi',
            incumbent_hrms = '2011000171',
            occupancy_status = 'Occupied'
        WHERE id = 870
    """)

    # 18. Dr. Sumit Chowdhury (2005000244): AD Vety HQ -> AD, ARD (VR&I), IAH&VB, Belgachia, Kolkata
    c.execute("""
        UPDATE master_all_cadre_employees
        SET designation = 'Assistant Director, ARD (VR&I)',
            present_posting = 'Assistant Director, ARD (VR&I), IAH&VB, Belgachia, Kolkata',
            establishment = 'IAH&VB, 37 Belgachia Road, Kolkata',
            district = 'Kolkata',
            is_hq_deployed = 0
        WHERE hrms_id = '2005000244'
    """)

    print("--- 2. Applying 5 Regional Decisions (Handwritten & Text Notes) ---")

    # Sl 60: Dr. Rabindra Nath Hansda (1998007220) -> Deputy Director, Jhargram
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 232,
            substantive_post_name = 'DD Sl 232: Deputy Director, ARD (District Office, Jhargram)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1998007220'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1998007220',
            allotted_name = 'Dr. Rabindra Nath Hansda'
        WHERE dd_sl = 232
    """)

    # Sl 138: Dr. Raju Das (1997000337) -> Deputy Director, Malda
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 132,
            substantive_post_name = 'DD Sl 132: Deputy Director, ARD (District Office, Malda)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1997000337'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1997000337',
            allotted_name = 'Dr. Raju Das'
        WHERE dd_sl = 132
    """)

    # Sl 199: Dr. Tapan Kumar Sur (2000000755) -> Deputy Director / Joint Director Charge, Jalpaiguri
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 97,
            substantive_post_name = 'DD Sl 97: Deputy Director, ARD (District Office, Jalpaiguri - Joint Director Charge)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '2000000755'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '2000000755',
            allotted_name = 'Dr. Tapan Kumar Sur'
        WHERE dd_sl = 97
    """)

    # Sl 228: Dr. Swapan Kumar Dass (2001000684) -> Deputy Director, Alipurduar
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 104,
            substantive_post_name = 'DD Sl 104: Deputy Director, ARD (District Office, Alipurduar)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '2001000684'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '2001000684',
            allotted_name = 'Dr. Swapan Kumar Dass'
        WHERE dd_sl = 104
    """)

    # Sl 239: Dr. Debasish Dutta (1994005981) -> Deputy Director / Joint Director Charge, Siliguri
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 94,
            substantive_post_name = 'DD Sl 94: Deputy Director, ARD (O/O the JD ARD, Siliguri - Joint Director Charge)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1994005981'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1994005981',
            allotted_name = 'Dr. Debasish Dutta'
        WHERE dd_sl = 94
    """)

    print("--- 3. Resolving 5 'Stay' Officers previously seated on Obliterated Posts ---")

    # Candidate #13: Dr. Some Nath Bhattacharjee (1992000815) -> DD Birbhum District Office (Active post)
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 203,
            substantive_post_name = 'DD Sl 203: Deputy Director, ARD (District Office, Birbhum)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1992000815'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1992000815',
            allotted_name = 'Dr. Some Nath Bhattacharjee'
        WHERE dd_sl = 203
    """)

    # Candidate #20: Dr. Samar Kumar Ghosh (1992003924) -> DD Haringhata Farm (Active post)
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 36,
            substantive_post_name = 'DD Sl 36: Deputy Director, ARD (O/O the Additional Director, ARD, Haringhata Farm)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1992003924'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1992003924',
            allotted_name = 'Dr. Samar Kumar Ghosh'
        WHERE dd_sl = 36
    """)

    # Candidate #31: Dr. Debasis Jana (1992000156) -> DD Nadia District Office (Active post)
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 146,
            substantive_post_name = 'DD Sl 146: Deputy Director, ARD (District Office, Nadia)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1992000156'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1992000156',
            allotted_name = 'Dr. Debasis Jana'
        WHERE dd_sl = 146
    """)

    # Candidate #50: Dr. Tapan Sadhukhan (1993000949) -> DD Hooghly District Office (Active post)
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 181,
            substantive_post_name = 'DD Sl 181: Deputy Director, ARD (District Office, Hooghly)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1993000949'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1993000949',
            allotted_name = 'Dr. Tapan Sadhukhan'
        WHERE dd_sl = 181
    """)

    # Candidate #75: Dr. Subrata Samanta (1994000068) -> DD Murshidabad District Office (Active post)
    c.execute("""
        UPDATE roster_50_point_candidates
        SET substantive_post_id = 138,
            substantive_post_name = 'DD Sl 138: Deputy Director, ARD (District Office, Murshidabad)',
            su_post_id = NULL,
            su_post_name = NULL,
            allotment_status = 'Allotted'
        WHERE hrms_id = '1994000068'
    """)
    c.execute("""
        UPDATE available_dd_posts
        SET allotment_status = 'Allotted',
            allotted_hrms = '1994000068',
            allotted_name = 'Dr. Subrata Samanta'
        WHERE dd_sl = 138
    """)

    print("--- 4. Registering simulation_assignments for all confirmed updates ---")

    all_assigned_candidates = c.execute("""
        SELECT sl_no, roster_point, officer_name, hrms_id, present_posting, present_district,
               substantive_post_id, substantive_post_name, su_post_id, su_post_name
        FROM roster_50_point_candidates
        WHERE substantive_post_id IS NOT NULL
    """).fetchall()

    for cand in all_assigned_candidates:
        c.execute("""
            INSERT OR REPLACE INTO simulation_assignments (
                session_id, officer_hrms_id, officer_name, from_post_id, from_post_name,
                to_post_id, to_post_name, substantive_post_id, substantive_post_name,
                su_post_id, su_post_name, officer_type, reason, timestamp
            ) VALUES (
                :session_id, :hrms_id, :name, 0, :from_post,
                :to_post_id, :to_post_name, :sub_id, :sub_name,
                :su_id, :su_name, 'roster', 'Confirmed Executive Cadre Promotion / Placement', :ts
            )
        """, {
            "session_id": session_id,
            "hrms_id": cand["hrms_id"],
            "name": cand["officer_name"],
            "from_post": f"{cand['present_posting']} ({cand['present_district']})",
            "to_post_id": cand["substantive_post_id"],
            "to_post_name": cand["substantive_post_name"],
            "sub_id": cand["substantive_post_id"],
            "sub_name": cand["substantive_post_name"],
            "su_id": cand["su_post_id"],
            "su_name": cand["su_post_name"],
            "ts": timestamp
        })

    print("--- 5. Flagging Group C Cascading Field Vacancies in RED ---")

    c.execute("""
        UPDATE officer_extended_dossier
        SET needs_backfill = 0,
            attention_flag = 0
    """)

    field_moves = c.execute("""
        SELECT r.hrms_id, r.officer_name, r.present_posting, r.present_district,
               r.substantive_post_name, r.su_post_name
        FROM roster_50_point_candidates r
        WHERE r.substantive_post_id IS NOT NULL
          AND (r.su_post_id IS NULL OR r.su_post_name NOT LIKE '%' || r.present_posting || '%')
          AND (r.present_posting LIKE '%BLDO%' OR r.present_posting LIKE '%BAHC%' OR r.present_posting LIKE '%SAHC%')
    """).fetchall()

    print(f"Total vacated field posts flagged for backfill: {len(field_moves)}")
    for fm in field_moves:
        c.execute("""
            INSERT INTO officer_extended_dossier (
                hrms_id, officer_name, needs_backfill, attention_flag, attention_reason
            ) VALUES (
                :hrms_id, :name, 1, 1, :reason
            )
            ON CONFLICT(hrms_id) DO UPDATE SET
                needs_backfill = 1,
                attention_flag = 1,
                attention_reason = :reason
        """, {
            "hrms_id": fm["hrms_id"],
            "name": fm["officer_name"],
            "reason": f"⚠️ Group C Cascading Warning: Officer transferred to {fm['substantive_post_name']}. Field post '{fm['present_posting']}' must be backfilled!"
        })

    conn.commit()
    conn.close()
    print("Database updates successfully applied!")

if __name__ == "__main__":
    run_updates()
