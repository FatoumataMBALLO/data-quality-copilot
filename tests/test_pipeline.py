import duckdb
import pytest


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect("data/dq.duckdb", read_only=True)
    yield c
    c.close()


def un(con, sql):
    return con.execute(sql).fetchone()[0]


def test_donnees_brutes_intactes(con):
    assert un(con, "SELECT COUNT(*) FROM raw_bank") == 41188


def test_copie_contient_les_doublons_injectes(con):
    assert un(con, "SELECT COUNT(*) FROM injected_bank") == 41188 + 200


def test_journal_d_injection_complet(con):
    assert un(con, "SELECT COUNT(*) FROM injection_log") == 3160


# (règle, colonne injectée, type d'anomalie, nombre injecté)
INJECTIONS = [
    ("COMP_01", "age", "valeur_manquante", 400),
    ("COMP_02", "job", "valeur_manquante", 800),
    ("COMP_03", "education", "valeur_manquante", 600),
    ("VALID_01", "age", "age_hors_plage", 200),
    ("VALID_02", "marital", "format_incorrect", 400),
    ("VALID_03", "month", "mois_invalide", 200),
    ("COH_01", "duration", "duree_nulle_avec_y_yes", 100),
    ("COH_02", "previous", "previous_zero_avec_pdays", 100),
    ("PLAUS_01", "campaign", "valeur_extreme", 80),
    ("PLAUS_02", "duration", "valeur_extreme", 80),
    ("UNIQ_01", "*", "ligne_dupliquee", 200),
]


@pytest.mark.parametrize("regle,colonne,anomalie,attendu", INJECTIONS)
def test_chaque_anomalie_injectee_est_detectee(con, regle, colonne, anomalie, attendu):
    sql_regle = un(con, f"SELECT sql_query FROM dq_rules WHERE rule_id = '{regle}'")
    detectees = un(con, f"""
        SELECT COUNT(*) FROM injection_log
        WHERE column_name = '{colonne}' AND anomaly_type = '{anomalie}'
          AND row_id IN ({sql_regle})
    """)
    assert detectees == attendu


def test_une_explication_par_regle_en_alerte(con):
    alertes = un(con, """SELECT COUNT(*) FROM dq_results
        WHERE status = 'ALERTE' AND run_id = (SELECT MAX(run_id) FROM dq_results)""")
    assert un(con, "SELECT COUNT(*) FROM dq_explanations") == alertes


def test_tous_les_chiffres_des_explications_sont_verifies(con):
    assert un(con, "SELECT COUNT(*) FROM dq_explanations WHERE NOT numbers_ok") == 0