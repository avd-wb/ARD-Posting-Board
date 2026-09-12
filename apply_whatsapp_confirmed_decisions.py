#!/usr/bin/env python3
"""
apply_whatsapp_confirmed_decisions.py
Applies executive transfer, promotion, and rehabilitation decisions from user WhatsApp update:
- DDDARD Howrah: Gouri Sankar Hatui, Amit Chalki (Uluberia)
- AD Howrah: Utpal Sinha, Prabir Santra (DEO)
- S24 Pgs: Nishith Panda (in-charge Jt. Director), Ujjwal Kr. Bag
- N24 Pgs: Dr. Sabin Majumder (BLDO Swarupnagar)
- North 24 Deputy: Rajkumar Maity (Jt. Charge), Sanjoy Bose, Basudev Sil,
                   Bidhan Bala (SU Habra-I BLDO), Tapan Bhattacharya (SU AD VR&I Basirhat),
                   Biplab Dasgupta (SU BLDO Deganga)
- AD North 24 Pgs: Jayanta Dutta, Sandip Choudhary (AD VR&I Barasat),
                   Sanat Sarkar (AD Directorate, SU North 24 Pgs),
                   Nabadwip Sarkar (transfer to BLDO Barasat-II)
- Lateral Transfers: Sanjay Ghatak (BLDO Katwa-I, Purba Bardhaman),
                     Abhradip Majumdar (VO ABAHC Barasat-I),
                     Palash Biswas (BLDO Gaighata),
                     Srimanta Sarkar (BLDO Rajarhat),
                     Prasanta Pal (BLDO Tarakeswar),
                     Kalidas Banerjee (SAHC Arambagh),
                     Ranjit Panja (VO ABAHC Tamluk, Purba Medinipur),
                     Chandan Das (SAHC Kharagpur / Salboni, Paschim Medinipur as per prayer)
"""

import sqlite3

DB_PATH = 'ard_master_truth.db'

