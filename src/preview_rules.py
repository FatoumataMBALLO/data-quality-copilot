import duckdb
import yaml

with open("rules/rules.yaml", encoding="utf-8") as f:
    rules = yaml.safe_load(f)["rules"]

con = duckdb.connect("data/dq.duckdb", read_only=True)
total = con.execute("SELECT COUNT(*) FROM injected_bank").fetchone()[0]

print(f"{'ID':9} {'Dimension':13} {'Erreurs':>8} {'Taux':>8} {'Seuil':>7}  Statut")
for r in rules:
    n = con.execute(f"SELECT COUNT(*) FROM ({r['sql']})").fetchone()[0]
    rate = n / total * 100
    statut = "ALERTE" if rate > r["threshold_pct"] else "ok"
    print(f"{r['id']:9} {r['dimension']:13} {n:8} {rate:7.2f}% {r['threshold_pct']:6.1f}%  {statut}")

con.close()