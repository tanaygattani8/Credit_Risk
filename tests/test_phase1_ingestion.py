"""
Phase 1 tests — validates BigQuery tables after ingestion
Run with: pytest tests/test_phase1_ingestion.py -v
"""

import os
import pytest
from google.cloud import bigquery
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

PROJECT_ID = os.environ["GCP_PROJECT_ID"]
client = bigquery.Client(project=PROJECT_ID)


def bq(sql: str):
    return list(client.query(sql).result())


class TestTransactionsTable:

    def test_table_exists(self):
        result = bq(f"""
            SELECT COUNT(*) as cnt
            FROM `{PROJECT_ID}.raw.INFORMATION_SCHEMA.TABLES`
            WHERE table_name = 'transactions'
        """)
        assert result[0].cnt == 1, "transactions table does not exist"

    def test_row_count(self):
        result = bq(f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.raw.transactions`")
        assert result[0].cnt > 500_000, f"Expected >500k rows, got {result[0].cnt}"

    def test_no_duplicate_transaction_ids(self):
        result = bq(f"""
            SELECT COUNT(*) as dupes FROM (
                SELECT TransactionID, COUNT(*) as c
                FROM `{PROJECT_ID}.raw.transactions`
                GROUP BY TransactionID
                HAVING c > 1
            )
        """)
        assert result[0].dupes == 0, f"Found {result[0].dupes} duplicate TransactionIDs"

    def test_fraud_label_is_binary(self):
        result = bq(f"""
            SELECT COUNT(DISTINCT isFraud) as distinct_vals
            FROM `{PROJECT_ID}.raw.transactions`
            WHERE isFraud IS NOT NULL
        """)
        assert result[0].distinct_vals == 2, "isFraud should only contain 0 and 1"

    def test_fraud_rate_is_realistic(self):
        result = bq(f"""
            SELECT ROUND(AVG(isFraud) * 100, 2) as fraud_pct
            FROM `{PROJECT_ID}.raw.transactions`
        """)
        pct = result[0].fraud_pct
        assert 2.0 < pct < 6.0, f"Fraud rate {pct}% looks wrong — expected 2–6%"

    def test_transaction_amount_positive(self):
        result = bq(f"""
            SELECT COUNT(*) as neg_rows
            FROM `{PROJECT_ID}.raw.transactions`
            WHERE TransactionAmt <= 0
        """)
        assert result[0].neg_rows == 0, "Found transactions with zero or negative amounts"

    def test_required_columns_exist(self):
        required = ["TransactionID", "isFraud", "TransactionDT",
                    "TransactionAmt", "ProductCD", "card1", "card4",
                    "P_emaildomain", "R_emaildomain"]
        result = bq(f"""
            SELECT column_name
            FROM `{PROJECT_ID}.raw.INFORMATION_SCHEMA.COLUMNS`
            WHERE table_name = 'transactions'
        """)
        actual_cols = {r.column_name for r in result}
        for col in required:
            assert col in actual_cols, f"Missing expected column: {col}"


class TestIdentityTable:

    def test_table_exists(self):
        result = bq(f"""
            SELECT COUNT(*) as cnt
            FROM `{PROJECT_ID}.raw.INFORMATION_SCHEMA.TABLES`
            WHERE table_name = 'identity'
        """)
        assert result[0].cnt == 1, "identity table does not exist"

    def test_row_count(self):
        result = bq(f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.raw.identity`")
        assert result[0].cnt > 100_000, f"Expected >100k rows, got {result[0].cnt}"

    def test_all_identity_txns_exist_in_transactions(self):
        """Every identity record should have a matching transaction"""
        result = bq(f"""
            SELECT COUNT(*) as orphans
            FROM `{PROJECT_ID}.raw.identity` i
            LEFT JOIN `{PROJECT_ID}.raw.transactions` t
                ON i.TransactionID = t.TransactionID
            WHERE t.TransactionID IS NULL
        """)
        assert result[0].orphans == 0, \
            f"Found {result[0].orphans} identity rows with no matching transaction"

    def test_device_type_values(self):
        result = bq(f"""
            SELECT DISTINCT DeviceType
            FROM `{PROJECT_ID}.raw.identity`
            WHERE DeviceType IS NOT NULL
        """)
        values = {r.DeviceType for r in result}
        expected = {"desktop", "mobile"}
        assert values.issubset(expected), \
            f"Unexpected DeviceType values: {values - expected}"