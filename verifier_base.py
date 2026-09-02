import sqlite3
import pandas as pd

conn = sqlite3.connect("business_data.db")

tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type = 'table'", conn)
lignes = pd.read_sql_query(
    "SELECT COUNT(*) AS lignes FROM final_consolidated_data", conn
)
colonnes = pd.read_sql_query("PRAGMA table_info(final_consolidated_data)", conn)

conn.close()

print("Tables de la base :")
print(tables)
print("\nNombre de lignes :")
print(lignes)
print("\nColonnes de la table finale :")
print(colonnes[["name", "type"]])