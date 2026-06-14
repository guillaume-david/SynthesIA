"""Persistance vectorielle — Étape 4b : sqlite-vec + embeddings locaux.

Recherche par sens : retrouver une synthèse par son idée, pas par ses mots
exacts ; corréler événements actuels et passés. Les embeddings sont calculés
EN LOCAL (fastembed, modèle multilingue léger) — aucune donnée ne sort de la
machine, aucune clé, aucun coût (OPSEC).

Les vecteurs vivent dans une table virtuelle sqlite-vec (`vec_synthese`),
séparée des tables relationnelles, jointe par l'id de synthèse.
"""

from __future__ import annotations

import sqlite3
import warnings
from functools import lru_cache
from pathlib import Path

import sqlite_vec

# Le mean-pooling est le comportement standard de ce modèle ; on tait l'avis.
warnings.filterwarnings("ignore", message=".*mean pooling.*")
from fastembed import TextEmbedding  # noqa: E402

from . import base

# Modèle d'embedding : multilingue (FR+EN), léger (0.22 Go, 384 dim).
MODELE_EMBED = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM = 384

SCHEMA_VEC = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS vec_synthese USING vec0(
    synthese_id INTEGER PRIMARY KEY,
    embedding FLOAT[{DIM}]
);
"""


@lru_cache(maxsize=1)
def _modele() -> TextEmbedding:
    """Charge le modèle une seule fois (téléchargé au 1er appel, puis caché)."""
    return TextEmbedding(model_name=MODELE_EMBED)


def embed(texte: str) -> list[float]:
    """Transforme un texte en vecteur (liste de 384 floats)."""
    return next(iter(_modele().embed([texte]))).tolist()


def texte_synthese(synthese: sqlite3.Row | base.SyntheseRecord) -> str:
    """Construit le texte représentatif d'une synthèse à vectoriser.

    On concatène l'essence sémantique : thème + assertion + argument + analogie.
    """
    if isinstance(synthese, base.SyntheseRecord):
        champs = (synthese.theme, synthese.assertion, synthese.parce_que,
                  synthese.cest_comme)
    else:
        champs = (synthese["theme"], synthese["assertion"],
                  synthese["parce_que"], synthese["cest_comme"])
    return " — ".join(c for c in champs if c)


def get_connection(db_path: Path = base.DB_PATH) -> sqlite3.Connection:
    """Connexion avec l'extension sqlite-vec chargée."""
    conn = base.get_connection(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def init_vec(conn: sqlite3.Connection) -> None:
    """Crée la table virtuelle vectorielle. Idempotent."""
    conn.executescript(SCHEMA_VEC)
    conn.commit()


def indexer_synthese(
    conn: sqlite3.Connection, synthese_id: int, texte: str
) -> None:
    """Calcule et stocke l'embedding d'une synthèse (remplace s'il existe)."""
    vecteur = sqlite_vec.serialize_float32(embed(texte))
    conn.execute(
        "INSERT OR REPLACE INTO vec_synthese (synthese_id, embedding) VALUES (?, ?)",
        (synthese_id, vecteur),
    )
    conn.commit()


def rechercher(
    conn: sqlite3.Connection, requete: str, k: int = 5
) -> list[tuple[sqlite3.Row, float]]:
    """Recherche les k synthèses les plus proches du sens de `requete`.

    Renvoie une liste de (ligne synthèse, distance) triée du plus proche au
    plus lointain (distance faible = plus pertinent).
    """
    vecteur = sqlite_vec.serialize_float32(embed(requete))
    proches = conn.execute(
        """
        SELECT synthese_id, distance FROM vec_synthese
        WHERE embedding MATCH ? AND k = ?
        ORDER BY distance
        """,
        (vecteur, k),
    ).fetchall()
    resultats: list[tuple[sqlite3.Row, float]] = []
    for row in proches:
        synth = base.get_synthese(conn, row["synthese_id"])
        if synth is not None:
            resultats.append((synth, row["distance"]))
    return resultats
