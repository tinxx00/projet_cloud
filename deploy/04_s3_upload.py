"""
04_s3_upload.py
Upload des fichiers CSV (backup + processed) vers un bucket S3 AWS.
Usage : python3 deploy/04_s3_upload.py
"""
import boto3
import os
from pathlib import Path
from datetime import datetime

# ---- VARIABLES À ADAPTER ----
BUCKET_NAME = "pa-market-data-005311908836"
AWS_REGION = "us-east-1"           # ← Adapte ta région
# -----------------------------

FILES_TO_UPLOAD = [
    "data/quotes_backup.csv",
    "data/processed_quotes.csv",
]

def upload_to_s3():
    s3 = boto3.client("s3", region_name=AWS_REGION)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    for local_path in FILES_TO_UPLOAD:
        path = Path(local_path)
        if not path.exists():
            print(f"⚠️  Fichier introuvable : {local_path}")
            continue

        # Chemin dans S3 : ex. data/2026-05-01/processed_quotes_20260501_120000.csv
        s3_key = f"data/{datetime.utcnow().strftime('%Y-%m-%d')}/{path.stem}_{timestamp}{path.suffix}"

        print(f"📤 Upload : {local_path} → s3://{BUCKET_NAME}/{s3_key}")
        s3.upload_file(str(path), BUCKET_NAME, s3_key)
        print(f"   ✅ OK")

    print("\n🎉 Tous les fichiers ont été uploadés sur S3 !")

if __name__ == "__main__":
    upload_to_s3()
