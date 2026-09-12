import os
import openpyxl
import pandas as pd
import json
import shutil
from typing import Dict, Any, List

SOURCE_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD"
DEST_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
ORDERS_REPO_DIR = os.path.join(DEST_DIR, "orders_repository")
BIBLE_PATH = os.path.join(SOURCE_DIR, "03_ARD_HR/ARD_BIBLE_20082026.xlsx")

DRIVE_MAP = {
    "TRANSFER": "https://drive.google.com/drive/u/0/folders/18gFWezrf0K0jtblDSwmU7Hj8w4Rk0Fmh",
    "APPOINTMENT": "https://drive.google.com/drive/u/0/folders/18gFWezrf0K0jtblDSwmU7Hj8w4Rk0Fmh",
    "CONFIRMATION_OF_SERVICE": "https://drive.google.com/drive/u/0/folders/1u5uwZk62DjN5Bb-QuLImjSxxhwgWZGBw",
    "PROMOTION": "https://drive.google.com/drive/u/0/folders/1BJVSIAOCJLl6lTSXP5qpglniqU_kdug1", # MCAS
    "MCAS": "https://drive.google.com/drive/u/0/folders/1BJVSIAOCJLl6lTSXP5qpglniqU_kdug1",
    "WBVAA": "https://drive.google.com/drive/folders/1r7jH3CNvaJA07w6FC23OJ7YMREwvsblc?usp=drive_link"
}

WEB_MAP = {
    "TRANSFER": "https://ard.wb.gov.in/appointment-transfers",
    "APPOINTMENT": "https://ard.wb.gov.in/appointment-transfers",
    "CONFIRMATION_OF_SERVICE": "https://ard.wb.gov.in/order-notifications",
    "PROMOTION": "https://ard.wb.gov.in/order-notifications",
    "CADRE_SCHEDULE": "https://ard.wb.gov.in/order-notifications",
    "STATUTORY_RULES": "https://ard.wb.gov.in/order-notifications",
    "HEAD_OF_OFFICE": "https://ard.wb.gov.in/order-notifications",
    "GRADATION_LIST": "https://ard.wb.gov.in/order-notifications",
    "TRANSFER_POLICY": "https://ard.wb.gov.in/order-notifications",
    "GENERAL": "https://ard.wb.gov.in/order-notifications"
}

