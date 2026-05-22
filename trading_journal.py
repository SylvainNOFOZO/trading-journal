import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Trading Journal Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS (ciblé, ne casse pas Streamlit) ───────────────────────────────────────
st.markdown("""
<style>
/* Fonts */
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

/* Fond général */
.stApp { background-color: #0a0c12; }
section[data-testid="stSidebar"] > div { background-color: #0c0f1a; border-right: 1px solid #1e2535; }

/* Textes */
h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #e8ecf4 !important; }
.stSelectbox label, .stNumberInput label, .stTextInput label,
.stTextArea label, .stDateInput label {
    color: #8892a4 !important; font-size: 11px !important;
    text-transform: uppercase; letter-spacing: 1px;
}

/* Inputs */
input, textarea, select,
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] [data-testid="stSelectbox"] {
    background-color: #0d111d !important;
    border-color: #1e2535 !important;
    color: #e8ecf4 !important;
}

/* Boutons */
.stButton > button {
    background-color: #00d4aa;
    color: #000;
    font-weight: 800;
    border: none;
    border-radius: 10px;
}
.stButton > button:hover {
    background-color: #00b898 !important;
    color: #000 !important;
}

/* Bouton secondaire */
.btn-sec > button {
    background-color: #1e2535 !important;
    color: #e8ecf4 !important;
}

/* KPI card */
.kpi {
    background: #111520;
    border: 1px solid #1e2535;
    border-radius: 14px;
    padding: 18px 20px 14px;
    position: relative;
    overflow: hidden;
    min-height: 110px;
}
.kpi-bar { position:absolute;top:0;left:0;right:0;height:3px; }
.kpi-icon { font-size:18px;margin-bottom:6px; }
.kpi-label { font-size:10px;color:#6b7894;letter-spacing:1.5px;text-transform:uppercase;font-weight:600; }
.kpi-value { font-size:24px;font-weight:800;font-family:'JetBrains Mono',monospace;margin:4px 0 2px; }
.kpi-sub { font-size:11px;color:#6b7894; }

/* Table */
.tj-table { width:100%;border-collapse:collapse;font-size:13px; }
.tj-table th { padding:10px 12px;text-align:left;font-size:10px;color:#6b7894;
    letter-spacing:1px;text-transform:uppercase;border-bottom:1px solid #1e2535;
    background:#0d111d;font-weight:600; }
.tj-table td { padding:11px 12px;border-bottom:1px solid rgba(30,37,53,.5);color:#e8ecf4; }
.tj-table tr:hover td { background:#161c2e; }

/* Badges */
.badge { padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.8px;display:inline-block; }
.b-win  { color:#00d4aa;background:rgba(0,212,170,.15);border:1px solid rgba(0,212,170,.3); }
.b-loss { color:#ff4d6d;background:rgba(255,77,109,.15);border:1px solid rgba(255,77,109,.3); }
.b-sym  { color:#7c6aff;background:rgba(124,106,255,.15);border:1px solid rgba(124,106,255,.3); }
.b-str  { color:#ff9f43;background:rgba(255,159,67,.15);border:1px solid rgba(255,159,67,.3); }

/* Divider */
hr { border-color: #1e2535 !important; }

/* Preview block */
.preview {
    background:#0d111d;border:1px solid #1e2535;border-radius:12px;
    padding:14px 20px;display:flex;gap:40px;align-items:center;margin:12px 0;
}
.preview-label { font-size:10px;color:#6b7894;letter-spacing:1px;text-transform:uppercase; }
.preview-value { font-size:22px;font-weight:800;font-family:'JetBrains Mono',monospace;margin-top:2px; }
</style>
""", unsafe_allow_html=True)

