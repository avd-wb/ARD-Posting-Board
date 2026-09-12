import os
import sqlite3
import pandas as pd
import openpyxl
import datetime as dt
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import re
from typing import Dict, Any, List

VERIFIED_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources "
DEST_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
DB_PATH = os.path.join(DEST_DIR, "ard_master_truth.db")

def clean_hrms(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s in ["None", "nan", "—", "-", "Under verification"]:
        return ""
    return s

def clean_str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s in ["None", "nan"]:
        return ""
    return s

def clean_name(val: Any) -> str:
    s = clean_str(val)
    s = re.sub(r'\(.*?\)', '', s)
    s = s.replace('Dr.', '').replace('Dr', '').strip()
    return s

def audit_against_verified_sources():
    print("=== AUDITING AGAINST 01_VERIFIED_SOURCES ===")
    
    conn = sqlite3.connect(DB_PATH)
    master_df = pd.read_sql_query("SELECT * FROM master_source_of_truth", conn)
    conn.close()
    print(f"Loaded master table: {len(master_df)} rows.")

    master_by_hrms = {}
    master_by_name = {}
    for idx, r in master_df.iterrows():
        hid = clean_hrms(r['present_officer_hrms_id'])
        name = clean_name(r['present_officer_name']).lower()
        if hid:
            master_by_hrms[hid] = r
        if name and name != "—":
            master_by_name[name] = r

    discrepancies = []

    # -------------------------------------------------------------
    # 1. Compare with Source from HRMS/2026090_HRMS_ARD_20260908.tsv
    # -------------------------------------------------------------
    hrms_tsv = os.path.join(VERIFIED_DIR, "Source from HRMS/2026090_HRMS_ARD_20260908.tsv")
    print(f"\n1. Auditing against official HRMS dump: {hrms_tsv}...")
    if os.path.exists(hrms_tsv):
        df_hrms = pd.read_csv(hrms_tsv, sep='\t')
        print(f"Total rows in HRMS dump: {len(df_hrms)}")
        
        # Check active status and superannuation
        for _, hr_row in df_hrms.iterrows():
            hid = clean_hrms(hr_row['hrms'])
            h_name = clean_str(hr_row['name'])
            h_status = clean_str(hr_row['status'])
            h_end = clean_str(hr_row['service_end_date'])
            h_post = clean_str(hr_row['post'])
            h_office = clean_str(hr_row['office_name'])

            if hid in master_by_hrms:
                m_rec = master_by_hrms[hid]
                m_name = m_rec['present_officer_name']
                m_dor = m_rec['present_officer_dor']
                m_status = m_rec['present_occupant_status']

                # Discrepancy: HRMS says retired/resigned/deceased but listed as active occupant
                if h_status.lower() in ["retired", "resigned", "deceased"] and m_status != "No":
                    discrepancies.append({
                        "Source_File": "2026090_HRMS_ARD_20260908.tsv",
                        "Officer_Name": m_name,
                        "HRMS_ID": hid,
                        "Category": "HRMS_STATUS_CONFLICT",
                        "Master_Value": f"Occupant Status: {m_status}",
                        "Verified_Source_Value": f"HRMS Status: {h_status} (End Date: {h_end})",
                        "Impact": "Officer has left service according to HRMS dump; should be excluded from active occupancy."
                    })

                # Discrepancy: Service End Date mismatch
                if h_end and m_dor != "—":
                    try:
                        # parse DD/MM/YYYY
                        hend_date = datetime.strptime(h_end, "%d/%m/%Y").date().isoformat()
                        if hend_date != m_dor:
                            discrepancies.append({
                                "Source_File": "2026090_HRMS_ARD_20260908.tsv",
                                "Officer_Name": m_name,
                                "HRMS_ID": hid,
                                "Category": "SUPERANNUATION_DATE_MISMATCH",
                                "Master_Value": m_dor,
                                "Verified_Source_Value": hend_date,
                                "Impact": f"Calculated DOR ({m_dor}) differs from HRMS service end date ({hend_date})."
                            })
                    except Exception:
                        pass

    # -------------------------------------------------------------
    # 2. Compare with From AD HQ/Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx
    # -------------------------------------------------------------
    roster_file = os.path.join(VERIFIED_DIR, "From AD HQ/Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx")
    print(f"\n2. Auditing against Revised 50 Point Roster: {roster_file}...")
    if os.path.exists(roster_file):
        wb_r = openpyxl.load_workbook(roster_file, read_only=True, data_only=True)
        ws_r = wb_r['Sheet1']
        roster_rows = [r for r in ws_r.iter_rows(values_only=True) if r[0] is not None and r[1] is not None]
        print(f"Total roster rows: {len(roster_rows)}")
        
        roster_found_in_master = 0
        for r in roster_rows:
            rank = int(r[0])
            r_name = clean_str(r[1])
            cname = clean_name(r_name).lower()

            # Check if this officer is in master
            match = master_by_name.get(cname)
            if match is not None:
                roster_found_in_master += 1
                m_rank = match['gradation_rank_roster']
                m_promo = match['elig_promotion']
                if str(m_rank) != str(rank) or m_promo != "Yes":
                    discrepancies.append({
                        "Source_File": "Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx",
                        "Officer_Name": r_name,
                        "HRMS_ID": match['present_officer_hrms_id'],
                        "Category": "ROSTER_RANK_OR_PROMOTION_FLAG_MISMATCH",
                        "Master_Value": f"Rank: {m_rank}, Promo: {m_promo}",
                        "Verified_Source_Value": f"Rank: {rank}, Promo: Yes",
                        "Impact": "Roster rank or promotion eligibility flag inconsistent with top authority roster."
                    })
            else:
                # Officer not matched by exact name
                discrepancies.append({
                    "Source_File": "Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx",
                    "Officer_Name": r_name,
                    "HRMS_ID": "—",
                    "Category": "ROSTER_OFFICER_NOT_HOLDING_SANCTIONED_POST",
                    "Master_Value": "Not found in active post occupant list",
                    "Verified_Source_Value": f"Roster Rank: {rank}",
                    "Impact": "Officer on promotion panel does not currently occupy an active establishment post in the schedule (likely at HQ/deputation or vacant)."
                })
        print(f"Roster officers matched directly to active posts in master: {roster_found_in_master} / {len(roster_rows)}")

    # -------------------------------------------------------------
    # 3. Compare with From AD HQ/Vacancy of DD.xlsx
    # -------------------------------------------------------------
    vac_dd_file = os.path.join(VERIFIED_DIR, "From AD HQ/Vacancy of DD.xlsx")
    print(f"\n3. Auditing against Vacancy of DD: {vac_dd_file}...")
    if os.path.exists(vac_dd_file):
        wb_v = openpyxl.load_workbook(vac_dd_file, read_only=True, data_only=True)
        ws_v = wb_v['Sheet1']
        vac_rows = list(ws_v.iter_rows(values_only=True))[1:]
        print(f"Total vacant DD posts in official HQ return: {len(vac_rows)}")
        
        # Check DD posts in master
        dd_master = master_df[master_df['designation'] == 'Deputy Director']
        dd_vacant_master = dd_master[dd_master['present_occupant_status'] == 'No']
        print(f"Total Deputy Director posts in Master: {len(dd_master)}, of which Vacant: {len(dd_vacant_master)}")

    # -------------------------------------------------------------
    # 4. Compare with From AD HQ/Directorate Headquarters.xlsx
    # -------------------------------------------------------------
    hq_file = os.path.join(VERIFIED_DIR, "From AD HQ/Directorate Headquarters.xlsx")
    print(f"\n4. Auditing against Directorate Headquarters return: {hq_file}...")
    if os.path.exists(hq_file):
        wb_hq = openpyxl.load_workbook(hq_file, read_only=True, data_only=True)
        ws_hq = wb_hq['Sheet1']
        hq_rows = [r for r in list(ws_hq.iter_rows(values_only=True))[1:] if r[1] is not None]
        print(f"Total HQ posts in return: {len(hq_rows)}")
        for hr in hq_rows:
            p_name = clean_str(hr[1])
            is_filled = clean_str(hr[2]).upper() == "F"
            inc_name = clean_str(hr[3])
            su_val = clean_str(hr[4])
            if is_filled and inc_name:
                cname = clean_name(inc_name).lower()
                if cname not in master_by_name:
                    discrepancies.append({
                        "Source_File": "Directorate Headquarters.xlsx",
                        "Officer_Name": inc_name,
                        "HRMS_ID": "—",
                        "Category": "HQ_OFFICER_POSTING_ALIGNMENT",
                        "Master_Value": "Not holding HQ post in 1794 schedule",
                        "Verified_Source_Value": f"Post: {p_name}, SU: {su_val}",
                        "Impact": "HQ return shows officer actively deployed at Directorate HQ."
                    })

    # -------------------------------------------------------------
    # 5. Compare with 20260906 Posting Preferences.xlsx (Google Form)
    # -------------------------------------------------------------
    form_file = os.path.join(VERIFIED_DIR, "20260906 Posting Preferences.xlsx")
    print(f"\n5. Auditing against Posting Preferences Google Form: {form_file}...")
    if os.path.exists(form_file):
        wb_f = openpyxl.load_workbook(form_file, read_only=True, data_only=True)
        ws_f = wb_f['Form responses 3']
        f_rows = list(ws_f.iter_rows(values_only=True))
        print(f"Total Google Form responses: {len(f_rows) - 1}")
        
        pref_matched_count = 0
        for r in f_rows[1:]:
            hid = clean_hrms(r[10])
            fname = clean_str(r[4])
            cname = clean_name(fname).lower()

            match = master_by_hrms.get(hid)
            if match is None:
                match = master_by_name.get(cname)
            if match is not None:
                pref_matched_count += 1
                m_prefs = match['posting_preferences_all']
                if m_prefs in ["—", "None", "", "Under verification"]:
                    discrepancies.append({
                        "Source_File": "20260906 Posting Preferences.xlsx",
                        "Officer_Name": fname,
                        "HRMS_ID": hid,
                        "Category": "MISSING_PREFERENCE_IN_MASTER",
                        "Master_Value": "No preferences recorded",
                        "Verified_Source_Value": "Preferences submitted in Google Form",
                        "Impact": "Officer filled preferences in Google Form but preferences were blank in master table."
                    })
        print(f"Form respondents matched to master table: {pref_matched_count} / {len(f_rows) - 1}")

    # -------------------------------------------------------------
    # Summary of Findings
    # -------------------------------------------------------------
    df_disc = pd.DataFrame(discrepancies)
    out_csv = os.path.join(DEST_DIR, "verified_sources_discrepancies.csv")
    df_disc.to_csv(out_csv, index=False)
    print(f"\nTotal discrepancies found against 01_Verified_Sources: {len(df_disc)}")
    print(f"Saved discrepancy report to: {out_csv}")
    
    if len(df_disc) > 0:
        print("\nDiscrepancy categories count:")
        print(df_disc['Category'].value_counts())
        print("\nSample discrepancies:")
        print(df_disc[['Source_File', 'Officer_Name', 'Category', 'Master_Value', 'Verified_Source_Value']].head(10))

if __name__ == "__main__":
    audit_against_verified_sources()
