
---

````markdown
# 📊 MafiCom – Analyse financière des communes

MafiCom est un outil interactif développé avec [Streamlit](https://streamlit.io/) permettant d’analyser les comptes des communes françaises.  
Il offre une visualisation claire et dynamique des principaux indicateurs financiers :

- 💰 Fonctionnement
- 🧾 Capacité d’Autofinancement (CAF)
- 🏦 Fiscalité
- 📉 Endettement
- 🏗️ Investissement
- 🔄 Fonds de roulement

## 🚀 Démo en ligne
👉 [Lien vers l’application]()

## ⚙️ Installation locale

Clonez le dépôt :
```bash
git clone https://github.com/ton-compte/maficom.git
cd maficom
````

Créez un environnement virtuel (optionnel mais recommandé) :

```bash
python -m venv venv
source venv/bin/activate   # sous Linux/Mac
venv\Scripts\activate      # sous Windows
```

Installez les dépendances :

```bash
pip install -r requirements.txt
```

## ▶️ Lancement

Exécutez :

```bash
streamlit run app.py
```

Puis ouvrez l’URL affichée dans ton navigateur (par défaut [http://localhost:8501](http://localhost:8501)).

---

## 📦 Dépendances principales

* [Streamlit](https://streamlit.io/) – Framework web
* [Pandas](https://pandas.pydata.org/) – Manipulation de données
* [Plotly](https://plotly.com/python/) – Graphiques interactifs
* [Requests](https://docs.python-requests.org/) – Requêtes API
* [Openpyxl](https://openpyxl.readthedocs.io/) – Export Excel

---

## 👤 Auteur

Développé par **Arthur Bodin**.

```

---
