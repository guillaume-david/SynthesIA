# SynthesIA — Plan d'implémentation

> Veille stratégique automatisée (OSINT) sur les domaines **PEMSI**
> (Politique, Militaire, Économique, Société, Science/Techno militaire, Géopolitique).
>
> **Objectif fondateur** : produire chaque jour **une idée claire, certaine et dicible en 30 secondes** à un chef.
> Format pivot : **ASSERTION → PARCE QUE → EXEMPLE → C'EST COMME**.

Statut : *en construction itérative — une étape validée à la fois.*
Dernière mise à jour : 2026-06-14.

---

## 1. Principes directeurs

1. **Léger d'abord.** Un seul dossier, un seul fichier base de données. On ne scale (Postgres, conteneurs) que quand la douleur l'exige.
2. **Itératif et testable.** Chaque étape produit une brique vérifiable seule, sans dépendre de la suivante.
3. **OPSEC.** Projet perso d'un officier → aucune exposition directe sur Internet. Accès distant via VPN privé.
4. **Le LLM sert le raisonnement, pas l'inverse.** La structure de sortie est imposée (formule ci-dessus), pas négociable par le modèle.
5. **Économie de tokens.** Tri en 2 passes : on ne paie le texte intégral que pour ce qui mérite analyse.

---

## 2. Stack technique (validée)

| Pièce | Outil | Rôle |
|---|---|---|
| Langage | **Python 3.10** | Cf. `.python-version` |
| Gestion deps / env | **uv** | Déjà initialisé (`pyproject.toml`) |
| Lecture RSS | **feedparser** | Sommaire automatique des sources |
| Téléchargement HTML | **httpx** (async) | Récupère le corps des articles |
| Extraction texte | **selectolax** ou **trafilatura** | Isole le texte utile du HTML |
| LLM | **API Anthropic** | Tri + synthèse |
| → Tri (passe 1) | **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) | Rapide, peu cher, sur titres seuls |
| → Synthèse (passe 2) | **Claude Sonnet 4.6** (`claude-sonnet-4-6`) | Qualité d'analyse sur texte complet |
| Base de données | **SQLite + sqlite-vec** | Fichier unique + recherche vectorielle |
| API web | **FastAPI + Uvicorn** | Consultation mobile |
| Planification | **cron** (WSL) | Déclenche collecte 6h30 / 13h30 |
| Accès distant | **Tailscale** (ou Wireguard) | VPN privé, zéro port ouvert sur Internet |

> Clé API : variable d'environnement `ANTHROPIC_API_KEY` (cf. `docs/memo.md`). Jamais en dur dans le code.

---

## 3. Sources de collecte (amorçage)

| Source | Langue | Type | Flux RSS (vérifié 2026-06-14) |
|---|---|---|---|
| Opex360 | FR | Presse défense | ✅ `https://www.opex360.com/feed/` |
| IRIS | FR | Think tank | ✅ `https://www.iris-france.org/feed/` |
| RAND Corporation | EN | Think tank | ✅ `https://www.rand.org/pubs/commentary.xml` |
| La Tribune | FR | Presse généraliste/éco | ✅ `https://www.latribune.fr/rss/homepage` (filtrer le bruit) |
| Meta-Defense.fr | FR | Presse défense | ❌ RSS coupé (HTTP 410). Scraping requis. |
| FRS | FR | Think tank | ⚠️ Inaccessible depuis WSL (TLS). À revérifier en prod. |

> Langues d'entrée : FR + EN. **Synthèse toujours produite en français.**
> RAND/La Tribune exigent un user-agent navigateur (sinon blocage). Réglé dans `collecte/rss.py`.

**Cadence de collecte** : 06h30 et 13h30. Volume estimé : 10–50 articles/jour.

---

## 4. Schéma de données

> **Deux niveaux distincts.** L'`article` est la matière brute (1 par lien collecté).
> La `synthese` est le produit analytique : elle peut **agréger plusieurs articles**
> d'un même thème en **une seule idée corrélée**. Une synthèse n'est pas le résumé
> d'un article — c'est une analyse transversale de la journée.

### 4.1 ARTICLE — matière première (1 lien collecté = 1 article)

| Champ | Contenu |
|---|---|
| `id` | Identifiant unique |
| `date_collecte` | Horodatage de capture |
| `date_publication` | Date de l'article |
| `source` | Nom de la source |
| `url` | Lien original |
| `langue_source` | FR / EN |
| `titre` | Titre original |
| `corps` | Texte intégral nettoyé (rempli en passe 2 si retenu) |
| `domaine_pemsi` | Un ou **plusieurs** domaines |
| `mots_cles` | 3–5 entités / concepts |
| `embedding` | Vecteur (recherche par sens, invisible) |
| `score_tri` | Note de la passe 1 (0–100) |
| `statut` | nouveau / retenu / écarté / analysé |

### 4.2 SYNTHÈSE — produit analytique (1..N articles → 1 idée)

| Champ | Contenu |
|---|---|
| `id` | Identifiant unique |
| `date` | Jour de production |
| `theme` | Le sujet corrélé (ex. « Posture russe au Sahel ») |
| `domaine_pemsi` | Un ou **plusieurs** domaines |
| `article_ids` | **Liste** des articles sources (1..N) → traçabilité & citation |
| `embedding` | Vecteur de la synthèse (liens transversaux historiques) |
| `score` | Importance (pour élire le brief du jour) |
| **— Cœur analytique (formule) —** | |
| `assertion` | L'idée claire et certaine |
| `parce_que` | L'argument causal |
| `exemple` | Le fait concret / chiffre choc / précédent |
| `cest_comme` | L'analogie — **obligatoire, jamais vide** |
| `so_what` | Ce que ça change / la décision |

