# Session Log 05 — 13/14.09.2026 (night) — batch 2 ingested, evidence ledger, truth tables (Fable 5.1)

## Outcome
The master now carries an evidence ledger and the three truth tables the owner asked for, built from what exists today; the DD promotion working list (242) is in the same workbook. Nothing was invented; every missing value reads "Under verification".

## Done
1. Versioned the master (`*_1957_*_pre-batch2.*`), then s17 loaded the 10 batch-2 tables from Opus Job 01.
2. s18 built `EVIDENCE` (33,842 rows) from six sources with the owner's precedence and §9 arithmetic, resolved 17,802 (officer, field) values, and queued 124 items for review. Two corrections made while building: (a) the portal's "entry into Govt. service" is a different fact from entry into WBAH&VS — kept separate; (b) the gradation OCR's date columns are shifted (e.g. "1996-01-01" landing in DOB/entry fields, garbage like "07-C3-2016") — excluded from resolution, kept in the ledger marked UNUSABLE.
3. s19 built T1–T7 and the workbook `02_MASTER_SOURCE_OF_TRUTH/20260914_AVD_TT_Truth_Tables_and_Promotion_List.xlsx`.
4. Verified: frozen tables intact (1,617 / 1,794 / 2,174 / 462); T1 = 1,617; T4 = 242; T5 = 244; T2 sanctioned sum = 1,794 and NO_RETURN sum = 592; zero cells with N/A, "-", NOT ON RECORD; every HRMS_ID in T1/T4 exists in PERSONS.
5. Fixed a mount problem: SQLite writes on the project folder fail; a stale journal from the first attempt blocked reads — moved to `_to_delete/`; scripts now copy-then-rename.

## What the numbers say
- Date of entry into WBAH&VS: VERIFIED 472 officers, UNDER VERIFICATION 639 (mostly single-source), DISPUTED 4, no evidence 502. Among **in-service** officers only 74 have no entry date at all, and 37 of those have a portal govt-service date as a lead.
- DOB: VERIFIED 351, DISPUTED 14 (declaration vs portal), UNDER VERIFICATION 665, no evidence 587.
- DD posts (244): filled 2, vacant 21, not established 2, **no return 219**; 2 posts recorded as held pending vigilance clearance per the owner (one located by HRMS office only, "Zone-I").
- Promotion 242: HRMS linked 207; 30 name-spelling proposals await the owner's yes (Kr.→Kumar, Ch.→Chandra, joined/split names; surname agrees); 5 unresolved (Kesang Bomzon, Swarup Mondal, Mousumi Ghosh (Jana), Swapna Rooz, Partha Sarathi Sengupta). Two-year rule from 13.09.2026: 77 Yes, 130 No, 35 unknown. Service-utilised among the 242: 8 Yes.
- Abolished-post leads (T3): 383 rows — 327 reported posts with no sanctioned line left in Order 1809 for that district/grade, 53 roll officers tied to no post, 17 marked OBLITERATED by coordinators; 62 of the occupants are on the DD list. Largest: Nadia 89, Paschim Medinipur 49 (BAHC/ABAHC typing issue), Kolkata 32. Derived, not from an order.
- Filled on paper but service-utilised elsewhere (T6): 58 rows.
- The Antigravity roster table carries different names at the same roster points as the Revised 50-Point Roster dt. 07.09.2026 (e.g. point 37) — not used, noted.

## Open / needs the owner
- Approve or reject the 30 roster-link proposals (sheet REVIEW_QUEUE / T4 column PROPOSED_HRMS_ID_NEEDS_YOUR_YES).
- Decisions from Session Log 03 still pending (L9 vs Tri-Check; v1 prompt retirement; below-60 rule).
- Gradation List 3768: needs a proper column-geometry re-parse and eye check (job for Antigravity/Opus) before its serials rank anyone.
- Manual recommendation sheets remain quarantined, unread.

## 14.09.2026 — two files dropped at the archive root by the owner
- `ard_master_truth.db` (Antigravity DB, 13.09.2026 23:30 snapshot): same 27 tables and identical row counts as the read-only review in Session Log 03; audit ledger still the single "genesis" row; vigilance still CLEARED for all 1,620; occupancy still two-state. Content differs from the 17:43 LIVEFILE copy in the officer dossier, roster, order schedule and simulation tables. Registered and moved to `_quarantine_manual_recommendations/AVD_AG_agent_repo/` as a dated snapshot. Verdict unchanged: leads only.
- `ARD_Master_Source_Of_Truth.xlsx` (12.09.2026, 1,900 rows × 33 columns, one row per post with present occupant): byte-identical to a file already in quarantine; moved to `_duplicate_copies/`, registered.
- Neither file was read into the master.

