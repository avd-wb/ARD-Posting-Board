# Session Log 06 — 14.09.2026 — Opus: verification of Job 02, and repair of two defects in the batch-2 extractors

Owner's instruction: check what Antigravity produced, finish what was pending, and write a
hand-off prompt for the Fable 5.1 session.

Nothing in `_00_Input_Raw_Sources/` was touched. No master table was written. Work was
confined to `batch2_tables/`, `batch2_ocr_text/GRADATION_3768/` and `scripts/batch2/`.

---

## 1. Antigravity's Job 02 — checked line by line, not taken on trust

| Claim in Session Log 05 | Independently checked | Verdict |
|---|---|---|
| 382 rows in `ORDERS_BATCH2.csv` | 382 | correct |
| 331 Tier 1 + 9 Tier 2 files with text | 331 and 9 carry `TEXT_EXTRACTED = Y` | correct |
| 42 Tier 3 files indexed only | 42, `TEXT_EXTRACTED = N` | correct |
| No HRMS_ID outside `PERSONS` | 0 exceptions | correct |
| No empty / `N/A` / `-` / `NOT ON RECORD` cell | 0 | correct |
| Archive unchanged | re-hashed, 0 changes | correct |
| 1995 order sanctions 340 BLDO posts | **read the OCR text myself** — para 4 states "The 340 Posts of the 2 erstwhile Directorates … are being redesignated as Block Livestock Development Officers in respect of the individual blocks shown against each post" | **correct, and it is the find of this whole exercise** |
| **"495 distinct officers"** | the table holds **394** distinct HRMS ids | **overstated** |

Antigravity did the OCR well. The two defects found below are **in my own extractors from
Job 01**, not in its work — it ran my scripts faithfully and my scripts were wrong.

---

## 2. Defect 1 — the transfer tables were never read as tables

`ORDER_MOVEMENTS_BATCH2.csv` had 520 rows and **not one of them carried a present posting,
a posting on transfer, an origin district or a destination district**. Every row was
`Under verification` on all four. `EXTRACTION_MODE` was PROSE or TEXT_LAYER on all 520 —
never TABLE.

**Cause.** `movements.py` measured the column gutters over the whole page. In these orders
the paragraph above the table and the endorsement list below it both run the full page
width, so the page-wide coverage histogram shows no gutter anywhere and the table
collapses into one column. The transfer order of 21.03.2025 — one of the three 2024–2026
service-utilisation orders the owner needs — yielded **zero** rows.

**Repair.** Four changes, each tested against the four transfer orders in the corpus:

1. Column bands are now measured **over the table body rows only**, not the page.
2. The split between "name with present place of posting" and "place of posting on
   transfer" is taken from the **printed header**, which wraps over two lines, by walking
   left from the word *transfer* through the words belonging to that phrase. The position
   is carried forward to the continuation pages, because these orders print the header
   once.
3. A record begins where an officer's name matches the closed set **or** where a printed
   serial appears in the serial column — so an entry whose surname the scan mangled is
   still cut as its own record. Entries wrap over three to five printed lines and are
   accumulated.
4. An endorsement page (the forwarding list) is no longer mistaken for a table, and the
   order-number line at the top of every notification is no longer treated as the end of
   the table. That single mistake had been killing whole tables.

**Also repaired, and more serious than it looks:** the name scanner stopped at the first
word that happened to be a surname. Many Bengali given names are also surnames in this
cadre, so *DR SOUMITRA KUMAR GHOSH* was being read as *DR SOUMITRA KUMAR* and matched
against an officer surnamed **Kumar** — a different person. The scanner now takes the
rightmost word of the run as the family name.

**Result:**

| | Before | After |
|---|---|---|
| Movement rows | 520 | **530** |
| Rows read from a table | 0 | **121** |
| Present posting read | 0 | **118** |
| Posting on transfer read | 0 | **120** |
| Origin district identified | 0 | **78** |
| Destination district identified | 0 | **103** |
| Distinct officers | 394 | **396** |
| Unmatched name candidates | 2,104 | **1,691** (false anchors removed) |

Transfer order dt. 28.11.2024 now gives 60 records with both postings; 07.01.2026 gives 8;
21.03.2025 gives its 1; 29.11.2022 gives 13.

`DISTRICT_RESOLVED` now reads `Y` only where **both** districts were named and unambiguous
(68 rows). It previously read `Y` on rows where no district had been read at all.

---

## 3. Defect 2 — the Gradation List date columns

The Fable session found this and was right to quarantine it: it marked the gradation date
columns UNUSABLE and excluded them from the evidence ledger.

