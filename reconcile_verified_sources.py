import os
import sqlite3
import pandas as pd
import openpyxl
import xlrd
import datetime as dt
from datetime import datetime
import re
from typing import Dict, Any, List

VERIFIED_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources "
DAHVS_DIR = os.path.join(VERIFIED_DIR, "From AD HQ DAHVS")
DEST_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DB_PATH = os.path.join(DEST_DIR, "ard_master_truth.db")

def clean_hrms(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    m = re.search(r'\b(19\d{8}|20\d{8})\b', s)
    if m:
        return m.group(1)
    if s in ["None", "nan", "—", "-"]:
        return ""
    return s

def clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s in ["None", "nan"]:
        return ""
    return s

def parse_date(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (dt.datetime, dt.date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip().split()[0]
    for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return s

def run_comprehensive_check():
    print("Running comprehensive cross-check between 01_Verified_Sources and Master Data...")
    
    conn = sqlite3.connect(DB_PATH)
    master_df = pd.read_sql_query("SELECT * FROM master_source_of_truth", conn)
    conn.close()

    master_by_hrms = {}
    for _, r in master_df.iterrows():
        hid = clean_hrms(r['present_officer_hrms_id'])
        if hid:
            master_by_hrms[hid] = r

    # 1. Parse DAHVS District Returns for Incumbents and Joining Dates
    district_officers = {} # hrms -> list of records from district returns
    
    files = [f for f in os.listdir(DAHVS_DIR) if not f.startswith('~$') and not f.startswith('.')]
    for fname in files:
        fpath = os.path.join(DAHVS_DIR, fname)
        ext = os.path.splitext(fname)[1].lower()
        rows_data = []
        if ext == ".xlsx":
            try:
                wb = openpyxl.load_workbook(fpath, data_only=True)
                for sname in wb.sheetnames:
                    ws = wb[sname]
                    for r in ws.iter_rows(values_only=True):
                        rows_data.append(r)
                wb.close()
            except Exception:
                continue
        elif ext == ".xls":
            try:
                wb = xlrd.open_workbook(fpath, on_demand=True)
                for sname in wb.sheet_names():
                    sh = wb.sheet_by_name(sname)
                    for ridx in range(sh.nrows):
                        rows_data.append([sh.cell_value(ridx, c) for c in range(sh.ncols)])
            except Exception:
                continue

        # Process rows
        for r in rows_data:
            # scan cells for HRMS ID
            row_hrms = ""
            for cell in r:
                hid = clean_hrms(cell)
                if hid:
                    row_hrms = hid
                    break
            if row_hrms:
                if row_hrms not in district_officers:
                    district_officers[row_hrms] = []
                district_officers[row_hrms].append((fname, r))

    print(f"Total distinct HRMS IDs located in DAHVS district returns: {len(district_officers)}")

    # Compare district returns with Master table
    all_discrepancies = []
    
    # Check 1: Superannuation 1st of month rule from HRMS dump
    hrms_tsv = os.path.join(VERIFIED_DIR, "Source from HRMS/2026090_HRMS_ARD_20260908.tsv")
    if os.path.exists(hrms_tsv):
        df_h = pd.read_csv(hrms_tsv, sep='\t')
        for _, hr in df_h.iterrows():
            hid = clean_hrms(hr['hrms'])
            h_end = clean_str(hr['service_end_date'])
            h_status = clean_str(hr['status'])
            h_name = clean_str(hr['name'])

            if hid in master_by_hrms:
                m_rec = master_by_hrms[hid]
                m_dor = m_rec['present_officer_dor']
                m_dob = m_rec['present_officer_dob']

                if h_end and m_dor != "—":
                    try:
                        hend_date = datetime.strptime(h_end, "%d/%m/%Y").strftime("%Y-%m-%d")
                        if hend_date != m_dor:
                            # Check if DOB was on 1st of month
                            is_first_day = (m_dob.endswith("-01")) if m_dob else False
                            rule_reason = "DOB on 1st of month: WBSR Rule 75(a) retires last day of preceding month" if is_first_day else "Discrepancy between HRMS database and formula calculation"
                            all_discrepancies.append({
                                "Conflict_ID": f"VERIF_{len(all_discrepancies)+1:04d}",
                                "Source_File": "Source from HRMS/2026090_HRMS_ARD_20260908.tsv",
                                "Officer_Name": m_rec['present_officer_name'],
                                "HRMS_ID": hid,
                                "Field_Name": "SUPERANNUATION_DOR",
                                "Master_Value": m_dor,
                                "Verified_Source_Value": hend_date,
                                "Discrepancy_Type": "1st_OF_MONTH_RULE" if is_first_day else "DOR_MISMATCH",
                                "Resolution_Rationale": f"Formula DOB+60 produced {m_dor}; Authority 2 (Official HRMS Portal) records {hend_date}. ({rule_reason})."
                            })
                    except Exception:
                        pass

    # Check 2: 50-Point Roster officers not holding establishment post
    roster_file = os.path.join(VERIFIED_DIR, "From AD HQ/Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx")
    wb_r = openpyxl.load_workbook(roster_file, read_only=True, data_only=True)
    ws_r = wb_r['Sheet1']
    for r in list(ws_r.iter_rows(values_only=True)):
        if r[0] is not None and r[1] is not None:
            rank = int(r[0])
            rname = clean_str(r[1])
            # Check if this officer exists as an active occupant in master
            match = master_df[(master_df['gradation_rank_roster'] == str(rank)) & (master_df['present_occupant_status'] != 'No')]
            if len(match) == 0:
                all_discrepancies.append({
                    "Conflict_ID": f"VERIF_{len(all_discrepancies)+1:04d}",
                    "Source_File": "From AD HQ/Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx",
                    "Officer_Name": rname,
                    "HRMS_ID": "—",
                    "Field_Name": "ROSTER_PROMOTION_CADRE_POST",
                    "Master_Value": "Post Occupant: No / Unmatched",
                    "Verified_Source_Value": f"Rank {rank} on DD Promotion Panel",
                    "Discrepancy_Type": "OFFICER_NOT_IN_FIELD_ESTABLISHMENT",
                    "Resolution_Rationale": f"Officer is on Authority 1 50-Point Roster for promotion, but holds an un-enumerated post (Directorate HQ, institute, or deputation/SU)."
                })
    wb_r.close()

    # Check 3: Directorate HQ officers from Directorate Headquarters.xlsx
    hq_file = os.path.join(VERIFIED_DIR, "From AD HQ/Directorate Headquarters.xlsx")
    wb_hq = openpyxl.load_workbook(hq_file, read_only=True, data_only=True)
    ws_hq = wb_hq['Sheet1']
    for r in list(ws_hq.iter_rows(values_only=True))[1:]:
        if r[1] is not None:
            pname = clean_str(r[1])
            is_f = clean_str(r[2]).upper() == "F"
            iname = clean_str(r[3])
            su_val = clean_str(r[4])
            if is_f and iname:
                # Check if in master
                m_match = master_df[(master_df['present_officer_name'].str.contains(iname[:8], case=False, na=False)) & (master_df['district'] == 'Kolkata')]
                if len(m_match) == 0:
                    all_discrepancies.append({
                        "Conflict_ID": f"VERIF_{len(all_discrepancies)+1:04d}",
                        "Source_File": "From AD HQ/Directorate Headquarters.xlsx",
                        "Officer_Name": iname,
                        "HRMS_ID": "—",
                        "Field_Name": "HQ_POST_DEPLOYMENT",
                        "Master_Value": "Not shown on Directorate HQ post",
                        "Verified_Source_Value": f"{pname} (SU: {su_val})",
                        "Discrepancy_Type": "HQ_DEPLOYMENT_RECONCILIATION",
                        "Resolution_Rationale": f"Officer shown as incumbent at Directorate HQ in AD HQ return; post is under reconciliation with No. 1809 HQ schedule."
                    })
    wb_hq.close()

    # Save to CSV
    df_all_disc = pd.DataFrame(all_discrepancies)
    out_path = os.path.join(DEST_DIR, "verified_sources_discrepancies_detailed.csv")
    df_all_disc.to_csv(out_path, index=False)
    print(f"\nTotal verified source discrepancies cataloged: {len(df_all_disc)}")
    print(f"Saved to: {out_path}")
    print("\nBreakdown by Discrepancy Type:")
    print(df_all_disc['Discrepancy_Type'].value_counts())

if __name__ == "__main__":
    run_comprehensive_check()
