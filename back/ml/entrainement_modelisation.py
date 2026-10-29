# ============================================================
# 1. IMPORTS
# ============================================================

import sqlite3

from collections import Counter
from pathlib import Path

import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ============================================================
# 2. CONFIGURATION
# ============================================================

DOSSIER_ML = Path(__file__).resolve().parent
DOSSIER_PROJET = DOSSIER_ML.parent
DOSSIER_DATA = DOSSIER_PROJET / "data"
DOSSIER_RAPPORTS = DOSSIER_PROJET / "rapports"

DB_PATH = DOSSIER_DATA / "news.db"

DOSSIER_RAPPORTS.mkdir(exist_ok=True)

FICHIER_RAPPORT = (DOSSIER_RAPPORTS / "rapport_detection_anomalies.md")


# ------------------------------------------------------------
# Paramètres du modèle principal
# ------------------------------------------------------------

CONTAMINATION_PRINCIPALE = 0.10
RANDOM_STATE = 42


# ------------------------------------------------------------
# Paramètres de la baseline
# ------------------------------------------------------------

SEUIL_Z = 2


# ------------------------------------------------------------
# Paramètres du test de robustesse
# ------------------------------------------------------------

CONTAMINATIONS = [
    0.05,
    0.10,
    0.15,
    0.20
]


# ============================================================
# 3. FONCTIONS UTILITAIRES
# ============================================================

def charger_indicateurs():
    """
    Charge les indicateurs hebdomadaires depuis SQLite.
    """

    connexion = sqlite3.connect(DB_PATH)

    try:

        df = pd.read_sql_query(
            """
            SELECT *
            FROM indicateurs_hebdomadaires
            ORDER BY semaine
            """,
            connexion
        )

    finally:

        connexion.close()

    return df


def entrainer_isolation_forest(X_scaled, contamination):
    """
    Entraîne un Isolation Forest avec le taux
    de contamination fourni.
    """

    modele = IsolationForest(
        contamination=contamination,
        random_state=RANDOM_STATE
    )

    predictions = modele.fit_predict(X_scaled)

    scores = modele.decision_function(X_scaled)

    return (modele, predictions,scores)


def obtenir_variables_atypiques(
    df,
    df_scaled,
    semaine,
    colonnes,
    nombre_variables=5
):
    """
    Retourne les variables les plus atypiques
    pour une semaine donnée.

    Le classement repose sur la valeur absolue
    du z-score.
    """

    ligne_scaled = df_scaled[df_scaled["semaine"] == semaine]

    if ligne_scaled.empty:
        return []

    valeurs_standardisees = (
        ligne_scaled[colonnes].iloc[0]
    )

    variables_triees = (
        valeurs_standardisees.abs().sort_values(ascending=False)
    )

    resultats = []

    for variable in (variables_triees.head(nombre_variables).index):

        valeur_originale = df.loc[df["semaine"] == semaine, variable].iloc[0]

        z_score = (valeurs_standardisees[variable])

        resultats.append(
            {
                "variable": variable,
                "valeur": valeur_originale,
                "z_score": z_score
            }
        )

    return resultats


# ============================================================
# 4. CHARGEMENT DES DONNÉES
# ============================================================

df = charger_indicateurs()


if df.empty:

    raise ValueError("La table indicateurs_hebdomadaires est vide.")


print("\nDonnées chargées :")
print(df.head())
print("\nNombre de semaines :",len(df))


# ============================================================
# 5. CONSTRUCTION DES VARIABLES D'ENTRÉE
# ============================================================

semaines = df["semaine"].copy()

X = df.drop(columns=["semaine"])

print("\nDimensions de X :", X.shape)
print("\nVariables utilisées :")
print(X.columns.tolist())


# ============================================================
# 6. CONTRÔLE DES DONNÉES
# ============================================================

print("\nTypes des variables :")
print(X.dtypes)
print("\nValeurs manquantes :")
print(X.isnull().sum())

if X.isnull().any().any():

    raise ValueError(
        "Des valeurs manquantes sont présentes "
        "dans les variables du modèle."
    )


