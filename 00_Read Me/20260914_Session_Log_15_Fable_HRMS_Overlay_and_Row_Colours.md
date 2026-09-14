# Session Log 15 — 14.09.2026 — Fable 5.1 — HRMS overlay (Director/Addl Director missing) + row colours

## Owner's two mid-session requests
1. "Director Dr Nikhil Shit and Addl Director Dr Prabir Kumar Pathak are absent" from the vacancy finder.
2. Review sheet: colour rows — white = finalised, all flags sorted; red = serious; yellow = moderate action.

## Finding (1)
Both are in the SOT (PERSONS from HRMS 08.09.2026): 1992005664 DR NIKHIL KUMAR SHIT, Director AH&VS, DOR 31.05.2027;
1994001279 DR PRABIR KUMAR PATHAK, Additional Director ARD, DOR 28.02.2030 (gradation 3768 serials 1 and 2).
They were absent from List 1 / the app because the Directorate HQ sent NO field return, so every Directorate line was
NO_RETURN_RECEIVED and OCCUPANCY (frozen) has no row for them. 36 in-service HRMS officers had no OCCUPANCY row at all.

## Fix (1) — scripts/s30_hrms_overlay.py → derived table HRMS_OVERLAY (+ 04_LISTS_FROM_SOT/20260914_1419_AVD_OVL_HRMS_Overlay_36.csv)
Rule: an in-service officer with no field-return row is placed on the Order-1809 line that his HRMS designation + office name
point to, only if that line is NO_RETURN_RECEIVED or VACANT; status FILLED_PER_HRMS, basis "HRMS extract 08.09.2026 — no field
return". Owner decisions win (Tuhin Chakraborty → JD line Purba Bardhaman P1176; Rupam Barua → DD line Hooghly P1100).
Placed 17 of 36: P0001 Director = Nikhil Kumar Shit; P0003 Addl Director = Prabir Kumar Pathak; P0012/P0013 JD Dte HQ = Utpal
Kumar Karmakar / Uttam Kumar Biswas (F4 still open — HRMS DDO code is Nadia's); P0072/P0073 AD HQ = Debasis Mukherjee / Rajat
Kumar Roy; P0070 AD Fodder = Pritam Goura; IAH&VB VR&I lines P0122–P0124 = Pralay Mandal / Abhrakanti Roy / Sourav Mandal;
Training Institute P1667 (DD/Principal) = Shanti Dev Bishayi, P1668/P1669 = Swapan Sheet / Dipak Kumar Maity; Salboni JD P0194 =
Mintu Chowdhury; Murshidabad AD VR&I P0658 = Sanjoy Goswami. Not placed (listed, never guessed): 11 VOs (Order 1809 gives VO
lines to a district set-up, not a named block; 2 are on deputation with Kolkata Police), 6 ADs whose office lines are all
already filled (SPF Tollygunge 2, IAH&VB Vety 2, Dte HQ Vety 1, Tushar Kanti Samanta JD Zone-II has no JD line), 2 BLDOs.
s24 patched to apply the overlay (List 1 now: FILLED 1143, NO_RETURN 578, VACANT 312, FILLED_PER_HRMS 17 …); s27 re-run;
app legend/filter gained FILLED_PER_HRMS; redeployed https://ard-review-board.vercel.app (14:37).
NOTE: HRMS_OVERLAY table exists in the cloud copy of the SQLite; on the Mac run `NOCOPY= COPYBACK=1 python3 s30_hrms_overlay.py`
(or s30 then scripts/copyback.sh) to add it — the mount was too slow today (a >170 s call reboots the Cowork VM and wipes ~/work).

## Fix (2) — s28 v2: severity column
New columns AU "রং (লাল/হলুদ/সাদা)" and AV "রং-এর কারণ"; conditional formatting colours the whole row from AU (red F4CCCC /
yellow FFF2CC / white). Rule: লাল if any serious flag (identity not in HRMS, no free DD line, not on roster, displacement chain
unknown, retirement date missing, roster/district mismatch); সাদা if owner decision recorded and no action flag left (data-gap
notes such as gender/category/AVD-membership unverified do not block white), or no flag at all; else হলুদ.
Counts now: লাল 28 · হলুদ 231 · সাদা 78. Reviewer columns no longer yellow-filled (colour is reserved for severity).
Live sheet updated in place (same id) with File → Import → "Replace spreadsheet" from 20260914_1435_AVD_GSH_Review_Sheet_337.xlsx
(after a full cell-by-cell check that nobody had edited it, and a backup copy "20260914_1439_backup_before_colour_rules_…" in
the backups folder). s29 now reads A1:AV338 and can write AU/AV from severity_updates.json; hourly task prompt updated.

## Open
F1–F5, Q40–79 as before; 19 HRMS officers without a line (list above); Animesh Sikder is returned by IAH&VB but linked to the
Dte HQ Addl Director line P0002 (IAH&VB's own Addl Director line P0129-ish shows NO_RETURN) — to swap when the owner confirms.
