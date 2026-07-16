import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime
import json, os, base64, requests, io
import calendar as _calmod

st.set_page_config(page_title="Trading Journal Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

# ── VÉRIFICATION CONFIGURATION ────────────────────────────────────────────────
_sb_url = st.secrets.get("SUPABASE_URL","")
_sb_key = st.secrets.get("SUPABASE_KEY","")
if not _sb_url or not _sb_url.startswith("https://") or not _sb_key:
    st.error("**Base de données non configurée**")
    st.markdown("""
    ### Configuration Supabase requise

    **Étape 1 — Créer un compte gratuit**  
    → https://supabase.com → New project

    **Étape 2 — Créer la table** (SQL Editor dans le dashboard Supabase) :
    ```sql
    CREATE TABLE journal_data (
        key        TEXT PRIMARY KEY,
        value      JSONB NOT NULL DEFAULT '[]',
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    INSERT INTO journal_data (key, value) VALUES ('trades', '[]');
    ALTER TABLE journal_data ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "allow_all" ON journal_data FOR ALL USING (true) WITH CHECK (true);
    ```

    **Étape 3 — Ajouter les secrets dans Streamlit Cloud**  
    Settings → Secrets :
    ```toml
    SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    *(Project URL et anon/public key disponibles dans Supabase → Settings → API)*
    """)
    st.info("En attendant la configuration, vos trades sont sauvegardés localement dans cette session.")
    st.divider()

STRATEGIES   = ["Breakout","Retracement","Support","Tendance","Range","Divergence","Scalping","News"]
MOODS        = ["Euphorique","Confiant","Neutre","Anxieux","Peureux","Frustré"]
SYMBOLS = [
    # Forex majeurs
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD","NZD/USD","USD/CAD",
    # Forex croisés
    "EUR/GBP","EUR/JPY","EUR/CHF","EUR/AUD","EUR/CAD",
    "GBP/JPY","GBP/CHF","GBP/CAD","AUD/JPY","CAD/JPY","CHF/JPY","AUD/NZD",
    # Indices
    "NAS100","SP500","DOW30","DAX40","FTSE100","CAC40","NIKKEI","ASX200",
    # Matières premières
    "GOLD","SILVER","OIL","GAS","COPPER","PLATINUM",
    # Crypto
    "BTC/USD","ETH/USD","XRP/USD","SOL/USD","BNB/USD","LTC/USD","ADA/USD",
    # Autre
    "Autre",
]
MOOD_EMOJI   = {"Euphorique":"🚀","Confiant":"😊","Neutre":"😐","Anxieux":"😰","Peureux":"😨","Frustré":"😤"}
MOOD_ICON = {
    "Euphorique": ('<i class="fa-solid fa-rocket"     style="color:#00d4aa"></i>', "#00d4aa"),
    "Confiant":   ('<i class="fa-solid fa-thumbs-up"  style="color:#00b894"></i>', "#00b894"),
    "Neutre":     ('<i class="fa-solid fa-minus"       style="color:#6b7894"></i>', "#6b7894"),
    "Anxieux":    ('<i class="fa-solid fa-triangle-exclamation" style="color:#ff9f43"></i>', "#ff9f43"),
    "Peureux":    ('<i class="fa-solid fa-shield-halved" style="color:#fd79a8"></i>', "#fd79a8"),
    "Frustré":    ('<i class="fa-solid fa-fire"        style="color:#ff4d6d"></i>', "#ff4d6d"),
}
def mood_html(mood):
    icon, color = MOOD_ICON.get(mood, ('<i class="fa-solid fa-circle" style="color:#6b7894"></i>', "#6b7894"))
    return f'<span title="{mood}" style="display:inline-flex;align-items:center;gap:5px">{icon}</span>'
CHART_COLORS = ["#00d4aa","#7c6aff","#ff9f43","#ff4d6d","#54a0ff","#5f27cd","#00cec9","#fdcb6e"]

# ── THÈMES ─────────────────────────────────────────────────────────────────────
THEMES = {
    "Émeraude Sombre": {
        "bg":"#0a0c12","bg2":"#0d111d","card":"#111520","border":"#1e2535",
        "text":"#e8ecf4","muted":"#6b7894","accent":"#00d4aa","win":"#00d4aa",
        "loss":"#ff4d6d","alt":"#7c6aff","orange":"#ff9f43","sidebar":"#0c0f1a",
        "btn_text":"#000000",
    },
    "Indigo Minuit": {
        "bg":"#0a0a16","bg2":"#0d0d1a","card":"#13131f","border":"#232336",
        "text":"#eaeaf5","muted":"#7a7a9a","accent":"#6c5ce7","win":"#2ecc91",
        "loss":"#ff5c7a","alt":"#00cec9","orange":"#fdcb6e","sidebar":"#0e0e1c",
        "btn_text":"#ffffff",
    },
    "Ardoise Bleu": {
        "bg":"#0b0e14","bg2":"#0e1118","card":"#141821","border":"#232a38",
        "text":"#e5e9f0","muted":"#6f7a8c","accent":"#4fa3ff","win":"#2dd4bf",
        "loss":"#fb7185","alt":"#a78bfa","orange":"#ffb454","sidebar":"#0d1016",
        "btn_text":"#0b0e14",
    },
    "Ambre Doré": {
        "bg":"#100d0a","bg2":"#14110d","card":"#1c1812","border":"#2e2620",
        "text":"#f5ece0","muted":"#9c8f7c","accent":"#f0a500","win":"#9ed36c",
        "loss":"#ff6b5e","alt":"#ff7849","orange":"#ffcb47","sidebar":"#120f0b",
        "btn_text":"#1c1410",
    },
    "Ivoire Clair": {
        "bg":"#f4f5f9","bg2":"#eceef4","card":"#ffffff","border":"#e1e4ec",
        "text":"#1a1d29","muted":"#6b7280","accent":"#00a884","win":"#00a884",
        "loss":"#e74c3c","alt":"#6c5ce7","orange":"#e67e22","sidebar":"#ffffff",
        "btn_text":"#ffffff",
    },
}
THEME_NAMES = list(THEMES.keys())

def get_theme():
    name = st.session_state.get("theme_name", THEME_NAMES[0])
    return THEMES.get(name, THEMES[THEME_NAMES[0]])

def build_css(t):
    """Génère le CSS complet en fonction du thème actif."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
.fa, .fas, .far, .fab, .fa-solid, .fa-regular {{ font-family: "Font Awesome 6 Free" !important; }}
.icon {{ display:inline-flex; align-items:center; justify-content:center;
        width:32px; height:32px; border-radius:8px; font-size:15px; }}
.icon-green  {{ color:{t['win']}; background:{t['win']}1f; }}
.icon-red    {{ color:{t['loss']}; background:{t['loss']}1f; }}
.icon-purple {{ color:{t['alt']}; background:{t['alt']}1f; }}
.icon-orange {{ color:{t['orange']}; background:{t['orange']}1f; }}
.icon-muted  {{ color:{t['muted']}; background:{t['muted']}1a; }}
.mood-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }}
.stApp {{ background-color: {t['bg']}; }}
section[data-testid="stSidebar"] > div {{ background-color: {t['sidebar']}; border-right: 1px solid {t['border']}; }}
h1,h2,h3,h4,h5,h6,p,label,.stMarkdown {{ color: {t['text']} !important; }}
.stSelectbox label,.stNumberInput label,.stTextInput label,.stTextArea label,.stDateInput label {{
    color: {t['muted']} !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px; }}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] > div {{
    background-color: {t['bg2']} !important; border-color: {t['border']} !important; color: {t['text']} !important; }}
.stButton > button {{ background-color:{t['accent']};color:{t['btn_text']};font-weight:800;border:none;border-radius:10px; }}
.stButton > button:hover {{ filter:brightness(0.92); color:{t['btn_text']} !important; }}
.kpi {{ background:{t['card']};border:1px solid {t['border']};border-radius:14px;padding:18px 20px 14px;
    position:relative;overflow:hidden;min-height:110px; }}
.kpi-bar {{ position:absolute;top:0;left:0;right:0;height:3px; }}
.kpi-icon {{ font-size:18px;margin-bottom:6px; }}
.kpi-label {{ font-size:10px;color:{t['muted']};letter-spacing:1.5px;text-transform:uppercase;font-weight:600; }}
.kpi-value {{ font-size:24px;font-weight:800;font-family:"JetBrains Mono",monospace;margin:4px 0 2px; }}
.kpi-sub {{ font-size:11px;color:{t['muted']}; }}
.tj-table {{ width:100%;border-collapse:collapse;font-size:13px; }}
.tj-table th {{ padding:10px 12px;text-align:left;font-size:10px;color:{t['muted']};letter-spacing:1px;
    text-transform:uppercase;border-bottom:1px solid {t['border']};background:{t['bg2']};font-weight:600; }}
.tj-table td {{ padding:11px 12px;border-bottom:1px solid {t['border']}80;color:{t['text']}; }}
.tj-table tr:hover td {{ background:{t['border']}55; }}
.badge {{ padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.8px;display:inline-block; }}
.b-win  {{ color:{t['win']};background:{t['win']}26;border:1px solid {t['win']}4d; }}
.b-loss {{ color:{t['loss']};background:{t['loss']}26;border:1px solid {t['loss']}4d; }}
.b-sym  {{ color:{t['alt']};background:{t['alt']}26;border:1px solid {t['alt']}4d; }}
.b-str  {{ color:{t['orange']};background:{t['orange']}26;border:1px solid {t['orange']}4d; }}
.b-real {{ color:{t['win']};background:{t['win']}26;border:1px solid {t['win']}4d; }}
.b-demo {{ color:{t['orange']};background:{t['orange']}26;border:1px solid {t['orange']}4d; }}
.b-inst {{ color:{t['alt']};background:{t['alt']}26;border:1px solid {t['alt']}4d; }}
hr {{ border-color:{t['border']} !important; }}
.sync-ok {{ background:{t['win']}18;border:1px solid {t['win']}44;border-radius:8px;padding:6px 14px;font-size:12px;color:{t['win']}; }}
.mode-banner-real {{ background:{t['win']}14;border:1px solid {t['win']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['win']};font-weight:700;margin-bottom:12px; }}
.mode-banner-inst {{ background:{t['alt']}14;border:1px solid {t['alt']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['alt']};font-weight:700;margin-bottom:12px; }}
.mode-banner-demo {{ background:{t['orange']}14;border:1px solid {t['orange']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['orange']};font-weight:700;margin-bottom:12px; }}
.mode-banner-all  {{ background:{t['alt']}14;border:1px solid {t['alt']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['alt']};font-weight:700;margin-bottom:12px; }}
</style>
"""
TRADE_MODES  = ["Démo", "Réel Indépendant", "Réel Institutionnel"]
MODE_FILTER_OPTIONS = ["Tous"] + TRADE_MODES
# Mapping universel : nom broker → nom normalisé
# Exness utilise le suffixe "m" (ex: XAUUSDm, BTCUSDm)
_BASE_PAIRS = {
    "EURUSD":"EUR/USD","GBPUSD":"GBP/USD","USDJPY":"USD/JPY","USDCHF":"USD/CHF",
    "AUDUSD":"AUD/USD","NZDUSD":"NZD/USD","USDCAD":"USD/CAD","EURGBP":"EUR/GBP",
    "EURJPY":"EUR/JPY","GBPJPY":"GBP/JPY","EURCAD":"EUR/CAD","AUDCAD":"AUD/CAD",
    "AUDNZD":"AUD/NZD","GBPCAD":"GBP/CAD","GBPCHF":"GBP/CHF","EURCHF":"EUR/CHF",
    "EURAUD":"EUR/AUD","EURCAD":"EUR/CAD","CADJPY":"CAD/JPY","CHFJPY":"CHF/JPY",
    "XAUUSD":"GOLD","XAGUSD":"SILVER","XPTUSD":"PLATINUM",
    "BTCUSD":"BTC/USD","ETHUSD":"ETH/USD","LTCUSD":"LTC/USD","XRPUSD":"XRP/USD",
    "BNBUSD":"BNB/USD","SOLUSD":"SOL/USD","ADAUSD":"ADA/USD","DOTUSD":"DOT/USD",
    "US30":"DOW30","US500":"SP500","SP500":"SP500","SPX500":"SP500",
    "USTEC":"NAS100","NAS100":"NAS100","NASDAQ":"NAS100","US100":"NAS100",
    "UK100":"FTSE100","GER40":"DAX40","GER30":"DAX40","FRA40":"CAC40",
    "JPN225":"NIKKEI","AUS200":"ASX200","HK50":"HK50",
    "USOIL":"OIL","UKOIL":"OIL","WTI":"OIL","BRENT":"OIL","NGAS":"GAS",
    "COPPER":"COPPER",
}
# Générer automatiquement les variantes avec suffixe "m" (Exness)
SYM_MAP = {}
for k, v in _BASE_PAIRS.items():
    SYM_MAP[k]        = v   # standard
    SYM_MAP[k + "m"]  = v   # Exness suffixe "m"
    SYM_MAP[k + "M"]  = v   # majuscule
    SYM_MAP[k + ".m"] = v   # point + m
    SYM_MAP[k + "_m"] = v   # underscore + m
# Cas spéciaux Exness
SYM_MAP.update({
    "XAUUSDm":"GOLD","XAGUSDm":"SILVER",
    "BTCUSDm":"BTC/USD","ETHUSDm":"ETH/USD",
    "USTECm":"NAS100","US30m":"DOW30","US500m":"SP500",
    "GER40m":"DAX40","UK100m":"FTSE100","FRA40m":"CAC40",
    "USOILm":"OIL","UKOILm":"OIL",
    "EURUSDm":"EUR/USD","GBPUSDm":"GBP/USD","USDJPYm":"USD/JPY",
    "USDCHFm":"USD/CHF","AUDUSDm":"AUD/USD","NZDUSDm":"NZD/USD",
    "USDCADm":"USD/CAD","EURGBPm":"EUR/GBP","EURJPYm":"EUR/JPY",
    "GBPJPYm":"GBP/JPY","XRPUSDm":"XRP/USD","SOLUSDm":"SOL/USD",
})
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#111520", plot_bgcolor="#111520",
    font=dict(color="#6b7894", family="DM Sans, sans-serif"),
    margin=dict(l=50,r=20,t=20,b=40),
    xaxis=dict(gridcolor="#1e2535",linecolor="#1e2535"),
    yaxis=dict(gridcolor="#1e2535",linecolor="#1e2535"),
    hovermode="x unified",
)

# ── SUPABASE PERSISTENCE ────────────────────────────────────────────────────
# Base PostgreSQL indépendante du code → données 100% sécurisées
SB_URL = st.secrets.get("SUPABASE_URL", "")
SB_KEY = st.secrets.get("SUPABASE_KEY", "")
SB_HDR = {
    "apikey":        SB_KEY,
    "Authorization": f"Bearer {SB_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "return=minimal",
}
SB_EP = f"{SB_URL}/rest/v1/journal_data"

def _sb_ready():
    """Vérifie que les secrets Supabase sont configurés."""
    return bool(SB_URL and SB_KEY and SB_URL.startswith("https://"))

def db_load():
    if not _sb_ready():
        return st.session_state.get("_local_trades", [])
    try:
        r = requests.get(f"{SB_EP}?key=eq.trades&select=value",
                         headers=SB_HDR, timeout=10)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            db_init()
            return []
        val = rows[0].get("value", [])
        return val if isinstance(val, list) else []
    except Exception as e:
        st.error(f"Erreur chargement base de données : {e}")
        return []

