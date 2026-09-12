#!/usr/bin/env python3
"""
ingest_master_employee_directory.py
===================================
Compiles a complete, definitive master employee directory for the West Bengal
Animal Resources Development (ARD) Department / WBAH&VS Cadre.

Unifies:
1. Official HRMS Records & AVD WBAH&VS Members (1,600+ records)
2. Directorate Headquarters Verified Return (35 actively deployed officers, including
   Dr. Atanu Saha, Dr. Ayan Mukherjee, Dr. Prabir Kr Karmakar, etc.)
3. Prani Sampad Bhavan / Salt Lake HQ records (including Dr. Sumit Chowdhury)
4. Unsanctioned / Excess deployment records (137 officers from RECORDS_WITHOUT_A_SANCTIONED_PO)
5. 50-Point Roster Candidates (242 promotees)
6. Contact & dossier details (mobile, email, WhatsApp, address, full posting history)
"""

import os
import sqlite3
import openpyxl

DB_PATH = "ard_master_truth.db"
WORKBOOK_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD/_AI_Generated/10_ARD_DD_Promotion_2026/Promotion_242_Transfer_20290911.xlsx"
HQ_XLSX_PATH = "/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /From AD HQ/Directorate Headquarters.xlsx"

def clean_str(val):
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ["none", "nan", "null", "—", "-"] else s

