import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# -----------------------
# Fonctions de récupération des données (reprises de vos modules)
# -----------------------

def fetch_commune_fonctionnement(commune, annees):
    """Récupère les données de fonctionnement"""
    df_list = []
    for annee in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f'an="{annee}" AND inom="{commune}"', "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()
        
        if "results" not in data or not data["results"]:
            continue
        
        df = pd.DataFrame(data["results"])
        colonnes_voulu = ['an', 'pop1', 'prod', 'charge', 'fprod', 'mprod',
                          'fcharge', 'mcharge', 'fdgf', 'mdgf', 'fperso', 'mperso']
        colonnes_existantes = [c for c in colonnes_voulu if c in df.columns]
        df_fonctionnement = df[colonnes_existantes].copy()

        # Renommer colonnes
        df_fonctionnement.rename(columns={
            "an": "Année",
            "pop1": "Population",
            "prod": "Recettes de fonctionnement",
            "charge": "Dépenses de fonctionnement",
            "fprod": "Recettes réelles fonctionnement / hab",
            "mprod": "Moyenne strate Recettes / hab",
            "fcharge": "Dépenses réelles fonctionnement / hab",
            "mcharge": "Moyenne strate Dépenses / hab",
            "fdgf": "DGF / habitant",
            "mdgf": "Moyenne strate DGF / hab",
            "fperso": "Dépenses personnel / hab",
            "mperso": "Moyenne strate Personnel / hab"
        }, inplace=True)
        
        # Ratios
        df_fonctionnement["Ratio Personnel/DRF Commune"] = (
            df_fonctionnement["Dépenses personnel / hab"] /
            df_fonctionnement["Dépenses réelles fonctionnement / hab"] * 100
        ).round(2)
        
        df_fonctionnement["Ratio Personnel/DRF Moyenne"] = (
            df_fonctionnement["Moyenne strate Personnel / hab"] /
            df_fonctionnement["Moyenne strate Dépenses / hab"] * 100
        ).round(2)
        
        df_list.append(df_fonctionnement)
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

