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

from app_fetchers import (
    fetch_commune_fonctionnement,
    fetch_commune_caf,
    fetch_commune_fiscalite,
    fetch_commune_investissement,
    fetch_commune_endettement,
    fetch_commune_fdr
)

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

@st.cache_data(show_spinner=False)
def search_commune(nom_commune, annee_reference=2024):
    """Recherche une commune et retourne les informations incluant le département"""
    dataset = get_dataset_for_year(annee_reference)
    url = f"https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/{dataset}/records"
    
    params = {
        "where": f'an="{annee_reference}" AND inom="{nom_commune}"',
        "limit": 100
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if "results" not in data or not data["results"]:
        return []
    
    communes = []
    for result in data["results"]:
        communes.append({
            "nom": result.get("inom", ""),
            "departement": result.get("dep", ""),
            "population": result.get("pop1", 0)
        })
    
    return communes

@st.cache_data(show_spinner=False)
def get_all_commune_data(commune, annees, departement):
    """Récupère toutes les données financières pour une commune - v2"""
    data = {}
    data['fonctionnement'] = fetch_commune_fonctionnement(commune, tuple(annees), departement)
    data['caf'] = fetch_commune_caf(commune, tuple(annees), departement)
    data['fiscalite'] = fetch_commune_fiscalite(commune, tuple(annees), departement)
    data['endettement'] = fetch_commune_endettement(commune, tuple(annees), departement)
    data['investissement'] = fetch_commune_investissement(commune, tuple(annees), departement)
    data['fdr'] = fetch_commune_fdr(commune, tuple(annees), departement)
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

import matplotlib.pyplot as plt
import seaborn as sns

def create_chart_image(df, colonnes, titre):
    """Crée un graphique Matplotlib et le sauvegarde comme image temporaire"""
    if df.empty or not colonnes:
        return None

    try:
        # Préparation des données
        df_plot = df[colonnes].reset_index().melt(
            id_vars="Année", var_name="Indicateur", value_name="Valeur"
        )

        # Vérifier qu'il y a des données
        if df_plot.empty or df_plot['Valeur'].isna().all():
            return None

        # Couleurs personnalisées
        colors_palette = ['#1f4e79', '#87ceeb']  # Bleu foncé, bleu clair

        # Création du graphique
        plt.figure(figsize=(8, 6))
        sns.set(style="whitegrid")

        for i, indicateur in enumerate(df_plot['Indicateur'].unique()):
            data = df_plot[df_plot['Indicateur'] == indicateur]
            plt.plot(
                data["Année"],
                data["Valeur"],
                marker='o',
                linewidth=2,
                markersize=6,
                label=indicateur,
                color=colors_palette[i % len(colors_palette)]
            )

        plt.title(f"Évolution - {titre}", fontsize=14, weight="bold")
        plt.xlabel("Année", fontsize=12)
        plt.ylabel("Valeur", fontsize=12)
        plt.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=len(df_plot['Indicateur'].unique()))
        plt.tight_layout()

        # Sauvegarde en fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_path = temp_file.name
        temp_file.close()

        plt.savefig(temp_path, dpi=150)
        plt.close()

        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            print(f"✅ Graphique créé: {titre} -> {temp_path}")
            return temp_path
        else:
            print(f"❌ Échec création: {titre}")
            return None

    except Exception as e:
        print(f"❌ Erreur création graphique {titre}: {e}")
        return None

def create_pdf_report(commune, annees, departement=None):
    """Crée un rapport PDF professionnel avec tous les indicateurs financiers et graphiques"""
    
    # Import local pour éviter les conflits
    from io import BytesIO as PDFBytesIO
    
    # Récupération de toutes les données
    with st.spinner("📄 Génération du rapport PDF avec graphiques..."):
        all_data = get_all_commune_data(commune, annees, departement)
    
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
        all_data = get_all_commune_data(commune, annees, departement)
    
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
    
def create_excel_report(commune, annees, departement):
    """Crée un fichier Excel complet avec tous les indicateurs financiers"""
    
    # Récupération de toutes les données
    with st.spinner("📊 Récupération des données financières..."):
        all_data = get_all_commune_data(commune, annees, departement)
    
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


# ============================================================
# 🔧 Initialisation des variables et du session_state
# ============================================================

if "commune" not in st.session_state:
    st.session_state["commune"] = None
if "departement" not in st.session_state:
    st.session_state["departement"] = None
if "annees" not in st.session_state:
    st.session_state["annees"] = list(range(2019, 2025))  # Par défaut 

commune_selectionnee = st.session_state["commune"]
departement_selectionne = st.session_state["departement"]
annees = st.session_state["annees"]

