"""Alertes e-mail avant les annonces économiques (exécuté par GitHub Actions toutes les 5 min).

Lit les préférences dans Supabase (journal_data, clé 'alert_prefs'), récupère le calendrier,
envoie un e-mail par créneau d'annonce dans le délai choisi, et mémorise les envois
(clé 'alert_sent') pour ne jamais envoyer deux fois la même alerte.

Variables d'environnement (secrets GitHub) :
  SUPABASE_URL, SUPABASE_KEY, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, [SMTP_FROM], [APP_URL]
Options : --dry-run (n'envoie rien, affiche), --test-email adresse@exemple.com
"""
import os, sys, json, ssl, smtplib, html
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import econ_kb
except Exception:
    econ_kb = None

USER_TZ_OFFSET = 1          # heures affichées en GMT+1
SENT_RETENTION_DAYS = 7
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
CC2CCY = {"US": "USD", "EU": "EUR", "DE": "EUR", "FR": "EUR", "IT": "EUR", "ES": "EUR", "NL": "EUR",
          "GB": "GBP", "UK": "GBP", "JP": "JPY", "CH": "CHF", "CA": "CAD", "AU": "AUD", "NZ": "NZD",
          "CN": "CNY"}
IMP_FR = {"High": "Fort", "Medium": "Moyen", "Low": "Faible"}


# ── Supabase (table journal_data : key TEXT, value JSONB) ─────────────────────
def _sb():
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise SystemExit("SUPABASE_URL / SUPABASE_KEY manquants.")
    return f"{url}/rest/v1/journal_data", {"apikey": key, "Authorization": f"Bearer {key}",
                                           "Content-Type": "application/json"}

def kv_get(key, default):
    ep, hdr = _sb()
    r = requests.get(f"{ep}?key=eq.{key}&select=value", headers=hdr, timeout=15)
    r.raise_for_status()
    rows = r.json()
    return rows[0].get("value") if rows and rows[0].get("value") is not None else default

def kv_set(key, value):
    ep, hdr = _sb()
    r = requests.patch(f"{ep}?key=eq.{key}", headers={**hdr, "Prefer": "return=representation"},
                       json={"value": value}, timeout=15)
    if r.status_code == 200 and r.json():
        return True
    r2 = requests.post(ep, headers={**hdr, "Prefer": "resolution=merge-duplicates,return=representation"},
                       json={"key": key, "value": value}, timeout=15)
    return r2.status_code in (200, 201)


# ── Calendrier ────────────────────────────────────────────────────────────────
def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_utc(iso):
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        return None

def _fmt(v, scale="", unit=""):
    if v is None or v == "":
        return ""
    try:
        x = float(v)
    except Exception:
        return str(v)
    s = f"{int(x)}" if x == int(x) else f"{x:.2f}".rstrip("0").rstrip(".")
    return s + (scale if scale in ("K", "M", "B", "T") else "") + ("%" if unit == "%" else "")

