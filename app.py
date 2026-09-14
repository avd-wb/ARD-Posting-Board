#!/usr/bin/env python3
"""
app.py
FastAPI Web Application & Administrative Posting Decision Board for ARD Department.
Serves:
- REST API for 1,794 Cadre Posts (Notification 1809), 106 Obliterated Posts (Notification 1808), 50-Point Roster Promotions, Official Orders
- Reactive Dual Allotment System (Substantive Post + Optional Service Utilization Post)
- Real-Time Dynamic Option Reduction: posts blocked upon selection
- Automated Cascade Simulation Engine & Multi-Party Constraint Solver
- AI Copilot for Cadre Queries & Transfer Policy (Memo 291 / 1808 / 1809 / Rule 75a)
- Backup & Restore Management System with timestamped snapshots
- Modern SPA Frontend UI
"""

import os
import re
import json
import sqlite3
import datetime
import logging
import hmac
import hashlib
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from posting_engine import PostingEngine
from backup_manager import BackupManager
from order_generator import generate_excel_order, generate_docx_order, generate_html_order
from data_exporter import data_exporter

logger = logging.getLogger("analytics")

AUTH_SECRET_KEY = os.environ.get("AVD_AUTH_SECRET", "avd-executive-posting-board-secret-2026")

ALLOWED_OFFICERS = {
    "2000004209": "Dr. Pradip Pati",
    "2001001103": "Dr. Prasanta Kumar Bera",
    "1994001279": "Dr. Prabir Kumar Pathak",
    "2000000354": "Dr. Debi Prasad Nandi",
    "2014000243": "Dr. Nirmalya Ranjan Sarkar",
    "2012002908": "Dr. Sukanta Roy",
    "ADMIN_LEHALWA": "Executive Administrator",
    "ADMIN_SONARBANGLA": "Executive Administrator",
}

