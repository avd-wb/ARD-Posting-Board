#!/usr/bin/env python3
"""
update_data_json.py
Updates static/data.json with the latest 337 officers, exact comments from the LIVE sheet,
and refreshed post-move vacancy statuses across all 2,174 posts.
"""

import os
import json
import sqlite3
import openpyxl
import datetime
import collections

WORKSPACE = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
SHEET_PATH = os.path.join(WORKSPACE, "scratch/20260914_AVD_GSH_Review_Sheet_LIVE.xlsx")
SOURCE_JSON = "/Users/nirmalyaranjansarkar/Projects/ARD PROMOTION/04_LISTS_FROM_SOT/app_data.json"
TARGET_JSON = os.path.join(WORKSPACE, "static/data.json")
DB_PATH = os.path.join(WORKSPACE, "ard_master_truth.db")

def update():
    print("--- 1. Reading LIVE Sheet ---")
    wb = openpyxl.load_workbook(SHEET_PATH, data_only=True)
    ws = wb["REVIEW"]

    live_officers = {}
    for r in range(2, ws.max_row + 1):
        h = str(ws.cell(r, 4).value or "").strip()
        if h:
            raw_opts = str(ws.cell(r, 23).value or "").strip()
            # Split options
            opts = [x.strip() for x in raw_opts.split("\n") if x.strip()]
            if not opts:
                opts = ["ক) ঠিক আছে", "খ) আপত্তি আছে", "গ) অন্য প্রস্তাব", "ঘ) জানি না"]

            live_officers[h] = {
                "sl": ws.cell(r, 1).value,
                "name": str(ws.cell(r, 3).value or "").strip(),
                "hrms": h,
                "cat": str(ws.cell(r, 5).value or "").strip(),
                "desig": str(ws.cell(r, 6).value or "").strip(),
                "estab": str(ws.cell(r, 7).value or "").strip(),
                "block": str(ws.cell(r, 8).value or "").strip(),
                "dist": str(ws.cell(r, 9).value or "").strip(),
                "dor": str(ws.cell(r, 10).value or "").strip(),
                "left": str(ws.cell(r, 11).value or "").strip(),
                "doj": str(ws.cell(r, 12).value or "").strip(),
                "tenure": str(ws.cell(r, 13).value or "").strip(),
                "post_full": str(ws.cell(r, 14).value or "").strip(),
                "su_now": str(ws.cell(r, 15).value or "").strip(),
                "basis": str(ws.cell(r, 16).value or "").strip(),
                "sub": str(ws.cell(r, 17).value or "").strip(),
                "su": str(ws.cell(r, 18).value or "").strip(),
                "su_final": str(ws.cell(r, 19).value or "").strip(),
                "avd": str(ws.cell(r, 20).value or "").strip(),
                "flags": [x.strip("• ").strip() for x in str(ws.cell(r, 21).value or "").split("\n") if x.strip()],
                "q": str(ws.cell(r, 22).value or "").strip(),
                "opts": opts,
                "rec": str(ws.cell(r, 24).value or "").strip(),
                "comments": str(ws.cell(r, 25).value or "").strip(),
                "justification": str(ws.cell(r, 26).value or "").strip(),
                "check": str(ws.cell(r, 27).value or "").strip()
            }

    print(f"Loaded {len(live_officers)} officers from LIVE sheet.")

    print("--- 2. Reading Cadre Vacancy DB Data ---")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
    SELECT id, post_sl, district, block, establishment, designation, post_code, pay_level,
           occupancy_status, post_move_vacancy_status, vacated_by_hrms, vacated_by_name,
           movement_details, is_actionable_vacancy, is_baseline_vacant, is_newly_vacated, is_su_retained
    FROM cadre_1794_posts
    """)
    cadre_by_pid = {}
    for r in cur.fetchall():
        pid = f"P{r['id']:04d}"
        cadre_by_pid[pid] = dict(r)

    print(f"Loaded {len(cadre_by_pid)} cadre posts from DB.")

    print("--- 3. Updating JSON Structure ---")
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 3.1 Update officers
    updated_officers = 0
    for o in data["officers"]:
        h = o["hrms"]
        if h in live_officers:
            lo = live_officers[h]
            o["name"] = lo["name"]
            o["sub"] = lo["sub"]
            o["su"] = lo["su_final"]
            o["basis"] = lo["basis"]
            if lo["comments"] and lo["comments"] != "None":
                o["exec"] = lo["comments"]
                o["comments"] = lo["comments"]
            if lo["q"]:
                o["ai"]["q"] = lo["q"]
            if lo["opts"]:
                o["ai"]["opts"] = lo["opts"]
            if lo["rec"]:
                o["ai"]["rec"] = lo["rec"]
            if lo["flags"]:
                o["ai"]["flags"] = lo["flags"]
            if lo["justification"]:
                o["justification"] = lo["justification"]
            updated_officers += 1

    print(f"Updated {updated_officers} officer objects in data.json.")

    # 3.2 Update vacancies
    updated_vac = 0
    actionable_count = 0
    for v in data["vacancies"]:
        pid = v.get("pid")
        cp = cadre_by_pid.get(pid)
        if cp:
            v["post_move_status"] = cp["post_move_vacancy_status"]
            v["is_actionable"] = cp["is_actionable_vacancy"]
            v["is_actionable_vacancy"] = cp["is_actionable_vacancy"]
            v["is_baseline_vacant"] = cp["is_baseline_vacant"]
            v["is_newly_vacated"] = cp["is_newly_vacated"]
            v["is_su_retained"] = cp["is_su_retained"]
            v["vacated_by_name"] = cp["vacated_by_name"]
            v["vacated_by_hrms"] = cp["vacated_by_hrms"]
            v["movement_details"] = cp["movement_details"]

            if cp["is_actionable_vacancy"]:
                actionable_count += 1
            if cp["is_newly_vacated"]:
                v["status"] = "VACATED_BY_MOVE"
                v["vacant"] = "Yes"
                v["promo"] = f"Yes — vacated by {cp['vacated_by_name']} ({cp['movement_details']})"
            elif cp["is_su_retained"]:
                v["status"] = "FILLED_ON_SU"
                v["promo"] = f"No — {cp['movement_details']}"
            elif cp["is_baseline_vacant"]:
                v["status"] = "VACANT"
                v["vacant"] = "Yes"
            updated_vac += 1

    print(f"Updated {updated_vac} vacancies. Total actionable vacancies in list: {actionable_count}")

    # 3.3 Update DD Tally
    # Get sanctioned DD lines per district from T5_DD_POSTS_244
    cur.execute("SELECT DISTRICT_UNIT FROM T5_DD_POSTS_244")
    t5_lines = collections.Counter(r[0] for r in cur.fetchall())
    
    def nd(s):
        s = (s or "").lower().replace("coochbehar", "cooch behar").replace("pgs", "parganas")
        return " ".join(s.split())

    keys = {nd(k): k for k in t5_lines}
    paper_tally = collections.Counter()
    for lo in live_officers.values():
        if lo["basis"] == "Promotion":
            s = nd(lo["sub"])
            k = next((kk for kk in sorted(keys, key=len, reverse=True) if kk in s), None)
            if "directorate" in s or "dte" in s:
                k = "kolkata"
            if k:
                paper_tally[k] += 1

    dd_tally = []
    for k in sorted(keys):
        dd_tally.append({
            "dist": keys[k],
            "paper": paper_tally.get(k, 0),
            "lines": t5_lines[keys[k]]
        })
    data["dd"] = dd_tally

    # 3.4 Metadata
    now_str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    data["built"] = now_str
    data["src"] = "20260914_AVD_GSH_Review_Sheet_LIVE.xlsx"
    data["summary"] = {
        "total_officers": len(live_officers),
        "total_cadre_posts": len(cadre_by_pid),
        "baseline_vacancies": 253,
        "newly_vacated_posts": 100,
        "total_actionable_vacancies": 353,
        "substantively_vacant_held_on_su": 123,
        "dd_allotted": 242,
        "dd_available": 2
    }

    conn.close()

    with open(TARGET_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Saved refreshed static/data.json ({round(os.path.getsize(TARGET_JSON)/1024/1024, 2)} MB) successfully!")

if __name__ == "__main__":
    update()
