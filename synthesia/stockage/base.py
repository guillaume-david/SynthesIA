"""Persistance — Étape 4a : tables relationnelles (SQLite pur).

Un seul fichier de base : data/synthesia.db (git-ignoré). Deux niveaux,
conformes au modèle de données (cf. docs/plan-implementation.md §4) :

  - article  : 1 par lien collecté (dédupliqué par URL).
  - synthese : produit analytique, agrégeant 1..N articles via une table
               de liaison synthese_article.

La couche vectorielle (sqlite-vec + embeddings) viendra en Étape 4b, dans
une table virtuelle séparée jointe par rowid — rien à changer ici.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "synthesia.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS article (
    id               INTEGER PRIMARY KEY,
    date_collecte    TEXT NOT NULL,
    date_publication TEXT,
    source           TEXT NOT NULL,
    url              TEXT NOT NULL UNIQUE,   -- dédup : un lien = un seul article
    langue           TEXT,
    titre            TEXT NOT NULL,
    corps            TEXT,                   -- rempli si l'article est retenu
    domaines         TEXT,                   -- JSON : liste de domaines PEMSI
    score_tri        INTEGER,
    statut           TEXT NOT NULL DEFAULT 'nouveau'  -- nouveau/retenu/ecarte/analyse
);

CREATE TABLE IF NOT EXISTS synthese (
    id        INTEGER PRIMARY KEY,
    date      TEXT NOT NULL,
    theme     TEXT NOT NULL,
    domaines  TEXT,            -- JSON : liste de domaines PEMSI
    assertion TEXT NOT NULL,
    parce_que TEXT NOT NULL,
    exemple   TEXT NOT NULL,
    cest_comme TEXT NOT NULL,
    so_what   TEXT NOT NULL,
    score     INTEGER DEFAULT 0,
    statut    TEXT NOT NULL DEFAULT 'nouveau'  -- nouveau/lu/archive
);

-- Liaison N..N : une synthèse agrège plusieurs articles ; un article peut
-- nourrir plusieurs synthèses.
CREATE TABLE IF NOT EXISTS synthese_article (
    synthese_id INTEGER NOT NULL REFERENCES synthese(id) ON DELETE CASCADE,
    article_id  INTEGER NOT NULL REFERENCES article(id)  ON DELETE CASCADE,
    PRIMARY KEY (synthese_id, article_id)
);

CREATE INDEX IF NOT EXISTS idx_article_statut  ON article(statut);
CREATE INDEX IF NOT EXISTS idx_synthese_date   ON synthese(date);
"""


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Ouvre la base, active les clés étrangères, renvoie des lignes nommées."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Crée les tables si elles n'existent pas. Idempotent."""
    conn.executescript(SCHEMA)
    conn.commit()


# --------------------------------------------------------------------------- #
#  Articles
# --------------------------------------------------------------------------- #

def inserer_article(
    conn: sqlite3.Connection,
    *,
    source: str,
    url: str,
    titre: str,
    langue: str | None = None,
    date_publication: str | None = None,
    corps: str | None = None,
    domaines: list[str] | None = None,
    score_tri: int | None = None,
    statut: str = "nouveau",
) -> int:
    """Insère un article (ou le retrouve s'il existe déjà, par URL).

    Renvoie l'id. Dédup : ré-collecter le même lien ne crée pas de doublon.
    """
    cur = conn.execute(
        """
        INSERT INTO article
            (date_collecte, date_publication, source, url, langue,
             titre, corps, domaines, score_tri, statut)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO NOTHING
        """,
        (
            _maintenant(), date_publication, source, url, langue,
            titre, corps, json.dumps(domaines or []), score_tri, statut,
        ),
    )
    conn.commit()
    if cur.lastrowid and cur.rowcount:
        return cur.lastrowid
    # Conflit (URL déjà présente) : on récupère l'id existant.
    row = conn.execute("SELECT id FROM article WHERE url = ?", (url,)).fetchone()
    return row["id"]


