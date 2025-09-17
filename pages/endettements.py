import pandas as pd
import requests
import streamlit as st
import plotly.express as px

def fetch_commune_endettement(commune, annees):
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
            df['Dette / Habitant Commune'] = df['fdette']
            df['Dette / Habitant Moyenne'] = df['mdette']
            df['Dettes / RRF Commune'] = (df['fdette'] / df['fcaf'] * 100).round(2)
            df['Dettes / RRF Moyenne'] = (df['mdette'] / df['mcaf'] * 100).round(2)
            df['Dette en années de CAF Brute Commune'] = (df['fdette'] / df['fcaf']).round(2)
            df['Dette en années de CAF Brute Moyenne'] = (df['mdette'] / df['mcaf']).round(2)
            df['Part du remboursement de la dette / CAF Brute Commune'] = (
                ((df['fcaf'] - df['fcafn']) / df['fcaf'] * 100).round(2)
            )
            df['Part du remboursement de la dette / CAF Brute Moyenne'] = (
                ((df['mcaf'] - df['mcafn']) / df['mcaf'] * 100).round(2)
            )

            df.rename(columns={'an': 'Année'}, inplace=True)
            df_list.append(df)
    if df_list:
        df_all = pd.concat(df_list, ignore_index=True).sort_values("Année")
        return df_all
    return pd.DataFrame()


def run():
    st.title("Endettement des communes")

    commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2019, 2024)),  # ordre croissant
        default=list(range(2019, 2024))
    )

    if commune_input and annees:
        df = fetch_commune_endettement(commune_input, annees)
        if not df.empty:
            df.set_index("Année", inplace=True)

            mini_tableaux = {
                "Dette / Habitant": ["Dette / Habitant Commune", "Dette / Habitant Moyenne"],
                "Dettes / RRF": ["Dettes / RRF Commune", "Dettes / RRF Moyenne"],
                "Dette en années de CAF Brute": ["Dette en années de CAF Brute Commune", "Dette en années de CAF Brute Moyenne"],
                "Part du remboursement de la dette / CAF Brute": [
                    "Part du remboursement de la dette / CAF Brute Commune",
                    "Part du remboursement de la dette / CAF Brute Moyenne"
                ]
            }

            with st.expander("Endettement"):
                for titre, colonnes in mini_tableaux.items():
                    with st.expander(titre):
                        st.dataframe(df[colonnes].T)

                        # Graphiques Plotly
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
