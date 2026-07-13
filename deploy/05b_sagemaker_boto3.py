"""05b_sagemaker_boto3.py — Lance le training SageMaker via boto3 pur (sans SDK sagemaker).

Avantage : pas besoin d'installer le package `sagemaker` (qui tire torch/mlflow/etc.)
On appelle l'API SageMaker directement avec boto3.

Pipeline :
  1. Upload du script sm_entry_point.py dans S3
  2. Crée le training job via boto3 create_training_job
  3. Attend la fin et affiche les métriques
  4. Télécharge et déploie le modèle sur l'EC2 dashboard

Usage :
  AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=xxx python3 deploy/05b_sagemaker_boto3.py
"""

import boto3
import json
import os
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────
BUCKET_NAME     = "pa-market-data-005311908836"
AWS_REGION      = "us-east-1"
ROLE_ARN        = "arn:aws:iam::005311908836:role/PA-SageMakerRole"
DASHBOARD_EC2   = "54.84.67.251"
SSH_KEY_PATH    = os.path.expanduser("~/Downloads/pa-key.pem")
SYMBOLS         = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
JOB_NAME        = f"market-direction-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
SKLEARN_IMAGE   = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.4-2-py312-cpu-py3"
INSTANCE_TYPE   = "ml.m5.large"
LOCAL_MODEL_DIR = Path("data/models")
# ─────────────────────────────────────────────────────────────────────────────


def upload_source_to_s3(s3_client) -> str:
    """Upload sm_entry_point.py et requirements_sm.txt dans S3 sous forme de tar.gz."""
    deploy_dir = Path(__file__).parent
    files = [
        deploy_dir / "sm_entry_point.py",
        deploy_dir / "requirements_sm.txt",
    ]

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tar_path = tmp.name

    with tarfile.open(tar_path, "w:gz") as tf:
        for f in files:
            if f.exists():
                # SageMaker cherche requirements.txt (pas requirements_sm.txt)
                arcname = "requirements.txt" if f.name == "requirements_sm.txt" else f.name
                tf.add(str(f), arcname=arcname)
                print(f"  Ajouté au tar: {f.name} → {arcname}")

    s3_key = f"market-direction/source/sourcedir.tar.gz"
    s3_client.upload_file(tar_path, BUCKET_NAME, s3_key)
    os.unlink(tar_path)
    print(f"  Source uploadée: s3://{BUCKET_NAME}/{s3_key}")
    return f"s3://{BUCKET_NAME}/{s3_key}"


def launch_training_job(sm_client, source_s3_uri: str) -> str:
    """Lance le training job SageMaker et retourne le nom du job."""

    response = sm_client.create_training_job(
        TrainingJobName=JOB_NAME,
        AlgorithmSpecification={
            "TrainingImage": SKLEARN_IMAGE,
            "TrainingInputMode": "File",
            "MetricDefinitions": [
                {"Name": "train:accuracy", "Regex": r"acc=(\S+)"},
                {"Name": "train:auc",      "Regex": r"auc=(\S+)"},
                {"Name": "train:f1",       "Regex": r"f1=(\S+)"},
            ],
        },
        RoleArn=ROLE_ARN,
        InputDataConfig=[
            {
                "ChannelName": "training",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": f"s3://{BUCKET_NAME}/market-direction/training-data/",
                        "S3DataDistributionType": "FullyReplicated",
                    }
                },
                "InputMode": "File",
            }
        ],
        OutputDataConfig={
            "S3OutputPath": f"s3://{BUCKET_NAME}/market-direction/model-artifacts/",
        },
        ResourceConfig={
            "InstanceType": INSTANCE_TYPE,
            "InstanceCount": 1,
            "VolumeSizeInGB": 10,
        },
        StoppingCondition={"MaxRuntimeInSeconds": 3600},
        HyperParameters={
            "sagemaker_program": "sm_entry_point.py",
            "sagemaker_submit_directory": source_s3_uri,
            "sagemaker_requirements": "requirements_sm.txt",
            "symbols": " ".join(SYMBOLS),
            "horizon": "1",
            "threshold-bps": "5.0",
            "n-splits": "5",
        },
        EnableNetworkIsolation=False,
    )

    print(f"  Job créé: {JOB_NAME}")
    return JOB_NAME


