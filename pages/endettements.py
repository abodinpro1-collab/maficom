import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import re
from functools import lru_cache
from difflib import SequenceMatcher

# Mapping des années vers les nouveaux datasets
DATASETS_MAPPING = {
    2019: "comptes-individuels-des-communes-fichier-global-2019-2020",
    2020: "comptes-individuels-des-communes-fichier-global-2019-2020",
    2021: "comptes-individuels-des-communes-fichier-global-2021",
    2022: "comptes-individuels-des-communes-fichier-global-2022",
    2023: "comptes-individuels-des-communes-fichier-global-2023-2024",
    2024: "comptes-individuels-des-communes-fichier-global-2023-2024"
}

def get_dataset_for_year(annee):
    """Retourne le dataset approprié pour une année donnée"""
    return DATASETS_MAPPING.get(annee, "comptes-individuels-des-communes-fichier-global-2023-2024")

def get_api_url_for_year(annee):
    """Retourne l'URL de l'API pour une année donnée"""
    dataset = get_dataset_for_year(annee)
    return f"https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/{dataset}/records"

class RobustCommuneFetcher:
    """Version adaptée aux nouveaux datasets"""
    
    def __init__(self):
        self._cache = {}
    
    @lru_cache(maxsize=500)
    def normalize_commune_name(self, name):
        """Normalise un nom de commune"""
        if not name:
            return ""
        
        normalized = name.strip().upper()

        # Supprimer le suffixe "commune nouvelle" présent dans les datasets 2019-2020
        # ex: "CHATEAUGIRON CNE NOUVELLE" → "CHATEAUGIRON"
        normalized = re.sub(r'\s+CNE\s+NOUVELLE\s*$', '', normalized)
        normalized = re.sub(r'\s+COMMUNE\s+NOUVELLE\s*$', '', normalized)

        patterns = [
            (r'^(LA|LE|LES)\s+(.+)$', r'\2 (\1)'),
            (r'^(.+)\s+\((LA|LE|LES)\)$', r'\2 \1'),
        ]
        
        for pattern, replacement in patterns:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        return re.sub(r'\s+', ' ', normalized).strip()
    
    def find_commune_variants(self, commune, departement=None):
        """Trouve les variantes d'une commune dans tous les datasets"""
        cache_key = f"{commune}_{departement}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        variants = []
        search_terms = self._generate_search_terms(commune)
        
        # Rechercher dans tous les datasets
        datasets_to_search = list(set(DATASETS_MAPPING.values()))
        
        for dataset in datasets_to_search:
            api_url = f"https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/{dataset}/records"
            
            for term in search_terms:
                where_clause = f'inom LIKE "%{term}%"'
                if departement:
                    where_clause += f' AND dep="{departement}"'
                where_clause += ' AND an IN ("2019","2020","2021","2022","2023","2024")'
                
                params = {"where": where_clause, "limit": 50, "select": "inom,dep"}
                
                try:
                    response = requests.get(api_url, params=params, timeout=10)
                    data = response.json()
                    
                    if "results" in data:
                        for record in data["results"]:
                            nom = record.get("inom", "")
                            dept = record.get("dep", "")
                            if nom and self._is_similar_commune(commune, nom):
                                variant = {"nom": nom, "departement": dept}
                                if variant not in variants:
                                    variants.append(variant)
                except:
                    continue
        
        if not variants:
            variants = [{"nom": commune, "departement": departement or ""}]
        
        self._cache[cache_key] = variants
        return variants
    
    def _generate_search_terms(self, commune):
        """Génère les termes de recherche"""
        terms = [commune]
        
        if commune.upper().startswith(('LA ', 'LE ', 'LES ')):
            base = commune[3:] if commune.upper().startswith('LA ') else commune[4:] if commune.upper().startswith('LES ') else commune[3:]
            terms.extend([base, f"{base} (LA)"])
        
        if '(' in commune:
            base = re.sub(r'\s*\([^)]+\)\s*', '', commune).strip()
            if '(LA)' in commune.upper():
                terms.append(f"LA {base}")
        
        return list(set(terms))
    
    def _is_similar_commune(self, search_commune, found_commune, threshold=0.8):
        """Vérifie la similarité"""
        norm1 = self.normalize_commune_name(search_commune)
        norm2 = self.normalize_commune_name(found_commune)
        return SequenceMatcher(None, norm1, norm2).ratio() >= threshold

# Instance globale cachée
@st.cache_resource
def get_fetcher():
    return RobustCommuneFetcher()

