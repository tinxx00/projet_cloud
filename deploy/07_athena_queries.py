"""
07_athena_queries.py
Setup Athena + exécution de requêtes analytiques sur les données de marché stockées dans S3.

Architecture : S3 (CSV) → Athena (SQL) → Résultats

Usage : python3 deploy/07_athena_queries.py
"""
import boto3
import time
import json

REGION = "us-east-1"
DATABASE = "pa_market"
DATA_BUCKET = "pa-market-data-005311908836"
RESULTS_BUCKET = "pa-athena-results-005311908836"
RESULTS_LOCATION = f"s3://{RESULTS_BUCKET}/"

athena = boto3.client("athena", region_name=REGION)


def run_query(sql: str, description: str) -> list:
    print(f"\n📊 {description}")
    print(f"   SQL: {sql[:80]}...")

    response = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": RESULTS_LOCATION},
    )
    qid = response["QueryExecutionId"]

    # Attente du résultat
    for _ in range(20):
        status = athena.get_query_execution(QueryExecutionId=qid)
        state = status["QueryExecution"]["Status"]["State"]
        if state == "SUCCEEDED":
            break
        elif state in ("FAILED", "CANCELLED"):
            reason = status["QueryExecution"]["Status"].get("StateChangeReason", "")
            print(f"   ❌ Échec : {reason}")
            return []
        time.sleep(2)

    # Récupération des résultats
    results = athena.get_query_results(QueryExecutionId=qid)
    rows = results["ResultSet"]["Rows"]
    headers = [c.get("VarCharValue", "") for c in rows[0]["Data"]]
    data = [
        {headers[i]: c.get("VarCharValue", "") for i, c in enumerate(row["Data"])}
        for row in rows[1:]
    ]
    return data


def print_table(data: list):
    if not data:
        return
    headers = list(data[0].keys())
    widths = {h: max(len(h), max(len(str(row.get(h, ""))) for row in data)) for h in headers}
    header_line = " | ".join(h.ljust(widths[h]) for h in headers)
    print("   " + header_line)
    print("   " + "-" * len(header_line))
    for row in data:
        print("   " + " | ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers))


def main():
    print("=" * 60)
    print("  ATHENA — Analyse des données de marché (S3 Data Lake)")
    print("=" * 60)
    print(f"  Source : s3://{DATA_BUCKET}/athena/quotes/")
    print(f"  Base   : {DATABASE}.quotes")

    queries = [
        (
            "Stats par symbole : prix moyen, variation, signaux UP/DOWN",
            """SELECT symbol,
                      ROUND(AVG(price_current), 2)  AS avg_price,
                      ROUND(AVG(delta_pct), 4)       AS avg_delta_pct,
                      SUM(CASE WHEN direction='up'   THEN 1 ELSE 0 END) AS signals_up,
                      SUM(CASE WHEN direction='down' THEN 1 ELSE 0 END) AS signals_down,
                      COUNT(*) AS total
               FROM pa_market.quotes
               GROUP BY symbol
               ORDER BY avg_delta_pct DESC""",
        ),
        (
            "Top 5 hausses les plus fortes (delta_pct)",
            """SELECT symbol, price_current, ROUND(delta_pct, 4) AS delta_pct,
                      direction, ingested_at
               FROM pa_market.quotes
               WHERE direction = 'up'
               ORDER BY delta_pct DESC
               LIMIT 5""",
        ),
        (
            "Top 5 baisses les plus fortes",
            """SELECT symbol, price_current, ROUND(delta_pct, 4) AS delta_pct,
                      direction, ingested_at
               FROM pa_market.quotes
               WHERE direction = 'down'
               ORDER BY delta_pct ASC
               LIMIT 5""",
        ),
        (
            "Nombre de quotes par source (kafka vs csv_fallback)",
            """SELECT ingestion_mode, COUNT(*) AS total
               FROM pa_market.quotes
               GROUP BY ingestion_mode""",
        ),
    ]

    all_results = {}
    for description, sql in queries:
        data = run_query(sql, description)
        print_table(data)
        all_results[description] = data

    # Export JSON
    with open("data/athena_results.json", "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Résultats exportés dans data/athena_results.json")
    print(f"✅ Résultats bruts dans s3://{RESULTS_BUCKET}/")
    print("\n🎉 Analyse Athena terminée !")


if __name__ == "__main__":
    main()
