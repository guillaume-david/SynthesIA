# Changelog

## 20260616 migration vers Gemini pour limiter les coûts
- ajout de GEMINI_API_KEY dans .env
- modification de analyse/client.py analyse/tri.py analyse/synthèse.py et analyse/pipeline.py (partie 5)

## 20260614
claude --resume 12e43257-dbfa-466a-914f-789d9b75c45d

- initialisation du projet
- **Étape 0** — schéma de données figé : tables `article` / `synthese`, format pivot du
  brief (ASSERTION → PARCE QUE → EXEMPLE → C'EST COMME → SO WHAT).
- **Étape 1** — collecte RSS (`collecte/rss.py`) : 4 sources actives (Opex360, IRIS, RAND,
  La Tribune) ; Meta-Defense (RSS coupé) et FRS (TLS WSL) désactivées.
- **Étape 2** — extraction du corps d'article (`collecte/extraction.py`, httpx + trafilatura).
- **Étape 3** — intégration LLM (`analyse/`) : tri Haiku + regroupement + analyse corrélée
  Sonnet, sorties structurées garanties (Pydantic + `messages.parse`).
- **Étape 4a** — persistance relationnelle SQLite (`stockage/base.py`), dédup par URL.
- **Étape 4b** — persistance vectorielle (`stockage/vecteurs.py`) : sqlite-vec + embeddings
  locaux fastembed (multilingue 384d), recherche par sens. Bascule `pysqlite3` en conteneur.
- **Étape 5** — orchestration du brief quotidien (`brief/pipeline.py`) : collecte → tri →
  regroupement → analyse → persistance + indexation → élection de la fiche reine.
- **Étape 6** — API web FastAPI (`api/app.py`) : page mobile (brief + détail) + JSON ;
  init des tables au démarrage (anti-500).
- **Email** — envoi du brief par Gmail (`notifier/mail.py`), plusieurs destinataires.
- **Déploiement** — Dockerfile + docker-compose + guide Synology ; conteneur en service sur
  le NAS DS224+, brief consultable au téléphone (LAN) et envoyé par email.
- **Docs** — `context_prompt.md`, `plan-implementation.md`, `deploiement-synology.md`,
  `README.md`, `Todo.md`.