# ── DONNÉES PAR DÉFAUT ────────────────────────────────────────────────────────
INIT_TRADES = [
    {"id":1,"date":"2026-04-01","symbol":"EUR/USD","direction":"LONG","entry":1.082,"exit":1.0891,"qty":10000,"fees":8,"sl":1.078,"tp":1.09,"strategy":"Breakout","mood":"Confiant","notes":"Break de résistance claire"},
    {"id":2,"date":"2026-04-03","symbol":"GBP/USD","direction":"SHORT","entry":1.264,"exit":1.259,"qty":5000,"fees":6,"sl":1.268,"tp":1.256,"strategy":"Retracement","mood":"Neutre","notes":"Rejet sur EMA 50"},
    {"id":3,"date":"2026-04-07","symbol":"NAS100","direction":"LONG","entry":17420,"exit":17310,"qty":1,"fees":12,"sl":17350,"tp":17550,"strategy":"Support","mood":"Anxieux","notes":"Stop touché"},
    {"id":4,"date":"2026-04-10","symbol":"GOLD","direction":"LONG","entry":2315,"exit":2380,"qty":5,"fees":15,"sl":2280,"tp":2400,"strategy":"Tendance","mood":"Confiant","notes":"Momentum fort"},
    {"id":5,"date":"2026-04-14","symbol":"EUR/USD","direction":"SHORT","entry":1.096,"exit":1.091,"qty":10000,"fees":8,"sl":1.099,"tp":1.088,"strategy":"Range","mood":"Neutre","notes":"Vente résistance"},
    {"id":6,"date":"2026-04-18","symbol":"BTC/USD","direction":"LONG","entry":64200,"exit":67500,"qty":0.5,"fees":22,"sl":62000,"tp":68000,"strategy":"Breakout","mood":"Euphorique","notes":"ATH proche"},
    {"id":7,"date":"2026-04-22","symbol":"SP500","direction":"SHORT","entry":5280,"exit":5340,"qty":1,"fees":10,"sl":5310,"tp":5200,"strategy":"Retracement","mood":"Peureux","notes":"Stop déclenché"},
    {"id":8,"date":"2026-04-28","symbol":"GOLD","direction":"SHORT","entry":2410,"exit":2370,"qty":3,"fees":12,"sl":2430,"tp":2360,"strategy":"Divergence","mood":"Confiant","notes":"RSI divergence"},
    {"id":9,"date":"2026-05-05","symbol":"EUR/USD","direction":"LONG","entry":1.088,"exit":1.094,"qty":15000,"fees":10,"sl":1.084,"tp":1.097,"strategy":"Tendance","mood":"Confiant","notes":"Continuation haussière"},
    {"id":10,"date":"2026-05-12","symbol":"NAS100","direction":"LONG","entry":18200,"exit":18650,"qty":1,"fees":14,"sl":18000,"tp":18800,"strategy":"Breakout","mood":"Euphorique","notes":"Earnings boost"},
]

STRATEGIES = ["Breakout","Retracement","Support","Tendance","Range","Divergence","Scalping","News"]
MOODS      = ["Euphorique","Confiant","Neutre","Anxieux","Peureux","Frustré"]
SYMBOLS    = ["EUR/USD","GBP/USD","USD/JPY","NAS100","SP500","GOLD","BTC/USD","ETH/USD","OIL","DAX40"]
MOOD_EMOJI = {"Euphorique":"🚀","Confiant":"😊","Neutre":"😐","Anxieux":"😰","Peureux":"😨","Frustré":"😤"}
CHART_COLORS = ["#00d4aa","#7c6aff","#ff9f43","#ff4d6d","#54a0ff","#5f27cd","#00cec9","#fdcb6e"]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#111520", plot_bgcolor="#111520",
    font=dict(color="#6b7894", family="DM Sans, sans-serif"),
    margin=dict(l=50, r=20, t=20, b=40),
    xaxis=dict(gridcolor="#1e2535", linecolor="#1e2535"),
    yaxis=dict(gridcolor="#1e2535", linecolor="#1e2535"),
    hovermode="x unified",
)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
if "trades" not in st.session_state:
    st.session_state.trades = []
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None

