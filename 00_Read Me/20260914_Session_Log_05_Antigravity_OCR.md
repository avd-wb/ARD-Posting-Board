# Session Log 05 — 14.09.2026 — Antigravity Batch-2 OCR, Tier 2 Sweep & Table Rebuild (Job 02)

Job prompt: `Prompt/20260914_AVD_CIOS_Antigravity_Job_02_Remaining_OCR.md`.  
Preceding log: `00_Read Me/20260914_Session_Log_04_Opus_OCR_Batch2.md`.  
Run on: local macOS workstation (`nrss-mac-local`), 8 CPU cores, 7 parallel OCR worker jobs.

---

# 🚨 CRITICAL DISCOVERY: PRE-2025 SANCTIONED POSTS & ESTABLISHMENT RESTRUCTURING ORDERS FOUND

As requested in §4 of the job specification, the corpus was scanned for pre-2025 establishment, sanctioned strength, post creation, and abolition orders. **Three foundational pre-2025 establishment orders were discovered**:

1. **`20260604_193856_ARD_Order_19950504_General_Orders_19950504_BLDO_set_up_formation_2.13_Mb.pdf` (Pages 1–23)**
   - **Order**: ARD Dept Memorandum dated **4th May, 1995** (implementing Dr. Biplab Dasgupta Committee recommendations following Notification No. 3096-AH/3M-46/90 dt. 04.11.1991).
   - **Content**: Reallocation and redesignation of sanctioned posts of the two erstwhile Directorates. **Explicitly establishes and redesignates 340 sanctioned posts across individual Blocks** as Block Livestock Development Officers (BLDOs) to be manned by officers of the WBAH&VS / WB Junior Veterinary Service.
   - **Annexure (Pages 2–23)**: Exhaustive block-by-block listing of all 340 sanctioned BLDO positions across the districts of West Bengal.

2. **`20260604_193832_ARD_Order_20151104_General_Orders_20151104_Order_for_BLDO_set_up_0.09_Mb.pdf` (Pages 1–4)**
   - **Order**: Notification No. **2036-AR&AH/3A-03/2009 dated 04.11.2015**.
   - **Content**: Block-level administrative restructuring:
     - Formally creates the standard BLDO block set-up: BLDO (1), VFS (1), UDC/LDC (1), Gr-D (1), Night Guard (1).
     - **Specific abolition list**: To create 138 UDC, 203 LDC, 341 Gr-D, and 341 Night Guard posts, **an equivalent number of existing posts were formally abolished** from establishments including Central Semen Bank & CSAHF Salboni, Haringhata Farm, State Livestock Farm (SLF) Kalyani, and erstwhile Superintendent of Livestock offices (detailed in Annexures 1, 2 & 3).

3. **`20260604_193626_ARD_Order_20130101_General_Orders_20130101_Compendium_of_Important_Government_Orders_0.85_Mb.pdf` (264 pages)**
   - **Content**: Compendium compiling key Finance Department and ARD Department establishment notifications, including Memo No. 1488-F(P) on creation and filling of posts, ban on contractual posts against non-sanctioned posts, and promotional rules.

---

## 1. Summary of Execution

### Step A: Tier 1 Remaining OCR (Completed)
- **Scope**: 288 files remaining from Job 01 (out of 331 total Tier 1 files).
- **Execution**: 3-pass OCR (Tesseract 5 `tessdata_best` TSV, Tesseract 5 stock Otsu, RapidOCR PP-OCRv4 ONNX) across 7 cores.
- **Total Tier 1 Files**: 331 files (1,660 pages).
- **Agreement Metrics**: Mean 3-way character agreement: **86.61%** (median **93.55%**).
- **Deliverables**: Generated `batch2_ocr_text/<stem>/` containing `page_NNN_pass1.txt`, `page_NNN_pass1.tsv`, `page_NNN_pass2.txt`, `page_NNN_pass3.txt`, merged `<stem>.txt`, and `_pages.json`.

### Step B: Tier 2 Compendium Sweep & 3-Pass Deep OCR (Completed)
- **Scope**: 9 compendiums and annual reports (1,930 pages total).
- **Pass 1 Sweep**: All 9 files, 1,930 pages processed with Pass 1 (Tesseract 5 `tessdata_best` TSV mode).
- **Keyword Scan**: Scanned all 1,930 pages for 11 establishment keywords (`sanctioned`, `cadre strength`, `creation of post`, `abolition`, `abolished`, `re-designation`, `restructur`, `Deputy Director`, `Block Livestock Development`, `Veterinary Officer`, `Additional Block`).
- **Hit Pages**: **73 distinct pages** matched keywords.
- **Deep 3-Pass Re-run**: All 73 hit pages were re-run through full 3 passes (`--passes 123`).
- **Agreement on Hit Pages**: Mean 3-way agreement: **92.40%** (median **96.18%**).
- **Updates**: Re-merged `<stem>.txt` and updated `_pages.json` for all touched Tier 2 documents.