def db_save(trades):
    if not _sb_ready():
        st.session_state["_local_trades"] = trades
        st.warning("Supabase non configuré — données en mémoire uniquement.")
        return False
    try:
        # 1. Essai PATCH (update de la ligne existante)
        r = requests.patch(
            f"{SB_EP}?key=eq.trades",
            headers={**SB_HDR, "Prefer": "return=representation"},
            json={"value": trades, "updated_at": "now()"},
            timeout=15
        )
        if r.status_code == 200:
            # PATCH réussi mais vérifie qu'une ligne a bien été modifiée
            result = r.json()
            if isinstance(result, list) and len(result) > 0:
                return True  # ✅ mis à jour
            # Ligne absente → INSERT
        if r.status_code in (204,):
            return True
        # 2. INSERT si la ligne n'existe pas encore
        r2 = requests.post(
            SB_EP,
            headers={**SB_HDR, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"key": "trades", "value": trades},
            timeout=15
        )
        if r2.status_code in (200, 201):
            return True
        st.error(f"Erreur sauvegarde [{r2.status_code}] : {r2.text[:200]}")
        return False
    except Exception as e:
        st.error(f"Erreur sauvegarde : {e}")
        return False
def db_init():
    try:
        requests.post(SB_EP, headers=SB_HDR,
            json={"key": "trades", "value": []}, timeout=10)
    except:
        pass


def db_status():
    """Vérifie la connexion et retourne le nombre de trades en base."""
    if not _sb_ready():
        return False, 0, "Secrets manquants"
    try:
        r = requests.get(f"{SB_EP}?key=eq.trades&select=value",
                         headers=SB_HDR, timeout=6)
        if r.status_code == 200:
            rows = r.json()
            if rows:
                val = rows[0].get("value", [])
                n = len(val) if isinstance(val, list) else 0
                return True, n, f"{n} trades en base"
            return True, 0, "Connecté · base vide"
        return False, 0, f"HTTP {r.status_code}"
    except Exception as e:
        return False, 0, str(e)[:50]
def cloud_save(trades):
    ok = db_save(trades)
    if ok: st.session_state.trades = trades
    else: st.warning("Sauvegarde échouée — vérifiez la connexion.")
    return ok

# ── MIGRATION DES MODES ─────────────────────────────────────────────────────
# Ancien schéma ("Réel", "Réel 💰", vide) → nouveau ("Réel Indépendant").
# Retourne (trades, nb_modifiés). Persistée en base dès qu'un changement a lieu.
_LEGACY_REAL = ("Réel", "Réel 💰", "Réel Indépendant 💰", "")
_LEGACY_DEMO = ("Démo 🧪", "Démo")

def migrate_modes(trades):
    changed = 0
    for t in trades:
        old_m = t.get("trade_mode", "")
        if old_m in _LEGACY_DEMO:
            new_m = "Démo"
        elif old_m in TRADE_MODES:
            new_m = old_m                       # déjà au nouveau format
        elif old_m in _LEGACY_REAL or not old_m:
            new_m = "Réel Indépendant"
        else:
            new_m = old_m                       # valeur inconnue : ne pas toucher
        if new_m != old_m:
            t["trade_mode"] = new_m
            changed += 1
    return trades, changed

def load_and_migrate():
    """Charge depuis la base, migre, et persiste la migration si nécessaire."""
    trades = db_load()
    trades, changed = migrate_modes(trades)
    if changed:
        if db_save(trades):
            st.session_state["_migration_msg"] = (
                f"{changed} trade(s) migrés vers « Réel Indépendant » et sauvegardés.")
        else:
            st.session_state["_migration_msg"] = (
                f"{changed} trade(s) migrés (affichage uniquement — sauvegarde échouée).")
    return trades

def force_reload():
    st.session_state.trades = load_and_migrate()
# ── INIT SESSION ────────────────────────────────────────────────────────────
if "trades" not in st.session_state:
    st.session_state.trades = load_and_migrate()
if "page"        not in st.session_state: st.session_state.page        = "dashboard"
if "edit_id"     not in st.session_state: st.session_state.edit_id     = None
if "theme_name"  not in st.session_state: st.session_state.theme_name  = THEME_NAMES[0]
if "mode_filter" not in st.session_state: st.session_state.mode_filter = "Tous"
if st.session_state.mode_filter not in MODE_FILTER_OPTIONS: st.session_state.mode_filter = "Tous"





def get_pnl(t): return float(t.get("pnl", 0))

def calc_rr(t):
    sl, tp, entry = t.get("sl",0), t.get("tp",0), t.get("entry",0)
    if not sl or not tp or not entry: return None
    risk = abs(entry - sl)
    return round(abs(tp - entry)/risk, 2) if risk else None

def fmt(n):
    if n is None: return "—"
    return f"+${n:,.2f}" if n >= 0 else f"-${abs(n):,.2f}"

def get_df(mode_filter="Tous"):
    rows = [dict(t, pnl=get_pnl(t), rr=calc_rr(t)) for t in st.session_state.trades]
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if df.empty: return df
    if "trade_mode" not in df.columns: df["trade_mode"] = "Réel Indépendant"
    if mode_filter in TRADE_MODES: return df[df["trade_mode"] == mode_filter]
    return df

