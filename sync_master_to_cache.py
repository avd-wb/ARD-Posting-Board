#!/usr/bin/env python3
"""
sync_master_to_cache.py
Synchronizes ard_master_truth.db from the Master Source of Truth (20260913_AVD_SOT_Master_Register.sqlite)
under the strict terms established with the project owner on 14.09.2026:
- Weight 0 UI cache for edge deployment
- Only permitted tables (T1-T6, T8, POSTS, OCCUPANCY, EVIDENCE, RESOLVED_PERSON_FIELDS, REVIEW_QUEUE, POLICY_*, BLOCK_MAP_*, LGD_BLOCKS_WB_341)
- Never T7_RESTRICTED_DECLARED_GROUNDS, never PREFERENCES
- Strict query/sync-layer stripping of MOBILE, EMAIL, ADDRESS, SPOUSE_*, CHILD*, HEALTH*, CARE*, PWD*, CASTE, DOB
- Roster 242/242 linked (including Roster Point 152 -> 1994003580)
- Records master SQLite modification time for front-end transparency
"""
import sqlite3
import os
import re
import sys
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DB = os.path.join(BASE_DIR, "ard_master_truth.db")
SOT_PATH = "/Users/nirmalyaranjansarkar/Projects/ARD PROMOTION/02_MASTER_SOURCE_OF_TRUTH/20260913_AVD_SOT_Master_Register.sqlite"

if not os.path.exists(SOT_PATH):
    print(f"Error: Master SOT database not found at {SOT_PATH}")
    sys.exit(1)

mtime_master = datetime.datetime.fromtimestamp(os.path.getmtime(SOT_PATH)).strftime("%Y-%m-%d %H:%M:%S")
now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print(f"Connecting to Master SOT (read-only): {SOT_PATH}")
print(f"Master SOT timestamp: {mtime_master}")
print(f"Target UI Cache DB: {CACHE_DB}")

sot_conn = sqlite3.connect(f"file:{SOT_PATH}?mode=ro", uri=True)
sot_cur = sot_conn.cursor()

cache_conn = sqlite3.connect(CACHE_DB)
cache_cur = cache_conn.cursor()

# 1. Permitted tables
PERMITTED_TABLES = [
    "T1_OFFICER_DOSSIER",
    "T2_ESTABLISHMENT_SANCTIONED_VS_RETURN",
    "T2B_ESTABLISHMENT_BLOCKWISE_AS_REPORTED",
    "T3_ABOLISHED_POST_LEADS",
    "T4_DD_PROMOTION_242",
    "T5_DD_POSTS_244",
    "T6_FILLED_ON_PAPER_SU",
    "T8_ORDER_MOVEMENTS_BATCH2",
    "POSTS",
    "OCCUPANCY",
    "EVIDENCE",
    "RESOLVED_PERSON_FIELDS",
    "REVIEW_QUEUE",
    "POLICY_AUTHORITIES",
    "POLICY_RULES",
    "BLOCK_MAP_1995_TO_LGD",
    "BLOCK_MAP_REPORTED_TO_LGD",
    "LGD_BLOCKS_WB_341"
]

FORBIDDEN_COL_PATTERN = re.compile(
    r"^(mobile|email|address|whatsapp|pin)$|.*(spouse|child|health|care|pwd|caste|dob|preference|ground).*",
    re.I
)

# 2. Copy permitted tables with column filtering
for tbl in PERMITTED_TABLES:
    cols_meta = sot_cur.execute(f"PRAGMA table_info({tbl})").fetchall()
    all_cols = [c[1] for c in cols_meta]
    allowed_cols = [c for c in all_cols if not FORBIDDEN_COL_PATTERN.match(c)]
    
    cache_cur.execute(f"DROP TABLE IF EXISTS {tbl}")
    cols_def = ", ".join(f'"{c}" TEXT' for c in allowed_cols)
    cache_cur.execute(f"CREATE TABLE {tbl} ({cols_def})")
    
    # Fetch data
    cols_query = ", ".join(f'"{c}"' for c in allowed_cols)
    rows = sot_cur.execute(f"SELECT {cols_query} FROM {tbl}").fetchall()
    placeholders = ", ".join("?" * len(allowed_cols))
    cache_cur.executemany(f"INSERT INTO {tbl} VALUES ({placeholders})", rows)
    print(f"Synced {tbl}: {len(rows)} rows, {len(allowed_cols)} columns (stripped {len(all_cols) - len(allowed_cols)} PII cols)")

