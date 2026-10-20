"""
ingest_and_clean.py
===================
Retail Orders & Global Mart Sales Analytics - Step 1 (Python)

What this script does
  1. INGEST   : downloads orders.csv from Kaggle with the Kaggle API (or uses the bundled zip)
  2. UNZIP    : extracts the raw file
  3. CLEAN    : standardises column names, fixes null-like ship modes, fixes dtypes
  4. ENGINEER : creates discount, sale_price, profit, revenue and date features
  5. VALIDATE : runs data-quality assertions
  6. LOAD     : writes the sanitised table to a relational database (SQLite by default,
                SQL Server / PostgreSQL / MySQL via a connection string)

Usage
  python ingest_and_clean.py --source local                 # use data/orders.csv.zip (bundled)
  python ingest_and_clean.py --source kaggle                # download the original Kaggle file
  python ingest_and_clean.py --source local --db "mssql+pyodbc://@localhost/GlobalMart?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

Kaggle credentials (only for --source kaggle)
  Put kaggle.json in ~/.kaggle/ (chmod 600)  OR  set KAGGLE_USERNAME and KAGGLE_KEY env vars.
"""
import argparse
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KAGGLE_DATASET = "ankitbansal06/retail-orders"
KAGGLE_FILE = "orders.csv"


# --------------------------------------------------------------------------- 1. INGEST
def ingest(source: str) -> Path:
    """Return the path of the downloaded zip (or the bundled zip)."""
    DATA.mkdir(exist_ok=True)
    zip_path = DATA / f"{KAGGLE_FILE}.zip"
    if source == "kaggle":
        try:
            # import here so the script still runs without the kaggle package in local mode
            import kaggle  # noqa: F401  (authenticates on import using kaggle.json / env vars)
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()
            api.dataset_download_file(KAGGLE_DATASET, KAGGLE_FILE, path=str(DATA))
            print(f"[ingest] downloaded {KAGGLE_DATASET}/{KAGGLE_FILE} -> {zip_path}")
        except Exception as exc:  # network / credentials problems
            sys.exit(f"[ingest] Kaggle download failed: {exc}\n"
                     f"         Fix credentials or re-run with --source local.")
    else:
        if not zip_path.exists():
            sys.exit(f"[ingest] {zip_path} not found. Run scripts/generate_raw_dataset.py first.")
        print(f"[ingest] using bundled file {zip_path}")
    return zip_path


# --------------------------------------------------------------------------- 2. UNZIP
def unzip(zip_path: Path) -> Path:
    # a plain CSV is returned untouched (newer kaggle versions sometimes save un-zipped)
    if not zipfile.is_zipfile(zip_path):
        return zip_path
    with zipfile.ZipFile(zip_path) as z:
        z.extract(KAGGLE_FILE, DATA)
    csv_path = DATA / KAGGLE_FILE
    print(f"[unzip] extracted -> {csv_path}")
    return csv_path


# --------------------------------------------------------------------------- 3. CLEAN
def clean(csv_path: Path) -> pd.DataFrame:
    # treat the dataset's two 'fake values' as missing at read time
    df = pd.read_csv(csv_path, na_values=["Not Available", "unknown", "N/A", ""])
    raw_rows = len(df)

    # 3a. standard column names: lower-case, underscores
    df.columns = (df.columns.str.strip().str.lower()
                  .str.replace(" ", "_", regex=False))

    # 3b. text columns: trim whitespace + consistent casing
    text_cols = ["ship_mode", "segment", "country", "city", "state", "region",
                 "category", "sub_category"]
    for c in text_cols:
        df[c] = df[c].astype("string").str.strip()
    df["product_id"] = df["product_id"].astype("string").str.strip().str.upper()

    # 3c. missing ship_mode -> explicit 'Unknown' bucket (keep the order, do not lose revenue)
    n_missing_ship = int(df["ship_mode"].isna().sum())
    df["ship_mode"] = df["ship_mode"].fillna("Unknown")

    # 3d. dtypes
    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="raise")
    df["postal_code"] = df["postal_code"].astype(str).str.zfill(5)      # keeps leading zeros (e.g. 02110)
    for c in ["cost_price", "list_price", "quantity", "discount_percent"]:
        df[c] = pd.to_numeric(df[c], errors="raise")

    # 3e. duplicates
    n_dupes = int(df.duplicated(subset=["order_id"]).sum())
    df = df.drop_duplicates(subset=["order_id"]).reset_index(drop=True)

    print(f"[clean] rows read={raw_rows:,} | ship_mode fixed={n_missing_ship:,} | duplicate order_id removed={n_dupes}")
    return df


