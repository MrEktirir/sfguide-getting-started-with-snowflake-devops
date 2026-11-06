
from snowflake.core import Root, CreateMode
from snowflake.snowpark import Session
from snowflake.core.user_defined_function import (
    Argument,
    ReturnDataType,
    PythonFunction,
    UserDefinedFunction,
)
from snowflake.core.view import View, ViewColumn


# ---------------------------------------------------------
# 1. Airport IATA -> City mapping
# ---------------------------------------------------------

map_city_to_airport = UserDefinedFunction(
    name="get_city_for_airport",
    arguments=[
        Argument(name="iata", datatype="VARCHAR")
    ],
    return_type=ReturnDataType(datatype="VARCHAR"),
    language_config=PythonFunction(
        runtime_version="3.11",
        packages=["snowflake-snowpark-python", "pandas"],
        handler="main",
    ),
    body="""
from snowflake.snowpark.files import SnowflakeFile
from _snowflake import vectorized
import pandas
import json

@vectorized(input=pandas.DataFrame)
def main(df):
    airport_list = json.loads(
        SnowflakeFile.open(
            "@QUICKSTART_COMMON.BRONZE.RAW/airport_list.json",
            "r",
            require_scoped_url=False
        ).read()
    )

    airports = {
        airport[3]: airport[1]
        for airport in airport_list
    }

    return df[0].apply(
        lambda iata: (
            airports.get(str(iata).upper())
            if pandas.notna(iata)
            else None
        )
    )
""",
)


# ---------------------------------------------------------
# 2. Data harmonization views
# ---------------------------------------------------------

