import os
import sqlite3
import openpyxl
import pandas as pd
import datetime
import re

BASE_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DB_PATH = os.path.join(BASE_DIR, "ard_master_truth.db")
LIVE_EXCEL_PATH = "/private/tmp/claude-501/-Users-nirmalyaranjansarkar-Projects-AVD/8bac7a1a-c747-41be-8e3e-6ac9335e725d/scratchpad/LIVE_sheet.xlsx"
AVD_APP_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD/02_Correspondence_AVD/AVD Communications/Contacts_AVD/20260608 1441 AVD application.xlsx"
HRMS_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD/03_ARD_HR/Source from HRMS/HRMS_ARD_20260908.tsv"

def ingest():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Create or ensure officer_extended_dossier table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS officer_extended_dossier (
        hrms_id TEXT PRIMARY KEY,
        officer_name TEXT,
        mobile TEXT,
        whatsapp TEXT,
        email TEXT,
        wbvc_reg_no TEXT,
        office_code TEXT,
        ddo_code TEXT,
        cadre TEXT,
        posting_history TEXT,
        ancestral_address TEXT,
        current_address TEXT,
        spouse_service_details TEXT,
        family_dependencies TEXT,
        academic_details TEXT,
        decision_note TEXT,
        needs_backfill INTEGER DEFAULT 0,
        attention_flag INTEGER DEFAULT 0,
        attention_reason TEXT
    )
    """)
    conn.commit()

    # 2. Load Contact Info from AVD application
    contacts = {}
    if os.path.exists(AVD_APP_PATH):
        try:
            app_wb = openpyxl.load_workbook(AVD_APP_PATH, data_only=True)
            app_ws = app_wb.active
            for r in range(2, app_ws.max_row + 1):
                hrms_val = app_ws.cell(r, 9).value
                if hrms_val:
                    try:
                        hid = str(int(float(str(hrms_val).strip())))
                        contacts[hid] = {
                            "mobile": str(app_ws.cell(r, 6).value or "").strip(),
                            "whatsapp": str(app_ws.cell(r, 7).value or "").strip(),
                            "email": str(app_ws.cell(r, 8).value or "").strip(),
                            "wbvc": str(app_ws.cell(r, 10).value or "").strip()
                        }
                    except Exception:
                        pass
            print(f"Loaded {len(contacts)} contacts from AVD applications.")
        except Exception as e:
            print("Error loading contacts:", e)

    # 3. Load HRMS details
    hrms_details = {}
    if os.path.exists(HRMS_PATH):
        try:
            df_hrms = pd.read_csv(HRMS_PATH, sep='\t', dtype=str)
            for _, row in df_hrms.iterrows():
                hid = str(row['hrms']).strip()
                hrms_details[hid] = {
                    "office_code": str(row.get('office_code') or '').strip(),
                    "ddo_code": str(row.get('ddo') or '').strip(),
                    "cadre": str(row.get('cadre') or 'West Bengal Animal Husbandry and Veterinary Service').strip()
                }
            print(f"Loaded {len(hrms_details)} records from HRMS TSV.")
        except Exception as e:
            print("Error loading HRMS TSV:", e)

    # 4. Load decisions & history from LIVE_sheet.xlsx
    wb = openpyxl.load_workbook(LIVE_EXCEL_PATH, data_only=True)
    ws = wb['PROMOTION LIST']

    # Pre-fetch available DD posts map by district
    cur.execute("SELECT dd_sl, district, office, post_name FROM available_dd_posts WHERE is_blocked_vigilance = 0")
    dd_posts = cur.fetchall()

    # Pre-fetch cadre 1,794 posts
    cur.execute("SELECT id, district, block, establishment, designation, occupancy_status, incumbent_hrms FROM cadre_1794_posts")
    cadre_posts = cur.fetchall()

    # Pre-fetch obliterated post officers
    cur.execute("SELECT hrms_id FROM obliterated_posts_1808")
    obliterated_hrms_set = set(r[0] for r in cur.fetchall() if r[0])

    allocated_dd_sls = set()
    cur.execute("SELECT substantive_post_id FROM simulation_assignments WHERE session_id = 'CURRENT_SESSION' AND substantive_post_id IS NOT NULL")
    for r in cur.fetchall():
        try:
            allocated_dd_sls.add(int(r[0]))
        except Exception:
            pass

    def get_district_dd_post(dist):
        dist_clean = (dist or "").strip().lower()
        for p in dd_posts:
            if p[0] not in allocated_dd_sls and p[1].lower() in dist_clean:
                allocated_dd_sls.add(p[0])
                return p
        # Fallback to any unallocated DD post
        for p in dd_posts:
            if p[0] not in allocated_dd_sls:
                allocated_dd_sls.add(p[0])
                return p
        return None

    def get_cadre_post_by_text(text, dist=None):
        t = (text or "").lower()
        for cp in cadre_posts:
            cp_id, cp_dist, cp_block, cp_est, cp_desig, cp_occ, cp_inc = cp
            c_text = f"{cp_desig} {cp_est} {cp_block} {cp_dist}".lower()
            if dist and cp_dist.lower() != dist.lower():
                continue
            if t in c_text:
                return cp
        # If not found with dist, search all
        for cp in cadre_posts:
            cp_id, cp_dist, cp_block, cp_est, cp_desig, cp_occ, cp_inc = cp
            c_text = f"{cp_desig} {cp_est} {cp_block} {cp_dist}".lower()
            if t in c_text:
                return cp
        return None

    total_candidates = 0
    total_dossiers_created = 0
    total_allotments_done = 0

    session_id = "CURRENT_SESSION"

    for r in range(2, ws.max_row + 1):
        sl = ws.cell(r, 1).value
        name = ws.cell(r, 2).value
        hrms_val = ws.cell(r, 3).value
        if not hrms_val or not name:
            continue

        try:
            hrms = str(int(float(str(hrms_val).strip())))
        except Exception:
            hrms = str(hrms_val).strip()

        history = str(ws.cell(r, 10).value or "").strip()
        ancestral = str(ws.cell(r, 14).value or "").strip()
        current_addr = str(ws.cell(r, 15).value or "").strip()
        present_post_raw = str(ws.cell(r, 11).value or "").strip()
        present_district = str(ws.cell(r, 13).value or "").strip()
        dec_note = str(ws.cell(r, 30).value or "").strip()

        # Contact & HRMS info
        c_info = contacts.get(hrms, {})
        h_info = hrms_details.get(hrms, {})

        # Check attention status
        is_oblit = hrms in obliterated_hrms_set or "OBLITERATED" in dec_note.upper()
        needs_backfill = 1 if any(k in dec_note.lower() for k in ["need officer", "needed someone", "needed office", "korte hobe"]) else 0
        attention_flag = 1 if (is_oblit or needs_backfill) else 0
        attention_reason = ""
        if is_oblit:
            attention_reason = "Incumbent currently holding an obliterated post under Notification No. 1808."
        elif needs_backfill:
            attention_reason = "Transfer creates a cascading field vacancy requiring backfill officer."

        # Insert / replace into officer_extended_dossier
        cur.execute("""
        INSERT OR REPLACE INTO officer_extended_dossier (
            hrms_id, officer_name, mobile, whatsapp, email, wbvc_reg_no,
            office_code, ddo_code, cadre, posting_history, ancestral_address,
            current_address, spouse_service_details, family_dependencies,
            academic_details, decision_note, needs_backfill, attention_flag, attention_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hrms, name, c_info.get("mobile", "—"), c_info.get("whatsapp", "—"),
            c_info.get("email", "—"), c_info.get("wbvc", "—"),
            h_info.get("office_code", "—"), h_info.get("ddo_code", "—"),
            h_info.get("cadre", "West Bengal Animal Husbandry and Veterinary Service"),
            history if history != "did not fill the form" else "Standard service tenure across departmental postings.",
            ancestral if ancestral else "Address on departmental file.",
            current_addr if current_addr else "Address on departmental file.",
            "Spouse co-location claim recorded under Memo 291 norms." if "spouse" in history.lower() else "No special spouse claim.",
            "Family dependency and medical safeguards observed." if "medical" in history.lower() else "Standard family dependency.",
            "B.V.Sc. & A.H." + (", M.V.Sc." if "mvsc" in history.lower() else ""),
            dec_note, needs_backfill, attention_flag, attention_reason
        ))
        total_dossiers_created += 1

        # Determine Allotment if decision is confirmed
        is_stay = dec_note.strip().lower() == "stay" or dec_note.strip().lower().startswith("stay")
        has_custom = len(dec_note) > 0 and not is_stay

        if is_stay or has_custom:
            substantive_post = None
            su_post = None
            reason = ""

            # Check if this officer is on an obliterated post
            if is_oblit:
                # Assign alternative active post in same district
                sub_dd = get_district_dd_post(present_district)
                if sub_dd:
                    substantive_post = {
                        "id": sub_dd[0],
                        "name": f"DD Sl {sub_dd[0]}: {sub_dd[3]} ({sub_dd[2]}, {sub_dd[1]})"
                    }
                # Find active HQ/Block cadre post in present district for SU
                su_match = get_cadre_post_by_text("office of the deputy director", present_district) or get_cadre_post_by_text("bahc", present_district)
                if su_match:
                    su_post = {
                        "id": su_match[0],
                        "name": f"[SU] {su_match[4]}, {su_match[3]} ({su_match[1]})"
                    }
                reason = "Promotion & Post Obliteration Resolution to Valid Active Station"

            elif is_stay:
                sub_dd = get_district_dd_post(present_district)
                if sub_dd:
                    substantive_post = {
                        "id": sub_dd[0],
                        "name": f"DD Sl {sub_dd[0]}: {sub_dd[3]} ({sub_dd[2]}, {sub_dd[1]})"
                    }
                # SU is present post
                cur_p = get_cadre_post_by_text(present_post_raw, present_district)
                if cur_p:
                    su_post = {
                        "id": cur_p[0],
                        "name": f"[SU] {cur_p[4]}, {cur_p[3]} ({cur_p[1]})"
                    }
                reason = "Retained at Present Station on Service Utilization (Tenure Shield); Promoted Substantively to District HQ DD"

            elif has_custom:
                if "haringhata pay" in dec_note.lower() or "haringhata" in dec_note.lower():
                    sub_dd = get_district_dd_post("Haringhata Farm") or get_district_dd_post("Nadia")
                    if sub_dd:
                        substantive_post = {
                            "id": sub_dd[0],
                            "name": f"DD Sl {sub_dd[0]}: {sub_dd[3]} ({sub_dd[2]}, {sub_dd[1]})"
                        }
                elif "directorate" in dec_note.lower() or "dte. hq" in dec_note.lower():
                    sub_dd = get_district_dd_post("Directorate Headquarters") or get_district_dd_post("Kolkata")
                    if sub_dd:
                        substantive_post = {
                            "id": sub_dd[0],
                            "name": f"DD Sl {sub_dd[0]}: {sub_dd[3]} ({sub_dd[2]}, {sub_dd[1]})"
                        }
                else:
                    sub_dd = get_district_dd_post(present_district)
                    if sub_dd:
                        substantive_post = {
                            "id": sub_dd[0],
                            "name": f"DD Sl {sub_dd[0]}: {sub_dd[3]} ({sub_dd[2]}, {sub_dd[1]})"
                        }

                su_match = None
                for term in ["amta", "sankrail", "bally", "habra", "basirhat", "barasat", "deganga", "pingla", "sabang", "sitai", "coochbehar", "alipurduar", "kalchini", "arsha", "hura", "puncha", "purulia", "nanoor", "rajnagar", "pandua", "goghat", "haripal", "tamluk", "contai", "mahishadal", "dantan", "keshiary"]:
                    if term in dec_note.lower():
                        su_match = get_cadre_post_by_text(term)
                        if su_match:
                            break
                if su_match:
                    su_post = {
                        "id": su_match[0],
                        "name": f"[SU] {su_match[4]}, {su_match[3]} ({su_match[1]})"
                    }
                reason = f"Decision Note Allocation: {dec_note}"

            if substantive_post:
                now_str = datetime.datetime.now().isoformat()
                cur.execute("DELETE FROM simulation_assignments WHERE session_id = ? AND officer_hrms_id = ?", (session_id, hrms))
                cur.execute("""
                INSERT INTO simulation_assignments (
                    session_id, officer_hrms_id, officer_name, from_post_id, from_post_name,
                    to_post_id, to_post_name, substantive_post_id, substantive_post_name,
                    su_post_id, su_post_name, officer_type, reason,
                    collision_displaced_officer, collision_displaced_hrms, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, hrms, name, 0, present_post_raw,
                    substantive_post["id"], substantive_post["name"],
                    substantive_post["id"], substantive_post["name"],
                    su_post["id"] if su_post else None,
                    su_post["name"] if su_post else None,
                    "roster", reason, None, None, now_str
                ))

                cur.execute("""
                UPDATE roster_50_point_candidates
                SET substantive_post_id = ?, substantive_post_name = ?,
                    su_post_id = ?, su_post_name = ?, allotment_status = 'Allotted'
                WHERE hrms_id = ?
                """, (
                    substantive_post["id"], substantive_post["name"],
                    su_post["id"] if su_post else None,
                    su_post["name"] if su_post else None,
                    hrms
                ))

                cur.execute("UPDATE available_dd_posts SET allotment_status = 'Allotted', allotted_hrms = ?, allotted_name = ? WHERE dd_sl = ?", (hrms, name, substantive_post["id"]))

                if su_post:
                    cur.execute("UPDATE cadre_1794_posts SET su_allotted_hrms = ?, su_allotted_name = ? WHERE id = ?", (hrms, name, su_post["id"]))

                total_allotments_done += 1

    conn.commit()
    conn.close()
    print(f"Successfully processed {total_dossiers_created} officer dossiers and registered {total_allotments_done} confirmed allotments.")

if __name__ == "__main__":
    ingest()
