# Session Log 04 — 13–14.09.2026 — Opus batch-2 OCR and parse (Job 01)

Job prompt: `Prompt/20260913_AVD_CIOS_Opus_Job_01_OCR_and_Parse_Batch2.md`.
Mechanical extraction only. Nothing was merged into the 20 master tables; nothing in
`_00_Input_Raw_Sources/` was edited, renamed, moved or deleted.

Written this session (and nothing else):
`02_MASTER_SOURCE_OF_TRUTH/batch2_ocr_text/`, `batch2_tables/`, `scripts/batch2/`,
this log.

---

## Where the work ran, and why

Heavy OCR ran in the cloud container, not in the Mac's Linux VM, as the job prompt
directs. Measured on this corpus in this session:

| Step | Cost |
|---|---|
| Page image via `pdfimages -png` | 1.3 s |
| Pass 1 — Tesseract 5 `tessdata_best`, psm 4, deskew + CLAHE | 3.9 s |
| Pass 2 — Tesseract 5 stock, psm 6, denoise then 2× upscale, Otsu | 3.4 s |
| Pass 3 — RapidOCR PP-OCRv4 | 8.8 s |
| **Throughput, 2 cores** | **~15–18 s per page** |

One change to the recipe, measured not assumed: pass 2 denoises at native resolution
and upscales afterwards. `fastNlMeansDenoising` on the 2× image took 8.1 s; the same
filter on the native image takes 2.1 s and Tesseract reads the same text from it
(944 characters against 931). Everything else is the recipe as handed over.

Agreement between the three passes is measured on characters, not words. RapidOCR
returns a whole line as one run with no spaces, so a word-level comparison scores it as
disagreeing with Tesseract even where both read the page identically.

---

## Task B — 933 departmental-portal employee profiles  ✔ complete

Script `scripts/batch2/b01_darah_profiles.py`, run on the Mac (no OCR needed, files
never left the machine). lxml parser, 4 workers, 43 s for all 933 files.

| Output | Rows |
|---|---|
| `batch2_tables/DARAH_PROFILES.csv` | 933 |
| `batch2_tables/DARAH_POSTINGS.csv` | 3,756 |
| `batch2_tables/DARAH_QUALIFICATIONS.csv` | 1,505 |
| `batch2_tables/DARAH_MATCH.csv` | 933 |

What the 933 pages carry:

- **Every one of the 933 has a date of entry into government service, and every one has
  a date of birth.** This is the cure the previous session hoped for: the master has 497
  officers with no entry date.
- 906 of the 933 HRMS ids are in the closed `PERSONS` set; 27 are not.
- Of those 27: **23 file names carry the portal's own 11-digit Employee Code, not a
  10-digit HRMS id.** Taking "the last 10 digits" of an 11-digit code would invent a
  value, so `HRMS_ID_FROM_FILENAME` is `Under verification` on those 23 rows and the
  page's own Employee Code is carried in `EMPLOYEE_CODE_ON_PAGE`. The remaining 4 have a
  10-digit id that is simply not in `PERSONS`. **No officer was created.**
- 3 pages have no posting table at all; 84 have no academic-qualification table.
- 882 of the 906 matched ids also agree on surname. **24 do not** and are flagged
  `SURNAME_AGREES = N` for eye check. Most are spelling or married-name variants
  (`Mandal`/`Mondal`, `SenGupta`/`Sen Gupta`, `Swapna Rooj` / `Swapna Rooj (Sikder)`),
  but at least one is a different person under the same id and must be resolved by hand:

  > HRMS **1994000172** — the portal page reads **Dr. Sabin Majumder**, `PERSONS` holds
  > **DR (MRS) SAMPA BHATTACHARYA**.

- The portal does not print an "as on" date. `CAPTURED_AT` is the file's modification
  time — the day the page was saved, 10–11.07.2026 — and that is stated, not inferred.
- Spouse and address fields were taken exactly as printed. Nothing about any spouse was
  looked up anywhere.

