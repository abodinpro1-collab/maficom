import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime
import tempfile
import os
import kaleido
# -----------------------
# Fonctions de récupération des données (reprises de vos modules)
# -----------------------

def fetch_commune_fonctionnement(commune, annees):
    """Récupère les données de fonctionnement"""
    df_list = []
    for annee in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f'an="{annee}" AND inom="{commune}"', "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()
        
        if "results" not in data or not data["results"]:
            continue
        
        df = pd.DataFrame(data["results"])
        colonnes_voulu = ['an', 'pop1', 'prod', 'charge', 'fprod', 'mprod',
                          'fcharge', 'mcharge', 'fdgf', 'mdgf', 'fperso', 'mperso']
        colonnes_existantes = [c for c in colonnes_voulu if c in df.columns]
        df_fonctionnement = df[colonnes_existantes].copy()

        # Renommer colonnes
        df_fonctionnement.rename(columns={
            "an": "Année",
            "pop1": "Population",
            "prod": "Recettes de fonctionnement",
            "charge": "Dépenses de fonctionnement",
            "fprod": "Recettes réelles fonctionnement / hab",
            "mprod": "Moyenne strate Recettes / hab",
            "fcharge": "Dépenses réelles fonctionnement / hab",
            "mcharge": "Moyenne strate Dépenses / hab",
            "fdgf": "DGF / habitant",
            "mdgf": "Moyenne strate DGF / hab",
            "fperso": "Dépenses personnel / hab",
            "mperso": "Moyenne strate Personnel / hab"
        }, inplace=True)
        
        # Ratios
        df_fonctionnement["Ratio Personnel/DRF Commune"] = (
            df_fonctionnement["Dépenses personnel / hab"] /
            df_fonctionnement["Dépenses réelles fonctionnement / hab"] * 100
        ).round(2)
        
        df_fonctionnement["Ratio Personnel/DRF Moyenne"] = (
            df_fonctionnement["Moyenne strate Personnel / hab"] /
            df_fonctionnement["Moyenne strate Dépenses / hab"] * 100
        ).round(2)
        
        df_list.append(df_fonctionnement)
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

def fetch_commune_caf(commune, annees):
    """Récupère les données CAF"""
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
            'fcaf': 'CAF brute / hab Commune',
            'mcaf': 'CAF brute / hab Moyenne'
        }, inplace=True)

        dfs.append(df_caf_final)

    if dfs:
        result = pd.concat(dfs, ignore_index=True)
        result.sort_values("Année", inplace=True)
        return result
    else:
        return pd.DataFrame()

def fetch_commune_fiscalite(commune, annees):
    """Récupère les données de fiscalité"""
    df_list = []
    for annee in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f'an=\"{annee}\" AND inom=\"{commune}\"', "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()

        if "results" not in data or not data["results"]:
            continue

        df = pd.DataFrame(data["results"])
        colonnes = ['an', 'fimpo1', 'mimpo1', 'fprod', 'mprod', 'tth', 'tmth', 'tfb', 'tmfb', 'tfnb', 'tmfnb']
        colonnes_existantes = [c for c in colonnes if c in df.columns]
        df_fiscalite = df[colonnes_existantes].copy()

        # Calcul des ratios Impôts locaux sur RRF
        if 'fimpo1' in df_fiscalite.columns and 'fprod' in df_fiscalite.columns:
            df_fiscalite['Impôts/RRF Commune'] = (df_fiscalite['fimpo1'] / df_fiscalite['fprod'] * 100).round(2)
        if 'mimpo1' in df_fiscalite.columns and 'mprod' in df_fiscalite.columns:
            df_fiscalite['Impôts/RRF Moyenne'] = (df_fiscalite['mimpo1'] / df_fiscalite['mprod'] * 100).round(2)

        # Renommer colonnes pour affichage
        rename_dict = {
            'an': 'Année',
            'fimpo1': 'Impôts / hab Commune',
            'mimpo1': 'Impôts / hab Moyenne',
            'tth': 'Taux TH Commune',
            'tmth': 'Taux TH Moyenne',
            'tfb': 'Taux TFB Commune',
            'tmfb': 'Taux TFB Moyenne',
            'tfnb': 'Taux TFNB Commune',
            'tmfnb': 'Taux TFNB Moyenne'
        }
        df_fiscalite.rename(columns=rename_dict, inplace=True)
        df_list.append(df_fiscalite)
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