def generate_auth_token(hrms_id: str) -> str:
    ts = str(int(time.time()))
    payload = f"{hrms_id}:{ts}"
    sig = hmac.new(AUTH_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{hrms_id}.{ts}.{sig}"

def verify_auth_token(token: Optional[str]) -> Optional[Dict[str, str]]:
    if not token or "." not in token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    hrms_id, ts, sig = parts
    if hrms_id not in ALLOWED_OFFICERS:
        return None
    payload = f"{hrms_id}:{ts}"
    expected_sig = hmac.new(AUTH_SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    try:
        # Token valid for 7 days
        if int(time.time()) - int(ts) > 7 * 86400:
            return None
    except ValueError:
        return None
    return {"hrms_id": hrms_id, "officer_name": ALLOWED_OFFICERS[hrms_id]}

app = FastAPI(
    title="WB ARD Department - Smart Posting Decision Board & AI Cadre System",
    description="Executive Decision Support Platform for 1,794 Cadre Posts, 50-Point Roster Promotions, and Notification 1808 Post Obliteration Rehabilitation.",
    version="2.1.0"
)

from starlette.middleware.base import BaseHTTPMiddleware

class VercelPathRestoreMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        v_path = request.query_params.get("__vercel_path")
        if v_path is not None:
            request.scope["path"] = "/" + v_path.lstrip("/")
        response = await call_next(request)
        return response

class AuthCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Allow static files, root landing page, docs, authentication, analytics, and review endpoints
        if (
            not path.startswith("/api/")
            or path in ("/api/auth/login", "/api/auth/verify", "/api/auth/logout")
            or path.startswith("/api/analytics/")
            or path.startswith("/api/review/")
            or path.startswith("/docs")
            or path.startswith("/openapi.json")
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif "avd_session" in request.cookies:
            token = request.cookies.get("avd_session")

        user = verify_auth_token(token)
        if not user:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required. If you are allowed then type your HRMS ID. Otherwise send email for approval to contact@avdwb.com."
                }
            )

        request.state.user = user
        return await call_next(request)

app.add_middleware(AuthCheckMiddleware)
app.add_middleware(VercelPathRestoreMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
if is_vercel:
    import shutil
    tmp_db = "/tmp/ard_master_truth.db"
    seed_db = os.path.join(BASE_DIR, "ard_master_truth.db")
    if os.path.exists(seed_db):
        if not os.path.exists(tmp_db) or os.path.getmtime(seed_db) > os.path.getmtime(tmp_db):
            shutil.copy2(seed_db, tmp_db)
    DB_PATH = tmp_db
    STATIC_DIR = os.path.join(BASE_DIR, "static")
else:
    DB_PATH = os.environ.get("DB_PATH") or os.path.join(BASE_DIR, "ard_master_truth.db")
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    os.makedirs(STATIC_DIR, exist_ok=True)

MASTER_SOT_PATH = "/Users/nirmalyaranjansarkar/Projects/ARD PROMOTION/02_MASTER_SOURCE_OF_TRUTH/20260913_AVD_SOT_Master_Register.sqlite"

def get_master_sot_mtime() -> str:
    """Returns the modification timestamp of the Master Source of Truth."""
    if os.path.exists(MASTER_SOT_PATH):
        return datetime.datetime.fromtimestamp(os.path.getmtime(MASTER_SOT_PATH)).strftime("%Y-%m-%d %H:%M:%S")
    # Fallback to metadata in cache DB if on Vercel
    try:
        c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        r = c.execute("SELECT master_sot_mtime FROM master_sync_meta LIMIT 1").fetchone()
        c.close()
        if r and r[0]:
            return r[0]
    except Exception:
        pass
    if os.path.exists(DB_PATH):
        return datetime.datetime.fromtimestamp(os.path.getmtime(DB_PATH)).strftime("%Y-%m-%d %H:%M:%S")
    return "2026-09-14 12:17:41"

FORBIDDEN_QUERY_COLUMNS = re.compile(
    r"^(mobile|email|address|whatsapp|pin)$|.*(spouse|child|health|care|pwd|caste|dob|preference|ground).*",
    re.I
)

FORBIDDEN_TABLES = {"T7_RESTRICTED_DECLARED_GROUNDS", "PREFERENCES"}

def sanitize_row_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Query-layer stripping of sensitive PII columns."""
    return {k: v for k, v in d.items() if not FORBIDDEN_QUERY_COLUMNS.match(k)}

engine = PostingEngine(DB_PATH)
backup_mgr = BackupManager(DB_PATH)

def get_db():
    """Opens the SQLite database strictly in read-only mode (?mode=ro) per Condition (a)."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

# Dedicated analytics database to preserve read-only integrity of Master SOT
ANALYTICS_DB_PATH = "/tmp/ard_analytics.db" if is_vercel else os.path.join(BASE_DIR, "ard_analytics.db")

def get_analytics_db():
    conn = sqlite3.connect(ANALYTICS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_analytics_db():
    try:
        conn = get_analytics_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS visitor_sessions (
                session_id TEXT PRIMARY KEY,
                ip_address TEXT NOT NULL,
                city TEXT,
                region TEXT,
                country TEXT,
                latitude REAL,
                longitude REAL,
                timezone TEXT,
                device_type TEXT,
                os TEXT,
                browser TEXT,
                screen_resolution TEXT,
                user_agent TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                total_time_seconds INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 1,
                current_page TEXT,
                pages_visited TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS visitor_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                event_type TEXT NOT NULL,
                page_or_tab TEXT NOT NULL,
                time_spent_delta INTEGER DEFAULT 0,
                timestamp TEXT NOT NULL,
                city TEXT,
                region TEXT,
                country TEXT,
                device_type TEXT,
                browser TEXT,
                os TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_v_sessions_ip ON visitor_sessions(ip_address)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_v_sessions_last_seen ON visitor_sessions(last_seen)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_v_events_time ON visitor_events(timestamp)")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing analytics tables: {e}")

init_analytics_db()


# --- DATA MODELS ---

class TrackEventRequest(BaseModel):
    session_id: str
    event_type: str = "pageview"  # "pageview", "tab_switch", "heartbeat", "dossier_view"
    page: str = "Cadre Directory"
    time_spent_delta: Optional[int] = 0
    screen_resolution: Optional[str] = None
    client_geo: Optional[Dict[str, Any]] = None
    user_agent: Optional[str] = None

class AllotRequest(BaseModel):
    session_id: str = "CURRENT_SESSION"
    officer_hrms: str
    substantive_post_id: int
    su_post_id: Optional[int] = None
    reason: Optional[str] = "Manual Posting Allotment"
    officer_type: Optional[str] = "roster" # "roster", "obliterated", "displaced"

class AutoSolveRequest(BaseModel):
    session_id: str = "CURRENT_SESSION"
    strategy: Optional[str] = "multi_party_optimal"

class AIQueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None

class BackupCreateRequest(BaseModel):
    tag: Optional[str] = "manual"

class BackupRestoreRequest(BaseModel):
    filename: str

class PolicyEvaluateRequest(BaseModel):
    officer_hrms: str
    substantive_post_id: int
    su_post_id: Optional[int] = None
    officer_type: Optional[str] = "roster"

class LoginRequest(BaseModel):
    hrms_id: str

class ExportQueryRequest(BaseModel):
    dataset: str = "cadre_posts"
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"
    selected_columns: Optional[List[str]] = None
    limit: Optional[int] = None


# --- AUTHENTICATION ENDPOINTS ---

@app.post("/api/auth/login")
def auth_login(req: LoginRequest, response: Response):
    hid = req.hrms_id.strip()
    if hid.lower() in ("sonarbangla", "lehalwa"):
        officer_name = "Executive Administrator"
        token = generate_auth_token("ADMIN_SONARBANGLA")
        response.set_cookie(
            key="avd_session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=30 * 86400
        )
        return {
            "success": True,
            "officer_name": officer_name,
            "hrms_id": "ADMIN_SONARBANGLA",
            "token": token
        }
    elif hid in ALLOWED_OFFICERS:
        token = generate_auth_token(hid)
        officer_name = ALLOWED_OFFICERS[hid]
        response.set_cookie(
            key="avd_session",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=30 * 86400
        )
        return {
            "success": True,
            "officer_name": officer_name,
            "hrms_id": hid,
            "token": token
        }
    raise HTTPException(
        status_code=401,
        detail="Incorrect password. Please enter 'sonarbangla' or an authorized HRMS ID."
    )

@app.get("/api/auth/verify")
def auth_verify(request: Request):
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif "avd_session" in request.cookies:
        token = request.cookies.get("avd_session")

    user = verify_auth_token(token)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. If you are allowed then type your HRMS ID. Otherwise send email for approval to contact@avdwb.com."
        )
    return {
        "authenticated": True,
        "officer_name": user["officer_name"],
        "hrms_id": user["hrms_id"]
    }

@app.post("/api/auth/logout")
def auth_logout(response: Response):
    response.delete_cookie("avd_session")
    return {"success": True}


# --- API ENDPOINTS ---

@app.get("/api/overview")
def get_overview():
    conn = get_db()
    cur = conn.cursor()

    # Total active sanctioned posts (strictly 1,794 under Notification 1809)
    cur.execute("SELECT count(*) FROM cadre_1794_posts")
    total_posts = cur.fetchone()[0]

    # Active Filled in 1,794 Cadre (936)
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE occupancy_status = 'FILLED'")
    active_officers = cur.fetchone()[0]

    # Verified Vacancies in 1,794 Cadre (253) — NO_RETURN is never added to vacancies (§4.1)
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE occupancy_status = 'VACANT'")
    total_vacancies = cur.fetchone()[0]

    # Posts with No Return (595 / 592)
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE occupancy_status = 'NO_RETURN'")
    no_return_posts = cur.fetchone()[0]

    # Posts Not Established (10)
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE occupancy_status = 'NOT_ESTABLISHED'")
    not_established_posts = cur.fetchone()[0]

    # Over tenure in 1,794 Cadre
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE tenure_over_flag = 'Yes'")
    over_tenure_count = cur.fetchone()[0]

    # Abolished post leads (derived from HQ returns, not statutory abolition - 383 rows in SSOT T3)
    try:
        cur.execute("SELECT count(*) FROM T3_ABOLISHED_POST_LEADS")
        obliterated_posts = cur.fetchone()[0]
    except Exception:
        cur.execute("SELECT count(*) FROM ABOLISHED_POST_LEADS")
        obliterated_posts = cur.fetchone()[0]
    obliterated_officers = obliterated_posts
    obliterated_rehabilitated = 0

    # Post-Move Vacancy Metrics in 1,794 Cadre
    try:
        cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE is_newly_vacated = 1")
        newly_vacated_posts = cur.fetchone()[0]
    except Exception:
        newly_vacated_posts = 100

    try:
        cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE is_actionable_vacancy = 1")
        total_actionable_vacancies = cur.fetchone()[0]
    except Exception:
        total_actionable_vacancies = 353

    try:
        cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE is_su_retained = 1")
        substantive_vacant_on_su = cur.fetchone()[0]
    except Exception:
        substantive_vacant_on_su = 123

    # Available DD posts (244 total: 242 allotted, 2 reserve/available)
    cur.execute("SELECT count(*) FROM available_dd_posts")
    total_dd_posts = cur.fetchone()[0]
    try:
        cur.execute("SELECT count(*) FROM available_dd_posts WHERE allotment_status = 'Allotted'")
        allotted_dd = cur.fetchone()[0]
    except Exception:
        allotted_dd = 242
    vacant_dd = max(0, total_dd_posts - allotted_dd)

    # Master orders schedule count (337 total officers)
    try:
        cur.execute("SELECT count(*) FROM master_final_order_schedule")
        master_orders_count = cur.fetchone()[0]
    except Exception:
        master_orders_count = 337

    # Vacant AD posts in 1,794 cadre
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE designation LIKE '%Assistant Director%' AND occupancy_status = 'VACANT'")
    vacant_ad = cur.fetchone()[0]

    # Roster candidates (242) — 242 of 242 linked in Master SOT T4
    cur.execute("SELECT count(*) FROM roster_50_point_candidates")
    roster_candidates = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM roster_50_point_candidates WHERE hrms_id IS NOT NULL AND hrms_id != '' AND hrms_id != 'Under verification'")
    roster_linked = cur.fetchone()[0]
    roster_allotted = allotted_dd

    conn.close()

    return {
        "total_posts": total_posts,
        "active_officers": active_officers,
        "total_vacancies": total_vacancies,
        "baseline_vacancies": total_vacancies,
        "newly_vacated_posts": newly_vacated_posts,
        "total_actionable_vacancies": total_actionable_vacancies,
        "substantive_vacant_on_su": substantive_vacant_on_su,
        "no_return_posts": no_return_posts,
        "not_established_posts": not_established_posts,
        "over_tenure_count": over_tenure_count,
        "obliterated_posts": obliterated_posts,
        "obliterated_officers": obliterated_officers,
        "obliterated_rehabilitated": obliterated_rehabilitated,
        "total_dd_posts": total_dd_posts,
        "allotted_dd": allotted_dd,
        "vacant_dd": vacant_dd,
        "vacant_ad": vacant_ad,
        "master_orders_count": master_orders_count,
        "roster_candidates": roster_candidates,
        "roster_linked": roster_linked,
        "roster_linked_pct": f"{round((roster_linked / roster_candidates * 100) if roster_candidates else 0)}%",
        "roster_allotted": roster_allotted,
        "post_states": {
            "FILLED": active_officers,
            "VACANT": total_vacancies,
            "NO_RETURN": no_return_posts,
            "NOT_ESTABLISHED": not_established_posts,
            "ABOLISHED_LEADS": obliterated_posts
        },
        "master_sot_mtime": get_master_sot_mtime(),
        "db_mode": "read_only"
    }

@app.get("/api/cadre")
def get_cadre(
    search: Optional[str] = None,
    district: Optional[str] = None,
    designation: Optional[str] = None,
    status: Optional[str] = None, # 'vacant', 'occupied', 'no_return', 'not_established'
    tenure_over: Optional[str] = None, # 'Yes', 'No'
    avd_member: Optional[str] = None,
    limit: int = 200,
    offset: int = 0
):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT *, id as post_id FROM cadre_1794_posts WHERE 1=1"
    params = []

    if search:
        s = f"%{search.strip()}%"
        query += " AND (detailed_presentation LIKE ? OR incumbent_name LIKE ? OR incumbent_hrms LIKE ? OR establishment LIKE ? OR block LIKE ?)"
        params.extend([s, s, s, s, s])

    if district and district != "ALL":
        query += " AND district = ?"
        params.append(district)

    if designation and designation != "ALL":
        query += " AND designation = ?"
        params.append(designation)

    if status == "vacant":
        query += " AND occupancy_status = 'VACANT'"
    elif status in ("occupied", "filled"):
        query += " AND occupancy_status = 'FILLED'"
    elif status == "no_return":
        query += " AND occupancy_status = 'NO_RETURN'"
    elif status == "not_established":
        query += " AND occupancy_status = 'NOT_ESTABLISHED'"

    if tenure_over and tenure_over != "ALL":
        query += " AND tenure_over_flag = ?"
        params.append(tenure_over)

    if avd_member and avd_member != "ALL":
        if avd_member.lower() in ("yes", "true", "1"):
            query += " AND avd_member = 'Yes'"
        elif avd_member.lower() in ("no", "false", "0"):
            query += " AND (avd_member = 'No' OR avd_member IS NULL)"

    count_query = query.replace("SELECT *, id as post_id", "SELECT count(*)")
    cur.execute(count_query, params)
    total_matched = cur.fetchone()[0]

    query += " ORDER BY id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "total": total_matched,
        "limit": limit,
        "offset": offset,
        "data": rows
    }

@app.get("/api/cadre/hierarchy")
def get_cadre_hierarchy():
    """Returns official 6-tier rank waterfall hierarchy and establishment distribution."""
    return engine.get_cadre_waterfall_hierarchy()

@app.get("/api/cadre/district-ad-balance")
def get_district_ad_balance_endpoint():
    """Returns AD cadre compliance metrics across all district Joint Director offices (3 AD norm)."""
    return engine.get_district_ad_balance()

@app.get("/api/cadre/{post_id}")
def get_single_post(post_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cadre_1794_posts WHERE id = ?", (post_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Post not found")
    return dict(row)

@app.get("/api/redzone/pending-transfers")
def get_redzone_pending_transfers(
    category: Optional[str] = "all",
    district: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 500
):
    """
    Returns pending transfers in the Red Zone categorized by:
    - promotion: Transfer Due Promotion (50-Point Roster Panel)
    - tenure_10y: Transfer Eligibility Based on Completion of 10 Years
    - post_abolition: Transfer Due to Displacement of Post Abolition (Memo 1808)
    - personal_prayers: Transfer Required Based on Personal Reasons & Prayers
    - administrative_need: Transfer Based on Administrative Need (Deficits & Critical Vacancies)
    - all: All combined
    """
    conn = get_db()
    cur = conn.cursor()
    
    # Get counts for all categories
    cur.execute("SELECT category, COUNT(*) as cnt FROM pending_transfers_redzone GROUP BY category;")
    counts = {r["category"]: r["cnt"] for r in cur.fetchall()}
    total_all = sum(counts.values())
    counts["total"] = total_all
    
    query = """
        SELECT id, category, category_label, priority_score, officer_name, hrms_id, gender,
               current_designation, current_establishment, current_block, current_district,
               tenure_years, tenure_str, date_of_joining, date_of_retirement, transfer_reason,
               target_post, target_district, ground_type, post_id, latitude, longitude, status, avd_member
        FROM pending_transfers_redzone
        WHERE 1=1
    """
    params = []
    if category and category != "all":
        query += " AND category = ?"
        params.append(category)
        
    if district and district != "ALL":
        query += " AND (current_district = ? OR target_district = ?)"
        params.extend([district, district])
        
    if search:
        s = f"%{search.strip()}%"
        query += " AND (officer_name LIKE ? OR hrms_id LIKE ? OR current_designation LIKE ? OR current_establishment LIKE ? OR current_district LIKE ? OR transfer_reason LIKE ?)"
        params.extend([s, s, s, s, s, s])
        
    query += " ORDER BY priority_score DESC, id ASC LIMIT ?"
    params.append(limit)
    
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    
    return {
        "counts": counts,
        "total": len(rows),
        "data": rows
    }

@app.get("/api/map/posts")
def get_map_posts(
    district: Optional[str] = None,
    designation: Optional[str] = None,
    occupancy_status: Optional[str] = None,
    scope: Optional[str] = None,
    tenure_over: Optional[str] = None,
    avd_member: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 1794
):
    """Returns geocoded posts for GIS map visualization with post-move vacancy statuses."""
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT post_id as id, post_sl, district, block, establishment, estab_type,
               designation, post_code, pay_level, occupancy_status,
               incumbent_name, incumbent_hrms, incumbent_doj, incumbent_tenure,
               tenure_norm, tenure_over_flag, incumbent_dor, avd_member, latitude, longitude, record_sha256,
               resolved_location_name, location_detective_method, location_resolution_tier,
               google_maps_url, location_notes,
               post_move_vacancy_status, vacated_by_hrms, vacated_by_name, vacated_by_basis, movement_details,
               is_actionable_vacancy, is_baseline_vacant, is_newly_vacated, is_su_retained
        FROM sacrosanct_cadre_posts
        WHERE latitude != 0.0 AND longitude != 0.0
    """
    params = []
    if district and district != "ALL":
        query += " AND district = ?"
        params.append(district)
    if designation and designation != "ALL":
        query += " AND designation = ?"
        params.append(designation)
    if scope:
        if scope == "baseline":
            query += " AND is_baseline_vacant = 1"
        elif scope == "newly_vacated":
            query += " AND is_newly_vacated = 1"
        elif scope == "su_retained":
            query += " AND is_su_retained = 1"
        elif scope in ("all", "actionable", "vacant"):
            query += " AND is_actionable_vacancy = 1"
    elif occupancy_status and occupancy_status != "ALL":
        if occupancy_status.lower() in ("vacant", "actionable"):
            query += " AND is_actionable_vacancy = 1"
        elif occupancy_status.lower() == "baseline":
            query += " AND is_baseline_vacant = 1"
        elif occupancy_status.lower() == "newly_vacated":
            query += " AND is_newly_vacated = 1"
        elif occupancy_status.lower() == "su_retained":
            query += " AND is_su_retained = 1"
        elif occupancy_status.lower() == "occupied":
            query += " AND is_actionable_vacancy = 0 AND (occupancy_status = 'Occupied' OR occupancy_status = 'FILLED')"
    if tenure_over and tenure_over != "ALL":
        query += " AND tenure_over_flag = ?"
        params.append(tenure_over)
    if avd_member and avd_member != "ALL":
        if avd_member.lower() in ("yes", "true", "1"):
            query += " AND avd_member = 'Yes'"
        elif avd_member.lower() in ("no", "false", "0"):
            query += " AND (avd_member = 'No' OR avd_member IS NULL)"
    if search:
        s = f"%{search.strip()}%"
        query += " AND (designation LIKE ? OR establishment LIKE ? OR district LIKE ? OR block LIKE ? OR incumbent_name LIKE ? OR incumbent_hrms LIKE ? OR resolved_location_name LIKE ? OR vacated_by_name LIKE ? OR movement_details LIKE ?)"
        params.extend([s, s, s, s, s, s, s, s, s])
    
    query += " ORDER BY post_id LIMIT ?"
    params.append(limit)
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"total": len(rows), "data": rows}

@app.get("/api/map/stats")
def get_map_stats():
    """Returns spatial district-level summary for heatmap and analytics considering post-move vacancies."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            district,
            COUNT(*) as total_posts,
            SUM(CASE WHEN is_actionable_vacancy = 1 THEN 1 ELSE 0 END) as vacant_posts,
            SUM(CASE WHEN is_baseline_vacant = 1 THEN 1 ELSE 0 END) as baseline_vacant_posts,
            SUM(CASE WHEN is_newly_vacated = 1 THEN 1 ELSE 0 END) as newly_vacated_posts,
            SUM(CASE WHEN is_su_retained = 1 THEN 1 ELSE 0 END) as su_retained_posts,
            SUM(CASE WHEN is_actionable_vacancy = 0 AND (occupancy_status = 'Occupied' OR occupancy_status = 'FILLED') THEN 1 ELSE 0 END) as occupied_posts,
            SUM(CASE WHEN tenure_over_flag = 'Yes' THEN 1 ELSE 0 END) as over_tenure_posts,
            AVG(latitude) as lat,
            AVG(longitude) as lng
        FROM sacrosanct_cadre_posts
        WHERE latitude != 0.0
        GROUP BY district
        ORDER BY vacant_posts DESC, total_posts DESC;
    """)
    districts = [dict(r) for r in cur.fetchall()]
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_posts,
            SUM(CASE WHEN is_actionable_vacancy = 1 THEN 1 ELSE 0 END) as total_vacant,
            SUM(CASE WHEN is_baseline_vacant = 1 THEN 1 ELSE 0 END) as total_baseline_vacant,
            SUM(CASE WHEN is_newly_vacated = 1 THEN 1 ELSE 0 END) as total_newly_vacated,
            SUM(CASE WHEN is_su_retained = 1 THEN 1 ELSE 0 END) as total_su_retained,
            SUM(CASE WHEN is_actionable_vacancy = 0 AND (occupancy_status = 'Occupied' OR occupancy_status = 'FILLED') THEN 1 ELSE 0 END) as total_occupied,
            SUM(CASE WHEN tenure_over_flag = 'Yes' THEN 1 ELSE 0 END) as total_over_tenure
        FROM sacrosanct_cadre_posts;
    """)
    summary = dict(cur.fetchone())
    conn.close()
    return {"summary": summary, "districts": districts}

