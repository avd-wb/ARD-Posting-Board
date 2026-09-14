# Session log — 13.09.2026

**Task:** build a detailed list of employees, list of posts and associated data from the
files inside this project folder, to stand as the source of truth. No outside source.

**Worked on:** `nrss-mac-local`, directly in `/Users/nirmalyaranjansarkar/Projects/ARD PROMOTION`.
Nothing was uploaded or downloaded; every file stayed on the machine.

---

## Decisions taken this session (by the project owner)

| Question | Answer |
|---|---|
| Precedence when sources disagree | Posting Preference form → HRMS → HQ status report → unit-coordinator verification |
| Posting Preference data | All 204 columns into the master |
| 929 order PDFs | Index all, and parse promotion + transfer orders |
| Output form | Excel workbook + CSVs + SQLite |

---

## What was read

1,132 files surveyed. Three folders found to be byte-identical triplicates (`From HQ`,
`Sourced form District returns`, `01_Verified_Sources /From AD HQ DAHVS`), and
`orders_published/raw` found to duplicate `orders_published`. Duplicates were left in place
but read only once.

| Source | As on | Taken |
|---|---|---|
| `20260911_AVD_CADRE-VERIFY_1794_Posts_Tab_Export.csv` (Order 1809) | 18.06.2025 | 1,794 posts |
| 24 unit-coordinator verification workbooks | 20.08.2026 | 1,501 post rows |
| Directorate HQ + IAH&VB returns | 01.07.2026 | 86 rows |
| 42 of 44 HQ district status reports | 01.07.2026 / 15.05.2026 | 2,470 rows, 4,951 history lines |
| HRMS extract | 08.09.2026 | 1,617 personnel records |
| Posting Preference form | 06.09.2026 | 513 responses × 204 columns |
| Revised 50-Point Roster | 07.09.2026 | 242 names |
| `Vacancy of DD.xlsx` | not stated | 244 DD posts |
| Order PDFs | 2010–2026 | 462 distinct documents |

Two HQ files were not read and the reason is recorded: `WB_LSD_IV_17_06_2026.xlsx` is
livestock vaccination data, not a personnel return; `~$Consolidated status report.xlsx` is
an Excel lock file. `ARD_Verification_Murshidabad_20082026(1).xlsx` was skipped as a
superseded duplicate of the 91-row version.

---

## What was built

Created `02_MASTER_SOURCE_OF_TRUTH/` containing:

- `20260913_AVD_SOT_Master_Register.xlsx` — 14 sheets, 2.4 MB
- `20260913_AVD_SOT_Master_Register.sqlite` — same 14 tables, indexed, 8.0 MB
- `csv/` — 14 CSVs, UTF-8 with BOM
- `scripts/` — 14 build scripts, re-runnable in order
- `_intermediate/` — per-stage extraction output
- `README.md` — hand-over note: precedence, keys, limits, headline figures, rebuild steps

Tables: POSTS 1,794 · PERSONS 1,617 · OCCUPANCY 2,174 · POSTING_HISTORY 6,797 ·
ESTABLISHMENT_BALANCE 313 · PREFERENCES 513×215 · PREFERENCES_DICTIONARY 204 ·
ROSTER_50POINT 242 · DD_VACANCY 244 · ORDERS 462 · ORDER_OFFICERS 67 ·
RECONCILIATION 24 · SOURCE_REGISTER 9 · HQ_FILE_PARSE_LOG 44.

Also created `00_Read Me/` for session logs.

---

## Method notes worth carrying forward

- **Every column was matched by header text, never by position.** No two HQ workbooks share
  a layout; header text wraps down as many as eight rows in one of them, so the parser picks
  the fold depth that maps the most fields.
- **Order 1809 does not name blocks** for block-level posts — it sanctions them against a
  district's "Sub-Divisional and Block Level Set up". A named block therefore cannot be tied
  to one sanctioned post line. `POST_ID` in OCCUPANCY is an allocation within
  (district, grade), and every row says so in `POST_ALLOCATION_BASIS`.
- **Officers on service utilisation or on a district roll do not consume that district's
  sanctioned strength** — 88 such rows are held separately.
- **Jalpaiguri and SPF Mohitnagar returns include Group C/D staff** (drivers, peons,
  pharmacists, attendants). They are kept and flagged `NON_CADRE_STAFF`, not merged into the
  officer cadre. 264 rows.
- **Post codes were derived from the words present only.** Where the words did not decide —
  an AD sub-designation outside the four in Order 1809, a bare "Veterinary Officer" with no
  centre type, "District Veterinary Officer" — the code was left blank with the reason
  written out, not guessed. `C&DD` is Cattle & Dairy Development and is explicitly kept from
  being read as Deputy Director.
- **Missing values read "Under verification"** throughout. 40 verification checks pass,
  including referential integrity across all five linking columns and spot checks against
  the original workbooks.

---

## Left open, needing a return or a decision

See `RECONCILIATION` in the workbook for all 24 items. The six that matter most:

1. 592 sanctioned posts have no field return — including 219 Deputy Director and 127 AD (Veterinary).
2. Six district/units returned nothing: Kolkata (part), North Bengal, Zones I–IV.
3. Paschim Medinipur typed all 39 health centres as BAHC against a sanction of 21 BAHC + 18 ABAHC.
4. `Vacancy of DD.xlsx` says all 244 DD posts are vacant; field returns show 2 filled.
5. 235 of 243 promotion/transfer orders are scanned images (502 pages, 164 MB). `tesseract`
   is present on this machine, so OCR is possible — awaiting a decision.
6. 35 Revised 50-Point Roster names do not match any officer in the master.

---

## Versioning

First build of this master; there was no earlier version to copy aside. From the next update
onward the standing rule applies: copy the current file in place, then update and re-stamp.
