import os
import json
import csv
from pathlib import Path

def validate_dataset(resources_dir: str):
    print(f"Validating dataset in: {resources_dir}\n" + "-"*40)
    
    resources_path = Path(resources_dir)
    if not resources_path.exists():
        print(f"[FAIL] Error: Resources directory '{resources_dir}' not found.")
        return False
        
    all_valid = True

    # 1. Validate store_layout.json
    layout_path = resources_path / "store_layout.json"
    if layout_path.exists():
        try:
            with open(layout_path, "r") as f:
                layout = json.load(f)
                if "STORE_BLR_002" not in layout:
                    print("[FAIL] store_layout.json: Missing 'STORE_BLR_002' key.")
                    all_valid = False
                else:
                    print("[OK]   store_layout.json: Valid JSON with STORE_BLR_002.")
        except json.JSONDecodeError:
            print("[FAIL] store_layout.json: Invalid JSON format.")
            all_valid = False
    else:
        print("[FAIL] store_layout.json: File missing.")
        all_valid = False

    # 2. Validate pos_transactions.csv
    pos_path = resources_path / "pos_transactions.csv"
    if pos_path.exists():
        try:
            with open(pos_path, "r", encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                expected_headers = ["transaction_id", "timestamp", "store_id", "basket_value_inr"]
                if not all(h in headers for h in expected_headers):
                    print(f"[WARN] pos_transactions.csv: Missing expected headers. Found {headers}")
                else:
                    print("[OK]   pos_transactions.csv: Valid headers.")
        except Exception as e:
            print(f"[FAIL] pos_transactions.csv: Error reading file - {e}")
            all_valid = False
    else:
        print("[FAIL] pos_transactions.csv: File missing.")
        all_valid = False

    # 3. Validate CCTV Footage directory presence
    footage_dir = None
    for item in resources_path.iterdir():
        if item.is_dir() and item.name.startswith("CCTV Footage"):
            footage_dir = item
            break
            
    if footage_dir:
        videos = list(footage_dir.rglob("*.mp4"))
        if len(videos) > 0:
            print(f"[OK]   CCTV Footage: Found {len(videos)} MP4 files.")
        else:
            print("[FAIL] CCTV Footage: No MP4 files found in the footage directory.")
            all_valid = False
    else:
        print("[FAIL] CCTV Footage: Directory missing.")
        all_valid = False

    print("-" * 40)
    if all_valid:
        print("[SUCCESS] Dataset Validation Passed! All required files are present and formatted correctly.")
    else:
        print("[WARNING] Dataset Validation Failed. Please check the errors above.")

if __name__ == "__main__":
    # Ensure it checks the correct path relative to the script
    base_dir = Path(__file__).parent.parent / "Resources"
    validate_dataset(str(base_dir))
