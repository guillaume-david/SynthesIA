# SynthesIA — Prompt de contexte

> **À lire en premier.** Ce document embarque n'importe quel LLM vierge de contexte
> sur le projet SynthesIA : but, philosophie, architecture, **détail de chaque fichier**,
> état d'avancement, et comment reprendre le travail. Lis-le entièrement avant d'agir.
> La source de vérité du plan reste `docs/plan-implementation.md`.

---

## 1. Qui et pourquoi

Le porteur du projet est un **officier supérieur de l'armée de Terre** (sapeur-pompier
de Paris, employé au pilotage des données à la SIMMT). Projet **personnel**, sur temps
perso. Objectif assumé : **« s'augmenter » comme officier d'état-major**.

Le besoin tient en une phrase : **avoir chaque jour UNE idée claire et certaine**,
percutante, dicible à un chef en 30 secondes — du type :

> « L'Ukraine est dans telle situation **PARCE QUE** [argument] … **EXEMPLE** [fait] …
> d'ailleurs **C'EST COMME** [analogie historique ou parallèle quelconque (jusqu'à image mentale)]. »

Cette structure rhétorique est **la colonne vertébrale de tout le projet**. Tout sert
à la produire. On la retrouve telle quelle dans les champs de la table `synthese` :
`assertion / parce_que / exemple / cest_comme / so_what`.

---

## 2. Ce que fait SynthesIA

Veille stratégique automatisée (OSINT) sur les domaines **PEMSI** : **P**olitique,
**M**ilitaire, **É**conomique, **S**ociété, **Sc**ience/Technologie à vocation
militaire, **G**éopolitique.

Chaîne de traitement d'une journée (toute orchestrée par `brief/pipeline.py`) :

```
Collecte RSS → persistance articles → Tri (Haiku) → maj scores/statuts
→ Regroupement thématique → (top clusters) Extraction du corps → Analyse corrélée (Sonnet)
→ persistance synthèses + indexation vectorielle → Élection de la « fiche reine »
→ Brief : affiché (web), et ENVOYÉ PAR EMAIL (canal quotidien principal)
```

Déclenchement prévu : **2× par jour** (06h30, 13h30 — Étape 7, pas encore faite).
Accès final visé : **serveur perso, consultable sur mobile** (API faite, Étape 6),
via VPN privé (Étape 8, pas encore faite ; OPSEC : pas d'exposition Internet).

---

## 3. Principes directeurs (à respecter absolument)

1. **Léger d'abord.** Un seul dossier, un seul fichier de base. On ne scale (Postgres,
   conteneurs) que quand la douleur l'exige.
2. **Itératif et testable.** Une étape = une brique vérifiable seule. **Le porteur valide
   à chaque palier — ne JAMAIS tout générer d'un coup.** Proposer → faire valider →
   exécuter une étape → vérifier.
3. **OPSEC.** Aucune exposition directe sur Internet. Embeddings calculés en local.
   Accès distant via VPN (Tailscale).
4. **Le LLM sert le raisonnement, pas l'inverse.** Le format de sortie est imposé
   (la formule §1), non négociable par le modèle. Garanti par Pydantic + `messages.parse()`.
5. **Économie de tokens.** Tri en 2 passes : on ne paie le texte intégral que pour ce
   qui mérite analyse. On ne synthétise que les meilleurs clusters.
6. **Pas de troncature silencieuse.** Si on borne (top N clusters), on **liste** ce qui
   est laissé de côté.
7. **Style de travail attendu :** réponses concises, phrases courtes, arguments clés,
   droit au but. Pas de fioritures.

---

## 4. Stack technique

| Pièce | Outil | Rôle |
|---|---|---|
| Langage | **Python 3.10** (cf. `.python-version`) | — |
| Env / deps | **uv** | `uv add ...`, `uv run ...` |
| Lecture RSS | **feedparser** | flux des sources |
| Téléchargement HTML | **httpx** | corps des articles |
| Extraction texte | **trafilatura** | isole l'article du HTML (menus/pubs retirés) |
| LLM | **SDK `anthropic`** | tri + synthèse |
| → Tri | **`claude-haiku-4-5`** | rapide, peu cher, sur titres |
| → Synthèse | **`claude-sonnet-4-6`** | analyse corrélée fine |
| Sorties LLM | **Pydantic + `messages.parse()`** | format garanti, zéro parsing fragile |
| Base relationnelle | **SQLite** (stdlib `sqlite3`) | fichier unique `data/synthesia.db` |
| Base vectorielle | **sqlite-vec** | table virtuelle de vecteurs, recherche par sens |
| Embeddings | **fastembed** (local) | modèle multilingue 384d, 0.22 Go, aucune donnée ne sort |
| API web | **FastAPI + Uvicorn** | consultation mobile |
| Config TOML | **tomli** (3.10 n'a pas `tomllib`) | lecture `sources.toml` |

**Clé API** : dans `.env` à la racine (variable `ANTHROPIC_API_KEY`), **git-ignoré**.
Jamais en dur. Chargée via `python-dotenv`. Modèle de format : `.env.example`.

---

## 5. Modèle de données (2 niveaux distincts)

> Détail des champs : `docs/plan-implementation.md` §4. Schéma SQL réel : `stockage/base.py`.

- **`article`** : la matière brute, **1 par lien collecté**, **dédupliqué par URL**.
  Champs : `id, date_collecte, date_publication, source, url, langue, titre, corps,
  domaines (JSON), score_tri, statut`. Statut : `nouveau → retenu/ecarte → analyse`.
- **`synthese`** : le produit analytique. Peut **agréger 1..N articles** d'un même thème
  en **une seule idée corrélée**. Champs : `id, date, theme, domaines (JSON), assertion,
  parce_que, exemple, cest_comme, so_what, score, statut`. Une synthèse **corrèle**, elle
  ne résume pas.
- **`synthese_article`** : table de liaison **N..N** (une synthèse cite ses 1..N articles ;
  un article peut nourrir plusieurs synthèses).
- **`vec_synthese`** : table virtuelle sqlite-vec, `(synthese_id, embedding FLOAT[384])`,
  jointe par `synthese_id`. Sépare le vectoriel du relationnel.

**Le brief du jour** = la synthèse au meilleur score du jour le plus récent, rendue :

```
🎯 [ASSERTION]
   Parce que [argument].
   Exemple : [fait choc].
   C'est comme [image mentale].
   → So what : [impact].
   📎 Sources : RAND, Opex360.  |  Domaines : ...
   ⚠ Exemple & analogie à recouper avant diffusion.
```

---

## 6. Sources de collecte (état vérifié 2026-06-14)

| Source | Langue | Flux RSS | État |
|---|---|---|---|
| Opex360 | FR | `https://www.opex360.com/feed/` | ✅ |
| IRIS | FR | `https://www.iris-france.org/feed/` | ✅ |
| RAND | EN | `https://www.rand.org/pubs/commentary.xml` | ✅ |
| La Tribune | FR | `https://www.latribune.fr/rss/homepage` | ✅ (généraliste, le tri filtre le bruit) |
| Meta-Defense | FR | — | ❌ RSS coupé (HTTP 410). Scraping requis plus tard. |
| FRS | FR | — | ⚠️ Inaccessible depuis WSL (TLS). À retester en prod. |

Langues d'entrée : FR + EN. **Synthèse toujours produite en français.**
RAND et La Tribune exigent un **user-agent navigateur** (sinon blocage) — réglé dans le code.
Sources éditables dans `config/sources.toml` sans toucher au code.

---

## 7. Anatomie du code — fichier par fichier

> Convention : chaque module `*.py` exécutable a un `if __name__ == "__main__"` ou se lance
> via `uv run python -m synthesia.<...>`. Les commentaires du code sont en français.

### Racine

- **`pyproject.toml` / `uv.lock`** — déclaration et verrou des dépendances (gérés par `uv`).
- **`.python-version`** — fixe Python **3.10** (impact réel : pas de `tomllib`, d'où `tomli`).
- **`.env`** — la clé API `ANTHROPIC_API_KEY`. **Git-ignoré**, ne jamais committer.
- **`.env.example`** — modèle versionné montrant le format attendu du `.env`.
- **`.gitignore`** — ignore `.venv`, `.env*` (sauf `.env.example`), `data/`, caches Python.
- **`main.py`** — **stub d'origine non utilisé** (juste un `print("Hello")`). Point d'entrée
  réel = les modules `synthesia.*`. À nettoyer ou repurposer un jour.
- **`README.md`** — mode d'emploi : prérequis, les 2 programmes (pipeline vs serveur),
  commandes, dépannage.
- **`Todo.md`** — reste à faire (déploiement, améliorations, dette).
- **`Changelog.md`** — minimal.
- **`Dockerfile`** — recette de l'image conteneur (base `uv` + Python 3.12, x86-64).
  `uv sync` installe les deps ; le serveur web est le processus principal.
- **`docker-compose.yml`** — config du conteneur (port externe au choix, volume `./data`,
  clé API via `.env` du NAS). Utilisé par Container Manager (« Projet »).
- **`.dockerignore`** — exclut `.env`, `data/`, `.venv`, `.git` de l'image.

### `config/`

- **`sources.toml`** — liste des sources : pour chaque flux, `nom`, `url`, `langue`,
  `active` (bool). Modifiable sans toucher au code. Meta-Defense et FRS sont à `active=false`
  avec un commentaire expliquant pourquoi (cf. §6).

### `synthesia/collecte/` — Étapes 1 & 2 (acquisition de la matière)

- **`rss.py`** — *lecture des flux RSS.*
  - `ArticleBrut` (dataclass) : `source, langue, titre, url, date_publication`. Une entrée
    de flux, avant tout traitement.
  - `USER_AGENT` : se présente comme un navigateur (sinon RAND/La Tribune bloquent).
  - `charger_sources()` : lit `config/sources.toml`, ne garde que les sources actives.
  - `collecter_source(source)` : lit un flux, renvoie ses `ArticleBrut`.
  - `collecter_tout()` : collecte toutes les sources actives. **Tolérant aux pannes** :
    une source en échec renvoie une liste vide, n'interrompt pas les autres. Renvoie
    `{nom_source: [ArticleBrut]}`.
  - `afficher(...)` / `main()` : aperçu terminal. Lancer : `uv run python -m synthesia.collecte.rss`.

- **`extraction.py`** — *récupération du corps d'un article.*
  - Deux responsabilités volontairement séparées :
    - `telecharger(url)` : I/O réseau (httpx, user-agent navigateur, suit les redirections).
      Renvoie le HTML ou `None` en cas d'échec.
    - `extraire_texte(html)` : **traitement pur** (testable hors-ligne), via trafilatura,
      retire menus/pubs/commentaires. Renvoie `(titre, texte)`.
  - `extraire(url)` : enchaîne les deux, renvoie un `Extraction` (`url, titre, texte,
    nb_caracteres, ok, erreur`).
  - `main()` : teste l'extraction sur quelques URLs. Lancer :
    `uv run python -m synthesia.collecte.extraction`.

### `synthesia/analyse/` — Étape 3 (le cerveau LLM)

- **`schemas.py`** — *structures de sortie garanties (Pydantic).* Passées au SDK via
  `messages.parse()` : le LLM **ne peut pas** dévier du format.
  - `DomainePEMSI` : `Literal` fermé des 6 domaines (le LLM ne peut pas inventer hors liste).
  - `TriArticle` (`index, score, domaines`) + `TriResultat` (liste) → sortie de la passe 1.
  - `Cluster` (`theme, indices`) + `Regroupement` (liste) → sortie de la passe 1bis.
  - `Synthese` (`theme, domaines_pemsi, assertion, parce_que, exemple, cest_comme,
    so_what`) → sortie du Mode A. **C'est la formule rhétorique du projet.**

- **`client.py`** — *client Anthropic partagé.*
  - `MODELE_TRI = "claude-haiku-4-5"`, `MODELE_SYNTHESE = "claude-sonnet-4-6"`.
  - `get_client()` : `load_dotenv()` puis crée le client. Lève une erreur **claire** si la
    clé manque (plutôt qu'un échec réseau obscur).

- **`tri.py`** — *passe 1 (tri) + passe 1bis (regroupement), avec Haiku.*
  - `SYSTEM_TRI` : prompt système. Note chaque titre 0-100 selon l'intérêt PEMSI ; consigne
    d'être **sévère** (peu d'articles > 70).
  - `trier(titres)` → `TriResultat` : un score + domaines par titre.
  - `SYSTEM_REGROUPEMENT` + `regrouper(titres)` → `Regroupement` : clusters thématiques.

- **`synthese.py`** — *passe 2, Mode A, analyse corrélée, avec Sonnet.*
  - `SYSTEM_SYNTHESE` : prompt système. Consigne clé : **ne pas résumer pièce par pièce**,
    produire **une seule analyse corrélée** ; `cest_comme` **obligatoire, jamais vide**.
  - `ArticleSource` (dataclass) : `source, titre, texte` — un article fourni à l'analyse.
  - `analyser(articles)` → `Synthese` : prend 1..N articles d'un même thème, renvoie la fiche.

### `synthesia/stockage/` — Étape 4 (la mémoire)

- **`base.py`** — *persistance relationnelle (SQLite pur, zéro dépendance externe).*
  - `DB_PATH` = `data/synthesia.db`. `SCHEMA` = DDL des 3 tables + index.
  - `get_connection()` : ouvre la base, active les clés étrangères, lignes nommées (`Row`).
  - `init_db(conn)` : crée les tables (idempotent).
  - `inserer_article(...)` : insère **ou retrouve** par URL (dédup, `ON CONFLICT DO NOTHING`),
    renvoie l'id.
  - `maj_article(...)` : met à jour les champs renseignés (corps, domaines, score, statut).
  - `get_article`, `lister_articles(statut=?)`.
  - `SyntheseRecord` (dataclass) : miroir persistable de `Synthese` (+ `score`, `date`).
  - `inserer_synthese(rec, article_ids)` : insère la synthèse **et** crée les liaisons.
  - `get_synthese`, `articles_de_synthese(id)` (pour citer les sources),
    `lister_syntheses(date=?)`, `archiver_synthese(id)`.

- **`vecteurs.py`** — *persistance vectorielle (sqlite-vec + embeddings locaux fastembed).*
  - `MODELE_EMBED` (multilingue 384d) ; un `warnings.filterwarnings` tait un avis fastembed
    bénin (mean-pooling).
  - `_modele()` (`lru_cache`) : charge le modèle une seule fois (téléchargé au 1er appel).
  - `embed(texte)` → vecteur de 384 floats.
  - `texte_synthese(synthese)` : construit le texte représentatif à vectoriser
    (thème + assertion + argument + analogie).
  - `CACHE_EMBED` : le modèle est mis en cache dans `data/.fastembed` (volume persistant
    → pas de re-téléchargement à chaque redémarrage du conteneur).
  - `get_connection()` : comme `base.get_connection` **+ charge l'extension sqlite-vec**.
    **Filet conteneur** : si le SQLite standard a le chargement d'extensions désactivé,
    bascule automatiquement sur `pysqlite3` (`_connexion_pysqlite3`).
  - `init_vec(conn)` : crée la table virtuelle `vec_synthese`.
  - `indexer_synthese(conn, id, texte)` : calcule et stocke l'embedding.
  - `rechercher(conn, requete, k)` : **recherche par sens** — embed la requête, KNN sqlite-vec,
    renvoie `[(ligne synthèse, distance)]`. C'est la brique de récupération du futur Mode B.

### `synthesia/brief/` — Étape 5 (l'orchestrateur)

- **`pipeline.py`** — *le chef d'orchestre d'une journée. C'est ICI que tout se branche.*
  - Constantes réglables : `SEUIL_RETENU=60`, `LIMITE_CLUSTERS=3`, `MAX_ART_PAR_CLUSTER=3`.
  - `SyntheseProduite` (dataclass) : `id, record, sources`.
  - `rendre_brief(rec, sources)` : met une synthèse au format brief (avec l'avertissement
    « à recouper »).
  - `executer_brief(...)` : le pipeline complet (cf. §2). Persiste articles, scores, statuts,
    synthèses et vecteurs. **Borne le coût** (top N clusters) et **liste** les clusters non
    traités. **Affiche sa progression** (`Tri…`, `analyse…`) pour ne pas paraître figé.
    Élit la reine (meilleur score) et l'affiche.
  - Lancer : `uv run python -m synthesia.brief.pipeline` (⚠ consomme l'API).

### `synthesia/api/` — Étape 6 (consultation mobile)

- **`app.py`** — *serveur web FastAPI, page lisible sur téléphone.*
  - `lifespan` : au démarrage, `init_db` → garantit que les tables existent (base vide →
    page « Aucune synthèse », **jamais d'erreur 500** même si le pipeline n'a pas tourné).
  - `_syntheses_du_jour(conn)` : synthèses du jour le plus récent, **reclassées par score**
    (la reine d'abord — corrige un piège du tri par date d'insertion).
  - `_sources(conn, id)` : liste des sources d'une synthèse.
  - `CSS` + `_page()` + `_fiche_html()` : rendu HTML sobre, responsive, clair/sombre auto.
  - Routes :
    - `GET /` → page : 🎯 fiche reine + liste des autres synthèses du jour (cliquables).
    - `GET /synthese/{id}` → détail d'une fiche (404 si absente).
    - `GET /api/brief` → le brief en JSON.
  - Lancer : `uv run uvicorn synthesia.api.app:app --host 0.0.0.0 --port 8000`.
    Sur le téléphone (même réseau) : `http://<IP-machine>:8000`.

### `synthesia/notifier/` — envoi du brief par email (canal « push »)

- **`mail.py`** — *envoi du brief par Gmail (SMTP SSL).*
  - Config lue dans le `.env` : `EMAIL_EXPEDITEUR`, `EMAIL_MOT_DE_PASSE` (mot de passe
    d'application Gmail), `EMAIL_DESTINATAIRE` (optionnel).
  - `email_configure()` : vrai si expéditeur + mot de passe présents. **Si absent →
    l'envoi est ignoré** (pas de spam en dev/tests).
  - `_destinataires(...)` : **plusieurs destinataires** (séparés par virgules/points-virgules ;
    défaut = expéditeur).
  - `construire_email(produites, date)` → `(sujet, html, texte)` : reine en tête + autres
    synthèses, version HTML stylée + repli texte.
  - `envoyer(...)` / `envoyer_brief(produites, date)` : envoie via `smtp.gmail.com:465`.
  - Appelé en fin de `pipeline.executer_brief` (échec d'envoi non bloquant pour le run).
  - *Import de `pipeline` paresseux* pour éviter un cycle (pipeline importe ce module).

### `synthesia/pilote.py` — **OBSOLÈTE**

- Démo de l'Étape 3 (collecte → tri → synthèse → rendu, **sans persistance**). **Remplacé**
  par `brief/pipeline.py`, qui fait tout + persiste. Gardé comme référence, peut être supprimé.

### `docs/`

- **`context_prompt.md`** — CE FICHIER (porte d'entrée rapide).
- **`plan-implementation.md`** — le plan détaillé, **source de vérité** (étapes, schéma, prompts).
- **`deploiement-synology.md`** — guide pas-à-pas de déploiement sur le NAS DS224+.
- **`target.md`** — le brief initial du porteur (vision d'origine, 2 modes de prompt).
- **`memo.md`** — liens utiles (génération de clé API, ajout de fonds).

---

## 8. État d'avancement

| Étape | Objet | Statut |
|---|---|---|
| **0** | Schéma fiche + format brief | ✅ Validé |
| **1** | Collecte RSS | ✅ Fait (4 sources, ~60 art./jour) |
| **2** | Extraction du corps d'article | ✅ Fait (httpx + trafilatura) |
| **3** | Intégration LLM (tri → regroupement → analyse corrélée) | ✅ Fait, pipeline réel testé |
| **4a** | Persistance relationnelle (SQLite) | ✅ Fait (testé) |
| **4b** | Persistance vectorielle (sqlite-vec + fastembed local) | ✅ Fait (testé) |
| **5** | Brief quotidien (orchestration + persistance + élection) | ✅ Fait (pipeline réel persisté) |
| **6** | API FastAPI (page mobile + JSON) | ✅ Fait |
| **Email** | Envoi du brief par Gmail, plusieurs destinataires | ✅ **Fait** (envoi réel testé) |
| **Déploiement** | Conteneur Docker sur le NAS DS224+ (image à jour : email + correctifs) | ✅ **Fait** (en service) |
| **7** | Planification (Planificateur DSM 06h30 / 13h30) | 🟡 **En cours** : tâches à créer + tester |
| **8** | Accès distant sécurisé (Tailscale) | 🟡 Préparé (guide) — **optionnel** depuis l'email |

**Le cœur fonctionnel est complet, déployé, et livré par email** : collecte → analyse →
mémoire → consultation mobile + **email quotidien**, en service sur le NAS. Reste à
finaliser la planification (7) ; l'accès extérieur (8) est devenu optionnel.

---

## 8bis. Déploiement Synology — état réel (session du 2026-06-14)

**Cible** : Synology **DS224+** (x86-64, ~2 Go RAM). Méthode : **Docker** via
Container Manager.

**Ce qui tourne aujourd'hui** :
- Conteneur **`synthesia`** up (image **reconstruite** avec le code à jour : email,
  anti-500, progression, pysqlite3), dans le dossier `docker/synthesia` du NAS.
- Serveur web accessible sur le **réseau local** : `http://192.168.1.15:9595`
  (port externe **9595** → 8000 interne ; IP du NAS **192.168.1.15**).
- Base et cache du modèle persistés dans le volume `data/` (créé **vide** à la main sur
  le NAS — un bind mount Synology exige que le dossier existe).
- `.env` **sur le NAS** : `ANTHROPIC_API_KEY` + variables `EMAIL_*` (transmises au
  conteneur via `docker-compose.yml`). Jamais dans l'image.
- **Brief envoyé par email** à chaque exécution du pipeline.

**Reconstruire l'image après une modif de code** : Container Manager n'a pas toujours de
bouton « Construire ». Méthode fiable : Projet → Arrêter → **Supprimer** (les fichiers et
`data/` du NAS restent) → onglet Image → supprimer `synthesia:latest` → **Créer** le projet
à nouveau (rebuild). Détail dans `docs/deploiement-synology.md`.

**Pièges rencontrés et résolus** (utile si ça recasse) :
1. **Bind mount échoué** : le dossier `data` doit exister sur le NAS avant le 1er démarrage.
2. **Erreur 500 sur la page** : la base était vide **sans tables** (le serveur ne créait
   pas les tables). Réglé en lançant le pipeline (`docker exec synthesia python -m
   synthesia.brief.pipeline`) **et** par le correctif `lifespan` dans `app.py` (init au
   démarrage). ⚠️ Ce correctif n'est **pas encore dans l'image** (conteneur = ancien code).
3. **Téléphone : « rien ne s'affiche »** alors que le PC marche → le navigateur mobile
   **force le HTTPS** sur un serveur HTTP simple (logs : `Invalid HTTP request received`).
   Contournement actuel : navigation privée, ou désactiver le forçage HTTPS du navigateur.
   **Solution durable = HTTPS via Tailscale (Étape 8).**

**Important** : le conteneur en service tourne avec le code **d'avant** les derniers
correctifs (anti-500, messages de progression, bascule pysqlite3). **À reconstruire**
quand le code à jour sera sur le NAS (cf. `Todo.md`).

---

## 9. Commandes utiles

```bash
uv run python -m synthesia.collecte.rss          # collecte seule (titres + liens)
uv run python -m synthesia.collecte.extraction   # test extraction de corps
uv run python -m synthesia.brief.pipeline        # pipeline complet du jour (consomme l'API)
uv run uvicorn synthesia.api.app:app --host 0.0.0.0 --port 8000   # serveur web
uv add <paquet>                                  # ajouter une dépendance
```

---

## 10. Points de vigilance ouverts

1. **⚠️ Risque #1 — analogies fausses avec aplomb.** Le `cest_comme` et l'`exemple` sont
   l'arme du brief, mais le LLM peut produire des parallèles/chiffres **inexacts** très
   convaincants. Mitigation **légère actuellement en place** : chaque brief porte la mention
   « ⚠ Exemple & analogie à recouper avant diffusion ». Options pour muscler plus tard :
   (b) 2e passe de fact-check (web search), (c) vérification humaine assumée. **Non résolu.**
2. **Meta-Defense** : plus de RSS (410) → scraping ciblé à prévoir, ou abandon. En attente.
3. **FRS** : à revérifier depuis le serveur de prod (bloqué en dev WSL — souci TLS).
4. **Seuil de tri** (`SEUIL_RETENU=60`), **`LIMITE_CLUSTERS=3`**, **prompts** : calibrables
   au vu des rendus réels. Pas figés.
5. **Mode B (requêtes transversales)** : la brique de récupération (`vecteurs.rechercher`)
   existe ; il manque la couche LLM qui synthétise une réponse actionnable + son exposition
   dans l'API. Prévu après.
6. **`main.py`** (stub mort) et **`pilote.py`** (obsolète) à nettoyer.
7. **Conteneur NAS = ancien code** : reconstruire l'image après avoir copié le code à jour.
8. **Accès téléphone en HTTP** : forçage HTTPS des navigateurs mobiles → contourné par
   navigation privée ; à régler proprement avec Tailscale (HTTPS).
9. **RAM du NAS (~2 Go)** : pic pendant le pipeline (modèle d'embedding) — à surveiller.

> Liste actionnable complète et priorisée : **`Todo.md`** à la racine.

---

## 11. Comment reprendre le travail

1. Lis `docs/plan-implementation.md` (plan détaillé) et **`Todo.md`** (reste à faire priorisé).
2. Respecte la **démarche itérative** : propose, fais valider, exécute une étape, vérifie.
   Style concis, droit au but, phrases courtes.
3. **Prochaines actions** (toutes côté NAS, via `docs/deploiement-synology.md`) :
   - **Étape 7** : Planificateur DSM → `docker exec synthesia python -m synthesia.brief.pipeline`
     à 06h30 et 13h30.
   - **Étape 8** : Tailscale (NAS + téléphone) → accès extérieur + HTTPS propre.
   - **Reconstruire l'image** avec le code à jour (correctifs anti-500, progression, pysqlite3).
   - **Commit Git** (rien n'est versionné).
