"""Brief quotidien — Étape 5 : orchestration de bout en bout.

Enchaîne et PERSISTE toute la chaîne d'une journée :

  collecte → persistance articles → tri (Haiku) → maj scores/statuts
  → regroupement → (top clusters) extraction + analyse corrélée (Sonnet)
  → persistance synthèses + indexation vectorielle → élection de la fiche reine
  → rendu du brief.

Pour borner le coût, on ne synthétise que les `limite_clusters` clusters les
mieux notés (les plus couverts/importants du jour). Les autres sont signalés,
pas silencieusement ignorés.

Lancer : uv run python -m synthesia.brief.pipeline
"""

from __future__ import annotations

from dataclasses import dataclass

from synthesia.analyse.synthese import ArticleSource, analyser
from synthesia.analyse.tri import regrouper, trier
from synthesia.collecte.extraction import extraire
from synthesia.collecte.rss import collecter_tout
from synthesia.stockage import base, vecteurs

SEUIL_RETENU = 60        # score de tri minimal pour analyser un article
LIMITE_CLUSTERS = 3      # nb de clusters synthétisés (borne le coût Sonnet)
MAX_ART_PAR_CLUSTER = 3  # nb d'articles extraits par cluster


@dataclass
class SyntheseProduite:
    """Une synthèse fraîchement produite et persistée."""

    id: int
    record: base.SyntheseRecord
    sources: list[str]


def rendre_brief(rec: base.SyntheseRecord, sources: list[str]) -> str:
    """Met une synthèse au format brief quotidien (dicible en 30 s)."""
    domaines = ", ".join(rec.domaines)
    src = ", ".join(sorted(set(sources)))
    return (
        f"🎯 {rec.assertion}\n"
        f"   Parce que {rec.parce_que}\n"
        f"   Exemple : {rec.exemple}\n"
        f"   C'est comme {rec.cest_comme}\n"
        f"   → So what : {rec.so_what}\n"
        f"   📎 Sources : {src}  |  Domaines : {domaines}\n"
        f"   ⚠ Exemple & analogie à recouper avant diffusion."
    )


def executer_brief(
    *,
    seuil: int = SEUIL_RETENU,
    limite_clusters: int = LIMITE_CLUSTERS,
    max_art: int = MAX_ART_PAR_CLUSTER,
) -> list[SyntheseProduite]:
    """Exécute le pipeline complet d'une journée. Renvoie les synthèses produites."""
    conn = vecteurs.get_connection()
    base.init_db(conn)
    vecteurs.init_vec(conn)

    # 1. Collecte + persistance des articles bruts (dédup par URL).
    collecte = collecter_tout()
    articles = [a for liste in collecte.values() for a in liste]
    db_ids = [
        base.inserer_article(
            conn, source=a.source, url=a.url, titre=a.titre, langue=a.langue,
            date_publication=a.date_publication.isoformat() if a.date_publication else None,
        )
        for a in articles
    ]
    print(f"Collecte : {len(articles)} articles persistés.")

    # 2. Tri (Haiku) + mise à jour des scores/domaines/statuts en base.
    titres = [a.titre for a in articles]
    tri = {t.index: t for t in trier(titres).articles}
    for idx, t in tri.items():
        if idx >= len(db_ids):
            continue
        statut = "retenu" if t.score >= seuil else "ecarte"
        base.maj_article(
            conn, db_ids[idx], score_tri=t.score,
            domaines=list(t.domaines), statut=statut,
        )
    retenus = [i for i, t in tri.items() if t.score >= seuil and i < len(db_ids)]
    print(f"Tri : {len(retenus)}/{len(articles)} articles retenus (score >= {seuil}).")
    if not retenus:
        print("Aucun article retenu — pas de brief aujourd'hui.")
        return []

    # 3. Regroupement thématique des retenus.
    titres_retenus = [titres[i] for i in retenus]
    clusters = regrouper(titres_retenus).clusters

    # 4. Score de cluster = meilleur score de tri parmi ses articles. On classe.
    classes = []
    for c in clusters:
        idx_reels = [retenus[j] for j in c.indices if j < len(retenus)]
        if not idx_reels:
            continue
        score = max(tri[i].score for i in idx_reels)
        classes.append((c, idx_reels, score))
    classes.sort(key=lambda x: x[2], reverse=True)

    a_traiter = classes[:limite_clusters]
    ignores = classes[limite_clusters:]
    print(f"Regroupement : {len(classes)} clusters ; {len(a_traiter)} synthétisés.")
    if ignores:
        print(f"  (non synthétisés ce tour : {', '.join(c.theme for c, _, _ in ignores)})")

    # 5. Pour chaque cluster retenu : extraction → analyse → persistance + index.
    produites: list[SyntheseProduite] = []
    for cluster, idx_reels, score in a_traiter:
        sources_art: list[ArticleSource] = []
        ids_art: list[int] = []
        for i in idx_reels[:max_art]:
            art = articles[i]
            ext = extraire(art.url)
            if ext.ok and ext.texte:
                base.maj_article(conn, db_ids[i], corps=ext.texte, statut="analyse")
                sources_art.append(ArticleSource(art.source, art.titre, ext.texte))
                ids_art.append(db_ids[i])
        if not sources_art:
            print(f"  ! « {cluster.theme} » : aucun corps extrait, sauté.")
            continue

        synth = analyser(sources_art)
        rec = base.SyntheseRecord(
            theme=synth.theme, assertion=synth.assertion, parce_que=synth.parce_que,
            exemple=synth.exemple, cest_comme=synth.cest_comme, so_what=synth.so_what,
            domaines=list(synth.domaines_pemsi), score=score,
        )
        sid = base.inserer_synthese(conn, rec, ids_art)
        vecteurs.indexer_synthese(conn, sid, vecteurs.texte_synthese(rec))
        produites.append(SyntheseProduite(sid, rec, [s.source for s in sources_art]))
        print(f"  ✓ synthèse #{sid} [{score}] « {synth.theme} »")

    # 6. Élection de la fiche reine + rendu.
    if produites:
        reine = max(produites, key=lambda p: p.record.score)
        print("\n" + "=" * 70)
        print("BRIEF DU JOUR")
        print("=" * 70)
        print(rendre_brief(reine.record, reine.sources))

    conn.close()
    return produites


if __name__ == "__main__":
    executer_brief()