pipeline = [

    # Flight CO2 emissions per passenger
    View(
        name="flight_emissions",
        columns=[
            ViewColumn(name="departure_airport"),
            ViewColumn(name="arrival_airport"),
            ViewColumn(name="co2_emissions_kg_per_person"),
        ],
        query="""
        SELECT
            departure_airport,
            arrival_airport,
            AVG(
                estimated_co2_total_tonnes / seats
            ) * 1000 AS co2_emissions_kg_per_person
        FROM
            OAG_FLIGHT_EMISSIONS_DATA_SAMPLE.PUBLIC.ESTIMATED_EMISSIONS_SCHEDULES_SAMPLE
        WHERE
            seats != 0
            AND estimated_co2_total_tonnes IS NOT NULL
        GROUP BY
            departure_airport,
            arrival_airport
        """,
    ),

    # Flight punctuality
    View(
        name="flight_punctuality",
        columns=[
            ViewColumn(name="departure_iata_airport_code"),
            ViewColumn(name="arrival_iata_airport_code"),
            ViewColumn(name="punctual_pct"),
        ],
        query="""
        SELECT
            departure_iata_airport_code,
            arrival_iata_airport_code,
            COUNT(
                CASE
                    WHEN arrival_actual_ingate_timeliness
                        IN ('OnTime', 'Early')
                    THEN 1
                END
            ) * 100.0 / NULLIF(COUNT(*), 0)
                AS punctual_pct
        FROM
            OAG_FLIGHT_STATUS_DATA_SAMPLE.PUBLIC.FLIGHT_STATUS_LATEST_SAMPLE
        WHERE
            arrival_actual_ingate_timeliness IS NOT NULL
        GROUP BY
            departure_iata_airport_code,
            arrival_iata_airport_code
        """,
    ),

    # Flights departing from home airport
    View(
        name="flights_from_home",
        columns=[
            ViewColumn(name="departure_airport"),
            ViewColumn(name="arrival_airport"),
            ViewColumn(name="arrival_city"),
            ViewColumn(name="co2_emissions_kg_per_person"),
            ViewColumn(name="punctual_pct"),
        ],
        query="""
        SELECT
            emissions.departure_airport,
            emissions.arrival_airport,
            QUICKSTART_PROD.SILVER.GET_CITY_FOR_AIRPORT(
                emissions.arrival_airport
            ) AS arrival_city,
            emissions.co2_emissions_kg_per_person,
            punctuality.punctual_pct
        FROM
            QUICKSTART_PROD.SILVER.FLIGHT_EMISSIONS emissions
        JOIN
            QUICKSTART_PROD.SILVER.FLIGHT_PUNCTUALITY punctuality
            ON emissions.departure_airport =
                punctuality.departure_iata_airport_code
            AND emissions.arrival_airport =
                punctuality.arrival_iata_airport_code
        WHERE
            emissions.departure_airport = (
                SELECT $1:airport::VARCHAR
                FROM
                    @QUICKSTART_COMMON.PUBLIC.QUICKSTART_REPO/branches/main/data/home.json
                    (
                        FILE_FORMAT =>
                            QUICKSTART_COMMON.BRONZE.JSON_FORMAT
                    )
            )
        """,
    ),

    # Weather forecast: city-level mapping
    View(
        name="weather_forecast",
        columns=[
            ViewColumn(name="geo_id"),
            ViewColumn(name="avg_temperature_air_f"),
            ViewColumn(name="total_precipitation_in"),
        ],
        query="""
        SELECT
            CASE LOWER(city_name)
                WHEN 'houston'
                    THEN 'geoId/4835000'
                WHEN 'los_angeles'
                    THEN 'geoId/0644000'
                WHEN 'new_york'
                    THEN 'geoId/3651000'
            END AS geo_id,
            AVG(
                avg_temperature_air_2m_f
            ) AS avg_temperature_air_f,
            SUM(
                tot_precipitation_in
            ) AS total_precipitation_in
        FROM
            GLOBAL_WEATHER_CLIMATE_DATA_BY_THE_WEATHER_NETWORK_FOR_BUSINESS
                .PWS_BI_SAMPLE.POINT_FORECAST_DAY
        WHERE
            country_code = 'US'
            AND LOWER(city_name) IN (
                'houston',
                'los_angeles',
                'new_york'
            )
        GROUP BY
            LOWER(city_name)
        """,
    ),

    # Major US cities (population > 100,000)
    View(
        name="major_us_cities",
        columns=[
            ViewColumn(name="geo_id"),
            ViewColumn(name="geo_name"),
            ViewColumn(name="total_population"),
        ],
        query="""
        SELECT
            geo.geo_id,
            geo.geo_name,
            MAX(ts.value) AS total_population
        FROM
            SNOWFLAKE_CURATED_DATA_FREE.PUBLIC_DATA_FREE.DATACOMMONS_TIMESERIES ts
        JOIN
            SNOWFLAKE_CURATED_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_INDEX geo
            ON ts.geo_id = geo.geo_id
        JOIN
            SNOWFLAKE_CURATED_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_RELATIONSHIPS geo_rel
            ON geo_rel.related_geo_id = geo.geo_id
        WHERE
            ts.variable = 'Count_Person_census.gov'
            AND ts.date >= '2020-01-01'
            AND geo.level = 'City'
            AND geo_rel.geo_id = 'country/USA'
            AND ts.value > 100000
        GROUP BY
            geo.geo_id,
            geo.geo_name
        """,
    ),

    # City -> ZIP relationships
    View(
        name="zip_codes_in_city",
        columns=[
            ViewColumn(name="city_geo_id"),
            ViewColumn(name="city_geo_name"),
            ViewColumn(name="zip_geo_id"),
            ViewColumn(name="zip_geo_name"),
        ],
        query="""
        SELECT
            city.geo_id AS city_geo_id,
            city.geo_name AS city_geo_name,
            city.related_geo_id AS zip_geo_id,
            city.related_geo_name AS zip_geo_name
        FROM
            SNOWFLAKE_CURATED_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_RELATIONSHIPS country
        JOIN
            SNOWFLAKE_CURATED_DATA_FREE.PUBLIC_DATA_FREE.GEOGRAPHY_RELATIONSHIPS city
            ON country.related_geo_id = city.geo_id
        WHERE
            country.geo_id = 'country/USA'
            AND city.level = 'City'
            AND city.related_level =
                'CensusZipCodeTabulationArea'
        """,
    ),

    # Weather joined with major cities via GEO_ID
    View(
        name="weather_joined_with_major_cities",
        columns=[
            ViewColumn(name="geo_id"),
            ViewColumn(name="geo_name"),
            ViewColumn(name="total_population"),
            ViewColumn(name="avg_temperature_air_f"),
            ViewColumn(name="total_precipitation_in"),
        ],
        query="""
        SELECT
            city.geo_id,
            city.geo_name,
            city.total_population,
            weather.avg_temperature_air_f,
            weather.total_precipitation_in
        FROM
            QUICKSTART_PROD.SILVER.MAJOR_US_CITIES city
        JOIN
            QUICKSTART_PROD.SILVER.WEATHER_FORECAST weather
            ON city.geo_id = weather.geo_id
        """,
    ),
]


# ---------------------------------------------------------
# 3. Snowflake Python API entry point
# ---------------------------------------------------------

session = Session.builder.getOrCreate()
root = Root(session)

import os

environment = os.environ["ENVIRONMENT"].upper()

if environment not in ("DEV", "PROD"):
    raise ValueError("environment must be DEV or PROD")

silver_schema = (
    root.databases[f"QUICKSTART_{environment}"]
        .schemas["SILVER"]
)

silver_schema.user_defined_functions.create(
    map_city_to_airport,
    mode=CreateMode.or_replace,
)

for view in pipeline:
    silver_schema.views.create(
        view,
        mode=CreateMode.or_replace,
    )

print("Snowflake harmonization objects created.")
