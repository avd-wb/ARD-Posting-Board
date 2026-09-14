#!/usr/bin/env python3
"""
monitor_and_rotate_review.py
Security monitor and automated password rotator for ARD Promotion & Transfer Review Board (337).

Rules:
1. Trigger A: 20 or more distinct IPs active concurrently on the review board in a 15-minute window.
2. Trigger B: 48 hours elapsed since 2026-09-14 19:33:55 IST (Deadline: 2026-09-16 19:33:55 IST).
Whichever occurs earlier triggers:
- Immediate password rotation to a new secure random passphrase.
- Update to server-side and client-side password hash.
- Automated commit & deployment to Vercel production (npx vercel --prod --yes).
- Direct email dispatch to nirmalyaranjansarkar@gmail.com via macOS Mail.app (with alert logging).
- Audit log entry.
"""

import os
import sys
import json
import time
import hashlib
import secrets
import string
import datetime
import subprocess
import urllib.request
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYTICS_DB = os.path.join(BASE_DIR, "ard_analytics.db")
REVIEW_HTML = os.path.join(BASE_DIR, "static", "review.html")
STATE_FILE = os.path.join(BASE_DIR, "review_security_state.json")

RECIPIENT_EMAIL = "nirmalyaranjansarkar@gmail.com"
START_TIME_STR = "2026-09-14 19:33:55"
DEADLINE_STR = "2026-09-16 19:33:55"
IP_THRESHOLD = 20

def get_ist_now() -> datetime.datetime:
    return datetime.datetime.now()

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "current_password": "lehalwa",
        "current_hash": hashlib.sha256("lehalwa".encode("utf-8")).hexdigest(),
        "created_at": START_TIME_STR,
        "expires_at": DEADLINE_STR,
        "ip_threshold": IP_THRESHOLD,
        "is_rotated": False,
        "rotation_history": []
    }

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def generate_secure_password() -> str:
    suffix = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    return f"wbard_rev_{suffix}"

def send_email_alert(recipient: str, subject: str, body: str) -> bool:
    print(f"Attempting to dispatch email to {recipient} via macOS Mail.app...")
    safe_subject = subject.replace('"', '\\"')
    safe_body = body.replace('"', '\\"').replace("\n", "\\n")
    
    applescript = f'''
    tell application "Mail"
        set newMessage to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:false}}
        tell newMessage
            make new to recipient at end of to recipients with properties {{address:"{recipient}"}}
            send
        end tell
    end tell
    '''
    try:
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            print("✓ Email dispatched successfully via macOS Mail.app!")
            return True
        else:
            print(f"Warning: AppleScript Mail error: {res.stderr.strip()}")
    except Exception as e:
        print(f"Warning: Could not invoke AppleScript Mail: {e}")

    alert_log = os.path.join(BASE_DIR, "SECURITY_EMAIL_ALERTS.log")
    with open(alert_log, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] TO: {recipient}\nSUBJECT: {subject}\n\n{body}\n{'='*60}\n\n")
    print(f"Recorded alert in {alert_log}")
    return False

