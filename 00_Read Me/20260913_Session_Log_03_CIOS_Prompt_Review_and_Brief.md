# Session Log 03 — 13.09.2026 (evening) — CIOS prompt review, new brief, drop-zone folder

## Done
- Read both files in Prompt/. v2.1 (20260913_211528_..._v2.1_Fable51Max.md) treated as the governing contract; the short v1 file conflicts with it (build-all-at-once vs staged).
- Checked v2.1 §3.1 against 02_MASTER_SOURCE_OF_TRUTH/*.sqlite: all 20 tables and row counts match. OCR votes 3170/2102/922 match.
- Found baseline numbers in v2.1 §4.1/§16 that do NOT reproduce from the SOT as written: OCCUPANCY rows give FILLED 1143 (+29 on SU), VACANT 315, NO_RETURN 592, NOT_ESTABLISHED 10, OFFICER_UNMATCHED 53, Under verification 32; DD no-return is 227 not 219. Tests 5 and 6 need pinning to named SQL.
- Raised 6 points to the owner (L9 vs Tri-Check conflict; v1 vs v2.1; baseline pinning; SQLite for Stage 1; nightly loop cannot run on Vercel free tier; below-60 rule hides unit-coordinator-only rows). Owner's answers pending.
- Created `_00_Input_Raw_Sources/` with README and `_processed/` sub-folder as the drop zone for new raw sources.

## Decided by owner (13.09.2026)
- The 242-row ROSTER_50POINT is the final Deputy Director promotee list.
- 244 DD posts sanctioned; 2 blocked pending vigilance clearance (owner statement) → 242 to fill.
- Only Order 1809 exists for the establishment; no pre-2025 sanctioned list on hand → abolished posts / rehabilitation list (owner estimate 86–100) cannot be identified until an old list is found.
- "2 years or less service left" is counted from 13.09.2026.
- Rule: promotee with ≤2 years left gets DD substantively, stays service-utilised in current post; manual recommendation by the authority supersedes.
- Build order: the three lists (promotion / rehabilitation / displacement) now by scripts on the SOT; CIOS app afterwards.
- External sources admitted: owner's Google Drive, Gmail, official websites (download, then cite).

## Open
- Owner's answers to the 6 review points above.
- Names of the two officers with the vigilance issue to be recorded as HUMAN_ENTRY (owner statement) in the SOT — not inferred.
- A pre-2025 sanctioned establishment list is needed for the rehabilitation list.

## Added later the same session
- Owner named the two officers holding DD posts pending vigilance clearance (owner statement, HUMAN_ENTRY, not inferred): Dr. Rupam Barua (HRMS 2013001674, HRMS designation Deputy Director ARD and Parisad Officer) and Dr. Sritanu Maiti (HRMS 1994000339, Deputy Director (Micro) IAH&VB) — the latter confirmed by owner from the closest master match. Neither is in the 242-name roster; both are incumbents. 244 − 2 = 242 DD posts to fill.
- Owner will supply paths to large folders of crude files (mixed true/false) on his Mac; Claude evaluates there, copies only what is needed into the archive, originals untouched.
- Manual recommendation sheets are known to be defective (names, present posting, SU status, HRMS ID, substantive posting, SU-on-transfer; recommendations scattered across Remarks and SU columns). They are NOT to be read until the SOT for officers, establishment and abolished posts is complete.
- Decided: one sacrosanct archive. All existing raw source folders to be moved (never edited) into `_00_Input_Raw_Sources/`, with a register of old path → new path and checksums; SOT scripts re-pointed. Move awaits owner's "go".
- Order 1809 gives block-level posts per district without block names. Plan: an official district→block reference (downloaded, cited) + the 1,423 unit-coordinator rows that name a block → block-wise establishment table; blocks with no return stay "Under verification".
- Rehabilitation list still blocked on a pre-2025 sanctioned establishment list; Claude to search the order corpus text, the owner's crude folders, Drive, Gmail and official portals for one.

## Archive build (later the same evening) — owner said go
- Owner granted read access to /Users/nirmalyaranjansarkar/Projects/AVD (15,541 files, 6.9 GB). Surveyed; excluded _AI_Generated, zzz Trash, _private, accounts, brand, publications, Documents.
- Fingerprinted 4,289 candidate files in Projects/AVD and 1,122 files in this project (SHA-256). 2,538 distinct files in AVD were not already here.
- Copied 1,329 files (KEEP) + 5 (QUARANTINE) into `_00_Input_Raw_Sources/`, renamed to the standing convention, every copy re-hashed and verified; 933 marked JUNK (broken PDF error pages), 271 SKIP (non-cadre or AI-written). Full record: `_00_Input_Raw_Sources/_register/ARCHIVE_REGISTER.csv`. Originals in Projects/AVD untouched.
- Key finds: 933 departmental-portal employee profiles (chronological postings, DOB, date of entry) — the likely cure for the 497 missing entry dates; Gradation List memo 3768 dt. 24.09.2025 (39-page scan); 382 orders/rules/acts not in the corpus, including transfer/SU orders dt. 21.03.2025, 28.11.2024, 07.01.2026 and the 05.01.2024 direct-recruitment appointment order; two further district returns (Purba Bardhaman, SLF Kalyani).
- Moved the project's own source folders into the archive (mv, no edits): 01_Verified_Sources → Verified_Sources_2026; 01 Verification data… → Establishment_Verification_2026; Orders, Notifications, Schemes etc. → ARD_Order_Corpus_2010_2026; 00_Important Orders → Important_Orders; the four byte-identical duplicate folders → _duplicate_copies/. All 1,122 files verified by hash at the new paths (`_register/MOVE_REGISTER.csv`).
- Re-pointed scripts/common.py, s10, s11, s13 (copies in scripts/_versions/); s01 re-run OK (1,794 posts). SOT README updated (pre-move copy kept). Table cells that store old path strings will refresh on the next full rebuild.
- Project root is now: 00_Read Me, 02_MASTER_SOURCE_OF_TRUTH, Prompt, _00_Input_Raw_Sources.

## Next (not started)
1. OCR the Gradation List scan (39 pages) and parse the 933 employee profiles → new evidence for PERSONS (date of entry, DOB, chronological postings).
2. Index + OCR the 382 new orders into the corpus (ORDERS/ORDER_MOVEMENTS), esp. the 2024–2026 transfer/SU orders.
3. Build the three truth tables: officers eligible for transfer; establishment district/block-wise; abolished posts (still needs a pre-2025 sanctioned list — search the 382 new orders for one).
4. Only then open `_quarantine_manual_recommendations/`.

## Second crude source: /Users/nirmalyaranjansarkar/Projects/AVD_AG (owner, later the same evening)
- This is the earlier AI agent's working repo (code + outputs). 184 files fingerprinted; 1 already held; 128 non-code files copied into `_00_Input_Raw_Sources/_quarantine_manual_recommendations/AVD_AG_agent_repo/` (all iterations of the Comprehensive Posting & Transfer Master Sheet, Google-Sheet downloads with manual remarks incl. `latest_gdrive_download/4.13 am mod ...`, `debi_da_final.xlsx`, draft transfer/promotion orders, Master_Decisions_Ledger.csv, conflict_audit_log.csv, verified_sources_discrepancies*.csv, remarks/column-N JSONs, the agent's SQLite backups). Code, images, .git, .vercel, static/ skipped. The agent's live `ard_master_truth.db` changed during copy and is marked `_LIVEFILE_`.
- Nothing from AVD_AG has been read. All of it stays in quarantine until the truth tables are built, per the owner's instruction.

## OCR coverage check and hand-off to Opus (owner's instruction, end of session)
- Checked what the earlier OCR run covered: 446 orders incl. 10 gradation-list documents (2015–2016 ASL/WBAH&VS/STA/AD lists; 2025–26 Agriculture Expert / Agricultural Engineer lists). The Gradation List memo 3768 dt. 24.09.2025 (39 pp) is NOT among them — new document, needs OCR.
- The 382 newly archived orders: 323 PDFs = 9,660 pages (4,271 scanned; 197 PDFs carry a text layer). Only 33 share an order date with an existing ORDERS row. The bulk of the page count is reference books (Treasury Rules, CrPC, WBSR, Acts, annual reports, compendiums) — triaged into three tiers in the job prompt.
- Owner will run the mechanical OCR/parse work on Opus 5.1 Max in a separate session of this project. Job prompt written: `Prompt/20260913_AVD_CIOS_Opus_Job_01_OCR_and_Parse_Batch2.md`. Output folders created and reserved: `02_MASTER_SOURCE_OF_TRUTH/batch2_ocr_text/`, `batch2_tables/`, `scripts/batch2/`. Page-count triage file placed in batch2_tables/.
- Nothing has been read or merged yet. Fable session resumes after Opus delivers, to merge batch2 into the master and build the three truth tables.

## Read-only review of the Antigravity database (owner's request, night of 13.09.2026)
File reviewed: /Users/nirmalyaranjansarkar/Projects/AVD_AG/ard_master_truth.db (20.6 MB, 27 tables), opened with SQLite `mode=ro`; nothing written, no config changed.
Status of Opus Job 01 at this point: DARAH profiles 933/933 done; gradation 3768 parsed 1,135 of ~1,236 rows; 43 of 331 Tier-1 orders OCR'd; remainder handed to Antigravity (Prompt/20260914_..._Job_02).

Findings (compared against our SOT, read-only):
1. Officers: 1,624 rows vs our closed 1,617. 9 HRMS IDs not in ours, of which 3 are junk rows (an HRMS of "Under verification", two rows whose hrms_id field holds descriptive sentences) and one is a second HRMS ID (1993000339) for Dr. Sritanu Maiti alongside the real 1994000339 — a duplicate identity. 2 of ours absent there.
2. Date of entry: AG fills 1,067; agrees with ours in 678 cases, differs in 270 (mix of dd/mm formats, one-day offsets, and HRMS-vs-declaration differences — AG appears to prefer HRMS; our precedence prefers the officer's declaration). Of 116 dates AG holds where we have "Under verification", 104 match the departmental-portal profiles exactly (legitimately sourced) and 12 have no visible source. 553 officers have blank (empty-string) DOB and DOJ — not "Under verification".
3. Vigilance: `vigilance_status = CLEARED` for all 1,620 officers, including the two the owner says are pending clearance. This is an inferred/defaulted value — forbidden by the contract (§18.8).
4. Verification claims: every officer `VERIFIED_SACROSANCT`, tier 4; 1,350 "10/10 unanimous pass". The audit ledger has one row, authorised by "VIGILANCE_CADRE_COMMITTEE", which is not a real approval. No per-fact evidence rows exist.
5. Posts: occupancy is two-state (Occupied 1,047 / Vacant 747). The 747 lumps our 592 NO_RETURN with genuinely vacant posts — exactly the error the contract forbids (§4.1). All 1,794 posts carry a named block although Order 1809 names none; no source column says where the block came from; a few are abbreviations ("R. R").
6. `obliterated_posts_1808` (106 rows, 76 occupied): not from any order text — the 1808/1809 texts in our corpus contain no abolition list. It is a derivation (posts seen in HQ returns that have no line in 1809: AD(SA), AD(MI), AD(Admin), DVO, CMS, farm and lab posts). Useful as a lead list, matches the owner's 86–100 estimate, but must be labelled derived, not sourced.
7. Roster: all 242 carry an HRMS ID and all exist in our PERSONS (we had 35 unmatched) — AG's matches are a lead to verify, not to copy. All 242 already "Allotted" to DD posts; two DD posts marked blocked (Sritanu Maiti at IAH&VB, Rupam Barua at Hooghly).
8. Spouse crosswalk (96 rows, all "Cadre-Verified") and `officer_extended_dossier` hold family/address data — personal fields; handle under the contract's restrictions.
Verdict: usable as a lead source only (rank: derived/AI output, weight 0). Nothing from it enters the master except where the underlying document is re-read.