---

## Task A — Gradation List memo 3768 dt. 24.09.2025  ✔ complete

**The document.** Notification No. 3768 - AR&AH/AD/O/3A-09/2025 dated 24.09.2025,
Government of West Bengal, Animal Resources Development Department, AR&AH Branch,
signed **Sd/- B. Sikdar, Special Secretary**. It publishes the **Final Gradation List**
of officers **other than Agriculture Expert** borne under the **West Bengal Animal
Husbandry & Veterinary Service**, **as on 01.09.2025**, superseding the Provisional
Gradation List published vide Memorandum No. 3001-AR&AH/3A-09/2025 dated 21.07.2025.
The notification states that corrections, **inclusions and deletions** were made after
considering claims and objections. 39 scanned pages, no text layer.

**OCR.** All 39 pages, all three passes. **Mean three-way agreement 74.8%**
(page range 53–86%). Lower than the 86.6% of the first corpus because these are
dense ruled tables at native scan resolution, where the three engines break lines
differently.

**Parsing.** `scripts/batch2/grad_geom.py` re-reads each page as word boxes
(Tesseract TSV, best model, psm 4) and `scripts/batch2/grad_parse.py` cuts the table by
x-position. Two things had to be got right:

1. **Rows are fitted as sloping lines, not flat bands.** After deskew these pages still
   lean a fraction of a degree. A row is 1,600 px wide, so the officer's name at x≈400
   sits up to 20 px off the y of the HRMS id at x≈760 — more than the row pitch. Fitting
   `y = m·x + c` through each row's own anchors recovered names on the majority of rows
   that a flat y-band had lost.
2. **Three independent seeds per printed line** — the 10-digit HRMS id, the dd-mm-yyyy
   dates, and the honorific that opens every name — so a line survives the failure of
   any one of them.

**Columns the memo actually prints**, per section:
`Sl. No. | Name of the Officers | HRMS ID | Qualification | Date of Birth (DD/MM/YR) |
Date of Entry in WBAH&VS (DD/MM/YR) | Category | Remarks`.
On the four grade sections of page 2 the sixth column instead reads *Date of Entry to
the post of &lt;grade&gt;*; that header text is carried on every row in
`OTHER_COLUMNS_RAW` so the meaning of `DATE_OF_ENTRY_RAW` is never lost.
`QUALIFICATION_RAW` is a printed column not named in the job prompt and was added with
the `_RAW` suffix. `DATE_OF_APPOINTMENT_RAW` and `PRESENT_POSTING_RAW` are
`Under verification` on every row — **the memo does not print those columns**.

**`batch2_tables/GRADATION_3768_ROWS.csv` — 1,135 rows.**

| Identity | Rows |
|---|---|
| Printed HRMS id found in `PERSONS`, surname agrees | 807 |
| Printed HRMS id found in `PERSONS`, name column not readable on that line | 106 |
| Printed HRMS id found in `PERSONS`, surname read differs — eye check | 87 |
| Id not in `PERSONS`, name matched under the surname guard | 72 |
| No match — goes to `GRADATION_3768_UNMATCHED_NAMES.csv` | 63 |

1,000 rows therefore carry an HRMS id that exists in the master. **No officer was
created.** Name votes across the three passes: 3 votes 393, 2 votes 444, 1 vote 189,
0 votes 109. A 1-vote or 0-vote row is a lead, not a fact.

Dates are copied as printed. `DOB_ISO` is filled on 388 rows and `DATE_OF_ENTRY_ISO` on
248 — only where **all three passes read the same digits** on the line carrying that
HRMS id. Everywhere else the ISO column is `Under verification` while the `_RAW` column
still shows what was printed.

