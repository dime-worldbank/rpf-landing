import os
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config, oauth_service_principal


SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")

def credentials_provider():
    print("Initializing credential provider...")
    config = Config(
        host = f"https://{SERVER_HOSTNAME}",
        client_id     = os.getenv("DATABRICKS_CLIENT_ID"),
        client_secret = os.getenv("DATABRICKS_CLIENT_SECRET"))
    return oauth_service_principal(config)


def execute_query(query):
    """
    Fetches data from the Databricks database and returns it as a pandas dataframe

    Returns
    -------
    df : pandas dataframe
        basic query of data from Databricks as a pandas dataframe
    """
    with sql.connect(
        server_hostname = SERVER_HOSTNAME,
        http_path = os.getenv("DATABRICKS_HTTP_PATH"),
        credentials_provider=credentials_provider,
    ) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        df = cursor.fetchall_arrow().to_pandas()

    return df


def get_available_data():
    return execute_query("SELECT * FROM prd_mega.boost.data_availability")


def get_gdp():
    return execute_query("SELECT * FROM prd_mega.indicator.gdp")

def get_country():
    return execute_query("SELECT * FROM prd_mega.indicator.country")


def get_health_data(gdp, country):
    health_indicator = execute_query("SELECT * FROM prd_mega.indicator.universal_health_coverage_index_gho")
    merged = pd.merge(gdp, health_indicator, on=['country_code', 'year'], how='inner')
    merged = merged[merged.gdp_per_capita_2017_ppp.notnull() & merged.universal_health_coverage_index.notnull()]
    df = pd.merge(merged, country, on=['country_code'], how='inner')
    df = df[df.income_level != 'INX']
    df['universal_health_coverage_index'] = df['universal_health_coverage_index']/100
    df['gdp_per_capita_2017_ppp'] = df['gdp_per_capita_2017_ppp'].astype(int)
    return df


def get_edu_data(gdp, country):
    edu_indicator = execute_query("SELECT * FROM prd_mega.indicator.learning_poverty_rate")
    merged = pd.merge(gdp, edu_indicator, on=['country_code', 'year'], how='inner')
    merged = merged[merged.gdp_per_capita_2017_ppp.notnull() & merged.learning_poverty_rate.notnull()]
    df = pd.merge(merged, country, on=['country_code'], how='inner')
    df = df[df.income_level != 'INX']

    # drop unncessary precision
    df['learning_poverty_rate'] = df['learning_poverty_rate'].round(2)
    df['gdp_per_capita_2017_ppp'] = df['gdp_per_capita_2017_ppp'].astype(int)

    # some years have very few countries' data available, drop them
    country_counts = df.groupby('year')['country_code'].nunique()
    comparable_years = country_counts[country_counts >= 45].index
    df_filtered = df[df['year'].isin(comparable_years)]


    return df_filtered

