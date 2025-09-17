import streamlit as st
import pandas as pd
import requests
import plotly.express as px

table_caf = pd.DataFrame()

def fetch_commune_caf(commune, annees):
    """
    Récupère les données CAF pour une commune sur une liste d'années.
    Renvoie un DataFrame prêt à l'affichage ou l'export.
    """
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
            'fcaf': 'CAF brute / habitant Commune',
            'mcaf': 'CAF brute / habitant Moyenne'
        }, inplace=True)

        dfs.append(df_caf_final)

    if dfs:
        result = pd.concat(dfs, ignore_index=True)
        result.sort_values("Année", inplace=True)
        return result
    else:
        return pd.DataFrame()


def run():
    global table_caf  # <- important pour que la variable soit accessible à l'extérieur
    st.title("🧾 CAF des communes")

    commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2019, 2024)),
        default=list(range(2019, 2024))
    )

    if commune_input and annees:
        caf = fetch_commune_caf(commune_input, annees)
        if caf.empty:
            st.warning("Aucune donnée disponible pour cette commune et ces années.")
            table_caf = pd.DataFrame()  # reset pour l'export
            return

        table_caf = caf.copy()  # <- on stocke le DataFrame global pour l'export

        mini_tableaux = {
            "CAF brute / habitant": ["CAF brute / habitant Commune", "CAF brute / habitant Moyenne"],
            "CAF brute / RRF": ["CAF brute / RRF Commune", "CAF brute / RRF Moyenne"],
            "CAF nette / RRF": ["CAF nette / RRF Commune", "CAF nette / RRF Moyenne"]
        }

        with st.expander("CAF"):
            for titre, colonnes in mini_tableaux.items():
                with st.expander(titre):
                    st.dataframe(caf.set_index('Année')[colonnes].T)

                    try:
                        df_plot = caf[colonnes].copy()
                        df_plot['Année'] = caf['Année']
                        df_plot = df_plot.melt(id_vars="Année", var_name="Indicateur", value_name="Valeur")

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