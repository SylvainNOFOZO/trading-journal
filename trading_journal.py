import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import json, os, base64, requests, io, hashlib, secrets as _secrets
import calendar as _calmod
import html as _html
try:
    import econ_kb as _kb          # fiches des indicateurs (fichier econ_kb.py à la racine du dépôt)
except Exception:
    _kb = None

st.set_page_config(page_title="Trading Journal Pro", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

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
    "Or & Noir": {
        "bg":"#070707","bg2":"#0d0d0d","card":"#151310","border":"#2b2616",
        "text":"#f6efdd","muted":"#8d8870",
        "accent":"#d4af37","win":"#5fd38a","loss":"#ff5c6c","alt":"#e8c35a",
        "orange":"#ffb300","sidebar":"#0a0a0a","btn_text":"#000000",
    },
    "Néon Électrique": {
        "bg":"#06070d","bg2":"#0a0c16","card":"#10131f","border":"#1c2238",
        "text":"#e9edff","muted":"#6f7aa0","accent":"#0078ff","win":"#22e3a0",
        "loss":"#ff2d55","alt":"#4d9bff","orange":"#ff8a3d","sidebar":"#080a12",
        "btn_text":"#ffffff",
    },
    "Violet Lavande": {
        "bg":"#0b0912","bg2":"#0f0c18","card":"#15111f","border":"#271f3a",
        "text":"#efeaff","muted":"#8278a0","accent":"#8a2be2","win":"#2ed19a",
        "loss":"#ff5c7a","alt":"#d8b4fe","orange":"#ffb454","sidebar":"#0d0a16",
        "btn_text":"#ffffff",
    },
    "Aubergine Doré": {
        "bg":"#0c0714","bg2":"#120a1d","card":"#190f28","border":"#2e1f42",
        "text":"#f3ecff","muted":"#9484ac","accent":"#9b59ff","win":"#46d6a0",
        "loss":"#ff6b81","alt":"#d4af37","orange":"#ffc24b","sidebar":"#0e0818",
        "btn_text":"#ffffff",
    },
    "Navy Corporate": {
        "bg":"#eef1f7","bg2":"#e5e9f2","card":"#ffffff","border":"#d9dfea",
        "text":"#1b2440","muted":"#6b7488","accent":"#2b3a67","win":"#16a085",
        "loss":"#e74c3c","alt":"#3d5a9a","orange":"#f39c12","sidebar":"#1e2a4a",
        "btn_text":"#ffffff",
    },
    "Violet Clair": {
        "bg":"#f5f3fd","bg2":"#efeafb","card":"#ffffff","border":"#e6def7",
        "text":"#211b33","muted":"#6d6786","accent":"#7c5cfc","win":"#10b981",
        "loss":"#ef4444","alt":"#b794f6","orange":"#f59e0b","sidebar":"#ffffff",
        "btn_text":"#ffffff",
    },
}
def _is_light(t):
    h = t["bg"].lstrip("#"); r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 150

# Designs clairs d'abord (fond non noir par défaut), puis les sombres, au choix
THEME_NAMES = ([n for n, t in THEMES.items() if _is_light(t)]
               + [n for n, t in THEMES.items() if not _is_light(t)])
DEFAULT_THEME = "Violet Lavande"   # design par défaut du dashboard
LOGIN_THEME   = "Navy Corporate"   # design unique de la page de connexion
DEFAULT_ACCOUNT = "Réel Indépendant"   # compte affiché à l'ouverture de l'app
DEFAULT_BG      = "Bitcoin"            # fond d'écran par défaut

# ── FONDS D'ÉCRAN (photos libres de droits, licence Unsplash) ─────────────────
# Rempli avec des photos dont la licence gratuite a été vérifiée. "Aucun" = pas d'image.
_UNS = "https://images.unsplash.com/photo-"
try:
    from backgrounds_data import BG_DATA      # images fournies, intégrées en base64 (backgrounds_data.py)
except Exception:
    BG_DATA = {}
# mode "cover" : image plein écran ; mode "logo" : filigrane centré
BACKGROUNDS = {"Aucun": None}
if BG_DATA:
    BACKGROUNDS.update({
        "Reporting & dashboard": {"data": "reporting", "mode": "cover"},
        "Forex trading":         {"data": "forex", "mode": "cover"},
        "Poste de trading":      {"data": "poste", "mode": "cover"},
        "CTC Finance":           {"data": "ctc", "data_light": "ctc_clair", "mode": "logo"},
        "Stat Vision":           {"data": "statvision", "mode": "logo"},
    })
BACKGROUNDS.update({
    "Salle multi-écrans":  {"url": _UNS + "1744782211816-c5224434614f", "credit": "Jakub Żerdzicki", "mode": "cover"},
    "Wall Street":         {"url": _UNS + "1468254095679-bbcba94a7066", "credit": "Patrick Weissenberger", "mode": "cover"},
    "Bourse de New York":  {"url": _UNS + "1625351814208-155cfe221d12", "credit": "tommao wang", "mode": "cover"},
    "Bitcoin":             {"url": _UNS + "1518544801976-3e159e50e5bb", "credit": "André François McKenzie", "mode": "cover"},
})
BG_NAMES = list(BACKGROUNDS.keys())

def bg_active():
    return BACKGROUNDS.get(st.session_state.get("bg_name", "Aucun")) is not None

def background_css(t, name):
    """Calque image + voile léger aux couleurs du design."""
    bg = BACKGROUNDS.get(name)
    if not bg:
        return ""
    light = _is_light(t)
    if "data" in bg:
        key = bg.get("data_light", bg["data"]) if light else bg["data"]
        if key not in BG_DATA:
            return ""
        mime, b64 = BG_DATA[key]
        src = f"data:{mime};base64,{b64}"
    else:
        src = bg["url"] + "?auto=format&fit=crop&w=2400&q=75"
    if bg.get("mode") == "logo":
        ov = 0.30 if light else 0.32
        layer = f"url('{src}') center 58% / min(58vw, 680px) auto no-repeat fixed"
    else:
        ov = 0.58 if light else 0.48
        layer = f"url('{src}') center / cover no-repeat fixed"
    credit = (f"<div style='position:fixed;right:12px;bottom:6px;z-index:5;font-size:10px;color:{t['muted']};"
              f"opacity:.75;pointer-events:none'>Photo : {bg['credit']} · Unsplash</div>") if bg.get("credit") else ""
    return (f"<style>.stApp {{ background:"
            f"linear-gradient(160deg, {_hexa(t['bg'], ov)} 0%, {_hexa(t['bg2'], ov)} 55%, {_hexa(t['bg'], ov)} 100%),"
            f"{layer}, {t['bg']} !important; }}</style>{credit}")

def theme_label(n):
    return ("Clair · " if _is_light(THEMES[n]) else "Sombre · ") + n

def get_theme():
    name = st.session_state.get("theme_name", DEFAULT_THEME)
    return THEMES.get(name, THEMES[DEFAULT_THEME])

# ── PROFILS GRAPHIQUES : chaque design change aussi le type et la config des graphiques ──
# equity   : "area" | "line" | "step" | "glow"      (courbe de capital / progression %)
# winloss  : "donut" | "pie" | "gauge" | "bar"       (répartition gagnants / perdants)
# monthly  : "bar" | "lollipop" | "area"             (P&L mensuel)
# ranking  : "hbar" | "lollipop"                     (classements actifs / stratégies)
CHART_STYLES = {
    "Classique": dict(equity="area", shape="linear", width=2.2, fill=0.10, markers=False,
        winloss="donut", hole=0.65, monthly="bar", ranking="hbar", corner=4, bar_opacity=0.85,
        bargap=0.25, grid="y", griddash="dot", font="Inter, sans-serif", hover="closest",
        toolbar=False, transparent=False, heat="RdYlGn", legend_top=False),
    "Néon": dict(equity="glow", shape="spline", width=3.0, fill=0.22, markers=False,
        winloss="donut", hole=0.80, monthly="area", ranking="lollipop", corner=8, bar_opacity=0.95,
        bargap=0.35, grid="none", griddash="solid", font="JetBrains Mono, monospace",
        hover="x unified", toolbar=False, transparent=True, heat="Plasma", legend_top=True),
    "Luxe": dict(equity="line", shape="spline", width=1.8, fill=0.0, markers=True,
        winloss="gauge", hole=0.0, monthly="lollipop", ranking="lollipop", corner=0, bar_opacity=0.9,
        bargap=0.45, grid="y", griddash="solid", font="Georgia, 'Times New Roman', serif",
        hover="closest", toolbar=False, transparent=True, heat="Cividis", legend_top=False),
    "Corporate": dict(equity="step", shape="hv", width=2.0, fill=0.06, markers=True,
        winloss="pie", hole=0.0, monthly="bar", ranking="hbar", corner=0, bar_opacity=1.0,
        bargap=0.15, grid="xy", griddash="solid", font="Arial, Helvetica, sans-serif",
        hover="x unified", toolbar=True, transparent=False, heat="Blues", legend_top=True),
    "Doux": dict(equity="area", shape="spline", width=2.6, fill=0.28, markers=False,
        winloss="bar", hole=0.55, monthly="area", ranking="hbar", corner=12, bar_opacity=0.8,
        bargap=0.30, grid="none", griddash="dot", font="Inter, sans-serif", hover="x unified",
        toolbar=False, transparent=True, heat="Purples", legend_top=True),
}
THEME_CHART_STYLE = {
    "Émeraude Sombre": "Classique", "Ardoise Bleu": "Classique",
    "Indigo Minuit": "Néon", "Néon Électrique": "Néon",
    "Ambre Doré": "Luxe", "Or & Noir": "Luxe", "Aubergine Doré": "Luxe",
    "Ivoire Clair": "Corporate", "Navy Corporate": "Corporate",
    "Violet Lavande": "Doux", "Violet Clair": "Doux",
}
CHART_STYLE_NAMES = list(CHART_STYLES.keys())

def get_chart_style_name():
    ov = st.session_state.get("chart_style_override", "Auto")
    if ov in CHART_STYLES:
        return ov
    return THEME_CHART_STYLE.get(st.session_state.get("theme_name", DEFAULT_THEME), "Classique")

def get_chart_style():
    return CHART_STYLES[get_chart_style_name()]

try:
    import plotly as _plotly_mod
    _PLOTLY_V = tuple(int(x) for x in _plotly_mod.__version__.split(".")[:2])
except Exception:
    _PLOTLY_V = (0, 0)
_PL_CORNER = _PLOTLY_V >= (5, 19)     # layout.barcornerradius
_PL_GRIDDASH = _PLOTLY_V >= (5, 13)   # axis.griddash

def _hexa(h, a):
    h = str(h).lstrip("#")
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except Exception:
        return h
    return f"rgba({r},{g},{b},{a})"

def chart_layout(t, cs, height=260, showlegend=False, **kwargs):
    """Layout Plotly selon design (couleurs) + profil graphique (police, survol, coins...)."""
    bg = "rgba(0,0,0,0)" if cs["transparent"] else t["card"]
    if bg_active():
        bg = _hexa(t["card"], 0.94)   # fond d'écran actif : graphiques sur fond plein, lisibles
    lay = dict(
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(color=t["muted"], family=cs["font"], size=12),
        height=height, margin=dict(l=54, r=18, t=18, b=36),
        showlegend=showlegend, hovermode=cs["hover"], bargap=cs["bargap"],
        hoverlabel=dict(bgcolor=t["card"], bordercolor=t["accent"],
                        font=dict(color=t["text"], family=cs["font"])),
    )
    if showlegend and cs["legend_top"]:
        lay["legend"] = dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                             font=dict(color=t["muted"]))
    if _PL_CORNER and cs["corner"]:
        lay["barcornerradius"] = cs["corner"]
    lay.update(kwargs)
    return lay

def chart_axes(fig, t, cs, xprefix="", yprefix="", xtickangle=0, free_y=False):
    gx = cs["grid"] in ("x", "xy"); gy = cs["grid"] in ("y", "xy")
    xa = dict(showgrid=gx, gridcolor=t["border"], linecolor=t["border"], tickcolor=t["border"],
              tickprefix=xprefix, tickangle=xtickangle, zeroline=False,
              showline=(cs["grid"] == "xy"), tickfont=dict(size=11))
    ya = dict(showgrid=gy, gridcolor=t["border"], linecolor=t["border"], tickcolor=t["border"],
              tickprefix=yprefix, showline=(cs["grid"] == "xy"), zeroline=True,
              zerolinecolor=t["border"], zerolinewidth=1, tickfont=dict(size=11),
              fixedrange=not free_y)
    if _PL_GRIDDASH:
        xa["griddash"] = cs["griddash"]; ya["griddash"] = cs["griddash"]
    fig.update_xaxes(**xa); fig.update_yaxes(**ya)

def diverging_scale(t):
    """Échelle perte -> neutre -> gain, adaptée au design (clair ou sombre)."""
    return [[0.0, _hexa(t["loss"], 0.9)], [0.5, t["card"]], [1.0, _hexa(t["win"], 0.9)]]

def sequential_scale(t, cs):
    """Échelle séquentielle propre au profil (comptes, intensités)."""
    if cs["heat"] in ("RdYlGn",):
        return [[0.0, t["card"]], [1.0, _hexa(t["accent"], 0.95)]]
    return cs["heat"]

def chart_config(cs):
    return {"displayModeBar": ("hover" if cs["toolbar"] else False), "displaylogo": False, "responsive": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}

def series_traces(x, y, color, cs, customdata=None, hovertemplate=None, name=None):
    """Traces d'une série temporelle (capital, %) selon le profil : area/line/step/glow."""
    shape = "hv" if cs["equity"] == "step" else cs["shape"]
    fill = "tozeroy" if cs["fill"] > 0 else None
    mode = "lines+markers" if cs["markers"] else "lines"
    traces = []
    if cs["equity"] == "glow":   # halo lumineux derrière la courbe
        traces.append(go.Scatter(x=x, y=y, mode="lines", hoverinfo="skip", showlegend=False,
            line=dict(color=_hexa(color, 0.25), width=cs["width"] * 4, shape=shape,
                      **({"smoothing": 0.6} if shape == "spline" else {}))))
    traces.append(go.Scatter(
        x=x, y=y, mode=mode, name=name or "",
        line=dict(color=color, width=cs["width"], shape=shape,
                  **({"smoothing": 0.6} if shape == "spline" else {})),
        marker=dict(size=5, color=color) if cs["markers"] else None,
        fill=fill, fillcolor=_hexa(color, cs["fill"]) if fill else None,
        customdata=customdata, hovertemplate=hovertemplate, showlegend=False))
    return traces

def winloss_figure(n_win, n_loss, wr_val, t, cs, height=260):
    """Graphique gagnants/perdants : donut | pie | gauge | bar selon le profil."""
    kind = cs["winloss"]
    if kind == "gauge":
        fig = go.Figure(go.Indicator(
            mode="gauge+number", value=round(wr_val, 1),
            number=dict(suffix="%", font=dict(size=34, color=t["win"], family=cs["font"])),
            gauge=dict(axis=dict(range=[0, 100], tickcolor=t["muted"],
                                 tickfont=dict(color=t["muted"], size=10)),
                       bar=dict(color=t["accent"], thickness=0.3),
                       bgcolor="rgba(0,0,0,0)", borderwidth=0,
                       steps=[dict(range=[0, 50], color=_hexa(t["loss"], 0.18)),
                              dict(range=[50, 100], color=_hexa(t["win"], 0.18))],
                       threshold=dict(line=dict(color=t["text"], width=2), value=50))))
        fig.add_annotation(text=f"{n_win} gagnants · {n_loss} perdants", x=0.5, y=-0.08,
                           showarrow=False, font=dict(color=t["muted"], size=12))
        fig.update_layout(**chart_layout(t, cs, height=height, margin=dict(l=24, r=24, t=30, b=30)))
        return fig
    if kind == "bar":
        fig = go.Figure()
        for lbl, v, col in (("Gagnants", n_win, t["win"]), ("Perdants", n_loss, t["loss"])):
            fig.add_trace(go.Bar(y=["Trades"], x=[v], name=lbl, orientation="h",
                marker=dict(color=col, opacity=cs["bar_opacity"]), text=[f"{lbl} · {v}"],
                textposition="inside", insidetextanchor="middle",
                textfont=dict(color="#ffffff", size=12),
                hovertemplate=f"<b>{lbl}</b>: %{{x}} trades<extra></extra>"))
        fig.update_layout(**chart_layout(t, cs, height=height, barmode="stack",
                                         margin=dict(l=10, r=10, t=60, b=20)))
        fig.update_xaxes(visible=False); fig.update_yaxes(visible=False)
        fig.add_annotation(text=f"<b>{wr_val:.0f}%</b> win rate", x=0.5, y=1.18, xref="paper",
            yref="paper", showarrow=False, font=dict(size=26, color=t["win"], family=cs["font"]))
        return fig
    hole = cs["hole"] if kind == "donut" else 0.0
    fig = go.Figure(go.Pie(
        values=[n_win, n_loss], labels=["Gagnants", "Perdants"], hole=hole, sort=False,
        pull=[0.04, 0] if kind == "pie" else None,
        marker=dict(colors=[t["win"], t["loss"]], line=dict(color=t["card"], width=3)),
        hovertemplate="<b>%{label}</b>: %{value} trades (%{percent})<extra></extra>",
        textinfo="percent" if kind == "pie" else "none",
        textfont=dict(color="#ffffff", size=13, family=cs["font"])))
    if kind == "donut":
        fig.add_annotation(text=f"<b>{wr_val:.0f}%</b>", x=0.5, y=0.58, showarrow=False,
            font=dict(size=28, color=t["win"], family=cs["font"]))
        fig.add_annotation(text="Win Rate", x=0.5, y=0.38, showarrow=False,
            font=dict(size=12, color=t["muted"]))
    fig.update_layout(**chart_layout(t, cs, height=height, showlegend=True,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.08,
                                  font=dict(color=t["muted"]))))
    return fig

def category_figure(cats, vals, colors, t, cs, kind, orientation="v", texts=None,
                    customdata=None, hovertemplate=None):
    """Barres ou sucettes (lollipop) ou aire, verticales ou horizontales."""
    h = orientation == "h"
    fig = go.Figure()
    if kind == "lollipop":
        for c, v, col in zip(cats, vals, colors):
            fig.add_trace(go.Scatter(
                x=[0, v] if h else [c, c], y=[c, c] if h else [0, v], mode="lines",
                line=dict(color=_hexa(col, 0.55), width=2), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(
            x=vals if h else cats, y=cats if h else vals, mode="markers+text" if texts else "markers",
            marker=dict(color=colors, size=13, line=dict(color=t["card"], width=2)),
            text=texts, textposition="middle right" if h else "top center",
            textfont=dict(size=11, color=t["muted"]),
            customdata=customdata, hovertemplate=hovertemplate, showlegend=False))
    elif kind == "area" and not h:
        col = t["win"] if sum(vals) >= 0 else t["loss"]
        fig.add_trace(go.Scatter(x=cats, y=vals, mode="lines+markers",
            line=dict(color=t["accent"], width=cs["width"], shape="linear"),
            marker=dict(color=colors, size=9, line=dict(color=t["card"], width=2)),
            fill="tozeroy", fillcolor=_hexa(t["accent"], max(cs["fill"], 0.12)),
            customdata=customdata, hovertemplate=hovertemplate, showlegend=False))
    else:
        fig.add_trace(go.Bar(
            x=vals if h else cats, y=cats if h else vals, orientation=orientation,
            marker=dict(color=colors, opacity=cs["bar_opacity"],
                        line=dict(color=t["card"], width=0.5)),
            text=texts, textposition="outside" if texts else None,
            textfont=dict(size=11, color=t["muted"]),
            customdata=customdata, hovertemplate=hovertemplate, showlegend=False))
    return fig

def build_css(t):
    """Génère le CSS complet en fonction du thème actif."""
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');
.fa, .fas, .far, .fab, .fa-solid, .fa-regular {{ font-family: "Font Awesome 6 Free" !important; }}
:root {{ --tj-bg:{t['bg']}; --tj-bg2:{t['bg2']}; --tj-card:{t['card']}; --tj-border:{t['border']};
        --tj-text:{t['text']}; --tj-muted:{t['muted']}; --tj-accent:{t['accent']};
        --tj-win:{t['win']}; --tj-loss:{t['loss']}; --tj-alt:{t['alt']}; --tj-orange:{t['orange']}; }}
.icon {{ display:inline-flex; align-items:center; justify-content:center;
        width:32px; height:32px; border-radius:8px; font-size:15px; }}
.icon-green  {{ color:{t['win']}; background:{t['win']}1f; }}
.icon-red    {{ color:{t['loss']}; background:{t['loss']}1f; }}
.icon-purple {{ color:{t['alt']}; background:{t['alt']}1f; }}
.icon-orange {{ color:{t['orange']}; background:{t['orange']}1f; }}
.icon-muted  {{ color:{t['muted']}; background:{t['muted']}1a; }}
.mood-dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }}
.stApp {{ background: linear-gradient(160deg, {t['bg']} 0%, {t['bg2']} 55%, {t['bg']} 100%); background-attachment: fixed; font-size:14px; }}
/* Navigation horizontale : masquer la sidebar */
section[data-testid="stSidebar"] {{ display:none; }}
button[data-testid="stBaseButton-headerNoPadding"] {{ display:none; }}
.block-container {{ padding-top:2.2rem; max-width:1500px; }}
/* Police réduite globale */
h1 {{ font-size:1.5rem !important; }}
h2 {{ font-size:1.2rem !important; }}
h3 {{ font-size:1.05rem !important; }}
h4 {{ font-size:0.92rem !important; }}
p,label,.stMarkdown,.stMarkdown li {{ font-size:13px; }}
/* Boutons de navigation compacts */
.stButton > button {{ font-size:13px; padding:6px 10px; }}
h1,h2,h3,h4,h5,h6,p,label,.stMarkdown {{ color: {t['text']} !important; }}
.stSelectbox label,.stNumberInput label,.stTextInput label,.stTextArea label,.stDateInput label {{
    color: {t['muted']} !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1px; }}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea,
div[data-baseweb="select"] > div {{
    background-color: {t['bg2']} !important; border-color: {t['border']} !important; color: {t['text']} !important; }}
/* Champs Streamlit 1.66 (react-aria) : fond, texte, contour et focus aux couleurs du design */
[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
[data-testid="stNumberInputContainer"], .stApp [data-rac][role="group"] {{
    background-color: {t['bg2']} !important; border:1px solid {t['border']} !important; border-radius:10px !important; }}
[data-testid="stTextInputRootElement"]:focus-within, [data-testid="stTextAreaRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within, .stApp [data-rac][role="group"]:focus-within {{
    border-color: {t['accent']} !important; box-shadow:0 0 0 2px {t['accent']}26 !important; }}
.stApp input, .stApp textarea {{ color: {t['text']} !important; caret-color: {t['accent']}; }}
.stApp input::placeholder, .stApp textarea::placeholder {{ color: {t['muted']} !important; opacity:.8; }}
.stApp [data-rac][role="group"] svg, [data-testid="stNumberInputContainer"] button {{ color: {t['muted']} !important; fill: {t['muted']}; }}
[role="listbox"] {{ background:{t['card']} !important; border:1px solid {t['border']} !important; border-radius:10px !important; }}
[role="listbox"] [role="option"] {{ color:{t['text']} !important; }}
[role="listbox"] [role="option"][data-focused="true"], [role="listbox"] [role="option"]:hover {{ background:{t['accent']}1f !important; }}
[role="listbox"] [role="option"][aria-selected="true"] {{ color:{t['accent']} !important; font-weight:700; }}
.stButton > button {{ background:linear-gradient(135deg,{t['accent']},{t['alt']});color:{t['btn_text']};font-weight:800;border:none;border-radius:10px;box-shadow:0 2px 8px {t['accent']}33; }}
.stButton > button:hover {{ filter:brightness(1.08); color:{t['btn_text']} !important; box-shadow:0 4px 14px {t['accent']}55; }}
.stButton > button p, .stButton > button [data-testid="stMarkdownContainer"] p,
.stButton > button [data-testid="stIconMaterial"] {{ color:{t['btn_text']} !important; }}
/* Bouton de téléchargement et zone de dépôt de fichier : thémés */
[data-testid="stDownloadButton"] > button {{ background:{t['card']} !important; color:{t['accent']} !important;
    border:1px solid {t['accent']}66 !important; border-radius:10px; font-weight:700; }}
[data-testid="stDownloadButton"] > button p {{ color:{t['accent']} !important; }}
[data-testid="stDownloadButton"] > button:hover {{ background:{t['accent']}1a !important; }}
[data-testid="stFileUploaderDropzone"] {{ background:{t['card']} !important; border:1px dashed {t['border']} !important;
    color:{t['text']} !important; border-radius:10px; }}
[data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderFile"] div, [data-testid="stFileUploaderFile"] small {{ color:{t['text']} !important; }}
[data-testid="stFileUploaderFile"] {{ background:{t['bg']} !important; border:1px solid {t['border']}; border-radius:8px; }}
[data-testid="stFileUploaderDropzone"] button {{ background:{t['accent']}1a !important; color:{t['accent']} !important;
    border:1px solid {t['accent']}55 !important; }}
/* Boutons de formulaire (Se connecter, Enregistrer...) : même style que les boutons du design */
[data-testid="stFormSubmitButton"] > button {{ background:linear-gradient(135deg,{t['accent']},{t['alt']}) !important;
    color:{t['btn_text']} !important; font-weight:800; border:none !important; border-radius:10px;
    box-shadow:0 2px 8px {t['accent']}33; }}
[data-testid="stFormSubmitButton"] > button:hover {{ filter:brightness(1.08); box-shadow:0 4px 14px {t['accent']}55; }}
[data-testid="stFormSubmitButton"] > button * {{ color:{t['btn_text']} !important; }}
[data-testid="stFormSubmitButton"] > button[kind="secondaryFormSubmit"] {{ background:{t['bg2']} !important;
    color:{t['text']} !important; border:1px solid {t['border']} !important; box-shadow:none; }}
[data-testid="stFormSubmitButton"] > button[kind="secondaryFormSubmit"] * {{ color:{t['text']} !important; }}
.kpi {{ background:linear-gradient(145deg,{t['card']},{t['bg2']});border:1px solid {t['border']};border-radius:12px;padding:12px 14px 10px;position:relative;overflow:hidden;min-height:84px;box-shadow:0 1px 2px rgba(0,0,0,.08),0 4px 14px rgba(0,0,0,.06); }}
.kpi-bar {{ position:absolute;top:0;left:0;right:0;height:3px; }}
.kpi-icon {{ font-size:14px;margin-bottom:2px;float:right;opacity:.85; }}
.kpi-label {{ font-size:10px;color:{t['muted']};letter-spacing:1.2px;text-transform:uppercase;font-weight:600; }}
.kpi-value {{ font-size:21px;font-weight:800;font-family:"JetBrains Mono",monospace;margin:3px 0 1px; }}
/* Onglets du dashboard */
.stTabs [data-baseweb="tab-list"], .stTabs [role="tablist"] {{ gap:6px; border-bottom:1px solid {t['border']}; }}
.stTabs [data-baseweb="tab"], [data-testid="stTab"] {{ height:38px; padding:0 14px !important; border-radius:9px 9px 0 0;
    color:{t['muted']} !important; font-weight:600; transition:all .15s ease; }}
[data-testid="stTab"] p {{ color:inherit !important; font-size:13px !important; font-weight:600; }}
[data-testid="stTab"]:hover {{ color:{t['text']} !important; background:{t['accent']}0d; }}
.stTabs [aria-selected="true"], [data-testid="stTab"][data-selected="true"] {{ color:{t['accent']} !important;
    background:{t['accent']}12; box-shadow:inset 0 -2px 0 {t['accent']}; }}
.stTabs [data-baseweb="tab-highlight"] {{ background:{t['accent']} !important; }}
[data-testid="stTab"] > div[data-rac] {{ background:{t['accent']} !important; }}
/* Curseurs (sliders) : poignées et valeurs aux couleurs du design, piste neutre */
[data-testid="stSlider"] div[data-rac][style*="translate(-50%"] {{ background:{t['accent']} !important;
    box-shadow:0 0 0 3px {t['accent']}30 !important; }}
[data-testid="stSlider"] div[style*="linear-gradient"] {{ filter:grayscale(1) contrast(1.1); }}
[data-testid="stSliderThumbValue"], [data-testid="stSliderThumbValue"] * {{ color:{t['accent']} !important; }}
div[data-testid="stExpander"] details {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:10px; }}
div[data-testid="stExpander"] summary p {{ font-size:12px !important; color:{t['muted']} !important; }}
.kpi-sub {{ font-size:11px;color:{t['muted']}; }}
.tj-table {{ width:100%;border-collapse:collapse;font-size:13px; }}
.tj-table th {{ padding:10px 12px;text-align:left;font-size:10px;color:{t['muted']};letter-spacing:1px;
    text-transform:uppercase;border-bottom:1px solid {t['border']};background:linear-gradient(180deg,{t['card']},{t['bg2']});font-weight:600; }}
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
.b-sec  {{ color:{t['orange']};background:{t['orange']}20;border:1px dashed {t['orange']}66; }}
hr {{ border-color:{t['border']} !important; }}
.sync-ok {{ background:{t['win']}18;border:1px solid {t['win']}44;border-radius:8px;padding:6px 14px;font-size:12px;color:{t['win']}; }}
.mode-banner-real {{ background:{t['win']}14;border:1px solid {t['win']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['win']};font-weight:700;margin-bottom:12px; }}
.mode-banner-sec {{ background:{t['orange']}12;border:1px dashed {t['orange']}66;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['orange']};font-weight:700;margin-bottom:12px; }}
.mode-banner-inst {{ background:{t['alt']}14;border:1px solid {t['alt']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['alt']};font-weight:700;margin-bottom:12px; }}
.mode-banner-demo {{ background:{t['orange']}14;border:1px solid {t['orange']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['orange']};font-weight:700;margin-bottom:12px; }}
.mode-banner-all  {{ background:{t['alt']}14;border:1px solid {t['alt']}4d;border-radius:10px;
    padding:8px 16px;font-size:12px;color:{t['alt']};font-weight:700;margin-bottom:12px; }}
.grad-card {{ background:linear-gradient(145deg,{t['card']},{t['bg2']});border:1px solid {t['border']};border-radius:14px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.18),0 8px 24px rgba(0,0,0,.08); }}
/* Couleurs du design sur les composants Streamlit (sinon rouge par défaut) */
header[data-testid="stHeader"] {{ background:transparent !important; }}
span[data-tag] {{ background:linear-gradient(135deg,{t['accent']},{t['alt']}) !important; color:{t['btn_text']} !important;
    border-radius:8px !important; }}
span[data-tag] * {{ color:{t['btn_text']} !important; }}
label[data-testid="stRadioOption"] > div > div:first-child {{ border-color:{t['border']} !important; }}
label[data-testid="stRadioOption"][data-selected="true"] > div > div:first-child {{
    background:{t['accent']} !important; border-color:{t['accent']} !important; }}
.grad-accent {{ background:linear-gradient(135deg,{t['accent']},{t['alt']});-webkit-background-clip:text;background-clip:text;color:transparent;font-weight:800; }}
/* ══ FORMES : chaque bloc prend une forme adaptée à ce qu'il porte ══════════════ */
/* KPI montant : feuille (angles opposés) · KPI ratio : capsule avec jauge · KPI risque : angles coupés */
.kpi {{ border-radius:22px 6px 22px 6px; }}
.kpi.kpi-ratio {{ border-radius:44px 14px 14px 44px; padding-left:18px; }}
.kpi.kpi-ratio .kpi-bar {{ left:30px; right:18px; border-radius:0 0 4px 4px; }}
.kpi.kpi-risk {{ border-radius:3px; border:none; background:linear-gradient(135deg,{t['loss']}14,{t['card']} 45%,{t['bg2']});
    clip-path:polygon(0 0,calc(100% - 20px) 0,100% 20px,100% 100%,20px 100%,0 calc(100% - 20px)); }}
.kpi.kpi-risk .kpi-bar {{ right:20px; }}
.kpi-ring {{ float:right; width:38px; height:38px; border-radius:50%; margin:-2px -2px 0 6px;
    -webkit-mask:radial-gradient(circle,transparent 11px,#000 12px); mask:radial-gradient(circle,transparent 11px,#000 12px); }}
/* Graphiques : une rangée forme un bloc continu (bords extérieurs très arrondis, joints serrés) */
[data-testid="stPlotlyChart"] {{ background:{t['card']}; border:1px solid {t['border']}; overflow:hidden;
    border-radius:26px 26px 8px 8px; }}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stPlotlyChart"] {{ border-radius:30px 8px 8px 30px; }}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child [data-testid="stPlotlyChart"] {{ border-radius:8px 30px 30px 8px; }}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:not(:first-child):not(:last-child) [data-testid="stPlotlyChart"] {{ border-radius:10px; }}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:only-child [data-testid="stPlotlyChart"] {{ border-radius:26px 26px 8px 8px; }}
/* Onglets : segments en pastille */
.stTabs [data-baseweb="tab"], [data-testid="stTab"] {{ border-radius:999px !important; margin-right:4px; }}
.stTabs [aria-selected="true"], [data-testid="stTab"][data-selected="true"] {{ box-shadow:inset 0 0 0 1px {t['accent']}66 !important;
    background:{t['accent']}1c !important; }}
[data-testid="stTab"] > div[data-rac] {{ display:none !important; }}
/* Zones repliables : coins alternés · messages : bulle (coin d'origine pointu) */
div[data-testid="stExpander"] details {{ border-radius:18px 4px 18px 4px !important; }}
div[data-testid="stExpander"] details summary, div[data-testid="stExpander"] details[open] summary {{ background:transparent !important; color:{t['text']} !important; border-radius:18px 4px 0 0; }}
div[data-testid="stExpander"] details summary:hover {{ background:{t['accent']}0d !important; }}
[data-testid="stAlert"] > div {{ border-radius:16px 16px 16px 4px !important; }}
.grad-card {{ border-radius:26px 6px 26px 6px; }}
.mode-banner-real, .mode-banner-sec, .mode-banner-inst, .mode-banner-demo, .mode-banner-all {{ border-radius:999px !important; }}
[data-testid="stDataFrame"], [data-testid="stTable"] {{ border-radius:14px 14px 4px 4px; overflow:hidden; }}
/* Boutons : pastilles · filtres à cocher : pastilles discrètes qui s'ouvrent en menu */
.stButton > button, [data-testid="stFormSubmitButton"] > button, [data-testid="stDownloadButton"] > button {{ border-radius:999px !important; }}
[data-testid="stPopover"] > div > button, [data-testid="stPopover"] button {{ background:{t['card']} !important;
    color:{t['text']} !important; border:1px solid {t['border']} !important; border-radius:999px !important;
    font-size:12.5px !important; font-weight:600; min-height:34px; padding:2px 14px !important; }}
[data-testid="stPopover"] button p, [data-testid="stPopover"] button span {{ color:{t['text']} !important; }}
[data-testid="stPopover"] button:hover {{ border-color:{t['accent']} !important; background:{t['accent']}12 !important; }}
[data-testid="stPopoverBody"] {{ background:{t['card']} !important; border:1px solid {t['border']} !important;
    border-radius:6px 20px 20px 20px !important; box-shadow:0 14px 40px rgba(0,0,0,.28) !important; }}
[data-testid="stPopoverBody"] .stButton > button {{ background:{t['accent']}14 !important; color:{t['accent']} !important;
    box-shadow:none; font-size:12px; padding:3px 8px; }}
[data-testid="stPopoverBody"] .stButton > button p {{ color:{t['accent']} !important; }}
[data-testid="stCheckbox"] label span:first-child {{ border-radius:6px !important; }}
[data-testid="stCheckbox"] label[data-checked="true"] span:first-child, [data-testid="stCheckbox"] input:checked + div,
[data-testid="stCheckbox"] [data-selected="true"] > span:first-child {{ background:{t['accent']} !important; border-color:{t['accent']} !important; }}
/* Fenêtres (export) : aux couleurs du design */
[data-testid="stDialog"] div:has(> [role="dialog"]), [data-testid="stDialog"] [role="dialog"] div {{ background-color:transparent; }}
[data-testid="stDialog"] div:has(> [role="dialog"]) {{ background:{t['card']} !important; border:1px solid {t['border']} !important;
    border-radius:8px 30px 30px 30px !important; }}
div[role="dialog"] {{ background:transparent !important; color:{t['text']} !important; border:1px solid {t['border']} !important;
    border-radius:8px 30px 30px 30px !important; }}
div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] h3, div[role="dialog"] p, div[role="dialog"] label,
div[role="dialog"] span, div[role="dialog"] [data-testid="stMarkdownContainer"] {{ color:{t['text']}; }}
div[role="dialog"] [data-testid="stCaptionContainer"] p {{ color:{t['muted']} !important; }}
div[role="dialog"] input {{ color:{t['text']} !important; }}
div[role="dialog"] button[aria-label="Close"] svg {{ color:{t['muted']}; fill:{t['muted']}; }}
.st-key-dash_filters, .st-key-jq_filters, .st-key-ex_filters, .st-key-news_filters {{ flex-wrap:wrap; }}
.st-key-dash_filters > div, .st-key-jq_filters > div, .st-key-ex_filters > div, .st-key-news_filters > div {{ flex:1 1 150px; min-width:130px; }}
</style>
"""
# Comptes par défaut (utilisés au tout premier lancement, puis gérés par l'admin)
DEFAULT_ACCOUNTS = [
    {"name": "Démo",                "kind": "demo"},
    {"name": "Réel Indépendant",    "kind": "real"},
    {"name": "Réel Institutionnel", "kind": "real"},
    {"name": "Compte Secondaire",   "kind": "real"},
]
# Rempli dynamiquement au démarrage depuis la base (voir plus bas)
TRADE_MODES  = [a["name"] for a in DEFAULT_ACCOUNTS]
MODE_FILTER_OPTIONS = ["Tous"] + TRADE_MODES
ACCOUNT_KIND = {a["name"]: a["kind"] for a in DEFAULT_ACCOUNTS}
_BADGE_PALETTE = ["#00d4aa","#7c6aff","#ff9f43","#54a0ff","#ff4d6d",
                  "#00cec9","#fdcb6e","#5f27cd","#fd79a8","#0984e3"]

def account_color(name):
    if name in TRADE_MODES:
        return _BADGE_PALETTE[TRADE_MODES.index(name) % len(_BADGE_PALETTE)]
    return "#8892a4"

def mode_badge(name):
    col = account_color(name)
    return (f'<span class="badge" style="color:{col};background:{col}26;'
            f'border:1px solid {col}4d">{name}</span>')
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
if "theme_name"  not in st.session_state: st.session_state.theme_name  = DEFAULT_THEME
if "mode_filter" not in st.session_state: st.session_state.mode_filter = "Tous"
if "mode_selection" not in st.session_state: st.session_state.mode_selection = []






# ── COMPTES (dynamiques, gérés par l'admin) ─────────────────────────────────
def accounts_load():
    if not _sb_ready():
        return st.session_state.get("_local_accounts", list(DEFAULT_ACCOUNTS))
    try:
        r = requests.get(f"{SB_EP}?key=eq.accounts&select=value", headers=SB_HDR, timeout=10)
        if r.status_code == 200 and r.json():
            val = r.json()[0].get("value", [])
            if isinstance(val, list) and val:
                # Normaliser : accepter liste de str ou de dicts
                out = []
                for a in val:
                    if isinstance(a, str):
                        out.append({"name": a, "kind": "demo" if "demo" in a.lower() or "démo" in a.lower() else "real"})
                    elif isinstance(a, dict) and a.get("name"):
                        out.append({"name": a["name"], "kind": a.get("kind", "real")})
                if out:
                    return out
        # Base vide → semer avec les comptes par défaut
        accounts_save(list(DEFAULT_ACCOUNTS))
        return list(DEFAULT_ACCOUNTS)
    except Exception:
        return list(DEFAULT_ACCOUNTS)

def accounts_save(accs):
    if not _sb_ready():
        st.session_state["_local_accounts"] = accs
        return False
    try:
        r = requests.patch(f"{SB_EP}?key=eq.accounts",
            headers={**SB_HDR, "Prefer": "return=representation"},
            json={"value": accs, "updated_at": "now()"}, timeout=15)
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            return True
        if r.status_code == 204:
            return True
        r2 = requests.post(SB_EP,
            headers={**SB_HDR, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"key": "accounts", "value": accs}, timeout=15)
        return r2.status_code in (200, 201)
    except Exception:
        return False

def apply_accounts(accs):
    """Réassigne les variables globales à partir de la liste de comptes."""
    global TRADE_MODES, MODE_FILTER_OPTIONS, ACCOUNT_KIND
    TRADE_MODES = [a["name"] for a in accs]
    MODE_FILTER_OPTIONS = ["Tous"] + TRADE_MODES
    ACCOUNT_KIND = {a["name"]: a.get("kind", "real") for a in accs}

# ── CAPITAL DE DÉPART PAR COMPTE ────────────────────────────────────────────
def capital_load():
    if not _sb_ready():
        return st.session_state.get("_local_capital", {})
    try:
        r = requests.get(f"{SB_EP}?key=eq.account_capital&select=value", headers=SB_HDR, timeout=10)
        if r.status_code == 200 and r.json():
            val = r.json()[0].get("value", {})
            return val if isinstance(val, dict) else {}
    except Exception:
        pass
    return {}

def capital_save(cap):
    if not _sb_ready():
        st.session_state["_local_capital"] = cap
        return False
    try:
        r = requests.patch(f"{SB_EP}?key=eq.account_capital",
            headers={**SB_HDR, "Prefer": "return=representation"},
            json={"value": cap, "updated_at": "now()"}, timeout=15)
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            return True
        if r.status_code == 204:
            return True
        r2 = requests.post(SB_EP,
            headers={**SB_HDR, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"key": "account_capital", "value": cap}, timeout=15)
        return r2.status_code in (200, 201)
    except Exception:
        return False

# ── Stockage clé/valeur générique (même table journal_data) ───────────────────
def kv_load(key, default=None):
    if not _sb_ready():
        return st.session_state.get(f"_local_kv_{key}", default)
    try:
        r = requests.get(f"{SB_EP}?key=eq.{key}&select=value", headers=SB_HDR, timeout=10)
        if r.status_code == 200 and r.json():
            v = r.json()[0].get("value")
            return default if v is None else v
    except Exception:
        pass
    return default

def kv_save(key, value):
    if not _sb_ready():
        st.session_state[f"_local_kv_{key}"] = value
        return False
    try:
        r = requests.patch(f"{SB_EP}?key=eq.{key}",
            headers={**SB_HDR, "Prefer": "return=representation"},
            json={"value": value, "updated_at": "now()"}, timeout=15)
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            return True
        r2 = requests.post(SB_EP,
            headers={**SB_HDR, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"key": key, "value": value}, timeout=15)
        return r2.status_code in (200, 201)
    except Exception:
        return False

# ── Alertes d'annonces économiques (préférences par utilisateur) ──────────────
ALERT_CCYS = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY"]
ALERT_DEFAULTS = {"impacts": ["High"], "ccys": ["USD", "EUR"], "chrono_h": 4}

def alert_prefs_get(user):
    allp = kv_load("alert_prefs", {}) or {}
    p = dict(ALERT_DEFAULTS); p.update(allp.get(user, {}) if isinstance(allp, dict) else {})
    return p

def alert_prefs_set(user, prefs):
    allp = kv_load("alert_prefs", {}) or {}
    if not isinstance(allp, dict):
        allp = {}
    allp[user] = prefs
    return kv_save("alert_prefs", allp)


def _resolve_scope(sel):
    """Normalise sel (str 'Tous'/compte, liste de comptes, ou None) en liste
    de comptes effectivement affichés, toujours restreinte aux droits."""
    allowed = allowed_accounts()
    if sel is None:
        sel = st.session_state.get("mode_selection", [])
    if isinstance(sel, str):
        sel = [sel] if sel in TRADE_MODES else []   # 'Tous' -> [] = tous les comptes autorisés
    scope = [m for m in sel if m in allowed]
    return scope if scope else list(allowed)

# ── CAPTURES D'ÉCRAN DES TRADES ─────────────────────────────────────────────
def screenshots_load():
    if not _sb_ready():
        return st.session_state.get("_local_shots", {})
    try:
        r = requests.get(f"{SB_EP}?key=eq.trade_screenshots&select=value", headers=SB_HDR, timeout=15)
        if r.status_code == 200 and r.json():
            val = r.json()[0].get("value", {})
            return val if isinstance(val, dict) else {}
    except Exception:
        pass
    return {}

def screenshots_save(shots):
    if not _sb_ready():
        st.session_state["_local_shots"] = shots
        return False
    try:
        r = requests.patch(f"{SB_EP}?key=eq.trade_screenshots",
            headers={**SB_HDR, "Prefer": "return=representation"},
            json={"value": shots, "updated_at": "now()"}, timeout=30)
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            return True
        if r.status_code == 204:
            return True
        r2 = requests.post(SB_EP,
            headers={**SB_HDR, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"key": "trade_screenshots", "value": shots}, timeout=30)
        return r2.status_code in (200, 201)
    except Exception:
        return False

def kv_load_many(keys):
    """Lit plusieurs clés en une requête : {clé: valeur}."""
    keys = [k for k in keys if k]
    if not keys:
        return {}
    if not _sb_ready():
        return {k: st.session_state.get(f"_local_kv_{k}") for k in keys}
    out = {}
    try:
        for i in range(0, len(keys), 40):
            chunk = keys[i:i + 40]
            r = requests.get(f"{SB_EP}?key=in.({','.join(chunk)})&select=key,value", headers=SB_HDR, timeout=20)
            if r.status_code == 200:
                out.update({row["key"]: row.get("value") for row in r.json()})
    except Exception:
        pass
    return out

def kv_delete(key):
    if not _sb_ready():
        st.session_state.pop(f"_local_kv_{key}", None)
        return False
    try:
        r = requests.delete(f"{SB_EP}?key=eq.{key}", headers=SB_HDR, timeout=15)
        return r.status_code in (200, 204)
    except Exception:
        return False

def compress_image(raw_bytes, max_side=1600, quality=80):
    """Redimensionne/compresse en JPEG et renvoie une data-URI base64.
    Repli sur l'image brute encodée si PIL indisponible."""
    try:
        from PIL import Image
        import io as _io
        im = Image.open(_io.BytesIO(raw_bytes))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.thumbnail((max_side, max_side))
        buf = _io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        # Réduire encore si trop lourd
        if len(data) > 900_000:
            buf = _io.BytesIO(); im.save(buf, format="JPEG", quality=60, optimize=True)
            data = buf.getvalue()
        return "data:image/jpeg;base64," + base64.b64encode(data).decode()
    except Exception:
        return "data:image/png;base64," + base64.b64encode(raw_bytes).decode()

def get_capital(mode_filter=None):
    """Capital de départ pour le périmètre affiché (somme des comptes sélectionnés)."""
    caps = st.session_state.get("account_capital", {})
    scope = _resolve_scope(mode_filter)
    return sum(float(caps.get(a, 0) or 0) for a in scope)

def is_admin():
    return st.session_state.get("auth_role") == "admin"

def selection_label():
    """Libellé lisible du périmètre de comptes actuellement affiché."""
    allowed = allowed_accounts()
    scope = _resolve_scope(None)
    if not scope or set(scope) == set(allowed):
        return "Tous les comptes" if len(allowed) != 1 else (allowed[0] if allowed else "—")
    if len(scope) == 1:
        return scope[0]
    return f"{len(scope)} comptes : " + ", ".join(scope)

if "accounts_meta" not in st.session_state:
    st.session_state.accounts_meta = accounts_load()
apply_accounts(st.session_state.accounts_meta)   # réassigne TRADE_MODES à chaque run
if "account_capital" not in st.session_state:
    st.session_state.account_capital = capital_load()
if "trade_screenshots" not in st.session_state:
    st.session_state.trade_screenshots = screenshots_load()


def get_pnl(t): return float(t.get("pnl", 0))

def calc_rr(t):
    sl, tp, entry = t.get("sl",0), t.get("tp",0), t.get("entry",0)
    if not sl or not tp or not entry: return None
    risk = abs(entry - sl)
    return round(abs(tp - entry)/risk, 2) if risk else None

def fmt(n):
    if n is None: return "—"
    return f"+${n:,.2f}" if n >= 0 else f"-${abs(n):,.2f}"

def get_df(mode_filter=None):
    rows = [dict(t, pnl=get_pnl(t), rr=calc_rr(t)) for t in st.session_state.trades]
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if df.empty: return df
    if "trade_mode" not in df.columns: df["trade_mode"] = "Réel Indépendant"
    allowed = allowed_accounts()
    if allowed:
        df = df[df["trade_mode"].isin(allowed)]
    # Filtrer sur les comptes sélectionnés (un, plusieurs, ou tous)
    scope = _resolve_scope(mode_filter)
    if scope and set(scope) != set(allowed):
        df = df[df["trade_mode"].isin(scope)]
    return df


# ── FILTRES À COCHER (menu repliable : on coche, on clique ailleurs, il se referme) ──
def _ck_sync(state_key, prefix, options):
    st.session_state[state_key] = [o for o in options if st.session_state.get(f"{prefix}__{o}")]

def _ck_all(state_key, prefix, options, value):
    for o in options:
        st.session_state[f"{prefix}__{o}"] = value
    st.session_state[state_key] = list(options) if value else []

def check_filter(title, options, state_key, prefix, all_label="Tous", fmt=str, icon=None):
    """Liste de cases à cocher dans un menu repliable. Rien de coché = tout est pris.
    Renvoie la liste cochée (filtrée sur les options existantes)."""
    options = list(options)
    sel = [o for o in st.session_state.get(state_key, []) if o in options]
    st.session_state[state_key] = sel
    if not sel:
        summ = all_label
    elif len(sel) == len(options):
        summ = "tout"
    elif len(sel) <= 2:
        summ = ", ".join(fmt(o) for o in sel)
    else:
        summ = f"{len(sel)} sélectionnés"
    with st.popover(f"{title} · {summ}", icon=icon, use_container_width=True):
        if not options:
            st.caption("Aucune valeur disponible.")
            return sel
        b1, b2 = st.columns(2)
        with b1:
            st.button("Tout", key=f"{prefix}__all", icon=":material/done_all:", use_container_width=True,
                      on_click=_ck_all, args=(state_key, prefix, options, True))
        with b2:
            st.button("Aucun", key=f"{prefix}__none", icon=":material/remove_done:", use_container_width=True,
                      on_click=_ck_all, args=(state_key, prefix, options, False))
        ncol = 3 if len(options) > 14 else (2 if len(options) > 6 else 1)
        cols = st.columns(ncol)
        for i, o in enumerate(options):
            k = f"{prefix}__{o}"
            st.session_state[k] = o in sel          # la liste mémorisée fait foi
            with cols[i % ncol]:
                st.checkbox(fmt(o), key=k, on_change=_ck_sync, args=(state_key, prefix, options))
    return st.session_state[state_key]

def period_filter(title, d_min, d_max, prefix):
    """Période : choix rapide à cocher, dates libres seulement en mode personnalisé."""
    from datetime import timedelta as _tdp
    presets = ["Tout", "7 derniers jours", "30 derniers jours", "3 derniers mois", "Cette année", "Personnalisée"]
    cur = st.session_state.get(f"{prefix}_preset", "Tout")
    with st.popover(f"{title} · {cur}", icon=":material/date_range:", use_container_width=True):
        cur = st.radio(title, presets, key=f"{prefix}_preset", label_visibility="collapsed")
        if cur == "Personnalisée":
            d1, d2 = st.columns(2)
            with d1: f = st.date_input("Depuis", value=d_min, key=f"{prefix}_from")
            with d2: t = st.date_input("Jusqu'au", value=d_max, key=f"{prefix}_to")
    today = date.today()
    if cur == "Personnalisée":
        return st.session_state.get(f"{prefix}_from", d_min), st.session_state.get(f"{prefix}_to", d_max)
    start = {"7 derniers jours": today - _tdp(days=6), "30 derniers jours": today - _tdp(days=29),
             "3 derniers mois": today - _tdp(days=91), "Cette année": date(today.year, 1, 1)}.get(cur, d_min)
    return min(start, d_max) if cur == "Tout" else start, max(d_max, today)

def kpi(icon, label, value, sub, color, kind=None):
    """Carte KPI dont la forme suit l'information : montant (feuille), ratio (capsule + jauge), risque (angles coupés)."""
    import re as _rek
    lab = str(label).lower()
    if kind is None:
        if any(w in lab for w in ("drawdown", "perte max", "risque", "perdants", "pire")):
            kind = "risk"
        elif any(w in lab for w in ("rate", "factor", "r:r", "ratio", "%", "taux", "réussite")) or str(value).strip().endswith(("%", "R")):
            kind = "ratio"
        else:
            kind = "money"
    deco = f'<div class="kpi-icon" style="color:{color}">{icon}</div>'
    _m = _rek.match(r"^\s*([\d.,]+)\s*%\s*$", str(value))
    if kind == "ratio" and _m:
        try:
            pv = max(0.0, min(100.0, float(_m.group(1).replace(",", "."))))
            deco = (f'<div class="kpi-ring" style="background:conic-gradient({color} {pv:.0f}%,'
                    f'var(--tj-border) 0)"></div>')
        except Exception:
            pass
    st.markdown(f"""<div class="kpi kpi-{kind}">
        <div class="kpi-bar" style="background:{color}"></div>
        {deco}
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color}">{value}</div>
        <div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

def badge(text, cls): return f'<span class="badge {cls}">{text}</span>'
def mode_badge_class(m):
    return "badge"  # conservé pour compat ; les badges de compte sont désormais colorés dynamiquement

def ev(key, default):
    ex = next((t for t in st.session_state.trades if t["id"]==st.session_state.edit_id), None)
    return ex[key] if ex else default

def safe_float(val):
    try: return float(str(val).replace(" ","").replace(",",".").strip() or 0)
    except: return 0.0

# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTIFICATION & PERMISSIONS PAR COMPTE
# Les utilisateurs sont stockés dans journal_data (key='users'). Seul l'admin
# crée les comptes et choisit, pour chacun, les comptes de trading visibles.
# ══════════════════════════════════════════════════════════════════════════════
def _users_ep():
    return f"{SB_URL}/rest/v1/journal_data?key=eq.users"

def hash_password(password, salt=None):
    if salt is None:
        salt = _secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"

def verify_password(password, stored):
    try:
        salt, _ = str(stored).split("$", 1)
        return hash_password(password, salt) == stored
    except Exception:
        return False

def users_load():
    if not _sb_ready():
        return st.session_state.get("_local_users", [])
    try:
        r = requests.get(f"{SB_EP}?key=eq.users&select=value", headers=SB_HDR, timeout=10)
        if r.status_code == 200 and r.json():
            val = r.json()[0].get("value", [])
            return val if isinstance(val, list) else []
    except Exception:
        pass
    return []

def users_save(users):
    if not _sb_ready():
        st.session_state["_local_users"] = users
        return False
    try:
        r = requests.patch(f"{SB_EP}?key=eq.users",
            headers={**SB_HDR, "Prefer": "return=representation"},
            json={"value": users, "updated_at": "now()"}, timeout=15)
        if r.status_code == 200 and isinstance(r.json(), list) and r.json():
            return True
        if r.status_code == 204:
            return True
        r2 = requests.post(SB_EP,
            headers={**SB_HDR, "Prefer": "resolution=merge-duplicates,return=representation"},
            json={"key": "users", "value": users}, timeout=15)
        return r2.status_code in (200, 201)
    except Exception:
        return False

def bootstrap_admin():
    """Crée l'admin initial depuis les secrets si aucun utilisateur n'existe."""
    users = users_load()
    if users:
        return users
    admin_user = st.secrets.get("ADMIN_USERNAME", os.environ.get("ADMIN_USERNAME", "admin"))
    admin_pass = st.secrets.get("ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "admin123"))
    users = [{
        "username": admin_user,
        "password_hash": hash_password(admin_pass),
        "role": "admin",
        "accounts": list(TRADE_MODES),
        "active": True,
    }]
    users_save(users)
    return users

def authenticate(username, password):
    users = bootstrap_admin()
    u = next((x for x in users if x.get("username") == username), None)
    if not u:
        return False, None, "Identifiants incorrects."
    if not u.get("active", True):
        return False, None, "Compte désactivé. Contactez l'administrateur."
    if verify_password(password, u.get("password_hash", "")):
        return True, u, "OK"
    return False, None, "Identifiants incorrects."

def allowed_accounts():
    """Comptes de trading que l'utilisateur connecté a le droit de voir."""
    if st.session_state.get("auth_role") == "admin":
        return list(TRADE_MODES)
    acc = st.session_state.get("auth_accounts", [])
    return [a for a in acc if a in TRADE_MODES]

def user_mode_options():
    """Options du filtre 'Afficher' selon les droits (≥2 comptes → + 'Tous')."""
    allowed = allowed_accounts()
    return (["Tous"] + allowed) if len(allowed) >= 2 else allowed

def logout():
    for k in ("auth_user", "auth_role", "auth_accounts"):
        st.session_state.pop(k, None)
    st.rerun()

def _logo_svg(c, sz):
    return (f"<svg width='{sz}' height='{sz}' viewBox='0 0 24 24' fill='none' stroke='{c}' stroke-width='2.4' "
            f"stroke-linecap='round' stroke-linejoin='round'><polyline points='3 17 9 11 13 15 21 7'/>"
            f"<polyline points='15 7 21 7 21 13'/></svg>")

def login_gate():
    """Affiche le formulaire de connexion. Retourne True si connecté."""
    if st.session_state.get("auth_user"):
        return True
    _t = THEMES[LOGIN_THEME]          # design unique pour la page de connexion
    st.markdown(build_css(_t), unsafe_allow_html=True)
    st.markdown(f"""<style>
.block-container {{ padding-top:3rem; max-width:1100px; }}
.stApp {{ background:
    radial-gradient(1100px 520px at 12% -10%, {_t['accent']}2e, transparent 60%),
    radial-gradient(900px 480px at 108% 8%, {_t['alt']}26, transparent 55%),
    radial-gradient(700px 400px at 50% 115%, {_t['orange']}14, transparent 60%),
    linear-gradient(160deg, {_t['bg']} 0%, {_t['bg2']} 60%, {_t['bg']} 100%) !important;
    background-attachment:fixed; }}
div[data-testid="stForm"] {{
    background:linear-gradient(160deg, {_t['card']}f2, {_t['bg2']}f2);
    border:1px solid {_t['border']}; border-radius:20px; padding:28px 30px 22px;
    position:relative; overflow:hidden; backdrop-filter:blur(8px);
    box-shadow:0 24px 70px rgba(0,0,0,.35), 0 0 0 1px {_t['accent']}14; }}
div[data-testid="stForm"]::before {{ content:''; position:absolute; top:0; left:0; right:0;
    height:4px; background:linear-gradient(90deg,{_t['accent']},{_t['alt']},{_t['orange']}); }}
div[data-testid="stForm"] input {{ padding:12px 14px !important; border-radius:10px !important;
    font-size:14px !important; }}
div[data-testid="stForm"] button {{ padding:11px 0 !important; font-size:14px !important;
    letter-spacing:.4px; margin-top:6px; }}
.tj-feat {{ display:flex; gap:10px; align-items:flex-start; margin-bottom:16px; }}
.tj-feat i {{ width:34px; height:34px; border-radius:10px; display:inline-flex; align-items:center;
    justify-content:center; background:{_t['accent']}1f; color:{_t['accent']}; flex-shrink:0; }}
.tj-feat b {{ color:{_t['text']}; font-size:13px; }}
.tj-feat span {{ color:{_t['muted']}; font-size:12px; }}
</style>""", unsafe_allow_html=True)

    # En-tête de marque
    st.markdown(
        f"<div style='text-align:center;padding:4px 0 26px'>"
        f"<div style='display:inline-flex;align-items:center;justify-content:center;width:68px;"
        f"height:68px;border-radius:20px;background:linear-gradient(135deg,{_t['accent']},{_t['alt']});"
        f"box-shadow:0 14px 34px {_t['accent']}55;margin-bottom:14px'>"
        + _logo_svg(_t['btn_text'], 30) + "</div>"
        f"<div style='font-size:32px;font-weight:800;letter-spacing:-.6px;color:{_t['text']}'>"
        f"Trading Journal <span class='grad-accent'>Pro</span></div>"
        f"<div style='color:{_t['muted']};font-size:13px;margin-top:6px'>"
        f"Performance, analytics et biais macro dans un seul poste de pilotage</div></div>",
        unsafe_allow_html=True)

    cleft, cright = st.columns([1.05, 1], gap="large")
    with cleft:
        st.markdown(
            f"<div style='padding:18px 6px 0 6px'>"
            f"<div class='tj-feat'><i class='fa-solid fa-gauge-high'></i><div><b>Dashboard temps réel</b><br>"
            f"<span>P&amp;L, win rate, drawdown et courbe de capital par compte.</span></div></div>"
            f"<div class='tj-feat'><i class='fa-solid fa-calendar-days'></i><div><b>Calendrier &amp; heatmaps</b><br>"
            f"<span>Résultats par jour, semaine, mois et heure de prise de position.</span></div></div>"
            f"<div class='tj-feat'><i class='fa-solid fa-newspaper'></i><div><b>Scorecard &amp; news</b><br>"
            f"<span>Consensus vs publié et impact estimé sur vos actifs (GMT+1).</span></div></div>"
            f"<div class='tj-feat'><i class='fa-solid fa-user-shield'></i><div><b>Accès multi-comptes</b><br>"
            f"<span>Permissions par utilisateur, comptes démo, réels et institutionnels.</span></div></div>"
            f"</div>", unsafe_allow_html=True)
    with cright:
        with st.form("login_form"):
            st.markdown(
                f"<div style='font-size:17px;font-weight:800;color:{_t['text']}'>"
                f"<i class='fa-solid fa-lock' style='color:{_t['accent']};margin-right:8px'></i>"
                f"Connexion sécurisée</div>"
                f"<div style='font-size:12px;color:{_t['muted']};margin:2px 0 10px'>"
                f"Identifiez-vous pour accéder à votre journal</div>", unsafe_allow_html=True)
            u = st.text_input("Utilisateur", placeholder="Nom d'utilisateur")
            p = st.text_input("Mot de passe", type="password", placeholder="••••••••")
            if st.form_submit_button("Se connecter", use_container_width=True, type="primary"):
                ok, user, msg = authenticate(u.strip(), p)
                if ok:
                    st.session_state.auth_user = user["username"]
                    st.session_state.auth_role = user.get("role", "user")
                    st.session_state.auth_accounts = user.get("accounts", [])
                    # Compte affiché par défaut à l'ouverture : Réel Indépendant (s'il est autorisé)
                    try:
                        _def_acc = [a for a in allowed_accounts() if a == DEFAULT_ACCOUNT]
                    except Exception:
                        _def_acc = []
                    st.session_state.mode_selection = _def_acc
                    st.rerun()
                else:
                    st.error(msg)
        st.markdown(
            f"<div style='text-align:center;margin-top:12px;font-size:11px;color:{_t['muted']}'>"
            f"<i class='fa-solid fa-shield-halved' style='margin-right:5px'></i>"
            f"Mots de passe chiffrés (PBKDF2-SHA256) · Accès sur invitation de l'administrateur</div>",
            unsafe_allow_html=True)
    return False

# ════════════════════════════════════════════════════════════════════════════
# CALENDRIER ÉCONOMIQUE (module) : utilisé par News & Analyse ET le chronomètre global
# ════════════════════════════════════════════════════════════════════════════
USER_TZ_OFFSET = 1  # GMT+1 (position géographique de l'utilisateur)

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
_CC2CCY = {"US": "USD", "EU": "EUR", "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR",
           "NL": "EUR", "GB": "GBP", "UK": "GBP", "JP": "JPY", "CH": "CHF", "CA": "CAD",
           "AU": "AUD", "NZ": "NZD", "CN": "CNY"}

def _tv_fmt(v, scale, unit):
    if v is None or v == "": return ""
    try: x = float(v)
    except Exception: return str(v)
    s = f"{int(x)}" if x == int(x) else f"{x:.2f}".rstrip("0").rstrip(".")
    if scale in ("K", "M", "B", "T"): s += scale
    if unit == "%": s += "%"
    return s

def _extract_json_object(s, start):
    """Depuis l'index d'un '{', renvoie la sous-chaîne JSON équilibrée (quote-aware)."""
    depth = 0; in_str = False; esc = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0: return s[start:i + 1]
    return None

def _ff_impact(ev):
    blob = (str(ev.get("impactTitle", "")) + " " + str(ev.get("impactClass", "")) + " "
            + str(ev.get("impactName", ""))).lower()
    if "red" in blob or "high" in blob: return "High"
    if "ora" in blob or "medium" in blob: return "Medium"
    if "yel" in blob or "low" in blob: return "Low"
    return "Low"

def _fetch_calendar_raw(scope="all"):
    """Renvoie (events, source). events normalisés avec 'actual' si la source le fournit.
    Ordre des sources : TradingView (Actual) -> ForexFactory (Actual) -> faireconomy (prévisions)."""
    import json as _json
    from datetime import timedelta as _tdd
    today = datetime.utcnow()
    if scope == "lastweek":   dfrom, dto = today - _tdd(days=9), today
    elif scope == "thisweek": dfrom, dto = today - _tdd(days=3), today + _tdd(days=4)
    elif scope == "nextweek": dfrom, dto = today + _tdd(days=1), today + _tdd(days=9)
    elif scope == "rates":    dfrom, dto = today - _tdd(days=400), today + _tdd(days=70)
    else:                     dfrom, dto = today - _tdd(days=16), today + _tdd(days=9)

    # ── Source 1 : TradingView (calendrier avec Actual) ──────────────────
    try:
        h = dict(_UA); h["Origin"] = "https://www.tradingview.com"
        h["Referer"] = "https://www.tradingview.com/"
        params = {"from": dfrom.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                  "to":   dto.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                  "countries": "US,EU,GB,JP,CH,CA,AU,NZ,CN,DE,FR,IT,ES"}
        r = requests.get("https://economic-calendar.tradingview.com/events",
                         params=params, headers=h, timeout=12)
        if r.status_code == 200:
            data = r.json()
            res = data.get("result", data if isinstance(data, list) else [])
            _imp = {1: "High", 0: "Medium", -1: "Low"}
            out = []
            for ev in res:
                ccy = _CC2CCY.get(str(ev.get("country", "")).upper())
                if not ccy: continue
                out.append({
                    "title": str(ev.get("title") or ev.get("indicator") or ""),
                    "country": ccy,
                    "impact": _imp.get(ev.get("importance", 0), "Medium"),
                    "actual": _tv_fmt(ev.get("actual"), ev.get("scale", ""), ev.get("unit", "")),
                    "forecast": _tv_fmt(ev.get("forecast"), ev.get("scale", ""), ev.get("unit", "")),
                    "previous": _tv_fmt(ev.get("previous"), ev.get("scale", ""), ev.get("unit", "")),
                    "date": str(ev.get("date", "")),
                })
            if out:
                return out, "TradingView"
    except Exception:
        pass

    # ── Source 2 : ForexFactory (page HTML, contient l'Actual) ───────────
    try:
        ffmap = {"lastweek": "last", "thisweek": "this", "nextweek": "next"}
        weeks = ["last", "this", "next"] if scope == "all" else [ffmap.get(scope, "this")]
        out, seen = [], set()
        for wk in weeks:
            try:
                r = requests.get(f"https://www.forexfactory.com/calendar?week={wk}",
                                 headers=_UA, timeout=12)
                if r.status_code != 200: continue
                html = r.text; pos = 0
                while True:
                    mk = html.find("calendarComponentStates[", pos)
                    if mk == -1: break
                    eq = html.find("=", mk); br = html.find("{", eq)
                    if eq == -1 or br == -1: break
                    obj = _extract_json_object(html, br)
                    pos = (br + len(obj)) if obj else (mk + 25)
                    if not obj: continue
                    try: state = _json.loads(obj)
                    except Exception: continue
                    for day in (state.get("days") or []):
                        for ev in (day.get("events") or []):
                            name = ev.get("name") or ev.get("eventName") or ""
                            cur = ev.get("currency") or ""
                            if not name or not cur: continue
                            dl = ev.get("dateline")
                            try:
                                iso = (datetime.utcfromtimestamp(int(dl))
                                       .strftime("%Y-%m-%dT%H:%M:%S+00:00")) if dl else ""
                            except Exception:
                                iso = ""
                            key = (str(name), iso, str(cur))
                            if key in seen: continue
                            seen.add(key)
                            out.append({
                                "title": str(name), "country": str(cur),
                                "impact": _ff_impact(ev),
                                "actual": str(ev.get("actual", "") or ""),
                                "forecast": str(ev.get("forecast", "") or ""),
                                "previous": str(ev.get("previous", "") or ""),
                                "date": iso,
                            })
            except Exception:
                continue
        if out:
            return out, "ForexFactory"
    except Exception:
        pass

    # ── Source 3 : faireconomy (prévisions seules, pas d'Actual) ─────────
    try:
        base = "https://nfs.faireconomy.media/ff_calendar_{}.json"
        scopes = ["lastweek", "thisweek", "nextweek"] if scope == "all" else [scope]
        out, seen = [], set()
        for sc in scopes:
            try:
                r = requests.get(base.format(sc), timeout=12, headers=_UA)
                if r.status_code == 200:
                    for ev in r.json():
                        key = (str(ev.get("title", "")), str(ev.get("date", "")),
                               str(ev.get("country", ev.get("currency", ""))))
                        if key in seen: continue
                        seen.add(key)
                        out.append({
                            "title": str(ev.get("title", "")),
                            "country": str(ev.get("country", ev.get("currency", ""))),
                            "impact": str(ev.get("impact", "")),
                            "actual": "",
                            "forecast": str(ev.get("forecast", ev.get("estimate", "")) or ""),
                            "previous": str(ev.get("previous", ev.get("prior", "")) or ""),
                            "date": str(ev.get("date", "")),
                        })
            except Exception:
                pass
        return out, "faireconomy (prévisions, sans chiffre publié)"
    except Exception:
        return [], "aucune"


@st.cache_data(ttl=1800, show_spinner=False, max_entries=12)
def _fetch_calendar_cached(scope, bucket):
    """Cache par tranche de temps : 30 min au calme, 1 min autour d'une annonce (voir calendar_hot)."""
    import time as _tmc
    ev, src = _fetch_calendar_raw(scope)
    return ev, src, _tmc.time()

def _calendar_hot(events, now_utc=None):
    """Instant (epoch) jusqu'auquel rafraîchir à la minute : annonce dans moins de 20 min,
    ou publiée depuis moins de 90 min sans chiffre encore récupéré."""
    from datetime import timezone as _tzh
    now = now_utc or datetime.utcnow()
    until = 0.0
    for ev in events or []:
        if str(ev.get("impact", "")) not in ("High", "Medium"):
            continue
        dt = _parse_utc(ev.get("date"))
        if dt is None:
            continue
        dmin = (dt - now).total_seconds() / 60
        no_actual = str(ev.get("actual", "")).strip() in ("", "nan", "None")
        if (0 < dmin <= 20) or (no_actual and -90 <= dmin <= 0):
            until = max(until, dt.replace(tzinfo=_tzh.utc).timestamp() + 90 * 60)
    return until

def _fetch_calendar(scope="all"):
    """Calendrier économique : (events, source). Rafraîchi à la minute autour des annonces."""
    import time as _tmc
    now = _tmc.time()
    hot_key = f"_cal_hot_{scope}"
    hot = st.session_state.get(hot_key, 0) > now if hasattr(st, "session_state") else False
    retry = st.session_state.get(f"_cal_empty_{scope}", 0) > now     # dernier essai vide : on retente vite
    bucket = int(now // 60) if hot else (int(now // 120) if retry else int(now // 1800))
    ev, src, ts = _fetch_calendar_cached(scope, bucket)
    try:
        st.session_state[f"_cal_empty_{scope}"] = (now + 1800) if not ev else 0
    except Exception:
        pass
    # ne jamais revenir à une version plus ancienne que celle déjà affichée (cache 30 min resté figé)
    _last = st.session_state.get(f"_cal_data_{scope}")
    if _last and _last[2] > ts:
        ev, src, ts = _last
    else:
        st.session_state[f"_cal_data_{scope}"] = (ev, src, ts)
    try:
        st.session_state[hot_key] = _calendar_hot(ev) if "sans chiffre publié" not in src else 0
        st.session_state[f"_cal_ts_{scope}"] = ts
    except Exception:
        pass
    return ev, src

def _to_num(x):
    if x is None: return None
    s = str(x).strip().replace("%", "").replace(",", "")
    if s in ("", "nan", "None"): return None
    mult = 1.0
    if s[-1:].upper() == "K": mult, s = 1e3, s[:-1]
    elif s[-1:].upper() == "M": mult, s = 1e6, s[:-1]
    elif s[-1:].upper() == "B": mult, s = 1e9, s[:-1]
    elif s[-1:].upper() == "T": mult, s = 1e12, s[:-1]
    try: return float(s) * mult
    except: return None

def _fmt_local(iso):
    """Convertit l'horodatage ForexFactory (UTC/offset) en GMT+1."""
    if not iso: return ("", None)
    try:
        s = str(iso).replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            from datetime import timezone
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        dt = dt + __import__("datetime").timedelta(hours=USER_TZ_OFFSET)
        _jf = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"][dt.weekday()]
        return (f"{_jf} " + dt.strftime("%d/%m · %H:%M"), dt)
    except Exception:
        return (str(iso)[:16].replace("T", " "), None)



def _parse_utc(iso):
    """Horodatage ISO (avec ou sans offset) -> datetime UTC naïf, ou None."""
    if not iso:
        return None
    try:
        from datetime import timezone as _tzu
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(_tzu.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None

def upcoming_major_events(ccys, impacts, horizon_h=168, past_min=15):
    """Annonces à venir regroupées par horaire : [{t (ms UTC), titles, ccys, local}]."""
    try:
        evs, _src = _fetch_calendar("all")
    except Exception:
        return []
    from datetime import timezone as _tzu
    now = datetime.utcnow(); groups = {}
    for ev in evs or []:
        c = str(ev.get("country", "")); imp = str(ev.get("impact", ""))
        if (ccys and c not in ccys) or (impacts and imp not in impacts):
            continue
        dt = _parse_utc(ev.get("date"))
        if dt is None:
            continue
        dsec = (dt - now).total_seconds()
        if dsec < -past_min * 60 or dsec > horizon_h * 3600:
            continue
        g = groups.setdefault(dt, {"t": int(dt.replace(tzinfo=_tzu.utc).timestamp() * 1000),
                                   "titles": [], "ccys": [], "local": _fmt_local(ev.get("date"))[0]})
        if ev.get("title") not in g["titles"]:
            g["titles"].append(str(ev.get("title", "")))
        if c not in g["ccys"]:
            g["ccys"].append(c)
    return [groups[k] for k in sorted(groups)]

def _cd_next(groups, now_ms=None):
    """Prochaine annonce encore pertinente (jusqu'à 10 min après l'heure)."""
    import time as _tm
    now_ms = now_ms if now_ms is not None else _tm.time() * 1000
    return next((g for g in groups or [] if g["t"] > now_ms - 10 * 60 * 1000), None)

def _cd_open():
    """Clic sur la sphère : ouvre l'annonce dans Analyse & News."""
    g = _cd_next(st.session_state.get("_cd_groups"))
    if g:
        st.session_state.focus_event = {"titles": list(g["titles"]), "t": g["t"]}
        st.session_state.page = "analyse"

def render_countdown(groups, window_h, t):
    """Sphère flottante : compte à rebours de la prochaine annonce majeure (JS, sans rechargement).
    Un clic ouvre la fiche de l'annonce dans Analyse & News (bouton Streamlit caché)."""
    import streamlit.components.v1 as _components
    if not _cd_next(groups):
        return
    st.session_state["_cd_groups"] = groups[:15]
    data = json.dumps(groups[:15], ensure_ascii=True).replace("</", "<\\/")
    st.markdown(
        "<style>.st-key-cd_sphere{position:fixed!important;right:20px;bottom:120px;z-index:9990;"
        "width:96px!important;height:96px;pointer-events:none}"
        ".st-key-cd_sphere iframe{pointer-events:auto;border-radius:50%}"
        ".st-key-cd_sphere [data-testid=stElementContainer]{width:96px!important}"
        ".st-key-cd_go{position:fixed!important;left:-10000px;top:0;width:1px;height:1px;overflow:hidden}"
        "</style>", unsafe_allow_html=True)
    with st.container(key="cd_go"):
        st.button("ouvrir l'annonce", key="cd_go_btn", on_click=_cd_open)
    html_c = """
<div id="sp" title=""><svg viewBox="0 0 100 100"><circle class="tr" cx="50" cy="50" r="45"/>
<circle id="ring" class="rg" cx="50" cy="50" r="45"/></svg>
<div class="in"><div id="cc" class="cc"></div><div id="tm" class="tm"></div><div id="lb" class="lb"></div></div></div>
<style>
 html,body{margin:0;background:transparent;overflow:hidden;font-family:Inter,-apple-system,Segoe UI,Roboto,Arial,sans-serif}
 #sp{position:relative;width:88px;height:88px;margin:4px;border-radius:50%;cursor:pointer;
     background:radial-gradient(circle at 32% 28%,__CARD__ 0%,__BG__ 100%);
     box-shadow:0 6px 20px rgba(0,0,0,.35),inset 0 0 0 1px __BORDER__;transition:transform .2s}
 #sp:hover{transform:scale(1.06)}
 #sp.pulse{animation:p 1.1s infinite}
 @keyframes p{0%{box-shadow:0 0 0 0 var(--c),0 6px 20px rgba(0,0,0,.35)}70%{box-shadow:0 0 0 12px transparent,0 6px 20px rgba(0,0,0,.35)}100%{box-shadow:0 0 0 0 transparent,0 6px 20px rgba(0,0,0,.35)}}
 svg{position:absolute;inset:0;transform:rotate(-90deg)}
 .tr{fill:none;stroke:__BORDER__;stroke-width:5}
 .rg{fill:none;stroke:var(--c);stroke-width:5;stroke-linecap:round;stroke-dasharray:282.7;transition:stroke-dashoffset 1s linear}
 .in{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
 .cc{font-size:10px;font-weight:800;letter-spacing:.6px;color:__TEXT__}
 .tm{font-family:"JetBrains Mono",Consolas,monospace;font-size:16px;font-weight:800;color:var(--c);line-height:1.15}
 .lb{font-size:8.5px;text-transform:uppercase;letter-spacing:.7px;font-weight:700;color:__MUTED__}
</style>
<script>
const G=__DATA__, WIN=__WIN__, C={acc:"__ACCENT__",ora:"__ORANGE__",loss:"__LOSS__",mut:"__MUTED__"};
const p=n=>String(n).padStart(2,"0");
function short(ms){const s=Math.floor(Math.abs(ms)/1000),h=Math.floor(s/3600),m=Math.floor(s%3600/60),x=s%60;
  if(h>=48)return Math.floor(h/24)+"j";if(h>=1)return h+"h"+p(m);return p(m)+":"+p(x);}
const sp=document.getElementById("sp"), ring=document.getElementById("ring");
sp.addEventListener("click",()=>{try{const b=window.parent.document.querySelector('.st-key-cd_go button');if(b)b.click();}catch(e){}});
function tick(){
  const now=Date.now(), g=G.find(x=>x.t>now-10*60*1000);
  if(!g){sp.style.display="none";return;}
  const rem=g.t-now; let c=C.mut, lab="dans", frac=0, pulse=false;
  if(rem<=0){c=C.loss;lab="en cours";frac=1;pulse=true;}
  else if(rem<=WIN){frac=1-rem/WIN; c=rem<=5*60000?C.loss:(rem<=30*60000?C.ora:C.acc); pulse=rem<=5*60000;}
  sp.style.setProperty("--c",c); sp.className=pulse?"pulse":"";
  ring.style.strokeDashoffset=(282.7*(1-Math.max(0.03,frac))).toFixed(1);
  document.getElementById("cc").textContent=g.ccys.slice(0,2).join("·");
  document.getElementById("tm").textContent=(rem<=0?"+":"")+short(rem);
  document.getElementById("lb").textContent=lab;
  sp.title=g.titles.join(" / ")+"\\n"+g.local+" (GMT+1)\\nCliquer pour ouvrir l'annonce";
}
tick(); setInterval(tick,1000);
</script>"""
    for k, v in {"__DATA__": data, "__WIN__": str(int(window_h * 3600 * 1000)),
                 "__CARD__": t["card"], "__BG__": t["bg"], "__BORDER__": t["border"], "__TEXT__": t["text"],
                 "__MUTED__": t["muted"], "__ACCENT__": t["accent"], "__ORANGE__": t["orange"],
                 "__LOSS__": t["loss"]}.items():
        html_c = html_c.replace(k, v)
    with st.container(key="cd_sphere"):
        _components.html(html_c, height=96, width=96)


# Porte d'authentification : rien ne s'affiche tant qu'on n'est pas connecté
if not login_gate():
    st.stop()


# ── SIDEBAR ────────────────────────────────────────────────────────────────────
# ── INJECTION CSS (avant le header pour que le thème s'applique) ─────────────────
st.markdown(build_css(get_theme()), unsafe_allow_html=True)
if "bg_name" not in st.session_state:
    st.session_state.bg_name = DEFAULT_BG if DEFAULT_BG in BACKGROUNDS else "Aucun"
if st.session_state.bg_name not in BACKGROUNDS:
    st.session_state.bg_name = "Aucun"
st.markdown(background_css(get_theme(), st.session_state.bg_name), unsafe_allow_html=True)

# ── EN-TÊTE MASQUABLE (panneau animé + navigation en onglets thémés) ─────────────
_thd = get_theme()
df_side = get_df()
total   = df_side["pnl"].sum() if not df_side.empty else 0
wr      = (len(df_side[df_side["pnl"]>0])/len(df_side)*100) if not df_side.empty else 0
col_pnl = _thd["win"] if total >= 0 else _thd["loss"]
if "hdr_open" not in st.session_state:
    st.session_state.hdr_open = True

_NAV = [
    ("dashboard", "Dashboard",  ":material/space_dashboard:"),
    ("journal",   "Journal",    ":material/table_rows:"),
]
if is_admin():
    _NAV += [
        ("add",     "Nouveau",    ":material/add_circle:"),
        ("import",  "Import MT5", ":material/upload_file:"),
    ]
_NAV += [
    ("analyse",   "Analyse & News", ":material/newspaper:"),
    ("calendar",  "Calendrier", ":material/calendar_month:"),
    ("sessions",  "Sessions", ":material/schedule:"),
    ("captures",  "Captures", ":material/image:"),
]
if is_admin():
    _NAV += [("users", "Utilisateurs", ":material/manage_accounts:")]

# Garde-fou : une page réservée admin demandée par un non-admin retombe sur dashboard
if not is_admin() and st.session_state.page in ("add", "import", "users"):
    st.session_state.page = "dashboard"
if st.session_state.page not in [k for k, _, _ in _NAV]:
    st.session_state.page = "dashboard"

# Comptes autorisés : nettoyage de la sélection, que le panneau soit ouvert ou non
_allowed = allowed_accounts()
if "mode_selection" not in st.session_state:
    st.session_state.mode_selection = [a for a in _allowed if a == DEFAULT_ACCOUNT]
st.session_state.mode_selection = [m for m in st.session_state.mode_selection if m in _allowed]
if len(_allowed) <= 1:
    st.session_state.mode_selection = list(_allowed)

def _nav_go(k):
    st.session_state.page = k
    st.session_state.edit_id = None

def _hdr_toggle():
    st.session_state.hdr_open = not st.session_state.hdr_open

def _render_nav(prefix):
    for k, lbl, ic in _NAV:
        st.button(lbl, key=f"{prefix}_{k}", icon=ic, on_click=_nav_go, args=(k,),
                  type=("primary" if k == st.session_state.page else "secondary"))

_t = _thd
_nav_btn = '[class*="st-key-tjnav_"] button, [class*="st-key-tjmnav_"] button'
_stagger = "".join(f".st-key-tj_nav > div:nth-child({i}){{animation-delay:{0.06 + i*0.035:.3f}s}}"
                   for i in range(1, 13))
st.markdown(f"""<style>
@keyframes tjDrop {{ 0% {{opacity:0; transform:translateY(-18px) scale(.985); filter:blur(3px)}}
                     100% {{opacity:1; transform:none; filter:none}} }}
@keyframes tjRise {{ 0% {{opacity:0; transform:translateY(10px)}} 100% {{opacity:1; transform:none}} }}
@keyframes tjSweep {{ 0% {{background-position:200% 0}} 100% {{background-position:0 0}} }}
@keyframes tjPop {{ 0% {{opacity:0; transform:scale(.6)}} 100% {{opacity:1; transform:none}} }}
.st-key-tj_hdr {{
  position:relative; overflow:hidden; border-radius:30px 30px 30px 8px; padding:14px 18px 12px;
  background:linear-gradient(145deg,{_t['card']},{_t['bg2']}); border:1px solid {_t['border']};
  box-shadow:0 1px 2px rgba(0,0,0,.06), 0 14px 34px rgba(0,0,0,.10);
  animation:tjDrop .55s cubic-bezier(.22,1,.36,1) both; }}
.st-key-tj_hdr::before {{ content:""; position:absolute; top:0; left:0; right:0; height:3px;
  background:linear-gradient(90deg,{_t['accent']},{_t['alt']},{_t['orange']},{_t['accent']});
  background-size:200% 100%; animation:tjSweep 1.4s ease-out both; }}
.st-key-tj_hdr_min {{
  border-radius:14px; padding:6px 8px; background:{_t['card']}; border:1px solid {_t['border']};
  box-shadow:0 6px 18px rgba(0,0,0,.07); animation:tjRise .35s cubic-bezier(.22,1,.36,1) both; }}
/* Piste d'onglets segmentée */
.st-key-tj_nav {{ background:{_t['bg2']}; border:1px solid {_t['border']}; border-radius:14px;
  padding:5px; gap:4px !important; margin-top:4px; }}
.st-key-tj_nav > div {{ animation:tjRise .45s cubic-bezier(.22,1,.36,1) both; }}
{_stagger}
{_nav_btn} {{
  background:transparent !important; border:1px solid transparent !important; box-shadow:none !important;
  color:{_t['muted']} !important; border-radius:10px !important; min-height:36px !important;
  padding:5px 13px !important; font-weight:600 !important; transition:all .18s ease !important; }}
{_nav_btn.replace(' button', ' button:hover')} {{
  background:{_t['accent']}14 !important; border-color:{_t['accent']}33 !important;
  color:{_t['text']} !important; transform:translateY(-1px); filter:none !important; }}
[class*="st-key-tjnav_"] button[kind="primary"], [class*="st-key-tjmnav_"] button[kind="primary"] {{
  background:linear-gradient(135deg,{_t['accent']},{_t['alt']}) !important; color:{_t['btn_text']} !important;
  box-shadow:0 6px 16px {_t['accent']}40 !important; animation:tjPop .3s ease-out both; }}
[class*="st-key-tjnav_"] button p, [class*="st-key-tjmnav_"] button p {{
  font-size:13px !important; color:inherit !important; margin:0 !important; }}
[class*="st-key-tjnav_"] button [data-testid="stIconMaterial"], [class*="st-key-tjmnav_"] button [data-testid="stIconMaterial"] {{
  font-size:18px !important; color:inherit !important; }}
[class*="st-key-tjnav_"] button[kind="primary"] *, [class*="st-key-tjmnav_"] button[kind="primary"] * {{
  color:{_t['btn_text']} !important; }}
/* Boutons d'action ronds (synchro, déconnexion, masquer/afficher) */
.st-key-hdr_sync button, .st-key-hdr_logout button, .st-key-hdr_toggle button, .st-key-hdr_show button {{
  background:{_t['bg2']} !important; color:{_t['muted']} !important; border:1px solid {_t['border']} !important;
  box-shadow:none !important; border-radius:11px !important; min-height:38px !important; padding:4px 10px !important;
  transition:all .18s ease !important; }}
.st-key-hdr_sync button:hover, .st-key-hdr_logout button:hover, .st-key-hdr_toggle button:hover, .st-key-hdr_show button:hover {{
  color:{_t['accent']} !important; border-color:{_t['accent']}66 !important; transform:translateY(-1px); }}
.st-key-hdr_show button {{ background:linear-gradient(135deg,{_t['accent']},{_t['alt']}) !important;
  color:{_t['btn_text']} !important; border:none !important; }}
.st-key-hdr_show button * {{ color:{_t['btn_text']} !important; }}
.st-key-tj_hdr_min [class*="st-key-tjmnav_"] button {{ padding:3px 9px !important; min-height:32px !important; }}
.st-key-tj_hdr_min [class*="st-key-tjmnav_"] button p {{ font-size:12px !important; }}
.st-key-tj_hdr_min [class*="st-key-tjmnav_"] button [data-testid="stIconMaterial"] {{ font-size:16px !important; }}
.st-key-tj_hdr_min {{ gap:2px !important; }}
.tj-cap {{ display:flex; gap:18px; align-items:baseline; flex-wrap:wrap; padding:2px 2px 4px; animation:tjRise .5s .1s both; }}
</style>""", unsafe_allow_html=True)

_role_lbl = "Admin" if is_admin() else "Utilisateur"
_brand = (f"<div style='display:flex;align-items:center;gap:10px'>"
          f"<span style='display:inline-flex;align-items:center;justify-content:center;width:34px;height:34px;"
          f"border-radius:10px;background:linear-gradient(135deg,{_t['accent']},{_t['alt']});"
          f"box-shadow:0 6px 14px {_t['accent']}40'>" + _logo_svg(_t['btn_text'], 17) + "</span>"
          f"<span style='line-height:1.15'><span style='font-size:15px;font-weight:800;color:{_t['text']}'>"
          f"Trading Journal <span class='grad-accent'>Pro</span></span><br>"
          f"<span style='font-size:11px;color:{_t['muted']}'>{st.session_state.get('auth_user','')} · {_role_lbl}</span>"
          f"</span></div>")

if st.session_state.hdr_open:
    with st.container(key="tj_hdr"):
        _r = st.columns([1.75, 1.75, 1.45, 1.75, 0.4, 0.4, 0.4], vertical_alignment="center", gap="small")
        with _r[0]:
            st.markdown(_brand, unsafe_allow_html=True)
        with _r[1]:
            _sel_theme = st.selectbox("Design", THEME_NAMES,
                index=THEME_NAMES.index(st.session_state.theme_name)
                      if st.session_state.theme_name in THEME_NAMES else 0,
                key="theme_selector", label_visibility="collapsed", format_func=theme_label,
                help="Design de l'interface : clair ou sombre, couleurs et style des graphiques")
            if _sel_theme != st.session_state.theme_name:
                st.session_state.theme_name = _sel_theme; st.rerun()
        with _r[2]:
            _cs_opts = ["Auto"] + CHART_STYLE_NAMES
            _cur_cs = st.session_state.get("chart_style_override", "Auto")
            _sel_cs = st.selectbox("Graphiques", _cs_opts,
                index=_cs_opts.index(_cur_cs) if _cur_cs in _cs_opts else 0,
                format_func=lambda x: (f"Graphiques · auto" if x == "Auto" else f"Graphiques · {x}"),
                key="chart_style_selector", label_visibility="collapsed",
                help="Type et configuration des graphiques. Auto = suit le design choisi "
                     f"(actuellement {THEME_CHART_STYLE.get(st.session_state.theme_name, 'Classique')}).")
            if _sel_cs != _cur_cs:
                st.session_state.chart_style_override = _sel_cs; st.rerun()
        with _r[3]:
            _sel_bg = st.selectbox("Fond", BG_NAMES,
                index=BG_NAMES.index(st.session_state.bg_name) if st.session_state.bg_name in BG_NAMES else 0,
                format_func=lambda n: "Fond · aucun" if n == "Aucun" else f"Fond · {n}",
                key="bg_selector", label_visibility="collapsed",
                help="Image de fond (photos libres de droits). « Aucun » pour un fond uni.")
            if _sel_bg != st.session_state.bg_name:
                st.session_state.bg_name = _sel_bg; st.rerun()
        with _r[4]:
            if st.button("", icon=":material/sync:", key="hdr_sync", help="Synchroniser", use_container_width=True):
                force_reload(); st.rerun()
        with _r[5]:
            if st.button("", icon=":material/logout:", key="hdr_logout", help="Déconnexion", use_container_width=True):
                logout()
        with _r[6]:
            st.button("", icon=":material/keyboard_arrow_up:", key="hdr_toggle", help="Masquer le panneau",
                      on_click=_hdr_toggle, use_container_width=True)
        _c1, _c2 = st.columns([3, 2.2], vertical_alignment="center", gap="small")
        with _c1:
            st.markdown(
                f"<div class='tj-cap'>"
                f"<span style='font-size:10.5px;color:{_t['muted']};text-transform:uppercase;letter-spacing:1.2px;"
                f"font-weight:700'>Capital · {selection_label()}</span>"
                f"<span style='font-size:20px;font-weight:800;color:{col_pnl};font-family:JetBrains Mono,monospace'>"
                f"{fmt(total)}</span>"
                f"<span style='font-size:11.5px;color:{_t['muted']}'>{len(df_side)} trades · {wr:.0f}% win</span></div>",
                unsafe_allow_html=True)
        with _c2:
            if len(_allowed) <= 1:
                st.markdown(f"<div style='font-size:12px;color:{_t['muted']}'>Compte : "
                            f"<b style='color:{_t['text']}'>{(_allowed[0] if _allowed else '—')}</b></div>",
                            unsafe_allow_html=True)
            else:
                check_filter("Comptes", _allowed, "mode_selection", "hacc", all_label="tous les comptes",
                             icon=":material/account_balance_wallet:")
        with st.container(horizontal=True, key="tj_nav", gap="small"):
            _render_nav("tjnav")
else:
    with st.container(horizontal=True, key="tj_hdr_min", gap="small", vertical_alignment="center"):
        st.markdown(
            f"<span style='display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;"
            f"border-radius:9px;background:linear-gradient(135deg,{_t['accent']},{_t['alt']})'>"
            + _logo_svg(_t['btn_text'], 15) + "</span>",
            unsafe_allow_html=True)
        _render_nav("tjmnav")
        st.markdown(f"<span style='font-size:13px;font-weight:800;color:{col_pnl};"
                    f"font-family:JetBrains Mono,monospace;padding:0 6px'>{fmt(total)}</span>",
                    unsafe_allow_html=True)
        st.button("", icon=":material/keyboard_arrow_down:", key="hdr_show", help="Afficher le panneau",
                  on_click=_hdr_toggle)
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# ── CHRONOMÈTRE GLOBAL : prochaine annonce majeure, visible quelle que soit la page ──
if "_alert_prefs" not in st.session_state:
    st.session_state["_alert_prefs"] = alert_prefs_get(st.session_state.get("auth_user", ""))
_ap = st.session_state["_alert_prefs"]
try:
    _cd_groups = upcoming_major_events(set(_ap.get("ccys") or ALERT_DEFAULTS["ccys"]),
                                       set(_ap.get("impacts") or ["High"]), horizon_h=168)
    render_countdown(_cd_groups, float(_ap.get("chrono_h", 4)), _thd)
except Exception:
    pass   # le chronomètre ne doit jamais bloquer l'app

# ── BANNER MODE ────────────────────────────────────────────────────────────────
def mode_banner():
    _t = get_theme()
    _sc = _resolve_scope(None)
    _al = allowed_accounts()
    def _band(col, icon, txt):
        st.markdown(
            f"<div style='background:linear-gradient(90deg,{col}22,{col}08);"
            f"border:1px solid {col}55;border-left:3px solid {col};border-radius:10px;"
            f"padding:8px 16px;font-size:12px;color:{col};font-weight:700;margin-bottom:12px'>"
            f"<i class='fa-solid {icon}'></i> {txt}</div>", unsafe_allow_html=True)
    if not _sc or set(_sc) == set(_al):
        _band(_t["alt"], "fa-layer-group", "Tous les comptes autorisés")
    elif len(_sc) == 1:
        name = _sc[0]; kind = ACCOUNT_KIND.get(name, "real")
        icon = "fa-flask" if kind == "demo" else "fa-circle-dot"
        _band(account_color(name), icon,
              f"{name} — compte {'démo' if kind=='demo' else 'réel'}")
    else:
        _band(_t["alt"], "fa-layer-group",
              f"{len(_sc)} comptes sélectionnés : {', '.join(_sc)}")

# ── MESSAGE DE MIGRATION (affiché une seule fois) ───────────────────────────────
_mig_msg = st.session_state.pop("_migration_msg", None)
if _mig_msg:
    st.success(_mig_msg, icon=":material/check_circle:")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════
# ANALYSE COMPORTEMENTALE : délais entre résultats, séries, contexte, émotions déduites,
# recommandations. Calculée sur le DataFrame déjà filtré (comptes sélectionnés + filtres).
# Les enchaînements sont calculés COMPTE PAR COMPTE (un trade démo n'est jamais la
# « reprise » d'une perte sur le compte réel), puis regroupés.
# ════════════════════════════════════════════════════════════════════════════
import re as _re_bh

REACTIVE_MOODS = ("Frustré", "Euphorique", "Anxieux", "Peureux")
CALM_MOODS = ("Neutre", "Confiant")

def _bh_mood_is_empty(row):
    """Émotion non renseignée : vide, ou « Neutre » posé par défaut à l'import MT5."""
    m = row.get("mood")
    if m is None or (isinstance(m, float) and pd.isna(m)) or str(m).strip() in ("", "nan", "None"):
        return True
    if row.get("mood_auto"):
        return True     # déjà déduite auparavant : on la recalcule
    return str(m) == "Neutre" and str(row.get("strategy", "")) == "Importé MT5"

def _bh_volume(notes):
    m = _re_bh.search(r"vol:([\d.]+)", str(notes or ""))
    try:
        return float(m.group(1)) if m else None
    except Exception:
        return None

def fmt_gap(minutes):
    if minutes is None or pd.isna(minutes):
        return "—"
    m = float(minutes)
    if m < 1:
        return "< 1 min"
    if m < 60:
        return f"{m:.0f} min"
    h = m / 60
    if h < 24:
        return f"{int(h)} h {int(m % 60):02d}"
    return f"{int(h // 24)} j {int(h % 24)} h"

def _bh_prepare(df):
    """Trie par compte et par heure d'ouverture, ajoute les variables de contexte."""
    d = df.copy()
    if d.empty:
        return d
    if "trade_mode" not in d.columns:
        d["trade_mode"] = "—"
    dt = pd.to_datetime(d.get("datetime"), errors="coerce") if "datetime" in d.columns else pd.Series(pd.NaT, index=d.index)
    dt = dt.fillna(pd.to_datetime(d["date"], errors="coerce"))
    d["_t"] = dt
    tm = d["time"].astype(str) if "time" in d.columns else pd.Series("", index=d.index)
    d["_has_time"] = (tm.str.match(r"^\d{1,2}:\d{2}$") & (tm != "00:00")) | (d["_t"].dt.hour + d["_t"].dt.minute > 0)
    d = d[d["_t"].notna()].sort_values(["trade_mode", "_t"]).reset_index(drop=True)
    d["_out"] = np.where(d["pnl"] > 0, "W", np.where(d["pnl"] < 0, "L", "B"))
    d["_vol"] = d["notes"].map(_bh_volume) if "notes" in d.columns else None
    g = d.groupby("trade_mode", sort=False)
    d["_prev_out"] = g["_out"].shift(1)
    d["_prev_pnl"] = g["pnl"].shift(1)
    d["_gap_prev"] = (d["_t"] - g["_t"].shift(1)).dt.total_seconds() / 60
    # séries de pertes / gains juste avant le trade, dans la même journée (l'état émotionnel
    # ne se reporte pas d'un jour à l'autre)
    d["_day"] = d["_t"].dt.date
    lb = pd.Series(0, index=d.index); wb = pd.Series(0, index=d.index)
    for _, grp in d.groupby(["trade_mode", "_day"], sort=False):
        cl = cw = 0
        for idx, o in zip(grp.index, grp["_out"]):
            lb[idx] = cl; wb[idx] = cw
            if o == "L":   cl, cw = cl + 1, 0
            elif o == "W": cw, cl = cw + 1, 0
    d["_loss_before"] = lb; d["_win_before"] = wb
    d["_day_rank"] = d.groupby(["trade_mode", "_day"]).cumcount() + 1
    med_vol = g["_vol"].transform("median")
    d["_vol_ratio"] = d["_vol"] / med_vol.replace(0, np.nan)
    wins = d.loc[d["pnl"] > 0, "pnl"]
    big = wins.quantile(0.8) if len(wins) >= 5 else (wins.max() if len(wins) else np.inf)
    d["_prev_big_win"] = d["_prev_pnl"] >= big
    return d

def _bh_gaps_between(d, a, b):
    """Délais (min) entre un trade de résultat a et le PROCHAIN trade de résultat b, par compte."""
    out = []
    for _, grp in d.groupby("trade_mode", sort=False):
        times, outs = grp["_t"].tolist(), grp["_out"].tolist()
        for i, o in enumerate(outs):
            if o != a:
                continue
            for j in range(i + 1, len(outs)):
                if outs[j] == b:
                    out.append((times[j] - times[i]).total_seconds() / 60)
                    break
    return pd.Series(out, dtype=float)

def _bh_stat(s):
    s = s.dropna()
    s5 = s[s <= 5 * 1440]          # au-delà de 5 jours (congés...) on écarte de la moyenne
    return {"n": int(len(s)), "median": float(s.median()) if len(s) else None,
            "mean": float(s5.mean()) if len(s5) else None}

def infer_mood(r):
    """Émotion probable AU MOMENT DE L'ENTRÉE, déduite du comportement (jamais du résultat du trade)."""
    gap, prev, lb, wb = r["_gap_prev"], r["_prev_out"], r["_loss_before"], r["_win_before"]
    vr, rank = r["_vol_ratio"], r["_day_rank"]
    quick = lambda m: gap is not None and not pd.isna(gap) and gap <= m and r["_has_time"]
    if lb >= 2 and quick(60):
        return "Frustré", f"{lb} pertes d'affilée, reprise {fmt_gap(gap)} après"
    if prev == "L" and quick(20):
        return "Frustré", f"reprise {fmt_gap(gap)} après une perte"
    if prev == "L" and vr is not None and not pd.isna(vr) and vr >= 1.3:
        return "Frustré", f"taille augmentée de {(vr - 1) * 100:.0f} % après une perte"
    if prev == "L" and vr is not None and not pd.isna(vr) and vr <= 0.7:
        return "Peureux", f"taille réduite de {(1 - vr) * 100:.0f} % après une perte"
    if lb >= 2 and quick(360):        # l'état émotionnel ne se reporte pas au lendemain
        return "Anxieux", f"après {lb} pertes d'affilée"
    if wb >= 3 and quick(360):
        return "Euphorique", f"après {wb} gains d'affilée"
    if prev == "W" and bool(r["_prev_big_win"]) and quick(30):
        return "Euphorique", f"reprise {fmt_gap(gap)} après un gros gain"
    if prev == "W" and vr is not None and not pd.isna(vr) and vr >= 1.3:
        return "Euphorique", f"taille augmentée de {(vr - 1) * 100:.0f} % après un gain"
    if rank >= 5:
        return "Anxieux", f"{rank}e trade de la journée (suractivité)"
    if prev == "W":
        return "Confiant", "après un gain, rythme et taille habituels"
    return "Neutre", "pas de signal émotionnel particulier"

def _bh_group(d, mask, label):
    s = d.loc[mask, "pnl"]
    n = int(len(s))
    return {"label": label, "n": n, "wr": float((s > 0).mean() * 100) if n else None,
            "exp": float(s.mean()) if n else None}

def behavior_analysis(df, keep_ids=None):
    """Métriques comportementales + émotions déduites.
    df : trades des comptes sélectionnés (séquence complète, pour le contexte de chaque trade).
    keep_ids : trades retenus par les filtres du dashboard ; les statistiques portent sur eux."""
    d = _bh_prepare(df)
    if keep_ids is not None and "id" in d.columns:
        d = d[d["id"].isin(keep_ids)].reset_index(drop=True)
    res = {"n": int(len(d)), "d": d}
    if d.empty:
        return res
    res["accounts"] = sorted(d["trade_mode"].unique().tolist())
    res["time_share"] = float(d["_has_time"].mean() * 100)
    res["gaps"] = {k: _bh_stat(_bh_gaps_between(d, a, b)) for k, (a, b) in {
        "LL": ("L", "L"), "WW": ("W", "W"), "LW": ("L", "W"), "WL": ("W", "L")}.items()}
    after_l = d.loc[d["_prev_out"] == "L", "_gap_prev"]
    after_w = d.loc[d["_prev_out"] == "W", "_gap_prev"]
    res["resume_after_loss"] = _bh_stat(after_l); res["resume_after_win"] = _bh_stat(after_w)
    # séries
    mx = {"W": 0, "L": 0}; cur = (None, 0)
    for _, grp in d.groupby("trade_mode", sort=False):
        c, k = None, 0
        for o in grp["_out"]:
            if o == "B":
                continue
            k = k + 1 if o == c else 1; c = o; mx[o] = max(mx[o], k)
        cur = (c, k) if k > cur[1] else cur
    res["max_win_streak"], res["max_loss_streak"] = mx["W"], mx["L"]
    # contexte
    base = _bh_group(d, d.index == d.index, "Tous les trades")
    quick_l = (d["_prev_out"] == "L") & (d["_gap_prev"] <= 30) & d["_has_time"]
    res["base"] = base
    res["context"] = [
        _bh_group(d, d["_prev_out"] == "W", "Après un gain"),
        _bh_group(d, d["_prev_out"] == "L", "Après une perte"),
        _bh_group(d, quick_l, "≤ 30 min après une perte"),
        _bh_group(d, d["_loss_before"] >= 2, "Après 2 pertes ou plus"),
        _bh_group(d, d["_prev_big_win"] & (d["_prev_out"] == "W"), "Après un gros gain"),
        _bh_group(d, d["_day_rank"] == 1, "1er trade du jour"),
        _bh_group(d, d["_day_rank"] >= 4, "4e trade du jour et +"),
    ]
    rk = d["_day_rank"].clip(upper=6)
    res["by_rank"] = [_bh_group(d, rk == k, (f"{k}e" if k < 6 else "6e+")) for k in range(1, 7) if (rk == k).any()]
    # volume après perte / gain
    if d["_vol"].notna().sum() >= 10:
        res["vol_after_loss"] = float(d.loc[d["_prev_out"] == "L", "_vol_ratio"].mean())
        res["vol_after_win"] = float(d.loc[d["_prev_out"] == "W", "_vol_ratio"].mean())
    # suractivité
    per_day = d.groupby(["trade_mode", "_day"]).size()
    res["trades_per_day_med"] = float(per_day.median())
    res["trades_per_day_max"] = int(per_day.max())
    # gains / pertes
    w, l = d.loc[d["pnl"] > 0, "pnl"], d.loc[d["pnl"] < 0, "pnl"]
    res["avg_win"] = float(w.mean()) if len(w) else 0.0
    res["avg_loss"] = float(l.mean()) if len(l) else 0.0
    res["payoff"] = (res["avg_win"] / abs(res["avg_loss"])) if len(l) and len(w) else None
    res["expectancy"] = float(d["pnl"].mean())
    # horaires
    if d["_has_time"].mean() >= 0.5:
        h = d[d["_has_time"]].assign(_h=lambda x: x["_t"].dt.hour)
        res["by_hour"] = h.groupby("_h")["pnl"].agg(["count", "mean", "sum"]).reset_index()
    wd = d.assign(_wd=d["_t"].dt.dayofweek)
    res["by_wd"] = wd.groupby("_wd")["pnl"].agg(["count", "mean", "sum"]).reset_index()
    res["by_sym"] = d.groupby("symbol")["pnl"].agg(["count", "mean", "sum"]).reset_index()
    # émotions : déclarées ou déduites
    empty = d.apply(_bh_mood_is_empty, axis=1)
    inf = d.apply(infer_mood, axis=1)
    d["mood_inferred"] = [x[0] for x in inf]; d["mood_reason"] = [x[1] for x in inf]
    d["mood_src"] = np.where(empty, "déduite", "déclarée")
    d["mood_final"] = np.where(empty, d["mood_inferred"], d["mood"])
    res["n_inferred"] = int(empty.sum())
    mf = d.groupby("mood_final")["pnl"].agg(["count", "mean", "sum"]).reset_index()
    mf["wr"] = d.groupby("mood_final")["pnl"].apply(lambda s: (s > 0).mean() * 100).values
    res["by_mood"] = mf
    res["reactive_share"] = float(d["mood_final"].isin(REACTIVE_MOODS).mean() * 100)
    res["reactive_exp"] = float(d.loc[d["mood_final"].isin(REACTIVE_MOODS), "pnl"].mean()) if d["mood_final"].isin(REACTIVE_MOODS).any() else None
    res["calm_exp"] = float(d.loc[d["mood_final"].isin(CALM_MOODS), "pnl"].mean()) if d["mood_final"].isin(CALM_MOODS).any() else None
    # épisodes de tilt : ≥ 3 pertes le même jour, chacune reprise en moins de 30 min
    tilt = 0
    for _, grp in d[d["_has_time"]].groupby(["trade_mode", "_day"]):
        run = 0
        for o, gp in zip(grp["_out"], grp["_gap_prev"].fillna(9e9)):
            run = run + 1 if (o == "L" and (run == 0 or gp <= 30)) else (0 if o != "L" else 1)
            if run == 3:
                tilt += 1
    res["tilt_episodes"] = tilt
    res["d"] = d
    return res

def emotion_level(res):
    """Conclusion sur le niveau émotionnel : (libellé, couleur clé, phrase sensible au signe)."""
    s = res.get("reactive_share", 0)
    re_, ca = res.get("reactive_exp"), res.get("calm_exp")
    cost = ""
    if re_ is not None and ca is not None:
        cost = f" Ces trades {result_phrase(re_)}, contre {result_noun(ca)} en état calme."
    if s >= 40:
        return "Élevé", "loss", f"{s:.0f} % de tes trades sont pris dans un état réactif (frustration, euphorie, anxiété, peur).{cost}"
    if s >= 20:
        return "Modéré", "orange", f"{s:.0f} % de tes trades sont pris dans un état réactif.{cost}"
    return "Maîtrisé", "win", f"Seulement {s:.0f} % de tes trades sont pris dans un état réactif.{cost}"

def recommendations(res, min_n=5):
    """Recommandations comportementales chiffrées, formulées selon le signe des métriques."""
    R = []
    if not res.get("n"):
        return R
    base = res["base"]; bwr, bexp = base["wr"] or 0, base["exp"] or 0
    ctx = {c["label"]: c for c in res["context"]}
    def add(level, title, detail, action, cat="Comportement & émotions"):
        R.append({"level": level, "cat": cat, "title": title, "detail": detail, "action": action})
    import math
    q = ctx.get("≤ 30 min après une perte")
    if q and q["n"] >= min_n and q["wr"] is not None and (q["wr"] < bwr - 8 or q["exp"] < min(0, bexp)):
        pause = res["resume_after_win"]["median"]
        add("critique", "Trading de revanche après une perte",
            f"Les {q['n']} trades repris moins de 30 min après une perte gagnent {q['wr']:.0f} % du temps "
            f"(contre {bwr:.0f} % en général) et {result_phrase(q['exp'])}.",
            f"Impose-toi une pause d'au moins {fmt_gap(max(30, pause or 30))} après chaque perte avant de reprendre.")
    l2 = ctx.get("Après 2 pertes ou plus")
    q_loss = max(0.01, min(0.99, 1 - bwr / 100)); n_tr = max(2, res["n"])
    exp_streak = math.log(max(1.0001, n_tr * (1 - q_loss))) / -math.log(q_loss)
    res["expected_loss_streak"] = exp_streak
    l2_bad = bool(l2 and l2["n"] >= min_n and l2["exp"] is not None and l2["exp"] < 0 and (l2["wr"] or 0) < bwr - 10)
    streak_bad = res.get("max_loss_streak", 0) > exp_streak + 1.5
    if streak_bad or l2_bad:
        parts = []
        if streak_bad:
            parts.append(f"Ta plus longue série est de {res['max_loss_streak']} pertes consécutives, plus que ce que "
                         f"le hasard explique avec ton taux de réussite (environ {exp_streak:.0f}).")
        if l2_bad:
            parts.append(f"Après 2 pertes d'affilée, tes trades {result_phrase(l2['exp'])} ({l2['n']} trades) et ne "
                         f"gagnent plus que {l2['wr']:.0f} % du temps.")
        add("critique" if res.get("max_loss_streak", 0) > exp_streak + 3 else "attention", "Séries de pertes",
            " ".join(parts),
            "Fixe un stop journalier : arrêt après 2 pertes d'affilée ou une perte cumulée de 2 % du capital.")
    if res.get("tilt_episodes", 0) >= 1:
        add("attention", "Épisodes de tilt",
            f"{res['tilt_episodes']} journée(s) avec au moins 3 pertes enchaînées à moins de 30 min d'intervalle.",
            "Dès la 2e perte rapide de la journée, ferme la plateforme et reviens le lendemain.")
    rk = [r for r in res.get("by_rank", []) if r["n"] >= min_n]
    if len(rk) >= 2:
        first = rk[0]; late = [r for r in rk if r["label"] in ("4e", "5e", "6e+")]
        if late:
            lexp = sum(r["exp"] * r["n"] for r in late) / sum(r["n"] for r in late)
            if lexp < 0 and lexp < first["exp"]:
                cutoff = next((i for i, r in enumerate(rk) if r["exp"] < 0), len(rk))
                best = max(rk, key=lambda r: r["exp"])
                best_txt = (f" ; tes trades les plus rentables sont les {best['label']} de la journée "
                            f"({result_noun(best['exp'])})" if best["exp"] > 0 else "")
                add("attention", "Suractivité en fin de journée",
                    f"À partir du 4e trade du jour, tes trades {result_phrase(lexp)}, contre {result_noun(first['exp'])} "
                    f"pour le 1er trade.",
                    f"Limite-toi à {max(1, cutoff)} trade(s) par jour et par compte{best_txt}.",
                    cat="Horaires & actifs")
    if res.get("payoff") is not None and res["payoff"] < 1 and bwr < 60:
        add("attention", "Gains trop courts par rapport aux pertes",
            f"Ton gain moyen ({money(res['avg_win'])}) est inférieur à ta perte moyenne ({money(res['avg_loss'])}) : "
            f"ratio {num(res['payoff'])}, avec {bwr:.0f} % de trades gagnants.",
            "Laisse courir les gagnants jusqu'à un objectif d'au moins 1,5 R et coupe les pertes au stop prévu.",
            cat="Risque & stops")
    elif res.get("payoff") is not None and res["payoff"] >= 1.5 and (base["exp"] or 0) > 0:
        add("positif", "Bon ratio gain / perte",
            f"Ton gain moyen ({money(res['avg_win'])}) vaut {num(res['payoff'])} fois ta perte moyenne.",
            "Garde ta gestion des sorties actuelle.", cat="Risque & stops")
    if res.get("vol_after_loss") and res["vol_after_loss"] >= 1.15:
        add("critique", "Taille de position augmentée après une perte",
            f"Après une perte, ta taille est en moyenne {num(res['vol_after_loss'])} fois ta taille habituelle.",
            "Garde une taille fixe (ou réduite) après une perte : ne cherche pas à te refaire.", cat="Volume & taille")
    bw = ctx.get("Après un gros gain")
    if bw and bw["n"] >= min_n and bw["exp"] is not None and bw["exp"] < 0 and bw["exp"] < bexp:
        add("attention", "Excès de confiance après un gros gain",
            f"Le trade qui suit un gros gain {result_phrase(bw['exp'], plural=False)} ({bw['n']} cas), "
            f"alors que l'ensemble de tes trades {result_phrase(bexp)}.",
            "Après un gros gain, fais une pause ou réduis la taille du trade suivant.")
    bm = res.get("by_mood")
    if bm is not None and len(bm):
        b5 = bm[bm["count"] >= min_n]
        worst = b5.sort_values("mean").head(1)
        if len(worst) and worst.iloc[0]["mean"] < 0 and worst.iloc[0]["mood_final"] in REACTIVE_MOODS:
            w0 = worst.iloc[0]
            add("attention", f"Trades en état « {w0['mood_final']} » perdants",
                f"Les {int(w0['count'])} trades pris dans cet état {result_phrase(w0['mean'])} et gagnent "
                f"{w0['wr']:.0f} % du temps.",
                f"Quand tu te sens {w0['mood_final'].lower()}, ne prends pas de position : note-le dans le journal et attends.")
        bestm = b5.sort_values("mean").tail(1)
        if len(bestm) and bestm.iloc[0]["mean"] > 0 and bestm.iloc[0]["mood_final"] in CALM_MOODS:
            add("positif", f"État « {bestm.iloc[0]['mood_final']} » rentable",
                f"Tes trades pris dans cet état {result_phrase(bestm.iloc[0]['mean'])} "
                f"({int(bestm.iloc[0]['count'])} trades).",
                "C'est ton état de référence : vérifie-le avant chaque entrée.")
    bh = res.get("by_hour")
    if bh is not None and len(bh):
        bh5 = bh[bh["count"] >= min_n].sort_values("mean")
        if len(bh5) >= 2:
            wst, bst = bh5.iloc[0], bh5.iloc[-1]
            if wst["mean"] < 0:
                alt = (f" ; ton créneau le plus rentable est {int(bst['_h']):02d}h ({result_noun(bst['mean'])})"
                       if bst["mean"] > 0 else " ; aucun créneau n'est rentable sur cette sélection")
                add("attention", f"Créneau de {int(wst['_h']):02d}h à éviter",
                    f"Les {int(wst['count'])} trades ouverts à {int(wst['_h']):02d}h {result_phrase(wst['mean'])}.",
                    f"Évite d'ouvrir à {int(wst['_h']):02d}h{alt}.", cat="Horaires & actifs")
            elif bst["mean"] > 0:
                add("positif", f"Créneau fort : {int(bst['_h']):02d}h",
                    f"Les {int(bst['count'])} trades ouverts à {int(bst['_h']):02d}h {result_phrase(bst['mean'])}.",
                    "Privilégie ce créneau pour tes meilleurs setups.", cat="Horaires & actifs")
    bs = res.get("by_sym")
    if bs is not None and len(bs):
        bs5 = bs[bs["count"] >= min_n].sort_values("sum")
        if len(bs5) >= 2 and bs5.iloc[0]["sum"] < 0:
            alt = (f" et concentre-toi sur {bs5.iloc[-1]['symbol']} (gain cumulé de {money(bs5.iloc[-1]['sum'])})"
                   if bs5.iloc[-1]["sum"] > 0 else " : aucun actif n'est rentable sur cette sélection")
            add("attention", f"Actif pénalisant : {bs5.iloc[0]['symbol']}",
                f"Les {int(bs5.iloc[0]['count'])} trades sur {bs5.iloc[0]['symbol']} cumulent une perte de "
                f"{money(bs5.iloc[0]['sum'])}.",
                f"Réduis ou suspends {bs5.iloc[0]['symbol']}{alt}.", cat="Horaires & actifs")
    lw = res["gaps"]["LW"]
    if lw["n"] >= min_n and lw["median"] is not None:
        add("info", "Temps de récupération",
            f"Il faut en médiane {fmt_gap(lw['median'])} pour qu'un gain suive une perte ({lw['n']} cas).",
            "Utilise ce délai comme repère : inutile de forcer un trade pour « te refaire » avant.")
    return R

def all_recommendations(bh, rk):
    """Toutes les recommandations, triées : critique, attention, info, puis points forts."""
    R = recommendations(bh) + risk_recommendations(rk)
    _exit_alerts = {"TP souvent trop loin", "Gains coupés avant l'objectif", "Trades gagnants qui finissent au stop",
                    "Sorties peu efficaces", "Gains trop courts par rapport aux pertes"}
    if any(r["title"] in _exit_alerts for r in R):
        R = [r for r in R if r["title"] not in ("Bonne capture des mouvements", "Bon ratio gain / perte")]
    if not any(r["level"] in ("critique", "attention") for r in R) and (bh.get("n") or 0) >= 5:
        R.append({"level": "positif", "cat": "Comportement & émotions", "title": "Discipline correcte",
                  "detail": "Aucun biais comportemental ou de gestion du risque marqué sur la sélection.",
                  "action": "Continue ainsi et garde le même plan de trading."})
    order = {"critique": 0, "attention": 1, "info": 2, "positif": 3}
    return sorted(R, key=lambda r: order[r["level"]])

# ════════════════════════════════════════════════════════════════════════════
# ANALYSE DU RISQUE : stops, TP, MAE / MFE, volumes. Formulations sensibles au signe.
# ════════════════════════════════════════════════════════════════════════════
def money(v):
    """Montant sans signe (le sens est porté par le verbe)."""
    return f"{abs(float(v)):,.2f}".replace(",", "\u202f").replace(".", ",") + " $"

def result_phrase(v, plural=True):
    """« rapportent en moyenne 12,30 $ » / « perdent en moyenne 6,88 $ » (jamais « perdent -6,88 »)."""
    v = float(v or 0)
    if plural:
        return f"rapportent en moyenne {money(v)}" if v >= 0 else f"perdent en moyenne {money(v)}"
    return f"rapporte en moyenne {money(v)}" if v >= 0 else f"perd en moyenne {money(v)}"

def result_noun(v):
    """« un gain moyen de 22,19 $ » / « une perte moyenne de 1,33 $ »."""
    v = float(v or 0)
    return f"un gain moyen de {money(v)}" if v >= 0 else f"une perte moyenne de {money(v)}"

def pct(v):
    return f"{v:.0f} %"

def num(v, d=2):
    """Nombre avec virgule décimale (phrases)."""
    return f"{float(v):.{d}f}".replace(".", ",")

EXIT_LABELS = ["Stop touché", "Stop suiveur / point mort", "TP touché",
               "Sortie manuelle en gain", "Sortie manuelle en perte", "Stop-out (marge)", "Sortie non mesurable"]

def risk_analysis(df):
    """Stops / TP / MAE-MFE / volume sur les trades filtrés du dashboard."""
    d = df.copy()
    res = {"n": int(len(d))}
    if d.empty:
        return res
    for c in ("entry", "exit", "sl", "tp", "volume", "mae", "mfe", "mae_money", "mfe_money", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce") if c in d.columns else np.nan
    if "notes" in d.columns:
        _v = d["notes"].map(_bh_volume)
        d["volume"] = d["volume"].fillna(pd.to_numeric(_v, errors="coerce"))
    d["exit_reason"] = d["exit_reason"].astype(str).str.upper() if "exit_reason" in d.columns else ""
    d["_dir"] = np.where(d.get("direction", pd.Series("LONG", index=d.index)).astype(str).str.upper().str.startswith("S"), -1, 1)
    e, x, sl, tp = d["entry"], d["exit"], d["sl"], d["tp"]
    # prix de sortie exploitable (les anciens imports enregistraient le prix d'entrée)
    d["_exit_ok"] = (e > 0) & (x > 0) & ~((x == e) & (d["pnl"].fillna(0) != 0))
    d["_has_sl"] = (sl > 0) & (sl != e) & (e > 0)
    d["_has_tp"] = (tp > 0) & (tp != e) & (e > 0)
    d["_sl_dist"] = np.where(d["_has_sl"], (e - sl).abs(), np.nan)
    d["_tp_dist"] = np.where(d["_has_tp"], (tp - e).abs(), np.nan)
    d["_sl_protect"] = d["_has_sl"] & ((e - sl) * d["_dir"] > 0)      # stop du côté de la perte (risque réel)
    d["_move"] = np.where(d["_exit_ok"], (x - e) * d["_dir"], np.nan)
    d["_R"] = np.where(d["_sl_protect"] & d["_exit_ok"], d["_move"] / d["_sl_dist"], np.nan)
    d["_rr_plan"] = np.where(d["_sl_protect"] & d["_has_tp"], d["_tp_dist"] / d["_sl_dist"], np.nan)

    def classify(r):
        rs = r["exit_reason"]
        if rs in ("SL", "TP", "STOPOUT"):
            if rs == "TP":
                return "TP touché"
            if rs == "STOPOUT":
                return "Stop-out (marge)"
            return "Stop touché" if (r["pnl"] or 0) < 0 else "Stop suiveur / point mort"
        if not r["_exit_ok"]:
            return "Sortie non mesurable"
        ref = r["_sl_dist"] if r["_has_sl"] else r["_tp_dist"]
        tol = 0.08 * ref if ref and ref > 0 else 0
        if r["_has_sl"] and tol and abs(r["exit"] - r["sl"]) <= tol:
            return "Stop touché" if (r["pnl"] or 0) < 0 else "Stop suiveur / point mort"
        if r["_has_tp"] and tol and abs(r["exit"] - r["tp"]) <= tol:
            return "TP touché"
        return "Sortie manuelle en gain" if (r["pnl"] or 0) >= 0 else "Sortie manuelle en perte"
    d["_exit_cls"] = d.apply(classify, axis=1)
    res["d"] = d
    measurable = d[d["_exit_cls"] != "Sortie non mesurable"]
    res["n_measurable"] = int(len(measurable))
    res["n_bad_exit"] = int(((d["exit"] == d["entry"]) & (d["pnl"].fillna(0) != 0) & (d["entry"] > 0)).sum())
    res["sl_cov"] = float(d["_has_sl"].mean() * 100)
    res["tp_cov"] = float(d["_has_tp"].mean() * 100)
    res["exit_mix"] = (measurable["_exit_cls"].value_counts(normalize=True) * 100).reindex(EXIT_LABELS).dropna()
    res["exit_exp"] = measurable.groupby("_exit_cls")["pnl"].agg(["count", "mean"]).reindex(EXIT_LABELS).dropna()
    res["rr_plan_med"] = float(np.nanmedian(d["_rr_plan"])) if d["_rr_plan"].notna().any() else None
    res["R_med"] = float(np.nanmedian(d["_R"])) if d["_R"].notna().any() else None
    res["R_win_med"] = float(np.nanmedian(d.loc[d["pnl"] > 0, "_R"])) if d.loc[d["pnl"] > 0, "_R"].notna().any() else None
    mw = d[(d["_exit_cls"] == "Sortie manuelle en gain") & d["_has_tp"] & d["_exit_ok"]]
    ml = d[(d["_exit_cls"] == "Sortie manuelle en perte") & d["_sl_protect"] & d["_exit_ok"]]
    res["manual_win_n"] = int(len(mw))
    res["manual_win_tp_frac"] = float((mw["_move"] / mw["_tp_dist"]).median()) if len(mw) else None
    res["manual_loss_n"] = int(len(ml))
    res["manual_loss_sl_frac"] = float((-ml["_move"] / ml["_sl_dist"]).median()) if len(ml) else None
    # ── MAE / MFE ───────────────────────────────────────────────────────────
    ex = d[d["mae"].notna() & d["mfe"].notna() & (d["mae"] >= 0) & (d["mfe"] >= 0)]
    res["n_excursion"] = int(len(ex))
    exR = ex[ex["_sl_protect"]].copy()
    if len(exR):
        exR["_maeR"] = exR["mae"] / exR["_sl_dist"]; exR["_mfeR"] = exR["mfe"] / exR["_sl_dist"]
        win, los = exR[exR["pnl"] > 0], exR[exR["pnl"] < 0]
        stopped = exR[exR["_exit_cls"] == "Stop touché"]
        res["exR"] = exR
        res["win_maeR_q"] = {q: float(win["_maeR"].quantile(q)) for q in (0.5, 0.8, 0.9, 0.95)} if len(win) >= 5 else None
        res["near_miss"] = float((win["_maeR"] >= 0.8).mean() * 100) if len(win) >= 5 else None
        res["stopped_mfe_1R"] = float((stopped["_mfeR"] >= 1).mean() * 100) if len(stopped) >= 5 else None
        res["stopped_mfe_half"] = float((stopped["_mfeR"] >= 0.5).mean() * 100) if len(stopped) >= 5 else None
        res["n_stopped_ex"] = int(len(stopped)); res["n_win_ex"] = int(len(win))
        res["e_ratio"] = float(exR["_mfeR"].mean() / exR["_maeR"].mean()) if exR["_maeR"].mean() > 0 else None
        res["mfe_med_R"] = float(exR["_mfeR"].median())
        tpR = exR[exR["_has_tp"]]
        if len(tpR) >= 5:
            reach = (tpR["mfe"] >= tpR["_tp_dist"])
            res["tp_reach"] = float(reach.mean() * 100)
            res["tp_reach_not_taken"] = float(((tpR["mfe"] >= tpR["_tp_dist"]) & (tpR["_exit_cls"] != "TP touché")).mean() * 100)
            res["tp_plan_med_R"] = float(tpR["_rr_plan"].median())
    winx = ex[(ex["pnl"] > 0) & (ex["mfe"] > 0) & ex["_exit_ok"]]
    res["exit_eff"] = float((winx["_move"] / winx["mfe"]).clip(0, 1).median() * 100) if len(winx) >= 5 else None
    # ── Volume ──────────────────────────────────────────────────────────────
    v = d[d["volume"] > 0].copy()
    res["n_volume"] = int(len(v))
    if len(v) >= 10:
        v["_rel"] = v["volume"] / v.groupby("symbol")["volume"].transform("median")
        v["_bucket"] = pd.cut(v["_rel"], [0, 0.8, 1.25, np.inf], labels=["Petite taille", "Taille habituelle", "Grande taille"])
        g = v.groupby("_bucket", observed=False)["pnl"]
        res["by_size"] = pd.DataFrame({"count": g.count(), "mean": g.mean(),
                                       "wr": g.apply(lambda s: (s > 0).mean() * 100 if len(s) else np.nan),
                                       "avg_loss": v[v["pnl"] < 0].groupby("_bucket", observed=False)["pnl"].mean()}).reset_index()
    st_l = d[(d["_exit_cls"] == "Stop touché")]["pnl"].abs()
    all_l = d[d["pnl"] < 0]["pnl"].abs()
    res["stop_loss_avg"] = float(st_l.mean()) if len(st_l) else None
    res["loss_cv"] = float(all_l.std() / all_l.mean()) if len(all_l) >= 10 and all_l.mean() > 0 else None
    res["loss_max_ratio"] = float(all_l.max() / all_l.mean()) if len(all_l) >= 10 and all_l.mean() > 0 else None
    res["loss_max"] = float(all_l.max()) if len(all_l) else None
    res["loss_avg"] = float(all_l.mean()) if len(all_l) else None
    return res

def risk_recommendations(rk, min_n=5):
    """Recommandations stops / TP / volume, formulées selon le signe des métriques."""
    R = []
    if not rk.get("n"):
        return R
    def add(level, title, detail, action):
        R.append({"level": level, "cat": "Risque & stops", "title": title, "detail": detail, "action": action})
    def addv(level, title, detail, action):
        R.append({"level": level, "cat": "Volume & taille", "title": title, "detail": detail, "action": action})
    if rk.get("n_bad_exit", 0) >= min_n:
        add("info", "Prix de sortie à corriger",
            f"{rk['n_bad_exit']} trades ont un prix de sortie égal au prix d'entrée (ancien import) : ils sont "
            "écartés de l'analyse des stops et TP.",
            "Réimporte tes rapports MT5 et clique sur « Corriger les trades déjà importés », ou importe le "
            "fichier du script MAE/MFE.")
    if rk["sl_cov"] < 80:
        add("critique" if rk["sl_cov"] < 50 else "attention", "Trades sans stop",
            f"Seulement {pct(rk['sl_cov'])} de tes trades ont un stop enregistré.",
            "Place un stop à l'ouverture de chaque position, avant même de penser à l'objectif.")
    elif rk["sl_cov"] >= 95:
        add("positif", "Stops systématiques", f"{pct(rk['sl_cov'])} de tes trades ont un stop.", "Garde cette règle.")
    if rk.get("rr_plan_med") is not None and rk["rr_plan_med"] < 1:
        add("attention", "R:R prévu inférieur à 1",
            f"En médiane, ton objectif est à {num(rk['rr_plan_med'])} fois la distance du stop : tu risques plus que "
            "tu ne vises.",
            "Ne prends que des setups où le TP est au moins à 1,5 fois la distance du stop.")
    fr = rk.get("manual_win_tp_frac")
    if fr is not None and rk.get("manual_win_n", 0) >= min_n and fr < 0.6:
        reach = rk.get("tp_reach_not_taken")
        if reach is not None and reach >= 20:
            add("attention", "Gains coupés avant l'objectif",
                f"Tu clôtures tes gagnants à la main à {pct(fr * 100)} du chemin vers le TP (médiane, "
                f"{rk['manual_win_n']} trades), alors que le prix atteint ensuite ou déjà le TP dans "
                f"{pct(reach)} des cas.",
                "Laisse travailler le TP : sors seulement si le scénario est invalidé, pas par peur de rendre le gain.")
        else:
            add("attention", "TP souvent trop loin",
                f"Tes sorties manuelles en gain se font à {pct(fr * 100)} du chemin vers le TP (médiane, "
                f"{rk['manual_win_n']} trades) : l'objectif est rarement réaliste.",
                "Rapproche le TP du mouvement que tu obtiens réellement, ou prends une partie des gains à mi-parcours.")
    ws = rk.get("win_maeR_q")
    if ws and rk.get("n_win_ex", 0) >= min_n:
        p90 = ws[0.9]
        if p90 < 0.6:
            add("attention", "Stop probablement trop large",
                f"90 % de tes gagnants n'ont jamais reculé de plus de {num(p90)} R avant de partir dans le bon sens "
                f"({rk['n_win_ex']} gagnants mesurés).",
                f"Un stop vers {num(min(1.0, p90 * 1.15))} fois ta distance actuelle conserverait l'essentiel des "
                "gagnants et améliorerait ton R:R.")
        nm = rk.get("near_miss")
        if nm is not None and nm >= 30:
            add("attention", "Stop probablement trop court",
                f"{pct(nm)} de tes gagnants sont passés à moins de 0,2 R du stop avant de repartir : tu frôles "
                "souvent la sortie.",
                "Place le stop derrière la structure (dernier swing, zone de liquidité) plutôt qu'à une distance fixe, "
                "en réduisant la taille pour garder le même risque.")
    s1 = rk.get("stopped_mfe_1R")
    if s1 is not None and rk.get("n_stopped_ex", 0) >= min_n and s1 >= 20:
        add("attention", "Trades gagnants qui finissent au stop",
            f"{pct(s1)} des trades stoppés étaient d'abord allés au moins 1 R en ta faveur "
            f"({rk['n_stopped_ex']} stops mesurés).",
            "Passe le stop au point mort à +1 R, ou prends une partie des gains à +1 R.")
    ef = rk.get("exit_eff")
    if ef is not None:
        if ef < 45:
            add("attention", "Sorties peu efficaces",
                f"Sur tes gagnants, tu ne gardes que {pct(ef)} du mouvement favorable maximal (médiane).",
                "Utilise un stop suiveur derrière les derniers creux/sommets, ou une sortie partielle sur l'extrême.")
        elif ef >= 65:
            add("positif", "Bonne capture des mouvements", f"Tu gardes {pct(ef)} du mouvement favorable maximal sur tes gagnants.",
                "Continue à gérer tes sorties de la même façon.")
    er = rk.get("e_ratio")
    if er is not None and rk.get("n_excursion", 0) >= 20:
        if er < 1:
            add("attention", "Avantage statistique faible à l'entrée",
                f"En moyenne, le prix va plus loin contre toi qu'en ta faveur (ratio MFE/MAE {num(er)}).",
                "Revois tes critères d'entrée : attends une confirmation ou entre plus près de la zone d'invalidation.")
        elif er >= 1.5:
            add("positif", "Bonnes entrées", f"Le prix va en moyenne {num(er, 1)} fois plus loin en ta faveur que contre toi.",
                "Tes entrées sont un point fort : concentre tes efforts sur la gestion de sortie.")
    bs = rk.get("by_size")
    if bs is not None and len(bs):
        big = bs[bs["_bucket"] == "Grande taille"]; usual = bs[bs["_bucket"] == "Taille habituelle"]
        if len(big) and len(usual) and big["count"].iloc[0] >= min_n and usual["count"].iloc[0] >= min_n:
            bm, um = float(big["mean"].iloc[0]), float(usual["mean"].iloc[0])
            if bm < min(0, um):
                addv("critique", "Tes grosses positions perdent",
                     f"Les trades de grande taille {result_phrase(bm)} ({int(big['count'].iloc[0])} trades), "
                     f"contre {result_noun(um)} en taille habituelle.",
                     "Fixe une taille maximale et calcule chaque position à partir d'un risque fixe en % du capital.")
            elif bm > um > 0:
                addv("info", "Grandes tailles plus rentables",
                     f"Les trades de grande taille {result_phrase(bm)}, contre {result_noun(um)} en taille habituelle.",
                     "N'augmente la taille que sur ces mêmes setups, en gardant un risque par trade plafonné.")
    cv = rk.get("loss_cv"); mr = rk.get("loss_max_ratio")
    if cv is not None and cv > 0.7:
        addv("attention", "Risque par trade irrégulier",
             f"Tes pertes varient beaucoup d'un trade à l'autre (perte moyenne {money(rk['loss_avg'])}, "
             f"coefficient de variation {num(cv)}).",
             "Dimensionne chaque position pour que la perte au stop soit toujours le même montant (ex. 1 % du capital).")
    if mr is not None and mr >= 3:
        addv("critique" if mr >= 5 else "attention", "Pertes extrêmes",
             f"Ta plus grosse perte ({money(rk['loss_max'])}) vaut {num(mr, 1)} fois ta perte moyenne.",
             "Ne déplace jamais un stop pour l'éloigner, et coupe toute position qui dépasse le risque prévu.")
    return R



# ══════════════════════════════════════════════════════════════════════════════
# MOTEUR MACRO : données (FRED, BIS, Yahoo Finance, calendrier) + règles de biais
# Sources gratuites sans clé. Chaque source est indépendante : si l'une tombe,
# les autres continuent et l'écran indique ce qui manque.
# ══════════════════════════════════════════════════════════════════════════════
MX_CCYS = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
MX_CB = {  # banque centrale, code BIS, séries FRED de secours
    "USD": ("Fed", "US", "DFEDTARU"), "EUR": ("BCE", "XM", "ECBDFR"), "GBP": ("BoE", "GB", "BOERUKM"),
    "JPY": ("BoJ", "JP", None), "CHF": ("BNS", "CH", None), "CAD": ("BoC", "CA", None),
    "AUD": ("RBA", "AU", None), "NZD": ("RBNZ", "NZ", None),
}
# Séries FRED : id -> (libellé, unité, transformation affichée)
#   yoy = glissement annuel %, mom = variation mensuelle, diff = variation absolue, lvl = niveau
MX_FRED = {
    # Politique monétaire & taux
    "DFEDTARU": ("Taux Fed (borne haute)", "%", "lvl"), "ECBDFR": ("Taux de dépôt BCE", "%", "lvl"),
    "BOERUKM": ("Taux BoE", "%", "lvl"), "DFF": ("Fed funds effectif", "%", "lvl"),
    "DGS2": ("US 2 ans", "%", "lvl"), "DGS10": ("US 10 ans", "%", "lvl"),
    "WALCL": ("Bilan de la Fed", "Md$", "lvl"), "ECBASSETSW": ("Bilan de la BCE", "Md€", "lvl"),
    "T5YIE": ("Inflation anticipée 5 ans", "%", "lvl"),
    # Inflation & emploi
    "CPIAUCSL": ("CPI US", "% a/a", "yoy"), "CPILFESL": ("Core CPI US", "% a/a", "yoy"),
    "PCEPI": ("PCE US", "% a/a", "yoy"), "PCEPILFE": ("Core PCE US", "% a/a", "yoy"),
    "PAYEMS": ("NFP (créations d'emplois)", "k", "diff"), "UNRATE": ("Taux de chômage US", "%", "lvl"),
    "CES0500000003": ("Salaire horaire moyen", "% a/a", "yoy"), "ICSA": ("Inscriptions au chômage", "k", "lvl"),
    # Croissance
    "A191RL1Q225SBEA": ("PIB US (t/t annualisé)", "%", "lvl"), "RSAFS": ("Ventes au détail US", "% m/m", "mom"),
    "INDPRO": ("Production industrielle US", "% a/a", "yoy"), "UMCSENT": ("Confiance consommateur (Michigan)", "pts", "lvl"),
    # Liquidité & sentiment
    "T10Y2Y": ("Courbe US 10 ans - 2 ans", "pb", "bp"), "T10Y3M": ("Courbe US 10 ans - 3 mois", "pb", "bp"),
    "VIXCLS": ("VIX", "pts", "lvl"), "BAMLH0A0HYM2": ("Spread High Yield", "pb", "bp"),
    "BAMLC0A0CM": ("Spread Investment Grade", "pb", "bp"), "M2SL": ("Masse monétaire M2", "% a/a", "yoy"),
    "NFCI": ("Conditions financières (Chicago Fed)", "idx", "lvl"), "DTWEXBGS": ("Dollar large (Fed)", "idx", "lvl"),
}
MX_YAHOO = {
    "DX-Y.NYB": "DXY", "^VIX": "VIX", "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "GC=F": "Or",
    "CL=F": "WTI", "BTC-USD": "Bitcoin", "ZQ=F": "Fed funds futures", "^TNX": "US 10 ans",
    "EURUSD=X": "EURUSD", "GBPUSD=X": "GBPUSD", "USDJPY=X": "USDJPY", "USDCHF=X": "USDCHF",
    "USDCAD=X": "USDCAD", "AUDUSD=X": "AUDUSD", "NZDUSD=X": "NZDUSD",
}
MX_FX = {"EUR": ("EURUSD=X", 1), "GBP": ("GBPUSD=X", 1), "JPY": ("USDJPY=X", -1), "CHF": ("USDCHF=X", -1),
         "CAD": ("USDCAD=X", -1), "AUD": ("AUDUSD=X", 1), "NZD": ("NZDUSD=X", 1)}
MX_IMPACT_W = {"High": 1.0, "Medium": 0.5, "Low": 0.2}
_MX_RATE_RX = ("interest rate decision", "rate decision", "policy rate", "cash rate", "bank rate",
               "funds rate", "overnight rate", "refinancing rate", "deposit facility rate", "deposit rate")


def macro_polarity(title):
    """+1 : un chiffre plus haut = économie plus forte / plus chaude ; -1 : l'inverse ; 0 : neutre."""
    t = str(title).lower()
    if any(k in t for k in ("unemployment rate", "unemployment change", "jobless", "claims", "claimant", "continuing")):
        return -1
    if any(k in t for k in ("cpi", "inflation", "ppi", "pce", "gdp", "retail", "nonfarm", "non-farm", "payroll",
                            "employment change", "adp", "jolts", "pmi", "ism", "confidence", "sentiment", "zew",
                            "ifo", "durable", "industrial", "rate decision", "interest rate", "spending", "earnings",
                            "wage", "production", "orders", "home sales", "building permits", "housing starts")):
        return 1
    return 0


def macro_category(title):
    t = str(title).lower()
    if any(k in t for k in _MX_RATE_RX) or any(k in t for k in ("fomc", "rate statement")):
        return "Taux"
    if any(k in t for k in ("cpi", "ppi", "pce", "inflation", "hicp")):
        return "Inflation"
    if any(k in t for k in ("nonfarm", "non-farm", "payroll", "unemployment", "jobless", "claims", "adp", "jolts",
                            "employment", "wage", "earnings")):
        return "Emploi"
    if any(k in t for k in ("gdp", "pmi", "ism", "retail", "confidence", "sentiment", "zew", "ifo", "durable",
                            "industrial", "spending", "orders", "home", "housing", "building", "production")):
        return "Croissance"
    return None


# ── Accès aux sources (non mis en cache : appelés par les paquets mis en cache) ──
def _fred_raw(sid, start="2012-01-01"):
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}",
                     headers=_UA, timeout=12)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d = d.iloc[:, :2]; d.columns = ["date", "value"]
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    s = d.dropna().set_index("date")["value"]
    if s.empty:
        raise ValueError("série vide")
    return s


def _yahoo_raw(ticker, rng="2y"):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                     params={"range": rng, "interval": "1d"}, headers=_UA, timeout=15)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(res["timestamp"], unit="s").normalize(), dtype=float).dropna()
    s = s[~s.index.duplicated(keep="last")]
    if s.empty:
        raise ValueError("série vide")
    return s


def _bis_policy_raw(start):
    areas = "+".join(v[1] for v in MX_CB.values())
    r = requests.get(f"https://stats.bis.org/api/v1/data/WS_CBPOL/D.{areas}",
                     params={"startPeriod": start, "format": "csv"}, headers=_UA, timeout=25)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    cols = {c.upper(): c for c in d.columns}
    ra = next(cols[c] for c in cols if "REF_AREA" in c)
    tp = next(cols[c] for c in cols if "TIME_PERIOD" in c)
    ov = next(cols[c] for c in cols if "OBS_VALUE" in c)
    d = d[[ra, tp, ov]].rename(columns={ra: "area", tp: "date", ov: "value"})
    d["area"] = d["area"].astype(str).str.split(":").str[0].str.strip()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d["value"] = pd.to_numeric(d["value"], errors="coerce")
    out = {}
    for ccy, (_, area, _) in MX_CB.items():
        s = d[d["area"] == area].dropna().set_index("date")["value"].sort_index()
        if not s.empty:
            out[ccy] = s
    if not out:
        raise ValueError("BIS : aucune série")
    return out


def _parallel(fn, keys, workers=8):
    from concurrent.futures import ThreadPoolExecutor
    ok, ko = {}, []
    def _one(k):
        try:
            return k, fn(k), None
        except Exception as e:
            return k, None, f"{type(e).__name__}"
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for k, v, err in ex.map(_one, keys):
            if err is None:
                ok[k] = v
            else:
                ko.append(k)
    return ok, ko


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def macro_fred_bundle(ids):
    ok, ko = _parallel(_fred_raw, list(ids))
    if not ok:
        raise RuntimeError("FRED injoignable")
    return ok, ko


@st.cache_data(ttl=30 * 60, show_spinner=False)
def macro_yahoo_bundle(tickers):
    ok, ko = _parallel(_yahoo_raw, list(tickers))
    if not ok:
        raise RuntimeError("Yahoo Finance injoignable")
    return ok, ko


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def macro_bis_rates(start):
    return _bis_policy_raw(start)


MX_TTL = {"fred": 6 * 3600, "yahoo": 30 * 60, "bis": 12 * 3600, "rates": 6 * 3600}
MX_RETRY = 10 * 60          # une source en échec n'est retentée qu'après 10 min
MX_SRC_LABEL = {"fred": "FRED", "yahoo": "Yahoo Finance", "bis": "BIS (taux directeurs)", "rates": "Décisions de taux"}


@st.cache_resource(show_spinner=False)
def _mx_store():
    """Mémoire partagée par toutes les sessions du serveur : les données ne sont chargées qu'une fois."""
    import threading
    return {"fred": {}, "yahoo": {}, "bis": {}, "rates": [], "ts": {}, "fail_ts": {}, "missing": {},
            "running": False, "lock": threading.Lock(), "started": 0.0}


def _mx_worker(store, jobs):
    import time as _t
    try:
        for kind in jobs:
            try:
                if kind == "fred":
                    ok, ko = _parallel(_fred_raw, list(MX_FRED), workers=12)
                elif kind == "yahoo":
                    ok, ko = _parallel(_yahoo_raw, list(MX_YAHOO), workers=12)
                elif kind == "bis":
                    ok, ko = _bis_policy_raw((date.today() - timedelta(days=800)).isoformat()), []
                else:
                    evs, _src = _fetch_calendar_raw("rates")
                    ok = [e for e in (evs or []) if any(k in str(e.get("title", "")).lower() for k in _MX_RATE_RX)]
                    ko = []
                if ok:
                    if kind == "rates":
                        store["rates"] = ok
                    else:
                        merged = dict(store[kind]); merged.update(ok); store[kind] = merged
                    store["ts"][kind] = _t.time()
                    store["missing"][kind] = list(ko)
                else:
                    store["fail_ts"][kind] = _t.time()
                    store["missing"][kind] = ["tout"]
            except Exception:
                store["fail_ts"][kind] = _t.time()
                store["missing"][kind] = ["tout"]
    finally:
        store["running"] = False


def macro_get(force=False):
    """Données macro disponibles tout de suite ; le rafraîchissement se fait en tâche de fond."""
    import threading, time as _t
    store = _mx_store(); now = _t.time()
    jobs = [k for k, ttl in MX_TTL.items()
            if force or ((now - store["ts"].get(k, 0) > ttl) and (now - store["fail_ts"].get(k, 0) > MX_RETRY))]
    with store["lock"]:
        if store["running"] and now - store["started"] > 300:      # tâche bloquée : on la relance
            store["running"] = False
        if jobs and not store["running"]:
            store["running"] = True; store["started"] = now
            threading.Thread(target=_mx_worker, args=(store, jobs), daemon=True).start()
    missing = {MX_SRC_LABEL[k]: v for k, v in store["missing"].items() if v}
    return {"fred": store["fred"], "yahoo": store["yahoo"], "bis": store["bis"], "rates": store["rates"],
            "missing": missing, "loading": store["running"],
            "empty": not (store["fred"] or store["yahoo"] or store["bis"])}


# ── Transformations et statistiques ───────────────────────────────────────────
def mx_transform(s, how):
    """Série brute -> série affichée (glissement annuel, variation, points de base...)."""
    if s is None or len(s) == 0:
        return s
    s = s.sort_index()
    if how in ("yoy", "mom"):
        step = 1
        if how == "yoy":
            per = pd.infer_freq(s.index[-8:]) if len(s) >= 8 else None
            step = 52 if (per or "").startswith("W") else (4 if (per or "").startswith("Q") else 12)
            if per and per.startswith("D"): step = 252
        return (s / s.shift(step) - 1).mul(100).dropna()
    if how == "diff":
        return s.diff().dropna()
    if how == "bp":
        return s.mul(100)
    return s


def mx_last(s):
    """(valeur actuelle, précédente, date) d'une série."""
    if s is None or len(s) == 0:
        return None, None, None
    v = float(s.iloc[-1]); p = float(s.iloc[-2]) if len(s) > 1 else None
    return v, p, s.index[-1]


def mx_z(s, window=252):
    """Écart à la moyenne en écarts-types sur la fenêtre (robuste aux séries courtes)."""
    if s is None or len(s) < 30:
        return None
    w = s.iloc[-window:]
    sd = float(w.std())
    return None if not sd else float((w.iloc[-1] - w.mean()) / sd)


def mx_chg(s, n):
    if s is None or len(s) <= n:
        return None
    return float(s.iloc[-1] / s.iloc[-1 - n] - 1)


def mx_z_change(s, n=20, window=252):
    """z-score de la variation sur n séances par rapport aux variations de l'année."""
    if s is None or len(s) < window // 2 + n:
        return None
    ch = s.diff(n).dropna().iloc[-window:]
    sd = float(ch.std())
    return None if not sd else float((ch.iloc[-1] - ch.mean()) / sd)


# ── Surprise macroéconomique ──────────────────────────────────────────────────
def mx_event_surprise(actual, forecast, previous):
    """Surprise standardisée d'une publication : (Actuel - Consensus) / échelle.
    Échelle = écart Consensus - Précédent (ampleur du mouvement attendu), avec un plancher de 5 % du
    consensus : faute d'historique de consensus, c'est l'estimation la plus stable de « l'erreur normale »."""
    try:
        a = _to_num(actual); f = _to_num(forecast); p = _to_num(previous)
    except Exception:
        return None
    if a is None or f is None:
        return None
    scale = max(abs(f - p) if p is not None else 0.0, abs(f) * 0.05, 1e-9)
    if scale < 1e-6 and a != f:
        scale = max(abs(a) * 0.05, 0.1)
    return max(-3.0, min(3.0, (a - f) / scale))


def mx_events_frame(events):
    """Calendrier brut -> DataFrame normalisé avec date UTC, catégorie, polarité et surprise signée."""
    if not events:
        return pd.DataFrame()
    d = pd.DataFrame(events)
    for c in ("title", "country", "impact", "actual", "forecast", "previous", "date"):
        if c not in d.columns:
            d[c] = ""
    d["dt"] = d["date"].map(_parse_utc)
    d = d[d["dt"].notna()].copy()
    d["cat"] = d["title"].map(macro_category)
    d["pol"] = d["title"].map(macro_polarity)
    d["has_actual"] = d["actual"].astype(str).str.strip().isin(["", "nan", "None"]) == False
    d["z"] = [mx_event_surprise(a, f, p) if h else None
              for a, f, p, h in zip(d["actual"], d["forecast"], d["previous"], d["has_actual"])]
    d["zs"] = [(z * pol) if (z is not None and pol) else None for z, pol in zip(d["z"], d["pol"])]
    d["w"] = d["impact"].map(MX_IMPACT_W).fillna(0.2)
    return d


def mx_surprise_index(ev, ccy, cats=None, horizon_days=30, tau=10.0):
    """Indice de surprise d'une devise (-100 à +100), façon Citi Economic Surprise Index :
    moyenne pondérée (importance x décroissance exp(-âge/τ)) des surprises signées des 30 derniers jours."""
    if ev is None or ev.empty:
        return None, 0
    now = datetime.utcnow()
    d = ev[(ev["country"] == ccy) & ev["zs"].notna()]
    if cats:
        d = d[d["cat"].isin(cats)]
    age = (now - d["dt"]).dt.total_seconds() / 86400
    d = d[(age >= 0) & (age <= horizon_days)]
    if d.empty:
        return None, 0
    age = (now - d["dt"]).dt.total_seconds() / 86400
    wt = d["w"] * np.exp(-age / tau)
    m = float((d["zs"] * wt).sum() / wt.sum())
    n_eff = float(wt.sum() ** 2 / (wt ** 2).sum())          # nombre effectif de publications
    m *= n_eff / (n_eff + 2.0)                              # peu de publications = indice modéré
    return float(np.tanh(m / 1.5) * 100), len(d)


# ── Politique monétaire ───────────────────────────────────────────────────────
def mx_policy(data, ev_rates):
    """Par devise : taux actuel, variation sur 6 mois, dernière décision, prochaine décision et consensus."""
    out = {}
    now = datetime.utcnow()
    for ccy, (cb, _, fred_id) in MX_CB.items():
        rec = {"cb": cb, "rate": None, "chg6m": None, "last_move": None, "last_date": None,
               "next_date": None, "next_cons": None, "src": None, "series": None}
        s = data["bis"].get(ccy)
        if s is not None and len(s):
            rec["src"] = "BIS"
        elif fred_id and fred_id in data["fred"]:
            s = data["fred"][fred_id]; rec["src"] = "FRED"
        if s is not None and len(s):
            s = s.sort_index(); rec["series"] = s; rec["rate"] = float(s.iloc[-1])
            past = s[s.index <= s.index[-1] - pd.Timedelta(days=182)]
            if len(past):
                rec["chg6m"] = float(s.iloc[-1] - past.iloc[-1])
            moves = s.diff()
            moves = moves[moves.abs() > 1e-9]
            if len(moves):
                rec["last_move"] = float(moves.iloc[-1]); rec["last_date"] = moves.index[-1]
        if ev_rates is not None and not ev_rates.empty:
            d = ev_rates[ev_rates["country"] == ccy].sort_values("dt")
            done = d[d["has_actual"]]
            if rec["rate"] is None and len(done):
                v = _to_num(done.iloc[-1]["actual"])
                if v is not None:
                    rec["rate"] = v; rec["src"] = "Calendrier"
                    pv = _to_num(done.iloc[-1]["previous"])
                    if pv is not None and abs(v - pv) > 1e-9:
                        rec["last_move"] = v - pv; rec["last_date"] = done.iloc[-1]["dt"]
            nxt = d[(d["dt"] >= now) & (~d["has_actual"])]
            if len(nxt):
                rec["next_date"] = nxt.iloc[0]["dt"]; rec["next_cons"] = _to_num(nxt.iloc[0]["forecast"])
        out[ccy] = rec
    return out


def mx_fed_pricing(data):
    """Anticipations de la Fed : taux implicite des Fed funds futures (100 - prix) et écart 2 ans - Fed."""
    res = {"implied": None, "effr": None, "bp": None, "spread2y": None}
    zq = data["yahoo"].get("ZQ=F")
    effr = data["fred"].get("DFF")
    if zq is not None and len(zq):
        res["implied"] = 100 - float(zq.iloc[-1])
    if effr is not None and len(effr):
        res["effr"] = float(effr.iloc[-1])
    if res["implied"] is not None and res["effr"] is not None:
        res["bp"] = (res["implied"] - res["effr"]) * 100
    d2, ft = data["fred"].get("DGS2"), data["fred"].get("DFEDTARU")
    if d2 is not None and ft is not None and len(d2) and len(ft):
        res["spread2y"] = (float(d2.iloc[-1]) - (float(ft.iloc[-1]) - 0.125)) * 100
    return res


def mx_stance(policy, ev, fed):
    """Score Hawkish / Dovish par devise (-100 à +100).
    40 % dynamique des taux (6 mois) · 30 % trajectoire attendue (consensus de la prochaine décision ;
    pour l'USD : Fed funds futures et écart 2 ans - Fed) · 20 % surprises d'inflation · 10 % croissance/emploi."""
    out = {}
    for ccy, p in policy.items():
        parts, wts, detail = [], [], []
        if p["chg6m"] is not None:
            parts.append(np.tanh(p["chg6m"] / 0.5)); wts.append(0.4)
            detail.append(f"taux {p['chg6m']*100:+.0f} pb sur 6 mois")
        exp_ = None
        if p["next_cons"] is not None and p["rate"] is not None:
            exp_ = (p["next_cons"] - p["rate"]) * 100
        if ccy == "USD":
            cands = [x for x in (fed.get("bp"), (fed.get("spread2y") or 0) * 0.5 if fed.get("spread2y") is not None else None,
                                 exp_) if x is not None]
            exp_ = float(np.mean(cands)) if cands else None
        if exp_ is not None:
            parts.append(np.tanh(exp_ / 25)); wts.append(0.3)
            detail.append(f"attendu {exp_:+.0f} pb")
        si, n_i = mx_surprise_index(ev, ccy, cats=["Inflation"], horizon_days=60, tau=20)
        if si is not None:
            parts.append(si / 100); wts.append(0.2); detail.append(f"surprises inflation {si:+.0f}")
        sg, n_g = mx_surprise_index(ev, ccy, cats=["Emploi", "Croissance"], horizon_days=45, tau=15)
        if sg is not None:
            parts.append(sg / 100); wts.append(0.1); detail.append(f"surprises activité {sg:+.0f}")
        if not wts:
            out[ccy] = (None, "Indisponible", "")
            continue
        sc = float(np.dot(parts, wts) / sum(wts) * 100)
        lab = "Hawkish" if sc >= 25 else ("Dovish" if sc <= -25 else "Neutre")
        out[ccy] = (sc, lab, " · ".join(detail))
    return out


def mx_risk_regime(data):
    """Régime Risk-On / Risk-Off (-100 à +100) : moyenne de z-scores sur un an.
    VIX (niveau, inversé) · spread High Yield (variation 20 j, inversé) · S&P 500 (performance 20 j) ·
    DXY (performance 20 j, inversé : dollar refuge) · conditions financières NFCI (inversé)."""
    comps = []
    def add(name, z, sign, how):
        if z is not None:
            comps.append((name, float(np.clip(z * sign, -3, 3)), how))
    vix = data["yahoo"].get("^VIX")
    if vix is None: vix = data["fred"].get("VIXCLS")
    add("VIX", mx_z(vix), -1, "niveau vs 1 an")
    add("Spread High Yield", mx_z_change(data["fred"].get("BAMLH0A0HYM2")), -1, "variation 20 j")
    add("S&P 500", mx_z_change(data["yahoo"].get("^GSPC")), 1, "variation 20 j")
    dxy = data["yahoo"].get("DX-Y.NYB")
    if dxy is None: dxy = data["fred"].get("DTWEXBGS")
    add("Dollar (DXY)", mx_z_change(dxy), -1, "variation 20 j")
    add("Conditions financières", mx_z(data["fred"].get("NFCI"), 104), -1, "niveau vs 2 ans")
    if not comps:
        return None, "Indisponible", comps
    sc = float(np.tanh(np.mean([c[1] for c in comps]) / 1.2) * 100)
    lab = "Risk-On" if sc >= 20 else ("Risk-Off" if sc <= -20 else "Neutre")
    return sc, lab, comps


def mx_strength(data):
    """Force relative des devises (%, vs moyenne du panier de 8) sur 1 j, 1 s, 1 m, 3 m."""
    hz = {"1 j": 1, "1 sem.": 5, "1 mois": 21, "3 mois": 63}
    rows = {}
    for lab, n in hz.items():
        r = {"USD": 0.0}
        for ccy, (tk, sgn) in MX_FX.items():
            s = data["yahoo"].get(tk)
            ch = mx_chg(s, n)
            if ch is None:
                r[ccy] = None
            else:
                r[ccy] = float(np.log1p(ch)) * sgn * 100
        vals = [v for v in r.values() if v is not None]
        if len(vals) < 4:
            continue
        m = float(np.mean(vals))
        rows[lab] = {c: (r[c] - m if r.get(c) is not None else None) for c in MX_CCYS}
    return pd.DataFrame(rows).reindex(MX_CCYS) if rows else pd.DataFrame()


def mx_expected_vol(row, regime_score, ev):
    """Volatilité attendue d'une annonce à venir : importance x sensibilité récente de la devise
    (surprises absolues moyennes) x régime de marché (stress = réactions amplifiées)."""
    base = MX_IMPACT_W.get(str(row.get("impact")), 0.2)
    if row.get("cat") == "Taux":
        base *= 1.3
    sens = 1.0
    if ev is not None and not ev.empty:
        h = ev[(ev["country"] == row.get("country")) & ev["z"].notna()]
        if len(h) >= 3:
            sens = float(np.clip(h["z"].abs().mean(), 0.5, 2.0))
    stress = 1.25 if (regime_score is not None and regime_score <= -20) else 1.0
    v = base * sens * stress
    lab = "Forte" if v >= 1.3 else ("Moyenne" if v >= 0.6 else "Faible")
    return v, lab


MX_METHOD_MD = r"""
#### Organisation de l'écran
| Zone | Contenu | Usage |
|---|---|---|
| Bandeau | Régime Risk-On / Risk-Off, DXY, VIX, courbe 10 ans - 2 ans, spread HY - IG | Lecture du contexte en 5 secondes |
| Synthèse & biais | Biais par devise, force des devises, composantes du régime, annonces à 72 h | Décider quelles devises acheter ou vendre |
| Calendrier & surprises | Indice de surprise par devise, fil des publications et impact par actif | Préparer et lire chaque annonce |
| Politique monétaire | Taux directeurs, dernière et prochaine décision, Fed funds futures, bilans | Orientation des banques centrales |
| Inflation & Emploi · Croissance | Indicateurs clés (actuel, précédent, consensus, surprise) et séries longues | Tendance de fond |
| Liquidité & Sentiment | Courbe des taux, spreads de crédit, M2, conditions financières, DXY, VIX | Appétit pour le risque |

#### Métriques affichées par indicateur
**Actuel** (dernière valeur), **Précédent**, **Consensus** (prévision des économistes, issue du calendrier) et **Surprise** en écarts-types (σ). Le signe de la surprise est corrigé de la polarité : un chômage plus bas que prévu compte comme une surprise positive.

#### Surprise macroéconomique
Pour chaque publication : `z = (Actuel − Consensus) / échelle`, où l'échelle est l'écart Consensus − Précédent (l'ampleur du mouvement que le marché attendait), avec un plancher de 5 % du consensus. Le résultat est borné à ±3 σ.

L'**indice de surprise d'une devise** (-100 à +100, sur le modèle du Citi Economic Surprise Index) est la moyenne des z signés des 30 derniers jours. Chaque publication est pondérée par son importance (Fort 1 · Moyen 0,5 · Faible 0,2) et par une décroissance `exp(−âge / 10 jours)`. La moyenne est ensuite modérée par `n / (n + 2)`, où n est le nombre effectif de publications : une seule surprise ne suffit pas à saturer l'indice. Le tout est ramené à l'échelle par `tanh(m / 1,5) × 100`.

**Volatilité attendue d'une annonce à venir** = importance × sensibilité récente de la devise × stress du marché.
- La sensibilité est la moyenne des |z| récents de la devise, bornée entre 0,5 et 2.
- Le stress vaut ×1,25 quand le régime est Risk-Off.
- Une décision de taux compte ×1,3.

#### Biais Hawkish / Dovish par devise (-100 à +100)
| Composante | Poids | Mesure |
|---|---|---|
| Dynamique des taux | 40 % | variation du taux directeur sur 6 mois, `tanh(Δ / 50 pb)` |
| Trajectoire attendue | 30 % | consensus de la prochaine décision moins le taux actuel ; pour l'USD, moyenne avec les Fed funds futures et l'écart US 2 ans - Fed |
| Surprises d'inflation | 20 % | indice de surprise limité à l'inflation, 60 jours |
| Surprises d'activité | 10 % | emploi et croissance, 45 jours |

Hawkish au-dessus de +25, Dovish en dessous de −25. Les poids sont recalculés sur les composantes disponibles.

**Biais global d'une devise** = 45 % orientation monétaire + 30 % indice de surprise + 25 % force de marché sur 1 mois. L'écart entre la devise la plus forte et la plus faible signale la paire où les fondamentaux divergent le plus.

#### Régime Risk-On / Risk-Off (-100 à +100)
Moyenne des z-scores sur un an, bornés à ±3, puis `tanh(m / 1,2) × 100` :
- VIX, en niveau, inversé ;
- spread High Yield, en variation sur 20 jours, inversé ;
- S&P 500, en performance sur 20 jours ;
- DXY, en performance sur 20 jours, inversé (le dollar sert de refuge) ;
- conditions financières de la Chicago Fed (NFCI), inversées.

Risk-On au-dessus de +20, Risk-Off en dessous de −20.

#### Force des devises
Rendement logarithmique de chaque devise contre l'USD, puis écart à la moyenne du panier de 8 devises, sur 1 jour, 1 semaine, 1 mois et 3 mois.

#### Sources de données
| Source | Coût | Données | Fréquence de mise à jour ici |
|---|---|---|---|
| FRED (Fed de Saint-Louis), export CSV public | gratuit, sans clé | inflation, emploi, PIB, taux, courbe, spreads, M2, bilans, VIX, NFCI | 6 h |
| BIS (Banque des règlements internationaux) | gratuit, sans clé | taux directeurs quotidiens des 8 banques centrales | 12 h |
| Yahoo Finance | gratuit, non officiel | DXY, VIX, S&P 500, change, or, pétrole, Bitcoin, Fed funds futures | 30 min |
| TradingView puis ForexFactory | gratuit, non officiel | calendrier, consensus, chiffres publiés | 30 min, chaque minute autour d'une annonce |

**Pour aller plus loin (payant)**
- Trading Economics : consensus historiques, ce qui permettrait un vrai écart-type de surprise par indicateur. C'est le meilleur gain de précision.
- Financial Modeling Prep et Polygon : cours en temps réel.
- CME FedWatch ou un fournisseur de swaps (€STR, SONIA, TONA) : courbe complète des anticipations de taux.
- Bloomberg ou Refinitiv : couverture institutionnelle complète.

#### Architecture technique
| Couche | Version actuelle | Version cible |
|---|---|---|
| Interface | Streamlit et Plotly, une seule application, déployée sur Streamlit Cloud | Next.js avec TypeScript, et TradingView Lightweight Charts ou ECharts, pour un rendu temps réel |
| Données | Python (pandas) et requests, en appels parallèles | Une API FastAPI qui alimente l'interface |
| Cache | `st.cache_data` | Redis entre les sources et l'API |
| Stockage | Supabase | Supabase (Postgres) pour l'historique des publications et des consensus, nécessaire à l'écart-type de surprise par indicateur |
| Collecte | à l'ouverture de la page | Un planificateur (APScheduler, ou une tâche Supabase) qui collecte en continu, plutôt qu'à l'ouverture de la page |

Le biais est une **aide à la décision** : il résume l'état des fondamentaux. Ce n'est pas un signal d'entrée, il se confirme toujours par l'analyse technique et la gestion du risque.
"""


# ── RECHERCHE ET EXPORT DE TRADES ─────────────────────────────────────────────
def trade_filters(prefix, df_all):
    """Filtres à cocher communs au journal et à l'export. Renvoie la requête (dict)."""
    dates_ = sorted(df_all["date"].dropna().astype(str).unique().tolist()) if not df_all.empty else []
    d_min = date.fromisoformat(dates_[0][:10]) if dates_ else date(2024, 1, 1)
    d_max = date.fromisoformat(dates_[-1][:10]) if dates_ else date.today()
    with st.container(horizontal=True, key=f"{prefix}_filters", gap="small"):
        f_from, f_to = period_filter("Période", d_min, d_max, f"{prefix}per")
        f_sym = check_filter("Actifs", sorted(df_all["symbol"].dropna().astype(str).unique().tolist()),
                             f"{prefix}_sym", f"{prefix}fs", icon=":material/candlestick_chart:")
        f_mode = check_filter("Comptes", allowed_accounts(), f"{prefix}_mode", f"{prefix}fm",
                              icon=":material/account_balance_wallet:")
        f_dir = check_filter("Direction", ["LONG", "SHORT"], f"{prefix}_dir", f"{prefix}fd", icon=":material/swap_vert:")
        f_strat = check_filter("Stratégies", sorted(df_all["strategy"].dropna().astype(str).unique().tolist())
                               if "strategy" in df_all.columns else [], f"{prefix}_strat", f"{prefix}fst",
                               all_label="Toutes", icon=":material/strategy:")
        f_res = check_filter("Résultat", ["Gagnants", "Perdants"], f"{prefix}_res", f"{prefix}fr", icon=":material/balance:")
    f_txt = st.text_input("Recherche", key=f"{prefix}_txt", label_visibility="collapsed",
                          placeholder="Recherche libre : notes, stratégie, émotion, identifiant MT5…")
    return {"from": f_from, "to": f_to, "sym": list(f_sym), "mode": list(f_mode), "dir": list(f_dir),
            "strat": list(f_strat), "res": list(f_res), "txt": (f_txt or "").strip()}

def apply_trade_filters(df, q):
    if df.empty or not q:
        return df
    d = df
    if q.get("from"): d = d[d["date"].astype(str) >= str(q["from"])]
    if q.get("to"):   d = d[d["date"].astype(str) <= str(q["to"])]
    if q.get("sym"):  d = d[d["symbol"].isin(q["sym"])]
    if q.get("mode"): d = d[d["trade_mode"].isin(q["mode"])]
    if q.get("dir"):  d = d[d["direction"].isin(q["dir"])]
    if q.get("strat") and "strategy" in d.columns: d = d[d["strategy"].isin(q["strat"])]
    if q.get("res") and len(q["res"]) == 1:
        d = d[d["pnl"] > 0] if q["res"][0] == "Gagnants" else d[d["pnl"] <= 0]
    if q.get("txt"):
        cols = [c for c in ("notes", "strategy", "mood", "mt5_id", "symbol") if c in d.columns]
        hay = d[cols].astype(str).agg(" ".join, axis=1).str.lower()
        d = d[hay.str.contains(q["txt"].lower(), regex=False, na=False)]
    return d

def describe_query(q):
    if q.get("last"):
        return f"{q['last']} derniers trades"
    parts = []
    if q.get("from") or q.get("to"):
        f, t = q.get("from"), q.get("to")
        parts.append(f"du {f:%d/%m/%Y} au {t:%d/%m/%Y}" if f and t and f != t else (f"le {f:%d/%m/%Y}" if f else ""))
    for k in ("sym", "mode", "dir", "strat", "res"):
        if q.get(k):
            parts.append(", ".join(map(str, q[k][:3])) + ("…" if len(q[k]) > 3 else ""))
    if q.get("txt"):
        parts.append(f"« {q['txt']} »")
    return " · ".join(p for p in parts if p) or "tous les trades"

_EXPORT_COLS = [("date", "Date"), ("time", "Heure"), ("close_datetime", "Clôture"), ("symbol", "Actif"),
                ("direction", "Direction"), ("trade_mode", "Compte"), ("volume", "Volume"), ("entry", "Entrée"),
                ("exit", "Sortie"), ("sl", "SL"), ("tp", "TP"), ("pnl", "P&L"), ("rr", "R:R"),
                ("strategy", "Stratégie"), ("mood", "Émotion"), ("exit_reason", "Motif de clôture"),
                ("mae", "MAE"), ("mfe", "MFE"), ("mt5_id", "ID MT5"), ("notes", "Notes")]

def export_frame(df):
    cols = [(c, l) for c, l in _EXPORT_COLS if c in df.columns]
    out = df[[c for c, _ in cols]].rename(columns=dict(cols))
    return out.sort_values([c for c in ("Date", "Heure") if c in out.columns])

@st.dialog("Exporter des trades", width="large")
def export_dialog():
    df_all = get_df("Tous")
    st.caption("Coche les filtres : rien de coché = tout est pris. Le fichier ne contient que les trades retenus.")
    q = trade_filters("ex", df_all)
    d = apply_trade_filters(df_all, q)
    tot = d["pnl"].sum() if not d.empty else 0.0
    st.markdown(f"**{len(d)}** trade(s) retenu(s) · P&L {fmt(tot)} · {describe_query(q)}")
    if d.empty:
        st.info("Aucun trade pour ces filtres.")
        return
    fmt_x = st.radio("Format", ["Excel (.xlsx)", "CSV (Excel FR, séparateur ;)"], horizontal=True, key="ex_fmt")
    xf = export_frame(d)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if fmt_x.startswith("Excel"):
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                xf.to_excel(w, index=False, sheet_name="Trades")
                ws = w.sheets["Trades"]
                for i, col in enumerate(xf.columns, 1):
                    ws.column_dimensions[ws.cell(1, i).column_letter].width = max(10, min(40, len(str(col)) + 4))
                ws.freeze_panes = "A2"
            st.download_button("Télécharger le fichier Excel", buf.getvalue(), file_name=f"trades_{stamp}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               type="primary", icon=":material/download:", use_container_width=True)
            return
        except Exception:
            st.warning("Excel indisponible sur ce serveur (module openpyxl absent) : export CSV proposé.")
    csv = xf.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
    st.download_button("Télécharger le fichier CSV", csv, file_name=f"trades_{stamp}.csv", mime="text/csv",
                       type="primary", icon=":material/download:", use_container_width=True)

if st.session_state.page == "dashboard":
    _tdb = get_theme()
    df_all_f    = get_df("Tous")
    syms_avail  = sorted(df_all_f["symbol"].unique().tolist()) if not df_all_f.empty else []
    moods_avail = list(MOODS)   # émotions déclarées ou déduites
    strat_avail = sorted(df_all_f["strategy"].unique().tolist()) if not df_all_f.empty else []
    dates       = sorted(df_all_f["date"].tolist()) if not df_all_f.empty else []
    d_min = date.fromisoformat(dates[0])  if dates else date(2024,1,1)
    d_max = date.fromisoformat(dates[-1]) if dates else date.today()

    # ── En-tête compact : titre + date à gauche, filtres repliables à droite ──
    _dh1, _dh2 = st.columns([1.6, 2.4])
    with _dh1:
        st.markdown(
            f"<div style='display:flex;align-items:baseline;gap:12px;padding-top:4px'>"
            f"<span style='font-size:22px;font-weight:800;color:{_tdb['text']}'>Dashboard</span>"
            f"<span style='font-size:12px;color:{_tdb['muted']}'>"
            f"{datetime.now().strftime('%d/%m/%Y')} · {selection_label()}</span></div>",
            unsafe_allow_html=True)
    with _dh2:
        with st.container(horizontal=True, key="dash_filters", gap="small"):
            f_sym   = check_filter("Actifs", syms_avail, "dsel_sym", "dfs", icon=":material/candlestick_chart:")
            f_mood  = check_filter("Émotions", moods_avail, "dsel_mood", "dfm", all_label="Toutes", icon=":material/mood:")
            f_strat = check_filter("Stratégies", strat_avail, "dsel_strat", "dfst", all_label="Toutes", icon=":material/strategy:")
            f_date_from, f_date_to = period_filter("Période", d_min, d_max, "dper")

    df = get_df()                       # trades des comptes sélectionnés dans le filtre du haut
    _df_scope = df.copy()
    if not df.empty:
        # Émotions : déclarées, ou déduites du comportement si la case est vide
        try:
            _ann = behavior_analysis(_df_scope)["d"]
            if "id" in df.columns and "id" in _ann.columns:
                _mf = dict(zip(_ann["id"], _ann["mood_final"]))
                _ms = dict(zip(_ann["id"], _ann["mood_src"]))
                df["mood"] = df["id"].map(_mf).fillna(df.get("mood"))
                df["mood_src"] = df["id"].map(_ms).fillna("déclarée")
        except Exception:
            pass
        if f_sym:   df = df[df["symbol"].isin(f_sym)]
        if f_mood:  df = df[df["mood"].isin(f_mood)]
        if f_strat: df = df[df["strategy"].isin(f_strat)]
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
        _W, _L, _O, _A = _tdb["win"], _tdb["loss"], _tdb["orange"], _tdb["alt"]
        with c1: kpi('<i class="fa-solid fa-coins"></i>',          "P&L Net",      fmt(total),       f"{len(df)} trades",             _W if total>=0 else _L)
        with c2: kpi('<i class="fa-solid fa-bullseye"></i>',       "Win Rate",     f"{wr_val:.1f}%", f"{len(wins)}W · {len(losses)}L",_W if wr_val>=50 else _L)
        with c3: kpi('<i class="fa-solid fa-scale-balanced"></i>', "Profit Factor",f"{pf:.2f}" if pf else "—","Gain/Perte",          _W if (pf or 0)>=1.5 else _O)
        with c4: kpi('<i class="fa-solid fa-arrow-trend-down"></i>',"Max Drawdown",f"${mdd:,.2f}",   "Perte cumulée max",             _L)
        with c5: kpi('<i class="fa-solid fa-bolt"></i>',           "R:R Moyen",   f"{avg_rr:.2f}R" if avg_rr else "—","Risque/Récomp",_A)
        with c6: kpi('<i class="fa-solid fa-arrow-trend-up"></i>', "Gain moyen",   fmt(avg_w),       "Par trade gagnant",             _W)

        # Analyse comportementale : contexte calculé sur les comptes sélectionnés, stats sur les trades filtrés
        try:
            _bh = behavior_analysis(_df_scope, keep_ids=set(df["id"]) if "id" in df.columns else None)
        except Exception as _e_bh:
            _bh = {"n": 0, "error": str(_e_bh)}
        try:
            _risk = risk_analysis(df)
        except Exception as _e_rk:
            _risk = {"n": 0, "error": str(_e_rk)}
        try:
            _recos = all_recommendations(_bh, _risk) if _bh.get("n") else risk_recommendations(_risk)
        except Exception:
            _recos = []
        if "reco_show" not in st.session_state:
            st.session_state.reco_show = False
        _top = [r for r in _recos if r["level"] in ("critique", "attention")][:2]
        if _top and st.session_state.reco_show:
            _lv = {"critique": _tdb["loss"], "attention": _tdb["orange"]}
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:8px 0 2px'>"
                f"<span style='font-size:10.5px;letter-spacing:1px;text-transform:uppercase;font-weight:800;"
                f"color:{_tdb['muted']}'>À surveiller</span>" + "".join(
                    f"<span style='font-size:12px;font-weight:700;color:{_lv[r['level']]};background:{_lv[r['level']]}14;"
                    f"border:1px solid {_lv[r['level']]}40;border-radius:8px;padding:3px 10px'>"
                    f"{'●' if r['level'] == 'critique' else '▲'} {r['title']}</span>" for r in _top) +
                f"<span style='font-size:11px;color:{_tdb['muted']}'>détails : onglet Recommandations</span></div>",
                unsafe_allow_html=True)

        # Comparaison par compte : une seule ligne de pastilles (pas une 2e rangée de cartes)
        _sc_dash = _resolve_scope(None)
        if len(_sc_dash) >= 2 and "trade_mode" in df.columns:
            _active_modes = [m for m in TRADE_MODES if not df[df["trade_mode"]==m].empty]
            if len(_active_modes) >= 2:
                _chips = ""
                for _m in _active_modes:
                    _df_m = df[df["trade_mode"]==_m]
                    _pm = _df_m["pnl"].sum()
                    _wr_m = len(_df_m[_df_m["pnl"]>0])/len(_df_m)*100 if len(_df_m) else 0
                    _cc = account_color(_m)
                    _chips += (f"<span style='display:inline-flex;align-items:center;gap:8px;"
                               f"background:{_tdb['card']};border:1px solid {_tdb['border']};"
                               f"border-left:3px solid {_cc};border-radius:9px;padding:4px 12px;"
                               f"margin:0 8px 6px 0;font-size:12px;color:{_tdb['muted']}'>"
                               f"<b style='color:{_tdb['text']}'>{_m}</b>"
                               f"<b style='color:{_W if _pm>=0 else _L};font-family:JetBrains Mono,monospace'>{fmt(_pm)}</b>"
                               f"{len(_df_m)} trades · {_wr_m:.0f}% win</span>")
                st.markdown(f"<div style='margin:6px 0 2px'>{_chips}</div>", unsafe_allow_html=True)

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

        _gridline = _theme["border"]
        _cs = get_chart_style()          # profil graphique lié au design
        if _cs["transparent"]:
            _bg = "rgba(0,0,0,0)"

        def _base_layout(height=260, showlegend=False, **kwargs):
            return chart_layout(_theme, _cs, height=height, showlegend=showlegend, **kwargs)

        def _style_axes(fig, xprefix="", yprefix="", xtickangle=0, free_y=False):
            chart_axes(fig, _theme, _cs, xprefix=xprefix, yprefix=yprefix,
                       xtickangle=xtickangle, free_y=free_y)

        def _card(title, subtitle=""):
            accent = _theme["accent"]
            sub_html = (f' <span style="font-size:11px;color:{_theme["muted"]}">{subtitle}</span>'
                        if subtitle else "")
            st.markdown(
                f'<div style="margin:8px 0 6px;display:flex;align-items:center;gap:8px">'
                f'<span style="font-size:13.5px;font-weight:700;color:{_theme["text"]};background:{accent}14;'
                f'border-left:3px solid {accent};border-radius:3px 999px 999px 3px;padding:3px 14px 3px 10px">{title}</span>'
                f'{sub_html}</div>',
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

        # Config commune : barre d'outils masquée par défaut (apparait au survol)
        _chart_cfg = chart_config(_cs)

        def _xaxis_pos(n):
            return dict(showticklabels=False, showgrid=False,
                        showline=False, zeroline=False)

        # ════════════════════════════════════════════════════════════════════
        # VUE D'ENSEMBLE : l'essentiel visible sans défiler
        # ════════════════════════════════════════════════════════════════════
        _base_cap = get_capital()
        _ov_pct = (f" · {((cumul.iloc[-1] if len(cumul) else 0)/_base_cap*100):+.2f}% du capital"
                   if _base_cap > 0 else "")
        ov1, ov2, ov3 = st.columns([2.3, 1.15, 1.55])
        with ov1:
            _card("Courbe de capital", f"{fmt(cumul.iloc[-1] if len(cumul) else 0)}{_ov_pct}")
            _eq_final = cumul.iloc[-1] if len(cumul) else 0
            _eq_col = _win if _eq_final >= 0 else _loss
            def _hex_rgba(h, a):
                h = h.lstrip("#"); r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
                return f"rgba({r},{g},{b},{a})"
            fig_eq = go.Figure(series_traces(
                pos_idx, cumul.tolist(), _eq_col, _cs,
                customdata=list(zip(df_s["symbol"].tolist(),
                                    df_s["direction"].tolist(), pos_labels)),
                hovertemplate=("<b>#%{x}</b> · %{customdata[2]}<br>"
                               "%{customdata[0]} %{customdata[1]}<br>"
                               "Capital : <b>%{y:+,.2f}$</b><extra></extra>")))
            fig_eq.update_layout(**_base_layout(height=235))
            _style_axes(fig_eq, yprefix="$")
            fig_eq.update_xaxes(**_xaxis_pos(n_pos))
            st.plotly_chart(fig_eq, use_container_width=True, config=_chart_cfg)

        with ov2:
            _card("Win / Loss")
            fig_pie = winloss_figure(len(wins), len(losses), wr_val, _theme, _cs, height=235)
            st.plotly_chart(fig_pie, use_container_width=True, config=_chart_cfg)

        with ov3:
            _card("P&L mensuel")
            fig_mo = category_figure(
                monthly["label"].tolist(), monthly["pnl"].tolist(),
                [_win if v>=0 else _loss for v in monthly["pnl"]], _theme, _cs,
                kind=_cs["monthly"], orientation="v",
                hovertemplate="<b>%{x}</b><br>%{y:+,.2f}$<extra></extra>")
            fig_mo.add_hline(y=0, line_dash="dot", line_color=_grid, line_width=1)
            fig_mo.update_layout(**_base_layout(height=235))
            _style_axes(fig_mo, yprefix="$")
            st.plotly_chart(fig_mo, use_container_width=True, config=_chart_cfg)


        # ════════════════════════════════════════════════════════════════════
        # DÉTAIL PAR CATÉGORIE : un onglet par thème
        # ════════════════════════════════════════════════════════════════════
        (tab_reco, tab_perf, tab_bh, tab_risk, tab_assets, tab_psy, tab_cal, tab_last) = st.tabs([
            "Recommandations", "Performance", "Comportement & émotions", "Risque & Volume", "Actifs & Stratégies",
            "Psychologie", "Calendrier", "Derniers trades"])
        def _reco_card(r, T):
            c = {"critique": T["loss"], "attention": T["orange"], "info": T["accent"], "positif": T["win"]}[r["level"]]
            lab = {"critique": "critique", "attention": "attention", "info": "à savoir", "positif": "point fort"}[r["level"]]
            st.markdown(
                f"<div style='background:{T['card']};border:1px solid {T['border']};border-left:4px solid {c};"
                f"border-radius:4px 20px 20px 4px;padding:9px 13px;margin-bottom:8px'>"
                f"<div style='display:flex;gap:8px;align-items:center;flex-wrap:wrap'>"
                f"<span style='font-size:9.5px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;"
                f"color:{c};background:{c}16;border-radius:5px;padding:1px 6px'>{lab}</span>"
                f"<b style='font-size:13px;color:{T['text']}'>{r['title']}</b>"
                f"<span style='font-size:10.5px;color:{T['muted']};margin-left:auto'>{r.get('cat', '')}</span></div>"
                f"<div style='font-size:12px;color:{T['muted']};margin:4px 0 3px'>{r['detail']}</div>"
                f"<div style='font-size:12.5px;color:{T['text']}'><b style='color:{c}'>→</b> {r['action']}</div></div>",
                unsafe_allow_html=True)

        with tab_reco:
            _T = _theme
            if not _recos:
                st.info("Pas assez de trades sur la sélection pour générer des recommandations (5 minimum).")
            else:
                _cnt = {lv: sum(1 for r in _recos if r["level"] == lv) for lv in ("critique", "attention", "info", "positif")}
                _chips = [("critique", "critique(s)", _T["loss"]), ("attention", "à surveiller", _T["orange"]),
                          ("info", "à savoir", _T["accent"]), ("positif", "point(s) fort(s)", _T["win"])]
                st.markdown(
                    "<div style='display:flex;gap:10px;flex-wrap:wrap;margin:4px 0 12px'>" + "".join(
                        f"<span style='font-size:12.5px;font-weight:700;color:{c};background:{c}14;border:1px solid {c}40;"
                        f"border-radius:9px;padding:4px 12px'><b style='font-size:15px'>{_cnt[k]}</b> {lab}</span>"
                        for k, lab, c in _chips) +
                    f"<span style='font-size:11.5px;color:{_T['muted']};align-self:center'>Calculé sur "
                    f"{_bh.get('n') or _risk.get('n', 0)} trades · comptes : {selection_label()} · filtres du dashboard appliqués</span></div>",
                    unsafe_allow_html=True)
                st.toggle("Afficher le détail des recommandations", key="_reco_tg",
                          value=st.session_state.reco_show,
                          on_change=lambda: st.session_state.update(reco_show=st.session_state["_reco_tg"]),
                          help="Masqué par défaut pour garder le dashboard compact. Affiché, il active aussi "
                               "le bandeau « À surveiller » sous les KPI.")
            if _recos and st.session_state.reco_show:
                rc1, rc2 = st.columns([3, 2], gap="medium")
                with rc1:
                    _card("Priorités", "à corriger en premier")
                    _pri = [r for r in _recos if r["level"] in ("critique", "attention")]
                    if not _pri:
                        st.success("Aucun point critique ou à surveiller sur cette sélection.")
                    for r in _pri:
                        _reco_card(r, _T)
                with rc2:
                    _card("Points forts", "à conserver")
                    _pos = [r for r in _recos if r["level"] == "positif"]
                    if not _pos:
                        st.caption("Aucun point fort statistiquement net pour l'instant.")
                    for r in _pos:
                        _reco_card(r, _T)
                    _inf_r = [r for r in _recos if r["level"] == "info"]
                    if _inf_r:
                        _card("À savoir")
                        for r in _inf_r:
                            _reco_card(r, _T)
                st.caption("Chaque recommandation exige au moins 5 trades concernés. Les montants sont des moyennes par "
                           "trade, sur la sélection en cours.")

        with tab_perf:
            pf1, pf2 = st.columns(2)
            with pf1:
                # ── Progression du capital en % (base = capital de départ du compte) ──
                _base_cap = get_capital()
                _card("Progression du capital (%)",
                      f"Base : {_base_cap:,.0f}$" if _base_cap > 0
                      else "Capital de départ non défini")
                if _base_cap > 0:
                    _pct = (cumul / _base_cap * 100.0)
                    _pcol = _win if (_pct.iloc[-1] if len(_pct) else 0) >= 0 else _loss
                    def _hx_rgba(h, a):
                        h = h.lstrip("#"); r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
                        return f"rgba({r},{g},{b},{a})"
                    fig_pct = go.Figure(series_traces(
                        pos_idx, _pct.tolist(), _pcol, _cs, customdata=pos_labels,
                        hovertemplate="<b>#%{x}</b> · %{customdata}<br>"
                                      "Progression : <b>%{y:+.2f}%</b><extra></extra>"))
                    fig_pct.add_hline(y=0, line_color=_grid, line_width=1)
                    fig_pct.update_layout(**_base_layout(height=260))
                    _style_axes(fig_pct)
                    fig_pct.update_yaxes(ticksuffix="%")
                    fig_pct.update_xaxes(**_xaxis_pos(n_pos))
                    st.plotly_chart(fig_pct, use_container_width=True, config=_chart_cfg)
                    _final_pct = _pct.iloc[-1] if len(_pct) else 0
                    st.markdown(
                        f"<div style='color:{_thd['muted']};font-size:12px;margin:-4px 0 10px'>"
                        f"Progression cumulée : <b style='color:{_pcol}'>{_final_pct:+.2f}%</b> "
                        f"sur un capital de départ de {_base_cap:,.0f}$.</div>",
                        unsafe_allow_html=True)
                else:
                    st.info("Définissez le capital de départ de ce compte dans "
                            "**Utilisateurs & comptes** (réservé à l'admin) pour afficher la progression en %.")
                st.markdown(" ")

            with pf2:
                _card("P&L par Position", f"{n_pos} trades — 1 barre = 1 position")
                fig_tl = go.Figure(go.Bar(
                    x=pos_idx,
                    y=df_s["pnl"].tolist(),
                    marker_color=[_win if p>0 else _loss for p in df_s["pnl"]],
                    marker_opacity=_cs["bar_opacity"],
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
                _style_axes(fig_tl, yprefix="$")
                fig_tl.update_xaxes(**_xaxis_pos(n_pos))
                st.plotly_chart(fig_tl, use_container_width=True, config=_chart_cfg)

        with tab_bh:
            if _bh.get("n", 0) < 5:
                st.info("Pas assez de trades sur la sélection pour une analyse comportementale (5 minimum).")
            else:
                _T = _theme
                _lvc = {"critique": _T["loss"], "attention": _T["orange"], "info": _T["accent"], "positif": _T["win"]}
                st.caption(f"{_bh['n']} trades analysés · comptes : {selection_label()} · filtres du dashboard appliqués. "
                           "Les enchaînements sont calculés compte par compte ; les délais sont des médianes.")
                if _bh.get("time_share", 100) < 50:
                    st.warning("Moins de la moitié de ces trades ont une heure d'ouverture : les délais sont calculés "
                               "sur la date seule et restent approximatifs.")
                G = _bh["gaps"]
                kk = st.columns(6)
                _kp = [("fa-arrows-left-right", "Entre 2 pertes", G["LL"], _T["loss"]),
                       ("fa-arrows-left-right", "Entre 2 gains", G["WW"], _T["win"]),
                       ("fa-arrow-trend-up", "Perte → gain", G["LW"], _T["accent"]),
                       ("fa-arrow-trend-down", "Gain → perte", G["WL"], _T["orange"])]
                for col, (ic, lab, st_, cc) in zip(kk[:4], _kp):
                    with col:
                        kpi(f'<i class="fa-solid {ic}"></i>', lab, fmt_gap(st_["median"]),
                            f"moy. {fmt_gap(st_['mean'])} · {st_['n']} cas", cc)
                with kk[4]:
                    _ra, _rw = _bh["resume_after_loss"], _bh["resume_after_win"]
                    kpi('<i class="fa-solid fa-stopwatch"></i>', "Reprise après perte", fmt_gap(_ra["median"]),
                        f"après un gain : {fmt_gap(_rw['median'])}",
                        _T["loss"] if (_ra["median"] or 0) < (_rw["median"] or 0) * 0.5 else _T["alt"])
                with kk[5]:
                    kpi('<i class="fa-solid fa-layer-group"></i>', "Séries max",
                        f"{_bh['max_win_streak']} G / {_bh['max_loss_streak']} P",
                        f"{_bh['trades_per_day_med']:.0f} trades/jour (médiane)", _T["alt"])

                b1, b2 = st.columns([2, 3], gap="medium")
                with b1:
                    _lvl, _lk, _ltxt = emotion_level(_bh)
                    _lc = _T[_lk]
                    _card("Niveau émotionnel", "émotions déclarées + déduites")
                    st.markdown(
                        f"<div style='background:{_T['card']};border:1px solid {_T['border']};border-radius:12px;padding:12px 14px'>"
                        f"<div style='display:flex;align-items:baseline;gap:10px'><span style='font-size:24px;font-weight:800;"
                        f"color:{_lc}'>{_lvl}</span><span style='font-size:12px;color:{_T['muted']}'>"
                        f"{_bh['reactive_share']:.0f} % de trades en état réactif · {_bh['tilt_episodes']} épisode(s) de tilt</span></div>"
                        f"<div style='height:7px;border-radius:4px;background:{_T['bg2']};margin:8px 0 6px;overflow:hidden'>"
                        f"<div style='width:{min(100, _bh['reactive_share']):.0f}%;height:100%;background:linear-gradient(90deg,"
                        f"{_T['orange']},{_T['loss']})'></div></div>"
                        f"<div style='font-size:12px;color:{_T['text']}'>{_ltxt}</div>"
                        f"<div style='font-size:11px;color:{_T['muted']};margin-top:6px'>{_bh['n_inferred']} émotion(s) déduite(s) "
                        f"du comportement à l'entrée (case vide ou « Neutre » par défaut de l'import MT5).</div></div>",
                        unsafe_allow_html=True)
                with b2:
                    _card("Espérance par émotion", "déclarées + déduites")
                    _bm = _bh["by_mood"].sort_values("mean")
                    fig_bm = category_figure(_bm["mood_final"].tolist(), _bm["mean"].round(2).tolist(),
                        [_T["win"] if v >= 0 else _T["loss"] for v in _bm["mean"]], _T, _cs, kind=_cs["ranking"],
                        orientation="h", texts=[f"{fmt(v)} · {int(n)} tr. · {w:.0f}%" for v, n, w in
                                                 zip(_bm["mean"], _bm["count"], _bm["wr"])],
                        hovertemplate="<b>%{y}</b><br>Espérance : %{x:+,.2f}$<extra></extra>")
                    fig_bm.add_vline(x=0, line_color=_grid, line_width=1)
                    _mx = float(max(abs(_bm["mean"].min()), abs(_bm["mean"].max()), 1))
                    fig_bm.update_xaxes(range=[min(0, _bm["mean"].min()) - _mx * 1.15, max(0, _bm["mean"].max()) + _mx * 1.15])
                    fig_bm.update_traces(cliponaxis=False)
                    fig_bm.update_layout(**_base_layout(height=max(190, 34 * len(_bm) + 40), margin=dict(l=90, r=20, t=10, b=26)))
                    _style_axes(fig_bm, xprefix="$")
                    st.plotly_chart(fig_bm, use_container_width=True, config=_chart_cfg)

                c1, c2 = st.columns(2, gap="medium")
                with c1:
                    _card("Réussite selon le contexte", f"ligne = moyenne générale ({_bh['base']['wr']:.0f} %)")
                    _cx = [c for c in _bh["context"] if c["n"] > 0]
                    fig_cx = category_figure([c["label"] for c in _cx][::-1], [round(c["wr"], 1) for c in _cx][::-1],
                        [(_T["win"] if c["wr"] >= _bh["base"]["wr"] else _T["loss"]) for c in _cx][::-1], _T, _cs,
                        kind=_cs["ranking"], orientation="h",
                        texts=[f"{c['wr']:.0f} % · {c['n']} tr. · {fmt(c['exp'])}" for c in _cx][::-1],
                        hovertemplate="<b>%{y}</b><br>Taux de réussite : %{x:.1f} %<extra></extra>")
                    fig_cx.add_vline(x=_bh["base"]["wr"], line_dash="dot", line_color=_T["muted"], line_width=1)
                    fig_cx.update_layout(**_base_layout(height=290, margin=dict(l=150, r=120, t=10, b=26)))
                    _style_axes(fig_cx); fig_cx.update_xaxes(ticksuffix="%", range=[0, 100])
                    st.plotly_chart(fig_cx, use_container_width=True, config=_chart_cfg)
                with c2:
                    _card("Espérance selon le rang du trade dans la journée", "par compte")
                    _rk = _bh["by_rank"]
                    fig_rk = category_figure([r["label"] for r in _rk], [round(r["exp"], 2) for r in _rk],
                        [_T["win"] if r["exp"] >= 0 else _T["loss"] for r in _rk], _T, _cs,
                        kind=("lollipop" if _cs["monthly"] == "lollipop" else "bar"), orientation="v",
                        customdata=[[r["n"], r["wr"]] for r in _rk],
                        hovertemplate="<b>%{x} trade du jour</b><br>Espérance : %{y:+,.2f}$<br>"
                                      "%{customdata[0]} trades · %{customdata[1]:.0f} % de réussite<extra></extra>")
                    fig_rk.add_hline(y=0, line_color=_grid, line_width=1)
                    fig_rk.update_layout(**_base_layout(height=290))
                    _style_axes(fig_rk, yprefix="$")
                    st.plotly_chart(fig_rk, use_container_width=True, config=_chart_cfg)

                _dd = _bh["d"]
                _inf = _dd[_dd["mood_src"] == "déduite"]
                with st.expander(f"Émotions déduites automatiquement · {len(_inf)} trade(s)"):
                    if _inf.empty:
                        st.caption("Toutes les émotions de la sélection sont renseignées.")
                    else:
                        _tab = _inf.sort_values("_t", ascending=False)[["_t", "trade_mode", "symbol", "pnl", "mood_inferred", "mood_reason"]].head(300)
                        _tab = _tab.rename(columns={"_t": "Ouverture", "trade_mode": "Compte", "symbol": "Actif", "pnl": "P&L",
                                                    "mood_inferred": "Émotion déduite", "mood_reason": "Raison (comportement à l'entrée)"})
                        st.dataframe(_tab, use_container_width=True, hide_index=True, height=260,
                                     column_config={"Ouverture": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm"),
                                                    "P&L": st.column_config.NumberColumn(format="%.2f $")})
                        st.caption("L'émotion est déduite uniquement du comportement au moment de l'entrée (reprise rapide "
                                   "après une perte, série en cours, taille de position, nombre de trades dans la journée), "
                                   "jamais du résultat du trade lui-même.")
                    if is_admin():
                        a1, a2 = st.columns(2)
                        with a1:
                            if not _inf.empty and st.button(f"Inscrire ces {len(_inf)} émotions dans le journal",
                                                            key="bh_save_moods", use_container_width=True):
                                _m = dict(zip(_inf["id"], _inf["mood_inferred"]))
                                for _t in st.session_state.trades:
                                    if _t.get("id") in _m:
                                        if not _t.get("mood_auto"):
                                            _t["mood_prev"] = _t.get("mood", "")
                                        _t["mood"] = _m[_t["id"]]; _t["mood_auto"] = True
                                (st.success if db_save(st.session_state.trades) else st.warning)(
                                    f"{len(_m)} émotion(s) inscrite(s), marquées « automatiques ». Modifier un trade "
                                    "à la main remplace son émotion par la tienne.")
                        with a2:
                            _n_auto = sum(1 for _t in st.session_state.trades if _t.get("mood_auto"))
                            if _n_auto and st.button(f"Annuler les {_n_auto} émotions inscrites automatiquement",
                                                     key="bh_undo_moods", use_container_width=True):
                                for _t in st.session_state.trades:
                                    if _t.get("mood_auto"):
                                        _t["mood"] = _t.pop("mood_prev", "")
                                        _t.pop("mood_auto", None)
                                (st.success if db_save(st.session_state.trades) else st.warning)("Émotions d'origine restaurées.")
                                st.rerun()
        with tab_risk:
            _R = _risk
            _T = _theme
            if _R.get("n", 0) >= 5:
                st.caption(f"{_R['n']} trades · comptes : {selection_label()} · filtres du dashboard appliqués. "
                           "R = distance entre l'entrée et le stop initial.")
                if _R.get("n_bad_exit", 0):
                    st.warning(f"{_R['n_bad_exit']} trades ont un prix de sortie égal au prix d'entrée (ancien import MT5) : "
                               "ils sont exclus de l'analyse des stops et des TP. Pour les corriger : page Import MT5, "
                               "réimporte tes rapports puis clique sur « Corriger les trades déjà importés ».")
                _mix = _R.get("exit_mix", pd.Series(dtype=float))
                kk = st.columns(6)
                with kk[0]: kpi('<i class="fa-solid fa-shield-halved"></i>', "Trades avec stop", f"{_R['sl_cov']:.0f} %",
                                "SL enregistré", _T["win"] if _R["sl_cov"] >= 90 else _T["orange"] if _R["sl_cov"] >= 60 else _T["loss"])
                with kk[1]: kpi('<i class="fa-solid fa-bullseye"></i>', "Trades avec TP", f"{_R['tp_cov']:.0f} %", "TP enregistré", _T["alt"])
                with kk[2]: kpi('<i class="fa-solid fa-circle-stop"></i>', "Stops touchés",
                                f"{float(_mix.get('Stop touché', 0)):.0f} %", f"{_R['n_measurable']} sorties mesurables", _T["loss"])
                with kk[3]: kpi('<i class="fa-solid fa-flag-checkered"></i>', "TP touchés",
                                f"{float(_mix.get('TP touché', 0)):.0f} %", "des sorties mesurables", _T["win"])
                with kk[4]: kpi('<i class="fa-solid fa-scale-balanced"></i>', "R:R prévu",
                                f"{_R['rr_plan_med']:.2f}" if _R.get("rr_plan_med") is not None else "—", "médiane TP / stop", _T["alt"])
                with kk[5]: kpi('<i class="fa-solid fa-ruler"></i>', "R réalisé",
                                f"{_R['R_med']:+.2f} R" if _R.get("R_med") is not None else "—",
                                (f"gagnants : {_R['R_win_med']:+.2f} R" if _R.get("R_win_med") is not None else "médiane par trade"),
                                _T["win"] if (_R.get("R_med") or 0) >= 0 else _T["loss"])
                g1, g2 = st.columns(2, gap="medium")
                with g1:
                    _card("Comment se terminent tes trades", "part des sorties mesurables")
                    _ee = _R.get("exit_exp")
                    if _ee is not None and len(_ee):
                        _cmap = {"Stop touché": _T["loss"], "Stop suiveur / point mort": _T["muted"], "TP touché": _T["win"],
                                 "Sortie manuelle en gain": _T["alt"], "Sortie manuelle en perte": _T["orange"],
                                 "Stop-out (marge)": _T["loss"]}
                        _labs = [l for l in _mix.index][::-1]
                        fig_ex = category_figure(_labs, [round(float(_mix[l]), 1) for l in _labs], [_cmap.get(l, _T["accent"]) for l in _labs],
                            _T, _cs, kind=_cs["ranking"], orientation="h",
                            texts=[f"{float(_mix[l]):.0f} % · {int(_ee.loc[l, 'count'])} tr. · {fmt(float(_ee.loc[l, 'mean']))}" for l in _labs],
                            hovertemplate="<b>%{y}</b><br>%{x:.1f} % des sorties<extra></extra>")
                        fig_ex.update_layout(**_base_layout(height=250, margin=dict(l=170, r=130, t=10, b=26)))
                        _style_axes(fig_ex); fig_ex.update_xaxes(ticksuffix="%", range=[0, max(100, float(_mix.max()) * 1.3)])
                        fig_ex.update_traces(cliponaxis=False)
                        st.plotly_chart(fig_ex, use_container_width=True, config=_chart_cfg)
                    else:
                        st.info("Aucune sortie mesurable (prix de sortie manquants).")
                with g2:
                    _card("Tes sorties manuelles par rapport au plan")
                    def _bar(label, frac, n, good_high, note):
                        if frac is None or n < 3:
                            return (f"<div style='margin:8px 0 14px;font-size:12px;color:{_T['muted']}'><b style='color:{_T['text']}'>"
                                    f"{label}</b> : pas assez de cas ({n}).</div>")
                        v = max(0.0, min(1.5, frac))
                        c = (_T["win"] if v >= 0.7 else _T["orange"]) if good_high else _T["accent"]
                        return (f"<div style='margin:8px 0 14px'><div style='display:flex;justify-content:space-between;font-size:12px'>"
                                f"<b style='color:{_T['text']}'>{label}</b><span style='color:{c};font-weight:800'>{frac * 100:.0f} %</span></div>"
                                f"<div style='height:9px;border-radius:5px;background:{_T['bg2']};margin:5px 0 4px;overflow:hidden'>"
                                f"<div style='width:{min(100, v / 1.0 * 100):.0f}%;height:100%;background:{c}'></div></div>"
                                f"<div style='font-size:11px;color:{_T['muted']}'>{note} · {n} trades</div></div>")
                    st.markdown(
                        f"<div style='background:{_T['card']};border:1px solid {_T['border']};border-radius:12px;padding:8px 14px'>"
                        + _bar("Gains pris à la main", _R.get("manual_win_tp_frac"), _R.get("manual_win_n", 0), True,
                               "part du chemin vers le TP au moment de sortir (100 % = TP)")
                        + _bar("Pertes coupées à la main", _R.get("manual_loss_sl_frac"), _R.get("manual_loss_n", 0), False,
                               "part de la distance du stop au moment de couper (100 % = stop)")
                        + "</div>", unsafe_allow_html=True)
                # ── MAE / MFE ──────────────────────────────────────────────────
                _exR = _R.get("exR")
                if _exR is not None and len(_exR) >= 5:
                    m1, m2 = st.columns(2, gap="medium")
                    with m1:
                        _card("MAE / MFE par trade", "en R · ligne verticale = stop initial")
                        fig_mm = go.Figure()
                        for lab, msk, col in (("Gagnants", _exR["pnl"] > 0, _T["win"]), ("Perdants", _exR["pnl"] <= 0, _T["loss"])):
                            sub = _exR[msk]
                            fig_mm.add_trace(go.Scatter(x=sub["_maeR"].clip(upper=3), y=sub["_mfeR"].clip(upper=6), mode="markers", name=lab,
                                marker=dict(color=col, size=7, opacity=0.7, line=dict(color=_T["card"], width=0.5)),
                                hovertemplate=lab + "<br>MAE %{x:.2f} R · MFE %{y:.2f} R<extra></extra>"))
                        fig_mm.add_vline(x=1, line_dash="dot", line_color=_T["loss"], line_width=1,
                                         annotation_text="stop", annotation_font=dict(color=_T["muted"], size=10))
                        if _R.get("tp_plan_med_R"):
                            fig_mm.add_hline(y=_R["tp_plan_med_R"], line_dash="dot", line_color=_T["win"], line_width=1,
                                             annotation_text="TP médian", annotation_font=dict(color=_T["muted"], size=10))
                        fig_mm.update_layout(**_base_layout(height=300, showlegend=True))
                        _style_axes(fig_mm, free_y=True); fig_mm.update_xaxes(title_text="MAE (R)"); fig_mm.update_yaxes(title_text="MFE (R)")
                        st.plotly_chart(fig_mm, use_container_width=True, config=_chart_cfg)
                    with m2:
                        _card("Recul des gagnants avant de partir (MAE)", "en R")
                        _w = _exR[_exR["pnl"] > 0]["_maeR"].clip(upper=1.5)
                        fig_h = go.Figure(go.Histogram(x=_w, nbinsx=20, marker=dict(color=_T["accent"], opacity=0.85),
                                                       hovertemplate="MAE %{x:.2f} R : %{y} gagnants<extra></extra>"))
                        if _R.get("win_maeR_q"):
                            fig_h.add_vline(x=_R["win_maeR_q"][0.9], line_dash="dash", line_color=_T["orange"], line_width=1.5,
                                            annotation_text="90 % des gagnants", annotation_position="top left", annotation_font=dict(color=_T["muted"], size=10))
                        fig_h.add_vline(x=1, line_dash="dot", line_color=_T["loss"], line_width=1,
                                        annotation_text="stop", annotation_position="bottom right", annotation_font=dict(color=_T["muted"], size=10))
                        fig_h.update_layout(**_base_layout(height=230))
                        _style_axes(fig_h); fig_h.update_xaxes(title_text="MAE (R)")
                        st.plotly_chart(fig_h, use_container_width=True, config=_chart_cfg)
                        _txt = []
                        if _R.get("e_ratio") is not None: _txt.append(f"Ratio MFE/MAE : <b>{_R['e_ratio']:.2f}</b>")
                        if _R.get("exit_eff") is not None: _txt.append(f"Mouvement capturé par les gagnants : <b>{_R['exit_eff']:.0f} %</b>")
                        if _R.get("stopped_mfe_1R") is not None: _txt.append(f"Stops passés d'abord par +1 R : <b>{_R['stopped_mfe_1R']:.0f} %</b>")
                        if _R.get("near_miss") is not None: _txt.append(f"Gagnants passés à moins de 0,2 R du stop : <b>{_R['near_miss']:.0f} %</b>")
                        st.markdown(f"<div style='font-size:12px;color:{_T['text']};line-height:1.7'>" + " · ".join(_txt) + "</div>",
                                    unsafe_allow_html=True)
                else:
                    st.info(f"MAE / MFE disponibles pour {_R.get('n_excursion', 0)} trade(s) sur cette sélection. Pour les "
                            "obtenir, exporte tes positions avec le script MT5 **ExportTJ_MAE_MFE** puis importe le fichier "
                            "dans la page **Import MT5** (rubrique « Enrichir avec MAE / MFE »). Elles indiquent si tes stops "
                            "sont trop larges ou trop courts et si tes TP sont réalistes.")
                # ── Volume ────────────────────────────────────────────────────
                v1, v2 = st.columns(2, gap="medium")
                with v1:
                    _card("Résultat selon la taille de position", "taille relative à ta taille habituelle sur l'actif")
                    _bs = _R.get("by_size")
                    if _bs is not None and len(_bs.dropna(subset=["mean"])):
                        _bs = _bs.dropna(subset=["mean"])
                        fig_bs = category_figure(_bs["_bucket"].astype(str).tolist(), _bs["mean"].round(2).tolist(),
                            [_T["win"] if v >= 0 else _T["loss"] for v in _bs["mean"]], _T, _cs, kind="bar", orientation="v",
                            texts=[f"{fmt(m)} · {int(c)} tr. · {w:.0f} %" for m, c, w in zip(_bs["mean"], _bs["count"], _bs["wr"])],
                            hovertemplate="<b>%{x}</b><br>Résultat moyen : %{y:+,.2f}$<extra></extra>")
                        fig_bs.add_hline(y=0, line_color=_grid, line_width=1)
                        fig_bs.update_layout(**_base_layout(height=250)); _style_axes(fig_bs, yprefix="$")
                        fig_bs.update_traces(cliponaxis=False)
                        st.plotly_chart(fig_bs, use_container_width=True, config=_chart_cfg)
                    else:
                        st.info("Volume non disponible : il est lu dans les imports MT5 (ou le fichier MAE/MFE).")
                with v2:
                    _card("Régularité du risque", "montant des pertes")
                    _ls = _R["d"].loc[_R["d"]["pnl"] < 0, "pnl"].abs()
                    if len(_ls) >= 5:
                        fig_ls = go.Figure(go.Histogram(x=_ls, nbinsx=25, marker=dict(color=_T["loss"], opacity=0.8),
                                                        hovertemplate="Perte %{x:,.2f}$ : %{y} trades<extra></extra>"))
                        fig_ls.add_vline(x=float(_ls.mean()), line_dash="dash", line_color=_T["text"], line_width=1,
                                         annotation_text="moyenne", annotation_font=dict(color=_T["muted"], size=10))
                        fig_ls.update_layout(**_base_layout(height=230)); _style_axes(fig_ls, xprefix="$")
                        st.plotly_chart(fig_ls, use_container_width=True, config=_chart_cfg)
                        _cvt = (f"Coefficient de variation {_R['loss_cv']:.2f} · " if _R.get("loss_cv") is not None else "")
                        st.markdown(f"<div style='font-size:12px;color:{_T['muted']}'>{_cvt}perte moyenne {money(_R['loss_avg'])}"
                                    f" · plus grosse perte {money(_R['loss_max'])}</div>", unsafe_allow_html=True)
                st.markdown(f"<hr style='border-color:{_T['border']};margin:14px 0 6px'>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:12px;color:{_T['muted']};margin-bottom:4px'>Graphiques complémentaires</div>",
                            unsafe_allow_html=True)
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
                    # Repères sobres 1R / 2R (lignes fines, sans bandes de couleur)
                    fig_rr.add_hline(y=1, line_dash="dot", line_color=_text, line_width=1,
                        annotation_text="1R", annotation_font=dict(color=_text, size=10))
                    fig_rr.add_hline(y=2, line_dash="dot", line_color=_text, line_width=1,
                        annotation_text="2R", annotation_font=dict(color=_text, size=10))
                    fig_rr.update_layout(**_base_layout(height=260, showlegend=False))
                    _style_axes(fig_rr)
                    fig_rr.update_yaxes(ticksuffix="R")
                    st.plotly_chart(fig_rr, use_container_width=True, config=_chart_cfg)
                    # Légende couleurs
                    st.markdown(
                        '<div style="display:flex;gap:20px;font-size:11px;color:var(--tj-muted);margin-top:-8px">'
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
                    st.plotly_chart(fig_vol, use_container_width=True, config=_chart_cfg)
                    st.caption("Volume non disponible dans les données — affichage P&L par actif. "
                               "Le volume est extrait des notes lors de l'import MT5.")
                else:
                    # Scatter P&L vs Volume
                    colors_v = [_win if p>0 else _loss for p in df_vol["pnl"]]
                    sizes_v  = [max(8, min(30, abs(p)/max(1,abs(df_vol["pnl"]).max())*30))
                                for p in df_vol["pnl"]]
                    fig_vol = go.Figure(go.Scatter(
                        x=df_vol["_vol"].tolist(), y=df_vol["pnl"].tolist(),
                        mode="markers", name="Trades",
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
                    fig_vol.update_layout(**_base_layout(height=260, showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.15)))
                    _style_axes(fig_vol, yprefix="$")
                    fig_vol.update_xaxes(title_text="Volume (lots)")
                    st.plotly_chart(fig_vol, use_container_width=True, config=_chart_cfg)

        with tab_assets:
            r4c1, r4c2 = st.columns(2)

            with r4c1:
                _card("Classement des Actifs", "Rentabilité décroissante")
                by_sym = df.groupby("symbol").agg(
                    pnl=("pnl","sum"), trades=("pnl","count"),
                    wins=("pnl", lambda x: (x>0).sum()),
                ).reset_index()
                by_sym["win_rate"] = (by_sym["wins"]/by_sym["trades"]*100).round(1)
                by_sym = by_sym.sort_values("pnl", ascending=True)
                fig_sym = category_figure(
                    by_sym["symbol"].tolist(), by_sym["pnl"].tolist(),
                    [_win if v>=0 else _loss for v in by_sym["pnl"]], _theme, _cs,
                    kind=_cs["ranking"], orientation="h",
                    texts=[f"{fmt(v)}  ·  {wr}% win" for v,wr in zip(by_sym["pnl"],by_sym["win_rate"])],
                    hovertemplate="<b>%{y}</b><br>P&L : %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                    customdata=list(zip(by_sym["trades"].tolist(), by_sym["win_rate"].tolist())))
                fig_sym.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
                fig_sym.update_layout(**_base_layout(height=max(280,len(by_sym)*48)))
                _style_axes(fig_sym, xprefix="$")
                st.plotly_chart(fig_sym, use_container_width=True, config=_chart_cfg)

            with r4c2:
                _card("P&L par Stratégie")
                by_strat = df.groupby("strategy").agg(
                    pnl=("pnl","sum"), trades=("pnl","count"),
                    wins=("pnl", lambda x: (x>0).sum()),
                ).reset_index()
                by_strat["win_rate"] = (by_strat["wins"]/by_strat["trades"]*100).round(1)
                by_strat = by_strat.sort_values("pnl", ascending=True)
                _strat_pal = [_theme["accent"], _theme["alt"], _theme["orange"], _theme["win"],
                              _theme["loss"]] + CHART_COLORS
                fig_st = category_figure(
                    by_strat["strategy"].tolist(), by_strat["pnl"].tolist(),
                    [_strat_pal[i % len(_strat_pal)] for i in range(len(by_strat))], _theme, _cs,
                    kind=_cs["ranking"], orientation="h",
                    texts=[f"{fmt(v)}  ·  {wr}% win" for v,wr in zip(by_strat["pnl"],by_strat["win_rate"])],
                    hovertemplate="<b>%{y}</b>: %{x:+,.2f}$<br>%{customdata[0]} trades · %{customdata[1]}% win<extra></extra>",
                    customdata=list(zip(by_strat["trades"].tolist(), by_strat["win_rate"].tolist())))
                fig_st.add_vline(x=0, line_dash="dot", line_color=_grid, line_width=1)
                fig_st.update_layout(**_base_layout(height=max(280,len(by_strat)*48)))
                _style_axes(fig_st, xprefix="$")
                st.plotly_chart(fig_st, use_container_width=True, config=_chart_cfg)

        with tab_psy:
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
                        colorscale=diverging_scale(_theme),
                        zmid=0,
                        text=[[f"${v:+,.0f}" for v in row] for row in pivot.values],
                        texttemplate="%{text}",
                        textfont=dict(size=12, color=_theme["text"], family=_cs["font"]),
                        xgap=3 if _cs["corner"] else 1, ygap=3 if _cs["corner"] else 1,
                        hovertemplate="<b>%{y} · %{x}</b><br>P&L : %{z:+,.2f}$<extra></extra>",
                        showscale=True,
                        colorbar=dict(tickprefix="$", tickfont=dict(color=_text, size=11),
                                      bgcolor=_bg, bordercolor=_grid, thickness=12),
                    ))
                    fig_hm.update_layout(**_base_layout(
                        height=max(280, len(pivot)*60),
                        margin=dict(l=100, r=60, t=20, b=60)))
                    fig_hm.update_xaxes(side="bottom", tickangle=-30,
                                        gridcolor=_grid, linecolor=_grid)
                    fig_hm.update_yaxes(gridcolor=_grid, linecolor=_grid)
                    st.plotly_chart(fig_hm, use_container_width=True, config=_chart_cfg)
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
                        opacity=_cs["bar_opacity"], line=dict(color=_bg, width=0.5)
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
                st.plotly_chart(fig_mood, use_container_width=True, config=_chart_cfg)

        with tab_cal:

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
                        marker_color=_bar_colors(vals_wd), marker_opacity=_cs["bar_opacity"],
                        customdata=n_wd.tolist(),
                        hovertemplate="<b>%{x}</b><br>" + cal_metric +
                                     " : %{y:,.2f}" + suffix +
                                     "<br>%{customdata} trades<extra></extra>",
                    ))
                    if not _neutral:
                        fig_wd.add_hline(y=0, line_color=_grid, line_width=1)
                    fig_wd.update_layout(**_base_layout(height=260))
                    _style_axes(fig_wd, yprefix=yprefix)
                    st.plotly_chart(fig_wd, use_container_width=True, config=_chart_cfg)

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
                            marker_color=_bar_colors(vals_hr), marker_opacity=_cs["bar_opacity"],
                            customdata=n_hr.tolist(),
                            hovertemplate="<b>%{x}</b><br>" + cal_metric +
                                         " : %{y:,.2f}" + suffix +
                                         "<br>%{customdata} trades<extra></extra>",
                        ))
                        if not _neutral:
                            fig_hrd.add_hline(y=0, line_color=_grid, line_width=1)
                        fig_hrd.update_layout(**_base_layout(height=260))
                        _style_axes(fig_hrd, yprefix=yprefix)
                        st.plotly_chart(fig_hrd, use_container_width=True, config=_chart_cfg)
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
                            _cscale = sequential_scale(_theme, _cs)
                            _zmid, _zmin, _zmax = None, None, None
                        elif cal_metric == "Win rate %":
                            _cscale = diverging_scale(_theme)
                            _zmid, _zmin, _zmax = 50, 0, 100
                        else:
                            _m = max(abs(np.nanmin(_vals)), abs(np.nanmax(_vals)), 1)
                            _cscale = diverging_scale(_theme)
                            _zmid, _zmin, _zmax = (1 if cal_metric=="R:R moyen" else 0), -_m if cal_metric!="R:R moyen" else 0, _m
                        _hm_kwargs = dict(
                            z=_vals,
                            x=[f"{int(h):02d}h" for h in pivot_wh.columns],
                            y=pivot_wh.index.tolist(),
                            colorscale=_cscale,
                            xgap=3 if _cs["corner"] else 1, ygap=3 if _cs["corner"] else 1,
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
                        st.plotly_chart(fig_hm, use_container_width=True, config=_chart_cfg)
                    else:
                        st.info("Pas assez de données horaires pour la heatmap.")
            st.markdown(" ")

        with tab_last:
            recent = df.sort_values("date", ascending=False).head(8)
            rows_html = ""
            for _, t in recent.iterrows():
                c  = "#00d4aa" if t["pnl"]>=0 else "#ff4d6d"
                dc = "b-win" if t["direction"]=="LONG" else "b-loss"
                _tm = t.get("trade_mode","Réel Indépendant")

                rows_html += f"""<tr>
                    <td style="color:var(--tj-muted);font-family:monospace">{t["date"]}</td>
                    <td>{badge(t["symbol"],"b-sym")}</td>
                    <td>{badge(t["direction"],dc)}</td>
                    <td>{mode_badge(t.get("trade_mode","Réel Indépendant"))}</td>
                    <td style="font-size:15px;text-align:center">{mood_html(t["mood"])}</td>
                    <td>{badge(t["strategy"],"b-str")}</td>
                    <td style="font-family:monospace;font-weight:800;color:{c}">{fmt(t["pnl"])}</td>
                    <td style="color:var(--tj-muted);font-size:12px">{str(t.get("notes",""))[:40]}</td>
                </tr>"""
            st.markdown(f"""<table class="tj-table"><thead><tr>
                <th>Date</th><th>Actif</th><th>Dir.</th><th>Mode</th>
                <th>Mood</th><th>Stratégie</th><th>P&L $</th><th>Notes</th>
            </tr></thead><tbody>{rows_html}</tbody></table>""", unsafe_allow_html=True)





elif st.session_state.page == "journal":
    _tj = get_theme()
    df_all = get_df("Tous")
    _n_all = len(df_all)

    _jh1, _jh2 = st.columns([4, 1.2], vertical_alignment="center")
    with _jh1:
        st.markdown(
            f"<div style='display:flex;align-items:baseline;gap:12px'>"
            f"<span style='font-size:22px;font-weight:800;color:{_tj['text']}'>Journal des Trades</span>"
            f"<span style='font-size:12px;color:{_tj['muted']}'>{_n_all:,} trades enregistrés · comptes autorisés</span></div>"
            .replace(",", " "), unsafe_allow_html=True)
    with _jh2:
        if st.button("Exporter", icon=":material/download:", key="jr_export_open", use_container_width=True,
                     disabled=df_all.empty):
            export_dialog()

    if df_all.empty:
        st.info("Aucun trade. Ajoutez-en un avec **Nouveau Trade** ou importez depuis MT5.")
        st.stop()

    # ══ REQUÊTE : rien n'est chargé tant qu'aucune recherche n'est lancée ═════════
    _q_live = trade_filters("jq", df_all)
    _b = st.columns([1.3, 1, 1, 1, 2.2])
    with _b[0]:
        if st.button("Rechercher", type="primary", icon=":material/search:", key="jq_go", use_container_width=True):
            st.session_state.jq = dict(_q_live); st.session_state.jq_page = 0
    _today = date.today()
    _quick = [("Aujourd'hui", {"from": _today, "to": _today}),
              ("7 derniers jours", {"from": _today - timedelta(days=6), "to": _today}),
              ("50 derniers", {"last": 50})]
    for _i, (_lbl, _qq) in enumerate(_quick):
        with _b[_i + 1]:
            if st.button(_lbl, key=f"jq_quick_{_i}", use_container_width=True):
                st.session_state.jq = _qq; st.session_state.jq_page = 0
    with _b[4]:
        if st.session_state.get("jq") is not None:
            if st.button("Effacer la recherche", icon=":material/close:", key="jq_clear", use_container_width=True):
                st.session_state.jq = None; st.rerun()

    _q = st.session_state.get("jq")
    if _q is None:
        st.markdown(
            f"<div style='margin-top:14px;padding:18px 20px;border:1px dashed {_tj['border']};"
            f"border-radius:6px 22px 22px 22px;color:{_tj['muted']};font-size:13px'>"
            f"Choisis des filtres puis <b style='color:{_tj['accent']}'>Rechercher</b>, ou utilise un raccourci. "
            f"Les trades ne sont affichés qu'à la demande pour que la page reste rapide, même avec des milliers de trades.</div>",
            unsafe_allow_html=True)
        st.stop()

    df = apply_trade_filters(df_all, _q).sort_values(["date", "time"] if "time" in df_all.columns else "date",
                                                     ascending=False)
    if _q.get("last"):
        df = df.head(int(_q["last"]))

    if df.empty:
        st.info("Aucun trade ne correspond à cette recherche.")
        st.stop()

    _tot = df["pnl"].sum(); _wr = (df["pnl"] > 0).mean() * 100
    _cf = _tj["win"] if _tot >= 0 else _tj["loss"]
    st.markdown(
        f"<div style='display:flex;gap:22px;align-items:center;flex-wrap:wrap;padding:8px 16px;margin:10px 0;"
        f"background:{_tj['card']};border:1px solid {_tj['border']};border-radius:999px;font-size:13px;color:{_tj['muted']}'>"
        f"<span><b style='color:{_tj['text']}'>{len(df)}</b> trade(s) trouvés</span>"
        f"<span>P&L : <b style='color:{_cf}'>{fmt(_tot)}</b></span>"
        f"<span>Win rate : <b style='color:{_tj['text']}'>{_wr:.0f}%</b></span>"
        f"<span style='margin-left:auto'>{describe_query(_q)}</span></div>", unsafe_allow_html=True)

    # ── Pagination ────────────────────────────────────────────────────────────
    _psz = int(st.session_state.get("jq_psz", 50))
    _npg = max(1, -(-len(df) // _psz))
    _pg = min(int(st.session_state.get("jq_page", 0)), _npg - 1)
    df_page = df.iloc[_pg * _psz:(_pg + 1) * _psz]

    rows_html = ""
    for _, t in df_page.iterrows():
        c = _tj["win"] if t["pnl"] >= 0 else _tj["loss"]
        dc = "b-win" if t["direction"] == "LONG" else "b-loss"
        rr_v = t.get("rr")
        rr_ok = rr_v is not None and not (isinstance(rr_v, float) and pd.isna(rr_v))
        rr_c = _tj["win"] if (rr_v or 0) >= 2 else _tj["orange"] if (rr_v or 0) >= 1 else _tj["loss"]
        rows_html += f"""<tr>
            <td style="color:var(--tj-muted);font-family:monospace;white-space:nowrap">{t["date"]} {str(t.get("time") or "")[:5]}</td>
            <td>{badge(t["symbol"],"b-sym")}</td>
            <td>{badge(t["direction"],dc)}</td>
            <td>{mode_badge(t.get("trade_mode","Réel Indépendant"))}</td>
            <td style="font-family:monospace">{t.get("entry","—")}</td>
            <td style="font-family:monospace">{t.get("exit","—")}</td>
            <td style="font-family:monospace;font-weight:800;color:{c};white-space:nowrap">{fmt(t["pnl"])}</td>
            <td style="font-family:monospace;color:{rr_c}">{rr_v if rr_ok and rr_v else "—"}</td>
            <td>{badge(t.get("strategy",""),"b-str")}</td>
            <td style="text-align:center">{mood_html(t.get("mood",""))}</td>
            <td style="color:var(--tj-muted);font-size:12px;max-width:160px">{_html.escape(str(t.get("notes","") or "")[:45])}</td>
        </tr>"""
    st.markdown(
        f"""<div style="overflow-x:auto"><table class="tj-table">
        <thead><tr>
            <th>Date</th><th>Actif</th><th>Dir.</th><th>Mode</th>
            <th>Entrée</th><th>Sortie</th><th>P&L $</th><th>R:R</th>
            <th>Stratégie</th><th>Mood</th><th>Notes</th>
        </tr></thead><tbody>{rows_html}</tbody></table></div>""",
        unsafe_allow_html=True)

    _p = st.columns([1, 1, 2.5, 1.3], vertical_alignment="center")
    with _p[0]:
        if st.button("Précédent", icon=":material/chevron_left:", key="jq_prev", disabled=_pg == 0, use_container_width=True):
            st.session_state.jq_page = _pg - 1; st.rerun()
    with _p[1]:
        if st.button("Suivant", icon=":material/chevron_right:", key="jq_next", disabled=_pg >= _npg - 1, use_container_width=True):
            st.session_state.jq_page = _pg + 1; st.rerun()
    with _p[2]:
        st.caption(f"Page {_pg + 1} / {_npg} · trades {_pg * _psz + 1} à {min(len(df), (_pg + 1) * _psz)} sur {len(df)}")
    with _p[3]:
        _ns = st.selectbox("Par page", [25, 50, 100], index=[25, 50, 100].index(_psz), key="jq_psz_sel",
                           label_visibility="collapsed", format_func=lambda n: f"{n} par page")
        if _ns != _psz:
            st.session_state.jq_psz = _ns; st.session_state.jq_page = 0; st.rerun()

    # ══ MODIFIER / SUPPRIMER (admin) : uniquement sur les résultats de la recherche ═══
    if is_admin():
        with st.expander(f"Modifier ou supprimer · {len(df)} trade(s) de la recherche"):
            tab1, tab2 = st.tabs(["Un trade", "Plusieurs trades (page affichée)"])
            with tab1:
                _cap = df.head(500)
                labels_one = [f"{r['date']}  ·  {r['symbol']}  ·  {r.get('trade_mode','Réel Indépendant')}  ·  "
                              f"{r['direction']}  ·  {fmt(r['pnl'])}" for _, r in _cap.iterrows()]
                ids_one = _cap["id"].tolist()
                if len(df) > 500:
                    st.caption("500 premiers résultats proposés : affine la recherche pour atteindre les autres.")
                sel_lbl = st.selectbox("Sélectionner un trade", labels_one, label_visibility="collapsed", key="jq_one")
                sel_id = ids_one[labels_one.index(sel_lbl)]
                sel_trade = next((t for t in st.session_state.trades if t["id"] == sel_id), None)
                ce, cd, _ = st.columns([1, 1, 5])
                with ce:
                    if st.button("Modifier", icon=":material/edit:", use_container_width=True, key="btn_edit_one"):
                        st.session_state.edit_id = sel_id; st.session_state.page = "add"; st.rerun()
                with cd:
                    if st.button("Supprimer", icon=":material/delete:", use_container_width=True, key="btn_del_one"):
                        st.session_state["confirm_del"] = sel_id
                if sel_trade and st.session_state.get("confirm_del") == sel_id:
                    st.warning(f"Confirmer la suppression de **{sel_trade.get('date','')} · "
                               f"{sel_trade.get('symbol','')} · {fmt(sel_trade.get('pnl',0))}** ?")
                    cc1, cc2, _ = st.columns([1, 1, 5])
                    with cc1:
                        if st.button("Oui, supprimer", icon=":material/check:", use_container_width=True, key="btn_confirm_del"):
                            st.session_state.trades = [t for t in st.session_state.trades if t["id"] != sel_id]
                            ok = cloud_save(st.session_state.trades)
                            st.session_state.pop("confirm_del", None)
                            st.success("Supprimé." if ok else "Erreur sauvegarde."); st.rerun()
                    with cc2:
                        if st.button("Annuler", icon=":material/close:", use_container_width=True, key="btn_cancel_del"):
                            st.session_state.pop("confirm_del", None); st.rerun()

                # Captures d'écran du trade sélectionné
                st.markdown("##### Captures d'écran du setup")
                _sid = str(sel_id)
                _shots = st.session_state.trade_screenshots
                _cur = _shots.get(_sid, [])
                up = st.file_uploader("Ajouter des captures (PNG/JPG)", type=["png", "jpg", "jpeg"],
                                      accept_multiple_files=True, key=f"up_{_sid}", label_visibility="collapsed")
                if up and st.button("Enregistrer les captures", icon=":material/save:", key=f"save_shot_{_sid}", type="primary"):
                    added = 0
                    for f in up:
                        try:
                            _cur.append({"name": f.name, "data": compress_image(f.getvalue()),
                                         "ts": datetime.now().isoformat(timespec="seconds")})
                            added += 1
                        except Exception as e:
                            st.warning(f"Échec {f.name} : {e}")
                    _shots[_sid] = _cur
                    st.session_state.trade_screenshots = _shots
                    ok = screenshots_save(_shots)
                    st.success(f"{added} capture(s) enregistrée(s)." if ok else f"{added} ajoutée(s) en session (sync à vérifier).")
                    st.rerun()
                if _cur:
                    gcols = st.columns(3)
                    for _i, sh in enumerate(list(_cur)):
                        with gcols[_i % 3]:
                            st.image(sh["data"], use_container_width=True, caption=sh.get("name", ""))
                            if st.button("Supprimer", icon=":material/delete:", key=f"delshot_{_sid}_{_i}", use_container_width=True):
                                _cur.pop(_i)
                                if _cur: _shots[_sid] = _cur
                                else: _shots.pop(_sid, None)
                                st.session_state.trade_screenshots = _shots
                                screenshots_save(_shots); st.rerun()
                else:
                    st.caption("Aucune capture pour ce trade.")

            with tab2:
                _ed = df_page[["id", "date", "symbol", "trade_mode", "direction", "pnl"]].copy()
                _ed.insert(0, "Suppr.", False)
                _out = st.data_editor(
                    _ed, key=f"jq_editor_{_pg}_{_psz}", hide_index=True, use_container_width=True,
                    disabled=["id", "date", "symbol", "trade_mode", "direction", "pnl"],
                    column_config={"id": None, "Suppr.": st.column_config.CheckboxColumn("Suppr.", width="small"),
                                   "date": "Date", "symbol": "Actif", "trade_mode": "Compte", "direction": "Dir.",
                                   "pnl": st.column_config.NumberColumn("P&L $", format="%.2f")})
                _sel = set(_out.loc[_out["Suppr."], "id"].tolist())
                if _sel:
                    _psel = df[df["id"].isin(_sel)]["pnl"].sum()
                    st.warning(f"{len(_sel)} trade(s) cochés · P&L {fmt(_psel)}. Suppression définitive.")
                    if st.button(f"Supprimer {len(_sel)} trade(s)", icon=":material/delete_sweep:", key="btn_del_multi"):
                        st.session_state.trades = [t for t in st.session_state.trades if t["id"] not in _sel]
                        ok = cloud_save(st.session_state.trades)
                        st.success(f"{len(_sel)} trade(s) supprimé(s)." if ok else "Erreur sauvegarde."); st.rerun()
                else:
                    st.caption("Coche les trades de la page affichée à supprimer.")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : ADD / EDIT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "add":
    if not is_admin():
        st.error("Seul l'administrateur peut ajouter ou modifier des trades.")
        st.stop()
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

        rtc1, _rtc2 = st.columns([1, 3])
        with rtc1:
            d_time = st.text_input("Heure (HH:MM)", value=str(ev("time", "00:00") or "00:00"))

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

        st.markdown("""<div style="background:var(--tj-bg2);border:2px solid #00d4aa44;border-radius:12px;
            padding:14px 20px;margin:12px 0 4px">
            <div style="font-size:11px;color:#00d4aa;letter-spacing:1.5px;text-transform:uppercase;font-weight:700;margin-bottom:4px">
                P&L Réel — tel qu'affiché par votre broker</div>
            <div style="font-size:12px;color:var(--tj-muted)">Saisissez le résultat exact · spread, commission et swap inclus</div>
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
    if not is_admin():
        st.error("Seul l'administrateur peut importer des trades.")
        st.stop()
    st.markdown("# Importer depuis MetaTrader 5")
    if st.button("Retour", icon=":material/arrow_back:"):
        st.session_state.page = "journal"; st.rerun()
    st.divider()

    # ── Enrichissement MAE / MFE (script MT5 ExportTJ_MAE_MFE) ────────────────
    with st.expander("Enrichir avec MAE / MFE et motifs de clôture (script MT5)"):
        st.markdown(
            "1. Dans MetaTrader 5 : **Fichier → Ouvrir le dossier des données → MQL5 → Scripts**, "
            "copie `ExportTJ_MAE_MFE.mq5`, puis ouvre-le dans MetaEditor et compile-le (F7).\n"
            "2. Glisse le script **ExportTJ_MAE_MFE** sur un graphique, choisis la profondeur d'historique, valide.\n"
            "3. Le fichier `TJ_MAE_MFE.csv` est créé dans le dossier **Common\\Files** de MetaTrader "
            "(le chemin exact s'affiche à la fin). Importe-le ci-dessous.")
        _sp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ExportTJ_MAE_MFE.mq5")
        if os.path.exists(_sp):
            st.download_button("Télécharger le script ExportTJ_MAE_MFE.mq5", open(_sp, "rb").read(),
                               file_name="ExportTJ_MAE_MFE.mq5", mime="text/plain", key="dl_mq5")
        _mf = st.file_uploader("Fichier TJ_MAE_MFE.csv", type=["csv", "txt"], key="mae_csv")
        if _mf is not None:
            try:
                _mx = pd.read_csv(_mf, sep=";", dtype=str, encoding_errors="ignore")
                _mx.columns = [c.strip().lower() for c in _mx.columns]
                _num = lambda v: (float(str(v).replace(",", ".")) if str(v).strip() not in ("", "nan", "None") else None)
                def _symk(x):
                    x = str(x).upper().replace("/", "").replace(".", "").replace("_", "")
                    for suf in ("PRO", "ECN", "RAW", "M"):
                        if x.endswith(suf) and len(x) > len(suf) + 2:
                            x = x[: -len(suf)]
                    return x
                _by_id = {str(t.get("mt5_id", "")).strip(): t for t in st.session_state.trades
                          if str(t.get("mt5_id", "")).strip()}
                _by_key = {}
                for t in st.session_state.trades:
                    try:
                        _k = (_symk(t.get("symbol")), str(pd.to_datetime(t.get("datetime") or t.get("date")))[:16],
                              "LONG" if str(t.get("direction", "")).upper().startswith("L") else "SHORT")
                        _by_key[_k] = t
                    except Exception:
                        pass
                _upd = []
                for _, r in _mx.iterrows():
                    t = _by_id.get(str(r.get("position_id", "")).strip())
                    if t is None:
                        _k = (_symk(r.get("symbol")), str(pd.to_datetime(r.get("open_time"), errors="coerce"))[:16],
                              "LONG" if str(r.get("type", "")).upper() == "BUY" else "SHORT")
                        t = _by_key.get(_k)
                    if t is not None:
                        _upd.append((t, r))
                st.info(f"{len(_mx)} positions dans le fichier · {len(_upd)} correspondent à des trades du journal "
                        f"· {sum(1 for _, r in _upd if _num(r.get('mae_price')) is not None)} avec MAE/MFE.")
                if _upd and st.button(f"Enrichir {len(_upd)} trades (MAE/MFE, sortie, SL/TP, motif de clôture)",
                                      type="primary", key="mae_apply"):
                    for t, r in _upd:
                        for src, dst in (("close_price", "exit"), ("sl_open", "sl"), ("tp_open", "tp"),
                                         ("sl_close", "sl_close"), ("tp_close", "tp_close"), ("volume", "volume"),
                                         ("mae_price", "mae"), ("mfe_price", "mfe"),
                                         ("mae_money", "mae_money"), ("mfe_money", "mfe_money")):
                            v = _num(r.get(src))
                            if v is not None and not (dst in ("sl", "tp") and v == 0):
                                t[dst] = v
                        if str(r.get("exit_reason", "")).strip():
                            t["exit_reason"] = str(r["exit_reason"]).strip().upper()
                        if str(r.get("close_time", "")).strip():
                            t["close_datetime"] = str(r["close_time"]).strip().replace(" ", "T")
                        if not t.get("mt5_id") and str(r.get("position_id", "")).strip():
                            t["mt5_id"] = str(r["position_id"]).strip()
                    (st.success if db_save(st.session_state.trades) else st.warning)(
                        f"{len(_upd)} trade(s) enrichi(s). L'analyse MAE/MFE est disponible dans le dashboard, "
                        "onglet Risque & Volume.")
            except Exception as _e:
                st.error(f"Fichier illisible : {type(_e).__name__}: {_e}")
    st.divider()

    # ── Mode du compte ────────────────────────────────────────────────────────
    ic1, ic2 = st.columns([2, 3])
    with ic1:
        imp_mode = st.radio("Type de compte", TRADE_MODES, horizontal=True, key="imp_mode",
                            index=TRADE_MODES.index(DEFAULT_ACCOUNT) if DEFAULT_ACCOUNT in TRADE_MODES else 0)
    with ic2:
        _ic = account_color(imp_mode)
        st.markdown(
            f'<div style="margin-top:8px;background:linear-gradient(90deg,{_ic}22,{_ic}08);'
            f'border:1px solid {_ic}55;border-left:3px solid {_ic};border-radius:10px;'
            f'padding:8px 16px;font-size:12px;color:{_ic};font-weight:700">'
            f'Trades étiquetés : {imp_mode}</div>', unsafe_allow_html=True)

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
                # Trouver la ligne d'en-tête des POSITIONS (contient Position + Profit)
                header_row = 0
                for i, row in xls_scan.iterrows():
                    vals = [str(v).strip().lower() for v in row.values]
                    if "position" in vals and "profit" in vals:
                        header_row = i; break
                else:
                    for i, row in xls_scan.iterrows():
                        vals = [str(v).strip().lower() for v in row.values]
                        if any(k in vals for k in ["symbol","time","profit","type","position"]):
                            header_row = i; break
                # Détecter la fin de la section : 1ère ligne "Orders"/"Deals"/"Results"
                # ou 1ère ligne vide APRÈS l'en-tête
                stop_row = len(xls_scan)
                for i in range(header_row + 1, len(xls_scan)):
                    first = str(xls_scan.iloc[i, 0]).strip().lower()
                    if first in ("orders", "deals", "results", "nan", ""):
                        stop_row = i; break
                n_read = stop_row - header_row - 1
                df_raw = pd.read_excel(io.BytesIO(file_bytes), skiprows=header_row,
                                       nrows=n_read, dtype=str)
            else:
                raw_text = file_bytes.decode("utf-8", errors="replace")
                counts   = {"	": raw_text.count("	"), ";": raw_text.count(";"), ",": raw_text.count(",")}
                sep      = max(counts, key=counts.get)
                tmp = pd.read_csv(io.StringIO(raw_text), sep=sep, header=None, dtype=str, on_bad_lines="skip")
                header_row = 0
                for i, row in tmp.iterrows():
                    vals = [str(v).strip().lower() for v in row.values]
                    if "position" in vals and "profit" in vals:
                        header_row = i; break
                else:
                    for i, row in tmp.iterrows():
                        vals = [str(v).strip().lower() for v in row.values]
                        if any(k in vals for k in ["symbol","time","profit","type","position"]):
                            header_row = i; break
                # Fin de section Positions
                stop_row = len(tmp)
                for i in range(header_row + 1, len(tmp)):
                    first = str(tmp.iloc[i, 0]).strip().lower()
                    if first in ("orders", "deals", "results", "nan", ""):
                        stop_row = i; break
                n_read = stop_row - header_row - 1
                df_raw = pd.read_csv(io.StringIO(raw_text), sep=sep, skiprows=header_row,
                                     nrows=n_read, dtype=str, on_bad_lines="skip")
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

        # Dédupliquer par Position si disponible (éviter double-comptage interne)
        if col_position:
            before = len(df_closed)
            df_closed = df_closed.drop_duplicates(subset=[col_position], keep="last")
            if len(df_closed) < before:
                st.info(f"Déduplication interne : {before - len(df_closed)} ligne(s) en double "
                        f"dans le fichier (même Position ID).")

        if df_closed.empty:
            st.warning("Aucun trade fermé détecté."); st.stop()

        # ── Parser la date d'ouverture pour le filtre de plage ────────────────
        df_closed["_open_dt"] = pd.to_datetime(
            df_closed[col_open_time], errors="coerce", format="mixed")
        _valid_dates = df_closed["_open_dt"].dropna()

        if _valid_dates.empty:
            st.warning("Impossible de lire les dates d'ouverture des positions.")
            st.stop()

        _dmin = _valid_dates.min().date()
        _dmax = _valid_dates.max().date()

        st.markdown("---")
        st.markdown("##### Plage de dates à importer")
        st.caption(f"Le fichier couvre du **{_dmin.strftime('%d/%m/%Y')}** "
                   f"au **{_dmax.strftime('%d/%m/%Y')}** ({len(df_closed)} positions fermées).")
        dc1, dc2 = st.columns(2)
        with dc1:
            imp_from = st.date_input("Depuis le", value=_dmin,
                                     min_value=_dmin, max_value=_dmax, key="imp_from")
        with dc2:
            imp_to = st.date_input("Jusqu'au", value=_dmax,
                                   min_value=_dmin, max_value=_dmax, key="imp_to")

        # Appliquer le filtre de dates (les positions sans date lisible sont écartées)
        _mask_date = (df_closed["_open_dt"].dt.date >= imp_from) & \
                     (df_closed["_open_dt"].dt.date <= imp_to)
        _before_date = len(df_closed)
        df_closed = df_closed[_mask_date].copy()
        st.info(f"{len(df_closed)} position(s) dans la plage sélectionnée "
                f"(sur {_before_date} au total dans le fichier).")

        if df_closed.empty:
            st.warning("Aucune position dans cette plage de dates."); st.stop()

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

                # Position ID MT5 : identifiant stable pour la déduplication
                _mt5_pos = rv(col_position, "").strip() if col_position else ""
                _close_full = ""
                if col_close_time:
                    try:
                        _close_full = pd.to_datetime(rv(col_close_time, "")).strftime("%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        _close_full = ""

                new_trades.append({
                    "id":         int(datetime.now().timestamp()*1000000)+len(new_trades),
                    "mt5_id":     _mt5_pos,
                    "close_datetime": _close_full,
                    "volume":     volume,
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

        # ── Déduplication contre la BASE existante ────────────────────────────
        # 1) Par Position ID MT5 (fiable, pour les imports récents)
        # 2) Par signature datetime+symbole+P&L (secours pour les anciens trades
        #    importés avant l'ajout du champ mt5_id)
        def _sig(t):
            return (str(t.get("datetime",""))[:16], str(t.get("symbol","")),
                    round(float(t.get("pnl",0) or 0), 2))
        _existing_mt5 = {str(t.get("mt5_id","")).strip()
                         for t in st.session_state.trades
                         if str(t.get("mt5_id","")).strip()}
        _existing_sig = {_sig(t) for t in st.session_state.trades}
        _dup_count = 0
        _fresh = []
        _dups = []
        for t in new_trades:
            _is_dup = (t.get("mt5_id") and t["mt5_id"] in _existing_mt5) \
                      or (_sig(t) in _existing_sig)
            if _is_dup:
                _dup_count += 1; _dups.append(t)
            else:
                _fresh.append(t)
        new_trades = _fresh

        if _dup_count:
            # Correction des trades déjà en base : prix de sortie, SL/TP, clôture, volume.
            # (Les anciens imports enregistraient le prix d'entrée comme prix de sortie.)
            _by_id = {str(t.get("mt5_id", "")).strip(): t for t in st.session_state.trades
                      if str(t.get("mt5_id", "")).strip()}
            _by_sig = {_sig(t): t for t in st.session_state.trades}
            _fixable = []
            for nt in _dups:
                old_t = _by_id.get(str(nt.get("mt5_id", "")).strip()) or _by_sig.get(_sig(nt))
                if old_t is None:
                    continue
                if any(abs(float(old_t.get(k) or 0) - float(nt.get(k) or 0)) > 1e-9 for k in ("exit", "sl", "tp")) \
                        or (nt.get("close_datetime") and not old_t.get("close_datetime")) \
                        or (nt.get("volume") and not old_t.get("volume")) \
                        or (nt.get("mt5_id") and not old_t.get("mt5_id")):
                    _fixable.append((old_t, nt))
            _bad_exit = sum(1 for o, _ in _fixable if float(o.get("exit") or 0) == float(o.get("entry") or 0)
                            and float(o.get("pnl") or 0) != 0)
            st.warning(f"{_dup_count} position(s) déjà présente(s) en base, non réimportée(s) (aucun doublon créé).")
            if _fixable:
                st.info(f"{len(_fixable)} de ces trades peuvent être complétés ou corrigés à partir de ce rapport"
                        + (f", dont {_bad_exit} enregistrés avec un prix de sortie égal au prix d'entrée "
                           f"(ancien import)" if _bad_exit else "")
                        + ". Seuls le prix de sortie, le SL, le TP, l'heure de clôture, le volume et l'identifiant MT5 "
                          "sont mis à jour : émotions, stratégies et notes sont conservées.")
                if is_admin() and st.button(f"Corriger les {len(_fixable)} trades déjà importés",
                                            key="imp_fix_existing", type="primary"):
                    for old_t, nt in _fixable:
                        for k in ("exit", "sl", "tp"):
                            old_t[k] = nt.get(k, old_t.get(k))
                        for k in ("close_datetime", "volume", "mt5_id"):
                            if nt.get(k):
                                old_t[k] = nt[k]
                    (st.success if db_save(st.session_state.trades) else st.warning)(
                        f"{len(_fixable)} trade(s) corrigé(s).")

        if not new_trades:
            st.success("Toutes les positions de cette plage sont déjà en base. "
                       "Rien de nouveau à importer.")
            st.stop()

        # Reconstruire l'aperçu à partir des seuls trades nouveaux
        preview_rows = [{
            "Date":        t["date"],
            "Heure":       t["time"],
            "Symbole":     t["symbol"],
            "Dir.":        t["direction"],
            "P&L net":     t["pnl"],
            "Position ID": t.get("mt5_id",""),
        } for t in new_trades]

        # ── Aperçu avec détail du calcul ──────────────────────────────────────
        total_imp  = round(sum(t["pnl"] for t in new_trades), 2)
        wins_imp   = [t for t in new_trades if t["pnl"] > 0]
        col_t      = "#00d4aa" if total_imp >= 0 else "#ff4d6d"

        st.markdown(f"### {len(new_trades)} nouveaux trades prêts à importer"
                    + (f" · {skipped} ignorés" if skipped else ""))

        s1, s2, s3 = st.columns(3)
        with s1: kpi('<i class="fa-solid fa-coins"></i>', "P&L Total", fmt(total_imp), "Résultat global", col_t)
        with s2: kpi('<i class="fa-solid fa-circle-check"></i>', "Gagnants", str(len(wins_imp)), f"{len(wins_imp)/len(new_trades)*100:.0f}% win", "#00d4aa")
        with s3: kpi('<i class="fa-solid fa-circle-xmark"></i>', "Perdants", str(len(new_trades)-len(wins_imp)), "Trades négatifs", "#ff4d6d")
        st.markdown(" ")

        # Tableau de vérification (30 premiers nouveaux trades)
        st.markdown("##### Aperçu des nouveaux trades (30 premiers)")
        df_preview = pd.DataFrame(preview_rows[:30])
        st.dataframe(
            df_preview.style
            .format({"P&L net":"{:+.2f}"})
            .map(lambda v: f"color:{'#00d4aa' if v>0 else '#ff4d6d' if v<0 else '#6b7894'}"
                 if isinstance(v,(int,float)) else "",
                 subset=["P&L net"]),
            use_container_width=True, hide_index=True
        )
        st.caption(
            f"Méthode P&L : {'Profit + Commission + Swap' if use_costs else 'Profit uniquement'}. "
            f"Déduplication par Position ID MT5 : réimporter le même fichier n'ajoutera aucun doublon."
        )

        st.markdown("---")
        add_mode = st.radio(
            "Mode d'import",
            ["Ajouter aux trades existants (recommandé)", "Remplacer TOUS les trades"],
            horizontal=True,
            help="« Ajouter » n'insère que les nouveaux trades (doublons déjà écartés). "
                 "« Remplacer » efface toute la base et la remplace par ces trades."
        )

        if st.button("Confirmer l'import", icon=":material/check_circle:", use_container_width=True):
            if "Remplacer" in add_mode:
                st.session_state.trades = new_trades
            else:
                # Les doublons ont déjà été écartés par mt5_id — ajout direct
                st.session_state.trades = st.session_state.trades + new_trades
            ok = cloud_save(st.session_state.trades)
            st.success(f"{len(new_trades)} nouveau(x) trade(s) importé(s) ({imp_mode}) — " +
                       ("synchronisés." if ok else "sauvegarde locale (sync à vérifier)."))
            st.session_state.page = "dashboard"; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CALENDRIER
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# PAGE : ANALYSE & NEWS — chiffres des annonces + impact sur les actifs
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "analyse":
    _ta = get_theme()
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:12px;flex-wrap:wrap'>"
        f"<span style='font-size:22px;font-weight:800;color:{_ta['text']}'>Analyse fondamentale & News</span>"
        f"<span style='font-size:12px;color:{_ta['muted']}'>politique monétaire · inflation · croissance · liquidité · "
        f"calendrier et surprises · heures en GMT+1</span></div>", unsafe_allow_html=True)

    # ── Réglages du chronomètre (annonces suivies) ────────────────────────────
    _me = st.session_state.get("auth_user", "")
    _ap = st.session_state.get("_alert_prefs") or alert_prefs_get(_me)
    with st.expander(f"Chronomètre · {', '.join(_ap.get('ccys') or ['USD'])} · "
                     f"affiché {int(_ap.get('chrono_h', 4))} h avant"):
        with st.form("chrono_form"):
            c1, c2, c3 = st.columns([2, 1.3, 1.6])
            with c1:
                ch_ccy = st.multiselect("Devises suivies", ALERT_CCYS,
                    default=[c for c in _ap.get("ccys", ["USD", "EUR"]) if c in ALERT_CCYS] or ["USD"])
            with c2:
                ch_imp = st.multiselect("Importance", ["High", "Medium", "Low"],
                    default=[i for i in _ap.get("impacts", ["High"]) if i in ("High", "Medium", "Low")] or ["High"],
                    format_func=lambda x: {"High": "Fort", "Medium": "Moyen", "Low": "Faible"}[x])
            with c3:
                ch_h = st.slider("Compte à rebours à partir de (h)", 1, 24, int(_ap.get("chrono_h", 4)))
            if st.form_submit_button("Enregistrer", type="primary"):
                _newp = dict(_ap); _newp.update({"ccys": ch_ccy or ["USD"], "impacts": ch_imp or ["High"],
                                                 "chrono_h": int(ch_h), "enabled": False})
                alert_prefs_set(_me, _newp)
                st.session_state["_alert_prefs"] = _newp
                st.rerun()
        st.caption("Le chronomètre s'affiche en haut de toutes les pages pour la prochaine annonce suivie.")

    USER_TZ_OFFSET = 1  # GMT+1 (position géographique de l'utilisateur)

    # ── Univers d'actifs (FX, indices, taux/obligations, matières, crypto) ────
    # cls = classe de réaction ; ccy = devises/pays dont les publications comptent
    ASSETS = {
        # Indices actions
        "US100 (Nasdaq)":      {"cls": "equity", "ccy": ["USD"]},
        "US500 (S&P 500)":     {"cls": "equity", "ccy": ["USD"]},
        "US30 (Dow Jones)":    {"cls": "equity", "ccy": ["USD"]},
        "DAX (Allemagne)":     {"cls": "equity", "ccy": ["EUR"]},
        "CAC 40 (France)":     {"cls": "equity", "ccy": ["EUR"]},
        "EuroStoxx 50":        {"cls": "equity", "ccy": ["EUR"]},
        "FTSE 100 (UK)":       {"cls": "equity", "ccy": ["GBP"]},
        "Nikkei 225 (JP)":     {"cls": "equity", "ccy": ["JPY"]},
        # Taux / obligations
        "US 10Y (T-Note)":     {"cls": "bond", "ccy": ["USD"]},
        "US 02Y (T-Note)":     {"cls": "bond", "ccy": ["USD"]},
        "Bund 10Y (DE)":       {"cls": "bond", "ccy": ["EUR"]},
        # FX majors
        "EUR/USD":             {"cls": "fx", "ccy": ["EUR", "USD"], "base": "EUR", "quote": "USD"},
        "GBP/USD":             {"cls": "fx", "ccy": ["GBP", "USD"], "base": "GBP", "quote": "USD"},
        "USD/JPY":             {"cls": "fx", "ccy": ["USD", "JPY"], "base": "USD", "quote": "JPY"},
        "USD/CHF":             {"cls": "fx", "ccy": ["USD", "CHF"], "base": "USD", "quote": "CHF"},
        "USD/CAD":             {"cls": "fx", "ccy": ["USD", "CAD"], "base": "USD", "quote": "CAD"},
        "AUD/USD":             {"cls": "fx", "ccy": ["AUD", "USD"], "base": "AUD", "quote": "USD"},
        "NZD/USD":             {"cls": "fx", "ccy": ["NZD", "USD"], "base": "NZD", "quote": "USD"},
        "EUR/GBP":             {"cls": "fx", "ccy": ["EUR", "GBP"], "base": "EUR", "quote": "GBP"},
        "DXY (Dollar US)":     {"cls": "dxy", "ccy": ["USD"]},
        # Métaux / énergie / crypto (cotés en USD)
        "XAUUSD (Or)":         {"cls": "metal", "ccy": ["USD"]},
        "XAGUSD (Argent)":     {"cls": "metal", "ccy": ["USD"]},
        "WTI (Pétrole)":       {"cls": "commodity", "ccy": ["USD"]},
        "BTC/USD":             {"cls": "crypto", "ccy": ["USD"]},
        "ETH/USD":             {"cls": "crypto", "ccy": ["USD"]},
    }
    _CLS_LABEL = {"equity": "Indice", "bond": "Obligation", "fx": "Devise",
                  "dxy": "Dollar", "metal": "Métal", "commodity": "Énergie",
                  "crypto": "Crypto"}

    # Polarité "économique" : +1 si un chiffre PLUS HAUT = économie plus forte/chaude
    def _growth_polarity(title):
        t = title.lower()
        if any(k in t for k in ["unemployment rate", "unemployment change", "jobless", "claims",
                                 "claimant", "continuing"]):
            return -1
        if any(k in t for k in ["cpi", "inflation", "ppi", "pce", "gdp", "retail", "nonfarm",
                                 "non-farm", "payroll", "employment change", "adp", "jolts",
                                 "pmi", "ism", "confidence", "sentiment", "durable", "industrial",
                                 "rate decision", "interest rate", "trade balance", "spending",
                                 "earnings", "wage", "production", "orders", "home sales",
                                 "building permits", "housing starts"]):
            return 1
        return 0

    def _category(title):
        t = title.lower()
        if any(k in t for k in ["rate decision", "interest rate", "rate statement",
                                "fomc", "ecb", "boe", "boj"]):
            return "Taux"
        if any(k in t for k in ["cpi", "ppi", "pce", "inflation"]): return "Inflation"
        if any(k in t for k in ["nonfarm", "non-farm", "payroll", "unemployment", "jobless",
                                "claims", "adp", "jolts", "employment", "wage", "earnings"]):
            return "Emploi"
        if any(k in t for k in ["gdp", "pmi", "ism", "retail", "confidence", "sentiment",
                                "durable", "industrial", "trade", "spending", "orders",
                                "home", "housing", "building", "production"]):
            return "Macro"
        return None

    def _impact(cfg, country, category, es):
        """Direction estimée sur l'actif à partir de la surprise économique es (-1/0/1)."""
        if es == 0: return 0
        cls = cfg["cls"]
        if cls == "fx":
            if country == cfg.get("base"): return es
            if country == cfg.get("quote"): return -es
            return 0
        if cls == "dxy":
            return es if country == "USD" else 0
        if cls in ("metal", "commodity", "crypto"):
            # cotés en USD : surprise US haussière -> USD fort + taux -> actif baisse
            return -es if country == "USD" else 0
        if cls == "equity":
            # inflation / taux plus chauds = hawkish = actions en baisse
            return -es if category in ("Inflation", "Taux") else es
        if cls == "bond":
            # économie/inflation plus chaudes = rendements en hausse = prix obligataire en baisse
            return -es
        return 0

    # Filtres de l'onglet News (lus ici pour les fonctions de carte ; affichés dans l'onglet)
    if "nsel_assets" not in st.session_state:
        st.session_state.nsel_assets = ["US100 (Nasdaq)", "DXY (Dollar US)", "XAUUSD (Or)"]
    if "nsel_imp" not in st.session_state:
        st.session_state.nsel_imp = ["High", "Medium"]
    _scope_map = {"3 semaines": "all", "Semaine passée": "lastweek",
                  "En cours": "thisweek", "À venir": "nextweek"}
    sel_assets = list(st.session_state.nsel_assets) or ["US100 (Nasdaq)", "DXY (Dollar US)", "XAUUSD (Or)"]
    imp_sel = list(st.session_state.nsel_imp)

    _imp_badge = {"High": ("Fort", _ta["loss"]), "Medium": ("Moyen", _ta["orange"]),
                  "Low": ("Faible", _ta["muted"])}

    def _stat_cell(lbl, val, big=False, color=None, bg=None):
        color = color or _ta["text"]
        vfont = "20px" if big else "14px"
        bgc = f"background:{bg};" if bg else ""
        return (f"<div style='flex:1;text-align:center;padding:6px 4px;border-radius:8px;{bgc}'>"
                f"<div style='font-size:9px;letter-spacing:.5px;text-transform:uppercase;"
                f"color:{_ta['muted']};font-weight:700'>{lbl}</div>"
                f"<div style='font-size:{vfont};font-weight:800;color:{color};"
                f"font-family:JetBrains Mono,monospace;line-height:1.3'>{val if val is not None else '—'}</div></div>")

    def _dir_chip(aset, d):
        if d > 0:   cc, ic = _ta["win"], "▲"
        elif d < 0: cc, ic = _ta["loss"], "▼"
        else:       cc, ic = _ta["muted"], "•"
        return (f"<span style='display:inline-block;font-size:11px;font-weight:700;color:{cc};"
                f"background:{cc}1A;border:1px solid {cc}40;border-radius:6px;padding:1px 7px;"
                f"margin:2px 4px 2px 0'>{ic} {_html.escape(aset.split(' (')[0])}</span>")

    _DIRLBL = {1: "Hausse", -1: "Baisse", 0: "Neutre"}

    def _kb_details(e, opened=False):
        """Fiche dépliable : description de l'indicateur, lecture du marché, scénarios, liens."""
        esc = lambda x: _html.escape(str(x), quote=False)
        d = _kb.describe(e["title"], e["country"]) if _kb else None
        lab = (f"font-size:10px;letter-spacing:.6px;text-transform:uppercase;font-weight:800;"
               f"color:{_ta['muted']};margin:10px 0 3px")
        txt = f"font-size:12.5px;line-height:1.55;color:{_ta['text']}"
        if d is None:
            body = (f"<div style='{txt}'>Fiche détaillée indisponible (fichier <code>econ_kb.py</code> "
                    f"absent du dépôt). L'impact dépend de l'écart entre le chiffre publié et le consensus.</div>")
        else:
            body = (f"<div style='{lab}'>Ce que c'est</div><div style='{txt}'>{esc(d['what'])}</div>"
                    f"<div style='display:flex;gap:18px;flex-wrap:wrap;font-size:11.5px;color:{_ta['muted']};margin-top:4px'>"
                    f"<span><b style='color:{_ta['text']}'>Publié par</b> : {esc(d['pub'])}</span>"
                    f"<span><b style='color:{_ta['text']}'>Fréquence</b> : {esc(d['freq'])}</span></div>"
                    f"<div style='{lab}'>Pourquoi le marché le suit</div><div style='{txt}'>{esc(d['why'])}</div>"
                    f"<div style='{lab}'>Lecture habituelle</div>"
                    f"<div style='{txt}'><b style='color:{_ta['win']}'>Au-dessus du consensus</b> : {esc(d['up'])}<br>"
                    f"<b style='color:{_ta['loss']}'>En dessous du consensus</b> : {esc(d['down'])}</div>")
            if e["has_actual"] and e["delta"] is not None and e["forecast"]:
                above = e["delta"] > 0; same = e["delta"] == 0
                verdict = ("conforme au consensus, réaction en général limitée." if same else
                           (("au-dessus" if above else "en dessous") + " du consensus. Lecture habituelle : "
                            + (d["up"] if above else d["down"]).split(" : ", 1)[-1]))
                vcol = _ta["muted"] if same else (_ta["win"] if e["es"] > 0 else _ta["loss"] if e["es"] < 0 else _ta["accent"])
                body += (f"<div style='margin-top:8px;padding:8px 10px;border-radius:8px;background:{vcol}14;"
                         f"border:1px solid {vcol}40;{txt}'><b style='color:{vcol}'>Résultat publié</b> : "
                         f"{esc(e['actual'])} pour {esc(e['forecast'])} attendu, {esc(verdict)}</div>")
        if e.get("scen"):
            rows = "".join(
                f"<tr><td style='padding:3px 10px 3px 0;color:{_ta['text']};font-size:12px'>{esc(a.split(' (')[0])}</td>"
                f"<td style='padding:3px 10px'>{_dir_chip(_DIRLBL[u], u)}</td>"
                f"<td style='padding:3px 10px'>{_dir_chip(_DIRLBL[dn], dn)}</td></tr>"
                for a, (u, dn) in e["scen"].items())
            body += (f"<div style='{lab}'>Scénarios pour vos actifs</div>"
                     f"<table style='border-collapse:collapse'><tr>"
                     f"<th style='text-align:left;font-size:10px;color:{_ta['muted']};padding:0 10px 2px 0'>Actif</th>"
                     f"<th style='font-size:10px;color:{_ta['win']};padding:0 10px 2px'>Si au-dessus</th>"
                     f"<th style='font-size:10px;color:{_ta['loss']};padding:0 10px 2px'>Si en dessous</th></tr>{rows}</table>")
        if d is not None and d["links"]:
            body += (f"<div style='{lab}'>Lire pour aller plus loin</div><div>" + "".join(
                f"<a href='{u}' target='_blank' rel='noopener noreferrer' style='display:inline-block;"
                f"font-size:12px;font-weight:700;color:{_ta['accent']};text-decoration:none;"
                f"border:1px solid {_ta['accent']}55;border-radius:7px;padding:3px 10px;margin:2px 6px 2px 0'>"
                f"Lire : {esc(l)} ↗</a>" for l, u in d["links"]) + "</div>")
        return (f"<details{' open' if opened else ''} style='margin-top:8px;border-top:1px dashed {_ta['border']};padding-top:6px'>"
                f"<summary style='cursor:pointer;font-size:12px;font-weight:700;color:{_ta['accent']};"
                f"list-style-position:inside'>Comprendre cette annonce et son impact</summary>"
                f"<div style='padding:4px 2px 2px'>{body}</div></details>")

    def _build_entry(ev):
        """Annonce brute -> entrée enrichie (chiffres, surprise, impact par actif)."""
        title = str(ev["title"]); country = str(ev["country"])
        actual, forecast, previous = ev["actual"], ev["forecast"], ev["previous"]
        has_actual = str(actual).strip() not in ("", "nan", "None")
        cat = _category(title)
        a, f = _to_num(actual), _to_num(forecast)
        # surprise économique (vs consensus)
        pol = _growth_polarity(title)
        es = 0
        if a is not None and f is not None and pol != 0 and a != f:
            es = 1 if ((a > f and pol > 0) or (a < f and pol < 0)) else -1
        # delta affichable
        delta = (a - f) if (a is not None and f is not None) else None
        tlabel, tdt = _fmt_local(ev["date"])
        # impact par actif concerné
        impacts = {}
        for aset in sel_assets:
            cfg = ASSETS[aset]
            if country not in cfg["ccy"]:
                continue
            adir = _impact(cfg, country, cat, es) if (has_actual and es != 0) else 0
            impacts[aset] = adir
        # scénarios : effet estimé si le chiffre sort au-dessus / en dessous du consensus
        scen = {}
        if pol != 0 and cat:
            for aset in sel_assets:
                cfg = ASSETS[aset]
                if country in cfg["ccy"]:
                    scen[aset] = (_impact(cfg, country, cat, pol), _impact(cfg, country, cat, -pol))
        return {
            "scen": scen,
            "title": title, "country": country, "impact": str(ev.get("impact", "")),
            "actual": str(actual).strip() if has_actual else None,
            "forecast": str(forecast).strip() if str(forecast).strip() not in ("", "nan", "None") else None,
            "previous": str(previous).strip() if str(previous).strip() not in ("", "nan", "None") else None,
            "has_actual": has_actual, "cat": cat, "es": es, "delta": delta,
            "impacts": impacts, "date": tlabel, "dt": tdt,
        }

    def _render_card(e, focus=False):
        """Carte d'une annonce (focus = mise en avant depuis le chronomètre)."""
        # couleur de bord selon la surprise
        if e["has_actual"] and e["es"] != 0:
            edge = _ta["win"] if e["es"] > 0 else _ta["loss"]
            act_col = edge
            act_bg = edge + "1A"
            _above = (e["delta"] or 0) > 0
            surp_txt = ("⬆ Au-dessus du consensus" if _above else "⬇ En dessous du consensus") + \
                       (" · lecture favorable à la devise" if e["es"] > 0 else " · lecture défavorable à la devise")
            surp_col = _ta["win"] if e["es"] > 0 else _ta["loss"]
        elif e["has_actual"]:
            edge = _ta["muted"]; act_col = _ta["text"]; act_bg = _ta["muted"] + "14"
            surp_txt, surp_col = "➡ Conforme / neutre", _ta["muted"]
        else:
            edge = _ta["accent"]; act_col = _ta["muted"]; act_bg = "transparent"
            surp_txt, surp_col = "À venir", _ta["accent"]

        imp_lbl, imp_col = _imp_badge.get(e["impact"], ("", _ta["muted"]))
        cat_txt = e["cat"] or "—"
        status = "PUBLIÉ" if e["has_actual"] else "À VENIR"
        status_col = edge

        # delta chiffré
        delta_html = ""
        if e["delta"] is not None and e["has_actual"]:
            dsign = "+" if e["delta"] >= 0 else ""
            dtxt = f"{dsign}{e['delta']:.2f}".rstrip("0").rstrip(".")
            delta_html = (f"<span style='font-size:11px;color:{surp_col};font-weight:700;"
                          f"margin-left:8px'>Δ {dtxt} vs prévu</span>")

        # chips d'impact par actif
        chips = ""
        for aset, adir in e["impacts"].items():
            if adir > 0:
                cc, ic, tt = _ta["win"], "▲", "haussier"
            elif adir < 0:
                cc, ic, tt = _ta["loss"], "▼", "baissier"
            else:
                cc, ic, tt = _ta["muted"], "•", "neutre"
            short = aset.split(" (")[0]
            chips += (f"<span style='display:inline-flex;align-items:center;gap:4px;"
                      f"font-size:11px;font-weight:700;color:{cc};background:{cc}1A;"
                      f"border:1px solid {cc}44;border-radius:7px;padding:2px 9px;margin:3px 4px 0 0'>"
                      f"{ic} {short}</span>")
        if not chips:
            _noimp = "En attente du chiffre" if not e["has_actual"] else "Pas d'impact directionnel estimé"
            chips = (f"<span style='font-size:11px;color:{_ta['muted']}'>{_noimp}</span>")

        st.markdown(
            f"<div style='background:{_ta['card']};border:1px solid {_ta['accent'] if focus else _ta['border']};"
            f"border-left:4px solid {edge};border-radius:6px 24px 6px 24px;padding:12px 16px;margin-bottom:10px;"
            f"{'box-shadow:0 0 0 2px ' + _ta['accent'] + '55,0 6px 22px ' + _ta['accent'] + '33' if focus else ''}'>"
            # ligne du haut
            f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px'>"
            f"<span style='font-size:11px;font-weight:800;color:{status_col};"
            f"background:{status_col}1A;border-radius:6px;padding:2px 8px'>{status}</span>"
            f"<span style='font-size:12px;font-weight:800;color:{_ta['text']};"
            f"border:1px solid {_ta['border']};border-radius:6px;padding:1px 7px'>{e['country']}</span>"
            f"<span style='font-size:10px;font-weight:700;color:{imp_col}'>● {imp_lbl}</span>"
            f"<span style='font-size:10px;color:{_ta['muted']}'>{cat_txt}</span>"
            f"<span style='font-size:11px;color:{_ta['muted']};margin-left:auto;"
            f"font-family:JetBrains Mono,monospace'>{e['date']}</span></div>"
            # titre
            f"<div style='font-size:14px;font-weight:700;color:{_ta['text']};margin-bottom:8px'>"
            f"{e['title']}</div>"
            # cellules prévu / publié / précédent
            f"<div style='display:flex;gap:8px;margin-bottom:8px'>"
            f"{_stat_cell('Prévu (consensus)', e['forecast'])}"
            f"{_stat_cell('Publié', e['actual'], big=True, color=act_col, bg=act_bg)}"
            f"{_stat_cell('Précédent', e['previous'])}"
            f"</div>"
            # bandeau surprise
            f"<div style='font-size:12px;font-weight:700;color:{surp_col};margin-bottom:6px'>"
            f"{surp_txt}{delta_html}</div>"
            # chips impact
            f"<div style='display:flex;flex-wrap:wrap;align-items:center;gap:0'>"
            f"<span style='font-size:10px;color:{_ta['muted']};text-transform:uppercase;"
            f"letter-spacing:.5px;font-weight:700;margin-right:8px'>Impact estimé</span>{chips}</div>"
            f"{_kb_details(e, opened=focus)}"
            f"</div>",
            unsafe_allow_html=True)

    # ── Annonce ciblée depuis la sphère du chronomètre ───────────────────────
    _fe = st.session_state.get("focus_event")
    if _fe:
        def _find_focus(evs):
            for _ev in evs or []:
                _r = {_k: _ev.get(_v) for _k, _v in (("title", "title"), ("country", "country"),
                      ("impact", "impact"), ("actual", "actual"), ("forecast", "forecast"),
                      ("previous", "previous"), ("date", "date"))}
                if str(_r["title"]) not in _fe.get("titles", []):
                    continue
                _d = _parse_utc(_r["date"])
                if _d is None:
                    continue
                from datetime import timezone as _tzf
                if abs(_d.replace(tzinfo=_tzf.utc).timestamp() * 1000 - _fe["t"]) <= 90_000:
                    for _k in ("actual", "forecast", "previous"):
                        if _r[_k] is None: _r[_k] = ""
                    return _r
            return None
        _fr = _find_focus(_fetch_calendar("all")[0])
        _fh1, _fh2 = st.columns([6, 1])
        with _fh1:
            st.markdown(f"<div style='font-size:11px;letter-spacing:1px;text-transform:uppercase;font-weight:800;"
                        f"color:{_ta['accent']};margin:6px 0 4px'>Prochaine annonce · ouverte depuis le chronomètre</div>",
                        unsafe_allow_html=True)
        with _fh2:
            st.button("Fermer", key="focus_close", icon=":material/close:", use_container_width=True,
                      on_click=lambda: st.session_state.pop("focus_event", None))
        if _fr is None:
            st.info("Annonce introuvable dans le calendrier actuel (déjà passée ou source momentanément indisponible).")
        else:
            _render_card(_build_entry(_fr), focus=True)
        st.markdown("---")

    @st.fragment
    def _news_fragment():
        """Onglet News : un filtre ne relance que cet onglet, pas le chargement des données macro."""
        global sel_assets, imp_sel, _src
        with st.container(horizontal=True, key="news_filters", gap="small"):
            sel_assets = check_filter("Actifs", list(ASSETS.keys()), "nsel_assets", "nfa", all_label="aucun",
                                      fmt=lambda a: a.split(" (")[0], icon=":material/candlestick_chart:")
            with st.popover(f"Période · {st.session_state.get('sc_scope', '3 semaines')}", icon=":material/date_range:",
                            use_container_width=True):
                scope_lbl = st.radio("Période", list(_scope_map.keys()), key="sc_scope", label_visibility="collapsed")
            imp_sel = check_filter("Impact", ["High", "Medium", "Low"], "nsel_imp", "nfi", all_label="tous",
                                   fmt=lambda x: {"High": "Fort", "Medium": "Moyen", "Low": "Faible"}[x],
                                   icon=":material/priority_high:")
        if not sel_assets:
            sel_assets = ["US100 (Nasdaq)", "DXY (Dollar US)", "XAUUSD (Or)"]
        events, _src = _fetch_calendar(_scope_map[scope_lbl])
        if not events:
            events = []
            st.warning("Calendrier économique indisponible pour le moment (sources injoignables). "
                       "Les autres onglets restent alimentés par FRED, BIS et Yahoo Finance.")
        _has_actual_src = "sans chiffre publié" not in _src
        # Fraîcheur + rafraîchissement automatique autour des annonces
        import time as _tmn
        _sk = _scope_map[scope_lbl]
        _ts = st.session_state.get(f"_cal_ts_{_sk}")
        _hot = st.session_state.get(f"_cal_hot_{_sk}", 0) > _tmn.time()
        _age = int((_tmn.time() - _ts) // 60) if _ts else None
        _fr1, _fr2 = st.columns([5, 1.2], vertical_alignment="center")
        with _fr1:
            st.caption((f"Données mises à jour il y a {_age} min" if _age else "Données à jour")
                       + (" · annonce en cours : actualisation automatique chaque minute jusqu'à la publication du chiffre"
                          if _hot else " · actualisation toutes les 30 min, chaque minute autour d'une annonce"))
        with _fr2:
            if st.button("Actualiser", key="cal_refresh", icon=":material/refresh:", use_container_width=True):
                _fetch_calendar_cached.clear(); st.rerun(scope="fragment")
        if _hot:
            import streamlit.components.v1 as _cmp
            st.markdown("<style>.st-key-cal_auto{position:fixed!important;left:-10000px;top:0;width:1px;height:1px;"
                        "overflow:hidden}</style>", unsafe_allow_html=True)
            with st.container(key="cal_auto"):
                st.button("auto", key="cal_auto_btn")
                _cmp.html("<script>setTimeout(()=>{try{const b=window.parent.document.querySelector("
                          "'.st-key-cal_auto button');if(b)b.click();}catch(e){}},60000);</script>", height=0)
        if _has_actual_src:
            st.caption(f"✅ Source : {_src} — chiffres publiés (Actual) disponibles.")
        else:
            st.warning(f"⚠️ Sources avec Actual (TradingView / ForexFactory) injoignables depuis "
                       f"le serveur. Repli sur {_src} : seules les prévisions sont affichées.")

        df = pd.DataFrame(events)
        ren = {}
        for col in df.columns:
            cl = str(col).strip().lower()
            if cl in ("country", "currency"): ren[col] = "country"
            elif cl in ("impact", "importance"): ren[col] = "impact"
            elif cl in ("title", "event", "name"): ren[col] = "title"
            elif cl == "actual": ren[col] = "actual"
            elif cl in ("forecast", "estimate"): ren[col] = "forecast"
            elif cl in ("previous", "prior"): ren[col] = "previous"
            elif cl in ("date", "datetime"): ren[col] = "date"
        df = df.rename(columns=ren)
        for col in ("country", "impact", "title", "actual", "forecast", "previous", "date"):
            if col not in df.columns: df[col] = ""
        _calendar_tab(df)

    def _calendar_tab(df):
        """Fil des publications : consensus vs résultat et impact par actif."""
        if df.empty or "country" not in df.columns:
            st.info("Calendrier indisponible pour le moment.")
            return
        # Union des devises de tous les actifs sélectionnés
        all_ccy = sorted({c for a in sel_assets for c in ASSETS[a]["ccy"]})
        df = df[df["country"].isin(all_ccy)]
        if imp_sel: df = df[df["impact"].isin(imp_sel)]
        if df.empty:
            st.info("Aucune publication pour ces actifs sur la période / les filtres choisis.")
            return

        # ── Construction des événements enrichis ─────────────────────────────────
        _w = {"High": 3, "Medium": 2, "Low": 1}
        feed = []
        # score par actif : {asset: [somme, poids]}
        asset_score = {a: [0.0, 0.0] for a in sel_assets}

        for _, ev in df.iterrows():
            _e = _build_entry(ev)
            feed.append(_e)
            if _e["has_actual"]:
                _wv = _w.get(_e["impact"], 1)
                for aset, adir in _e["impacts"].items():
                    if adir != 0:
                        asset_score[aset][0] += adir * _wv
                        asset_score[aset][1] += _wv

        def _norm(acc):
            return (acc[0] / acc[1] * 100.0) if acc[1] else 0.0

        def _bias_label(s):
            if s >= 50:  return "Très Haussier", _ta["win"]
            if s >= 15:  return "Haussier", _ta["win"]
            if s > -15:  return "Neutre", _ta["muted"]
            if s > -50:  return "Baissier", _ta["loss"]
            return "Très Baissier", _ta["loss"]

        # ── Bandeau de biais par actif ───────────────────────────────────────────
        st.markdown("##### <i class='fa-solid fa-gauge-high'></i> Biais fondamental par actif",
                    unsafe_allow_html=True)
        ncol = min(3, len(sel_assets))
        rows_assets = [sel_assets[i:i + ncol] for i in range(0, len(sel_assets), ncol)]
        for grp in rows_assets:
            bcols = st.columns(ncol)
            for i, aset in enumerate(grp):
                cfg = ASSETS[aset]
                s = _norm(asset_score[aset])
                lbl, col = _bias_label(s)
                n_rel = sum(
                    1 for e in feed if aset in e["impacts"] and e["has_actual"] and e["impacts"][aset] != 0)
                pos = max(0.0, min(100.0, (s + 100.0) / 2.0))  # position 0-100 sur la barre
                with bcols[i]:
                    st.markdown(
                        f"<div class='grad-card' style='padding:14px 16px'>"
                        f"<div style='display:flex;justify-content:space-between;align-items:center'>"
                        f"<span style='font-weight:800;color:{_ta['text']};font-size:14px'>{aset}</span>"
                        f"<span style='font-size:9px;letter-spacing:.5px;text-transform:uppercase;"
                        f"color:{_ta['muted']};border:1px solid {_ta['border']};padding:1px 6px;"
                        f"border-radius:6px'>{_CLS_LABEL.get(cfg['cls'], '')}</span></div>"
                        f"<div style='display:flex;align-items:baseline;gap:8px;margin:6px 0 2px'>"
                        f"<span style='font-size:26px;font-weight:800;color:{col};"
                        f"font-family:JetBrains Mono,monospace'>{s:+.0f}</span>"
                        f"<span style='font-size:12px;font-weight:700;color:{col}'>{lbl}</span></div>"
                        f"<div style='position:relative;height:7px;border-radius:4px;margin:8px 0 4px;"
                        f"background:linear-gradient(90deg,{_ta['loss']}33,{_ta['muted']}22,{_ta['win']}33)'>"
                        f"<div style='position:absolute;left:calc({pos:.0f}% - 5px);top:-2px;width:10px;"
                        f"height:11px;border-radius:3px;background:{col};box-shadow:0 0 6px {col}'></div></div>"
                        f"<div style='font-size:10px;color:{_ta['muted']}'>{n_rel} chiffre(s) publié(s) pris en compte</div>"
                        f"</div>",
                        unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:11px;color:{_ta['muted']};margin:6px 2px 2px'>"
            f"Score = moyenne pondérée (importance) de l'effet des surprises publiées sur l'actif. "
            f"Positif = pression haussière, négatif = baissière.</div>",
            unsafe_allow_html=True)

        st.markdown("---")

        # ── Fil des publications : Prévu vs Publié + impact ──────────────────────
        st.markdown("##### <i class='fa-solid fa-newspaper'></i> Publications — consensus vs résultat",
                    unsafe_allow_html=True)

        # Tri : publiés récents en premier, puis à venir (plus proche d'abord)
        published = [e for e in feed if e["has_actual"]]
        upcoming = [e for e in feed if not e["has_actual"]]
        published.sort(key=lambda e: e["dt"] or datetime.min, reverse=True)
        upcoming.sort(key=lambda e: e["dt"] or datetime.max)
        ordered = published + upcoming
        MAXN = 45
        shown = ordered[:MAXN]

        for e in shown:
            _render_card(e)

        if len(ordered) > MAXN:
            st.caption(f"{len(ordered)} publications au total · {MAXN} affichées (publiées en premier). "
                       f"Affinez via les filtres Période / Impact.")

        st.caption(f"Source des données : {_src}. L'impact par actif est une estimation directionnelle "
                   "fondée sur la réaction habituelle : un chiffre supérieur au consensus renforce "
                   "généralement la devise (sauf chômage / inscriptions). Pour les indices actions, "
                   "une inflation ou un taux plus chauds pèsent (effet hawkish) ; pour les obligations, "
                   "des chiffres plus chauds font monter les rendements et baisser le prix. "
                   "Analyse indicative, à recouper avec le contexte de marché.")

    # ══════════════════════════════════════════════════════════════════════════
    # TABLEAU DE BORD MACRO : données, biais, puis zones
    # ══════════════════════════════════════════════════════════════════════════
    _cs_m = get_chart_style()
    _mx = macro_get()
    if _mx["loading"]:
        @st.fragment(run_every=4)
        def _mx_wait():
            if not _mx_store()["running"]:
                st.rerun(scope="app")
            st.caption("⏳ Données macro en cours de chargement en arrière-plan (FRED, BIS, Yahoo Finance). "
                       "Tu peux utiliser la page, elle se complète toute seule.")
        _mx_wait()
    try:
        _ev3w = mx_events_frame(_fetch_calendar("all")[0])
    except Exception:
        _ev3w = pd.DataFrame()
    try:
        _evr = mx_events_frame(_mx["rates"])
    except Exception:
        _evr = pd.DataFrame()
    _ev_all = pd.concat([x for x in (_ev3w, _evr) if not x.empty]).drop_duplicates(
        subset=["title", "country", "date"]) if (not _ev3w.empty or not _evr.empty) else pd.DataFrame()

    _pol = mx_policy(_mx, _evr)
    _fed = mx_fed_pricing(_mx)
    _stance = mx_stance(_pol, _ev_all, _fed)
    _reg_sc, _reg_lab, _reg_comps = mx_risk_regime(_mx)
    _strength = mx_strength(_mx)
    _surp = {c: mx_surprise_index(_ev_all, c) for c in MX_CCYS}

    def _sgn_col(v, pos_good=True):
        if v is None: return _ta["muted"]
        if abs(v) < 1e-12: return _ta["muted"]
        return _ta["win"] if ((v > 0) == pos_good) else _ta["loss"]

    def _nfr(v, d=2, suf=""):
        return "—" if v is None else (f"{v:,.{d}f}".replace(",", " ").replace(".", ",") + suf)

    def _spark(s, color, w=110, h=30, n=60):
        if s is None or len(s) < 3:
            return ""
        v = list(s.iloc[-n:].astype(float))
        lo, hi = min(v), max(v); rg = (hi - lo) or 1.0
        pts = " ".join(f"{i * w / (len(v) - 1):.1f},{h - 2 - (x - lo) / rg * (h - 4):.1f}" for i, x in enumerate(v))
        return (f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}'><polyline points='{pts}' fill='none' "
                f"stroke='{color}' stroke-width='1.6' stroke-linejoin='round'/></svg>")

    def _gauge(score, lab_neg, lab_pos):
        pos = 50 if score is None else (score + 100) / 2
        col = _ta["muted"] if score is None else (_ta["win"] if score >= 20 else (_ta["loss"] if score <= -20 else _ta["orange"]))
        return (f"<div style='position:relative;height:8px;border-radius:999px;margin:10px 0 4px;"
                f"background:linear-gradient(90deg,{_ta['loss']}55,{_ta['muted']}22,{_ta['win']}55)'>"
                f"<div style='position:absolute;left:calc({pos:.0f}% - 7px);top:-4px;width:14px;height:16px;"
                f"border-radius:4px;background:{col};box-shadow:0 0 8px {col}'></div></div>"
                f"<div style='display:flex;justify-content:space-between;font-size:10px;color:{_ta['muted']}'>"
                f"<span>{lab_neg}</span><span>{lab_pos}</span></div>")

    def _chip(txt, col):
        return (f"<span style='font-size:11px;font-weight:800;color:{col};background:{col}18;border:1px solid {col}44;"
                f"border-radius:999px;padding:1px 9px;white-space:nowrap'>{txt}</span>")

    # ── ZONE 1 : bandeau global (régime + baromètres de liquidité) ─────────────
    def _tile(label, s, unit, d=2, pos_good=None, chg_n=1, how="lvl", shape="22px 6px 22px 6px"):
        s2 = mx_transform(s, how) if s is not None else None
        v, p, dt_ = mx_last(s2)
        ch = (v - s2.iloc[-1 - chg_n]) if (s2 is not None and len(s2) > chg_n) else None
        col = _ta["text"] if pos_good is None else _sgn_col(ch, pos_good)
        return (f"<div style='flex:1 1 150px;min-width:140px;background:{_ta['card']};border:1px solid {_ta['border']};"
                f"border-radius:{shape};padding:10px 14px'>"
                f"<div style='font-size:10px;letter-spacing:1px;text-transform:uppercase;color:{_ta['muted']};font-weight:700'>{label}</div>"
                f"<div style='display:flex;align-items:flex-end;justify-content:space-between;gap:6px'>"
                f"<div><div style='font-size:20px;font-weight:800;color:{_ta['text']};font-family:JetBrains Mono,monospace'>"
                f"{_nfr(v, d)}<span style='font-size:11px;color:{_ta['muted']}'> {unit}</span></div>"
                f"<div style='font-size:11px;font-weight:700;color:{col}'>{'' if ch is None else ('▲ ' if ch > 0 else '▼ ') + _nfr(abs(ch), d)}</div></div>"
                f"{_spark(s2, col if pos_good is not None else _ta['accent'])}</div></div>")

    _rc = _ta["muted"] if _reg_sc is None else (_ta["win"] if _reg_sc >= 20 else (_ta["loss"] if _reg_sc <= -20 else _ta["orange"]))
    _vix = _mx["yahoo"].get("^VIX", _mx["fred"].get("VIXCLS"))
    _dxy = _mx["yahoo"].get("DX-Y.NYB", _mx["fred"].get("DTWEXBGS"))
    _hy = _mx["fred"].get("BAMLH0A0HYM2"); _ig = _mx["fred"].get("BAMLC0A0CM")
    _hyig = (_hy - _ig).dropna() if (_hy is not None and _ig is not None) else None
    st.markdown(
        "<div style='display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 10px'>"
        f"<div style='flex:1.4 1 230px;min-width:220px;background:linear-gradient(135deg,{_rc}1f,{_ta['card']});"
        f"border:1px solid {_rc}55;border-radius:30px 8px 30px 8px;padding:10px 16px'>"
        f"<div style='font-size:10px;letter-spacing:1px;text-transform:uppercase;color:{_ta['muted']};font-weight:700'>Régime de marché</div>"
        f"<div style='display:flex;align-items:baseline;gap:10px'><span style='font-size:22px;font-weight:800;color:{_rc}'>{_reg_lab}</span>"
        f"<span style='font-family:JetBrains Mono,monospace;color:{_rc};font-weight:700'>{'' if _reg_sc is None else f'{_reg_sc:+.0f}'}</span></div>"
        f"{_gauge(_reg_sc, 'Risk-Off', 'Risk-On')}</div>"
        + _tile("Dollar (DXY)", _dxy, "", 2, None)
        + _tile("VIX", _vix, "", 1, False, shape="44px 12px 12px 44px")
        + _tile("Courbe 10 ans - 2 ans", _mx["fred"].get("T10Y2Y"), "pb", 0, True, how="bp")
        + _tile("Spread HY - IG", _hyig, "pb", 0, False, how="bp",
                shape="3px 20px 3px 20px")
        + "</div>", unsafe_allow_html=True)
    if _mx["missing"] and not _mx["loading"]:
        st.caption("Données partielles · " + " · ".join(
            (f"{k} : indisponible" if v == ["tout"] else f"{k} : {len(v)} série(s) manquante(s)")
            for k, v in _mx["missing"].items()) + " · nouvel essai automatique dans 10 min")

    (tab_syn, tab_cal, tab_mon, tab_inf, tab_gro, tab_liq, tab_met) = st.tabs([
        "Synthèse & biais", "Calendrier & surprises", "Politique monétaire", "Inflation & Emploi",
        "Croissance", "Liquidité & Sentiment", "Méthode & sources"])

    def _hz_series(s, key, default="3 ans"):
        hz = st.session_state.get(key, default)
        days = {"1 an": 365, "3 ans": 1095, "5 ans": 1825, "10 ans": 3650}.get(hz, 1095)
        return s[s.index >= s.index[-1] - pd.Timedelta(days=days)] if (s is not None and len(s)) else s

    def _ts_chart(series_list, key, height=250, ref=None, unit=""):
        """series_list : [(libellé, série, couleur)] ; ref = ligne horizontale (ex. cible 2 %)."""
        fig = go.Figure()
        for lab, s, col in series_list:
            if s is None or len(s) == 0:
                continue
            s = _hz_series(s, key)
            fig.add_trace(go.Scatter(x=s.index, y=s.values, name=lab, mode="lines",
                                     line=dict(color=col, width=2), hovertemplate=f"%{{y:.2f}} {unit}<extra>{lab}</extra>"))
        if not fig.data:
            st.caption("Série indisponible pour le moment.")
            return
        if ref is not None:
            fig.add_hline(y=ref, line=dict(color=_ta["muted"], dash="dot", width=1))
        fig.update_layout(**chart_layout(_ta, _cs_m, height=height, showlegend=len(fig.data) > 1,
                                         margin=dict(l=44, r=12, t=24, b=30),
                                         legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0,
                                                     font=dict(color=_ta["text"], size=11), bgcolor="rgba(0,0,0,0)")))
        chart_axes(fig, _ta, _cs_m)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=f"mxc_{key}_{series_list[0][0]}")

    def _hz_picker(key):
        st.radio("Horizon", ["1 an", "3 ans", "5 ans", "10 ans"], index=1, horizontal=True, key=key,
                 label_visibility="collapsed")

    _MX_CAL_MATCH = {  # série FRED -> mots du titre de la publication correspondante (USD)
        "CPIAUCSL": (["cpi"], ["core", "m/m", "mom"]), "CPILFESL": (["core cpi"], ["m/m", "mom"]),
        "PCEPILFE": (["core pce"], []), "PCEPI": (["pce price"], ["core"]),
        "PAYEMS": (["non-farm", "nonfarm"], []), "UNRATE": (["unemployment rate"], []),
        "CES0500000003": (["average hourly earnings"], []), "ICSA": (["jobless claims", "initial claims"], ["continuing"]),
        "A191RL1Q225SBEA": (["gdp"], ["deflator", "price"]), "RSAFS": (["retail sales"], ["core", "control", "ex"]),
        "UMCSENT": (["michigan", "consumer sentiment"], ["expectations", "inflation"]),
        "INDPRO": (["industrial production"], []),
    }

    def _cal_last(sid):
        if _ev_all is None or _ev_all.empty or sid not in _MX_CAL_MATCH:
            return None
        inc, exc = _MX_CAL_MATCH[sid]
        t = _ev_all["title"].astype(str).str.lower()
        m = (_ev_all["country"] == "USD") & _ev_all["has_actual"] & t.map(lambda x: any(k in x for k in inc) and not any(k in x for k in exc))
        d = _ev_all[m].sort_values("dt")
        return None if d.empty else d.iloc[-1]

    def _ind_card(sid, label=None, d=1, pos_good=True, shape="22px 6px 22px 6px"):
        lab_, unit, how = MX_FRED[sid]
        s = mx_transform(_mx["fred"].get(sid), how)
        v, p, dt_ = mx_last(s)
        ch = None if (v is None or p is None) else v - p
        col = _sgn_col(ch, pos_good)
        cal = _cal_last(sid)
        cal_html = ""
        if cal is not None:
            z = cal["zs"]
            zc = _ta["muted"] if z is None or abs(z) < 0.3 else (_ta["win"] if z > 0 else _ta["loss"])
            cal_html = (f"<div style='margin-top:6px;font-size:11px;color:{_ta['muted']};line-height:1.5'>"
                        f"Publié <b style='color:{_ta['text']}'>{_html.escape(str(cal['actual']))}</b> · consensus "
                        f"<b style='color:{_ta['text']}'>{_html.escape(str(cal['forecast']) or '—')}</b> · préc. "
                        f"{_html.escape(str(cal['previous']) or '—')}<br>"
                        + (_chip(f"Surprise {z:+.1f} σ", zc) if z is not None else "") + "</div>")
        st.markdown(
            f"<div style='background:{_ta['card']};border:1px solid {_ta['border']};border-radius:{shape};"
            f"padding:10px 14px;margin-bottom:10px;min-height:118px'>"
            f"<div style='display:flex;justify-content:space-between;gap:6px'>"
            f"<span style='font-size:11.5px;font-weight:700;color:{_ta['text']}'>{label or lab_}</span>"
            f"<span style='font-size:10px;color:{_ta['muted']}'>{'' if dt_ is None else dt_.strftime('%m/%Y')}</span></div>"
            f"<div style='display:flex;align-items:flex-end;justify-content:space-between'>"
            f"<div><span style='font-size:22px;font-weight:800;color:{_ta['text']};font-family:JetBrains Mono,monospace'>{_nfr(v, d)}</span>"
            f"<span style='font-size:11px;color:{_ta['muted']}'> {unit}</span>"
            f"<div style='font-size:11px;color:{col};font-weight:700'>préc. {_nfr(p, d)} "
            f"{'' if ch is None else ('▲' if ch > 0 else '▼' if ch < 0 else '=')}</div></div>"
            f"{_spark(s, _ta['accent'])}</div>{cal_html}</div>", unsafe_allow_html=True)

    def _releases_table(cats, title):
        if _ev_all is None or _ev_all.empty:
            st.caption("Calendrier indisponible.")
            return
        d = _ev_all[_ev_all["cat"].isin(cats) & _ev_all["has_actual"]].sort_values("dt", ascending=False).head(18)
        if d.empty:
            st.caption("Aucune publication récente dans le calendrier.")
            return
        rows = ""
        for _, r in d.iterrows():
            z = r["zs"]
            zc = _ta["muted"] if z is None or abs(z) < 0.3 else (_ta["win"] if z > 0 else _ta["loss"])
            rows += (f"<tr><td style='white-space:nowrap;color:var(--tj-muted)'>{_fmt_local(r['date'])[0]}</td>"
                     f"<td><b>{r['country']}</b></td><td>{_html.escape(str(r['title']))}</td>"
                     f"<td style='font-family:monospace;font-weight:800'>{_html.escape(str(r['actual']))}</td>"
                     f"<td style='font-family:monospace'>{_html.escape(str(r['forecast']) or '—')}</td>"
                     f"<td style='font-family:monospace;color:var(--tj-muted)'>{_html.escape(str(r['previous']) or '—')}</td>"
                     f"<td>{_chip(f'{z:+.1f} σ', zc) if z is not None else '—'}</td></tr>")
        _card_t(title)
        st.markdown(f"<div style='overflow-x:auto'><table class='tj-table'><thead><tr><th>Date</th><th>Devise</th>"
                    f"<th>Indicateur</th><th>Actuel</th><th>Consensus</th><th>Précédent</th><th>Surprise</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)

    def _card_t(title, sub=""):
        st.markdown(f"<div style='margin:6px 0 8px'><span style='font-size:13.5px;font-weight:700;color:{_ta['text']};"
                    f"background:{_ta['accent']}14;border-left:3px solid {_ta['accent']};border-radius:3px 999px 999px 3px;"
                    f"padding:3px 14px 3px 10px'>{title}</span>"
                    + (f" <span style='font-size:11px;color:{_ta['muted']}'>{sub}</span>" if sub else "") + "</div>",
                    unsafe_allow_html=True)

    # ── ONGLET 1 : SYNTHÈSE & BIAIS ───────────────────────────────────────────
    with tab_syn:
        _comp = {}
        for c in MX_CCYS:
            st_sc = _stance.get(c, (None,))[0]
            su = _surp.get(c, (None, 0))[0]
            fs = None
            if not _strength.empty and "1 mois" in _strength.columns and _strength.loc[c, "1 mois"] is not None \
                    and not pd.isna(_strength.loc[c, "1 mois"]):
                fs = float(np.tanh(_strength.loc[c, "1 mois"] / 1.5) * 100)
            parts = [(x, w) for x, w in ((st_sc, 0.45), (su, 0.30), (fs, 0.25)) if x is not None]
            _comp[c] = (sum(x * w for x, w in parts) / sum(w for _, w in parts)) if parts else None

        s1, s2 = st.columns([1.05, 1], gap="medium")
        with s1:
            _card_t("Biais par devise", "politique monétaire · surprises · force de marché")
            rows = ""
            for c in sorted(MX_CCYS, key=lambda x: -(_comp[x] if _comp[x] is not None else -999)):
                p = _pol[c]; sc, lab, det = _stance.get(c, (None, "Indisponible", ""))
                lc = {"Hawkish": _ta["win"], "Dovish": _ta["loss"]}.get(lab, _ta["muted"])
                su = _surp[c][0]; cp = _comp[c]
                cc = _ta["muted"] if cp is None else (_ta["win"] if cp >= 15 else (_ta["loss"] if cp <= -15 else _ta["orange"]))
                rows += (f"<tr><td><b>{c}</b> <span style='color:var(--tj-muted);font-size:11px'>{p['cb']}</span></td>"
                         f"<td style='font-family:monospace'>{_nfr(p['rate'], 2, ' %')}</td>"
                         f"<td title='{_html.escape(det)}'>{_chip(lab + ('' if sc is None else f' {sc:+.0f}'), lc)}</td>"
                         f"<td style='font-family:monospace;color:{_sgn_col(su)}'>{'—' if su is None else f'{su:+.0f}'}</td>"
                         f"<td><div style='display:flex;align-items:center;gap:6px'><div style='width:70px;height:6px;"
                         f"border-radius:999px;background:{_ta['border']};position:relative'><div style='position:absolute;"
                         f"left:{50 if cp is None else (cp + 100) / 2:.0f}%;top:-3px;width:4px;height:12px;border-radius:2px;"
                         f"background:{cc}'></div></div><b style='color:{cc};font-family:monospace'>"
                         f"{'—' if cp is None else f'{cp:+.0f}'}</b></div></td></tr>")
            st.markdown(f"<table class='tj-table'><thead><tr><th>Devise</th><th>Taux</th><th>Politique</th>"
                        f"<th>Surprise 30 j</th><th>Biais global</th></tr></thead><tbody>{rows}</tbody></table>",
                        unsafe_allow_html=True)
            _rk = [c for c in MX_CCYS if _comp[c] is not None]
            if len(_rk) >= 2:
                hi = max(_rk, key=lambda c: _comp[c]); lo = min(_rk, key=lambda c: _comp[c])
                if _comp[hi] - _comp[lo] >= 25:
                    st.markdown(
                        f"<div style='margin-top:8px;padding:8px 14px;border-radius:16px 16px 16px 4px;"
                        f"background:{_ta['accent']}12;border:1px solid {_ta['accent']}44;font-size:12.5px;color:{_ta['text']}'>"
                        f"Divergence la plus marquée : <b>{hi}</b> ({_comp[hi]:+.0f}) contre <b>{lo}</b> ({_comp[lo]:+.0f}). "
                        f"Les fondamentaux favorisent <b>{hi}/{lo}</b> à la hausse, à confirmer par la technique.</div>",
                        unsafe_allow_html=True)
        with s2:
            _card_t("Force des devises", "performance relative au panier, en %")
            if _strength.empty:
                st.caption("Cours de change indisponibles.")
            else:
                z = _strength.astype(float)
                zmax = float(np.nanmax(np.abs(z.values))) or 1.0
                fig = go.Figure(go.Heatmap(
                    z=z.values, x=list(z.columns), y=list(z.index), zmin=-zmax, zmax=zmax,
                    colorscale=[[0, _ta["loss"]], [0.5, _ta["card"]], [1, _ta["win"]]], showscale=False,
                    text=[[("" if pd.isna(v) else f"{v:+.2f}") for v in row] for row in z.values],
                    texttemplate="%{text}", textfont=dict(size=12, color=_ta["text"]),
                    hovertemplate="%{y} · %{x} : %{z:+.2f} %<extra></extra>", xgap=3, ygap=3))
                fig.update_layout(**chart_layout(_ta, _cs_m, height=300, margin=dict(l=44, r=10, t=10, b=30)))
                fig.update_yaxes(autorange="reversed", tickfont=dict(color=_ta["text"]), ticks="", showgrid=False, zeroline=False)
                fig.update_xaxes(side="top", tickfont=dict(color=_ta["muted"]), ticks="", showgrid=False, zeroline=False)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="mx_heat")

        r1, r2 = st.columns([1, 1.05], gap="medium")
        with r1:
            _card_t("Régime Risk-On / Risk-Off", "composantes, en écarts-types")
            if not _reg_comps:
                st.caption("Données de marché indisponibles.")
            else:
                fig = go.Figure(go.Bar(
                    y=[c[0] for c in _reg_comps], x=[c[1] for c in _reg_comps], orientation="h",
                    marker_color=[_ta["win"] if c[1] >= 0 else _ta["loss"] for c in _reg_comps],
                    text=[f"{c[1]:+.1f} σ" for c in _reg_comps], textposition="outside",
                    customdata=[c[2] for c in _reg_comps],
                    hovertemplate="%{y} (%{customdata}) : %{x:+.2f} σ<extra></extra>"))
                fig.update_layout(**chart_layout(_ta, _cs_m, height=230, margin=dict(l=150, r=30, t=10, b=24)))
                fig.update_xaxes(range=[-3.4, 3.4], zeroline=True, zerolinecolor=_ta["muted"], gridcolor=_ta["border"])
                fig.update_yaxes(tickfont=dict(color=_ta["text"]))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="mx_regime")
                st.caption("Vert = pousse vers le Risk-On. Le dollar et le VIX sont inversés : leur hausse traduit une "
                           "recherche de refuge.")
        with r2:
            _card_t("Prochaines annonces à fort impact", "72 h · volatilité attendue")
            if _ev3w.empty:
                st.caption("Calendrier indisponible.")
            else:
                now = datetime.utcnow()
                up = _ev3w[(_ev3w["dt"] >= now - timedelta(minutes=15)) & (_ev3w["dt"] <= now + timedelta(hours=72))
                           & _ev3w["impact"].isin(["High", "Medium"]) & _ev3w["country"].isin(MX_CCYS)].sort_values("dt").head(9)
                if up.empty:
                    st.caption("Aucune annonce Fort / Moyen dans les 72 prochaines heures.")
                for _, r in up.iterrows():
                    vv, vl = mx_expected_vol(r, _reg_sc, _ev_all)
                    vc = {"Forte": _ta["loss"], "Moyenne": _ta["orange"]}.get(vl, _ta["muted"])
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:10px;padding:6px 12px;margin-bottom:6px;"
                        f"background:{_ta['card']};border:1px solid {_ta['border']};border-left:3px solid {vc};"
                        f"border-radius:4px 18px 18px 4px'>"
                        f"<span style='font-family:JetBrains Mono,monospace;font-size:11.5px;color:{_ta['muted']};min-width:98px'>"
                        f"{_fmt_local(r['date'])[0]}</span><b style='font-size:12px'>{r['country']}</b>"
                        f"<span style='font-size:12.5px;color:{_ta['text']};flex:1'>{_html.escape(str(r['title']))}</span>"
                        f"<span style='font-size:11px;color:{_ta['muted']}'>cons. {_html.escape(str(r['forecast']) or '—')}</span>"
                        f"{_chip('Vol. ' + vl.lower(), vc)}</div>", unsafe_allow_html=True)

    # ── ONGLET 2 : CALENDRIER & SURPRISES (fil existant) ──────────────────────
    with tab_cal:
        _card_t("Indice de surprise par devise", "30 derniers jours, -100 à +100")
        _sv = [(c, _surp[c][0], _surp[c][1]) for c in MX_CCYS if _surp[c][0] is not None]
        if _sv:
            fig = go.Figure(go.Bar(x=[c for c, _, _ in _sv], y=[v for _, v, _ in _sv],
                                   marker_color=[_ta["win"] if v >= 0 else _ta["loss"] for _, v, _ in _sv],
                                   text=[f"{v:+.0f}" for _, v, _ in _sv], textposition="outside",
                                   customdata=[n for _, _, n in _sv],
                                   hovertemplate="%{x} : %{y:+.0f} (%{customdata} publications)<extra></extra>"))
            fig.update_layout(**chart_layout(_ta, _cs_m, height=200, margin=dict(l=40, r=10, t=14, b=26)))
            fig.update_yaxes(range=[-110, 110], gridcolor=_ta["border"], zeroline=True, zerolinecolor=_ta["muted"])
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="mx_surp")
        else:
            st.caption("Pas encore de publications avec consensus sur 30 jours.")
        _news_fragment()

    # ── ONGLET 3 : POLITIQUE MONÉTAIRE ────────────────────────────────────────
    with tab_mon:
        m1, m2 = st.columns([1.25, 1], gap="medium")
        with m1:
            _card_t("Taux directeurs", "niveau, dernière décision, prochaine réunion")
            rows = ""
            for c in MX_CCYS:
                p = _pol[c]; sc, lab, det = _stance.get(c, (None, "Indisponible", ""))
                lc = {"Hawkish": _ta["win"], "Dovish": _ta["loss"]}.get(lab, _ta["muted"])
                lm = p["last_move"]
                lm_t = "—" if lm is None else (f"{lm*100:+.0f} pb" + (f" ({pd.Timestamp(p['last_date']).strftime('%d/%m/%y')})"
                                                                       if p["last_date"] is not None else ""))
                c6 = "—" if p["chg6m"] is None else f"{p['chg6m'] * 100:+.0f} pb"
                nx = "—" if p["next_date"] is None else pd.Timestamp(p["next_date"]).strftime("%d/%m")
                exp_ = "" if (p["next_cons"] is None or p["rate"] is None) else f" · cons. {_nfr(p['next_cons'], 2, ' %')}"
                rows += (f"<tr><td><b>{p['cb']}</b> <span style='color:var(--tj-muted);font-size:11px'>{c}</span></td>"
                         f"<td style='font-family:monospace;font-weight:800'>{_nfr(p['rate'], 2, ' %')}</td>"
                         f"<td style='font-family:monospace;color:{_sgn_col(lm)}'>{lm_t}</td>"
                         f"<td style='font-family:monospace;color:{_sgn_col(p['chg6m'])}'>"
                         f"{c6}</td>"
                         f"<td style='font-size:12px'>{nx}{exp_}</td>"
                         f"<td title='{_html.escape(det)}'>{_chip(lab, lc)}</td>"
                         f"<td style='font-size:10.5px;color:var(--tj-muted)'>{p['src'] or '—'}</td></tr>")
            st.markdown(f"<div style='overflow-x:auto'><table class='tj-table'><thead><tr><th>Banque</th><th>Taux</th>"
                        f"<th>Dernier mouvement</th><th>6 mois</th><th>Prochaine réunion</th><th>Orientation</th>"
                        f"<th>Source</th></tr></thead><tbody>{rows}</tbody></table></div>", unsafe_allow_html=True)
        with m2:
            _card_t("Anticipations sur la Fed")
            fb = _fed.get("bp"); sp = _fed.get("spread2y")
            st.markdown(
                "<div style='display:flex;gap:10px;flex-wrap:wrap'>"
                f"<div style='flex:1;min-width:150px;background:{_ta['card']};border:1px solid {_ta['border']};border-radius:44px 12px 12px 44px;padding:10px 16px'>"
                f"<div style='font-size:10px;text-transform:uppercase;letter-spacing:1px;color:{_ta['muted']};font-weight:700'>Fed funds futures</div>"
                f"<div style='font-size:20px;font-weight:800;color:{_sgn_col(fb)};font-family:JetBrains Mono,monospace'>{'—' if fb is None else f'{fb:+.0f} pb'}</div>"
                f"<div style='font-size:11px;color:{_ta['muted']}'>taux implicite {_nfr(_fed.get('implied'), 2, ' %')} vs effectif {_nfr(_fed.get('effr'), 2, ' %')}</div></div>"
                f"<div style='flex:1;min-width:150px;background:{_ta['card']};border:1px solid {_ta['border']};border-radius:12px 44px 44px 12px;padding:10px 16px'>"
                f"<div style='font-size:10px;text-transform:uppercase;letter-spacing:1px;color:{_ta['muted']};font-weight:700'>US 2 ans - Fed</div>"
                f"<div style='font-size:20px;font-weight:800;color:{_sgn_col(sp)};font-family:JetBrains Mono,monospace'>{'—' if sp is None else f'{sp:+.0f} pb'}</div>"
                f"<div style='font-size:11px;color:{_ta['muted']}'>positif : hausses anticipées · négatif : baisses</div></div></div>",
                unsafe_allow_html=True)
            st.caption("Le contrat Fed funds le plus proche indique le taux moyen attendu sur son mois d'échéance. "
                       "Pour la courbe complète des anticipations (FedWatch, swaps €STR / SONIA), voir la méthode.")
        _hz_picker("hz_mon")
        g1, g2 = st.columns(2, gap="medium")
        with g1:
            _card_t("Taux directeurs")
            pal = [_ta["accent"], _ta["alt"], _ta["orange"], _ta["win"], _ta["loss"], _ta["muted"], "#8ab4f8", "#c58af9"]
            _ts_chart([(f"{_pol[c]['cb']}", _pol[c]["series"], pal[i % len(pal)]) for i, c in enumerate(MX_CCYS)
                       if _pol[c]["series"] is not None], "hz_mon", unit="%")
        with g2:
            _card_t("Bilans des banques centrales", "Fed et BCE, milliers de milliards")
            fw = _mx["fred"].get("WALCL"); ew = _mx["fred"].get("ECBASSETSW")
            _ts_chart([("Fed (T$)", fw / 1e6 if fw is not None else None, _ta["accent"]),
                       ("BCE (T€)", ew / 1e6 if ew is not None else None, _ta["alt"])], "hz_mon")

    # ── ONGLET 4 : INFLATION & EMPLOI ─────────────────────────────────────────
    with tab_inf:
        _card_t("États-Unis", "dernière valeur · précédente · publication vs consensus")
        ic = st.columns(4)
        for i, (sid, pg) in enumerate([("CPIAUCSL", False), ("CPILFESL", False), ("PCEPILFE", False), ("CES0500000003", False)]):
            with ic[i]:
                _ind_card(sid, pos_good=pg, d=1, shape=["22px 6px 22px 6px", "44px 12px 12px 44px", "3px 20px 3px 20px", "12px 44px 44px 12px"][i])
        ic = st.columns(4)
        for i, (sid, pg, dd) in enumerate([("PAYEMS", True, 0), ("UNRATE", False, 1), ("ICSA", False, 0), ("T5YIE", False, 2)]):
            with ic[i]:
                _ind_card(sid, pos_good=pg, d=dd, shape=["12px 44px 44px 12px", "22px 6px 22px 6px", "44px 12px 12px 44px", "3px 20px 3px 20px"][i])
        _hz_picker("hz_inf")
        g1, g2 = st.columns(2, gap="medium")
        with g1:
            _card_t("Inflation US", "% sur un an · cible Fed 2 %")
            _ts_chart([("CPI", mx_transform(_mx["fred"].get("CPIAUCSL"), "yoy"), _ta["loss"]),
                       ("Core CPI", mx_transform(_mx["fred"].get("CPILFESL"), "yoy"), _ta["orange"]),
                       ("Core PCE", mx_transform(_mx["fred"].get("PCEPILFE"), "yoy"), _ta["accent"])], "hz_inf", ref=2.0, unit="%")
        with g2:
            _card_t("Marché du travail US", "chômage % · salaires % a/a")
            _ts_chart([("Chômage", _mx["fred"].get("UNRATE"), _ta["alt"]),
                       ("Salaires a/a", mx_transform(_mx["fred"].get("CES0500000003"), "yoy"), _ta["win"])], "hz_inf", unit="%")
        _releases_table(["Inflation", "Emploi"], "Dernières publications, toutes devises")

    # ── ONGLET 5 : CROISSANCE ─────────────────────────────────────────────────
    with tab_gro:
        _card_t("États-Unis", "activité et confiance")
        gc = st.columns(4)
        for i, (sid, dd) in enumerate([("A191RL1Q225SBEA", 1), ("RSAFS", 1), ("INDPRO", 1), ("UMCSENT", 1)]):
            with gc[i]:
                _ind_card(sid, d=dd, shape=["44px 12px 12px 44px", "22px 6px 22px 6px", "3px 20px 3px 20px", "12px 44px 44px 12px"][i])
        _hz_picker("hz_gro")
        g1, g2 = st.columns(2, gap="medium")
        with g1:
            _card_t("PIB US", "croissance trimestrielle annualisée, %")
            gdp = _mx["fred"].get("A191RL1Q225SBEA")
            if gdp is not None and len(gdp):
                gs = _hz_series(gdp, "hz_gro")
                fig = go.Figure(go.Bar(x=gs.index, y=gs.values, marker_color=[_ta["win"] if v >= 0 else _ta["loss"] for v in gs.values],
                                       hovertemplate="%{x|%m/%Y} : %{y:.1f} %<extra></extra>"))
                fig.update_layout(**chart_layout(_ta, _cs_m, height=250, margin=dict(l=40, r=10, t=14, b=30)))
                chart_axes(fig, _ta, _cs_m)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key="mx_gdp")
            else:
                st.caption("Série indisponible pour le moment.")
        with g2:
            _card_t("Consommation et industrie", "% sur un an")
            _ts_chart([("Ventes au détail a/a", mx_transform(_mx["fred"].get("RSAFS"), "yoy"), _ta["accent"]),
                       ("Production industrielle a/a", mx_transform(_mx["fred"].get("INDPRO"), "yoy"), _ta["orange"])], "hz_gro", ref=0, unit="%")
        _releases_table(["Croissance"], "PMI, ISM, ZEW, IFO, ventes, confiance : dernières publications")

    # ── ONGLET 6 : LIQUIDITÉ & SENTIMENT ──────────────────────────────────────
    with tab_liq:
        lc = st.columns(4)
        tiles = [("Courbe 10 ans - 3 mois", _mx["fred"].get("T10Y3M"), "pb", 0, True, "bp"),
                 ("Spread High Yield", _hy, "pb", 0, False, "bp"),
                 ("Masse monétaire M2", _mx["fred"].get("M2SL"), "% a/a", 1, True, "yoy"),
                 ("Conditions financières", _mx["fred"].get("NFCI"), "", 2, False, "lvl")]
        shapes = ["22px 6px 22px 6px", "44px 12px 12px 44px", "3px 20px 3px 20px", "12px 44px 44px 12px"]
        for i, (lab, s, u, dd, pg, how) in enumerate(tiles):
            with lc[i]:
                st.markdown("<div style='display:flex'>" + _tile(lab, s, u, dd, pg, how=how, shape=shapes[i]) + "</div>",
                            unsafe_allow_html=True)
        _hz_picker("hz_liq")
        g1, g2 = st.columns(2, gap="medium")
        with g1:
            _card_t("Courbe des taux US", "points de base · négatif = courbe inversée")
            _ts_chart([("10 ans - 2 ans", mx_transform(_mx["fred"].get("T10Y2Y"), "bp"), _ta["accent"]),
                       ("10 ans - 3 mois", mx_transform(_mx["fred"].get("T10Y3M"), "bp"), _ta["orange"])], "hz_liq", ref=0, unit="pb")
        with g2:
            _card_t("Spreads de crédit", "points de base")
            _ts_chart([("High Yield", mx_transform(_hy, "bp") if _hy is not None else None, _ta["loss"]),
                       ("Investment Grade", mx_transform(_ig, "bp") if _ig is not None else None, _ta["accent"]),
                       ("HY - IG", mx_transform(_hyig, "bp") if _hyig is not None else None, _ta["orange"])], "hz_liq", unit="pb")
        g3, g4 = st.columns(2, gap="medium")
        with g3:
            _card_t("Dollar et volatilité", "DXY · VIX")
            _ts_chart([("DXY", _dxy, _ta["accent"]), ("VIX", _vix, _ta["loss"])], "hz_liq")
        with g4:
            _card_t("Liquidité", "M2 % a/a · bilan Fed en T$")
            fw = _mx["fred"].get("WALCL")
            _ts_chart([("M2 a/a", mx_transform(_mx["fred"].get("M2SL"), "yoy"), _ta["win"]),
                       ("Bilan Fed", fw / 1e6 if fw is not None else None, _ta["alt"])], "hz_liq")

    # ── ONGLET 7 : MÉTHODE & SOURCES ──────────────────────────────────────────
    with tab_met:
        _st_ts = [v for v in _mx_store()["ts"].values()]
        _m1, _m2 = st.columns([4, 1.3], vertical_alignment="center")
        with _m1:
            st.caption("Dernier chargement des données macro : " + (
                datetime.fromtimestamp(max(_st_ts)).strftime("%d/%m %H:%M") if _st_ts else "en cours")
                + " · FRED toutes les 6 h, cours toutes les 30 min, taux directeurs toutes les 12 h.")
        with _m2:
            if st.button("Recharger les données", icon=":material/refresh:", key="mx_force", use_container_width=True):
                macro_get(force=True); st.rerun()
        st.markdown(MX_METHOD_MD)


elif st.session_state.page == "calendar":
    st.markdown("# Calendrier de Performance")
    mode_banner()

    df_cal = get_df()

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
                html += f'<th style="color:var(--tj-muted);font-size:11px;font-weight:700;padding:6px;text-transform:uppercase;letter-spacing:.5px">{d}</th>'
            html += '<th style="color:var(--tj-muted);font-size:11px;font-weight:700;padding:6px;text-transform:uppercase;letter-spacing:.5px">Semaine</th>'
            html += '</tr></thead><tbody>'

            today_iso = date.today().isoformat()

            for week in weeks:
                week_pnl, week_trades, week_active = 0, 0, 0
                row = "<tr>"
                for day in week:
                    if day == 0:
                        row += '<td style="background:var(--tj-bg);border-radius:10px;height:78px"></td>'
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
                            <div style="font-size:10px;color:var(--tj-muted)">{day}</div>
                            <div style="font-size:13px;font-weight:800;color:{text_col};
                                font-family:'JetBrains Mono',monospace;margin-top:6px">{fmt(pnl_v)}</div>
                            <div style="font-size:9px;color:var(--tj-muted);margin-top:3px">
                                {trades_v} trade{"s" if trades_v>1 else ""}</div>
                        </td>'''
                    else:
                        row += f'''<td style="background:var(--tj-card);border-radius:10px;height:78px;
                            padding:8px;vertical-align:top;border:{border_today}">
                            <div style="font-size:10px;color:#3d4760">{day}</div>
                        </td>'''
                # Cellule total semaine
                if week_active > 0:
                    wcol = "#00d4aa" if week_pnl >= 0 else "#ff4d6d"
                    wbg  = "rgba(0,212,170,0.10)" if week_pnl >= 0 else "rgba(255,77,109,0.10)"
                    wpnl_txt = fmt(week_pnl)
                else:
                    wcol = "#3d4760"; wbg = "var(--tj-bg2)"; wpnl_txt = "—"
                row += f'''<td style="background:{wbg};border-radius:10px;height:78px;
                    padding:8px;vertical-align:top;border:1px solid {wcol}33">
                    <div style="font-size:9px;color:var(--tj-muted);text-transform:uppercase">Total</div>
                    <div style="font-size:13px;font-weight:800;color:{wcol};
                        font-family:'JetBrains Mono',monospace;margin-top:6px">{wpnl_txt}</div>
                    <div style="font-size:9px;color:var(--tj-muted);margin-top:3px">
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
                        f"<div style='padding-top:8px;color:var(--tj-muted)'>"
                        f"{_jn} {zoom_day:02d} {mois_fr[month-1]} {year} — "
                        f"<i>aucun trade</i></div>", unsafe_allow_html=True)
                else:
                    zpnl = df_zoom_day["pnl"].sum()
                    ztrades = len(df_zoom_day)
                    zcol = "#00d4aa" if zpnl >= 0 else "#ff4d6d"
                    st.markdown(
                        f"<div style='padding-top:8px'>"
                        f"<span style='color:var(--tj-muted)'>{_jn} {zoom_day:02d} · P&L : </span>"
                        f"<b style='color:{zcol};font-family:JetBrains Mono,monospace'>{fmt(zpnl)}</b>"
                        f"<span style='color:var(--tj-muted)'> · {ztrades} position"
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

                        _zt = get_theme(); _zcs = get_chart_style()
                        fig_hr = category_figure(
                            [f"{int(h):02d}h" for h in hour_agg.index], hour_agg["pnl"].tolist(),
                            [_zt["win"] if v>=0 else _zt["loss"] for v in hour_agg["pnl"]],
                            _zt, _zcs, kind=("lollipop" if _zcs["monthly"]=="lollipop" else "bar"),
                            orientation="v", customdata=hour_agg["trades"].tolist(),
                            hovertemplate="<b>%{x}</b><br>P&L : %{y:+,.2f}$<br>"
                                          "%{customdata} position(s)<extra></extra>")
                        fig_hr.add_hline(y=0, line_color=_zt["border"], line_width=1)
                        fig_hr.update_layout(**chart_layout(_zt, _zcs, height=260,
                                             margin=dict(l=50,r=20,t=10,b=30)))
                        chart_axes(fig_hr, _zt, _zcs, yprefix="$", free_y=True)
                        _zcfg = chart_config(_zcs); _zcfg.update(scrollZoom=True, displayModeBar=True)
                        st.plotly_chart(fig_hr, use_container_width=True, config=_zcfg)

                        # Courbe de P&L cumulé intra-journalier
                        _dz_sorted = _dz_f.sort_values("_dtz")
                        _cum = _dz_sorted["pnl"].cumsum()
                        _cum_cs = dict(_zcs); _cum_cs["markers"] = True
                        if _cum_cs["equity"] != "glow":
                            _cum_cs["equity"] = "step"
                        fig_cum = go.Figure(series_traces(
                            _dz_sorted["_dtz"].dt.strftime("%H:%M").tolist(), _cum.tolist(),
                            _zt["alt"], _cum_cs,
                            customdata=list(zip(_dz_sorted["symbol"], _dz_sorted["pnl"])),
                            hovertemplate="<b>%{x}</b><br>%{customdata[0]}<br>"
                                          "Trade : %{customdata[1]:+,.2f}$<br>"
                                          "Cumulé : %{y:+,.2f}$<extra></extra>"))
                        fig_cum.data[-1].marker.color = [_zt["win"] if p>0 else _zt["loss"]
                                                         for p in _dz_sorted["pnl"]]
                        fig_cum.data[-1].marker.size = 7
                        fig_cum.add_hline(y=0, line_color=_zt["border"], line_width=1)
                        fig_cum.update_layout(**chart_layout(_zt, _zcs, height=220,
                            margin=dict(l=50,r=20,t=24,b=30),
                            title=dict(text="P&L cumulé au fil de la journée",
                                       font=dict(size=12, color=_zt["muted"]), x=0.01)))
                        chart_axes(fig_cum, _zt, _zcs, yprefix="$")
                        st.plotly_chart(fig_cum, use_container_width=True, config=chart_config(_zcs))

                        # Liste détaillée des positions
                        st.markdown("##### Positions prises ce jour")
                        for _, zt in _dz_sorted.iterrows():
                            zh = zt["_dtz"].strftime("%H:%M") if pd.notna(zt["_dtz"]) else "—"
                            zc = "#00d4aa" if zt["pnl"]>=0 else "#ff4d6d"
                            st.markdown(
                                f"<div style='display:flex;gap:14px;align-items:center;"
                                f"background:var(--tj-card);border:1px solid var(--tj-border);border-radius:8px;"
                                f"padding:7px 14px;margin-bottom:5px;font-size:13px'>"
                                f"<span style='color:var(--tj-muted);font-family:JetBrains Mono,monospace;"
                                f"min-width:42px'>{zh}</span>"
                                f"<span style='color:#e8ecf4;font-weight:600'>{zt['symbol']}</span>"
                                f"<span style='color:var(--tj-muted)'>{zt['direction']}</span>"
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
                    bg = "var(--tj-card)"; text_col = "#3d4760"; pnl_txt = "—"; trades_v = 0
                html += f'''<div title="Semaine {w}, {trades_v} trades" style="background:{bg};
                    border-radius:9px;padding:10px 4px;text-align:center;
                    border:1px solid rgba(255,255,255,0.04)">
                    <div style="font-size:9px;color:var(--tj-muted)">S{w}</div>
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
                    bg = "var(--tj-card)"; text_col = "#3d4760"; border_col = "rgba(255,255,255,0.04)"
                    pnl_txt = "—"; trades_v = 0
                html += f'''<div style="background:{bg};border-radius:14px;padding:18px;
                    border:1px solid {border_col}">
                    <div style="font-size:12px;color:var(--tj-muted);text-transform:uppercase;
                        letter-spacing:.5px">{mois_fr[m-1]} {year}</div>
                    <div style="font-size:22px;font-weight:800;color:{text_col};
                        font-family:'JetBrains Mono',monospace;margin-top:8px">{pnl_txt}</div>
                    <div style="font-size:11px;color:var(--tj-muted);margin-top:6px">
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
                    <div style="font-size:13px;color:var(--tj-muted)">{int(r["_year"])}</div>
                    <div style="font-size:24px;font-weight:800;color:{text_col};
                        font-family:'JetBrains Mono',monospace;margin-top:8px">{fmt(r["pnl"])}</div>
                    <div style="font-size:11px;color:var(--tj-muted);margin-top:6px">
                        {int(r["trades"])} trade{"s" if r["trades"]!=1 else ""}</div>
                </div>'''
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        # ── Légende couleur ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            '<div style="display:flex;gap:24px;align-items:center;font-size:12px;color:var(--tj-muted)">'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            'background:rgba(0,212,170,0.65);margin-right:6px;vertical-align:middle"></span>Gain</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            'background:rgba(255,77,109,0.65);margin-right:6px;vertical-align:middle"></span>Perte</span>'
            '<span><span style="display:inline-block;width:12px;height:12px;border-radius:3px;'
            'background:var(--tj-card);margin-right:6px;vertical-align:middle;border:1px solid var(--tj-border)"></span>'
            'Aucun trade</span>'
            '<span style="color:var(--tj-muted)">L\'intensité de la couleur reflète l\'ampleur du P&L</span>'
            '</div>', unsafe_allow_html=True
        )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : UTILISATEURS (ADMIN) — comptes, permissions, capital de départ
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "users":
    if not is_admin():
        st.error("Accès réservé à l'administrateur."); st.stop()
    _t = get_theme()
    st.markdown("# Utilisateurs & comptes")
    st.caption("Créez les accès, choisissez les comptes visibles par utilisateur, "
               "et définissez le capital de départ de chaque compte.")

    users = users_load()

    # ── GESTION DES COMPTES DE TRADING ───────────────────────────────────────
    st.markdown("### Comptes de trading")
    st.caption("Créez ou supprimez des comptes (ex. retirer Démo, ajouter un réel).")
    accs = list(st.session_state.get("accounts_meta", []))
    # Liste + suppression
    for _i, a in enumerate(accs):
        nm = a["name"]; kd = a.get("kind", "real")
        col = account_color(nm)
        n_tr = sum(1 for t in st.session_state.trades if t.get("trade_mode") == nm)
        ac1, ac2, ac3 = st.columns([3, 1.4, 1.4])
        with ac1:
            st.markdown(
                f"<div style='padding-top:8px'>"
                f"<span style='display:inline-block;width:10px;height:10px;border-radius:3px;"
                f"background:{col};margin-right:8px'></span>"
                f"<b style='color:{_t['text']}'>{nm}</b> "
                f"<span style='color:{_t['muted']};font-size:12px'>· {'démo' if kd=='demo' else 'réel'} "
                f"· {n_tr} trade(s)</span></div>", unsafe_allow_html=True)
        with ac2:
            st.markdown(f"<div style='color:{_t['muted']};font-size:12px;padding-top:9px'>"
                        f"capital {float(st.session_state.get('account_capital',{}).get(nm,0) or 0):,.0f}$</div>",
                        unsafe_allow_html=True)
        with ac3:
            if st.button("Supprimer", key=f"delacc_{_i}", use_container_width=True):
                st.session_state[f"confirm_delacc_{_i}"] = True
        if st.session_state.get(f"confirm_delacc_{_i}"):
            warn = (f" {n_tr} trade(s) resteront enregistrés sous ce nom mais ne seront "
                    f"plus filtrables." if n_tr else "")
            st.warning(f"Supprimer le compte « {nm} » ?{warn}")
            d1, d2, _ = st.columns([1, 1, 4])
            with d1:
                if st.button("Oui, supprimer", key=f"cfa_{_i}"):
                    accs.pop(_i)
                    st.session_state.accounts_meta = accs
                    accounts_save(accs); apply_accounts(accs)
                    caps_now = dict(st.session_state.get("account_capital", {}))
                    caps_now.pop(nm, None)
                    st.session_state.account_capital = caps_now; capital_save(caps_now)
                    st.session_state.pop(f"confirm_delacc_{_i}", None); st.rerun()
            with d2:
                if st.button("Annuler", key=f"cfna_{_i}"):
                    st.session_state.pop(f"confirm_delacc_{_i}", None); st.rerun()
    # Ajout
    with st.form("add_account_form"):
        nc1, nc2, nc3 = st.columns([2.4, 1.4, 1.2])
        with nc1:
            na_name = st.text_input("Nom du nouveau compte", placeholder="ex. Réel Prop Firm")
        with nc2:
            na_kind = st.selectbox("Type", ["real", "demo"],
                                   format_func=lambda k: "Réel" if k == "real" else "Démo")
        with nc3:
            na_cap = st.number_input("Capital départ", min_value=0.0, step=100.0, value=0.0)
        if st.form_submit_button("Ajouter le compte", icon=":material/add:", type="primary"):
            nm = na_name.strip()
            if not nm:
                st.error("Nom requis.")
            elif any(a["name"] == nm for a in accs):
                st.error("Ce compte existe déjà.")
            else:
                accs.append({"name": nm, "kind": na_kind})
                st.session_state.accounts_meta = accs
                accounts_save(accs); apply_accounts(accs)
                if na_cap:
                    caps_now = dict(st.session_state.get("account_capital", {}))
                    caps_now[nm] = na_cap
                    st.session_state.account_capital = caps_now; capital_save(caps_now)
                st.success(f"Compte « {nm} » créé.")
                st.rerun()

    st.markdown("---")

    # ── CAPITAL DE DÉPART PAR COMPTE ─────────────────────────────────────────
    st.markdown("### Capital de départ par compte")
    st.caption("Sert de base au calcul de la progression en %.")
    caps = dict(st.session_state.get("account_capital", {}))
    with st.form("capital_form"):
        cap_cols = st.columns(len(TRADE_MODES))
        new_caps = {}
        for _cc, acc in zip(cap_cols, TRADE_MODES):
            with _cc:
                new_caps[acc] = st.number_input(
                    acc, min_value=0.0, step=100.0,
                    value=float(caps.get(acc, 0) or 0), key=f"cap_{acc}")
        if st.form_submit_button("Enregistrer les capitaux", icon=":material/save:",
                                 type="primary"):
            st.session_state.account_capital = new_caps
            ok = capital_save(new_caps)
            st.success("Capitaux enregistrés." if ok else "Enregistré en session (sync à vérifier).")

    st.markdown("---")

    # ── CRÉER UN UTILISATEUR ─────────────────────────────────────────────────
    st.markdown("### Créer un utilisateur")
    with st.form("create_user_form"):
        cu1, cu2 = st.columns(2)
        with cu1:
            nu_name = st.text_input("Nom d'utilisateur")
        with cu2:
            nu_pass = st.text_input("Mot de passe", type="password",
                                    help="À transmettre à l'utilisateur de façon sécurisée")
        nu_accounts = st.multiselect("Comptes visibles par cet utilisateur", TRADE_MODES,
                                     default=[], help="L'utilisateur ne verra QUE ces comptes.")
        cc1, cc2 = st.columns([1, 1])
        with cc1:
            submit_new = st.form_submit_button("Créer le compte", icon=":material/person_add:",
                                               type="primary", use_container_width=True)
        with cc2:
            gen_pw = st.form_submit_button("Suggérer un mot de passe", use_container_width=True)
        if gen_pw:
            st.info(f"Mot de passe suggéré : `{_secrets.token_urlsafe(9)}`")
        if submit_new:
            if not nu_name.strip() or not nu_pass:
                st.error("Nom d'utilisateur et mot de passe requis.")
            elif len(nu_pass) < 6:
                st.error("Mot de passe : 6 caractères minimum.")
            elif any(x.get("username") == nu_name.strip() for x in users):
                st.error("Ce nom d'utilisateur existe déjà.")
            elif not nu_accounts:
                st.error("Sélectionnez au moins un compte visible.")
            else:
                users.append({
                    "username": nu_name.strip(),
                    "password_hash": hash_password(nu_pass),
                    "role": "user",
                    "accounts": nu_accounts,
                    "active": True,
                })
                if users_save(users):
                    st.success(f"Utilisateur « {nu_name.strip()} » créé "
                               f"(accès : {', '.join(nu_accounts)}).")
                    st.rerun()
                else:
                    st.error("Échec de la sauvegarde.")

    st.markdown("---")
    st.markdown("### Utilisateurs existants")
    if not users:
        st.info("Aucun utilisateur.")
    else:
        me = st.session_state.get("auth_user")
        for i, u in enumerate(users):
            uname = u.get("username", "")
            is_adm = u.get("role") == "admin"
            active = u.get("active", True)
            status_col = _t["win"] if active else _t["loss"]
            with st.container():
                st.markdown(
                    f"<div style='background:{_t['card']};border:1px solid {_t['border']};"
                    f"border-radius:12px;padding:12px 16px;margin-bottom:4px'>"
                    f"<b style='color:{_t['text']}'>{uname}</b> "
                    f"{'👑 admin' if is_adm else ''} "
                    f"<span style='color:{status_col};font-size:12px'>"
                    f"● {'actif' if active else 'désactivé'}</span><br>"
                    f"<span style='color:{_t['muted']};font-size:12px'>Comptes : "
                    f"{', '.join(u.get('accounts', [])) if not is_adm else 'tous (admin)'}</span></div>",
                    unsafe_allow_html=True)
                if not is_adm:
                    e1, e2, e3, e4 = st.columns([2.4, 1.4, 1.4, 1.2])
                    with e1:
                        new_acc = st.multiselect("Comptes", TRADE_MODES,
                            default=[a for a in u.get("accounts", []) if a in TRADE_MODES],
                            key=f"acc_{i}", label_visibility="collapsed")
                    with e2:
                        if st.button("Enregistrer accès", key=f"save_acc_{i}",
                                     use_container_width=True):
                            users[i]["accounts"] = new_acc
                            (st.success if users_save(users) else st.error)(
                                "Accès mis à jour." if new_acc else "Aucun compte : l'utilisateur ne verra rien.")
                            st.rerun()
                    with e3:
                        if st.button("Activer" if not active else "Désactiver",
                                     key=f"tog_{i}", use_container_width=True):
                            users[i]["active"] = not active
                            users_save(users); st.rerun()
                    with e4:
                        if st.button("Supprimer", key=f"del_{i}", use_container_width=True):
                            st.session_state[f"confirm_del_{i}"] = True
                    npw = st.text_input("Nouveau mot de passe", key=f"npw_{i}",
                                        label_visibility="collapsed",
                                        placeholder="Réinitialiser le mot de passe…")
                    if npw:
                        if len(npw) < 6:
                            st.warning("6 caractères minimum.")
                        elif st.button("Réinitialiser", key=f"rst_{i}"):
                            users[i]["password_hash"] = hash_password(npw)
                            (st.success if users_save(users) else st.error)("Mot de passe réinitialisé.")
                    if st.session_state.get(f"confirm_del_{i}"):
                        st.error(f"Supprimer définitivement « {uname} » ?")
                        dc1, dc2, _ = st.columns([1, 1, 4])
                        with dc1:
                            if st.button("Oui, supprimer", key=f"cfd_{i}"):
                                users.pop(i); users_save(users)
                                st.session_state.pop(f"confirm_del_{i}", None); st.rerun()
                        with dc2:
                            if st.button("Annuler", key=f"cfn_{i}"):
                                st.session_state.pop(f"confirm_del_{i}", None); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE : CAPTURES — galerie des screenshots de trades, filtrable par date/compte
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# PAGE : SESSIONS DE TRADING (heures en GMT+1)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "sessions":
    _t = get_theme()
    from datetime import timezone as _tz, timedelta as _tdl
    GMT1 = _tz(_tdl(hours=1))

    st.markdown("# Sessions de trading")
    st.caption("Horaires des grandes places financières, ajustés à votre fuseau (GMT+1). "
               "Le Forex est fermé le week-end.")

    # Fuseaux RÉELS de chaque place (le DST été/hiver est géré automatiquement)
    # Heures d'ouverture exprimées en HEURE LOCALE de la place.
    try:
        from zoneinfo import ZoneInfo
    except Exception:
        ZoneInfo = None
    SESSIONS = [
        {"name": "Sydney",   "icon": "fa-earth-oceania", "tz": "Australia/Sydney",  "open": 7, "close": 16, "color": "#f0506e"},
        {"name": "Tokyo",    "icon": "fa-earth-asia",    "tz": "Asia/Tokyo",        "open": 9, "close": 18, "color": "#9d7bff"},
        {"name": "Londres",  "icon": "fa-earth-europe",  "tz": "Europe/London",     "open": 8, "close": 17, "color": "#4f8cff"},
        {"name": "New York", "icon": "fa-earth-americas","tz": "America/New_York",  "open": 8, "close": 17, "color": "#2dd4a7"},
    ]

    now_utc = datetime.now(_tz.utc)

    def _session_window(sess, ref_utc):
        """Fenêtre courante (ou prochaine), calculée dans le vrai fuseau de la place.
        Pas de session le week-end local. Retourne (is_open, open_utc, close_utc)."""
        if ZoneInfo is None:
            return False, None, None
        try:
            tz = ZoneInfo(sess["tz"])
        except Exception:
            return False, None, None
        oh, ch = sess["open"], sess["close"]
        here = ref_utc.astimezone(tz)
        # Fenêtre en cours : hier / aujourd'hui (heure locale)
        for d in (-1, 0):
            ld = (here + _tdl(days=d))
            if ld.weekday() >= 5:            # samedi/dimanche local → pas de session
                continue
            o = ld.replace(hour=oh, minute=0, second=0, microsecond=0)
            cl = o + _tdl(hours=(ch - oh))
            o_utc, c_utc = o.astimezone(_tz.utc), cl.astimezone(_tz.utc)
            if o_utc <= ref_utc < c_utc:
                return True, o_utc, c_utc
        # Sinon : prochaine ouverture (7 jours glissants, jours ouvrés)
        for d in range(0, 8):
            ld = (here + _tdl(days=d))
            if ld.weekday() >= 5:
                continue
            o = ld.replace(hour=oh, minute=0, second=0, microsecond=0)
            cl = o + _tdl(hours=(ch - oh))
            o_utc, c_utc = o.astimezone(_tz.utc), cl.astimezone(_tz.utc)
            if o_utc > ref_utc:
                return False, o_utc, c_utc
        return False, None, None

    def _fmt(dt_utc):
        if dt_utc is None: return "—"
        return dt_utc.astimezone(GMT1).strftime("%a %d/%m · %H:%M")

    # Pré-calcul : statut de chaque session → l'état du marché en découle
    _sess_results = {s["name"]: _session_window(s, now_utc) for s in SESSIONS}
    open_count = sum(1 for v in _sess_results.values() if v[0])
    market_closed = (open_count == 0)

    # Bandeau heure locale + état marché
    _mk_col = _t["loss"] if market_closed else _t["win"]
    st.markdown(
        f"<div style='display:flex;gap:20px;align-items:center;margin-bottom:14px'>"
        f"<span style='font-size:12px;color:{_t['muted']};text-transform:uppercase;"
        f"letter-spacing:1px'>Heure locale (GMT+1)</span>"
        f"<span style='font-size:18px;font-weight:800;color:{_t['text']};"
        f"font-family:JetBrains Mono,monospace'>{now_utc.astimezone(GMT1).strftime('%A %d/%m %H:%M')}</span>"
        f"<span style='background:{_mk_col}22;color:{_mk_col};border:1px solid {_mk_col}55;"
        f"border-radius:20px;padding:3px 12px;font-size:12px;font-weight:700'>"
        f"{'Marché FERMÉ' if market_closed else 'Marché OUVERT'}</span>"
        f"</div>", unsafe_allow_html=True)

    cols = st.columns(len(SESSIONS))
    for _col, sess in zip(cols, SESSIONS):
        is_open, o_utc, c_utc = _sess_results[sess["name"]]
        col = sess["color"]
        status_col = _t["win"] if is_open else _t["muted"]
        status_txt = "OUVERTE" if is_open else "Fermée"
        with _col:
            if is_open:
                body = (f"<div style='font-size:11px;color:{_t['muted']};margin-top:8px'>Ouverture</div>"
                        f"<div style='font-size:13px;font-weight:700;color:{_t['text']};"
                        f"font-family:JetBrains Mono,monospace'>{_fmt(o_utc)}</div>"
                        f"<div style='font-size:11px;color:{_t['muted']};margin-top:4px'>Fermeture</div>"
                        f"<div style='font-size:13px;font-weight:700;color:{_t['text']};"
                        f"font-family:JetBrains Mono,monospace'>{_fmt(c_utc)}</div>")
            else:
                body = (f"<div style='font-size:11px;color:{_t['muted']};margin-top:8px'>Prochaine ouverture</div>"
                        f"<div style='font-size:13px;font-weight:700;color:{_t['muted']};"
                        f"font-family:JetBrains Mono,monospace'>{_fmt(o_utc)}</div>"
                        f"<div style='font-size:11px;color:{_t['muted']};margin-top:4px'>Clôture prévue</div>"
                        f"<div style='font-size:12px;color:{_t['muted']};"
                        f"font-family:JetBrains Mono,monospace'>{_fmt(c_utc)}</div>")
            st.markdown(
                f"<div class='grad-card' style='border-top:3px solid {col}'>"
                f"<div style='display:flex;align-items:center;justify-content:space-between'>"
                f"<span style='font-size:15px;font-weight:800;color:{_t['text']}'>"
                f"<i class='fa-solid {sess['icon']}' style='color:{col};margin-right:6px'></i>{sess['name']}</span>"
                f"<span style='background:{status_col}22;color:{status_col};border:1px solid {status_col}55;"
                f"border-radius:20px;padding:2px 10px;font-size:10px;font-weight:800'>{status_txt}</span>"
                f"</div>"
                f"<div style='font-size:10px;color:{_t['muted']};margin-top:4px'>"
                f"Local : {sess['open']:02d}:00–{sess['close']:02d}:00 ({sess['tz'].split('/')[-1].replace('_',' ')})</div>"
                f"{body}</div>",
                unsafe_allow_html=True)

    st.markdown(" ")
    if market_closed:
        st.info("Marché Forex fermé pour le week-end. Réouverture dimanche soir (session de Sydney).")
    else:
        # Chevauchements notables
        st.markdown(
            f"<div style='color:{_t['muted']};font-size:12px;margin-top:6px'>"
            f"<b style='color:{_t['text']}'>{open_count}</b> session(s) ouverte(s) actuellement. "
            f"Le chevauchement <b style='color:{_t['text']}'>Londres · New York</b> "
            f"(14:00–18:00 GMT+1) concentre la plus forte liquidité.</div>",
            unsafe_allow_html=True)

elif st.session_state.page == "captures":
    _t = get_theme()
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:12px'>"
        f"<span style='font-size:22px;font-weight:800;color:{_t['text']}'>Captures d'écran</span>"
        f"<span style='font-size:12px;color:{_t['muted']}'>images libres ou rattachées aux trades</span></div>",
        unsafe_allow_html=True)
    tab_free, tab_trc = st.tabs(["Captures libres", "Captures des trades"])

    # ══ CAPTURES LIBRES : images seules, datées à l'import, commentables ═══════
    with tab_free:
        _me = st.session_state.get("auth_user", "")
        if "_free_idx" not in st.session_state:
            st.session_state._free_idx = kv_load("free_captures_index", []) or []
        if "_free_grp" not in st.session_state:
            st.session_state._free_grp = kv_load("free_captures_groups", {}) or {}
        _idx = st.session_state._free_idx
        _grp = st.session_state._free_grp
        _gid = lambda c: c.get("group") or f"{c['ts']}|{c.get('owner', '')}"
        # anciens imports : la note commune devient le commentaire du groupe
        for c in _idx:
            if c.get("note") and _gid(c) not in _grp:
                _grp[_gid(c)] = c["note"]
        _vis = [c for c in _idx if is_admin() or c.get("owner") == _me]

        def _save_caps():
            ok1 = kv_save("free_captures_index", st.session_state._free_idx)
            ok2 = kv_save("free_captures_groups", st.session_state._free_grp)
            return ok1 and ok2

        # ── Import : commentaire de groupe + commentaire par image ──
        _nup = st.session_state.get("_free_up_n", 0)
        with st.expander("Importer des images", expanded=not _vis, icon=":material/add_photo_alternate:"):
            _ups = st.file_uploader("Images (PNG, JPG, WEBP)", type=["png", "jpg", "jpeg", "webp"],
                                    accept_multiple_files=True, key=f"free_up_{_nup}", label_visibility="collapsed")
            if _ups:
                _gnote = st.text_area("Commentaire du groupe", key=f"free_gnote_{_nup}", height=70,
                                      placeholder="Commentaire commun à ces images : contexte, marché, idée…")
                if len(_ups) == 1:
                    _per = [st.text_input("Commentaire de l'image", key=f"free_c_{_nup}_0",
                                          placeholder="Facultatif")]
                else:
                    st.caption("Commentaire propre à chaque image (facultatif)")
                    _per = []
                    _pc = st.columns(min(3, len(_ups)))
                    for _i, f in enumerate(_ups):
                        with _pc[_i % len(_pc)]:
                            st.image(f, use_container_width=True)
                            _per.append(st.text_input(f.name[:38], key=f"free_c_{_nup}_{_i}",
                                                      placeholder="Commentaire…"))
                if st.button(f"Importer {len(_ups)} image(s)", type="primary", icon=":material/upload:",
                             key="free_save"):
                    _now = datetime.now()
                    _g = f"{_now.strftime('%Y%m%d%H%M%S')}{_secrets.token_hex(2)}"
                    _added, _ok_all = 0, True
                    for _i, f in enumerate(_ups):
                        try:
                            _cid = f"{_now.strftime('%Y%m%d%H%M%S')}{_i:03d}{_secrets.token_hex(2)}"
                            _data = compress_image(f.getvalue())
                            _ok_all &= bool(kv_save(f"free_cap_{_cid}", _data))
                            st.session_state[f"_free_img_{_cid}"] = _data
                            _idx.append({"id": _cid, "name": f.name, "ts": _now.isoformat(timespec="seconds"),
                                         "owner": _me, "group": _g, "comment": (_per[_i] or "").strip()})
                            _added += 1
                        except Exception as e:
                            st.warning(f"Échec {f.name} : {e}")
                    if (_gnote or "").strip():
                        _grp[_g] = _gnote.strip()
                    st.session_state._free_idx = _idx; st.session_state._free_grp = _grp
                    _ok_all &= bool(_save_caps())
                    st.session_state._free_up_n = _nup + 1
                    st.toast(f"{_added} image(s) importée(s)" + ("" if _ok_all else " (sauvegarde en ligne à vérifier)"))
                    st.rerun()

        if not _vis:
            st.info("Aucune capture libre pour l'instant : importe une ou plusieurs images ci-dessus.")
        else:
            _dd = sorted(c["ts"][:10] for c in _vis)
            _fmin, _fmax = date.fromisoformat(_dd[0]), date.fromisoformat(_dd[-1])
            with st.container(horizontal=True, key="fc_filters", gap="small"):
                _f_from, _f_to = period_filter("Date d'import", _fmin, _fmax, "fcper")
            _q = st.text_input("Recherche", key="fc_q", label_visibility="collapsed",
                               placeholder="Rechercher dans les commentaires ou le nom du fichier…")
            _sel = [c for c in _vis if str(_f_from) <= c["ts"][:10] <= str(_f_to)]
            if _q:
                _ql = _q.lower()
                _sel = [c for c in _sel if _ql in " ".join([c.get("name", ""), c.get("comment", ""),
                                                            _grp.get(_gid(c), "")]).lower()]
            _sel.sort(key=lambda c: (c["ts"], c["id"]), reverse=True)

            # ── Commentaire d'une sélection de plusieurs images ──
            _pk = st.session_state.get("fc_sel_n", 0)
            _picked = [c for c in _sel if st.session_state.get(f"fc_pick_{_pk}_{c['id']}")]
            if _picked:
                with st.container(key="fc_selbar"):
                    sb1, sb2, sb3 = st.columns([3.2, 1.4, 1.1], vertical_alignment="bottom")
                    with sb1:
                        _sc = st.text_input(f"Commentaire pour les {len(_picked)} image(s) sélectionnée(s)",
                                            key=f"fc_sel_txt_{st.session_state.get('fc_sel_n', 0)}",
                                            placeholder="Même commentaire pour toute la sélection")
                    with sb2:
                        _mode = st.radio("Mode", ["Remplacer", "Ajouter à la suite"], key="fc_sel_mode",
                                         horizontal=True, label_visibility="collapsed")
                    with sb3:
                        if st.button("Appliquer", type="primary", key="fc_sel_go", icon=":material/comment:",
                                     use_container_width=True, disabled=not (_sc or "").strip()):
                            for c in _picked:
                                old = c.get("comment", "")
                                c["comment"] = _sc.strip() if (_mode == "Remplacer" or not old) else f"{old} · {_sc.strip()}"
                            _save_caps(); st.session_state.fc_sel_n = st.session_state.get("fc_sel_n", 0) + 1
                            st.toast(f"Commentaire appliqué à {len(_picked)} image(s)"); st.rerun()

            _PER = 12
            _np = max(1, -(-len(_sel) // _PER))
            _pg = min(st.session_state.get("fc_page", 0), _np - 1)
            _page = _sel[_pg * _PER:(_pg + 1) * _PER]
            st.markdown(f"<div style='color:{_t['muted']};font-size:13px;margin:6px 0 10px'>"
                        f"<b style='color:{_t['accent']};font-family:JetBrains Mono,monospace'>{len(_sel)}</b> "
                        f"image(s) · page {_pg + 1} / {_np} · coche des images pour les commenter ensemble</div>",
                        unsafe_allow_html=True)

            _need = [c["id"] for c in _page if f"_free_img_{c['id']}" not in st.session_state]
            if _need:
                _got = kv_load_many([f"free_cap_{i}" for i in _need])
                for i in _need:
                    st.session_state[f"_free_img_{i}"] = _got.get(f"free_cap_{i}")

            # ── Galerie regroupée par import ──
            _groups = []
            for c in _page:
                if not _groups or _groups[-1][0] != _gid(c):
                    _groups.append((_gid(c), []))
                _groups[-1][1].append(c)
            for _g, _items in _groups:
                _can = is_admin() or _items[0].get("owner") == _me
                _gtot = sum(1 for c in _vis if _gid(c) == _g)
                _d = datetime.fromisoformat(_items[0]["ts"])
                gh1, gh2 = st.columns([5, 1.3], vertical_alignment="center")
                with gh1:
                    _gc = _grp.get(_g, "")
                    st.markdown(
                        f"<div style='margin:14px 0 6px;padding:8px 14px;background:{_t['accent']}10;"
                        f"border-left:3px solid {_t['accent']};border-radius:4px 18px 18px 4px'>"
                        f"<span style='font-size:12.5px;font-weight:800;color:{_t['text']}'>Import du "
                        f"{_d.strftime('%d/%m/%Y à %H:%M')}</span> <span style='font-size:11px;color:{_t['muted']}'>· "
                        f"{_gtot} image(s)</span>"
                        + (f"<div style='font-size:12.5px;color:{_t['text']};margin-top:3px'>{_html.escape(_gc)}</div>"
                           if _gc else f"<div style='font-size:11.5px;color:{_t['muted']};margin-top:2px'>"
                                       f"Pas de commentaire de groupe</div>")
                        + "</div>", unsafe_allow_html=True)
                with gh2:
                    if _can:
                        with st.popover("Groupe", icon=":material/edit_note:", use_container_width=True):
                            _ng = st.text_area("Commentaire du groupe", value=_gc, key=f"fc_g_{_g}", height=90)
                            if st.button("Enregistrer", key=f"fc_gs_{_g}", type="primary", use_container_width=True):
                                if _ng.strip(): _grp[_g] = _ng.strip()
                                else: _grp.pop(_g, None)
                                st.session_state._free_grp = _grp; _save_caps(); st.rerun()
                gcols = st.columns(3)
                for _i, c in enumerate(_items):
                    with gcols[_i % 3]:
                        _img = st.session_state.get(f"_free_img_{c['id']}")
                        ch1, ch2 = st.columns([4, 1], vertical_alignment="center")
                        with ch1:
                            st.markdown(f"<div style='font-size:11.5px;color:{_t['muted']}'>"
                                        f"{_html.escape(c.get('name', ''))[:40]}</div>", unsafe_allow_html=True)
                        with ch2:
                            if _can:
                                st.checkbox("Sélection", key=f"fc_pick_{_pk}_{c['id']}", label_visibility="collapsed")
                        if _img:
                            st.image(_img, use_container_width=True)
                        else:
                            st.caption("Image indisponible.")
                        if c.get("comment"):
                            st.markdown(f"<div style='font-size:12.5px;color:{_t['text']};margin:2px 0 6px;"
                                        f"padding:6px 10px;background:{_t['card']};border:1px solid {_t['border']};"
                                        f"border-radius:4px 14px 14px 14px'>{_html.escape(c['comment'])}</div>",
                                        unsafe_allow_html=True)
                        if _can:
                            a1, a2 = st.columns(2)
                            with a1:
                                with st.popover("Commenter", icon=":material/comment:", use_container_width=True):
                                    _nc = st.text_area("Commentaire de l'image", value=c.get("comment", ""),
                                                       key=f"fc_c_{c['id']}", height=90)
                                    if st.button("Enregistrer", key=f"fc_cs_{c['id']}", type="primary",
                                                 use_container_width=True):
                                        c["comment"] = _nc.strip(); _save_caps(); st.rerun()
                            with a2:
                                if st.session_state.get("fc_del") == c["id"]:
                                    if st.button("Confirmer", key=f"fc_yes_{c['id']}", icon=":material/check:",
                                                 use_container_width=True):
                                        kv_delete(f"free_cap_{c['id']}")
                                        st.session_state._free_idx = [x for x in _idx if x["id"] != c["id"]]
                                        _save_caps()
                                        st.session_state.pop(f"_free_img_{c['id']}", None)
                                        st.session_state.pop("fc_del", None); st.rerun()
                                elif st.button("Supprimer", key=f"fc_del_{c['id']}", icon=":material/delete:",
                                               use_container_width=True):
                                    st.session_state.fc_del = c["id"]; st.rerun()

            if _np > 1:
                p1, p2, p3 = st.columns([1, 1, 4])
                with p1:
                    if st.button("Précédent", key="fc_prev", icon=":material/chevron_left:", disabled=_pg == 0,
                                 use_container_width=True):
                        st.session_state.fc_page = _pg - 1; st.rerun()
                with p2:
                    if st.button("Suivant", key="fc_next", icon=":material/chevron_right:", disabled=_pg >= _np - 1,
                                 use_container_width=True):
                        st.session_state.fc_page = _pg + 1; st.rerun()

    # ══ CAPTURES DES TRADES (existant) ══════════════════════════════════════════
    with tab_trc:
        st.caption("Toutes les captures de setups, filtrables par date et par compte. "
                   + ("L'ajout se fait dans le Journal (trade sélectionné)."
                      if is_admin() else "Consultation limitée à vos comptes."))

        _shots = st.session_state.get("trade_screenshots", {})
        _allowed = allowed_accounts()
        # Index des trades par id
        _by_id = {str(t["id"]): t for t in st.session_state.trades}

        # Construire la liste (trade, screenshot) visible selon droits
        _items = []
        for tid, lst in _shots.items():
            tr = _by_id.get(str(tid))
            if not tr:
                continue
            if tr.get("trade_mode", "Réel Indépendant") not in _allowed:
                continue
            for sh in lst:
                _items.append((tr, sh))

        if not _items:
            st.info("Aucune capture disponible pour vos comptes. "
                    + ("Ajoutez-en depuis le Journal." if is_admin() else ""))
        else:
            # Bornes de dates
            _dts = sorted([tr.get("date", "") for tr, _ in _items if tr.get("date")])
            _dmin = date.fromisoformat(_dts[0]) if _dts else date(2024, 1, 1)
            _dmax = date.fromisoformat(_dts[-1]) if _dts else date.today()

            fc1, fc2, fc3 = st.columns([1.2, 1.2, 2.4])
            with fc1:
                c_from = st.date_input("Du", value=_dmin, key="cap_from")
            with fc2:
                c_to = st.date_input("Au", value=_dmax, key="cap_to")
            with fc3:
                c_acc = st.multiselect("Comptes", _allowed, default=[],
                                       placeholder="Tous mes comptes", key="cap_acc")

            # Filtrage
            def _in_range(tr):
                d = tr.get("date", "")
                try:
                    dd = date.fromisoformat(d)
                except Exception:
                    return False
                if dd < c_from or dd > c_to:
                    return False
                if c_acc and tr.get("trade_mode") not in c_acc:
                    return False
                return True

            _filtered = [(tr, sh) for tr, sh in _items if _in_range(tr)]
            # Trier par date décroissante
            _filtered.sort(key=lambda x: (x[0].get("date", ""), x[1].get("ts", "")), reverse=True)

            st.markdown(
                f"<div style='color:{_t['muted']};font-size:13px;margin:6px 0 12px'>"
                f"<b style='color:{_t['accent']};font-family:JetBrains Mono,monospace'>"
                f"{len(_filtered)}</b> capture(s) sur la période.</div>",
                unsafe_allow_html=True)

            if not _filtered:
                st.info("Aucune capture sur cette plage de dates.")
            else:
                gcols = st.columns(3)
                for _i, (tr, sh) in enumerate(_filtered):
                    with gcols[_i % 3]:
                        _pnl = tr.get("pnl", 0)
                        _pc = _t["win"] if _pnl >= 0 else _t["loss"]
                        st.markdown(
                            f"<div style='font-size:12px;margin-bottom:2px'>"
                            f"<b style='color:{_t['text']}'>{tr.get('date','')} "
                            f"{tr.get('time','') or ''}</b> · "
                            f"<span style='color:{_t['muted']}'>{tr.get('symbol','')} "
                            f"{tr.get('direction','')}</span> · "
                            f"<span style='color:{_pc};font-family:JetBrains Mono,monospace'>"
                            f"{fmt(_pnl)}</span></div>",
                            unsafe_allow_html=True)
                        st.markdown(
                            f"<div style='font-size:10px;color:{_t['muted']};margin-bottom:4px'>"
                            f"{tr.get('trade_mode','')} · {tr.get('strategy','')}</div>",
                            unsafe_allow_html=True)
                        st.image(sh["data"], use_container_width=True)
