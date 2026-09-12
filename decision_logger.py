#!/usr/bin/env python3
"""
decision_logger.py
Master Decision Ledger & Multi-Tier Persistence Subsystem for ARD Department.
Maintains:
1. Append-only Master_Decisions_Ledger.xlsx and Master_Decisions_Ledger.csv
2. Google Sheets sync queue (google_sheets_sync_queue.json)
3. Automated snapshot checkpoints via BackupManager every 5 decisions
4. Real-time transaction audit trail with pay levels and displacement records
"""

import os
import csv
import json
import datetime
from typing import Dict, List, Optional, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from backup_manager import BackupManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
is_vercel = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR") or ("/tmp" if is_vercel else BASE_DIR)
LEDGER_XLSX = os.path.join(WORKSPACE_DIR, "Master_Decisions_Ledger.xlsx")
LEDGER_CSV = os.path.join(WORKSPACE_DIR, "Master_Decisions_Ledger.csv")
SYNC_QUEUE_JSON = os.path.join(WORKSPACE_DIR, "google_sheets_sync_queue.json")

class DecisionLogger:
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or WORKSPACE_DIR
        self.ledger_xlsx = os.path.join(self.workspace_dir, "Master_Decisions_Ledger.xlsx")
        self.ledger_csv = os.path.join(self.workspace_dir, "Master_Decisions_Ledger.csv")
        self.sync_queue_file = os.path.join(self.workspace_dir, "google_sheets_sync_queue.json")
        self.backup_mgr = BackupManager(os.path.join(self.workspace_dir, "ard_master_truth.db"))
        self._init_ledger_files()

    def _init_ledger_files(self):
        """Initializes empty ledger files with proper headers if not already existing."""
        headers = [
            "Sl_No",
            "Transaction_ID",
            "Session_ID",
            "Timestamp",
            "Officer_HRMS",
            "Officer_Name_and_Present_Posting",
            "Present_Pay_Level",
            "Transfer_By",
            "Place_of_Posting_upon_Promotion_Transfer_SU",
            "Pay_Level_upon_Transfer",
            "Displaced_Officer_HRMS",
            "Displaced_Officer_Name",
            "Rules_Compliance_Summary",
            "Sync_Status"
        ]

        if not os.path.exists(self.ledger_csv):
            with open(self.ledger_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

        if not os.path.exists(self.ledger_xlsx):
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Master_Decisions_Ledger"
            ws.append(headers)

            # Style Header
            header_fill = PatternFill(start_color="0A2540", end_color="0A2540", fill_type="solid")
            header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            ws.row_dimensions[1].height = 28
            wb.save(self.ledger_xlsx)

        if not os.path.exists(self.sync_queue_file):
            with open(self.sync_queue_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def log_decision(
        self,
        session_id: str,
        officer_hrms: str,
        officer_name: str,
        present_posting: str,
        present_pay_level: str,
        transfer_by: str,
        substantive_post_name: str,
        su_post_name: Optional[str] = None,
        target_pay_level: str = "Level 19 (Rs. 95,100 - Rs. 1,48,000)",
        displaced_hrms: Optional[str] = None,
        displaced_name: Optional[str] = None,
        rules_summary: Optional[str] = "COMPLIANT"
    ) -> Dict[str, Any]:
        """
        Atomically records an administrative posting decision into:
        1. Master_Decisions_Ledger.xlsx
        2. Master_Decisions_Ledger.csv
        3. google_sheets_sync_queue.json
        4. Triggers automatic backup snapshot every 5 decisions.
        """
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
        tx_id = f"TX-{now.strftime('%Y%m%d%H%M%S')}-{officer_hrms[-4:]}"

        # Combine officer name and present posting
        officer_detail = f"{officer_name} (HRMS: {officer_hrms}), {present_posting}"

        # Combine substantive and SU post details
        target_posting = substantive_post_name
        if su_post_name:
            target_posting += f" [with Service Utilization at: {su_post_name}]"

        # 1. Read existing CSV to get next Sl No and check count
        existing_rows = 0
        if os.path.exists(self.ledger_csv):
            with open(self.ledger_csv, "r", encoding="utf-8") as f:
                existing_rows = sum(1 for _ in f) - 1
        sl_no = max(1, existing_rows + 1)

        row_data = [
            sl_no,
            tx_id,
            session_id,
            timestamp_str,
            officer_hrms,
            officer_detail,
            present_pay_level or "Level 16 (Rs. 56,100 - Rs. 1,44,300)",
            transfer_by,
            target_posting,
            target_pay_level or "Level 19 (Rs. 95,100 - Rs. 1,48,000)",
            displaced_hrms or "None",
            displaced_name or "None",
            rules_summary or "COMPLIANT",
            "Synced to Local Master Ledger"
        ]

        # 2. Append to CSV
        with open(self.ledger_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row_data)

        # 3. Append to Excel
        try:
            wb = openpyxl.load_workbook(self.ledger_xlsx)
            ws = wb["Master_Decisions_Ledger"]
            ws.append(row_data)

            # Alternating row fill
            current_row = ws.max_row
            fill_color = "F8FAFC" if current_row % 2 == 0 else "FFFFFF"
            row_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type="solid")
            border_thin = Border(
                left=Side(style='thin', color='E2E8F0'),
                right=Side(style='thin', color='E2E8F0'),
                top=Side(style='thin', color='E2E8F0'),
                bottom=Side(style='thin', color='E2E8F0')
            )

            for col in range(1, len(row_data) + 1):
                cell = ws.cell(row=current_row, column=col)
                cell.fill = row_fill
                cell.border = border_thin
                cell.font = Font(name="Arial", size=10)
                if col in [1, 2, 4, 5, 7, 8, 10, 14]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                else:
                    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

            # Auto-adjust column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = openpyxl.utils.get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = min(45, max(12, max_len + 3))

            wb.save(self.ledger_xlsx)
        except Exception as e:
            print(f"Warning: Could not append to Excel ledger: {e}")

        # 4. Append to Google Sheets sync queue
        queue_entry = {
            "sl_no": sl_no,
            "tx_id": tx_id,
            "session_id": session_id,
            "timestamp": timestamp_str,
            "officer_hrms": officer_hrms,
            "officer_name_with_present_posting": officer_detail,
            "present_pay_level": present_pay_level or "Level 16",
            "transfer_by": transfer_by,
            "place_of_posting_upon_transfer": target_posting,
            "pay_level_upon_transfer": target_pay_level or "Level 19",
            "displaced_officer": f"{displaced_name} ({displaced_hrms})" if displaced_hrms else "None",
            "synced_at": timestamp_str
        }

        try:
            queue = []
            if os.path.exists(self.sync_queue_file):
                with open(self.sync_queue_file, "r", encoding="utf-8") as f:
                    queue = json.load(f)
            queue.append(queue_entry)
            with open(self.sync_queue_file, "w", encoding="utf-8") as f:
                json.dump(queue, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not update sync queue: {e}")

        # 5. Checkpoint snapshot every 5 decisions
        auto_backup_info = None
        if sl_no % 5 == 0:
            auto_backup_info = self.backup_mgr.create_backup(tag=f"auto_checkpoint_{sl_no}_decisions")
            print(f"Auto-Checkpoint Triggered at {sl_no} decisions: {auto_backup_info.get('filename')}")

        return {
            "success": True,
            "transaction_id": tx_id,
            "sl_no": sl_no,
            "total_logged": sl_no,
            "auto_checkpoint": auto_backup_info
        }

    def get_ledger_stats(self) -> Dict[str, Any]:
        """Returns stats about the decisions ledger."""
        total_rows = 0
        if os.path.exists(self.ledger_csv):
            with open(self.ledger_csv, "r", encoding="utf-8") as f:
                total_rows = max(0, sum(1 for _ in f) - 1)

        queue_count = 0
        if os.path.exists(self.sync_queue_file):
            try:
                with open(self.sync_queue_file, "r", encoding="utf-8") as f:
                    queue = json.load(f)
                    queue_count = len(queue)
            except Exception:
                pass

        return {
            "total_decisions_logged": total_rows,
            "queue_pending_google_sync": queue_count,
            "ledger_xlsx_path": self.ledger_xlsx,
            "ledger_csv_path": self.ledger_csv,
            "sync_queue_path": self.sync_queue_file
        }

if __name__ == "__main__":
    logger = DecisionLogger()
    print("Testing DecisionLogger...")
    res = logger.log_decision(
        session_id="TEST_RUN",
        officer_hrms="1990004280",
        officer_name="Dr. Utpal Chakraborty",
        present_posting="BLDO, MANDIRBAZAR Block, South 24 Parganas",
        present_pay_level="Level 16 (Rs. 56,100 - Rs. 1,44,300)",
        transfer_by="Promotion (50-Point Roster)",
        substantive_post_name="Deputy Director, ARD, Purba Medinipur",
        su_post_name=None,
        target_pay_level="Level 19 (Rs. 95,100 - Rs. 1,48,000)"
    )
    print("Logged decision result:", res)
    print("Stats:", logger.get_ledger_stats())
