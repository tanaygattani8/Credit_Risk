-- staging/stg_transactions.sql
-- Cleans and type-casts the raw transactions table

WITH source AS (
    SELECT * FROM {{ source('raw', 'transactions') }}
),

cleaned AS (
    SELECT
        -- Keys
        CAST(TransactionID AS INT64)                    AS transaction_id,

        -- Label
        CAST(isFraud AS INT64)                          AS is_fraud,

        -- Time (TransactionDT is seconds offset from a reference date)
        CAST(TransactionDT AS INT64)                    AS transaction_dt,
        TIMESTAMP_ADD(
            TIMESTAMP '2017-12-01 00:00:00',
            INTERVAL CAST(TransactionDT AS INT64) SECOND 
        )                                               AS transaction_timestamp,

        -- Amount
        ROUND(CAST(TransactionAmt AS FLOAT64), 2)       AS transaction_amt,

        -- Product
        UPPER(TRIM(ProductCD))                          AS product_cd,

        -- Card Info
        CAST(card1 AS INT64)                            AS card1,
        CAST(card2 AS FLOAT64)                          AS card2,
        CAST(card3 AS FLOAT64)                          AS card3,
        LOWER(TRIM(card4))                              AS card4_type,      -- visa, mastercard etc
        CAST(card5 AS FLOAT64)                          AS card5,
        LOWER(TRIM(card6))                              AS card6_category,  -- credit, debit etc

        -- Address
        CAST(addr1 AS FLOAT64)                          AS billing_zip,
        CAST(addr2 AS FLOAT64)                          AS billing_country_code,

        -- Distance
        CAST(dist1 AS FLOAT64)                          AS dist1,
        CAST(dist2 AS FLOAT64)                          AS dist2,

        -- Email domains
        LOWER(TRIM(P_emaildomain))                      AS purchaser_email_domain,
        LOWER(TRIM(R_emaildomain))                      AS recipient_email_domain,

        -- Email domain match flag (useful fraud signal)
        CASE
            WHEN LOWER(TRIM(P_emaildomain)) = LOWER(TRIM(R_emaildomain)) THEN TRUE
            WHEN P_emaildomain IS NULL OR R_emaildomain IS NULL THEN NULL
            ELSE FALSE
        END                                             AS email_domains_match,

        -- Count of C columns (transaction count features)
        CAST(C1  AS FLOAT64)                            AS c1,
        CAST(C2  AS FLOAT64)                            AS c2,
        CAST(C3  AS FLOAT64)                            AS c3,
        CAST(C4  AS FLOAT64)                            AS c4,
        CAST(C5  AS FLOAT64)                            AS c5,
        CAST(C6  AS FLOAT64)                            AS c6,
        CAST(C7  AS FLOAT64)                            AS c7,
        CAST(C8  AS FLOAT64)                            AS c8,
        CAST(C9  AS FLOAT64)                            AS c9,
        CAST(C10 AS FLOAT64)                            AS c10,
        CAST(C11 AS FLOAT64)                            AS c11,
        CAST(C12 AS FLOAT64)                            AS c12,
        CAST(C13 AS FLOAT64)                            AS c13,
        CAST(C14 AS FLOAT64)                            AS c14
    
    FROM source
    WHERE TransactionID IS NOT NULL
        AND TransactionAmt > 0 -- drop zero/negative amounts
)

SELECT * FROM cleaned