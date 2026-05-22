import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import json, os, base64, requests, io

st.set_page_config(page_title="Trading Journal Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
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
CHART_COLORS = ["#00d4aa","#7c6aff","#ff9f43","#ff4d6d","#54a0ff","#5f27cd","#00cec9","#fdcb6e"]
TRADE_MODES  = ["Réel 💰", "Démo 🧪"]
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

GH_TOKEN = st.secrets.get("GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN",""))
GH_REPO  = st.secrets.get("GITHUB_REPO",  "SylvainNOFOZO/trading-journal")
GH_FILE  = st.secrets.get("DATA_FILE",    "trades_data.json")
GH_API   = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE}"
GH_HDR   = {"Authorization": f"token {GH_TOKEN}", "Accept":"application/vnd.github.v3+json"}

def gh_load():
    try:
        r = requests.get(GH_API, headers=GH_HDR, timeout=8); r.raise_for_status()
        d = r.json()
        return json.loads(base64.b64decode(d["content"]).decode()), d["sha"]
    except Exception as e:
        st.error(f"Erreur chargement GitHub : {e}"); return [], None

def gh_save(trades, sha):
    try:
        content = base64.b64encode(json.dumps(trades, ensure_ascii=False, indent=2).encode()).decode()
        r = requests.put(GH_API, headers=GH_HDR,
            json={"message":f"Update trades ({len(trades)} total)","content":content,"sha":sha}, timeout=10)
        r.raise_for_status()
        return r.json()["content"]["sha"], True
    except Exception as e:
        st.error(f"Erreur sync GitHub : {e}"); return sha, False

if "trades"      not in st.session_state:
    t, s = gh_load(); st.session_state.trades = t; st.session_state.gh_sha = s
if "page"        not in st.session_state: st.session_state.page     = "dashboard"
if "edit_id"     not in st.session_state: st.session_state.edit_id  = None
if "mode_filter" not in st.session_state: st.session_state.mode_filter = "Tous"

def cloud_save(trades):
    sha, ok = gh_save(trades, st.session_state.gh_sha)
    st.session_state.gh_sha = sha; return ok

def force_reload():
    t, s = gh_load(); st.session_state.trades = t; st.session_state.gh_sha = s

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
    if "trade_mode" not in df.columns: df["trade_mode"] = "Réel 💰"
    if mode_filter == "Réel 💰":  return df[df["trade_mode"] == "Réel 💰"]
    if mode_filter == "Démo 🧪":  return df[df["trade_mode"] == "Démo 🧪"]
    return df