def fetch_commune_endettement(commune, annees):
    """Récupère les données d'endettement"""
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
            df['Dette / hab Commune'] = df['fdette']
            df['Dette / hab Moyenne'] = df['mdette']
            df['Dette / RRF Commune'] = (df['fdette'] / df['fcaf'] * 100).round(2)
            df['Dette / RRF Moyenne'] = (df['mdette'] / df['mcaf'] * 100).round(2)
            df['Dette en années CAF Commune'] = (df['fdette'] / df['fcaf']).round(2)
            df['Dette en années CAF Moyenne'] = (df['mdette'] / df['mcaf']).round(2)

            df.rename(columns={'an': 'Année'}, inplace=True)
            df_list.append(df)
    if df_list:
        return pd.concat(df_list, ignore_index=True).sort_values("Année")
    return pd.DataFrame()

def fetch_commune_investissement(commune, annees):
    """Récupère les données d'investissement"""
    df_list = []
    for an in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f'an="{an}" AND inom="{commune}"', "limit": 100}
        r = requests.get(url, params=params)
        data = r.json().get("results", [])
        if data:
            df = pd.DataFrame(data)
            cols = ['an', 'fequip', 'mequip', 'fprod', 'mprod']
            df_exist = [c for c in cols if c in df.columns]
            df = df[df_exist].copy()

            # Mini-tableaux
            df['Équipement / hab Commune'] = df['fequip']
            df['Équipement / hab Moyenne'] = df['mequip']
            df['Équipement / RRF Commune'] = (df['fequip'] / df['fprod'] * 100).round(2)
            df['Équipement / RRF Moyenne'] = (df['mequip'] / df['mprod'] * 100).round(2)

            df.rename(columns={'an': 'Année'}, inplace=True)
            df_list.append(df)
    if df_list:
        return pd.concat(df_list, ignore_index=True).sort_values("Année")
    return pd.DataFrame()

def fetch_commune_fdr(commune, annees):
    """Récupère les données de fonds de roulement"""
    df_list = []
    for annee in annees:
        url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
        params = {"where": f"an='{annee}' AND inom='{commune}'", "limit": 100}
        response = requests.get(url, params=params)
        data = response.json()

        if "results" not in data or not data["results"]:
            continue

        df = pd.DataFrame(data["results"])
        colonnes = ['an', 'ffdr', 'mfdr', 'fcharge', 'mcharge']
        colonnes_existantes = [c for c in colonnes if c in df.columns]
        df_fr = df[colonnes_existantes].copy()

        # Renommage pour lisibilité
        df_fr.rename(columns={
            'an': 'Année',
            'ffdr': 'FDR / hab Commune',
            'mfdr': 'FDR / hab Moyenne',
            'fcharge': 'Charges fonct / hab Commune',
            'mcharge': 'Charges fonct / hab Moyenne'
        }, inplace=True)

        # Calcul fonds de roulement en jours de charges
        df_fr['FDR en jours DRF Commune'] = (
            df_fr['FDR / hab Commune'] / df_fr['Charges fonct / hab Commune'] * 365
        ).round(2)
        df_fr['FDR en jours DRF Moyenne'] = (
            df_fr['FDR / hab Moyenne'] / df_fr['Charges fonct / hab Moyenne'] * 365
        ).round(2)

        # Suppression colonnes intermédiaires
        df_fr.drop(columns=['Charges fonct / hab Commune', 'Charges fonct / hab Moyenne'], inplace=True)
        df_list.append(df_fr)
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def get_all_commune_data(commune, annees):
    """Récupère toutes les données financières pour une commune"""
    data = {}
    data['fonctionnement'] = fetch_commune_fonctionnement(commune, annees)
    data['caf'] = fetch_commune_caf(commune, annees)
    data['fiscalite'] = fetch_commune_fiscalite(commune, annees)
    data['endettement'] = fetch_commune_endettement(commune, annees)
    data['investissement'] = fetch_commune_investissement(commune, annees)
    data['fdr'] = fetch_commune_fdr(commune, annees)
    return data

import plotly.io as pio
import tempfile
import os
import streamlit as st

import plotly.express as px
import plotly.io as pio
import tempfile
import os
import streamlit as st
import subprocess
import sys