def apply_decisions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=== APPLYING WHATSAPP CONFIRMED EXECUTIVE DECISIONS ===")

    # -------------------------------------------------------------------------
    # 1. Update 50-Point Roster Candidates
    # -------------------------------------------------------------------------
    roster_updates = [
        # (hrms_id, sub_id, sub_name, su_name)
        ("1994000104", 156, "DD Sl 156: Deputy Director, ARD (North 24 Parganas)", "[Additional Charge] Joint Director, ARD, North 24 Parganas (Post 846)"),
        ("1995000219", 157, "DD Sl 157: Deputy Director, ARD (North 24 Parganas)", None),
        ("1992001867", 158, "DD Sl 158: Deputy Director, ARD (North 24 Parganas)", None),
        ("1992004588", 159, "DD Sl 159: Deputy Director, ARD (North 24 Parganas)", "[SU] Block Livestock Development Officer, Habra-I (Post 866)"),
        ("1992000961", 160, "DD Sl 160: Deputy Director, ARD (North 24 Parganas)", "[SU] Assistant Director, ARD (VR&I), Pathological cum Diagnostic Laboratory at Basirhat (Post 930)"),
        ("1995006049", 161, "DD Sl 161: Deputy Director, ARD (North 24 Parganas)", "[SU] Block Livestock Development Officer, Deganga (Post 870)"),
        ("1994000172", 162, "DD Sl 162: Deputy Director, ARD (North 24 Parganas)", "[SU] Block Livestock Development Officer, Swarupnagar (Post 869)"),
        
        ("1994000623", 174, "DD Sl 174: Deputy Director, ARD (O/O the JD ARD, Howrah)", None),
        ("1995000678", 175, "DD Sl 175: Deputy Director, ARD (O/O the JD ARD, Howrah)", "[SU] Block Livestock Development Officer, Uluberia-I (Post 1084)"),
        
        ("2001001132", 170, "DD Sl 170: Deputy Director, ARD (South 24 Parganas)", None),
        ("1997000295", 211, "DD Sl 211: Deputy Director, ARD (O/O the JD ARD, Bankura)", "[SU] Block Livestock Development Officer, Rajarhat (Post 878)"),

        # Relocating displaced officers cleanly to vacated DD posts
        ("1992000321", 41, "DD Sl 41: Deputy Director, ARD (I.A.H. & V.B., (R. & T.))", None),
        ("1992000077", 4, "DD Sl 4: Deputy Director, ARD (O/O the DAH & VS, W.B., Directorate Headquarters)", None),
        ("1994004985", 25, "DD Sl 25: Deputy Director, ARD (Directorate Headquarters)", None),
        ("1995000290", 227, "DD Sl 227: Deputy Director, ARD (O/O the JD ARD, Paschim Medinipur)", None),
        ("1994000265", 239, "DD Sl 239: Deputy Director, ARD (O/O the JD ARD, Purba Medinipur)", None),
        ("1994001091", 115, "DD Sl 115: Deputy Director, ARD (Cooch Behar, Cooch Behar)", None),
        ("1994000920", 84, "DD Sl 84: Deputy Director, ARD (O/O the JD ARD, Kalimpong)", None),
        ("2016000128", 64, "DD Sl 64: Deputy Director, ARD (O/O the Additional Director, ARD, Set up of North Bengal)", None),
    ]

    for hid, sub_id, sub_name, su_name in roster_updates:
        cur.execute("""
            UPDATE roster_50_point_candidates
            SET substantive_post_id = ?,
                substantive_post_name = ?,
                su_post_name = ?,
                allotment_status = 'Allotted'
            WHERE hrms_id = ?
        """, (sub_id, sub_name, su_name, hid))
        print(f"  Roster: Updated HRMS {hid} -> {sub_name} (SU: {su_name})")

    # -------------------------------------------------------------------------
    # 2. Update available_dd_posts Table
    # -------------------------------------------------------------------------
    cur.execute("SELECT hrms_id, officer_name, substantive_post_id, substantive_post_name FROM roster_50_point_candidates WHERE substantive_post_id IS NOT NULL")
    all_allotted_roster = cur.fetchall()
    
    cur.execute("UPDATE available_dd_posts SET allotment_status = 'Available', allotted_hrms = NULL, allotted_name = NULL WHERE is_blocked_vigilance = 0")
    for r in all_allotted_roster:
        cur.execute("""
            UPDATE available_dd_posts
            SET allotment_status = 'Allotted',
                allotted_hrms = ?,
                allotted_name = ?
            WHERE dd_sl = ?
        """, (r['hrms_id'], r['officer_name'], r['substantive_post_id']))

    print("  Available DD Posts: Synchronized all 242 DD post assignments.")

    # -------------------------------------------------------------------------
    # 3. Update Obliterated Posts (Memo 1808)
    # -------------------------------------------------------------------------
    cur.execute("""
        UPDATE obliterated_posts_1808
        SET substantive_post_name = 'Joint Director, ARD (in-charge), South 24 Parganas (Post 932)',
            su_post_name = 'In-charge Joint Director, South 24 Parganas',
            rehabilitation_status = 'Rehabilitated'
        WHERE hrms_id = '1996001878'
    """)
    print("  Obliterated: Dr. Nisith Kumar Panda -> In-charge Joint Director, South 24 Parganas (Post 932)")

    cur.execute("""
        UPDATE obliterated_posts_1808
        SET substantive_post_name = 'Assistant Director, ARD (Directorate Headquarter, Salt Lake)',
            su_post_name = '[SU] North 24 Parganas District Office',
            rehabilitation_status = 'Rehabilitated'
        WHERE hrms_id = '2001000187'
    """)
    print("  Obliterated: Dr. Sanat Sarkar -> AD Directorate, SU North 24 Parganas")

    cur.execute("""
        UPDATE obliterated_posts_1808
        SET substantive_post_name = 'Block Livestock Development Officer, Barasat-II (Post 882)',
            su_post_name = NULL,
            rehabilitation_status = 'Rehabilitated'
        WHERE hrms_id = '2012003854'
    """)
    print("  Obliterated: Dr. Nabadwip Kumar Sarkar -> BLDO Barasat-II (Post 882)")

    # -------------------------------------------------------------------------
    # 4. Executive Lateral Transfers & Field Postings Table
    # -------------------------------------------------------------------------
    cur.execute("DROP TABLE IF EXISTS executive_lateral_transfers")
    cur.execute("""
        CREATE TABLE executive_lateral_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sl_no INTEGER,
            hrms_id TEXT,
            officer_name TEXT,
            present_posting TEXT,
            transferred_post_name TEXT,
            district_from TEXT,
            district_to TEXT,
            transfer_type TEXT,
            reason_notes TEXT
        )
    """)

    lateral_transfers = [
        (1, "1996001878", "Dr. Nisith Kumar Panda", "District Veterinary Officer, South 24 Parganas", "Joint Director, ARD (in-charge), South 24 Parganas (Post 932)", "South 24 Parganas", "South 24 Parganas", "Executive Elevation", "In-charge Joint Director, South 24 Parganas"),
        (2, "2011000454", "Dr. Utpal Kumar Singha", "Assistant Director of Animal Resources Development (DI), Howrah", "Assistant Director, ARD, Howrah (Post 1079)", "Howrah", "Howrah", "Cadre Confirmation", "Confirmed as Assistant Director, ARD, Howrah"),
        (3, "1998005468", "Dr. Prabir Kumar Santra", "Assistant Director of Animal Resources Development (VR&I), Howrah", "Assistant Director, ARD (DEO), Howrah (Post 1080)", "Howrah", "Howrah", "Cadre Confirmation", "Confirmed as Assistant Director, ARD (DEO), Howrah"),
        (4, "1997000142", "Dr. Jayanta Datta", "Assistant Director of Animal Resources Development, North 24 Parganas", "Assistant Director, ARD, North 24 Parganas (Post 852)", "North 24 Parganas", "North 24 Parganas", "Cadre Confirmation", "Confirmed as Assistant Director, ARD, North 24 Parganas"),
        (5, "2001002253", "Dr. Sandip Chaudhury", "Assistant Director of Animal Resources Development (DI), North 24 Parganas", "Assistant Director, ARD (VR&I), Barasat, North 24 Parganas (Post 853)", "North 24 Parganas", "North 24 Parganas", "Cadre Confirmation", "Confirmed as Assistant Director, ARD (VR&I), Barasat"),
        (6, "2001000187", "Dr. Sanat Sarkar", "AD ARD (C&DD), North 24 Parganas [SU PBGSBS]", "Assistant Director, ARD (Directorate HQ, Salt Lake) [SU at North 24 Parganas]", "Kolkata", "North 24 Parganas", "Rehabilitation & SU", "Substantive at Directorate HQ, Service Utilized at North 24 Parganas"),
        (7, "2012003854", "Dr. Nabadwip Kumar Sarkar", "AD ARD (Admin), North 24 Parganas", "Block Livestock Development Officer, Barasat-II, North 24 Parganas (Post 882)", "North 24 Parganas", "North 24 Parganas", "Rehabilitation Transfer", "Absorbed into clear vacant BLDO post at Barasat-II"),
        (8, "1998001826", "Dr. Sanjay Ghatak", "Assistant Director, ARD (SA), North 24 Parganas", "Block Livestock Development Officer, Katwa-I, Purba Bardhaman (Post 1213)", "North 24 Parganas", "Purba Bardhaman", "Field Transfer", "Transferred to vacant BLDO post in Purba Bardhaman"),
        (9, "2019003929", "Dr. Abhradip Majumder", "Veterinary Officer, BLDO Coochbehar-II", "Veterinary Officer, ABAHC Barasat-I, North 24 Parganas (Post 912)", "Cooch Behar", "North 24 Parganas", "Inter-District Transfer", "Transferred to VO ABAHC Barasat-I"),
        (10, "2019012934", "Dr. Palash Biswas", "Veterinary Officer, ABAHC Tufanganj-I", "Block Livestock Development Officer, Gaighata, North 24 Parganas (Post 871)", "Cooch Behar", "North 24 Parganas", "Inter-District Transfer", "Transferred from VO ABAHC Tufanganj to BLDO Gaighata"),
        (11, "2005000472", "Dr. Prasanta Pal", "Block Livestock Development Officer, Rajarhat, North 24 Parganas", "Block Livestock Development Officer, Tarakeswar, Hooghly (Post 1131)", "North 24 Parganas", "Hooghly", "Inter-District Transfer", "Transferred from BLDO Rajarhat to vacant BLDO Tarakeswar, freeing Rajarhat for Dr. Srimanta Sarkar"),
        (12, "2001000032", "Dr. Kalidas Banerjee", "Block Livestock Development Officer, Hirbandh, Bankura", "Veterinary Officer, SAHC Arambagh, Hooghly (Post 1132)", "Bankura", "Hooghly", "Inter-District Transfer", "Transferred from BLDO Hirbandh to SAHC Arambagh"),
        (13, "2001001503", "Dr. Ranjit Kumar Panja", "Block Livestock Development Officer, Beldanga-II, Murshidabad", "Veterinary Officer, ABAHC Tamluk, Purba Medinipur (Post 1790)", "Murshidabad", "Purba Medinipur", "Transfer on Prayer", "Transferred to Purba Medinipur as per prayer"),
        (14, "2000003056", "Dr. Chandan Kumar Das", "Block Livestock Development Officer, Uluberia-II, Howrah", "Veterinary Officer, SAHC Kharagpur / Salboni, Paschim Medinipur (Post 201 / 1617)", "Howrah", "Paschim Medinipur", "Transfer on Prayer", "Transferred to Paschim Medinipur as per prayer (Home district / health)")
    ]

    for row in lateral_transfers:
        cur.execute("""
            INSERT INTO executive_lateral_transfers (
                sl_no, hrms_id, officer_name, present_posting, transferred_post_name,
                district_from, district_to, transfer_type, reason_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)
        print(f"  Lateral: [{row[0]}] {row[2]} ({row[1]}) -> {row[4]}")

    # -------------------------------------------------------------------------
    # 5. Update cadre_1794_posts Incumbents & SU Markers
    # -------------------------------------------------------------------------
    cur.execute("""
        UPDATE cadre_1794_posts
        SET detailed_presentation = 'Joint Director, ARD, District Office, North 24 Parganas [Held by Dr. Rajkumar Maity on additional charge]',
            su_allotted_name = 'Dr. Rajkumar Maity (Joint Charge)',
            su_allotted_hrms = '1994000104'
        WHERE post_sl = 846
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Nisith Kumar Panda',
            incumbent_hrms = '1996001878',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Nisith Kumar Panda (1996001878) — Joint Director, ARD (in-charge), South 24 Parganas'
        WHERE post_sl = 932
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Nabadwip Kumar Sarkar',
            incumbent_hrms = '2012003854',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Nabadwip Kumar Sarkar (2012003854) — Block Livestock Development Officer, Barasat-II, North 24 Parganas'
        WHERE post_sl = 882
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Sanjay Ghatak',
            incumbent_hrms = '1998001826',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Sanjay Ghatak (1998001826) — Block Livestock Development Officer, Katwa-I, Purba Bardhaman'
        WHERE post_sl = 1213
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Prasanta Pal',
            incumbent_hrms = '2005000472',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Prasanta Pal (2005000472) — Block Livestock Development Officer, Tarakeswar, Hooghly'
        WHERE post_sl = 1131
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET su_allotted_name = 'Dr. Srimanta Sarkar',
            su_allotted_hrms = '1997000295',
            detailed_presentation = 'Dr. Srimanta Sarkar (1997000295) — Block Livestock Development Officer, Rajarhat, North 24 Parganas [SU on Promotion to DD Bankura]'
        WHERE post_sl = 878
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Kalidas Banerjee',
            incumbent_hrms = '2001000032',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Kalidas Banerjee (2001000032) — Veterinary Officer, SAHC Arambagh, Hooghly'
        WHERE post_sl = 1132
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Abhradip Majumder',
            incumbent_hrms = '2019003929',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Abhradip Majumder (2019003929) — Veterinary Officer, ABAHC Barasat-I, North 24 Parganas'
        WHERE post_sl = 912
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Palash Biswas',
            incumbent_hrms = '2019012934',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Palash Biswas (2019012934) — Block Livestock Development Officer, Gaighata, North 24 Parganas'
        WHERE post_sl = 871
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Ranjit Kumar Panja',
            incumbent_hrms = '2001001503',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Ranjit Kumar Panja (2001001503) — Veterinary Officer, ABAHC Tamluk, Purba Medinipur'
        WHERE post_sl = 1790
    """)

    cur.execute("""
        UPDATE cadre_1794_posts
        SET incumbent_name = 'Dr. Chandan Kumar Das',
            incumbent_hrms = '2000003056',
            occupancy_status = 'Occupied',
            detailed_presentation = 'Dr. Chandan Kumar Das (2000003056) — Assistant Director / VO, Paschim Medinipur'
        WHERE post_sl = 201
    """)

    conn.commit()
    conn.close()
    print("\nAll WhatsApp executive decisions applied successfully to ard_master_truth.db!")

if __name__ == '__main__':
    apply_decisions()
