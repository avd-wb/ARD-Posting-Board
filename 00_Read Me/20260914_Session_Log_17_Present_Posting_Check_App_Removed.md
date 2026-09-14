# Session Log 17 — 14.09.2026 (late) — LLM — present-posting check (s31), review app removed

## Owner
- The review app is no longer wanted: https://ard-review-board.vercel.app removed from Vercel (project deleted; URL now 404).
  https://ard-posting-board.vercel.app (the other board) untouched — stays published.
- All work now on the Google Sheet 20260914_AVD_GSH_Review_Sheet_LIVE only.
- "Many present postings have flaws — Dr Tapan Sadhukhan is AD (DI) Hooghly, the sheet said IAH&VB. Check the list thoroughly."

## Finding
s25 had kept the present posting as printed in the AG list wherever it disagreed with the master (flag "sheet kept, check").
Dr Tapan Sadhukhan (1993000949): HRMS 08.09.2026 = AD (DI), DDO office DD ARD & PO Hooghly; HQ status 01.07.2026 = Hooghly;
Hooghly return 20.08.2026 = "Assistant Director, ARD (DI), Hooghly" — the AG list had him as JD IAH&VB Kolkata. Owner is right.

## s31_present_posting_check.py (new) — SOT is the authority for present posting
Compared every row's present-posting cells with the preference form, HRMS pay office, HQ status and the district returns.
- District-level errors corrected (all sources agree, AG list differed): 4 — Tapan Sadhukhan (Kolkata→Hooghly, AD (DI)),
  Bharat Chandra Haldar (N24P→Purulia: AD VR&I Check Post Jhalda, SU at SPF Gobardanga), Suchitra Bhujel (Darjeeling→Siliguri,
  AD (DI)), Sadananda Das (Dakshin Dinajpur→Purba Bardhaman, AD (Vety) CMS). SU FINAL re-derived for 2 of them (no owner decision).
- Present SU filled from the returns where the sheet had none: 7.
- Pay office ≠ physical place (service utilisation, not an error): noted, sheet kept (e.g. Soumen Ghosh, Partha Sarathi Sengupta,
  Ratanlal Biswas, Narayan Chandra Sadhukhan, Sanjit Bhowmick, Sumit Chowdhury, La Tshering Bhutia).
- Same district but the return names a DIFFERENT AD post than the sheet (Management / SA / DI vs Vety / VR&I / Fodder): 15 rows
  flagged CHECK (yellow) — matters because AD (Management), AD (SA), AD (C&DD) are abolished posts: Tapas Sarkar, Samar Kumar
  Ghosh, Debasis Jana, Debaprasad Mondal, Ashok Kumar Patra, Ishita Ghosh, Manoj Kumar Biswas, Sudhangsu Sekhar Das, Damodar
  Mandal, Saumindranath Basak, Bhaskar Prasad Maji, Sandip Das, Narayan Mondal, Debdulal Sana, Pradip Kr. Panja.
- Report: 04_LISTS_FROM_SOT/20260914_1538_AVD_CHK_Present_Posting_Check_337.csv; master 20260914_1538_AVD_MPT_…_337.csv
  (new column "Present posting — source check (14.09.2026)", also last column AX of the review sheet).
- Review sheet rebuilt: 20260914_1538_AVD_GSH_Review_Sheet_337.xlsx — সাদা 301 · হলুদ 34 · লাল 2 (copied to the Drive outbox).

## Not done
The live sheet was NOT replaced this time: Drive shows it was edited at 15:42 UTC (21:12 IST) after the last import, and the Chrome
window with the sheet was hidden, so the cell-by-cell "nobody has written" check could not be run. To apply: open the sheet in
Chrome (visible), then File → Import → My Drive → 20260914_1538_AVD_GSH_Review_Sheet_337.xlsx → Replace spreadsheet — after
copying any reviewer comments out, or tell the LLM what was edited and it will merge.
