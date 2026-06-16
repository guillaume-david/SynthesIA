"""Passe 2 — Mode A : analyse corrélée (la fiche reine).

On fournit un ou plusieurs articles d'un même thème. Le LLM (Sonnet) ne résume
PAS pièce par pièce : il produit UNE analyse qui croise les sources et tranche,
structurée selon la colonne vertébrale rhétorique du projet.
"""

from __future__ import annotations

from dataclasses import dataclass

import anthropic
from google import genai
from google.genai import types


from .client import MODELE_SYNTHESE, get_client
from .schemas import Synthese

SYSTEM_SYNTHESE = (
    "Tu es un analyste de recherche interarmées senior. On te fournit UN OU PLUSIEURS "
    "articles portant sur un même thème. Ne résume pas chaque article séparément : "
    "produis UNE SEULE analyse corrélée qui croise les sources, fait ressortir "
    "l'essentiel et tranche. Synthèse toujours en français, style soutenu, concis, "
    "direct, neutre, sans fioritures.\n\n"
    "Structure imposée :\n"
    "- assertion : l'idée importante du jour, claire et certaine (1-2 phrases).\n"
    "- parce_que : l'argument causal qui la fonde.\n"
    "- exemple : un fait concret, un chiffre choc ou un précédent.\n"
    "- cest_comme : un parallèle historique ou une analogie marquante. "
    "OBLIGATOIRE, jamais vide : il faut une image mentale à laquelle se raccrocher.\n"
    "- so_what : ce que ça change concrètement, la conséquence stratégique.\n"
    "Choisis aussi un thème court et le(s) domaine(s) PEMSI concerné(s)."
)


@dataclass
class ArticleSource:
    """Un article fourni à l'analyse, avec sa provenance pour citation."""

    source: str
    titre: str
    texte: str


def _formater(articles: list[ArticleSource]) -> str:
    blocs = []
    for i, a in enumerate(articles, 1):
        blocs.append(
            f"=== Article {i} — source : {a.source} ===\n"
            f"Titre : {a.titre}\n\n{a.texte}"
        )
    return "\n\n".join(blocs)


def analyser(
    articles: list[ArticleSource], client: genai.Client | None = None
) -> Synthese:
    """Produit une synthèse corrélée à partir de 1..N articles d'un même thème."""
    if not articles:
        raise ValueError("Aucun article fourni à analyser.")
    client = client or get_client()
    
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_SYNTHESE,
        temperature=0.2,
        response_mime_type="application/json",
        response_schema=Synthese,
    )
    
    reponse = client.models.generate_content(
        model=MODELE_SYNTHESE,
        contents=_formater(articles),
        config=config,
    )
    
    # Le SDK valide et parse automatiquement si response_schema est fourni
    return reponse.parsed
    