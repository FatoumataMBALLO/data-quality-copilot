import os
import re
import duckdb

DB = "data/dq.duckdb"

# Phrases rédigées à l'avance : (cause probable, impact, correction suggérée).
# Aucun chiffre ici : tous les nombres viennent des résultats des contrôles.
MODELES = {
    "COMP_01": ("Âge absent à la saisie ou perdu lors d'une transformation de données.",
                "Les analyses par tranche d'âge et les modèles qui utilisent l'âge excluent ces lignes ou sont faussés.",
                "Retrouver l'âge dans la source ; sinon le coder explicitement comme inconnu et bloquer les imports où il est vide."),
    "COMP_02": ("Profession non renseignée, ou colonne mal alimentée lors de l'import.",
                "Les segmentations par profession sous-représentent ces clients.",
                "Compléter depuis la source, ou utiliser la modalité unknown déjà prévue plutôt qu'une valeur vide."),
    "COMP_03": ("Niveau d'études non renseigné, ou colonne mal alimentée lors de l'import.",
                "Les analyses par niveau d'études perdent une partie des clients.",
                "Compléter depuis la source, ou utiliser la modalité unknown plutôt qu'une valeur vide."),
    "COMP_04": ("Information collectée de façon incomplète auprès des clients, déjà présente dans la source.",
                "La variable est peu exploitable telle quelle : une part importante des clients n'a pas de valeur connue.",
                "Documenter la limite, traiter unknown comme une catégorie à part, ou envisager d'écarter la variable."),
    "VALID_01": ("Erreur de saisie, ou valeur technique utilisée à la place de l'âge.",
                 "Des âges impossibles faussent les moyennes et les tranches d'âge.",
                 "Rejeter à l'import les âges hors de la plage autorisée et corriger à la source."),
    "VALID_02": ("Saisie libre, ou casse et espaces non normalisés.",
                 "Les regroupements par statut marital créent de fausses catégories.",
                 "Normaliser (minuscules, espaces retirés) et restreindre la saisie à la liste autorisée."),
    "VALID_03": ("Abréviations non conformes, ou valeurs non reconnues pour le mois.",
                 "Les analyses saisonnières et le tri chronologique deviennent incorrects.",
                 "Valider le mois contre la liste des abréviations autorisées."),
    "COH_01": ("Durée d'appel effacée ou mal enregistrée alors que la souscription est notée.",
               "Le lien entre durée d'appel et souscription est faussé, ce qui peut tromper un modèle.",
               "Vérifier ces lignes dans le système d'origine et corriger la durée ou le résultat."),
    "COH_02": ("Nombre de contacts précédents non mis à jour alors qu'un délai depuis le dernier contact existe.",
               "L'historique de contact des clients est sous-estimé.",
               "Recalculer le nombre de contacts précédents à partir de l'historique."),
    "COH_03": ("Code de substitution du délai utilisé alors que des contacts précédents sont enregistrés, déjà présent dans la source.",
               "Les statistiques sur le délai depuis le dernier contact sont peu fiables pour ces clients.",
               "Documenter l'incohérence et traiter ces lignes à part dans les analyses sur le délai."),
    "PLAUS_01": ("Campagnes exceptionnellement longues, ou erreurs de saisie.",
                 "Les valeurs extrêmes tirent les moyennes vers le haut.",
                 "Examiner ces valeurs ; les plafonner ou les exclure selon l'analyse."),
    "PLAUS_02": ("Appels exceptionnellement longs, ou erreurs de mesure de la durée.",
                 "Les valeurs extrêmes tirent les moyennes vers le haut.",
                 "Examiner ces valeurs ; les plafonner ou les exclure selon l'analyse."),
    "UNIQ_01": ("Double chargement des données, ou fusion de sources sans clé unique.",
                "Les clients dupliqués sont comptés plusieurs fois et gonflent les volumes.",
                "Dédoublonner à l'import et mettre en place une clé unique."),
}

GENERIQUE = ("Cause à investiguer dans la source ou dans le pipeline d'import.",
             "La qualité des analyses qui utilisent cette colonne est dégradée.",
             "Examiner les lignes en erreur et corriger à la source.")

NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")
IDENTIFIANT = re.compile(r"\b[A-Z]+_\d+\b")


def nombres_dans(texte):
    """Tous les nombres d'un texte, hors identifiants de règles (COMP_04...)."""
    texte = IDENTIFIANT.sub("", texte)
    return {round(float(n.replace(",", ".")), 4) for n in NOMBRE.findall(texte)}


