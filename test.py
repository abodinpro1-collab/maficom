import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from functools import lru_cache
from difflib import SequenceMatcher
import numpy as np

# Configuration
st.set_page_config(
    page_title="CAF Analytics Pro",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS ÉLÉGANT ET COMPLET
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    * { font-family: 'DM Sans', sans-serif; }
    .stApp { background: #fafafa; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    
    /* Header */
    .elegant-header {
        padding: 60px 0 40px 0;
        border-bottom: 1px solid #e8e8e8;
        margin-bottom: 40px;
    }
    .main-title {
        font-size: 2.8rem;
        font-weight: 300;
        color: #1a1a1a;
        letter-spacing: -1px;
        margin-bottom: 8px;
    }
    .main-title strong { font-weight: 600; }
    .subtitle {
        font-size: 0.95rem;
        color: #666;
        font-weight: 400;
        letter-spacing: 0.5px;
    }
    
    /* Section */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a1a;
        margin: 50px 0 20px 0;
        letter-spacing: -0.3px;
    }
    
    /* Insight card */
    .insight-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        padding: 30px;
        margin: 20px 0;
    }
    .insight-title {
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        opacity: 0.9;
        margin-bottom: 15px;
    }
    .insight-text {
        font-size: 1.2rem;
        font-weight: 500;
        line-height: 1.6;
    }
    .insight-icon {
        font-size: 2rem;
        margin-bottom: 10px;
    }
    
    /* Score card */
    .score-card {
        background: white;
        border: 2px solid #e8e8e8;
        border-radius: 12px;
        padding: 30px;
        text-align: center;
        transition: all 0.3s ease;
    }
    .score-value {
        font-size: 4rem;
        font-weight: 700;
        line-height: 1;
        margin: 20px 0;
    }
    .score-label {
        font-size: 0.9rem;
        color: #666;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .score-excellent { color: #10b981; border-color: #10b981; }
    .score-good { color: #3b82f6; border-color: #3b82f6; }
    .score-warning { color: #f59e0b; border-color: #f59e0b; }
    .score-danger { color: #ef4444; border-color: #ef4444; }
    
    /* Stat card with tooltip */
    .stat-card {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 28px 24px;
        transition: all 0.3s ease;
        position: relative;
    }
    .stat-card:hover {
        border-color: #1a1a1a;
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    }
    .stat-value {
        font-size: 2.2rem;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 8px;
        letter-spacing: -1px;
        font-family: 'JetBrains Mono', monospace;
    }
    .stat-label {
        font-size: 0.8rem;
        color: #999;
        font-weight: 500;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .stat-vs-moyenne {
        font-size: 0.85rem;
        font-weight: 500;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #f0f0f0;
    }
    .badge-health {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 8px;
    }
    .badge-excellent { background: #d1fae5; color: #065f46; }
    .badge-good { background: #dbeafe; color: #1e40af; }
    .badge-warning { background: #fef3c7; color: #92400e; }
    .badge-danger { background: #fee2e2; color: #991b1b; }
    
    /* Tooltip icon */
    .tooltip-icon {
        display: inline-block;
        width: 16px;
        height: 16px;
        background: #e0e0e0;
        border-radius: 50%;
        text-align: center;
        line-height: 16px;
        font-size: 11px;
        color: #666;
        cursor: help;
        margin-left: 5px;
    }
    
    /* Alert box */
    .alert-box {
        background: white;
        border-left: 4px solid;
        border-radius: 8px;
        padding: 20px;
        margin: 15px 0;
    }
    .alert-info { border-color: #3b82f6; }
    .alert-warning { border-color: #f59e0b; }
    .alert-success { border-color: #10b981; }
    .alert-danger { border-color: #ef4444; }
    .alert-title {
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 8px;
    }
    .alert-text {
        font-size: 0.9rem;
        color: #666;
        line-height: 1.5;
    }
    
    /* Priority list */
    .priority-item {
        background: white;
        border-left: 4px solid #ef4444;
        padding: 15px 20px;
        margin: 10px 0;
        border-radius: 8px;
    }
    .priority-number {
        display: inline-block;
        width: 24px;
        height: 24px;
        background: #1a1a1a;
        color: white;
        border-radius: 50%;
        text-align: center;
        line-height: 24px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 10px;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 14px 18px;
        font-size: 0.95rem;
        color: #1a1a1a;
        transition: all 0.2s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #1a1a1a;
        box-shadow: 0 0 0 1px #1a1a1a;
    }
    .stTextInput > label, .stMultiSelect > label {
        font-size: 0.85rem;
        font-weight: 500;
        color: #666;
        letter-spacing: 0.3px;
        text-transform: uppercase;
    }
    .stMultiSelect > div > div {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    
    /* Buttons */
    .stButton > button {
        background: white;
        color: #1a1a1a;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: #1a1a1a;
        color: white;
        border-color: #1a1a1a;
    }
    
    /* Carousel */
    .carousel-container {
        background: white;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 40px;
        margin: 30px 0;
    }
    .carousel-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #1a1a1a;
        letter-spacing: -0.5px;
        margin-bottom: 10px;
    }
    .carousel-description {
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 25px;
        line-height: 1.6;
    }
    .nav-dots {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 25px;
    }
    .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #e0e0e0;
        transition: all 0.3s ease;
    }
    .dot.active {
        width: 24px;
        border-radius: 3px;
        background: #1a1a1a;
    }
    
    /* Dataframe */
    .dataframe {
        font-size: 0.9rem;
        border: none !important;
    }
    .dataframe thead tr th {
        background: #fafafa !important;
        color: #666 !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        border-bottom: 2px solid #e8e8e8 !important;
    }
    .dataframe tbody tr td {
        border-bottom: 1px solid #f5f5f5 !important;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
    }
    
    hr { border: none; border-top: 1px solid #e8e8e8; margin: 40px 0; }
</style>
""", unsafe_allow_html=True)

# Mapping des datasets
DATASETS_MAPPING = {
    2019: "comptes-individuels-des-communes-fichier-global-2019-2020",
    2020: "comptes-individuels-des-communes-fichier-global-2019-2020",
    2021: "comptes-individuels-des-communes-fichier-global-2021",
    2022: "comptes-individuels-des-communes-fichier-global-2022",
    2023: "comptes-individuels-des-communes-fichier-global-2023-2024",
    2024: "comptes-individuels-des-communes-fichier-global-2023-2024"
}

def get_dataset_for_year(annee):
    return DATASETS_MAPPING.get(annee, "comptes-individuels-des-communes-fichier-global-2023-2024")

def get_api_url_for_year(annee):
    dataset = get_dataset_for_year(annee)
    return f"https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/{dataset}/records"

class RobustCommuneFetcher:
    def __init__(self):
        self._cache = {}
    
    @lru_cache(maxsize=500)
    def normalize_commune_name(self, name):
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
        cache_key = f"{commune}_{departement}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        variants = []
        search_terms = self._generate_search_terms(commune)
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
        norm1 = self.normalize_commune_name(search_commune)
        norm2 = self.normalize_commune_name(found_commune)
        return SequenceMatcher(None, norm1, norm2).ratio() >= threshold

@st.cache_resource
def get_fetcher():
    return RobustCommuneFetcher()

def fetch_commune_caf(commune, annees, departement=None):
    fetcher = get_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
    if len(variants) > 1:
        variant_names = [v["nom"] for v in variants]
        st.info(f"Variantes détectées : {', '.join(set(variant_names))}")
    
    dfs = []
    for annee in annees:
        annee_trouvee = False
        api_url = get_api_url_for_year(annee)
        
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
                df_caf['CAF brute / RRF Commune'] = df_caf.apply(
                    lambda row: (row['fcaf'] / row['fprod']) * 100 if row['fprod'] != 0 else None, axis=1)
                df_caf['CAF brute / RRF Moyenne'] = df_caf.apply(
                    lambda row: (row['mcaf'] / row['mprod']) * 100 if row['mprod'] != 0 else None, axis=1)
                df_caf['CAF nette / RRF Commune'] = df_caf.apply(
                    lambda row: (row['fcafn'] / row['fprod']) * 100 if row['fprod'] != 0 else None, axis=1)
                df_caf['CAF nette / RRF Moyenne'] = df_caf.apply(
                    lambda row: (row['mcafn'] / row['mprod']) * 100 if row['mprod'] != 0 else None, axis=1)
                
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
                break
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            st.warning(f"Données non disponibles pour {annee}")
    
    if dfs:
        result = pd.concat(dfs, ignore_index=True)
        result.sort_values("Année", inplace=True)
        return result
    else:
        st.warning(f"Aucune donnée trouvée pour {commune}")
        return pd.DataFrame()

# Fonctions d'analyse
def calculer_score_sante(caf_df):
    """Calcule un score de santé financière sur 100"""
    if caf_df.empty:
        return 0
    
    derniere = caf_df.iloc[-1]
    score = 50
    
    if derniere['CAF brute / RRF Commune'] > 10:
        score += 20
    elif derniere['CAF brute / RRF Commune'] > 7:
        score += 10
    elif derniere['CAF brute / RRF Commune'] < 5:
        score -= 10
    
    if derniere['CAF brute / RRF Commune'] > derniere['CAF brute / RRF Moyenne']:
        score += 15
    else:
        score -= 5
    
    if len(caf_df) > 1:
        evolution = ((caf_df['CAF brute / habitant Commune'].iloc[-1] / 
                     caf_df['CAF brute / habitant Commune'].iloc[0]) - 1) * 100
        if evolution > 5:
            score += 15
        elif evolution > 0:
            score += 10
        elif evolution < -5:
            score -= 15
    
    return max(0, min(100, score))

def get_health_status(score):
    """Retourne le statut de santé selon le score"""
    if score >= 80:
        return "excellent", "Excellente santé", "#10b981"
    elif score >= 60:
        return "good", "Bonne santé", "#3b82f6"
    elif score >= 40:
        return "warning", "À surveiller", "#f59e0b"
    else:
        return "danger", "Attention requise", "#ef4444"

def generer_insights(caf_df):
    """Génère des insights intelligents"""
    insights = []
    
    if caf_df.empty:
        return insights
    
    derniere = caf_df.iloc[-1]
    
    diff_rrf = derniere['CAF brute / RRF Commune'] - derniere['CAF brute / RRF Moyenne']
    if abs(diff_rrf) > 2:
        if diff_rrf > 0:
            insights.append({
                "icon": "📈",
                "text": f"Votre CAF/RRF est supérieur de {diff_rrf:.1f} points à la moyenne nationale. Excellente performance !"
            })
        else:
            insights.append({
                "icon": "⚠️",
                "text": f"Votre CAF/RRF est inférieur de {abs(diff_rrf):.1f} points à la moyenne. Des marges d'amélioration existent."
            })
    
    if len(caf_df) > 1:
        evolution = ((caf_df['CAF brute / habitant Commune'].iloc[-1] / 
                     caf_df['CAF brute / habitant Commune'].iloc[0]) - 1) * 100
        if evolution > 10:
            insights.append({
                "icon": "🚀",
                "text": f"Croissance remarquable de {evolution:.1f}% de votre CAF/habitant sur la période."
            })
        elif evolution < -10:
            insights.append({
                "icon": "📉",
                "text": f"Attention : diminution de {abs(evolution):.1f}% de votre CAF/habitant. Analyse recommandée."
            })
    
    if derniere['CAF brute / RRF Commune'] < 5:
        insights.append({
            "icon": "🔴",
            "text": "Votre CAF/RRF est sous le seuil de vigilance de 5%. Action immédiate recommandée."
        })
    
    return insights

def identifier_priorites(caf_df):
    """Identifie les 3 priorités d'action"""
    priorites = []
    
    if caf_df.empty:
        return priorites
    
    derniere = caf_df.iloc[-1]
    
    if derniere['CAF brute / RRF Commune'] < 7:
        priorites.append("Améliorer le ratio CAF/RRF (objectif > 7%) pour renforcer la capacité d'autofinancement")
    
    if derniere['CAF brute / RRF Commune'] < derniere['CAF brute / RRF Moyenne']:
        priorites.append("Rattraper la moyenne nationale en optimisant les recettes de fonctionnement")
    
    if len(caf_df) > 1:
        evolution = ((caf_df['CAF brute / habitant Commune'].iloc[-1] / 
                     caf_df['CAF brute / habitant Commune'].iloc[0]) - 1) * 100
        if evolution < 0:
            priorites.append("Inverser la tendance baissière observée sur les dernières années")
    
    if len(priorites) == 0:
        priorites.append("Maintenir le bon niveau de performance actuel")
        priorites.append("Anticiper les investissements futurs en conservant une CAF élevée")
    
    return priorites[:3]

# SIDEBAR : Glossaire
with st.sidebar:
    st.markdown("### 📚 Glossaire")
    
    with st.expander("CAF (Capacité d'Autofinancement)"):
        st.markdown("""
        **Définition** : Ressource disponible pour financer les investissements et rembourser la dette.
        
        **Formule** :  
        `CAF = Recettes réelles - Dépenses réelles de fonctionnement`
        
        **Seuil de référence** : Une CAF saine représente généralement > 15% des recettes de fonctionnement.
        """)
    
    with st.expander("RRF (Recettes Réelles de Fonctionnement)"):
        st.markdown("""
        **Définition** : Ensemble des recettes encaissées par la commune pour son fonctionnement courant.
        
        **Composition** :
        - Impôts et taxes
        - Dotations de l'État
        - Autres recettes
        
        **Indicateur clé** pour mesurer les ressources disponibles.
        """)
    
    with st.expander("CAF / RRF (%)"):
        st.markdown("""
        **Définition** : Ratio mesurant la part des recettes qui peut être consacrée à l'investissement.
        
        **Formule** :  
        `(CAF / RRF) × 100`
        
        **Interprétation** :
        - < 5% : Situation préoccupante
        - 5-7% : Situation fragile
        - 7-10% : Situation correcte
        - > 10% : Bonne situation
        """)
    
    with st.expander("CAF nette"):
        st.markdown("""
        **Définition** : CAF après remboursement du capital de la dette.
        
        **Formule** :  
        `CAF nette = CAF brute - Remboursement en capital`
        
        **Usage** : Mesure la capacité d'investissement réelle après gestion de la dette.
        """)

# HEADER
st.markdown("""
<div class="elegant-header">
    <div class="main-title"><strong>CAF</strong> Analytics Pro</div>
    <div class="subtitle">ANALYSE FINANCIÈRE COMMUNALE AVANCÉE</div>
</div>
""", unsafe_allow_html=True)

# RECHERCHE
col1, col2 = st.columns([3, 1])
with col1:
    commune_selectionnee = st.text_input("Commune", value="RENAGE")
with col2:
    departement_selectionne = st.text_input("Département", value="")

annees_disponibles = list(range(2024, 2018, -1))
annees = st.multiselect(
    "Années d'analyse",
    options=annees_disponibles,
    default=annees_disponibles
)

# Initialisation carrousel
if 'carousel_index' not in st.session_state:
    st.session_state.carousel_index = 0

if commune_selectionnee and annees:
    caf = fetch_commune_caf(commune_selectionnee, annees, departement_selectionne)
    
    if not caf.empty:
        derniere_annee = caf['Année'].max()
        derniere_ligne = caf[caf['Année'] == derniere_annee].iloc[0]
        
        # SCORE DE SANTÉ
        score = calculer_score_sante(caf)
        status, status_label, status_color = get_health_status(score)
        
        st.markdown('<div class="section-title">Score de Santé Financière</div>', unsafe_allow_html=True)
        
        col_score, col_insights = st.columns([1, 2])
        
        with col_score:
            st.markdown(f"""
            <div class="score-card score-{status}">
                <div class="score-label">Score Global</div>
                <div class="score-value">{score}/100</div>
                <div class="score-label">{status_label}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_insights:
            insights = generer_insights(caf)
            if insights:
                for insight in insights[:2]:
                    st.markdown(f"""
                    <div class="insight-card">
                        <div class="insight-icon">{insight['icon']}</div>
                        <div class="insight-text">{insight['text']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # PRIORITÉS
        st.markdown('<div class="section-title">Priorités d\'Action</div>', unsafe_allow_html=True)
        priorites = identifier_priorites(caf)
        
        for i, priorite in enumerate(priorites, 1):
            st.markdown(f"""
            <div class="priority-item">
                <span class="priority-number">{i}</span>
                <span>{priorite}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # KPI avec contexte
        st.markdown('<div class="section-title">Indicateurs Clés</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            pop = int(derniere_ligne['Population'])
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{pop:,}</div>
                <div class="stat-label">Population <span class="tooltip-icon" title="Nombre d'habitants">?</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            caf_hab = derniere_ligne['CAF brute / habitant Commune']
            caf_hab_moy = derniere_ligne['CAF brute / habitant Moyenne']
            diff_hab = ((caf_hab / caf_hab_moy) - 1) * 100
            badge_class = "excellent" if diff_hab > 10 else "good" if diff_hab > 0 else "warning" if diff_hab > -10 else "danger"
            
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{caf_hab:.0f}€</div>
                <div class="stat-label">CAF par habitant <span class="tooltip-icon" title="Capacité d'autofinancement par habitant">?</span></div>
                <div class="stat-vs-moyenne">vs moyenne: {diff_hab:+.1f}%</div>
                <span class="badge-health badge-{badge_class}">{'Au-dessus' if diff_hab > 0 else 'En-dessous'}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            caf_rrf = derniere_ligne['CAF brute / RRF Commune']
            caf_rrf_moy = derniere_ligne['CAF brute / RRF Moyenne']
            health_badge = "excellent" if caf_rrf > 10 else "good" if caf_rrf > 7 else "warning" if caf_rrf > 5 else "danger"
            health_text = "Excellent" if caf_rrf > 10 else "Bon" if caf_rrf > 7 else "Fragile" if caf_rrf > 5 else "Critique"
            
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{caf_rrf:.1f}%</div>
                <div class="stat-label">CAF / RRF <span class="tooltip-icon" title="Capacité d'autofinancement sur recettes">?</span></div>
                <div class="stat-vs-moyenne">Moyenne: {caf_rrf_moy:.1f}%</div>
                <span class="badge-health badge-{health_badge}">{health_text}</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            if len(caf) > 1:
                evolution = ((caf['CAF brute / habitant Commune'].iloc[-1] / caf['CAF brute / habitant Commune'].iloc[0]) - 1) * 100
                sign = "+" if evolution >= 0 else ""
                color_class = "excellent" if evolution > 10 else "good" if evolution > 0 else "warning" if evolution > -10 else "danger"
                trend_text = "Forte croissance" if evolution > 10 else "Croissance" if evolution > 0 else "Stable" if abs(evolution) < 5 else "Déclin"
                
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-value">{sign}{evolution:.1f}%</div>
                    <div class="stat-label">Évolution <span class="tooltip-icon" title="Évolution sur la période">?</span></div>
                    <div class="stat-vs-moyenne">{len(caf)} années</div>
                    <span class="badge-health badge-{color_class}">{trend_text}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="stat-card">
                    <div class="stat-value">—</div>
                    <div class="stat-label">Évolution</div>
                    <div class="stat-vs-moyenne">Données insuffisantes</div>
                </div>
                """, unsafe_allow_html=True)
        
        # ALERTES CONTEXTUELLES
        st.markdown("---")
        
        if caf_rrf < 7:
            st.markdown(f"""
            <div class="alert-box alert-warning">
                <div class="alert-title">⚠️ Capacité d'autofinancement à surveiller</div>
                <div class="alert-text">
                Votre ratio CAF/RRF de {caf_rrf:.1f}% est inférieur au seuil recommandé de 7%. 
                Cela peut limiter votre capacité d'investissement. Considérez une optimisation des dépenses 
                de fonctionnement ou une augmentation des recettes.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if len(caf) > 2:
            derniers_3_ans = caf.tail(3)
            if (derniers_3_ans['CAF brute / habitant Commune'].iloc[-1] < 
                derniers_3_ans['CAF brute / habitant Commune'].iloc[0]):
                st.markdown("""
                <div class="alert-box alert-info">
                    <div class="alert-title">📊 Tendance observée</div>
                    <div class="alert-text">
                    Une diminution de la CAF est observée sur les 3 dernières années. 
                    Il serait pertinent d'analyser l'évolution des charges de fonctionnement et 
                    d'identifier les leviers d'optimisation.
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        if caf_rrf > 10 and diff_hab > 10:
            st.markdown("""
            <div class="alert-box alert-success">
                <div class="alert-title">✅ Excellente performance financière</div>
                <div class="alert-text">
                Votre commune affiche une santé financière remarquable, bien au-dessus des moyennes nationales. 
                Cette situation favorable vous offre une grande marge de manœuvre pour vos projets d'investissement.
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # SMALL MULTIPLES
        st.markdown('<div class="section-title">Vue d\'Ensemble - Tous les Indicateurs</div>', unsafe_allow_html=True)
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('CAF par habitant', 'CAF / RRF (%)', 
                          'Évolution CAF brute', 'Comparaison Commune vs Moyenne'),
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        fig.add_trace(
            go.Scatter(x=caf['Année'], y=caf['CAF brute / habitant Commune'],
                      mode='lines+markers', name='Commune',
                      line=dict(color='#1a1a1a', width=2)),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=caf['Année'], y=caf['CAF brute / habitant Moyenne'],
                      mode='lines+markers', name='Moyenne',
                      line=dict(color='#999999', width=2, dash='dash')),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(x=caf['Année'], y=caf['CAF brute / RRF Commune'],
                      mode='lines+markers', name='CAF/RRF',
                      line=dict(color='#1a1a1a', width=2)),
            row=1, col=2
        )
        fig.add_hrect(y0=7, y1=15, fillcolor="#10b981", opacity=0.1,
                     line_width=0, row=1, col=2)
        fig.add_hrect(y0=5, y1=7, fillcolor="#f59e0b", opacity=0.1,
                     line_width=0, row=1, col=2)
        fig.add_hrect(y0=0, y1=5, fillcolor="#ef4444", opacity=0.1,
                     line_width=0, row=1, col=2)
        
        if len(caf) > 1:
            base_caf = caf['CAF brute / habitant Commune'].iloc[0]
            evolution_indexee = (caf['CAF brute / habitant Commune'] / base_caf * 100) - 100
            fig.add_trace(
                go.Bar(x=caf['Année'], y=evolution_indexee,
                      marker_color=['#10b981' if v > 0 else '#ef4444' for v in evolution_indexee],
                      name='Évolution %'),
                row=2, col=1
            )
            fig.add_hline(y=0, line_dash="dash", line_color="#999", row=2, col=1)
        
        ecart = caf['CAF brute / RRF Commune'] - caf['CAF brute / RRF Moyenne']
        fig.add_trace(
            go.Bar(x=caf['Année'], y=ecart,
                  marker_color=['#10b981' if v > 0 else '#ef4444' for v in ecart],
                  name='Écart points'),
            row=2, col=2
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#999", row=2, col=2)
        
        fig.update_layout(
            height=600,
            showlegend=False,
            template="plotly_white",
            font=dict(family="DM Sans", size=11),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        fig.update_xaxes(showgrid=False, showline=True, linewidth=1, linecolor='#e8e8e8')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#f5f5f5')
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # CARROUSEL DÉTAILLÉ
        st.markdown('<div class="section-title">Analyse Détaillée par Indicateur</div>', unsafe_allow_html=True)
        
        indicateurs = {
            "CAF brute par habitant": {
                "colonnes": ["CAF brute / habitant Commune", "CAF brute / habitant Moyenne"],
                "unite": "€",
                "description": "Mesure la capacité d'autofinancement rapportée au nombre d'habitants. Un montant élevé indique une bonne santé financière."
            },
            "CAF brute sur RRF": {
                "colonnes": ["CAF brute / RRF Commune", "CAF brute / RRF Moyenne"],
                "unite": "%",
                "description": "Ratio clé mesurant la part des recettes disponible pour l'investissement. Un ratio > 7% est considéré comme sain."
            },
            "CAF nette sur RRF": {
                "colonnes": ["CAF nette / RRF Commune", "CAF nette / RRF Moyenne"],
                "unite": "%",
                "description": "CAF après remboursement de la dette. Mesure la capacité d'investissement réelle de la commune."
            }
        }
        
        st.markdown('<div class="carousel-container">', unsafe_allow_html=True)
        
        # Navigation
        col_title, col_nav = st.columns([4, 1])
        
        current_index = st.session_state.carousel_index
        current_key = list(indicateurs.keys())[current_index]
        current_data = indicateurs[current_key]
        current_colonnes = current_data["colonnes"]
        
        with col_title:
            st.markdown(f'<div class="carousel-title">{current_key}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="carousel-description">{current_data["description"]}</div>', unsafe_allow_html=True)
        
        with col_nav:
            col_prev, col_next = st.columns(2)
            with col_prev:
                if st.button("←", key="prev"):
                    st.session_state.carousel_index = (current_index - 1) % len(indicateurs)
                    st.rerun()
            with col_next:
                if st.button("→", key="next"):
                    st.session_state.carousel_index = (current_index + 1) % len(indicateurs)
                    st.rerun()
        
        # Tableau avec formatage
        df_display = caf.set_index('Année')[current_colonnes].copy()
        if current_data["unite"] == "€":
            df_display = df_display.round(0).astype(int)
        else:
            df_display = df_display.round(1)
        
        st.dataframe(df_display.T, use_container_width=True)
        
        # Graphique avec zone de référence
        df_plot = caf[current_colonnes].copy()
        df_plot['Année'] = caf['Année']
        df_plot = df_plot.melt(id_vars="Année", var_name="Indicateur", value_name="Valeur")
        
        fig = go.Figure()
        
        colors = ['#1a1a1a', '#999999']
        for idx, indicateur in enumerate(df_plot['Indicateur'].unique()):
            data = df_plot[df_plot['Indicateur'] == indicateur]
            fig.add_trace(go.Scatter(
                x=data['Année'],
                y=data['Valeur'],
                mode='lines+markers',
                name=indicateur.replace('Commune', '🏛️').replace('Moyenne', '📊'),
                line=dict(color=colors[idx], width=3 if idx == 0 else 2),
                marker=dict(size=8 if idx == 0 else 6, color=colors[idx])
            ))
        
        # Zones de référence pour les %
        if current_data["unite"] == "%":
            fig.add_hrect(y0=10, y1=20, fillcolor="#10b981", opacity=0.05,
                         annotation_text="Zone excellente", annotation_position="top left",
                         line_width=0)
            fig.add_hrect(y0=7, y1=10, fillcolor="#3b82f6", opacity=0.05,
                         annotation_text="Zone correcte", annotation_position="top left",
                         line_width=0)
            fig.add_hrect(y0=5, y1=7, fillcolor="#f59e0b", opacity=0.05,
                         annotation_text="Zone fragile", annotation_position="top left",
                         line_width=0)
        
        fig.update_layout(
            template="plotly_white",
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="DM Sans", size=12, color="#666"),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.15,
                xanchor="center",
                x=0.5
            ),
            xaxis=dict(showgrid=False, showline=True, linewidth=1, linecolor='#e8e8e8'),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='#f5f5f5', showline=False),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Stats rapides sur l'indicateur
        col_min, col_max, col_moy = st.columns(3)
        valeur_commune = caf[current_colonnes[0]]
        
        with col_min:
            st.metric("Minimum", f"{valeur_commune.min():.1f} {current_data['unite']}")
        with col_max:
            st.metric("Maximum", f"{valeur_commune.max():.1f} {current_data['unite']}")
        with col_moy:
            st.metric("Moyenne", f"{valeur_commune.mean():.1f} {current_data['unite']}")
        
        # Dots navigation
        dots_html = '<div class="nav-dots">'
        for i in range(len(indicateurs)):
            active_class = "active" if i == current_index else ""
            dots_html += f'<span class="dot {active_class}"></span>'
        dots_html += '</div>'
        st.markdown(dots_html, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # DONNÉES COMPLÈTES
        with st.expander("📋 Voir toutes les données", expanded=False):
            st.dataframe(
                caf.style.format({
                    'Population': '{:,.0f}',
                    'CAF brute / habitant Commune': '{:.0f}€',
                    'CAF brute / habitant Moyenne': '{:.0f}€',
                    'CAF brute / RRF Commune': '{:.1f}%',
                    'CAF brute / RRF Moyenne': '{:.1f}%',
                    'CAF nette / RRF Commune': '{:.1f}%',
                    'CAF nette / RRF Moyenne': '{:.1f}%'
                }),
                use_container_width=True,
                height=400
            )
            
            # Bouton export
            if st.button("📥 Exporter en CSV"):
                csv = caf.to_csv(index=False)
                st.download_button(
                    label="Télécharger les données",
                    data=csv,
                    file_name=f"caf_{commune_selectionnee}_{min(annees)}-{max(annees)}.csv",
                    mime="text/csv"
                )

if __name__ == "__main__":
    pass