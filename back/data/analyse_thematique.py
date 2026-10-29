import sqlite3
import re

from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, date

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


# ============================================================
# 1. CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent
DB_PATH = DOSSIER_SCRIPT / "news.db"

DATE_DEBUT = date(2016, 1, 1)
DATE_FIN = date(2016, 11, 8)


# ============================================================
# 2. PARAMÈTRES DE L'ANALYSE LEXICALE
# ============================================================

# Mots très fréquents de liaison / grammaire
STOPWORDS = set(ENGLISH_STOP_WORDS)


# Mots fréquents dans le langage journalistique
# mais peu utiles pour identifier un thème
BRUIT_JOURNALISTIQUE = {
    "said",
    "says",
    "say",
    "report",
    "reported",
    "reports",
    "according",
    "news",
    "photo",
    "video"
}


# Mots très fréquents dans le corpus
# mais peu discriminants pour l'analyse
BRUIT_CORPUS = {
    "like",
    "people",
    "just",
    "new",
    "time",
    "year",
    "years",
    "way",
    "think",
    "make",
    "work",
    "know",
    "really",
    "going",
    "told",
    "day",
    "did",
    "right",
    "want",
    "good",
    "lot",
    "life",
    "things",
    "long",
    "got",
    "old",
    "use",
    "come",
    "big",
    "week",
    "need",
    "thing",
    "little",

    # Contractions fréquentes mal gérées par les stopwords
    "it's",
    "don't",
    "that's",
    "i'm",
    "he's"
}


# Mots issus du scraping ou du contenu technique des pages
MOTS_PARASITES_BIGRAMMES = {
    "menu",
    "icon",
    "chevron",
    "navigation",
    "section",
    "expandable",
    "previous",
    "options",
    "originally",
    "appeared",
    "recode",
    "coverage",
    "source",
    "text",
    "twitter",
    "pic",
    "advertise",
    "hyperallergic",
    "nectar",
    "ads"
}


# ============================================================
# 3. THÈMES EXPÉRIMENTAUX
# ============================================================

THEMES = {

    "politique_electorale": [
        "donald trump",
        "hillary clinton",
        "bernie sanders",
        "ted cruz",
        "republican party",
        "democratic party",
        "trump campaign",
        "president elect"
    ],

    "institutions_gouvernement": [
        "white house",
        "supreme court",
        "federal government",
        "state department",
        "vice president",
        "obama administration",
        "president obama",
        "barack obama"
    ],

    "relations_internationales_securite": [
        "foreign policy",
        "islamic state",
        "north korea",
        "european union",
        "hong kong",
        "prime minister",
        "law enforcement",
        "police officers"
    ],

    "droits_societe": [
        "human rights",
        "civil rights",
        "african american",
        "sexual assault",
        "mental health"
    ],

    "economie": [
        "wall street",
        "real estate",
        "silicon valley"
    ],

    "sante_environnement": [
        "health care",
        "climate change"
    ],

    "technologie_medias": [
        "social media",
        "virtual reality",
        "washington post",
        "york times"
    ],

    "territoires": [
        "united states",
        "north carolina",
        "south carolina",
        "los angeles",
        "york city",
        "san francisco"
    ]
}


# ============================================================
# 4. FONCTIONS UTILITAIRES
# ============================================================

def extraire_mots_filtres(texte):
    """
    Extrait les mots d'un texte puis retire :
    - les stopwords ;
    - le bruit journalistique ;
    - le bruit propre au corpus ;
    - les mots de moins de 3 caractères.
    """

    texte = texte.lower()

    mots = re.findall(
        r"\b[a-zA-Z']+\b",
        texte
    )

    return [
        mot
        for mot in mots
        if mot not in STOPWORDS
        and mot not in BRUIT_JOURNALISTIQUE
        and mot not in BRUIT_CORPUS
        and len(mot) > 2
    ]


def bigramme_est_propre(bigramme):
    """
    Retourne True si aucun mot du bigramme
    ne fait partie des mots parasites.
    """

    mots = bigramme.split()

    return not any(
        mot in MOTS_PARASITES_BIGRAMMES
        for mot in mots
    )


# ============================================================
# 5. CHARGEMENT DES ARTICLES
# ============================================================

connexion = sqlite3.connect(DB_PATH)
curseur = connexion.cursor()


curseur.execute("""
SELECT
    date,
    article_normalise
FROM articles
WHERE is_nlp_usable = 1
  AND article_normalise IS NOT NULL
  AND TRIM(article_normalise) != ''
ORDER BY date
""")


articles_normalises = curseur.fetchall()


print(
    "\nNombre d'articles normalisés chargés :",
    len(articles_normalises)
)


# ============================================================
# 6. ANALYSE LEXICALE : MOTS ET BIGRAMMES
# ============================================================

