import pandas as pd
import sqlite3
import requests

# --- Constantes du projet ---
START_DATE = "2024-05-01"
END_DATE = "2024-08-31"
DB_PATH = "business_data.db"
FINAL_TABLE_NAME = "final_consolidated_data"

CITY_COORDS = {
    "Paris": (48.8566, 2.3522),
    "Lyon": (45.7640, 4.8357),
    "Marseille": (43.2965, 5.3698),
    "Bordeaux": (44.8378, -0.5792),
    "Lille": (50.6292, 3.0573),
    "Nantes": (47.2184, -1.5536),
    "Toulouse": (43.6047, 1.4442),
    "Nice": (43.7102, 7.2620)
}


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open("stores.sql", "r", encoding="utf-8") as f:
        stores_sql = f.read()

    with open("products.sql", "r", encoding="utf-8") as f:
        products_sql = f.read()

    cursor.executescript(stores_sql)
    cursor.executescript(products_sql)

    conn.commit()
    conn.close()

    print("Base initialisée : tables stores et products créées")


def fetch_weather_for_city(city, lat, lon):
    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max"
        ],
        "timezone": "Europe/Paris"
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data["daily"])
    df["city"] = city

    df = df.rename(columns={
        "time": "date",
        "temperature_2m_max": "temperature_max",
        "temperature_2m_min": "temperature_min",
        "windspeed_10m_max": "windspeed_max"
    })

    df["date"] = pd.to_datetime(df["date"])

    return df


def extract():
    sales = pd.read_csv("sales.csv")
    marketing = pd.read_csv("marketing_campaigns.csv")

    sales["date"] = pd.to_datetime(sales["date"])
    marketing["date"] = pd.to_datetime(marketing["date"])

    conn = sqlite3.connect(DB_PATH)
    stores = pd.read_sql_query("SELECT * FROM stores", conn)
    products = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()

    stores["opening_date"] = pd.to_datetime(stores["opening_date"])

    weather_data = []

    for city, (lat, lon) in CITY_COORDS.items():
        df_city = fetch_weather_for_city(city, lat, lon)
        weather_data.append(df_city)
        print("Météo récupérée :", city)

    weather = pd.concat(weather_data, ignore_index=True)

    print("weather :", weather.shape)
    print("villes :", sorted(weather["city"].unique()))
    print("du", weather["date"].min(), "au", weather["date"].max())

    data = {
        "sales": sales,
        "marketing": marketing,
        "stores": stores,
        "products": products,
        "weather": weather
    }

    print("sales :", sales.shape)
    print("marketing :", marketing.shape)

    return data


