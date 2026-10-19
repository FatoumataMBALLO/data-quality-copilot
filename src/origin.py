import duckdb
import yaml

with open("rules/rules.yaml", encoding="utf-8") as f:
    rules = yaml.safe_load(f)["rules"]

con = duckdb.connect("data/dq.duckdb")

# Même règles, appliquées sur les données brutes
raw_flags = {}
for r in rules:
    sql_raw = r["sql"].replace("injected_bank", "raw_bank")
    raw_flags[r["id"]] = {row[0] for row in con.execute(sql_raw).fetchall()}

run_id = con.execute("SELECT MAX(run_id) FROM dq_results").fetchone()[0]

con.execute("DROP TABLE IF EXISTS dq_origin")
con.execute("""
    CREATE TABLE dq_origin (
        run_id INTEGER, rule_id VARCHAR,
        structural_count BIGINT, injected_count BIGINT
    )
""")

print(f"{'ID':9} {'Structurelles':>14} {'Injectées':>10}")
for r in rules:
    inj_ids = {row[0] for row in con.execute(r["sql"]).fetchall()}
    structural = len(inj_ids & raw_flags[r["id"]])
    injected = len(inj_ids) - structural
    con.execute("INSERT INTO dq_origin VALUES (?, ?, ?, ?)",
                [run_id, r["id"], structural, injected])
    print(f"{r['id']:9} {structural:14} {injected:10}")

con.execute("COPY dq_origin TO 'powerbi/data/dq_origin.csv' (HEADER, DELIMITER ',')")
con.close()