-- mart/mart_fraud_summary.sql
-- Aggregated summary table for Looker Studio dashboard
-- Shows fraud trends by day, product, card type, device, email domain

WITH features AS (
    SELECT * FROM {{ ref('mart_fraud_features') }}
),

daily AS (
    SELECT
        DATE(transaction_timestamp)         AS txn_date,
        product_cd,
        card4_type,
        card6_category,
        device_type,
        is_mobile,
        is_night_transaction,
        is_weekend,
        is_free_email,

        -- Volume
        COUNT(*)                            AS total_transactions,
        SUM(is_fraud)                       AS total_fraud,
        ROUND(AVG(is_fraud) * 100, 4)       AS fraud_rate_pct,

        -- Amounts
        ROUND(SUM(transaction_amt), 2)          AS total_amt,
        ROUND(AVG(transaction_amt), 2)          AS avg_amt,
        ROUND(SUM(CASE WHEN is_fraud = 1
              THEN transaction_amt ELSE 0 END), 2) AS fraud_amt,

        -- Velocity averages
        ROUND(AVG(card_txn_count_1h), 2)    AS avg_velocity_1h,
        ROUND(AVG(card_txn_count_24h), 2)   AS avg_velocity_24h,
        ROUND(AVG(amt_deviation_from_avg), 2) AS avg_amt_deviation

    FROM features
    GROUP BY 1,2,3,4,5,6,7,8,9
)

SELECT * FROM daily
ORDER BY txn_date DESC