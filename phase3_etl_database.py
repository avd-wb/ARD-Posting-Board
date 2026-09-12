import os
import sqlite3
import openpyxl
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

AS_OF = dt.date(2026, 9, 12)

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
    # North Bengal except Malda
    nb_districts = ["alipurduar", "cooch behar", "coochbehar", "darjeeling", "jalpaiguri", "kalimpong", "uttar dinajpur", "dakshin dinajpur", "siliguri"]
    if any(nb in dist_clean for nb in nb_districts):
        return 4, "4 years (North Bengal difficult area)"

    # Specific blocks in Purulia
    if "purulia" in dist_clean and any(b in block_clean for b in ["bundowan", "bagmundi", "manbazar-ii", "manbazar ii"]):
        return 4, "4 years (Purulia difficult block)"

    # Specific blocks in Bankura
    if "bankura" in dist_clean and any(b in block_clean for b in ["hirbundh", "ranibundh"]):
        return 4, "4 years (Bankura difficult block)"

    # Specific blocks in Paschim Medinipur / Jhargram
    if any(d in dist_clean for d in ["paschim medinipur", "jhargram"]) and any(b in block_clean for b in ["nayagram", "jamboni", "binpur-i", "binpur-ii", "gopiballavpur-i", "gopiballavpur-ii", "binpur i", "binpur ii", "gopiballavpur i", "gopiballavpur ii"]):
        return 4, "4 years (Jungle Mahal difficult block)"

    # Specific blocks in North 24 Parganas
    if "north 24" in dist_clean and any(b in block_clean for b in ["hingalgunj", "sandeshkhali-i", "sandeshkhali-ii", "sandeshkhali i", "sandeshkhali ii"]):
        return 4, "4 years (Sundarbans difficult block)"

    # Specific blocks in South 24 Parganas
    if "south 24" in dist_clean and any(b in block_clean for b in ["gosaba", "basanti", "sagar", "pathar pratima", "namkhana"]):
        return 4, "4 years (Sundarbans difficult block)"

    return 5, "5 years (Normal area norm)"

