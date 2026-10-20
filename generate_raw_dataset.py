"""
generate_raw_dataset.py
-----------------------
Builds a RAW 'Global Mart' retail orders file (data/orders.csv) that mirrors the schema,
column naming quirks and dirty values of the public Kaggle dataset
`ankitbansal06/retail-orders` (orders.csv, 9,994 rows, 16 columns).

NOTE: This is SYNTHETIC data (seeded, reproducible). It is NOT the original Kaggle file.
Use it when you cannot reach Kaggle; the cleaning / SQL / Power BI steps are identical
for the real file because the schema is the same.
"""
import numpy as np
import pandas as pd
import zipfile
from pathlib import Path

SEED = 42
N_ROWS = 9994
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- geography
# (city, state, region, postal_code, weight)
GEO = [
    # West
    ("Los Angeles", "California", "West", 90036, 9), ("San Francisco", "California", "West", 94122, 8),
    ("Seattle", "Washington", "West", 98103, 7), ("Portland", "Oregon", "West", 97206, 4),
    ("San Diego", "California", "West", 92037, 4), ("Denver", "Colorado", "West", 80219, 3),
    ("Phoenix", "Arizona", "West", 85023, 2), ("Las Vegas", "Nevada", "West", 89115, 2),
    ("Salt Lake City", "Utah", "West", 84106, 1.5), ("Sacramento", "California", "West", 95823, 1.5),
    ("Tucson", "Arizona", "West", 85705, 1), ("Fresno", "California", "West", 93727, 1),
    ("Spokane", "Washington", "West", 99207, 1), ("Boise", "Idaho", "West", 83704, 0.8),
    ("Albuquerque", "New Mexico", "West", 87105, 0.8),
    # East
    ("New York City", "New York", "East", 10009, 12), ("Philadelphia", "Pennsylvania", "East", 19140, 8),
    ("Boston", "Massachusetts", "East", 2110, 3), ("Pittsburgh", "Pennsylvania", "East", 15213, 2),
    ("Newark", "New Jersey", "East", 7104, 2), ("Buffalo", "New York", "East", 14215, 2),
    ("Baltimore", "Maryland", "East", 21215, 1.5), ("Providence", "Rhode Island", "East", 2908, 1.5),
    ("Hartford", "Connecticut", "East", 6106, 1), ("Rochester", "New York", "East", 14609, 1.5),
    ("Jersey City", "New Jersey", "East", 7305, 1.5), ("Washington", "District of Columbia", "East", 20024, 2),
    ("Wilmington", "Delaware", "East", 19801, 1), ("Burlington", "Vermont", "East", 5401, 0.7),
    ("Portsmouth", "New Hampshire", "East", 3801, 0.7),
    # Central
    ("Chicago", "Illinois", "Central", 60610, 7), ("Houston", "Texas", "Central", 77070, 7),
    ("Dallas", "Texas", "Central", 75217, 4), ("San Antonio", "Texas", "Central", 78207, 3),
    ("Austin", "Texas", "Central", 78745, 3), ("Detroit", "Michigan", "Central", 48234, 3),
    ("Minneapolis", "Minnesota", "Central", 55407, 2), ("Milwaukee", "Wisconsin", "Central", 53209, 2),
    ("Indianapolis", "Indiana", "Central", 46203, 2), ("Columbus", "Ohio", "Central", 43229, 2.5),
    ("Cleveland", "Ohio", "Central", 44105, 2), ("Kansas City", "Missouri", "Central", 64111, 1.5),
    ("St. Louis", "Missouri", "Central", 63116, 1.5), ("Omaha", "Nebraska", "Central", 68104, 1),
    ("Madison", "Wisconsin", "Central", 53711, 1), ("Oklahoma City", "Oklahoma", "Central", 73120, 1),
    ("Des Moines", "Iowa", "Central", 50315, 0.8),
    # South
    ("Miami", "Florida", "South", 33180, 3), ("Atlanta", "Georgia", "South", 30318, 3),
    ("Charlotte", "North Carolina", "South", 28205, 2), ("Jacksonville", "Florida", "South", 32216, 2.5),
    ("Nashville", "Tennessee", "South", 37211, 2), ("Memphis", "Tennessee", "South", 38109, 1.5),
    ("New Orleans", "Louisiana", "South", 70122, 1.5), ("Orlando", "Florida", "South", 32839, 2),
    ("Louisville", "Kentucky", "South", 40214, 1.5), ("Richmond", "Virginia", "South", 23223, 1.5),
    ("Raleigh", "North Carolina", "South", 27604, 1.5), ("Tampa", "Florida", "South", 33614, 1.5),
    ("Birmingham", "Alabama", "South", 35205, 1), ("Charleston", "South Carolina", "South", 29407, 1),
    ("Jackson", "Mississippi", "South", 39212, 0.8),
]
geo_df = pd.DataFrame(GEO, columns=["city", "state", "region", "postal", "w"])
geo_p = geo_df["w"] / geo_df["w"].sum()