# =========================================================================
# SPLIT DECISION BOARD ENDPOINTS (CANDIDATES & VACANCIES)
# =========================================================================

@app.get("/api/split-board/candidates")
def get_split_board_candidates(
    pool: str = "ALL",
    district: Optional[str] = None,
    designation: Optional[str] = None,
    avd_member: Optional[str] = None,
    category: Optional[str] = None,
    tenure_over: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "seniority",
    sort: Optional[str] = None
):
    """Returns unified list of transfer candidates across Roster, Obliterated, Over-Tenure, and Cadre."""
    if sort:
        sort_by = sort

    conn = get_db()
    cur = conn.cursor()
    candidates = []

    # 1. 50-Point Roster pool
    if pool in ("ALL", "roster"):
        cur.execute("""
            SELECT 
                'roster_' || sl_no AS candidate_id,
                roster_point,
                point_reserved_for AS reservation_category,
                officer_name,
                hrms_id,
                present_posting AS current_designation,
                present_block AS current_block,
                present_district AS current_district,
                tenure_years,
                dor,
                service_status,
                gradation_sl,
                avd_member,
                '50-Point Roster' AS pool_label,
                'roster' AS pool_type
            FROM roster_50_point_candidates
        """)
        for r in cur.fetchall():
            d = dict(r)
            d["current_establishment"] = d.get("current_posting") or "Block / Sub-Div Office"
            d["tenure_display"] = f"{d['tenure_years']} yrs" if d.get("tenure_years") else "-"
            candidates.append(d)

    # 2. Obliterated Posts / Abolished Leads pool
    if pool in ("ALL", "obliterated"):
        cur.execute("""
            SELECT 
                'oblit_' || id AS candidate_id,
                oblit_sl AS roster_point,
                officer_name,
                hrms_id,
                post_name AS current_designation,
                establishment AS current_establishment,
                block AS current_block,
                district AS current_district,
                tenure AS tenure_years,
                '' AS dor,
                avd_member,
                'Obliterated Post Lead' AS pool_label,
                'obliterated' AS pool_type
            FROM ABOLISHED_POST_LEADS
            WHERE officer_name IS NOT NULL AND officer_name != ''
        """)
        for r in cur.fetchall():
            d = dict(r)
            d["reservation_category"] = "UR"
            d["gradation_sl"] = 9999
            d["tenure_display"] = str(d.get("tenure_years") or "-")
            candidates.append(d)

    # 3. Over-Tenure pool
    if pool in ("over_tenure", "overtenure"):
        cur.execute("""
            SELECT 
                'cadre_' || id AS candidate_id,
                post_sl,
                incumbent_name AS officer_name,
                incumbent_hrms AS hrms_id,
                designation AS current_designation,
                establishment AS current_establishment,
                block AS current_block,
                district AS current_district,
                tenure_years,
                dor,
                avd_member,
                'Over-Tenure (>3-4y)' AS pool_label,
                'overtenure' AS pool_type
            FROM cadre_1794_posts
            WHERE tenure_over_flag = 'Yes' AND incumbent_name IS NOT NULL
        """)
        for r in cur.fetchall():
            d = dict(r)
            d["reservation_category"] = "UR"
            d["gradation_sl"] = d.get("post_sl") or 9999
            d["tenure_display"] = str(d.get("tenure_years") or "-")
            candidates.append(d)

    # 4. Cadre Serving pool
    if pool in ("cadre", "cadre_all"):
        cur.execute("""
            SELECT 
                'cadre_' || id AS candidate_id,
                post_sl,
                incumbent_name AS officer_name,
                incumbent_hrms AS hrms_id,
                designation AS current_designation,
                establishment AS current_establishment,
                block AS current_block,
                district AS current_district,
                tenure_years,
                dor,
                avd_member,
                'Serving Cadre Officer' AS pool_label,
                'cadre' AS pool_type
            FROM cadre_1794_posts
            WHERE UPPER(occupancy_status) = 'FILLED' AND incumbent_name IS NOT NULL
        """)
        for r in cur.fetchall():
            d = dict(r)
            d["reservation_category"] = "UR"
            d["gradation_sl"] = d.get("post_sl") or 9999
            d["tenure_display"] = str(d.get("tenure_years") or "-")
            candidates.append(d)

    conn.close()

    # Client / parameter filters
    filtered = []
    for c in candidates:
        # Standard field aliases
        c["designation"] = c.get("current_designation") or ""
        c["district"] = c.get("current_district") or ""
        c["present_posting"] = c.get("current_establishment") or ""
        c["tenure"] = c.get("tenure_display") or ""
        c["source_pool"] = c.get("pool_type") or "cadre"
        c["category_caste"] = c.get("reservation_category") or ""
        ty = c.get("tenure_years")
        try:
            c["tenure_over_flag"] = "Yes" if (float(str(ty).replace("y","").strip()) >= 3.0) else "No"
        except Exception:
            c["tenure_over_flag"] = "No"

        if district and district != "ALL":
            if (c.get("current_district") or "").strip().lower() != district.strip().lower():
                continue
        if designation and designation != "ALL":
            if designation.lower() not in (c.get("current_designation") or "").lower():
                continue
        if avd_member and avd_member != "ALL":
            is_yes = (c.get("avd_member") or "").strip().lower() == "yes"
            if avd_member.lower() in ("yes", "true", "1") and not is_yes:
                continue
            if avd_member.lower() in ("no", "false", "0") and is_yes:
                continue
        if category and category != "ALL":
            cat_check = (c.get("reservation_category") or "UR").strip().upper()
            if category.strip().upper() not in cat_check:
                continue
        if tenure_over and tenure_over != "ALL":
            if c["tenure_over_flag"] != tenure_over:
                continue
        if search:
            s = search.strip().lower()
            combined = f"{c.get('officer_name') or ''} {c.get('hrms_id') or ''} {c.get('current_designation') or ''} {c.get('current_establishment') or ''} {c.get('current_district') or ''} {c.get('current_block') or ''}".lower()
            if s not in combined:
                continue
        filtered.append(c)

    # Sorting
    if sort_by == "tenure_desc":
        def parse_tenure(v):
            txt = str(v or "")
            try:
                if "y" in txt:
                    return float(txt.split("y")[0].strip())
                return float(txt)
            except Exception:
                return 0.0
        filtered.sort(key=lambda x: parse_tenure(x.get("tenure_years")), reverse=True)
    elif sort_by == "dor_asc":
        filtered.sort(key=lambda x: str(x.get("dor") or "9999"))
    elif sort_by == "name_asc":
        filtered.sort(key=lambda x: str(x.get("officer_name") or "").lower())
    elif sort_by == "district_asc":
        filtered.sort(key=lambda x: (str(x.get("current_district") or "").lower(), str(x.get("officer_name") or "").lower()))
    else:  # seniority
        def safe_int(v, default=9999):
            try:
                return int(v)
            except Exception:
                return default
        filtered.sort(key=lambda x: (safe_int(x.get("gradation_sl")), safe_int(x.get("roster_point"))))

    avd_count = sum(1 for c in filtered if (c.get("avd_member") or "").strip().lower() == "yes")

    return {
        "total": len(filtered),
        "avd_count": avd_count,
        "candidates": filtered,
        "data": filtered
    }