def ensure_kaleido_chrome():
    """
    Vérifie si Kaleido + Chrome sont installés.
    Si non, tente de les installer automatiquement.
    """
    try:
        import kaleido
    except ImportError:
        st.info("📥 Installation de kaleido...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "kaleido"])
    
    try:
        # Test simple pour voir si Kaleido peut exporter PNG
        import plotly.io as pio
        fig_test = px.line(x=[1, 2], y=[1, 2])
        fig_test.to_image(format="png")
    except Exception:
        st.info("⚙ Installation de Chrome pour Kaleido...")
        try:
            subprocess.check_call([sys.executable, "-m", "kaleido"])
        except Exception:
            st.error("❌ Impossible d'installer Chrome pour Kaleido. Veuillez l'installer manuellement.")
            return False
    return True


def create_chart_image(df, colonnes, titre):
    """Crée un graphique Plotly et le sauvegarde comme image temporaire"""
    if df.empty or not colonnes:
        return None
    
    try:
        # Vérifier que kaleido est disponible
        import kaleido
        
        # Préparation des données pour le graphique
        df_plot = df[colonnes].reset_index().melt(
            id_vars="Année", var_name="Indicateur", value_name="Valeur"
        )
        
        # Vérifier qu'il y a des données à afficher
        if df_plot.empty or df_plot['Valeur'].isna().all():
            return None
        
        # Couleurs personnalisées : bleu foncé et bleu clair
        colors_palette = ['#1f4e79', '#87ceeb']  # Bleu foncé, bleu clair
        
        # Création du graphique Plotly
        fig = px.line(
            df_plot,
            x="Année",
            y="Valeur",
            color="Indicateur",
            markers=True,
            title=f"Évolution - {titre}",
            color_discrete_sequence=colors_palette
        )
        
        fig.update_traces(mode="lines+markers", line=dict(width=3), marker=dict(size=8))
        fig.update_layout(
            template="plotly_white", 
            hovermode="x unified",
            width=600,
            height=450,  # Augmenté pour la légende en bas
            title_x=0.5,
            title_font_size=14,
            font=dict(size=11),
            showlegend=True,
            legend=dict(
                orientation="h",  # Légende horizontale
                yanchor="top",
                y=-0.15,  # Positionner en dessous du graphique
                xanchor="center",
                x=0.5,
                font=dict(size=10)
            ),
            margin=dict(l=60, r=60, t=60, b=80)  # Marges ajustées pour la légende
        )
        
        # Sauvegarder l'image temporairement
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_path = temp_file.name
        temp_file.close()
        
        # Export de l'image avec gestion d'erreur
        pio.write_image(fig, temp_path, format='png', width=600, height=450, scale=2, engine='kaleido')
        
        # Vérifier que le fichier a été créé
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            print(f"✅ Graphique créé: {titre} -> {temp_path}")
            return temp_path
        else:
            print(f"❌ Échec création: {titre}")
            return None
    
    except ImportError:
        print("❌ Kaleido non installé - graphiques désactivés")
        return None
    except Exception as e:
        print(f"❌ Erreur création graphique {titre}: {e}")
        return None


def create_pdf_report(commune, annees):
    """Crée un rapport PDF professionnel avec tous les indicateurs financiers et graphiques"""
    
    # Import local pour éviter les conflits
    from io import BytesIO as PDFBytesIO
    
    # Récupération de toutes les données
    with st.spinner("📄 Génération du rapport PDF avec graphiques..."):
        all_data = get_all_commune_data(commune, annees)
    
    # Liste pour stocker les fichiers temporaires à nettoyer
    temp_files = []
    
    # Création du PDF en mémoire
    pdf_buffer = PDFBytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, leftMargin=50, rightMargin=50)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=30,
        spaceAfter=50,
        textColor=colors.darkblue,
        alignment=1  # Center

    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        fontName='Helvetica-Bold',
        parent=styles['Heading2'],
        fontSize=30,
        spaceAfter=60,
        textColor=colors.navy,
        alignment=1
    )
    
    sub_heading_style = ParagraphStyle(
        'SubHeading',
        fontName='Helvetica-Bold',
        parent=styles['Heading3'],
        fontSize=26,
        spaceAfter=50,
        textColor=colors.darkgrey
    )
    
    # Contenu du PDF
    story = []
    
    # Page de titre
    story.append(Paragraph(f"Focus Financier", title_style))
    story.append(Paragraph(f"Analyse financière de la commune de {commune.upper()}", styles['Normal']))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Période : {min(annees)} - {max(annees)}", styles['Normal']))
    story.append(Paragraph(f"Date du rapport : {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(PageBreak())
    
    # Synthèse exécutive
    if not all_data['fonctionnement'].empty:
        story.append(Paragraph("SYNTHÈSE EXÉCUTIVE", heading_style))
        
        # Tableau de synthèse
        synthese_data = []
        synthese_data.append(['Indicateur', 'Commune', 'Moyenne Strate'])
        
        # Population
        pop_data = all_data['fonctionnement'].sort_values('Année')
        if len(pop_data) > 0:
            derniere_pop = pop_data.iloc[-1]['Population']
            if len(pop_data) > 1:
                evolution_pop = derniere_pop - pop_data.iloc[0]['Population']
                synthese_data.append(['Population', f"{derniere_pop:,.0f} hab.", f"{evolution_pop:+.0f}"])
            else:
                synthese_data.append(['Population', f"{derniere_pop:,.0f} hab.", "N/A"])
        
       # FONCTIONNEMENT
        if not all_data['fonctionnement'].empty:
            fonc_data = all_data['fonctionnement'].sort_values('Année')
            derniere_fonc = fonc_data.iloc[-1]
            
            rec_commune = derniere_fonc['Recettes réelles fonctionnement / hab']
            rec_moyenne = derniere_fonc['Moyenne strate Recettes / hab']
            synthese_data.append(['Recettes réelles fonct. / hab', f"{rec_commune:.0f} €", f"{rec_moyenne:.0f} €"])
            
            dep_commune = derniere_fonc['Dépenses réelles fonctionnement / hab']
            dep_moyenne = derniere_fonc['Moyenne strate Dépenses / hab']
            synthese_data.append(['Dépenses réelles fonct. / hab', f"{dep_commune:.0f} €", f"{dep_moyenne:.0f} €"])
            
            perso_commune = derniere_fonc['Dépenses personnel / hab']
            perso_moyenne = derniere_fonc['Moyenne strate Personnel / hab']
            synthese_data.append(['Dépenses personnel / hab', f"{perso_commune:.0f} €", f"{perso_moyenne:.0f} €"])
            
            ratio_commune = derniere_fonc['Ratio Personnel/DRF Commune']
            ratio_moyenne = derniere_fonc['Ratio Personnel/DRF Moyenne']
            synthese_data.append(['Ratio Personnel / DRF', f"{ratio_commune:.1f} %", f"{ratio_moyenne:.1f} %"])
        
        # CAF
        if not all_data['caf'].empty:
            caf_data = all_data['caf'].sort_values('Année')
            derniere_caf = caf_data.iloc[-1]
            
            caf_commune = derniere_caf['CAF brute / hab Commune']
            caf_moyenne = derniere_caf['CAF brute / hab Moyenne']
            synthese_data.append(['CAF brute / hab', f"{caf_commune:.0f} €", f"{caf_moyenne:.0f} €"])
            
            cafbrut_commune = derniere_caf['CAF brute / RRF Commune']
            cafbrut_moyenne = derniere_caf['CAF brute / RRF Moyenne']
            synthese_data.append(['CAF brute / RRF', f"{cafbrut_commune:.1f} %", f"{cafbrut_moyenne:.1f} %"])
            
            cafnette_commune = derniere_caf['CAF nette / RRF Commune']
            cafnette_moyenne = derniere_caf['CAF nette / RRF Moyenne']
            synthese_data.append(['CAF nette / RRF', f"{cafnette_commune:.1f} %", f"{cafnette_moyenne:.1f} %"])
        
        # FISCALITÉ
        if not all_data['fiscalite'].empty:
            fisc_data = all_data['fiscalite'].sort_values('Année')
            derniere_fisc = fisc_data.iloc[-1]
            
            impots_commune = derniere_fisc['Impôts / hab Commune']
            impots_moyenne = derniere_fisc['Impôts / hab Moyenne']
            synthese_data.append(['Impôts locaux / hab', f"{impots_commune:.0f} €", f"{impots_moyenne:.0f} €"])
            
            taux_th_commune = derniere_fisc['Taux TH Commune']
            taux_th_moyenne = derniere_fisc['Taux TH Moyenne']
            synthese_data.append(['Taux taxe habitation', f"{taux_th_commune:.2f} %", f"{taux_th_moyenne:.2f} %"])
            
            taux_tfb_commune = derniere_fisc['Taux TFB Commune']
            taux_tfb_moyenne = derniere_fisc['Taux TFB Moyenne']
            synthese_data.append(['Taux foncier bâti', f"{taux_tfb_commune:.2f} %", f"{taux_tfb_moyenne:.2f} %"])
            
            taux_tfnb_commune = derniere_fisc['Taux TFNB Commune']
            taux_tfnb_moyenne = derniere_fisc['Taux TFNB Moyenne']
            synthese_data.append(['Taux foncier non bâti', f"{taux_tfnb_commune:.2f} %", f"{taux_tfnb_moyenne:.2f} %"])
        
        # ENDETTEMENT
        if not all_data['endettement'].empty:
            dette_data = all_data['endettement'].sort_values('Année')
            derniere_dette = dette_data.iloc[-1]
            
            dette_commune = derniere_dette['Dette / hab Commune']
            dette_moyenne = derniere_dette['Dette / hab Moyenne']
            synthese_data.append(['Dette / hab', f"{dette_commune:.0f} €", f"{dette_moyenne:.0f} €"])
            
            dette_ans_commune = derniere_dette['Dette en années CAF Commune']
            dette_ans_moyenne = derniere_dette['Dette en années CAF Moyenne']
            synthese_data.append(['Dette en années CAF', f"{dette_ans_commune:.1f} ans", f"{dette_ans_moyenne:.1f} ans"])

        #FDR
        if not all_data['fdr'].empty:
            fdr_data = all_data['fdr'].sort_values('Année')
            derniere_fdr = fdr_data.iloc[-1]
            
            fdr_commune = derniere_fdr['FDR / hab Commune']
            fdr_moyenne = derniere_fdr['FDR / hab Moyenne']
            synthese_data.append(['Fonds de roulement / hab', f"{fdr_commune:.0f} €", f"{fdr_moyenne:.0f} €"])
            
            fdr_jours_commune = derniere_fdr['FDR en jours DRF Commune']
            fdr_jours_moyenne = derniere_fdr['FDR en jours DRF Moyenne']
            synthese_data.append(['Fonds de roulement en jours de DRF', f"{fdr_jours_commune:.1f} jours", f"{fdr_jours_moyenne:.1f} jours"])
        
        # INVESTISSEMENT
        if not all_data['investissement'].empty:
            invest_data = all_data['investissement'].sort_values('Année')
            derniere_invest = invest_data.iloc[-1]
            
            equip_commune = derniere_invest['Équipement / hab Commune']
            equip_moyenne = derniere_invest['Équipement / hab Moyenne']
            synthese_data.append(['Équipement / hab', f"{equip_commune:.0f} €", f"{equip_moyenne:.0f} €"])
        

        # Créer le tableau
        synthese_table = Table(synthese_data)
        synthese_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0),colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(synthese_table)
        story.append(Spacer(1, 20))
    
    # Section par section avec graphiques
    sections_config = {
        'Fonctionnement': {
            'data': all_data['fonctionnement'],
            'mini_tableaux': {
                "Recettes et Dépenses": ["Recettes de fonctionnement", "Dépenses de fonctionnement"],
                "Population": ["Population"],
                "RRF / habitant": ["Recettes réelles fonctionnement / hab", "Moyenne strate Recettes / hab"],
                "DRF / habitant": ["Dépenses réelles fonctionnement / hab", "Moyenne strate Dépenses / hab"],
                "Dotation Globale de Fonctionnement": ["DGF / habitant", "Moyenne strate DGF / hab"],
                "Dépenses de personnel / habitant": ["Dépenses personnel / hab", "Moyenne strate Personnel / hab"],
                "Dépenses de personnel / DRF": ["Ratio Personnel/DRF Commune", "Ratio Personnel/DRF Moyenne"]
            }
        },
        'CAF': {
            'data': all_data['caf'],
            'mini_tableaux': {
                "CAF brute / habitant": ["CAF brute / hab Commune", "CAF brute / hab Moyenne"],
                "CAF brute / RRF": ["CAF brute / RRF Commune", "CAF brute / RRF Moyenne"],
                "CAF nette / RRF": ["CAF nette / RRF Commune", "CAF nette / RRF Moyenne"]
            }
        },
        'Fiscalité': {
            'data': all_data['fiscalite'],
            'mini_tableaux': {
                "Impôts locaux par habitant": ["Impôts / hab Commune", "Impôts / hab Moyenne"],
                "Impôts locaux sur RRF": ["Impôts/RRF Commune", "Impôts/RRF Moyenne"],
                "Taux taxe d'habitation": ["Taux TH Commune", "Taux TH Moyenne"],
                "Taux taxe foncier bâti": ["Taux TFB Commune", "Taux TFB Moyenne"],
                "Taux taxe foncier non bâti": ["Taux TFNB Commune", "Taux TFNB Moyenne"]
            }
        },
        'Endettement': {
            'data': all_data['endettement'],
            'mini_tableaux': {
                "Dette / Habitant": ["Dette / hab Commune", "Dette / hab Moyenne"],
                "Dettes / RRF": ["Dette / RRF Commune", "Dette / RRF Moyenne"],
                "Dette en années de CAF Brute": ["Dette en années CAF Commune", "Dette en années CAF Moyenne"],
                "Part du remboursement de la dette / CAF Brute": [
                    "Part du remboursement de la dette / CAF Brute Commune",
                    "Part du remboursement de la dette / CAF Brute Moyenne"
                ]
            }
        },
        'Investissement': {
            'data': all_data['investissement'],
            'mini_tableaux': {
                "Dépenses d'équipement / habitant": ["Équipement / hab Commune", "Équipement / hab Moyenne"],
                "Dépenses d'équipement / RRF": ["Équipement / RRF Commune", "Équipement / RRF Moyenne"]
            }
        },
        'Fonds de roulement': {
            'data': all_data['fdr'],
            'mini_tableaux': {
                "Fonds de roulement / habitant": ["FDR / hab Commune", "FDR / hab Moyenne"],
                "Fonds de roulement en jours de DRF": ["FDR en jours DRF Commune", "FDR en jours DRF Moyenne"]
            }
        }
    }
    
    for section_name, config in sections_config.items():
        df = config['data']
        mini_tableaux = config['mini_tableaux']
        
        if not df.empty:
            story.append(PageBreak())
            story.append(Paragraph(section_name.upper(), heading_style))
            
            # Préparer le DataFrame avec index Année
            if 'Année' in df.columns:
                df_indexed = df.set_index('Année')
            else:
                df_indexed = df
            
            # Pour chaque mini-tableau dans la section
            for titre, colonnes in mini_tableaux.items():
                # Vérifier que les colonnes existent
                colonnes_existantes = [col for col in colonnes if col in df_indexed.columns]
                
                if colonnes_existantes:
                    story.append(Paragraph(titre, sub_heading_style))
                    
                    # Créer le tableau de données
                    df_subset = df_indexed[colonnes_existantes].copy()
                    
                    # Convertir en liste pour le tableau PDF
                    data = [['Année'] + list(df_subset.columns)]  # En-têtes
                    for annee, row in df_subset.iterrows():
                        formatted_row = [str(int(annee))]  # Année
                        for val in row:
                            if pd.isna(val):
                                formatted_row.append("N/A")
                            elif isinstance(val, (int, float)):
                                formatted_row.append(f"{val:,.1f}")
                            else:
                                formatted_row.append(str(val))
                        data.append(formatted_row)
                    
                    # Créer le tableau
                    table = Table(data)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 10))
                    
                    # Créer et ajouter le graphique
                    chart_path = create_chart_image(df_indexed, colonnes_existantes, titre)
                    if chart_path:
                        temp_files.append(chart_path)
                        try:
                            # Vérifier que l'image existe et a une taille > 0
                            if os.path.exists(chart_path) and os.path.getsize(chart_path) > 1000:  # Au moins 1KB
                                chart_image = Image(chart_path, width=5*inch, height=3.3*inch)
                                story.append(chart_image)
                                story.append(Spacer(1, 15))
                                story.append(PageBreak())
                            else:
                                # Message de diagnostic
                                story.append(Paragraph(f"[Graphique {titre} non généré - données insuffisantes]", styles['Normal']))
                                story.append(Spacer(1, 10))
                        except Exception as e:
                            # Message d'erreur dans le PDF
                            story.append(Paragraph(f"[Erreur graphique {titre}: {str(e)[:50]}]", styles['Normal']))
                            story.append(Spacer(1, 10))
                    else:
                        # Pas de graphique généré
                        story.append(Paragraph(f"[Graphique {titre} non disponible]", styles['Normal']))
                        story.append(Spacer(1, 10))
    
    # Page de notes/méthodologie
    story.append(PageBreak())
    story.append(Paragraph("NOTES MÉTHODOLOGIQUES", heading_style))
    
    notes_text = """
    <b>Sources des données :</b><br/>
    - Direction Générale des Finances Publiques (DGFiP)<br/>
    - SFP COLLECTIVITÉS<br/>
    - Dataset : Comptes individuels des communes<br/><br/>
    """
    
    story.append(Paragraph(notes_text, styles['Normal']))
    
    # Construire le PDF
    try:
        doc.build(story)
        pdf_buffer.seek(0)
        pdf_data = pdf_buffer.getvalue()
        
        # Nettoyage des fichiers temporaires
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return pdf_data
    
    except Exception as e:
        # Nettoyage en cas d'erreur
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        raise e
    """Crée un fichier Excel complet avec tous les indicateurs financiers"""
    
    # Récupération de toutes les données
    with st.spinner("📊 Récupération des données financières..."):
        all_data = get_all_commune_data(commune, annees)
    
    # Création du fichier Excel en mémoire avec BytesIO (solution alternative)
    from io import BytesIO
    
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        
        # Page de synthèse
        if not all_data['fonctionnement'].empty:
            # Création d'un tableau de synthèse
            synthese = all_data['fonctionnement'][['Année', 'Population']].copy()
            
            # Ajout des indicateurs clés de chaque module
            if not all_data['caf'].empty:
                synthese = synthese.merge(
                    all_data['caf'][['Année', 'CAF brute / hab Commune', 'CAF brute / RRF Commune']], 
                    on='Année', how='left'
                )
            
            if not all_data['fiscalite'].empty:
                synthese = synthese.merge(
                    all_data['fiscalite'][['Année', 'Impôts / hab Commune']], 
                    on='Année', how='left'
                )
            
            if not all_data['endettement'].empty:
                synthese = synthese.merge(
                    all_data['endettement'][['Année', 'Dette / hab Commune', 'Dette en années CAF Commune']], 
                    on='Année', how='left'
                )
            
            synthese.to_excel(writer, sheet_name='Synthèse', index=False)
        
        # Écriture des données par module
        if not all_data['fonctionnement'].empty:
            all_data['fonctionnement'].to_excel(writer, sheet_name='Fonctionnement', index=False)
        
        if not all_data['caf'].empty:
            all_data['caf'].to_excel(writer, sheet_name='CAF', index=False)
        
        if not all_data['fiscalite'].empty:
            all_data['fiscalite'].to_excel(writer, sheet_name='Fiscalité', index=False)
        
        if not all_data['endettement'].empty:
            all_data['endettement'].to_excel(writer, sheet_name='Endettement', index=False)
        
        if not all_data['investissement'].empty:
            all_data['investissement'].to_excel(writer, sheet_name='Investissement', index=False)
        
        if not all_data['fdr'].empty:
            all_data['fdr'].to_excel(writer, sheet_name='Fonds de roulement', index=False)
    
    # Récupération des données depuis le buffer
    excel_buffer.seek(0)
    excel_data = excel_buffer.getvalue()
    
