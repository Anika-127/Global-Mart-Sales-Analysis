"""Runs every Qnn block in sql/02_analysis_queries.sql against data/globalmart.db and prints/saves results."""
import re, sqlite3, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sql = (ROOT / "sql" / "02_analysis_queries.sql").read_text()
blocks = re.split(r"(?m)^-- (Q\d\d) \|", sql)
con = sqlite3.connect(ROOT / "data" / "globalmart.db")
out_dir = ROOT / "data" / "sql_results"; out_dir.mkdir(exist_ok=True)
pd.set_option("display.width", 220, "display.max_columns", 30)
for i in range(1, len(blocks), 2):
    qid, body = blocks[i], blocks[i + 1]
    title = body.split("\n")[0].strip(" -")
    stmt = "\n".join(body.split("\n")[1:]).strip().rstrip(";")
    df = pd.read_sql_query(stmt, con)
    df.to_csv(out_dir / f"{qid}.csv", index=False)
    print(f"\n=== {qid} | {title} ({len(df)} rows)")
    print(df.head(12).to_string(index=False))
