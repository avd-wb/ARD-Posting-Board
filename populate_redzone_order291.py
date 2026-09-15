#!/usr/bin/env python3
"""
populate_redzone_order291.py
Populates Category 2 of the Red Zone (pending_transfers_redzone) with officers whose tenure
exceeds the statutory norm under Order No. 291 of 2009 (Memo No. 291-AR & AH/3A-11/06 dt. 19.02.2009):
- 4.0 years for difficult, hill, Sundarbans, and Jungle Mahal zones/blocks
- 5.0 years for general areas
Calculated from the date of joining at current station (last available transfer order).
"""

import sqlite3
import re
import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ard_master_truth.db")

def populate_order291_tenure():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f"Connecting to database: {DB_PATH}")

    # 1. Clear existing arbitrary 10y records or previous tenure records
    cur.execute("DELETE FROM pending_transfers_redzone WHERE category IN ('tenure_10y', 'tenure_over');")
    print(f"Deleted old tenure records from pending_transfers_redzone.")

    # 2. Query all over-tenure posts from sacrosanct_cadre_posts
    cur.execute("""
        SELECT post_id, post_sl, district, block, establishment, designation,
               incumbent_name, incumbent_hrms, incumbent_doj, incumbent_tenure,
               tenure_norm, tenure_over_flag, incumbent_dor, latitude, longitude,
               avd_member
        FROM sacrosanct_cadre_posts
        WHERE tenure_over_flag = 'Yes' AND incumbent_hrms IS NOT NULL AND incumbent_hrms != ''
        ORDER BY post_id;
    """)
    posts = [dict(r) for r in cur.fetchall()]
    print(f"Found {len(posts)} over-tenure posts in sacrosanct_cadre_posts.")

    inserted_count = 0
    ref_date = datetime.datetime(2026, 9, 15)

    for p in posts:
        t_str = p.get("incumbent_tenure") or ""
        doj = p.get("incumbent_doj") or ""
        norm = float(p.get("tenure_norm") or 5.0)

        # Parse years from tenure string e.g. "9 y 2 m 26 d"
        m = re.search(r'(\d+)\s*y', t_str)
        years = float(m.group(1)) if m else 0.0
        mm = re.search(r'(\d+)\s*m', t_str)
        if mm:
            years += round(float(mm.group(1)) / 12.0, 1)

        # Fallback to DOJ calculation if tenure string lacks years
        if years == 0.0 and doj and len(doj) >= 10:
            try:
                doj_clean = doj[:10]
                doj_dt = datetime.datetime.strptime(doj_clean, "%Y-%m-%d")
                years = round((ref_date - doj_dt).days / 365.25, 1)
                t_str = f"{years:.1f} years"
            except Exception:
                pass

        excess = max(0.0, years - norm)
        # Priority score: 85 base + 1.5 per excess year, capped at 98
        priority_score = min(98, int(85 + excess * 1.5))

        is_difficult = (norm <= 4.0)
        zone_type = "Difficult / Hill / Sundarbans / Jungle Mahal (4-year norm)" if is_difficult else "General Area (5-year norm)"
        block_label = f" / {p['block']}" if p.get("block") and p["block"] != "Under verification" else ""
        
        reason = (
            f"Officer has completed {t_str or f'{years:.1f} years'} in station (norm: {int(norm)} years under Order No. 291 of 2009 for {p['district']}{block_label} — {zone_type}). "
            f"Mandatory rotational transfer due."
        )

        cur.execute("""
            INSERT INTO pending_transfers_redzone (
                category, category_label, priority_score, officer_name, hrms_id, gender,
                current_designation, current_establishment, current_block, current_district,
                tenure_years, tenure_str, date_of_joining, date_of_retirement, transfer_reason,
                target_post, target_district, ground_type, post_id, latitude, longitude, status, avd_member
            ) VALUES (
                'tenure_over', 'Order 291 Over-Tenure', ?, ?, ?, 'Male',
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                'Routine Cadre Rotation / Transferable Station', ?, ?, ?, ?, ?, 'Pending Rotation Order', ?
            );
        """, (
            priority_score,
            p["incumbent_name"],
            p["incumbent_hrms"],
            p["designation"],
            p["establishment"],
            p["block"] or "HQ",
            p["district"],
            float(years),
            t_str or f"{years:.1f} years",
            doj or "—",
            p.get("incumbent_dor") or "—",
            reason,
            p["district"],
            f"Order 291 Over-Tenure (>{int(norm)}y)",
            p["post_id"],
            p["latitude"],
            p["longitude"],
            p.get("avd_member") or "No"
        ))
        inserted_count += 1

    conn.commit()
    print(f"Successfully inserted {inserted_count} Order 291 over-tenure records into pending_transfers_redzone.")

    # Print summary of categories
    cur.execute("SELECT category, category_label, COUNT(*) FROM pending_transfers_redzone GROUP BY category;")
    print("\nUpdated Red Zone Categories Summary:")
    for row in cur.fetchall():
        print(f"  - {row[0]} ({row[1]}): {row[2]} records")

    cur.execute("SELECT COUNT(*) FROM pending_transfers_redzone;")
    total = cur.fetchone()[0]
    print(f"\nTotal Actionable Red Zone Transfers: {total}")

    conn.close()

if __name__ == "__main__":
    populate_order291_tenure()
