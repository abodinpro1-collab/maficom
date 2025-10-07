# app_fetchers.py - Fonctions fetch robustes pour votre app.py
import pandas as pd
import requests
import streamlit as st
import re
from functools import lru_cache
from difflib import SequenceMatcher

class AppRobustFetcher:
    """Fetcher robuste spécifique pour app.py et génération PDF"""
    
    def __init__(self):
        self.api_base_url = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/records"
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

# Instance globale cachée
@st.cache_resource
def get_app_fetcher():
    return AppRobustFetcher()

# ==============================================================
# FONCTIONS FETCH ROBUSTES POUR APP.PY
# ==============================================================

def fetch_commune_fonctionnement(commune, annees, departement):
    """Version robuste - REMPLACE votre fonction dans app.py"""
    fetcher = get_app_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
    df_list = []
    
    for annee in annees:
        annee_trouvee = False
        
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

                # Renommer colonnes (identique à votre version)
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
                
                # Ratios (identiques à votre version)
                if "Dépenses personnel / hab" in df_fonctionnement.columns and "Dépenses réelles fonctionnement / hab" in df_fonctionnement.columns:
                    df_fonctionnement["Ratio Personnel/DRF Commune"] = (
                        df_fonctionnement["Dépenses personnel / hab"] /
                        df_fonctionnement["Dépenses réelles fonctionnement / hab"] * 100
                    ).round(2)
                
                if "Moyenne strate Personnel / hab" in df_fonctionnement.columns and "Moyenne strate Dépenses / hab" in df_fonctionnement.columns:
                    df_fonctionnement["Ratio Personnel/DRF Moyenne"] = (
                        df_fonctionnement["Moyenne strate Personnel / hab"] /
                        df_fonctionnement["Moyenne strate Dépenses / hab"] * 100
                    ).round(2)
                
                df_list.append(df_fonctionnement)
                annee_trouvee = True
                break
                
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            print(f"WARN: Fonctionnement non trouvé pour {commune} en {annee}")
    
    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

def fetch_commune_investissement(commune, annees, departement):
    """Version robuste - REMPLACE votre fonction dans app.py"""
    fetcher = get_app_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
    df_list = []
    
    for an in annees:
        annee_trouvee = False
        
        for variant in variants:
            commune_nom = variant["nom"]
            dept = variant["departement"] if not departement else departement
            
            where_clause = f'an="{an}" AND inom="{commune_nom}"'
            if dept:
                where_clause += f' AND dep="{dept}"'
            
            params = {"where": where_clause, "limit": 100}
            
            try:
                r = requests.get(fetcher.api_base_url, params=params, timeout=10)
                data = r.json().get("results", [])
                
                if data:
                    df = pd.DataFrame(data)
                    cols = ['an', 'fequip', 'mequip', 'fprod', 'mprod']
                    df_exist = [c for c in cols if c in df.columns]
                    
                    if df_exist:
                        df = df[df_exist].copy()
                        
                        # Calculs spécifiques investissement (selon votre version app.py)
                        df['Équipement / hab Commune'] = df['fequip']
                        df['Équipement / hab Moyenne'] = df['mequip']
                        df['Équipement / RRF Commune'] = (df['fequip'] / df['fprod'].replace(0, pd.NA) * 100).round(2)
                        df['Équipement / RRF Moyenne'] = (df['mequip'] / df['mprod'].replace(0, pd.NA) * 100).round(2)
                        
                        df.rename(columns={'an': 'Année'}, inplace=True)
                        df_list.append(df)
                        annee_trouvee = True
                        break
                        
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            print(f"WARN: Investissement non trouvé pour {commune} en {an}")
    
    if df_list:
        return pd.concat(df_list, ignore_index=True).sort_values("Année")
    return pd.DataFrame()

def fetch_commune_caf(commune, annees, departement):
    """Version robuste - REMPLACE votre fonction dans app.py"""
    fetcher = get_app_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
    dfs = []
    
    for annee in annees:
        annee_trouvee = False
        
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
                colonnes_calc = ['an', 'pop1', 'fcaf', 'mcaf', 'fprod', 'mprod', 'fcafn', 'mcafn']
                colonnes_existantes = [c for c in colonnes_calc if c in df.columns]
                
                if not colonnes_existantes:
                    continue
                    
                df_caf = df[colonnes_existantes].copy()

                # Calcul des ratios (identique à votre version)
                df_caf['CAF brute / RRF Commune'] = df_caf.apply(
                    lambda row: (row['fcaf']/row['fprod'])*100 if row['fprod'] != 0 else None, axis=1)
                df_caf['CAF brute / RRF Moyenne'] = df_caf.apply(
                    lambda row: (row['mcaf']/row['mprod'])*100 if row['mprod'] != 0 else None, axis=1)
                df_caf['CAF nette / RRF Commune'] = df_caf.apply(
                    lambda row: (row['fcafn']/row['fprod'])*100 if row['fprod'] != 0 else None, axis=1)
                df_caf['CAF nette / RRF Moyenne'] = df_caf.apply(
                    lambda row: (row['mcafn']/row['mprod'])*100 if row['mprod'] != 0 else None, axis=1)

                # Sélection finale et renommage (identique à votre version)
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
                annee_trouvee = True
                break
                
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            print(f"WARN: CAF non trouvé pour {commune} en {annee}")

    if dfs:
        result = pd.concat(dfs, ignore_index=True)
        result.sort_values("Année", inplace=True)
        return result
    else:
        return pd.DataFrame()

