"""Pilote de bout en bout — test de l'Étape 3.

Enchaîne : collecte RSS → tri (Haiku) → regroupement thématique → extraction
du corps des articles retenus → analyse corrélée (Sonnet) → rendu au format brief.

Lancer : uv run python -m synthesia.pilote
"""

from __future__ import annotations

from synthesia.analyse.synthese import ArticleSource, analyser
from synthesia.analyse.tri import regrouper, trier
from synthesia.collecte.extraction import extraire
from synthesia.collecte.rss import collecter_tout

SEUIL_RETENU = 60  # score minimal de tri pour mériter une analyse


def rendre_brief(synthese, sources: list[str]) -> str:
    """Met une synthèse au format brief quotidien (dicible en 30 s)."""
    domaines = ", ".join(synthese.domaines_pemsi)
    return (
        f"🎯 {synthese.assertion}\n"
        f"   Parce que {synthese.parce_que}\n"
        f"   Exemple : {synthese.exemple}\n"
        f"   C'est comme {synthese.cest_comme}\n"
        f"   → So what : {synthese.so_what}\n"
        f"   📎 Sources : {', '.join(sorted(set(sources)))}  |  Domaines : {domaines}"
    )


def main() -> None:
    # 1. Collecte
    resultats = collecter_tout()
    articles = [a for liste in resultats.values() for a in liste]
    print(f"Collecte : {len(articles)} articles.")

    # 2. Tri (Haiku) sur les titres
    titres = [a.titre for a in articles]
    tri = trier(titres)
    retenus = sorted(
        [t for t in tri.articles if t.score >= SEUIL_RETENU],
        key=lambda t: t.score,
        reverse=True,
    )
    print(f"Tri : {len(retenus)} articles retenus (score >= {SEUIL_RETENU}).")
    for t in retenus[:10]:
        print(f"  [{t.score:3d}] {', '.join(t.domaines):30s} | {titres[t.index]}")

    if not retenus:
        print("Aucun article retenu — rien à analyser.")
        return

    # 3. Regroupement thématique des retenus
    idx_retenus = [t.index for t in retenus]
    titres_retenus = [titres[i] for i in idx_retenus]
    regroup = regrouper(titres_retenus)
    print(f"\nRegroupement : {len(regroup.clusters)} clusters.")
    for c in regroup.clusters:
        print(f"  • {c.theme} ({len(c.indices)} art.)")

    # 4. On prend le plus gros cluster (le sujet le plus couvert du jour)
    cluster = max(regroup.clusters, key=lambda c: len(c.indices))
    # indices du cluster -> index réels dans `articles` (max 3 pour le test)
    indices_reels = [idx_retenus[i] for i in cluster.indices][:3]
    print(f"\nCluster analysé : « {cluster.theme} » — {len(indices_reels)} article(s).")

    # 5. Extraction du corps des articles du cluster
    sources_synthese: list[ArticleSource] = []
    noms_sources: list[str] = []
    for i in indices_reels:
        art = articles[i]
        ext = extraire(art.url)
        if ext.ok and ext.texte:
            sources_synthese.append(
                ArticleSource(source=art.source, titre=art.titre, texte=ext.texte)
            )
            noms_sources.append(art.source)
            print(f"  extrait : {art.source} — {ext.nb_caracteres} c.")
        else:
            print(f"  ! extraction échouée : {art.url}")

    if not sources_synthese:
        print("Aucun corps d'article extrait — analyse impossible.")
        return

    # 6. Analyse corrélée (Sonnet) + rendu
    synthese = analyser(sources_synthese)
    print("\n" + "=" * 70)
    print("BRIEF DU JOUR")
    print("=" * 70)
    print(rendre_brief(synthese, noms_sources))


if __name__ == "__main__":
    main()