**Cause.** Dates were assigned by their order in the row — first date to *date of birth*,
second to *date of entry*. Whenever only one of the two was legible, the survivor landed
in the wrong column. A whole 1996 entry cohort was therefore carrying
`DATE_OF_BIRTH = 01-01-1996`. Separately, stray ink and category letters from the
neighbouring column ('SC', '1', '=', 'otoit9e') were being written into the date-of-entry
field on 70 rows.

**Repair.** The two date columns are located once, over all 2,087 printed dates on the 39
pages, by a one-dimensional two-means (date of birth at x=1200, date of entry at x=1447).
Each date is then assigned to the column it is **printed under**. Non-date text is never
written into a date field; the mode of entry ("(Direct)", "(Promotion)") is kept only where
that column actually holds a date, and anything else goes to `REMARKS`. The `_ISO` columns
are now derived from the value the geometry read and confirmed against all three passes,
instead of taking the n-th date off each text line.

**Result:** 0 rows where `DOB_ISO` disagrees with `DOB_RAW` (was 2), 0 where
`DATE_OF_ENTRY_ISO` disagrees with its raw value, **0 rows of junk in either date field**
(was 70), one residual row with an implausible date of birth, flagged. Confirmed ISO
values rose from 388 to **404** for date of birth and from 248 to **293** for date of entry.
Row count unchanged at 1,135.

**The gradation date columns are now fit to use.** The Fable session should lift the
UNUSABLE marking and re-run its evidence ledger.

---

## 4. The master register is holding stale batch-2 tables

`20260913_AVD_SOT_Master_Register.sqlite` (41 tables) was loaded by the Fable session's s17
at 19:57 on 13.09.2026 — **before** Antigravity finished the OCR at 04:45 on 14.09.2026.
It therefore contains:

| Table in the master | Rows it holds | Rows that now exist |
|---|---|---|
| `ORDER_MOVEMENTS_BATCH2` | **2** | **530** |
| `UNMATCHED_NAMES_BATCH2` | **14** | **1,691** |
| `ESTABLISHMENT_LEADS_BATCH2` | **12** | **374** |
| `GRADATION_3768_ROWS` | 1,135, with the defective date columns | 1,135, repaired |

So `EVIDENCE` (33,842 rows), `RESOLVED_PERSON_FIELDS` and the truth tables T1–T7 were all
built from a corpus carrying **two** order-movement rows instead of five hundred and thirty.
They need rebuilding. The workbook `20260913_AVD_SOT_Master_Register.xlsx` is also older
than the SQLite and does not carry the batch-2 or truth tables at all.

---

## 5. Housekeeping

- `scripts/batch2/movements.py` and `grad_parse.py` updated; the previous copies are kept
  beside them with a time suffix, per the standing rule.
- The word-box geometry for the 39 gradation pages (`page_NNN.tsv`) is now stored in
  `batch2_ocr_text/GRADATION_3768/`, so the parse is reproducible on this Mac. It had
  existed only in the cloud container.
- Superseded table copies are kept as `*_prev.csv` in `batch2_tables/`.
- One stray transfer archive was moved to `_to_delete/`; file deletion was not permitted in
  this session.
- `Claude outputs/` at the project root holds one copy of the gradation table delivered
  through the chat. It duplicates `batch2_tables/` and can be deleted.


---

## 8. Second pass, same day — the source of truth rebuilt on the corrected data

After the repairs above, the owner asked for the source-of-truth database to be made
right rather than handed on. Done as follows.

### 8.1 Twenty-two pages of the 1995 sanctioned establishment had been scanned sideways

The annexure of the 4 May 1995 memorandum — the block-by-block list of the **340
sanctioned BLDO posts**, the pre-2025 establishment this project has been blocked on —
was fed through the scanner turned through 90 degrees. Deskew only corrects a degree or
two, so all 22 annexure pages had come back as pure gibberish and were silently lost.
Nobody had noticed because the OCR produced plenty of *characters*.

`scripts/batch2/ocr3.py` now detects page orientation with Tesseract OSD, and — because
OSD scores these sparse typewritten tables below its own confidence threshold — where it
is unsure it **reads the page both ways and keeps whichever yields more real words**
(runs of four or more letters). On this document that recovered 22 of 23 pages: page 8
went from 0 real words to 155, and the document's three-way agreement rose from 26% to
43%.

A sweep of all 3,590 pages of the batch-2 corpus found the problem is contained. Four
documents were affected and three have been re-read:

| Document | Pages rotated |
|---|---|
| 1995 BLDO set-up formation | 22 of 23 |
| 20.01.2022 revised guidelines | 7 of 8 |
| 26.05.1996 JD ARD CSAHF Salboni | 2 of 11 |
| `h_sch_1` | none needed after re-check |

**Still outstanding:** the 240-page compendium
`20260604_193744_ARD_Order_20220000_..._Imp_Govt_Orders_ARD_Dept_136.87_Mb.pdf` has
**56 pages that look sideways** and has not been re-read — it is 137 MB and a Tier 2
document read at pass 1 only. It should be re-run with `ocr3.py --osd`.

