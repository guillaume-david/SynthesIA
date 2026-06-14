"""API FastAPI — Étape 6 : consultation du brief sur mobile.

Sert une page web sobre et lisible (la fiche reine du jour + les synthèses du
jour), plus un point JSON. Conçu pour être ouvert dans le navigateur d'un
téléphone, sur le réseau local.

Lancer :  uv run uvicorn synthesia.api.app:app --host 0.0.0.0 --port 8000
Puis, sur le téléphone (même réseau) :  http://<IP-de-la-machine>:8000

(L'accès depuis l'extérieur viendra à l'Étape 8 — VPN Tailscale.)
La recherche par sens (Mode B) sera ajoutée plus tard.
"""

from __future__ import annotations

import html
import json
import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from synthesia.stockage import base

app = FastAPI(title="SynthesIA", description="Veille stratégique PEMSI")


# --------------------------------------------------------------------------- #
#  Accès aux données
# --------------------------------------------------------------------------- #

def _syntheses_du_jour(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Renvoie les synthèses du jour le plus récent, reine en tête (score desc).

    `lister_syntheses` trie par date décroissante : on isole le jour le plus
    récent, puis on reclasse PAR SCORE pour que la reine (meilleur score) sorte
    en tête, indépendamment de l'ordre d'insertion.
    """
    toutes = base.lister_syntheses(conn)
    if not toutes:
        return []
    jour = toutes[0]["date"][:10]  # AAAA-MM-JJ du plus récent
    du_jour = [s for s in toutes if s["date"][:10] == jour]
    return sorted(du_jour, key=lambda s: s["score"], reverse=True)


def _sources(conn: sqlite3.Connection, synthese_id: int) -> str:
    rows = base.articles_de_synthese(conn, synthese_id)
    return ", ".join(sorted({r["source"] for r in rows})) or "—"


# --------------------------------------------------------------------------- #
#  Rendu HTML
# --------------------------------------------------------------------------- #

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 17px/1.55 Georgia, 'Times New Roman', serif; margin: 0;
       background: #f4f1ea; color: #1a1a1a; }
@media (prefers-color-scheme: dark) { body { background:#16161a; color:#e8e6e0; } }
.wrap { max-width: 720px; margin: 0 auto; padding: 1.2rem 1.1rem 3rem; }
header { border-bottom: 2px solid #b5651d; padding-bottom:.5rem; margin-bottom:1.4rem; }
header h1 { font-size:1.3rem; margin:0; letter-spacing:.04em; }
header .d { font-size:.8rem; opacity:.6; }
.card { background: rgba(127,127,127,.06); border-left: 4px solid #b5651d;
        border-radius: 6px; padding: 1rem 1.1rem; margin-bottom: 1.2rem; }
.assertion { font-size: 1.18rem; font-weight: bold; margin:.1rem 0 .7rem; }
.bloc { margin:.45rem 0; }
.bloc b { color:#b5651d; }
.meta { font-size:.78rem; opacity:.65; margin-top:.8rem; border-top:1px solid rgba(127,127,127,.2); padding-top:.5rem; }
.warn { font-size:.78rem; color:#9a5b00; margin-top:.4rem; }
.autres { margin-top:2rem; }
.autres h2 { font-size:.95rem; text-transform:uppercase; letter-spacing:.05em; opacity:.7; }
.autres a { display:block; padding:.55rem .2rem; border-bottom:1px solid rgba(127,127,127,.15);
            text-decoration:none; color:inherit; }
.autres a:hover { color:#b5651d; }
.pill { font-size:.72rem; background:#b5651d; color:#fff; border-radius:10px; padding:.05rem .5rem; }
a.retour { color:#b5651d; text-decoration:none; font-size:.85rem; }
"""


def _page(titre: str, corps: str) -> str:
    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(titre)}</title><style>{CSS}</style></head>"
        f"<body><div class='wrap'>{corps}</div></body></html>"
    )


