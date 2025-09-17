import streamlit as st

# -----------------------
# Sidebar navigation
# -----------------------
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choisissez la page :", [
    "Accueil",
    "Fonctionnement",
    "CAF",
    "Fiscalité",
    "Endettement",
    "Investissement",
    "Fonds de roulement"
])

# -----------------------
# Page Accueil
# -----------------------
if page == "Accueil":
    st.title("Bienvenue sur **MafiCom**")
    st.markdown("""""**MafiCom** est un outil d'analyse des comptes des communes françaises, offrant :
                - Consultation des données financières : fonctionnement, CAF, fiscalité, endettement, investissements, fonds de roulement
                - Comparaison avec la moyenne de la strate
                - Graphiques interactifs pour visualiser l'évolution dans le temps
    """)

    commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2019, 2024)),
        default=list(range(2019, 2024))
    )

# -----------------------
# Import dynamique des pages
# -----------------------
else:
    if page == "Fonctionnement":
        from pages.fonctionnement import run
    elif page == "CAF":
        from pages.caf import run
    elif page == "Fiscalité":
        from pages.fiscalite import run
    elif page == "Endettement":
        from pages.endettements import run
    elif page == "Investissement":
        from pages.investissements import run
    elif page == "Fonds de roulement":
        from pages.fdr import run

    # Exécution de la page sélectionnée
    run()
