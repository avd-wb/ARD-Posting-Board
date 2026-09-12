#!/usr/bin/env python3
"""
sync_sheet_remarks_daemon.py
Periodically checks Column M ('remarks') of the master Google Sheet:
https://docs.google.com/spreadsheets/d/17tv3exhMVzAfedLU7pS8ps1ZWEteMP1Z/edit?gid=1818729425#gid=1818729425

If any changes or new directives are detected in Column M:
1. Parses the directive (Stay, specific SU post, transfer target, Nil, etc.).
2. Applies the updates in `ard_master_truth.db`.
3. Updates Column 11 (Substantive), Column 12 (SU), Column 13 (remarks), and visual shading in the Google Sheet.
4. Uploads the updated sheet back to Google Drive overwriting the file in place.
5. Re-generates the master multi-tab workbook and official 4-column Word document.
6. Commits and pushes changes to git origin main to update the Vercel app and GitHub repository.
"""

import os
import sys
import time
import json
import sqlite3
import re
import subprocess
import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

WORKSPACE = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DRIVE_FOLDER_ID = "1BgJE4thWGsCLv4qFHqmWobW_met8UuEL"
REMOTE_FILENAME = "20260913_0012_WB_ARD_Comprehensive_Posting_and_Transfer_Master_Sheet_0.03MB_mb.xlsx"
LOCAL_EXCEL = os.path.join(WORKSPACE, REMOTE_FILENAME)
BASELINE_FILE = os.path.join(WORKSPACE, "remarks_baseline.json")
LOG_FILE = os.path.join(WORKSPACE, "sync_remarks.log")
DB_PATH = os.path.join(WORKSPACE, "ard_master_truth.db")

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(formatted + "\n")
    except Exception as e:
        print(f"Failed writing to log: {e}")