compteur_mots = Counter()
compteur_bigrammes = Counter()


for _, texte in articles_normalises:

    # Le filtrage des mots n'est réalisé qu'une seule fois
    # pour chaque article.
    mots_filtres = extraire_mots_filtres(texte)

    # Comptage des mots
    compteur_mots.update(mots_filtres)

    # Création des bigrammes à partir des mots filtrés
    bigrammes = [
        f"{mot1} {mot2}"
        for mot1, mot2 in zip(
            mots_filtres,
            mots_filtres[1:]
        )
    ]

    compteur_bigrammes.update(bigrammes)


# ------------------------------------------------------------
# Affichage des mots les plus fréquents
# ------------------------------------------------------------

print("\n50 mots les plus fréquents après filtrage :")

for mot, occurrence in compteur_mots.most_common(50):

    print(mot, occurrence)


# ------------------------------------------------------------
# Affichage des bigrammes propres
# ------------------------------------------------------------

print("\n50 bigrammes propres les plus fréquents :")

nombre_affiche = 0

for bigramme, occurrence in compteur_bigrammes.most_common():

    if not bigramme_est_propre(bigramme):
        continue

    print(bigramme, occurrence)

    nombre_affiche += 1

    if nombre_affiche == 50:
        break


# ============================================================
# 7. ANALYSE HEBDOMADAIRE DES THÈMES
# ============================================================

# Nombre total d'articles par semaine
total_par_semaine = defaultdict(int)

# Nombre d'articles associés à chaque thème par semaine
themes_par_semaine = defaultdict(lambda: defaultdict(int))


for date_texte, texte in articles_normalises:

    # --------------------------------------------------------
    # Conversion de la date
    # --------------------------------------------------------

    try:

        date_article = datetime.fromisoformat(str(date_texte)).date()

    except (ValueError, TypeError):

        continue


    # --------------------------------------------------------
    # Limitation de la période étudiée
    # --------------------------------------------------------

    if not (
        DATE_DEBUT
        <= date_article
        <= DATE_FIN
    ):
        continue


    # --------------------------------------------------------
    # Numéro de semaine ISO
    # --------------------------------------------------------

    annee_iso, semaine_iso, _ = (date_article.isocalendar())

    cle_semaine = (f"{annee_iso}-S{semaine_iso:02d}")

    total_par_semaine[
        cle_semaine
    ] += 1

    texte_minuscule = texte.lower()


    # --------------------------------------------------------
    # Recherche des thèmes
    # --------------------------------------------------------

    for theme, bigrammes_theme in THEMES.items():

        # Un article compte une seule fois pour un thème,
        # même si plusieurs bigrammes du thème apparaissent.
        theme_present = any(
            bigramme in texte_minuscule
            for bigramme in bigrammes_theme
        )

        if theme_present:

            themes_par_semaine[cle_semaine][theme] += 1


# ============================================================
# 8. CALCUL DES PROPORTIONS HEBDOMADAIRES
# ============================================================

semaines = sorted(total_par_semaine.keys())

proportions_par_semaine = defaultdict(dict)


for semaine in semaines:

    total = total_par_semaine[semaine]

    for theme in THEMES:

        nombre = themes_par_semaine[semaine][theme]

        if total > 0:

            proportion = (nombre / total* 100)

        else:

            proportion = 0

        proportions_par_semaine[semaine][theme] = proportion


# ------------------------------------------------------------
# Affichage des résultats hebdomadaires
# ------------------------------------------------------------

print(
    "\nNombre et proportion d'articles "
    "par thème et par semaine :"
)


for semaine in semaines:

    total = total_par_semaine[semaine]

    print("\n-----------------------------------")

    print(f"Semaine : {semaine}")

    print(f"Total articles exploitables : {total}")


    for theme in THEMES:

        nombre = themes_par_semaine[semaine][theme]

        proportion = proportions_par_semaine[semaine][theme]

        print(
            f"{theme} : "
            f"{nombre} articles "
            f"({proportion:.2f} %)"
        )


# ============================================================
# 9. CALCUL DES INDICATEURS HEBDOMADAIRES
# ============================================================

# Les quatre premières semaines ne peuvent pas être utilisées,
# car quatre semaines précédentes sont nécessaires pour
# calculer la moyenne mobile.

indicateurs_hebdomadaires = {}


print(
    "\n\nMoyenne mobile sur 4 semaines "
    "et écart à la tendance précédente :"
)


