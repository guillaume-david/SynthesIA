# Déploiement sur Synology DS224+

> Objectif : **voir ton brief du jour sur ton téléphone**, via un lien, sur le port
> de ton choix. Le DS224+ (x86-64) fait tourner SynthesIA en conteneur Docker.
>
> Le NAS assure les 3 dernières briques : le **serveur web** (Étape 6, déjà codé),
> la **planification** 6h30/13h30 (Étape 7, via le Planificateur DSM) et l'**accès
> distant sécurisé** (Étape 8, via Tailscale).

---

## Vue d'ensemble

```
NAS DS224+
├── Conteneur "synthesia"  → serveur web (port de ton choix)     [toujours allumé]
├── Planificateur DSM      → lance le pipeline à 6h30 et 13h30   [docker exec]
└── Paquet Tailscale       → accès depuis le téléphone, dehors   [VPN, rien d'exposé]
```

**Deux rôles, un seul conteneur :**
- le **serveur web** est le processus principal du conteneur (il tourne en continu, léger) ;
- le **pipeline** (qui produit le brief, plus lourd) est déclenché ponctuellement
  *dans* ce conteneur par le Planificateur DSM.

---

## Prérequis (sur le NAS, une fois)

1. **DSM 7.2+**.
2. **Container Manager** installé (Centre de paquets).
3. **Tailscale** installé (Centre de paquets) — pour l'accès mobile depuis l'extérieur.
4. Un dossier partagé `docker` (créé par défaut par Container Manager) accessible via
   **File Station**.

---

## Étape A — Déposer le projet sur le NAS

1. Dans **File Station**, crée le dossier `docker/synthesia`.
2. Copies-y le contenu du projet (au minimum : `Dockerfile`, `docker-compose.yml`,
   `.dockerignore`, `pyproject.toml`, `uv.lock`, le dossier `synthesia/`, le dossier
   `config/`). Glisser-déposer depuis ton PC suffit.
3. **Crée le fichier de clé API** : dans `docker/synthesia`, crée un fichier nommé
   **`.env`** contenant **une seule ligne** :
   ```
   ANTHROPIC_API_KEY=sk-ant-...ta_clé...
   ```
   > C'est ce fichier (sur le NAS, jamais dans l'image, jamais sur GitHub) qui fournit
   > la clé au conteneur.

---

## Étape B — Construire et lancer le conteneur

1. Ouvre **Container Manager → Projet → Créer**.
2. **Nom du projet** : `synthesia`. **Chemin** : le dossier `docker/synthesia`.
3. **Source** : « Utiliser un fichier docker-compose.yml existant » (celui que tu as déposé).
4. **Choisis ton port** : dans `docker-compose.yml`, la ligne `ports` est `"8000:8000"`.
   Le nombre **de gauche** est le port externe — mets celui que tu veux (ex. `"9595:8000"`).
   Tu peux l'éditer directement dans l'éditeur de Container Manager.
5. Lance la construction. Le NAS télécharge les dépendances et fabrique l'image
   (**quelques minutes** la première fois — pas de panique).
6. Une fois démarré, le conteneur **`synthesia`** tourne. Le serveur web écoute sur ton port.

---

## Étape C — Premier remplissage (produire un premier brief)

La base est vide au départ — il faut lancer le pipeline une fois pour avoir une synthèse.

Dans **Container Manager → Conteneur `synthesia` → Terminal**, ou en SSH sur le NAS :
```bash
docker exec synthesia python -m synthesia.brief.pipeline
```
> ⏳ Le **premier** lancement télécharge aussi le modèle d'embedding (~220 Mo) → compte
> quelques minutes. Les suivants sont plus rapides (modèle mis en cache dans le volume).
> C'est l'étape la plus gourmande en RAM — voir « Dépannage » si ça coince.

---

## Étape D — Tester sur ton réseau local

Sur ton téléphone (connecté au **même Wi-Fi**), ouvre :
```
http://<IP-du-NAS>:<ton-port>
```
(IP du NAS : visible dans DSM, ou via `Panneau de configuration → Réseau`.)

➡️ **Tu dois voir ton brief du jour.** 🎯

---

## Étape E — Planifier le pipeline (6h30 et 13h30)

Dans **DSM → Panneau de configuration → Planificateur de tâches → Créer → Tâche planifiée
→ Script défini par l'utilisateur** :

- **Utilisateur** : `root`.
- **Programmation** : tous les jours, à `06:30`. (Crée une 2e tâche pour `13:30`.)
- **Script** :
  ```bash
  docker exec synthesia python -m synthesia.brief.pipeline
  ```
  > Si `docker` n'est pas trouvé, utilise le chemin complet :
  > `/usr/local/bin/docker exec synthesia python -m synthesia.brief.pipeline`.

À chaque déclenchement, le brief est régénéré et la page web se met à jour.

---

## Étape F — Accès mobile depuis l'extérieur (Tailscale)

**Sans ouvrir aucun port sur Internet** (OPSEC) :

1. Sur le NAS : ouvre le paquet **Tailscale**, connecte-toi à ton compte.
2. Sur ton téléphone : installe l'app **Tailscale**, connecte-toi au **même compte**.
3. Récupère le nom/IP Tailscale du NAS (dans l'app ou la console Tailscale).
4. Depuis n'importe où (4G/5G incluse), ouvre :
   ```
   http://<nom-ou-IP-Tailscale-du-NAS>:<ton-port>
   ```

➡️ Ton brief, partout, chiffré, sans exposer ton NAS.

---

## Dépannage

- **Vérifier que le SQLite du conteneur charge les extensions** (sécurité sqlite-vec) :
  ```bash
  docker exec synthesia python -c "from synthesia.stockage import vecteurs, base; \
c=vecteurs.get_connection(base.DB_PATH); print('vecteurs OK')"
  ```
  Le code bascule automatiquement sur `pysqlite3` si besoin — ce test doit afficher `vecteurs OK`.

- **Mémoire (le DS224+ a ~2 Go)** : le pic se produit pendant le pipeline (modèle
  d'embedding). Si le pipeline est tué (OOM) :
  - lance-le quand le NAS est peu sollicité (pas pendant une sauvegarde, etc.) ;
  - en dernier recours, on peut produire le brief sur le PC et ne garder que le serveur
    web sur le NAS (la base est un simple fichier à synchroniser).

- **Page « Aucune synthèse »** : la base est vide → lance le pipeline (Étape C).

- **`docker: command not found` dans le Planificateur** : utilise le chemin complet
  `/usr/local/bin/docker`.

- **Voir les logs** : Container Manager → conteneur `synthesia` → Journal ; ou
  `docker logs synthesia`.
