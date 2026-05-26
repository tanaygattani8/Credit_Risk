-- intermediate/int_transactions_enriched.sql
-- Joins staging tables + engineers fraud-signal features

WITH transactions AS (
    SELECT * FROM {{ ref('stg_transactions') }}
),

identity AS (
    SELECT * FROM {{ ref('stg_identity') }}
),

joined AS (
    SELECT
        t.*,

        -- Identity fields
        COALESCE(i.device_type, 'unknown') AS device_type,
        i.device_info,
        i.os,
        i.browser,
        i.screen_resolution,
        i.id_01,
        i.id_02,
        i.id_05,
        i.id_06,
        i.id_11,
        i.id_13,
        i.id_17,
        i.id_19,
        i.id_20

    FROM transactions t
    LEFT JOIN identity i
        ON t.transaction_id = i.transaction_id
),

velocity_features AS (
    SELECT
        *,

        -- ── Time-based features ─────────────────────────────────────────
        EXTRACT(HOUR FROM transaction_timestamp)    AS txn_hour,
        EXTRACT(DAYOFWEEK FROM transaction_timestamp) AS txn_day_of_week,

        -- Night-time flag (midnight to 6am) — higher fraud signal
        CASE
            WHEN EXTRACT(HOUR FROM transaction_timestamp) BETWEEN 0 AND 5
            THEN TRUE ELSE FALSE
        END                                          AS is_night_transaction,

        -- Weekend flag
        CASE
            WHEN EXTRACT(DAYOFWEEK FROM transaction_timestamp) IN (1, 7)
            THEN TRUE ELSE FALSE
        END                                          AS is_weekend,

        -- ── Velocity features (rolling window over card1) ────────────────
        -- Number of transactions by same card in last 1 hour
        COUNT(*) OVER (
            PARTITION BY card1
            ORDER BY transaction_dt
            RANGE BETWEEN 3600 PRECEDING AND CURRENT ROW
        )                                            AS card_txn_count_1h,

        -- Number of transactions by same card in last 24 hours
        COUNT(*) OVER (
            PARTITION BY card1
            ORDER BY transaction_dt
            RANGE BETWEEN 86400 PRECEDING AND CURRENT ROW
        )                                            AS card_txn_count_24h,

        -- Total amount spent by same card in last 24 hours
        SUM(transaction_amt) OVER (
            PARTITION BY card1
            ORDER BY transaction_dt
            RANGE BETWEEN 86400 PRECEDING AND CURRENT ROW
        )                                            AS card_amt_sum_24h,

        -- Rolling average amount for this card (last 30 transactions)
        AVG(transaction_amt) OVER (
            PARTITION BY card1
            ORDER BY transaction_dt
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        )                                            AS card_avg_amt_30_txns,

        -- ── Amount deviation features ────────────────────────────────────
        -- How far this transaction is from the card's rolling average
        transaction_amt - AVG(transaction_amt) OVER (
            PARTITION BY card1
            ORDER BY transaction_dt
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        )                                            AS amt_deviation_from_avg,

        -- ── Email domain features ────────────────────────────────────────
        -- Flag transactions where purchaser email domain is free webmail
        CASE
            WHEN purchaser_email_domain IN (
                'gmail.com', 'yahoo.com', 'hotmail.com',
                'outlook.com', 'live.com', 'aol.com'
            ) THEN TRUE ELSE FALSE
        END                                          AS is_free_email,

        -- ── Device features ─────────────────────────────────────────────
        CASE WHEN device_type = 'mobile' THEN TRUE ELSE FALSE
        END                                          AS is_mobile

    FROM joined
)

SELECT * FROM velocity_features