# ---------------------------------------------------------------- catalogue
# sub_category: (category, code, price_low, price_high, n_products, popularity, base_cost_ratio)
SUBCATS = {
    "Bookcases":   ("Furniture", "FUR", "BO", 150, 900, 60, 1.0, 0.78),
    "Chairs":      ("Furniture", "FUR", "CH", 80, 700, 110, 1.6, 0.70),
    "Furnishings": ("Furniture", "FUR", "FU", 10, 120, 150, 2.2, 0.62),
    "Tables":      ("Furniture", "FUR", "TA", 200, 1200, 55, 0.8, 0.86),
    "Appliances":  ("Office Supplies", "OFF", "AP", 20, 600, 70, 1.0, 0.68),
    "Art":         ("Office Supplies", "OFF", "AR", 5, 60, 140, 2.4, 0.60),
    "Binders":     ("Office Supplies", "OFF", "BI", 3, 90, 200, 3.0, 0.72),
    "Envelopes":   ("Office Supplies", "OFF", "EN", 5, 60, 55, 1.2, 0.58),
    "Fasteners":   ("Office Supplies", "OFF", "FA", 3, 30, 45, 1.0, 0.60),
    "Labels":      ("Office Supplies", "OFF", "LA", 4, 40, 60, 1.3, 0.57),
    "Paper":       ("Office Supplies", "OFF", "PA", 5, 120, 190, 3.2, 0.62),
    "Storage":     ("Office Supplies", "OFF", "ST", 15, 300, 150, 2.2, 0.66),
    "Supplies":    ("Office Supplies", "OFF", "SU", 10, 250, 50, 0.9, 0.70),
    "Accessories": ("Technology", "TEC", "AC", 10, 250, 140, 2.2, 0.64),
    "Copiers":     ("Technology", "TEC", "CO", 400, 3000, 15, 0.45, 0.60),
    "Machines":    ("Technology", "TEC", "MA", 150, 1500, 40, 0.7, 0.82),
    "Phones":      ("Technology", "TEC", "PH", 50, 900, 120, 2.4, 0.67),
}

products = []
used_ids = set()
for sub, (cat, pre, code, lo, hi, n_prod, pop, cr) in SUBCATS.items():
    for _ in range(n_prod):
        while True:
            pid = f"{pre}-{code}-{rng.integers(10000000, 10004500)}"
            if pid not in used_ids:
                used_ids.add(pid)
                break
        # log-uniform list price so cheap items are common
        lp = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        lp = max(1, round(lp))
        cost = max(1, round(lp * float(np.clip(rng.normal(cr, 0.07), 0.45, 0.93))))
        products.append((pid, cat, sub, cost, lp, pop * float(rng.pareto(2.5) + 0.4)))
prod_df = pd.DataFrame(products, columns=["pid", "cat", "sub", "cost", "lp", "w"])
prod_p = prod_df["w"] / prod_df["w"].sum()