def maj_article(
    conn: sqlite3.Connection,
    article_id: int,
    *,
    corps: str | None = None,
    domaines: list[str] | None = None,
    score_tri: int | None = None,
    statut: str | None = None,
) -> None:
    """Met à jour les champs renseignés d'un article (les None sont ignorés)."""
    champs, valeurs = [], []
    if corps is not None:
        champs.append("corps = ?"); valeurs.append(corps)
    if domaines is not None:
        champs.append("domaines = ?"); valeurs.append(json.dumps(domaines))
    if score_tri is not None:
        champs.append("score_tri = ?"); valeurs.append(score_tri)
    if statut is not None:
        champs.append("statut = ?"); valeurs.append(statut)
    if not champs:
        return
    valeurs.append(article_id)
    conn.execute(f"UPDATE article SET {', '.join(champs)} WHERE id = ?", valeurs)
    conn.commit()


def get_article(conn: sqlite3.Connection, article_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM article WHERE id = ?", (article_id,)).fetchone()


def lister_articles(
    conn: sqlite3.Connection, statut: str | None = None
) -> list[sqlite3.Row]:
    if statut:
        return conn.execute(
            "SELECT * FROM article WHERE statut = ? ORDER BY date_collecte DESC",
            (statut,),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM article ORDER BY date_collecte DESC"
    ).fetchall()


# --------------------------------------------------------------------------- #
#  Synthèses
# --------------------------------------------------------------------------- #

@dataclass
class SyntheseRecord:
    """Données d'une synthèse à persister (miroir du schéma Pydantic Synthese)."""

    theme: str
    assertion: str
    parce_que: str
    exemple: str
    cest_comme: str
    so_what: str
    domaines: list[str] = field(default_factory=list)
    score: int = 0
    date: str | None = None


def inserer_synthese(
    conn: sqlite3.Connection,
    synthese: SyntheseRecord,
    article_ids: list[int],
) -> int:
    """Insère une synthèse et la relie à ses articles sources. Renvoie l'id."""
    cur = conn.execute(
        """
        INSERT INTO synthese
            (date, theme, domaines, assertion, parce_que, exemple,
             cest_comme, so_what, score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            synthese.date or _maintenant(), synthese.theme,
            json.dumps(synthese.domaines), synthese.assertion,
            synthese.parce_que, synthese.exemple, synthese.cest_comme,
            synthese.so_what, synthese.score,
        ),
    )
    synthese_id = cur.lastrowid
    conn.executemany(
        "INSERT OR IGNORE INTO synthese_article (synthese_id, article_id) VALUES (?, ?)",
        [(synthese_id, aid) for aid in article_ids],
    )
    conn.commit()
    return synthese_id


def get_synthese(conn: sqlite3.Connection, synthese_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM synthese WHERE id = ?", (synthese_id,)
    ).fetchone()


def articles_de_synthese(
    conn: sqlite3.Connection, synthese_id: int
) -> list[sqlite3.Row]:
    """Renvoie les articles sources d'une synthèse (pour citer les sources)."""
    return conn.execute(
        """
        SELECT a.* FROM article a
        JOIN synthese_article sa ON sa.article_id = a.id
        WHERE sa.synthese_id = ?
        """,
        (synthese_id,),
    ).fetchall()


def lister_syntheses(
    conn: sqlite3.Connection, date: str | None = None
) -> list[sqlite3.Row]:
    if date:  # filtre sur le préfixe AAAA-MM-JJ
        return conn.execute(
            "SELECT * FROM synthese WHERE date LIKE ? ORDER BY score DESC",
            (f"{date}%",),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM synthese ORDER BY date DESC, score DESC"
    ).fetchall()


def archiver_synthese(conn: sqlite3.Connection, synthese_id: int) -> None:
    conn.execute(
        "UPDATE synthese SET statut = 'archive' WHERE id = ?", (synthese_id,)
    )
    conn.commit()
