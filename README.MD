# 📊 Focus Financier

**Focus Financier** est une application web interactive développée avec [Streamlit](https://streamlit.io/) permettant d'analyser en profondeur les comptes des communes françaises. L'outil offre une visualisation claire et dynamique des principaux indicateurs financiers avec comparaison automatique aux moyennes de strate.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## ✨ Fonctionnalités principales

### 📈 Analyse financière complète
- **💰 Fonctionnement** : Recettes, dépenses, dotations, personnel
- **🧾 Capacité d'Autofinancement (CAF)** : CAF brute et nette
- **🏦 Fiscalité** : Impôts locaux, taux TH/TFB/TFNB
- **📉 Endettement** : Dette par habitant, années de CAF
- **🏗️ Investissement** : Dépenses d'équipement
- **🔄 Fonds de roulement** : En euros et en jours de DRF

### 🎯 Fonctionnalités avancées
- ✅ **Comparaison automatique** avec la moyenne de la strate
- 📊 **Graphiques interactifs** Plotly pour visualiser les évolutions
- 📄 **Export Excel complet** avec 7 onglets (synthèse + 6 modules)
- 📑 **Rapport PDF professionnel** avec tableaux, graphiques et synthèse exécutive
- 💾 **Export CSV** pour analyses externes
- 🔍 **Détection intelligente des homonymes** de communes
- 🔄 **Gestion des variantes de noms** de communes (avec/sans articles)

## 🚀 Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Étapes d'installation

1. **Cloner le dépôt**
```bash
git clone https://github.com/votre-compte/focus-financier.git
cd focus-financier
```

2. **Créer un environnement virtuel** (recommandé)
```bash
python -m venv venv

# Activation sous Linux/Mac
source venv/bin/activate

# Activation sous Windows
venv\Scripts\activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

## ▶️ Lancement de l'application

```bash
streamlit run prod.py
```

L'application s'ouvre automatiquement dans votre navigateur à l'adresse [http://localhost:8501](http://localhost:8501).

## 📂 Structure du projet

```
focus-financier/
├── prod.py                    # Point d'entrée principal
├── app_fetchers.py           # Module de récupération des données
├── pages/
│   ├── accueil.py            # Page d'accueil (obsolète, voir prod.py)
│   ├── fonctionnement.py     # Module Fonctionnement
│   ├── caf.py                # Module CAF
│   ├── fiscalite.py          # Module Fiscalité
│   ├── endettements.py       # Module Endettement
│   ├── investissements.py    # Module Investissement
│   └── fdr.py                # Module Fonds de roulement
├── requirements.txt          # Dépendances Python
└── README.md                 # Documentation
```

## 📦 Dépendances principales

| Bibliothèque | Version | Usage |
|--------------|---------|-------|
| [Streamlit](https://streamlit.io/) | ≥1.28 | Framework web interactif |
| [Pandas](https://pandas.pydata.org/) | ≥2.0 | Manipulation de données |
| [Plotly](https://plotly.com/python/) | ≥5.14 | Graphiques interactifs |
| [Requests](https://docs.python-requests.org/) | ≥2.31 | Requêtes API |
| [ReportLab](https://www.reportlab.com/) | ≥4.0 | Génération PDF |
| [OpenPyXL](https://openpyxl.readthedocs.io/) | ≥3.1 | Export Excel |
| [Matplotlib](https://matplotlib.org/) | ≥3.7 | Graphiques pour PDF |
| [Seaborn](https://seaborn.pydata.org/) | ≥0.12 | Visualisations statistiques |

## 🎯 Utilisation

### 1️⃣ Sélection d'une commune
- Saisissez le nom de la commune **EN MAJUSCULES**
- Si plusieurs homonymes existent, sélectionnez la commune dans la liste déroulante
- Le département est détecté automatiquement

### 2️⃣ Choix de la période
- Sélectionnez une ou plusieurs années (2019-2023 disponibles)
- Les données sont récupérées automatiquement depuis l'API

### 3️⃣ Navigation
Utilisez la barre latérale pour accéder aux différents modules :
- **Accueil** : Vue d'ensemble et exports
- **Fonctionnement** : Analyse des recettes et dépenses
- **CAF** : Capacité d'autofinancement
- **Fiscalité** : Impôts et taux
- **Endettement** : Situation de la dette
- **Investissement** : Dépenses d'équipement
- **Fonds de roulement** : Trésorerie disponible

### 4️⃣ Exports
Depuis la page d'accueil, générez :
- **📄 Excel** : Toutes les données sur 7 onglets
- **📑 PDF** : Rapport professionnel avec graphiques
- **💾 CSV** : Données brutes pour analyses externes

## 🔧 Architecture technique

### Système de cache
L'application utilise plusieurs niveaux de cache pour optimiser les performances :
- `@st.cache_data` : Cache des données API
- `@st.cache_resource` : Cache du fetcher de communes
- `@lru_cache` : Cache des normalisations de noms

### Gestion des variantes de communes
Le système `RobustCommuneFetcher` gère automatiquement :
- Articles "LA", "LE", "LES" (ex: "La Rochelle" = "Rochelle (LA)")
- Changements de noms historiques
- Recherche par similarité (seuil 80%)

### Source des données
API : [data.economie.gouv.fr](https://data.economie.gouv.fr/explore/dataset/comptes-individuels-des-communes-fichier-global-a-compter-de-2000/)

## 🐛 Résolution de problèmes

### Commune introuvable
- ✅ Vérifiez l'orthographe (MAJUSCULES requises)
- ✅ Essayez avec/sans article (ex: "LA ROCHELLE" vs "ROCHELLE")
- ✅ Spécifiez le département si plusieurs homonymes

### Données manquantes pour certaines années
- Certaines communes n'ont pas publié de données pour toutes les années
- Le message "Années manquantes" indique lesquelles
- Utilisez le bouton "🔍 Recherche élargie" pour investiguer

### Erreur d'export PDF
- Vérifiez l'installation de `kaleido` : `pip install kaleido`
- Sous Linux, installez Chrome/Chromium si nécessaire

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Poussez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📝 Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 👤 Auteur

**Arthur Bodin**

- 📧 Email : [votre-email@exemple.com]
- 💼 LinkedIn : [Votre profil LinkedIn]
- 🐙 GitHub : [@votre-username](https://github.com/votre-username)

## 🙏 Remerciements

- **Direction Générale des Finances Publiques (DGFiP)** pour les données ouvertes
- **Streamlit** pour le framework
- Tous les contributeurs du projet

## 📊 Statistiques du projet

![GitHub stars](https://img.shields.io/github/stars/votre-username/focus-financier?style=social)
![GitHub forks](https://img.shields.io/github/forks/votre-username/focus-financier?style=social)
![GitHub issues](https://img.shields.io/github/issues/votre-username/focus-financier)

---

<p align="center">
  Fait avec ❤️ pour faciliter l'analyse financière des communes françaises
</p>
