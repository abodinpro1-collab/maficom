import pandas as pd
import streamlit as st
import plotly.express as px
import requests
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
        """Trouve les variantes d'une commune - VERSION CORRECTE"""
        cache_key = f"{commune}_{departement}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        variants = []
        search_terms = self._generate_search_terms(commune)
        
        # Recherche sur toutes les années pour détecter les changements de nom
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
                            # Évite les doublons
                            if variant not in variants:
                                variants.append(variant)
            except:
                continue
        
        # Si aucune variante trouvée, utilise le nom original
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

def fetch_commune_investissement(commune, annees, departement=None):
    """Version robuste du fetch investissement - AUTONOME avec diagnostic"""
    
    fetcher = get_fetcher()
    
    # 1. Trouve les variantes
    variants = fetcher.find_commune_variants(commune, departement)
    
    if len(variants) > 1:
        variant_names = [v["nom"] for v in variants]
        st.info(f"🔍 Variantes détectées: {', '.join(set(variant_names))}")
    
    # 2. Diagnostic détaillé par année
    st.write("🔍 **Diagnostic par année:**")
    diagnostic_data = []
    
    # 3. Récupère les données avec diagnostic
    df_list = []
    
    for annee in annees:
        annee_trouvee = False
        
        for variant in variants:
            commune_nom = variant["nom"]
            dept = variant["departement"] if not departement else departement
            
            url = fetcher.api_base_url
            where_clause = f'an="{annee}" AND inom="{commune_nom}"'
            if dept:
                where_clause += f' AND dep="{dept}"'
            
            params = {"where": where_clause, "limit": 100}
            
            try:
                r = requests.get(url, params=params, timeout=10)
                data = r.json().get("results", [])
                
                if data:
                    df = pd.DataFrame(data)
                    cols = ['an', 'fequip', 'mequip', 'fprod', 'mprod']
                    df_exist = [c for c in cols if c in df.columns]
                    
                    if df_exist:
                        df = df[df_exist].copy()

                        # Calculs identiques à votre version
                        df['Dépenses d\'équipement / habitant Commune'] = df['fequip']
                        df['Dépenses d\'équipement / habitant Moyenne'] = df['mequip']
                        df['Dépenses d\'équipement / RRF Commune'] = (df['fequip'] / df['fprod'] * 100).round(2)
                        df['Dépenses d\'équipement / RRF Moyenne'] = (df['mequip'] / df['mprod'] * 100).round(2)

                        df.rename(columns={'an': 'Année'}, inplace=True)
                        df_list.append(df)
                        annee_trouvee = True
                        
                        # Diagnostic positif
                        diagnostic_data.append({
                            "Année": annee,
                            "Status": "✅ Trouvée",
                            "Commune utilisée": commune_nom,
                            "Département": dept
                        })
                        break  # Année trouvée, on passe à la suivante
                        
            except requests.RequestException as e:
                continue
        
        # Si aucune variante n'a donné de résultat pour cette année
        if not annee_trouvee:
            diagnostic_data.append({
                "Année": annee,
                "Status": "❌ Manquante",
                "Commune utilisée": "Aucune",
                "Département": departement or "Non spécifié"
            })
    
    # Affiche le diagnostic
    if diagnostic_data:
        df_diagnostic = pd.DataFrame(diagnostic_data)
        st.dataframe(df_diagnostic, use_container_width=True)
        
        # Compte les années manquantes
        annees_manquantes = [d["Année"] for d in diagnostic_data if d["Status"] == "❌ Manquante"]
        if annees_manquantes:
            st.warning(f"⚠️ **Années manquantes: {annees_manquantes}**")
            st.info("💡 **Solutions possibles:**")
            st.write("1. Vérifiez l'orthographe exacte de la commune")
            st.write("2. La commune a peut-être changé de nom ces années-là")
            st.write("3. Essayez de préciser le département")
            
            # Recherche élargie pour les années manquantes
            if st.button("🔍 Recherche élargie pour les années manquantes"):
                st.write("**Recherche élargie en cours...**")
                for annee_manquante in annees_manquantes:
                    st.write(f"\n**Année {annee_manquante}:**")
                    
                    # Recherche avec critères plus souples
                    for term in [commune, commune.upper(), commune.replace("(LA)", "").strip(), f"LA {commune.replace('(LA)', '').strip()}"]:
                        where_clause = f'inom LIKE "%{term}%" AND an="{annee_manquante}"'
                        if departement:
                            where_clause += f' AND dep="{departement}"'
                        
                        params = {"where": where_clause, "limit": 10, "select": "inom,dep"}
                        
                        try:
                            response = requests.get(fetcher.api_base_url, params=params, timeout=8)
                            data = response.json()
                            
                            if "results" in data and data["results"]:
                                st.write(f"Communes similaires trouvées pour '{term}':")
                                for result in data["results"][:5]:
                                    st.write(f"  • {result.get('inom', '')} (dép: {result.get('dep', '')})")
                                break
                        except:
                            continue
    
    # 4. Résultat final
    if df_list:
        df_final = pd.concat(df_list, ignore_index=True)
        df_final = df_final.drop_duplicates(subset=['Année'], keep='first')
        df_final = df_final.sort_values("Année")
        
        st.success(f"✅ **Données récupérées: {len(df_final)} lignes sur {len(annees)} demandées**")
        return df_final
    
    return pd.DataFrame()

def run(commune=None, annees=None, departement=None):
    """Votre fonction run - CODE ORIGINAL + fetch robuste"""
    st.title("🏗️ Investissements des communes")

    commune_selectionnee = st.text_input("Nom de la commune :", value=commune or "RENAGE")
    departement_selectionne = st.text_input('Département (optionnel) :', value=departement or "")
    annees = st.multiselect(
        "Sélectionnez les années à afficher :",
        options=list(range(2023, 2018, -1)),
        default=annees or list(range(2023, 2018, -1))
    )
    
    if commune_selectionnee and annees:
        # ✅ VERSION ROBUSTE - sans import externe
        df = fetch_commune_investissement(commune_selectionnee, annees, departement_selectionne)
        
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

if __name__ == "__main__":
    run()