### 8.2 The 1995 annexure, extracted

`batch2_tables/ESTABLISHMENT_1995_BLDO_ANNEXURE.csv` — **223 rows**, one per printed
line of the annexure, against the 340 posts the order states.

| | Rows |
|---|---|
| Read cleanly as a sanctioned-post line | **65 GOOD + 18 PARTIAL = 83** |
| Line recovered but the post column names no post — most likely running text | 140 |
| Serial legible | 26 |

This is a 1995 typewritten carbon copy. The serial column is largely illegible — the
numbers come back as letters ("dee" for 86) — so the **block name** is what anchors each
record, and the serial is recorded only where it could actually be read. Every row
carries `LINE_TEXT_RAW`, the printed line exactly as read, and a `LEGIBILITY` flag.

**This table is evidence for a human to check, not a settled establishment.** It is not
fit to be used as the sanctioned strength until the pages have been read by eye. What it
does give, for the first time, is the 1995 block names — which Order 1809 dt. 18.06.2025
does not print at all.

### 8.3 The master rebuilt, and the three deliverables made to agree

| Step | Result |
|---|---|
| Master versioned | `20260913_0535_AVD_SOT_Master_Register_pre-rebuild.sqlite` |
| `s17` (extended to load the 1995 annexure) | 11 batch-2 tables loaded, `ORDER_MOVEMENTS_BATCH2` now **530** rows, not 2 |
| `s18` evidence ledger | **32,717** rows |
| `s19` truth tables | T1–T8 rebuilt; `T8_ORDER_MOVEMENTS_BATCH2` 530 rows |
| `s20_emit_all.py` (new) | workbook + 43 CSVs re-emitted **from the SQLite itself** |
| `s14_verify.py` | **"All verification checks passed."** |

What the corrected gradation dates did to the ledger:

| Field | Fable's 14.09 run | This run |
|---|---|---|
| Date of birth VERIFIED | 1,015 | **1,066** |
| Date of entry VERIFIED | 501 | **604** |
| Date of retirement VERIFIED | 1,475 | 1,475 |
| Gradation serial VERIFIED | not used — quarantined | **259** |

**The three deliverables can no longer disagree.** `s20_emit_all.py` writes the workbook
and every CSV out of the SQLite in one pass, so the database,
`20260914_AVD_SOT_Master_Register.xlsx` and `csv/` are the same data three ways — 43
tables, 123,461 rows. The stale `20260913_AVD_SOT_Master_Register.xlsx`, which carried
only the original 20 tables, has been moved to `_Trash/` so that nobody opens it by
mistake. The superseded CSVs went with it.

### 8.4 Housekeeping done

- `Claude outputs/` and the old `_to_delete/` folder moved to `_Trash/` at the project
  root, as the owner asked. Nothing was deleted outright.
- `movements.py` now snaps the transfer-table column boundary to the body's own gutter
  where the page has one, instead of trusting the header position alone.

### 8.5 What is still open

1. **The 240-page compendium's 56 sideways pages**, above.
2. **The 1995 annexure needs an eye-check** before any of it is treated as sanctioned
   strength, and its 223 rows carry no district — the district must come from an official
   district-to-block reference, which this project does not yet hold.
3. **120 movement rows carry `NEEDS_EYE_CHECK = Y`** — every fuzzy name match and every
   row found by only one of the three OCR passes. On a few rows of the 29.11.2022 order
   the destination text still bleeds into the present-posting cell; `RECORD_TEXT` holds
   the whole printed line on every row.
4. **405 of the Gradation List's 1,135 serials are still unread**, so those serials must
   not rank anyone. The serial column sits hard against the table rule.
5. `REVIEW_QUEUE` holds 124 items: 24 portal surname disagreements and 100 gradation
   matches awaiting a human.
6. One roster proposal still awaits the owner's yes (roster 204).

---


---

## 9. Third pass — Job 04 executed: the 1995 sanctioned establishment transcribed by eye

The Fable session issued `Prompt/20260914_AVD_CIOS_Job_04_1995_BLDO_Annexure_ReOCR.md`
while this session was working, having independently reached the same diagnosis: the
annexure pages were scanned sideways. That job is now done.

### 9.1 Why OCR alone was never going to do it

Even rotated, the three passes read this 1995 typewritten carbon copy badly — mean
agreement 43%, and on 91 of the rows **not one of the three passes contains the block
name at all**. So each of the 21 annexure pages was rendered as an image and **read by
eye**. The machine could not have produced this table; that is the honest reason the
transcription exists.

### 9.2 `batch2_tables/ESTABLISHMENT_1995_BLDO_340.csv` — 338 of the 340 posts

