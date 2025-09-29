import streamlit as st
import pandas as pd
import requests
import plotly.express as px

def fetch_commune_fdr(commune, annee):
    url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
    params = {"where": f"an='{annee}' AND inom='{commune}'", "limit": 100}
    response = requests.get(url, params=params)
    data = response.json()

    if "results" not in data or not data["results"]:
        return pd.DataFrame()

    df = pd.DataFrame(data["results"])

    colonnes = ['an', 'ffdr', 'mfdr', 'fcharge', 'mcharge']
    colonnes_existantes = [c for c in colonnes if c in df.columns]
    df_fr = df[colonnes_existantes].copy()

    # Renommage pour lisibilité
    df_fr.rename(columns={
        'an': 'Année',
        'ffdr': 'Fonds de roulement / hab Commune',
        'mfdr': 'Fonds de roulement / hab Moyenne',
        'fcharge': 'Charges de fonctionnement / hab Commune',
        'mcharge': 'Charges de fonctionnement / hab Moyenne'
    }, inplace=True)

    # Calcul fonds de roulement en jours de charges
    df_fr['Fonds de roulement en jours de DRF Commune'] = (
        df_fr['Fonds de roulement / hab Commune'] / df_fr['Charges de fonctionnement / hab Commune'] * 365
    ).round(2)
    df_fr['Fonds de roulement en jours de DRF Moyenne'] = (
        df_fr['Fonds de roulement / hab Moyenne'] / df_fr['Charges de fonctionnement / hab Moyenne'] * 365
    ).round(2)

    # Suppression colonnes intermédiaires
    df_fr.drop(columns=['Charges de fonctionnement / hab Commune', 'Charges de fonctionnement / hab Moyenne'], inplace=True)

    return df_fr

def run():
    st.title("🔄 Fonds de roulement des communes")

    commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2019, 2024)),  # ordre croissant
        default=list(range(2019, 2024))
    )

    df_list = []
    if commune_input and annees:
        for annee in annees:
            df_annee = fetch_commune_fdr(commune_input, annee)
            if not df_annee.empty:
                df_list.append(df_annee)

        if df_list:
            fdr = pd.concat(df_list, ignore_index=True)
            fdr.set_index("Année", inplace=True)
            fdr.sort_index(inplace=True)

            mini_tableaux = {
                "Fonds de roulement / habitant": ["Fonds de roulement / hab Commune", "Fonds de roulement / hab Moyenne"],
                "Fonds de roulement en jours de DRF": ["Fonds de roulement en jours de DRF Commune", "Fonds de roulement en jours de DRF Moyenne"]
            }

            with st.expander("Fonds de roulement"):
                for titre, colonnes in mini_tableaux.items():
                    with st.expander(titre):
                        st.dataframe(fdr[colonnes].T)

                        # Graphique Plotly
                        try:
                            df_plot = fdr[colonnes].reset_index().melt(
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
