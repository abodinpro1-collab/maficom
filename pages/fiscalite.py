import streamlit as st
import pandas as pd
import requests
import plotly.express as px

def fetch_commune_fiscalite(commune, annee):
    url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
    params = {"where": f'an=\"{annee}\" AND inom=\"{commune}\"', "limit": 100}
    response = requests.get(url, params=params)
    data = response.json()

    if "results" not in data or not data["results"]:
        return pd.DataFrame()

    df = pd.DataFrame(data["results"])
    colonnes = ['an', 'fimpo1', 'mimpo1', 'fprod', 'mprod', 'tth', 'tmth', 'tfb', 'tmfb', 'tfnb', 'tmfnb']
    colonnes_existantes = [c for c in colonnes if c in df.columns]
    df_fiscalite = df[colonnes_existantes].copy()

    # Calcul des ratios Impôts locaux sur RRF
    if 'fimpo1' in df_fiscalite.columns and 'fprod' in df_fiscalite.columns:
        df_fiscalite['Commune'] = (df_fiscalite['fimpo1'] / df_fiscalite['fprod'] * 100).round(2)
    if 'mimpo1' in df_fiscalite.columns and 'mprod' in df_fiscalite.columns:
        df_fiscalite['Moyenne de la strate'] = (df_fiscalite['mimpo1'] / df_fiscalite['mprod'] * 100).round(2)

    # Renommer colonnes pour affichage
    rename_dict = {
        'an': 'Année',
        'fimpo1': 'Impôts / Commune',
        'mimpo1': 'Impôts / Moyenne',
        'tth': 'Taxe habitation / Commune',
        'tmth': 'Taxe habitation / Moyenne',
        'tfb': 'TFB / Commune',
        'tmfb': 'TFB / Moyenne',
        'tfnb': 'TFNB / Commune',
        'tmfnb': 'TFNB / Moyenne'
    }
    df_fiscalite.rename(columns=rename_dict, inplace=True)

    return df_fiscalite

def run():
    st.title("🏦 Fiscalité des communes")

    commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2019, 2024)),  # ordre croissant
        default=list(range(2019, 2024))
    )

    df_list = []
    if commune_input and annees:
        for annee in annees:
            df_annee = fetch_commune_fiscalite(commune_input, annee)
            if not df_annee.empty:
                df_list.append(df_annee)

        if df_list:
            fiscalite = pd.concat(df_list, ignore_index=True)
            fiscalite.set_index("Année", inplace=True)
            fiscalite.sort_index(inplace=True)

            mini_tableaux = {
                "Impôts locaux par habitant": ["Impôts / Commune", "Impôts / Moyenne"],
                "Impôts locaux sur RRF": ["Commune", "Moyenne de la strate"],
                "Taux taxe d'habitation": ["Taxe habitation / Commune", "Taxe habitation / Moyenne"],
                "Taux taxe foncier bâti": ["TFB / Commune", "TFB / Moyenne"],
                "Taux taxe foncier non bâti": ["TFNB / Commune", "TFNB / Moyenne"]
            }

            with st.expander("Fiscalité"):
                for titre, colonnes in mini_tableaux.items():
                    with st.expander(titre):
                        st.dataframe(fiscalite[colonnes].T)

                        # 🔹 Graphique Plotly
                        try:
                            df_plot = fiscalite[colonnes].reset_index().melt(
                                id_vars="Année", var_name="Indicateur", value_name="Valeur"
                            )
                            fig = px.line(
                                df_plot,
                                x="Année",
                                y="Valeur",
                                color="Indicateur",
                                markers=True,
                                title=f"Évolution - {titre}"
                            )
                            fig.update_traces(mode="lines+markers", line=dict(width=2), marker=dict(size=6))
                            fig.update_layout(template="plotly_white", hovermode="x unified")
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Impossible d'afficher le graphique pour {titre} ({e})")
        else:
            st.warning("Aucune donnée disponible pour cette commune et ces années.")