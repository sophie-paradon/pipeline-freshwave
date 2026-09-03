"""
Analyse complémentaire de la table finale produite par pipeline.py.

Le pipeline compare des moyennes. Ce script mesure en plus la dispersion,
ce qui permet de dire si un écart de moyennes est interprétable ou s'il est
noyé dans la variabilité des ventes elles-mêmes.

Il ne modifie rien : il lit business_data.db et affiche des résultats.
Lancer après pipeline.py :  python analyse_complementaire.py
"""

import sqlite3
import pandas as pd
import numpy as np

DB_PATH = "business_data.db"
FINAL_TABLE_NAME = "final_consolidated_data"

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(f"SELECT * FROM {FINAL_TABLE_NAME}", conn)
stores = pd.read_sql_query("SELECT city, COUNT(*) AS nb_magasins FROM stores GROUP BY city", conn)
conn.close()


def dispersion(donnees, colonne_groupe):
    """Effectif, moyenne et écart-type du chiffre d'affaires, par groupe."""
    return (
        donnees
        .groupby(colonne_groupe, as_index=False, observed=False)
        .agg(
            effectif=("total_revenue", "size"),
            moyenne=("total_revenue", "mean"),
            ecart_type=("total_revenue", "std")
        )
        .round(2)
    )


# --- 1. Chiffre d'affaires par ville, rapporté au nombre de magasins ---
par_ville = (
    df.groupby("city", as_index=False)
    .agg(ca_total=("total_revenue", "sum"))
    .merge(stores, on="city")
)
par_ville["ca_par_magasin"] = (par_ville["ca_total"] / par_ville["nb_magasins"]).round(0)
par_ville = par_ville.sort_values("ca_total", ascending=False)

print("=== Chiffre d'affaires par ville ===")
print(par_ville.to_string(index=False))

# --- 2. Température, sur les glaces uniquement ---
print("\n=== Température, catégorie ice_cream ===")
print(dispersion(df[df["category"] == "ice_cream"], "temp_bucket").to_string(index=False))

# --- 3. Pluie ---
print("\n=== Tranches de pluie ===")
print(dispersion(df, "rain_bucket").to_string(index=False))

# --- 4. Campagnes marketing ---
print("\n=== Jours avec campagne contre jours sans ===")
df["avec_campagne"] = df["nb_campaigns"] > 0
print(dispersion(df, "avec_campagne").to_string(index=False))

# --- 5. Week-end, comparé à la bonne échelle ---
# Une ligne de la table est un produit dans un magasin un jour donné.
# Comparer des week-ends à des jours de semaine demande de totaliser
# d'abord par journée et par ville, sinon on compare des paniers, pas des journées.
journees = (
    df.groupby(["date", "city", "is_weekend"], as_index=False)
    .agg(ca_jour=("total_revenue", "sum"))
)

week_end = journees[journees["is_weekend"] == 1]["ca_jour"]
semaine = journees[journees["is_weekend"] == 0]["ca_jour"]

ecart = week_end.mean() - semaine.mean()
erreur_type = np.sqrt(week_end.var(ddof=1) / len(week_end) + semaine.var(ddof=1) / len(semaine))
borne_basse = ecart - 1.96 * erreur_type
borne_haute = ecart + 1.96 * erreur_type

print("\n=== Week-end contre semaine, par journée et par ville ===")
print(f"week-end : {week_end.mean():.2f} EUR sur {len(week_end)} journees")
print(f"semaine  : {semaine.mean():.2f} EUR sur {len(semaine)} journees")
print(f"ecart    : {ecart:+.2f} EUR, soit {100 * ecart / semaine.mean():+.1f} %")
print(f"IC 95 %  : [{borne_basse:.2f} ; {borne_haute:.2f}]")
if borne_basse < 0 < borne_haute:
    print("L'intervalle contient zero : l'ecart n'est pas significatif.")

# --- 6. Le même écart, ville par ville ---
print("\n=== Ecart week-end, ville par ville ===")
for ville, groupe in journees.groupby("city"):
    we = groupe[groupe["is_weekend"] == 1]["ca_jour"].mean()
    sem = groupe[groupe["is_weekend"] == 0]["ca_jour"].mean()
    print(f"{ville:<10} {100 * (we - sem) / sem:+5.1f} %")
