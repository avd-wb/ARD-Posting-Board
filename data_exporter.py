"""
WB ARD Department - Smart Posting Decision Board
Departmental Data Exporter & Executive Report Builder
Supports dynamic multi-criteria filtering, multi-field sorting, custom column projection,
and high-fidelity export to formatted Excel (.xlsx) and Word (.docx) documents.
"""

import os
import io
import datetime
import sqlite3
from typing import Dict, List, Any, Optional, Tuple

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ard_master_truth.db")
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if is_vercel:
    DB_PATH = "/tmp/ard_master_truth.db" if os.path.exists("/tmp/ard_master_truth.db") else DB_PATH

OUT_DIR = "/tmp" if is_vercel else os.path.join(BASE_DIR, "backups")
os.makedirs(OUT_DIR, exist_ok=True)


# --- DATASET SCHEMA DEFINITIONS ---

DATASET_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "cadre_posts": {
        "id": "cadre_posts",
        "label": "Sanctioned Cadre Posts (1,794)",
        "table": "cadre_1794_posts",
        "description": "Reconstituted cadre posts statewide under Notification 1809 dt. 18.06.2025.",
        "columns": [
            {"key": "post_sl", "label": "Sl No", "width": 8, "align": "center", "is_default": True},
            {"key": "district", "label": "District", "width": 16, "align": "left", "is_default": True},
            {"key": "block", "label": "Block / Subdivision", "width": 20, "align": "left", "is_default": True},
            {"key": "establishment", "label": "Establishment / Office", "width": 32, "align": "left", "is_default": True},
            {"key": "estab_type", "label": "Office Tier", "width": 16, "align": "left", "is_default": False},
            {"key": "designation", "label": "Designation", "width": 26, "align": "left", "is_default": True},
            {"key": "pay_level", "label": "Pay Level", "width": 12, "align": "center", "is_default": True},
            {"key": "occupancy_status", "label": "Occupancy", "width": 14, "align": "center", "is_default": True},
            {"key": "incumbent_name", "label": "Incumbent Name", "width": 26, "align": "left", "is_default": True},
            {"key": "incumbent_hrms", "label": "HRMS ID", "width": 14, "align": "center", "is_default": True},
            {"key": "incumbent_tenure", "label": "Tenure (Yrs)", "width": 14, "align": "right", "is_default": True},
            {"key": "tenure_norm", "label": "Norm (Yrs)", "width": 12, "align": "center", "is_default": False},
            {"key": "tenure_over_flag", "label": "Tenure Status", "width": 16, "align": "center", "is_default": True},
            {"key": "incumbent_dor", "label": "Retirement (DOR)", "width": 16, "align": "center", "is_default": True},
            {"key": "service_utilized_flag", "label": "SU Deployed", "width": 14, "align": "center", "is_default": False},
            {"key": "qualification", "label": "Specialization", "width": 20, "align": "left", "is_default": False}
        ],
        "default_sort": "post_sl",
        "default_order": "asc"
    },
    "employees": {
        "id": "employees",
        "label": "Master Cadre Personnel (1,624)",
        "table": "master_all_cadre_employees",
        "description": "Complete departmental personnel directory with service dates, postings, and credentials.",
        "columns": [
            {"key": "hrms_id", "label": "HRMS ID", "width": 14, "align": "center", "is_default": True},
            {"key": "officer_name", "label": "Officer Name", "width": 26, "align": "left", "is_default": True},
            {"key": "designation", "label": "Designation", "width": 24, "align": "left", "is_default": True},
            {"key": "establishment", "label": "Station / Office", "width": 30, "align": "left", "is_default": True},
            {"key": "district", "label": "District", "width": 16, "align": "left", "is_default": True},
            {"key": "cadre", "label": "Cadre Service", "width": 14, "align": "center", "is_default": False},
            {"key": "service_status", "label": "Service Status", "width": 16, "align": "center", "is_default": True},
            {"key": "dob", "label": "Date of Birth", "width": 14, "align": "center", "is_default": False},
            {"key": "dor", "label": "Date of Retirement", "width": 16, "align": "center", "is_default": True},
            {"key": "years_to_dor", "label": "Years to DOR", "width": 14, "align": "right", "is_default": True},
            {"key": "is_hq_deployed", "label": "HQ Deployment", "width": 16, "align": "center", "is_default": True},
            {"key": "is_50pt_candidate", "label": "Roster Candidate", "width": 16, "align": "center", "is_default": True},
            {"key": "mobile", "label": "Mobile Contact", "width": 16, "align": "center", "is_default": False},
            {"key": "wbvc_reg_no", "label": "WBVC Reg No", "width": 16, "align": "center", "is_default": False}
        ],
        "default_sort": "officer_name",
        "default_order": "asc"
    },
    "roster": {
        "id": "roster",
        "label": "50-Point Roster DD Promotion Panel (242)",
        "table": "roster_50_point_candidates",
        "description": "Statutory promotion panel to Deputy Director under 50-point roster reservation.",
        "columns": [
            {"key": "sl_no", "label": "Merit Sl", "width": 10, "align": "center", "is_default": True},
            {"key": "roster_point", "label": "Roster Pt", "width": 10, "align": "center", "is_default": True},
            {"key": "point_reserved_for", "label": "Quota", "width": 10, "align": "center", "is_default": True},
            {"key": "officer_name", "label": "Officer Name", "width": 26, "align": "left", "is_default": True},
            {"key": "hrms_id", "label": "HRMS ID", "width": 14, "align": "center", "is_default": True},
            {"key": "caste", "label": "Category", "width": 12, "align": "center", "is_default": True},
            {"key": "present_posting", "label": "Present Posting", "width": 30, "align": "left", "is_default": True},
            {"key": "present_district", "label": "District", "width": 16, "align": "left", "is_default": True},
            {"key": "dor", "label": "Retirement Date", "width": 16, "align": "center", "is_default": True},
            {"key": "allotment_status", "label": "Allotment Status", "width": 16, "align": "center", "is_default": True},
            {"key": "substantive_post_name", "label": "Substantive Allotted Post", "width": 32, "align": "left", "is_default": True},
            {"key": "su_post_name", "label": "SU Allotted Post", "width": 28, "align": "left", "is_default": True},
            {"key": "pref_1", "label": "Preference 1", "width": 20, "align": "left", "is_default": False},
            {"key": "pref_2", "label": "Preference 2", "width": 20, "align": "left", "is_default": False},
            {"key": "pref_3", "label": "Preference 3", "width": 20, "align": "left", "is_default": False}
        ],
        "default_sort": "sl_no",
        "default_order": "asc"
    },
    "obliterated": {
        "id": "obliterated",
        "label": "Obliterated Posts & Rehabilitation (76)",
        "table": "obliterated_posts_1808",
        "description": "Abolished block-level setup posts under Notification 1808 and rehabilitation tracking.",
        "columns": [
            {"key": "oblit_sl", "label": "Sl No", "width": 8, "align": "center", "is_default": True},
            {"key": "district", "label": "District", "width": 16, "align": "left", "is_default": True},
            {"key": "block", "label": "Block", "width": 18, "align": "left", "is_default": True},
            {"key": "establishment", "label": "Establishment", "width": 30, "align": "left", "is_default": True},
            {"key": "post_name", "label": "Abolished Post Title", "width": 26, "align": "left", "is_default": True},
            {"key": "officer_name", "label": "Serving Officer", "width": 26, "align": "left", "is_default": True},
            {"key": "hrms_id", "label": "HRMS ID", "width": 14, "align": "center", "is_default": True},
            {"key": "tenure", "label": "Tenure (Yrs)", "width": 14, "align": "right", "is_default": True},
            {"key": "rehabilitation_status", "label": "Rehab Status", "width": 16, "align": "center", "is_default": True},
            {"key": "substantive_post_name", "label": "Rehabilitation Post", "width": 30, "align": "left", "is_default": True},
            {"key": "su_post_name", "label": "Rehabilitation SU Unit", "width": 26, "align": "left", "is_default": True}
        ],
        "default_sort": "oblit_sl",
        "default_order": "asc"
    },
    "posts_with_employees": {
        "id": "posts_with_employees",
        "label": "Unified Cadre Census (Posts + Officers + Dossier)",
        "table": "cadre_1794_posts",
        "description": "Comprehensive statewide cross-match of sanctioned posts, incumbents, and dossier attributes.",
        "columns": [
            {"key": "post_sl", "label": "Post Sl", "width": 8, "align": "center", "is_default": True},
            {"key": "district", "label": "District", "width": 16, "align": "left", "is_default": True},
            {"key": "block", "label": "Block", "width": 18, "align": "left", "is_default": True},
            {"key": "establishment", "label": "Establishment", "width": 30, "align": "left", "is_default": True},
            {"key": "designation", "label": "Post Designation", "width": 26, "align": "left", "is_default": True},
            {"key": "pay_level", "label": "Pay Level", "width": 12, "align": "center", "is_default": True},
            {"key": "occupancy_status", "label": "Occupancy", "width": 14, "align": "center", "is_default": True},
            {"key": "incumbent_name", "label": "Incumbent Name", "width": 26, "align": "left", "is_default": True},
            {"key": "incumbent_hrms", "label": "HRMS ID", "width": 14, "align": "center", "is_default": True},
            {"key": "incumbent_tenure", "label": "Tenure (Yrs)", "width": 14, "align": "right", "is_default": True},
            {"key": "tenure_over_flag", "label": "Tenure Status", "width": 16, "align": "center", "is_default": True},
            {"key": "incumbent_dor", "label": "Retirement Date", "width": 16, "align": "center", "is_default": True},
            {"key": "caste", "label": "Caste", "width": 12, "align": "center", "is_default": False},
            {"key": "home_district", "label": "Native District", "width": 16, "align": "left", "is_default": False},
            {"key": "spouse_service_details", "label": "Spouse Details", "width": 24, "align": "left", "is_default": False},
            {"key": "children_board_exams", "label": "Board Exam Safeguard", "width": 20, "align": "left", "is_default": False}
        ],
        "default_sort": "post_sl",
        "default_order": "asc"
    }
}


