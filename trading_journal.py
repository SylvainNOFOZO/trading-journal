import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import json, os, base64, requests, io

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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
.fa, .fas, .far, .fab, .fa-solid, .fa-regular { font-family: "Font Awesome 6 Free" !important; }
.icon { display:inline-flex; align-items:center; justify-content:center;
        width:32px; height:32px; border-radius:8px; font-size:15px; }
.icon-green  { color:#00d4aa; background:rgba(0,212,170,.12); }
.icon-red    { color:#ff4d6d; background:rgba(255,77,109,.12); }
.icon-purple { color:#7c6aff; background:rgba(124,106,255,.12); }
.icon-orange { color:#ff9f43; background:rgba(255,159,67,.12); }
.icon-muted  { color:#6b7894; background:rgba(107,120,148,.1); }
.mood-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
.stApp { background-color: #0a0c12; }
section[data-testid="stSidebar"] > div { background-color: #0c0f1a; border-right: 1px solid #1e2535; }
h1,h2,h3,h4,h5,h6,p,label,.stMarkdown { color: #e8ecf4 !important; }
.stSelectbox label,.stNumberInput label,.stTextInput label,.stTextArea label,.stDateInput label {
    color: #8892a4 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px; }
.stButton > button { background-color:#00d4aa;color:#000;font-weight:800;border:none;border-radius:10px; }
.stButton > button:hover { background-color:#00b898 !important;color:#000 !important; }
.kpi { background:#111520;border:1px solid #1e2535;border-radius:14px;padding:18px 20px 14px;
    position:relative;overflow:hidden;min-height:110px; }
.kpi-bar { position:absolute;top:0;left:0;right:0;height:3px; }
.kpi-icon { font-size:18px;margin-bottom:6px; }
.kpi-label { font-size:10px;color:#6b7894;letter-spacing:1.5px;text-transform:uppercase;font-weight:600; }
.kpi-value { font-size:24px;font-weight:800;font-family:"JetBrains Mono",monospace;margin:4px 0 2px; }
.kpi-sub { font-size:11px;color:#6b7894; }
.tj-table { width:100%;border-collapse:collapse;font-size:13px; }
.tj-table th { padding:10px 12px;text-align:left;font-size:10px;color:#6b7894;letter-spacing:1px;
    text-transform:uppercase;border-bottom:1px solid #1e2535;background:#0d111d;font-weight:600; }
.tj-table td { padding:11px 12px;border-bottom:1px solid rgba(30,37,53,.5);color:#e8ecf4; }
.tj-table tr:hover td { background:#161c2e; }
.badge { padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.8px;display:inline-block; }
.b-win  { color:#00d4aa;background:rgba(0,212,170,.15);border:1px solid rgba(0,212,170,.3); }
.b-loss { color:#ff4d6d;background:rgba(255,77,109,.15);border:1px solid rgba(255,77,109,.3); }
.b-sym  { color:#7c6aff;background:rgba(124,106,255,.15);border:1px solid rgba(124,106,255,.3); }
.b-str  { color:#ff9f43;background:rgba(255,159,67,.15);border:1px solid rgba(255,159,67,.3); }
.b-real { color:#00d4aa;background:rgba(0,212,170,.15);border:1px solid rgba(0,212,170,.3); }
.b-demo { color:#ff9f43;background:rgba(255,159,67,.15);border:1px solid rgba(255,159,67,.3); }
hr { border-color:#1e2535 !important; }
.sync-ok { background:#00d4aa18;border:1px solid #00d4aa44;border-radius:8px;padding:6px 14px;font-size:12px;color:#00d4aa; }
.mode-banner-real { background:rgba(0,212,170,.08);border:1px solid rgba(0,212,170,.3);border-radius:10px;
    padding:8px 16px;font-size:12px;color:#00d4aa;font-weight:700;margin-bottom:12px; }
.mode-banner-demo { background:rgba(255,159,67,.08);border:1px solid rgba(255,159,67,.3);border-radius:10px;
    padding:8px 16px;font-size:12px;color:#ff9f43;font-weight:700;margin-bottom:12px; }
.mode-banner-all  { background:rgba(124,106,255,.08);border:1px solid rgba(124,106,255,.3);border-radius:10px;
    padding:8px 16px;font-size:12px;color:#7c6aff;font-weight:700;margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)

STRATEGIES   = ["Breakout","Retracement","Support","Tendance","Range","Divergence","Scalping","News"]
MOODS        = ["Euphorique","Confiant","Neutre","Anxieux","Peureux","Frustré"]
SYMBOLS      = ["EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD","NZD/USD","USD/CAD",
                "EUR/GBP","EUR/JPY","GBP/JPY","NAS100","SP500","DOW30","DAX40","FTSE100",
                "GOLD","SILVER","BTC/USD","ETH/USD","OIL","Autre"]
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
TRADE_MODES  = ["Réel", "Démo"]
SYM_MAP = {
    "EURUSD":"EUR/USD","GBPUSD":"GBP/USD","USDJPY":"USD/JPY","USDCHF":"USD/CHF",
    "AUDUSD":"AUD/USD","NZDUSD":"NZD/USD","USDCAD":"USD/CAD","EURGBP":"EUR/GBP",
    "EURJPY":"EUR/JPY","GBPJPY":"GBP/JPY","EURCAD":"EUR/CAD","AUDCAD":"AUD/CAD",
    "XAUUSD":"GOLD","XAGUSD":"SILVER","BTCUSD":"BTC/USD","ETHUSD":"ETH/USD",
    "US30":"DOW30","US500":"SP500","SP500":"SP500","USTEC":"NAS100","NAS100":"NAS100",
    "UK100":"FTSE100","GER40":"DAX40","FRA40":"CAC40","USOIL":"OIL","UKOIL":"OIL","WTI":"OIL",
}
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

def force_reload():
    trades = db_load()
    for t in trades:
        if t.get("trade_mode","") in ("Réel 💰",""): t["trade_mode"] = "Réel"
        if t.get("trade_mode","") == "Démo 🧪": t["trade_mode"] = "Démo"
        if not t.get("trade_mode"): t["trade_mode"] = "Réel"
    st.session_state.trades = trades
# ── INIT SESSION ────────────────────────────────────────────────────────────
if "trades" not in st.session_state:
    _t = db_load()
    for _x in _t:
        if _x.get("trade_mode","") in ("Réel 💰",""): _x["trade_mode"] = "Réel"
        if _x.get("trade_mode","") == "Démo 🧪": _x["trade_mode"] = "Démo"
        if not _x.get("trade_mode"): _x["trade_mode"] = "Réel"
    st.session_state.trades = _t
if "page"        not in st.session_state: st.session_state.page        = "dashboard"
if "edit_id"     not in st.session_state: st.session_state.edit_id     = None
if "mode_filter" not in st.session_state: st.session_state.mode_filter = "Tous"
if st.session_state.mode_filter not in ["Tous","Réel","Démo"]: st.session_state.mode_filter = "Tous"





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
    if "trade_mode" not in df.columns: df["trade_mode"] = "Réel"
    if mode_filter == "Réel":  return df[df["trade_mode"] == "Réel"]
    if mode_filter == "Démo":  return df[df["trade_mode"] == "Démo"]
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
    st.divider()

    # Filtre global mode
    mode_f = st.radio("Afficher", ["Tous", "Réel", "Démo"],
        index=["Tous","Réel","Démo"].index(st.session_state.mode_filter) if st.session_state.mode_filter in ["Tous","Réel","Démo"] else 0,
        horizontal=True, label_visibility="collapsed")
    if mode_f != st.session_state.mode_filter:
        st.session_state.mode_filter = mode_f; st.rerun()
    st.divider()

    df_side = get_df(st.session_state.mode_filter)
    total   = df_side["pnl"].sum() if not df_side.empty else 0
    wr      = (len(df_side[df_side["pnl"]>0])/len(df_side)*100) if not df_side.empty else 0
    col_pnl = "#00d4aa" if total >= 0 else "#ff4d6d"
    mode_icon = {"Tous":"Tous","Réel":"Réel","Démo":"Démo"}[st.session_state.mode_filter]

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
    if m == "Réel":
        st.markdown('<div class="mode-banner-real"><i class="fa-solid fa-circle-dot"></i> Mode RÉEL — Performances sur compte réel</div>', unsafe_allow_html=True)
    elif m == "Démo":
        st.markdown('<div class="mode-banner-demo"><i class="fa-solid fa-flask"></i> Mode DÉMO — Performances sur compte démo</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mode-banner-all"><i class="fa-solid fa-layer-group"></i> Tous les trades — Réel + Démo confondus</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "dashboard":
    st.markdown("# Dashboard")
    st.caption(datetime.now().strftime("%A %d %B %Y"))
    mode_banner()

    # ── FILTRES GLOBAUX ──────────────────────────────────────────────────────
    st.markdown('<div style="background:#111520;border:1px solid #1e2535;border-radius:14px;padding:16px 20px;margin:12px 0 20px">', unsafe_allow_html=True)
    df_all_f    = get_df("Tous")
    syms_avail  = sorted(df_all_f["symbol"].unique().tolist()) if not df_all_f.empty else []
    moods_avail = sorted(df_all_f["mood"].unique().tolist())   if not df_all_f.empty else []
    strat_avail = sorted(df_all_f["strategy"].unique().tolist()) if not df_all_f.empty else []
    dates       = sorted(df_all_f["date"].tolist()) if not df_all_f.empty else []
    d_min = date.fromisoformat(dates[0])  if dates else date(2024,1,1)
    d_max = date.fromisoformat(dates[-1]) if dates else date.today()
    fc1,fc2,fc3,fc4,fc5 = st.columns(5)
    with fc1: f_sym       = st.selectbox("Actif",       ["Tous"]   + syms_avail,  key="d_sym")
    with fc2: f_mood      = st.selectbox("Émotion",     ["Toutes"] + moods_avail, key="d_mood")
    with fc3: f_strat     = st.selectbox("Stratégie",   ["Toutes"] + strat_avail, key="d_strat")
    with fc4: f_date_from = st.date_input("Depuis",     value=d_min, key="d_from")
    with fc5: f_date_to   = st.date_input("Jusqu'au",  value=d_max, key="d_to")

    # Appliquer filtres
    df = get_df(st.session_state.mode_filter)
    if not df.empty:
        if f_sym   != "Tous":   df = df[df["symbol"]   == f_sym]
        if f_mood  != "Toutes": df = df[df["mood"]     == f_mood]
        if f_strat != "Toutes": df = df[df["strategy"] == f_strat]
        df = df[df["date"].between(str(f_date_from), str(f_date_to))]

    if df.empty:
        st.warning("Aucun trade pour ces filtres. Ajoutez des trades ou modifiez les filtres.")
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
        with c1: kpi('<i class="fa-solid fa-coins"></i>',"P&L Net",      fmt(total),       f"{len(df)} trades",             "#00d4aa" if total>=0 else "#ff4d6d")
        with c2: kpi('<i class="fa-solid fa-bullseye"></i>',"Win Rate",     f"{wr_val:.1f}%", f"{len(wins)}W · {len(losses)}L","#00d4aa" if wr_val>=50 else "#ff4d6d")
        with c3: kpi('<i class="fa-solid fa-scale-balanced"></i>',"Profit Factor",f"{pf:.2f}" if pf else "—","Gain/Perte",          "#00d4aa" if (pf or 0)>=1.5 else "#ff9f43")
        with c4: kpi('<i class="fa-solid fa-arrow-trend-down"></i>',"Max Drawdown", f"${mdd:,.2f}",   "Perte cumulée max",             "#ff4d6d")
        with c5: kpi('<i class="fa-solid fa-bolt"></i>',"R:R Moyen",   f"{avg_rr:.2f}R" if avg_rr else "—","Risque/Récomp","#7c6aff")
        with c6: kpi('<i class="fa-solid fa-arrow-trend-up"></i>',"Gain moyen",   fmt(avg_w),       "Par trade gagnant",             "#00d4aa")
        st.markdown(" ")

        # ── Comparaison Réel/Démo si mode Tous ───────────────────────────────
        if st.session_state.mode_filter == "Tous" and "trade_mode" in df.columns:
            df_r = df[df["trade_mode"]=="Réel"]; df_d = df[df["trade_mode"]=="Démo"]
            if not df_r.empty and not df_d.empty:
                st.markdown("#### Comparaison Réel · Démo")
                cr1,cr2,cr3,cr4 = st.columns(4)
                wr_r = len(df_r[df_r["pnl"]>0])/len(df_r)*100 if len(df_r) else 0
                wr_d = len(df_d[df_d["pnl"]>0])/len(df_d)*100 if len(df_d) else 0
                with cr1: kpi('<i class="fa-solid fa-coins"></i>',"P&L Réel",     fmt(df_r["pnl"].sum()),f"{len(df_r)} trades","#00d4aa")
                with cr2: kpi('<i class="fa-solid fa-flask"></i>',"P&L Démo",     fmt(df_d["pnl"].sum()),f"{len(df_d)} trades","#ff9f43")
                with cr3: kpi('<i class="fa-solid fa-bullseye"></i>',"Win Rate Réel",f"{wr_r:.1f}%","Compte réel","#00d4aa")
                with cr4: kpi('<i class="fa-solid fa-bullseye"></i>',"Win Rate Démo",f"{wr_d:.1f}%","Compte démo","#ff9f43")
                st.markdown(" ")

        # ══════════════════════════════════════════════════════════════════════
        # ROW 1 : Courbe capital + Distribution trades
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("### Performance dans le temps")
        r1c1, r1c2 = st.columns([3,2])

        with r1c1:
            st.markdown("#### Courbe de Capital")
            fig_eq = go.Figure()
            # Zone sous la courbe
            fig_eq.add_trace(go.Scatter(
                x=df_s["date"].tolist(), y=cumul.tolist(),
                mode="lines+markers",
                line=dict(color="#00d4aa", width=2.5),
                marker=dict(color="#00d4aa", size=5, line=dict(color="#0a0c12",width=1)),
                fill="tozeroy", fillcolor="rgba(0,212,170,0.07)",
                name="Capital cumulé",
                hovertemplate="<b>%{x}</b><br>Capital: %{y:+,.2f}$<extra></extra>",
            ))
            # Ligne zéro
            fig_eq.add_hline(y=0, line_dash="dot", line_color="#1e2535", line_width=1)
            fig_eq.update_layout(**PLOTLY_LAYOUT, height=260, showlegend=False)
            fig_eq.update_xaxes(gridcolor="#1e2535", linecolor="#1e2535", showgrid=True)
            fig_eq.update_yaxes(gridcolor="#1e2535", linecolor="#1e2535", tickprefix="$", showgrid=True)
            st.plotly_chart(fig_eq, use_container_width=True)

        with r1c2:
            st.markdown("#### Répartition")
            fig_pie = go.Figure(go.Pie(
                values=[len(wins), len(losses)],
                labels=["Gagnants","Perdants"], hole=0.62,
                marker=dict(colors=["#00d4aa","#ff4d6d"], line=dict(color="#111520",width=3)),
                hovertemplate="<b>%{label}</b>: %{value} trades (%{percent})<extra></extra>",
            ))
            fig_pie.add_annotation(text=f"{wr_val:.0f}%", x=0.5, y=0.58,
                font=dict(size=28,color="#00d4aa",family="JetBrains Mono"), showarrow=False)
            fig_pie.add_annotation(text="Win Rate", x=0.5, y=0.38,
                font=dict(size=12,color="#6b7894"), showarrow=False)
            fig_pie.update_layout(**PLOTLY_LAYOUT, height=260, showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.05, font=dict(color="#8892a4")))
            st.plotly_chart(fig_pie, use_container_width=True)

        # ══════════════════════════════════════════════════════════════════════
        # ROW 2 : Timeline des trades + P&L mensuel
        # ══════════════════════════════════════════════════════════════════════
        r2c1, r2c2 = st.columns([3,2])

        with r2c1:
            st.markdown("#### Trades individuels")
            colors_trades = ["#00d4aa" if p>0 else "#ff4d6d" for p in df_s["pnl"]]
            fig_tl = go.Figure()
            fig_tl.add_trace(go.Bar(
                x=df_s["date"].tolist(),
                y=df_s["pnl"].tolist(),
                marker_color=colors_trades,
                marker_opacity=0.85,
                name="P&L par trade",
                hovertemplate="<b>%{x}</b><br>%{customdata[0]} · %{customdata[1]}<br>P&L: %{y:+,.2f}$<extra></extra>",
                customdata=list(zip(df_s["symbol"].tolist(), df_s["direction"].tolist())),
            ))
            fig_tl.add_hline(y=0, line_dash="dot", line_color="#1e2535", line_width=1)
            fig_tl.update_layout(**PLOTLY_LAYOUT, height=220, showlegend=False)
            fig_tl.update_xaxes(gridcolor="#1e2535", linecolor="#1e2535")
            fig_tl.update_yaxes(gridcolor="#1e2535", linecolor="#1e2535", tickprefix="$")
            st.plotly_chart(fig_tl, use_container_width=True)

        with r2c2:
            st.markdown("#### P&L Mensuel")
            fig_mo = go.Figure(go.Bar(
                x=monthly["label"].tolist(), y=monthly["pnl"].tolist(),
                marker_color=["#00d4aa" if v>=0 else "#ff4d6d" for v in monthly["pnl"]],
                marker_opacity=0.85,
                hovertemplate="<b>%{x}</b><br>%{y:+,.2f}$<extra></extra>",
            ))
            fig_mo.add_hline(y=0, line_dash="dot", line_color="#1e2535", line_width=1)
            fig_mo.update_layout(**PLOTLY_LAYOUT, height=220)
            fig_mo.update_xaxes(gridcolor="#1e2535", linecolor="#1e2535")
            fig_mo.update_yaxes(gridcolor="#1e2535", linecolor="#1e2535", tickprefix="$")
            st.plotly_chart(fig_mo, use_container_width=True)

        # ══════════════════════════════════════════════════════════════════════
        # ROW 3 : Classement actifs + P&L par stratégie
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("### Analyse par Actif & Stratégie")
        r3c1, r3c2 = st.columns(2)

        with r3c1:
            st.markdown("#### Classement des Actifs — rentabilité décroissante")
            by_sym = df.groupby("symbol").agg(
                pnl=("pnl","sum"),
                trades=("pnl","count"),
                wins=("pnl", lambda x: (x>0).sum()),
            ).reset_index()
            by_sym["win_rate"] = (by_sym["wins"]/by_sym["trades"]*100).round(1)
            by_sym = by_sym.sort_values("pnl", ascending=False)

            colors_sym = ["#00d4aa" if v>=0 else "#ff4d6d" for v in by_sym["pnl"]]
            fig_sym = go.Figure(go.Bar(
                y=by_sym["symbol"].tolist(),
                x=by_sym["pnl"].tolist(),
                orientation="h",
                marker_color=colors_sym,
                marker_opacity=0.85,
                text=[f"{fmt(v)}  ({wr}% win)" for v,wr in zip(by_sym["pnl"], by_sym["win_rate"])],
                textposition="outside",
                textfont=dict(color="#8892a4", size=11),
                hovertemplate="<b>%{y}</b><br>P&L: %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                customdata=list(zip(by_sym["trades"].tolist(), by_sym["win_rate"].tolist())),
            ))
            fig_sym.add_vline(x=0, line_dash="dot", line_color="#1e2535", line_width=1)
            h_sym = max(280, len(by_sym)*45)
            fig_sym.update_layout(**PLOTLY_LAYOUT, height=h_sym)
            fig_sym.update_xaxes(gridcolor="#1e2535", linecolor="#1e2535", tickprefix="$")
            fig_sym.update_yaxes(gridcolor="#1e2535", linecolor="#1e2535", categoryorder="total ascending")
            st.plotly_chart(fig_sym, use_container_width=True)

        with r3c2:
            st.markdown("#### P&L par Stratégie")
            by_strat = df.groupby("strategy").agg(
                pnl=("pnl","sum"),
                trades=("pnl","count"),
                wins=("pnl", lambda x: (x>0).sum()),
            ).reset_index()
            by_strat["win_rate"] = (by_strat["wins"]/by_strat["trades"]*100).round(1)
            by_strat = by_strat.sort_values("pnl", ascending=False)

            fig_st = go.Figure(go.Bar(
                y=by_strat["strategy"].tolist(),
                x=by_strat["pnl"].tolist(),
                orientation="h",
                marker_color=CHART_COLORS[:len(by_strat)],
                marker_opacity=0.85,
                text=[f"{fmt(v)}  ({wr}% win)" for v,wr in zip(by_strat["pnl"], by_strat["win_rate"])],
                textposition="outside",
                textfont=dict(color="#8892a4", size=11),
                hovertemplate="<b>%{y}</b><br>P&L: %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                customdata=list(zip(by_strat["trades"].tolist(), by_strat["win_rate"].tolist())),
            ))
            fig_st.add_vline(x=0, line_dash="dot", line_color="#1e2535", line_width=1)
            h_st = max(280, len(by_strat)*45)
            fig_st.update_layout(**PLOTLY_LAYOUT, height=h_st)
            fig_st.update_xaxes(gridcolor="#1e2535", linecolor="#1e2535", tickprefix="$")
            fig_st.update_yaxes(gridcolor="#1e2535", linecolor="#1e2535", categoryorder="total ascending")
            st.plotly_chart(fig_st, use_container_width=True)

        # ══════════════════════════════════════════════════════════════════════
        # ROW 4 : Heatmap Actif × Émotion + Stats émotions
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("### Psychologie de Trading")
        r4c1, r4c2 = st.columns([3,2])

        with r4c1:
            st.markdown("#### Heatmap : Actif × Émotion")
            if len(df["symbol"].unique()) >= 1 and len(df["mood"].unique()) >= 1:
                pivot = df.pivot_table(
                    values="pnl", index="mood", columns="symbol",
                    aggfunc="sum", fill_value=0
                )
                # Ordonner les émotions
                mood_order = [m for m in ["Euphorique","Confiant","Neutre","Anxieux","Peureux","Frustré"]
                              if m in pivot.index]
                pivot = pivot.reindex(mood_order)

                # Ajouter emoji aux labels
                y_labels = [m for m in pivot.index]

                fig_hm = go.Figure(go.Heatmap(
                    z=pivot.values.tolist(),
                    x=pivot.columns.tolist(),
                    y=y_labels,
                    colorscale=[
                        [0.0,  "#ff4d6d"],
                        [0.45, "#2d1a2e"],
                        [0.5,  "#1e2535"],
                        [0.55, "#1a2d25"],
                        [1.0,  "#00d4aa"],
                    ],
                    zmid=0,
                    text=[[f"${v:+,.0f}" for v in row] for row in pivot.values],
                    texttemplate="%{text}",
                    textfont=dict(size=11, color="white"),
                    hovertemplate="<b>%{y} · %{x}</b><br>P&L: %{z:+,.2f}$<extra></extra>",
                    showscale=True,
                    colorbar=dict(
                        tickprefix="$", tickfont=dict(color="#6b7894"),
                        bgcolor="#111520", bordercolor="#1e2535",
                    ),
                ))
                fig_hm.update_layout(**PLOTLY_LAYOUT, height=max(280, len(pivot)*55))
                fig_hm.update_layout(margin=dict(l=120, r=60, t=20, b=60))
                fig_hm.update_xaxes(side="bottom", tickangle=-30, gridcolor="#1e2535", linecolor="#1e2535")
                fig_hm.update_yaxes(gridcolor="#1e2535", linecolor="#1e2535")
                st.plotly_chart(fig_hm, use_container_width=True)
            else:
                st.info("Pas assez de données pour la heatmap.")

        with r4c2:
            st.markdown("#### P&L par Émotion")
            by_mood = df.groupby("mood").agg(
                pnl=("pnl","sum"),
                trades=("pnl","count"),
                wins=("pnl", lambda x: (x>0).sum()),
            ).reset_index()
            by_mood["win_rate"] = (by_mood["wins"]/by_mood["trades"]*100).round(1)
            by_mood["emoji"]    = by_mood["mood"]
            by_mood["label"]    = by_mood["mood"]
            by_mood = by_mood.sort_values("pnl", ascending=False)

            fig_mood = go.Figure(go.Bar(
                y=by_mood["label"].tolist(),
                x=by_mood["pnl"].tolist(),
                orientation="h",
                marker_color=["#00d4aa" if v>=0 else "#ff4d6d" for v in by_mood["pnl"]],
                marker_opacity=0.85,
                text=[f"{fmt(v)}  ({wr}% win  ·  {n} trades)"
                      for v,wr,n in zip(by_mood["pnl"], by_mood["win_rate"], by_mood["trades"])],
                textposition="outside",
                textfont=dict(color="#8892a4", size=10),
                hovertemplate="<b>%{y}</b><br>P&L: %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                customdata=list(zip(by_mood["trades"].tolist(), by_mood["win_rate"].tolist())),
            ))
            fig_mood.add_vline(x=0, line_dash="dot", line_color="#1e2535", line_width=1)
            fig_mood.update_layout(**PLOTLY_LAYOUT, height=max(280, len(by_mood)*55))
            fig_mood.update_xaxes(gridcolor="#1e2535", linecolor="#1e2535", tickprefix="$")
            fig_mood.update_yaxes(gridcolor="#1e2535", linecolor="#1e2535")
            st.plotly_chart(fig_mood, use_container_width=True)

        # ══════════════════════════════════════════════════════════════════════
        # ROW 5 : Derniers trades
        # ══════════════════════════════════════════════════════════════════════
        st.markdown("### Derniers Trades")
        recent = df.sort_values("date", ascending=False).head(8)
        rows_html = ""
        for _, t in recent.iterrows():
            c  = "#00d4aa" if t["pnl"]>=0 else "#ff4d6d"
            dc = "b-win" if t["direction"]=="LONG" else "b-loss"
            mc = "b-real" if t.get("trade_mode","Réel")=="Réel" else "b-demo"
            rows_html += f"""<tr>
                <td style="color:#6b7894;font-family:monospace">{t["date"]}</td>
                <td>{badge(t["symbol"],"b-sym")}</td>
                <td>{badge(t["direction"],dc)}</td>
                <td>{badge(t.get("trade_mode","Réel"),mc)}</td>
                <td style="font-size:16px" title="{t["mood"]}">{mood_html(t['mood'])}</td>
                <td>{badge(t["strategy"],"b-str")}</td>
                <td style="font-family:monospace;font-weight:800;color:{c}">{fmt(t["pnl"])}</td>
                <td style="color:#6b7894;font-size:12px">{str(t.get("notes",""))[:40]}</td>
            </tr>"""
        st.markdown(f"""<table class="tj-table"><thead><tr>
            <th>Date</th><th>Symbole</th><th>Dir.</th><th>Mode</th>
            <th>Mood</th><th>Stratégie</th><th>P&L $</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════
# PAGE : JOURNAL
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "journal":
    st.markdown("# Journal des Trades")
    mode_banner()

    df_all = get_df("Tous")

    if df_all.empty:
        st.info("Aucun trade. Ajoutez-en un avec **Nouveau Trade** ou importez depuis MT5.")
    else:
        # ── FILTRES ──────────────────────────────────────────────────────────
        st.markdown('''<div style="background:#111520;border:1px solid #1e2535;
            border-radius:14px;padding:18px 20px;margin-bottom:18px">''',
            unsafe_allow_html=True)

        fa1, fa2, fa3, fa4, fa5 = st.columns(5)

        dates_avail = sorted(df_all["date"].dropna().unique().tolist())
        d_min = date.fromisoformat(dates_avail[0])  if dates_avail else date(2024,1,1)
        d_max = date.fromisoformat(dates_avail[-1]) if dates_avail else date.today()

        with fa1:
            f_from = st.date_input("Du", value=d_min, key="j_from",
                                   min_value=d_min, max_value=d_max)
        with fa2:
            f_to   = st.date_input("Au", value=d_max, key="j_to",
                                   min_value=d_min, max_value=d_max)
        with fa3:
            syms   = ["Tous"] + sorted(df_all["symbol"].unique().tolist())
            f_sym  = st.selectbox("Actif", syms, key="j_sym")
        with fa4:
            f_mode = st.selectbox("Mode", ["Tous","Réel","Démo"], key="j_mode")
        with fa5:
            f_dir  = st.selectbox("Direction", ["Tous","LONG","SHORT"], key="j_dir")

        st.markdown("</div>", unsafe_allow_html=True)

        # ── APPLIQUER FILTRES ─────────────────────────────────────────────────
        df = df_all.copy()
        df = df[df["date"].between(str(f_from), str(f_to))]
        if f_sym  != "Tous": df = df[df["symbol"]    == f_sym]
        if f_mode != "Tous": df = df[df["trade_mode"].isin([f_mode, f_mode+" 💰" if f_mode=="Réel" else f_mode+" 🧪"])]
        if f_dir  != "Tous": df = df[df["direction"] == f_dir]
        df = df.sort_values("date", ascending=False)

        # Résumé filtres
        total_f = df["pnl"].sum() if not df.empty else 0
        wins_f  = len(df[df["pnl"] > 0]) if not df.empty else 0
        col_f   = "#00d4aa" if total_f >= 0 else "#ff4d6d"
        st.markdown(
            f'''<div style="display:flex;gap:24px;align-items:center;
                margin-bottom:16px;padding:10px 16px;background:#0d111d;
                border-radius:10px;border:1px solid #1e2535">
                <span style="color:#6b7894;font-size:13px">
                    <b style="color:#e8ecf4">{len(df)}</b> trades affichés
                </span>
                <span style="color:#6b7894;font-size:13px">
                    P&L : <b style="color:{col_f}">{fmt(total_f)}</b>
                </span>
                <span style="color:#6b7894;font-size:13px">
                    Win rate : <b style="color:#00d4aa">{wins_f/len(df)*100:.0f}%</b>
                </span>
            </div>''' if not df.empty else "",
            unsafe_allow_html=True
        )

        # ── TABLEAU ───────────────────────────────────────────────────────────
        if df.empty:
            st.info("Aucun trade pour ces filtres.")
        else:
            rows_html = ""
            for _, t in df.iterrows():
                c    = "#00d4aa" if t["pnl"]>=0 else "#ff4d6d"
                dc   = "b-win" if t["direction"]=="LONG" else "b-loss"
                rr_v = t["rr"]
                rr_c = "#00d4aa" if (rr_v or 0)>=2 else "#ff9f43" if (rr_v or 0)>=1 else "#ff4d6d"
                mc   = "b-real" if t.get("trade_mode","Réel") in ("Réel","Réel 💰") else "b-demo"
                rows_html += f"""<tr>
                    <td style="color:#6b7894;font-family:monospace;white-space:nowrap">{t["date"]}</td>
                    <td>{badge(t["symbol"],"b-sym")}</td>
                    <td>{badge(t["direction"],dc)}</td>
                    <td>{badge(t.get("trade_mode","Réel"),mc)}</td>
                    <td style="font-family:monospace">{t.get("entry","—")}</td>
                    <td style="font-family:monospace">{t.get("exit","—")}</td>
                    <td style="font-family:monospace;font-weight:800;color:{c};white-space:nowrap">{fmt(t["pnl"])}</td>
                    <td style="font-family:monospace;color:{rr_c}">{rr_v if rr_v else "—"}</td>
                    <td>{badge(t["strategy"],"b-str")}</td>
                    <td style="text-align:center">{mood_html(t["mood"])}</td>
                    <td style="color:#6b7894;font-size:12px;max-width:160px">{str(t.get("notes",""))[:45]}</td>
                </tr>"""
            st.markdown(f"""<div style="overflow-x:auto"><table class="tj-table">
                <thead><tr>
                    <th>Date</th><th>Actif</th><th>Dir.</th><th>Mode</th>
                    <th>Entrée</th><th>Sortie</th><th>P&L $</th><th>R:R</th>
                    <th>Stratégie</th><th>Mood</th><th>Notes</th>
                </tr></thead><tbody>{rows_html}</tbody></table></div>""",
                unsafe_allow_html=True)

        # ── MODIFIER / SUPPRIMER ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("##### Modifier ou supprimer un trade")

        # Construire les labels depuis les trades filtrés
        if not df.empty:
            df_sel = df.copy()
        else:
            df_sel = df_all.sort_values("date", ascending=False)

        if df_sel.empty:
            st.info("Aucun trade disponible.")
        else:
            labels = [
                f"{r['date']}  ·  {r['symbol']}  ·  {r.get('trade_mode','Réel')}  ·  {r['direction']}  ·  {fmt(r['pnl'])}"
                for _, r in df_sel.iterrows()
            ]
            ids = df_sel["id"].tolist()

            sel_lbl = st.selectbox("Sélectionner un trade", labels,
                                   label_visibility="collapsed")
            sel_id  = ids[labels.index(sel_lbl)]

            # Afficher le détail du trade sélectionné
            sel_trade = next((t for t in st.session_state.trades if t["id"] == sel_id), None)
            if sel_trade:
                mc_s = "mode-banner-real" if sel_trade.get("trade_mode","Réel") in ("Réel","Réel 💰") else "mode-banner-demo"
                pnl_s = sel_trade.get("pnl", 0)
                col_s = "#00d4aa" if pnl_s >= 0 else "#ff4d6d"
                st.markdown(f'''<div style="background:#0d111d;border:1px solid #1e2535;
                    border-radius:10px;padding:12px 18px;margin:8px 0;
                    display:flex;gap:24px;align-items:center;flex-wrap:wrap">
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
                             use_container_width=True):
                    st.session_state.edit_id = sel_id
                    st.session_state.page = "add"
                    st.rerun()
            with cd:
                if st.button("Supprimer", icon=":material/delete:",
                             use_container_width=True):
                    st.session_state["confirm_del"] = sel_id

            # Confirmation suppression
            if st.session_state.get("confirm_del") == sel_id:
                st.warning(
                    f"Confirmer la suppression de ce trade ? "
                    f"**{sel_trade.get('date','')} · {sel_trade.get('symbol','')} · {fmt(sel_trade.get('pnl',0))}**"
                )
                cc1, cc2, _ = st.columns([1, 1, 5])
                with cc1:
                    if st.button("Oui, supprimer", icon=":material/check:",
                                 use_container_width=True):
                        st.session_state.trades = [
                            t for t in st.session_state.trades if t["id"] != sel_id
                        ]
                        ok = cloud_save(st.session_state.trades)
                        st.session_state.pop("confirm_del", None)
                        if ok:
                            st.success("Trade supprimé et sauvegardé.")
                        else:
                            st.error("Supprimé localement mais erreur de sauvegarde.")
                        st.rerun()
                with cc2:
                    if st.button("Annuler", icon=":material/close:",
                                 use_container_width=True):
                        st.session_state.pop("confirm_del", None)
                        st.rerun()

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
            cur_mode = ev("trade_mode","Réel")
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
            new_t = {"id":ex["id"] if is_edit else int(datetime.now().timestamp()*1000),
                "date":str(d_date),"symbol":d_sym,"direction":d_dir,"trade_mode":d_mode,
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

    # ── Choix du mode ────────────────────────────────────────────────────────
    ic1, ic2 = st.columns([2, 3])
    with ic1:
        imp_mode = st.radio("Type de compte", ["Réel", "Démo"], horizontal=True)
    with ic2:
        mc = "mode-banner-real" if imp_mode == "Réel" else "mode-banner-demo"
        st.markdown(f'<div class="{mc}" style="margin-top:8px">Trades importés étiquetés : {imp_mode}</div>',
                    unsafe_allow_html=True)

    st.markdown("---")

    with st.expander("Comment exporter depuis MT5 ?", expanded=False):
        st.markdown("""
        1. MT5 → **Affichage → Historique des transactions**
        2. Clic droit → **Enregistrer en tant que rapport** → **Detailed Report** → **XLSX** ou **CSV**
        
        **Colonnes attendues** :  
        `Time · Position · Symbol · Type · Volume · Price · S/L · T/P · Time · Price · Commission · Swap · Profit`
        """)

    uploaded = st.file_uploader(
        "Choisir le fichier MT5 (CSV, TXT ou XLSX)",
        type=["csv", "txt", "xlsx", "xls"],
        label_visibility="collapsed"
    )

    if uploaded:
        fname      = uploaded.name.lower()
        file_bytes = uploaded.getvalue()   # lire UNE SEULE FOIS en mémoire

        # ── 1. Lecture brute ─────────────────────────────────────────────────
        try:
            if fname.endswith((".xlsx", ".xls")):
                # Trouver la ligne d'en-tête (peut y avoir des titres au-dessus)
                xls_scan = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)
                header_row = 0
                for i, row in xls_scan.iterrows():
                    vals = [str(v).strip().lower() for v in row.values]
                    if any(k in vals for k in ["symbol", "time", "profit", "type", "position"]):
                        header_row = i
                        break
                df_raw = pd.read_excel(io.BytesIO(file_bytes), skiprows=header_row, dtype=str)

            else:
                raw_text = file_bytes.decode("utf-8", errors="replace")
                # Détecter séparateur
                counts = {"\t": raw_text.count("\t"), ";": raw_text.count(";"), ",": raw_text.count(",")}
                sep = max(counts, key=counts.get)

                # Trouver ligne d'en-tête
                tmp = pd.read_csv(io.StringIO(raw_text), sep=sep, header=None,
                                  dtype=str, on_bad_lines="skip")
                header_row = 0
                for i, row in tmp.iterrows():
                    vals = [str(v).strip().lower() for v in row.values]
                    if any(k in vals for k in ["symbol", "time", "profit", "type", "position"]):
                        header_row = i
                        break
                df_raw = pd.read_csv(io.StringIO(raw_text), sep=sep, skiprows=header_row,
                                     dtype=str, on_bad_lines="skip")

        except Exception as e:
            st.error(f"Erreur lecture fichier : {e}")
            st.exception(e)
            st.stop()

        # ── 2. Nettoyage colonnes ────────────────────────────────────────────
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        df_raw = df_raw.dropna(axis=1, how="all")
        df_raw = df_raw.loc[df_raw.astype(str).apply(
            lambda r: r.str.strip().ne("").any(), axis=1)]

        # Renommer colonnes dupliquées : Time→Time, Time→Time_2 / Price→Price, Price→Price_2
        seen_cols = {}
        renamed   = []
        for c in df_raw.columns:
            key = c.strip().lower()
            if key in seen_cols:
                seen_cols[key] += 1
                renamed.append(f"{c}_{seen_cols[key]}")
            else:
                seen_cols[key] = 1
                renamed.append(c)
        df_raw.columns = renamed

        # ── 3. Mapping colonnes ───────────────────────────────────────────────
        def norm_col(s):
            import re
            return re.sub(r'[\s/_\\-]+', '_', str(s).strip().lower())

        col_index = {norm_col(c): c for c in df_raw.columns}

        def find_col(*candidates):
            # Recherche exacte puis partielle
            for cand in candidates:
                key = norm_col(cand)
                if key in col_index:
                    return col_index[key]
            for cand in candidates:
                key = norm_col(cand)
                for k, v in col_index.items():
                    if key in k or k in key:
                        return v
            return None

        col_open_time   = find_col("time", "time_1", "open_time", "open time", "date")
        col_close_time  = find_col("time_2", "close_time", "close time")
        col_symbol      = find_col("symbol", "asset", "instrument", "pair")
        col_type        = find_col("type", "action", "order_type", "operation")
        col_volume      = find_col("volume", "vol", "lots", "size", "quantity")
        col_open_price  = find_col("price", "price_1", "open_price", "entry_price", "entry price")
        col_close_price = find_col("price_2", "close_price", "exit_price", "exit price")
        col_sl          = find_col("s / l", "s/l", "sl", "stop_loss", "stoploss", "stop loss")
        col_tp          = find_col("t / p", "t/p", "tp", "take_profit", "takeprofit", "take profit")
        col_commission  = find_col("commission", "comm", "fee", "fees")
        col_swap        = find_col("swap", "rollover")
        col_profit      = find_col("profit", "p&l", "result", "net_profit", "net profit")

        # Afficher le diagnostic
        with st.expander(f"Colonnes détectées ({len(df_raw.columns)})", expanded=True):
            d1, d2 = st.columns(2)
            mapping_info = [
                ("Open Time",    col_open_time),
                ("Close Time",   col_close_time),
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
            half = len(mapping_info) // 2
            with d1:
                for k, v in mapping_info[:half]:
                    st.markdown(f"{'OK' if v else '—'} · **{k}** → `{v or 'Non trouvé'}`")
            with d2:
                for k, v in mapping_info[half:]:
                    st.markdown(f"{'OK' if v else '—'} · **{k}** → `{v or 'Non trouvé'}`")
            st.caption(f"Toutes les colonnes : {list(df_raw.columns)}")
            st.dataframe(df_raw.head(3))

        if not col_profit:
            st.error("Colonne Profit introuvable. Vérifiez les colonnes affichées ci-dessus.")
            st.stop()

        if not col_symbol:
            st.error("Colonne Symbol introuvable.")
            st.stop()

        # ── 4. Filtrage lignes valides ────────────────────────────────────────
        df_work = df_raw.copy()

        # Supprimer dépôts / retraits / balance
        if col_type:
            df_work = df_work[~df_work[col_type].str.lower().str.contains(
                "balance|deposit|withdrawal|credit|bonus", na=False)]

        # Garder lignes avec profit non nul
        def has_value(x):
            try:
                return float(str(x).replace(" ", "").replace(",", ".")) != 0
            except:
                return False

        df_closed = df_work[df_work[col_profit].apply(has_value)].copy()
        if df_closed.empty:
            df_closed = df_work.dropna(subset=[col_profit]).copy()

        if df_closed.empty:
            st.warning("Aucun trade fermé détecté. Vérifiez le fichier.")
            st.stop()

        st.success(f"{len(df_closed)} lignes de trades détectées")

        # ── 5. Construction des trades ────────────────────────────────────────
        SYM_MAP_LOCAL = {
            "EURUSD":"EUR/USD","GBPUSD":"GBP/USD","USDJPY":"USD/JPY","USDCHF":"USD/CHF",
            "AUDUSD":"AUD/USD","NZDUSD":"NZD/USD","USDCAD":"USD/CAD","EURGBP":"EUR/GBP",
            "EURJPY":"EUR/JPY","GBPJPY":"GBP/JPY","EURCAD":"EUR/CAD","AUDCAD":"AUD/CAD",
            "XAUUSD":"GOLD","XAGUSD":"SILVER","BTCUSD":"BTC/USD","ETHUSD":"ETH/USD",
            "US30":"DOW30","US500":"SP500","SP500":"SP500","USTEC":"NAS100","NAS100":"NAS100",
            "UK100":"FTSE100","GER40":"DAX40","FRA40":"CAC40","USOIL":"OIL","UKOIL":"OIL",
        }

        new_trades = []
        skipped    = 0

        for _, row in df_closed.iterrows():
            try:
                def rv(col, default="0"):
                    if not col: return default
                    v = row.get(col, default)
                    return str(v) if v is not None and str(v).lower() != "nan" else default

                def rfloat(col):
                    try:
                        return float(rv(col).replace(" ", "").replace(",", "."))
                    except:
                        return 0.0

                # Date
                try:
                    parsed_date = pd.to_datetime(rv(col_open_time, str(date.today()))).strftime("%Y-%m-%d")
                except:
                    parsed_date = str(date.today())

                # Symbole
                sym_raw = rv(col_symbol, "UNKNOWN").strip().upper()
                symbol  = SYM_MAP_LOCAL.get(sym_raw, sym_raw)

                # Direction
                direction = "LONG"
                if col_type:
                    tv = rv(col_type).strip().lower()
                    if any(k in tv for k in ["sell", "short", "s", "vente"]):
                        direction = "SHORT"

                # Prix
                entry_price = rfloat(col_open_price)
                exit_price  = rfloat(col_close_price)
                sl_val      = rfloat(col_sl)
                tp_val      = rfloat(col_tp)
                volume      = rfloat(col_volume)

                # P&L net = profit + commission + swap
                profit   = rfloat(col_profit)
                comm     = rfloat(col_commission)
                swap_v   = rfloat(col_swap)
                pnl_reel = round(profit + comm + swap_v, 2)

                parts = []
                if volume:  parts.append(f"vol:{volume}")
                if comm:    parts.append(f"comm:{comm:.2f}")
                if swap_v:  parts.append(f"swap:{swap_v:.2f}")
                notes_str = "Import MT5" + (" · " + " · ".join(parts) if parts else "")

                new_trades.append({
                    "id":         int(datetime.now().timestamp() * 1000000) + len(new_trades),
                    "date":       parsed_date,
                    "symbol":     symbol,
                    "direction":  direction,
                    "trade_mode": imp_mode,
                    "entry":      entry_price,
                    "exit":       exit_price,
                    "sl":         sl_val,
                    "tp":         tp_val,
                    "pnl":        pnl_reel,
                    "strategy":   "Importé MT5",
                    "mood":       "Neutre",
                    "notes":      notes_str,
                })
            except Exception as ex:
                skipped += 1

        if not new_trades:
            st.error("Aucun trade valide extrait. Vérifiez le diagnostic des colonnes.")
            st.stop()

        # ── 6. Résumé + aperçu ────────────────────────────────────────────────
        total_imp = round(sum(t["pnl"] for t in new_trades), 2)
        wins_imp  = [t for t in new_trades if t["pnl"] > 0]
        col_t     = "#00d4aa" if total_imp >= 0 else "#ff4d6d"

        st.markdown(f"### {len(new_trades)} trades prêts à importer" +
                    (f" · {skipped} ignorés" if skipped else ""))
        s1, s2, s3 = st.columns(3)
        with s1: kpi('<i class="fa-solid fa-coins"></i>', "P&L Total",  fmt(total_imp),  "Résultat global",           col_t)
        with s2: kpi('<i class="fa-solid fa-circle-check"></i>', "Gagnants",   str(len(wins_imp)), f"{len(wins_imp)/len(new_trades)*100:.0f}% win", "#00d4aa")
        with s3: kpi('<i class="fa-solid fa-circle-xmark"></i>', "Perdants",   str(len(new_trades)-len(wins_imp)), "Trades négatifs", "#ff4d6d")
        st.markdown(" ")

        rows_html = ""
        for t in new_trades[:30]:
            c  = "#00d4aa" if t["pnl"] >= 0 else "#ff4d6d"
            dc = "b-win" if t["direction"] == "LONG" else "b-loss"
            mc = "b-real" if t["trade_mode"] == "Réel" else "b-demo"
            rows_html += f"""<tr>
                <td style="color:#6b7894;font-family:monospace">{t["date"]}</td>
                <td>{badge(t["symbol"],"b-sym")}</td>
                <td>{badge(t["direction"],dc)}</td>
                <td>{badge(t["trade_mode"],mc)}</td>
                <td style="font-family:monospace">{t["entry"] or "—"}</td>
                <td style="font-family:monospace">{t["exit"] or "—"}</td>
                <td style="font-family:monospace;font-weight:800;color:{c}">{fmt(t["pnl"])}</td>
                <td style="color:#6b7894;font-size:11px">{t["notes"]}</td>
            </tr>"""
        if len(new_trades) > 30:
            rows_html += f"<tr><td colspan='8' style='color:#6b7894;text-align:center;padding:10px'>... et {len(new_trades)-30} autres</td></tr>"

        st.markdown(f"""<div style="overflow-x:auto"><table class="tj-table"><thead><tr>
            <th>Date</th><th>Symbole</th><th>Dir.</th><th>Mode</th>
            <th>Entrée</th><th>Sortie</th><th>P&L $</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table></div>""", unsafe_allow_html=True)

        st.markdown("---")
        add_mode = st.radio("Mode d'import",
            ["Ajouter aux trades existants", "Remplacer tous les trades"],
            horizontal=True)

        if st.button("Confirmer l'import", icon=":material/check_circle:", use_container_width=True):
            if "Remplacer" in add_mode:
                st.session_state.trades = new_trades
            else:
                existing_ids = {t["id"] for t in st.session_state.trades}
                st.session_state.trades += [t for t in new_trades if t["id"] not in existing_ids]
            ok = cloud_save(st.session_state.trades)
            st.success(f"{len(new_trades)} trades importés ({imp_mode}) — " +
                       ("synchronisés !" if ok else "erreur sync GitHub."))
            st.session_state.page = "dashboard"
            st.rerun()
