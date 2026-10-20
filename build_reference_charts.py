"""Builds reference images of the four dashboard visuals from the SQL results (for the docs)."""
from pathlib import Path
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "data" / "sql_results"
img = ROOT / "docs"; img.mkdir(exist_ok=True)
NAVY, TEAL, ORANGE, GREY, RED = "#1F3A5F", "#2A9D8F", "#E76F51", "#8D99AE", "#C0392B"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})

# 1 ship mode
s = pd.read_csv(R / "Q11.csv").sort_values("orders")
fig, ax = plt.subplots(figsize=(6, 3.4))
ax.barh(s["ship_mode"], s["orders"], color=[GREY if m == "Unknown" else NAVY for m in s["ship_mode"]])
for y, (o, p) in enumerate(zip(s["orders"], s["order_share_pct"])):
    ax.text(o + 60, y, f"{o:,}  ({p:.1f}%)", va="center", fontsize=8)
ax.set_xlim(0, s["orders"].max() * 1.3); ax.set_title("Orders by Ship Mode", loc="left", fontweight="bold", fontsize=11)
ax.set_xlabel("Orders"); fig.tight_layout(); fig.savefig(img / "viz1_ship_mode.png", dpi=170); plt.close(fig)

# 2 city ranking
c = pd.read_csv(R / "Q09.csv").head(10).sort_values("revenue")
fig, ax = plt.subplots(figsize=(6, 3.9))
ax.barh(c["city"], c["revenue"] / 1000, color=TEAL)
for y, v in enumerate(c["revenue"] / 1000):
    ax.text(v + 2, y, f"{v:,.0f}K", va="center", fontsize=8)
ax.set_xlim(0, (c["revenue"] / 1000).max() * 1.15)
ax.set_title("Top 10 Cities by Revenue (post-discount)", loc="left", fontweight="bold", fontsize=11)
ax.set_xlabel("Revenue (K)"); fig.tight_layout(); fig.savefig(img / "viz2_city_revenue.png", dpi=170); plt.close(fig)

# 3 category discount vs margin
k = pd.read_csv(R / "Q12.csv")
fig, ax = plt.subplots(figsize=(6, 3.6)); x = range(len(k)); w = 0.38
b1 = ax.bar([i - w / 2 for i in x], k["discount_rate_pct"], w, color=ORANGE, label="Discount rate %")
b2 = ax.bar([i + w / 2 for i in x], k["margin_pct"], w, color=NAVY, label="Profit margin %")
ax.bar_label(b1, fmt="%.1f", fontsize=8); ax.bar_label(b2, fmt="%.1f", fontsize=8)
ax.set_xticks(list(x)); ax.set_xticklabels(k["category"]); ax.legend(frameon=False, fontsize=8)
ax.set_title("Discount Rate vs Profit Margin by Category", loc="left", fontweight="bold", fontsize=11)
fig.tight_layout(); fig.savefig(img / "viz3_category_discount.png", dpi=170); plt.close(fig)

# 4 product profitability (top 10 by profit)
p = pd.read_csv(R / "Q06.csv").sort_values("profit")
fig, ax = plt.subplots(figsize=(6, 3.9))
ax.barh(p["product_id"], p["profit"] / 1000, color=NAVY)
for y, (v, m) in enumerate(zip(p["profit"] / 1000, p["margin_pct"])):
    ax.text(v + 0.3, y, f"{v:,.1f}K  | {m:.0f}% margin", va="center", fontsize=7.5)
ax.set_xlim(0, (p["profit"] / 1000).max() * 1.4)
ax.set_title("Top 10 Products by Profit", loc="left", fontweight="bold", fontsize=11)
ax.set_xlabel("Profit (K)"); fig.tight_layout(); fig.savefig(img / "viz4_product_profit.png", dpi=170); plt.close(fig)

# 5 discount effectiveness
d = pd.read_csv(R / "Q14.csv")
fig, ax = plt.subplots(figsize=(6, 3.6))
ax.plot(d["discount_percent"].astype(str) + "%", d["margin_pct"], marker="o", color=RED, label="Profit margin %")
ax.set_ylabel("Profit margin %", color=RED); ax.set_ylim(0, 35)
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.bar(d["discount_percent"].astype(str) + "%", d["avg_units_per_line"], alpha=.25, color=NAVY)
ax2.set_ylabel("Avg units per order line", color=NAVY); ax2.set_ylim(0, 4.5)
ax.set_title("Deeper Discount: Margin Falls, Units Do Not Rise", loc="left", fontweight="bold", fontsize=11)
fig.tight_layout(); fig.savefig(img / "viz5_discount_effectiveness.png", dpi=170); plt.close(fig)
print("ok")