def run_cmd(cmd_list, timeout=120):
    res = subprocess.run(cmd_list, cwd=WORKSPACE, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0:
        log(f"Command failed: {' '.join(cmd_list)}\nSTDERR: {res.stderr}")
    return res

def download_remote_sheet():
    tmp_path = os.path.join(WORKSPACE, "temp_check_sheet.xlsx")
    cmd = [
        "rclone", "copyto",
        f"gdrive:{REMOTE_FILENAME}",
        tmp_path,
        "--drive-root-folder-id", DRIVE_FOLDER_ID
    ]
    res = run_cmd(cmd)
    if res.returncode == 0 and os.path.exists(tmp_path):
        return tmp_path
    return None

def upload_remote_sheet(file_path):
    cmd = [
        "rclone", "copyto",
        file_path,
        f"gdrive:{REMOTE_FILENAME}",
        "--drive-root-folder-id", DRIVE_FOLDER_ID
    ]
    res = run_cmd(cmd)
    return res.returncode == 0

def load_baseline():
    if os.path.exists(BASELINE_FILE):
        try:
            with open(BASELINE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_baseline(data):
    with open(BASELINE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def search_post_from_remark(remark, fallback_dist=""):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rem = remark.strip()

    # Check for DD post
    if re.search(r'\b(DD|Deputy Director)\b', rem, re.I):
        m_dist = re.search(r'\b(?:DD|Deputy Director)\s*(?:ARD)?\s*(?:at|in|to|of)?\s*([A-Za-z\s]+)', rem, re.I)
        target_dist = m_dist.group(1).strip() if m_dist else fallback_dist
        cur.execute("SELECT dd_sl, district, office, post_name FROM available_dd_posts WHERE district LIKE ?", (f"%{target_dist}%",))
        dd = cur.fetchone()
        if dd:
            conn.close()
            return "DD", f"Deputy Director, ARD, District Office, {dd['district']}"

    # Search in cadre_1794_posts
    words = [w for w in re.findall(r'[a-zA-Z0-9]+', rem) if len(w) > 2 and w.lower() not in ['the', 'and', 'for', 'set', 'level', 'post', 'order', 'please', 'transfer', 'service', 'utilized']]
    cur.execute("SELECT post_sl, designation, establishment, block, district FROM cadre_1794_posts")
    all_p = cur.fetchall()
    scored = []
    for p in all_p:
        p_txt = f"{p['designation']} {p['establishment']} {p['block']} {p['district']}".lower()
        score = 0
        for w in words:
            wl = w.lower()
            if p['block'] and wl in p['block'].lower():
                score += 3
            elif wl in p['designation'].lower():
                score += 2
            elif wl in p_txt:
                score += 1
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    conn.close()

    if scored:
        best = scored[0][1]
        desig = best["designation"]
        estab = best["establishment"]
        block = best["block"]
        dist = best["district"]
        is_block = any(k in desig.upper() for k in ["BLDO", "BLOCK LIVE", "ABAHC", "BAHC"])
        parts = [desig, estab]
        if is_block and block and str(block).strip().lower() not in ['none', 'null', 'nil', '', '-']:
            parts.append(block)
        parts.append(dist)
        clean_parts = []
        for pt in parts:
            if pt and (not clean_parts or pt.lower() != clean_parts[-1].lower()):
                clean_parts.append(pt)
        return "CADRE", ", ".join(clean_parts)

    return "RAW", rem

def clean_post_string(text):
    if not text or str(text).strip().lower() in ["nil", "none", "null", "-", ""]:
        return "Nil" if str(text).strip().lower() in ["nil", "none", "null", "-", ""] else ""
    t = str(text).strip()
    t = re.sub(r'(?i)(?:Assistant Director,?\s*ARD,?\s*)+', 'Assistant Director, ARD, ', t)
    t = re.sub(r'(?i)(?:Deputy Director,?\s*ARD,?\s*)+', 'Deputy Director, ARD, ', t)
    t = re.sub(r'(?i)(?:Veterinary Officer,?\s*)+', 'Veterinary Officer, ', t)
    parts = [p.strip() for p in t.split(',') if p.strip()]
    dedup = []
    for p in parts:
        if not dedup or p.lower() != dedup[-1].lower():
            dedup.append(p)
    return ', '.join(dedup)


def apply_parsed_directive(sl_242, sl_global, name, rem_text, cur_sub, cur_su, pres_post, pres_dist):
    """
    Returns (new_substantive, new_su, log_description)
    """
    rt = rem_text.strip()
    rt_lower = rt.lower()

    if not rt or rt_lower in ["none", "null", "-", "", "consequential transfer", "rehabilitated to active cadre", "rehabilitation", "service utilized (su)"]:
        return cur_sub, cur_su, "No change"

    # Case 1: Stay at present post
    if any(k in rt_lower for k in ["stay", "same post", "present post"]):
        # If SU is already set to something meaningful, preserve it
        new_su = cur_su if (cur_su and cur_su != "Nil") else pres_post
        new_sub = cur_sub
        if sl_242 and str(sl_242).strip().isdigit() and not cur_sub.startswith("Deputy Director"):
            new_sub = f"Deputy Director, ARD, District Office, {pres_dist}"
        return new_sub, new_su, f"Stay applied (SU: {new_su})"

    # Case 2: Nil SU or pure promotion without SU
    if rt_lower in ["nil", "no su", "without su"] or (
        "promoted to deputy director" in rt_lower and not any(k in rt_lower for k in ["su as", "su at", "[su]", "service utilized", "stay", "at bahc", "at sahc", "at bldo"])
    ):
        p_type, formatted = search_post_from_remark(rt, pres_dist)
        new_sub = formatted if p_type == "DD" else cur_sub
        return new_sub, "Nil", f"Promoted with SU: Nil ({new_sub})"

    # Case 3: Explicit SU directive (e.g. 'SU as ...', 'SU at ...', 'SU ...')
    if re.search(r'^(?:\[?SU\]?|service utilized)\s*(?:as|at|:)?\s*', rt, re.I):
        post_query = re.sub(r'^(?:\[?SU\]?|service utilized)\s*(?:as|at|:)?\s*', '', rt, flags=re.I).strip()
        p_type, formatted = search_post_from_remark(post_query, pres_dist)
        return cur_sub, formatted, f"SU assigned: {formatted}"

    # Case 4: General transfer directive (e.g. 'BLDO ...', 'VO ...', 'DD ...')
    p_type, formatted = search_post_from_remark(rt, pres_dist)
    is_promotee = sl_242 is not None and str(sl_242).strip().isdigit()
    if is_promotee: # Officer is a promotee (Pay Level 19)
        if p_type == "DD":
            # If user specified a DD substantive post without SU mentioned, default SU to Nil
            return formatted, (cur_su if cur_su and cur_su != "Nil" and "stay" in cur_su.lower() else "Nil"), f"Substantive DD updated: {formatted}"
        else:
            # Cadre post assigned as SU attachment while maintaining DD Level 19 at District HQ
            sub_hq = cur_sub if "Deputy Director" in cur_sub else f"Deputy Director, ARD, District Office, {pres_dist}"
            return sub_hq, formatted, f"Promotee SU assigned: {formatted}"
    else: # Lateral transfer or Obliterated post rehab
        if p_type == "CADRE" or any(k in rt_lower for k in ["transfer", "posted as", "posted to", "bldo", "bahc", "sahc", "director"]):
            return formatted, "Nil", f"Transfer post updated: {formatted}"
        else:
            return cur_sub, cur_su, "No change"

COLUMN_N_FILE = os.path.join(WORKSPACE, "column_n_comments.json")

def load_column_n_comments():
    if os.path.exists(COLUMN_N_FILE):
        try:
            with open(COLUMN_N_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_column_n_comments(data):
    try:
        with open(COLUMN_N_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"Error saving column N comments: {e}")

def check_and_sync():
    log("Starting check of Column N ('comments'), Column M ('remarks'), and manual cell edits from Google Sheet...")
    remote_tmp = download_remote_sheet()
    if not remote_tmp:
        log("ERROR: Could not download remote spreadsheet via rclone.")
        return

    baseline = load_baseline()
    col_n_map = load_column_n_comments()
    wb = openpyxl.load_workbook(remote_tmp)
    ws = wb.worksheets[0]

    # Check headers
    if ws.cell(row=1, column=13).value != "remarks":
        ws.cell(row=1, column=13, value="remarks")

    col_n_hdr = ws.cell(row=1, column=14).value
    if not col_n_hdr:
        ws.cell(row=1, column=14, value="Comments (Debi Da)")

    changes_detected = []
    updated_baseline = dict(baseline)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    for r in range(2, ws.max_row + 1):
        sl_global = ws.cell(row=r, column=1).value
        if not sl_global:
            continue
        sl_242 = ws.cell(row=r, column=2).value
        name = ws.cell(row=r, column=3).value
        desig = ws.cell(row=r, column=4).value
        dist = ws.cell(row=r, column=7).value
        pres_post = ws.cell(row=r, column=8).value
        cur_sub = str(ws.cell(row=r, column=11).value or "").strip()
        cur_su = str(ws.cell(row=r, column=12).value or "").strip()
        rem_val = ws.cell(row=r, column=13).value or ""
        rem_str = str(rem_val).strip()

        # Column N: Comments written by Debi Da (NEVER OVERWRITE OR CLEAR)
        col_n_val = ws.cell(row=r, column=14).value
        col_n_str = str(col_n_val).strip() if col_n_val is not None else ""

        prev_entry = baseline.get(str(sl_global), {})
        prev_rem = prev_entry.get("remark", "").strip()
        prev_sub = prev_entry.get("substantive", "").strip()
        prev_su = prev_entry.get("su", "").strip()
        prev_col_n = prev_entry.get("comment_n", "").strip()

        # Check if Debi Da commented in Column N, or edited cells manually, or edited Column M
        col_n_changed = (col_n_str and col_n_str != prev_col_n)
        sub_or_su_manually_edited = (cur_sub and prev_sub and cur_sub != prev_sub) or (cur_su and prev_su and cur_su != prev_su)
        remark_changed = (rem_str and rem_str != prev_rem)

        if col_n_changed or sub_or_su_manually_edited or remark_changed:
            if col_n_changed:
                log(f"Detected Debi Da's comment in Column N at Row {r} (Sl {sl_global}, {name}): '{col_n_str}' (Previous: '{prev_col_n}')")
                new_sub, new_su, action_desc = apply_parsed_directive(
                    sl_242=sl_242,
                    sl_global=sl_global,
                    name=name,
                    rem_text=col_n_str,
                    cur_sub=cur_sub,
                    cur_su=cur_su,
                    pres_post=pres_post,
                    pres_dist=dist
                )
            elif sub_or_su_manually_edited:
                log(f"Detected direct manual cell edit by Debi Da at Row {r} (Sl {sl_global}, {name}): Sub='{cur_sub}', SU='{cur_su}'")
                new_sub, new_su = clean_post_string(cur_sub), clean_post_string(cur_su)
                action_desc = "Manual cell edit preserved"
            else:
                log(f"Detected remark change at Row {r} (Sl {sl_global}, {name}): '{rem_str}' (Previous: '{prev_rem}')")
                new_sub, new_su, action_desc = apply_parsed_directive(
                    sl_242=sl_242,
                    sl_global=sl_global,
                    name=name,
                    rem_text=rem_str,
                    cur_sub=cur_sub,
                    cur_su=cur_su,
                    pres_post=pres_post,
                    pres_dist=dist
                )

            new_sub = clean_post_string(new_sub)
            new_su = clean_post_string(new_su)
            log(f"  -> Applied: Substantive='{new_sub}', SU='{new_su}' ({action_desc})")

            # Update worksheet cells (Column 11 Substantive, Column 12 SU)
            # CRITICAL: DO NOT TOUCH COLUMN 14 (Column N). It remains untouched and intact.
            ws.cell(row=r, column=11, value=new_sub)
            ws.cell(row=r, column=12, value=new_su)
            
            # Highlight manual row in white (Cols 1 to 13)
            manual_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            for c in range(1, 14):
                ws.cell(row=r, column=c).fill = manual_fill

            # Update DB
            is_promotee = sl_242 is not None and str(sl_242).strip().isdigit()
            if is_promotee:
                cur.execute("""
                    UPDATE roster_50_point_candidates
                    SET substantive_post_name = ?,
                        su_post_name = ?,
                        is_manual_recommendation = 1
                    WHERE sl_no = ?
                """, (new_sub, new_su if new_su != "Nil" else None, int(str(sl_242).strip())))
            else:
                # Check obliterated_posts_1808
                cur.execute("""
                    UPDATE obliterated_posts_1808
                    SET substantive_post_name = ?,
                        su_post_name = ?,
                        is_manual_recommendation = 1
                    WHERE officer_name LIKE ?
                """, (new_sub, new_su if new_su != "Nil" else None, f"%{name}%"))
                # Check executive_lateral_transfers
                cur.execute("""
                    UPDATE executive_lateral_transfers
                    SET transferred_post_name = ?,
                        is_manual_recommendation = 1
                    WHERE officer_name LIKE ?
                """, (new_sub, f"%{name}%"))

            changes_detected.append({
                "row": r,
                "sl": sl_global,
                "name": name,
                "col_n_comment": col_n_str,
                "old_remark": prev_rem,
                "new_remark": rem_str,
                "new_sub": new_sub,
                "new_su": new_su
            })

            updated_baseline[str(sl_global)] = {
                "row": r,
                "sl_242": sl_242,
                "name": name,
                "remark": rem_str,
                "substantive": new_sub,
                "su": new_su,
                "comment_n": col_n_str
            }
        else:
            if str(sl_global) in updated_baseline:
                updated_baseline[str(sl_global)]["comment_n"] = col_n_str

        if col_n_str:
            col_n_map[str(sl_global)] = col_n_str

    conn.commit()
    conn.close()

    save_column_n_comments(col_n_map)

    if changes_detected:
        log(f"Total changes detected and applied: {len(changes_detected)}")
        save_baseline(updated_baseline)

        # Trigger universal synchronization across all database tables, all tabs in all sheets, and web app
        from sync_orchestrator import run_full_sync
        run_full_sync()

        log(f"Successfully synchronized all {len(changes_detected)} changes across all tabs, all sheets, database, and web app.")
    else:
        log("No changes detected in Column N comments or Column M remarks. System is up to date.")

    # Clean up temp file
    if os.path.exists(remote_tmp):
        try:
            os.remove(remote_tmp)
        except Exception:
            pass

def main():
    if "--once" in sys.argv:
        check_and_sync()
        return

    log("Starting Remarks Sync Daemon (running every 30 minutes / 1800s)...")
    while True:
        try:
            check_and_sync()
        except Exception as e:
            log(f"Error during sync cycle: {e}")
        time.sleep(1800)

if __name__ == "__main__":
    main()
