# Retail Orders & Global Mart Sales Analytics

End-to-end data analyst project: Kaggle API ingestion -> Pandas cleaning -> SQL database -> SQL analysis -> Power BI dashboard.

## IMPORTANT: about the dataset
`data/orders.csv` is a **synthetic, reproducible dataset** (seed 42) built to the same 16-column schema,
naming quirks and dirty `Ship Mode` values as the public Kaggle dataset `ankitbansal06/retail-orders`.
It is **not** the original Kaggle file, so numbers differ from the original. To use the real file:

    pip install kaggle          # then place kaggle.json in ~/.kaggle/
    python scripts/ingest_and_clean.py --source kaggle

## Quick start
    pip install pandas numpy sqlalchemy kaggle pyodbc matplotlib
    python scripts/ingest_and_clean.py --source local   # clean + engineer + validate + load SQLite
    python scripts/run_sql_pack.py                      # run the 19 SQL queries -> data/sql_results/

## Contents
| Path | Purpose |
|---|---|
| data/orders.csv, orders.csv.zip | RAW dataset (9,994 rows) |
| data/orders_cleaned.csv | Cleaned + engineered dataset (32 columns) |
| data/globalmart.db | SQLite database (table df_orders) |
| scripts/ingest_and_clean.py | Ingest (Kaggle API), unzip, clean, engineer, validate, load |
| sql/01_create_table_sqlserver.sql | SQL Server DDL (optional) |
| sql/02_analysis_queries.sql | 19 portable analysis queries |
| powerbi/ | Power Query M, DAX measures, theme JSON |
| docs/01_Project_Requirements.docx | Business requirements document |
| docs/02_Solution_Guide.docx | Full step-by-step solution, results, recommendations |

## Testing status
Python pipeline and all 19 SQL queries were run end to end on SQLite. SQL is ANSI/portable for
SQL Server, PostgreSQL and MySQL 8 but was not executed on those engines. The Power BI .pbix must be
built in Power BI Desktop using the recipe and files in `powerbi/` and the Solution Guide.