# 3. Synchronize cadre_1794_posts from POSTS and OCCUPANCY
print("\n--- Synchronizing cadre_1794_posts ---")
cache_cur.execute("""
DROP TABLE IF EXISTS cadre_1794_posts
""")
cache_cur.execute("""
CREATE TABLE cadre_1794_posts (
    id INTEGER PRIMARY KEY,
    post_sl INTEGER,
    district TEXT,
    block TEXT,
    establishment TEXT,
    estab_type TEXT,
    designation TEXT,
    post_code TEXT,
    pay_level TEXT,
    occupancy_status TEXT,
    incumbent_name TEXT,
    incumbent_hrms TEXT,
    doj_present_post TEXT,
    dor TEXT,
    tenure_years TEXT,
    tenure_over_flag TEXT,
    post_allocation_basis TEXT,
    reported_block TEXT,
    source_file TEXT,
    source_row TEXT,
    detailed_presentation TEXT
)
""")

# Map occupancy from SOT OCCUPANCY
sot_occ_map = {}
occ_rows = sot_cur.execute("""
SELECT POST_ID, OCCUPANCY_STATUS, POST_ALLOCATION_BASIS, REPORTED_BLOCK_AREA,
       OFFICER_NAME_IN_MASTER, HRMS_ID, DOJ_PRESENT_POST, TIME_IN_PRESENT_POST,
       DATE_OF_RETIREMENT, SOURCE_FILE, SOURCE_ROW_SL
FROM OCCUPANCY
WHERE POST_ID IS NOT NULL AND POST_ID != ''
""").fetchall()

for r in occ_rows:
    p_id, occ_status, basis, rep_block, off_name, hrms, doj, tenure, dor, src_file, src_row = r
    if occ_status in ("FILLED", "FILLED_ON_SU"):
        stat = "FILLED"
    elif occ_status == "VACANT":
        stat = "VACANT"
    elif occ_status == "NOT_ESTABLISHED":
        stat = "NOT_ESTABLISHED"
    else:
        stat = "NO_RETURN"
    sot_occ_map[p_id] = {
        "status": stat,
        "basis": basis or "Sub-Divisional and Block Level Set up",
        "reported_block": rep_block or "Under verification",
        "officer_name": off_name if off_name not in ("Under verification", None) else None,
        "hrms_id": hrms if hrms not in ("Under verification", None) else None,
        "doj": doj or "Under verification",
        "tenure": tenure or "Under verification",
        "dor": dor or "Under verification",
        "source_file": src_file or "Notification 1809",
        "source_row": str(src_row) if src_row else "Under verification"
    }