def _fiche_html(s: sqlite3.Row, sources: str, reine: bool = False) -> str:
    e = html.escape
    domaines = ", ".join(json.loads(s["domaines"] or "[]"))
    couronne = "🎯 " if reine else ""
    return (
        "<div class='card'>"
        f"<div class='assertion'>{couronne}{e(s['assertion'])}</div>"
        f"<div class='bloc'><b>Parce que</b> {e(s['parce_que'])}</div>"
        f"<div class='bloc'><b>Exemple :</b> {e(s['exemple'])}</div>"
        f"<div class='bloc'><b>C'est comme</b> {e(s['cest_comme'])}</div>"
        f"<div class='bloc'><b>→ So what :</b> {e(s['so_what'])}</div>"
        f"<div class='meta'>📎 {e(sources)} &nbsp;|&nbsp; {e(domaines)}</div>"
        "<div class='warn'>⚠ Exemple &amp; analogie à recouper avant diffusion.</div>"
        "</div>"
    )


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #

@app.get("/", response_class=HTMLResponse)
def accueil() -> str:
    """Page d'accueil : la fiche reine du jour + les autres synthèses du jour."""
    conn = base.get_connection()
    try:
        jour = _syntheses_du_jour(conn)
        if not jour:
            corps = (
                "<header><h1>SynthesIA</h1></header>"
                "<p>Aucune synthèse en base. Lance d'abord le brief :<br>"
                "<code>uv run python -m synthesia.brief.pipeline</code></p>"
            )
            return _page("SynthesIA", corps)

        reine = jour[0]
        date_aff = reine["date"][:10]
        corps = [
            f"<header><h1>SynthesIA — Brief du jour</h1>"
            f"<div class='d'>{html.escape(date_aff)}</div></header>",
            _fiche_html(reine, _sources(conn, reine["id"]), reine=True),
        ]
        if len(jour) > 1:
            corps.append("<div class='autres'><h2>Autres synthèses du jour</h2>")
            for s in jour[1:]:
                corps.append(
                    f"<a href='/synthese/{s['id']}'>"
                    f"<span class='pill'>{s['score']}</span> "
                    f"{html.escape(s['theme'])} — {html.escape(s['assertion'])}</a>"
                )
            corps.append("</div>")
        return _page("SynthesIA — Brief du jour", "".join(corps))
    finally:
        conn.close()


@app.get("/synthese/{synthese_id}", response_class=HTMLResponse)
def fiche(synthese_id: int) -> str:
    """Page détail d'une synthèse."""
    conn = base.get_connection()
    try:
        s = base.get_synthese(conn, synthese_id)
        if s is None:
            raise HTTPException(status_code=404, detail="Synthèse introuvable")
        corps = (
            f"<header><h1>{html.escape(s['theme'])}</h1>"
            f"<div class='d'>{html.escape(s['date'][:10])}</div></header>"
            + _fiche_html(s, _sources(conn, s["id"]))
            + "<p><a class='retour' href='/'>← Retour au brief</a></p>"
        )
        return _page(s["theme"], corps)
    finally:
        conn.close()


@app.get("/api/brief")
def api_brief() -> JSONResponse:
    """Le brief du jour en JSON (pour une appli ou un autre client)."""
    conn = base.get_connection()
    try:
        jour = _syntheses_du_jour(conn)
        if not jour:
            return JSONResponse({"brief": None})
        reine = jour[0]
        return JSONResponse({
            "date": reine["date"][:10],
            "theme": reine["theme"],
            "assertion": reine["assertion"],
            "parce_que": reine["parce_que"],
            "exemple": reine["exemple"],
            "cest_comme": reine["cest_comme"],
            "so_what": reine["so_what"],
            "domaines": json.loads(reine["domaines"] or "[]"),
            "sources": _sources(conn, reine["id"]).split(", "),
            "avertissement": "Exemple & analogie à recouper avant diffusion.",
        })
    finally:
        conn.close()