# --------------------------------------------------------------------------- 4. FEATURE ENGINEERING
def engineer(df: pd.DataFrame) -> pd.DataFrame:
    """
    Unit-level money fields (per item)       Order-line fields (x quantity)
      discount     = list_price x disc% / 100   gross_revenue = list_price x quantity     (pre-discount)
      sale_price   = list_price - discount      net_revenue   = sale_price x quantity     (post-discount)
      profit       = sale_price - cost_price    total_profit  = profit x quantity
    """
    df["discount"] = (df["list_price"] * df["discount_percent"] / 100).round(2)
    df["sale_price"] = (df["list_price"] - df["discount"]).round(2)
    df["profit"] = (df["sale_price"] - df["cost_price"]).round(2)

    df["gross_revenue"] = (df["list_price"] * df["quantity"]).round(2)
    df["discount_amount"] = (df["discount"] * df["quantity"]).round(2)
    df["net_revenue"] = (df["sale_price"] * df["quantity"]).round(2)
    df["total_cost"] = (df["cost_price"] * df["quantity"]).round(2)
    df["total_profit"] = (df["profit"] * df["quantity"]).round(2)
    df["profit_margin_pct"] = np.where(df["net_revenue"] > 0,
                                       (df["total_profit"] / df["net_revenue"] * 100).round(2), 0.0)

    df["order_year"] = df["order_date"].dt.year
    df["order_month"] = df["order_date"].dt.month
    df["order_month_name"] = df["order_date"].dt.strftime("%b")
    df["order_year_month"] = df["order_date"].dt.strftime("%Y-%m")
    df["order_quarter"] = "Q" + df["order_date"].dt.quarter.astype(str)
    df["is_loss_making"] = (df["total_profit"] < 0).astype(int)
    df["discount_band"] = pd.cut(df["discount_percent"], bins=[-1, 3, 5, 10, 100],
                                 labels=["0-3%", "4-5%", "6-10%", ">10%"]).astype(str)
    return df


# --------------------------------------------------------------------------- 5. VALIDATE
def validate(df: pd.DataFrame) -> None:
    checks = {
        "order_id is unique":              df["order_id"].is_unique,
        "no nulls in key columns":         df[["order_id", "order_date", "ship_mode", "region", "category",
                                               "product_id", "list_price", "quantity"]].notna().all().all(),
        "quantity >= 1":                   (df["quantity"] >= 1).all(),
        "list_price > 0":                  (df["list_price"] > 0).all(),
        "0 <= discount_percent <= 100":    df["discount_percent"].between(0, 100).all(),
        "sale_price <= list_price":        (df["sale_price"] <= df["list_price"]).all(),
        "net_revenue <= gross_revenue":    (df["net_revenue"] <= df["gross_revenue"]).all(),
        "ship_mode has no fake values":    ~df["ship_mode"].isin(["Not Available", "unknown"]).any(),
        "date range is 2 full years":      df["order_date"].min().year != df["order_date"].max().year,
        "one category per sub_category":   (df.groupby("sub_category")["category"].nunique() == 1).all(),
    }
    failed = [k for k, ok in checks.items() if not ok]
    for k, ok in checks.items():
        print(f"[validate] {'PASS' if ok else 'FAIL'}  {k}")
    if failed:
        sys.exit(f"[validate] {len(failed)} check(s) failed -> stop before loading to the database.")


# --------------------------------------------------------------------------- 6. LOAD
def load_to_sql(df: pd.DataFrame, db_url: str, table: str = "df_orders") -> None:
    engine = create_engine(db_url)
    out = df.copy()
    out["order_date"] = out["order_date"].dt.date          # DATE column, not datetime
    # chunksize keeps SQL Server under its 2100-parameter limit
    out.to_sql(table, engine, index=False, if_exists="replace", chunksize=500)
    print(f"[load] {len(out):,} rows -> table '{table}' on {engine.url.render_as_string(hide_password=True)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["kaggle", "local"], default="local")
    ap.add_argument("--db", default=f"sqlite:///{(ROOT / 'data' / 'globalmart.db').as_posix()}",
                    help="SQLAlchemy URL (default: SQLite file data/globalmart.db)")
    args = ap.parse_args()

    csv_path = unzip(ingest(args.source))
    df = engineer(clean(csv_path))
    validate(df)

    cleaned = DATA / "orders_cleaned.csv"
    df.to_csv(cleaned, index=False)
    print(f"[export] cleaned file -> {cleaned}")
    load_to_sql(df, args.db)

    print("\n[summary]")
    print(f"  orders         : {len(df):,}")
    print(f"  date range     : {df['order_date'].min().date()} -> {df['order_date'].max().date()}")
    print(f"  gross revenue  : {df['gross_revenue'].sum():,.0f}")
    print(f"  net revenue    : {df['net_revenue'].sum():,.0f}")
    print(f"  total profit   : {df['total_profit'].sum():,.0f}")


if __name__ == "__main__":
    main()
