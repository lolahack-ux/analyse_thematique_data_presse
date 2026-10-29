from datasets import load_dataset
import sqlite3
from pathlib import Path
import time


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_NAME = "rjac/all-the-news-2-1-Component-one"

ANNEE_CIBLE = "2016"

TAILLE_LOT = 500

DOSSIER_SCRIPT = Path(__file__).resolve().parent
DB_PATH = DOSSIER_SCRIPT / "news.db"


# ============================================================
# CONNEXION SQLITE
# ============================================================

connexion = sqlite3.connect(DB_PATH)
curseur = connexion.cursor()


# ============================================================
# CRÉATION DE LA TABLE ARTICLES
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    idx_source INTEGER,
    article_idx INTEGER UNIQUE,

    date TEXT,
    year INTEGER,
    month INTEGER,
    day INTEGER,

    author TEXT,
    title TEXT,
    article TEXT,

    url TEXT,
    section TEXT,
    publication TEXT,

    is_nlp_usable INTEGER DEFAULT 1,
    article_normalise TEXT
)
""")

# ============================================================
# VÉRIFICATION DES COLONNES NLP
# ============================================================

curseur.execute("""
PRAGMA table_info(articles)
""")

colonnes_existantes = {
    ligne[1]
    for ligne in curseur.fetchall()
}


if "is_nlp_usable" not in colonnes_existantes:

    curseur.execute("""
    ALTER TABLE articles
    ADD COLUMN is_nlp_usable INTEGER DEFAULT 1
    """)


if "article_normalise" not in colonnes_existantes:

    curseur.execute("""
    ALTER TABLE articles
    ADD COLUMN article_normalise TEXT
    """)


connexion.commit()

# ============================================================
# TABLE DE SUIVI DE L'IMPORT
# ============================================================

curseur.execute("""
CREATE TABLE IF NOT EXISTS import_progress (
    dataset_name TEXT PRIMARY KEY,
    dernier_idx INTEGER NOT NULL DEFAULT -1,
    date_mise_a_jour TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


connexion.commit()


# ============================================================
# RÉCUPÉRATION DU DERNIER IDX TRAITÉ
# ============================================================

curseur.execute(
    """
    SELECT dernier_idx
    FROM import_progress
    WHERE dataset_name = ?
    """,
    (DATASET_NAME,)
)

resultat = curseur.fetchone()

if resultat is None:
    dernier_idx = -1

    curseur.execute(
        """
        INSERT INTO import_progress (
            dataset_name,
            dernier_idx
        )
        VALUES (?, ?)
        """,
        (DATASET_NAME, dernier_idx)
    )

    connexion.commit()

else:
    dernier_idx = resultat[0]


print()
print("==============================================")
print("IMPORT ALL THE NEWS")
print("==============================================")
print(f"Base SQLite : {DB_PATH}")
print(f"Année cible : {ANNEE_CIBLE}")
print(f"Dernier idx déjà traité : {dernier_idx}")
print()


# ============================================================
# REQUÊTE D'INSERTION
# ============================================================

REQUETE_INSERTION = """
INSERT OR IGNORE INTO articles (
    idx_source,
    article_idx,
    date,
    year,
    month,
    day,
    author,
    title,
    article,
    url,
    section,
    publication
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


# ============================================================
# FONCTION DE CONVERSION DES VALEURS
# ============================================================

def convertir_entier(valeur):
    """
    Convertit proprement des valeurs telles que :
    '12.0' -> 12
    '2016' -> 2016
    None -> None
    """

    if valeur is None:
        return None

    try:
        return int(float(valeur))

    except (ValueError, TypeError):
        return None


# ============================================================
# ENREGISTREMENT D'UN LOT
# ============================================================

def enregistrer_lot(lot, dernier_idx_lot):

    try:

        connexion.execute("BEGIN")

        if lot:
            curseur.executemany(REQUETE_INSERTION, lot)

        curseur.execute(
            """
            UPDATE import_progress

            SET
                dernier_idx = ?,
                date_mise_a_jour = CURRENT_TIMESTAMP

            WHERE dataset_name = ?
            """,
            (dernier_idx_lot, DATASET_NAME)
        )

        connexion.commit()

    except Exception:
        connexion.rollback()
        raise


# ============================================================
# CHARGEMENT DU DATASET EN STREAMING
# ============================================================

print("Connexion à Hugging Face...")

dataset = load_dataset(
    DATASET_NAME,
    split="train",
    streaming=True
)

print("Streaming démarré.")
print()


# ============================================================
# IMPORT
# ============================================================

lot = []

nombre_lignes_lues = 0
nombre_articles_2016 = 0

dernier_idx_courant = dernier_idx


try:

    for ligne in dataset:

        idx_source = convertir_entier(ligne.get("idx"))

        if idx_source is None:
            continue


        # ----------------------------------------------------
        # REPRISE APRÈS INTERRUPTION
        # ----------------------------------------------------

        if idx_source <= dernier_idx:
            continue


        nombre_lignes_lues += 1
        dernier_idx_courant = idx_source


        # ----------------------------------------------------
        # FILTRE ANNÉE 2016
        # ----------------------------------------------------

        if str(ligne.get("year")) == ANNEE_CIBLE:

            article = (

                idx_source,

                convertir_entier(ligne.get("article_idx")),

                ligne.get("date"),

                convertir_entier(ligne.get("year")),

                convertir_entier(ligne.get("month")),

                convertir_entier(ligne.get("day")),

                ligne.get("author"),

                ligne.get("title"),

                ligne.get("article"),

                ligne.get("url"),

                ligne.get("section"),

                ligne.get("publication")
            )

            lot.append(article)

            nombre_articles_2016 += 1


        # ----------------------------------------------------
        # SAUVEGARDE PAR LOTS
        #
        # On utilise le nombre de lignes lues et non le nombre
        # d'articles 2016 : ainsi le checkpoint progresse même
        # lorsque les articles ne concernent pas 2016.
        # ----------------------------------------------------

        if nombre_lignes_lues % TAILLE_LOT == 0:

            enregistrer_lot(lot, dernier_idx_courant)

            lot.clear()

            print(
                f"idx : {dernier_idx_courant:,} | "
                f"lignes parcourues : {nombre_lignes_lues:,} | "
                f"articles 2016 trouvés : {nombre_articles_2016:,}"
            )


    # ========================================================
    # DERNIER LOT
    # ========================================================

    enregistrer_lot(lot, dernier_idx_courant)

    lot.clear()

    print()
    print("==============================================")
    print("IMPORT TERMINÉ")
    print("==============================================")


except KeyboardInterrupt:

    print()
    print()
    print("Interruption demandée par l'utilisateur.")

    # Sauvegarde du lot restant avant fermeture

    if dernier_idx_courant > dernier_idx:

        enregistrer_lot(lot, dernier_idx_courant)

    print(
        f"Progression sauvegardée jusqu'à idx "
        f"{dernier_idx_courant:,}"
    )

    print(
        "Tu peux relancer le script : "
        "il reprendra automatiquement."
    )


except Exception as erreur:

    print()
    print()
    print("ERREUR PENDANT LE STREAMING")
    print("----------------------------------------------")
    print(erreur)

    # Le dernier lot non enregistré n'est pas utilisé pour
    # avancer artificiellement le checkpoint.
    #
    # Tout ce qui avait déjà été validé par enregistrer_lot()
    # reste présent dans SQLite.

    print()
    print("Les lots précédemment validés sont conservés.")

    print(
        "Relance simplement le script pour reprendre "
        "à partir du dernier checkpoint."
    )


finally:

    connexion.close()

    print()
    print("Connexion SQLite fermée.")