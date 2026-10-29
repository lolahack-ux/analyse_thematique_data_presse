import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# 1. CONFIGURATION
# ============================================================

DOSSIER_FRONT = Path(__file__).resolve().parent
DOSSIER_PROJET = DOSSIER_FRONT.parent
DOSSIER_BACK = DOSSIER_PROJET / "back"
DB_PATH = (DOSSIER_BACK / "data" / "news.db")

st.set_page_config(
    page_title="Analyse thématique de la presse",
    page_icon="📰",
    layout="wide"
)

# ============================================================
# 2. CHARGEMENT DES DONNÉES
# ============================================================

@st.cache_data
def charger_indicateurs():

    connexion = sqlite3.connect(DB_PATH)

    df = pd.read_sql_query(
        """
        SELECT *
        FROM indicateurs_hebdomadaires
        ORDER BY semaine
        """,
        connexion
    )

    connexion.close()

    return df


@st.cache_data
def charger_statistiques_articles():

    connexion = sqlite3.connect(DB_PATH)

    total_articles = pd.read_sql_query(
        """
        SELECT COUNT(*) AS total
        FROM articles
        """,
        connexion
    ).iloc[0]["total"]

    articles_exploitables = pd.read_sql_query(
        """
        SELECT COUNT(*) AS total
        FROM articles
        WHERE is_nlp_usable = 1
        """,
        connexion
    ).iloc[0]["total"]

    connexion.close()

    return (total_articles, articles_exploitables)


# ============================================================
# 3. CHARGEMENT
# ============================================================

df = charger_indicateurs()
(total_articles, articles_exploitables) = charger_statistiques_articles()

# ============================================================
# 4. TITRE
# ============================================================

st.title("📰 Analyse des évolutions thématiques de la presse")

st.write(
    """
    Cette application présente une expérimentation de détection
    de périodes thématiquement atypiques dans un corpus de presse
    américain publié en 2016.

    L'objectif est de mettre en évidence des évolutions
    inhabituelles pouvant servir de points d'attention pour
    une analyse humaine.
    """
)

st.divider()

# ============================================================
# 5. INDICATEURS PRINCIPAUX
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Articles collectés",
        f"{total_articles:,}".replace(",", " ")
    )

with col2:
    st.metric(
        "Articles exploitables",
        f"{articles_exploitables:,}".replace(",", " ")
    )

with col3:
    st.metric(
        "Semaines analysées",
        len(df)
    )

st.divider()


# ============================================================
# 6. ÉVOLUTION DES THÈMES
# ============================================================

st.header("Évolution hebdomadaire des thèmes")


THEMES = {

    "Politique électorale":
        "politique_electorale_proportion",

    "Institutions et gouvernement":
        "institutions_gouvernement_proportion",

    "Relations internationales et sécurité":
        "relations_internationales_securite_proportion",

    "Droits et société":
        "droits_societe_proportion",

    "Économie":
        "economie_proportion",

    "Santé et environnement":
        "sante_environnement_proportion",

    "Technologie et médias":
        "technologie_medias_proportion",

    "Territoires":
        "territoires_proportion"
}


theme_selectionne = st.selectbox("Choisir un thème",options=list(THEMES.keys()))
colonne_theme = THEMES[theme_selectionne]


# ============================================================
# 7. GRAPHIQUE
# ============================================================

df_graphique = df[["semaine",colonne_theme]].copy()
df_graphique = df_graphique.set_index("semaine")
st.line_chart(df_graphique)


# ============================================================
# 8. TABLEAU DES DONNÉES
# ============================================================

with st.expander("Voir les données utilisées"):

    st.dataframe(
        df[["semaine",colonne_theme]],
        use_container_width=True
    )