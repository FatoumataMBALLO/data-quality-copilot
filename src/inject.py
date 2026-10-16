import duckdb
import numpy as np

SEED = 42  # graine fixe : le résultat est reproductible
rng = np.random.default_rng(SEED)

con = duckdb.connect("data/dq.duckdb")

# raw_bank reste intacte : on travaille sur une copie
con.execute("DROP TABLE IF EXISTS injected_bank")
con.execute("DROP TABLE IF EXISTS injection_log")
con.execute("CREATE TABLE injected_bank AS SELECT * FROM raw_bank")
con.execute("""
    CREATE TABLE injection_log (
        row_id BIGINT,
        column_name VARCHAR,
        anomaly_type VARCHAR,
        dimension VARCHAR,
        original_value VARCHAR,
        injected_value VARCHAR
    )
""")

used = set()  # une ligne ne reçoit qu'une seule anomalie
log = []


def pick(k, where="TRUE"):
    """Tire k row_id au hasard, parmi les lignes non encore modifiées."""
    ids = [r[0] for r in con.execute(
        f"SELECT row_id FROM injected_bank WHERE {where}").fetchall()]
    ids = [i for i in ids if i not in used]
    chosen = [int(i) for i in rng.choice(ids, size=k, replace=False)]
    used.update(chosen)
    return chosen


def inject(col, k, make_value, anomaly_type, dimension, where="TRUE"):
    for rid in pick(k, where):
        old = con.execute(
            f'SELECT "{col}" FROM injected_bank WHERE row_id = ?', [rid]
        ).fetchone()[0]
        new = make_value()
        con.execute(
            f'UPDATE injected_bank SET "{col}" = ? WHERE row_id = ?', [new, rid]
        )
        log.append((rid, col, anomaly_type, dimension,
                    str(old), None if new is None else str(new)))


# --- Complétude : valeurs manquantes ---
inject("age", 400, lambda: None, "valeur_manquante", "Complétude")
inject("job", 800, lambda: None, "valeur_manquante", "Complétude")
inject("education", 600, lambda: None, "valeur_manquante", "Complétude")

# --- Validité : valeurs hors plage ou mal formatées ---
inject("age", 200, lambda: int(rng.choice([0, -3, 150, 200, 999])),
       "age_hors_plage", "Validité")
inject("marital", 400,
       lambda: str(rng.choice(["Married", "marrried", " single", "SINGLE"])),
       "format_incorrect", "Validité")
inject("month", 200, lambda: str(rng.choice(["sept", "13", "xyz"])),
       "mois_invalide", "Validité")

# --- Cohérence : champs qui se contredisent ---
inject("duration", 100, lambda: 0, "duree_nulle_avec_y_yes", "Cohérence",
       where="y = 'yes'")
inject("previous", 100, lambda: 0, "previous_zero_avec_pdays", "Cohérence",
       where="pdays < 999 AND previous > 0")

# --- Plausibilité : valeurs extrêmes ---
inject("campaign", 80, lambda: int(rng.integers(200, 501)),
       "valeur_extreme", "Plausibilité")
inject("duration", 80, lambda: int(rng.integers(20000, 50001)),
       "valeur_extreme", "Plausibilité")

# --- Unicité : lignes dupliquées (nouveau row_id, contenu identique) ---
src_ids = pick(200)
next_id = con.execute("SELECT MAX(row_id) FROM injected_bank").fetchone()[0] + 1
for offset, rid in enumerate(src_ids):
    new_id = next_id + offset
    con.execute(
        "INSERT INTO injected_bank "
        "SELECT CAST(? AS BIGINT), * EXCLUDE (row_id) "
        "FROM injected_bank WHERE row_id = ?",
        [new_id, rid],
    )
    log.append((new_id, "*", "ligne_dupliquee", "Unicité",
                f"copie de row_id={rid}", None))

# --- Enregistrement du journal ---
con.executemany("INSERT INTO injection_log VALUES (?, ?, ?, ?, ?, ?)", log)
con.execute(
    "COPY injection_log TO 'data/injected/injection_log.csv' (HEADER, DELIMITER ',')"
)

print("Lignes raw_bank      :", con.execute("SELECT COUNT(*) FROM raw_bank").fetchone()[0])
print("Lignes injected_bank :", con.execute("SELECT COUNT(*) FROM injected_bank").fetchone()[0])
print()
print(con.execute("""
    SELECT dimension, anomaly_type, column_name, COUNT(*) AS n
    FROM injection_log
    GROUP BY ALL
    ORDER BY dimension, anomaly_type, column_name
""").df().to_string(index=False))

con.close()