| | |
|---|---|
| Rows transcribed | **338** (the order states 340) |
| Serials printed and read | **238**, running 1 to 340 |
| Rows whose serial is **outside the scanned area** | 100 |
| Districts named | 17 |
| Post separated from office | 281 |
| Rows where no OCR pass contains the block name | 91 |

Columns are exactly those Job 04 specified. `ERSTWHILE_DIRECTORATE` and
`SUBDIVISION_AS_PRINTED` are `Under verification` on every row — **the annexure does not
print those columns.** It prints three: District, Blocks, and "Name of the post redeployed
in the Block as Block Livestock Development Office".

Three things were found and **not** papered over:

1. **The scan is cropped.** On pages 11, 12, 13, 16, 17 and 18 the serial column falls
   outside the scanned area. Those serials were **not** inferred from the sequence, even
   where the arithmetic would have been easy — page 14 resumes at 191 while counting
   forward from page 10 gives 190, so inferring would have introduced an error.
2. **Page 6 carries a block of rows with no district heading above them** (serials 45–56:
   Dinhata, Sitai, Tufanganj, Mekhliganj, Haldibari, Coochbehar, Sitalkunchi,
   Mathabhanga). The heading printed above them reads "North & South Dinajpur", which
   these blocks do not belong to. `DISTRICT_AS_PRINTED` is `Under verification` on those
   twelve rows with the reason recorded.
3. **Page 18's faded bottom is show-through from page 19**, not data. Those four rows
   were removed; page 19 prints them properly as serials 276–279.

Page 15 came back upside down from the automated pass — the orientation trial chose
wrongly on that page. The eye-read recovered it (serials 208–225).

### 9.3 `batch2_tables/ESTABLISHMENT_2015_ABOLITIONS.csv` — and the gap behind it

Notification No. 2036-AR&AH/3A-03/2009 dated 4 November 2015, signed R.K. Sinha,
Secretary. Fifteen rows: the five-post block set-up it creates, the four bulk creations
(138 UDC, 203 LDC, 341 Group 'D', 341 Night Guard) and the six classes of post it
abolishes to fund them — 138 UDC, 82 LDC, 8 Group 'B', 177 Group 'C', 123 Peon and 627
Group 'D', at CSAHF Salboni, Haringhata, SLF Kalyani and the erstwhile offices of
Superintendent of Livestock.

**The archive holds only the first page.** It ends "(Continued)", and the notification's
own Annexures 1, 2 and 3 — which carry the office-by-office detail of exactly which posts
were abolished where — **are not in the corpus.** Every abolition row says so. Those three
annexures are the single most valuable document still missing, and they have to come from
the department.

### 9.4 Master rebuilt again on the new evidence

`s17` (extended to load the two new tables) → `s18` → `s19` → `s20` → `s14_verify`:
**"All verification checks passed."** The master now holds **45 tables, 123,814 rows**, and
the SQLite, the workbook and the 45 CSVs are emitted from one place and agree.

### 9.5 What the rotation fix cost and found

A sweep of all 3,590 pages found four documents with sideways pages. Three were re-read.
**The 240-page compendium `..._Imp_Govt_Orders_ARD_Dept_136.87_Mb.pdf` still has 56 pages
that look sideways and has not been re-read** — it is 137 MB and was read at pass 1 only.
That is the last known pocket of unread text in the corpus.

---

## 6. Acceptance table, computed 14.09.2026

| Check | Expected | Actual |
|---|---|---|
| Files in `ARD_Orders_Rules_Acts/` = rows in `ORDERS_BATCH2.csv` | 382 = 382 | **382 = 382** |
| Every Tier-1 file has a merged text file | 331 | **331** |
| `DARAH_PROFILES.csv` rows | 933 | **933** |
| Every HRMS_ID written in a batch-2 table exists in `PERSONS` | 0 exceptions | **0** |
| No cell empty, "N/A", "-", "NOT ON RECORD" | 0 | **0** |
| No new officer created | 0 | **0** |
| `GRADATION_3768_ROWS.csv` rows | 1,135 | **1,135** |
| Nothing under `_00_Input_Raw_Sources/` changed | 0 | **1,467 re-hashed, 0 changed** |

| Batch-2 output | Rows |
|---|---|
| `ORDER_MOVEMENTS_BATCH2.csv` | 530, 396 distinct officers, 121 cut from tables with postings |
| `UNMATCHED_NAMES_BATCH2.csv` | 1,691 |
| `ESTABLISHMENT_LEADS_BATCH2.csv` | 374 |

## 7. Hand-off

`Prompt/20260914_AVD_CIOS_Message_to_Fable_Job_03_Rebuild_On_Corrected_Batch2.md` —
for the Fable 5.1 session that owns the master.