> Les sources citées dans le rendu sont dérivées de `article_ids` (source + url de chacun).

### 4.3 LE BRIEF DU JOUR — livrable

Chaque jour, sélection de **la synthèse reine** (meilleur `score`), rendue ainsi :

```
🎯 [ASSERTION]
   Parce que [argument].
   Exemple : [fait choc].
   C'est comme [image mentale].
   → So what : [impact].
   📎 Sources : RAND, Opex360.
```

Lisible en 15 s sur mobile. Dicible en 30 s à un chef.

---

## 5. Prompts LLM

### Passe 1 — Tri (Haiku)
Entrée : liste de titres + chapôs du jour.
Sortie : pour chaque article, `score_tri` (0–100) + domaines PEMSI pressentis.
But : ne récupérer le texte complet que des articles à fort score.

### Passe 1bis — Regroupement thématique (Haiku, optionnel)
Entrée : les articles retenus de la journée.
Sortie : regroupement en **clusters thématiques** (un cluster = 1..N articles parlant du même sujet).
But : permettre à la passe 2 de corréler plutôt que de résumer pièce par pièce.

### Passe 2 — Mode A : analyse corrélée (Sonnet)
> *« Agis comme un analyste de recherche interarmées senior. On te fournit **un ou plusieurs articles**
> portant sur un même thème. Ne résume pas chaque article : produis **une seule analyse corrélée**
> qui croise les sources, fait ressortir l'essentiel et tranche. Structure :*
> 1. *L'idée importante (1–2 phrases, clarté maximale) → `assertion`*
> 2. *Pourquoi (argument causal) → `parce_que`*
> 3. *Insights clés / conséquences à 6 mois, menaces & opportunités → `so_what`*
> 4. *Exemple choc / parallèle historique obligatoire → `exemple` + `cest_comme`*
> *Cite les sources mobilisées. Style soutenu, concis, direct, neutre. Pas de fioritures. En français. »*

### Mode B — requêtes transversales sur la base (Sonnet)
> *« À partir des fiches stockées et d'une question transversale : clarifier l'idée centrale, hiérarchiser les faits, identifier les pièces manquantes (hypothèses implicites, données absentes), proposer une version actionnable avec prochaines étapes. »*

> Exploite la recherche vectorielle (`embedding`) pour relier événements actuels et passés.

---

## 6. Étapes de développement

| Étape | Objet | Livrable testable | Statut |
|---|---|---|---|
| **0** | Schéma de la fiche + format du brief | Ce document | ✅ Validé |
| **1** | Collecte RSS | Script qui lit les flux et affiche titres + liens au terminal. **Sans LLM, sans base.** | ✅ Fait (4 sources, 60 articles) |
| **2** | Extraction du corps d'article | Récupérer et nettoyer le texte d'un article depuis son URL | ✅ Fait (httpx + trafilatura, 4 sources OK) |
| **3** | Intégration LLM | Tri (passe 1) → regroupement thématique → analyse corrélée **multi-articles** (Mode A) | ✅ Fait (pipeline réel testé : Haiku + Sonnet, sorties structurées) |
| **4a** | Persistance relationnelle | SQLite pur : tables `article` + `synthese` + liaison, insérer, dédupliquer, archiver | ✅ Fait (testé) |
| **4b** | Persistance vectorielle | sqlite-vec + embeddings locaux (fastembed, multilingue 384d) : recherche par sens | ✅ Fait (testé) |
| **5** | Brief quotidien | Orchestration complète + persistance + élection de la synthèse reine + rendu | ✅ Fait (pipeline réel persisté) |
| **6** | API FastAPI | Page web mobile (brief reine + synthèses du jour + détail) + point JSON | ✅ Fait (Mode B/recherche : plus tard) |
| **7** | Planification | Planificateur DSM 6h30 / 13h30 (`docker exec`) | 🟡 Préparé (guide Synology) — à exécuter sur le NAS |
| **8** | Accès distant sécurisé | Tailscale (paquet Synology), zéro port exposé | 🟡 Préparé (guide Synology) — à exécuter sur le NAS |

**Déploiement Synology DS224+** : `Dockerfile`, `docker-compose.yml`, `.dockerignore` +
guide pas-à-pas `docs/deploiement-synology.md`. Code rendu résilient pour conteneur
(bascule `pysqlite3` si extensions SQLite désactivées ; cache du modèle d'embedding
persisté dans le volume `data/`).

> Ordre de test : valider le prompt LLM (Étape 3) **avant** d'industrialiser la collecte complète.

---

## 7. Arborescence cible (indicative)

```
SynthesIA/
├── docs/
│   ├── plan-implementation.md   ← ce fichier
│   ├── target.md                ← brief initial
│   └── memo.md                  ← clé API & liens
├── synthesia/
│   ├── collecte/                ← RSS + extraction (Étapes 1-2)
│   ├── analyse/                 ← tri, regroupement, prompts & appels LLM (Étape 3)
│   ├── stockage/                ← SQLite + sqlite-vec (Étape 4)
│   ├── brief/                   ← sélection & rendu (Étape 5)
│   └── api/                     ← FastAPI (Étape 6)
├── data/
│   └── synthesia.db             ← base SQLite (git-ignorée)
├── config/
│   └── sources.toml             ← liste des flux RSS
├── pyproject.toml
└── main.py
```

> Arborescence créée progressivement, étape par étape — pas d'un coup.

---

## 8. Sécurité / OPSEC

- Clé API en variable d'environnement, jamais commitée.
- `data/` (fiches, base) git-ignorée.
- Accès mobile **uniquement** via VPN privé (Tailscale) — aucun port exposé sur Internet.
- À terme si besoin web public : reverse-proxy + authentification forte. À trancher le moment venu.
