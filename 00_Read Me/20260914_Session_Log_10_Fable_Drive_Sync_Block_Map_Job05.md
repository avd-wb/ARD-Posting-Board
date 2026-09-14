# Session Log 10 — Fable · 14.09.2026 · Drive sync, official block list, roster 152, Memo 291, Job 05, SOT status
Session: Claude Fable 5.1 (Cowork) · owner: Dr. N. R. Sarkar · contract v2.1 · previous Fable log: 08 · Opus: 06 (Job 04 done) · Antigravity: 09 (reply)

## Owner instructions this turn (recorded)
- Missing documents (2015 Annexures 1–3, cleaner 1995 scan): "not possible — think of a way around".
- "No eye checks possible. Use multiple assessment engines and AI detectives to finalize. Do not give me work."
- Keep a copy of the SOT in Google Drive folder `ARD/00. Database ARD ` (id 1m-altHIPqyyrlh4cKiijREFRW_JX9kFC) on every update.
- Asked: SOT status; can real work start.

## Done
1. **Drive copy, zero-token route.** Google Drive for Desktop is on the Mac (`~/Library/CloudStorage/GoogleDrive-…/My Drive/ARD/00. Database ARD /`). New script `scripts/sync_sot_to_drive.sh` rsyncs the SQLite, both workbooks, README, `csv/`, `batch2_tables/`, `scripts/` into subfolder **`05. SOT_ARD_PROMOTION_Master`** (Drive folder id 15OIsz5s6wMAEYZxAVZp_3cVF3xku7JMC) and appends `_SYNC_LOG.txt`. First sync 11:38 (440 files, 263 MB); confirmed through the Drive connector. The script is the last step of every rebuild from now on (s20 → s14 → sync). `_versions/`, `_intermediate/`, OCR text and `*_prev.xlsx` are not copied. The stray `*_prev.xlsx` emit backups in the SOT root were moved to `_versions/emit_prev_20260914/`.
2. **Way-around for the missing annexures — official block list.** The owner's Drive already held `[Pub] Blocks_WB_as_on_20230706.xlsx` (LGD-numbered, 341 blocks, pre-2017 district set). Fetched via its public link, stored as `_00_Input_Raw_Sources/Reference_Lists_Official/20230706_LGD_Blocks_WB_Pub_Blocks_WB_as_on_20230706.xlsx` with an ORIGIN note; SHA-256 `c20e568f…4317`; registered (2 rows appended to ARCHIVE_REGISTER.csv). Weight: reference geography only. The sibling Districts and Sub-Div lists are not public and were not fetched.
3. **`scripts/s21_block_map_1995_to_lgd.py`** → tables/CSVs `BLOCK_MAP_1995_TO_LGD` (338: 279 VERIFIED exact-normalised, 41 UNDER VERIFICATION fuzzy, 18 unmatched), `BLOCK_MAP_REPORTED_TO_LGD` (528 distinct district/reported-area pairs from T2B: 297 exact, 38 fuzzy, 193 unmatched incl. 21 non-block areas), `LGD_BLOCKS_WB_341` (with counts of 1995 posts and 2026 reported rows per block). Nothing here asserts a post or an officer; fuzzy/unmatched rows go to Job 05 WP5.
4. **Roster 152 linked = 1994003580** (machine adjudication, owner-authorised under "no eye checks / do not give me work"): roster string == gradation memo 3768 p.7 sl.149 string incl. " - 1" == HRMS id printed beside it (HRMS_ID_PRINTED_EXACT, 2 votes); 1994003580 is DR.PRADIP KUMAR ROY, in service; 204 " - 2" = 1995000449 by owner. `s19` patched (backup in `_versions/s19_truth_tables_*_before_152.py`). T4: **242/242 linked, 242 distinct, 0 proposals**. Owner may veto with one word.
5. **Memo 291-AR&AH/3A-11/06 dt. 19.02.2009** (transfer policy) — located by Antigravity in `ARD_Orders_Rules_Acts/20260604_194024_ARD_Order_00000000_Other_0.15_Mb.pdf`; SHA verified. New `scripts/s22_policy_authorities.py` → `POLICY_AUTHORITIES` (1) and `POLICY_RULES` (13 paras; 1–3, 5–10 from OCR pass 3; 4, 11–13 unread/partly read). All paragraphs UNDER VERIFICATION; not applied to any officer.
6. **Rebuild**: s19 → s20 (51 sheets, 125,035 rows, 50 CSVs) → s14 all checks passed → Drive sync.
7. **Job 05** written: `Prompt/20260914_AVD_CIOS_Job_05_Multi_Engine_Adjudication.md` — eight work packages (T8 120 rows, REVIEW_QUEUE 124, gradation serials, 1995 zero-vote rows, block-map fuzzies, Memo 291 paras, 56 sideways compendium pages, 2015 citation search), ≥3 independent engines, majority vote, results marked "machine adjudication, owner-authorised".
8. **Reply to Antigravity** written: `Prompt/20260914_AVD_CIOS_Reply_to_Antigravity_and_Wiring_Terms.md` — accepts items 2–4 of its reply, records Memo 291, sets seven checkable conditions (a–g) for wiring the app read-only to the master, invites it to take WP5/WP7.

## Not done / still open
- 2015 Annexures 1–3: unavailable; treated as such (WP8 searches for citations only).
- Two missing 1995 serials, 81 zero-vote rows, 120 T8 rows, 124 queue items, 395 serials, 56 pages: all in Job 05 — no owner eye-checks requested.
- Quarantined manual-recommendation sheets: still unread (needs the owner's "go").
- `Prompt/CLAUDE_FABLE_5_1_MASTER_PROMPT.md` (v1) still in place; to be moved to `_Trash/` as superseded.
- Antigravity's log is numbered 09; this log is 10 to avoid the collision.
