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
import json
import sqlite3
import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import Request
import httpx
from posting_engine import PostingEngine
from backup_manager import BackupManager
from order_generator import generate_excel_order, generate_docx_order, generate_html_order

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
    if not os.path.exists(tmp_db) and os.path.exists(seed_db):
        shutil.copy2(seed_db, tmp_db)
    DB_PATH = tmp_db
    STATIC_DIR = os.path.join(BASE_DIR, "static")
else:
    DB_PATH = os.environ.get("DB_PATH") or os.path.join(BASE_DIR, "ard_master_truth.db")
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    os.makedirs(STATIC_DIR, exist_ok=True)

engine = PostingEngine(DB_PATH)
backup_mgr = BackupManager(DB_PATH)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- DATA MODELS ---

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

# --- API ENDPOINTS ---

@app.get("/api/overview")
def get_overview():
    conn = get_db()
    cur = conn.cursor()

    # Total active sanctioned posts (strictly 1,794 under Notification 1809)
    cur.execute("SELECT count(*) FROM cadre_1794_posts")
    total_posts = cur.fetchone()[0]

    # Active Occupants in 1,794 Cadre
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE occupancy_status = 'Occupied'")
    active_officers = cur.fetchone()[0]

    # Clear Vacancies in 1,794 Cadre
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE occupancy_status = 'Vacant'")
    total_vacancies = cur.fetchone()[0]

    # Over tenure in 1,794 Cadre
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE tenure_over_flag = 'Yes'")
    over_tenure_count = cur.fetchone()[0]

    # Obliterated posts under Notification 1808 (106 posts, 84 incumbents)
    cur.execute("SELECT count(*) FROM obliterated_posts_1808")
    obliterated_posts = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM obliterated_posts_1808 WHERE is_vacant != 'Yes'")
    obliterated_officers = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM obliterated_posts_1808 WHERE rehabilitation_status = 'Rehabilitated'")
    obliterated_rehabilitated = cur.fetchone()[0]

    # Available DD posts (242 available, 2 vigilance holds out of 244)
    cur.execute("SELECT count(*) FROM available_dd_posts WHERE is_blocked_vigilance = 0 AND allotment_status = 'Available'")
    vacant_dd = cur.fetchone()[0]

    # Vacant AD posts in 1,794 cadre
    cur.execute("SELECT count(*) FROM cadre_1794_posts WHERE designation LIKE '%Assistant Director%' AND occupancy_status = 'Vacant'")
    vacant_ad = cur.fetchone()[0]

    # Roster candidates
    cur.execute("SELECT count(*) FROM roster_50_point_candidates")
    roster_candidates = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM roster_50_point_candidates WHERE allotment_status = 'Allotted'")
    roster_allotted = cur.fetchone()[0]

    conn.close()

    return {
        "total_posts": total_posts,
        "active_officers": active_officers,
        "total_vacancies": total_vacancies,
        "over_tenure_count": over_tenure_count,
        "obliterated_posts": obliterated_posts,
        "obliterated_officers": obliterated_officers,
        "obliterated_rehabilitated": obliterated_rehabilitated,
        "vacant_dd": vacant_dd,
        "vacant_ad": vacant_ad,
        "roster_candidates": roster_candidates,
        "roster_allotted": roster_allotted
    }

@app.get("/api/cadre")
def get_cadre(
    search: Optional[str] = None,
    district: Optional[str] = None,
    designation: Optional[str] = None,
    status: Optional[str] = None, # 'vacant', 'occupied'
    tenure_over: Optional[str] = None, # 'Yes', 'No'
    avd_member: Optional[str] = None,
    limit: int = 200,
    offset: int = 0
):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM cadre_1794_posts WHERE 1=1"
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
        query += " AND occupancy_status = 'Vacant'"
    elif status == "occupied":
        query += " AND occupancy_status = 'Occupied'"

    if tenure_over and tenure_over != "ALL":
        query += " AND tenure_over_flag = ?"
        params.append(tenure_over)

    if avd_member and avd_member != "ALL":
        query += " AND avd_member = ?"
        params.append(avd_member)

    count_query = query.replace("SELECT *", "SELECT count(*)")
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