def fetch_commune_fiscalite(commune, annees, departement):
    """Version robuste - REMPLACE votre fonction dans app.py"""
    fetcher = get_app_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
    df_list = []
    
    for annee in annees:
        annee_trouvee = False
        
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
                colonnes = ['an', 'fimpo1', 'mimpo1', 'fprod', 'mprod', 'tth', 'tmth', 'tfb', 'tmfb', 'tfnb', 'tmfnb']
                colonnes_existantes = [c for c in colonnes if c in df.columns]
                
                if not colonnes_existantes:
                    continue
                    
                df_fiscalite = df[colonnes_existantes].copy()

                # Calcul des ratios Impôts locaux sur RRF (selon votre version app.py)
                if 'fimpo1' in df_fiscalite.columns and 'fprod' in df_fiscalite.columns:
                    df_fiscalite['Impôts/RRF Commune'] = (df_fiscalite['fimpo1'] / df_fiscalite['fprod'].replace(0, pd.NA) * 100).round(2)
                if 'mimpo1' in df_fiscalite.columns and 'mprod' in df_fiscalite.columns:
                    df_fiscalite['Impôts/RRF Moyenne'] = (df_fiscalite['mimpo1'] / df_fiscalite['mprod'].replace(0, pd.NA) * 100).round(2)

                # Renommer colonnes pour affichage (selon votre version app.py)
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
                annee_trouvee = True
                break
                
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            print(f"WARN: Fiscalité non trouvée pour {commune} en {annee}")
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

def fetch_commune_endettement(commune, annees, departement):
    """Version robuste - REMPLACE votre fonction dans app.py"""
    fetcher = get_app_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
    df_list = []
    
    for an in annees:
        annee_trouvee = False
        
        for variant in variants:
            commune_nom = variant["nom"]
            dept = variant["departement"] if not departement else departement
            
            where_clause = f'an="{an}" AND inom="{commune_nom}"'
            if dept:
                where_clause += f' AND dep="{dept}"'
            
            params = {"where": where_clause, "limit": 100}
            
            try:
                r = requests.get(fetcher.api_base_url, params=params, timeout=10)
                data = r.json().get("results", [])
                
                if data:
                    df = pd.DataFrame(data)
                    cols = ['an', 'fdette', 'mdette', 'fcaf', 'mcaf', 'fcafn', 'mcafn']
                    df_exist = [c for c in cols if c in df.columns]
                    
                    if df_exist:
                        df = df[df_exist].copy()

                        # Calculs spécifiques endettement (selon votre version app.py)
                        df['Dette / hab Commune'] = df['fdette']
                        df['Dette / hab Moyenne'] = df['mdette']
                        df['Dette / RRF Commune'] = (df['fdette'] / df['fcaf'].replace(0, pd.NA) * 100).round(2)
                        df['Dette / RRF Moyenne'] = (df['mdette'] / df['mcaf'].replace(0, pd.NA) * 100).round(2)
                        df['Dette en années CAF Commune'] = (df['fdette'] / df['fcaf'].replace(0, pd.NA)).round(2)
                        df['Dette en années CAF Moyenne'] = (df['mdette'] / df['mcaf'].replace(0, pd.NA)).round(2)

                        df.rename(columns={'an': 'Année'}, inplace=True)
                        df_list.append(df)
                        annee_trouvee = True
                        break
                        
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            print(f"WARN: Endettement non trouvé pour {commune} en {an}")
    
    if df_list:
        return pd.concat(df_list, ignore_index=True).sort_values("Année")
    return pd.DataFrame()

def fetch_commune_fdr(commune, annees, departement):
    """Version robuste - REMPLACE votre fonction dans app.py"""
    fetcher = get_app_fetcher()
    variants = fetcher.find_commune_variants(commune, departement)
    
    df_list = []
    
    for annee in annees:
        annee_trouvee = False
        
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
                colonnes = ['an', 'ffdr', 'mfdr', 'fcharge', 'mcharge']
                colonnes_existantes = [c for c in colonnes if c in df.columns]
                
                if not colonnes_existantes:
                    continue
                    
                df_fr = df[colonnes_existantes].copy()

                # Renommage pour lisibilité (selon votre version app.py)
                df_fr.rename(columns={
                    'an': 'Année',
                    'ffdr': 'FDR / hab Commune',
                    'mfdr': 'FDR / hab Moyenne',
                    'fcharge': 'Charges fonct / hab Commune',
                    'mcharge': 'Charges fonct / hab Moyenne'
                }, inplace=True)

                # Calcul fonds de roulement en jours de charges (selon votre version app.py)
                df_fr['FDR en jours DRF Commune'] = (
                    df_fr['FDR / hab Commune'] / df_fr['Charges fonct / hab Commune'].replace(0, pd.NA) * 365
                ).round(2)
                df_fr['FDR en jours DRF Moyenne'] = (
                    df_fr['FDR / hab Moyenne'] / df_fr['Charges fonct / hab Moyenne'].replace(0, pd.NA) * 365
                ).round(2)

                # Suppression colonnes intermédiaires (selon votre version app.py)
                columns_to_drop = ['Charges fonct / hab Commune', 'Charges fonct / hab Moyenne']
                df_fr.drop(columns=columns_to_drop, inplace=True)
                
                df_list.append(df_fr)
                annee_trouvee = True
                break
                
            except requests.RequestException:
                continue
        
        if not annee_trouvee:
            print(f"WARN: FDR non trouvé pour {commune} en {annee}")
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()