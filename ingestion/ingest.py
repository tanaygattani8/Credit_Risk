"""
Phase 1 — IEEE-CIS Fraud Detection: Ingestion Script
Loads raw transaction + identity CSVs into BigQuery
"""

import os
import argparse
import pandas as pd
from google.cloud import bigquery
from google.api_core.exceptions import Conflict
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_ID  = os.environ["GCP_PROJECT_ID"]
DATASET_ID  = "raw"
LOCATION    = "US"

TABLES = {
    "transactions": {
        "file": "train_transaction.csv",
        "table": "transactions",
        "description": "IEEE-CIS raw payment transactions (590k rows)"
    },
    "identity": {
        "file": "train_identity.csv",
        "table": "identity",
        "description": "IEEE-CIS identity metadata linked to transactions"
    }
}

# ── Schema overrides (BigQuery auto-detects most, but we force key types) ─────
TRANSACTION_SCHEMA = [
    bigquery.SchemaField("TransactionID",  "INTEGER"),
    bigquery.SchemaField("isFraud",        "INTEGER"),
    bigquery.SchemaField("TransactionDT",  "INTEGER"),   # seconds offset, not a real timestamp
    bigquery.SchemaField("TransactionAmt", "FLOAT"),
    bigquery.SchemaField("ProductCD",      "STRING"),
    bigquery.SchemaField("card1",          "INTEGER"),
    bigquery.SchemaField("card2",          "FLOAT"),
    bigquery.SchemaField("card3",          "FLOAT"),
    bigquery.SchemaField("card4",          "STRING"),
    bigquery.SchemaField("card5",          "FLOAT"),
    bigquery.SchemaField("card6",          "STRING"),
    bigquery.SchemaField("addr1",          "FLOAT"),
    bigquery.SchemaField("addr2",          "FLOAT"),
    bigquery.SchemaField("dist1",          "FLOAT"),
    bigquery.SchemaField("dist2",          "FLOAT"),
    bigquery.SchemaField("P_emaildomain",  "STRING"),
    bigquery.SchemaField("R_emaildomain",  "STRING"),
]

IDENTITY_SCHEMA = [
    bigquery.SchemaField("TransactionID",  "INTEGER"),
    bigquery.SchemaField("DeviceType",     "STRING"),
    bigquery.SchemaField("DeviceInfo",     "STRING"),
]


def create_dataset_if_not_exists(client: bigquery.Client) -> None:
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = LOCATION
    dataset_ref.description = "Raw ingestion layer — IEEE-CIS Fraud Detection"
    try:
        client.create_dataset(dataset_ref)
        print(f"  ✓ Dataset '{DATASET_ID}' created")
    except Conflict:
        print(f"  · Dataset '{DATASET_ID}' already exists — skipping")


def load_table(
    client: bigquery.Client,
    csv_path: str,
    table_name: str,
    schema: list,
    chunksize: int = 50_000  # Lowered from 100k to 50k for safer Windows RAM usage
) -> None:
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    print(f"\n  Loading {csv_path} → {table_ref}")

    # Build schema map to optimize column data types
    schema_map = {f.name: f.field_type for f in schema}
    first_chunk = True

    # Stream chunks straight to BigQuery without storing them in a list
    for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunksize)):
        print(f"    · Processing and uploading chunk {i+1}...          ", end="\r")
        
        # 1. Optimize data types for the current chunk only
        for col in chunk.columns:
            if col in schema_map:
                if schema_map[col] == "INTEGER":
                    chunk[col] = pd.to_numeric(chunk[col], errors="coerce").astype("Int64")
                elif schema_map[col] == "FLOAT":
                    chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
                elif schema_map[col] == "STRING":
                    chunk[col] = chunk[col].astype(str).replace("nan", None)
            
            # Downcast all other unmapped float columns to save an extra 50% RAM
            elif chunk[col].dtype == 'float64':
                chunk[col] = pd.to_numeric(chunk[col], downcast='float')

        # 2. Configure BigQuery to OVERWRITE on chunk 1, but APPEND on later chunks
        job_config = bigquery.LoadJobConfig(
            write_disposition=(
                bigquery.WriteDisposition.WRITE_TRUNCATE if first_chunk 
                else bigquery.WriteDisposition.WRITE_APPEND
            ),
            autodetect=True, 
        )

        # 3. Stream the chunk up to the cloud
        job = client.load_table_from_dataframe(chunk, table_ref, job_config=job_config)
        job.result()  # Wait for this chunk to upload before moving to the next
        
        first_chunk = False

    # Print confirmation using BigQuery's actual numbers
    table = client.get_table(table_ref)
    print(f"    ✓ Successfully loaded {table.num_rows:,} rows into {table_ref} (Streamed in chunks)")


def run_validation(client: bigquery.Client) -> None:
    """Basic post-load checks — row counts + fraud rate sanity"""
    print("\n── Validation ──────────────────────────────────────────────────")

    checks = [
        ("Row count — transactions",
         f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.transactions`",
         lambda r: r[0].cnt > 500_000, "> 500k rows"),

        ("Row count — identity",
         f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.identity`",
         lambda r: r[0].cnt > 100_000, "> 100k rows"),

        ("Fraud rate sanity",
         f"SELECT ROUND(AVG(isFraud)*100, 2) as fraud_pct FROM `{PROJECT_ID}.{DATASET_ID}.transactions`",
         lambda r: 2.0 < r[0].fraud_pct < 5.0, "fraud rate between 2–5%"),

        ("No duplicate TransactionIDs",
         f"""SELECT COUNT(*) = COUNT(DISTINCT TransactionID) as ok
             FROM `{PROJECT_ID}.{DATASET_ID}.transactions`""",
         lambda r: r[0].ok is True, "all IDs unique"),
    ]

    all_passed = True
    for name, sql, check_fn, expectation in checks:
        result = list(client.query(sql).result())
        passed = check_fn(result)
        status = "✓" if passed else "✗"
        if not passed:
            all_passed = False
        print(f"  {status} {name} — expected: {expectation}")

    if all_passed:
        print("\n  ✓ All checks passed. Raw layer is ready for DBT.")
    else:
        print("\n  ✗ Some checks failed — inspect the table before proceeding.")


def main(data_dir: str) -> None:
    print("── Phase 1: BigQuery Ingestion ─────────────────────────────────")
    print(f"   Project : {PROJECT_ID}")
    print(f"   Dataset : {DATASET_ID}")
    print(f"   Data dir: {data_dir}\n")

    client = bigquery.Client(project=PROJECT_ID)

    # 1. Create dataset
    print("── Step 1: Create dataset")
    create_dataset_if_not_exists(client)

    # 2. Load transactions
    print("\n── Step 2: Load transactions table")
    txn_path = os.path.join(data_dir, TABLES["transactions"]["file"])
    load_table(client, txn_path, "transactions", TRANSACTION_SCHEMA)

    # 3. Load identity
    print("\n── Step 3: Load identity table")
    id_path = os.path.join(data_dir, TABLES["identity"]["file"])
    load_table(client, id_path, "identity", IDENTITY_SCHEMA)

    # 4. Validate
    print("\n── Step 4: Validate")
    run_validation(client)

    print("\n── Done. Next step: run dbt init inside /dbt ────────────────────")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest IEEE-CIS data into BigQuery")
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="Path to folder containing train_transaction.csv and train_identity.csv"
    )
    args = parser.parse_args()
    main(args.data_dir)