def kpi(icon, label, value, sub, color):
    st.markdown(f"""<div class="kpi">
        <div class="kpi-bar" style="background:{color}"></div>
        <div class="kpi-icon" style="font-size:17px;margin-bottom:8px;color:{color};opacity:.9">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
        <div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

def badge(text, cls): return f'<span class="badge {cls}">{text}</span>'

def ev(key, default):
    ex = next((t for t in st.session_state.trades if t["id"]==st.session_state.edit_id), None)
    return ex[key] if ex else default

def safe_float(val):
    try: return float(str(val).replace(" ","").replace(",",".").strip() or 0)
    except: return 0.0

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Trading Journal")
    st.caption("Pro · v3.0 · GitHub Sync")

    _sel_theme = st.selectbox(
        "Thème", THEME_NAMES,
        index=THEME_NAMES.index(st.session_state.theme_name)
              if st.session_state.theme_name in THEME_NAMES else 0,
        key="theme_selector", label_visibility="collapsed"
    )
    if _sel_theme != st.session_state.theme_name:
        st.session_state.theme_name = _sel_theme
        st.rerun()

    st.divider()

    # Filtre global mode
    mode_f = st.selectbox("Afficher", MODE_FILTER_OPTIONS,
        index=MODE_FILTER_OPTIONS.index(st.session_state.mode_filter) if st.session_state.mode_filter in MODE_FILTER_OPTIONS else 0,
        label_visibility="collapsed")
    if mode_f != st.session_state.mode_filter:
        st.session_state.mode_filter = mode_f; st.rerun()
    st.divider()

    df_side = get_df(st.session_state.mode_filter)
    total   = df_side["pnl"].sum() if not df_side.empty else 0
    wr      = (len(df_side[df_side["pnl"]>0])/len(df_side)*100) if not df_side.empty else 0
    col_pnl = "#00d4aa" if total >= 0 else "#ff4d6d"
    mode_icon = st.session_state.mode_filter

    st.markdown(f"""<div style="margin-bottom:16px;padding:10px 0">
        <div style="font-size:10px;color:#6b7894;letter-spacing:1px;text-transform:uppercase">
            Capital Net · {mode_icon} {st.session_state.mode_filter}</div>
        <div style="font-size:22px;font-weight:800;color:{col_pnl};font-family:\'JetBrains Mono\',monospace">{fmt(total)}</div>
        <div style="font-size:11px;color:#6b7894;margin-top:2px">{len(df_side)} trades · {wr:.0f}% win</div>
    </div>""", unsafe_allow_html=True)

    if st.button("  Dashboard",     icon=":material/dashboard:",     use_container_width=True):
        st.session_state.page="dashboard"; st.session_state.edit_id=None; st.rerun()
    if st.button("  Journal",       icon=":material/table_rows:",       use_container_width=True):
        st.session_state.page="journal";   st.session_state.edit_id=None; st.rerun()
    if st.button("  Nouveau Trade", icon=":material/add_circle:", use_container_width=True):
        st.session_state.page="add";       st.session_state.edit_id=None; st.rerun()
    if st.button("  Importer MT5",  icon=":material/upload_file:",  use_container_width=True):
        st.session_state.page="import";    st.session_state.edit_id=None; st.rerun()
    if st.button("  Calendrier",    icon=":material/calendar_month:", use_container_width=True):
        st.session_state.page="calendar";  st.session_state.edit_id=None; st.rerun()
    if st.button("  Synchroniser",  icon=":material/sync:",  use_container_width=True):
        force_reload(); st.success("Données rechargées."); st.rerun()

    st.divider()
    if not df_side.empty:
        csv = df_side.to_csv(index=False).encode("utf-8")
        st.download_button("  Exporter CSV", data=csv, file_name="trades.csv", mime="text/csv", icon=":material/download:", use_container_width=True)

    st.markdown('<div class="sync-ok"><i class="fa-solid fa-database"></i> Supabase · connecté</div>', unsafe_allow_html=True)

# ── BANNER MODE ────────────────────────────────────────────────────────────────
def mode_banner():
    m = st.session_state.mode_filter
    if m == "Réel Indépendant":
        st.markdown('<div class="mode-banner-real"><i class="fa-solid fa-circle-dot"></i> Réel Indépendant — Compte personnel</div>', unsafe_allow_html=True)
    elif m == "Réel Institutionnel":
        st.markdown('<div class="mode-banner-inst"><i class="fa-solid fa-building-columns"></i> Réel Institutionnel — Fonds commun avec partenaires financiers</div>', unsafe_allow_html=True)
    elif m == "Démo":
        st.markdown('<div class="mode-banner-demo"><i class="fa-solid fa-flask"></i> Mode DÉMO — Performances sur compte démo</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mode-banner-all"><i class="fa-solid fa-layer-group"></i> Tous les trades — tous comptes confondus</div>', unsafe_allow_html=True)

# ── INJECTION CSS SELON LE THÈME ACTIF ──────────────────────────────────────────
st.markdown(build_css(get_theme()), unsafe_allow_html=True)

# ── MESSAGE DE MIGRATION (affiché une seule fois) ───────────────────────────────
_mig_msg = st.session_state.pop("_migration_msg", None)
if _mig_msg:
    st.success(_mig_msg, icon=":material/check_circle:")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "dashboard":
    st.markdown("# Dashboard")
    st.caption(datetime.now().strftime("%A %d %B %Y"))
    mode_banner()

    # ── FILTRES ───────────────────────────────────────────────────────────────
    st.markdown('<div style="background:#111520;border:1px solid #1e2535;border-radius:14px;padding:16px 20px;margin:12px 0 20px">',
                unsafe_allow_html=True)
    df_all_f    = get_df("Tous")
    syms_avail  = sorted(df_all_f["symbol"].unique().tolist()) if not df_all_f.empty else []
    moods_avail = sorted(df_all_f["mood"].unique().tolist())   if not df_all_f.empty else []
    strat_avail = sorted(df_all_f["strategy"].unique().tolist()) if not df_all_f.empty else []
    dates       = sorted(df_all_f["date"].tolist()) if not df_all_f.empty else []
    d_min = date.fromisoformat(dates[0])  if dates else date(2024,1,1)
    d_max = date.fromisoformat(dates[-1]) if dates else date.today()
    fc1,fc2,fc3,fc4,fc5 = st.columns(5)
    with fc1: f_sym       = st.selectbox("Actif",       ["Tous"]+syms_avail,  key="d_sym")
    with fc2: f_mood      = st.selectbox("Émotion",     ["Toutes"]+moods_avail, key="d_mood")
    with fc3: f_strat     = st.selectbox("Stratégie",   ["Toutes"]+strat_avail, key="d_strat")
    with fc4: f_date_from = st.date_input("Depuis",     value=d_min, key="d_from")
    with fc5: f_date_to   = st.date_input("Jusqu'au",   value=d_max, key="d_to")
    st.markdown('</div>', unsafe_allow_html=True)

    df = get_df(st.session_state.mode_filter)
    if not df.empty:
        if f_sym   != "Tous":   df = df[df["symbol"]   == f_sym]
        if f_mood  != "Toutes": df = df[df["mood"]     == f_mood]
        if f_strat != "Toutes": df = df[df["strategy"] == f_strat]
        df = df[df["date"].between(str(f_date_from), str(f_date_to))]

    if df.empty:
        st.warning("Aucun trade pour ces filtres.")
    else:
        wins   = df[df["pnl"]>0]; losses = df[df["pnl"]<=0]
        total  = df["pnl"].sum()
        avg_w  = wins["pnl"].mean()   if len(wins)   else 0
        avg_l  = losses["pnl"].mean() if len(losses) else 0
        pf     = round(abs(avg_w/avg_l),2) if avg_l else None
        rr_df  = df[df["rr"].notna()]
        avg_rr = rr_df["rr"].mean() if len(rr_df) else None
        wr_val = len(wins)/len(df)*100
        df_s   = df.sort_values("date")
        cumul  = df_s["pnl"].cumsum()
        mdd    = (cumul.cummax()-cumul).max()
        df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
        monthly = df.groupby("month")["pnl"].sum().reset_index()
        monthly["label"] = monthly["month"].str[5:]+"/"+monthly["month"].str[2:4]

        # ── KPIs ─────────────────────────────────────────────────────────────
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        with c1: kpi('<i class="fa-solid fa-coins"></i>',          "P&L Net",      fmt(total),       f"{len(df)} trades",             "#00d4aa" if total>=0 else "#ff4d6d")
        with c2: kpi('<i class="fa-solid fa-bullseye"></i>',       "Win Rate",     f"{wr_val:.1f}%", f"{len(wins)}W · {len(losses)}L","#00d4aa" if wr_val>=50 else "#ff4d6d")
        with c3: kpi('<i class="fa-solid fa-scale-balanced"></i>', "Profit Factor",f"{pf:.2f}" if pf else "—","Gain/Perte",          "#00d4aa" if (pf or 0)>=1.5 else "#ff9f43")
        with c4: kpi('<i class="fa-solid fa-arrow-trend-down"></i>',"Max Drawdown",f"${mdd:,.2f}",   "Perte cumulée max",             "#ff4d6d")
        with c5: kpi('<i class="fa-solid fa-bolt"></i>',           "R:R Moyen",   f"{avg_rr:.2f}R" if avg_rr else "—","Risque/Récomp","#7c6aff")
        with c6: kpi('<i class="fa-solid fa-arrow-trend-up"></i>', "Gain moyen",   fmt(avg_w),       "Par trade gagnant",             "#00d4aa")
        st.markdown(" ")

        # Comparaison par mode de compte
        if st.session_state.mode_filter == "Tous" and "trade_mode" in df.columns:
            _mode_cfg = {
                "Démo":               ("#ff9f43", "fa-flask"),
                "Réel Indépendant":   ("#00d4aa", "fa-circle-dot"),
                "Réel Institutionnel":("#7c6aff", "fa-building-columns"),
            }
            _active_modes = [m for m in TRADE_MODES if not df[df["trade_mode"]==m].empty]
            if len(_active_modes) >= 2:
                st.markdown("#### Comparaison par mode de compte")
                _cols = st.columns(len(_active_modes))
                for _col, _m in zip(_cols, _active_modes):
                    _df_m = df[df["trade_mode"]==_m]
                    _color, _icon = _mode_cfg.get(_m, ("#8892a4","fa-circle"))
                    _wr_m = len(_df_m[_df_m["pnl"]>0])/len(_df_m)*100 if len(_df_m) else 0
                    with _col:
                        kpi(f'<i class="fa-solid {_icon}"></i>', f"P&L {_m}",
                            fmt(_df_m["pnl"].sum()),
                            f"{len(_df_m)} trades · {_wr_m:.0f}% win", _color)
                st.markdown(" ")

        # ════════════════════════════════════════════════════════════════════
        # COULEURS & STYLE COMMUNS
        # ════════════════════════════════════════════════════════════════════
        _theme = get_theme()
        _bg   = _theme["card"]
        _grid = _theme["border"]
        _text = _theme["muted"]
        _win  = _theme["win"]
        _loss = _theme["loss"]
        _alt  = _theme["alt"]
        _ora  = _theme["orange"]

        def _base_layout(height=260, showlegend=False, **kwargs):
            """showlegend est un param nommé — jamais en doublon avec **kwargs."""
            return dict(
                paper_bgcolor=_bg, plot_bgcolor=_bg,
                font=dict(color=_text, family="DM Sans, sans-serif", size=12),
                height=height,
                margin=dict(l=50,r=20,t=30,b=40),
                showlegend=showlegend,
                hovermode="x unified",
                **kwargs
            )

        def _style_axes(fig, xprefix="", yprefix="", xtickangle=0, free_y=False):
            fig.update_xaxes(gridcolor=_grid, linecolor=_grid, tickcolor=_grid,
                             tickprefix=xprefix, tickangle=xtickangle,
                             showline=True, zeroline=False)
            fig.update_yaxes(gridcolor=_grid, linecolor=_grid, tickcolor=_grid,
                             tickprefix=yprefix, showline=True, zeroline=True,
                             zerolinecolor="#2a3248", zerolinewidth=1,
                             fixedrange=not free_y)

        def _card(title, subtitle=""):
            sub_html = f' <span style="font-size:12px;color:#6b7894">{subtitle}</span>' if subtitle else ""
            st.markdown(
                f'<div style="margin-bottom:4px"><span style="font-size:15px;font-weight:700;color:#e8ecf4">{title}</span>{sub_html}</div>',
                unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # AXE TEMPOREL — datetime précis si disponible, sinon date
        # ════════════════════════════════════════════════════════════════════
        def _get_x(df_sorted):
            """Retourne (x_list, label) avec datetime précis si possible."""
            if "datetime" in df_sorted.columns:
                x = pd.to_datetime(df_sorted["datetime"], errors="coerce")
                if x.notna().sum() > 0:
                    return x.tolist(), "Date · Heure"
            return df_sorted["date"].tolist(), "Date"

        # ════════════════════════════════════════════════════════════════════
        # AXE X : une entrée unique PAR POSITION (jamais agrégé)
        # ════════════════════════════════════════════════════════════════════
        # Construire des labels de position uniques : "DD/MM HH:MM · SYMBOL"
        def _position_labels(df_sorted):
            labels = []
            for i, (_, row) in enumerate(df_sorted.iterrows()):
                if "datetime" in df_sorted.columns and pd.notna(row.get("datetime",""))                         and str(row.get("datetime","")) not in ("","nan","NaT"):
                    try:
                        dt = pd.to_datetime(row["datetime"])
                        lbl = dt.strftime("%d/%m %H:%M")
                    except:
                        lbl = str(row["date"])
                else:
                    lbl = str(row["date"])
                # Rendre unique si plusieurs trades même instant
                lbl_unique = f"{lbl} · {row['symbol']}"
                labels.append(lbl_unique)
            return labels

        pos_labels = _position_labels(df_s)   # un label par position
        n_pos      = len(pos_labels)
        # Index numérique pour l'axe X : barres larges quel que soit le nb de trades
        pos_idx    = list(range(n_pos))

        # Ticks : afficher seulement ~12 dates sur l'axe pour rester lisible
        _tick_step = max(1, n_pos // 12)
        _tick_vals = pos_idx[::_tick_step]
        _tick_text = [pos_labels[i] for i in _tick_vals]

        # Config commune
        _chart_cfg = {
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["lasso2d","select2d"],
            "toImageButtonOptions": {"format":"png","scale":2},
        }

        def _xaxis_pos(n):
            return dict(
                showticklabels=False,   # pas de labels sur l'axe X
                rangeslider=dict(visible=True, thickness=0.04,
                                 bgcolor="#0d111d", bordercolor=_grid, borderwidth=1),
            )

        # ════════════════════════════════════════════════════════════════════
        # ROW 1 : Capital cumulé + Win/Loss
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Performance dans le temps")
        r1c1, r1c2 = st.columns([3,2])

        with r1c1:
            _card("Capital Cumulé par Position")
            fig_eq = go.Figure(go.Bar(
                x=pos_idx,
                y=cumul.tolist(),
                marker_color=[_win if v >= 0 else _loss for v in cumul],
                marker_opacity=0.8,
                hovertemplate=(
                    "<b>Position #%{pointNumber+1}</b><br>"
                    "%{customdata[2]}<br>"
                    "%{customdata[0]} · %{customdata[1]}<br>"
                    "Capital cumulé : <b>%{y:+,.2f}$</b><extra></extra>"
                ),
                customdata=list(zip(
                    df_s["symbol"].tolist(),
                    df_s["direction"].tolist(),
                    pos_labels,
                )),
                showlegend=False,
            ))
            fig_eq.add_hline(y=0, line_color=_grid, line_width=1)
            fig_eq.update_layout(**_base_layout(height=300))
            _style_axes(fig_eq, yprefix="$", free_y=True)
            fig_eq.update_xaxes(**_xaxis_pos(n_pos))
            fig_eq.update_layout(dragmode="zoom")
            st.plotly_chart(fig_eq, use_container_width=True, config=_chart_cfg)

        with r1c2:
            _card("Win / Loss")
            fig_pie = go.Figure(go.Pie(
                values=[len(wins), len(losses)],
                labels=["Gagnants","Perdants"], hole=0.65,
                marker=dict(colors=[_win, _loss], line=dict(color=_bg, width=3)),
                hovertemplate="<b>%{label}</b>: %{value} trades (%{percent})<extra></extra>",
                textinfo="none",
            ))
            fig_pie.add_annotation(text=f"<b>{wr_val:.0f}%</b>", x=0.5, y=0.58,
                font=dict(size=28,color=_win,family="JetBrains Mono"), showarrow=False)
            fig_pie.add_annotation(text="Win Rate", x=0.5, y=0.38,
                font=dict(size=12,color=_text), showarrow=False)
            fig_pie.update_layout(**_base_layout(height=260, showlegend=True),
                legend=dict(orientation="h", yanchor="bottom", y=-0.08,
                            font=dict(color=_text)))
            st.plotly_chart(fig_pie, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # ROW 2 : P&L par position + P&L mensuel
        # ════════════════════════════════════════════════════════════════════
        r2c1, r2c2 = st.columns([3,2])

        with r2c1:
            _card("P&L par Position", f"{n_pos} trades — 1 barre = 1 position")
            fig_tl = go.Figure(go.Bar(
                x=pos_idx,
                y=df_s["pnl"].tolist(),
                marker_color=[_win if p>0 else _loss for p in df_s["pnl"]],
                marker_opacity=0.8,
                hovertemplate=(
                    "<b>Position #%{pointNumber+1}</b><br>"
                    "%{customdata[2]}<br>"
                    "%{customdata[0]} · %{customdata[1]}<br>"
                    "P&L : <b>%{y:+,.2f}$</b><extra></extra>"
                ),
                customdata=list(zip(
                    df_s["symbol"].tolist(),
                    df_s["direction"].tolist(),
                    pos_labels,
                )),
                showlegend=False,
            ))
            fig_tl.add_hline(y=0, line_color=_grid, line_width=1)
            fig_tl.update_layout(**_base_layout(height=280))
            _style_axes(fig_tl, yprefix="$", free_y=True)
            fig_tl.update_xaxes(**_xaxis_pos(n_pos))
            fig_tl.update_layout(dragmode="zoom")
            st.plotly_chart(fig_tl, use_container_width=True, config=_chart_cfg)

        with r2c2:
            _card("P&L Mensuel")
            fig_mo = go.Figure(go.Bar(
                x=monthly["label"].tolist(), y=monthly["pnl"].tolist(),
                marker=dict(
                    color=[_win if v>=0 else _loss for v in monthly["pnl"]],
                    opacity=0.85,
                    line=dict(color=_bg, width=0.5)
                ),
                hovertemplate="<b>%{x}</b><br>%{y:+,.2f}$<extra></extra>",
            ))
            fig_mo.add_hline(y=0, line_dash="dot", line_color=_grid, line_width=1)
            fig_mo.update_layout(**_base_layout(height=230))
            _style_axes(fig_mo, yprefix="$")
            st.plotly_chart(fig_mo, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # ROW 3 : Évolution R:R + P&L vs Volume
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Analyse Risque & Volume")
        r3c1, r3c2 = st.columns(2)

        with r3c1:
            _card("Évolution du R:R par trade", "Ratio risque/récompense dans le temps")
            df_rr = df_s[df_s["rr"].notna()].copy()
            if not df_rr.empty:
                rr_colors = [_win if r>=2 else _ora if r>=1 else _loss for r in df_rr["rr"]]
                fig_rr = go.Figure()
                # Ligne de tendance lissée
                # Axe X : datetime si disponible, sinon date
                if "datetime" in df_rr.columns and df_rr["datetime"].notna().any():
                    _xrr = pd.to_datetime(df_rr["datetime"], errors="coerce")
                    x_rr = _xrr.tolist() if _xrr.notna().sum() > 0 else df_rr["date"].tolist()
                else:
                    x_rr = df_rr["date"].tolist()

                if len(df_rr) >= 3:
                    rr_smooth = pd.Series(df_rr["rr"].values).rolling(
                        window=min(5,len(df_rr)), min_periods=1).mean()
                    fig_rr.add_trace(go.Scatter(
                        x=x_rr, y=rr_smooth.tolist(),
                        mode="lines", name="Tendance",
                        line=dict(color=_alt, width=1.5, dash="dash"),
                        hoverinfo="skip",
                    ))
                # Points R:R
                fig_rr.add_trace(go.Scatter(
                    x=x_rr, y=df_rr["rr"].tolist(),
                    mode="markers",
                    marker=dict(color=rr_colors, size=9,
                                line=dict(color=_bg, width=1.5)),
                    hovertemplate="<b>%{x}</b><br>%{customdata[0]} %{customdata[1]}<br>R:R : %{y:.2f}<extra></extra>",
                    customdata=list(zip(df_rr["symbol"].tolist(), df_rr["direction"].tolist())),
                    name="R:R",
                ))
                # Zones de référence
                fig_rr.add_hrect(y0=2, y1=max(df_rr["rr"].max()*1.1,3),
                    fillcolor="rgba(0,212,170,0.04)", line_width=0)
                fig_rr.add_hrect(y0=1, y1=2,
                    fillcolor="rgba(255,159,67,0.04)", line_width=0)
                fig_rr.add_hrect(y0=0, y1=1,
                    fillcolor="rgba(255,77,109,0.04)", line_width=0)
                fig_rr.add_hline(y=1, line_dash="dot", line_color=_ora, line_width=1,
                    annotation_text="1R", annotation_font=dict(color=_ora, size=10))
                fig_rr.add_hline(y=2, line_dash="dot", line_color=_win, line_width=1,
                    annotation_text="2R", annotation_font=dict(color=_win, size=10))
                fig_rr.update_layout(**_base_layout(height=260, showlegend=True),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15,
                                font=dict(color=_text, size=11)))
                _style_axes(fig_rr)
                fig_rr.update_yaxes(ticksuffix="R")
                st.plotly_chart(fig_rr, use_container_width=True)
                # Légende couleurs
                st.markdown(
                    '<div style="display:flex;gap:20px;font-size:11px;color:#6b7894;margin-top:-8px">'
                    f'<span><span style="color:{_win}">●</span> R:R ≥ 2 (excellent)</span>'
                    f'<span><span style="color:{_ora}">●</span> 1 ≤ R:R < 2 (correct)</span>'
                    f'<span><span style="color:{_loss}">●</span> R:R < 1 (insuffisant)</span>'
                    f'<span style="color:{_alt}">— Tendance</span>'
                    '</div>', unsafe_allow_html=True)
            else:
                st.info("Renseignez SL et TP lors de l'ajout de trades pour calculer le R:R.")

        with r3c2:
            _card("P&L en fonction du Volume", "Gain ou perte selon la taille de position")
            df_vol = df[df["entry"].notna() & df["entry"].ne(0)].copy()
            # Utiliser la colonne notes pour extraire le volume si disponible
            # Sinon utiliser entry comme proxy
            has_vol = False
            if "notes" in df_vol.columns:
                vol_extracted = df_vol["notes"].str.extract(r"vol:([\d.]+)")
                if vol_extracted[0].notna().sum() > 0:
                    df_vol["_vol"] = pd.to_numeric(vol_extracted[0], errors="coerce")
                    df_vol = df_vol[df_vol["_vol"].notna()]
                    has_vol = len(df_vol) > 0

            if not has_vol:
                # Fallback : regrouper par actif et montrer P&L par symbole
                _card_note = "Données de volume non disponibles — affichage par actif"
                by_sym_v = df.groupby("symbol").agg(
                    pnl=("pnl","sum"), trades=("pnl","count")).reset_index().sort_values("pnl")
                fig_vol = go.Figure(go.Bar(
                    y=by_sym_v["symbol"].tolist(),
                    x=by_sym_v["pnl"].tolist(),
                    orientation="h",
                    marker=dict(
                        color=[_win if v>=0 else _loss for v in by_sym_v["pnl"]],
                        opacity=0.85, line=dict(color=_bg, width=0.5)
                    ),
                    text=[f"{fmt(v)}" for v in by_sym_v["pnl"]],
                    textposition="outside",
                    textfont=dict(size=11, color=_text),
                    hovertemplate="<b>%{y}</b><br>P&L : %{x:+,.2f}$<br>%{customdata} trades<extra></extra>",
                    customdata=by_sym_v["trades"].tolist(),
                ))
                fig_vol.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
                fig_vol.update_layout(**_base_layout(height=260))
                _style_axes(fig_vol, xprefix="$")
                fig_vol.update_yaxes(categoryorder="total ascending")
                st.plotly_chart(fig_vol, use_container_width=True)
                st.caption("Volume non disponible dans les données — affichage P&L par actif. "
                           "Le volume est extrait des notes lors de l'import MT5.")
            else:
                # Scatter P&L vs Volume
                colors_v = [_win if p>0 else _loss for p in df_vol["pnl"]]
                sizes_v  = [max(8, min(30, abs(p)/max(1,abs(df_vol["pnl"]).max())*30))
                            for p in df_vol["pnl"]]
                fig_vol = go.Figure(go.Scatter(
                    x=df_vol["_vol"].tolist(), y=df_vol["pnl"].tolist(),
                    mode="markers",
                    marker=dict(color=colors_v, size=sizes_v, opacity=0.8,
                                line=dict(color=_bg, width=1.5)),
                    hovertemplate="<b>%{customdata[0]}</b><br>Volume : %{x}<br>P&L : %{y:+,.2f}$<extra></extra>",
                    customdata=list(zip(df_vol["symbol"].tolist(), df_vol["direction"].tolist())),
                ))
                # Ligne de tendance
                if len(df_vol) >= 3:
                    import numpy as np
                    try:
                        z = np.polyfit(df_vol["_vol"], df_vol["pnl"], 1)
                        p_fn = np.poly1d(z)
                        x_range = [df_vol["_vol"].min(), df_vol["_vol"].max()]
                        fig_vol.add_trace(go.Scatter(
                            x=x_range, y=[p_fn(x) for x in x_range],
                            mode="lines", line=dict(color=_alt, width=2, dash="dash"),
                            name="Tendance", hoverinfo="skip",
                        ))
                    except: pass
                fig_vol.add_hline(y=0, line_dash="dot", line_color=_grid, line_width=1)
                fig_vol.update_layout(**_base_layout(height=260, showlegend=True),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15))
                _style_axes(fig_vol, yprefix="$")
                fig_vol.update_xaxes(title_text="Volume (lots)")
                st.plotly_chart(fig_vol, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # ROW 4 : Classement actifs + Stratégies
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Analyse par Actif & Stratégie")
        r4c1, r4c2 = st.columns(2)

        with r4c1:
            _card("Classement des Actifs", "Rentabilité décroissante")
            by_sym = df.groupby("symbol").agg(
                pnl=("pnl","sum"), trades=("pnl","count"),
                wins=("pnl", lambda x: (x>0).sum()),
            ).reset_index()
            by_sym["win_rate"] = (by_sym["wins"]/by_sym["trades"]*100).round(1)
            by_sym = by_sym.sort_values("pnl", ascending=True)
            fig_sym = go.Figure(go.Bar(
                y=by_sym["symbol"].tolist(), x=by_sym["pnl"].tolist(),
                orientation="h",
                marker=dict(
                    color=[_win if v>=0 else _loss for v in by_sym["pnl"]],
                    opacity=0.85, line=dict(color=_bg, width=0.5),
                ),
                text=[f"{fmt(v)}  ·  {wr}% win" for v,wr in zip(by_sym["pnl"],by_sym["win_rate"])],
                textposition="outside", textfont=dict(size=11, color=_text),
                hovertemplate="<b>%{y}</b><br>P&L : %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                customdata=list(zip(by_sym["trades"].tolist(), by_sym["win_rate"].tolist())),
            ))
            fig_sym.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
            fig_sym.update_layout(**_base_layout(height=max(280,len(by_sym)*48)))
            _style_axes(fig_sym, xprefix="$")
            st.plotly_chart(fig_sym, use_container_width=True)

        with r4c2:
            _card("P&L par Stratégie")
            by_strat = df.groupby("strategy").agg(
                pnl=("pnl","sum"), trades=("pnl","count"),
                wins=("pnl", lambda x: (x>0).sum()),
            ).reset_index()
            by_strat["win_rate"] = (by_strat["wins"]/by_strat["trades"]*100).round(1)
            by_strat = by_strat.sort_values("pnl", ascending=True)
            fig_st = go.Figure(go.Bar(
                y=by_strat["strategy"].tolist(), x=by_strat["pnl"].tolist(),
                orientation="h",
                marker=dict(color=CHART_COLORS[:len(by_strat)], opacity=0.85,
                            line=dict(color=_bg, width=0.5)),
                text=[f"{fmt(v)}  ·  {wr}% win" for v,wr in zip(by_strat["pnl"],by_strat["win_rate"])],
                textposition="outside", textfont=dict(size=11, color=_text),
                hovertemplate="<b>%{y}</b>: %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                customdata=list(zip(by_strat["trades"].tolist(), by_strat["win_rate"].tolist())),
            ))
            fig_st.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
            fig_st.update_layout(**_base_layout(height=max(280,len(by_strat)*48)))
            _style_axes(fig_st, xprefix="$")
            st.plotly_chart(fig_st, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # ROW 5 : Heatmap + P&L par émotion
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Psychologie de Trading")
        r5c1, r5c2 = st.columns([3,2])

        with r5c1:
            _card("Heatmap Rentabilité", "Actif × Émotion")
            if len(df["symbol"].unique()) >= 1 and len(df["mood"].unique()) >= 1:
                pivot = df.pivot_table(values="pnl", index="mood", columns="symbol",
                                       aggfunc="sum", fill_value=0)
                mood_order = [m for m in ["Euphorique","Confiant","Neutre","Anxieux","Peureux","Frustré"]
                              if m in pivot.index]
                pivot = pivot.reindex(mood_order)
                fig_hm = go.Figure(go.Heatmap(
                    z=pivot.values.tolist(),
                    x=pivot.columns.tolist(),
                    y=pivot.index.tolist(),
                    colorscale=[
                        [0.0,"#ff4d6d"],[0.4,"#2d1520"],[0.5,"#1e2535"],
                        [0.6,"#152d25"],[1.0,"#00d4aa"],
                    ],
                    zmid=0,
                    text=[[f"${v:+,.0f}" for v in row] for row in pivot.values],
                    texttemplate="%{text}",
                    textfont=dict(size=12, color="white"),
                    hovertemplate="<b>%{y} · %{x}</b><br>P&L : %{z:+,.2f}$<extra></extra>",
                    showscale=True,
                    colorbar=dict(tickprefix="$", tickfont=dict(color=_text, size=11),
                                  bgcolor=_bg, bordercolor=_grid, thickness=12),
                ))
                fig_hm.update_layout(
                    paper_bgcolor=_bg, plot_bgcolor=_bg,
                    font=dict(color=_text, family="DM Sans, sans-serif"),
                    height=max(280, len(pivot)*60),
                    margin=dict(l=100, r=60, t=20, b=60),
                    showlegend=False,
                )
                fig_hm.update_xaxes(side="bottom", tickangle=-30,
                                    gridcolor=_grid, linecolor=_grid)
                fig_hm.update_yaxes(gridcolor=_grid, linecolor=_grid)
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("Pas assez de données pour la heatmap.")

        with r5c2:
            _card("P&L par Émotion")
            by_mood = df.groupby("mood").agg(
                pnl=("pnl","sum"), trades=("pnl","count"),
                wins=("pnl", lambda x: (x>0).sum()),
            ).reset_index()
            by_mood["win_rate"] = (by_mood["wins"]/by_mood["trades"]*100).round(1)
            by_mood["label"]    = by_mood["mood"]
            by_mood = by_mood.sort_values("pnl", ascending=True)
            fig_mood = go.Figure(go.Bar(
                y=by_mood["label"].tolist(), x=by_mood["pnl"].tolist(),
                orientation="h",
                marker=dict(
                    color=[_win if v>=0 else _loss for v in by_mood["pnl"]],
                    opacity=0.85, line=dict(color=_bg, width=0.5)
                ),
                text=[f"{fmt(v)}  ·  {wr}% win  ·  {n}t"
                      for v,wr,n in zip(by_mood["pnl"],by_mood["win_rate"],by_mood["trades"])],
                textposition="outside", textfont=dict(size=11, color=_text),
                hovertemplate="<b>%{y}</b><br>P&L : %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                customdata=list(zip(by_mood["trades"].tolist(), by_mood["win_rate"].tolist())),
            ))
            fig_mood.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
            fig_mood.update_layout(**_base_layout(height=max(280,len(by_mood)*60)))
            _style_axes(fig_mood, xprefix="$")
            st.plotly_chart(fig_mood, use_container_width=True)

        # ════════════════════════════════════════════════════════════════════
        # STATISTIQUES CALENDAIRES — jour de semaine, heure, heatmap
        # (héritent des filtres actif/émotion/stratégie/dates du dashboard)
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Statistiques calendaires")

        df_cal_stats = df.copy()
        if "datetime" in df_cal_stats.columns:
            df_cal_stats["_dtp"] = pd.to_datetime(df_cal_stats["datetime"], errors="coerce")
        else:
            df_cal_stats["_dtp"] = pd.NaT

        _jours_fr = {"Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi",
                    "Thursday":"Jeudi","Friday":"Vendredi","Saturday":"Samedi","Sunday":"Dimanche"}
        _jours_ordre = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
        df_cal_stats["_weekday"] = pd.to_datetime(df_cal_stats["date"]).dt.day_name().map(_jours_fr)

        # ── FILTRES SPÉCIFIQUES AUX GRAPHIQUES CALENDAIRES ───────────────────
        st.markdown('<div style="background:#111520;border:1px solid #1e2535;'
                    'border-radius:14px;padding:14px 18px;margin:8px 0 16px">',
                    unsafe_allow_html=True)
        kc1, kc2, kc3 = st.columns([1.4, 2.2, 2])
        with kc1:
            cal_metric = st.selectbox(
                "Métrique", ["P&L net", "Nombre de trades", "Win rate %", "R:R moyen"],
                key="cal_metric")
        with kc2:
            cal_days = st.multiselect(
                "Jours de semaine", _jours_ordre, default=_jours_ordre,
                key="cal_days_filter")
        with kc3:
            cal_hours = st.slider("Plage horaire", 0, 23, (0, 23), key="cal_hours_filter")
        st.markdown('</div>', unsafe_allow_html=True)

        # Application des filtres calendaires
        if cal_days:
            df_cal_stats = df_cal_stats[df_cal_stats["_weekday"].isin(cal_days)]
        _h_series = df_cal_stats["_dtp"].dt.hour
        _hour_mask = _h_series.between(cal_hours[0], cal_hours[1]) | _h_series.isna()
        df_cal_stats = df_cal_stats[_hour_mask]

        _has_hours = df_cal_stats["_dtp"].notna().any()
        _days_shown = [d for d in _jours_ordre if d in (cal_days or _jours_ordre)]

        if df_cal_stats.empty:
            st.info("Aucun trade ne correspond à ces filtres calendaires.")
        else:
            # ── Agrégation selon la métrique choisie ─────────────────────────
            def _agg_metric(grouped):
                """Retourne (Series valeurs, Series nb trades, suffixe, préfixe axe)."""
                n = grouped["pnl"].count()
                if cal_metric == "P&L net":
                    return grouped["pnl"].sum(), n, "$", "$"
                if cal_metric == "Nombre de trades":
                    return n.astype(float), n, "", ""
                if cal_metric == "Win rate %":
                    return grouped["pnl"].apply(
                        lambda s: (s > 0).sum()/len(s)*100 if len(s) else 0), n, "%", ""
                # R:R moyen
                return grouped["rr"].mean().fillna(0), n, "R", ""

            _neutral = cal_metric in ("Nombre de trades",)
            def _bar_colors(vals):
                if _neutral:
                    return ["#7c6aff"] * len(vals)
                if cal_metric == "Win rate %":
                    return ["#00d4aa" if v >= 50 else "#ff4d6d" for v in vals]
                if cal_metric == "R:R moyen":
                    return ["#00d4aa" if v >= 1 else "#ff4d6d" for v in vals]
                return ["#00d4aa" if v >= 0 else "#ff4d6d" for v in vals]

            cs1, cs2 = st.columns(2)

            with cs1:
                _card(f"{cal_metric} par jour de semaine")
                g_wd = df_cal_stats.groupby("_weekday")
                vals_wd, n_wd, suffix, yprefix = _agg_metric(g_wd)
                vals_wd = vals_wd.reindex(_days_shown, fill_value=0)
                n_wd    = n_wd.reindex(_days_shown, fill_value=0)
                fig_wd = go.Figure(go.Bar(
                    x=vals_wd.index.tolist(), y=vals_wd.tolist(),
                    marker_color=_bar_colors(vals_wd), marker_opacity=0.85,
                    customdata=n_wd.tolist(),
                    hovertemplate="<b>%{x}</b><br>" + cal_metric +
                                 " : %{y:,.2f}" + suffix +
                                 "<br>%{customdata} trades<extra></extra>",
                ))
                if not _neutral:
                    fig_wd.add_hline(y=0, line_color=_grid, line_width=1)
                fig_wd.update_layout(**_base_layout(height=260))
                _style_axes(fig_wd, yprefix=yprefix)
                st.plotly_chart(fig_wd, use_container_width=True)

            with cs2:
                _card(f"{cal_metric} par heure de la journée")
                if _has_hours:
                    _df_hr = df_cal_stats[df_cal_stats["_dtp"].notna()].copy()
                    _df_hr["_hour"] = _df_hr["_dtp"].dt.hour.astype(int)
                    _hrange = list(range(cal_hours[0], cal_hours[1] + 1))
                    g_hr = _df_hr.groupby("_hour")
                    vals_hr, n_hr, suffix, yprefix = _agg_metric(g_hr)
                    vals_hr = vals_hr.reindex(_hrange, fill_value=0)
                    n_hr    = n_hr.reindex(_hrange, fill_value=0)
                    fig_hrd = go.Figure(go.Bar(
                        x=[f"{int(h):02d}h" for h in vals_hr.index],
                        y=vals_hr.tolist(),
                        marker_color=_bar_colors(vals_hr), marker_opacity=0.85,
                        customdata=n_hr.tolist(),
                        hovertemplate="<b>%{x}</b><br>" + cal_metric +
                                     " : %{y:,.2f}" + suffix +
                                     "<br>%{customdata} trades<extra></extra>",
                    ))
                    if not _neutral:
                        fig_hrd.add_hline(y=0, line_color=_grid, line_width=1)
                    fig_hrd.update_layout(**_base_layout(height=260))
                    _style_axes(fig_hrd, yprefix=yprefix)
                    st.plotly_chart(fig_hrd, use_container_width=True)
                else:
                    st.info("Aucune heure enregistrée sur la période filtrée.")

            # ── Heatmap Jour × Heure ─────────────────────────────────────────
            if _has_hours:
                _card(f"Heatmap Jour de semaine × Heure", cal_metric)
                _df_hm = df_cal_stats[df_cal_stats["_dtp"].notna()].copy()
                _df_hm["_hour2"] = _df_hm["_dtp"].dt.hour.astype(int)
                if cal_metric == "P&L net":
                    _aggf = "sum"; _vcol = "pnl"
                elif cal_metric == "Nombre de trades":
                    _aggf = "count"; _vcol = "pnl"
                elif cal_metric == "Win rate %":
                    _df_hm["_is_win"] = (_df_hm["pnl"] > 0).astype(float) * 100
                    _aggf = "mean"; _vcol = "_is_win"
                else:
                    _aggf = "mean"; _vcol = "rr"
                pivot_wh = _df_hm.pivot_table(
                    index="_weekday", columns="_hour2", values=_vcol,
                    aggfunc=_aggf, fill_value=0).reindex(_days_shown, fill_value=0)
                if not pivot_wh.empty and pivot_wh.shape[1] > 0:
                    _vals = pivot_wh.values.astype(float)
                    if _neutral:
                        _cscale = [[0,"#111520"],[1,"rgba(124,106,255,0.9)"]]
                        _zmid, _zmin, _zmax = None, None, None
                    elif cal_metric == "Win rate %":
                        _cscale = [[0,"rgba(255,77,109,0.85)"],[0.5,"#111520"],[1,"rgba(0,212,170,0.85)"]]
                        _zmid, _zmin, _zmax = 50, 0, 100
                    else:
                        _m = max(abs(np.nanmin(_vals)), abs(np.nanmax(_vals)), 1)
                        _cscale = [[0,"rgba(255,77,109,0.85)"],[0.5,"#111520"],[1,"rgba(0,212,170,0.85)"]]
                        _zmid, _zmin, _zmax = (1 if cal_metric=="R:R moyen" else 0), -_m if cal_metric!="R:R moyen" else 0, _m
                    _hm_kwargs = dict(
                        z=_vals,
                        x=[f"{int(h):02d}h" for h in pivot_wh.columns],
                        y=pivot_wh.index.tolist(),
                        colorscale=_cscale,
                        hovertemplate="<b>%{y} · %{x}</b><br>" + cal_metric +
                                     " : %{z:,.2f}" + suffix + "<extra></extra>",
                        showscale=True,
                        colorbar=dict(tickfont=dict(color=_text, size=10), thickness=10),
                    )
                    if _zmid is not None:
                        _hm_kwargs.update(zmid=_zmid, zmin=_zmin, zmax=_zmax)
                    fig_hm = go.Figure(go.Heatmap(**_hm_kwargs))
                    fig_hm.update_layout(**_base_layout(height=280))
                    fig_hm.update_xaxes(gridcolor=_grid, linecolor=_grid)
                    fig_hm.update_yaxes(gridcolor=_grid, linecolor=_grid)
                    st.plotly_chart(fig_hm, use_container_width=True)
                else:
                    st.info("Pas assez de données horaires pour la heatmap.")
        st.markdown(" ")

        # ════════════════════════════════════════════════════════════════════
        # ROW 6 : Derniers trades
        # ════════════════════════════════════════════════════════════════════
        st.markdown("### Derniers Trades")
        recent = df.sort_values("date", ascending=False).head(8)
        rows_html = ""
        for _, t in recent.iterrows():
            c  = "#00d4aa" if t["pnl"]>=0 else "#ff4d6d"
            dc = "b-win" if t["direction"]=="LONG" else "b-loss"
            _tm = t.get("trade_mode","Réel Indépendant")
            mc = "b-demo" if _tm == "Démo" else ("b-inst" if _tm == "Réel Institutionnel" else "b-real")
            rows_html += f"""<tr>
                <td style="color:#6b7894;font-family:monospace">{t["date"]}</td>
                <td>{badge(t["symbol"],"b-sym")}</td>
                <td>{badge(t["direction"],dc)}</td>
                <td>{badge(t.get("trade_mode","Réel Indépendant"),mc)}</td>
                <td style="font-size:15px;text-align:center">{mood_html(t["mood"])}</td>
                <td>{badge(t["strategy"],"b-str")}</td>
                <td style="font-family:monospace;font-weight:800;color:{c}">{fmt(t["pnl"])}</td>
                <td style="color:#6b7894;font-size:12px">{str(t.get("notes",""))[:40]}</td>
            </tr>"""
        st.markdown(f"""<table class="tj-table"><thead><tr>
            <th>Date</th><th>Actif</th><th>Dir.</th><th>Mode</th>
            <th>Mood</th><th>Stratégie</th><th>P&L $</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)



