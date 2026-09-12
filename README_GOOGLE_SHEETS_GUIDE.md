# West Bengal ARD Department - Interactive Google Sheets Posting Dashboard

This guide explains how to use the dynamic transfer & posting cockpit: **`WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx`**.

---

## 1. Quick Start: How to Open & Share in Google Sheets

1. **Google Drive Folder**:
   The latest workbook and scripts are live in your Google Drive folder:
   [Google Drive Folder Link](https://drive.google.com/drive/u/0/folders/1BgJE4thWGsCLv4qFHqmWobW_met8UuEL)
2. **Open in Google Sheets**:
   - Double-click `WB_ARD_Interactive_Posting_Board_GoogleSheets_Ready.xlsx` in Google Drive. It opens directly to the **`Posting_Dashboard`** tab.
3. **Share with Committee Members**:
   - Click the blue **"Share"** button in the top-right corner to grant access to your team.

---

## 2. Key Enhancements & Verified Truth Solved

### ✅ Issue 1: Verified Full Officer Name for HRMS 1995004945
* **Previous Error**: Row 127 previously showed only `"Dr"` without a full name.
* **Master Truth Resolution**: Verified against official Cadre 1046 and HRMS records. Full name **`Dr. Soma Das (nee Saha)`** (DOB: 16/11/1970, Superannuation: 30/11/2030, Assistant Director, ARD (Admn.), Howrah District HQ) is now cleanly populated across all dashboard rows, database tables, and the Secretariat order schedule.

### ✅ Issue 2: Cross-Column Dynamic Dropdown Reduction & Vivid Red Duplicate Warning
* **Option Reduction in Dropdowns (Cross-Column Synchronized)**:
  - **The Core Rule**: Dropdowns will **ONLY NOT SHOW** posts that are already used up somewhere in **that column** OR in the **service utilized column**!
  - **Substantive Column (Column J)**:
    * As soon as a post is allotted in Column J, it is automatically filtered out from subsequent dropdowns (`Available_DD_Posts!$I$2:$I$243`).
    * If a post is assigned under Service Utilization in Column L, it is **also** automatically filtered out and will NOT show in Column J!
  - **Service Utilized Column (Column L)**:
    * As soon as a cadre or DD post is chosen for Service Utilization in Column L, it is automatically filtered out (`All_Cadre_Posts_1794!$J$2:$J$2037`).
    * If a post is assigned as a Substantive post in Column J, it is **also** automatically filtered out and will NOT show in Column L!
  - **Dynamic Reappearance**: If any officer's post assignment is cleared or changed, that post immediately becomes available and reappears in both dropdown lists.
* **Instant Red Duplicate Warning**:
  - If any post is duplicate-selected across Column J and/or Column L:
    * **Column J & Column L**: Immediately highlights in **BRIGHT RED** (`#FEE2E2` fill, `#991B1B` bold font).
    * **Column M (`Allotment & Transfer Status`)**: Displays `⚠️ DUPLICATE ALLOTMENT (X OFFICERS SELECTED)` in bold red.
    * **Column N (`Displaced / Alert Notes`)**: Displays `⚠️ ERROR: Post duplicate allotted across substantive/SU columns! Reassign post.` in bold red.
    * **Top KPI Card**: `⚠️ DUPLICATE ALERTS` turns RED and counts overallocated posts.
    * **Availability Sheets**: Turn bright red with status `⚠️ DUPLICATE ALLOTMENT!` and note `⚠️ OVERALLOCATED`.
    * **Google Apps Script `onEdit` Listener**: Delivers an immediate browser toast notification warning the administrator if a post is duplicate-assigned across columns.

### ✅ Issue 3: Explicit Block Names for Block-Level Posts
* **Previous Ambiguity**: Posts previously displayed generic department phrases like `"Block/Sub-Divisional Level Set up in Darjeeling District"`.
* **Standardized Nomenclature**: All block-level posts (`ABAHC`, `BAHC`, `BLDO`, `SAHC`, `VO`) now explicitly display their block name immediately after the designation:
  * `[285] Block Livestock Development Officer, Darjeeling Pulbazar dev Block, Bijanbari (Darjeeling)`
  * `[291] Veterinary Officer, BAHC, Darjeeling Pulbazar Block (Darjeeling)`
  * `[296] Veterinary Officer, ABAHC, Darjeeling Pulbazar Block (Darjeeling)`
  * `[318] Veterinary Officer, BAHC, Gorubathan Block (Kalimpong)`
  * `[387] Veterinary Officer, ABAHC, Dhupguri Block (Jalpaiguri)`
  * `[422] Veterinary Officer, BAHC, Alipurduar-I Block (Alipurduar)`
  * `[790] Veterinary Officer, SAHC, Bethuadahari Block (Nadia)`
  * `[812] Veterinary Officer, BAHC, Nakashipara Block (Nadia)`
* All 242 promotion candidates now have their present blocks or Headquarters fully specified (0 blank blocks).

---

## 3. Walkthrough of the `Posting_Dashboard` Tab (Master Cockpit)

### A. Executive Live KPIs (Rows 5 & 6)
* **TOTAL CADRE POSTS**: 1,794 sanctioned posts under Notification No. 1809.
* **CLEAR VACANCIES**: 750 available cadre posts.
* **AVAILABLE DD POSTS**: Live formula tracking remaining unallotted Deputy Director posts (`=COUNTIF(Available_DD_Posts!$F$2:$F$243, "AVAILABLE")`).
* **TOTAL ALLOTTED**: Live count of decisions made.
* **DISPLACED DUE TO SU**: Live count of collision events.
* **PENDING SELECTION**: Candidates awaiting post allocation.
* **⚠️ DUPLICATE ALERTS**: Flags any duplicate post allocations in bright red!

---

### B. Section 1: 50-Point Roster Promotion Console (242 Candidates)
* **Columns A - H**: Candidate profile (`Sl`, `Roster Pt & Quota`, `HRMS ID`, `Officer Name`, `Present Posting`, `Present Block`, `Present District`, `Superannuation DOR`).
* **Column I (`Stated Preferences`)**: Officer's stated choices for reference.
* **Column J (`Eligible Post Picker: Deputy Director`)**:
  - **Dynamic Drop-down**: Displays only unallotted posts from `Available_DD_Posts!$I$2:$I$243`.
* **Column K (`Enable Service Utilization?`)**:
  - **Toggle Drop-down**: Choose `NO` (direct substantive posting) or `YES` (attach Service Utilization).
* **Column L (`Service Utilization Post Picker`)**:
  - **Cadre Drop-down**: If SU is `YES`, click to select any station across all 1,794 cadre posts.
* **Column M (`Allotment & Transfer Status`)**:
  - Automatically turns:
    * 🟢 **Soft Green (`ALLOTTED DIRECT`)**: Substantive post selected without SU.
    * 🔵 **Soft Blue (`ALLOTTED WITH SU`)**: Substantive post + clear vacant SU post.
    * 🔴 **Soft Rose (`⚠️ SU COLLISION (DISPLACEMENT TRIGGERED)`)**: Chosen SU post is occupied! Incumbent officer flagged for transfer.
    * 🔴 **Bright Red (`⚠️ DUPLICATE ALLOTMENT`)**: Post selected for more than one candidate.
    * 🟡 **Soft Amber (`PENDING`)**: Awaiting allocation.
* **Column N (`Displaced Incumbent Status`)**:
  - Displays collision notices and marks displaced doctors as `MARKED AS ELIGIBLE OFFICER FOR TRANSFER DUE TO DISPLACEMENT`.
* **Columns O - Q**: Official Transfer Category, Present Pay Level (`Level 16`), and New Pay Level (`Level 19`).

---

### C. Section 2: Obliterated Post Rehabilitation (84 Serving Displaced Officers)
* Lists the 84 active officers serving on abolished posts under Notification No. 1808 (including Dr. Nirmalya Ranjan Sarkar at Sl. 48).
* Equipped with drop-downs for clear Assistant Director cadre vacancies (`Available_AD_Vacancies`) and SU toggles.

---

### D. Section 3: Transferable Displaced Officers Pool (From SU Collisions)
* Pre-configured queue where officers displaced by incoming SU allocations can immediately receive new substantive and SU postings.

---

## 4. The Other Interactive Sheets

| Tab Name | Purpose |
| :--- | :--- |
| **`Secretariat_Posting_Order`** | **Mirrors decisions live**: Compiles the official Government Order in the **exact 6 columns** required by the Secretariat (`Sl No`, `Name & Present Posting`, `Present Pay Level`, `Transfer by`, `Place of posting`, `Pay level upon transfer`). |
| **`Available_DD_Posts`** | **242 DD Posts**: Live allocation counter (`COUNTIF`). Displays status (`AVAILABLE`, `ALLOTTED`, `⚠️ DUPLICATE ALLOTMENT!`) and provides the dynamic unallotted list in Column I. |
| **`Available_AD_Vacancies`** | **157 Clear Vacancies** for absorbing obliterated officers, with dynamic dropdown filtering in Column I. |
| **`All_Cadre_Posts_1794`** | Complete lookup database of all 1,794 posts with explicit block-level names and live occupancy status (`Vacant` vs `Occupied`). |
| **`Instructions_&_Legend`** | Full guide and color legend. |

---

## 5. Companion Google Apps Script (`google_apps_script.js`)

The script includes:
1. **Real-Time `onEdit` Trigger**: Fires instantly when an officer selects a post in Column J and displays an immediate toast alert if duplicate-assigned.
2. **`⚡ Scan Collisions & Displacement Conflicts`**: Instant audit of substantive duplicates and SU collisions.
3. **`🔄 Prune Dropdowns (Hide Already Allotted Posts)`**: Dynamically hides already-selected posts.
4. **`🔑 Configure Google AI Studio Gemini API Key`**: Securely saves API key for Gemini models.
5. **`✨ Run AI Auto-Allotment with Gemini Flash`**: Intelligent transfer matching considering seniority, district, and preferences.
6. **`📄 Export Secretariat Order to Official Google Doc`**: Formats Memo 391 standard order in Google Drive.
