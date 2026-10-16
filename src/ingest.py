import duckdb

CSV = "data/raw/bank-additional-full.csv"
DB = "data/dq.duckdb"

con = duckdb.connect(DB)

con.execute("DROP TABLE IF EXISTS raw_bank")
con.execute(f"""
    CREATE TABLE raw_bank AS
    SELECT row_number() OVER () AS row_id, *
    FROM read_csv('{CSV}', delim=';', header=true, types={{'y': 'VARCHAR'}})
""")

print("Nombre de lignes :", con.execute("SELECT COUNT(*) FROM raw_bank").fetchone()[0])
print()
print("Colonnes et types :")
for name, dtype in con.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_name = 'raw_bank' ORDER BY ordinal_position"
).fetchall():
    print(f"  {name:20} {dtype}")

print()
print("Aperçu :")
print(con.execute("SELECT * FROM raw_bank LIMIT 3").df().to_string())

con.close()