def fetch_calendar():
    """TradingView en priorité, puis faireconomy (prévisions). Renvoie une liste normalisée."""
    now = _utcnow()
    try:
        r = requests.get("https://economic-calendar.tradingview.com/events", timeout=15,
            headers={**UA, "Origin": "https://www.tradingview.com", "Referer": "https://www.tradingview.com/"},
            params={"from": (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "to": (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "countries": "US,EU,GB,JP,CH,CA,AU,NZ,CN,DE,FR,IT,ES"})
        if r.status_code == 200:
            data = r.json(); res = data.get("result", data if isinstance(data, list) else [])
            out = []
            for ev in res:
                ccy = CC2CCY.get(str(ev.get("country", "")).upper())
                if not ccy:
                    continue
                out.append({"title": str(ev.get("title") or ev.get("indicator") or ""), "country": ccy,
                            "impact": {1: "High", 0: "Medium", -1: "Low"}.get(ev.get("importance", 0), "Medium"),
                            "forecast": _fmt(ev.get("forecast"), ev.get("scale", ""), ev.get("unit", "")),
                            "previous": _fmt(ev.get("previous"), ev.get("scale", ""), ev.get("unit", "")),
                            "date": str(ev.get("date", ""))})
            if out:
                return out, "TradingView"
    except Exception as e:
        print("TradingView indisponible:", type(e).__name__)
    out, seen = [], set()
    for sc in ("thisweek", "nextweek"):
        try:
            r = requests.get(f"https://nfs.faireconomy.media/ff_calendar_{sc}.json", headers=UA, timeout=15)
            if r.status_code != 200:
                continue
            for ev in r.json():
                k = (ev.get("title"), ev.get("date"), ev.get("country"))
                if k in seen:
                    continue
                seen.add(k)
                out.append({"title": str(ev.get("title", "")), "country": str(ev.get("country", "")),
                            "impact": str(ev.get("impact", "")), "forecast": str(ev.get("forecast", "") or ""),
                            "previous": str(ev.get("previous", "") or ""), "date": str(ev.get("date", ""))})
        except Exception as e:
            print("faireconomy indisponible:", sc, type(e).__name__)
    return out, "faireconomy"


# ── Sélection des alertes dues ────────────────────────────────────────────────
def due_alerts(events, prefs, sent, now):
    """{(user, email): [(dt_utc, [events])]} des créneaux à notifier maintenant."""
    plan = {}
    for user, p in (prefs or {}).items():
        if not isinstance(p, dict) or not p.get("enabled") or not p.get("email"):
            continue
        lead = int(p.get("lead_min", 30)); imps = set(p.get("impacts") or ["High"])
        ccys = set(p.get("ccys") or ["USD"])
        slots = {}
        for ev in events:
            if ev["country"] not in ccys or ev["impact"] not in imps:
                continue
            dt = _parse_utc(ev["date"])
            if dt is None:
                continue
            rem = (dt - now).total_seconds()
            if not (0 < rem <= lead * 60):
                continue
            if f"{user}|{ev['title']}|{ev['date']}" in sent:
                continue
            slots.setdefault(dt, []).append(ev)
        if slots:
            plan[(user, p["email"])] = sorted(slots.items())
    return plan

def build_email(slot_dt, evs, now):
    esc = lambda x: html.escape(str(x), quote=False)
    mins = max(1, round((slot_dt - now).total_seconds() / 60))
    local = (slot_dt + timedelta(hours=USER_TZ_OFFSET)).strftime("%d/%m/%Y à %H:%M")
    names = ", ".join(sorted({e["title"] for e in evs}))
    subject = f"⏱ Dans {mins} min : {evs[0]['country']} {evs[0]['title']}" + (f" (+{len(evs)-1})" if len(evs) > 1 else "")
    blocks = ""
    for e in evs:
        d = econ_kb.describe(e["title"], e["country"]) if econ_kb else None
        links = "".join(f'<a href="{u}" style="color:#2b3a67;font-weight:700;margin-right:12px">Lire : {esc(l)} ↗</a>'
                        for l, u in (d["links"] if d else []))
        kb = (f'<p style="margin:6px 0;color:#1b2440"><b>Ce que c\'est :</b> {esc(d["what"])}</p>'
              f'<p style="margin:6px 0;color:#1b2440"><b>Pourquoi c\'est suivi :</b> {esc(d["why"])}</p>'
              f'<p style="margin:6px 0;color:#16a085"><b>Au-dessus du consensus :</b> {esc(d["up"])}</p>'
              f'<p style="margin:6px 0;color:#e74c3c"><b>En dessous du consensus :</b> {esc(d["down"])}</p>'
              f'<p style="margin:8px 0 0">{links}</p>') if d else ""
        blocks += (f'<div style="border:1px solid #d9dfea;border-left:4px solid #2b3a67;border-radius:10px;'
                   f'padding:12px 16px;margin:12px 0;background:#ffffff">'
                   f'<div style="font-size:12px;color:#6b7488"><b style="color:#1b2440">{esc(e["country"])}</b> · '
                   f'Importance {esc(IMP_FR.get(e["impact"], e["impact"]))}</div>'
                   f'<div style="font-size:16px;font-weight:800;color:#1b2440;margin:4px 0 2px">{esc(e["title"])}</div>'
                   + (f'<div style="font-size:13px;color:#2b3a67;margin:0 0 8px">{esc(d["name"])}</div>'
                      if d and d.get("known") else '<div style="height:6px"></div>') +
                   f'<table style="border-collapse:collapse"><tr>'
                   f'<td style="padding:4px 16px 4px 0;color:#6b7488">Prévu (consensus)</td>'
                   f'<td style="padding:4px 0;font-weight:800;font-family:Consolas,monospace">{esc(e["forecast"] or "—")}</td></tr>'
                   f'<tr><td style="padding:4px 16px 4px 0;color:#6b7488">Précédent</td>'
                   f'<td style="padding:4px 0;font-family:Consolas,monospace">{esc(e["previous"] or "—")}</td></tr></table>'
                   f'{kb}</div>')
    app_url = os.environ.get("APP_URL", "")
    app_link = (f'<p style="margin-top:16px"><a href="{esc(app_url)}" style="color:#2b3a67;font-weight:700">'
                f'Ouvrir le Trading Journal ↗</a></p>') if app_url else ""
    body = (f'<div style="font-family:Arial,Helvetica,sans-serif;background:#eef1f7;padding:20px">'
            f'<div style="max-width:640px;margin:auto">'
            f'<div style="background:#1e2a4a;color:#fff;border-radius:12px;padding:16px 20px">'
            f'<div style="font-size:12px;letter-spacing:1px;text-transform:uppercase;opacity:.8">Alerte annonce économique</div>'
            f'<div style="font-size:22px;font-weight:800;margin-top:4px">Dans {mins} min · {esc(local)} (GMT+1)</div>'
            f'<div style="font-size:13px;opacity:.85;margin-top:4px">{esc(names)}</div></div>'
            f'{blocks}{app_link}'
            f'<p style="font-size:11px;color:#6b7488;margin-top:16px">Alerte envoyée par votre Trading Journal. '
            f'Réglages : page Analyse &amp; News, « Alertes e-mail et chronomètre ».</p></div></div>')
    return subject, body

def send_email(to, subject, body):
    host = os.environ.get("SMTP_HOST", ""); port = int(os.environ.get("SMTP_PORT", "465") or 465)
    user = os.environ.get("SMTP_USER", ""); pwd = os.environ.get("SMTP_PASS", "")
    sender = os.environ.get("SMTP_FROM", "") or user
    if not (host and user and pwd):
        raise SystemExit("SMTP_HOST / SMTP_USER / SMTP_PASS manquants.")
    msg = MIMEMultipart("alternative"); msg["Subject"] = subject; msg["From"] = sender; msg["To"] = to
    msg.attach(MIMEText(body, "html", "utf-8"))
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as s:
            s.login(user, pwd); s.sendmail(sender, [to], msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ssl.create_default_context()); s.login(user, pwd)
            s.sendmail(sender, [to], msg.as_string())


def main(argv):
    dry = "--dry-run" in argv
    if "--test-email" in argv:
        to = argv[argv.index("--test-email") + 1]
        send_email(to, "Trading Journal · test des alertes", "<p>Les alertes e-mail fonctionnent.</p>")
        print("E-mail de test envoyé à", to); return 0
    now = _utcnow()
    prefs = kv_get("alert_prefs", {}) or {}
    sent = kv_get("alert_sent", {}) or {}
    events, src = fetch_calendar()
    print(f"{now:%Y-%m-%d %H:%M} UTC · {len(events)} événements ({src}) · {len(prefs)} profil(s)")
    plan = due_alerts(events, prefs, sent, now)
    n = 0
    for (user, email), slots in plan.items():
        for slot_dt, evs in slots:
            subject, body = build_email(slot_dt, evs, now)
            if dry:
                print(f"[dry-run] -> {email}: {subject}")
            else:
                try:
                    send_email(email, subject, body); n += 1
                    print(f"Envoyé -> {user}: {subject}")
                except Exception as e:
                    print(f"Échec d'envoi -> {user}: {type(e).__name__}: {e}")
                    continue
            for e in evs:
                sent[f"{user}|{e['title']}|{e['date']}"] = now.isoformat()
    cutoff = now - timedelta(days=SENT_RETENTION_DAYS)
    sent = {k: v for k, v in sent.items() if (_parse_utc(v) or now) >= cutoff}
    if not dry and plan:
        kv_set("alert_sent", sent)
    print(f"{n} e-mail(s) envoyé(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
