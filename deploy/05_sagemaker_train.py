"""05_sagemaker_train.py — Lance un SageMaker Training Job pour entraîner le modèle de direction.

Pipeline complet :
  1. Upload des CSV OHLCV (un par symbole) vers S3 (canal training)
  2. Lance un SKLearn Estimator SageMaker avec sm_entry_point.py
  3. Attend la fin du job et affiche les métriques
  4. Télécharge le modèle artifact (model.tar.gz) depuis S3
  5. Décompresse et copie vers data/models/ (local) et dashboard EC2

Prérequis :
  - Credentials AWS actifs (variables d'environnement ou ~/.aws/credentials)
  - pip install boto3 sagemaker yfinance
  - DASHBOARD_EC2  : IP de l'EC2 dashboard (ex: 98.81.248.77)
  - SSH_KEY_PATH   : chemin vers la clé PEM (ex: ~/Downloads/labsuser.pem)
  - BUCKET_NAME    : nom du bucket S3

Usage :
  python3 deploy/05_sagemaker_train.py
"""
from __future__ import annotations

import os
import subprocess
import tarfile
import tempfile
from pathlib import Path

import boto3
import yfinance as yf
import pandas as pd

# ─── À CONFIGURER ────────────────────────────────────────────────────────────
BUCKET_NAME    = "c196829a5042926l14945956t1w321273741-sandboxbucket-cu3wzhwzpjaq"
AWS_REGION     = "us-east-1"
ROLE_ARN       = "arn:aws:iam::321273741000:role/c196829a5042926l14945956t1w3-SageMakerExecutionRole-e2QV54JUcPYH"
DASHBOARD_EC2  = "3.88.114.74"
SSH_KEY_PATH   = "~/Downloads/labsuser.pem"
SYMBOLS        = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"]
JOB_PREFIX     = "market-direction"
SKLEARN_VERSION = "1.2-1"                   # version SKLearn du container SageMaker
PYTHON_VERSION  = "py3"
INSTANCE_TYPE   = "ml.m5.large"             # ← Sans GPU, suffisant pour SKLearn
# ─────────────────────────────────────────────────────────────────────────────

S3_DATA_PREFIX  = f"{JOB_PREFIX}/training-data"
S3_MODEL_PREFIX = f"{JOB_PREFIX}/model-artifacts"
LOCAL_MODEL_DIR = Path("data/models")


