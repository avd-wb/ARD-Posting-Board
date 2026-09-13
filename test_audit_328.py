import sqlite3
import openpyxl
import re

def clean(n):
    if not n: return ''
    n = re.sub(r'\(.*?\)', '', str(n))
    n = re.sub(r'^(dr\.|dr\s+|smt\.\s*|smt\s+)', '', n, flags=re.I)
    n = re.sub(r'[^a-zA-Z\s]', '', n)
    return ' '.join(n.lower().split())

conn = sqlite3.connect('ard_master_truth.db')
c = conn.cursor()

# Preload cadre_1794_posts
c.execute('SELECT post_sl, designation, establishment, block, district, incumbent_name, incumbent_hrms, service_utilized_flag FROM cadre_1794_posts')
cadre_by_hrms = {}
for r in c.fetchall():
    psl, des, est, blk, dist, inc_name, inc_hrms, su_flag = r
    if inc_hrms and str(inc_hrms).strip():
        cadre_by_hrms[str(inc_hrms).strip()] = {
            'post_sl': psl, 'designation': des, 'establishment': est, 'block': blk,
            'district': dist, 'name': inc_name, 'hrms': inc_hrms, 'su': su_flag
        }

# Preload master_all_cadre_employees
c.execute('SELECT hrms_id, officer_name, clean_name, designation, present_posting, establishment, district FROM master_all_cadre_employees')
all_cadre_by_hrms = {}
for r in c.fetchall():
    h, n, cn, des, pres, est, dist = r
    if h and str(h).strip():
        all_cadre_by_hrms[str(h).strip()] = {
            'hrms': h, 'name': n, 'clean_name': cn, 'designation': des,
            'present_posting': pres, 'establishment': est, 'district': dist
        }

# Preload preferences
wb_pref = openpyxl.load_workbook('/Users/nirmalyaranjansarkar/Projects/AVD/_00_Sources/01_Verified_Sources /20260906 Posting Preferences.xlsx', data_only=True)
ws_pref = wb_pref.active
pref_by_hrms = {}
for row in ws_pref.iter_rows(min_row=2, values_only=True):
    hrms = str(row[10]).strip() if row[10] else ''
    if hrms and len(hrms) >= 8:
        pref_by_hrms[hrms] = {
            'name': row[4],
            'pest': row[89],
            'pdist': row[90],
            'psu': row[92],
            'ppost_203': row[202]
        }

# Load schedule
c.execute('''
    SELECT sl_no, roster_sl, officer_name, clean_name, present_designation,
           present_establishment, present_block, present_district, present_post_full,
           present_su, hrms_id
    FROM master_final_order_schedule
    ORDER BY sl_no
''')
schedule = c.fetchall()

print(f"Auditing {len(schedule)} rows...")

# Specific ground truth overrides verified from official district reports
overrides = {
    '1992001867': {'block': 'Bongaon', 'estab': 'SAHC Bongaon, Sub-Divisional and Block Level Set up of North 24 Parganas District'}, # Dr. Basudev Sil
    '1994001537': {'block': 'Habra-I', 'estab': 'SAHC Habra-I, Sub-Divisional and Block Level Set up of North 24 Parganas District'}, # Dr. Nilay Kanti Biswas
    '1994000399': {'block': 'Memari-I', 'estab': 'SAHC Memari-I, Sub-Divisional and Block Level Set up of Purba Bardhaman'}, # Dr. Malay Kumar Roy
    '1994005813': {'district': 'Paschim Medinipur', 'block': 'Midnapore Sadar', 'estab': 'Office of the Deputy Director, ARD & PO, Training Institute, Paschim Medinipur'}, # Dr. Shantidev Bishayi
    '1994009135': {'block': 'Kalimpong', 'estab': 'Block Level Set up of Kalimpong District'}, # Dr. La Tshering Bhutia
    '2000010253': {'block': 'Kalimpong', 'estab': 'BAHC Kalimpong, Block Level Set up of Kalimpong District'}, # Dr. Kesang Bomzon
    '1994001175': {'block': 'Kolkata Police HQ', 'estab': 'Office of the Joint Commissioner of Police, Crime, Kolkata', 'district': 'Kolkata'}, # Dr. Santanu Acharya
    '2014003936': {'block': 'Kolkata Police HQ', 'estab': 'Office of the Joint Commissioner of Police, Crime, Kolkata', 'district': 'Kolkata'}, # Dr. Surajit Basu
    '2014004119': {'block': 'District HQ', 'estab': 'Office of the Deputy Director, ARD & PO, Malda', 'desig': 'Assistant Director, ARD (Veterinary)'}, # Dr. Halim Sarkar
}