### Step C: Rebuilding Batch-2 Tables (Completed)
- Backed up previous output tables with timestamps (`_20260914_101445` / `_20260914_101449`).
- Executed `scripts/batch2/movements.py` over `batch2_ocr_text/` with closed `PERSONS` set (`csv/20260913_AVD_SOT_02_PERSONS.csv`) and master orders (`csv/20260913_AVD_SOT_10_ORDERS.csv`).
- Output tables generated in `batch2_tables/` (UTF-8 with BOM):
  - **`ORDERS_BATCH2.csv`**: 382 rows (100% of corpus accounted for; metadata and duplicate links populated).
  - **`ORDER_MOVEMENTS_BATCH2.csv`**: 520 rows (495 distinct officers identified under strict surname guard; match methods: 438 exact, 82 fuzzy).
  - **`UNMATCHED_NAMES_BATCH2.csv`**: 2,104 rows (candidate names not matching the closed set or failing surname guard).
  - **`ESTABLISHMENT_LEADS_BATCH2.csv`**: 374 rows (keyword hits with 120-character contextual snippets).

---

## 2. Table Row Counts Summary

| Table | Status | Rows | Note |
|---|---|---|---|
| `batch2_tables/ORDERS_BATCH2.csv` | Rebuilt | 382 | 1 row per corpus document; columns populated from OCR & triage |
| `batch2_tables/ORDER_MOVEMENTS_BATCH2.csv` | Rebuilt | 520 | 495 distinct cadre officers identified |
| `batch2_tables/UNMATCHED_NAMES_BATCH2.csv` | Rebuilt | 2,104 | Unmatched names recorded with vote count & reason |
| `batch2_tables/ESTABLISHMENT_LEADS_BATCH2.csv` | Rebuilt | 374 | Contextual establishment leads |
| `batch2_tables/DARAH_PROFILES.csv` | Job 01 | 933 | Intact |
| `batch2_tables/DARAH_POSTINGS.csv` | Job 01 | 3,756 | Intact |
| `batch2_tables/DARAH_QUALIFICATIONS.csv` | Job 01 | 1,505 | Intact |
| `batch2_tables/DARAH_MATCH.csv` | Job 01 | 933 | Intact |
| `batch2_tables/GRADATION_3768_ROWS.csv` | Job 01 | 1,135 | Intact |
| `batch2_tables/GRADATION_3768_UNMATCHED_NAMES.csv` | Job 01 | 63 | Intact |

---

## 3. Exceptions, Unverified Items & Notes

1. **Damaged PDF (1 file)**:
   - `20260604_193328_ARD_Order_00000000_General_Orders_Right_to_Information_Application_Procedure_0.25_Mb.pdf` is corrupt (corrupt xref table and trailer dictionary). `pdfinfo` and `pdftotext` both fail. Documented in progress log with error; placeholder merged file written with `PAGES: 0` and error note.
2. **Tier 3 Statutory Books (42 files)**:
   - Statutory manuals and acts over 30 pages (e.g. WB Financial Rules, IPC, Secretariat Manual) indexed in `ORDERS_BATCH2.csv` with `TEXT_EXTRACTED = N` and owner ruling note per 13.09.2026 instruction.
3. **Missing Values**:
   - Strictly represented by the literal string `Under verification` across all generated CSV tables. Zero empty cells, dashes, or `N/A`s exist.
4. **Surname Guard & Officer Count**:
   - Exactly zero new officers were added to `PERSONS`. The set remains closed at 1,617. All matches required exact surname equality.

---

## 4. Archive Integrity & Verification

Both archive registers were re-hashed against `_00_Input_Raw_Sources/`:
- `b04_verify_archive.py`: **1,464 files OK**, 0 changed, 0 missing (`FINAL: {'OK': 1464}`).
- Move register verification: **1,122 files OK**, 0 changed, 0 missing (`OK: 1122`).
- Total archive files verified: **2,586 files** — absolute zero mutations to `_00_Input_Raw_Sources/`.

---

## 5. Acceptance Table (§7)

| Check | Expected | Actual | Status |
|---|---|---|:---:|
| Files in `ARD_Orders_Rules_Acts/` = rows in `ORDERS_BATCH2.csv` | 382 = 382 | 382 = 382 | **PASS** |
| Every Tier 1 file has a merged `<stem>.txt` | 331 = 331 | 331 = 331 | **PASS** |
| Every Tier 2 file has pass-1 text for every page | 9 files, 1,930 pages | 9 files, 1,930 pages | **PASS** |
| `HRMS_ID` values written in any batch-2 table that are not in `PERSONS` | 0 | 0 | **PASS** |
| Cells in any batch-2 CSV that are empty, `N/A`, `-` or `NOT ON RECORD` | 0 | 0 | **PASS** |
| New officers created | 0 | 0 | **PASS** |
| Files under `_00_Input_Raw_Sources/` whose SHA-256 changed | 0 | 0 (2,586 verified) | **PASS** |