def download_ohlcv(symbols: list[str], period: str = "5y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Télécharge les données OHLCV via yfinance."""
    result = {}
    for sym in symbols:
        print(f"  Téléchargement {sym}...")
        df = yf.download(sym, period=period, interval=interval, auto_adjust=True, progress=False)
        if df.empty:
            print(f"  [warn] Pas de données pour {sym}")
            continue
        # Aplatir les colonnes MultiIndex si nécessaire
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        result[sym] = df
    return result


def upload_training_data(s3_client, data: dict[str, pd.DataFrame]) -> str:
    """Upload un CSV par symbole dans S3, retourne le s3_uri du dossier."""
    with tempfile.TemporaryDirectory() as tmpdir:
        for sym, df in data.items():
            csv_path = Path(tmpdir) / f"{sym}.csv"
            df.to_csv(csv_path)
            s3_key = f"{S3_DATA_PREFIX}/{sym}.csv"
            s3_client.upload_file(str(csv_path), BUCKET_NAME, s3_key)
            print(f"  Uploadé s3://{BUCKET_NAME}/{s3_key}")

    return f"s3://{BUCKET_NAME}/{S3_DATA_PREFIX}"


def launch_training_job(s3_training_uri: str) -> str:
    """Lance le training job SageMaker et retourne le nom du job."""
    try:
        import sagemaker
        from sagemaker.sklearn.estimator import SKLearn
    except ImportError:
        raise ImportError("Installe sagemaker : pip install sagemaker")

    sess = sagemaker.Session(boto_session=boto3.Session(region_name=AWS_REGION))

    estimator = SKLearn(
        entry_point="sm_entry_point.py",
        source_dir=str(Path(__file__).parent),   # deploy/
        role=ROLE_ARN,
        instance_type=INSTANCE_TYPE,
        instance_count=1,
        framework_version=SKLEARN_VERSION,
        py_version=PYTHON_VERSION,
        output_path=f"s3://{BUCKET_NAME}/{S3_MODEL_PREFIX}",
        sagemaker_session=sess,
        base_job_name=JOB_PREFIX,
        hyperparameters={
            "symbols":        " ".join(SYMBOLS),
            "horizon":        "1",
            "threshold-bps":  "5.0",
            "n-splits":       "5",
        },
        dependencies=[str(Path(__file__).parent / "requirements_sm.txt")],  # yfinance + joblib
        metric_definitions=[
            {"Name": "train:accuracy", "Regex": r"acc=(\S+)"},
            {"Name": "train:auc",      "Regex": r"auc=(\S+)"},
            {"Name": "train:f1",       "Regex": r"f1=(\S+)"},
        ],
    )

    print(f"\n[SageMaker] Lancement du training job...")
    estimator.fit(wait=True, logs="All")  # Pas de canal training : yfinance télécharge directement

    job_name = estimator.latest_training_job.name
    print(f"[SageMaker] Job terminé : {job_name}")
    return estimator.model_data  # s3://bucket/.../model.tar.gz


def download_model(s3_client, model_s3_uri: str) -> Path:
    """Télécharge et décompresse model.tar.gz depuis S3."""
    # model_s3_uri = s3://bucket/prefix/job-name/output/model.tar.gz
    parts     = model_s3_uri.replace("s3://", "").split("/", 1)
    bucket    = parts[0]
    key       = parts[1]
    tar_path  = Path(tempfile.mktemp(suffix=".tar.gz"))

    print(f"\n[Download] s3://{bucket}/{key} → {tar_path}")
    s3_client.download_file(bucket, key, str(tar_path))

    LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:gz") as tf:
        tf.extractall(LOCAL_MODEL_DIR)
    print(f"[Download] Modèle extrait dans {LOCAL_MODEL_DIR}/")
    tar_path.unlink(missing_ok=True)
    return LOCAL_MODEL_DIR


def deploy_to_dashboard_ec2(local_model_dir: Path) -> None:
    """Copie les artifacts ML vers l'EC2 dashboard via SCP."""
    key = os.path.expanduser(SSH_KEY_PATH)
    remote = f"ec2-user@{DASHBOARD_EC2}:~/PA/data/models/"

    files = list(local_model_dir.glob("*.joblib")) + \
            list(local_model_dir.glob("*.json")) + \
            list(local_model_dir.glob("*.csv"))

    if not files:
        print("[warn] Aucun fichier modèle trouvé à copier")
        return

    cmd = ["scp", "-i", key, "-o", "StrictHostKeyChecking=no"] + \
          [str(f) for f in files] + [remote]
    print(f"\n[SCP] Copie vers {DASHBOARD_EC2}...")
    subprocess.run(cmd, check=True)

    # Redémarre le dashboard pour charger le nouveau modèle
    ssh_cmd = [
        "ssh", "-i", key, "-o", "StrictHostKeyChecking=no",
        f"ec2-user@{DASHBOARD_EC2}",
        "sudo systemctl restart streamlit-dashboard",
    ]
    subprocess.run(ssh_cmd, check=True)
    print(f"[ok] Dashboard redémarré avec le nouveau modèle !")


def main():
    if BUCKET_NAME == "<TON_BUCKET_S3>":
        raise ValueError("Configure BUCKET_NAME dans ce script !")
    if ROLE_ARN == "<TON_SAGEMAKER_ROLE_ARN>":
        raise ValueError("Configure ROLE_ARN dans ce script !")

    s3 = boto3.client("s3", region_name=AWS_REGION)

    # 1. Lancer le training job SageMaker (yfinance télécharge les données directement)
    print("=== [1/3] Training Job SageMaker ===")
    model_s3_uri = launch_training_job(None)
    print(f"  Modèle artifact : {model_s3_uri}")

    # 2. Télécharger et décompresser le modèle localement
    print("\n=== [2/3] Téléchargement du modèle depuis S3 ===")
    local_model_dir = download_model(s3, model_s3_uri)

    # 3. Déployer sur l'EC2 dashboard du Big Data sandbox
    print("\n=== [3/3] Déploiement sur EC2 dashboard ===")
    deploy_to_dashboard_ec2(local_model_dir)

    print("\n✅ Pipeline SageMaker terminé !")
    print(f"   Dashboard : http://{DASHBOARD_EC2}:8501")


if __name__ == "__main__":
    main()
