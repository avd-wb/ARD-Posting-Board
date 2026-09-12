# West Bengal ARD Smart Posting Board & Cadre Decision System

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Favd-wb%2FARD-Posting-Board)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![AI Studio](https://img.shields.io/badge/AI-Google%20AI%20Studio%20(Gemini%202.0%20Flash)-4285F4.svg)](https://aistudio.google.com/)

An enterprise-grade, statutory cadre decision and automated posting management system for the **Animal Resources Development (ARD) Department, Government of West Bengal**.

Built to resolve administrative transfer, promotion, service utilization, and cadre restructuring workflows with 100% data verification across all official government notifications, ROPA 2019 pay levels, and 50-point roster rules.

---

## 🏛️ Statutory Cadre Baseline & Master Source of Truth

The system is calibrated against official West Bengal Government statutory orders:

1. **Restructured Cadre Strength (Notification No. 1809-AR&AH/AD/0/3A-16/2025)**:
   - Exactly **1,794 sanctioned department cadre posts** (strictly excluding 105 ex-cadre WBACS posts).
   - Dynamic waterfall hierarchy breakdown by administrative tier, wing, and district.
2. **Post Obliteration & Redeployment (Notification No. 1808-AR&AH/AD/0/3A-16/2025)**:
   - **106 obliterated posts** tracked in real-time.
   - Displaced officer pool management ensuring zero administrative displacement without rehabilitation.
3. **50-Point Promotion Roster**:
   - **242 eligible officers** for promotion from Assistant Director to Deputy Director (Pay Level 16 → Level 19: Rs. 95,100 – Rs. 1,48,000).
   - Candidate preference tracking (Preferences 1–10, district preferences, spouse ground, board exam considerations).
4. **Area Tenure Rules (Govt Memo No. 291-AR&AH)**:
   - Special tenure enforcement: 4.0 years maximum tenure for Hill/Dooars/Western districts (Alipurduar, Coochbehar, Jalpaiguri, Darjeeling, Kalimpong, Purulia, Bankura, Jhargram, Paschim Medinipur) vs 5.0 years standard.
   - Real-time over-tenure alerts.
5. **Superannuation Schedule (WBSR Rule 75(a))**:
   - Automated Date of Retirement (DOR) calculation to the last calendar day of the officer's birth month.

---

## 🤖 Dual AI Engine: Google AI Studio & Gemini 2.0 Flash

The system natively integrates **Google AI Studio** with Gemini:

1. **AI-Powered Statutory Allotment Recommendation (`/api/simulation/recommend-allotment`)**:
   - Evaluates officer preference hierarchy, home/present district proximity, area tenure guidelines, and existing vacancies.
   - Formulates legally defensible statutory justifications citing specific government notifications and ROPA pay matrix levels.
2. **AI Cadre Copilot Assistant (`/api/ai/query`)**:
   - Answers complex administrative inquiries on cadre distribution, post availability, officer dossiers, and vacancy status.
   - Operates with `gemini-2.0-flash` or `gemini-1.5-flash` with zero-latency responses.
3. **Google Sheets AI Allotment Automation**:
   - Directly calls Gemini from Apps Script (`runGeminiAutoAllot`) to suggest optimal posting cells in the interactive spreadsheet.

---

## 🚀 Live Hosting & Continuous Deployment Workflow

This repository enables a tri-directional version control and hosting pipeline:

- **GitHub Repository**: `avd-wb/ARD-Posting-Board` (single source of truth for code and versioning).
- **Vercel Serverless Functions**: Deploys the FastAPI application and static dashboard automatically upon pushing to `main`.
- **Google AI Studio**: Directly integrates with the repository for agent workflows and Gemini prompt tuning.

---

## 💻 Local Setup & Development

### 1. Clone the Repository
```bash
git clone https://github.com/avd-wb/ARD-Posting-Board.git
cd ARD-Posting-Board
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file (refer to `.env.example`):
```env
GEMINI_API_KEY=your_google_ai_studio_api_key
GEMINI_MODEL=gemini-2.0-flash
PORT=8000
```

### 4. Run the Local Server
```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at `http://localhost:8000`.

---

## ☁️ Deploying to Vercel

1. **Import the Project into Vercel**:
   - Go to [Vercel Dashboard](https://vercel.com/dashboard).
   - Click **Add New** → **Project**.
   - Select the **`avd-wb/ARD-Posting-Board`** GitHub repository.
2. **Set Environment Variables**:
   - In Vercel Project Settings → **Environment Variables**, add:
     - `GEMINI_API_KEY`: Your Google AI Studio API key.
     - `GEMINI_MODEL`: `gemini-2.0-flash` (or `gemini-1.5-flash`).
3. **Deploy**:
   - Click **Deploy**. Vercel will build the serverless functions via `api/index.py` and serve the dashboard globally.

---

## 📊 Google Sheets Edition

For team members preferring spreadsheet-based workflows:
- Download the interactive Google Sheets template from the dashboard or generate via:
  ```bash
  python3 generate_posting_dashboard_sheet.py
  ```
- **Features**:
  - Mutual exclusive dynamic post reduction (Column J Substantive Post and Column L Service Utilization Post cannot conflict).
  - Prominent red duplicate collision highlight alerts.
  - One-click Gemini Auto-Allotment macro (`google_apps_script.js`).
  - Google Docs Gazette Order exporter.

---

## 📄 License & Government Notice

Confidential & Proprietary. Developed for official administrative decision support under the Directorate of Animal Resources & Animal Health, Government of West Bengal.