**Row-count reconciliation, as required.** The memo prints no total. Its sections are:
Director ARD 1 row, Additional Director ARD 1, Joint Director ARD 5, Deputy Director ARD
13 (all on page 2), then one long section — *Veterinary Officer / Block Livestock
Development Officer / Assistant Director, ARD* — running from page 3 to page 39 whose
printed serials reach **1203** on the last page. Taking each page's own legible serial
run, the 37 pages of that section span **1,216 serial numbers** and **1,114 rows were
extracted from them — a shortfall of 102 lines, 8.4%.** Those lines are ones where the
id, both dates and the honorific all failed to register on a badly-scanned row. They are
not recorded anywhere as blanks; they are simply absent, and the 8.4% is stated here so
the merge session knows the table is not complete. Only **730 of the printed serials
were legible at all**, so `GRAD_SL` is `Under verification` on 405 rows even where the
officer is identified — the serial column sits hard against the table rule and Tesseract
frequently glues it to the honorific.

Page 1 is the notification text and carries no table rows.

**Merge caution for the next session:** this list gives a *date of entry into WBAH&VS*
and the Task B profiles give a *date of entry into government service*. They are not the
same field and must not be folded together.

---

## Task C — 382 orders, rules and acts

### Triage  ✔ complete
`scripts/batch2/b02_triage_orders.py` → `batch2_tables/ORDERS_BATCH2.csv`,
**382 rows, one per file in `ARD_Orders_Rules_Acts/`** (323 pdf, 22 jpeg, 19 doc,
13 docx, 5 jpg). `SHA256` and `ORIGINAL_NAME` are taken from
`_register/ARCHIVE_REGISTER.csv`; the order date comes from the archive file name where
the name carries one and is `Under verification` where it carries `00000000`.

| Tier | Files | What |
|---|---|---|
| 1 | 331 | every PDF of 30 pages or fewer (271, 1,424 pages) + all 32 doc/docx + all 27 jpeg/jpg + 1 PDF whose page count is unreadable |
| 2 | 9 | scanned compendiums and annual reports over 30 pages |
| 3 | 42 | statutory reference books, indexed only |

**One triage question was put to the owner and answered on 13.09.2026.** Twenty-five
files over 30 pages are statutory reference books of the same kind as the Tier 3 list in
the job prompt but are not named in it — WB Financial Rules, IPC, West Bengal
Secretariat Manual, Death-cum-Retirement Benefit Rules, ROPA, WBHS forms and rate lists,
pension and Government Accounting Rules, WBSCCAR, ZP/PS Finance & Accounts Rules — plus
one scanned 177-page file named only `ARD_17` (2016). **The owner ruled: sweep only
`ARD_17`; index the other 24 with no text extracted.** `ARD_17` is therefore in Tier 2
and the other 24 are in Tier 3, each carrying that ruling in its `NOTE` column.

One PDF is damaged — `pdfinfo` cannot read its cross-reference table:
`20260604_193328_ARD_Order_00000000_General_Orders_Right_to_Information_Application_Procedure_0.25_Mb.pdf`.
It is in Tier 1 and its `PAGES` is `Under verification`.

### Tier 1 OCR  — stopped part-way on the owner's instruction, 13.09.2026

**43 of the 331 Tier 1 files were OCR'd (86 pages, all three passes) before the owner
stopped the run** because the remaining time was too long. Everything produced up to that
point is saved in place; nothing is half-written.

- Text and word boxes for the 43: `batch2_ocr_text/<archive file stem>/`
- Checkpoint: `scripts/batch2/tier1_progress.jsonl` — one JSON line per finished
  document. Re-running `ocr_files.py` with the same arguments skips these 43 and
  continues. Two documents that were mid-page when the run was killed had their partial
  folders deleted, so the checkpoint and the folders agree exactly.
- Remaining work lists written for the hand-off:
  `scripts/batch2/tier1_remaining.list` (288 files, 1,365 known pages plus 17 doc/docx
  whose page count follows conversion) and `scripts/batch2/tier2.list` (9 files,
  1,930 pages).

**Why it was going to take ten hours.** The container has two cores. Three passes over a
page cost about 22 s of CPU, so the ceiling is roughly 11 s per page, and Tier 1 plus
Tier 2 is about 3,300 pages. Three measured changes were made during the run and are in
`ocr3.py` for whoever finishes it:

| Change | Before | After | Text lost |
|---|---|---|---|
| Denoise before upscaling, not after | 8.1 s | 2.1 s | none (944 vs 931 characters) |
| Cap pass 1 at 2600 px, pass 2 at 1700, pass 3 at 1600 | 32.9 s/page | 22.7 s/page | pass 1 99.9% identical, pass 2 100.0% |
| One thread per worker (OMP, OpenCV, onnxruntime) | 25 s/page | ~11 s/page | none |

A 300 dpi A4 render is 3509 × 2480 and none of the three engines uses that resolution;
that was where two thirds of the time was going.

**Tables rebuilt from the 43 documents** (`scripts/batch2/movements.py`):

| Table | Rows |
|---|---|
| `batch2_tables/ORDERS_BATCH2.csv` | 382 (43 now carry `TEXT_EXTRACTED = Y`) |
| `batch2_tables/ORDER_MOVEMENTS_BATCH2.csv` | 2 |
| `batch2_tables/UNMATCHED_NAMES_BATCH2.csv` | 14 |
| `batch2_tables/ESTABLISHMENT_LEADS_BATCH2.csv` | 12 |

Only 2 movement rows because the 43 files OCR'd first were the *smallest* files in the
corpus — the driver works smallest-first — and they are almost all general orders, forms
and rules that name no cadre officer. The transfer and promotion orders that carry the
officer names are larger files and are all still in the remaining 288.

One deliberate difference from the master `ORDER_MOVEMENTS` table: the master leaves an
unknown cell empty, batch 2 writes `Under verification`, as the job prompt requires.
`DISTRICT_RESOLVED` was added to carry the split-district verdict.

### Archive integrity — verified

| Register | Files | Result |
|---|---|---|
| `_register/ARCHIVE_REGISTER.csv` | 1,462 | 1,462 OK, 0 changed, 0 missing |
| `_register/MOVE_REGISTER.csv` | 1,122 | 1,122 OK, 0 changed, 0 missing |

**Nothing under `_00_Input_Raw_Sources/` was altered by this job.** Evidence:
`scripts/batch2/archive_hash_progress.jsonl` and `scripts/batch2/move_register_check.json`.

### Hand-off

The remaining OCR is handed to Google Antigravity running on the Mac. The job prompt is
`Prompt/20260914_AVD_CIOS_Antigravity_Job_02_Remaining_OCR.md` — it carries the measured
recipe, the engine set-up, the resume commands, the column lists, the hard rules and the
acceptance table, and it names the folders to write into. The scripts it calls are already
in `scripts/batch2/`.

### Acceptance table — as it stands at hand-off

| Check | Expected | Now |
|---|---|---|
| Files in `ARD_Orders_Rules_Acts/` = rows in `ORDERS_BATCH2.csv` | 382 = 382 | **382 = 382 ✔** |
| Every Tier 1 file has a merged text file | 331 | **43 — outstanding, handed to Job 02** |
| `DARAH_PROFILES.csv` rows | 933 | **933 ✔** |
| Every HRMS_ID written in a batch-2 table exists in `PERSONS` | 0 exceptions | **0 exceptions ✔** |
| No cell empty, "N/A", "-", "NOT ON RECORD" | 0 | **0 ✔** |
| No new officer created | 0 | **0 ✔** |
| `GRADATION_3768_ROWS.csv` = rows printed on the 39 pages | stated and reconciled | **1,135 extracted against about 1,236 printed; 8.4% of the main section not recovered — stated in the Task A section above ✔** |
| Nothing under `_00_Input_Raw_Sources/` changed | 0 changes | **0 changes, 2,584 files re-hashed ✔** |

### Housekeeping — cleared
`scripts/batch2/_stage/` held 518 MB of transfer tars used only to move files between
this Mac and the cloud container. The owner granted deletion and the folder was removed.
Nothing else was deleted.