def kpi(icon, label, value, sub, color):
    st.markdown(f"""<div class="kpi">
        <div class="kpi-bar" style="background:{color}"></div>
        <div class="kpi-icon">{icon}</div>
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
    st.markdown("## 📈 Trading Journal")
    st.caption("Pro · v3.0  |  ☁️ GitHub Sync")
    st.divider()

    # Filtre global mode
    mode_f = st.radio("Afficher", ["Tous", "Réel 💰", "Démo 🧪"],
        index=["Tous","Réel 💰","Démo 🧪"].index(st.session_state.mode_filter),
        horizontal=True, label_visibility="collapsed")
    if mode_f != st.session_state.mode_filter:
        st.session_state.mode_filter = mode_f; st.rerun()
    st.divider()

    df_side = get_df(st.session_state.mode_filter)
    total   = df_side["pnl"].sum() if not df_side.empty else 0
    wr      = (len(df_side[df_side["pnl"]>0])/len(df_side)*100) if not df_side.empty else 0
    col_pnl = "#00d4aa" if total >= 0 else "#ff4d6d"
    mode_icon = {"Tous":"🌐","Réel 💰":"💰","Démo 🧪":"🧪"}[st.session_state.mode_filter]

    st.markdown(f"""<div style="margin-bottom:16px;padding:10px 0">
        <div style="font-size:10px;color:#6b7894;letter-spacing:1px;text-transform:uppercase">
            Capital Net · {mode_icon} {st.session_state.mode_filter}</div>
        <div style="font-size:22px;font-weight:800;color:{col_pnl};font-family:\'JetBrains Mono\',monospace">{fmt(total)}</div>
        <div style="font-size:11px;color:#6b7894;margin-top:2px">{len(df_side)} trades · {wr:.0f}% win</div>
    </div>""", unsafe_allow_html=True)

    if st.button("🏠  Dashboard",     use_container_width=True):
        st.session_state.page="dashboard"; st.session_state.edit_id=None; st.rerun()
    if st.button("📋  Journal",       use_container_width=True):
        st.session_state.page="journal";   st.session_state.edit_id=None; st.rerun()
    if st.button("➕  Nouveau Trade", use_container_width=True):
        st.session_state.page="add";       st.session_state.edit_id=None; st.rerun()
    if st.button("📂  Importer MT5",  use_container_width=True):
        st.session_state.page="import";    st.session_state.edit_id=None; st.rerun()
    if st.button("🔄  Synchroniser",  use_container_width=True):
        force_reload(); st.success("✅ Rechargé !"); st.rerun()

    st.divider()
    if not df_side.empty:
        csv = df_side.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter CSV", csv, "trades.csv", "text/csv", use_container_width=True)

    sha_s = st.session_state.get("gh_sha","")[:7] if st.session_state.get("gh_sha") else "—"
    st.markdown(f'<div class="sync-ok">☁️ GitHub · {sha_s}</div>', unsafe_allow_html=True)

# ── BANNER MODE ────────────────────────────────────────────────────────────────
def mode_banner():
    m = st.session_state.mode_filter
    if m == "Réel 💰":
        st.markdown('<div class="mode-banner-real">💰 Mode RÉEL — Performances sur compte réel</div>', unsafe_allow_html=True)
    elif m == "Démo 🧪":
        st.markdown('<div class="mode-banner-demo">🧪 Mode DÉMO — Performances sur compte démo</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mode-banner-all">🌐 Tous les trades — Réel + Démo confondus</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "dashboard":
    st.markdown("# Dashboard")
    st.caption(datetime.now().strftime("%A %d %B %Y"))
    mode_banner()
    st.divider()

    df = get_df(st.session_state.mode_filter)
    if df.empty:
        st.warning("Aucun trade. Cliquez sur **➕ Nouveau Trade** ou **📂 Importer MT5**.")
    else:
        wins   = df[df["pnl"]>0]; losses = df[df["pnl"]<=0]
        avg_w  = wins["pnl"].mean()   if len(wins)   else 0
        avg_l  = losses["pnl"].mean() if len(losses) else 0
        pf     = round(abs(avg_w/avg_l),2) if avg_l else None
        rr_df  = df[df["rr"].notna()]
        avg_rr = rr_df["rr"].mean() if len(rr_df) else None
        wr_val = len(wins)/len(df)*100
        df_s   = df.sort_values("date"); cumul = df_s["pnl"].cumsum()
        mdd    = (cumul.cummax()-cumul).max()
        df["month"]  = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
        monthly      = df.groupby("month")["pnl"].sum().reset_index()
        monthly["label"] = monthly["month"].str[5:]+"/"+monthly["month"].str[2:4]

        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("💰","P&L Net",      fmt(total),       f"{len(df)} trades",             "#00d4aa" if total>=0 else "#ff4d6d")
        with c2: kpi("🎯","Win Rate",     f"{wr_val:.1f}%", f"{len(wins)}W · {len(losses)}L","#00d4aa" if wr_val>=50 else "#ff4d6d")
        with c3: kpi("⚖️","Profit Factor",f"{pf:.2f}" if pf else "—","Gain/Perte",          "#00d4aa" if (pf or 0)>=1.5 else "#ff9f43")
        with c4: kpi("📉","Max Drawdown", f"${mdd:,.2f}",   "Perte max cumulée",             "#ff4d6d")
        st.markdown(" ")
        c1,c2,c3,c4 = st.columns(4)
        freq = len(df)/max(1,len(monthly))
        with c1: kpi("📈","Gain moyen",   fmt(avg_w),                        "Par trade gagnant",  "#00d4aa")
        with c2: kpi("📉","Perte moyenne",fmt(avg_l),                        "Par trade perdant",  "#ff4d6d")
        with c3: kpi("⚡","R:R Moyen",   f"{avg_rr:.2f}R" if avg_rr else "—","Risque/Récompense", "#7c6aff")
        with c4: kpi("📆","Trades/Mois", f"{freq:.1f}",                      "Fréquence",          "#ff9f43")
        st.markdown(" ")

        # Comparaison Réel vs Démo si "Tous"
        if st.session_state.mode_filter == "Tous":
            df_all = get_df("Tous")
            if "trade_mode" in df_all.columns:
                df_real = df_all[df_all["trade_mode"]=="Réel 💰"]
                df_demo = df_all[df_all["trade_mode"]=="Démo 🧪"]
                if not df_real.empty and not df_demo.empty:
                    st.markdown("#### ⚡ Comparaison Réel vs Démo")
                    cr1,cr2,cr3,cr4 = st.columns(4)
                    wr_r = len(df_real[df_real["pnl"]>0])/len(df_real)*100 if len(df_real) else 0
                    wr_d = len(df_demo[df_demo["pnl"]>0])/len(df_demo)*100 if len(df_demo) else 0
                    with cr1: kpi("💰","P&L Réel",   fmt(df_real["pnl"].sum()), f"{len(df_real)} trades","#00d4aa")
                    with cr2: kpi("🧪","P&L Démo",   fmt(df_demo["pnl"].sum()), f"{len(df_demo)} trades","#ff9f43")
                    with cr3: kpi("🎯","Win Rate Réel",f"{wr_r:.1f}%","Compte réel","#00d4aa")
                    with cr4: kpi("🎯","Win Rate Démo",f"{wr_d:.1f}%","Compte démo","#ff9f43")
                    st.markdown(" ")

        col_l,col_r = st.columns([3,2])
        with col_l:
            st.markdown("#### 📊 Courbe de Capital")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_s["date"].tolist(), y=cumul.tolist(), mode="lines+markers",
                line=dict(color="#00d4aa",width=2.5), marker=dict(color="#00d4aa",size=5),
                fill="tozeroy", fillcolor="rgba(0,212,170,0.07)",
                hovertemplate="<b>%{x}</b><br>%{y:+,.2f} $<extra></extra>",
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=240)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown("#### 🎯 Win / Loss")
            fig2 = go.Figure(go.Pie(
                values=[len(wins),len(losses)], labels=["Gagnants","Perdants"], hole=0.62,
                marker=dict(colors=["#00d4aa","#ff4d6d"],line=dict(color="#111520",width=3)),
                hovertemplate="<b>%{label}</b>: %{value} trades<extra></extra>",
            ))
            fig2.add_annotation(text=f"{wr_val:.0f}%",x=0.5,y=0.58,font=dict(size=26,color="#00d4aa",family="JetBrains Mono"),showarrow=False)
            fig2.add_annotation(text="Win Rate",x=0.5,y=0.38,font=dict(size=12,color="#6b7894"),showarrow=False)
            fig2.update_layout(**PLOTLY_LAYOUT,height=240,showlegend=True,
                legend=dict(orientation="h",yanchor="bottom",y=-0.05,font=dict(color="#8892a4")))
            st.plotly_chart(fig2, use_container_width=True)

        col_l2,col_r2 = st.columns(2)
        with col_l2:
            st.markdown("#### 📅 P&L Mensuel")
            fig3 = go.Figure(go.Bar(
                x=monthly["label"].tolist(), y=monthly["pnl"].tolist(),
                marker_color=["#00d4aa" if v>=0 else "#ff4d6d" for v in monthly["pnl"]],
                marker_opacity=0.85, hovertemplate="<b>%{x}</b><br>%{y:+,.2f} $<extra></extra>",
            ))
            fig3.update_layout(**PLOTLY_LAYOUT,height=220); st.plotly_chart(fig3,use_container_width=True)

        with col_r2:
            st.markdown("#### 🎲 P&L par Stratégie")
            bs = df.groupby("strategy")["pnl"].sum().reset_index().sort_values("pnl")
            fig4 = go.Figure(go.Bar(
                y=bs["strategy"].tolist(), x=bs["pnl"].tolist(), orientation="h",
                marker_color=CHART_COLORS[:len(bs)], marker_opacity=0.85,
                hovertemplate="<b>%{y}</b>: %{x:+,.2f} $<extra></extra>",
            ))
            fig4.update_layout(**PLOTLY_LAYOUT,height=220); st.plotly_chart(fig4,use_container_width=True)

        st.markdown("#### 🕐 Derniers Trades")
        recent = df.sort_values("date",ascending=False).head(5)
        rows_html = ""
        for _,t in recent.iterrows():
            c  = "#00d4aa" if t["pnl"]>=0 else "#ff4d6d"
            dc = "b-win" if t["direction"]=="LONG" else "b-loss"
            mc = "b-real" if t.get("trade_mode","Réel 💰")=="Réel 💰" else "b-demo"
            rows_html += f"""<tr>
                <td style="color:#6b7894;font-family:monospace">{t["date"]}</td>
                <td>{badge(t["symbol"],"b-sym")}</td>
                <td>{badge(t["direction"],dc)}</td>
                <td>{badge(t.get("trade_mode","Réel 💰"),mc)}</td>
                <td style="font-family:monospace;font-weight:800;color:{c}">{fmt(t["pnl"])}</td>
                <td style="color:#6b7894;font-size:12px">{str(t.get("notes",""))[:40]}</td>
            </tr>"""
        st.markdown(f"""<table class="tj-table"><thead><tr>
            <th>Date</th><th>Symbole</th><th>Dir.</th><th>Mode</th><th>P&L Réel $</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : JOURNAL
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "journal":
    st.markdown("# 📋 Journal des Trades")
    mode_banner()
    st.divider()

    df = get_df(st.session_state.mode_filter)
    if df.empty:
        st.info("Aucun trade. Ajoutez-en un ou importez depuis MT5.")
    else:
        f1,f2,f3,f4,f5 = st.columns(5)
        with f1: fs  = st.selectbox("Symbole",    ["Tous"]+sorted(df["symbol"].unique().tolist()))
        with f2: fd  = st.selectbox("Direction",  ["Tous","LONG","SHORT"])
        with f3: fst = st.selectbox("Stratégie",  ["Toutes"]+STRATEGIES+["Importé MT5"])
        with f4: fmo = st.selectbox("Mode",       ["Tous","Réel 💰","Démo 🧪"])
        with f5: srt = st.selectbox("Trier par",  ["Date ↓","Date ↑","P&L ↓","P&L ↑"])

        if fs !="Tous":   df=df[df["symbol"]   ==fs]
        if fd !="Tous":   df=df[df["direction"]==fd]
        if fst!="Toutes": df=df[df["strategy"] ==fst]
        if fmo!="Tous":
            if "trade_mode" in df.columns: df=df[df["trade_mode"]==fmo]
        sm={"Date ↓":("date",False),"Date ↑":("date",True),"P&L ↓":("pnl",False),"P&L ↑":("pnl",True)}
        sc,sa=sm[srt]; df=df.sort_values(sc,ascending=sa)

        st.caption(f"{len(df)} trades affichés")
        rows_html=""
        for _,t in df.iterrows():
            c  = "#00d4aa" if t["pnl"]>=0 else "#ff4d6d"
            dc = "b-win" if t["direction"]=="LONG" else "b-loss"
            rr_v=t["rr"]; rr_c="#00d4aa" if (rr_v or 0)>=2 else "#ff9f43" if (rr_v or 0)>=1 else "#ff4d6d"
            mc = "b-real" if t.get("trade_mode","Réel 💰")=="Réel 💰" else "b-demo"
            rows_html+=f"""<tr>
                <td style="color:#6b7894;font-family:monospace;white-space:nowrap">{t["date"]}</td>
                <td>{badge(t["symbol"],"b-sym")}</td>
                <td>{badge(t["direction"],dc)}</td>
                <td>{badge(t.get("trade_mode","Réel 💰"),mc)}</td>
                <td style="font-family:monospace">{t.get("entry","—")}</td>
                <td style="font-family:monospace">{t.get("exit","—")}</td>
                <td style="font-family:monospace;font-weight:800;color:{c};white-space:nowrap">{fmt(t["pnl"])}</td>
                <td style="font-family:monospace;color:{rr_c}">{rr_v if rr_v else "—"}</td>
                <td>{badge(t["strategy"],"b-str")}</td>
                <td title="{t["mood"]}" style="font-size:15px">{MOOD_EMOJI.get(t["mood"],"😐")}</td>
                <td style="color:#6b7894;font-size:12px">{str(t.get("notes",""))[:45]}</td>
            </tr>"""
        st.markdown(f"""<div style="overflow-x:auto"><table class="tj-table"><thead><tr>
            <th>Date</th><th>Symbole</th><th>Dir.</th><th>Mode</th><th>Entrée</th><th>Sortie</th>
            <th>P&L $</th><th>R:R</th><th>Stratégie</th><th>Mood</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table></div>""", unsafe_allow_html=True)

        st.divider()
        st.markdown("##### Modifier / Supprimer")
        df_full = get_df("Tous").sort_values("date",ascending=False)
        labels  = [f"{r['date']}  ·  {r['symbol']}  ·  {r.get('trade_mode','Réel 💰')}  ·  {fmt(r['pnl'])}" for _,r in df_full.iterrows()]
        ids     = df_full["id"].tolist()
        if labels:
            sel_lbl = st.selectbox("Sélectionner",labels,label_visibility="collapsed")
            sel_id  = ids[labels.index(sel_lbl)]
            ce,cd,_ = st.columns([1,1,5])
            with ce:
                if st.button("✏️ Modifier"):
                    st.session_state.edit_id=sel_id; st.session_state.page="add"; st.rerun()
            with cd:
                if st.button("🗑️ Supprimer"):
                    st.session_state.trades=[t for t in st.session_state.trades if t["id"]!=sel_id]
                    ok=cloud_save(st.session_state.trades)
                    st.success("✅ Supprimé." if ok else "⚠️ Erreur sync."); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : ADD / EDIT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "add":
    is_edit = st.session_state.edit_id is not None
    st.markdown(f"# {'✏️ Modifier' if is_edit else '➕ Nouveau Trade'}")
    if st.button("← Retour"):
        st.session_state.page="journal"; st.session_state.edit_id=None; st.rerun()
    st.divider()

    with st.form("form_trade"):
        r1c1,r1c2,r1c3,r1c4 = st.columns(4)
        with r1c1: d_date = st.date_input("Date", value=date.fromisoformat(ev("date",str(date.today()))))
        with r1c2: d_sym  = st.selectbox("Symbole", SYMBOLS, index=SYMBOLS.index(ev("symbol","EUR/USD")) if ev("symbol","EUR/USD") in SYMBOLS else 0)
        with r1c3: d_dir  = st.selectbox("Direction", ["LONG","SHORT"], index=["LONG","SHORT"].index(ev("direction","LONG")))
        with r1c4:
            cur_mode = ev("trade_mode","Réel 💰")
            d_mode = st.selectbox("Mode", TRADE_MODES, index=TRADE_MODES.index(cur_mode) if cur_mode in TRADE_MODES else 0)

        r2c1,r2c2,r2c3,r2c4 = st.columns(4)
        with r2c1: d_entry = st.number_input("Prix d'entrée",  value=float(ev("entry",0.0)), format="%.5f",step=0.0001)
        with r2c2: d_exit  = st.number_input("Prix de sortie", value=float(ev("exit",0.0)),  format="%.5f",step=0.0001)
        with r2c3: d_sl    = st.number_input("Stop Loss",      value=float(ev("sl",0.0)),    format="%.5f",step=0.0001)
        with r2c4: d_tp    = st.number_input("Take Profit",    value=float(ev("tp",0.0)),    format="%.5f",step=0.0001)

        r3c1,r3c2 = st.columns(2)
        with r3c1: d_strat = st.selectbox("Stratégie",    STRATEGIES,index=STRATEGIES.index(ev("strategy","Breakout")))
        with r3c2: d_mood  = st.selectbox("État d'esprit",MOODS,     index=MOODS.index(ev("mood","Confiant")))

        st.markdown("""<div style="background:#0d111d;border:2px solid #00d4aa44;border-radius:12px;
            padding:14px 20px;margin:12px 0 4px">
            <div style="font-size:11px;color:#00d4aa;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;margin-bottom:4px">
                💰 P&L Réel (tel qu'affiché par votre broker)</div>
            <div style="font-size:12px;color:#6b7894">Saisissez le résultat exact · spread, commission et swap inclus</div>
        </div>""", unsafe_allow_html=True)

        pc1,pc2 = st.columns([1,3])
        with pc1:
            d_pnl = st.number_input("P&L ($)", value=float(ev("pnl",0.0)), format="%.2f", step=0.01)
        with pc2:
            if d_pnl != 0:
                color = "#00d4aa" if d_pnl>=0 else "#ff4d6d"
                sign  = "✅ GAIN" if d_pnl>=0 else "❌ PERTE"
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

        if st.form_submit_button("✓  Sauvegarder" if is_edit else "✓  Enregistrer le Trade", use_container_width=True):
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
            st.success("✅ Synchronisé !" if ok else "⚠️ Sauvegardé localement.")
            st.session_state.page="journal"; st.session_state.edit_id=None; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : IMPORT MT5
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "import":
    st.markdown("# 📂 Importer depuis MetaTrader 5")
    if st.button("← Retour"):
        st.session_state.page = "journal"; st.rerun()
    st.divider()

    # ── Choix du mode ────────────────────────────────────────────────────────
    ic1, ic2 = st.columns([2, 3])
    with ic1:
        imp_mode = st.radio("Type de compte", ["Réel 💰", "Démo 🧪"], horizontal=True)
    with ic2:
        mc = "mode-banner-real" if imp_mode == "Réel 💰" else "mode-banner-demo"
        st.markdown(f'<div class="{mc}" style="margin-top:8px">Trades importés étiquetés : {imp_mode}</div>',
                    unsafe_allow_html=True)

    st.markdown("---")

    with st.expander("📖 Comment exporter depuis MT5 ?", expanded=False):
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
            st.error(f"❌ Erreur lecture fichier : {e}")
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
        with st.expander(f"🔍 Colonnes détectées ({len(df_raw.columns)})", expanded=True):
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
                    st.markdown(f"{'✅' if v else '❌'} **{k}** → `{v or 'Non trouvé'}`")
            with d2:
                for k, v in mapping_info[half:]:
                    st.markdown(f"{'✅' if v else '❌'} **{k}** → `{v or 'Non trouvé'}`")
            st.caption(f"Toutes les colonnes : {list(df_raw.columns)}")
            st.dataframe(df_raw.head(3))

        if not col_profit:
            st.error("❌ Colonne Profit introuvable. Vérifiez les colonnes affichées ci-dessus.")
            st.stop()

        if not col_symbol:
            st.error("❌ Colonne Symbol introuvable.")
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
            st.warning("⚠️ Aucun trade fermé détecté. Vérifiez le fichier.")
            st.stop()

        st.success(f"✅ {len(df_closed)} lignes de trades détectées")

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
            st.error("❌ Aucun trade valide extrait. Vérifiez le diagnostic des colonnes.")
            st.stop()

        # ── 6. Résumé + aperçu ────────────────────────────────────────────────
        total_imp = round(sum(t["pnl"] for t in new_trades), 2)
        wins_imp  = [t for t in new_trades if t["pnl"] > 0]
        col_t     = "#00d4aa" if total_imp >= 0 else "#ff4d6d"

        st.markdown(f"### ✅ {len(new_trades)} trades prêts à importer" +
                    (f" · {skipped} ignorés" if skipped else ""))
        s1, s2, s3 = st.columns(3)
        with s1: kpi("💰", "P&L Total",  fmt(total_imp),  "Résultat global",           col_t)
        with s2: kpi("✅", "Gagnants",   str(len(wins_imp)), f"{len(wins_imp)/len(new_trades)*100:.0f}% win", "#00d4aa")
        with s3: kpi("❌", "Perdants",   str(len(new_trades)-len(wins_imp)), "Trades négatifs", "#ff4d6d")
        st.markdown(" ")

        rows_html = ""
        for t in new_trades[:30]:
            c  = "#00d4aa" if t["pnl"] >= 0 else "#ff4d6d"
            dc = "b-win" if t["direction"] == "LONG" else "b-loss"
            mc = "b-real" if t["trade_mode"] == "Réel 💰" else "b-demo"
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
            ["➕ Ajouter aux trades existants", "🔄 Remplacer tous les trades"],
            horizontal=True)

        if st.button("✅  Confirmer l'import", use_container_width=True):
            if "Remplacer" in add_mode:
                st.session_state.trades = new_trades
            else:
                existing_ids = {t["id"] for t in st.session_state.trades}
                st.session_state.trades += [t for t in new_trades if t["id"] not in existing_ids]
            ok = cloud_save(st.session_state.trades)
            st.success(f"✅ {len(new_trades)} trades importés ({imp_mode}) — " +
                       ("synchronisés !" if ok else "erreur sync GitHub."))
            st.session_state.page = "dashboard"
            st.rerun()