for index in range(4,len(semaines)):

    semaine_actuelle = semaines[index]

    # La semaine S45 ne contient que les 7 et 8 novembre.
    # Elle est donc exclue de la modélisation.
    if semaine_actuelle == "2016-S45":
        continue

    semaines_precedentes = semaines[index - 4:index]

    indicateurs_hebdomadaires[semaine_actuelle] = {}

    print("\n===================================")

    print(f"Semaine : {semaine_actuelle}")


    for theme in THEMES:

        proportion_actuelle = (
            proportions_par_semaine[semaine_actuelle][theme]
        )

        valeurs_precedentes = [
            proportions_par_semaine[semaine][theme]
            for semaine
            in semaines_precedentes
        ]

        moyenne_mobile = (sum(valeurs_precedentes)/ len(valeurs_precedentes))

        ecart = (proportion_actuelle - moyenne_mobile)


        # Les résultats sont stockés une fois.
        # Ils seront ensuite utilisés directement
        # pour l'insertion dans SQLite.
        indicateurs_hebdomadaires[semaine_actuelle][
            f"{theme}_proportion"
        ] = proportion_actuelle


        indicateurs_hebdomadaires[semaine_actuelle][
            f"{theme}_ecart"
        ] = ecart


        print(
            f"{theme} : "
            f"{proportion_actuelle:.2f} % | "
            f"moyenne 4 sem. : "
            f"{moyenne_mobile:.2f} % | "
            f"écart : {ecart:+.2f} points"
        )


# ============================================================
# 10. CRÉATION DE LA TABLE DES INDICATEURS
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS indicateurs_hebdomadaires (

    semaine TEXT PRIMARY KEY,

    politique_electorale_proportion REAL,
    politique_electorale_ecart REAL,

    institutions_gouvernement_proportion REAL,
    institutions_gouvernement_ecart REAL,

    relations_internationales_securite_proportion REAL,
    relations_internationales_securite_ecart REAL,

    droits_societe_proportion REAL,
    droits_societe_ecart REAL,

    economie_proportion REAL,
    economie_ecart REAL,

    sante_environnement_proportion REAL,
    sante_environnement_ecart REAL,

    technologie_medias_proportion REAL,
    technologie_medias_ecart REAL,

    territoires_proportion REAL,
    territoires_ecart REAL
)
""")


connexion.commit()


# ============================================================
# 11. INSERTION DES INDICATEURS DANS SQLITE
# ============================================================

# On vide la table afin que son contenu corresponde exactement
# au résultat du calcul courant.
#
# Cela évite de conserver une ancienne semaine si la période
# d'analyse ou la méthode de calcul sont modifiées plus tard.

curseur.execute("""DELETE FROM indicateurs_hebdomadaires""")


REQUETE_INSERTION = """
INSERT INTO indicateurs_hebdomadaires (

    semaine,

    politique_electorale_proportion,
    politique_electorale_ecart,

    institutions_gouvernement_proportion,
    institutions_gouvernement_ecart,

    relations_internationales_securite_proportion,
    relations_internationales_securite_ecart,

    droits_societe_proportion,
    droits_societe_ecart,

    economie_proportion,
    economie_ecart,

    sante_environnement_proportion,
    sante_environnement_ecart,

    technologie_medias_proportion,
    technologie_medias_ecart,

    territoires_proportion,
    territoires_ecart

)
VALUES (
    ?, ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?, ?, ?
)
"""


lignes_a_inserer = []


for semaine, valeurs in (
    indicateurs_hebdomadaires.items()
):

    ligne = (

        semaine,
        valeurs["politique_electorale_proportion"],
        valeurs["politique_electorale_ecart"],
        valeurs["institutions_gouvernement_proportion"],
        valeurs["institutions_gouvernement_ecart"],
        valeurs["relations_internationales_securite_proportion"],
        valeurs["relations_internationales_securite_ecart"],
        valeurs["droits_societe_proportion"],
        valeurs["droits_societe_ecart"],
        valeurs["economie_proportion"],
        valeurs["economie_ecart"],
        valeurs["sante_environnement_proportion"],
        valeurs["sante_environnement_ecart"],
        valeurs["technologie_medias_proportion"],
        valeurs["technologie_medias_ecart"],
        valeurs["territoires_proportion"],
        valeurs["territoires_ecart"]
    )

    lignes_a_inserer.append(ligne)

curseur.executemany(REQUETE_INSERTION, lignes_a_inserer)


connexion.commit()


# ============================================================
# 12. CONTRÔLE DE LA TABLE
# ============================================================

curseur.execute("""
SELECT COUNT(*)
FROM indicateurs_hebdomadaires
""")

nombre_semaines = curseur.fetchone()[0]

print("\nNombre de semaines enregistrées :", nombre_semaines)

curseur.execute("""
SELECT *
FROM indicateurs_hebdomadaires
ORDER BY semaine
LIMIT 5
""")


print(
    "\nPremières lignes de la table "
    "indicateurs_hebdomadaires :"
)


for ligne in curseur.fetchall():

    print(ligne)


# ============================================================
# 13. FERMETURE DE LA CONNEXION
# ============================================================

connexion.close()

print("\nAnalyse thématique terminée.")