@app.get("/api/roster")
def get_roster_candidates(
    category: Optional[str] = None,
    allotment_status: Optional[str] = None,
    search: Optional[str] = None
):
    conn = get_db()
    cur = conn.cursor()

    query = """
    SELECT r.*, 
           COALESCE(e.attention_flag, 0) as attention_flag, 
           e.attention_reason, 
           COALESCE(e.needs_backfill, 0) as needs_backfill, 
           e.decision_note,
           e.mobile, e.email, e.current_address
    FROM roster_50_point_candidates r
    LEFT JOIN officer_extended_dossier e ON r.hrms_id = e.hrms_id
    WHERE 1=1
    """
    params = []

    if category and category != "ALL":
        query += " AND r.caste = ?"
        params.append(category)

    if allotment_status and allotment_status != "ALL":
        query += " AND r.allotment_status = ?"
        params.append(allotment_status)

    if search:
        s = f"%{search.strip()}%"
        query += " AND (r.officer_name LIKE ? OR r.hrms_id LIKE ? OR r.present_posting LIKE ? OR r.present_block LIKE ? OR r.present_district LIKE ?)"
        params.extend([s, s, s, s, s])

    query += " ORDER BY r.sl_no"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {"count": len(rows), "data": rows}

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
def get_obliterated_officers(status: Optional[str] = None, search: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM obliterated_posts_1808 WHERE 1=1"
    params = []

    if status and status != "ALL":
        query += " AND rehabilitation_status = ?"
        params.append(status)

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
    """Exports official Excel order with strict required 6 columns."""
    file_path = generate_excel_order(session_id)
    return FileResponse(file_path, filename=os.path.basename(file_path), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/api/simulation/export-docx")
def export_simulation_docx(session_id: str = "CURRENT_SESSION"):
    """Exports official Secretariat Government Notification in Word .docx format (Memo 391 standard)."""
    file_path = generate_docx_order(session_id)
    return FileResponse(file_path, filename=os.path.basename(file_path), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

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
- Dr. Nirmalya Ranjan Sarkar (HRMS 2014000243) is on the obliterated post of Asstt. Director ARD(SA) Hooghly (Sl 48 of Memo 1808), joined 2024-12-23 via Order 4246. Directorate HQ Post 54/445 is a clear vacancy.
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

    # Check for Nirmalya Ranjan Sarkar query
    if ("nirmalya" in q and "sarkar" in q) or "2014000243" in q or "nirmalya" in q:
        cur.execute("SELECT * FROM obliterated_posts_1808 WHERE hrms_id = '2014000243' OR (officer_name LIKE '%Nirmalya%' AND officer_name LIKE '%Sarkar%')")
        row = cur.fetchone()
        if row:
            r = dict(row)
            response_text = f"""### 👤 Officer Truth Record: Dr. Nirmalya Ranjan Sarkar
- **HRMS ID**: `{r['hrms_id']}`
- **Designation / Obliterated Post**: **{r['post_name']}**
- **Establishment**: {r['establishment']}
- **District / Block**: {r['district']} | {r['block']}
- **Statutory Status**: **OBLITERATED** under **Notification No. 1808-AR&AH/3A-08/23 dt. 18.06.2025** (Sl. No. {r['oblit_sl']}).
- **Administrative Position**: Displaced active serving officer awaiting rehabilitation into active cadre.
- **Rehabilitation Status**: `{r['rehabilitation_status']}` (Substantive Post: {r['substantive_post_name'] or 'Pending'}, SU Post: {r['su_post_name'] or 'None'}).
- **Correction Note**: He does **not** occupy Post 54/445 at Directorate HQ Kolkata (that is a clear vacancy).
"""
        else:
            response_text = "Record for Dr. Nirmalya Ranjan Sarkar not located."

    # Check for retirement query
    elif "retire" in q or "superannuat" in q or "dor" in q:
        cur.execute("""
        SELECT incumbent_name, incumbent_hrms, designation, district, 
               incumbent_dor
        FROM cadre_1794_posts
        WHERE occupancy_status = 'Occupied' AND incumbent_dor <= '2027-06-30'
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
        WHERE occupancy_status = 'Vacant'
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
               sum(case when caste = 'SC' then 1 else 0 end),
               sum(case when caste = 'ST' then 1 else 0 end),
               sum(case when caste = 'Gen' or caste = 'GENERAL' then 1 else 0 end)
        FROM roster_50_point_candidates
        """)
        r_stats = cur.fetchone()
        response_text = f"""### 📊 50-Point Roster Promotion Panel Status
- **Total Candidates on Roster**: {r_stats[0]} officers
- **SC Candidates**: {r_stats[1]}
- **ST Candidates**: {r_stats[2]}
- **UR / General Candidates**: {r_stats[3]}
- **Available Deputy Director Vacancies**: 242 clear sanctioned posts (2 blocked on vigilance)
- **Obliteration Overlap**: 23 officers are on abolished posts AND on the roster. Promoting them cleanly extinguishes their abolished post with zero third-party displacement!
"""

    # Obliteration queries
    elif "obliterat" in q or "1808" in q or "abolish" in q:
        cur.execute("""
        SELECT count(*),
               sum(case when is_on_roster = 1 then 1 else 0 end),
               sum(case when is_on_roster = 0 AND is_vacant != 'Yes' then 1 else 0 end)
        FROM obliterated_posts_1808
        """)
        ob_stats = cur.fetchone()
        response_text = f"""### ⚠️ Notification No. 1808 Post Obliteration Analysis
- **Total Abolished Posts**: {ob_stats[0]} posts
- **Serving Officers on Roster**: {ob_stats[1]} officers (can be cleanly promoted into 242 DD vacancies)
- **Serving Officers Requiring Lateral Rehabilitation**: {ob_stats[2]} officers (absorbable into vacant Assistant Director cadre posts)
- **Cascading Collisions**: Zero forced displacements required if mapped to clear vacancies!
"""

    else:
        response_text = f"""### 💡 ARD Department Decision Support Engine
You asked: *"{req.query}"*

I can assist you with:
1. **50-Point Roster Analysis**: Roster points, caste category compliance, and candidate choices for 242 available DD posts.
2. **Obliteration Rehabilitation**: Absorption of 84 serving displaced officers from Memo 1808 into active cadre posts.
3. **Transfer Policy 2009 (Memo 291)**: Tenure compliance (4 yrs special areas / 5 yrs general), spouse co-location (Para 5), child board exams (Para 13).
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
    file_path = os.path.join(BASE_DIR, "WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Google Sheets version workbook not found.")
    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx"
    )

# --- SERVE FRONTEND ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