elif st.session_state.page == "journal":
    st.markdown("# Journal des Trades")
    mode_banner()

    df_all = get_df("Tous")

    if df_all.empty:
        st.info("Aucun trade. Ajoutez-en un avec **Nouveau Trade** ou importez depuis MT5.")
    else:
        # ══════════════════════════════════════════════════════════════════════
        # ACTIONS EN HAUT — modifier / supprimer
        # ══════════════════════════════════════════════════════════════════════
        with st.expander("Modifier ou supprimer des trades", expanded=True):
            tab1, tab2 = st.tabs(["  Un trade", "  Plusieurs trades"])

            # ── Onglet : UN TRADE ─────────────────────────────────────────────
            with tab1:
                df_all_s = df_all.sort_values("date", ascending=False)
                labels_one = [
                    f"{r['date']}  ·  {r['symbol']}  ·  {r.get('trade_mode','Réel Indépendant')}  ·  {r['direction']}  ·  {fmt(r['pnl'])}"
                    for _, r in df_all_s.iterrows()
                ]
                ids_one = df_all_s["id"].tolist()

                sel_lbl   = st.selectbox("Sélectionner un trade",
                                         labels_one, label_visibility="collapsed")
                sel_id    = ids_one[labels_one.index(sel_lbl)]
                sel_trade = next((t for t in st.session_state.trades
                                  if t["id"] == sel_id), None)

                if sel_trade:
                    pnl_s = sel_trade.get("pnl", 0)
                    col_s = "#00d4aa" if pnl_s >= 0 else "#ff4d6d"
                    st.markdown(
                        f'''<div style="background:#0d111d;border:1px solid #1e2535;
                            border-radius:10px;padding:10px 16px;margin:6px 0;
                            display:flex;gap:20px;align-items:center;flex-wrap:wrap">
                            <span style="color:#6b7894;font-family:monospace">{sel_trade.get("date","")}</span>
                            <span style="font-weight:700">{sel_trade.get("symbol","")}</span>
                            <span style="color:#7c6aff">{sel_trade.get("direction","")}</span>
                            <span style="color:{col_s};font-weight:800;font-family:monospace">{fmt(pnl_s)}</span>
                            <span style="color:#6b7894;font-size:12px">{sel_trade.get("strategy","")}</span>
                            <span style="color:#6b7894;font-size:12px">{str(sel_trade.get("notes",""))[:50]}</span>
                        </div>''', unsafe_allow_html=True)

                ce, cd, _ = st.columns([1, 1, 5])
                with ce:
                    if st.button("Modifier", icon=":material/edit:",
                                 use_container_width=True, key="btn_edit_one"):
                        st.session_state.edit_id = sel_id
                        st.session_state.page = "add"
                        st.rerun()
                with cd:
                    if st.button("Supprimer", icon=":material/delete:",
                                 use_container_width=True, key="btn_del_one"):
                        st.session_state["confirm_del"] = sel_id

                if st.session_state.get("confirm_del") == sel_id:
                    st.warning(
                        f"Confirmer la suppression de **{sel_trade.get('date','')} · "
                        f"{sel_trade.get('symbol','')} · {fmt(sel_trade.get('pnl',0))}** ?"
                    )
                    cc1, cc2, _ = st.columns([1, 1, 5])
                    with cc1:
                        if st.button("Oui, supprimer", icon=":material/check:",
                                     use_container_width=True, key="btn_confirm_del"):
                            st.session_state.trades = [
                                t for t in st.session_state.trades if t["id"] != sel_id
                            ]
                            ok = cloud_save(st.session_state.trades)
                            st.session_state.pop("confirm_del", None)
                            st.success("Supprimé." if ok else "Erreur sauvegarde.")
                            st.rerun()
                    with cc2:
                        if st.button("Annuler", icon=":material/close:",
                                     use_container_width=True, key="btn_cancel_del"):
                            st.session_state.pop("confirm_del", None)
                            st.rerun()

            # ── Onglet : PLUSIEURS TRADES ────────────────────────────────────
            with tab2:
                df_multi = df_all.sort_values("date", ascending=False)

                # ── 1. FILTRES ─────────────────────────────────────────────
                mf1, mf2, mf3, mf4, mf5 = st.columns(5)
                dates_m = sorted(df_all["date"].dropna().unique().tolist())
                d_min_m = date.fromisoformat(dates_m[0])  if dates_m else date(2024,1,1)
                d_max_m = date.fromisoformat(dates_m[-1]) if dates_m else date.today()
                with mf1: mf_from = st.date_input("Du",    value=d_min_m, key="mf_from")
                with mf2: mf_to   = st.date_input("Au",    value=d_max_m, key="mf_to")
                with mf3: mf_sym  = st.selectbox("Actif",  ["Tous"]+sorted(df_all["symbol"].unique().tolist()), key="mf_sym")
                with mf4: mf_mode = st.selectbox("Mode",   MODE_FILTER_OPTIONS, key="mf_mode")
                with mf5: mf_dir  = st.selectbox("Dir.",   ["Tous","LONG","SHORT"], key="mf_dir")

                df_multi = df_multi[df_multi["date"].between(str(mf_from), str(mf_to))]
                if mf_sym  != "Tous": df_multi = df_multi[df_multi["symbol"]   == mf_sym]
                if mf_mode != "Tous": df_multi = df_multi[df_multi["trade_mode"] == mf_mode]
                if mf_dir  != "Tous": df_multi = df_multi[df_multi["direction"] == mf_dir]
                filtered_ids = df_multi["id"].tolist()

                # ── 2. SÉLECTION RAPIDE ────────────────────────────────────
                sc1, sc2, sc3 = st.columns([1, 1, 4])
                with sc1:
                    if st.button("Tout sélectionner", use_container_width=True,
                                 key="sel_all", icon=":material/select_all:"):
                        for _tid in filtered_ids:
                            st.session_state[f"chk_{_tid}"] = True
                        st.rerun()
                with sc2:
                    if st.button("Tout désélectionner", use_container_width=True,
                                 key="desel_all", icon=":material/deselect:"):
                        for _tid in filtered_ids:
                            st.session_state[f"chk_{_tid}"] = False
                        st.rerun()

                # ── 3. BOUTON SUPPRIMER + CONFIRMATION (AVANT les checkboxes) ──
                selected_ids = {
                    tid for tid in filtered_ids
                    if st.session_state.get(f"chk_{tid}", False)
                }
                n_sel = len(selected_ids)

                if n_sel > 0:
                    sel_data = [t for t in st.session_state.trades if t["id"] in selected_ids]
                    pnl_sel  = sum(t.get("pnl", 0) for t in sel_data)
                    col_psel = "#00d4aa" if pnl_sel >= 0 else "#ff4d6d"

                    # Bandeau résumé + bouton supprimer
                    st.markdown(
                        f'''<div style="background:#ff4d6d12;border:1px solid #ff4d6d55;
                            border-radius:10px;padding:10px 16px;margin:8px 0;
                            display:flex;gap:24px;align-items:center;flex-wrap:wrap">
                            <span style="color:#ff4d6d;font-weight:700">
                                <i class="fa-solid fa-triangle-exclamation"></i>
                                &nbsp;{n_sel} trade{"s" if n_sel>1 else ""} sélectionné{"s" if n_sel>1 else ""}
                            </span>
                            <span style="color:#6b7894">
                                P&L sélection : <b style="color:{col_psel}">{fmt(pnl_sel)}</b>
                            </span>
                        </div>''', unsafe_allow_html=True)

                    bd1, bd2, _ = st.columns([1.5, 1, 4])
                    with bd1:
                        if st.button(
                            f"Supprimer {n_sel} trade{'s' if n_sel>1 else ''}",
                            icon=":material/delete_sweep:",
                            use_container_width=True, key="btn_del_multi"
                        ):
                            st.session_state["confirm_multi"] = True

                    # Confirmation immédiatement sous le bouton
                    if st.session_state.get("confirm_multi"):
                        st.error(
                            f"Supprimer définitivement **{n_sel} trade{'s' if n_sel>1 else ''}** "
                            f"(P&L total : {fmt(pnl_sel)}) ?"
                        )
                        cm1, cm2, _ = st.columns([1, 1, 5])
                        with cm1:
                            if st.button("Confirmer la suppression",
                                         icon=":material/check:",
                                         use_container_width=True, key="btn_multi_yes"):
                                st.session_state.trades = [
                                    t for t in st.session_state.trades
                                    if t["id"] not in selected_ids
                                ]
                                ok = cloud_save(st.session_state.trades)
                                for _tid in selected_ids:
                                    st.session_state.pop(f"chk_{_tid}", None)
                                st.session_state.pop("confirm_multi", None)
                                st.success(f"{n_sel} trade(s) supprimé(s)." if ok else "Erreur sauvegarde.")
                                st.rerun()
                        with cm2:
                            if st.button("Annuler", icon=":material/close:",
                                         use_container_width=True, key="btn_multi_no"):
                                st.session_state.pop("confirm_multi", None)
                                st.rerun()

                    st.markdown("---")

                else:
                    st.caption(f"{len(filtered_ids)} trades · Cochez ceux à supprimer")

                # ── 4. LISTE DES CHECKBOXES ────────────────────────────────
                for _, row in df_multi.iterrows():
                    tid = row["id"]
                    c_pnl = "#00d4aa" if row["pnl"] >= 0 else "#ff4d6d"
                    st.checkbox(
                        f"{row['date']}  ·  {row['symbol']}  ·  "
                        f"{row.get('trade_mode','Réel Indépendant')}  ·  {row['direction']}  ·  {fmt(row['pnl'])}",
                        key=f"chk_{tid}"
                    )

        # ══════════════════════════════════════════════════════════════════════
        # FILTRES + TABLEAU
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("---")

        fa1, fa2, fa3, fa4, fa5 = st.columns(5)
        dates_avail = sorted(df_all["date"].dropna().unique().tolist())
        d_min = date.fromisoformat(dates_avail[0])  if dates_avail else date(2024,1,1)
        d_max = date.fromisoformat(dates_avail[-1]) if dates_avail else date.today()

        with fa1: f_from = st.date_input("Du",        value=d_min, key="j_from")
        with fa2: f_to   = st.date_input("Au",        value=d_max, key="j_to")
        with fa3: f_sym  = st.selectbox("Actif",      ["Tous"]+sorted(df_all["symbol"].unique().tolist()), key="j_sym")
        with fa4: f_mode = st.selectbox("Mode",       MODE_FILTER_OPTIONS, key="j_mode")
        with fa5: f_dir  = st.selectbox("Direction",  ["Tous","LONG","SHORT"], key="j_dir")

        df = df_all.copy()
        df = df[df["date"].between(str(f_from), str(f_to))]
        if f_sym  != "Tous": df = df[df["symbol"]    == f_sym]
        if f_mode != "Tous": df = df[df["trade_mode"] == f_mode]
        if f_dir  != "Tous": df = df[df["direction"] == f_dir]
        df = df.sort_values("date", ascending=False)

        # Résumé
        if not df.empty:
            total_f = df["pnl"].sum()
            wins_f  = len(df[df["pnl"] > 0])
            col_f   = "#00d4aa" if total_f >= 0 else "#ff4d6d"
            st.markdown(
                f'''<div style="display:flex;gap:24px;align-items:center;
                    padding:8px 14px;background:#0d111d;border-radius:8px;
                    border:1px solid #1e2535;margin:10px 0;font-size:13px">
                    <span style="color:#6b7894">
                        <b style="color:#e8ecf4">{len(df)}</b> trades
                    </span>
                    <span style="color:#6b7894">
                        P&L : <b style="color:{col_f}">{fmt(total_f)}</b>
                    </span>
                    <span style="color:#6b7894">
                        Win rate : <b style="color:#00d4aa">
                        {len(df[df["pnl"]>0])/len(df)*100:.0f}%</b>
                    </span>
                </div>''', unsafe_allow_html=True)

        if df.empty:
            st.info("Aucun trade pour ces filtres.")
        else:
            rows_html = ""
            for _, t in df.iterrows():
                c    = "#00d4aa" if t["pnl"]>=0 else "#ff4d6d"
                dc   = "b-win" if t["direction"]=="LONG" else "b-loss"
                rr_v = t["rr"]
                rr_c = "#00d4aa" if (rr_v or 0)>=2 else "#ff9f43" if (rr_v or 0)>=1 else "#ff4d6d"
                _tm2 = t.get("trade_mode","Réel Indépendant")
                mc   = "b-demo" if _tm2 == "Démo" else ("b-inst" if _tm2 == "Réel Institutionnel" else "b-real")
                rows_html += f"""<tr>
                    <td style="color:#6b7894;font-family:monospace;white-space:nowrap">{t["date"]}</td>
                    <td>{badge(t["symbol"],"b-sym")}</td>
                    <td>{badge(t["direction"],dc)}</td>
                    <td>{badge(t.get("trade_mode","Réel Indépendant"),mc)}</td>
                    <td style="font-family:monospace">{t.get("entry","—")}</td>
                    <td style="font-family:monospace">{t.get("exit","—")}</td>
                    <td style="font-family:monospace;font-weight:800;color:{c};white-space:nowrap">{fmt(t["pnl"])}</td>
                    <td style="font-family:monospace;color:{rr_c}">{rr_v if rr_v else "—"}</td>
                    <td>{badge(t["strategy"],"b-str")}</td>
                    <td style="text-align:center">{mood_html(t["mood"])}</td>
                    <td style="color:#6b7894;font-size:12px;max-width:160px">{str(t.get("notes",""))[:45]}</td>
                </tr>"""
            st.markdown(
                f"""<div style="overflow-x:auto"><table class="tj-table">
                <thead><tr>
                    <th>Date</th><th>Actif</th><th>Dir.</th><th>Mode</th>
                    <th>Entrée</th><th>Sortie</th><th>P&L $</th><th>R:R</th>
                    <th>Stratégie</th><th>Mood</th><th>Notes</th>
                </tr></thead><tbody>{rows_html}</tbody></table></div>""",
                unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : ADD / EDIT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "add":
    is_edit = st.session_state.edit_id is not None
    st.markdown(f"# {'Modifier le Trade' if is_edit else 'Nouveau Trade'}")
    if st.button("Retour", icon=":material/arrow_back:"):
        st.session_state.page="journal"; st.session_state.edit_id=None; st.rerun()
    st.divider()

    with st.form("form_trade"):
        r1c1,r1c2,r1c3,r1c4 = st.columns(4)
        with r1c1: d_date = st.date_input("Date", value=date.fromisoformat(ev("date",str(date.today()))))
        with r1c2: d_sym  = st.selectbox("Symbole", SYMBOLS, index=SYMBOLS.index(ev("symbol","EUR/USD")) if ev("symbol","EUR/USD") in SYMBOLS else 0)
        with r1c3: d_dir  = st.selectbox("Direction", ["LONG","SHORT"], index=["LONG","SHORT"].index(ev("direction","LONG")))
        with r1c4:
            cur_mode = ev("trade_mode","Réel Indépendant")
            d_mode = st.selectbox("Mode", TRADE_MODES, index=TRADE_MODES.index(cur_mode) if cur_mode in TRADE_MODES else 0)

        r2c1,r2c2,r2c3,r2c4 = st.columns(4)
        with r2c1: d_entry = st.number_input("Prix d'entrée",  value=float(ev("entry",0.0)), format="%.5f",step=0.0001)
        with r2c2: d_exit  = st.number_input("Prix de sortie", value=float(ev("exit",0.0)),  format="%.5f",step=0.0001)
        with r2c3: d_sl    = st.number_input("Stop Loss",      value=float(ev("sl",0.0)),    format="%.5f",step=0.0001)
        with r2c4: d_tp    = st.number_input("Take Profit",    value=float(ev("tp",0.0)),    format="%.5f",step=0.0001)

        r3c1,r3c2 = st.columns(2)
        strat_val  = ev("strategy","Breakout")
        strat_list = STRATEGIES if strat_val in STRATEGIES else [strat_val] + STRATEGIES
        mood_val   = ev("mood","Confiant")
        mood_list  = MOODS if mood_val in MOODS else [mood_val] + MOODS
        with r3c1: d_strat = st.selectbox("Stratégie",    strat_list, index=0)
        with r3c2: d_mood  = st.selectbox("État d'esprit",mood_list,  index=0)

        st.markdown("""<div style="background:#0d111d;border:2px solid #00d4aa44;border-radius:12px;
            padding:14px 20px;margin:12px 0 4px">
            <div style="font-size:11px;color:#00d4aa;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;margin-bottom:4px">
                P&L Réel — tel qu'affiché par votre broker</div>
            <div style="font-size:12px;color:#6b7894">Saisissez le résultat exact · spread, commission et swap inclus</div>
        </div>""", unsafe_allow_html=True)

        pc1,pc2 = st.columns([1,3])
        with pc1:
            d_pnl = st.number_input("P&L ($)", value=float(ev("pnl",0.0)), format="%.2f", step=0.01)
        with pc2:
            if d_pnl != 0:
                color = "#00d4aa" if d_pnl>=0 else "#ff4d6d"
                sign  = "GAIN" if d_pnl>=0 else "PERTE"
                rr_h  = ""
                if d_entry and d_sl and d_tp:
                    risk = abs(d_entry-d_sl)
                    if risk:
                        rr_v = round(abs(d_tp-d_entry)/risk,2)
                        rr_h = f" &nbsp;·&nbsp; <span style='color:#7c6aff'>R:R {rr_v}</span>"
                st.markdown(f"""<div style="margin-top:26px;font-size:24px;font-weight:800;
                    font-family:'JetBrains Mono',monospace;color:{color}">
                    {sign} &nbsp; {fmt(d_pnl)}{rr_h}</div>""", unsafe_allow_html=True)

        d_notes = st.text_area("Notes & Analyse", value=ev("notes",""),
            placeholder="Raison du trade, contexte, leçons...", height=80)

        if st.form_submit_button("Sauvegarder" if is_edit else "Enregistrer le Trade", use_container_width=True):
            ex    = next((t for t in st.session_state.trades if t["id"]==st.session_state.edit_id),None)
            # Construire le datetime complet pour l'intraday
            _time_clean = d_time.strip() if d_time.strip() else "00:00"
            try: datetime.strptime(_time_clean, "%H:%M")
            except: _time_clean = "00:00"
            _dt_str = f"{d_date}T{_time_clean}"
            new_t = {"id":ex["id"] if is_edit else int(datetime.now().timestamp()*1000),
                "date":str(d_date),"time":_time_clean,"datetime":_dt_str,
                "symbol":d_sym,"direction":d_dir,"trade_mode":d_mode,
                "entry":d_entry,"exit":d_exit,"sl":d_sl,"tp":d_tp,"pnl":d_pnl,
                "strategy":d_strat,"mood":d_mood,"notes":d_notes}
            if is_edit:
                st.session_state.trades=[new_t if t["id"]==ex["id"] else t for t in st.session_state.trades]
            else:
                st.session_state.trades.append(new_t)
            ok = cloud_save(st.session_state.trades)
            st.success("Synchronisé." if ok else "Sauvegardé localement (vérifiez la connexion).")
            st.session_state.page="journal"; st.session_state.edit_id=None; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : IMPORT MT5
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "import":
    st.markdown("# Importer depuis MetaTrader 5")
    if st.button("Retour", icon=":material/arrow_back:"):
        st.session_state.page = "journal"; st.rerun()
    st.divider()

    # ── Mode du compte ────────────────────────────────────────────────────────
    ic1, ic2 = st.columns([2, 3])
    with ic1:
        imp_mode = st.radio("Type de compte", TRADE_MODES, horizontal=True)
    with ic2:
        _mc_map = {"Démo":"mode-banner-demo","Réel Indépendant":"mode-banner-real",
                   "Réel Institutionnel":"mode-banner-inst"}
        mc = _mc_map.get(imp_mode, "mode-banner-real")
        st.markdown(f'<div class="{mc}" style="margin-top:8px">Trades étiquetés : {imp_mode}</div>',
                    unsafe_allow_html=True)

    st.markdown("---")

    with st.expander("Comment exporter depuis MT5 ?", expanded=False):
        st.markdown("""
        1. MT5 → **Affichage → Historique des transactions**
        2. Clic droit → **Enregistrer en tant que rapport** → **XLSX** ou **CSV**

        **Colonnes attendues** :  
        `Time · Position · Symbol · Type · Volume · Price · S/L · T/P · Time · Price · Commission · Swap · Profit`
        """)

    # ── Option calcul P&L ─────────────────────────────────────────────────────
    st.markdown("##### Calcul du P&L")
    pnl_method = st.radio(
        "Méthode de calcul",
        [
            "Profit + Commission + Swap  (P&L brut + tous les coûts)",
            "Profit uniquement  (si MT5 affiche déjà le net)",
        ],
        horizontal=True,
        help="Si le P&L importé semble surestimé, essayez 'Profit uniquement'."
    )
    use_costs = "Profit +" in pnl_method

    st.markdown("---")

    uploaded = st.file_uploader(
        "Choisir le fichier MT5 (CSV, TXT ou XLSX)",
        type=["csv", "txt", "xlsx", "xls"],
        label_visibility="collapsed"
    )

    if uploaded:
        fname      = uploaded.name.lower()
        file_bytes = uploaded.getvalue()

        # ── Lecture fichier ───────────────────────────────────────────────────
        try:
            if fname.endswith((".xlsx", ".xls")):
                xls_scan  = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)
                header_row = 0
                for i, row in xls_scan.iterrows():
                    vals = [str(v).strip().lower() for v in row.values]
                    if any(k in vals for k in ["symbol","time","profit","type","position"]):
                        header_row = i; break
                df_raw = pd.read_excel(io.BytesIO(file_bytes), skiprows=header_row, dtype=str)
            else:
                raw_text = file_bytes.decode("utf-8", errors="replace")
                counts   = {"	": raw_text.count("	"), ";": raw_text.count(";"), ",": raw_text.count(",")}
                sep      = max(counts, key=counts.get)
                tmp = pd.read_csv(io.StringIO(raw_text), sep=sep, header=None, dtype=str, on_bad_lines="skip")
                header_row = 0
                for i, row in tmp.iterrows():
                    vals = [str(v).strip().lower() for v in row.values]
                    if any(k in vals for k in ["symbol","time","profit","type","position"]):
                        header_row = i; break
                df_raw = pd.read_csv(io.StringIO(raw_text), sep=sep, skiprows=header_row,
                                     dtype=str, on_bad_lines="skip")
        except Exception as e:
            st.error(f"Erreur lecture fichier : {e}"); st.stop()

        # ── Nettoyage colonnes ────────────────────────────────────────────────
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        df_raw = df_raw.dropna(axis=1, how="all")
        df_raw = df_raw.loc[df_raw.astype(str).apply(lambda r: r.str.strip().ne("").any(), axis=1)]

        # Gérer colonnes dupliquées (Time×2, Price×2)
        seen_c = {}; renamed = []
        for c in df_raw.columns:
            k = c.strip().lower()
            if k in seen_c:
                seen_c[k] += 1
                renamed.append(f"{c}_{seen_c[k]}")
            else:
                seen_c[k] = 1
                renamed.append(c)
        df_raw.columns = renamed

        # ── Détection colonnes MT5 ────────────────────────────────────────────
        import re as _re
        def norm_c(s): return _re.sub(r"[\s/_.\-]+","_",str(s).strip().lower())
        col_idx = {norm_c(c): c for c in df_raw.columns}
        def fc(*candidates):
            for cand in candidates:
                k = norm_c(cand)
                if k in col_idx: return col_idx[k]
            return None

        def norm_symbol(raw):
            """Normalise un nom de symbole broker (Exness, etc.) vers le nom standard.
            Gère les suffixes m/M/.m/_m/pro/ecn ajoutés par certains brokers."""
            s = str(raw).strip().upper()
            if s in SYM_MAP:
                return SYM_MAP[s]
            for suffix in ["M", ".M", "_M", "PRO", "ECN", "RAW"]:
                if s.endswith(suffix):
                    base = s[:-len(suffix)]
                    if base in SYM_MAP:
                        return SYM_MAP[base]
            return s

        # Note: pandas renomme automatiquement les colonnes dupliquées
        # "Time" → "Time" + "Time.1", "Price" → "Price" + "Price.1"
        col_open_time  = fc("time","time_1","open_time","open time","date")
        col_close_time = fc("time.1","time_2","close_time","close time")
        col_position   = fc("position","deal","ticket","order","pos")
        col_symbol     = fc("symbol","asset","instrument","pair")
        col_type       = fc("type","action","order_type","operation")
        col_volume     = fc("volume","vol","lots","size","quantity")
        col_open_price = fc("price","price_1","open_price","entry_price","entry price")
        col_close_price= fc("price.1","price_2","close_price","exit_price","exit price")
        col_sl         = fc("s / l","s/l","sl","stop_loss","stoploss","stop loss")
        col_tp         = fc("t / p","t/p","tp","take_profit","takeprofit","take profit")
        col_commission = fc("commission","comm","fee","fees")
        col_swap       = fc("swap","rollover")
        col_profit     = fc("profit","p&l","result","net_profit","net profit")

        # Si col_close_price n'a pas été trouvée mais qu'il y a 2 colonnes "Price",
        # prendre la 2e occurrence directement (gestion robuste du mangling pandas)
        if not col_close_price:
            price_cols = [c for c in df_raw.columns if norm_c(c).startswith("price")]
            if len(price_cols) >= 2:
                col_close_price = price_cols[1]
        if not col_close_time:
            time_cols = [c for c in df_raw.columns if norm_c(c).startswith("time")]
            if len(time_cols) >= 2:
                col_close_time = time_cols[1]

        # Diagnostic
        with st.expander(f"Colonnes détectées ({len(df_raw.columns)})", expanded=False):
            d1, d2 = st.columns(2)
            mapping = [
                ("Open Time",    col_open_time),
                ("Close Time",   col_close_time),
                ("Position ID",  col_position),
                ("Symbol",       col_symbol),
                ("Type",         col_type),
                ("Volume",       col_volume),
                ("Entry Price",  col_open_price),
                ("Exit Price",   col_close_price),
                ("S/L",          col_sl),
                ("T/P",          col_tp),
                ("Commission",   col_commission),
                ("Swap",         col_swap),
                ("Profit",       col_profit),
            ]
            for i, (k, v) in enumerate(mapping):
                with (d1 if i < 6 else d2):
                    st.markdown(f"{'OK' if v else '—'} · **{k}** → `{v or 'Non trouvé'}`")
            st.dataframe(df_raw.head(5))

        if not col_profit:
            st.error("Colonne Profit introuvable."); st.stop()
        if not col_symbol:
            st.error("Colonne Symbol introuvable."); st.stop()

        # ── Filtrage lignes ───────────────────────────────────────────────────
        df_work = df_raw.copy()

        # Supprimer balance / dépôts
        if col_type:
            df_work = df_work[~df_work[col_type].str.lower().str.contains(
                "balance|deposit|withdrawal|credit|bonus|in$", na=False)]

        def to_float(x):
            try: return float(str(x).replace(" ","").replace(",","."))
            except: return None

        # Ne garder QUE les lignes avec Profit non nul
        # (les lignes d'ouverture de position ont Profit = 0)
        df_work["_profit_val"] = df_work[col_profit].apply(to_float)
        df_closed = df_work[df_work["_profit_val"].notna() &
                             df_work["_profit_val"].ne(0)].copy()

        # Dédupliquer par Position si disponible (éviter double-comptage)
        if col_position:
            before = len(df_closed)
            df_closed = df_closed.drop_duplicates(subset=[col_position], keep="last")
            if len(df_closed) < before:
                st.info(f"Déduplication : {before - len(df_closed)} doublon(s) supprimé(s) "
                        f"(même Position ID gardée une seule fois).")

        if df_closed.empty:
            st.warning("Aucun trade fermé détecté."); st.stop()

        # ── Construction trades + aperçu détaillé ────────────────────────────
        new_trades = []; skipped = 0
        preview_rows = []   # pour tableau de vérification

        for _, row in df_closed.iterrows():
            try:
                def rv(col, default="0"):
                    if not col: return default
                    v = row.get(col, default)
                    return str(v) if v is not None and str(v).lower() not in ("nan","none","") else default

                def rfloat(col):
                    try: return float(rv(col).replace(" ","").replace(",","."))
                    except: return 0.0

                # Date
                try: parsed_date = pd.to_datetime(rv(col_open_time,str(date.today()))).strftime("%Y-%m-%d")
                except: parsed_date = str(date.today())

                # Symbole
                sym_raw = rv(col_symbol,"UNKNOWN").strip()
                symbol  = norm_symbol(sym_raw)

                # Direction
                direction = "LONG"
                if col_type:
                    tv = rv(col_type).strip().lower()
                    if any(k in tv for k in ["sell","short","s"]):
                        direction = "SHORT"

                # Valeurs brutes
                profit_raw = rfloat(col_profit)
                comm_raw   = rfloat(col_commission)
                swap_raw   = rfloat(col_swap)
                entry_p    = rfloat(col_open_price)
                exit_p     = rfloat(col_close_price)
                volume     = rfloat(col_volume)
                sl_val     = rfloat(col_sl)
                tp_val     = rfloat(col_tp)

                # P&L selon méthode choisie
                if use_costs:
                    pnl_reel = round(profit_raw + comm_raw + swap_raw, 2)
                else:
                    pnl_reel = round(profit_raw, 2)

                parts = []
                if volume:   parts.append(f"vol:{volume}")
                if comm_raw: parts.append(f"comm:{comm_raw:.2f}")
                if swap_raw: parts.append(f"swap:{swap_raw:.2f}")
                notes_str = "Import MT5" + (" · "+" · ".join(parts) if parts else "")

                # Extraire l'heure depuis open_time
                _time_str = "00:00"
                try:
                    _dt_parsed = pd.to_datetime(rv(col_open_time, str(date.today())))
                    _time_str  = _dt_parsed.strftime("%H:%M")
                    _dt_full   = _dt_parsed.strftime("%Y-%m-%dT%H:%M")
                except:
                    _dt_full = f"{parsed_date}T00:00"

                new_trades.append({
                    "id":         int(datetime.now().timestamp()*1000000)+len(new_trades),
                    "date":       parsed_date,
                    "time":       _time_str,
                    "datetime":   _dt_full,
                    "symbol":     symbol,
                    "direction":  direction,
                    "trade_mode": imp_mode,
                    "entry":      entry_p,
                    "exit":       exit_p,
                    "sl":         sl_val,
                    "tp":         tp_val,
                    "pnl":        pnl_reel,
                    "strategy":   "Importé MT5",
                    "mood":       "Neutre",
                    "notes":      notes_str,
                })
                preview_rows.append({
                    "Date":       parsed_date,
                    "Symbole":    symbol,
                    "Dir.":       direction,
                    "Profit brut":profit_raw,
                    "Commission": comm_raw,
                    "Swap":       swap_raw,
                    "P&L net":    pnl_reel,
                })
            except Exception:
                skipped += 1

        if not new_trades:
            st.error("Aucun trade valide extrait."); st.stop()

        # ── Aperçu avec détail du calcul ──────────────────────────────────────
        total_imp  = round(sum(t["pnl"] for t in new_trades), 2)
        wins_imp   = [t for t in new_trades if t["pnl"] > 0]
        col_t      = "#00d4aa" if total_imp >= 0 else "#ff4d6d"

        st.markdown(f"### {len(new_trades)} trades prêts à importer"
                    + (f" · {skipped} ignorés" if skipped else ""))

        s1, s2, s3 = st.columns(3)
        with s1: kpi('<i class="fa-solid fa-coins"></i>', "P&L Total", fmt(total_imp), "Résultat global", col_t)
        with s2: kpi('<i class="fa-solid fa-circle-check"></i>', "Gagnants", str(len(wins_imp)), f"{len(wins_imp)/len(new_trades)*100:.0f}% win", "#00d4aa")
        with s3: kpi('<i class="fa-solid fa-circle-xmark"></i>', "Perdants", str(len(new_trades)-len(wins_imp)), "Trades négatifs", "#ff4d6d")
        st.markdown(" ")

        # Tableau de vérification du calcul
        st.markdown("##### Vérification du calcul P&L (25 premiers trades)")
        df_preview = pd.DataFrame(preview_rows[:25])
        st.dataframe(
            df_preview.style
            .format({"Profit brut":"{:+.2f}","Commission":"{:+.2f}","Swap":"{:+.2f}","P&L net":"{:+.2f}"})
            .map(lambda v: f"color:{'#00d4aa' if v>0 else '#ff4d6d' if v<0 else '#6b7894'}" 
                 if isinstance(v,(int,float)) else "",
                 subset=["Profit brut","Commission","Swap","P&L net"]),
            use_container_width=True, hide_index=True
        )
        st.caption(
            f"Méthode : {'Profit + Commission + Swap' if use_costs else 'Profit uniquement'}. "
            f"Si les valeurs semblent incorrectes, changez la méthode ci-dessus et réimportez."
        )

        st.markdown("---")
        add_mode = st.radio(
            "Mode d'import",
            ["Ajouter aux trades existants", "Remplacer tous les trades"],
            horizontal=True
        )

        if st.button("Confirmer l'import", icon=":material/check_circle:", use_container_width=True):
            if "Remplacer" in add_mode:
                st.session_state.trades = new_trades
            else:
                existing_ids = {t["id"] for t in st.session_state.trades}
                st.session_state.trades += [t for t in new_trades if t["id"] not in existing_ids]
            ok = cloud_save(st.session_state.trades)
            st.success(f"{len(new_trades)} trades importés ({imp_mode}) — " +
                       ("synchronisés." if ok else "erreur sync GitHub."))
            st.session_state.page = "dashboard"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CALENDRIER
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "calendar":
    st.markdown("# Calendrier de Performance")
    mode_banner()

    df_cal = get_df(st.session_state.mode_filter)

    if df_cal.empty:
        st.warning("Aucun trade enregistré.")
    else:
        df_cal = df_cal.copy()
        df_cal["_dt"] = pd.to_datetime(df_cal["date"])

        # ── Couleur selon intensité du P&L ──────────────────────────────────
        _cal_theme = get_theme()
        def _hex2rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2],16) for i in (0,2,4))
        _win_rgb  = _hex2rgb(_cal_theme["win"])
        _loss_rgb = _hex2rgb(_cal_theme["loss"])

        def _pnl_color(value, max_abs):
            if value == 0 or max_abs == 0:
                return _cal_theme["bg2"], _cal_theme["muted"], "rgba(255,255,255,0.04)"
            intensity = min(abs(value) / max_abs, 1.0)
            alpha = 0.18 + 0.55 * intensity
            if value > 0:
                r,g,b = _win_rgb
                return f"rgba({r},{g},{b},{alpha:.2f})", _cal_theme["text"], f"rgba({r},{g},{b},0.35)"
            else:
                r,g,b = _loss_rgb
                return f"rgba({r},{g},{b},{alpha:.2f})", _cal_theme["text"], f"rgba({r},{g},{b},0.35)"

        # ── Sélecteur de granularité ─────────────────────────────────────────
        gc1, gc2, gc3 = st.columns([2, 2, 3])
        with gc1:
            granularity = st.selectbox(
                "Vue", ["Jour", "Semaine", "Mois", "Année"],
                index=["Jour","Semaine","Mois","Année"].index(
                    st.session_state.get("cal_gran", "Jour")
                ),
                key="cal_gran_sel"
            )
            st.session_state.cal_gran = granularity

        years_avail = sorted(df_cal["_dt"].dt.year.unique().tolist(), reverse=True)
        if "cal_year" not in st.session_state:
            st.session_state.cal_year = years_avail[0] if years_avail else date.today().year
        if "cal_month" not in st.session_state:
            st.session_state.cal_month = date.today().month

        # ── Navigation contextuelle selon la vue ────────────────────────────
        if granularity == "Jour":
            with gc2:
                nav1, nav2, nav3 = st.columns([1, 3, 1])
                with nav1:
                    if st.button("←", use_container_width=True, key="cal_prev_m"):
                        m, y = st.session_state.cal_month, st.session_state.cal_year
                        m -= 1
                        if m == 0: m = 12; y -= 1
                        st.session_state.cal_month, st.session_state.cal_year = m, y
                        st.rerun()
                with nav2:
                    mois_fr = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet",
                               "Août","Septembre","Octobre","Novembre","Décembre"]
                    st.markdown(
                        f'<div style="text-align:center;padding-top:6px;font-weight:700;font-size:15px">'
                        f'{mois_fr[st.session_state.cal_month-1]} {st.session_state.cal_year}</div>',
                        unsafe_allow_html=True
                    )
                with nav3:
                    if st.button("→", use_container_width=True, key="cal_next_m"):
                        m, y = st.session_state.cal_month, st.session_state.cal_year
                        m += 1
                        if m == 13: m = 1; y += 1
                        st.session_state.cal_month, st.session_state.cal_year = m, y
                        st.rerun()
        elif granularity in ("Semaine", "Mois"):
            with gc2:
                sel_year = st.selectbox(
                    "Année", years_avail,
                    index=years_avail.index(st.session_state.cal_year)
                          if st.session_state.cal_year in years_avail else 0,
                    key="cal_year_sel"
                )
                st.session_state.cal_year = sel_year

        st.markdown("---")

        # ════════════════════════════════════════════════════════════════════
        # VUE JOUR — Calendrier mensuel avec totaux hebdomadaires
        # ════════════════════════════════════════════════════════════════════
        if granularity == "Jour":
            year  = st.session_state.cal_year
            month = st.session_state.cal_month

            df_month = df_cal[(df_cal["_dt"].dt.year == year) & (df_cal["_dt"].dt.month == month)]
            day_agg  = df_month.groupby(df_month["_dt"].dt.day).agg(
                pnl=("pnl", "sum"), trades=("pnl", "count")
            )
            max_abs  = day_agg["pnl"].abs().max() if not day_agg.empty else 1

            cal_obj = _calmod.Calendar(firstweekday=6)  # Dimanche en premier
            weeks   = cal_obj.monthdayscalendar(year, month)

            # KPIs résumé du mois
            month_total  = day_agg["pnl"].sum() if not day_agg.empty else 0
            month_trades = int(day_agg["trades"].sum()) if not day_agg.empty else 0
            active_days  = len(day_agg)
            mc1, mc2, mc3 = st.columns(3)
            with mc1: kpi('<i class="fa-solid fa-coins"></i>', "P&L du mois", fmt(month_total),
                          f"{month_trades} trades", "#00d4aa" if month_total>=0 else "#ff4d6d")
            with mc2: kpi('<i class="fa-solid fa-calendar-check"></i>', "Jours actifs", str(active_days),
                          f"sur {len(weeks)*7} jours du calendrier", "#7c6aff")
            with mc3:
                avg_day = month_total/active_days if active_days else 0
                kpi('<i class="fa-solid fa-chart-line"></i>', "Moyenne / jour actif", fmt(avg_day),
                    "P&L moyen", "#ff9f43")
            st.markdown(" ")

            # Construction HTML du calendrier
            html = '<div style="overflow-x:auto"><table style="width:100%;border-collapse:separate;border-spacing:6px">'
            html += '<thead><tr>'
            for d in ["Dim","Lun","Mar","Mer","Jeu","Ven","Sam"]:
                html += f'<th style="color:#6b7894;font-size:11px;font-weight:700;padding:6px;text-transform:uppercase;letter-spacing:.5px">{d}</th>'
            html += '<th style="color:#6b7894;font-size:11px;font-weight:700;padding:6px;text-transform:uppercase;letter-spacing:.5px">Semaine</th>'
            html += '</tr></thead><tbody>'

            today_iso = date.today().isoformat()

            for week in weeks:
                week_pnl, week_trades, week_active = 0, 0, 0
                row = "<tr>"
                for day in week:
                    if day == 0:
                        row += '<td style="background:#0a0c12;border-radius:10px;height:78px"></td>'
                        continue
                    cell_date = date(year, month, day).isoformat()
                    is_today  = cell_date == today_iso
                    border_today = "2px solid #00d4aa" if is_today else "1px solid rgba(255,255,255,0.04)"

                    if day in day_agg.index:
                        pnl_v    = day_agg.loc[day, "pnl"]
                        trades_v = int(day_agg.loc[day, "trades"])
                        week_pnl += pnl_v; week_trades += trades_v; week_active += 1
                        bg, text_col, _ = _pnl_color(pnl_v, max_abs)
                        row += f'''<td style="background:{bg};border-radius:10px;height:78px;
                            padding:8px;vertical-align:top;border:{border_today}">
                            <div style="font-size:10px;color:#8892a4">{day}</div>
                            <div style="font-size:13px;font-weight:800;color:{text_col};
                                font-family:'JetBrains Mono',monospace;margin-top:6px">{fmt(pnl_v)}</div>
                            <div style="font-size:9px;color:#8892a4;margin-top:3px">
                                {trades_v} trade{"s" if trades_v>1 else ""}</div>
                        </td>'''
                    else:
                        row += f'''<td style="background:#111520;border-radius:10px;height:78px;
                            padding:8px;vertical-align:top;border:{border_today}">
                            <div style="font-size:10px;color:#3d4760">{day}</div>
                        </td>'''
                # Cellule total semaine
                if week_active > 0:
                    wcol = "#00d4aa" if week_pnl >= 0 else "#ff4d6d"
                    wbg  = "rgba(0,212,170,0.10)" if week_pnl >= 0 else "rgba(255,77,109,0.10)"
                    wpnl_txt = fmt(week_pnl)
                else:
                    wcol = "#3d4760"; wbg = "#0d111d"; wpnl_txt = "—"
                row += f'''<td style="background:{wbg};border-radius:10px;height:78px;
                    padding:8px;vertical-align:top;border:1px solid {wcol}33">
                    <div style="font-size:9px;color:#6b7894;text-transform:uppercase">Total</div>
                    <div style="font-size:13px;font-weight:800;color:{wcol};
                        font-family:'JetBrains Mono',monospace;margin-top:6px">{wpnl_txt}</div>
                    <div style="font-size:9px;color:#8892a4;margin-top:3px">
                        {week_trades} trade{"s" if week_trades!=1 else ""}</div>
                </td>'''
                row += "</tr>"
                html += row
            html += '</tbody></table></div>'

            st.markdown(html, unsafe_allow_html=True)

            # ════════════════════════════════════════════════════════════════
            # ZOOM HORAIRE — détail des prises de position d'un jour précis
            # ════════════════════════════════════════════════════════════════
            st.markdown("---")
            st.markdown("#### Détail horaire d'une journée")

            _n_days_month = _calmod.monthrange(year, month)[1]
            _all_days = list(range(1, _n_days_month + 1))

            zc1, zc2, zc3 = st.columns([1.6, 1.2, 2.4])
            with zc1:
                _default_day = (int(day_agg["pnl"].abs().idxmax())
                                if not day_agg.empty else date.today().day)
                if _default_day not in _all_days:
                    _default_day = _all_days[0]
                zoom_day = st.selectbox(
                    "Jour du mois", _all_days,
                    index=_all_days.index(_default_day),
                    format_func=lambda d: (
                        f"{d:02d} {mois_fr[month-1]}"
                        + (f" · {int(day_agg.loc[d,'trades'])} trades"
                           if d in day_agg.index else " · —")
                    ),
                    key="cal_zoom_day"
                )
            with zc2:
                _only_active = st.checkbox("Jours actifs seulement", value=False,
                                           key="cal_zoom_active_only",
                                           help="Masque les jours sans aucun trade "
                                                "dans la liste ci-contre")
                if _only_active and not day_agg.empty:
                    _act = sorted(day_agg.index.tolist())
                    if zoom_day not in _act:
                        zoom_day = _act[-1]
                        st.caption(f"→ {zoom_day:02d} (1er jour actif)")

            zoom_date_obj = date(year, month, zoom_day)
            zoom_date_iso = zoom_date_obj.isoformat()
            df_zoom_day = df_cal[df_cal["_dt"].dt.date.astype(str) == zoom_date_iso].copy()

            with zc3:
                _jn = {"Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi",
                       "Thursday":"Jeudi","Friday":"Vendredi","Saturday":"Samedi",
                       "Sunday":"Dimanche"}[zoom_date_obj.strftime("%A")]
                if df_zoom_day.empty:
                    st.markdown(
                        f"<div style='padding-top:8px;color:#6b7894'>"
                        f"{_jn} {zoom_day:02d} {mois_fr[month-1]} {year} — "
                        f"<i>aucun trade</i></div>", unsafe_allow_html=True)
                else:
                    zpnl = df_zoom_day["pnl"].sum()
                    ztrades = len(df_zoom_day)
                    zcol = "#00d4aa" if zpnl >= 0 else "#ff4d6d"
                    st.markdown(
                        f"<div style='padding-top:8px'>"
                        f"<span style='color:#6b7894'>{_jn} {zoom_day:02d} · P&L : </span>"
                        f"<b style='color:{zcol};font-family:JetBrains Mono,monospace'>{fmt(zpnl)}</b>"
                        f"<span style='color:#6b7894'> · {ztrades} position"
                        f"{'s' if ztrades>1 else ''}</span></div>",
                        unsafe_allow_html=True)

            if df_zoom_day.empty:
                st.info(f"Aucun trade enregistré le {zoom_day:02d} {mois_fr[month-1]} {year}.")
            else:
                if "datetime" in df_zoom_day.columns:
                    df_zoom_day["_dtz"] = pd.to_datetime(
                        df_zoom_day["datetime"], errors="coerce")
                else:
                    df_zoom_day["_dtz"] = pd.NaT

                if df_zoom_day["_dtz"].notna().any():
                    _dz = df_zoom_day[df_zoom_day["_dtz"].notna()].copy()
                    _dz["_hour"] = _dz["_dtz"].dt.hour.astype(int)

                    # KPIs de la journée
                    _hr_pnl = _dz.groupby("_hour")["pnl"].sum()
                    _best_h = int(_hr_pnl.idxmax()); _worst_h = int(_hr_pnl.idxmin())
                    _wr_day = (_dz["pnl"] > 0).sum()/len(_dz)*100
                    zk1, zk2, zk3, zk4 = st.columns(4)
                    with zk1: kpi('<i class="fa-solid fa-clock"></i>', "1ère position",
                                  _dz["_dtz"].min().strftime("%H:%M"),
                                  f"dernière : {_dz['_dtz'].max().strftime('%H:%M')}", "#7c6aff")
                    with zk2: kpi('<i class="fa-solid fa-arrow-trend-up"></i>', "Meilleure heure",
                                  f"{_best_h:02d}h", fmt(_hr_pnl.max()), "#00d4aa")
                    with zk3: kpi('<i class="fa-solid fa-arrow-trend-down"></i>', "Pire heure",
                                  f"{_worst_h:02d}h", fmt(_hr_pnl.min()), "#ff4d6d")
                    with zk4: kpi('<i class="fa-solid fa-bullseye"></i>', "Win rate du jour",
                                  f"{_wr_day:.0f}%", f"{len(_dz)} positions",
                                  "#00d4aa" if _wr_day>=50 else "#ff4d6d")
                    st.markdown(" ")

                    # Plage horaire à afficher
                    _hmin, _hmax = int(_dz["_hour"].min()), int(_dz["_hour"].max())
                    zh1, zh2 = st.columns([2, 3])
                    with zh1:
                        _hr_range = st.slider("Plage horaire affichée", 0, 23,
                                              (max(0,_hmin-1), min(23,_hmax+1)),
                                              key="cal_zoom_hours")
                    _hrange_list = list(range(_hr_range[0], _hr_range[1]+1))
                    _dz_f = _dz[_dz["_hour"].between(_hr_range[0], _hr_range[1])]

                    if _dz_f.empty:
                        st.info("Aucune position dans cette plage horaire.")
                    else:
                        hour_agg = _dz_f.groupby("_hour").agg(
                            pnl=("pnl","sum"), trades=("pnl","count")
                        ).reindex(_hrange_list, fill_value=0)

                        fig_hr = go.Figure(go.Bar(
                            x=[f"{int(h):02d}h" for h in hour_agg.index],
                            y=hour_agg["pnl"].tolist(),
                            marker_color=["#00d4aa" if v>=0 else "#ff4d6d" for v in hour_agg["pnl"]],
                            marker_opacity=0.85,
                            customdata=hour_agg["trades"].tolist(),
                            hovertemplate="<b>%{x}</b><br>P&L : %{y:+,.2f}$<br>"
                                         "%{customdata} position(s)<extra></extra>",
                        ))
                        fig_hr.add_hline(y=0, line_color="#1a2035", line_width=1)
                        fig_hr.update_layout(
                            paper_bgcolor="#111520", plot_bgcolor="#111520",
                            font=dict(color="#8892a4", size=11), height=260,
                            margin=dict(l=50,r=20,t=10,b=30), showlegend=False)
                        fig_hr.update_xaxes(gridcolor="#1a2035", linecolor="#1a2035")
                        fig_hr.update_yaxes(gridcolor="#1a2035", linecolor="#1a2035", tickprefix="$")
                        st.plotly_chart(fig_hr, use_container_width=True,
                                        config={"scrollZoom": True, "displayModeBar": True,
                                               "modeBarButtonsToRemove": ["lasso2d","select2d"]})

                        # Courbe de P&L cumulé intra-journalier
                        _dz_sorted = _dz_f.sort_values("_dtz")
                        _cum = _dz_sorted["pnl"].cumsum()
                        fig_cum = go.Figure(go.Scatter(
                            x=_dz_sorted["_dtz"].dt.strftime("%H:%M").tolist(),
                            y=_cum.tolist(), mode="lines+markers",
                            line=dict(color="#7c6aff", width=2.5, shape="hv"),
                            marker=dict(size=7,
                                        color=["#00d4aa" if p>0 else "#ff4d6d"
                                               for p in _dz_sorted["pnl"]]),
                            customdata=list(zip(_dz_sorted["symbol"], _dz_sorted["pnl"])),
                            hovertemplate="<b>%{x}</b><br>%{customdata[0]}<br>"
                                         "Trade : %{customdata[1]:+,.2f}$<br>"
                                         "Cumulé : %{y:+,.2f}$<extra></extra>",
                        ))
                        fig_cum.add_hline(y=0, line_color="#1a2035", line_width=1)
                        fig_cum.update_layout(
                            paper_bgcolor="#111520", plot_bgcolor="#111520",
                            font=dict(color="#8892a4", size=11), height=220,
                            margin=dict(l=50,r=20,t=24,b=30), showlegend=False,
                            title=dict(text="P&L cumulé au fil de la journée",
                                      font=dict(size=12, color="#8892a4"), x=0.01))
                        fig_cum.update_xaxes(gridcolor="#1a2035", linecolor="#1a2035")
                        fig_cum.update_yaxes(gridcolor="#1a2035", linecolor="#1a2035", tickprefix="$")
                        st.plotly_chart(fig_cum, use_container_width=True)

                        # Liste détaillée des positions
                        st.markdown("##### Positions prises ce jour")
                        for _, zt in _dz_sorted.iterrows():
                            zh = zt["_dtz"].strftime("%H:%M") if pd.notna(zt["_dtz"]) else "—"
                            zc = "#00d4aa" if zt["pnl"]>=0 else "#ff4d6d"
                            st.markdown(
                                f"<div style='display:flex;gap:14px;align-items:center;"
                                f"background:#111520;border:1px solid #1e2535;border-radius:8px;"
                                f"padding:7px 14px;margin-bottom:5px;font-size:13px'>"
                                f"<span style='color:#6b7894;font-family:JetBrains Mono,monospace;"
                                f"min-width:42px'>{zh}</span>"
                                f"<span style='color:#e8ecf4;font-weight:600'>{zt['symbol']}</span>"
                                f"<span style='color:#6b7894'>{zt['direction']}</span>"
                                f"<span style='color:{zc};font-family:JetBrains Mono,monospace;"
                                f"font-weight:700;margin-left:auto'>{fmt(zt['pnl'])}</span>"
                                f"</div>", unsafe_allow_html=True)
                else:
                    st.info("Aucune heure précise enregistrée pour ce jour "
                           "(trades saisis sans heure).")

        # ════════════════════════════════════════════════════════════════════
        # VUE SEMAINE — Grille des semaines de l'année
        # ════════════════════════════════════════════════════════════════════
        elif granularity == "Semaine":
            year = st.session_state.cal_year
            df_year = df_cal[df_cal["_dt"].dt.year == year].copy()
            df_year["_week"] = df_year["_dt"].dt.isocalendar().week
            week_agg = df_year.groupby("_week").agg(pnl=("pnl","sum"), trades=("pnl","count"))
            max_abs  = week_agg["pnl"].abs().max() if not week_agg.empty else 1

            total_y  = week_agg["pnl"].sum() if not week_agg.empty else 0
            trades_y = int(week_agg["trades"].sum()) if not week_agg.empty else 0
            active_w = len(week_agg)
            mc1, mc2, mc3 = st.columns(3)
            with mc1: kpi('<i class="fa-solid fa-coins"></i>', f"P&L {year}", fmt(total_y),
                          f"{trades_y} trades", "#00d4aa" if total_y>=0 else "#ff4d6d")
            with mc2: kpi('<i class="fa-solid fa-calendar-week"></i>', "Semaines actives", str(active_w),
                          "sur 52-53 semaines", "#7c6aff")
            with mc3:
                avg_w = total_y/active_w if active_w else 0
                kpi('<i class="fa-solid fa-chart-line"></i>', "Moyenne / semaine", fmt(avg_w),
                    "P&L moyen", "#ff9f43")
            st.markdown(" ")

            html = '<div style="display:grid;grid-template-columns:repeat(13,1fr);gap:8px">'
            for w in range(1, 54):
                if w in week_agg.index:
                    pnl_v = week_agg.loc[w,"pnl"]; trades_v = int(week_agg.loc[w,"trades"])
                    bg, text_col, _ = _pnl_color(pnl_v, max_abs)
                    pnl_txt = fmt(pnl_v)
                else:
                    bg = "#111520"; text_col = "#3d4760"; pnl_txt = "—"; trades_v = 0
                html += f'''<div title="Semaine {w}, {trades_v} trades" style="background:{bg};
                    border-radius:9px;padding:10px 4px;text-align:center;
                    border:1px solid rgba(255,255,255,0.04)">
                    <div style="font-size:9px;color:#6b7894">S{w}</div>
                    <div style="font-size:11px;font-weight:800;color:{text_col};
                        font-family:'JetBrains Mono',monospace;margin-top:4px">{pnl_txt}</div>
                </div>'''
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # VUE MOIS — 12 cartes mensuelles
        # ════════════════════════════════════════════════════════════════════
        elif granularity == "Mois":
            year = st.session_state.cal_year
            df_year  = df_cal[df_cal["_dt"].dt.year == year]
            month_agg = df_year.groupby(df_year["_dt"].dt.month).agg(
                pnl=("pnl","sum"), trades=("pnl","count")
            )
            max_abs  = month_agg["pnl"].abs().max() if not month_agg.empty else 1
            mois_fr  = ["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Août","Sep","Oct","Nov","Déc"]

            total_y  = month_agg["pnl"].sum() if not month_agg.empty else 0
            trades_y = int(month_agg["trades"].sum()) if not month_agg.empty else 0
            active_m = len(month_agg)
            mc1, mc2, mc3 = st.columns(3)
            with mc1: kpi('<i class="fa-solid fa-coins"></i>', f"P&L {year}", fmt(total_y),
                          f"{trades_y} trades", "#00d4aa" if total_y>=0 else "#ff4d6d")
            with mc2: kpi('<i class="fa-solid fa-calendar-days"></i>', "Mois actifs", str(active_m),
                          "sur 12 mois", "#7c6aff")
            with mc3:
                avg_m = total_y/active_m if active_m else 0
                kpi('<i class="fa-solid fa-chart-line"></i>', "Moyenne / mois", fmt(avg_m),
                    "P&L moyen", "#ff9f43")
            st.markdown(" ")

            html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">'
            for m in range(1, 13):
                if m in month_agg.index:
                    pnl_v = month_agg.loc[m,"pnl"]; trades_v = int(month_agg.loc[m,"trades"])
                    bg, text_col, border_col = _pnl_color(pnl_v, max_abs)
                    pnl_txt = fmt(pnl_v)
                else:
                    bg = "#111520"; text_col = "#3d4760"; border_col = "rgba(255,255,255,0.04)"
                    pnl_txt = "—"; trades_v = 0
                html += f'''<div style="background:{bg};border-radius:14px;padding:18px;
                    border:1px solid {border_col}">
                    <div style="font-size:12px;color:#8892a4;text-transform:uppercase;
                        letter-spacing:.5px">{mois_fr[m-1]} {year}</div>
                    <div style="font-size:22px;font-weight:800;color:{text_col};
                        font-family:'JetBrains Mono',monospace;margin-top:8px">{pnl_txt}</div>
                    <div style="font-size:11px;color:#8892a4;margin-top:6px">
                        {trades_v} trade{"s" if trades_v!=1 else ""}</div>
                </div>'''
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # VUE ANNÉE — Cartes par année (historique complet)
        # ════════════════════════════════════════════════════════════════════
        elif granularity == "Année":
            df_all_y  = df_cal.copy()
            df_all_y["_year"] = df_all_y["_dt"].dt.year
            year_agg  = df_all_y.groupby("_year").agg(
                pnl=("pnl","sum"), trades=("pnl","count")
            ).reset_index().sort_values("_year")
            max_abs   = year_agg["pnl"].abs().max() if not year_agg.empty else 1

            total_all  = year_agg["pnl"].sum()
            trades_all = int(year_agg["trades"].sum())
            mc1, mc2, mc3 = st.columns(3)
            with mc1: kpi('<i class="fa-solid fa-coins"></i>', "P&L Total", fmt(total_all),
                          f"{trades_all} trades", "#00d4aa" if total_all>=0 else "#ff4d6d")
            with mc2: kpi('<i class="fa-solid fa-calendar"></i>', "Années actives", str(len(year_agg)),
                          "années de trading", "#7c6aff")
            with mc3:
                avg_y = total_all/len(year_agg) if len(year_agg) else 0
                kpi('<i class="fa-solid fa-chart-line"></i>', "Moyenne / année", fmt(avg_y),
                    "P&L moyen", "#ff9f43")
            st.markdown(" ")

            html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px">'
            for _, r in year_agg.iterrows():
                bg, text_col, border_col = _pnl_color(r["pnl"], max_abs)
                html += f'''<div style="background:{bg};border-radius:14px;padding:20px;
                    border:1px solid {border_col}">
                    <div style="font-size:13px;color:#8892a4">{int(r["_year"])}</div>
                    <div style="font-size:24px;font-weight:800;color:{text_col};
                        font-family:'JetBrains Mono',monospace;margin-top:8px">{fmt(r["pnl"])}</div>
                    <div style="font-size:11px;color:#8892a4;margin-top:6px">
                        {int(r["trades"])} trade{"s" if r["trades"]!=1 else ""}</div>
                </div>'''
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        # ── Légende couleur ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            '<div style="display:flex;gap:24px;align-items:center;font-size:12px;color:#6b7894">'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            'background:rgba(0,212,170,0.65);margin-right:6px;vertical-align:middle"></span>Gain</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            'background:rgba(255,77,109,0.65);margin-right:6px;vertical-align:middle"></span>Perte</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            'background:#111520;margin-right:6px;vertical-align:middle;border:1px solid #1e2535"></span>'
            'Aucun trade</span>'
            '<span style="color:#8892a4">L\'intensité de la couleur reflète l\'ampleur du P&L</span>'
            '</div>', unsafe_allow_html=True
        )