## 14.09.2026 — review of the Antigravity web app https://ard-posting-board.vercel.app (owner's request)
Studied: Projects/AVD_AG (README, app.py 1,894 lines FastAPI, api/index.py, vercel.json, static/index.html + app.js, 45 build scripts) and two live endpoints (`/api/overview`, `/api/officer/{hrms}`), read-only.
Findings:
1. **No authentication anywhere.** `/api/officer/{HRMS_ID}` returns, to anyone on the internet, the officer's mobile, alternate mobile, WhatsApp, e-mail, DOB, caste, home and current addresses with PIN, spouse name/department/posting, number of children and their board-exam years, health conditions, care needs, PwD status and spouse health. 13 tabs, 32 API routes, all open. This is the personal data the officers gave AVD in confidence on the preference form.
2. The site also fingerprints every visitor (IP, city, device, time on page) into `visitor_sessions/visitor_events` — a tracker on a government-records tool, with no notice.
3. Data claims the contract forbids: "Vacant 747" (592 no-return posts counted as vacant); all 1,620 officers "VERIFIED_SACROSANCT" and vigilance "CLEARED"; 242 roster candidates shown as already "allotted"; obliterated posts "106 tracked in real time" though no abolition list exists in any order; a 4-year "Hill/Dooars/Western" tenure rule attributed to "Memo 291-AR&AH" (not in our corpus — unverified).
4. Roster names differ from the Revised 50-Point Roster dt. 07.09.2026 at the same points (see Session Log 03); duplicate HRMS ID for one DD.
5. Architecture: on Vercel the SQLite DB is copied to `/tmp` on each cold start, so every "allotment" made in the simulator is silently lost; Gemini calls give "statutory justifications" drafted by a language model with no evidence ids.
6. What is good and worth keeping as ideas: one-click officer dossier, omni search, district/organogram views, visual post grid, export to Excel/DOCX, mobile-first layout, the displaced-officer pool concept.
Recommendation given to owner: take the site private today (Vercel password/deployment protection or delete the deployment) and treat it as a UI prototype only; its data must not be shown to anyone as fact.

## 14.09.2026 (morning) — roster links settled; live WBIFMS lookup; message to Antigravity
- Owner decision: approve only the very close name-variant proposals. Applied as similarity ≥ 0.95 after Kr./Ch. expansion with surname exact → 28 linked (basis "name variant approved by owner 14.09.2026"). Two are AMBIGUOUS (another officer scores ≥ 0.90 with the same name) and stay unlinked pending the owner: roster 101 Dr. Tapas Kr. Ghosh (1990003426 retired vs 1995000577 in service) and roster 204 "Dr. Pradip Kr Roy – 2" (1981000203 superannuated vs 1994003580 / 1995000449 in service).
- Owner instruction: look the five unplaced names up live in WBIFMS HRMS-ESS (owner logged in, Claude in Chrome). Employee Search is capped at 200 rows per query; the advanced (cadre) search does not page, so name-contains searches were used within cadre WBAHVS. All five exist in the master under different spellings: 71 Kesang Bomzon = 2000010253 DR KESANG BOMZAN; 79 Swarup Mondal = 1995002200 DR SWARUP MANDAL; 111 Mousumi Ghosh (Jana) = 1995006326 ". Dr. MOUSUMI (GHOSH) JANA"; 113 Swapna Rooz = 1994003385 DR. MRS. SWAPNA ROOJ; 180 Partha Sarathi Sengupta = 1995001799 PARTHA SARATHI SEN GUPTA. The surname guard had blocked them (Bomzan/Bomzon, Mandal/Mondal, Rooj/Rooz, "SEN GUPTA", bracketed maiden name). 16 captured rows + 2 screenshots archived in `Verified_Sources_2026/Source from HRMS/` (registered) and shown as sheet "HRMS data from WBIFMS" in the truth-tables workbook. Linked in T4 with basis "WBIFMS live lookup 14.09.2026; owner instruction".
- T4 now: 240 of 242 linked; two-year rule 85 yes / 155 no / 2 unknown.
- Lesson recorded for the name-variant RULES table: surname spellings Mandal≡Mondal, Rooj≡Rooz, Bomzan≡Bomzon; split surnames (Sen Gupta); bracketed maiden names — proposals only, never auto-merge.
- A full re-extract of HRMS from WBIFMS is possible but slow (200 rows per query, ~50 s each, no paging on cadre search); the 08.09.2026 extract remains the HRMS source until a scripted refresh is scheduled.
- Message to Google Antigravity written: `Prompt/20260914_AVD_CIOS_Message_to_Antigravity_Web_App_Review.md`.
- Owner decisions (later, 14.09.2026): roster 101 = 1995000577 (serving Tapas Kumar Ghosh); roster 204 to be cross-checked with the gradation list → gradation 3768 prints "Dr. Pradip Kumar Roy - 1" = 1994003580 (p.7, sl 149) and the portal profile of 1995000449 is filed as "Pradip Kr. Roy.2", so "– 2" = 1995000449 is proposed (not linked) for the owner's yes; VERIFIED rule changed to §8-L9 reading (one rank-1/rank-2 source, score ≥ 85, is enough). s18/s19 re-run: DOB VERIFIED 1,015; entry date VERIFIED 501 / under verification 610 (unit-coordinator-only, weight 0.55) / none 502; DOR VERIFIED 1,475. T4: 241 of 242 linked.