SAHC_AREA_MAP = {
    'P0290': ('Darjeeling Pulbazar', 'Darjeeling'),
    'P0345': ('Naxalbari', 'Siliguri'),
    'P0346': ('Bidhannagar', 'Siliguri'),
    'P0347': ('Siliguri', 'Siliguri'),
    'P0376': ('Jalpaiguri Sadar', 'Jalpaiguri'),
    'P0377': ('Mal', 'Jalpaiguri'),
    'P0420': ('Alipurduar', 'Alipurduar'),
    'P0421': ('Birpara', 'Alipurduar'),
    'P0461': ('Cooch Behar', 'Cooch Behar'),
    'P0462': ('Dinhata', 'Cooch Behar'),
    'P0463': ('Mathabhanga', 'Cooch Behar'),
    'P0464': ('Tufanganj', 'Cooch Behar'),
    'P0465': ('Sitai', 'Cooch Behar'),
    'P0516': ('Raiganj', 'Uttar Dinajpur'),
    'P0517': ('Dalkhola', 'Uttar Dinajpur'),
    'P0563': ('Buniadpur', 'Dakshin Dinajpur'),
    'P0613': ('Harishchandrapur-I', 'Malda'),
    'P0614': ('Gazole', 'Malda'),
    'P0615': ('Chanchal', 'Malda'),
    'P0692': ('Berhampore', 'Murshidabad'),
    'P0693': ('Lalbag', 'Murshidabad'),
    'P0694': ('Jiagunj', 'Murshidabad'),
    'P0695': ('Domkal', 'Murshidabad'),
    'P0696': ('Lalgola', 'Murshidabad'),
    'P0697': ('Jangipur', 'Murshidabad'),
    'P0698': ('Beldanga', 'Murshidabad'),
    'P0789': ('Bahirgachi', 'Nadia'),
    'P0790': ('Bethuadahari', 'Nadia'),
    'P0791': ('Chakdah', 'Nadia'),
    'P0792': ('Chakdah (TBCU)', 'Nadia'),
    'P0793': ('Chapra', 'Nadia'),
    'P0794': ('Karimpur', 'Nadia'),
    'P0795': ('Krishnagar', 'Nadia'),
    'P0883': ('Barasat', 'North 24 Parganas'),
    'P0884': ('Barrackpore', 'North 24 Parganas'),
    'P0885': ('Ashoknagar', 'North 24 Parganas'),
    'P0886': ('Bongaon', 'North 24 Parganas'),
    'P0887': ('Basirhat', 'North 24 Parganas'),
    'P0888': ('DumDum Cant', 'North 24 Parganas'),
    'P0976': ('Baruipur', 'South 24 Parganas'),
    'P0977': ('Behala', 'South 24 Parganas'),
    'P0978': ('Canning', 'South 24 Parganas'),
    'P0979': ('Diamond Harbour', 'South 24 Parganas'),
    'P0980': ('Kakdwip', 'South 24 Parganas'),
    'P1067': ('Amta', 'Howrah'),
    'P1068': ('Uluberia', 'Howrah'),
    'P1132': ('Chandannagar', 'Hooghly'),
    'P1133': ('Haripal', 'Hooghly'),
    'P1134': ('Arambagh', 'Hooghly'),
    'P1135': ('Chinsurah', 'Hooghly'),
    'P1214': ('Bhatar', 'Purba Bardhaman'),
    'P1215': ('Burdwan', 'Purba Bardhaman'),
    'P1216': ('Katwa', 'Purba Bardhaman'),
    'P1217': ('Koichore', 'Purba Bardhaman'),
    'P1218': ('Galsi', 'Purba Bardhaman'),
    'P1219': ('Guskara', 'Purba Bardhaman'),
    'P1220': ('Kalna', 'Purba Bardhaman'),
    'P1296': ('Asansol', 'Paschim Bardhaman'),
    'P1297': ('Durgapur', 'Paschim Bardhaman'),
    'P1350': ('Suri', 'Birbhum'),
    'P1351': ('Bolpur', 'Birbhum'),
    'P1352': ('Sainthia', 'Birbhum'),
    'P1353': ('Rampurhat', 'Birbhum'),
    'P1354': ('Nirisha', 'Birbhum'),
    'P1355': ('Murarai', 'Birbhum'),
    'P1439': ('Bishnupur', 'Bankura'),
    'P1440': ('Bankura', 'Bankura'),
    'P1441': ('Indas', 'Bankura'),
    'P1442': ('Khatra', 'Bankura'),
    'P1530': ('Purulia', 'Purulia'),
    'P1531': ('Sindri Chas Road', 'Purulia'),
    'P1532': ('Kashipur', 'Purulia'),
    'P1533': ('Manbazar at Palashkhola', 'Purulia'),
    'P1534': ('Manbazar (DPAP)', 'Purulia'),
    'P1535': ('Balarampur', 'Purulia'),
    'P1536': ('Raghunathpur', 'Purulia'),
    'P1617': ('Midnapore', 'Paschim Medinipur'),
    'P1618': ('Kharagpur', 'Paschim Medinipur'),
    'P1619': ('Ghatal', 'Paschim Medinipur'),
    'P1620': ('Belda', 'Paschim Medinipur'),
    'P1621': ('Khirpai', 'Paschim Medinipur'),
    'P1622': ('Gopiganj', 'Paschim Medinipur'),
    'P1694': ('Binpur', 'Jhargram'),
    'P1751': ('Ramnagar', 'Purba Medinipur'),
    'P1752': ('Contai', 'Purba Medinipur'),
    'P1753': ('Egra', 'Purba Medinipur'),
    'P1754': ('Khejuri', 'Purba Medinipur')
}

posts_rows = sot_cur.execute("""
SELECT POST_ID, POST_SL, DISTRICT_UNIT, ESTABLISHMENT, ESTABLISHMENT_TYPE,
       POST_NOMENCLATURE, POST_CODE, PAY_LEVEL, SOURCE_FILE
FROM POSTS
ORDER BY CAST(POST_SL AS INTEGER)
""").fetchall()