def fetch_commune_caf(commune, annees):
    """Récupère les données CAF"""
    url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
    dfs = []

    for annee in annees:
        params = {"where": f'an="{annee}" AND inom="{commune}"', "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()

        if "results" not in data or not data["results"]:
            continue

        df = pd.DataFrame(data["results"])
        colonnes_calc = ['an', 'pop1', 'fcaf', 'mcaf', 'fprod', 'mprod', 'fcafn', 'mcafn']
        colonnes_existantes = [c for c in colonnes_calc if c in df.columns]
        df_caf = df[colonnes_existantes].copy()

        # Calcul des ratios
        df_caf['CAF brute / RRF Commune'] = df_caf.apply(
            lambda row: (row['fcaf']/row['fprod'])*100 if row['fprod'] != 0 else None, axis=1)
        df_caf['CAF brute / RRF Moyenne'] = df_caf.apply(
            lambda row: (row['mcaf']/row['mprod'])*100 if row['mprod'] != 0 else None, axis=1)
        df_caf['CAF nette / RRF Commune'] = df_caf.apply(
            lambda row: (row['fcafn']/row['fprod'])*100 if row['fprod'] != 0 else None, axis=1)
        df_caf['CAF nette / RRF Moyenne'] = df_caf.apply(
            lambda row: (row['mcafn']/row['mprod'])*100 if row['mprod'] != 0 else None, axis=1)

        # Sélection finale et renommage
        df_caf_final = df_caf[['an', 'pop1', 'fcaf', 'mcaf',
                                'CAF brute / RRF Commune', 'CAF brute / RRF Moyenne',
                                'CAF nette / RRF Commune', 'CAF nette / RRF Moyenne']].copy()
        df_caf_final.rename(columns={
            'an': 'Année',
            'pop1': 'Population',
            'fcaf': 'CAF brute / hab Commune',
            'mcaf': 'CAF brute / hab Moyenne'
        }, inplace=True)

        dfs.append(df_caf_final)

    if dfs:
        result = pd.concat(dfs, ignore_index=True)
        result.sort_values("Année", inplace=True)
        return result
    else:
        return pd.DataFrame()

def fetch_commune_fiscalite(commune, annees):
    """Récupère les données de fiscalité"""
    df_list = []
    for annee in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f'an=\"{annee}\" AND inom=\"{commune}\"', "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()

        if "results" not in data or not data["results"]:
            continue

        df = pd.DataFrame(data["results"])
        colonnes = ['an', 'fimpo1', 'mimpo1', 'fprod', 'mprod', 'tth', 'tmth', 'tfb', 'tmfb', 'tfnb', 'tmfnb']
        colonnes_existantes = [c for c in colonnes if c in df.columns]
        df_fiscalite = df[colonnes_existantes].copy()

        # Calcul des ratios Impôts locaux sur RRF
        if 'fimpo1' in df_fiscalite.columns and 'fprod' in df_fiscalite.columns:
            df_fiscalite['Impôts/RRF Commune'] = (df_fiscalite['fimpo1'] / df_fiscalite['fprod'] * 100).round(2)
        if 'mimpo1' in df_fiscalite.columns and 'mprod' in df_fiscalite.columns:
            df_fiscalite['Impôts/RRF Moyenne'] = (df_fiscalite['mimpo1'] / df_fiscalite['mprod'] * 100).round(2)

        # Renommer colonnes pour affichage
        rename_dict = {
            'an': 'Année',
            'fimpo1': 'Impôts / hab Commune',
            'mimpo1': 'Impôts / hab Moyenne',
            'tth': 'Taux TH Commune',
            'tmth': 'Taux TH Moyenne',
            'tfb': 'Taux TFB Commune',
            'tmfb': 'Taux TFB Moyenne',
            'tfnb': 'Taux TFNB Commune',
            'tmfnb': 'Taux TFNB Moyenne'
        }
        df_fiscalite.rename(columns=rename_dict, inplace=True)
        df_list.append(df_fiscalite)
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

def fetch_commune_endettement(commune, annees):
    """Récupère les données d'endettement"""
    df_list = []
    for an in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f'an="{an}" AND inom="{commune}"', "limit": 100}
        r = requests.get(url, params=params)
        data = r.json().get("results", [])
        if data:
            df = pd.DataFrame(data)
            cols = ['an', 'fdette', 'mdette', 'fcaf', 'mcaf', 'fcafn', 'mcafn']
            df_exist = [c for c in cols if c in df.columns]
            df = df[df_exist].copy()

            # Mini-tableaux
            df['Dette / hab Commune'] = df['fdette']
            df['Dette / hab Moyenne'] = df['mdette']
            df['Dette / RRF Commune'] = (df['fdette'] / df['fcaf'] * 100).round(2)
            df['Dette / RRF Moyenne'] = (df['mdette'] / df['mcaf'] * 100).round(2)
            df['Dette en années CAF Commune'] = (df['fdette'] / df['fcaf']).round(2)
            df['Dette en années CAF Moyenne'] = (df['mdette'] / df['mcaf']).round(2)

            df.rename(columns={'an': 'Année'}, inplace=True)
            df_list.append(df)
    if df_list:
        return pd.concat(df_list, ignore_index=True).sort_values("Année")
    return pd.DataFrame()

def fetch_commune_investissement(commune, annees):
    """Récupère les données d'investissement"""
    df_list = []
    for an in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f'an="{an}" AND inom="{commune}"', "limit": 100}
        r = requests.get(url, params=params)
        data = r.json().get("results", [])
        if data:
            df = pd.DataFrame(data)
            cols = ['an', 'fequip', 'mequip', 'fprod', 'mprod']
            df_exist = [c for c in cols if c in df.columns]
            df = df[df_exist].copy()

            # Mini-tableaux
            df['Équipement / hab Commune'] = df['fequip']
            df['Équipement / hab Moyenne'] = df['mequip']
            df['Équipement / RRF Commune'] = (df['fequip'] / df['fprod'] * 100).round(2)
            df['Équipement / RRF Moyenne'] = (df['mequip'] / df['mprod'] * 100).round(2)

            df.rename(columns={'an': 'Année'}, inplace=True)
            df_list.append(df)
    if df_list:
        return pd.concat(df_list, ignore_index=True).sort_values("Année")
    return pd.DataFrame()

