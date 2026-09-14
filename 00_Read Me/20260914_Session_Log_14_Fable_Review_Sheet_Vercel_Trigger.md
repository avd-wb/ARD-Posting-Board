# Session Log 14 — 14.09.2026 — Fable 5.1 — Reviewers' Google Sheet, Vercel app, hourly sync task

## Done
1. `05_REVIEW_APP/index_vercel.html` + `04_LISTS_FROM_SOT/app_data.json` (s27, 337 officers, 2,174 vacancies, floating F1–F5) deployed
   from `05_REVIEW_APP/site/` with the Mac's Vercel CLI (team team_zHzO2gLFtLuGYCzvFsgVIJzQ, project ard-review-board).
   Public URL: https://ard-review-board.vercel.app — client-side password gate (SHA-256 of owner's password), answers in localStorage,
   share via WhatsApp / copy / download. No claude.ai in the URL (owner's requirement). Claude artifact v2 kept as backup.
2. s28 → `04_LISTS_FROM_SOT/20260914_1356_AVD_GSH_Review_Sheet_337.xlsx` (46 cols: master + Bengali flags, AI question, options ক–ঙ,
   AI recommendation+reason, 5 reviewer comment cols AO–AS [প্রদীপ দা, প্রশান্ত দা, সুকান্ত দা, দেবী দা, বাচ্চা], AI status col AT).
   Converted in Chrome to native Google Sheet `20260914_AVD_GSH_Review_Sheet_LIVE`
   id 1CziwG-gMmYp9cJuM4Goga7q-2LqzehnIRG-rp5EJ8sE, tab REVIEW rows 2–338, folder "20260908 Promotion 244" (1BgJE4thWGsCLv4qFHqmWobW_met8UuEL).
   Backups folder `_backups_Review_Sheet (auto every 30 min)` id 1s4ZXYPfBncHcwpl19eieDrw-jZeSKUoC.
3. `05_REVIEW_APP/s29_sheet_sync.py` (diff / build / commit) — baseline snapshot stored (337 rows, 0 changes).
   Route: Chrome Name box A1:AT338 → cmd+c → `pbpaste` (LANG=en_US.UTF-8) → clipboard_A_AT.tsv (csv.reader, tab) → diff → AT column → pbcopy → paste at AT2.
4. Scheduled task trig_01GW9PDoLRxW88PXnKR6Q6B4 "ARD Review Sheet — hourly check & update", cron `2 * * * *` (UTC), push notifications.
   Owner asked for 30 min — platform minimum is 1 hour; owner informed. Task created "not bound: no_signed_approval — cloud only":
   owner must approve/bind it to the Mac (Chrome + clipboard steps need the Mac).

## Rules kept
Never edit A..AS; only AT (AI status) is written by the sync; backup copy before every change; no posting decision is taken by the sync.

## Open (owner)
F1 Kolkata physical DD count; F2 Murshidabad present in-charge (not in records); F3 Atit Maji Fodder district; F4 Uttam Kumar Biswas office;
F5 release vigilance-held DD posts; Q40–79 remaining districts; Q82 to be rephrased; Sukanta Roy Dte HQ AD line; Tarani Kanta Bera TI line.
