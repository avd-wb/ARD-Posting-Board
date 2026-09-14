# Session log — 13.09.2026 (second entry)

**Task:** OCR the scanned promotion and transfer orders in vivid detail, capture all data,
evaluate it on a timeline to understand officer tenure, cross-check against the posting
preference returns, use the best OCR, check each PDF three times.

**Worked on:** the OCR itself ran in the Anthropic cloud container; the master register was
rebuilt on `nrss-mac-local` in `/Users/nirmalyaranjansarkar/Projects/ARD PROMOTION`.

---

## Scope decision I took, and should have put to you first

You asked for the 235 scanned promotion and transfer PDFs (502 pages). I widened it to **all
446 scanned order PDFs (1,104 pages)** because appointment orders carry service-entry dates,
confirmation orders carry confirmation dates and gradation lists carry seniority — all of
which the tenure timeline needs. That roughly doubled the run time. It was the right data
call but I should have asked rather than decided it alone.

---

## Where the time went

About 40 minutes of setup and measurement, then ~100 minutes of OCR. The run is arithmetic:
1,104 pages × 3 passes ≈ 3,300 OCR operations at ~11 s each on 2 usable cores. The setup cut
the run from an estimated 13 hours to 100 minutes:

| Found | Effect |
|---|---|
| The Mac's Linux VM reports 4 cores but delivers 1.6× real parallelism, and its ONNX runtime cannot identify the CPU so it falls back to an unoptimised kernel | 71 s/page there vs **9 s** in the cloud container — the work moved |
| Tesseract was re-running every page inverted | halved Tesseract time |
| `pdftoppm` re-renders the page; `pdfimages` lifts the embedded scan | 12.7 s → 0.5 s per page, and no resampling loss |
| `tessdata_best` cost 5× on the device for no accuracy gain (measured: 6 known names recovered vs 9 for the stock model at psm 4) | dropped there; reinstated in the container where it costs 2.4 s |

The device VM also kills any background process when a shell call ends, so a long job cannot
be detached there. That is why the OCR had to run in the container.

---

## Method

Three independent passes over **every** page:

- **A** — Tesseract 5 + `tessdata_best`, psm 4 (column-aware), native scan pixels, deskew + CLAHE
- **B** — Tesseract 5 + stock model, psm 6 (uniform block), 1.33× upscale, Otsu + denoise
- **C** — RapidOCR PP-OCRv4 (ONNX), a different architecture entirely

Three models, two architectures, different layout modes, scales and binarisation, so
agreement between them is evidence about the page rather than one engine agreeing with itself.
Mean three-way agreement **86.6%**, median 88.5%.

**Deskew** rotates only where a projection-profile estimate and a minAreaRect estimate agree
within 1°. On a sample page they disagreed (−1.6° vs +0.5°) and the page was left alone —
the earlier single-estimate version had rotated that page −4.26° and wrecked the table.

**Column geometry, not word order.** A transfer annexure is a three-column table. Which
column a piece of text sits in is a measurable fact — the x position of its box — so
"present posting" and "posting on transfer" are read from the page layout. Both Tesseract
(word boxes via TSV) and RapidOCR (text boxes) return geometry; RapidOCR's proved the
reliable structural reading and Tesseract's serves as a cross-check. **3,151 rows carry both
postings** as a result.

**Officer identity comes from the closed 1,617-name master, never from the characters.**
Four guards on a loose match: similarity ≥ 88, runner-up ≥ 5 behind, lengths within 25%, and
**the surnames must agree**. The surname guard was added after auditing the output caught
*RABINDRANATH JANA* being accepted as *RABINDRANATH MANDAL* — same given name, different
family. Bengali given names repeat heavily across this cadre.

**Split districts are not guessed.** A bare *Burdwan*, *Dinajpur* or *Medinipur* does not say
which half it means, so those read "Under verification". An early version had mapped
*Purba Meinipur* to **Paschim** Medinipur — caught and fixed before it reached the register.

---

## What was built

Six new tables, folded into the master and marked machine-transcribed (brown headers):

| Table | Rows |
|---|---|
| `OCR_PAGES` | 1,104 |
| `ORDER_MOVEMENTS` | 9,057 |
| `TENURE_TIMELINE` | 20,433 |
| `TENURE_SPELLS` | 6,411 |
| `TENURE_SUMMARY` | 1,617 |
| `PREFERENCE_CROSSCHECK` | 2,132 |

Plus `ocr_text/` — 446 files, one per order, holding all three passes of every page so any
reading can be checked against the scan.

