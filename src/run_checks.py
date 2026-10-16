import os
import duckdb
import yaml

DB = "data/dq.duckdb"
TABLE = "injected_bank"

with open("rules/rules.yaml", encoding="utf-8") as f:
    rules = yaml.safe_load(f)["rules"]

con = duckdb.connect(DB)

# Catalogue des règles : recréé à chaque exécution depuis le YAML
con.execute("DROP TABLE IF EXISTS dq_rules")
con.execute("""
    CREATE TABLE dq_rules (
        rule_id VARCHAR, rule_name VARCHAR, dimension VARCHAR,
        severity VARCHAR, threshold_pct DOUBLE,
        description VARCHAR, sql_query VARCHAR
    )
""")
con.executemany(
    "INSERT INTO dq_rules VALUES (?, ?, ?, ?, ?, ?, ?)",
    [(r["id"], r["name"], r["dimension"], r["severity"],
      r["threshold_pct"], r["description"], r["sql"].strip()) for r in rules],
)

# Historique : ces deux tables ne sont jamais vidées
con.execute("""
    CREATE TABLE IF NOT EXISTS dq_runs (
        run_id INTEGER, run_ts TIMESTAMP, table_name VARCHAR,
        total_rows BIGINT, rows_with_error BIGINT, clean_rows_pct DOUBLE,
        n_rules INTEGER, n_alerts INTEGER
    )
""")
con.execute("""
    CREATE TABLE IF NOT EXISTS dq_results (
        run_id INTEGER, rule_id VARCHAR, error_count BIGINT,
        error_rate_pct DOUBLE, status VARCHAR, sample_row_ids VARCHAR
    )
""")

run_id = con.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM dq_runs").fetchone()[0]
total = con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]

bad_rows = set()
n_alerts = 0
print(f"Run n°{run_id} sur {TABLE} ({total} lignes)\n")
print(f"{'ID':9} {'Erreurs':>8} {'Taux':>8} {'Seuil':>7}  Statut")

for r in rules:
    ids = [row[0] for row in con.execute(r["sql"]).fetchall()]
    bad_rows.update(ids)
    rate = len(ids) / total * 100
    status = "ALERTE" if rate > r["threshold_pct"] else "ok"
    n_alerts += status == "ALERTE"
    sample = ",".join(str(i) for i in sorted(ids)[:5])
    con.execute(
        "INSERT INTO dq_results VALUES (?, ?, ?, ?, ?, ?)",
        [run_id, r["id"], len(ids), round(rate, 3), status, sample],
    )
    print(f"{r['id']:9} {len(ids):8} {rate:7.2f}% {r['threshold_pct']:6.1f}%  {status}")

clean_pct = round((1 - len(bad_rows) / total) * 100, 2)
con.execute(
    "INSERT INTO dq_runs VALUES (?, now()::TIMESTAMP, ?, ?, ?, ?, ?, ?)",
    [run_id, TABLE, total, len(bad_rows), clean_pct, len(rules), n_alerts],
)

print(f"\nLignes avec au moins une erreur : {len(bad_rows)} ({100 - clean_pct:.2f} %)")
print(f"Lignes sans aucune erreur       : {clean_pct} %")
print(f"Règles en alerte                : {n_alerts} / {len(rules)}")

# Export CSV pour Power BI
os.makedirs("powerbi/data", exist_ok=True)
for t in ["dq_rules", "dq_runs", "dq_results"]:
    con.execute(f"COPY {t} TO 'powerbi/data/{t}.csv' (HEADER, DELIMITER ',')")
print("\nExport CSV : powerbi/data/")

con.close()