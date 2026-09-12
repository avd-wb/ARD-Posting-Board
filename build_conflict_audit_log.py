import os
import openpyxl
import pandas as pd
from datetime import datetime

SOURCE_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD"
DEST_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
OUTPUT_CSV = os.path.join(DEST_DIR, "conflict_audit_log.csv")

def parse_date(val):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    s = str(val).strip().split()[0]
    for fmt in ['%d.%m.%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def build_audit_log():
    conflicts = []
    conflict_counter = 1

    # 1. Ingest CHECKS sheet from Gradation List 01092026
    grad_path = os.path.join(SOURCE_DIR, "03_ARD_HR/ARD_HR/02. Working Outputs/20260908 Gradation List 01092026/20260908_AVD_DDP_Gradation_List_01092026.xlsx")
    wb_grad = openpyxl.load_workbook(grad_path, data_only=True)
    ws_checks = wb_grad['CHECKS']
    for r in list(ws_checks.iter_rows(values_only=True))[4:]:
        diff_type = r[0]
        hrms = str(r[1]).strip() if r[1] is not None else ""
        officer = r[2] or ""
        sources_say = r[3] or ""
        action = r[4] or ""
        
        if not diff_type:
            continue

        resolved = ""
        rationale = ""
        field = "HRMS_ID"
        auth1_val = ""
        auth2_val = ""
        auth3_val = ""

        if "does not exist" in diff_type:
            field = "HRMS_ID_TYPO"
            auth1_val = hrms
            # extract corrected ID from text if present
            # e.g., 'The HRMS record for this officer is 2001000629'
            import re
            m = re.search(r'is (\d{10})', sources_say)
            if m:
                resolved = m.group(1)
                auth2_val = resolved
                rationale = f"Authority 2 (HRMS portal) verified valid ID {resolved}; Authority 1 contained typographic error {hrms}."
            else:
                resolved = hrms
                rationale = "Retained Authority 1 printed ID pending official correction."
        elif "left service" in diff_type:
            field = "SERVICE_STATUS"
            auth1_val = "In Gradation List"
            auth2_val = sources_say
            resolved = "Retired / Left Service"
            rationale = "Authority 2 (Official HRMS exit record) confirms superannuation/retirement; excluded from active posting roster per business rules."
        elif "Not found in iFMS" in diff_type:
            field = "HRMS_VERIFICATION"
            auth1_val = hrms
            auth2_val = "Not Found in HRMS"
            resolved = hrms
            rationale = "Retained Authority 1 record under verification with Directorate."
        else:
            field = "DISCREPANCY"
            auth1_val = sources_say
            resolved = action
            rationale = action

        conflicts.append({
            "Conflict_ID": f"CONF_{conflict_counter:04d}",
            "Officer_Name": officer,
            "HRMS_ID": hrms,
            "Field_Name": field,
            "Authority_1_Value": auth1_val,
            "Authority_2_Value": auth2_val,
            "Authority_3_Value": auth3_val,
            "Resolved_Value": resolved,
            "Resolution_Rationale": rationale
        })
        conflict_counter += 1

    # 2. Compare Gradation List vs Employee Encyclopedia (Bible) vs Google Form
    ws_grad_main = wb_grad['GRADATION_2026']
    grad_officers = {}
    for r in list(ws_grad_main.iter_rows(values_only=True))[5:]:
        name = r[4]
        hrms = str(r[5]).strip() if r[5] is not None else ""
        if hrms.endswith('.0'):
            hrms = hrms[:-2]
        if hrms and hrms != 'None':
            grad_officers[hrms] = {
                'name': name,
                'dob': parse_date(r[7]),
                'doj': parse_date(r[9]),
                'dor': parse_date(r[10]),
                'cat': r[11]
            }

    # Load Google Form responses
    form_path = os.path.join(SOURCE_DIR, "_00_Sources/01_Verified_Sources /20260906 Posting Preferences.xlsx")
    wb_form = openpyxl.load_workbook(form_path, data_only=True)
    ws_form = wb_form['Form responses 3']
    for r in list(ws_form.iter_rows(values_only=True))[1:]:
        fname = r[4]
        fhrms = str(r[10]).strip() if r[10] is not None else ""
        if fhrms.endswith('.0'):
            fhrms = fhrms[:-2]
        fdob = parse_date(r[8])
        fdoj = parse_date(r[9])

        if fhrms in grad_officers:
            go = grad_officers[fhrms]
            # DOB comparison
            if fdob and go['dob'] and fdob != go['dob']:
                conflicts.append({
                    "Conflict_ID": f"CONF_{conflict_counter:04d}",
                    "Officer_Name": fname or go['name'],
                    "HRMS_ID": fhrms,
                    "Field_Name": "DOB",
                    "Authority_1_Value": go['dob'],
                    "Authority_2_Value": go['dob'],
                    "Authority_3_Value": fdob,
                    "Resolved_Value": go['dob'],
                    "Resolution_Rationale": "Authority 1 & 2 (Official Gradation / HRMS record) takes precedence over self-declared Google Form survey."
                })
                conflict_counter += 1

            # DOJ comparison
            if fdoj and go['doj'] and fdoj != go['doj']:
                # Distinguish between ad-hoc entry vs notional seniority date
                conflicts.append({
                    "Conflict_ID": f"CONF_{conflict_counter:04d}",
                    "Officer_Name": fname or go['name'],
                    "HRMS_ID": fhrms,
                    "Field_Name": "DOJ",
                    "Authority_1_Value": go['doj'],
                    "Authority_2_Value": go['doj'],
                    "Authority_3_Value": fdoj,
                    "Resolved_Value": go['doj'],
                    "Resolution_Rationale": "Authority 1 (Gradation List official seniority entry date) takes precedence over self-reported date of joining."
                })
                conflict_counter += 1

    wb_grad.close()
    wb_form.close()

    df_conflicts = pd.DataFrame(conflicts)
    df_conflicts.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"Total conflicts logged: {len(df_conflicts)}")
    print(f"Audit log successfully written to: {OUTPUT_CSV}")

if __name__ == "__main__":
    build_audit_log()