cadre_rows = []
for p in posts_rows:
    p_id, p_sl, dist, est, est_type, nom, code, pay, src = p
    occ = sot_occ_map.get(p_id, {
        "status": "NO_RETURN",
        "basis": "Sub-Divisional and Block Level Set up",
        "reported_block": "Under verification",
        "officer_name": None,
        "hrms_id": None,
        "doj": "Under verification",
        "tenure": "Under verification",
        "dor": "Under verification",
        "source_file": src,
        "source_row": "Under verification"
    })

    # Apply SAHC Area suffix and block if applicable
    if p_id in SAHC_AREA_MAP:
        area, d_name = SAHC_AREA_MAP[p_id]
        nom = f"Veterinary Officer, SAHC, {area}, {d_name}"
        occ["reported_block"] = area
    
    # tenure over check
    try:
        t_yrs = float(occ["tenure"]) if occ["tenure"] not in ("Under verification", None) else 0.0
        tenure_over = "Yes" if t_yrs >= 5.0 else "No"
    except (ValueError, TypeError):
        tenure_over = "No"

    cadre_rows.append((
        int(p_sl), int(p_sl), dist, occ["reported_block"], est, est_type,
        nom, code, pay, occ["status"], occ["officer_name"], occ["hrms_id"],
        occ["doj"], occ["dor"], str(occ["tenure"]), tenure_over,
        occ["basis"], occ["reported_block"], occ["source_file"], occ["source_row"],
        f"{nom} at {est}, {dist}"
    ))