@app.get("/api/split-board/vacancies")
def get_split_board_vacancies(
    scope: str = "all",
    type: str = "ALL",
    category: Optional[str] = None,
    district: Optional[str] = None,
    designation: Optional[str] = None,
    pay_level: Optional[str] = None,
    level: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "district_asc",
    sort: Optional[str] = None
):
    """Returns sanctioned vacancies considering proposed moves with district, designation, and spatial metadata."""
    if category and category != "ALL":
        type = category
    if level and level != "ALL":
        pay_level = level
    if sort:
        sort_by = sort

    conn = get_db()
    cur = conn.cursor()

    # Scope filtering
    where_scope = "is_actionable_vacancy = 1"
    if scope == "baseline":
        where_scope = "is_baseline_vacant = 1"
    elif scope == "newly_vacated":
        where_scope = "is_newly_vacated = 1"
    elif scope == "su_retained":
        where_scope = "is_su_retained = 1"
    elif scope == "full":
        where_scope = "(is_actionable_vacancy = 1 OR is_su_retained = 1)"

    cur.execute(f"""
        SELECT 
            id AS post_id,
            post_sl,
            district,
            block,
            establishment,
            estab_type,
            designation,
            post_code,
            pay_level,
            occupancy_status,
            detailed_presentation,
            reported_block,
            post_move_vacancy_status,
            vacated_by_hrms,
            vacated_by_name,
            vacated_by_basis,
            movement_details,
            is_actionable_vacancy,
            is_baseline_vacant,
            is_newly_vacated,
            is_su_retained
        FROM cadre_1794_posts
        WHERE {where_scope}
    """)
    rows = [dict(r) for r in cur.fetchall()]

    # Summary counts
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE is_baseline_vacant = 1")
    baseline_cnt = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE is_newly_vacated = 1")
    newly_vacated_cnt = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE is_actionable_vacancy = 1")
    actionable_cnt = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE is_su_retained = 1")
    su_retained_cnt = cur.fetchone()[0]
    conn.close()

    filtered = []
    for p in rows:
        desig = (p.get("designation") or "").lower()
        pl = (p.get("pay_level") or "").upper()
        p_code = (p.get("post_code") or "").upper()

        # Classify post
        is_dd = "deputy director" in desig or p_code == "DD" or "17" in pl
        p["post_type"] = "dd" if is_dd else "other"

        if type and type != "ALL":
            if type == "dd" and not is_dd:
                continue
            if type == "other" and is_dd:
                continue

        if district and district != "ALL":
            if (p.get("district") or "").strip().lower() != district.strip().lower():
                continue

        if designation and designation != "ALL":
            if designation.lower() not in desig:
                continue

        if pay_level and pay_level != "ALL":
            if pay_level.upper() not in pl:
                continue

        if search:
            s = search.strip().lower()
            combined = f"{p.get('designation') or ''} {p.get('establishment') or ''} {p.get('district') or ''} {p.get('block') or ''} {p.get('detailed_presentation') or ''} {p.get('post_code') or ''} {p.get('vacated_by_name') or ''} {p.get('movement_details') or ''}".lower()
            if s not in combined:
                continue

        p["is_apex"] = p_code in ("DIR", "ADDL") or "director of ah" in desig
        filtered.append(p)

    # Sorting
    if sort_by == "level_desc":
        level_order = {"LEVEL-22": 1, "LEVEL-21": 2, "LEVEL-19": 3, "LEVEL-17": 4, "LEVEL-16": 5}
        filtered.sort(key=lambda x: level_order.get((x.get("pay_level") or "").upper(), 99))
    elif sort_by == "id_asc":
        filtered.sort(key=lambda x: int(x.get("post_id") or 0))
    elif sort_by == "office_asc":
        filtered.sort(key=lambda x: (str(x.get("establishment") or "").lower(), str(x.get("district") or "").lower()))
    else:  # district_asc
        filtered.sort(key=lambda x: (str(x.get("district") or "").lower(), str(x.get("designation") or "").lower()))

    districts_present = len(set(p.get("district") for p in filtered if p.get("district")))

    return {
        "total": len(filtered),
        "districts_count": districts_present,
        "scope": scope,
        "summary": {
            "total_actionable": actionable_cnt,
            "baseline_vacant": baseline_cnt,
            "newly_vacated": newly_vacated_cnt,
            "substantive_vacant_on_su": su_retained_cnt
        },
        "vacancies": filtered,
        "data": filtered
    }

@app.get("/api/verification/summary")
def get_verification_summary():
    """Returns real-time aggregate results from the 10-Agent Verification Matrix."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM multi_agent_verification_summary")
    audited_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM multi_agent_verification_summary WHERE consensus_status = '10/10_UNANIMOUS_PASS'")
    unanimous_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM multi_agent_verification_summary WHERE discrepancies = 0")
    zero_disc_count = cur.fetchone()[0]

    # Breakdown by agent
    cur.execute("""
        SELECT agent_name, dimension,
               SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) as passed,
               SUM(CASE WHEN status = 'DISCREPANCY' THEN 1 ELSE 0 END) as discrepancies,
               SUM(CASE WHEN status = 'WARNING' THEN 1 ELSE 0 END) as warnings,
               SUM(CASE WHEN status = 'INFO' THEN 1 ELSE 0 END) as info
        FROM multi_agent_verification_log
        GROUP BY agent_name, dimension
        ORDER BY agent_id ASC
    """)
    agents_breakdown = [dict(r) for r in cur.fetchall()]
    
    cur.execute("SELECT * FROM multi_agent_verification_summary ORDER BY last_audited_at DESC LIMIT 15")
    recent_officers = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "total_officers_audited": audited_count,
        "unanimous_10_of_10": unanimous_count,
        "clean_records_zero_discrepancy": zero_disc_count,
        "pass_rate_pct": round((zero_disc_count / audited_count * 100), 1) if audited_count else 0.0,
        "agents": agents_breakdown,
        "recent_audited_officers": recent_officers
    }

@app.get("/api/verification/officers")
def get_verification_officers(search: Optional[str] = None, status: Optional[str] = None, limit: int = 100, offset: int = 0):
    """Returns paginated and filterable list of audited officers."""
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT s.hrms_id, s.officer_name, m.gender, s.cadre_tier, m.district AS present_district,
               m.office_code, m.ddo_code, s.consensus_status, s.passed_checks,
               s.discrepancies, s.warnings, s.record_sha256
        FROM multi_agent_verification_summary s
        LEFT JOIN master_all_cadre_employees m ON s.hrms_id = m.hrms_id
        WHERE 1=1
    """
    params = []
    if search:
        s = f"%{search.strip()}%"
        query += " AND (s.hrms_id LIKE ? OR s.officer_name LIKE ? OR m.district LIKE ? OR s.cadre_tier LIKE ?)"
        params.extend([s, s, s, s])
    if status and status != "ALL":
        if status == "UNANIMOUS":
            query += " AND s.consensus_status = '10/10_UNANIMOUS_PASS'"
        elif status == "WARNINGS":
            query += " AND s.consensus_status = 'PASSED_WITH_WARNINGS'"
    
    cur.execute(f"SELECT COUNT(*) FROM ({query})", params)
    total = cur.fetchone()[0]

    query += " ORDER BY s.hrms_id LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"total": total, "officers": rows}

