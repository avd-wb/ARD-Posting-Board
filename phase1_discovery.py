import os
import sys
import hashlib
import json
import traceback
from datetime import datetime

SOURCE_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD"
DEST_DIR = "/Users/nirmalyaranjansarkar/Projects/AVD_AG"
MANIFEST_FILE = os.path.join(DEST_DIR, "file_manifest.json")

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def inspect_excel_xlsx(filepath):
    import openpyxl
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        sheets = wb.sheetnames
        wb.close()
        return {"sheet_names": sheets, "error": None}
    except Exception as e:
        return {"sheet_names": [], "error": str(e)}

def inspect_excel_xls(filepath):
    import xlrd
    try:
        wb = xlrd.open_workbook(filepath, on_demand=True)
        sheets = wb.sheet_names()
        return {"sheet_names": sheets, "error": None}
    except Exception as e:
        return {"sheet_names": [], "error": str(e)}

def inspect_csv(filepath):
    import csv
    encodings = ["utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc, errors="replace") as f:
                sample = f.read(8192)
                f.seek(0)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample) if sample.strip() else None
                reader = csv.reader(f, dialect=dialect) if dialect else csv.reader(f)
                row_count = sum(1 for _ in reader)
                return {
                    "encoding": enc,
                    "delimiter": dialect.delimiter if dialect else ",",
                    "row_count_estimate": row_count,
                    "error": None
                }
        except Exception as e:
            continue
    return {"encoding": None, "delimiter": None, "row_count_estimate": None, "error": "Failed to sniff/read CSV"}

def inspect_pdf(filepath):
    import pypdf
    try:
        reader = pypdf.PdfReader(filepath)
        page_count = len(reader.pages)
        return {"page_count": page_count, "error": None}
    except Exception as e:
        return {"page_count": None, "error": str(e)}

def scan():
    print(f"Scanning source directory: {SOURCE_DIR}")
    files_inventory = []
    hash_map = {}

    target_extensions = {".xlsx", ".xls", ".csv", ".pdf"}

    for root, dirs, files in os.walk(SOURCE_DIR):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in target_extensions:
                fpath = os.path.join(root, fname)
                rel_path = os.path.relpath(fpath, SOURCE_DIR)
                stat = os.stat(fpath)
                file_size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                
                is_temp_lock = fname.startswith("~$")
                
                file_info = {
                    "filename": fname,
                    "relative_path": rel_path,
                    "absolute_path": fpath,
                    "extension": ext,
                    "size_bytes": file_size,
                    "modified_time": mtime,
                    "is_temp_lock_file": is_temp_lock,
                    "sha256": None,
                    "metadata": {}
                }

                if not is_temp_lock:
                    try:
                        sha = compute_sha256(fpath)
                        file_info["sha256"] = sha
                        if sha not in hash_map:
                            hash_map[sha] = []
                        hash_map[sha].append(rel_path)
                    except Exception as e:
                        file_info["metadata"]["hash_error"] = str(e)

                    # Extract metadata based on extension
                    if ext == ".xlsx":
                        file_info["metadata"].update(inspect_excel_xlsx(fpath))
                    elif ext == ".xls":
                        file_info["metadata"].update(inspect_excel_xls(fpath))
                    elif ext == ".csv":
                        file_info["metadata"].update(inspect_csv(fpath))
                    elif ext == ".pdf":
                        file_info["metadata"].update(inspect_pdf(fpath))
                else:
                    file_info["metadata"]["note"] = "Excel temporary lock file"

                files_inventory.append(file_info)

    # Detect duplicates
    duplicates_summary = {sha: paths for sha, paths in hash_map.items() if len(paths) > 1}

    manifest = {
        "scan_time": datetime.now().isoformat(),
        "source_dir": SOURCE_DIR,
        "total_files_scanned": len(files_inventory),
        "total_unique_hashes": len(hash_map),
        "duplicate_groups_count": len(duplicates_summary),
        "duplicate_groups": duplicates_summary,
        "files": files_inventory
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Discovery complete.")
    print(f"Total target files found: {len(files_inventory)}")
    print(f"Unique SHA-256 hashes: {len(hash_map)}")
    print(f"Duplicate content groups: {len(duplicates_summary)}")
    print(f"Manifest written to: {MANIFEST_FILE}")

if __name__ == "__main__":
    scan()