def wait_for_job(sm_client, job_name: str) -> dict:
    """Attend la fin du job et retourne les détails."""
    print(f"\n  En attente du job {job_name}...")
    while True:
        resp = sm_client.describe_training_job(TrainingJobName=job_name)
        status = resp["TrainingJobStatus"]
        secondary = resp.get("SecondaryStatus", "")
        print(f"  Status: {status} / {secondary}", end="\r")

        if status in ("Completed", "Failed", "Stopped"):
            print()
            return resp

        time.sleep(30)


def download_model(s3_client, job_details: dict) -> Path:
    """Télécharge et décompresse model.tar.gz depuis S3."""
    model_uri = job_details["ModelArtifacts"]["S3ModelArtifacts"]
    parts  = model_uri.replace("s3://", "").split("/", 1)
    bucket = parts[0]
    key    = parts[1]

    tar_path = Path(tempfile.mktemp(suffix=".tar.gz"))
    print(f"\n  Téléchargement: s3://{bucket}/{key}")
    s3_client.download_file(bucket, key, str(tar_path))

    LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tf:
        tf.extractall(LOCAL_MODEL_DIR)
    tar_path.unlink(missing_ok=True)
    print(f"  Modèle extrait dans {LOCAL_MODEL_DIR}/")
    return LOCAL_MODEL_DIR


def deploy_to_dashboard(local_model_dir: Path) -> None:
    """Copie les artifacts ML vers l'EC2 dashboard via SCP."""
    files = (
        list(local_model_dir.glob("*.joblib")) +
        list(local_model_dir.glob("*.json")) +
        list(local_model_dir.glob("*.csv"))
    )
    if not files:
        print("  [warn] Aucun fichier modèle trouvé")
        return

    cmd = ["scp", "-i", SSH_KEY_PATH, "-o", "StrictHostKeyChecking=no"] + \
          [str(f) for f in files] + \
          [f"ec2-user@{DASHBOARD_EC2}:~/PA/data/models/"]
    print(f"\n  Copie SCP vers {DASHBOARD_EC2}...")
    subprocess.run(cmd, check=True)

    ssh_cmd = ["ssh", "-i", SSH_KEY_PATH, "-o", "StrictHostKeyChecking=no",
               f"ec2-user@{DASHBOARD_EC2}",
               "sudo systemctl restart streamlit-dashboard"]
    subprocess.run(ssh_cmd, check=True)
    print(f"  Dashboard redémarré avec le nouveau modèle ✅")


def main():
    session  = boto3.Session(region_name=AWS_REGION)
    s3       = session.client("s3")
    sm       = session.client("sagemaker")

    print("=== [1/4] Upload du code source vers S3 ===")
    source_uri = upload_source_to_s3(s3)

    print("\n=== [2/4] Lancement du Training Job SageMaker ===")
    job_name = launch_training_job(sm, source_uri)
    print(f"  Nom du job: {job_name}")
    print(f"  Console: https://console.aws.amazon.com/sagemaker/home?region={AWS_REGION}#/jobs/{job_name}")

    print("\n=== [3/4] Attente de la fin du job (5-15 min)... ===")
    details = wait_for_job(sm, job_name)

    if details["TrainingJobStatus"] != "Completed":
        print(f"\n❌ Job échoué: {details.get('FailureReason', 'inconnu')}")
        return

    print(f"\n✅ Job terminé avec succès!")
    model_uri = details["ModelArtifacts"]["S3ModelArtifacts"]
    print(f"   Modèle S3: {model_uri}")

    print("\n=== [4/4] Téléchargement et déploiement du modèle ===")
    local_dir = download_model(s3, details)
    deploy_to_dashboard(local_dir)

    print(f"\n🎉 Pipeline SageMaker complet!")
    print(f"   Dashboard: http://{DASHBOARD_EC2}:8501")


if __name__ == "__main__":
    main()