def fmt_taux(x):
    return f"{x:.2f}".replace(".", ",")


def fmt_seuil(x):
    return f"{x:g}".replace(".", ",")


def generer(f):
    """Point d'extension : un vrai modèle pourrait remplacer cette fonction.
    Elle reçoit les faits d'une règle et renvoie cause, impact, correction."""
    cause, impact, correction = MODELES.get(f["rule_id"], GENERIQUE)
    if f["structural"] is not None:
        cause += (f" Sur {f['count']} lignes en erreur, {f['structural']} sont déjà dans les "
                  f"données brutes et {f['injected']} sont apparues ensuite.")
    impact += f" Taux observé : {fmt_taux(f['rate'])} %, seuil d'alerte : {fmt_seuil(f['threshold'])} %."
    if f["sample"]:
        correction += f" Lignes à examiner en premier (row_id) : {', '.join(f['sample'])}."
    return {"cause": cause, "impact": impact, "correction": correction}


def verifier(f, texte):
    """Les chiffres obligatoires sont présents, et aucun nombre n'est inventé."""
    autorises = nombres_dans(f["name"] + " " + f["description"])
    autorises |= {float(f["count"]), float(fmt_taux(f["rate"]).replace(",", ".")),
                  float(fmt_seuil(f["threshold"]).replace(",", "."))}
    if f["structural"] is not None:
        autorises |= {float(f["structural"]), float(f["injected"])}
    autorises |= {float(i) for i in f["sample"]}
    obligatoires = {float(f["count"]), float(fmt_taux(f["rate"]).replace(",", "."))}
    trouves = nombres_dans(texte)
    return obligatoires <= trouves and trouves <= autorises


con = duckdb.connect(DB)

lignes = con.execute("""
    SELECT d.run_id, r.rule_id, r.rule_name, r.dimension, r.severity, r.threshold_pct,
           r.description, d.error_count, d.error_rate_pct, d.sample_row_ids,
           o.structural_count, o.injected_count
    FROM dq_results d
    JOIN dq_rules r ON r.rule_id = d.rule_id
    LEFT JOIN dq_origin o ON o.rule_id = d.rule_id AND o.run_id = d.run_id
    WHERE d.run_id = (SELECT MAX(run_id) FROM dq_results)
      AND d.status = 'ALERTE'
    ORDER BY CASE r.severity WHEN 'critique' THEN 1 WHEN 'majeure' THEN 2 ELSE 3 END,
             d.error_rate_pct DESC
""").fetchall()

con.execute("DROP TABLE IF EXISTS dq_explanations")
con.execute("""
    CREATE TABLE dq_explanations (
        run_id INTEGER, rule_id VARCHAR, severity VARCHAR,
        cause VARCHAR, impact VARCHAR, correction VARCHAR,
        generator VARCHAR, numbers_ok BOOLEAN
    )
""")

os.makedirs("docs", exist_ok=True)
md = ["# Explications des contrôles qualité", ""]
print(f"{'Règle':9} {'Sévérité':9} {'Chiffres vérifiés'}")

for (run_id, rule_id, name, dim, sev, thr, desc, count, rate, sample,
     structural, injected) in lignes:
    f = {
        "rule_id": rule_id, "name": name, "description": desc, "threshold": thr,
        "count": int(count), "rate": float(rate),
        "sample": [s for s in (sample or "").split(",") if s],
        "structural": None if structural is None else int(structural),
        "injected": None if injected is None else int(injected),
    }
    e = generer(f)
    ok = verifier(f, " ".join(e.values()))
    con.execute("INSERT INTO dq_explanations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [run_id, rule_id, sev, e["cause"], e["impact"], e["correction"],
                 "modeles_de_phrases", ok])
    print(f"{rule_id:9} {sev:9} {'OK' if ok else 'ECHEC'}")
    md += [f"## {rule_id} : {name} ({sev})", "",
           f"- **Cause probable** : {e['cause']}",
           f"- **Impact** : {e['impact']}",
           f"- **Correction suggérée** : {e['correction']}",
           f"- *Chiffres vérifiés : {'oui' if ok else 'NON'}*", ""]

with open("docs/explications.md", "w", encoding="utf-8") as fh:
    fh.write("\n".join(md))

con.execute("COPY dq_explanations TO 'powerbi/data/dq_explanations.csv' (HEADER, DELIMITER ',')")
print(f"\n{len(lignes)} explications générées : docs/explications.md et powerbi/data/dq_explanations.csv")
con.close()