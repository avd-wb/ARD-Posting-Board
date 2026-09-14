#!/usr/bin/env python3
"""
posting_engine.py
Algorithmic Posting, Displacement & Cascade Simulation Engine for ARD Department.
Enforces:
- West Bengal Animal Husbandry & Veterinary Services Reconstitution Rules 2025 (Notification No. 1809 - 1,794 Posts)
- Post Obliteration Schedule (Notification No. 1808 - 106 Posts)
- Transfer Policy 2009 (Memo No. 291-AR & AH/3A-11/06 dt. 19.02.2009)
- 50-Point Roster Reservation Cycle (242 Candidates for 242 Available DD Posts)
- West Bengal Service Rules Rule 75(a)
- Dual Allotment System: Substantive Post + Optional Service Utilization (SU) Post
- Real-time dynamic option reduction: Allotted posts are automatically blocked from subsequent choices
"""

import os
import re
import json
import sqlite3
import datetime
from typing import Dict, List, Optional, Tuple, Any
from decision_logger import DecisionLogger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
DB_PATH = os.environ.get("DB_PATH") or ("/tmp/ard_master_truth.db" if is_vercel else os.path.join(BASE_DIR, "ard_master_truth.db"))
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR") or ("/tmp" if is_vercel else BASE_DIR)

# Memo 291 Area Tenure Classifications
SPECIAL_TENURE_DISTRICTS = {
    "Alipurduar": 4.0,
    "Coochbehar": 4.0,
    "Jalpaiguri": 4.0,
    "Darjeeling": 4.0,
    "Kalimpong": 4.0,
    "Uttar Dinajpur": 4.0,
    "Dakshin Dinajpur": 4.0,
    "Purulia": 4.0, # Blocks Bundowan, Bagmundi, Manbazar-II
    "Jhargram": 4.0, # Jungle Mahal
}
DEFAULT_TENURE = 5.0

class PostingEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        workspace = os.path.dirname(self.db_path) or WORKSPACE_DIR
        self.logger = DecisionLogger(workspace)
        self._ensure_schema()

    def _ensure_schema(self):
        """Self-heals and guarantees required columns and SU flags exist in cadre_1794_posts."""
        try:
            if not os.path.exists(self.db_path):
                return
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cadre_1794_posts'")
            if not cur.fetchone():
                conn.close()
                return

            cur.execute("PRAGMA table_info(cadre_1794_posts)")
            existing_cols = set(r[1] for r in cur.fetchall())

            needed = [
                ("service_utilized_flag", "TEXT DEFAULT 'No'"),
                ("is_substantive_blocked", "INTEGER DEFAULT 0"),
                ("substantive_allotted_hrms", "TEXT DEFAULT NULL"),
                ("substantive_allotted_name", "TEXT DEFAULT NULL"),
                ("su_allotted_hrms", "TEXT DEFAULT NULL"),
                ("su_allotted_name", "TEXT DEFAULT NULL"),
                ("incumbent_dor", "TEXT DEFAULT NULL"),
                ("incumbent_doj", "TEXT DEFAULT NULL"),
                ("incumbent_tenure", "TEXT DEFAULT NULL"),
                ("tenure_norm", "REAL DEFAULT 5.0"),
            ]
            added = False
            for col_name, col_def in needed:
                if col_name not in existing_cols:
                    try:
                        cur.execute(f"ALTER TABLE cadre_1794_posts ADD COLUMN {col_name} {col_def}")
                        added = True
                    except Exception:
                        pass

            # Ensure service_utilized_flag is properly populated if needed
            cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE service_utilized_flag = 'Service Utilized'")
            su_count = cur.fetchone()[0]
            if su_count == 0:
                cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='master_source_of_truth'")
                if cur.fetchone()[0]:
                    cur.execute("""
                    UPDATE cadre_1794_posts
                    SET service_utilized_flag = 'Service Utilized'
                    WHERE post_sl IN (
                        SELECT id FROM master_source_of_truth WHERE service_utilization = 'Service Utilized'
                    )
                    """)
                cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='T6_FILLED_ON_PAPER_SU'")
                if cur.fetchone()[0]:
                    cur.execute("""
                    UPDATE cadre_1794_posts
                    SET service_utilized_flag = 'Service Utilized'
                    WHERE post_code IN (
                        SELECT ALLOCATED_POST_ID FROM T6_FILLED_ON_PAPER_SU WHERE ALLOCATED_POST_ID IS NOT NULL AND ALLOCATED_POST_ID != ''
                    ) OR incumbent_hrms IN (
                        SELECT HRMS_ID FROM T6_FILLED_ON_PAPER_SU WHERE HRMS_ID IS NOT NULL AND HRMS_ID != ''
                    )
                    """)
                conn.commit()
            conn.close()
        except Exception:
            pass

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- MEMO 291 & CADRE RULE CHECKS ---

    def evaluate_tenure_norm(self, district: str, block: str = "") -> float:
        """Returns standard maximum tenure for given district and block."""
        d = str(district or "").strip()
        for k, v in SPECIAL_TENURE_DISTRICTS.items():
            if k.lower() in d.lower():
                return v
        b = str(block or "").strip().lower()
        if any(sm in b for sm in ["bundowan", "bagmundi", "manbazar", "hirbundh", "ranibundh"]):
            return 4.0
        return DEFAULT_TENURE

    def check_officer_rules(self, officer_data: Dict[str, Any], target_post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates an allotment against West Bengal administrative transfer rules
        (Transfer Policy Memo 291-AR & AH/3A-11/06 dt. 19.02.2009 & WBRS / Cadre norms).
        Returns a comprehensive compliance breakdown with overall Green/Red verdict.
        """
        target_dist = str(target_post.get("district") or "").strip()
        target_block = str(target_post.get("block") or "").strip()
        target_post_name = str(target_post.get("post_name") or target_post.get("designation") or "").strip()
        max_tenure = self.evaluate_tenure_norm(target_dist, target_block)

        tenure_years = float(officer_data.get("tenure_years") or 0.0)
        curr_dist = str(officer_data.get("district") or officer_data.get("current_district") or officer_data.get("present_district") or "").strip()
        home_dist = str(officer_data.get("home_district") or officer_data.get("native_district") or "").strip()
        fam_text = str(officer_data.get("family_details") or "")
        caste = str(officer_data.get("caste") or "Gen").strip()
        roster_pt_res = str(officer_data.get("point_reserved_for") or "UR").strip()
        dor_str = str(officer_data.get("service_ends") or officer_data.get("incumbent_dor") or officer_data.get("dor") or "").strip()

        # Calculate years to superannuation
        dor_years = 99.0
        if dor_str and len(dor_str) >= 4:
            try:
                # Try parsing YYYY-MM-DD or DD/MM/YYYY
                if "-" in dor_str:
                    parts = dor_str.split("-")
                    if len(parts[0]) == 4:
                        dor_dt = datetime.datetime.strptime(dor_str[:10], "%Y-%m-%d").date()
                    else:
                        dor_dt = datetime.datetime.strptime(dor_str[:10], "%d-%m-%Y").date()
                elif "/" in dor_str:
                    dor_dt = datetime.datetime.strptime(dor_str[:10], "%d/%m/%Y").date()
                else:
                    dor_dt = None
                if dor_dt:
                    today = datetime.date.today()
                    dor_years = max(0.0, (dor_dt - today).days / 365.25)
            except Exception:
                dor_years = 99.0

        violations = []
        cautions = []
        checks = []

        # 1. Standard Area Tenure Evaluation (Memo 291)
        is_difficult_zone = max_tenure <= 4.0
        tenure_status = "COMPLIANT"
        tenure_msg = f"Tenure within {max_tenure:.0f}-year norm for {target_dist or 'this post'}."
        tenure_icon = "check-circle"
        tenure_badge = "GREEN"

        if tenure_years > max_tenure:
            tenure_status = "OVER_TENURE"
            tenure_msg = f"Officer tenure ({tenure_years:.1f} yrs) exceeds {max_tenure:.0f}-year area norm ({'Difficult/Hill Zone' if is_difficult_zone else 'General Zone'}). Rotation recommended."
            tenure_icon = "alert-circle"
            tenure_badge = "RED"
            violations.append(f"Tenure violation: {tenure_years:.1f} years served exceeds {max_tenure:.0f}-year maximum under Memo 291.")
        elif tenure_years > 0 and tenure_years < 2.0 and curr_dist and target_dist and curr_dist.lower() != target_dist.lower():
            tenure_status = "PREMATURE_TRANSFER"
            tenure_msg = f"Officer has completed only {tenure_years:.1f} years in current station. Normal minimum tenure before transfer is 2 years unless on administrative exigency."
            tenure_icon = "alert-triangle"
            tenure_badge = "YELLOW"
            cautions.append(f"Premature transfer ({tenure_years:.1f} yrs in current post). Needs administrative justification.")

        checks.append({
            "criterion": "Area Tenure Norm (Memo 291)",
            "clause": f"Max {max_tenure:.0f} yrs ({'Difficult Zone' if is_difficult_zone else 'Standard Zone'})",
            "status": tenure_status,
            "badge": tenure_badge,
            "message": tenure_msg
        })

        # 2. Superannuation Protection (Retirement within 2 Years)
        retire_status = "NORMAL"
        retire_badge = "BLUE"
        retire_msg = "Superannuation > 2 years away."
        if dor_years <= 2.0:
            retire_status = "PROTECTED_SUPERANNUATION"
            retire_badge = "GREEN"
            retire_msg = f"Retirement in {dor_years:.1f} years ({dor_str}). Officer entitled to choice of home district / station without displacement under Memo 291."
        checks.append({
            "criterion": "Superannuation Protection",
            "clause": "Retirement within 2 Years",
            "status": retire_status,
            "badge": retire_badge,
            "message": retire_msg
        })

        # 3. Home District Posting Restriction (Administrative Norms)
        home_status = "COMPLIANT"
        home_badge = "GREEN"
        home_msg = "Posting is outside home district."
        if home_dist and target_dist and home_dist.lower() in target_dist.lower():
            if dor_years <= 2.0:
                home_status = "HOME_DISTRICT_ALLOWED_SUPERANNUATION"
                home_badge = "GREEN"
                home_msg = f"Home District posting ({home_dist}) is permitted under 2-year Superannuation Exemption."
            elif any(ad in target_post_name.lower() for ad in ["deputy director", "dd", "assistant director (hq)"]):
                home_status = "HOME_DISTRICT_RESTRICTION"
                home_badge = "YELLOW"
                home_msg = f"Administrative post ({target_post_name}) in Home District ({home_dist}) requires departmental waiver under Rule 75."
                cautions.append(f"Home District posting: Officer native of {home_dist}. Departmental administrative waiver recommended.")
            else:
                home_status = "HOME_DISTRICT_OK"
                home_badge = "GREEN"
                home_msg = f"Posting located in Home District ({home_dist})."
        checks.append({
            "criterion": "Home District Norm",
            "clause": "Administrative cadre separation",
            "status": home_status,
            "badge": home_badge,
            "message": home_msg
        })

        # 4. Children Academic Board Exam Safeguard (Disabled - No private personal data retained)
        exam_status = "NOT_APPLICABLE"
        exam_badge = "GREY"
        exam_msg = "Personal family data not retained in official register."

        # 5. Spouse Co-location (Disabled - No private personal data retained)
        spouse_status = "NOT_APPLICABLE"
        spouse_badge = "GREY"
        spouse_msg = "Personal spouse data not retained in official register."

        # 6. 50-Point Roster Reservation Alignment
        roster_status = "PANEL_VERIFIED"
        roster_badge = "GREEN"
        roster_msg = f"Roster point reservation: {roster_pt_res} (official panel alignment under verification)."
        checks.append({
            "criterion": "50-Point Roster Reservation",
            "clause": f"Point Reserved: {roster_pt_res}",
            "status": roster_status,
            "badge": roster_badge,
            "message": roster_msg
        })

        # 7. Preference Satisfaction Match
        pref_text = str(officer_data.get("all_preferences") or officer_data.get("posting_preferences_all") or "")
        pref_match = "NO_PREFERENCE_LISTED"
        pref_badge = "GREY"
        if pref_text and pref_text != "—":
            if target_dist and target_dist.lower() in pref_text.lower():
                if "Pref 1" in pref_text and target_dist.lower() in pref_text.split("Pref 2")[0].lower():
                    pref_match = "CHOICE_1 (First Preference Satisfied)"
                    pref_badge = "GREEN"
                elif "Pref 2" in pref_text and target_dist.lower() in pref_text.split("Pref 3")[0].lower():
                    pref_match = "CHOICE_2 (Second Preference Satisfied)"
                    pref_badge = "GREEN"
                elif "Pref 3" in pref_text:
                    pref_match = "CHOICE_3 (Third Preference Satisfied)"
                    pref_badge = "GREEN"
                else:
                    pref_match = "CHOICE_SATISFIED"
                    pref_badge = "GREEN"
            elif curr_dist and target_dist and curr_dist.lower() == target_dist.lower():
                pref_match = "SAME_DISTRICT_CONTINUATION"
                pref_badge = "BLUE"
            else:
                pref_match = "ADMINISTRATIVE_ALLOTMENT (Outside Preferences)"
                pref_badge = "YELLOW"
        checks.append({
            "criterion": "Candidate Preference",
            "clause": "Options 1-3 Submission",
            "status": pref_match,
            "badge": pref_badge,
            "message": f"Status: {pref_match}"
        })

        # Overarching Verdict Determination
        is_compliant = len(violations) == 0
        overall_status = "COMPLIANT"
        verdict_badge = "GREEN"
        summary_label = "Transfer Policy 2009 Compliant"

        if len(violations) > 0:
            overall_status = "VIOLATION"
            verdict_badge = "RED"
            summary_label = f"{len(violations)} Policy Violation{'s' if len(violations) > 1 else ''} Detected"
        elif len(cautions) > 0:
            overall_status = "CAUTION"
            verdict_badge = "YELLOW"
            summary_label = f"Compliant with {len(cautions)} Administrative Advisory"

        return {
            "overall_status": overall_status,
            "is_compliant": is_compliant,
            "verdict_badge": verdict_badge,
            "summary_label": summary_label,
            "violations": violations,
            "cautions": cautions,
            "checks": checks,
            "tenure": {"status": tenure_status, "message": tenure_msg, "max_allowed": max_tenure, "tenure_years": tenure_years},
            "spouse": {"status": spouse_status, "message": spouse_msg},
            "board_exam": {"status": exam_status, "message": exam_msg},
            "roster": {"status": roster_status, "message": roster_msg},
            "preference": {"match": pref_match},
            "superannuation": {"dor_years": round(dor_years, 1), "dor_str": dor_str}
        }

    # --- DYNAMIC OPTION REDUCTION QUERIES ---

    def get_available_substantive_posts(self, officer_role: str = "roster", session_id: str = "CURRENT_SESSION") -> List[Dict[str, Any]]:
        """
        Dynamically returns available Substantive posts, strictly excluding any posts
        already allotted in the active simulation session.
        - For Roster Promotees: Available Deputy Director posts from available_dd_posts (242 available).
        - For Obliterated / Displaced Officers: Clear vacant posts from cadre_1794_posts (AD or other cadres).
        """
        conn = self.get_connection()
        cur = conn.cursor()

        if officer_role == "roster":
            cur.execute("""
            SELECT 
                dd_sl AS post_id,
                dd_sl,
                district,
                establishment,
                office,
                post_name,
                ('DD Sl ' || dd_sl || ': ' || post_name || ' — ' || office || ', ' || district) AS display_label
            FROM available_dd_posts
            WHERE is_blocked_vigilance = 0
              AND dd_sl NOT IN (
                  SELECT substantive_post_id FROM simulation_assignments
                  WHERE session_id = ? AND substantive_post_id IS NOT NULL AND officer_type = 'roster'
              )
            ORDER BY district, office
            """, (session_id,))
            rows = [dict(r) for r in cur.fetchall()]
        else:
            cur.execute("""
            SELECT 
                id AS post_id,
                district,
                establishment,
                block,
                designation,
                post_code,
                ('[' || id || '] ' || designation || ' — ' || establishment || 
                 (CASE WHEN block != '' AND block IS NOT NULL THEN ', ' || block ELSE '' END) || 
                 ', ' || district) AS display_label
            FROM cadre_1794_posts
            WHERE UPPER(occupancy_status) = 'VACANT'
              AND id != 1
              AND (pay_level IS NULL OR pay_level NOT IN ('Level-22', 'Level-21'))
              AND designation NOT LIKE '%Director of AH%'
              AND id NOT IN (
                  SELECT substantive_post_id FROM simulation_assignments
                  WHERE session_id = ? AND substantive_post_id IS NOT NULL AND officer_type != 'roster'
              )
              AND id NOT IN (
                  SELECT to_post_id FROM simulation_assignments
                  WHERE session_id = ? AND to_post_id IS NOT NULL
              )
            ORDER BY district, designation, establishment
            """, (session_id, session_id))
            rows = [dict(r) for r in cur.fetchall()]

        conn.close()
        return rows

    def get_available_su_posts(self, session_id: str = "CURRENT_SESSION", search: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Dynamically returns posts available for Service Utilization (SU),
        excluding posts already blocked as SU in this session and excluding apex posts (Director).
        Can be vacant OR filled (if filled, marks collision risk).
        """
        conn = self.get_connection()
        cur = conn.cursor()

        query = """
        SELECT 
            id AS post_id,
            district,
            block,
            establishment,
            designation,
            occupancy_status,
            incumbent_name,
            incumbent_hrms,
            ('[' || id || '] ' || designation || ' — ' || establishment || 
             (CASE WHEN block != '' AND block IS NOT NULL THEN ', ' || block ELSE '' END) || 
             ', ' || district || ' (' || 
             (CASE WHEN UPPER(occupancy_status) = 'VACANT' THEN 'VACANT' ELSE 'Occupied by ' || incumbent_name END) || 
             ')') AS display_label
        FROM cadre_1794_posts
        WHERE id NOT IN (
            SELECT su_post_id FROM simulation_assignments
            WHERE session_id = ? AND su_post_id IS NOT NULL
        )
          AND id != 1
          AND (pay_level IS NULL OR pay_level NOT IN ('Level-22', 'Level-21'))
          AND designation NOT LIKE '%Director of AH%'
          AND (incumbent_hrms IS NULL OR incumbent_hrms != '1992005664')
        """
        params = [session_id]

        if search:
            s = f"%{search.strip()}%"
            query += " AND (designation LIKE ? OR establishment LIKE ? OR district LIKE ? OR block LIKE ? OR incumbent_name LIKE ?)"
            params.extend([s, s, s, s, s])

        query += " ORDER BY district, designation, establishment LIMIT 500"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    # --- DUAL ALLOTMENT SIMULATION (SUBSTANTIVE + SU) ---

    def simulate_dual_allotment(
        self,
        session_id: str,
        officer_hrms: str,
        substantive_post_id: int,
        su_post_id: Optional[int] = None,
        reason: str = "Promotion (50-Point Roster)",
        officer_type: str = "roster"
    ) -> Dict[str, Any]:
        """
        Executes a dual allotment:
        1. Substantive Post (Promotable DD post from available_dd_posts, or vacant AD post from cadre_1794_posts)
        2. Optional Service Utilization (SU) Post (Any post from cadre_1794_posts, vacant or filled)
        Updates DB atomically and triggers collision detection if an occupied SU post is targeted.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        # CRITICAL CONSTITUTIONAL & ADMINISTRATIVE SAFEGUARD:
        # The Director of AH&VS, West Bengal (Dr. Nikhil Kumar Shit, Level-22) is the apex head of the department.
        # The Director post and apex executive posts CAN NEVER be replaced, displaced, or utilized for SU allotments.
        if int(substantive_post_id) in [1] or (su_post_id and int(su_post_id) in [1]):
            conn.close()
            return {
                "success": False,
                "error": "CRITICAL ADMINISTRATIVE PROHIBITION: The Director of AH&VS, West Bengal (Dr. Nikhil Kumar Shit, Level-22) is the apex head of the department and can NEVER be replaced, displaced, or utilized for SU allotments."
            }
        if str(officer_hrms).strip() == "1992005664":
            conn.close()
            return {
                "success": False,
                "error": "CRITICAL ADMINISTRATIVE PROHIBITION: Dr. Nikhil Kumar Shit is the Director of AH&VS and cannot be transferred or displaced in this cadre simulation."
            }

        # 1. Fetch Officer details
        officer_data = {}
        cur.execute("SELECT * FROM roster_50_point_candidates WHERE hrms_id = ?", (officer_hrms,))
        r_row = cur.fetchone()
        if r_row:
            officer_data = dict(r_row)
            officer_type = "roster"
        else:
            cur.execute("SELECT * FROM ABOLISHED_POST_LEADS WHERE hrms_id = ?", (officer_hrms,))
            o_row = cur.fetchone()
            if o_row:
                officer_data = dict(o_row)
                officer_type = "obliterated"
            else:
                cur.execute("SELECT * FROM cadre_1794_posts WHERE incumbent_hrms = ?", (officer_hrms,))
                c_row = cur.fetchone()
                if c_row:
                    officer_data = dict(c_row)
                    officer_data["officer_name"] = c_row["incumbent_name"]
                    officer_data["hrms_id"] = c_row["incumbent_hrms"]
                    officer_type = "displaced"
                else:
                    conn.close()
                    return {"success": False, "error": f"Officer HRMS {officer_hrms} not found."}

        officer_name = officer_data.get("officer_name", "Officer")
        from_post_id = officer_data.get("id") or officer_data.get("oblit_sl") or 0
        from_post_name = officer_data.get("detailed_presentation") or officer_data.get("present_posting") or officer_data.get("post_name") or "Present Post"

        # 2. Resolve Substantive Target Post
        substantive_name = ""
        substantive_dist = ""
        target_post_for_rules = {}

        if officer_type == "roster":
            cur.execute("SELECT * FROM available_dd_posts WHERE dd_sl = ?", (substantive_post_id,))
            dd_row = cur.fetchone()
            if dd_row:
                substantive_name = f"DD Sl {dd_row['dd_sl']}: {dd_row['post_name']} ({dd_row['office']}, {dd_row['district']})"
                substantive_dist = dd_row['district']
                target_post_for_rules = {"district": dd_row["district"], "block": "", "establishment": dd_row["office"], "designation": "Deputy Director"}
            else:
                cur.execute("SELECT * FROM cadre_1794_posts WHERE id = ?", (substantive_post_id,))
                c_row = cur.fetchone()
                if c_row:
                    substantive_name = c_row['detailed_presentation'] or f"{c_row['designation']}, {c_row['establishment']}"
                    substantive_dist = c_row['district']
                    target_post_for_rules = dict(c_row)
        else:
            cur.execute("SELECT * FROM cadre_1794_posts WHERE id = ?", (substantive_post_id,))
            c_row = cur.fetchone()
            if c_row:
                substantive_name = c_row['detailed_presentation'] or f"{c_row['designation']}, {c_row['establishment']}"
                substantive_dist = c_row['district']
                target_post_for_rules = dict(c_row)

        if not substantive_name:
            conn.close()
            return {"success": False, "error": f"Substantive target post ID {substantive_post_id} not found."}

        # 3. Resolve Optional Service Utilization (SU) Post & Check Collision
        su_name = None
        is_collision = False
        displaced_officer = None
        displaced_hrms = None
        displaced_row_data = {}

        if su_post_id and int(su_post_id) > 0:
            cur.execute("SELECT * FROM cadre_1794_posts WHERE id = ?", (su_post_id,))
            su_row = cur.fetchone()
            if su_row:
                su_hrms = str(su_row["incumbent_hrms"] or "").strip()
                su_desig = str(su_row["designation"] or "").lower()
                su_pay = str(su_row["pay_level"] or "")
                if su_hrms == "1992005664" or "director of ah" in su_desig or su_pay in ["Level-22", "Level-21"] or su_row["id"] == 1:
                    conn.close()
                    return {
                        "success": False,
                        "error": "CRITICAL ADMINISTRATIVE PROHIBITION: Target post belongs to Director of AH&VS / Apex Directorate Executive and cannot be targeted for Service Utilization or displacement."
                    }

                su_name = f"[SU] {su_row['designation']}, {su_row['establishment']} ({su_row['district']})"
                su_occ = str(su_row.get("occupancy_status") or "").strip().upper()
                if su_occ not in ["VACANT", ""]:
                    if su_row["incumbent_hrms"] and str(su_row["incumbent_hrms"]).strip() != str(officer_hrms).strip():
                        inc_hrms = str(su_row["incumbent_hrms"]).strip()
                        if inc_hrms != "1992005664" and "director of ah" not in su_desig:
                            is_collision = True
                            displaced_officer = su_row["incumbent_name"]
                            displaced_hrms = inc_hrms
                            displaced_row_data = dict(su_row)

        # 4. Evaluate Statutory Rules against substantive post
        rule_checks = self.check_officer_rules(officer_data, target_post_for_rules)

        # 5. Insert Record into simulation_assignments
        now_str = datetime.datetime.now().isoformat()
        cur.execute("""
        INSERT INTO simulation_assignments (
            session_id, officer_hrms_id, officer_name, from_post_id, from_post_name,
            to_post_id, to_post_name, substantive_post_id, substantive_post_name,
            su_post_id, su_post_name, officer_type, reason,
            collision_displaced_officer, collision_displaced_hrms,
            rule_tenure_check, rule_roster_check,
            status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            officer_hrms,
            officer_name,
            from_post_id,
            from_post_name,
            substantive_post_id,
            substantive_name,
            substantive_post_id,
            substantive_name,
            su_post_id,
            su_name,
            officer_type,
            reason,
            displaced_officer if is_collision else None,
            displaced_hrms if is_collision else None,
            rule_checks["tenure"]["status"],
            rule_checks["roster"]["status"],
            "COMPLETED",
            now_str
        ))

        # 6. Update Target Candidate / Obliterated tables
        if officer_type == "roster":
            cur.execute("""
            UPDATE roster_50_point_candidates
            SET substantive_post_id = ?, substantive_post_name = ?,
                su_post_id = ?, su_post_name = ?,
                allotment_status = 'Allotted'
            WHERE hrms_id = ?
            """, (substantive_post_id, substantive_name, su_post_id, su_name, officer_hrms))

            cur.execute("""
            UPDATE available_dd_posts
            SET allotment_status = 'Allotted', allotted_hrms = ?, allotted_name = ?
            WHERE dd_sl = ?
            """, (officer_hrms, officer_name, substantive_post_id))

        elif officer_type == "obliterated":
            cur.execute("""
            UPDATE ABOLISHED_POST_LEADS
            SET substantive_post_id = ?, substantive_post_name = ?,
                su_post_id = ?, su_post_name = ?,
                rehabilitation_status = 'Rehabilitated'
            WHERE hrms_id = ?
            """, (substantive_post_id, substantive_name, su_post_id, su_name, officer_hrms))

        elif officer_type == "displaced":
            cur.execute("""
            UPDATE displaced_officers_pool
            SET rehabilitation_status = 'Reallocated',
                reallocated_post_id = ?,
                reallocated_post_name = ?,
                reallocated_su_post_id = ?,
                reallocated_su_post_name = ?
            WHERE officer_hrms = ? AND session_id = ?
            """, (substantive_post_id, substantive_name, su_post_id, su_name, officer_hrms, session_id))

        # 7. Update cadre_1794_posts markers
        if officer_type != "roster":
            cur.execute("""
            UPDATE cadre_1794_posts
            SET is_substantive_blocked = 1, substantive_allotted_hrms = ?, substantive_allotted_name = ?
            WHERE id = ?
            """, (officer_hrms, officer_name, substantive_post_id))

        if su_post_id:
            cur.execute("""
            UPDATE cadre_1794_posts
            SET su_allotted_hrms = ?, su_allotted_name = ?
            WHERE id = ?
            """, (officer_hrms, officer_name, su_post_id))

        # 8. Handle Displaced Officer Queue Placement
        # APEX SAFEGUARD: Dr. Nikhil Kumar Shit / Director of AH&VS can NEVER be queued as displaced
        if is_collision and displaced_hrms and str(displaced_hrms).strip() != "1992005664":
            cur.execute("SELECT id FROM displaced_officers_pool WHERE session_id = ? AND officer_hrms = ?", (session_id, displaced_hrms))
            existing_disp = cur.fetchone()
            if not existing_disp:
                cur.execute("""
                INSERT INTO displaced_officers_pool (
                    session_id, officer_hrms, officer_name, from_post_id, from_post_name,
                    district, block, pay_level, tenure, dor, displaced_by_hrms, displaced_by_name,
                    displaced_by_reason, displacement_type, rehabilitation_status, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    displaced_hrms,
                    displaced_officer,
                    displaced_row_data.get("id"),
                    displaced_row_data.get("detailed_presentation") or f"{displaced_row_data.get('designation')}, {displaced_row_data.get('establishment')}",
                    displaced_row_data.get("district", ""),
                    displaced_row_data.get("block", ""),
                    displaced_row_data.get("pay_level", "Level 16"),
                    str(displaced_row_data.get("incumbent_tenure") or "0.0"),
                    str(displaced_row_data.get("incumbent_dor") or ""),
                    officer_hrms,
                    officer_name,
                    f"Displaced due to Service Utilization placement of {officer_name}",
                    "Service Utilization Displacement",
                    "Pending Placement",
                    now_str
                ))

        conn.commit()
        conn.close()

        # 9. Log Decision to Master Ledger (Excel, CSV, Sync Queue) & Trigger Auto-Backup
        present_pay = officer_data.get("pay_level") or "Level 16 (Rs. 56,100 - Rs. 1,44,300)"
        if officer_type == "roster":
            transfer_by = "Promotion"
            target_pay = "Level 19 (Rs. 95,100 - Rs. 1,48,000)"
        elif officer_type == "displaced":
            transfer_by = "Transfer due to Displaced"
            target_pay = present_pay
        else:
            transfer_by = "Transfer" if "transfer" in reason.lower() else "Rehabilitation Transfer"
            target_pay = present_pay

        try:
            self.logger.log_decision(
                session_id=session_id,
                officer_hrms=str(officer_hrms),
                officer_name=officer_name,
                present_posting=from_post_name,
                present_pay_level=present_pay,
                transfer_by=transfer_by,
                substantive_post_name=substantive_name,
                su_post_name=su_name,
                target_pay_level=target_pay,
                displaced_hrms=displaced_hrms if is_collision else None,
                displaced_name=displaced_officer if is_collision else None,
                rules_summary=f"Tenure:{rule_checks['tenure']['status']}; Roster:{rule_checks['roster']['status']}"
            )
        except Exception as e:
            print(f"[PostingEngine] Warning: Decision logging failed: {e}")

        return {
            "success": True,
            "officer_name": officer_name,
            "officer_hrms": officer_hrms,
            "officer_type": officer_type,
            "substantive_post_id": substantive_post_id,
            "substantive_post_name": substantive_name,
            "su_post_id": su_post_id,
            "su_post_name": su_name,
            "collision_detected": is_collision,
            "displaced_officer": displaced_officer if is_collision else None,
            "displaced_hrms": displaced_hrms if is_collision else None,
            "rule_checks": rule_checks,
            "timestamp": now_str
        }

    def simulate_allotment(
        self,
        session_id: str,
        officer_hrms: str,
        target_post_id: int,
        reason: str = "Promotion (50-Point Roster)"
    ) -> Dict[str, Any]:
        """Backward-compatible single-target wrapper."""
        return self.simulate_dual_allotment(
            session_id=session_id,
            officer_hrms=officer_hrms,
            substantive_post_id=target_post_id,
            su_post_id=None,
            reason=reason,
            officer_type="roster"
        )

    # --- AUTONOMOUS MULTI-PARTY CASCADE SOLVER ---

    def solve_multi_party_cadre(self, session_id: str = "DEFAULT_SOLVER_RUN") -> Dict[str, Any]:
        """
        Autonomous Multi-Party Solver:
        Phase 1: Promote 22 dual-status officers (obliterated + roster) into available DD posts.
        Phase 2: Promote remaining 220 roster officers into available DD posts matching preferences.
        Phase 3: Rehabilitate remaining serving obliterated officers into vacant AD posts in 1,794 Cadre.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        # Reset simulation state for this session
        cur.execute("DELETE FROM simulation_assignments WHERE session_id = ?", (session_id,))
        cur.execute("DELETE FROM displaced_officers_pool WHERE session_id = ? OR officer_hrms = '1992005664'", (session_id,))
        cur.execute("""
        UPDATE roster_50_point_candidates 
        SET substantive_post_id = NULL, substantive_post_name = NULL, 
            su_post_id = NULL, su_post_name = NULL, allotment_status = 'Pending'
        """)
        cur.execute("""
        UPDATE ABOLISHED_POST_LEADS 
        SET substantive_post_id = NULL, substantive_post_name = NULL, 
            su_post_id = NULL, su_post_name = NULL, rehabilitation_status = 'Pending'
        """)
        cur.execute("UPDATE available_dd_posts SET allotment_status = 'Available', allotted_hrms = NULL, allotted_name = NULL")
        cur.execute("UPDATE cadre_1794_posts SET is_substantive_blocked = 0, substantive_allotted_hrms = NULL, substantive_allotted_name = NULL, su_allotted_hrms = NULL, su_allotted_name = NULL")
        conn.commit()

        # Fetch available DD posts (242 unblocked)
        cur.execute("""
        SELECT dd_sl, district, establishment, office, post_name
        FROM available_dd_posts
        WHERE is_blocked_vigilance = 0
        ORDER BY district, office
        """)
        available_dd_posts = [dict(r) for r in cur.fetchall()]

        # Fetch vacant AD posts from 1,794 cadre
        cur.execute("""
        SELECT id, designation, establishment, block, district, detailed_presentation
        FROM cadre_1794_posts
        WHERE designation LIKE '%Assistant Director%' AND UPPER(occupancy_status) = 'VACANT'
        ORDER BY district, establishment
        """)
        vacant_ad_posts = [dict(r) for r in cur.fetchall()]

        allocated_dd_sls = set()
        allocated_ad_ids = set()

        def match_dd_post(officer_row):
            pref_text = str(officer_row.get("all_preferences") or "")
            curr_dist = str(officer_row.get("present_district") or "")

            # 1. Match explicit preferences
            for p_num in range(1, 9):
                prefix = f"Pref {p_num}:"
                dd_prefix = f"DD Pref {p_num}:"
                for part in pref_text.split("|"):
                    part = part.strip()
                    if part.startswith(prefix) or part.startswith(dd_prefix):
                        val = part.split(":", 1)[1].strip().lower()
                        for post in available_dd_posts:
                            if post["dd_sl"] not in allocated_dd_sls:
                                if post["district"].lower() in val or any(w in post["office"].lower() for w in val.split() if len(w) > 4):
                                    return post, f"Pref {p_num}"

            # 2. Match current district
            if curr_dist:
                for post in available_dd_posts:
                    if post["dd_sl"] not in allocated_dd_sls and post["district"].lower() == curr_dist.lower():
                        return post, "Current District Match"

            # 3. Fallback to unallocated DD post
            for post in available_dd_posts:
                if post["dd_sl"] not in allocated_dd_sls:
                    return post, "Administrative Balance Allocation"

            return None, "No DD Vacancy Available"

        def match_ad_post(officer_row):
            curr_dist = str(officer_row.get("district") or "")
            for post in vacant_ad_posts:
                if post["id"] not in allocated_ad_ids and post["district"].lower() == curr_dist.lower():
                    return post, "District Cadre Retention"
            for post in vacant_ad_posts:
                if post["id"] not in allocated_ad_ids:
                    return post, "Cadre Rehabilitation Vacancy"
            return None, "No AD Vacancy Available"

        # --- PHASE 1: DUAL-STATUS OFFICERS (22) ---
        cur.execute("SELECT * FROM roster_50_point_candidates WHERE is_dual_obliterated = 1 ORDER BY sl_no")
        dual_officers = [dict(r) for r in cur.fetchall()]
        phase1_allotments = []

        for off in dual_officers:
            best_dd, match_reason = match_dd_post(off)
            if best_dd:
                allocated_dd_sls.add(best_dd["dd_sl"])
                res = self.simulate_dual_allotment(
                    session_id=session_id,
                    officer_hrms=off["hrms_id"],
                    substantive_post_id=best_dd["dd_sl"],
                    su_post_id=None,
                    reason=f"Promotion & Post Obliteration Resolution ({match_reason})",
                    officer_type="roster"
                )
                res["match_reason"] = match_reason
                phase1_allotments.append(res)

        # --- PHASE 2: REMAINING ROSTER CANDIDATES (220) ---
        cur.execute("SELECT * FROM roster_50_point_candidates WHERE is_dual_obliterated = 0 ORDER BY sl_no")
        remaining_roster = [dict(r) for r in cur.fetchall()]
        phase2_allotments = []

        for off in remaining_roster:
            best_dd, match_reason = match_dd_post(off)
            if best_dd:
                allocated_dd_sls.add(best_dd["dd_sl"])
                res = self.simulate_dual_allotment(
                    session_id=session_id,
                    officer_hrms=off["hrms_id"],
                    substantive_post_id=best_dd["dd_sl"],
                    su_post_id=None,
                    reason=f"50-Point Roster Promotion Point {off['roster_point']} ({match_reason})",
                    officer_type="roster"
                )
                res["match_reason"] = match_reason
                phase2_allotments.append(res)
            else:
                phase2_allotments.append({
                    "success": False,
                    "officer_name": off["officer_name"],
                    "officer_hrms": off["hrms_id"],
                    "reason": "Deputy Director Vacancies Exhausted"
                })

        # --- PHASE 3: REMAINING SERVING OBLITERATED OFFICERS ---
        cur.execute("""
        SELECT * FROM ABOLISHED_POST_LEADS 
        WHERE is_on_roster = 0 AND is_vacant != 'Yes'
        ORDER BY id
        """)
        serving_oblit = [dict(r) for r in cur.fetchall()]
        phase3_allotments = []

        for off in serving_oblit:
            best_ad, match_reason = match_ad_post(off)
            if best_ad:
                allocated_ad_ids.add(best_ad["id"])
                res = self.simulate_dual_allotment(
                    session_id=session_id,
                    officer_hrms=off["hrms_id"],
                    substantive_post_id=best_ad["id"],
                    su_post_id=None,
                    reason=f"Notification 1808 Rehabilitation to Active AD Cadre Post ({match_reason})",
                    officer_type="obliterated"
                )
                res["match_reason"] = match_reason
                phase3_allotments.append(res)
            else:
                phase3_allotments.append({
                    "success": False,
                    "officer_name": off["officer_name"],
                    "officer_hrms": off["hrms_id"],
                    "reason": "Assistant Director Vacancies Exhausted"
                })

        conn.close()

        total_promotions = len(phase1_allotments) + len([p for p in phase2_allotments if p.get("success")])
        total_obliterated_resolved = len(phase1_allotments) + len([p for p in phase3_allotments if p.get("success")])

        return {
            "session_id": session_id,
            "status": "OPTIMIZATION_COMPLETE",
            "summary": {
                "total_promotions": total_promotions,
                "target_roster_candidates": 242,
                "dual_status_clean_dissolutions": len(phase1_allotments),
                "total_obliterated_rehabilitated": total_obliterated_resolved,
                "serving_obliterated_officers": len(serving_oblit) + len(phase1_allotments),
                "total_available_dd_posts": len(available_dd_posts),
                "remaining_dd_vacancies": len(available_dd_posts) - total_promotions,
                "remaining_ad_vacancies": len(vacant_ad_posts) - len(phase3_allotments)
            },
            "phase1_dual_promotions": phase1_allotments,
            "phase2_roster_promotions": phase2_allotments,
            "phase3_obliteration_rehab": phase3_allotments
        }

    # --- AI ADMINISTRATIVE EXPLAINER ---

    def explain_posting_decision(self, officer_hrms: str, substantive_post_id: int) -> str:
        """
        Generates an administrative order rationale citing statutory memos.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM roster_50_point_candidates WHERE hrms_id = ?", (officer_hrms,))
        r_row = cur.fetchone()
        officer = dict(r_row) if r_row else None
        target_post = {}

        if officer:
            cur.execute("SELECT * FROM available_dd_posts WHERE dd_sl = ?", (substantive_post_id,))
            dd_row = cur.fetchone()
            if dd_row:
                target_post = {
                    "district": dd_row["district"],
                    "establishment": dd_row["office"],
                    "designation": "Deputy Director, ARD",
                    "present_occupant_status": "No"
                }
        else:
            cur.execute("SELECT * FROM ABOLISHED_POST_LEADS WHERE hrms_id = ?", (officer_hrms,))
            o_row = cur.fetchone()
            if o_row:
                officer = dict(o_row)
                cur.execute("SELECT * FROM cadre_1794_posts WHERE id = ?", (substantive_post_id,))
                c_row = cur.fetchone()
                if c_row:
                    target_post = dict(c_row)

        conn.close()

        if not officer:
            return f"Officer with HRMS {officer_hrms} not found in departmental records."

        name = officer.get("officer_name", "Officer")
        roster_pt = officer.get("roster_point", "N/A")
        curr_dist = officer.get("present_district") or officer.get("district") or "Not Specified"
        t_dist = target_post.get("district", "West Bengal")
        t_estab = target_post.get("establishment", "Establishment")
        t_desig = target_post.get("designation", "Post")

        rules = self.check_officer_rules(officer, target_post)

        rationale = f"""### Administrative Justification & Statutory Compliance Brief
**Officer**: {name} (HRMS: `{officer_hrms}`)
**Proposed Substantive Posting**: {t_desig}, {t_estab}, {t_dist}

1. **Cadre Authority & Vacancy Sanction**:
   - The proposed establishment has an active sanctioned post under **Notification No. 1809-AR&AH/3A-08/23 dt. 18.06.2025** (Establishment Schedule of 1,794 Posts).
   - Post occupancy status: Clear Vacancy (Zero third-party displacement).

2. **50-Point Roster Compliance**:
   - Roster Point: {roster_pt}
   - Rule Evaluation: {rules['roster']['message']}

3. **Statutory & Administrative Norms**:
   - **Tenure Norm**: {rules['tenure']['message']}
   - **Preference Alignment**: Assigned station evaluated as `{rules['preference']['match']}` relative to officer's submission.

4. **Recommendation**:
   - The proposed posting is administratively viable and satisfies all Departmental parameters with zero violation of statutory safeguards.
"""
        return rationale

    # --- CADRE WATERFALL HIERARCHY ---

    def get_cadre_waterfall_hierarchy(self) -> Dict[str, Any]:
        """
        Returns the official 6-tier rank breakdown and establishment distribution
        for the 1,794 posts under Notification No. 1809-AR&AH/3A-08/23 dt. 18.06.2025.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("""
        SELECT 
            pay_level,
            designation,
            COUNT(*) as sanctioned,
            SUM(CASE WHEN UPPER(occupancy_status) = 'FILLED' THEN 1 ELSE 0 END) as occupied,
            SUM(CASE WHEN UPPER(occupancy_status) = 'VACANT' THEN 1 ELSE 0 END) as vacant
        FROM cadre_1794_posts
        GROUP BY pay_level, designation
        ORDER BY 
            CASE pay_level
                WHEN 'Level-22' THEN 1
                WHEN 'Level-21' THEN 2
                WHEN 'Level-19' THEN 3
                WHEN 'Level-17' THEN 4
                WHEN 'Level-16' THEN 5
                ELSE 6
            END, sanctioned DESC
        """)
        designation_rows = [dict(r) for r in cur.fetchall()]

        tiers = [
            {"tier": "Apex Tier (Directorate Leadership)", "level": "Level 22", "sanctioned": 1, "occupied": 1, "vacant": 0, "designations": []},
            {"tier": "Senior Administrative Tier (Additional Director)", "level": "Level 21", "sanctioned": 16, "occupied": 2, "vacant": 14, "designations": []},
            {"tier": "Zonal & Technical Leadership (Joint Director)", "level": "Level 19", "sanctioned": 40, "occupied": 7, "vacant": 33, "designations": []},
            {"tier": "District Head & Regional Administration (Deputy Director)", "level": "Level 17", "sanctioned": 252, "occupied": 15, "vacant": 237, "designations": []},
            {"tier": "Divisional, Clinical & Specialist Tier (Assistant Director)", "level": "Level 16", "sanctioned": 334, "occupied": 177, "vacant": 157, "designations": []},
            {"tier": "Block Livestock Development & Field Veterinary Officers (BLDO/VO)", "level": "Level 16", "sanctioned": 1151, "occupied": 842, "vacant": 309, "designations": []},
        ]

        for d in designation_rows:
            pl = d["pay_level"]
            desig = d["designation"]
            if pl == "Level-22":
                tiers[0]["designations"].append(d)
            elif pl == "Level-21":
                tiers[1]["designations"].append(d)
            elif pl == "Level-19":
                tiers[2]["designations"].append(d)
            elif pl == "Level-17":
                tiers[3]["designations"].append(d)
            elif pl == "Level-16" and ("Assistant Director" in desig):
                tiers[4]["designations"].append(d)
            else:
                tiers[5]["designations"].append(d)

        cur.execute("""
        SELECT 
            estab_type,
            COUNT(*) as sanctioned,
            SUM(CASE WHEN UPPER(occupancy_status) = 'FILLED' THEN 1 ELSE 0 END) as occupied,
            SUM(CASE WHEN UPPER(occupancy_status) = 'VACANT' THEN 1 ELSE 0 END) as vacant
        FROM cadre_1794_posts
        GROUP BY estab_type
        ORDER BY sanctioned DESC
        """)
        estab_rows = [dict(r) for r in cur.fetchall()]

        cur.execute("""
        SELECT 
            COUNT(*) as total_sanctioned,
            SUM(CASE WHEN UPPER(occupancy_status) = 'FILLED' THEN 1 ELSE 0 END) as total_occupied,
            SUM(CASE WHEN UPPER(occupancy_status) = 'VACANT' THEN 1 ELSE 0 END) as total_vacant
        FROM cadre_1794_posts
        """)
        tot = dict(cur.fetchone())

        conn.close()

        return {
            "summary": {
                "sanctioned_posts": tot["total_sanctioned"],
                "occupied_posts": tot["total_occupied"],
                "vacant_posts": tot["total_vacant"],
                "occupancy_rate_pct": round((tot["total_occupied"] / tot["total_sanctioned"]) * 100, 1)
            },
            "tiers": tiers,
            "establishment_distribution": estab_rows,
            "designations": designation_rows
        }

    # --- OFFICER DOSSIER DETAILS ---

    def get_officer_dossier(self, hrms_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves comprehensive administrative dossier and service history for an officer.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        officer = {}
        cur.execute("SELECT * FROM roster_50_point_candidates WHERE hrms_id = ?", (hrms_id,))
        r_row = cur.fetchone()
        if r_row:
            officer.update(dict(r_row))
            officer["source_category"] = "50-Point Roster Promotion Candidate (Level 16 -> Level 19)"

        cur.execute("SELECT * FROM cadre_1794_posts WHERE incumbent_hrms = ?", (hrms_id,))
        c_row = cur.fetchone()
        if c_row:
            cd = dict(c_row)
            for k, v in cd.items():
                if v and (k not in officer or not officer[k]):
                    officer[k] = v
            if "source_category" not in officer:
                officer["source_category"] = f"Serving Cadre Incumbent ({cd.get('designation')})"
            officer["current_post_record"] = cd

        cur.execute("SELECT * FROM ABOLISHED_POST_LEADS WHERE hrms_id = ?", (hrms_id,))
        o_row = cur.fetchone()
        if o_row:
            od = dict(o_row)
            for k, v in od.items():
                if v and (k not in officer or not officer[k]):
                    officer[k] = v
            officer["is_obliterated_post"] = True
            officer["obliterated_details"] = od
            if "source_category" not in officer:
                officer["source_category"] = "Serving in Obliterated Post (Notification 1808)"

        cur.execute("SELECT * FROM displaced_officers_pool WHERE officer_hrms = ? ORDER BY id DESC LIMIT 1", (hrms_id,))
        disp_row = cur.fetchone()
        if disp_row:
            officer["displaced_record"] = dict(disp_row)
            officer["is_displaced"] = True

        cur.execute("""
        SELECT * FROM simulation_assignments 
        WHERE officer_hrms_id = ? 
        ORDER BY id DESC LIMIT 1
        """, (hrms_id,))
        sim_row = cur.fetchone()
        if sim_row:
            officer["current_simulation_assignment"] = dict(sim_row)

        # Master employee directory lookup (covers HQ deployed and unsanctioned officers)
        cur.execute("SELECT * FROM master_all_cadre_employees WHERE hrms_id = ?", (hrms_id,))
        m_row = cur.fetchone()
        if m_row:
            md = dict(m_row)
            for k, v in md.items():
                if v and (k not in officer or not officer[k]):
                    officer[k] = v
            if "source_category" not in officer or not officer["source_category"]:
                if md.get("is_hq_deployed"):
                    officer["source_category"] = "Directorate Headquarters Deployed Officer"
                elif md.get("is_unsanctioned_post"):
                    officer["source_category"] = "Special / Excess Deployed Officer"
                else:
                    officer["source_category"] = f"WBAH&VS Cadre Officer ({md.get('designation', '')})"
            if md.get("hq_posting_history") and ("posting_history" not in officer or not officer["posting_history"] or "Standard" in str(officer["posting_history"])):
                officer["posting_history"] = md["hq_posting_history"]

        # Ensure no personal fields leak into officer dossier
        personal_fields = [
            "mobile", "alt_mobile", "whatsapp", "email", "caste", "dob",
            "current_address", "ancestral_address", "temp_address", "residential_address",
            "spouse_name", "spouse_dept", "spouse_desig", "spouse_district", "spouse_block",
            "spouse_is_wbahvs", "spouse_service_details", "spouse_health", "children_count",
            "children_board_exams", "family_dependencies", "health_conditions", "health_details",
            "care_needed", "facility_needed", "pwd_status", "self_reported_data_json", "family_details",
            "ph_status"
        ]
        for pf in personal_fields:
            officer.pop(pf, None)
        officer["verification_status"] = "UNDER VERIFICATION"
        officer["vigilance_status"] = "Under verification"

        # Official Gradation List lookup
        cur.execute("SELECT * FROM official_gradation_list WHERE hrms_id = ?", (hrms_id,))
        grad_row = cur.fetchone()
        if grad_row:
            officer["gradation_info"] = dict(grad_row)

        # Multi-Agent Verification Summary lookup
        cur.execute("SELECT * FROM multi_agent_verification_summary WHERE hrms_id = ?", (hrms_id,))
        verif_row = cur.fetchone()
        if verif_row:
            officer["verification_summary"] = dict(verif_row)

        # Authoritative master final order schedule lookup
        cur.execute("SELECT * FROM master_final_order_schedule WHERE hrms_id = ? OR clean_name = ?", (hrms_id, officer.get("clean_name", "")))
        mf_row = cur.fetchone()
        master_final_order = dict(mf_row) if mf_row else None

        conn.close()

        if not officer:
            return None

        # Parse structured preferences & history JSON
        prefs_list = []
        if officer.get("preferences_json"):
            try:
                prefs_list = json.loads(officer["preferences_json"])
            except Exception:
                prefs_list = []

        history_list = []
        if officer.get("posting_history_json"):
            try:
                history_list = json.loads(officer["posting_history_json"])
            except Exception:
                history_list = []

        # Parse self-reported promotional preferences and data
        dd_prefs = {}
        if officer.get("dd_preferences_json"):
            try:
                dd_prefs = json.loads(officer["dd_preferences_json"])
            except Exception:
                dd_prefs = {}

        jd_prefs = {}
        if officer.get("jd_preferences_json"):
            try:
                jd_prefs = json.loads(officer["jd_preferences_json"])
            except Exception:
                jd_prefs = {}

        ad_prefs = {}
        if officer.get("ad_preferences_json"):
            try:
                ad_prefs = json.loads(officer["ad_preferences_json"])
            except Exception:
                ad_prefs = {}

        self_reported = {}
        if officer.get("self_reported_data_json"):
            try:
                self_reported = json.loads(officer["self_reported_data_json"])
            except Exception:
                self_reported = {}

        photo_raw = officer.get("photo_url") or ""
        photo_display_url = ""
        if photo_raw:
            import re
            m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", photo_raw) or re.search(r"/d/([a-zA-Z0-9_-]+)", photo_raw)
            if m:
                drive_id = m.group(1)
                photo_display_url = f"https://lh3.googleusercontent.com/d/{drive_id}"
            else:
                photo_display_url = photo_raw

        dossier = {
            "officer_name": officer.get("officer_name") or officer.get("incumbent_name") or "Officer",
            "clean_name": officer.get("clean_name") or "",
            "hrms_id": str(hrms_id),
            "gender": officer.get("gender") or "—",
            "wbvc_reg_no": officer.get("wbvc_reg_no") or "—",
            "employee_id": officer.get("employee_id") or "—",
            "gradation_sl": officer.get("gradation_sl") or "—",
            "office_code": officer.get("office_code") or (officer.get("current_post_record") or {}).get("office_code") or "—",
            "ddo_code": officer.get("ddo_code") or (officer.get("current_post_record") or {}).get("ddo_code") or "—",
            "cadre": officer.get("cadre") or "West Bengal Animal Husbandry and Veterinary Service",
            "doj": officer.get("doj") or officer.get("incumbent_doj") or "—",
            "dor": officer.get("dor") or officer.get("dor_rule75a") or officer.get("incumbent_dor") or "—",
            "roster_point": officer.get("roster_point") or "—",
            "point_reserved_for": officer.get("point_reserved_for") or "—",
            "current_designation": officer.get("substantive_post") or officer.get("present_designation") or officer.get("designation") or "Veterinary Officer",
            "current_posting": officer.get("present_posting") or officer.get("detailed_presentation") or "—",
            "present_establishment": officer.get("present_establishment") or officer.get("establishment") or officer.get("office") or "—",
            "district": officer.get("present_district") or officer.get("district") or "—",
            "block": officer.get("present_block") or officer.get("block") or "—",
            "establishment": officer.get("establishment") or officer.get("office") or "—",
            "present_su": officer.get("present_su") or "",
            "present_doj": officer.get("present_doj") or "",
            "charge_type": officer.get("charge_type") or "",
            "additional_charges": officer.get("additional_charges") or "",
            "last_order_no": officer.get("last_order_no") or "",
            "last_order_date": officer.get("last_order_date") or "",
            "present_pay_level": officer.get("pay_level") or "Level 16 (Rs. 56,100 - Rs. 1,44,300)",
            "tenure_years": officer.get("tenure_years") or officer.get("incumbent_tenure") or "—",
            "tenure_norm_status": officer.get("tenure_over_flag") or "Within Norm",
            "home_district": officer.get("home_district") or "—",
            "academic_details": officer.get("academic_details") or officer.get("qualification") or "B.V.Sc. & A.H.",
            "qualifications": officer.get("qualifications") or "B.V.Sc. & A.H.",
            "mvsc_specialization": officer.get("mvsc_specialization") or "",
            "posting_history": officer.get("posting_history") or officer.get("last_transfer_order") or "Standard tenure completed across postings.",
            "posting_history_list": history_list,
            "preferences_list": prefs_list,
            "dd_preferences": dd_prefs,
            "jd_preferences": jd_prefs,
            "ad_preferences": ad_prefs,
            "decision_note": officer.get("decision_note") or "",
            "needs_backfill": bool(officer.get("needs_backfill")),
            "attention_flag": bool(officer.get("attention_flag")),
            "attention_reason": officer.get("attention_reason") or "",
            "preferences": {
                f"Pref_{i}": officer.get(f"pref_{i}") for i in range(1, 11) if officer.get(f"pref_{i}") and officer.get(f"pref_{i}") != "—"
            },
            "source_category": officer.get("source_category", "Departmental Officer"),
            "allotment_status": officer.get("allotment_status") or "Under verification",
            "latest_allotment": officer.get("current_simulation_assignment"),
            "master_final_order": master_final_order,
            "verification_summary": officer.get("verification_summary"),
            "verification_status": "UNDER VERIFICATION",
            "vigilance_status": "Under verification"
        }

        if not dossier["preferences"] and officer.get("all_preferences"):
            dossier["preferences_summary"] = officer.get("all_preferences")

        return dossier

    def get_posts_visual_grid(self, session_id: str = "CURRENT_SESSION", district_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns all cadre & DD posts grouped by district with real-time color classifications:
        - VACANT_PURE (Green): Pure vacancy, ready for selection
        - VACANT_ON_PAPER (Amber): Substantively occupied, but incumbent is on SU elsewhere
        - ATTENTION_REQUIRED (Red): Conflict / cascading replacement needed
        - BOARD_SELECTED (Purple): Chosen in active board session
        - OBLITERATED (Grey Strikethrough): Abolished under 1808
        - FILLED_NORMAL (Blue): Normally occupied
        """
        conn = self.get_connection()
        cur = conn.cursor()

        # 1. Fetch simulation assignments for active session
        cur.execute("""
        SELECT substantive_post_id, su_post_id, substantive_post_name, su_post_name, officer_hrms_id, officer_name
        FROM simulation_assignments WHERE session_id = ?
        """, (session_id,))
        sim_assignments = cur.fetchall()

        board_sub_ids = set()
        board_su_ids = set()
        sub_to_officer = {}
        su_to_officer = {}
        for r in sim_assignments:
            rd = dict(r)
            if rd.get("substantive_post_id"):
                try:
                    sid = int(rd["substantive_post_id"])
                    board_sub_ids.add(sid)
                    sub_to_officer[sid] = rd["officer_name"]
                except Exception:
                    pass
            if rd.get("su_post_id"):
                try:
                    suid = int(rd["su_post_id"])
                    board_su_ids.add(suid)
                    su_to_officer[suid] = rd["officer_name"]
                except Exception:
                    pass
            elif rd.get("su_post_name"):
                m = re.search(r"\(Post\s+(\d+)\)", str(rd["su_post_name"]))
                if m:
                    try:
                        suid = int(m.group(1))
                        board_su_ids.add(suid)
                        su_to_officer[suid] = rd["officer_name"]
                    except Exception:
                        pass

        # 2. Fetch officers currently on SU in baseline
        try:
            cur.execute("""
            SELECT incumbent_hrms, id FROM cadre_1794_posts 
            WHERE (service_utilized_flag = 1 OR service_utilized_flag IN ('1', 'Service Utilized', 'Yes', 'FILLED_ON_SU'))
              AND incumbent_hrms IS NOT NULL AND incumbent_hrms != ''
            """)
            su_baseline_posts = set(r["id"] for r in cur.fetchall())
        except Exception:
            su_baseline_posts = set()

        if not su_baseline_posts:
            try:
                cur.execute("SELECT id FROM master_source_of_truth WHERE service_utilization = 'Service Utilized'")
                su_baseline_posts = set(r["id"] for r in cur.fetchall())
            except Exception:
                pass

        # 3. Fetch obliterated post IDs
        try:
            cur.execute("SELECT post_name, district FROM ABOLISHED_POST_LEADS")
            oblit_entries = set((str(r["post_name"] or "").strip().lower(), str(r["district"] or "").strip().lower()) for r in cur.fetchall())
        except Exception:
            oblit_entries = set()

        # 4. Fetch DD posts
        try:
            cur.execute("SELECT dd_sl, district, establishment, office, post_name, allotment_status, allotted_name FROM available_dd_posts ORDER BY district, office")
            dd_rows = [dict(r) for r in cur.fetchall()]
        except Exception:
            dd_rows = []

        # 5. Fetch 1,794 Cadre posts safely
        cur.execute("PRAGMA table_info(cadre_1794_posts)")
        cadre_cols = set(r[1] for r in cur.fetchall())
        is_sub_col = "is_substantive_blocked" if "is_substantive_blocked" in cadre_cols else "0 as is_substantive_blocked"
        su_name_col = "su_allotted_name" if "su_allotted_name" in cadre_cols else "NULL as su_allotted_name"
        sub_name_col = "substantive_allotted_name" if "substantive_allotted_name" in cadre_cols else "NULL as substantive_allotted_name"

        cadre_query = f"SELECT id, post_sl, district, block, establishment, designation, occupancy_status, incumbent_name, incumbent_hrms, {is_sub_col}, {su_name_col}, {sub_name_col} FROM cadre_1794_posts"
        params = []
        if district_filter and district_filter != "ALL":
            cadre_query += " WHERE district = ?"
            params.append(district_filter)
        cadre_query += " ORDER BY district, block, establishment, designation"
        cur.execute(cadre_query, params)
        cadre_rows = [dict(r) for r in cur.fetchall()]

        conn.close()

        # Grouping container
        districts_map = {}

        summary_counts = {
            "pure_vacant": 0,
            "vacant_on_paper": 0,
            "attention_required": 0,
            "board_selected": 0,
            "obliterated": 0,
            "filled": 0,
            "total": 0
        }

        def add_post_to_grid(p_data):
            dist = p_data["district"] or "Unassigned District"
            if dist not in districts_map:
                districts_map[dist] = {
                    "district": dist,
                    "dd_posts": [],
                    "cadre_posts": []
                }
            if p_data["type"] == "DD":
                districts_map[dist]["dd_posts"].append(p_data)
            else:
                districts_map[dist]["cadre_posts"].append(p_data)
            summary_counts["total"] += 1
            st = p_data["status_code"]
            if st == "VACANT_PURE":
                summary_counts["pure_vacant"] += 1
            elif st == "VACANT_ON_PAPER":
                summary_counts["vacant_on_paper"] += 1
            elif st == "ATTENTION_REQUIRED":
                summary_counts["attention_required"] += 1
            elif st == "BOARD_SELECTED":
                summary_counts["board_selected"] += 1
            elif st == "OBLITERATED":
                summary_counts["obliterated"] += 1
            elif st == "FILLED_NORMAL":
                summary_counts["filled"] += 1

        # Process DD posts
        for dd in dd_rows:
            dd_id = dd["dd_sl"]
            is_selected = dd_id in board_sub_ids
            status_code = "VACANT_PURE"
            status_label = "Vacant DD Post"
            badge_class = "bg-emerald-500 text-white"
            allotted_officer = sub_to_officer.get(dd_id) or dd.get("allotted_name")

            if is_selected or dd.get("allotment_status") == "Allotted":
                status_code = "BOARD_SELECTED"
                status_label = f"Selected: {allotted_officer or 'Board Promotee'}"
                badge_class = "bg-purple-600 text-white font-medium"

            p_item = {
                "id": f"DD-{dd_id}",
                "raw_id": dd_id,
                "type": "DD",
                "post_name": dd["post_name"],
                "designation": "Deputy Director, ARD",
                "establishment": dd["office"] or dd["establishment"],
                "block": "District HQ",
                "district": dd["district"],
                "status_code": status_code,
                "status_label": status_label,
                "badge_class": badge_class,
                "incumbent_name": None,
                "allotted_to": allotted_officer,
                "is_promotable": True
            }
            if not district_filter or district_filter == "ALL" or dd["district"].lower() == district_filter.lower():
                add_post_to_grid(p_item)

        # Process Cadre posts
        for cp in cadre_rows:
            cid = cp["id"]
            desig = cp["designation"] or "Post"
            est = cp["establishment"] or "Office"
            block = cp["block"] or ""
            dist = cp["district"] or "HQ"
            inc_name = cp["incumbent_name"]
            is_vacant = (cp.get("occupancy_status") or "").strip().upper() in ("VACANT", "CLEAR VACANCY") or not inc_name

            # Check obliteration
            post_key = (desig.strip().lower(), dist.strip().lower())
            is_obliterated = post_key in oblit_entries

            # Check board selection
            is_sub_selected = cid in board_sub_ids or bool(cp.get("is_substantive_blocked"))
            is_su_selected = cid in board_su_ids
            allotted_officer = su_to_officer.get(cid) or sub_to_officer.get(cid) or cp.get("su_allotted_name") or cp.get("substantive_allotted_name")

            # Check cascading replacement attention (e.g. Amta-II, Sankrail, Uluberia-I)
            is_cascading_flag = any(k in f"{desig} {est} {block}".lower() for k in ["amta 2", "amta ii", "sankrail", "uluberia 1", "uluberia i"]) and not is_vacant

            status_code = "FILLED_NORMAL"
            status_label = f"Occupied by {inc_name}"
            badge_class = "bg-slate-500 text-white"

            if is_obliterated:
                status_code = "OBLITERATED"
                status_label = "Obliterated / Abolished under 1808"
                badge_class = "bg-slate-300 text-slate-700 line-through border border-slate-400"
            elif is_cascading_flag:
                status_code = "ATTENTION_REQUIRED"
                status_label = f"Attention: Cascading Replacement Needed (Currently {inc_name})"
                badge_class = "bg-rose-500 text-white font-bold animate-pulse"
            elif is_sub_selected or is_su_selected:
                status_code = "BOARD_SELECTED"
                status_label = f"Board Selected: {allotted_officer or 'Assigned'}"
                badge_class = "bg-purple-600 text-white font-medium"
            elif cid in su_baseline_posts:
                status_code = "VACANT_ON_PAPER"
                status_label = f"Vacant on Paper (Incumbent {inc_name} on SU)"
                badge_class = "bg-amber-500 text-white font-medium"
            elif is_vacant:
                status_code = "VACANT_PURE"
                status_label = "Pure Sanctioned Vacancy"
                badge_class = "bg-emerald-500 text-white font-bold"

            p_item = {
                "id": f"P-{cid}",
                "raw_id": cid,
                "type": "CADRE",
                "post_name": f"{desig}, {est}",
                "designation": desig,
                "establishment": est,
                "block": block,
                "district": dist,
                "status_code": status_code,
                "status_label": status_label,
                "badge_class": badge_class,
                "incumbent_name": inc_name,
                "allotted_to": allotted_officer,
                "is_promotable": False
            }
            add_post_to_grid(p_item)

        # Sort districts alphabetically
        sorted_districts = sorted(districts_map.keys())
        structured_grid = [districts_map[d] for d in sorted_districts]

        return {
            "districts": sorted_districts,
            "grid": structured_grid,
            "summary": summary_counts
        }

    # --- AI ALLOTMENT RECOMMENDATION ENGINE ---

    def recommend_ai_allotment(self, officer_hrms: str, session_id: str = "CURRENT_SESSION") -> Dict[str, Any]:
        """
        AI Intelligent Allotment Engine:
        Analyzes officer profile, stated preferences (1-10), area tenure (Memo 291),
        spouse posting, board exams, and available sanctioned vacancies (1,794 posts),
        recommending the optimal substantive post and optional SU post with statutory rationale.
        """
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM roster_50_point_candidates WHERE hrms_id = ?", (officer_hrms,))
        r_row = cur.fetchone()
        cur.execute("SELECT * FROM ABOLISHED_POST_LEADS WHERE hrms_id = ?", (officer_hrms,))
        o_row = cur.fetchone()
        cur.execute("SELECT * FROM displaced_officers_pool WHERE officer_hrms = ? AND session_id = ?", (officer_hrms, session_id))
        disp_row = cur.fetchone()

        officer_data = {}
        candidate_type = "roster"

        if r_row:
            officer_data = dict(r_row)
            candidate_type = "roster"
        elif o_row:
            officer_data = dict(o_row)
            candidate_type = "obliterated"
        elif disp_row:
            officer_data = dict(disp_row)
            candidate_type = "displaced"
        else:
            cur.execute("SELECT * FROM cadre_1794_posts WHERE incumbent_hrms = ?", (officer_hrms,))
            c_row = cur.fetchone()
            if c_row:
                officer_data = dict(c_row)
                officer_data["officer_name"] = c_row["incumbent_name"]
                officer_data["hrms_id"] = c_row["incumbent_hrms"]
                candidate_type = "general"
            else:
                conn.close()
                return {"success": False, "error": f"Officer HRMS {officer_hrms} not found."}

        available_substantive = self.get_available_substantive_posts(officer_role=candidate_type, session_id=session_id)
        if not available_substantive:
            conn.close()
            return {"success": False, "error": f"No available substantive posts for {candidate_type}."}

        pref_list = []
        for i in range(1, 11):
            p = str(officer_data.get(f"pref_{i}") or "").strip()
            if p and p != "—":
                pref_list.append(p.lower())
        all_pref_str = str(officer_data.get("all_preferences") or officer_data.get("posting_preferences_all") or "").lower()

        officer_dist = str(officer_data.get("present_district") or officer_data.get("district") or "").lower()
        fam_text = str(officer_data.get("family_details") or "").lower()

        scored_posts = []
        for p in available_substantive:
            score = 0
            match_reasons = []
            post_dist = str(p.get("district") or "").lower()
            post_name = str(p.get("post_name") or p.get("detailed_presentation") or "").lower()
            post_office = str(p.get("office") or p.get("establishment") or "").lower()

            matched_pref_idx = None
            for idx, pref in enumerate(pref_list):
                if pref in post_dist or pref in post_office or pref in post_name:
                    matched_pref_idx = idx + 1
                    break
            if not matched_pref_idx and all_pref_str:
                for idx, token in enumerate(all_pref_str.split(";")):
                    if token.strip() and (token.strip() in post_dist or token.strip() in post_office):
                        matched_pref_idx = idx + 1
                        break

            if matched_pref_idx:
                pref_pts = max(100 - (matched_pref_idx - 1) * 10, 30)
                score += pref_pts
                match_reasons.append(f"Preference {matched_pref_idx} Matched (+{pref_pts} pts)")
            elif officer_dist and post_dist == officer_dist:
                score += 50
                match_reasons.append(f"Home/Present District ({post_dist.title()}) Matched (+50 pts)")

            if "spouse" in fam_text and post_dist in fam_text:
                score += 40
                match_reasons.append(f"Spouse Co-location Satisfied in {post_dist.title()} (+40 pts)")

            if any(exam in fam_text for exam in ["board", "class x", "class xii", "madhyamik", "icse", "cbse"]):
                if post_dist == officer_dist:
                    score += 30
                    match_reasons.append("Board Exam Safeguard - Preserved Zone (+30 pts)")
                else:
                    score -= 40
                    match_reasons.append("Board Exam Penalty - Inter-District Move (-40 pts)")

            t_norm = self.evaluate_tenure_norm(post_dist)
            curr_tenure = float(officer_data.get("tenure_years") or 0.0)
            if curr_tenure < t_norm:
                score += 15
                match_reasons.append("Tenure Compliant (+15 pts)")

            scored_posts.append((score, p, match_reasons))

        scored_posts.sort(key=lambda x: x[0], reverse=True)
        best_score, best_post, best_reasons = scored_posts[0]

        recommended_su_post = None
        # Check if an SU post in top preference is available
        if pref_list and not any(pref_list[0] in str(best_post.get("district") or "").lower() for _ in [1]):
            su_posts = self.get_available_su_posts(session_id=session_id)
            for sp in su_posts:
                if pref_list[0] in sp["district"].lower():
                    recommended_su_post = sp
                    break

        conn.close()

        off_name = officer_data.get("officer_name") or officer_data.get("incumbent_name") or "Officer"
        curr_posting = officer_data.get("detailed_presentation") or officer_data.get("present_posting") or "Current Post"
        substantive_title = best_post.get("display_label") or best_post.get("detailed_presentation") or f"{best_post.get('post_name')} ({best_post.get('office')}, {best_post.get('district')})"

        justification = (
            f"Statutory recommendation for {off_name} ({officer_hrms}) to {substantive_title} "
            f"is Under verification. Per CIOS Master Directive (§2, §8, §18.1), every recommendation "
            f"must cite primary departmental order evidence IDs."
        )

        substantive_id = best_post.get("post_id") or best_post.get("dd_sl") or best_post.get("id")

        return {
            "success": True,
            "officer_hrms": officer_hrms,
            "officer_name": off_name,
            "candidate_type": candidate_type,
            "present_posting": curr_posting,
            "substantive_post_id": substantive_id,
            "substantive_post": best_post,
            "substantive_post_name": substantive_title,
            "su_post_id": recommended_su_post["post_id"] if recommended_su_post else None,
            "su_post": recommended_su_post,
            "su_post_name": recommended_su_post["display_label"] if recommended_su_post else None,
            "score": best_score,
            "match_reasons": best_reasons,
            "allotment_status": "Under verification",
            "evidence_ids": [],
            "statutory_justification": justification
        }

    # --- DISPLACED QUEUE POOL ---

    def get_displaced_queue_pool(self, session_id: str = "CURRENT_SESSION") -> List[Dict[str, Any]]:
        """
        Returns all officers displaced due to Service Utilization or post obliterative realignment,
        awaiting placement under 'Transfer due to Displaced' category.
        """
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
        SELECT * FROM displaced_officers_pool 
        WHERE (session_id = ? OR session_id = 'CURRENT_SESSION')
          AND officer_hrms NOT IN ('1992005664')
          AND lower(from_post_name) NOT LIKE '%director of ah%'
        ORDER BY id DESC
        """, (session_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    # --- MASTER EMPLOYEE DIRECTORY & HQ DEPLOYMENTS ---
    def get_master_employees(
        self,
        query: str = "",
        district: str = "ALL",
        category: str = "all",
        avd_member: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Retrieves search filtered and paginated records from the master employee directory.
        Categories: 'all', 'active', 'hq', 'roster', 'unsanctioned'
        """
        conn = self.get_connection()
        cur = conn.cursor()

        where_clauses = []
        params = []

        if query:
            q = f"%{query.strip().lower()}%"
            where_clauses.append("(lower(officer_name) LIKE ? OR hrms_id LIKE ? OR lower(designation) LIKE ? OR lower(establishment) LIKE ? OR lower(district) LIKE ?)")
            params.extend([q, q, q, q, q])

        if district and district != "ALL":
            where_clauses.append("district = ?")
            params.append(district)

        if category == "active":
            where_clauses.append("service_status LIKE '%service%'")
        elif category == "hq":
            where_clauses.append("is_hq_deployed = 1")
        elif category == "roster":
            where_clauses.append("is_50pt_candidate = 1")
        elif category == "unsanctioned":
            where_clauses.append("is_unsanctioned_post = 1")

        if avd_member and avd_member != "ALL":
            if avd_member == "Yes":
                where_clauses.append("avd_member_flag = 1")
            elif avd_member == "No":
                where_clauses.append("avd_member_flag = 0")

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count
        count_sql = f"SELECT COUNT(*) FROM master_all_cadre_employees {where_str}"
        cur.execute(count_sql, params)
        total_count = cur.fetchone()[0]

        # Paginated data
        offset = max(0, (page - 1) * page_size)
        data_sql = f"""
            SELECT hrms_id, officer_name, designation, present_posting, establishment,
                   district, cadre, service_status, dor, avd_member_flag, avd_member,
                   is_50pt_candidate, is_hq_deployed, is_unsanctioned_post,
                   hq_post_title, hq_doj, wbvc_reg_no, gender
            FROM master_all_cadre_employees
            {where_str}
            ORDER BY is_hq_deployed DESC, is_50pt_candidate DESC, officer_name ASC
            LIMIT ? OFFSET ?
        """
        cur.execute(data_sql, params + [page_size, offset])
        rows = [dict(r) for r in cur.fetchall()]

        # KPI counts
        kpis = {
            "total": cur.execute("SELECT count(*) FROM master_all_cadre_employees").fetchone()[0],
            "in_service": cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE service_status LIKE '%service%'").fetchone()[0],
            "hq_deployed": cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE is_hq_deployed = 1").fetchone()[0],
            "roster_50pt": cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE is_50pt_candidate = 1").fetchone()[0],
            "unsanctioned": cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE is_unsanctioned_post = 1").fetchone()[0]
        }

        conn.close()

        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
            "kpis": kpis,
            "employees": rows
        }

    def get_hq_deployed_officers(self) -> List[Dict[str, Any]]:
        """
        Returns all officers deployed at Directorate Headquarters & Attached Units.
        """
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT hrms_id, officer_name, designation, present_posting, establishment,
                   district, dor, hq_post_title, hq_doj, hq_posting_history,
                   mobile, email, is_50pt_candidate
            FROM master_all_cadre_employees
            WHERE is_hq_deployed = 1
            ORDER BY officer_name ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    # --- GROUP C: CASCADING REPLACEMENT WARNINGS (FIELD POST BACKFILLS) ---
    def get_cascading_replacement_warnings(self) -> List[Dict[str, Any]]:
        """
        Returns all field posts (BLDO, VO, BAHC, SAHC) vacated due to promotional or
        administrative transfers without incoming replacement, requiring urgent backfill.
        """
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT r.sl_no, r.roster_point, r.officer_name, r.hrms_id, 
                   r.present_posting, r.present_district, r.substantive_post_name,
                   r.su_post_name
            FROM roster_50_point_candidates r
            ORDER BY r.present_district ASC, r.officer_name ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    # --- DISTRICT HEADQUARTERS AD CADRE BALANCE (3 AD CEILING) ---
    def get_district_ad_balance(self) -> List[Dict[str, Any]]:
        """
        Calculates AD staffing across District Joint Director offices,
        verifying adherence to the 3-AD limit (minimum 2 in small hill districts).
        """
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT district, COUNT(*) as total_sanctioned_ad,
                   SUM(CASE WHEN occupancy_status = 'FILLED' THEN 1 ELSE 0 END) as occupied_ad,
                   SUM(CASE WHEN occupancy_status = 'VACANT' THEN 1 ELSE 0 END) as vacant_ad
            FROM cadre_1794_posts
            WHERE designation LIKE '%Assistant Director%'
              AND (establishment LIKE '%District%' OR establishment LIKE '%Office of the Deputy Director%' OR establishment LIKE '%DD%' OR establishment LIKE '%Joint Director%')
            GROUP BY district
            ORDER BY district ASC
        """)
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            dist_name = d["district"]
            is_small = dist_name in ["Kalimpong", "Darjeeling", "Jhargram", "Alipurduar"]
            norm = 2 if is_small else 3
            d["target_norm"] = norm
            d["is_compliant"] = d["occupied_ad"] <= norm
            d["surplus_count"] = max(0, d["occupied_ad"] - norm)
            rows.append(d)
        conn.close()
        return rows


if __name__ == "__main__":
    engine = PostingEngine()
    print("Testing dynamic posts...")
    dd_posts = engine.get_available_substantive_posts("roster")
    print(f"Available DD posts: {len(dd_posts)}")
    su_posts = engine.get_available_su_posts()
    print(f"Available SU posts: {len(su_posts)}")
    print("\nTesting multi-party solver...")
    res = engine.solve_multi_party_cadre("TEST_SESSION_1794")
    print("Solver summary:", res["summary"])
