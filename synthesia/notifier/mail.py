"""Envoi du brief par email (Gmail SMTP).

Canal de livraison « push » : le brief arrive chaque matin dans la boîte mail,
sans rien à ouvrir. Complète le serveur web (qui reste pour fouiller l'historique).

Configuration via le .env (jamais dans le code) :
    EMAIL_EXPEDITEUR=ton.adresse@gmail.com
    EMAIL_MOT_DE_PASSE=xxxx xxxx xxxx xxxx   # « mot de passe d'application » Gmail
    EMAIL_DESTINATAIRE=a@x.fr, b@y.fr        # optionnel ; plusieurs séparés par virgule

Si EMAIL_EXPEDITEUR / EMAIL_MOT_DE_PASSE sont absents, l'envoi est simplement
ignoré (utile en dev/tests : on ne spamme pas).
"""

from __future__ import annotations

import html
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

# Import paresseux de pipeline (cf. construire_email) pour éviter un cycle :
# pipeline importe ce module, ce module n'importe pipeline qu'à l'exécution.
# Les annotations `SyntheseProduite` ne sont pas évaluées (from __future__ ...).

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL implicite


def _destinataires(brut: str | None, expediteur: str | None) -> list[str]:
    """Liste des destinataires : virgules ou points-virgules. Défaut = expéditeur."""
    if not brut:
        return [expediteur] if expediteur else []
    return [d.strip() for d in brut.replace(";", ",").split(",") if d.strip()]


def _config() -> tuple[str | None, str | None, list[str]]:
    load_dotenv(_ENV_PATH)
    exp = os.getenv("EMAIL_EXPEDITEUR")
    mdp = os.getenv("EMAIL_MOT_DE_PASSE")
    dest = _destinataires(os.getenv("EMAIL_DESTINATAIRE"), exp)
    return exp, mdp, dest


def email_configure() -> bool:
    """Vrai si l'envoi est configuré (expéditeur + mot de passe présents)."""
    exp, mdp, _ = _config()
    return bool(exp and mdp)


# --------------------------------------------------------------------------- #
#  Construction du message
# --------------------------------------------------------------------------- #

def _fiche_html(p: SyntheseProduite, reine: bool = False) -> str:
    e = html.escape
    r = p.record
    src = ", ".join(sorted(set(p.sources)))
    domaines = ", ".join(r.domaines)
    couronne = "🎯 " if reine else ""
    return (
        '<div style="border-left:4px solid #b5651d;background:#faf8f3;'
        'padding:14px 16px;margin:0 0 18px;border-radius:6px">'
        f'<div style="font-size:18px;font-weight:bold;margin-bottom:10px">{couronne}{e(r.assertion)}</div>'
        f'<p style="margin:6px 0"><b style="color:#b5651d">Parce que</b> {e(r.parce_que)}</p>'
        f'<p style="margin:6px 0"><b style="color:#b5651d">Exemple :</b> {e(r.exemple)}</p>'
        f'<p style="margin:6px 0"><b style="color:#b5651d">C\'est comme</b> {e(r.cest_comme)}</p>'
        f'<p style="margin:6px 0"><b style="color:#b5651d">→ So what :</b> {e(r.so_what)}</p>'
        f'<p style="font-size:13px;color:#666;margin-top:10px;border-top:1px solid #e5e0d5;padding-top:6px">'
        f'📎 {e(src)} &nbsp;|&nbsp; {e(domaines)}</p>'
        '<p style="font-size:12px;color:#9a5b00;margin:4px 0 0">'
        '⚠ Exemple &amp; analogie à recouper avant diffusion.</p>'
        '</div>'
    )


def construire_email(
    produites: list[SyntheseProduite], date: str
) -> tuple[str, str, str]:
    """Construit (sujet, corps_html, corps_texte) à partir des synthèses du jour.

    La reine (meilleur score) est mise en tête ; les autres suivent.
    """
    from synthesia.brief.pipeline import rendre_brief  # import paresseux (cf. en-tête)

    classees = sorted(produites, key=lambda p: p.record.score, reverse=True)
    reine = classees[0]

    sujet = f"🎯 Brief SynthesIA — {date} — {reine.record.theme}"

    # Version HTML
    cartes = [_fiche_html(reine, reine=True)]
    cartes += [_fiche_html(p) for p in classees[1:]]
    corps_html = (
        '<div style="max-width:680px;margin:0 auto;'
        'font-family:Georgia,\'Times New Roman\',serif;color:#1a1a1a">'
        f'<h2 style="border-bottom:2px solid #b5651d;padding-bottom:6px">'
        f'SynthesIA — Brief du jour <span style="font-size:13px;color:#888">({html.escape(date)})</span></h2>'
        + "".join(cartes)
        + '<p style="font-size:12px;color:#999">Généré automatiquement par SynthesIA.</p>'
        '</div>'
    )

    # Version texte (repli pour les clients sans HTML)
    blocs = [rendre_brief(reine.record, reine.sources)]
    for p in classees[1:]:
        blocs.append("\n" + rendre_brief(p.record, p.sources))
    corps_texte = f"SynthesIA — Brief du jour ({date})\n\n" + "\n".join(blocs)

    return sujet, corps_html, corps_texte


# --------------------------------------------------------------------------- #
#  Envoi
# --------------------------------------------------------------------------- #

def envoyer(sujet: str, corps_html: str, corps_texte: str) -> None:
    """Envoie un email via Gmail SMTP (SSL). Lève si non configuré."""
    exp, mdp, dest = _config()
    if not (exp and mdp):
        raise RuntimeError(
            "Envoi non configuré : renseigne EMAIL_EXPEDITEUR et "
            "EMAIL_MOT_DE_PASSE dans le .env."
        )
    if not dest:
        raise RuntimeError("Aucun destinataire (EMAIL_DESTINATAIRE).")

    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = exp
    msg["To"] = ", ".join(dest)   # plusieurs destinataires
    msg.set_content(corps_texte)               # repli texte
    msg.add_alternative(corps_html, subtype="html")  # version riche

    contexte = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=contexte) as serveur:
        serveur.login(exp, mdp)
        serveur.send_message(msg)


def envoyer_brief(produites: list[SyntheseProduite], date: str) -> None:
    """Construit et envoie le brief du jour. Ne fait rien si non configuré."""
    if not produites or not email_configure():
        return
    sujet, corps_html, corps_texte = construire_email(produites, date)
    envoyer(sujet, corps_html, corps_texte)
