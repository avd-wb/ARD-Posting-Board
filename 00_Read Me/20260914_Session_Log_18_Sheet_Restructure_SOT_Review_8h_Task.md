# Session Log 18 — 14.09.2026 (night) — LLM — sheet restructured, full SOT data review, 8-hourly task

## Owner instructions (14.09.2026 ~21:30 IST)
Replace the live sheet now; five reviewer columns → one "Comments / Answers" (any answer there is final); 8-hourly checks until
16.09.2026 then manual; remove 19 columns (LLM status, রং, রং-এর কারণ, AVD member basis, Roster link basis, LLM verification,
Owner decision (chat), Comments from CAG, Administrative Remarks, Administrative Directives & Remarks, Executive directive,
Re-anchor basis, Substantive DD post FINAL, DOJ source, Office Code, DDO Code, Two-year rule, Gender, Name as in HRMS);
review all sheet data against the SOT; share as a published view-only sheet (no download/copy/modify, password entry, DRAFT watermark).

## Done
- s32_sot_data_review.py: every row's name, category, retirement date, DOJ, designation, roster serial and AVD flag compared
  with T1/T4/PERSONS/AVD register. Names, retirement dates and roster serials all agree (spelling variants already approved).
  Filled from verified SOT values: AVD flag 11 rows, category 5, DOJ 4. Notes only: 1 DOJ disputed (Subrata Pramanik), 1
  designation (Ashim Raj Rana VO vs HRMS DVO). SERIOUS: Sl 308 Dr. Sukanta Roy 1995000213 — HRMS says Retired 31.10.2025,
  yet the AG list carried him as "Displacement due to post abolition" → red. Report 20260914_1620_AVD_CHK_SOT_Data_Review_337.csv.
- s28 v4: columns dropped as instructed; "Transferred Substantive Post (Level 19)" now carries the FINAL (re-anchored/decided)
  pay post so nothing final is lost; single column Y "Comments / Answers"; row colour is a static fill (লাল 3 / হলুদ 34 / সাদা 300)
  since the colour columns are gone; Justification = column Z; source-check = AA. 27 columns.
- The owner's test answers found in the old sheet (written 21:12 IST) were carried over into "Comments / Answers" and logged in
  04_LISTS_FROM_SOT/REVIEWER_COMMENTS_LOG.csv: Nil Ratan Kole (দেবী দা + Baccha: সুপারিশ ক), Swarup Mondal (দেবী দা: সুপারিশ ক),
  Somen Chatterjee (দেবী দা: সুপারিশ ক), Partha Sarathi Sengupta (দেবী দা: SU at ET Lab, Haringhata).
- Live sheet replaced in place from 20260914_1621_AVD_GSH_Review_Sheet_337.xlsx (backup "20260914_2153_backup_before_single_comments_column_…").
- Scheduled task now "ARD Review Sheet — 8-hourly check (until 16.09.2026)", cron 2 */8 * * * UTC (05:32 / 13:32 / 21:32 IST):
  backup → read column Y → log new answers → report; it never edits the sheet; it switches itself off after 16.09.2026.
  s29 reads A1:AA338 and the single comments column; snapshot reset to the new sheet.
- Master csv of record: 20260914_1620_AVD_MPT_Master_Promotion_Transfer_Sheet_337.csv (keeps every dropped column).

## Sharing — what Google Sheets can and cannot do
Can: share with named Google accounts as Viewer, with "viewers can download/print/copy" switched OFF, and a DRAFT banner (title /
frozen header). Cannot: a password (Sheets has no password gate — access is by Google account or by link), a true watermark.
A password + watermark is possible only as a PDF export (password-protected, DRAFT watermark) — but then nobody can answer in it.
Owner to say which persons (emails) get Viewer access, or whether a PDF is wanted.
