#!/usr/bin/env bash
# ==============================================================================
# West Bengal Animal Resources Development Department (ARD)
# Smart Posting Decision Board & AI Cadre Management Platform
# ==============================================================================

cd "/Users/nirmalyaranjansarkar/Projects/AVD_AG" || exit 1

echo "========================================================================"
echo "  GOVERNMENT OF WEST BENGAL | ANIMAL RESOURCES DEVELOPMENT DEPARTMENT  "
echo "        Smart Posting Decision Board & AI Cadre Management Engine       "
echo "========================================================================"
echo "Master Source of Truth: ard_master_truth.db (1,899 Cadre Posts)"
echo "Starting Application Server on http://127.0.0.1:8000..."
echo "Press CTRL+C to stop the server."
echo ""

python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
