# SynthesIA — TODO

État au 2026-06-14. Le cœur (collecte → analyse → mémoire → API + email) est **fait et
déployé sur le NAS** ; le brief est consultable au téléphone (LAN) et **envoyé par email**.
Reste à finaliser la planification, puis l'accès extérieur et quelques finitions.

## Prioritaire — finir le déploiement

- [~] **Étape 7 — Automatiser le pipeline.** Planificateur DSM, 2 tâches : 06h30 et 13h30,
      script `docker exec synthesia python -m synthesia.brief.pipeline` (chemin complet
      `/usr/local/bin/docker` si besoin). **En cours** : tâches à créer + tester via
      « Exécuter ». Réf : `docs/deploiement-synology.md` §E.
- [ ] **Étape 8 — Tailscale.** Installer le paquet sur le NAS + l'app sur le téléphone
      → accès depuis l'extérieur (4G/5G) **sans exposer de port**. Réf : §F.
      Devenu **optionnel** depuis l'email (qui livre déjà le brief partout). Bonus : règle
      le souci de navigation privée (HTTPS propre via `tailscale serve`).
- [x] **Image reconstruite avec le code à jour** (anti-500, progression, pysqlite3, email).
- [ ] **Commit Git** — rien n'est versionné pour l'instant.

## Améliorations fonctionnelles

- [ ] **Risque #1 — analogies fausses.** Aujourd'hui : simple mention « à recouper ».
      À muscler : 2e passe LLM de fact-check (web search) ou validation humaine assumée.
- [ ] **Mode B — recherche transversale.** La brique `vecteurs.rechercher` existe ; il
      manque la couche LLM (réponse actionnable) + une route API (`/recherche?q=...`).
- [ ] **Meta-Defense** — RSS coupé (410) : prévoir un scraping ciblé, ou abandonner.
- [ ] **FRS** — revérifier l'accès **depuis le NAS** (bloqué en dev WSL pour cause TLS).
- [ ] **Calibrage** — ajuster `SEUIL_RETENU` (60), `LIMITE_CLUSTERS` (3), et les prompts
      au vu des briefs réels.

## Nettoyage / dette technique

- [ ] Supprimer `main.py` (stub mort) et `synthesia/pilote.py` (obsolète, remplacé par
      `brief/pipeline.py`).
- [ ] Surveiller la **RAM du NAS** (~2 Go) pendant le pipeline — pic = chargement du
      modèle d'embedding. Mitigations dans `docs/deploiement-synology.md` § Dépannage.

## Email quotidien — ✅ FAIT

- [x] Module `synthesia/notifier/mail.py` : envoi du brief par Gmail.
- [x] **Plusieurs destinataires** (séparés par virgules ; défaut = expéditeur).
- [x] Mot de passe d'application Gmail créé + `.env` (PC) configuré ; **envoi réel testé** ✅.
- [x] `docker-compose.yml` transmet les variables `EMAIL_*` au conteneur.
- [x] Variables `EMAIL_*` ajoutées au `.env` **du NAS**.
- [ ] Vérifier l'envoi depuis la **tâche planifiée** (une fois l'Étape 7 finalisée).

## Idées (plus tard)

- [ ] HTTPS propre (via Tailscale `serve`) — confort + fin du souci navigateur.
- [ ] Page d'historique / recherche dans l'API.