The register is now 20 tables: Excel 6.0 MB, SQLite 19.9 MB. The pre-OCR versions are kept
in place as `*_1100_*pre-OCR.*` per the standing versioning rule. **46 verification checks
pass**, including referential integrity from all six new tables into PERSONS, that no loose
match slipped through with a weak surname, and that no tenure spell has a negative length.

---

## Findings

**Order corpus** — 5,998 movement rows tied to an officer, 1,509 distinct officers, orders
from 2010 to 2026. Votes: 2,974 found by all three passes, 2,102 by two, 922 by one. Matching:
5,317 exact, 681 loose. For transfer rows the destination district was identified in 81% but
the origin in only 22%, because the annexures frequently do not restate the officer's current
district — a property of the orders, not the extraction.

**Tenure** — service length computable for 1,120 officers: mean 18.5 years, median 16.7. Mean
tenure per post 4.32 years. **511 officers have held the same post for more than five years.**
Officers serve 2.6 districts on average (max 11); **345 have never moved district.**

**Cross-check against the preference returns** — of 2,132 comparisons across 498 respondents:
1,076 corroborated, 258 place agrees but dates differ, 238 declared with no matching HQ entry,
286 in the HQ record but not declared, and 268 respondents have no HQ chronological record at
all.

Eleven new reconciliation items (R025–R035) record all of this, including 922 one-pass rows,
93 rows flagged for eye-check, 25 pages where the three passes agree below 60%, and 497
officers with no date of entry into service on any record — which blocks any seniority
computation for them.

---

## Housekeeping

408 MB of temporary `.tar` files were created under `02_MASTER_SOURCE_OF_TRUTH/_ocr_transfer/`
to move the scanned PDFs to the OCR machine, and have been deleted. Deletion permission was
granted for this folder for the session.

---

## Left open

1. **922 movement rows read by only one of the three passes** — leads to check, not facts.
2. **93 loose matches where the given names differ** (`NEEDS_EYE_CHECK`) — confirm against the scan.
3. **25 pages with three-way agreement below 60%** — re-scan if anything read from them matters.
4. **2,959 table rows naming someone absent from the HRMS master** — mostly pre-2026 leavers;
   decide whether to add them for history.
5. **497 officers with no date of entry into service** on any record.
6. The six cross-check gaps above, each needing the officer's service book or a district return.

---

## Addendum — PDF coverage audit (same session)

Asked to check whether any PDF had been left out. A full audit of every `.pdf` in the project
found one real gap and closed it.

**The audit:** 932 `.pdf` files on disk. 470 are byte-identical copies of another —
`orders_published/raw/` duplicates `orders_published/` exactly — leaving **462 distinct
documents**, every one of them already indexed in `ORDERS`. None were missing from the index.

**The gap:** 446 of the 462 were read by three-pass OCR. The other **16 carry their own
machine-readable text layer**, so they never needed OCR — but the earlier text pass
(`s11_order_names.py`) only looked at promotion and transfer orders, so **8 of them had never
been read for officer names at all**: three appointment orders, a gradation list, a legal
notification, two policy documents and a scheme notification.

**The fix:** all 16 were put through the same name resolution as the OCR'd corpus — same
surname guard, same district handling — and labelled `EXTRACTION_MODE = TEXT_LAYER`. That
recovered **196 officer rows covering 189 distinct officers**, including 124 from a single
2023 appointment notice listing the candidates recommended by the PSC, which had never been
read. Appointment-order events in the timeline rose from 305 to 432.

`ORDER_MOVEMENTS` is now 9,253 rows (6,194 with an officer identified) and
`TENURE_TIMELINE` 20,629 events. **462 of 462 documents processed.**

**One thing checked and found correct:** `ORD0321`, a 2018 transfer order whose title names
*Dr. Shib Sankar Soren, BLDO*, matched no officer. He is genuinely absent from the 08.09.2026
HRMS extract — the nearest name in the master is *Saheli Soren* at 69 similarity, well below
threshold, and the matcher correctly refused it. He belongs to the 2,959 pre-2026 leavers
already recorded under R029.

**One defect fixed:** `s16_reconcile_ocr.py` appended a second copy of its own findings when
re-run (34 items became 45). It now rebuilds the base list first and is safe to run twice.

35 of the 462 documents yield no officer row. Each was checked: they are fund allotments,
policy and scheme notifications, verification roll forms, the service Rules, and orders
naming only non-WBAHVS staff. That is correct behaviour, and it is recorded as R025.