def fetch_commune_endettement(commune, annees, departement=None):
    """Version robuste adaptée aux nouveaux datasets"""
    
    fetcher = get_fetcher()
    
    # 1. Trouve les variantes
    variants = fetcher.find_commune_variants(commune, departement)
    
    if len(variants) > 1:
        variant_names = [v["nom"] for v in variants]
        st.info(f"🔍 Variantes détectées: {', '.join(set(variant_names))}")
    
    # 2. Récupère les données année par année
    df_list = []
    
    for annee in annees:
        annee_trouvee = False
        api_url = get_api_url_for_year(annee)  # URL adaptée à l'année
        
        # Essaye chaque variante pour cette année
        for variant in variants:
            commune_nom = variant["nom"]
            dept = variant["departement"] if not departement else departement
            
            where_clause = f'an="{annee}" AND inom="{commune_nom}"'
            if dept:
                where_clause += f' AND dep="{dept}"'
            
            params = {"where": where_clause, "limit": 100}
            
            try:
                r = requests.get(api_url, params=params, timeout=10)
                data = r.json().get("results", [])

                if data:
                    df = pd.DataFrame(data)
                    cols = ['an', 'fdet2cal', 'mdet2cal', 'fcaf', 'mcaf', 'fcafn', 'mcafn','fprod','mprod']
                    df_exist = [c for c in cols if c in df.columns]
                    
                    if df_exist:
                        df = df[df_exist].copy()

                        # Calculs identiques à votre version
                        df['Dette / Habitant Commune'] = df['fdet2cal']
                        df['Dette / Habitant Moyenne'] = df['mdet2cal']
                        
                        # Calculs sécurisés avec vérification de division par zéro
                        df['Dettes / RRF Commune'] = (df['fdet2cal'] / df['fprod'].replace(0, pd.NA) * 100).round(2)
                        df['Dettes / RRF Moyenne'] = (df['mdet2cal'] / df['mprod'].replace(0, pd.NA) * 100).round(2)
                        df['Dette en années de CAF Brute Commune'] = (df['fdet2cal'] / df['fcaf'].replace(0, pd.NA)).round(2)
                        df['Dette en années de CAF Brute Moyenne'] = (df['mdet2cal'] / df['mcaf'].replace(0, pd.NA)).round(2)
                        df['Part du remboursement de la dette / CAF Brute Commune'] = (
                            ((df['fcaf'] - df['fcafn']) / df['fcaf'].replace(0, pd.NA) * 100).round(2)
                        )
                        df['Part du remboursement de la dette / CAF Brute Moyenne'] = (
                            ((df['mcaf'] - df['mcafn']) / df['mcaf'].replace(0, pd.NA) * 100).round(2)
                        )

                        df.rename(columns={'an': 'Année'}, inplace=True)
                        df_list.append(df)
                        annee_trouvee = True
                        break  # Année trouvée avec cette variante, passe à l'année suivante
                        
            except requests.RequestException:
                continue
        
        # Debug pour voir ce qui se passe
        if not annee_trouvee:
            st.warning(f"⚠️ Année {annee} non trouvée pour {commune}")
    
    # 3. Combine les résultats
    if df_list:
        df_all = pd.concat(df_list, ignore_index=True)
        df_all = df_all.drop_duplicates(subset=['Année'], keep='first')
        df_all = df_all.sort_values("Année")
        
        st.success(f"✅ Données endettement récupérées: {len(df_all)} lignes sur {len(annees)} années demandées")
        
        # Debug : affiche les années trouvées
        annees_trouvees = sorted(df_all['Année'].unique())
        st.write(f"🔍 **DEBUG**: Années récupérées: {annees_trouvees}")
        
        return df_all
        
    st.warning(f"❌ Aucune donnée d'endettement trouvée pour '{commune}'")
    return pd.DataFrame()

def run(commune=None, annees=None, departement=None):
    """Votre fonction run - CODE ORIGINAL + fetch robuste mis à jour"""
    st.title("📉 Endettement des communes")

    commune_selectionnee = st.text_input("Nom de la commune :", value=commune or "RENAGE")
    departement_selectionne = st.text_input('Département (optionnel) :', value=departement or "")
    
    # Années étendues pour inclure 2024
    annees_disponibles = list(range(2024, 2018, -1))
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=annees_disponibles,
        default=annees or annees_disponibles
    )

    if commune_selectionnee and annees:
        # ✅ VERSION ROBUSTE ADAPTÉE AUX NOUVEAUX DATASETS
        df = fetch_commune_endettement(commune_selectionnee, annees, departement_selectionne)
        
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

                        # Graphiques Plotly (identiques à votre version)
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

if __name__ == "__main__":
    run()