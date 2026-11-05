
USE ROLE ACCOUNTADMIN;
USE WAREHOUSE QUICKSTART_WH;
USE SCHEMA QUICKSTART_PROD.GOLD;

-- =========================================================
-- 1. GOLD TARGET TABLE
-- =========================================================

CREATE TABLE IF NOT EXISTS QUICKSTART_PROD.GOLD.VACATION_SPOTS (
    CITY VARCHAR,
    AIRPORT VARCHAR,
    CO2_EMISSIONS_KG_PER_PERSON FLOAT,
    PUNCTUAL_PCT FLOAT,
    AVG_TEMPERATURE_AIR_F FLOAT,
    TOTAL_PRECIPITATION_IN FLOAT
)
DATA_RETENTION_TIME_IN_DAYS = 1;


-- =========================================================
-- 2. TASK: UPDATE GOLD TABLE
-- =========================================================

CREATE OR REPLACE TASK QUICKSTART_PROD.GOLD.VACATION_SPOTS_UPDATE
    WAREHOUSE = QUICKSTART_WH
    SCHEDULE = '1440 MINUTE'
AS
MERGE INTO QUICKSTART_PROD.GOLD.VACATION_SPOTS AS target
USING (
    SELECT
        flight.ARRIVAL_CITY,
        flight.ARRIVAL_AIRPORT,
        flight.CO2_EMISSIONS_KG_PER_PERSON,
        flight.PUNCTUAL_PCT,
        city.AVG_TEMPERATURE_AIR_F,
        city.TOTAL_PRECIPITATION_IN
    FROM QUICKSTART_PROD.SILVER.FLIGHTS_FROM_HOME AS flight
    JOIN QUICKSTART_PROD.SILVER.WEATHER_JOINED_WITH_MAJOR_CITIES AS city
        ON city.GEO_NAME = flight.ARRIVAL_CITY
) AS source
ON target.CITY = source.ARRIVAL_CITY
   AND target.AIRPORT = source.ARRIVAL_AIRPORT

WHEN MATCHED THEN
    UPDATE SET
        target.CO2_EMISSIONS_KG_PER_PERSON =
            source.CO2_EMISSIONS_KG_PER_PERSON,
        target.PUNCTUAL_PCT =
            source.PUNCTUAL_PCT,
        target.AVG_TEMPERATURE_AIR_F =
            source.AVG_TEMPERATURE_AIR_F,
        target.TOTAL_PRECIPITATION_IN =
            source.TOTAL_PRECIPITATION_IN

WHEN NOT MATCHED THEN
    INSERT (
        CITY,
        AIRPORT,
        CO2_EMISSIONS_KG_PER_PERSON,
        PUNCTUAL_PCT,
        AVG_TEMPERATURE_AIR_F,
        TOTAL_PRECIPITATION_IN
    )
    VALUES (
        source.ARRIVAL_CITY,
        source.ARRIVAL_AIRPORT,
        source.CO2_EMISSIONS_KG_PER_PERSON,
        source.PUNCTUAL_PCT,
        source.AVG_TEMPERATURE_AIR_F,
        source.TOTAL_PRECIPITATION_IN
    );


-- =========================================================
-- 3. MANUALLY EXECUTE THE ROOT TASK
-- =========================================================

EXECUTE TASK QUICKSTART_PROD.GOLD.VACATION_SPOTS_UPDATE;
