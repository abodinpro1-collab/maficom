import streamlit as st
import pandas as pd
import requests
import plotly.express as px

def fetch_commune_fonctionnement(commune, annee):
    url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
    params = {"where": f'an="{annee}" AND inom="{commune}"', "limit": 100}
    response = requests.get(url, params=params)
    data = response.json()
    
    if "results" not in data or not data["results"]:
        return pd.DataFrame()
    
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
        "fprod": "Recettes réelles de fonctionnement / habitant",
        "mprod": "Moyenne de la strate Recettes réelles fonctionnement / habitant",
        "fcharge": "Dépenses réelles de fonctionnement / habitant",
        "mcharge": "Moyenne de la strate Dépenses réelles fonctionnement / habitant",
        "fdgf": "Dotation Globale de Fonctionnement / habitant",
        "mdgf": "Moyenne de la strate Dotation Globale de fonctionnement / habitant",
        "fperso": "Dépenses de personnel / habitant",
        "mperso": "Moyenne de la strate Dépenses de personnel / habitant"
    }, inplace=True)
    
    # Ratios
    df_fonctionnement["Ratio Dépenses personnel / Dépenses fonctionnement"] = (
        df_fonctionnement["Dépenses de personnel / habitant"] /
        df_fonctionnement["Dépenses réelles de fonctionnement / habitant"] * 100
    ).round(2)
    
    df_fonctionnement["Ratio Moyenne Dépenses personnel / Dépenses fonctionnement"] = (
        df_fonctionnement["Moyenne de la strate Dépenses de personnel / habitant"] /
        df_fonctionnement["Moyenne de la strate Dépenses réelles fonctionnement / habitant"] * 100
    ).round(2)
    
    return df_fonctionnement


def run():
    st.title("Fonctionnement des communes")

    commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2023, 2018, -1)),
        default=list(range(2023, 2018, -1))
    )

    df_list = []
    if commune_input and annees:
        for annee in annees:
            df_annee = fetch_commune_fonctionnement(commune_input, annee)
            if not df_annee.empty:
                df_list.append(df_annee)

        if df_list:
            fonctionnement = pd.concat(df_list, ignore_index=True)
            fonctionnement.set_index("Année", inplace=True)

            mini_tableaux = {
                "Population": ["Population"],
                "Recettes et Dépenses": ["Recettes de fonctionnement", "Dépenses de fonctionnement"],
                "RRF / habitant": ["Recettes réelles de fonctionnement / habitant",
                                   "Moyenne de la strate Recettes réelles fonctionnement / habitant"],
                "DRF / habitant": ["Dépenses réelles de fonctionnement / habitant",
                                   "Moyenne de la strate Dépenses réelles fonctionnement / habitant"],
                "Dotation Globale de Fonctionnement": ["Dotation Globale de Fonctionnement / habitant",
                             "Moyenne de la strate Dotation Globale de fonctionnement / habitant"],
                "Dépenses de personnel / habitant": ["Dépenses de personnel / habitant",
                                       "Moyenne de la strate Dépenses de personnel / habitant",],
                "Dépenses de personnel / DRF" :["Ratio Dépenses personnel / Dépenses fonctionnement",
                                       "Ratio Moyenne Dépenses personnel / Dépenses fonctionnement"]
            }

            with st.expander("Fonctionnement"):
                for titre, colonnes in mini_tableaux.items():
                    with st.expander(titre):
                        # Tableau
                        st.dataframe(fonctionnement[colonnes].T)

                        # Graphique avec Plotly
                        try:
                            df_plot = (
                                fonctionnement[colonnes]
                                .reset_index()
                                .sort_values("Année")  # trie croissant
                                .melt(id_vars="Année", var_name="Indicateur", value_name="Valeur")
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
                            fig.update_layout(
                                xaxis_title="Année",
                                yaxis_title="Valeur",
                                template="plotly_white",
                                hovermode="x unified"
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Impossible d'afficher le graphique pour {titre} ({e})")
        else:
            st.warning("Aucune donnée disponible pour cette commune et ces années.")