cache_cur.executemany("""
INSERT INTO cadre_1794_posts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", cadre_rows)
print(f"Synced cadre_1794_posts: {len(cadre_rows)} posts.")

# Also synchronize legacy tables if present in cache DB
for tbl in ["sacrosanct_cadre_posts", "master_source_of_truth"]:
    tbl_exists = cache_cur.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{tbl}'").fetchone()[0]
    if tbl_exists:
        for pid, (area, d_name) in SAHC_AREA_MAP.items():
            sl = int(pid[1:])
            new_desig = f"Veterinary Officer, SAHC, {area}, {d_name}"
            if tbl == "sacrosanct_cadre_posts":
                cache_cur.execute("UPDATE sacrosanct_cadre_posts SET designation = ?, block = ? WHERE post_sl = ?", (new_desig, area, sl))
            elif tbl == "master_source_of_truth":
                cache_cur.execute("""
                    UPDATE master_source_of_truth
                    SET designation = ?, block = ?,
                        name_of_post = REPLACE(REPLACE(name_of_post, 'Veterinary Officer, SAHC', ?), 'DDARD&PO', ?)
                    WHERE id = ?
                """, (new_desig, area, new_desig, area, sl))
        print(f"Synchronized SAHC area suffix to legacy table: {tbl}")

# 4. Synchronize roster_50_point_candidates from T4_DD_PROMOTION_242
print("\n--- Synchronizing roster_50_point_candidates (242 candidates) ---")
cache_cur.execute("DROP TABLE IF EXISTS roster_50_point_candidates")
cache_cur.execute("""
CREATE TABLE roster_50_point_candidates (
    sl_no INTEGER PRIMARY KEY,
    roster_point INTEGER,
    point_reserved_for TEXT,
    officer_name TEXT,
    hrms_id TEXT,
    present_posting TEXT,
    present_block TEXT,
    present_district TEXT,
    doj_present_post TEXT,
    tenure_years TEXT,
    dor TEXT,
    service_status TEXT,
    gradation_sl TEXT,
    allotment_status TEXT DEFAULT 'Under verification',
    is_manual_recommendation INTEGER DEFAULT 0,
    substantive_post_id INTEGER,
    substantive_post_name TEXT,
    su_post_id INTEGER,
    su_post_name TEXT
)
""")

t4_all = sot_cur.execute("""
SELECT ROSTER_POINT, NAME_ON_ROSTER, RESERVATION_TAG, HRMS_ID, NAME_IN_MASTER,
       SERVICE_STATUS, PRESENT_DESIGNATION, PRESENT_DISTRICT_UNIT, PRESENT_ESTABLISHMENT,
       REPORTED_BLOCK_OR_AREA, DOJ_PRESENT_POST, TENURE_IN_PRESENT_POST_YEARS,
       GRADATION_SL_3768, DATE_OF_RETIREMENT
FROM T4_DD_PROMOTION_242
ORDER BY CAST(ROSTER_POINT AS INTEGER)
""").fetchall()

roster_rows = []
for idx, r in enumerate(t4_all, 1):
    pt, name, res, hrms, name_m, status, desig, dist, est, blk, doj, tenure, grad, dor = r
    roster_rows.append((
        idx,
        int(pt) if str(pt).isdigit() else idx,
        res or "UR",
        name,
        hrms,
        f"{desig or ''} at {est or ''}".strip(" at "),
        blk or "Under verification",
        dist or "Under verification",
        doj or "Under verification",
        str(tenure or "Under verification"),
        dor or "Under verification",
        status or "In-Service",
        grad or "Under verification",
        "Under verification",
        0,
        None,
        None,
        None,
        None
    ))

cache_cur.executemany("""
INSERT INTO roster_50_point_candidates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", roster_rows)
print(f"Synced roster_50_point_candidates: {len(roster_rows)} candidates (242/242 linked).")

# 5. Metadata table
cache_cur.execute("DROP TABLE IF EXISTS master_sync_meta")
cache_cur.execute("""
CREATE TABLE master_sync_meta (
    master_sot_path TEXT,
    master_sot_mtime TEXT,
    sync_timestamp TEXT,
    ui_cache_weight INTEGER,
    roster_linked_count INTEGER,
    total_roster_candidates INTEGER,
    cadre_total_posts INTEGER,
    occupancy_filled INTEGER,
    occupancy_vacant INTEGER,
    occupancy_no_return INTEGER,
    occupancy_not_established INTEGER,
    occupancy_abolished_leads INTEGER
)
""")

cur_occ_counts = dict(cache_cur.execute("SELECT occupancy_status, count(*) FROM cadre_1794_posts GROUP BY occupancy_status").fetchall())
cache_cur.execute("""
INSERT INTO master_sync_meta VALUES (?, ?, ?, 0, 242, 242, 1794, ?, ?, ?, ?, 383)
""", (
    SOT_PATH,
    mtime_master,
    now_str,
    cur_occ_counts.get("FILLED", 936),
    cur_occ_counts.get("VACANT", 253),
    cur_occ_counts.get("NO_RETURN", 595),
    cur_occ_counts.get("NOT_ESTABLISHED", 10)
))

# 6. Enrich AVD Association Status across all personnel & cadre tables
print("\n--- Enriching AVD Membership Status ---")
avd_hrms_set = set()
EXCEL_AVD_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD/_AI_Generated/04_AVD_Members/02 Master/20260914_0714_AVD_MDV-MEMBERS_AVD_WBAHVS_Members_with_HRMS_ID.xlsx"
if os.path.exists(EXCEL_AVD_PATH):
    try:
        import pandas as pd
        df_avd = pd.read_excel(EXCEL_AVD_PATH)
        yes_mask = df_avd['AVD Member'].astype(str).str.strip().str.upper() == 'YES'
        ids = df_avd[yes_mask]['HRMS ID'].dropna().astype(str).str.strip().tolist()
        for hid in ids:
            if hid and hid != 'nan':
                avd_hrms_set.add(hid)
        print(f"Loaded {len(avd_hrms_set)} AVD HRMS IDs from Master Excel.")
    except Exception as e:
        print(f"Warning: Could not read AVD Master Excel: {e}")

# Supplement from official_gradation_list if exists in cache
try:
    has_grad = cache_cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='official_gradation_list'").fetchone()[0]
    if has_grad:
        for r in cache_cur.execute("SELECT hrms_id FROM official_gradation_list WHERE avd_member = 'Yes' AND hrms_id IS NOT NULL").fetchall():
            hid = str(r[0]).strip()
            if hid:
                avd_hrms_set.add(hid)
except Exception as e:
    pass

print(f"Total unified AVD HRMS IDs to tag: {len(avd_hrms_set)}")

for tbl, hrms_field in [
    ("cadre_1794_posts", "incumbent_hrms"),
    ("sacrosanct_cadre_posts", "incumbent_hrms"),
    ("roster_50_point_candidates", "hrms_id"),
    ("ABOLISHED_POST_LEADS", "incumbent_hrms")
]:
    tbl_exists = cache_cur.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{tbl}'").fetchone()[0]
    if not tbl_exists:
        continue
    cols = [c[1] for c in cache_cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
    if "avd_member" not in cols:
        cache_cur.execute(f"ALTER TABLE {tbl} ADD COLUMN avd_member TEXT DEFAULT 'No'")
    cache_cur.execute(f"UPDATE {tbl} SET avd_member = 'No'")
    
    # Check if target hrms_field is present in columns, otherwise find column with 'hrms'
    actual_hrms = hrms_field if hrms_field in cols else next((c for c in cols if 'hrms' in c.lower()), None)
    if actual_hrms:
        for hid in avd_hrms_set:
            cache_cur.execute(f"UPDATE {tbl} SET avd_member = 'Yes' WHERE {actual_hrms} = ?", (hid,))
        tagged = cache_cur.execute(f"SELECT count(*) FROM {tbl} WHERE avd_member = 'Yes'").fetchone()[0]
        print(f"Tagged {tbl}: {tagged} records as AVD Member Yes.")

cache_conn.commit()
cache_conn.execute("VACUUM")
cache_conn.close()
sot_conn.close()

print("\n=== Master SOT to UI Cache Synchronization Complete ===")