def transform(data):
    sales = data["sales"]
    marketing = data["marketing"]
    stores = data["stores"]
    products = data["products"]
    weather = data["weather"]

    sales["date"] = pd.to_datetime(sales["date"])
    marketing["date"] = pd.to_datetime(marketing["date"])
    weather["date"] = pd.to_datetime(weather["date"])

    sales = sales[
        (sales["date"] >= START_DATE) & (sales["date"] <= END_DATE)
    ]
    marketing = marketing[
        (marketing["date"] >= START_DATE) & (marketing["date"] <= END_DATE)
    ]

    print("après filtrage, sales :", sales.shape, "marketing :", marketing.shape)

    sales_enriched = (
        sales
        .merge(stores, on="store_id", how="left")
        .merge(
            products[["product_id", "product_name", "category"]],
            on="product_id", how="left"
        )
    )

    print("sales_enriched :", sales_enriched.shape)

    marketing_daily = (
        marketing
        .groupby(["date", "city"], as_index=False)
        .agg(
            marketing_spend=("marketing_spend", "sum"),
            nb_campaigns=("campaign_id", "count")
        )
    )

    sales_weather = sales_enriched.merge(weather, on=["date", "city"], how="left")
    sales_full = sales_weather.merge(marketing_daily, on=["date", "city"], how="left")

    sales_full["marketing_spend"] = sales_full["marketing_spend"].fillna(0)
    sales_full["nb_campaigns"] = sales_full["nb_campaigns"].fillna(0)

    print("sales_full :", sales_full.shape)
    print("lignes sans météo :", sales_full["temperature_max"].isna().sum())

    sales_full["day_of_week"] = sales_full["date"].dt.day_name()
    sales_full["is_weekend"] = sales_full["day_of_week"].isin(["Saturday", "Sunday"])

    sales_full["temp_bucket"] = pd.cut(
        sales_full["temperature_max"],
        bins=[-100, 20, 25, 30, 100],
        labels=["<=20°C", "20-25°C", "25-30°C", ">30°C"]
    )

    sales_full["rain_bucket"] = pd.cut(
        sales_full["precipitation_sum"],
        bins=[-0.1, 0, 5, 20, 1000],
        labels=["0 mm", "0-5 mm", "5-20 mm", ">20 mm"]
    )

    print(sales_full["temp_bucket"].value_counts())
    print(sales_full["rain_bucket"].value_counts())
    print("ventes le week-end :", sales_full["is_weekend"].sum())

    final_df = (
        sales_full
        .groupby(
            [
                "date", "store_id", "store_name", "city", "region",
                "product_id", "product_name", "category",
                "is_weekend", "temp_bucket", "rain_bucket"
            ],
            as_index=False,
            observed=True
        )
        .agg(
            total_revenue=("revenue", "sum"),
            total_quantity=("quantity_sold", "sum"),
            nb_transactions=("sale_id", "count"),
            temperature_max=("temperature_max", "mean"),
            temperature_min=("temperature_min", "mean"),
            precipitation_sum=("precipitation_sum", "mean"),
            windspeed_max=("windspeed_max", "mean"),
            marketing_spend=("marketing_spend", "mean"),
            nb_campaigns=("nb_campaigns", "mean")
        )
    )

    print("final_df :", final_df.shape)

    analysis_temp = (
        final_df
        .groupby(["category", "temp_bucket"], as_index=False, observed=False)
        .agg(avg_revenue=("total_revenue", "mean"))
        .sort_values(["category", "temp_bucket"])
    )

    analysis_rain = (
        final_df
        .groupby(["category", "rain_bucket"], as_index=False, observed=False)
        .agg(avg_revenue=("total_revenue", "mean"))
        .sort_values(["category", "rain_bucket"])
    )

    analysis_marketing = (
        final_df
        .groupby(["city", "nb_campaigns"], as_index=False)
        .agg(
            avg_revenue=("total_revenue", "mean"),
            avg_marketing_spend=("marketing_spend", "mean")
        )
        .sort_values(["city", "nb_campaigns"])
    )

    analysis_city = (
        final_df
        .groupby("city", as_index=False)
        .agg(total_revenue=("total_revenue", "sum"))
        .sort_values("total_revenue", ascending=False)
    )

    analysis_weekend = (
        final_df
        .groupby("is_weekend", as_index=False)
        .agg(avg_revenue=("total_revenue", "mean"))
    )

    results = {
        "final_df": final_df,
        "analysis_temp": analysis_temp,
        "analysis_rain": analysis_rain,
        "analysis_marketing": analysis_marketing,
        "analysis_city": analysis_city,
        "analysis_weekend": analysis_weekend
    }

    return results


def load(data):
    final_df = data["final_df"]

    conn = sqlite3.connect(DB_PATH)
    final_df.to_sql(FINAL_TABLE_NAME, conn, if_exists="replace", index=False)

    check_df = pd.read_sql_query(f"SELECT * FROM {FINAL_TABLE_NAME} LIMIT 5", conn)
    columns_df = pd.read_sql_query(f"PRAGMA table_info({FINAL_TABLE_NAME})", conn)
    conn.close()

    print("Table SQLite créée :", FINAL_TABLE_NAME)
    print("Aperçu :")
    print(check_df)
    print("Colonnes :")
    print(columns_df[["name", "type"]])

    print("\n=== Ventes par température ===")
    print(data["analysis_temp"])
    print("\n=== Impact de la pluie ===")
    print(data["analysis_rain"])
    print("\n=== Impact des campagnes ===")
    print(data["analysis_marketing"])
    print("\n=== Performances par ville ===")
    print(data["analysis_city"])
    print("\n=== Week-end vs semaine ===")
    print(data["analysis_weekend"])


def main():
    init_database()
    data = extract()
    data = transform(data)
    load(data)


if __name__ == "__main__":
    main()