import streamlit as st
import pandas as pd
import requests
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

def fetch_commune_fiscalite(commune, annee, departement=None):
    """Version robuste adaptée aux nouveaux datasets"""
    
    fetcher = get_fetcher()
    api_url = get_api_url_for_year(annee)  # URL adaptée à l'année
    
    # 1. Trouve les variantes (une seule fois pour toutes les années)
    variants = fetcher.find_commune_variants(commune, departement)
    
    # 2. Essaye chaque variante pour cette année spécifique
    for variant in variants:
        commune_nom = variant["nom"]
        dept = variant["departement"] if not departement else departement
        
        where_clause = f'an="{annee}" AND inom="{commune_nom}"'
        if dept:
            where_clause += f' AND dep="{dept}"'
        
        params = {"where": where_clause, "limit": 100}
        
        try:
            response = requests.get(api_url, params=params, timeout=10)
            data = response.json()

            if "results" not in data or not data["results"]:
                continue  # Essaye la variante suivante

            df = pd.DataFrame(data["results"])
            colonnes = ['an', 'fimpo1', 'mimpo1', 'fprod', 'mprod', 'tth', 'tmth', 'tfb', 'tmfb', 'tfnb', 'tmfnb']
            colonnes_existantes = [c for c in colonnes if c in df.columns]
            
            if not colonnes_existantes:
                continue  # Essaye la variante suivante
                
            df_fiscalite = df[colonnes_existantes].copy()

            # Calcul des ratios Impôts locaux sur RRF (identique à votre version)
            if 'fimpo1' in df_fiscalite.columns and 'fprod' in df_fiscalite.columns:
                df_fiscalite['Commune'] = (df_fiscalite['fimpo1'] / df_fiscalite['fprod'] * 100).round(2)
            if 'mimpo1' in df_fiscalite.columns and 'mprod' in df_fiscalite.columns:
                df_fiscalite['Moyenne de la strate'] = (df_fiscalite['mimpo1'] / df_fiscalite['mprod'] * 100).round(2)

            # Renommer colonnes pour affichage (identique à votre version)
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

            # Succès ! Donnée trouvée avec cette variante
            if commune_nom != commune:
                st.info(f"🔍 Données trouvées pour '{commune}' via '{commune_nom}'")

            return df_fiscalite
            
        except requests.RequestException:
            continue  # Essaye la variante suivante
    
    # Aucune variante n'a fonctionné
    return pd.DataFrame()

def run(commune=None, annees=None, departement=None):
    """Votre fonction run - CODE ORIGINAL + fetch robuste mis à jour"""
    st.title("🏦 Fiscalité des communes")

    commune_selectionnee = st.text_input("Nom de la commune :", value=commune or "RENAGE")
    departement_selectionne = st.text_input('Département (optionnel) :', value=departement or "")
    
    # Années étendues pour inclure 2024
    annees_disponibles = list(range(2024, 2018, -1))
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=annees_disponibles,
        default=annees or annees_disponibles
    )

    df_list = []
    if commune_selectionnee and annees:
        # Affiche les variantes une seule fois
        fetcher = get_fetcher()
        variants = fetcher.find_commune_variants(commune_selectionnee, departement_selectionne)
        
        if len(variants) > 1:
            variant_names = [v["nom"] for v in variants]
            st.info(f"🔍 Variantes détectées: {', '.join(set(variant_names))}")
        
        for annee in annees:
            # ✅ VERSION ROBUSTE ADAPTÉE AUX NOUVEAUX DATASETS
            df_annee = fetch_commune_fiscalite(commune_selectionnee, annee, departement_selectionne)
            if not df_annee.empty:
                df_list.append(df_annee)

        if df_list:
            fiscalite = pd.concat(df_list, ignore_index=True)
            fiscalite.set_index("Année", inplace=True)
            fiscalite.sort_index(inplace=True)
            
            st.success(f"✅ Données fiscalité récupérées: {len(df_list)} années sur {len(annees)} demandées")

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

                        # 🔹 Graphique Plotly (identique à votre version)
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

if __name__ == "__main__":
    run()