def create_excel_report(commune, annees):
    """Crée un fichier Excel complet avec tous les indicateurs financiers"""
    
    # Récupération de toutes les données
    with st.spinner("📊 Récupération des données financières..."):
        all_data = get_all_commune_data(commune, annees)
    
    # Création du fichier Excel en mémoire
    excel_buffer = BytesIO()
    
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        
        # Page de synthèse
        if not all_data['fonctionnement'].empty:
            # Création d'un tableau de synthèse
            synthese = all_data['fonctionnement'][['Année', 'Population']].copy()
            
            # Ajout des indicateurs clés de chaque module
            if not all_data['caf'].empty:
                synthese = synthese.merge(
                    all_data['caf'][['Année', 'CAF brute / hab Commune', 'CAF brute / RRF Commune']], 
                    on='Année', how='left'
                )
            
            if not all_data['fiscalite'].empty:
                synthese = synthese.merge(
                    all_data['fiscalite'][['Année', 'Impôts / hab Commune']], 
                    on='Année', how='left'
                )
            
            if not all_data['endettement'].empty:
                synthese = synthese.merge(
                    all_data['endettement'][['Année', 'Dette / hab Commune', 'Dette en années CAF Commune']], 
                    on='Année', how='left'
                )
            
            synthese.to_excel(writer, sheet_name='Synthèse', index=False)
        
        # Écriture des données par module
        if not all_data['fonctionnement'].empty:
            all_data['fonctionnement'].to_excel(writer, sheet_name='Fonctionnement', index=False)
        
        if not all_data['caf'].empty:
            all_data['caf'].to_excel(writer, sheet_name='CAF', index=False)
        
        if not all_data['fiscalite'].empty:
            all_data['fiscalite'].to_excel(writer, sheet_name='Fiscalité', index=False)
        
        if not all_data['endettement'].empty:
            all_data['endettement'].to_excel(writer, sheet_name='Endettement', index=False)
        
        if not all_data['investissement'].empty:
            all_data['investissement'].to_excel(writer, sheet_name='Investissement', index=False)
        
        if not all_data['fdr'].empty:
            all_data['fdr'].to_excel(writer, sheet_name='Fonds de roulement', index=False)
    
    # Récupération des données depuis le buffer
    excel_buffer.seek(0)
    excel_data = excel_buffer.getvalue()
    
    return excel_data