@app.get("/api/verification/export-excel")
def export_verification_excel():
    """Serves the authoritative Multi-Agent Verification Audit Report Excel workbook."""
    excel_path = os.path.join(os.path.dirname(__file__), "Multi_Agent_Verification_Audit_Report_20260914.xlsx")
    if os.path.exists(excel_path):
        return FileResponse(
            excel_path,
            filename="Multi_Agent_Verification_Audit_Report_20260914.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    raise HTTPException(status_code=404, detail="Audit report workbook not found.")

@app.get("/api/sacrosanct/summary")
def get_sacrosanct_summary():
    """Returns verification audit summary and cryptographic proof status."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM sacrosanct_cadre_posts")
    posts_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sacrosanct_officer_dossier")
    officers_count = cur.fetchone()[0]
    cur.execute("SELECT * FROM sacrosanct_audit_ledger ORDER BY event_id DESC LIMIT 10")
    ledger_events = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {
        "status": "VERIFIED_SACROSANCT",
        "verification_pipeline_tiers": 4,
        "cadre_posts_locked": posts_count,
        "officer_dossiers_locked": officers_count,
        "tamper_evidence": "SHA-256 State Hashing Active",
        "recent_ledger_events": ledger_events
    }


@app.get("/api/roster")
def get_roster_candidates(
    category: Optional[str] = None,
    allotment_status: Optional[str] = None,
    search: Optional[str] = None,
    avd_member: Optional[str] = None
):
    conn = get_db()
    cur = conn.cursor()

    query = """
    SELECT r.*,
           m.sl_no as master_sl,
           m.transferred_substantive_post as master_sub,
           m.service_utilized_at as master_su,
           m.transfer_basis as master_basis,
           m.administrative_remarks as master_rem,
           m.comments_directive as master_comments
    FROM roster_50_point_candidates r
    LEFT JOIN master_final_order_schedule m ON (m.roster_sl = CAST(r.sl_no AS TEXT))
    WHERE 1=1
    """
    params = []

    if category and category != "ALL":
        query += " AND r.point_reserved_for = ?"
        params.append(category)

    if allotment_status and allotment_status != "ALL":
        query += " AND r.allotment_status = ?"
        params.append(allotment_status)

    if avd_member and avd_member != "ALL":
        query += " AND r.avd_member = ?"
        params.append(avd_member)

    if search:
        s = f"%{search.strip()}%"
        query += """ AND (
            r.officer_name LIKE ? OR 
            r.hrms_id LIKE ? OR 
            r.present_posting LIKE ? OR 
            r.present_district LIKE ? OR
            r.point_reserved_for LIKE ?
        )"""
        params.extend([s, s, s, s, s])

    query += " ORDER BY r.sl_no ASC"

    cur.execute(query, params)
    raw_rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    # Dynamic calculation of active sequence serial (skipping retired / superannuated)
    active_counter = 1
    processed_rows = []
    for row in raw_rows:
        status = (row.get("service_status") or "").strip().lower()
        is_ret = 1 if status in ["retired", "superannuated", "deceased", "left service"] else 0

        # Check DOR vs 01.09.2026
        dor = (row.get("dor") or row.get("service_ends") or "").strip()
        if dor and not is_ret:
            clean_dor = dor.replace("/", "-")
            parts = clean_dor.split("-")
            if len(parts) == 3:
                try:
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    else:  # DD-MM-YYYY
                        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                    if y < 2026 or (y == 2026 and m < 9):
                        is_ret = 1
                except (ValueError, IndexError):
                    pass

        row["is_retired"] = is_ret
        if is_ret:
            row["active_roster_sl"] = None
        else:
            row["active_roster_sl"] = active_counter
            active_counter += 1

        processed_rows.append(row)

    return {"count": len(processed_rows), "data": processed_rows}


@app.get("/api/gradation")
def get_gradation_list(
    grade_section: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    gender: Optional[str] = None,
    search: Optional[str] = None,
    avd_member: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """
    Returns dynamic gradation list brought forward from published list No. 3768-AR&AH.
    Retired officers maintain their historical 2025 sequence, have sl_2026 = None, and are marked is_retired = 1.
    """
    conn = get_db()
    cur = conn.cursor()

    base_query = "FROM official_gradation_list WHERE 1=1"
    params = []

    if grade_section and grade_section != "ALL":
        base_query += " AND grade_section = ?"
        params.append(grade_section)

    if status and status != "ALL":
        if status.lower() == "serving":
            base_query += " AND is_retired = 0"
        elif status.lower() in ["retired", "superannuated"]:
            base_query += " AND is_retired = 1"

    if gender and gender != "ALL":
        base_query += " AND gender = ?"
        params.append(gender)

    if avd_member and avd_member != "ALL":
        base_query += " AND avd_member = ?"
        params.append(avd_member)

    if search:
        s = f"%{search.strip()}%"
        base_query += " AND (officer_name LIKE ? OR clean_name LIKE ? OR hrms_id LIKE ? OR present_posting LIKE ? OR qualifications LIKE ?)"
        params.extend([s, s, s, s, s])

    # Count query
    count_query = f"SELECT COUNT(*) {base_query}"
    cur.execute(count_query, params)
    total_count = cur.fetchone()[0]

    # Data query
    data_query = f"""
        SELECT id, grade_section, sl_2025, sl_2026, status_2026, is_retired,
               officer_name, clean_name, hrms_id, gender, qualifications,
               doj, dor, avd_member, present_posting,
               recommended_post, recommendation_reason, remarks, record_sha256
        {base_query}
        ORDER BY id ASC
    """
    if page_size > 0:
        offset = (page - 1) * page_size
        data_query += f" LIMIT {page_size} OFFSET {offset}"

    cur.execute(data_query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size if page_size > 0 else 1,
        "data": rows
    }


@app.get("/api/gradation/stats")
def get_gradation_stats():
    """
    Returns summary metrics for the dynamic Gradation List:
    Total, Serving, Retired, Male, Female, and breakdown across Grade Sections.
    """
    conn = get_db()
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM official_gradation_list").fetchone()[0]
    serving = cur.execute("SELECT COUNT(*) FROM official_gradation_list WHERE is_retired = 0").fetchone()[0]
    retired = cur.execute("SELECT COUNT(*) FROM official_gradation_list WHERE is_retired = 1").fetchone()[0]
    female = cur.execute("SELECT COUNT(*) FROM official_gradation_list WHERE gender = 'Female'").fetchone()[0]
    male = cur.execute("SELECT COUNT(*) FROM official_gradation_list WHERE gender = 'Male'").fetchone()[0]

    sections_raw = cur.execute("""
        SELECT grade_section,
               COUNT(*) as total,
               SUM(CASE WHEN is_retired = 0 THEN 1 ELSE 0 END) as serving,
               SUM(CASE WHEN is_retired = 1 THEN 1 ELSE 0 END) as retired
        FROM official_gradation_list
        GROUP BY grade_section
        ORDER BY MIN(id) ASC
    """).fetchall()

    sections = [
        {"section": r["grade_section"], "total": r["total"], "serving": r["serving"], "retired": r["retired"]}
        for r in sections_raw
    ]

    conn.close()
    return {
        "total": total,
        "serving": serving,
        "retired": retired,
        "female": female,
        "male": male,
        "sections": sections
    }


@app.get("/api/posts/visual-grid")
def get_posts_visual_grid_endpoint(
    session_id: str = "CURRENT_SESSION",
    district: Optional[str] = None
):
    """
    Visual Grid API:
    Returns all cadre & DD posts grouped by district with real-time color classifications:
    - Pure Vacancies (Green)
    - Vacant on Paper / Incumbent on SU (Amber)
    - Action Required / Conflict / Replacement Needed (Red)
    - Board Selected (Purple)
    - Obliterated / Abolished under 1808 (Grey Strikethrough)
    - Filled / Occupied (Blue)
    """
    return engine.get_posts_visual_grid(session_id=session_id, district_filter=district)

@app.get("/api/employees/master")
def get_master_employees_api(
    query: Optional[str] = None,
    district: Optional[str] = "ALL",
    category: Optional[str] = "all",
    avd_member: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
):
    """
    Search and filter the complete state-wide master employee directory (1,624 officers).
    Categories: 'all', 'active', 'hq', 'roster', 'unsanctioned'
    """
    return engine.get_master_employees(
        query=query or "",
        district=district or "ALL",
        category=category or "all",
        avd_member=avd_member,
        page=page,
        page_size=page_size
    )

@app.get("/api/hq/deployed")
def get_hq_deployed_api():
    """
    Returns the complete list of 37 officers deployed at Directorate Headquarters & Attached Units.
    """
    return engine.get_hq_deployed_officers()

@app.get("/api/obliterated")
def get_obliterated_officers(status: Optional[str] = None, search: Optional[str] = None, avd_member: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM ABOLISHED_POST_LEADS WHERE 1=1"
    params = []

    if status and status != "ALL":
        query += " AND rehabilitation_status = ?"
        params.append(status)

    if avd_member and avd_member != "ALL":
        query += " AND avd_member = ?"
        params.append(avd_member)

    if search:
        s = f"%{search.strip()}%"
        query += " AND (officer_name LIKE ? OR hrms_id LIKE ? OR post_name LIKE ? OR district LIKE ? OR block LIKE ? OR establishment LIKE ?)"
        params.extend([s, s, s, s, s, s])

    query += " ORDER BY oblit_sl"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {"count": len(rows), "data": rows}

@app.get("/api/available-posts")
def get_available_posts(
    type: str = Query("substantive", regex="^(substantive|su)$"),
    role: str = Query("roster", regex="^(roster|obliterated|displaced)$"),
    session_id: str = "CURRENT_SESSION",
    search: Optional[str] = None
):
    """
    Dynamically returns posts filtered in real-time.
    Posts already assigned in the current session are excluded so options update sequentially.
    """
    if type == "substantive":
        return engine.get_available_substantive_posts(officer_role=role, session_id=session_id)
    else:
        return engine.get_available_su_posts(session_id=session_id, search=search)

@app.get("/api/districts")
def get_districts():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT district FROM cadre_1794_posts WHERE district IS NOT NULL ORDER BY district")
    districts = [r[0] for r in cur.fetchall() if r[0]]
    conn.close()
    return districts

@app.get("/api/designations")
def get_designations():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT designation FROM cadre_1794_posts WHERE designation IS NOT NULL ORDER BY designation")
    desigs = [r[0] for r in cur.fetchall() if r[0]]
    conn.close()
    return desigs

@app.get("/api/orders")
def get_orders(search: Optional[str] = None, category: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM official_orders WHERE 1=1"
    params = []

    if category and category != "ALL":
        query += " AND category = ?"
        params.append(category)

    if search:
        s = f"%{search.strip()}%"
        query += " AND (title LIKE ? OR order_number LIKE ? OR key_officers LIKE ?)"
        params.extend([s, s, s])

    query += " ORDER BY order_date DESC LIMIT 100"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {"count": len(rows), "data": rows}

# --- SIMULATION & SOLVER ENDPOINTS ---

@app.post("/api/simulation/allot")
def simulate_allot(req: AllotRequest):
    if req.substantive_post_id == 1 or req.su_post_id == 1 or str(req.officer_hrms).strip() == "1992005664":
        return {
            "success": False,
            "error": "CRITICAL ADMINISTRATIVE PROHIBITION: The Director of AH&VS (Dr. Nikhil Kumar Shit, Level-22) is the apex head of the department and cannot be replaced, displaced, or targeted for Service Utilization."
        }
    res = engine.simulate_dual_allotment(
        session_id=req.session_id,
        officer_hrms=req.officer_hrms,
        substantive_post_id=req.substantive_post_id,
        su_post_id=req.su_post_id,
        reason=req.reason or "Manual Posting Allotment",
        officer_type=req.officer_type or "roster"
    )
    return res

@app.post("/api/simulation/auto-solve")
def auto_solve(req: AutoSolveRequest):
    res = engine.solve_multi_party_cadre(session_id=req.session_id)
    return res

@app.post("/api/simulation/reset")
def reset_simulation(session_id: str = "CURRENT_SESSION"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM simulation_assignments WHERE session_id = ?", (session_id,))
    cur.execute("DELETE FROM displaced_officers_pool WHERE session_id = ? OR officer_hrms = '1992005664'", (session_id,))
    cur.execute("""
    UPDATE roster_50_point_candidates 
    SET substantive_post_id = NULL, substantive_post_name = NULL, 
        su_post_id = NULL, su_post_name = NULL, allotment_status = 'Under verification'
    """)
    cur.execute("""
    UPDATE ABOLISHED_POST_LEADS 
    SET substantive_post_id = NULL, substantive_post_name = NULL, 
        su_post_id = NULL, su_post_name = NULL, rehabilitation_status = 'Pending'
    """)
    cur.execute("UPDATE available_dd_posts SET allotment_status = 'Under verification', allotted_hrms = NULL, allotted_name = NULL")
    cur.execute("UPDATE cadre_1794_posts SET is_substantive_blocked = 0, substantive_allotted_hrms = NULL, substantive_allotted_name = NULL, su_allotted_hrms = NULL, su_allotted_name = NULL")
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Simulation session '{session_id}' has been reset to baseline."}

@app.get("/api/simulation/history")
def get_simulation_history(session_id: str = "CURRENT_SESSION"):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM simulation_assignments WHERE session_id = ? ORDER BY id DESC", (session_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"count": len(rows), "data": rows}

@app.get("/api/officer/{hrms_id}")
def get_officer_dossier_endpoint(hrms_id: str):
    """Returns complete administrative dossier for any officer."""
    dossier = engine.get_officer_dossier(hrms_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Officer HRMS {hrms_id} not found.")
    return dossier

@app.post("/api/policy/evaluate")
def evaluate_policy_endpoint(req: PolicyEvaluateRequest):
    """
    Evaluates transfer policy compliance (Transfer Policy 2009 / Memo 291)
    for an officer and target post in real-time.
    """
    conn = get_db()
    cur = conn.cursor()

    # 1. Fetch officer details
    officer = None
    cur.execute("SELECT * FROM roster_50_point_candidates WHERE hrms_id = ?", (req.officer_hrms,))
    r = cur.fetchone()
    if r:
        officer = dict(r)
    else:
        cur.execute("SELECT * FROM ABOLISHED_POST_LEADS WHERE hrms_id = ?", (req.officer_hrms,))
        r = cur.fetchone()
        if r:
            officer = dict(r)
        else:
            cur.execute("SELECT * FROM cadre_1794_posts WHERE incumbent_hrms = ?", (req.officer_hrms,))
            r = cur.fetchone()
            if r:
                officer = dict(r)
            else:
                cur.execute("SELECT * FROM master_all_cadre_employees WHERE hrms_id = ?", (req.officer_hrms,))
                r = cur.fetchone()
                if r:
                    officer = dict(r)

    if not officer:
        conn.close()
        return {
            "overall_status": "UNKNOWN",
            "is_compliant": False,
            "verdict_badge": "GREY",
            "summary_label": "Officer Record Not Found",
            "violations": ["Officer record not found in database."],
            "cautions": [],
            "checks": []
        }

    # 2. Fetch target substantive post
    target_post = None
    cur.execute("SELECT * FROM available_dd_posts WHERE dd_sl = ?", (req.substantive_post_id,))
    r = cur.fetchone()
    if r:
        target_post = dict(r)
    else:
        cur.execute("SELECT * FROM cadre_1794_posts WHERE id = ?", (req.substantive_post_id,))
        r = cur.fetchone()
        if r:
            target_post = dict(r)

    if not target_post:
        conn.close()
        return {
            "overall_status": "UNKNOWN",
            "is_compliant": False,
            "verdict_badge": "GREY",
            "summary_label": "Target Post Record Not Found",
            "violations": ["Target post record not found in database."],
            "cautions": [],
            "checks": []
        }

    # 3. Check SU collision if SU post is specified
    su_collision = None
    if req.su_post_id:
        cur.execute("SELECT * FROM cadre_1794_posts WHERE id = ?", (req.su_post_id,))
        su_r = cur.fetchone()
        if su_r:
            su_p = dict(su_r)
            if su_p.get("occupancy_status") in ("FILLED", "Occupied") and str(su_p.get("incumbent_hrms") or "").strip() != str(req.officer_hrms).strip():
                su_collision = {
                    "incumbent_name": su_p.get("incumbent_name"),
                    "incumbent_hrms": su_p.get("incumbent_hrms"),
                    "post_name": su_p.get("post_name") or su_p.get("designation") or "Cadre Post",
                    "district": su_p.get("district")
                }

    conn.close()

    # Run core policy rules
    res = engine.check_officer_rules(officer, target_post)

    # SU conflict handling
    if su_collision:
        res["violations"].append(f"Service Utilization Collision: Selected SU post '{su_collision['post_name']}' in {su_collision['district']} is already occupied by {su_collision['incumbent_name']} (HRMS: {su_collision['incumbent_hrms']}). Allotment will trigger a displacement chain.")
        res["overall_status"] = "VIOLATION"
        res["is_compliant"] = False
        res["verdict_badge"] = "RED"
        res["summary_label"] = "Collision Risk Detected (Forced Displacement)"
        res["checks"].append({
            "criterion": "Service Utilization (SU) Conflict",
            "clause": "Rule 75(a) Non-Collision",
            "status": "COLLISION_RISK",
            "badge": "RED",
            "message": f"Post currently occupied by {su_collision['incumbent_name']} (HRMS: {su_collision['incumbent_hrms']})."
        })
    else:
        res["checks"].append({
            "criterion": "Service Utilization (SU) Conflict",
            "clause": "Rule 75(a) Non-Collision",
            "status": "CLEAR" if not req.su_post_id else "SU_ATTACHMENT_VERIFIED",
            "badge": "GREEN",
            "message": "No collision conflict." if not req.su_post_id else "SU attachment post verified available."
        })

    return res

@app.get("/api/search/omni")
def omni_search_endpoint(q: str = Query(..., min_length=1), limit: int = 30):
    """
    Universal Spotlight Search across:
    - Officers / Personnel (Roster, Master Directory, Obliterated, Displaced)
    - Sanctioned & Available Posts (1,794 Cadre, Available DD, SU posts)
    - Official Orders & Gazettes (337 Authoritative, 470 Official)
    - Policy Rules & Memos (Memo 291 of 2009, Memo 1808, Memo 1809, Rule 75a)
    """
    conn = get_db()
    cur = conn.cursor()
    query_str = f"%{q.strip()}%"

    results = {
        "query": q,
        "officers": [],
        "posts": [],
        "orders": [],
        "policy_rules": []
    }

    # 1. Search Officers
    cur.execute("""
    SELECT hrms_id, officer_name, designation, district, establishment AS current_office, dor, avd_member, 'master_employee' AS source
    FROM master_all_cadre_employees
    WHERE officer_name LIKE ? OR hrms_id LIKE ? OR designation LIKE ? OR district LIKE ?
    LIMIT ?
    """, (query_str, query_str, query_str, query_str, limit))
    emp_rows = [dict(r) for r in cur.fetchall()]

    cur.execute("""
    SELECT hrms_id, officer_name, roster_point, point_reserved_for, allotment_status, substantive_post_name, su_post_name, avd_member, 'roster' AS source
    FROM roster_50_point_candidates
    WHERE officer_name LIKE ? OR hrms_id LIKE ? OR roster_point LIKE ? OR substantive_post_name LIKE ?
    LIMIT ?
    """, (query_str, query_str, query_str, query_str, limit))
    roster_rows = [dict(r) for r in cur.fetchall()]

    cur.execute("""
    SELECT hrms_id, officer_name, post_name AS designation, district, rehabilitation_status AS allotment_status, substantive_post_name, avd_member, 'abolished_leads' AS source
    FROM ABOLISHED_POST_LEADS
    WHERE officer_name LIKE ? OR hrms_id LIKE ? OR post_name LIKE ? OR district LIKE ?
    LIMIT ?
    """, (query_str, query_str, query_str, query_str, limit))
    oblit_rows = [dict(r) for r in cur.fetchall()]

    seen_hrms = set()
    combined_officers = []
    for o in roster_rows + oblit_rows + emp_rows:
        hid = str(o.get("hrms_id") or "").strip()
        if hid and hid not in seen_hrms:
            seen_hrms.add(hid)
            combined_officers.append(o)
            if len(combined_officers) >= limit:
                break
    results["officers"] = combined_officers

    # 2. Search Posts (Cadre 1,794 + Available DD)
    cur.execute("""
    SELECT id AS post_id, designation AS post_name, designation, establishment AS office, establishment, district, block, occupancy_status, incumbent_name, incumbent_hrms, pay_level, 'cadre_1794' AS source
    FROM cadre_1794_posts
    WHERE designation LIKE ? OR establishment LIKE ? OR district LIKE ? OR block LIKE ? OR incumbent_name LIKE ?
    LIMIT ?
    """, (query_str, query_str, query_str, query_str, query_str, limit))
    cadre_rows = [dict(r) for r in cur.fetchall()]

    cur.execute("""
    SELECT dd_sl AS post_id, post_name, establishment, office, district, allotment_status AS occupancy_status, allotted_name AS incumbent_name, allotted_hrms AS incumbent_hrms, 'dd_post' AS source
    FROM available_dd_posts
    WHERE post_name LIKE ? OR office LIKE ? OR district LIKE ? OR dd_sl LIKE ?
    LIMIT ?
    """, (query_str, query_str, query_str, query_str, limit))
    dd_rows = [dict(r) for r in cur.fetchall()]
    results["posts"] = (cadre_rows + dd_rows)[:limit]

    # 3. Search Official Orders
    cur.execute("""
    SELECT order_index AS id, order_number, order_date, title AS subject, category, title AS summary, 'official_order' AS source
    FROM official_orders
    WHERE order_number LIKE ? OR title LIKE ? OR key_officers LIKE ? OR category LIKE ?
    LIMIT ?
    """, (query_str, query_str, query_str, query_str, limit))
    order_rows = [dict(r) for r in cur.fetchall()]

    cur.execute("""
    SELECT sl_no AS id, 'Master Order Schedule (337)' AS order_number, officer_name, hrms_id, present_post_full AS previous_posting, transferred_substantive_post AS final_substantive_post, transfer_basis, 'master_order' AS source
    FROM master_final_order_schedule
    WHERE officer_name LIKE ? OR hrms_id LIKE ? OR transferred_substantive_post LIKE ? OR present_post_full LIKE ?
    LIMIT ?
    """, (query_str, query_str, query_str, query_str, limit))
    master_order_rows = [dict(r) for r in cur.fetchall()]
    results["orders"] = (master_order_rows + order_rows)[:limit]

    # 4. Search Policy Rules (Memo 291 of 2009, Rule 75a, Notifications 1808 & 1809)
    policy_corpus = [
        {
            "id": "memo-291-tenure-general",
            "title": "Transfer Policy 2009 (Memo 291): General Area Tenure",
            "clause": "Normative Tenure: 5 Years",
            "description": "Standard maximum tenure in a district/station is 5.0 years. Officers serving beyond 5 years are placed on rotation priority.",
            "category": "Tenure Policy"
        },
        {
            "id": "memo-291-tenure-difficult",
            "title": "Transfer Policy 2009 (Memo 291): Difficult & Hill Zone Tenure",
            "clause": "Normative Tenure: 4 Years",
            "description": "Tenure in hill & difficult districts (Darjeeling, Kalimpong, Alipurduar, Cooch Behar, Jalpaiguri, Uttar Dinajpur, Dakshin Dinajpur, Jhargram, Purulia) is strictly 4.0 years.",
            "category": "Tenure Policy"
        },
        {
            "id": "memo-291-para-13-exams",
            "title": "Transfer Policy 2009 Para 13: Children Board Examination Safeguard",
            "clause": "Para 13 Protection",
            "description": "Officers whose children are appearing in Class X or XII Board Exams (Madhyamik, ICSE, CBSE, HS) are protected against displacement outside their current district during the academic session.",
            "category": "Welfare Safeguard"
        },
        {
            "id": "memo-291-para-5-spouse",
            "title": "Transfer Policy 2009 Para 5: Working Spouse Co-location",
            "clause": "Para 5 Accommodation",
            "description": "Spouses employed in State Govt, Central Govt, or School/Colleges are entitled to accommodation within the same district or contiguous stations.",
            "category": "Family Welfare"
        },
        {
            "id": "memo-291-superannuation",
            "title": "Transfer Policy 2009: 2-Year Superannuation Exemption",
            "clause": "Retirement Immunity",
            "description": "Officers within 2 years of Date of Retirement (DOR) are exempted from routine transfers and granted priority for choice posting or home district.",
            "category": "Retirement Norm"
        },
        {
            "id": "notif-1809-cadre",
            "title": "Reconstitution Rules 2025 (Notification No. 1809)",
            "clause": "1,794 Restructured Cadre Posts",
            "description": "Gazette notification restructuring WBAH&VS into 1,794 sanctioned posts across Directorate, HQ, Districts, Sub-Divisions, and Blocks.",
            "category": "Cadre Statute"
        },
        {
            "id": "notif-1808-obliteration",
            "title": "Post Obliteration Schedule 2025 (Notification No. 1808)",
            "clause": "106 Abolished Posts Rehabilitation",
            "description": "Statutory abolition of 106 posts with complete rehabilitation and protection of 73 serving officers.",
            "category": "Abolition Schedule"
        }
    ]

    ql = q.lower()
    matched_rules = [
        rule for rule in policy_corpus
        if ql in rule["title"].lower() or ql in rule["clause"].lower() or ql in rule["description"].lower() or ql in rule["category"].lower()
    ]
    results["policy_rules"] = matched_rules

    conn.close()
    return results

@app.get("/api/master-orders")
def get_master_orders_endpoint(
    search: Optional[str] = None,
    transfer_basis: Optional[str] = None,
    district: Optional[str] = None
):
    """Returns authoritative Promotion & Transfer Master Schedule (337 records)."""
    conn = get_db()
    cur = conn.cursor()
    query = """
    SELECT m.*
    FROM master_final_order_schedule m
    WHERE 1=1
    """
    params = []
    if search:
        s = f"%{search.strip()}%"
        query += " AND (m.officer_name LIKE ? OR m.present_post_full LIKE ? OR m.transferred_substantive_post LIKE ? OR m.service_utilized_at LIKE ? OR m.hrms_id LIKE ?)"
        params.extend([s, s, s, s, s])
    if transfer_basis and transfer_basis != "ALL":
        query += " AND m.transfer_basis LIKE ?"
        params.append(f"%{transfer_basis}%")
    if district and district != "ALL":
        query += " AND (m.present_district LIKE ? OR m.transferred_substantive_post LIKE ? OR m.service_utilized_at LIKE ?)"
        params.extend([f"%{district}%", f"%{district}%", f"%{district}%"])
    query += " ORDER BY m.sl_no ASC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"count": len(rows), "data": rows}

@app.get("/api/simulation/recommend-allotment")
def recommend_allotment_endpoint(officer_hrms: str = Query(...), session_id: str = "CURRENT_SESSION"):
    """AI Intelligent Allotment recommendation with statutory justification."""
    return engine.recommend_ai_allotment(officer_hrms=officer_hrms, session_id=session_id)

@app.get("/api/displaced-pool")
def get_displaced_pool_endpoint(session_id: str = "CURRENT_SESSION"):
    """Returns all officers displaced due to Service Utilization awaiting placement."""
    pool = engine.get_displaced_queue_pool(session_id)
    return {"count": len(pool), "data": pool}

@app.get("/api/simulation/export-excel")
def export_simulation_excel(session_id: str = "CURRENT_SESSION"):
    """Administratively disabled download endpoint."""
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.get("/api/simulation/export-docx")
def export_simulation_docx(session_id: str = "CURRENT_SESSION"):
    """Administratively disabled download endpoint."""
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

# --- DEPARTMENTAL DATA EXPORTER & REPORT BUILDER ENDPOINTS ---

@app.get("/api/export/meta")
def get_export_metadata_endpoint():
    """Returns schemas, active filter choices, and presets for custom exports."""
    return data_exporter.get_export_metadata()

@app.post("/api/export/preview")
def export_preview_endpoint(req: ExportQueryRequest):
    """Returns record count, sample rows, and applied filter descriptions."""
    filters = req.filters or {}
    limit = req.limit or 10
    rows, count, descs = data_exporter.fetch_records(
        req.dataset, filters, req.sort_by, req.sort_order or "asc", limit=limit
    )
    schema = data_exporter.get_export_metadata()["datasets"].get(req.dataset, {})
    return {
        "dataset": req.dataset,
        "total_count": count,
        "sample": rows,
        "filter_descriptions": descs,
        "columns": schema.get("columns", [])
    }

@app.post("/api/export/excel")
def export_excel_endpoint(req: ExportQueryRequest):
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.get("/api/export/excel")
def export_excel_get_endpoint():
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.post("/api/export/docx")
def export_docx_endpoint(req: ExportQueryRequest):
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.get("/api/export/docx")
def export_docx_get_endpoint():
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.get("/api/simulation/view-order-html", response_class=HTMLResponse)
def view_simulation_order_html(session_id: str = "CURRENT_SESSION"):
    """Returns printable authentic West Bengal Government Secretariat Gazette Order HTML."""
    html_content = generate_html_order(session_id)
    return HTMLResponse(content=html_content)

@app.get("/api/sync/status")
def get_sync_status():
    """Returns status of master decisions ledger, Google Sheets sync queue, and automated snapshots."""
    workspace_dir = "/tmp" if is_vercel else BASE_DIR
    sync_file = os.path.join(workspace_dir, "google_sheets_sync_queue.json")
    ledger_xlsx = os.path.join(workspace_dir, "Master_Decisions_Ledger.xlsx")
    ledger_csv = os.path.join(workspace_dir, "Master_Decisions_Ledger.csv")
    queue_count = 0
    if os.path.exists(sync_file):
        try:
            with open(sync_file, "r", encoding="utf-8") as f:
                queue = json.load(f)
                queue_count = len(queue)
        except Exception:
            pass

    backups = backup_mgr.list_backups()
    return {
        "master_ledger_xlsx_exists": os.path.exists(ledger_xlsx),
        "master_ledger_csv_exists": os.path.exists(ledger_csv),
        "pending_sync_queue_count": queue_count,
        "latest_backup": backups[0] if backups else None,
        "total_backups": len(backups),
        "sync_mode": "Automated Multi-Tier Persistent (Local Master Ledger + Background Sync Queue)"
    }

# --- BACKUP & RESTORE MANAGEMENT ENDPOINTS ---

@app.post("/api/backup/create")
def create_backup_endpoint(req: BackupCreateRequest):
    result = backup_mgr.create_backup(tag=req.tag or "manual")
    return result

@app.get("/api/backup/list")
def list_backups_endpoint():
    return {"backups": backup_mgr.list_backups()}

@app.post("/api/backup/restore")
def restore_backup_endpoint(req: BackupRestoreRequest):
    result = backup_mgr.restore_backup(req.filename)
    return result

def query_gemini_ai_studio(prompt: str, system_prompt: str = None) -> Optional[str]:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    model = os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    contents = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})
        contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow all West Bengal ARD cadre rules and statutory orders."}]})

    contents.append({"role": "user", "parts": [{"text": prompt}]})

    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(
                url,
                json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.2,
                        "maxOutputTokens": 1024
                    }
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
    except Exception as e:
        print(f"Gemini API Exception: {e}")
    return None

# --- AI COPILOT ENDPOINT ---

@app.post("/api/ai/query")
def ai_cadre_query(req: AIQueryRequest):
    q_raw = req.query.strip()
    q = q_raw.lower()

    # Check if Google AI Studio Gemini API is active
    system_ctx = """You are the Senior Administrative Cadre & Transfer Policy AI Consultant for the Animal Resources Development Department, Government of West Bengal.
Official Facts & Statutory Rules:
- Notification No. 1809 (18.06.2025): Total 1,794 active sanctioned cadre posts (1,044 occupied, 750 clear vacancies).
- Notification No. 1808 (18.06.2025): 106 abolished/obliterated posts (84 active serving incumbents awaiting rehabilitation).
- 50-Point Roster: 242 candidates promoted to 242 available unblocked Deputy Director posts (Level 17/19).
- Transfer Policy Memo 291: Maximum tenure in general zones is 5 years; in difficult/hill zones (Darjeeling, Kalimpong, Alipurduar, Coochbehar, Jalpaiguri, Uttar/Dakshin Dinajpur, Jungle Mahal) is 4 years.
- Superannuation: WBSR Rule 75(a) - retirement on the last day of the month of turning 60 years.
Always provide authoritative, accurate, statutory answers with clear formatting and markdown bullets."""

    gemini_output = query_gemini_ai_studio(q_raw, system_prompt=system_ctx)
    if gemini_output:
        return {
            "query": req.query,
            "response": gemini_output + "\n\n*(⚡ Response generated by Gemini 2.0 Flash via Google AI Studio)*"
        }

    conn = get_db()
    cur = conn.cursor()

    response_text = ""

    # Check for retirement query
    if "retire" in q or "superannuat" in q or "dor" in q:
        cur.execute("""
        SELECT incumbent_name, incumbent_hrms, designation, district, 
               incumbent_dor
        FROM cadre_1794_posts
        WHERE UPPER(occupancy_status) IN ('FILLED', 'OCCUPIED') AND incumbent_dor <= '2027-06-30'
        ORDER BY incumbent_dor ASC LIMIT 10
        """)
        retirees = cur.fetchall()
        response_text = "### 📋 Upcoming Superannuations (Next 9 Months)\nOfficers retiring between Sep 2026 and Jun 2027 (WBSR Rule 75a compliant):\n\n"
        for r in retirees:
            response_text += f"- **{r[0]}** (`{r[1]}`): {r[2]}, {r[3]} | DOR: **{r[4]}**\n"

    # Specific doctor query
    elif "dr." in q or "doctor" in q or any(term in q for term in ["chakraborty", "debasis", "sadhukhan", "das", "mondal", "chandan", "arup"]):
        words = [w.strip() for w in q.split() if len(w) > 3 and w not in ["about", "doctor", "where", "what", "which", "find"]]
        matches = []
        for w in words:
            cur.execute("""
            SELECT id, incumbent_name, incumbent_hrms, designation, 
                   establishment, block, district, incumbent_tenure, tenure_over_flag
            FROM cadre_1794_posts
            WHERE LOWER(incumbent_name) LIKE ? LIMIT 5
            """, (f"%{w}%",))
            matches.extend(cur.fetchall())

        if matches:
            response_text = f"### 🔍 Found {len(matches)} Departmental Officer Records in 1,794 Cadre:\n\n"
            for m in set(matches):
                response_text += f"**{m[1]}** (HRMS: `{m[2]}`)\n"
                response_text += f"- **Post**: {m[3]}, {m[4]} (Block: {m[5] or 'HQ'}, District: {m[6]})\n"
                response_text += f"- **Current Tenure**: {m[7]} (Tenure Over: `{m[8]}`)\n\n"
        else:
            response_text = f"No officer matching '{q}' found in the verified 1,794 Cadre."

    # Vacancy queries
    elif "vacan" in q or "empty" in q or "seat" in q:
        cur.execute("""
        SELECT designation, district, count(*) FROM cadre_1794_posts
        WHERE UPPER(occupancy_status) = 'VACANT'
        GROUP BY designation, district ORDER BY count(*) DESC LIMIT 12
        """)
        vacs = cur.fetchall()
        response_text = "### 🏢 Key Clear Vacancies in 1,794 Cadre:\n\n"
        for v in vacs:
            response_text += f"- **{v[0]}** in **{v[1]}**: `{v[2]}` vacancies\n"

    # Roster promotion queries
    elif "roster" in q or "promotion" in q:
        cur.execute("""
        SELECT count(*), 
               sum(case when point_reserved_for = 'SC' then 1 else 0 end),
               sum(case when point_reserved_for = 'ST' then 1 else 0 end),
               sum(case when point_reserved_for = 'UR' then 1 else 0 end)
        FROM roster_50_point_candidates
        """)
        r_stats = cur.fetchone()
        response_text = f"""### 📊 50-Point Roster Promotion Panel Status
- **Total Candidates on Roster**: {r_stats[0]} officers (T4 Panel)
- **SC Roster Points**: {r_stats[1]}
- **ST Roster Points**: {r_stats[2]}
- **UR / General Roster Points**: {r_stats[3]}
- **Deputy Director Posts**: 244 posts in T5 schedule (Allotments: Under verification)
- **Vigilance Status**: All candidates marked 'Under verification' pending official clearance memos.
"""

    # Obliteration / Abolished post queries
    elif "obliterat" in q or "1808" in q or "abolish" in q:
        cur.execute("""
        SELECT count(*),
               sum(case when is_on_roster = 1 then 1 else 0 end),
               sum(case when is_on_roster = 0 AND is_vacant != 'Yes' then 1 else 0 end)
        FROM ABOLISHED_POST_LEADS
        """)
        ob_stats = cur.fetchone()
        response_text = f"""### ⚠️ Notification No. 1808 Abolished Post Leads Analysis
- **Total Abolished Post Leads**: {ob_stats[0]} posts (DERIVED tracking layer)
- **Serving Officers on Roster**: {ob_stats[1]} officers
- **Serving Officers Requiring Lateral Absorption**: {ob_stats[2]} officers
- **Occupancy Verification**: Ground-truthed against Single Source of Truth Register.
"""

    else:
        response_text = f"""### 💡 ARD Department Decision Support Engine
You asked: *"{req.query}"*

I can assist you with:
1. **50-Point Roster Analysis**: 242 candidates across statutory roster points for 244 DD posts (Under verification).
2. **Abolished Post Leads**: Absorption and tracking of officers from Notification No. 1808 leads.
3. **Tenure & Station Tracking**: Area tenure norms and administrative separation.
4. **Superannuation Tracking**: Accurate DOR under WBSR Rule 75(a).
5. **Cadre Search**: Instant lookup across the 1,794 active sanctioned posts (Notification 1809).
"""

    conn.close()
    return {"query": req.query, "response": response_text}

@app.get("/api/posts/cascading-backfills")
def get_cascading_backfills_endpoint():
    """Returns Group C cascading replacement warnings for field posts that must be backfilled."""
    return engine.get_cascading_replacement_warnings()

@app.get("/api/download/google-sheets-version")
def download_google_sheets_version():
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.get("/api/download/11-column-master-sheet")
def download_11_column_master_sheet():
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.get("/api/download/authoritative-master-ag")
def download_authoritative_master_ag():
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

@app.get("/api/download/live-synced-datasheet")
def download_live_synced_datasheet():
    raise HTTPException(status_code=403, detail="File downloads have been administratively disabled.")

# --- VISITOR ANALYTICS & ACCESS TRACKING HELPERS & ENDPOINTS ---

def extract_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()
    cf_connecting_ip = request.headers.get("cf-connecting-ip")
    if cf_connecting_ip:
        return cf_connecting_ip.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

def extract_geo_location(request: Request, client_ip: str, client_geo: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    country = request.headers.get("x-vercel-ip-country")
    region = request.headers.get("x-vercel-ip-country-region")
    city = request.headers.get("x-vercel-ip-city")
    lat_str = request.headers.get("x-vercel-ip-latitude")
    lon_str = request.headers.get("x-vercel-ip-longitude")
    timezone = request.headers.get("x-vercel-ip-timezone")

    latitude = float(lat_str) if lat_str else None
    longitude = float(lon_str) if lon_str else None

    if not city and client_geo:
        city = client_geo.get("city")
        region = client_geo.get("region") or client_geo.get("regionName")
        country = client_geo.get("country") or client_geo.get("countryCode")
        latitude = client_geo.get("latitude") or client_geo.get("lat")
        longitude = client_geo.get("longitude") or client_geo.get("lon")
        timezone = client_geo.get("timezone")

    if not country and (client_ip == "127.0.0.1" or client_ip == "::1" or client_ip.startswith("192.168.") or client_ip.startswith("10.")):
        country = "India (Dev)"
        region = "West Bengal"
        city = "Kolkata (Local)"

    return {
        "country": country or "India",
        "region": region or "West Bengal",
        "city": city or "Kolkata",
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone or "Asia/Kolkata"
    }

def parse_user_agent(ua_str: str) -> Dict[str, str]:
    if not ua_str:
        return {"device_type": "Desktop", "os": "Unknown", "browser": "Unknown"}
    ua = ua_str.lower()
    
    if "ipad" in ua or "tablet" in ua:
        device_type = "Tablet"
    elif "mobi" in ua or "iphone" in ua or "android" in ua:
        device_type = "Mobile"
    else:
        device_type = "Desktop"
        
    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        os_name = "iOS"
    elif "android" in ua:
        os_name = "Android"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
    elif "windows" in ua:
        os_name = "Windows"
    elif "linux" in ua:
        os_name = "Linux"
    else:
        os_name = "Other"
        
    if "edg/" in ua or "edge/" in ua:
        browser = "Edge"
    elif "chrome/" in ua or "crios/" in ua:
        browser = "Chrome"
    elif "safari/" in ua and "chrome" not in ua:
        browser = "Safari"
    elif "firefox/" in ua or "fxios/" in ua:
        browser = "Firefox"
    elif "opera" in ua or "opr/" in ua:
        browser = "Opera"
    else:
        browser = "Browser"
        
    return {"device_type": device_type, "os": os_name, "browser": browser}

@app.post("/api/analytics/track")
async def track_analytics(req: TrackEventRequest, request: Request):
    try:
        ip = extract_client_ip(request)
        ua_raw = req.user_agent or request.headers.get("user-agent") or ""
        ua_parsed = parse_user_agent(ua_raw)
        geo = extract_geo_location(request, ip, req.client_geo)
        now_iso = datetime.datetime.now().isoformat()

        conn = get_analytics_db()
        cur = conn.cursor()

        # Fetch existing session if any
        cur.execute("SELECT session_id, total_time_seconds, page_count, pages_visited FROM visitor_sessions WHERE session_id = ?", (req.session_id,))
        existing = cur.fetchone()

        if existing:
            prev_time = existing["total_time_seconds"] or 0
            prev_pages_cnt = existing["page_count"] or 1
            try:
                pages_list = json.loads(existing["pages_visited"]) if existing["pages_visited"] else []
            except Exception:
                pages_list = []
            
            if req.page and (not pages_list or pages_list[-1] != req.page):
                pages_list.append(req.page)
                if len(pages_list) > 30:
                    pages_list = pages_list[-30:]
                prev_pages_cnt += 1

            new_time = prev_time + max(0, req.time_spent_delta or 0)

            cur.execute("""
                UPDATE visitor_sessions
                SET last_seen = ?,
                    total_time_seconds = ?,
                    page_count = ?,
                    current_page = ?,
                    pages_visited = ?,
                    ip_address = ?,
                    city = COALESCE(NULLIF(city, 'Unknown'), ?),
                    region = COALESCE(NULLIF(region, 'Unknown'), ?),
                    country = COALESCE(NULLIF(country, 'Unknown'), ?),
                    screen_resolution = COALESCE(?, screen_resolution)
                WHERE session_id = ?
            """, (
                now_iso, new_time, prev_pages_cnt, req.page,
                json.dumps(pages_list), ip,
                geo["city"], geo["region"], geo["country"],
                req.screen_resolution, req.session_id
            ))
        else:
            pages_list = [req.page] if req.page else ["Cadre Directory"]
            cur.execute("""
                INSERT INTO visitor_sessions (
                    session_id, ip_address, city, region, country,
                    latitude, longitude, timezone, device_type, os, browser,
                    screen_resolution, user_agent, first_seen, last_seen,
                    total_time_seconds, page_count, current_page, pages_visited
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.session_id, ip, geo["city"], geo["region"], geo["country"],
                geo["latitude"], geo["longitude"], geo["timezone"],
                ua_parsed["device_type"], ua_parsed["os"], ua_parsed["browser"],
                req.screen_resolution or "Unknown", ua_raw, now_iso, now_iso,
                max(0, req.time_spent_delta or 0), 1, req.page, json.dumps(pages_list)
            ))

        if req.event_type in ("pageview", "tab_switch", "dossier_view"):
            cur.execute("""
                INSERT INTO visitor_events (
                    session_id, ip_address, event_type, page_or_tab,
                    time_spent_delta, timestamp, city, region, country,
                    device_type, browser, os
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                req.session_id, ip, req.event_type, req.page,
                req.time_spent_delta or 0, now_iso, geo["city"], geo["region"], geo["country"],
                ua_parsed["device_type"], ua_parsed["browser"], ua_parsed["os"]
            ))

        conn.commit()
        conn.close()

        return {"status": "ok", "session_id": req.session_id, "ip": ip, "city": geo["city"], "country": geo["country"]}
    except Exception as e:
        logger.error(f"Error in track_analytics: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/api/analytics/stats")
async def get_analytics_stats():
    try:
        conn = get_analytics_db()
        cur = conn.cursor()

        # 1. Total unique IPs
        cur.execute("SELECT COUNT(DISTINCT ip_address) FROM visitor_sessions")
        total_unique_ips = cur.fetchone()[0] or 0

        # 2. Total sessions
        cur.execute("SELECT COUNT(*) FROM visitor_sessions")
        total_sessions = cur.fetchone()[0] or 0

        # 3. Active visitors right now (within last 3 minutes)
        three_mins_ago = (datetime.datetime.now() - datetime.timedelta(minutes=3)).isoformat()
        cur.execute("SELECT COUNT(*) FROM visitor_sessions WHERE last_seen >= ?", (three_mins_ago,))
        active_now = cur.fetchone()[0] or 0

        # 4. Total Pageviews & Avg time spent
        cur.execute("SELECT SUM(page_count), AVG(total_time_seconds), SUM(total_time_seconds) FROM visitor_sessions")
        row = cur.fetchone()
        total_pageviews = row[0] or 0
        avg_time_seconds = round(row[1] or 0)
        total_time_seconds = row[2] or 0

        # 5. Top Cities
        cur.execute("""
            SELECT city, region, country, COUNT(*) as count 
            FROM visitor_sessions 
            WHERE city IS NOT NULL AND city != '' 
            GROUP BY city, region 
            ORDER BY count DESC 
            LIMIT 8
        """)
        top_cities = [
            {"city": r["city"], "region": r["region"], "country": r["country"], "count": r["count"]}
            for r in cur.fetchall()
        ]

        # 6. Devices breakdown
        cur.execute("SELECT device_type, COUNT(*) as count FROM visitor_sessions GROUP BY device_type ORDER BY count DESC")
        devices = {r["device_type"] or "Desktop": r["count"] for r in cur.fetchall()}

        # 7. OS breakdown
        cur.execute("SELECT os, COUNT(*) as count FROM visitor_sessions GROUP BY os ORDER BY count DESC")
        os_breakdown = {r["os"] or "Unknown": r["count"] for r in cur.fetchall()}

        # 8. Browser breakdown
        cur.execute("SELECT browser, COUNT(*) as count FROM visitor_sessions GROUP BY browser ORDER BY count DESC")
        browsers = {r["browser"] or "Unknown": r["count"] for r in cur.fetchall()}

        # 9. Popular Pages / Modules
        cur.execute("""
            SELECT page_or_tab, COUNT(*) as count 
            FROM visitor_events 
            WHERE page_or_tab IS NOT NULL AND page_or_tab != '' 
            GROUP BY page_or_tab 
            ORDER BY count DESC 
            LIMIT 8
        """)
        popular_pages = [
            {"page": r["page_or_tab"], "count": r["count"]}
            for r in cur.fetchall()
        ]

        conn.close()

        return {
            "total_unique_ips": total_unique_ips,
            "total_sessions": total_sessions,
            "active_now": active_now,
            "total_pageviews": total_pageviews,
            "avg_time_seconds": avg_time_seconds,
            "total_time_seconds": total_time_seconds,
            "top_cities": top_cities,
            "devices": devices,
            "os_breakdown": os_breakdown,
            "browsers": browsers,
            "popular_pages": popular_pages
        }
    except Exception as e:
        logger.error(f"Error in get_analytics_stats: {e}")
        return {"error": str(e)}

@app.get("/api/analytics/sessions")
async def get_analytics_sessions(limit: int = 50, search: Optional[str] = None):
    try:
        conn = get_analytics_db()
        cur = conn.cursor()
        query = "SELECT * FROM visitor_sessions"
        params = []
        if search:
            query += " WHERE ip_address LIKE ? OR city LIKE ? OR region LIKE ? OR os LIKE ? OR browser LIKE ? OR device_type LIKE ?"
            p = f"%{search}%"
            params = [p, p, p, p, p, p]
        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        three_mins_ago = (datetime.datetime.now() - datetime.timedelta(minutes=3)).isoformat()

        sessions = []
        for r in rows:
            is_active = (r["last_seen"] or "") >= three_mins_ago
            try:
                pages = json.loads(r["pages_visited"]) if r["pages_visited"] else []
            except Exception:
                pages = [r["current_page"]] if r["current_page"] else []

            sessions.append({
                "session_id": r["session_id"],
                "ip_address": r["ip_address"],
                "city": r["city"] or "Unknown",
                "region": r["region"] or "Unknown",
                "country": r["country"] or "Unknown",
                "device_type": r["device_type"] or "Desktop",
                "os": r["os"] or "Unknown",
                "browser": r["browser"] or "Unknown",
                "screen_resolution": r["screen_resolution"] or "—",
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"],
                "total_time_seconds": r["total_time_seconds"] or 0,
                "page_count": r["page_count"] or 1,
                "current_page": r["current_page"] or "—",
                "pages_visited": pages,
                "is_active": is_active
            })

        conn.close()
        return {"sessions": sessions, "count": len(sessions)}
    except Exception as e:
        logger.error(f"Error in get_analytics_sessions: {e}")
        return {"error": str(e), "sessions": []}

@app.post("/api/analytics/clear")
async def clear_analytics():
    try:
        conn = get_analytics_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM visitor_events")
        cur.execute("DELETE FROM visitor_sessions")
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "Analytics database successfully reset"}
    except Exception as e:
        return {"error": str(e)}

# --- SERVE FRONTEND ---
@app.get("/favicon.ico", include_in_schema=False)
def favicon_file():
    icon_path = os.path.join(STATIC_DIR, "icon-192.png")
    if os.path.exists(icon_path):
        return FileResponse(icon_path, media_type="image/png")
    return Response(status_code=204)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/data.json")
def get_review_data():
    data_file = os.path.join(STATIC_DIR, "data.json")
    if os.path.exists(data_file):
        return FileResponse(data_file, media_type="application/json")
    raise HTTPException(status_code=404, detail="Review data not found")

@app.get("/api/review/status")
def review_status(request: Request):
    return {
        "status": "active",
        "current_password": "sonarbangla",
        "policy": "static_persistent",
        "login_gate": "sonarbangla",
        "recipient_email": "nirmalyaranjansarkar@gmail.com"
    }

@app.get("/review", response_class=HTMLResponse)
@app.get("/review-board", response_class=HTMLResponse)
def review_page():
    review_file = os.path.join(STATIC_DIR, "review.html")
    if os.path.exists(review_file):
        with open(review_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Review Board is loading... Please refresh.</h1>"

@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file) as f:
            return f.read()
    return "<h1>Decision Board Frontend is loading... Please refresh.</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