def fetch_commune_fdr(commune, annees):
    """Récupère les données de fonds de roulement"""
    df_list = []
    for annee in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f"an='{annee}' AND inom='{commune}'", "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()

        if "results" not in data or not data["results"]:
            continue

        df = pd.DataFrame(data["results"])
        colonnes = ['an', 'ffdr', 'mfdr', 'fcharge', 'mcharge']
        colonnes_existantes = [c for c in colonnes if c in df.columns]
        df_fr = df[colonnes_existantes].copy()

        # Renommage pour lisibilité
        df_fr.rename(columns={
            'an': 'Année',
            'ffdr': 'FDR / hab Commune',
            'mfdr': 'FDR / hab Moyenne',
            'fcharge': 'Charges fonct / hab Commune',
            'mcharge': 'Charges fonct / hab Moyenne'
        }, inplace=True)

        # Calcul fonds de roulement en jours de charges
        df_fr['FDR en jours DRF Commune'] = (
            df_fr['FDR / hab Commune'] / df_fr['Charges fonct / hab Commune'] * 365
        ).round(2)
        df_fr['FDR en jours DRF Moyenne'] = (
            df_fr['FDR / hab Moyenne'] / df_fr['Charges fonct / hab Moyenne'] * 365
        ).round(2)

        # Suppression colonnes intermédiaires
        df_fr.drop(columns=['Charges fonct / hab Commune', 'Charges fonct / hab Moyenne'], inplace=True)
        df_list.append(df_fr)
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def get_all_commune_data(commune, annees):
    """Récupère toutes les données financières pour une commune"""
    data = {}
    data['fonctionnement'] = fetch_commune_fonctionnement(commune, annees)
    data['caf'] = fetch_commune_caf(commune, annees)
    data['fiscalite'] = fetch_commune_fiscalite(commune, annees)
    data['endettement'] = fetch_commune_endettement(commune, annees)
    data['investissement'] = fetch_commune_investissement(commune, annees)
    data['fdr'] = fetch_commune_fdr(commune, annees)
    return data

