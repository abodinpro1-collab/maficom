import streamlit as st
import pandas as pd
from io import BytesIO

# -----------------------
# Sidebar navigation
# -----------------------
st.sidebar.title("⛵ Navigation")

# Mapping emojis → nom interne
page_labels = {
    "🏠 Accueil": "Accueil",
    "💰 Fonctionnement": "Fonctionnement",
    "🧾 CAF": "CAF",
    "🏦 Fiscalité": "Fiscalité",
    "📉 Endettement": "Endettement",
    "🏗️ Investissement": "Investissement",
    "🔄 Fonds de roulement": "Fonds de roulement"
}

page_emoji = st.sidebar.radio("Choisissez la page :", list(page_labels.keys()))
page = page_labels[page_emoji]

# -----------------------
# Import des pages
# -----------------------
import pages.fonctionnement as fonctionnement
import pages.caf as caf
import pages.fiscalite as fiscalite
import pages.endettements as endettements
import pages.investissements as investissements
import pages.fdr as fdr

page_modules = {
    "Fonctionnement": fonctionnement,
    "CAF": caf,
    "Fiscalité": fiscalite,
    "Endettement": endettements,
    "Investissement": investissements,
    "Fonds de roulement": fdr
}

# -----------------------
# Page Accueil
# -----------------------
if page == "Accueil":
    st.title("Bienvenue sur MafiCom")
    st.markdown("""
    **MafiCom** est un outil d'analyse des comptes des communes françaises, offrant :

    - Consultation des données financières : fonctionnement, CAF, fiscalité, endettement, investissements, fonds de roulement
    - Comparaison avec la moyenne de la strate
    - Graphiques interactifs pour visualiser l'évolution dans le temps
    """)

    # Filtres côte à côte
    col1, col2 = st.columns(2)
    with col1:
        commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    with col2:
        annees = st.multiselect(
            "Sélectionnez les années à afficher :",
            options=list(range(2019, 2024)),
            default=list(range(2019, 2024))
        )

else:
    module = page_modules.get(page)
    if module and hasattr(module, "run"):
        module.run()
    else:
        st.warning(f"La page {page} n'a pas de fonction run() définie.")
