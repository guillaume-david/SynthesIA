"""Schémas de sortie LLM — structures garanties (Pydantic).

Ces modèles sont passés au SDK Anthropic via `messages.parse()`, qui force
le modèle à répondre exactement dans ce format. Pas de parsing fragile.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# Domaines PEMSI — valeurs fermées (le LLM ne peut pas inventer hors liste).
DomainePEMSI = Literal[
    "Politique",
    "Militaire",
    "Économique",
    "Société",
    "Science/Technologie",
    "Géopolitique",
]


class TriArticle(BaseModel):
    """Verdict de tri (passe 1) pour un article, désigné par son index."""

    index: int
    score: int  # 0-100 : intérêt PEMSI pressenti d'après le seul titre
    domaines: list[DomainePEMSI]


class TriResultat(BaseModel):
    """Sortie de la passe 1 : un verdict par article soumis."""

    articles: list[TriArticle]


class Cluster(BaseModel):
    """Un regroupement thématique : les index d'articles parlant du même sujet."""

    theme: str
    indices: list[int]


class Regroupement(BaseModel):
    """Sortie de la passe 1bis : les clusters thématiques de la journée."""

    clusters: list[Cluster]


class Synthese(BaseModel):
    """Sortie du Mode A : une analyse corrélée (la fiche reine en puissance).

    Structure imposée = la colonne vertébrale rhétorique du projet :
    ASSERTION → PARCE QUE → EXEMPLE → C'EST COMME → SO WHAT.
    """

    theme: str
    domaines_pemsi: list[DomainePEMSI]
    assertion: str       # L'idée claire et certaine (1-2 phrases)
    parce_que: str       # L'argument causal
    exemple: str         # Le fait concret / chiffre choc / précédent
    cest_comme: str      # L'analogie obligatoire — l'image mentale
    so_what: str         # Ce que ça change / la décision