# ============================================================
# 7. STANDARDISATION
# ============================================================

scaler = StandardScaler()

X_scaled = scaler.fit_transform(X)
df_scaled = pd.DataFrame(X_scaled, columns=X.columns)
df_scaled["semaine"] = semaines.values

print("\nDimensions après standardisation :", X_scaled.shape)


# ============================================================
# 8. MODÈLE PRINCIPAL : ISOLATION FOREST
# ============================================================

(modele,predictions,scores) = entrainer_isolation_forest(
    X_scaled,
    CONTAMINATION_PRINCIPALE
)

df["anomalie"] = predictions

df["score_anomalie"] = scores

# ============================================================
# 9. SEMAINES ATYPIQUES
# ============================================================

semaines_atypiques = (
    df[df["anomalie"] == -1].sort_values(by="score_anomalie")
)

print("\nSemaines détectées comme atypiques :")
print(semaines_atypiques[["semaine", "score_anomalie"]])


# ============================================================
# 10. EXPLICATION DES ANOMALIES
# ============================================================

explications_anomalies = {}


print("\nVariables les plus atypiques ""par semaine :")


for semaine in (semaines_atypiques["semaine"]):

    variables_atypiques = (
        obtenir_variables_atypiques(
            df,
            df_scaled,
            semaine,
            X.columns
        )
    )

    explications_anomalies[semaine] = variables_atypiques

    print("\n===================================")
    print(f"Semaine : {semaine}")


    for resultat in variables_atypiques:

        print(
            f"{resultat['variable']} : "
            f"valeur = "
            f"{resultat['valeur']:.2f} | "
            f"z = "
            f"{resultat['z_score']:+.2f}"
        )


# ============================================================
# 11. BASELINE NAÏVE
# ============================================================

df_scaled["z_max_abs"] = (
    df_scaled[X.columns].abs().max(axis=1)
)

df_scaled["anomalie_baseline"] = (
    df_scaled["z_max_abs"]>= SEUIL_Z
)

semaines_baseline = (
    df_scaled[df_scaled[
            "anomalie_baseline"
        ]
    ][
        [
            "semaine",
            "z_max_abs"
        ]
    ]
    .sort_values(by="z_max_abs",ascending=False)
)

print("\nSemaines détectées ""par la baseline naïve :")
print(semaines_baseline)

# ============================================================
# 12. COMPARAISON BASELINE / ISOLATION FOREST
# ============================================================

semaines_isolation_forest = set(semaines_atypiques["semaine"])
semaines_baseline_set = set(semaines_baseline["semaine"])

communes = (semaines_isolation_forest & semaines_baseline_set)

uniquement_isolation_forest = (semaines_isolation_forest - semaines_baseline_set)

uniquement_baseline = (semaines_baseline_set - semaines_isolation_forest)

print("\n===================================")
print("COMPARAISON DES MÉTHODES")
print("===================================")
print("\nSemaines détectées ""par les deux méthodes :",sorted(communes))
print("\nUniquement par Isolation Forest :",sorted(uniquement_isolation_forest))
print("\nUniquement par la baseline naïve :",sorted(uniquement_baseline))
print("\nRésumé :")
print("Nombre d'anomalies Isolation Forest :",len(semaines_isolation_forest))
print("Nombre d'anomalies baseline :",len(semaines_baseline_set))
print("Nombre d'anomalies communes :",len(communes))


# ============================================================
# 13. ANALYSE DE ROBUSTESSE
# ============================================================

stabilite_anomalies = Counter()

resultats_contaminations = {}

print("\n===================================")
print("COMPARAISON DES CONTAMINATIONS")
print("===================================")

for contamination in CONTAMINATIONS:

    (_, predictions_test,_) = entrainer_isolation_forest(X_scaled,contamination)

    semaines_detectees = df.loc[predictions_test == -1,"semaine"].tolist()

    resultats_contaminations[contamination] = semaines_detectees

    stabilite_anomalies.update(semaines_detectees)


    print(
        f"\nContamination = "
        f"{contamination}"
    )

    print("Semaines détectées :",semaines_detectees)

