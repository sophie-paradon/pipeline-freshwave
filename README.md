# FreshWave : pipeline de données et API REST

Projet blanc du bloc de compétences **RNCP 37827BC01** (collecte, stockage et mise à disposition des données), formation Data Analyst DataBird.

FreshWave est une enseigne fictive de glaces et de boissons fraîches (12 magasins, 8 villes). Le projet consolide quatre sources (ventes, campagnes marketing, magasins et produits, météo Open-Meteo) dans une base SQLite, puis expose la table consolidée par une API Flask.

```
sales.csv                 ─┐
marketing_campaigns.csv   ─┤
stores.sql / products.sql ─┼──►  pipeline.py  ──►  business_data.db  ──►  api.py  ──►  ngrok
API Open-Meteo            ─┘
```

## Installer

Python 3.10 ou plus récent, puis depuis le dossier `project` :

```
pip install -r requirements.txt
```

## Exécuter le pipeline

```
python pipeline.py
```

Le script crée la base `business_data.db` (tables `stores` et `products` à partir des scripts SQL), lit les deux CSV, appelle l'API Open-Meteo pour les huit villes (période du 1er mai au 31 août 2024), joint et agrège les données, écrit la table `final_consolidated_data` (8 525 lignes, 20 colonnes) et affiche les cinq analyses demandées. Une connexion Internet est nécessaire pour la météo.

Contrôles :

```
python verifier_base.py            # tables, nombre de lignes, colonnes de la table finale
python analyse_complementaire.py   # effectifs, écarts-types, intervalle de confiance week-end
```

## Lancer l'API

```
python api.py
```

| Endpoint | Réponse |
|---|---|
| `GET /health` | `{"status": "ok"}` |
| `GET /sales` | les 100 premières lignes de la table finale, en JSON |
| `GET /sales-by-city` | le chiffre d'affaires total par ville, ordre décroissant |

Exposition publique pour une démonstration : `ngrok http 5000` dans un second terminal.

## Fichiers

| Fichier | Rôle |
|---|---|
| `pipeline.py` | `init_database()`, `extract()`, `transform()`, `load()`, `main()` |
| `api.py` | l'API Flask et ses trois endpoints |
| `verifier_env.py`, `test_meteo.py`, `verifier_base.py` | scripts de contrôle |
| `analyse_complementaire.py` | mesures de dispersion complémentaires |
| `stores.sql`, `products.sql`, `sales.csv`, `marketing_campaigns.csv` | les sources fournies |
| `business_data.db` | résultat du pipeline, non versionné |
