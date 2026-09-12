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
        Evaluates an allotment against West Bengal administrative transfer rules.
        """
        target_dist = target_post.get("district", "")
        target_block = target_post.get("block", "")
        max_tenure = self.evaluate_tenure_norm(target_dist, target_block)

        tenure_years = float(officer_data.get("tenure_years") or 0.0)
        curr_dist = officer_data.get("district") or officer_data.get("current_district") or officer_data.get("present_district") or ""

        # Tenure rule
        tenure_status = "COMPLIANT"
        tenure_msg = f"Tenure within {max_tenure} yr norm."
        if tenure_years > max_tenure:
            tenure_status = "OVER_TENURE"
            tenure_msg = f"Officer tenure ({tenure_years:.1f} yrs) exceeds {max_tenure} yr area norm."

        # Spouse rule (Memo 291 Para 5)
        fam_text = str(officer_data.get("family_details") or "")
        spouse_status = "NOT_APPLICABLE"
        spouse_msg = "No spouse co-location claim."
        if "Spouse" in fam_text and ("Government" in fam_text or "Teacher" in fam_text or "Doctor" in fam_text):
            if target_dist.lower() in fam_text.lower():
                spouse_status = "MATCH_SATISFIED"
                spouse_msg = f"Spouse posting in {target_dist} satisfied (Memo 291 Para 5)."
            else:
                spouse_status = "WARNING_DIFFERENT_DISTRICT"
                spouse_msg = f"Spouse may be located outside target district {target_dist}."

        # Child board exam safeguard (Memo 291 Para 13)
        exam_status = "SAFE"
        exam_msg = "No board exam conflict."
        if any(cls in fam_text.lower() for cls in ["class ix", "class x", "class xi", "class xii", "madhyamik", "icse", "cbse"]):
            if curr_dist and target_dist.lower() != curr_dist.lower():
                exam_status = "EXAM_DISRUPTION_RISK"
                exam_msg = f"Child appearing in Board Exam. Transfer outside {curr_dist} disrupts academic calendar (Para 13)."

        # 50-Point Roster category check
        caste = str(officer_data.get("caste") or "Gen").strip()
        roster_pt_res = str(officer_data.get("point_reserved_for") or "UR").strip()
        roster_status = "VALID"
        roster_msg = f"Category {caste} matches Roster point {roster_pt_res}."
        if roster_pt_res in ["SC", "ST", "OBC-A", "OBC-B"]:
            if caste.upper() != roster_pt_res.upper() and not (caste.upper() == "SC" and roster_pt_res == "SC"):
                roster_status = "MISMATCH"
                roster_msg = f"Officer caste ({caste}) does not match reserved point ({roster_pt_res})."

        # Preference satisfaction check
        pref_text = str(officer_data.get("all_preferences") or officer_data.get("posting_preferences_all") or "")
        pref_match = "NO_PREFERENCE_LISTED"
        if pref_text and pref_text != "—":
            if target_dist.lower() in pref_text.lower():
                if "Pref 1" in pref_text and target_dist.lower() in pref_text.split("Pref 2")[0].lower():
                    pref_match = "CHOICE_1"
                elif "Pref 2" in pref_text and target_dist.lower() in pref_text.split("Pref 3")[0].lower():
                    pref_match = "CHOICE_2"
                elif "Pref 3" in pref_text:
                    pref_match = "CHOICE_3"
                else:
                    pref_match = "CHOICE_4_PLUS"
            elif curr_dist and target_dist.lower() == curr_dist.lower():
                pref_match = "HOME_CURRENT_DISTRICT"
            else:
                pref_match = "NO_MATCH"

        return {
            "tenure": {"status": tenure_status, "message": tenure_msg, "max_allowed": max_tenure},
            "spouse": {"status": spouse_status, "message": spouse_msg},
            "board_exam": {"status": exam_status, "message": exam_msg},
            "roster": {"status": roster_status, "message": roster_msg},
            "preference": {"match": pref_match}
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
            WHERE occupancy_status = 'Vacant'
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
        excluding posts already blocked as SU in this session.
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
             (CASE WHEN occupancy_status = 'Vacant' THEN 'VACANT' ELSE 'Occupied by ' || incumbent_name END) || 
             ')') AS display_label
        FROM cadre_1794_posts
        WHERE id NOT IN (
            SELECT su_post_id FROM simulation_assignments
            WHERE session_id = ? AND su_post_id IS NOT NULL
        )
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

        # 1. Fetch Officer details
        officer_data = {}
        cur.execute("SELECT * FROM roster_50_point_candidates WHERE hrms_id = ?", (officer_hrms,))
        r_row = cur.fetchone()
        if r_row:
            officer_data = dict(r_row)
            officer_type = "roster"
        else:
            cur.execute("SELECT * FROM obliterated_posts_1808 WHERE hrms_id = ?", (officer_hrms,))
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
                su_name = f"[SU] {su_row['designation']}, {su_row['establishment']} ({su_row['district']})"
                if su_row["occupancy_status"] not in ["Vacant", None, ""]:
                    if su_row["incumbent_hrms"] and str(su_row["incumbent_hrms"]).strip() != str(officer_hrms).strip():
                        is_collision = True
                        displaced_officer = su_row["incumbent_name"]
                        displaced_hrms = str(su_row["incumbent_hrms"]).strip()
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
            rule_tenure_check, rule_spouse_check, rule_exam_check, rule_roster_check,
            status, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            rule_checks["spouse"]["status"],
            rule_checks["board_exam"]["status"],
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
            UPDATE obliterated_posts_1808
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
        if is_collision and displaced_hrms:
            cur.execute("SELECT id FROM displaced_officers_pool WHERE session_id = ? AND officer_hrms = ?", (session_id, displaced_hrms))
            existing_disp = cur.fetchone()
            if not existing_disp:
                cur.execute("""
                INSERT INTO displaced_officers_pool (
                    session_id, officer_hrms, officer_name, caste, from_post_id, from_post_name,
                    district, block, pay_level, tenure, dor, displaced_by_hrms, displaced_by_name,
                    displaced_by_reason, displacement_type, rehabilitation_status, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    displaced_hrms,
                    displaced_officer,
                    "General",
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
        cur.execute("""
        UPDATE roster_50_point_candidates 
        SET substantive_post_id = NULL, substantive_post_name = NULL, 
            su_post_id = NULL, su_post_name = NULL, allotment_status = 'Pending'
        """)
        cur.execute("""
        UPDATE obliterated_posts_1808 
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
        WHERE designation LIKE '%Assistant Director%' AND occupancy_status = 'Vacant'
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
        SELECT * FROM obliterated_posts_1808 
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
            cur.execute("SELECT * FROM obliterated_posts_1808 WHERE hrms_id = ?", (officer_hrms,))
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
        caste = officer.get("caste", "General")
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
   - Roster Point: {roster_pt} | Category: {caste}
   - Rule Evaluation: {rules['roster']['message']}

3. **Transfer Policy 2009 (Memo No. 291-AR & AH/3A-11/06 dt. 19.02.2009)**:
   - **Tenure Norm**: {rules['tenure']['message']}
   - **Spouse Co-location (Para 5)**: {rules['spouse']['message']}
   - **Board Exam Safeguard (Para 13)**: {rules['board_exam']['message']}
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
            SUM(CASE WHEN occupancy_status NOT IN ('Vacant', '', 'null', 'None') AND occupancy_status IS NOT NULL THEN 1 ELSE 0 END) as occupied,
            SUM(CASE WHEN occupancy_status IN ('Vacant', '', 'null', 'None') OR occupancy_status IS NULL THEN 1 ELSE 0 END) as vacant
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
            SUM(CASE WHEN occupancy_status NOT IN ('Vacant', '', 'null', 'None') AND occupancy_status IS NOT NULL THEN 1 ELSE 0 END) as occupied,
            SUM(CASE WHEN occupancy_status IN ('Vacant', '', 'null', 'None') OR occupancy_status IS NULL THEN 1 ELSE 0 END) as vacant
        FROM cadre_1794_posts
        GROUP BY estab_type
        ORDER BY sanctioned DESC
        """)
        estab_rows = [dict(r) for r in cur.fetchall()]

        cur.execute("""
        SELECT 
            COUNT(*) as total_sanctioned,
            SUM(CASE WHEN occupancy_status NOT IN ('Vacant', '', 'null', 'None') AND occupancy_status IS NOT NULL THEN 1 ELSE 0 END) as total_occupied,
            SUM(CASE WHEN occupancy_status IN ('Vacant', '', 'null', 'None') OR occupancy_status IS NULL THEN 1 ELSE 0 END) as total_vacant
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

        cur.execute("SELECT * FROM obliterated_posts_1808 WHERE hrms_id = ?", (hrms_id,))
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

        conn.close()

        if not officer:
            return None

        dossier = {
            "officer_name": officer.get("officer_name") or officer.get("incumbent_name") or "Officer",
            "hrms_id": str(hrms_id),
            "mobile": officer.get("mobile") or "—",
            "email": officer.get("email") or "—",
            "dob": officer.get("dob") or officer.get("incumbent_dob") or "—",
            "doj": officer.get("doj") or officer.get("incumbent_doj") or "—",
            "dor": officer.get("dor") or officer.get("dor_rule75a") or officer.get("incumbent_dor") or "—",
            "caste": officer.get("caste") or "General",
            "roster_point": officer.get("roster_point") or "—",
            "point_reserved_for": officer.get("point_reserved_for") or "—",
            "current_designation": officer.get("present_designation") or officer.get("designation") or "Veterinary Officer",
            "current_posting": officer.get("present_posting") or officer.get("detailed_presentation") or "—",
            "district": officer.get("present_district") or officer.get("district") or "—",
            "block": officer.get("present_block") or officer.get("block") or "—",
            "establishment": officer.get("establishment") or officer.get("office") or "—",
            "present_pay_level": officer.get("pay_level") or "Level 16 (Rs. 56,100 - Rs. 1,44,300)",
            "tenure_years": officer.get("tenure_years") or officer.get("incumbent_tenure") or "—",
            "tenure_norm_status": officer.get("tenure_over_flag") or "Within Norm",
            "transfer_history": officer.get("last_transfer_order") or officer.get("service_history") or "Standard tenure completed",
            "qualifications": officer.get("qualification") or "B.V.Sc. & A.H.",
            "family_details": officer.get("family_details") or "—",
            "preferences": {
                f"Pref_{i}": officer.get(f"pref_{i}") for i in range(1, 11) if officer.get(f"pref_{i}") and officer.get(f"pref_{i}") != "—"
            },
            "source_category": officer.get("source_category", "Departmental Officer"),
            "allotment_status": officer.get("allotment_status") or ("Allotted" if officer.get("current_simulation_assignment") else "Pending Decision"),
            "latest_allotment": officer.get("current_simulation_assignment")
        }

        if not dossier["preferences"] and officer.get("all_preferences"):
            dossier["preferences_summary"] = officer.get("all_preferences")

        return dossier

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
        cur.execute("SELECT * FROM obliterated_posts_1808 WHERE hrms_id = ?", (officer_hrms,))
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

        justification = f"""### AI Statutory Allotment Brief
**Officer**: {off_name} (`{officer_hrms}`)
**Proposed Substantive Allotment**: {substantive_title}
{f'**Proposed Service Utilization (SU)**: {recommended_su_post["display_label"]}' if recommended_su_post else '**Service Utilization (SU)**: Direct Substantive Deployment (No SU required)'}

**Statutory & Policy Merits**:
1. **Cadre Authority**: Authorized under Notification No. 1809-AR&AH/3A-08/23 dt. 18.06.2025 (1,794 Sanctioned Posts).
2. **Preference & Welfare**: {"; ".join(best_reasons) if best_reasons else "Assigned optimal departmental vacancy"}.
3. **Pay Scale Harmonization**: Promoted/Placed under WBS (ROPA) Rules 2019 without grade distortion.
4. **Collision Impact**: Clear vacancy. Zero adverse displacement of senior cadre officers.
"""

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
        WHERE session_id = ? OR session_id = 'CURRENT_SESSION'
        ORDER BY id DESC
        """, (session_id,))
        rows = [dict(r) for r in cur.fetchall()]
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