def build_orders_repository():
    print(f"Creating orders repository in {ORDERS_REPO_DIR}...")
    os.makedirs(ORDERS_REPO_DIR, exist_ok=True)
    
    # Subdirectories by major administrative stream
    categories = [
        "01_appointments_and_transfers",
        "02_service_confirmation",
        "03_mcas_and_promotions",
        "04_cadre_restructuring_and_rules",
        "05_gradation_lists_and_rosters",
        "06_general_orders_and_circulars"
    ]
    for cat in categories:
        os.makedirs(os.path.join(ORDERS_REPO_DIR, cat), exist_ok=True)

    # 1. Load catalog from Bible Tab 09
    wb = openpyxl.load_workbook(BIBLE_PATH, read_only=True, data_only=True)
    ws_ord = wb['09 Orders & Notifications Index']
    orders = []
    for r in list(ws_ord.iter_rows(values_only=True))[1:]:
        if r[0] is not None and str(r[0]).isdigit():
            c_type = str(r[1]).strip() if r[1] else "GENERAL"
            dt_val = str(r[2]).split()[0] if r[2] else ""
            ord_no = str(r[3]).strip() if r[3] else ""
            title = str(r[4]).strip() if r[4] else ""
            officers = str(r[5]).strip() if r[5] else ""
            file_name = str(r[9]).strip() if len(r) > 9 and r[9] else ""

            # Determine folder and drive/web source
            target_sub = "06_general_orders_and_circulars"
            drive_link = DRIVE_MAP.get(c_type, DRIVE_MAP["WBVAA"])
            web_link = WEB_MAP.get(c_type, "https://ard.wb.gov.in/order-notifications")

            if c_type in ["TRANSFER", "APPOINTMENT"]:
                target_sub = "01_appointments_and_transfers"
            elif c_type == "CONFIRMATION_OF_SERVICE":
                target_sub = "02_service_confirmation"
            elif c_type in ["PROMOTION", "MCAS"]:
                target_sub = "03_mcas_and_promotions"
            elif c_type in ["CADRE_SCHEDULE", "STATUTORY_RULES", "HEAD_OF_OFFICE"]:
                target_sub = "04_cadre_restructuring_and_rules"
            elif c_type in ["GRADATION_LIST", "ROSTER_PROMOTION"]:
                target_sub = "05_gradation_lists_and_rosters"

            orders.append({
                "Order_Index": int(r[0]),
                "Category": c_type,
                "Order_Date": dt_val,
                "Order_Number": ord_no,
                "Title": title,
                "Key_Beneficiaries_or_Officers": officers,
                "Subdirectory": target_sub,
                "Web_Source_Portal": web_link,
                "Google_Drive_Archive": drive_link,
                "Referenced_File": file_name
            })
    wb.close()

    df_orders = pd.DataFrame(orders)
    csv_path = os.path.join(ORDERS_REPO_DIR, "orders_master_index.csv")
    json_path = os.path.join(ORDERS_REPO_DIR, "orders_master_index.json")

    df_orders.to_csv(csv_path, index=False)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2)

    print(f"Orders repository initialized with {len(df_orders)} records.")
    print(f"Master index saved to: {csv_path} and {json_path}")

    # Generate README for orders repository
    readme_path = os.path.join(ORDERS_REPO_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# ARD Department Orders & Notifications Master Repository\n\n")
        f.write("This repository organizes and indexes all official published documents from:\n")
        f.write("* [https://ard.wb.gov.in/appointment-transfers](https://ard.wb.gov.in/appointment-transfers)\n")
        f.write("* [https://ard.wb.gov.in/order-notifications](https://ard.wb.gov.in/order-notifications)\n")
        f.write("* **Google Drive Archives**:\n")
        f.write("  * `Appointments_&_Transfers`: [18gFWezrf0K0jtblDSwmU7Hj8w4Rk0Fmh](https://drive.google.com/drive/u/0/folders/18gFWezrf0K0jtblDSwmU7Hj8w4Rk0Fmh)\n")
        f.write("  * `Service_Confirmation`: [1u5uwZk62DjN5Bb-QuLImjSxxhwgWZGBw](https://drive.google.com/drive/u/0/folders/1u5uwZk62DjN5Bb-QuLImjSxxhwgWZGBw)\n")
        f.write("  * `MCAS`: [1BJVSIAOCJLl6lTSXP5qpglniqU_kdug1](https://drive.google.com/drive/u/0/folders/1BJVSIAOCJLl6lTSXP5qpglniqU_kdug1)\n")
        f.write("  * `00_LIVE_WBVAA_Search_Bar`: [1r7jH3CNvaJA07w6FC23OJ7YMREwvsblc](https://drive.google.com/drive/folders/1r7jH3CNvaJA07w6FC23OJ7YMREwvsblc)\n\n")
        f.write("## Repository Structure\n\n")
        f.write("```\n")
        f.write("orders_repository/\n")
        f.write("├── 01_appointments_and_transfers/     # 169 Transfer orders & 38 PSC appointment notifications\n")
        f.write("├── 02_service_confirmation/           # 83 Service confirmation orders in WBAH&VS\n")
        f.write("├── 03_mcas_and_promotions/            # 75 MCAS promotion orders (8, 15, 16, 24, 25 years)\n")
        f.write("├── 04_cadre_restructuring_and_rules/  # Landmark Rules No. 1808, Schedule No. 1809, HoO No. 575\n")
        f.write("├── 05_gradation_lists_and_rosters/    # Final Gradation List No. 3768 & 50-Point Roster\n")
        f.write("├── 06_general_orders_and_circulars/   # 49 Misc orders, leave rules, SAR/APR hierarchies\n")
        f.write("├── orders_master_index.csv            # Tabular master index with metadata and links\n")
        f.write("└── orders_master_index.json           # Machine-readable JSON index for LLM ingestion\n")
        f.write("```\n")

    print(f"README generated at: {readme_path}")

if __name__ == "__main__":
    build_orders_repository()
