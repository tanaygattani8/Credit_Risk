-- mart/mart_fraud_features.sql
-- Final model-ready feature table for the ML classifier (Phase 3)
-- One row per transaction, all features normalised and ready

WITH enriched AS (
    SELECT * FROM {{ ref('int_transactions_enriched') }}
)

SELECT
    -- ── Identity ────────────────────────────────────────────────────────
    transaction_id,
    is_fraud,                           -- target label

    -- ── Core transaction features ────────────────────────────────────────
    transaction_amt,
    product_cd,
    card4_type,                         -- visa / mastercard / amex etc
    card6_category,                     -- credit / debit
    billing_country_code,
    dist1,
    dist2,

    -- ── Email signals ────────────────────────────────────────────────────
    purchaser_email_domain,
    recipient_email_domain,
    CASE WHEN email_domains_match = TRUE  THEN 1
         WHEN email_domains_match = FALSE THEN 0
         ELSE -1 END                    AS email_domains_match,
    CASE WHEN is_free_email THEN 1 ELSE 0 END AS is_free_email,

    -- ── Time features ────────────────────────────────────────────────────
    txn_hour,
    txn_day_of_week,
    CASE WHEN is_night_transaction THEN 1 ELSE 0 END AS is_night_transaction,
    CASE WHEN is_weekend           THEN 1 ELSE 0 END AS is_weekend,

    -- ── Velocity features ────────────────────────────────────────────────
    card_txn_count_1h,
    card_txn_count_24h,
    ROUND(card_amt_sum_24h, 2)          AS card_amt_sum_24h,
    ROUND(card_avg_amt_30_txns, 2)      AS card_avg_amt_30_txns,
    ROUND(amt_deviation_from_avg, 2)    AS amt_deviation_from_avg,

    -- Amount-to-average ratio — strong fraud signal
    CASE
        WHEN card_avg_amt_30_txns > 0
        THEN ROUND(transaction_amt / card_avg_amt_30_txns, 4)
        ELSE NULL
    END                                 AS amt_to_avg_ratio,

    -- ── Device features ──────────────────────────────────────────────────
    device_type,
    CASE WHEN is_mobile THEN 1 ELSE 0 END AS is_mobile,
    os,
    browser,

    -- ── C-columns (transaction count aggregates from Vesta) ──────────────
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14,

    -- ── Identity numeric features ─────────────────────────────────────────
    id_01, id_02, id_05, id_06, id_11, id_13, id_17, id_19, id_20,

    -- ── Metadata ─────────────────────────────────────────────────────────
    transaction_timestamp

FROM enriched