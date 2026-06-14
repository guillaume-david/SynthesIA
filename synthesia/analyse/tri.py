"""Passe 1 — tri, et passe 1bis — regroupement thématique.

Tri : à partir des seuls titres de la journée, un LLM rapide (Haiku) note
l'intérêt PEMSI de chaque article (0-100) pour décider lesquels méritent qu'on
en récupère le texte intégral. Économie de tokens : on ne paie le corps complet
que pour ce qui compte.

Regroupement : parmi les articles retenus, on identifie les clusters
thématiques pour permettre une analyse corrélée plutôt qu'un résumé par pièce.
"""

from __future__ import annotations

import anthropic

from .client import MODELE_TRI, get_client
from .schemas import Regroupement, TriResultat

SYSTEM_TRI = (
    "Tu es un analyste de veille stratégique interarmées. On te fournit une liste "
    "de titres d'articles du jour, numérotés. Pour chacun, évalue son intérêt pour "
    "une veille PEMSI (Politique, Militaire, Économique, Société, "
    "Science/Technologie à vocation militaire, Géopolitique) par une note de 0 à 100, "
    "et indique le ou les domaines PEMSI pressentis. "
    "Note bas (<30) le bruit non stratégique (faits divers, people, sport, météo). "
    "Note haut (>70) ce qui touche à la défense, la stratégie, la géopolitique, "
    "les ruptures technologiques militaires. Sois sévère : peu d'articles méritent >70."
)

SYSTEM_REGROUPEMENT = (
    "Tu es un analyste de veille. On te fournit des titres d'articles numérotés. "
    "Regroupe en clusters thématiques ceux qui traitent du même sujet ou d'un sujet "
    "connecté (même conflit, même dossier, même acteur). Un cluster peut ne contenir "
    "qu'un seul article s'il est isolé. Donne à chaque cluster un thème court et clair."
)


def _numeroter(titres: list[str]) -> str:
    return "\n".join(f"[{i}] {t}" for i, t in enumerate(titres))


def trier(
    titres: list[str], client: anthropic.Anthropic | None = None
) -> TriResultat:
    """Passe 1 : note chaque titre (0-100) + domaines PEMSI pressentis."""
    client = client or get_client()
    reponse = client.messages.parse(
        model=MODELE_TRI,
        max_tokens=4000,
        system=SYSTEM_TRI,
        messages=[{"role": "user", "content": _numeroter(titres)}],
        output_format=TriResultat,
    )
    return reponse.parsed_output


def regrouper(
    titres: list[str], client: anthropic.Anthropic | None = None
) -> Regroupement:
    """Passe 1bis : regroupe les titres en clusters thématiques."""
    client = client or get_client()
    reponse = client.messages.parse(
        model=MODELE_TRI,
        max_tokens=2000,
        system=SYSTEM_REGROUPEMENT,
        messages=[{"role": "user", "content": _numeroter(titres)}],
        output_format=Regroupement,
    )
    return reponse.parsed_output