class DepartmentDataExporter:
    """
    Core engine for querying, filtering, sorting, and exporting departmental data
    to styled Excel (.xlsx) and Word (.docx) formats.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- METADATA & SCHEMA DISCOVERY ---

    def get_export_metadata(self) -> Dict[str, Any]:
        """Returns datasets, column definitions, and dynamic filter option lists."""
        conn = self.get_connection()
        cur = conn.cursor()

        # Extract distinct districts
        cur.execute("SELECT DISTINCT district FROM cadre_1794_posts WHERE district IS NOT NULL AND district != '' ORDER BY district ASC")
        districts = [r["district"] for r in cur.fetchall()]

        # Extract distinct designations
        cur.execute("SELECT DISTINCT designation FROM cadre_1794_posts WHERE designation IS NOT NULL AND designation != '' ORDER BY designation ASC")
        designations = [r["designation"] for r in cur.fetchall()]

        # Extract distinct pay levels
        cur.execute("SELECT DISTINCT pay_level FROM cadre_1794_posts WHERE pay_level IS NOT NULL AND pay_level != '' ORDER BY pay_level ASC")
        pay_levels = [r["pay_level"] for r in cur.fetchall()]

        # Extract distinct office tiers
        cur.execute("SELECT DISTINCT estab_type FROM cadre_1794_posts WHERE estab_type IS NOT NULL AND estab_type != '' ORDER BY estab_type ASC")
        estab_types = [r["estab_type"] for r in cur.fetchall()]

        conn.close()

        return {
            "datasets": DATASET_SCHEMAS,
            "filters": {
                "districts": districts,
                "designations": designations,
                "pay_levels": pay_levels,
                "estab_types": estab_types,
                "occupancies": ["All", "Clear Vacancies Only", "Occupied Only"],
                "tenures": ["All", "Over-Tenure (>Norm Memo 291)", "Normal Tenure"],
                "superannuations": ["All", "Retiring in ≤ 1 Year", "Retiring in ≤ 2 Years", "Retiring in ≤ 3 Years"],
                "roster_quotas": ["All", "UR", "SC", "ST", "OBC-A", "OBC-B"],
                "allotment_statuses": ["All", "Allotted", "Pending Allotment"]
            },
            "presets": [
                {
                    "id": "clear_vacancies",
                    "label": "Statewide Clear Cadre Vacancies",
                    "dataset": "cadre_posts",
                    "params": {"occupancy_status": "Vacant"},
                    "badge": "GREEN",
                    "count_hint": "747 Posts"
                },
                {
                    "id": "over_tenure",
                    "label": "Over-Tenure Officers (>4/5 Yrs)",
                    "dataset": "cadre_posts",
                    "params": {"occupancy_status": "Occupied", "tenure_filter": "over_tenure"},
                    "badge": "RED",
                    "count_hint": "321 Officers"
                },
                {
                    "id": "superannuation_2yrs",
                    "label": "Superannuation Protection (≤ 2 Yrs)",
                    "dataset": "employees",
                    "params": {"superannuation_filter": "within_2_yrs"},
                    "badge": "GREEN",
                    "count_hint": "Protection Norm"
                },
                {
                    "id": "roster_dd_master",
                    "label": "50-Point Roster Promotion Master",
                    "dataset": "roster",
                    "params": {},
                    "badge": "BLUE",
                    "count_hint": "242 Candidates"
                },
                {
                    "id": "obliterated_rehab",
                    "label": "Obliterated Posts (1808) Status",
                    "dataset": "obliterated",
                    "params": {},
                    "badge": "YELLOW",
                    "count_hint": "76 Posts"
                },
                {
                    "id": "hq_deployments",
                    "label": "Directorate HQ Physical Deployments",
                    "dataset": "employees",
                    "params": {"hq_deployed": True},
                    "badge": "GREY",
                    "count_hint": "37 Officers"
                }
            ]
        }

    # --- QUERY BUILDER ---

    def build_dataset_query(self, dataset: str, filters: Dict[str, Any], sort_by: Optional[str] = None, sort_order: str = "asc") -> Tuple[str, List[Any], List[str]]:
        """
        Dynamically builds SQL statement, parameters, and active filter descriptions.
        """
        if dataset not in DATASET_SCHEMAS:
            dataset = "cadre_posts"

        where_clauses = []
        params = []
        filter_descriptions = []

        schema = DATASET_SCHEMAS[dataset]
        table = schema["table"]

        # 1. Base query selection
        if dataset == "cadre_posts":
            sql = "SELECT * FROM cadre_1794_posts"
        elif dataset == "employees":
            sql = "SELECT * FROM master_all_cadre_employees"
        elif dataset == "roster":
            sql = "SELECT * FROM roster_50_point_candidates"
        elif dataset == "obliterated":
            sql = "SELECT * FROM obliterated_posts_1808"
        elif dataset == "posts_with_employees":
            sql = """
            SELECT 
                p.id, p.post_sl, p.district, p.block, p.establishment, p.estab_type,
                p.designation, p.pay_level, p.occupancy_status, p.incumbent_name,
                p.incumbent_hrms, p.incumbent_tenure, p.tenure_norm, p.tenure_over_flag,
                p.incumbent_dor, e.caste, d.home_district, d.spouse_service_details,
                d.children_board_exams
            FROM cadre_1794_posts p
            LEFT JOIN master_all_cadre_employees e ON p.incumbent_hrms = e.hrms_id
            LEFT JOIN officer_extended_dossier d ON p.incumbent_hrms = d.hrms_id
            """

        # 2. Apply Filters

        # District filter
        district = filters.get("district")
        if district and district not in ["ALL", "All", ""]:
            dist_col = "p.district" if dataset == "posts_with_employees" else "district"
            where_clauses.append(f"{dist_col} = ?")
            params.append(district)
            filter_descriptions.append(f"District: {district}")

        # Designation filter
        designation = filters.get("designation")
        if designation and designation not in ["ALL", "All", ""]:
            desig_col = "p.designation" if dataset == "posts_with_employees" else "designation"
            where_clauses.append(f"{desig_col} = ?")
            params.append(designation)
            filter_descriptions.append(f"Designation: {designation}")

        # Occupancy Status (cadre_posts & posts_with_employees)
        occupancy = filters.get("occupancy_status")
        if occupancy in ["Vacant", "Clear Vacancies Only"]:
            occ_col = "p.occupancy_status" if dataset == "posts_with_employees" else "occupancy_status"
            where_clauses.append(f"{occ_col} = 'Vacant'")
            filter_descriptions.append("Occupancy: Clear Vacancies Only")
        elif occupancy in ["Occupied", "Occupied Only"]:
            occ_col = "p.occupancy_status" if dataset == "posts_with_employees" else "occupancy_status"
            where_clauses.append(f"{occ_col} = 'Occupied'")
            filter_descriptions.append("Occupancy: Occupied Only")

        # Tenure Filter (cadre_posts & posts_with_employees)
        tenure_flt = filters.get("tenure_filter")
        if tenure_flt in ["over_tenure", "Over-Tenure (>Norm Memo 291)"]:
            tenure_col = "p.tenure_over_flag" if dataset == "posts_with_employees" else "tenure_over_flag"
            where_clauses.append(f"({tenure_col} = 'Yes' OR {tenure_col} = 1)")
            filter_descriptions.append("Tenure: Exceeding Memo 291 Norm")
        elif tenure_flt in ["normal", "Normal Tenure"]:
            tenure_col = "p.tenure_over_flag" if dataset == "posts_with_employees" else "tenure_over_flag"
            where_clauses.append(f"({tenure_col} = 'No' OR {tenure_col} = 0 OR {tenure_col} IS NULL)")
            filter_descriptions.append("Tenure: Within Normal Norm")

        # Superannuation Filter (employees & posts_with_employees)
        super_flt = filters.get("superannuation_filter")
        if super_flt and super_flt not in ["All", "ALL", ""]:
            today = datetime.date.today()
            if super_flt in ["within_1_yr", "Retiring in ≤ 1 Year"]:
                max_date = today + datetime.timedelta(days=365)
                filter_descriptions.append("Superannuation: Within 1 Year")
            elif super_flt in ["within_2_yrs", "Retiring in ≤ 2 Years"]:
                max_date = today + datetime.timedelta(days=730)
                filter_descriptions.append("Superannuation: Within 2 Years (Memo 291 Protected)")
            elif super_flt in ["within_3_yrs", "Retiring in ≤ 3 Years"]:
                max_date = today + datetime.timedelta(days=1095)
                filter_descriptions.append("Superannuation: Within 3 Years")
            else:
                max_date = None

            if max_date:
                dor_col = "p.incumbent_dor" if dataset == "posts_with_employees" else ("dor" if dataset in ["employees", "roster"] else "incumbent_dor")
                where_clauses.append(f"{dor_col} IS NOT NULL AND {dor_col} != '' AND {dor_col} <= ? AND {dor_col} >= ?")
                params.extend([max_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")])

        # Roster Quota Filter (roster)
        quota = filters.get("roster_quota") or filters.get("quota")
        if quota and quota not in ["All", "ALL", ""]:
            where_clauses.append("point_reserved_for = ?")
            params.append(quota)
            filter_descriptions.append(f"Roster Quota: {quota}")

        # Allotment Status (roster & obliterated)
        allot_status = filters.get("allotment_status")
        if allot_status and allot_status not in ["All", "ALL", ""]:
            status_col = "rehabilitation_status" if dataset == "obliterated" else "allotment_status"
            if allot_status in ["Allotted", "Finalized"]:
                where_clauses.append(f"{status_col} = 'Allotted'")
                filter_descriptions.append("Status: Allotted")
            elif allot_status in ["Pending", "Pending Allotment"]:
                where_clauses.append(f"({status_col} IS NULL OR {status_col} != 'Allotted')")
                filter_descriptions.append("Status: Pending Allotment")

        # HQ Deployed (employees)
        if filters.get("hq_deployed") is True:
            where_clauses.append("is_hq_deployed = 1")
            filter_descriptions.append("Physical HQ Deployed: Yes")

        # Free text search
        q = filters.get("search_query")
        if q and str(q).strip():
            term = f"%{str(q).strip()}%"
            if dataset == "cadre_posts":
                where_clauses.append("(designation LIKE ? OR establishment LIKE ? OR district LIKE ? OR incumbent_name LIKE ? OR incumbent_hrms LIKE ?)")
                params.extend([term, term, term, term, term])
            elif dataset == "employees":
                where_clauses.append("(officer_name LIKE ? OR hrms_id LIKE ? OR designation LIKE ? OR establishment LIKE ? OR district LIKE ?)")
                params.extend([term, term, term, term, term])
            elif dataset == "roster":
                where_clauses.append("(officer_name LIKE ? OR hrms_id LIKE ? OR present_posting LIKE ? OR substantive_post_name LIKE ?)")
                params.extend([term, term, term, term])
            elif dataset == "obliterated":
                where_clauses.append("(officer_name LIKE ? OR hrms_id LIKE ? OR post_name LIKE ? OR establishment LIKE ?)")
                params.extend([term, term, term, term])
            elif dataset == "posts_with_employees":
                where_clauses.append("(p.designation LIKE ? OR p.establishment LIKE ? OR p.incumbent_name LIKE ? OR p.incumbent_hrms LIKE ?)")
                params.extend([term, term, term, term])
            filter_descriptions.append(f"Keyword: '{str(q).strip()}'")

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        # 3. Apply Sorting
        valid_cols = [c["key"] for c in schema["columns"]]
        if not sort_by or sort_by not in valid_cols:
            sort_by = schema.get("default_sort", valid_cols[0])
        
        sort_dir = "DESC" if str(sort_order).lower() == "desc" else "ASC"
        
        # Map sort_by if joined table
        if dataset == "posts_with_employees" and sort_by in ["post_sl", "district", "designation", "pay_level", "occupancy_status", "incumbent_tenure"]:
            sort_col_sql = f"p.{sort_by}"
        else:
            sort_col_sql = sort_by

        sql += f" ORDER BY {sort_col_sql} {sort_dir}"

        if not filter_descriptions:
            filter_descriptions = ["All Records (No filters applied)"]

        return sql, params, filter_descriptions

    def fetch_records(self, dataset: str, filters: Dict[str, Any], sort_by: Optional[str] = None, sort_order: str = "asc", limit: Optional[int] = None) -> Tuple[List[Dict[str, Any]], int, List[str]]:
        """
        Executes query and returns (records, total_count, filter_descriptions).
        """
        conn = self.get_connection()
        cur = conn.cursor()

        sql, params, descriptions = self.build_dataset_query(dataset, filters, sort_by, sort_order)

        # Fetch total count
        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        cur.execute(count_sql, params)
        total_count = cur.fetchone()[0]

        # Apply limit if requested (e.g. for preview)
        if limit and limit > 0:
            sql += f" LIMIT {limit}"

        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        # Format rows: calculate years to DOR, clean values
        today = datetime.date.today()
        for r in rows:
            dor_val = r.get("dor") or r.get("incumbent_dor")
            if dor_val and len(str(dor_val)) >= 4:
                try:
                    parts = str(dor_val)[:10].split("-")
                    if len(parts) == 3 and len(parts[0]) == 4:
                        dor_dt = datetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                        diff = max(0.0, (dor_dt - today).days / 365.25)
                        r["years_to_dor"] = f"{diff:.1f} yrs"
                except Exception:
                    r["years_to_dor"] = "—"
            
            if "incumbent_tenure" in r and r["incumbent_tenure"] is not None:
                try:
                    r["incumbent_tenure"] = f"{float(str(r['incumbent_tenure']).strip()):.1f}"
                except Exception:
                    pass
            if "tenure" in r and r["tenure"] is not None:
                try:
                    r["tenure"] = f"{float(str(r['tenure']).strip()):.1f}"
                except Exception:
                    pass

            tof_str = str(r.get("tenure_over_flag") or "").strip().lower()
            if tof_str in ["yes", "1", "true", "over-tenure"]:
                r["tenure_over_flag"] = "OVER-TENURE (>Norm)"
            elif tof_str in ["no", "0", "false", "normal"]:
                r["tenure_over_flag"] = "Normal"

        return rows, total_count, descriptions

    # --- EXCEL EXPORT GENERATOR ---

    def generate_excel_report(self, dataset: str, filters: Dict[str, Any], sort_by: Optional[str] = None, sort_order: str = "asc", selected_columns: Optional[List[str]] = None) -> str:
        """
        Generates professionally styled Excel (.xlsx) file with government headers,
        status highlights, auto column widths, and metadata.
        """
        if dataset not in DATASET_SCHEMAS:
            dataset = "cadre_posts"

        schema = DATASET_SCHEMAS[dataset]
        all_cols = schema["columns"]

        if selected_columns and len(selected_columns) > 0:
            active_cols = [c for c in all_cols if c["key"] in selected_columns]
            if not active_cols:
                active_cols = [c for c in all_cols if c["is_default"]]
        else:
            active_cols = [c for c in all_cols if c["is_default"]]

        records, total_count, filter_descs = self.fetch_records(dataset, filters, sort_by, sort_order)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = schema["label"][:30].replace("/", "-")
        ws.views.sheetView[0].showGridLines = True

        navy_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        light_gray_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        soft_green_fill = PatternFill(start_color="E6F4EA", end_color="E6F4EA", fill_type="solid")
        soft_red_fill = PatternFill(start_color="FCE8E6", end_color="FCE8E6", fill_type="solid")
        soft_yellow_fill = PatternFill(start_color="FEF7E0", end_color="FEF7E0", fill_type="solid")
        soft_blue_fill = PatternFill(start_color="E8F0FE", end_color="E8F0FE", fill_type="solid")

        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        title_font = Font(name="Arial", size=14, bold=True, color="0F172A")
        dept_font = Font(name="Arial", size=11, bold=True, color="3C4043")
        meta_font = Font(name="Arial", size=9, italic=True, color="5F6368")
        data_font = Font(name="Arial", size=9, color="202124")
        bold_font = Font(name="Arial", size=9, bold=True, color="202124")

        thin_side = Side(border_style="thin", color="DADCE0")
        cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

        num_cols = len(active_cols)
        end_col_letter = get_column_letter(max(1, num_cols))

        # 1. Government Title Header Block
        ws.merge_cells(f"A1:{end_col_letter}1")
        ws["A1"] = "GOVERNMENT OF WEST BENGAL"
        ws["A1"].font = dept_font
        ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

        ws.merge_cells(f"A2:{end_col_letter}2")
        ws["A2"] = "DEPARTMENT OF ANIMAL RESOURCES DEVELOPMENT"
        ws["A2"].font = title_font
        ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

        ws.merge_cells(f"A3:{end_col_letter}3")
        ws["A3"] = f"Executive Cadre Report: {schema['label']} (Generated: {datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')})"
        ws["A3"].font = dept_font
        ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

        ws.merge_cells(f"A4:{end_col_letter}4")
        filter_str = " | ".join(filter_descs)
        ws["A4"] = f"Filter Scope: {filter_str} | Total Records: {total_count}"
        ws["A4"].font = meta_font
        ws["A4"].alignment = Alignment(horizontal="center", vertical="center")

        ws.row_dimensions[1].height = 20
        ws.row_dimensions[2].height = 25
        ws.row_dimensions[3].height = 20
        ws.row_dimensions[4].height = 18
        ws.row_dimensions[5].height = 10

        # 2. Table Header Row (Row 6)
        row_num = 6
        ws.row_dimensions[row_num].height = 28
        for c_idx, col in enumerate(active_cols, 1):
            cell = ws.cell(row=row_num, column=c_idx, value=col["label"])
            cell.fill = navy_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = cell_border

        # 3. Data Rows
        row_num = 7
        for r_idx, rec in enumerate(records):
            ws.row_dimensions[row_num].height = 20
            is_even = (r_idx % 2 == 0)

            for c_idx, col in enumerate(active_cols, 1):
                val = rec.get(col["key"])
                if val is None:
                    val = "—"
                cell = ws.cell(row=row_num, column=c_idx, value=val)
                cell.font = data_font
                cell.border = cell_border

                align_h = col.get("align", "left")
                cell.alignment = Alignment(horizontal=align_h, vertical="center")
                cell.fill = PatternFill(fill_type=None) if is_even else light_gray_fill

                # Status Highlights
                str_val = str(val).upper()
                if str_val in ["VACANT", "ALLOTTED", "COMPLIANT"]:
                    cell.fill = soft_green_fill
                    cell.font = bold_font
                elif "OVER-TENURE" in str_val or str_val in ["OCCUPIED", "BLOCKED", "COLLISION_RISK"]:
                    cell.fill = soft_red_fill
                    cell.font = bold_font
                elif "PENDING" in str_val or str_val in ["CAUTION", "ADVISORY"]:
                    cell.fill = soft_yellow_fill
                    cell.font = bold_font

            row_num += 1

        # 4. Summary / Footer Row
        ws.row_dimensions[row_num].height = 24
        ws.merge_cells(f"A{row_num}:B{row_num}")
        sum_cell = ws.cell(row=row_num, column=1, value=f"Total Records: {total_count}")
        sum_cell.font = bold_font
        sum_cell.alignment = Alignment(horizontal="left", vertical="center")
        sum_cell.fill = light_gray_fill

        for c_idx in range(1, num_cols + 1):
            ws.cell(row=row_num, column=c_idx).border = cell_border
            ws.cell(row=row_num, column=c_idx).fill = light_gray_fill

        # 5. Auto-adjust column widths
        for c_idx, col in enumerate(active_cols, 1):
            col_letter = get_column_letter(c_idx)
            target_width = col.get("width", 15)
            ws.column_dimensions[col_letter].width = max(target_width, 10)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"WB_ARD_{dataset}_{timestamp_str}.xlsx"
        filepath = os.path.join(OUT_DIR, filename)
        wb.save(filepath)
        return filepath

    # --- WORD (.DOCX) EXPORT GENERATOR ---

    def generate_docx_report(self, dataset: str, filters: Dict[str, Any], sort_by: Optional[str] = None, sort_order: str = "asc", selected_columns: Optional[List[str]] = None) -> str:
        """
        Generates authentic official West Bengal Government Document (.docx)
        with letterhead, repeat header rows, executive metadata, and clean formatting.
        """
        if dataset not in DATASET_SCHEMAS:
            dataset = "cadre_posts"

        schema = DATASET_SCHEMAS[dataset]
        all_cols = schema["columns"]

        if selected_columns and len(selected_columns) > 0:
            active_cols = [c for c in all_cols if c["key"] in selected_columns]
            if not active_cols:
                active_cols = [c for c in all_cols if c["is_default"]]
        else:
            active_cols = [c for c in all_cols if c["is_default"]][:8]

        records, total_count, filter_descs = self.fetch_records(dataset, filters, sort_by, sort_order)

        doc = docx.Document()

        # Page Setup: Landscape for wide tables
        section = doc.sections[0]
        section.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
        section.page_width = Inches(11.69)
        section.page_height = Inches(8.27)
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

        # 1. Government Letterhead
        p1 = doc.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run("GOVERNMENT OF WEST BENGAL")
        r1.bold = True
        r1.font.size = Pt(13)
        r1.font.name = "Arial"
        r1.font.color.rgb = RGBColor(28, 28, 30)

        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_after = Pt(2)
        r2 = p2.add_run("ANIMAL RESOURCES DEVELOPMENT DEPARTMENT")
        r2.bold = True
        r2.font.size = Pt(11)
        r2.font.name = "Arial"
        r2.font.color.rgb = RGBColor(60, 64, 67)

        p3 = doc.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p3.paragraph_format.space_after = Pt(6)
        r3 = p3.add_run("DIRECTORATE OF ANIMAL HEALTH & VETERINARY SERVICES\nLB-2, Sector-III, Salt Lake City, Kolkata - 700 106")
        r3.font.size = Pt(9)
        r3.font.name = "Arial"
        r3.font.color.rgb = RGBColor(95, 99, 104)

        # Title
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_title.paragraph_format.space_after = Pt(4)
        r_title = p_title.add_run(f"EXECUTIVE CADRE REPORT: {schema['label'].upper()}")
        r_title.bold = True
        r_title.font.size = Pt(11)
        r_title.font.name = "Arial"

        # Metadata Box
        p_meta = doc.add_paragraph()
        p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_meta.paragraph_format.space_after = Pt(10)
        filter_str = " | ".join(filter_descs)
        r_meta = p_meta.add_run(f"Filter Criteria: {filter_str}  •  Total Records: {total_count}  •  Generated: {datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p')}")
        r_meta.italic = True
        r_meta.font.size = Pt(8.5)
        r_meta.font.color.rgb = RGBColor(95, 99, 104)

        # 2. Main Data Table
        num_cols = len(active_cols)
        table = doc.add_table(rows=1, cols=num_cols)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True

        # Header Row
        hdr_row = table.rows[0]
        trPr = hdr_row._tr.get_or_add_trPr()
        trPr.append(parse_xml(r'<w:tblHeader %s/>' % nsdecls('w')))

        for c_idx, col in enumerate(active_cols):
            cell = hdr_row.cells[c_idx]
            cell.text = col["label"]
            shading = parse_xml(r'<w:shd %s w:fill="1E293B"/>' % nsdecls('w'))
            cell._tc.get_or_add_tcPr().append(shading)

            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(8.5)
                run.font.name = "Arial"
                run.font.color.rgb = RGBColor(255, 255, 255)

        # Data Rows
        for r_idx, rec in enumerate(records):
            row = table.add_row()
            trPr = row._tr.get_or_add_trPr()
            trPr.append(parse_xml(r'<w:cantSplit %s/>' % nsdecls('w')))

            is_even = (r_idx % 2 == 0)

            for c_idx, col in enumerate(active_cols):
                cell = row.cells[c_idx]
                val = rec.get(col["key"])
                if val is None:
                    val = "—"
                cell.text = str(val)

                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after = Pt(3)

                align_h = col.get("align", "left")
                if align_h == "center":
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif align_h == "right":
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                for run in p.runs:
                    run.font.size = Pt(8)
                    run.font.name = "Arial"
                    run.font.color.rgb = RGBColor(32, 33, 36)

                if not is_even:
                    shading = parse_xml(r'<w:shd %s w:fill="F8FAFC"/>' % nsdecls('w'))
                    cell._tc.get_or_add_tcPr().append(shading)

        # Set subtle table border
        tblPr = table._tbl.tblPr
        borders = parse_xml(
            r'<w:tblBorders %s>'
            r'  <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
            r'  <w:left w:val="none"/>'
            r'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="1E293B"/>'
            r'  <w:right w:val="none"/>'
            r'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>'
            r'  <w:insideV w:val="none"/>'
            r'</w:tblBorders>' % nsdecls('w')
        )
        tblPr.append(borders)

        # 3. Departmental Notice
        doc.add_paragraph().paragraph_format.space_after = Pt(12)
        p_notice = doc.add_paragraph()
        r_notice = p_notice.add_run(
            "Note: This document is an authenticated administrative extract produced by the Smart Posting Decision Board "
            "for executive deployment and cadre evaluation in accordance with Notification Nos. 1808 & 1809 and Transfer Policy Memo 291 of 2009."
        )
        r_notice.italic = True
        r_notice.font.size = Pt(7.5)
        r_notice.font.color.rgb = RGBColor(128, 134, 139)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"WB_ARD_{dataset}_{timestamp_str}.docx"
        filepath = os.path.join(OUT_DIR, filename)
        doc.save(filepath)
        return filepath


# Singleton instance
data_exporter = DepartmentDataExporter()