# -----------------------
# Sidebar navigation
# -----------------------
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choisissez la page :", [
    "Accueil",
    "Fonctionnement",
    "CAF",
    "Fiscalité",
    "Endettement",
    "Investissement",
    "Fonds de roulement"
])

# -----------------------
# Page Accueil
# -----------------------
if page == "Accueil":
    st.title("Bienvenue sur **Focus Financier**")
    st.markdown("""
    **Focus Financier** est un outil d'analyse des comptes des communes françaises, offrant :
    - Consultation des données financières : fonctionnement, CAF, fiscalité, endettement, investissements, fonds de roulement
    - Comparaison avec la moyenne de la strate
    - Graphiques interactifs pour visualiser l'évolution dans le temps
    - **Export Excel complet de toutes les données**
    - **Génération d'un rapport PDF professionnel** avec graphiques et synthèse
    """)

    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        commune_input = st.text_input("Nom de la commune :", value="RENAGE")
    with col2:
        annees = st.multiselect(
            "Sélectionnez les années à afficher :",
            options=list(range(2019, 2025)),  # 2024 inclus maintenant
            default=list(range(2019, 2025))   # 2024 inclus par défaut
        )
    
    # Section Export Excel et PDF
    st.markdown("---")
    st.markdown("### 📊 Export des données")
    
    if commune_input and annees:
        col1, col2, col3 = st.columns(3)
        
        # Export Excel
        with col1:
            if st.button("📄 Rapport Excel", type="primary", use_container_width=True):
                try:
                    excel_data = create_excel_report(commune_input, annees)
                    
                    filename = f"Focus_Financier_{commune_input}_{min(annees)}-{max(annees)}.xlsx"
                    
                    st.download_button(
                        label="📥 Télécharger Excel",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    st.success("✅ Excel généré !")
                    
                except Exception as e:
                    st.error(f"❌ Erreur Excel : {str(e)}")
        
        # Export PDF
        with col2:
            if st.button("📄 Rapport PDF", type="secondary", use_container_width=True):
                try:
                    # Test d'import avant exécution
                    import plotly.io as pio_test
                    
                    pdf_data = create_pdf_report(commune_input, annees)
                    
                    filename_pdf = f"Focus_Financier_{commune_input}_{min(annees)}-{max(annees)}.pdf"
                    
                    st.download_button(
                        label="📥 Télécharger PDF",
                        data=pdf_data,
                        file_name=filename_pdf,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                    st.success("✅ PDF généré !")
                    
                except ImportError as ie:
                    st.error("❌ Dépendance manquante : pip install kaleido")
                    st.info("ℹ️ Kaleido est requis pour les graphiques PDF")
                except Exception as e:
                    st.error(f"❌ Erreur PDF : {str(e)}")
                    st.error("💡 Essayez l'export Excel en attendant")
        
        # Export CSV
        with col3:
            if st.button("📊 Export CSV", use_container_width=True):
                try:
                    all_data = get_all_commune_data(commune_input, annees)
                    if not all_data['fonctionnement'].empty:
                        csv_data = all_data['fonctionnement'].to_csv(index=False)
                        filename_csv = f"Focus_Financier_{commune_input}_fonctionnement.csv"
                        
                        st.download_button(
                            label="📥 Télécharger CSV",
                            data=csv_data,
                            file_name=filename_csv,
                            mime="text/csv",
                            use_container_width=True
                        )
                    else:
                        st.warning("Aucune donnée disponible.")
                except Exception as e:
                    st.error(f"Erreur : {str(e)}")
        
        # Informations sur les formats
        st.markdown("---")
        st.markdown("### 📋 Formats d'export")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📄 Excel :**
            - Toutes les données détaillées
            - 7 onglets (Synthèse + 6 modules)
            - Idéal pour analyses poussées
            - Compatible Office/LibreOffice
            """)
        
        with col2:
            st.markdown("""
            **📄 PDF :**
            - Rapport de présentation
            - Synthèse exécutive
            - Tableaux principaux
            - Prêt pour impression/diffusion
            """)
        
        with col3:
            st.markdown("""
            **📊 CSV :**
            - Données de fonctionnement
            - Format universel
            - Import facile autres outils
            - Léger et rapide
            """)
    else:
        st.info("Veuillez sélectionner une commune et des années pour générer les rapports")
    
# -----------------------
# Import dynamique des pages
# -----------------------
else:
    if page == "Fonctionnement":
        from pages.fonctionnement import run
    elif page == "CAF":
        from pages.caf import run
    elif page == "Fiscalité":
        from pages.fiscalite import run
    elif page == "Endettement":
        from pages.endettements import run
    elif page == "Investissement":
        from pages.investissements import run
    elif page == "Fonds de roulement":
        from pages.fdr import run

    # Exécution de la page sélectionnée
    run()