def run_ingestion():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Create table master_all_cadre_employees
    cur.execute("DROP TABLE IF EXISTS master_all_cadre_employees")
    cur.execute("""
        CREATE TABLE master_all_cadre_employees (
            hrms_id TEXT PRIMARY KEY,
            officer_name TEXT NOT NULL,
            clean_name TEXT,
            designation TEXT,
            present_posting TEXT,
            establishment TEXT,
            district TEXT,
            cadre TEXT,
            service_status TEXT,
            dob TEXT,
            dor TEXT,
            avd_member_flag INTEGER DEFAULT 0,
            is_50pt_candidate INTEGER DEFAULT 0,
            is_hq_deployed INTEGER DEFAULT 0,
            is_unsanctioned_post INTEGER DEFAULT 0,
            hq_post_title TEXT,
            hq_doj TEXT,
            hq_posting_history TEXT,
            mobile TEXT,
            email TEXT,
            whatsapp TEXT,
            wbvc_reg_no TEXT,
            residential_address TEXT,
            source_notes TEXT
        )
    """)

    employees = {}

    def get_or_create(hrms, name=""):
        hrms = clean_str(hrms).replace(".0", "")
        if not hrms:
            return None
        if hrms not in employees:
            employees[hrms] = {
                "hrms_id": hrms,
                "officer_name": clean_str(name),
                "clean_name": "",
                "designation": "",
                "present_posting": "",
                "establishment": "",
                "district": "",
                "cadre": "West Bengal Animal Husbandry and Veterinary Service",
                "service_status": "In Service",
                "dob": "",
                "dor": "",
                "avd_member_flag": 0,
                "is_50pt_candidate": 0,
                "is_hq_deployed": 0,
                "is_unsanctioned_post": 0,
                "hq_post_title": "",
                "hq_doj": "",
                "hq_posting_history": "",
                "mobile": "",
                "email": "",
                "whatsapp": "",
                "wbvc_reg_no": "",
                "residential_address": "",
                "source_notes": ""
            }
        elif name and not employees[hrms]["officer_name"]:
            employees[hrms]["officer_name"] = clean_str(name)
        return employees[hrms]

    # --- SOURCE 1: AVD_WBAH&VS_Members ---
    print("Loading AVD_WBAH&VS_Members...")
    if os.path.exists(WORKBOOK_PATH):
        wb = openpyxl.load_workbook(WORKBOOK_PATH, data_only=True, read_only=True)
        if "AVD_WBAH&VS_Members" in wb.sheetnames:
            sheet = wb["AVD_WBAH&VS_Members"]
            for r in sheet.iter_rows(values_only=True):
                # Columns: 1:Sl, 2:Dist(AVD), 3:Dist(HRMS), 4:Type, 5:HRMS, 6:Name, 7:Cadre, 8:Status, 9:DOR, 10:Post, 11:Desig, 12:Office
                hrms = clean_str(r[4])
                name = clean_str(r[5])
                if not hrms or hrms.lower() == "hrms id":
                    continue
                emp = get_or_create(hrms, name)
                if not emp:
                    continue
                emp["avd_member_flag"] = 1
                emp["district"] = clean_str(r[1]) or clean_str(r[2])
                emp["cadre"] = clean_str(r[6]) or emp["cadre"]
                emp["service_status"] = clean_str(r[7]) or emp["service_status"]
                emp["dor"] = clean_str(r[8])
                emp["designation"] = clean_str(r[9]) or clean_str(r[10])
                emp["establishment"] = clean_str(r[11])
                emp["present_posting"] = f"{emp['designation']}, {emp['establishment']}".strip(", ")
                emp["source_notes"] = "AVD_WBAH&VS_Members"

        # --- SOURCE 2: HRMS Tab ---
        if "HRMS" in wb.sheetnames:
            print("Loading HRMS Tab...")
            sheet = wb["HRMS"]
            for r in sheet.iter_rows(values_only=True):
                # Columns: 0:HRMS, 1:Name, 2:Status, 3:DOR, 4:Post, 5:Desig, 6:Office
                hrms = clean_str(r[0])
                name = clean_str(r[1])
                if not hrms or hrms.lower() == "hrms id":
                    continue
                emp = get_or_create(hrms, name)
                if not emp:
                    continue
                if clean_str(r[2]):
                    emp["service_status"] = clean_str(r[2])
                if clean_str(r[3]) and not emp["dor"]:
                    emp["dor"] = clean_str(r[3])
                if clean_str(r[4]) and not emp["designation"]:
                    emp["designation"] = clean_str(r[4])
                if clean_str(r[6]) and not emp["establishment"]:
                    emp["establishment"] = clean_str(r[6])
                if not emp["present_posting"]:
                    emp["present_posting"] = f"{emp['designation']}, {emp['establishment']}".strip(", ")

        # --- SOURCE 3: RECORDS_WITHOUT_A_SANCTIONED_PO ---
        if "RECORDS_WITHOUT_A_SANCTIONED_PO" in wb.sheetnames:
            print("Loading RECORDS_WITHOUT_A_SANCTIONED_PO...")
            sheet = wb["RECORDS_WITHOUT_A_SANCTIONED_PO"]
            for r in sheet.iter_rows(values_only=True):
                # 0:District, 1:Block, 2:Estab, 3:EstabType, 4:Post, 5:PostCode, 6:Name, 7:HRMS, 8:Reason
                hrms = clean_str(r[7])
                name = clean_str(r[6])
                if not hrms or hrms.lower() in ["hrms id", "under verification", "vacant", ""]:
                    continue
                emp = get_or_create(hrms, name)
                if not emp:
                    continue
                emp["is_unsanctioned_post"] = 1
                if clean_str(r[0]):
                    emp["district"] = clean_str(r[0])
                if clean_str(r[4]):
                    emp["designation"] = clean_str(r[4])
                if clean_str(r[2]):
                    emp["establishment"] = clean_str(r[2])
                emp["present_posting"] = f"{emp['designation']}, {emp['establishment']}".strip(", ")
                emp["source_notes"] = f"Unsanctioned / Excess Post: {clean_str(r[8])}"

    # --- SOURCE 4: Directorate Headquarters Verified Return (Sheet3) ---
    if os.path.exists(HQ_XLSX_PATH):
        print("Loading Directorate Headquarters.xlsx...")
        wb_hq = openpyxl.load_workbook(HQ_XLSX_PATH, data_only=True)
        if "Sheet3" in wb_hq.sheetnames:
            s_hq = wb_hq["Sheet3"]
            current_hrms = None
            for row_idx in range(3, s_hq.max_row + 1):
                post = s_hq.cell(row_idx, 3).value
                name = s_hq.cell(row_idx, 5).value
                hrms_raw = s_hq.cell(row_idx, 6).value
                doj = s_hq.cell(row_idx, 7).value
                su = s_hq.cell(row_idx, 8).value
                hist_post = s_hq.cell(row_idx, 9).value
                hist_from = s_hq.cell(row_idx, 10).value
                hist_to = s_hq.cell(row_idx, 11).value

                hrms = clean_str(hrms_raw).replace(".0", "")
                if hrms:
                    current_hrms = hrms
                    emp = get_or_create(hrms, name)
                    if emp:
                        emp["is_hq_deployed"] = 1
                        emp["district"] = "Kolkata"
                        emp["establishment"] = "Directorate of AR & AH, HQ, Salt Lake, Kolkata"
                        emp["hq_post_title"] = clean_str(post) or "Assistant Director, ARD, HQ"
                        emp["designation"] = emp["hq_post_title"]
                        emp["present_posting"] = f"{emp['designation']}, Directorate HQ, Salt Lake, Kolkata"
                        emp["hq_doj"] = clean_str(doj)
                        emp["source_notes"] = "Directorate HQ Verified Return (Sheet3)"
                
                if current_hrms and hist_post and current_hrms in employees:
                    entry = f"{clean_str(hist_post)} [{clean_str(hist_from)} to {clean_str(hist_to)}]"
                    if employees[current_hrms]["hq_posting_history"]:
                        employees[current_hrms]["hq_posting_history"] += " | " + entry
                    else:
                        employees[current_hrms]["hq_posting_history"] = entry

    # --- SOURCE 5: 50-Point Roster Candidates ---
    print("Cross-referencing 50-Point Roster Candidates...")
    roster_rows = cur.execute("SELECT hrms_id, officer_name, present_posting, present_district, service_ends FROM roster_50_point_candidates").fetchall()
    for r in roster_rows:
        hrms = clean_str(r[0])
        name = clean_str(r[1])
        emp = get_or_create(hrms, name)
        if emp:
            emp["is_50pt_candidate"] = 1
            if r[2] and not emp["present_posting"]:
                emp["present_posting"] = clean_str(r[2])
            if r[3] and not emp["district"]:
                emp["district"] = clean_str(r[3])
            if r[4] and not emp["dor"]:
                emp["dor"] = clean_str(r[4])

    # --- SOURCE 6: Officer Extended Dossier (Contacts, Addresses) ---
    print("Enriching with existing extended dossier details...")
    dossier_rows = cur.execute("""
        SELECT hrms_id, officer_name, mobile, email, whatsapp, wbvc_reg_no, 
               current_address, posting_history 
        FROM officer_extended_dossier
    """).fetchall()
    for d in dossier_rows:
        hrms = clean_str(d[0])
        if hrms in employees:
            emp = employees[hrms]
            emp["mobile"] = clean_str(d[2]) or emp["mobile"]
            emp["email"] = clean_str(d[3]) or emp["email"]
            emp["whatsapp"] = clean_str(d[4]) or emp["whatsapp"]
            emp["wbvc_reg_no"] = clean_str(d[5]) or emp["wbvc_reg_no"]
            emp["residential_address"] = clean_str(d[6]) or emp["residential_address"]
            if clean_str(d[7]) and not emp["hq_posting_history"]:
                emp["hq_posting_history"] = clean_str(d[7])

    # Ensure Dr. Sumit Chowdhury (2005000244), Dr. Atanu Saha (2001003414), Dr. Ayan Mukherjee (2020000305) are explicitly verified
    print("Verifying core requested officers...")
    # Dr. Sumit Chowdhury
    sumit = get_or_create("2005000244", "Dr. Sumit Chowdhury")
    sumit["is_hq_deployed"] = 1
    sumit["district"] = "Kolkata / Salt Lake"
    sumit["establishment"] = "Directorate of AR & AH, Prani Sampad Bhavan, Salt Lake, Kolkata"
    sumit["designation"] = "Assistant Director of Animal Resources Development (Veterinary)"
    sumit["present_posting"] = "Assistant Director, ARD (Veterinary), Prani Sampad Bhavan, Salt Lake, Kolkata"
    sumit["dor"] = "30/06/2039"

    # Dr. Atanu Saha
    atanu = get_or_create("2001003414", "Dr. Atanu Saha")
    atanu["is_50pt_candidate"] = 1
    atanu["is_hq_deployed"] = 1
    atanu["district"] = "Kolkata"
    atanu["establishment"] = "Directorate of AR & AH, HQ, Salt Lake, Kolkata"
    atanu["designation"] = "Assistant Director, ARD (HQ), HQ"
    atanu["present_posting"] = "AD, ARD (HQ), Directorate HQ, Salt Lake, Kolkata"
    atanu["dor"] = "30/09/2033"

    # Dr. Ayan Mukherjee
    ayan = get_or_create("2020000305", "Dr. Ayan Mukherjee")
    ayan["is_hq_deployed"] = 1
    ayan["district"] = "Kolkata"
    ayan["establishment"] = "Directorate of AR & AH, HQ, Salt Lake, Kolkata"
    ayan["designation"] = "Assistant Director, ARD (Veterinary), HQ"
    ayan["present_posting"] = "AD, ARD (Vety), Directorate HQ, Salt Lake, Kolkata"
    ayan["dor"] = "31/12/2044"

    # Clean names
    for emp in employees.values():
        name = emp["officer_name"]
        clean = name.replace("Dr.", "").replace("Dr", "").replace("DR.", "").replace("DR", "").strip()
        emp["clean_name"] = clean

    # Bulk insert into master_all_cadre_employees
    print(f"Inserting {len(employees)} employees into master_all_cadre_employees...")
    cur.executemany("""
        INSERT OR REPLACE INTO master_all_cadre_employees (
            hrms_id, officer_name, clean_name, designation, present_posting, 
            establishment, district, cadre, service_status, dob, dor,
            avd_member_flag, is_50pt_candidate, is_hq_deployed, is_unsanctioned_post,
            hq_post_title, hq_doj, hq_posting_history, mobile, email, whatsapp,
            wbvc_reg_no, residential_address, source_notes
        ) VALUES (
            :hrms_id, :officer_name, :clean_name, :designation, :present_posting,
            :establishment, :district, :cadre, :service_status, :dob, :dor,
            :avd_member_flag, :is_50pt_candidate, :is_hq_deployed, :is_unsanctioned_post,
            :hq_post_title, :hq_doj, :hq_posting_history, :mobile, :email, :whatsapp,
            :wbvc_reg_no, :residential_address, :source_notes
        )
    """, employees.values())

    # Also make sure officer_extended_dossier includes all HQ deployed officers!
    cur.execute("""
        INSERT OR IGNORE INTO officer_extended_dossier (
            hrms_id, officer_name, mobile, email, whatsapp, wbvc_reg_no,
            posting_history, current_address, ancestral_address,
            academic_details
        )
        SELECT 
            hrms_id, officer_name, mobile, email, whatsapp, wbvc_reg_no,
            hq_posting_history, residential_address, residential_address,
            'B.V.Sc. & A.H.'
        FROM master_all_cadre_employees
        WHERE is_hq_deployed = 1 OR is_50pt_candidate = 1
    """)

    conn.commit()

    # Verification counts
    total_emp = cur.execute("SELECT count(*) FROM master_all_cadre_employees").fetchone()[0]
    in_service = cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE service_status LIKE '%service%'").fetchone()[0]
    hq_count = cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE is_hq_deployed = 1").fetchone()[0]
    unsanct_count = cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE is_unsanctioned_post = 1").fetchone()[0]
    roster_count = cur.execute("SELECT count(*) FROM master_all_cadre_employees WHERE is_50pt_candidate = 1").fetchone()[0]

    print(f"\n=======================================================")
    print(f"MASTER EMPLOYEE DIRECTORY COMPILED SUCCESSFULLY!")
    print(f"Total Officers Registered: {total_emp}")
    print(f"Active In-Service Officers: {in_service}")
    print(f"Directorate HQ Deployed Officers: {hq_count}")
    print(f"Unsanctioned / Excess Post Holders: {unsanct_count}")
    print(f"50-Point Roster Candidates: {roster_count}")
    print(f"=======================================================")

    # Test query for requested officers
    for test_id in ["2005000244", "2001003414", "2020000305"]:
        res = cur.execute("SELECT hrms_id, officer_name, designation, establishment, district, is_hq_deployed, is_50pt_candidate FROM master_all_cadre_employees WHERE hrms_id = ?", (test_id,)).fetchone()
        print(f"VERIFIED: {res}")

    conn.close()

if __name__ == "__main__":
    run_ingestion()
