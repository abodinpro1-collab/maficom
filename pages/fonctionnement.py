import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import re
from functools import lru_cache
from difflib import SequenceMatcher

class RobustCommuneFetcher:
    """Version autonome du fetcher - pas d'import externe"""
    
    def __init__(self):
        self.api_base_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
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
        """Trouve les variantes d'une commune"""
        cache_key = f"{commune}_{departement}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        variants = []
        search_terms = self._generate_search_terms(commune)
        
        for term in search_terms:
            where_clause = f'inom LIKE "%{term}%"'
            if departement:
                where_clause += f' AND dep="{departement}"'
            where_clause += ' AND an IN ("2019","2020","2021","2022","2023")'
            
            params = {"where": where_clause, "limit": 50, "select": "inom,dep"}
            
            try:
                response = requests.get(self.api_base_url, params=params, timeout=10)
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

def fetch_commune_fonctionnement(commune, annee, departement=None):
    """Version robuste du fetch fonctionnement - AUTONOME"""
    
    fetcher = get_fetcher()
    
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
            response = requests.get(fetcher.api_base_url, params=params, timeout=10)
            data = response.json()
            
            if "results" not in data or not data["results"]:
                continue  # Essaye la variante suivante
            
            df = pd.DataFrame(data["results"])
            colonnes_voulu = ['an', 'pop1', 'prod', 'charge', 'fprod', 'mprod',
                              'fcharge', 'mcharge', 'fdgf', 'mdgf', 'fperso', 'mperso']
            colonnes_existantes = [c for c in colonnes_voulu if c in df.columns]
            
            if not colonnes_existantes:
                continue  # Essaye la variante suivante
                
            df_fonctionnement = df[colonnes_existantes].copy()

            # Renommer colonnes (identique à votre version)
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
            
            # Ratios (identiques à votre version)
            if "Dépenses de personnel / habitant" in df_fonctionnement.columns and "Dépenses réelles de fonctionnement / habitant" in df_fonctionnement.columns:
                df_fonctionnement["Ratio Dépenses personnel / Dépenses fonctionnement"] = (
                    df_fonctionnement["Dépenses de personnel / habitant"] /
                    df_fonctionnement["Dépenses réelles de fonctionnement / habitant"] * 100
                ).round(2)
            
            if "Moyenne de la strate Dépenses de personnel / habitant" in df_fonctionnement.columns and "Moyenne de la strate Dépenses réelles fonctionnement / habitant" in df_fonctionnement.columns:
                df_fonctionnement["Ratio Moyenne Dépenses personnel / Dépenses fonctionnement"] = (
                    df_fonctionnement["Moyenne de la strate Dépenses de personnel / habitant"] /
                    df_fonctionnement["Moyenne de la strate Dépenses réelles fonctionnement / habitant"] * 100
                ).round(2)
            
            # Succès ! Donnée trouvée avec cette variante
            if commune_nom != commune:
                st.info(f"🔍 Données trouvées pour '{commune}' via '{commune_nom}'")
            
            return df_fonctionnement
            
        except requests.RequestException:
            continue  # Essaye la variante suivante
    
    # Aucune variante n'a fonctionné
    return pd.DataFrame()

def run(commune=None, annees=None, departement=None):
    """Votre fonction run - CODE ORIGINAL + fetch robuste"""
    st.title("💰 Fonctionnement des communes")

    commune_selectionnee = st.text_input("Nom de la commune :", value=commune or "RENAGE")
    departement_selectionne = st.text_input('Département (optionnel) :', value=departement or "")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2023, 2018, -1)),
        default=annees or list(range(2023, 2018, -1))
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
            # ✅ VERSION ROBUSTE - sans import externe
            df_annee = fetch_commune_fonctionnement(commune_selectionnee, annee, departement_selectionne)
            if not df_annee.empty:
                df_list.append(df_annee)

        if df_list:
            fonctionnement = pd.concat(df_list, ignore_index=True)
            fonctionnement.set_index("Année", inplace=True)
            
            st.success(f"✅ Données fonctionnement récupérées: {len(df_list)} années sur {len(annees)} demandées")

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

                        # Graphique avec Plotly (identique à votre version)
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

if __name__ == "__main__":
    run()