# ---------------------------------------------------------------- orders
n = N_ROWS
# order dates 2022-01-01 .. 2023-12-31 with seasonality + 2023 growth
days = pd.date_range("2022-01-01", "2023-12-31", freq="D")
season = {1: .55, 2: .55, 3: .85, 4: .8, 5: .85, 6: .9, 7: .85, 8: .9, 9: 1.35, 10: .95, 11: 1.45, 12: 1.5}
dw = np.array([season[d.month] * (1.0 if d.year == 2022 else 1.18) * (0.9 if d.dayofweek >= 5 else 1.0) for d in days])
dates = rng.choice(days, size=n, p=dw / dw.sum())
dates = pd.to_datetime(dates)

gi = rng.choice(len(geo_df), size=n, p=geo_p)
g = geo_df.iloc[gi].reset_index(drop=True)

pi_ = rng.choice(len(prod_df), size=n, p=prod_p)
p = prod_df.iloc[pi_].reset_index(drop=True)

segment = rng.choice(["Consumer", "Corporate", "Home Office"], size=n, p=[0.52, 0.30, 0.18])

# ship mode: Corporate leans to First/Same Day a little
ship = np.empty(n, dtype=object)
for i, seg in enumerate(segment):
    probs = [0.595, 0.195, 0.155, 0.055] if seg != "Corporate" else [0.55, 0.19, 0.19, 0.07]
    ship[i] = rng.choice(["Standard Class", "Second Class", "First Class", "Same Day"], p=probs)

quantity = rng.choice([1, 2, 3, 4, 5], size=n, p=[0.07, 0.27, 0.27, 0.22, 0.17])

# discount percent: mostly 2-5, heavier tail for some sub-categories and the Central region
disc_vals = np.array([2, 3, 4, 5, 10, 15, 20])
disc = np.empty(n, dtype=int)
heavy_sub = {"Tables": 3.0, "Bookcases": 2.2, "Binders": 2.0, "Machines": 1.6, "Appliances": 1.4, "Chairs": 1.2}
for i in range(n):
    tail = 0.050 * heavy_sub.get(p.loc[i, "sub"], 0.7) * (1.8 if g.loc[i, "region"] == "Central" else 1.0)
    tail = min(tail, 0.35)
    base = np.array([0.30, 0.28, 0.22, 0.15 - 0.0])
    base = base / base.sum() * (1 - tail)
    tails = np.array([0.60, 0.28, 0.12]) * tail
    disc[i] = rng.choice(disc_vals, p=np.concatenate([base, tails]))

df = pd.DataFrame({
    "Order Id": np.arange(1, n + 1),
    "Order Date": dates.strftime("%Y-%m-%d"),
    "Ship Mode": ship,
    "Segment": segment,
    "Country": "United States",
    "City": g["city"],
    "State": g["state"],
    "Postal Code": g["postal"],
    "Region": g["region"],
    "Category": p["cat"],
    "Sub Category": p["sub"],
    "Product Id": p["pid"],
    "cost price": p["cost"].astype(int),
    "List Price": p["lp"].astype(int),
    "Quantity": quantity,
    "Discount Percent": disc,
})

# order ids follow date order like a real order log
df = df.sort_values("Order Date", kind="stable").reset_index(drop=True)
df["Order Id"] = np.arange(1, n + 1)

# ---------------------------------------------------------------- inject DIRTY values (the cleaning step must fix these)
idx = rng.permutation(n)
df.loc[idx[:38], "Ship Mode"] = "Not Available"
df.loc[idx[38:70], "Ship Mode"] = "unknown"
df.loc[idx[70:96], "Ship Mode"] = np.nan

out = Path(__file__).resolve().parent.parent / "data"
out.mkdir(exist_ok=True)
df.to_csv(out / "orders.csv", index=False)
with zipfile.ZipFile(out / "orders.csv.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write(out / "orders.csv", "orders.csv")
print(df.shape)
print(df.head())
