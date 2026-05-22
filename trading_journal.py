import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import json, os, base64, requests

st.set_page_config(page_title="Trading Journal Pro", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
.stApp { background-color: #0a0c12; }
section[data-testid="stSidebar"] > div { background-color: #0c0f1a; border-right: 1px solid #1e2535; }
h1,h2,h3,h4,h5,h6,p,label,.stMarkdown { color: #e8ecf4 !important; }
.stSelectbox label,.stNumberInput label,.stTextInput label,.stTextArea label,.stDateInput label {
    color: #8892a4 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px;
}
.stButton > button { background-color:#00d4aa;color:#000;font-weight:800;border:none;border-radius:10px; }
.stButton > button:hover { background-color:#00b898 !important;color:#000 !important; }
.kpi { background:#111520;border:1px solid #1e2535;border-radius:14px;padding:18px 20px 14px;position:relative;overflow:hidden;min-height:110px; }
.kpi-bar { position:absolute;top:0;left:0;right:0;height:3px; }
.kpi-icon { font-size:18px;margin-bottom:6px; }
.kpi-label { font-size:10px;color:#6b7894;letter-spacing:1.5px;text-transform:uppercase;font-weight:600; }
.kpi-value { font-size:24px;font-weight:800;font-family:'JetBrains Mono',monospace;margin:4px 0 2px; }
.kpi-sub { font-size:11px;color:#6b7894; }
.tj-table { width:100%;border-collapse:collapse;font-size:13px; }
.tj-table th { padding:10px 12px;text-align:left;font-size:10px;color:#6b7894;letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid #1e2535;background:#0d111d;font-weight:600; }
.tj-table td { padding:11px 12px;border-bottom:1px solid rgba(30,37,53,.5);color:#e8ecf4; }
.tj-table tr:hover td { background:#161c2e; }
.badge { padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.8px;display:inline-block; }
.b-win  { color:#00d4aa;background:rgba(0,212,170,.15);border:1px solid rgba(0,212,170,.3); }
.b-loss { color:#ff4d6d;background:rgba(255,77,109,.15);border:1px solid rgba(255,77,109,.3); }
.b-sym  { color:#7c6aff;background:rgba(124,106,255,.15);border:1px solid rgba(124,106,255,.3); }
.b-str  { color:#ff9f43;background:rgba(255,159,67,.15);border:1px solid rgba(255,159,67,.3); }
hr { border-color:#1e2535 !important; }
.pnl-input-box { background:#0d111d;border:1px solid #1e2535;border-radius:12px;padding:16px 20px;margin:10px 0; }
.pnl-input-title { font-size:11px;color:#6b7894;letter-spacing:1.5px;text-transform:uppercase;font-weight:600;margin-bottom:8px; }
.sync-ok { background:#00d4aa18;border:1px solid #00d4aa44;border-radius:8px;padding:6px 14px;font-size:12px;color:#00d4aa; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTES ─────────────────────────────────────────────────────────────────
STRATEGIES   = ["Breakout","Retracement","Support","Tendance","Range","Divergence","Scalping","News"]
MOODS        = ["Euphorique","Confiant","Neutre","Anxieux","Peureux","Frustré"]
SYMBOLS      = ["EUR/USD","GBP/USD","USD/JPY","NAS100","SP500","GOLD","BTC/USD","ETH/USD","OIL","DAX40"]
MOOD_EMOJI   = {"Euphorique":"🚀","Confiant":"😊","Neutre":"😐","Anxieux":"😰","Peureux":"😨","Frustré":"😤"}
CHART_COLORS = ["#00d4aa","#7c6aff","#ff9f43","#ff4d6d","#54a0ff","#5f27cd","#00cec9","#fdcb6e"]
PLOTLY_LAYOUT = dict(
    paper_bgcolor="#111520", plot_bgcolor="#111520",
    font=dict(color="#6b7894", family="DM Sans, sans-serif"),
    margin=dict(l=50, r=20, t=20, b=40),
    xaxis=dict(gridcolor="#1e2535", linecolor="#1e2535"),
    yaxis=dict(gridcolor="#1e2535", linecolor="#1e2535"),
    hovermode="x unified",
)

# ── GITHUB PERSISTENCE ─────────────────────────────────────────────────────────
GH_TOKEN = st.secrets.get("GITHUB_TOKEN", os.environ.get("GITHUB_TOKEN",""))
GH_REPO  = st.secrets.get("GITHUB_REPO",  "SylvainNOFOZO/trading-journal")
GH_FILE  = st.secrets.get("DATA_FILE",    "trades_data.json")
GH_API   = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_FILE}"
GH_HDR   = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def gh_load():
    try:
        r = requests.get(GH_API, headers=GH_HDR, timeout=8)
        r.raise_for_status()
        data    = r.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return json.loads(content), data["sha"]
    except Exception as e:
        st.error(f"Erreur chargement GitHub : {e}")
        return [], None

def gh_save(trades, sha):
    try:
        content = base64.b64encode(json.dumps(trades, ensure_ascii=False, indent=2).encode()).decode()
        body    = {"message": f"Update trades ({len(trades)} total)", "content": content, "sha": sha}
        r       = requests.put(GH_API, headers=GH_HDR, json=body, timeout=10)
        r.raise_for_status()
        return r.json()["content"]["sha"], True
    except Exception as e:
        st.error(f"Erreur sauvegarde GitHub : {e}")
        return sha, False

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if "trades"  not in st.session_state:
    trades, sha = gh_load()
    st.session_state.trades  = trades
    st.session_state.gh_sha  = sha
if "page"    not in st.session_state: st.session_state.page    = "dashboard"
if "edit_id" not in st.session_state: st.session_state.edit_id = None

def cloud_save(trades):
    new_sha, ok = gh_save(trades, st.session_state.gh_sha)
    st.session_state.gh_sha = new_sha
    return ok

def force_reload():
    trades, sha = gh_load()
    st.session_state.trades = trades
    st.session_state.gh_sha = sha

# ── HELPERS ────────────────────────────────────────────────────────────────────
# P&L est maintenant saisi directement par l'utilisateur — plus de calcul automatique
def get_pnl(t):
    """Retourne le P&L tel que saisi par l'utilisateur (réel broker)."""
    return float(t.get("pnl", 0))

def calc_rr(t):
    sl, tp, entry = t.get("sl",0), t.get("tp",0), t.get("entry",0)
    if not sl or not tp or not entry: return None
    risk = abs(entry - sl)
    return round(abs(tp - entry) / risk, 2) if risk else None

def fmt(n):
    if n is None: return "—"
    return f'+${n:,.2f}' if n >= 0 else f'-${abs(n):,.2f}'

def get_df():
    rows = [dict(t, pnl=get_pnl(t), rr=calc_rr(t)) for t in st.session_state.trades]
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def kpi(icon, label, value, sub, color):
    st.markdown(f"""<div class="kpi">
        <div class="kpi-bar" style="background:{color}"></div>
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'

def ev(key, default):
    ex = next((t for t in st.session_state.trades if t["id"] == st.session_state.edit_id), None)
    return ex[key] if ex else default

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Trading Journal")
    st.caption("Pro · v2.0  |  ☁️ GitHub Sync")
    st.divider()

    df_side = get_df()
    total   = df_side["pnl"].sum() if not df_side.empty else 0
    wr      = (len(df_side[df_side["pnl"] > 0]) / len(df_side) * 100) if not df_side.empty else 0
    col_pnl = "#00d4aa" if total >= 0 else "#ff4d6d"

    st.markdown(f"""<div style="margin-bottom:20px;padding:12px 0">
        <div style="font-size:10px;color:#6b7894;letter-spacing:1px;text-transform:uppercase">Capital Net</div>
        <div style="font-size:24px;font-weight:800;color:{col_pnl};font-family:'JetBrains Mono',monospace">{fmt(total)}</div>
        <div style="font-size:12px;color:#6b7894;margin-top:3px">{len(df_side)} trades &nbsp;·&nbsp; {wr:.0f}% win rate</div>
    </div>""", unsafe_allow_html=True)

    if st.button("🏠  Dashboard",     use_container_width=True):
        st.session_state.page="dashboard"; st.session_state.edit_id=None; st.rerun()
    if st.button("📋  Journal",       use_container_width=True):
        st.session_state.page="journal";   st.session_state.edit_id=None; st.rerun()
    if st.button("➕  Nouveau Trade", use_container_width=True):
        st.session_state.page="add";       st.session_state.edit_id=None; st.rerun()
    if st.button("📂  Importer MT5",   use_container_width=True):
        st.session_state.page="import";    st.session_state.edit_id=None; st.rerun()
    if st.button("🔄  Synchroniser",  use_container_width=True):
        force_reload(); st.success("✅ Rechargé depuis GitHub !"); st.rerun()

    st.divider()
    if not df_side.empty:
        csv = df_side.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter CSV", csv, "trades.csv", "text/csv", use_container_width=True)

    sha_display = st.session_state.get("gh_sha","")[:7] if st.session_state.get("gh_sha") else "—"
    st.markdown(f'<div class="sync-ok">☁️ GitHub sync · {sha_display}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "dashboard":
    st.markdown("# Dashboard")
    st.caption(datetime.now().strftime("%A %d %B %Y"))
    st.divider()

    df = get_df()
    if df.empty:
        st.warning("Aucun trade. Cliquez sur **➕ Nouveau Trade** pour commencer.")
    else:
        wins   = df[df["pnl"] > 0]
        losses = df[df["pnl"] <= 0]
        avg_w  = wins["pnl"].mean()   if len(wins)   else 0
        avg_l  = losses["pnl"].mean() if len(losses) else 0
        pf     = round(abs(avg_w / avg_l), 2) if avg_l else None
        rr_df  = df[df["rr"].notna()]
        avg_rr = rr_df["rr"].mean() if len(rr_df) else None
        wr_val = len(wins) / len(df) * 100
        df_s   = df.sort_values("date")
        cumul  = df_s["pnl"].cumsum()
        mdd    = (cumul.cummax() - cumul).max()
        df["month"]  = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
        monthly      = df.groupby("month")["pnl"].sum().reset_index()
        monthly["label"] = monthly["month"].str[5:] + "/" + monthly["month"].str[2:4]

        c1,c2,c3,c4 = st.columns(4)
        with c1: kpi("💰","P&L Net",      fmt(total),       f"{len(df)} trades total",      "#00d4aa" if total>=0 else "#ff4d6d")
        with c2: kpi("🎯","Win Rate",     f"{wr_val:.1f}%", f"{len(wins)}W · {len(losses)}L","#00d4aa" if wr_val>=50 else "#ff4d6d")
        with c3: kpi("⚖️","Profit Factor",f"{pf:.2f}" if pf else "—","Gain / Perte",        "#00d4aa" if (pf or 0)>=1.5 else "#ff9f43")
        with c4: kpi("📉","Max Drawdown", f"${mdd:,.2f}",   "Perte max cumulée",             "#ff4d6d")
        st.markdown(" ")
        c1,c2,c3,c4 = st.columns(4)
        freq = len(df) / max(1, len(monthly))
        with c1: kpi("📈","Gain moyen",   fmt(avg_w),                      "Par trade gagnant",  "#00d4aa")
        with c2: kpi("📉","Perte moyenne",fmt(avg_l),                      "Par trade perdant",  "#ff4d6d")
        with c3: kpi("⚡","R:R Moyen",   f"{avg_rr:.2f}R" if avg_rr else "—","Risque/Récompense","#7c6aff")
        with c4: kpi("📆","Trades/Mois", f"{freq:.1f}",                    "Fréquence moyenne",  "#ff9f43")
        st.markdown(" ")

        col_l, col_r = st.columns([3, 2])
        with col_l:
            st.markdown("#### 📊 Courbe de Capital")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_s["date"].tolist(), y=cumul.tolist(), mode="lines+markers",
                line=dict(color="#00d4aa", width=2.5), marker=dict(color="#00d4aa", size=5),
                fill="tozeroy", fillcolor="rgba(0,212,170,0.07)",
                hovertemplate="<b>%{x}</b><br>%{y:+,.2f} $<extra></extra>",
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=240)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown("#### 🎯 Win / Loss")
            fig2 = go.Figure(go.Pie(
                values=[len(wins), len(losses)], labels=["Gagnants","Perdants"], hole=0.62,
                marker=dict(colors=["#00d4aa","#ff4d6d"], line=dict(color="#111520", width=3)),
                hovertemplate="<b>%{label}</b>: %{value} trades<extra></extra>",
            ))
            fig2.add_annotation(text=f"{wr_val:.0f}%", x=0.5, y=0.58, font=dict(size=26,color="#00d4aa",family="JetBrains Mono"), showarrow=False)
            fig2.add_annotation(text="Win Rate",        x=0.5, y=0.38, font=dict(size=12,color="#6b7894"), showarrow=False)
            fig2.update_layout(**PLOTLY_LAYOUT, height=240, showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.05, font=dict(color="#8892a4")))
            st.plotly_chart(fig2, use_container_width=True)

        col_l2, col_r2 = st.columns(2)
        with col_l2:
            st.markdown("#### 📅 P&L Mensuel")
            fig3 = go.Figure(go.Bar(
                x=monthly["label"].tolist(), y=monthly["pnl"].tolist(),
                marker_color=["#00d4aa" if v>=0 else "#ff4d6d" for v in monthly["pnl"]],
                marker_opacity=0.85, hovertemplate="<b>%{x}</b><br>%{y:+,.2f} $<extra></extra>",
            ))
            fig3.update_layout(**PLOTLY_LAYOUT, height=220)
            st.plotly_chart(fig3, use_container_width=True)

        with col_r2:
            st.markdown("#### 🎲 P&L par Stratégie")
            bs = df.groupby("strategy")["pnl"].sum().reset_index().sort_values("pnl")
            fig4 = go.Figure(go.Bar(
                y=bs["strategy"].tolist(), x=bs["pnl"].tolist(), orientation="h",
                marker_color=CHART_COLORS[:len(bs)], marker_opacity=0.85,
                hovertemplate="<b>%{y}</b>: %{x:+,.2f} $<extra></extra>",
            ))
            fig4.update_layout(**PLOTLY_LAYOUT, height=220)
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown("#### 🕐 Derniers Trades")
        recent    = df.sort_values("date", ascending=False).head(5)
        rows_html = ""
        for _, t in recent.iterrows():
            c  = "#00d4aa" if t["pnl"] >= 0 else "#ff4d6d"
            dc = "b-win" if t["direction"] == "LONG" else "b-loss"
            rows_html += f"""<tr>
                <td style="color:#6b7894;font-family:monospace">{t['date']}</td>
                <td>{badge(t['symbol'],'b-sym')}</td>
                <td>{badge(t['direction'],dc)}</td>
                <td style="font-family:monospace">{t.get('entry','—')}</td>
                <td style="font-family:monospace">{t.get('exit','—')}</td>
                <td style="font-family:monospace;font-weight:800;color:{c}">{fmt(t['pnl'])}</td>
                <td style="color:#6b7894;font-size:12px">{str(t.get('notes',''))[:45]}</td>
            </tr>"""
        st.markdown(f"""<table class="tj-table"><thead><tr>
            <th>Date</th><th>Symbole</th><th>Dir.</th>
            <th>Entrée</th><th>Sortie</th><th>P&L Réel</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : JOURNAL
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "journal":
    st.markdown("# 📋 Journal des Trades")
    st.divider()

    df = get_df()
    if df.empty:
        st.info("Aucun trade. Ajoutez-en un avec **➕ Nouveau Trade**.")
    else:
        f1,f2,f3,f4 = st.columns(4)
        with f1: fs  = st.selectbox("Symbole",   ["Tous"] + sorted(df["symbol"].unique().tolist()))
        with f2: fd  = st.selectbox("Direction", ["Tous","LONG","SHORT"])
        with f3: fst = st.selectbox("Stratégie", ["Toutes"] + STRATEGIES)
        with f4: srt = st.selectbox("Trier par", ["Date ↓","Date ↑","P&L ↓","P&L ↑"])

        if fs  != "Tous":   df = df[df["symbol"]    == fs]
        if fd  != "Tous":   df = df[df["direction"] == fd]
        if fst != "Toutes": df = df[df["strategy"]  == fst]
        sm = {"Date ↓":("date",False),"Date ↑":("date",True),"P&L ↓":("pnl",False),"P&L ↑":("pnl",True)}
        sc, sa = sm[srt]; df = df.sort_values(sc, ascending=sa)

        st.caption(f"{len(df)} trades affichés")
        rows_html = ""
        for _, t in df.iterrows():
            c    = "#00d4aa" if t["pnl"] >= 0 else "#ff4d6d"
            dc   = "b-win" if t["direction"] == "LONG" else "b-loss"
            rr_v = t["rr"]
            rr_c = "#00d4aa" if (rr_v or 0) >= 2 else "#ff9f43" if (rr_v or 0) >= 1 else "#ff4d6d"
            rows_html += f"""<tr>
                <td style="color:#6b7894;font-family:monospace;white-space:nowrap">{t['date']}</td>
                <td>{badge(t['symbol'],'b-sym')}</td>
                <td>{badge(t['direction'],dc)}</td>
                <td style="font-family:monospace">{t.get('entry','—')}</td>
                <td style="font-family:monospace">{t.get('exit','—')}</td>
                <td style="font-family:monospace;font-weight:800;color:{c};white-space:nowrap">{fmt(t['pnl'])}</td>
                <td style="font-family:monospace;color:{rr_c}">{rr_v if rr_v else '—'}</td>
                <td>{badge(t['strategy'],'b-str')}</td>
                <td title="{t['mood']}" style="font-size:16px">{MOOD_EMOJI.get(t['mood'],'😐')}</td>
                <td style="color:#6b7894;font-size:12px;max-width:180px">{str(t.get('notes',''))[:50]}</td>
            </tr>"""
        st.markdown(f"""<div style="overflow-x:auto;margin-top:10px">
        <table class="tj-table"><thead><tr>
            <th>Date</th><th>Symbole</th><th>Dir.</th><th>Entrée</th><th>Sortie</th>
            <th>P&L Réel $</th><th>R:R</th><th>Stratégie</th><th>Mood</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table></div>""", unsafe_allow_html=True)

        st.divider()
        st.markdown("##### Modifier / Supprimer")
        df_full = get_df().sort_values("date", ascending=False)
        labels  = [f"{r['date']}  ·  {r['symbol']}  ·  {fmt(r['pnl'])}" for _, r in df_full.iterrows()]
        ids     = df_full["id"].tolist()
        if labels:
            sel_lbl = st.selectbox("Sélectionner", labels, label_visibility="collapsed")
            sel_id  = ids[labels.index(sel_lbl)]
            ce, cd, _ = st.columns([1, 1, 5])
            with ce:
                if st.button("✏️ Modifier"):
                    st.session_state.edit_id = sel_id; st.session_state.page = "add"; st.rerun()
            with cd:
                if st.button("🗑️ Supprimer"):
                    st.session_state.trades = [t for t in st.session_state.trades if t["id"] != sel_id]
                    ok = cloud_save(st.session_state.trades)
                    st.success("✅ Supprimé et synchronisé." if ok else "⚠️ Supprimé (erreur sync).")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : ADD / EDIT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "add":
    is_edit = st.session_state.edit_id is not None
    st.markdown(f"# {'✏️ Modifier' if is_edit else '➕ Nouveau Trade'}")
    if st.button("← Retour"):
        st.session_state.page = "journal"; st.session_state.edit_id = None; st.rerun()
    st.divider()

    with st.form("form_trade"):

        # ── Ligne 1 : date, symbole, direction ──
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1: d_date = st.date_input("Date", value=date.fromisoformat(ev("date", str(date.today()))))
        with r1c2: d_sym  = st.selectbox("Symbole",   SYMBOLS,          index=SYMBOLS.index(ev("symbol","EUR/USD")))
        with r1c3: d_dir  = st.selectbox("Direction", ["LONG","SHORT"],  index=["LONG","SHORT"].index(ev("direction","LONG")))

        # ── Ligne 2 : entrée, sortie (optionnels, pour info) ──
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1: d_entry = st.number_input("Prix d'entrée",  value=float(ev("entry",0.0)), format="%.5f", step=0.0001)
        with r2c2: d_exit  = st.number_input("Prix de sortie", value=float(ev("exit",0.0)),  format="%.5f", step=0.0001)
        with r2c3: d_sl    = st.number_input("Stop Loss",      value=float(ev("sl",0.0)),    format="%.5f", step=0.0001)
        with r2c4: d_tp    = st.number_input("Take Profit",    value=float(ev("tp",0.0)),    format="%.5f", step=0.0001)

        # ── Ligne 3 : stratégie, mood ──
        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        with r3c1: d_strat = st.selectbox("Stratégie",    STRATEGIES, index=STRATEGIES.index(ev("strategy","Breakout")))
        with r3c2: d_mood  = st.selectbox("État d'esprit",MOODS,      index=MOODS.index(ev("mood","Confiant")))
        with r3c3: pass
        with r3c4: pass

        # ── P&L RÉEL — champ principal ──────────────────────────────────────
        st.markdown("""
        <div style="background:#0d111d;border:2px solid #00d4aa44;border-radius:12px;padding:16px 20px;margin:14px 0 4px">
            <div style="font-size:11px;color:#00d4aa;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;margin-bottom:4px">
                💰 P&L Réel (tel qu'affiché par votre broker)
            </div>
            <div style="font-size:12px;color:#6b7894;margin-bottom:10px">
                Saisissez le profit ou la perte exacte · spread, commission et swap déjà inclus · positif = gain · négatif = perte
            </div>
        </div>
        """, unsafe_allow_html=True)

        pnl_col1, pnl_col2 = st.columns([1, 3])
        with pnl_col1:
            d_pnl = st.number_input(
                "P&L ($)",
                value=float(ev("pnl", 0.0)),
                format="%.2f",
                step=0.01,
                help="Copiez exactement le montant affiché par votre broker (ex: +45.30 ou -22.50)"
            )
        with pnl_col2:
            if d_pnl != 0:
                color = "#00d4aa" if d_pnl >= 0 else "#ff4d6d"
                sign  = "✅ GAIN" if d_pnl >= 0 else "❌ PERTE"
                # Calcul R:R si SL et TP renseignés
                rr_preview = ""
                if d_entry and d_sl and d_tp:
                    risk = abs(d_entry - d_sl)
                    if risk:
                        rr_val = round(abs(d_tp - d_entry) / risk, 2)
                        rr_preview = f"&nbsp;&nbsp;·&nbsp;&nbsp;<span style='color:#7c6aff'>R:R {rr_val}</span>"
                st.markdown(f"""
                <div style="margin-top:28px;font-size:26px;font-weight:800;
                    font-family:'JetBrains Mono',monospace;color:{color}">
                    {sign} &nbsp; {fmt(d_pnl)}{rr_preview}
                </div>""", unsafe_allow_html=True)

        d_notes = st.text_area("Notes & Analyse", value=ev("notes",""),
                               placeholder="Raison du trade, contexte de marché, leçons apprises...", height=90)

        submitted = st.form_submit_button(
            "✓  Sauvegarder" if is_edit else "✓  Enregistrer le Trade",
            use_container_width=True
        )

        if submitted:
            ex    = next((t for t in st.session_state.trades if t["id"] == st.session_state.edit_id), None)
            new_t = {
                "id":        ex["id"] if is_edit else int(datetime.now().timestamp() * 1000),
                "date":      str(d_date),
                "symbol":    d_sym,
                "direction": d_dir,
                "entry":     d_entry,
                "exit":      d_exit,
                "sl":        d_sl,
                "tp":        d_tp,
                "pnl":       d_pnl,          # ← P&L réel broker
                "strategy":  d_strat,
                "mood":      d_mood,
                "notes":     d_notes,
            }
            if is_edit:
                st.session_state.trades = [new_t if t["id"] == ex["id"] else t for t in st.session_state.trades]
            else:
                st.session_state.trades.append(new_t)

            ok = cloud_save(st.session_state.trades)
            if ok:
                st.success("✅ Trade sauvegardé et synchronisé sur GitHub !")
            else:
                st.warning("⚠️ Sauvegardé localement mais erreur de synchronisation.")

            st.session_state.page = "journal"; st.session_state.edit_id = None; st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : IMPORT MT5
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# PAGE : IMPORT MT5
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "import":
    import io
    st.markdown("# 📂 Importer depuis MetaTrader 5")
    if st.button("← Retour"):
        st.session_state.page = "journal"; st.rerun()
    st.divider()

    with st.expander("📖 Comment exporter depuis MT5 ?", expanded=False):
        st.markdown("""
        1. Ouvrez **MetaTrader 5**
        2. Allez dans **Affichage → Historique des transactions** (ou onglet *History*)
        3. Clic droit dans le tableau → **Enregistrer sous** → choisir **CSV**
        4. Uploadez ce fichier ci-dessous
        
        > ✅ Les colonnes détectées automatiquement : Time, Symbol, Type, Direction, Price, Commission, Swap, Profit
        """)

    uploaded = st.file_uploader("Choisir le fichier CSV MT5", type=["csv","txt"], label_visibility="collapsed")

    if uploaded:
        raw = uploaded.read().decode("utf-8", errors="replace")
        sep = "	" if raw.count("	") > raw.count(",") else ","

        try:
            df_raw = pd.read_csv(io.StringIO(raw), sep=sep, header=None, dtype=str)
        except Exception as e:
            st.error(f"Erreur lecture CSV : {e}")
            st.stop()

        # Trouver la ligne d en-tete
        header_row = 0
        for i, row in df_raw.iterrows():
            vals = [str(v).strip().lower() for v in row.values]
            if any(k in vals for k in ["symbol","time","deal","profit","type"]):
                header_row = i
                break

        try:
            df_raw = pd.read_csv(io.StringIO(raw), sep=sep, skiprows=header_row, dtype=str)
        except Exception as e:
            st.error(f"Erreur parsing : {e}")
            st.stop()

        df_raw.columns = [str(c).strip().lower().replace(" ","_") for c in df_raw.columns]

        with st.expander(f"Colonnes détectées ({len(df_raw.columns)})", expanded=False):
            st.write(list(df_raw.columns))
            st.dataframe(df_raw.head(5))

        def find_col(df, candidates):
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        col_time   = find_col(df_raw, ["time","open_time","date","timestamp"])
        col_symbol = find_col(df_raw, ["symbol","asset","instrument","pair"])
        col_type   = find_col(df_raw, ["type","action","operation","order_type"])
        col_dir    = find_col(df_raw, ["direction","in/out","entry","in_out"])
        col_price  = find_col(df_raw, ["price","open_price","entry_price"])
        col_profit = find_col(df_raw, ["profit","p&l","result","net_profit"])
        col_comm   = find_col(df_raw, ["commission","comm","fee"])
        col_swap   = find_col(df_raw, ["swap","rollover"])
        col_sl     = find_col(df_raw, ["s/l","sl","stop_loss","stoploss"])
        col_tp     = find_col(df_raw, ["t/p","tp","take_profit","takeprofit"])

        if not col_profit:
            st.error("❌ Colonne Profit introuvable. Colonnes disponibles : " + str(list(df_raw.columns)))
            st.stop()

        # Filtrer les trades fermes
        df_work = df_raw.copy()

        # Supprimer lignes balance/depot
        if col_type:
            df_work = df_work[~df_work[col_type].str.lower().str.contains(
                "balance|deposit|withdrawal|credit|bonus", na=False)]

        # Garder uniquement direction OUT si disponible
        if col_dir:
            mask_out = df_work[col_dir].str.lower().str.contains("out|close|exit|sell", na=False)
            df_closed = df_work[mask_out].copy()
            if df_closed.empty:
                df_closed = df_work.copy()
        else:
            # Garder lignes avec profit non nul
            def has_value(x):
                try:
                    return float(str(x).replace(" ","")) != 0
                except:
                    return False
            df_closed = df_work[df_work[col_profit].apply(has_value)].copy()

        if df_closed.empty:
            st.warning("Aucun trade fermé détecté. Vérifiez le format.")
            st.stop()

        SYM_MAP = {
            "EURUSD":"EUR/USD","GBPUSD":"GBP/USD","USDJPY":"USD/JPY","USDCHF":"USD/CHF",
            "AUDUSD":"AUD/USD","NZDUSD":"NZD/USD","USDCAD":"USD/CAD","EURGBP":"EUR/GBP",
            "EURJPY":"EUR/JPY","GBPJPY":"GBP/JPY","EURCAD":"EUR/CAD","AUDCAD":"AUD/CAD",
            "XAUUSD":"GOLD","XAGUSD":"SILVER","BTCUSD":"BTC/USD","ETHUSD":"ETH/USD",
            "US30":"DOW30","US500":"SP500","SP500":"SP500","USTEC":"NAS100",
            "NAS100":"NAS100","UK100":"FTSE100","GER40":"DAX40","FRA40":"CAC40",
            "USOIL":"OIL","UKOIL":"OIL","WTI":"OIL",
        }

        new_trades = []
        skipped    = 0

        for _, row in df_closed.iterrows():
            try:
                def safe_float(col):
                    if not col: return 0.0
                    try:
                        return float(str(row.get(col,"0")).replace(" ","").replace(",",".") or 0)
                    except:
                        return 0.0

                # Date
                raw_date = str(row[col_time]).strip() if col_time else str(date.today())
                try:
                    parsed_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
                except:
                    parsed_date = str(date.today())

                # Symbol
                symbol_raw = str(row[col_symbol]).strip().upper() if col_symbol else "UNKNOWN"
                symbol = SYM_MAP.get(symbol_raw, symbol_raw)

                # Direction
                direction = "LONG"
                if col_type:
                    t_val = str(row[col_type]).strip().lower()
                    if any(k in t_val for k in ["sell","short","s","vente"]):
                        direction = "SHORT"
                elif col_dir:
                    d_val = str(row[col_dir]).strip().lower()
                    if any(k in d_val for k in ["sell","short","out","close"]):
                        direction = "SHORT"

                # P&L reel = profit + commission + swap
                profit = safe_float(col_profit)
                comm   = safe_float(col_comm)
                swap   = safe_float(col_swap)
                pnl_reel = round(profit + comm + swap, 2)

                entry_price = safe_float(col_price)
                sl_val      = safe_float(col_sl)
                tp_val      = safe_float(col_tp)

                notes_parts = []
                if comm: notes_parts.append(f"comm:{comm:.2f}")
                if swap: notes_parts.append(f"swap:{swap:.2f}")
                notes_str = "Import MT5" + (" · " + " · ".join(notes_parts) if notes_parts else "")

                new_trades.append({
                    "id":        int(datetime.now().timestamp()*1000*1000) + len(new_trades),
                    "date":      parsed_date,
                    "symbol":    symbol,
                    "direction": direction,
                    "entry":     entry_price,
                    "exit":      0.0,
                    "sl":        sl_val,
                    "tp":        tp_val,
                    "pnl":       pnl_reel,
                    "strategy":  "Importé MT5",
                    "mood":      "Neutre",
                    "notes":     notes_str,
                })
            except Exception:
                skipped += 1

        if not new_trades:
            st.error("Aucun trade valide extrait du fichier.")
            st.stop()

        total_import = round(sum(t["pnl"] for t in new_trades), 2)
        wins_import  = [t for t in new_trades if t["pnl"] > 0]
        col_t = "#00d4aa" if total_import >= 0 else "#ff4d6d"

        st.markdown(f"### ✅ {len(new_trades)} trades prêts à importer" + (f" · {skipped} ignorés" if skipped else ""))
        c1, c2, c3 = st.columns(3)
        with c1: kpi("💰","P&L Total Import", fmt(total_import), "Tous trades confondus", col_t)
        with c2: kpi("✅","Gagnants",  str(len(wins_import)),  f"{len(wins_import)/len(new_trades)*100:.0f}% win rate","#00d4aa")
        with c3: kpi("❌","Perdants",  str(len(new_trades)-len(wins_import)), "Trades négatifs","#ff4d6d")
        st.markdown(" ")

        # Aperçu tableau
        rows_html = ""
        preview_list = new_trades[:20]
        for t in preview_list:
            c  = "#00d4aa" if t["pnl"] >= 0 else "#ff4d6d"
            dc = "b-win" if t["direction"] == "LONG" else "b-loss"
            rows_html += f"""<tr>
                <td style='color:#6b7894;font-family:monospace'>{t["date"]}</td>
                <td><span class='badge b-sym'>{t["symbol"]}</span></td>
                <td><span class='badge {dc}'>{t["direction"]}</span></td>
                <td style='font-family:monospace'>{t["entry"] if t["entry"] else "—"}</td>
                <td style='font-family:monospace;font-weight:800;color:{c}'>{fmt(t["pnl"])}</td>
                <td style='color:#6b7894;font-size:11px'>{t["notes"]}</td>
            </tr>"""
        if len(new_trades) > 20:
            rows_html += f"<tr><td colspan='6' style='color:#6b7894;text-align:center;padding:12px'>... et {len(new_trades)-20} autres</td></tr>"

        st.markdown(f"""<div style="overflow-x:auto">
        <table class="tj-table"><thead><tr>
            <th>Date</th><th>Symbole</th><th>Dir.</th><th>Entrée</th><th>P&L Réel $</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table></div>""", unsafe_allow_html=True)

        st.markdown("---")
        mode = st.radio(
            "Mode d'import",
            ["➕ Ajouter aux trades existants", "🔄 Remplacer tous les trades"],
            horizontal=True
        )

        if st.button("✅  Confirmer l'import", use_container_width=True):
            if "Remplacer" in mode:
                st.session_state.trades = new_trades
            else:
                existing_ids = {t["id"] for t in st.session_state.trades}
                to_add = [t for t in new_trades if t["id"] not in existing_ids]
                st.session_state.trades += to_add

            ok = cloud_save(st.session_state.trades)
            msg = f"✅ {len(new_trades)} trades importés et synchronisés sur GitHub !"
            if not ok:
                msg = f"⚠️ {len(new_trades)} trades importés localement (erreur sync GitHub)."
            st.success(msg)
            st.session_state.page = "dashboard"
            st.rerun()
