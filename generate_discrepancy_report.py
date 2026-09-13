import sqlite3
from fix_schedule_current_postings import run_fix

comparison_log = run_fix()
print(f"Total corrections logged: {len(comparison_log)}")

# Categorize
by_cat = {
    "1. District Column Anomalies (Establishment / Complex as District)": [],
    "2. Embedded Administrative Notes & Corrupted Designations": [],
    "3. Missing Block Field Stations Restored": [],
    "4. Generic Establishment Restored to Specific Field Unit (SAHC/BAHC/ABAHC)": [],
    "5. Institutional Headquarters (District HQ / Directorate HQ) Standardized": []
}

for item in comparison_log:
    reasons = "; ".join(item['flaws'])
    if "District listed as" in reasons or "District updated" in reasons:
        by_cat["1. District Column Anomalies (Establishment / Complex as District)"].append(item)
    elif "Embedded SU notes" in reasons or "Normalized all-caps" in reasons or "Standardized designation" in reasons:
        by_cat["2. Embedded Administrative Notes & Corrupted Designations"].append(item)
    elif "Missing block restored" in reasons or "Block restored" in reasons:
        by_cat["3. Missing Block Field Stations Restored"].append(item)
    elif "Specified" in reasons:
        by_cat["4. Generic Establishment Restored to Specific Field Unit (SAHC/BAHC/ABAHC)"].append(item)
    else:
        by_cat["5. Institutional Headquarters (District HQ / Directorate HQ) Standardized"].append(item)

for cat_name, items in by_cat.items():
    print(f"{cat_name}: {len(items)} officers")

