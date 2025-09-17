import pandas as pd
import requests
import streamlit as st
import plotly.express as px

def fetch_commune_investissement(commune, annees):
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
            df['Dépenses d\'équipement / habitant Commune'] = df['fequip']
            df['Dépenses d\'équipement / habitant Moyenne'] = df['mequip']
            df['Dépenses d\'équipement / RRF Commune'] = (df['fequip'] / df['fprod'] * 100).round(2)
            df['Dépenses d\'équipement / RRF Moyenne'] = (df['mequip'] / df['mprod'] * 100).round(2)

            df.rename(columns={'an': 'Année'}, inplace=True)
            df_list.append(df)
    if df_list:
        return pd.concat(df_list, ignore_index=True).sort_values("Année")
    return pd.DataFrame()


def run():
    st.title("Investissements des communes")

    commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2019, 2024)),  # ordre croissant
        default=list(range(2019, 2024))
    )

    if commune_input and annees:
        df = fetch_commune_investissement(commune_input, annees)
        if not df.empty:
            df.set_index("Année", inplace=True)

            mini_tableaux = {
                "Dépenses d'équipement / habitant": [
                    "Dépenses d'équipement / habitant Commune",
                    "Dépenses d'équipement / habitant Moyenne"
                ],
                "Dépenses d'équipement / RRF": [
                    "Dépenses d'équipement / RRF Commune",
                    "Dépenses d'équipement / RRF Moyenne"
                ]
            }

            with st.expander("Investissements"):
                for titre, colonnes in mini_tableaux.items():
                    with st.expander(titre):
                        st.dataframe(df[colonnes].T)

                        # Graphique Plotly
                        try:
                            df_plot = df[colonnes].reset_index().melt(
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