print("\nStabilité des anomalies :")


for semaine, nombre in (stabilite_anomalies.most_common()):

    pourcentage = (nombre / len(CONTAMINATIONS)* 100)

    print(
        f"{semaine} : "
        f"{nombre}/"
        f"{len(CONTAMINATIONS)} "
        f"({pourcentage:.0f} %)"
    )


# ============================================================
# 14. TABLEAU DE STABILITÉ
# ============================================================

donnees_stabilite = []


for semaine, nombre in (stabilite_anomalies.most_common()):

    donnees_stabilite.append(
        {
            "semaine": semaine,
            "nombre_detections": nombre,
            "nombre_tests": len(CONTAMINATIONS),
            "stabilite_pct": (nombre / len(CONTAMINATIONS)* 100)
        }
    )

df_stabilite = pd.DataFrame(donnees_stabilite)

print("\nTableau de stabilité :")
print(df_stabilite)


# ============================================================
# 15. GÉNÉRATION DU RAPPORT
# ============================================================

with open(FICHIER_RAPPORT, "w", encoding="utf-8") as rapport:

    # --------------------------------------------------------
    # Titre
    # --------------------------------------------------------

    rapport.write(
        "# Rapport de détection "
        "des anomalies thématiques\n\n"
    )


    # --------------------------------------------------------
    # Méthodologie
    # --------------------------------------------------------

    rapport.write("## 1. Méthodologie\n\n")

    rapport.write(
        "L'analyse repose sur 16 variables "
        "hebdomadaires : la proportion et "
        "l'écart à la moyenne mobile sur "
        "4 semaines pour chacun des "
        "8 thèmes étudiés.\n\n"
    )

    rapport.write(
        "Les variables ont été standardisées "
        "avec `StandardScaler`.\n\n"
    )

    rapport.write(
        "Le modèle principal utilisé est "
        "`IsolationForest`, avec un taux "
        f"de contamination fixé à "
        f"{CONTAMINATION_PRINCIPALE:.0%}.\n\n"
    )

    rapport.write(
        "Les semaines détectées doivent être "
        "interprétées comme des périodes "
        "thématiquement atypiques et non comme "
        "des signaux faibles avérés.\n\n"
    )


    # --------------------------------------------------------
    # Isolation Forest
    # --------------------------------------------------------

    rapport.write(
        "## 2. Semaines détectées "
        "par Isolation Forest\n\n"
    )

    rapport.write("| Semaine | Score d'anomalie |\n")

    rapport.write("|---|---:|\n")

    for _, ligne in (semaines_atypiques.iterrows()):

        rapport.write(
            f"| {ligne['semaine']} "
            f"| "
            f"{ligne['score_anomalie']:.4f} "
            f"|\n"
        )


    # --------------------------------------------------------
    # Explication
    # --------------------------------------------------------

    rapport.write(
        "\n## 3. Variables expliquant "
        "les anomalies\n\n"
    )

    for semaine in (semaines_atypiques["semaine"]):

        rapport.write(f"### {semaine}\n\n")
        rapport.write("| Variable | Valeur | z-score |\n")
        rapport.write("|---|---:|---:|\n")

        for resultat in (explications_anomalies[semaine]):

            rapport.write(
                f"| "
                f"{resultat['variable']} "
                f"| "
                f"{resultat['valeur']:.2f} "
                f"| "
                f"{resultat['z_score']:+.2f} "
                f"|\n"
            )

        rapport.write("\n")


    # --------------------------------------------------------
    # Baseline
    # --------------------------------------------------------

    rapport.write("## 4. Baseline naïve\n\n")

    rapport.write(
        "La baseline considère une semaine "
        "comme atypique lorsqu'au moins "
        "une variable présente "
        f"`|z| >= {SEUIL_Z}`.\n\n"
    )

    rapport.write(
        f"Nombre de semaines détectées : "
        f"**{len(semaines_baseline_set)}**"
        "\n\n"
    )

    rapport.write("| Semaine | z-score maximal |\n")

    rapport.write("|---|---:|\n")

    for _, ligne in (semaines_baseline.iterrows()):

        rapport.write(
            f"| {ligne['semaine']} "
            f"| {ligne['z_max_abs']:.2f} "
            f"|\n"
        )


    # --------------------------------------------------------
    # Comparaison
    # --------------------------------------------------------

    rapport.write("\n## 5. Comparaison ""des méthodes\n\n")

    rapport.write(
        f"- Isolation Forest : "
        f"**{len(semaines_isolation_forest)}** "
        f"semaines\n"
    )

    rapport.write(
        f"- Baseline naïve : "
        f"**{len(semaines_baseline_set)}** "
        f"semaines\n"
    )

    rapport.write(
        f"- Anomalies communes : "
        f"**{len(communes)}** "
        f"semaines\n\n"
    )

    rapport.write("### Détectées par les deux méthodes\n\n")

    if communes:

        for semaine in sorted(communes):
            rapport.write(f"- {semaine}\n")

    else:
        rapport.write("Aucune.\n")
    rapport.write("\n### Uniquement ""par Isolation Forest\n\n")


    if uniquement_isolation_forest:

        for semaine in sorted(uniquement_isolation_forest):
            rapport.write(f"- {semaine}\n")

    else:
        rapport.write("Aucune.\n")
    rapport.write("\n### Uniquement ""par la baseline\n\n")

    if uniquement_baseline:

        for semaine in sorted(uniquement_baseline):
            rapport.write(f"- {semaine}\n")

    else:
        rapport.write("Aucune.\n")


    # --------------------------------------------------------
    # Robustesse
    # --------------------------------------------------------

    rapport.write(
        "\n## 6. Analyse de robustesse "
        "du modèle\n\n"
    )

    rapport.write(
        "Le modèle a été testé avec plusieurs "
        "taux de contamination afin de vérifier "
        "si certaines semaines restent détectées "
        "lorsque ce paramètre varie.\n\n"
    )

    rapport.write(
        "| Semaine | Nombre de détections "
        "| Stabilité |\n"
    )

    rapport.write("|---|---:|---:|\n")


    for _, ligne in (df_stabilite.iterrows()):

        rapport.write(
            f"| {ligne['semaine']} "
            f"| "
            f"{int(ligne['nombre_detections'])}"
            f"/"
            f"{int(ligne['nombre_tests'])} "
            f"| "
            f"{ligne['stabilite_pct']:.0f} % "
            f"|\n"
        )


    rapport.write(
        "\nLes semaines détectées dans plusieurs "
        "configurations sont considérées comme "
        "plus stables vis-à-vis du choix du "
        "paramètre de contamination.\n\n"
    )


    rapport.write(
        "Cette stabilité ne constitue cependant "
        "pas une mesure de performance du modèle "
        "et ne permet pas de qualifier "
        "automatiquement une période comme "
        "signal faible.\n"
    )


    # --------------------------------------------------------
    # Conclusion
    # --------------------------------------------------------

    rapport.write("\n## 7. Conclusion\n\n")
    rapport.write(
        "La baseline naïve détecte davantage "
        "de semaines atypiques qu'Isolation "
        "Forest.\n\n"
    )
    rapport.write(
        "Dans cette expérimentation, les "
        "anomalies détectées par le modèle "
        "principal sont également retrouvées "
        "par la baseline.\n\n"
    )
    rapport.write(
        "Isolation Forest fournit cependant "
        "une sélection plus restreinte des "
        "semaines dont la combinaison des "
        "indicateurs thématiques est "
        "inhabituelle.\n\n"
    )
    rapport.write(
        "En l'absence de vérité terrain, "
        "il n'est pas possible d'affirmer "
        "qu'une semaine détectée correspond "
        "à un véritable signal faible.\n\n"
    )
    rapport.write(
        "Les résultats doivent donc être "
        "interprétés comme des périodes "
        "atypiques pouvant orienter une "
        "analyse humaine plus approfondie.\n"
    )


# ============================================================
# 16. FIN DU SCRIPT
# ============================================================

print("\nRapport généré :", FICHIER_RAPPORT)
print("\nEntraînement et analyse terminés.")