# ============================================================
# 🏠 Page d'accueil
# ============================================================

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

    # Filtres principaux
    col1, col2 = st.columns(2)
    with col1:
        commune_input = st.text_input(
            "Nom de la commune (⚠️ écrire le nom de la commune en majuscule) :", 
            value="RENAGE"
        )

        commune_selectionnee = None
        departement_selectionne = None

        if commune_input and len(commune_input) >= 1:
            communes_trouvees = search_commune(commune_input)

            if len(communes_trouvees) == 0:
                st.error(f"❌ Aucune commune trouvée avec le nom '{commune_input}'")

            elif len(communes_trouvees) == 1:
                # ✅ Une seule commune trouvée
                commune_selectionnee = communes_trouvees[0]["nom"]
                departement_selectionne = communes_trouvees[0]["departement"]
                st.success(f"✅ Commune sélectionnée : **{commune_selectionnee}** (Dépt. {departement_selectionne})")

            else:
                # ⚠️ Plusieurs homonymes trouvés
                st.warning(f"⚠️ {len(communes_trouvees)} communes portent le nom '{commune_input}'")

                options = [
                    f"{c['nom']} - Dépt {c['departement']} (Pop: {c['population']:,})"
                    for c in communes_trouvees
                ]
                selection = st.selectbox("Choisissez la commune :", options)

                # Extraction de la sélection
                for i, opt in enumerate(options):
                    if opt == selection:
                        commune_selectionnee = communes_trouvees[i]["nom"]
                        departement_selectionne = communes_trouvees[i]["departement"]
                        break

        # 🔁 Sauvegarde en session state
        if commune_selectionnee and departement_selectionne:
            st.session_state["commune"] = commune_selectionnee
            st.session_state["departement"] = departement_selectionne

    # Sélecteur d’années
    with col2:
        annees = st.multiselect(
            "Sélectionnez les années à afficher :",
            options=list(range(2019, 2025)),
            default=st.session_state["annees"]
        )
        st.session_state["annees"] = annees

    # ============================================================
    # 📊 Section Export Excel / PDF / CSV
    # ============================================================

    st.markdown("---")
    st.markdown("### 📊 Export des données")

    if commune_selectionnee and departement_selectionne and annees:
        col1, col2, col3 = st.columns(3)

        # Export Excel
        with col1:
            if st.button("📄 Rapport Excel", type="primary", use_container_width=True):
                try:
                    excel_data = create_excel_report(commune_selectionnee, annees, departement_selectionne)
                    filename = f"Focus_Financier_{commune_selectionnee}_{min(annees)}-{max(annees)}.xlsx"
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
                    pdf_data = create_pdf_report(commune_selectionnee, annees, departement_selectionne)
                    filename_pdf = f"Focus_Financier_{commune_selectionnee}_{min(annees)}-{max(annees)}.pdf"
                    st.download_button(
                        label="📥 Télécharger PDF",
                        data=pdf_data,
                        file_name=filename_pdf,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("✅ PDF généré !")
                except ImportError:
                    st.error("❌ Dépendance manquante : `pip install kaleido`")
                except Exception as e:
                    st.error(f"❌ Erreur PDF : {str(e)}")

        # Export CSV
        with col3:
            if st.button("📊 Export CSV", use_container_width=True):
                try:
                    all_data = get_all_commune_data(commune_selectionnee, annees, departement_selectionne)
                    if not all_data["fonctionnement"].empty:
                        csv_data = all_data["fonctionnement"].to_csv(index=False)
                        filename_csv = f"Focus_Financier_{commune_selectionnee}_fonctionnement.csv"
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

    elif commune_input and annees and not commune_selectionnee:
        st.info("Veuillez sélectionner une commune dans la liste ci-dessus pour générer les rapports.")

# ============================================================
# 🔄 Autres pages (fonctionnement, CAF, fiscalité, etc.)
# ============================================================

else:
    commune = st.session_state.get("commune")
    departement = st.session_state.get("departement")
    annees_session = st.session_state.get("annees", [])

    if not commune or not annees_session:
        st.warning("⚠️ Veuillez d'abord sélectionner une commune sur la page d'accueil.")
        if st.button("🏠 Retour à l'accueil"):
            st.switch_page("pages/accueil.py")
    else:
        st.markdown(f"**Commune :** {commune} | **Département :** {departement or 'N/A'} | **Période :** {min(annees_session)}–{max(annees_session)}")
        st.markdown("---")

        try:
            if page == "Fonctionnement":
                from pages.fonctionnement import run
                run(commune, annees_session, departement)
            elif page == "CAF":
                from pages.caf import run
                run(commune, annees_session, departement)
            elif page == "Fiscalité":
                from pages.fiscalite import run
                run(commune, annees_session, departement)
            elif page == "Endettement":
                from pages.endettements import run
                run(commune, annees_session, departement)
            elif page == "Investissement":
                from pages.investissements import run
                run(commune, annees_session, departement)
            elif page == "Fonds de roulement":
                from pages.fdr import run
                run(commune, annees_session, departement)
        except ImportError as e:
            st.error(f"Erreur lors du chargement de la page : {str(e)}")
        except Exception as e:
            st.error(f"Erreur lors de l'exécution : {str(e)}")
