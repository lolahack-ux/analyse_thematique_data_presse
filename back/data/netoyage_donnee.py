import sqlite3
import re
import unicodedata
from collections import Counter
from pathlib import Path
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from collections import defaultdict
from datetime import datetime, date, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

DOSSIER_SCRIPT = Path(__file__).resolve().parent
DB_PATH = DOSSIER_SCRIPT / "news.db"


# ============================================================
# FONCTION DE NORMALISATION
# ============================================================

def normaliser_texte(texte):
    """
    Nettoyage léger du texte pour préparer les futures analyses NLP.
    Le texte original reste conservé dans la colonne 'article'.
    """

    if texte is None:
        return None

    # Normalisation Unicode
    texte = unicodedata.normalize("NFKC", texte)

    # Remplacement des espaces insécables
    texte = texte.replace("\xa0", " ")

    # Remplacement des retours à la ligne et tabulations
    texte = texte.replace("\n", " ")
    texte = texte.replace("\t", " ")

    # Réduction des espaces multiples
    texte = re.sub(r"\s+", " ", texte)

    # Suppression des espaces au début et à la fin
    texte = texte.strip()

    return texte


# ============================================================
# CONNEXION À LA BASE
# ============================================================

connexion = sqlite3.connect(DB_PATH)
curseur = connexion.cursor()


# ============================================================
# 1. MARQUAGE DES ARTICLES NON EXPLOITABLES
# ============================================================

# Tous les articles sont considérés exploitables par défaut
curseur.execute("""
UPDATE articles
SET is_nlp_usable = 1
""")

curseur.execute("""
UPDATE articles
SET is_nlp_usable = 0
WHERE article IS NULL
   OR TRIM(article) = ''
   OR LENGTH(TRIM(article)) < 100
""")

connexion.commit()


# ============================================================
# 2. VÉRIFICATION DU NOMBRE D'ARTICLES EXPLOITABLES
# ============================================================

curseur.execute("""
SELECT is_nlp_usable, COUNT(*)
FROM articles
GROUP BY is_nlp_usable
""")

print("\nRépartition des articles :")

for ligne in curseur.fetchall():
    print(ligne)


# ============================================================
# 3. EXEMPLES D'ARTICLES NON EXPLOITABLES
# ============================================================

curseur.execute("""
SELECT id, title, article, is_nlp_usable
FROM articles
WHERE is_nlp_usable = 0
LIMIT 20
""")

print("\nExemples d'articles non exploitables :")

for ligne in curseur.fetchall():
    print(ligne)


# ============================================================
# 4. RÉPARTITION DES ARTICLES PAR PUBLICATION
# ============================================================

curseur.execute("""
SELECT
    publication,
    COUNT(*) AS nombre_articles
FROM articles
WHERE is_nlp_usable = 1
GROUP BY publication
ORDER BY nombre_articles DESC
""")

print("\nRépartition par publication :")

for ligne in curseur.fetchall():
    print(ligne)


# ============================================================
# 5. ARTICLES CONTENANT DES TERMES LIÉS À L'ÉLECTION
# ============================================================

curseur.execute("""
SELECT
    publication,
    COUNT(*) AS nb_articles_politiques
FROM articles
WHERE is_nlp_usable = 1
  AND (
        LOWER(article) LIKE '%trump%'
     OR LOWER(article) LIKE '%clinton%'
     OR LOWER(article) LIKE '%election%'
     OR LOWER(article) LIKE '%campaign%'
     OR LOWER(article) LIKE '%republican%'
     OR LOWER(article) LIKE '%democrat%'
  )
GROUP BY publication
ORDER BY nb_articles_politiques DESC
""")

print("\nArticles contenant des termes liés à l'élection :")

for ligne in curseur.fetchall():
    print(ligne)


# ============================================================
# 6. RÉCUPÉRATION DES ARTICLES À NORMALISER
# ============================================================

curseur.execute("""
SELECT id, article
FROM articles
WHERE is_nlp_usable = 1
""")

articles = curseur.fetchall()


# ============================================================
# 7. NORMALISATION ET MISE À JOUR DE LA BDD
# ============================================================

for id_article, texte in articles:

    texte_normalise = normaliser_texte(texte)

    curseur.execute("""
    UPDATE articles
    SET article_normalise = ?
    WHERE id = ?
    """, (
        texte_normalise,
        id_article
    ))

connexion.commit()


# ============================================================
# 8. CONTRÔLE DU NOMBRE D'ARTICLES NORMALISÉS
# ============================================================

curseur.execute("""
SELECT COUNT(*)
FROM articles
WHERE is_nlp_usable = 1
  AND article_normalise IS NOT NULL
  AND TRIM(article_normalise) != ''
""")

nombre_articles_normalises = curseur.fetchone()[0]

print(
    "\nArticles normalisés :",
    nombre_articles_normalises
)

# ============================================================
# 9. CONTRÔLE VISUEL DE 5 ARTICLES NORMALISÉS
# ============================================================

curseur.execute("""
SELECT
    id,
    article_normalise
FROM articles
WHERE is_nlp_usable = 1
  AND article_normalise IS NOT NULL
LIMIT 5
""")

print("\nContrôle de 5 articles normalisés :")

for id_article, texte in curseur.fetchall():

    longueur = len(texte)

    contient_retour_ligne = "\n" in texte or "\r" in texte

    contient_espaces_multiples = bool(
        re.search(r"\s{2,}", texte)
    )

    print("\n-----------------------------------")
    print(f"ID : {id_article}")
    print(f"Longueur : {longueur} caractères")
    print(f"Retour à la ligne présent : {contient_retour_ligne}")
    print(
        f"Espaces multiples présents : "
        f"{contient_espaces_multiples}"
    )

    print("Extrait :")
    print(texte[:300])


# ============================================================
# FERMETURE DE LA CONNEXION
# ============================================================

connexion.close()