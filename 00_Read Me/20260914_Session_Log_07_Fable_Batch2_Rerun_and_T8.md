# Session Log 07 — 14.09.2026 — Fable: Job 03 executed (batch-2 re-ingest, ledger and truth tables rebuilt)

## Outcome
The evidence ledger and truth tables were rebuilt on the corrected batch 2; the master SQLite and the master workbook now agree (42 tables each); the newly archived orders' transfers are on a new sheet T8.

## Done (in order)
1. Verified Opus's Job 03 claims against disk before acting: ORDER_MOVEMENTS_BATCH2 530 rows, UNMATCHED 1,691, LEADS 374, 340 orders with text, gradation ISO dates 404 DOB / 293 entry. Correct.
2. Versioned master (`20260914_<hhmm>_..._pre-batch2-rerun.sqlite`, workbook likewise). s17 re-run (10 tables). s18 patched to read `DOB_ISO` / `DATE_OF_ENTRY_ISO` from the repaired gradation table (three-pass agreement only) and to drop the UNUSABLE marking; EVIDENCE now 32,717 rows. s19 patched: T8_ORDER_MOVEMENTS_BATCH2 (530 rows; 118 with named postings; 120 flagged for eye-check), T1 gains LATEST_ORDER_BATCH2_* (353 officers), empty cells replaced by explicit phrases.
3. New script `s20_reemit_master_xlsx.py`: master .xlsx re-emitted from SQLite (previous copy kept as `*_pre-batch2-reemit.xlsx`).
4. Verification: frozen tables intact (1,617 / 1,794 / 2,174 / 462); every HRMS_ID in T8 exists in PERSONS; zero empty/N-A cells across all nine T-tables; T4 241 of 242 linked.
5. Resolution now: DOB VERIFIED 1,066 (DISPUTED 23); entry into WBAH&VS VERIFIED 604, UNDER VERIFICATION 511, DISPUTED 17, no evidence 485; among in-service officers only 63 have no entry date at all.
6. The 1995 BLDO annexure OCR checked: pages 2–23 unreadable (agreement 6–8 %, landscape scan). Job 04 written for a rotation-aware re-OCR and transcription (`Prompt/20260914_AVD_CIOS_Job_04_1995_BLDO_Annexure_ReOCR.md`). T3 stays derived until that table exists.

## Findings for the owner
- 17 entry-date disputes are one systematic difference: the gradation list prints 01.01.1996 for the 1995 recruitment batch while the officers (and unit coordinators) give 15.09.1995. Likely both are true (joining vs. cadre entry) — needs one decision on which the promotion list uses.
- T8 gives, for the first time, the printed "present posting → posting on transfer" pairs from the 28.11.2024, 21.03.2025 and 07.01.2026 orders. NEEDS_EYE_CHECK = Y rows must be read against PRINTED_LINE before use.

## Not done / skipped
- TENURE_TIMELINE / TENURE_SPELLS were not rebuilt with the batch-2 moves (the tenure scripts belong to the OCR-1 pipeline); T8 carries the moves instead. Folding them in is a later step once eye-checks are done.
- 1995 annexure not parsed (unreadable OCR — Job 04).
- Manual recommendation sheets remain quarantined.
