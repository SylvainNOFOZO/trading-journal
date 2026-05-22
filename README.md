# Trading Journal Pro 📈

Application Streamlit de suivi de trades avec synchronisation GitHub.

## Déploiement sur Streamlit Cloud

### 1. Ajouter les secrets dans Streamlit Cloud

Dans l'interface Streamlit Cloud → **Settings → Secrets**, coller :

```toml
GITHUB_TOKEN = "votre_token_github"
GITHUB_REPO  = "SylvainNOFOZO/trading-journal"
DATA_FILE    = "trades_data.json"
```

### 2. Lancer en local

```bash
pip install -r requirements.txt
# Créer .streamlit/secrets.toml avec les valeurs ci-dessus
streamlit run trading_journal.py
```

## Fonctionnalités

- ✅ Dashboard avec KPIs, courbes et graphiques
- ✅ Journal des trades filtrable et triable
- ✅ Ajout / modification / suppression de trades
- ✅ Persistance cloud via GitHub (synchronisé sur tous vos appareils)
- ✅ Export CSV
