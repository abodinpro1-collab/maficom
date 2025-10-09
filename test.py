import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from functools import lru_cache
from difflib import SequenceMatcher

# Configuration de la page
st.set_page_config(
    page_title="Finances Communales", 
    page_icon="💰", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design moderne
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.8rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    
    .kpi-container {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 1rem;
        border-radius: 0.8rem;
        margin: 1rem 0;
    }
    
    .section-header {
        background: linear-gradient(90deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1.5rem 0 1rem 0;
        font-size: 1.2rem;
        font-weight: bold;
    }
    
    .warning-box {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    
    .success-box {
        background: #d1fae5;
        border: 1px solid #10b981;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Palette de couleurs cohérente
COLORS = {
    'commune': '#1e40af',      # Bleu foncé pour la commune
    'strate': '#60a5fa',       # Bleu clair pour la strate
    'positive': '#10b981',     # Vert pour les valeurs positives
    'negative': '#ef4444',     # Rouge pour les valeurs négatives
    'neutral': '#6b7280'       # Gris pour les valeurs neutres
}

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

@st.cache_resource
def get_fetcher():
    return RobustCommuneFetcher()

def fetch_commune_fonctionnement(commune, annee, departement=None):
    """Version robuste du fetch fonctionnement - AUTONOME"""
    
    fetcher = get_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
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
                continue
            
            df = pd.DataFrame(data["results"])
            colonnes_voulu = ['an', 'pop1', 'prod', 'charge', 'fprod', 'mprod',
                              'fcharge', 'mcharge', 'fdgf', 'mdgf', 'fperso', 'mperso']
            colonnes_existantes = [c for c in colonnes_voulu if c in df.columns]
            
            if not colonnes_existantes:
                continue
                
            df_fonctionnement = df[colonnes_existantes].copy()

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
            
            # Calculs des ratios
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
            
            # Calculs supplémentaires
            if "Recettes de fonctionnement" in df_fonctionnement.columns and "Dépenses de fonctionnement" in df_fonctionnement.columns:
                df_fonctionnement["Résultat de fonctionnement"] = (
                    df_fonctionnement["Recettes de fonctionnement"] - df_fonctionnement["Dépenses de fonctionnement"]
                )
                df_fonctionnement["Taux d'épargne"] = (
                    df_fonctionnement["Résultat de fonctionnement"] / df_fonctionnement["Recettes de fonctionnement"] * 100
                ).round(2)
            
            if commune_nom != commune:
                st.info(f"🔍 Données trouvées pour '{commune}' via '{commune_nom}'")
            
            return df_fonctionnement
            
        except requests.RequestException:
            continue
    
    return pd.DataFrame()

def create_kpi_cards(df, annee_reference):
    """Crée des cartes KPI pour l'année de référence"""
    if annee_reference not in df.index:
        return
    
    data = df.loc[annee_reference]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h4>👥 Population</h4>
            <h2>{int(data.get('Population', 0)):,}</h2>
            <small>habitants</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        resultat = data.get('Résultat de fonctionnement', 0)
        color = COLORS['positive'] if resultat >= 0 else COLORS['negative']
        st.markdown(f"""
        <div class="metric-card">
            <h4>💰 Résultat de fonctionnement</h4>
            <h2 style="color: {color}">{resultat:,.0f} €</h2>
            <small>{'Excédent' if resultat >= 0 else 'Déficit'}</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        taux_epargne = data.get('Taux d\'épargne', 0)
        color = COLORS['positive'] if taux_epargne >= 10 else COLORS['negative'] if taux_epargne < 5 else COLORS['neutral']
        st.markdown(f"""
        <div class="metric-card">
            <h4>📊 Taux d'épargne</h4>
            <h2 style="color: {color}">{taux_epargne:.1f}%</h2>
            <small>{'Excellent' if taux_epargne >= 15 else 'Bon' if taux_epargne >= 10 else 'Moyen' if taux_epargne >= 5 else 'Faible'}</small>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        ratio_personnel = data.get('Ratio Dépenses personnel / Dépenses fonctionnement', 0)
        color = COLORS['positive'] if ratio_personnel <= 50 else COLORS['negative'] if ratio_personnel > 70 else COLORS['neutral']
        st.markdown(f"""
        <div class="metric-card">
            <h4>👔 Part des dépenses de personnel</h4>
            <h2 style="color: {color}">{ratio_personnel:.1f}%</h2>
            <small>{'Maîtrisé' if ratio_personnel <= 50 else 'Élevé' if ratio_personnel > 70 else 'Correct'}</small>
        </div>
        """, unsafe_allow_html=True)

def create_evolution_chart(df, colonnes, titre, format_y="€"):
    """Crée un graphique d'évolution avec la palette de couleurs définie"""
    df_plot = df[colonnes].reset_index().sort_values("Année").melt(
        id_vars="Année", var_name="Indicateur", value_name="Valeur"
    )
    
    fig = go.Figure()
    
    for i, indicateur in enumerate(df_plot['Indicateur'].unique()):
        data_ind = df_plot[df_plot['Indicateur'] == indicateur]
        
        # Attribution des couleurs selon le type d'indicateur
        if 'Moyenne' in indicateur or 'strate' in indicateur:
            color = COLORS['strate']
            line_style = 'dash'
        else:
            color = COLORS['commune']
            line_style = 'solid'
        
        fig.add_trace(go.Scatter(
            x=data_ind['Année'],
            y=data_ind['Valeur'],
            mode='lines+markers',
            name=indicateur,
            line=dict(color=color, width=3, dash=line_style),
            marker=dict(size=8, color=color),
            hovertemplate=f'<b>%{{fullData.name}}</b><br>Année: %{{x}}<br>Valeur: %{{y:,.0f}} {format_y}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(text=titre, x=0.5, font=dict(size=16, color=COLORS['commune'])),
        xaxis_title="Année",
        yaxis_title=f"Valeur ({format_y})",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400
    )
    
    return fig

def create_comparison_chart(df, col_commune, col_strate, titre):
    """Crée un graphique de comparaison commune vs strate"""
    if col_commune not in df.columns or col_strate not in df.columns:
        return None
    
    df_sorted = df[[col_commune, col_strate]].reset_index().sort_values("Année")
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Commune',
        x=df_sorted['Année'],
        y=df_sorted[col_commune],
        marker_color=COLORS['commune'],
        opacity=0.8
    ))
    
    fig.add_trace(go.Bar(
        name='Moyenne de la strate',
        x=df_sorted['Année'],
        y=df_sorted[col_strate],
        marker_color=COLORS['strate'],
        opacity=0.8
    ))
    
    fig.update_layout(
        title=dict(text=titre, x=0.5, font=dict(size=16, color=COLORS['commune'])),
        xaxis_title="Année",
        yaxis_title="Valeur (€/habitant)",
        template="plotly_white",
        barmode='group',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_dashboard_summary(df):
    """Crée un tableau de bord de synthèse"""
    st.markdown('<div class="section-header">📊 Tableau de bord synthétique</div>', unsafe_allow_html=True)
    
    # Calculs des évolutions
    annees = sorted(df.index)
    if len(annees) >= 2:
        evolution_data = []
        
        for col in ['Population', 'Recettes réelles de fonctionnement / habitant', 
                   'Dépenses réelles de fonctionnement / habitant', 'Taux d\'épargne']:
            if col in df.columns:
                val_recent = df.loc[annees[-1], col]
                val_ancien = df.loc[annees[0], col]
                evolution = ((val_recent - val_ancien) / val_ancien * 100) if val_ancien != 0 else 0
                
                evolution_data.append({
                    'Indicateur': col,
                    'Valeur actuelle': val_recent,
                    'Évolution (%)': f"{evolution:+.1f}%",
                    'Tendance': '📈' if evolution > 0 else '📉' if evolution < 0 else '➡️'
                })
        
        if evolution_data:
            df_evolution = pd.DataFrame(evolution_data)
            st.dataframe(df_evolution, use_container_width=True, hide_index=True)

def run(commune=None, annees=None, departement=None):
    """Fonction principale avec design amélioré"""
    
    # En-tête principal
    st.markdown("""
    <div class="main-header">
        <h1>💰 Analyse Financière des Communes</h1>
        <p>Explorez les données financières de fonctionnement des communes françaises</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar pour les paramètres
    with st.sidebar:
        st.header("🔧 Paramètres")
        commune_selectionnee = st.text_input("🏘️ Nom de la commune :", value=commune or "RENAGE")
        departement_selectionne = st.text_input('🗺️ Département (optionnel) :', value=departement or "")
        annees = st.multiselect(
            "📅 Années à analyser :",
            options=list(range(2023, 2018, -1)),
            default=annees or list(range(2023, 2018, -1))
        )
        
        st.markdown("---")
        st.markdown("### 💡 Aide")
        st.markdown("""
        **Indicateurs clés :**
        - 🔵 **Bleu foncé** : Données de la commune
        - 🔵 **Bleu clair** : Moyenne de la strate
        - 📊 **Taux d'épargne** : (Recettes - Dépenses) / Recettes
        """)

    if not commune_selectionnee or not annees:
        st.warning("⚠️ Veuillez saisir une commune et sélectionner des années.")
        return

    # Récupération des données
    df_list = []
    fetcher = get_fetcher()
    variants = fetcher.find_commune_variants(commune_selectionnee, departement_selectionne)
    
    if len(variants) > 1:
        variant_names = [v["nom"] for v in variants]
        st.info(f"🔍 Variantes détectées: {', '.join(set(variant_names))}")
    
    progress_bar = st.progress(0)
    for i, annee in enumerate(annees):
        df_annee = fetch_commune_fonctionnement(commune_selectionnee, annee, departement_selectionne)
        if not df_annee.empty:
            df_list.append(df_annee)
        progress_bar.progress((i + 1) / len(annees))
    
    progress_bar.empty()

    if not df_list:
        st.error("❌ Aucune donnée disponible pour cette commune et ces années.")
        return

    # Consolidation des données
    fonctionnement = pd.concat(df_list, ignore_index=True)
    fonctionnement.set_index("Année", inplace=True)
    
    st.markdown(f"""
    <div class="success-box">
        ✅ <strong>Données récupérées avec succès :</strong> {len(df_list)} années sur {len(annees)} demandées
    </div>
    """, unsafe_allow_html=True)

    # KPI Cards
    annee_reference = max(fonctionnement.index)
    create_kpi_cards(fonctionnement, annee_reference)
    
    # Tableau de bord synthétique
    create_dashboard_summary(fonctionnement)

    # Graphiques principaux
    st.markdown('<div class="section-header">📈 Analyses détaillées</div>', unsafe_allow_html=True)
    
    # Organisation en onglets
    tab1, tab2, tab3, tab4 = st.tabs(["💰 Vue d'ensemble", "👥 Par habitant", "📊 Ratios", "🔍 Détails"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            # Recettes vs Dépenses
            if all(col in fonctionnement.columns for col in ['Recettes de fonctionnement', 'Dépenses de fonctionnement']):
                fig = create_evolution_chart(
                    fonctionnement, 
                    ['Recettes de fonctionnement', 'Dépenses de fonctionnement'],
                    "Évolution Recettes vs Dépenses"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Évolution de la population
            if 'Population' in fonctionnement.columns:
                fig = create_evolution_chart(
                    fonctionnement, 
                    ['Population'],
                    "Évolution de la Population",
                    "habitants"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            # Recettes par habitant
            cols_recettes = ['Recettes réelles de fonctionnement / habitant',
                           'Moyenne de la strate Recettes réelles fonctionnement / habitant']
            if all(col in fonctionnement.columns for col in cols_recettes):
                fig = create_comparison_chart(
                    fonctionnement,
                    cols_recettes[0],
                    cols_recettes[1],
                    "Recettes réelles de fonctionnement / habitant"
                )
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Dépenses par habitant
            cols_depenses = ['Dépenses réelles de fonctionnement / habitant',
                           'Moyenne de la strate Dépenses réelles fonctionnement / habitant']
            if all(col in fonctionnement.columns for col in cols_depenses):
                fig = create_comparison_chart(
                    fonctionnement,
                    cols_depenses[0],
                    cols_depenses[1],
                    "Dépenses réelles de fonctionnement / habitant"
                )
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            # Taux d'épargne
            if 'Taux d\'épargne' in fonctionnement.columns:
                fig = create_evolution_chart(
                    fonctionnement, 
                    ['Taux d\'épargne'],
                    "Évolution du Taux d'épargne",
                    "%"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Ratio personnel
            cols_ratio = ['Ratio Dépenses personnel / Dépenses fonctionnement',
                         'Ratio Moyenne Dépenses personnel / Dépenses fonctionnement']
            if all(col in fonctionnement.columns for col in cols_ratio):
                fig = create_evolution_chart(
                    fonctionnement, 
                    cols_ratio,
                    "Part des dépenses de personnel",
                    "%"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        # Tableaux détaillés par catégorie - STRUCTURE ORIGINALE CONSERVÉE
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
                                   "Moyenne de la strate Dépenses de personnel / habitant"],
            "Dépenses de personnel / DRF": ["Ratio Dépenses personnel / Dépenses fonctionnement",
                                   "Ratio Moyenne Dépenses personnel / Dépenses fonctionnement"]
        }

        for titre, colonnes in mini_tableaux.items():
            with st.expander(f"📋 {titre}"):
                colonnes_existantes = [col for col in colonnes if col in fonctionnement.columns]
                if colonnes_existantes:
                    st.dataframe(
                        fonctionnement[colonnes_existantes].T.style.format("{:,.0f}"),
                        use_container_width=True
                    )

if __name__ == "__main__":
    run()