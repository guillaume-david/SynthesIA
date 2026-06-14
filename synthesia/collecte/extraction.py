"""Extraction du corps d'article — Étape 2.

Depuis une URL, télécharge la page (avec un user-agent navigateur, car
certaines sources bloquent les robots) et isole le texte de l'article,
débarrassé des menus, pubs, pieds de page et autres scories.

On sépare volontairement deux responsabilités :
  - telecharger() : I/O réseau (peut échouer, peut être lent)
  - extraire_texte() : traitement pur du HTML (testable hors-ligne)
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import trafilatura

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TIMEOUT = httpx.Timeout(20.0)


@dataclass
class Extraction:
    """Résultat d'extraction pour une URL."""

    url: str
    titre: str | None
    texte: str | None
    nb_caracteres: int
    ok: bool
    erreur: str | None = None


def telecharger(url: str) -> str | None:
    """Récupère le HTML brut d'une URL. Renvoie None en cas d'échec."""
    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            follow_redirects=True,
        ) as client:
            reponse = client.get(url)
            reponse.raise_for_status()
            return reponse.text
    except Exception:
        return None


def extraire_texte(html: str) -> tuple[str | None, str | None]:
    """Isole (titre, corps) d'un article à partir du HTML. Traitement pur.

    trafilatura retire automatiquement navigation, pubs, commentaires.
    Renvoie (None, None) si rien d'exploitable n'est trouvé.
    """
    texte = trafilatura.extract(
        html,
        favor_precision=True,   # privilégie un texte propre, quitte à couper
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )
    titre = None
    meta = trafilatura.extract_metadata(html)
    if meta is not None:
        titre = meta.title
    return titre, texte


def extraire(url: str) -> Extraction:
    """Pipeline complet pour une URL : télécharge puis extrait."""
    html = telecharger(url)
    if html is None:
        return Extraction(url, None, None, 0, ok=False, erreur="téléchargement échoué")

    titre, texte = extraire_texte(html)
    if not texte:
        return Extraction(url, titre, None, 0, ok=False, erreur="extraction vide")

    return Extraction(url, titre, texte, len(texte), ok=True)


def main() -> None:
    """Test manuel : extrait quelques URLs représentatives des sources."""
    urls = [
        "https://www.opex360.com/2026/06/13/la-pologne-a-lintention-dacquerir-trente-deux-chasseurs-bombardiers-f-35a-supplementaires/",
        "https://www.iris-france.org/un-g7-pour-quoi-faire/",
        "https://www.rand.org/pubs/commentary/2026/06/how-china-misperceives-itself.html",
    ]
    for url in urls:
        res = extraire(url)
        print(f"\n=== {url}")
        if res.ok:
            print(f"  titre : {res.titre}")
            print(f"  taille: {res.nb_caracteres} caractères")
            print(f"  extrait:\n    {res.texte[:300].strip()}...")
        else:
            print(f"  ÉCHEC : {res.erreur}")


if __name__ == "__main__":
    main()