def get_concurrent_ips_count() -> int:
    distinct_ips = set()
    if os.path.exists(ANALYTICS_DB):
        try:
            conn = sqlite3.connect(ANALYTICS_DB)
            fifteen_mins_ago = (datetime.datetime.now() - datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.cursor()
            rows = cur.execute(
                "SELECT DISTINCT ip_address FROM visitor_sessions WHERE last_seen >= ?", 
                (fifteen_mins_ago,)
            ).fetchall()
            for r in rows:
                if r[0]:
                    distinct_ips.add(r[0])
            conn.close()
        except Exception as e:
            pass
            
    try:
        req = urllib.request.Request(
            "https://ard-posting-board.vercel.app/api/analytics/stats",
            headers={"User-Agent": "ARD-Security-Monitor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            active_now = data.get("active_online_now", 0)
            if active_now > len(distinct_ips):
                return active_now
    except Exception:
        pass
        
    return len(distinct_ips)

def check_conditions(state: dict):
    now = get_ist_now()
    deadline = datetime.datetime.strptime(state.get("expires_at", DEADLINE_STR), "%Y-%m-%d %H:%M:%S")
    time_expired = now >= deadline
    
    current_ips = get_concurrent_ips_count()
    ip_threshold_breached = current_ips >= state.get("ip_threshold", IP_THRESHOLD)
    
    auto_rotate_enabled = state.get("auto_rotate", False)
    return {
        "now": now.strftime("%Y-%m-%d %H:%M:%S"),
        "deadline": deadline.strftime("%Y-%m-%d %H:%M:%S"),
        "time_expired": time_expired,
        "seconds_remaining": max(0, int((deadline - now).total_seconds())),
        "concurrent_ips": current_ips,
        "ip_threshold": state.get("ip_threshold", IP_THRESHOLD),
        "ip_threshold_breached": ip_threshold_breached,
        "auto_rotate_enabled": auto_rotate_enabled,
        "should_rotate": auto_rotate_enabled and (time_expired or ip_threshold_breached) and not state.get("is_rotated", False)
    }

def rotate_password(trigger_reason: str):
    state = load_state()
    old_pw = state["current_password"]
    new_pw = generate_secure_password()
    new_hash = hashlib.sha256(new_pw.encode("utf-8")).hexdigest()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n[!] INITIATING PASSWORD ROTATION: {trigger_reason}")
    print(f"Old Password: {old_pw}")
    print(f"New Password: {new_pw} (SHA-256: {new_hash})")
    
    # 1. Update static/review.html client-side hash
    if os.path.exists(REVIEW_HTML):
        with open(REVIEW_HTML, "r", encoding="utf-8") as f:
            content = f.read()
        old_hash_line = f'const HASH="{state["current_hash"]}";'
        new_hash_line = f'const HASH="{new_hash}";'
        if old_hash_line in content:
            content = content.replace(old_hash_line, new_hash_line)
            with open(REVIEW_HTML, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated hash in {REVIEW_HTML}")
        else:
            print(f"Warning: Could not find exact line {old_hash_line} in {REVIEW_HTML}")

    # 2. Update state file
    state["current_password"] = new_pw
    state["current_hash"] = new_hash
    state["is_rotated"] = True
    state["rotation_history"].append({
        "timestamp": now_str,
        "reason": trigger_reason,
        "previous_password": old_pw,
        "new_password": new_pw
    })
    save_state(state)
    
    # 3. Commit and deploy to Vercel
    try:
        print("Staging and committing password rotation to Git...")
        subprocess.run(["git", "add", "static/review.html", "review_security_state.json"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"security: rotate Review Board password ({trigger_reason})"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=True)
        print("Git push completed. Deploying to Vercel production...")
        subprocess.run(["npx", "vercel", "--prod", "--yes"], cwd=BASE_DIR, check=True)
        print("Vercel production deployment completed!")
    except Exception as e:
        print(f"Error during git/vercel deployment: {e}")

    # 4. Send email alert to owner
    email_subject = f"[ARD Security Alert] Review Board Password Rotated ({trigger_reason})"
    email_body = f"""Dear Dr. Sarkar,

The ARD Promotion & Transfer Review Board (337) password has been automatically rotated according to your security protocol.

Trigger Details:
- Reason: {trigger_reason}
- Timestamp: {now_str}
- Previous Password: {old_pw} (NOW INVALID)
- Revised Active Password: {new_pw}

Access URL:
https://ard-posting-board.vercel.app/review

Please share this revised password only with authorized reviewing officers.

---
West Bengal Animal Resources Development Department
Automated Security & Access Governance Daemon
"""
    send_email_alert(RECIPIENT_EMAIL, email_subject, email_body)
    return new_pw

def main():
    state = load_state()
    cond = check_conditions(state)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        print(json.dumps(cond, indent=2))
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--force-rotate":
        reason = sys.argv[2] if len(sys.argv) > 2 else "Manual administrative rotation"
        rotate_password(reason)
        return

    print("=== ARD Review Board Security Audit Check ===")
    print(f"Current Time:          {cond['now']}")
    print(f"48-Hour Deadline:      {cond['deadline']} ({cond['seconds_remaining'] // 3600}h {(cond['seconds_remaining'] % 3600) // 60}m remaining)")
    print(f"Concurrent Active IPs:  {cond['concurrent_ips']} / {cond['ip_threshold']} limit")
    print(f"Current Password:      {state.get('current_password', 'lehalwa')}")
    print(f"Policy:                {state.get('policy', 'static_persistent')}")
    print(f"Auto-Rotate:           {state.get('auto_rotate', False)}")
    
    if cond["should_rotate"]:
        reason = ""
        if cond["ip_threshold_breached"]:
            reason = f"High concurrency threshold breached ({cond['concurrent_ips']} active IPs >= {cond['ip_threshold']})"
        elif cond["time_expired"]:
            reason = "48-hour access window expired"
        rotate_password(reason)
    else:
        print("✓ Access thresholds within acceptable limits. No password rotation needed at this time.")

if __name__ == "__main__":
    main()
