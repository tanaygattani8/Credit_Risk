-- staging/stg_identity.sql
-- Cleans and type-casts the raw identity table
 
WITH source AS (
    SELECT * FROM {{ source('raw', 'identity') }}
),
 
cleaned AS (
    SELECT
        -- Key
        CAST(TransactionID AS INT64)            AS transaction_id,
 
        -- Device
        LOWER(TRIM(DeviceType))                 AS device_type,     -- mobile / desktop
        TRIM(DeviceInfo)                        AS device_info,
 
        -- Identity columns id_01 to id_38
        CAST(id_01 AS FLOAT64)                  AS id_01,
        CAST(id_02 AS FLOAT64)                  AS id_02,
        CAST(id_03 AS FLOAT64)                  AS id_03,
        CAST(id_04 AS FLOAT64)                  AS id_04,
        CAST(id_05 AS FLOAT64)                  AS id_05,
        CAST(id_06 AS FLOAT64)                  AS id_06,
        CAST(id_09 AS FLOAT64)                  AS id_09,
        CAST(id_10 AS FLOAT64)                  AS id_10,
        CAST(id_11 AS FLOAT64)                  AS id_11,
        LOWER(TRIM(id_12))                      AS id_12,
        CAST(id_13 AS FLOAT64)                  AS id_13,
        CAST(id_14 AS FLOAT64)                  AS id_14,
        LOWER(TRIM(id_15))                      AS id_15,
        LOWER(TRIM(id_16))                      AS id_16,
        CAST(id_17 AS FLOAT64)                  AS id_17,
        CAST(id_18 AS FLOAT64)                  AS id_18,
        CAST(id_19 AS FLOAT64)                  AS id_19,
        CAST(id_20 AS FLOAT64)                  AS id_20,
        LOWER(TRIM(id_28))                      AS id_28,
        LOWER(TRIM(id_29))                      AS id_29,
        LOWER(TRIM(id_30))                      AS os,              -- operating system
        LOWER(TRIM(id_31))                      AS browser,         -- browser type
        CAST(id_32 AS FLOAT64)                  AS screen_resolution,
        LOWER(TRIM(id_33))                      AS screen_size,
        LOWER(TRIM(id_34))                      AS id_34,
        LOWER(TRIM(id_35))                      AS id_35,
        LOWER(TRIM(id_36))                      AS id_36,
        LOWER(TRIM(id_37))                      AS id_37,
        LOWER(TRIM(id_38))                      AS id_38
 
    FROM source
    WHERE TransactionID IS NOT NULL
)
 
SELECT * FROM cleaned