def create_excel_report(commune, annees):
    """Crée un fichier Excel complet avec tous les indicateurs financiers"""
    
    # Récupération de toutes les données
    with st.spinner("📊 Récupération des données financières..."):
        all_data = get_all_commune_data(commune, annees)
    
    # Création du fichier Excel en mémoire avec BytesIO (solution alternative)
    from io import BytesIO
    
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        
        # Page de synthèse
        if not all_data['fonctionnement'].empty:
            # Création d'un tableau de synthèse
            synthese = all_data['fonctionnement'][['Année', 'Population']].copy()
            
            # Ajout des indicateurs clés de chaque module
            if not all_data['caf'].empty:
                synthese = synthese.merge(
                    all_data['caf'][['Année', 'CAF brute / hab Commune', 'CAF brute / RRF Commune']], 
                    on='Année', how='left'
                )
            
            if not all_data['fiscalite'].empty:
                synthese = synthese.merge(
                    all_data['fiscalite'][['Année', 'Impôts / hab Commune']], 
                    on='Année', how='left'
                )
            
            if not all_data['endettement'].empty:
                synthese = synthese.merge(
                    all_data['endettement'][['Année', 'Dette / hab Commune', 'Dette en années CAF Commune']], 
                    on='Année', how='left'
                )
            
            synthese.to_excel(writer, sheet_name='Synthèse', index=False)
        
        # Écriture des données par module
        if not all_data['fonctionnement'].empty:
            all_data['fonctionnement'].to_excel(writer, sheet_name='Fonctionnement', index=False)
        
        if not all_data['caf'].empty:
            all_data['caf'].to_excel(writer, sheet_name='CAF', index=False)
        
        if not all_data['fiscalite'].empty:
            all_data['fiscalite'].to_excel(writer, sheet_name='Fiscalité', index=False)
        
        if not all_data['endettement'].empty:
            all_data['endettement'].to_excel(writer, sheet_name='Endettement', index=False)
        
        if not all_data['investissement'].empty:
            all_data['investissement'].to_excel(writer, sheet_name='Investissement', index=False)
        
        if not all_data['fdr'].empty:
            all_data['fdr'].to_excel(writer, sheet_name='Fonds de roulement', index=False)
    
    # Récupération des données depuis le buffer
    excel_buffer.seek(0)
    excel_data = excel_buffer.getvalue()
    
    return excel_data

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
    st.title("Bienvenue sur **Focus Financier**")
    st.markdown("""
    **Focus Financier** est un outil d'analyse des comptes des communes françaises, offrant :
    - Consultation des données financières : fonctionnement, CAF, fiscalité, endettement, investissements, fonds de roulement
    - Comparaison avec la moyenne de la strate
    - Graphiques interactifs pour visualiser l'évolution dans le temps
    - **Export Excel complet de toutes les données**
    """)

    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    with col2:
        annees = st.multiselect(
            "Sélectionnez les années à afficher :",
            options=list(range(2019, 2024)),
            default=list(range(2019, 2024))
        )
    
    # Section Export Excel
    st.markdown("---")
    st.markdown("### 📊 Export Excel complet")
    
    if commune_input and annees:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🔄 Générer le rapport Excel", type="primary", use_container_width=True):
                try:
                    excel_data = create_excel_report(commune_input, annees)
                    
                    filename = f"Focus_Financier_{commune_input}_{min(annees)}-{max(annees)}.xlsx"
                    
                    st.download_button(
                        label="📥 Télécharger le rapport Excel",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="secondary",
                        use_container_width=True
                    )
                    
                    st.success("✅ Rapport Excel généré avec succès !")
                    st.info(f"📋 Le fichier contient les onglets : Synthèse, Fonctionnement, CAF, Fiscalité, Endettement, Investissement, Fonds de roulement")
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de la génération du rapport : {str(e)}")
                    st.error("💡 Vérifiez que le nom de la commune est correct et que des données sont disponibles.")
        
        # Alternative : Export CSV simple
        st.markdown("---")
        st.markdown("### 📄 Export CSV (Alternative)")
        
        col1_csv, col2_csv = st.columns(2)
        
        with col1_csv:
            if st.button("📊 Export données principales (CSV)", use_container_width=True):
                try:
                    all_data = get_all_commune_data(commune_input, annees)
                    if not all_data['fonctionnement'].empty:
                        csv_data = all_data['fonctionnement'].to_csv(index=False)
                        filename_csv = f"Focus_Financier_{commune_input}_fonctionnement.csv"
                        
                        st.download_button(
                            label="📥 Télécharger le CSV",
                            data=csv_data,
                            file_name=filename_csv,
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning("Aucune donnée de fonctionnement disponible.")
                except Exception as e:
                    st.error(f"Erreur : {str(e)}")
        
        with col2_csv:
            st.info("💡 **Export CSV** : Plus simple et compatible avec tous les tableurs. Contient les données principales de fonctionnement.")
    else:
        st.info("👆 Veuillez sélectionner une commune et des années pour générer le rapport Excel")
    
    # Informations sur le contenu du rapport
    st.markdown("---")
    st.markdown("### 📋 Contenu du rapport Excel")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📈 Onglet Synthèse :**
        - Population
        - CAF brute par habitant
        - CAF brute / RRF
        - Impôts locaux par habitant
        - Dette par habitant
        - Dette en années de CAF
        """)
        
        st.markdown("""
        **💰 Onglet Fonctionnement :**
        - Recettes et dépenses
        - Dotation globale de fonctionnement
        - Dépenses de personnel
        - Ratios avec moyennes de strate
        """)
        
        st.markdown("""
        **🧾 Onglet CAF :**
        - CAF brute et nette par habitant
        - Ratios CAF / RRF
        - Comparaisons avec moyennes
        """)
    
    with col2:
        st.markdown("""
        **🏦 Onglet Fiscalité :**
        - Impôts locaux par habitant
        - Taux d'imposition (TH, TFB, TFNB)
        - Ratios fiscaux
        """)
        
        st.markdown("""
        **📉 Onglet Endettement :**
        - Dette par habitant
        - Capacité de désendettement
        - Ratios d'endettement
        """)
        
        st.markdown("""
        **🏗️ Onglets Investissement & FDR :**
        - Dépenses d'équipement
        - Fonds de roulement
        - Ratios d'investissement
        """)

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