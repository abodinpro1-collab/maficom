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

def fetch_commune_caf(commune, annees, departement=None):
    """Version robuste adaptée aux nouveaux datasets"""
    
    fetcher = get_fetcher()
    
    # 1. Trouve les variantes
    variants = fetcher.find_commune_variants(commune, departement)
    
    if len(variants) > 1:
        variant_names = [v["nom"] for v in variants]
        st.info(f"🔍 Variantes détectées: {', '.join(set(variant_names))}")
    
    # 2. Récupère les données année par année
    dfs = []
    
    for annee in annees:
        annee_trouvee = False
        api_url = get_api_url_for_year(annee)  # URL adaptée à l'année
        
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
                    continue

                df = pd.DataFrame(data["results"])
                colonnes_calc = ['an', 'pop1', 'fcaf', 'mcaf', 'fprod', 'mprod', 'fcafn', 'mcafn']
                colonnes_existantes = [c for c in colonnes_calc if c in df.columns]
                
                if not colonnes_existantes:
                    continue
                    
                df_caf = df[colonnes_existantes].copy()

                # Calculs identiques à votre version originale
                df_caf['CAF brute / RRF Commune'] = df_caf.apply(
                    lambda row: (row['fcaf'] / row['fprod']) * 100 if row['fprod'] != 0 else None, axis=1)
                df_caf['CAF brute / RRF Moyenne'] = df_caf.apply(
                    lambda row: (row['mcaf'] / row['mprod']) * 100 if row['mprod'] != 0 else None, axis=1)
                df_caf['CAF nette / RRF Commune'] = df_caf.apply(
                    lambda row: (row['fcafn'] / row['fprod']) * 100 if row['fprod'] != 0 else None, axis=1)
                df_caf['CAF nette / RRF Moyenne'] = df_caf.apply(
                    lambda row: (row['mcafn'] / row['mprod']) * 100 if row['mprod'] != 0 else None, axis=1)

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
                annee_trouvee = True
                break  # Année trouvée, passe à la suivante
                
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            st.warning(f"⚠️ Données CAF non trouvées pour {commune} en {annee}")

    # 3. Résultat final
    if dfs:
        result = pd.concat(dfs, ignore_index=True)
        result.sort_values("Année", inplace=True)
        st.success(f"✅ Données CAF récupérées: {len(result)} lignes sur {len(annees)} années demandées")
        return result
    else:
        st.warning(f"❌ Aucune donnée CAF trouvée pour '{commune}'")
        return pd.DataFrame()

def run(commune=None, annees=None, departement=None):
    """Votre fonction run - CODE ORIGINAL + fetch robuste mis à jour"""
    global table_caf  # <- important pour l'export
    st.title("🧾 CAF des communes")

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
        caf = fetch_commune_caf(commune_selectionnee, annees, departement_selectionne)
        
        if caf.empty:
            st.warning("Aucune donnée disponible pour cette commune et ces années.")
            table_caf = pd.DataFrame()  # reset pour l'export
            return

        table_caf = caf.copy()  # on stocke pour export

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

if __name__ == "__main__":
    run()