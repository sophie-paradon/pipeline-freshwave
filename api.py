from flask import Flask, jsonify
import pandas as pd
import sqlite3

DB_PATH = "business_data.db"
FINAL_TABLE_NAME = "final_consolidated_data"

app = Flask(__name__)


def run_query(query):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/sales", methods=["GET"])
def get_sales():
    query = f"""
    SELECT *
    FROM {FINAL_TABLE_NAME}
    LIMIT 100
    """
    df = run_query(query)
    return jsonify(df.to_dict(orient="records"))


@app.route("/sales-by-city", methods=["GET"])
def sales_by_city():
    query = f"""
    SELECT
        city,
        SUM(total_revenue) AS total_revenue
    FROM {FINAL_TABLE_NAME}
    GROUP BY city
    ORDER BY total_revenue DESC
    """
    df = run_query(query)
    return jsonify(df.to_dict(orient="records"))


if __name__ == "__main__":
    app.run(debug=True)