# Deploy WB ARD Smart Decision Board to Vercel via GitHub

This guide explains how to deploy this application to **Vercel** with continuous deployment from **GitHub**, integrated with **Google AI Studio (Gemini 2.0 Flash / Flash-Lite)**.

---

## 1. Quick Architecture Overview

* **Frontend**: Responsive Single Page Application (Tailwind CSS, Lucide icons, Vanilla JS) served statically by Vercel's global edge network.
* **Backend**: FastAPI running on **Vercel Serverless Functions** (`api/index.py` with `@vercel/python`).
* **Database**: `ard_master_truth.db` (SQLite) bundled into the deployment for ultra-fast, zero-latency serverless reads.
* **AI Intelligence**: **Google AI Studio Gemini API** (`gemini-2.0-flash` or `gemini-1.5-flash` or `gemini-2.0-flash-lite`) via `httpx`.

---

## 2. Step-by-Step Deployment Instructions

### Step 1: Push the Codebase to GitHub
1. In your terminal, initialize git (if not already done) and commit the files:
   ```bash
   cd /Users/nirmalyaranjansarkar/Projects/AVD_AG
   git init
   git add .
   git commit -m "Initial commit: ARD Decision Board & AI Cadre System with Google Sheets & Gemini 2.0"
   ```
2. Create a new repository on your GitHub account (e.g. `wb-ard-decision-board`).
3. Push to GitHub:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/wb-ard-decision-board.git
   git branch -M main
   git push -u origin main
   ```

---

### Step 2: Get a Free Gemini API Key from Google AI Studio
1. Visit **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Sign in with your Google account.
3. Click **"Create API Key"** and copy the generated key.

---

### Step 3: Deploy on Vercel
1. Go to **[vercel.com](https://vercel.com)** and log in.
2. Click **"Add New..."** -> **"Project"**.
3. Select your GitHub repository (`wb-ard-decision-board`) and click **"Import"**.
4. In the **Configure Project** screen:
   * **Framework Preset**: Leave as *Other*.
   * **Root Directory**: `./` (Default).
5. Open the **Environment Variables** section and add:
   * **Key**: `GEMINI_API_KEY`
     * **Value**: *(Paste your API key from Google AI Studio)*
   * **Key**: `GEMINI_MODEL` *(Optional, defaults to `gemini-2.0-flash`)*
     * **Value**: `gemini-2.0-flash` *(or `gemini-1.5-flash` or `gemini-2.0-flash-lite`)*
6. Click **"Deploy"**.

Within ~60 seconds, Vercel will build and deploy the app to a production URL (e.g., `https://wb-ard-decision-board.vercel.app`).

---

## 3. Supported Google AI Studio Models

| Model | Value in `GEMINI_MODEL` | Speed | Best For |
| :--- | :--- | :--- | :--- |
| **Gemini 2.0 Flash** *(Default)* | `gemini-2.0-flash` | Ultra-fast (<1s) | Real-time administrative queries & policy reasoning |
| **Gemini 2.0 Flash Lite** | `gemini-2.0-flash-lite` | Instant | High-throughput batch allocations |
| **Gemini 1.5 Flash** | `gemini-1.5-flash` | Very fast | Standard transfers & roster calculations |
| **Gemini 1.5 Pro** | `gemini-1.5-pro` | Deep reasoning | Complex multi-tier restructuring & grievance resolutions |

---

## 4. Local Testing with Gemini API
You can also run locally with Gemini:
```bash
export GEMINI_API_KEY="your_api_key_here"
export GEMINI_MODEL="gemini-2.0-flash"
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Open `http://localhost:8000` and click the purple **"AI Assistant"** button in the top-right header to start chatting with Gemini about cadre posts!
