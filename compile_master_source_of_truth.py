import os
import sqlite3
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import datetime as dt
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import re
from typing import Optional, Dict, Any, List, Tuple

SOURCE_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD"
DEST_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
CODEX_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_Codex"
DB_PATH = os.path.join(DEST_DIR, "ard_master_truth.db")
EXCEL_PATH = os.path.join(DEST_DIR, "ARD_Master_Source_Of_Truth.xlsx")

AS_OF = dt.date(2026, 9, 12)

# Styling constants for Excel
FONT_FAMILY = "Segoe UI"
HEADER_FONT = Font(name=FONT_FAMILY, size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid") # Dark Navy Blue
DATA_FONT = Font(name=FONT_FAMILY, size=10, color="000000")
DATA_FONT_MUTED = Font(name=FONT_FAMILY, size=10, color="7F7F7F")

# Required conditional fills
RED_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid") # Light Red
RED_FONT = Font(name=FONT_FAMILY, size=10, bold=True, color="9C0006") # Dark Red

SAFFRON_FILL = PatternFill(start_color="FFC04C", end_color="FFC04C", fill_type="solid") # Warm Saffron
SAFFRON_FONT = Font(name=FONT_FAMILY, size=10, bold=True, color="7A3E00")

GREEN_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid") # Soft Green
GREEN_FONT = Font(name=FONT_FAMILY, size=10, bold=True, color="006100") # Dark Green

BORDER_THIN = Border(
    left=Side(style='thin', color='D9D9D9'),
    right=Side(style='thin', color='D9D9D9'),
    top=Side(style='thin', color='D9D9D9'),
    bottom=Side(style='thin', color='D9D9D9')
)

def parse_date(val: Any) -> Optional[dt.date]:
    if val is None:
        return None
    if isinstance(val, (dt.datetime, dt.date)):
        if isinstance(val, dt.datetime):
            return val.date()
        return val
    s = str(val).strip().split()[0]
    for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def calc_dor(dob: Optional[dt.date]) -> Optional[dt.date]:
    if not dob:
        return None
    ret_year = dob.year + 60
    ret_month = dob.month
    last_day = calendar.monthrange(ret_year, ret_month)[1]
    return dt.date(ret_year, ret_month, last_day)

def calc_service_left(dor: Optional[dt.date], ref_date: dt.date = AS_OF) -> str:
    if not dor:
        return "—"
    if dor < ref_date:
        return "0 years, 0 months, 0 days (Retired)"
    rd = relativedelta(dor, ref_date)
    return f"{rd.years} years, {rd.months} months, {rd.days} days"

def calc_tenure(doj_post: Optional[dt.date], ref_date: dt.date = AS_OF) -> Tuple[float, str]:
    if not doj_post:
        return 0.0, "—"
    rd = relativedelta(ref_date, doj_post)
    years_float = round((ref_date - doj_post).days / 365.25, 1)
    label = f"{rd.years} years, {rd.months} months"
    return years_float, label

def get_normal_tenure(district: str, block: str) -> Tuple[int, str]:
    dist_clean = (district or "").strip().lower()
    block_clean = (block or "").strip().lower()

    # Difficult areas: 4 years
    nb_districts = ["alipurduar", "cooch behar", "coochbehar", "darjeeling", "jalpaiguri", "kalimpong", "uttar dinajpur", "dakshin dinajpur", "siliguri"]
    if any(nb in dist_clean for nb in nb_districts):
        return 4, "4 years (North Bengal difficult area)"

    if "purulia" in dist_clean and any(b in block_clean for b in ["bundowan", "bagmundi", "manbazar-ii", "manbazar ii"]):
        return 4, "4 years (Purulia difficult block)"

    if "bankura" in dist_clean and any(b in block_clean for b in ["hirbundh", "ranibundh"]):
        return 4, "4 years (Bankura difficult block)"

    if any(d in dist_clean for d in ["paschim medinipur", "jhargram"]) and any(b in block_clean for b in ["nayagram", "jamboni", "binpur-i", "binpur-ii", "gopiballavpur-i", "gopiballavpur-ii", "binpur i", "binpur ii", "gopiballavpur i", "gopiballavpur ii"]):
        return 4, "4 years (Jungle Mahal difficult block)"

    if "north 24" in dist_clean and any(b in block_clean for b in ["hingalgunj", "sandeshkhali-i", "sandeshkhali-ii", "sandeshkhali i", "sandeshkhali ii"]):
        return 4, "4 years (Sundarbans difficult block)"

    if "south 24" in dist_clean and any(b in block_clean for b in ["gosaba", "basanti", "sagar", "pathar pratima", "namkhana"]):
        return 4, "4 years (Sundarbans difficult block)"

    return 5, "5 years (Normal area norm)"

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

def compile_and_export():
    print("Step 1: Ingesting verified source datasets...")
    
    # 1. Load Conflicts Log to apply resolved values
    conflict_log_path = os.path.join(DEST_DIR, "conflict_audit_log.csv")
    resolved_conflicts = {} # (hrms, field) -> resolved_value
    if os.path.exists(conflict_log_path):
        c_df = pd.read_csv(conflict_log_path)
        for _, cr in c_df.iterrows():
            hid = clean_hrms(cr['HRMS_ID'])
            fld = clean_str(cr['Field_Name'])
            rval = clean_str(cr['Resolved_Value'])
            if hid and fld and rval:
                resolved_conflicts[(hid, fld)] = rval
    print(f"Loaded {len(resolved_conflicts)} resolved conflicts from conflict audit log.")

    # 2. Load AVD Members
    members_set = set()
    members_path = os.path.join(SOURCE_DIR, "04_AVD_Members/02 Master/20260911_1745_AVD_MDV-MEMBERS_AVD_WBAHVS_Members_with_HRMS_ID.xlsx")
    if os.path.exists(members_path):
        wb_m = openpyxl.load_workbook(members_path, read_only=True, data_only=True)
        ws_m = wb_m['AVD_WBAH&VS_Members']
        for r in list(ws_m.iter_rows(values_only=True))[1:]:
            hid = clean_hrms(r[4])
            if hid:
                members_set.add(hid)
        wb_m.close()

    # Also load Zoho contacts for AVD membership
    zoho_path = os.path.join(SOURCE_DIR, "_00_Sources/Members/20260909 zoho members Contacts.xlsx")
    if os.path.exists(zoho_path):
        z_df = pd.read_excel(zoho_path)
        for _, zr in z_df.iterrows():
            # Check phone, email, name
            cname = clean_name(zr.get('Contact Name') or zr.get('Display Name'))
            if cname:
                members_set.add(cname.lower())

    print(f"Total AVD Membership lookup tokens: {len(members_set)}")

    # 3. Load 50-Point Roster
    roster_ranks_by_name = {}
    roster_path = os.path.join(SOURCE_DIR, "_00_Sources/01_Verified_Sources /From AD HQ/Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx")
    wb_r = openpyxl.load_workbook(roster_path, read_only=True, data_only=True)
    ws_r = wb_r['Sheet1']
    for r in list(ws_r.iter_rows(values_only=True)):
        if r[0] is not None and r[1] is not None:
            try:
                rank = int(r[0])
                cname = clean_name(r[1]).lower()
                roster_ranks_by_name[cname] = rank
            except Exception:
                pass
    wb_r.close()

    # Load 50-Point Roster from PROMOTION_242
    grad_file = os.path.join(SOURCE_DIR, "03_ARD_HR/ARD_HR/02. Working Outputs/20260908 Gradation List 01092026/20260908_AVD_DDP_Gradation_List_01092026.xlsx")
    wb_g = openpyxl.load_workbook(grad_file, read_only=True, data_only=True)
    ws_promo = wb_g['PROMOTION_242']
    roster_ranks_by_hrms = {}
    for r in list(ws_promo.iter_rows(values_only=True))[5:]:
        rank = r[0]
        hid = clean_hrms(r[4])
        if hid and rank:
            try:
                roster_ranks_by_hrms[hid] = int(rank)
            except Exception:
                pass

    # 4. Load GRADATION_2026
    ws_g26 = wb_g['GRADATION_2026']
    grad_officers = {}
    for r in list(ws_g26.iter_rows(values_only=True))[5:]:
        hid = clean_hrms(r[5])
        cname = clean_name(r[4]).lower()
        rec = {
            "name": clean_str(r[4]),
            "qual": clean_str(r[6]),
            "dob": parse_date(r[7]),
            "doj": parse_date(r[9]),
            "dor": parse_date(r[10]),
            "cat": clean_str(r[11]),
            "serial_2026": r[2],
            "status_2026": clean_str(r[3]),
            "hrms_status": clean_str(r[22]),
            "hrms_office": clean_str(r[27])
        }
        if hid:
            grad_officers[hid] = rec
        if cname:
            grad_officers[cname] = rec
    wb_g.close()
    print(f"Loaded {len(grad_officers)} officer records from GRADATION_2026.")

    # 5. Load Employee Encyclopedia (Bible Tab 03B)
    bible_file = os.path.join(SOURCE_DIR, "03_ARD_HR/ARD_BIBLE_20082026.xlsx")
    wb_b = openpyxl.load_workbook(bible_file, read_only=True, data_only=True)
    ws_enc = wb_b['03B Employee Encyclopedia']
    encyclopedia = {}
    for r in list(ws_enc.iter_rows(values_only=True))[4:]:
        hid = clean_hrms(r[1])
        cname = clean_name(r[2]).lower()
        rec = {
            "name": clean_str(r[2]),
            "gender": clean_str(r[3]),
            "category": clean_str(r[5]) or clean_str(r[59]),
            "dob": parse_date(r[6]) or parse_date(r[42]),
            "doj": parse_date(r[7]) or parse_date(r[8]) or parse_date(r[46]),
            "dor": parse_date(r[9]) or parse_date(r[43]),
            "qualification": clean_str(r[11]),
            "home_district": clean_str(r[12]),
            "present_post": clean_str(r[13]),
            "district": clean_str(r[14]),
            "doj_present_post": parse_date(r[16]),
            "tenure_in_post": clean_str(r[17]),
            "su_deputation": clean_str(r[18]),
            "past_postings": clean_str(r[25]),
            "spouse_name": clean_str(r[34]),
            "spouse_occ": clean_str(r[35]),
            "spouse_dept": clean_str(r[36]),
            "spouse_station": clean_str(r[37]),
            "children_count": clean_str(r[39]),
            "children_age": clean_str(r[40]),
            "children_raw": clean_str(r[41])
        }
        if hid:
            encyclopedia[hid] = rec
        if cname:
            encyclopedia[cname] = rec
    wb_b.close()
    print(f"Loaded {len(encyclopedia)} officers from Employee Encyclopedia.")

    # 6. Load HR from DB_ARD_WB.xlsx
    master_db_path = os.path.join(SOURCE_DIR, "_00_Sources/02_Subject to application of mind/20260907_1647_DB_ARD_WB.xlsx")
    wb_m = openpyxl.load_workbook(master_db_path, read_only=True, data_only=True)
    ws_hr = wb_m['HR']
    hr_headers = list(ws_hr.iter_rows(values_only=True))[0]
    hr_idx = {clean_str(h): i for i, h in enumerate(hr_headers)}
    hr_official = {}
    for r in list(ws_hr.iter_rows(values_only=True))[1:]:
        hid = clean_hrms(r[hr_idx.get('hrms', 0)])
        cname = clean_name(r[hr_idx.get('name', 7)]).lower()
        rec = {
            "name": clean_str(r[hr_idx.get('name', 7)]),
            "record_status": clean_str(r[hr_idx.get('record_status', 1)]),
            "dob": parse_date(r[hr_idx.get('dob', 10)]) if 'dob' in hr_idx else None,
            "doj": parse_date(r[hr_idx.get('date_of_entry_seniority', 13)]) if 'date_of_entry_seniority' in hr_idx else None,
            "dor": parse_date(r[hr_idx.get('superannuation_date', 14)]) if 'superannuation_date' in hr_idx else None,
            "doj_present_post": parse_date(r[hr_idx.get('doj_present_post', 18)]) if 'doj_present_post' in hr_idx else None,
            "caste": clean_str(r[hr_idx.get('caste', 11)]) if 'caste' in hr_idx else "",
            "gender": clean_str(r[hr_idx.get('gender', 9)]) if 'gender' in hr_idx else "",
            "charge_type": clean_str(r[hr_idx.get('charge_type', 19)]) if 'charge_type' in hr_idx else "",
            "su_deputation": clean_str(r[hr_idx.get('su_deputation', 20)]) if 'su_deputation' in hr_idx else "",
            "past_postings": clean_str(r[hr_idx.get('past_postings_chronological', 22)]) if 'past_postings_chronological' in hr_idx else ""
        }
        if hid:
            hr_official[hid] = rec
        if cname:
            hr_official[cname] = rec
    wb_m.close()
    print(f"Loaded {len(hr_official)} officers from DB_ARD_WB HR sheet.")

    # 7. Load Google Form Survey Responses
    form_file = os.path.join(SOURCE_DIR, "_00_Sources/01_Verified_Sources /20260906 Posting Preferences.xlsx")
    wb_f = openpyxl.load_workbook(form_file, read_only=True, data_only=True)
    ws_f = wb_f['Form responses 3']
    f_rows = list(ws_f.iter_rows(values_only=True))
    f_headers = f_rows[0]
    f_idx = {clean_str(h): i for i, h in enumerate(f_headers) if h}

    form_by_hrms = {}
    for r in f_rows[1:]:
        hid = clean_hrms(r[10])
        cname = clean_name(r[4]).lower() if len(r) > 4 else ""

        def safe_val(col_name):
            idx = f_idx.get(col_name)
            if idx is not None and 0 <= idx < len(r):
                return clean_str(r[idx])
            return ""

        prefs = []
        for p_num in range(1, 9):
            d_val = safe_val(f"Preference {p_num}: District / Unit")
            b_val = safe_val(f"Preference {p_num}: Establishment or block name, as you know it (for example: BAHC Goghat-II; BLDO Office Swarupnagar; DDARD Office Hooghly)")
            if d_val or b_val:
                prefs.append(f"Pref {p_num}: {d_val} - {b_val}")

        dd_prefs = []
        for p_num in range(1, 9):
            val = safe_val(f"If promoted to Deputy Director, preference {p_num}")
            if val:
                dd_prefs.append(f"DD Pref {p_num}: {val}")

        other_pref = safe_val("Any other preferred posting, in your own words (optional)")
        all_prefs_str = " | ".join(prefs + dd_prefs + ([f"Notes: {other_pref}"] if other_pref else []))

        spouse_name = safe_val("Spouse's name")
        spouse_occ = safe_val("Spouse's occupation sector")
        spouse_dept = safe_val("Spouse's department or organisation")
        spouse_desig = safe_val("Spouse's designation")
        spouse_dist = safe_val("Spouse's posting district")
        spouse_block = safe_val("Spouse's posting block")
        is_spouse_wb = safe_val("Is your spouse also a WBAHVS officer?")

        fam_parts = []
        if spouse_name or spouse_occ or spouse_dist:
            fam_parts.append(f"Spouse: {spouse_name} ({spouse_desig}, {spouse_dept}, Dist: {spouse_dist}, Block: {spouse_block}; WBAHVS: {is_spouse_wb})")

        num_children = safe_val("Number of children")
        ch1_board = safe_val("Child 1: board examination year")
        ch2_board = safe_val("Child 2: board examination year")
        if num_children and num_children != "0":
            ch_str = f"Children: {num_children}"
            if ch1_board: ch_str += f" (Child 1 Board: {ch1_board})"
            if ch2_board: ch_str += f" (Child 2 Board: {ch2_board})"
            fam_parts.append(ch_str)

        health = safe_val("Any spouse health condition relevant to your posting (optional)")
        if health:
            fam_parts.append(f"Health: {health}")

        qual = safe_val("Formal qualifications (tick all)")
        add_qual = safe_val("MVSc or PhD subject, if any")
        ph_status = safe_val("PwD certificate status (optional)")
        want_trans = safe_val("Do you want to continue in your present post, or would you prefer another post from where you can serve better?")

        rec = {
            "name": clean_str(r[4]) if len(r) > 4 else "",
            "gender": clean_str(r[7]) if len(r) > 7 else "",
            "dob": parse_date(r[8]) if len(r) > 8 else None,
            "doj": parse_date(r[9]) if len(r) > 9 else None,
            "preferences": all_prefs_str,
            "family_details": " | ".join(fam_parts),
            "qualification": qual,
            "additional_qualification": add_qual,
            "ph_status": "Yes" if "yes" in ph_status.lower() or "certificate" in ph_status.lower() else "No",
            "want_transfer": want_trans
        }
        if hid:
            form_by_hrms[hid] = rec
        if cname:
            form_by_hrms[cname] = rec
    wb_f.close()
    print(f"Loaded {len(form_by_hrms)} form responses.")

    # 8. Load Base 1,899 Post Roster from AVD_Codex board
    codex_csv = os.path.join(CODEX_DIR, "AVD_ARD_posting_decision_board.csv")
    print(f"Loading Base 1,899 Posts from {codex_csv}...")
    base_df = pd.read_csv(codex_csv)
    print(f"Base posts count: {len(base_df)}")

    master_records = []
    retired_officers_excluded = 0

    for idx, row in base_df.iterrows():
        p_key = clean_str(row['post_key'])
        h_rank = int(row['hierarchy_rank']) if pd.notnull(row['hierarchy_rank']) else 7
        name_of_post = clean_str(row['name_of_post'])
        post_type = clean_str(row['type'])
        if post_type == "Obliterated":
            post_type = "Abolished"
        elif post_type == "Under verification":
            post_type = "Unchanged"

        desig = clean_str(row['designation'])
        post = clean_str(row['post'])
        estab = clean_str(row['establishment'])
        block = clean_str(row['block'])
        if block == "Directorate HQ" or "headquarter" in estab.lower():
            block = "" # Clean block display for HQ
        district = clean_str(row['district'])

        norm_years, norm_label = get_normal_tenure(district, block)

        # Incumbent identification
        raw_occupant_status = clean_str(row['present_occupant_status'])
        raw_name = clean_str(row['present_officer_name'])
        raw_hrms = clean_hrms(row['present_officer_hrms_id'])
        cname = clean_name(raw_name).lower() if raw_name else ""

        # Normalize Occupant Status
        occupant_status = "No"
        if raw_occupant_status.lower() in ["yes", "filled"]:
            occupant_status = "Yes"
        elif "service" in raw_occupant_status.lower():
            occupant_status = "on Service Utilized"
        elif "additional" in raw_occupant_status.lower():
            occupant_status = "on Additional Charge"

        if raw_name in ["—", "None", "", "Under verification"]:
            occupant_status = "No"
            raw_name = ""

        # Pull officer data from Authority Hierarchy
        grad = grad_officers.get(raw_hrms) or grad_officers.get(cname) or {}
        enc = encyclopedia.get(raw_hrms) or encyclopedia.get(cname) or {}
        hro = hr_official.get(raw_hrms) or hr_official.get(cname) or {}
        frm = form_by_hrms.get(raw_hrms) or form_by_hrms.get(cname) or {}

        # Check Conflict Overrides
        if (raw_hrms, "HRMS_ID_TYPO") in resolved_conflicts:
            raw_hrms = resolved_conflicts[(raw_hrms, "HRMS_ID_TYPO")]

        # Determine DOB & DOR
        dob = grad.get("dob") or hro.get("dob") or enc.get("dob") or frm.get("dob")
        dor = calc_dor(dob)

        # Determine DOJ
        doj = grad.get("doj") or hro.get("doj") or enc.get("doj") or frm.get("doj")

        # Determine Present Post DOJ and Tenure
        doj_post = parse_date(row['present_officer_tenure_since_posting'])
        if not doj_post:
            doj_post = hro.get("doj_present_post") or enc.get("doj_present_post")

        tenure_float, tenure_str = calc_tenure(doj_post, AS_OF) if occupant_status != "No" else (0.0, "—")
        if tenure_str == "—" and clean_str(row['present_officer_tenure_since_posting']) not in ["—", "Under verification", ""]:
            tenure_str = clean_str(row['present_officer_tenure_since_posting'])

        # Check DOR Exclusion Rule
        is_retired = False
        if occupant_status != "No" and dor:
            if dor < AS_OF:
                is_retired = True
                retired_officers_excluded += 1
                occupant_status = "No"
                raw_name = ""
                raw_hrms = ""
                tenure_str = "—"
                tenure_float = 0.0

        is_tenure_over = "Yes" if (occupant_status != "No" and tenure_float > norm_years) else "No"
        # If tenure_str indicates > norm_years
        if occupant_status != "No" and is_tenure_over == "No":
            if row['eligible_due_to_tenure_over'] == "Yes":
                is_tenure_over = "Yes"

        # Check AVD Affiliation
        avd_affiliation = "No"
        if occupant_status != "No":
            if raw_hrms in members_set or cname in members_set or row['present_officer_avd_affiliation'] == "Yes":
                avd_affiliation = "Yes"

        # Service utilization
        su_util = clean_str(row['present_officer_service_utilization'])
        if su_util in ["—", "Under verification", "None"]:
            su_util = hro.get("su_deputation") or enc.get("su_deputation") or "—"
        if su_util != "—" and occupant_status == "Yes":
            occupant_status = "on Service Utilized"

        # Last posting history
        past_postings = clean_str(row['present_officer_last_posting_history'])
        if past_postings in ["—", "Under verification", "None"]:
            past_postings = hro.get("past_postings") or enc.get("past_postings") or "—"

        # Roster Rank
        roster_rank = None
        if occupant_status != "No":
            if raw_hrms in roster_ranks_by_hrms:
                roster_rank = roster_ranks_by_hrms[raw_hrms]
            elif cname in roster_ranks_by_name:
                roster_rank = roster_ranks_by_name[cname]
            elif pd.notnull(row['present_officer_revised_50_point_roster_rank']) and str(row['present_officer_revised_50_point_roster_rank']).isdigit():
                roster_rank = int(row['present_officer_revised_50_point_roster_rank'])

        # Caste / Category
        caste = "Gen"
        if occupant_status != "No":
            raw_c = grad.get("cat") or hro.get("caste") or enc.get("category") or row['present_officer_caste'] or "Gen"
            c_str = str(raw_c).upper()
            if "SC" in c_str: caste = "SC"
            elif "ST" in c_str: caste = "ST"
            elif "OBC" in c_str: caste = "OBC"
            elif "EWS" in c_str: caste = "EWS"
            else: caste = "Gen"

        # PH Status
        ph_status = "No"
        if occupant_status != "No":
            if frm.get("ph_status") == "Yes" or row['present_officer_ph_status'] == "Yes":
                ph_status = "Yes"

        # Gender
        gender = "Male"
        if occupant_status != "No":
            g_raw = frm.get("gender") or hro.get("gender") or enc.get("gender") or row['present_officer_gender']
            if g_raw and "female" in str(g_raw).lower():
                gender = "Female"

        # Preferences
        prefs = "—"
        if occupant_status != "No":
            prefs = frm.get("preferences") or clean_str(row['present_officer_posting_preferences_all'])
            if not prefs or prefs == "Under verification":
                prefs = "—"

        # Family Details
        fam = "—"
        if occupant_status != "No":
            fam = frm.get("family_details") or clean_str(row['family_details'])
            if not fam or fam == "Under verification":
                if enc.get("spouse_name"):
                    fam = f"Spouse: {enc.get('spouse_name')} ({enc.get('spouse_occ')}, {enc.get('spouse_dept')})"
                else:
                    fam = "—"

        # Qualifications
        qual = "B.V.Sc. & A.H."
        add_qual = "—"
        if occupant_status != "No":
            qual = frm.get("qualification") or grad.get("qual") or enc.get("qualification") or clean_str(row['qualification']) or "B.V.Sc. & A.H."
            if qual in ["—", "Under verification", "None"]:
                qual = "B.V.Sc. & A.H."
            add_qual = frm.get("additional_qualification") or clean_str(row['additional_qualification']) or "—"
            if add_qual in ["—", "Under verification", "None"]:
                add_qual = "—"

        # Date & Age Strings
        dob_str = dob.isoformat() if (dob and occupant_status != "No") else "—"
        doj_str = doj.isoformat() if (doj and occupant_status != "No") else "—"
        dor_str = dor.isoformat() if (dor and occupant_status != "No") else "—"
        age_str = str(relativedelta(AS_OF, dob).years) if (dob and occupant_status != "No") else "—"
        service_left_str = calc_service_left(dor, AS_OF) if (dor and occupant_status != "No") else "—"

        # Transfer Eligibility Evaluation
        elig_promo = "Yes" if (occupant_status != "No" and roster_rank is not None and 1 <= roster_rank <= 242) else "No"
        elig_tenure = is_tenure_over
        elig_displace = "Yes" if (occupant_status != "No" and post_type == "Abolished") else "No"
        elig_oblit = "Yes" if (occupant_status != "No" and post_type == "Abolished") else "No"
        elig_other = "No"
        if occupant_status != "No":
            if (frm and frm.get("want_transfer") and "prefer another" in frm.get("want_transfer", "").lower()) or (fam and ("Health" in fam or "Board" in fam)):
                elig_other = "Yes"

        # Hierarchically Formatted Name of Post:
        # <Designation>, <post>, <establishment>, <block if any>, <district>
        if block:
            formatted_post_name = f"{desig}, {post}, {estab}, {block}, {district}"
        else:
            formatted_post_name = f"{desig}, {post}, {estab}, {district}"

        rec = {
            "hierarchy_rank": h_rank,
            "col1_name_of_post": formatted_post_name,
            "col2_type": post_type,
            "col3_designation": desig,
            "col4_post": post,
            "col5_establishment": estab,
            "col6_block": block if block else "—",
            "col7_district": district,
            "col8_normal_tenure": norm_label,
            "col9_occupant_status": occupant_status,
            "col10_officer_name": raw_name if occupant_status != "No" else "—",
            "col11_tenure": tenure_str if occupant_status != "No" else "—",
            "is_tenure_over": is_tenure_over,
            "col12_hrms_id": raw_hrms if occupant_status != "No" else "—",
            "col13_dob": dob_str,
            "col14_age": age_str,
            "col15_doj": doj_str,
            "col16_dor": dor_str,
            "col17_service_left": service_left_str,
            "col18_avd_affiliation": avd_affiliation if occupant_status != "No" else "No",
            "col19_service_utilization": su_util if occupant_status != "No" else "—",
            "col20_last_posting_history": past_postings if occupant_status != "No" else "—",
            "col21_roster_rank": str(roster_rank) if (roster_rank and occupant_status != "No") else "—",
            "col22_caste": caste if occupant_status != "No" else "—",
            "col23_ph_status": ph_status if occupant_status != "No" else "—",
            "col24_gender": gender if occupant_status != "No" else "—",
            "col25_preferences": prefs if occupant_status != "No" else "—",
            "col26_elig_promotion": elig_promo,
            "col27_elig_tenure_over": elig_tenure,
            "col28_elig_displacement": elig_displace,
            "col29_elig_post_obliteration": elig_oblit,
            "col30_elig_other_reasons": elig_other,
            "col31_qualification": qual if occupant_status != "No" else "—",
            "col32_additional_qualification": add_qual if occupant_status != "No" else "—",
            "col33_family_details": fam if occupant_status != "No" else "—"
        }
        master_records.append(rec)

    # Sort master records hierarchically: rank, type order (Unchanged=0, New=1, Abolished=2), district, block, establishment
    type_priority = {"Unchanged": 0, "New": 1, "Abolished": 2}
    master_records.sort(key=lambda x: (
        x['hierarchy_rank'],
        type_priority.get(x['col2_type'], 3),
        x['col7_district'],
        x['col6_block'],
        x['col5_establishment']
    ))

    print(f"Total compiled master records: {len(master_records)}")
    print(f"Retired officers excluded from active roster: {retired_officers_excluded}")

    # Step 2: Write to SQLite Database
    print(f"Step 2: Writing into SQLite Database: {DB_PATH}...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE master_source_of_truth (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_of_post TEXT,
        type TEXT,
        designation TEXT,
        post TEXT,
        establishment TEXT,
        block TEXT,
        district TEXT,
        normal_tenure TEXT,
        present_occupant_status TEXT,
        present_officer_name TEXT,
        present_officer_tenure TEXT,
        tenure_over_flag TEXT,
        present_officer_hrms_id TEXT,
        present_officer_dob TEXT,
        age TEXT,
        present_officer_doj TEXT,
        present_officer_dor TEXT,
        years_months_days_left TEXT,
        avd_affiliation TEXT,
        service_utilization TEXT,
        last_posting_history TEXT,
        gradation_rank_roster TEXT,
        caste TEXT,
        ph_status TEXT,
        gender TEXT,
        posting_preferences_all TEXT,
        elig_promotion TEXT,
        elig_tenure_over TEXT,
        elig_displacement TEXT,
        elig_post_obliteration TEXT,
        elig_other_reasons TEXT,
        qualification TEXT,
        additional_qualification TEXT,
        family_details TEXT
    )
    """)

    insert_sql = """
    INSERT INTO master_source_of_truth (
        name_of_post, type, designation, post, establishment, block, district, normal_tenure,
        present_occupant_status, present_officer_name, present_officer_tenure, tenure_over_flag,
        present_officer_hrms_id, present_officer_dob, age, present_officer_doj, present_officer_dor,
        years_months_days_left, avd_affiliation, service_utilization, last_posting_history,
        gradation_rank_roster, caste, ph_status, gender, posting_preferences_all, elig_promotion,
        elig_tenure_over, elig_displacement, elig_post_obliteration, elig_other_reasons,
        qualification, additional_qualification, family_details
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for r in master_records:
        cur.execute(insert_sql, (
            r['col1_name_of_post'], r['col2_type'], r['col3_designation'], r['col4_post'],
            r['col5_establishment'], r['col6_block'], r['col7_district'], r['col8_normal_tenure'],
            r['col9_occupant_status'], r['col10_officer_name'], r['col11_tenure'], r['is_tenure_over'],
            r['col12_hrms_id'], r['col13_dob'], r['col14_age'], r['col15_doj'], r['col16_dor'],
            r['col17_service_left'], r['col18_avd_affiliation'], r['col19_service_utilization'],
            r['col20_last_posting_history'], r['col21_roster_rank'], r['col22_caste'], r['col23_ph_status'],
            r['col24_gender'], r['col25_preferences'], r['col26_elig_promotion'], r['col27_elig_tenure_over'],
            r['col28_elig_displacement'], r['col29_elig_post_obliteration'], r['col30_elig_other_reasons'],
            r['col31_qualification'], r['col32_additional_qualification'], r['col33_family_details']
        ))

    conn.commit()
    conn.close()

    if os.path.exists(CODEX_DIR):
        import shutil
        shutil.copy2(DB_PATH, os.path.join(CODEX_DIR, "ard_master_truth.db"))
        print(f"Mirrored database to: {os.path.join(CODEX_DIR, 'ard_master_truth.db')}")

    # Step 3: Generate ARD_Master_Source_Of_Truth.xlsx with conditional styling
    print(f"Step 3: Generating formatted Excel: {EXCEL_PATH}...")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master Source of Truth"
    ws.views.sheetView[0].showGridLines = True

    headers = [
        "Name of the Posts of ARD Departments",
        "Type",
        "Designation",
        "Post",
        "Establishment",
        "Block",
        "District",
        "Normal tenure of the post as per transfer policy of 2009",
        "Present occupant officer status",
        "Present occupant officer's Name",
        "Present officer's tenure since posting",
        "Present officer's HRMS ID",
        "Present officer's DOB",
        "Age",
        "Present officer's Date of Joining to the service (DOJ)",
        "Present officer's Date of retirement (DOR)",
        "Years, months, days left to retirement",
        "Present officer's Association affiliation status for AVD",
        "Present officer's Service Utilization if any",
        "Present officer's Last posting history with tenure",
        "Present officer's Gradation list rank as per 'Revised 50 Point Roster (Only Name) dt. 07-09-2026 (1)'",
        "Present officer's Caste",
        "Present officer's PH status",
        "Present officer's Gender",
        "Present officer's Posting preferences all",
        "Is eligible for transfer - due to promotion?",
        "Is eligible for transfer - due to tenure over?",
        "Is eligible for transfer - due to displacement while another officer posted in place?",
        "Is eligible for transfer - due to post obliteration due to service restructuring?",
        "Is eligible for transfer - due to other reasons (manual)?",
        "His Qualification",
        "Additional qualification",
        "Family details"
    ]

    ws.append(headers)

    # Style Header Row
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_THIN
    ws.row_dimensions[1].height = 42

    # Data Rows
    row_idx = 2
    for r in master_records:
        row_vals = [
            r['col1_name_of_post'],
            r['col2_type'],
            r['col3_designation'],
            r['col4_post'],
            r['col5_establishment'],
            r['col6_block'],
            r['col7_district'],
            r['col8_normal_tenure'],
            r['col9_occupant_status'],
            r['col10_officer_name'],
            r['col11_tenure'],
            r['col12_hrms_id'],
            r['col13_dob'],
            r['col14_age'],
            r['col15_doj'],
            r['col16_dor'],
            r['col17_service_left'],
            r['col18_avd_affiliation'],
            r['col19_service_utilization'],
            r['col20_last_posting_history'],
            r['col21_roster_rank'],
            r['col22_caste'],
            r['col23_ph_status'],
            r['col24_gender'],
            r['col25_preferences'],
            r['col26_elig_promotion'],
            r['col27_elig_tenure_over'],
            r['col28_elig_displacement'],
            r['col29_elig_post_obliteration'],
            r['col30_elig_other_reasons'],
            r['col31_qualification'],
            r['col32_additional_qualification'],
            r['col33_family_details']
        ]
        ws.append(row_vals)
        ws.row_dimensions[row_idx].height = 22

        # Apply cell styling and conditional fills
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.font = DATA_FONT
            cell.border = BORDER_THIN
            cell.alignment = Alignment(vertical="center")

            # Column 11: Tenure since posting -> Red if tenure over
            if col_num == 11:
                if r['is_tenure_over'] == "Yes":
                    cell.fill = RED_FILL
                    cell.font = RED_FONT

            # Column 18: AVD Affiliation -> Saffron if Yes
            elif col_num == 18:
                if r['col18_avd_affiliation'] == "Yes":
                    cell.fill = SAFFRON_FILL
                    cell.font = SAFFRON_FONT
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="center", vertical="center")

            # Columns 26, 27, 28, 29, 30: Transfer Eligibility -> Green if Yes
            elif col_num in [26, 27, 28, 29, 30]:
                cell_val = str(cell.value)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if cell_val == "Yes":
                    cell.fill = GREEN_FILL
                    cell.font = GREEN_FONT

            # Align specific columns
            elif col_num in [2, 9, 12, 13, 14, 15, 16, 21, 22, 23, 24]:
                cell.alignment = Alignment(horizontal="center", vertical="center")

        row_idx += 1

    # Freeze Header Row & Auto-filter
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # Auto-fit column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col[:100])
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)

    wb.save(EXCEL_PATH)
    print(f"Successfully generated: {EXCEL_PATH} (File size: {os.path.getsize(EXCEL_PATH)/1024/1024:.2f} MB)")

    # Also save a copy to AVD_Codex if exists
    if os.path.exists(CODEX_DIR):
        import shutil
        shutil.copy2(EXCEL_PATH, os.path.join(CODEX_DIR, "ARD_Master_Source_Of_Truth.xlsx"))
        print(f"Mirrored Excel to: {os.path.join(CODEX_DIR, 'ARD_Master_Source_Of_Truth.xlsx')}")

if __name__ == "__main__":
    compile_and_export()
