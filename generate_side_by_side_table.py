import sqlite3
import openpyxl

wb_orig = openpyxl.load_workbook('/Users/nirmalyaranjansarkar/Projects/AVD_AG/comments_final.xlsx', data_only=True)
ws_orig = wb_orig['11_Column_Master_Posting_Order']

conn = sqlite3.connect('ard_master_truth.db')
c = conn.cursor()

c.execute('''
    SELECT sl_no, roster_sl, officer_name, present_designation,
           present_establishment, present_block, present_district, present_post_full,
           present_su, hrms_id
    FROM master_final_order_schedule
    ORDER BY sl_no
''')
corrected_rows = {r[0]: r for r in c.fetchall()}

comparison = []
for r_idx in range(2, 312):
    orig_sl = ws_orig.cell(r_idx, 1).value
    orig_rsl = ws_orig.cell(r_idx, 2).value
    orig_name = ws_orig.cell(r_idx, 3).value
    orig_des = ws_orig.cell(r_idx, 4).value or ''
    orig_est = ws_orig.cell(r_idx, 5).value or ''
    orig_blk = ws_orig.cell(r_idx, 6).value or ''
    orig_dist = ws_orig.cell(r_idx, 7).value or ''
    orig_post = ws_orig.cell(r_idx, 8).value or ''
    
    if not orig_sl or orig_sl not in corrected_rows:
        continue
        
    corr = corrected_rows[orig_sl]
    (c_sl, c_rsl, c_name, c_des, c_est, c_blk, c_dist, c_post, c_su, c_hrms) = corr
    
    flaws = []
    category = "General"
    if orig_dist != c_dist:
        flaws.append(f"District was listed as '{orig_dist}' -> Corrected to '{c_dist}'")
        category = "1. District Anomaly"
    elif (not orig_blk or orig_blk.strip() == '') and c_blk and c_blk not in ['District HQ', 'Directorate HQ']:
        flaws.append(f"Missing block restored to '{c_blk}' (was blank)")
        category = "2. Missing Field Block Restored"
    elif any(k in orig_des.lower() for k in ['su at', 's/u as', 'dist.', 'd.v.o.']) or orig_des.isupper() or 'AD, ARD (DI)' in orig_des:
        flaws.append(f"Designation cleaned from '{orig_des}' -> '{c_des}'")
        category = "3. Corrupted Designation / Embedded Notes"
    elif 'sub-divisional and block level' in orig_est.lower() and c_est != orig_est:
        flaws.append(f"Generic establishment '{orig_est}' replaced with specific unit '{c_est}'")
        category = "4. Generic Establishment Specified"
    elif (not orig_blk or orig_blk.strip() == '') and c_blk in ['District HQ', 'Directorate HQ']:
        flaws.append(f"Institutional station standardized as '{c_blk}' (was blank)")
        category = "5. Institutional HQ Standardized"
        
    if flaws:
        comparison.append({
            'sl_no': c_sl,
            'roster_sl': c_rsl,
            'name': c_name,
            'hrms_id': c_hrms,
            'orig_post': orig_post,
            'corr_post': c_post,
            'category': category,
            'flaws': "; ".join(flaws)
        })

print(f"Total compared: {len(comparison)}")
by_cat = {}
for item in comparison:
    by_cat.setdefault(item['category'], []).append(item)

for cat, items in sorted(by_cat.items()):
    print(f"\n### {cat} ({len(items)} officers)")
    for it in items[:6]:
        print(f"- **Sl #{it['sl_no']} ({it['name']}) [HRMS {it['hrms_id']}]:**")
        print(f"  - **Old/PDF Post**: `{it['orig_post']}`")
        print(f"  - **Ground Truth Post**: `{it['corr_post']}`")
        print(f"  - **Root Cause & Fix**: {it['flaws']}")
