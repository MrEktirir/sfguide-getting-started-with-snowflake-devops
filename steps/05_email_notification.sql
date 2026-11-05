CREATE OR REPLACE TASK QUICKSTART_PROD.GOLD.EMAIL_NOTIFICATION
    WAREHOUSE = QUICKSTART_WH
    AFTER QUICKSTART_PROD.GOLD.VACATION_SPOTS_UPDATE
AS
EXECUTE IMMEDIATE $$
DECLARE
    email_body VARCHAR;
BEGIN
    SELECT
        'Snowflake DevOps - Vacation Recommendations' || CHR(10) || CHR(10) ||
        COALESCE(
            LISTAGG(
                'City: ' || CITY ||
                ' | Airport: ' || AIRPORT ||
                ' | Temperature: ' || ROUND(AVG_TEMPERATURE_AIR_F, 1) || ' F' ||
                ' | Punctuality: ' || ROUND(PUNCTUAL_PCT, 1) || '%',
                ' | '
            ) WITHIN GROUP (ORDER BY CITY),
            'No vacation destinations available.'
        )
    INTO :email_body
    FROM QUICKSTART_PROD.GOLD.VACATION_SPOTS;

    CALL SYSTEM$SEND_EMAIL(
        'EMAIL_INTEGRATION',
        'mehmet.ektirir@std.antalya.edu.tr',
        'Snowflake DevOps - Vacation Recommendations',
        :email_body
    );
END;
$$;
