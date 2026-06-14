"""Collecte RSS — Étape 1.

Lit les flux RSS définis dans config/sources.toml et renvoie la liste
des articles repérés (titre, lien, date, source). Aucun LLM, aucune base :
on vérifie seulement qu'on capte bien la matière première.
"""

from __future__ import annotations

import tomli
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import feedparser

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "sources.toml"

# Certains sites (RAND, La Tribune) bloquent le user-agent par défaut de
# feedparser. On se présente comme un navigateur.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


@dataclass
class ArticleBrut:
    """Une entrée de flux RSS, avant tout traitement."""

    source: str
    langue: str
    titre: str
    url: str
    date_publication: datetime | None


def charger_sources(config_path: Path = CONFIG_PATH) -> list[dict]:
    """Charge les sources actives depuis le fichier TOML."""
    with open(config_path, "rb") as f:
        data = tomli.load(f)
    return [s for s in data.get("sources", []) if s.get("active", True)]


def _parse_date(entry) -> datetime | None:
    """Extrait une date de publication exploitable, sinon None."""
    parsed = getattr(entry, "published_parsed", None) or getattr(
        entry, "updated_parsed", None
    )
    if parsed is None:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


def collecter_source(source: dict) -> list[ArticleBrut]:
    """Lit un flux RSS et renvoie ses articles. Tolérant aux pannes."""
    flux = feedparser.parse(source["url"], agent=USER_AGENT)
    articles: list[ArticleBrut] = []
    for entry in flux.entries:
        articles.append(
            ArticleBrut(
                source=source["nom"],
                langue=source.get("langue", "?"),
                titre=getattr(entry, "title", "(sans titre)"),
                url=getattr(entry, "link", ""),
                date_publication=_parse_date(entry),
            )
        )
    return articles


def collecter_tout(config_path: Path = CONFIG_PATH) -> dict[str, list[ArticleBrut]]:
    """Collecte toutes les sources actives. Renvoie {nom_source: [articles]}.

    Une source en échec (URL morte, flux invalide) renvoie une liste vide
    plutôt que de faire planter l'ensemble.
    """
    resultats: dict[str, list[ArticleBrut]] = {}
    for source in charger_sources(config_path):
        try:
            resultats[source["nom"]] = collecter_source(source)
        except Exception as exc:  # collecte robuste : on n'interrompt pas
            print(f"  ! Échec collecte {source['nom']}: {exc}")
            resultats[source["nom"]] = []
    return resultats


def afficher(resultats: dict[str, list[ArticleBrut]], max_par_source: int = 5) -> None:
    """Affiche un aperçu au terminal : titres + liens, par source."""
    total = sum(len(v) for v in resultats.values())
    print(f"\n=== Collecte RSS — {total} articles repérés ===\n")
    for nom, articles in resultats.items():
        statut = f"{len(articles)} articles" if articles else "AUCUN (à vérifier)"
        print(f"## {nom} — {statut}")
        for a in articles[:max_par_source]:
            date = a.date_publication.strftime("%Y-%m-%d") if a.date_publication else "????-??-??"
            print(f"  [{date}] {a.titre}")
            print(f"          {a.url}")
        if len(articles) > max_par_source:
            print(f"  ... (+{len(articles) - max_par_source} autres)")
        print()


def main() -> None:
    afficher(collecter_tout())


if __name__ == "__main__":
    main()