diffs = []
for r in schedule:
    sl_no, rsl, name, c_name, pdes, pest, pblk, pdist, ppost_full, psu, hrms = r
    h_str = str(hrms).strip() if hrms else ''
    
    cad = cadre_by_hrms.get(h_str)
    all_cad = all_cadre_by_hrms.get(h_str)
    pref = pref_by_hrms.get(h_str)
    
    new_des = pdes
    new_est = pest
    new_blk = pblk
    new_dist = pdist
    new_su = psu if psu and psu != 'None' else 'Nil'
    reasons = []
    
    # 1. District anomalies
    if pdist == 'Training Institutes':
        new_dist = 'Paschim Medinipur'
        reasons.append('District was erroneously listed as "Training Institutes" -> corrected to Paschim Medinipur')
    elif pdist == 'Haringhata Farm':
        new_dist = 'Nadia'
        new_blk = 'Haringhata'
        reasons.append('District was erroneously listed as "Haringhata Farm" -> corrected to Nadia (Block: Haringhata)')
    elif pdist == 'Siliguri':
        new_dist = 'Darjeeling'
        new_blk = 'Siliguri'
        reasons.append('District was erroneously listed as "Siliguri" -> corrected to Darjeeling (Siliguri Sub-Division / SMP)')
        
    # 2. Overrides from district reports
    if h_str in overrides:
        ov = overrides[h_str]
        if 'district' in ov and ov['district'] != new_dist:
            new_dist = ov['district']
            reasons.append(f"District updated to {new_dist}")
        if 'block' in ov and ov['block'] != new_blk:
            old_b = new_blk
            new_blk = ov['block']
            reasons.append(f"Block restored to {new_blk} (was '{old_b}') from verified district report")
        if 'estab' in ov and ov['estab'] != new_est:
            new_est = ov['estab']
            reasons.append(f"Establishment corrected from official district report")
        if 'desig' in ov and ov['desig'] != new_des:
            new_des = ov['desig']
            reasons.append(f"Designation corrected to {new_des}")
            
    # 3. Clean designations with embedded SU notes
    if 'su at dcf-domkal' in new_des.lower():
        new_des = 'Assistant Director, ARD (State Animal Husbandry)'
        new_su = 'Duck Breeding Farm, Domkal, Murshidabad'
        reasons.append('Extracted embedded SU notes from designation into Service Utilized field')
    elif 's/u as deo' in new_des.lower():
        new_des = 'Assistant Director, ARD (Microbiology)'
        new_su = 'District Executive Officer (DEO), PBGSBS, Murshidabad'
        reasons.append('Extracted embedded SU notes from designation into Service Utilized field')
    elif new_des == 'DISTRICT VETERINARY OFFICER':
        new_des = 'District Veterinary Officer'
        reasons.append('Cleaned uppercase designation')
    elif new_des == 'AD, ARD (DI), Murshidabad':
        new_des = 'Assistant Director, ARD (Disease Investigation)'
        reasons.append('Standardized abbreviated designation')
    elif new_des == 'Dist. Vety. Officer, Hooghly':
        new_des = 'District Veterinary Officer'
        reasons.append('Standardized abbreviated designation')
    elif new_des == 'AD ARD (DI)':
        new_des = 'Assistant Director, ARD (Disease Investigation)'
        reasons.append('Standardized abbreviated designation')
    elif new_des == 'AD ARD (MI)':
        new_des = 'Assistant Director, ARD (Microbiology)'
        reasons.append('Standardized abbreviated designation')
    elif new_des == 'AD ARD (CMS)':
        new_des = 'Assistant Director, ARD (Central Medical Stores)'
        reasons.append('Standardized abbreviated designation')
    elif new_des == 'AD ARD(C&DD)':
        new_des = 'Assistant Director, ARD (Cattle & Dairy Development)'
        reasons.append('Standardized abbreviated designation')
        
    # 4. Cadre block recovery for block officers
    if (not new_blk or new_blk.strip() == '') and cad and cad.get('block'):
        cad_b = cad['block'].strip()
        if cad_b and cad_b.lower() not in [new_dist.lower(), 'district hq', 'directorate hq', 'iah&vb']:
            new_blk = cad_b
            reasons.append(f"Missing block restored from Cadre Post #{cad['post_sl']} ({cad_b})")
            
    # 5. Standardize generic establishment
    if 'sub-divisional and block level set up of' in (new_est or '').lower() and new_blk and new_blk not in ['District HQ', 'Directorate HQ']:
        if 'sahc' in new_des.lower() and not new_est.startswith('SAHC'):
            new_est = f"SAHC {new_blk}, Sub-Divisional and Block Level Set up of {new_dist}"
            reasons.append(f"Specified SAHC field establishment ({new_blk})")
        elif ('bahc' in new_des.lower() or 'bldo' in new_des.lower()) and not new_est.startswith('BAHC') and not new_est.startswith('BLDO'):
            new_est = f"BAHC {new_blk}, Sub-Divisional and Block Level Set up of {new_dist}"
            reasons.append(f"Specified BAHC field establishment ({new_blk})")
        elif 'abahc' in new_des.lower() and not new_est.startswith('ABAHC'):
            new_est = f"ABAHC {new_blk}, Sub-Divisional and Block Level Set up of {new_dist}"
            reasons.append(f"Specified ABAHC field establishment ({new_blk})")
            
    # 6. District HQ / Directorate HQ standardized blocks
    if (not new_blk or new_blk.strip() == ''):
        if any(k in new_des.lower() for k in ['dvo', 'district veterinary officer', 'assistant director', 'principal']):
            if new_dist in ['Kolkata']:
                new_blk = 'Directorate HQ'
            else:
                new_blk = 'District HQ'
            reasons.append(f"Standardized institutional headquarters location as '{new_blk}'")
            
    # Re-synthesize full post
    if new_blk and new_blk not in ['District HQ', 'Directorate HQ']:
        new_ppost_full = f"{new_des}, {new_est}, {new_blk}, {new_dist}"
    else:
        new_ppost_full = f"{new_des}, {new_est}, {new_dist}"
        
    if reasons:
        diffs.append({
            'sl_no': sl_no,
            'rsl': rsl,
            'name': name,
            'hrms': hrms,
            'old_post': ppost_full,
            'new_post': new_ppost_full,
            'old_dist': pdist,
            'new_dist': new_dist,
            'old_blk': pblk,
            'new_blk': new_blk,
            'old_est': pest,
            'new_est': new_est,
            'old_des': pdes,
            'new_des': new_des,
            'old_su': psu,
            'new_su': new_su,
            'reasons': reasons
        })

print(f"Total officers with discrepancies/flaws corrected: {len(diffs)}")
