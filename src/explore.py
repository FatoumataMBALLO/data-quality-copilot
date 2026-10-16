import duckdb

con = duckdb.connect("data/dq.duckdb", read_only=True)

total = con.execute("SELECT COUNT(*) FROM raw_bank").fetchone()[0]
print("Lignes :", total)

cols = con.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_name = 'raw_bank' ORDER BY ordinal_position"
).fetchall()

print("\n--- Valeurs NULL et 'unknown' par colonne ---")
for name, dtype in cols:
    if name == "row_id":
        continue
    nulls = con.execute(f'SELECT COUNT(*) FROM raw_bank WHERE "{name}" IS NULL').fetchone()[0]
    line = f"{name:16} NULL={nulls:5}"
    if dtype == "VARCHAR":
        unk = con.execute(
            f"""SELECT COUNT(*) FROM raw_bank WHERE "{name}" = 'unknown'"""
        ).fetchone()[0]
        line += f"   unknown={unk:5} ({unk / total:.1%})"
    print(line)

print("\n--- Colonnes numériques (min, max, moyenne) ---")
for name, dtype in cols:
    if dtype in ("BIGINT", "INTEGER", "DOUBLE") and name != "row_id":
        mn, mx, avg = con.execute(
            f'SELECT MIN("{name}"), MAX("{name}"), ROUND(AVG("{name}"), 2) FROM raw_bank'
        ).fetchone()
        print(f"{name:16} min={mn:>10}  max={mx:>10}  moyenne={avg}")

print("\n--- Doublons (lignes identiques, hors row_id) ---")
distinct = con.execute(
    "SELECT COUNT(*) FROM (SELECT DISTINCT * EXCLUDE (row_id) FROM raw_bank)"
).fetchone()[0]
print("Lignes en trop :", total - distinct)

print("\n--- Répartition de y ---")
print(con.execute("SELECT y, COUNT(*) AS n FROM raw_bank GROUP BY y ORDER BY n DESC").df().to_string(index=False))

print("\n--- Cohérence pdays / previous ---")
print("pdays = 999 mais previous > 0 :", con.execute(
    "SELECT COUNT(*) FROM raw_bank WHERE pdays = 999 AND previous > 0"
).fetchone()[0])
print("pdays < 999 mais previous = 0 :", con.execute(
    "SELECT COUNT(*) FROM raw_bank WHERE pdays < 999 AND previous = 0"
).fetchone()[0])

con.close()