# ── FONCTIONS UTILITAIRES ─────────────────────────────────────────────────────
def calc_pnl(t):
    raw = (t["exit"] - t["entry"]) * t["qty"] if t["direction"] == "LONG" \
          else (t["entry"] - t["exit"]) * t["qty"]
    return round(raw - t.get("fees", 0), 2)

def calc_rr(t):
    sl, tp, entry = t.get("sl", 0), t.get("tp", 0), t["entry"]
    if not sl or not tp:
        return None
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    return round(reward / risk, 2) if risk else None

def fmt_pnl(n):
    if n is None: return "—"
    return f'+${n:,.0f}' if n >= 0 else f'-${abs(n):,.0f}'

def get_df():
    rows = [dict(t, pnl=calc_pnl(t), rr=calc_rr(t)) for t in st.session_state.trades]
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def kpi_card(icon, label, value, sub, color):
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-bar" style="background:{color}"></div>
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Trading Journal")
    st.caption("Pro · v2.0")
    st.divider()

    df_side = get_df()
    total   = df_side["pnl"].sum() if not df_side.empty else 0
    wr      = (len(df_side[df_side["pnl"] > 0]) / len(df_side) * 100) if not df_side.empty else 0
    col_pnl = "#00d4aa" if total >= 0 else "#ff4d6d"

    st.markdown(f"""
    <div style="margin-bottom:20px;padding:12px 0">
        <div style="font-size:10px;color:#6b7894;letter-spacing:1px;text-transform:uppercase">Capital Net</div>
        <div style="font-size:24px;font-weight:800;color:{col_pnl};font-family:'JetBrains Mono',monospace">{fmt_pnl(total)}</div>
        <div style="font-size:12px;color:#6b7894;margin-top:3px">{len(df_side)} trades &nbsp;·&nbsp; {wr:.0f}% win rate</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🏠  Dashboard",      use_container_width=True):
        st.session_state.page = "dashboard"; st.session_state.edit_id = None; st.rerun()
    if st.button("📋  Journal",        use_container_width=True):
        st.session_state.page = "journal";   st.session_state.edit_id = None; st.rerun()
    if st.button("➕  Nouveau Trade",  use_container_width=True):
        st.session_state.page = "add";       st.session_state.edit_id = None; st.rerun()

    st.divider()
    if not df_side.empty:
        csv = df_side.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter CSV", csv, "trades.csv", "text/csv", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "dashboard":
    st.markdown("# Dashboard")
    st.caption(datetime.now().strftime("%A %d %B %Y"))
    st.divider()

    df = get_df()

    if df.empty:
        st.warning("Aucun trade enregistré. Cliquez sur **➕ Nouveau Trade** pour commencer.")
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

        df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
        monthly = df.groupby("month")["pnl"].sum().reset_index()
        monthly["label"] = monthly["month"].str[5:] + "/" + monthly["month"].str[2:4]

        # ── KPIs row 1 ──
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("💰","P&L Net",      fmt_pnl(total),        f"{len(df)} trades total",    "#00d4aa" if total>=0 else "#ff4d6d")
        with c2: kpi_card("🎯","Win Rate",     f"{wr_val:.1f}%",      f"{len(wins)}W · {len(losses)}L", "#00d4aa" if wr_val>=50 else "#ff4d6d")
        with c3: kpi_card("⚖️","Profit Factor",f"{pf:.2f}" if pf else "—", "Gain / Perte",          "#00d4aa" if (pf or 0)>=1.5 else "#ff9f43")
        with c4: kpi_card("📉","Max Drawdown", f"${mdd:,.0f}",        "Perte max cumulée",           "#ff4d6d")

        st.markdown(" ")

        # ── KPIs row 2 ──
        c1, c2, c3, c4 = st.columns(4)
        freq = len(df) / max(1, len(monthly))
        with c1: kpi_card("📈","Gain moyen",   fmt_pnl(avg_w),        "Par trade gagnant",  "#00d4aa")
        with c2: kpi_card("📉","Perte moyenne",fmt_pnl(avg_l),        "Par trade perdant",  "#ff4d6d")
        with c3: kpi_card("⚡","R:R Moyen",   f"{avg_rr:.2f}R" if avg_rr else "—","Risque/Récompense","#7c6aff")
        with c4: kpi_card("📆","Trades/Mois", f"{freq:.1f}",          "Fréquence moyenne",  "#ff9f43")

        st.markdown(" ")

        # ── Equity curve + Donut ──
        col_l, col_r = st.columns([3, 2])

        with col_l:
            st.markdown("#### 📊 Courbe de Capital")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_s["date"].tolist(), y=cumul.tolist(),
                mode="lines+markers",
                line=dict(color="#00d4aa", width=2.5),
                marker=dict(color="#00d4aa", size=5),
                fill="tozeroy", fillcolor="rgba(0,212,170,0.07)",
                hovertemplate="<b>%{x}</b><br>%{y:+,.0f} $<extra></extra>",
            ))
            fig.update_layout(**PLOTLY_LAYOUT, height=240)
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.markdown("#### 🎯 Win / Loss")
            fig2 = go.Figure(go.Pie(
                values=[len(wins), len(losses)],
                labels=["Gagnants","Perdants"],
                hole=0.62,
                marker=dict(colors=["#00d4aa","#ff4d6d"], line=dict(color="#111520", width=3)),
                hovertemplate="<b>%{label}</b>: %{value} trades<extra></extra>",
            ))
            fig2.add_annotation(
                text=f"{wr_val:.0f}%", x=0.5, y=0.58,
                font=dict(size=26, color="#00d4aa", family="JetBrains Mono"), showarrow=False
            )
            fig2.add_annotation(
                text="Win Rate", x=0.5, y=0.38,
                font=dict(size=12, color="#6b7894"), showarrow=False
            )
            fig2.update_layout(**PLOTLY_LAYOUT, height=240, showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.05, font=dict(color="#8892a4")))
            st.plotly_chart(fig2, use_container_width=True)

        # ── Monthly + Stratégie ──
        col_l2, col_r2 = st.columns(2)

        with col_l2:
            st.markdown("#### 📅 P&L Mensuel")
            fig3 = go.Figure(go.Bar(
                x=monthly["label"].tolist(),
                y=monthly["pnl"].tolist(),
                marker_color=["#00d4aa" if v >= 0 else "#ff4d6d" for v in monthly["pnl"]],
                marker_opacity=0.85,
                hovertemplate="<b>%{x}</b><br>%{y:+,.0f} $<extra></extra>",
            ))
            fig3.update_layout(**PLOTLY_LAYOUT, height=220)
            st.plotly_chart(fig3, use_container_width=True)

        with col_r2:
            st.markdown("#### 🎲 P&L par Stratégie")
            bs = df.groupby("strategy")["pnl"].sum().reset_index().sort_values("pnl")
            fig4 = go.Figure(go.Bar(
                y=bs["strategy"].tolist(),
                x=bs["pnl"].tolist(),
                orientation="h",
                marker_color=CHART_COLORS[:len(bs)],
                marker_opacity=0.85,
                hovertemplate="<b>%{y}</b>: %{x:+,.0f} $<extra></extra>",
            ))
            fig4.update_layout(**PLOTLY_LAYOUT, height=220)
            st.plotly_chart(fig4, use_container_width=True)

        # ── Derniers trades ──
        st.markdown("#### 🕐 Derniers Trades")
        recent = df.sort_values("date", ascending=False).head(5)
        rows_html = ""
        for _, t in recent.iterrows():
            c = "#00d4aa" if t["pnl"] >= 0 else "#ff4d6d"
            dc = "b-win" if t["direction"] == "LONG" else "b-loss"
            rows_html += f"""<tr>
                <td style="color:#6b7894;font-family:monospace">{t['date']}</td>
                <td>{badge(t['symbol'],'b-sym')}</td>
                <td>{badge(t['direction'],dc)}</td>
                <td style="font-family:monospace">{t['entry']}</td>
                <td style="font-family:monospace">{t['exit']}</td>
                <td style="font-family:monospace;font-weight:800;color:{c}">{fmt_pnl(t['pnl'])}</td>
                <td style="color:#6b7894;font-size:12px">{t['notes'][:40]}{'...' if len(str(t['notes']))>40 else ''}</td>
            </tr>"""
        st.markdown(f"""
        <table class="tj-table">
            <thead><tr>
                <th>Date</th><th>Symbole</th><th>Dir.</th>
                <th>Entrée</th><th>Sortie</th><th>P&L</th><th>Notes</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

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
        # Filtres
        f1, f2, f3, f4 = st.columns(4)
        with f1: fs  = st.selectbox("Symbole",    ["Tous"] + sorted(df["symbol"].unique().tolist()))
        with f2: fd  = st.selectbox("Direction",  ["Tous","LONG","SHORT"])
        with f3: fst = st.selectbox("Stratégie",  ["Toutes"] + STRATEGIES)
        with f4: srt = st.selectbox("Trier par",  ["Date ↓","Date ↑","P&L ↓","P&L ↑"])

        if fs  != "Tous":   df = df[df["symbol"]    == fs]
        if fd  != "Tous":   df = df[df["direction"] == fd]
        if fst != "Toutes": df = df[df["strategy"]  == fst]

        sm = {"Date ↓":("date",False),"Date ↑":("date",True),"P&L ↓":("pnl",False),"P&L ↑":("pnl",True)}
        sc, sa = sm[srt]
        df = df.sort_values(sc, ascending=sa)

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
                <td style="font-family:monospace">{t['entry']}</td>
                <td style="font-family:monospace">{t['exit']}</td>
                <td style="font-family:monospace">{t['qty']}</td>
                <td style="font-family:monospace;font-weight:800;color:{c};white-space:nowrap">{fmt_pnl(t['pnl'])}</td>
                <td style="font-family:monospace;color:{rr_c}">{rr_v if rr_v else '—'}</td>
                <td>{badge(t['strategy'],'b-str')}</td>
                <td title="{t['mood']}" style="font-size:16px">{MOOD_EMOJI.get(t['mood'],'😐')}</td>
                <td style="color:#6b7894;font-size:12px;max-width:180px">{str(t['notes'])[:50]}</td>
            </tr>"""

        st.markdown(f"""
        <div style="overflow-x:auto;margin-top:10px">
        <table class="tj-table">
            <thead><tr>
                <th>Date</th><th>Symbole</th><th>Dir.</th><th>Entrée</th><th>Sortie</th>
                <th>Qté</th><th>P&L</th><th>R:R</th><th>Stratégie</th><th>Mood</th><th>Notes</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.markdown("##### Modifier / Supprimer un trade")
        df_full = get_df().sort_values("date", ascending=False)
        labels  = [f"{r['date']}  ·  {r['symbol']}  ·  {fmt_pnl(r['pnl'])}" for _, r in df_full.iterrows()]
        ids     = df_full["id"].tolist()

        if labels:
            sel_lbl = st.selectbox("Sélectionner", labels, label_visibility="collapsed")
            sel_id  = ids[labels.index(sel_lbl)]
            c_e, c_d, _ = st.columns([1, 1, 5])
            with c_e:
                if st.button("✏️ Modifier"):
                    st.session_state.edit_id = sel_id
                    st.session_state.page = "add"
                    st.rerun()
            with c_d:
                if st.button("🗑️ Supprimer"):
                    st.session_state.trades = [t for t in st.session_state.trades if t["id"] != sel_id]
                    st.success("Trade supprimé.")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : ADD / EDIT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "add":
    is_edit  = st.session_state.edit_id is not None
    existing = next((t for t in st.session_state.trades if t["id"] == st.session_state.edit_id), None)

    st.markdown(f"# {'✏️ Modifier le Trade' if is_edit else '➕ Nouveau Trade'}")
    if st.button("← Retour"):
        st.session_state.page = "journal"
        st.session_state.edit_id = None
        st.rerun()
    st.divider()

    def ev(key, default):
        return existing[key] if existing else default

    with st.form("form_trade"):
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1: d_date = st.date_input("Date", value=date.fromisoformat(ev("date", str(date.today()))))
        with r1c2: d_sym  = st.selectbox("Symbole",   SYMBOLS,          index=SYMBOLS.index(ev("symbol","EUR/USD")))
        with r1c3: d_dir  = st.selectbox("Direction", ["LONG","SHORT"],  index=["LONG","SHORT"].index(ev("direction","LONG")))

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        with r2c1: d_entry = st.number_input("Prix d'entrée",  value=float(ev("entry",0)),  format="%.5f", step=0.0001)
        with r2c2: d_exit  = st.number_input("Prix de sortie", value=float(ev("exit",0)),   format="%.5f", step=0.0001)
        with r2c3: d_qty   = st.number_input("Quantité",       value=float(ev("qty",1)),    format="%.4f", step=0.1)
        with r2c4: d_fees  = st.number_input("Frais ($)",      value=float(ev("fees",0)),   format="%.2f", step=0.5)

        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        with r3c1: d_sl    = st.number_input("Stop Loss",   value=float(ev("sl",0)),  format="%.5f", step=0.0001)
        with r3c2: d_tp    = st.number_input("Take Profit", value=float(ev("tp",0)),  format="%.5f", step=0.0001)
        with r3c3: d_strat = st.selectbox("Stratégie",  STRATEGIES, index=STRATEGIES.index(ev("strategy","Breakout")))
        with r3c4: d_mood  = st.selectbox("État d'esprit", MOODS,   index=MOODS.index(ev("mood","Confiant")))

        d_notes = st.text_area("Notes & Analyse", value=ev("notes",""),
                               placeholder="Raison du trade, contexte de marché, leçons apprises...", height=100)

        # ── Live preview ──
        if d_entry and d_exit and d_qty:
            raw     = (d_exit - d_entry)*d_qty if d_dir=="LONG" else (d_entry-d_exit)*d_qty
            est_pnl = round(raw - d_fees, 2)
            est_rr  = None
            if d_sl and d_tp:
                risk = abs(d_entry - d_sl)
                est_rr = round(abs(d_tp - d_entry)/risk, 2) if risk else None

            pc   = "#00d4aa" if est_pnl >= 0 else "#ff4d6d"
            rr_h = f'<div><div class="preview-label">R:R</div><div class="preview-value" style="color:#7c6aff">{est_rr}R</div></div>' if est_rr else ""
            st.markdown(f"""
            <div class="preview">
                <div><div class="preview-label">P&L ESTIMÉ</div>
                <div class="preview-value" style="color:{pc}">{fmt_pnl(est_pnl)}</div></div>
                {rr_h}
            </div>
            """, unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "✓  Sauvegarder les modifications" if is_edit else "✓  Enregistrer le Trade",
            use_container_width=True
        )

        if submitted:
            if not d_entry or not d_exit or not d_qty:
                st.error("Entrée, sortie et quantité sont obligatoires.")
            else:
                new_t = {
                    "id":        existing["id"] if is_edit else int(datetime.now().timestamp()*1000),
                    "date":      str(d_date),
                    "symbol":    d_sym,
                    "direction": d_dir,
                    "entry":     d_entry,
                    "exit":      d_exit,
                    "qty":       d_qty,
                    "fees":      d_fees,
                    "sl":        d_sl,
                    "tp":        d_tp,
                    "strategy":  d_strat,
                    "mood":      d_mood,
                    "notes":     d_notes,
                }
                if is_edit:
                    st.session_state.trades = [
                        new_t if t["id"] == existing["id"] else t
                        for t in st.session_state.trades
                    ]
                    st.success("✅ Trade modifié !")
                else:
                    st.session_state.trades.append(new_t)
                    st.success("✅ Trade enregistré !")

                st.session_state.page    = "journal"
                st.session_state.edit_id = None
                st.rerun()