def clean_hrms(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
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

def run_etl():
    print(f"Starting Phase 3 ETL at {datetime.now().isoformat()}...")
    
    # 1. Load AVD Members
    print("Loading AVD Members...")
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
    print(f"Loaded {len(members_set)} verified AVD members by HRMS ID.")

    # 2. Load 50-Point Roster
    print("Loading Revised 50-Point Roster...")
    roster_ranks = {} # hrms -> rank, and name -> rank
    roster_path = os.path.join(SOURCE_DIR, "_00_Sources/01_Verified_Sources /From AD HQ/Revised 50 Point Roster (Only Name) dt. 07-09-2026.xlsx")
    wb_r = openpyxl.load_workbook(roster_path, read_only=True, data_only=True)
    ws_r = wb_r['Sheet1']
    for r in list(ws_r.iter_rows(values_only=True)):
        if r[0] is not None and r[1] is not None:
            try:
                rank = int(r[0])
                name = clean_str(r[1])
                clean_n = re.sub(r'\(.*?\)', '', name).replace('Dr.', '').replace('Dr', '').strip().lower()
                roster_ranks[clean_n] = rank
            except Exception:
                pass
    wb_r.close()
    print(f"Loaded {len(roster_ranks)} ranks from 50-Point Roster.")

    # Also map roster ranks from PROMOTION_242 in Gradation List (which has HRMS IDs!)
    grad_file = os.path.join(SOURCE_DIR, "03_ARD_HR/ARD_HR/02. Working Outputs/20260908 Gradation List 01092026/20260908_AVD_DDP_Gradation_List_01092026.xlsx")
    wb_g = openpyxl.load_workbook(grad_file, read_only=True, data_only=True)
    ws_promo = wb_g['PROMOTION_242']
    roster_by_hrms = {}
    for r in list(ws_promo.iter_rows(values_only=True))[5:]:
        rank = r[0]
        hid = clean_hrms(r[4])
        if hid and rank:
            try:
                roster_by_hrms[hid] = int(rank)
            except Exception:
                pass
    print(f"Loaded {len(roster_by_hrms)} roster ranks mapped directly to HRMS ID.")

    # 3. Load Gradation List 2026 details
    ws_g26 = wb_g['GRADATION_2026']
    grad_details = {}
    for r in list(ws_g26.iter_rows(values_only=True))[5:]:
        hid = clean_hrms(r[5])
        if hid:
            grad_details[hid] = {
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
    wb_g.close()
    print(f"Loaded {len(grad_details)} officer records from GRADATION_2026.")

    # 4. Load Employee Encyclopedia (Bible Tab 03B)
    print("Loading Employee Encyclopedia (Bible Tab 03B)...")
    bible_file = os.path.join(SOURCE_DIR, "03_ARD_HR/ARD_BIBLE_20082026.xlsx")
    wb_b = openpyxl.load_workbook(bible_file, read_only=True, data_only=True)
    ws_enc = wb_b['03B Employee Encyclopedia']
    encyclopedia = {}
    for r in list(ws_enc.iter_rows(values_only=True))[4:]:
        hid = clean_hrms(r[1])
        if hid:
            encyclopedia[hid] = {
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
    wb_b.close()
    print(f"Loaded {len(encyclopedia)} officers from Employee Encyclopedia.")

    # 5. Load Google Form Responses
    print("Loading Google Form responses...")
    form_file = os.path.join(SOURCE_DIR, "_00_Sources/01_Verified_Sources /20260906 Posting Preferences.xlsx")
    wb_f = openpyxl.load_workbook(form_file, read_only=True, data_only=True)
    ws_f = wb_f['Form responses 3']
    f_rows = list(ws_f.iter_rows(values_only=True))
    f_headers = f_rows[0]
    
    # Map header index
    f_idx = {clean_str(h): i for i, h in enumerate(f_headers) if h}
    
    form_by_hrms = {}
    for r in f_rows[1:]:
        hid = clean_hrms(r[10]) # 'HRMS ID (10 digits), fill if known'
        if not hid:
            # try mobile matching or name matching later if needed
            continue
        
        def safe_val(col_name):
            idx = f_idx.get(col_name)
            if idx is not None and 0 <= idx < len(r):
                return clean_str(r[idx])
            return ""

        # Compile preferences 1 to 8
        prefs = []
        for p_num in range(1, 9):
            d_col = f"Preference {p_num}: District / Unit"
            e_col = f"Preference {p_num}: Establishment type"
            b_col = f"Preference {p_num}: Establishment or block name, as you know it (for example: BAHC Goghat-II; BLDO Office Swarupnagar; DDARD Office Hooghly)"
            d_val = safe_val(d_col)
            b_val = safe_val(b_col)
            if d_val or b_val:
                prefs.append(f"Pref {p_num}: {d_val} - {b_val}")
        
        # DD tier prefs
        dd_prefs = []
        for p_num in range(1, 9):
            col = f"If promoted to Deputy Director, preference {p_num}"
            val = safe_val(col)
            if val:
                dd_prefs.append(f"DD Pref {p_num}: {val}")
        
        # Other text prefs
        other_pref = safe_val("Any other preferred posting, in your own words (optional)")
        
        all_prefs_str = " | ".join(prefs + dd_prefs + ([f"Notes: {other_pref}"] if other_pref else []))

        # Family & Spouse details
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
        ch1_dob = safe_val("Child 1: date of birth")
        ch1_board = safe_val("Child 1: board examination year")
        ch2_dob = safe_val("Child 2: date of birth")
        ch2_board = safe_val("Child 2: board examination year")
        
        if num_children and num_children != "0":
            ch_str = f"Children: {num_children}"
            if ch1_board: ch_str += f" (Child 1 Board: {ch1_board})"
            if ch2_board: ch_str += f" (Child 2 Board: {ch2_board})"
            fam_parts.append(ch_str)

        # Health condition
        health = safe_val("Any spouse health condition relevant to your posting (optional)")
        if health:
            fam_parts.append(f"Health: {health}")

        # Qualifications
        qual = safe_val("Formal qualifications (tick all)")
        add_qual = safe_val("MVSc or PhD subject, if any")
        ph_status = safe_val("PwD certificate status (optional)")
        want_trans = safe_val("Do you want to continue in your present post, or would you prefer another post from where you can serve better?")

        form_by_hrms[hid] = {
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
    wb_f.close()
    print(f"Loaded {len(form_by_hrms)} validated form responses keyed by HRMS ID.")

    # 6. Load Sanctioned Posts & Incumbents (1,899 posts = 1,794 from Cadre Schedule + 105 Obliterated from VF-POSTS)
    print("Compiling complete Post Universe (1,794 Cadre + 105 Obliterated = 1,899 posts)...")
    
    # Load Cadre 1794
    cadre_df = pd.read_csv(os.path.join(SOURCE_DIR, "03_ARD_HR/01 Verification data for establishment and Posts from districts/20260911_AVD_CADRE-VERIFY_1794_Posts_Tab_Export.csv"))
    
    # Load VF-POSTS (has incumbents, post status, dates)
    vf_posts_df = pd.read_excel(os.path.join(SOURCE_DIR, "04_AVD_Members/06 Vacancies/20260911_AVD_VF-POSTS_Sanctioned_Posts_Incumbents_and_Likely_Vacancies.xlsx"), sheet_name="POSTS")
    
    # Build lookup from VF-POSTS by composite key (district, establishment, post) and by HRMS ID
    vf_by_post_key = {}
    vf_by_hrms = {}
    for _, row in vf_posts_df.iterrows():
        d = clean_str(row['District / Unit'])
        e = clean_str(row['Establishment'])
        p = clean_str(row['Post'])
        b = clean_str(row['Block / Sub-division'])
        hid = clean_hrms(row['HRMS ID'])
        pkey = f"{d.lower()}|{e.lower()}|{p.lower()}"
        vf_by_post_key[pkey] = row
        if hid:
            vf_by_hrms[hid] = row

    # Identify the 105 Obliterated Posts from VF-POSTS
    obliterated_rows = vf_posts_df[vf_posts_df['Status under No.1809'] == 'OBLITERATED']
    print(f"Found {len(obliterated_rows)} obliterated posts under No. 1808 in VF-POSTS.")

    # Create master list of post records
    all_master_records = []
    seen_incumbent_hrms = set()

    # Part A: Process all 1,794 posts from Cadre Schedule No. 1809
    for idx, c_row in cadre_df.iterrows():
        d = clean_str(c_row['District / Unit'])
        e = clean_str(c_row['Establishment'])
        p = clean_str(c_row['Post (nomenclature)'])
        p_code = clean_str(c_row['Post code'])
        estab_type = clean_str(c_row['Establishment type'])
        
        # Determine Designation and Rank
        desig = "Veterinary Officer"
        rank_order = 7
        if p_code == "DIR":
            desig = "Director"
            rank_order = 1
        elif "ADDL" in p_code:
            desig = "Additional Director"
            rank_order = 2
        elif "JD" in p_code:
            desig = "Joint Director"
            rank_order = 3
        elif "DD" in p_code:
            desig = "Deputy Director"
            rank_order = 4
        elif "AD" in p_code:
            desig = "Assistant Director"
            rank_order = 5
        elif p_code == "BLDO":
            desig = "Block Livestock Development Officer"
            rank_order = 6

        # Try to match with VF-POSTS
        pkey = f"{d.lower()}|{e.lower()}|{p.lower()}"
        vf_match = vf_by_post_key.get(pkey)
        
        block = ""
        post_type = "Unchanged"
        # If it's a newly created post under 1809 (e.g. JD at district office, new DDs, new polyclinic VOs)
        if p_code in ["JD", "JD_F"] or (p_code in ["DD", "DD_F"] and "directorate" not in e.lower() and "iah" not in e.lower() and not vf_match):
            post_type = "New"
        elif vf_match is not None and clean_str(vf_match['Status under No.1809']) == "New":
            post_type = "New"

        incumbent_name = ""
        hrms_id = ""
        post_status = "No" # Vacant
        doj_present_post = None
        su_util = ""
        
        if vf_match is not None:
            block = clean_str(vf_match['Block / Sub-division'])
            raw_status = clean_str(vf_match['Post status'])
            incumbent_name = clean_str(vf_match['Incumbent'])
            hrms_id = clean_hrms(vf_match['HRMS ID'])
            doj_present_post = parse_date(vf_match['Date of joining present post'])
            if raw_status == "FILLED" and incumbent_name and incumbent_name != "—":
                post_status = "Yes"

        # Check exclusion rule for retired officers
        officer_dob = None
        officer_doj = None
        officer_dor = None
        caste = "Gen"
        gender = "Male"
        ph_status = "No"
        qual = "B.V.Sc. & A.H."
        add_qual = ""
        fam_details = ""
        prefs = ""
        past_postings = ""
        avd_member = "No"
        roster_rank = None

        if hrms_id:
            # Check Encyclopedia / Gradation / Form
            enc = encyclopedia.get(hrms_id, {})
            grad = grad_details.get(hrms_id, {})
            form = form_by_hrms.get(hrms_id, {})

            officer_dob = grad.get("dob") or enc.get("dob") or form.get("dob")
            officer_doj = grad.get("doj") or enc.get("doj") or form.get("doj")
            officer_dor = calc_dor(officer_dob)

            # Check DOR Exclusion Rule: DOR < 2026-09-12
            if officer_dor and officer_dor < AS_OF:
                # Officer is retired! Clear incumbent details from active roster
                incumbent_name = ""
                hrms_id = ""
                post_status = "No"
                doj_present_post = None
            else:
                seen_incumbent_hrms.add(hrms_id)
                # Resolve attributes
                caste = enc.get("category") or grad.get("cat") or "Gen"
                # Standardize caste
                c_upper = caste.upper()
                if "SC" in c_upper: caste = "SC"
                elif "ST" in c_upper: caste = "ST"
                elif "OBC" in c_upper: caste = "OBC"
                elif "EWS" in c_upper: caste = "EWS"
                else: caste = "Gen"

                gender = enc.get("gender") or form.get("gender") or "Male"
                ph_status = form.get("ph_status", "No")
                qual = form.get("qualification") or enc.get("qualification") or grad.get("qual") or "B.V.Sc. & A.H."
                add_qual = form.get("additional_qualification") or ""
                fam_details = form.get("family_details") or ""
                if not fam_details and enc.get("spouse_name"):
                    fam_details = f"Spouse: {enc.get('spouse_name')} ({enc.get('spouse_occ')}, {enc.get('spouse_dept')})"
                
                prefs = form.get("preferences") or ""
                past_postings = enc.get("past_postings") or ""
                su_util = enc.get("su_deputation") or ""
                if su_util and su_util != "—":
                    post_status = "on Service Utilized"

                if hrms_id in members_set:
                    avd_member = "Yes"

                # Check 50-Point Roster Rank
                if hrms_id in roster_by_hrms:
                    roster_rank = roster_by_hrms[hrms_id]
                else:
                    clean_n = re.sub(r'\(.*?\)', '', incumbent_name).replace('Dr.', '').replace('Dr', '').strip().lower()
                    if clean_n in roster_ranks:
                        roster_rank = roster_ranks[clean_n]

        # Normal Tenure Calculation
        norm_years, norm_label = get_normal_tenure(d, block)
        tenure_float, tenure_str = calc_tenure(doj_present_post, AS_OF) if post_status != "No" else (0.0, "—")
        is_tenure_over = "Yes" if (post_status != "No" and tenure_float > norm_years) else "No"

        # Service Left Calculation
        age_str = str(relativedelta(AS_OF, officer_dob).years) if (officer_dob and post_status != "No") else "—"
        dor_str = officer_dor.isoformat() if (officer_dor and post_status != "No") else "—"
        service_left_str = calc_service_left(officer_dor, AS_OF) if (officer_dor and post_status != "No") else "—"
        dob_str = officer_dob.isoformat() if (officer_dob and post_status != "No") else "—"
        doj_str = officer_doj.isoformat() if (officer_doj and post_status != "No") else "—"

        # Format Name of the Posts of ARD Departments:
        # <Designation>, <post>, <establishment>, <block if any>, <district>
        if block:
            full_post_name = f"{desig}, {p}, {e}, {block}, {d}"
        else:
            full_post_name = f"{desig}, {p}, {e}, {d}"

        # Transfer Eligibility Flags:
        # 1. Due to promotion: Yes if on 242 DD promotion roster
        elig_promo = "Yes" if (post_status != "No" and roster_rank is not None and 1 <= roster_rank <= 242) else "No"
        # 2. Due to tenure over:
        elig_tenure = is_tenure_over
        # 3. Due to displacement:
        elig_displace = "No" # Active post under 1809
        # 4. Due to post obliteration:
        elig_oblit = "No"
        # 5. Due to other reasons (manual/hardship/health/spouse/survey request):
        elig_other = "No"
        if post_status != "No":
            if (form and form.get("want_transfer") and "prefer another" in form.get("want_transfer", "").lower()) or (fam_details and ("Health" in fam_details or "Board" in fam_details)):
                elig_other = "Yes"

        rec = {
            "rank_order": rank_order,
            "name_of_post": full_post_name,
            "type": post_type,
            "designation": desig,
            "post": p,
            "establishment": e,
            "block": block,
            "district": d,
            "normal_tenure": norm_label,
            "present_occupant_status": post_status,
            "present_officer_name": incumbent_name if post_status != "No" else "—",
            "present_officer_tenure": tenure_str if post_status != "No" else "—",
            "tenure_over_flag": is_tenure_over,
            "present_officer_hrms_id": hrms_id if post_status != "No" else "—",
            "present_officer_dob": dob_str,
            "age": age_str,
            "present_officer_doj": doj_str,
            "present_officer_dor": dor_str,
            "years_months_days_left": service_left_str,
            "avd_affiliation": avd_member if post_status != "No" else "No",
            "service_utilization": su_util if post_status != "No" else "—",
            "last_posting_history": past_postings if post_status != "No" else "—",
            "gradation_rank_roster": str(roster_rank) if (roster_rank and post_status != "No") else "—",
            "caste": caste if post_status != "No" else "—",
            "ph_status": ph_status if post_status != "No" else "—",
            "gender": gender if post_status != "No" else "—",
            "posting_preferences_all": prefs if post_status != "No" else "—",
            "elig_promotion": elig_promo,
            "elig_tenure_over": elig_tenure,
            "elig_displacement": elig_displace,
            "elig_post_obliteration": elig_oblit,
            "elig_other_reasons": elig_other,
            "qualification": qual if post_status != "No" else "—",
            "additional_qualification": add_qual if post_status != "No" else "—",
            "family_details": fam_details if post_status != "No" else "—"
        }
        all_master_records.append(rec)

    # Part B: Process all 105 Obliterated Posts under No. 1808
    for _, o_row in obliterated_rows.iterrows():
        d = clean_str(o_row['District / Unit'])
        e = clean_str(o_row['Establishment'])
        p = clean_str(o_row['Post'])
        b = clean_str(o_row['Block / Sub-division'])
        raw_status = clean_str(o_row['Post status'])
        incumbent_name = clean_str(o_row['Incumbent'])
        hrms_id = clean_hrms(o_row['HRMS ID'])
        doj_present_post = parse_date(o_row['Date of joining present post'])
        
        desig = "Assistant Director"
        if "DVO" in p.upper() or "DISTRICT VETERINARY" in p.upper():
            desig = "District Veterinary Officer"
        elif "DD" in p.upper():
            desig = "Deputy Director"

        post_status = "No"
        if raw_status == "FILLED" and incumbent_name and incumbent_name != "—":
            post_status = "Yes"

        # Check exclusion rule for retired officers
        officer_dob = None
        officer_doj = None
        officer_dor = None
        caste = "Gen"
        gender = "Male"
        ph_status = "No"
        qual = "B.V.Sc. & A.H."
        add_qual = ""
        fam_details = ""
        prefs = ""
        past_postings = ""
        avd_member = "No"
        roster_rank = None
        su_util = ""

        if hrms_id:
            enc = encyclopedia.get(hrms_id, {})
            grad = grad_details.get(hrms_id, {})
            form = form_by_hrms.get(hrms_id, {})

            officer_dob = grad.get("dob") or enc.get("dob") or form.get("dob")
            officer_doj = grad.get("doj") or enc.get("doj") or form.get("doj")
            officer_dor = calc_dor(officer_dob)

            if officer_dor and officer_dor < AS_OF:
                incumbent_name = ""
                hrms_id = ""
                post_status = "No"
                doj_present_post = None
            else:
                seen_incumbent_hrms.add(hrms_id)
                caste = enc.get("category") or grad.get("cat") or "Gen"
                c_upper = caste.upper()
                if "SC" in c_upper: caste = "SC"
                elif "ST" in c_upper: caste = "ST"
                elif "OBC" in c_upper: caste = "OBC"
                elif "EWS" in c_upper: caste = "EWS"
                else: caste = "Gen"

                gender = enc.get("gender") or form.get("gender") or "Male"
                ph_status = form.get("ph_status", "No")
                qual = form.get("qualification") or enc.get("qualification") or grad.get("qual") or "B.V.Sc. & A.H."
                add_qual = form.get("additional_qualification") or ""
                fam_details = form.get("family_details") or ""
                if not fam_details and enc.get("spouse_name"):
                    fam_details = f"Spouse: {enc.get('spouse_name')} ({enc.get('spouse_occ')}, {enc.get('spouse_dept')})"
                
                prefs = form.get("preferences") or ""
                past_postings = enc.get("past_postings") or ""
                su_util = enc.get("su_deputation") or ""
                if su_util and su_util != "—":
                    post_status = "on Service Utilized"

                if hrms_id in members_set:
                    avd_member = "Yes"

                if hrms_id in roster_by_hrms:
                    roster_rank = roster_by_hrms[hrms_id]
                else:
                    clean_n = re.sub(r'\(.*?\)', '', incumbent_name).replace('Dr.', '').replace('Dr', '').strip().lower()
                    if clean_n in roster_ranks:
                        roster_rank = roster_ranks[clean_n]

        norm_years, norm_label = get_normal_tenure(d, b)
        tenure_float, tenure_str = calc_tenure(doj_present_post, AS_OF) if post_status != "No" else (0.0, "—")
        is_tenure_over = "Yes" if (post_status != "No" and tenure_float > norm_years) else "No"

        age_str = str(relativedelta(AS_OF, officer_dob).years) if (officer_dob and post_status != "No") else "—"
        dor_str = officer_dor.isoformat() if (officer_dor and post_status != "No") else "—"
        service_left_str = calc_service_left(officer_dor, AS_OF) if (officer_dor and post_status != "No") else "—"
        dob_str = officer_dob.isoformat() if (officer_dob and post_status != "No") else "—"
        doj_str = officer_doj.isoformat() if (officer_doj and post_status != "No") else "—"

        if b:
            full_post_name = f"{desig}, {p}, {e}, {b}, {d}"
        else:
            full_post_name = f"{desig}, {p}, {e}, {d}"

        elig_promo = "Yes" if (post_status != "No" and roster_rank is not None and 1 <= roster_rank <= 242) else "No"
        elig_tenure = is_tenure_over
        elig_displace = "Yes" if post_status != "No" else "No" # Displaced because post is abolished!
        elig_oblit = "Yes" if post_status != "No" else "No" # Post obliterated!
        elig_other = "No"
        if post_status != "No":
            if (form and form.get("want_transfer") and "prefer another" in form.get("want_transfer", "").lower()) or (fam_details and ("Health" in fam_details or "Board" in fam_details)):
                elig_other = "Yes"

        rec = {
            "rank_order": 99, # Abolished post tier
            "name_of_post": full_post_name,
            "type": "Abolished",
            "designation": desig,
            "post": p,
            "establishment": e,
            "block": b,
            "district": d,
            "normal_tenure": norm_label,
            "present_occupant_status": post_status,
            "present_officer_name": incumbent_name if post_status != "No" else "—",
            "present_officer_tenure": tenure_str if post_status != "No" else "—",
            "tenure_over_flag": is_tenure_over,
            "present_officer_hrms_id": hrms_id if post_status != "No" else "—",
            "present_officer_dob": dob_str,
            "age": age_str,
            "present_officer_doj": doj_str,
            "present_officer_dor": dor_str,
            "years_months_days_left": service_left_str,
            "avd_affiliation": avd_member if post_status != "No" else "No",
            "service_utilization": su_util if post_status != "No" else "—",
            "last_posting_history": past_postings if post_status != "No" else "—",
            "gradation_rank_roster": str(roster_rank) if (roster_rank and post_status != "No") else "—",
            "caste": caste if post_status != "No" else "—",
            "ph_status": ph_status if post_status != "No" else "—",
            "gender": gender if post_status != "No" else "—",
            "posting_preferences_all": prefs if post_status != "No" else "—",
            "elig_promotion": elig_promo,
            "elig_tenure_over": elig_tenure,
            "elig_displacement": elig_displace,
            "elig_post_obliteration": elig_oblit,
            "elig_other_reasons": elig_other,
            "qualification": qual if post_status != "No" else "—",
            "additional_qualification": add_qual if post_status != "No" else "—",
            "family_details": fam_details if post_status != "No" else "—"
        }
        all_master_records.append(rec)

    # Sort records hierarchically: rank_order, district, block, establishment, post
    all_master_records.sort(key=lambda x: (x['rank_order'], x['district'], x['block'], x['establishment'], x['post']))

    print(f"Total compiled master records: {len(all_master_records)}")

    # 7. Write to SQLite Database
    print(f"Writing to SQLite database: {DB_PATH}...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE master_source_of_truth (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rank_order INTEGER,
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
        rank_order, name_of_post, type, designation, post, establishment, block, district,
        normal_tenure, present_occupant_status, present_officer_name, present_officer_tenure,
        tenure_over_flag, present_officer_hrms_id, present_officer_dob, age, present_officer_doj,
        present_officer_dor, years_months_days_left, avd_affiliation, service_utilization,
        last_posting_history, gradation_rank_roster, caste, ph_status, gender,
        posting_preferences_all, elig_promotion, elig_tenure_over, elig_displacement,
        elig_post_obliteration, elig_other_reasons, qualification, additional_qualification, family_details
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for r in all_master_records:
        cur.execute(insert_sql, (
            r['rank_order'], r['name_of_post'], r['type'], r['designation'], r['post'], r['establishment'],
            r['block'], r['district'], r['normal_tenure'], r['present_occupant_status'], r['present_officer_name'],
            r['present_officer_tenure'], r['tenure_over_flag'], r['present_officer_hrms_id'], r['present_officer_dob'],
            r['age'], r['present_officer_doj'], r['present_officer_dor'], r['years_months_days_left'],
            r['avd_affiliation'], r['service_utilization'], r['last_posting_history'], r['gradation_rank_roster'],
            r['caste'], r['ph_status'], r['gender'], r['posting_preferences_all'], r['elig_promotion'],
            r['elig_tenure_over'], r['elig_displacement'], r['elig_post_obliteration'], r['elig_other_reasons'],
            r['qualification'], r['additional_qualification'], r['family_details']
        ))

    conn.commit()
    conn.close()

    # Also duplicate DB to CODEX_DIR if exists
    if os.path.exists(CODEX_DIR):
        import shutil
        shutil.copy2(DB_PATH, os.path.join(CODEX_DIR, "ard_master_truth.db"))
        print(f"Mirrored database to: {os.path.join(CODEX_DIR, 'ard_master_truth.db')}")

    print(f"Phase 3 ETL Complete. Database saved at: {DB_PATH}")

if __name__ == "__main__":
    run_etl()
